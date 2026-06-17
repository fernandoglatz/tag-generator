#!/usr/bin/env python3
"""Tile the per-icon preview PNGs into one enumerated selection sheet per colour.

generate-preview.py renders a white-icon-on-coloured-tag PNG per icon, named
``<icon>-<colour>.png`` in ``output/previews/icons``. This script composes those into
a numbered grid -- a catalog a customer can browse to pick an icon by number
("I'll take #5 in red").

Numbering comes from a single global alphabetical sort of the icons in
``icons/``, so icon #N is the same icon in every colour's catalog. One PNG is
written per colour that has previews (or just ``--color`` if given). Cells whose
preview is missing render a placeholder so the numbering never shifts.

Usage:
    python3 generate-catalog.py                 # a catalog per colour with previews
    python3 generate-catalog.py --color red     # just the red catalog
    python3 generate-catalog.py --columns 5
"""

import argparse
import importlib.util
import os
import sys

from taggen.catalog import (
    CATALOG_TITLE_PTBR,
    color_label,
    colors_with_previews,
    grid_rows,
    icon_label,
    numbered_icons,
    preview_filename,
)

ROOT = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(ROOT, "icons")

# Icon stems left out of the catalog (e.g. the default/sample icon, not for sale).
EXCLUDED_ICONS = {"travel-svgrepo-com"}
PREVIEWS_DIR = os.path.join(ROOT, "output", "previews", "icons")
OUTPUT_DIR = os.path.join(ROOT, "output", "catalog")


def _load_preview_module():
    """Load generate-preview.py (hyphenated name) for its colour palette."""
    path = os.path.join(ROOT, "generate-preview.py")
    spec = importlib.util.spec_from_file_location("generate_preview", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_preview = _load_preview_module()
COLORS = _preview.COLORS
color_slug = _preview.color_slug
select_color = _preview.select_color


def run_generate_preview(argv):
    """Invoke generate-preview in-process to render previews on demand.

    Raises ``RuntimeError`` if generate-preview exits non-zero so the catalog
    doesn't press on to a second failure on the still-missing PNGs.
    """
    code = _preview.main(argv)
    if code != 0:
        raise RuntimeError("generate-preview failed while regenerating previews.")


def ensure_previews(ns, stems, numbered, slug_to_name):
    """Render any preview PNGs the catalog needs but doesn't have yet.

    Target colours: ``--color`` selects just that one; with no ``--color`` the
    existing previews are kept as-is when any are present, and when none exist
    yet the whole palette is generated so a full catalog can be built. For each
    target colour, the icons missing a preview are rendered in a single
    generate-preview call (info side skipped, output aimed at the previews root).
    """
    if ns.color:
        color_name, _ = select_color(ns.color)
        target_slugs = [color_slug(color_name)]
    else:
        available = (
            set(os.listdir(ns.previews_dir))
            if os.path.isdir(ns.previews_dir)
            else set()
        )
        if colors_with_previews(stems, list(slug_to_name), available):
            return
        target_slugs = list(slug_to_name)

    os.makedirs(ns.previews_dir, exist_ok=True)
    previews_root = os.path.dirname(ns.previews_dir)
    for slug in target_slugs:
        color_name = slug_to_name[slug]
        missing = [
            stem
            for _number, stem in numbered
            if not os.path.isfile(
                os.path.join(ns.previews_dir, preview_filename(stem, slug))
            )
        ]
        if missing:
            run_generate_preview(
                [*missing, "--color", color_name,
                 "--output-dir", previews_root, "--no-info"]
            )

# Layout constants (pixels). Cells are square thumbnails with a caption strip.
PADDING = 24
CAPTION_H = 74
CAPTION_LINE_H = 30
HEADER_H = 110
BG = (255, 255, 255)
INK = (34, 34, 34)
MUTED = (140, 140, 140)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Tile per-icon previews into an enumerated catalog per colour."
    )
    parser.add_argument(
        "--color",
        default=None,
        help="Build only this colour (name from the palette). Default: every "
        "colour that has previews.",
    )
    parser.add_argument(
        "--columns", type=int, default=4, help="Cells per row (default 4)."
    )
    parser.add_argument(
        "--cell-size",
        type=int,
        default=256,
        help="Thumbnail edge in pixels (default 256).",
    )
    parser.add_argument(
        "--icons-dir", default=ICONS_DIR, help="Directory of SVG icons (the index)."
    )
    parser.add_argument(
        "--previews-dir", default=PREVIEWS_DIR, help="Directory of preview PNGs."
    )
    parser.add_argument(
        "--output-dir", default=OUTPUT_DIR, help="Where to write the catalog PNGs."
    )
    return parser.parse_args(argv)


def icon_stems(icons_dir):
    """Return the sellable icon stems -- one per ``.svg`` in ``icons_dir``.

    Stems in ``EXCLUDED_ICONS`` (e.g. the default sample icon) are left out.
    """
    return [
        stem
        for f in os.listdir(icons_dir)
        if f.lower().endswith(".svg")
        for stem in [os.path.splitext(f)[0]]
        if stem not in EXCLUDED_ICONS
    ]


def load_font(size):
    """Return a TrueType font at ``size``, falling back to Pillow's default.

    DejaVuSans ships with Pillow; if it (and the common system paths) can't be
    found we use the bitmap default so the script still produces a sheet.
    """
    from PIL import ImageFont

    candidates = [
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _text_centered(draw, center_x, top, text, font, fill):
    """Draw ``text`` horizontally centred on ``center_x`` at ``top``."""
    left, upper, right, lower = draw.textbbox((0, 0), text, font=font)
    draw.text(
        (center_x - (right - left) / 2, top - upper), text, font=font, fill=fill
    )


def _wrap_lines(draw, text, font, max_width, max_lines=2):
    """Word-wrap ``text`` to lines no wider than ``max_width``.

    Keeps at most ``max_lines`` (ellipsising the last if the caption still
    overruns), so a long name like "New York Famous Building" stacks within its
    cell instead of bleeding into the neighbour.
    """
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = (current + " " + word).strip()
        if not current or draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
        if len(lines) == max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)

    if draw.textlength(lines[-1], font=font) > max_width:
        truncated = lines[-1]
        while truncated and draw.textlength(truncated + "…", font=font) > max_width:
            truncated = truncated[:-1]
        lines[-1] = truncated + "…"
    return lines


def render_catalog(numbered, color_name, slug, previews_dir, columns, cell_size):
    """Compose and return the catalog image for one colour.

    ``numbered`` is the global ``(n, stem)`` list. Each cell shows the icon's
    preview thumbnail (or a placeholder if absent) captioned ``N. <PT-BR name>``;
    a PT-BR header names the colour.
    """
    from PIL import Image, ImageDraw

    cell_w = cell_size
    cell_h = cell_size + CAPTION_H
    rows = grid_rows(len(numbered), columns)
    width = PADDING + columns * (cell_w + PADDING)
    height = HEADER_H + rows * (cell_h + PADDING) + PADDING

    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)

    _text_centered(
        draw, width / 2, PADDING + 8,
        CATALOG_TITLE_PTBR.format(color=color_label(slug, color_name)),
        load_font(44), INK,
    )

    caption_font = load_font(26)
    for index, (number, stem) in enumerate(numbered):
        row, col = divmod(index, columns)
        x = PADDING + col * (cell_w + PADDING)
        y = HEADER_H + row * (cell_h + PADDING)

        png = os.path.join(previews_dir, preview_filename(stem, slug))
        if os.path.isfile(png):
            thumb = Image.open(png).convert("RGB")
            thumb.thumbnail((cell_size, cell_size), Image.LANCZOS)
            image.paste(thumb, (x + (cell_w - thumb.width) // 2,
                                y + (cell_size - thumb.height) // 2))
        else:
            draw.rectangle(
                [x, y, x + cell_w, y + cell_size], outline=MUTED, width=2
            )
            _text_centered(
                draw, x + cell_w / 2, y + cell_size / 2 - 18, "—",
                load_font(40), MUTED,
            )

        caption = f"{number}. {icon_label(stem)}"
        lines = _wrap_lines(draw, caption, caption_font, cell_w)
        for line_no, line in enumerate(lines):
            _text_centered(
                draw, x + cell_w / 2, y + cell_size + 14 + line_no * CAPTION_LINE_H,
                line, caption_font, INK,
            )

    return image


def main(argv=None):
    """Write one catalog PNG per selected colour. Returns an exit code."""
    ns = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print(
            "Error: Pillow is required to build the catalog "
            "(pip install Pillow).",
            file=sys.stderr,
        )
        return 1

    try:
        stems = icon_stems(ns.icons_dir)
        if not stems:
            raise ValueError(f"No SVG icons found in {ns.icons_dir}")

        numbered = numbered_icons(stems)
        slug_to_name = {color_slug(name): name for name in COLORS}

        # Render any previews the catalog needs but doesn't have yet, cascading
        # through generate-preview (which in turn regenerates the tag/icon STLs).
        ensure_previews(ns, stems, numbered, slug_to_name)

        if not os.path.isdir(ns.previews_dir):
            raise FileNotFoundError(
                f"Previews directory not found: {ns.previews_dir} "
                "(run generate-preview.py first)."
            )

        available = set(os.listdir(ns.previews_dir))

        if ns.color:
            color_name, _ = select_color(ns.color)
            slugs = [color_slug(color_name)]
        else:
            slugs = colors_with_previews(stems, list(slug_to_name), available)
            if not slugs:
                raise ValueError(
                    f"No icon previews found in {ns.previews_dir} "
                    "(run generate-preview.py first)."
                )

        os.makedirs(ns.output_dir, exist_ok=True)
        for slug in slugs:
            color_name = slug_to_name[slug]
            image = render_catalog(
                numbered, color_name, slug, ns.previews_dir,
                ns.columns, ns.cell_size,
            )
            out_path = os.path.join(ns.output_dir, f"catalog-{slug}.png")
            image.save(out_path)
            print(f"Wrote {out_path}")
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
