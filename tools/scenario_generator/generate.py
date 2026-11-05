"""Build a synthetic scenario from a seed.

Everything random comes from one `random.Random(seed)`, drawn in a fixed order, and the start date
is a constant, so a seed alone decides the output. The assumptions behind each draw are listed in
`model.ASSUMPTIONS` and written into every scenario's metadata.
"""

import random
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final

from tools.scenario_generator.model import (
    ASSUMPTIONS,
    GENERATOR_VERSION,
    PROFILES,
    START_DATE,
    SYNTHETIC_LABEL,
    Scenario,
    ScenarioSize,
    SizeProfile,
)

Row = dict[str, object]
_DATETIME_FORMAT: Final = "%Y-%m-%d %H:%M:%S"
_DAILY_NOISE: Final = 3


@dataclass(frozen=True)
class _VesselType:
    code: str
    weight: float
    container: bool
    loa: tuple[float, float, float]  # triangular low, high, mode (metres)
    beam_ratio: tuple[float, float]  # beam as a share of LOA
    draft: tuple[float, float, float]  # triangular low, high, mode (metres)


_VESSEL_TYPES: Final = (
    _VesselType("GENERAL_CARGO", 0.15, False, (90, 200, 140), (0.15, 0.18), (5, 10, 7.5)),
    _VesselType("CONTAINER", 0.55, True, (150, 400, 300), (0.14, 0.16), (8, 16, 13)),
    _VesselType("BULK_CARRIER", 0.20, False, (150, 290, 220), (0.15, 0.17), (9, 17, 13)),
    _VesselType("TANKER", 0.10, False, (120, 250, 180), (0.15, 0.17), (7, 14, 10)),
)


def imo_check_digit_is_valid(imo: str) -> bool:
    """The IMO rule: the first six digits, weighted 7 down to 2, sum to the last digit mod 10."""
    digits = [int(char) for char in imo]
    total = sum(digit * weight for digit, weight in zip(digits[:6], range(7, 1, -1), strict=True))
    return total % 10 == digits[6]


def _fake_imo(rng: random.Random, used: set[str]) -> str:
    """A seven-digit number with a wrong check digit, so it can't name a real ship.

    Not in `used`: vessels.imo_number is UNIQUE, so a repeat would make the scenario unloadable.
    """
    while True:
        first_six = rng.randrange(100000, 1000000)
        digits = [int(char) for char in str(first_six)]
        total = sum(digit * weight for digit, weight in zip(digits, range(7, 1, -1), strict=True))
        wrong = (total % 10 + rng.randrange(1, 10)) % 10
        imo = f"{first_six}{wrong}"
        if imo not in used:
            used.add(imo)
            return imo


def _money(value: float) -> str:
    return f"{value:.2f}"


def _gross_tonnage(loa: float, beam: float, max_draft: float) -> int:
    return round(0.25 * loa * beam * max_draft)


def _build_terminals(profile: SizeProfile) -> list[Row]:
    types = ["CONTAINER"] * profile.container_terminals
    types += ["NON_CONTAINER"] * profile.non_container_terminals
    return [
        {
            "id": number,
            "code": f"SYN-T{number:02d}",
            "name": f"SYNTHETIC TERMINAL {number:02d}",
            "terminal_type": terminal_type,
            "is_active": 1,
        }
        for number, terminal_type in enumerate(types, start=1)
    ]


def _build_berths(
    rng: random.Random, profile: SizeProfile, terminals: list[Row]
) -> tuple[list[Row], list[Row]]:
    berths: list[Row] = []
    links: list[Row] = []
    for index in range(profile.berths):
        terminal = terminals[index % len(terminals)]
        low, high = (180, 400) if terminal["terminal_type"] == "CONTAINER" else (150, 300)
        length = round(rng.uniform(low, high), 2)
        number = index + 1
        berths.append(
            {
                "id": number,
                "code": f"SYN-B{number:02d}",
                "name": f"SYNTHETIC BERTH {number:02d}",
                "length": _money(length),
                "water_depth": _money(rng.uniform(11, 16)),
                "depth_datum": "LAT",
                "max_vessel_loa": _money(length - 10),
                "status": "ACTIVE",
            }
        )
        links.append({"berth_id": number, "terminal_id": terminal["id"]})
    return berths, links


def _build_tugboats(rng: random.Random, profile: SizeProfile) -> list[Row]:
    return [
        {
            "id": number,
            "name": f"SYNTHETIC TUG {number:02d}",
            "tug_power": _money(rng.uniform(40, 80)),
            "tug_power_unit": "BOLLARD_PULL_TONNES",
            "status": "AVAILABLE",
        }
        for number in range(1, profile.tugboats + 1)
    ]


def _build_channel() -> tuple[list[Row], list[Row]]:
    channel: list[Row] = [
        {
            "id": 1,
            "name": "SYNTHETIC CHANNEL",
            "depth": "16.00",
            "depth_datum": "LAT",
            "width": "250.00",
            "speed_limit_knots": "10.0",
            "is_active": 1,
        }
    ]
    waypoints: list[Row] = [
        {
            "id": order,
            "channel_id": 1,
            "sequence_order": order,
            "label": f"SYN-WP{order}",
            "latitude": f"{order * 0.01:.6f}",
            "longitude": f"{order * 0.01:.6f}",
        }
        for order in range(1, 5)
    ]
    return channel, waypoints


def _draw_vessel(
    rng: random.Random, number: int, vessel_type: _VesselType, type_id: int, used_imos: set[str]
) -> Row:
    loa = round(rng.triangular(*vessel_type.loa[:2], vessel_type.loa[2]), 2)
    beam = round(loa * rng.uniform(*vessel_type.beam_ratio), 2)
    max_draft = round(rng.triangular(*vessel_type.draft[:2], vessel_type.draft[2]), 2)
    return {
        "id": number,
        "imo_number": _fake_imo(rng, used_imos),
        "name": f"SYNTHETIC VESSEL {number:05d}",
        "vessel_type_id": type_id,
        "loa": _money(loa),
        "beam": _money(beam),
        "max_draft": _money(max_draft),
        "net_tonnage": round(_gross_tonnage(loa, beam, max_draft) * 0.6),
    }


def _build_traffic(
    rng: random.Random, profile: SizeProfile, terminals: list[Row], days: int
) -> tuple[list[Row], list[Row]]:
    start = datetime.strptime(START_DATE, _DATETIME_FORMAT).replace(tzinfo=UTC)
    by_kind = {
        True: [t for t in terminals if t["terminal_type"] == "CONTAINER"],
        False: [t for t in terminals if t["terminal_type"] == "NON_CONTAINER"],
    }
    eligible = [(i, t) for i, t in enumerate(_VESSEL_TYPES, start=1) if by_kind[t.container]]
    weights = [t.weight for _, t in eligible]
    vessels: list[Row] = []
    requests: list[Row] = []
    used_imos: set[str] = set()
    for day in range(days):
        count = max(1, profile.requests_per_day + rng.randint(-_DAILY_NOISE, _DAILY_NOISE))
        day_start = start + timedelta(days=day)
        offsets = sorted(rng.randrange(86400) for _ in range(count))
        for offset in offsets:
            number = len(vessels) + 1
            type_id, vessel_type = rng.choices(eligible, weights=weights)[0]
            vessel = _draw_vessel(rng, number, vessel_type, type_id, used_imos)
            loa, beam, max_draft = (float(str(vessel[k])) for k in ("loa", "beam", "max_draft"))
            arrival_draft = round(max_draft * rng.uniform(0.6, 0.95), 2)
            gross_tonnage = _gross_tonnage(loa, beam, max_draft)
            vessels.append(vessel)
            requests.append(
                {
                    "id": number,
                    "vessel_id": number,
                    "requested_terminal_id": rng.choice(by_kind[vessel_type.container])["id"],
                    "source": "EXTERNAL",
                    "external_system_id": 1,
                    "external_reference": f"SYNTHETIC-{number:06d}",
                    "requested_eta": (day_start + timedelta(seconds=offset)).strftime(
                        _DATETIME_FORMAT
                    ),
                    "arrival_draft": _money(arrival_draft),
                    "block_coefficient": f"{rng.uniform(0.55, 0.85):.3f}",
                    "gross_tonnage": gross_tonnage,
                    "deadweight_tonnes": round(gross_tonnage * 1.4),
                    "status": "SUBMITTED",
                }
            )
    return vessels, requests


def generate(size: ScenarioSize, seed: int, days: int = 7) -> Scenario:
    """The scenario for `size`, `seed` and a horizon of `days` days from the fixed start date."""
    if days < 1:
        raise ValueError(f"days must be at least 1, got {days}")
    profile = PROFILES[size]
    rng = random.Random(seed)
    terminals = _build_terminals(profile)
    berths, berth_terminals = _build_berths(rng, profile, terminals)
    channel, waypoints = _build_channel()
    tugboats = _build_tugboats(rng, profile)
    vessels, requests = _build_traffic(rng, profile, terminals, days)
    port_name = f"SYNTHETIC {size.value.upper()} PORT"
    tables: dict[str, list[Row]] = {
        "port_profiles": [
            {
                "id": 1,
                "public_id": str(uuid.UUID(int=rng.getrandbits(128), version=4)),
                "port_code": None,
                "governorate_code": "EG-SYN",
                "name": port_name,
                "latitude": "0.000000",
                "longitude": "0.000000",
                "timezone": "Africa/Cairo",
            }
        ],
        "terminals": terminals,
        "berths": berths,
        "berth_terminals": berth_terminals,
        "navigation_channels": channel,
        "channel_waypoints": waypoints,
        "tugboats": tugboats,
        "vessel_types": [
            {"id": i, "code": t.code, "name": f"SYNTHETIC {t.code.lower().replace('_', ' ')}"}
            for i, t in enumerate(_VESSEL_TYPES, start=1)
        ],
        "vessels": vessels,
        "external_systems": [{"id": 1, "code": "SYN-EXT", "name": "SYNTHETIC external system"}],
        "berthing_requests": requests,
    }
    metadata: dict[str, object] = {
        "synthetic": True,
        "label": SYNTHETIC_LABEL,
        "size": size.value,
        "seed": seed,
        "days": days,
        "generator_version": GENERATOR_VERSION,
        "start_date": START_DATE,
        "counts": {name: len(rows) for name, rows in tables.items()},
        "assumptions": list(ASSUMPTIONS),
    }
    return Scenario(metadata=metadata, tables=tables)
