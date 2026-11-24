import pytest

from universal.universal_extract import extract_universal
from universal.schema_detector import detect_schema


def test_valid_csv(tmp_path):
    file = tmp_path / "valid.csv"
    file.write_text(
        "Name,Age\nArun,25\nMeena,30\n",
        encoding="utf-8"
    )

    df = extract_universal(file)

    assert df.shape == (2, 2)
    assert df.columns.tolist() == ["Name", "Age"]


@pytest.mark.parametrize("delimiter", [",", ";", "|", "\t"])
def test_delimiter_detection(tmp_path, delimiter):
    file = tmp_path / "delimiter.csv"
    file.write_text(
        f"Name{delimiter}Age\nArun{delimiter}25\n",
        encoding="utf-8"
    )

    df = extract_universal(file)

    assert df.shape == (1, 2)
    assert df.iloc[0]["Name"] == "Arun"


@pytest.mark.parametrize(
    "encoding",
    ["utf-8", "utf-8-sig", "utf-16", "cp1252", "latin-1"]
)
def test_encoding_detection(tmp_path, encoding):
    file = tmp_path / "encoding.csv"
    file.write_text(
        "Name,Age\nAndr\u00e9,25\n",
        encoding=encoding
    )

    df = extract_universal(file)

    assert df.iloc[0]["Name"] == "Andr\u00e9"


def test_empty_csv(tmp_path):
    file = tmp_path / "empty.csv"
    file.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="empty"):
        extract_universal(file)


def test_whitespace_csv(tmp_path):
    file = tmp_path / "whitespace.csv"
    file.write_text("   \n   ", encoding="utf-8")

    with pytest.raises(ValueError):
        extract_universal(file)


def test_header_only_csv(tmp_path):
    file = tmp_path / "header_only.csv"
    file.write_text("Name,Age\n", encoding="utf-8")

    with pytest.raises(ValueError, match="no records"):
        extract_universal(file)


def test_extra_columns(tmp_path):
    file = tmp_path / "extra_columns.csv"
    file.write_text(
        "Name,Age\nArun,25,Chennai\n",
        encoding="utf-8"
    )

    with pytest.raises(ValueError, match="Malformed CSV"):
        extract_universal(file)


def test_missing_columns(tmp_path):
    file = tmp_path / "missing_columns.csv"
    file.write_text(
        "Name,Age,City\nArun,25\n",
        encoding="utf-8"
    )

    with pytest.raises(ValueError, match="Malformed CSV"):
        extract_universal(file)


def test_invalid_quotes(tmp_path):
    file = tmp_path / "invalid_quotes.csv"
    file.write_text(
        'Name,Age\n"Arun,25\n',
        encoding="utf-8"
    )

    with pytest.raises(ValueError):
        extract_universal(file)


def test_empty_header(tmp_path):
    file = tmp_path / "empty_header.csv"
    file.write_text(
        "Product ID,,Price\n001,Laptop,45000\n",
        encoding="utf-8"
    )

    df = extract_universal(file)
    standardized, schema = detect_schema(df)

    assert standardized.columns.tolist() == [
        "product_id", "column_2", "price"
    ]


def test_duplicate_headers(tmp_path):
    file = tmp_path / "duplicate_headers.csv"
    file.write_text(
        "Name,Name,Price\nArun,Laptop,45000\n",
        encoding="utf-8"
    )

    df = extract_universal(file)
    standardized, schema = detect_schema(df)

    assert standardized.columns.tolist() == [
        "name", "name_2", "price"
    ]


def test_blank_headers(tmp_path):
    file = tmp_path / "blank_headers.csv"
    file.write_text(
        ",,\n001,Laptop,45000\n",
        encoding="utf-8"
    )

    with pytest.raises(ValueError, match="blank headers"):
        extract_universal(file)


def test_identifier_preservation(tmp_path):
    file = tmp_path / "identifiers.csv"
    file.write_text(
        "Product ID,SKU,Phone Number\n"
        "00101,000245,0987654321\n",
        encoding="utf-8"
    )

    df = extract_universal(file)

    assert df.iloc[0]["Product ID"] == "00101"
    assert df.iloc[0]["SKU"] == "000245"
    assert df.iloc[0]["Phone Number"] == "0987654321"


def test_literal_na_preservation(tmp_path):
    file = tmp_path / "literal_na.csv"
    file.write_text(
        "Code,Description\nNA,Unknown\n",
        encoding="utf-8"
    )

    df = extract_universal(file)

    assert df.iloc[0]["Code"] == "NA"


def test_missing_file(tmp_path):
    file = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError):
        extract_universal(file)


def test_unsupported_file_type(tmp_path):
    file = tmp_path / "unsupported.txt"
    file.write_text(
        "Name,Age\nArun,25\n",
        encoding="utf-8"
    )

    with pytest.raises(ValueError, match="CSV files only"):
        extract_universal(file)


def test_exception_logging(tmp_path, caplog):
    file = tmp_path / "empty.csv"
    file.write_text("", encoding="utf-8")

    with pytest.raises(ValueError):
        extract_universal(file)

    assert "UNIVERSAL EXTRACTION FAILED" in caplog.text
