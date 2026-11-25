
import pytest

from src.universal.execution_tracker import (
    start_execution,
    complete_execution,
    fail_execution
)

from src.universal.execution_monitor import (
    get_execution_history,
    get_execution_details,
    get_execution_statistics
)


def create_test_history(database):

    first = start_execution(
        "retail",
        "retail.csv",
        database
    )

    complete_execution(
        first,
        total_records=10,
        valid_records=8,
        warning_records=2,
        rejected_records=0
    )

    second = start_execution(
        "employee",
        "employee.csv",
        database
    )

    fail_execution(
        second,
        failed_stage="TRANSFORM",
        error_message="Transformation failed"
    )

    return first, second


def test_get_execution_history(tmp_path):

    database = tmp_path / "history.db"

    create_test_history(database)

    history = get_execution_history(database)

    assert len(history) == 2


def test_filter_successful_executions(tmp_path):

    database = tmp_path / "history.db"

    create_test_history(database)

    history = get_execution_history(
        database,
        status="SUCCESS"
    )

    assert len(history) == 1
    assert history[0]["status"] == "SUCCESS"


def test_filter_failed_executions(tmp_path):

    database = tmp_path / "history.db"

    create_test_history(database)

    history = get_execution_history(
        database,
        status="FAILED"
    )

    assert len(history) == 1
    assert history[0]["status"] == "FAILED"


def test_get_execution_details(tmp_path):

    database = tmp_path / "history.db"

    first, second = create_test_history(database)

    details = get_execution_details(
        second["execution_id"],
        database
    )

    assert details is not None
    assert details["dataset_name"] == "employee"
    assert details["failed_stage"] == "TRANSFORM"


def test_unknown_execution_returns_none(tmp_path):

    database = tmp_path / "history.db"

    create_test_history(database)

    details = get_execution_details(
        "unknown-execution-id",
        database
    )

    assert details is None


def test_execution_statistics(tmp_path):

    database = tmp_path / "history.db"

    create_test_history(database)

    statistics = get_execution_statistics(database)

    assert statistics["total_executions"] == 2
    assert statistics["successful_executions"] == 1
    assert statistics["failed_executions"] == 1
    assert statistics["success_rate"] == 50.0
    assert statistics["failure_rate"] == 50.0


def test_empty_history_statistics(tmp_path):

    database = tmp_path / "history.db"

    from src.universal.execution_tracker import (
        initialize_execution_history
    )

    initialize_execution_history(database)

    statistics = get_execution_statistics(database)

    assert statistics["total_executions"] == 0
    assert statistics["success_rate"] == 0
    assert statistics["failure_rate"] == 0


def test_invalid_status_is_rejected(tmp_path):

    database = tmp_path / "history.db"

    create_test_history(database)

    with pytest.raises(ValueError):

        get_execution_history(
            database,
            status="UNKNOWN"
        )


def test_invalid_limit_is_rejected(tmp_path):

    database = tmp_path / "history.db"

    create_test_history(database)

    with pytest.raises(ValueError):

        get_execution_history(
            database,
            limit=-1
        )


def test_execution_history_limit(tmp_path):

    database = tmp_path / "history.db"

    create_test_history(database)

    history = get_execution_history(
        database,
        limit=1
    )

    assert len(history) == 1
