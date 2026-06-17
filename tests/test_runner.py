import pytest

from taggen.runner import build_commands, resolve_openscad, run_commands


def test_build_stl_command():
    cmds = build_commands("openscad", "tpl.scad", ["-D", 'X="y"'], "out/tag.stl")
    assert len(cmds) == 1
    assert cmds[0] == ["openscad", "-o", "out/tag.stl", "-D", 'X="y"', "tpl.scad"]


def test_build_stl_command_with_backend():
    cmds = build_commands(
        "openscad", "tpl.scad", ["-D", 'X="y"'], "out/tag.stl", backend="manifold"
    )
    assert cmds[0] == [
        "openscad",
        "--backend=manifold",
        "-o",
        "out/tag.stl",
        "-D",
        'X="y"',
        "tpl.scad",
    ]


def test_build_stl_command_no_backend_omits_flag():
    cmds = build_commands(
        "openscad", "tpl.scad", [], "out/tag.stl", backend=None
    )
    assert not any(a.startswith("--backend") for a in cmds[0])


def test_resolve_openscad_uses_explicit_existing_path(tmp_path):
    fake = tmp_path / "openscad"
    fake.write_text("#!/bin/sh\n")
    fake.chmod(0o755)
    assert resolve_openscad(str(fake)) == str(fake)


def test_resolve_openscad_missing_raises():
    with pytest.raises(FileNotFoundError) as exc:
        resolve_openscad("/nonexistent/openscad-binary-xyz")
    assert "OpenSCAD" in str(exc.value)


def test_run_commands_streams_child_output(capfd):
    # Long OpenSCAD renders must show progress, not be swallowed.
    run_commands([["sh", "-c", "echo HELLO_FROM_CHILD"]])
    assert "HELLO_FROM_CHILD" in capfd.readouterr().out


def test_run_commands_raises_on_failure():
    with pytest.raises(RuntimeError):
        run_commands([["sh", "-c", "exit 5"]])
