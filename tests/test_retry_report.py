
import json

from src.universal.execution_tracker import start_execution

from src.universal.stage_tracker import (
    start_stage,
    complete_stage,
    fail_stage
)

from src.universal.retry_manager import execute_with_retry

from src.universal.retry_report import (
    generate_retry_summary,
    generate_retry_report
)


def test_empty_retry_history(tmp_path):

    database = tmp_path / "history.db"

    summary = generate_retry_summary(database)

    assert summary["total_retry_attempts"] == 0
    assert summary["successful_recoveries"] == 0
    assert summary["exhausted_attempts"] == 0


def test_recovered_stage_is_counted(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "retail",
        "retail.csv",
        database
    )

    stage = start_stage(
        execution,
        "TRANSFORM"
    )

    attempts = {"count": 0}

    def operation():

        attempts["count"] += 1

        if attempts["count"] == 1:
            raise ConnectionError("Temporary failure")

        return "SUCCESS"

    execute_with_retry(
        operation,
        max_attempts=3,
        sleep=lambda delay: None,
        execution_id=execution["execution_id"],
        stage_name="TRANSFORM",
        database_path=database
    )

    complete_stage(stage)

    summary = generate_retry_summary(database)

    assert summary["successful_recoveries"] == 1
    assert summary["retrying_attempts"] == 1


def test_exhausted_retry_is_counted(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "retail",
        "retail.csv",
        database
    )

    stage = start_stage(
        execution,
        "EXTRACT"
    )

    try:

        execute_with_retry(
            lambda: (_ for _ in ()).throw(
                TimeoutError("Service unavailable")
            ),
            max_attempts=2,
            sleep=lambda delay: None,
            execution_id=execution["execution_id"],
            stage_name="EXTRACT",
            database_path=database
        )

    except TimeoutError as error:

        fail_stage(stage, error)

    summary = generate_retry_summary(database)

    assert summary["exhausted_attempts"] == 1
    assert summary["exhausted_stages"] == 1


def test_non_retryable_failure_is_counted(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "retail",
        "retail.csv",
        database
    )

    stage = start_stage(
        execution,
        "EXTRACT"
    )

    try:

        execute_with_retry(
            lambda: (_ for _ in ()).throw(
                FileNotFoundError("Missing CSV")
            ),
            max_attempts=3,
            sleep=lambda delay: None,
            execution_id=execution["execution_id"],
            stage_name="EXTRACT",
            database_path=database
        )

    except FileNotFoundError as error:

        fail_stage(stage, error)

    summary = generate_retry_summary(database)

    assert summary["non_retryable_attempts"] == 1
    assert summary["non_retryable_stages"] == 1


def test_stage_wise_statistics(tmp_path):

    database = tmp_path / "history.db"

    execution = start_execution(
        "retail",
        "retail.csv",
        database
    )

    stage = start_stage(
        execution,
        "TRANSFORM"
    )

    def operation():
        raise ConnectionError("Temporary failure")

    try:

        execute_with_retry(
            operation,
            max_attempts=3,
            sleep=lambda delay: None,
            execution_id=execution["execution_id"],
            stage_name="TRANSFORM",
            database_path=database
        )

    except ConnectionError as error:

        fail_stage(stage, error)

    summary = generate_retry_summary(database)

    statistics = summary["stage_statistics"]["TRANSFORM"]

    assert statistics["total_attempts"] == 3
    assert statistics["retrying_attempts"] == 2
    assert statistics["exhausted_attempts"] == 1


def test_retry_report_json_generation(tmp_path):

    database = tmp_path / "history.db"
    output = tmp_path / "reports" / "retry_report.json"

    result = generate_retry_report(
        database_path=database,
        output_path=output
    )

    assert output.exists()

    with open(output, encoding="utf-8") as file:
        saved = json.load(file)

    assert saved["total_retry_attempts"] == 0
    assert result["report_path"] == str(output)


def test_retry_delay_statistics(tmp_path):

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

    execute_with_retry(
        operation,
        max_attempts=3,
        base_delay_seconds=2,
        max_delay_seconds=30,
        sleep=lambda delay: None,
        execution_id=execution["execution_id"],
        stage_name="TRANSFORM",
        database_path=database
    )

    stage = start_stage(
        execution,
        "TRANSFORM"
    )

    complete_stage(stage)

    summary = generate_retry_summary(database)

    assert summary["total_retry_delay_seconds"] == 6
    assert summary["average_retry_delay_seconds"] == 3
