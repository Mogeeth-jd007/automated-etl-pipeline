import pandas as pd

from .schema_detector import is_identifier_column


def validate_identifiers(
    df,
    schema=None,
    excluded_columns=None
):
    """
    Analyze identifier completeness and uniqueness.

    Repeated identifiers are reported without automatically
    rejecting records or assuming primary-key constraints.
    """

    excluded_columns = set(excluded_columns or [])

    identifier_columns = []

    for column in df.columns:

        if column in excluded_columns:
            continue

        if schema is not None:

            details = schema.get(column, {})

            if details.get("generated", False):
                continue

            if "data_type" in details:

                is_identifier = (
                    details["data_type"] == "identifier"
                )

            else:

                is_identifier = is_identifier_column(column)

        else:

            is_identifier = is_identifier_column(column)

        if is_identifier:

            identifier_columns.append(column)

    column_summary = {}

    candidate_keys = []

    repeated_identifier_columns = []

    missing_identifier_columns = []

    affected_positions = set()

    record_issues = {}

    for column in identifier_columns:

        values = df[column].astype("string").str.strip()

        missing_mask = (
            values.isna()
            | values.eq("").fillna(False)
        )

        available_values = values[~missing_mask]

        total_count = len(df)

        missing_count = int(missing_mask.sum())

        available_count = len(available_values)

        unique_count = int(available_values.nunique())

        repeated_count = available_count - unique_count

        repeated_members = (
            available_values.duplicated(keep=False)
        )

        repeated_member_count = int(
            repeated_members.sum()
        )

        uniqueness_rate = (
            round(
                unique_count / available_count * 100,
                2
            )
            if available_count > 0
            else None
        )

        completeness_rate = (
            round(
                available_count / total_count * 100,
                2
            )
            if total_count > 0
            else None
        )

        is_candidate_key = (
            total_count >= 2
            and missing_count == 0
            and unique_count == total_count
        )

        if is_candidate_key:

            candidate_keys.append(column)

        if repeated_count > 0:

            repeated_identifier_columns.append(column)

        if missing_count > 0:

            missing_identifier_columns.append(column)

        column_summary[column] = {
            "total_records": total_count,
            "available_count": available_count,
            "missing_count": missing_count,
            "unique_count": unique_count,
            "repeated_occurrences": repeated_count,
            "repeated_group_members": repeated_member_count,
            "uniqueness_rate_percent": uniqueness_rate,
            "completeness_rate_percent": completeness_rate,
            "candidate_unique_key": is_candidate_key
        }

        repeated_mask = (
            values.duplicated(keep=False)
            & ~missing_mask
        )

        for position in range(total_count):

            reasons = []

            if missing_mask.iloc[position]:

                reasons.append("MISSING_IDENTIFIER")

            if repeated_mask.iloc[position]:

                reasons.append("REPEATED_IDENTIFIER")

            if reasons:

                affected_positions.add(position)

                record_issues.setdefault(
                    position, []
                ).append({
                    "column": column,
                    "reasons": reasons
                })

    record_details = [
        {
            "row_position": position,
            "issues": record_issues[position]
        }
        for position in sorted(record_issues)
    ]

    return {
        "total_records": int(len(df)),
        "identifier_column_count": len(identifier_columns),
        "identifier_columns": identifier_columns,
        "candidate_unique_keys": candidate_keys,
        "repeated_identifier_columns": (
            repeated_identifier_columns
        ),
        "missing_identifier_columns": (
            missing_identifier_columns
        ),
        "affected_record_count": len(affected_positions),
        "affected_row_positions": sorted(affected_positions),
        "column_summary": column_summary,
        "record_details": record_details
    }
