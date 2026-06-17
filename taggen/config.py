"""Load and validate the YAML config that drives tag generation."""

import os

import yaml

DEFAULTS = {
    "template": "scripts/dados-tag.scad",
    "output_dir": "output/stl",
    "openscad": None,
    "backend": None,
    "cache_dir": ".taggen-cache",
}

REQUIRED = ["name", "last-name", "qr_action", "phone_number", "email"]


def _slugify(*parts):
    """Filename-safe slug: lowercase the parts, join on hyphens, collapse spaces."""
    return "-".join(" ".join(parts).lower().split())


def load_config(path):
    """Read ``path``, validate required fields and apply defaults.

    Raises ``FileNotFoundError`` if the file is missing and ``ValueError`` with
    a descriptive message for any missing or malformed required field.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path) as fh:
        config = yaml.safe_load(fh) or {}

    if not isinstance(config, dict):
        raise ValueError("Config must be a mapping of keys to values")

    for key in REQUIRED:
        if key not in config or config[key] in (None, ""):
            raise ValueError(f"Missing required config field: {key}")

    merged = dict(DEFAULTS)
    merged.update(config)

    # Default the output filename to a slug of the name, so configs don't need
    # to repeat it: "John" + "Doe" -> "john-doe".
    if not merged.get("output_name"):
        merged["output_name"] = _slugify(merged["name"], merged["last-name"])

    return merged
