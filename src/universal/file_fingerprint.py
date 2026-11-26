
import hashlib

from pathlib import Path


def calculate_file_hash(file_path, chunk_size=65536):
    """
    Calculate the SHA-256 fingerprint of a file.

    Reads the file in chunks to avoid loading
    the entire file into memory.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    if not file_path.is_file():
        raise ValueError(
            f"Expected a file: {file_path}"
        )

    if chunk_size <= 0:
        raise ValueError(
            "Chunk size must be greater than zero."
        )

    sha256_hash = hashlib.sha256()

    with file_path.open("rb") as file:

        while True:

            chunk = file.read(chunk_size)

            if not chunk:
                break

            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()
