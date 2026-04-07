"""Shared pytest fixtures for pipeline tests."""

import json
from pathlib import Path

import pytest

from subject_to_buildings import SubjectToBuildingsProcessor
from filter_buildings import BuildingDataFilter
from add_building_hours import BuildingHoursProcessor
from add_building_coordinates import BuildingCoordinateProcessor

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def sample_html():
    return (FIXTURES_DIR / "sample_search_results.html").read_text()


@pytest.fixture
def sample_courses():
    with open(FIXTURES_DIR / "sample_courses.json") as f:
        return json.load(f)


@pytest.fixture
def sample_building_hours():
    with open(FIXTURES_DIR / "sample_building_hours.json") as f:
        return json.load(f)


@pytest.fixture
def sample_geojson():
    with open(FIXTURES_DIR / "sample_geojson.json") as f:
        return json.load(f)


@pytest.fixture
def sample_academic_calendar():
    with open(FIXTURES_DIR / "sample_academic_calendar.json") as f:
        return json.load(f)


@pytest.fixture
def sample_buildings_derived(sample_courses):
    """Generate derived buildings data from sample courses."""
    processor = SubjectToBuildingsProcessor()
    return processor.process_to_buildings(sample_courses)


@pytest.fixture
def sample_buildings_filtered(sample_buildings_derived):
    """Generate filtered buildings data."""
    filt = BuildingDataFilter()
    return filt.filter_buildings(sample_buildings_derived)


@pytest.fixture
def sample_buildings_with_hours(sample_buildings_filtered, sample_building_hours):
    """Add hours to filtered buildings."""
    processor = BuildingHoursProcessor()
    for building_code in sample_buildings_filtered.get("buildings", {}):
        if building_code in sample_building_hours:
            sample_buildings_filtered["buildings"][building_code]["hours"] = (
                processor.parse_building_hours(sample_building_hours[building_code])
            )
    return sample_buildings_filtered


@pytest.fixture
def sample_buildings_enriched(sample_buildings_with_hours, sample_geojson):
    """Add coordinates to buildings with hours."""
    processor = BuildingCoordinateProcessor()
    coords_map = processor.create_coordinates_map(sample_geojson)
    enriched, _ = processor.add_coordinates_to_buildings(sample_buildings_with_hours, coords_map)
    return enriched
