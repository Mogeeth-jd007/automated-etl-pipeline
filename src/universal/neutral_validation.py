
"""
Neutral result factories for disabled validation modules.

These results preserve the expected return structures while
ensuring disabled validators contribute no issues.
"""

import pandas as pd


def _false_series(df):
    """Create an indexed Boolean Series containing only False."""

    return pd.Series(
        False,
        index=df.index,
        dtype=bool
    )


def _zero_series(df):
    """Create an indexed integer Series containing only zero."""

    return pd.Series(
        0,
        index=df.index,
        dtype="int64"
    )


def neutral_missing_value_result(df):

    false = _false_series(df)

    return {
        "missing_mask": pd.DataFrame(
            False,
            index=df.index,
            columns=df.columns,
            dtype=bool
        ),
        "missing_counts": _zero_series(df),
        "missing_rows": false.copy(),
        "empty_rows": false.copy(),
        "required_missing_rows": false.copy(),
        "warning_rows": false.copy(),
        "rejected_rows": false.copy(),
        "report": {
            "total_records": len(df),
            "source_columns": len(df.columns),
            "total_cells": len(df) * len(df.columns),
            "missing_cells": 0,
            "missing_value_rows": 0,
            "empty_rows": 0,
            "required_missing_rows": 0,
            "warning_rows": 0,
            "rejected_rows": 0,
            "completeness_score": 100.0 if len(df) * len(df.columns) else None,
            "column_summary": {},
            "record_details": []
        }
    }


def neutral_duplicate_result(df):

    false = _false_series(df)

    return {
        "exact_duplicates": false.copy(),
        "exact_duplicate_members": false.copy(),
        "key_duplicates": false.copy(),
        "key_duplicate_members": false.copy(),
        "rejected_rows": false.copy(),
        "report": {
            "total_records": len(df),
            "exact_duplicate_rows": 0,
            "exact_duplicate_group_members": 0,
            "key_duplicate_rows": 0,
            "key_duplicate_group_members": 0,
            "additional_key_duplicate_rows": 0,
            "total_duplicate_rows": 0,
            "duplicate_rate_percent": 0.0,
            "key_columns": [],
            "record_details": []
        }
    }


def neutral_identifier_result(df):

    return {
        "total_records": len(df),
        "identifier_column_count": 0,
        "identifier_columns": [],
        "candidate_unique_keys": [],
        "repeated_identifier_columns": [],
        "missing_identifier_columns": [],
        "affected_record_count": 0,
        "affected_row_positions": [],
        "column_summary": {},
        "record_details": []
    }


def neutral_conversion_result(df):

    false = _false_series(df)

    return {
        "failed_rows": false.copy(),
        "warning_rows": false.copy(),
        "rejected_rows": false.copy(),
        "report": {
            "total_records": len(df),
            "tracked_columns": 0,
            "attempted_conversions": 0,
            "successful_conversions": 0,
            "failed_conversions": 0,
            "failure_rate_percent": 0.0,
            "affected_record_count": 0,
            "warning_rows": 0,
            "rejected_rows": 0,
            "affected_row_positions": [],
            "column_summary": {},
            "record_details": []
        }
    }


def neutral_numeric_result(df):

    false = _false_series(df)

    return {
        "outlier_rows": false.copy(),
        "range_violation_rows": false.copy(),
        "warning_rows": false.copy(),
        "rejected_rows": false.copy(),
        "report": {
            "total_records": len(df),
            "numeric_column_count": 0,
            "numeric_columns": [],
            "iqr_multiplier": None,
            "minimum_samples": None,
            "total_outlier_cells": 0,
            "total_range_violations": 0,
            "outlier_record_count": 0,
            "range_violation_record_count": 0,
            "affected_record_count": 0,
            "warning_rows": 0,
            "rejected_rows": 0,
            "affected_row_positions": [],
            "column_summary": {},
            "record_details": []
        }
    }


def neutral_date_result(df):

    false = _false_series(df)

    return {
        "warning_rows": false.copy(),
        "rejected_rows": false.copy(),
        "invalid_date_rows": false.copy(),
        "range_violation_rows": false.copy(),
        "future_date_rows": false.copy(),
        "chronology_violation_rows": false.copy(),
        "timezone_mismatch_rows": false.copy(),
        "report": {
            "total_records": len(df),
            "date_column_count": 0,
            "date_columns": [],
            "reference_time": None,
            "invalid_date_record_count": 0,
            "range_violation_record_count": 0,
            "future_date_record_count": 0,
            "chronology_violation_record_count": 0,
            "timezone_mismatch_record_count": 0,
            "affected_record_count": 0,
            "warning_rows": 0,
            "rejected_rows": 0,
            "affected_row_positions": [],
            "column_summary": {},
            "chronological_summary": {},
            "record_details": []
        }
    }


def neutral_contact_result(df):

    false = _false_series(df)

    return {
        "invalid_email_rows": false.copy(),
        "invalid_phone_rows": false.copy(),
        "warning_rows": false.copy(),
        "rejected_rows": false.copy(),
        "report": {
            "total_records": len(df),
            "contact_column_count": 0,
            "email_columns": [],
            "phone_columns": [],
            "total_invalid_emails": 0,
            "total_invalid_phones": 0,
            "invalid_email_record_count": 0,
            "invalid_phone_record_count": 0,
            "affected_record_count": 0,
            "warning_rows": 0,
            "rejected_rows": 0,
            "affected_row_positions": [],
            "column_summary": {},
            "record_details": []
        }
    }


def build_neutral_validation_results(df):
    """Build neutral results for all seven validators."""

    return {
        "missing_values": neutral_missing_value_result(df),
        "duplicates": neutral_duplicate_result(df),
        "identifiers": neutral_identifier_result(df),
        "conversion": neutral_conversion_result(df),
        "numeric": neutral_numeric_result(df),
        "dates": neutral_date_result(df),
        "contacts": neutral_contact_result(df)
    }
