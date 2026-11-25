
import pytest

from universal.universal_extract import (
    extract_universal,
    validate_extraction_config
)


def test_default_configuration_preserves_automatic_detection():

    settings = validate_extraction_config()

    assert settings == {
        "encoding": "auto",
        "delimiter": "auto",
        "header": True,
        "on_bad_lines": "error"
    }


def test_explicit_delimiter(tmp_path):

    file = tmp_path / "semicolon.csv"

    file.write_text(
        "Name;Age\nArun;25\n",
        encoding="utf-8"
    )

    df = extract_universal(
        file,
        config={
            "encoding": "utf-8",
            "delimiter": ";"
        }
    )

    assert df.shape == (1, 2)
    assert df.iloc[0]["Name"] == "Arun"


def test_explicit_encoding(tmp_path):

    file = tmp_path / "encoded.csv"

    file.write_text(
        "Name,Age\nAndré,25\n",
        encoding="cp1252"
    )

    df = extract_universal(
        file,
        config={
            "encoding": "cp1252",
            "delimiter": ","
        }
    )

    assert df.iloc[0]["Name"] == "André"


def test_headerless_csv(tmp_path):

    file = tmp_path / "headerless.csv"

    file.write_text(
        "Arun,25\nMeena,30\n",
        encoding="utf-8"
    )

    df = extract_universal(
        file,
        config={
            "header": False,
            "delimiter": ","
        }
    )

    assert df.shape == (2, 2)

    assert df.columns.tolist() == [
        "column_1",
        "column_2"
    ]

    assert df.iloc[0]["column_1"] == "Arun"
    assert df.iloc[1]["column_2"] == "30"


def test_invalid_encoding_is_rejected():

    with pytest.raises(ValueError, match="Unsupported encoding"):

        validate_extraction_config({
            "encoding": "unknown-encoding"
        })


def test_invalid_delimiter_is_rejected():

    with pytest.raises(ValueError, match="Unsupported delimiter"):

        validate_extraction_config({
            "delimiter": "::"
        })


def test_invalid_header_setting_is_rejected():

    with pytest.raises(ValueError, match="header must be a boolean"):

        validate_extraction_config({
            "header": "yes"
        })


def test_unsupported_bad_line_policy_is_rejected():

    with pytest.raises(ValueError, match="Only on_bad_lines"):

        validate_extraction_config({
            "on_bad_lines": "skip"
        })


def test_config_must_be_dictionary():

    with pytest.raises(ValueError, match="must be a dictionary"):

        validate_extraction_config("invalid")


def test_configured_malformed_csv_is_still_rejected(tmp_path):

    file = tmp_path / "malformed.csv"

    file.write_text(
        "Name,Age\nArun,25,Chennai\n",
        encoding="utf-8"
    )

    with pytest.raises(ValueError, match="Malformed CSV"):

        extract_universal(
            file,
            config={
                "encoding": "utf-8",
                "delimiter": ",",
                "header": True,
                "on_bad_lines": "error"
            }
        )
