import pandas as pd
import pytest

from universal.numeric_handler import (
    clean_numeric_value,
    clean_numeric_series
)


@pytest.mark.parametrize(
    "original, expected",
    [
        ("45000", "45000"),
        ("45,000", "45000"),
        ("1,00,000", "100000"),
        ("1,234.56", "1234.56"),
        ("-5,000", "-5000"),
        ("+250", "+250"),
        ("0", "0"),
        ("2.5e3", "2.5e3"),
        ("12,34,567", "1234567"),
        ("1,234,567", "1234567"),
        (" 1500 ", "1500"),
        (".5", ".5"),
        ("-0.25", "-0.25"),
        ("100.50", "100.50")
    ]
)
def test_valid_numeric_formats(original, expected):

    assert clean_numeric_value(original) == expected


@pytest.mark.parametrize(
    "value",
    [
        "12,34",
        "1,2,3",
        "abc",
        "",
        "   ",
        None,
        pd.NA,
        "inf",
        "-inf",
        "1.2.3",
        "1,23,45",
        "USD 100"
    ]
)
def test_invalid_numeric_formats(value):

    assert pd.isna(clean_numeric_value(value))


def test_numeric_series_conversion():

    series = pd.Series([
        "45,000",
        "1,00,000",
        "1,234.56",
        "12,34",
        "-500",
        None
    ])

    result = clean_numeric_series(series)

    assert result.dropna().tolist() == [
        45000,
        100000,
        1234.56,
        -500
    ]

    assert result.isna().sum() == 2

    assert pd.api.types.is_numeric_dtype(result)


def test_scientific_notation():

    series = pd.Series([
        "2.5e3",
        "1e2",
        "5e-1"
    ])

    result = clean_numeric_series(series)

    assert result.tolist() == [
        2500,
        100,
        0.5
    ]


def test_zero_preservation():

    series = pd.Series([
        "0",
        "0.0",
        "-0"
    ])

    result = clean_numeric_series(series)

    assert result.tolist() == [0, 0, 0]

    assert result.isna().sum() == 0


def test_index_preservation():

    series = pd.Series(
        ["100", "200", "invalid"],
        index=[10, 20, 30]
    )

    result = clean_numeric_series(series)

    assert result.index.equals(series.index)


def test_original_series_unchanged():

    series = pd.Series([
        "45,000",
        "12,34",
        "1500"
    ])

    original = series.copy(deep=True)

    clean_numeric_series(series)

    pd.testing.assert_series_equal(
        series,
        original
    )
