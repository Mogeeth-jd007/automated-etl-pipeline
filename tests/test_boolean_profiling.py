
import pandas as pd
import pytest

from src.universal.data_profiler import (
    profile_boolean_column,
    profile_dataset
)


def test_true_and_false_counts():
    series = pd.Series(["YES", "NO", "TRUE", "FALSE", "1", "0"])
    result = profile_boolean_column(series)

    assert result["true_count"] == 3
    assert result["false_count"] == 3
    assert result["valid_count"] == 6
    assert result["invalid_count"] == 0


def test_boolean_percentages():
    series = pd.Series(["YES", "YES", "YES", "NO"])
    result = profile_boolean_column(series)

    assert result["true_percentage"] == 75.0
    assert result["false_percentage"] == 25.0


def test_missing_boolean_values():
    series = pd.Series(["YES", "NO", None, ""])
    result = profile_boolean_column(series)

    assert result["true_count"] == 1
    assert result["false_count"] == 1
    assert result["missing_count"] == 2
    assert result["invalid_count"] == 0


def test_invalid_boolean_values():
    series = pd.Series(["YES", "NO", "maybe", "unknown"])
    result = profile_boolean_column(series)

    assert result["valid_count"] == 2
    assert result["invalid_count"] == 2
    assert len(result["invalid_examples"]) == 2


def test_all_true_values():
    series = pd.Series(["YES", "TRUE", "1", "ON"])
    result = profile_boolean_column(series)

    assert result["true_count"] == 4
    assert result["false_count"] == 0
    assert result["dominant_value"] is True
    assert result["single_value_column"] is True


def test_all_false_values():
    series = pd.Series(["NO", "FALSE", "0", "OFF"])
    result = profile_boolean_column(series)

    assert result["true_count"] == 0
    assert result["false_count"] == 4
    assert result["dominant_value"] is False
    assert result["single_value_column"] is True


def test_mixed_boolean_values():
    series = pd.Series(["YES", "NO", "TRUE", "FALSE"])
    result = profile_boolean_column(series)

    assert result["single_value_column"] is False


def test_boolean_column_with_only_invalid_values():
    series = pd.Series(["maybe", "unknown", "invalid"])
    result = profile_boolean_column(series)

    assert result["valid_count"] == 0
    assert result["invalid_count"] == 3
    assert result["true_percentage"] is None
    assert result["false_percentage"] is None
    assert result["dominant_value"] is None
    assert result["single_value_column"] is False


def test_boolean_column_with_only_missing_values():
    series = pd.Series([None, "", "   "])
    result = profile_boolean_column(series)

    assert result["missing_count"] == 3
    assert result["valid_count"] == 0
    assert result["invalid_count"] == 0
    assert result["completeness_percentage"] == 0.0


def test_empty_boolean_series():
    series = pd.Series([], dtype="object")
    result = profile_boolean_column(series)

    assert result["total_records"] == 0
    assert result["true_count"] == 0
    assert result["false_count"] == 0
    assert result["true_percentage"] is None
    assert result["false_percentage"] is None


def test_boolean_completeness_percentage():
    series = pd.Series(["YES", "NO", None, "maybe"])
    result = profile_boolean_column(series)

    assert result["completeness_percentage"] == 50.0


def test_boolean_invalid_examples_use_row_positions():
    series = pd.Series(["YES", "invalid"], index=[100, 200])
    result = profile_boolean_column(series)

    assert result["invalid_examples"] == [
        {"row_position": 1}
    ]


def test_boolean_profiling_integrated():
    df = pd.DataFrame({
        "customer_id": ["C001", "C002", "C003", "C004"],
        "is_active": ["YES", "NO", "YES", "NO"],
        "amount": [100, 200, 300, 400]
    })

    result = profile_dataset(df)

    assert "boolean_profiles" in result
    assert "is_active" in result["boolean_profiles"]

    boolean_profile = result["boolean_profiles"]["is_active"]

    assert boolean_profile["true_count"] == 2
    assert boolean_profile["false_count"] == 2
    assert boolean_profile["valid_count"] == 4


def test_boolean_profiling_with_invalid_values_integrated():
    df = pd.DataFrame({
        "is_active": [
            "YES",
            "NO",
            "maybe",
            "YES",
            "NO"
        ]
    })

    result = profile_dataset(df)

    boolean_profile = result["boolean_profiles"]["is_active"]

    assert boolean_profile["true_count"] == 2
    assert boolean_profile["false_count"] == 2
    assert boolean_profile["invalid_count"] == 1
    assert boolean_profile["valid_count"] == 4


def test_boolean_profiling_preserves_original_dataframe():
    df = pd.DataFrame({
        "is_active": ["YES", "NO", "invalid"]
    })

    original = df.copy(deep=True)

    profile_dataset(df)

    pd.testing.assert_frame_equal(df, original)


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
        "is_active": ["YES", "NO", "YES", "NO"],
        "amount": [100, 200, 300, 400]
    })

    result = profile_dataset(
        df,
        reference_time="2026-11-26T12:00:00Z"
    )

    expected_sections = {
        "dataset_summary",
        "column_profiles",
        "numeric_profiles",
        "categorical_profiles",
        "identifier_profiles",
        "contact_profiles",
        "date_profiles",
        "boolean_profiles",
        "missing_profiles"
    }

    assert expected_sections.issubset(result.keys())


def test_boolean_percentage_denominator_excludes_invalid_and_missing():
    series = pd.Series(["YES", "NO", "YES", "invalid", None])
    result = profile_boolean_column(series)

    assert result["true_percentage"] == 66.67
    assert result["false_percentage"] == 33.33


def test_boolean_profile_uses_nullable_boolean_values():
    series = pd.Series(
        [True, False, pd.NA],
        dtype="boolean"
    )

    result = profile_boolean_column(series)

    assert result["true_count"] == 1
    assert result["false_count"] == 1
    assert result["missing_count"] == 1
