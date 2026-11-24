import json
from pathlib import Path
from datetime import datetime

import pandas as pd
import pytest

from universal.universal_transform import transform_universal
from universal.universal_validate import validate_universal
from universal.report_generator import (
    generate_reports,
    safe_filename
)


@pytest.fixture
def generated_reports(tmp_path, monkeypatch):

    monkeypatch.setattr(
        "universal.report_generator.PROJECT_ROOT",
        tmp_path
    )

    df = pd.DataFrame({
        "Record ID": [
            "001", "002", "003",
            "004", "005", "006"
        ],
        "Price": [
            "45000", "1500", "2500",
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
            "Laptop", "Mouse", "Keyboard",
            "Monitor", "Printer", "Scanner"
        ]
    })

    transformed, schema = transform_universal(df)

    valid, warning, rejected, report = (
        validate_universal(transformed)
    )

    files = generate_reports(
        valid,
        warning,
        rejected,
        report,
        schema,
        "transformation_test"
    )

    with open(
        files["quality_report"],
        encoding="utf-8"
    ) as file:

        saved_report = json.load(file)

    return files, saved_report


@pytest.mark.parametrize(
    "original, expected",
    [
        ("retail_sales", "retail_sales"),
        ("Retail Sales", "Retail_Sales"),
        ("sales@2026", "sales_2026"),
        ("sales---2026", "sales---2026"),
        ("sales___2026", "sales_2026"),
        ("!!!", "dataset"),
        ("", "dataset")
    ]
)
def test_safe_filename(original, expected):

    assert safe_filename(original) == expected


def test_output_file_count(generated_reports):

    files, report = generated_reports

    assert len(files) == 5


@pytest.mark.parametrize(
    "file_key",
    [
        "processed_file",
        "valid_file",
        "warning_file",
        "rejected_file",
        "quality_report"
    ]
)
def test_output_file_exists(
    generated_reports,
    file_key
):

    files, report = generated_reports

    assert Path(files[file_key]).is_file()


def test_json_report_structure(generated_reports):

    files, report = generated_reports

    assert set(report.keys()) == {
        "dataset",
        "generated_at",
        "quality_summary",
        "detected_schema",
        "transformation_summary"
    }


def test_dataset_name(generated_reports):

    files, report = generated_reports

    assert report["dataset"] == "transformation_test"


def test_report_timestamp(generated_reports):

    files, report = generated_reports

    timestamp = datetime.fromisoformat(
        report["generated_at"]
    )

    assert timestamp.tzinfo is not None

    assert timestamp.utcoffset().total_seconds() == 0


def test_validation_summary(generated_reports):

    files, report = generated_reports

    quality = report["quality_summary"]

    assert quality["total_records"] == 6

    assert quality["valid_records"] == 4

    assert quality["warning_records"] == 2

    assert quality["rejected_records"] == 0


def test_schema_metadata(generated_reports):

    files, report = generated_reports

    schema = report["detected_schema"]

    assert len(schema) == 8

    assert schema["record_id"]["data_type"] == "identifier"

    assert schema["price"]["data_type"] == "numeric"

    assert schema["revenue"]["data_type"] == "currency"

    assert schema["discount"]["data_type"] == "percentage"

    assert schema["order_date"]["data_type"] == "date"

    assert schema["is_active"]["data_type"] == "boolean"

    assert schema["product_name"]["data_type"] == "text"


def test_transformation_summary(generated_reports):

    files, report = generated_reports

    summary = report["transformation_summary"]

    assert summary["source_columns"] == 7

    assert summary["generated_columns"] == 1

    assert summary["total_output_columns"] == 8

    assert summary["original_missing_cells"] == 5

    assert summary["attempted_conversions"] == 25

    assert summary["successful_conversions"] == 20

    assert summary["failed_conversions"] == 5

    assert summary["conversion_success_rate_percent"] == 80.0

    assert summary["conversion_failure_rate_percent"] == 20.0


def test_affected_record_tracking(generated_reports):

    files, report = generated_reports

    summary = report["transformation_summary"]

    assert summary["affected_column_count"] == 5

    assert summary["affected_record_count"] == 1

    assert summary["affected_row_positions"] == [4]


def test_column_conversion_metadata(generated_reports):

    files, report = generated_reports

    conversion = report["detected_schema"]["price"][
        "conversion_report"
    ]

    assert conversion["attempted_conversions"] == 5

    assert conversion["successful_conversions"] == 4

    assert conversion["failed_conversions"] == 1

    assert conversion["failed_row_positions"] == [4]


def test_generated_currency_metadata(generated_reports):

    files, report = generated_reports

    schema = report["detected_schema"]

    assert schema["revenue_currency"]["generated"] is True

    assert schema["revenue_currency"]["source_column"] == (
        "revenue"
    )


@pytest.mark.parametrize(
    "file_key, expected_count",
    [
        ("processed_file", 6),
        ("valid_file", 4),
        ("warning_file", 2),
        ("rejected_file", 0)
    ]
)
def test_csv_record_counts(
    generated_reports,
    file_key,
    expected_count
):

    files, report = generated_reports

    df = pd.read_csv(files[file_key])

    assert len(df) == expected_count


def test_processed_identifier_preservation(
    generated_reports
):

    files, report = generated_reports

    df = pd.read_csv(
        files["processed_file"],
        dtype={"record_id": "string"}
    )

    assert df["record_id"].tolist() == [
        "001", "002", "003",
        "004", "005", "006"
    ]


def test_output_directory_isolation(
    generated_reports,
    tmp_path
):

    files, report = generated_reports

    for file_path in files.values():

        assert Path(file_path).is_relative_to(tmp_path)


def test_no_conversion_report(tmp_path, monkeypatch):

    monkeypatch.setattr(
        "universal.report_generator.PROJECT_ROOT",
        tmp_path
    )

    df = pd.DataFrame({
        "product": ["Laptop", "Mouse", "Keyboard"]
    })

    transformed, schema = transform_universal(df)

    valid, warning, rejected, report = (
        validate_universal(transformed)
    )

    files = generate_reports(
        valid,
        warning,
        rejected,
        report,
        schema,
        "text_only"
    )

    with open(
        files["quality_report"],
        encoding="utf-8"
    ) as file:

        saved_report = json.load(file)

    summary = saved_report["transformation_summary"]

    assert summary["attempted_conversions"] == 0

    assert summary["conversion_success_rate_percent"] is None

    assert summary["conversion_failure_rate_percent"] is None
