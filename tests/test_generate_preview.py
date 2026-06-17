"""Tests for the generate-preview.py interactive menu helpers.

The module name has a hyphen, so it is loaded by path via importlib.
"""

import importlib.util
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_generate_preview():
    path = os.path.join(ROOT, "generate-preview.py")
    spec = importlib.util.spec_from_file_location("generate_preview", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---- ensure_tag_stl ---------------------------------------------------------


def test_ensure_tag_stl_generates_when_missing(tmp_path, monkeypatch):
    module = load_generate_preview()
    tag = tmp_path / "tag.stl"
    calls = []

    def fake_tag(argv, openscad, runner):
        calls.append((argv, openscad, runner))
        tag.write_text("STL")

    monkeypatch.setattr(module, "run_generate_tag", fake_tag)
    ns = module.parse_args(["--tag", str(tag)])
    module.ensure_tag_stl(ns, "oscad", "RUNNER")

    assert len(calls) == 1
    # The resolved openscad and runner are threaded through to generate-tag.
    assert calls[0][1] == "oscad"
    assert calls[0][2] == "RUNNER"


def test_ensure_tag_stl_skips_when_present(tmp_path, monkeypatch):
    module = load_generate_preview()
    tag = tmp_path / "tag.stl"
    tag.write_text("already here")
    called = []
    monkeypatch.setattr(
        module, "run_generate_tag", lambda *a, **k: called.append(a)
    )
    ns = module.parse_args(["--tag", str(tag)])
    module.ensure_tag_stl(ns, "oscad", "RUNNER")

    assert called == []


def test_ensure_tag_stl_passes_config_when_file_exists(tmp_path, monkeypatch):
    module = load_generate_preview()
    tag = tmp_path / "tag.stl"
    config = tmp_path / "config-x.yaml"
    config.write_text("dummy: true\n")
    captured = {}

    def fake_tag(argv, openscad, runner):
        captured["argv"] = argv
        tag.write_text("STL")

    monkeypatch.setattr(module, "run_generate_tag", fake_tag)
    ns = module.parse_args(["--tag", str(tag), "--config", str(config)])
    module.ensure_tag_stl(ns, "oscad", "RUNNER")

    assert captured["argv"] == [str(config)]


def test_ensure_tag_stl_no_config_arg_when_file_absent(tmp_path, monkeypatch):
    module = load_generate_preview()
    tag = tmp_path / "tag.stl"
    captured = {}

    def fake_tag(argv, openscad, runner):
        captured["argv"] = argv
        tag.write_text("STL")

    monkeypatch.setattr(module, "run_generate_tag", fake_tag)
    # --config points at a non-existent file (mirrors the missing default
    # configs/config.yaml): generate-tag is invoked with no config so it shows
    # its own menu.
    ns = module.parse_args(
        ["--tag", str(tag), "--config", str(tmp_path / "nope.yaml")]
    )
    module.ensure_tag_stl(ns, "oscad", "RUNNER")

    assert captured["argv"] == []


def test_ensure_tag_stl_raises_if_still_missing(tmp_path, monkeypatch):
    module = load_generate_preview()
    tag = tmp_path / "tag.stl"
    # generate-tag "runs" but produces nothing where preview expects it.
    monkeypatch.setattr(module, "run_generate_tag", lambda *a, **k: None)
    ns = module.parse_args(["--tag", str(tag)])
    with pytest.raises(FileNotFoundError):
        module.ensure_tag_stl(ns, "oscad", "RUNNER")


# ---- ensure_icon_stls -------------------------------------------------------


def test_ensure_icon_stls_generates_missing_requested(tmp_path, monkeypatch):
    module = load_generate_preview()
    icons_dir = tmp_path / "stl"
    icons_dir.mkdir()
    (icons_dir / "world.stl").write_text("present")
    captured = {}
    monkeypatch.setattr(
        module,
        "run_generate_icons",
        lambda argv, openscad, runner: captured.update(argv=argv),
    )
    ns = module.parse_args(
        ["world", "travel", "--icons-dir", str(icons_dir)]
    )
    module.ensure_icon_stls(ns, "oscad", "RUNNER")

    # Only the missing stem is rendered; the present one is left alone.
    assert captured["argv"] == ["travel"]


def test_ensure_icon_stls_skips_when_all_present(tmp_path, monkeypatch):
    module = load_generate_preview()
    icons_dir = tmp_path / "stl"
    icons_dir.mkdir()
    (icons_dir / "world.stl").write_text("present")
    called = []
    monkeypatch.setattr(
        module, "run_generate_icons", lambda *a, **k: called.append(a)
    )
    ns = module.parse_args(["world", "--icons-dir", str(icons_dir)])
    module.ensure_icon_stls(ns, "oscad", "RUNNER")

    assert called == []


def test_ensure_icon_stls_all_default_uses_svg_source(tmp_path, monkeypatch):
    module = load_generate_preview()
    src = tmp_path / "svg"
    src.mkdir()
    (src / "world.svg").write_text("<svg/>")
    (src / "travel.svg").write_text("<svg/>")
    (src / "notes.txt").write_text("ignore")
    icons_dir = tmp_path / "stl"
    icons_dir.mkdir()
    (icons_dir / "world.stl").write_text("present")
    monkeypatch.setattr(module, "ICONS_SRC", str(src))
    captured = {}
    monkeypatch.setattr(
        module,
        "run_generate_icons",
        lambda argv, openscad, runner: captured.update(argv=argv),
    )
    ns = module.parse_args(["--icons-dir", str(icons_dir)])
    module.ensure_icon_stls(ns, "oscad", "RUNNER")

    # Stems come from the SVG sources; only the un-rendered one is generated.
    assert captured["argv"] == ["travel"]


# ---- previews_dirs ----------------------------------------------------------


def test_previews_dirs_splits_icons_and_tags(tmp_path):
    module = load_generate_preview()
    icons, tags = module.previews_dirs(str(tmp_path))
    assert icons == os.path.join(str(tmp_path), "icons")
    assert tags == os.path.join(str(tmp_path), "tags")


def test_run_icons_mode_routes_to_icons_and_tags_dirs(tmp_path, monkeypatch):
    module = load_generate_preview()
    captured = []
    monkeypatch.setattr(module, "ensure_icon_stls", lambda ns, o, r: None)
    monkeypatch.setattr(module, "select_icons", lambda d, req: ["/x/travel.stl"])
    monkeypatch.setattr(
        module, "render_info_stl", lambda c, o, r, **kw: "/x/john-info.stl"
    )
    monkeypatch.setattr(
        module,
        "render_overlays",
        lambda openscad, runner, ns, overlays, colors, out_dir: captured.append(
            ([os.path.basename(o) for o in overlays], out_dir)
        ),
    )
    ns = module.parse_args(["--output-dir", str(tmp_path), "--color", "red"])
    module.run_icons_mode("oscad", lambda c: None, ns)

    assert (["travel.stl"], os.path.join(str(tmp_path), "icons")) in captured
    assert (
        ["john-info.stl"],
        os.path.join(str(tmp_path), "tags"),
    ) in captured


def test_run_tags_mode_routes_to_tags_dir(tmp_path, monkeypatch):
    module = load_generate_preview()
    captured = []
    monkeypatch.setattr(
        module, "resolve_tag_config", lambda ns: "/c/config-john-doe.yaml"
    )
    monkeypatch.setattr(
        module, "render_info_stl", lambda c, o, r, **kw: "/x/john-doe-info.stl"
    )
    monkeypatch.setattr(
        module,
        "render_overlays",
        lambda openscad, runner, ns, overlays, colors, out_dir: captured.append(
            ([os.path.basename(o) for o in overlays], out_dir)
        ),
    )
    ns = module.parse_args(
        ["--output-dir", str(tmp_path), "--color", "red", "--mode", "tags"]
    )
    module.run_tags_mode("oscad", lambda c: None, ns)

    assert captured == [
        (["john-doe-info.stl"], os.path.join(str(tmp_path), "tags"))
    ]


def make_configs(tmp_path, names):
    configs = tmp_path / "configs"
    configs.mkdir()
    for name in names:
        (configs / name).write_text("dummy: true\n")
    return str(configs)


# ---- --no-cache -------------------------------------------------------------


def test_parse_args_no_cache_default_false():
    module = load_generate_preview()
    ns = module.parse_args([])
    assert ns.no_cache is False


def test_parse_args_no_cache_flag():
    module = load_generate_preview()
    ns = module.parse_args(["--no-cache"])
    assert ns.no_cache is True


def test_render_info_stl_no_cache_skips_restore_but_stores(tmp_path):
    module = load_generate_preview()
    out_dir = tmp_path / "out"
    cache_dir = tmp_path / "cache"
    tpl = tmp_path / "tpl.scad"
    tpl.write_text("cube();")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "name: F\n"
        "last-name: G\n"
        'qr_action: "Wa"\n'
        'phone_number: "+5511999999999"\n'
        'email: "f@g.com"\n'
        "icon: false\n"
        f'template: "{tpl}"\n'
        f'output_dir: "{out_dir}"\n'
        f'cache_dir: "{cache_dir}"\n'
    )
    calls = {"n": 0}

    def runner(commands):
        calls["n"] += 1
        cmd = commands[0]
        stl = cmd[cmd.index("-o") + 1]
        with open(stl, "w") as fh:
            fh.write("INFO")

    # Populate the cache.
    module.render_info_stl(str(config_path), "openscad", runner)
    assert calls["n"] == 1

    # no_cache re-renders rather than restoring.
    module.render_info_stl(str(config_path), "openscad", runner, no_cache=True)
    assert calls["n"] == 2

    # The store still ran, so a plain call now restores without rendering.
    module.render_info_stl(str(config_path), "openscad", runner)
    assert calls["n"] == 2


# ---- select_colors ----------------------------------------------------------


def test_select_colors_all_returns_whole_palette():
    module = load_generate_preview()
    assert module.select_colors("all") == list(module.COLORS.items())


def test_select_colors_single_name():
    module = load_generate_preview()
    assert module.select_colors("red") == [("Red", module.COLORS["Red"])]


def test_select_colors_comma_separated_names_in_order():
    module = load_generate_preview()
    assert module.select_colors("gray, orange") == [
        ("Gray", module.COLORS["Gray"]),
        ("Orange", module.COLORS["Orange"]),
    ]


def test_select_colors_drops_duplicates():
    module = load_generate_preview()
    assert module.select_colors("red, red") == [("Red", module.COLORS["Red"])]


def test_select_colors_unknown_raises():
    module = load_generate_preview()
    with pytest.raises(ValueError):
        module.select_colors("red, bogus")


# ---- prompt_color -----------------------------------------------------------


def test_prompt_color_single_number(monkeypatch):
    module = load_generate_preview()
    monkeypatch.setattr("builtins.input", lambda _="": "4")
    items = list(module.COLORS.items())
    assert module.prompt_color() == [items[3]]


def test_prompt_color_comma_separated_numbers(monkeypatch):
    module = load_generate_preview()
    monkeypatch.setattr("builtins.input", lambda _="": "4,5")
    items = list(module.COLORS.items())
    assert module.prompt_color() == [items[3], items[4]]


def test_prompt_color_mixed_numbers_and_names(monkeypatch):
    module = load_generate_preview()
    monkeypatch.setattr("builtins.input", lambda _="": "gray, 5")
    items = list(module.COLORS.items())
    assert module.prompt_color() == [items[3], items[4]]


def test_prompt_color_all_number_returns_palette(monkeypatch):
    module = load_generate_preview()
    items = list(module.COLORS.items())
    monkeypatch.setattr("builtins.input", lambda _="": str(len(items) + 1))
    assert module.prompt_color() == items


def test_prompt_color_reasks_on_bad_token(monkeypatch):
    module = load_generate_preview()
    answers = iter(["4,bogus", "5"])
    monkeypatch.setattr("builtins.input", lambda _="": next(answers))
    items = list(module.COLORS.items())
    assert module.prompt_color() == [items[4]]


# ---- list_tag_configs -------------------------------------------------------


def test_list_tag_configs_returns_sorted_config_yaml(tmp_path):
    module = load_generate_preview()
    configs_dir = make_configs(
        tmp_path, ["config-bravo.yaml", "config.yaml", "config-alpha.yaml"]
    )
    paths = module.list_tag_configs(configs_dir)
    assert [os.path.basename(p) for p in paths] == [
        "config-alpha.yaml",
        "config-bravo.yaml",
        "config.yaml",
    ]


def test_list_tag_configs_ignores_non_config_yaml(tmp_path):
    module = load_generate_preview()
    configs_dir = make_configs(
        tmp_path, ["config.yaml", "notes.yaml", "config-x.yaml", "readme.txt"]
    )
    paths = module.list_tag_configs(configs_dir)
    assert [os.path.basename(p) for p in paths] == ["config-x.yaml", "config.yaml"]


def test_list_tag_configs_missing_dir_returns_empty(tmp_path):
    module = load_generate_preview()
    paths = module.list_tag_configs(str(tmp_path / "nope"))
    assert paths == []


# ---- prompt_mode ------------------------------------------------------------


def test_prompt_mode_accepts_number(monkeypatch):
    module = load_generate_preview()
    monkeypatch.setattr("builtins.input", lambda _="": "2")
    assert module.prompt_mode() == "tags"


def test_prompt_mode_accepts_name(monkeypatch):
    module = load_generate_preview()
    monkeypatch.setattr("builtins.input", lambda _="": "Icons")
    assert module.prompt_mode() == "icons"


def test_prompt_mode_reasks_on_invalid(monkeypatch):
    module = load_generate_preview()
    answers = iter(["", "bogus", "1"])
    monkeypatch.setattr("builtins.input", lambda _="": next(answers))
    assert module.prompt_mode() == "icons"


def test_prompt_mode_raises_on_closed_stdin(monkeypatch):
    module = load_generate_preview()

    def closed(_=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", closed)
    with pytest.raises(ValueError):
        module.prompt_mode()


# ---- prompt_tag_config ------------------------------------------------------


def test_prompt_tag_config_selects_by_number(tmp_path, monkeypatch):
    module = load_generate_preview()
    configs_dir = make_configs(tmp_path, ["config.yaml", "config-john-doe.yaml"])
    configs = module.list_tag_configs(configs_dir)
    monkeypatch.setattr("builtins.input", lambda _="": "1")
    assert module.prompt_tag_config(configs) == configs[0]


def test_prompt_tag_config_selects_by_name(tmp_path, monkeypatch):
    module = load_generate_preview()
    configs_dir = make_configs(tmp_path, ["config.yaml", "config-john-doe.yaml"])
    configs = module.list_tag_configs(configs_dir)
    monkeypatch.setattr("builtins.input", lambda _="": "config-john-doe")
    chosen = module.prompt_tag_config(configs)
    assert os.path.basename(chosen) == "config-john-doe.yaml"


def test_prompt_tag_config_reasks_on_invalid(tmp_path, monkeypatch):
    module = load_generate_preview()
    configs_dir = make_configs(tmp_path, ["config.yaml"])
    configs = module.list_tag_configs(configs_dir)
    answers = iter(["99", "nope", "1"])
    monkeypatch.setattr("builtins.input", lambda _="": next(answers))
    assert module.prompt_tag_config(configs) == configs[0]


def test_prompt_tag_config_raises_on_closed_stdin(tmp_path, monkeypatch):
    module = load_generate_preview()
    configs_dir = make_configs(tmp_path, ["config.yaml"])
    configs = module.list_tag_configs(configs_dir)

    def closed(_=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", closed)
    with pytest.raises(ValueError):
        module.prompt_tag_config(configs)
