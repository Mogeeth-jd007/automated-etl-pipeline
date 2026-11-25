
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
    "utf-16",
    "cp1252",
    "latin-1"
]

SUPPORTED_DELIMITERS = ",;\t|"


def validate_extraction_config(config=None):
    """Validate universal extraction configuration."""

    if config is None:
        config = {}

    if not isinstance(config, dict):
        raise ValueError(
            "Universal extraction configuration must be a dictionary."
        )

    encoding = config.get("encoding", "auto")
    delimiter = config.get("delimiter", "auto")
    header = config.get("header", True)
    on_bad_lines = config.get("on_bad_lines", "error")

    if not isinstance(encoding, str):
        raise ValueError("encoding must be a string.")

    if (
        encoding != "auto"
        and encoding not in SUPPORTED_ENCODINGS
    ):
        raise ValueError(
            f"Unsupported encoding: {encoding}"
        )

    if not isinstance(delimiter, str):
        raise ValueError("delimiter must be a string.")

    if (
        delimiter != "auto"
        and delimiter not in SUPPORTED_DELIMITERS
    ):
        raise ValueError(
            f"Unsupported delimiter: {delimiter!r}"
        )

    if not isinstance(header, bool):
        raise ValueError("header must be a boolean.")

    if on_bad_lines != "error":
        raise ValueError(
            "Only on_bad_lines='error' is currently supported "
            "because strict CSV structure validation is enabled."
        )

    return {
        "encoding": encoding,
        "delimiter": delimiter,
        "header": header,
        "on_bad_lines": on_bad_lines
    }


def detect_encoding(file_path):
    """Detect a compatible encoding for the CSV file."""

    file_path = Path(file_path)
    raw_data = file_path.read_bytes()

    if raw_data.startswith((b"\xff\xfe", b"\xfe\xff")):
        raw_data.decode("utf-16")
        return "utf-16"

    for encoding in SUPPORTED_ENCODINGS:

        if encoding == "utf-16":
            continue

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


def validate_csv_structure(
    file_path,
    encoding,
    delimiter,
    has_header=True
):
    """Validate CSV structure and generate column names if needed."""

    expected_columns = None
    headers = None
    data_row_count = 0

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

                if headers is None and has_header:

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

                if expected_columns is None:
                    expected_columns = len(row)

                if len(row) != expected_columns:

                    raise ValueError(
                        f"Malformed CSV at line "
                        f"{reader.line_num}: "
                        f"expected {expected_columns} columns, "
                        f"found {len(row)}"
                    )

                data_row_count += 1

    except csv.Error as error:

        raise ValueError(
            f"Invalid CSV structure in "
            f"{Path(file_path).name}: {error}"
        ) from error

    if has_header:

        if headers is None:

            raise ValueError(
                f"CSV file contains no readable data: "
                f"{Path(file_path).name}"
            )

        return headers

    if expected_columns is None:

        raise ValueError(
            f"CSV file contains no readable data: "
            f"{Path(file_path).name}"
        )

    if data_row_count == 0:

        raise ValueError(
            f"CSV file contains no records: "
            f"{Path(file_path).name}"
        )

    return [
        f"column_{index}"
        for index in range(1, expected_columns + 1)
    ]


def extract_universal(file_path, config=None):
    """Extract CSV data using configurable extraction settings."""

    try:

        file_path = Path(file_path)

        settings = validate_extraction_config(config)

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

        # STEP 1: Encoding.

        if settings["encoding"] == "auto":

            encoding = detect_encoding(file_path)

        else:

            encoding = settings["encoding"]

            # Verify that the configured encoding can decode the file.

            try:

                file_path.read_bytes().decode(encoding)

            except UnicodeDecodeError as error:

                raise ValueError(
                    f"File cannot be decoded using configured "
                    f"encoding: {encoding}"
                ) from error

        # STEP 2: Delimiter.

        if settings["delimiter"] == "auto":

            delimiter = detect_delimiter(
                file_path,
                encoding
            )

        else:

            delimiter = settings["delimiter"]

        logger.info("Encoding: %s", encoding)
        logger.info("Delimiter: %r", delimiter)
        logger.info("Header enabled: %s", settings["header"])

        # STEP 3: Validate structure.

        original_headers = validate_csv_structure(
            file_path,
            encoding,
            delimiter,
            has_header=settings["header"]
        )

        # STEP 4: Read CSV.

        try:

            if settings["header"]:

                df = pd.read_csv(
                    file_path,
                    encoding=encoding,
                    sep=delimiter,
                    dtype="string",
                    keep_default_na=False,
                    on_bad_lines=settings["on_bad_lines"]
                )

            else:

                df = pd.read_csv(
                    file_path,
                    encoding=encoding,
                    sep=delimiter,
                    header=None,
                    names=original_headers,
                    dtype="string",
                    keep_default_na=False,
                    on_bad_lines=settings["on_bad_lines"]
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

        # Preserve original or generated column names.

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

