import pandas as pd
import pytest

from universal.universal_transform import (
    transform_universal
)

from universal.transformation_reporter import (
    generate_transformation_summary
)


@pytest.fixture
def sample_dataset():

    return pd.DataFrame({

        "Record ID": [
            "001", "002", "003",
            "004", "005", "006"
        ],

        "Price": [
            "45,000", "1500", "2500",
            "800", "12,34", "NULL"
        ],

        "Revenue": [
            "USD 100", "USD 200", "USD 300",
            "USD 400", "USD abc", "NULL"
        ],

        "Discount": [
            "10%", "15%", "20%",
            "25%", "abc%", "NULL"
        ],

        "Order Date": [
            "2026-11-24",
            "2026-11-25",
            "2026-11-26",
            "2026-11-27",
            "01/02/2026",
            "NULL"
        ],

        "Is Active": [
            "YES", "NO", "ON",
            "OFF", "maybe", "NULL"
        ],

        "Product Name": [
            "  Laptop  ",
            "Gaming   Mouse",
            "Keyboard",
            "Monitor",
            "Printer",
            "Scanner"
        ]
    })


@pytest.fixture
def transformed_dataset(sample_dataset):

    return transform_universal(sample_dataset)


def test_standardized_column_names(transformed_dataset):

    df, schema = transformed_dataset

    assert df.columns.tolist() == [
        "record_id",
        "price",
        "revenue",
        "discount",
        "order_date",
        "is_active",
        "product_name",
        "revenue_currency"
    ]


def test_detected_schema_types(transformed_dataset):

    df, schema = transformed_dataset

    expected = {
        "record_id": "identifier",
        "price": "numeric",
        "revenue": "currency",
        "discount": "percentage",
        "order_date": "date",
        "is_active": "boolean",
        "product_name": "text",
        "revenue_currency": "text"
    }

    actual = {
        column: details["data_type"]
        for column, details in schema.items()
    }

    assert actual == expected


def test_identifier_preservation(transformed_dataset):

    df, schema = transformed_dataset

    assert df["record_id"].tolist() == [
        "001", "002", "003",
        "004", "005", "006"
    ]


def test_numeric_transformation(transformed_dataset):

    df, schema = transformed_dataset

    assert df["price"].dropna().tolist() == [
        45000, 1500, 2500, 800
    ]

    assert df["price"].isna().sum() == 2


def test_currency_transformation(transformed_dataset):

    df, schema = transformed_dataset

    assert df["revenue"].dropna().tolist() == [
        "100", "200", "300", "400"
    ]

    assert df["revenue_currency"].dropna().tolist() == [
        "USD", "USD", "USD", "USD"
    ]

    assert df["revenue"].isna().sum() == 2

    assert df["revenue_currency"].isna().sum() == 2

    assert schema["revenue"]["storage_type"] == (
        "decimal_string"
    )


def test_generated_currency_schema(transformed_dataset):

    df, schema = transformed_dataset

    details = schema["revenue_currency"]

    assert details["generated"] is True

    assert details["source_column"] == "revenue"

    assert details["non_null_count"] == 4

    assert details["null_count"] == 2


def test_percentage_transformation(transformed_dataset):

    df, schema = transformed_dataset

    assert df["discount"].dropna().tolist() == [
        "0.1", "0.15", "0.2", "0.25"
    ]

    assert df["discount"].isna().sum() == 2

    assert schema["discount"]["unit"] == "fraction"


def test_datetime_transformation(transformed_dataset):

    df, schema = transformed_dataset

    assert df["order_date"].dropna().tolist() == [
        "2026-11-24T00:00:00",
        "2026-11-25T00:00:00",
        "2026-11-26T00:00:00",
        "2026-11-27T00:00:00"
    ]

    assert df["order_date"].isna().sum() == 2


def test_boolean_transformation(transformed_dataset):

    df, schema = transformed_dataset

    assert df["is_active"].dropna().tolist() == [
        True, False, True, False
    ]

    assert df["is_active"].isna().sum() == 2

    assert str(df["is_active"].dtype) == "boolean"

    assert schema["is_active"]["boolean_summary"] == {
        "true_count": 2,
        "false_count": 2,
        "missing_count": 2
    }


def test_text_transformation(transformed_dataset):

    df, schema = transformed_dataset

    assert df["product_name"].tolist() == [
        "Laptop",
        "Gaming Mouse",
        "Keyboard",
        "Monitor",
        "Printer",
        "Scanner"
    ]


@pytest.mark.parametrize(
    "column",
    [
        "price",
        "revenue",
        "discount",
        "order_date",
        "is_active"
    ]
)
def test_column_conversion_tracking(
    transformed_dataset,
    column
):

    df, schema = transformed_dataset

    report = schema[column]["conversion_report"]

    assert report["total_records"] == 6

    assert report["original_missing_count"] == 1

    assert report["attempted_conversions"] == 5

    assert report["successful_conversions"] == 4

    assert report["failed_conversions"] == 1

    assert report["failure_rate_percent"] == 20.0

    assert report["failed_row_positions"] == [4]


def test_dataset_transformation_summary(
    transformed_dataset
):

    df, schema = transformed_dataset

    summary = generate_transformation_summary(schema)

    assert summary["source_columns"] == 7

    assert summary["generated_columns"] == 1

    assert summary["total_output_columns"] == 8

    assert summary["tracked_conversion_columns"] == 5

    assert summary["original_missing_cells"] == 5

    assert summary["attempted_conversions"] == 25

    assert summary["successful_conversions"] == 20

    assert summary["failed_conversions"] == 5

    assert summary["conversion_success_rate_percent"] == 80.0

    assert summary["conversion_failure_rate_percent"] == 20.0

    assert summary["affected_column_count"] == 5

    assert summary["affected_record_count"] == 1

    assert summary["affected_row_positions"] == [4]


def test_record_count_preservation(
    sample_dataset,
    transformed_dataset
):

    df, schema = transformed_dataset

    assert len(df) == len(sample_dataset)


def test_original_dataframe_unchanged(sample_dataset):

    original = sample_dataset.copy(deep=True)

    transform_universal(sample_dataset)

    pd.testing.assert_frame_equal(
        sample_dataset,
        original
    )


def test_currency_column_collision():

    df = pd.DataFrame({
        "revenue": ["USD 100", "USD 200"],
        "revenue_currency": ["original", "original"]
    })

    result, schema = transform_universal(df)

    assert result["revenue_currency"].tolist() == [
        "original", "original"
    ]

    assert result["revenue_currency_2"].tolist() == [
        "USD", "USD"
    ]

    assert schema["revenue"]["currency_column"] == (
        "revenue_currency_2"
    )


def test_binary_numeric_protection():

    df = pd.DataFrame({
        "quantity": ["0", "1", "0", "1"],
        "is_active": ["0", "1", "0", "1"]
    })

    result, schema = transform_universal(df)

    assert schema["quantity"]["data_type"] == "numeric"

    assert schema["is_active"]["data_type"] == "boolean"

    assert result["quantity"].tolist() == [
        0, 1, 0, 1
    ]

    assert result["is_active"].tolist() == [
        False, True, False, True
    ]


def test_index_preservation(sample_dataset):

    sample_dataset.index = [
        10, 20, 30, 40, 50, 60
    ]

    result, schema = transform_universal(sample_dataset)

    assert result.index.equals(sample_dataset.index)


def test_text_only_dataset():

    df = pd.DataFrame({
        "product": ["Laptop", "Mouse", "Keyboard"]
    })

    result, schema = transform_universal(df)

    summary = generate_transformation_summary(schema)

    assert schema["product"]["data_type"] == "text"

    assert summary["attempted_conversions"] == 0

    assert summary["conversion_success_rate_percent"] is None
