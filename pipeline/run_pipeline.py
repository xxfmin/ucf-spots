"""
Pipeline orchestrator for ucf-spots data pipeline.

Runs all 6 pipeline steps in sequence, with support for partial runs.

Usage:
    python run_pipeline.py --term SP26
    python run_pipeline.py --term SP26 --skip-scrape
    python run_pipeline.py --term SP26 --start-from filter --stop-after hours
    python run_pipeline.py --term SP26 --dry-run
"""

import argparse
import logging
import time

from pipeline_config import STEP_NAMES, input_file, output_file, setup_logging

logger = logging.getLogger(__name__)


def run_scrape(term: str, dry_run: bool = False) -> None:
    """Step 1: Scrape UCF course data."""
    if dry_run:
        logger.info("[scrape] DRY RUN - would scrape courses for %s", term)
        return
    from scraper import scrape_all_subjects, save_data, delete_checkpoint

    subjects, interrupted, failed = scrape_all_subjects(
        headless=True, term_code=term
    )
    # Always persist whatever we have so --resume can pick it up later.
    save_data(subjects, term_code=term)

    if interrupted:
        raise SystemExit(
            "Scrape was interrupted (Ctrl-C). Refusing to continue the pipeline "
            "with partial data — re-run with --start-from scrape to resume."
        )
    if failed:
        raise SystemExit(
            f"Scrape finished with {len(failed)} failed subject(s): {failed}. "
            "Refusing to continue the pipeline with incomplete data — re-run "
            "with --start-from scrape to retry."
        )

    delete_checkpoint(term)


def run_transform(term: str, dry_run: bool = False) -> None:
    """Step 2: Transform subject-sorted to building-sorted data."""
    if dry_run:
        logger.info("[transform] DRY RUN - would transform courses for %s", term)
        return
    from subject_to_buildings import SubjectToBuildingsProcessor

    processor = SubjectToBuildingsProcessor(term_code=term)
    processor.process()


def run_filter(term: str, dry_run: bool = False) -> None:
    """Step 3: Filter buildings by room count and exclusion list."""
    if dry_run:
        logger.info("[filter] DRY RUN - would filter buildings for %s", term)
        return
    from filter_buildings import BuildingDataFilter

    filt = BuildingDataFilter(term_code=term)
    filt.process()


def run_hours(term: str, dry_run: bool = False) -> None:
    """Step 4: Add building hours."""
    if dry_run:
        logger.info("[hours] DRY RUN - would add hours for %s", term)
        return
    from add_building_hours import BuildingHoursProcessor

    processor = BuildingHoursProcessor(term_code=term)
    processor.process()


def run_coordinates(term: str, dry_run: bool = False) -> None:
    """Step 5: Add building coordinates from GeoJSON."""
    if dry_run:
        logger.info("[coordinates] DRY RUN - would add coordinates for %s", term)
        return
    from add_building_coordinates import BuildingCoordinateProcessor

    processor = BuildingCoordinateProcessor(term_code=term)
    processor.process()


def run_load(term: str, dry_run: bool = False) -> None:
    """Step 6: Load enriched data into PostgreSQL."""
    from load_to_postgres import load_data

    load_data(term=term, dry_run=dry_run)


STEP_RUNNERS = {
    "scrape": run_scrape,
    "transform": run_transform,
    "filter": run_filter,
    "hours": run_hours,
    "coordinates": run_coordinates,
    "load": run_load,
}


def get_steps_to_run(start_from: str, stop_after: str) -> list:
    """Return the list of step names to run based on start/stop flags."""
    start_idx = STEP_NAMES.index(start_from)
    stop_idx = STEP_NAMES.index(stop_after)
    if start_idx > stop_idx:
        raise ValueError(
            f"--start-from '{start_from}' is after --stop-after '{stop_after}'"
        )
    return STEP_NAMES[start_idx : stop_idx + 1]


def validate_step_input(term: str, step: str) -> None:
    """Check that the required input file exists before running a step."""
    required = input_file(term, step)
    if required is not None and not required.exists():
        raise FileNotFoundError(
            f"Step '{step}' requires {required.name} but it does not exist. "
            f"Run the previous step first."
        )


def run_pipeline(
    term: str,
    start_from: str = "scrape",
    stop_after: str = "load",
    dry_run: bool = False,
) -> None:
    """Run the pipeline from start_from through stop_after."""
    steps = get_steps_to_run(start_from, stop_after)

    logger.info("Pipeline: running steps %s for term %s", steps, term)
    if dry_run:
        logger.info("DRY RUN MODE - no data will be modified")

    for step in steps:
        # Validate input exists (skip for scrape and dry-run mode)
        if step != "scrape" and not dry_run:
            validate_step_input(term, step)

        logger.info("--- Step: %s ---", step)
        step_start = time.time()

        try:
            STEP_RUNNERS[step](term, dry_run=dry_run)
        except Exception:
            logger.error("Step '%s' failed", step, exc_info=True)
            raise

        elapsed = time.time() - step_start
        logger.info("Step '%s' completed in %.1fs", step, elapsed)

        # Validate output was created (skip for load which writes to DB)
        expected_out = output_file(term, step)
        if expected_out is not None and not dry_run and not expected_out.exists():
            raise RuntimeError(
                f"Step '{step}' did not produce expected output: {expected_out.name}"
            )

    logger.info("Pipeline complete.")


def main():
    parser = argparse.ArgumentParser(
        description="UCF Spots data pipeline orchestrator"
    )
    parser.add_argument(
        "--term", default="SP26", help="Term code (e.g., SP26, FA25, SU25)"
    )
    parser.add_argument(
        "--start-from",
        choices=STEP_NAMES,
        default="scrape",
        help="Start from this step (default: scrape)",
    )
    parser.add_argument(
        "--stop-after",
        choices=STEP_NAMES,
        default="load",
        help="Stop after this step (default: load)",
    )
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        help="Shortcut for --start-from transform",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs/outputs without modifying data",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable debug logging"
    )

    args = parser.parse_args()
    setup_logging(verbose=args.verbose)

    start_from = args.start_from
    if args.skip_scrape and start_from == "scrape":
        start_from = "transform"

    run_pipeline(
        term=args.term,
        start_from=start_from,
        stop_after=args.stop_after,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
