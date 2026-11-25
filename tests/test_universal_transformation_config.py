
import pandas as pd
import pytest

from universal.universal_transform import (
    transform_universal,
    validate_transformation_config
)


def test_default_configuration():

    settings = validate_transformation_config()

    assert all(settings.values())
    assert len(settings) == 9


def test_invalid_configuration_type():

    with pytest.raises(ValueError):

        validate_transformation_config("invalid")


def test_unknown_configuration_key():

    with pytest.raises(ValueError, match="Unknown transformation"):

        validate_transformation_config({
            "unknown_option": True
        })


def test_non_boolean_setting():

    with pytest.raises(ValueError, match="must be a boolean"):

        validate_transformation_config({
            "clean_text": "yes"
        })


def test_column_standardization_can_be_disabled():

    df = pd.DataFrame({
        "Product Name": ["Laptop", "Mouse"]
    })

    result, schema = transform_universal(
        df,
        config={
            "standardize_columns": False
        }
    )

    assert "Product Name" in result.columns
    assert "Product Name" in schema


def test_text_cleaning_can_be_disabled():

    df = pd.DataFrame({
        "Product": ["  Laptop  ", "  Gaming Mouse  "]
    })

    result, schema = transform_universal(
        df,
        config={
            "clean_text": False,
            "auto_convert_types": False
        }
    )

    assert result["product"].tolist() == [
        "  Laptop  ",
        "  Gaming Mouse  "
    ]


def test_missing_value_normalization_can_be_disabled():

    df = pd.DataFrame({
        "Product": ["Laptop", "NULL", "N/A"]
    })

    result, schema = transform_universal(
        df,
        config={
            "normalize_missing_values": False
        }
    )

    assert result["product"].iloc[1] == "NULL"
    assert result["product"].iloc[2] == "N/A"


def test_automatic_type_conversion_can_be_disabled():

    df = pd.DataFrame({
        "Price": ["100", "200", "300"]
    })

    result, schema = transform_universal(
        df,
        config={
            "auto_convert_types": False
        }
    )

    assert result["price"].tolist() == [
        "100", "200", "300"
    ]

    assert schema["price"]["data_type"] == "numeric"


def test_currency_detection_can_be_disabled():

    df = pd.DataFrame({
        "Revenue": ["USD 100", "USD 200", "USD 300"]
    })

    result, schema = transform_universal(
        df,
        config={
            "detect_currency": False
        }
    )

    assert schema["revenue"]["data_type"] != "currency"
    assert "revenue_currency" not in result.columns


def test_percentage_detection_can_be_disabled():

    df = pd.DataFrame({
        "Discount": ["10%", "20%", "30%"]
    })

    result, schema = transform_universal(
        df,
        config={
            "detect_percentage": False
        }
    )

    assert schema["discount"]["data_type"] != "percentage"


def test_date_detection_can_be_disabled():

    df = pd.DataFrame({
        "Order Date": [
            "2026-01-01",
            "2026-01-02",
            "2026-01-03"
        ]
    })

    result, schema = transform_universal(
        df,
        config={
            "detect_dates": False
        }
    )

    assert schema["order_date"]["data_type"] != "date"


def test_boolean_detection_can_be_disabled():

    df = pd.DataFrame({
        "Is Active": ["YES", "NO", "YES"]
    })

    result, schema = transform_universal(
        df,
        config={
            "detect_booleans": False
        }
    )

    assert schema["is_active"]["data_type"] == "text"


def test_conversion_tracking_can_be_disabled():

    df = pd.DataFrame({
        "Price": ["100", "200", "invalid"]
    })

    result, schema = transform_universal(
        df,
        config={
            "track_conversion_failures": False
        }
    )

    assert "conversion_report" not in schema["price"]


def test_original_dataframe_is_unchanged():

    df = pd.DataFrame({
        "Product Name": ["  Laptop  "],
        "Price": ["100"]
    })

    original = df.copy(deep=True)

    transform_universal(df)

    pd.testing.assert_frame_equal(df, original)
