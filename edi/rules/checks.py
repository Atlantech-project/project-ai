"""BAPLIE content rules (AI-031): one rule set for the parse job and for staff corrections.

CT-12 v1.1 lists the issues: ERROR moves the file to QUARANTINED, WARNING leaves it PARSED.
Codes, severities, segment references and message texts follow the AI-023 corpus oracles
(CT-24) where a case exists; the other codes are Proposed in the AI-031 task decision.

The rules are pure: the reference data the Backend's tables hold is passed in (`Reference`).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Final, Literal

from edi.records import ParsedLine, ParsedVessel, ParseIssue, Severity

# Codes with a corpus case (CT-24; `MISSING_FULL_EMPTY` is Proposed there by AI-023).
IMO_MISMATCH: Final = "IMO_MISMATCH"
DUPLICATE_CONTAINER_NUMBER: Final = "DUPLICATE_CONTAINER_NUMBER"
UNKNOWN_SIZE_TYPE: Final = "UNKNOWN_SIZE_TYPE"
UNKNOWN_IMDG_CLASS: Final = "UNKNOWN_IMDG_CLASS"
MALFORMED_WEIGHT: Final = "MALFORMED_WEIGHT"
MALFORMED_UNLOCODE: Final = "MALFORMED_UNLOCODE"
TEMPERATURE_OUT_OF_RANGE: Final = "TEMPERATURE_OUT_OF_RANGE"
REEFER_MISSING_TEMPERATURE: Final = "REEFER_MISSING_TEMPERATURE"
INVALID_STOWAGE_COORDINATE: Final = "INVALID_STOWAGE_COORDINATE"
MISSING_MANDATORY_SEGMENT: Final = "MISSING_MANDATORY_SEGMENT"
CHECK_DIGIT_MISMATCH: Final = "CHECK_DIGIT_MISMATCH"
MISSING_FULL_EMPTY: Final = "MISSING_FULL_EMPTY"
# Proposed (AI-031 task decision): CT-12 names the rule, no corpus case names the code.
MALFORMED_CONTAINER_NUMBER: Final = "MALFORMED_CONTAINER_NUMBER"
MALFORMED_TEMPERATURE: Final = "MALFORMED_TEMPERATURE"
MALFORMED_OOG: Final = "MALFORMED_OOG"
MISSING_PORT_OF_DISCHARGE: Final = "MISSING_PORT_OF_DISCHARGE"
VESSEL_NAME_MISMATCH: Final = "VESSEL_NAME_MISMATCH"
SIZE_TYPE_CHANGED: Final = "SIZE_TYPE_CHANGED"
# Approved 2026-11-22 (AI-031 task decision item 10, R12): a call sign `vessels.call_sign` cannot
# store, or one that is not text. Listing in CT-24 is pending with the QA Team (INT-Q2).
MALFORMED_CALL_SIGN: Final = "MALFORMED_CALL_SIGN"

# `chk_cme_pol` / `chk_cme_pod` (schema): five characters, country then location.
_UNLOCODE: Final = re.compile(r"[A-Z]{2}[A-Z2-9]{3}")
# ISO 6346: owner code (3 letters), category letter, serial (6 digits), check digit.
_CONTAINER_NUMBER: Final = re.compile(r"[A-Z]{4}[0-9]{7}")
# `chk_cme_reefer` (schema): -40 to 40 °C, inclusive.
TEMPERATURE_MIN: Final = Decimal(-40)
TEMPERATURE_MAX: Final = Decimal(40)

_OOG_SIDES: Final = ("front", "back", "right", "left", "height")
# `container_manifest_entries` stores weight, overhangs and stowage in signed `int` columns; a
# larger value cannot be written, so it is an ERROR here rather than a database error in AI-032.
INT_COLUMN_MAX: Final = 2_147_483_647
# `vessels.call_sign` is `varchar(10)` (utf8mb4 counts characters, like `len`). Only a staff
# correction can supply a call sign: the parser reads the IMO and name from TDT only.
CALL_SIGN_MAX_LENGTH: Final = 10

Outcome = Literal["PARSED", "QUARANTINED"]


@dataclass(frozen=True)
class Reference:
    """Reference data read by the caller (AI-032) for one file.

    - `vessel_imo`, `vessel_name`: `vessels` row of the berthing request.
    - `size_types`: `container_size_types.code` to `is_reefer`.
    - `imdg_classes`: `imdg_classes.code` values.
    - `stored_size_types`: container number (uppercase, no spaces) to the `code` of the
      size type already stored in `containers`, for numbers that exist.
    """

    vessel_imo: str | None
    vessel_name: str | None
    size_types: Mapping[str, bool]
    imdg_classes: frozenset[str]
    stored_size_types: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Finding:
    """One issue, with the line it belongs to (`None` for a file-level issue)."""

    line_no: int | None
    issue: ParseIssue


def normalise_container_number(number: str) -> str:
    """CT-12 upsert key: uppercase, no spaces."""
    return "".join(number.split()).upper()


def _letter_values() -> dict[str, int]:
    """ISO 6346 letter values: A = 10 upwards, skipping multiples of 11 (B = 12, L = 23 ...)."""
    values: dict[str, int] = {}
    value = 10
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if value % 11 == 0:
            value += 1
        values[letter] = value
        value += 1
    return values


_LETTER_VALUES: Final = _letter_values()


def iso6346_check_digit(number: str) -> int:
    """The ISO 6346 check digit of the first ten characters of a well-formed number."""
    total = 0
    for position, char in enumerate(number[:10]):
        total += (_LETTER_VALUES[char] if char.isalpha() else int(char)) * 2**position
    return total % 11 % 10


def validate(
    vessel: ParsedVessel | None, lines: Iterable[ParsedLine], reference: Reference
) -> tuple[Finding, ...]:
    """Every CT-12 content rule, in file order: vessel first, then each line."""
    findings = list(_vessel_findings(vessel, reference))
    seen: set[str] = set()
    reported: set[str] = set()
    for line in lines:
        findings.extend(Finding(line.line_no, i) for i in _line_issues(line, reference))
        number = line.container_number
        if number is None:
            continue
        key = normalise_container_number(number)
        if key in seen and key not in reported:
            reported.add(key)
            message = f"Container {number} appears more than once in the file"
            issue = ParseIssue("ERROR", DUPLICATE_CONTAINER_NUMBER, _eqd_ref(line), message)
            findings.append(Finding(line.line_no, issue))
        seen.add(key)
    return tuple(findings)


def outcome(findings: Iterable[Finding]) -> Outcome:
    """QUARANTINED when any ERROR applies (CT-12); otherwise PARSED."""
    return "QUARANTINED" if any(f.issue.severity == "ERROR" for f in findings) else "PARSED"


def _vessel_findings(vessel: ParsedVessel | None, reference: Reference) -> Iterable[Finding]:
    if reference.vessel_imo is None:
        raise ValueError("the berthing request's vessel has no IMO number")
    file_imo = vessel.imo_number if vessel is not None else None
    ref = vessel.segment_ref if vessel is not None else None
    if file_imo != reference.vessel_imo:
        shown = file_imo if file_imo is not None else "missing"
        message = (
            f"Vessel IMO in BAPLIE file ({shown}) does not match berthing request vessel IMO "
            f"({reference.vessel_imo})"
        )
        yield Finding(None, ParseIssue("ERROR", IMO_MISMATCH, ref, message))
    file_name = vessel.name if vessel is not None else None
    if (
        file_name is not None
        and reference.vessel_name is not None
        and _same_name(file_name) != _same_name(reference.vessel_name)
    ):
        message = (
            f"Vessel name in BAPLIE file ({file_name}) differs from the registered name "
            f"({reference.vessel_name})"
        )
        yield Finding(None, ParseIssue("WARNING", VESSEL_NAME_MISMATCH, ref, message))
    raw_call_sign = vessel.unconverted.get("call_sign") if vessel is not None else None
    if raw_call_sign is not None:
        message = f"Call sign {raw_call_sign} is not text"
        yield Finding(None, ParseIssue("ERROR", MALFORMED_CALL_SIGN, ref, message))
    call_sign = vessel.call_sign if vessel is not None else None
    if call_sign is not None and len(call_sign) > CALL_SIGN_MAX_LENGTH:
        message = (
            f"Call sign is {len(call_sign)} characters; the stored maximum is "
            f"{CALL_SIGN_MAX_LENGTH}"
        )
        yield Finding(None, ParseIssue("ERROR", MALFORMED_CALL_SIGN, ref, message))


def _same_name(name: str) -> str:
    return " ".join(name.split()).casefold()


def _eqd_ref(line: ParsedLine) -> str:
    """The corpus oracles' short reference for a container: ``EQD+CN+<number>``."""
    if line.container_number is None:
        return line.segment_ref
    return f"EQD+CN+{line.container_number}"


def _ref(line: ParsedLine, field_name: str) -> str:
    return line.segment_refs.get(field_name, line.segment_ref)


def _issue(severity: Severity, code: str, ref: str, message: str) -> ParseIssue:
    return ParseIssue(severity, code, ref, message)


def _line_issues(line: ParsedLine, reference: Reference) -> list[ParseIssue]:
    issues: list[ParseIssue] = []
    issues.extend(_container_number(line))
    issues.extend(_size_type(line, reference))
    issues.extend(_imdg(line, reference))
    issues.extend(_weight(line))
    issues.extend(_ports(line))
    issues.extend(_temperature(line, reference))
    issues.extend(_stowage(line))
    issues.extend(_oog(line))
    issues.extend(_check_digit(line))
    issues.extend(_full_empty(line))
    issues.extend(_port_of_discharge(line))
    return issues


def _container_number(line: ParsedLine) -> list[ParseIssue]:
    number = line.container_number
    if number is None:
        message = f"Container number missing on line {line.line_no}"
        return [_issue("ERROR", MALFORMED_CONTAINER_NUMBER, line.segment_ref, message)]
    if not _CONTAINER_NUMBER.fullmatch(normalise_container_number(number)):
        message = f"Container number {number} is not four letters and seven digits (ISO 6346)"
        return [_issue("ERROR", MALFORMED_CONTAINER_NUMBER, _eqd_ref(line), message)]
    return []


def _size_type(line: ParsedLine, reference: Reference) -> list[ParseIssue]:
    code = line.iso_size_type
    if code is None:
        return [_issue("ERROR", UNKNOWN_SIZE_TYPE, _eqd_ref(line), "Size type missing")]
    if code not in reference.size_types:
        return [_issue("ERROR", UNKNOWN_SIZE_TYPE, _eqd_ref(line), f"Size type {code} not found")]
    number = line.container_number
    stored = (
        reference.stored_size_types.get(normalise_container_number(number))
        if number is not None
        else None
    )
    if stored is not None and stored != code:
        message = (
            f"Container {number} is stored with size type {stored}; the file says {code}. "
            "The stored value is kept"
        )
        return [_issue("WARNING", SIZE_TYPE_CHANGED, _eqd_ref(line), message)]
    return []


def _imdg(line: ParsedLine, reference: Reference) -> list[ParseIssue]:
    code = line.imdg_class
    if "imdg_class" in line.unconverted:
        code = line.unconverted["imdg_class"]
    if code is None or code in reference.imdg_classes:
        return []
    return [
        _issue(
            "ERROR", UNKNOWN_IMDG_CLASS, _ref(line, "imdg_class"), f"IMDG class {code} not found"
        )
    ]


def _weight(line: ParsedLine) -> list[ParseIssue]:
    ref = _ref(line, "weight_kg")
    if "weight_kg" in line.unconverted:
        raw = line.unconverted["weight_kg"]
        return [_issue("ERROR", MALFORMED_WEIGHT, ref, f"Weight {raw} is not a positive number")]
    if line.weight_kg is None:
        message = f"Mandatory segment MEA (weight) missing for container {line.container_number}"
        return [_issue("ERROR", MISSING_MANDATORY_SEGMENT, _eqd_ref(line), message)]
    if line.weight_kg <= 0:  # `chk_cme_weight`
        message = f"Weight {line.weight_kg} is not a positive number"
        return [_issue("ERROR", MALFORMED_WEIGHT, ref, message)]
    if line.weight_kg > INT_COLUMN_MAX:
        message = f"Weight {line.weight_kg} is larger than the stored maximum {INT_COLUMN_MAX}"
        return [_issue("ERROR", MALFORMED_WEIGHT, ref, message)]
    return []


def _ports(line: ParsedLine) -> list[ParseIssue]:
    issues = []
    for name in ("port_of_load", "port_of_discharge"):
        code = getattr(line, name)
        if code is not None and not _UNLOCODE.fullmatch(code):
            message = f"{code} is not a valid UN/LOCODE"
            issues.append(_issue("ERROR", MALFORMED_UNLOCODE, _ref(line, name), message))
    return issues


def _temperature(line: ParsedLine, reference: Reference) -> list[ParseIssue]:
    ref = _ref(line, "reefer_set_temperature")
    if "reefer_set_temperature" in line.unconverted:
        raw = line.unconverted["reefer_set_temperature"]
        message = f"Set temperature {raw} is not a number in degrees Celsius"
        return [_issue("ERROR", MALFORMED_TEMPERATURE, ref, message)]
    value = line.reefer_set_temperature
    if value is not None and not TEMPERATURE_MIN <= value <= TEMPERATURE_MAX:
        message = f"Set temperature {value} C is outside -40 to 40"
        return [_issue("ERROR", TEMPERATURE_OUT_OF_RANGE, ref, message)]
    is_reefer = reference.size_types.get(line.iso_size_type or "", False)
    if is_reefer and value is None:
        message = f"Reefer container {line.container_number} has no set temperature"
        return [_issue("ERROR", REEFER_MISSING_TEMPERATURE, _eqd_ref(line), message)]
    return []


def _stowage(line: ParsedLine) -> list[ParseIssue]:
    ref = _ref(line, "stowage")
    if "stowage" in line.unconverted:
        raw = line.unconverted["stowage"]
        message = f"Stowage position {raw} is not a valid bay/row/tier (BBBRRTT)"
        return [_issue("ERROR", INVALID_STOWAGE_COORDINATE, ref, message)]
    s = line.stowage
    # `chk_cme_stowage` (schema): bay > 0, row >= 0, tier > 0, and the `int` columns' maximum.
    # No document gives operational upper bounds (corpus case 12).
    bad = (
        (s.bay is not None and s.bay <= 0)
        or (s.row is not None and s.row < 0)
        or (s.tier is not None and s.tier <= 0)
        or any(v is not None and v > INT_COLUMN_MAX for v in (s.bay, s.row, s.tier))
    )
    if bad:
        message = f"Stowage bay/row/tier {s.bay}/{s.row}/{s.tier} out of bounds"
        return [_issue("ERROR", INVALID_STOWAGE_COORDINATE, ref, message)]
    return []


def _oog(line: ParsedLine) -> list[ParseIssue]:
    issues = []
    for side in _OOG_SIDES:
        key = f"oog.{side}_cm"
        value: int | None = getattr(line.oog, f"{side}_cm")
        raw = line.unconverted.get(key)
        if raw is not None or (value is not None and value <= 0):  # `chk_cme_oog`
            shown = raw if raw is not None else value
            message = f"Out-of-gauge {side} overhang {shown} is not a positive number of cm"
            issues.append(_issue("ERROR", MALFORMED_OOG, _ref(line, key), message))
        elif value is not None and value > INT_COLUMN_MAX:
            message = (
                f"Out-of-gauge {side} overhang {value} cm is larger than the stored maximum "
                f"{INT_COLUMN_MAX}"
            )
            issues.append(_issue("ERROR", MALFORMED_OOG, _ref(line, key), message))
    return issues


def _check_digit(line: ParsedLine) -> list[ParseIssue]:
    number = line.container_number
    if number is None:
        return []
    key = normalise_container_number(number)
    if not _CONTAINER_NUMBER.fullmatch(key) or iso6346_check_digit(key) == int(key[-1]):
        return []
    message = f"Container check digit does not match ISO 6346 for {number}"
    return [_issue("WARNING", CHECK_DIGIT_MISMATCH, _eqd_ref(line), message)]


def _full_empty(line: ParsedLine) -> list[ParseIssue]:
    if line.full_empty is not None:
        return []
    raw = line.unconverted.get("full_empty")
    if raw is not None:
        message = (
            f"Full/empty indicator {raw} not recognised for container {line.container_number}; "
            "written as NULL"
        )
    else:
        message = (
            f"Full/empty indicator missing for container {line.container_number}; written as NULL"
        )
    return [_issue("WARNING", MISSING_FULL_EMPTY, _eqd_ref(line), message)]


def _port_of_discharge(line: ParsedLine) -> list[ParseIssue]:
    if line.port_of_discharge is not None:
        return []
    message = f"Port of discharge missing for container {line.container_number}; written as NULL"
    return [_issue("WARNING", MISSING_PORT_OF_DISCHARGE, _eqd_ref(line), message)]
