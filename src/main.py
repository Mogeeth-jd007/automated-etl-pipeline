
import argparse
import sys

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from universal.universal_pipeline import run_universal_pipeline
from universal.batch_processor import run_batch_pipeline

from extract import extract_data
from transform import transform_data

from validate import (
    validate_data,
    classify_records,
    separate_records,
    save_validation_results
)

from load import load_data

from config import load_config, load_dataset_config
from logger import get_logger


logger = get_logger("MAIN")


def run_pipeline(dataset_name=None, input_file=None):

    try:

        config = load_config()

        if dataset_name is None:
            dataset_name = config["active_dataset"]

        dataset_config = load_dataset_config(dataset_name)

        logger.info("========== ETL PIPELINE STARTED ==========")
        logger.info("Selected dataset: %s", dataset_name)

        # STEP 1: EXTRACT

        logger.info("STEP 1: EXTRACT")

        df = extract_data(
            filename=input_file,
            dataset_name=dataset_name
        )

        logger.info("Extraction completed successfully")

        # STEP 2: TRANSFORM

        logger.info("STEP 2: TRANSFORM")

        transformed_df = transform_data(
            df,
            dataset_name=dataset_name
        )

        logger.info("Transformation completed successfully")

        # STEP 3: VALIDATE

        logger.info("STEP 3: VALIDATE")

        validate_data(
            transformed_df,
            dataset_name=dataset_name
        )

        logger.info("Validation completed successfully")

        # STEP 4: CLASSIFY

        logger.info("STEP 4: CLASSIFY")

        classified_df = classify_records(
            transformed_df,
            dataset_name=dataset_name
        )

        logger.info("Classification completed successfully")

        # STEP 5: SEPARATE RECORDS

        logger.info("STEP 5: SEPARATE RECORDS")

        valid_records, warning_records, rejected_records = (
            separate_records(classified_df)
        )

        logger.info(
            "Record separation completed: Valid=%s, Warnings=%s, Rejected=%s",
            len(valid_records),
            len(warning_records),
            len(rejected_records)
        )

        # STEP 6: SAVE VALIDATION RESULTS

        logger.info("STEP 6: SAVE VALIDATION FILES")

        save_validation_results(
            valid_records,
            warning_records,
            rejected_records,
            dataset_name=dataset_name
        )

        logger.info("Validation files saved successfully")

        # STEP 7: LOAD ELIGIBLE RECORDS

        logger.info("STEP 7: LOAD")

        records_to_load = pd.concat(
            [valid_records, warning_records],
            ignore_index=True
        )

        records_to_load = records_to_load.drop(
            columns=["status"],
            errors="ignore"
        )

        date_columns = dataset_config["transformation"].get(
            "date_columns",
            []
        )

        for column in date_columns:

            if column in records_to_load.columns:
                records_to_load[column] = (
                    records_to_load[column].astype(str)
                )

        load_data(
            records_to_load,
            dataset_name=dataset_name
        )

        logger.info("Loading completed successfully")

        logger.info(
            "========== ETL PIPELINE COMPLETED SUCCESSFULLY =========="
        )

    except Exception:

        logger.exception("ETL PIPELINE FAILED")
        raise


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Universal Automated ETL Pipeline"
    )

    execution_mode = parser.add_mutually_exclusive_group()

    execution_mode.add_argument(
        "--dataset",
        choices=["retail", "employee", "student"],
        default=None,
        help="Run the existing dataset-specific ETL pipeline"
    )

    execution_mode.add_argument(
        "--file",
        default=None,
        help="Run universal ETL on a single CSV file"
    )

    execution_mode.add_argument(
        "--batch",
        action="store_true",
        help="Automatically process all CSV files in data/raw"
    )

    args = parser.parse_args()

    if args.batch:

        run_batch_pipeline()

    elif args.file:

        run_universal_pipeline(args.file)

    else:

        run_pipeline(
            dataset_name=args.dataset
        )
