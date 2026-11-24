import json
import re
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

from .transformation_reporter import (
    generate_transformation_summary
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def safe_filename(name):
    """Generate a safe filename from the input dataset name."""

    name = re.sub(r"[^a-zA-Z0-9_-]", "_", str(name))
    name = re.sub(r"_+", "_", name).strip("_")

    return name or "dataset"


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
