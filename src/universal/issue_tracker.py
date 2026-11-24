import json


ISSUE_MESSAGES = {
    "MISSING_VALUE": "Record contains missing values.",
    "MISSING_REQUIRED_VALUE": "A required field is missing.",
    "EMPTY_RECORD": "Record contains no usable values.",
    "EXACT_DUPLICATE": "Record duplicates an earlier record.",
    "DUPLICATE_KEY": "Record contains a duplicate key.",
    "CONVERSION_FAILURE": "Value could not be converted to the detected data type.",
    "INVALID_EMAIL": "Email address format is invalid.",
    "INVALID_PHONE": "Phone number format is invalid.",
    "INVALID_DATE": "Date value is invalid.",
    "FUTURE_DATE": "Date is later than the permitted reference date.",
    "NUMERIC_OUTLIER": "Numeric value is statistically unusual.",
    "NUMERIC_RANGE_VIOLATION": "Numeric value is outside the configured range."
}


def create_issue(
    code,
    column=None,
    severity="WARNING",
    message=None
):
    """Create a standardized quality issue."""

    if severity not in {"WARNING", "REJECTED"}:
        raise ValueError(
            f"Unsupported issue severity: {severity}"
        )

    if not code:
        raise ValueError("Issue code cannot be empty.")

    return {
        "code": str(code),
        "column": column,
        "severity": severity,
        "message": message or ISSUE_MESSAGES.get(
            code,
            "Data quality validation failed."
        )
    }


def add_issue(
    issue_collection,
    row_position,
    code,
    column=None,
    severity="WARNING",
    message=None
):
    """Add an issue to a specific record."""

    if type(row_position) is not int or row_position < 0:
        raise ValueError("Invalid row position.")

    issue = create_issue(
        code=code,
        column=column,
        severity=severity,
        message=message
    )

    issue_collection.setdefault(
        row_position,
        []
    ).append(issue)


def build_quality_reasons(
    issue_collection,
    total_records
):
    """Generate a quality reason for every record."""

    if type(total_records) is not int or total_records < 0:
        raise ValueError("Invalid record count.")

    results = []

    for position in range(total_records):

        issues = issue_collection.get(
            position,
            []
        )

        has_rejection = any(
            issue["severity"] == "REJECTED"
            for issue in issues
        )

        status = (
            "REJECTED"
            if has_rejection
            else "WARNING"
            if issues
            else "VALID"
        )

        # Remove duplicate issue entries while preserving order.

        unique_issues = []
        seen = set()

        for issue in issues:

            key = (
                issue["code"],
                issue["column"],
                issue["severity"],
                issue["message"]
            )

            if key not in seen:
                seen.add(key)
                unique_issues.append(issue)

        results.append({
            "row_position": position,
            "quality_status": status,
            "quality_reasons": unique_issues
        })

    return results


def generate_issue_summary(record_details):
    """Generate dataset-level issue statistics."""

    summary = {
        "total_affected_records": 0,
        "warning_records": 0,
        "rejected_records": 0,
        "total_issues": 0,
        "issue_code_counts": {}
    }

    for record in record_details:

        issues = record["quality_reasons"]

        if not issues:
            continue

        summary["total_affected_records"] += 1

        if record["quality_status"] == "REJECTED":
            summary["rejected_records"] += 1

        else:
            summary["warning_records"] += 1

        summary["total_issues"] += len(issues)

        for issue in issues:

            code = issue["code"]

            summary["issue_code_counts"][code] = (
                summary["issue_code_counts"].get(code, 0) + 1
            )

    return summary


def validate_issue_report(record_details, total_records):
    """Verify issue report integrity."""

    if len(record_details) != total_records:
        raise ValueError("Record count mismatch.")

    for position, record in enumerate(record_details):

        if record["row_position"] != position:
            raise ValueError("Record position mismatch.")

        issues = record["quality_reasons"]

        expected_status = (
            "REJECTED"
            if any(
                issue["severity"] == "REJECTED"
                for issue in issues
            )
            else "WARNING"
            if issues
            else "VALID"
        )

        if record["quality_status"] != expected_status:
            raise ValueError("Quality status mismatch.")

        for issue in issues:

            if set(issue) != {
                "code",
                "column",
                "severity",
                "message"
            }:
                raise ValueError("Invalid issue structure.")

    return True

def collect_validation_issues(
    df,
    missing_result,
    duplicate_result,
    conversion_result,
    numeric_result,
    date_result,
    contact_result
):
    """
    Collect record-level reasons from all validation modules.

    Uses zero-based row positions to preserve alignment
    with the original DataFrame.
    """

    issues = {}

    def add_mask_issues(
        mask,
        code,
        severity,
        message=None
    ):

        for position, affected in enumerate(mask.tolist()):

            if affected:

                add_issue(
                    issues,
                    position,
                    code,
                    severity=severity,
                    message=message
                )

    # 1. Missing-value validation.

    missing_report = missing_result["report"]

    missing_details = missing_report.get(
        "record_details",
        []
    )

    for detail in missing_details:

        position = detail["row_position"]

        missing_columns = detail.get(
            "missing_columns",
            []
        )

        required_missing = detail.get(
            "missing_required_columns",
            []
        )

        for column in missing_columns:

            required = column in required_missing

            add_issue(
                issues,
                position,
                (
                    "MISSING_REQUIRED_VALUE"
                    if required
                    else "MISSING_VALUE"
                ),
                column=column,
                severity=(
                    "REJECTED"
                    if required
                    else "WARNING"
                )
            )

    add_mask_issues(
        missing_result["empty_rows"],
        "EMPTY_RECORD",
        "REJECTED"
    )

    # 2. Duplicate validation.

    duplicate_report = duplicate_result["report"]

    duplicate_details = duplicate_report.get(
        "record_details",
        []
    )

    if duplicate_details:

        for detail in duplicate_details:

            position = detail.get("row_position")

            if position is not None:

                add_issue(
                    issues,
                    position,
                    detail.get("issue_code", "DUPLICATE_RECORD"),
                    severity="REJECTED"
                )

    else:

        add_mask_issues(
            duplicate_result["rejected_rows"],
            "DUPLICATE_RECORD",
            "REJECTED"
        )

    # 3. Conversion validation.

    add_mask_issues(
        conversion_result["failed_rows"],
        "CONVERSION_FAILURE",
        "WARNING"
    )

    # 4. Numeric validation.

    add_mask_issues(
        numeric_result["outlier_rows"],
        "NUMERIC_OUTLIER",
        "WARNING"
    )

    add_mask_issues(
        numeric_result["range_violation_rows"],
        "NUMERIC_RANGE_VIOLATION",
        "REJECTED"
    )

    # 5. Date validation.

    date_issue_masks = [
        (
            "invalid_date_rows",
            "INVALID_DATE",
            "WARNING"
        ),
        (
            "range_violation_rows",
            "DATE_RANGE_VIOLATION",
            "REJECTED"
        ),
        (
            "future_date_rows",
            "FUTURE_DATE",
            "WARNING"
        ),
        (
            "chronology_violation_rows",
            "CHRONOLOGY_VIOLATION",
            "WARNING"
        ),
        (
            "timezone_mismatch_rows",
            "TIMEZONE_MISMATCH",
            "WARNING"
        )
    ]

    for mask_name, code, severity in date_issue_masks:

        if mask_name in date_result:

            add_mask_issues(
                date_result[mask_name],
                code,
                severity
            )

    # 6. Contact validation.

    contact_details = contact_result[
        "report"
    ].get("record_details", [])

    for detail in contact_details:

        position = detail["row_position"]

        for item in detail.get("issues", []):

            add_issue(
                issues,
                position,
                item["reason"],
                column=item["column"],
                severity=item["severity"]
            )

    return build_quality_reasons(
        issues,
        len(df)
    )