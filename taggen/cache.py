"""Content-addressed cache for rendered STLs.

A render is keyed by the template's contents, its ``-D`` define args and the
chosen backend, so an unchanged tag is restored from disk instead of being
re-rendered. Note: files *referenced* by the template (e.g. an icon SVG passed
by path) are not hashed -- bump the cache or change the config to force a
re-render after editing one.
"""

import hashlib
import os
import shutil


def cache_key(template, define_args, backend=None):
    """Return a hex digest identifying this render's inputs."""
    h = hashlib.sha256()
    with open(template, "rb") as fh:
        h.update(fh.read())
    h.update(b"\0")
    h.update("\0".join(define_args).encode())
    h.update(b"\0")
    h.update((backend or "").encode())
    return h.hexdigest()


def cache_path_for(cache_dir, key):
    """Return the on-disk path for a cached STL with this key."""
    return os.path.join(cache_dir, key + ".stl")


def restore(cache_path, stl_path):
    """Copy a cached STL to ``stl_path`` if present. Return True if restored."""
    if not os.path.isfile(cache_path):
        return False
    os.makedirs(os.path.dirname(stl_path) or ".", exist_ok=True)
    shutil.copyfile(cache_path, stl_path)
    return True


def store(stl_path, cache_path):
    """Copy a freshly rendered STL into the cache. No-op if it doesn't exist."""
    if not os.path.isfile(stl_path):
        return
    os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
    shutil.copyfile(stl_path, cache_path)
