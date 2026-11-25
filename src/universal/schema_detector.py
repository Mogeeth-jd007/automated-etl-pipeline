import pandas as pd
import re

from .numeric_handler import clean_numeric_series
from .financial_handler import infer_financial_type
from .datetime_handler import infer_datetime_type
from .boolean_handler import infer_boolean_type

from .contact_detector import (
    is_email_column,
    is_phone_column
)


IDENTIFIER_NAMES = {
    "id", "sku", "upc", "isbn", "uuid",
    "guid", "barcode", "reference", "ref",
    "serial", "number", "phone", "postcode",
    "zipcode", "pincode"
}


IDENTIFIER_SUFFIXES = (
    "_id", "_sku", "_code", "_reference",
    "_ref", "_serial", "_number", "_no",
    "_uuid", "_guid", "_barcode", "_phone",
    "_zipcode", "_postcode", "_pincode"
)


def standardize_column_names(df):
    """Convert column names into unique snake_case names."""

    df = df.copy()
    standardized = []
    used_names = set()

    for index, column in enumerate(df.columns, start=1):

        name = str(column).strip().lower()

        name = re.sub(r"[^a-z0-9]+", "_", name)
        name = re.sub(r"_+", "_", name)
        name = name.strip("_")

        if not name:
            name = f"column_{index}"

        original_name = name
        suffix = 2

        while name in used_names:

            name = f"{original_name}_{suffix}"
            suffix += 1

        used_names.add(name)
        standardized.append(name)

    df.columns = standardized

    return df


def is_identifier_column(column_name):
    """Protect identifier and phone columns from conversion."""

    name = column_name.lower()

    # Email columns are textual contact information.

    if is_email_column(name):

        return False

    # Protect phone numbers from numeric conversion.

    if is_phone_column(name):

        return True

    return (
        name in IDENTIFIER_NAMES
        or name.endswith(IDENTIFIER_SUFFIXES)
    )


def looks_like_date(values):
    """Check whether values resemble supported date formats."""

    return infer_datetime_type(values)



def infer_column_type(
    column_name,
    series,
    detection_config=None
):
    """Automatically infer a column's logical data type."""

    settings = {
        "detect_currency": True,
        "detect_percentage": True,
        "detect_dates": True,
        "detect_booleans": True
    }

    if detection_config is not None:
        settings.update(detection_config)

    column_name = str(column_name)

    # Preserve email addresses as text.

    if is_email_column(column_name):
        return "text"

    # Preserve identifiers and phone numbers.

    if is_identifier_column(column_name):
        return "identifier"

    values = series.dropna()

    if values.empty:
        return "text"

    # Boolean detection.

    if settings["detect_booleans"]:

        if infer_boolean_type(column_name, values):
            return "boolean"

    # Financial detection.

    if settings["detect_currency"] or settings["detect_percentage"]:

        financial_type = infer_financial_type(values)

        if (
            financial_type == "currency"
            and settings["detect_currency"]
        ):
            return "currency"

        if (
            financial_type == "percentage"
            and settings["detect_percentage"]
        ):
            return "percentage"

    # Date detection.

    if settings["detect_dates"]:

        if looks_like_date(values):
            return "date"

    # Numeric detection.

    numeric_values = clean_numeric_series(values)

    if numeric_values.notna().mean() >= 0.8:
        return "numeric"

    return "text"




def detect_schema(
    df,
    standardize_columns=True,
    detection_config=None
):
    """Generate schema metadata with configurable detection."""

    df = df.copy()

    if standardize_columns:
        df = standardize_column_names(df)

    if not df.columns.is_unique:
        raise ValueError(
            "Duplicate column names must be resolved "
            "before schema detection."
        )

    schema = {}

    for column in df.columns:

        schema[column] = {
            "data_type": infer_column_type(
                column,
                df[column],
                detection_config=detection_config
            ),
            "total_records": int(len(df)),
            "non_null_count": int(df[column].notna().sum()),
            "null_count": int(df[column].isna().sum()),
            "unique_count": int(df[column].nunique()),
            "sample_values": (
                df[column]
                .dropna()
                .head(3)
                .astype(str)
                .tolist()
            )
        }

    return df, schema

