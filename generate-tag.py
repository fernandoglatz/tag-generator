#!/usr/bin/env python3
"""Entry point: generate an STL from a SCAD tag template + YAML config.

Run with no config to pick one from a console menu of configs/; pass a path or
config name to skip the menu.

Usage:
    python3 generate-tag.py                          # pick a config from a menu
    python3 generate-tag.py configs/config.yaml      # explicit path
    python3 generate-tag.py config-john-doe              # by config name
"""

from taggen.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
