-- ============================================
-- get_cached_spots Function
-- ============================================
-- Fast version of get_spots using pre-computed cache
-- Falls back to get_spots if cache is not available
-- ============================================

CREATE OR REPLACE FUNCTION get_cached_spots(
    check_time_param TIME,
    check_date_param DATE,
    min_minutes_param INTEGER DEFAULT 30
)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
    check_timestamp TIMESTAMP;
    min_interval INTERVAL;
BEGIN
    SET LOCAL statement_timeout = '6s';

    -- If cache doesn't exist for this date, fall back to real-time calculation
    IF NOT EXISTS (SELECT 1 FROM room_availability_cache WHERE check_date = check_date_param LIMIT 1) THEN
        RETURN get_spots(check_time_param, check_date_param, min_minutes_param);
    END IF;
    
    check_timestamp := (check_date_param || ' ' || check_time_param)::timestamp;
    min_interval := (min_minutes_param || ' minutes')::interval;

    WITH building_info AS (
        SELECT 
            b.name,
            b.latitude,
            b.longitude,
            -- Determine open/close for this specific day
            CASE EXTRACT(DOW FROM check_date_param)
                WHEN 1 THEN b.monday_open WHEN 2 THEN b.tuesday_open WHEN 3 THEN b.wednesday_open
                WHEN 4 THEN b.thursday_open WHEN 5 THEN b.friday_open WHEN 6 THEN b.saturday_open
                WHEN 0 THEN b.sunday_open
            END as open_time,
            CASE EXTRACT(DOW FROM check_date_param)
                WHEN 1 THEN b.monday_close WHEN 2 THEN b.tuesday_close WHEN 3 THEN b.wednesday_close
                WHEN 4 THEN b.thursday_close WHEN 5 THEN b.friday_close WHEN 6 THEN b.saturday_close
                WHEN 0 THEN b.sunday_close
            END as close_time
        FROM buildings b
    ),
    room_state AS (
        SELECT
            c.building_name,
            c.room_number,
            bi.open_time,
            bi.close_time,
            c.schedule_data,
            c.busy_times,
            c.gap_starts,
            c.gap_ends,
            c.gap_minutes,
            -- Is the room currently occupied?
            (c.busy_times @> check_timestamp) as is_occupied,

            -- Find current class details from JSON
            (SELECT item FROM jsonb_array_elements(c.schedule_data) as item
             WHERE (item->>'start')::time <= check_time_param AND (item->>'end')::time > check_time_param
             LIMIT 1) as current_class_json,

            -- Find next class details from JSON
            (SELECT item FROM jsonb_array_elements(c.schedule_data) as item
             WHERE (item->>'start')::time > check_time_param
             ORDER BY (item->>'start')::time ASC
             LIMIT 1) as next_class_json

        FROM room_availability_cache c
        JOIN building_info bi ON c.building_name = bi.name
        WHERE c.check_date = check_date_param
          AND bi.open_time IS NOT NULL -- Only consider open buildings
    ),
    calculated_availability AS (
        SELECT
            rs.*,
            -- Extract timestamps from JSON for easier math
            (rs.current_class_json->>'end')::time as current_end_time,
            (rs.next_class_json->>'start')::time as next_start_time,
            
            -- Calculate Available Until
            CASE 
                WHEN NOT rs.is_occupied THEN
                    COALESCE((rs.next_class_json->>'start')::time, rs.close_time)
                ELSE NULL
            END as available_until_time
        FROM room_state rs
    ),
    -- For occupied rooms, find the first meaningful gap from pre-computed arrays
    occupied_gap AS (
        SELECT
            ca.building_name,
            ca.room_number,
            g.gap_start as meaningful_available_at,
            g.gap_end as meaningful_available_until
        FROM calculated_availability ca
        CROSS JOIN LATERAL (
            SELECT
                ca.gap_starts[idx] as gap_start,
                ca.gap_ends[idx] as gap_end
            FROM generate_series(1, COALESCE(array_length(ca.gap_starts, 1), 0)) as idx
            WHERE ca.gap_starts[idx] >= ca.current_end_time
              AND ca.gap_minutes[idx] >= EXTRACT(EPOCH FROM min_interval) / 60
            ORDER BY ca.gap_starts[idx]
            LIMIT 1
        ) g
        WHERE ca.is_occupied
          AND ca.gap_starts IS NOT NULL
    ),
    final_metrics AS (
        SELECT
            ca.*,
            CASE
                WHEN is_occupied THEN 'occupied'
                ELSE 'available'
            END as status_text,

            -- passingPeriod logic: Available, but next class starts within min interval
            -- Must check next_start_time IS NOT NULL to avoid false positives near closing
            (NOT is_occupied AND next_start_time IS NOT NULL AND (next_start_time - check_time_param) < min_interval) as is_passing_period,

            -- availableFor logic: now uses pre-computed gaps for occupied rooms
            CASE
                WHEN NOT is_occupied THEN
                    EXTRACT(EPOCH FROM (available_until_time - check_time_param))/60
                WHEN is_occupied AND og.meaningful_available_at IS NOT NULL THEN
                    CASE
                        WHEN og.meaningful_available_until IS NOT NULL THEN
                            EXTRACT(EPOCH FROM (og.meaningful_available_until - og.meaningful_available_at))/60
                        ELSE
                            EXTRACT(EPOCH FROM (ca.close_time - og.meaningful_available_at))/60
                    END
                ELSE NULL
            END as available_for_minutes,

            -- availableAt logic: uses meaningful gap start for occupied rooms
            -- Falls back to close_time when no meaningful gap exists (matches get_spots behavior)
            CASE
                WHEN is_occupied THEN COALESCE(og.meaningful_available_at, ca.close_time)
                ELSE NULL
            END as available_at_time
        FROM calculated_availability ca
        LEFT JOIN occupied_gap og ON ca.building_name = og.building_name
            AND ca.room_number = og.room_number
    ),
    -- Aggregation per building
    building_agg AS (
        SELECT
            bi.name,
            jsonb_build_object(
                'name', bi.name,
                'coordinates', jsonb_build_object('latitude', bi.latitude, 'longitude', bi.longitude),
                'hours', jsonb_build_object('open', bi.open_time, 'close', bi.close_time),
                'isOpen', COALESCE((check_time_param >= bi.open_time AND check_time_param < bi.close_time), false),
                'roomCounts', jsonb_build_object(
                    'total', COUNT(fm.room_number),
                    'available', COUNT(fm.room_number) FILTER (WHERE fm.status_text = 'available')
                ),
                'rooms', COALESCE(jsonb_object_agg(
                    fm.room_number,
                    jsonb_build_object(
                        'status', fm.status_text,
                        'available', fm.status_text = 'available',
                        'passingPeriod', fm.is_passing_period,
                        'currentClass', fm.current_class_json->'details',
                        'nextClass', fm.next_class_json->'details',
                        'availableAt', fm.available_at_time,
                        'availableUntil', fm.available_until_time,
                        'availableFor', fm.available_for_minutes
                    )
                ) FILTER (WHERE fm.room_number IS NOT NULL), '{}'::jsonb)
            ) as building_data
        FROM building_info bi
        LEFT JOIN final_metrics fm ON bi.name = fm.building_name
        GROUP BY bi.name, bi.latitude, bi.longitude, bi.open_time, bi.close_time
    )
    SELECT jsonb_build_object(
        'timestamp', NOW(),
        'buildings', jsonb_object_agg(name, building_data)
    ) INTO result
    FROM building_agg;

    RETURN result;
END;
$$ LANGUAGE plpgsql;
