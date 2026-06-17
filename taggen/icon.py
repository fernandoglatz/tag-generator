"""Resolve the SVG icon path so OpenSCAD's ``import(FILE)`` can find it.

The template imports the icon by bare filename, which OpenSCAD resolves
relative to the ``.scad`` file's directory (``scripts/``). The icons actually
live in a sibling ``icons/`` directory, so we resolve to an absolute path and
pass it via ``-D FILE=...``.
"""

import os
import subprocess
import tempfile

DEFAULT_ICON = "travel-svgrepo-com.svg"


def resolve_icon(icon, template):
    """Return an absolute path to ``icon``.

    Looks for the icon as a direct path, next to the template, then in the
    sibling ``icons/`` directory. Raises ``ValueError`` if not found.
    """
    if os.path.isfile(icon):
        return os.path.abspath(icon)

    template_dir = os.path.dirname(os.path.abspath(template))

    alongside = os.path.join(template_dir, icon)
    if os.path.isfile(alongside):
        return alongside

    icons_dir = os.path.join(os.path.dirname(template_dir), "icons")
    in_icons = os.path.join(icons_dir, icon)
    if os.path.isfile(in_icons):
        return in_icons

    raise ValueError(f"Icon file not found: {icon}")


def icon_vars(config):
    """Return SCAD vars for the icon: an absolute ``FILE`` + ``ENABLE_SVG``.

    ``icon`` defaults to the bundled travel icon. Set ``icon: false`` (or null)
    to disable the icon entirely (no import, no warning).
    """
    icon = config.get("icon", DEFAULT_ICON)
    if not icon:
        return {"ENABLE_SVG": False}
    return {"FILE": resolve_icon(icon, config["template"]), "ENABLE_SVG": True}


def parse_dxf_aspect(dxf_text):
    """Return ``height / width`` of the geometry in an OpenSCAD-exported DXF.

    DXF stores coordinates as ``(group_code, value)`` line pairs; X lives in
    group codes 10/11 and Y in 20/21. Falls back to ``1.0`` (square, i.e. the
    template's legacy width-fit) when there's no usable geometry.
    """
    lines = dxf_text.splitlines()
    xs, ys = [], []
    for i in range(0, len(lines) - 1, 2):
        code = lines[i].strip()
        try:
            value = float(lines[i + 1].strip())
        except ValueError:
            continue
        if code in ("10", "11"):
            xs.append(value)
        elif code in ("20", "21"):
            ys.append(value)

    if not xs or not ys:
        return 1.0
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    if width <= 0:
        return 1.0
    return height / width


def _export_dxf(openscad, icon_path, run=subprocess.run):
    """Render ``icon_path`` to a 2D DXF and return its text, or ``None``.

    Returns ``None`` if OpenSCAD exits non-zero or writes no file, so callers
    can fall back to the legacy sizing instead of failing the whole render.
    """
    with tempfile.TemporaryDirectory() as tmp:
        scad_path = os.path.join(tmp, "measure.scad")
        dxf_path = os.path.join(tmp, "measure.dxf")
        # OpenSCAD resolves import() relative to the .scad file (here, a temp
        # dir), so the icon path must be absolute.
        abs_icon = os.path.abspath(icon_path)
        escaped = abs_icon.replace("\\", "\\\\").replace('"', '\\"')
        with open(scad_path, "w") as fh:
            fh.write(f'import("{escaped}", center=true);\n')

        result = run([openscad, "-o", dxf_path, scad_path])
        if result.returncode != 0 or not os.path.isfile(dxf_path):
            return None
        with open(dxf_path) as fh:
            return fh.read()


def measure_aspect(icon_path, openscad, exporter=_export_dxf):
    """Return the icon geometry's ``height / width`` (1.0 if unmeasurable)."""
    dxf = exporter(openscad, icon_path)
    if not dxf:
        return 1.0
    return parse_dxf_aspect(dxf)


def aspect_vars(icon_path, openscad, measure=measure_aspect):
    """Return the ``SVG_ASPECT`` SCAD var for ``icon_path`` (rounded)."""
    return {"SVG_ASPECT": round(measure(icon_path, openscad), 4)}


def fit_svg_size(aspect, w_max, h_max):
    """Return the template's ``SVG_SIZE`` to fit an icon in a ``w_max`` x ``h_max`` box.

    The template scales the icon so its *bound* dimension equals ``SVG_SIZE``:
    height when ``aspect > 1`` (tall), width otherwise (wide/square). The tag is
    much taller than it is wide, so passing a larger ``h_max`` lets tall icons
    (e.g. a 4:1 skyscraper) grow vertically instead of being capped at the small
    square width budget and looking tiny -- while keeping every icon's width
    within ``w_max`` so it never overflows the tag's sides.
    """
    if aspect > 1:
        # Bound dimension is height; cap it at h_max and at the width budget
        # (height = w_max * aspect when the width is the binding constraint).
        return min(h_max, w_max * aspect)
    # Bound dimension is width; cap at w_max and at the height budget
    # (width = h_max / aspect when the height is the binding constraint).
    return min(w_max, h_max / aspect)
