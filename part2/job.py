"""The `queue:part2` PART2_SOLVE handler (AI-059): one run from the C-02 triggers to its rows.

CT-10 and the AI-011 runtime. The runtime claims the run (QUEUED → RUNNING, so a re-delivered
message is not handled twice), retries technical errors, and commits the handler's writes with the
guarded `solver_runs` update, or rolls everything back and sends a FAILED C-06. The handler:

1. reads the scope from the trigger entries (`part2.replan`), the run's horizon, and checks each
   REPLAN entry names its request's CONFIRMED plan;
2. loads the AI-050 snapshot, the B2 context (AI-060 loader) and the B3 inputs;
3. times each request with B3 (AI-052); a request B3 can't time is `NO_FEASIBLE_PLAN` with
   `ENTRY_WINDOW` "No service time (B3): <reason>", as AI-056 does (CT-10 v1.2 `NOT_SOLVED` is only
   Proposed);
4. pins the started components of REPLAN requests and solves with fallback (AI-056, B5);
5. builds the rationale (AI-057) and the B4 level per option (AI-053), and writes through AI-058,
   which refuses a regenerate before any write (INT-B11).

B4 gets no forecast: no forecast feed exists yet (AI-020, AI-021) and no rule says which
`forecast_runs` row a solve uses, so the level is NULL under DEC-21 rule 5 ("forecast missing").
"""

import importlib.metadata
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Final

from common.config import WorkerPart
from common.db.connection import core_of
from common.db.repository import WorkerRepository
from common.runtime.envelope import JobType
from common.runtime.errors import ErrorCategory, JobError
from common.runtime.worker import JobContext, JobResult, WorkerDefinition
from part2.context import ContextError, load_filter_context
from part2.delay_risk import assess_delay_risk
from part2.filter import BindingConstraint, Code, Kind
from part2.filter.pairing import truncate
from part2.inputs import (
    as_duration,
    check_replan_plans,
    read_run_horizon,
    read_service_inputs,
    service_times,
)
from part2.outcomes import (
    PURPOSE_DELAY_REPLAN,
    PURPOSE_INITIAL,
    RequestOutcome,
    RequestResult,
    RunOutcome,
    SolveOutcome,
    handle_solve,
)
from part2.persist import (
    OptionEstimate,
    plan_run,
    read_current_versions,
    read_objective_term_ids,
    read_template_catalog,
    request_facts,
    write_run,
)
from part2.rationale import build_rationales
from part2.replan import pins_for, scope_from_payload
from part2.solver import SolverSettings
from part2.solver.model import (
    KEY_EQUIVALENCE,
    KEY_OPTIONS,
    KEY_TIME_LIMIT,
    KEY_WEIGHT_RESOURCE,
    KEY_WEIGHT_WAITING,
)
from part2.state.snapshot import load_port_state

WORKER_VERSION: Final = "part2-0.1.0"
KEY_MAX_FORECAST_AGE: Final = "part1_stored_data_max_age_hours"  # CT-18 §4, DEC-21 rule 5
USED_SETTING_KEYS: Final = (
    KEY_TIME_LIMIT,
    KEY_OPTIONS,
    KEY_EQUIVALENCE,
    KEY_WEIGHT_WAITING,
    KEY_WEIGHT_RESOURCE,
    KEY_MAX_FORECAST_AGE,
)


def handler(context: JobContext) -> JobResult:
    run_id = context.envelope.run_id
    if run_id is None:  # the envelope schema requires it for PART2_SOLVE
        raise JobError(ErrorCategory.INVALID_ENVELOPE, "PART2_SOLVE needs a run_id")
    scope = scope_from_payload(context.envelope.payload)
    connection = context.connection
    core = core_of(connection)
    try:
        horizon_start, horizon_end = read_run_horizon(connection, run_id)
        check_replan_plans(connection, scope.replan_plans)
    finally:
        core.rollback()  # load_port_state needs no open transaction

    state = load_port_state(
        connection, scope.request_ids, horizon_start=horizon_start, horizon_end=horizon_end
    )
    found = {r.request_id for r in state.requests}
    missing = sorted(set(scope.request_ids) - found)
    if missing:
        raise JobError(
            ErrorCategory.PRECONDITION_FAILED, f"requests {missing} were not found with a vessel"
        )
    try:
        filter_context = load_filter_context(connection, state)
    except ContextError as error:
        raise JobError(ErrorCategory.DATA_UNAVAILABLE, str(error)) from error
    try:
        inputs = read_service_inputs(connection, scope.request_ids)
    finally:
        core.rollback()
    timed = service_times(state, inputs, filter_context.vessel_type_ids)

    durations: dict[int, timedelta] = {}
    unplanned: dict[int, str] = {}
    for request_id in scope.request_ids:
        result = timed.get(request_id)
        if result is None:
            unplanned[request_id] = "The request has no confirmed entry window"
        elif result.p50_hours is None:
            unplanned[request_id] = f"No service time (B3): {result.excluded_reason}"
        else:
            durations[request_id] = as_duration(result.p50_hours)
    replan = scope.replan_request_ids
    solved = None
    if durations:
        solved = handle_solve(
            state,
            durations,
            filter_context,
            durations,
            SolverSettings.from_port_settings(context.settings),
            replan_request_ids=replan & durations.keys(),
            pins=pins_for(state, replan & durations.keys()),
        )
    outcome = with_unplanned(solved, unplanned, replan)

    max_age = context.settings.get_int(KEY_MAX_FORECAST_AGE)
    estimates: dict[tuple[int, int], OptionEstimate] = {}
    for request in outcome.requests:
        for planned in request.options:
            service = timed[request.request_id]  # only timed requests reach the solve
            if service.p50_hours is None:
                raise JobError(ErrorCategory.INTERNAL_ERROR, "an option without a service time")
            risk = assess_delay_risk(
                window_start=planned.option.start,
                window_end=planned.option.end,
                forecast=None,
                max_forecast_age_hours=max_age,
                congestion=None,
                storm_days=None,
                time_zone=state.time_zone,
            )
            estimates[(request.request_id, planned.rank)] = OptionEstimate(
                service.method, service.p50_hours, service.p90_hours, risk.code
            )

    # The plan may have changed since the snapshot; the write transaction checks it again, so a
    # REPLAN whose pins were read from a plan that is no longer CONFIRMED is never written.
    check_replan_plans(connection, scope.replan_plans)
    terminals, proposals = request_facts(state, scope.request_ids)
    plan = plan_run(
        state_requests=terminals,
        proposals=proposals,
        outcome=outcome,
        rationales=build_rationales(state, outcome, read_template_catalog(connection)),
        estimates=estimates,
        term_ids=read_objective_term_ids(connection),
        constraint_type_ids={c.code: c.id for c in filter_context.constraint_types},
        current_versions=read_current_versions(connection, scope.request_ids),
        model_version_ids=(),  # Phase 1 uses no ML model version (no CHAMPION, OD-17)
        generated_at=datetime.now(UTC),
    )
    return write_run(WorkerRepository(connection, WorkerPart.PART2, run_id), run_id, plan)


def with_unplanned(
    solved: SolveOutcome | None, unplanned: Mapping[int, str], replan: frozenset[int]
) -> SolveOutcome:
    """The run's outcome with the requests that never reached the solve added as NO_FEASIBLE_PLAN
    (CT-10), each with its `ENTRY_WINDOW` detail text."""
    extra = tuple(
        RequestOutcome(
            request_id,
            RequestResult.NO_FEASIBLE_PLAN,
            PURPOSE_DELAY_REPLAN if request_id in replan else PURPOSE_INITIAL,
            (),
            (
                BindingConstraint(
                    Kind.STRUCTURAL,
                    Code.ENTRY_WINDOW,
                    truncate(detail),
                ),
            ),
        )
        for request_id, detail in sorted(unplanned.items())
    )
    if solved is None:
        return SolveOutcome(
            outcome=RunOutcome.NO_FEASIBLE_PLAN,
            solver_status="INFEASIBLE",
            source="AI",
            error_category=None,
            failure_message=None,
            requests=extra,
            objective_value=None,
            solve_time_ms=0,
            solver_version=f"ortools {importlib.metadata.version('ortools')}",
            flags=(),
        )
    if not extra:
        return solved
    requests = tuple(sorted((*solved.requests, *extra), key=lambda r: r.request_id))
    if solved.outcome is RunOutcome.FIFO_FALLBACK:
        return replace(solved, requests=requests)
    if not any(r.options for r in requests):
        return replace(
            solved,
            outcome=RunOutcome.NO_FEASIBLE_PLAN,
            solver_status="INFEASIBLE",
            requests=requests,
            objective_value=None,
        )
    return replace(solved, outcome=RunOutcome.PARTIALLY_SOLVED, requests=requests)


DEFINITION: Final = WorkerDefinition(
    JobType.PART2_SOLVE, handler, USED_SETTING_KEYS, WORKER_VERSION
)
