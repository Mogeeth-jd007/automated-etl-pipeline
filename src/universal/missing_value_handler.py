
import pandas as pd

from .schema_detector import is_identifier_column


MISSING_VALUE_MARKERS = {
    "",
    "null",
    "none",
    "nan",
    "n/a"
}


def normalize_missing_values(df, strip_whitespace=True):
    """
    Normalize common missing-value representations.

    Whitespace cleaning can be independently enabled or disabled.

    Preserve identifiers and potentially meaningful text.
    """

    if not isinstance(strip_whitespace, bool):
        raise ValueError(
            "strip_whitespace must be a boolean."
        )

    df = df.copy()

    text_columns = df.select_dtypes(
        include=["object", "string"]
    ).columns

    for column in text_columns:

        original = df[column].astype("string")

        # Use stripped values only for missing-value detection.

        comparison_values = original.str.strip()

        if is_identifier_column(column):

            missing_mask = (
                comparison_values.eq("")
                .fillna(False)
            )

        else:

            missing_mask = (
                comparison_values
                .str.lower()
                .isin(MISSING_VALUE_MARKERS)
            )

        # Preserve original text when whitespace cleaning is disabled.

        if strip_whitespace:

            cleaned = comparison_values

        else:

            cleaned = original

        df[column] = cleaned.mask(
            missing_mask,
            pd.NA
        )

    return df
