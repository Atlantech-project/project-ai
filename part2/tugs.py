"""Tug requirement per berthing request (AI-054, DEC-20).

Computed before the solver and passed to CP-SAT as integers; CP-SAT doesn't compute them (AI-055).
Every number lives in `tug_rules.json` with its source, so this module holds no thresholds.
No reduction is applied for bow or stern thrusters: there is no thruster data, so results are
conservative. A missing input with no conservative default raises, and nothing is guessed.
"""

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Final

from common.config import ConfigurationError

RULES_PATH: Final = Path(__file__).with_name("tug_rules.json")

_BOLLARD_PULL_UNIT: Final = "BOLLARD_PULL_TONNES"
_RULE_STATUSES: Final = frozenset({"PROPOSED", "APPROVED"})

FLAG_CB_FALLBACK: Final = "cb_fallback_used"
FLAG_MAX_DRAFT: Final = "max_draft_used"
FLAG_PILOT_OVERRIDE: Final = "pilot_override"
FLAG_PILOT_UNKNOWN: Final = "pilot_request_unknown"
FLAG_RULES_UNVALIDATED: Final = "rules_unvalidated"
FLAG_TUG_POWER: Final = "tug_power_not_bollard_pull"


@dataclass(frozen=True)
class Band:
    n_base: int
    min_bp_per_tug: Decimal
    bp_floor: int


@dataclass(frozen=True)
class LoaBand(Band):
    loa_max: Decimal


@dataclass(frozen=True)
class TugRules:
    status: str
    gt_threshold: int
    cb_min: Decimal
    cb_max: Decimal
    cb_by_vessel_type: Mapping[str, Decimal]
    cb_default: Decimal
    water_density_factor: Decimal
    mass_vessel_types: frozenset[str]
    mass_coefficient: Decimal
    mass_divisor: Decimal
    mass_constant: Decimal
    loa_bands: tuple[LoaBand, ...]
    large_gt_min: int
    large_draught_split: Decimal
    large_below_split: Band
    large_at_or_above_split: Band
    n_cap_offset: int


@dataclass(frozen=True)
class PilotOverride:
    n_min: int | None = None
    bp_req: int | None = None


@dataclass(frozen=True)
class Tug:
    id: int
    tug_power: Decimal
    tug_power_unit: str


@dataclass(frozen=True)
class TugRequest:
    """The inputs, from `vessels`, `vessel_types` and `berthing_requests`."""

    loa: Decimal | None
    beam: Decimal | None
    arrival_draft: Decimal | None
    max_draft: Decimal | None
    gross_tonnage: int | None
    vessel_type_code: str | None
    block_coefficient: Decimal | None
    # No such field exists yet. None applies the table, so unknown never means zero tugs.
    pilot_requested: bool | None
    pilot_override: PilotOverride | None = None


@dataclass(frozen=True)
class TugRequirement:
    n_min: int
    n_cap: int
    bp_req: int
    eligible_tugs: frozenset[int]
    flags: tuple[str, ...]


def _section(data: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    section: Mapping[str, Any] = data[name]
    if not section["source"] or not isinstance(section["interim"], bool):
        raise ValueError(f"{name} needs a source and an interim note")
    return section


def _decimal(value: Any) -> Decimal:
    # Strings only: a JSON float would already have lost exactness.
    if not isinstance(value, str):
        raise TypeError("a decimal value must be a string")
    return Decimal(value)


def _band(row: Mapping[str, Any]) -> Band:
    return Band(int(row["n_base"]), _decimal(row["min_bp_per_tug"]), int(row["bp_floor"]))


def _parse_rules(data: Mapping[str, Any]) -> TugRules:
    if data["status"] not in _RULE_STATUSES:
        raise ValueError("unknown status")
    compulsory = _section(data, "compulsory_towage")
    cb = _section(data, "block_coefficient")
    displacement = _section(data, "displacement")
    mass = _section(data, "mass_bollard_pull")
    bands = _section(data, "loa_bands")
    large = _section(data, "large_vessel")
    n_cap = _section(data, "n_cap")
    loa_bands = tuple(
        LoaBand(
            int(row["n_base"]),
            _decimal(row["min_bp_per_tug"]),
            int(row["bp_floor"]),
            _decimal(row["loa_max"]),
        )
        for row in bands["bands"]
    )
    limits = [band.loa_max for band in loa_bands]
    if not limits or limits != sorted(limits):
        raise ValueError("loa_bands must be a non-empty ascending list")
    large_bands = {row["draught"]: _band(row) for row in large["bands"]}
    return TugRules(
        status=data["status"],
        gt_threshold=int(compulsory["gt_threshold"]),
        cb_min=_decimal(cb["valid_min"]),
        cb_max=_decimal(cb["valid_max"]),
        cb_by_vessel_type={code: _decimal(v) for code, v in cb["by_vessel_type"].items()},
        cb_default=_decimal(cb["default"]),
        water_density_factor=_decimal(displacement["water_density_factor"]),
        mass_vessel_types=frozenset(mass["vessel_types"]),
        mass_coefficient=_decimal(mass["coefficient"]),
        mass_divisor=_decimal(mass["divisor"]),
        mass_constant=_decimal(mass["constant"]),
        loa_bands=loa_bands,
        large_gt_min=int(large["gt_min"]),
        large_draught_split=_decimal(large["draught_split"]),
        large_below_split=large_bands["below_split"],
        large_at_or_above_split=large_bands["at_or_above_split"],
        n_cap_offset=int(n_cap["offset"]),
    )


def load_rules(path: Path = RULES_PATH) -> TugRules:
    """Load and check the rules file. A problem is a configuration error."""
    try:
        return _parse_rules(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError, InvalidOperation) as error:
        raise ConfigurationError(
            f"tug rules {path.name} can't be used: {type(error).__name__}: {error}"
        ) from error


def _positive(name: str, value: Decimal | int | None) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, Decimal | int) or value <= 0:
        raise ConfigurationError(f"{name} must be a positive number", [name])
    return Decimal(value)


def block_coefficient(
    value: Decimal | None, vessel_type_code: str | None, rules: TugRules
) -> tuple[Decimal, bool]:
    """The request's Cb, or the type table's. The bool says whether the table was used."""
    if value is not None and rules.cb_min <= value <= rules.cb_max:
        return value, False
    if vessel_type_code is None:
        return rules.cb_default, True
    return rules.cb_by_vessel_type.get(vessel_type_code, rules.cb_default), True


def displacement_tonnes(
    loa: Decimal, beam: Decimal, draught: Decimal, cb: Decimal, rules: TugRules
) -> Decimal:
    """Displacement from the hull's dimensions.

    Never use GT or NT here: they measure volume, not weight.
    """
    return loa * beam * draught * cb * rules.water_density_factor


def mass_bollard_pull(displacement: Decimal, rules: TugRules) -> Decimal:
    return rules.mass_coefficient * displacement / rules.mass_divisor + rules.mass_constant


def _band_for(loa: Decimal, gross_tonnage: Decimal, draught: Decimal, rules: TugRules) -> Band:
    if gross_tonnage < rules.large_gt_min:
        for band in rules.loa_bands:
            if loa <= band.loa_max:
                return band
    if draught < rules.large_draught_split:
        return rules.large_below_split
    return rules.large_at_or_above_split


def _override_value(name: str, value: int | None, computed: int) -> int:
    if value is None:
        return computed
    if value < 0:
        raise ConfigurationError(f"pilot_override {name} must not be negative", ["pilot_override"])
    return value


def compute_tug_requirement(
    request: TugRequest, tugs: Iterable[Tug], rules: TugRules
) -> TugRequirement:
    """Compute one request's tug requirement (DEC-20). A pure function: no I/O, no solver."""
    flags: list[str] = []
    if rules.status != "APPROVED":
        flags.append(FLAG_RULES_UNVALIDATED)

    loa = _positive("loa", request.loa)
    beam = _positive("beam", request.beam)
    gross_tonnage = _positive("gross_tonnage", request.gross_tonnage)
    if request.arrival_draft is None:
        draught = _positive("max_draft", request.max_draft)
        flags.append(FLAG_MAX_DRAFT)
    else:
        draught = _positive("arrival_draft", request.arrival_draft)

    below_threshold = gross_tonnage < rules.gt_threshold
    if below_threshold and request.pilot_requested is False and request.pilot_override is None:
        return TugRequirement(0, 0, 0, frozenset(), tuple(flags))
    if below_threshold and request.pilot_requested is None:
        flags.append(FLAG_PILOT_UNKNOWN)

    band = _band_for(loa, gross_tonnage, draught, rules)
    bp_required = Decimal(band.bp_floor)
    if request.vessel_type_code in rules.mass_vessel_types:
        cb, fell_back = block_coefficient(
            request.block_coefficient, request.vessel_type_code, rules
        )
        if fell_back:
            flags.append(FLAG_CB_FALLBACK)
        displacement = displacement_tonnes(loa, beam, draught, cb, rules)
        bp_required = max(bp_required, mass_bollard_pull(displacement, rules))
    bp_req = int(bp_required.to_integral_value(rounding=ROUND_CEILING))
    n_min = band.n_base

    if request.pilot_override is not None:
        n_min = _override_value("n_min", request.pilot_override.n_min, n_min)
        bp_req = _override_value("bp_req", request.pilot_override.bp_req, bp_req)
        flags.append(FLAG_PILOT_OVERRIDE)

    # HP and kW have no agreed conversion to bollard pull, so those tugs aren't eligible.
    eligible: set[int] = set()
    unrated = False
    for tug in tugs:
        if tug.tug_power_unit != _BOLLARD_PULL_UNIT:
            unrated = True
        elif tug.tug_power >= band.min_bp_per_tug:
            eligible.add(tug.id)
    if unrated:
        flags.append(FLAG_TUG_POWER)

    return TugRequirement(
        n_min=n_min,
        n_cap=n_min + rules.n_cap_offset,
        bp_req=bp_req,
        eligible_tugs=frozenset(eligible),
        flags=tuple(flags),
    )
