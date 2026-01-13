from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
from pathlib import Path
import re
import time
from typing import List, Optional

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException


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


SUBJECT_CODES = [
    'ACG', 'ADE', 'ADV', 'AFA', 'AFH', 'AFR', 'AMH', 'AML', 'ANT', 'APK', 'ARA',
    'ARC', 'ARE', 'ARH', 'ART', 'ASH', 'ASL', 'AST', 'ATR', 'BCH', 'BME', 'BOT',
    'BSC', 'BTE', 'BUL', 'CAI', 'CAP', 'CCE', 'CCJ', 'CDA', 'CEG', 'CEN', 'CES',
    'CGN', 'CGS', 'CHI', 'CHM', 'CHS', 'CIS', 'CJC', 'CJE', 'CJJ', 'CJL', 'CJT',
    'CLP', 'CLT', 'CNT', 'COM', 'COP', 'COT', 'CPO', 'CRW', 'CWR', 'DAA', 'DAE',
    'DAN', 'DEP', 'DIG', 'DSC', 'EAB', 'EAP', 'EAS', 'ECM', 'ECO', 'ECP', 'ECS',
    'ECT', 'ECW', 'EDE', 'EDF', 'EDG', 'EDP', 'EEC', 'EEE', 'EEL', 'EES', 'EEX',
    'EGM', 'EGN', 'EGS', 'EIN', 'EMA', 'EME', 'EML', 'ENC', 'ENG', 'ENL', 'ENT',
    'ENV', 'ENY', 'ESE', 'ESI', 'EUH', 'EVR', 'EXP', 'FIL', 'FIN', 'FLE', 'FOL',
    'FRE', 'FRT', 'FRW', 'FSS', 'GEA', 'GEB', 'GEO', 'GER', 'GEW', 'GEY', 'GIS',
    'GLY', 'GRA', 'HAI', 'HAT', 'HBR', 'HCW', 'HFT', 'HIM', 'HIS', 'HLP', 'HSA',
    'HSC', 'HUM', 'HUN', 'IDH', 'IDS', 'IHS', 'INP', 'INR', 'ISC', 'ITA', 'ITT',
    'ITW', 'JOU', 'JPN', 'JST', 'KOR', 'LAE', 'LAH', 'LAS', 'LDR', 'LIN', 'LIT',
    'MAA', 'MAC', 'MAD', 'MAE', 'MAN', 'MAP', 'MAR', 'MAS', 'MAT', 'MCB', 'MET',
    'MGF', 'MHF', 'MHS', 'MLS', 'MMC', 'MSL', 'MTG', 'MUC', 'MUE', 'MUG', 'MUH',
    'MUL', 'MUM', 'MUN', 'MUO', 'MUS', 'MUT', 'MVB', 'MVJ', 'MVK', 'MVP', 'MVS',
    'MVV', 'MVW', 'NSP', 'NUR', 'OCE', 'OSE', 'PAD', 'PAZ', 'PCB', 'PCO', 'PEL',
    'PEM', 'PEO', 'PET', 'PGY', 'PHH', 'PHI', 'PHM', 'PHP', 'PHT', 'PHY', 'PHZ',
    'PLA', 'POR', 'POS', 'POT', 'PPE', 'PSB', 'PSC', 'PSY', 'PUP', 'PUR', 'QMB',
    'RED', 'REE', 'REL', 'RMI', 'RTV', 'RUS', 'RUT', 'SCC', 'SCE', 'SLS', 'SOP',
    'SOW', 'SPA', 'SPB', 'SPC', 'SPM', 'SPN', 'SPT', 'SPW', 'SSE', 'STA', 'SYA',
    'SYD', 'SYG', 'SYO', 'SYP', 'TAX', 'THE', 'TPA', 'TPP', 'TSL', 'TTE', 'VIC',
    'WOH', 'WST', 'ZOO'
]

BASE_URL = "https://csprod-ss.net.ucf.edu/psc/CSPROD/EMPLOYEE/SA/c/COMMUNITY_ACCESS.CLASS_SEARCH.GBL"


def setup_driver(headless: bool = True) -> webdriver.Chrome:
    """Initialize Chrome WebDriver with options."""
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    return driver


def wait_for_page_load(driver: webdriver.Chrome, timeout: int = 30):
    """Wait for page to finish loading."""
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    time.sleep(1)


def parse_days(day_str: str) -> List[str]:
    """Parse day string like 'TuTh 10:30AM' into list of day codes."""
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
    # Handle single-letter formats (M, W, F without o/e/r suffix)
    if not days:
        if 'M' in day_str and 'Mo' not in day_str:
            days.append('M')
        if 'W' in day_str and 'We' not in day_str:
            days.append('W')
        if 'F' in day_str and 'Fr' not in day_str:
            days.append('F')
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

    # Find all course header divs (contain course name in title attribute)
    course_headers = soup.find_all('a', attrs={'title': re.compile(r'Collapse section [A-Z]{3} \d{4}')})
    
    for header in course_headers:
        title = header.get('title', '')
        # Ensure title is a string
        if not isinstance(title, str):
            continue
        # Extract "ACG 2021 - Principles of Financial Accounting" from title
        match = re.search(r'Collapse section ([A-Z]{3} \d{4}) - (.+)', title)
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
                    
                    # Parse date range (format: MM/DD/YYYY - MM/DD/YYYY)
                    start_date = ''
                    end_date = ''
                    date_match = re.search(r'(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})', date_str)
                    if date_match:
                        try:
                            start_date = datetime.strptime(date_match.group(1), '%m/%d/%Y').strftime('%Y-%m-%d')
                            end_date = datetime.strptime(date_match.group(2), '%m/%d/%Y').strftime('%Y-%m-%d')
                        except ValueError:
                            pass
                    
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
                continue
        
        if course.sections:
            courses.append(course)

    return courses


def search_subject(driver: webdriver.Chrome, subject_code: str, is_first: bool = True, debug: bool = False) -> str:
    """
    Execute search for a specific subject and return the results HTML.
    
    Steps:
    1. Navigate to search page (first time) OR click "Modify Search" (subsequent)
    2. Tick "Verify Search"
    3. Add subject code to "Subject" field
    4. Choose empty option for "Course Career"
    5. Select "Main Campus (Orlando)" for Location
    6. Untick "Show Open Classes Only"
    7. Click Search and wait for results
    """
    debug_dir = Path(__file__).parent / "debug"
    
    try:
        if is_first:
            # Navigate to search page (first time only)
            driver.get(BASE_URL)
            wait_for_page_load(driver)

            # Debug: Save initial page state
            if debug:
                debug_dir.mkdir(exist_ok=True)
                driver.save_screenshot(str(debug_dir / f"{subject_code}_initial.png"))
                with open(debug_dir / f"{subject_code}_initial.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print(f"  Debug files saved to {debug_dir}")

            # Wait for page to be interactive
            time.sleep(3)
        else:
            # Use "Modify Search" button for subsequent searches (much faster!)
            try:
                modify_button = driver.find_element(By.ID, "CLASS_SRCH_WRK2_SSR_PB_MODIFY")
                driver.execute_script("arguments[0].click();", modify_button)
                print("  Clicked 'Modify Search'...")
                
                # Wait for search form to load
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.ID, "SSR_CLSRCH_WRK_SUBJECT$0"))
                )
                wait_for_page_load(driver)
                time.sleep(1)  # Small buffer for form to be ready
            except (NoSuchElementException, TimeoutException) as e:
                print(f"  Could not find Modify Search button, navigating to base URL: {e}")
                driver.get(BASE_URL)
                wait_for_page_load(driver)
                time.sleep(3)

        # Find elements with correct UCF PeopleSoft IDs
        try:
            search_button = driver.find_element(By.ID, "CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH")
        except NoSuchElementException:
            print("  Could not find search button!")
            return ""

        # 1. Tick "Verify Search" checkbox
        try:
            verify_checkbox = driver.find_element(By.ID, "FX_CLSSRCH_DER_FLAG")
            if not verify_checkbox.is_selected():
                verify_checkbox.click()
                print("  Checked verify search")
        except NoSuchElementException:
            print("  Verify checkbox not found (continuing anyway)")

        if is_first:
            time.sleep(0.3)  # Only needed on first load

        # 2. Enter subject code
        try:
            subject_field = driver.find_element(By.ID, "SSR_CLSRCH_WRK_SUBJECT$0")
            subject_field.clear()
            subject_field.send_keys(subject_code)
            print(f"  Entered subject: {subject_code}")
        except NoSuchElementException:
            print("  Could not find subject field!")
            return ""

        # 3. Set Course Career to empty (all careers)
        try:
            career_dropdown = Select(driver.find_element(By.ID, "SSR_CLSRCH_WRK_ACAD_CAREER$3"))
            career_dropdown.select_by_value("")  # Empty = all
            print("  Set career to: All")
            if is_first:
                time.sleep(0.5)  # Only needed on first load
        except (NoSuchElementException, Exception) as e:
            print(f"  Career dropdown issue: {e}")

        # 4. Select Location - Main Campus (Orlando)
        try:
            # Re-find element after page update to avoid stale reference
            location_dropdown = Select(driver.find_element(By.ID, "SSR_CLSRCH_WRK_LOCATION$4"))
            for option in location_dropdown.options:
                if 'Main' in option.text or 'Orlando' in option.text:
                    location_dropdown.select_by_visible_text(option.text)
                    print(f"  Set location to: {option.text}")
                    break
            time.sleep(0.3)
        except (NoSuchElementException, Exception) as e:
            print(f"  Location dropdown issue (may be okay): {e}")

        # 5. Untick "Show Open Classes Only"
        try:
            open_checkbox = driver.find_element(By.ID, "SSR_CLSRCH_WRK_SSR_OPEN_ONLY$6")
            if open_checkbox.is_selected():
                open_checkbox.click()
                print("  Unchecked 'Show Open Classes Only'")
        except NoSuchElementException:
            print("  Open only checkbox not found")

        time.sleep(0.2)  # Small buffer before search

        # Debug: Save state before search
        if debug:
            driver.save_screenshot(str(debug_dir / f"{subject_code}_before_search.png"))

        # 6. Click Search button
        driver.execute_script("arguments[0].click();", search_button)
        print("  Clicked search...")

        # Wait for results page to load - look for "class section(s) found" text
        try:
            WebDriverWait(driver, 45).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'class section')]"))
            )
            print("  Results loaded!")
        except TimeoutException:
            # Check for "no classes found" or similar
            page_text = driver.page_source.lower()
            if 'no classes found' in page_text or 'search returned no results' in page_text:
                print(f"  No classes found for {subject_code}")
                return ""
            
            if debug:
                driver.save_screenshot(str(debug_dir / f"{subject_code}_no_results.png"))
                with open(debug_dir / f"{subject_code}_no_results.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
            print("  Timeout waiting for results")
            return ""

        wait_for_page_load(driver)

        # Expand all course sections to see section details
        expand_all_sections(driver)

        # Debug: Save final state
        if debug:
            driver.save_screenshot(str(debug_dir / f"{subject_code}_results.png"))
            with open(debug_dir / f"{subject_code}_results.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)

        return driver.page_source

    except TimeoutException as e:
        print(f"Timeout while searching for {subject_code}: {e}")
        if debug:
            debug_dir.mkdir(exist_ok=True)
            driver.save_screenshot(str(debug_dir / f"{subject_code}_timeout.png"))
            with open(debug_dir / f"{subject_code}_timeout.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
        return ""
    except Exception as e:
        print(f"Error searching for {subject_code}: {e}")
        if debug:
            debug_dir.mkdir(exist_ok=True)
            try:
                driver.save_screenshot(str(debug_dir / f"{subject_code}_error.png"))
                with open(debug_dir / f"{subject_code}_error.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
            except:
                pass
        return ""


def expand_all_sections(driver: webdriver.Chrome):
    """Expand all collapsible course sections to reveal section details."""
    try:
        expand_links = driver.find_elements(
            By.CSS_SELECTOR,
            "a[id^='CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH']"
        )

        for link in expand_links:
            try:
                if link.is_displayed():
                    driver.execute_script("arguments[0].click();", link)
                    time.sleep(0.3)
            except:
                continue

        wait_for_page_load(driver)
    except Exception as e:
        print(f"Error expanding sections: {e}")


def save_data(subjects: List[Subject], term: str = "Spring 2026"):
    """Save scraped data to JSON file."""
    data_dir = Path(__file__).parent / "archive"
    data_dir.mkdir(exist_ok=True)

    data = {
        "last_updated": datetime.now().isoformat(),
        "term": term,
        "subjects": [asdict(subject) for subject in subjects]
    }

    output_file = data_dir / "courses_SP26.json"
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Data saved to {output_file}")


def scrape_all_subjects(
    headless: bool = True,
    debug: bool = False,
    subject_codes: Optional[List[str]] = None
) -> List[Subject]:
    """Main scraping function."""
    if subject_codes is None:
        subject_codes = SUBJECT_CODES

    start_time = datetime.now()
    driver = setup_driver(headless=headless)
    subjects = []

    total_subjects = len(subject_codes)
    total_courses = 0
    total_sections = 0

    try:
        for i, code in enumerate(subject_codes, 1):
            print(f"[{i}/{total_subjects}] Scraping subject: {code}")

            html_content = search_subject(driver, code, is_first=(i == 1), debug=debug)

            if html_content:
                courses = scrape_search_results(html_content)

                # Filter courses with at least one section with a valid location
                valid_courses = []
                for course in courses:
                    valid_sections = [s for s in course.sections if s.location is not None]
                    if valid_sections:
                        course.sections = valid_sections
                        valid_courses.append(course)

                if valid_courses:
                    subject = Subject(code=code, courses=valid_courses)
                    subjects.append(subject)

                    course_count = len(valid_courses)
                    section_count = sum(len(c.sections) for c in valid_courses)
                    total_courses += course_count
                    total_sections += section_count

                    print(f"  Found {course_count} courses, {section_count} sections")

            # Small delay between requests
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nScraping interrupted, saving partial results...")
    finally:
        driver.quit()

    duration = datetime.now() - start_time
    print(f"\nScraping complete in {duration.total_seconds():.1f}s")
    print(f"Total: {len(subjects)} subjects, {total_courses} courses, {total_sections} sections")

    return subjects


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Scrape UCF course data')
    parser.add_argument('--headless', action='store_true', default=True,
                        help='Run browser in headless mode')
    parser.add_argument('--no-headless', dest='headless', action='store_false',
                        help='Show browser window')
    parser.add_argument('--debug', action='store_true',
                        help='Save debug screenshots and HTML')
    parser.add_argument('--subjects', nargs='+', default=None,
                        help='Specific subject codes to scrape (default: all)')
    parser.add_argument('--test', action='store_true',
                        help='Test mode: scrape only first 3 subjects')

    args = parser.parse_args()

    subject_codes = args.subjects
    if args.test:
        subject_codes = SUBJECT_CODES[:3]

    print("Starting UCF course scraper...")
    print("Press Ctrl+C to stop and save partial results\n")

    subjects = scrape_all_subjects(
        headless=args.headless,
        debug=args.debug,
        subject_codes=subject_codes
    )

    save_data(subjects)
