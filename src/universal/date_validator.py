from datetime import datetime, timezone

import pandas as pd

from .datetime_handler import parse_datetime_value


def validate_dates(
    df,
    schema=None,
    date_ranges=None,
    no_future_columns=None,
    chronological_rules=None,
    excluded_columns=None,
    reference_time=None
):
    """
    Validate date values, explicit date ranges,
    future-date constraints and chronological consistency.
    """

    schema = schema or {}

    date_ranges = date_ranges or {}

    no_future_columns = list(
        no_future_columns or []
    )

    chronological_rules = list(
        chronological_rules or []
    )

    excluded_columns = set(
        excluded_columns or []
    )

    if reference_time is None:

        reference_time = pd.Timestamp(
            datetime.now(timezone.utc)
        )

    else:

        reference_time = parse_datetime_value(
            reference_time
        )

        if pd.isna(reference_time):

            raise ValueError(
                "Invalid reference time."
            )

    # STEP 1: Identify eligible date columns.

    date_columns = []

    for column in df.columns:

        if column in excluded_columns:
            continue

        details = schema.get(column, {})

        if details.get("generated", False):
            continue

        if "data_type" in details:

            is_date = (
                details["data_type"] == "date"
            )

        else:

            is_date = (
                pd.api.types.is_datetime64_any_dtype(
                    df[column]
                )
            )

        if is_date:

            date_columns.append(column)

    # STEP 2: Validate rule configuration.

    configured_columns = (
        set(date_ranges)
        | set(no_future_columns)
    )

    for rule in chronological_rules:

        if (
            not isinstance(rule, (list, tuple))
            or len(rule) != 2
            or rule[0] == rule[1]
        ):

            raise ValueError(
                "Chronological rules require two distinct columns."
            )

        configured_columns.update(rule)

    invalid_columns = (
        configured_columns - set(date_columns)
    )

    if invalid_columns:

        raise ValueError(
            "Rules require eligible date columns: "
            f"{sorted(invalid_columns)}"
        )

    def comparable(first, second):

        return (
            (first.tzinfo is None)
            == (second.tzinfo is None)
        )

    parsed_ranges = {}

    for column, rule in date_ranges.items():

        if not isinstance(rule, dict):

            raise ValueError(
                f"Invalid date range rule: {column}"
            )

        if set(rule) - {"min", "max"}:

            raise ValueError(
                f"Unsupported date range option: {column}"
            )

        bounds = {}

        for name in ["min", "max"]:

            value = rule.get(name)

            if value is None:

                bounds[name] = None

                continue

            parsed = parse_datetime_value(value)

            if pd.isna(parsed):

                raise ValueError(
                    f"Invalid date bound: {column}"
                )

            bounds[name] = parsed

        minimum = bounds["min"]
        maximum = bounds["max"]

        if minimum is not None and maximum is not None:

            if not comparable(minimum, maximum):

                raise ValueError(
                    f"Incompatible date bound timezones: {column}"
                )

            if minimum > maximum:

                raise ValueError(
                    f"Minimum date exceeds maximum: {column}"
                )

        parsed_ranges[column] = bounds

    # STEP 3: Initialize validation results.

    warning_rows = pd.Series(
        False,
        index=df.index,
        dtype=bool
    )

    rejected_rows = warning_rows.copy()

    invalid_date_rows = warning_rows.copy()

    range_violation_rows = warning_rows.copy()

    future_date_rows = warning_rows.copy()

    chronology_violation_rows = warning_rows.copy()

    timezone_mismatch_rows = warning_rows.copy()

    parsed_columns = {}

    column_summary = {}

    record_issues = {}

    chronological_summary = []

    def add_issue(
        position,
        column,
        reason,
        severity,
        related_column=None
    ):

        issue = {
            "column": column,
            "reason": reason,
            "severity": severity
        }

        if related_column is not None:

            issue["related_column"] = related_column

        record_issues.setdefault(
            position, []
        ).append(issue)

        if severity == "REJECTED":

            rejected_rows.iloc[position] = True

        else:

            warning_rows.iloc[position] = True

    # STEP 4: Validate individual date columns.

    for column in date_columns:

        parsed_values = []

        missing_count = 0
        invalid_count = 0
        range_count = 0
        future_count = 0
        timezone_count = 0

        bounds = parsed_ranges.get(column, {})

        minimum = bounds.get("min")
        maximum = bounds.get("max")

        for position, value in enumerate(df[column]):

            if pd.isna(value) or not str(value).strip():

                missing_count += 1

                parsed_values.append(pd.NaT)

                continue

            parsed = parse_datetime_value(value)

            parsed_values.append(parsed)

            if pd.isna(parsed):

                invalid_count += 1

                invalid_date_rows.iloc[position] = True

                add_issue(
                    position,
                    column,
                    "INVALID_DATE",
                    "WARNING"
                )

                continue

            # Check explicit minimum and maximum dates.

            range_violation = False

            timezone_mismatch = False

            for bound, direction in [
                (minimum, "min"),
                (maximum, "max")
            ]:

                if bound is None:
                    continue

                if not comparable(parsed, bound):

                    timezone_mismatch = True

                    continue

                if direction == "min" and parsed < bound:

                    range_violation = True

                if direction == "max" and parsed > bound:

                    range_violation = True

            if range_violation:

                range_count += 1

                range_violation_rows.iloc[position] = True

                add_issue(
                    position,
                    column,
                    "DATE_RANGE_VIOLATION",
                    "REJECTED"
                )

            # Check explicitly prohibited future dates.

            if column in no_future_columns:

                if not comparable(parsed, reference_time):

                    timezone_mismatch = True

                elif parsed > reference_time:

                    future_count += 1

                    future_date_rows.iloc[position] = True

                    add_issue(
                        position,
                        column,
                        "FUTURE_DATE",
                        "REJECTED"
                    )

            if timezone_mismatch:

                timezone_count += 1

                timezone_mismatch_rows.iloc[position] = True

                add_issue(
                    position,
                    column,
                    "TIMEZONE_MISMATCH",
                    "WARNING"
                )

        parsed_columns[column] = parsed_values

        column_summary[column] = {
            "total_records": int(len(df)),
            "missing_count": missing_count,
            "invalid_date_count": invalid_count,
            "parsed_date_count": (
                len(df) - missing_count - invalid_count
            ),
            "range_violation_count": range_count,
            "future_date_count": future_count,
            "timezone_mismatch_count": timezone_count,
            "configured_minimum": (
                minimum.isoformat()
                if minimum is not None
                else None
            ),
            "configured_maximum": (
                maximum.isoformat()
                if maximum is not None
                else None
            ),
            "future_dates_prohibited": (
                column in no_future_columns
            )
        }

    # STEP 5: Validate chronological relationships.

    for start_column, end_column in chronological_rules:

        checked_count = 0
        skipped_count = 0
        violation_count = 0
        timezone_count = 0

        for position in range(len(df)):

            start = parsed_columns[start_column][position]

            end = parsed_columns[end_column][position]

            if pd.isna(start) or pd.isna(end):

                skipped_count += 1

                continue

            if not comparable(start, end):

                timezone_count += 1

                skipped_count += 1

                timezone_mismatch_rows.iloc[position] = True

                add_issue(
                    position,
                    start_column,
                    "CHRONOLOGY_TIMEZONE_MISMATCH",
                    "WARNING",
                    related_column=end_column
                )

                continue

            checked_count += 1

            if start > end:

                violation_count += 1

                chronology_violation_rows.iloc[position] = True

                add_issue(
                    position,
                    start_column,
                    "CHRONOLOGICAL_VIOLATION",
                    "REJECTED",
                    related_column=end_column
                )

        chronological_summary.append({
            "start_column": start_column,
            "end_column": end_column,
            "checked_records": checked_count,
            "skipped_records": skipped_count,
            "violation_count": violation_count,
            "timezone_mismatch_count": timezone_count
        })

    # STEP 6: Apply rejection priority.

    warning_rows = warning_rows & ~rejected_rows

    affected_rows = warning_rows | rejected_rows

    # STEP 7: Generate detailed validation report.

    return {
        "warning_rows": warning_rows,
        "rejected_rows": rejected_rows,
        "invalid_date_rows": invalid_date_rows,
        "range_violation_rows": range_violation_rows,
        "future_date_rows": future_date_rows,
        "chronology_violation_rows": chronology_violation_rows,
        "timezone_mismatch_rows": timezone_mismatch_rows,
        "report": {
            "total_records": int(len(df)),
            "date_column_count": len(date_columns),
            "date_columns": date_columns,
            "reference_time": reference_time.isoformat(),
            "invalid_date_record_count": int(
                invalid_date_rows.sum()
            ),
            "range_violation_record_count": int(
                range_violation_rows.sum()
            ),
            "future_date_record_count": int(
                future_date_rows.sum()
            ),
            "chronology_violation_record_count": int(
                chronology_violation_rows.sum()
            ),
            "timezone_mismatch_record_count": int(
                timezone_mismatch_rows.sum()
            ),
            "affected_record_count": int(
                affected_rows.sum()
            ),
            "warning_rows": int(warning_rows.sum()),
            "rejected_rows": int(rejected_rows.sum()),
            "affected_row_positions": sorted(
                record_issues
            ),
            "column_summary": column_summary,
            "chronological_summary": chronological_summary,
            "record_details": [
                {
                    "row_position": position,
                    "issues": record_issues[position]
                }
                for position in sorted(record_issues)
            ]
        }
    }
