
import pytest

from src.universal.quality_scorer import (
    score_record,
    score_records,
    get_quality_grade,
    calculate_dataset_quality,
    validate_penalty_config
)


def test_perfect_record_score():
    result = score_record([])

    assert result["quality_score"] == 100
    assert result["quality_grade"] == "EXCELLENT"


def test_single_invalid_email():
    result = score_record([
        {
            "code": "INVALID_EMAIL",
            "column": "email",
            "severity": "WARNING"
        }
    ])

    assert result["quality_score"] == 90
    assert result["total_penalty"] == 10


def test_multiple_issues():
    result = score_record([
        {
            "code": "INVALID_EMAIL",
            "column": "email",
            "severity": "WARNING"
        },
        {
            "code": "INVALID_PHONE",
            "column": "mobile",
            "severity": "WARNING"
        }
    ])

    assert result["quality_score"] == 80


def test_duplicate_issue_not_penalized_twice():
    issue = {
        "code": "INVALID_EMAIL",
        "column": "email",
        "severity": "WARNING"
    }

    result = score_record([issue, issue])

    assert result["quality_score"] == 90
    assert result["issue_count"] == 1


def test_same_issue_on_different_columns():
    result = score_record([
        {
            "code": "MISSING_VALUE",
            "column": "email",
            "severity": "WARNING"
        },
        {
            "code": "MISSING_VALUE",
            "column": "mobile",
            "severity": "WARNING"
        }
    ])

    assert result["quality_score"] == 84
    assert result["issue_count"] == 2


def test_score_never_below_zero():
    result = score_record([
        {
            "code": "EMPTY_RECORD",
            "column": None,
            "severity": "REJECTED"
        },
        {
            "code": "DUPLICATE_RECORD",
            "column": None,
            "severity": "REJECTED"
        },
        {
            "code": "MISSING_REQUIRED_VALUE",
            "column": "employee_id",
            "severity": "REJECTED"
        }
    ])

    assert result["total_penalty"] == 120
    assert result["quality_score"] == 0
    assert result["quality_grade"] == "CRITICAL"


def test_custom_penalty():
    result = score_record(
        [{
            "code": "INVALID_EMAIL",
            "column": "email",
            "severity": "WARNING"
        }],
        penalty_config={"INVALID_EMAIL": 20}
    )

    assert result["quality_score"] == 80


def test_unknown_issue_uses_severity_fallback():
    result = score_record([
        {
            "code": "UNKNOWN_ISSUE",
            "column": "field",
            "severity": "WARNING"
        }
    ])

    assert result["quality_score"] == 95


def test_quality_grade_boundaries():
    assert get_quality_grade(100) == "EXCELLENT"
    assert get_quality_grade(90) == "EXCELLENT"
    assert get_quality_grade(89) == "GOOD"
    assert get_quality_grade(75) == "GOOD"
    assert get_quality_grade(74) == "FAIR"
    assert get_quality_grade(60) == "FAIR"
    assert get_quality_grade(59) == "POOR"
    assert get_quality_grade(40) == "POOR"
    assert get_quality_grade(39) == "CRITICAL"
    assert get_quality_grade(0) == "CRITICAL"


def test_multiple_record_scoring():
    records = [
        {"quality_reasons": []},
        {
            "quality_reasons": [
                {
                    "code": "INVALID_EMAIL",
                    "column": "email",
                    "severity": "WARNING"
                }
            ]
        }
    ]

    results = score_records(records)

    assert results[0]["quality_score"] == 100
    assert results[1]["quality_score"] == 90


def test_dataset_average_score():
    records = [
        {"quality_score": 100},
        {"quality_score": 80},
        {"quality_score": 60}
    ]

    result = calculate_dataset_quality(records)

    assert result["dataset_quality_score"] == 80
    assert result["dataset_quality_grade"] == "GOOD"


def test_dataset_grade_distribution():
    records = [
        {"quality_score": 100},
        {"quality_score": 95},
        {"quality_score": 80},
        {"quality_score": 50},
        {"quality_score": 20}
    ]

    result = calculate_dataset_quality(records)

    assert result["grade_distribution"] == {
        "EXCELLENT": 2,
        "GOOD": 1,
        "POOR": 1,
        "CRITICAL": 1
    }


def test_empty_dataset():
    result = calculate_dataset_quality([])

    assert result["total_records"] == 0
    assert result["dataset_quality_score"] is None
    assert result["dataset_quality_grade"] == "NO_DATA"


def test_invalid_penalty():
    with pytest.raises(ValueError):
        validate_penalty_config({
            "INVALID_EMAIL": -10
        })


def test_invalid_issue_structure():
    with pytest.raises(ValueError):
        score_record([
            {
                "code": "INVALID_EMAIL",
                "column": "email",
                "severity": "UNKNOWN"
            }
        ])


def test_invalid_input_type():
    with pytest.raises(TypeError):
        score_record("INVALID_EMAIL")


def test_invalid_record_score():
    with pytest.raises(ValueError):
        calculate_dataset_quality([
            {"quality_score": 150}
        ])


def test_original_records_are_not_modified():
    records = [
        {"quality_reasons": []}
    ]

    score_records(records)

    assert "quality_score" not in records[0]


def test_penalty_configuration_validation():
    validate_penalty_config({
        "INVALID_EMAIL": 15,
        "INVALID_PHONE": 12
    })
