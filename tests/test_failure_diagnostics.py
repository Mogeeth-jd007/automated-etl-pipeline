
import sqlite3

from src.universal.execution_tracker import (
    start_execution,
    fail_execution
)

from src.universal.stage_tracker import (
    start_stage,
    fail_stage
)

from src.universal.execution_monitor import (
    get_failure_history,
    get_failure_details
)


def test_execution_exception_type_is_saved(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "retail",
        "retail.csv",
        database
    )

    try:
        raise ValueError("Invalid transformation")

    except Exception as error:

        fail_execution(
            execution,
            failed_stage="TRANSFORM",
            error_message=error
        )

    details = get_failure_details(
        execution["execution_id"],
        database
    )

    record = details["execution"]

    assert record["exception_type"] == "ValueError"
    assert record["error_message"] == "Invalid transformation"


def test_execution_traceback_is_saved(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "retail",
        "retail.csv",
        database
    )

    try:
        raise RuntimeError("Database connection failed")

    except Exception as error:

        fail_execution(
            execution,
            failed_stage="DATABASE_LOAD",
            error_message=error
        )

    details = get_failure_details(
        execution["execution_id"],
        database
    )

    traceback_text = details["execution"]["traceback_details"]

    assert "RuntimeError" in traceback_text
    assert "Database connection failed" in traceback_text


def test_failure_timestamp_is_saved(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "retail",
        "retail.csv",
        database
    )

    try:
        raise ValueError("Test failure")

    except Exception as error:

        fail_execution(
            execution,
            failed_stage="TRANSFORM",
            error_message=error
        )

    details = get_failure_details(
        execution["execution_id"],
        database
    )

    assert details["execution"]["failure_timestamp"] is not None


def test_stage_failure_diagnostics_are_retrievable(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "retail",
        "retail.csv",
        database
    )

    stage = start_stage(
        execution,
        "VALIDATION"
    )

    try:
        raise TypeError("Invalid validation input")

    except Exception as error:

        fail_stage(stage, error)

        fail_execution(
            execution,
            failed_stage="VALIDATION",
            error_message=error
        )

    details = get_failure_details(
        execution["execution_id"],
        database
    )

    assert len(details["failed_stages"]) == 1

    failed_stage = details["failed_stages"][0]

    assert failed_stage["stage_name"] == "VALIDATION"
    assert failed_stage["exception_type"] == "TypeError"
    assert "Invalid validation input" in failed_stage["traceback_details"]


def test_failure_history_returns_failed_executions(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "retail",
        "retail.csv",
        database
    )

    try:
        raise FileNotFoundError("Missing CSV")

    except Exception as error:

        fail_execution(
            execution,
            failed_stage="EXTRACT",
            error_message=error
        )

    history = get_failure_history(database)

    assert len(history) == 1
    assert history[0]["status"] == "FAILED"
    assert history[0]["failed_stage"] == "EXTRACT"


def test_failure_details_survive_database_reopening(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "retail",
        "retail.csv",
        database
    )

    try:
        raise ValueError("Persistent failure")

    except Exception as error:

        fail_execution(
            execution,
            failed_stage="TRANSFORM",
            error_message=error
        )

    # Close all connections and retrieve the record again.

    details = get_failure_details(
        execution["execution_id"],
        database
    )

    assert details is not None

    record = details["execution"]

    assert record["exception_type"] == "ValueError"
    assert record["failure_timestamp"] is not None
    assert "Persistent failure" in record["traceback_details"]

    with sqlite3.connect(database) as connection:

        saved = connection.execute(
            """
            SELECT status, exception_type
            FROM pipeline_execution_history
            WHERE execution_id = ?
            """,
            (execution["execution_id"],)
        ).fetchone()

    assert saved == ("FAILED", "ValueError")
