import pandas as pd
import pytest

from universal.text_handler import (
    normalize_text_value,
    normalize_text_series,
    normalize_text_columns
)


@pytest.mark.parametrize(
    "original, expected",
    [
        ("  Laptop  ", "Laptop"),
        ("Gaming   Laptop", "Gaming Laptop"),
        ("Hello\tWorld", "Hello World"),
        ("Hello\nWorld", "Hello World"),
        ("Hello\r\nWorld", "Hello World"),
        ("Hello\u00a0World", "Hello World"),
        ("Lap\u200btop", "Laptop"),
        ("\ufeffLaptop", "Laptop"),
        ("Lap\u2060top", "Laptop"),
        ("\uff21\uff22\uff23", "ABC"),
        ("\uff11\uff12\uff13", "123"),
        ("Cafe\u0301", "Caf\u00e9"),
        ("MiXeD CaSe", "MiXeD CaSe"),
        ("Hello, World!", "Hello, World!"),
        ("0", "0")
    ]
)
def test_text_normalization(original, expected):

    assert normalize_text_value(original) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "\t\n",
        "\u200b",
        None,
        pd.NA
    ]
)
def test_missing_text_values(value):

    assert pd.isna(normalize_text_value(value))


def test_text_series_normalization():

    series = pd.Series([
        "  Laptop  ",
        "Gaming   Mouse",
        "Hello\tWorld",
        None,
        "\u200b"
    ])

    result = normalize_text_series(series)

    assert result.dropna().tolist() == [
        "Laptop",
        "Gaming Mouse",
        "Hello World"
    ]

    assert result.isna().sum() == 2

    assert str(result.dtype) == "string"


def test_identifier_protection():

    df = pd.DataFrame({
        "product_id": ["001", "A  002", "\uff21\uff22\uff23"],
        "product_name": [
            "  Laptop  ",
            "Gaming   Mouse",
            "\uff21\uff22\uff23"
        ]
    })

    result = normalize_text_columns(df)

    pd.testing.assert_series_equal(
        result["product_id"],
        df["product_id"]
    )

    assert result["product_name"].tolist() == [
        "Laptop",
        "Gaming Mouse",
        "ABC"
    ]


def test_numeric_columns_preserved():

    df = pd.DataFrame({
        "quantity": [0, 10, 20],
        "price": [100.5, 200.5, 300.5],
        "product": [" Laptop ", " Mouse ", " Keyboard "]
    })

    result = normalize_text_columns(df)

    pd.testing.assert_series_equal(
        result["quantity"],
        df["quantity"]
    )

    pd.testing.assert_series_equal(
        result["price"],
        df["price"]
    )


def test_multiple_text_columns():

    df = pd.DataFrame({
        "product": [" Laptop ", " Gaming   Mouse "],
        "city": [" Chennai ", " New   Delhi "]
    })

    result = normalize_text_columns(df)

    assert result["product"].tolist() == [
        "Laptop", "Gaming Mouse"
    ]

    assert result["city"].tolist() == [
        "Chennai", "New Delhi"
    ]


def test_index_preservation():

    series = pd.Series(
        [" Laptop ", " Mouse "],
        index=[10, 20]
    )

    result = normalize_text_series(series)

    assert result.index.equals(series.index)


def test_original_series_unchanged():

    series = pd.Series([
        " Laptop ",
        "Gaming   Mouse"
    ])

    original = series.copy(deep=True)

    normalize_text_series(series)

    pd.testing.assert_series_equal(
        series,
        original
    )


def test_original_dataframe_unchanged():

    df = pd.DataFrame({
        "product_id": ["001", "002"],
        "product": [" Laptop ", " Mouse "]
    })

    original = df.copy(deep=True)

    normalize_text_columns(df)

    pd.testing.assert_frame_equal(
        df,
        original
    )
