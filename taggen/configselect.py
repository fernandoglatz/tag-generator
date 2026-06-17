"""Discover and select a tag YAML config, by argument or interactive menu.

Shared by generate-tag.py (the STL pipeline) and generate-preview.py so the
config menu behaves identically in both. ``config*.yaml`` files under the
configs directory are the selectable set; either tool can take an explicit
path/name or, given none, fall back to a numbered console menu.
"""

import os


def config_name(path):
    """Display name for a config path (filename without the .yaml suffix)."""
    return os.path.splitext(os.path.basename(path))[0]


def list_tag_configs(configs_dir):
    """Return absolute paths of selectable tag configs, sorted by name.

    Matches ``config*.yaml`` in ``configs_dir``. A missing directory yields an
    empty list (the caller reports it), so discovery never raises here.
    """
    try:
        names = os.listdir(configs_dir)
    except FileNotFoundError:
        return []
    matches = sorted(
        n
        for n in names
        if n.startswith("config") and n.lower().endswith(".yaml")
    )
    return [os.path.join(configs_dir, n) for n in matches]


def prompt_tag_config(configs):
    """Show a numbered menu of tag configs and return the chosen path.

    Accepts the menu number or the config name without extension (case-
    insensitive), re-asks on invalid input. Raises ``ValueError`` if the input
    stream closes (e.g. piped/non-interactive with no selection).
    """
    by_name = {config_name(p).lower(): p for p in configs}
    print("Select a tag config:")
    for number, path in enumerate(configs, start=1):
        print(f"  {number:2d}) {config_name(path)}")

    while True:
        try:
            choice = input("Config number or name: ").strip()
        except EOFError:
            raise ValueError("No tag config selected (input closed).")
        if not choice:
            continue
        if choice.isdigit():
            number = int(choice)
            if 1 <= number <= len(configs):
                return configs[number - 1]
            print(f"Enter a number between 1 and {len(configs)}.")
            continue
        match = by_name.get(choice.lower())
        if match:
            return match
        print(f"Unknown config: {choice}. Available: "
              + ", ".join(config_name(p) for p in configs))


def resolve_config(config_arg, configs_dir):
    """Return the config path: the explicit ``config_arg`` or a console menu.

    A ``config_arg`` that is an existing file is used directly; otherwise it is
    matched by name (no extension, case-insensitive) against the configs in
    ``configs_dir``. With no ``config_arg``, the configs are offered as a console
    menu. Raises ``ValueError`` when nothing resolves.
    """
    configs = list_tag_configs(configs_dir)
    if config_arg:
        if os.path.isfile(config_arg):
            return config_arg
        wanted = config_name(config_arg).lower()
        for path in configs:
            if config_name(path).lower() == wanted:
                return path
        raise ValueError(
            f"Tag config not found: {config_arg}. Available: "
            + (", ".join(config_name(p) for p in configs) or "none")
        )
    if not configs:
        raise ValueError(f"No tag configs found in {configs_dir}")
    return prompt_tag_config(configs)
