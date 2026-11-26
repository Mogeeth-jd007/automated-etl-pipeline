
import pandas as pd
import pytest

from src.universal.data_profiler import (
    profile_contact_column,
    profile_dataset
)


def test_valid_email_profiling():

    series = pd.Series([
        "arun@example.com",
        "meena@example.com",
        "ravi@example.com"
    ])

    result = profile_contact_column(series, "email")

    assert result["valid_count"] == 3
    assert result["invalid_count"] == 0
    assert result["missing_count"] == 0
    assert result["validity_rate_percent"] == 100.0


def test_invalid_email_profiling():

    series = pd.Series([
        "invalid-email",
        "another-invalid",
        "valid@example.com"
    ])

    result = profile_contact_column(series, "email")

    assert result["valid_count"] == 1
    assert result["invalid_count"] == 2
    assert result["validity_rate_percent"] == 33.33
    assert len(result["invalid_examples"]) == 2


def test_missing_email_values():

    series = pd.Series([
        "arun@example.com",
        None,
        "",
        "meena@example.com"
    ])

    result = profile_contact_column(series, "email")

    assert result["valid_count"] == 2
    assert result["missing_count"] == 2
    assert result["invalid_count"] == 0
    assert result["validity_rate_percent"] == 100.0


def test_valid_phone_profiling():

    series = pd.Series([
        "9876543210",
        "+919876543210",
        "987-654-3210"
    ])

    result = profile_contact_column(series, "phone")

    assert result["valid_count"] == 3
    assert result["invalid_count"] == 0
    assert result["validity_rate_percent"] == 100.0


def test_invalid_phone_profiling():

    series = pd.Series([
        "123",
        "abc123",
        "9876543210"
    ])

    result = profile_contact_column(series, "phone")

    assert result["valid_count"] == 1
    assert result["invalid_count"] == 2


def test_missing_phone_values():

    series = pd.Series([
        "9876543210",
        None,
        "",
        "9876543211"
    ])

    result = profile_contact_column(series, "phone")

    assert result["valid_count"] == 2
    assert result["missing_count"] == 2
    assert result["invalid_count"] == 0


def test_all_contact_values_invalid():

    series = pd.Series([
        "invalid-one",
        "invalid-two"
    ])

    result = profile_contact_column(series, "email")

    assert result["valid_count"] == 0
    assert result["invalid_count"] == 2
    assert result["validity_rate_percent"] == 0.0


def test_all_contact_values_missing():

    series = pd.Series([
        None,
        "",
        "   "
    ])

    result = profile_contact_column(series, "email")

    assert result["missing_count"] == 3
    assert result["available_count"] == 0
    assert result["validity_rate_percent"] is None


def test_empty_contact_series():

    series = pd.Series([], dtype="object")

    result = profile_contact_column(series, "email")

    assert result["total_records"] == 0
    assert result["missing_count"] == 0
    assert result["validity_rate_percent"] is None


def test_invalid_contact_type():

    series = pd.Series(["value"])

    with pytest.raises(ValueError):

        profile_contact_column(series, "address")


def test_contact_examples_do_not_expose_values():

    series = pd.Series(
        ["invalid-email"],
        index=[100]
    )

    result = profile_contact_column(series, "email")

    assert result["invalid_examples"] == [
        {"row_position": 0}
    ]


def test_contact_profiling_integrated():

    df = pd.DataFrame({
        "customer_id": ["C001", "C002", "C003"],
        "email": [
            "arun@example.com",
            "invalid-email",
            None
        ],
        "phone_number": [
            "9876543210",
            "123",
            "9876543211"
        ],
        "amount": [100, 200, 300]
    })

    result = profile_dataset(df)

    assert "email" in result["contact_profiles"]

    assert "phone_number" in result["contact_profiles"]

    email = result["contact_profiles"]["email"]

    assert email["valid_count"] == 1
    assert email["invalid_count"] == 1
    assert email["missing_count"] == 1

    phone = result["contact_profiles"]["phone_number"]

    assert phone["valid_count"] == 2
    assert phone["invalid_count"] == 1


def test_contact_profiling_preserves_original_dataframe():

    df = pd.DataFrame({
        "email": [
            "arun@example.com",
            "invalid-email"
        ],
        "phone_number": [
            "9876543210",
            "123"
        ]
    })

    original = df.copy(deep=True)

    profile_dataset(df)

    pd.testing.assert_frame_equal(df, original)


def test_existing_profiles_are_preserved():

    df = pd.DataFrame({
        "customer_id": ["C001", "C002", "C003"],
        "customer_name": ["Arun", "Meena", "Ravi"],
        "email": [
            "arun@example.com",
            "meena@example.com",
            "ravi@example.com"
        ],
        "amount": [100, 200, 300]
    })

    result = profile_dataset(df)

    assert "identifier_profiles" in result
    assert "numeric_profiles" in result
    assert "categorical_profiles" in result
    assert "missing_profiles" in result
    assert "contact_profiles" in result
