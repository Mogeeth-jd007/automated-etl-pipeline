
import pytest

from src.universal.execution_tracker import start_execution

from src.universal.stage_tracker import get_stage_history

from src.universal.retry_manager import get_retry_history

from src.universal.universal_pipeline import (
    run_monitored_stage,
    load_retry_config
)


RETRY_CONFIG = {
    "enabled": True,
    "max_attempts": 3,
    "base_delay_seconds": 2,
    "max_delay_seconds": 30
}


def test_monitored_stage_recovers_after_transient_failure(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "retail",
        "retail.csv",
        database
    )

    attempts = {"count": 0}

    def operation():

        attempts["count"] += 1

        if attempts["count"] < 3:
            raise ConnectionError("Temporary failure")

        return "SUCCESS"

    result = run_monitored_stage(
        execution,
        "TRANSFORM",
        operation,
        RETRY_CONFIG,
        retry_enabled=True
    )

    assert result == "SUCCESS"
    assert attempts["count"] == 3

    stages = get_stage_history(
        execution["execution_id"],
        database
    )

    assert len(stages) == 1
    assert stages[0]["status"] == "SUCCESS"

    history = get_retry_history(
        database,
        execution_id=execution["execution_id"]
    )

    assert len(history) == 2
    assert all(
        item["outcome"] == "RETRYING"
        for item in history
    )


def test_monitored_stage_fails_after_retries_exhausted(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "retail",
        "retail.csv",
        database
    )

    attempts = {"count": 0}

    def operation():

        attempts["count"] += 1

        raise TimeoutError("Service unavailable")

    with pytest.raises(TimeoutError):

        run_monitored_stage(
            execution,
            "EXTRACT",
            operation,
            RETRY_CONFIG,
            retry_enabled=True
        )

    assert attempts["count"] == 3

    stages = get_stage_history(
        execution["execution_id"],
        database
    )

    assert stages[0]["status"] == "FAILED"

    history = get_retry_history(
        database,
        execution_id=execution["execution_id"]
    )

    assert len(history) == 3
    assert history[0]["outcome"] == "EXHAUSTED"


def test_monitored_stage_does_not_retry_permanent_error(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "retail",
        "retail.csv",
        database
    )

    attempts = {"count": 0}

    def operation():

        attempts["count"] += 1

        raise FileNotFoundError("Missing CSV")

    with pytest.raises(FileNotFoundError):

        run_monitored_stage(
            execution,
            "EXTRACT",
            operation,
            RETRY_CONFIG,
            retry_enabled=True
        )

    assert attempts["count"] == 1

    history = get_retry_history(
        database,
        execution_id=execution["execution_id"]
    )

    assert len(history) == 1
    assert history[0]["outcome"] == "NOT_RETRYABLE"


def test_database_load_is_not_retried(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "retail",
        "retail.csv",
        database
    )

    attempts = {"count": 0}

    def operation():

        attempts["count"] += 1

        raise ConnectionError("Temporary connection failure")

    with pytest.raises(ConnectionError):

        run_monitored_stage(
            execution,
            "DATABASE_LOAD",
            operation,
            RETRY_CONFIG,
            retry_enabled=False
        )

    assert attempts["count"] == 1

    stages = get_stage_history(
        execution["execution_id"],
        database
    )

    assert stages[0]["status"] == "FAILED"

    history = get_retry_history(
        database,
        execution_id=execution["execution_id"]
    )

    assert history == []


def test_retry_configuration_validation(monkeypatch):

    import src.universal.universal_pipeline as pipeline

    monkeypatch.setattr(
        pipeline,
        "load_config",
        lambda: {
            "retry": {
                "enabled": True,
                "max_attempts": 0,
                "base_delay_seconds": 2,
                "max_delay_seconds": 30
            }
        }
    )

    with pytest.raises(ValueError):
        load_retry_config()


def test_retry_disabled_in_configuration(monkeypatch):

    import src.universal.universal_pipeline as pipeline

    monkeypatch.setattr(
        pipeline,
        "load_config",
        lambda: {
            "retry": {
                "enabled": False,
                "max_attempts": 3,
                "base_delay_seconds": 2,
                "max_delay_seconds": 30
            }
        }
    )

    result = load_retry_config()

    assert result["enabled"] is False
    assert result["max_attempts"] == 3
