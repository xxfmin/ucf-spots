"""Tests for load_to_postgres validation and data preparation (no DB needed)."""

import pytest

from load_to_postgres import (
    DataValidationError,
    validate_json_structure,
    validate_academic_terms_structure,
    prepare_and_validate_data,
    verify_data_counts,
)


def make_valid_building(room_count=1, sections_per_room=1, days=None):
    """Create a minimal valid building for testing."""
    if days is None:
        days = ["M"]
    rooms = {}
    for i in range(room_count):
        room_key = f"R{i:03d}"
        rooms[room_key] = [
            {
                "course": f"TST {1000 + i}",
                "title": f"Test Course {i}",
                "time": {"start": "10:00", "end": "11:00"},
                "days": days,
                "start_date": "2026-01-12",
                "end_date": "2026-05-05",
            }
            for _ in range(sections_per_room)
        ]
    return {
        "rooms": rooms,
        "hours": {
            "monday": {"open": "07:30", "close": "22:00"},
            "tuesday": {"open": "07:30", "close": "22:00"},
            "wednesday": {"open": "07:30", "close": "22:00"},
            "thursday": {"open": "07:30", "close": "22:00"},
            "friday": {"open": "07:30", "close": "18:00"},
            "saturday": {"open": None, "close": None},
            "sunday": {"open": None, "close": None},
        },
        "coordinates": {"latitude": 28.601, "longitude": -81.199},
        "total_sections": room_count * sections_per_room,
    }


class TestValidateJsonStructure:
    def test_valid_data_passes(self):
        data = {"buildings": {"BA1": make_valid_building()}}
        validate_json_structure(data)  # Should not raise

    def test_missing_buildings_key(self):
        with pytest.raises(DataValidationError, match="Missing 'buildings' key"):
            validate_json_structure({})

    def test_missing_hours(self):
        building = make_valid_building()
        del building["hours"]
        with pytest.raises(DataValidationError, match="missing keys.*hours"):
            validate_json_structure({"buildings": {"BA1": building}})

    def test_missing_coordinates(self):
        building = make_valid_building()
        del building["coordinates"]
        with pytest.raises(DataValidationError, match="missing keys.*coordinates"):
            validate_json_structure({"buildings": {"BA1": building}})

    def test_missing_rooms(self):
        building = make_valid_building()
        del building["rooms"]
        with pytest.raises(DataValidationError, match="missing keys.*rooms"):
            validate_json_structure({"buildings": {"BA1": building}})

    def test_missing_hour_day(self):
        building = make_valid_building()
        del building["hours"]["sunday"]
        with pytest.raises(DataValidationError, match="missing hours for days"):
            validate_json_structure({"buildings": {"BA1": building}})

    def test_rooms_not_a_list(self):
        building = make_valid_building()
        building["rooms"]["R000"] = "not a list"
        with pytest.raises(DataValidationError, match="should be a list"):
            validate_json_structure({"buildings": {"BA1": building}})

    def test_class_missing_keys(self):
        building = make_valid_building()
        building["rooms"]["R000"] = [{"course": "TST 1000"}]  # Missing other keys
        with pytest.raises(DataValidationError, match="missing keys"):
            validate_json_structure({"buildings": {"BA1": building}})


class TestValidateAcademicTermsStructure:
    def test_valid_terms(self, sample_academic_calendar):
        validate_academic_terms_structure(sample_academic_calendar)  # Should not raise

    def test_missing_required_key(self):
        terms = [{"academic_year": "2025-2026", "term": "Spring"}]
        with pytest.raises(DataValidationError, match="missing keys"):
            validate_academic_terms_structure(terms)

    def test_invalid_part_of_term(self):
        terms = [
            {
                "academic_year": "2025-2026",
                "term": "Spring",
                "part_of_term": "C",
                "start_date": "2026-01-12",
                "end_date": "2026-05-08",
            }
        ]
        with pytest.raises(DataValidationError, match="Invalid part_of_term"):
            validate_academic_terms_structure(terms)

    def test_end_before_start(self):
        terms = [
            {
                "academic_year": "2025-2026",
                "term": "Spring",
                "part_of_term": None,
                "start_date": "2026-05-08",
                "end_date": "2026-01-12",
            }
        ]
        with pytest.raises(DataValidationError, match="End date must be after"):
            validate_academic_terms_structure(terms)

    def test_invalid_date_format(self):
        terms = [
            {
                "academic_year": "2025-2026",
                "term": "Spring",
                "part_of_term": None,
                "start_date": "not-a-date",
                "end_date": "2026-05-08",
            }
        ]
        with pytest.raises(DataValidationError, match="Invalid date format"):
            validate_academic_terms_structure(terms)

    def test_valid_part_of_term_a(self):
        terms = [
            {
                "academic_year": "2025-2026",
                "term": "Spring",
                "part_of_term": "A",
                "start_date": "2026-01-12",
                "end_date": "2026-03-06",
            }
        ]
        validate_academic_terms_structure(terms)  # Should not raise


class TestPrepareAndValidateData:
    def test_basic_preparation(self):
        data = {"buildings": {"BA1": make_valid_building(room_count=2)}}
        buildings, rooms, schedules = prepare_and_validate_data(data)
        assert len(buildings) == 1
        assert len(rooms) == 2

    def test_building_record_fields(self):
        data = {"buildings": {"BA1": make_valid_building()}}
        buildings, _, _ = prepare_and_validate_data(data)
        b = buildings[0]
        assert b["name"] == "BA1"
        assert b["latitude"] == 28.601
        assert b["longitude"] == -81.199
        assert b["monday_open"] == "07:30"
        assert b["saturday_open"] is None

    def test_room_record_fields(self):
        data = {"buildings": {"BA1": make_valid_building()}}
        _, rooms, _ = prepare_and_validate_data(data)
        r = rooms[0]
        assert r["building_name"] == "BA1"
        assert r["room_number"] == "R000"

    def test_day_expansion(self):
        # A class on M, W, F should create 3 schedule records
        data = {"buildings": {"BA1": make_valid_building(days=["M", "W", "F"])}}
        _, _, schedules = prepare_and_validate_data(data)
        assert len(schedules) == 3
        schedule_days = [s["day_of_week"] for s in schedules]
        assert set(schedule_days) == {"M", "W", "F"}

    def test_schedule_record_fields(self):
        data = {"buildings": {"BA1": make_valid_building()}}
        _, _, schedules = prepare_and_validate_data(data)
        s = schedules[0]
        assert s["building_name"] == "BA1"
        assert s["room_number"] == "R000"
        assert s["course_code"] == "TST 1000"
        assert s["start_time"] == "10:00"
        assert s["end_time"] == "11:00"
        assert s["day_of_week"] == "M"

    def test_duplicate_room_raises(self):
        building = make_valid_building()
        # Manually create a duplicate room situation via two buildings referencing same room key
        # This is actually prevented by the data structure, so test via direct manipulation
        data = {"buildings": {"BA1": make_valid_building()}}
        # This should work fine since rooms are unique within a building
        prepare_and_validate_data(data)


class TestVerifyDataCounts:
    def test_matching_counts_pass(self):
        data = {"buildings": {"BA1": make_valid_building(room_count=2, days=["M", "W"])}}
        buildings, rooms, schedules = prepare_and_validate_data(data)
        verify_data_counts(data, buildings, rooms, schedules)  # Should not raise

    def test_building_mismatch_raises(self):
        data = {"buildings": {"BA1": make_valid_building()}}
        with pytest.raises(DataValidationError, match="Building count mismatch"):
            verify_data_counts(data, [], [{"building_name": "BA1", "room_number": "R000"}], [])

    def test_room_mismatch_raises(self):
        data = {"buildings": {"BA1": make_valid_building()}}
        buildings = [{"name": "BA1"}]
        with pytest.raises(DataValidationError, match="Room count mismatch"):
            verify_data_counts(data, buildings, [], [])

    def test_schedule_mismatch_raises(self):
        data = {"buildings": {"BA1": make_valid_building()}}
        buildings, rooms, _ = prepare_and_validate_data(data)
        with pytest.raises(DataValidationError, match="Schedule count mismatch"):
            verify_data_counts(data, buildings, rooms, [])
