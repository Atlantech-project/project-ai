"""The queue:validate handler and the shared B2 context loader (AI-060). SYNTHETIC data."""

from dataclasses import replace
from decimal import Decimal
from typing import Any

import pytest

from common.config import PortSettings
from common.runtime.envelope import Envelope, JobType
from common.runtime.errors import ErrorCategory, JobError
from common.runtime.worker import JobContext
from part2 import context as context_module
from part2.context import ContextError, tug_requirements
from part2.tugs import load_rules
from part2.validation import job
from tests.unit.part2.filter.builders import (
    OTHER_BERTH,
    REQUEST,
    context,
    option,
    request,
    state,
)


class _Core:
    def rollback(self) -> None:
        pass


def envelope(payload: dict[str, Any]) -> Envelope:
    return Envelope("1.0", JobType.VALIDATION, "j1", None, "2026-11-21T12:00:00Z", 41, payload)


def run(
    monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any], status: str = "PENDING_REVIEW"
) -> Any:
    monkeypatch.setattr(job, "core_of", lambda _c: _Core())
    monkeypatch.setattr(job, "read_option", lambda _c, _id: (option(), status))
    monkeypatch.setattr(job, "load_port_state", lambda *_a, **_k: state())
    monkeypatch.setattr(job, "load_filter_context", lambda _c, _s: context())
    return job.handler(JobContext(envelope(payload), PortSettings([]), object(), 0))  # type: ignore[arg-type]


BERTH_CHANGE = {
    "validation_type": "OVERRIDE",
    "subject_id": 9031,
    "proposed_change": {"changes": [{"component_type": "BERTH", "override_berth_id": OTHER_BERTH}]},
}


def test_valid_override_returns_the_c06_result(monkeypatch: pytest.MonkeyPatch) -> None:
    result = run(monkeypatch, BERTH_CHANGE)
    assert result.outcome == "VALID"
    assert result.completion_fields["validation_result"]["subject_id"] == 9031


def test_violation_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        **BERTH_CHANGE,
        "proposed_change": {
            "changes": [
                {"component_type": "TUG", "original_tugboat_id": 42, "override_tugboat_id": None}
            ]
        },
    }
    result = run(monkeypatch, payload)
    assert result.outcome == "VIOLATIONS"


@pytest.mark.parametrize("status", ["CONFIRMED", "REPLACED", "REJECTED"])
def test_recommendation_not_editable_is_a_precondition_failure(
    monkeypatch: pytest.MonkeyPatch, status: str
) -> None:
    with pytest.raises(JobError) as caught:
        run(monkeypatch, BERTH_CHANGE, status)
    assert caught.value.category is ErrorCategory.PRECONDITION_FAILED


def test_change_that_does_not_fit_is_a_precondition_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        **BERTH_CHANGE,
        "proposed_change": {
            "changes": [
                {"component_type": "TUG", "original_tugboat_id": 99, "override_tugboat_id": 43}
            ]
        },
    }
    with pytest.raises(JobError) as caught:
        run(monkeypatch, payload)
    assert caught.value.category is ErrorCategory.PRECONDITION_FAILED


def test_yard_adjustment_is_refused_until_ai067(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(JobError) as caught:
        run(
            monkeypatch,
            {"validation_type": "YARD_ADJUSTMENT", "subject_id": 1, "proposed_change": {}},
        )
    assert caught.value.category is ErrorCategory.CONFIGURATION_ERROR


def test_missing_tug_data_is_data_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(_c: Any, _s: Any) -> Any:
        raise ContextError("request 1: loa must be positive")

    monkeypatch.setattr(job, "core_of", lambda _c: _Core())
    monkeypatch.setattr(job, "read_option", lambda _c, _id: (option(), "PENDING_REVIEW"))
    monkeypatch.setattr(job, "load_port_state", lambda *_a, **_k: state())
    monkeypatch.setattr(job, "load_filter_context", broken)
    with pytest.raises(JobError) as caught:
        job.handler(JobContext(envelope(BERTH_CHANGE), PortSettings([]), object(), 0))  # type: ignore[arg-type]
    assert caught.value.category is ErrorCategory.DATA_UNAVAILABLE


def test_definition_is_the_validation_worker() -> None:
    assert job.DEFINITION.job_type is JobType.VALIDATION


# --- shared context loader ---------------------------------------------------------------------


def test_tug_requirements_follow_ai054_for_every_snapshot_request() -> None:
    requirements = tug_requirements(state(), load_rules())
    assert set(requirements) == {REQUEST}
    assert requirements[REQUEST].n_min >= 1


def test_tug_requirements_refuse_bad_vessel_data() -> None:
    bad = state(requests=(request(loa=Decimal(0)),))
    with pytest.raises(ContextError, match="request 1"):
        tug_requirements(bad, load_rules())


def test_loader_reads_types_and_leaves_no_transaction(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class Core:
        def rollback(self) -> None:
            calls.append("rollback")

    monkeypatch.setattr(context_module, "core_of", lambda _c: Core())
    monkeypatch.setattr(
        context_module, "read_constraint_types", lambda _c: context().constraint_types
    )
    monkeypatch.setattr(context_module, "read_vessel_type_ids", lambda _c: {"CONTAINER": 21})
    loaded = context_module.load_filter_context(object(), state())  # type: ignore[arg-type]

    assert calls == ["rollback"]
    assert loaded.vessel_type_ids == {"CONTAINER": 21}
    assert set(loaded.tug_requirements) == {REQUEST}
    assert replace(loaded, tug_requirements={}).constraint_types == context().constraint_types
