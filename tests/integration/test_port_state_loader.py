"""The Part 2 port-state loader on the real schema, as the real `w_part2` account (AI-050).

Rows are seeded the way the Backend would write them (foreign key checks off, committed), so each
test states only the columns it cares about. Every test starts and ends with the touched tables
empty, because the port database is shared with the other integration tests.
"""

from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Final

import pymysql
import pytest

from common.config import WorkerPart, load_env_settings
from common.db.connection import WorkerConnection, connect_worker, core_of, dispose_engines
from part2.state import snapshot
from part2.state.availability import (
    is_berth_available,
    is_pilot_available,
    is_tug_available,
    without_requests,
)
from part2.state.model import Identified, PortState, ResourceKind
from part2.state.snapshot import PortStateError, load_port_state
from tests.support.port_db import PortDatabase, seed_row
from tests.support.scenarios import LOAD_ORDER, load_scenario, read_scenario

pytestmark = pytest.mark.integration

H0: Final = datetime(2026, 11, 10, 8, 0, tzinfo=UTC)
H1: Final = H0 + timedelta(hours=12)
TERMINAL: Final = 7
# Passes chk_br_cb and chk_br_source, which the generic placeholders do not.
REQUEST_COLUMNS: Final = {
    "requested_terminal_id": TERMINAL,
    "block_coefficient": 0.7,
    "source": "MANUAL",
    "submitted_by": 1,
}
REFERENCE: Final = (
    Path(__file__).resolve().parents[1] / "fixtures" / "SYNTHETIC_reference_seed1.json"
)

TOUCHED_TABLES: Final = (
    "baplie_files",
    "berth_terminals",
    "berths",
    "berthing_requests",
    "container_manifest_entries",
    "entry_window_proposals",
    "feasible_windows",
    "operational_plans",
    "pilot_profiles",
    "pilot_rank_limits",
    "pilot_schedules",
    "plan_components",
    "port_profiles",
    "port_shifts",
    "recommendation_option_tugs",
    "recommendation_options",
    "recommendations",
    "safety_constraints",
    "tug_master_profiles",
    "tug_master_schedules",
    "tugboats",
    "user_role_assignments",
    "users",
    "vessel_types",
    "vessels",
)


def _sql(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")


def _empty(database: PortDatabase, tables: tuple[str, ...] = TOUCHED_TABLES) -> None:
    """DELETE is much quicker than TRUNCATE on the tables a test leaves empty."""
    conn = database.root()  # its session starts with foreign key checks off
    try:
        with conn.cursor() as cursor:
            for table in tables:
                cursor.execute(f"DELETE FROM `{table}`")  # noqa: S608
        conn.commit()
    finally:
        conn.close()


def _empty_scenario(database: PortDatabase) -> None:
    conn = database.root()
    try:
        with conn.cursor() as cursor:
            for table in reversed(LOAD_ORDER):
                cursor.execute(f"TRUNCATE TABLE `{table}`")  # noqa: S608
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def root(port_db: PortDatabase) -> Iterator[pymysql.connections.Connection[Any]]:
    _empty(port_db)
    conn = port_db.root()
    try:
        yield conn
    finally:
        conn.close()
        dispose_engines()
        _empty(port_db)


@pytest.fixture
def scenario_tables(port_db: PortDatabase) -> Iterator[None]:
    """The scenario tables empty before the test and after it."""
    _empty_scenario(port_db)
    try:
        yield
    finally:
        _empty_scenario(port_db)


@pytest.fixture
def worker(
    port_db: PortDatabase, root: pymysql.connections.Connection[Any]
) -> Iterator[WorkerConnection]:
    connection = connect_worker(
        load_env_settings(port_db.worker_env(WorkerPart.PART2), WorkerPart.PART2)
    )
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


class World:
    """Seeds the rows a test needs, one call each, and keeps the ids apart."""

    def __init__(self, root: pymysql.connections.Connection[Any]) -> None:
        self.root = root
        self._names = 0
        seed_row(root, "port_profiles", id=1, timezone="Africa/Cairo")

    def _next(self) -> int:
        self._names += 1
        return self._names

    def user(self, *, active: bool = True) -> int:
        n = self._next()
        return seed_row(
            self.root, "users", username=f"user{n:03d}", name=f"User {n}", is_active=active
        )

    def role(self, user_id: int, role: str, *, ended: bool = False) -> None:
        seed_row(
            self.root,
            "user_role_assignments",
            user_id=user_id,
            role=role,
            unit_type="MARINE_SERVICES",
            active_from="2026-01-01 00:00:00",
            active_to="2026-06-01 00:00:00" if ended else None,
        )

    def pilot(self, *, active: bool = True, role_ended: bool = False) -> int:
        user_id = self.user(active=active)
        self.role(user_id, "MARINE_PILOT", ended=role_ended)
        seed_row(self.root, "pilot_profiles", user_id=user_id, pilot_rank="FIRST")
        return user_id

    def tug(self, status: str = "AVAILABLE", *, master: bool = True) -> int:
        tug_id = seed_row(
            self.root,
            "tugboats",
            name=f"Tug {self._next()}",
            tug_power=50,
            tug_power_unit="BOLLARD_PULL_TONNES",
            status=status,
        )
        if master:
            user_id = self.user()
            self.role(user_id, "TUG_MASTER")
            seed_row(self.root, "tug_master_profiles", user_id=user_id, assigned_tugboat_id=tug_id)
        return tug_id

    def master_of(self, tug_id: int) -> int:
        with self.root.cursor() as cursor:
            cursor.execute(
                "SELECT user_id FROM tug_master_profiles WHERE assigned_tugboat_id = %s", (tug_id,)
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    def shift(self, start: str = "06:00:00", end: str = "18:00:00", *, active: bool = True) -> int:
        return seed_row(
            self.root,
            "port_shifts",
            code=f"S{self._next()}",
            name="Shift",
            start_time=start,
            end_time=end,
            is_active=active,
        )

    def schedule_pilot(self, pilot_id: int, shift_id: int, day: str = "2026-11-10") -> None:
        seed_row(
            self.root,
            "pilot_schedules",
            pilot_user_id=pilot_id,
            shift_date=day,
            port_shift_id=shift_id,
        )

    def schedule_master(self, master_id: int, shift_id: int, day: str = "2026-11-10") -> None:
        seed_row(
            self.root,
            "tug_master_schedules",
            tug_master_user_id=master_id,
            shift_date=day,
            port_shift_id=shift_id,
        )

    def berth(self, status: str = "ACTIVE") -> int:
        berth_id = seed_row(
            self.root,
            "berths",
            code=f"B{self._next()}",
            length=300,
            water_depth=15,
            depth_datum="LAT",
            max_vessel_loa=280,
            status=status,
        )
        seed_row(self.root, "berth_terminals", berth_id=berth_id, terminal_id=TERMINAL)
        return berth_id

    def request(self) -> int:
        return seed_row(self.root, "berthing_requests", **REQUEST_COLUMNS)

    def plan(self, request_id: int, status: str = "CONFIRMED", *, option_id: int = 0) -> int:
        return seed_row(
            self.root,
            "operational_plans",
            berthing_request_id=request_id,
            recommendation_id=1,
            recommendation_option_id=option_id,
            status=status,
        )

    def component(
        self,
        plan_id: int,
        component_type: str,
        start: datetime,
        end: datetime,
        *,
        resource_id: int | None = None,
        state: str = "RESERVED",
        assigned_user_id: int | None = None,
    ) -> int:
        overrides: dict[str, object] = {
            "operational_plan_id": plan_id,
            "component_type": component_type,
            "planned_start": _sql(start),
            "planned_end": _sql(end),
            "reservation_state": state,
            "assigned_user_id": assigned_user_id,
            "assigned_at": None if assigned_user_id is None else "2026-11-09 09:00:00",
            "berth_id": resource_id if component_type == "BERTH" else None,
            "tugboat_id": resource_id if component_type == "TUG" else None,
            "terminal_id": None,
        }
        return seed_row(self.root, "plan_components", **overrides)

    def recommendation(self, request_id: int, status: str = "PENDING_REVIEW") -> int:
        return seed_row(
            self.root,
            "recommendations",
            berthing_request_id=request_id,
            terminal_id=TERMINAL,
            status=status,
            generated_at="2026-11-09 09:00:00",
        )

    def option(
        self,
        recommendation_id: int,
        rank: int,
        berth_id: int,
        start: datetime,
        end: datetime,
        *,
        pilot_id: int | None = None,
        tug_ids: tuple[int, ...] = (),
    ) -> int:
        option_id = seed_row(
            self.root,
            "recommendation_options",
            recommendation_id=recommendation_id,
            terminal_id=TERMINAL,
            option_rank=rank,
            berth_id=berth_id,
            planned_start=_sql(start),
            planned_end=_sql(end),
            pilot_user_id=pilot_id,
        )
        for tug_id in tug_ids:
            seed_row(
                self.root, "recommendation_option_tugs", option_id=option_id, tugboat_id=tug_id
            )
        return option_id


@pytest.fixture
def world(root: pymysql.connections.Connection[Any]) -> World:
    return World(root)


def _load(
    worker: WorkerConnection, *request_ids: int, start: datetime = H0, end: datetime = H1
) -> PortState:
    return load_port_state(worker, request_ids, horizon_start=start, horizon_end=end)


# Occupancy: RESERVED rows overlapping the horizon (criterion 1)


def test_reserved_components_of_a_confirmed_plan_become_confirmed_holds(
    world: World, worker: WorkerConnection
) -> None:
    berth, tug, pilot = world.berth(), world.tug(), world.pilot()
    request = world.request()
    plan = world.plan(request)
    start, end = H0 + timedelta(hours=1), H0 + timedelta(hours=5)
    berth_row = world.component(plan, "BERTH", start, end, resource_id=berth)
    tug_row = world.component(plan, "TUG", start, end, resource_id=tug)
    pilot_row = world.component(plan, "PILOT", start, end, assigned_user_id=pilot)

    state = _load(worker, request)

    holds = {(hold.kind, hold.resource_id): hold for hold in state.confirmed_holds}
    assert set(holds) == {
        (ResourceKind.BERTH, berth),
        (ResourceKind.TUG, tug),
        (ResourceKind.PILOT, pilot),
    }
    for hold in holds.values():
        assert (hold.start, hold.end) == (start, end)
        assert hold.berthing_request_id == request  # the solver can drop a run's own holds
        assert hold.operational_plan_id == plan
        assert hold.identified is Identified.COMPONENT
    assert {hold.plan_component_id for hold in holds.values()} == {berth_row, tug_row, pilot_row}
    assert state.pending_holds == ()


@pytest.mark.parametrize("reservation_state", ["RELEASED", "CONSUMED"])
def test_released_and_consumed_rows_hold_nothing(
    world: World, worker: WorkerConnection, reservation_state: str
) -> None:
    berth = world.berth()
    plan = world.plan(world.request())
    world.component(
        plan, "BERTH", H0, H0 + timedelta(hours=3), resource_id=berth, state=reservation_state
    )

    assert _load(worker).confirmed_holds == ()


def test_a_reserved_row_under_an_unconfirmed_plan_holds_nothing_and_is_reported(
    world: World, worker: WorkerConnection
) -> None:
    berth = world.berth()
    plan = world.plan(world.request(), status="CANCELLED")
    row = world.component(plan, "BERTH", H0, H0 + timedelta(hours=3), resource_id=berth)

    state = _load(worker)

    assert state.confirmed_holds == ()
    assert [(i.code, i.table, i.row_id) for i in state.inconsistencies] == [
        ("reserved_under_unconfirmed_plan", "plan_components", row)
    ]


def test_terminal_ops_rows_are_not_resource_holds(world: World, worker: WorkerConnection) -> None:
    plan = world.plan(world.request())
    seed_row(
        world.root,
        "plan_components",
        operational_plan_id=plan,
        component_type="TERMINAL_OPS",
        terminal_id=TERMINAL,
        berth_id=None,
        tugboat_id=None,
        planned_start=_sql(H0),
        planned_end=_sql(H0 + timedelta(hours=2)),
    )

    assert _load(worker).confirmed_holds == ()


# Horizon edges: overlap, not containment


@pytest.mark.parametrize(
    ("start_offset", "end_offset", "loaded"),
    [
        (-3, 1, True),  # starts before horizon_start and reaches into it
        (11, 15, True),  # starts inside and ends after horizon_end
        (-5, 20, True),  # contains the whole horizon
        (2, 4, True),  # inside
        (-4, 0, False),  # ends exactly at horizon_start: back to back
        (12, 16, False),  # starts exactly at horizon_end: back to back
        (-9, -2, False),  # entirely before
        (14, 18, False),  # entirely after
    ],
)
def test_holds_are_loaded_when_they_overlap_the_horizon(
    world: World, worker: WorkerConnection, start_offset: int, end_offset: int, loaded: bool
) -> None:
    berth = world.berth()
    plan = world.plan(world.request())
    world.component(
        plan,
        "BERTH",
        H0 + timedelta(hours=start_offset),
        H0 + timedelta(hours=end_offset),
        resource_id=berth,
    )
    option_berth = world.berth()
    recommendation = world.recommendation(world.request())
    world.option(
        recommendation,
        1,
        option_berth,
        H0 + timedelta(hours=start_offset),
        H0 + timedelta(hours=end_offset),
    )

    state = _load(worker)

    assert (len(state.confirmed_holds), len(state.pending_holds)) == ((1, 1) if loaded else (0, 0))


# The pilot of a confirmed plan (Proposed row, rule 1)


def test_assigned_user_wins_over_the_selected_option_pilot(
    world: World, worker: WorkerConnection
) -> None:
    berth, option_pilot, replacement = world.berth(), world.pilot(), world.pilot()
    request = world.request()
    recommendation = world.recommendation(request, "CONFIRMED")
    option = world.option(
        recommendation, 1, berth, H0, H0 + timedelta(hours=4), pilot_id=option_pilot
    )
    plan = world.plan(request, option_id=option)
    world.component(plan, "PILOT", H0, H0 + timedelta(hours=4), assigned_user_id=replacement)

    (hold,) = _load(worker).confirmed_holds

    assert (hold.resource_id, hold.identified) == (replacement, Identified.COMPONENT)


def test_before_dispatch_the_pilot_is_the_selected_options_pilot(
    world: World, worker: WorkerConnection
) -> None:
    berth, option_pilot = world.berth(), world.pilot()
    request = world.request()
    recommendation = world.recommendation(request, "CONFIRMED")
    option = world.option(
        recommendation, 1, berth, H0, H0 + timedelta(hours=4), pilot_id=option_pilot
    )
    plan = world.plan(request, option_id=option)
    world.component(plan, "PILOT", H0, H0 + timedelta(hours=4))  # assigned_user_id is NULL

    (hold,) = _load(worker).confirmed_holds

    assert (hold.kind, hold.resource_id, hold.identified) == (
        ResourceKind.PILOT,
        option_pilot,
        Identified.SELECTED_OPTION,
    )


def test_a_pilot_row_naming_nobody_holds_nothing_and_is_reported(
    world: World, worker: WorkerConnection
) -> None:
    berth = world.berth()
    request = world.request()
    recommendation = world.recommendation(request, "CONFIRMED")
    option = world.option(recommendation, 1, berth, H0, H0 + timedelta(hours=4))  # no pilot
    plan = world.plan(request, option_id=option)
    row = world.component(plan, "PILOT", H0, H0 + timedelta(hours=4))

    state = _load(worker)

    assert state.confirmed_holds == ()
    assert [(i.code, i.row_id) for i in state.inconsistencies] == [
        ("hold_resource_unidentified", row)
    ]


# Pending holds: option 1 of PENDING_REVIEW and MODIFIED_BY_STAFF (DEC-32 rule 3(b))


@pytest.mark.parametrize("status", ["PENDING_REVIEW", "MODIFIED_BY_STAFF"])
def test_option_one_of_a_pending_recommendation_holds_berth_pilot_and_tugs(
    world: World, worker: WorkerConnection, status: str
) -> None:
    berth, pilot, tug_a, tug_b = world.berth(), world.pilot(), world.tug(), world.tug()
    request = world.request()
    recommendation = world.recommendation(request, status)
    start, end = H0 + timedelta(hours=1), H0 + timedelta(hours=6)
    option = world.option(
        recommendation, 1, berth, start, end, pilot_id=pilot, tug_ids=(tug_a, tug_b)
    )

    state = _load(worker)

    assert state.confirmed_holds == ()  # not RESERVED rows: labelled apart
    assert {(h.kind, h.resource_id) for h in state.pending_holds} == {
        (ResourceKind.BERTH, berth),
        (ResourceKind.PILOT, pilot),
        (ResourceKind.TUG, tug_a),
        (ResourceKind.TUG, tug_b),
    }
    for hold in state.pending_holds:
        assert (hold.start, hold.end) == (start, end)
        assert hold.berthing_request_id == request
        assert hold.recommendation_id == recommendation
        assert hold.recommendation_status == status
        assert (hold.option_id, hold.option_rank) == (option, 1)


def test_options_two_and_three_hold_nothing(world: World, worker: WorkerConnection) -> None:
    berth_1, berth_2, berth_3 = world.berth(), world.berth(), world.berth()
    recommendation = world.recommendation(world.request())
    end = H0 + timedelta(hours=5)
    world.option(recommendation, 1, berth_1, H0, end)
    world.option(recommendation, 2, berth_2, H0, end, pilot_id=world.pilot())
    world.option(recommendation, 3, berth_3, H0, end, tug_ids=(world.tug(),))

    state = _load(worker)

    assert {hold.resource_id for hold in state.pending_holds} == {berth_1}


@pytest.mark.parametrize("status", ["REPLACED", "REJECTED", "INVALIDATED", "CONFIRMED"])
def test_other_recommendation_statuses_hold_no_pending_resources(
    world: World, worker: WorkerConnection, status: str
) -> None:
    recommendation = world.recommendation(world.request(), status)
    world.option(
        recommendation, 1, world.berth(), H0, H0 + timedelta(hours=5), pilot_id=world.pilot()
    )

    assert _load(worker).pending_holds == ()


# Shifts, roles and the rest of the snapshot


def test_a_shift_is_loaded_as_a_utc_interval_and_an_overnight_shift_crosses_midnight(
    world: World, worker: WorkerConnection
) -> None:
    pilot = world.pilot()
    day, night = world.shift("06:00:00", "18:00:00"), world.shift("18:00:00", "06:00:00")
    world.schedule_pilot(pilot, day, "2026-11-10")
    world.schedule_pilot(pilot, night, "2026-11-10")
    world.schedule_pilot(
        pilot, night, "2026-11-09"
    )  # ends 2026-11-10 06:00 Cairo, 04:00 UTC: before H0

    state = _load(worker)

    assert {(s.shift_id, s.start, s.end) for s in state.pilot_shifts} == {
        (day, datetime(2026, 11, 10, 4, 0, tzinfo=UTC), datetime(2026, 11, 10, 16, 0, tzinfo=UTC)),
        (
            night,
            datetime(2026, 11, 10, 16, 0, tzinfo=UTC),
            datetime(2026, 11, 11, 4, 0, tzinfo=UTC),
        ),
    }


def test_a_shift_that_started_before_the_horizon_and_reaches_into_it_is_loaded(
    world: World, worker: WorkerConnection
) -> None:
    pilot = world.pilot()
    night = world.shift(
        "18:00:00", "10:00:00"
    )  # 2026-11-09 18:00 to 2026-11-10 10:00 Cairo = 08:00 UTC
    world.schedule_pilot(pilot, night, "2026-11-09")

    shifts = _load(worker, start=H0 - timedelta(minutes=1), end=H1).pilot_shifts

    assert [s.end for s in shifts] == [datetime(2026, 11, 10, 8, 0, tzinfo=UTC)]
    assert _load(worker, start=H0, end=H1).pilot_shifts == ()  # ends exactly at the horizon start


def test_a_shift_in_a_local_time_that_does_not_exist_is_reported_not_guessed(
    world: World, worker: WorkerConnection
) -> None:
    """Cairo moved its clocks forward at 00:00 on 2026-04-24, so 00:30 that day never happened."""
    pilot = world.pilot()
    shift = world.shift("00:30:00", "08:00:00")
    schedule = seed_row(
        world.root,
        "pilot_schedules",
        pilot_user_id=pilot,
        shift_date="2026-04-24",
        port_shift_id=shift,
    )
    start = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)

    state = _load(worker, start=start, end=start + timedelta(days=2))

    assert state.pilot_shifts == ()
    assert [(i.code, i.table, i.row_id) for i in state.inconsistencies] == [
        ("shift_time_unresolvable", "pilot_schedules", schedule)
    ]


def test_people_flags_follow_the_user_and_the_role(world: World, worker: WorkerConnection) -> None:
    good, inactive, ended = world.pilot(), world.pilot(active=False), world.pilot(role_ended=True)
    tug = world.tug()
    master = world.master_of(tug)

    state = _load(worker)

    flags = {p.user_id: (p.is_active, p.has_active_pilot_role) for p in state.pilots}
    assert flags == {good: (True, True), inactive: (False, True), ended: (True, False)}
    ((loaded_master),) = state.tug_masters
    assert (loaded_master.user_id, loaded_master.tugboat_id) == (master, tug)
    assert (loaded_master.is_active, loaded_master.has_active_tug_master_role) == (True, True)


def test_berths_tugs_rank_limits_and_constraints_are_loaded(
    world: World, worker: WorkerConnection
) -> None:
    berth, tug = world.berth("MAINTENANCE"), world.tug("BUSY", master=False)
    seed_row(world.root, "pilot_rank_limits", pilot_rank="FIRST", max_vessel_loa=None)
    inside = seed_row(
        world.root,
        "safety_constraints",
        value=1,
        active_from=_sql(H0 - timedelta(days=1)),
        active_to=None,
    )
    seed_row(  # ended before the horizon
        world.root,
        "safety_constraints",
        value=1,
        active_from=_sql(H0 - timedelta(days=9)),
        active_to=_sql(H0),
    )
    seed_row(  # starts exactly when the horizon ends
        world.root, "safety_constraints", value=1, active_from=_sql(H1), active_to=None
    )

    state = _load(worker)

    assert [(b.id, b.status, b.terminal_ids) for b in state.berths] == [
        (berth, "MAINTENANCE", frozenset({TERMINAL}))
    ]
    assert [(t.id, t.status) for t in state.tugs] == [(tug, "BUSY")]
    assert [(r.pilot_rank, r.max_vessel_loa) for r in state.pilot_rank_limits] == [("FIRST", None)]
    assert [c.id for c in state.safety_constraints] == [inside]
    assert state.time_zone == "Africa/Cairo"


def test_requests_confirmed_windows_and_manifests_of_the_requests_in_scope(
    world: World, worker: WorkerConnection
) -> None:
    vessel_type = seed_row(world.root, "vessel_types", code="CONTAINER")
    vessel = seed_row(world.root, "vessels", vessel_type_id=vessel_type)
    mine = seed_row(world.root, "berthing_requests", vessel_id=vessel, **REQUEST_COLUMNS)
    other = seed_row(world.root, "berthing_requests", vessel_id=vessel, **REQUEST_COLUMNS)
    proposal = seed_row(
        world.root, "entry_window_proposals", berthing_request_id=mine, status="PROPOSED"
    )
    window = seed_row(
        world.root,
        "feasible_windows",
        proposal_id=proposal,
        window_start=_sql(H0),
        window_end=_sql(H0 + timedelta(hours=3)),
    )
    with world.root.cursor() as cursor:
        cursor.execute(
            "UPDATE entry_window_proposals SET status = 'CONFIRMED', confirmed_window_id = %s, "
            "confirmed_by = 1, confirmed_at = '2026-11-09 09:00:00' WHERE id = %s",
            (window, proposal),
        )
    world.root.commit()
    seed_row(world.root, "entry_window_proposals", berthing_request_id=other, status="PROPOSED")
    active = seed_row(
        world.root,
        "baplie_files",
        berthing_request_id=mine,
        status="ACTIVE",
        parse_status="PARSED",
        file_hash_sha256="a" * 64,
    )
    replaced = seed_row(
        world.root,
        "baplie_files",
        berthing_request_id=mine,
        status="REPLACED",
        parse_status="PARSED",
        file_hash_sha256="b" * 64,
    )
    seed_row(
        world.root,
        "container_manifest_entries",
        baplie_file_id=active,
        container_id=1,
        weight_kg=9000,
    )
    seed_row(
        world.root,
        "container_manifest_entries",
        baplie_file_id=replaced,
        container_id=2,
        weight_kg=1,
    )

    state = _load(worker, mine, 999_999)  # an unknown request is skipped

    assert [r.request_id for r in state.requests] == [mine]
    assert [(w.berthing_request_id, w.window_id, w.start) for w in state.confirmed_windows] == [
        (mine, window, H0)
    ]
    assert [
        (m.berthing_request_id, m.container_id, m.weight_kg) for m in state.manifest_entries
    ] == [(mine, 1, 9000)]


# Arguments, transaction and consistency


def test_the_horizon_must_be_aware_and_non_empty(worker: WorkerConnection) -> None:
    naive = datetime(2026, 11, 10, 8, 0)  # noqa: DTZ001 - the point of the test
    with pytest.raises(PortStateError, match="aware"):
        load_port_state(worker, [], horizon_start=naive, horizon_end=H1)
    with pytest.raises(PortStateError, match="end after"):
        load_port_state(worker, [], horizon_start=H1, horizon_end=H0)


def test_the_horizon_has_no_default(worker: WorkerConnection) -> None:
    call: Callable[..., PortState] = load_port_state
    with pytest.raises(TypeError, match="horizon_start"):
        call(worker, [])


def test_the_loader_takes_a_connection_with_no_open_transaction_and_leaves_none(
    world: World, worker: WorkerConnection
) -> None:
    core_of(worker).exec_driver_sql("SELECT 1")  # autobegin
    with pytest.raises(PortStateError, match="no open transaction"):
        _load(worker)
    worker.rollback()

    world.berth()
    _load(worker)

    assert not core_of(worker).in_transaction()


def test_a_row_committed_during_the_load_is_not_seen_by_it(
    world: World, worker: WorkerConnection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One REPEATABLE READ snapshot: a plan confirmed halfway through is in no table of the load."""
    real = snapshot._read_pending_holds  # noqa: SLF001
    late_berth = world.berth()

    def read_after_a_commit(*args: Any, **kwargs: Any) -> Any:
        recommendation = world.recommendation(world.request())
        world.option(recommendation, 1, late_berth, H0, H0 + timedelta(hours=4))
        return real(*args, **kwargs)

    monkeypatch.setattr(snapshot, "_read_pending_holds", read_after_a_commit)
    assert _load(worker).pending_holds == ()  # the snapshot predates the commit

    monkeypatch.setattr(snapshot, "_read_pending_holds", real)
    assert len(_load(worker).pending_holds) == 1  # a new load sees it


# The loaded state, judged by the DEC-32 and berth rules


def test_the_loaded_state_answers_the_availability_rules(
    world: World, worker: WorkerConnection
) -> None:
    pilot, tug, berth = world.pilot(), world.tug(), world.berth()
    shift = world.shift("06:00:00", "18:00:00")  # 04:00 to 16:00 UTC
    world.schedule_pilot(pilot, shift)
    world.schedule_master(world.master_of(tug), shift)
    held_request = world.request()
    recommendation = world.recommendation(held_request)
    world.option(
        recommendation,
        1,
        berth,
        H0 + timedelta(hours=2),
        H0 + timedelta(hours=6),
        pilot_id=pilot,
        tug_ids=(tug,),
    )
    start, end = H0 + timedelta(hours=1), H0 + timedelta(hours=3)

    state = _load(worker, held_request)

    assert not is_pilot_available(state, pilot, start, end)
    assert not is_tug_available(state, tug, start, end)
    assert not is_berth_available(state, berth, TERMINAL, start, end)
    # The request of the current run: its previous PENDING_REVIEW recommendation holds nothing.
    left = without_requests(state.pending_holds, [held_request])
    assert is_pilot_available(state, pilot, start, end, pending_holds=left)
    assert is_tug_available(state, tug, start, end, pending_holds=left)
    assert is_berth_available(state, berth, TERMINAL, start, end, pending_holds=left)
    # Back to back with the held job is free, and a job crossing the shift change is not.
    assert is_pilot_available(state, pilot, H0, H0 + timedelta(hours=2))
    assert not is_pilot_available(state, pilot, H0 + timedelta(hours=7), H0 + timedelta(hours=9))


# Load time (criterion 3)


def test_the_load_time_of_the_reference_port_is_measured(
    world: World,
    worker: WorkerConnection,
    root: pymysql.connections.Connection[Any],
    scenario_tables: None,
    record_property: Callable[[str, object], None],
) -> None:
    """Loads the synthetic reference port and a busy day on top of it, and records the times.

    There is no threshold: the backlog asks for the figure, not a limit. It is on the test report
    (`record_property`) and printed with `-s`.
    """
    scenario = read_scenario(REFERENCE)
    with root.cursor() as cursor:
        cursor.execute("DELETE FROM port_profiles")  # the scenario brings its own
    root.commit()
    load_scenario(root, scenario)
    with root.cursor() as cursor:
        cursor.execute(
            "SET foreign_key_checks = 0"
        )  # the loader turned them on; seeding is the Backend's
    shift = world.shift("06:00:00", "18:00:00")
    pilots = [world.pilot() for _ in range(60)]
    for pilot in pilots:
        world.schedule_pilot(pilot, shift)
    request_ids = [row[0] for row in _fetch(root, "SELECT id FROM berthing_requests ORDER BY id")]
    berth_ids = [row[0] for row in _fetch(root, "SELECT id FROM berths ORDER BY id")]
    tug_ids = [row[0] for row in _fetch(root, "SELECT id FROM tugboats ORDER BY id")]
    for index, request in enumerate(request_ids[:120]):
        start = H0 + timedelta(minutes=30 * (index % 20))
        end = start + timedelta(hours=4)
        plan = world.plan(request)
        world.component(plan, "BERTH", start, end, resource_id=berth_ids[index % len(berth_ids)])
        world.component(plan, "TUG", start, end, resource_id=tug_ids[index % len(tug_ids)])
        world.component(plan, "PILOT", start, end, assigned_user_id=pilots[index % len(pilots)])
    root.commit()

    state = _load(worker, *request_ids)

    for step, seconds in state.timings.items():
        record_property(f"port_state_load_seconds_{step}", round(seconds, 4))
    print(  # noqa: T201 - the figure the task asks for
        "port-state load:",
        {"requests": len(state.requests), "holds": len(state.confirmed_holds)},
        {step: round(seconds, 4) for step, seconds in state.timings.items()},
    )
    assert state.timings["total"] > 0
    assert len(state.requests) == len(request_ids)
    assert len(state.confirmed_holds) == 360
    assert len(state.berths) == len(berth_ids)


def _fetch(conn: pymysql.connections.Connection[Any], sql: str) -> list[tuple[Any, ...]]:
    with conn.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
    conn.commit()
    return [tuple(row) for row in rows]
