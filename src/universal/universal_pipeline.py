
from pathlib import Path

import pandas as pd

from .universal_extract import extract_universal
from .universal_transform import transform_universal
from .universal_validate import validate_universal
from .universal_load import load_universal
from .report_generator import generate_reports

try:
    from ..config import load_config
except ImportError:
    from config import load_config


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_input_file(input_file):
    """Resolve absolute, project-relative and raw-folder CSV paths."""

    path = Path(input_file)

    if path.is_absolute():
        resolved_path = path

    else:
        candidates = [
            PROJECT_ROOT / path,
            PROJECT_ROOT / "data" / "raw" / path
        ]

        resolved_path = next(
            (
                candidate
                for candidate in candidates
                if candidate.is_file()
            ),
            None
        )

    if resolved_path is None or not resolved_path.is_file():
        raise FileNotFoundError(
            f"Input CSV not found: {input_file}"
        )

    if resolved_path.suffix.lower() != ".csv":
        raise ValueError(
            "Universal pipeline currently accepts CSV files only."
        )

    return resolved_path


def load_quality_scoring_config():
    """Load and validate global quality scoring configuration."""

    config = load_config()

    scoring_config = config.get("quality_scoring", {})

    if not isinstance(scoring_config, dict):
        raise ValueError(
            "quality_scoring configuration must be a dictionary."
        )

    penalties = scoring_config.get("penalties", {})
    severity_penalties = scoring_config.get(
        "severity_penalties",
        {}
    )

    if not isinstance(penalties, dict):
        raise ValueError(
            "quality_scoring.penalties must be a dictionary."
        )

    if not isinstance(severity_penalties, dict):
        raise ValueError(
            "quality_scoring.severity_penalties must be a dictionary."
        )

    return penalties, severity_penalties


def run_universal_pipeline(input_file):

    print("\n")
    print("=" * 60)
    print("       UNIVERSAL AUTOMATED ETL PIPELINE")
    print("=" * 60)

    file_path = resolve_input_file(input_file)

    dataset_name = file_path.stem

    print(f"\nInput file: {file_path}")
    print(f"Dataset name: {dataset_name}")

    # STEP 1: Extract data.

    print("\n[STEP 1/5] EXTRACTING DATA")

    df = extract_universal(file_path)

    # STEP 2: Transform data and generate schema.

    print("\n[STEP 2/5] TRANSFORMING DATA")

    transformed_df, schema = transform_universal(df)

    # STEP 3: Load configurable quality scoring penalties.

    print("\n[STEP 3/5] LOADING SCORING CONFIGURATION")

    scoring_penalties, severity_penalties = (
        load_quality_scoring_config()
    )

    print("Quality scoring configuration loaded.")
    print("Configured issue penalties:", len(scoring_penalties))
    print("Configured severity penalties:", len(severity_penalties))

    # STEP 4: Schema-aware validation and quality scoring.

    print("\n[STEP 4/5] VALIDATING DATA")

    valid, warning, rejected, report = validate_universal(
        transformed_df,
        schema=schema,
        scoring_penalties=scoring_penalties,
        scoring_severity_penalties=severity_penalties
    )

    # Load eligible records.

    print("\n[DATABASE] LOADING ELIGIBLE RECORDS")

    eligible_records = pd.concat(
        [valid, warning]
    ).sort_index()

    database_result = load_universal(
        eligible_records,
        table_name=dataset_name
    )

    # STEP 5: Generate reports.

    print("\n[STEP 5/5] GENERATING REPORTS")

    report_files = generate_reports(
        valid,
        warning,
        rejected,
        report,
        schema,
        dataset_name
    )

    print("\n")
    print("=" * 60)
    print("       UNIVERSAL ETL PIPELINE COMPLETED")
    print("=" * 60)

    print(f"Dataset: {dataset_name}")
    print(f"Total records: {report['total_records']}")
    print(f"Valid records: {report['valid_records']}")
    print(f"Warning records: {report['warning_records']}")
    print(f"Rejected records: {report['rejected_records']}")

    print(
        "Dataset quality score:",
        report["dataset_quality_summary"][
            "dataset_quality_score"
        ]
    )

    print(
        "Dataset quality grade:",
        report["dataset_quality_summary"][
            "dataset_quality_grade"
        ]
    )

    print(
        f"Conversion failure rows: "
        f"{report['conversion_failure_rows']}"
    )

    print(
        f"Failed conversions: "
        f"{report['conversion_summary']['failed_conversions']}"
    )

    print(
        f"Database table: "
        f"{database_result['table_name']}"
    )

    print("\nAll pipeline stages completed successfully.")

    return {
        "dataset": dataset_name,
        "quality_report": report,
        "database": database_result,
        "files": report_files
    }
