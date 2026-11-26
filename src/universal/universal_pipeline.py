
import hashlib
from pathlib import Path

import pandas as pd

from .universal_extract import extract_universal
from .universal_transform import transform_universal
from .universal_validate import validate_universal
from .universal_load import load_universal

from .report_generator import (
    generate_reports,
    generate_profiling_report
)

from .execution_tracker import (
    start_execution,
    update_execution_stage,
    complete_execution,
    fail_execution
)

from .stage_tracker import (
    start_stage,
    complete_stage,
    fail_stage
)

from .retry_manager import (
    execute_with_retry,
    validate_retry_config
)

from .processing_registry import (
    get_database_path,
    is_file_processed,
    record_processed_file
)

try:
    from ..config import load_config
except ImportError:
    from config import load_config


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RETRY_SAFE_STAGES = {
    "EXTRACT",
    "TRANSFORM",
    "SCORING_CONFIGURATION",
    "VALIDATION"
}


# ============================================================
# FILE RESOLUTION AND FINGERPRINTING
# ============================================================

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


def calculate_file_hash(file_path):
    """Generate a SHA-256 fingerprint using file contents."""

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:

        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b""
        ):
            sha256.update(chunk)

    return sha256.hexdigest()


# ============================================================
# CONFIGURATION
# ============================================================

def load_quality_scoring_config():
    """Load and validate quality scoring configuration."""

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


def load_retry_config():
    """Load and validate automatic retry configuration."""

    config = load_config()

    retry_config = config.get("retry", {})

    if not isinstance(retry_config, dict):
        raise ValueError(
            "retry configuration must be a dictionary."
        )

    enabled = retry_config.get("enabled", True)

    if not isinstance(enabled, bool):
        raise ValueError(
            "retry.enabled must be a boolean."
        )

    max_attempts = retry_config.get("max_attempts", 3)
    base_delay = retry_config.get("base_delay_seconds", 2)
    max_delay = retry_config.get("max_delay_seconds", 30)

    validate_retry_config(
        max_attempts=max_attempts,
        base_delay_seconds=base_delay,
        max_delay_seconds=max_delay
    )

    return {
        "enabled": enabled,
        "max_attempts": max_attempts,
        "base_delay_seconds": base_delay,
        "max_delay_seconds": max_delay
    }


def load_profiling_config():
    """Load and validate automatic profiling configuration."""

    config = load_config()

    profiling_config = config.get(
        "universal_profiling",
        {}
    )

    if not isinstance(profiling_config, dict):
        raise ValueError(
            "universal_profiling configuration must be a dictionary."
        )

    allowed_options = {"enabled"}

    unknown_options = set(profiling_config) - allowed_options

    if unknown_options:
        raise ValueError(
            "Unknown universal_profiling options: "
            f"{sorted(unknown_options)}"
        )

    enabled = profiling_config.get("enabled", True)

    if not isinstance(enabled, bool):
        raise ValueError(
            "universal_profiling.enabled must be a boolean."
        )

    return {
        "enabled": enabled
    }


def load_date_validation_config():
    """Load and validate date-specific validation rules."""

    config = load_config()

    date_config = config.get(
        "universal_date_validation",
        {}
    )

    if not isinstance(date_config, dict):
        raise ValueError(
            "universal_date_validation must be a dictionary."
        )

    allowed_options = {
        "date_ranges",
        "no_future_columns",
        "chronological_rules",
        "reference_time"
    }

    unknown_options = set(date_config) - allowed_options

    if unknown_options:
        raise ValueError(
            f"Unknown date validation options: "
            f"{sorted(unknown_options)}"
        )

    date_ranges = date_config.get("date_ranges", {})

    no_future_columns = date_config.get(
        "no_future_columns",
        []
    )

    chronological_rules = date_config.get(
        "chronological_rules",
        []
    )

    reference_time = date_config.get("reference_time")

    if not isinstance(date_ranges, dict):
        raise ValueError(
            "date_ranges must be a dictionary."
        )

    if (
        not isinstance(no_future_columns, list)
        or not all(
            isinstance(column, str) and column
            for column in no_future_columns
        )
    ):
        raise ValueError(
            "no_future_columns must be a list of column names."
        )

    if not isinstance(chronological_rules, list):
        raise ValueError(
            "chronological_rules must be a list."
        )

    for rule in chronological_rules:

        if (
            not isinstance(rule, (list, tuple))
            or len(rule) != 2
            or not all(
                isinstance(column, str) and column
                for column in rule
            )
        ):
            raise ValueError(
                "Each chronological rule must contain "
                "two column names."
            )

    return {
        "date_ranges": date_ranges,
        "no_future_columns": no_future_columns,
        "chronological_rules": chronological_rules,
        "reference_time": reference_time
    }


# ============================================================
# STAGE MONITORING AND RETRY MANAGEMENT
# ============================================================

def run_monitored_stage(
    execution,
    stage_name,
    operation,
    retry_config=None,
    retry_enabled=False
):
    """Execute and monitor a stage with optional automatic retries."""

    update_execution_stage(
        execution,
        stage_name
    )

    stage = start_stage(
        execution,
        stage_name
    )

    print(
        f"\n========== STAGE STARTED: {stage_name} =========="
    )

    try:

        if retry_enabled:

            if retry_config is None:
                retry_config = load_retry_config()

            def on_retry(attempt, error, delay):

                print(f"\nRETRY: {stage_name}")
                print(f"Failed attempt: {attempt}")
                print(f"Error: {error}")
                print(f"Waiting: {delay} seconds")

            result = execute_with_retry(
                operation,
                max_attempts=retry_config["max_attempts"],
                base_delay_seconds=retry_config["base_delay_seconds"],
                max_delay_seconds=retry_config["max_delay_seconds"],
                on_retry=on_retry,
                execution_id=execution["execution_id"],
                stage_name=stage_name,
                database_path=execution["database_path"]
            )

        else:

            result = operation()

        stage_result = complete_stage(stage)

        print(
            f"Stage completed: {stage_name} | "
            f"Duration: {stage_result['duration_seconds']} seconds"
        )

        return result

    except Exception as error:

        try:

            fail_stage(stage, error)

            print(
                f"Stage failure diagnostics saved: {stage_name}"
            )

        except Exception as tracking_error:

            print(
                "WARNING: Stage failure tracking failed:",
                tracking_error
            )

        raise


# ============================================================
# PERSISTENT FILE PROCESSING REGISTRY
# ============================================================

def check_duplicate_file(file_path):
    """
    Check whether the CSV content has already been processed.

    Returns the SHA-256 fingerprint and duplicate status.
    """

    file_hash = calculate_file_hash(file_path)

    database_path = get_database_path()

    duplicate = is_file_processed(
        file_hash,
        database_path=database_path
    )

    return file_hash, duplicate


def register_successful_file(
    file_hash,
    file_path,
    dataset_name,
    execution_id,
    records_processed,
    database_path
):
    """Register a file only after successful pipeline completion."""

    return record_processed_file(
        file_hash=file_hash,
        file_name=Path(file_path).name,
        dataset_name=dataset_name,
        execution_id=execution_id,
        records_processed=records_processed,
        database_path=database_path
    )


# ============================================================
# UNIVERSAL AUTOMATED ETL PIPELINE
# ============================================================

def run_universal_pipeline(input_file):
    """Run the universal ETL pipeline with persistent deduplication."""

    print("\n")
    print("=" * 60)
    print("       UNIVERSAL AUTOMATED ETL PIPELINE")
    print("=" * 60)

    dataset_name = Path(input_file).stem

    # --------------------------------------------------------
    # STEP 0: DUPLICATE FILE DETECTION
    # --------------------------------------------------------

    resolved_input = None
    file_hash = None

    try:

        resolved_input = resolve_input_file(input_file)

        print("\n========== FILE PROCESSING REGISTRY ==========")

        print(
            "Checking incoming file:",
            resolved_input.name
        )

        try:

            file_hash, duplicate = check_duplicate_file(
                resolved_input
            )

            print("SHA-256 fingerprint:", file_hash)

            if duplicate:

                print("\nDUPLICATE FILE DETECTED")
                print(
                    "This file has already been successfully processed."
                )

                print("Dataset:", resolved_input.stem)

                print(
                    "Pipeline execution skipped to prevent "
                    "duplicate processing."
                )

                return {
                    "dataset": resolved_input.stem,
                    "status": "SKIPPED_DUPLICATE",
                    "duplicate": True,
                    "file_hash": file_hash,
                    "execution_id": None
                }

            print("Duplicate check: PASSED")
            print("New file detected.")

        except Exception as registry_error:

            print(
                "WARNING: Duplicate detection unavailable:",
                registry_error
            )

            print(
                "Pipeline will continue without pre-execution "
                "duplicate protection."
            )

            file_hash = None

    except (FileNotFoundError, ValueError):

        # Preserve the original execution failure tracking.
        # The EXTRACT stage will capture the actual error.

        resolved_input = None

    # --------------------------------------------------------
    # START EXECUTION
    # --------------------------------------------------------

    execution = start_execution(
        dataset_name=dataset_name,
        input_file=str(input_file)
    )

    execution_id = execution["execution_id"]

    df = None
    report = None

    valid = pd.DataFrame()
    warning = pd.DataFrame()
    rejected = pd.DataFrame()

    database_result = None
    report_files = None

    profiling_result = {
        "status": "NOT_STARTED",
        "profiling_report": None
    }

    registry_result = {
        "status": "NOT_REGISTERED"
    }

    # --------------------------------------------------------
    # RECORD COUNTS
    # --------------------------------------------------------

    def get_record_counts():

        if report is not None:

            return {
                "total_records": int(
                    report.get("total_records", 0)
                ),
                "valid_records": int(
                    report.get("valid_records", 0)
                ),
                "warning_records": int(
                    report.get("warning_records", 0)
                ),
                "rejected_records": int(
                    report.get("rejected_records", 0)
                )
            }

        if df is not None:

            return {
                "total_records": int(len(df)),
                "valid_records": int(len(valid)),
                "warning_records": int(len(warning)),
                "rejected_records": int(len(rejected))
            }

        return {
            "total_records": 0,
            "valid_records": 0,
            "warning_records": 0,
            "rejected_records": 0
        }

    try:

        retry_config = load_retry_config()

        print("\nRETRY CONFIGURATION")
        print("Enabled:", retry_config["enabled"])
        print("Maximum attempts:", retry_config["max_attempts"])
        print("Base delay:", retry_config["base_delay_seconds"])
        print("Maximum delay:", retry_config["max_delay_seconds"])

        # ====================================================
        # STEP 1: EXTRACTION
        # ====================================================

        def extract_operation():

            file_path = (
                resolved_input
                if resolved_input is not None
                else resolve_input_file(input_file)
            )

            print(f"Input file: {file_path}")

            extraction_config = load_config().get(
                "universal_extraction",
                {}
            )

            return (
                file_path,
                extract_universal(
                    file_path,
                    config=extraction_config
                )
            )

        file_path, df = run_monitored_stage(
            execution,
            "EXTRACT",
            extract_operation,
            retry_config,
            retry_config["enabled"]
            and "EXTRACT" in RETRY_SAFE_STAGES
        )

        dataset_name = file_path.stem

        print(f"Execution ID: {execution_id}")
        print(f"Dataset name: {dataset_name}")

        # ====================================================
        # STEP 2: TRANSFORMATION
        # ====================================================

        transformation_config = load_config().get(
            "universal_transformation",
            {}
        )

        transformed_df, schema = run_monitored_stage(
            execution,
            "TRANSFORM",
            lambda: transform_universal(
                df,
                config=transformation_config
            ),
            retry_config,
            retry_config["enabled"]
            and "TRANSFORM" in RETRY_SAFE_STAGES
        )

        # ====================================================
        # STEP 3: QUALITY SCORING CONFIGURATION
        # ====================================================

        scoring_penalties, severity_penalties = run_monitored_stage(
            execution,
            "SCORING_CONFIGURATION",
            load_quality_scoring_config,
            retry_config,
            retry_config["enabled"]
            and "SCORING_CONFIGURATION" in RETRY_SAFE_STAGES
        )

        # ====================================================
        # STEP 4: VALIDATION CONFIGURATION
        # ====================================================

        pipeline_config = load_config()

        validation_config = pipeline_config.get(
            "universal_validation",
            {}
        )

        date_validation_config = load_date_validation_config()

        # ====================================================
        # STEP 5: VALIDATION
        # ====================================================

        valid, warning, rejected, report = run_monitored_stage(
            execution,
            "VALIDATION",
            lambda: validate_universal(
                transformed_df,
                schema=schema,
                scoring_penalties=scoring_penalties,
                scoring_severity_penalties=severity_penalties,
                validation_config=validation_config,
                date_ranges=date_validation_config["date_ranges"],
                no_future_columns=date_validation_config[
                    "no_future_columns"
                ],
                chronological_rules=date_validation_config[
                    "chronological_rules"
                ],
                reference_time=date_validation_config[
                    "reference_time"
                ]
            ),
            retry_config,
            retry_config["enabled"]
            and "VALIDATION" in RETRY_SAFE_STAGES
        )

        # ====================================================
        # STEP 6: DATABASE LOAD
        # ====================================================
        # Database writes are deliberately excluded from retries.

        def database_operation():

            eligible_records = pd.concat(
                [valid, warning]
            ).sort_index()

            return load_universal(
                eligible_records,
                table_name=dataset_name
            )

        database_result = run_monitored_stage(
            execution,
            "DATABASE_LOAD",
            database_operation,
            retry_config,
            retry_enabled=False
        )

        # ====================================================
        # STEP 7: REPORT GENERATION
        # ====================================================
        # Report writes are deliberately excluded from retries.

        report_files = run_monitored_stage(
            execution,
            "REPORT_GENERATION",
            lambda: generate_reports(
                valid,
                warning,
                rejected,
                report,
                schema,
                dataset_name
            ),
            retry_config,
            retry_enabled=False
        )

        # ====================================================
        # STEP 8: DATASET PROFILING
        # ====================================================

        def profiling_operation():

            profiling_config = load_profiling_config()

            print("\nPROFILING CONFIGURATION")
            print("Enabled:", profiling_config["enabled"])

            if not profiling_config["enabled"]:

                print(
                    "Dataset profiling skipped because "
                    "it is disabled in config.json."
                )

                return {
                    "status": "DISABLED",
                    "profiling_report": None
                }

            result = generate_profiling_report(
                df,
                dataset_name,
                reference_time=date_validation_config[
                    "reference_time"
                ]
            )

            return {
                "status": "COMPLETED",
                "profiling_report": result["profiling_report"]
            }

        profiling_result = run_monitored_stage(
            execution,
            "DATASET_PROFILING",
            profiling_operation,
            retry_config,
            retry_enabled=False
        )

        # ====================================================
        # STEP 9: COMPLETE EXECUTION
        # ====================================================

        execution_result = complete_execution(
            execution,
            **get_record_counts()
        )

        # ====================================================
        # STEP 10: REGISTER SUCCESSFULLY PROCESSED FILE
        # ====================================================
        # Registration happens only after all pipeline stages
        # and execution completion have succeeded.
        #
        # Registry failure must not convert an already successful
        # ETL execution into a failed execution.

        try:

            if file_hash is None:

                file_hash = calculate_file_hash(file_path)

            registry_result = {
                "status": "REGISTERED",
                "file_hash": file_hash,
                "registered": register_successful_file(
                    file_hash=file_hash,
                    file_path=file_path,
                    dataset_name=dataset_name,
                    execution_id=execution_id,
                    records_processed=report["total_records"],
                    database_path=execution["database_path"]
                )
            }

            print("\n========== FILE REGISTRY UPDATE ==========")
            print("File:", file_path.name)
            print("SHA-256:", file_hash)
            print("Registry status:", registry_result["status"])
            print("Registration successful.")

        except Exception as registry_error:

            registry_result = {
                "status": "REGISTRATION_FAILED",
                "error": str(registry_error)
            }

            print(
                "\nWARNING: Pipeline succeeded, but file "
                "registry registration failed."
            )

            print("Registry error:", registry_error)

        # ====================================================
        # FINAL PIPELINE SUMMARY
        # ====================================================

        print("\n")
        print("=" * 60)
        print("       UNIVERSAL ETL PIPELINE COMPLETED")
        print("=" * 60)

        print(f"Dataset: {dataset_name}")
        print(f"Execution ID: {execution_id}")
        print(f"Execution status: {execution_result['status']}")

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

        print(f"Database table: {database_result['table_name']}")

        print(
            "Profiling status:",
            profiling_result["status"]
        )

        print(
            "File registry status:",
            registry_result["status"]
        )

        if profiling_result["profiling_report"] is not None:

            print(
                "Profiling report:",
                profiling_result["profiling_report"]
            )

        print("\nExecution and retry history saved successfully.")

        return {
            "dataset": dataset_name,
            "status": execution_result["status"],
            "execution_id": execution_id,
            "quality_report": report,
            "database": database_result,
            "files": report_files,
            "profiling_status": profiling_result["status"],
            "profiling_report": profiling_result["profiling_report"],
            "file_registry": registry_result
        }

    # ========================================================
    # FAILURE HANDLING
    # ========================================================

    except Exception as error:

        failed_stage = execution.get("current_stage")

        print("\n========== PIPELINE EXECUTION FAILED ==========")
        print(f"Execution ID: {execution_id}")
        print(f"Failed stage: {failed_stage}")
        print(f"Exception type: {type(error).__name__}")
        print(f"Error: {error}")

        try:

            fail_execution(
                execution,
                failed_stage=failed_stage,
                error_message=error,
                **get_record_counts()
            )

            print(
                "Complete execution failure diagnostics saved."
            )

        except Exception as tracking_error:

            print(
                "WARNING: Execution failure tracking failed:",
                tracking_error
            )

        # Failed files are deliberately NOT registered.

        print(
            "File registry unchanged: failed executions "
            "are not registered."
        )

        raise
