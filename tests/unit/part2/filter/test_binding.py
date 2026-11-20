"""Reasons usable for NO_FEASIBLE_PLAN (AI-051 criterion 3), shaped as CT-10 `binding_constraints`.

SYNTHETIC data only.
"""

from decimal import Decimal

from part2.filter import (
    BindingConstraint,
    Kind,
    binding_constraints,
    check_option,
    filter_candidates,
)
from part2.state.model import ConfirmedHold, Identified, ResourceKind
from tests.unit.part2.filter.builders import (
    BERTH,
    HOUR,
    OTHER_BERTH,
    OTHER_PILOT,
    OTHER_TERMINAL,
    PILOT,
    REQUEST,
    SYN_MAX_BEAM,
    T0,
    berth,
    context,
    limit,
    option,
    pilot,
    state,
)


def test_a_request_with_a_berth_left_has_no_binding_constraints() -> None:
    assert binding_constraints(filter_candidates(state(), REQUEST, context())) == ()


def test_one_item_per_distinct_reason_with_its_kind() -> None:
    berths = (
        berth(BERTH, max_vessel_loa=Decimal("100")),
        berth(OTHER_BERTH, max_vessel_loa=Decimal("150"), terminal_ids=frozenset({OTHER_TERMINAL})),
    )
    rows = (limit(SYN_MAX_BEAM, "10"),)
    c = filter_candidates(state(berths=berths, safety_constraints=rows), REQUEST, context())
    items = binding_constraints(c)
    assert [(i.kind, i.constraint_type_code) for i in items] == [
        (Kind.SAFETY, SYN_MAX_BEAM.code),
        (Kind.STRUCTURAL, "MAX_LOA"),
        (Kind.STRUCTURAL, "TERMINAL_COMPATIBILITY"),
    ]
    max_loa = items[1]
    assert "B11" in max_loa.detail and "B12" in max_loa.detail


def test_a_request_wide_reason_is_reported_once() -> None:
    c = filter_candidates(state(confirmed_windows=()), REQUEST, context())
    (item,) = binding_constraints(c)
    assert item == BindingConstraint(Kind.STRUCTURAL, "ENTRY_WINDOW", item.detail)
    assert "window" in item.detail


def test_detail_is_at_most_255_characters() -> None:
    many = tuple(
        berth(100 + i, code=f"BERTH-WITH-A-LONG-CODE-{i}", max_vessel_loa=Decimal("1"))
        for i in range(40)
    )
    c = filter_candidates(state(berths=many), REQUEST, context())
    (item,) = binding_constraints(c)
    assert item.constraint_type_code == "MAX_LOA"
    assert len(item.detail) <= 255


def test_the_order_is_stable() -> None:
    berths = (berth(BERTH, status="INACTIVE"), berth(OTHER_BERTH, max_vessel_loa=Decimal("1")))
    c = filter_candidates(state(berths=berths), REQUEST, context())
    first = binding_constraints(c)
    reversed_state = state(berths=tuple(reversed(berths)))
    again = binding_constraints(filter_candidates(reversed_state, REQUEST, context()))
    assert [i.constraint_type_code for i in first] == [i.constraint_type_code for i in again]


# Pilotage is compulsory for every vessel (confirmed rule, AI-051 task decision): no pilot means
# NO_FEASIBLE_PLAN with PILOT_UNAVAILABLE, never an option with a NULL pilot.


def test_no_active_pilot_gives_no_feasible_plan_with_pilot_unavailable() -> None:
    s = state(pilots=(pilot(PILOT, is_active=False), pilot(OTHER_PILOT, role=False)))
    c = filter_candidates(s, REQUEST, context())
    assert not c.feasible
    assert [(i.kind, i.constraint_type_code) for i in binding_constraints(c)] == [
        (Kind.STRUCTURAL, "PILOT_UNAVAILABLE")
    ]
    assert not check_option(s, option(pilot_user_id=None), context()).passes


def test_with_every_pilot_busy_no_option_passes_not_even_one_without_a_pilot() -> None:
    def busy(pilot_id: int) -> ConfirmedHold:
        return ConfirmedHold(
            ResourceKind.PILOT, pilot_id, T0, T0 + 24 * HOUR, 9, 1, 1, Identified.COMPONENT
        )

    s = state(confirmed_holds=(busy(PILOT), busy(OTHER_PILOT)))
    for pilot_id in (PILOT, OTHER_PILOT, None):
        result = check_option(s, option(pilot_user_id=pilot_id), context())
        assert [r.code for r in result.removals] == ["PILOT_UNAVAILABLE"]
