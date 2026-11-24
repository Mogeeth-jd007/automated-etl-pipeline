
import json
import pandas as pd

from .missing_value_validator import validate_missing_values
from .duplicate_validator import validate_duplicates
from .identifier_validator import validate_identifiers
from .conversion_validator import validate_conversion_failures
from .numeric_validator import validate_numeric_values
from .date_validator import validate_dates
from .contact_validator import validate_contacts

from .issue_tracker import (
    collect_validation_issues,
    generate_issue_summary
)


def validate_universal(
    df,
    required_columns=None,
    excluded_columns=None,
    key_columns=None,
    schema=None,
    numeric_ranges=None,
    iqr_multiplier=1.5,
    min_samples=8,
    date_ranges=None,
    no_future_columns=None,
    chronological_rules=None,
    reference_time=None,
    contact_columns=None
):
    """
    Execute all seven validation modules and generate
    record-level quality explanations.

    Returns:
        valid_records,
        warning_records,
        rejected_records,
        report
    """

    print("\n========== UNIVERSAL VALIDATION STARTED ==========")

    df = df.copy()

    # STEP 1: Protect generated columns.

    reserved_columns = {
        "quality_status",
        "quality_reasons"
    }

    existing_reserved = reserved_columns.intersection(
        df.columns
    )

    if existing_reserved:
        raise ValueError(
            f"Input contains reserved columns: "
            f"{sorted(existing_reserved)}"
        )

    excluded_columns = set(excluded_columns or [])

    if schema is not None:
        excluded_columns.update(
            column
            for column, details in schema.items()
            if details.get("generated", False)
        )

    # STEP 2: Missing-value validation.

    missing_result = validate_missing_values(
        df,
        required_columns=required_columns,
        excluded_columns=excluded_columns
    )

    missing_rows = missing_result["missing_rows"]
    empty_rows = missing_result["empty_rows"]

    # STEP 3: Duplicate validation.

    duplicate_result = validate_duplicates(
        df,
        key_columns=key_columns,
        excluded_columns=excluded_columns
    )

    duplicate_rows = duplicate_result["rejected_rows"]

    # STEP 4: Identifier validation.

    identifier_report = validate_identifiers(
        df,
        schema=schema,
        excluded_columns=excluded_columns
    )

    # STEP 5: Conversion validation.

    conversion_result = validate_conversion_failures(
        df,
        schema=schema,
        required_columns=required_columns,
        excluded_columns=excluded_columns
    )

    conversion_report = conversion_result["report"]

    # STEP 6: Numeric validation.

    numeric_result = validate_numeric_values(
        df,
        schema=schema,
        numeric_ranges=numeric_ranges,
        excluded_columns=excluded_columns,
        iqr_multiplier=iqr_multiplier,
        min_samples=min_samples
    )

    numeric_report = numeric_result["report"]

    # STEP 7: Date validation.

    date_result = validate_dates(
        df,
        schema=schema,
        date_ranges=date_ranges,
        no_future_columns=no_future_columns,
        chronological_rules=chronological_rules,
        excluded_columns=excluded_columns,
        reference_time=reference_time
    )

    date_report = date_result["report"]

    # STEP 8: Contact validation.

    contact_result = validate_contacts(
        df,
        schema=schema,
        required_columns=required_columns,
        excluded_columns=excluded_columns,
        contact_columns=contact_columns
    )

    contact_report = contact_result["report"]

    # STEP 9: Combine existing classification masks.

    warning_mask = (
        missing_result["warning_rows"]
        | conversion_result["warning_rows"]
        | numeric_result["warning_rows"]
        | date_result["warning_rows"]
        | contact_result["warning_rows"]
    )

    rejected_mask = (
        missing_result["rejected_rows"]
        | duplicate_rows
        | conversion_result["rejected_rows"]
        | numeric_result["rejected_rows"]
        | date_result["rejected_rows"]
        | contact_result["rejected_rows"]
    )

    # Rejection has priority over warning.

    warning_mask = warning_mask & ~rejected_mask

    df["quality_status"] = "VALID"

    df.loc[warning_mask, "quality_status"] = "WARNING"

    df.loc[rejected_mask, "quality_status"] = "REJECTED"

    # STEP 10: Collect record-level issue explanations.

    quality_details = collect_validation_issues(
        df=df,
        missing_result=missing_result,
        duplicate_result=duplicate_result,
        conversion_result=conversion_result,
        numeric_result=numeric_result,
        date_result=date_result,
        contact_result=contact_result
    )

    # Make explanations agree with actual classification.

    quality_reasons_column = []

    for position, detail in enumerate(quality_details):

        actual_status = df.iloc[position]["quality_status"]

        detail["quality_status"] = actual_status

        if (
            actual_status != "VALID"
            and not detail["quality_reasons"]
        ):
            detail["quality_reasons"].append({
                "code": "QUALITY_VALIDATION_FAILURE",
                "column": None,
                "severity": actual_status,
                "message": (
                    "Record was classified by a validation rule "
                    "without an available detailed explanation."
                )
            })

        quality_reasons_column.append(
            json.dumps(
                detail["quality_reasons"],
                ensure_ascii=False
            )
        )

    df["quality_reasons"] = quality_reasons_column

    issue_summary = generate_issue_summary(
        quality_details
    )

    # STEP 11: Separate records.

    valid_records = df[
        df["quality_status"] == "VALID"
    ].copy()

    warning_records = df[
        df["quality_status"] == "WARNING"
    ].copy()

    rejected_records = df[
        df["quality_status"] == "REJECTED"
    ].copy()

    # STEP 12: Generate complete quality report.

    report = {
        "total_records": int(len(df)),
        "valid_records": int(len(valid_records)),
        "warning_records": int(len(warning_records)),
        "rejected_records": int(len(rejected_records)),

        "missing_value_rows": int(missing_rows.sum()),
        "duplicate_rows": int(duplicate_rows.sum()),
        "empty_rows": int(empty_rows.sum()),

        "conversion_failure_rows": int(
            conversion_result["failed_rows"].sum()
        ),

        "numeric_outlier_rows": int(
            numeric_result["outlier_rows"].sum()
        ),

        "numeric_range_violation_rows": int(
            numeric_result["range_violation_rows"].sum()
        ),

        "invalid_date_rows": int(
            date_result["invalid_date_rows"].sum()
        ),

        "date_range_violation_rows": int(
            date_result["range_violation_rows"].sum()
        ),

        "future_date_rows": int(
            date_result["future_date_rows"].sum()
        ),

        "chronology_violation_rows": int(
            date_result["chronology_violation_rows"].sum()
        ),

        "timezone_mismatch_rows": int(
            date_result["timezone_mismatch_rows"].sum()
        ),

        "invalid_email_rows": int(
            contact_result["invalid_email_rows"].sum()
        ),

        "invalid_phone_rows": int(
            contact_result["invalid_phone_rows"].sum()
        ),

        "excluded_columns": sorted(excluded_columns),

        "missing_value_summary": missing_result["report"],
        "duplicate_summary": duplicate_result["report"],
        "identifier_summary": identifier_report,
        "conversion_summary": conversion_report,
        "numeric_summary": numeric_report,
        "date_summary": date_report,
        "contact_summary": contact_report,

        # NEW: Centralized issue tracking.

        "issue_summary": issue_summary,
        "record_quality_details": quality_details
    }

    # STEP 13: Console reporting.

    print("\n========== DATA QUALITY REPORT ==========")

    for key, value in report.items():

        if not key.endswith("_summary") and key != "record_quality_details":
            print(f"{key}: {value}")

    print("\n========== RECORD-LEVEL ISSUE SUMMARY ==========")

    print(
        "Affected records:",
        issue_summary["total_affected_records"]
    )

    print(
        "Warning records:",
        issue_summary["warning_records"]
    )

    print(
        "Rejected records:",
        issue_summary["rejected_records"]
    )

    print(
        "Total issues:",
        issue_summary["total_issues"]
    )

    print("\nISSUE CODE FREQUENCY")

    for code, count in issue_summary[
        "issue_code_counts"
    ].items():
        print(f"{code}: {count}")

    print("\n========== UNIVERSAL VALIDATION COMPLETED ==========\n")

    # STEP 14: Preserve original four-value return structure.

    return (
        valid_records,
        warning_records,
        rejected_records,
        report
    )
