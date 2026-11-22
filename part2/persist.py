"""Recommendation persistence (AI-058): one PART2_SOLVE run's rows, written in one transaction.

`plan_run` is pure: it turns AI-056's `SolveOutcome`, AI-057's rationales and the B3/B4 estimates
into rows and checks them against the schema's CHECKs (`chk_ro_values`, `chk_ro_p90`,
`chk_ro_pilot_interval`, `uq_ro_rank`, `chk_rrf_kind`) before anything is sent. `write_run` inserts
them through `WorkerRepository` and returns the `JobResult`; the shared runtime (AI-011) commits
them together with the guarded `solver_runs` update, or rolls everything back (CT-08, NFR-REL-5).

Ownership (DEC-02, CT-15): the worker inserts `recommendations` (always `PENDING_REVIEW`), options,
tugs, factors and `solver_run_model_versions`, and completes its own `solver_runs` row. It never
changes another recommendation or a `berthing_requests` status: the Backend does that on C-06.

**Regenerate (INT-B11).** `uq_rec_active` allows one current INITIAL version per request, and only
the Backend may set the previous one to `REPLACED`, after C-06 (DEC-02, CT-10). So a request that
already has a current INITIAL version cannot get a new one written. `plan_run` refuses such a run
with `PRECONDITION_FAILED` before writing anything, so the previous version stays current. First
recommendations and `DELAY_REPLAN` proposals (`active_key` NULL) are not affected.

**CT-10 v1.1 codes.** Approved CT-10 v1.1 closes the STRUCTURAL `binding_constraints` list. B2 can
also give `PILOT_RANK_LIMIT` and `TUG_COUNT`, which are only Proposed (INT-B1); they are written
as the approved `PILOT_UNAVAILABLE` and `TUG_UNAVAILABLE`, with B2's own text kept in `detail`.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Final

import sqlalchemy as sa

from common.config import ConfigurationError
from common.db.connection import core_of
from common.db.repository import WorkerRepository
from common.db.tables import OBJECTIVE_TERMS, RATIONALE_TEMPLATES, RECOMMENDATIONS
from common.runtime.errors import ErrorCategory, JobError
from common.runtime.runs import Connection
from common.runtime.worker import JobResult
from part2.filter.pairing import confirmed_window
from part2.outcomes import SOURCE_FIFO, PlannedOption, RequestOutcome, RequestResult, SolveOutcome
from part2.rationale import FactorType, OptionRationale, RationaleTemplate, TemplateCatalog
from part2.state.model import PortState

PENDING_REVIEW: Final = "PENDING_REVIEW"
INITIAL: Final = "INITIAL"
METHODS: Final = frozenset({"FORMULA", "ML"})
MAX_OPTIONS: Final = 3  # CT-10 `options_count` 1 to 3 (DEC-23)
SOLVER_VERSION_LENGTH: Final = 40  # `solver_runs.solver_version` varchar(40)

# CT-10 v1.1 (approved): the closed STRUCTURAL list for `binding_constraints`.
CT10_STRUCTURAL: Final = frozenset(
    {
        "MAX_LOA",
        "MAX_DRAFT",
        "TERMINAL_COMPATIBILITY",
        "BERTH_UNAVAILABLE",
        "BERTH_OCCUPIED",
        "TUG_UNAVAILABLE",
        "PILOT_UNAVAILABLE",
        "ENTRY_WINDOW",
    }
)
# B2 codes outside v1.1 (CT-10 Proposed change, INT-B1) → the approved code they fall under.
PROPOSED_TO_APPROVED: Final = {
    "PILOT_RANK_LIMIT": "PILOT_UNAVAILABLE",
    "TUG_COUNT": "TUG_UNAVAILABLE",
}

_P50_STEP: Final = Decimal("0.01")  # decimal(6,2)
_P50_LIMIT: Final = Decimal("10000")
_RISK_STEP: Final = Decimal("0.001")  # decimal(4,3)
_SCORE_STEP: Final = Decimal("0.0001")  # decimal(14,4)
_SCORE_LIMIT: Final = Decimal("1e10")


class PersistError(ValueError):
    """The inputs disagree with each other or with a schema CHECK: a defect upstream."""


@dataclass(frozen=True)
class OptionEstimate:
    """B3 and B4 for one option: `service_time_method`, P50 / P90 hours, `delay_risk`."""

    service_time_method: str
    p50_hours: Decimal
    p90_hours: Decimal | None
    delay_risk: Decimal | None


@dataclass(frozen=True)
class OptionRow:
    """One `recommendation_options` row with its tugs and factor rows (ids resolved)."""

    values: Mapping[str, object]  # every column but `id` and `recommendation_id`
    tug_ids: tuple[int, ...]
    factors: tuple[Mapping[str, object], ...]  # every column but `id` and `option_id`


@dataclass(frozen=True)
class RecommendationRow:
    request_id: int
    values: Mapping[str, object]  # every column but `id`
    options: tuple[OptionRow, ...]


@dataclass(frozen=True)
class RunPlan:
    outcome: SolveOutcome
    recommendations: tuple[RecommendationRow, ...]
    model_version_ids: tuple[int, ...]


# --- reads ----------------------------------------------------------------------------------


def read_objective_term_ids(connection: Connection) -> dict[str, int]:
    """`objective_terms.code` → id (CT-18 seed)."""
    rows = core_of(connection).execute(sa.select(OBJECTIVE_TERMS.c.code, OBJECTIVE_TERMS.c.id))
    return {row.code: int(row.id) for row in rows}


def read_template_catalog(connection: Connection) -> TemplateCatalog:
    """The active `rationale_templates` rows as AI-057's catalogue."""
    t = RATIONALE_TEMPLATES
    rows = core_of(connection).execute(
        sa.select(t.c.id, t.c.code, t.c.version, t.c.template_text).where(t.c.is_active == 1)
    )
    return TemplateCatalog(
        RationaleTemplate(int(r.id), r.code, int(r.version), r.template_text) for r in rows
    )


def read_current_versions(connection: Connection, request_ids: Sequence[int]) -> dict[int, str]:
    """Request id → status of its current INITIAL recommendation (`active_key` not NULL)."""
    if not request_ids:
        return {}
    r = RECOMMENDATIONS
    rows = core_of(connection).execute(
        sa.select(r.c.berthing_request_id, r.c.status).where(
            r.c.berthing_request_id.in_(list(request_ids)), r.c.active_key.is_not(None)
        )
    )
    return {int(row.berthing_request_id): str(row.status) for row in rows}


# --- plan -----------------------------------------------------------------------------------


def plan_run(
    *,
    state_requests: Mapping[int, int],
    proposals: Mapping[int, int],
    outcome: SolveOutcome,
    rationales: Sequence[OptionRationale],
    estimates: Mapping[tuple[int, int], OptionEstimate],
    term_ids: Mapping[str, int],
    constraint_type_ids: Mapping[str, int],
    current_versions: Mapping[int, str],
    model_version_ids: Sequence[int],
    generated_at: datetime,
) -> RunPlan:
    """The rows of one run, checked. Nothing is read or written.

    - `state_requests`: request id → `requested_terminal_id`; `proposals`: request id → the
      CONFIRMED `entry_window_proposals.id` (from the AI-050 snapshot, see `request_facts`).
    - `estimates` and `rationales` hold one entry per option, keyed by (request id, rank).
    - `current_versions`: from `read_current_versions`.
    """
    if generated_at.utcoffset() is None:
        raise PersistError("generated_at must be timezone-aware")
    if len(outcome.solver_version) > SOLVER_VERSION_LENGTH:
        raise PersistError(f"solver_version is longer than {SOLVER_VERSION_LENGTH}")
    by_option = {(r.request_id, r.rank): r for r in rationales}
    if len(by_option) != len(rationales):
        raise PersistError("two rationales for the same option")
    expected = {(r.request_id, o.rank) for r in outcome.requests for o in r.options}
    for name, keys in (("rationale", set(by_option)), ("estimate", set(estimates))):
        if keys != expected:
            raise PersistError(f"{name}s don't match the options: {sorted(keys ^ expected)}")

    written = [r for r in outcome.requests if r.options]
    _refuse_current_versions(written, current_versions)
    recommendations = []
    for request in sorted(written, key=lambda r: r.request_id):
        if request.outcome is RequestResult.NO_FEASIBLE_PLAN:
            raise PersistError(f"request {request.request_id} is NO_FEASIBLE_PLAN with options")
        terminal_id = state_requests.get(request.request_id)
        proposal_id = proposals.get(request.request_id)
        if terminal_id is None or proposal_id is None:
            raise PersistError(f"request {request.request_id}: no terminal or confirmed proposal")
        ranks = [o.rank for o in request.options]
        if ranks != list(range(1, len(ranks) + 1)) or len(ranks) > MAX_OPTIONS:  # uq_ro_rank
            raise PersistError(f"request {request.request_id}: ranks must be 1..n, n ≤ 3: {ranks}")
        options = []
        for planned in request.options:
            key = (request.request_id, planned.rank)
            if (outcome.source == SOURCE_FIFO) != (planned.objective_score is None):
                raise PersistError(f"option {key}: FIFO options and only they have no score")
            options.append(
                OptionRow(
                    values=_option_values(planned, terminal_id, estimates[key], by_option[key]),
                    tug_ids=tuple(sorted(set(planned.option.tug_ids))),
                    factors=_factor_values(by_option[key], term_ids, constraint_type_ids),
                )
            )
        recommendations.append(
            RecommendationRow(
                request.request_id,
                {
                    "solver_run_id": None,  # set by write_run
                    "berthing_request_id": request.request_id,
                    "terminal_id": terminal_id,
                    "entry_window_proposal_id": proposal_id,
                    "status": PENDING_REVIEW,
                    "source": outcome.source,
                    "purpose": request.purpose,
                    "generated_at": generated_at,
                },
                tuple(options),
            )
        )
    return RunPlan(outcome, tuple(recommendations), tuple(sorted(set(model_version_ids))))


def request_facts(
    state: PortState, request_ids: Sequence[int]
) -> tuple[dict[int, int], dict[int, int]]:
    """`state_requests` and `proposals` for `plan_run`, from the AI-050 snapshot."""
    terminals = {r.request_id: r.requested_terminal_id for r in state.requests}
    proposals = {}
    for request_id in request_ids:
        window = confirmed_window(state, request_id)
        if window is not None:
            proposals[request_id] = window.proposal_id
    return terminals, proposals


def _refuse_current_versions(
    written: Sequence[RequestOutcome], current_versions: Mapping[int, str]
) -> None:
    blocked = []
    for request in written:
        request_id = request.request_id
        if request.purpose != INITIAL or request_id not in current_versions:
            continue
        status = current_versions[request_id]
        if status == "CONFIRMED":
            blocked.append(
                f"request {request_id} has a CONFIRMED version; only REPLAN may re-solve it (CT-10)"
            )
        else:
            blocked.append(
                f"request {request_id} already has a current INITIAL version ({status}); writing "
                "a new one needs the previous one REPLACED first, which only the Backend may do "
                "after C-06 (uq_rec_active, DEC-02; INT-B11)"
            )
    if blocked:
        raise JobError(ErrorCategory.PRECONDITION_FAILED, "; ".join(blocked))


def _option_values(
    planned: PlannedOption,
    terminal_id: int,
    estimate: OptionEstimate,
    rationale: OptionRationale,
) -> dict[str, object]:
    option, rank, score = planned.option, planned.rank, planned.objective_score
    key = f"option {rank} of request {option.request_id}"
    if rank < 1 or option.end <= option.start:  # chk_ro_values
        raise PersistError(f"{key}: rank must be positive and the end after the start")
    _check_estimate(key, estimate)
    if score is not None and (score.quantize(_SCORE_STEP) != score or abs(score) >= _SCORE_LIMIT):
        raise PersistError(f"{key}: objective_score does not fit decimal(14,4): {score}")
    return {
        "terminal_id": terminal_id,
        "option_rank": rank,
        "berth_id": option.berth_id,
        "planned_start": option.start,
        "planned_end": option.end,
        "pilot_user_id": option.pilot_user_id,
        # NULL = the option's own interval (DEC-32 rule 4): no source gives job durations yet.
        "pilot_start": None,
        "pilot_end": None,
        "service_time_method": estimate.service_time_method,
        "service_time_p50_hours": estimate.p50_hours,
        "service_time_p90_hours": estimate.p90_hours,
        "delay_risk": estimate.delay_risk,
        "objective_score": score,
        "rationale_template_id": rationale.rationale_template_id,
        "rationale_params": rationale.params,
    }


def _check_estimate(key: str, estimate: OptionEstimate) -> None:
    p50, p90 = estimate.p50_hours, estimate.p90_hours
    if estimate.service_time_method not in METHODS:
        raise PersistError(f"{key}: service_time_method {estimate.service_time_method!r}")
    if not (Decimal(0) < p50 < _P50_LIMIT) or p50.quantize(_P50_STEP) != p50:
        raise PersistError(f"{key}: service_time_p50_hours must fit decimal(6,2), > 0: {p50}")
    if (estimate.service_time_method == "ML") != (p90 is not None):  # chk_ro_p90
        raise PersistError(f"{key}: service_time_p90_hours is set exactly for ML")
    if p90 is not None and (p90 < p50 or p90 >= _P50_LIMIT or p90.quantize(_P50_STEP) != p90):
        raise PersistError(f"{key}: service_time_p90_hours must fit decimal(6,2), ≥ P50: {p90}")
    risk = estimate.delay_risk
    if risk is not None and (
        not Decimal(0) <= risk <= Decimal(1) or risk.quantize(_RISK_STEP) != risk
    ):
        raise PersistError(f"{key}: delay_risk must be 0 to 1 with 3 decimals: {risk}")


def _factor_values(
    rationale: OptionRationale,
    term_ids: Mapping[str, int],
    constraint_type_ids: Mapping[str, int],
) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for factor in rationale.factors:
        if factor.factor_type is FactorType.OBJECTIVE_TERM:
            ids, column, other = term_ids, "objective_term_id", "constraint_type_id"
        else:
            ids, column, other = constraint_type_ids, "constraint_type_id", "objective_term_id"
        if factor.code not in ids:
            raise ConfigurationError(f"{column}: no seeded row with code {factor.code}")
        rows.append(
            {
                "factor_type": factor.factor_type.value,
                column: ids[factor.code],
                other: None,
                "factor_value": factor.factor_value,
                "display_order": factor.display_order,
            }
        )
    return tuple(rows)


# --- write ----------------------------------------------------------------------------------


def write_run(repo: WorkerRepository, run_id: int, plan: RunPlan) -> JobResult:
    """Insert the plan's rows and return the result whose run columns complete `solver_runs`."""
    recommendation_ids: dict[int, int] = {}
    for recommendation in plan.recommendations:
        rec_id = repo.insert("recommendations", {**recommendation.values, "solver_run_id": run_id})
        recommendation_ids[recommendation.request_id] = rec_id
        for option in recommendation.options:
            option_id = repo.insert(
                "recommendation_options", {**option.values, "recommendation_id": rec_id}
            )
            repo.insert_many(
                "recommendation_option_tugs",
                [
                    {
                        "option_id": option_id,
                        "tugboat_id": tug,
                        "planned_start": None,
                        "planned_end": None,
                    }
                    for tug in option.tug_ids
                ],
            )
            repo.insert_many(
                "recommendation_rationale_factors",
                [{**factor, "option_id": option_id} for factor in option.factors],
            )
    repo.insert_many(
        "solver_run_model_versions",
        [{"solver_run_id": run_id, "model_version_id": v} for v in plan.model_version_ids],
    )
    outcome = plan.outcome
    return JobResult(
        outcome=outcome.outcome.value,
        run_columns={
            "status": outcome.solver_status,
            "objective_value": outcome.objective_value,
            "solve_time_ms": outcome.solve_time_ms,
            "solver_version": outcome.solver_version,
            "result_detail": result_detail(outcome, recommendation_ids),
        },
        error_category=(
            None if outcome.error_category is None else ErrorCategory(outcome.error_category)
        ),
    )


def result_detail(
    outcome: SolveOutcome, recommendation_ids: Mapping[int, int]
) -> dict[str, object]:
    """AI-056's `result_detail` with `recommendation_id` filled and codes kept to CT-10 v1.1."""
    detail = outcome.result_detail()
    requests: list[dict[str, object]] = []
    items: list[Mapping[str, object]] = detail["requests"]  # type: ignore[assignment]
    for original in items:
        item = dict(original)
        item["recommendation_id"] = recommendation_ids.get(int(str(item["request_id"])))
        bindings: list[Mapping[str, object]] = item["binding_constraints"]  # type: ignore[assignment]
        item["binding_constraints"] = [_approved(b) for b in bindings]
        requests.append(item)
    return {**detail, "requests": requests}


def _approved(binding: Mapping[str, object]) -> dict[str, object]:
    if binding["kind"] != "STRUCTURAL":
        return dict(binding)
    code = str(binding["constraint_type_code"])
    code = PROPOSED_TO_APPROVED.get(code, code)
    if code not in CT10_STRUCTURAL:
        raise PersistError(f"STRUCTURAL code {code} is not in CT-10 v1.1")
    return {**binding, "constraint_type_code": code}
