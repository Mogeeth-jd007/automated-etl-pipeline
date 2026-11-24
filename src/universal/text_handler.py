import re
import unicodedata

import pandas as pd

from .schema_detector import is_identifier_column


INVISIBLE_CHARACTERS = {
    "\u200b": "",
    "\ufeff": "",
    "\u2060": ""
}


def normalize_text_value(value):
    """Normalize text while preserving its meaningful content."""

    if pd.isna(value):
        return pd.NA

    text = str(value)

    # Normalize equivalent Unicode representations.
    text = unicodedata.normalize("NFKC", text)

    # Remove selected invisible formatting characters.
    for character, replacement in INVISIBLE_CHARACTERS.items():

        text = text.replace(
            character,
            replacement
        )

    # Replace consecutive whitespace with a single space.
    text = re.sub(r"\s+", " ", text)

    # Remove leading and trailing whitespace.
    text = text.strip()

    if not text:
        return pd.NA

    return text


def normalize_text_series(series):
    """Normalize a complete text column."""

    return series.map(
        normalize_text_value
    ).astype("string")


def normalize_text_columns(df):
    """Normalize text columns while protecting identifiers."""

    df = df.copy()

    text_columns = df.select_dtypes(
        include=["object", "string"]
    ).columns

    for column in text_columns:

        if is_identifier_column(column):
            continue

        df[column] = normalize_text_series(
            df[column]
        )

    return df
