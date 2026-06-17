"""Command-line entry point: config -> OpenSCAD STL export."""

import argparse
import os
import sys

from taggen.cache import cache_key, cache_path_for, restore, store
from taggen.config import load_config
from taggen.configselect import resolve_config
from taggen.icon import aspect_vars, icon_vars
from taggen.runner import build_commands, resolve_openscad, run_commands
from taggen.varmap import (
    blank_tag_vars,
    build_scad_vars,
    info_tag_vars,
    to_define_args,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIGS_DIR = os.path.join(ROOT, "configs")


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Generate an STL from a SCAD tag template using a YAML config."
    )
    parser.add_argument(
        "config",
        nargs="?",
        default=None,
        help="Path or name of the YAML config file. Omit to pick from a "
        "console menu of configs/.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Force a fresh render, ignoring any cached STL. The result is "
        "still written back to the cache.",
    )
    return parser.parse_args(argv)


def output_path(config):
    """Path for the printable info side -- the name/QR/icon white overlay.

    The full combined tag (body + info) is no longer exported here; only this
    ``<output_name>-info.stl`` and the bare ``tag.stl`` body are written.
    """
    return os.path.join(config["output_dir"], config["output_name"]) + "-info.stl"


def blank_output_path(config):
    """Path for the info-less tag body (the preview tool's default base).

    Always ``<output_dir>/tag.stl``. The info side is exported as
    ``<output_name>-info.stl``, so the two never collide.
    """
    return os.path.join(config["output_dir"], "tag.stl")


def render_stl(config, openscad, define_args, stl_path, runner, label, no_cache=False):
    """Render one STL, reusing the cache when enabled. Returns the path.

    With ``no_cache`` set, the cache is never *read* (always re-render) but the
    fresh result is still *written* back, refreshing the cache.
    """
    backend = config["backend"]
    cache_dir = config["cache_dir"]
    cached = None
    if cache_dir:
        key = cache_key(config["template"], define_args, backend)
        cached = cache_path_for(cache_dir, key)
        if not no_cache and restore(cached, stl_path):
            print(f"Reused cached STL: {stl_path}")
            return stl_path

    commands = build_commands(
        openscad, config["template"], define_args, stl_path, backend=backend
    )
    print(label, flush=True)
    runner(commands)
    if cached:
        store(stl_path, cached)
    print(f"Wrote {stl_path}")
    return stl_path


def main(
    argv=None,
    resolver=resolve_openscad,
    runner=run_commands,
    aspect=aspect_vars,
    configs_dir=CONFIGS_DIR,
):
    """Run the full pipeline. Returns a process exit code."""
    ns = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        config_path = resolve_config(ns.config, configs_dir)
        config = load_config(config_path)
        openscad = resolver(config["openscad"])

        iv = icon_vars(config)
        if iv.get("ENABLE_SVG"):
            # Measure the icon's aspect ratio so the template fits it inside an
            # SVG_SIZE box instead of overflowing vertically on tall icons.
            iv.update(aspect(iv["FILE"], openscad))
        scad_vars = build_scad_vars(config, icon_vars=iv)
        os.makedirs(config["output_dir"], exist_ok=True)

        render_stl(
            config,
            openscad,
            to_define_args(info_tag_vars(scad_vars)),
            output_path(config),
            runner,
            "Rendering info side STL with OpenSCAD (this can take a few minutes)...",
            no_cache=ns.no_cache,
        )
        # Also export the bare tag body (no text/QR/icon) for the preview tool.
        render_stl(
            config,
            openscad,
            to_define_args(blank_tag_vars(scad_vars)),
            blank_output_path(config),
            runner,
            "Rendering blank tag STL...",
            no_cache=ns.no_cache,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
