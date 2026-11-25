
import sqlite3
import pytest

from src.universal.retry_manager import (
    execute_with_retry,
    get_retry_history,
    initialize_retry_history
)


def test_retry_history_is_saved(tmp_path):

    database = tmp_path / "retry.db"

    attempts = {"count": 0}

    def operation():

        attempts["count"] += 1

        if attempts["count"] == 1:
            raise ConnectionError("Temporary failure")

        return "SUCCESS"

    result = execute_with_retry(
        operation,
        max_attempts=3,
        sleep=lambda delay: None,
        execution_id="execution-001",
        stage_name="DATABASE_LOAD",
        database_path=database
    )

    history = get_retry_history(
        database,
        execution_id="execution-001"
    )

    assert result == "SUCCESS"
    assert len(history) == 1
    assert history[0]["attempt_number"] == 1
    assert history[0]["outcome"] == "RETRYING"
    assert history[0]["exception_type"] == "ConnectionError"


def test_exhausted_retries_are_saved(tmp_path):

    database = tmp_path / "retry.db"

    def operation():
        raise TimeoutError("Service unavailable")

    with pytest.raises(TimeoutError):

        execute_with_retry(
            operation,
            max_attempts=3,
            sleep=lambda delay: None,
            execution_id="execution-002",
            stage_name="EXTRACT",
            database_path=database
        )

    history = get_retry_history(
        database,
        execution_id="execution-002"
    )

    assert len(history) == 3

    assert history[0]["outcome"] == "EXHAUSTED"
    assert history[0]["attempt_number"] == 3

    assert sum(
        item["outcome"] == "RETRYING"
        for item in history
    ) == 2


def test_permanent_failure_is_saved(tmp_path):

    database = tmp_path / "retry.db"

    def operation():
        raise FileNotFoundError("CSV missing")

    with pytest.raises(FileNotFoundError):

        execute_with_retry(
            operation,
            max_attempts=3,
            sleep=lambda delay: None,
            execution_id="execution-003",
            stage_name="EXTRACT",
            database_path=database
        )

    history = get_retry_history(
        database,
        execution_id="execution-003"
    )

    assert len(history) == 1
    assert history[0]["outcome"] == "NOT_RETRYABLE"
    assert history[0]["attempt_number"] == 1


def test_retry_history_survives_reinitialization(tmp_path):

    database = tmp_path / "retry.db"

    def operation():
        raise ConnectionError("Network unavailable")

    with pytest.raises(ConnectionError):

        execute_with_retry(
            operation,
            max_attempts=2,
            sleep=lambda delay: None,
            execution_id="execution-004",
            stage_name="DATABASE_LOAD",
            database_path=database
        )

    initialize_retry_history(database)

    history = get_retry_history(
        database,
        execution_id="execution-004"
    )

    assert len(history) == 2

    assert history[0]["outcome"] == "EXHAUSTED"


def test_retry_history_can_be_filtered_by_stage(tmp_path):

    database = tmp_path / "retry.db"

    for execution_id, stage_name in [
        ("execution-005", "EXTRACT"),
        ("execution-006", "DATABASE_LOAD")
    ]:

        with pytest.raises(ConnectionError):

            execute_with_retry(
                lambda: (_ for _ in ()).throw(
                    ConnectionError("Temporary failure")
                ),
                max_attempts=2,
                sleep=lambda delay: None,
                execution_id=execution_id,
                stage_name=stage_name,
                database_path=database
            )

    history = get_retry_history(
        database,
        stage_name="DATABASE_LOAD"
    )

    assert len(history) == 2
    assert all(
        item["stage_name"] == "DATABASE_LOAD"
        for item in history
    )


def test_retry_database_contains_required_columns(tmp_path):

    database = tmp_path / "retry.db"

    initialize_retry_history(database)

    with sqlite3.connect(database) as connection:

        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(pipeline_retry_history)"
            ).fetchall()
        }

    expected = {
        "retry_id",
        "execution_id",
        "stage_name",
        "attempt_number",
        "exception_type",
        "error_message",
        "retry_delay_seconds",
        "retry_timestamp",
        "outcome"
    }

    assert expected.issubset(columns)
