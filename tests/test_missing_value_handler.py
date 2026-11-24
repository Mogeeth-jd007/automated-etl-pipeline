import pandas as pd
import pytest

from universal.missing_value_handler import (
    normalize_missing_values
)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "NULL",
        "null",
        "None",
        "NaN",
        "N/A",
        "  NULL  ",
        None,
        pd.NA
    ]
)
def test_missing_value_markers(value):

    df = pd.DataFrame({
        "price": [value]
    }, dtype="string")

    result = normalize_missing_values(df)

    assert pd.isna(result["price"].iloc[0])


@pytest.mark.parametrize(
    "value",
    ["NA", "0", "45000", "Laptop"]
)
def test_meaningful_values_preserved(value):

    df = pd.DataFrame({
        "value": [value]
    })

    result = normalize_missing_values(df)

    assert result["value"].iloc[0] == value


def test_identifier_preservation():

    df = pd.DataFrame({
        "product_id": [
            "001",
            "002",
            "NA",
            "NULL",
            ""
        ]
    })

    result = normalize_missing_values(df)

    assert result["product_id"].dropna().tolist() == [
        "001", "002", "NA", "NULL"
    ]

    assert result["product_id"].isna().sum() == 1


def test_numeric_columns_preserved():

    df = pd.DataFrame({
        "quantity": [0, 10, 20]
    })

    result = normalize_missing_values(df)

    pd.testing.assert_series_equal(
        result["quantity"],
        df["quantity"]
    )


def test_whitespace_removal():

    df = pd.DataFrame({
        "product": ["  Laptop  ", " Mouse "]
    })

    result = normalize_missing_values(df)

    assert result["product"].tolist() == [
        "Laptop", "Mouse"
    ]


def test_original_dataframe_unchanged():

    df = pd.DataFrame({
        "price": ["NULL", "1500"]
    })

    original = df.copy(deep=True)

    normalize_missing_values(df)

    pd.testing.assert_frame_equal(df, original)
