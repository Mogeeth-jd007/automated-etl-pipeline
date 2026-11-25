
from src.universal.retry_manager import (
    execute_with_retry,
    get_retry_history
)

from src.universal.retry_report import (
    generate_retry_summary
)


def test_standalone_retry_does_not_save_history(tmp_path):

    database = tmp_path / "history.db"

    def operation():
        raise TimeoutError("Temporary failure")

    try:

        execute_with_retry(
            operation,
            max_attempts=2,
            sleep=lambda delay: None
        )

    except TimeoutError:
        pass

    history = get_retry_history(database)

    assert history == []


def test_standalone_retry_with_database_path_does_not_save_history(
    tmp_path
):

    database = tmp_path / "history.db"

    def operation():
        raise ConnectionError("Temporary failure")

    try:

        execute_with_retry(
            operation,
            max_attempts=2,
            sleep=lambda delay: None,
            database_path=database
        )

    except ConnectionError:
        pass

    history = get_retry_history(database)

    assert history == []


def test_monitored_retry_still_saves_history(tmp_path):

    database = tmp_path / "history.db"

    def operation():
        raise TimeoutError("Temporary failure")

    try:

        execute_with_retry(
            operation,
            max_attempts=2,
            sleep=lambda delay: None,
            execution_id="test-execution-001",
            stage_name="EXTRACT",
            database_path=database
        )

    except TimeoutError:
        pass

    history = get_retry_history(
        database,
        execution_id="test-execution-001"
    )

    assert len(history) == 2


def test_report_ignores_old_unlinked_records(tmp_path):

    from src.universal.retry_manager import (
        record_retry_attempt
    )

    database = tmp_path / "history.db"

    record_retry_attempt(
        stage_name="UNKNOWN",
        attempt_number=1,
        error=TimeoutError("Old test failure"),
        outcome="EXHAUSTED",
        database_path=database
    )

    summary = generate_retry_summary(database)

    assert summary["total_retry_attempts"] == 0
    assert summary["ignored_unlinked_records"] == 1
    assert summary["stage_statistics"] == {}


def test_report_counts_only_monitored_executions(tmp_path):

    from src.universal.retry_manager import (
        record_retry_attempt
    )

    database = tmp_path / "history.db"

    # Historical orphan record.

    record_retry_attempt(
        stage_name="UNKNOWN",
        attempt_number=1,
        error=TimeoutError("Old test failure"),
        outcome="EXHAUSTED",
        database_path=database
    )

    # Actual monitored execution record.

    record_retry_attempt(
        stage_name="EXTRACT",
        attempt_number=1,
        error=ConnectionError("Temporary failure"),
        outcome="RETRYING",
        retry_delay_seconds=2,
        execution_id="real-execution-001",
        database_path=database
    )

    summary = generate_retry_summary(database)

    assert summary["total_retry_attempts"] == 1
    assert summary["ignored_unlinked_records"] == 1
    assert "EXTRACT" in summary["stage_statistics"]
    assert "UNKNOWN" not in summary["stage_statistics"]
