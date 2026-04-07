"""Shared configuration for pipeline orchestration."""

import logging
from pathlib import Path
from typing import Optional


ARCHIVE_DIR = Path(__file__).parent / "archive"
DATA_DIR = Path(__file__).parent / "data"

STEP_NAMES = [
    "scrape",
    "transform",
    "filter",
    "hours",
    "coordinates",
    "load",
]

# Steps that have no file input or output (None means N/A for that step)
_NO_INPUT_STEPS = {"scrape"}
_NO_OUTPUT_STEPS = {"load"}


def input_file(term: str, step: str) -> Optional[Path]:
    """Return the expected input file for a pipeline step, or None if N/A.

    Note: 'hours' modifies buildings_filtered in place, then 'coordinates'
    reads the same file. Running 'coordinates' without 'hours' first will
    produce data missing building hours.
    """
    if step in _NO_INPUT_STEPS:
        return None
    mapping = {
        "transform": ARCHIVE_DIR / f"courses_{term}.json",
        "filter": ARCHIVE_DIR / f"buildings_derived_{term}.json",
        "hours": ARCHIVE_DIR / f"buildings_filtered_{term}.json",
        "coordinates": ARCHIVE_DIR / f"buildings_filtered_{term}.json",
        "load": ARCHIVE_DIR / f"buildings_enriched_{term}.json",
    }
    if step not in mapping:
        raise ValueError(f"Unknown pipeline step: {step}")
    return mapping[step]


def output_file(term: str, step: str) -> Optional[Path]:
    """Return the expected output file for a pipeline step, or None if N/A."""
    if step in _NO_OUTPUT_STEPS:
        return None
    mapping = {
        "scrape": ARCHIVE_DIR / f"courses_{term}.json",
        "transform": ARCHIVE_DIR / f"buildings_derived_{term}.json",
        "filter": ARCHIVE_DIR / f"buildings_filtered_{term}.json",
        "hours": ARCHIVE_DIR / f"buildings_filtered_{term}.json",
        "coordinates": ARCHIVE_DIR / f"buildings_enriched_{term}.json",
    }
    if step not in mapping:
        raise ValueError(f"Unknown pipeline step: {step}")
    return mapping[step]


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the pipeline."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )
