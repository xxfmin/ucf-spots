"""Tests for building coordinate enrichment."""

import pytest

from add_building_coordinates import BuildingCoordinateProcessor


@pytest.fixture
def processor():
    return BuildingCoordinateProcessor()


class TestCreateCoordinatesMap:
    def test_parses_geojson(self, processor, sample_geojson):
        result = processor.create_coordinates_map(sample_geojson)
        assert "BA1" in result
        assert "ENG1" in result
        assert len(result) == 4

    def test_coordinate_values(self, processor, sample_geojson):
        result = processor.create_coordinates_map(sample_geojson)
        coords = result["BA1"]
        assert coords[0] == pytest.approx(-81.19912, abs=0.001)
        assert coords[1] == pytest.approx(28.60105, abs=0.001)

    def test_empty_geojson(self, processor):
        result = processor.create_coordinates_map({"features": []})
        assert result == {}

    def test_missing_name_skipped(self, processor):
        geojson = {
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {"coordinates": [-81.0, 28.0], "type": "Point"},
                }
            ]
        }
        result = processor.create_coordinates_map(geojson)
        assert result == {}

    def test_insufficient_coordinates_skipped(self, processor):
        geojson = {
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "BA1"},
                    "geometry": {"coordinates": [-81.0], "type": "Point"},
                }
            ]
        }
        result = processor.create_coordinates_map(geojson)
        assert result == {}


class TestAddCoordinatesToBuildings:
    def test_adds_coordinates(self, processor, sample_geojson):
        coords_map = processor.create_coordinates_map(sample_geojson)
        building_data = {
            "buildings": {
                "BA1": {"rooms": {}},
                "ENG1": {"rooms": {}},
            }
        }
        result, count = processor.add_coordinates_to_buildings(building_data, coords_map)
        assert count == 2
        assert "coordinates" in result["buildings"]["BA1"]
        assert result["buildings"]["BA1"]["coordinates"]["longitude"] == pytest.approx(-81.19912, abs=0.001)
        assert result["buildings"]["BA1"]["coordinates"]["latitude"] == pytest.approx(28.60105, abs=0.001)

    def test_missing_coordinates_not_added(self, processor):
        coords_map = {"BA1": [-81.0, 28.0]}
        building_data = {
            "buildings": {
                "BA1": {"rooms": {}},
                "UNKNOWN": {"rooms": {}},
            }
        }
        result, count = processor.add_coordinates_to_buildings(building_data, coords_map)
        assert count == 1
        assert "coordinates" in result["buildings"]["BA1"]
        assert "coordinates" not in result["buildings"]["UNKNOWN"]

    def test_empty_buildings(self, processor):
        result, count = processor.add_coordinates_to_buildings({"buildings": {}}, {})
        assert count == 0
