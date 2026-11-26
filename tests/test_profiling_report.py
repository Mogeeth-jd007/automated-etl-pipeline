
import json

import pandas as pd
import pytest

from universal.report_generator import (
    generate_profiling_report,
    build_profiling_observations
)


@pytest.fixture
def sample_dataset():

    return pd.DataFrame({
        "customer_id": [
            "C001",
            "C002",
            "C003",
            "C004",
            "C005"
        ],
        "customer_name": [
            "Arun",
            "Meena",
            "Ravi",
            "Divya",
            "Kiran"
        ],
        "quantity": [5, 10, 15, 20, 25],
        "revenue": [
            "INR 1000",
            "INR 2000",
            "INR 3000",
            "INR 4000",
            "INR 5000"
        ],
        "discount": [
            "10%",
            "20%",
            "30%",
            "40%",
            "50%"
        ],
        "is_active": [
            "YES",
            "NO",
            "YES",
            "NO",
            "YES"
        ]
    })


def test_profiling_report_file_created(
    sample_dataset,
    tmp_path
):

    result = generate_profiling_report(
        sample_dataset,
        "test_dataset",
        output_dir=tmp_path
    )

    assert result["profiling_report"]

    assert result["profiling_report"].endswith(
        "test_dataset_profiling_report.json"
    )


def test_profiling_report_is_valid_json(
    sample_dataset,
    tmp_path
):

    result = generate_profiling_report(
        sample_dataset,
        "test_dataset",
        output_dir=tmp_path
    )

    with open(
        result["profiling_report"],
        encoding="utf-8"
    ) as file:

        report = json.load(file)

    assert isinstance(report, dict)


def test_profiling_report_structure(
    sample_dataset,
    tmp_path
):

    result = generate_profiling_report(
        sample_dataset,
        "test_dataset",
        output_dir=tmp_path
    )

    report = result["report"]

    assert report["report_type"] == (
        "DATASET_PROFILING_REPORT"
    )

    assert report["dataset"] == "test_dataset"

    assert "generated_at" in report
    assert "dataset_summary" in report
    assert "column_profiles" in report
    assert "profiling_sections" in report
    assert "quality_observations" in report


def test_dataset_summary(
    sample_dataset,
    tmp_path
):

    result = generate_profiling_report(
        sample_dataset,
        "test_dataset",
        output_dir=tmp_path
    )

    summary = result["report"]["dataset_summary"]

    assert summary["total_records"] == 5
    assert summary["total_columns"] == 6


def test_all_profiling_sections_included(
    sample_dataset,
    tmp_path
):

    result = generate_profiling_report(
        sample_dataset,
        "test_dataset",
        output_dir=tmp_path
    )

    sections = result["report"]["profiling_sections"]

    expected_sections = {
        "numeric_profiles",
        "categorical_profiles",
        "identifier_profiles",
        "contact_profiles",
        "date_profiles",
        "boolean_profiles",
        "currency_profiles",
        "percentage_profiles",
        "missing_profiles"
    }

    assert expected_sections.issubset(sections.keys())


def test_currency_and_percentage_profiles_in_report(
    sample_dataset,
    tmp_path
):

    result = generate_profiling_report(
        sample_dataset,
        "test_dataset",
        output_dir=tmp_path
    )

    sections = result["report"]["profiling_sections"]

    assert "revenue" in sections["currency_profiles"]
    assert "discount" in sections["percentage_profiles"]


def test_report_contains_quality_observations(
    tmp_path
):

    df = pd.DataFrame({
        "customer": ["Arun", None, "Ravi"],
        "quantity": [10, 20, 30]
    })

    result = generate_profiling_report(
        df,
        "missing_dataset",
        output_dir=tmp_path
    )

    observations = result["report"]["quality_observations"]

    assert any(
        item["category"] == "MISSING_VALUES"
        for item in observations
    )


def test_duplicate_records_are_reported():

    profile = {
        "dataset_summary": {
            "total_records": 5,
            "completeness_score": 100,
            "duplicate_records": 2
        },
        "column_profiles": {},
        "numeric_profiles": {},
        "currency_profiles": {},
        "percentage_profiles": {},
        "date_profiles": {},
        "boolean_profiles": {},
        "contact_profiles": {}
    }

    observations = build_profiling_observations(profile)

    assert any(
        item["category"] == "DUPLICATE_RECORDS"
        for item in observations
    )


def test_original_dataframe_is_preserved(
    sample_dataset,
    tmp_path
):

    original = sample_dataset.copy(deep=True)

    generate_profiling_report(
        sample_dataset,
        "test_dataset",
        output_dir=tmp_path
    )

    pd.testing.assert_frame_equal(
        sample_dataset,
        original
    )


def test_custom_output_directory(
    sample_dataset,
    tmp_path
):

    custom_directory = tmp_path / "custom_reports"

    result = generate_profiling_report(
        sample_dataset,
        "test_dataset",
        output_dir=custom_directory
    )

    assert custom_directory.exists()

    assert (
        custom_directory
        / "test_dataset_profiling_report.json"
    ).is_file()


def test_invalid_dataset_input(tmp_path):

    with pytest.raises(TypeError):

        generate_profiling_report(
            ["invalid"],
            "test_dataset",
            output_dir=tmp_path
        )


def test_empty_dataset_name(sample_dataset, tmp_path):

    with pytest.raises(ValueError):

        generate_profiling_report(
            sample_dataset,
            " ",
            output_dir=tmp_path
        )
