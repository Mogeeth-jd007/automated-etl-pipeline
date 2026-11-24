
"""
Intelligent record classification engine.

Determines VALID, WARNING or REJECTED
using standardized quality issue information.
"""


VALID_STATUSES = {
    "VALID",
    "WARNING",
    "REJECTED"
}


VALID_SEVERITIES = {
    "WARNING",
    "REJECTED"
}


DEFAULT_CRITICAL_ISSUE_CODES = {
    "MISSING_REQUIRED_VALUE",
    "EMPTY_RECORD",
    "EXACT_DUPLICATE",
    "DUPLICATE_KEY",
    "DUPLICATE_RECORD",
    "NUMERIC_RANGE_VIOLATION",
    "DATE_RANGE_VIOLATION"
}


def classify_record(
    quality_reasons,
    critical_issue_codes=None
):
    """
    Classify one record based on its quality issues.

    Rules:
    1. No issues means VALID.
    2. Any REJECTED issue means REJECTED.
    3. Explicitly configured critical issues mean REJECTED.
    4. Other issues mean WARNING.

    Multiple warnings do not automatically cause rejection.
    """

    if not isinstance(quality_reasons, list):
        raise TypeError(
            "quality_reasons must be a list."
        )

    critical_codes = (
        DEFAULT_CRITICAL_ISSUE_CODES
        if critical_issue_codes is None
        else set(critical_issue_codes)
    )

    if not all(
        isinstance(code, str) and code
        for code in critical_codes
    ):
        raise ValueError(
            "Critical issue codes must be non-empty strings."
        )

    if not quality_reasons:
        return "VALID"

    has_warning = False

    for issue in quality_reasons:

        if not isinstance(issue, dict):
            raise TypeError(
                "Every quality issue must be a dictionary."
            )

        if "code" not in issue or "severity" not in issue:
            raise ValueError(
                "Every issue must contain code and severity."
            )

        code = issue["code"]
        severity = issue["severity"]

        if not isinstance(code, str) or not code:
            raise ValueError("Issue code must be non-empty.")

        if severity not in VALID_SEVERITIES:
            raise ValueError(
                f"Unsupported issue severity: {severity}"
            )

        # Critical issue priority.
        if code in critical_codes:
            return "REJECTED"

        # Explicit rejection priority.
        if severity == "REJECTED":
            return "REJECTED"

        if severity == "WARNING":
            has_warning = True

    return "WARNING" if has_warning else "VALID"


def classify_records(
    record_details,
    critical_issue_codes=None
):
    """
    Classify multiple records.

    Returns new dictionaries without modifying
    the original record details.
    """

    if not isinstance(record_details, list):
        raise TypeError(
            "record_details must be a list."
        )

    classified_records = []

    for detail in record_details:

        if not isinstance(detail, dict):
            raise TypeError(
                "Every record detail must be a dictionary."
            )

        if "quality_reasons" not in detail:
            raise ValueError(
                "Record is missing quality_reasons."
            )

        record = detail.copy()

        record["quality_status"] = classify_record(
            record["quality_reasons"],
            critical_issue_codes=critical_issue_codes
        )

        classified_records.append(record)

    return classified_records


def generate_classification_summary(record_details):
    """Generate dataset-level classification statistics."""

    summary = {
        "total_records": len(record_details),
        "valid_records": 0,
        "warning_records": 0,
        "rejected_records": 0
    }

    for record in record_details:

        status = record.get("quality_status")

        if status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid classification status: {status}"
            )

        if status == "VALID":
            summary["valid_records"] += 1

        elif status == "WARNING":
            summary["warning_records"] += 1

        elif status == "REJECTED":
            summary["rejected_records"] += 1

    return summary


def validate_classification_summary(summary):
    """Verify classification totals."""

    required_keys = {
        "total_records",
        "valid_records",
        "warning_records",
        "rejected_records"
    }

    if not required_keys.issubset(summary):
        raise ValueError(
            "Classification summary is incomplete."
        )

    total = (
        summary["valid_records"]
        + summary["warning_records"]
        + summary["rejected_records"]
    )

    if total != summary["total_records"]:
        raise ValueError(
            "Classification record counts do not match."
        )

    return True
