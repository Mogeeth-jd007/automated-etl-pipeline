import pandas as pd


SUPPORTED_TYPES = {
    "numeric",
    "currency",
    "percentage",
    "date",
    "boolean"
}


def validate_conversion_failures(
    df,
    schema=None,
    required_columns=None,
    excluded_columns=None
):
    """
    Validate conversion failures recorded during transformation.

    Optional field failures generate warnings.
    Required field failures generate rejections.
    """

    required_columns = set(required_columns or [])
    excluded_columns = set(excluded_columns or [])

    unknown_columns = required_columns - set(df.columns)

    if unknown_columns:
        raise ValueError(
            f"Required columns not found: {sorted(unknown_columns)}"
        )

    if required_columns & excluded_columns:
        raise ValueError(
            "Required columns cannot also be excluded."
        )

    schema = schema or {}

    total_records = len(df)

    failed_rows = pd.Series(
        False,
        index=df.index,
        dtype=bool
    )

    rejected_rows = failed_rows.copy()

    column_summary = {}

    record_issues = {}

    total_attempted = 0
    total_successful = 0
    total_failed = 0

    for column, details in schema.items():

        if column in excluded_columns:
            continue

        if details.get("generated", False):
            continue

        conversion = details.get("conversion_report")

        if conversion is None:
            continue

        if column not in df.columns:
            raise ValueError(
                f"Conversion column not found: {column}"
            )

        data_type = details.get("data_type")

        if data_type not in SUPPORTED_TYPES:
            raise ValueError(
                f"Unsupported conversion type: {data_type}"
            )

        if conversion["total_records"] != total_records:
            raise ValueError(
                f"Conversion record count mismatch: {column}"
            )

        positions = conversion["failed_row_positions"]

        attempted = conversion["attempted_conversions"]

        successful = conversion["successful_conversions"]

        failed = conversion["failed_conversions"]

        original_missing = conversion["original_missing_count"]

        if (
            min(attempted, successful, failed, original_missing) < 0
            or attempted != successful + failed
            or attempted + original_missing != total_records
            or failed != len(positions)
            or len(positions) != len(set(positions))
        ):
            raise ValueError(
                f"Inconsistent conversion metadata: {column}"
            )

        for position in positions:

            if (
                type(position) is not int
                or position < 0
                or position >= total_records
            ):
                raise ValueError(
                    f"Invalid conversion row position: {position}"
                )

            if not pd.isna(df[column].iloc[position]):
                raise ValueError(
                    f"Conversion metadata mismatch: {column}"
                )

            failed_rows.iloc[position] = True

            is_required = column in required_columns

            if is_required:
                rejected_rows.iloc[position] = True

            record_issues.setdefault(
                position, []
            ).append({
                "column": column,
                "data_type": data_type,
                "reason": "CONVERSION_FAILURE",
                "severity": (
                    "REJECTED" if is_required else "WARNING"
                )
            })

        total_attempted += attempted
        total_successful += successful
        total_failed += failed

        column_summary[column] = {
            "data_type": data_type,
            "attempted_conversions": attempted,
            "successful_conversions": successful,
            "failed_conversions": failed,
            "original_missing_count": original_missing,
            "required": column in required_columns,
            "failed_row_positions": positions
        }

    warning_rows = failed_rows & ~rejected_rows

    affected_positions = sorted(record_issues)

    record_details = [
        {
            "row_position": position,
            "issues": record_issues[position]
        }
        for position in affected_positions
    ]

    failure_rate = (
        round(total_failed / total_attempted * 100, 2)
        if total_attempted > 0
        else None
    )

    return {
        "failed_rows": failed_rows,
        "warning_rows": warning_rows,
        "rejected_rows": rejected_rows,
        "report": {
            "total_records": total_records,
            "tracked_columns": len(column_summary),
            "attempted_conversions": total_attempted,
            "successful_conversions": total_successful,
            "failed_conversions": total_failed,
            "failure_rate_percent": failure_rate,
            "affected_record_count": int(failed_rows.sum()),
            "warning_rows": int(warning_rows.sum()),
            "rejected_rows": int(rejected_rows.sum()),
            "affected_row_positions": affected_positions,
            "column_summary": column_summary,
            "record_details": record_details
        }
    }
