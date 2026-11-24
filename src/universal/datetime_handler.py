import re
from datetime import datetime

import pandas as pd


SUPPORTED_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%d-%b-%Y",
    "%d-%B-%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%B %d, %Y"
)


NUMERIC_DATE_PATTERN = re.compile(
    r"^([0-9]{1,2})([/.-])([0-9]{1,2})\2([0-9]{4})$"
)


ISO_TIMESTAMP_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}"
    r"[T ][0-9]{2}:[0-9]{2}"
    r"(?::[0-9]{2}(?:\.[0-9]{1,6})?)?"
    r"(?:Z|[+-][0-9]{2}:[0-9]{2})?$"
)


def parse_datetime_value(value):
    """Parse dates without guessing ambiguous numeric formats."""

    if pd.isna(value):
        return pd.NaT

    text = str(value).strip()

    if not text:
        return pd.NaT

    # Handle numeric dates with potentially ambiguous ordering.
    match = NUMERIC_DATE_PATTERN.fullmatch(text)

    if match:

        first = int(match.group(1))
        second = int(match.group(3))
        year = int(match.group(4))

        if first == second and 1 <= first <= 12:
            day, month = first, second

        elif first > 12 and 1 <= second <= 12:
            day, month = first, second

        elif second > 12 and 1 <= first <= 12:
            month, day = first, second

        else:
            return pd.NaT

        try:
            return pd.Timestamp(
                datetime(year, month, day)
            )
        except (ValueError, OverflowError):
            return pd.NaT

    # Handle ISO timestamps, including timezone offsets.
    if ISO_TIMESTAMP_PATTERN.fullmatch(text):

        try:
            timestamp = pd.Timestamp(text)

            if timestamp.tzinfo is not None:
                timestamp = timestamp.tz_convert("UTC")

            return timestamp

        except (ValueError, OverflowError):
            return pd.NaT

    # Handle explicitly supported date formats.
    for date_format in SUPPORTED_DATE_FORMATS:

        try:
            parsed = datetime.strptime(
                text,
                date_format
            )

            return pd.Timestamp(parsed)

        except (ValueError, OverflowError):
            continue

    return pd.NaT


def parse_datetime_series(series):
    """Parse a complete date or timestamp column."""

    return series.map(parse_datetime_value)


def infer_datetime_type(series, threshold=0.8):
    """Detect date columns using successful parsing rates."""

    values = series.dropna()

    if values.empty:
        return False

    parsed = parse_datetime_series(values)

    return bool(
        parsed.notna().mean() >= threshold
    )
