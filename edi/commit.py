"""What a BAPLIE parse writes (AI-032), decided without touching the database.

CT-12 v1.1 outcomes:

- `REJECTED` (not a usable BAPLIE): the parser's one ERROR issue; `parse_status = FAILED`.
- `QUARANTINED` (readable, at least one ERROR): the issues and `staged_payload`; no data rows.
- `PARSED`: new containers, one manifest entry per line, WARNING issues, NULL vessel fields
  filled; `parse_status = PARSED`.

The worker never writes `baplie_files.status`: the Backend activates the file and replaces the
earlier ACTIVE one on `PARSED` (CT-12 step 5, DEC-08). The caller writes everything returned
here in one transaction (`edi.job`).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Final, Literal

from edi.records import ParsedLine, ParsedVessel, ParseIssue, ParseResult
from edi.rules import Finding, Reference, outcome, validate
from edi.rules.checks import normalise_container_number

Outcome = Literal["PARSED", "QUARANTINED", "REJECTED"]
SEGMENT_REF_MAX: Final = 60  # `baplie_parse_issues.segment_ref`
MESSAGE_MAX: Final = 500  # `baplie_parse_issues.message`
STAGED_FORMAT_VERSION: Final = "1.0"
_PARSE_STATUS: Final[Mapping[Outcome, str]] = {
    "PARSED": "PARSED",
    "QUARANTINED": "QUARANTINED",
    "REJECTED": "FAILED",
}


@dataclass(frozen=True)
class SizeType:
    id: int
    code: str
    is_reefer: bool


@dataclass(frozen=True)
class FileContext:
    """What the database says about the file and its vessel (read by `edi.job`)."""

    baplie_file_id: int
    vessel_id: int
    vessel_imo: str | None
    vessel_name: str | None
    vessel_call_sign: str | None
    port_code: str | None
    size_types: Mapping[str, SizeType]  # by code
    imdg_classes: frozenset[str]
    stored_size_types: Mapping[str, str]  # container number -> code, for numbers that exist


@dataclass(frozen=True)
class WritePlan:
    outcome: Outcome
    parse_status: str
    issues: tuple[dict[str, object], ...]  # `baplie_parse_issues` rows
    staged_payload: dict[str, Any] | None
    new_containers: tuple[dict[str, object], ...]  # `containers` rows (insert unknown only)
    manifest: tuple[dict[str, object], ...]  # rows without `container_id`, by `container_number`
    vessel_fills: dict[str, object]
    result_detail: dict[str, object]
    container_count: int
    issue_counts: dict[str, int] = field(default_factory=dict)


def reference(context: FileContext) -> Reference:
    return Reference(
        vessel_imo=context.vessel_imo,
        vessel_name=context.vessel_name,
        size_types={code: st.is_reefer for code, st in context.size_types.items()},
        imdg_classes=context.imdg_classes,
        stored_size_types=context.stored_size_types,
    )


def plan_from_parse(parsed: ParseResult, context: FileContext) -> WritePlan:
    """The write plan for a parsed file (`source = FILE`)."""
    if parsed.outcome == "REJECTED":
        issues = [Finding(None, issue) for issue in parsed.issues]
        return _plan("REJECTED", issues, None, (), context)
    parser_issues = [Finding(None, issue) for issue in parsed.issues]
    return plan_from_records(parsed.vessel, parsed.lines, context, parser_issues)


def plan_from_records(
    vessel: ParsedVessel | None,
    lines: Sequence[ParsedLine],
    context: FileContext,
    extra: Sequence[Finding] = (),
) -> WritePlan:
    """The write plan for readable records (a file, or a corrected `staged_payload`)."""
    findings = [*extra, *validate(vessel, lines, reference(context))]
    result: Outcome = "QUARANTINED" if outcome(findings) == "QUARANTINED" else "PARSED"
    return _plan(result, findings, vessel, lines, context)


def _plan(
    result: Outcome,
    findings: Sequence[Finding],
    vessel: ParsedVessel | None,
    lines: Sequence[ParsedLine],
    context: FileContext,
) -> WritePlan:
    issues = tuple(_issue_row(context.baplie_file_id, f.issue) for f in findings)
    counts = {
        "ERROR": sum(1 for f in findings if f.issue.severity == "ERROR"),
        "WARNING": sum(1 for f in findings if f.issue.severity == "WARNING"),
    }
    staged = _staged_payload(vessel, lines, findings) if result == "QUARANTINED" else None
    containers: tuple[dict[str, object], ...] = ()
    manifest: tuple[dict[str, object], ...] = ()
    fills: dict[str, object] = {}
    if result == "PARSED":
        containers = tuple(_container_row(line, context) for line in lines)
        manifest = tuple(_manifest_row(line, context.baplie_file_id) for line in lines)
        if vessel is not None and vessel.call_sign and context.vessel_call_sign is None:
            fills["call_sign"] = vessel.call_sign
    discharged = sum(
        1 for line in lines if context.port_code and line.port_of_discharge == context.port_code
    )
    detail: dict[str, object] = {
        "container_count": len(lines) if result == "PARSED" else 0,
        "discharged_here_count": discharged if result == "PARSED" else 0,
        "issue_counts": counts,
        "vessel_fields_filled": sorted(fills),
        "failure_reason": None,
    }
    return WritePlan(
        outcome=result,
        parse_status=_PARSE_STATUS[result],
        issues=issues,
        staged_payload=staged,
        new_containers=containers,
        manifest=manifest,
        vessel_fills=fills,
        result_detail=detail,
        container_count=len(lines) if result == "PARSED" else 0,
        issue_counts=counts,
    )


def _issue_row(file_id: int, issue: ParseIssue) -> dict[str, object]:
    ref = issue.segment_ref
    return {
        "baplie_file_id": file_id,
        "severity": issue.severity,
        "segment_ref": ref[:SEGMENT_REF_MAX] if ref is not None else None,
        "message": f"{issue.code}: {issue.message}"[:MESSAGE_MAX],
    }


def _container_row(line: ParsedLine, context: FileContext) -> dict[str, object]:
    # PARSED means no ERROR: the number is well formed and the size type is known.
    number = normalise_container_number(line.container_number or "")
    return {
        "container_number": number,
        "size_type_id": context.size_types[line.iso_size_type or ""].id,
    }


def _manifest_row(line: ParsedLine, file_id: int) -> dict[str, object]:
    return {
        "container_number": normalise_container_number(line.container_number or ""),
        "baplie_file_id": file_id,
        "full_empty": line.full_empty,
        "weight_kg": line.weight_kg,
        "imdg_class": line.imdg_class,
        "oog_over_front_cm": line.oog.front_cm,
        "oog_over_back_cm": line.oog.back_cm,
        "oog_over_right_cm": line.oog.right_cm,
        "oog_over_left_cm": line.oog.left_cm,
        "oog_over_height_cm": line.oog.height_cm,
        "reefer_set_temperature": line.reefer_set_temperature,
        "stowage_bay": line.stowage.bay,
        "stowage_row": line.stowage.row,
        "stowage_tier": line.stowage.tier,
        "port_of_load": line.port_of_load,
        "port_of_discharge": line.port_of_discharge,
    }


def _staged_payload(
    vessel: ParsedVessel | None, lines: Sequence[ParsedLine], findings: Sequence[Finding]
) -> dict[str, Any]:
    """CT-12 `staged_payload` (format 1.0). File-level issues (for example `IMO_MISMATCH`) are in
    `baplie_parse_issues` only: the CT-12 vessel object has no issues list."""
    per_line: dict[int, list[dict[str, str]]] = {}
    for finding in findings:
        if finding.line_no is not None:
            per_line.setdefault(finding.line_no, []).append(_issue_json(finding.issue))
    return {
        "format_version": STAGED_FORMAT_VERSION,
        "vessel": {
            "imo_number": vessel.imo_number if vessel else None,
            "name": vessel.name if vessel else None,
            "call_sign": vessel.call_sign if vessel else None,
        },
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
                "reefer_set_temperature": _number(line.reefer_set_temperature),
                "stowage": {
                    "bay": line.stowage.bay,
                    "row": line.stowage.row,
                    "tier": line.stowage.tier,
                },
                "port_of_load": line.port_of_load,
                "port_of_discharge": line.port_of_discharge,
                "issues": per_line.get(line.line_no, []),
            }
            for line in lines
        ],
    }


def _issue_json(issue: ParseIssue) -> dict[str, str]:
    return {"severity": issue.severity, "code": issue.code, "message": issue.message}


def _number(value: Decimal | None) -> float | None:
    """A JSON number (`decimal(5,2)` values, so the float round-trips through `str`)."""
    return None if value is None else float(value)
