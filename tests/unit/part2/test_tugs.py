import ast
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from common.config import ConfigurationError
from part2.tugs import (
    RULES_PATH,
    PilotOverride,
    Tug,
    TugRequest,
    TugRules,
    block_coefficient,
    compute_tug_requirement,
    displacement_tonnes,
    load_rules,
    mass_bollard_pull,
)


@pytest.fixture(scope="module")
def rules() -> TugRules:
    return load_rules()


def _request(**overrides: Any) -> TugRequest:
    values: dict[str, Any] = {
        "loa": Decimal(225),
        "beam": Decimal(32),
        "arrival_draft": Decimal(13),
        "max_draft": Decimal(15),
        "gross_tonnage": 40_000,
        "vessel_type_code": "BULK_CARRIER",
        "block_coefficient": Decimal("0.80"),
        "pilot_requested": True,
    }
    return TugRequest(**(values | overrides))


FLEET = (
    Tug(1, Decimal(10), "BOLLARD_PULL_TONNES"),
    Tug(2, Decimal(17), "BOLLARD_PULL_TONNES"),
    Tug(3, Decimal(25), "BOLLARD_PULL_TONNES"),
    Tug(4, Decimal(45), "BOLLARD_PULL_TONNES"),
    Tug(5, Decimal(60), "BOLLARD_PULL_TONNES"),
)


# The worked example


def test_the_worked_example(rules: TugRules) -> None:
    request = _request()
    delta = displacement_tonnes(Decimal(225), Decimal(32), Decimal(13), Decimal("0.80"), rules)
    assert delta == Decimal("76752.000")
    assert mass_bollard_pull(delta, rules) == Decimal("86.0512")
    result = compute_tug_requirement(request, FLEET, rules)
    assert result.bp_req == 87
    assert result.n_min == 2
    assert result.n_cap == 3
    assert result.eligible_tugs == frozenset({3, 4, 5})


def test_the_published_example_of_the_formula(rules: TugRules) -> None:
    # 10,000 t gives 46 t in the seanews article cited by the rules file.
    assert mass_bollard_pull(Decimal(10_000), rules) == Decimal(46)


def test_results_are_integers(rules: TugRules) -> None:
    result = compute_tug_requirement(_request(), FLEET, rules)
    assert type(result.bp_req) is int
    assert type(result.n_min) is int
    assert type(result.n_cap) is int


@pytest.mark.parametrize(
    ("beam", "expected"),
    [(Decimal(32), 87), (Decimal("32.01"), 87), (Decimal(1), 50)],
)
def test_bp_req_rounds_up_and_takes_the_larger_value(
    rules: TugRules, beam: Decimal, expected: int
) -> None:
    assert compute_tug_requirement(_request(beam=beam), (), rules).bp_req == expected


def test_a_whole_mass_value_isnt_rounded_up_again(rules: TugRules) -> None:
    # 60 x 100,000 / 100,000 + 40 = 100 exactly, at 100,000 t.
    assert mass_bollard_pull(Decimal(100_000), rules) == Decimal(100)
    request = _request(
        loa=Decimal(250),
        beam=Decimal(40),
        arrival_draft=Decimal(12),
        block_coefficient=Decimal("0.81300813008"),
    )
    assert compute_tug_requirement(request, (), rules).bp_req == 100


# Compulsory towage: below the threshold


def test_below_the_threshold_with_no_pilot_is_zero(rules: TugRules) -> None:
    request = _request(gross_tonnage=999, pilot_requested=False)
    result = compute_tug_requirement(request, FLEET, rules)
    assert (result.n_min, result.n_cap, result.bp_req) == (0, 0, 0)
    assert result.eligible_tugs == frozenset()


def test_the_threshold_is_1000(rules: TugRules) -> None:
    result = compute_tug_requirement(_request(gross_tonnage=1000, pilot_requested=False), (), rules)
    assert result.n_min == 2


def test_below_the_threshold_with_a_pilot_still_gets_tugs(rules: TugRules) -> None:
    request = _request(gross_tonnage=999, pilot_requested=True)
    result = compute_tug_requirement(request, FLEET, rules)
    assert result.n_min == 2
    assert "pilot_request_unknown" not in result.flags


def test_unknown_pilot_request_applies_the_table_and_flags(rules: TugRules) -> None:
    request = _request(gross_tonnage=999, pilot_requested=None)
    result = compute_tug_requirement(request, FLEET, rules)
    assert result.n_min == 2
    assert "pilot_request_unknown" in result.flags


def test_unknown_pilot_request_isnt_flagged_when_it_makes_no_difference(rules: TugRules) -> None:
    result = compute_tug_requirement(_request(pilot_requested=None), FLEET, rules)
    assert "pilot_request_unknown" not in result.flags


# Displacement inputs


def test_the_requests_block_coefficient_wins(rules: TugRules) -> None:
    result = compute_tug_requirement(_request(block_coefficient=Decimal("0.90")), (), rules)
    # 225 x 32 x 13 x 0.90 x 1.025 = 86,346 t, so 60 x 0.86346 + 40 = 91.8076.
    assert result.bp_req == 92
    assert "cb_fallback_used" not in result.flags


@pytest.mark.parametrize(
    ("value", "code", "expected"),
    [
        (Decimal("0.50"), "TANKER", Decimal("0.50")),
        (Decimal("0.90"), "TANKER", Decimal("0.90")),
        (Decimal("0.49"), "TANKER", Decimal("0.80")),
        (Decimal("0.91"), "BULK_CARRIER", Decimal("0.80")),
        (None, "CONTAINER", Decimal("0.65")),
        (None, "BULK_CARRIER", Decimal("0.80")),
        (None, "TANKER", Decimal("0.80")),
        (None, "GENERAL_CARGO", Decimal("0.85")),
        (None, "LNG_CARRIER", Decimal("0.85")),
        (None, "RO_RO", Decimal("0.85")),
        (None, "NOT_A_TYPE", Decimal("0.85")),
        (None, None, Decimal("0.85")),
    ],
)
def test_block_coefficient_fallback(
    rules: TugRules, value: Decimal | None, code: str | None, expected: Decimal
) -> None:
    used, fell_back = block_coefficient(value, code, rules)
    assert used == expected
    assert fell_back is (value != expected)


@pytest.mark.parametrize("value", [None, Decimal("0.2"), Decimal("0.95")])
def test_a_fallback_is_flagged(rules: TugRules, value: Decimal | None) -> None:
    result = compute_tug_requirement(_request(block_coefficient=value), (), rules)
    assert "cb_fallback_used" in result.flags
    assert result.bp_req == 87


def test_arrival_draft_is_used_when_present(rules: TugRules) -> None:
    result = compute_tug_requirement(_request(arrival_draft=Decimal(13)), (), rules)
    assert "max_draft_used" not in result.flags
    assert result.bp_req == 87


def test_max_draft_is_the_fallback_and_is_flagged(rules: TugRules) -> None:
    result = compute_tug_requirement(_request(arrival_draft=None), (), rules)
    # 225 x 32 x 15 x 0.80 x 1.025 = 88,560 t, so 60 x 0.8856 + 40 = 93.136.
    assert result.bp_req == 94
    assert "max_draft_used" in result.flags


def test_gross_tonnage_is_never_used_as_a_weight(rules: TugRules) -> None:
    low = compute_tug_requirement(_request(gross_tonnage=1000), (), rules)
    high = compute_tug_requirement(_request(gross_tonnage=74_999), (), rules)
    assert low.bp_req == high.bp_req == 87


@pytest.mark.parametrize(
    "overrides",
    [
        {"loa": None},
        {"loa": Decimal(0)},
        {"beam": None},
        {"beam": Decimal(-1)},
        {"gross_tonnage": None},
        {"gross_tonnage": 0},
        {"arrival_draft": None, "max_draft": None},
        {"arrival_draft": Decimal(0)},
        {"arrival_draft": None, "max_draft": Decimal(0)},
        {"loa": 225.0},
    ],
)
def test_input_with_no_conservative_default_raises(
    rules: TugRules, overrides: dict[str, Any]
) -> None:
    with pytest.raises(ConfigurationError):
        compute_tug_requirement(_request(**overrides), (), rules)


# Which types use the mass formula


@pytest.mark.parametrize("code", ["BULK_CARRIER", "TANKER"])
def test_bulk_and_tanker_use_the_mass_formula(rules: TugRules, code: str) -> None:
    assert compute_tug_requirement(_request(vessel_type_code=code), (), rules).bp_req == 87


@pytest.mark.parametrize(
    "code", ["CONTAINER", "GENERAL_CARGO", "LNG_CARRIER", "RO_RO", "NOT_A_TYPE", None]
)
def test_other_types_use_the_floor_only(rules: TugRules, code: str | None) -> None:
    assert compute_tug_requirement(_request(vessel_type_code=code), (), rules).bp_req == 50


# The LOA table


@pytest.mark.parametrize(
    ("loa", "n_base", "floor", "min_per_tug"),
    [
        ("60", 1, 10, 10),
        ("60.01", 2, 20, 10),
        ("61", 2, 20, 10),
        ("122", 2, 20, 10),
        ("122.01", 2, 34, 17),
        ("123", 2, 34, 17),
        ("200", 2, 34, 17),
        ("200.01", 2, 50, 25),
        ("201", 2, 50, 25),
        ("280", 2, 50, 25),
        ("280.01", 4, 100, 25),
        ("281", 4, 100, 25),
    ],
)
def test_loa_band_boundaries(
    rules: TugRules, loa: str, n_base: int, floor: int, min_per_tug: int
) -> None:
    request = _request(loa=Decimal(loa), beam=Decimal(10), vessel_type_code="CONTAINER")
    result = compute_tug_requirement(request, FLEET, rules)
    assert result.n_min == n_base
    assert result.n_cap == n_base + 1
    assert result.bp_req == floor
    expected = {tug.id for tug in FLEET if tug.tug_power >= min_per_tug}
    assert result.eligible_tugs == expected


@pytest.mark.parametrize(
    ("gt", "draught", "n_base", "floor", "min_per_tug"),
    [
        (74_999, "16.99", 2, 34, 17),
        (75_000, "16.99", 4, 100, 25),
        (75_000, "17", 4, 180, 45),
        (75_001, "20", 4, 180, 45),
    ],
)
def test_the_gt_and_draught_rules(
    rules: TugRules, gt: int, draught: str, n_base: int, floor: int, min_per_tug: int
) -> None:
    request = _request(
        loa=Decimal(150),
        beam=Decimal(10),
        gross_tonnage=gt,
        arrival_draft=Decimal(draught),
        vessel_type_code="CONTAINER",
    )
    result = compute_tug_requirement(request, FLEET, rules)
    assert (result.n_min, result.bp_req) == (n_base, floor)
    assert result.eligible_tugs == {tug.id for tug in FLEET if tug.tug_power >= min_per_tug}


def test_a_long_ship_with_a_deep_draught_needs_the_top_band(rules: TugRules) -> None:
    request = _request(
        loa=Decimal(300),
        beam=Decimal(10),
        arrival_draft=Decimal(17),
        vessel_type_code="CONTAINER",
    )
    assert compute_tug_requirement(request, (), rules).bp_req == 180


def test_max_draft_decides_the_draught_rule_when_it_is_the_fallback(rules: TugRules) -> None:
    request = _request(
        loa=Decimal(300),
        beam=Decimal(10),
        arrival_draft=None,
        max_draft=Decimal(18),
        vessel_type_code="CONTAINER",
    )
    assert compute_tug_requirement(request, (), rules).bp_req == 180


# Tug power units (AI-054 criterion)


@pytest.mark.parametrize("unit", ["HP", "KW", "UNKNOWN_UNIT"])
def test_tugs_not_rated_in_bollard_pull_are_excluded_and_flagged(
    rules: TugRules, unit: str
) -> None:
    fleet = (Tug(1, Decimal(100_000), unit), Tug(2, Decimal(25), "BOLLARD_PULL_TONNES"))
    result = compute_tug_requirement(_request(), fleet, rules)
    assert result.eligible_tugs == frozenset({2})
    assert result.flags.count("tug_power_not_bollard_pull") == 1


def test_a_fleet_rated_only_in_hp_leaves_no_eligible_tug(rules: TugRules) -> None:
    fleet = (Tug(1, Decimal(5000), "HP"), Tug(2, Decimal(4000), "KW"))
    result = compute_tug_requirement(_request(), fleet, rules)
    assert result.eligible_tugs == frozenset()
    assert result.n_min == 2


def test_a_bollard_pull_fleet_isnt_flagged(rules: TugRules) -> None:
    result = compute_tug_requirement(_request(), FLEET, rules)
    assert "tug_power_not_bollard_pull" not in result.flags


@pytest.mark.parametrize(
    ("loa", "gt", "draught", "minimum"),
    [
        ("60", 40_000, "13", "10"),
        ("122", 40_000, "13", "10"),
        ("200", 40_000, "13", "17"),
        ("280", 40_000, "13", "25"),
        ("281", 40_000, "13", "25"),
        ("150", 75_000, "16.99", "25"),
        ("281", 40_000, "17", "45"),
        ("150", 75_000, "17", "45"),
    ],
)
def test_every_bands_exact_minimum_power(
    rules: TugRules, loa: str, gt: int, draught: str, minimum: str
) -> None:
    fleet = (
        Tug(1, Decimal(minimum) - Decimal("0.01"), "BOLLARD_PULL_TONNES"),
        Tug(2, Decimal(minimum), "BOLLARD_PULL_TONNES"),
    )
    request = _request(loa=Decimal(loa), gross_tonnage=gt, arrival_draft=Decimal(draught))
    assert compute_tug_requirement(request, fleet, rules).eligible_tugs == {2}


def test_eligibility_is_inclusive_at_the_minimum(rules: TugRules) -> None:
    fleet = (
        Tug(1, Decimal("24.99"), "BOLLARD_PULL_TONNES"),
        Tug(2, Decimal(25), "BOLLARD_PULL_TONNES"),
    )
    assert compute_tug_requirement(_request(), fleet, rules).eligible_tugs == {2}


def test_a_zero_requirement_doesnt_flag_power_units(rules: TugRules) -> None:
    request = _request(gross_tonnage=500, pilot_requested=False)
    result = compute_tug_requirement(request, (Tug(1, Decimal(50), "HP"),), rules)
    assert "tug_power_not_bollard_pull" not in result.flags


# Pilot override


def test_pilot_override_replaces_both_values(rules: TugRules) -> None:
    request = _request(pilot_override=PilotOverride(n_min=3, bp_req=120))
    result = compute_tug_requirement(request, FLEET, rules)
    assert (result.n_min, result.n_cap, result.bp_req) == (3, 4, 120)
    assert "pilot_override" in result.flags


def test_pilot_override_of_n_min_only(rules: TugRules) -> None:
    request = _request(pilot_override=PilotOverride(n_min=1))
    result = compute_tug_requirement(request, FLEET, rules)
    assert (result.n_min, result.n_cap, result.bp_req) == (1, 2, 87)


def test_pilot_override_of_bp_req_only(rules: TugRules) -> None:
    request = _request(pilot_override=PilotOverride(bp_req=40))
    result = compute_tug_requirement(request, FLEET, rules)
    assert (result.n_min, result.n_cap, result.bp_req) == (2, 3, 40)


def test_pilot_override_applies_below_the_threshold(rules: TugRules) -> None:
    request = _request(
        gross_tonnage=500, pilot_requested=False, pilot_override=PilotOverride(n_min=1)
    )
    result = compute_tug_requirement(request, FLEET, rules)
    assert result.n_min == 1
    assert result.eligible_tugs == frozenset({3, 4, 5})


@pytest.mark.parametrize("override", [PilotOverride(n_min=-1), PilotOverride(bp_req=-1)])
def test_a_negative_override_raises(rules: TugRules, override: PilotOverride) -> None:
    with pytest.raises(ConfigurationError, match="pilot_override"):
        compute_tug_requirement(_request(pilot_override=override), (), rules)


def test_no_override_means_no_flag(rules: TugRules) -> None:
    assert "pilot_override" not in compute_tug_requirement(_request(), (), rules).flags


# The rules file


def test_every_result_says_the_rules_are_unvalidated(rules: TugRules) -> None:
    normal = compute_tug_requirement(_request(), (), rules)
    zero = compute_tug_requirement(_request(gross_tonnage=500, pilot_requested=False), (), rules)
    assert "rules_unvalidated" in normal.flags
    assert "rules_unvalidated" in zero.flags


def test_approved_rules_arent_flagged(tmp_path: Path) -> None:
    data = _rules_data()
    data["status"] = "APPROVED"
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert compute_tug_requirement(_request(), (), load_rules(path)).flags == ()


def test_the_rules_file_is_proposed_with_a_source_on_every_section() -> None:
    data = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    assert data["decision"] == "DEC-20"
    assert data["status"] == "PROPOSED"
    sections = [value for value in data.values() if isinstance(value, dict)]
    assert len(sections) == 7
    for section in sections:
        assert section["source"]
        assert isinstance(section["interim"], bool)


def test_the_rules_file_values_are_the_agreed_ones() -> None:
    data = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    assert data["compulsory_towage"]["gt_threshold"] == 1000
    assert data["compulsory_towage"]["interim"] is True
    assert data["block_coefficient"]["by_vessel_type"] == {
        "BULK_CARRIER": "0.80",
        "TANKER": "0.80",
        "CONTAINER": "0.65",
    }
    assert data["block_coefficient"]["default"] == "0.85"
    assert data["block_coefficient"]["valid_min"] == "0.50"
    assert data["block_coefficient"]["valid_max"] == "0.90"
    assert data["mass_bollard_pull"]["vessel_types"] == ["BULK_CARRIER", "TANKER"]
    assert data["n_cap"]["offset"] == 1


def _rules_data() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    return data


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.pop("n_cap"),
        lambda d: d.__setitem__("status", "APPROVED_BY_NOBODY"),
        lambda d: d["loa_bands"]["bands"].clear(),
        lambda d: d["loa_bands"]["bands"].reverse(),
        lambda d: d["compulsory_towage"].pop("source"),
        lambda d: d["compulsory_towage"].pop("interim"),
        lambda d: d["compulsory_towage"].__setitem__("source", ""),
        lambda d: d["compulsory_towage"].__setitem__("interim", "yes"),
        lambda d: d["block_coefficient"].__setitem__("default", 0.85),
        lambda d: d["block_coefficient"].__setitem__("default", "not a number"),
        lambda d: d["large_vessel"]["bands"].pop(),
    ],
)
def test_a_broken_rules_file_is_refused(tmp_path: Path, change: Any) -> None:
    data = _rules_data()
    change(data)
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_rules(path)


def test_a_missing_rules_file_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="rules"):
        load_rules(tmp_path / "nope.json")


def test_changing_the_rules_file_changes_the_result_without_code(tmp_path: Path) -> None:
    data = _rules_data()
    data["compulsory_towage"]["gt_threshold"] = 2000
    data["n_cap"]["offset"] = 2
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    rules = load_rules(path)
    request = _request(gross_tonnage=1500, pilot_requested=False)
    assert compute_tug_requirement(request, (), rules).n_min == 0
    assert compute_tug_requirement(_request(), (), rules).n_cap == 4


# The module stays outside the solver


def test_the_module_imports_no_solver() -> None:
    source = (Path(__file__).resolve().parents[3] / "part2" / "tugs.py").read_text(encoding="utf-8")
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported & {"ortools", "pymysql", "redis"}


def test_the_function_doesnt_change_its_inputs(rules: TugRules) -> None:
    request = _request()
    fleet = list(FLEET)
    first = compute_tug_requirement(request, fleet, rules)
    second = compute_tug_requirement(request, fleet, rules)
    assert first == second
    assert fleet == list(FLEET)
