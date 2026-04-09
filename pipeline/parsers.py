"""
Pure parsing functions and dataclasses for UCF PeopleSoft HTML scraping.

Extracted from scraper.py so they can be tested without Selenium.
"""

from dataclasses import dataclass, field
from datetime import datetime
import logging
import re
from typing import List, Optional

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class TimeSlot:
    start: str  # "09:30"
    end: str    # "10:50"


@dataclass
class Location:
    building: str  # "BA1"
    room: str      # "O107"


@dataclass
class Section:
    time: Optional[TimeSlot]
    location: Optional[Location]
    days: List[str]    # ["M", "W", "R"]
    start_date: str    # "2026-01-12"
    end_date: str      # "2026-05-05"


@dataclass
class Course:
    number: str                    # "ACG 2021"
    title: Optional[str] = None    # "Principles of Financial Accounting"
    sections: List[Section] = field(default_factory=list)


@dataclass
class Subject:
    code: str  # "ACG"
    courses: List[Course] = field(default_factory=list)


def parse_days(day_str: str) -> List[str]:
    """Parse day string like 'TuTh 10:30AM' into list of day codes."""
    if not day_str or 'TBA' in day_str or 'ARR' in day_str:
        return []
    day_mapping = {
        'Mo': 'M',
        'Tu': 'T',
        'We': 'W',
        'Th': 'R',
        'Fr': 'F',
        'Sa': 'S',
        'Su': 'U'
    }
    days = []
    for abbrev, code in day_mapping.items():
        if abbrev in day_str:
            days.append(code)
    # Handle single-letter formats (MTWRFSU) when no two-letter codes matched
    if not days:
        valid_single = {'M', 'T', 'W', 'R', 'F', 'S', 'U'}
        for char in day_str:
            if char in valid_single and char not in days:
                days.append(char)
    return days


def parse_time(time_str: str) -> Optional[TimeSlot]:
    """Parse time string like '10:30AM - 11:50AM' into TimeSlot."""
    if not time_str or 'TBA' in time_str or 'ARR' in time_str:
        return None

    time_match = re.search(r'(\d{1,2}:\d{2}[AP]M)\s*-\s*(\d{1,2}:\d{2}[AP]M)', time_str)
    if not time_match:
        return None

    start_str, end_str = time_match.groups()

    try:
        start_24 = datetime.strptime(start_str, '%I:%M%p').strftime('%H:%M')
        end_24 = datetime.strptime(end_str, '%I:%M%p').strftime('%H:%M')
        return TimeSlot(start=start_24, end=end_24)
    except ValueError:
        return None


def parse_location(room_str: str) -> Optional[Location]:
    """Parse room string like 'ENG2 0302' into Location."""
    if not room_str or 'TBA' in room_str or 'WEB' in room_str:
        return None

    parts = room_str.strip().split()
    if len(parts) >= 2:
        building = parts[0]
        room = parts[1]
        return Location(building=building, room=room)
    return None


def parse_dates(date_str: str) -> tuple:
    """Parse date range like '01/12/2026 - 05/05/2026' into (start, end) as YYYY-MM-DD."""
    if not date_str:
        return ('', '')

    # UCF format: MM/DD/YYYY - MM/DD/YYYY
    date_match = re.search(r'(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})', date_str)
    if date_match:
        start_str, end_str = date_match.groups()
        # Convert MM/DD/YYYY to YYYY-MM-DD
        try:
            start_date = datetime.strptime(start_str, '%m/%d/%Y').strftime('%Y-%m-%d')
            end_date = datetime.strptime(end_str, '%m/%d/%Y').strftime('%Y-%m-%d')
            return (start_date, end_date)
        except ValueError:
            pass

    return ('', '')


def scrape_search_results(html_content: str) -> List[Course]:
    """Parse the UCF PeopleSoft search results HTML into Course objects."""
    soup = BeautifulSoup(html_content, 'html.parser')
    courses = []

    # Find all course header divs (contain course name in title attribute).
    # UCF course numbers are 4 digits, optionally followed by a trailing letter
    # like "H" for honors (e.g. "IDH 4030H"). Subject codes are 3 or 4 letters.
    course_headers = soup.find_all('a', attrs={'title': re.compile(r'Collapse section [A-Z]{3,4} \d{4}[A-Z]?')})

    for header in course_headers:
        title = header.get('title', '')
        # Ensure title is a string
        if not isinstance(title, str):
            continue
        # Extract "ACG 2021 - Principles of Financial Accounting" (or
        # "IDH 4030H - Honors Windows...") from title.
        match = re.search(r'Collapse section ([A-Z]{3,4} \d{4}[A-Z]?) - (.+)', title)
        if not match:
            continue

        course_code = match.group(1)
        course_title = match.group(2)
        course = Course(number=course_code, title=course_title)

        # Find the parent groupbox div to scope section search
        parent_div = header.find_parent('div', id=re.compile(r'win0divSSR_CLSRSLT_WRK_GROUPBOX2\$\d+'))
        if not parent_div:
            continue

        # Find section rows within this course's groupbox
        section_rows = parent_div.find_all('tr', id=re.compile(r'trSSR_CLSRCH_MTG1\$\d+_row\d+'))

        for row in section_rows:
            try:
                # Extract days/times from MTG_DAYTIME span (use separator to handle <br> tags)
                daytime_span = row.find('span', id=re.compile(r'MTG_DAYTIME\$\d+'))
                days_times_list = daytime_span.get_text(separator='\n', strip=True).split('\n') if daytime_span else []

                # Extract room from MTG_ROOM span
                room_span = row.find('span', id=re.compile(r'MTG_ROOM\$\d+'))
                room_list = room_span.get_text(separator='\n', strip=True).split('\n') if room_span else []

                # Extract meeting dates from MTG_TOPIC span
                dates_span = row.find('span', id=re.compile(r'MTG_TOPIC\$\d+'))
                dates_list = dates_span.get_text(separator='\n', strip=True).split('\n') if dates_span else []

                # Create a section for EACH meeting entry (they can have different dates/rooms/times)
                num_entries = max(len(days_times_list), len(room_list), len(dates_list))

                for i in range(num_entries):
                    daytime_str = days_times_list[i].strip() if i < len(days_times_list) else ''
                    room_str = room_list[i].strip() if i < len(room_list) else ''
                    date_str = dates_list[i].strip() if i < len(dates_list) else ''

                    # Parse time and location
                    time_slot = parse_time(daytime_str)
                    location = parse_location(room_str)
                    days = parse_days(daytime_str)

                    start_date, end_date = parse_dates(date_str)

                    # Only add sections with valid location (physical rooms) and time
                    if location and time_slot:
                        section = Section(
                            time=time_slot,
                            location=location,
                            days=days,
                            start_date=start_date,
                            end_date=end_date
                        )
                        course.sections.append(section)

            except Exception as e:
                logger.warning("Failed to parse section row for course %s: %s", course_code, e)
                continue

        if course.sections:
            courses.append(course)

    return courses
