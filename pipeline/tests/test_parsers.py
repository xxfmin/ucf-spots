"""Tests for HTML parsing functions extracted from scraper.py."""

import pytest

from parsers import (
    TimeSlot,
    Location,
    parse_days,
    parse_time,
    parse_location,
    parse_dates,
    scrape_search_results,
)


class TestParseDays:
    def test_mo_we_fr(self):
        assert parse_days("MoWeFr 10:30AM") == ["M", "W", "F"]

    def test_tu_th(self):
        assert parse_days("TuTh 9:00AM") == ["T", "R"]

    def test_mo_we(self):
        assert parse_days("MoWe 10:30AM - 11:50AM") == ["M", "W"]

    def test_single_day_mo(self):
        assert parse_days("Mo 8:00AM") == ["M"]

    def test_all_weekdays(self):
        result = parse_days("MoTuWeThFr")
        assert result == ["M", "T", "W", "R", "F"]

    def test_saturday(self):
        assert parse_days("Sa 10:00AM") == ["S"]

    def test_sunday(self):
        assert parse_days("Su 10:00AM") == ["U"]

    def test_single_letter_fallback(self):
        assert parse_days("MTWRF") == ["M", "T", "W", "R", "F"]

    def test_empty_string(self):
        assert parse_days("") == []

    def test_tba(self):
        assert parse_days("TBA") == []

    def test_arr(self):
        assert parse_days("ARR") == []

    def test_no_duplicate_days(self):
        result = parse_days("MoMo")
        assert result == ["M"]


class TestParseTime:
    def test_standard_time(self):
        result = parse_time("10:30AM - 11:50AM")
        assert result == TimeSlot(start="10:30", end="11:50")

    def test_pm_time(self):
        result = parse_time("1:30PM - 2:20PM")
        assert result == TimeSlot(start="13:30", end="14:20")

    def test_morning_to_afternoon(self):
        result = parse_time("11:30AM - 12:45PM")
        assert result == TimeSlot(start="11:30", end="12:45")

    def test_noon(self):
        result = parse_time("12:00PM - 1:15PM")
        assert result == TimeSlot(start="12:00", end="13:15")

    def test_early_morning(self):
        result = parse_time("7:30AM - 8:50AM")
        assert result == TimeSlot(start="07:30", end="08:50")

    def test_evening(self):
        result = parse_time("6:00PM - 9:00PM")
        assert result == TimeSlot(start="18:00", end="21:00")

    def test_tba_returns_none(self):
        assert parse_time("TBA") is None

    def test_arr_returns_none(self):
        assert parse_time("ARR") is None

    def test_empty_returns_none(self):
        assert parse_time("") is None

    def test_none_returns_none(self):
        assert parse_time(None) is None

    def test_no_match_returns_none(self):
        assert parse_time("some random text") is None

    def test_time_with_day_prefix(self):
        result = parse_time("MoWe 10:30AM - 11:50AM")
        assert result == TimeSlot(start="10:30", end="11:50")


class TestParseLocation:
    def test_standard_location(self):
        result = parse_location("BA1 O107")
        assert result == Location(building="BA1", room="O107")

    def test_engineering_building(self):
        result = parse_location("ENG2 0302")
        assert result == Location(building="ENG2", room="0302")

    def test_tba_returns_none(self):
        assert parse_location("TBA") is None

    def test_web_returns_none(self):
        assert parse_location("WEB") is None

    def test_empty_returns_none(self):
        assert parse_location("") is None

    def test_none_returns_none(self):
        assert parse_location(None) is None

    def test_single_word_returns_none(self):
        assert parse_location("ONLINE") is None

    def test_whitespace_handling(self):
        result = parse_location("  BA1  O107  ")
        assert result == Location(building="BA1", room="O107")


class TestParseDates:
    def test_standard_date_range(self):
        result = parse_dates("01/12/2026 - 05/05/2026")
        assert result == ("2026-01-12", "2026-05-05")

    def test_summer_dates(self):
        result = parse_dates("05/18/2026 - 08/07/2026")
        assert result == ("2026-05-18", "2026-08-07")

    def test_empty_string(self):
        assert parse_dates("") == ("", "")

    def test_no_match(self):
        assert parse_dates("invalid date") == ("", "")

    def test_malformed_date(self):
        assert parse_dates("13/32/2026 - 05/05/2026") == ("", "")


class TestScrapeSearchResults:
    def test_parses_courses_from_html(self, sample_html):
        courses = scrape_search_results(sample_html)
        # ACG 3103 is TBA/WEB so it should be excluded (no valid location+time)
        # COP 3502 has 2 meeting entries (lecture + lab)
        assert len(courses) == 3

    def test_course_numbers(self, sample_html):
        courses = scrape_search_results(sample_html)
        numbers = [c.number for c in courses]
        assert "ACG 2021" in numbers
        assert "ACG 2071" in numbers
        assert "COP 3502" in numbers

    def test_course_titles(self, sample_html):
        courses = scrape_search_results(sample_html)
        titles = {c.number: c.title for c in courses}
        assert titles["ACG 2021"] == "Principles of Financial Accounting"
        assert titles["ACG 2071"] == "Managerial Accounting"

    def test_acg2021_has_two_sections(self, sample_html):
        courses = scrape_search_results(sample_html)
        acg2021 = next(c for c in courses if c.number == "ACG 2021")
        assert len(acg2021.sections) == 2

    def test_section_time_parsed(self, sample_html):
        courses = scrape_search_results(sample_html)
        acg2021 = next(c for c in courses if c.number == "ACG 2021")
        section = acg2021.sections[0]
        assert section.time == TimeSlot(start="10:30", end="11:50")

    def test_section_location_parsed(self, sample_html):
        courses = scrape_search_results(sample_html)
        acg2021 = next(c for c in courses if c.number == "ACG 2021")
        section = acg2021.sections[0]
        assert section.location == Location(building="BA1", room="O107")

    def test_section_days_parsed(self, sample_html):
        courses = scrape_search_results(sample_html)
        acg2021 = next(c for c in courses if c.number == "ACG 2021")
        assert acg2021.sections[0].days == ["M", "W"]
        assert acg2021.sections[1].days == ["T", "R"]

    def test_section_dates_parsed(self, sample_html):
        courses = scrape_search_results(sample_html)
        acg2021 = next(c for c in courses if c.number == "ACG 2021")
        assert acg2021.sections[0].start_date == "2026-01-12"
        assert acg2021.sections[0].end_date == "2026-05-05"

    def test_tba_web_courses_excluded(self, sample_html):
        courses = scrape_search_results(sample_html)
        numbers = [c.number for c in courses]
        # ACG 3103 has TBA time and WEB location, so no valid sections
        assert "ACG 3103" not in numbers

    def test_multi_meeting_course(self, sample_html):
        courses = scrape_search_results(sample_html)
        cop3502 = next(c for c in courses if c.number == "COP 3502")
        # Has lecture (MoWe) + lab (Fr) = 2 sections
        assert len(cop3502.sections) == 2
        assert cop3502.sections[0].days == ["M", "W"]
        assert cop3502.sections[1].days == ["F"]

    def test_empty_html(self):
        assert scrape_search_results("") == []

    def test_html_with_no_courses(self):
        html = "<html><body><div>No results</div></body></html>"
        assert scrape_search_results(html) == []

    def test_malformed_section_row_skipped(self):
        """A section row that raises an exception should be skipped, not crash."""
        html = """
        <div id="win0divSSR_CLSRSLT_WRK_GROUPBOX2$0">
          <a title="Collapse section TST 1000 - Test Course">link</a>
          <tr id="trSSR_CLSRCH_MTG1$0_row1">
            <td><span id="MTG_DAYTIME$0">MoWe 10:30AM - 11:50AM</span></td>
            <td><span id="MTG_ROOM$0">BA1 O107</span></td>
            <td><span id="MTG_TOPIC$0">01/12/2026 - 05/05/2026</span></td>
          </tr>
          <tr id="trSSR_CLSRCH_MTG1$0_row2">
            <!-- row with no spans at all - edge case -->
          </tr>
        </div>
        """
        courses = scrape_search_results(html)
        assert len(courses) == 1
        assert courses[0].number == "TST 1000"
        assert len(courses[0].sections) == 1

    def test_course_without_groupbox_parent_skipped(self):
        """A course header not inside a groupbox div should be skipped."""
        html = """
        <div id="some_other_div">
          <a title="Collapse section TST 2000 - Orphan Course">link</a>
          <tr id="trSSR_CLSRCH_MTG1$0_row1">
            <td><span id="MTG_DAYTIME$0">MoWe 10:30AM - 11:50AM</span></td>
            <td><span id="MTG_ROOM$0">BA1 O107</span></td>
            <td><span id="MTG_TOPIC$0">01/12/2026 - 05/05/2026</span></td>
          </tr>
        </div>
        """
        courses = scrape_search_results(html)
        assert len(courses) == 0

    def test_non_string_title_attribute_skipped(self):
        """A title attribute that is not a string should be skipped."""
        html = """
        <div id="win0divSSR_CLSRSLT_WRK_GROUPBOX2$0">
          <a title="Collapse section TST 3000" id="test">link</a>
        </div>
        """
        # Title matches the regex but doesn't have " - CourseTitle" part
        courses = scrape_search_results(html)
        assert len(courses) == 0

    def test_section_row_exception_logged_and_skipped(self):
        """A section row that triggers an exception in parsing is skipped gracefully."""
        # Create HTML where MTG_DAYTIME has content but room span triggers
        # an edge case. We force an exception by making the span's get_text
        # return something that causes max() to be called with 0 entries,
        # but since max of empty lists would fail... let's use a mock approach
        from unittest.mock import patch

        html = """
        <div id="win0divSSR_CLSRSLT_WRK_GROUPBOX2$0">
          <a title="Collapse section TST 4000 - Exception Course">link</a>
          <tr id="trSSR_CLSRCH_MTG1$0_row1">
            <td><span id="MTG_DAYTIME$0">MoWe 10:30AM - 11:50AM</span></td>
            <td><span id="MTG_ROOM$0">BA1 O107</span></td>
            <td><span id="MTG_TOPIC$0">01/12/2026 - 05/05/2026</span></td>
          </tr>
        </div>
        """
        # Patch parse_time to throw on first call to trigger the except branch
        original_parse_time = parse_time
        call_count = [0]

        def exploding_parse_time(time_str):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("forced error")
            return original_parse_time(time_str)

        with patch("parsers.parse_time", side_effect=exploding_parse_time):
            courses = scrape_search_results(html)
        # Course has no valid sections after the error, so it's excluded
        assert len(courses) == 0


class TestParseTimeEdgeCases:
    def test_regex_match_but_strptime_fails(self):
        """Time that matches regex pattern but has invalid hour value."""
        # 99:99AM matches the regex r'(\d{1,2}:\d{2}[AP]M)' but strptime fails
        result = parse_time("99:99AM - 11:50AM")
        assert result is None

    def test_none_input(self):
        result = parse_time(None)
        assert result is None


class TestParseDatesEdgeCases:
    def test_none_input(self):
        result = parse_dates(None)
        assert result == ("", "")
