
"""
Configuration management for universal data validation.

Supports independently configurable validators and
optional date-validation settings.
"""

DEFAULT_VALIDATION_CONFIG = {
    "missing_values": {"enabled": True},
    "duplicates": {"enabled": True},
    "identifiers": {"enabled": True},
    "conversion": {"enabled": True},
    "numeric": {"enabled": True},
    "dates": {"enabled": True},
    "contacts": {"enabled": True}
}


def validate_validation_config(config=None):
    """
    Validate universal validation configuration.

    Missing settings default to enabled to preserve
    existing validation behavior.

    Date-specific options:
        no_future_columns: columns that must not contain
        dates later than the reference date.
    """

    if config is None:
        config = {}

    if not isinstance(config, dict):
        raise ValueError(
            "Universal validation configuration must be a dictionary."
        )

    unknown_keys = (
        set(config) - set(DEFAULT_VALIDATION_CONFIG)
    )

    if unknown_keys:
        raise ValueError(
            f"Unknown validation settings: {sorted(unknown_keys)}"
        )

    validated = {}

    for validator, defaults in DEFAULT_VALIDATION_CONFIG.items():

        supplied = config.get(validator, {})

        if not isinstance(supplied, dict):
            raise ValueError(
                f"Validation setting '{validator}' must be a dictionary."
            )

        allowed_options = {"enabled"}

        if validator == "dates":
            allowed_options.add("no_future_columns")

        unknown_options = set(supplied) - allowed_options

        if unknown_options:
            raise ValueError(
                f"Unknown options for '{validator}': "
                f"{sorted(unknown_options)}"
            )

        enabled = supplied.get(
            "enabled",
            defaults["enabled"]
        )

        if not isinstance(enabled, bool):
            raise ValueError(
                f"'{validator}.enabled' must be a boolean."
            )

        validated[validator] = {
            "enabled": enabled
        }

        # Validate optional date-specific configuration.
        if validator == "dates" and "no_future_columns" in supplied:

            columns = supplied["no_future_columns"]

            if not isinstance(columns, list):
                raise ValueError(
                    "'dates.no_future_columns' must be a list."
                )

            if any(
                not isinstance(column, str) or not column.strip()
                for column in columns
            ):
                raise ValueError(
                    "'dates.no_future_columns' must contain "
                    "non-empty column names."
                )

            if len(columns) != len(set(columns)):
                raise ValueError(
                    "'dates.no_future_columns' cannot contain duplicates."
                )

            validated[validator]["no_future_columns"] = columns.copy()

    return validated
