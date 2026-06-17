"""Map a parsed config dict to OpenSCAD variables and ``-D`` CLI arguments."""

from taggen.phone import derive_phone_lines

# Text is auto-sized to span the tag's usable width: the font size is roughly
# REFERENCE_WIDTH / len(text), capped at MAX_DERIVED_SIZE. REFERENCE_WIDTH is
# tuned by rendering the HarmonyOS Sans SC fallback so the 24-char sample email
# lands at size 17 -- the size at which it spans the QR's ~44 mm width (the QR
# occupies x in [6, 50] and the text left edge sits at x~5.5). The name lines
# (1/2) start at the same left edge and share that width, so they reuse the same
# reference. The phone lines (4/5) keep the template's default sizes unless the
# config overrides them.
REFERENCE_WIDTH = 408
MAX_DERIVED_SIZE = 33


def auto_size(text):
    """Font size that makes ``text`` roughly fill the tag width, capped."""
    length = len(text)
    if length <= 0:
        return MAX_DERIVED_SIZE
    return min(MAX_DERIVED_SIZE, round(REFERENCE_WIDTH / length))


def build_scad_vars(config, icon_vars=None):
    """Build an ordered dict of SCAD variable name -> value from ``config``.

    Derives lines 4/5 from the phone number, maps the email to line 6, defaults
    ``HIDE_TAG`` to ``False`` so the tag body is exported, merges any
    ``icon_vars`` (resolved icon path / toggle), then applies any ``extra``
    overrides last (so they win over both computed and icon values).
    """
    name = config["name"]
    last_name = config["last-name"]

    line4, line5 = derive_phone_lines(config["phone_number"])
    email = config["email"]

    # Auto-fit the name (lines 1/2) to the tag width. Both lines render at one
    # common size -- the size of whichever name is longer -- so they stay
    # visually matched. Auto-fit the email to the QR width too. The phone lines
    # (4/5) keep the template's default sizes unless the config pins them.
    size_name = min(auto_size(name), auto_size(last_name))
    size6 = config.get("size_line_6") or auto_size(email)

    scad_vars = {
        # Show the printable tag body (the template hides it by default).
        "HIDE_TAG": False,
        "TEXT_LINE_1": name,
        "SIZE_TEXT_LINE_1": size_name,
        "TEXT_LINE_2": last_name,
        "SIZE_TEXT_LINE_2": size_name,
        "QR_ACTION": config["qr_action"],
        "Phone_Number": config["phone_number"],
        "Email": email,
        "TEXT_LINE_4": line4,
        "TEXT_LINE_5": line5,
        "TEXT_LINE_6": email,
        "SIZE_TEXT_LINE_6": size6,
    }

    # Only pin the phone-line sizes when the config asks for it; otherwise the
    # template's defaults (33 / 25) apply.
    if config.get("size_line_4") is not None:
        scad_vars["SIZE_TEXT_LINE_4"] = config["size_line_4"]
    if config.get("size_line_5") is not None:
        scad_vars["SIZE_TEXT_LINE_5"] = config["size_line_5"]

    scad_vars.update(icon_vars or {})
    scad_vars.update(config.get("extra") or {})
    return scad_vars


def blank_tag_vars(scad_vars):
    """Return a copy of ``scad_vars`` with all info stripped to the bare body.

    Turns off the QR code, the SVG icon and every text line (1-9) while keeping
    the tag body (``HIDE_TAG=False``). Used to export a plain tag onto which the
    preview tool overlays coloured icons. The input dict is left untouched.
    """
    blank = dict(scad_vars)
    blank["HIDE_TAG"] = False
    blank["HIDE_QR"] = True
    blank["ENABLE_SVG"] = False
    for i in range(1, 10):
        blank[f"ADD_TEXT_LINE_{i}"] = False
    return blank


def info_tag_vars(scad_vars):
    """Return a copy of ``scad_vars`` for the info side: text/QR/icon, no body.

    Hides the tag body (``HIDE_TAG=True``) while keeping the QR, the configured
    icon and every text line, and gives the glyphs real thickness so the result
    prints as a white overlay for the coloured tag body. ``Facedown_Mode`` is
    turned off (it would extrude a paper-thin shell that barely shows over the
    tag) and the icon's Z thickness (``SVG_THICKNESS``) is pinned to the text
    thickness (0.5) so it sits flush with the glyphs instead of towering at the
    template's default. The input dict is left untouched.
    """
    info = dict(scad_vars)
    info["HIDE_TAG"] = True
    info["Facedown_Mode"] = False
    info["SVG_THICKNESS"] = 0.5
    return info


def _render_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, tuple)):
        # An OpenSCAD vector literal (e.g. SVG_LOCATION=[10, -7]) so the template
        # can index it; quoting would make it a string and break SVG_LOCATION[0].
        return "[" + ", ".join(_render_value(item) for item in value) + "]"
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def to_define_args(scad_vars):
    """Return a flat list of ``-D NAME=value`` arguments for the OpenSCAD CLI."""
    args = []
    for name, value in scad_vars.items():
        args.append("-D")
        args.append(f"{name}={_render_value(value)}")
    return args
