"""Live integration test: multi-career scraping must return all career levels.

UCF PeopleSoft does NOT honor a blank Course Career as "all" -- it filters
to undergraduate only. scraper.scrape_subject_with_retry works around this by
querying each level in CAREER_LEVELS (UGRD + GRAD) and merging the results.

This test verifies the merged behavior against UCF's live PeopleSoft search by
scraping a multi-career subject and asserting that both undergraduate
(course numbers 1xxx-4xxx) and graduate (5xxx-7xxx) courses come back.

Run with:
    pytest tests/test_scraper_career.py -v -m integration
"""

from typing import Optional

import pytest

from scraper import setup_driver, scrape_subject_with_retry


# Subjects that reliably offer both undergrad and grad sections at UCF.
# Tried in order; the test passes as soon as one yields both careers.
CANDIDATE_SUBJECTS = ["PSY", "EEL", "STA"]


def _career_of(course_number: str) -> Optional[str]:
    """Return 'undergrad', 'grad', or None based on UCF course-number ranges."""
    digits = "".join(c for c in course_number if c.isdigit())
    if not digits:
        return None
    first = digits[0]
    if first in "1234":
        return "undergrad"
    if first in "567":
        return "grad"
    return None


@pytest.mark.integration
@pytest.mark.slow
def test_multi_career_scrape_returns_all_careers():
    """scrape_subject_with_retry must merge UGRD and GRAD courses for mixed subjects."""
    try:
        driver = setup_driver(headless=True)
    except Exception as e:
        pytest.skip(f"Selenium/Chrome unavailable: {e}")

    try:
        attempted = []
        for code in CANDIDATE_SUBJECTS:
            courses = scrape_subject_with_retry(driver, code, debug=False)
            if not courses:
                attempted.append(f"{code}=no-results")
                continue

            careers = {_career_of(c.number) for c in courses}
            careers.discard(None)
            attempted.append(f"{code}={sorted(careers)}")

            if {"undergrad", "grad"}.issubset(careers):
                return  # success: merged scrape returned both career levels

        pytest.fail(
            "Multi-career scrape did not yield both undergraduate and "
            "graduate courses for any candidate subject. Attempts: "
            + ", ".join(attempted)
        )
    finally:
        driver.quit()
