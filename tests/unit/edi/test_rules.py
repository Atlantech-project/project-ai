"""BAPLIE content rules (AI-031) against the AI-023 corpus and rule by rule.

The reference data below is SYNTHETIC: the request vessel the corpus README states (IMO
9811000), and the size types and IMDG classes the corpus uses, minus the ones its cases mark
unknown (45X9, 99).
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Any

import pytest

import edi.rules.staged as staged_module
from edi import Oog, ParsedLine, ParsedVessel, ParseIssue, Stowage, parse_baplie
from edi.rules import (
    Finding,
    Reference,
    StagedPayloadError,
    checks,
    iso6346_check_digit,
    outcome,
    read_staged_payload,
    validate,
    validate_staged_payload,
)
from tests.support.edi_corpus import CorpusCase, load_cases
from tests.support.edi_corpus import iso6346_check_digit as corpus_digit

REFERENCE = Reference(
    vessel_imo="9811000",
    vessel_name="MSC ALEXANDRIA",
    size_types={"22G1": False, "45G1": False, "45R1": True},
    imdg_classes=frozenset({"3"}),
)
PARSER_CODES = {
    "UNREADABLE_FILE",
    "NOT_EDIFACT",
    "CORRUPTED_SYNTAX",
    "WRONG_MESSAGE_TYPE",
    "UNSUPPORTED_BAPLIE_VERSION",
    "UNKNOWN_SEGMENT",
}
# Case 12 expects bay/row/tier 999/99/99 to be out of bounds (its message says "99/99/99"), but
# no document gives upper stowage bounds; only the schema's lower bounds are enforced.
UNDEFINED_BOUNDS = {"12-invalid-stowage-coordinate"}

READ_CASES = [c for c in load_cases() if c.oracle["expected_outcome"] != "REJECTED"]


def _issues(findings: tuple[Finding, ...]) -> list[ParseIssue]:
    return [f.issue for f in findings]


def _oracle(case: CorpusCase) -> list[ParseIssue]:
    raw: list[dict[str, Any]] = case.oracle["issues"]
    return [
        ParseIssue(i["severity"], i["code"], i.get("segment_ref"), i["message"])
        for i in raw
        if i["code"] not in PARSER_CODES
    ]


@pytest.mark.parametrize("case", READ_CASES, ids=[c.name for c in READ_CASES])
def test_corpus_rule_issues_match_the_oracle(case: CorpusCase) -> None:
    if case.name in UNDEFINED_BOUNDS:
        pytest.skip("upper stowage bounds are not defined (integration request to QA / Leads)")
    parsed = parse_baplie(case.edi_path.read_bytes())
    findings = validate(parsed.vessel, parsed.lines, REFERENCE)

    assert _issues(findings) == _oracle(case)
    assert outcome(findings) == case.oracle["expected_outcome"]


# --- the correction path runs the same code ----------------------------------------------


def _payload(vessel: ParsedVessel | None, lines: tuple[ParsedLine, ...]) -> dict[str, Any]:
    """A CT-12 `staged_payload` from parsed records (test-only; AI-032 writes the real one)."""
    assert vessel is not None
    return {
        "format_version": "1.0",
        "vessel": {"imo_number": vessel.imo_number, "name": vessel.name, "call_sign": None},
        "lines": [
            {
                "line_no": line.line_no,
                "segment_ref": line.segment_ref,
                "container_number": line.container_number,
                "iso_size_type": line.iso_size_type,
                "full_empty": line.full_empty,
                "weight_kg": line.weight_kg,
                "imdg_class": line.imdg_class,
                "oog": {
                    "front_cm": line.oog.front_cm,
                    "back_cm": line.oog.back_cm,
                    "right_cm": line.oog.right_cm,
                    "left_cm": line.oog.left_cm,
                    "height_cm": line.oog.height_cm,
                },
                "reefer_set_temperature": (
                    None
                    if line.reefer_set_temperature is None
                    else str(line.reefer_set_temperature)
                ),
                "stowage": {
                    "bay": line.stowage.bay,
                    "row": line.stowage.row,
                    "tier": line.stowage.tier,
                },
                "port_of_load": line.port_of_load,
                "port_of_discharge": line.port_of_discharge,
                "issues": [],
            }
            for line in lines
        ],
    }


def test_correction_path_calls_the_same_validate(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    real = checks.validate

    def spy(*args: Any, **kwargs: Any) -> tuple[Finding, ...]:
        calls.append(1)
        return real(*args, **kwargs)

    monkeypatch.setattr(staged_module, "validate", spy)
    parsed = parse_baplie(READ_CASES[0].edi_path.read_bytes())
    validate_staged_payload(_payload(parsed.vessel, parsed.lines), REFERENCE)

    assert calls == [1]
    assert real is validate


@pytest.mark.parametrize("case", READ_CASES, ids=[c.name for c in READ_CASES])
def test_correction_path_gives_the_same_findings(case: CorpusCase) -> None:
    parsed = parse_baplie(case.edi_path.read_bytes())
    from_file = validate(parsed.vessel, parsed.lines, REFERENCE)
    from_payload = validate_staged_payload(_payload(parsed.vessel, parsed.lines), REFERENCE)

    # The payload carries no segment texts, so only the references may differ.
    def key(f: Finding) -> tuple[int | None, str, str, str]:
        return (f.line_no, f.issue.severity, f.issue.code, f.issue.message)

    assert [key(f) for f in from_payload] == [key(f) for f in from_file]


def test_corrected_payload_becomes_clean() -> None:
    case = next(c for c in READ_CASES if c.name == "06-unknown-iso-size-type")
    parsed = parse_baplie(case.edi_path.read_bytes())
    payload = _payload(parsed.vessel, parsed.lines)
    assert outcome(validate_staged_payload(payload, REFERENCE)) == "QUARANTINED"

    payload["lines"][0]["iso_size_type"] = "45G1"  # staff correct the size type
    assert validate_staged_payload(payload, REFERENCE) == ()


def test_wrongly_typed_payload_values_are_malformed() -> None:
    parsed = parse_baplie(READ_CASES[0].edi_path.read_bytes())
    payload = _payload(parsed.vessel, parsed.lines)
    payload["lines"][0]["weight_kg"] = "heavy"
    payload["lines"][0]["reefer_set_temperature"] = "cold"
    payload["lines"][0]["stowage"] = {"bay": "x", "row": 2, "tier": 82}

    codes = {f.issue.code for f in validate_staged_payload(payload, REFERENCE)}
    assert {"MALFORMED_WEIGHT", "MALFORMED_TEMPERATURE", "INVALID_STOWAGE_COORDINATE"} <= codes


@pytest.mark.parametrize(
    "payload",
    [{}, {"format_version": "2.0", "vessel": {}, "lines": []}, {"format_version": "1.0"}],
)
def test_payload_of_the_wrong_shape_is_refused(payload: dict[str, Any]) -> None:
    with pytest.raises(StagedPayloadError):
        read_staged_payload(payload)


# --- rule by rule: positive and negative -----------------------------------------------------

VESSEL = ParsedVessel("9811000", "MSC ALEXANDRIA", None, "TDT+20+X")


def line(**changes: Any) -> ParsedLine:
    base = ParsedLine(
        line_no=1,
        segment_ref="LOC+147+0010282",
        container_number="MSCU1234566",
        iso_size_type="22G1",
        full_empty="FULL",
        weight_kg=24500,
        imdg_class=None,
        oog=Oog(),
        reefer_set_temperature=None,
        stowage=Stowage(1, 2, 82),
        port_of_load="CNSHA",
        port_of_discharge="EGDAM",
        segment_refs={},
        unconverted={},
    )
    return replace(base, **changes)


def codes(
    *lines: ParsedLine, vessel: ParsedVessel = VESSEL, ref: Reference = REFERENCE
) -> list[str]:
    return [f.issue.code for f in validate(vessel, lines, ref)]


def test_clean_line_has_no_issue() -> None:
    assert codes(line()) == []


def test_imo_mismatch_and_missing_imo_are_errors() -> None:
    assert codes(line(), vessel=replace(VESSEL, imo_number="9123456")) == ["IMO_MISMATCH"]
    findings = validate(replace(VESSEL, imo_number=None), [line()], REFERENCE)
    assert findings[0].issue.code == "IMO_MISMATCH"
    assert "(missing)" in findings[0].issue.message
    assert outcome(findings) == "QUARANTINED"
    assert codes(line(), vessel=None) == ["IMO_MISMATCH"]  # type: ignore[arg-type]


def test_request_vessel_without_imo_is_a_caller_error() -> None:
    with pytest.raises(ValueError, match="no IMO"):
        validate(VESSEL, [line()], replace(REFERENCE, vessel_imo=None))


def test_vessel_name_difference_is_a_warning() -> None:
    assert codes(line(), vessel=replace(VESSEL, name="  msc   alexandria ")) == []
    findings = validate(replace(VESSEL, name="OTHER NAME"), [line()], REFERENCE)
    assert [f.issue.code for f in findings] == ["VESSEL_NAME_MISMATCH"]
    assert outcome(findings) == "PARSED"


def test_duplicate_container_reported_once() -> None:
    lines = [line(line_no=n) for n in (1, 2, 3)]
    assert codes(*lines) == ["DUPLICATE_CONTAINER_NUMBER"]
    assert codes(line(), line(line_no=2, container_number="mscu 1234566")) == [
        "DUPLICATE_CONTAINER_NUMBER"
    ]
    assert codes(line(), line(line_no=2, container_number="MSKU1234565")) == []


def test_container_number_format() -> None:
    assert codes(line(container_number=None))[0] == "MALFORMED_CONTAINER_NUMBER"
    assert codes(line(container_number="MSC1234566")) == ["MALFORMED_CONTAINER_NUMBER"]
    assert codes(line(container_number="mscu1234566")) == []  # normalised to uppercase


def test_check_digit() -> None:
    assert codes(line(container_number="MSCU1234567")) == ["CHECK_DIGIT_MISMATCH"]
    assert codes(line(container_number="MSKU1234565")) == []


@pytest.mark.parametrize("number", ["MSKU1234565", "MSCU1234566", "CMAU3456787", "MAEU4567896"])
def test_check_digit_agrees_with_the_corpus_helper(number: str) -> None:
    assert iso6346_check_digit(number) == corpus_digit(number)


def test_size_type() -> None:
    assert codes(line(iso_size_type="45X9")) == ["UNKNOWN_SIZE_TYPE"]
    assert codes(line(iso_size_type=None)) == ["UNKNOWN_SIZE_TYPE"]
    assert codes(line(iso_size_type="45G1")) == []


def test_stored_size_type_differs_is_a_warning() -> None:
    ref = replace(REFERENCE, stored_size_types={"MSCU1234566": "45G1"})
    assert codes(line(), ref=ref) == ["SIZE_TYPE_CHANGED"]
    same = replace(REFERENCE, stored_size_types={"MSCU1234566": "22G1"})
    assert codes(line(), ref=same) == []


def test_imdg_class() -> None:
    assert codes(line(imdg_class="99")) == ["UNKNOWN_IMDG_CLASS"]
    assert codes(line(imdg_class="3")) == []
    assert codes(line(imdg_class=None)) == []


def test_weight() -> None:
    assert codes(line(weight_kg=0)) == ["MALFORMED_WEIGHT"]
    assert codes(line(weight_kg=-1)) == ["MALFORMED_WEIGHT"]
    assert codes(line(weight_kg=None, unconverted={"weight_kg": "KGM:ABC"})) == ["MALFORMED_WEIGHT"]
    assert codes(line(weight_kg=None)) == ["MISSING_MANDATORY_SEGMENT"]
    assert codes(line(weight_kg=1)) == []


def test_unlocode() -> None:
    assert codes(line(port_of_load="E!DAM")) == ["MALFORMED_UNLOCODE"]
    assert codes(line(port_of_discharge="egdam")) == ["MALFORMED_UNLOCODE"]
    assert codes(line(port_of_load="EGDA1")) == ["MALFORMED_UNLOCODE"]  # digits 2 to 9 only
    assert codes(line(port_of_load="EGDA9")) == []


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("-40", []),
        ("40", []),
        ("-40.01", ["TEMPERATURE_OUT_OF_RANGE"]),
        ("40.5", ["TEMPERATURE_OUT_OF_RANGE"]),
    ],
)
def test_temperature_bounds_are_inclusive(value: str, expected: list[str]) -> None:
    assert codes(line(iso_size_type="45R1", reefer_set_temperature=Decimal(value))) == expected


def test_unconverted_temperature_is_malformed() -> None:
    bad = line(iso_size_type="45R1", unconverted={"reefer_set_temperature": "x:CEL"})
    assert codes(bad) == ["MALFORMED_TEMPERATURE"]


def test_reefer_needs_a_set_temperature() -> None:
    assert codes(line(iso_size_type="45R1")) == ["REEFER_MISSING_TEMPERATURE"]
    assert codes(line(iso_size_type="45R1", reefer_set_temperature=Decimal("-18"))) == []
    assert codes(line(iso_size_type="22G1")) == []  # not a reefer


def test_stowage_lower_bounds_from_the_schema() -> None:
    assert codes(line(stowage=Stowage(0, 2, 82))) == ["INVALID_STOWAGE_COORDINATE"]
    assert codes(line(stowage=Stowage(1, -1, 82))) == ["INVALID_STOWAGE_COORDINATE"]
    assert codes(line(stowage=Stowage(1, 2, 0))) == ["INVALID_STOWAGE_COORDINATE"]
    assert codes(line(stowage=Stowage(1, 0, 1))) == []  # row 00 = centre line
    assert codes(line(stowage=Stowage(None, None, None), unconverted={"stowage": "12AB"})) == [
        "INVALID_STOWAGE_COORDINATE"
    ]


def test_oog_overhangs_must_be_positive() -> None:
    assert codes(line(oog=Oog(front_cm=0))) == ["MALFORMED_OOG"]
    assert codes(line(unconverted={"oog.height_cm": "CMT:abc"})) == ["MALFORMED_OOG"]
    assert codes(line(oog=Oog(front_cm=20, height_cm=30))) == []


# The schema stores weight, overhangs and stowage in signed 32-bit `int` columns; a larger value
# cannot be written, so it is a quarantine finding, not a database error in AI-032.
INT_MAX = 2_147_483_647


def test_values_the_int_columns_cannot_store_are_errors() -> None:
    assert codes(line(weight_kg=INT_MAX)) == []
    assert codes(line(weight_kg=INT_MAX + 1)) == ["MALFORMED_WEIGHT"]
    assert codes(line(oog=Oog(front_cm=INT_MAX))) == []
    assert codes(line(oog=Oog(left_cm=INT_MAX + 1))) == ["MALFORMED_OOG"]
    assert codes(line(stowage=Stowage(INT_MAX, 0, 1))) == []
    assert codes(line(stowage=Stowage(1, INT_MAX + 1, 82))) == ["INVALID_STOWAGE_COORDINATE"]


def test_oversized_weight_from_a_file_is_quarantined() -> None:
    raw = READ_CASES[0].edi_path.read_bytes()
    assert b"MEA+WT++KGM:" in raw
    edited = raw.replace(b"MEA+WT++KGM:24500'", b"MEA+WT++KGM:3000000000'", 1)
    assert edited != raw
    parsed = parse_baplie(edited)
    findings = validate(parsed.vessel, parsed.lines, REFERENCE)

    assert [f.issue.code for f in findings] == ["MALFORMED_WEIGHT"]
    assert outcome(findings) == "QUARANTINED"


def test_oversized_corrected_values_are_quarantined() -> None:
    parsed = parse_baplie(READ_CASES[0].edi_path.read_bytes())
    payload = _payload(parsed.vessel, parsed.lines)
    payload["lines"][0]["weight_kg"] = INT_MAX + 1
    payload["lines"][0]["stowage"] = {"bay": 1, "row": 2, "tier": INT_MAX + 1}

    codes = {f.issue.code for f in validate_staged_payload(payload, REFERENCE)}
    assert codes == {"MALFORMED_WEIGHT", "INVALID_STOWAGE_COORDINATE"}


def test_full_empty_missing_or_unknown_is_a_warning() -> None:
    assert codes(line(full_empty=None)) == ["MISSING_FULL_EMPTY"]
    unknown = validate(VESSEL, [line(full_empty=None, unconverted={"full_empty": "7"})], REFERENCE)
    assert "indicator 7 not recognised" in unknown[0].issue.message
    assert outcome(unknown) == "PARSED"


def test_port_of_discharge_missing_is_a_warning() -> None:
    findings = validate(VESSEL, [line(port_of_discharge=None)], REFERENCE)
    assert [f.issue.code for f in findings] == ["MISSING_PORT_OF_DISCHARGE"]
    assert outcome(findings) == "PARSED"


def test_issue_refs_use_segment_text_when_known() -> None:
    bad = line(weight_kg=-5, segment_refs={"weight_kg": "MEA+WT++KGM:-5"})
    assert validate(VESSEL, [bad], REFERENCE)[0].issue.segment_ref == "MEA+WT++KGM:-5"
    assert validate(VESSEL, [line(weight_kg=-5)], REFERENCE)[0].issue.segment_ref == (
        "LOC+147+0010282"
    )
