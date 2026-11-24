import pandas as pd


def validate_missing_values(
    df,
    required_columns=None,
    excluded_columns=None
):
    """
    Analyze missing values and record completeness.

    Required columns must be explicitly specified.
    Excluded columns do not affect source completeness.
    """

    required_columns = list(required_columns or [])
    excluded_columns = set(excluded_columns or [])

    unknown_columns = set(required_columns) - set(df.columns)

    if unknown_columns:
        raise ValueError(
            f"Required columns not found: {sorted(unknown_columns)}"
        )

    if set(required_columns) & excluded_columns:
        raise ValueError(
            "Required columns cannot also be excluded."
        )

    source_columns = [
        column
        for column in df.columns
        if column not in excluded_columns
    ]

    if not source_columns:
        raise ValueError(
            "No source columns available for validation."
        )

    source = df[source_columns].copy()

    missing_mask = source.isna()

    # Detect empty and whitespace-only text values.
    for column in source_columns:

        blank_mask = (
            source[column]
            .astype("string")
            .str.strip()
            .eq("")
            .fillna(False)
        )

        missing_mask[column] = (
            missing_mask[column] | blank_mask
        )

    # Record-level missing-value detection.
    missing_counts = missing_mask.sum(axis=1)

    empty_rows = missing_mask.all(axis=1)

    missing_rows = missing_mask.any(axis=1)

    # Required-field validation.
    required_missing_rows = pd.Series(
        False,
        index=df.index,
        dtype=bool
    )

    if required_columns:

        required_missing_rows = (
            missing_mask[required_columns].any(axis=1)
        )

    rejected_rows = empty_rows | required_missing_rows

    warning_rows = missing_rows & ~rejected_rows

    # Column-level missing-value statistics.
    column_summary = {}

    for column in source_columns:

        missing_count = int(missing_mask[column].sum())

        missing_percentage = (
            round(missing_count / len(df) * 100, 2)
            if len(df) > 0
            else 0.0
        )

        column_summary[column] = {
            "missing_count": missing_count,
            "missing_percentage": missing_percentage,
            "required": column in required_columns
        }

    total_cells = len(df) * len(source_columns)

    missing_cells = int(missing_mask.sum().sum())

    completeness_score = (
        round(
            (total_cells - missing_cells)
            / total_cells * 100,
            2
        )
        if total_cells > 0
        else None
    )

    # Record-level missing field details.
    record_details = []

    for position, row in enumerate(
        missing_mask.itertuples(index=False, name=None)
    ):

        missing_columns = [
            column
            for column, missing in zip(source_columns, row)
            if missing
        ]

        if missing_columns:

            record_details.append({
                "row_position": position,
                "missing_columns": missing_columns,
                "missing_required_columns": [
                    column
                    for column in missing_columns
                    if column in required_columns
                ]
            })

    return {
        "missing_mask": missing_mask,
        "missing_counts": missing_counts,
        "missing_rows": missing_rows,
        "empty_rows": empty_rows,
        "required_missing_rows": required_missing_rows,
        "warning_rows": warning_rows,
        "rejected_rows": rejected_rows,
        "report": {
            "total_records": int(len(df)),
            "source_columns": len(source_columns),
            "total_cells": total_cells,
            "missing_cells": missing_cells,
            "missing_value_rows": int(missing_rows.sum()),
            "empty_rows": int(empty_rows.sum()),
            "required_missing_rows": int(
                required_missing_rows.sum()
            ),
            "warning_rows": int(warning_rows.sum()),
            "rejected_rows": int(rejected_rows.sum()),
            "completeness_score": completeness_score,
            "column_summary": column_summary,
            "record_details": record_details
        }
    }
