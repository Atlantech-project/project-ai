"""Envelope checks of the BAPLIE parser (AI-030): reading-the-file problems only."""

from __future__ import annotations

import pytest

from edi.parser import parse_baplie
from edi.records import ParseIssue, ParseResult
from tests.unit.edi.builders import CONTAINER_A, TDT, UNA, UNB, message

SUPPORTED_TEXT = "Supported: SMDG 2.2.1 (D.95B), SMDG 3.1.1 (D.13B)"


def _rejected_with(result: ParseResult, issue: ParseIssue) -> None:
    assert result.outcome == "REJECTED"
    assert result.lines == ()
    assert result.vessel is None
    assert result.issues == (issue,)


@pytest.mark.parametrize("data", [b"", b"  \n", b"\xef\xbb\xbf"])
def test_empty(data: bytes) -> None:
    _rejected_with(
        parse_baplie(data),
        ParseIssue("ERROR", "UNREADABLE_FILE", None, "File is empty or cannot be read"),
    )


@pytest.mark.parametrize(
    ("data", "found"),
    [
        # CT-12 v1.1: <found> = the first 3 characters of the file as read (user, 2026-11-10).
        (b"This is not an EDIFACT file.\nPlain text report.\n", "Thi"),
        (b"\xef\xbb\xbfXML<root/>", "XML"),
        (b"  PK\x03\x04", "  P"),
        (b"ab", "ab"),
        # No readable character in the first 3: "none".
        (b"\x00\x01\x02\x03rest", "none"),
        (b"\t\x00\nrest", "none"),
    ],
)
def test_not_edifact(data: bytes, found: str) -> None:
    _rejected_with(
        parse_baplie(data),
        ParseIssue(
            "ERROR",
            "NOT_EDIFACT",
            "UNH",
            f"Unsupported BAPLIE version: {found}. {SUPPORTED_TEXT}",
        ),
    )


def test_truncated() -> None:
    text = UNA + UNB + "UNH+1+BAPLIE:D:95B:UN:SMDG22'" + TDT + "'" + "LOC+12+EGDAM:139:6"
    _rejected_with(
        parse_baplie(text.encode()),
        ParseIssue(
            "ERROR",
            "CORRUPTED_SYNTAX",
            None,
            "File is truncated: last segment is unterminated and UNT/UNZ are missing",
        ),
    )


def test_unterminated_after_unz() -> None:
    text = message(TDT).decode() + "GARBAGE"
    _rejected_with(
        parse_baplie(text.encode()),
        ParseIssue(
            "ERROR", "CORRUPTED_SYNTAX", None, "File is corrupted: last segment is unterminated"
        ),
    )


def test_missing_unz() -> None:
    text = message(TDT).decode().removesuffix("UNZ+1+1'")
    _rejected_with(
        parse_baplie(text.encode()),
        ParseIssue("ERROR", "CORRUPTED_SYNTAX", None, "File is truncated: UNZ is missing"),
    )


def test_missing_unt() -> None:
    text = UNA + UNB + "UNH+1+BAPLIE:D:95B:UN:SMDG22'" + TDT + "'UNZ+1+1'"
    _rejected_with(
        parse_baplie(text.encode()),
        ParseIssue("ERROR", "CORRUPTED_SYNTAX", None, "File is truncated: UNT is missing"),
    )


def test_unt_before_unh() -> None:
    text = UNA + UNB + "UNT+2+1'UNH+1+BAPLIE:D:95B:UN:SMDG22'" + TDT + "'UNZ+1+1'"
    _rejected_with(
        parse_baplie(text.encode()),
        ParseIssue("ERROR", "CORRUPTED_SYNTAX", None, "File is truncated: UNT is missing"),
    )


def test_missing_unh() -> None:
    text = UNA + UNB + TDT + "'UNT+2+1'UNZ+1+1'"
    _rejected_with(
        parse_baplie(text.encode()),
        ParseIssue("ERROR", "CORRUPTED_SYNTAX", None, "UNH segment is missing"),
    )


def test_unt_count_mismatch() -> None:
    text = message(TDT, *CONTAINER_A).decode().replace("UNT+8+1", "UNT+9+1")
    _rejected_with(
        parse_baplie(text.encode()),
        ParseIssue(
            "ERROR", "CORRUPTED_SYNTAX", "UNT", "UNT segment count 9 does not match 8 segments"
        ),
    )


def test_two_messages() -> None:
    first = message(TDT).decode()
    second_message = "UNH+2+BAPLIE:D:95B:UN:SMDG22'" + TDT + "'UNT+3+2'"
    text = first.replace("UNZ+1+1'", second_message + "UNZ+2+1'")
    _rejected_with(
        parse_baplie(text.encode()),
        ParseIssue(
            "ERROR",
            "CORRUPTED_SYNTAX",
            "UNH",
            "File holds 2 messages; one BAPLIE message per file is expected",
        ),
    )


def test_wrong_message_type() -> None:
    _rejected_with(
        parse_baplie(message(unh="COPRAR:D:95B:UN:SMDG22")),
        ParseIssue(
            "ERROR",
            "WRONG_MESSAGE_TYPE",
            "UNH",
            f"Unsupported BAPLIE version: COPRAR:D:95B:UN:SMDG22. {SUPPORTED_TEXT}",
        ),
    )


@pytest.mark.parametrize(
    "identifier",
    ["BAPLIE:1:5:UN:SMDG15", "BAPLIE:D:17A:UN:SMDG20", "BAPLIE:D:95B:XX:SMDG22", "BAPLIE"],
)
def test_unsupported_versions(identifier: str) -> None:
    _rejected_with(
        parse_baplie(message(TDT, unh=identifier)),
        ParseIssue(
            "ERROR",
            "UNSUPPORTED_BAPLIE_VERSION",
            "UNH",
            f"Unsupported BAPLIE version: {identifier}. {SUPPORTED_TEXT}",
        ),
    )


@pytest.mark.parametrize(
    ("identifier", "version"),
    [
        ("BAPLIE:D:95B:UN:SMDG22", "D95B"),
        ("BAPLIE:D:13B:UN:SMDG31", "D13B"),
        ("BAPLIE:D:95B:UN:SMDG21", "D95B"),
    ],
)
def test_supported_versions(identifier: str, version: str) -> None:
    result = parse_baplie(message(TDT, unh=identifier))
    assert result.outcome == "READ"
    assert result.version == version
    assert result.message_identifier == identifier
    assert result.issues == ()


def test_latin1_fallback() -> None:
    data = message("TDT+20+001A+1++MSC:172:20+++9811000::11:CAF\xc9").decode("utf-8")
    result = parse_baplie(data.encode("latin-1"))
    assert result.outcome == "READ"
    assert result.issues == ()
