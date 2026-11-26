import json
import time
import uuid

from datetime import datetime, timezone
from pathlib import Path

from .universal_pipeline import run_universal_pipeline


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_INPUT_DIRECTORY = PROJECT_ROOT / "data" / "raw"

DEFAULT_REPORT_DIRECTORY = PROJECT_ROOT / "reports"


def discover_csv_files(input_directory=None):
    """Discover CSV files in the incoming directory."""

    directory = (
        Path(input_directory)
        if input_directory is not None
        else DEFAULT_INPUT_DIRECTORY
    )

    if not directory.is_absolute():
        directory = PROJECT_ROOT / directory

    if not directory.exists():
        raise FileNotFoundError(
            f"Input directory not found: {directory}"
        )

    if not directory.is_dir():
        raise NotADirectoryError(
            f"Input path is not a directory: {directory}"
        )

    return sorted(
        (
            file_path
            for file_path in directory.iterdir()
            if file_path.is_file()
            and file_path.suffix.lower() == ".csv"
        ),
        key=lambda path: path.name.lower()
    )


def generate_batch_report(summary):
    """Generate and save a permanent JSON batch report."""

    report_directory = DEFAULT_REPORT_DIRECTORY

    report_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    report_path = (
        report_directory
        / f"batch_execution_{summary['batch_id']}.json"
    )

    with open(
        report_path,
        "w",
        encoding="utf-8"
    ) as report_file:

        json.dump(
            summary,
            report_file,
            indent=4,
            ensure_ascii=False
        )

    return str(report_path)


def run_batch_pipeline(input_directory=None):
    """Process all discovered CSV files independently."""

    batch_id = str(uuid.uuid4())

    started_at = datetime.now(timezone.utc)

    start_timer = time.perf_counter()

    print("\n")
    print("=" * 60)
    print("       UNIVERSAL ETL BATCH PROCESSOR")
    print("=" * 60)

    files = discover_csv_files(input_directory)

    directory = (
        Path(input_directory)
        if input_directory is not None
        else DEFAULT_INPUT_DIRECTORY
    )

    if not directory.is_absolute():
        directory = PROJECT_ROOT / directory

    summary = {
        "batch_id": batch_id,
        "status": "RUNNING",
        "input_directory": str(directory),
        "started_at": started_at.isoformat(),
        "completed_at": None,
        "duration_seconds": 0,
        "total_files": len(files),
        "successful": 0,
        "skipped": 0,
        "failed": 0,
        "results": []
    }

    print("\n========== BATCH DISCOVERY ==========")

    print("Batch ID:", batch_id)
    print("Input directory:", directory)
    print("Discovered CSV files:", len(files))

    if not files:
        print("No CSV files found.")

    for index, file_path in enumerate(files, start=1):

        print("\n")
        print("=" * 60)
        print(f"BATCH FILE {index}/{len(files)}")
        print("File:", file_path.name)
        print("=" * 60)

        try:

            result = run_universal_pipeline(
                str(file_path)
            )

            status = result.get(
                "status",
                "UNKNOWN"
            )

            file_result = {
                "file": file_path.name,
                "status": status,
                "execution_id": result.get("execution_id")
            }

            if status == "SUCCESS":

                summary["successful"] += 1

            elif status == "SKIPPED_DUPLICATE":

                summary["skipped"] += 1

            else:

                summary["failed"] += 1

                file_result["error"] = (
                    f"Unexpected pipeline status: {status}"
                )

            summary["results"].append(file_result)

        except Exception as error:

            summary["failed"] += 1

            summary["results"].append({
                "file": file_path.name,
                "status": "FAILED",
                "exception_type": type(error).__name__,
                "error": str(error)
            })

            print("\nBATCH PROCESSING ERROR")
            print("File:", file_path.name)
            print("Exception:", type(error).__name__)
            print("Error:", error)

            print(
                "Continuing with the next file."
            )

    # Finalize batch execution.

    completed_at = datetime.now(timezone.utc)

    duration = time.perf_counter() - start_timer

    summary["completed_at"] = completed_at.isoformat()

    summary["duration_seconds"] = round(
        duration,
        4
    )

    summary["status"] = (
        "COMPLETED_WITH_ERRORS"
        if summary["failed"] > 0
        else "SUCCESS"
    )

    # Generate permanent JSON report.

    print("\n========== GENERATING BATCH REPORT ==========")

    report_path = generate_batch_report(summary)

    summary["report_path"] = report_path

    print("Batch report saved:", report_path)

    # Final terminal summary.

    print("\n")
    print("=" * 60)
    print("       BATCH EXECUTION SUMMARY")
    print("=" * 60)

    print("Batch ID:", summary["batch_id"])
    print("Batch status:", summary["status"])

    print("Total files:", summary["total_files"])
    print("Successful:", summary["successful"])
    print("Skipped duplicates:", summary["skipped"])
    print("Failed:", summary["failed"])

    print(
        "Duration:",
        summary["duration_seconds"],
        "seconds"
    )

    print("\n========== FILE EXECUTION DETAILS ==========")

    for result in summary["results"]:

        print(
            f"{result['file']} | {result['status']}"
        )

    print("\nJSON Report:", report_path)

    print("\n========== BATCH PROCESSING COMPLETED ==========")

    return summary
