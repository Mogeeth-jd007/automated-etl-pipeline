from collections import Counter


def generate_transformation_summary(schema):
    """Generate dataset-level transformation quality statistics."""

    source_columns = {
        column: details
        for column, details in schema.items()
        if not details.get("generated", False)
    }

    generated_columns = [
        column
        for column, details in schema.items()
        if details.get("generated", False)
    ]

    data_type_distribution = Counter()

    attempted = 0
    successful = 0
    failed = 0
    original_missing = 0

    affected_rows = set()
    affected_columns = []

    tracked_columns = 0

    for column, details in source_columns.items():

        data_type = details["data_type"]

        data_type_distribution[data_type] += 1

        original_missing += details.get(
            "null_count", 0
        )

        report = details.get("conversion_report")

        if report is None:
            continue

        tracked_columns += 1

        attempted += report["attempted_conversions"]

        successful += report["successful_conversions"]

        failed += report["failed_conversions"]

        if report["failed_conversions"] > 0:

            affected_columns.append(column)

            affected_rows.update(
                report["failed_row_positions"]
            )

    success_rate = (
        round(successful / attempted * 100, 2)
        if attempted > 0
        else None
    )

    failure_rate = (
        round(failed / attempted * 100, 2)
        if attempted > 0
        else None
    )

    return {
        "source_columns": len(source_columns),
        "generated_columns": len(generated_columns),
        "total_output_columns": len(schema),
        "generated_column_names": generated_columns,
        "data_type_distribution": dict(
            sorted(data_type_distribution.items())
        ),
        "tracked_conversion_columns": tracked_columns,
        "original_missing_cells": original_missing,
        "attempted_conversions": attempted,
        "successful_conversions": successful,
        "failed_conversions": failed,
        "conversion_success_rate_percent": success_rate,
        "conversion_failure_rate_percent": failure_rate,
        "affected_column_count": len(affected_columns),
        "affected_columns": affected_columns,
        "affected_record_count": len(affected_rows),
        "affected_row_positions": sorted(affected_rows)
    }
