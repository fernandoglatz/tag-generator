from taggen.catalog import (
    color_label,
    colors_with_previews,
    friendly_name,
    grid_rows,
    icon_label,
    numbered_icons,
    preview_filename,
)


def test_friendly_name_strips_svgrepo_suffix_and_titlecases():
    assert friendly_name("travel-svgrepo-com") == "Travel"
    assert friendly_name("coconut-tree-6-svgrepo-com") == "Coconut Tree 6"
    assert (
        friendly_name("new-york-famous-building-svgrepo-com")
        == "New York Famous Building"
    )


def test_friendly_name_without_suffix():
    assert friendly_name("world") == "World"


def test_preview_filename_joins_stem_and_slug():
    assert preview_filename("travel-svgrepo-com", "yellow") == (
        "travel-svgrepo-com-yellow.png"
    )
    assert preview_filename("world", "steel-blue") == "world-steel-blue.png"


def test_numbered_icons_sorts_alphabetically_and_numbers_from_one():
    result = numbered_icons(["world", "anchor-svgrepo-com", "travel-svgrepo-com"])
    assert result == [
        (1, "anchor-svgrepo-com"),
        (2, "travel-svgrepo-com"),
        (3, "world"),
    ]


def test_colors_with_previews_keeps_palette_order_and_only_present_colors():
    icons = ["travel-svgrepo-com", "world"]
    slugs = ["yellow", "steel-blue", "red"]
    files = {
        "travel-svgrepo-com-yellow.png",
        "world-yellow.png",
        "world-red.png",
        "john-doe-info-yellow.png",  # not an icon -> ignored
    }
    assert colors_with_previews(icons, slugs, files) == ["yellow", "red"]


def test_colors_with_previews_excludes_color_with_no_icon_previews():
    icons = ["travel-svgrepo-com"]
    slugs = ["yellow", "red"]
    files = {"travel-svgrepo-com-yellow.png", "john-doe-info-red.png"}
    assert colors_with_previews(icons, slugs, files) == ["yellow"]


def test_icon_label_translates_known_stems_to_ptbr():
    assert icon_label("travel-svgrepo-com") == "Viagem"
    assert icon_label("anchor-svgrepo-com") == "Âncora"
    assert icon_label("eiffel-tower-svgrepo-com") == "Torre Eiffel"
    assert icon_label("holland-mill-svgrepo-com") == "Moinho holandês"
    assert icon_label("world") == "Mundo"


def test_icon_label_falls_back_to_friendly_name_for_unknown_stem():
    assert icon_label("custom-thing") == "Custom Thing"


def test_color_label_translates_known_slugs_to_ptbr():
    assert color_label("yellow", "Yellow") == "Amarelo"
    assert color_label("steel-blue", "Steel blue") == "Azul aço"


def test_color_label_falls_back_to_given_name_for_unknown_slug():
    assert color_label("chartreuse", "Chartreuse") == "Chartreuse"


def test_grid_rows_rounds_up():
    assert grid_rows(0, 4) == 0
    assert grid_rows(1, 4) == 1
    assert grid_rows(4, 4) == 1
    assert grid_rows(5, 4) == 2
    assert grid_rows(17, 4) == 5
