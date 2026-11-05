"""The Part 2 port-state loader: one consistent view of the live port for one solve (AI-050).

Everything is read from the primary in a single REPEATABLE READ transaction (DEC-08, OD-21), so a
plan confirmed while the load runs is either seen in every table or in none. The loader ends its
transaction before it returns; it takes a connection with none open.

What it returns follows the DEC-32 rule and the AI-050 Proposed row:

- confirmed holds: RESERVED `plan_components` rows of CONFIRMED plans, for berths, pilots and tugs;
- pending holds: option 1 of PENDING_REVIEW and MODIFIED_BY_STAFF recommendations;
- every hold carries its `berthing_request_id`, so the solver can drop the holds of the requests in
  its run (`availability.without_requests`). The loader drops none itself.

It returns every row that overlaps `[horizon_start, horizon_end)`, not only rows inside it.
"""

import logging
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from typing import Any

import sqlalchemy as sa

from common.db.connection import core_of
from common.db.read_models import _is_known, read_request_with_vessel, read_tugboats
from common.db.tables import (
    BAPLIE_FILES,
    BERTH_TERMINALS,
    BERTHS,
    CONTAINER_MANIFEST_ENTRIES,
    ENTRY_WINDOW_PROPOSALS,
    FEASIBLE_WINDOWS,
    OPERATIONAL_PLANS,
    PILOT_PROFILES,
    PILOT_RANK_LIMITS,
    PILOT_SCHEDULES,
    PLAN_COMPONENTS,
    PORT_PROFILES,
    PORT_SHIFTS,
    RECOMMENDATION_OPTION_TUGS,
    RECOMMENDATION_OPTIONS,
    RECOMMENDATIONS,
    SAFETY_CONSTRAINTS,
    TUG_MASTER_PROFILES,
    TUG_MASTER_SCHEDULES,
    USER_ROLE_ASSIGNMENTS,
    USERS,
)
from common.runtime.logs import log_event
from common.runtime.runs import Connection
from common.time import LocalTimeError, shift_interval_utc, to_local
from part2.state.model import (
    Berth,
    ConfirmedHold,
    ConfirmedWindow,
    Identified,
    Inconsistency,
    ManifestEntry,
    PendingHold,
    Pilot,
    PilotRankLimit,
    PortState,
    ResourceKind,
    SafetyConstraint,
    Shift,
    TugMaster,
)

# The recommendation statuses whose option 1 holds resources (DEC-32 rule 3(b)).
PENDING_STATUSES = ("PENDING_REVIEW", "MODIFIED_BY_STAFF")
_COMPONENT_KINDS = ("BERTH", "PILOT", "TUG")


class PortStateError(RuntimeError):
    """The state can't be loaded: a bad argument, an open transaction, or no port profile."""


def load_port_state(
    connection: Connection,
    request_ids: Sequence[int],
    *,
    horizon_start: datetime,
    horizon_end: datetime,
) -> PortState:
    """Read the live port state for the given requests and the horizon, as one snapshot.

    `horizon_start` and `horizon_end` are required and aware: the caller sets them (AI-050).
    """
    for name, value in (("horizon_start", horizon_start), ("horizon_end", horizon_end)):
        if value.utcoffset() is None:
            raise PortStateError(f"{name} must be an aware datetime, got {value.isoformat()}")
    start = horizon_start.astimezone(UTC)
    end = horizon_end.astimezone(UTC)
    if end <= start:
        raise PortStateError(f"the horizon must end after it starts: {start} to {end}")
    core = core_of(connection)
    if core.in_transaction():
        raise PortStateError("load_port_state needs a connection with no open transaction")

    timings: dict[str, float] = {}
    began = time.perf_counter()
    # The setting applies to the next transaction only; the snapshot is taken at its start.
    core.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
    core.exec_driver_sql("START TRANSACTION WITH CONSISTENT SNAPSHOT")
    try:
        state = _read_all(connection, request_ids, start, end, timings)
    finally:
        core.rollback()  # read-only: nothing to keep, and the next read gets a fresh snapshot
    timings["total"] = time.perf_counter() - began
    state.timings.update(timings)
    log_event(
        logging.INFO,
        "port_state_loaded",
        {
            "requests": len(state.requests),
            "confirmed_holds": len(state.confirmed_holds),
            "pending_holds": len(state.pending_holds),
            "inconsistencies": len(state.inconsistencies),
            "seconds": round(timings["total"], 4),
        },
    )
    return state


@contextmanager
def _timed(timings: dict[str, float], step: str) -> Iterator[None]:
    began = time.perf_counter()
    try:
        yield
    finally:
        timings[step] = time.perf_counter() - began


def _utc(value: datetime) -> datetime:
    """The database returns UTC datetimes without an offset (CT-17 §2)."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _utc_or_none(value: datetime | None) -> datetime | None:
    return None if value is None else _utc(value)


def _rows(
    connection: Connection, statement: sa.Select[Any], columns: Sequence[sa.Column[Any]]
) -> list[sa.RowMapping]:
    result = core_of(connection).execute(statement).mappings()
    return [row for row in result if _is_known(row, columns)]


def _read_all(
    connection: Connection,
    request_ids: Sequence[int],
    horizon_start: datetime,
    horizon_end: datetime,
    timings: dict[str, float],
) -> PortState:
    inconsistencies: list[Inconsistency] = []
    with _timed(timings, "port_profile"):
        time_zone = _read_time_zone(connection)
    with _timed(timings, "requests"):
        requests = tuple(
            request
            for request_id in dict.fromkeys(request_ids)
            if (request := read_request_with_vessel(connection, request_id)) is not None
        )
        in_scope = [request.request_id for request in requests]
    with _timed(timings, "confirmed_windows"):
        windows = _read_confirmed_windows(connection, in_scope)
    with _timed(timings, "berths"):
        berths = _read_berths(connection)
    with _timed(timings, "tugs"):
        tugs = tuple(read_tugboats(connection))
    with _timed(timings, "people"):
        pilots = _read_pilots(connection)
        tug_masters = _read_tug_masters(connection)
        rank_limits = _read_rank_limits(connection)
    with _timed(timings, "shifts"):
        pilot_shifts = _read_shifts(
            connection, PILOT_SCHEDULES, "pilot_user_id", time_zone, horizon_start, horizon_end,
            inconsistencies,
        )  # fmt: skip
        master_shifts = _read_shifts(
            connection, TUG_MASTER_SCHEDULES, "tug_master_user_id", time_zone, horizon_start,
            horizon_end, inconsistencies,
        )  # fmt: skip
    with _timed(timings, "confirmed_holds"):
        confirmed = _read_confirmed_holds(connection, horizon_start, horizon_end, inconsistencies)
    with _timed(timings, "pending_holds"):
        pending = _read_pending_holds(connection, horizon_start, horizon_end)
    with _timed(timings, "safety_constraints"):
        constraints = _read_safety_constraints(connection, horizon_start, horizon_end)
    with _timed(timings, "manifests"):
        manifests = _read_manifests(connection, in_scope)
    return PortState(
        horizon_start=horizon_start,
        horizon_end=horizon_end,
        time_zone=time_zone,
        requests=requests,
        confirmed_windows=windows,
        berths=berths,
        tugs=tugs,
        pilots=pilots,
        tug_masters=tug_masters,
        pilot_rank_limits=rank_limits,
        pilot_shifts=pilot_shifts,
        tug_master_shifts=master_shifts,
        confirmed_holds=confirmed,
        pending_holds=pending,
        safety_constraints=constraints,
        manifest_entries=manifests,
        inconsistencies=tuple(inconsistencies),
    )


def _read_time_zone(connection: Connection) -> str:
    row = core_of(connection).execute(sa.select(PORT_PROFILES.c.timezone).limit(1)).first()
    if row is None:
        raise PortStateError("there is no port profile, so shift times have no time zone")
    return str(row[0])


def _read_confirmed_windows(
    connection: Connection, request_ids: Sequence[int]
) -> tuple[ConfirmedWindow, ...]:
    if not request_ids:
        return ()
    columns = (
        ENTRY_WINDOW_PROPOSALS.c.berthing_request_id,
        ENTRY_WINDOW_PROPOSALS.c.id,
        FEASIBLE_WINDOWS.c.id,
        FEASIBLE_WINDOWS.c.window_start,
        FEASIBLE_WINDOWS.c.window_end,
        FEASIBLE_WINDOWS.c.confidence,
    )
    statement = (
        sa.select(*columns)
        .select_from(
            ENTRY_WINDOW_PROPOSALS.join(
                FEASIBLE_WINDOWS,
                FEASIBLE_WINDOWS.c.id == ENTRY_WINDOW_PROPOSALS.c.confirmed_window_id,
            )
        )
        .where(
            ENTRY_WINDOW_PROPOSALS.c.status == "CONFIRMED",
            ENTRY_WINDOW_PROPOSALS.c.berthing_request_id.in_(request_ids),
        )
        .order_by(ENTRY_WINDOW_PROPOSALS.c.berthing_request_id)
    )
    return tuple(
        ConfirmedWindow(
            berthing_request_id=row[columns[0]],
            proposal_id=row[columns[1]],
            window_id=row[columns[2]],
            start=_utc(row[columns[3]]),
            end=_utc(row[columns[4]]),
            confidence=row[columns[5]],
        )
        for row in _rows(connection, statement, columns)
    )


def _read_berths(connection: Connection) -> tuple[Berth, ...]:
    terminals: dict[int, set[int]] = {}
    pairs = core_of(connection).execute(
        sa.select(BERTH_TERMINALS.c.berth_id, BERTH_TERMINALS.c.terminal_id)
    )
    for berth_id, terminal_id in pairs:
        terminals.setdefault(berth_id, set()).add(terminal_id)
    columns = (
        BERTHS.c.id,
        BERTHS.c.code,
        BERTHS.c.status,
        BERTHS.c.length,
        BERTHS.c.water_depth,
        BERTHS.c.depth_datum,
        BERTHS.c.max_vessel_loa,
    )
    return tuple(
        Berth(
            id=row[BERTHS.c.id],
            code=row[BERTHS.c.code],
            status=row[BERTHS.c.status],
            length=row[BERTHS.c.length],
            water_depth=row[BERTHS.c.water_depth],
            depth_datum=row[BERTHS.c.depth_datum],
            max_vessel_loa=row[BERTHS.c.max_vessel_loa],
            terminal_ids=frozenset(terminals.get(row[BERTHS.c.id], ())),
        )
        for row in _rows(connection, sa.select(*columns).order_by(BERTHS.c.id), columns)
    )


def _users_with_active_role(connection: Connection, role: str) -> set[int]:
    """Users whose assignment of the role has no end (`active_to` NULL; DEC-36)."""
    statement = sa.select(USER_ROLE_ASSIGNMENTS.c.user_id).where(
        USER_ROLE_ASSIGNMENTS.c.role == role, USER_ROLE_ASSIGNMENTS.c.active_to.is_(None)
    )
    return {row[0] for row in core_of(connection).execute(statement)}


def _read_pilots(connection: Connection) -> tuple[Pilot, ...]:
    with_role = _users_with_active_role(connection, "MARINE_PILOT")
    columns = (USERS.c.id, USERS.c.name, USERS.c.is_active, PILOT_PROFILES.c.pilot_rank)
    statement = (
        sa.select(*columns)
        .select_from(PILOT_PROFILES.join(USERS, USERS.c.id == PILOT_PROFILES.c.user_id))
        .order_by(USERS.c.id)
    )
    return tuple(
        Pilot(
            user_id=row[USERS.c.id],
            name=row[USERS.c.name],
            rank=row[PILOT_PROFILES.c.pilot_rank],
            is_active=bool(row[USERS.c.is_active]),
            has_active_pilot_role=row[USERS.c.id] in with_role,
        )
        for row in _rows(connection, statement, columns)
    )


def _read_tug_masters(connection: Connection) -> tuple[TugMaster, ...]:
    with_role = _users_with_active_role(connection, "TUG_MASTER")
    columns = (
        USERS.c.id,
        USERS.c.name,
        USERS.c.is_active,
        TUG_MASTER_PROFILES.c.assigned_tugboat_id,
    )
    statement = (
        sa.select(*columns)
        .select_from(TUG_MASTER_PROFILES.join(USERS, USERS.c.id == TUG_MASTER_PROFILES.c.user_id))
        .order_by(USERS.c.id)
    )
    return tuple(
        TugMaster(
            user_id=row[USERS.c.id],
            name=row[USERS.c.name],
            tugboat_id=row[TUG_MASTER_PROFILES.c.assigned_tugboat_id],
            is_active=bool(row[USERS.c.is_active]),
            has_active_tug_master_role=row[USERS.c.id] in with_role,
        )
        for row in _rows(connection, statement, columns)
    )


def _read_rank_limits(connection: Connection) -> tuple[PilotRankLimit, ...]:
    columns = (PILOT_RANK_LIMITS.c.pilot_rank, PILOT_RANK_LIMITS.c.max_vessel_loa)
    statement = sa.select(*columns).order_by(PILOT_RANK_LIMITS.c.pilot_rank)
    return tuple(
        PilotRankLimit(*(row[c] for c in columns)) for row in _rows(connection, statement, columns)
    )


def _read_shifts(
    connection: Connection,
    schedule: sa.Table,
    person_column: str,
    time_zone: str,
    horizon_start: datetime,
    horizon_end: datetime,
    inconsistencies: list[Inconsistency],
) -> tuple[Shift, ...]:
    """Scheduled shifts that overlap the horizon, as UTC intervals.

    A shift is dated by the local day it starts on and may end the next day, so the dates read
    start one day before the horizon's first local date.
    """
    first: date = to_local(horizon_start, time_zone).date() - timedelta(days=1)
    last: date = to_local(horizon_end, time_zone).date()
    columns = (
        schedule.c.id,
        schedule.c[person_column],
        schedule.c.shift_date,
        PORT_SHIFTS.c.id,
        PORT_SHIFTS.c.start_time,
        PORT_SHIFTS.c.end_time,
        PORT_SHIFTS.c.is_active,
    )
    statement = (
        sa.select(*columns)
        .select_from(schedule.join(PORT_SHIFTS, PORT_SHIFTS.c.id == schedule.c.port_shift_id))
        .where(schedule.c.shift_date.between(first, last))
        .order_by(schedule.c.shift_date, schedule.c.id)
    )
    shifts: list[Shift] = []
    for row in _rows(connection, statement, columns):
        try:
            begins, ends = shift_interval_utc(
                row[schedule.c.shift_date],
                _as_time(row[PORT_SHIFTS.c.start_time]),
                _as_time(row[PORT_SHIFTS.c.end_time]),
                time_zone,
            )
        except LocalTimeError as error:
            # Local time that doesn't exist or repeats: no safe UTC interval, so none is offered.
            inconsistencies.append(
                Inconsistency(
                    "shift_time_unresolvable", schedule.name, row[schedule.c.id], str(error)
                )
            )
            continue
        if begins < horizon_end and horizon_start < ends:
            shifts.append(
                Shift(
                    person_id=row[schedule.c[person_column]],
                    shift_id=row[PORT_SHIFTS.c.id],
                    start=begins,
                    end=ends,
                    shift_is_active=bool(row[PORT_SHIFTS.c.is_active]),
                )
            )
    return tuple(shifts)


def _as_time(value: Any) -> Any:
    """PyMySQL returns a MySQL TIME as a `timedelta`; the shift helper wants a `time`."""
    if isinstance(value, timedelta):
        return (datetime.min + value).time()
    return value


def _read_confirmed_holds(
    connection: Connection,
    horizon_start: datetime,
    horizon_end: datetime,
    inconsistencies: list[Inconsistency],
) -> tuple[ConfirmedHold, ...]:
    pc = PLAN_COMPONENTS
    columns = (
        pc.c.id,
        pc.c.operational_plan_id,
        pc.c.component_type,
        pc.c.berth_id,
        pc.c.tugboat_id,
        pc.c.assigned_user_id,
        pc.c.planned_start,
        pc.c.planned_end,
        pc.c.reservation_state,
        OPERATIONAL_PLANS.c.berthing_request_id,
        OPERATIONAL_PLANS.c.status,
        RECOMMENDATION_OPTIONS.c.pilot_user_id,
    )
    statement = (
        sa.select(*columns)
        .select_from(
            pc.join(
                OPERATIONAL_PLANS, OPERATIONAL_PLANS.c.id == pc.c.operational_plan_id
            ).outerjoin(
                RECOMMENDATION_OPTIONS,
                RECOMMENDATION_OPTIONS.c.id == OPERATIONAL_PLANS.c.recommendation_option_id,
            )
        )
        .where(
            pc.c.reservation_state == "RESERVED",
            pc.c.component_type.in_(_COMPONENT_KINDS),
            pc.c.planned_start < horizon_end,
            pc.c.planned_end > horizon_start,
        )
        .order_by(pc.c.id)
    )
    holds: list[ConfirmedHold] = []
    for row in _rows(connection, statement, columns):
        component_id = row[pc.c.id]
        if row[OPERATIONAL_PLANS.c.status] != "CONFIRMED":
            inconsistencies.append(
                Inconsistency(
                    "reserved_under_unconfirmed_plan",
                    "plan_components",
                    component_id,
                    f"plan {row[pc.c.operational_plan_id]} is {row[OPERATIONAL_PLANS.c.status]}",
                )
            )
            continue
        kind = ResourceKind(row[pc.c.component_type])
        identified = Identified.COMPONENT
        if kind is ResourceKind.BERTH:
            resource_id = row[pc.c.berth_id]
        elif kind is ResourceKind.TUG:
            resource_id = row[pc.c.tugboat_id]
        else:
            # `assigned_user_id` wins: a replacement (P5-M1) may have changed it. Before dispatch it
            # is NULL, and the pilot is the one the plan's selected option names.
            resource_id = row[pc.c.assigned_user_id]
            if resource_id is None:
                resource_id = row[RECOMMENDATION_OPTIONS.c.pilot_user_id]
                identified = Identified.SELECTED_OPTION
        if resource_id is None:
            inconsistencies.append(
                Inconsistency(
                    "hold_resource_unidentified",
                    "plan_components",
                    component_id,
                    f"{kind} row of plan {row[pc.c.operational_plan_id]} names no resource",
                )
            )
            continue
        holds.append(
            ConfirmedHold(
                kind=kind,
                resource_id=resource_id,
                start=_utc(row[pc.c.planned_start]),
                end=_utc(row[pc.c.planned_end]),
                berthing_request_id=row[OPERATIONAL_PLANS.c.berthing_request_id],
                operational_plan_id=row[pc.c.operational_plan_id],
                plan_component_id=component_id,
                identified=identified,
            )
        )
    return tuple(holds)


def _read_pending_holds(
    connection: Connection, horizon_start: datetime, horizon_end: datetime
) -> tuple[PendingHold, ...]:
    ro = RECOMMENDATION_OPTIONS
    columns = (
        RECOMMENDATIONS.c.id,
        RECOMMENDATIONS.c.berthing_request_id,
        RECOMMENDATIONS.c.status,
        ro.c.id,
        ro.c.option_rank,
        ro.c.berth_id,
        ro.c.pilot_user_id,
        ro.c.planned_start,
        ro.c.planned_end,
    )
    statement = (
        sa.select(*columns)
        .select_from(RECOMMENDATIONS.join(ro, ro.c.recommendation_id == RECOMMENDATIONS.c.id))
        .where(
            RECOMMENDATIONS.c.status.in_(PENDING_STATUSES),
            ro.c.option_rank == 1,
            ro.c.planned_start < horizon_end,
            ro.c.planned_end > horizon_start,
        )
        .order_by(ro.c.id)
    )
    options = _rows(connection, statement, columns)
    tugs_by_option: dict[int, list[int]] = {}
    if options:
        option_ids = [row[ro.c.id] for row in options]
        tug_rows = core_of(connection).execute(
            sa.select(
                RECOMMENDATION_OPTION_TUGS.c.option_id, RECOMMENDATION_OPTION_TUGS.c.tugboat_id
            )
            .where(RECOMMENDATION_OPTION_TUGS.c.option_id.in_(option_ids))
            .order_by(
                RECOMMENDATION_OPTION_TUGS.c.option_id, RECOMMENDATION_OPTION_TUGS.c.tugboat_id
            )
        )
        for option_id, tugboat_id in tug_rows:
            tugs_by_option.setdefault(option_id, []).append(tugboat_id)
    holds: list[PendingHold] = []
    for row in options:
        option_id = row[ro.c.id]
        resources = [(ResourceKind.BERTH, row[ro.c.berth_id])]
        if row[ro.c.pilot_user_id] is not None:
            resources.append((ResourceKind.PILOT, row[ro.c.pilot_user_id]))
        resources.extend((ResourceKind.TUG, tug_id) for tug_id in tugs_by_option.get(option_id, []))
        holds.extend(
            PendingHold(
                kind=kind,
                resource_id=resource_id,
                start=_utc(row[ro.c.planned_start]),
                end=_utc(row[ro.c.planned_end]),
                berthing_request_id=row[RECOMMENDATIONS.c.berthing_request_id],
                recommendation_id=row[RECOMMENDATIONS.c.id],
                recommendation_status=row[RECOMMENDATIONS.c.status],
                option_id=option_id,
                option_rank=row[ro.c.option_rank],
            )
            for kind, resource_id in resources
        )
    return tuple(holds)


def _read_safety_constraints(
    connection: Connection, horizon_start: datetime, horizon_end: datetime
) -> tuple[SafetyConstraint, ...]:
    sc = SAFETY_CONSTRAINTS
    columns = (
        sc.c.id,
        sc.c.constraint_type_id,
        sc.c.terminal_id,
        sc.c.berth_id,
        sc.c.vessel_type_id,
        sc.c.imdg_class,
        sc.c.equipment_category_id,
        sc.c.value,
        sc.c.active_from,
        sc.c.active_to,
    )
    statement = (
        sa.select(*columns)
        .where(
            sc.c.active_from < horizon_end,
            sa.or_(sc.c.active_to.is_(None), sc.c.active_to > horizon_start),
        )
        .order_by(sc.c.id)
    )
    return tuple(
        SafetyConstraint(
            id=row[sc.c.id],
            constraint_type_id=row[sc.c.constraint_type_id],
            terminal_id=row[sc.c.terminal_id],
            berth_id=row[sc.c.berth_id],
            vessel_type_id=row[sc.c.vessel_type_id],
            imdg_class=row[sc.c.imdg_class],
            equipment_category_id=row[sc.c.equipment_category_id],
            value=row[sc.c.value],
            active_from=_utc(row[sc.c.active_from]),
            active_to=_utc_or_none(row[sc.c.active_to]),
        )
        for row in _rows(connection, statement, columns)
    )


def _read_manifests(
    connection: Connection, request_ids: Sequence[int]
) -> tuple[ManifestEntry, ...]:
    """Entries of each request's ACTIVE, PARSED BAPLIE file (one active file per request)."""
    if not request_ids:
        return ()
    me = CONTAINER_MANIFEST_ENTRIES
    columns = (
        BAPLIE_FILES.c.berthing_request_id,
        me.c.container_id,
        me.c.full_empty,
        me.c.weight_kg,
        me.c.imdg_class,
        me.c.oog_over_height_cm,
        me.c.reefer_set_temperature,
    )
    statement = (
        sa.select(*columns)
        .select_from(me.join(BAPLIE_FILES, BAPLIE_FILES.c.id == me.c.baplie_file_id))
        .where(
            BAPLIE_FILES.c.berthing_request_id.in_(request_ids),
            BAPLIE_FILES.c.status == "ACTIVE",
            BAPLIE_FILES.c.parse_status == "PARSED",
        )
        .order_by(BAPLIE_FILES.c.berthing_request_id, me.c.id)
    )
    return tuple(
        ManifestEntry(*(row[column] for column in columns))
        for row in _rows(connection, statement, columns)
    )
