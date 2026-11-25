
import pytest

from src.universal.execution_tracker import start_execution

from src.universal.stage_tracker import (
    start_stage,
    complete_stage,
    fail_stage
)

from src.universal.execution_monitor import (
    get_stage_performance_report
)


def test_stage_performance_report(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "retail",
        "retail.csv",
        database
    )

    for stage_name in [
        "EXTRACT",
        "TRANSFORM",
        "VALIDATION"
    ]:

        stage = start_stage(execution, stage_name)
        complete_stage(stage)

    report = get_stage_performance_report(
        execution["execution_id"],
        database
    )

    assert report["total_stages"] == 3
    assert report["successful_stages"] == 3
    assert report["failed_stages"] == 0
    assert report["stage_success_rate"] == 100


def test_stage_failure_performance(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "retail",
        "retail.csv",
        database
    )

    stage = start_stage(execution, "TRANSFORM")

    fail_stage(stage, "Invalid data")

    report = get_stage_performance_report(
        execution["execution_id"],
        database
    )

    assert report["failed_stages"] == 1
    assert report["successful_stages"] == 0
    assert report["stages"][0]["error_message"] == "Invalid data"


def test_slowest_stage_detection(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "retail",
        "retail.csv",
        database
    )

    first = start_stage(execution, "EXTRACT")
    complete_stage(first)

    second = start_stage(execution, "TRANSFORM")
    complete_stage(second)

    report = get_stage_performance_report(
        execution["execution_id"],
        database
    )

    assert report["slowest_stage"] in [
        "EXTRACT",
        "TRANSFORM"
    ]

    assert report["slowest_stage_duration"] >= 0


def test_empty_stage_history_raises_error(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "retail",
        "retail.csv",
        database
    )

    with pytest.raises(ValueError):

        get_stage_performance_report(
            execution["execution_id"],
            database
        )


def test_running_stage_is_counted(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "retail",
        "retail.csv",
        database
    )

    start_stage(execution, "EXTRACT")

    report = get_stage_performance_report(
        execution["execution_id"],
        database
    )

    assert report["running_stages"] == 1
    assert report["successful_stages"] == 0
