
import argparse
import json
import math

from datetime import datetime, timezone
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_REPORT_DIRECTORY = PROJECT_ROOT / "reports"

DEFAULT_OUTPUT_PATH = (
    DEFAULT_REPORT_DIRECTORY
    / "performance_comparison_report.json"
)

REPORT_PATTERN = "performance_benchmark_*.json"

REQUIRED_METRICS = [
    "file_count",
    "total_records",
    "successful",
    "skipped",
    "failed",
    "execution_time_seconds",
    "average_time_per_file_seconds",
    "throughput_files_per_second",
    "peak_memory_mb",
    "success_rate_percentage"
]


# ============================================================
# VALIDATION
# ============================================================

def validate_benchmark_report(report, file_path):
    """Validate the structure of an individual benchmark report."""

    if not isinstance(report, dict):
        raise ValueError(
            f"Invalid JSON structure: {file_path.name}"
        )

    if report.get("report_type") != "ETL_PERFORMANCE_BENCHMARK":
        raise ValueError(
            f"Unsupported report type: {file_path.name}"
        )

    results = report.get("results")

    if not isinstance(results, list):
        raise ValueError(
            f"Results must be a list: {file_path.name}"
        )

    validated_results = []

    for result in results:

        if not isinstance(result, dict):
            raise ValueError(
                f"Invalid benchmark result in {file_path.name}"
            )

        if result.get("status") != "COMPLETED":
            continue

        for metric in REQUIRED_METRICS:

            if metric not in result:
                raise ValueError(
                    f"Missing metric '{metric}' "
                    f"in {file_path.name}"
                )

        file_count = result["file_count"]

        if (
            isinstance(file_count, bool)
            or not isinstance(file_count, int)
            or file_count <= 0
        ):
            raise ValueError(
                f"Invalid file count in {file_path.name}"
            )

        for metric in REQUIRED_METRICS[1:]:

            value = result[metric]

            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
            ):
                raise ValueError(
                    f"Invalid value for '{metric}' "
                    f"in {file_path.name}"
                )

        if (
            result["successful"]
            + result["skipped"]
            + result["failed"]
            != file_count
        ):
            raise ValueError(
                f"File count mismatch in {file_path.name}"
            )

        validated_results.append(result)

    return validated_results


# ============================================================
# REPORT DISCOVERY
# ============================================================

def discover_benchmark_reports(report_directory=None):
    """Discover existing individual benchmark JSON reports."""

    if report_directory is None:
        report_directory = DEFAULT_REPORT_DIRECTORY

    report_directory = Path(report_directory)

    if not report_directory.is_dir():
        raise FileNotFoundError(
            f"Report directory does not exist: {report_directory}"
        )

    files = sorted(
        report_directory.glob(REPORT_PATTERN)
    )

    if not files:
        raise FileNotFoundError(
            "No benchmark reports found in "
            f"{report_directory}"
        )

    return files


# ============================================================
# REPORT COLLECTION
# ============================================================

def collect_benchmark_results(report_files):
    """Load benchmark reports and collect completed results."""

    collected = []

    for file_path in report_files:

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as file:

                report = json.load(file)

        except json.JSONDecodeError as error:

            raise ValueError(
                f"Malformed JSON report: {file_path.name}"
            ) from error

        results = validate_benchmark_report(
            report,
            file_path
        )

        for result in results:

            collected.append({
                **result,
                "source_report": file_path.name,
                "generated_at": report.get("generated_at")
            })

    if not collected:
        raise ValueError(
            "No completed benchmark results were found."
        )

    return collected


# ============================================================
# DUPLICATE SCALE HANDLING
# ============================================================

def select_latest_results(results):
    """
    Select the latest completed benchmark for each file count.

    ISO-8601 timestamps are used to identify the latest report.
    """

    selected = {}

    for result in results:

        file_count = result["file_count"]

        generated_at = result.get("generated_at")

        if not isinstance(generated_at, str):
            raise ValueError(
                "Benchmark report is missing generated_at."
            )

        try:

            datetime.fromisoformat(
                generated_at.replace("Z", "+00:00")
            )

        except ValueError as error:

            raise ValueError(
                f"Invalid generated_at timestamp: {generated_at}"
            ) from error

        previous = selected.get(file_count)

        if (
            previous is None
            or generated_at > previous["generated_at"]
        ):

            selected[file_count] = result

    return sorted(
        selected.values(),
        key=lambda item: item["file_count"]
    )


# ============================================================
# PERFORMANCE COMPARISON
# ============================================================

def build_performance_comparison(results):
    """Calculate performance changes against the smallest scale."""

    baseline = results[0]

    baseline_time = baseline["execution_time_seconds"]
    baseline_throughput = baseline["throughput_files_per_second"]
    baseline_memory = baseline["peak_memory_mb"]

    comparisons = []

    for result in results:

        execution_time = result["execution_time_seconds"]
        throughput = result["throughput_files_per_second"]
        memory = result["peak_memory_mb"]

        execution_growth = (
            execution_time / baseline_time
            if baseline_time > 0
            else None
        )

        throughput_change = (
            (
                (throughput - baseline_throughput)
                / baseline_throughput
            ) * 100
            if baseline_throughput > 0
            else None
        )

        memory_change = (
            memory - baseline_memory
        )

        memory_change_percentage = (
            (memory_change / baseline_memory) * 100
            if baseline_memory > 0
            else None
        )

        average_time_change = (
            (
                (
                    result["average_time_per_file_seconds"]
                    - baseline["average_time_per_file_seconds"]
                )
                / baseline["average_time_per_file_seconds"]
            ) * 100
            if baseline["average_time_per_file_seconds"] > 0
            else None
        )

        comparisons.append({

            "file_count": result["file_count"],

            "total_records": result["total_records"],

            "successful": result["successful"],

            "skipped": result["skipped"],

            "failed": result["failed"],

            "execution_time_seconds": execution_time,

            "average_time_per_file_seconds": (
                result["average_time_per_file_seconds"]
            ),

            "throughput_files_per_second": throughput,

            "peak_memory_mb": memory,

            "success_rate_percentage": (
                result["success_rate_percentage"]
            ),

            "execution_time_growth_factor": (
                round(execution_growth, 4)
                if execution_growth is not None
                else None
            ),

            "throughput_change_percentage": (
                round(throughput_change, 2)
                if throughput_change is not None
                else None
            ),

            "average_time_change_percentage": (
                round(average_time_change, 2)
                if average_time_change is not None
                else None
            ),

            "memory_change_mb": round(
                memory_change,
                2
            ),

            "memory_change_percentage": (
                round(memory_change_percentage, 2)
                if memory_change_percentage is not None
                else None
            ),

            "source_report": result["source_report"]

        })

    return comparisons


# ============================================================
# PERFORMANCE FINDINGS
# ============================================================

def generate_performance_findings(comparisons):
    """Generate findings from measured benchmark results."""

    highest_throughput = max(
        comparisons,
        key=lambda item: item["throughput_files_per_second"]
    )

    highest_memory = max(
        comparisons,
        key=lambda item: item["peak_memory_mb"]
    )

    lowest_average_time = min(
        comparisons,
        key=lambda item: item["average_time_per_file_seconds"]
    )

    total_files = sum(
        item["file_count"]
        for item in comparisons
    )

    total_records = sum(
        item["total_records"]
        for item in comparisons
    )

    total_successful = sum(
        item["successful"]
        for item in comparisons
    )

    total_failed = sum(
        item["failed"]
        for item in comparisons
    )

    total_skipped = sum(
        item["skipped"]
        for item in comparisons
    )

    findings = {

        "total_benchmark_configurations": len(comparisons),

        "total_files_tested": total_files,

        "total_records_tested": total_records,

        "total_successful_files": total_successful,

        "total_skipped_files": total_skipped,

        "total_failed_files": total_failed,

        "overall_success_rate_percentage": round(
            total_successful / total_files * 100,
            2
        ),

        "highest_throughput": {
            "file_count": highest_throughput["file_count"],
            "files_per_second": (
                highest_throughput["throughput_files_per_second"]
            )
        },

        "highest_memory_consumption": {
            "file_count": highest_memory["file_count"],
            "memory_mb": highest_memory["peak_memory_mb"]
        },

        "lowest_average_processing_time": {
            "file_count": lowest_average_time["file_count"],
            "seconds_per_file": (
                lowest_average_time[
                    "average_time_per_file_seconds"
                ]
            )
        }

    }

    return findings


# ============================================================
# CONSOLIDATED REPORT GENERATION
# ============================================================

def generate_comparison_report(
    report_directory=None,
    output_path=None
):
    """Generate the consolidated ETL performance report."""

    if report_directory is None:
        report_directory = DEFAULT_REPORT_DIRECTORY

    if output_path is None:
        output_path = DEFAULT_OUTPUT_PATH

    print("\n")
    print("=" * 60)
    print("       ETL PERFORMANCE ANALYSIS")
    print("=" * 60)

    report_files = discover_benchmark_reports(
        report_directory
    )

    print("\nDISCOVERED BENCHMARK REPORTS")

    for file_path in report_files:
        print(file_path.name)

    collected = collect_benchmark_results(
        report_files
    )

    selected = select_latest_results(
        collected
    )

    selected.sort(
        key=lambda item: item["file_count"]
    )

    comparisons = build_performance_comparison(
        selected
    )

    findings = generate_performance_findings(
        comparisons
    )

    report = {

        "report_type": "ETL_PERFORMANCE_COMPARISON",

        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "baseline_file_count": (
            comparisons[0]["file_count"]
        ),

        "source_reports": [
            item["source_report"]
            for item in selected
        ],

        "comparison_results": comparisons,

        "performance_findings": findings

    }

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            indent=4,
            ensure_ascii=False,
            allow_nan=False
        )

    # Display comparison.

    print("\n========== PERFORMANCE COMPARISON ==========")

    for item in comparisons:

        print(
            f"\nFiles: {item['file_count']}"
        )

        print(
            "Execution time:",
            item["execution_time_seconds"]
        )

        print(
            "Throughput:",
            item["throughput_files_per_second"]
        )

        print(
            "Peak memory:",
            item["peak_memory_mb"],
            "MB"
        )

        print(
            "Throughput change:",
            item["throughput_change_percentage"],
            "%"
        )

        print(
            "Memory change:",
            item["memory_change_mb"],
            "MB"
        )

    print("\n========== PERFORMANCE FINDINGS ==========")

    for key, value in findings.items():
        print(f"{key}: {value}")

    print("\nComparison report saved:", output_path)

    print(
        "\n========== PERFORMANCE ANALYSIS COMPLETED ==========\n"
    )

    return report


# ============================================================
# COMMAND LINE INTERFACE
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="ETL Performance Comparison Analyzer"
    )

    parser.add_argument(
        "--reports-dir",
        default=str(DEFAULT_REPORT_DIRECTORY)
    )

    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH)
    )

    args = parser.parse_args()

    generate_comparison_report(
        report_directory=args.reports_dir,
        output_path=args.output
    )


if __name__ == "__main__":
    main()
