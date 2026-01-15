# ucfSpots Data Collection

This directory contains scripts for collecting and processing UCF course and building data. The process is split into multiple stages to collect, transform, and load the data.

## Scripts & Data Flow

1. **scraper.py**

   - Scrapes all course data from UCF "Class Search" system
   - Output: `archive/courses_{TERM}.json`

2. **subject_to_buildings.py**

   - Transforms subject-sorted data into building-sorted data
   - Input: `archive/courses_{TERM}.json`
   - Output: `archive/buildings_derived_{TERM}.json`

3. **filter_buildings.py**

   - Filters buildings based on criteria (minimum rooms, exclusion list)
   - Input: `archive/buildings_derived_{TERM}.json`
   - Output: `archive/buildings_filtered_{TERM}.json`

4. **add_building_hours.py**

   - Adds operating hours to each building
   - Input: `archive/buildings_filtered_{TERM}.json`, `data/building_hours.json`
   - Updates: `archive/buildings_filtered_{TERM}.json`

5. **add_building_coordinates.py**

   - Adds geographical coordinates to each building
   - Input: `archive/buildings_filtered_{TERM}.json`, `data/ucf_buildings.geojson`
   - Output: `archive/buildings_enriched_{TERM}.json`

6. **load_to_postgres.py**

   - Loads the final data into Supabase PostgreSQL database
   - Input: `archive/buildings_enriched_{TERM}.json`, `data/academic_calendar.json`
   - Creates and populates database tables (buildings, rooms, class_schedule, academic_terms)

7. **events_scraper.py** (To Be Implemented)
   - Scrapes daily event data from events.ucf.edu and loads it into PostgreSQL
   - Updates the `daily_events` table with current day's events
   - **Note:** This script is intended to run as a cron job daily to keep the `daily_events` table up-to-date.

## Data Flow Diagram

```
Web Data → courses_{TERM}.json → buildings_derived_{TERM}.json → buildings_filtered_{TERM}.json
                                                                    ↓
                                                  [+ building hours & coordinates]
                                                                    ↓
                                                   buildings_enriched_{TERM}.json
                                                                    ↓
                                                              Database Load
                                                                    ↓
                                                  [+ daily events from events.ucf.edu]
                                                                    ↓
                                                              Database Update
```

## Environment

- Python 3.11+
- Install dependencies: `pip install -r requirements.txt`
- `.env.local` with `SUPABASE_URL` and `SUPABASE_KEY` (needed for `load_to_postgres.py`)

## Quick Run

1. Scrape courses → `archive/courses_SP26.json`  
   `python scraper.py --term SP26`

2. Derive buildings → `archive/buildings_derived_SP26.json`  
   `python subject_to_buildings.py --term SP26`

3. Filter buildings → `archive/buildings_filtered_SP26.json`  
   `python filter_buildings.py --term SP26`

4. Add hours (in place) → `archive/buildings_filtered_SP26.json`  
   `python add_building_hours.py --term SP26`

5. Add coordinates → `archive/buildings_enriched_SP26.json`  
   `python add_building_coordinates.py --term SP26`

6. Load to Postgres (reads `archive/buildings_enriched_SP26.json` and `data/academic_calendar.json`)  
   `python load_to_postgres.py --term SP26`

## Building Filtering Criteria

- Minimum 4 rooms per building
- Certain buildings explicitly excluded (see [`filter_buildings.py`](filter_buildings.py))
  - Currently excluded: DPAC, RSH, CROL, PAC

## Database Schema

- See [`tables.sql`](../database/schema/tables.sql)

## Required Input Files

- `data/building_hours.json`: Building operating hours
- `data/ucf_buildings.geojson`: Building coordinate data
- `data/academic_calendar.json`: Academic term date ranges

## Output Files

- `archive/courses_{TERM}.json`: Raw course data organized by subject
- `archive/buildings_derived_{TERM}.json`: Data reorganized by building and room
- `archive/buildings_filtered_{TERM}.json`: Filtered building data (exclusions/min rooms), also enriched with hours
- `archive/buildings_enriched_{TERM}.json`: Final processed building data including hours and coordinates

## Term Codes

Term codes follow the format: `{SEASON}{YEAR}`

- `SP26` = Spring 2026
- `FA25` = Fall 2025
- `SU25` = Summer 2025

All scripts accept a `--term` parameter to specify which term's data to process.
