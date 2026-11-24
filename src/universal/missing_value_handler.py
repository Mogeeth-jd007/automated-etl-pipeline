import pandas as pd

from .schema_detector import is_identifier_column


MISSING_VALUE_MARKERS = {
    "",
    "null",
    "none",
    "nan",
    "n/a"
}


def normalize_missing_values(df):
    """
    Normalize common missing-value representations.

    Preserve identifiers and potentially meaningful text.
    """

    df = df.copy()

    text_columns = df.select_dtypes(
        include=["object", "string"]
    ).columns

    for column in text_columns:

        cleaned = (
            df[column]
            .astype("string")
            .str.strip()
        )

        if is_identifier_column(column):

            missing_mask = cleaned.eq("").fillna(False)

        else:

            missing_mask = (
                cleaned
                .str.lower()
                .isin(MISSING_VALUE_MARKERS)
            )

        df[column] = cleaned.mask(
            missing_mask,
            pd.NA
        )

    return df
