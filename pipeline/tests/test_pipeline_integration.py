"""Integration test: chain pipeline steps 2-5 with fixture data."""

import json

import pytest

from subject_to_buildings import SubjectToBuildingsProcessor
from filter_buildings import BuildingDataFilter
from add_building_hours import BuildingHoursProcessor
from add_building_coordinates import BuildingCoordinateProcessor
from load_to_postgres import (
    validate_json_structure,
    prepare_and_validate_data,
    verify_data_counts,
)


class TestPipelineIntegration:
    """Chain steps 2-5 and validate the output is database-ready."""

    def test_full_pipeline_produces_valid_output(
        self, sample_courses, sample_building_hours, sample_geojson
    ):
        # Step 2: subject_to_buildings
        s2b = SubjectToBuildingsProcessor()
        derived = s2b.process_to_buildings(sample_courses)
        assert len(derived["buildings"]) > 0

        # Step 3: filter_buildings
        filt = BuildingDataFilter()
        filtered = filt.filter_buildings(derived)
        # With min_rooms=4, only buildings with 4+ rooms survive.
        # From sample data: PSY has 2 rooms, BA1 has 2, ENG1 has 2, ENG2 has 1
        # None have 4+, so we lower the threshold for this test
        filt.min_rooms = 1
        filtered = filt.filter_buildings(derived)
        assert len(filtered["buildings"]) > 0

        # Step 4: add_building_hours
        hours_proc = BuildingHoursProcessor()
        for building_code in filtered.get("buildings", {}):
            if building_code in sample_building_hours:
                filtered["buildings"][building_code]["hours"] = (
                    hours_proc.parse_building_hours(sample_building_hours[building_code])
                )

        # Verify all buildings got hours
        for code, bdata in filtered["buildings"].items():
            assert "hours" in bdata, f"Building {code} missing hours"

        # Step 5: add_building_coordinates
        coord_proc = BuildingCoordinateProcessor()
        coords_map = coord_proc.create_coordinates_map(sample_geojson)
        enriched, _ = coord_proc.add_coordinates_to_buildings(filtered, coords_map)

        # Verify all buildings got coordinates
        for code, bdata in enriched["buildings"].items():
            assert "coordinates" in bdata, f"Building {code} missing coordinates"

        # Validate the output is ready for database loading
        validate_json_structure(enriched)
        buildings, rooms, schedules = prepare_and_validate_data(enriched)
        verify_data_counts(enriched, buildings, rooms, schedules)

        # Sanity checks on final data
        assert len(buildings) > 0
        assert len(rooms) > 0
        assert len(schedules) > 0

    def test_pipeline_with_file_io(
        self, tmp_path, sample_courses, sample_building_hours, sample_geojson
    ):
        """Test pipeline using actual file I/O via tmp_path."""
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()

        # Write input
        courses_file = archive_dir / "courses_TEST.json"
        with open(courses_file, "w") as f:
            json.dump(sample_courses, f)

        # Step 2: read and transform
        with open(courses_file) as f:
            course_data = json.load(f)
        s2b = SubjectToBuildingsProcessor()
        derived = s2b.process_to_buildings(course_data)

        derived_file = archive_dir / "buildings_derived_TEST.json"
        with open(derived_file, "w") as f:
            json.dump(derived, f)

        # Step 3: filter (lowered threshold for test data)
        filt = BuildingDataFilter()
        filt.min_rooms = 1
        with open(derived_file) as f:
            derived_data = json.load(f)
        filtered = filt.filter_buildings(derived_data)

        filtered_file = archive_dir / "buildings_filtered_TEST.json"
        with open(filtered_file, "w") as f:
            json.dump(filtered, f)

        # Step 4: hours
        with open(filtered_file) as f:
            filtered_data = json.load(f)
        hours_proc = BuildingHoursProcessor()
        for code in filtered_data.get("buildings", {}):
            if code in sample_building_hours:
                filtered_data["buildings"][code]["hours"] = (
                    hours_proc.parse_building_hours(sample_building_hours[code])
                )
        with open(filtered_file, "w") as f:
            json.dump(filtered_data, f)

        # Step 5: coordinates
        with open(filtered_file) as f:
            data = json.load(f)
        coord_proc = BuildingCoordinateProcessor()
        coords_map = coord_proc.create_coordinates_map(sample_geojson)
        enriched, _ = coord_proc.add_coordinates_to_buildings(data, coords_map)

        enriched_file = archive_dir / "buildings_enriched_TEST.json"
        with open(enriched_file, "w") as f:
            json.dump(enriched, f)

        # Final validation
        with open(enriched_file) as f:
            final_data = json.load(f)
        validate_json_structure(final_data)

    def test_schedule_day_expansion_correct(self, sample_courses):
        """Verify that multi-day classes expand to correct number of schedule rows."""
        s2b = SubjectToBuildingsProcessor()
        derived = s2b.process_to_buildings(sample_courses)

        filt = BuildingDataFilter()
        filt.min_rooms = 1
        filtered = filt.filter_buildings(derived)

        # Count total days across all sections in input
        expected_schedule_rows = 0
        for building in filtered["buildings"].values():
            for room_classes in building["rooms"].values():
                for cls in room_classes:
                    expected_schedule_rows += len(cls["days"])

        # Add minimal hours and coordinates for validation
        hours_proc = BuildingHoursProcessor()
        coord_proc = BuildingCoordinateProcessor()

        for code in filtered["buildings"]:
            filtered["buildings"][code]["hours"] = hours_proc.parse_building_hours({
                "M-TH": "7:30AM-10:00PM",
                "F": "7:30AM-6:00PM",
                "SAT": "LOCKED",
                "SUN": "LOCKED",
            })
            filtered["buildings"][code]["coordinates"] = {
                "latitude": 28.0,
                "longitude": -81.0,
            }

        _, _, schedules = prepare_and_validate_data(filtered)
        assert len(schedules) == expected_schedule_rows
