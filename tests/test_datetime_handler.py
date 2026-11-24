import pandas as pd
import pytest

from universal.datetime_handler import (
    parse_datetime_value,
    parse_datetime_series,
    infer_datetime_type
)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("2026-11-24", "2026-11-24"),
        ("2026/11/24", "2026-11-24"),
        ("2026.11.24", "2026-11-24"),
        ("24/11/2026", "2026-11-24"),
        ("11/24/2026", "2026-11-24"),
        ("24-Nov-2026", "2026-11-24"),
        ("24-November-2026", "2026-11-24"),
        ("24 Nov 2026", "2026-11-24"),
        ("24 November 2026", "2026-11-24"),
        ("Nov 24, 2026", "2026-11-24"),
        ("November 24, 2026", "2026-11-24"),
        ("2024-02-29", "2024-02-29"),
        ("05/05/2026", "2026-05-05"),
        (" 2026-11-24 ", "2026-11-24")
    ]
)
def test_valid_date_formats(value, expected):

    result = parse_datetime_value(value)

    assert result == pd.Timestamp(expected)


@pytest.mark.parametrize(
    "value",
    [
        "01/02/2026",
        "12/11/2026",
        "2026-02-30",
        "2026-02-29",
        "32/01/2026",
        "2026-13-01",
        "abc",
        "45000",
        "",
        "   ",
        None,
        pd.NA,
        "24/11/26",
        "2026-11-24T25:00:00"
    ]
)
def test_invalid_or_ambiguous_dates(value):

    assert pd.isna(parse_datetime_value(value))


@pytest.mark.parametrize(
    "value, expected",
    [
        (
            "2026-11-24 14:30:00",
            "2026-11-24 14:30:00"
        ),
        (
            "2026-11-24T14:30:00",
            "2026-11-24 14:30:00"
        ),
        (
            "2026-11-24T14:30",
            "2026-11-24 14:30:00"
        ),
        (
            "2026-11-24T14:30:00.123456",
            "2026-11-24 14:30:00.123456"
        )
    ]
)
def test_naive_timestamps(value, expected):

    result = parse_datetime_value(value)

    assert result == pd.Timestamp(expected)

    assert result.tzinfo is None


@pytest.mark.parametrize(
    "value, expected",
    [
        (
            "2026-11-24T14:30:00+05:30",
            "2026-11-24T09:00:00Z"
        ),
        (
            "2026-11-24T14:30:00Z",
            "2026-11-24T14:30:00Z"
        ),
        (
            "2026-11-24T14:30:00-05:00",
            "2026-11-24T19:30:00Z"
        ),
        (
            "2026-11-24T01:00:00+05:30",
            "2026-11-23T19:30:00Z"
        )
    ]
)
def test_timezone_normalization(value, expected):

    result = parse_datetime_value(value)

    assert result == pd.Timestamp(expected)

    assert str(result.tzinfo) == "UTC"


def test_datetime_type_inference():

    series = pd.Series([
        "2026-11-24",
        "2026-11-25",
        "26-Nov-2026",
        "27/11/2026",
        "invalid"
    ])

    assert infer_datetime_type(series)


def test_insufficient_date_matches():

    series = pd.Series([
        "2026-11-24",
        "2026-11-25",
        "invalid",
        "abc",
        "12345"
    ])

    assert not infer_datetime_type(series)


def test_numeric_values_not_dates():

    series = pd.Series([
        "100",
        "200",
        "45000"
    ])

    assert not infer_datetime_type(series)


def test_empty_datetime_series():

    series = pd.Series(
        [None, pd.NA],
        dtype="string"
    )

    assert not infer_datetime_type(series)


def test_datetime_series_conversion():

    series = pd.Series([
        "2026-11-24",
        "25/11/2026",
        "01/02/2026",
        "invalid",
        None
    ])

    result = parse_datetime_series(series)

    assert result.dropna().tolist() == [
        pd.Timestamp("2026-11-24"),
        pd.Timestamp("2026-11-25")
    ]

    assert result.isna().sum() == 3


def test_index_preservation():

    series = pd.Series(
        ["2026-11-24", "invalid"],
        index=[10, 20]
    )

    result = parse_datetime_series(series)

    assert result.index.equals(series.index)


def test_original_series_unchanged():

    series = pd.Series([
        "2026-11-24",
        "24/11/2026",
        "invalid"
    ])

    original = series.copy(deep=True)

    parse_datetime_series(series)

    pd.testing.assert_series_equal(
        series,
        original
    )
