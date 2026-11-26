
"""
Universal Dataset Profiling Engine.

Generates dataset-level and column-level profiling statistics.

Supported profiling:
- Numeric
- Categorical
- Identifier
- Contact
- Date
- Boolean
- Currency
- Percentage
- Missing values

The original DataFrame is never modified.
"""

from datetime import datetime, timezone

import pandas as pd

from .schema_detector import detect_schema
from .numeric_handler import clean_numeric_series
from .missing_value_handler import normalize_missing_values
from .contact_detector import detect_contact_type
from .contact_validator import is_valid_email, is_valid_phone
from .datetime_handler import parse_datetime_value
from .boolean_handler import parse_boolean_value
from .financial_profiler import (
    profile_currency_column,
    profile_percentage_column
)


def _safe_number(value):
    """Convert statistical results into JSON-compatible numbers."""

    if pd.isna(value):
        return None

    return float(value)


def profile_numeric_column(series):
    """Calculate descriptive statistics for a numeric column."""

    numeric_values = clean_numeric_series(series)
    valid_values = numeric_values.dropna()

    valid_count = int(len(valid_values))
    total_count = int(len(series))
    invalid_count = total_count - valid_count

    if valid_count == 0:
        return {
            "total_count": total_count,
            "valid_count": 0,
            "invalid_count": invalid_count,
            "mean": None,
            "median": None,
            "mode": [],
            "minimum": None,
            "maximum": None,
            "standard_deviation": None,
            "variance": None,
            "q1": None,
            "q2": None,
            "q3": None,
            "iqr": None,
            "skewness": None
        }

    q1 = valid_values.quantile(0.25)
    q2 = valid_values.quantile(0.50)
    q3 = valid_values.quantile(0.75)

    return {
        "total_count": total_count,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "mean": _safe_number(valid_values.mean()),
        "median": _safe_number(valid_values.median()),
        "mode": [
            _safe_number(value)
            for value in valid_values.mode().tolist()
        ],
        "minimum": _safe_number(valid_values.min()),
        "maximum": _safe_number(valid_values.max()),
        "standard_deviation": _safe_number(valid_values.std()),
        "variance": _safe_number(valid_values.var()),
        "q1": _safe_number(q1),
        "q2": _safe_number(q2),
        "q3": _safe_number(q3),
        "iqr": _safe_number(q3 - q1),
        "skewness": (
            _safe_number(valid_values.skew())
            if valid_count >= 3
            else None
        )
    }


def profile_categorical_column(series, top_n=10):
    """Calculate frequency and cardinality statistics."""

    if (
        isinstance(top_n, bool)
        or not isinstance(top_n, int)
        or top_n < 1
    ):
        raise ValueError("top_n must be a positive integer.")

    total_count = int(len(series))
    valid_values = series.dropna().astype("string")
    non_null_count = int(len(valid_values))
    missing_count = total_count - non_null_count

    if non_null_count == 0:
        return {
            "total_count": total_count,
            "non_null_count": 0,
            "missing_count": missing_count,
            "unique_count": 0,
            "cardinality_ratio": None,
            "mode": [],
            "top_values": []
        }

    frequencies = valid_values.value_counts(dropna=True)
    unique_count = int(len(frequencies))

    top_values = []

    for value, count in frequencies.head(top_n).items():
        count = int(count)

        top_values.append({
            "value": str(value),
            "count": count,
            "percentage": round(
                count / non_null_count * 100, 2
            )
        })

    maximum_frequency = int(frequencies.max())

    modes = [
        str(value)
        for value, count in frequencies.items()
        if int(count) == maximum_frequency
    ]

    return {
        "total_count": total_count,
        "non_null_count": non_null_count,
        "missing_count": missing_count,
        "unique_count": unique_count,
        "cardinality_ratio": round(
            unique_count / non_null_count, 4
        ),
        "mode": modes,
        "top_values": top_values
    }


def profile_identifier_column(series):
    """Calculate identifier completeness and uniqueness."""

    values = series.astype("string").str.strip()

    missing_mask = (
        values.isna()
        | values.eq("").fillna(False)
    )

    available_values = values[~missing_mask]

    total_records = int(len(series))
    missing_count = int(missing_mask.sum())
    available_count = int(len(available_values))
    unique_count = int(available_values.nunique())

    repeated_occurrences = available_count - unique_count

    repeated_group_members = int(
        available_values.duplicated(keep=False).sum()
    )

    uniqueness_rate = (
        round(unique_count / available_count * 100, 2)
        if available_count > 0
        else None
    )

    completeness_rate = (
        round(available_count / total_records * 100, 2)
        if total_records > 0
        else None
    )

    is_candidate_key = (
        total_records >= 2
        and missing_count == 0
        and unique_count == total_records
    )

    return {
        "total_records": total_records,
        "available_count": available_count,
        "missing_count": missing_count,
        "unique_count": unique_count,
        "repeated_occurrences": repeated_occurrences,
        "repeated_group_members": repeated_group_members,
        "uniqueness_rate_percent": uniqueness_rate,
        "completeness_rate_percent": completeness_rate,
        "candidate_unique_key": is_candidate_key
    }


def profile_contact_column(series, contact_type):
    """Profile email or phone values."""

    if contact_type not in {"email", "phone"}:
        raise ValueError(
            "contact_type must be 'email' or 'phone'."
        )

    valid_count = 0
    invalid_count = 0
    missing_count = 0
    invalid_examples = []

    validator = (
        is_valid_email
        if contact_type == "email"
        else is_valid_phone
    )

    for position, value in enumerate(series):

        if pd.isna(value) or not str(value).strip():
            missing_count += 1
            continue

        if validator(value):
            valid_count += 1
        else:
            invalid_count += 1
            invalid_examples.append({
                "row_position": position
            })

    total_records = int(len(series))
    available_count = valid_count + invalid_count

    validity_rate = (
        round(valid_count / available_count * 100, 2)
        if available_count > 0
        else None
    )

    completeness_rate = (
        round(available_count / total_records * 100, 2)
        if total_records > 0
        else None
    )

    return {
        "contact_type": contact_type,
        "total_records": total_records,
        "available_count": available_count,
        "missing_count": missing_count,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "validity_rate_percent": validity_rate,
        "completeness_rate_percent": completeness_rate,
        "invalid_examples": invalid_examples
    }


def profile_date_column(series, reference_time=None):
    """Profile dates and timestamps."""

    if reference_time is None:
        reference_time = pd.Timestamp(
            datetime.now(timezone.utc)
        )
    else:
        reference_time = parse_datetime_value(reference_time)

        if pd.isna(reference_time):
            raise ValueError("Invalid reference time.")

    if reference_time.tzinfo is None:
        reference_utc = reference_time.tz_localize("UTC")
    else:
        reference_utc = reference_time.tz_convert("UTC")

    valid_values = []
    invalid_examples = []

    valid_count = 0
    invalid_count = 0
    missing_count = 0
    future_count = 0

    unique_timestamps = set()

    for position, value in enumerate(series):

        if pd.isna(value) or not str(value).strip():
            missing_count += 1
            continue

        parsed = parse_datetime_value(value)

        if pd.isna(parsed):
            invalid_count += 1
            invalid_examples.append({
                "row_position": position
            })
            continue

        valid_count += 1

        if parsed.tzinfo is None:
            comparable_timestamp = parsed.tz_localize("UTC")
        else:
            comparable_timestamp = parsed.tz_convert("UTC")

        timestamp_ns = int(comparable_timestamp.value)

        valid_values.append({
            "timestamp": parsed,
            "timestamp_ns": timestamp_ns
        })

        unique_timestamps.add(timestamp_ns)

        if comparable_timestamp > reference_utc:
            future_count += 1

    total_records = int(len(series))
    available_count = valid_count + invalid_count

    if valid_values:
        earliest = min(
            valid_values,
            key=lambda item: item["timestamp_ns"]
        )

        latest = max(
            valid_values,
            key=lambda item: item["timestamp_ns"]
        )

        earliest_date = earliest["timestamp"].isoformat()
        latest_date = latest["timestamp"].isoformat()

        date_range_days = round(
            (
                latest["timestamp_ns"]
                - earliest["timestamp_ns"]
            ) / 86_400_000_000_000,
            2
        )
    else:
        earliest_date = None
        latest_date = None
        date_range_days = None

    validity_rate = (
        round(valid_count / available_count * 100, 2)
        if available_count > 0
        else None
    )

    completeness_rate = (
        round(available_count / total_records * 100, 2)
        if total_records > 0
        else None
    )

    return {
        "total_records": total_records,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "missing_count": missing_count,
        "validity_rate_percent": validity_rate,
        "completeness_rate_percent": completeness_rate,
        "earliest_date": earliest_date,
        "latest_date": latest_date,
        "date_range_days": date_range_days,
        "unique_date_count": len(unique_timestamps),
        "future_date_count": future_count,
        "invalid_examples": invalid_examples
    }


def profile_boolean_column(series):
    """Profile Boolean values using the existing Boolean parser."""

    true_count = 0
    false_count = 0
    missing_count = 0
    invalid_count = 0

    invalid_examples = []

    for position, value in enumerate(series):

        if pd.isna(value) or (
            isinstance(value, str) and not value.strip()
        ):
            missing_count += 1
            continue

        parsed = parse_boolean_value(value)

        if pd.isna(parsed):
            invalid_count += 1
            invalid_examples.append({
                "row_position": position
            })

        elif parsed is True:
            true_count += 1

        else:
            false_count += 1

    total_records = int(len(series))
    valid_count = true_count + false_count

    true_percentage = (
        round(true_count / valid_count * 100, 2)
        if valid_count > 0
        else None
    )

    false_percentage = (
        round(false_count / valid_count * 100, 2)
        if valid_count > 0
        else None
    )

    completeness_percentage = (
        round(valid_count / total_records * 100, 2)
        if total_records > 0
        else None
    )

    if valid_count == 0:
        dominant_value = None
        single_value_column = False
    elif true_count == valid_count:
        dominant_value = True
        single_value_column = True
    elif false_count == valid_count:
        dominant_value = False
        single_value_column = True
    else:
        dominant_value = true_count > false_count
        single_value_column = False

    return {
        "total_records": total_records,
        "true_count": true_count,
        "false_count": false_count,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "missing_count": missing_count,
        "true_percentage": true_percentage,
        "false_percentage": false_percentage,
        "completeness_percentage": completeness_percentage,
        "dominant_value": dominant_value,
        "single_value_column": single_value_column,
        "invalid_examples": invalid_examples
    }


def profile_missing_values(df):
    """Generate missing-value and completeness statistics."""

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a pandas DataFrame.")

    if not df.columns.is_unique:
        raise ValueError(
            "Duplicate column names must be resolved before profiling."
        )

    normalized_df = normalize_missing_values(df)

    total_records = len(normalized_df)
    total_columns = len(normalized_df.columns)
    total_cells = total_records * total_columns

    missing_mask = normalized_df.isna()
    missing_cells = int(missing_mask.sum().sum())
    non_missing_cells = total_cells - missing_cells

    completeness_score = (
        round(non_missing_cells / total_cells * 100, 2)
        if total_cells > 0
        else None
    )

    column_summary = {}
    empty_columns = []

    for column in normalized_df.columns:

        missing_count = int(missing_mask[column].sum())
        non_missing_count = total_records - missing_count

        missing_percentage = (
            round(missing_count / total_records * 100, 2)
            if total_records > 0
            else None
        )

        non_missing_percentage = (
            round(non_missing_count / total_records * 100, 2)
            if total_records > 0
            else None
        )

        completely_missing = (
            total_records > 0
            and missing_count == total_records
        )

        if completely_missing:
            empty_columns.append(column)

        column_summary[column] = {
            "missing_count": missing_count,
            "non_missing_count": non_missing_count,
            "missing_percentage": missing_percentage,
            "non_missing_percentage": non_missing_percentage,
            "completely_missing": completely_missing
        }

    if total_records > 0 and total_columns > 0:
        empty_row_mask = missing_mask.all(axis=1)
        missing_row_mask = missing_mask.any(axis=1)
    else:
        empty_row_mask = pd.Series(
            False, index=normalized_df.index, dtype=bool
        )
        missing_row_mask = pd.Series(
            False, index=normalized_df.index, dtype=bool
        )

    record_details = []

    for position, row in enumerate(
        missing_mask.itertuples(index=False, name=None)
    ):
        missing_columns = [
            column
            for column, missing in zip(normalized_df.columns, row)
            if missing
        ]

        if missing_columns:
            record_details.append({
                "row_position": position,
                "missing_count": len(missing_columns),
                "missing_columns": missing_columns,
                "is_empty_record": bool(
                    empty_row_mask.iloc[position]
                )
            })

    return {
        "total_records": total_records,
        "total_columns": total_columns,
        "total_cells": total_cells,
        "missing_cells": missing_cells,
        "non_missing_cells": non_missing_cells,
        "missing_value_rows": int(missing_row_mask.sum()),
        "empty_rows": int(empty_row_mask.sum()),
        "empty_columns": len(empty_columns),
        "empty_column_names": empty_columns,
        "completeness_score": completeness_score,
        "column_summary": column_summary,
        "record_details": record_details
    }


def profile_dataset(
    df,
    detection_config=None,
    reference_time=None
):
    """Generate complete dataset profiling statistics."""

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a pandas DataFrame.")

    if not df.columns.is_unique:
        raise ValueError(
            "Duplicate column names must be resolved before profiling."
        )

    original_df = df.copy(deep=True)
    normalized_df = normalize_missing_values(original_df)

    standardized_df, schema = detect_schema(
        normalized_df,
        standardize_columns=True,
        detection_config=detection_config
    )

    total_records = len(standardized_df)
    total_columns = len(standardized_df.columns)
    total_cells = total_records * total_columns

    missing_cells = int(
        standardized_df.isna().sum().sum()
    )

    completeness_score = (
        round(
            (total_cells - missing_cells) / total_cells * 100,
            2
        )
        if total_cells > 0
        else None
    )

    duplicate_rows = int(standardized_df.duplicated().sum())

    dataset_summary = {
        "total_records": total_records,
        "total_columns": total_columns,
        "total_cells": total_cells,
        "missing_cells": missing_cells,
        "completeness_score": completeness_score,
        "duplicate_records": duplicate_rows,
        "memory_usage_bytes": int(
            standardized_df.memory_usage(
                index=False, deep=True
            ).sum()
        )
    }

    column_profiles = {}
    numeric_profiles = {}
    categorical_profiles = {}
    identifier_profiles = {}
    contact_profiles = {}
    date_profiles = {}
    boolean_profiles = {}
    currency_profiles = {}
    percentage_profiles = {}

    for column, details in schema.items():

        series = standardized_df[column]

        non_null_count = int(series.notna().sum())
        null_count = int(series.isna().sum())
        unique_count = int(series.nunique())

        missing_percentage = (
            round(null_count / total_records * 100, 2)
            if total_records > 0
            else None
        )

        uniqueness_percentage = (
            round(unique_count / non_null_count * 100, 2)
            if non_null_count > 0
            else None
        )

        data_type = details["data_type"]

        column_profiles[column] = {
            "data_type": data_type,
            "total_records": total_records,
            "non_null_count": non_null_count,
            "null_count": null_count,
            "missing_percentage": missing_percentage,
            "unique_count": unique_count,
            "uniqueness_percentage": uniqueness_percentage,
            "sample_values": details["sample_values"]
        }

        contact_type = detect_contact_type(column)

        if contact_type is not None:

            contact_profiles[column] = profile_contact_column(
                series,
                contact_type
            )

        elif data_type == "boolean":

            boolean_profiles[column] = profile_boolean_column(
                series
            )

        elif data_type == "currency":

            currency_profiles[column] = profile_currency_column(
                series
            )

        elif data_type == "percentage":

            percentage_profiles[column] = profile_percentage_column(
                series
            )

        elif data_type == "date":

            date_profiles[column] = profile_date_column(
                series,
                reference_time=reference_time
            )

        elif data_type == "numeric":

            numeric_profiles[column] = profile_numeric_column(
                series
            )

        elif data_type == "text":

            categorical_profiles[column] = (
                profile_categorical_column(series)
            )

        elif data_type == "identifier":

            identifier_profiles[column] = (
                profile_identifier_column(series)
            )

    return {
        "dataset_summary": dataset_summary,
        "column_profiles": column_profiles,
        "numeric_profiles": numeric_profiles,
        "categorical_profiles": categorical_profiles,
        "identifier_profiles": identifier_profiles,
        "contact_profiles": contact_profiles,
        "date_profiles": date_profiles,
        "boolean_profiles": boolean_profiles,
        "currency_profiles": currency_profiles,
        "percentage_profiles": percentage_profiles,
        "missing_profiles": profile_missing_values(original_df)
    }
