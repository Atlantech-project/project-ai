"""The real port schema and worker accounts for the AI-013 tests, and the published matrix.

The database is built from the PortHub mirror, including its Worker roles section. Accounts follow
`php artisan atlantech:worker-accounts`: for each one CREATE USER, ALTER USER, GRANT role, SET
DEFAULT ROLE, with host `%`. CT-17 asks for the Backend's docker compose; these tests use the CI
services instead, a deviation recorded in `docs/tasks/status/AI-013.md`.
"""

import hashlib
import json
import re
import secrets
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import pymysql
from pymysql.constants import CLIENT

from common.config import WorkerPart
from common.db.connection import dispose_engines
from tests.support.services import ServiceSettings

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
SCHEMA_PATH: Final = REPO_ROOT / "docs" / "ref" / "db" / "schema.sql"
MANIFEST_PATH: Final = REPO_ROOT / "docs" / "ref" / "db" / "schema.sql.source.json"
OWNERSHIP_PATH: Final = REPO_ROOT / "docs" / "ref" / "ai-payloads" / "table-ownership.md"
ACCOUNTS: Final[Mapping[WorkerPart, tuple[str, str]]] = {
    WorkerPart.PART1: ("w_part1", "r_part1"),
    WorkerPart.PART2: ("w_part2", "r_part2"),
    WorkerPart.YARD: ("w_yard", "r_yard"),
    WorkerPart.EDI: ("w_edi", "r_edi"),
    WorkerPart.VALIDATE: ("w_validate", "r_validate"),
    WorkerPart.PART3: ("w_part3", "r_part3"),
}


def mirror_problem(schema_path: Path, manifest_path: Path) -> str | None:
    """Why the schema copy doesn't match its manifest, or None. Needs no network."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual = hashlib.sha256(schema_path.read_bytes()).hexdigest()
    if actual != manifest["sha256"]:
        return f"{schema_path.name} has SHA-256 {actual}, the manifest records {manifest['sha256']}"
    if not re.fullmatch(r"[0-9a-f]{40}", manifest["source_commit"]):
        return f"source_commit isn't a full commit id: {manifest['source_commit']}"
    return None


@dataclass(frozen=True)
class Ownership:
    """The parsed matrix: `readable` maps a table to the columns it limits reads to, or None."""

    readable: Mapping[str, frozenset[str] | None]
    hidden: frozenset[str]
    inserts: Mapping[str, frozenset[str]]
    updates: Mapping[str, Mapping[str, frozenset[str]]]


def _section(text: str, number: int) -> str:
    match = re.search(rf"^## {number}\. .*?(?=^## )", text, re.MULTILINE | re.DOTALL)
    if match is None:
        raise ValueError(f"table-ownership.md has no section {number}")
    return match.group(0)


def _rows(section: str) -> list[list[str]]:
    lines = [line for line in section.splitlines() if line.startswith("| ")]
    return [[cell.strip() for cell in line.strip("|").split(" | ")] for line in lines[2:]]


def parse_ownership(text: str) -> Ownership:
    readable: dict[str, frozenset[str] | None] = {}
    for number in (1, 2, 3):
        for row in _rows(_section(text, number)):
            table = row[0].strip("`")
            limited = re.fullmatch(r"All workers, columns: (.+)", row[-1])
            if limited is None and not row[-1].startswith("All workers"):
                raise ValueError(f"unknown read rule for {table}: {row[-1]}")
            readable[table] = None if limited is None else frozenset(limited[1].split(", "))
    hidden = frozenset(row[0].strip("`") for row in _rows(_section(text, 4)))
    inserts: dict[str, frozenset[str]] = {}
    updates: dict[str, dict[str, frozenset[str]]] = {}
    for row in _rows(_section(text, 5)):
        account = re.findall(r"`(\w+)`", row[0])[0]
        inserts[account] = frozenset(re.findall(r"`(\w+)`", row[2]))
        updates[account] = {
            table: frozenset(columns.split(", "))
            for table, columns in re.findall(r"`(\w+)` \(([^)]+)\)", row[3])
        }
    return Ownership(readable, hidden, inserts, updates)


Privileges = dict[str, frozenset[str] | None]


def expected_role_grants(ownership: Ownership, user: str) -> dict[str, Privileges]:
    """What the matrix says a role holds: table -> privilege -> its columns, or None for all."""
    expected: dict[str, Privileges] = {
        table: {"SELECT": columns} for table, columns in ownership.readable.items()
    }
    for table in ownership.inserts[user]:
        expected[table]["INSERT"] = None
    for table, columns in ownership.updates[user].items():
        expected[table]["UPDATE"] = columns
    return expected


def parse_role_grants(lines: Iterable[str], database: str) -> dict[str, Privileges]:
    """`SHOW GRANTS` as the same shape. Any other scope is kept under its full name."""
    parsed: dict[str, Privileges] = {}
    for line in lines:
        match = re.fullmatch(r"GRANT (.+) ON (\S+) TO \S+", line)
        if match is None:
            raise ValueError(f"unknown grant line: {line}")
        privileges = {
            name: None if columns == "" else frozenset(re.findall(r"`(\w+)`", columns))
            for name, columns in re.findall(r"([A-Z][A-Z ]*?)(?: \(([^)]*)\))?(?:, |$)", match[1])
        }
        scope = match[2]
        if scope == "*.*" and privileges == {"USAGE": None}:
            continue
        table = re.fullmatch(rf"`{re.escape(database)}`\.`(\w+)`", scope)
        parsed[table[1] if table else scope] = privileges
    return parsed


def load_ownership() -> Ownership:
    return parse_ownership(OWNERSHIP_PATH.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class PortDatabase:
    name: str
    service: ServiceSettings
    passwords: Mapping[WorkerPart, str]

    def root(self) -> pymysql.connections.Connection[Any]:
        return pymysql.connect(
            host=self.service.mysql_host,
            port=self.service.mysql_port,
            user=self.service.mysql_user,
            password=self.service.mysql_password,
            database=self.name,
            charset="utf8mb4",
            init_command=(
                "SET time_zone = '+00:00', foreign_key_checks = 0, innodb_lock_wait_timeout = 5"
            ),
        )

    def worker_env(self, part: WorkerPart) -> dict[str, str]:
        """The variables a deployed worker gets, as `load_env_settings` reads them."""
        return {
            "AI_DB_HOST": self.service.mysql_host,
            "AI_DB_PORT": str(self.service.mysql_port),
            "AI_DB_NAME": self.name,
            f"AI_DB_USER_{part}": ACCOUNTS[part][0],
            f"AI_DB_PASSWORD_{part}": self.passwords[part],
            "AI_REDIS_URL": self.service.redis_url,
        }


def _root_session(service: ServiceSettings) -> pymysql.connections.Connection[Any]:
    return pymysql.connect(
        host=service.mysql_host,
        port=service.mysql_port,
        user=service.mysql_user,
        password=service.mysql_password,
        charset="utf8mb4",
        client_flag=CLIENT.MULTI_STATEMENTS,
    )


def create_port_database(service: ServiceSettings) -> PortDatabase:
    name = f"ai013_{secrets.token_hex(6)}"
    passwords = {part: secrets.token_urlsafe(24) for part in ACCOUNTS}
    conn = _root_session(service)
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE `{name}`")
            cursor.execute(f"USE `{name}`")
            # The whole file, with the mysqldump session settings and the Worker roles section.
            cursor.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
            while cursor.nextset():
                pass
            for part, (user, role) in ACCOUNTS.items():
                cursor.execute(
                    f"CREATE USER IF NOT EXISTS '{user}'@'%%' IDENTIFIED BY %s", (passwords[part],)
                )
                cursor.execute(f"ALTER USER '{user}'@'%%' IDENTIFIED BY %s", (passwords[part],))
                cursor.execute(f"GRANT '{role}' TO '{user}'@'%'")
                cursor.execute(f"SET DEFAULT ROLE '{role}' TO '{user}'@'%'")
    finally:
        conn.close()
    return PortDatabase(name, service, passwords)


def drop_port_database(database: PortDatabase) -> None:
    # A pooled session holding a lock would make DROP DATABASE wait forever.
    dispose_engines()
    conn = _root_session(database.service)
    try:
        with conn.cursor() as cursor:
            for user, role in ACCOUNTS.values():
                cursor.execute(f"DROP USER IF EXISTS '{user}'@'%'")
                cursor.execute(f"DROP ROLE IF EXISTS '{role}'")
            cursor.execute(f"DROP DATABASE IF EXISTS `{database.name}`")
    finally:
        conn.close()


# Values that pass the schema's CHECK constraints, where a placeholder doesn't.
_CHECK_SAFE: Final[Mapping[str, Mapping[str, object]]] = {
    "baplie_files": {"file_hash_sha256": "0" * 64},
    "blocked_periods": {"period_start": "2026-11-03", "period_end": "2026-11-04"},
    "demand_forecast_slots": {
        "slot_start": "2026-11-03",
        "slot_end": "2026-11-04",
        "congestion_score": 0,
    },
    "drift_measurements": {"metric_type": "ROLLING_MAE"},
    "evaluation_metrics": {
        "metric_name": "WINDOW_ACCURACY",
        "period_start": "2026-11-03",
        "period_end": "2026-11-04",
    },
    "feasible_windows": {"window_start": "2026-11-03", "window_end": "2026-11-04"},
    "recommendation_options": {"planned_start": "2026-11-03", "planned_end": "2026-11-04"},
    "recommendation_rationale_factors": {"factor_type": "CONSTRAINT", "constraint_type_id": 1},
    "solver_runs": {"horizon_start": "2026-11-03", "horizon_end": "2026-11-04"},
    "tide_prediction_runs": {"horizon_start": "2026-11-03", "horizon_end": "2026-11-04"},
    "vessels": {"loa": 100, "beam": 20, "max_draft": 10, "imo_number": "1234567"},
}


def is_generated_column(extra: str) -> bool:
    """From `information_schema.columns.extra`, where DEFAULT_GENERATED only marks a default."""
    return "STORED GENERATED" in extra or "VIRTUAL GENERATED" in extra


def _placeholder(column_type: str, data_type: str) -> object:
    enum = re.match(r"enum\('([^']*)'", column_type)
    if enum:
        return enum[1]
    if data_type in {"datetime", "timestamp"}:
        return "2026-11-03 10:00:00"
    if data_type in {"char", "varchar", "text", "mediumtext", "longtext"}:
        return "X"
    return 1


def required_row(
    root: pymysql.connections.Connection[Any], table: str, overrides: Mapping[str, object]
) -> dict[str, object]:
    """A row with a value for every column the table requires, then the overrides."""
    with root.cursor() as cursor:
        cursor.execute(
            "SELECT column_name, column_type, data_type FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = %s AND is_nullable = 'NO' "
            "AND column_default IS NULL AND extra NOT LIKE '%%auto_increment%%' "
            "AND extra NOT LIKE '%%STORED GENERATED%%' AND extra NOT LIKE '%%VIRTUAL GENERATED%%'",
            (table,),
        )
        row = {name: _placeholder(ctype, dtype) for name, ctype, dtype in cursor.fetchall()}
    return row | dict(_CHECK_SAFE.get(table, {})) | dict(overrides)


def seed_row(root: pymysql.connections.Connection[Any], table: str, **overrides: object) -> int:
    """Insert a row as the Backend would, with foreign key checks off, committed. Returns its id."""
    row = required_row(root, table, overrides)
    names = ", ".join(f"`{name}`" for name in row)
    marks = ", ".join(["%s"] * len(row))
    with root.cursor() as cursor:
        cursor.execute(f"INSERT INTO `{table}` ({names}) VALUES ({marks})", tuple(row.values()))  # noqa: S608
        new_id = cursor.lastrowid
    root.commit()
    return int(new_id)
