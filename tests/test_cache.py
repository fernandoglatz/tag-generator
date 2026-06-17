import os

from taggen.cache import cache_key, cache_path_for, restore, store


def write_template(tmp_path, text):
    path = tmp_path / "tpl.scad"
    path.write_text(text)
    return str(path)


def test_cache_key_is_deterministic(tmp_path):
    tpl = write_template(tmp_path, "cube();")
    assert cache_key(tpl, ["-D", 'X="y"']) == cache_key(tpl, ["-D", 'X="y"'])


def test_cache_key_changes_with_template_contents(tmp_path):
    tpl = write_template(tmp_path, "cube();")
    key_a = cache_key(tpl, [])
    tmp_path.joinpath("tpl.scad").write_text("sphere();")
    assert cache_key(tpl, []) != key_a


def test_cache_key_changes_with_define_args(tmp_path):
    tpl = write_template(tmp_path, "cube();")
    assert cache_key(tpl, ["-D", 'X="a"']) != cache_key(tpl, ["-D", 'X="b"'])


def test_cache_key_changes_with_backend(tmp_path):
    tpl = write_template(tmp_path, "cube();")
    assert cache_key(tpl, []) != cache_key(tpl, [], backend="manifold")


def test_cache_path_for_uses_key():
    assert cache_path_for("/c", "abc123") == os.path.join("/c", "abc123.stl")


def test_restore_returns_false_when_absent(tmp_path):
    stl = tmp_path / "out" / "tag.stl"
    assert restore(str(tmp_path / "missing.stl"), str(stl)) is False
    assert not stl.exists()


def test_restore_copies_cached_file(tmp_path):
    cached = tmp_path / "cache" / "k.stl"
    cached.parent.mkdir()
    cached.write_text("SOLID")
    stl = tmp_path / "out" / "tag.stl"

    assert restore(str(cached), str(stl)) is True
    assert stl.read_text() == "SOLID"


def test_store_copies_into_cache(tmp_path):
    stl = tmp_path / "out" / "tag.stl"
    stl.parent.mkdir()
    stl.write_text("SOLID")
    cached = tmp_path / "cache" / "k.stl"

    store(str(stl), str(cached))
    assert cached.read_text() == "SOLID"


def test_store_skips_when_source_missing(tmp_path):
    cached = tmp_path / "cache" / "k.stl"
    store(str(tmp_path / "nope.stl"), str(cached))
    assert not cached.exists()
