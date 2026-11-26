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


