"""Tests for the pipeline orchestrator."""

from unittest.mock import patch, MagicMock

import pytest

from run_pipeline import get_steps_to_run, validate_step_input, run_pipeline
from pipeline_config import STEP_NAMES, input_file, output_file


class TestGetStepsToRun:
    def test_all_steps(self):
        steps = get_steps_to_run("scrape", "load")
        assert steps == STEP_NAMES

    def test_skip_scrape(self):
        steps = get_steps_to_run("transform", "load")
        assert steps[0] == "transform"
        assert "scrape" not in steps

    def test_single_step(self):
        steps = get_steps_to_run("filter", "filter")
        assert steps == ["filter"]

    def test_middle_range(self):
        steps = get_steps_to_run("filter", "coordinates")
        assert steps == ["filter", "hours", "coordinates"]

    def test_start_after_stop_raises(self):
        with pytest.raises(ValueError, match="is after"):
            get_steps_to_run("load", "scrape")


class TestValidateStepInput:
    def test_missing_input_raises(self, tmp_path):
        # transform needs courses_{term}.json which won't exist for fake term
        with pytest.raises(FileNotFoundError, match="does not exist"):
            validate_step_input("FAKE99", "transform")

    def test_existing_input_passes(self, tmp_path):
        fake_file = tmp_path / "courses_TEST99.json"
        fake_file.write_text("{}")
        with patch("pipeline_config.ARCHIVE_DIR", tmp_path):
            validate_step_input("TEST99", "transform")  # Should not raise


class TestInputOutputFiles:
    def test_transform_input(self):
        path = input_file("SP26", "transform")
        assert path.name == "courses_SP26.json"

    def test_filter_input(self):
        path = input_file("SP26", "filter")
        assert path.name == "buildings_derived_SP26.json"

    def test_scrape_output(self):
        path = output_file("SP26", "scrape")
        assert path.name == "courses_SP26.json"

    def test_coordinates_output(self):
        path = output_file("SP26", "coordinates")
        assert path.name == "buildings_enriched_SP26.json"

    def test_scrape_has_no_input(self):
        assert input_file("SP26", "scrape") is None

    def test_load_has_no_output(self):
        assert output_file("SP26", "load") is None

    def test_unknown_step_raises(self):
        with pytest.raises(ValueError, match="Unknown pipeline step"):
            input_file("SP26", "nonexistent")

    def test_unknown_output_step_raises(self):
        with pytest.raises(ValueError, match="Unknown pipeline step"):
            output_file("SP26", "nonexistent")


class TestRunPipeline:
    def test_dry_run_single_step(self):
        """Dry run of transform step should succeed without files."""
        # Dry run doesn't actually call the processor, so no files needed
        run_pipeline(
            term="FAKE99",
            start_from="transform",
            stop_after="transform",
            dry_run=True,
        )

    def test_step_failure_stops_pipeline(self):
        """If a step fails, subsequent steps should not run."""
        with patch("run_pipeline.STEP_RUNNERS", {
            "scrape": MagicMock(side_effect=RuntimeError("scrape failed")),
            "transform": MagicMock(),
        }):
            with pytest.raises(RuntimeError, match="scrape failed"):
                run_pipeline(
                    term="TEST",
                    start_from="scrape",
                    stop_after="transform",
                )

    def test_validates_input_before_step(self):
        """Steps requiring input files that don't exist should fail early."""
        with pytest.raises(FileNotFoundError):
            run_pipeline(
                term="NONEXISTENT99",
                start_from="transform",
                stop_after="transform",
            )


    def test_real_transform_step_with_fixture(self, tmp_path, sample_courses):
        """Run the transform step for real against fixture data in tmp_path."""
        import json

        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()

        # Write input file
        (archive_dir / "courses_TEST.json").write_text(json.dumps(sample_courses))

        with patch("pipeline_config.ARCHIVE_DIR", archive_dir), \
             patch("subject_to_buildings.SubjectToBuildingsProcessor.__init__",
                   lambda self, term_code="SP26": self.__dict__.update({
                       "term_code": term_code,
                       "data_dir": archive_dir,
                       "input_file": archive_dir / f"courses_{term_code}.json",
                       "output_file": archive_dir / f"buildings_derived_{term_code}.json",
                   })):
            run_pipeline(
                term="TEST",
                start_from="transform",
                stop_after="transform",
            )

        assert (archive_dir / "buildings_derived_TEST.json").exists()
        result = json.loads((archive_dir / "buildings_derived_TEST.json").read_text())
        assert "buildings" in result
        assert len(result["buildings"]) > 0

    def test_missing_output_raises_runtime_error(self, tmp_path):
        """If a step completes but its output file is missing, raise RuntimeError."""
        from pathlib import Path

        mock_runner = MagicMock()  # Does nothing, so no output file created
        # Create input file so validation passes, but output won't exist
        (tmp_path / "courses_TEST.json").write_text("{}")
        with patch("run_pipeline.STEP_RUNNERS", {"transform": mock_runner}), \
             patch("pipeline_config.ARCHIVE_DIR", tmp_path):
            with pytest.raises(RuntimeError, match="did not produce expected output"):
                run_pipeline(
                    term="TEST",
                    start_from="transform",
                    stop_after="transform",
                )

    def test_step_failure_does_not_run_subsequent(self, tmp_path):
        """Verify the second step never runs when the first fails."""
        mock_filter = MagicMock(side_effect=ValueError("filter broke"))
        mock_hours = MagicMock()
        # Create input file so validation passes
        (tmp_path / "buildings_derived_TEST.json").write_text("{}")
        with patch("run_pipeline.STEP_RUNNERS", {
            "filter": mock_filter,
            "hours": mock_hours,
        }), patch("pipeline_config.ARCHIVE_DIR", tmp_path):
            with pytest.raises(ValueError, match="filter broke"):
                run_pipeline(term="TEST", start_from="filter", stop_after="hours")
        mock_hours.assert_not_called()

    def test_dry_run_skips_input_validation(self):
        """Dry run should not check for input files."""
        run_pipeline(
            term="NONEXISTENT99",
            start_from="transform",
            stop_after="coordinates",
            dry_run=True,
        )  # Should not raise FileNotFoundError


class TestStepRunners:
    def test_run_transform_dry_run(self):
        """Dry run of transform just logs, doesn't call processor."""
        from run_pipeline import run_transform
        run_transform("FAKE", dry_run=True)  # Should not raise

    def test_run_filter_dry_run(self):
        from run_pipeline import run_filter
        run_filter("FAKE", dry_run=True)

    def test_run_hours_dry_run(self):
        from run_pipeline import run_hours
        run_hours("FAKE", dry_run=True)

    def test_run_coordinates_dry_run(self):
        from run_pipeline import run_coordinates
        run_coordinates("FAKE", dry_run=True)

    def test_run_scrape_dry_run(self):
        from run_pipeline import run_scrape
        run_scrape("FAKE", dry_run=True)


class TestStepNames:
    def test_step_count(self):
        assert len(STEP_NAMES) == 6

    def test_step_order(self):
        assert STEP_NAMES == [
            "scrape", "transform", "filter", "hours", "coordinates", "load"
        ]
