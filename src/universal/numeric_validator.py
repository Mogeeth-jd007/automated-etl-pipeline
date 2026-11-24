import math
import pandas as pd

from .schema_detector import is_identifier_column


def validate_numeric_values(
    df,
    schema=None,
    numeric_ranges=None,
    excluded_columns=None,
    iqr_multiplier=1.5,
    min_samples=8
):
    """
    Validate numeric ranges and detect statistical outliers.

    Explicit range violations generate rejections.
    Statistical outliers generate warnings.
    """

    numeric_ranges = numeric_ranges or {}
    excluded_columns = set(excluded_columns or [])

    if (
        not math.isfinite(iqr_multiplier)
        or iqr_multiplier <= 0
    ):
        raise ValueError(
            "IQR multiplier must be positive and finite."
        )

    if type(min_samples) is not int or min_samples < 4:
        raise ValueError(
            "Minimum samples must be an integer of at least 4."
        )

    unknown_columns = set(numeric_ranges) - set(df.columns)

    if unknown_columns:
        raise ValueError(
            f"Range columns not found: {sorted(unknown_columns)}"
        )

    numeric_columns = []

    for column in df.columns:

        if column in excluded_columns:
            continue

        details = (schema or {}).get(column, {})

        if details.get("generated", False):
            continue

        if "data_type" in details:

            is_numeric = (
                details["data_type"] == "numeric"
            )

        else:

            is_numeric = (
                pd.api.types.is_numeric_dtype(df[column])
                and not pd.api.types.is_bool_dtype(df[column])
                and not is_identifier_column(column)
            )

        if is_numeric:
            numeric_columns.append(column)

    invalid_range_columns = (
        set(numeric_ranges) - set(numeric_columns)
    )

    if invalid_range_columns:
        raise ValueError(
            "Range rules require eligible numeric columns: "
            f"{sorted(invalid_range_columns)}"
        )

    outlier_rows = pd.Series(
        False,
        index=df.index,
        dtype=bool
    )

    range_violation_rows = outlier_rows.copy()

    column_summary = {}

    record_issues = {}

    total_outlier_cells = 0
    total_range_violations = 0

    for column in numeric_columns:

        values = pd.to_numeric(
            df[column],
            errors="coerce"
        )

        values = values.replace(
            [float("inf"), float("-inf")],
            float("nan")
        )

        available = values.dropna()

        range_rule = numeric_ranges.get(column, {})

        minimum = range_rule.get("min")
        maximum = range_rule.get("max")

        for bound in [minimum, maximum]:

            if bound is not None:

                if (
                    isinstance(bound, bool)
                    or not isinstance(bound, (int, float))
                    or not math.isfinite(bound)
                ):
                    raise ValueError(
                        f"Invalid numeric bound: {column}"
                    )

        if (
            minimum is not None
            and maximum is not None
            and minimum > maximum
        ):
            raise ValueError(
                f"Minimum exceeds maximum: {column}"
            )

        range_mask = pd.Series(
            False,
            index=df.index,
            dtype=bool
        )

        if minimum is not None:

            range_mask = (
                range_mask
                | values.lt(minimum).fillna(False)
            )

        if maximum is not None:

            range_mask = (
                range_mask
                | values.gt(maximum).fillna(False)
            )

        outlier_mask = pd.Series(
            False,
            index=df.index,
            dtype=bool
        )

        q1 = None
        q3 = None
        iqr = None
        lower_bound = None
        upper_bound = None

        detection_status = "INSUFFICIENT_SAMPLES"

        # Exclude explicit range violations from the
        # statistical reference population.
        reference = values[~range_mask].dropna()

        if len(reference) >= min_samples:

            q1 = float(reference.quantile(0.25))
            q3 = float(reference.quantile(0.75))

            iqr = q3 - q1

            if iqr > 0 and math.isfinite(iqr):

                lower_bound = q1 - iqr_multiplier * iqr
                upper_bound = q3 + iqr_multiplier * iqr

                if (
                    math.isfinite(lower_bound)
                    and math.isfinite(upper_bound)
                ):

                    outlier_mask = (
                        values.lt(lower_bound).fillna(False)
                        | values.gt(upper_bound).fillna(False)
                    )

                    outlier_mask = (
                        outlier_mask & ~range_mask
                    )

                    detection_status = "COMPLETED"

                else:

                    lower_bound = None
                    upper_bound = None

                    detection_status = "NONFINITE_BOUNDS"

            else:

                detection_status = (
                    "ZERO_IQR"
                    if iqr == 0
                    else "NONFINITE_IQR"
                )

        outlier_rows = outlier_rows | outlier_mask

        range_violation_rows = (
            range_violation_rows | range_mask
        )

        outlier_count = int(outlier_mask.sum())

        range_count = int(range_mask.sum())

        total_outlier_cells += outlier_count

        total_range_violations += range_count

        for position in range(len(df)):

            if range_mask.iloc[position]:

                record_issues.setdefault(
                    position, []
                ).append({
                    "column": column,
                    "reason": "NUMERIC_RANGE_VIOLATION",
                    "severity": "REJECTED"
                })

            elif outlier_mask.iloc[position]:

                record_issues.setdefault(
                    position, []
                ).append({
                    "column": column,
                    "reason": "STATISTICAL_OUTLIER",
                    "severity": "WARNING"
                })

        column_summary[column] = {
            "available_values": int(len(available)),
            "reference_samples": int(len(reference)),
            "configured_minimum": minimum,
            "configured_maximum": maximum,
            "q1": q1,
            "q3": q3,
            "iqr": (
                iqr
                if iqr is not None and math.isfinite(iqr)
                else None
            ),
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "outlier_count": outlier_count,
            "range_violation_count": range_count,
            "detection_status": detection_status
        }

    rejected_rows = range_violation_rows

    warning_rows = outlier_rows & ~rejected_rows

    affected_rows = outlier_rows | rejected_rows

    return {
        "outlier_rows": outlier_rows,
        "range_violation_rows": range_violation_rows,
        "warning_rows": warning_rows,
        "rejected_rows": rejected_rows,
        "report": {
            "total_records": int(len(df)),
            "numeric_column_count": len(numeric_columns),
            "numeric_columns": numeric_columns,
            "iqr_multiplier": iqr_multiplier,
            "minimum_samples": min_samples,
            "total_outlier_cells": total_outlier_cells,
            "total_range_violations": total_range_violations,
            "outlier_record_count": int(outlier_rows.sum()),
            "range_violation_record_count": int(
                range_violation_rows.sum()
            ),
            "affected_record_count": int(affected_rows.sum()),
            "warning_rows": int(warning_rows.sum()),
            "rejected_rows": int(rejected_rows.sum()),
            "affected_row_positions": sorted(record_issues),
            "column_summary": column_summary,
            "record_details": [
                {
                    "row_position": position,
                    "issues": record_issues[position]
                }
                for position in sorted(record_issues)
            ]
        }
    }
