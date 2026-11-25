
"""
Configuration management for universal data validation.
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
    Validate validation configuration.

    Missing settings default to enabled to preserve
    existing validation behavior.
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

        unknown_options = set(supplied) - {"enabled"}

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

    return validated
