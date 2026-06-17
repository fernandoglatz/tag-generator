"""Tests for the generate-icons.py orchestration script.

The module name has a hyphen, so it is loaded by path via importlib.
"""

import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_generate_icons():
    path = os.path.join(ROOT, "generate-icons.py")
    spec = importlib.util.spec_from_file_location("generate_icons", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_main_includes_measured_svg_aspect(tmp_path):
    """Each icon render must carry its measured SVG_ASPECT so tall icons fit
    by height instead of overflowing the tag."""
    gi = load_generate_icons()
    icons_dir = tmp_path / "icons"
    icons_dir.mkdir()
    (icons_dir / "tall.svg").write_text("<svg/>")
    out_dir = tmp_path / "out"

    captured = []

    def fake_runner(commands):
        captured.append(commands)

    code = gi.main(
        ["--icons-dir", str(icons_dir), "--output-dir", str(out_dir)],
        resolver=lambda v: "openscad",
        runner=fake_runner,
        aspect=lambda file, openscad: {"SVG_ASPECT": 2.44},
    )

    assert code == 0
    assert any("SVG_ASPECT=2.44" in arg for arg in captured[0][0])
