# ucfSpots Data Collection

This directory contains scripts for collecting and processing UCF course and building data. The process is split into multiple stages to collect, transform, and load the data.

## Orchestrator

`run_pipeline.py` runs all 6 implemented steps in order (`scrape` → `transform` → `filter` → `hours` → `coordinates` → `load`) with shared logging, input/output validation, and partial-run support. Step config (file paths, step names) lives in `pipeline_config.py`; reusable scraping/parsing helpers live in `parsers.py`.

```bash
python run_pipeline.py --term SP26                              # Run all steps
python run_pipeline.py --term SP26 --skip-scrape                # Shortcut for --start-from transform
python run_pipeline.py --term SP26 --start-from filter --stop-after hours
python run_pipeline.py --term SP26 --dry-run                    # Validate without modifying data
python run_pipeline.py --term SP26 --verbose                    # Debug logging
```

Step names: `scrape`, `transform`, `filter`, `hours`, `coordinates`, `load`. Individual step scripts below remain runnable standalone.

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

   - Adds operating hours to each building (modifies the filtered file in place)
   - Input: `archive/buildings_filtered_{TERM}.json`, `data/building_hours.json`
   - Updates: `archive/buildings_filtered_{TERM}.json` in place

5. **add_building_coordinates.py**

   - Adds geographical coordinates to each building
   - Input: `archive/buildings_filtered_{TERM}.json`, `data/ucf_buildings.geojson`
   - Output: `archive/buildings_enriched_{TERM}.json`

6. **load_to_postgres.py**

   - Loads the final data into Supabase PostgreSQL database
   - Input: `archive/buildings_enriched_{TERM}.json`, `data/academic_calendar.json`
   - Creates and populates database tables (buildings, rooms, class_schedule, academic_terms)

## Planned / Not Yet Implemented

- **events_scraper.py** — will scrape daily event data from events.ucf.edu and upsert it into the `daily_events` table. Intended to run as a daily cron job. Not part of `run_pipeline.py` and not present in the repo yet.

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
                              (planned) [+ daily events from events.ucf.edu]
                                                                    ↓
                                                       (planned) Database Update
```

## Environment

- Python 3.11+ (developed against 3.14)
- Install dependencies: `pip install -r requirements.txt`
- `SUPABASE_URL` and `SUPABASE_KEY` (service-role key) must be available for `load_to_postgres.py`. The script uses `find_dotenv(".env.local")` to discover a `.env.local`, but note that `frontend/.env.local` uses different variable names (`NEXT_PUBLIC_SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY`) and will NOT be picked up automatically. Create a `pipeline/.env.local` with the pipeline-specific names:

  ```env
  SUPABASE_URL=https://xxxxx.supabase.co
  SUPABASE_KEY=your_service_role_key
  ```

## Quick Run

Single command (recommended):

```bash
python run_pipeline.py --term SP26
```

Or run steps individually:

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

## Tests

Tests live under `tests/` (with fixtures in `tests/fixtures/`). Pytest config is in `pyproject.toml`.

```bash
pytest                       # Unit tests (integration tests skipped by default)
pytest -m integration        # Live tests against PeopleSoft / Supabase
pytest tests/test_parsers.py # Single module
```

## Building Filtering Criteria

- Minimum 4 rooms per building
- Certain buildings explicitly excluded — see the `excluded_buildings` set in [`filter_buildings.py`](filter_buildings.py) for the authoritative list.

## Database Schema

- Tables: [`tables.sql`](../database/schema/tables.sql), [`cache_tables.sql`](../database/schema/cache_tables.sql), [`feedback.sql`](../database/schema/feedback.sql)
- Functions: [`database/functions/`](../database/functions) (`get_spots`, `get_cached_spots`, `get_room_schedule`, `get_room_schedule_cached`, `refresh_room_availability_cache`)
- Migrations: [`database/migrations/`](../database/migrations) — currently `001_optimize_gap_computation.sql` (required for `get_cached_spots` gap arrays)

## Required Input Files

- `data/building_hours.json`: Building operating hours
- `data/ucf_buildings.geojson`: Building coordinate data
- `data/academic_calendar.json`: Academic term date ranges
- Supabase credentials (`SUPABASE_URL`, `SUPABASE_KEY`) in a discoverable `.env.local` for `load_to_postgres.py`

## Output Files

- `archive/courses_{TERM}.json`: Raw course data organized by subject
- `archive/buildings_derived_{TERM}.json`: Data reorganized by building and room
- `archive/buildings_filtered_{TERM}.json`: Filtered building data (exclusions/min rooms), also enriched with hours
- `archive/buildings_enriched_{TERM}.json`: Final processed building data including hours and coordinates

## Term Codes

Term codes follow the format: `{SEASON}{YEAR}`

Examples:

- `SP26` = Spring 2026
- `FA25` = Fall 2025
- `SU25` = Summer 2025

Any `{SEASON}{YEAR}` code recognized by PeopleSoft works; the values above are just the currently archived terms. All scripts accept a `--term` parameter to specify which term's data to process.
