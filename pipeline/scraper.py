from dataclasses import asdict
from datetime import datetime
import json
import logging
from pathlib import Path
import time
from typing import List, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementNotInteractableException,
    JavascriptException,
    WebDriverException,
)

from parsers import (
    TimeSlot,
    Location,
    Section,
    Course,
    Subject,
    parse_days,
    parse_time,
    parse_location,
    parse_dates,
    scrape_search_results,
)

logger = logging.getLogger(__name__)


SUBJECT_CODES = [
    'ACG', 'ADE', 'ADV', 'AFA', 'AFH', 'AFR', 'AMH', 'AML', 'ANG', 'ANT', 'APK',
    'ARA', 'ARC', 'ARE', 'ARH', 'ART', 'ASH', 'ASL', 'AST', 'ATR', 'AVM', 'BCH',
    'BME', 'BMS', 'BOT', 'BSC', 'BTE', 'BUL', 'CAI', 'CAP', 'CBH', 'CCE', 'CCJ',
    'CDA', 'CEG', 'CEN', 'CES', 'CGN', 'CGS', 'CHI', 'CHM', 'CHS', 'CIS', 'CJC',
    'CJE', 'CJJ', 'CJL', 'CJT', 'CLA', 'CLP', 'CLT', 'CNT', 'COM', 'COP', 'COT',
    'CPO', 'CRW', 'CWR', 'CYP', 'DAA', 'DAE', 'DAN', 'DEP', 'DIE', 'DIG', 'DSC',
    'EAB', 'EAP', 'EAS', 'EBD', 'ECM', 'ECO', 'ECP', 'ECS', 'ECT', 'ECW', 'EDA',
    'EDE', 'EDF', 'EDG', 'EDH', 'EDM', 'EDP', 'EDS', 'EEC', 'EEE', 'EEL', 'EES',
    'EEX', 'EGC', 'EGI', 'EGM', 'EGN', 'EGS', 'EIN', 'ELD', 'EMA', 'EME', 'EML',
    'EMR', 'ENC', 'ENG', 'ENL', 'ENT', 'ENV', 'ENY', 'ESE', 'ESI', 'EUH', 'EVR',
    'EXP', 'FIL', 'FIN', 'FLE', 'FOL', 'FRE', 'FRT', 'FRW', 'FSS', 'GEA', 'GEB',
    'GEO', 'GER', 'GEW', 'GEY', 'GIS', 'GLY', 'GMS', 'GRA', 'HAI', 'HAT', 'HBR',
    'HCW', 'HFT', 'HIM', 'HIS', 'HLP', 'HMG', 'HSA', 'HSC', 'HUM', 'HUN', 'IDC',
    'IDH', 'IDS', 'IHS', 'INP', 'INR', 'ISC', 'ISM', 'ITA', 'ITT', 'ITW', 'JOU',
    'JPN', 'JST', 'KOR', 'LAE', 'LAH', 'LAS', 'LDR', 'LEI', 'LIN', 'LIT', 'MAA',
    'MAC', 'MAD', 'MAE', 'MAN', 'MAP', 'MAR', 'MAS', 'MAT', 'MCB', 'MDC', 'MDE',
    'MDI', 'MDR', 'MDX', 'MET', 'MGF', 'MHF', 'MHS', 'MLS', 'MMC', 'MSL', 'MTG',
    'MUC', 'MUE', 'MUG', 'MUH', 'MUL', 'MUM', 'MUN', 'MUO', 'MUS', 'MUT', 'MVB',
    'MVJ', 'MVK', 'MVO', 'MVP', 'MVS', 'MVV', 'MVW', 'NGR', 'NSP', 'NUR', 'OCE',
    'OSE', 'PAD', 'PAF', 'PAZ', 'PCB', 'PCO', 'PEL', 'PEM', 'PEO', 'PET', 'PGY',
    'PHC', 'PHH', 'PHI', 'PHM', 'PHP', 'PHT', 'PHY', 'PHZ', 'PLA', 'POR', 'POS',
    'POT', 'PPE', 'PSB', 'PSC', 'PSY', 'PUP', 'PUR', 'QMB', 'RED', 'REE', 'REL',
    'RMI', 'RTV', 'RUS', 'RUT', 'SCC', 'SCE', 'SDS', 'SLS', 'SOP', 'SOW', 'SPA',
    'SPB', 'SPC', 'SPM', 'SPN', 'SPS', 'SPT', 'SPW', 'SSE', 'STA', 'SYA', 'SYD',
    'SYG', 'SYO', 'SYP', 'TAX', 'THE', 'TPA', 'TPP', 'TSL', 'TTE', 'URP', 'VIC',
    'WOH', 'WST', 'ZOO'
]

BASE_URL = "https://csprod-ss.net.ucf.edu/psc/CSPROD/EMPLOYEE/SA/c/COMMUNITY_ACCESS.CLASS_SEARCH.GBL"

TERM_LABELS = {
    'SP26': 'Spring 2026',
    'SU26': 'Summer 2026',
    'FA26': 'Fall 2026',
    'SP25': 'Spring 2025',
    'SU25': 'Summer 2025',
    'FA25': 'Fall 2025',
}


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
    time.sleep(0.3)


# A single blank-career ("") pass returns ALL careers (UGRD + GRAD + MED + OTHR)
# in one search, verified manually against UCF PeopleSoft with COP (223 sections,
# including COP 5xxx/6xxx/7xxx grad courses). The blank option MUST be selected
# LAST, after every other field, because PeopleSoft's onchange AJAX re-renders
# the form and reverts the career dropdown to its UGRD default on subsequent
# changes to location / open-only.
CAREER_LEVELS = [""]


def dismiss_overflow_confirmation(driver: webdriver.Chrome, subject_code: str, timeout: int = 8) -> bool:
    """Click OK on the ">300 classes, continue?" modal if PeopleSoft shows it.

    Returns True if the modal was found and dismissed, False otherwise. The
    modal takes a few seconds to appear after clicking Search, but is not
    guaranteed to appear at all (most subjects stay under the 300-class cap).
    We poll briefly; if no modal appears we assume this subject is under the
    cap and let the caller's results-wait do its job.
    """
    end = time.time() + timeout
    while time.time() < end:
        frames = driver.find_elements(By.ID, "ptModFrame_0")
        if frames and frames[0].is_displayed():
            try:
                driver.switch_to.frame(frames[0])
                # The OK button id literally contains a '#' prefix, which is
                # invalid in CSS selectors -- use XPath with the exact id.
                ok_buttons = driver.find_elements(By.XPATH, "//input[@id='#ICSave']")
                if ok_buttons and ok_buttons[0].is_displayed():
                    driver.execute_script("arguments[0].click();", ok_buttons[0])
                    logger.info(
                        "Dismissed '>300 classes' confirmation for %s",
                        subject_code,
                    )
                    driver.switch_to.default_content()
                    return True
            except (NoSuchElementException, StaleElementReferenceException) as e:
                logger.debug("Modal dismiss attempt failed: %s", e)
            finally:
                try:
                    driver.switch_to.default_content()
                except WebDriverException:
                    pass
        time.sleep(0.3)
    return False


def search_subject(driver: webdriver.Chrome, subject_code: str, career: str = "", debug: bool = False) -> str:
    """
    Execute search for a specific subject and return the results HTML.

    Field-interaction order mirrors the user's verified manual click sequence
    and MUST NOT be reordered casually:
    1. Navigate fresh to the search page
    2. Enter subject code
    3. Tick "Verify Search"
    4. Select "Main Campus (Orlando)" for Location
    5. Untick "Show Open Classes Only"
    6. Select Course Career (blank = all careers) -- LAST, no field touched after
    7. Click Search and wait for results
    """
    debug_dir = Path(__file__).parent / "debug"
    
    try:
        # Clear cookies before each subject. PeopleSoft holds server-side
        # session state that survives `driver.get(BASE_URL)` and leaves the
        # form in a half-stale state for the second-and-subsequent subject in
        # a session, causing the search to time out or return empty results.
        # delete_all_cookies forces a clean PeopleSoft session per subject.
        try:
            driver.delete_all_cookies()
        except WebDriverException as cookie_err:
            logger.debug("delete_all_cookies failed (continuing): %s", cookie_err)

        # Always navigate fresh to the search page. The "Modify Search" path
        # has proved unreliable: for subjects with no results, the modify-search
        # page transition hangs and times out. Fresh navigation is ~2s slower
        # but 100% reliable.
        driver.get(BASE_URL)
        wait_for_page_load(driver)

        # Debug: Save initial page state
        if debug:
            debug_dir.mkdir(exist_ok=True)
            driver.save_screenshot(str(debug_dir / f"{subject_code}_initial.png"))
            with open(debug_dir / f"{subject_code}_initial.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            logger.debug("Debug files saved to %s", debug_dir)

        # Wait for search form to be interactive
        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH"))
        )
        time.sleep(0.5)  # PeopleSoft JS initialization buffer

        # Find elements with correct UCF PeopleSoft IDs
        try:
            search_button = driver.find_element(By.ID, "CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH")
        except NoSuchElementException:
            logger.error("Could not find search button!")
            return ""

        # 1. Enter subject code
        try:
            subject_field = driver.find_element(By.ID, "SSR_CLSRCH_WRK_SUBJECT$0")
            subject_field.clear()
            subject_field.send_keys(subject_code)
            logger.info("Entered subject: %s", subject_code)
        except NoSuchElementException:
            logger.error("Could not find subject field!")
            return ""

        # 2. Tick "Verify Search" checkbox
        try:
            verify_checkbox = driver.find_element(By.ID, "FX_CLSSRCH_DER_FLAG")
            if not verify_checkbox.is_selected():
                verify_checkbox.click()
                logger.info("Checked verify search")
        except NoSuchElementException:
            logger.warning("Verify checkbox not found (continuing anyway)")

        time.sleep(0.2)  # PeopleSoft checkbox AJAX buffer

        # 3. Select Location - Main Campus (Orlando)
        try:
            location_dropdown = Select(driver.find_element(By.ID, "SSR_CLSRCH_WRK_LOCATION$4"))
            for option in location_dropdown.options:
                if 'Main' in option.text or 'Orlando' in option.text:
                    location_dropdown.select_by_visible_text(option.text)
                    logger.info("Set location to: %s", option.text)
                    break
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "SSR_CLSRCH_WRK_SSR_OPEN_ONLY$6"))
            )
            time.sleep(0.3)  # AJAX settle
        except (NoSuchElementException, StaleElementReferenceException, TimeoutException) as e:
            logger.warning("Location dropdown issue (may be okay): %s", e)

        # 4. Untick "Show Open Classes Only"
        try:
            open_checkbox = driver.find_element(By.ID, "SSR_CLSRCH_WRK_SSR_OPEN_ONLY$6")
            if open_checkbox.is_selected():
                open_checkbox.click()
                logger.info("Unchecked 'Show Open Classes Only'")
                time.sleep(0.2)  # checkbox AJAX settle
        except NoSuchElementException:
            logger.warning("Open only checkbox not found")

        # 5. Set Course Career LAST, so no subsequent AJAX re-renders it.
        # PeopleSoft reverts the dropdown to UGRD on every form refresh, so
        # this MUST come after every other field has been set. Only click the
        # dropdown if the desired value differs from current; re-selecting the
        # same value does not fire onchange and leaves form state stale.
        try:
            career_dropdown = Select(driver.find_element(By.ID, "SSR_CLSRCH_WRK_ACAD_CAREER$3"))
            current_career = career_dropdown.first_selected_option.get_attribute("value")
            if current_career != career:
                career_dropdown.select_by_value(career)
                logger.info("Set career to: %s (was %s)", career or "blank", current_career or "blank")
                # Wait for PeopleSoft AJAX refresh, then verify selection stuck
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "SSR_CLSRCH_WRK_ACAD_CAREER$3"))
                )
                time.sleep(0.3)
                post_career = Select(
                    driver.find_element(By.ID, "SSR_CLSRCH_WRK_ACAD_CAREER$3")
                ).first_selected_option.get_attribute("value")
                if post_career != career:
                    logger.warning(
                        "Career dropdown reverted to %s after setting %s",
                        post_career or "blank", career or "blank",
                    )
            else:
                logger.info("Career already %s, skipping re-selection", career or "blank")
        except (NoSuchElementException, StaleElementReferenceException, TimeoutException) as e:
            logger.warning("Career dropdown issue: %s", e)

        # Debug: Save state before search
        if debug:
            driver.save_screenshot(str(debug_dir / f"{subject_code}_before_search.png"))

        # 6. Click Search button
        driver.execute_script("arguments[0].click();", search_button)
        logger.info("Clicked search...")

        # Dismiss PeopleSoft's "Your search will return over 300 classes,
        # would you like to continue?" confirmation modal if it appears. The
        # modal is an iframe (`ptModFrame_0`) containing an OK button with
        # id `#ICSave`. Without clicking OK, the search stalls indefinitely
        # and the results wait times out -- which was the root cause of
        # EEL/PHY/OCE "overflow" being silently dropped.
        dismiss_overflow_confirmation(driver, subject_code)

        # Wait for results page to load - look for EITHER results OR no-results message
        try:
            WebDriverWait(driver, 60).until(
                lambda d: (
                    d.find_elements(By.XPATH, "//*[contains(text(), 'class section')]")
                    or d.find_elements(By.ID, "DERIVED_CLSMSG_ERROR_TEXT")
                )
            )
        except TimeoutException:
            if debug:
                driver.save_screenshot(str(debug_dir / f"{subject_code}_no_results.png"))
                with open(debug_dir / f"{subject_code}_no_results.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
            # A 45s timeout on the results wait strongly correlates with
            # PeopleSoft's result-set cap for huge departments (EEL, PHY, OCE)
            # where the cap-exceeded message never finishes rendering. Return
            # OVERFLOW so scrape_subject_with_retry can retry with a narrower
            # UGRD+GRAD split. If the timeout was actually a network hiccup,
            # the split retry will simply time out again and the caller will
            # fall back to the normal failure path.
            logger.warning("Timeout waiting for results for %s (treating as overflow)", subject_code)
            return OVERFLOW_SENTINEL

        # Check if we got an error message. PeopleSoft uses the same element
        # for both "no results" and "too many results (narrow your search)",
        # so we must read the text to tell them apart.
        error_elements = driver.find_elements(By.ID, "DERIVED_CLSMSG_ERROR_TEXT")
        if error_elements:
            err_text = (error_elements[0].text or "").strip().lower()
            if "narrow" in err_text or "additional selection" in err_text:
                logger.info("Too many results for %s (overflow, will retry with career split)", subject_code)
                return OVERFLOW_SENTINEL
            logger.info("No classes found for %s", subject_code)
            return NO_RESULTS_SENTINEL

        logger.info("Results loaded!")

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
        logger.error("Timeout while searching for %s: %s", subject_code, e)
        if debug:
            debug_dir.mkdir(exist_ok=True)
            driver.save_screenshot(str(debug_dir / f"{subject_code}_timeout.png"))
            with open(debug_dir / f"{subject_code}_timeout.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
        return ""
    except WebDriverException:
        # Let driver crashes (invalid session id, etc.) propagate to the outer
        # loop so it can restart the browser. Swallowing these causes every
        # subsequent subject in the run to silently fail against a dead driver.
        raise
    except Exception as e:
        logger.error("Error searching for %s: %s", subject_code, e)
        if debug:
            debug_dir.mkdir(exist_ok=True)
            try:
                driver.save_screenshot(str(debug_dir / f"{subject_code}_error.png"))
                with open(debug_dir / f"{subject_code}_error.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
            except Exception as screenshot_err:
                logger.debug("Failed to save debug screenshot: %s", screenshot_err)
        return ""


def expand_all_sections(driver: webdriver.Chrome):
    """Expand all collapsible course sections to reveal section details."""
    try:
        expand_links = driver.find_elements(
            By.CSS_SELECTOR,
            "a[id^='CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH']"
        )

        # Batch-click all expand links, then wait once for page to settle
        for link in expand_links:
            try:
                if link.is_displayed():
                    driver.execute_script("arguments[0].click();", link)
            except (StaleElementReferenceException, ElementNotInteractableException, JavascriptException) as expand_err:
                logger.debug("Failed to expand section link: %s", expand_err)
                continue

        if expand_links:
            wait_for_page_load(driver)
    except Exception as e:
        logger.error("Error expanding sections: %s", e)


def save_data(subjects: List[Subject], term_code: str = "SP26", output_path: Optional[Path] = None):
    """Save scraped data to JSON file.

    Args:
        subjects: Scraped subject data
        term_code: Term code (used for default output filename)
        output_path: Optional custom output path. If None, uses
                     archive/courses_{term_code}.json (default behavior).
    """
    data_dir = Path(__file__).parent / "archive"
    data_dir.mkdir(exist_ok=True)

    term_label = TERM_LABELS.get(term_code, term_code)

    data = {
        "last_updated": datetime.now().isoformat(),
        "term": term_label,
        "subjects": [asdict(subject) for subject in subjects]
    }

    if output_path is None:
        output_path = data_dir / f"courses_{term_code}.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    logger.info("Data saved to %s", output_path)


MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0

# Restart the browser every N subjects to prevent chromedriver memory/state
# accumulation that causes crashes on long scraping runs.
BROWSER_RESTART_INTERVAL = 40

# Sentinel returned by search_subject when the search executed successfully
# but PeopleSoft reported no matching classes (a legitimate empty result).
NO_RESULTS_SENTINEL = "__NO_RESULTS__"

# Sentinel returned when PeopleSoft's result set exceeds its cap and the UI
# asks us to narrow the search ("Specify additional selection criteria..."),
# or when the results wait times out on a huge department (which empirically
# correlates with overflow). Caller must retry with narrower criteria --
# scrape_subject_with_retry handles this by splitting a blank-career search
# into explicit UGRD + GRAD passes.
OVERFLOW_SENTINEL = "__OVERFLOW__"


def _checkpoint_path(term_code: str) -> Path:
    return Path(__file__).parent / "archive" / f"checkpoint_{term_code}.json"


def load_checkpoint(term_code: str) -> dict:
    """Load checkpoint data for resumable scraping. Returns empty dict if none exists."""
    cp_path = _checkpoint_path(term_code)
    if cp_path.exists():
        with open(cp_path, "r") as f:
            return json.load(f)
    return {}


def save_checkpoint(term_code: str, completed: List[str], failed: List[str]):
    """Save checkpoint with completed/failed subject lists."""
    cp_path = _checkpoint_path(term_code)
    cp_path.parent.mkdir(exist_ok=True)
    data = {
        "term": term_code,
        "completed_subjects": completed,
        "failed_subjects": failed,
        "timestamp": datetime.now().isoformat(),
    }
    with open(cp_path, "w") as f:
        json.dump(data, f, indent=2)


def delete_checkpoint(term_code: str):
    """Remove checkpoint file after successful completion."""
    cp_path = _checkpoint_path(term_code)
    if cp_path.exists():
        cp_path.unlink()
        logger.info("Checkpoint file removed: %s", cp_path)


def _search_single_career_with_retry(
    driver: webdriver.Chrome,
    code: str,
    career: str,
    debug: bool,
) -> str:
    """Search a single career level with exponential backoff on failure."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            html_content = search_subject(driver, code, career=career, debug=debug)
        except WebDriverException:
            raise  # Let caller handle driver crashes
        if html_content == NO_RESULTS_SENTINEL:
            return NO_RESULTS_SENTINEL
        if html_content == OVERFLOW_SENTINEL:
            # Don't retry overflow -- the result set won't shrink on its own.
            # Let the caller decide whether to narrow the search.
            return OVERFLOW_SENTINEL
        if html_content:
            return html_content
        if attempt < MAX_RETRIES:
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning(
                "Attempt %d/%d failed for %s [%s], retrying in %.1fs",
                attempt + 1, MAX_RETRIES, code, career, delay,
            )
            time.sleep(delay)
    return ""


def scrape_subject_with_retry(
    driver: webdriver.Chrome,
    code: str,
    debug: bool,
    careers: Optional[List[str]] = None,
) -> list:
    """Scrape a subject across the given career levels and merge the courses.

    By default a single blank-career ("") search is issued; PeopleSoft treats
    that as "all careers" and returns UGRD + GRAD + MED + OTHR in one pass,
    provided the career dropdown is set LAST (see search_subject). The
    multi-career loop is retained only as a debugging escape hatch.

    Args:
        careers: Career levels to query. Defaults to CAREER_LEVELS ([""]).

    Returns:
        - List of Course objects (merged across all careers, deduped by number)
        - Empty list if all career searches returned no results or failed
    """
    if careers is None:
        careers = CAREER_LEVELS
    all_courses: dict = {}  # course_number -> Course
    any_results_or_no_results = False
    hit_overflow = False

    for career in careers:
        result = _search_single_career_with_retry(driver, code, career, debug)
        career_label = career or "blank"
        if result == NO_RESULTS_SENTINEL:
            any_results_or_no_results = True
            logger.info("  [%s %s] No results", code, career_label)
            continue
        if result == OVERFLOW_SENTINEL:
            hit_overflow = True
            logger.info("  [%s %s] Overflow (too many results)", code, career_label)
            continue
        if not result:
            logger.warning("  [%s %s] Failed after %d retries", code, career_label, MAX_RETRIES)
            continue

        any_results_or_no_results = True
        courses = scrape_search_results(result)
        for course in courses:
            if course.number not in all_courses:
                all_courses[course.number] = course
            else:
                # Merge sections from the same course found in multiple careers
                # (rare but possible)
                existing = all_courses[course.number]
                existing.sections.extend(course.sections)
        logger.info("  [%s %s] %d courses parsed", code, career_label, len(courses))

    # Overflow fallback: a blank-career search that hit PeopleSoft's result
    # cap returns nothing usable. Retry the same subject with explicit
    # UGRD + GRAD splits, which each stay under the cap for every UCF subject
    # we've observed (EEL, PHY, OCE). Only fall back once -- if the split
    # also overflows (never seen), the caller just gets an empty result.
    if hit_overflow and careers == [""] and not all_courses:
        logger.info(
            "  [%s] Falling back to UGRD+GRAD split after blank-career overflow",
            code,
        )
        return scrape_subject_with_retry(
            driver, code, debug=debug, careers=["UGRD", "GRAD"],
        )

    if not any_results_or_no_results and not hit_overflow:
        return []  # Total failure - nothing succeeded
    return list(all_courses.values())


def scrape_all_subjects(
    headless: bool = True,
    debug: bool = False,
    subject_codes: Optional[List[str]] = None,
    delay: float = 1.0,
    term_code: str = "SP26",
    resume: bool = False,
    careers: Optional[List[str]] = None,
) -> List[Subject]:
    """Main scraping function with optional resume support."""
    if subject_codes is None:
        subject_codes = SUBJECT_CODES

    # Resume: load checkpoint and skip already-completed subjects
    completed_codes = []
    subjects = []
    failed_subjects = []

    if resume:
        checkpoint = load_checkpoint(term_code)
        if checkpoint:
            completed_codes = checkpoint.get("completed_subjects", [])
            failed_subjects = checkpoint.get("failed_subjects", [])
            logger.info("Resuming: %d subjects already completed, %d previously failed",
                        len(completed_codes), len(failed_subjects))
            # Load previously saved partial results
            output_file = Path(__file__).parent / "archive" / f"courses_{term_code}.json"
            if output_file.exists():
                with open(output_file, "r") as f:
                    prev_data = json.load(f)
                for subj_data in prev_data.get("subjects", []):
                    subj = Subject(
                        code=subj_data["code"],
                        courses=[
                            Course(
                                number=c["number"],
                                title=c.get("title"),
                                sections=[
                                    Section(
                                        time=TimeSlot(**s["time"]) if s.get("time") else None,
                                        location=Location(**s["location"]) if s.get("location") else None,
                                        days=s.get("days", []),
                                        start_date=s.get("start_date", ""),
                                        end_date=s.get("end_date", ""),
                                    )
                                    for s in c.get("sections", [])
                                ],
                            )
                            for c in subj_data.get("courses", [])
                        ],
                    )
                    subjects.append(subj)
            # Derive completed_codes from actually loaded subjects to avoid drift
            loaded_codes = {s.code for s in subjects}
            completed_codes = list(loaded_codes)
            failed_subjects = []
            # Filter to only remaining subjects (previously failed get retried)
            codes_to_scrape = [c for c in subject_codes if c not in loaded_codes]
            logger.info("Remaining subjects to scrape: %d", len(codes_to_scrape))
        else:
            codes_to_scrape = list(subject_codes)
            logger.info("No checkpoint found, starting fresh")
    else:
        codes_to_scrape = list(subject_codes)

    start_time = datetime.now()
    driver = setup_driver(headless=headless)

    total_subjects = len(codes_to_scrape)
    total_courses = sum(len(s.courses) for s in subjects)
    total_sections = sum(sum(len(c.sections) for c in s.courses) for s in subjects)

    try:
        for i, code in enumerate(codes_to_scrape, 1):
            logger.info("[%d/%d] Scraping subject: %s", i, total_subjects, code)

            # Periodically restart the browser to prevent accumulated state
            # from causing chromedriver crashes on long runs.
            if i > 1 and (i - 1) % BROWSER_RESTART_INTERVAL == 0:
                logger.info("Restarting browser after %d subjects to keep session fresh", i - 1)
                try:
                    driver.quit()
                except Exception as e:
                    logger.warning("Error quitting driver before restart: %s", e)
                driver = setup_driver(headless=headless)

            try:
                courses = scrape_subject_with_retry(driver, code, debug=debug, careers=careers)
            except WebDriverException as e:
                logger.error("Driver crashed while scraping %s: %s. Restarting...", code, e)
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = setup_driver(headless=headless)
                # Retry this subject once with the fresh driver
                try:
                    courses = scrape_subject_with_retry(driver, code, debug=debug, careers=careers)
                except WebDriverException as e2:
                    logger.error("Driver crashed again for %s: %s", code, e2)
                    courses = None  # Signal total failure

            if courses is None:
                # Driver crash; actual failure
                failed_subjects.append(code)
            elif not courses:
                # No results in any career level (legitimately empty or all failed)
                logger.info("  No classes for %s", code)
                completed_codes.append(code)
            else:
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

                    logger.info("  Found %d courses, %d sections", course_count, section_count)

                completed_codes.append(code)

            # Save checkpoint after each subject
            save_checkpoint(term_code, completed_codes, failed_subjects)

            time.sleep(delay)

    except KeyboardInterrupt:
        logger.warning("Scraping interrupted, saving partial results...")
        interrupted = True
    else:
        interrupted = False
    finally:
        driver.quit()

    duration = datetime.now() - start_time
    logger.info("Scraping complete in %.1fs", duration.total_seconds())
    logger.info("Total: %d subjects, %d courses, %d sections", len(subjects), total_courses, total_sections)
    if failed_subjects:
        logger.warning("Failed subjects (even after %d retries): %s", MAX_RETRIES, failed_subjects)

    return subjects, interrupted, failed_subjects


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
    parser.add_argument('--term', default='SP26',
                        help='Term code (e.g., SP26, FA25, SU25)')
    parser.add_argument('--test', action='store_true',
                        help='Test mode: scrape only first 3 subjects')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from last checkpoint if available')
    parser.add_argument('--delay', type=float, default=1.0,
                        help='Delay between subject requests in seconds (default: 1.0)')
    parser.add_argument('--output', default=None,
                        help='Custom output file path (default: archive/courses_{term}.json). '
                             'Use this to scrape into a separate file without overwriting existing data.')
    parser.add_argument('--careers', nargs='+', default=None,
                        choices=['', 'UGRD', 'GRAD', 'MED', 'OTHR'],
                        help='Career levels to query (default: [""] blank = all careers). '
                             'Override only for debugging a specific career.')

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    subject_codes = args.subjects
    if args.test:
        subject_codes = SUBJECT_CODES[:3]

    logger.info("Starting UCF course scraper...")
    logger.info("Press Ctrl+C to stop and save partial results")

    subjects, interrupted, failed = scrape_all_subjects(
        headless=args.headless,
        debug=args.debug,
        subject_codes=subject_codes,
        delay=args.delay,
        term_code=args.term,
        resume=args.resume,
        careers=args.careers,
    )

    output_path = Path(args.output) if args.output else None
    save_data(subjects, term_code=args.term, output_path=output_path)

    # Only clean up checkpoint on full successful completion (no failures, not interrupted)
    if not interrupted and not failed:
        delete_checkpoint(args.term)
    elif failed:
        logger.warning(
            "Checkpoint preserved so you can resume failed subjects with: python scraper.py --resume --term %s",
            args.term,
        )
