import pytest

from src.universal.classification_engine import (
    classify_record,
    classify_records,
    generate_classification_summary,
    validate_classification_summary
)


def test_valid_record():
    assert classify_record([]) == "VALID"


def test_single_warning():
    issues = [
        {"code": "INVALID_EMAIL", "severity": "WARNING"}
    ]
    assert classify_record(issues) == "WARNING"


def test_multiple_warnings():
    issues = [
        {"code": "INVALID_EMAIL", "severity": "WARNING"},
        {"code": "INVALID_PHONE", "severity": "WARNING"},
        {"code": "MISSING_VALUE", "severity": "WARNING"}
    ]
    assert classify_record(issues) == "WARNING"


def test_rejection_priority():
    issues = [
        {"code": "INVALID_EMAIL", "severity": "WARNING"},
        {"code": "DUPLICATE_RECORD", "severity": "REJECTED"}
    ]
    assert classify_record(issues) == "REJECTED"


def test_critical_issue_priority():
    issues = [
        {"code": "MISSING_REQUIRED_VALUE", "severity": "WARNING"}
    ]
    assert classify_record(issues) == "REJECTED"


def test_custom_critical_issue_codes():
    issues = [
        {"code": "INVALID_EMAIL", "severity": "WARNING"}
    ]
    assert classify_record(
        issues,
        critical_issue_codes={"INVALID_EMAIL"}
    ) == "REJECTED"


def test_multiple_record_classification():
    records = [
        {"row_position": 0, "quality_reasons": []},
        {
            "row_position": 1,
            "quality_reasons": [
                {"code": "INVALID_EMAIL", "severity": "WARNING"}
            ]
        },
        {
            "row_position": 2,
            "quality_reasons": [
                {"code": "DUPLICATE_RECORD", "severity": "REJECTED"}
            ]
        }
    ]

    result = classify_records(records)

    assert [r["quality_status"] for r in result] == [
        "VALID", "WARNING", "REJECTED"
    ]


def test_original_records_are_not_modified():
    records = [{"quality_reasons": []}]

    classify_records(records)

    assert "quality_status" not in records[0]


def test_classification_summary():
    records = [
        {"quality_status": "VALID"},
        {"quality_status": "VALID"},
        {"quality_status": "WARNING"},
        {"quality_status": "REJECTED"}
    ]

    summary = generate_classification_summary(records)

    assert summary["total_records"] == 4
    assert summary["valid_records"] == 2
    assert summary["warning_records"] == 1
    assert summary["rejected_records"] == 1


def test_summary_integrity():
    summary = {
        "total_records": 3,
        "valid_records": 1,
        "warning_records": 1,
        "rejected_records": 1
    }

    assert validate_classification_summary(summary)


def test_invalid_severity():
    with pytest.raises(ValueError):
        classify_record([
            {"code": "INVALID_EMAIL", "severity": "UNKNOWN"}
        ])


def test_invalid_issue_structure():
    with pytest.raises(ValueError):
        classify_record([{"code": "INVALID_EMAIL"}])


def test_invalid_input_type():
    with pytest.raises(TypeError):
        classify_record("INVALID_EMAIL")


def test_inconsistent_summary():
    summary = {
        "total_records": 5,
        "valid_records": 2,
        "warning_records": 1,
        "rejected_records": 1
    }

    with pytest.raises(ValueError):
        validate_classification_summary(summary)
