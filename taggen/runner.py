"""Locate the OpenSCAD binary, build its command and run the export."""

import os
import shutil
import subprocess

INSTALL_HINT = (
    "OpenSCAD was not found. Install it (https://openscad.org/downloads.html) "
    "or set 'openscad' in the config to the binary path."
)


def resolve_openscad(openscad):
    """Return a usable OpenSCAD binary path.

    Accepts an explicit path/command (from config) or ``None`` to search
    ``PATH``. Raises ``FileNotFoundError`` with an install hint if none works.
    """
    candidate = openscad or "openscad"

    if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
        return candidate

    found = shutil.which(candidate)
    if found:
        return found

    raise FileNotFoundError(INSTALL_HINT)


def build_commands(openscad, template, define_args, stl_path, backend=None):
    """Build the OpenSCAD command list for the STL export.

    ``backend`` selects the geometry engine (e.g. ``"manifold"``, far faster
    than the default CGAL backend on OpenSCAD 2023.06+). Omit it on older
    builds that don't recognise ``--backend``.
    """
    backend_args = [f"--backend={backend}"] if backend else []
    return [[openscad, *backend_args, "-o", stl_path, *define_args, template]]


def run_commands(commands):
    """Run each command, streaming its output live.

    Output is inherited (not captured) so OpenSCAD's progress is visible during
    long renders. Raises ``RuntimeError`` naming the failed command on a
    non-zero exit.
    """
    for cmd in commands:
        result = subprocess.run(cmd)
        if result.returncode != 0:
            raise RuntimeError(
                f"OpenSCAD exited with status {result.returncode}: {' '.join(cmd)}"
            )
