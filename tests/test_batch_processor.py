import json
import sys

from datetime import datetime
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from universal import batch_processor


def test_discover_csv_files(tmp_path):

    (tmp_path / "zebra.csv").write_text("id\n1")
    (tmp_path / "apple.csv").write_text("id\n2")
    (tmp_path / "notes.txt").write_text("ignored")
    (tmp_path / "data.json").write_text("{}")

    files = batch_processor.discover_csv_files(tmp_path)

    assert [file.name for file in files] == [
        "apple.csv",
        "zebra.csv"
    ]


def test_discover_csv_files_missing_directory(tmp_path):

    missing_directory = tmp_path / "missing"

    with pytest.raises(FileNotFoundError):
        batch_processor.discover_csv_files(
            missing_directory
        )


def test_generate_batch_report(tmp_path, monkeypatch):

    monkeypatch.setattr(
        batch_processor,
        "DEFAULT_REPORT_DIRECTORY",
        tmp_path
    )

    summary = {
        "batch_id": "test-batch-001",
        "status": "SUCCESS",
        "started_at": "2026-11-26T07:00:00+00:00",
        "completed_at": "2026-11-26T07:00:05+00:00",
        "duration_seconds": 5.0,
        "total_files": 2,
        "successful": 2,
        "skipped": 0,
        "failed": 0,
        "results": [
            {
                "file": "first.csv",
                "status": "SUCCESS",
                "execution_id": "execution-001"
            },
            {
                "file": "second.csv",
                "status": "SUCCESS",
                "execution_id": "execution-002"
            }
        ]
    }

    report_path = batch_processor.generate_batch_report(
        summary
    )

    report_file = Path(report_path)

    assert report_file.exists()
    assert report_file.name == (
        "batch_execution_test-batch-001.json"
    )

    with open(
        report_file,
        encoding="utf-8"
    ) as file:

        report = json.load(file)

    assert report["batch_id"] == "test-batch-001"
    assert report["status"] == "SUCCESS"
    assert report["total_files"] == 2
    assert report["successful"] == 2
    assert report["skipped"] == 0
    assert report["failed"] == 0
    assert len(report["results"]) == 2


def test_batch_execution_and_failure_isolation(
    tmp_path,
    monkeypatch
):

    files = [
        tmp_path / "success.csv",
        tmp_path / "duplicate.csv",
        tmp_path / "failure.csv"
    ]

    monkeypatch.setattr(
        batch_processor,
        "DEFAULT_REPORT_DIRECTORY",
        tmp_path / "reports"
    )

    monkeypatch.setattr(
        batch_processor,
        "discover_csv_files",
        lambda directory=None: files
    )

    def mock_pipeline(file_path):

        name = Path(file_path).name

        if name == "success.csv":

            return {
                "status": "SUCCESS",
                "execution_id": "execution-001"
            }

        if name == "duplicate.csv":

            return {
                "status": "SKIPPED_DUPLICATE",
                "execution_id": None
            }

        if name == "failure.csv":

            raise ValueError("SIMULATED_FILE_FAILURE")

    monkeypatch.setattr(
        batch_processor,
        "run_universal_pipeline",
        mock_pipeline
    )

    summary = batch_processor.run_batch_pipeline(
        tmp_path
    )

    assert summary["total_files"] == 3
    assert summary["successful"] == 1
    assert summary["skipped"] == 1
    assert summary["failed"] == 1

    assert summary["status"] == "COMPLETED_WITH_ERRORS"

    assert len(summary["results"]) == 3

    assert summary["results"][0]["status"] == "SUCCESS"

    assert (
        summary["results"][1]["status"]
        == "SKIPPED_DUPLICATE"
    )

    assert summary["results"][2]["status"] == "FAILED"

    assert (
        summary["results"][2]["error"]
        == "SIMULATED_FILE_FAILURE"
    )

    assert summary["results"][2]["exception_type"] == "ValueError"

    assert Path(summary["report_path"]).exists()

    with open(
        summary["report_path"],
        encoding="utf-8"
    ) as file:

        report = json.load(file)

    assert report["total_files"] == 3
    assert report["successful"] == 1
    assert report["skipped"] == 1
    assert report["failed"] == 1

    assert len(report["results"]) == 3


def test_empty_batch_generates_report(
    tmp_path,
    monkeypatch
):

    report_directory = tmp_path / "reports"

    monkeypatch.setattr(
        batch_processor,
        "DEFAULT_REPORT_DIRECTORY",
        report_directory
    )

    summary = batch_processor.run_batch_pipeline(
        tmp_path
    )

    assert summary["total_files"] == 0
    assert summary["successful"] == 0
    assert summary["skipped"] == 0
    assert summary["failed"] == 0

    assert summary["status"] == "SUCCESS"

    assert Path(summary["report_path"]).exists()

    with open(
        summary["report_path"],
        encoding="utf-8"
    ) as file:

        report = json.load(file)

    assert report["results"] == []
    assert report["total_files"] == 0



def test_batch_continues_after_failure(
    tmp_path,
    monkeypatch
):
    """Verify that a failed file does not stop later files."""

    files = [
        tmp_path / "failure.csv",
        tmp_path / "recovery.csv"
    ]

    monkeypatch.setattr(
        batch_processor,
        "DEFAULT_REPORT_DIRECTORY",
        tmp_path / "reports"
    )

    monkeypatch.setattr(
        batch_processor,
        "discover_csv_files",
        lambda directory=None: files
    )

    processed_files = []

    def mock_pipeline(file_path):

        name = Path(file_path).name

        processed_files.append(name)

        if name == "failure.csv":
            raise ValueError("SIMULATED_EXTRACTION_FAILURE")

        return {
            "status": "SUCCESS",
            "execution_id": "recovery-execution-001"
        }

    monkeypatch.setattr(
        batch_processor,
        "run_universal_pipeline",
        mock_pipeline
    )

    summary = batch_processor.run_batch_pipeline(
        tmp_path
    )

    assert processed_files == [
        "failure.csv",
        "recovery.csv"
    ]

    assert summary["total_files"] == 2
    assert summary["successful"] == 1
    assert summary["failed"] == 1
    assert summary["skipped"] == 0

    assert summary["status"] == "COMPLETED_WITH_ERRORS"

    assert summary["results"][0]["status"] == "FAILED"
    assert summary["results"][1]["status"] == "SUCCESS"

    assert (
        summary["results"][0]["error"]
        == "SIMULATED_EXTRACTION_FAILURE"
    )

    assert Path(summary["report_path"]).exists()


def test_batch_handles_multiple_failures(
    tmp_path,
    monkeypatch
):
    """Verify multiple failures do not interrupt batch execution."""

    files = [
        tmp_path / "failure_one.csv",
        tmp_path / "success.csv",
        tmp_path / "failure_two.csv",
        tmp_path / "recovery.csv"
    ]

    monkeypatch.setattr(
        batch_processor,
        "DEFAULT_REPORT_DIRECTORY",
        tmp_path / "reports"
    )

    monkeypatch.setattr(
        batch_processor,
        "discover_csv_files",
        lambda directory=None: files
    )

    processed_files = []

    def mock_pipeline(file_path):

        name = Path(file_path).name

        processed_files.append(name)

        if name == "failure_one.csv":
            raise ValueError("SIMULATED_FAILURE_ONE")

        if name == "failure_two.csv":
            raise RuntimeError("SIMULATED_FAILURE_TWO")

        return {
            "status": "SUCCESS",
            "execution_id": f"execution-{name}"
        }

    monkeypatch.setattr(
        batch_processor,
        "run_universal_pipeline",
        mock_pipeline
    )

    summary = batch_processor.run_batch_pipeline(
        tmp_path
    )

    assert processed_files == [
        "failure_one.csv",
        "success.csv",
        "failure_two.csv",
        "recovery.csv"
    ]

    assert summary["total_files"] == 4
    assert summary["successful"] == 2
    assert summary["failed"] == 2
    assert summary["skipped"] == 0

    assert summary["status"] == "COMPLETED_WITH_ERRORS"

    assert summary["results"][0]["status"] == "FAILED"
    assert summary["results"][1]["status"] == "SUCCESS"
    assert summary["results"][2]["status"] == "FAILED"
    assert summary["results"][3]["status"] == "SUCCESS"

    assert (
        summary["results"][0]["error"]
        == "SIMULATED_FAILURE_ONE"
    )

    assert (
        summary["results"][2]["error"]
        == "SIMULATED_FAILURE_TWO"
    )

    assert (
        summary["results"][0]["exception_type"]
        == "ValueError"
    )

    assert (
        summary["results"][2]["exception_type"]
        == "RuntimeError"
    )

    assert Path(summary["report_path"]).exists()


import json


def test_batch_report_accuracy_after_failures(
    tmp_path,
    monkeypatch
):
    """Verify batch JSON report accurately records failures and successes."""

    files = [
        tmp_path / "failed.csv",
        tmp_path / "successful.csv"
    ]

    monkeypatch.setattr(
        batch_processor,
        "DEFAULT_REPORT_DIRECTORY",
        tmp_path / "reports"
    )

    monkeypatch.setattr(
        batch_processor,
        "discover_csv_files",
        lambda directory=None: files
    )

    def mock_pipeline(file_path):

        if Path(file_path).name == "failed.csv":
            raise ValueError("SIMULATED_REPORT_FAILURE")

        return {
            "status": "SUCCESS",
            "execution_id": "successful-execution-001"
        }

    monkeypatch.setattr(
        batch_processor,
        "run_universal_pipeline",
        mock_pipeline
    )

    summary = batch_processor.run_batch_pipeline(
        tmp_path
    )

    report_path = Path(summary["report_path"])

    assert report_path.exists()

    with open(
        report_path,
        "r",
        encoding="utf-8"
    ) as file:
        report = json.load(file)

    assert report["batch_id"] == summary["batch_id"]
    assert report["status"] == "COMPLETED_WITH_ERRORS"
    assert report["total_files"] == 2
    assert report["successful"] == 1
    assert report["failed"] == 1
    assert report["skipped"] == 0

    assert len(report["results"]) == 2

    assert report["results"][0]["file"] == "failed.csv"
    assert report["results"][0]["status"] == "FAILED"
    assert report["results"][0]["exception_type"] == "ValueError"

    assert (
        report["results"][0]["error"]
        == "SIMULATED_REPORT_FAILURE"
    )

    assert report["results"][1]["file"] == "successful.csv"
    assert report["results"][1]["status"] == "SUCCESS"

    assert (
        report["results"][1]["execution_id"]
        == "successful-execution-001"
    )


def test_failed_file_can_be_reprocessed_after_correction(
    tmp_path,
    monkeypatch
):
    """Verify failed files can be retried successfully after correction."""

    test_file = tmp_path / "recovery_test.csv"

    test_file.write_text(
        "id,name,amount\n1,INVALID\n",
        encoding="utf-8"
    )

    monkeypatch.setattr(
        batch_processor,
        "DEFAULT_REPORT_DIRECTORY",
        tmp_path / "reports"
    )

    monkeypatch.setattr(
        batch_processor,
        "discover_csv_files",
        lambda directory=None: [test_file]
    )

    execution_count = 0

    def mock_pipeline(file_path):

        nonlocal execution_count

        execution_count += 1

        if execution_count == 1:
            raise ValueError("SIMULATED_INITIAL_FAILURE")

        return {
            "status": "SUCCESS",
            "execution_id": "recovery-success-001"
        }

    monkeypatch.setattr(
        batch_processor,
        "run_universal_pipeline",
        mock_pipeline
    )

    # FIRST BATCH: Initial failure.

    first_summary = batch_processor.run_batch_pipeline(
        tmp_path
    )

    assert first_summary["failed"] == 1
    assert first_summary["successful"] == 0

    assert (
        first_summary["results"][0]["status"]
        == "FAILED"
    )

    # CORRECT THE FILE.

    test_file.write_text(
        "id,name,amount\n1,Arun,1000\n",
        encoding="utf-8"
    )

    # SECOND BATCH: Retry corrected file.

    second_summary = batch_processor.run_batch_pipeline(
        tmp_path
    )

    assert second_summary["total_files"] == 1
    assert second_summary["successful"] == 1
    assert second_summary["failed"] == 0

    assert second_summary["status"] == "SUCCESS"

    assert (
        second_summary["results"][0]["status"]
        == "SUCCESS"
    )

    assert (
        second_summary["results"][0]["execution_id"]
        == "recovery-success-001"
    )

    assert execution_count == 2

