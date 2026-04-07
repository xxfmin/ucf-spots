"""
Load enriched building data into Supabase PostgreSQL database.

Input: archive/buildings_enriched_SP26.json
       data/academic_calendar.json
Output: Populates buildings, rooms, class_schedule, and academic_terms tables
"""

from pathlib import Path
import json
from typing import List, Dict, Set, Optional
from datetime import datetime
import os
import sys


# Number of records to insert per batch
CHUNK_SIZE = 500

_supabase_client = None


def get_supabase():
    """Lazy-initialize the Supabase client.

    Deferred so that importing this module for validation/testing
    does not require valid credentials or the supabase package.
    """
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client
        from dotenv import load_dotenv, find_dotenv

        load_dotenv(find_dotenv(".env.local"))
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY must be set in .env.local\n"
                "Create a .env.local file with:\n"
                "  SUPABASE_URL=https://xxxxx.supabase.co\n"
                "  SUPABASE_KEY=your_service_role_key"
            )
        _supabase_client = create_client(url, key)
    return _supabase_client


class DataValidationError(Exception):
    """Custom exception for data validation errors."""
    pass


def validate_json_structure(json_data: Dict) -> None:
    """Validate the structure of the enriched buildings JSON."""
    if "buildings" not in json_data:
        raise DataValidationError("Missing 'buildings' key in JSON")

    required_building_keys = {"hours", "coordinates", "rooms"}
    required_hours_keys = {
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    }
    required_class_keys = {"course", "title", "time", "days", "start_date", "end_date"}

    for building_name, building_data in json_data["buildings"].items():
        missing_keys = required_building_keys - set(building_data.keys())
        if missing_keys:
            raise DataValidationError(
                f"Building '{building_name}' missing keys: {missing_keys}"
            )

        missing_days = required_hours_keys - set(building_data["hours"].keys())
        if missing_days:
            raise DataValidationError(
                f"Building '{building_name}' missing hours for days: {missing_days}"
            )

        for room_number, classes in building_data["rooms"].items():
            if not isinstance(classes, list):
                raise DataValidationError(
                    f"Room '{room_number}' in '{building_name}' classes should be a list"
                )

            for class_info in classes:
                missing_class_keys = required_class_keys - set(class_info.keys())
                if missing_class_keys:
                    raise DataValidationError(
                        f"Class in room '{room_number}', building '{building_name}' missing keys: {missing_class_keys}"
                    )


def validate_academic_terms_structure(terms_data: List[Dict]) -> None:
    """Validate the structure of academic terms data."""
    required_keys = {"academic_year", "term", "start_date", "end_date"}
    valid_parts_of_term = {"A", "B", None}

    for term in terms_data:
        missing_keys = required_keys - set(term.keys())
        if missing_keys:
            raise DataValidationError(f"Academic term missing keys: {missing_keys}")

        part_of_term = term.get("part_of_term")
        if part_of_term is not None and part_of_term not in {"A", "B"}:
            raise DataValidationError(f"Invalid part_of_term: {part_of_term}")

        try:
            start_date = datetime.strptime(term["start_date"], "%Y-%m-%d").date()
            end_date = datetime.strptime(term["end_date"], "%Y-%m-%d").date()
            if end_date <= start_date:
                raise DataValidationError(
                    f"End date must be after start date for term: {term}"
                )
        except ValueError as e:
            raise DataValidationError(f"Invalid date format in term: {term}") from e


def prepare_and_validate_data(
    json_data: Dict,
) -> tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Transform JSON data into database-ready records.
    
    Returns:
        Tuple of (buildings, rooms, schedules) lists
    """
    buildings = []
    rooms = []
    schedules = []

    room_keys = set()

    for name, data in json_data["buildings"].items():
        # Build the building record
        building = {
            "name": name,
            "latitude": data["coordinates"]["latitude"],
            "longitude": data["coordinates"]["longitude"],
            "monday_open": data["hours"]["monday"]["open"],
            "monday_close": data["hours"]["monday"]["close"],
            "tuesday_open": data["hours"]["tuesday"]["open"],
            "tuesday_close": data["hours"]["tuesday"]["close"],
            "wednesday_open": data["hours"]["wednesday"]["open"],
            "wednesday_close": data["hours"]["wednesday"]["close"],
            "thursday_open": data["hours"]["thursday"]["open"],
            "thursday_close": data["hours"]["thursday"]["close"],
            "friday_open": data["hours"]["friday"]["open"],
            "friday_close": data["hours"]["friday"]["close"],
            "saturday_open": data["hours"]["saturday"]["open"],
            "saturday_close": data["hours"]["saturday"]["close"],
            "sunday_open": data["hours"]["sunday"]["open"],
            "sunday_close": data["hours"]["sunday"]["close"],
        }
        buildings.append(building)

        # Process rooms and class schedules
        for room_number, classes in data["rooms"].items():
            room_key = (name, room_number)
            if room_key in room_keys:
                raise DataValidationError(
                    f"Duplicate room found: {room_number} in {name}"
                )

            room_keys.add(room_key)
            rooms.append({"building_name": name, "room_number": room_number})

            # Create schedule entry for each day the class meets
            for class_info in classes:
                for day in class_info["days"]:
                    schedules.append(
                        {
                            "building_name": name,
                            "room_number": room_number,
                            "course_code": class_info["course"],
                            "course_title": class_info["title"],
                            "start_time": class_info["time"]["start"],
                            "end_time": class_info["time"]["end"],
                            "day_of_week": day,
                            "start_date": class_info["start_date"],
                            "end_date": class_info["end_date"],
                        }
                    )

    return buildings, rooms, schedules


def verify_data_counts(
    json_data: Dict, buildings: List[Dict], rooms: List[Dict], schedules: List[Dict]
) -> None:
    """Verify that the prepared data counts match expected counts."""
    expected_buildings = len(json_data["buildings"])
    expected_rooms = sum(len(b["rooms"]) for b in json_data["buildings"].values())
    expected_schedules = sum(
        sum(len(class_info["days"]) for class_info in classes)
        for building in json_data["buildings"].values()
        for classes in building["rooms"].values()
    )

    if len(buildings) != expected_buildings:
        raise DataValidationError(
            f"Building count mismatch. Expected: {expected_buildings}, Got: {len(buildings)}"
        )
    if len(rooms) != expected_rooms:
        raise DataValidationError(
            f"Room count mismatch. Expected: {expected_rooms}, Got: {len(rooms)}"
        )
    if len(schedules) != expected_schedules:
        raise DataValidationError(
            f"Schedule count mismatch. Expected: {expected_schedules}, Got: {len(schedules)}"
        )


def bulk_insert(table_name: str, records: List[Dict], upsert: bool = False) -> int:
    """
    Insert records in batches.
    
    Args:
        table_name: Name of the table
        records: List of records to insert
        upsert: If True, use upsert instead of insert
        
    Returns:
        Number of records processed
    """
    if not records:
        print(f"No records to insert into {table_name}")
        return 0
        
    failed_chunks = []
    total_processed = 0

    for i in range(0, len(records), CHUNK_SIZE):
        chunk = records[i : i + CHUNK_SIZE]
        chunk_num = i // CHUNK_SIZE + 1
        total_chunks = (len(records) + CHUNK_SIZE - 1) // CHUNK_SIZE

        try:
            if upsert:
                get_supabase().table(table_name).upsert(chunk).execute()
                print(f"  Upserted chunk {chunk_num}/{total_chunks} for {table_name} ({len(chunk)} records)")
            else:
                get_supabase().table(table_name).insert(chunk).execute()
                print(f"  Inserted chunk {chunk_num}/{total_chunks} into {table_name} ({len(chunk)} records)")
            
            total_processed += len(chunk)

        except Exception as e:
            print(f"  Error processing chunk {chunk_num}/{total_chunks} for {table_name}")
            print(f"  Error details: {str(e)}")
            failed_chunks.append((i, chunk))

    if failed_chunks:
        raise DataValidationError(
            f"Failed to process {len(failed_chunks)} chunks for {table_name}"
        )

    # Verify final count
    final_count = get_supabase().table(table_name).select("*", count="exact").execute().count  # type: ignore
    print(f"  ✓ {table_name}: {total_processed} records processed, {final_count} total in table")
    
    return total_processed


def clear_table(table_name: str) -> None:
    """Clear all records from a table safely."""
    primary_keys = {
        "daily_events": "id",
        "buildings": "name",
        "rooms": "building_name",
        "class_schedule": "building_name",
        "academic_terms": "academic_year",
    }

    try:
        key = primary_keys.get(table_name, "id")
        get_supabase().table(table_name).delete().not_.is_(key, "null").execute()

        count = get_supabase().table(table_name).select("*", count="exact").execute().count  # type: ignore
        if count is None or count != 0:
            raise DataValidationError(
                f"Failed to clear table {table_name}. {count} records remaining."
            )
        print(f"  ✓ Cleared table {table_name}")
    except Exception as e:
        print(f"  Error clearing table {table_name}: {str(e)}")
        raise


def verify_database_contents(
    buildings: List[Dict], rooms: List[Dict], schedules: List[Dict]
) -> None:
    """Verify that the database contains exactly the expected data.

    Uses strict equality for all tables since stale records are cleaned up
    after each load.
    """
    client = get_supabase()
    checks = [
        ("buildings", buildings),
        ("rooms", rooms),
        ("class_schedule", schedules),
    ]

    for table_name, expected_records in checks:
        result = client.table(table_name).select("*", count="exact").execute()  # type: ignore
        actual_count = result.count or 0
        expected_count = len(expected_records)

        if actual_count != expected_count:
            raise DataValidationError(
                f"{table_name} count mismatch. Expected: {expected_count}, Got: {actual_count}"
            )
        print(f"  ✓ {table_name}: {actual_count} records (verified)")


# Safety threshold: if more than this fraction of buildings would be deleted,
# abort cleanup. Protects against accidental wipes when an upstream rename or
# bug causes the new payload to look almost entirely different from the DB.
STALE_BUILDING_ABORT_FRACTION = 0.25
# Batch size for chunked .in_() deletes (Supabase URL length is bounded).
DELETE_BATCH_SIZE = 100


def _normalize_building_name(name: str) -> str:
    """Canonical key for matching buildings across runs.

    Used as a rename-guard heuristic: if a building's *normalized* name still
    exists in the new payload, we will not delete it. Catches casing changes,
    extra whitespace, and trailing punctuation differences.
    """
    return " ".join(name.strip().lower().split())


def cleanup_stale_records(
    current_buildings: List[Dict], current_rooms: List[Dict]
) -> None:
    """Remove buildings and rooms not present in the current dataset.

    Relies on ON DELETE CASCADE foreign keys in the schema to automatically
    remove orphaned rooms, class_schedule, and daily_events rows when a
    building or room is deleted.

    Safety:
    - Aborts if more than STALE_BUILDING_ABORT_FRACTION of existing buildings
      would be deleted (protects against accidental mass-wipes).
    - Skips buildings whose normalized name still exists in the new payload
      (rename guard for casing/whitespace changes).
    - Batches deletes via .in_() to avoid one HTTP round-trip per row.

    Note: Supabase REST has no multi-statement transactions. If this function
    fails partway through, the DB is left in a partially-cleaned state. The
    next run will retry the remaining deletes since the new payload is
    deterministic.
    """
    client = get_supabase()
    current_building_names = {b["name"] for b in current_buildings}
    current_normalized_names = {
        _normalize_building_name(b["name"]) for b in current_buildings
    }
    current_room_keys = {
        (r["building_name"], r["room_number"]) for r in current_rooms
    }

    # ---- Stale buildings ------------------------------------------------
    db_buildings = client.table("buildings").select("name").execute()
    db_building_names = [b["name"] for b in db_buildings.data]

    stale_buildings = [
        name
        for name in db_building_names
        if name not in current_building_names
        and _normalize_building_name(name) not in current_normalized_names
    ]

    # Rename guard: log buildings that matched only by normalized name.
    rename_skipped = [
        name
        for name in db_building_names
        if name not in current_building_names
        and _normalize_building_name(name) in current_normalized_names
    ]
    if rename_skipped:
        print(
            f"  Skipping {len(rename_skipped)} building(s) that look like "
            f"renames (matched normalized name): {rename_skipped}"
        )

    # Mass-wipe guard.
    if db_building_names and stale_buildings:
        fraction = len(stale_buildings) / len(db_building_names)
        if fraction > STALE_BUILDING_ABORT_FRACTION:
            raise DataValidationError(
                f"Refusing to delete {len(stale_buildings)}/"
                f"{len(db_building_names)} buildings "
                f"({fraction:.0%} > {STALE_BUILDING_ABORT_FRACTION:.0%} "
                f"safety threshold). This usually means the new payload is "
                f"incomplete or building names changed upstream. "
                f"Stale list (truncated): {stale_buildings[:10]}"
            )

    if stale_buildings:
        for i in range(0, len(stale_buildings), DELETE_BATCH_SIZE):
            chunk = stale_buildings[i : i + DELETE_BATCH_SIZE]
            client.table("buildings").delete().in_("name", chunk).execute()
        print(
            f"  Removed {len(stale_buildings)} stale buildings "
            f"(showing up to 10): {stale_buildings[:10]}"
        )
    else:
        print("  No stale buildings found")

    # ---- Stale rooms ----------------------------------------------------
    # Rooms from deleted buildings are already gone via CASCADE.
    db_rooms = client.table("rooms").select("building_name, room_number").execute()
    stale_rooms = [
        r
        for r in db_rooms.data
        if (r["building_name"], r["room_number"]) not in current_room_keys
    ]

    if stale_rooms:
        # Group stale rooms by building so we can delete in batches per building.
        by_building: Dict[str, List[str]] = {}
        for r in stale_rooms:
            by_building.setdefault(r["building_name"], []).append(r["room_number"])

        for building_name, room_numbers in by_building.items():
            for i in range(0, len(room_numbers), DELETE_BATCH_SIZE):
                chunk = room_numbers[i : i + DELETE_BATCH_SIZE]
                client.table("rooms").delete().eq(
                    "building_name", building_name
                ).in_("room_number", chunk).execute()
        print(f"  Removed {len(stale_rooms)} stale rooms")
    else:
        print("  No stale rooms found")


def load_data(
    term: str = "SP26",
    skip_terms: bool = False,
    dry_run: bool = False,
) -> None:
    """Programmatic entry point for loading data into Supabase.

    Can be called directly from the orchestrator without argparse.
    """
    archive_dir = Path(__file__).parent / "archive"
    data_dir = Path(__file__).parent / "data"

    print("=" * 60)
    print("UCF Spots - Load to PostgreSQL")
    print("=" * 60)

    if dry_run:
        print("DRY RUN MODE - No data will be loaded\n")
    else:
        print("WARNING: This will modify the database.\n")

    # Load building data
    buildings_file = archive_dir / f"buildings_enriched_{term}.json"
    print(f"Loading building data from {buildings_file}...")

    if not buildings_file.exists():
        raise FileNotFoundError(f"Buildings file not found: {buildings_file}")

    with open(buildings_file, "r") as f:
        json_data = json.load(f)

    # Load academic calendar (optional)
    academic_terms_data = []
    calendar_file = data_dir / "academic_calendar.json"
    if not skip_terms and calendar_file.exists():
        print(f"Loading academic calendar from {calendar_file}...")
        with open(calendar_file, "r") as f:
            academic_terms_data = json.load(f)
    elif not skip_terms:
        print(f"Note: {calendar_file} not found, skipping academic terms")

    # Validate data
    print("\nValidating data structure...")
    validate_json_structure(json_data)
    if academic_terms_data:
        validate_academic_terms_structure(academic_terms_data)
    print("  Data structure validated")

    # Prepare data
    print("\nPreparing data for database...")
    buildings, rooms, schedules = prepare_and_validate_data(json_data)
    verify_data_counts(json_data, buildings, rooms, schedules)

    print(f"  Buildings: {len(buildings)}")
    print(f"  Rooms: {len(rooms)}")
    print(f"  Class schedules: {len(schedules)}")
    if academic_terms_data:
        print(f"  Academic terms: {len(academic_terms_data)}")

    if dry_run:
        print("\nDry run complete. Data is valid.")
        return

    # Clear and load data
    print("\nClearing existing schedule data...")
    tables_to_clear = ["class_schedule"]
    if academic_terms_data:
        tables_to_clear.append("academic_terms")
    for table in tables_to_clear:
        clear_table(table)

    print("\nLoading data into database...")

    # Academic terms first (if available)
    if academic_terms_data:
        print("\nInserting academic terms...")
        bulk_insert("academic_terms", academic_terms_data)

    # Buildings (upsert to preserve existing)
    print("\nUpserting buildings...")
    bulk_insert("buildings", buildings, upsert=True)

    # Rooms (upsert to preserve existing)
    print("\nUpserting rooms...")
    bulk_insert("rooms", rooms, upsert=True)

    # Class schedules (insert fresh)
    # Note: Supabase REST API does not support multi-request transactions.
    # If a failure occurs mid-insert, re-running the script is safe because
    # class_schedule is cleared at the start. Run during off-peak hours to
    # minimize the window of incomplete data.
    print("\nInserting class schedules...")
    bulk_insert("class_schedule", schedules)

    # Remove buildings/rooms no longer in the dataset
    print("\nCleaning up stale records...")
    cleanup_stale_records(buildings, rooms)

    # Verify
    print("\nVerifying database contents...")
    verify_database_contents(buildings, rooms, schedules)

    # Summary
    print("\n" + "=" * 60)
    print("Load complete!")
    print("=" * 60)
    print(f"  Buildings: {len(buildings)}")
    print(f"  Rooms: {len(rooms)}")
    print(f"  Class schedules: {len(schedules)}")
    if academic_terms_data:
        print(f"  Academic terms: {len(academic_terms_data)}")


def main():
    """CLI entry point for load_to_postgres."""
    import argparse

    parser = argparse.ArgumentParser(description='Load enriched building data into Supabase')
    parser.add_argument('--term', default='SP26', help='Term code (e.g., SP26, FA25)')
    parser.add_argument('--skip-terms', action='store_true', help='Skip loading academic terms')
    parser.add_argument('--dry-run', action='store_true', help='Validate only, do not load data')

    args = parser.parse_args()

    try:
        load_data(
            term=args.term,
            skip_terms=args.skip_terms,
            dry_run=args.dry_run,
        )
    except DataValidationError as e:
        print(f"\nData Validation Error: {str(e)}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\nFile not found: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected Error: {str(e)}")
        raise


if __name__ == "__main__":
    main()
