-- ============================================
-- Database Schema
-- ============================================
-- Building names: Uses building codes (BA1, CB1, etc.)
-- Buildings table: Stores building information, hours, and coordinates
-- Building codes are used as primary keys (e.g., BA1, CB1, NSC)
-- ============================================

CREATE TABLE buildings (
    name TEXT PRIMARY KEY,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(10, 8),
    monday_open TIME,
    monday_close TIME,
    tuesday_open TIME,
    tuesday_close TIME,
    wednesday_open TIME,
    wednesday_close TIME,
    thursday_open TIME,
    thursday_close TIME,
    friday_open TIME,
    friday_close TIME,
    saturday_open TIME,
    saturday_close TIME,
    sunday_open TIME,
    sunday_close TIME
);

-- Rooms table: Stores all rooms in each building
CREATE TABLE rooms (
    building_name TEXT REFERENCES buildings(name) ON DELETE CASCADE,
    room_number TEXT,
    PRIMARY KEY (building_name, room_number)
);

-- Class schedule table: Stores all class sections with times and dates
-- UCF course codes follow format like "ACG 2021", "COP 3502"
CREATE TABLE class_schedule (
    building_name TEXT,
    room_number TEXT,
    course_code TEXT NOT NULL,
    course_title TEXT NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    day_of_week CHAR(1) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    -- Generated column for efficient date range queries
    date_range daterange GENERATED ALWAYS AS (
        daterange(start_date, end_date, '[]')
    ) STORED,

    FOREIGN KEY (building_name, room_number)
        REFERENCES rooms(building_name, room_number) ON DELETE CASCADE,

    -- Day codes: M=Monday, T=Tuesday, W=Wednesday, R=Thursday, F=Friday, S=Saturday, U=Sunday
    CONSTRAINT valid_class_day
        CHECK (day_of_week IN ('M','T','W','R','F','S','U')),
    CONSTRAINT valid_class_times
        CHECK (end_time > start_time),
    CONSTRAINT valid_term_dates
        CHECK (end_date >= start_date)
);

-- Class schedule indexes for performance
CREATE INDEX idx_class_schedule_day_time
    ON class_schedule(day_of_week, start_time, end_time);
CREATE INDEX idx_class_schedule_next
    ON class_schedule(day_of_week, start_time);
CREATE INDEX idx_class_schedule_room_day
    ON class_schedule(building_name, room_number, day_of_week);
CREATE INDEX idx_class_schedule_daterange
    ON class_schedule USING gist (date_range);

-- Daily events table: Stores university events that occupy rooms
-- Events are scraped from events.ucf.edu
CREATE TABLE daily_events (
    id SERIAL PRIMARY KEY,
    building_name TEXT NOT NULL,
    room_number TEXT NOT NULL,
    event_name TEXT NOT NULL,
    occupant TEXT NOT NULL DEFAULT '',
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    FOREIGN KEY (building_name, room_number)
        REFERENCES rooms(building_name, room_number) ON DELETE CASCADE,
    CONSTRAINT valid_event_times
        CHECK (end_time > start_time)
);

-- Daily events indexes (fixed: use DATE() function instead of non-existent event_date column)
CREATE INDEX idx_daily_events_date_time
    ON daily_events(DATE(start_time AT TIME ZONE 'America/New_York'), start_time, end_time);
CREATE INDEX idx_daily_events_room
    ON daily_events(building_name, room_number);

-- Academic terms table: Stores semester date ranges
-- Used to determine if a class is active on a given date
CREATE TABLE academic_terms (
    id SERIAL PRIMARY KEY,
    academic_year TEXT,           -- e.g., "2025-2026"
    term TEXT,                    -- e.g., "Spring", "Fall", "Summer"
    part_of_term CHAR(1) NULL,    -- Optional: 'A' or 'B' for split terms, NULL if not applicable
    start_date DATE,
    end_date DATE,

    CONSTRAINT valid_part_of_term
        CHECK (part_of_term IS NULL OR part_of_term IN ('A', 'B')),
    CONSTRAINT valid_term_dates
        CHECK (end_date > start_date)
);

CREATE INDEX idx_academic_terms_dates
    ON academic_terms(start_date, end_date);
