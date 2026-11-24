import pandas as pd

from src.universal.issue_tracker import (
    collect_validation_issues
)


def test_collect_validation_issues():

    df = pd.DataFrame({
        "email": [
            "valid@example.com",
            "invalid-email",
            "another@example.com"
        ]
    })

    missing = {
        "warning_rows": pd.Series([False, False, False]),
        "rejected_rows": pd.Series([False, False, False]),
        "empty_rows": pd.Series([False, False, False]),
        "report": {
            "record_details": []
        }
    }

    duplicate = {
        "rejected_rows": pd.Series([False, False, True]),
        "report": {}
    }

    conversion = {
        "failed_rows": pd.Series([False, True, False]),
        "warning_rows": pd.Series([False, True, False]),
        "rejected_rows": pd.Series([False, False, False]),
        "report": {}
    }

    numeric = {
        "outlier_rows": pd.Series([False, False, False]),
        "range_violation_rows": pd.Series([False, False, False]),
        "warning_rows": pd.Series([False, False, False]),
        "rejected_rows": pd.Series([False, False, False]),
        "report": {}
    }

    dates = {
        "invalid_date_rows": pd.Series([False, False, False]),
        "range_violation_rows": pd.Series([False, False, False]),
        "future_date_rows": pd.Series([False, False, False]),
        "chronology_violation_rows": pd.Series([False, False, False]),
        "timezone_mismatch_rows": pd.Series([False, False, False]),
        "warning_rows": pd.Series([False, False, False]),
        "rejected_rows": pd.Series([False, False, False]),
        "report": {}
    }

    contacts = {
        "report": {
            "record_details": [
                {
                    "row_position": 1,
                    "issues": [
                        {
                            "column": "email",
                            "reason": "INVALID_EMAIL",
                            "severity": "WARNING"
                        }
                    ]
                }
            ]
        }
    }

    records = collect_validation_issues(
        df,
        missing,
        duplicate,
        conversion,
        numeric,
        dates,
        contacts
    )

    assert len(records) == 3

    assert records[0]["quality_status"] == "VALID"

    assert records[1]["quality_status"] == "WARNING"

    assert records[2]["quality_status"] == "REJECTED"

    codes = {
        issue["code"]
        for issue in records[1]["quality_reasons"]
    }

    assert "CONVERSION_FAILURE" in codes
    assert "INVALID_EMAIL" in codes

    assert records[2]["quality_reasons"][0]["code"] == (
        "DUPLICATE_RECORD"
    )


def test_empty_dataset():

    empty = pd.Series(dtype=bool)

    result = collect_validation_issues(
        pd.DataFrame(),
        {
            "empty_rows": empty,
            "report": {"record_details": []}
        },
        {
            "rejected_rows": empty,
            "report": {}
        },
        {
            "failed_rows": empty,
            "report": {}
        },
        {
            "outlier_rows": empty,
            "range_violation_rows": empty
        },
        {},
        {
            "report": {"record_details": []}
        }
    )

    assert result == []


print("Issue collection tests executed.")

