import hashlib
import sqlite3

from contextlib import closing
from pathlib import Path

from datetime import datetime, timezone


PROJECT_ROOT = Path(__file__).resolve().parents[2]
def calculate_file_hash(file_path):
    """
    Calculate the SHA-256 fingerprint of a file.

    Reads the file in chunks to support large datasets.
    """

    file_path = Path(file_path)

    if not file_path.is_file():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:

        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b""
        ):

            sha256.update(chunk)

    return sha256.hexdigest()

def get_database_path(database_path=None):

    if database_path is None:

        return (
            PROJECT_ROOT
            / "data"
            / "universal_pipeline.db"
        )

    path = Path(database_path)

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    return path


def initialize_processing_registry(database_path=None):
    """Create the persistent file processing history."""

    database_path = get_database_path(database_path)

    database_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with closing(sqlite3.connect(database_path)) as connection:

        with connection:

            connection.execute("""
                CREATE TABLE IF NOT EXISTS file_processing_history (

                    file_hash TEXT PRIMARY KEY,

                    file_name TEXT NOT NULL,

                    dataset_name TEXT NOT NULL,

                    execution_id TEXT,

                    records_processed INTEGER DEFAULT 0,

                    processed_at TEXT NOT NULL

                )
            """)

    return str(database_path)


def is_file_processed(file_hash, database_path=None):
    """Check whether a fingerprint already exists."""

    database_path = get_database_path(database_path)

    initialize_processing_registry(database_path)

    with closing(sqlite3.connect(database_path)) as connection:

        result = connection.execute(
            """
            SELECT 1
            FROM file_processing_history
            WHERE file_hash = ?
            """,
            (file_hash,)
        ).fetchone()

    return result is not None


def record_processed_file(
    file_hash,
    file_name,
    dataset_name,
    execution_id=None,
    records_processed=0,
    database_path=None
):
    """Register a successfully processed file."""

    if not file_hash or len(file_hash) != 64:
        raise ValueError(
            "A valid SHA-256 fingerprint is required."
        )

    if records_processed < 0:
        raise ValueError(
            "Record count cannot be negative."
        )

    database_path = get_database_path(database_path)

    initialize_processing_registry(database_path)

    processed_at = datetime.now(
        timezone.utc
    ).isoformat()

    with closing(sqlite3.connect(database_path)) as connection:

        with connection:

            connection.execute(
                """
                INSERT INTO file_processing_history (
                    file_hash,
                    file_name,
                    dataset_name,
                    execution_id,
                    records_processed,
                    processed_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    file_hash,
                    file_name,
                    dataset_name,
                    execution_id,
                    records_processed,
                    processed_at
                )
            )

    return True
