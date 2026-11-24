import re

import pandas as pd

from .contact_detector import detect_contact_type


EMAIL_LOCAL_PATTERN = re.compile(
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
)

DOMAIN_LABEL_PATTERN = re.compile(
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
)

PHONE_PATTERN = re.compile(
    r"\+?[0-9(][0-9() .-]*[0-9)]"
)


def is_valid_email(value):
    """Check common email address syntax."""

    if pd.isna(value):
        return False

    text = str(value).strip()

    if len(text) > 254:
        return False

    if text.count("@") != 1:
        return False

    local, domain = text.split("@")

    if not local or not domain:
        return False

    if len(local) > 64:
        return False

    if not EMAIL_LOCAL_PATTERN.fullmatch(local):
        return False

    if (
        local.startswith(".")
        or local.endswith(".")
        or ".." in local
    ):
        return False

    labels = domain.split(".")

    if len(labels) < 2:
        return False

    if not all(
        DOMAIN_LABEL_PATTERN.fullmatch(label)
        for label in labels
    ):
        return False

    if not re.fullmatch(
        r"[A-Za-z]{2,63}",
        labels[-1]
    ):
        return False

    return True


def is_valid_phone(value):
    """Check general phone-number format plausibility."""

    if pd.isna(value):
        return False

    text = str(value).strip()

    if not PHONE_PATTERN.fullmatch(text):
        return False

    # Validate parentheses.

    if text.count("(") != text.count(")"):
        return False

    if text.count("(") > 1:
        return False

    if "(" in text:

        if not re.search(
            r"\([0-9]+\)",
            text
        ):
            return False

    # Reject repeated punctuation separators.

    if re.search(r"[.-]{2,}", text):
        return False

    digits = re.sub(
        r"[^0-9]",
        "",
        text
    )

    # General plausibility, not country-specific validation.

    if not 7 <= len(digits) <= 15:
        return False

    if text.startswith("+"):

        if digits.startswith("0"):
            return False

    return True


def validate_contacts(
    df,
    schema=None,
    required_columns=None,
    excluded_columns=None,
    contact_columns=None
):
    """
    Validate email and phone columns without modifying
    the original contact information.
    """

    schema = schema or {}

    required_columns = set(
        required_columns or []
    )

    excluded_columns = set(
        excluded_columns or []
    )

    contact_columns = contact_columns or {}

    excluded_columns.update(
        column
        for column, details in schema.items()
        if details.get("generated", False)
    )

    # STEP 1: Validate configuration.

    unknown_required = (
        required_columns - set(df.columns)
    )

    if unknown_required:

        raise ValueError(
            "Required columns not found: "
            f"{sorted(unknown_required)}"
        )

    if required_columns & excluded_columns:

        raise ValueError(
            "Required columns cannot be excluded."
        )

    for column, contact_type in contact_columns.items():

        if column not in df.columns:

            raise ValueError(
                f"Contact column not found: {column}"
            )

        if column in excluded_columns:

            raise ValueError(
                f"Contact column is excluded: {column}"
            )

        if contact_type not in {"email", "phone"}:

            raise ValueError(
                f"Unsupported contact type: {contact_type}"
            )

    # STEP 2: Detect eligible contact columns.

    detected_columns = {}

    for column in df.columns:

        if column in excluded_columns:
            continue

        contact_type = contact_columns.get(
            column,
            detect_contact_type(column)
        )

        if contact_type is not None:

            detected_columns[column] = contact_type

    # STEP 3: Initialize validation masks.

    invalid_email_rows = pd.Series(
        False,
        index=df.index,
        dtype=bool
    )

    invalid_phone_rows = invalid_email_rows.copy()

    warning_rows = invalid_email_rows.copy()

    rejected_rows = invalid_email_rows.copy()

    column_summary = {}

    record_issues = {}

    total_invalid_emails = 0

    total_invalid_phones = 0

    # STEP 4: Validate contact values.

    for column, contact_type in detected_columns.items():

        missing_count = 0

        valid_count = 0

        invalid_count = 0

        for position, value in enumerate(df[column]):

            if pd.isna(value) or not str(value).strip():

                missing_count += 1

                continue

            if contact_type == "email":

                valid = is_valid_email(value)

                reason = "INVALID_EMAIL"

            else:

                valid = is_valid_phone(value)

                reason = "INVALID_PHONE"

            if valid:

                valid_count += 1

                continue

            invalid_count += 1

            if contact_type == "email":

                invalid_email_rows.iloc[position] = True

                total_invalid_emails += 1

            else:

                invalid_phone_rows.iloc[position] = True

                total_invalid_phones += 1

            if column in required_columns:

                severity = "REJECTED"

                rejected_rows.iloc[position] = True

            else:

                severity = "WARNING"

                warning_rows.iloc[position] = True

            record_issues.setdefault(
                position,
                []
            ).append({
                "column": column,
                "contact_type": contact_type,
                "reason": reason,
                "severity": severity
            })

        available_count = (
            valid_count + invalid_count
        )

        validity_rate = (
            round(
                valid_count / available_count * 100,
                2
            )
            if available_count
            else None
        )

        column_summary[column] = {
            "contact_type": contact_type,
            "total_records": int(len(df)),
            "missing_count": missing_count,
            "available_count": available_count,
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "validity_rate_percent": validity_rate,
            "required": column in required_columns
        }

    # STEP 5: Apply rejection priority.

    warning_rows = warning_rows & ~rejected_rows

    affected_rows = warning_rows | rejected_rows

    # STEP 6: Generate detailed report.

    return {
        "invalid_email_rows": invalid_email_rows,
        "invalid_phone_rows": invalid_phone_rows,
        "warning_rows": warning_rows,
        "rejected_rows": rejected_rows,
        "report": {
            "total_records": int(len(df)),
            "contact_column_count": len(
                detected_columns
            ),
            "email_columns": [
                column
                for column, contact_type
                in detected_columns.items()
                if contact_type == "email"
            ],
            "phone_columns": [
                column
                for column, contact_type
                in detected_columns.items()
                if contact_type == "phone"
            ],
            "total_invalid_emails": total_invalid_emails,
            "total_invalid_phones": total_invalid_phones,
            "invalid_email_record_count": int(
                invalid_email_rows.sum()
            ),
            "invalid_phone_record_count": int(
                invalid_phone_rows.sum()
            ),
            "affected_record_count": int(
                affected_rows.sum()
            ),
            "warning_rows": int(
                warning_rows.sum()
            ),
            "rejected_rows": int(
                rejected_rows.sum()
            ),
            "affected_row_positions": sorted(
                record_issues
            ),
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
