import re
from decimal import Decimal, DecimalException

import pandas as pd

from .numeric_handler import clean_numeric_value


CURRENCY_UNITS = {
    "\u20b9": "INR",
    "$": "DOLLAR_UNSPECIFIED",
    "\u20ac": "EUR",
    "\u00a3": "GBP",
    "INR": "INR",
    "USD": "USD",
    "EUR": "EUR",
    "GBP": "GBP",
    "CAD": "CAD",
    "AUD": "AUD",
    "JPY": "JPY"
}


def parse_financial_value(value):
    """Parse financial values while preserving units."""

    if pd.isna(value):
        return None

    text = str(value).strip()

    if not text:
        return None

    if text.endswith("%"):

        cleaned = clean_numeric_value(text[:-1].strip())

        if pd.isna(cleaned):
            return None

        try:
            amount = Decimal(cleaned) / Decimal("100")
        except DecimalException:
            return None

        return {
            "value": amount,
            "data_type": "percentage",
            "unit": "percentage"
        }

    for marker, unit in CURRENCY_UNITS.items():

        pattern = re.escape(marker)

        prefix = re.fullmatch(
            pattern + r"\s*(.+)",
            text,
            flags=re.IGNORECASE
        )

        suffix = re.fullmatch(
            r"(.+?)\s*" + pattern,
            text,
            flags=re.IGNORECASE
        )

        match = prefix or suffix

        if match is None:
            continue

        cleaned = clean_numeric_value(match.group(1))

        if pd.isna(cleaned):
            return None

        try:
            amount = Decimal(cleaned)
        except DecimalException:
            return None

        return {
            "value": amount,
            "data_type": "currency",
            "unit": unit
        }

    return None


def infer_financial_type(series, threshold=0.8):
    """Detect currency or percentage columns."""

    values = series.dropna()

    if values.empty:
        return None

    parsed_values = [
        parse_financial_value(value)
        for value in values
    ]

    currency_count = sum(
        item is not None and item["data_type"] == "currency"
        for item in parsed_values
    )

    percentage_count = sum(
        item is not None and item["data_type"] == "percentage"
        for item in parsed_values
    )

    total = len(values)

    # Do not combine currency and percentage values.
    if currency_count > 0 and percentage_count > 0:
        return None

    if currency_count / total >= threshold:
        return "currency"

    if percentage_count / total >= threshold:
        return "percentage"

    return None


def convert_financial_series(series, data_type):
    """Convert financial values and preserve their units."""

    amounts = []
    units = []

    for value in series:

        parsed = parse_financial_value(value)

        if parsed is None or parsed["data_type"] != data_type:

            amounts.append(pd.NA)
            units.append(pd.NA)

        else:

            amounts.append(str(parsed["value"]))
            units.append(parsed["unit"])

    return (
        pd.Series(
            amounts,
            index=series.index,
            dtype="string"
        ),
        pd.Series(
            units,
            index=series.index,
            dtype="string"
        )
    )


def generate_currency_column_name(column, existing_columns):
    """Generate a currency column without overwriting existing data."""

    base_name = f"{column}_currency"
    candidate = base_name
    suffix = 2

    while candidate in existing_columns:

        candidate = f"{base_name}_{suffix}"
        suffix += 1

    return candidate
