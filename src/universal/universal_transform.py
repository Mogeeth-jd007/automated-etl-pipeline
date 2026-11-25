
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


DEFAULT_TRANSFORMATION_CONFIG = {
    "standardize_columns": True,
    "clean_text": True,
    "normalize_missing_values": True,
    "auto_convert_types": True,
    "detect_currency": True,
    "detect_percentage": True,
    "detect_dates": True,
    "detect_booleans": True,
    "track_conversion_failures": True
}


def validate_transformation_config(config=None):
    """Validate transformation configuration and apply defaults."""

    if config is None:
        config = {}

    if not isinstance(config, dict):
        raise ValueError(
            "Transformation configuration must be a dictionary."
        )

    unknown_keys = set(config) - set(DEFAULT_TRANSFORMATION_CONFIG)

    if unknown_keys:
        raise ValueError(
            f"Unknown transformation settings: {sorted(unknown_keys)}"
        )

    settings = DEFAULT_TRANSFORMATION_CONFIG.copy()
    settings.update(config)

    for name, value in settings.items():

        if not isinstance(value, bool):
            raise ValueError(
                f"Transformation setting '{name}' must be a boolean."
            )

    return settings


def clean_text_columns(
    df,
    clean_text=True,
    normalize_missing=True
):
    """Normalize text and missing values independently."""

    df = df.copy()

    if clean_text:
        df = normalize_text_columns(df)

    if normalize_missing:
        df = normalize_missing_values(
            df,
            strip_whitespace=clean_text
        )

    return df


def convert_column_types(
    df,
    schema,
    track_failures=True
):
    """Convert columns and optionally track conversion failures."""

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
                "sample_values": units.dropna().head(3).tolist()
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

            df[column] = convert_boolean_series(df[column])

            details["storage_type"] = "nullable_boolean"

            details["boolean_summary"] = {
                "true_count": int(df[column].eq(True).sum()),
                "false_count": int(df[column].eq(False).sum()),
                "missing_count": int(df[column].isna().sum())
            }

        # Track conversion failures only when enabled.

        if (
            track_failures
            and data_type in TRACKED_DATA_TYPES
        ):

            details["conversion_report"] = (
                track_conversion_failures(
                    original_series,
                    df[column],
                    data_type
                )
            )

    schema.update(generated_schema)

    return df


def transform_universal(df, config=None):
    """Transform a dataset using configurable processing rules."""

    settings = validate_transformation_config(config)

    print("\n========== UNIVERSAL TRANSFORMATION STARTED ==========")

    df = df.copy()

    # STEP 1: Standardize column names.

    if settings["standardize_columns"]:

        df = standardize_column_names(df)

        print("Column names standardized successfully.")

    else:

        print("Column name standardization disabled.")

    # STEP 2: Normalize text and missing values.

    df = clean_text_columns(
        df,
        clean_text=settings["clean_text"],
        normalize_missing=settings["normalize_missing_values"]
    )

    print(
        "Text normalization:",
        settings["clean_text"]
    )

    print(
        "Missing-value normalization:",
        settings["normalize_missing_values"]
    )

    # STEP 3: Detect schema.

    detection_config = {
        "detect_currency": settings["detect_currency"],
        "detect_percentage": settings["detect_percentage"],
        "detect_dates": settings["detect_dates"],
        "detect_booleans": settings["detect_booleans"]
    }

    df, schema = detect_schema(
        df,
        standardize_columns=False,
        detection_config=detection_config
    )

    print("Automatic schema detection completed.")

    # STEP 4: Convert data types.

    if settings["auto_convert_types"]:

        df = convert_column_types(
            df,
            schema,
            track_failures=settings["track_conversion_failures"]
        )

        print("Intelligent data type conversion completed.")

        print("Financial values and currency units processed.")
        print("Advanced datetime conversion completed.")
        print("Boolean value standardization completed.")

    else:

        print("Automatic data type conversion disabled.")

    print(
        "Conversion failure tracking:",
        settings["track_conversion_failures"]
    )

    print("========== UNIVERSAL TRANSFORMATION COMPLETED ==========\n")

    return df, schema
