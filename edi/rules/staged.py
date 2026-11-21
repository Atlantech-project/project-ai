"""The correction path (AI-031, DEC-03, CT-12 `source = STAGED_PAYLOAD`).

A staff-corrected `staged_payload` is read back into the parser's records and checked by the same
`validate` as a file. Writing `staged_payload` is the commit's job (AI-032).

The payload has no segment texts, so every issue points at the line's `segment_ref`. A value of
the wrong JSON type is kept as text in `unconverted`, exactly as the parser keeps a value it
cannot convert, so the same malformed-value rules apply.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any, Final

from edi.records import FullEmpty, Oog, ParsedLine, ParsedVessel, Stowage
from edi.rules.checks import Finding, Reference, validate

FORMAT_VERSION: Final = "1.0"
_FULL_EMPTY: Final[Mapping[str, FullEmpty]] = {"FULL": "FULL", "EMPTY": "EMPTY"}
_OOG_SIDES: Final = ("front", "back", "right", "left", "height")


class StagedPayloadError(ValueError):
    """The payload is not a CT-12 `staged_payload` at all (shape, not content)."""


def read_staged_payload(payload: Mapping[str, Any]) -> tuple[ParsedVessel, tuple[ParsedLine, ...]]:
    if payload.get("format_version") != FORMAT_VERSION:
        raise StagedPayloadError(f"format_version must be {FORMAT_VERSION!r}")
    vessel_data = payload.get("vessel")
    lines_data = payload.get("lines")
    if not isinstance(vessel_data, Mapping) or not isinstance(lines_data, list):
        raise StagedPayloadError("staged_payload needs a 'vessel' object and a 'lines' array")
    vessel = ParsedVessel(
        imo_number=_text(vessel_data.get("imo_number")),
        name=_text(vessel_data.get("name")),
        call_sign=_text(vessel_data.get("call_sign")),
        segment_ref=None,
    )
    lines = []
    for index, item in enumerate(lines_data, start=1):
        if not isinstance(item, Mapping):
            raise StagedPayloadError(f"line {index} is not an object")
        lines.append(_line(item, index))
    return vessel, tuple(lines)


def validate_staged_payload(
    payload: Mapping[str, Any], reference: Reference
) -> tuple[Finding, ...]:
    """Re-validate a corrected payload with the file rules (CT-12 correction step 3)."""
    vessel, lines = read_staged_payload(payload)
    return validate(vessel, lines, reference)


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value != "" else None


def _raw(value: object) -> str:
    return value if isinstance(value, str) else json.dumps(value)


def _line(item: Mapping[str, Any], index: int) -> ParsedLine:
    unconverted: dict[str, str] = {}

    def integer(key: str, value: object) -> int | None:
        if value is None:
            return None
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        unconverted[key] = _raw(value)
        return None

    line_no = item.get("line_no")
    if not isinstance(line_no, int) or isinstance(line_no, bool):
        line_no = index
    segment_ref = _text(item.get("segment_ref")) or f"line {line_no}"

    full_empty_value = item.get("full_empty")
    full_empty = _FULL_EMPTY.get(full_empty_value) if isinstance(full_empty_value, str) else None
    if full_empty is None and full_empty_value is not None:
        unconverted["full_empty"] = _raw(full_empty_value)

    temperature = _decimal(item.get("reefer_set_temperature"))
    if temperature is None and item.get("reefer_set_temperature") is not None:
        unconverted["reefer_set_temperature"] = _raw(item["reefer_set_temperature"])

    imdg = item.get("imdg_class")
    if imdg is not None and not isinstance(imdg, str):
        unconverted["imdg_class"] = _raw(imdg)

    oog_value = item.get("oog")
    oog_data: Mapping[str, Any] = oog_value if isinstance(oog_value, Mapping) else {}
    oog = Oog(**{f"{s}_cm": integer(f"oog.{s}_cm", oog_data.get(f"{s}_cm")) for s in _OOG_SIDES})

    stowage_data = item.get("stowage")
    if isinstance(stowage_data, Mapping):
        stowage = Stowage(
            integer("stowage", stowage_data.get("bay")),
            integer("stowage", stowage_data.get("row")),
            integer("stowage", stowage_data.get("tier")),
        )
    else:
        stowage = Stowage(None, None, None)
        if stowage_data is not None:
            unconverted["stowage"] = _raw(stowage_data)

    return ParsedLine(
        line_no=line_no,
        segment_ref=segment_ref,
        container_number=_text(item.get("container_number")),
        iso_size_type=_text(item.get("iso_size_type")),
        full_empty=full_empty,
        weight_kg=integer("weight_kg", item.get("weight_kg")),
        imdg_class=_text(imdg),
        oog=oog,
        reefer_set_temperature=temperature,
        stowage=stowage,
        port_of_load=_text(item.get("port_of_load")),
        port_of_discharge=_text(item.get("port_of_discharge")),
        segment_refs={},
        unconverted=unconverted,
    )


def _decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            number = Decimal(value)
        except InvalidOperation:
            return None
        return number if number.is_finite() else None
    return None
