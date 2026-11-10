"""Message walk, container grouping and field mapping of the BAPLIE parser (AI-030)."""

from __future__ import annotations

import time
from decimal import Decimal

import pytest

from edi.parser import parse_baplie
from edi.records import Oog, ParsedLine, ParsedVessel, ParseIssue, Stowage
from tests.unit.edi.builders import CONTAINER_A, TDT, message, message_text

CONTAINER_B = (
    "LOC+147+0010482",
    "MEA+WT++KGM:21800",
    "EQD+CN+CMAU3456787+22G1+++5",
    "LOC+11+CNSHA:139:6",
    "LOC+12+EGDAM:139:6",
)


def _line(*segments: str) -> ParsedLine:
    result = parse_baplie(message(TDT, *segments))
    assert result.outcome == "READ"
    assert len(result.lines) == 1
    return result.lines[0]


def test_vessel_from_tdt() -> None:
    result = parse_baplie(message(TDT))
    assert result.vessel == ParsedVessel("9811000", "MSC ALEXANDRIA", None, TDT)


def test_no_tdt_gives_empty_vessel() -> None:
    result = parse_baplie(message(*CONTAINER_A))
    assert result.vessel == ParsedVessel(None, None, None, None)


def test_full_line() -> None:
    line = _line(
        "LOC+147+0010282",
        "MEA+WT++KGM:24500",
        "EQD+CN+MSCU1234566+45G1+++5",
        "DGS+IMD+3+1993",
        "TMP+2+-18:CEL",
        "DIM+5+CMT:20",
        "DIM+13+CMT:30",
        "LOC+11+CNSHA:139:6",
        "LOC+12+EGDAM:139:6",
    )
    assert line.line_no == 1
    assert line.stowage == Stowage(1, 2, 82)
    assert line.weight_kg == 24500
    assert line.container_number == "MSCU1234566"
    assert line.iso_size_type == "45G1"
    assert line.full_empty == "FULL"
    assert line.imdg_class == "3"
    assert line.reefer_set_temperature == Decimal("-18")
    assert line.oog == Oog(20, None, None, None, 30)
    assert line.port_of_load == "CNSHA"
    assert line.port_of_discharge == "EGDAM"
    assert line.segment_ref == "LOC+147+0010282"
    assert line.unconverted == {}
    assert line.segment_refs == {
        "stowage": "LOC+147+0010282",
        "weight_kg": "MEA+WT++KGM:24500",
        "container_number": "EQD+CN+MSCU1234566+45G1+++5",
        "iso_size_type": "EQD+CN+MSCU1234566+45G1+++5",
        "full_empty": "EQD+CN+MSCU1234566+45G1+++5",
        "imdg_class": "DGS+IMD+3+1993",
        "reefer_set_temperature": "TMP+2+-18:CEL",
        "oog.front_cm": "DIM+5+CMT:20",
        "oog.height_cm": "DIM+13+CMT:30",
        "port_of_load": "LOC+11+CNSHA:139:6",
        "port_of_discharge": "LOC+12+EGDAM:139:6",
    }


def test_vgm_weight_qualifier() -> None:
    line = _line("LOC+147+0010282", "MEA+AAE+VGM+KGM:21000", "EQD+CN+MSCU1234566+45G1+++5")
    assert line.weight_kg == 21000


def test_empty_code() -> None:
    assert _line("EQD+CN+MSCU1234566+45G1+++4").full_empty == "EMPTY"


def test_missing_full_empty_is_none_without_issue() -> None:
    result = parse_baplie(message(TDT, "LOC+147+0010282", "EQD+CN+MSCU1234566+45G1"))
    assert result.lines[0].full_empty is None
    assert result.lines[0].unconverted == {}
    assert result.issues == ()


@pytest.mark.parametrize(
    ("segment", "attribute", "expected"),
    [
        ("MEA+WT++KGM:-100", "weight_kg", -100),
        ("TMP+2+55:CEL", "reefer_set_temperature", Decimal("55")),
        ("LOC+147+9999999", "stowage", Stowage(999, 99, 99)),
        ("LOC+12+E!DAM:139:6", "port_of_discharge", "E!DAM"),
        ("EQD+CN+mscu 1234566+45G1+++5", "container_number", "mscu 1234566"),
        ("EQD+CN+MSCU1234566+45X9+++5", "iso_size_type", "45X9"),
        ("DGS+IMD+99+1993", "imdg_class", "99"),
    ],
)
def test_values_kept_as_written(segment: str, attribute: str, expected: object) -> None:
    base = {"LOC+147": "LOC+147+0010282", "EQD": "EQD+CN+MSCU1234566+45G1+++5"}
    if segment.startswith("LOC+147"):
        base["LOC+147"] = segment
        segments = [base["LOC+147"], base["EQD"]]
    elif segment.startswith("EQD"):
        segments = [base["LOC+147"], segment]
    else:
        segments = [base["LOC+147"], base["EQD"], segment]
    result = parse_baplie(message(TDT, *segments))
    assert getattr(result.lines[0], attribute) == expected
    assert result.lines[0].unconverted == {}
    assert result.issues == ()


@pytest.mark.parametrize(
    ("segment", "attribute", "empty_value", "unconverted"),
    [
        ("MEA+WT++KGM:ABC", "weight_kg", None, {"weight_kg": "KGM:ABC"}),
        ("MEA+WT++LBR:24500", "weight_kg", None, {"weight_kg": "LBR:24500"}),
        ("MEA+WT++KGM:24500.5", "weight_kg", None, {"weight_kg": "KGM:24500.5"}),
        ("TMP+2+x:CEL", "reefer_set_temperature", None, {"reefer_set_temperature": "x:CEL"}),
        ("TMP+2+20:FAH", "reefer_set_temperature", None, {"reefer_set_temperature": "20:FAH"}),
        ("DIM+5+CMT:abc", "oog", Oog(), {"oog.front_cm": "CMT:abc"}),
        ("DIM+5+INH:20", "oog", Oog(), {"oog.front_cm": "INH:20"}),
    ],
)
def test_unconverted_raw_text(
    segment: str, attribute: str, empty_value: object, unconverted: dict[str, str]
) -> None:
    line = _line("LOC+147+0010282", "EQD+CN+MSCU1234566+45G1+++5", segment)
    assert getattr(line, attribute) == empty_value
    assert line.unconverted == unconverted


def test_unconverted_stowage() -> None:
    line = _line("LOC+147+12AB", "EQD+CN+MSCU1234566+45G1+++5")
    assert line.stowage == Stowage(None, None, None)
    assert line.unconverted == {"stowage": "12AB"}
    assert line.segment_ref == "LOC+147+12AB"


def test_unconverted_full_empty() -> None:
    line = _line("LOC+147+0010282", "EQD+CN+MSCU1234566+45G1+++7")
    assert line.full_empty is None
    assert line.unconverted == {"full_empty": "7"}


def test_repeated_field_keeps_first() -> None:
    line = _line(
        "LOC+147+0010282",
        "MEA+WT++KGM:24500",
        "MEA+WT++KGM:30000",
        "EQD+CN+MSCU1234566+45G1+++5",
    )
    assert line.weight_kg == 24500
    assert line.unconverted == {"weight_kg#2": "MEA+WT++KGM:30000"}


def test_decimal_mark_from_una() -> None:
    text = message_text(
        TDT, "LOC+147+0010282", "EQD+CN+MAEU4567896+45R1+++5", "TMP+2+-18,5:CEL", una="UNA:+,? '"
    )
    line = parse_baplie(text.encode()).lines[0]
    assert line.reefer_set_temperature == Decimal("-18.5")


def test_eqd_first_grouping() -> None:
    def eqd_first(container: tuple[str, ...]) -> tuple[str, ...]:
        loc147, mea, eqd, load, discharge = container
        return (eqd, mea, loc147, load, discharge)

    stowage_first = parse_baplie(message(TDT, *CONTAINER_A, *CONTAINER_B))
    reordered = parse_baplie(message(TDT, *eqd_first(CONTAINER_A), *eqd_first(CONTAINER_B)))
    assert len(stowage_first.lines) == 2
    assert reordered.lines == stowage_first.lines


def test_line_without_stowage() -> None:
    line = _line("EQD+CN+MSCU1234566+45G1+++5", "MEA+WT++KGM:24500")
    assert line.segment_ref == "EQD+CN+MSCU1234566+45G1+++5"
    assert line.stowage == Stowage(None, None, None)
    assert line.weight_kg == 24500


def test_lines_numbered_in_file_order() -> None:
    result = parse_baplie(message(TDT, *CONTAINER_A, *CONTAINER_B))
    assert [(line.line_no, line.container_number) for line in result.lines] == [
        (1, "MSCU1234566"),
        (2, "CMAU3456787"),
    ]


def test_unknown_segment_warns_and_continues() -> None:
    result = parse_baplie(message(TDT, *CONTAINER_A, "XYZ+1+UNKNOWN", *CONTAINER_B))
    assert result.outcome == "READ"
    assert len(result.lines) == 2
    assert result.issues == (
        ParseIssue(
            "WARNING",
            "UNKNOWN_SEGMENT",
            "XYZ+1+UNKNOWN",
            "Unknown segment XYZ ignored; valid containers still loaded",
        ),
    )


def test_known_unmapped_segments_silent() -> None:
    result = parse_baplie(message(TDT, "FTX+AAA+++TEXT", "RFF+BM:1", *CONTAINER_A, "LOC+9+X"))
    assert result.issues == ()
    assert len(result.lines) == 1


def test_deterministic() -> None:
    data = message(TDT, *CONTAINER_A, "XYZ+1", *CONTAINER_B)
    assert parse_baplie(data) == parse_baplie(data)


def test_many_repeats_in_one_line_are_linear() -> None:
    # Review finding: finding the next free "<field>#n" key was quadratic.
    repeats = ["MEA+WT++KGM:1"] * 20_000
    data = message(TDT, "LOC+147+0010282", *repeats, "EQD+CN+MSCU1234566+45G1+++5")
    started = time.perf_counter()
    line = parse_baplie(data).lines[0]
    assert time.perf_counter() - started < 3.0
    assert line.weight_kg == 1
    assert len(line.unconverted) == 19_999
    assert line.unconverted["weight_kg#20000"] == "MEA+WT++KGM:1"
