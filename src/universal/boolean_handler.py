import pandas as pd


BOOLEAN_MAPPING = {
    "true": True,
    "false": False,
    "yes": True,
    "no": False,
    "y": True,
    "n": False,
    "t": True,
    "f": False,
    "on": True,
    "off": False,
    "enabled": True,
    "disabled": False,
    "1": True,
    "0": False
}


BOOLEAN_COLUMN_NAMES = {
    "active",
    "enabled",
    "disabled",
    "verified",
    "approved",
    "completed",
    "available",
    "deleted",
    "paid",
    "flag"
}


BOOLEAN_COLUMN_PREFIXES = (
    "is_",
    "has_",
    "can_",
    "was_",
    "should_"
)


def is_boolean_column_name(column_name):
    """Check whether a column name suggests Boolean meaning."""

    name = str(column_name).strip().lower()

    return (
        name in BOOLEAN_COLUMN_NAMES
        or name.startswith(BOOLEAN_COLUMN_PREFIXES)
        or name.endswith("_flag")
    )


def parse_boolean_value(value):
    """Convert supported Boolean representations."""

    if pd.isna(value):
        return pd.NA

    normalized = str(value).strip().lower()

    return BOOLEAN_MAPPING.get(
        normalized,
        pd.NA
    )


def convert_boolean_series(series):
    """Convert a complete column into nullable Boolean values."""

    return series.map(
        parse_boolean_value
    ).astype("boolean")


def infer_boolean_type(
    column_name,
    series,
    threshold=0.8
):
    """Detect Boolean columns with numeric ambiguity protection."""

    values = series.dropna()

    if values.empty:
        return False

    normalized = (
        values.astype(str)
        .str.strip()
        .str.lower()
    )

    boolean_matches = normalized.isin(
        BOOLEAN_MAPPING
    )

    if boolean_matches.mean() < threshold:
        return False

    textual_matches = normalized.isin(
        set(BOOLEAN_MAPPING) - {"0", "1"}
    )

    # Numeric-only Boolean representations require context.
    if not textual_matches.any():

        return is_boolean_column_name(
            column_name
        )

    return True
