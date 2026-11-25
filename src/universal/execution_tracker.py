
import sqlite3
import uuid
import time
import traceback

from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_DATABASE = (
    PROJECT_ROOT / "data" / "universal_pipeline.db"
)

TABLE_NAME = "pipeline_execution_history"


def get_database_path(database_path=None):
    """Resolve the execution-history database path."""

    if database_path is None:
        return DEFAULT_DATABASE

    path = Path(database_path)

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    return path


def get_current_timestamp():
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


def initialize_execution_history(database_path=None):
    """Create and safely migrate execution-history storage."""

    database = get_database_path(database_path)

    database.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with sqlite3.connect(database) as connection:

        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (

                execution_id TEXT PRIMARY KEY,
                dataset_name TEXT NOT NULL,
                input_file TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_seconds REAL,

                status TEXT NOT NULL
                    CHECK (
                        status IN ('RUNNING', 'SUCCESS', 'FAILED')
                    ),

                current_stage TEXT,
                failed_stage TEXT,
                error_message TEXT,
                total_records INTEGER DEFAULT 0,
                valid_records INTEGER DEFAULT 0,
                warning_records INTEGER DEFAULT 0,
                rejected_records INTEGER DEFAULT 0

            )
            """
        )

        # Backward-compatible database migration.

        existing_columns = {
            row[1]
            for row in connection.execute(
                f"PRAGMA table_info({TABLE_NAME})"
            ).fetchall()
        }

        new_columns = {
            "exception_type": "TEXT",
            "failure_timestamp": "TEXT",
            "traceback_details": "TEXT"
        }

        for column, data_type in new_columns.items():

            if column not in existing_columns:

                connection.execute(
                    f"""
                    ALTER TABLE {TABLE_NAME}
                    ADD COLUMN {column} {data_type}
                    """
                )

    return str(database)


def start_execution(
    dataset_name,
    input_file,
    database_path=None
):
    """Create a new execution-history record."""

    database = initialize_execution_history(
        database_path
    )

    execution_id = str(uuid.uuid4())

    start_time = get_current_timestamp()

    monotonic_start = time.perf_counter()

    with sqlite3.connect(database) as connection:

        connection.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                execution_id,
                dataset_name,
                input_file,
                start_time,
                status,
                current_stage
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                execution_id,
                str(dataset_name),
                str(input_file),
                start_time,
                "RUNNING",
                "INITIALIZATION"
            )
        )

    return {
        "execution_id": execution_id,
        "database_path": database,
        "monotonic_start": monotonic_start,
        "current_stage": "INITIALIZATION"
    }


def update_execution_stage(execution, stage):
    """Update the currently executing pipeline stage."""

    database = get_database_path(
        execution["database_path"]
    )

    stage = str(stage)

    with sqlite3.connect(database) as connection:

        cursor = connection.execute(
            f"""
            UPDATE {TABLE_NAME}
            SET current_stage = ?
            WHERE execution_id = ?
            AND status = 'RUNNING'
            """,
            (
                stage,
                execution["execution_id"]
            )
        )

        if cursor.rowcount != 1:
            raise ValueError(
                "Execution does not exist or is no longer running."
            )

    execution["current_stage"] = stage


def finalize_execution(
    execution,
    status,
    failed_stage=None,
    error_message=None,
    total_records=0,
    valid_records=0,
    warning_records=0,
    rejected_records=0,
    exception_type=None,
    failure_timestamp=None,
    traceback_details=None
):
    """Finalize execution and persist failure diagnostics."""

    if status not in {"SUCCESS", "FAILED"}:
        raise ValueError(
            "Final status must be SUCCESS or FAILED."
        )

    counts = {
        "total_records": total_records,
        "valid_records": valid_records,
        "warning_records": warning_records,
        "rejected_records": rejected_records
    }

    for name, value in counts.items():

        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise ValueError(
                f"{name} must be a non-negative integer."
            )

    if status == "FAILED" and failure_timestamp is None:
        failure_timestamp = get_current_timestamp()

    database = get_database_path(
        execution["database_path"]
    )

    duration = round(
        time.perf_counter() - execution["monotonic_start"],
        6
    )

    end_time = get_current_timestamp()

    with sqlite3.connect(database) as connection:

        cursor = connection.execute(
            f"""
            UPDATE {TABLE_NAME}

            SET
                end_time = ?,
                duration_seconds = ?,
                status = ?,
                failed_stage = ?,
                error_message = ?,
                total_records = ?,
                valid_records = ?,
                warning_records = ?,
                rejected_records = ?,
                exception_type = ?,
                failure_timestamp = ?,
                traceback_details = ?

            WHERE execution_id = ?
            AND status = 'RUNNING'
            """,
            (
                end_time,
                duration,
                status,
                failed_stage,
                error_message,
                total_records,
                valid_records,
                warning_records,
                rejected_records,
                exception_type,
                failure_timestamp if status == "FAILED" else None,
                traceback_details,
                execution["execution_id"]
            )
        )

        if cursor.rowcount != 1:
            raise ValueError(
                "Execution does not exist or has already finished."
            )

    return {
        "execution_id": execution["execution_id"],
        "status": status,
        "start_time": None,
        "end_time": end_time,
        "duration_seconds": duration,
        **counts
    }


def complete_execution(
    execution,
    total_records=0,
    valid_records=0,
    warning_records=0,
    rejected_records=0
):
    """Mark an execution as successful."""

    return finalize_execution(
        execution,
        status="SUCCESS",
        total_records=total_records,
        valid_records=valid_records,
        warning_records=warning_records,
        rejected_records=rejected_records
    )


def fail_execution(
    execution,
    failed_stage,
    error_message,
    total_records=0,
    valid_records=0,
    warning_records=0,
    rejected_records=0,
    exception_type=None,
    traceback_details=None,
    failure_timestamp=None
):
    """Mark an execution as failed and save diagnostics."""

    if isinstance(error_message, BaseException):

        error = error_message

        if exception_type is None:
            exception_type = type(error).__name__

        if traceback_details is None:
            traceback_details = "".join(
                traceback.format_exception(
                    type(error),
                    error,
                    error.__traceback__
                )
            )

        error_message = str(error)

    return finalize_execution(
        execution,
        status="FAILED",
        failed_stage=failed_stage,
        error_message=str(error_message),
        total_records=total_records,
        valid_records=valid_records,
        warning_records=warning_records,
        rejected_records=rejected_records,
        exception_type=exception_type,
        failure_timestamp=failure_timestamp,
        traceback_details=traceback_details
    )
