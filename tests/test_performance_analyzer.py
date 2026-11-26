
import json

import pytest

from benchmarks import performance_analyzer as analyzer


# ============================================================
# TEST DATA
# ============================================================

def create_benchmark_result(file_count):

    return {
        "status": "COMPLETED",
        "file_count": file_count,
        "records_per_file": 100,
        "total_records": file_count * 100,
        "successful": file_count,
        "skipped": 0,
        "failed": 0,
        "execution_time_seconds": file_count * 0.3,
        "average_time_per_file_seconds": 0.3,
        "throughput_files_per_second": 3.3333,
        "peak_memory_mb": 90.0,
        "success_rate_percentage": 100.0,
        "batch_status": "SUCCESS",
        "batch_duration_seconds": file_count * 0.28,
        "execution_log_tail": None
    }


def create_report(file_count, generated_at):

    return {
        "report_type": "ETL_PERFORMANCE_BENCHMARK",
        "generated_at": generated_at,
        "started_at": generated_at,
        "completed_at": generated_at,
        "total_benchmark_duration_seconds": (
            file_count * 0.3
        ),
        "records_per_file": 100,
        "benchmark_scales": [file_count],
        "results": [
            create_benchmark_result(file_count)
        ]
    }


def save_report(directory, file_count, generated_at):

    directory.mkdir(
        parents=True,
        exist_ok=True
    )

    file_path = (
        directory
        / f"performance_benchmark_{file_count}.json"
    )

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            create_report(file_count, generated_at),
            file
        )

    return file_path


# ============================================================
# REPORT DISCOVERY TESTS
# ============================================================

def test_discover_benchmark_reports(tmp_path):

    save_report(
        tmp_path,
        10,
        "2026-11-26T07:40:00+00:00"
    )

    save_report(
        tmp_path,
        50,
        "2026-11-26T07:41:00+00:00"
    )

    reports = analyzer.discover_benchmark_reports(
        tmp_path
    )

    assert len(reports) == 2

    assert all(
        report.name.startswith("performance_benchmark_")
        for report in reports
    )


def test_discover_reports_missing_directory(tmp_path):

    missing_directory = tmp_path / "missing"

    with pytest.raises(FileNotFoundError):

        analyzer.discover_benchmark_reports(
            missing_directory
        )


def test_discover_reports_empty_directory(tmp_path):

    with pytest.raises(FileNotFoundError):

        analyzer.discover_benchmark_reports(
            tmp_path
        )


# ============================================================
# REPORT VALIDATION TESTS
# ============================================================

def test_validate_valid_benchmark_report(tmp_path):

    file_path = save_report(
        tmp_path,
        10,
        "2026-11-26T07:40:00+00:00"
    )

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:

        report = json.load(file)

    results = analyzer.validate_benchmark_report(
        report,
        file_path
    )

    assert len(results) == 1

    assert results[0]["file_count"] == 10


def test_validate_report_missing_metric(tmp_path):

    report = create_report(
        10,
        "2026-11-26T07:40:00+00:00"
    )

    del report["results"][0]["peak_memory_mb"]

    with pytest.raises(ValueError):

        analyzer.validate_benchmark_report(
            report,
            tmp_path / "invalid.json"
        )


def test_validate_report_wrong_type(tmp_path):

    report = create_report(
        10,
        "2026-11-26T07:40:00+00:00"
    )

    report["report_type"] = "INVALID_REPORT"

    with pytest.raises(ValueError):

        analyzer.validate_benchmark_report(
            report,
            tmp_path / "invalid.json"
        )


def test_validate_report_inconsistent_file_count(tmp_path):

    report = create_report(
        10,
        "2026-11-26T07:40:00+00:00"
    )

    report["results"][0]["successful"] = 9

    with pytest.raises(ValueError):

        analyzer.validate_benchmark_report(
            report,
            tmp_path / "invalid.json"
        )


def test_validate_report_rejects_nan_metric(tmp_path):

    report = create_report(
        10,
        "2026-11-26T07:40:00+00:00"
    )

    report["results"][0]["peak_memory_mb"] = float("nan")

    with pytest.raises(ValueError):

        analyzer.validate_benchmark_report(
            report,
            tmp_path / "invalid.json"
        )


# ============================================================
# REPORT COLLECTION TESTS
# ============================================================

def test_collect_benchmark_results(tmp_path):

    save_report(
        tmp_path,
        10,
        "2026-11-26T07:40:00+00:00"
    )

    save_report(
        tmp_path,
        50,
        "2026-11-26T07:41:00+00:00"
    )

    files = analyzer.discover_benchmark_reports(
        tmp_path
    )

    results = analyzer.collect_benchmark_results(
        files
    )

    assert len(results) == 2

    assert results[0]["file_count"] == 10

    assert results[1]["file_count"] == 50


def test_collect_rejects_malformed_json(tmp_path):

    file_path = (
        tmp_path
        / "performance_benchmark_invalid.json"
    )

    file_path.write_text(
        '{"invalid": ',
        encoding="utf-8"
    )

    with pytest.raises(ValueError):

        analyzer.collect_benchmark_results(
            [file_path]
        )


# ============================================================
# DUPLICATE SCALE TESTS
# ============================================================

def test_select_latest_benchmark_for_duplicate_scale():

    results = [

        {
            **create_benchmark_result(10),
            "generated_at": "2026-11-26T07:40:00+00:00"
        },

        {
            **create_benchmark_result(10),
            "generated_at": "2026-11-26T08:00:00+00:00"
        }

    ]

    selected = analyzer.select_latest_results(
        results
    )

    assert len(selected) == 1

    assert (
        selected[0]["generated_at"]
        == "2026-11-26T08:00:00+00:00"
    )


# ============================================================
# PERFORMANCE COMPARISON TESTS
# ============================================================

def test_performance_comparison_calculations():

    results = [

        {
            **create_benchmark_result(10),
            "generated_at": "2026-11-26T07:40:00+00:00",
            "source_report": "benchmark_10.json"
        },

        {
            **create_benchmark_result(50),
            "generated_at": "2026-11-26T07:41:00+00:00",
            "source_report": "benchmark_50.json"
        }

    ]

    comparisons = analyzer.build_performance_comparison(
        results
    )

    assert len(comparisons) == 2

    assert (
        comparisons[0]["execution_time_growth_factor"]
        == 1.0
    )

    assert (
        comparisons[1]["execution_time_growth_factor"]
        == 5.0
    )

    assert (
        comparisons[1]["memory_change_mb"]
        == 0.0
    )


def test_generate_performance_findings():

    comparisons = [

        {
            **create_benchmark_result(10),
            "source_report": "benchmark_10.json"
        },

        {
            **create_benchmark_result(50),
            "source_report": "benchmark_50.json"
        }

    ]

    findings = analyzer.generate_performance_findings(
        comparisons
    )

    assert findings["total_files_tested"] == 60

    assert findings["total_records_tested"] == 6000

    assert findings["total_successful_files"] == 60

    assert findings["total_failed_files"] == 0

    assert (
        findings["overall_success_rate_percentage"]
        == 100.0
    )


# ============================================================
# END-TO-END REPORT GENERATION TEST
# ============================================================

def test_generate_comparison_report(tmp_path):

    reports_directory = tmp_path / "reports"

    output_path = (
        tmp_path
        / "output"
        / "comparison.json"
    )

    save_report(
        reports_directory,
        10,
        "2026-11-26T07:40:00+00:00"
    )

    save_report(
        reports_directory,
        50,
        "2026-11-26T07:41:00+00:00"
    )

    save_report(
        reports_directory,
        100,
        "2026-11-26T07:42:00+00:00"
    )

    report = analyzer.generate_comparison_report(
        report_directory=reports_directory,
        output_path=output_path
    )

    assert output_path.is_file()

    assert report["report_type"] == (
        "ETL_PERFORMANCE_COMPARISON"
    )

    assert report["baseline_file_count"] == 10

    assert len(report["comparison_results"]) == 3

    assert (
        report["performance_findings"]["total_files_tested"]
        == 160
    )

    with open(
        output_path,
        "r",
        encoding="utf-8"
    ) as file:

        saved_report = json.load(file)

    assert saved_report["performance_findings"][
        "overall_success_rate_percentage"
    ] == 100.0
