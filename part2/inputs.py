"""Reads the PART2_SOLVE handler needs beyond the AI-050 snapshot and the B2 context (AI-059).

- The run's horizon: `solver_runs.horizon_start` / `horizon_end`, set by the Backend (CT-10).
- REPLAN: the entry's `operational_plan_id` must be the request's CONFIRMED plan.
- B3 inputs (AI-052, DEC-28): `port_profiles.port_code`, `terminal_productivity_profiles`, and the
  `port_of_discharge` of each manifest row of the request's ACTIVE, PARSED BAPLIE.

Every function reads in the caller's transaction and leaves ending it to the caller.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import sqlalchemy as sa

from common.db.connection import core_of
from common.db.tables import (
    BAPLIE_FILES,
    CONTAINER_MANIFEST_ENTRIES,
    OPERATIONAL_PLANS,
    PORT_PROFILES,
    SOLVER_RUNS,
    TERMINAL_PRODUCTIVITY_PROFILES,
)
from common.runtime.errors import ErrorCategory, JobError
from common.runtime.runs import Connection
from common.time import to_local
from part2.filter.pairing import confirmed_window
from part2.service_time import (
    ProductivityProfile,
    ServiceTimeResult,
    compute_service_time,
    count_moves,
)
from part2.state.model import PortState


@dataclass(frozen=True)
class ServiceInputs:
    port_code: str | None
    profiles: tuple[ProductivityProfile, ...]
    active_baplie: frozenset[int]  # requests with an ACTIVE, PARSED file
    discharge_ports: Mapping[int, tuple[str | None, ...]] = field(default_factory=dict)


def read_run_horizon(connection: Connection, run_id: int) -> tuple[datetime, datetime]:
    row = (
        core_of(connection)
        .execute(
            sa.select(SOLVER_RUNS.c.horizon_start, SOLVER_RUNS.c.horizon_end).where(
                SOLVER_RUNS.c.id == run_id
            )
        )
        .first()
    )
    if row is None:
        raise JobError(ErrorCategory.PRECONDITION_FAILED, f"no solver_runs row {run_id}")
    start, end = _utc(row.horizon_start), _utc(row.horizon_end)
    if end <= start:  # chk_sr_horizon holds this; a bad row is the sender's, never a retry
        raise JobError(
            ErrorCategory.PRECONDITION_FAILED, f"run {run_id}: horizon ends before it starts"
        )
    return start, end


def check_replan_plans(connection: Connection, plans: Mapping[int, int]) -> None:
    """Each REPLAN entry names its request's CONFIRMED plan (CT-10), or the run fails."""
    for request_id, plan_id in sorted(plans.items()):
        row = (
            core_of(connection)
            .execute(
                sa.select(
                    OPERATIONAL_PLANS.c.berthing_request_id, OPERATIONAL_PLANS.c.status
                ).where(OPERATIONAL_PLANS.c.id == plan_id)
            )
            .first()
        )
        if row is None or row.berthing_request_id != request_id or row.status != "CONFIRMED":
            raise JobError(
                ErrorCategory.PRECONDITION_FAILED,
                f"REPLAN of request {request_id}: operational plan {plan_id} is not its "
                "CONFIRMED plan",
            )


def read_service_inputs(connection: Connection, request_ids: Sequence[int]) -> ServiceInputs:
    core = core_of(connection)
    port_code = core.execute(sa.select(PORT_PROFILES.c.port_code)).scalar()
    t = TERMINAL_PRODUCTIVITY_PROFILES
    profiles = tuple(
        ProductivityProfile(
            id=int(r.id),
            terminal_id=int(r.terminal_id),
            vessel_type_id=None if r.vessel_type_id is None else int(r.vessel_type_id),
            productivity_rate=Decimal(r.productivity_rate),
            rate_unit=str(r.rate_unit),
            fixed_overhead_minutes=int(r.fixed_overhead_minutes),
            valid_from=r.valid_from,
            valid_to=r.valid_to,
        )
        for r in core.execute(
            sa.select(
                t.c.id,
                t.c.terminal_id,
                t.c.vessel_type_id,
                t.c.productivity_rate,
                t.c.rate_unit,
                t.c.fixed_overhead_minutes,
                t.c.valid_from,
                t.c.valid_to,
            ).order_by(t.c.id)
        )
    )
    if not request_ids:
        return ServiceInputs(port_code, profiles, frozenset())
    b, me = BAPLIE_FILES, CONTAINER_MANIFEST_ENTRIES
    active_files = {
        int(r.id): int(r.berthing_request_id)
        for r in core.execute(
            sa.select(b.c.id, b.c.berthing_request_id).where(
                b.c.berthing_request_id.in_(list(request_ids)),
                b.c.status == "ACTIVE",
                b.c.parse_status == "PARSED",
            )
        )
    }
    ports: dict[int, list[str | None]] = {r: [] for r in active_files.values()}
    if active_files:
        for r in core.execute(
            sa.select(me.c.baplie_file_id, me.c.port_of_discharge).where(
                me.c.baplie_file_id.in_(list(active_files))
            )
        ):
            ports[active_files[int(r.baplie_file_id)]].append(r.port_of_discharge)
    return ServiceInputs(
        port_code,
        profiles,
        frozenset(active_files.values()),
        {request: tuple(values) for request, values in ports.items()},
    )


def service_times(
    state: PortState, inputs: ServiceInputs, vessel_type_ids: Mapping[str, int]
) -> dict[int, ServiceTimeResult]:
    """B3 per request of the snapshot, at its requested terminal (AI-052).

    `on_date` is the port-local date of the confirmed window's start (AI-052 ruling 1). A request
    without a confirmed window gets no result here: B2 removes it with `ENTRY_WINDOW`.
    """
    results: dict[int, ServiceTimeResult] = {}
    for request in state.requests:
        window = confirmed_window(state, request.request_id)
        if window is None:
            continue
        type_id = vessel_type_ids.get(request.vessel_type_code)
        if type_id is None:
            raise JobError(
                ErrorCategory.DATA_UNAVAILABLE,
                f"vessel type {request.vessel_type_code} of request {request.request_id} "
                "has no vessel_types row",
            )
        moves = count_moves(
            has_active_baplie=request.request_id in inputs.active_baplie,
            discharge_ports=inputs.discharge_ports.get(request.request_id, ()),
            port_code=inputs.port_code,
            loading_count=request.loading_container_count,
        )
        results[request.request_id] = compute_service_time(
            vessel_type_code=request.vessel_type_code,
            vessel_type_id=type_id,
            terminal_id=request.requested_terminal_id,
            moves=moves,
            profiles=inputs.profiles,
            on_date=to_local(window.start, state.time_zone).date(),
        )
    return results


def as_duration(hours: Decimal) -> timedelta:
    """B3 hours (2 decimals, so whole seconds) as a duration for the solve."""
    return timedelta(seconds=int(hours * 3600))


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.utcoffset() is None else value.astimezone(UTC)
