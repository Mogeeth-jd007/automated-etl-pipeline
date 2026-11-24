from decimal import Decimal

import pandas as pd
import pytest

from universal.financial_handler import (
    parse_financial_value,
    infer_financial_type,
    convert_financial_series,
    generate_currency_column_name
)


@pytest.mark.parametrize(
    "value, amount, unit",
    [
        ("\u20b945,000", "45000", "INR"),
        ("INR 1,00,000", "100000", "INR"),
        ("USD 250", "250", "USD"),
        ("250 USD", "250", "USD"),
        ("$750", "750", "DOLLAR_UNSPECIFIED"),
        ("\u20ac2,500", "2500", "EUR"),
        ("\u00a3500", "500", "GBP"),
        ("CAD 100", "100", "CAD"),
        ("AUD 200", "200", "AUD"),
        ("JPY 5000", "5000", "JPY"),
        ("USD -500", "-500", "USD"),
        ("usd 100.50", "100.50", "USD")
    ]
)
def test_currency_parsing(value, amount, unit):

    result = parse_financial_value(value)

    assert result is not None

    assert result["data_type"] == "currency"

    assert result["value"] == Decimal(amount)

    assert result["unit"] == unit


@pytest.mark.parametrize(
    "value, expected",
    [
        ("10%", "0.1"),
        ("15%", "0.15"),
        ("12.5%", "0.125"),
        ("100%", "1"),
        ("0%", "0"),
        ("-5%", "-0.05"),
        ("150%", "1.5"),
        (" 25% ", "0.25")
    ]
)
def test_percentage_parsing(value, expected):

    result = parse_financial_value(value)

    assert result is not None

    assert result["data_type"] == "percentage"

    assert result["value"] == Decimal(expected)

    assert result["unit"] == "percentage"


@pytest.mark.parametrize(
    "value",
    [
        "USD abc",
        "abc%",
        "$",
        "%",
        "",
        None,
        pd.NA,
        "45000",
        "USD 12,34",
        "10%%",
        "(USD 100)",
        "abc"
    ]
)
def test_invalid_financial_values(value):

    assert parse_financial_value(value) is None


def test_currency_type_inference():

    series = pd.Series([
        "USD 100",
        "USD 200",
        "INR 300",
        "EUR 400",
        "invalid"
    ])

    assert infer_financial_type(series) == "currency"


def test_percentage_type_inference():

    series = pd.Series([
        "10%",
        "20%",
        "30%",
        "40%",
        "invalid"
    ])

    assert infer_financial_type(series) == "percentage"


def test_mixed_financial_types():

    series = pd.Series([
        "USD 100",
        "USD 200",
        "USD 300",
        "USD 400",
        "10%"
    ])

    assert infer_financial_type(series) is None


def test_insufficient_financial_matches():

    series = pd.Series([
        "USD 100",
        "USD 200",
        "invalid",
        "invalid",
        "invalid"
    ])

    assert infer_financial_type(series) is None


def test_empty_financial_series():

    series = pd.Series(
        [None, pd.NA],
        dtype="string"
    )

    assert infer_financial_type(series) is None


def test_currency_series_conversion():

    series = pd.Series([
        "USD 100",
        "INR 200",
        "$750",
        "invalid",
        None
    ])

    amounts, units = convert_financial_series(
        series,
        "currency"
    )

    assert amounts.dropna().tolist() == [
        "100", "200", "750"
    ]

    assert units.dropna().tolist() == [
        "USD", "INR", "DOLLAR_UNSPECIFIED"
    ]

    assert amounts.isna().sum() == 2

    assert units.isna().sum() == 2


def test_percentage_series_conversion():

    series = pd.Series([
        "10%",
        "12.5%",
        "0%",
        "invalid"
    ])

    amounts, units = convert_financial_series(
        series,
        "percentage"
    )

    assert amounts.dropna().tolist() == [
        "0.1", "0.125", "0"
    ]

    assert units.dropna().tolist() == [
        "percentage",
        "percentage",
        "percentage"
    ]

    assert amounts.isna().sum() == 1


def test_currency_column_name():

    result = generate_currency_column_name(
        "revenue",
        ["revenue", "product"]
    )

    assert result == "revenue_currency"


def test_currency_column_name_collision():

    result = generate_currency_column_name(
        "revenue",
        [
            "revenue",
            "revenue_currency",
            "revenue_currency_2"
        ]
    )

    assert result == "revenue_currency_3"


def test_index_preservation():

    series = pd.Series(
        ["USD 100", "INR 200"],
        index=[10, 20]
    )

    amounts, units = convert_financial_series(
        series,
        "currency"
    )

    assert amounts.index.equals(series.index)

    assert units.index.equals(series.index)


def test_original_series_unchanged():

    series = pd.Series([
        "USD 100",
        "INR 200",
        "invalid"
    ])

    original = series.copy(deep=True)

    convert_financial_series(series, "currency")

    pd.testing.assert_series_equal(
        series,
        original
    )
