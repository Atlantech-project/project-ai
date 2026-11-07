"""B3 service time Phase 1 (AI-052, DEC-28): moves, profiles, the formula and exclusions."""

from datetime import date
from decimal import Decimal
from itertools import product
from pathlib import Path
from typing import Final

import pytest

from common.config import ConfigurationError
from part2.service_time import (
    FLAG_LOADING_ESTIMATED,
    REASON_AMBIGUOUS_PROFILE,
    REASON_BASIS_UNDEFINED,
    REASON_MISSING_MOVES,
    REASON_NO_VALID_PROFILE,
    REASON_NON_POSITIVE,
    REASON_UNIT_MISMATCH,
    Moves,
    ProductivityProfile,
    ServiceTimeResult,
    compute_service_time,
    count_moves,
    resolve_profile,
)

SCHEMA_PATH: Final = Path(__file__).parents[3] / "docs" / "ref" / "db" / "schema.sql"
TODAY: Final = date(2026, 11, 7)
CONTAINER_TYPE_ID: Final = 7
TERMINAL_ID: Final = 1


def profile(
    *,
    id: int = 1,
    terminal_id: int = TERMINAL_ID,
    vessel_type_id: int | None = None,
    rate: str = "25.00",
    unit: str = "MOVES_PER_HOUR",
    overhead: int = 30,
    valid_from: date = date(2026, 1, 1),
    valid_to: date | None = None,
) -> ProductivityProfile:
    return ProductivityProfile(
        id=id,
        terminal_id=terminal_id,
        vessel_type_id=vessel_type_id,
        productivity_rate=Decimal(rate),
        rate_unit=unit,
        fixed_overhead_minutes=overhead,
        valid_from=valid_from,
        valid_to=valid_to,
    )


def compute(
    moves: Moves | None, profiles: list[ProductivityProfile], *, code: str = "CONTAINER"
) -> ServiceTimeResult:
    return compute_service_time(
        vessel_type_code=code,
        vessel_type_id=CONTAINER_TYPE_ID,
        terminal_id=TERMINAL_ID,
        moves=moves,
        profiles=profiles,
        on_date=TODAY,
    )


# ---- Task 1: moves (DEC-28 rules 1 to 5) ----


def test_discharge_counts_only_this_port() -> None:
    moves = count_moves(
        has_active_baplie=True,
        discharge_ports=["EGDAM", "EGDAM", "CNSHA", None],
        port_code="EGDAM",
        loading_count=None,
    )
    assert moves == Moves(discharge=2, loading=2, loading_estimated=True)
    assert moves is not None
    assert moves.total == 4


def test_given_loading_is_used() -> None:
    moves = count_moves(
        has_active_baplie=True,
        discharge_ports=["EGDAM", "EGDAM"],
        port_code="EGDAM",
        loading_count=5,
    )
    assert moves == Moves(discharge=2, loading=5, loading_estimated=False)
    assert moves is not None
    assert moves.total == 7


def test_zero_loading_is_a_real_zero() -> None:
    moves = count_moves(
        has_active_baplie=True, discharge_ports=["EGDAM"], port_code="EGDAM", loading_count=0
    )
    assert moves == Moves(discharge=1, loading=0, loading_estimated=False)


def test_no_active_baplie_gives_none_even_with_ports() -> None:
    assert (
        count_moves(
            has_active_baplie=False,
            discharge_ports=["EGDAM"],
            port_code="EGDAM",
            loading_count=None,
        )
        is None
    )


def test_active_baplie_with_no_discharge_here_is_zero_not_none() -> None:
    moves = count_moves(
        has_active_baplie=True, discharge_ports=["CNSHA"], port_code="EGDAM", loading_count=None
    )
    assert moves == Moves(discharge=0, loading=0, loading_estimated=True)


@pytest.mark.parametrize("port_code", [None, "", "  "])
def test_unset_port_code_raises_configuration_error(port_code: str | None) -> None:
    with pytest.raises(ConfigurationError):
        count_moves(
            has_active_baplie=True,
            discharge_ports=["EGDAM"],
            port_code=port_code,
            loading_count=None,
        )


def test_port_code_is_not_needed_when_there_is_no_baplie() -> None:
    # The vessel is left out as MISSING_MOVES first; the configuration gap is not the cause.
    assert (
        count_moves(has_active_baplie=False, discharge_ports=[], port_code=None, loading_count=None)
        is None
    )


def test_negative_loading_raises() -> None:
    with pytest.raises(ValueError, match="loading"):
        count_moves(has_active_baplie=True, discharge_ports=[], port_code="EGDAM", loading_count=-1)


# ---- Task 2: profile resolution ----


def resolve(profiles: list[ProductivityProfile], on: date = TODAY) -> tuple[object, str | None]:
    return resolve_profile(
        profiles, terminal_id=TERMINAL_ID, vessel_type_id=CONTAINER_TYPE_ID, on_date=on
    )


def test_valid_from_and_valid_to_are_inclusive() -> None:
    p = profile(valid_from=date(2026, 11, 7), valid_to=date(2026, 11, 7))
    assert resolve([p], date(2026, 11, 7)) == (p, None)
    assert resolve([p], date(2026, 11, 6)) == (None, REASON_NO_VALID_PROFILE)
    assert resolve([p], date(2026, 11, 8)) == (None, REASON_NO_VALID_PROFILE)


def test_open_ended_profile_is_valid() -> None:
    p = profile(valid_to=None)
    assert resolve([p], date(2099, 1, 1)) == (p, None)


def test_vessel_type_row_beats_terminal_default() -> None:
    default = profile(id=1, vessel_type_id=None)
    specific = profile(id=2, vessel_type_id=CONTAINER_TYPE_ID, rate="30.00")
    assert resolve([default, specific]) == (specific, None)
    assert resolve([specific, default]) == (specific, None)


def test_default_used_when_no_type_row() -> None:
    default = profile(id=1, vessel_type_id=None)
    assert resolve([default]) == (default, None)


def test_expired_type_row_falls_back_to_default() -> None:
    default = profile(id=1, vessel_type_id=None)
    expired = profile(id=2, vessel_type_id=CONTAINER_TYPE_ID, valid_to=date(2026, 11, 6))
    assert resolve([default, expired]) == (default, None)


def test_other_terminal_and_other_type_ignored() -> None:
    other_terminal = profile(id=1, terminal_id=2)
    other_type = profile(id=2, vessel_type_id=99)
    assert resolve([other_terminal, other_type]) == (None, REASON_NO_VALID_PROFILE)


def test_two_equal_rows_are_ambiguous() -> None:
    a = profile(id=1, vessel_type_id=CONTAINER_TYPE_ID)
    b = profile(id=2, vessel_type_id=CONTAINER_TYPE_ID, rate="40.00")
    assert resolve([a, b]) == (None, REASON_AMBIGUOUS_PROFILE)
    assert resolve([profile(id=1), profile(id=2)]) == (None, REASON_AMBIGUOUS_PROFILE)


def test_no_profiles_gives_no_valid_profile() -> None:
    assert resolve([]) == (None, REASON_NO_VALID_PROFILE)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"rate": "0.00"},
        {"rate": "-1.00"},
        {"overhead": -1},
        {"valid_from": date(2026, 2, 1), "valid_to": date(2026, 1, 1)},
    ],
)
def test_profile_the_schema_forbids_is_rejected(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        profile(**kwargs)  # type: ignore[arg-type]


# ---- Task 3: the formula (hand values) ----


def test_hand_value_whole_hours() -> None:
    # 900 moves / 25 per hour = 36 h; 30 min overhead = 0.5 h.
    result = compute(Moves(450, 450, False), [profile()])
    assert result.p50_hours == Decimal("36.50")
    assert result.p90_hours is None
    assert result.method == "FORMULA"
    assert result.excluded_reason is None
    assert FLAG_LOADING_ESTIMATED not in result.flags


def test_rounds_up_never_down() -> None:
    # 100 / 30 = 3.3333...; + 15 min = 0.25 -> 3.5833... -> 3.59 (up).
    result = compute(Moves(50, 50, False), [profile(rate="30.00", overhead=15)])
    assert result.p50_hours == Decimal("3.59")


def test_exact_value_is_not_bumped() -> None:
    result = compute(Moves(30, 30, False), [profile(rate="30.00", overhead=0)])
    assert result.p50_hours == Decimal("2.00")


def test_tiny_excess_rounds_up_one_cent() -> None:
    # 1 move / 100 per hour = 0.01 h exactly; 61 moves / 100 = 0.61; 1 move + 1 min overhead
    # = 0.01 + 0.016666... = 0.026666... -> 0.03.
    assert compute(Moves(1, 0, False), [profile(rate="100.00", overhead=0)]).p50_hours == Decimal(
        "0.01"
    )
    assert compute(Moves(1, 0, False), [profile(rate="100.00", overhead=1)]).p50_hours == Decimal(
        "0.03"
    )


def test_loading_estimated_flag_is_carried() -> None:
    result = compute(Moves(10, 10, True), [profile()])
    assert FLAG_LOADING_ESTIMATED in result.flags
    assert result.inputs["loading_estimated"] is True


def test_inputs_record_discharge_loading_moves_and_profile() -> None:
    result = compute(Moves(10, 4, False), [profile(id=42, rate="20.00", overhead=45)])
    assert result.inputs == {
        "discharge": 10,
        "loading": 4,
        "loading_estimated": False,
        "moves": 14,
        "profile_id": 42,
        "productivity_rate": Decimal("20.00"),
        "rate_unit": "MOVES_PER_HOUR",
        "fixed_overhead_minutes": 45,
        "on_date": TODAY,
    }


def test_zero_moves_with_overhead_is_overhead_only() -> None:
    assert compute(Moves(0, 0, True), [profile(overhead=30)]).p50_hours == Decimal("0.50")


# ---- Task 3: exclusions ----


def assert_excluded(result: ServiceTimeResult, reason: str) -> None:
    assert result.p50_hours is None
    assert result.p90_hours is None
    assert result.method == "FORMULA"
    assert result.excluded_reason == reason


def test_moves_none_excluded_missing_moves() -> None:
    assert_excluded(compute(None, [profile()]), REASON_MISSING_MOVES)


def test_no_profile_excluded_with_reason() -> None:
    assert_excluded(compute(Moves(1, 1, False), []), REASON_NO_VALID_PROFILE)


def test_ambiguous_profile_excluded() -> None:
    result = compute(Moves(1, 1, False), [profile(id=1), profile(id=2)])
    assert_excluded(result, REASON_AMBIGUOUS_PROFILE)


def test_non_container_excluded_basis_undefined_even_with_a_profile() -> None:
    result = compute(Moves(5, 5, False), [profile()], code="BULK_CARRIER")
    assert_excluded(result, REASON_BASIS_UNDEFINED)


def test_non_container_without_moves_is_basis_undefined_not_missing_moves() -> None:
    assert_excluded(compute(None, [], code="TANKER"), REASON_BASIS_UNDEFINED)


def test_container_with_non_moves_unit_excluded() -> None:
    result = compute(Moves(5, 5, False), [profile(unit="TONNES_PER_HOUR")])
    assert_excluded(result, REASON_UNIT_MISMATCH)


def test_zero_moves_zero_overhead_excluded_non_positive() -> None:
    assert_excluded(compute(Moves(0, 0, True), [profile(overhead=0)]), REASON_NON_POSITIVE)


# ---- Task 3, step 5: the schema checks (criterion 3) ----


def chk_ro_p90(method: str, p50: Decimal, p90: Decimal | None) -> bool:
    """Python mirror of `chk_ro_p90`: method ML <=> P90 set, and P90 >= P50 when set."""
    return (method == "ML") == (p90 is not None) and (p90 is None or p90 >= p50)


def chk_ro_values_p50(p50: Decimal) -> bool:
    """Python mirror of the P50 part of `chk_ro_values`, plus the decimal(6,2) range."""
    return p50 > 0 and p50 < Decimal("10000")


def test_results_satisfy_the_schema_checks() -> None:
    checked = 0
    for discharge, loading, rate, overhead in product(
        (0, 1, 7, 450, 2000), (0, 3, 450), ("1.00", "25.00", "33.33", "99999999.99"), (0, 1, 30)
    ):
        result = compute(Moves(discharge, loading, False), [profile(rate=rate, overhead=overhead)])
        if result.p50_hours is None:
            assert result.excluded_reason == REASON_NON_POSITIVE
            assert discharge + loading == 0 and overhead == 0
            continue
        checked += 1
        assert chk_ro_p90(result.method, result.p50_hours, result.p90_hours)
        assert chk_ro_values_p50(result.p50_hours)
        assert result.p50_hours == result.p50_hours.quantize(Decimal("0.01"))
    assert checked > 0


def test_schema_checks_have_not_drifted() -> None:
    """If `schema.sql` changes these constraints, the mirrors above must be reviewed."""
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    lines = {
        name: next(line for line in schema.splitlines() if f"CONSTRAINT `{name}`" in line)
        for name in ("chk_ro_p90", "chk_ro_values", "chk_tpp_unit", "chk_tpp_values")
    }
    assert "`service_time_method` = _utf8mb4'ML'" in lines["chk_ro_p90"]
    assert "`service_time_p90_hours` is not null" in lines["chk_ro_p90"]
    assert "`service_time_p90_hours` >= `service_time_p50_hours`" in lines["chk_ro_p90"]
    assert "`service_time_p50_hours` > 0" in lines["chk_ro_values"]
    assert "`terminal_type` = _utf8mb4'CONTAINER'" in lines["chk_tpp_unit"]
    assert "`rate_unit` = _utf8mb4'MOVES_PER_HOUR'" in lines["chk_tpp_unit"]
    assert "`productivity_rate` > 0" in lines["chk_tpp_values"]
    assert "`fixed_overhead_minutes` >= 0" in lines["chk_tpp_values"]
    assert "`service_time_p50_hours` decimal(6,2) NOT NULL" in schema
