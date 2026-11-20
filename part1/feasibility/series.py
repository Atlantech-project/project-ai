"""Which constraint codes A4 owns, which belong to another component, and the series they read.

`constraint_types` has no column naming the quantity a code limits, so the mapping is kept here
(AI-044 task decision, Proposed). Every active code must be in exactly one of the two lists; a code
in neither is a configuration error, never a silent pass. A new seed code (gust, visibility,
tide/surge: AI-009 criterion 1) needs a line here.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final

from common.units import Unit
from part1.feasibility.model import Series, SeriesUnits


@dataclass(frozen=True)
class CodeRegistry:
    """`a4`: code -> series A4 checks. `elsewhere`: code -> the component that owns it."""

    a4: Mapping[str, Series] = field(default_factory=dict)
    elsewhere: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        both = sorted(set(self.a4) & set(self.elsewhere))
        if both:
            raise ValueError(f"constraint codes in both lists: {', '.join(both)}")
        object.__setattr__(self, "a4", MappingProxyType(dict(self.a4)))
        object.__setattr__(self, "elsewhere", MappingProxyType(dict(self.elsewhere)))


DEFAULT_REGISTRY: Final = CodeRegistry(
    a4={
        "MAX_WIND_KN": Series.WIND_SPEED,
        "MAX_WAVE_HEIGHT_M": Series.WAVE_HEIGHT,
    },
    elsewhere={
        "MIN_UKC_M": "AI-045 (A5 under-keel clearance)",
        # Vessel and berth safety codes such as LOA go here, owned by B2 (AI-051), once seeded.
    },
)


def series_unit(series: Series, units: SeriesUnits) -> str:
    """The unit a series arrives in (`forecast_runs` columns; the rest are metres)."""
    match series:
        case Series.WIND_SPEED | Series.WIND_GUST:
            return units.wind_speed_unit
        case Series.VISIBILITY:
            return units.visibility_unit
        case Series.CURRENT_SPEED:
            return units.current_speed_unit
        case Series.WAVE_HEIGHT | Series.SEA_LEVEL | Series.TIDE | Series.SURGE:
            return Unit.METRES.value
