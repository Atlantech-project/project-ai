"""The BAPLIE parser against the AI-023 corpus (AI-030 acceptance criteria)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from edi import ParseIssue, Stowage, parse_baplie
from tests.support.edi_corpus import CorpusCase, load_cases
from tests.unit.edi.builders import TDT, message
from tests.unit.edi.expected_records import EXPECTED

PARSER_CODES = {
    "UNREADABLE_FILE",
    "NOT_EDIFACT",
    "CORRUPTED_SYNTAX",
    "WRONG_MESSAGE_TYPE",
    "UNSUPPORTED_BAPLIE_VERSION",
    "UNKNOWN_SEGMENT",
}

SUPPORTED_TEXT = "Supported: SMDG 2.2.1 (D.95B), SMDG 3.1.1 (D.13B)"

# Corpus oracles that disagree with CT-12 v1.1 (Contracts line 793). By the user's
# decision of 2026-11-10 the parser follows CT-12; correcting these two oracles is
# AI-023's (AI Team), and QA owns CT-24. Remove an entry when its oracle is corrected.
CT12_OVERRIDES: dict[str, ParseIssue] = {
    "15-non-edifact-payload": ParseIssue(
        "ERROR", "NOT_EDIFACT", "UNH", f"Unsupported BAPLIE version: Thi. {SUPPORTED_TEXT}"
    ),
    "17-wrong-message-type": ParseIssue(
        "ERROR",
        "WRONG_MESSAGE_TYPE",
        "UNH",
        f"Unsupported BAPLIE version: COPRAR:D:95B:UN:SMDG22. {SUPPORTED_TEXT}",
    ),
}

CASES = load_cases()
PARSED = [c for c in CASES if c.oracle["expected_outcome"] == "PARSED"]
QUARANTINED = [c for c in CASES if c.oracle["expected_outcome"] == "QUARANTINED"]
REJECTED = [c for c in CASES if c.oracle["expected_outcome"] == "REJECTED"]


def _ids(cases: list[CorpusCase]) -> list[str]:
    return [c.name for c in cases]


def _oracle_issues(case: CorpusCase, *, parser_only: bool) -> tuple[ParseIssue, ...]:
    issues: list[dict[str, Any]] = case.oracle["issues"]
    return tuple(
        ParseIssue(i["severity"], i["code"], i.get("segment_ref"), i["message"])
        for i in issues
        if not parser_only or i["code"] in PARSER_CODES
    )


def test_every_case_covered() -> None:
    assert len(CASES) == 25
    assert len(PARSED) + len(QUARANTINED) + len(REJECTED) == len(CASES)
    assert sorted(_ids(PARSED)) == sorted(EXPECTED)


@pytest.mark.parametrize("case", PARSED, ids=_ids(PARSED))
def test_valid_files_parse_to_expected_records(case: CorpusCase) -> None:
    result = parse_baplie(case.edi_path.read_bytes())
    vessel, lines = EXPECTED[case.name]
    assert result.outcome == "READ"
    assert result.vessel == vessel
    assert result.lines == lines
    assert len(result.lines) == case.oracle["containers"]
    assert result.vessel is not None
    assert result.vessel.imo_number == case.oracle["vessel_imo"]
    assert result.issues == _oracle_issues(case, parser_only=True)


@pytest.mark.parametrize("case", REJECTED, ids=_ids(REJECTED))
def test_rejected_files(case: CorpusCase) -> None:
    result = parse_baplie(case.edi_path.read_bytes())
    assert result.outcome == "REJECTED"
    assert result.lines == ()
    assert result.vessel is None
    if case.name in CT12_OVERRIDES:
        oracle = _oracle_issues(case, parser_only=False)
        assert [(i.severity, i.code) for i in result.issues] == [
            (i.severity, i.code) for i in oracle
        ]
        assert result.issues == (CT12_OVERRIDES[case.name],)
    else:
        assert result.issues == _oracle_issues(case, parser_only=False)


def test_ct12_overrides_still_differ_from_their_oracles() -> None:
    # Fails once AI-023 corrects an oracle, so the override is removed rather than kept stale.
    for name, issue in CT12_OVERRIDES.items():
        case = next(c for c in CASES if c.name == name)
        assert _oracle_issues(case, parser_only=False) != (issue,)


@pytest.mark.parametrize("case", QUARANTINED, ids=_ids(QUARANTINED))
def test_quarantine_files_still_read(case: CorpusCase) -> None:
    result = parse_baplie(case.edi_path.read_bytes())
    assert result.outcome == "READ"
    assert len(result.lines) == case.oracle["containers"]
    assert result.issues == _oracle_issues(case, parser_only=True)


def test_large_file_smoke() -> None:
    body: list[str] = []
    for n in range(20_000):
        body += [
            f"LOC+147+{n % 100:03d}{n % 50:02d}82",
            "MEA+WT++KGM:24500",
            f"EQD+CN+MSCU{n:07d}+45G1+++5",
            "LOC+11+CNSHA:139:6",
            "LOC+12+EGDAM:139:6",
        ]
    result = parse_baplie(message(TDT, *body))
    assert result.outcome == "READ"
    assert len(result.lines) == 20_000
    assert result.issues == ()


@pytest.mark.parametrize(
    ("name", "attribute", "expected"),
    [
        ("08-malformed-weight", "weight_kg", -100),
        ("12-invalid-stowage-coordinate", "stowage", Stowage(999, 99, 99)),
        ("06-unknown-iso-size-type", "iso_size_type", "45X9"),
        ("07-unknown-imdg-class", "imdg_class", "99"),
        ("10-temperature-out-of-range", "reefer_set_temperature", Decimal("55")),
        ("09-malformed-unlocode", "port_of_discharge", "E!DAM"),
    ],
)
def test_content_problems_kept_as_written(name: str, attribute: str, expected: object) -> None:
    case = next(c for c in CASES if c.name == name)
    lines = parse_baplie(case.edi_path.read_bytes()).lines
    assert expected in [getattr(line, attribute) for line in lines]
    assert all(line.unconverted == {} for line in lines)


def test_imo_mismatch_file_keeps_its_own_imo() -> None:
    case = next(c for c in CASES if c.name == "04-imo-mismatch")
    vessel = parse_baplie(case.edi_path.read_bytes()).vessel
    assert vessel is not None
    assert vessel.imo_number == "9123456"
