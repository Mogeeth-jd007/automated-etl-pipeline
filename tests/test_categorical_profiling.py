
import pandas as pd
import pytest

from src.universal.data_profiler import (
    profile_categorical_column,
    profile_dataset
)


def test_categorical_frequency():

    series = pd.Series([
        "Chennai",
        "Madurai",
        "Chennai",
        "Chennai",
        "Madurai"
    ])

    result = profile_categorical_column(series)

    assert result["total_count"] == 5
    assert result["non_null_count"] == 5
    assert result["unique_count"] == 2

    assert result["mode"] == ["Chennai"]

    assert result["top_values"][0] == {
        "value": "Chennai",
        "count": 3,
        "percentage": 60.0
    }


def test_multiple_modes():

    series = pd.Series([
        "IT",
        "HR",
        "IT",
        "HR"
    ])

    result = profile_categorical_column(series)

    assert set(result["mode"]) == {"IT", "HR"}


def test_cardinality_ratio():

    series = pd.Series([
        "IT",
        "HR",
        "Finance",
        "IT"
    ])

    result = profile_categorical_column(series)

    assert result["unique_count"] == 3

    assert result["cardinality_ratio"] == 0.75


def test_missing_categorical_values():

    series = pd.Series([
        "Chennai",
        None,
        "Madurai",
        "Chennai",
        None
    ])

    result = profile_categorical_column(series)

    assert result["total_count"] == 5

    assert result["non_null_count"] == 3

    assert result["missing_count"] == 2

    assert result["unique_count"] == 2


def test_top_n_limit():

    series = pd.Series([
        "A", "A", "A",
        "B", "B",
        "C", "C",
        "D", "E"
    ])

    result = profile_categorical_column(
        series,
        top_n=2
    )

    assert len(result["top_values"]) == 2

    assert result["top_values"][0]["value"] == "A"


def test_empty_categorical_series():

    series = pd.Series([], dtype="object")

    result = profile_categorical_column(series)

    assert result["total_count"] == 0

    assert result["unique_count"] == 0

    assert result["cardinality_ratio"] is None

    assert result["mode"] == []


def test_all_missing_categorical_values():

    series = pd.Series([
        None,
        None,
        None
    ])

    result = profile_categorical_column(series)

    assert result["missing_count"] == 3

    assert result["unique_count"] == 0

    assert result["top_values"] == []


def test_invalid_top_n():

    series = pd.Series(["IT", "HR"])

    with pytest.raises(ValueError):

        profile_categorical_column(
            series,
            top_n=0
        )


def test_categorical_profiles_integrated():

    df = pd.DataFrame({
        "customer": [
            "Arun",
            "Meena",
            "Ravi",
            "Arun"
        ],
        "amount": [
            100,
            200,
            300,
            400
        ]
    })

    result = profile_dataset(df)

    assert "customer" in result["categorical_profiles"]

    assert "amount" not in result["categorical_profiles"]

    assert (
        result["categorical_profiles"]["customer"]["unique_count"]
        == 3
    )


def test_original_dataframe_is_not_modified():

    df = pd.DataFrame({
        "city": [
            "Chennai",
            "Madurai",
            "Chennai"
        ]
    })

    original = df.copy(deep=True)

    profile_dataset(df)

    pd.testing.assert_frame_equal(df, original)


def test_categorical_profiles_preserve_missing_values():

    df = pd.DataFrame({
        "department": [
            "IT",
            None,
            "HR",
            "IT"
        ]
    })

    result = profile_dataset(df)

    profile = result["categorical_profiles"]["department"]

    assert profile["total_count"] == 4

    assert profile["missing_count"] == 1

    assert profile["unique_count"] == 2
