
import pandas as pd
import pytest

from src.universal.data_profiler import (
    profile_missing_values,
    profile_dataset
)


def create_test_dataframe():

    return pd.DataFrame({
        "customer": [
            "Arun",
            "Meena",
            "Ravi",
            "Divya",
            "Kiran"
        ],
        "age": [
            25,
            None,
            35,
            None,
            40
        ],
        "city": [
            "Chennai",
            "Chennai",
            None,
            "Madurai",
            "Chennai"
        ],
        "salary": [
            30000,
            40000,
            None,
            35000,
            None
        ]
    })


def test_column_missing_statistics():

    result = profile_missing_values(
        create_test_dataframe()
    )

    columns = result["column_summary"]

    assert columns["customer"]["missing_count"] == 0

    assert columns["age"]["missing_count"] == 2

    assert columns["age"]["missing_percentage"] == 40.0

    assert columns["city"]["missing_count"] == 1

    assert columns["city"]["missing_percentage"] == 20.0

    assert columns["salary"]["missing_count"] == 2

    assert columns["salary"]["missing_percentage"] == 40.0


def test_dataset_completeness():

    result = profile_missing_values(
        create_test_dataframe()
    )

    assert result["total_records"] == 5

    assert result["total_columns"] == 4

    assert result["total_cells"] == 20

    assert result["missing_cells"] == 5

    assert result["non_missing_cells"] == 15

    assert result["completeness_score"] == 75.0


def test_missing_value_row_count():

    result = profile_missing_values(
        create_test_dataframe()
    )

    assert result["missing_value_rows"] == 4


def test_empty_rows():

    df = pd.DataFrame({
        "name": ["Arun", None, None],
        "age": [25, None, None]
    })

    result = profile_missing_values(df)

    assert result["empty_rows"] == 2


def test_empty_columns():

    df = pd.DataFrame({
        "name": ["Arun", "Meena"],
        "age": [None, None],
        "city": ["Chennai", "Madurai"]
    })

    result = profile_missing_values(df)

    assert result["empty_columns"] == 1

    assert result["empty_column_names"] == ["age"]


def test_blank_strings_are_missing():

    df = pd.DataFrame({
        "name": ["Arun", "   ", "Meena"]
    })

    result = profile_missing_values(df)

    assert result["missing_cells"] == 1

    assert (
        result["column_summary"]["name"]["missing_percentage"]
        == 33.33
    )


def test_missing_markers_are_normalized():

    df = pd.DataFrame({
        "value": [
            "Arun",
            "NULL",
            "N/A",
            "None"
        ]
    })

    result = profile_missing_values(df)

    assert result["missing_cells"] == 3


def test_identifier_values_are_preserved():

    df = pd.DataFrame({
        "customer_id": [
            "001",
            "NA",
            "NULL",
            ""
        ]
    })

    result = profile_missing_values(df)

    assert result["missing_cells"] == 1


def test_record_missing_details():

    df = pd.DataFrame({
        "name": ["Arun", None],
        "age": [25, None],
        "city": ["Chennai", "Madurai"]
    })

    result = profile_missing_values(df)

    assert len(result["record_details"]) == 1

    detail = result["record_details"][0]

    assert detail["row_position"] == 1

    assert detail["missing_columns"] == [
        "name",
        "age"
    ]

    assert detail["is_empty_record"] is False


def test_original_dataframe_unchanged():

    df = pd.DataFrame({
        "name": ["Arun", " NULL "],
        "age": [25, None]
    })

    original = df.copy(deep=True)

    profile_missing_values(df)

    pd.testing.assert_frame_equal(df, original)


def test_empty_dataframe():

    df = pd.DataFrame({
        "name": pd.Series(dtype="object"),
        "age": pd.Series(dtype="float64")
    })

    result = profile_missing_values(df)

    assert result["total_records"] == 0

    assert result["total_cells"] == 0

    assert result["missing_cells"] == 0

    assert result["completeness_score"] is None

    assert result["empty_rows"] == 0


def test_invalid_input():

    with pytest.raises(TypeError):

        profile_missing_values([
            {"name": "Arun"}
        ])


def test_duplicate_columns():

    df = pd.DataFrame(
        [[1, 2]],
        columns=["age", "age"]
    )

    with pytest.raises(ValueError):

        profile_missing_values(df)


def test_missing_profiles_integrated():

    df = create_test_dataframe()

    result = profile_dataset(df)

    assert "missing_profiles" in result

    assert (
        result["missing_profiles"]["completeness_score"]
        == 75.0
    )

    assert "numeric_profiles" in result

    assert "categorical_profiles" in result


def test_existing_numeric_and_categorical_profiles_preserved():

    df = pd.DataFrame({
        "customer": ["Arun", "Meena", "Ravi"],
        "amount": [100, 200, 300]
    })

    result = profile_dataset(df)

    assert "customer" in result["categorical_profiles"]

    assert "amount" in result["numeric_profiles"]

    assert "missing_profiles" in result
