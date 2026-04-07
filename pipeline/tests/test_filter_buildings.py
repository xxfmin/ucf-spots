"""Tests for building filtering logic."""

import pytest

from filter_buildings import BuildingDataFilter


@pytest.fixture
def filt():
    return BuildingDataFilter()


def make_building(room_count):
    """Helper to create a building with N rooms."""
    return {
        "rooms": {f"R{i:03d}": [] for i in range(room_count)},
        "total_sections": room_count,
    }


class TestFilterBuildings:
    def test_keeps_buildings_with_enough_rooms(self, filt):
        data = {
            "buildings": {
                "BIG": make_building(10),
                "SMALL": make_building(2),
            }
        }
        result = filt.filter_buildings(data)
        assert "BIG" in result["buildings"]
        assert "SMALL" not in result["buildings"]

    def test_exactly_min_rooms_kept(self, filt):
        data = {"buildings": {"EXACT": make_building(4)}}
        result = filt.filter_buildings(data)
        assert "EXACT" in result["buildings"]

    def test_below_min_rooms_removed(self, filt):
        data = {"buildings": {"TINY": make_building(3)}}
        result = filt.filter_buildings(data)
        assert "TINY" not in result["buildings"]

    def test_excluded_building_removed(self, filt):
        data = {"buildings": {"DPAC": make_building(20)}}
        result = filt.filter_buildings(data)
        assert "DPAC" not in result["buildings"]

    def test_all_excluded_buildings(self, filt):
        data = {
            "buildings": {
                code: make_building(50)
                for code in ["DPAC", "RSH", "CROL", "PAC"]
            }
        }
        result = filt.filter_buildings(data)
        assert len(result["buildings"]) == 0

    def test_preserves_metadata(self, filt):
        data = {
            "last_updated": "2026-01-15",
            "term": "Spring 2026",
            "buildings": {"BA1": make_building(10)},
        }
        result = filt.filter_buildings(data)
        assert result["last_updated"] == "2026-01-15"
        assert result["term"] == "Spring 2026"

    def test_empty_input(self, filt):
        data = {"buildings": {}}
        result = filt.filter_buildings(data)
        assert result["buildings"] == {}

    def test_preserves_building_data(self, filt):
        building = make_building(5)
        data = {"buildings": {"BA1": building}}
        result = filt.filter_buildings(data)
        assert result["buildings"]["BA1"] == building

    def test_mixed_filtering(self, filt):
        data = {
            "buildings": {
                "BA1": make_building(10),   # keep: enough rooms
                "TINY": make_building(2),   # remove: too few rooms
                "DPAC": make_building(20),  # remove: excluded
                "ENG1": make_building(5),   # keep: enough rooms
            }
        }
        result = filt.filter_buildings(data)
        assert set(result["buildings"].keys()) == {"BA1", "ENG1"}
