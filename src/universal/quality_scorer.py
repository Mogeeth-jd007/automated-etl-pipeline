"""
Intelligent Data Quality Scoring Engine.

Calculates record-level and dataset-level quality scores.

Classification and quality scoring are independent.
"""

import math


DEFAULT_PENALTIES = {
    "INVALID_EMAIL": 10,
    "INVALID_PHONE": 10,
    "MISSING_VALUE": 8,
    "CONVERSION_FAILURE": 12,
    "NUMERIC_OUTLIER": 8,
    "FUTURE_DATE": 8,
    "MISSING_REQUIRED_VALUE": 30,
    "DUPLICATE_RECORD": 40,
    "EXACT_DUPLICATE": 40,
    "DUPLICATE_KEY": 40,
    "EMPTY_RECORD": 50,
    "NUMERIC_RANGE_VIOLATION": 25,
    "DATE_RANGE_VIOLATION": 25,
    "INVALID_DATE": 12,
    "QUALITY_VALIDATION_FAILURE": 10
}

DEFAULT_SEVERITY_PENALTIES = {
    "WARNING": 5,
    "REJECTED": 25
}

QUALITY_GRADES = (
    (90, "EXCELLENT"),
    (75, "GOOD"),
    (60, "FAIR"),
    (40, "POOR"),
    (0, "CRITICAL")
)


def validate_penalty_config(penalties):
    """Validate configurable issue penalties."""

    if not isinstance(penalties, dict):
        raise TypeError("Penalty configuration must be a dictionary.")

    for code, penalty in penalties.items():

        if not isinstance(code, str) or not code:
            raise ValueError("Issue codes must be non-empty strings.")

        if (
            isinstance(penalty, bool)
            or not isinstance(penalty, (int, float))
            or not math.isfinite(penalty)
            or penalty < 0
        ):
            raise ValueError(
                f"Invalid penalty for {code}: {penalty}"
            )


def get_quality_grade(score):
    """Convert a numerical quality score into a grade."""

    if (
        isinstance(score, bool)
        or not isinstance(score, (int, float))
        or not math.isfinite(score)
        or not 0 <= score <= 100
    ):
        raise ValueError("Quality score must be between 0 and 100.")

    for minimum, grade in QUALITY_GRADES:

        if score >= minimum:
            return grade

    return "CRITICAL"


def score_record(
    quality_reasons,
    penalty_config=None,
    severity_penalties=None
):
    """
    Calculate the quality score of one record.

    Duplicate issue codes affecting the same column
    are penalized only once.

    Different columns can receive separate penalties.
    """

    if not isinstance(quality_reasons, list):
        raise TypeError("quality_reasons must be a list.")

    penalties = dict(DEFAULT_PENALTIES)

    if penalty_config is not None:
        validate_penalty_config(penalty_config)
        penalties.update(penalty_config)

    severity_weights = dict(DEFAULT_SEVERITY_PENALTIES)

    if severity_penalties is not None:

        validate_penalty_config(severity_penalties)
        severity_weights.update(severity_penalties)

    applied = []
    seen = set()

    for issue in quality_reasons:

        if not isinstance(issue, dict):
            raise TypeError("Every quality issue must be a dictionary.")

        code = issue.get("code")
        column = issue.get("column")
        severity = issue.get("severity")

        if not isinstance(code, str) or not code:
            raise ValueError("Every issue must have a valid code.")

        if severity not in {"WARNING", "REJECTED"}:
            raise ValueError(
                f"Unsupported issue severity: {severity}"
            )

        # Deduplicate identical issues on the same column.
        key = (code, column)

        if key in seen:
            continue

        seen.add(key)

        penalty = penalties.get(
            code,
            severity_weights[severity]
        )

        applied.append({
            "code": code,
            "column": column,
            "severity": severity,
            "penalty": penalty
        })

    total_penalty = sum(
        item["penalty"] for item in applied
    )

    score = round(
        max(0, 100 - total_penalty),
        2
    )

    return {
        "quality_score": score,
        "quality_grade": get_quality_grade(score),
        "issue_count": len(applied),
        "total_penalty": total_penalty,
        "applied_penalties": applied
    }


def score_records(
    record_details,
    penalty_config=None,
    severity_penalties=None
):
    """Calculate quality scores for multiple records."""

    if not isinstance(record_details, list):
        raise TypeError("record_details must be a list.")

    results = []

    for position, record in enumerate(record_details):

        if not isinstance(record, dict):
            raise TypeError("Every record must be a dictionary.")

        if "quality_reasons" not in record:
            raise ValueError("Record is missing quality_reasons.")

        result = score_record(
            record["quality_reasons"],
            penalty_config=penalty_config,
            severity_penalties=severity_penalties
        )

        result["row_position"] = record.get(
            "row_position",
            position
        )

        results.append(result)

    return results


def calculate_dataset_quality(record_scores):
    """Generate dataset-level quality statistics."""

    if not isinstance(record_scores, list):
        raise TypeError("record_scores must be a list.")

    if not record_scores:
        return {
            "total_records": 0,
            "dataset_quality_score": None,
            "dataset_quality_grade": "NO_DATA",
            "minimum_score": None,
            "maximum_score": None,
            "grade_distribution": {}
        }

    scores = []

    for record in record_scores:

        if not isinstance(record, dict):
            raise TypeError("Every score must be a dictionary.")

        score = record.get("quality_score")

        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not math.isfinite(score)
            or not 0 <= score <= 100
        ):
            raise ValueError("Invalid record quality score.")

        scores.append(score)

    average_score = round(
        sum(scores) / len(scores),
        2
    )

    distribution = {}

    for score in scores:

        grade = get_quality_grade(score)

        distribution[grade] = (
            distribution.get(grade, 0) + 1
        )

    return {
        "total_records": len(scores),
        "dataset_quality_score": average_score,
        "dataset_quality_grade": get_quality_grade(
            average_score
        ),
        "minimum_score": min(scores),
        "maximum_score": max(scores),
        "grade_distribution": distribution
    }
