"""Worker configuration, from the environment and `port_settings` (AI-012).

Secrets and endpoints come from environment variables; a missing one stops the worker at
startup. Runtime-changeable values come from `port_settings`, read per job without cache
(DEC-12, CT-18 §4): that is the refresh rule, so a saved change applies from the next read.
Values are never defaulted in code. Errors name the key, never the value.

Use an autocommit connection, or commit or roll back after every read. On a non-autocommit
connection the read itself opens a transaction, and MySQL's default REPEATABLE READ then keeps
returning the old values until it ends.
"""

import json
import math
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any, ClassVar, Final, Protocol

_READ_QUERY: Final = "SELECT setting_key, setting_value, value_type FROM port_settings"

_INT_TEXT: Final = re.compile(r"-?[0-9]+")
_PORT_TEXT: Final = re.compile(r"[0-9]{1,5}")
_DECIMAL_TEXT: Final = re.compile(r"-?[0-9]+(\.[0-9]+)?")
_BOOL_TEXT: Final[Mapping[str, bool]] = {"1": True, "true": True, "0": False, "false": False}
_MAX_PORT: Final = 65535


class ConfigurationError(ValueError):
    """Configuration is missing or unusable. During a job it maps to CONFIGURATION_ERROR (CT-08)."""

    error_category: ClassVar[str] = "CONFIGURATION_ERROR"

    def __init__(self, message: str, keys: Iterable[str] = ()) -> None:
        super().__init__(message)
        self.keys = tuple(keys)


class ValueType(StrEnum):
    """The values of `port_settings.value_type`."""

    INT = "INT"
    DECIMAL = "DECIMAL"
    BOOL = "BOOL"
    STRING = "STRING"
    JSON = "JSON"


class WorkerPart(StrEnum):
    """One per DEC-08 worker account; the suffix of the per-part environment variables."""

    PART1 = "PART1"
    PART2 = "PART2"
    YARD = "YARD"
    EDI = "EDI"
    VALIDATE = "VALIDATE"
    PART3 = "PART3"


class OptionalEnvVar(StrEnum):
    """Variables only some workers need; those workers ask for them with `require_env`."""

    PROVIDER_PRIMARY = "AI_PROVIDER_PRIMARY_KEY"
    PROVIDER_SECONDARY = "AI_PROVIDER_SECONDARY_KEY"
    ARTIFACT_DIR = "AI_ARTIFACT_DIR"
    BAPLIE_VOLUME = "AI_BAPLIE_VOLUME"
    # Where the contract schemas are; defaults to the docs/ref mirror only in a checkout (AI-011).
    SCHEMA_DIR = "AI_SCHEMA_DIR"


# CT-18 §4: every AI key and its type. Values belong to the seed, never to this module.
AI_SETTING_TYPES: Final[Mapping[str, ValueType]] = {
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

# The keys with an approved value in CT-18 §4 today. The other keys are still ⟨AI⟩ (CT-18 §7), so
# the startup check skips them; otherwise no worker could start. Move a key here once its value
# is approved.
KEYS_WITH_APPROVED_VALUE: Final[frozenset[str]] = frozenset(
    {
        "part1_stored_data_max_age_hours",
        "solver_time_limit_seconds",
        "solver_options_per_request",
        "solver_option_equivalence_pct",
        "objective_weight_waiting_time",
        "objective_weight_resource",
        "part1_max_retries",
        "validation_timeout_seconds",
        "validation_result_ttl_seconds",
    }
)


def require_env(env: Mapping[str, str], keys: Iterable[str]) -> dict[str, str]:
    """Return the named variables, or raise naming every one that is missing or blank."""
    names = [str(key) for key in keys]
    missing = [name for name in names if not env.get(name, "").strip()]
    if missing:
        raise ConfigurationError(f"Missing environment variables: {', '.join(missing)}", missing)
    return {name: env[name] for name in names}


@dataclass(frozen=True)
class EnvSettings:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str = field(repr=False)
    # A Redis URL can hold a password.
    redis_url: str = field(repr=False)


def load_env_settings(env: Mapping[str, str], part: WorkerPart) -> EnvSettings:
    """Load the database and Redis settings every worker needs, with this part's own account."""
    user_key = f"AI_DB_USER_{part}"
    password_key = f"AI_DB_PASSWORD_{part}"
    values = require_env(
        env,
        ["AI_DB_HOST", "AI_DB_PORT", "AI_DB_NAME", user_key, password_key, "AI_REDIS_URL"],
    )
    port_text = values["AI_DB_PORT"]
    if not _PORT_TEXT.fullmatch(port_text) or not 1 <= int(port_text) <= _MAX_PORT:
        raise ConfigurationError("AI_DB_PORT must be a port number", ["AI_DB_PORT"])
    return EnvSettings(
        db_host=values["AI_DB_HOST"],
        db_port=int(port_text),
        db_name=values["AI_DB_NAME"],
        db_user=values[user_key],
        db_password=values[password_key],
        redis_url=values["AI_REDIS_URL"],
    )


def _bad_value(key: str, value_type: ValueType) -> ConfigurationError:
    return ConfigurationError(f"port_settings key {key!r} is not a valid {value_type}", [key])


def _reject_json_constant(_: str) -> None:
    raise ValueError("NaN and Infinity are not JSON")


def _finite_json_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("JSON numbers must be finite")
    return value


def _parse_int(key: str, raw: str) -> int:
    if not _INT_TEXT.fullmatch(raw):
        raise _bad_value(key, ValueType.INT)
    return int(raw)


def _parse_decimal(key: str, raw: str) -> Decimal:
    if not _DECIMAL_TEXT.fullmatch(raw):
        raise _bad_value(key, ValueType.DECIMAL)
    return Decimal(raw)


def _parse_bool(key: str, raw: str) -> bool:
    if raw not in _BOOL_TEXT:
        raise _bad_value(key, ValueType.BOOL)
    return _BOOL_TEXT[raw]


def _parse_string(_: str, raw: str) -> str:
    return raw


def _parse_json(key: str, raw: str) -> Any:
    try:
        return json.loads(raw, parse_constant=_reject_json_constant, parse_float=_finite_json_float)
    except ValueError:
        pass
    # Raised outside the except block, so the decode error holding the raw value isn't attached.
    raise _bad_value(key, ValueType.JSON)


_PARSERS: Final[Mapping[ValueType, Callable[[str, str], object]]] = {
    ValueType.INT: _parse_int,
    ValueType.DECIMAL: _parse_decimal,
    ValueType.BOOL: _parse_bool,
    ValueType.STRING: _parse_string,
    ValueType.JSON: _parse_json,
}


class PortSettings:
    """One read of `port_settings`. Values are parsed when asked for, so a bad row fails only
    the jobs that use it, and a tester's `mock_scenario` can't affect anything else."""

    def __init__(self, rows: Iterable[Sequence[Any]]) -> None:
        self._rows: Mapping[str, tuple[str, str]] = {
            key: (value, value_type) for key, value, value_type in rows
        }

    def _raw(self, key: str, value_type: ValueType) -> str:
        if key not in self._rows:
            raise ConfigurationError(f"port_settings key {key!r} is missing", [key])
        raw, stored_type = self._rows[key]
        if stored_type != value_type:
            raise ConfigurationError(
                f"port_settings key {key!r} has value_type {stored_type}, read as {value_type}",
                [key],
            )
        expected_type = AI_SETTING_TYPES.get(key, value_type)
        if value_type != expected_type:
            raise ConfigurationError(
                f"port_settings key {key!r} has value_type {stored_type}, "
                f"CT-18 says {expected_type}",
                [key],
            )
        return raw

    def get_int(self, key: str) -> int:
        return _parse_int(key, self._raw(key, ValueType.INT))

    def get_decimal(self, key: str) -> Decimal:
        return _parse_decimal(key, self._raw(key, ValueType.DECIMAL))

    def get_bool(self, key: str) -> bool:
        return _parse_bool(key, self._raw(key, ValueType.BOOL))

    def get_str(self, key: str) -> str:
        return _parse_string(key, self._raw(key, ValueType.STRING))

    def get_json(self, key: str) -> Any:
        return _parse_json(key, self._raw(key, ValueType.JSON))

    def check(self, key: str, value_type: ValueType) -> None:
        """Raise unless the key is present, has this type and parses."""
        _PARSERS[value_type](key, self._raw(key, value_type))


class _Cursor(Protocol):
    def execute(self, query: str) -> object: ...

    def fetchall(self) -> Iterable[Sequence[Any]]: ...

    def close(self) -> object: ...


class DbConnection(Protocol):
    """The part of a DB-API connection this module needs; AI-013 owns the connections."""

    def cursor(self) -> _Cursor: ...


def read_port_settings(connection: DbConnection) -> PortSettings:
    """Read the table now. Call once per job and keep nothing (DEC-12); see the module docstring."""
    cursor = connection.cursor()
    try:
        cursor.execute(_READ_QUERY)
        return PortSettings(cursor.fetchall())
    finally:
        cursor.close()


def check_startup_settings(settings: PortSettings, used_keys: Iterable[str]) -> None:
    """Raise, naming every problem, for keys this worker uses that have an approved value.

    Other keys are read when a job needs them; a problem then fails that job only.
    """
    problems: list[ConfigurationError] = []
    for key in used_keys:
        if key in KEYS_WITH_APPROVED_VALUE:
            try:
                settings.check(key, AI_SETTING_TYPES[key])
            except ConfigurationError as error:
                problems.append(error)
    if problems:
        raise ConfigurationError(
            "; ".join(str(problem) for problem in problems),
            [key for problem in problems for key in problem.keys],
        )


def check_consistency(settings: PortSettings, used_keys: Iterable[str]) -> None:
    """Check the CT-18 §4 cross-field rules whose keys this worker uses.

    The third rule (`run_stale_after_seconds`) needs a value the AI Team has not computed yet.
    """
    used = set(used_keys)
    if {"part1_min_window_minutes", "part1_time_step_minutes"} <= used:
        window = settings.get_int("part1_min_window_minutes")
        step = settings.get_int("part1_time_step_minutes")
        if step <= 0 or window % step != 0:
            raise ConfigurationError(
                "part1_min_window_minutes must be a multiple of part1_time_step_minutes",
                ["part1_min_window_minutes", "part1_time_step_minutes"],
            )
    if {"validation_result_ttl_seconds", "validation_timeout_seconds"} <= used:
        ttl = settings.get_int("validation_result_ttl_seconds")
        timeout = settings.get_int("validation_timeout_seconds")
        if ttl <= timeout:
            raise ConfigurationError(
                "validation_result_ttl_seconds must be greater than validation_timeout_seconds",
                ["validation_result_ttl_seconds", "validation_timeout_seconds"],
            )
