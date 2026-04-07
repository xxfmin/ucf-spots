"""Tests for subject-to-buildings transformation."""

import pytest

from subject_to_buildings import SubjectToBuildingsProcessor


@pytest.fixture
def processor():
    return SubjectToBuildingsProcessor()


class TestProcessToBuildings:
    def test_groups_by_building(self, processor, sample_courses):
        result = processor.process_to_buildings(sample_courses)
        buildings = result["buildings"]
        # sample_courses has sections in BA1, ENG1, ENG2, PSY
        assert "BA1" in buildings
        assert "ENG1" in buildings
        assert "ENG2" in buildings
        assert "PSY" in buildings

    def test_building_count(self, processor, sample_courses):
        result = processor.process_to_buildings(sample_courses)
        assert len(result["buildings"]) == 4

    def test_rooms_assigned_correctly(self, processor, sample_courses):
        result = processor.process_to_buildings(sample_courses)
        ba1_rooms = result["buildings"]["BA1"]["rooms"]
        # BA1 has O107 (2 sections from ACG 2021) and O209 (1 section from ACG 2071)
        assert "O107" in ba1_rooms
        assert "O209" in ba1_rooms
        assert len(ba1_rooms["O107"]) == 2
        assert len(ba1_rooms["O209"]) == 1

    def test_section_count(self, processor, sample_courses):
        result = processor.process_to_buildings(sample_courses)
        # BA1: O107 has 2 sections, O209 has 1 = 3 total
        assert result["buildings"]["BA1"]["total_sections"] == 3

    def test_section_info_fields(self, processor, sample_courses):
        result = processor.process_to_buildings(sample_courses)
        section = result["buildings"]["BA1"]["rooms"]["O107"][0]
        assert "course" in section
        assert "title" in section
        assert "time" in section
        assert "days" in section
        assert "start_date" in section
        assert "end_date" in section

    def test_preserves_term(self, processor, sample_courses):
        result = processor.process_to_buildings(sample_courses)
        assert result["term"] == "Spring 2026"

    def test_has_last_updated(self, processor, sample_courses):
        result = processor.process_to_buildings(sample_courses)
        assert "last_updated" in result

    def test_empty_subjects(self, processor):
        data = {"subjects": [], "term": "Spring 2026"}
        result = processor.process_to_buildings(data)
        assert result["buildings"] == {}

    def test_section_without_location_skipped(self, processor):
        data = {
            "term": "Spring 2026",
            "subjects": [
                {
                    "code": "TST",
                    "courses": [
                        {
                            "number": "TST 1000",
                            "title": "Test Course",
                            "sections": [
                                {
                                    "time": {"start": "10:00", "end": "11:00"},
                                    "location": None,
                                    "days": ["M"],
                                    "start_date": "2026-01-12",
                                    "end_date": "2026-05-05",
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        result = processor.process_to_buildings(data)
        assert result["buildings"] == {}


class TestGetStats:
    def test_stats_counts(self, processor, sample_courses):
        building_data = processor.process_to_buildings(sample_courses)
        stats = processor.get_stats(building_data)
        assert stats["total_buildings"] == 4
        assert stats["total_rooms"] > 0
        assert stats["total_sections"] > 0

    def test_top_buildings_sorted(self, processor, sample_courses):
        building_data = processor.process_to_buildings(sample_courses)
        stats = processor.get_stats(building_data)
        top = stats["top_buildings"]
        # Should be sorted by room count descending
        for i in range(len(top) - 1):
            assert top[i][1] >= top[i + 1][1]
