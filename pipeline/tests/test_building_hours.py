"""Tests for building hours parsing and time format conversion."""

import pytest

from add_building_hours import BuildingHoursProcessor


@pytest.fixture
def processor():
    return BuildingHoursProcessor()


class TestConvertTimeFormat:
    def test_standard_am(self, processor):
        assert processor.convert_time_format("7:30AM") == "07:30"

    def test_standard_pm(self, processor):
        assert processor.convert_time_format("10:00PM") == "22:00"

    def test_noon(self, processor):
        assert processor.convert_time_format("12:00PM") == "12:00"

    def test_12am_midnight(self, processor):
        # 12AM is treated as midnight close (23:59)
        assert processor.convert_time_format("12AM") == "23:59"

    def test_12_00am_midnight(self, processor):
        assert processor.convert_time_format("12:00AM") == "23:59"

    def test_no_colon_am(self, processor):
        assert processor.convert_time_format("7AM") == "07:00"

    def test_no_colon_pm(self, processor):
        assert processor.convert_time_format("6PM") == "18:00"

    def test_locked_returns_none(self, processor):
        assert processor.convert_time_format("LOCKED") is None

    def test_whitespace_stripped(self, processor):
        assert processor.convert_time_format("  7:30AM  ") == "07:30"

    def test_invalid_format_raises(self, processor):
        with pytest.raises(ValueError):
            processor.convert_time_format("invalid")

    def test_1am(self, processor):
        assert processor.convert_time_format("1AM") == "01:00"

    def test_11pm(self, processor):
        assert processor.convert_time_format("11:00PM") == "23:00"


class TestParseBuildingHours:
    def test_standard_hours(self, processor):
        hours = {
            "M-TH": "7:30AM-10:00PM",
            "F": "7:30AM-6:00PM",
            "SAT": "LOCKED",
            "SUN": "LOCKED",
        }
        result = processor.parse_building_hours(hours)

        assert result["monday"] == {"open": "07:30", "close": "22:00"}
        assert result["tuesday"] == {"open": "07:30", "close": "22:00"}
        assert result["wednesday"] == {"open": "07:30", "close": "22:00"}
        assert result["thursday"] == {"open": "07:30", "close": "22:00"}
        assert result["friday"] == {"open": "07:30", "close": "18:00"}
        assert result["saturday"] == {"open": None, "close": None}
        assert result["sunday"] == {"open": None, "close": None}

    def test_24_hours(self, processor):
        hours = {
            "M-TH": "24 HOURS",
            "F": "24 HOURS",
            "SAT": "11:00AM-10:00PM",
            "SUN": "11:00AM-24 HOURS",
        }
        result = processor.parse_building_hours(hours)

        assert result["monday"] == {"open": "00:00", "close": "23:59"}
        assert result["friday"] == {"open": "00:00", "close": "23:59"}
        assert result["saturday"] == {"open": "11:00", "close": "22:00"}
        assert result["sunday"] == {"open": "11:00", "close": "23:59"}

    def test_all_locked(self, processor):
        hours = {
            "M-TH": "LOCKED",
            "F": "LOCKED",
            "SAT": "LOCKED",
            "SUN": "LOCKED",
        }
        result = processor.parse_building_hours(hours)
        for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            assert result[day] == {"open": None, "close": None}

    def test_all_seven_days_present(self, processor):
        hours = {
            "M-TH": "8:00AM-5:00PM",
            "F": "8:00AM-5:00PM",
            "SAT": "LOCKED",
            "SUN": "LOCKED",
        }
        result = processor.parse_building_hours(hours)
        expected_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
        assert set(result.keys()) == expected_days

    def test_unknown_day_group_skipped(self, processor):
        hours = {
            "M-TH": "8:00AM-5:00PM",
            "F": "8:00AM-5:00PM",
            "SAT": "LOCKED",
            "SUN": "LOCKED",
            "HOLIDAY": "LOCKED",
        }
        result = processor.parse_building_hours(hours)
        # Should still have 7 days, unknown group ignored
        assert len(result) == 7

    def test_m_th_expands_to_four_days(self, processor):
        hours = {
            "M-TH": "9:00AM-5:00PM",
            "F": "LOCKED",
            "SAT": "LOCKED",
            "SUN": "LOCKED",
        }
        result = processor.parse_building_hours(hours)
        for day in ["monday", "tuesday", "wednesday", "thursday"]:
            assert result[day] == {"open": "09:00", "close": "17:00"}
