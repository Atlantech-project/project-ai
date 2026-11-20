"""B2 pre-solve rules (AI-051 criterion "Each rule has tests"). SYNTHETIC data only."""

from decimal import Decimal

import pytest

from common.config import ConfigurationError
from part2.filter import Candidates, Kind, filter_candidates
from part2.state.model import PilotRankLimit
from tests.unit.part2.filter.builders import (
    BERTH,
    OTHER_BERTH,
    OTHER_TERMINAL,
    REQUEST,
    TUG_A,
    TUG_B,
    TUG_C,
    berth,
    context,
    pilot,
    request,
    requirement,
    state,
    tug,
    window,
)


def _codes(c: Candidates, berth_id: int = BERTH) -> list[str]:
    (result,) = [b for b in c.berths if b.berth_id == berth_id]
    return [r.code for r in (*c.request_removals, *result.removals)]


def _run(**state_changes: object) -> Candidates:
    return filter_candidates(state(**state_changes), REQUEST, context())


def test_a_fitting_berth_is_kept() -> None:
    c = _run()
    assert c.feasible
    assert c.feasible_berth_ids == (BERTH, OTHER_BERTH)
    assert c.request_removals == ()


# --- Per berth ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("terminals", "removed"),
    [(frozenset({1}), False), (frozenset({1, 2}), False), (frozenset({OTHER_TERMINAL}), True)],
)
def test_terminal_compatibility(terminals: frozenset[int], removed: bool) -> None:
    c = _run(berths=(berth(terminal_ids=terminals),))
    assert _codes(c) == (["TERMINAL_COMPATIBILITY"] if removed else [])


@pytest.mark.parametrize(
    ("status", "removed"), [("ACTIVE", False), ("MAINTENANCE", True), ("INACTIVE", True)]
)
def test_berth_unavailable(status: str, removed: bool) -> None:
    c = _run(berths=(berth(status=status),))
    assert _codes(c) == (["BERTH_UNAVAILABLE"] if removed else [])


@pytest.mark.parametrize(
    ("max_loa", "removed"), [("250.00", False), ("200.00", False), ("199.99", True)]
)
def test_max_loa(max_loa: str, removed: bool) -> None:
    c = _run(berths=(berth(max_vessel_loa=Decimal(max_loa)),))
    assert _codes(c) == (["MAX_LOA"] if removed else [])


@pytest.mark.parametrize(("depth", "removed"), [("14.00", False), ("10.00", False), ("9.99", True)])
def test_max_draft_is_static(depth: str, removed: bool) -> None:
    # Equal depth passes MAX_DRAFT; UKC (AI-045) must reject it later (test_safety.py, skipped).
    c = _run(berths=(berth(water_depth=Decimal(depth)),))
    assert _codes(c) == (["MAX_DRAFT"] if removed else [])


def test_a_berth_failing_several_rules_keeps_every_reason() -> None:
    bad = berth(
        status="MAINTENANCE",
        terminal_ids=frozenset({OTHER_TERMINAL}),
        max_vessel_loa=Decimal("100"),
        water_depth=Decimal("5"),
    )
    c = _run(berths=(bad,))
    assert _codes(c) == ["BERTH_UNAVAILABLE", "MAX_DRAFT", "MAX_LOA", "TERMINAL_COMPATIBILITY"]
    assert {r.kind for r in c.berths[0].removals} == {Kind.STRUCTURAL}


def test_only_the_failing_berth_is_removed() -> None:
    c = _run(berths=(berth(BERTH, max_vessel_loa=Decimal("100")), berth(OTHER_BERTH)))
    assert c.feasible_berth_ids == (OTHER_BERTH,)


def test_no_berth_in_the_snapshot_is_a_reason() -> None:
    c = _run(berths=())
    assert not c.feasible
    assert [r.code for r in c.request_removals] == ["TERMINAL_COMPATIBILITY"]


# --- Per request --------------------------------------------------------------------------------


def test_no_confirmed_window_removes_every_berth() -> None:
    c = _run(confirmed_windows=())
    assert not c.feasible
    assert [r.code for r in c.request_removals] == ["ENTRY_WINDOW"]


def test_two_confirmed_windows_are_an_error() -> None:
    with pytest.raises(ValueError, match="confirmed window"):
        _run(confirmed_windows=(window(), window()))


@pytest.mark.parametrize(
    ("pilots", "loa", "code"),
    [
        ((pilot(rank="FIRST"),), "400", None),  # NULL limit: no limit
        ((pilot(rank="SECOND"),), "250.00", None),  # equal passes
        ((pilot(rank="SECOND"),), "250.01", "PILOT_RANK_LIMIT"),
        ((pilot(rank="THIRD"), pilot(32, rank="SECOND")), "200", None),  # one pilot is enough
        ((pilot(rank="FIRST", is_active=False),), "100", "PILOT_UNAVAILABLE"),
        ((pilot(rank="FIRST", role=False),), "100", "PILOT_UNAVAILABLE"),
        ((), "100", "PILOT_UNAVAILABLE"),
    ],
    ids=["null-limit", "equal", "over", "one-enough", "inactive", "ended-role", "none"],
)
def test_pilot_rank(pilots: tuple[object, ...], loa: str, code: str | None) -> None:
    c = filter_candidates(
        state(pilots=pilots, requests=(request(loa=Decimal(loa)),)),
        REQUEST,
        context(),
    )
    assert [r.code for r in c.request_removals if r.code.startswith("PILOT")] == (
        [code] if code else []
    )


def test_a_rank_without_a_limits_row_is_not_allowed() -> None:
    ranks = (PilotRankLimit("SECOND", Decimal("250")),)
    c = filter_candidates(
        state(pilots=(pilot(rank="FIRST"),), pilot_rank_limits=ranks), REQUEST, context()
    )
    assert [r.code for r in c.request_removals] == ["PILOT_RANK_LIMIT"]


@pytest.mark.parametrize(
    ("tugs", "eligible", "n_min", "removed"),
    [
        ((TUG_A, TUG_B), (TUG_A, TUG_B, TUG_C), 2, False),
        ((TUG_A,), (TUG_A, TUG_B, TUG_C), 2, True),
        ((TUG_A, TUG_B, TUG_C), (TUG_A,), 2, True),  # ineligible tugs don't count
        ((), (), 0, False),  # no tug needed
    ],
)
def test_tug_count(
    tugs: tuple[int, ...], eligible: tuple[int, ...], n_min: int, removed: bool
) -> None:
    c = filter_candidates(
        state(tugs=tuple(tug(t) for t in tugs)),
        REQUEST,
        context(tug_requirements={REQUEST: requirement(n_min, eligible)}),
    )
    assert [r.code for r in c.request_removals] == (["TUG_COUNT"] if removed else [])


def test_out_of_service_tugs_do_not_count() -> None:
    tugs = (tug(TUG_A), tug(TUG_B, "MAINTENANCE"), tug(TUG_C, "INACTIVE"))
    c = filter_candidates(state(tugs=tugs), REQUEST, context())
    assert [r.code for r in c.request_removals] == ["TUG_COUNT"]


@pytest.mark.parametrize("unvalidated", [True, False])
def test_tug_count_detail_says_when_the_rules_are_unvalidated(unvalidated: bool) -> None:
    c = filter_candidates(
        state(tugs=(tug(TUG_A),)),
        REQUEST,
        context(tug_requirements={REQUEST: requirement(unvalidated=unvalidated)}),
    )
    (removal,) = c.request_removals
    assert ("unvalidated" in removal.detail) is unvalidated


def test_a_missing_tug_requirement_is_a_configuration_error() -> None:
    with pytest.raises(ConfigurationError, match="tug requirement"):
        filter_candidates(state(), REQUEST, context(tug_requirements={}))


def test_an_unknown_request_is_an_error() -> None:
    with pytest.raises(KeyError, match="999"):
        filter_candidates(state(), 999, context())
