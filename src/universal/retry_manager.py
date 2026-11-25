
import sqlite3
import time
import uuid

from datetime import datetime, timezone

from .execution_tracker import get_database_path


RETRY_TABLE = "pipeline_retry_history"


def get_current_timestamp():
    return datetime.now(timezone.utc).isoformat()


def validate_retry_config(
    max_attempts=3,
    base_delay_seconds=2,
    max_delay_seconds=30
):
    """Validate retry configuration."""

    if (
        isinstance(max_attempts, bool)
        or not isinstance(max_attempts, int)
        or max_attempts < 1
    ):
        raise ValueError(
            "max_attempts must be a positive integer."
        )

    for name, value in {
        "base_delay_seconds": base_delay_seconds,
        "max_delay_seconds": max_delay_seconds
    }.items():

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or value < 0
        ):
            raise ValueError(
                f"{name} must be a non-negative number."
            )

    if max_delay_seconds < base_delay_seconds:
        raise ValueError(
            "max_delay_seconds cannot be smaller than base_delay_seconds."
        )


def is_retryable_error(error):
    """Identify temporary errors that are safe to retry."""

    if isinstance(error, (TimeoutError, ConnectionError)):
        return True

    if isinstance(error, sqlite3.OperationalError):

        message = str(error).lower()

        return (
            "database is locked" in message
            or "database is busy" in message
        )

    return False


def calculate_retry_delay(
    failed_attempt,
    base_delay_seconds=2,
    max_delay_seconds=30
):
    """Calculate exponential backoff delay."""

    if (
        isinstance(failed_attempt, bool)
        or not isinstance(failed_attempt, int)
        or failed_attempt < 1
    ):
        raise ValueError(
            "failed_attempt must be a positive integer."
        )

    delay = base_delay_seconds * (
        2 ** (failed_attempt - 1)
    )

    return min(delay, max_delay_seconds)


def initialize_retry_history(database_path=None):
    """Create persistent retry-history storage."""

    database = get_database_path(database_path)

    database.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with sqlite3.connect(database) as connection:

        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {RETRY_TABLE} (

                retry_id TEXT PRIMARY KEY,

                execution_id TEXT,

                stage_name TEXT NOT NULL,

                attempt_number INTEGER NOT NULL,

                exception_type TEXT,

                error_message TEXT,

                retry_delay_seconds REAL,

                retry_timestamp TEXT NOT NULL,

                outcome TEXT NOT NULL CHECK (
                    outcome IN (
                        'RETRYING',
                        'EXHAUSTED',
                        'NOT_RETRYABLE'
                    )
                )
            )
            """
        )

    return str(database)


def record_retry_attempt(
    stage_name,
    attempt_number,
    error,
    outcome,
    retry_delay_seconds=None,
    execution_id=None,
    database_path=None
):
    """Persist an individual failed retry attempt."""

    if outcome not in {
        "RETRYING",
        "EXHAUSTED",
        "NOT_RETRYABLE"
    }:
        raise ValueError("Invalid retry outcome.")

    if (
        isinstance(attempt_number, bool)
        or not isinstance(attempt_number, int)
        or attempt_number < 1
    ):
        raise ValueError(
            "attempt_number must be a positive integer."
        )

    if retry_delay_seconds is not None:

        if (
            isinstance(retry_delay_seconds, bool)
            or not isinstance(retry_delay_seconds, (int, float))
            or retry_delay_seconds < 0
        ):
            raise ValueError(
                "retry_delay_seconds must be non-negative."
            )

    database = initialize_retry_history(database_path)

    retry_id = str(uuid.uuid4())

    with sqlite3.connect(database) as connection:

        connection.execute(
            f"""
            INSERT INTO {RETRY_TABLE} (
                retry_id,
                execution_id,
                stage_name,
                attempt_number,
                exception_type,
                error_message,
                retry_delay_seconds,
                retry_timestamp,
                outcome
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                retry_id,
                execution_id,
                str(stage_name),
                attempt_number,
                type(error).__name__,
                str(error),
                retry_delay_seconds,
                get_current_timestamp(),
                outcome
            )
        )

    return {
        "retry_id": retry_id,
        "execution_id": execution_id,
        "stage_name": str(stage_name),
        "attempt_number": attempt_number,
        "exception_type": type(error).__name__,
        "error_message": str(error),
        "retry_delay_seconds": retry_delay_seconds,
        "outcome": outcome
    }


def get_retry_history(
    database_path=None,
    execution_id=None,
    stage_name=None,
    limit=100
):
    """Retrieve persisted retry attempts."""

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or limit < 1
    ):
        raise ValueError(
            "limit must be a positive integer."
        )

    database = initialize_retry_history(database_path)

    query = f"SELECT * FROM {RETRY_TABLE} WHERE 1=1"
    parameters = []

    if execution_id is not None:
        query += " AND execution_id = ?"
        parameters.append(execution_id)

    if stage_name is not None:
        query += " AND stage_name = ?"
        parameters.append(stage_name)

    query += " ORDER BY retry_timestamp DESC, rowid DESC LIMIT ?"
    parameters.append(limit)

    with sqlite3.connect(database) as connection:

        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            query,
            parameters
        ).fetchall()

    return [dict(row) for row in rows]


def display_retry_history(
    database_path=None,
    execution_id=None,
    stage_name=None,
    limit=100
):
    """Display retry history."""

    records = get_retry_history(
        database_path=database_path,
        execution_id=execution_id,
        stage_name=stage_name,
        limit=limit
    )

    print("\n========== RETRY HISTORY ==========\n")

    if not records:
        print("No retry attempts found.")
        return records

    for record in records:

        print("Execution ID:", record["execution_id"])
        print("Stage:", record["stage_name"])
        print("Attempt:", record["attempt_number"])
        print("Exception:", record["exception_type"])
        print("Error:", record["error_message"])
        print("Delay:", record["retry_delay_seconds"])
        print("Outcome:", record["outcome"])
        print("Timestamp:", record["retry_timestamp"])
        print("-" * 55)

    return records


def execute_with_retry(
    operation,
    max_attempts=3,
    base_delay_seconds=2,
    max_delay_seconds=30,
    on_retry=None,
    sleep=time.sleep,
    execution_id=None,
    stage_name="UNKNOWN",
    database_path=None
):
    """
    Execute an operation with bounded retries.

    Retry history is persisted only when an explicit execution ID
    is supplied. Standalone operations and unit tests do not
    pollute production execution history.
    """

    if not callable(operation):
        raise TypeError(
            "operation must be callable."
        )

    if on_retry is not None and not callable(on_retry):
        raise TypeError(
            "on_retry must be callable or None."
        )

    if not callable(sleep):
        raise TypeError(
            "sleep must be callable."
        )

    validate_retry_config(
        max_attempts,
        base_delay_seconds,
        max_delay_seconds
    )

    # Persistence is restricted to monitored executions.

    persist_history = execution_id is not None

    if persist_history and not str(execution_id).strip():
        raise ValueError(
            "execution_id cannot be empty."
        )

    attempt = 1

    while attempt <= max_attempts:

        try:
            return operation()

        except Exception as error:

            retryable = is_retryable_error(error)

            if not retryable:

                if persist_history:

                    record_retry_attempt(
                        stage_name,
                        attempt,
                        error,
                        "NOT_RETRYABLE",
                        execution_id=execution_id,
                        database_path=database_path
                    )

                raise

            if attempt >= max_attempts:

                if persist_history:

                    record_retry_attempt(
                        stage_name,
                        attempt,
                        error,
                        "EXHAUSTED",
                        execution_id=execution_id,
                        database_path=database_path
                    )

                raise

            delay = calculate_retry_delay(
                attempt,
                base_delay_seconds,
                max_delay_seconds
            )

            if persist_history:

                record_retry_attempt(
                    stage_name,
                    attempt,
                    error,
                    "RETRYING",
                    retry_delay_seconds=delay,
                    execution_id=execution_id,
                    database_path=database_path
                )

            if on_retry is not None:

                on_retry(
                    attempt,
                    error,
                    delay
                )

            sleep(delay)

            attempt += 1

    raise RuntimeError(
        "Unexpected retry execution state."
    )
