#!/usr/bin/env python3
"""Render PNGs overlaying a white icon STL on the tag STL in one tag colour.

The icon is always white; the tag is rendered in the single ``--color`` you
pick from the palette below, on a white background. OpenSCAD only honours
``color()`` in its
preview (ThrownTogether) PNG -- a full ``--render`` collapses everything to one
material colour -- so this writes a throwaway SCAD that ``import()``s both STLs
wrapped in ``color()`` and exports with ``--preview``.

The ``Nature`` colour scheme gives a flat near-white (#fafafa) background;
post-processing then snaps that flat colour to pure white (sampling the corner
pixel, so it works whatever scheme you pick). Needs Pillow for the snap -- if
it's missing the render is kept as-is (near-white) and a note is printed.

Besides the icon side, it also previews the *info* side -- the name/QR/phone/
email face built from ``configs/config.yaml`` via the generate-tag pipeline. That
face is rendered with ``HIDE_TAG=true`` (text + QR + icon, no body) so it can be
overlaid in white on the coloured tag, mirroring the icon side. Pass
``--no-info`` to skip it.

Run with no disambiguating args to pick a mode from a console menu: *icons*
(every icon on a coloured tag, the flow above) or *tags* (one tag config from
``configs/`` previewed on its own in a chosen colour).

PNGs are split by kind under the previews root: icon previews in
``output/previews/icons`` and tag-name (info side) previews in
``output/previews/tags``.

Usage:
    python3 generate-preview.py                              # pick mode + colour from menus
    python3 generate-preview.py travel-svgrepo-com           # icons mode, pick colour
    python3 generate-preview.py --color red                  # every icon + info, red tag
    python3 generate-preview.py travel-svgrepo-com --color "steel blue"
    python3 generate-preview.py --color red --no-info        # icon side only
    python3 generate-preview.py --mode tags                  # pick a tag config + colour
    python3 generate-preview.py --mode tags --tag-config config-john-doe --color red
"""

import argparse
import importlib.util
import os
import sys
import tempfile

from taggen.cache import cache_key, cache_path_for, restore, store
from taggen.config import load_config
from taggen.configselect import (
    config_name,
    list_tag_configs,
    prompt_tag_config,
    resolve_config,
)
from taggen.icon import icon_vars
from taggen.runner import build_commands, resolve_openscad, run_commands
from taggen.varmap import build_scad_vars, info_tag_vars, to_define_args

ROOT = os.path.dirname(os.path.abspath(__file__))
TAG_STL = os.path.join(ROOT, "output", "stl", "tag.stl")
ICONS_DIR = os.path.join(ROOT, "output", "stl", "icons")
ICONS_SRC = os.path.join(ROOT, "icons")  # the SVG sources behind the icon STLs
OUTPUT_DIR = os.path.join(ROOT, "output", "previews")
CONFIGS_DIR = os.path.join(ROOT, "configs")
CONFIG = os.path.join(CONFIGS_DIR, "config.yaml")

ICON_COLOR = "#ffffff"  # the icon (and the info text/QR) is always white

# Tag colours, in the order requested. Names map to filament-like hex values;
# the lowercased name (spaces -> hyphens) becomes the PNG filename suffix.
COLORS = {
    "Yellow": "#ffd500",
    "Steel blue": "#4682b4",
    "Turquoise blue": "#1ab7c5",
    "Gray": "#808080",
    "Orange": "#ff7f0e",
    "Brown": "#7a4a23",
    "Black": "#111111",
    "Bubblegum pink": "#fd6c9e",
    "Light pink": "#ffb6c1",
    "Lime green": "#32cd32",
    "Red": "#e02020",
    "Dark violet": "#9400d3",
}


def _load_icons_module():
    """Load generate-icons.py (hyphenated name) so its main() can be invoked."""
    path = os.path.join(ROOT, "generate-icons.py")
    spec = importlib.util.spec_from_file_location("generate_icons", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_generate_tag(argv, openscad, runner):
    """Invoke the generate-tag pipeline in-process, reusing the resolved tools.

    Threads the already-resolved ``openscad`` and the active ``runner`` through
    so the cascade neither re-resolves the binary nor bypasses a test runner.
    Raises ``RuntimeError`` if generate-tag exits non-zero.
    """
    from taggen.cli import main as tag_main

    code = tag_main(argv, resolver=lambda _path=None: openscad, runner=runner)
    if code != 0:
        raise RuntimeError("generate-tag failed while regenerating the tag STL.")


def run_generate_icons(argv, openscad, runner):
    """Invoke generate-icons in-process, reusing the resolved tools.

    Same threading as ``run_generate_tag``. Raises ``RuntimeError`` if
    generate-icons exits non-zero.
    """
    module = _load_icons_module()
    code = module.main(argv, resolver=lambda _path=None: openscad, runner=runner)
    if code != 0:
        raise RuntimeError("generate-icons failed while regenerating icon STLs.")


def ensure_tag_stl(ns, openscad, runner):
    """Make sure the base tag STL exists, generating it with generate-tag if not.

    generate-tag exports the bare ``tag.stl`` body (the preview base) as a side
    effect. The config is passed through only when ``--config`` names a real
    file; otherwise no config is forwarded so generate-tag shows its own config
    menu (the historical default ``configs/config.yaml`` may no longer exist).
    Raises ``FileNotFoundError`` if the tag STL is still absent afterwards.
    """
    if os.path.isfile(ns.tag):
        return
    argv = [ns.config] if (ns.config and os.path.isfile(ns.config)) else []
    print(
        f"Tag STL missing ({ns.tag}); generating it with generate-tag...",
        flush=True,
    )
    run_generate_tag(argv, openscad, runner)
    if not os.path.isfile(ns.tag):
        raise FileNotFoundError(
            f"Tag STL still not found after generate-tag: {ns.tag}"
        )


def ensure_icon_stls(ns, openscad, runner):
    """Make sure the needed icon STLs exist, rendering missing ones via generate-icons.

    The needed stems are the requested ``ns.icons`` (by stem/filename) or, when
    none are given, every ``.svg`` stem in ``ICONS_SRC`` (the "all" default).
    Any stem without a matching ``<stem>.stl`` in ``ns.icons_dir`` is rendered in
    a single generate-icons call; when nothing is missing it is not invoked.
    """
    if ns.icons:
        stems = [os.path.splitext(os.path.basename(name))[0] for name in ns.icons]
    elif os.path.isdir(ICONS_SRC):
        stems = sorted(
            os.path.splitext(f)[0]
            for f in os.listdir(ICONS_SRC)
            if f.lower().endswith(".svg")
        )
    else:
        return

    missing = [
        stem
        for stem in stems
        if not os.path.isfile(os.path.join(ns.icons_dir, stem + ".stl"))
    ]
    if missing:
        print(
            f"Missing icon STLs ({', '.join(missing)}); generating with "
            "generate-icons...",
            flush=True,
        )
        run_generate_icons(missing, openscad, runner)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Render a white-icon-on-coloured-tag PNG for each tag colour."
    )
    parser.add_argument(
        "icons",
        nargs="*",
        help="Optional icon STL names to render (stem or filename). Default: all.",
    )
    parser.add_argument(
        "--mode",
        choices=["icons", "tags"],
        default=None,
        help="What to preview. Omit to pick from a console menu (unless icons "
        "or --color are given, which default to icons).",
    )
    parser.add_argument("--tag", default=TAG_STL, help="Path to the tag STL.")
    parser.add_argument(
        "--config",
        default=CONFIG,
        help="YAML config driving the info side in icons mode (default "
        "configs/config.yaml).",
    )
    parser.add_argument(
        "--configs-dir",
        default=CONFIGS_DIR,
        help="Directory of selectable tag configs for tags mode.",
    )
    parser.add_argument(
        "--tag-config",
        default=None,
        help="Tag config name (or path) to preview in tags mode. Omit to pick "
        "from a console menu.",
    )
    parser.add_argument(
        "--no-info",
        action="store_true",
        help="Skip the info (name/QR) side; render only the icon side.",
    )
    parser.add_argument(
        "--icons-dir", default=ICONS_DIR, help="Directory of icon STLs."
    )
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR,
        help="Previews root. Icon PNGs go in its icons/ subfolder, tag-name "
        "(info side) PNGs in tags/.",
    )
    parser.add_argument(
        "--color",
        default=None,
        help="Tag colour(s) by name, comma-separated (any of: " + ", ".join(COLORS)
        + ", or 'all'). Omit to pick from a console menu.",
    )
    parser.add_argument(
        "--icon-color", default=ICON_COLOR, help="Icon colour (default white)."
    )
    parser.add_argument(
        "--size", default="1024,1024", help="PNG width,height (default 1024,1024)."
    )
    parser.add_argument(
        "--camera",
        default=None,
        help="OpenSCAD --camera string. Omit to auto-frame with --viewall.",
    )
    parser.add_argument(
        "--projection",
        default="ortho",
        choices=["ortho", "perspective"],
        help="Camera projection (default ortho).",
    )
    parser.add_argument(
        "--colorscheme",
        default="Nature",
        help="OpenSCAD scheme (default Nature: a flat near-white background).",
    )
    parser.add_argument(
        "--no-whiten",
        action="store_true",
        help="Keep the scheme's background instead of snapping it to pure white.",
    )
    parser.add_argument(
        "--openscad", default=None, help="Path/command to the OpenSCAD binary."
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Force a fresh render of the info side, ignoring any cached STL. "
        "The result is still written back to the cache.",
    )
    return parser.parse_args(argv)


def select_icons(icons_dir, requested):
    """Return absolute paths of icon STLs to render.

    With no ``requested`` names, returns every ``.stl`` in ``icons_dir`` sorted
    by name. Otherwise matches each requested name by stem or filename, raising
    ``ValueError`` for any request that doesn't resolve.
    """
    available = sorted(
        f for f in os.listdir(icons_dir) if f.lower().endswith(".stl")
    )
    if not requested:
        return [os.path.join(icons_dir, f) for f in available]

    by_stem = {os.path.splitext(f)[0]: f for f in available}
    by_name = {f: f for f in available}
    selected = []
    for name in requested:
        match = by_name.get(name) or by_stem.get(os.path.splitext(name)[0])
        if not match:
            raise ValueError(f"Icon STL not found in {icons_dir}: {name}")
        selected.append(os.path.join(icons_dir, match))
    return selected


def select_color(requested):
    """Return the (name, hex) tag colour for ``requested``.

    Matching is case-insensitive on the palette names. Raises ``ValueError``
    if the colour isn't in ``COLORS``.
    """
    lookup = {name.lower(): (name, value) for name, value in COLORS.items()}
    match = lookup.get(requested.lower())
    if not match:
        raise ValueError(
            f"Unknown colour: {requested}. Available: {', '.join(COLORS)}"
        )
    return match


def select_colors(requested):
    """Return a list of (name, hex) tag colours for ``requested``.

    ``all`` (case-insensitive) selects the whole palette in order. Otherwise the
    value is split on commas and each token resolves to a colour via
    ``select_color``; order is preserved and duplicates dropped, so
    ``"gray, orange"`` yields two colours. Raises ``ValueError`` if a token isn't
    in ``COLORS`` or nothing resolves.
    """
    if requested.strip().lower() == "all":
        return list(COLORS.items())
    selected = []
    for token in requested.split(","):
        token = token.strip()
        if not token:
            continue
        entry = select_color(token)
        if entry not in selected:
            selected.append(entry)
    if not selected:
        raise ValueError("No colour selected.")
    return selected


def resolve_color_choice(choice, items, all_number):
    """Resolve a comma-separated colour ``choice`` to a list of (name, hex).

    Each comma-separated token may be a menu number or a palette name (case-
    insensitive); a token of ``all`` or the "All colours" number selects the
    whole palette. Order is preserved and duplicates dropped, so ``"4,5"`` or
    ``"gray, orange"`` both yield two colours. Raises ``ValueError`` on any token
    that doesn't resolve, or if nothing is selected.
    """
    selected = []

    def add(entry):
        if entry not in selected:
            selected.append(entry)

    for raw in choice.split(","):
        token = raw.strip()
        if not token:
            continue
        if token.lower() == "all" or (
            token.isdigit() and int(token) == all_number
        ):
            for entry in items:
                add(entry)
            continue
        if token.isdigit():
            number = int(token)
            if not 1 <= number <= len(items):
                raise ValueError(f"Enter a number between 1 and {all_number}.")
            add(items[number - 1])
        else:
            add(select_color(token))
    if not selected:
        raise ValueError("No colour selected.")
    return selected


def prompt_color():
    """Show a numbered menu of palette colours and return the chosen colours.

    Returns a list of (name, hex) tuples. Accepts a comma-separated mix of menu
    numbers and colour names (e.g. ``4,5`` or ``gray, orange``), or ``all`` /
    the "All colours" number for the whole palette (all case-insensitive), and
    re-asks on invalid input. Raises ``ValueError`` if the input stream closes
    (e.g. piped/non-interactive with no selection).
    """
    items = list(COLORS.items())
    all_number = len(items) + 1
    print("Select a tag colour:")
    for number, (name, value) in enumerate(items, start=1):
        print(f"  {number:2d}) {name} ({value})")
    print(f"  {all_number:2d}) All colours")

    while True:
        try:
            choice = input(
                "Colour number(s), name(s), or 'all' (comma-separated): "
            ).strip()
        except EOFError:
            raise ValueError("No colour selected (input closed).")
        if not choice:
            continue
        try:
            return resolve_color_choice(choice, items, all_number)
        except ValueError as exc:
            print(exc)


def prompt_mode():
    """Show the top-level menu and return ``"icons"`` or ``"tags"``.

    Accepts the menu number or the mode name (case-insensitive), re-asks on
    invalid input. Raises ``ValueError`` if the input stream closes (e.g. piped/
    non-interactive with no selection).
    """
    modes = [
        ("icons", "every icon on a coloured tag"),
        ("tags", "a single tag config's info side"),
    ]
    print("What do you want to preview?")
    for number, (name, blurb) in enumerate(modes, start=1):
        print(f"  {number}) {name.capitalize():6s} - {blurb}")

    while True:
        try:
            choice = input("Choice (number or name): ").strip().lower()
        except EOFError:
            raise ValueError("No mode selected (input closed).")
        if not choice:
            continue
        if choice.isdigit():
            number = int(choice)
            if 1 <= number <= len(modes):
                return modes[number - 1][0]
            print(f"Enter a number between 1 and {len(modes)}.")
            continue
        for name, _ in modes:
            if choice == name:
                return name
        print("Enter 'icons' or 'tags'.")


def color_slug(name):
    """Filename-safe suffix for a colour name (lowercase, spaces -> hyphens)."""
    return name.lower().replace(" ", "-")


def scad_source(tag_stl, tag_color, icon_stl, icon_color):
    """SCAD that imports both STLs, each wrapped in its own ``color()``.

    Paths are escaped so backslashes/quotes survive into the string literal.
    ``import()`` happens in the source coordinate space, so the meshes overlay
    exactly as they were exported.
    """

    def lit(path):
        return '"' + path.replace("\\", "\\\\").replace('"', '\\"') + '"'

    return (
        f'color("{tag_color}") import({lit(tag_stl)});\n'
        f'color("{icon_color}") import({lit(icon_stl)});\n'
    )


def build_png_command(openscad, scad_path, png_path, ns):
    """Build the OpenSCAD preview-PNG export command.

    ``--preview`` (ThrownTogether) is what keeps the per-object ``color()``; a
    plain ``--render`` would discard it.
    """
    cmd = [
        openscad,
        "-o",
        png_path,
        "--preview",
        f"--imgsize={ns.size}",
        f"--projection={ns.projection}",
        f"--colorscheme={ns.colorscheme}",
    ]
    if ns.camera:
        cmd.append(f"--camera={ns.camera}")
    else:
        cmd += ["--autocenter", "--viewall"]
    cmd.append(scad_path)
    return cmd


def whiten_background(png_path):
    """Snap the flat background colour to pure white in-place.

    Samples the top-left corner (always background under ``--viewall`` padding)
    and replaces every exactly-matching pixel with ``#ffffff``. Returns ``True``
    on success, ``False`` if Pillow isn't installed (render is left untouched).
    """
    try:
        from PIL import Image
    except ImportError:
        return False

    image = Image.open(png_path).convert("RGB")
    background = image.getpixel((0, 0))
    white = (255, 255, 255)
    if background != white:
        image.putdata(
            [white if px == background else px for px in image.getdata()]
        )
        image.save(png_path)
    return True


def render_info_stl(config_path, openscad, runner, no_cache=False):
    """Render the info-side STL -- the name/QR/phone/email text plus the icon, no body.

    Drives the same generate-tag pipeline as ``generate-tag.py`` from
    ``config_path``, but overrides ``HIDE_TAG``/``Facedown_Mode`` so the text +
    QR + configured icon come out (no tag body) at a real thickness -- ready to
    overlay in white on the coloured tag body. Reuses the taggen render cache, so
    an unchanged info side is restored instead of re-rendered. With ``no_cache``
    set, the cache is never read (always re-render) but the fresh result is still
    written back, refreshing it. Returns the STL path.
    """
    config = load_config(config_path)

    # Text + QR + icon, no body (ENABLE_SVG/FILE come from icon_vars) -- the same
    # info side generate-tag exports, ready to overlay in white on the tag body.
    scad_vars = info_tag_vars(build_scad_vars(config, icon_vars=icon_vars(config)))
    define_args = to_define_args(scad_vars)

    # Absolute path: the overlay SCAD lives in a temp dir, so a relative
    # import() would resolve against /tmp instead of the output dir.
    output_dir = os.path.abspath(config["output_dir"])
    os.makedirs(output_dir, exist_ok=True)
    info_stl = os.path.join(output_dir, config["output_name"] + "-info.stl")

    template = config["template"]
    backend = config["backend"]
    cache_dir = config["cache_dir"]
    cached = None
    if cache_dir:
        cached = cache_path_for(cache_dir, cache_key(template, define_args, backend))
        if not no_cache and restore(cached, info_stl):
            print(f"Reused cached info side: {info_stl}")
            return info_stl

    commands = build_commands(
        openscad, template, define_args, info_stl, backend=backend
    )
    print(f"Rendering info side (name/QR) -> {info_stl}", flush=True)
    runner(commands)
    if cached:
        store(info_stl, cached)
    return info_stl


def render_preview(openscad, runner, ns, overlay_stl, color_hex, png_path, label):
    """Render one overlay PNG: coloured tag + white ``overlay_stl``.

    Writes a throwaway SCAD with the two coloured imports, exports the preview
    PNG, then snaps the background to white. Returns the ``whiten_background``
    result (``True`` if whitened or skipped, ``False`` if Pillow is missing).
    """
    source = scad_source(ns.tag, color_hex, overlay_stl, ns.icon_color)

    # OpenSCAD needs a file on disk to import from; the temp SCAD is only the
    # two coloured imports and is removed once the PNG is out.
    with tempfile.NamedTemporaryFile("w", suffix=".scad", delete=False) as handle:
        handle.write(source)
        scad_path = handle.name
    try:
        command = build_png_command(openscad, scad_path, png_path, ns)
        print(label, flush=True)
        runner([command])
    finally:
        os.unlink(scad_path)

    whitened = ns.no_whiten or whiten_background(png_path)
    print(f"Wrote {png_path}")
    return whitened


def previews_dirs(output_dir):
    """Split the previews root into its ``icons`` and ``tags`` subfolders.

    Icon previews land in ``<output_dir>/icons`` and the info side (the
    name/QR/phone face) in ``<output_dir>/tags``, so the two kinds never mix.
    Returns ``(icons_dir, tags_dir)``.
    """
    return (
        os.path.join(output_dir, "icons"),
        os.path.join(output_dir, "tags"),
    )


def render_overlays(openscad, runner, ns, overlays, colors, out_dir):
    """Render every (colour, overlay) pair to ``<out_dir>/<stem>-<slug>.png``.

    ``overlays`` is the ordered list of white overlay STL paths (icons or the
    info side); each is composited on the coloured tag once per colour into
    ``out_dir`` (created if absent). Prints a one-time note if Pillow is missing
    so the near-white background can't be snapped to pure white.
    """
    os.makedirs(out_dir, exist_ok=True)
    whiten_warned = False
    total = len(overlays) * len(colors)
    step = 0

    for color_name, color_hex in colors:
        slug = color_slug(color_name)
        for overlay_stl in overlays:
            step += 1
            stem = os.path.splitext(os.path.basename(overlay_stl))[0]
            png_path = os.path.join(out_dir, f"{stem}-{slug}.png")
            whitened = render_preview(
                openscad,
                runner,
                ns,
                overlay_stl,
                color_hex,
                png_path,
                f"[{step}/{total}] {stem} / {color_name} -> {png_path}",
            )
            if not whitened and not whiten_warned:
                print(
                    "Note: Pillow not installed; leaving the near-white "
                    "background as rendered (pip install Pillow to snap it to "
                    "pure white).",
                    file=sys.stderr,
                )
                whiten_warned = True


def resolve_mode(ns):
    """Decide the preview mode: the explicit ``--mode``, an icons default, or a menu.

    Honours ``--mode`` when given. Otherwise, a scripted call that named icons or
    a ``--color`` defaults to icons (preserving prior non-interactive behaviour);
    a bare interactive call shows the top-level menu.
    """
    if ns.mode:
        return ns.mode
    if ns.icons or ns.color:
        return "icons"
    return prompt_mode()


def resolve_tag_config(ns):
    """Return the tag config path for tags mode (``--tag-config`` or a menu).

    Delegates to the shared ``resolve_config``: ``--tag-config`` may be a file
    path or a config name (no extension, case-insensitive) matched against
    ``--configs-dir``; omitting it offers the configs as a console menu.
    """
    return resolve_config(ns.tag_config, ns.configs_dir)


def pick_colors(ns):
    """Resolve the tag colours: the explicit ``--color``, or the console menu."""
    return select_colors(ns.color) if ns.color else prompt_color()


def run_icons_mode(openscad, runner, ns):
    """Render the icon side per icon plus the info side (the original flow)."""
    ensure_icon_stls(ns, openscad, runner)
    icons = select_icons(ns.icons_dir, ns.icons)
    if not icons:
        raise ValueError(f"No icon STLs found in {ns.icons_dir}")

    colors = pick_colors(ns)
    icons_dir, tags_dir = previews_dirs(ns.output_dir)
    render_overlays(openscad, runner, ns, icons, colors, icons_dir)
    # The info side is rendered once (it depends on neither icon nor colour) and
    # filed under tags/, since it's a tag-name face rather than an icon.
    if not ns.no_info:
        info_stl = render_info_stl(ns.config, openscad, runner, no_cache=ns.no_cache)
        render_overlays(openscad, runner, ns, [info_stl], colors, tags_dir)


def run_tags_mode(openscad, runner, ns):
    """Render one selected tag config's info side, one preview per colour."""
    config_path = resolve_tag_config(ns)
    print(f"Previewing tag config: {config_name(config_path)}")
    colors = pick_colors(ns)
    _, tags_dir = previews_dirs(ns.output_dir)
    info_stl = render_info_stl(config_path, openscad, runner, no_cache=ns.no_cache)
    render_overlays(openscad, runner, ns, [info_stl], colors, tags_dir)


def main(argv=None, resolver=resolve_openscad, runner=run_commands):
    """Preview icons or a single tag config in chosen colours. Returns an exit code."""
    ns = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        openscad = resolver(ns.openscad)
        ensure_tag_stl(ns, openscad, runner)

        if resolve_mode(ns) == "tags":
            run_tags_mode(openscad, runner, ns)
        else:
            run_icons_mode(openscad, runner, ns)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
