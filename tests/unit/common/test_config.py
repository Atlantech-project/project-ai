import json
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from common.config import (
    AI_SETTING_TYPES,
    KEYS_WITH_APPROVED_VALUE,
    ConfigurationError,
    EnvSettings,
    OptionalEnvVar,
    PortSettings,
    ValueType,
    WorkerPart,
    check_consistency,
    check_startup_settings,
    load_env_settings,
    read_port_settings,
    require_env,
)

SEED_SPEC = (
    Path(__file__).resolve().parents[3] / "docs" / "drafts" / "ai-payloads" / "seed-spec.json"
)

SECRET = "not-a-real-password"
COMPLETE_ENV = {
    "AI_DB_HOST": "db.internal",
    "AI_DB_PORT": "3306",
    "AI_DB_NAME": "portsync",
    "AI_DB_USER_PART2": "w_part2",
    "AI_DB_PASSWORD_PART2": SECRET,
    "AI_REDIS_URL": f"redis://:{SECRET}@redis.internal:6379/0",
}


def _settings(*rows: tuple[str, str, str]) -> PortSettings:
    return PortSettings(rows)


class _FakeCursor:
    def __init__(self, rows: Sequence[tuple[str, str, str]]) -> None:
        self._rows = rows
        self.queries: list[str] = []
        self.closed = False

    def execute(self, query: str) -> int:
        self.queries.append(query)
        return len(self._rows)

    def fetchall(self) -> Sequence[Sequence[Any]]:
        return self._rows

    def close(self) -> None:
        self.closed = True


class _FakeConnection:
    def __init__(self, rows: Sequence[tuple[str, str, str]]) -> None:
        self.rows = rows
        self.cursors: list[_FakeCursor] = []

    def cursor(self) -> _FakeCursor:
        cursor = _FakeCursor(self.rows)
        self.cursors.append(cursor)
        return cursor


def test_error_carries_the_contract_category() -> None:
    assert ConfigurationError("x").error_category == "CONFIGURATION_ERROR"


# Environment


def test_complete_env_loads_the_workers_own_account() -> None:
    assert load_env_settings(COMPLETE_ENV, WorkerPart.PART2) == EnvSettings(
        db_host="db.internal",
        db_port=3306,
        db_name="portsync",
        db_user="w_part2",
        db_password=SECRET,
        redis_url=COMPLETE_ENV["AI_REDIS_URL"],
    )


def test_another_parts_account_does_not_satisfy_this_part() -> None:
    with pytest.raises(ConfigurationError, match="AI_DB_USER_YARD.*AI_DB_PASSWORD_YARD"):
        load_env_settings(COMPLETE_ENV, WorkerPart.YARD)


def test_all_six_dec08_accounts_are_parts() -> None:
    assert {part.value for part in WorkerPart} == {
        "PART1",
        "PART2",
        "YARD",
        "EDI",
        "VALIDATE",
        "PART3",
    }


@pytest.mark.parametrize("key", sorted(COMPLETE_ENV))
def test_each_missing_env_var_is_named(key: str) -> None:
    env = {k: v for k, v in COMPLETE_ENV.items() if k != key}
    with pytest.raises(ConfigurationError, match=key):
        load_env_settings(env, WorkerPart.PART2)


def test_empty_env_var_counts_as_missing() -> None:
    with pytest.raises(ConfigurationError, match="AI_DB_HOST"):
        load_env_settings({**COMPLETE_ENV, "AI_DB_HOST": ""}, WorkerPart.PART2)


def test_every_missing_env_var_is_reported_at_once() -> None:
    with pytest.raises(ConfigurationError) as info:
        load_env_settings({}, WorkerPart.PART2)
    assert set(info.value.keys) == set(COMPLETE_ENV)


@pytest.mark.parametrize("port", ["abc", "0", "65536", "-1", " 3306", "3_306", "٣٣٠٦"])
def test_bad_port_raises(port: str) -> None:
    with pytest.raises(ConfigurationError, match="AI_DB_PORT"):
        load_env_settings({**COMPLETE_ENV, "AI_DB_PORT": port}, WorkerPart.PART2)


@pytest.mark.parametrize(("port", "expected"), [("1", 1), ("65535", 65535)])
def test_boundary_ports_are_valid(port: str, expected: int) -> None:
    settings = load_env_settings({**COMPLETE_ENV, "AI_DB_PORT": port}, WorkerPart.PART2)
    assert settings.db_port == expected


def test_very_long_port_raises_a_configuration_error() -> None:
    with pytest.raises(ConfigurationError, match="AI_DB_PORT"):
        load_env_settings({**COMPLETE_ENV, "AI_DB_PORT": "9" * 5000}, WorkerPart.PART2)


@pytest.mark.parametrize("key", ["AI_DB_HOST", "AI_DB_PASSWORD_PART2"])
def test_blank_env_var_counts_as_missing(key: str) -> None:
    with pytest.raises(ConfigurationError, match=key):
        load_env_settings({**COMPLETE_ENV, key: "   "}, WorkerPart.PART2)


def test_secrets_stay_out_of_repr_and_errors() -> None:
    assert SECRET not in repr(load_env_settings(COMPLETE_ENV, WorkerPart.PART2))
    with pytest.raises(ConfigurationError) as info:
        load_env_settings({**COMPLETE_ENV, "AI_DB_PORT": SECRET}, WorkerPart.PART2)
    assert SECRET not in str(info.value)


def test_require_env_returns_the_values_for_later_tasks() -> None:
    env = {OptionalEnvVar.PROVIDER_PRIMARY.value: "v"}
    assert require_env(env, [OptionalEnvVar.PROVIDER_PRIMARY]) == {"AI_PROVIDER_PRIMARY_KEY": "v"}


def test_optional_env_var_names() -> None:
    assert {name.value for name in OptionalEnvVar} == {
        "AI_PROVIDER_PRIMARY_KEY",
        "AI_PROVIDER_SECONDARY_KEY",
        "AI_ARTIFACT_DIR",
        "AI_BAPLIE_VOLUME",
        "AI_SCHEMA_DIR",
    }


# Typed parsing


@pytest.mark.parametrize(("raw", "expected"), [("10", 10), ("0", 0), ("-3", -3)])
def test_int_values(raw: str, expected: int) -> None:
    assert _settings(("k", raw, "INT")).get_int("k") == expected


@pytest.mark.parametrize("raw", ["", " 5", "5 ", "1_000", "1.5", "1e3", "abc", "٥", "+5"])
def test_bad_int_values_raise(raw: str) -> None:
    with pytest.raises(ConfigurationError, match="'k'"):
        _settings(("k", raw, "INT")).get_int("k")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("10", Decimal("10")), ("1.0", Decimal("1.0")), ("-0.25", Decimal("-0.25"))],
)
def test_decimal_values(raw: str, expected: Decimal) -> None:
    value = _settings(("k", raw, "DECIMAL")).get_decimal("k")
    assert isinstance(value, Decimal)
    assert value == expected


def test_decimal_keeps_digits_that_float_would_lose() -> None:
    raw = "0.12345678901234567890"
    assert Decimal(str(float(raw))) != Decimal(raw)
    assert _settings(("k", raw, "DECIMAL")).get_decimal("k") == Decimal(raw)


@pytest.mark.parametrize(
    "raw", ["", "NaN", "Infinity", "-Infinity", "sNaN", "1e3", "1_000", " 1", ".5", "1.", "٥"]
)
def test_bad_decimal_values_raise(raw: str) -> None:
    with pytest.raises(ConfigurationError, match="'k'"):
        _settings(("k", raw, "DECIMAL")).get_decimal("k")


@pytest.mark.parametrize(
    ("raw", "expected"), [("1", True), ("true", True), ("0", False), ("false", False)]
)
def test_bool_values(raw: str, expected: bool) -> None:
    assert _settings(("k", raw, "BOOL")).get_bool("k") is expected


@pytest.mark.parametrize("raw", ["", "TRUE", "True", "False", "yes", "no", "2", " 1"])
def test_bad_bool_values_raise(raw: str) -> None:
    with pytest.raises(ConfigurationError, match="'k'"):
        _settings(("k", raw, "BOOL")).get_bool("k")


def test_string_is_returned_as_stored() -> None:
    assert _settings(("k", " 0 0 * * * ", "STRING")).get_str("k") == " 0 0 * * * "


def test_json_value() -> None:
    assert _settings(("k", '{"a": [1, 0.5]}', "JSON")).get_json("k") == {"a": [1, 0.5]}


@pytest.mark.parametrize(
    "raw", ["{", "", "NaN", "Infinity", '{"a": -Infinity}', "1e999", "-1e999", "[1e999]", "1E400"]
)
def test_bad_json_values_raise(raw: str) -> None:
    with pytest.raises(ConfigurationError, match="'k'"):
        _settings(("k", raw, "JSON")).get_json("k")


@pytest.mark.parametrize("value_type", ["INT", "DECIMAL", "BOOL", "JSON"])
def test_bad_value_is_not_kept_anywhere_on_the_error(value_type: str) -> None:
    with pytest.raises(ConfigurationError) as info:
        _settings(("k", SECRET, value_type)).check("k", ValueType(value_type))
    assert SECRET not in str(info.value)
    assert info.value.__cause__ is None
    assert info.value.__context__ is None


def test_accessor_must_match_the_rows_type() -> None:
    with pytest.raises(ConfigurationError, match="'k'.*DECIMAL.*INT"):
        _settings(("k", "10", "DECIMAL")).get_int("k")


def test_job_time_read_rejects_a_row_of_the_wrong_ct18_type() -> None:
    settings = _settings(("solver_time_limit_seconds", "10.5", "DECIMAL"))
    with pytest.raises(ConfigurationError, match="solver_time_limit_seconds.*CT-18 says INT"):
        settings.get_decimal("solver_time_limit_seconds")


def test_unknown_value_type_raises() -> None:
    with pytest.raises(ConfigurationError, match="'k'"):
        _settings(("k", "10", "FLOAT")).get_int("k")


def test_missing_key_raises_naming_it_with_no_default() -> None:
    with pytest.raises(ConfigurationError, match="'solver_time_limit_seconds'") as info:
        _settings().get_int("solver_time_limit_seconds")
    assert info.value.keys == ("solver_time_limit_seconds",)


def test_bad_unrelated_row_does_not_affect_a_good_key() -> None:
    settings = _settings(("mock_scenario", "{", "JSON"), ("k", "5", "INT"))
    assert settings.get_int("k") == 5


# Key lists


def test_key_types_match_ct18_section_4() -> None:
    assert AI_SETTING_TYPES == {
        "weather_pull_hours": ValueType.INT,
        "tide_horizon_days": ValueType.INT,
        "part1_stored_data_max_age_hours": ValueType.INT,
        "part1_assessment_horizon_hours": ValueType.INT,
        "part1_time_step_minutes": ValueType.INT,
        "part1_min_window_minutes": ValueType.INT,
        "demand_slot_minutes": ValueType.INT,
        "solver_time_limit_seconds": ValueType.INT,
        "solver_options_per_request": ValueType.INT,
        "solver_option_equivalence_pct": ValueType.DECIMAL,
        "objective_weight_waiting_time": ValueType.DECIMAL,
        "objective_weight_resource": ValueType.DECIMAL,
        "part1_max_retries": ValueType.INT,
        "run_stale_after_seconds": ValueType.INT,
        "validation_timeout_seconds": ValueType.INT,
        "validation_result_ttl_seconds": ValueType.INT,
        "part3_evaluation_cron": ValueType.STRING,
        "drift_psi_threshold": ValueType.DECIMAL,
        "drift_mae_threshold": ValueType.DECIMAL,
    }


def test_approved_keys_match_the_seed_spec_draft_in_name_and_type() -> None:
    spec = json.loads(SEED_SPEC.read_text(encoding="utf-8"))
    seeded = {row["setting_key"]: row["value_type"] for row in spec["port_settings"]}
    assert set(seeded) == KEYS_WITH_APPROVED_VALUE
    assert seeded == {key: AI_SETTING_TYPES[key].value for key in KEYS_WITH_APPROVED_VALUE}


@pytest.mark.parametrize(
    "key",
    [
        "weather_pull_hours",
        "tide_horizon_days",
        "part1_assessment_horizon_hours",
        "part1_time_step_minutes",
        "part1_min_window_minutes",
        "demand_slot_minutes",
        "run_stale_after_seconds",
        "part3_evaluation_cron",
        "drift_psi_threshold",
        "drift_mae_threshold",
    ],
)
def test_pending_keys_have_no_approved_value(key: str) -> None:
    assert key in AI_SETTING_TYPES
    assert key not in KEYS_WITH_APPROVED_VALUE


# Startup check


def test_startup_passes_when_used_approved_keys_are_good() -> None:
    settings = _settings(("solver_time_limit_seconds", "10", "INT"))
    check_startup_settings(settings, ["solver_time_limit_seconds"])


def test_startup_stops_on_every_used_approved_problem_at_once() -> None:
    settings = _settings(("solver_time_limit_seconds", "abc", "INT"))
    with pytest.raises(ConfigurationError) as info:
        check_startup_settings(settings, ["solver_time_limit_seconds", "part1_max_retries"])
    assert set(info.value.keys) == {"solver_time_limit_seconds", "part1_max_retries"}


def test_startup_rejects_a_row_of_the_wrong_ct18_type() -> None:
    settings = _settings(("solver_time_limit_seconds", "10", "DECIMAL"))
    with pytest.raises(ConfigurationError, match="solver_time_limit_seconds"):
        check_startup_settings(settings, ["solver_time_limit_seconds"])


def test_startup_ignores_pending_keys_the_worker_uses() -> None:
    check_startup_settings(_settings(), ["drift_psi_threshold", "run_stale_after_seconds"])


def test_startup_ignores_approved_keys_the_worker_does_not_use() -> None:
    check_startup_settings(_settings(), [])


def test_pending_key_missing_when_a_job_reads_it_fails_with_the_category() -> None:
    settings = _settings()
    check_startup_settings(settings, ["drift_psi_threshold"])
    with pytest.raises(ConfigurationError) as info:
        settings.get_decimal("drift_psi_threshold")
    assert info.value.error_category == "CONFIGURATION_ERROR"


# Cross-field rules (CT-18 §4)


@pytest.mark.parametrize(
    ("window", "step", "ok"),
    [
        ("30", "10", True),
        ("10", "10", True),
        ("25", "10", False),
        ("30", "0", False),
        ("30", "-10", False),
    ],
)
def test_window_must_be_a_multiple_of_the_step(window: str, step: str, ok: bool) -> None:
    settings = _settings(
        ("part1_min_window_minutes", window, "INT"), ("part1_time_step_minutes", step, "INT")
    )
    keys = ["part1_min_window_minutes", "part1_time_step_minutes"]
    if ok:
        check_consistency(settings, keys)
    else:
        with pytest.raises(ConfigurationError, match="part1_min_window_minutes"):
            check_consistency(settings, keys)


@pytest.mark.parametrize(
    ("ttl", "timeout", "ok"), [("600", "15", True), ("16", "15", True), ("15", "15", False)]
)
def test_ttl_must_exceed_the_timeout(ttl: str, timeout: str, ok: bool) -> None:
    settings = _settings(
        ("validation_result_ttl_seconds", ttl, "INT"),
        ("validation_timeout_seconds", timeout, "INT"),
    )
    keys = ["validation_result_ttl_seconds", "validation_timeout_seconds"]
    if ok:
        check_consistency(settings, keys)
    else:
        with pytest.raises(ConfigurationError, match="validation_result_ttl_seconds"):
            check_consistency(settings, keys)


def test_consistency_skips_rules_for_keys_the_worker_does_not_use() -> None:
    settings = _settings(
        ("validation_result_ttl_seconds", "15", "INT"), ("validation_timeout_seconds", "15", "INT")
    )
    check_consistency(settings, ["solver_time_limit_seconds"])


@pytest.mark.parametrize(
    "rows",
    [
        (("part1_min_window_minutes", "25", "INT"), ("part1_time_step_minutes", "10", "INT")),
        (
            ("validation_result_ttl_seconds", "1", "INT"),
            ("validation_timeout_seconds", "9", "INT"),
        ),
    ],
)
@pytest.mark.parametrize("used", [0, 1])
def test_consistency_rule_needs_both_keys_used(
    rows: tuple[tuple[str, str, str], ...], used: int
) -> None:
    check_consistency(PortSettings(rows), [rows[used][0]])


def test_consistency_raises_when_a_used_key_is_missing() -> None:
    settings = _settings(("validation_timeout_seconds", "15", "INT"))
    with pytest.raises(ConfigurationError, match="validation_result_ttl_seconds"):
        check_consistency(settings, ["validation_result_ttl_seconds", "validation_timeout_seconds"])


# Reading


def test_read_uses_one_cursor_and_closes_it() -> None:
    connection = _FakeConnection([("k", "5", "INT")])
    assert read_port_settings(connection).get_int("k") == 5
    assert len(connection.cursors) == 1
    assert connection.cursors[0].queries == [
        "SELECT setting_key, setting_value, value_type FROM port_settings"
    ]
    assert connection.cursors[0].closed


def test_cursor_is_closed_when_the_query_fails() -> None:
    class _FailingCursor(_FakeCursor):
        def execute(self, query: str) -> int:
            raise RuntimeError("query failed")

    cursor = _FailingCursor([])

    class _Connection:
        def cursor(self) -> _FailingCursor:
            return cursor

    with pytest.raises(RuntimeError, match="query failed"):
        read_port_settings(_Connection())
    assert cursor.closed


def test_every_read_queries_again_and_sees_the_new_value() -> None:
    connection = _FakeConnection([("k", "5", "INT")])
    first = read_port_settings(connection)
    connection.rows = [("k", "6", "INT")]
    second = read_port_settings(connection)
    assert second.get_int("k") == 6
    assert first.get_int("k") == 5
    assert len(connection.cursors) == 2


def test_value_type_enum_matches_the_db_enum() -> None:
    assert {member.value for member in ValueType} == {"INT", "DECIMAL", "BOOL", "STRING", "JSON"}
