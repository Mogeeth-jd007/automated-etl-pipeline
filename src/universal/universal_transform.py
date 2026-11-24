import pandas as pd

from .schema_detector import (
    detect_schema,
    standardize_column_names
)

from .missing_value_handler import normalize_missing_values
from .numeric_handler import clean_numeric_series
from .datetime_handler import parse_datetime_series
from .boolean_handler import convert_boolean_series
from .text_handler import normalize_text_columns

from .conversion_tracker import (
    TRACKED_DATA_TYPES,
    track_conversion_failures
)

from .financial_handler import (
    convert_financial_series,
    generate_currency_column_name
)


def clean_text_columns(df):
    """Normalize text and missing-value representations."""

    df = normalize_text_columns(df)
    df = normalize_missing_values(df)

    return df


def convert_column_types(df, schema):
    """Convert columns and track data conversion failures."""

    df = df.copy()

    generated_schema = {}

    for column, details in schema.items():

        data_type = details["data_type"]

        original_series = df[column].copy()

        if data_type == "identifier":

            df[column] = (
                df[column]
                .astype("string")
                .str.strip()
            )

        elif data_type == "numeric":

            df[column] = clean_numeric_series(df[column])

        elif data_type == "currency":

            amounts, units = convert_financial_series(
                df[column],
                "currency"
            )

            currency_column = generate_currency_column_name(
                column,
                df.columns
            )

            df[column] = amounts
            df[currency_column] = units

            details["currency_column"] = currency_column
            details["storage_type"] = "decimal_string"

            details["detected_currencies"] = sorted(
                units.dropna().unique().tolist()
            )

            generated_schema[currency_column] = {
                "data_type": "text",
                "generated": True,
                "source_column": column,
                "total_records": int(len(df)),
                "non_null_count": int(units.notna().sum()),
                "null_count": int(units.isna().sum()),
                "unique_count": int(units.nunique()),
                "sample_values": (
                    units.dropna().head(3).tolist()
                )
            }

        elif data_type == "percentage":

            amounts, _ = convert_financial_series(
                df[column],
                "percentage"
            )

            df[column] = amounts

            details["unit"] = "fraction"
            details["storage_type"] = "decimal_string"

        elif data_type == "date":

            parsed = parse_datetime_series(df[column])

            df[column] = parsed.map(
                lambda value: (
                    value.isoformat()
                    if pd.notna(value)
                    else pd.NA
                )
            ).astype("string")

            details["storage_type"] = "iso8601_string"

            details["timezone_policy"] = (
                "Normalize aware timestamps to UTC; "
                "preserve naive timestamps"
            )

        elif data_type == "boolean":

            df[column] = convert_boolean_series(
                df[column]
            )

            details["storage_type"] = "nullable_boolean"

            details["boolean_summary"] = {
                "true_count": int(
                    df[column].eq(True).sum()
                ),
                "false_count": int(
                    df[column].eq(False).sum()
                ),
                "missing_count": int(
                    df[column].isna().sum()
                )
            }

        # Track conversions for supported logical data types.
        if data_type in TRACKED_DATA_TYPES:

            details["conversion_report"] = (
                track_conversion_failures(
                    original_series,
                    df[column],
                    data_type
                )
            )

    schema.update(generated_schema)

    return df


def transform_universal(df):
    """Automatically standardize, clean and convert a dataset."""

    print("\n========== UNIVERSAL TRANSFORMATION STARTED ==========")

    df = standardize_column_names(df)

    print("Column names standardized successfully.")

    df = clean_text_columns(df)

    print("Advanced text normalization completed.")
    print("Missing-value normalization completed.")

    df, schema = detect_schema(df)

    print("Automatic schema detection completed.")

    df = convert_column_types(df, schema)

    print("Intelligent data type conversion completed.")
    print("Financial values and currency units processed.")
    print("Advanced datetime conversion completed.")
    print("Boolean value standardization completed.")
    print("Data conversion failure tracking completed.")

    print("========== UNIVERSAL TRANSFORMATION COMPLETED ==========\n")

    return df, schema
