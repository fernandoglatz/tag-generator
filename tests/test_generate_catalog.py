"""Tests for the generate-catalog.py orchestration script.

The module name has a hyphen, so it is loaded by path via importlib.
"""

import importlib.util
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_generate_catalog():
    path = os.path.join(ROOT, "generate-catalog.py")
    spec = importlib.util.spec_from_file_location("generate_catalog", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_preview(path, size=(64, 64), color=(255, 215, 0)):
    Image.new("RGB", size, color).save(path)


def test_icon_stems_lists_svg_stems(tmp_path):
    module = load_generate_catalog()
    icons = tmp_path / "icons"
    icons.mkdir()
    (icons / "travel.svg").write_text("<svg/>")
    (icons / "world.svg").write_text("<svg/>")
    (icons / "notes.txt").write_text("ignore me")

    assert sorted(module.icon_stems(str(icons))) == ["travel", "world"]


def test_icon_stems_excludes_configured_icons(tmp_path):
    module = load_generate_catalog()
    icons = tmp_path / "icons"
    icons.mkdir()
    for stem in module.EXCLUDED_ICONS:
        (icons / f"{stem}.svg").write_text("<svg/>")
    (icons / "world.svg").write_text("<svg/>")

    assert module.icon_stems(str(icons)) == ["world"]


def test_main_writes_one_catalog_per_color_with_previews(tmp_path):
    module = load_generate_catalog()
    icons = tmp_path / "icons"
    previews = tmp_path / "previews"
    out = tmp_path / "catalog"
    icons.mkdir()
    previews.mkdir()
    (icons / "travel.svg").write_text("<svg/>")
    (icons / "world.svg").write_text("<svg/>")
    # Only the yellow previews exist -> only the yellow catalog is built.
    make_preview(previews / "travel-yellow.png")
    make_preview(previews / "world-yellow.png")

    code = module.main(
        [
            "--icons-dir", str(icons),
            "--previews-dir", str(previews),
            "--output-dir", str(out),
        ]
    )

    assert code == 0
    assert [p.name for p in out.iterdir()] == ["catalog-yellow.png"]


def test_main_errors_without_previews_dir(tmp_path, capsys, monkeypatch):
    module = load_generate_catalog()
    icons = tmp_path / "icons"
    icons.mkdir()
    (icons / "travel.svg").write_text("<svg/>")
    # The cascade "runs" but produces nothing, so the dir is still missing.
    monkeypatch.setattr(module, "run_generate_preview", lambda argv: None)

    code = module.main(
        [
            "--icons-dir", str(icons),
            "--previews-dir", str(tmp_path / "missing"),
            "--output-dir", str(tmp_path / "catalog"),
        ]
    )

    assert code == 1
    # The cascade ran but produced nothing, so the "no previews" guard fires.
    assert "No icon previews found" in capsys.readouterr().err


# ---- ensure_previews (cascade to generate-preview) --------------------------


def _numbered(module, stems):
    return module.numbered_icons(stems)


def test_ensure_previews_generates_missing_for_color(tmp_path, monkeypatch):
    module = load_generate_catalog()
    previews = tmp_path / "out" / "icons"
    previews.mkdir(parents=True)
    stems = ["travel", "world"]
    numbered = _numbered(module, stems)
    slug_to_name = {module.color_slug(n): n for n in module.COLORS}
    captured = []
    monkeypatch.setattr(
        module, "run_generate_preview", lambda argv: captured.append(argv)
    )
    ns = module.parse_args(["--previews-dir", str(previews), "--color", "red"])
    module.ensure_previews(ns, stems, numbered, slug_to_name)

    assert len(captured) == 1
    argv = captured[0]
    # Missing stems are passed positionally; only the red colour is targeted,
    # the previews root (parent of the icons dir) is the output dir, and the
    # info side is skipped.
    assert "travel" in argv and "world" in argv
    assert argv[argv.index("--color") + 1] == "Red"
    assert argv[argv.index("--output-dir") + 1] == str(tmp_path / "out")
    assert "--no-info" in argv


def test_ensure_previews_skips_when_all_present(tmp_path, monkeypatch):
    module = load_generate_catalog()
    previews = tmp_path / "out" / "icons"
    previews.mkdir(parents=True)
    stems = ["travel", "world"]
    for stem in stems:
        make_preview(previews / module.preview_filename(stem, "red"))
    numbered = _numbered(module, stems)
    slug_to_name = {module.color_slug(n): n for n in module.COLORS}
    called = []
    monkeypatch.setattr(
        module, "run_generate_preview", lambda argv: called.append(argv)
    )
    ns = module.parse_args(["--previews-dir", str(previews), "--color", "red"])
    module.ensure_previews(ns, stems, numbered, slug_to_name)

    assert called == []


def test_ensure_previews_all_colors_when_none_exist(tmp_path, monkeypatch):
    module = load_generate_catalog()
    previews = tmp_path / "out" / "icons"
    previews.mkdir(parents=True)
    stems = ["travel", "world"]
    numbered = _numbered(module, stems)
    slug_to_name = {module.color_slug(n): n for n in module.COLORS}
    colors = []
    monkeypatch.setattr(
        module,
        "run_generate_preview",
        lambda argv: colors.append(argv[argv.index("--color") + 1]),
    )
    ns = module.parse_args(["--previews-dir", str(previews)])
    module.ensure_previews(ns, stems, numbered, slug_to_name)

    # No --color and no previews yet -> every palette colour is generated.
    assert colors == list(module.COLORS)


def test_ensure_previews_default_keeps_existing_colors(tmp_path, monkeypatch):
    module = load_generate_catalog()
    previews = tmp_path / "out" / "icons"
    previews.mkdir(parents=True)
    stems = ["travel", "world"]
    make_preview(previews / module.preview_filename("travel", "yellow"))
    numbered = _numbered(module, stems)
    slug_to_name = {module.color_slug(n): n for n in module.COLORS}
    called = []
    monkeypatch.setattr(
        module, "run_generate_preview", lambda argv: called.append(argv)
    )
    ns = module.parse_args(["--previews-dir", str(previews)])
    module.ensure_previews(ns, stems, numbered, slug_to_name)

    # Some previews already exist, so the existing-colour set is built as-is
    # rather than triggering a full all-colours render.
    assert called == []
