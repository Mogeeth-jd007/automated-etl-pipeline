
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import psutil


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIRECTORY = PROJECT_ROOT / "src"
CONFIG_FILE = PROJECT_ROOT / "config.json"

REPORT_DIRECTORY = PROJECT_ROOT / "reports"

DEFAULT_SCALES = [10, 50, 100]
DEFAULT_RECORDS_PER_FILE = 100
DEFAULT_TIMEOUT = 900

SUMMARY_MARKER = "BENCHMARK_SUMMARY="


# ============================================================
# SYNTHETIC DATA GENERATION
# ============================================================

def generate_benchmark_dataset(
    output_directory,
    file_count,
    records_per_file=DEFAULT_RECORDS_PER_FILE
):
    """Generate independent CSV files for benchmarking."""

    output_directory = Path(output_directory)

    output_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    for file_number in range(1, file_count + 1):

        data = pd.DataFrame({

            "transaction_id": [
                f"T{file_number:03d}_{row:06d}"
                for row in range(1, records_per_file + 1)
            ],

            "customer_name": [
                f"Customer_{file_number}_{row}"
                for row in range(1, records_per_file + 1)
            ],

            "amount": [
                1000 + (row * 25) + file_number
                for row in range(1, records_per_file + 1)
            ],

            "transaction_date": pd.date_range(
                start="2026-01-01",
                periods=records_per_file,
                freq="D"
            ).strftime("%Y-%m-%d"),

            "email": [
                f"customer{file_number}_{row}@example.com"
                for row in range(1, records_per_file + 1)
            ],

            "is_active": [
                True if row % 2 == 0 else False
                for row in range(1, records_per_file + 1)
            ]

        })

        file_path = (
            output_directory
            / f"benchmark_{file_number:03d}.csv"
        )

        data.to_csv(
            file_path,
            index=False
        )

    return {
        "files_generated": file_count,
        "records_per_file": records_per_file,
        "total_records": file_count * records_per_file
    }


# ============================================================
# ISOLATED PROJECT CREATION
# ============================================================

def create_isolated_project(sandbox_directory):
    """Create a temporary copy of the ETL source."""

    sandbox_directory = Path(sandbox_directory)

    sandbox_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    if not SOURCE_DIRECTORY.is_dir():
        raise FileNotFoundError(
            f"Source directory not found: {SOURCE_DIRECTORY}"
        )

    if not CONFIG_FILE.is_file():
        raise FileNotFoundError(
            f"Configuration file not found: {CONFIG_FILE}"
        )

    shutil.copytree(
        SOURCE_DIRECTORY,
        sandbox_directory / "src",
        ignore=shutil.ignore_patterns(
            "__pycache__",
            "*.pyc"
        )
    )

    shutil.copy2(
        CONFIG_FILE,
        sandbox_directory / "config.json"
    )

    return sandbox_directory


# ============================================================
# MEMORY MONITORING
# ============================================================

def get_process_tree_memory(process):
    """Measure RSS memory used by the process and its children."""

    try:

        parent = psutil.Process(process.pid)

        processes = [parent]

        processes.extend(
            parent.children(recursive=True)
        )

        total_memory = 0

        for child in processes:

            try:

                total_memory += (
                    child.memory_info().rss
                )

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied
            ):
                continue

        return total_memory

    except (
        psutil.NoSuchProcess,
        psutil.AccessDenied
    ):
        return 0


# ============================================================
# SUBPROCESS EXECUTION
# ============================================================

def execute_isolated_batch(
    sandbox_directory,
    input_directory,
    timeout_seconds=DEFAULT_TIMEOUT
):
    """Execute the real batch processor in the isolated project."""

    sandbox_directory = Path(sandbox_directory)
    input_directory = Path(input_directory)

    script = (
        "import sys, json\n"
        f"sys.path.insert(0, {str(sandbox_directory / 'src')!r})\n"
        "from universal.batch_processor import run_batch_pipeline\n"
        f"result = run_batch_pipeline({str(input_directory)!r})\n"
        f"print({SUMMARY_MARKER!r} + json.dumps(result), flush=True)\n"
    )

    log_path = sandbox_directory / "benchmark_execution.log"

    start_time = time.perf_counter()

    peak_memory = 0

    with open(
        log_path,
        "w",
        encoding="utf-8"
    ) as log_file:

        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                script
            ],
            cwd=str(sandbox_directory),
            stdout=log_file,
            stderr=subprocess.STDOUT
        )

        timed_out = False

        try:

            while process.poll() is None:

                current_memory = get_process_tree_memory(
                    process
                )

                peak_memory = max(
                    peak_memory,
                    current_memory
                )

                if (
                    time.perf_counter() - start_time
                    > timeout_seconds
                ):

                    timed_out = True

                    process.kill()

                    break

                time.sleep(0.05)

            process.wait()

        finally:

            if process.poll() is None:
                process.kill()
                process.wait()

    duration = time.perf_counter() - start_time

    log_text = log_path.read_text(
        encoding="utf-8",
        errors="replace"
    )

    if timed_out:

        raise TimeoutError(
            f"Benchmark exceeded {timeout_seconds} seconds."
        )

    if process.returncode != 0:

        raise RuntimeError(
            "Isolated ETL execution failed.\n"
            + log_text[-4000:]
        )

    summary_line = next(
        (
            line[len(SUMMARY_MARKER):]
            for line in reversed(log_text.splitlines())
            if line.startswith(SUMMARY_MARKER)
        ),
        None
    )

    if summary_line is None:

        raise RuntimeError(
            "Batch execution summary was not found.\n"
            + log_text[-4000:]
        )

    summary = json.loads(summary_line)

    return {
        "duration_seconds": round(duration, 4),
        "peak_memory_mb": round(
            peak_memory / (1024 * 1024),
            2
        ),
        "batch_summary": summary,
        "execution_log_tail": (
            log_text[-4000:]
            if summary.get("failed", 0) > 0
            else None
        )
    }


# ============================================================
# SINGLE SCALE BENCHMARK
# ============================================================

def benchmark_scale(
    file_count,
    records_per_file,
    timeout_seconds=DEFAULT_TIMEOUT
):
    """Benchmark one CSV file-count configuration."""

    print("\n")
    print("=" * 60)
    print(f"BENCHMARK: {file_count} CSV FILES")
    print("=" * 60)

    with tempfile.TemporaryDirectory(
        prefix="etl_benchmark_"
    ) as temporary_directory:

        sandbox_directory = (
            Path(temporary_directory)
            / "isolated_project"
        )

        create_isolated_project(
            sandbox_directory
        )

        input_directory = (
            sandbox_directory
            / "data"
            / "raw"
            / "benchmark_input"
        )

        generation = generate_benchmark_dataset(
            input_directory,
            file_count,
            records_per_file
        )

        print(
            "Generated files:",
            generation["files_generated"]
        )

        print(
            "Total records:",
            generation["total_records"]
        )

        execution = execute_isolated_batch(
            sandbox_directory,
            input_directory,
            timeout_seconds
        )

        summary = execution["batch_summary"]

        successful = summary.get("successful", 0)
        skipped = summary.get("skipped", 0)
        failed = summary.get("failed", 0)

        duration = execution["duration_seconds"]

        throughput = (
            successful / duration
            if duration > 0
            else 0
        )

        success_rate = (
            successful / file_count * 100
            if file_count > 0
            else 0
        )

        result = {
            "file_count": file_count,
            "records_per_file": records_per_file,
            "total_records": generation["total_records"],
            "successful": successful,
            "skipped": skipped,
            "failed": failed,
            "execution_time_seconds": duration,
            "average_time_per_file_seconds": round(
                duration / file_count,
                4
            ),
            "throughput_files_per_second": round(
                throughput,
                4
            ),
            "peak_memory_mb": execution["peak_memory_mb"],
            "success_rate_percentage": round(
                success_rate,
                2
            ),
            "batch_status": summary.get("status"),
            "batch_duration_seconds": summary.get(
                "duration_seconds"
            ),
            "execution_log_tail": execution["execution_log_tail"]
        }

        print("\nBENCHMARK RESULTS")

        for key, value in result.items():

            if key != "execution_log_tail":
                print(f"{key}: {value}")

        return result


# ============================================================
# COMPLETE BENCHMARK EXECUTION
# ============================================================

def run_benchmarks(
    scales=None,
    records_per_file=DEFAULT_RECORDS_PER_FILE,
    timeout_seconds=DEFAULT_TIMEOUT
):
    """Execute all requested benchmark configurations."""

    if scales is None:
        scales = DEFAULT_SCALES

    if not scales:
        raise ValueError(
            "At least one benchmark scale is required."
        )

    if any(
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
        for value in scales
    ):
        raise ValueError(
            "Benchmark scales must be positive integers."
        )

    if (
        isinstance(records_per_file, bool)
        or not isinstance(records_per_file, int)
        or records_per_file <= 0
    ):
        raise ValueError(
            "Records per file must be a positive integer."
        )

    results = []

    benchmark_started = datetime.now(
        timezone.utc
    )

    overall_timer = time.perf_counter()

    print("\n")
    print("=" * 60)
    print("       ETL PERFORMANCE BENCHMARK")
    print("=" * 60)

    for file_count in scales:

        try:

            result = benchmark_scale(
                file_count,
                records_per_file,
                timeout_seconds
            )

            results.append({
                "status": "COMPLETED",
                **result
            })

        except Exception as error:

            print("\nBENCHMARK FAILED")
            print("File count:", file_count)
            print("Error:", error)

            results.append({
                "status": "FAILED",
                "file_count": file_count,
                "exception_type": type(error).__name__,
                "error": str(error)
            })

    total_duration = time.perf_counter() - overall_timer

    completed_at = datetime.now(
        timezone.utc
    )

    report = {
        "report_type": "ETL_PERFORMANCE_BENCHMARK",
        "generated_at": completed_at.isoformat(),
        "started_at": benchmark_started.isoformat(),
        "completed_at": completed_at.isoformat(),
        "total_benchmark_duration_seconds": round(
            total_duration,
            4
        ),
        "records_per_file": records_per_file,
        "benchmark_scales": scales,
        "results": results
    }

    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    report_path = (
        REPORT_DIRECTORY
        / (
            "performance_benchmark_"
            + completed_at.strftime("%Y%m%d_%H%M%S")
            + ".json"
        )
    )

    with open(
        report_path,
        "w",
        encoding="utf-8"
    ) as report_file:

        json.dump(
            report,
            report_file,
            indent=4,
            ensure_ascii=False
        )

    print("\n")
    print("=" * 60)
    print("       PERFORMANCE BENCHMARK SUMMARY")
    print("=" * 60)

    for result in results:

        print(
            f"{result['file_count']} files: "
            f"{result['status']}"
        )

    print(
        "\nTotal benchmark duration:",
        report["total_benchmark_duration_seconds"],
        "seconds"
    )

    print("Benchmark report:", report_path)

    return report


# ============================================================
# COMMAND LINE INTERFACE
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="Universal ETL Performance Benchmark"
    )

    parser.add_argument(
        "--scales",
        nargs="+",
        type=int,
        default=DEFAULT_SCALES,
        help="Number of CSV files to benchmark"
    )

    parser.add_argument(
        "--records-per-file",
        type=int,
        default=DEFAULT_RECORDS_PER_FILE
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT
    )

    args = parser.parse_args()

    run_benchmarks(
        scales=args.scales,
        records_per_file=args.records_per_file,
        timeout_seconds=args.timeout
    )


if __name__ == "__main__":
    main()
