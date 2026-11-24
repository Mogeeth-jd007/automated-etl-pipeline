import re


EMAIL_COLUMN_NAMES = {
    "email",
    "e_mail",
    "email_address",
    "e_mail_address",
    "email_id",
    "mail_id"
}


PHONE_COLUMN_NAMES = {
    "phone",
    "phone_number",
    "phone_no",
    "mobile",
    "mobile_number",
    "mobile_no",
    "telephone",
    "telephone_number",
    "telephone_no",
    "tel",
    "tel_number",
    "cell_phone",
    "cell_number",
    "contact_number",
    "contact_no",
    "contact_phone",
    "whatsapp",
    "whatsapp_number"
}


def normalize_contact_column_name(column_name):
    """Normalize a column name for contact detection."""

    name = str(column_name).strip().lower()

    name = re.sub(
        r"[^a-z0-9]+",
        "_",
        name
    )

    return name.strip("_")


def matches_contact_name(name, supported_names):
    """Match exact names and prefixed contact names."""

    return (
        name in supported_names
        or any(
            name.endswith("_" + supported_name)
            for supported_name in supported_names
        )
    )


def is_email_column(column_name):
    """Identify email-related columns."""

    name = normalize_contact_column_name(
        column_name
    )

    return matches_contact_name(
        name,
        EMAIL_COLUMN_NAMES
    )


def is_phone_column(column_name):
    """Identify phone-related columns."""

    name = normalize_contact_column_name(
        column_name
    )

    return matches_contact_name(
        name,
        PHONE_COLUMN_NAMES
    )


def detect_contact_type(column_name):
    """Return the detected contact type, if available."""

    if is_email_column(column_name):

        return "email"

    if is_phone_column(column_name):

        return "phone"

    return None
