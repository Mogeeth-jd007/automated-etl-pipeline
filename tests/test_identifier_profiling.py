
import pandas as pd

from src.universal.data_profiler import (
    profile_identifier_column,
    profile_dataset
)


def test_unique_identifier_column():

    series = pd.Series(["C001", "C002", "C003"])

    result = profile_identifier_column(series)

    assert result["total_records"] == 3
    assert result["available_count"] == 3
    assert result["unique_count"] == 3
    assert result["repeated_occurrences"] == 0
    assert result["uniqueness_rate_percent"] == 100.0
    assert result["candidate_unique_key"] is True


def test_repeated_identifiers():

    series = pd.Series(["C001", "C002", "C001", "C003"])

    result = profile_identifier_column(series)

    assert result["unique_count"] == 3
    assert result["repeated_occurrences"] == 1
    assert result["repeated_group_members"] == 2
    assert result["candidate_unique_key"] is False


def test_missing_identifiers():

    series = pd.Series(["C001", None, "C003"])

    result = profile_identifier_column(series)

    assert result["missing_count"] == 1
    assert result["available_count"] == 2
    assert result["completeness_rate_percent"] == 66.67
    assert result["candidate_unique_key"] is False


def test_all_identifiers_missing():

    series = pd.Series([None, None, None])

    result = profile_identifier_column(series)

    assert result["missing_count"] == 3
    assert result["available_count"] == 0
    assert result["unique_count"] == 0
    assert result["uniqueness_rate_percent"] is None
    assert result["candidate_unique_key"] is False


def test_empty_identifier_series():

    series = pd.Series([], dtype="object")

    result = profile_identifier_column(series)

    assert result["total_records"] == 0
    assert result["missing_count"] == 0
    assert result["unique_count"] == 0
    assert result["completeness_rate_percent"] is None


def test_identifier_whitespace():

    series = pd.Series([" C001 ", "C002", "C003"])

    result = profile_identifier_column(series)

    assert result["unique_count"] == 3
    assert result["candidate_unique_key"] is True


def test_identifier_profiling_integrated():

    df = pd.DataFrame({
        "customer_id": ["C001", "C002", "C003"],
        "customer_name": ["Arun", "Meena", "Ravi"],
        "amount": [100, 200, 300]
    })

    result = profile_dataset(df)

    assert "customer_id" in result["identifier_profiles"]

    identifier = result["identifier_profiles"]["customer_id"]

    assert identifier["unique_count"] == 3
    assert identifier["candidate_unique_key"] is True


def test_repeated_identifier_integration():

    df = pd.DataFrame({
        "customer_id": ["C001", "C002", "C001"],
        "amount": [100, 200, 300]
    })

    result = profile_dataset(df)

    identifier = result["identifier_profiles"]["customer_id"]

    assert identifier["repeated_occurrences"] == 1
    assert identifier["candidate_unique_key"] is False


def test_identifier_profiling_preserves_original_dataframe():

    df = pd.DataFrame({
        "customer_id": [" C001 ", "C002", "C003"],
        "amount": [100, 200, 300]
    })

    original = df.copy(deep=True)

    profile_dataset(df)

    pd.testing.assert_frame_equal(df, original)


def test_existing_profiles_are_preserved():

    df = pd.DataFrame({
        "customer_id": ["C001", "C002", "C003"],
        "customer_name": ["Arun", "Meena", "Ravi"],
        "amount": [100, 200, 300]
    })

    result = profile_dataset(df)

    assert "numeric_profiles" in result
    assert "categorical_profiles" in result
    assert "missing_profiles" in result
    assert "identifier_profiles" in result

    assert "amount" in result["numeric_profiles"]
    assert "customer_name" in result["categorical_profiles"]
