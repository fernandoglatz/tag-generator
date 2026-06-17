import pytest

from taggen.phone import derive_phone_lines


def test_brazilian_nine_digit_number():
    line4, line5 = derive_phone_lines("+5511999999999")
    assert line4 == "+55"
    assert line5 == "(11) 99999-9999"


def test_brazilian_eight_digit_number():
    line4, line5 = derive_phone_lines("+551133334444")
    assert line4 == "+55"
    assert line5 == "(11) 3333-4444"


def test_ignores_spaces_and_punctuation():
    line4, line5 = derive_phone_lines("+55 (11) 99999-9999")
    assert line4 == "+55"
    assert line5 == "(11) 99999-9999"


def test_works_without_leading_plus():
    line4, line5 = derive_phone_lines("5511999999999")
    assert line4 == "+55"
    assert line5 == "(11) 99999-9999"


def test_too_short_raises():
    with pytest.raises(ValueError):
        derive_phone_lines("+5511")
