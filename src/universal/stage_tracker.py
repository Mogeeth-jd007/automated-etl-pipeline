
import sqlite3
import uuid
import time
import traceback

from .execution_tracker import (
    get_database_path,
    get_current_timestamp,
    initialize_execution_history
)


TABLE_NAME = "pipeline_stage_history"


def initialize_stage_history(database_path=None):
    """Create and safely migrate stage-history storage."""

    database = initialize_execution_history(database_path)

    database = get_database_path(database)

    with sqlite3.connect(database) as connection:

        connection.execute("PRAGMA foreign_keys = ON")

        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (

                stage_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                stage_name TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_seconds REAL,

                status TEXT NOT NULL CHECK (
                    status IN ('RUNNING', 'SUCCESS', 'FAILED')
                ),

                error_message TEXT,

                FOREIGN KEY (execution_id)
                    REFERENCES pipeline_execution_history(execution_id)
            )
            """
        )

        # Safely migrate existing stage-history databases.

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


def start_stage(execution, stage_name):
    """Record the beginning of a pipeline stage."""

    database = initialize_stage_history(
        execution["database_path"]
    )

    stage_id = str(uuid.uuid4())

    start_time = get_current_timestamp()
    monotonic_start = time.perf_counter()

    with sqlite3.connect(database) as connection:

        connection.execute("PRAGMA foreign_keys = ON")

        connection.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                stage_id,
                execution_id,
                stage_name,
                start_time,
                status
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                stage_id,
                execution["execution_id"],
                str(stage_name),
                start_time,
                "RUNNING"
            )
        )

    return {
        "stage_id": stage_id,
        "execution_id": execution["execution_id"],
        "stage_name": str(stage_name),
        "database_path": database,
        "monotonic_start": monotonic_start
    }


def finalize_stage(
    stage,
    status,
    error_message=None,
    exception_type=None,
    failure_timestamp=None,
    traceback_details=None
):
    """Finalize a stage and persist its diagnostic information."""

    if status not in {"SUCCESS", "FAILED"}:
        raise ValueError(
            "Stage status must be SUCCESS or FAILED."
        )

    database = get_database_path(
        stage["database_path"]
    )

    duration = round(
        time.perf_counter() - stage["monotonic_start"],
        6
    )

    end_time = get_current_timestamp()

    if status == "FAILED" and failure_timestamp is None:
        failure_timestamp = get_current_timestamp()

    with sqlite3.connect(database) as connection:

        cursor = connection.execute(
            f"""
            UPDATE {TABLE_NAME}

            SET
                end_time = ?,
                duration_seconds = ?,
                status = ?,
                error_message = ?,
                exception_type = ?,
                failure_timestamp = ?,
                traceback_details = ?

            WHERE stage_id = ?
            AND status = 'RUNNING'
            """,
            (
                end_time,
                duration,
                status,
                error_message,
                exception_type,
                failure_timestamp if status == "FAILED" else None,
                traceback_details,
                stage["stage_id"]
            )
        )

        if cursor.rowcount != 1:
            raise ValueError(
                "Stage does not exist or has already finished."
            )

    return {
        "stage_id": stage["stage_id"],
        "stage_name": stage["stage_name"],
        "status": status,
        "duration_seconds": duration,
        "end_time": end_time,
        "error_message": error_message,
        "exception_type": exception_type,
        "failure_timestamp": failure_timestamp,
        "traceback_details": traceback_details
    }


def complete_stage(stage):
    """Mark a stage as successfully completed."""

    return finalize_stage(
        stage,
        status="SUCCESS"
    )


def fail_stage(stage, error):
    """Mark a stage as failed and capture its diagnostics."""

    if isinstance(error, BaseException):

        exception_type = type(error).__name__
        error_message = str(error)

        traceback_details = "".join(
            traceback.format_exception(
                type(error),
                error,
                error.__traceback__
            )
        )

    else:

        exception_type = "Exception"
        error_message = str(error)
        traceback_details = None

    return finalize_stage(
        stage,
        status="FAILED",
        error_message=error_message,
        exception_type=exception_type,
        failure_timestamp=get_current_timestamp(),
        traceback_details=traceback_details
    )


def get_stage_history(execution_id, database_path=None):
    """Retrieve all stage records for an execution."""

    database = initialize_stage_history(database_path)

    with sqlite3.connect(database) as connection:

        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            f"""
            SELECT *
            FROM {TABLE_NAME}
            WHERE execution_id = ?
            ORDER BY start_time, rowid
            """,
            (execution_id,)
        ).fetchall()

    return [dict(row) for row in rows]
