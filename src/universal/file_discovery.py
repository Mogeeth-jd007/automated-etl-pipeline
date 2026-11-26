
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def discover_csv_files(input_directory, recursive=False):
    """
    Discover CSV files inside a specified directory.

    Args:
        input_directory: Directory containing CSV files.
        recursive: Whether to search subdirectories.

    Returns:
        A sorted list of discovered CSV file paths.
    """

    directory = Path(input_directory)

    # Resolve relative paths using the project root.
    if not directory.is_absolute():
        directory = PROJECT_ROOT / directory

    directory = directory.resolve()

    # Verify that the input directory exists.
    if not directory.exists():
        raise FileNotFoundError(
            f"Input directory not found: {directory}"
        )

    # Verify that the supplied path is a directory.
    if not directory.is_dir():
        raise NotADirectoryError(
            f"Expected a directory: {directory}"
        )

    # Discover CSV files.
    if recursive:
        candidates = directory.rglob("*")
    else:
        candidates = directory.glob("*")

    csv_files = [
        file
        for file in candidates
        if file.is_file()
        and file.suffix.lower() == ".csv"
    ]

    # Return files in deterministic alphabetical order.
    return sorted(
        csv_files,
        key=lambda file: file.name.casefold()
    )
