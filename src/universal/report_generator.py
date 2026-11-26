
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal

import numpy as np
import pandas as pd

from .transformation_reporter import (
    generate_transformation_summary
)

from .data_profiler import profile_dataset


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def safe_filename(name):
    """Generate a safe filename from the input dataset name."""

    name = re.sub(r"[^a-zA-Z0-9_-]", "_", str(name))
    name = re.sub(r"_+", "_", name).strip("_")

    return name or "dataset"


def json_safe_value(value):
    """Convert pandas, NumPy and other values into JSON-compatible data."""

    if value is None or value is pd.NA or value is pd.NaT:
        return None

    if isinstance(value, dict):
        return {
            str(key): json_safe_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            json_safe_value(item)
            for item in value
        ]

    if isinstance(value, set):
        return [
            json_safe_value(item)
            for item in sorted(value, key=str)
        ]

    if isinstance(value, np.generic):
        return json_safe_value(value.item())

    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, float) and not np.isfinite(value):
        return None

    return value


def build_profiling_observations(profile):
    """
    Generate observations from measurable profiling results.

    These observations identify potential data-quality concerns.
    They do not automatically reject or modify records.
    """

    observations = []

    summary = profile.get("dataset_summary", {})

    # Dataset completeness.
    completeness = summary.get("completeness_score")

    if completeness is not None and completeness < 100:

        observations.append({
            "category": "MISSING_VALUES",
            "severity": "WARNING",
            "description": (
                f"Dataset completeness is {completeness}%."
            ),
            "affected_records": summary.get(
                "total_records", 0
            ),
            "affected_columns": []
        })

    # Duplicate records.
    duplicate_count = summary.get("duplicate_records", 0)

    if duplicate_count > 0:

        observations.append({
            "category": "DUPLICATE_RECORDS",
            "severity": "WARNING",
            "description": (
                f"{duplicate_count} duplicate records detected."
            ),
            "affected_records": duplicate_count,
            "affected_columns": []
        })

    # Column-level missing values.
    missing_columns = []

    for column, details in profile.get(
        "column_profiles", {}
    ).items():

        missing_percentage = details.get(
            "missing_percentage"
        )

        if missing_percentage is not None and missing_percentage > 0:
            missing_columns.append({
                "column": column,
                "missing_percentage": missing_percentage
            })

    if missing_columns:

        observations.append({
            "category": "COLUMN_COMPLETENESS",
            "severity": "WARNING",
            "description": (
                "One or more columns contain missing values."
            ),
            "affected_records": None,
            "affected_columns": missing_columns
        })

    # Invalid-value checks across specialized profiles.
    profile_sections = [
        "numeric_profiles",
        "currency_profiles",
        "percentage_profiles",
        "date_profiles",
        "boolean_profiles",
        "contact_profiles"
    ]

    for section_name in profile_sections:

        section = profile.get(section_name, {})

        for column, details in section.items():

            invalid_count = details.get("invalid_count", 0)

            if invalid_count > 0:

                observations.append({
                    "category": "INVALID_VALUES",
                    "severity": "WARNING",
                    "description": (
                        f"{invalid_count} invalid values detected "
                        f"in column '{column}'."
                    ),
                    "affected_records": invalid_count,
                    "affected_columns": [column]
                })

    return observations


def generate_profiling_report(
    df,
    dataset_name,
    output_dir=None,
    detection_config=None,
    reference_time=None
):
    """
    Generate a comprehensive JSON dataset profiling report.

    Parameters
    ----------
    df : pandas.DataFrame
        Original input dataset.

    dataset_name : str
        Name of the dataset.

    output_dir : str or Path, optional
        Custom report output directory.

    detection_config : dict, optional
        Configuration passed to the profiling engine.

    reference_time : datetime or str, optional
        Reference time used for date profiling.

    Returns
    -------
    dict
        Generated report path and profiling results.
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            "Input must be a pandas DataFrame."
        )

    if not isinstance(dataset_name, str) or not dataset_name.strip():
        raise ValueError(
            "Dataset name must be a non-empty string."
        )

    print("\n========== DATASET PROFILING REPORT STARTED ==========")

    dataset_name = safe_filename(dataset_name)

    # Execute the existing universal profiling engine.
    profiling_results = profile_dataset(
        df,
        detection_config=detection_config,
        reference_time=reference_time
    )

    # Generate measurable quality observations.
    observations = build_profiling_observations(
        profiling_results
    )

    # Determine report directory.
    if output_dir is None:
        reports_dir = PROJECT_ROOT / "reports"
    else:
        reports_dir = Path(output_dir)

    reports_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # Construct comprehensive report.
    profiling_report = {
        "report_type": "DATASET_PROFILING_REPORT",
        "dataset": dataset_name,
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "dataset_summary": profiling_results[
            "dataset_summary"
        ],
        "column_profiles": profiling_results[
            "column_profiles"
        ],
        "profiling_sections": {
            "numeric_profiles": profiling_results[
                "numeric_profiles"
            ],
            "categorical_profiles": profiling_results[
                "categorical_profiles"
            ],
            "identifier_profiles": profiling_results[
                "identifier_profiles"
            ],
            "contact_profiles": profiling_results[
                "contact_profiles"
            ],
            "date_profiles": profiling_results[
                "date_profiles"
            ],
            "boolean_profiles": profiling_results[
                "boolean_profiles"
            ],
            "currency_profiles": profiling_results[
                "currency_profiles"
            ],
            "percentage_profiles": profiling_results[
                "percentage_profiles"
            ],
            "missing_profiles": profiling_results[
                "missing_profiles"
            ]
        },
        "quality_observations": observations,
        "quality_observation_count": len(observations)
    }

    # Convert all values into JSON-compatible representations.
    profiling_report = json_safe_value(
        profiling_report
    )

    report_path = (
        reports_dir
        / f"{dataset_name}_profiling_report.json"
    )

    with open(
        report_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            profiling_report,
            file,
            indent=4,
            ensure_ascii=False,
            allow_nan=False
        )

    print("Dataset:", dataset_name)

    print(
        "Total records:",
        profiling_report["dataset_summary"]["total_records"]
    )

    print(
        "Total columns:",
        profiling_report["dataset_summary"]["total_columns"]
    )

    print(
        "Completeness:",
        profiling_report["dataset_summary"]["completeness_score"]
    )

    print(
        "Quality observations:",
        len(observations)
    )

    print("Profiling report saved:", report_path)

    print(
        "\n========== DATASET PROFILING REPORT COMPLETED ==========\n"
    )

    return {
        "profiling_report": str(report_path),
        "report": profiling_report,
        "profiling_results": profiling_results,
        "observations": observations
    }


def generate_reports(
    valid_records,
    warning_records,
    rejected_records,
    report,
    schema,
    dataset_name
):
    """
    Generate processed CSVs, rejected CSVs,
    validation statistics and transformation quality reports.
    """

    print("\n========== REPORT GENERATION STARTED ==========")

    dataset_name = safe_filename(dataset_name)

    processed_dir = PROJECT_ROOT / "data" / "processed"
    rejected_dir = PROJECT_ROOT / "data" / "rejected"
    reports_dir = PROJECT_ROOT / "reports"

    processed_dir.mkdir(parents=True, exist_ok=True)
    rejected_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    processed_records = pd.concat(
        [valid_records, warning_records]
    ).sort_index()

    # Save processed records.
    processed_path = processed_dir / f"{dataset_name}_processed.csv"
    processed_records.to_csv(processed_path, index=False)

    # Save valid records.
    valid_path = processed_dir / f"{dataset_name}_valid.csv"
    valid_records.to_csv(valid_path, index=False)

    # Save warning records.
    warning_path = processed_dir / f"{dataset_name}_warnings.csv"
    warning_records.to_csv(warning_path, index=False)

    # Save rejected records.
    rejected_path = rejected_dir / f"{dataset_name}_rejected.csv"
    rejected_records.to_csv(rejected_path, index=False)

    # Generate dataset-level transformation statistics.
    transformation_summary = generate_transformation_summary(
        schema
    )

    # Combine validation, schema and transformation statistics.
    quality_report = {
        "dataset": dataset_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "quality_summary": report,
        "detected_schema": schema,
        "transformation_summary": transformation_summary
    }

    report_path = reports_dir / f"{dataset_name}_quality_report.json"

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(
            quality_report,
            file,
            indent=4,
            default=str
        )

    print("Processed CSV saved:", processed_path)
    print("Valid CSV saved:", valid_path)
    print("Warning CSV saved:", warning_path)
    print("Rejected CSV saved:", rejected_path)
    print("Quality report saved:", report_path)

    print("\nTRANSFORMATION QUALITY SUMMARY:")

    print(
        "Source columns:",
        transformation_summary["source_columns"]
    )

    print(
        "Generated columns:",
        transformation_summary["generated_columns"]
    )

    print(
        "Attempted conversions:",
        transformation_summary["attempted_conversions"]
    )

    print(
        "Successful conversions:",
        transformation_summary["successful_conversions"]
    )

    print(
        "Failed conversions:",
        transformation_summary["failed_conversions"]
    )

    print(
        "Affected records:",
        transformation_summary["affected_record_count"]
    )

    success_rate = transformation_summary[
        "conversion_success_rate_percent"
    ]

    if success_rate is None:
        print("Conversion success rate: N/A")
    else:
        print(f"Conversion success rate: {success_rate:.2f}%")

    print("\n========== REPORT GENERATION COMPLETED ==========\n")

    return {
        "processed_file": str(processed_path),
        "valid_file": str(valid_path),
        "warning_file": str(warning_path),
        "rejected_file": str(rejected_path),
        "quality_report": str(report_path)
    }
