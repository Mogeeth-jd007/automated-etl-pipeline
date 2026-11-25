
import pandas as pd

from universal.neutral_validation import (
    build_neutral_validation_results
)


def create_dataframe():
    return pd.DataFrame(
        {
            "customer_id": ["001", "002", "003"],
            "email": [
                "invalid-email",
                "test@example.com",
                "another-invalid"
            ],
            "amount": [100, 200, 300]
        },
        index=[10, 20, 30]
    )


def test_neutral_results_contain_all_validators():

    df = create_dataframe()

    results = build_neutral_validation_results(df)

    assert set(results) == {
        "missing_values",
        "duplicates",
        "identifiers",
        "conversion",
        "numeric",
        "dates",
        "contacts"
    }



def test_neutral_boolean_series_preserve_dataframe_index():

    df = create_dataframe()

    results = build_neutral_validation_results(df)

    for validator_name, result in results.items():

        for key, value in result.items():

            if isinstance(value, pd.Series):

                assert value.index.equals(df.index)

                if key == "missing_counts":
                    assert pd.api.types.is_integer_dtype(
                        value.dtype
                    )
                else:
                    assert value.dtype == bool
                    assert not value.any()



def test_neutral_missing_values_result():

    df = create_dataframe()

    result = build_neutral_validation_results(
        df
    )["missing_values"]

    assert result["report"]["missing_cells"] == 0
    assert result["report"]["record_details"] == []


def test_neutral_duplicate_result():

    df = create_dataframe()

    result = build_neutral_validation_results(
        df
    )["duplicates"]

    assert result["report"]["total_duplicate_rows"] == 0
    assert result["report"]["record_details"] == []


def test_neutral_identifier_result():

    df = create_dataframe()

    result = build_neutral_validation_results(
        df
    )["identifiers"]

    assert result["identifier_columns"] == []
    assert result["affected_record_count"] == 0


def test_neutral_conversion_result():

    df = create_dataframe()

    result = build_neutral_validation_results(
        df
    )["conversion"]

    assert result["report"]["failed_conversions"] == 0
    assert not result["failed_rows"].any()


def test_neutral_numeric_result():

    df = create_dataframe()

    result = build_neutral_validation_results(
        df
    )["numeric"]

    assert result["report"]["total_outlier_cells"] == 0
    assert not result["range_violation_rows"].any()


def test_neutral_date_result():

    df = create_dataframe()

    result = build_neutral_validation_results(
        df
    )["dates"]

    assert result["report"]["invalid_date_record_count"] == 0
    assert not result["timezone_mismatch_rows"].any()


def test_neutral_contact_result():

    df = create_dataframe()

    result = build_neutral_validation_results(
        df
    )["contacts"]

    assert result["report"]["total_invalid_emails"] == 0
    assert result["report"]["total_invalid_phones"] == 0


def test_neutral_results_support_empty_dataframe():

    df = pd.DataFrame(
        columns=["id", "value"]
    )

    results = build_neutral_validation_results(df)

    assert len(results["missing_values"]["missing_rows"]) == 0
    assert len(results["duplicates"]["rejected_rows"]) == 0
