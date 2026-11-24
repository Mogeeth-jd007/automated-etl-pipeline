
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

from .classification_engine import (
    classify_records,
    generate_classification_summary,
    validate_classification_summary
)

from .quality_scorer import (
    score_records,
    calculate_dataset_quality
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
    contact_columns=None,
    scoring_penalties=None,
    scoring_severity_penalties=None
):
    """
    Execute seven validation modules, intelligent classification
    and record-level/dataset-level quality scoring.

    Existing classification masks remain authoritative whenever
    the intelligent engine disagrees with legacy classification.

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
        "quality_reasons",
        "quality_score",
        "quality_grade"
    }

    existing_reserved = reserved_columns.intersection(df.columns)

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

    # STEP 9: Legacy classification.

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

    warning_mask = warning_mask & ~rejected_mask

    df["quality_status"] = "VALID"

    df.loc[warning_mask, "quality_status"] = "WARNING"

    df.loc[rejected_mask, "quality_status"] = "REJECTED"

    legacy_statuses = df["quality_status"].astype(str).tolist()

    # STEP 10: Collect quality issues.

    quality_details = collect_validation_issues(
        df=df,
        missing_result=missing_result,
        duplicate_result=duplicate_result,
        conversion_result=conversion_result,
        numeric_result=numeric_result,
        date_result=date_result,
        contact_result=contact_result
    )

    if len(quality_details) != len(df):
        raise ValueError(
            "Issue tracker returned an incorrect record count."
        )

    for position, detail in enumerate(quality_details):

        actual_status = legacy_statuses[position]

        detail["legacy_status"] = actual_status

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

    # STEP 11: Intelligent classification.

    print("\n========== INTELLIGENT CLASSIFICATION ==========")

    engine_results = classify_records(quality_details)

    classification_matches = 0
    classification_mismatches = 0
    mismatch_details = []

    final_statuses = []

    for position, result in enumerate(engine_results):

        legacy_status = legacy_statuses[position]
        engine_status = result["quality_status"]

        matches = engine_status == legacy_status

        if matches:
            final_status = engine_status
            classification_matches += 1

        else:
            final_status = legacy_status
            classification_mismatches += 1

            mismatch_details.append({
                "row_position": position,
                "legacy_status": legacy_status,
                "engine_status": engine_status
            })

        result["engine_status"] = engine_status
        result["legacy_status"] = legacy_status
        result["classification_match"] = matches

        result["classification_source"] = (
            "intelligent_engine"
            if matches
            else "legacy_compatibility"
        )

        result["quality_status"] = final_status

        final_statuses.append(final_status)

    df["quality_status"] = final_statuses

    # STEP 12: Generate classification summary.

    classification_summary = (
        generate_classification_summary(engine_results)
    )

    validate_classification_summary(
        classification_summary
    )

    classification_audit = {
        "total_records": int(len(df)),
        "matching_records": int(classification_matches),
        "mismatching_records": int(classification_mismatches),
        "classification_match_rate": (
            round(classification_matches / len(df) * 100, 2)
            if len(df) else 100.0
        ),
        "mismatch_details": mismatch_details,
        "legacy_classification_preserved": True
    }

    # STEP 13: INTELLIGENT QUALITY SCORING.

    print("\n========== INTELLIGENT QUALITY SCORING ==========")

    record_scores = score_records(
        engine_results,
        penalty_config=scoring_penalties,
        severity_penalties=scoring_severity_penalties
    )

    if len(record_scores) != len(df):
        raise ValueError(
            "Quality scorer returned an incorrect record count."
        )

    # Attach individual scores to the detailed records.

    for detail, score_result in zip(
        engine_results,
        record_scores
    ):

        detail["quality_score"] = score_result["quality_score"]
        detail["quality_grade"] = score_result["quality_grade"]
        detail["total_penalty"] = score_result["total_penalty"]
        detail["applied_penalties"] = score_result["applied_penalties"]

    # Add scores to the DataFrame.

    df["quality_score"] = [
        result["quality_score"]
        for result in record_scores
    ]

    df["quality_grade"] = [
        result["quality_grade"]
        for result in record_scores
    ]

    # Calculate overall dataset quality.

    dataset_quality_summary = calculate_dataset_quality(
        record_scores
    )

    print("\nRECORD QUALITY SCORING")

    print(
        "Average dataset score:",
        dataset_quality_summary["dataset_quality_score"]
    )

    print(
        "Dataset grade:",
        dataset_quality_summary["dataset_quality_grade"]
    )

    print(
        "Grade distribution:",
        dataset_quality_summary["grade_distribution"]
    )

    # STEP 14: Generate issue summary.

    issue_summary = generate_issue_summary(
        engine_results
    )

    # STEP 15: Serialize record-level quality reasons.

    df["quality_reasons"] = [
        json.dumps(
            detail["quality_reasons"],
            ensure_ascii=False
        )
        for detail in engine_results
    ]

    # STEP 16: Separate records.

    valid_records = df[
        df["quality_status"] == "VALID"
    ].copy()

    warning_records = df[
        df["quality_status"] == "WARNING"
    ].copy()

    rejected_records = df[
        df["quality_status"] == "REJECTED"
    ].copy()

    # STEP 17: Generate complete quality report.

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

        # Centralized issue tracking.

        "issue_summary": issue_summary,
        "record_quality_details": engine_results,

        # Intelligent classification.

        "classification_summary": classification_summary,
        "classification_audit": classification_audit,

        # Intelligent quality scoring.

        "dataset_quality_summary": dataset_quality_summary
    }

    # STEP 18: Console reporting.

    print("\n========== CLASSIFICATION SUMMARY ==========")

    print(classification_summary)

    print("\n========== CLASSIFICATION AUDIT ==========")

    print(classification_audit)

    print("\n========== DATASET QUALITY SUMMARY ==========")

    print(dataset_quality_summary)

    print("\n========== DATA QUALITY REPORT ==========")

    for key, value in report.items():

        if key not in {
            "record_quality_details",
            "classification_audit"
        } and not key.endswith("_summary"):
            print(f"{key}: {value}")

    print("\n========== ISSUE CODE FREQUENCY ==========")

    for code, count in issue_summary[
        "issue_code_counts"
    ].items():
        print(f"{code}: {count}")

    print("\n========== UNIVERSAL VALIDATION COMPLETED ==========\n")

    # STEP 19: Preserve original four-value return structure.

    return (
        valid_records,
        warning_records,
        rejected_records,
        report
    )
