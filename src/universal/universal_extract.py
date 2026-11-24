import csv
from pathlib import Path

import pandas as pd

if __package__ == "src.universal":
    from src.logger import get_logger
else:
    from logger import get_logger


logger = get_logger("UNIVERSAL_EXTRACT")

SUPPORTED_ENCODINGS = [
    "utf-8-sig",
    "utf-8",
    "cp1252",
    "latin-1"
]

SUPPORTED_DELIMITERS = ",;\t|"


def detect_encoding(file_path):
    """Detect a compatible encoding for the CSV file."""

    file_path = Path(file_path)
    raw_data = file_path.read_bytes()

    if raw_data.startswith((b"\xff\xfe", b"\xfe\xff")):
        raw_data.decode("utf-16")
        return "utf-16"

    for encoding in SUPPORTED_ENCODINGS:
        try:
            raw_data.decode(encoding)
            return encoding

        except UnicodeDecodeError:
            logger.debug(
                "Encoding attempt failed: %s",
                encoding
            )

    raise ValueError(
        f"Unable to detect file encoding: {file_path}"
    )


def detect_delimiter(file_path, encoding):
    """Automatically detect the CSV delimiter."""

    with open(
        file_path,
        mode="r",
        encoding=encoding,
        newline=""
    ) as file:

        sample = file.read(8192)

    try:
        dialect = csv.Sniffer().sniff(
            sample,
            delimiters=SUPPORTED_DELIMITERS
        )

        return dialect.delimiter

    except csv.Error:
        logger.warning(
            "Delimiter detection failed. "
            "Using comma as fallback."
        )

        return ","


def validate_csv_structure(file_path, encoding, delimiter):
    """Validate CSV structure and preserve original headers."""

    expected_columns = None
    headers = None

    try:
        with open(
            file_path,
            mode="r",
            encoding=encoding,
            newline=""
        ) as file:

            reader = csv.reader(
                file,
                delimiter=delimiter,
                strict=True
            )

            for row in reader:

                if not row or (
                    len(row) == 1 and not row[0].strip()
                ):
                    continue

                if headers is None:

                    headers = row
                    expected_columns = len(row)

                    if all(
                        not header.strip()
                        for header in headers
                    ):
                        raise ValueError(
                            "CSV contains entirely blank headers"
                        )

                    continue

                if len(row) != expected_columns:

                    raise ValueError(
                        f"Malformed CSV at line "
                        f"{reader.line_num}: "
                        f"expected {expected_columns} columns, "
                        f"found {len(row)}"
                    )

    except csv.Error as error:

        raise ValueError(
            f"Invalid CSV structure in "
            f"{Path(file_path).name}: {error}"
        ) from error

    if headers is None:

        raise ValueError(
            f"CSV file contains no readable data: "
            f"{Path(file_path).name}"
        )

    logger.info("CSV structure validation successful")

    return headers


def extract_universal(file_path):
    """Extract CSV data while preserving original values."""

    try:
        file_path = Path(file_path)

        logger.info(
            "========== UNIVERSAL EXTRACTION STARTED =========="
        )

        logger.info("Input file: %s", file_path)

        if not file_path.is_file():

            raise FileNotFoundError(
                f"CSV file not found: {file_path}"
            )

        if file_path.suffix.lower() != ".csv":

            raise ValueError(
                "Universal extraction accepts CSV files only."
            )

        if file_path.stat().st_size == 0:

            raise ValueError(
                f"CSV file is empty: {file_path.name}"
            )

        encoding = detect_encoding(file_path)

        delimiter = detect_delimiter(
            file_path,
            encoding
        )

        logger.info("Detected encoding: %s", encoding)
        logger.info("Detected delimiter: %r", delimiter)

        original_headers = validate_csv_structure(
            file_path,
            encoding,
            delimiter
        )

        try:
            df = pd.read_csv(
                file_path,
                encoding=encoding,
                sep=delimiter,
                dtype="string",
                keep_default_na=False,
                on_bad_lines="error"
            )

        except pd.errors.EmptyDataError as error:

            raise ValueError(
                f"CSV file contains no readable data: "
                f"{file_path.name}"
            ) from error

        except pd.errors.ParserError as error:

            raise ValueError(
                f"Unable to parse CSV file: "
                f"{file_path.name}"
            ) from error

        if df.empty:

            raise ValueError(
                f"CSV file contains no records: "
                f"{file_path.name}"
            )

        df.columns = original_headers

        logger.info("Records extracted: %s", len(df))
        logger.info("Columns extracted: %s", len(df.columns))

        logger.info(
            "========== UNIVERSAL EXTRACTION COMPLETED =========="
        )

        return df

    except Exception:

        logger.exception("UNIVERSAL EXTRACTION FAILED")

        raise