import pytest

from taggen.config import load_config

VALID = """
name: John
last-name: Doe
qr_action: "Wa"
phone_number: "+5511999999999"
email: "john.doe@example.com"
"""


def write(tmp_path, text):
    path = tmp_path / "config.yaml"
    path.write_text(text)
    return str(path)


def test_loads_valid_config(tmp_path):
    config = load_config(write(tmp_path, VALID))
    assert config["name"] == "John"
    assert config["last-name"] == "Doe"
    assert config["qr_action"] == "Wa"


def test_applies_defaults(tmp_path):
    config = load_config(write(tmp_path, VALID))
    assert config["template"] == "scripts/dados-tag.scad"
    assert config["output_dir"] == "output/stl"


def test_output_name_derived_from_name(tmp_path):
    config = load_config(write(tmp_path, VALID))
    assert config["output_name"] == "john-doe"


def test_keeps_explicit_values_over_defaults(tmp_path):
    text = VALID + '\noutput_dir: "build"\noutput_name: "john"\n'
    config = load_config(write(tmp_path, text))
    assert config["output_dir"] == "build"
    assert config["output_name"] == "john"


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(str(tmp_path / "nope.yaml"))


def test_missing_required_field_raises(tmp_path):
    text = 'name: A\nlast-name: B\nqr_action: "Wa"\nemail: "a@b.com"\n'
    with pytest.raises(ValueError) as exc:
        load_config(write(tmp_path, text))
    assert "phone_number" in str(exc.value)


def test_missing_name_raises(tmp_path):
    text = 'last-name: "Doe"\nqr_action: "Wa"\nphone_number: "+5511999999999"\nemail: "a@b.com"\n'
    with pytest.raises(ValueError) as exc:
        load_config(write(tmp_path, text))
    assert "name" in str(exc.value)
