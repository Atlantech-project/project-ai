import json
import re
from decimal import Decimal

import pytest

from tools.scenario_generator.generate import generate, imo_check_digit_is_valid
from tools.scenario_generator.model import Scenario, ScenarioSize


def _scenario(size: ScenarioSize, seed: int = 1, days: int = 7) -> Scenario:
    return generate(size, seed, days)


def _dump(scenario: Scenario) -> str:
    return json.dumps([scenario.metadata, scenario.tables], sort_keys=True)


def test_minimum_has_one_terminal_and_five_berths() -> None:
    tables = _scenario(ScenarioSize.MINIMUM).tables
    assert len(tables["terminals"]) == 1
    assert len(tables["berths"]) == 5
    assert len(tables["berth_terminals"]) == 5


def test_reference_has_eight_terminals_and_thirty_six_berths() -> None:
    tables = _scenario(ScenarioSize.REFERENCE).tables
    assert len(tables["terminals"]) == 8
    assert len(tables["berths"]) == 36
    assert len(tables["berth_terminals"]) == 36
    assert {row["berth_id"] for row in tables["berth_terminals"]} == set(range(1, 37))


def test_reference_averages_about_26_requests_a_day() -> None:
    total = len(_scenario(ScenarioSize.REFERENCE, days=7).tables["berthing_requests"])
    assert 26 * 7 - 21 <= total <= 26 * 7 + 21


def test_minimum_scales_requests_with_berths() -> None:
    total = len(_scenario(ScenarioSize.MINIMUM, days=7).tables["berthing_requests"])
    assert 1 * 7 <= total <= 7 * 7


def test_same_seed_gives_identical_scenarios() -> None:
    for size in ScenarioSize:
        first, second = _scenario(size, seed=42), _scenario(size, seed=42)
        assert first == second
        assert _dump(first) == _dump(second)


def test_different_seeds_differ() -> None:
    for size in ScenarioSize:
        assert _dump(_scenario(size, seed=1)) != _dump(_scenario(size, seed=2))


def test_metadata_is_labelled_synthetic() -> None:
    for size in ScenarioSize:
        scenario = _scenario(size, seed=7, days=3)
        meta = scenario.metadata
        assert meta["synthetic"] is True
        assert str(meta["label"]).startswith("SYNTHETIC")
        assert meta["size"] == size.value
        assert meta["seed"] == 7
        assert meta["days"] == 3
        assert meta["assumptions"]
        assert meta["counts"] == {name: len(rows) for name, rows in scenario.tables.items()}


def test_tables_come_in_insert_order() -> None:
    assert list(_scenario(ScenarioSize.MINIMUM).tables) == [
        "port_profiles",
        "terminals",
        "berths",
        "berth_terminals",
        "navigation_channels",
        "channel_waypoints",
        "tugboats",
        "vessel_types",
        "vessels",
        "external_systems",
        "berthing_requests",
    ]


def test_rows_satisfy_schema_checks() -> None:
    for size in ScenarioSize:
        tables = _scenario(size, seed=3).tables
        for berth in tables["berths"]:
            assert Decimal(str(berth["max_vessel_loa"])) <= Decimal(str(berth["length"]))
            assert Decimal(str(berth["water_depth"])) > 0
        imos = [str(vessel["imo_number"]) for vessel in tables["vessels"]]
        assert len(set(imos)) == len(imos)
        draft_limit = {v["id"]: Decimal(str(v["max_draft"])) for v in tables["vessels"]}
        for vessel in tables["vessels"]:
            assert re.fullmatch(r"[0-9]{7}", str(vessel["imo_number"]))
            assert Decimal(str(vessel["beam"])) < Decimal(str(vessel["loa"]))
        for request in tables["berthing_requests"]:
            assert Decimal("0.3") < Decimal(str(request["block_coefficient"])) < Decimal("1.0")
            assert Decimal(str(request["arrival_draft"])) <= draft_limit[request["vessel_id"]]
            assert Decimal(str(request["arrival_draft"])) > 0
            assert int(str(request["gross_tonnage"])) > 0
            assert int(str(request["deadweight_tonnes"])) > 0
            assert "departure_draft" not in request or request["departure_draft"] is None


def test_no_vessel_has_a_valid_imo_check_digit() -> None:
    tables = _scenario(ScenarioSize.REFERENCE, seed=5).tables
    assert not any(imo_check_digit_is_valid(str(v["imo_number"])) for v in tables["vessels"])


def test_imo_check_digit_rule() -> None:
    assert imo_check_digit_is_valid("9074729")  # the IMO's own worked example
    assert not imo_check_digit_is_valid("9074720")


def test_foreign_keys_resolve_inside_the_scenario() -> None:
    tables = _scenario(ScenarioSize.REFERENCE, seed=9).tables
    ids = {name: {row["id"] for row in rows if "id" in row} for name, rows in tables.items()}
    assert {row["terminal_id"] for row in tables["berth_terminals"]} <= ids["terminals"]
    assert {row["berth_id"] for row in tables["berth_terminals"]} <= ids["berths"]
    assert {row["channel_id"] for row in tables["channel_waypoints"]} <= ids["navigation_channels"]
    assert {row["vessel_type_id"] for row in tables["vessels"]} <= ids["vessel_types"]
    requests = tables["berthing_requests"]
    assert {row["vessel_id"] for row in requests} <= ids["vessels"]
    assert {row["requested_terminal_id"] for row in requests} <= ids["terminals"]
    assert {row["external_system_id"] for row in requests} <= ids["external_systems"]


def test_container_vessels_request_container_terminals() -> None:
    tables = _scenario(ScenarioSize.REFERENCE, seed=11).tables
    terminal_type = {t["id"]: t["terminal_type"] for t in tables["terminals"]}
    type_code = {t["id"]: t["code"] for t in tables["vessel_types"]}
    vessel_type = {v["id"]: type_code[v["vessel_type_id"]] for v in tables["vessels"]}
    for request in tables["berthing_requests"]:
        wanted = (
            "CONTAINER" if vessel_type[request["vessel_id"]] == "CONTAINER" else "NON_CONTAINER"
        )
        assert terminal_type[request["requested_terminal_id"]] == wanted


def test_minimum_has_only_container_vessels() -> None:
    tables = _scenario(ScenarioSize.MINIMUM, seed=4).tables
    code = {t["id"]: t["code"] for t in tables["vessel_types"]}
    assert {code[v["vessel_type_id"]] for v in tables["vessels"]} == {"CONTAINER"}


def test_requests_fall_inside_the_horizon() -> None:
    requests = _scenario(ScenarioSize.REFERENCE, days=3).tables["berthing_requests"]
    etas = [str(r["requested_eta"]) for r in requests]
    assert min(etas) >= "2026-01-05 00:00:00"
    assert max(etas) < "2026-01-08 00:00:00"


def test_no_real_port_identity() -> None:
    profile = _scenario(ScenarioSize.REFERENCE).tables["port_profiles"][0]
    assert profile["port_code"] is None
    assert str(profile["name"]).startswith("SYNTHETIC")


def test_names_carry_the_label() -> None:
    tables = _scenario(ScenarioSize.REFERENCE).tables
    for table in ("terminals", "vessels", "tugboats", "navigation_channels", "external_systems"):
        assert all(str(row["name"]).startswith("SYNTHETIC") for row in tables[table])


@pytest.mark.parametrize("days", [0, -1])
def test_rejects_bad_days(days: int) -> None:
    with pytest.raises(ValueError, match="days"):
        generate(ScenarioSize.MINIMUM, 1, days)


def test_imo_numbers_are_unique_for_many_seeds() -> None:
    # Seed 59 used to repeat an IMO number, which the UNIQUE key would refuse on load.
    for seed in range(1, 101):
        vessels = _scenario(ScenarioSize.REFERENCE, seed=seed).tables["vessels"]
        imos = [vessel["imo_number"] for vessel in vessels]
        assert len(set(imos)) == len(imos), f"duplicate IMO number with seed {seed}"
