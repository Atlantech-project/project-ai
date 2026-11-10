"""BAPLIE parser (AI-030): bytes in, in-memory records out.

Deterministic, no I/O. Handles reading-the-file problems only: an unreadable or
non-EDIFACT file, broken syntax, a wrong message type or unsupported version (REJECTED),
and unknown segments (WARNING). Content checks belong to AI-031.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal

from edi import mapping as m
from edi.records import (
    FullEmpty,
    Oog,
    ParsedLine,
    ParsedVessel,
    ParseIssue,
    ParseResult,
    Stowage,
    Version,
)
from edi.syntax import Segment, ServiceChars, SyntaxProblem, tokenize

_BOM = "﻿"
_NUMBER = re.compile(r"[+-]?[0-9]+(\.[0-9]+)?")


class _Rejected(Exception):
    def __init__(self, code: str, segment_ref: str | None, message: str) -> None:
        super().__init__(message)
        self.issue = ParseIssue("ERROR", code, segment_ref, message)


def parse_baplie(data: bytes) -> ParseResult:
    """Parse one BAPLIE file. Never raises for bad input; problems become issues."""
    try:
        chars, version, identifier, body = _read_envelope(data)
    except _Rejected as rejected:
        return ParseResult("REJECTED", None, None, None, (), (rejected.issue,))
    vessel, lines, issues = _walk(body, chars)
    return ParseResult("READ", version, identifier, vessel, lines, issues)


# --- Message walk ------------------------------------------------------------------


@dataclass
class _LineBuilder:
    """Fields of one container line while it is being read."""

    chars: ServiceChars
    values: dict[str, object] = field(default_factory=dict)
    refs: dict[str, str] = field(default_factory=dict)
    unconverted: dict[str, str] = field(default_factory=dict)
    repeats: dict[str, int] = field(default_factory=dict)
    first_text: str = ""
    has_stowage: bool = False
    has_container: bool = False

    def set(self, name: str, value: object, segment: Segment) -> None:
        """Keep the first value of a field; a repeat is kept as raw text."""
        if name in self.refs or name in self.unconverted:
            self._repeat(name, segment)
            return
        self.values[name] = value
        self.refs[name] = segment.text

    def raw(self, name: str, text: str, segment: Segment) -> None:
        """A value that cannot be converted: the field stays ``None``, the text is kept."""
        if name in self.refs or name in self.unconverted:
            self._repeat(name, segment)
            return
        self.unconverted[name] = text
        self.refs[name] = segment.text

    def _repeat(self, name: str, segment: Segment) -> None:
        """Keep the segment text of a repeat as ``<name>#2``, ``<name>#3``, ..."""
        n = self.repeats.get(name, 1) + 1
        self.repeats[name] = n
        self.unconverted[f"{name}#{n}"] = segment.text

    def element_text(self, components: tuple[str, ...]) -> str:
        return self.chars.component.join(components).rstrip(self.chars.component)

    def build(self, line_no: int) -> ParsedLine:
        v = self.values
        refs = self.refs
        segment_ref = refs.get("stowage") or refs.get("container_number") or self.first_text
        stowage = v.get("stowage")
        temperature = v.get("reefer_set_temperature")
        full_empty = v.get("full_empty")
        return ParsedLine(
            line_no=line_no,
            segment_ref=segment_ref,
            container_number=_str(v.get("container_number")),
            iso_size_type=_str(v.get("iso_size_type")),
            full_empty="FULL"
            if full_empty == "FULL"
            else "EMPTY"
            if full_empty == "EMPTY"
            else None,
            weight_kg=_int(v.get("weight_kg")),
            imdg_class=_str(v.get("imdg_class")),
            oog=Oog(
                front_cm=_int(v.get("oog.front_cm")),
                back_cm=_int(v.get("oog.back_cm")),
                right_cm=_int(v.get("oog.right_cm")),
                left_cm=_int(v.get("oog.left_cm")),
                height_cm=_int(v.get("oog.height_cm")),
            ),
            reefer_set_temperature=temperature if isinstance(temperature, Decimal) else None,
            stowage=stowage if isinstance(stowage, Stowage) else Stowage(None, None, None),
            port_of_load=_str(v.get("port_of_load")),
            port_of_discharge=_str(v.get("port_of_discharge")),
            segment_refs=dict(refs),
            unconverted=dict(self.unconverted),
        )


def _str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _walk(
    body: list[Segment], chars: ServiceChars
) -> tuple[ParsedVessel, tuple[ParsedLine, ...], tuple[ParseIssue, ...]]:
    vessel = ParsedVessel(None, None, None, None)
    builders: list[_LineBuilder] = []
    issues: list[ParseIssue] = []

    for segment in body:
        tag = segment.tag
        if tag not in m.KNOWN_TAGS:
            issues.append(
                ParseIssue("WARNING", m.UNKNOWN_SEGMENT, segment.text, m.msg_unknown_segment(tag))
            )
            continue
        qualifier = _component(segment, 0, 0)

        if tag == "TDT" and qualifier == m.VESSEL_TDT_QUALIFIER:
            if vessel.segment_ref is None:
                vessel = _vessel(segment)
            continue

        starts_stowage = tag == "LOC" and qualifier == m.STOWAGE_QUALIFIER
        starts_container = tag == "EQD" and qualifier == m.CONTAINER_QUALIFIER
        if starts_stowage or starts_container:
            current = builders[-1] if builders else None
            if (
                current is None
                or (starts_stowage and current.has_stowage)
                or (starts_container and current.has_container)
            ):
                current = _LineBuilder(chars, first_text=segment.text)
                builders.append(current)
        if not builders:
            continue  # header segment
        _map(builders[-1], segment, qualifier, chars)

    lines = tuple(builder.build(n) for n, builder in enumerate(builders, start=1))
    return vessel, lines, tuple(issues)


def _component(segment: Segment, element: int, component: int) -> str:
    if element >= len(segment.elements):
        return ""
    parts = segment.elements[element]
    return parts[component] if component < len(parts) else ""


def _vessel(segment: Segment) -> ParsedVessel:
    imo = _component(segment, m.VESSEL_ID_ELEMENT, 0)
    name = _component(segment, m.VESSEL_ID_ELEMENT, 3)
    return ParsedVessel(imo or None, name or None, None, segment.text)


def _map(line: _LineBuilder, segment: Segment, qualifier: str, chars: ServiceChars) -> None:
    tag = segment.tag
    if tag == "LOC" and qualifier == m.STOWAGE_QUALIFIER:
        line.has_stowage = True
        _map_stowage(line, segment)
    elif tag == "LOC" and qualifier in m.PORT_QUALIFIERS:
        port = _component(segment, 1, 0)
        if port:
            line.set(m.PORT_QUALIFIERS[qualifier], port, segment)
    elif tag == "EQD" and qualifier == m.CONTAINER_QUALIFIER:
        line.has_container = True
        _map_container(line, segment)
    elif tag == "MEA" and (
        qualifier in m.WEIGHT_QUALIFIERS or _component(segment, 1, 0) in m.WEIGHT_QUALIFIERS
    ):
        _map_measure(line, "weight_kg", segment, 2, m.WEIGHT_UNIT, chars, integral=True)
    elif tag == "TMP" and qualifier == m.TEMPERATURE_QUALIFIER:
        _map_measure(
            line, "reefer_set_temperature", segment, 1, m.TEMPERATURE_UNIT, chars, integral=False
        )
    elif tag == "DGS" and qualifier == m.DG_QUALIFIER:
        imdg = _component(segment, 1, 0)
        if imdg:
            line.set("imdg_class", imdg, segment)
    elif tag == "DIM" and qualifier in m.OOG_QUALIFIERS:
        _map_measure(
            line,
            f"oog.{m.OOG_QUALIFIERS[qualifier]}",
            segment,
            1,
            m.OOG_UNIT,
            chars,
            integral=True,
            first_number=True,
        )


def _map_stowage(line: _LineBuilder, segment: Segment) -> None:
    position = _component(segment, 1, 0)
    if not position:
        return
    if len(position) == m.STOWAGE_DIGITS and position.isascii() and position.isdigit():
        line.set(
            "stowage",
            Stowage(int(position[0:3]), int(position[3:5]), int(position[5:7])),
            segment,
        )
    else:
        line.raw("stowage", position, segment)


def _map_container(line: _LineBuilder, segment: Segment) -> None:
    number = _component(segment, 1, 0)
    size_type = _component(segment, 2, 0)
    full_empty = _component(segment, m.FULL_EMPTY_ELEMENT, 0)
    if number:
        line.set("container_number", number, segment)
    if size_type:
        line.set("iso_size_type", size_type, segment)
    if full_empty:
        code: FullEmpty | None = m.FULL_EMPTY_CODES.get(full_empty)
        if code is None:
            line.raw("full_empty", full_empty, segment)
        else:
            line.set("full_empty", code, segment)


def _map_measure(
    line: _LineBuilder,
    name: str,
    segment: Segment,
    element: int,
    unit: str,
    chars: ServiceChars,
    *,
    integral: bool,
    first_number: bool = False,
) -> None:
    """Map ``<unit>:<value>`` (TMP: ``<value>:<unit>``) to a number, or keep the raw text."""
    if element >= len(segment.elements):
        return
    components = segment.elements[element]
    raw = line.element_text(components)
    if not raw:
        return
    if segment.tag == "TMP":
        found_unit = components[1] if len(components) > 1 else ""
        value = components[0]
    else:
        found_unit = components[0]
        rest = components[1:]
        if first_number:
            value = next((c for c in rest if c), "")
        else:
            value = rest[0] if rest else ""
    number = _number(value, chars) if found_unit == unit else None
    if number is None or (integral and number != number.to_integral_value()):
        line.raw(name, raw, segment)
        return
    line.set(name, int(number) if integral else number, segment)


def _number(text: str, chars: ServiceChars) -> Decimal | None:
    normalised = text.replace(chars.decimal, ".") if chars.decimal != "." else text
    if not _NUMBER.fullmatch(normalised):
        return None
    return Decimal(normalised)


# --- Envelope ----------------------------------------------------------------------


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("iso-8859-1")


def _read_envelope(data: bytes) -> tuple[ServiceChars, Version, str, list[Segment]]:
    """Check the envelope; return the separators, version, identifier and message body.

    The body is the segments strictly between ``UNH`` and ``UNT``.
    """
    text = _decode(data).removeprefix(_BOM)
    stripped = text.strip()
    if not stripped:
        raise _Rejected(m.UNREADABLE_FILE, None, m.MSG_UNREADABLE)
    if not stripped.startswith(("UNA", "UNB")):
        found = _found_in_non_edifact(text)
        raise _Rejected(m.NOT_EDIFACT, "UNH", m.msg_unsupported(found))

    try:
        chars, segments = tokenize(stripped)
    except SyntaxProblem as problem:
        if problem.reason == "UNTERMINATED":
            complete = _complete_tags(stripped)
            if "UNT" not in complete and "UNZ" not in complete:
                raise _Rejected(m.CORRUPTED_SYNTAX, None, m.MSG_TRUNCATED) from problem
            raise _Rejected(m.CORRUPTED_SYNTAX, None, m.MSG_UNTERMINATED) from problem
        raise _Rejected(m.UNREADABLE_FILE, None, m.MSG_UNREADABLE) from problem

    tags = [segment.tag for segment in segments]
    if "UNH" not in tags:
        raise _Rejected(m.CORRUPTED_SYNTAX, None, m.MSG_NO_UNH)
    unh_at = tags.index("UNH")
    if "UNT" not in tags[unh_at:]:
        raise _Rejected(m.CORRUPTED_SYNTAX, None, m.MSG_NO_UNT)
    if "UNZ" not in tags:
        raise _Rejected(m.CORRUPTED_SYNTAX, None, m.MSG_NO_UNZ)

    unh = segments[unh_at]
    identifier_parts = unh.elements[1] if len(unh.elements) > 1 else ("",)
    identifier = ":".join(identifier_parts)
    message_type = identifier_parts[0]
    if message_type != m.MESSAGE_TYPE:
        raise _Rejected(m.WRONG_MESSAGE_TYPE, "UNH", m.msg_unsupported(identifier))
    key = tuple((list(identifier_parts[1:4]) + ["", "", ""])[:3])
    version = m.SUPPORTED_VERSIONS.get((key[0], key[1], key[2]))
    if version is None:
        raise _Rejected(m.UNSUPPORTED_BAPLIE_VERSION, "UNH", m.msg_unsupported(identifier))

    message_count = tags.count("UNH")
    if message_count > 1:
        raise _Rejected(m.CORRUPTED_SYNTAX, "UNH", m.msg_message_count(message_count))

    unt_at = tags.index("UNT", unh_at)
    unt = segments[unt_at]
    declared = unt.elements[0][0] if unt.elements else ""
    counted = unt_at - unh_at + 1
    if declared != str(counted):
        raise _Rejected(m.CORRUPTED_SYNTAX, "UNT", m.msg_unt_count(declared, counted))

    return chars, version, identifier, segments[unh_at + 1 : unt_at]


def _found_in_non_edifact(text: str) -> str:
    """The first 3 characters as read (BOM removed), or "none" if none is readable."""
    found = text[: m.NOT_EDIFACT_FOUND_LENGTH]
    if any(char.isprintable() and not char.isspace() for char in found):
        return found
    return m.NOT_EDIFACT_FOUND_NONE


def _complete_tags(text: str) -> set[str]:
    """Tags of the complete segments of an unterminated text (best effort)."""
    try:
        _chars, segments = tokenize(text[: _last_terminator(text) + 1])
    except SyntaxProblem:
        return set()
    return {segment.tag for segment in segments}


def _last_terminator(text: str) -> int:
    terminator = ServiceChars.DEFAULT.terminator
    if text.startswith("UNA") and len(text) >= 9:
        terminator = text[8]
    return text.rfind(terminator)
