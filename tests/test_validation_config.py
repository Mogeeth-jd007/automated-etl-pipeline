
import pytest

from universal.validation_config import (
    DEFAULT_VALIDATION_CONFIG,
    validate_validation_config
)


def test_default_configuration_enables_all_validators():

    result = validate_validation_config()

    assert result == DEFAULT_VALIDATION_CONFIG


def test_existing_configuration_is_preserved():

    result = validate_validation_config({
        "missing_values": {"enabled": True},
        "duplicates": {"enabled": True}
    })

    assert result["missing_values"]["enabled"] is True
    assert result["duplicates"]["enabled"] is True
    assert result["numeric"]["enabled"] is True


def test_validator_can_be_disabled():

    result = validate_validation_config({
        "contacts": {"enabled": False}
    })

    assert result["contacts"]["enabled"] is False
    assert result["dates"]["enabled"] is True


def test_all_validators_can_be_disabled():

    config = {
        name: {"enabled": False}
        for name in DEFAULT_VALIDATION_CONFIG
    }

    result = validate_validation_config(config)

    assert all(
        not settings["enabled"]
        for settings in result.values()
    )


def test_invalid_configuration_type():

    with pytest.raises(ValueError):
        validate_validation_config("invalid")


def test_unknown_validator_is_rejected():

    with pytest.raises(ValueError, match="Unknown validation settings"):

        validate_validation_config({
            "unknown_validator": {"enabled": True}
        })


def test_validator_configuration_must_be_dictionary():

    with pytest.raises(ValueError, match="must be a dictionary"):

        validate_validation_config({
            "numeric": True
        })


def test_non_boolean_enabled_value_is_rejected():

    with pytest.raises(ValueError, match="must be a boolean"):

        validate_validation_config({
            "numeric": {"enabled": "yes"}
        })


def test_unknown_validator_option_is_rejected():

    with pytest.raises(ValueError, match="Unknown options"):

        validate_validation_config({
            "numeric": {
                "enabled": True,
                "unexpected": False
            }
        })


def test_partial_configuration_preserves_defaults():

    result = validate_validation_config({
        "numeric": {"enabled": False}
    })

    assert result["numeric"]["enabled"] is False

    for name in result:
        if name != "numeric":
            assert result[name]["enabled"] is True


def test_explicit_null_enabled_value_is_rejected():

    with pytest.raises(ValueError, match="must be a boolean"):

        validate_validation_config({
            "contacts": {"enabled": None}
        })
