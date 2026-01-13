-- ============================================
-- Cache Tables
-- ============================================
-- Used to pre-compute room availability for faster queries
-- Cache is refreshed daily via cron job
-- ============================================

-- Room availability cache: Pre-computed room availability for each date
CREATE TABLE IF NOT EXISTS room_availability_cache (
    building_name TEXT,
    room_number TEXT,
    check_date DATE,
    busy_times tsmultirange,      -- Multirange of busy timestamps
    schedule_data JSONB,          -- Pre-computed schedule blocks as JSON
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (building_name, room_number, check_date)
);

-- Cache indexes
CREATE INDEX IF NOT EXISTS idx_cache_check_date 
    ON room_availability_cache(check_date);
-- GIST index for fast overlap queries on busy times
CREATE INDEX IF NOT EXISTS idx_cache_busy_times 
    ON room_availability_cache USING GIST (busy_times);
