"""Derive tag text lines 4 and 5 from a phone number.

Brazilian formatting: line 4 is the country code (``+CC``) and line 5 is the
area code in parentheses followed by the formatted subscriber number.
"""

import re


def derive_phone_lines(phone_number):
    """Return ``(line4, line5)`` for a Brazilian phone number.

    Expects ``+55DDNNNNNNNN`` or ``+55DDNNNNNNNNN`` (8- or 9-digit number).
    Any spaces or punctuation are ignored. Raises ``ValueError`` if there are
    not enough digits to split into country code, area code and number.
    """
    digits = re.sub(r"\D", "", phone_number)

    country_code = digits[:2]
    area_code = digits[2:4]
    number = digits[4:]

    if len(country_code) < 2 or len(area_code) < 2 or len(number) < 8:
        raise ValueError(f"Phone number has too few digits: {phone_number!r}")

    if len(number) >= 9:
        formatted_number = f"{number[:5]}-{number[5:9]}"
    else:
        formatted_number = f"{number[:4]}-{number[4:8]}"

    line4 = f"+{country_code}"
    line5 = f"({area_code}) {formatted_number}"
    return line4, line5
