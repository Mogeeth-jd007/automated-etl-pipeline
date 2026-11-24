import pandas as pd
import pytest

from universal.transformation_reporter import (
    generate_transformation_summary
)

from universal.conversion_tracker import (
    track_conversion_failures
)


@pytest.fixture
def sample_schema():

    price_report = track_conversion_failures(
        pd.Series(["100", "invalid", "300", None]),
        pd.Series([100, pd.NA, 300, pd.NA]),
        "numeric"
    )

    revenue_report = track_conversion_failures(
        pd.Series(["USD 100", "invalid", "USD 300", None]),
        pd.Series(["100", pd.NA, "300", pd.NA]),
        "currency"
    )

    return {
        "record_id": {
            "data_type": "identifier",
            "null_count": 0
        },
        "price": {
            "data_type": "numeric",
            "null_count": 1,
            "conversion_report": price_report
        },
        "revenue": {
            "data_type": "currency",
            "null_count": 1,
            "conversion_report": revenue_report
        },
        "product_name": {
            "data_type": "text",
            "null_count": 0
        },
        "revenue_currency": {
            "data_type": "text",
            "generated": True,
            "source_column": "revenue",
            "null_count": 2
        }
    }


def test_source_column_count(sample_schema):

    summary = generate_transformation_summary(
        sample_schema
    )

    assert summary["source_columns"] == 4


def test_generated_column_count(sample_schema):

    summary = generate_transformation_summary(
        sample_schema
    )

    assert summary["generated_columns"] == 1

    assert summary["generated_column_names"] == [
        "revenue_currency"
    ]


def test_total_output_columns(sample_schema):

    summary = generate_transformation_summary(
        sample_schema
    )

    assert summary["total_output_columns"] == 5


def test_data_type_distribution(sample_schema):

    summary = generate_transformation_summary(
        sample_schema
    )

    assert summary["data_type_distribution"] == {
        "identifier": 1,
        "numeric": 1,
        "currency": 1,
        "text": 1
    }


def test_tracked_conversion_columns(sample_schema):

    summary = generate_transformation_summary(
        sample_schema
    )

    assert summary["tracked_conversion_columns"] == 2


def test_original_missing_cells(sample_schema):

    summary = generate_transformation_summary(
        sample_schema
    )

    assert summary["original_missing_cells"] == 2


def test_aggregated_conversion_counts(sample_schema):

    summary = generate_transformation_summary(
        sample_schema
    )

    assert summary["attempted_conversions"] == 6

    assert summary["successful_conversions"] == 4

    assert summary["failed_conversions"] == 2


def test_conversion_rates(sample_schema):

    summary = generate_transformation_summary(
        sample_schema
    )

    assert summary["conversion_success_rate_percent"] == 66.67

    assert summary["conversion_failure_rate_percent"] == 33.33


def test_affected_columns(sample_schema):

    summary = generate_transformation_summary(
        sample_schema
    )

    assert summary["affected_column_count"] == 2

    assert set(summary["affected_columns"]) == {
        "price", "revenue"
    }


def test_unique_affected_records(sample_schema):

    summary = generate_transformation_summary(
        sample_schema
    )

    assert summary["affected_record_count"] == 1

    assert summary["affected_row_positions"] == [1]


def test_text_only_schema():

    schema = {
        "product": {
            "data_type": "text",
            "null_count": 1
        }
    }

    summary = generate_transformation_summary(schema)

    assert summary["source_columns"] == 1

    assert summary["tracked_conversion_columns"] == 0

    assert summary["original_missing_cells"] == 1

    assert summary["attempted_conversions"] == 0

    assert summary["conversion_success_rate_percent"] is None

    assert summary["conversion_failure_rate_percent"] is None


def test_empty_schema():

    summary = generate_transformation_summary({})

    assert summary["source_columns"] == 0

    assert summary["generated_columns"] == 0

    assert summary["total_output_columns"] == 0

    assert summary["data_type_distribution"] == {}

    assert summary["attempted_conversions"] == 0

    assert summary["affected_record_count"] == 0

    assert summary["affected_row_positions"] == []

    assert summary["conversion_success_rate_percent"] is None


def test_no_conversion_failures():

    report = track_conversion_failures(
        pd.Series(["100", "200"]),
        pd.Series([100, 200]),
        "numeric"
    )

    schema = {
        "price": {
            "data_type": "numeric",
            "null_count": 0,
            "conversion_report": report
        }
    }

    summary = generate_transformation_summary(schema)

    assert summary["successful_conversions"] == 2

    assert summary["failed_conversions"] == 0

    assert summary["conversion_success_rate_percent"] == 100.0

    assert summary["conversion_failure_rate_percent"] == 0.0

    assert summary["affected_record_count"] == 0

    assert summary["affected_columns"] == []


def test_all_conversions_failed():

    report = track_conversion_failures(
        pd.Series(["invalid", "abc"]),
        pd.Series([pd.NA, pd.NA]),
        "numeric"
    )

    schema = {
        "price": {
            "data_type": "numeric",
            "null_count": 0,
            "conversion_report": report
        }
    }

    summary = generate_transformation_summary(schema)

    assert summary["successful_conversions"] == 0

    assert summary["failed_conversions"] == 2

    assert summary["conversion_success_rate_percent"] == 0.0

    assert summary["conversion_failure_rate_percent"] == 100.0

    assert summary["affected_record_count"] == 2


def test_original_schema_unchanged(sample_schema):

    from copy import deepcopy

    original = deepcopy(sample_schema)

    generate_transformation_summary(sample_schema)

    assert sample_schema == original
