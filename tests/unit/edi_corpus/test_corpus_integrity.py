"""Integrity checks for the AI-023 BAPLIE test corpus (``tests/edi_corpus``)."""

from __future__ import annotations

import re

import pytest

from tests.support.edi_corpus import (
    CORPUS_ROOT,
    CorpusCase,
    container_numbers,
    iso6346_check_digit,
    load_cases,
    split_segments,
)

CASES = load_cases()
IDS = [case.name for case in CASES]

CT24_NAMES = [
    "01-valid-221",
    "02-valid-311",
    "03-valid-with-warnings",
    "04-imo-mismatch",
    "05-duplicate-container",
    "06-unknown-iso-size-type",
    "07-unknown-imdg-class",
    "08-malformed-weight",
    "09-malformed-unlocode",
    "10-temperature-out-of-range",
    "11-reefer-missing-temp",
    "12-invalid-stowage-coordinate",
    "13-missing-mandatory-segment",
    "14-multiple-errors-composite",
    "15-non-edifact-payload",
    "16-unsupported-version",
    "17-wrong-message-type",
    "18-corrupted-syntax",
]
ADDED_NAMES = [
    "19-valid-dangerous-goods",
    "20-valid-reefer",
    "21-valid-oog",
    "22-missing-full-empty",
    "23-unknown-segment",
    "24-unreadable-file",
    "25-unsupported-version-d17a",
]
SUPPORTED_UNH = {"BAPLIE:D:95B:UN:SMDG22", "BAPLIE:D:13B:UN:SMDG31"}
ORACLE_KEYS = {
    "file",
    "expected_outcome",
    "expected_parse_status",
    "vessel_imo",
    "containers",
    "issues",
    "is_synthetic",
}
STATUS_FOR_OUTCOME = {"PARSED": "PARSED", "QUARANTINED": "QUARANTINED", "REJECTED": "FAILED"}


def _codes(case: CorpusCase) -> set[str]:
    return {issue["code"] for issue in case.oracle["issues"]}


def test_iso6346_known_values() -> None:
    assert iso6346_check_digit("MSKU1234565") == 5
    assert iso6346_check_digit("MSCU1234567") == 6
    assert iso6346_check_digit("CMAU3456787") == 7
    assert iso6346_check_digit("MSCU1234566") == 6


def test_split_segments() -> None:
    assert split_segments("UNA:+.? '\nUNH+1+X'\nUNT+2+1'\n") == ["UNH+1+X", "UNT+2+1"]
    assert split_segments("FTX+AAA+++IT?'S OK'") == ["FTX+AAA+++IT?'S OK"]
    with pytest.raises(ValueError):
        split_segments("UNH+1+X'\nUNT+2")


def test_corpus_is_not_empty() -> None:
    assert CASES, "no cases found in tests/edi_corpus"


def test_every_edi_has_an_oracle_and_the_reverse() -> None:
    edi = {p.name.removesuffix(".edi") for p in CORPUS_ROOT.glob("*.edi")}
    oracle = {p.name.removesuffix(".expected.json") for p in CORPUS_ROOT.glob("*.expected.json")}
    assert edi == oracle


def test_ct24_and_added_cases_are_present() -> None:
    assert IDS == sorted(CT24_NAMES + ADDED_NAMES)


def test_no_size_class_files() -> None:
    # Scope exception (DEC-17, CT-24 README section 3, thresholds register TR-08).
    for name in IDS:
        assert not re.search(r"small|medium|large", name)


def test_index_lists_exactly_the_cases() -> None:
    index = (CORPUS_ROOT / "INDEX.md").read_text(encoding="utf-8")
    listed = set(re.findall(r"`(\d\d-[a-z0-9-]+)`", index))
    assert listed == set(IDS)


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_oracle_schema(case: CorpusCase) -> None:
    oracle = case.oracle
    assert set(oracle) == ORACLE_KEYS
    assert oracle["file"] == f"{case.name}.edi"
    assert STATUS_FOR_OUTCOME[oracle["expected_outcome"]] == oracle["expected_parse_status"]
    assert oracle["is_synthetic"] is True
    assert isinstance(oracle["containers"], int)
    for issue in oracle["issues"]:
        assert issue["severity"] in {"ERROR", "WARNING"}
        assert issue["code"] and issue["message"]
        assert set(issue) <= {"severity", "code", "segment_ref", "message"}
    if oracle["vessel_imo"] is not None:
        assert re.fullmatch(r"\d{7}", oracle["vessel_imo"])
    else:
        assert oracle["expected_outcome"] == "REJECTED"


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_severity_matches_outcome(case: CorpusCase) -> None:
    severities = {issue["severity"] for issue in case.oracle["issues"]}
    outcome = case.oracle["expected_outcome"]
    if outcome == "PARSED":
        assert "ERROR" not in severities
    else:
        assert "ERROR" in severities
    if outcome == "REJECTED":
        assert case.oracle["containers"] == 0


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_readable_files_are_well_formed(case: CorpusCase) -> None:
    if case.oracle["expected_outcome"] == "REJECTED":
        pytest.skip("rejected cases are checked separately")
    segments = split_segments(case.edi_path.read_text(encoding="utf-8"))
    unh = next(i for i, s in enumerate(segments) if s.startswith("UNH+"))
    unt = next(i for i, s in enumerate(segments) if s.startswith("UNT+"))
    assert segments[unt] == f"UNT+{unt - unh + 1}+1"
    assert segments[-1].startswith("UNZ+")
    assert len(container_numbers(segments)) == case.oracle["containers"]
    for segment in segments:
        if segment.startswith(("LOC+11+", "LOC+12+")):
            assert re.fullmatch(r"LOC\+1[12]\+[^:]+:139:6", segment), segment
    tdt = next(s for s in segments if s.startswith("TDT+"))
    assert f"+++{case.oracle['vessel_imo']}::11:" in tdt


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_readable_files_use_a_supported_version(case: CorpusCase) -> None:
    if case.oracle["expected_outcome"] == "REJECTED":
        pytest.skip("rejected cases are checked separately")
    segments = split_segments(case.edi_path.read_text(encoding="utf-8"))
    unh = next(s for s in segments if s.startswith("UNH+"))
    assert unh.split("+")[2] in SUPPORTED_UNH


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_check_digits_match_oracle(case: CorpusCase) -> None:
    if case.oracle["expected_outcome"] == "REJECTED":
        pytest.skip("rejected cases are checked separately")
    segments = split_segments(case.edi_path.read_text(encoding="utf-8"))
    wrong = {
        f"EQD+CN+{n}" for n in container_numbers(segments) if iso6346_check_digit(n) != int(n[-1])
    }
    flagged = {
        issue["segment_ref"]
        for issue in case.oracle["issues"]
        if issue["code"] == "CHECK_DIGIT_MISMATCH"
    }
    assert wrong == flagged
    if flagged:
        assert all(
            issue["severity"] == "WARNING"
            for issue in case.oracle["issues"]
            if issue["code"] == "CHECK_DIGIT_MISMATCH"
        )


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_rejected_cases_are_not_usable_baplie(case: CorpusCase) -> None:
    if case.oracle["expected_outcome"] != "REJECTED":
        pytest.skip("only rejected cases")
    text = case.edi_path.read_text(encoding="utf-8")
    codes = _codes(case)
    assert len(codes) == 1
    (code,) = codes
    if code == "CORRUPTED_SYNTAX":
        with pytest.raises(ValueError):
            split_segments(text)
    elif code in {"NOT_EDIFACT", "UNREADABLE_FILE"}:
        assert not text.startswith(("UNA", "UNB"))
    elif code in {"UNSUPPORTED_BAPLIE_VERSION", "WRONG_MESSAGE_TYPE"}:
        segments = split_segments(text)
        unh = next(s for s in segments if s.startswith("UNH+"))
        assert unh.split("+")[2] not in SUPPORTED_UNH
        if code == "WRONG_MESSAGE_TYPE":
            assert unh.split("+")[2].startswith("COPRAR")
    else:
        pytest.fail(f"unexpected code for a rejected case: {code}")


def test_unknown_segment_case_still_counts_valid_containers() -> None:
    case = next(c for c in CASES if c.name == "23-unknown-segment")
    assert case.oracle["expected_outcome"] == "PARSED"
    assert case.oracle["containers"] == 2
    assert _codes(case) == {"UNKNOWN_SEGMENT"}
    assert case.oracle["issues"][0]["severity"] == "WARNING"


def _ref_in_file(ref: str, segments: list[str]) -> bool:
    return any(segment == ref or segment.startswith(ref) for segment in segments)


def test_ref_in_file_helper() -> None:
    segments = ["UNH+1+X", "EQD+CN+MSCU1234566+45G1+++5"]
    assert _ref_in_file("UNH", segments)
    assert _ref_in_file("EQD+CN+MSCU1234566", segments)
    assert not _ref_in_file("EQD+CN+MSCU9999999", segments)


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_segment_refs_point_into_the_file(case: CorpusCase) -> None:
    refs = [i["segment_ref"] for i in case.oracle["issues"] if "segment_ref" in i]
    if not refs:
        pytest.skip("no segment_ref in this case")
    segments = split_segments(case.edi_path.read_text(encoding="utf-8"))
    for ref in refs:
        assert _ref_in_file(ref, segments), f"{ref!r} is not a segment of {case.name}.edi"


def test_d17a_case_is_rejected_as_unsupported_version() -> None:
    # D.17A is not supported: CT-12 v1.1 accepts only D.95B and D.13B.
    case = next(c for c in CASES if c.name == "25-unsupported-version-d17a")
    segments = split_segments(case.edi_path.read_text(encoding="utf-8"))
    unh = next(s for s in segments if s.startswith("UNH+"))
    assert unh == "UNH+1+BAPLIE:D:17A:UN:SMDG20"
    assert case.oracle["expected_outcome"] == "REJECTED"
    assert case.oracle["expected_parse_status"] == "FAILED"
    assert case.oracle["containers"] == 0
    (issue,) = case.oracle["issues"]
    assert issue["severity"] == "ERROR"
    assert issue["code"] == "UNSUPPORTED_BAPLIE_VERSION"
    assert issue["segment_ref"] == "UNH"
    assert issue["message"] == (
        "Unsupported BAPLIE version: BAPLIE:D:17A:UN:SMDG20. "
        "Supported: SMDG 2.2.1 (D.95B), SMDG 3.1.1 (D.13B)"
    )
