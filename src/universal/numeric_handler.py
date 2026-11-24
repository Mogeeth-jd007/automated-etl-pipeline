import re

import pandas as pd


PLAIN_NUMBER_PATTERN = re.compile(
    r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)"
    r"(?:[eE][+-]?[0-9]+)?"
)

INTERNATIONAL_NUMBER_PATTERN = re.compile(
    r"[+-]?[0-9]{1,3}(?:,[0-9]{3})+"
    r"(?:\.[0-9]+)?"
)

INDIAN_NUMBER_PATTERN = re.compile(
    r"[+-]?[0-9]{1,2}(?:,[0-9]{2})*,[0-9]{3}"
    r"(?:\.[0-9]+)?"
)


def clean_numeric_value(value):
    """
    Validate and clean an individual numeric value.

    Supports plain numbers, scientific notation,
    international grouping and Indian grouping.
    """

    if pd.isna(value):
        return pd.NA

    value = str(value).strip()

    if not value:
        return pd.NA

    if PLAIN_NUMBER_PATTERN.fullmatch(value):
        return value

    if INTERNATIONAL_NUMBER_PATTERN.fullmatch(value):
        return value.replace(",", "")

    if INDIAN_NUMBER_PATTERN.fullmatch(value):
        return value.replace(",", "")

    return pd.NA


def clean_numeric_series(series):
    """Validate and convert a complete numeric column."""

    cleaned = series.map(clean_numeric_value)

    converted = pd.to_numeric(
        cleaned.astype("string"),
        errors="coerce"
    )

    converted = converted.replace(
        [float("inf"), float("-inf")],
        pd.NA
    )

    return converted
