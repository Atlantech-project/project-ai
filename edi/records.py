"""In-memory records produced by the BAPLIE parser (AI-030).

Values are kept exactly as written in the file. A value that cannot be converted to its
type leaves the typed field ``None`` and keeps its raw text in ``ParsedLine.unconverted``.
Content rules (AI-031) and the commit (AI-032) work from these records.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

Severity = Literal["ERROR", "WARNING"]
FullEmpty = Literal["FULL", "EMPTY"]
Version = Literal["D95B", "D13B"]


@dataclass(frozen=True)
class ParseIssue:
    severity: Severity
    code: str
    segment_ref: str | None
    message: str


@dataclass(frozen=True)
class ParsedVessel:
    imo_number: str | None
    name: str | None
    call_sign: str | None
    segment_ref: str | None


@dataclass(frozen=True)
class Stowage:
    bay: int | None
    row: int | None
    tier: int | None


@dataclass(frozen=True)
class Oog:
    """Out-of-gauge overhangs in cm (``DIM``); ``None`` = none given."""

    front_cm: int | None = None
    back_cm: int | None = None
    right_cm: int | None = None
    left_cm: int | None = None
    height_cm: int | None = None


@dataclass(frozen=True)
class ParsedLine:
    """One container line; field names follow the CT-12 ``staged_payload`` line.

    ``segment_ref`` is ``LOC+147+<position>`` (or the ``EQD`` text when the line has no
    stowage segment). ``segment_refs`` maps each filled field to the full text of its
    source segment. ``unconverted`` keeps raw text the parser could not map, in three
    shapes:

    - a measure (``weight_kg``, ``reefer_set_temperature``, ``oog.<side>_cm``): the
      whole element as written, unit included (``KGM:ABC``, ``x:CEL``, ``CMT:abc``);
    - ``stowage`` and ``full_empty``: the code as written (``12AB``, ``7``);
    - ``<field>#2``, ``<field>#3``, ...: the full text of a later segment that gave the
      same field again; the first value is kept. ``MEA+WT`` and ``MEA+VGM`` both map to
      ``weight_kg``, so a line with both has ``weight_kg#2`` (DEC-28 item 7).
    """

    line_no: int
    segment_ref: str
    container_number: str | None
    iso_size_type: str | None
    full_empty: FullEmpty | None
    weight_kg: int | None
    imdg_class: str | None
    oog: Oog
    reefer_set_temperature: Decimal | None
    stowage: Stowage
    port_of_load: str | None
    port_of_discharge: str | None
    segment_refs: Mapping[str, str] = field(default_factory=dict)
    unconverted: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ParseResult:
    """``READ``: the file is a readable BAPLIE (content rules not yet applied).

    ``REJECTED``: not a usable BAPLIE; exactly one ERROR issue, no vessel, no lines.
    """

    outcome: Literal["READ", "REJECTED"]
    version: Version | None
    message_identifier: str | None
    vessel: ParsedVessel | None
    lines: tuple[ParsedLine, ...]
    issues: tuple[ParseIssue, ...]
