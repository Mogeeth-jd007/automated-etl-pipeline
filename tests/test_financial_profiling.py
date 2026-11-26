
from decimal import Decimal

import pandas as pd
import pytest

from src.universal.financial_profiler import (
    profile_currency_column,
    profile_percentage_column
)


# ==========================================
# CURRENCY PROFILING TESTS
# ==========================================

def test_currency_counts():

    series = pd.Series([
        "INR 100",
        "INR 200",
        "USD 300",
        "USD 400"
    ])

    result = profile_currency_column(series)

    assert result["valid_count"] == 4
    assert result["invalid_count"] == 0
    assert result["missing_count"] == 0


def test_currency_unit_detection():

    series = pd.Series([
        "INR 100",
        "USD 200",
        "EUR 300",
        "GBP 400"
    ])

    result = profile_currency_column(series)

    assert set(result["currency_units"]) == {
        "INR", "USD", "EUR", "GBP"
    }


def test_currency_statistics():

    series = pd.Series([
        "INR 100",
        "INR 200",
        "INR 300",
        "INR 400"
    ])

    result = profile_currency_column(series)

    statistics = result["unit_summary"]["INR"]["statistics"]

    assert statistics["minimum"] == 100.0
    assert statistics["maximum"] == 400.0
    assert statistics["mean"] == 250.0
    assert statistics["median"] == 250.0
    assert statistics["sum"] == 1000.0


def test_currency_statistics_are_separated_by_unit():

    series = pd.Series([
        "INR 100",
        "INR 200",
        "USD 500",
        "USD 700"
    ])

    result = profile_currency_column(series)

    assert result["unit_summary"]["INR"]["count"] == 2
    assert result["unit_summary"]["USD"]["count"] == 2

    assert (
        result["unit_summary"]["INR"]["statistics"]["sum"]
        == 300.0
    )

    assert (
        result["unit_summary"]["USD"]["statistics"]["sum"]
        == 1200.0
    )


def test_currency_missing_values():

    series = pd.Series([
        "INR 100",
        None,
        "",
        "USD 200"
    ])

    result = profile_currency_column(series)

    assert result["valid_count"] == 2
    assert result["missing_count"] == 2
    assert result["invalid_count"] == 0


def test_currency_invalid_values():

    series = pd.Series([
        "INR 100",
        "USD abc",
        "invalid",
        "EUR 300"
    ])

    result = profile_currency_column(series)

    assert result["valid_count"] == 2
    assert result["invalid_count"] == 2
    assert len(result["invalid_examples"]) == 2


def test_currency_completeness_percentage():

    series = pd.Series([
        "INR 100",
        "INR 200",
        None,
        "invalid"
    ])

    result = profile_currency_column(series)

    assert result["completeness_percentage"] == 50.0


def test_currency_validity_percentage():

    series = pd.Series([
        "INR 100",
        "INR 200",
        "invalid",
        None
    ])

    result = profile_currency_column(series)

    assert result["validity_percentage"] == 66.67


def test_currency_all_invalid():

    series = pd.Series([
        "invalid",
        "USD abc",
        "unknown"
    ])

    result = profile_currency_column(series)

    assert result["valid_count"] == 0
    assert result["invalid_count"] == 3
    assert result["currency_units"] == []
    assert result["unit_summary"] == {}


def test_currency_all_missing():

    series = pd.Series([
        None,
        pd.NA,
        ""
    ])

    result = profile_currency_column(series)

    assert result["missing_count"] == 3
    assert result["valid_count"] == 0
    assert result["invalid_count"] == 0
    assert result["validity_percentage"] is None


def test_empty_currency_series():

    series = pd.Series([], dtype="object")

    result = profile_currency_column(series)

    assert result["total_records"] == 0
    assert result["valid_count"] == 0
    assert result["currency_units"] == []
    assert result["completeness_percentage"] is None


def test_currency_negative_values():

    series = pd.Series([
        "USD -100",
        "USD 200"
    ])

    result = profile_currency_column(series)

    statistics = result["unit_summary"]["USD"]["statistics"]

    assert statistics["minimum"] == -100.0
    assert statistics["maximum"] == 200.0
    assert statistics["sum"] == 100.0


# ==========================================
# PERCENTAGE PROFILING TESTS
# ==========================================

def test_percentage_counts():

    series = pd.Series([
        "10%",
        "20%",
        "30%",
        "40%"
    ])

    result = profile_percentage_column(series)

    assert result["valid_count"] == 4
    assert result["invalid_count"] == 0
    assert result["missing_count"] == 0


def test_percentage_statistics():

    series = pd.Series([
        "10%",
        "20%",
        "30%",
        "40%"
    ])

    result = profile_percentage_column(series)

    statistics = result["percentage_statistics"]

    assert statistics["minimum"] == 10.0
    assert statistics["maximum"] == 40.0
    assert statistics["mean"] == 25.0
    assert statistics["median"] == 25.0
    assert statistics["sum"] == 100.0


def test_percentage_decimal_statistics():

    series = pd.Series([
        "10%",
        "20%",
        "30%"
    ])

    result = profile_percentage_column(series)

    statistics = result["decimal_statistics"]

    assert statistics["minimum"] == 0.1
    assert statistics["maximum"] == 0.3
    assert statistics["mean"] == pytest.approx(0.2)


def test_percentage_missing_values():

    series = pd.Series([
        "10%",
        None,
        "",
        "30%"
    ])

    result = profile_percentage_column(series)

    assert result["valid_count"] == 2
    assert result["missing_count"] == 2
    assert result["invalid_count"] == 0


def test_percentage_invalid_values():

    series = pd.Series([
        "10%",
        "invalid",
        "20%",
        "abc%"
    ])

    result = profile_percentage_column(series)

    assert result["valid_count"] == 2
    assert result["invalid_count"] == 2


def test_percentage_completeness_percentage():

    series = pd.Series([
        "10%",
        "20%",
        None,
        "invalid"
    ])

    result = profile_percentage_column(series)

    assert result["completeness_percentage"] == 50.0


def test_percentage_all_invalid():

    series = pd.Series([
        "invalid",
        "abc%",
        "unknown"
    ])

    result = profile_percentage_column(series)

    assert result["valid_count"] == 0
    assert result["invalid_count"] == 3
    assert result["percentage_statistics"]["mean"] is None


def test_percentage_all_missing():

    series = pd.Series([
        None,
        pd.NA,
        ""
    ])

    result = profile_percentage_column(series)

    assert result["missing_count"] == 3
    assert result["valid_count"] == 0
    assert result["invalid_count"] == 0


def test_empty_percentage_series():

    series = pd.Series([], dtype="object")

    result = profile_percentage_column(series)

    assert result["total_records"] == 0
    assert result["valid_count"] == 0
    assert result["percentage_statistics"]["mean"] is None


def test_percentage_zero_and_hundred():

    series = pd.Series([
        "0%",
        "100%"
    ])

    result = profile_percentage_column(series)

    statistics = result["percentage_statistics"]

    assert statistics["minimum"] == 0.0
    assert statistics["maximum"] == 100.0
    assert statistics["mean"] == 50.0


def test_percentage_negative_values():

    series = pd.Series([
        "-10%",
        "20%"
    ])

    result = profile_percentage_column(series)

    statistics = result["percentage_statistics"]

    assert statistics["minimum"] == -10.0
    assert statistics["maximum"] == 20.0


def test_currency_original_series_unchanged():

    series = pd.Series([
        "INR 100",
        "USD 200",
        "invalid"
    ])

    original = series.copy(deep=True)

    profile_currency_column(series)

    pd.testing.assert_series_equal(
        series,
        original
    )


def test_percentage_original_series_unchanged():

    series = pd.Series([
        "10%",
        "20%",
        "invalid"
    ])

    original = series.copy(deep=True)

    profile_percentage_column(series)

    pd.testing.assert_series_equal(
        series,
        original
    )


def test_currency_invalid_examples_use_row_positions():

    series = pd.Series(
        ["INR 100", "invalid"],
        index=[100, 200]
    )

    result = profile_currency_column(series)

    assert result["invalid_examples"] == [
        {"row_position": 1}
    ]
