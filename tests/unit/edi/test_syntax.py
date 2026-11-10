"""EDIFACT syntax layer (AI-030): service characters, segments, elements, components."""

from __future__ import annotations

import time

import pytest

from edi.syntax import ServiceChars, SyntaxProblem, tokenize


def test_default_separators() -> None:
    chars, segments = tokenize("UNB+UNOA:2+S+R'UNH+1+BAPLIE:D:95B:UN:SMDG22'")
    assert chars == ServiceChars.DEFAULT
    assert [s.tag for s in segments] == ["UNB", "UNH"]
    assert segments[1].elements == (("1",), ("BAPLIE", "D", "95B", "UN", "SMDG22"))
    assert segments[1].text == "UNH+1+BAPLIE:D:95B:UN:SMDG22"
    assert [s.index for s in segments] == [0, 1]


def test_una_overrides_separators() -> None:
    chars, segments = tokenize("UNA;*,! #UNB*X;Y#")
    assert chars == ServiceChars(";", "*", ",", "!", "#")
    assert segments[0].tag == "UNB"
    assert segments[0].elements == (("X", "Y"),)


def test_release_character() -> None:
    _, segments = tokenize("TDT+20+++++++1::11:O?'BRIEN ?+ SON'")
    tdt = segments[0]
    assert tdt.elements[7] == ("1", "", "11", "O'BRIEN + SON")
    assert tdt.text == "TDT+20+++++++1::11:O?'BRIEN ?+ SON"


def test_released_release_character_and_separator_in_component() -> None:
    _, segments = tokenize("FTX+AAA+++A??B?:C'")
    assert segments[0].elements[3] == ("A?B:C",)


def test_whitespace_between_segments() -> None:
    plain = tokenize("UNB+X'UNH+1'")[1]
    crlf = tokenize("UNB+X'\r\nUNH+1'\r\n")[1]
    bom = tokenize("﻿UNB+X'UNH+1'\n")[1]
    assert [(s.tag, s.text) for s in crlf] == [(s.tag, s.text) for s in plain]
    assert [(s.tag, s.text) for s in bom] == [(s.tag, s.text) for s in plain]


def test_una_after_bom() -> None:
    chars, segments = tokenize("﻿UNA:+,? 'UNB+X'")
    assert chars.decimal == ","
    assert segments[0].tag == "UNB"


def test_empty_elements_kept() -> None:
    _, segments = tokenize("EQD+CN+MSCU1234566+45G1+++5'")
    eqd = segments[0]
    assert eqd.elements[5] == ("5",)
    assert eqd.elements[2] == ("45G1",)
    assert eqd.elements[3] == ("",)
    assert eqd.elements[4] == ("",)
    assert eqd.elements[0] == ("CN",)


def test_unterminated_raises() -> None:
    with pytest.raises(SyntaxProblem) as caught:
        tokenize("UNB+X'UNH+1")
    assert caught.value.reason == "UNTERMINATED"


@pytest.mark.parametrize("text", ["", "   ", "\r\n"])
def test_no_segments_raises(text: str) -> None:
    with pytest.raises(SyntaxProblem) as caught:
        tokenize(text)
    assert caught.value.reason == "NO_SEGMENTS"


def test_long_element_is_linear() -> None:
    # Review finding: building components by string concatenation was quadratic.
    started = time.perf_counter()
    _, segments = tokenize("FTX+AAA+++" + "A" * 1_000_000 + "'")
    assert time.perf_counter() - started < 3.0
    assert len(segments[0].elements[3][0]) == 1_000_000
