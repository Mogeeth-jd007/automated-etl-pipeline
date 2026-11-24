
import pandas as pd

from universal.schema_detector import (
    detect_schema,
    infer_column_type,
    is_identifier_column
)

from universal.universal_transform import transform_universal


def test_identifier_detection():
    """Check recognition of common identifier columns."""

    identifiers = [
        "sku",
        "product_code",
        "transaction_reference",
        "customer_id",
        "serial_number"
    ]

    for column in identifiers:
        assert is_identifier_column(column)


def test_identifier_values_preserve_leading_zeros():
    """Identifiers must retain leading zeros after transformation."""

    df = pd.DataFrame({
        "SKU": ["001245", "001246"],
        "Product Code": ["000100", "000200"]
    })

    transformed, schema = transform_universal(df)

    assert transformed["sku"].tolist() == ["001245", "001246"]
    assert transformed["product_code"].tolist() == ["000100", "000200"]

    assert schema["sku"]["data_type"] == "identifier"
    assert schema["product_code"]["data_type"] == "identifier"


def test_comma_formatted_numeric_detection():
    """Numbers containing thousands separators should be numeric."""

    values = pd.Series(["25,000", "30,000", "45,000"])

    result = infer_column_type("salary", values)

    assert result == "numeric"


def test_comma_formatted_numeric_transformation():
    """Comma-formatted numeric values should become actual numbers."""

    df = pd.DataFrame({
        "Salary": ["25,000", "30,000", "45,000"]
    })

    transformed, schema = transform_universal(df)

    assert transformed["salary"].tolist() == [25000, 30000, 45000]
    assert schema["salary"]["data_type"] == "numeric"

    assert pd.api.types.is_numeric_dtype(transformed["salary"])


def test_duplicate_column_names():
    """Standardized duplicate names should become unique."""

    df = pd.DataFrame(
        [["Pen", "Pencil"]],
        columns=["Product Name", "product-name"]
    )

    transformed, schema = detect_schema(df)

    assert list(transformed.columns) == [
        "product_name",
        "product_name_2"
    ]

    assert len(schema) == 2


def test_empty_column_names():
    """Empty column names should receive fallback names."""

    df = pd.DataFrame(
        [["A", "B"]],
        columns=["", "   "]
    )

    transformed, schema = detect_schema(df)

    assert list(transformed.columns) == [
        "column_1",
        "column_2"
    ]

    assert len(schema) == 2
