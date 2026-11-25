
import pandas as pd
import pytest

import universal.universal_pipeline as pipeline


VALIDATORS = {
    "missing_values",
    "duplicates",
    "identifiers",
    "conversion",
    "numeric",
    "dates",
    "contacts"
}


# ============================================================
# TEST DATA GENERATION
# ============================================================

def create_input_csv(tmp_path, df=None):

    tmp_path.mkdir(parents=True, exist_ok=True)

    csv_file = tmp_path / "validation_test.csv"

    if df is None:
        df = pd.DataFrame({
            "customer_id": ["001", "002", "003"],
            "email": [
                "invalid-email",
                "valid@example.com",
                "another-invalid"
            ],
            "amount": [100, 200, 300]
        })

    df.to_csv(csv_file, index=False)

    return csv_file


def create_comprehensive_dataset():

    records = []

    amounts = [
        90, 95, 100, 105, 110, 95,
        100, 105, 90, 110, 100, 100000
    ]

    for position in range(12):

        records.append({
            "customer_id": f"C{position:03d}",

            "email": (
                "invalid-email"
                if position == 0
                else f"user{position}@example.com"
            ),

            "phone_number": (
                "123"
                if position == 1
                else "9876543210"
            ),

            "amount": amounts[position],

            "transaction_date": (
                "not-a-date"
                if position == 9
                else (
                    "2099-12-31"
                    if position == 11
                    else f"2026-01-{position + 1:02d}"
                )
            ),

            "conversion_value": (
                "not-a-number"
                if position == 8
                else str(100 + position)
            ),

            "customer_note": (
                None
                if position == 7
                else "Customer record"
            )
        })

    # Introduce an exact duplicate.
    # Preserve the numeric outlier and future date.
    records[10] = records[5].copy()

    return pd.DataFrame(records)


# ============================================================
# PIPELINE TEST CONFIGURATION
# ============================================================

def configure_pipeline_test(
    tmp_path,
    monkeypatch,
    validation_config,
    input_df=None
):

    csv_file = create_input_csv(
        tmp_path,
        input_df
    )

    # Apply future-date validation only when the
    # supplied dataset actually contains transaction_date.
    date_columns = (
        ["transaction_date"]
        if input_df is not None
        and "transaction_date" in input_df.columns
        else []
    )

    config = {
        "universal_extraction": {},

        "universal_transformation": {},

        "quality_scoring": {
            "penalties": {},
            "severity_penalties": {}
        },

        "retry": {
            "enabled": False,
            "max_attempts": 3,
            "base_delay_seconds": 0,
            "max_delay_seconds": 0
        },

        "universal_validation": validation_config,

        "universal_date_validation": {
            "date_ranges": {},

            "no_future_columns": date_columns,

            "chronological_rules": [],

            # Date-only reference time.
            # This matches the timezone-naive test dates.
            "reference_time": "2026-11-26"
        }
    }

    monkeypatch.setattr(
        pipeline,
        "load_config",
        lambda: config
    )

    monkeypatch.setattr(
        pipeline,
        "resolve_input_file",
        lambda input_file: csv_file
    )

    monkeypatch.setattr(
        pipeline,
        "start_execution",
        lambda **kwargs: {
            "execution_id": "test-execution",
            "database_path": tmp_path / "history.db",
            "monotonic_start": 0,
            "current_stage": None
        }
    )

    def update_execution_stage(execution, stage):
        execution["current_stage"] = stage

    monkeypatch.setattr(
        pipeline,
        "update_execution_stage",
        update_execution_stage
    )

    monkeypatch.setattr(
        pipeline,
        "start_stage",
        lambda execution, stage_name: {
            "stage_name": stage_name
        }
    )

    monkeypatch.setattr(
        pipeline,
        "complete_stage",
        lambda stage: {
            "duration_seconds": 0.001
        }
    )

    monkeypatch.setattr(
        pipeline,
        "fail_stage",
        lambda stage, error: None
    )

    monkeypatch.setattr(
        pipeline,
        "complete_execution",
        lambda execution, **kwargs: {
            "status": "SUCCESS"
        }
    )

    monkeypatch.setattr(
        pipeline,
        "fail_execution",
        lambda execution, **kwargs: None
    )

    monkeypatch.setattr(
        pipeline,
        "load_universal",
        lambda records, table_name: {
            "table_name": table_name,
            "records_loaded": len(records)
        }
    )

    monkeypatch.setattr(
        pipeline,
        "generate_reports",
        lambda *args, **kwargs: {
            "generated": True
        }
    )

    return csv_file


def run_test_pipeline(
    tmp_path,
    monkeypatch,
    validation_config,
    input_df=None
):

    csv_file = configure_pipeline_test(
        tmp_path,
        monkeypatch,
        validation_config,
        input_df
    )

    original_validate = pipeline.validate_universal

    captured_config = {}

    def tracked_validate(*args, **kwargs):

        captured_config.update(
            kwargs.get("validation_config", {})
        )

        return original_validate(
            *args,
            **kwargs
        )

    monkeypatch.setattr(
        pipeline,
        "validate_universal",
        tracked_validate
    )

    result = pipeline.run_universal_pipeline(
        str(csv_file)
    )

    return result, captured_config


# ============================================================
# REPORT HELPERS
# ============================================================

def get_issue_codes(report):

    return {
        issue["code"]
        for record in report["record_quality_details"]
        for issue in record["quality_reasons"]
    }


def get_penalty_codes(report):

    return {
        penalty["code"]
        for record in report["record_quality_details"]
        for penalty in record["applied_penalties"]
    }


# ============================================================
# EXISTING PIPELINE INTEGRATION TESTS
# ============================================================

def test_pipeline_forwards_disabled_contact_configuration(
    tmp_path,
    monkeypatch
):

    result, captured = run_test_pipeline(
        tmp_path,
        monkeypatch,
        {
            "contacts": {
                "enabled": False
            }
        }
    )

    assert captured["contacts"]["enabled"] is False

    report = result["quality_report"]

    assert (
        report["validation_configuration"]["contacts"]["enabled"]
        is False
    )

    assert report["invalid_email_rows"] == 0


def test_pipeline_executes_enabled_contact_validation(
    tmp_path,
    monkeypatch
):

    result, captured = run_test_pipeline(
        tmp_path,
        monkeypatch,
        {
            "contacts": {
                "enabled": True
            }
        }
    )

    assert captured["contacts"]["enabled"] is True

    report = result["quality_report"]

    assert report["invalid_email_rows"] > 0

    assert "INVALID_EMAIL" in get_issue_codes(report)


def test_pipeline_defaults_to_all_validators_enabled(
    tmp_path,
    monkeypatch
):

    result, captured = run_test_pipeline(
        tmp_path,
        monkeypatch,
        {}
    )

    assert captured == {}

    report = result["quality_report"]

    effective_config = report["validation_configuration"]

    assert set(effective_config) == VALIDATORS

    for validator in effective_config.values():
        assert validator["enabled"] is True


def test_pipeline_preserves_execution_and_reports(
    tmp_path,
    monkeypatch
):

    result, captured = run_test_pipeline(
        tmp_path,
        monkeypatch,
        {
            "contacts": {
                "enabled": False
            }
        }
    )

    assert result["database"]["table_name"] == "validation_test"

    assert result["database"]["records_loaded"] == 3

    assert result["files"]["generated"] is True

    assert result["quality_report"]["total_records"] == 3


# ============================================================
# COMPREHENSIVE DATASET TEST
# ============================================================

def test_all_enabled_validators_detect_test_data(
    tmp_path,
    monkeypatch
):

    result, captured = run_test_pipeline(
        tmp_path,
        monkeypatch,
        {},
        create_comprehensive_dataset()
    )

    report = result["quality_report"]

    assert set(report["validation_configuration"]) == VALIDATORS

    for settings in report["validation_configuration"].values():
        assert settings["enabled"] is True

    # Missing-value validation.
    assert report["missing_value_rows"] > 0

    # Duplicate validation.
    assert report["duplicate_rows"] > 0

    # Conversion validation.
    assert report["conversion_failure_rows"] > 0

    assert "CONVERSION_FAILURE" in get_issue_codes(report)

    # Numeric validation.
    assert (
        report["numeric_outlier_rows"] > 0
        or report["numeric_range_violation_rows"] > 0
    )

    # Future-date validation.
    assert report["future_date_rows"] > 0

    assert "FUTURE_DATE" in get_issue_codes(report)

    # Contact validation.
    assert report["invalid_email_rows"] > 0

    assert report["invalid_phone_rows"] > 0

    # Identifier validation.
    assert (
        report["identifier_summary"]["identifier_column_count"] > 0
    )


# ============================================================
# INDIVIDUAL VALIDATOR DISABLING
# ============================================================

@pytest.mark.parametrize(
    "validator, report_fields, issue_codes",
    [
        (
            "missing_values",
            [
                "missing_value_rows",
                "empty_rows"
            ],
            [
                "MISSING_VALUE",
                "MISSING_REQUIRED_VALUE",
                "EMPTY_RECORD"
            ]
        ),
        (
            "duplicates",
            [
                "duplicate_rows"
            ],
            [
                "DUPLICATE_RECORD",
                "EXACT_DUPLICATE",
                "DUPLICATE_KEY"
            ]
        ),
        (
            "identifiers",
            [],
            []
        ),
        (
            "conversion",
            [
                "conversion_failure_rows"
            ],
            [
                "CONVERSION_FAILURE"
            ]
        ),
        (
            "numeric",
            [
                "numeric_outlier_rows",
                "numeric_range_violation_rows"
            ],
            [
                "NUMERIC_OUTLIER",
                "NUMERIC_RANGE_VIOLATION"
            ]
        ),
        (
            "dates",
            [
                "invalid_date_rows",
                "date_range_violation_rows",
                "future_date_rows",
                "chronology_violation_rows",
                "timezone_mismatch_rows"
            ],
            [
                "INVALID_DATE",
                "DATE_RANGE_VIOLATION",
                "FUTURE_DATE"
            ]
        ),
        (
            "contacts",
            [
                "invalid_email_rows",
                "invalid_phone_rows"
            ],
            [
                "INVALID_EMAIL",
                "INVALID_PHONE"
            ]
        )
    ]
)
def test_individual_validator_can_be_disabled(
    tmp_path,
    monkeypatch,
    validator,
    report_fields,
    issue_codes
):

    config = {
        validator: {
            "enabled": False
        }
    }

    result, captured = run_test_pipeline(
        tmp_path,
        monkeypatch,
        config,
        create_comprehensive_dataset()
    )

    report = result["quality_report"]

    effective_config = report["validation_configuration"]

    assert effective_config[validator]["enabled"] is False

    # All other validators must remain enabled.
    for name, settings in effective_config.items():

        if name != validator:
            assert settings["enabled"] is True

    # Disabled validator metrics must be zero.
    for field in report_fields:

        assert report[field] == 0, (
            f"{validator} was disabled but {field} was not zero"
        )

    actual_issues = get_issue_codes(report)

    actual_penalties = get_penalty_codes(report)

    for code in issue_codes:

        assert code not in actual_issues

        assert code not in actual_penalties

    # Identifier validation is reporting-only.
    if validator == "identifiers":

        assert (
            report["identifier_summary"]["identifier_column_count"]
            == 0
        )

        assert (
            report["identifier_summary"]["affected_record_count"]
            == 0
        )


# ============================================================
# IDENTIFIER VALIDATOR DISABLED
# ============================================================

def test_identifier_validator_can_be_disabled(
    tmp_path,
    monkeypatch
):

    result, captured = run_test_pipeline(
        tmp_path,
        monkeypatch,
        {
            "identifiers": {
                "enabled": False
            }
        },
        create_comprehensive_dataset()
    )

    report = result["quality_report"]

    assert (
        report["validation_configuration"]["identifiers"]["enabled"]
        is False
    )

    assert report["identifier_summary"]["identifier_column_count"] == 0

    assert report["identifier_summary"]["affected_record_count"] == 0


# ============================================================
# MIXED CONFIGURATION TEST
# ============================================================

def test_mixed_validator_configuration(
    tmp_path,
    monkeypatch
):

    config = {
        "missing_values": {
            "enabled": False
        },

        "duplicates": {
            "enabled": True
        },

        "identifiers": {
            "enabled": False
        },

        "conversion": {
            "enabled": True
        },

        "numeric": {
            "enabled": False
        },

        "dates": {
            "enabled": True
        },

        "contacts": {
            "enabled": False
        }
    }

    result, captured = run_test_pipeline(
        tmp_path,
        monkeypatch,
        config,
        create_comprehensive_dataset()
    )

    report = result["quality_report"]

    effective = report["validation_configuration"]

    # Verify all seven settings.
    for validator, settings in config.items():

        assert (
            effective[validator]["enabled"]
            == settings["enabled"]
        )

    # Disabled validators must contribute no issues.
    assert report["missing_value_rows"] == 0

    assert report["duplicate_rows"] > 0

    assert report["conversion_failure_rows"] > 0

    assert report["numeric_outlier_rows"] == 0

    assert report["numeric_range_violation_rows"] == 0

    assert report["future_date_rows"] > 0

    assert report["invalid_email_rows"] == 0

    assert report["invalid_phone_rows"] == 0

    assert report["identifier_summary"]["identifier_column_count"] == 0

    # Enabled conversion validation must still execute.
    assert "CONVERSION_FAILURE" in get_issue_codes(report)

    # Enabled date validation must still execute.
    assert "FUTURE_DATE" in get_issue_codes(report)


# ============================================================
# ALL VALIDATORS DISABLED
# ============================================================

def test_all_validators_can_be_disabled(
    tmp_path,
    monkeypatch
):

    config = {
        validator: {
            "enabled": False
        }
        for validator in VALIDATORS
    }

    result, captured = run_test_pipeline(
        tmp_path,
        monkeypatch,
        config,
        create_comprehensive_dataset()
    )

    report = result["quality_report"]

    for validator in VALIDATORS:

        assert (
            report["validation_configuration"][validator]["enabled"]
            is False
        )

    assert report["missing_value_rows"] == 0

    assert report["duplicate_rows"] == 0

    assert report["conversion_failure_rows"] == 0

    assert report["numeric_outlier_rows"] == 0

    assert report["numeric_range_violation_rows"] == 0

    assert report["invalid_date_rows"] == 0

    assert report["date_range_violation_rows"] == 0

    assert report["future_date_rows"] == 0

    assert report["chronology_violation_rows"] == 0

    assert report["timezone_mismatch_rows"] == 0

    assert report["invalid_email_rows"] == 0

    assert report["invalid_phone_rows"] == 0

    assert report["identifier_summary"]["identifier_column_count"] == 0

    assert report["issue_summary"]["total_issues"] == 0

    assert get_issue_codes(report) == set()

    assert get_penalty_codes(report) == set()

    assert (
        report["dataset_quality_summary"]["dataset_quality_score"]
        == 100.0
    )


# ============================================================
# IDENTIFIER REPORTING-ONLY BEHAVIOUR
# ============================================================

def test_identifier_validation_does_not_affect_quality_score(
    tmp_path,
    monkeypatch
):

    config = {
        validator: {
            "enabled": validator == "identifiers"
        }
        for validator in VALIDATORS
    }

    result, captured = run_test_pipeline(
        tmp_path,
        monkeypatch,
        config,
        create_comprehensive_dataset()
    )

    report = result["quality_report"]

    assert report["identifier_summary"]["identifier_column_count"] > 0

    assert report["issue_summary"]["total_issues"] == 0

    assert (
        report["dataset_quality_summary"]["dataset_quality_score"]
        == 100.0
    )

    assert get_penalty_codes(report) == set()
