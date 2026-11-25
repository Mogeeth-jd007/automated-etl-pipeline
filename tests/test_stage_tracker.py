import sqlite3
import pytest

from src.universal.execution_tracker import (
    start_execution,
    complete_execution
)

from src.universal.stage_tracker import (
    initialize_stage_history,
    start_stage,
    complete_stage,
    fail_stage,
    get_stage_history
)


def create_execution(database):

    return start_execution(
        "retail",
        "retail.csv",
        database
    )


def test_initialize_stage_history(tmp_path):

    database = tmp_path / "history.db"

    execution = create_execution(database)

    initialize_stage_history(database)

    with sqlite3.connect(database) as connection:

        result = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name = 'pipeline_stage_history'
            """
        ).fetchone()

    assert result is not None


def test_start_stage(tmp_path):

    database = tmp_path / "history.db"

    execution = create_execution(database)

    stage = start_stage(execution, "EXTRACT")

    history = get_stage_history(
        execution["execution_id"],
        database
    )

    assert len(history) == 1
    assert history[0]["stage_name"] == "EXTRACT"
    assert history[0]["status"] == "RUNNING"


def test_complete_stage(tmp_path):

    database = tmp_path / "history.db"

    execution = create_execution(database)

    stage = start_stage(execution, "TRANSFORM")

    result = complete_stage(stage)

    history = get_stage_history(
        execution["execution_id"],
        database
    )

    assert result["status"] == "SUCCESS"
    assert result["duration_seconds"] >= 0

    assert history[0]["status"] == "SUCCESS"
    assert history[0]["end_time"] is not None


def test_fail_stage(tmp_path):

    database = tmp_path / "history.db"

    execution = create_execution(database)

    stage = start_stage(execution, "VALIDATION")

    fail_stage(stage, "Invalid data")

    history = get_stage_history(
        execution["execution_id"],
        database
    )

    assert history[0]["status"] == "FAILED"
    assert history[0]["error_message"] == "Invalid data"


def test_multiple_stages(tmp_path):

    database = tmp_path / "history.db"

    execution = create_execution(database)

    extract = start_stage(execution, "EXTRACT")
    complete_stage(extract)

    transform = start_stage(execution, "TRANSFORM")
    complete_stage(transform)

    history = get_stage_history(
        execution["execution_id"],
        database
    )

    assert len(history) == 2
    assert history[0]["stage_name"] == "EXTRACT"
    assert history[1]["stage_name"] == "TRANSFORM"


def test_stage_cannot_be_completed_twice(tmp_path):

    database = tmp_path / "history.db"

    execution = create_execution(database)

    stage = start_stage(execution, "EXTRACT")

    complete_stage(stage)

    with pytest.raises(ValueError):
        complete_stage(stage)


def test_invalid_stage_status(tmp_path):

    database = tmp_path / "history.db"

    execution = create_execution(database)

    stage = start_stage(execution, "EXTRACT")

    from src.universal.stage_tracker import finalize_stage

    with pytest.raises(ValueError):
        finalize_stage(stage, "UNKNOWN")


def test_stage_requires_existing_execution(tmp_path):

    database = tmp_path / "history.db"

    initialize_stage_history(database)

    fake_execution = {
        "execution_id": "unknown-id",
        "database_path": database
    }

    with pytest.raises(sqlite3.IntegrityError):
        start_stage(fake_execution, "EXTRACT")


def test_stage_history_is_separate_from_execution_history(tmp_path):

    database = tmp_path / "history.db"

    execution = create_execution(database)

    stage = start_stage(execution, "EXTRACT")
    complete_stage(stage)

    complete_execution(execution)

    with sqlite3.connect(database) as connection:

        execution_count = connection.execute(
            "SELECT COUNT(*) FROM pipeline_execution_history"
        ).fetchone()[0]

        stage_count = connection.execute(
            "SELECT COUNT(*) FROM pipeline_stage_history"
        ).fetchone()[0]

    assert execution_count == 1
    assert stage_count == 1
