import io
import os

import pytest

from taggen.configselect import (
    config_name,
    list_tag_configs,
    prompt_tag_config,
    resolve_config,
)


def write_configs(configs_dir, *names):
    os.makedirs(configs_dir, exist_ok=True)
    for name in names:
        with open(os.path.join(configs_dir, name), "w") as fh:
            fh.write("")
    return configs_dir


# ---- config_name ------------------------------------------------------------


def test_config_name_strips_dir_and_suffix():
    assert config_name("/a/b/config-john-doe.yaml") == "config-john-doe"


# ---- list_tag_configs -------------------------------------------------------


def test_list_tag_configs_returns_sorted_config_yaml(tmp_path):
    configs_dir = write_configs(
        str(tmp_path / "configs"), "config.yaml", "config-john-doe.yaml"
    )
    paths = list_tag_configs(configs_dir)
    assert [os.path.basename(p) for p in paths] == [
        "config-john-doe.yaml",
        "config.yaml",
    ]


def test_list_tag_configs_ignores_non_config_yaml(tmp_path):
    configs_dir = write_configs(
        str(tmp_path / "configs"), "config.yaml", "notes.yaml", "config.txt"
    )
    paths = list_tag_configs(configs_dir)
    assert [os.path.basename(p) for p in paths] == ["config.yaml"]


def test_list_tag_configs_missing_dir_returns_empty(tmp_path):
    assert list_tag_configs(str(tmp_path / "nope")) == []


# ---- prompt_tag_config ------------------------------------------------------


def test_prompt_tag_config_selects_by_number(tmp_path, monkeypatch):
    configs = list_tag_configs(
        write_configs(str(tmp_path / "configs"), "config.yaml", "config-b.yaml")
    )
    monkeypatch.setattr("sys.stdin", io.StringIO("1\n"))
    assert prompt_tag_config(configs) == configs[0]


def test_prompt_tag_config_selects_by_name(tmp_path, monkeypatch):
    configs = list_tag_configs(
        write_configs(str(tmp_path / "configs"), "config.yaml", "config-b.yaml")
    )
    monkeypatch.setattr("sys.stdin", io.StringIO("config-b\n"))
    chosen = prompt_tag_config(configs)
    assert config_name(chosen) == "config-b"


def test_prompt_tag_config_reasks_on_invalid(tmp_path, monkeypatch):
    configs = list_tag_configs(
        write_configs(str(tmp_path / "configs"), "config.yaml", "config-b.yaml")
    )
    monkeypatch.setattr("sys.stdin", io.StringIO("nope\n1\n"))
    assert prompt_tag_config(configs) == configs[0]


def test_prompt_tag_config_raises_on_closed_stdin(tmp_path, monkeypatch):
    configs = list_tag_configs(
        write_configs(str(tmp_path / "configs"), "config.yaml")
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    with pytest.raises(ValueError):
        prompt_tag_config(configs)


# ---- resolve_config ---------------------------------------------------------


def test_resolve_config_uses_existing_file_directly(tmp_path):
    path = tmp_path / "anywhere.yaml"
    path.write_text("")
    assert resolve_config(str(path), str(tmp_path / "configs")) == str(path)


def test_resolve_config_matches_by_name(tmp_path):
    configs_dir = write_configs(
        str(tmp_path / "configs"), "config.yaml", "config-john-doe.yaml"
    )
    resolved = resolve_config("config-john-doe", configs_dir)
    assert config_name(resolved) == "config-john-doe"


def test_resolve_config_unknown_name_raises(tmp_path):
    configs_dir = write_configs(str(tmp_path / "configs"), "config.yaml")
    with pytest.raises(ValueError):
        resolve_config("missing", configs_dir)


def test_resolve_config_no_arg_prompts(tmp_path, monkeypatch):
    configs_dir = write_configs(
        str(tmp_path / "configs"), "config.yaml", "config-b.yaml"
    )
    monkeypatch.setattr("sys.stdin", io.StringIO("1\n"))
    resolved = resolve_config(None, configs_dir)
    assert resolved == list_tag_configs(configs_dir)[0]


def test_resolve_config_no_arg_no_configs_raises(tmp_path):
    with pytest.raises(ValueError):
        resolve_config(None, str(tmp_path / "empty"))
