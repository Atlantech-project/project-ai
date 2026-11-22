"""Recommendation persistence against MySQL (AI-058), as `w_part2`, with real keys and CHECKs.

Every value is SYNTHETIC. The run is completed through the runtime's own guarded `write_done`,
so the test covers the whole transaction a PART2_SOLVE job commits.
"""

import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Final

import pymysql
import pytest
import sqlalchemy as sa

from common.config import WorkerPart, load_env_settings
from common.db.connection import WorkerConnection, connect_worker, dispose_engines
from common.db.repository import WorkerRepository
from common.runtime.envelope import JobType
from common.runtime.errors import JobError
from common.runtime.runs import RUN_TABLES, write_done
from part2.filter import Option
from part2.outcomes import PlannedOption, RequestOutcome, RequestResult, RunOutcome, SolveOutcome
from part2.persist import (
    OptionEstimate,
    plan_run,
    read_current_versions,
    read_objective_term_ids,
    read_template_catalog,
    write_run,
)
from part2.rationale import OptionRationale, objective_factors
from part2.solver import TERM_RESOURCE_COST, TERM_WAITING_TIME, TermValue
from tests.support.port_db import PortDatabase, seed_row

pytestmark = pytest.mark.integration

TERMINAL: Final = 7
H0: Final = datetime(2026, 11, 10, 8, 0, tzinfo=UTC)
NOW: Final = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)
TOUCHED: Final = (
    "solver_run_model_versions",
    "recommendation_rationale_factors",
    "recommendation_option_tugs",
    "recommendation_options",
    "recommendations",
    "solver_runs",
    "rationale_templates",
    "objective_terms",
    "entry_window_proposals",
    "berthing_requests",
    "berth_terminals",
    "berths",
    "tugboats",
    "pilot_profiles",
    "users",
    "ml_model_versions",
    "ml_models",
)
TERMS: Final = (
    TermValue(TERM_WAITING_TIME, Decimal("0.25"), Decimal("1.0")),
    TermValue(TERM_RESOURCE_COST, Decimal("0.5"), Decimal("1.0")),
)


@pytest.fixture(autouse=True)
def fresh_sessions() -> Iterator[None]:
    yield
    dispose_engines()


@pytest.fixture
def root(port_db: PortDatabase) -> Iterator[pymysql.connections.Connection[Any]]:
    conn = port_db.root()
    try:
        yield conn
    finally:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                for table in TOUCHED:
                    cursor.execute(f"DELETE FROM `{table}`")  # noqa: S608 - fixed names
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            conn.commit()
        finally:
            conn.close()


@pytest.fixture
def worker(port_db: PortDatabase, root: Any) -> Iterator[WorkerConnection]:
    settings = load_env_settings(port_db.worker_env(WorkerPart.PART2), WorkerPart.PART2)
    connection = connect_worker(settings)
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


class Port:
    """The rows one run needs, seeded as the Backend would."""

    def __init__(self, root: Any) -> None:
        self.root = root
        self.request = seed_row(
            root,
            "berthing_requests",
            requested_terminal_id=TERMINAL,
            block_coefficient=0.7,
            source="MANUAL",
            submitted_by=1,
        )
        self.proposal = seed_row(
            root,
            "entry_window_proposals",
            berthing_request_id=self.request,  # its status is the loader's concern
        )
        self.berth = seed_row(
            root,
            "berths",
            code="SYN-B1",
            length=300,
            water_depth=15,
            depth_datum="LAT",
            max_vessel_loa=280,
        )
        seed_row(root, "berth_terminals", berth_id=self.berth, terminal_id=TERMINAL)
        self.pilot = seed_row(root, "users", username="synpilot", name="SYNTHETIC PILOT")
        seed_row(root, "pilot_profiles", user_id=self.pilot, pilot_rank="FIRST")
        self.tugs = tuple(
            seed_row(
                root,
                "tugboats",
                name=f"SYNTHETIC TUG {n}",
                tug_power=50,
                tug_power_unit="BOLLARD_PULL_TONNES",
            )
            for n in (1, 2)
        )
        for code, name in (
            (TERM_WAITING_TIME, "Vessel waiting time"),
            (TERM_RESOURCE_COST, "Resource cost"),
        ):
            seed_row(root, "objective_terms", code=code, name=name)
        self.template = seed_row(
            root,
            "rationale_templates",
            code="SYNTHETIC_BEST",
            version=1,
            template_text="SYNTHETIC {vessel} at {berth}.",
        )
        model = seed_row(
            root, "ml_models", model_key="M2_SERVICE_TIME", algorithm_family="LightGBM"
        )
        self.model_version = seed_row(
            root,
            "ml_model_versions",
            ml_model_id=model,
            version_no=1,
            status="CHALLENGER",
            artifact_path="M2_SERVICE_TIME/v1/model.bin",
            trained_at="2026-11-01 00:00:00",
        )
        self.run = seed_row(
            root,
            "solver_runs",
            trigger_type="NEW_REQUEST",
            status="RUNNING",
            solver_version="pending",
            queued_at="2026-11-09 11:59:00",
            started_at="2026-11-09 11:59:30",
            horizon_start="2026-11-09 00:00:00",
            horizon_end="2026-11-16 00:00:00",
        )

    def option(self, rank: int, offset_hours: int) -> PlannedOption:
        start = H0 + timedelta(hours=offset_hours)
        option = Option(
            self.request, self.berth, start, start + timedelta(hours=4), self.pilot, self.tugs
        )
        return PlannedOption(rank, option, Decimal("750.0000"), TERMS)

    def outcome(self, purpose: str = "INITIAL") -> SolveOutcome:
        options = (self.option(1, 0), self.option(2, 1))
        request = RequestOutcome(self.request, RequestResult.SOLVED, purpose, options, ())
        return SolveOutcome(
            RunOutcome.SOLVED,
            "OPTIMAL",
            "AI",
            None,
            None,
            (request,),
            Decimal("750.0000"),
            123,
            "ortools SYNTHETIC",
            (),
        )

    def recommendation(self, status: str, purpose: str = "INITIAL") -> int:
        return seed_row(
            self.root,
            "recommendations",
            berthing_request_id=self.request,
            terminal_id=TERMINAL,
            entry_window_proposal_id=self.proposal,
            status=status,
            purpose=purpose,
            generated_at="2026-11-08 09:00:00",
        )


def _plan(port: Port, worker: WorkerConnection, outcome: SolveOutcome) -> Any:
    catalog = read_template_catalog(worker)
    template = catalog.require("SYNTHETIC_BEST")
    rationales = [
        OptionRationale(
            port.request,
            o.rank,
            objective_factors(o.terms),
            template,
            {"vessel": "SYNTHETIC VESSEL", "berth": "SYN-B1"},
        )
        for o in outcome.requests[0].options
    ]
    estimate = OptionEstimate("FORMULA", Decimal("4.00"), None, Decimal("0.250"))
    current = read_current_versions(worker, [port.request])
    worker.rollback()  # end the read transaction; the write starts its own
    return plan_run(
        state_requests={port.request: TERMINAL},
        proposals={port.request: port.proposal},
        outcome=outcome,
        rationales=rationales,
        estimates={(port.request, o.rank): estimate for o in outcome.requests[0].options},
        term_ids=read_objective_term_ids(worker),
        constraint_type_ids={},
        current_versions=current,
        model_version_ids=(port.model_version,),
        generated_at=NOW,
    )


def _complete(port: Port, worker: WorkerConnection, outcome: SolveOutcome) -> Any:
    plan = _plan(port, worker, outcome)
    result = write_run(WorkerRepository(worker, WorkerPart.PART2, port.run), port.run, plan)
    spec = RUN_TABLES[JobType.PART2_SOLVE]
    assert write_done(worker, spec, port.run, result.outcome, result.run_columns, "test")
    worker.commit()
    return result


def _fetch(root: Any, query: str, *args: object) -> tuple[Any, ...]:
    root.commit()  # a fresh snapshot
    with root.cursor() as cursor:
        cursor.execute(query, args)
        return tuple(cursor.fetchall())


def test_a_first_recommendation_is_written_and_fully_traceable(
    root: Any, worker: WorkerConnection
) -> None:
    port = Port(root)
    _complete(port, worker, port.outcome())

    [(rec_id, status, source, purpose, run_id, proposal)] = _fetch(
        root,
        "SELECT id, status, source, purpose, solver_run_id, entry_window_proposal_id "
        "FROM recommendations",
    )
    assert (status, source, purpose, run_id, proposal) == (
        "PENDING_REVIEW",
        "AI",
        "INITIAL",
        port.run,
        port.proposal,
    )
    options = _fetch(
        root,
        "SELECT id, option_rank, service_time_method, service_time_p50_hours, delay_risk, "
        "objective_score, rationale_template_id, rationale_params FROM recommendation_options "
        "WHERE recommendation_id = %s ORDER BY option_rank",
        rec_id,
    )
    assert [o[1] for o in options] == [1, 2]  # uq_ro_rank
    assert options[0][2:7] == (
        "FORMULA",
        Decimal("4.00"),
        Decimal("0.250"),
        Decimal("750.0000"),
        port.template,
    )
    assert json.loads(options[0][7]) == {"vessel": "SYNTHETIC VESSEL", "berth": "SYN-B1"}
    option_ids = [o[0] for o in options]
    tugs = _fetch(
        root, "SELECT option_id, tugboat_id FROM recommendation_option_tugs ORDER BY 1, 2"
    )
    assert tugs == tuple((o, t) for o in option_ids for t in port.tugs)
    factors = _fetch(
        root,
        "SELECT option_id, factor_type, factor_value, display_order FROM "
        "recommendation_rationale_factors ORDER BY option_id, display_order",
    )
    assert factors[:2] == (
        (option_ids[0], "OBJECTIVE_TERM", Decimal("500.0000"), 1),
        (option_ids[0], "OBJECTIVE_TERM", Decimal("250.0000"), 2),
    )
    [(run_status, value, ms, version, detail)] = _fetch(
        root,
        "SELECT status, objective_value, solve_time_ms, solver_version, result_detail "
        "FROM solver_runs WHERE id = %s",
        port.run,
    )
    assert (run_status, value, ms, version) == (
        "OPTIMAL",
        Decimal("750.0000"),
        123,
        "ortools SYNTHETIC",
    )
    assert json.loads(detail)["requests"][0]["recommendation_id"] == rec_id
    assert _fetch(
        root, "SELECT solver_run_id, model_version_id FROM solver_run_model_versions"
    ) == ((port.run, port.model_version),)


@pytest.mark.parametrize("status", ["PENDING_REVIEW", "MODIFIED_BY_STAFF"])
def test_a_regenerate_is_refused_and_the_previous_version_stays_current(
    root: Any, worker: WorkerConnection, status: str
) -> None:
    port = Port(root)
    previous = port.recommendation(status)
    with pytest.raises(JobError, match="INT-B11"):
        _plan(port, worker, port.outcome())

    assert _fetch(root, "SELECT id, status FROM recommendations") == ((previous, status),)
    assert _fetch(root, "SELECT COUNT(*) FROM recommendation_options") == ((0,),)


def test_without_the_check_the_schema_would_refuse_the_insert(
    root: Any, worker: WorkerConnection
) -> None:
    """Why the check exists (INT-B11): `uq_rec_active` rejects a second current INITIAL row."""
    port = Port(root)
    port.recommendation("PENDING_REVIEW")
    repo = WorkerRepository(worker, WorkerPart.PART2, port.run)
    with pytest.raises(sa.exc.IntegrityError, match="uq_rec_active"):
        repo.insert(
            "recommendations",
            {
                "solver_run_id": port.run,
                "berthing_request_id": port.request,
                "terminal_id": TERMINAL,
                "entry_window_proposal_id": port.proposal,
                "status": "PENDING_REVIEW",
                "source": "AI",
                "purpose": "INITIAL",
                "generated_at": NOW,
            },
        )


def test_a_delay_replan_proposal_is_written_next_to_the_confirmed_version(
    root: Any, worker: WorkerConnection
) -> None:
    port = Port(root)
    confirmed = port.recommendation("CONFIRMED")
    _complete(port, worker, port.outcome(purpose="DELAY_REPLAN"))

    rows = _fetch(root, "SELECT id, status, purpose FROM recommendations ORDER BY id")
    assert rows[0] == (confirmed, "CONFIRMED", "INITIAL")  # untouched
    assert rows[1][1:] == ("PENDING_REVIEW", "DELAY_REPLAN")
