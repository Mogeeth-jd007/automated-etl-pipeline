import pandas as pd

from .missing_value_validator import validate_missing_values
from .duplicate_validator import validate_duplicates
from .identifier_validator import validate_identifiers
from .conversion_validator import validate_conversion_failures
from .numeric_validator import validate_numeric_values
from .date_validator import validate_dates
from .contact_validator import validate_contacts


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
    Validate an unknown dataset using advanced missing-value,
    duplicate, identifier, conversion, numeric, date and
    contact validation.
    """

    print("\n========== UNIVERSAL VALIDATION STARTED ==========")

    df = df.copy()

    if "quality_status" in df.columns:

        raise ValueError(
            "Input contains the reserved column: quality_status"
        )

    # Automatically exclude generated metadata columns.

    excluded_columns = set(excluded_columns or [])

    if schema is not None:

        excluded_columns.update(
            column
            for column, details in schema.items()
            if details.get("generated", False)
        )

    # STEP 1: Missing-value validation.

    missing_result = validate_missing_values(
        df,
        required_columns=required_columns,
        excluded_columns=excluded_columns
    )

    missing_rows = missing_result["missing_rows"]
    empty_rows = missing_result["empty_rows"]

    # STEP 2: Duplicate detection.

    duplicate_result = validate_duplicates(
        df,
        key_columns=key_columns,
        excluded_columns=excluded_columns
    )

    duplicate_rows = duplicate_result["rejected_rows"]

    # STEP 3: Identifier analysis.

    identifier_report = validate_identifiers(
        df,
        schema=schema,
        excluded_columns=excluded_columns
    )

    # STEP 4: Conversion failure validation.

    conversion_result = validate_conversion_failures(
        df,
        schema=schema,
        required_columns=required_columns,
        excluded_columns=excluded_columns
    )

    conversion_report = conversion_result["report"]

    # STEP 5: Numeric range and anomaly validation.

    numeric_result = validate_numeric_values(
        df,
        schema=schema,
        numeric_ranges=numeric_ranges,
        excluded_columns=excluded_columns,
        iqr_multiplier=iqr_multiplier,
        min_samples=min_samples
    )

    numeric_report = numeric_result["report"]

    # STEP 6: Date and timestamp validation.

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

    # STEP 7: Email and phone validation.

    contact_result = validate_contacts(
        df,
        schema=schema,
        required_columns=required_columns,
        excluded_columns=excluded_columns,
        contact_columns=contact_columns
    )

    contact_report = contact_result["report"]

    # STEP 8: Combine validation results.

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

    # Rejection takes priority over warnings.

    warning_mask = warning_mask & ~rejected_mask

    df["quality_status"] = "VALID"

    df.loc[
        warning_mask,
        "quality_status"
    ] = "WARNING"

    df.loc[
        rejected_mask,
        "quality_status"
    ] = "REJECTED"

    # STEP 9: Separate records.

    valid_records = df[
        df["quality_status"] == "VALID"
    ].copy()

    warning_records = df[
        df["quality_status"] == "WARNING"
    ].copy()

    rejected_records = df[
        df["quality_status"] == "REJECTED"
    ].copy()

    # STEP 10: Generate detailed quality report.

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
        "contact_summary": contact_report
    }

    print("\nDATA QUALITY REPORT")

    for key, value in report.items():

        if not key.endswith("_summary"):

            print(f"{key}: {value}")

    print("\nMISSING VALUE SUMMARY")

    print(
        "Missing cells:",
        missing_result["report"]["missing_cells"]
    )

    print(
        "Required missing rows:",
        missing_result["report"]["required_missing_rows"]
    )

    score = missing_result["report"]["completeness_score"]

    if score is None:

        print("Completeness score: N/A")

    else:

        print(f"Completeness score: {score:.2f}%")

    print("\nDUPLICATE SUMMARY")

    duplicate_summary = duplicate_result["report"]

    print(
        "Exact duplicate rows:",
        duplicate_summary["exact_duplicate_rows"]
    )

    print(
        "Key duplicate rows:",
        duplicate_summary["key_duplicate_rows"]
    )

    print(
        "Additional key duplicate rows:",
        duplicate_summary["additional_key_duplicate_rows"]
    )

    print(
        "Total duplicate rows:",
        duplicate_summary["total_duplicate_rows"]
    )

    duplicate_rate = duplicate_summary[
        "duplicate_rate_percent"
    ]

    if duplicate_rate is None:

        print("Duplicate rate: N/A")

    else:

        print(f"Duplicate rate: {duplicate_rate:.2f}%")

    print("\nIDENTIFIER SUMMARY")

    print(
        "Identifier columns:",
        identifier_report["identifier_column_count"]
    )

    print(
        "Detected identifiers:",
        identifier_report["identifier_columns"]
    )

    print(
        "Candidate unique keys:",
        identifier_report["candidate_unique_keys"]
    )

    print(
        "Repeated identifier columns:",
        identifier_report["repeated_identifier_columns"]
    )

    print(
        "Missing identifier columns:",
        identifier_report["missing_identifier_columns"]
    )

    print(
        "Records with identifier observations:",
        identifier_report["affected_record_count"]
    )

    print("\nCONVERSION VALIDATION SUMMARY")

    print(
        "Tracked columns:",
        conversion_report["tracked_columns"]
    )

    print(
        "Attempted conversions:",
        conversion_report["attempted_conversions"]
    )

    print(
        "Successful conversions:",
        conversion_report["successful_conversions"]
    )

    print(
        "Failed conversions:",
        conversion_report["failed_conversions"]
    )

    print(
        "Affected records:",
        conversion_report["affected_record_count"]
    )

    print(
        "Conversion warning rows:",
        conversion_report["warning_rows"]
    )

    print(
        "Conversion rejection rows:",
        conversion_report["rejected_rows"]
    )

    failure_rate = conversion_report["failure_rate_percent"]

    if failure_rate is None:

        print("Conversion failure rate: N/A")

    else:

        print(
            f"Conversion failure rate: {failure_rate:.2f}%"
        )

    print("\nNUMERIC VALIDATION SUMMARY")

    print(
        "Numeric columns:",
        numeric_report["numeric_columns"]
    )

    print(
        "IQR multiplier:",
        numeric_report["iqr_multiplier"]
    )

    print(
        "Minimum reference samples:",
        numeric_report["minimum_samples"]
    )

    print(
        "Statistical outlier cells:",
        numeric_report["total_outlier_cells"]
    )

    print(
        "Numeric range violations:",
        numeric_report["total_range_violations"]
    )

    print(
        "Records containing outliers:",
        numeric_report["outlier_record_count"]
    )

    print(
        "Records containing range violations:",
        numeric_report["range_violation_record_count"]
    )

    print(
        "Numeric warning rows:",
        numeric_report["warning_rows"]
    )

    print(
        "Numeric rejection rows:",
        numeric_report["rejected_rows"]
    )

    print("\nDATE VALIDATION SUMMARY")

    print(
        "Date columns:",
        date_report["date_columns"]
    )

    print(
        "Reference time:",
        date_report["reference_time"]
    )

    print(
        "Invalid date records:",
        date_report["invalid_date_record_count"]
    )

    print(
        "Date range violations:",
        date_report["range_violation_record_count"]
    )

    print(
        "Prohibited future date records:",
        date_report["future_date_record_count"]
    )

    print(
        "Chronological violations:",
        date_report["chronology_violation_record_count"]
    )

    print(
        "Timezone mismatch records:",
        date_report["timezone_mismatch_record_count"]
    )

    print(
        "Date warning rows:",
        date_report["warning_rows"]
    )

    print(
        "Date rejection rows:",
        date_report["rejected_rows"]
    )

    print("\nCONTACT VALIDATION SUMMARY")

    print(
        "Contact columns:",
        contact_report["contact_column_count"]
    )

    print(
        "Email columns:",
        contact_report["email_columns"]
    )

    print(
        "Phone columns:",
        contact_report["phone_columns"]
    )

    print(
        "Invalid email values:",
        contact_report["total_invalid_emails"]
    )

    print(
        "Invalid phone values:",
        contact_report["total_invalid_phones"]
    )

    print(
        "Records containing invalid emails:",
        contact_report["invalid_email_record_count"]
    )

    print(
        "Records containing invalid phones:",
        contact_report["invalid_phone_record_count"]
    )

    print(
        "Affected contact records:",
        contact_report["affected_record_count"]
    )

    print(
        "Contact warning rows:",
        contact_report["warning_rows"]
    )

    print(
        "Contact rejection rows:",
        contact_report["rejected_rows"]
    )

    print("\n========== UNIVERSAL VALIDATION COMPLETED ==========\n")

    return (
        valid_records,
        warning_records,
        rejected_records,
        report
    )
