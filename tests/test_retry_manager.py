
import sqlite3
import pytest

from src.universal.retry_manager import (
    execute_with_retry,
    is_retryable_error,
    calculate_retry_delay,
    validate_retry_config
)


def test_transient_failure_then_success():

    attempts = {"count": 0}
    delays = []

    def operation():

        attempts["count"] += 1

        if attempts["count"] < 3:
            raise ConnectionError("Temporary connection failure")

        return "SUCCESS"

    result = execute_with_retry(
        operation,
        max_attempts=3,
        base_delay_seconds=2,
        on_retry=lambda attempt, error, delay: delays.append(delay),
        sleep=lambda delay: None
    )

    assert result == "SUCCESS"
    assert attempts["count"] == 3
    assert delays == [2, 4]


def test_retries_exhausted():

    attempts = {"count": 0}

    def operation():

        attempts["count"] += 1

        raise TimeoutError("Connection timed out")

    with pytest.raises(TimeoutError):

        execute_with_retry(
            operation,
            max_attempts=3,
            sleep=lambda delay: None
        )

    assert attempts["count"] == 3


def test_permanent_error_is_not_retried():

    attempts = {"count": 0}

    def operation():

        attempts["count"] += 1

        raise FileNotFoundError("Missing CSV")

    with pytest.raises(FileNotFoundError):

        execute_with_retry(
            operation,
            max_attempts=3,
            sleep=lambda delay: None
        )

    assert attempts["count"] == 1


def test_sqlite_locked_error_is_retryable():

    error = sqlite3.OperationalError(
        "database is locked"
    )

    assert is_retryable_error(error)


def test_sqlite_other_error_is_not_retryable():

    error = sqlite3.OperationalError(
        "no such table: customers"
    )

    assert not is_retryable_error(error)


def test_exponential_backoff():

    assert calculate_retry_delay(1) == 2
    assert calculate_retry_delay(2) == 4
    assert calculate_retry_delay(3) == 8
    assert calculate_retry_delay(4) == 16
    assert calculate_retry_delay(5) == 30


def test_retry_delay_maximum_cap():

    assert calculate_retry_delay(
        10,
        base_delay_seconds=2,
        max_delay_seconds=10
    ) == 10


def test_invalid_attempt_count():

    with pytest.raises(ValueError):
        validate_retry_config(max_attempts=0)


def test_invalid_negative_delay():

    with pytest.raises(ValueError):
        validate_retry_config(base_delay_seconds=-1)


def test_maximum_delay_validation():

    with pytest.raises(ValueError):
        validate_retry_config(
            base_delay_seconds=10,
            max_delay_seconds=5
        )


def test_boolean_attempt_count_rejected():

    with pytest.raises(ValueError):
        validate_retry_config(max_attempts=True)


def test_success_without_retry():

    attempts = {"count": 0}

    def operation():

        attempts["count"] += 1

        return 100

    result = execute_with_retry(
        operation,
        sleep=lambda delay: None
    )

    assert result == 100
    assert attempts["count"] == 1
