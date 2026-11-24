import pandas as pd


def validate_duplicates(
    df,
    key_columns=None,
    excluded_columns=None
):
    """
    Detect exact duplicates and explicitly configured
    duplicate keys without modifying the input data.
    """

    key_columns = list(key_columns or [])
    excluded_columns = set(excluded_columns or [])

    unknown_columns = set(key_columns) - set(df.columns)

    if unknown_columns:
        raise ValueError(
            f"Key columns not found: {sorted(unknown_columns)}"
        )

    if set(key_columns) & excluded_columns:
        raise ValueError(
            "Key columns cannot also be excluded."
        )

    source_columns = [
        column
        for column in df.columns
        if column not in excluded_columns
    ]

    if not source_columns:
        raise ValueError(
            "No source columns available for duplicate detection."
        )

    source = df[source_columns].copy()

    # Detect exact duplicates, retaining the first record.
    exact_duplicates = source.duplicated(keep="first")

    # Identify all members of exact duplicate groups.
    exact_duplicate_members = source.duplicated(keep=False)

    key_duplicates = pd.Series(
        False,
        index=df.index,
        dtype=bool
    )

    key_duplicate_members = key_duplicates.copy()

    if key_columns:

        keys = source[key_columns]

        # Exclude incomplete keys from uniqueness checks.
        complete_keys = keys.notna().all(axis=1)

        for column in key_columns:

            blank_values = (
                keys[column]
                .astype("string")
                .str.strip()
                .eq("")
                .fillna(False)
            )

            complete_keys = complete_keys & ~blank_values

        eligible_positions = [
            position
            for position, complete in enumerate(complete_keys)
            if complete
        ]

        eligible_keys = keys.iloc[eligible_positions]

        duplicate_flags = eligible_keys.duplicated(
            keep="first"
        )

        member_flags = eligible_keys.duplicated(
            keep=False
        )

        key_duplicates.iloc[eligible_positions] = (
            duplicate_flags.to_numpy()
        )

        key_duplicate_members.iloc[eligible_positions] = (
            member_flags.to_numpy()
        )

    # Avoid counting the same rejected record twice.
    rejected_rows = exact_duplicates | key_duplicates

    additional_key_duplicates = (
        key_duplicates & ~exact_duplicates
    )

    record_details = []

    for position in range(len(df)):

        reasons = []

        if exact_duplicates.iloc[position]:

            reasons.append("EXACT_DUPLICATE")

        if key_duplicates.iloc[position]:

            reasons.append("DUPLICATE_KEY")

        if reasons:

            record_details.append({
                "row_position": position,
                "reasons": reasons
            })

    duplicate_count = int(rejected_rows.sum())

    duplicate_rate = (
        round(duplicate_count / len(df) * 100, 2)
        if len(df) > 0
        else None
    )

    return {
        "exact_duplicates": exact_duplicates,
        "exact_duplicate_members": exact_duplicate_members,
        "key_duplicates": key_duplicates,
        "key_duplicate_members": key_duplicate_members,
        "rejected_rows": rejected_rows,
        "report": {
            "total_records": int(len(df)),
            "exact_duplicate_rows": int(
                exact_duplicates.sum()
            ),
            "exact_duplicate_group_members": int(
                exact_duplicate_members.sum()
            ),
            "key_duplicate_rows": int(
                key_duplicates.sum()
            ),
            "key_duplicate_group_members": int(
                key_duplicate_members.sum()
            ),
            "additional_key_duplicate_rows": int(
                additional_key_duplicates.sum()
            ),
            "total_duplicate_rows": duplicate_count,
            "duplicate_rate_percent": duplicate_rate,
            "key_columns": key_columns,
            "record_details": record_details
        }
    }
