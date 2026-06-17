"""Pure helpers for the icon catalog (selection sheet).

The catalog tiles the per-icon preview PNGs (rendered by generate-preview.py)
into one enumerated grid per tag colour, so a customer can pick an icon by
number. These functions cover the index/layout logic; the Pillow compositing
lives in generate-catalog.py so this module stays testable without an image
backend.
"""

import math

SVGREPO_SUFFIX = "-svgrepo-com"

# Customer-facing PT-BR labels for the catalog. Keyed by icon stem; any stem not
# listed falls back to friendly_name() so a newly added icon still shows a name.
ICON_LABELS_PTBR = {
    "anchor-svgrepo-com": "Âncora",
    "beach-svgrepo-com": "Praia",
    "coconut-tree-6-svgrepo-com": "Coqueiro",
    "cristo-redentor-svgrepo-com": "Cristo Redentor",
    "cruise-svgrepo-com": "Cruzeiro",
    "cruise-yacht-svgrepo-com": "Iate",
    "eiffel-tower-svgrepo-com": "Torre Eiffel",
    "game-controller-svgrepo-com": "Videogame",
    "holland-mill-svgrepo-com": "Moinho holandês",
    "info-circle-svgrepo-com": "Informação",
    "location-pin-svgrepo-com": "Localização",
    "london-eye-svgrepo-com": "Londres",
    "luggage-03-svgrepo-com": "Bagagem",
    "new-york-famous-building-svgrepo-com": "Prédio de Nova York",
    "new-york-svgrepo-com": "Nova York",
    "paris-svgrepo-com": "Paris",
    "scooter-svgrepo-com": "Patinete",
    "suitcase-travel-vacation-svgrepo-com": "Mala de viagem",
    "travel-svgrepo-com": "Viagem",
    "world": "Mundo",
}

# PT-BR colour names for the header. Keyed by the colour slug (from
# generate-preview.py's palette); unknown slugs fall back to the English name.
COLOR_LABELS_PTBR = {
    "yellow": "Amarelo",
    "steel-blue": "Azul aço",
    "turquoise-blue": "Azul turquesa",
    "gray": "Cinza",
    "orange": "Laranja",
    "brown": "Marrom",
    "black": "Preto",
    "bubblegum-pink": "Rosa chiclete",
    "light-pink": "Rosa claro",
    "lime-green": "Verde limão",
    "red": "Vermelho",
    "dark-violet": "Violeta escuro",
}

# Catalog header (PT-BR), formatted with the translated colour name.
CATALOG_TITLE_PTBR = "Escolha sua imagem de fundo — {color}"


def friendly_name(stem):
    """Return a human-facing label for an icon ``stem``.

    Drops the ``-svgrepo-com`` provenance suffix the bundled icons carry,
    turns hyphens into spaces, and title-cases each word: e.g.
    ``coconut-tree-6-svgrepo-com`` -> ``Coconut Tree 6``.
    """
    if stem.endswith(SVGREPO_SUFFIX):
        stem = stem[: -len(SVGREPO_SUFFIX)]
    return " ".join(word.capitalize() for word in stem.split("-") if word)


def icon_label(stem):
    """Return the customer-facing PT-BR label for an icon ``stem``.

    Falls back to ``friendly_name`` for any stem without a PT-BR entry, so a
    newly added icon still gets a (English) label instead of nothing.
    """
    return ICON_LABELS_PTBR.get(stem, friendly_name(stem))


def color_label(color_slug, fallback):
    """Return the PT-BR colour name for ``color_slug`` (``fallback`` if unknown)."""
    return COLOR_LABELS_PTBR.get(color_slug, fallback)


def preview_filename(icon_stem, color_slug):
    """Return the preview PNG name generate-preview.py writes for this pair."""
    return f"{icon_stem}-{color_slug}.png"


def numbered_icons(icon_stems):
    """Return ``(number, stem)`` pairs in a single global alphabetical order.

    Numbering is derived from the sorted stems alone, so icon #N is the same
    icon in every colour's catalog -- a customer's pick is colour-independent.
    """
    return list(enumerate(sorted(icon_stems), start=1))


def colors_with_previews(icon_stems, color_slugs, available_files):
    """Return the ``color_slugs`` that have at least one icon preview present.

    A colour counts only when some icon's ``preview_filename`` is in
    ``available_files``; palette order is preserved. Files that aren't an icon
    preview (e.g. the info side) never match a constructed name, so they're
    ignored automatically.
    """
    present = []
    for slug in color_slugs:
        if any(
            preview_filename(stem, slug) in available_files for stem in icon_stems
        ):
            present.append(slug)
    return present


def grid_rows(count, columns):
    """Return the number of rows needed to lay ``count`` cells in ``columns``."""
    if count <= 0:
        return 0
    return math.ceil(count / columns)
