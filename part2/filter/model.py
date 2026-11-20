"""B2 data: what the filter takes and returns (AI-051).

Reasons carry CT-10/CT-13 codes: STRUCTURAL codes from their closed lists, or a SAFETY
`constraint_types.code`. Every datetime is timezone-aware UTC.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from part1.feasibility import ConstraintType
from part2.filter.codes import DEFAULT_B2_REGISTRY, B2Registry
from part2.tugs import TugRequirement


class Kind(StrEnum):
    STRUCTURAL = "STRUCTURAL"
    SAFETY = "SAFETY"


class Code(StrEnum):
    """STRUCTURAL codes: the CT-13 OVERRIDE list.

    `PILOT_RANK_LIMIT` and `TUG_COUNT` are Proposed for CT-10 (AI-051).
    """

    TERMINAL_COMPATIBILITY = "TERMINAL_COMPATIBILITY"
    BERTH_UNAVAILABLE = "BERTH_UNAVAILABLE"
    BERTH_OCCUPIED = "BERTH_OCCUPIED"
    MAX_LOA = "MAX_LOA"
    MAX_DRAFT = "MAX_DRAFT"
    ENTRY_WINDOW = "ENTRY_WINDOW"
    PILOT_UNAVAILABLE = "PILOT_UNAVAILABLE"
    PILOT_RANK_LIMIT = "PILOT_RANK_LIMIT"
    TUG_UNAVAILABLE = "TUG_UNAVAILABLE"
    TUG_COUNT = "TUG_COUNT"


@dataclass(frozen=True)
class Removal:
    """One reason a candidate is out. `berth_id` None means it applies to the whole request."""

    kind: Kind
    code: str
    detail: str
    berth_id: int | None = None


@dataclass(frozen=True)
class BerthResult:
    berth_id: int
    berth_code: str
    removals: tuple[Removal, ...]  # ordered by code

    @property
    def kept(self) -> bool:
        return not self.removals


@dataclass(frozen=True)
class Candidates:
    """B2's answer for one request before the solve."""

    request_id: int
    request_removals: tuple[Removal, ...]  # reasons that remove every berth
    berths: tuple[BerthResult, ...]  # ordered by berth id

    @property
    def feasible_berth_ids(self) -> tuple[int, ...]:
        if self.request_removals:
            return ()
        return tuple(b.berth_id for b in self.berths if b.kept)

    @property
    def feasible(self) -> bool:
        return bool(self.feasible_berth_ids)


@dataclass(frozen=True)
class BindingConstraint:
    """One CT-10 `binding_constraints` item; `detail` is English, at most 255 characters."""

    kind: Kind
    constraint_type_code: str
    detail: str


@dataclass(frozen=True)
class Option:
    """An emitted option (AI or FIFO): `recommendation_options` plus its tugs.

    The pilot and tugs are checked over the option's own interval (DEC-32 rule 3).
    """

    request_id: int
    berth_id: int
    start: datetime
    end: datetime
    pilot_user_id: int | None
    tug_ids: tuple[int, ...]


@dataclass(frozen=True)
class OptionCheck:
    option: Option
    removals: tuple[Removal, ...]  # ordered by code, one per code

    @property
    def passes(self) -> bool:
        return not self.removals


@dataclass(frozen=True)
class FilterContext:
    """Inputs the AI-050 snapshot doesn't carry (user's choice: explicit inputs).

    - `constraint_types`: the `constraint_types` rows.
    - `vessel_type_ids`: `vessel_types.code` to id, because `safety_constraints` scope by id.
    - `tug_requirements`: AI-054's result per request id.
    """

    constraint_types: tuple[ConstraintType, ...]
    vessel_type_ids: Mapping[str, int]
    tug_requirements: Mapping[int, TugRequirement]
    registry: B2Registry = field(default=DEFAULT_B2_REGISTRY)
