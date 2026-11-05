"""What the port-state loader returns: plain frozen values, no database objects (AI-050).

Every datetime is an aware UTC value. Times of day in `port_shifts` are port local time; the loader
turns each scheduled shift into a UTC interval before it reaches these types.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from common.db.read_models import RequestWithVessel, Tugboat


class ResourceKind(StrEnum):
    BERTH = "BERTH"
    PILOT = "PILOT"
    TUG = "TUG"


class Identified(StrEnum):
    """Where a confirmed hold's resource came from (AI-050 Proposed row, rule 1)."""

    COMPONENT = "COMPONENT"  # `assigned_user_id`, or the berth or tug of the row itself
    SELECTED_OPTION = "SELECTED_OPTION"  # the plan's option, because `assigned_user_id` is NULL


@dataclass(frozen=True)
class ConfirmedHold:
    """A RESERVED `plan_components` row of a CONFIRMED plan, for a berth, pilot or tug."""

    kind: ResourceKind
    resource_id: int  # berths.id, the pilot's users.id, or tugboats.id
    start: datetime
    end: datetime
    berthing_request_id: int
    operational_plan_id: int
    plan_component_id: int
    identified: Identified


@dataclass(frozen=True)
class PendingHold:
    """Option 1 of a PENDING_REVIEW or MODIFIED_BY_STAFF recommendation (DEC-32 rule 3(b)).

    Not a RESERVED row: the backlog output list does not name it, DEC-32 requires it.
    """

    kind: ResourceKind
    resource_id: int
    start: datetime
    end: datetime
    berthing_request_id: int
    recommendation_id: int
    recommendation_status: str
    option_id: int
    option_rank: int


@dataclass(frozen=True)
class ConfirmedWindow:
    berthing_request_id: int
    proposal_id: int
    window_id: int
    start: datetime
    end: datetime
    confidence: Decimal | None


@dataclass(frozen=True)
class Berth:
    id: int
    code: str
    status: str
    length: Decimal
    water_depth: Decimal
    depth_datum: str
    max_vessel_loa: Decimal
    terminal_ids: frozenset[int]  # `berth_terminals`


@dataclass(frozen=True)
class Pilot:
    user_id: int
    name: str
    rank: str
    is_active: bool  # users.is_active
    has_active_pilot_role: bool  # a MARINE_PILOT assignment with `active_to` NULL (DEC-36)


@dataclass(frozen=True)
class TugMaster:
    user_id: int
    name: str
    tugboat_id: int | None  # tug_master_profiles.assigned_tugboat_id
    is_active: bool
    has_active_tug_master_role: bool


@dataclass(frozen=True)
class Shift:
    """One scheduled shift of one person, as a UTC interval."""

    person_id: int  # the pilot's or the tug master's users.id
    shift_id: int  # port_shifts.id
    start: datetime
    end: datetime
    shift_is_active: bool  # port_shifts.is_active


@dataclass(frozen=True)
class PilotRankLimit:
    pilot_rank: str
    max_vessel_loa: Decimal | None


@dataclass(frozen=True)
class SafetyConstraint:
    id: int
    constraint_type_id: int
    terminal_id: int | None
    berth_id: int | None
    vessel_type_id: int | None
    imdg_class: str | None
    equipment_category_id: int | None
    value: Decimal
    active_from: datetime
    active_to: datetime | None


@dataclass(frozen=True)
class ManifestEntry:
    berthing_request_id: int
    container_id: int
    full_empty: str | None
    weight_kg: int | None
    imdg_class: str | None
    oog_over_height_cm: int | None
    reefer_set_temperature: Decimal | None


@dataclass(frozen=True)
class Inconsistency:
    """A row the loader did not turn into a hold, with the reason. A safety net, not a rule."""

    code: str
    table: str
    row_id: int
    detail: str


@dataclass(frozen=True)
class PortState:
    horizon_start: datetime
    horizon_end: datetime
    time_zone: str
    requests: tuple[RequestWithVessel, ...]
    confirmed_windows: tuple[ConfirmedWindow, ...]
    berths: tuple[Berth, ...]
    tugs: tuple[Tugboat, ...]
    pilots: tuple[Pilot, ...]
    tug_masters: tuple[TugMaster, ...]
    pilot_rank_limits: tuple[PilotRankLimit, ...]
    pilot_shifts: tuple[Shift, ...]
    tug_master_shifts: tuple[Shift, ...]
    confirmed_holds: tuple[ConfirmedHold, ...]
    pending_holds: tuple[PendingHold, ...]
    safety_constraints: tuple[SafetyConstraint, ...]
    manifest_entries: tuple[ManifestEntry, ...]
    inconsistencies: tuple[Inconsistency, ...]
    # Seconds, per step and "total". Measured, never a pass/fail threshold (AI-050).
    timings: dict[str, float] = field(default_factory=dict)
