
import pandas as pd

from src.universal.data_profiler import profile_dataset


def create_financial_dataset():

    return pd.DataFrame({
        "customer_id": [
            "C001", "C002", "C003", "C004", "C005"
        ],
        "revenue": [
            "INR 1000",
            "INR 2000",
            "USD 500",
            "INR 3000",
            "USD 700"
        ],
        "discount": [
            "10%", "20%", "15%", "25%", "30%"
        ],
        "quantity": [5, 10, 8, 12, 15],
        "is_active": [
            "YES", "NO", "YES", "NO", "YES"
        ],
        "customer_name": [
            "Arun", "Meena", "Ravi", "Divya", "Kiran"
        ]
    })


def test_currency_profiling_integrated():

    df = create_financial_dataset()

    result = profile_dataset(df)

    assert "revenue" in result["currency_profiles"]

    profile = result["currency_profiles"]["revenue"]

    assert profile["valid_count"] == 5
    assert profile["invalid_count"] == 0

    assert "INR" in profile["unit_summary"]
    assert "USD" in profile["unit_summary"]


def test_percentage_profiling_integrated():

    df = create_financial_dataset()

    result = profile_dataset(df)

    assert "discount" in result["percentage_profiles"]

    profile = result["percentage_profiles"]["discount"]

    assert profile["valid_count"] == 5
    assert profile["invalid_count"] == 0

    statistics = profile["percentage_statistics"]

    assert statistics["minimum"] == 10.0
    assert statistics["maximum"] == 30.0
    assert statistics["mean"] == 20.0
    assert statistics["median"] == 20.0


def test_mixed_currency_units_remain_separate():

    df = create_financial_dataset()

    result = profile_dataset(df)

    profile = result["currency_profiles"]["revenue"]

    inr = profile["unit_summary"]["INR"]
    usd = profile["unit_summary"]["USD"]

    assert inr["count"] == 3
    assert usd["count"] == 2

    assert inr["statistics"]["sum"] == 6000.0
    assert usd["statistics"]["sum"] == 1200.0


def test_currency_missing_and_invalid_values_integrated():

    df = pd.DataFrame({
        "revenue": [
            "INR 100",
            "INR 200",
            "INR 300",
            "INR 400",
            "invalid",
            None
        ]
    })

    result = profile_dataset(df)

    profile = result["currency_profiles"]["revenue"]

    assert profile["valid_count"] == 4
    assert profile["missing_count"] == 1
    assert profile["invalid_count"] == 1


def test_percentage_missing_and_invalid_values_integrated():

    df = pd.DataFrame({
        "discount": [
            "10%",
            "20%",
            "30%",
            "40%",
            "invalid",
            None
        ]
    })

    result = profile_dataset(df)

    profile = result["percentage_profiles"]["discount"]

    assert profile["valid_count"] == 4
    assert profile["missing_count"] == 1
    assert profile["invalid_count"] == 1


def test_financial_profiling_preserves_original_dataframe():

    df = create_financial_dataset()

    original = df.copy(deep=True)

    profile_dataset(df)

    pd.testing.assert_frame_equal(df, original)


def test_all_existing_profiling_sections_are_preserved():

    df = create_financial_dataset()

    df["email"] = [
        "arun@example.com",
        "meena@example.com",
        "ravi@example.com",
        "divya@example.com",
        "kiran@example.com"
    ]

    df["transaction_date"] = [
        "2026-11-20",
        "2026-11-21",
        "2026-11-22",
        "2026-11-23",
        "2026-11-24"
    ]

    result = profile_dataset(
        df,
        reference_time="2026-11-26T12:00:00Z"
    )

    expected_sections = {
        "dataset_summary",
        "column_profiles",
        "numeric_profiles",
        "categorical_profiles",
        "identifier_profiles",
        "contact_profiles",
        "date_profiles",
        "boolean_profiles",
        "currency_profiles",
        "percentage_profiles",
        "missing_profiles"
    }

    assert expected_sections.issubset(result.keys())

    assert "revenue" in result["currency_profiles"]
    assert "discount" in result["percentage_profiles"]
    assert "quantity" in result["numeric_profiles"]
    assert "is_active" in result["boolean_profiles"]
    assert "email" in result["contact_profiles"]
    assert "transaction_date" in result["date_profiles"]
    assert "customer_id" in result["identifier_profiles"]
    assert "customer_name" in result["categorical_profiles"]


def test_financial_profile_column_types_are_correct():

    df = create_financial_dataset()

    result = profile_dataset(df)

    assert (
        result["column_profiles"]["revenue"]["data_type"]
        == "currency"
    )

    assert (
        result["column_profiles"]["discount"]["data_type"]
        == "percentage"
    )


def test_financial_columns_are_not_added_to_numeric_profiles():

    df = create_financial_dataset()

    result = profile_dataset(df)

    assert "revenue" not in result["numeric_profiles"]
    assert "discount" not in result["numeric_profiles"]

    assert "revenue" in result["currency_profiles"]
    assert "discount" in result["percentage_profiles"]


def test_empty_financial_profile_sections_are_returned():

    df = pd.DataFrame({
        "quantity": [10, 20, 30, 40, 50]
    })

    result = profile_dataset(df)

    assert result["currency_profiles"] == {}
    assert result["percentage_profiles"] == {}


def test_financial_profiling_does_not_change_input_column_names():

    df = pd.DataFrame({
        "Revenue Amount": [
            "INR 100",
            "INR 200",
            "INR 300",
            "INR 400",
            "INR 500"
        ]
    })

    original_columns = df.columns.tolist()

    profile_dataset(df)

    assert df.columns.tolist() == original_columns
