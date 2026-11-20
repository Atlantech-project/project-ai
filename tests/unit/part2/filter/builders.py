"""SYNTHETIC port-state builders for the B2 tests (AI-051).

Every berth, vessel, pilot, tug and limit here is made up. None is a real port value, and no limit
is a proposal for the thresholds register (DEC-30). Codes starting with `SYNTHETIC_` exist only in
these tests; they stand in for Marine Safety Officer codes the seed doesn't have yet (AI-009).
"""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Final

from common.db.read_models import RequestWithVessel, Tugboat
from part1.feasibility import DEFAULT_REGISTRY, Category, CodeRegistry, Comparator, ConstraintType
from part2.filter import B2Registry, FilterContext, Option, VesselAttribute
from part2.state.model import (
    Berth,
    ConfirmedWindow,
    ManifestEntry,
    Pilot,
    PilotRankLimit,
    PortState,
    SafetyConstraint,
    Shift,
    TugMaster,
)
from part2.tugs import FLAG_RULES_UNVALIDATED, TugRequirement

T0: Final = datetime(2026, 1, 5, tzinfo=UTC)
HOUR: Final = timedelta(hours=1)

TERMINAL: Final = 1
OTHER_TERMINAL: Final = 2
REQUEST: Final = 1
OTHER_REQUEST: Final = 2
BERTH: Final = 11
OTHER_BERTH: Final = 12
PILOT: Final = 31
OTHER_PILOT: Final = 32
TUG_A: Final = 41
TUG_B: Final = 42
TUG_C: Final = 43
VESSEL_TYPE_ID: Final = 21


def request(**changes: object) -> RequestWithVessel:
    base = RequestWithVessel(
        request_id=REQUEST,
        status="ENTRY_WINDOW_CONFIRMED",
        requested_terminal_id=TERMINAL,
        requested_eta=T0,
        arrival_draft=Decimal("10.00"),
        block_coefficient=Decimal("0.70"),
        gross_tonnage=30000,
        deadweight_tonnes=40000,
        vessel_id=REQUEST,
        vessel_name="SYNTHETIC VESSEL",
        vessel_type_code="CONTAINER",
        loa=Decimal("200.00"),
        beam=Decimal("30.00"),
        max_draft=Decimal("12.00"),
    )
    return replace(base, **changes)  # type: ignore[arg-type]


def berth(berth_id: int = BERTH, **changes: object) -> Berth:
    base = Berth(
        id=berth_id,
        code=f"B{berth_id}",
        status="ACTIVE",
        length=Decimal("300.00"),
        water_depth=Decimal("14.00"),
        depth_datum="LAT",
        max_vessel_loa=Decimal("250.00"),
        terminal_ids=frozenset({TERMINAL}),
    )
    return replace(base, **changes)  # type: ignore[arg-type]


def window(
    request_id: int = REQUEST, start: datetime = T0, end: datetime = T0 + 6 * HOUR
) -> ConfirmedWindow:
    return ConfirmedWindow(
        berthing_request_id=request_id,
        proposal_id=request_id,
        window_id=request_id,
        start=start,
        end=end,
        confidence=None,
    )


def pilot(
    user_id: int = PILOT, rank: str = "FIRST", is_active: bool = True, role: bool = True
) -> Pilot:
    return Pilot(user_id, f"SYNTHETIC PILOT {user_id}", rank, is_active, role)


RANKS: Final = (
    PilotRankLimit("FIRST", None),
    PilotRankLimit("SECOND", Decimal("250.00")),
    PilotRankLimit("THIRD", Decimal("150.00")),
)


def tug(tug_id: int, status: str = "AVAILABLE") -> Tugboat:
    return Tugboat(tug_id, f"SYNTHETIC TUG {tug_id}", Decimal("50.00"), "TONNES", status)


def master(user_id: int, tug_id: int) -> TugMaster:
    return TugMaster(user_id, f"SYNTHETIC MASTER {user_id}", tug_id, True, True)


def shift(person_id: int) -> Shift:
    return Shift(person_id, person_id, T0 - 24 * HOUR, T0 + 48 * HOUR, True)


def state(**changes: object) -> PortState:
    base = PortState(
        horizon_start=T0 - 24 * HOUR,
        horizon_end=T0 + 7 * 24 * HOUR,
        time_zone="Africa/Cairo",
        requests=(request(),),
        confirmed_windows=(window(),),
        berths=(berth(BERTH), berth(OTHER_BERTH)),
        tugs=(tug(TUG_A), tug(TUG_B), tug(TUG_C)),
        pilots=(pilot(PILOT), pilot(OTHER_PILOT)),
        tug_masters=(master(51, TUG_A), master(52, TUG_B), master(53, TUG_C)),
        pilot_rank_limits=RANKS,
        pilot_shifts=(shift(PILOT), shift(OTHER_PILOT)),
        tug_master_shifts=(shift(51), shift(52), shift(53)),
        confirmed_holds=(),
        pending_holds=(),
        safety_constraints=(),
        manifest_entries=(),
        inconsistencies=(),
    )
    return replace(base, **changes)  # type: ignore[arg-type]


def requirement(
    n_min: int = 2, eligible: tuple[int, ...] = (TUG_A, TUG_B, TUG_C), unvalidated: bool = False
) -> TugRequirement:
    return TugRequirement(
        n_min=n_min,
        n_cap=n_min + 1,
        bp_req=40,
        eligible_tugs=frozenset(eligible),
        flags=(FLAG_RULES_UNVALIDATED,) if unvalidated else (),
    )


# Test-only Marine Safety Officer codes (B2-owned in the test registry).
SYN_MAX_BEAM: Final = ConstraintType(
    7, "SYNTHETIC_MAX_BEAM_M", Category.VESSEL_SAFETY, "METRES", Comparator.MAX_ALLOWED
)
SYN_MIN_DWT: Final = ConstraintType(
    8, "SYNTHETIC_MIN_DWT_T", Category.VESSEL_SAFETY, "TONNES", Comparator.MIN_REQUIRED
)
SYN_UNOWNED: Final = ConstraintType(
    9, "SYNTHETIC_UNOWNED_M", Category.VESSEL_SAFETY, "METRES", Comparator.MAX_ALLOWED
)
WIND: Final = ConstraintType(
    1, "MAX_WIND_KN", Category.ENVIRONMENTAL, "KNOTS", Comparator.MAX_ALLOWED
)
UKC: Final = ConstraintType(3, "MIN_UKC_M", Category.UKC, "METRES", Comparator.MIN_REQUIRED)
TYPES: Final = (WIND, UKC, SYN_MAX_BEAM, SYN_MIN_DWT, SYN_UNOWNED)

TEST_A4_REGISTRY: Final = CodeRegistry(
    a4=DEFAULT_REGISTRY.a4,
    elsewhere={
        **DEFAULT_REGISTRY.elsewhere,
        SYN_MAX_BEAM.code: "AI-051 (B2)",
        SYN_MIN_DWT.code: "AI-051 (B2)",
    },
)
TEST_REGISTRY: Final = B2Registry(
    b2={SYN_MAX_BEAM.code: VesselAttribute.BEAM, SYN_MIN_DWT.code: VesselAttribute.DEADWEIGHT},
    a4=TEST_A4_REGISTRY,
)


def context(**changes: object) -> FilterContext:
    base = FilterContext(
        constraint_types=TYPES,
        vessel_type_ids={"CONTAINER": VESSEL_TYPE_ID},
        tug_requirements={REQUEST: requirement(), OTHER_REQUEST: requirement()},
        registry=TEST_REGISTRY,
    )
    return replace(base, **changes)  # type: ignore[arg-type]


_ids = iter(range(1000, 100000))


def limit(
    ctype: ConstraintType,
    value: str,
    *,
    terminal_id: int | None = None,
    berth_id: int | None = None,
    vessel_type_id: int | None = None,
    imdg_class: str | None = None,
    equipment_category_id: int | None = None,
    active_from: datetime = T0 - 24 * HOUR,
    active_to: datetime | None = None,
) -> SafetyConstraint:
    """A synthetic `safety_constraints` row, as the AI-050 loader returns it."""
    return SafetyConstraint(
        id=next(_ids),
        constraint_type_id=ctype.id,
        terminal_id=terminal_id,
        berth_id=berth_id,
        vessel_type_id=vessel_type_id,
        imdg_class=imdg_class,
        equipment_category_id=equipment_category_id,
        value=Decimal(value),
        active_from=active_from,
        active_to=active_to,
    )


def cargo(imdg_class: str, request_id: int = REQUEST) -> ManifestEntry:
    return ManifestEntry(request_id, next(_ids), "F", 10000, imdg_class, None, None)


def option(**changes: object) -> Option:
    base = Option(
        request_id=REQUEST,
        berth_id=BERTH,
        start=T0 + HOUR,
        end=T0 + 13 * HOUR,
        pilot_user_id=PILOT,
        tug_ids=(TUG_A, TUG_B),
    )
    return replace(base, **changes)  # type: ignore[arg-type]
