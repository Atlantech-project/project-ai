"""B2 Marine Safety Officer limits and code lists (AI-051). SYNTHETIC limits only."""

import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any, Final

import pytest

from common.config import ConfigurationError
from part2.filter import DEFAULT_B2_REGISTRY, B2Registry, Kind, VesselAttribute, filter_candidates
from part2.state.model import SafetyConstraint
from tests.unit.part2.filter.builders import (
    BERTH,
    HOUR,
    OTHER_BERTH,
    OTHER_TERMINAL,
    REQUEST,
    SYN_MAX_BEAM,
    SYN_MIN_DWT,
    SYN_UNOWNED,
    T0,
    TERMINAL,
    TEST_A4_REGISTRY,
    UKC,
    VESSEL_TYPE_ID,
    WIND,
    berth,
    cargo,
    context,
    limit,
    state,
    window,
)

SEED_SPEC: Final = (
    Path(__file__).resolve().parents[4] / "docs" / "drafts" / "ai-payloads" / "seed-spec.json"
)


def _safety(rows: tuple[SafetyConstraint, ...], **state_changes: object) -> dict[int, list[str]]:
    c = filter_candidates(state(safety_constraints=rows, **state_changes), REQUEST, context())
    return {b.berth_id: [r.code for r in b.removals if r.kind is Kind.SAFETY] for b in c.berths}


# beam 30.00 m, deadweight 40000 t in the builders.
@pytest.mark.parametrize(
    ("row", "removed"),
    [
        (limit(SYN_MAX_BEAM, "30.00"), False),  # MAX_ALLOWED equal passes
        (limit(SYN_MAX_BEAM, "29.99"), True),
        (limit(SYN_MIN_DWT, "40000"), False),  # MIN_REQUIRED equal passes
        (limit(SYN_MIN_DWT, "40001"), True),
    ],
)
def test_comparators(row: SafetyConstraint, removed: bool) -> None:
    result = _safety((row,))
    code = SYN_MAX_BEAM.code if row.constraint_type_id == SYN_MAX_BEAM.id else SYN_MIN_DWT.code
    assert result == {BERTH: [code] if removed else [], OTHER_BERTH: [code] if removed else []}


def test_strictest_wins_per_candidate_berth() -> None:
    rows = (
        limit(SYN_MAX_BEAM, "40"),
        limit(SYN_MAX_BEAM, "25", terminal_id=TERMINAL, berth_id=BERTH),
    )
    assert _safety(rows) == {BERTH: [SYN_MAX_BEAM.code], OTHER_BERTH: []}


@pytest.mark.parametrize(
    ("row", "removed"),
    [
        (limit(SYN_MAX_BEAM, "25", vessel_type_id=VESSEL_TYPE_ID), True),
        (limit(SYN_MAX_BEAM, "25", vessel_type_id=99), False),
        (limit(SYN_MAX_BEAM, "25", terminal_id=OTHER_TERMINAL), False),
        (limit(SYN_MAX_BEAM, "25", imdg_class="2"), True),  # cargo 2.1: class covers division
        (limit(SYN_MAX_BEAM, "25", imdg_class="3"), False),
    ],
)
def test_scope(row: SafetyConstraint, removed: bool) -> None:
    result = _safety((row,), manifest_entries=(cargo("2.1"),))
    assert result[BERTH] == ([SYN_MAX_BEAM.code] if removed else [])


@pytest.mark.parametrize(
    ("active_from", "active_to", "removed"),
    [
        (T0 - HOUR, T0, False),  # ends at the window start
        (T0 - HOUR, T0 + HOUR, True),  # overlaps the start
        (T0 + 5 * HOUR, None, True),  # starts inside the window
        (T0 + 6 * HOUR, None, False),  # starts at the window end (half-open)
    ],
)
def test_a_limit_active_at_any_moment_of_the_window_applies(
    active_from: object, active_to: object, removed: bool
) -> None:
    row = limit(SYN_MAX_BEAM, "25", active_from=active_from, active_to=active_to)  # type: ignore[arg-type]
    assert _safety((row,))[BERTH] == ([SYN_MAX_BEAM.code] if removed else [])


def test_a_tighter_limit_later_in_the_window_still_applies() -> None:
    rows = (
        limit(SYN_MAX_BEAM, "40", active_to=T0 + 3 * HOUR),
        limit(SYN_MAX_BEAM, "25", active_from=T0 + 3 * HOUR),
    )
    assert _safety(rows)[BERTH] == [SYN_MAX_BEAM.code]


def test_equipment_limits_are_not_applied() -> None:
    # Blocked: the snapshot has no berth-equipment link (AI-051 task decision).
    assert _safety((limit(SYN_MAX_BEAM, "1", equipment_category_id=5),))[BERTH] == []


def test_a4_and_ukc_codes_are_not_rechecked_by_b2() -> None:
    rows = (limit(WIND, "0"), limit(UKC, "1000"))
    assert _safety(rows) == {BERTH: [], OTHER_BERTH: []}


def test_a_code_in_no_list_fails_loudly() -> None:
    with pytest.raises(ConfigurationError, match="SYNTHETIC_UNOWNED_M"):
        _safety((limit(SYN_UNOWNED, "1"),))


def test_a_code_in_no_list_is_ignored_when_no_row_applies() -> None:
    assert _safety((limit(SYN_UNOWNED, "1", terminal_id=OTHER_TERMINAL),))[BERTH] == []


def test_a_code_in_no_list_is_ignored_when_it_starts_after_the_window() -> None:
    row = limit(SYN_UNOWNED, "1", active_from=T0 + 6 * HOUR)
    assert _safety((row,))[BERTH] == []


def test_a_row_of_an_unknown_constraint_type_is_a_configuration_error() -> None:
    orphan = replace(limit(SYN_MAX_BEAM, "40"), constraint_type_id=999)
    with pytest.raises(ConfigurationError, match="999"):
        _safety((orphan,))


def test_an_unknown_limit_unit_is_a_configuration_error() -> None:
    odd = replace(SYN_MAX_BEAM, unit="FATHOMS")
    with pytest.raises(ConfigurationError, match="FATHOMS"):
        filter_candidates(
            state(safety_constraints=(limit(odd, "40"),)),
            REQUEST,
            context(constraint_types=(odd,)),
        )


def test_a_missing_vessel_type_id_is_a_configuration_error() -> None:
    with pytest.raises(ConfigurationError, match="CONTAINER"):
        filter_candidates(
            state(safety_constraints=(limit(SYN_MAX_BEAM, "40"),)),
            REQUEST,
            context(vessel_type_ids={}),
        )


def test_no_window_skips_the_safety_check() -> None:
    c = filter_candidates(
        state(safety_constraints=(limit(SYN_MAX_BEAM, "1"),), confirmed_windows=()),
        REQUEST,
        context(),
    )
    assert [r.code for r in c.request_removals] == ["ENTRY_WINDOW"]
    assert all(not b.removals for b in c.berths)


def test_a_limit_unit_of_another_dimension_is_a_configuration_error() -> None:
    knots_beam = replace(SYN_MAX_BEAM, unit="KNOTS")
    with pytest.raises(ConfigurationError, match="SYNTHETIC_MAX_BEAM_M"):
        filter_candidates(
            state(safety_constraints=(limit(knots_beam, "40"),)),
            REQUEST,
            context(constraint_types=(knots_beam,)),
        )


@pytest.mark.parametrize(
    ("limit_nm", "removed"),
    [("0.0161", True), ("0.0170", False)],  # 29.82 m and 31.48 m against a 30 m beam
)
def test_a_converted_limit_unit_is_compared_in_its_own_unit(limit_nm: str, removed: bool) -> None:
    nm_beam = replace(SYN_MAX_BEAM, unit="NAUTICAL_MILES")
    c = filter_candidates(
        state(safety_constraints=(limit(nm_beam, limit_nm),)),
        REQUEST,
        context(constraint_types=(nm_beam,)),
    )
    assert [r.code for r in c.berths[0].removals] == ([SYN_MAX_BEAM.code] if removed else [])


# --- Code lists ---------------------------------------------------------------------------------


def _seeded_codes() -> list[str]:
    with SEED_SPEC.open(encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return [str(row["code"]) for row in data["constraint_types"]]


@pytest.mark.parametrize("code", _seeded_codes())
def test_every_seeded_code_has_exactly_one_owner(code: str) -> None:
    r = DEFAULT_B2_REGISTRY
    owners = [code in r.b2, code in r.a4.a4, code in r.a4.elsewhere and code not in r.b2]
    assert owners.count(True) == 1, code


def test_no_b2_code_is_seeded_yet() -> None:
    # AI-009 criterion 1: the Marine Safety Officer codes must be seeded before these rules are
    # active in production.
    assert dict(DEFAULT_B2_REGISTRY.b2) == {}


def test_a_b2_code_must_be_listed_as_owned_elsewhere_by_a4() -> None:
    with pytest.raises(ValueError, match="SYNTHETIC_X"):
        B2Registry(b2={"SYNTHETIC_X": VesselAttribute.LOA}, a4=TEST_A4_REGISTRY)


def test_a_b2_code_must_not_be_an_a4_code() -> None:
    with pytest.raises(ValueError, match="MAX_WIND_KN"):
        B2Registry(b2={"MAX_WIND_KN": VesselAttribute.LOA}, a4=TEST_A4_REGISTRY)


# --- UKC: not enforced until AI-045 (user's choice, 2026-11-20) ---------------------------------


@pytest.mark.skip(reason="enabled once AI-045 exists: UKC is not yet enforced by B2")
@pytest.mark.parametrize(
    ("depth", "min_ukc"),
    [("14.00", "5.00"), ("10.00", "0.50")],  # fails MIN_UKC_M; draft == water_depth
    ids=["fails-min-ukc", "draft-equals-depth"],
)
def test_b2_rejects_a_berth_that_fails_min_ukc_via_ai_045(depth: str, min_ukc: str) -> None:
    rows = (limit(UKC, min_ukc),)
    c = filter_candidates(
        state(
            safety_constraints=rows,
            berths=(berth(water_depth=Decimal(depth)),),
            confirmed_windows=(window(),),
        ),
        REQUEST,
        context(),
    )
    assert "MIN_UKC_M" in [r.code for r in c.berths[0].removals]
