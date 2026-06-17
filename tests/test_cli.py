import os

from taggen.cli import blank_output_path, main, output_path, parse_args

VALID = """
name: John
last-name: Doe
qr_action: "Wa"
phone_number: "+5511999999999"
email: "john.doe@example.com"
output_dir: "build"
output_name: "john"
"""


def write(tmp_path, text):
    path = tmp_path / "config.yaml"
    path.write_text(text)
    return str(path)


def test_parse_args():
    ns = parse_args(["config.yaml"])
    assert ns.config == "config.yaml"
    assert ns.no_cache is False


def test_parse_args_config_optional():
    ns = parse_args([])
    assert ns.config is None


def test_parse_args_no_cache_flag():
    ns = parse_args(["config.yaml", "--no-cache"])
    assert ns.no_cache is True


def test_output_path():
    config = {"output_dir": "build", "output_name": "john"}
    assert output_path(config) == os.path.join("build", "john-info.stl")


def test_blank_output_path():
    config = {"output_dir": "build", "output_name": "john"}
    assert blank_output_path(config) == os.path.join("build", "tag.stl")


def test_main_prompts_for_config_when_omitted(tmp_path, monkeypatch):
    import io

    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    out_dir = tmp_path / "out"
    text = VALID + f'\noutput_dir: "{out_dir}"\nicon: false\ncache_dir: false\n'
    (configs_dir / "config.yaml").write_text(text)
    monkeypatch.setattr("sys.stdin", io.StringIO("1\n"))
    runs = []

    code = main(
        [],
        resolver=lambda v: "openscad",
        runner=lambda commands: runs.append(commands),
        configs_dir=str(configs_dir),
    )

    assert code == 0
    assert len(runs) == 2  # full tag + blank tag, from the chosen config


def test_main_runs_stl_command_only(tmp_path):
    out_dir = tmp_path / "out"
    text = VALID + f'\noutput_dir: "{out_dir}"\n'
    config_path = write(tmp_path, text)
    runs = []

    def fake_resolver(value):
        return "openscad"

    def fake_runner(commands):
        runs.append(commands)

    code = main([config_path], resolver=fake_resolver, runner=fake_runner)

    assert code == 0
    cmds = runs[0]  # the info side, rendered first
    assert len(cmds) == 1  # stl only
    cmd = cmds[0]
    out = cmd[cmd.index("-o") + 1]
    assert out.endswith("-info.stl")  # info side, not the full tag
    assert "HIDE_TAG=true" in cmd  # body hidden -- info overlay only
    assert not any("--render" in a or ".png" in a for a in cmd)  # no PNG
    assert os.path.isdir(str(out_dir))  # output dir created
    # derived phone line present in the -D args
    assert any('TEXT_LINE_5="(11) 99999-9999"' == a for a in cmd)


def test_main_also_renders_blank_tag(tmp_path):
    out_dir = tmp_path / "out"
    text = VALID + f'\noutput_dir: "{out_dir}"\nicon: false\ncache_dir: false\n'
    config_path = write(tmp_path, text)
    runs = []

    code = main(
        [config_path],
        resolver=lambda v: "openscad",
        runner=lambda commands: runs.append(commands),
    )

    assert code == 0
    assert len(runs) == 2  # full tag, then blank tag
    blank_cmd = runs[1][0]
    out = blank_cmd[blank_cmd.index("-o") + 1]
    assert out == os.path.join(str(out_dir), "tag.stl")
    # info stripped: only the tag body remains
    assert "HIDE_TAG=false" in blank_cmd
    assert "HIDE_QR=true" in blank_cmd
    assert "ENABLE_SVG=false" in blank_cmd
    assert all(f"ADD_TEXT_LINE_{i}=false" in blank_cmd for i in range(1, 10))


def test_main_includes_measured_svg_aspect(tmp_path):
    tpl = tmp_path / "tpl.scad"
    tpl.write_text("cube();")
    svg = tmp_path / "tall.svg"
    svg.write_text("<svg/>")
    out_dir = tmp_path / "out"
    text = (
        VALID
        + f'\noutput_dir: "{out_dir}"\ntemplate: "{tpl}"'
        + f'\nicon: "{svg}"\ncache_dir: false\n'
    )
    config_path = write(tmp_path, text)
    captured = {}

    def fake_runner(commands):
        captured["commands"] = commands

    code = main(
        [config_path],
        resolver=lambda v: "openscad",
        runner=fake_runner,
        aspect=lambda file, openscad: {"SVG_ASPECT": 2.44},
    )

    assert code == 0
    assert "SVG_ASPECT=2.44" in captured["commands"][0]


def test_main_skips_aspect_when_icon_disabled(tmp_path):
    tpl = tmp_path / "tpl.scad"
    tpl.write_text("cube();")
    out_dir = tmp_path / "out"
    text = (
        VALID
        + f'\noutput_dir: "{out_dir}"\ntemplate: "{tpl}"'
        + "\nicon: false\ncache_dir: false\n"
    )
    config_path = write(tmp_path, text)
    captured = {}

    def boom(file, openscad):
        raise AssertionError("aspect must not be measured when icon is disabled")

    code = main(
        [config_path],
        resolver=lambda v: "openscad",
        runner=lambda c: captured.setdefault("commands", c),
        aspect=boom,
    )

    assert code == 0
    assert not any("SVG_ASPECT" in a for a in captured["commands"][0])


def test_main_passes_backend_to_command(tmp_path):
    tpl = tmp_path / "tpl.scad"
    tpl.write_text("cube();")
    out_dir = tmp_path / "out"
    text = (
        VALID
        + f'\noutput_dir: "{out_dir}"\ntemplate: "{tpl}"'
        + "\nicon: false\nbackend: manifold\ncache_dir: false\n"
    )
    config_path = write(tmp_path, text)
    captured = {}

    def fake_runner(commands):
        captured["commands"] = commands

    code = main([config_path], resolver=lambda v: "openscad", runner=fake_runner)

    assert code == 0
    assert "--backend=manifold" in captured["commands"][0]


def test_main_reuses_cache_on_second_run(tmp_path):
    tpl = tmp_path / "tpl.scad"
    tpl.write_text("cube();")
    out_dir = tmp_path / "out"
    cache_dir = tmp_path / "cache"
    text = (
        VALID
        + f'\noutput_dir: "{out_dir}"\ntemplate: "{tpl}"'
        + f'\nicon: false\ncache_dir: "{cache_dir}"\n'
    )
    config_path = write(tmp_path, text)
    calls = {"n": 0}

    def fake_runner(commands):
        calls["n"] += 1
        cmd = commands[0]
        stl = cmd[cmd.index("-o") + 1]
        with open(stl, "w") as fh:
            fh.write("SOLID")

    def resolver(value):
        return "openscad"

    assert main([config_path], resolver=resolver, runner=fake_runner) == 0
    assert calls["n"] == 2  # first run renders the full tag and the blank tag

    assert main([config_path], resolver=resolver, runner=fake_runner) == 0
    assert calls["n"] == 2  # second run restored both from cache, no re-render
    assert (out_dir / "john-info.stl").read_text() == "SOLID"
    assert (out_dir / "tag.stl").read_text() == "SOLID"


def test_main_no_cache_forces_rerender_but_refreshes_cache(tmp_path):
    tpl = tmp_path / "tpl.scad"
    tpl.write_text("cube();")
    out_dir = tmp_path / "out"
    cache_dir = tmp_path / "cache"
    text = (
        VALID
        + f'\noutput_dir: "{out_dir}"\ntemplate: "{tpl}"'
        + f'\nicon: false\ncache_dir: "{cache_dir}"\n'
    )
    config_path = write(tmp_path, text)
    calls = {"n": 0}

    def fake_runner(commands):
        calls["n"] += 1
        cmd = commands[0]
        stl = cmd[cmd.index("-o") + 1]
        with open(stl, "w") as fh:
            fh.write(f"SOLID{calls['n']}")

    def resolver(value):
        return "openscad"

    # First run populates the cache.
    assert main([config_path], resolver=resolver, runner=fake_runner) == 0
    assert calls["n"] == 2

    # --no-cache re-renders both tags instead of restoring them.
    assert (
        main([config_path, "--no-cache"], resolver=resolver, runner=fake_runner)
        == 0
    )
    assert calls["n"] == 4  # re-rendered, not restored

    # The cache was refreshed: a plain run now restores the new contents.
    assert main([config_path], resolver=resolver, runner=fake_runner) == 0
    assert calls["n"] == 4  # restored from the refreshed cache, no re-render
    assert (out_dir / "john-info.stl").read_text() == "SOLID3"


def test_main_missing_openscad_returns_error(tmp_path, capsys):
    config_path = write(tmp_path, VALID.replace('output_dir: "build"', f'output_dir: "{tmp_path / "out"}"'))

    def failing_resolver(value):
        raise FileNotFoundError("OpenSCAD was not found.")

    code = main([config_path], resolver=failing_resolver, runner=lambda c: None)
    assert code == 1
    assert "OpenSCAD" in capsys.readouterr().err
