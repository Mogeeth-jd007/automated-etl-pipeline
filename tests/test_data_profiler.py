
import pandas as pd
import pytest

from src.universal.data_profiler import profile_dataset


def create_test_dataframe():

    return pd.DataFrame({
        "Customer Name": [
            "Arun",
            "Meena",
            "Arun",
            "Ravi"
        ],
        "Age": [
            25,
            30,
            25,
            None
        ],
        "City": [
            "Chennai",
            "Madurai",
            "Chennai",
            None
        ]
    })


def test_dataset_summary_statistics():

    df = create_test_dataframe()

    result = profile_dataset(df)

    summary = result["dataset_summary"]

    assert summary["total_records"] == 4

    assert summary["total_columns"] == 3

    assert summary["total_cells"] == 12

    assert summary["missing_cells"] == 2

    assert summary["completeness_score"] == 83.33

    assert summary["duplicate_records"] == 1

    assert summary["memory_usage_bytes"] > 0


def test_column_names_are_standardized():

    df = create_test_dataframe()

    result = profile_dataset(df)

    profiles = result["column_profiles"]

    assert "customer_name" in profiles

    assert "age" in profiles

    assert "city" in profiles


def test_column_statistics():

    df = create_test_dataframe()

    result = profile_dataset(df)

    profiles = result["column_profiles"]

    assert profiles["customer_name"]["non_null_count"] == 4

    assert profiles["customer_name"]["null_count"] == 0

    assert profiles["customer_name"]["unique_count"] == 3

    assert profiles["customer_name"]["missing_percentage"] == 0.0

    assert profiles["age"]["non_null_count"] == 3

    assert profiles["age"]["null_count"] == 1

    assert profiles["age"]["unique_count"] == 2

    assert profiles["age"]["missing_percentage"] == 25.0

    assert profiles["city"]["null_count"] == 1

    assert profiles["city"]["missing_percentage"] == 25.0


def test_uniqueness_percentage():

    df = create_test_dataframe()

    result = profile_dataset(df)

    profiles = result["column_profiles"]

    assert (
        profiles["customer_name"]["uniqueness_percentage"]
        == 75.0
    )

    assert (
        profiles["age"]["uniqueness_percentage"]
        == 66.67
    )


def test_profile_contains_data_types_and_samples():

    df = create_test_dataframe()

    result = profile_dataset(df)

    profiles = result["column_profiles"]

    assert profiles["age"]["data_type"] == "numeric"

    assert profiles["customer_name"]["data_type"] == "text"

    assert profiles["age"]["sample_values"] == [
        "25.0",
        "30.0",
        "25.0"
    ]


def test_original_dataframe_is_not_modified():

    df = create_test_dataframe()

    original = df.copy(deep=True)

    profile_dataset(df)

    pd.testing.assert_frame_equal(df, original)


def test_empty_dataframe():

    df = pd.DataFrame({
        "customer_id": pd.Series(dtype="object"),
        "amount": pd.Series(dtype="float64")
    })

    result = profile_dataset(df)

    summary = result["dataset_summary"]

    assert summary["total_records"] == 0

    assert summary["total_columns"] == 2

    assert summary["total_cells"] == 0

    assert summary["missing_cells"] == 0

    assert summary["completeness_score"] is None

    assert summary["duplicate_records"] == 0

    assert (
        result["column_profiles"]["amount"]["missing_percentage"]
        is None
    )

    assert (
        result["column_profiles"]["amount"]["uniqueness_percentage"]
        is None
    )


def test_dataframe_without_columns():

    df = pd.DataFrame()

    result = profile_dataset(df)

    assert result["dataset_summary"]["total_records"] == 0

    assert result["dataset_summary"]["total_columns"] == 0

    assert result["dataset_summary"]["total_cells"] == 0

    assert result["column_profiles"] == {}


def test_invalid_input_type():

    with pytest.raises(TypeError):

        profile_dataset([
            {"name": "Arun"}
        ])


def test_duplicate_column_names():

    df = pd.DataFrame(
        [[1, 2]],
        columns=["amount", "amount"]
    )

    with pytest.raises(ValueError):

        profile_dataset(df)
