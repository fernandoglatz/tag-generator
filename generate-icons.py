#!/usr/bin/env python3
"""Render an STL for every SVG icon using scripts/icone-tag.scad.

The icone-tag template extrudes a single SVG icon (the tag body and QR code are
hidden by default). This script walks the icons/ directory and exports one STL
per icon, passing each icon's absolute path to OpenSCAD via -D FILE=... (the
template's bare-filename import otherwise looks in the wrong directory).

Usage:
    python3 generate-icons.py                 # render every icon in icons/
    python3 generate-icons.py world travel    # render only these (by stem or filename)
    python3 generate-icons.py --size 40 --thickness 1.0
"""

import argparse
import os
import sys

from taggen.icon import aspect_vars, fit_svg_size
from taggen.runner import build_commands, resolve_openscad, run_commands
from taggen.varmap import to_define_args

ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(ROOT, "scripts", "icone-tag.scad")
ICONS_DIR = os.path.join(ROOT, "icons")
OUTPUT_DIR = os.path.join(ROOT, "output", "stl", "icons")


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Render an STL for every SVG icon using icone-tag.scad."
    )
    parser.add_argument(
        "icons",
        nargs="*",
        help="Optional icon names to render (stem or filename). Default: all.",
    )
    parser.add_argument(
        "--icons-dir", default=ICONS_DIR, help="Directory of SVG icons."
    )
    parser.add_argument(
        "--output-dir", default=OUTPUT_DIR, help="Where to write the STLs."
    )
    parser.add_argument(
        "--template", default=TEMPLATE, help="SCAD template to render."
    )
    parser.add_argument(
        "--size",
        type=float,
        default=45.0,
        help="Max icon width in mm (default 45). Wide/square icons fill this.",
    )
    parser.add_argument(
        "--max-height",
        type=float,
        default=75.0,
        help="Max icon height in mm (default 75). Tall icons fill this so a "
        "skinny skyscraper isn't capped at the small square width budget.",
    )
    parser.add_argument(
        "--thickness",
        type=float,
        default=0.5,
        help="SVG_THICKNESS in mm (default 0.5). Requires --solid to take effect.",
    )
    parser.add_argument(
        "--openscad", default=None, help="Path/command to the OpenSCAD binary."
    )
    parser.add_argument(
        "--backend",
        default=None,
        help="Geometry engine (e.g. 'manifold' on OpenSCAD 2023.06+).",
    )
    return parser.parse_args(argv)


def select_icons(icons_dir, requested):
    """Return absolute paths of SVGs to render.

    With no ``requested`` names, returns every ``.svg`` in ``icons_dir`` sorted
    by name. Otherwise matches each requested name by stem or filename. Raises
    ``ValueError`` naming any request that doesn't resolve.
    """
    available = sorted(
        f for f in os.listdir(icons_dir) if f.lower().endswith(".svg")
    )
    if not requested:
        return [os.path.join(icons_dir, f) for f in available]

    by_stem = {os.path.splitext(f)[0]: f for f in available}
    by_name = {f: f for f in available}
    selected = []
    for name in requested:
        match = by_name.get(name) or by_stem.get(os.path.splitext(name)[0])
        if not match:
            raise ValueError(f"Icon not found in {icons_dir}: {name}")
        selected.append(os.path.join(icons_dir, match))
    return selected


def main(argv=None, resolver=resolve_openscad, runner=run_commands, aspect=aspect_vars):
    """Render an STL per icon. Returns a process exit code."""
    ns = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        openscad = resolver(ns.openscad)
        icons = select_icons(ns.icons_dir, ns.icons)
        if not icons:
            print(f"No SVG icons found in {ns.icons_dir}", file=sys.stderr)
            return 1

        os.makedirs(ns.output_dir, exist_ok=True)

        for index, icon_path in enumerate(icons, start=1):
            stem = os.path.splitext(os.path.basename(icon_path))[0]
            stl_path = os.path.join(ns.output_dir, stem + ".stl")

            # Force the icon to a real, solid thickness: the template defaults to
            # Facedown_Mode, which extrudes a paper-thin 0.004 mm shell that is
            # useless as a standalone print.
            # Measure the icon's aspect ratio, then size it to fill a
            # width x height rectangle rather than a small square box. Without the
            # aspect a tall icon would be fit by width and overflow the tag; with
            # only a square box a 4:1 skyscraper would be capped at the width
            # budget and look tiny. fit_svg_size lets tall icons use the larger
            # height budget while every icon stays within the width budget.
            av = aspect(icon_path, openscad)
            size = fit_svg_size(av["SVG_ASPECT"], ns.size, ns.max_height)
            scad_vars = {
                "ENABLE_SVG": True,
                "FILE": icon_path,
                "Facedown_Mode": False,
                "SVG_SIZE": size,
                "SVG_THICKNESS": ns.thickness,
            }
            scad_vars.update(av)
            define_args = to_define_args(scad_vars)
            commands = build_commands(
                openscad, ns.template, define_args, stl_path, backend=ns.backend
            )
            print(
                f"[{index}/{len(icons)}] Rendering {stem} -> {stl_path}",
                flush=True,
            )
            runner(commands)
            print(f"Wrote {stl_path}")
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
