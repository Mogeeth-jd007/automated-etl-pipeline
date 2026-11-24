import json
import pytest

from src.universal.issue_tracker import (
    create_issue,
    add_issue,
    build_quality_reasons,
    generate_issue_summary,
    validate_issue_report
)


def test_issue_creation():

    issue = create_issue(
        "INVALID_EMAIL",
        "email",
        "WARNING"
    )

    assert issue["code"] == "INVALID_EMAIL"
    assert issue["severity"] == "WARNING"
    assert issue["column"] == "email"


def test_multiple_issues_per_record():

    issues = {}

    add_issue(issues, 0, "INVALID_EMAIL", "email")
    add_issue(issues, 0, "INVALID_PHONE", "mobile")

    result = build_quality_reasons(issues, 1)

    assert len(result[0]["quality_reasons"]) == 2


def test_rejection_priority():

    issues = {}

    add_issue(issues, 0, "INVALID_EMAIL")
    add_issue(issues, 0, "DUPLICATE_KEY", severity="REJECTED")

    result = build_quality_reasons(issues, 1)

    assert result[0]["quality_status"] == "REJECTED"


def test_valid_record():

    result = build_quality_reasons({}, 1)

    assert result[0]["quality_status"] == "VALID"
    assert result[0]["quality_reasons"] == []


def test_warning_record():

    issues = {}

    add_issue(issues, 0, "INVALID_PHONE")

    result = build_quality_reasons(issues, 1)

    assert result[0]["quality_status"] == "WARNING"


def test_duplicate_issue_removal():

    issues = {}

    add_issue(issues, 0, "INVALID_EMAIL")
    add_issue(issues, 0, "INVALID_EMAIL")

    result = build_quality_reasons(issues, 1)

    assert len(result[0]["quality_reasons"]) == 1


def test_issue_summary():

    issues = {}

    add_issue(issues, 0, "INVALID_EMAIL")
    add_issue(issues, 1, "DUPLICATE_KEY", severity="REJECTED")

    records = build_quality_reasons(issues, 3)

    summary = generate_issue_summary(records)

    assert summary["total_affected_records"] == 2
    assert summary["warning_records"] == 1
    assert summary["rejected_records"] == 1
    assert summary["total_issues"] == 2


def test_report_integrity():

    issues = {}

    add_issue(issues, 0, "INVALID_EMAIL")

    records = build_quality_reasons(issues, 2)

    assert validate_issue_report(records, 2)


def test_invalid_severity():

    with pytest.raises(ValueError):

        create_issue(
            "INVALID_EMAIL",
            severity="UNKNOWN"
        )


def test_invalid_position():

    with pytest.raises(ValueError):

        add_issue({}, -1, "INVALID_EMAIL")


def test_json_compatibility():

    records = build_quality_reasons({}, 2)

    json.dumps(records, allow_nan=False)


def test_invalid_report_count():

    with pytest.raises(ValueError):

        validate_issue_report([], 2)
