import pandas as pd

from .schema_detector import (
    detect_schema,
    standardize_column_names
)


def clean_text_columns(df):
    """Remove unnecessary whitespace and standardize blank values."""

    df = df.copy()

    text_columns = df.select_dtypes(
        include=["object", "string"]
    ).columns

    for column in text_columns:

        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
        )

        df[column] = df[column].replace("", pd.NA)

    return df


def convert_column_types(df, schema):
    """Convert columns using automatically detected data types."""

    df = df.copy()

    for column, details in schema.items():

        data_type = details["data_type"]

        if data_type == "identifier":

            df[column] = (
                df[column]
                .astype("string")
                .str.strip()
            )

        elif data_type == "numeric":

            cleaned_values = (
                df[column]
                .astype("string")
                .str.replace(",", "", regex=False)
            )

            df[column] = pd.to_numeric(
                cleaned_values,
                errors="coerce"
            )

        elif data_type == "date":

            df[column] = pd.to_datetime(
                df[column],
                format="mixed",
                errors="coerce"
            )

        elif data_type == "boolean":

            boolean_mapping = {
                "true": True,
                "false": False,
                "yes": True,
                "no": False,
                "y": True,
                "n": False
            }

            normalized = (
                df[column]
                .astype("string")
                .str.strip()
                .str.lower()
            )

            df[column] = normalized.map(
                boolean_mapping
            ).astype("boolean")

    return df


def transform_universal(df):
    """
    Automatically standardize, clean and convert an unknown dataset.

    No dataset profile or manual column configuration is required.
    """

    print("\n========== UNIVERSAL TRANSFORMATION STARTED ==========")

    # STEP 1: Standardize column names.
    df = standardize_column_names(df)

    print("Column names standardized successfully.")

    # STEP 2: Clean text and missing values.
    df = clean_text_columns(df)

    print("Text columns cleaned successfully.")

    # STEP 3: Detect schema after cleaning.
    df, schema = detect_schema(df)

    print("Automatic schema detection completed.")

    # STEP 4: Convert detected data types.
    df = convert_column_types(df, schema)

    print("Automatic data type conversion completed.")

    print("========== UNIVERSAL TRANSFORMATION COMPLETED ==========\n")

    return df, schema
