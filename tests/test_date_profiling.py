
import pandas as pd
import pytest

from src.universal.data_profiler import (
    profile_date_column,
    profile_dataset
)


REFERENCE_TIME = "2026-11-26T12:00:00Z"


def test_valid_date_profiling():

    series = pd.Series([
        "2026-01-10",
        "2026-01-11",
        "2026-01-12"
    ])

    result = profile_date_column(
        series,
        reference_time=REFERENCE_TIME
    )

    assert result["valid_count"] == 3
    assert result["invalid_count"] == 0
    assert result["missing_count"] == 0
    assert result["validity_rate_percent"] == 100.0


def test_invalid_date_profiling():

    series = pd.Series([
        "2026-01-10",
        "not-a-date",
        "2026-01-12"
    ])

    result = profile_date_column(
        series,
        reference_time=REFERENCE_TIME
    )

    assert result["valid_count"] == 2
    assert result["invalid_count"] == 1
    assert result["missing_count"] == 0
    assert len(result["invalid_examples"]) == 1


def test_missing_date_values():

    series = pd.Series([
        "2026-01-10",
        None,
        "",
        "2026-01-12"
    ])

    result = profile_date_column(
        series,
        reference_time=REFERENCE_TIME
    )

    assert result["valid_count"] == 2
    assert result["missing_count"] == 2
    assert result["invalid_count"] == 0


def test_earliest_and_latest_dates():

    series = pd.Series([
        "2026-01-15",
        "2026-01-10",
        "2026-01-20",
        "2026-01-12"
    ])

    result = profile_date_column(
        series,
        reference_time=REFERENCE_TIME
    )

    assert result["earliest_date"] == "2026-01-10T00:00:00"

    assert result["latest_date"] == "2026-01-20T00:00:00"


def test_date_range_calculation():

    series = pd.Series([
        "2026-01-01",
        "2026-01-06",
        "2026-01-11"
    ])

    result = profile_date_column(
        series,
        reference_time=REFERENCE_TIME
    )

    assert result["date_range_days"] == 10.0


def test_unique_date_count():

    series = pd.Series([
        "2026-01-10",
        "2026-01-10",
        "2026-01-11",
        "2026-01-11"
    ])

    result = profile_date_column(
        series,
        reference_time=REFERENCE_TIME
    )

    assert result["unique_date_count"] == 2


def test_future_date_detection():

    series = pd.Series([
        "2026-11-20",
        "2026-11-25",
        "2026-11-27",
        "2026-12-01"
    ])

    result = profile_date_column(
        series,
        reference_time=REFERENCE_TIME
    )

    assert result["future_date_count"] == 2


def test_all_dates_are_future():

    series = pd.Series([
        "2026-12-01",
        "2026-12-05"
    ])

    result = profile_date_column(
        series,
        reference_time=REFERENCE_TIME
    )

    assert result["future_date_count"] == 2


def test_all_dates_are_invalid():

    series = pd.Series([
        "invalid",
        "not-a-date",
        "2026-02-30"
    ])

    result = profile_date_column(
        series,
        reference_time=REFERENCE_TIME
    )

    assert result["valid_count"] == 0
    assert result["invalid_count"] == 3
    assert result["earliest_date"] is None
    assert result["latest_date"] is None
    assert result["date_range_days"] is None


def test_all_dates_are_missing():

    series = pd.Series([
        None,
        "",
        "   "
    ])

    result = profile_date_column(
        series,
        reference_time=REFERENCE_TIME
    )

    assert result["missing_count"] == 3
    assert result["valid_count"] == 0
    assert result["invalid_count"] == 0
    assert result["validity_rate_percent"] is None


def test_empty_date_series():

    series = pd.Series([], dtype="object")

    result = profile_date_column(
        series,
        reference_time=REFERENCE_TIME
    )

    assert result["total_records"] == 0
    assert result["valid_count"] == 0
    assert result["missing_count"] == 0
    assert result["unique_date_count"] == 0


def test_multiple_supported_date_formats():

    series = pd.Series([
        "2026-11-24",
        "2026/11/24",
        "24-Nov-2026",
        "November 24, 2026"
    ])

    result = profile_date_column(
        series,
        reference_time=REFERENCE_TIME
    )

    assert result["valid_count"] == 4
    assert result["invalid_count"] == 0
    assert result["unique_date_count"] == 1


def test_ambiguous_numeric_dates_are_invalid():

    series = pd.Series([
        "01/02/2026",
        "12/11/2026"
    ])

    result = profile_date_column(
        series,
        reference_time=REFERENCE_TIME
    )

    assert result["valid_count"] == 0
    assert result["invalid_count"] == 2


def test_invalid_reference_time():

    series = pd.Series([
        "2026-01-10"
    ])

    with pytest.raises(ValueError):

        profile_date_column(
            series,
            reference_time="invalid-reference"
        )


def test_date_profiling_preserves_original_series():

    series = pd.Series([
        "2026-01-10",
        "invalid",
        None
    ])

    original = series.copy(deep=True)

    profile_date_column(
        series,
        reference_time=REFERENCE_TIME
    )

    pd.testing.assert_series_equal(
        series,
        original
    )


def test_date_profiling_integrated():

    df = pd.DataFrame({
        "transaction_id": [
            "T001",
            "T002",
            "T003",
            "T004",
            "T005"
        ],
        "transaction_date": [
            "2026-11-20",
            "2026-11-21",
            "2026-11-22",
            "2026-11-23",
            "invalid"
        ],
        "amount": [
            100,
            200,
            300,
            400,
            500
        ]
    })

    result = profile_dataset(
        df,
        reference_time=REFERENCE_TIME
    )

    assert "date_profiles" in result

    assert "transaction_date" in result["date_profiles"]

    date_profile = result["date_profiles"]["transaction_date"]

    assert date_profile["valid_count"] == 4
    assert date_profile["invalid_count"] == 1


def test_date_profiling_preserves_original_dataframe():

    df = pd.DataFrame({
        "transaction_date": [
            "2026-11-20",
            "2026-11-21",
            "invalid"
        ],
        "amount": [100, 200, 300]
    })

    original = df.copy(deep=True)

    profile_dataset(
        df,
        reference_time=REFERENCE_TIME
    )

    pd.testing.assert_frame_equal(
        df,
        original
    )


def test_existing_profiles_are_preserved():

    df = pd.DataFrame({
        "customer_id": ["C001", "C002", "C003", "C004"],
        "customer_name": ["Arun", "Meena", "Ravi", "Divya"],
        "email": [
            "arun@example.com",
            "meena@example.com",
            "ravi@example.com",
            "divya@example.com"
        ],
        "transaction_date": [
            "2026-11-20",
            "2026-11-21",
            "2026-11-22",
            "2026-11-23"
        ],
        "amount": [100, 200, 300, 400]
    })

    result = profile_dataset(
        df,
        reference_time=REFERENCE_TIME
    )

    assert "dataset_summary" in result
    assert "column_profiles" in result
    assert "numeric_profiles" in result
    assert "categorical_profiles" in result
    assert "identifier_profiles" in result
    assert "contact_profiles" in result
    assert "date_profiles" in result
    assert "missing_profiles" in result
