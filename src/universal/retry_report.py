
import json
from collections import defaultdict
from pathlib import Path

from .retry_manager import get_retry_history
from .stage_tracker import get_stage_history


PROJECT_ROOT = Path(__file__).resolve().parents[2]

REPORT_DIRECTORY = PROJECT_ROOT / "reports"


def generate_retry_summary(
    database_path=None,
    execution_id=None
):
    """Generate retry statistics for monitored executions."""

    all_records = get_retry_history(
        database_path=database_path,
        execution_id=execution_id,
        limit=100000
    )

    # Exclude historical records that cannot be linked
    # to an actual monitored execution.

    retry_records = [
        record
        for record in all_records
        if (
            record["execution_id"] is not None
            and record["stage_name"] != "UNKNOWN"
        )
    ]

    ignored_unlinked_records = (
        len(all_records) - len(retry_records)
    )

    execution_ids = {
        record["execution_id"]
        for record in retry_records
    }

    stage_records = []

    for current_execution_id in execution_ids:

        stage_records.extend(
            get_stage_history(
                current_execution_id,
                database_path
            )
        )

    stage_status = {}

    for stage in stage_records:

        key = (
            stage["execution_id"],
            stage["stage_name"]
        )

        stage_status[key] = stage["status"]

    grouped = defaultdict(list)

    for record in retry_records:

        key = (
            record["execution_id"],
            record["stage_name"]
        )

        grouped[key].append(record)

    total_attempts = len(retry_records)

    retrying_attempts = sum(
        record["outcome"] == "RETRYING"
        for record in retry_records
    )

    exhausted_attempts = sum(
        record["outcome"] == "EXHAUSTED"
        for record in retry_records
    )

    non_retryable_attempts = sum(
        record["outcome"] == "NOT_RETRYABLE"
        for record in retry_records
    )

    recovered_stages = 0
    exhausted_stages = 0
    non_retryable_stages = 0

    stage_statistics = defaultdict(
        lambda: {
            "total_attempts": 0,
            "retrying_attempts": 0,
            "exhausted_attempts": 0,
            "non_retryable_attempts": 0,
            "total_retry_delay_seconds": 0.0,
            "recovered_stages": 0,
            "failed_stages": 0
        }
    )

    for key, records in grouped.items():

        execution, stage_name = key

        statistics = stage_statistics[stage_name]

        statistics["total_attempts"] += len(records)

        retry_count = sum(
            record["outcome"] == "RETRYING"
            for record in records
        )

        exhausted_count = sum(
            record["outcome"] == "EXHAUSTED"
            for record in records
        )

        permanent_count = sum(
            record["outcome"] == "NOT_RETRYABLE"
            for record in records
        )

        statistics["retrying_attempts"] += retry_count
        statistics["exhausted_attempts"] += exhausted_count
        statistics["non_retryable_attempts"] += permanent_count

        delay = sum(
            record["retry_delay_seconds"] or 0
            for record in records
        )

        statistics["total_retry_delay_seconds"] += delay

        current_status = stage_status.get(
            key,
            "UNKNOWN"
        )

        if retry_count > 0 and current_status == "SUCCESS":

            recovered_stages += 1
            statistics["recovered_stages"] += 1

        if exhausted_count > 0:

            exhausted_stages += 1
            statistics["failed_stages"] += 1

        if permanent_count > 0:

            non_retryable_stages += 1
            statistics["failed_stages"] += 1

    total_delay = sum(
        record["retry_delay_seconds"] or 0
        for record in retry_records
    )

    average_delay = (
        total_delay / retrying_attempts
        if retrying_attempts
        else 0
    )

    return {
        "total_retry_attempts": total_attempts,
        "ignored_unlinked_records": ignored_unlinked_records,
        "retrying_attempts": retrying_attempts,
        "exhausted_attempts": exhausted_attempts,
        "non_retryable_attempts": non_retryable_attempts,
        "successful_recoveries": recovered_stages,
        "exhausted_stages": exhausted_stages,
        "non_retryable_stages": non_retryable_stages,
        "total_retry_delay_seconds": round(total_delay, 3),
        "average_retry_delay_seconds": round(average_delay, 3),
        "stage_statistics": {
            stage: {
                key: round(value, 3)
                if isinstance(value, float)
                else value
                for key, value in statistics.items()
            }
            for stage, statistics in stage_statistics.items()
        }
    }


def generate_retry_report(
    database_path=None,
    execution_id=None,
    output_path=None
):
    """Generate and save a JSON retry monitoring report."""

    summary = generate_retry_summary(
        database_path=database_path,
        execution_id=execution_id
    )

    if output_path is None:

        REPORT_DIRECTORY.mkdir(
            parents=True,
            exist_ok=True
        )

        output_path = (
            REPORT_DIRECTORY / "retry_monitoring_report.json"
        )

    else:

        output_path = Path(output_path)

        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            summary,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\n========== RETRY MONITORING REPORT ==========")

    print(
        "Total retry attempts:",
        summary["total_retry_attempts"]
    )

    print(
        "Ignored unlinked records:",
        summary["ignored_unlinked_records"]
    )

    print(
        "Successful recoveries:",
        summary["successful_recoveries"]
    )

    print(
        "Exhausted attempts:",
        summary["exhausted_attempts"]
    )

    print(
        "Non-retryable failures:",
        summary["non_retryable_attempts"]
    )

    print(
        "Total retry delay:",
        summary["total_retry_delay_seconds"],
        "seconds"
    )

    print("\nSTAGE-WISE STATISTICS")

    for stage, statistics in summary["stage_statistics"].items():

        print(f"\n{stage}")

        for key, value in statistics.items():

            print(f"  {key}: {value}")

    print("\nReport saved:", output_path)

    print("========== REPORT GENERATION COMPLETED ==========")

    return {
        "summary": summary,
        "report_path": str(output_path)
    }
