"""Recommendation persistence (AI-058). Port values are SYNTHETIC (B2 builders)."""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from common.config import ConfigurationError
from common.runtime.errors import ErrorCategory, JobError
from part2.filter import BindingConstraint, Kind
from part2.outcomes import SolveOutcome, handle_solve
from part2.persist import (
    OptionEstimate,
    PersistError,
    RunPlan,
    plan_run,
    request_facts,
    result_detail,
    write_run,
)
from part2.rationale import RationaleTemplate, TemplateCatalog, build_rationales
from part2.solver import TERM_RESOURCE_COST, TERM_WAITING_TIME
from part2.state.model import PortState
from tests.unit.part2.filter.builders import REQUEST, TERMINAL, context, request, state
from tests.unit.part2.solver.test_cpsat import FOUR_HOURS, SETTINGS, two_requests
from tests.unit.part2.test_outcomes import timed_out

NOW = datetime(2026, 1, 5, 12, tzinfo=UTC)
TERMS = {TERM_WAITING_TIME: 501, TERM_RESOURCE_COST: 502}
FORMULA = OptionEstimate("FORMULA", Decimal("4.00"), None, Decimal("0.250"))
RUN_ID = 77


def estimates(outcome: SolveOutcome, estimate: OptionEstimate = FORMULA) -> dict[Any, Any]:
    return {(r.request_id, o.rank): estimate for r in outcome.requests for o in r.options}


def plan(outcome: SolveOutcome, port: PortState | None = None, **changes: Any) -> RunPlan:
    port = port or two_requests()
    terminals, proposals = request_facts(port, [r.request_id for r in outcome.requests])
    values: dict[str, Any] = {
        "state_requests": terminals,
        "proposals": proposals,
        "outcome": outcome,
        "rationales": build_rationales(port, outcome),
        "estimates": estimates(outcome),
        "term_ids": TERMS,
        "constraint_type_ids": {},
        "current_versions": {},
        "model_version_ids": (),
        "generated_at": NOW,
    }
    values.update(changes)
    return plan_run(**values)


def solved() -> SolveOutcome:
    return handle_solve(two_requests(), [REQUEST], context(), FOUR_HOURS, SETTINGS)


def fifo() -> SolveOutcome:
    return handle_solve(
        two_requests(), [REQUEST], context(), FOUR_HOURS, SETTINGS, solve_fn=timed_out
    )


def infeasible() -> SolveOutcome:
    port = state(requests=(request(loa=Decimal("400.00")),))
    return handle_solve(port, [REQUEST], context(), FOUR_HOURS, SETTINGS)


class FakeRepo:
    def __init__(self) -> None:
        self.rows: list[tuple[str, dict[str, object]]] = []
        self._ids = iter(range(900, 10_000))

    def insert(self, table: str, row: dict[str, object]) -> int:
        self.rows.append((table, dict(row)))
        return next(self._ids)

    def insert_many(self, table: str, rows: list[dict[str, object]]) -> None:
        self.rows.extend((table, dict(row)) for row in rows)

    def table(self, name: str) -> list[dict[str, object]]:
        return [row for table, row in self.rows if table == name]


# --- the plan --------------------------------------------------------------------------------


def test_a_solved_request_gets_one_pending_recommendation_with_ranked_options() -> None:
    outcome = solved()
    run = plan(outcome)

    [rec] = run.recommendations
    assert rec.values == {
        "solver_run_id": None,
        "berthing_request_id": REQUEST,
        "terminal_id": TERMINAL,
        "entry_window_proposal_id": REQUEST,  # builders: proposal id = request id
        "status": "PENDING_REVIEW",
        "source": "AI",
        "purpose": "INITIAL",
        "generated_at": NOW,
    }
    planned = outcome.requests[0].options
    assert [o.values["option_rank"] for o in rec.options] == [o.rank for o in planned]
    first = rec.options[0]
    assert first.values["berth_id"] == planned[0].option.berth_id
    assert first.values["planned_start"] == planned[0].option.start
    assert first.values["objective_score"] == planned[0].objective_score
    assert first.values["service_time_method"] == "FORMULA"
    assert first.values["service_time_p90_hours"] is None
    assert (first.values["pilot_start"], first.values["pilot_end"]) == (None, None)
    assert first.tug_ids == tuple(sorted(planned[0].option.tug_ids))
    assert {f["objective_term_id"] for f in first.factors} == {501, 502}
    assert all(f["constraint_type_id"] is None for f in first.factors)


def test_fifo_options_are_source_fifo_with_no_score_and_no_factor() -> None:
    run = plan(fifo())
    [rec] = run.recommendations
    assert rec.values["source"] == "FIFO"
    assert [(o.values["objective_score"], o.factors) for o in rec.options] == [(None, ())]


def test_an_infeasible_run_writes_no_recommendation() -> None:
    assert plan(infeasible()).recommendations == ()


def test_a_delay_replan_request_is_written_with_its_purpose() -> None:
    outcome = handle_solve(
        two_requests(), [REQUEST], context(), FOUR_HOURS, SETTINGS, replan_request_ids=[REQUEST]
    )
    run = plan(outcome, current_versions={REQUEST: "CONFIRMED"})
    assert run.recommendations[0].values["purpose"] == "DELAY_REPLAN"


# --- regenerate: INT-B11 -------------------------------------------------------------------


@pytest.mark.parametrize("status", ["PENDING_REVIEW", "MODIFIED_BY_STAFF"])
def test_a_request_with_a_current_version_is_refused_before_any_write(status: str) -> None:
    with pytest.raises(JobError) as caught:
        plan(solved(), current_versions={REQUEST: status})
    assert caught.value.category is ErrorCategory.PRECONDITION_FAILED
    assert "INT-B11" in caught.value.message and status in caught.value.message


def test_a_confirmed_request_may_only_be_replanned() -> None:
    with pytest.raises(JobError, match="only REPLAN"):
        plan(solved(), current_versions={REQUEST: "CONFIRMED"})


def test_a_request_without_options_is_not_refused_for_its_current_version() -> None:
    assert plan(infeasible(), current_versions={REQUEST: "PENDING_REVIEW"}).recommendations == ()


# --- schema checks before the write ---------------------------------------------------------


@pytest.mark.parametrize(
    ("estimate", "message"),
    [
        (OptionEstimate("FORMULA", Decimal(0), None, None), "p50"),
        (OptionEstimate("FORMULA", Decimal("4.001"), None, None), "p50"),
        (OptionEstimate("FORMULA", Decimal(10000), None, None), "p50"),
        (OptionEstimate("ML", Decimal("4.00"), None, None), "exactly for ML"),
        (OptionEstimate("FORMULA", Decimal("4.00"), Decimal("5.00"), None), "exactly for ML"),
        (OptionEstimate("ML", Decimal("4.00"), Decimal("3.00"), None), "≥ P50"),
        (OptionEstimate("FORMULA", Decimal("4.00"), None, Decimal("1.5")), "delay_risk"),
        (OptionEstimate("FORMULA", Decimal("4.00"), None, Decimal("0.1234")), "delay_risk"),
        (OptionEstimate("MANUAL", Decimal("4.00"), None, None), "service_time_method"),
    ],
)
def test_option_checks_mirror_chk_ro_values_and_chk_ro_p90(
    estimate: OptionEstimate, message: str
) -> None:
    outcome = solved()
    with pytest.raises(PersistError, match=message):
        plan(outcome, estimates=estimates(outcome, estimate))


def test_an_ml_estimate_with_p90_is_accepted() -> None:
    outcome = solved()
    ml = OptionEstimate("ML", Decimal("4.00"), Decimal("5.50"), None)
    first = plan(outcome, estimates=estimates(outcome, ml)).recommendations[0].options[0]
    assert first.values["service_time_p90_hours"] == Decimal("5.50")


def test_ranks_must_run_from_one() -> None:
    outcome = solved()
    request_outcome = outcome.requests[0]
    shifted = tuple(replace(o, rank=o.rank + 1) for o in request_outcome.options)
    broken = replace(outcome, requests=(replace(request_outcome, options=shifted),))
    with pytest.raises(PersistError):
        plan(broken)


def test_more_than_three_options_are_refused() -> None:
    outcome = solved()
    request_outcome = outcome.requests[0]
    first = request_outcome.options[0]
    four = tuple(replace(first, rank=n) for n in range(1, 5))
    broken = replace(outcome, requests=(replace(request_outcome, options=four),))
    keys = {(REQUEST, n): FORMULA for n in range(1, 5)}
    rationales = [
        replace(build_rationales(two_requests(), outcome)[0], rank=n) for n in range(1, 5)
    ]
    with pytest.raises(PersistError, match="n ≤ 3"):
        plan(broken, estimates=keys, rationales=rationales)


def test_rationales_and_estimates_must_cover_every_option() -> None:
    outcome = solved()
    with pytest.raises(PersistError, match="rationales"):
        plan(outcome, rationales=build_rationales(two_requests(), outcome)[:1])
    with pytest.raises(PersistError, match="estimates"):
        plan(outcome, estimates={})


def test_an_unseeded_objective_term_is_a_configuration_error() -> None:
    with pytest.raises(ConfigurationError, match="RESOURCE_COST"):
        plan(solved(), term_ids={TERM_WAITING_TIME: 501})


def test_a_missing_confirmed_proposal_is_refused() -> None:
    with pytest.raises(PersistError, match="confirmed proposal"):
        plan(solved(), proposals={})


def test_naive_time_and_long_solver_version_are_refused() -> None:
    with pytest.raises(PersistError, match="timezone-aware"):
        plan(solved(), generated_at=NOW.replace(tzinfo=None))
    with pytest.raises(PersistError, match="solver_version"):
        plan(replace(solved(), solver_version="x" * 41))


def test_the_template_link_and_params_are_carried_to_the_option() -> None:
    outcome = solved()
    template = RationaleTemplate(7, "SYNTHETIC_BEST", 1, "SYNTHETIC {vessel} at {berth}.")
    rationales = build_rationales(
        two_requests(), outcome, TemplateCatalog([template]), lambda *_: "SYNTHETIC_BEST"
    )
    first = plan(outcome, rationales=rationales).recommendations[0].options[0]
    assert first.values["rationale_template_id"] == 7
    assert first.values["rationale_params"] == rationales[0].params


# --- the write and result_detail ------------------------------------------------------------


def test_write_links_every_row_and_fills_the_recommendation_id() -> None:
    repo = FakeRepo()
    result = write_run(repo, RUN_ID, plan(solved(), model_version_ids=(5, 5, 3)))  # type: ignore[arg-type]

    [rec] = repo.table("recommendations")
    assert rec["solver_run_id"] == RUN_ID
    options = repo.table("recommendation_options")
    assert {o["recommendation_id"] for o in options} == {900}
    option_ids = set(range(901, 901 + len(options)))
    assert {t["option_id"] for t in repo.table("recommendation_option_tugs")} <= option_ids
    assert {f["option_id"] for f in repo.table("recommendation_rationale_factors")} == option_ids
    assert repo.table("solver_run_model_versions") == [
        {"solver_run_id": RUN_ID, "model_version_id": 3},
        {"solver_run_id": RUN_ID, "model_version_id": 5},
    ]
    assert result.outcome == "SOLVED" and result.error_category is None
    columns = dict(result.run_columns)
    assert columns["status"] == "OPTIMAL"
    detail: Any = columns["result_detail"]
    assert detail["requests"][0]["recommendation_id"] == 900
    assert detail["requests"][0]["options_count"] == len(options)


def test_write_of_a_fifo_run_reports_its_error_category() -> None:
    result = write_run(FakeRepo(), RUN_ID, plan(fifo()))  # type: ignore[arg-type]
    assert result.outcome == "FIFO_FALLBACK"
    assert result.error_category is ErrorCategory.TIMEOUT
    assert dict(result.run_columns)["status"] == "ERROR"


def test_write_of_an_infeasible_run_inserts_nothing() -> None:
    repo = FakeRepo()
    result = write_run(repo, RUN_ID, plan(infeasible()))  # type: ignore[arg-type]
    assert repo.rows == []
    detail: Any = dict(result.run_columns)["result_detail"]
    assert result.outcome == "NO_FEASIBLE_PLAN"
    assert detail["requests"][0]["recommendation_id"] is None
    assert detail["requests"][0]["binding_constraints"]


@pytest.mark.parametrize(
    ("code", "written"),
    [
        ("PILOT_RANK_LIMIT", "PILOT_UNAVAILABLE"),
        ("TUG_COUNT", "TUG_UNAVAILABLE"),
        ("MAX_LOA", "MAX_LOA"),
    ],
)
def test_result_detail_keeps_structural_codes_to_ct10_v11(code: str, written: str) -> None:
    outcome = infeasible()
    reason = BindingConstraint(Kind.STRUCTURAL, code, "SYNTHETIC detail")
    changed = replace(outcome.requests[0], binding_constraints=(reason,))
    detail: Any = result_detail(replace(outcome, requests=(changed,)), {})
    [binding] = detail["requests"][0]["binding_constraints"]
    assert binding == {
        "kind": "STRUCTURAL",
        "constraint_type_code": written,
        "detail": "SYNTHETIC detail",
    }


def test_safety_codes_pass_and_an_unknown_structural_code_is_refused() -> None:
    outcome = infeasible()
    safety = BindingConstraint(Kind.SAFETY, "MAX_WIND_KN", "SYNTHETIC")
    unknown = BindingConstraint(Kind.STRUCTURAL, "SOMETHING_NEW", "SYNTHETIC")
    ok = replace(outcome.requests[0], binding_constraints=(safety,))
    detail: Any = result_detail(replace(outcome, requests=(ok,)), {})
    assert detail["requests"][0]["binding_constraints"][0]["constraint_type_code"] == "MAX_WIND_KN"
    bad = replace(outcome.requests[0], binding_constraints=(unknown,))
    with pytest.raises(PersistError, match="CT-10 v1.1"):
        result_detail(replace(outcome, requests=(bad,)), {})
