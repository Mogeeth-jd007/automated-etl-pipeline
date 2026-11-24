import pandas as pd
import pytest

from universal.conversion_tracker import (
    track_conversion_failures
)


@pytest.mark.parametrize(
    "data_type",
    [
        "numeric",
        "currency",
        "percentage",
        "date",
        "boolean"
    ]
)
def test_supported_conversion_types(data_type):

    original = pd.Series(["value"])
    converted = pd.Series(["converted"])

    report = track_conversion_failures(
        original,
        converted,
        data_type
    )

    assert report["data_type"] == data_type

    assert report["successful_conversions"] == 1


def test_successful_conversions():

    original = pd.Series(["100", "200", "300"])
    converted = pd.Series([100, 200, 300])

    report = track_conversion_failures(
        original,
        converted,
        "numeric"
    )

    assert report["total_records"] == 3

    assert report["attempted_conversions"] == 3

    assert report["successful_conversions"] == 3

    assert report["failed_conversions"] == 0

    assert report["failure_rate_percent"] == 0.0

    assert report["failed_row_positions"] == []


def test_partial_conversion_failures():

    original = pd.Series([
        "100", "invalid", "300", "abc"
    ])

    converted = pd.Series([
        100, pd.NA, 300, pd.NA
    ])

    report = track_conversion_failures(
        original,
        converted,
        "numeric"
    )

    assert report["attempted_conversions"] == 4

    assert report["successful_conversions"] == 2

    assert report["failed_conversions"] == 2

    assert report["failure_rate_percent"] == 50.0

    assert report["failed_row_positions"] == [1, 3]


def test_original_missing_values():

    original = pd.Series([
        "100", None, "invalid", pd.NA
    ])

    converted = pd.Series([
        100, pd.NA, pd.NA, pd.NA
    ])

    report = track_conversion_failures(
        original,
        converted,
        "numeric"
    )

    assert report["total_records"] == 4

    assert report["original_missing_count"] == 2

    assert report["attempted_conversions"] == 2

    assert report["successful_conversions"] == 1

    assert report["failed_conversions"] == 1

    assert report["failure_rate_percent"] == 50.0

    assert report["failed_row_positions"] == [2]


def test_all_conversions_failed():

    original = pd.Series(["abc", "invalid"])
    converted = pd.Series([pd.NA, pd.NA])

    report = track_conversion_failures(
        original,
        converted,
        "numeric"
    )

    assert report["successful_conversions"] == 0

    assert report["failed_conversions"] == 2

    assert report["failure_rate_percent"] == 100.0

    assert report["failed_row_positions"] == [0, 1]


def test_all_original_values_missing():

    original = pd.Series([None, pd.NA])
    converted = pd.Series([pd.NA, pd.NA])

    report = track_conversion_failures(
        original,
        converted,
        "numeric"
    )

    assert report["original_missing_count"] == 2

    assert report["attempted_conversions"] == 0

    assert report["successful_conversions"] == 0

    assert report["failed_conversions"] == 0

    assert report["failure_rate_percent"] == 0.0


def test_empty_series():

    original = pd.Series([], dtype="string")
    converted = pd.Series([], dtype="Float64")

    report = track_conversion_failures(
        original,
        converted,
        "numeric"
    )

    assert report["total_records"] == 0

    assert report["attempted_conversions"] == 0

    assert report["failed_conversions"] == 0

    assert report["failure_rate_percent"] == 0.0

    assert report["failed_row_positions"] == []


def test_custom_index_row_positions():

    original = pd.Series(
        ["100", "invalid", "300"],
        index=[10, 20, 30]
    )

    converted = pd.Series(
        [100, pd.NA, 300],
        index=[10, 20, 30]
    )

    report = track_conversion_failures(
        original,
        converted,
        "numeric"
    )

    assert report["failed_row_positions"] == [1]


def test_failure_rate_rounding():

    original = pd.Series([
        "100", "invalid", "300"
    ])

    converted = pd.Series([
        100, pd.NA, 300
    ])

    report = track_conversion_failures(
        original,
        converted,
        "numeric"
    )

    assert report["failure_rate_percent"] == 33.33


def test_mismatched_series_lengths():

    original = pd.Series(["100", "200"])
    converted = pd.Series([100])

    with pytest.raises(ValueError, match="equal lengths"):

        track_conversion_failures(
            original,
            converted,
            "numeric"
        )


def test_mismatched_series_indexes():

    original = pd.Series(
        ["100", "200"],
        index=[10, 20]
    )

    converted = pd.Series(
        [100, 200],
        index=[20, 30]
    )

    with pytest.raises(ValueError, match="matching indexes"):

        track_conversion_failures(
            original,
            converted,
            "numeric"
        )


def test_unsupported_conversion_type():

    original = pd.Series(["Laptop"])
    converted = pd.Series(["Laptop"])

    with pytest.raises(
        ValueError,
        match="Unsupported conversion type"
    ):

        track_conversion_failures(
            original,
            converted,
            "text"
        )


def test_original_series_unchanged():

    original = pd.Series(["100", "invalid"])
    converted = pd.Series([100, pd.NA])

    original_copy = original.copy(deep=True)
    converted_copy = converted.copy(deep=True)

    track_conversion_failures(
        original,
        converted,
        "numeric"
    )

    pd.testing.assert_series_equal(
        original,
        original_copy
    )

    pd.testing.assert_series_equal(
        converted,
        converted_copy
    )
