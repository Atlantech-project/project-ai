"""Checks the AI seed specification against CT-18 v1.0 (AI-009)."""

import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pytest

SEED_SPEC = (
    Path(__file__).resolve().parents[3] / "docs" / "drafts" / "ai-payloads" / "seed-spec.json"
)

# CT-18 §2 section order.
SECTIONS = [
    "constraint_types",
    "safety_constraints",
    "objective_terms",
    "rationale_templates",
    "ml_models",
    "ml_model_versions",
    "port_settings",
]

# DB enums, ClassDiagramContext.md lines 139 and 263.
CONSTRAINT_CATEGORY = {"ENVIRONMENTAL", "UKC", "VESSEL_SAFETY"}
CONSTRAINT_UNIT = {
    "KNOTS",
    "METRES_PER_SECOND",
    "METRES",
    "NAUTICAL_MILES",
    "PERCENT",
    "DEGREES",
    "MINUTES",
    "TONNES",
}
CONSTRAINT_COMPARATOR = {"MAX_ALLOWED", "MIN_REQUIRED"}
SETTING_VALUE_TYPE = {"INT", "DECIMAL", "BOOL", "STRING", "JSON"}
MODEL_KEY = {"M2_SERVICE_TIME", "M3_DEMAND_FORECAST", "M4_DELAY_RISK", "FORECAST_BIAS_CORRECTION"}
MODEL_VERSION_STATUS = {"CHALLENGER", "CHAMPION", "ARCHIVED", "REJECTED"}

# CT-18 §6 placeholder list.
PLACEHOLDERS = {
    "vessel",
    "berth",
    "terminal",
    "etb",
    "waiting_minutes",
    "delta_minutes",
    "tug_count",
    "window_start",
    "window_end",
    "constraint",
    "value",
    "limit",
    "unit",
}

# Rows delivered in spec 1.0. Later minor versions add rows; they never change these.
DELIVERED_CONSTRAINT_TYPES = {
    "MAX_WIND_KN": ("ENVIRONMENTAL", "KNOTS", "MAX_ALLOWED", True),
    "MIN_UKC_M": ("UKC", "METRES", "MIN_REQUIRED", True),
    "MAX_WAVE_HEIGHT_M": ("ENVIRONMENTAL", "METRES", "MAX_ALLOWED", True),
}
DELIVERED_OBJECTIVE_TERMS = {
    "WAITING_TIME": "Vessel waiting time",
    "RESOURCE_COST": "Resource cost",
}
DELIVERED_ML_MODELS = {
    "M2_SERVICE_TIME": "GRADIENT_BOOSTING",
    "M3_DEMAND_FORECAST": "GRADIENT_BOOSTING",
    "M4_DELAY_RISK": "GRADIENT_BOOSTING",
}
# CT-18 §4: (value_type, value, min, max).
DELIVERED_PORT_SETTINGS = {
    "part1_stored_data_max_age_hours": ("INT", "48", 1, 168),
    "solver_time_limit_seconds": ("INT", "10", 1, 120),
    "solver_options_per_request": ("INT", "3", 1, 3),
    "solver_option_equivalence_pct": ("DECIMAL", "10", 0, 50),
    "objective_weight_waiting_time": ("DECIMAL", "1.0", 0, 10),
    "objective_weight_resource": ("DECIMAL", "1.0", 0, 10),
    "part1_max_retries": ("INT", "3", 0, 10),
    "validation_timeout_seconds": ("INT", "15", 5, 60),
    "validation_result_ttl_seconds": ("INT", "600", 60, 3600),
}


@pytest.fixture(scope="module")
def spec() -> dict[str, Any]:
    with SEED_SPEC.open(encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return data


def _keys_anywhere(node: Any) -> list[str]:
    if isinstance(node, dict):
        keys = list(node)
        for value in node.values():
            keys.extend(_keys_anywhere(value))
        return keys
    if isinstance(node, list):
        return [key for item in node for key in _keys_anywhere(item)]
    return []


def _values_for_key(node: Any, key: str) -> list[Any]:
    if isinstance(node, dict):
        found = [node[key]] if key in node else []
        for value in node.values():
            found.extend(_values_for_key(value, key))
        return found
    if isinstance(node, list):
        return [value for item in node for value in _values_for_key(item, key)]
    return []


def test_top_level_shape(spec: dict[str, Any]) -> None:
    assert list(spec) == ["spec_version", *SECTIONS]
    assert re.fullmatch(r"1\.\d+", spec["spec_version"])
    for section in SECTIONS:
        assert isinstance(spec[section], list), section


def test_codes_never_ids(spec: dict[str, Any]) -> None:
    offending = [k for k in _keys_anywhere(spec) if k == "id" or k.endswith("_id")]
    assert offending == []


def test_constraint_types(spec: dict[str, Any]) -> None:
    rows = spec["constraint_types"]
    codes = [row["code"] for row in rows]
    assert len(codes) == len(set(codes))
    for row in rows:
        assert set(row) == {
            "code",
            "category",
            "unit",
            "comparator",
            "is_hard_safety_limit",
            "description",
        }
        assert re.fullmatch(r"[A-Z][A-Z0-9_]*", row["code"]) and len(row["code"]) <= 60
        assert row["category"] in CONSTRAINT_CATEGORY
        assert row["unit"] in CONSTRAINT_UNIT
        assert row["comparator"] in CONSTRAINT_COMPARATOR
        assert isinstance(row["is_hard_safety_limit"], bool)
        assert isinstance(row["description"], str) and row["description"].strip()


def test_constraint_type_references_exist(spec: dict[str, Any]) -> None:
    codes = {row["code"] for row in spec["constraint_types"]}
    referenced = _values_for_key(spec, "constraint_type_code")
    assert [code for code in referenced if code not in codes] == []


def test_objective_terms(spec: dict[str, Any]) -> None:
    rows = spec["objective_terms"]
    for row in rows:
        assert set(row) == {"code", "name"}
    assert {row["code"]: row["name"] for row in rows} == DELIVERED_OBJECTIVE_TERMS
    assert len(rows) == len(DELIVERED_OBJECTIVE_TERMS)


def test_ml_models(spec: dict[str, Any]) -> None:
    rows = spec["ml_models"]
    keys = [row["model_key"] for row in rows]
    assert len(keys) == len(set(keys))
    for row in rows:
        assert set(row) == {"model_key", "algorithm_family", "description"}
        assert row["model_key"] in MODEL_KEY
        family = row["algorithm_family"]
        assert isinstance(family, str) and family.strip() and len(family) <= 40
        assert isinstance(row["description"], str) and row["description"].strip()


def test_ml_model_versions(spec: dict[str, Any]) -> None:
    model_keys = {row["model_key"] for row in spec["ml_models"]}
    champions: list[str] = []
    seen: set[tuple[str, int]] = set()
    for row in spec["ml_model_versions"]:
        assert row["model_key"] in model_keys
        assert row["status"] in MODEL_VERSION_STATUS
        assert isinstance(row["version_no"], int) and row["version_no"] > 0
        assert (row["model_key"], row["version_no"]) not in seen
        seen.add((row["model_key"], row["version_no"]))
        if row["status"] == "CHAMPION":
            champions.append(row["model_key"])
    assert len(champions) == len(set(champions))


def test_rationale_templates(spec: dict[str, Any]) -> None:
    seen: set[tuple[str, int]] = set()
    for row in spec["rationale_templates"]:
        assert isinstance(row["version"], int) and row["version"] > 0
        assert (row["code"], row["version"]) not in seen
        seen.add((row["code"], row["version"]))
        assert set(re.findall(r"\{(\w+)\}", row["template_text"])) <= PLACEHOLDERS


def _number(text: str, value_type: str) -> Decimal:
    if value_type == "INT":
        assert re.fullmatch(r"-?\d+", text), text
    try:
        return Decimal(text)
    except InvalidOperation:
        pytest.fail(f"not a number: {text!r}")


def test_port_settings(spec: dict[str, Any]) -> None:
    rows = spec["port_settings"]
    keys = [row["setting_key"] for row in rows]
    assert len(keys) == len(set(keys))
    by_key = {}
    for row in rows:
        value_type = row["value_type"]
        assert value_type in SETTING_VALUE_TYPE
        assert isinstance(row["value"], str)
        assert isinstance(row["description"], str) and row["description"].strip()
        if value_type in {"STRING", "JSON", "BOOL"}:
            assert "min" not in row and "max" not in row
        else:
            value = _number(row["value"], value_type)
            assert row.get("min", value) <= value <= row.get("max", value)
        by_key[row["setting_key"]] = row
    if {"validation_timeout_seconds", "validation_result_ttl_seconds"} <= set(by_key):
        ttl = int(by_key["validation_result_ttl_seconds"]["value"])
        timeout = int(by_key["validation_timeout_seconds"]["value"])
        assert ttl > timeout


def test_port_setting_bounds_are_optional(spec: dict[str, Any]) -> None:
    # CT-18 §4 leaves min and max blank for the DEC-24 keys, which later minor versions add.
    row = {"setting_key": "unbounded", "value_type": "INT", "value": "1", "description": "x"}
    test_port_settings({**spec, "port_settings": [*spec["port_settings"], row]})


def test_delivered_rows_match_contract(spec: dict[str, Any]) -> None:
    constraint_types = {row["code"]: row for row in spec["constraint_types"]}
    for code, (category, unit, comparator, hard) in DELIVERED_CONSTRAINT_TYPES.items():
        row = constraint_types[code]
        assert (row["category"], row["unit"], row["comparator"], row["is_hard_safety_limit"]) == (
            category,
            unit,
            comparator,
            hard,
        )
    assert constraint_types["MAX_WIND_KN"]["description"] == "Maximum sustained wind for entry"

    ml_models = {row["model_key"]: row for row in spec["ml_models"]}
    for key, family in DELIVERED_ML_MODELS.items():
        assert ml_models[key]["algorithm_family"] == family
    assert ml_models["M2_SERVICE_TIME"]["description"] == "Berth service time (P50 / P90)"

    port_settings = {row["setting_key"]: row for row in spec["port_settings"]}
    for key, (value_type, value, low, high) in DELIVERED_PORT_SETTINGS.items():
        row = port_settings[key]
        assert (row["value_type"], row["value"], row["min"], row["max"]) == (
            value_type,
            value,
            low,
            high,
        )
    assert (
        port_settings["solver_time_limit_seconds"]["description"] == "CP-SAT time limit per solve"
    )
