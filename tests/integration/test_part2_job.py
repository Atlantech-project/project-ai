"""The PART2_SOLVE handler end to end (AI-059): real runtime, MySQL and Redis, one scenario per
trigger and per outcome. Every value is SYNTHETIC.

Each test sends a C-02 message through `Worker.process_message`: the runtime claims the run,
calls the handler, commits with the guarded `solver_runs` update and pushes C-06 to Redis. The
assertions read the database and the C-06, never only the handler's return value.
"""

import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Final

import pymysql
import pytest
import redis
from ortools.sat.python import cp_model

from common.config import WorkerPart, load_env_settings
from common.db.connection import connect_worker, dispose_engines
from common.runtime.envelope import load_schemas
from common.runtime.worker import AI_RESULTS_QUEUE, Worker, connect_redis
from part2 import job, persist
from part2.solver import cpsat
from tests.support.port_db import PortDatabase, seed_row
from tests.support.services import ServiceSettings

pytestmark = pytest.mark.integration

SCHEMAS: Final = Path(__file__).resolve().parents[2] / "docs" / "ref" / "ai-payloads"
TERMINAL: Final = 7
H0: Final = datetime(2026, 11, 10, 8, 0, tzinfo=UTC)  # 10:00 in Cairo
WINDOW: Final = (H0, H0 + timedelta(hours=6))
SETTINGS: Final = (
    ("solver_time_limit_seconds", "10", "INT"),
    ("solver_options_per_request", "3", "INT"),
    ("solver_option_equivalence_pct", "10", "DECIMAL"),
    ("objective_weight_waiting_time", "1.0", "DECIMAL"),
    ("objective_weight_resource", "1.0", "DECIMAL"),
    ("part1_stored_data_max_age_hours", "48", "INT"),
)
TABLES: Final = (
    "actual_status_updates",
    "plan_components",
    "operational_plans",
    "solver_run_model_versions",
    "recommendation_rationale_factors",
    "recommendation_option_tugs",
    "recommendation_options",
    "recommendations",
    "solver_runs",
    "objective_terms",
    "rationale_templates",
    "port_settings",
    "terminal_productivity_profiles",
    "baplie_files",
    "entry_window_proposals",
    "feasible_windows",
    "berthing_requests",
    "vessels",
    "vessel_types",
    "berth_terminals",
    "berths",
    "tug_master_schedules",
    "tug_master_profiles",
    "tugboats",
    "pilot_schedules",
    "pilot_rank_limits",
    "pilot_profiles",
    "port_shifts",
    "user_role_assignments",
    "users",
    "port_profiles",
    "constraint_types",
)


def _sql(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")


@pytest.fixture
def root(port_db: PortDatabase) -> Iterator[pymysql.connections.Connection[Any]]:
    conn = port_db.root()

    def empty() -> None:
        with conn.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            for table in TABLES:
                cursor.execute(f"DELETE FROM `{table}`")  # noqa: S608 - fixed names
        conn.commit()

    empty()
    try:
        yield conn
    finally:
        dispose_engines()
        empty()
        conn.close()


@pytest.fixture
def queues(service_settings: ServiceSettings) -> Iterator[redis.Redis]:
    client = connect_redis(service_settings.redis_url)
    client.delete(AI_RESULTS_QUEUE)
    try:
        yield client
    finally:
        client.delete(AI_RESULTS_QUEUE)
        client.close()


class Port:
    """A small SYNTHETIC port: two berths, two pilots, three tugs, one terminal."""

    def __init__(self, root: Any, port_db: PortDatabase, queues: redis.Redis) -> None:
        self.root, self.port_db, self.queues = root, port_db, queues
        self._n = 0
        seed_row(root, "port_profiles", id=1, port_code="EGDAM", timezone="Africa/Cairo")
        for key, value, value_type in SETTINGS:
            seed_row(
                root, "port_settings", setting_key=key, setting_value=value, value_type=value_type
            )
        for code, name in (
            ("WAITING_TIME", "Vessel waiting time"),
            ("RESOURCE_COST", "Resource cost"),
        ):
            seed_row(root, "objective_terms", code=code, name=name)
        self.container = seed_row(root, "vessel_types", code="CONTAINER")
        seed_row(
            root,
            "terminal_productivity_profiles",
            terminal_id=TERMINAL,
            terminal_type="CONTAINER",
            vessel_type_id=None,
            productivity_rate=25,
            rate_unit="MOVES_PER_HOUR",
            fixed_overhead_minutes=60,
            valid_from="2026-01-01",
        )
        shift = seed_row(
            root,
            "port_shifts",
            code="DAY",
            name="Day",
            start_time="06:00:00",
            end_time="18:00:00",
            is_active=True,
        )
        seed_row(root, "pilot_rank_limits", pilot_rank="FIRST", max_vessel_loa=None)
        self.berths = tuple(self._berth() for _ in range(2))
        self.pilots = tuple(self._pilot(shift) for _ in range(2))
        self.tugs = tuple(self._tug(shift) for _ in range(3))

    def _next(self) -> int:
        self._n += 1
        return self._n

    def _user(self, role: str) -> int:
        n = self._next()
        user = seed_row(self.root, "users", username=f"syn{n:03d}", name=f"SYNTHETIC {n}")
        seed_row(
            self.root,
            "user_role_assignments",
            user_id=user,
            role=role,
            unit_type="MARINE_SERVICES",
            active_from="2026-01-01 00:00:00",
            active_to=None,
        )
        return user

    def _berth(self) -> int:
        berth = seed_row(
            self.root,
            "berths",
            code=f"SYN-B{self._next()}",
            length=300,
            water_depth=15,
            depth_datum="LAT",
            max_vessel_loa=280,
            status="ACTIVE",
        )
        seed_row(self.root, "berth_terminals", berth_id=berth, terminal_id=TERMINAL)
        return berth

    def _pilot(self, shift: int) -> int:
        user = self._user("MARINE_PILOT")
        seed_row(self.root, "pilot_profiles", user_id=user, pilot_rank="FIRST")
        seed_row(
            self.root,
            "pilot_schedules",
            pilot_user_id=user,
            shift_date="2026-11-10",
            port_shift_id=shift,
        )
        return user

    def _tug(self, shift: int) -> int:
        tug = seed_row(
            self.root,
            "tugboats",
            name=f"SYNTHETIC TUG {self._next()}",
            tug_power=50,
            tug_power_unit="BOLLARD_PULL_TONNES",
            status="AVAILABLE",
        )
        master = self._user("TUG_MASTER")
        seed_row(self.root, "tug_master_profiles", user_id=master, assigned_tugboat_id=tug)
        seed_row(
            self.root,
            "tug_master_schedules",
            tug_master_user_id=master,
            shift_date="2026-11-10",
            port_shift_id=shift,
        )
        return tug

    def request(
        self, *, loa: int = 200, baplie: bool = True, status: str = "ENTRY_WINDOW_CONFIRMED"
    ) -> int:
        n = self._next()
        vessel = seed_row(
            self.root,
            "vessels",
            vessel_type_id=self.container,
            name=f"SYNTHETIC VESSEL {n}",
            loa=loa,
            beam=30,
            max_draft=12,
            imo_number=f"{9000000 + n}",
        )
        request = seed_row(
            self.root,
            "berthing_requests",
            vessel_id=vessel,
            requested_terminal_id=TERMINAL,
            status=status,
            requested_eta=_sql(H0),
            arrival_draft=10,
            block_coefficient=0.7,
            gross_tonnage=30000,
            deadweight_tonnes=40000,
            loading_container_count=10,
            source="MANUAL",
            submitted_by=1,
        )
        window = seed_row(
            self.root, "feasible_windows", window_start=_sql(WINDOW[0]), window_end=_sql(WINDOW[1])
        )
        self.proposal = seed_row(
            self.root,
            "entry_window_proposals",
            berthing_request_id=request,
            status="CONFIRMED",
            confirmed_window_id=window,
            confirmed_by=1,
            confirmed_at="2026-11-09 09:00:00",
        )
        if baplie:
            seed_row(
                self.root,
                "baplie_files",
                berthing_request_id=request,
                status="ACTIVE",
                parse_status="PARSED",
            )
        return request

    def recommendation(self, request: int, status: str) -> int:
        return seed_row(
            self.root,
            "recommendations",
            berthing_request_id=request,
            terminal_id=TERMINAL,
            entry_window_proposal_id=self.proposal,
            status=status,
            purpose="INITIAL",
            generated_at="2026-11-09 09:00:00",
        )

    def confirmed_plan(self, request: int, start: datetime, end: datetime) -> dict[str, int]:
        """A CONFIRMED recommendation, its option and plan, with berth, pilot and two tug rows."""
        rec = self.recommendation(request, "CONFIRMED")
        option = seed_row(
            self.root,
            "recommendation_options",
            recommendation_id=rec,
            terminal_id=TERMINAL,
            option_rank=1,
            berth_id=self.berths[1],
            planned_start=_sql(start),
            planned_end=_sql(end),
            pilot_user_id=self.pilots[1],
            service_time_method="FORMULA",
            service_time_p50_hours=1.4,
        )
        plan = seed_row(
            self.root,
            "operational_plans",
            berthing_request_id=request,
            recommendation_id=rec,
            recommendation_option_id=option,
            status="CONFIRMED",
        )
        rows = {"recommendation": rec, "plan": plan}
        parts = (
            ("BERTH", self.berths[1]),
            ("PILOT", self.pilots[1]),
            ("TUG", self.tugs[2]),
            ("TUG", self.tugs[1]),
        )
        for kind, resource in parts:
            rows[f"{kind}-{resource}"] = seed_row(
                self.root,
                "plan_components",
                operational_plan_id=plan,
                component_type=kind,
                berth_id=resource if kind == "BERTH" else None,
                tugboat_id=resource if kind == "TUG" else None,
                terminal_id=None,
                assigned_user_id=resource if kind == "PILOT" else None,
                assigned_at="2026-11-09 10:00:00" if kind == "PILOT" else None,
                planned_start=_sql(start),
                planned_end=_sql(end),
                reservation_state="RESERVED",
            )
        return rows

    def started(self, component: int, kind: str) -> None:
        seed_row(
            self.root,
            "actual_status_updates",
            client_event_id=str(uuid.uuid4()),
            plan_component_id=component,
            component_type=kind,
            reported_by=1,
            status="STARTED",
            reported_at="2026-11-10 08:30:00",
            sync_source="MOBILE",
        )

    def run(self, trigger: str = "NEW_REQUEST") -> int:
        return seed_row(
            self.root,
            "solver_runs",
            trigger_type=trigger,
            status="QUEUED",
            solver_version="pending",
            queued_at="2026-11-09 11:59:00",
            horizon_start=_sql(H0 - timedelta(days=1)),
            horizon_end=_sql(H0 + timedelta(days=7)),
            triggered_by=1 if trigger == "MANUAL" else None,
        )

    def send(
        self, run_id: int, triggers: list[dict[str, Any]], message: bytes | None = None
    ) -> bytes:
        """Handle one C-02 message (built from `triggers`, or `message` as given)."""
        raw = message if message is not None else _message(run_id, triggers)
        settings = load_env_settings(self.port_db.worker_env(WorkerPart.PART2), WorkerPart.PART2)
        worker = Worker(
            job.DEFINITION, lambda: connect_worker(settings), self.queues, load_schemas(SCHEMAS)
        )
        worker.process_message(raw)
        return raw

    def completions(self) -> list[dict[str, Any]]:
        return [json.loads(item) for item in self.queues.lrange(AI_RESULTS_QUEUE, 0, -1)]

    def fetch(self, query: str, *args: object) -> tuple[Any, ...]:
        self.root.commit()
        with self.root.cursor() as cursor:
            cursor.execute(query, args)
            return tuple(cursor.fetchall())

    def run_row(self, run_id: int) -> tuple[str, dict[str, Any]]:
        [(status, detail)] = self.fetch(
            "SELECT status, result_detail FROM solver_runs WHERE id = %s", run_id
        )
        return status, json.loads(detail) if detail else {}


PRECEDENCE: Final = ("NEW_REQUEST", "MANUAL", "RESOURCE_CHANGE", "REPLAN")  # CT-10, lowest first


def _message(run_id: int, triggers: list[dict[str, Any]]) -> bytes:
    top = max(triggers, key=lambda t: PRECEDENCE.index(t["trigger_type"]))
    envelope = {
        "contract_version": "1.0",
        "job_type": "PART2_SOLVE",
        "job_id": str(uuid.uuid4()),
        "run_id": run_id,
        "enqueued_at": "2026-11-09T12:00:00Z",
        "triggered_by_user_id": None,
        "payload": {"trigger_type": top["trigger_type"], "triggers": triggers},
    }
    return json.dumps(envelope).encode()


@pytest.fixture
def port(root: Any, port_db: PortDatabase, queues: redis.Redis) -> Port:
    return Port(root, port_db, queues)


def entry(trigger: str, *ids: int, **extra: Any) -> dict[str, Any]:
    return {"trigger_type": trigger, "berthing_request_ids": list(ids), **extra}


# --- NEW_REQUEST: the first recommendation ---------------------------------------------------


def test_new_request_writes_the_first_recommendation_with_its_rows(port: Port) -> None:
    request = port.request()
    run = port.run()
    port.send(run, [entry("NEW_REQUEST", request)])

    [c06] = port.completions()
    assert (c06["status"], c06["outcome"], c06["error_category"]) == ("DONE", "SOLVED", None)
    status, detail = port.run_row(run)
    assert status in ("OPTIMAL", "FEASIBLE")
    [(rec, rec_status, source, purpose, proposal)] = port.fetch(
        "SELECT id, status, source, purpose, entry_window_proposal_id FROM recommendations"
    )
    assert (rec_status, source, purpose, proposal) == (
        "PENDING_REVIEW",
        "AI",
        "INITIAL",
        port.proposal,
    )
    assert detail["requests"][0]["recommendation_id"] == rec
    options = port.fetch(
        "SELECT id, planned_start, planned_end, service_time_method, service_time_p50_hours, "
        "delay_risk FROM recommendation_options WHERE recommendation_id = %s ORDER BY option_rank",
        rec,
    )
    assert options and detail["requests"][0]["options_count"] == len(options)
    first = options[0]
    # B3: 10 moves at 25 moves/h plus 60 min overhead = 1.40 h; B4: no forecast, so NULL.
    assert (first[3], first[4], first[5]) == ("FORMULA", Decimal("1.40"), None)
    assert first[2] - first[1] == timedelta(minutes=84)
    assert WINDOW[0] <= first[1].replace(tzinfo=UTC) < WINDOW[1]
    assert (
        port.fetch(
            "SELECT COUNT(*) FROM recommendation_option_tugs WHERE option_id = %s", first[0]
        )[0][0]
        >= 1
    )
    assert port.fetch(
        "SELECT COUNT(*) FROM recommendation_rationale_factors WHERE option_id = %s", first[0]
    ) == ((2,),)


# --- MANUAL and RESOURCE_CHANGE: written without a current version, refused with one ---------


def test_manual_for_a_request_without_a_current_version_is_written(port: Port) -> None:
    request = port.request()
    run = port.run("MANUAL")
    port.send(run, [entry("MANUAL", request, requested_by_user_id=1)])

    assert port.completions()[0]["outcome"] == "SOLVED"
    assert port.fetch("SELECT status, purpose FROM recommendations") == (
        ("PENDING_REVIEW", "INITIAL"),
    )


@pytest.mark.parametrize(
    ("trigger", "current", "message"),
    [
        ("MANUAL", "PENDING_REVIEW", "INT-B11"),
        ("RESOURCE_CHANGE", "MODIFIED_BY_STAFF", "INT-B11"),
        ("RESOURCE_CHANGE", "CONFIRMED", "only REPLAN"),
    ],
)
def test_a_re_solve_of_a_request_with_a_current_version_fails_and_keeps_it(
    port: Port, trigger: str, current: str, message: str
) -> None:
    request = port.request(status="RECOMMENDATION_GENERATED")
    previous = port.recommendation(request, current)
    run = port.run(trigger)
    extra: dict[str, Any] = (
        {"requested_by_user_id": 1}
        if trigger == "MANUAL"
        else {"changed_resources": [{"type": "TUG", "id": port.tugs[0]}]}
    )
    port.send(run, [entry(trigger, request, **extra)])

    [c06] = port.completions()
    assert (c06["status"], c06["outcome"], c06["error_category"]) == (
        "FAILED",
        "GENERATION_FAILED",
        "PRECONDITION_FAILED",
    )
    status, detail = port.run_row(run)
    assert status == "ERROR" and message in detail["failure_reason"]["message"]
    assert port.fetch("SELECT id, status FROM recommendations") == ((previous, current),)
    assert port.fetch("SELECT COUNT(*) FROM recommendation_options") == ((0,),)


def test_resource_change_for_a_request_without_a_current_version_is_written(port: Port) -> None:
    request = port.request()
    run = port.run("RESOURCE_CHANGE")
    port.send(
        run,
        [
            entry(
                "RESOURCE_CHANGE",
                request,
                changed_resources=[{"type": "BERTH", "id": port.berths[0]}],
            )
        ],
    )

    assert port.completions()[0]["outcome"] == "SOLVED"
    assert port.fetch("SELECT status, purpose FROM recommendations") == (
        ("PENDING_REVIEW", "INITIAL"),
    )


# --- REPLAN: a DELAY_REPLAN proposal that keeps the started components ------------------------


def test_replan_writes_a_delay_replan_proposal_keeping_started_components(port: Port) -> None:
    request = port.request(status="PLAN_CONFIRMED")
    start, end = H0 + timedelta(hours=2), H0 + timedelta(hours=3, minutes=24)
    rows = port.confirmed_plan(request, start, end)
    port.started(rows[f"PILOT-{port.pilots[1]}"], "PILOT")
    port.started(rows[f"TUG-{port.tugs[2]}"], "TUG")
    run = port.run("REPLAN")
    port.send(run, [entry("REPLAN", request, operational_plan_id=rows["plan"])])

    [c06] = port.completions()
    assert (c06["status"], c06["outcome"]) == ("DONE", "SOLVED")
    recs = port.fetch("SELECT id, status, purpose FROM recommendations ORDER BY id")
    assert recs[0] == (rows["recommendation"], "CONFIRMED", "INITIAL")  # untouched
    proposal = recs[1]
    assert proposal[1:] == ("PENDING_REVIEW", "DELAY_REPLAN")
    options = port.fetch(
        "SELECT id, planned_start, planned_end, pilot_user_id FROM recommendation_options "
        "WHERE recommendation_id = %s",
        proposal[0],
    )
    assert options
    for option_id, o_start, o_end, pilot in options:
        assert (o_start.replace(tzinfo=UTC), o_end.replace(tzinfo=UTC), pilot) == (
            start,
            end,
            port.pilots[1],
        )
        tugs = {
            t
            for (t,) in port.fetch(
                "SELECT tugboat_id FROM recommendation_option_tugs WHERE option_id = %s", option_id
            )
        }
        assert port.tugs[2] in tugs  # the started tug stays; the others may change


def test_replan_naming_another_plan_fails_and_writes_nothing(port: Port) -> None:
    request = port.request(status="PLAN_CONFIRMED")
    rows = port.confirmed_plan(request, H0 + timedelta(hours=2), H0 + timedelta(hours=3))
    run = port.run("REPLAN")
    port.send(run, [entry("REPLAN", request, operational_plan_id=rows["plan"] + 999)])

    assert port.completions()[0]["error_category"] == "PRECONDITION_FAILED"
    assert port.fetch("SELECT COUNT(*) FROM recommendations") == ((1,),)  # only the CONFIRMED one


def test_replan_with_a_started_tug_now_in_maintenance_is_no_feasible_plan(port: Port) -> None:
    request = port.request(status="PLAN_CONFIRMED")
    rows = port.confirmed_plan(
        request, H0 + timedelta(hours=2), H0 + timedelta(hours=3, minutes=24)
    )
    port.started(rows[f"TUG-{port.tugs[2]}"], "TUG")
    with port.root.cursor() as cursor:
        cursor.execute("UPDATE tugboats SET status = 'MAINTENANCE' WHERE id = %s", (port.tugs[2],))
    port.root.commit()
    run = port.run("REPLAN")
    port.send(run, [entry("REPLAN", request, operational_plan_id=rows["plan"])])

    [c06] = port.completions()
    assert (c06["status"], c06["outcome"]) == ("DONE", "NO_FEASIBLE_PLAN")
    status, detail = port.run_row(run)
    assert status == "INFEASIBLE"
    codes = [b["constraint_type_code"] for b in detail["requests"][0]["binding_constraints"]]
    assert "TUG_UNAVAILABLE" in codes  # the pinned tug, not the berth or the pilot, is missing
    assert port.fetch("SELECT COUNT(*) FROM recommendations") == ((1,),)


# --- no feasible plan, partial runs ------------------------------------------------------------


def test_a_request_no_berth_can_take_is_no_feasible_plan_and_writes_nothing(port: Port) -> None:
    request = port.request(loa=300)  # every berth takes at most 280 m
    run = port.run()
    port.send(run, [entry("NEW_REQUEST", request)])

    [c06] = port.completions()
    assert (c06["status"], c06["outcome"]) == ("DONE", "NO_FEASIBLE_PLAN")
    status, detail = port.run_row(run)
    assert status == "INFEASIBLE"
    codes = [b["constraint_type_code"] for b in detail["requests"][0]["binding_constraints"]]
    assert "MAX_LOA" in codes  # the 300 m vessel also lacks tugs (DEC-20): TUG_UNAVAILABLE, v1.1
    assert set(codes) <= {"MAX_LOA", "MAX_DRAFT", "TUG_UNAVAILABLE", "PILOT_UNAVAILABLE"}
    assert port.fetch("SELECT COUNT(*) FROM recommendations") == ((0,),)


def test_a_request_b3_cannot_time_is_reported_and_the_rest_is_solved(port: Port) -> None:
    timed, untimed = port.request(), port.request(baplie=False)
    run = port.run()
    port.send(run, [entry("NEW_REQUEST", timed, untimed)])

    assert port.completions()[0]["outcome"] == "PARTIALLY_SOLVED"
    _, detail = port.run_row(run)
    left = next(r for r in detail["requests"] if r["request_id"] == untimed)
    assert left["outcome"] == "NO_FEASIBLE_PLAN"
    assert left["binding_constraints"][0]["detail"] == "No service time (B3): MISSING_MOVES"
    assert port.fetch("SELECT berthing_request_id FROM recommendations") == ((timed,),)


# --- technical failures, retries and re-delivery -------------------------------------------------


def test_a_solver_timeout_writes_a_fifo_plan(port: Port, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cpsat, "_run", lambda *a, **k: cpsat._Outcome(cp_model.UNKNOWN, {}))
    request = port.request()
    run = port.run()
    port.send(run, [entry("NEW_REQUEST", request)])

    [c06] = port.completions()
    assert (c06["status"], c06["outcome"], c06["error_category"]) == (
        "DONE",
        "FIFO_FALLBACK",
        "TIMEOUT",
    )
    status, detail = port.run_row(run)
    assert status == "ERROR" and detail["failure_reason"]["error_category"] == "TIMEOUT"
    assert port.fetch("SELECT source FROM recommendations") == (("FIFO",),)
    assert port.fetch("SELECT objective_score FROM recommendation_options") == ((None,),)


def test_a_write_failure_rolls_everything_back_after_the_retry(
    port: Port, monkeypatch: pytest.MonkeyPatch
) -> None:
    attempts: list[int] = []
    real = persist.write_run

    def failing(repo: Any, run_id: int, plan: Any) -> Any:
        real(repo, run_id, plan)  # rows really inserted in the transaction ...
        attempts.append(run_id)
        raise RuntimeError("SYNTHETIC failure after the inserts")  # ... then lost

    monkeypatch.setattr(job, "write_run", failing)
    request = port.request()
    run = port.run()
    port.send(run, [entry("NEW_REQUEST", request)])

    assert len(attempts) == 2  # first try and one retry (PART2_SOLVE: one retry)
    [c06] = port.completions()
    assert (c06["status"], c06["outcome"], c06["error_category"]) == (
        "FAILED",
        "GENERATION_FAILED",
        "INTERNAL_ERROR",
    )
    assert port.run_row(run)[0] == "ERROR"
    assert port.fetch("SELECT COUNT(*) FROM recommendations") == ((0,),)
    assert port.fetch("SELECT COUNT(*) FROM recommendation_options") == ((0,),)


def test_a_failed_first_attempt_leaves_no_duplicate_after_the_retry(
    port: Port, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = persist.write_run
    calls: list[int] = []

    def flaky(repo: Any, run_id: int, plan: Any) -> Any:
        result = real(repo, run_id, plan)
        calls.append(run_id)
        if len(calls) == 1:
            raise RuntimeError("SYNTHETIC transient failure")
        return result

    monkeypatch.setattr(job, "write_run", flaky)
    request = port.request()
    run = port.run()
    port.send(run, [entry("NEW_REQUEST", request)])

    assert len(calls) == 2
    assert port.completions()[0]["outcome"] == "SOLVED"
    assert port.fetch("SELECT COUNT(*) FROM recommendations") == ((1,),)


def test_a_re_delivered_message_is_not_handled_twice(port: Port) -> None:
    request = port.request()
    run = port.run()
    raw = port.send(run, [entry("NEW_REQUEST", request)])
    port.send(run, [], message=raw)  # the same message again (CT-08 at-least-once delivery)

    assert len(port.completions()) == 1
    assert port.fetch("SELECT COUNT(*) FROM recommendations") == ((1,),)


def test_a_mixed_message_writes_each_request_with_its_own_purpose(port: Port) -> None:
    new = port.request()
    replanned = port.request(status="PLAN_CONFIRMED")
    rows = port.confirmed_plan(
        replanned, H0 + timedelta(hours=2), H0 + timedelta(hours=3, minutes=24)
    )
    run = port.run("REPLAN")
    port.send(
        run,
        [entry("NEW_REQUEST", new), entry("REPLAN", replanned, operational_plan_id=rows["plan"])],
    )

    assert port.completions()[0]["outcome"] == "SOLVED"
    written = port.fetch(
        "SELECT berthing_request_id, status, purpose FROM recommendations WHERE id <> %s "
        "ORDER BY berthing_request_id",
        rows["recommendation"],
    )
    assert written == (
        (new, "PENDING_REVIEW", "INITIAL"),
        (replanned, "PENDING_REVIEW", "DELAY_REPLAN"),
    )
    _, detail = port.run_row(run)
    assert {r["request_id"]: r["purpose"] for r in detail["requests"]} == {
        new: "INITIAL",
        replanned: "DELAY_REPLAN",
    }


def test_a_request_that_does_not_exist_fails_the_run(port: Port) -> None:
    request = port.request()
    run = port.run()
    port.send(run, [entry("NEW_REQUEST", request, request + 9999)])

    [c06] = port.completions()
    assert (c06["status"], c06["error_category"]) == ("FAILED", "PRECONDITION_FAILED")
    assert "not found" in port.run_row(run)[1]["failure_reason"]["message"]
    assert port.fetch("SELECT COUNT(*) FROM recommendations") == ((0,),)
