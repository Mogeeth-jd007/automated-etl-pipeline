import sqlite3
import pytest

from src.universal.execution_tracker import (
    start_execution,
    update_execution_stage,
    complete_execution,
    fail_execution,
    initialize_execution_history,
    finalize_execution
)


def get_record(database, execution_id):

    with sqlite3.connect(database) as connection:

        return connection.execute(
            """
            SELECT *
            FROM pipeline_execution_history
            WHERE execution_id = ?
            """,
            (execution_id,)
        ).fetchone()


def test_initialize_execution_history(tmp_path):

    database = tmp_path / "history.db"

    initialize_execution_history(database)

    with sqlite3.connect(database) as connection:

        result = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name = 'pipeline_execution_history'
            """
        ).fetchone()

    assert result is not None


def test_start_execution(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "sales",
        "sales.csv",
        database
    )

    record = get_record(
        database,
        execution["execution_id"]
    )

    assert record is not None
    assert record[1] == "sales"
    assert record[2] == "sales.csv"
    assert record[6] == "RUNNING"
    assert record[7] == "INITIALIZATION"


def test_execution_ids_are_unique(tmp_path):

    database = tmp_path / "history.db"

    first = start_execution("sales", "sales.csv", database)
    second = start_execution("sales", "sales.csv", database)

    assert first["execution_id"] != second["execution_id"]


def test_update_execution_stage(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "sales",
        "sales.csv",
        database
    )

    update_execution_stage(
        execution,
        "TRANSFORM"
    )

    record = get_record(
        database,
        execution["execution_id"]
    )

    assert record[6] == "RUNNING"
    assert record[7] == "TRANSFORM"


def test_complete_execution(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "sales",
        "sales.csv",
        database
    )

    result = complete_execution(
        execution,
        total_records=10,
        valid_records=7,
        warning_records=2,
        rejected_records=1
    )

    record = get_record(
        database,
        execution["execution_id"]
    )

    assert record[6] == "SUCCESS"
    assert record[4] is not None
    assert record[5] >= 0

    assert record[10] == 10
    assert record[11] == 7
    assert record[12] == 2
    assert record[13] == 1

    assert result["status"] == "SUCCESS"


def test_fail_execution(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "sales",
        "sales.csv",
        database
    )

    fail_execution(
        execution,
        failed_stage="TRANSFORM",
        error_message="Invalid data format"
    )

    record = get_record(
        database,
        execution["execution_id"]
    )

    assert record[6] == "FAILED"
    assert record[8] == "TRANSFORM"
    assert record[9] == "Invalid data format"


def test_execution_cannot_be_completed_twice(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "sales",
        "sales.csv",
        database
    )

    complete_execution(execution)

    with pytest.raises(ValueError):

        complete_execution(execution)


def test_invalid_final_status_is_rejected(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "sales",
        "sales.csv",
        database
    )

    with pytest.raises(ValueError):

        finalize_execution(
            execution,
            status="UNKNOWN"
        )


def test_negative_record_count_is_rejected(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "sales",
        "sales.csv",
        database
    )

    with pytest.raises(ValueError):

        complete_execution(
            execution,
            total_records=-1
        )


def test_execution_history_survives_reinitialization(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "sales",
        "sales.csv",
        database
    )

    complete_execution(
        execution,
        total_records=5
    )

    initialize_execution_history(database)

    record = get_record(
        database,
        execution["execution_id"]
    )

    assert record is not None
    assert record[6] == "SUCCESS"
