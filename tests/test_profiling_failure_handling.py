
import pandas as pd
import pytest

from universal import universal_pipeline as pipeline


def test_profiling_failure_marks_stage_and_execution_failed(
    monkeypatch,
    tmp_path
):
    """Verify profiling failures propagate through both trackers."""

    source_file = tmp_path / "test_dataset.csv"

    source_df = pd.DataFrame({
        "customer_id": ["C001", "C002"],
        "quantity": [10, 20]
    })

    source_file.write_text(
        "customer_id,quantity\nC001,10\nC002,20",
        encoding="utf-8"
    )

    execution = {
        "execution_id": "test-execution-001",
        "database_path": str(tmp_path / "test.db"),
        "current_stage": None
    }

    stage_failures = []
    execution_failures = []

    # Mock execution tracking.

    monkeypatch.setattr(
        pipeline,
        "start_execution",
        lambda **kwargs: execution
    )

    def update_stage(execution, stage_name):
        execution["current_stage"] = stage_name

    monkeypatch.setattr(
        pipeline,
        "update_execution_stage",
        update_stage
    )

    # Mock stage tracking.

    def start_test_stage(execution, stage_name):
        return {"stage_name": stage_name}

    monkeypatch.setattr(
        pipeline,
        "start_stage",
        start_test_stage
    )

    monkeypatch.setattr(
        pipeline,
        "complete_stage",
        lambda stage: {
            "duration_seconds": 0.01
        }
    )

    def record_stage_failure(stage, error):
        stage_failures.append({
            "stage": stage["stage_name"],
            "error": error
        })

    monkeypatch.setattr(
        pipeline,
        "fail_stage",
        record_stage_failure
    )

    def record_execution_failure(
        execution,
        **kwargs
    ):
        execution_failures.append({
            "execution": execution,
            "details": kwargs
        })

    monkeypatch.setattr(
        pipeline,
        "fail_execution",
        record_execution_failure
    )

    # Disable retries for deterministic testing.

    monkeypatch.setattr(
        pipeline,
        "load_retry_config",
        lambda: {
            "enabled": False,
            "max_attempts": 1,
            "base_delay_seconds": 0,
            "max_delay_seconds": 0
        }
    )

    # Mock input extraction.

    monkeypatch.setattr(
        pipeline,
        "resolve_input_file",
        lambda path: source_file
    )

    monkeypatch.setattr(
        pipeline,
        "extract_universal",
        lambda *args, **kwargs: source_df.copy()
    )

    # Mock transformation.

    monkeypatch.setattr(
        pipeline,
        "transform_universal",
        lambda df, **kwargs: (
            df.copy(),
            {}
        )
    )

    # Mock scoring configuration.

    monkeypatch.setattr(
        pipeline,
        "load_quality_scoring_config",
        lambda: ({}, {})
    )

    # Mock configuration.

    monkeypatch.setattr(
        pipeline,
        "load_config",
        lambda: {
            "universal_transformation": {},
            "universal_validation": {}
        }
    )

    monkeypatch.setattr(
        pipeline,
        "load_date_validation_config",
        lambda: {
            "date_ranges": {},
            "no_future_columns": [],
            "chronological_rules": [],
            "reference_time": None
        }
    )

    # Mock successful validation.

    valid = source_df.copy()

    warning = pd.DataFrame(
        columns=source_df.columns
    )

    rejected = pd.DataFrame(
        columns=source_df.columns
    )

    report = {
        "total_records": 2,
        "valid_records": 2,
        "warning_records": 0,
        "rejected_records": 0
    }

    monkeypatch.setattr(
        pipeline,
        "validate_universal",
        lambda *args, **kwargs: (
            valid,
            warning,
            rejected,
            report
        )
    )

    # Mock successful database loading.

    monkeypatch.setattr(
        pipeline,
        "load_universal",
        lambda *args, **kwargs: {
            "table_name": "test_dataset"
        }
    )

    # Mock successful ETL report generation.

    monkeypatch.setattr(
        pipeline,
        "generate_reports",
        lambda *args, **kwargs: {
            "quality_report": "test_quality_report.json"
        }
    )

    # Enable profiling.

    monkeypatch.setattr(
        pipeline,
        "load_profiling_config",
        lambda: {
            "enabled": True
        }
    )

    # Simulate a profiling failure.

    profiling_error = RuntimeError(
        "Simulated dataset profiling failure"
    )

    def failing_profiling(*args, **kwargs):
        raise profiling_error

    monkeypatch.setattr(
        pipeline,
        "generate_profiling_report",
        failing_profiling
    )

    # Execute the pipeline and verify exception propagation.

    with pytest.raises(
        RuntimeError,
        match="Simulated dataset profiling failure"
    ):
        pipeline.run_universal_pipeline(
            str(source_file)
        )

    # Verify profiling stage failure.

    assert len(stage_failures) == 1

    assert stage_failures[0]["stage"] == (
        "DATASET_PROFILING"
    )

    assert stage_failures[0]["error"] is profiling_error

    # Verify overall execution failure.

    assert len(execution_failures) == 1

    failure = execution_failures[0]

    assert failure["details"]["failed_stage"] == (
        "DATASET_PROFILING"
    )

    assert failure["details"]["error_message"] is profiling_error

    assert failure["execution"]["current_stage"] == (
        "DATASET_PROFILING"
    )


def test_profiling_failure_does_not_mark_stage_completed(
    monkeypatch
):
    """Verify a failed profiling operation never completes its stage."""

    execution = {
        "execution_id": "test-execution-002",
        "database_path": ":memory:"
    }

    stage = {"stage_name": "DATASET_PROFILING"}

    stage_failures = []
    completed_stages = []

    monkeypatch.setattr(
        pipeline,
        "update_execution_stage",
        lambda execution, stage_name: None
    )

    monkeypatch.setattr(
        pipeline,
        "start_stage",
        lambda execution, stage_name: stage
    )

    monkeypatch.setattr(
        pipeline,
        "complete_stage",
        lambda stage: completed_stages.append(stage)
    )

    monkeypatch.setattr(
        pipeline,
        "fail_stage",
        lambda stage, error: stage_failures.append(
            (stage, error)
        )
    )

    expected_error = RuntimeError(
        "Profiling operation failed"
    )

    def operation():
        raise expected_error

    with pytest.raises(
        RuntimeError,
        match="Profiling operation failed"
    ):
        pipeline.run_monitored_stage(
            execution,
            "DATASET_PROFILING",
            operation,
            retry_enabled=False
        )

    assert len(stage_failures) == 1

    assert stage_failures[0][1] is expected_error

    assert completed_stages == []
