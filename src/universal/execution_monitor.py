
import sqlite3

from .execution_tracker import get_database_path
from .stage_tracker import get_stage_history


TABLE_NAME = "pipeline_execution_history"


def get_execution_history(
    database_path=None,
    status=None,
    limit=20
):
    """Retrieve recent pipeline executions."""

    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer.")

    if status is not None:

        status = status.upper()

        if status not in {"RUNNING", "SUCCESS", "FAILED"}:
            raise ValueError(
                "status must be RUNNING, SUCCESS or FAILED."
            )

    database = get_database_path(database_path)

    query = f"SELECT * FROM {TABLE_NAME}"
    parameters = []

    if status is not None:
        query += " WHERE status = ?"
        parameters.append(status)

    query += " ORDER BY start_time DESC LIMIT ?"
    parameters.append(limit)

    with sqlite3.connect(database) as connection:

        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            query,
            parameters
        ).fetchall()

    return [dict(row) for row in rows]


def get_execution_details(
    execution_id,
    database_path=None
):
    """Retrieve complete details of one execution."""

    database = get_database_path(database_path)

    with sqlite3.connect(database) as connection:

        connection.row_factory = sqlite3.Row

        row = connection.execute(
            f"""
            SELECT *
            FROM {TABLE_NAME}
            WHERE execution_id = ?
            """,
            (execution_id,)
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def get_execution_statistics(database_path=None):
    """Calculate overall execution statistics."""

    database = get_database_path(database_path)

    with sqlite3.connect(database) as connection:

        result = connection.execute(
            f"""
            SELECT
                COUNT(*),

                SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END),

                SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END),

                SUM(CASE WHEN status = 'RUNNING' THEN 1 ELSE 0 END),

                AVG(
                    CASE WHEN status = 'SUCCESS'
                    THEN duration_seconds END
                )

            FROM {TABLE_NAME}
            """
        ).fetchone()

    total = result[0] or 0
    successful = result[1] or 0
    failed = result[2] or 0
    running = result[3] or 0

    completed = successful + failed

    return {
        "total_executions": total,
        "successful_executions": successful,
        "failed_executions": failed,
        "running_executions": running,
        "success_rate": round(successful / completed * 100, 2) if completed else 0.0,
        "failure_rate": round(failed / completed * 100, 2) if completed else 0.0,
        "average_success_duration": result[4]
    }


def display_execution_history(
    database_path=None,
    status=None,
    limit=20
):
    """Display recent execution history."""

    executions = get_execution_history(
        database_path,
        status,
        limit
    )

    print("\n========== PIPELINE EXECUTION HISTORY ==========\n")

    if not executions:
        print("No execution records found.")
        return

    for execution in executions:

        print(f"Execution ID : {execution['execution_id']}")
        print(f"Dataset      : {execution['dataset_name']}")
        print(f"Status       : {execution['status']}")
        print(f"Start time   : {execution['start_time']}")
        print(f"Duration     : {execution['duration_seconds']}")
        print(f"Failed stage : {execution['failed_stage']}")
        print("-" * 60)


def display_execution_statistics(database_path=None):
    """Display execution statistics."""

    statistics = get_execution_statistics(database_path)

    print("\n========== EXECUTION STATISTICS ==========\n")

    for key, value in statistics.items():
        print(f"{key}: {value}")

    print("\n==========================================\n")


def get_stage_performance_report(
    execution_id,
    database_path=None
):
    """Generate stage-level performance metrics."""

    stages = get_stage_history(
        execution_id,
        database_path
    )

    if not stages:
        raise ValueError(
            f"No stage history found for execution: {execution_id}"
        )

    total_stages = len(stages)

    successful = sum(
        stage["status"] == "SUCCESS"
        for stage in stages
    )

    failed = sum(
        stage["status"] == "FAILED"
        for stage in stages
    )

    running = sum(
        stage["status"] == "RUNNING"
        for stage in stages
    )

    completed = [
        stage for stage in stages
        if stage["duration_seconds"] is not None
    ]

    cumulative = sum(
        stage["duration_seconds"] or 0
        for stage in stages
    )

    slowest = (
        max(
            completed,
            key=lambda stage: stage["duration_seconds"]
        )
        if completed else None
    )

    return {
        "execution_id": execution_id,
        "total_stages": total_stages,
        "successful_stages": successful,
        "failed_stages": failed,
        "running_stages": running,
        "stage_success_rate": round(successful / total_stages * 100, 2),
        "cumulative_stage_duration": round(cumulative, 6),
        "slowest_stage": slowest["stage_name"] if slowest else None,
        "slowest_stage_duration": slowest["duration_seconds"] if slowest else None,
        "stages": stages
    }


def display_stage_performance_report(
    execution_id,
    database_path=None
):
    """Display stage performance."""

    report = get_stage_performance_report(
        execution_id,
        database_path
    )

    print("\n========== PIPELINE PERFORMANCE REPORT ==========\n")

    print(f"Execution ID: {execution_id}")

    for stage in report["stages"]:

        print(
            f"{stage['stage_name']:<25}"
            f"{stage['status']:<12}"
            f"{stage['duration_seconds']}"
        )

    print("\nTotal stages:", report["total_stages"])
    print("Successful stages:", report["successful_stages"])
    print("Failed stages:", report["failed_stages"])
    print("Running stages:", report["running_stages"])

    print(
        "Cumulative duration:",
        report["cumulative_stage_duration"]
    )

    print("Slowest stage:", report["slowest_stage"])

    print("\n==================================================\n")

    return report


def get_failure_history(database_path=None, limit=20):
    """Retrieve recent failed executions."""

    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer.")

    database = get_database_path(database_path)

    with sqlite3.connect(database) as connection:

        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            f"""
            SELECT *
            FROM {TABLE_NAME}
            WHERE status = 'FAILED'
            ORDER BY COALESCE(
                failure_timestamp,
                end_time,
                start_time
            ) DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

    return [dict(row) for row in rows]


def get_failure_details(execution_id, database_path=None):
    """Retrieve overall and stage-level failure diagnostics."""

    execution = get_execution_details(
        execution_id,
        database_path
    )

    if execution is None:
        return None

    stages = get_stage_history(
        execution_id,
        database_path
    )

    failed_stages = [
        stage for stage in stages
        if stage["status"] == "FAILED"
    ]

    return {
        "execution": execution,
        "failed_stages": failed_stages
    }


def display_failure_diagnostics(
    execution_id,
    database_path=None
):
    """Display complete persisted failure diagnostics."""

    details = get_failure_details(
        execution_id,
        database_path
    )

    if details is None:
        print("Execution not found.")
        return None

    execution = details["execution"]

    if execution["status"] != "FAILED":
        print("This execution did not fail.")
        return details

    print("\n========== FAILURE DIAGNOSTICS ==========\n")

    print("Execution ID:", execution["execution_id"])
    print("Dataset:", execution["dataset_name"])
    print("Failed stage:", execution["failed_stage"])
    print("Exception type:", execution["exception_type"])
    print("Error message:", execution["error_message"])
    print("Failure timestamp:", execution["failure_timestamp"])

    print("\nOVERALL TRACEBACK")
    print(execution["traceback_details"] or "Not available")

    for stage in details["failed_stages"]:

        print("\nFAILED STAGE:", stage["stage_name"])
        print("Exception:", stage["exception_type"])
        print("Message:", stage["error_message"])
        print("Timestamp:", stage["failure_timestamp"])

        print("\nSTAGE TRACEBACK")
        print(stage["traceback_details"] or "Not available")

    print("\n=========================================\n")

    return details
