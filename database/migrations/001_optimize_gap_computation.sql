-- Migration: Optimize gap computation
-- Replaces per-room recursive CTE with pre-computed gap arrays and set-based window functions
-- Run this BEFORE deploying the updated SQL functions

BEGIN;

-- 1. Add pre-computed gap columns to cache table
ALTER TABLE room_availability_cache
    ADD COLUMN IF NOT EXISTS gap_starts TIME[],
    ADD COLUMN IF NOT EXISTS gap_ends TIME[],
    ADD COLUMN IF NOT EXISTS gap_minutes REAL[];

-- 2. Drop redundant indexes (subsumed by new covering index)
DROP INDEX IF EXISTS idx_class_schedule_next;
DROP INDEX IF EXISTS idx_class_schedule_room_day;

-- 3. Add covering index for gap analysis (avoids heap lookups)
CREATE INDEX IF NOT EXISTS idx_class_schedule_room_day_times
    ON class_schedule(building_name, room_number, day_of_week, start_time, end_time);

COMMIT;

-- 4. After deploying updated functions, refresh the cache to populate gap arrays:
-- SELECT refresh_room_availability_cache(CURRENT_DATE);
