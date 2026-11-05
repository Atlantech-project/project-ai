"""The scenario data type, the two sizes and the constants every generated file carries."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

SYNTHETIC_PREFIX: Final = "SYNTHETIC"
SYNTHETIC_LABEL: Final = "SYNTHETIC - generated test data, not operational data"
GENERATOR_VERSION: Final = "1"
START_DATE: Final = "2026-01-05 00:00:00"  # UTC; fixed so a seed alone decides the output

# Tables in insert order: parents before the rows that point at them.
TABLE_ORDER: Final = (
    "port_profiles",
    "terminals",
    "berths",
    "berth_terminals",
    "navigation_channels",
    "channel_waypoints",
    "tugboats",
    "vessel_types",
    "vessels",
    "external_systems",
    "berthing_requests",
)

ASSUMPTIONS: Final = (
    "All figures are assumptions, not data from any real port.",
    "Size: minimum is 1 terminal and 5 berths; reference is 8 terminals and 36 berths "
    "(Master_Context section 4). Berths are spread over terminals as evenly as possible.",
    "Terminal types: reference has 5 CONTAINER and 3 NON_CONTAINER; minimum has 1 CONTAINER.",
    "Berths: length uniform 180-400 m (container) or 150-300 m (non-container); "
    "max_vessel_loa is length minus 10 m; depth alongside uniform 11-16 m, datum LAT.",
    "Arrivals: mean 26 requests a day at reference scale and 4 at minimum (26 x 5/36, rounded), "
    "plus integer noise in [-3, +3] with a floor of 1. ETAs are uniform within the day. "
    "The start date is fixed at 2026-01-05 00:00:00 UTC.",
    "Vessels: one vessel per request. Types GENERAL_CARGO, CONTAINER, BULK_CARRIER and TANKER "
    "with weights 0.15, 0.55, 0.20 and 0.10 where a non-container terminal exists; "
    "minimum has container vessels only. LOA, beam ratio and max draft are drawn with "
    "triangular distributions inside per-type bounds. Arrival draft is 60-95% of max draft. "
    "Block coefficient is uniform 0.55-0.85. GT = 0.25 x LOA x beam x max draft; DWT = 1.4 x GT.",
    "Per-type bounds (LOA in m as low-high with mode; beam as a share of LOA; max draft in m "
    "as low-high with mode): GENERAL_CARGO 90-200 mode 140, 0.15-0.18, 5-10 mode 7.5; "
    "CONTAINER 150-400 mode 300, 0.14-0.16, 8-16 mode 13; BULK_CARRIER 150-290 mode 220, "
    "0.15-0.17, 9-17 mode 13; TANKER 120-250 mode 180, 0.15-0.17, 7-14 mode 10. "
    "Net tonnage = 0.6 x GT.",
    "Vessel-to-berth fit is not guaranteed: a vessel's LOA or draft can exceed every berth or "
    "the channel depth. Feasibility tests must filter or expect that.",
    "IMO numbers are random, unique seven-digit numbers whose check digit is deliberately wrong, "
    "so none can be a real ship.",
    "Exact bytes depend on Python's random module (3.14 here); a Python upgrade can change "
    "them, and the samples are then regenerated from the register.",
    "Requests: source EXTERNAL through one synthetic external system, status SUBMITTED. "
    "Container vessels request CONTAINER terminals; other vessels request NON_CONTAINER ones.",
    "Tugboats: 12 at reference scale, 3 at minimum; 40-80 tonnes bollard pull, all AVAILABLE.",
    "One navigation channel (depth 16 m, width 250 m, 10 knots, datum LAT) with 4 waypoints.",
    "The port is at latitude 0, longitude 0 with no UN/LOCODE. Time zone is Africa/Cairo.",
    "Not generated: users, tides, weather, pilots, tug masters, containers, BAPLIE data, "
    "recommendations. The schema copy is docs/ref/db/schema.sql (PortHub b4d2deb).",
)


class ScenarioSize(StrEnum):
    MINIMUM = "minimum"
    REFERENCE = "reference"


@dataclass(frozen=True)
class SizeProfile:
    container_terminals: int
    non_container_terminals: int
    berths: int
    tugboats: int
    requests_per_day: int


PROFILES: Final = {
    ScenarioSize.MINIMUM: SizeProfile(1, 0, 5, 3, 4),
    ScenarioSize.REFERENCE: SizeProfile(5, 3, 36, 12, 26),
}


@dataclass(frozen=True)
class Scenario:
    """A metadata block plus rows per table; plain data, so it round-trips through JSON."""

    metadata: dict[str, object]
    tables: dict[str, list[dict[str, object]]]
