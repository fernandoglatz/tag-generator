from taggen.varmap import (
    blank_tag_vars,
    build_scad_vars,
    info_tag_vars,
    to_define_args,
)


def sample_config():
    return {
        "name": "John",
        "last-name": "Doe",
        "qr_action": "Wa",
        "phone_number": "+5511999999999",
        "email": "john.doe@example.com",
    }


def test_maps_basic_text_lines():
    v = build_scad_vars(sample_config())
    assert v["TEXT_LINE_1"] == "John"
    assert v["TEXT_LINE_2"] == "Doe"


def test_name_lines_are_auto_sized_and_capped_at_33():
    # Short names fit at the maximum size.
    v = build_scad_vars(sample_config())
    assert v["SIZE_TEXT_LINE_1"] == 33
    assert v["SIZE_TEXT_LINE_2"] == 33


def test_name_lines_share_the_same_size():
    # Lines 1 and 2 must render at one common size even when their lengths
    # differ, so the size is driven by whichever name is longer.
    config = sample_config()
    config["name"] = "Bob"
    config["last-name"] = "Vandermeer-Johnson"  # long -> below the cap
    v = build_scad_vars(config)
    assert v["SIZE_TEXT_LINE_1"] == v["SIZE_TEXT_LINE_2"]
    assert v["SIZE_TEXT_LINE_1"] < 33


def test_passes_through_qr_phone_email():
    v = build_scad_vars(sample_config())
    assert v["QR_ACTION"] == "Wa"
    assert v["Phone_Number"] == "+5511999999999"
    assert v["Email"] == "john.doe@example.com"


def test_derives_phone_lines():
    v = build_scad_vars(sample_config())
    assert v["TEXT_LINE_4"] == "+55"
    assert v["TEXT_LINE_5"] == "(11) 99999-9999"


def test_email_becomes_line_6():
    v = build_scad_vars(sample_config())
    assert v["TEXT_LINE_6"] == "john.doe@example.com"


def test_email_auto_sized_to_fill_qr_width():
    # 20-char email -> size 20, which spans the QR code's width.
    v = build_scad_vars(sample_config())
    assert v["SIZE_TEXT_LINE_6"] == 20


def test_phone_line_sizes_not_emitted_by_default():
    # Lines 4/5 fall back to the template's defaults (33 / 25) when unset.
    v = build_scad_vars(sample_config())
    assert "SIZE_TEXT_LINE_4" not in v
    assert "SIZE_TEXT_LINE_5" not in v


def test_auto_size_shrinks_for_longer_text():
    config = sample_config()
    config["email"] = "a.much.longer.address@example-company.com"  # 41 chars
    v = build_scad_vars(config)
    assert v["SIZE_TEXT_LINE_6"] < 17


def test_explicit_email_size_overrides_auto():
    config = sample_config()
    config["size_line_6"] = 12
    v = build_scad_vars(config)
    assert v["SIZE_TEXT_LINE_6"] == 12


def test_explicit_phone_line_sizes_are_emitted():
    config = sample_config()
    config["size_line_4"] = 33
    config["size_line_5"] = 30
    v = build_scad_vars(config)
    assert v["SIZE_TEXT_LINE_4"] == 33
    assert v["SIZE_TEXT_LINE_5"] == 30


def test_qr_message_not_emitted_by_default():
    # Without qr_message the template's default Text applies.
    v = build_scad_vars(sample_config())
    assert "Text" not in v


def test_qr_message_maps_to_text():
    config = sample_config()
    config["qr_message"] = "I found your bag!"
    v = build_scad_vars(config)
    assert v["Text"] == "I found your bag!"


def test_extra_overrides_qr_message():
    config = sample_config()
    config["qr_message"] = "from qr_message"
    config["extra"] = {"Text": "from extra"}
    v = build_scad_vars(config)
    assert v["Text"] == "from extra"


def test_hide_tag_defaults_false():
    v = build_scad_vars(sample_config())
    assert v["HIDE_TAG"] is False


def test_extra_overrides_applied_last():
    config = sample_config()
    config["extra"] = {"Tag_Size": "L", "HIDE_TAG": True}
    v = build_scad_vars(config)
    assert v["Tag_Size"] == "L"
    assert v["HIDE_TAG"] is True


def test_icon_vars_merged():
    v = build_scad_vars(sample_config(), icon_vars={"FILE": "/abs/x.svg", "ENABLE_SVG": True})
    assert v["FILE"] == "/abs/x.svg"
    assert v["ENABLE_SVG"] is True


def test_extra_wins_over_icon_vars():
    config = sample_config()
    config["extra"] = {"ENABLE_SVG": False}
    v = build_scad_vars(config, icon_vars={"FILE": "/abs/x.svg", "ENABLE_SVG": True})
    assert v["ENABLE_SVG"] is False


def test_to_define_args_quotes_strings_and_leaves_numbers():
    args = to_define_args({"TEXT_LINE_1": "John", "SIZE_TEXT_LINE_1": 33})
    assert "-D" in args
    assert 'TEXT_LINE_1="John"' in args
    assert "SIZE_TEXT_LINE_1=33" in args


def test_to_define_args_renders_booleans_lowercase():
    args = to_define_args({"HIDE_TAG": False})
    assert "HIDE_TAG=false" in args


def test_to_define_args_renders_lists_as_unquoted_vectors():
    # A list must become an OpenSCAD vector literal, not a quoted string, so the
    # template can index it (e.g. SVG_LOCATION[0]).
    args = to_define_args({"SVG_LOCATION": [10, -7]})
    assert "SVG_LOCATION=[10, -7]" in args


def test_to_define_args_escapes_double_quotes():
    args = to_define_args({"TEXT_LINE_1": 'a"b'})
    assert r'TEXT_LINE_1="a\"b"' in args


def test_blank_tag_vars_strips_all_info():
    base = build_scad_vars(
        sample_config(), icon_vars={"FILE": "/abs/x.svg", "ENABLE_SVG": True}
    )
    blank = blank_tag_vars(base)
    assert blank["HIDE_TAG"] is False  # tag body kept
    assert blank["HIDE_QR"] is True  # QR removed
    assert blank["ENABLE_SVG"] is False  # icon removed
    for i in range(1, 10):
        assert blank[f"ADD_TEXT_LINE_{i}"] is False  # all text removed


def test_blank_tag_vars_does_not_mutate_input():
    base = build_scad_vars(sample_config())
    blank_tag_vars(base)
    assert "HIDE_QR" not in base
    assert "ADD_TEXT_LINE_1" not in base


def test_info_tag_vars_keeps_info_and_drops_body():
    base = build_scad_vars(
        sample_config(), icon_vars={"FILE": "/abs/x.svg", "ENABLE_SVG": True}
    )
    info = info_tag_vars(base)
    assert info["HIDE_TAG"] is True  # tag body removed
    assert info["Facedown_Mode"] is False  # glyphs extruded at real thickness
    assert info["SVG_THICKNESS"] == 0.5  # icon pinned to text thickness
    assert info["ENABLE_SVG"] is True  # icon kept
    assert info["TEXT_LINE_1"] == "John"  # text kept


def test_info_tag_vars_does_not_mutate_input():
    base = build_scad_vars(sample_config())
    info_tag_vars(base)
    assert base["HIDE_TAG"] is False
    assert "SVG_THICKNESS" not in base
