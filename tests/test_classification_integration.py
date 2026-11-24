import json

from src.universal.issue_tracker import (
    build_quality_reasons
)

from src.universal.classification_engine import (
    classify_records,
    generate_classification_summary,
    validate_classification_summary
)


def test_issue_tracker_to_classification():

    issues = {}

    # Record 0: No issues.
    # Record 1: Invalid email.
    # Record 2: Duplicate record.
    # Record 3: Multiple warnings.

    from src.universal.issue_tracker import add_issue

    add_issue(issues, 1, "INVALID_EMAIL")

    add_issue(
        issues,
        2,
        "DUPLICATE_RECORD",
        severity="REJECTED"
    )

    add_issue(issues, 3, "INVALID_PHONE")
    add_issue(issues, 3, "MISSING_VALUE")

    details = build_quality_reasons(issues, 4)

    classified = classify_records(details)

    statuses = [
        record["quality_status"]
        for record in classified
    ]

    assert statuses == [
        "VALID",
        "WARNING",
        "REJECTED",
        "WARNING"
    ]


def test_classification_summary_integration():

    issues = {}

    from src.universal.issue_tracker import add_issue

    add_issue(issues, 1, "INVALID_EMAIL")
    add_issue(
        issues,
        2,
        "DUPLICATE_RECORD",
        severity="REJECTED"
    )

    details = build_quality_reasons(issues, 3)

    classified = classify_records(details)

    summary = generate_classification_summary(classified)

    assert summary == {
        "total_records": 3,
        "valid_records": 1,
        "warning_records": 1,
        "rejected_records": 1
    }

    assert validate_classification_summary(summary)


def test_classification_json_compatibility():

    issues = {}

    from src.universal.issue_tracker import add_issue

    add_issue(issues, 0, "INVALID_EMAIL")

    details = build_quality_reasons(issues, 2)

    classified = classify_records(details)

    serialized = json.dumps(classified)

    restored = json.loads(serialized)

    assert len(restored) == 2
    assert restored[0]["quality_status"] == "WARNING"
    assert restored[1]["quality_status"] == "VALID"


print("Classification integration tests completed.")
