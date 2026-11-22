"""BAPLIE write plan and writes (AI-032). Reference data is SYNTHETIC (corpus README values)."""

from dataclasses import replace
from typing import Any

import pytest

from common.runtime.errors import JobError
from edi import parse_baplie
from edi.commit import FileContext, SizeType, plan_from_parse, plan_from_records
from edi.job import write
from edi.rules import read_staged_payload, validate_staged_payload
from tests.support.edi_corpus import CorpusCase, load_cases
from tests.unit.edi.test_rules import REFERENCE

CONTEXT = FileContext(
    baplie_file_id=21,
    vessel_id=5,
    vessel_imo="9811000",
    vessel_name="MSC ALEXANDRIA",
    vessel_call_sign=None,
    port_code="EGDAM",
    size_types={
        "22G1": SizeType(1, "22G1", False),
        "45G1": SizeType(2, "45G1", False),
        "45R1": SizeType(3, "45R1", True),
    },
    imdg_classes=frozenset({"3"}),
    stored_size_types={},
)
CASES = {c.name: c for c in load_cases()}
UNDEFINED_BOUNDS = {"12-invalid-stowage-coordinate"}  # see AI-031: no upper stowage bounds


def plan(name: str, context: FileContext = CONTEXT) -> Any:
    return plan_from_parse(parse_baplie(CASES[name].edi_path.read_bytes()), context)


@pytest.mark.parametrize("case", list(CASES.values()), ids=list(CASES))
def test_every_corpus_case_gets_its_outcome(case: CorpusCase) -> None:
    if case.name in UNDEFINED_BOUNDS:
        pytest.skip("upper stowage bounds are not defined (INT-Q1)")
    result = plan(case.name)
    assert result.outcome == case.oracle["expected_outcome"]
    expected_status = {"PARSED": "PARSED", "QUARANTINED": "QUARANTINED", "REJECTED": "FAILED"}
    assert result.parse_status == expected_status[result.outcome]


def test_parsed_file_writes_containers_manifest_and_warnings() -> None:
    result = plan("03-valid-with-warnings")

    assert result.outcome == "PARSED"
    assert len(result.manifest) == len(result.new_containers) == result.container_count == 1
    assert result.new_containers[0] == {"container_number": "MSCU1234567", "size_type_id": 2}
    entry = result.manifest[0]
    assert entry["baplie_file_id"] == 21 and entry["port_of_discharge"] == "EGDAM"
    assert [i["severity"] for i in result.issues] == ["WARNING"]
    assert str(result.issues[0]["message"]).startswith("CHECK_DIGIT_MISMATCH: ")
    assert result.staged_payload is None
    assert result.result_detail["discharged_here_count"] == 1
    assert result.result_detail["issue_counts"] == {"ERROR": 0, "WARNING": 1}


def test_quarantined_file_writes_no_data_and_a_staged_payload() -> None:
    result = plan("04-imo-mismatch")

    assert result.outcome == "QUARANTINED"
    assert result.new_containers == () and result.manifest == () and result.vessel_fills == {}
    assert result.container_count == 0
    payload = result.staged_payload
    assert payload is not None and payload["format_version"] == "1.0"
    assert set(payload["vessel"]) == {"imo_number", "name", "call_sign"}  # CT-12 shape
    vessel, lines = read_staged_payload(payload)
    assert vessel.imo_number == "9123456" and len(lines) == 1


def test_staged_payload_round_trips_through_the_correction_path() -> None:
    result = plan("06-unknown-iso-size-type")
    payload = result.staged_payload
    assert payload is not None
    assert payload["lines"][0]["issues"][0]["code"] == "UNKNOWN_SIZE_TYPE"
    assert [f.issue.code for f in validate_staged_payload(payload, REFERENCE)] == [
        "UNKNOWN_SIZE_TYPE"
    ]
    payload["lines"][0]["iso_size_type"] = "45G1"
    vessel, lines = read_staged_payload(payload)
    corrected = plan_from_records(vessel, lines, CONTEXT)
    assert corrected.outcome == "PARSED"
    assert corrected.new_containers[0]["size_type_id"] == 2


def test_reefer_temperature_is_a_json_number_in_the_payload() -> None:
    result = plan("10-temperature-out-of-range")
    payload = result.staged_payload
    assert payload is not None
    assert payload["lines"][0]["reefer_set_temperature"] == 55.0


def test_rejected_file_keeps_the_parser_issue_only() -> None:
    result = plan("16-unsupported-version")

    assert (result.outcome, result.parse_status) == ("REJECTED", "FAILED")
    assert len(result.issues) == 1 and result.issues[0]["segment_ref"] == "UNH"
    assert result.staged_payload is None and result.manifest == ()


def test_parser_warnings_are_kept_on_a_parsed_file() -> None:
    result = plan("23-unknown-segment")
    assert result.outcome == "PARSED"
    assert any(str(i["message"]).startswith("UNKNOWN_SEGMENT") for i in result.issues)


def test_call_sign_is_filled_only_when_the_vessel_has_none() -> None:
    parsed = parse_baplie(CASES["01-valid-221"].edi_path.read_bytes())
    assert parsed.vessel is not None
    vessel = replace(parsed.vessel, call_sign="3FAB7")
    empty = plan_from_records(vessel, parsed.lines, CONTEXT)
    kept = plan_from_records(vessel, parsed.lines, replace(CONTEXT, vessel_call_sign="OLD1"))

    assert empty.vessel_fills == {"call_sign": "3FAB7"}
    assert empty.result_detail["vessel_fields_filled"] == ["call_sign"]
    assert kept.vessel_fills == {}


def test_oversized_call_sign_is_quarantined_not_filled() -> None:
    parsed = parse_baplie(CASES["01-valid-221"].edi_path.read_bytes())
    assert parsed.vessel is not None
    vessel = replace(parsed.vessel, call_sign="A" * 11)
    plan = plan_from_records(vessel, parsed.lines, CONTEXT)

    assert plan.outcome == "QUARANTINED"
    assert plan.vessel_fills == {}
    assert plan.staged_payload is not None
    assert plan.staged_payload["vessel"]["call_sign"] == "A" * 11  # kept for staff to fix


def test_segment_ref_and_message_fit_their_columns() -> None:
    from edi.commit import _issue_row
    from edi.records import ParseIssue

    row = _issue_row(1, ParseIssue("ERROR", "X", "R" * 80, "m" * 600))
    assert len(str(row["segment_ref"])) == 60 and len(str(row["message"])) == 500


# --- writes ------------------------------------------------------------------------------------


class FakeRepo:
    def __init__(self, update_ok: bool = True) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.update_ok = update_ok

    def insert_new_containers(self, rows: list[dict[str, object]]) -> dict[str, int]:
        self.calls.append(("containers", rows))
        return {str(r["container_number"]): 100 + n for n, r in enumerate(rows)}

    def insert_many(self, table: str, rows: list[dict[str, object]]) -> None:
        self.calls.append((table, rows))

    def fill_vessel_nulls(self, vessel_id: int, values: dict[str, object]) -> bool:
        self.calls.append(("vessels", (vessel_id, values)))
        return True

    def update_baplie_file(self, file_id: int, values: dict[str, object]) -> bool:
        self.calls.append(("baplie_files", (file_id, values)))
        return self.update_ok


def test_parsed_writes_data_then_issues_then_parse_status_never_file_status() -> None:
    repo = FakeRepo()
    write(repo, 21, {"vessel_id": 5}, plan("03-valid-with-warnings"))  # type: ignore[arg-type]

    tables = [name for name, _ in repo.calls]
    assert tables == [
        "containers",
        "container_manifest_entries",
        "baplie_parse_issues",
        "baplie_files",
    ]
    manifest = repo.calls[1][1][0]
    assert manifest["container_id"] == 100 and "container_number" not in manifest
    assert repo.calls[-1][1] == (21, {"parse_status": "PARSED"})  # never `status` (DEC-08)


def test_quarantine_writes_issues_and_the_payload_only() -> None:
    repo = FakeRepo()
    write(repo, 21, {"vessel_id": 5}, plan("04-imo-mismatch"))  # type: ignore[arg-type]

    assert [name for name, _ in repo.calls] == ["baplie_parse_issues", "baplie_files"]
    values = repo.calls[-1][1][1]
    assert values["parse_status"] == "QUARANTINED" and "staged_payload" in values


def test_a_missing_file_row_fails_the_job() -> None:
    with pytest.raises(JobError):
        write(FakeRepo(update_ok=False), 21, {"vessel_id": 5}, plan("01-valid-221"))  # type: ignore[arg-type]
