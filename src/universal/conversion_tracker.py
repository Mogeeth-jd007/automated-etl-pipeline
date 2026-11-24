import pandas as pd


TRACKED_DATA_TYPES = {
    "numeric",
    "currency",
    "percentage",
    "date",
    "boolean"
}


def track_conversion_failures(
    original_series,
    converted_series,
    data_type
):
    """Measure successful and failed data conversions."""

    if len(original_series) != len(converted_series):
        raise ValueError(
            "Original and converted series must have equal lengths."
        )

    if not original_series.index.equals(converted_series.index):
        raise ValueError(
            "Original and converted series must have matching indexes."
        )

    if data_type not in TRACKED_DATA_TYPES:
        raise ValueError(
            f"Unsupported conversion type: {data_type}"
        )

    original_missing = original_series.isna()

    attempted = original_series.notna()

    successful = (
        attempted
        & converted_series.notna()
    )

    failed = (
        attempted
        & converted_series.isna()
    )

    total_records = int(len(original_series))

    attempted_count = int(attempted.sum())

    successful_count = int(successful.sum())

    failed_count = int(failed.sum())

    failure_rate = (
        round(
            failed_count / attempted_count * 100,
            2
        )
        if attempted_count > 0
        else 0.0
    )

    return {
        "data_type": data_type,
        "total_records": total_records,
        "original_missing_count": int(
            original_missing.sum()
        ),
        "attempted_conversions": attempted_count,
        "successful_conversions": successful_count,
        "failed_conversions": failed_count,
        "failure_rate_percent": failure_rate,
        "failed_row_positions": [
            position
            for position, status in enumerate(failed)
            if status
        ]
    }
