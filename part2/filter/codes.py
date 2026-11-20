"""Which Marine Safety Officer codes B2 checks, and against which vessel attribute (AI-051).

`constraint_types` has no column naming the quantity a code limits, so B2 keeps its own list, as A4
does (AI-044). A B2 code must also be listed by A4 as owned elsewhere, so A4 never fails on it.

**The B2 list is empty**: no vessel-safety code is seeded yet (AI-009 criterion 1). The Marine
Safety Officer codes must be seeded, and added here, before these rules are active in production.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from common.units import Unit
from part1.feasibility import DEFAULT_REGISTRY, CodeRegistry


class VesselAttribute(StrEnum):
    """A request or vessel value B2 can compare with a limit, and its unit."""

    LOA = "loa"
    BEAM = "beam"
    ARRIVAL_DRAFT = "arrival_draft"
    DEADWEIGHT = "deadweight_tonnes"

    @property
    def unit(self) -> str:
        return Unit.TONNES.value if self is VesselAttribute.DEADWEIGHT else Unit.METRES.value


@dataclass(frozen=True)
class B2Registry:
    """`b2`: code -> the attribute B2 compares. `a4`: A4's lists, for the codes B2 doesn't own."""

    b2: Mapping[str, VesselAttribute] = field(default_factory=dict)
    a4: CodeRegistry = field(default=DEFAULT_REGISTRY)

    def __post_init__(self) -> None:
        in_a4 = sorted(set(self.b2) & set(self.a4.a4))
        if in_a4:
            raise ValueError(f"B2 codes that A4 checks: {', '.join(in_a4)}")
        unlisted = sorted(set(self.b2) - set(self.a4.elsewhere))
        if unlisted:
            raise ValueError(f"B2 codes A4 doesn't list as owned elsewhere: {', '.join(unlisted)}")
        object.__setattr__(self, "b2", MappingProxyType(dict(self.b2)))

    def owner(self, code: str) -> str | None:
        """`"B2"`, `"A4"`, another owner, or None for a code no list knows."""
        if code in self.b2:
            return "B2"
        if code in self.a4.a4:
            return "A4"
        return self.a4.elsewhere.get(code)


DEFAULT_B2_REGISTRY: Final = B2Registry()
