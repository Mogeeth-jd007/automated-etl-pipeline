
import math

import pandas as pd
import pytest

from src.universal.data_profiler import (
    profile_numeric_column,
    profile_dataset
)


def test_numeric_statistics():

    series = pd.Series([10, 20, 30, 40, 50])

    result = profile_numeric_column(series)

    assert result["total_count"] == 5

    assert result["valid_count"] == 5

    assert result["invalid_count"] == 0

    assert result["mean"] == 30.0

    assert result["median"] == 30.0

    assert result["minimum"] == 10.0

    assert result["maximum"] == 50.0

    assert result["q1"] == 20.0

    assert result["q2"] == 30.0

    assert result["q3"] == 40.0

    assert result["iqr"] == 20.0


def test_numeric_mode():

    series = pd.Series([10, 20, 20, 30, 30, 30])

    result = profile_numeric_column(series)

    assert result["mode"] == [30.0]


def test_multiple_modes():

    series = pd.Series([10, 10, 20, 20, 30])

    result = profile_numeric_column(series)

    assert result["mode"] == [10.0, 20.0]


def test_standard_deviation_and_variance():

    series = pd.Series([10, 20, 30, 40, 50])

    result = profile_numeric_column(series)

    assert result["standard_deviation"] == pytest.approx(
        15.8113883
    )

    assert result["variance"] == 250.0


def test_skewness():

    series = pd.Series([1, 2, 3, 4, 5])

    result = profile_numeric_column(series)

    assert result["skewness"] == pytest.approx(0.0, abs=1e-10)


def test_invalid_numeric_values():

    series = pd.Series([
        "100",
        "200",
        "invalid",
        "300",
        None
    ])

    result = profile_numeric_column(series)

    assert result["total_count"] == 5

    assert result["valid_count"] == 3

    assert result["invalid_count"] == 2

    assert result["mean"] == 200.0


def test_all_invalid_values():

    series = pd.Series([
        "invalid",
        "unknown",
        "not-a-number"
    ])

    result = profile_numeric_column(series)

    assert result["valid_count"] == 0

    assert result["invalid_count"] == 3

    assert result["mean"] is None

    assert result["median"] is None


def test_single_numeric_value():

    series = pd.Series([100])

    result = profile_numeric_column(series)

    assert result["mean"] == 100.0

    assert result["median"] == 100.0

    assert result["standard_deviation"] is None

    assert result["variance"] is None

    assert result["skewness"] is None


def test_empty_numeric_series():

    series = pd.Series([], dtype="float64")

    result = profile_numeric_column(series)

    assert result["total_count"] == 0

    assert result["valid_count"] == 0

    assert result["mean"] is None


def test_numeric_profiles_integrated_into_dataset():

    df = pd.DataFrame({
        "customer_name": [
            "Arun",
            "Meena",
            "Ravi",
            "Divya"
        ],
        "amount": [100, 200, 300, 400]
    })

    result = profile_dataset(df)

    assert "amount" in result["numeric_profiles"]

    assert "customer_name" not in result["numeric_profiles"]

    assert result["numeric_profiles"]["amount"]["mean"] == 250.0


def test_numeric_profile_preserves_original_dataframe():

    df = pd.DataFrame({
        "amount": ["100", "200", "300"],
        "customer": ["Arun", "Meena", "Ravi"]
    })

    original = df.copy(deep=True)

    profile_dataset(df)

    pd.testing.assert_frame_equal(df, original)


def test_numeric_profile_handles_infinity():

    series = pd.Series([
        100,
        200,
        float("inf"),
        float("-inf")
    ])

    result = profile_numeric_column(series)

    assert result["valid_count"] == 2

    assert result["invalid_count"] == 2

    assert result["mean"] == 150.0

    assert math.isfinite(result["mean"])
