
from decimal import Decimal, InvalidOperation

import pandas as pd

from .financial_handler import parse_financial_value


def _safe_float(value):
    """Convert Decimal values into JSON-compatible floats."""

    if value is None:
        return None

    try:
        result = float(value)

        if pd.isna(result) or result in (float("inf"), float("-inf")):
            return None

        return result

    except (ValueError, TypeError, OverflowError):
        return None


def _calculate_statistics(values):
    """Calculate descriptive statistics using Decimal precision."""

    if not values:
        return {
            "minimum": None,
            "maximum": None,
            "mean": None,
            "median": None,
            "sum": None
        }

    ordered = sorted(values)

    count = len(ordered)

    middle = count // 2

    if count % 2 == 0:
        median = (
            ordered[middle - 1] + ordered[middle]
        ) / Decimal("2")
    else:
        median = ordered[middle]

    mean = sum(ordered, Decimal("0")) / Decimal(count)

    return {
        "minimum": _safe_float(ordered[0]),
        "maximum": _safe_float(ordered[-1]),
        "mean": _safe_float(mean),
        "median": _safe_float(median),
        "sum": _safe_float(
            sum(ordered, Decimal("0"))
        )
    }


def profile_currency_column(series):
    """
    Profile currency values while preserving currency units.

    Statistics are calculated separately for each currency.
    Different currencies are never combined.
    """

    total_records = len(series)

    missing_count = 0
    invalid_count = 0
    valid_count = 0

    currency_values = {}

    invalid_examples = []

    for position, value in enumerate(series):

        if pd.isna(value) or not str(value).strip():

            missing_count += 1
            continue

        parsed = parse_financial_value(value)

        if (
            parsed is None
            or parsed["data_type"] != "currency"
        ):

            invalid_count += 1

            invalid_examples.append({
                "row_position": position
            })

            continue

        unit = parsed["unit"]

        currency_values.setdefault(
            unit, []
        ).append(parsed["value"])

        valid_count += 1

    unit_summary = {}

    for unit, values in currency_values.items():

        unit_summary[unit] = {
            "count": len(values),
            "statistics": _calculate_statistics(values)
        }

    completeness = (
        round(valid_count / total_records * 100, 2)
        if total_records > 0
        else None
    )

    validity = (
        round(
            valid_count / (valid_count + invalid_count) * 100,
            2
        )
        if valid_count + invalid_count > 0
        else None
    )

    return {
        "financial_type": "currency",
        "total_records": total_records,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "missing_count": missing_count,
        "completeness_percentage": completeness,
        "validity_percentage": validity,
        "currency_units": list(currency_values.keys()),
        "unit_summary": unit_summary,
        "invalid_examples": invalid_examples
    }


def profile_percentage_column(series):
    """
    Profile percentage values.

    Financial handler stores percentages as decimal fractions.
    Example: 25% becomes 0.25.
    """

    total_records = len(series)

    valid_values = []

    missing_count = 0
    invalid_count = 0

    invalid_examples = []

    for position, value in enumerate(series):

        if pd.isna(value) or not str(value).strip():

            missing_count += 1
            continue

        parsed = parse_financial_value(value)

        if (
            parsed is None
            or parsed["data_type"] != "percentage"
        ):

            invalid_count += 1

            invalid_examples.append({
                "row_position": position
            })

            continue

        valid_values.append(parsed["value"])

    valid_count = len(valid_values)

    decimal_statistics = _calculate_statistics(
        valid_values
    )

    percentage_statistics = {
        key: (
            _safe_float(
                Decimal(str(value)) * Decimal("100")
            )
            if value is not None
            else None
        )
        for key, value in decimal_statistics.items()
    }

    completeness = (
        round(valid_count / total_records * 100, 2)
        if total_records > 0
        else None
    )

    validity = (
        round(
            valid_count / (valid_count + invalid_count) * 100,
            2
        )
        if valid_count + invalid_count > 0
        else None
    )

    return {
        "financial_type": "percentage",
        "total_records": total_records,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "missing_count": missing_count,
        "completeness_percentage": completeness,
        "validity_percentage": validity,
        "decimal_statistics": decimal_statistics,
        "percentage_statistics": percentage_statistics,
        "invalid_examples": invalid_examples
    }
