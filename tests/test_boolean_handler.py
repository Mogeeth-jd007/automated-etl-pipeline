import pandas as pd
import pytest

from universal.boolean_handler import (
    parse_boolean_value,
    convert_boolean_series,
    infer_boolean_type,
    is_boolean_column_name
)


@pytest.mark.parametrize(
    "value",
    [
        "true",
        "TRUE",
        "yes",
        "YES",
        "y",
        "t",
        "on",
        "enabled",
        "1",
        "  True  "
    ]
)
def test_true_values(value):

    assert parse_boolean_value(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "false",
        "FALSE",
        "no",
        "NO",
        "n",
        "f",
        "off",
        "disabled",
        "0",
        "  False  "
    ]
)
def test_false_values(value):

    assert parse_boolean_value(value) is False


@pytest.mark.parametrize(
    "value",
    [
        "maybe",
        "unknown",
        "2",
        "-1",
        "1.0",
        "",
        "   ",
        None,
        pd.NA
    ]
)
def test_invalid_boolean_values(value):

    assert pd.isna(parse_boolean_value(value))


@pytest.mark.parametrize(
    "column",
    [
        "active",
        "enabled",
        "verified",
        "approved",
        "is_active",
        "has_access",
        "can_edit",
        "was_deleted",
        "should_notify",
        "payment_flag"
    ]
)
def test_boolean_column_names(column):

    assert is_boolean_column_name(column)


@pytest.mark.parametrize(
    "column",
    [
        "quantity",
        "price",
        "marks",
        "product_id",
        "status_code"
    ]
)
def test_non_boolean_column_names(column):

    assert not is_boolean_column_name(column)


def test_textual_boolean_inference():

    series = pd.Series([
        "YES",
        "NO",
        "ON",
        "OFF",
        "maybe"
    ])

    assert infer_boolean_type(
        "status",
        series
    )


def test_binary_boolean_inference():

    series = pd.Series([
        "1", "0", "1", "0"
    ])

    assert infer_boolean_type(
        "is_active",
        series
    )


def test_binary_numeric_protection():

    series = pd.Series([
        "1", "0", "1", "0"
    ])

    assert not infer_boolean_type(
        "quantity",
        series
    )


def test_insufficient_boolean_matches():

    series = pd.Series([
        "YES",
        "NO",
        "maybe",
        "unknown",
        "invalid"
    ])

    assert not infer_boolean_type(
        "is_active",
        series
    )


def test_empty_boolean_series():

    series = pd.Series(
        [None, pd.NA],
        dtype="string"
    )

    assert not infer_boolean_type(
        "is_active",
        series
    )


def test_boolean_series_conversion():

    series = pd.Series([
        "YES",
        "NO",
        "1",
        "0",
        "maybe",
        None
    ])

    result = convert_boolean_series(series)

    assert result.dropna().tolist() == [
        True,
        False,
        True,
        False
    ]

    assert result.isna().sum() == 2

    assert str(result.dtype) == "boolean"


def test_index_preservation():

    series = pd.Series(
        ["YES", "NO", "invalid"],
        index=[10, 20, 30]
    )

    result = convert_boolean_series(series)

    assert result.index.equals(series.index)


def test_original_series_unchanged():

    series = pd.Series([
        "YES",
        "NO",
        "invalid"
    ])

    original = series.copy(deep=True)

    convert_boolean_series(series)

    pd.testing.assert_series_equal(
        series,
        original
    )
