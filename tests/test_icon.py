import os
import types

import pytest

from taggen.icon import (
    _export_dxf,
    aspect_vars,
    fit_svg_size,
    icon_vars,
    measure_aspect,
    parse_dxf_aspect,
    resolve_icon,
)


# A minimal DXF whose geometry spans x in [0, 2] and y in [0, 4] -> aspect 4/2.
DXF_2x4 = "\n".join(
    [
        "0", "SECTION",
        "2", "ENTITIES",
        "0", "LINE",
        "10", "0.0",
        "20", "0.0",
        "11", "2.0",
        "21", "4.0",
        "0", "ENDSEC",
        "0", "EOF",
        "",
    ]
)


def make_layout(tmp_path):
    """Create a repo-like layout: <root>/scripts/tpl.scad and <root>/icons/."""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "icons").mkdir()
    template = tmp_path / "scripts" / "tpl.scad"
    template.write_text("// template")
    icon = tmp_path / "icons" / "travel.svg"
    icon.write_text("<svg/>")
    return str(template), str(icon)


def test_resolve_icon_finds_in_icons_dir(tmp_path):
    template, icon = make_layout(tmp_path)
    assert resolve_icon("travel.svg", template) == os.path.abspath(icon)


def test_resolve_icon_accepts_direct_path(tmp_path):
    template, icon = make_layout(tmp_path)
    assert resolve_icon(icon, template) == os.path.abspath(icon)


def test_resolve_icon_missing_raises(tmp_path):
    template, _ = make_layout(tmp_path)
    with pytest.raises(ValueError):
        resolve_icon("nope.svg", template)


def test_icon_vars_resolves_and_enables(tmp_path):
    template, icon = make_layout(tmp_path)
    config = {"template": template, "icon": "travel.svg"}
    v = icon_vars(config)
    assert v["FILE"] == os.path.abspath(icon)
    assert v["ENABLE_SVG"] is True


def test_icon_vars_disabled_when_false(tmp_path):
    template, _ = make_layout(tmp_path)
    config = {"template": template, "icon": False}
    v = icon_vars(config)
    assert v["ENABLE_SVG"] is False
    assert "FILE" not in v


def test_parse_dxf_aspect_returns_height_over_width():
    assert parse_dxf_aspect(DXF_2x4) == pytest.approx(2.0)


def test_parse_dxf_aspect_zero_width_falls_back_to_one():
    # A vertical line has no width; avoid dividing by zero.
    flat = "\n".join(["10", "5.0", "20", "0.0", "11", "5.0", "21", "4.0", ""])
    assert parse_dxf_aspect(flat) == 1.0


def test_parse_dxf_aspect_no_coords_falls_back_to_one():
    assert parse_dxf_aspect("0\nSECTION\n0\nEOF\n") == 1.0


def _fake_run_writing(dxf_text, returncode=0):
    def run(cmd, *args, **kwargs):
        out = cmd[cmd.index("-o") + 1]
        with open(out, "w") as fh:
            fh.write(dxf_text)
        return types.SimpleNamespace(returncode=returncode)

    return run


def test_export_dxf_returns_file_contents(tmp_path):
    icon = tmp_path / "icon.svg"
    icon.write_text("<svg/>")
    dxf = _export_dxf("openscad", str(icon), run=_fake_run_writing(DXF_2x4))
    assert dxf == DXF_2x4


def test_export_dxf_imports_icon_by_absolute_path(tmp_path, monkeypatch):
    # OpenSCAD resolves import() relative to the temp .scad file, so the icon
    # path must be made absolute or a relative path would silently fail.
    icon = tmp_path / "icon.svg"
    icon.write_text("<svg/>")
    monkeypatch.chdir(tmp_path)
    seen = {}

    def run(cmd, *args, **kwargs):
        with open(cmd[-1]) as fh:
            seen["scad"] = fh.read()
        out = cmd[cmd.index("-o") + 1]
        open(out, "w").write(DXF_2x4)
        return types.SimpleNamespace(returncode=0)

    _export_dxf("openscad", "icon.svg", run=run)
    assert os.path.abspath(str(icon)) in seen["scad"]


def test_export_dxf_returns_none_on_nonzero_exit(tmp_path):
    icon = tmp_path / "icon.svg"
    icon.write_text("<svg/>")
    run = _fake_run_writing(DXF_2x4, returncode=1)
    assert _export_dxf("openscad", str(icon), run=run) is None


def test_measure_aspect_uses_exporter_output():
    aspect = measure_aspect("icon.svg", "openscad", exporter=lambda *a: DXF_2x4)
    assert aspect == pytest.approx(2.0)


def test_measure_aspect_falls_back_to_one_when_export_fails():
    aspect = measure_aspect("icon.svg", "openscad", exporter=lambda *a: None)
    assert aspect == 1.0


def test_aspect_vars_emits_rounded_svg_aspect():
    v = aspect_vars("icon.svg", "openscad", measure=lambda *a: 2.44444)
    assert v == {"SVG_ASPECT": 2.4444}


def test_fit_svg_size_square_uses_width_budget():
    # A square icon is width-bound: SVG_SIZE == w_max.
    assert fit_svg_size(1.0, w_max=45, h_max=75) == 45


def test_fit_svg_size_wide_icon_stays_within_width():
    # Wide (aspect < 1): still width-bound at w_max, never overflows height.
    assert fit_svg_size(0.5, w_max=45, h_max=75) == 45


def test_fit_svg_size_tall_icon_uses_height_budget():
    # A very tall icon (aspect 4) is bound by the height budget, not the small
    # square box -- so it fills the tag's vertical room instead of looking tiny.
    assert fit_svg_size(4.0, w_max=45, h_max=75) == 75


def test_fit_svg_size_moderately_tall_icon_is_width_bound():
    # aspect 1.2: width binds at w_max=45, so the bound dimension (height) is
    # 45*1.2 = 54, still under the 75 height budget.
    assert fit_svg_size(1.2, w_max=45, h_max=75) == 54
