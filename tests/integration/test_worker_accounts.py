"""AI-013: each worker's real account can do what table-ownership.md lists, and nothing else.

Every probe is a statement MySQL checks privileges for before it touches a row: `WHERE 1 = 0` and
`LIMIT 0` change nothing. Errors 1142 and 1143 mean refused; any other error fails the test.
"""

import contextlib
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any

import pymysql
import pytest

from common.config import WorkerPart, load_env_settings
from common.db.connection import WorkerConnection, connect_worker
from tests.support.port_db import (
    ACCOUNTS,
    Ownership,
    PortDatabase,
    expected_role_grants,
    is_generated_column,
    load_ownership,
    parse_role_grants,
)

pytestmark = pytest.mark.integration

_REFUSED = {1142, 1143}
# Administration and DDL can also be refused as: 1044 database, 1227 a global privilege.
_ADMIN_REFUSED = {1044, 1045, 1142, 1143, 1227, 1370, 1410}
PARTS = list(ACCOUNTS)
LARAVEL_TABLES = 8


@dataclass(frozen=True)
class SchemaFacts:
    columns: Mapping[str, list[str]]
    generated: Mapping[str, frozenset[str]]


@pytest.fixture(scope="module")
def schema(port_db: PortDatabase) -> SchemaFacts:
    root = port_db.root()
    columns: dict[str, list[str]] = {}
    generated: dict[str, set[str]] = {}
    try:
        with root.cursor() as cursor:
            cursor.execute(
                "SELECT table_name, column_name, extra FROM information_schema.columns "
                "WHERE table_schema = DATABASE() ORDER BY table_name, ordinal_position"
            )
            for table, column, extra in cursor.fetchall():
                columns.setdefault(table, []).append(column)
                generated.setdefault(table, set())
                if is_generated_column(extra):
                    generated[table].add(column)
    finally:
        root.close()
    return SchemaFacts(columns, {t: frozenset(c) for t, c in generated.items()})


@pytest.fixture(scope="module")
def ownership() -> Ownership:
    return load_ownership()


@pytest.fixture
def account(request: pytest.FixtureRequest, port_db: PortDatabase) -> Iterator[WorkerConnection]:
    part: WorkerPart = request.param
    connection = connect_worker(load_env_settings(port_db.worker_env(part), part))
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


def _allowed(connection: WorkerConnection, sql: str, refused: set[int] = _REFUSED) -> bool:
    cursor = connection.cursor()
    try:
        cursor.execute(sql)
        cursor.fetchall()
    except pymysql.err.MySQLError as error:
        if error.args[0] in refused:
            return False
        raise
    finally:
        cursor.close()
    return True


def _rights(connection: WorkerConnection, schema: SchemaFacts) -> dict[str, dict[str, Any]]:
    """What the server really allows this account, on every table and column."""
    actual: dict[str, dict[str, Any]] = {}
    for table, columns in schema.columns.items():
        plain = [c for c in columns if c not in schema.generated[table]]
        names = ", ".join(f"`{c}`" for c in plain)
        actual[table] = {
            "select": {
                c
                for c in columns
                if _allowed(connection, f"SELECT `{c}` FROM `{table}` LIMIT 0")  # noqa: S608
            },
            "update": {
                c
                for c in plain
                if _allowed(connection, f"UPDATE `{table}` SET `{c}` = NULL WHERE 1 = 0")  # noqa: S608
            },
            "insert": _allowed(
                connection,
                f"INSERT INTO `{table}` ({names}) SELECT {names} FROM `{table}` WHERE 1 = 0",  # noqa: S608
            ),
            "delete": _allowed(connection, f"DELETE FROM `{table}` WHERE 1 = 0"),  # noqa: S608
        }
    return actual


def _expected(user: str, schema: SchemaFacts, ownership: Ownership) -> dict[str, dict[str, Any]]:
    expected: dict[str, dict[str, Any]] = {}
    for table, columns in schema.columns.items():
        limit = ownership.readable.get(table)
        if table not in ownership.readable:
            select: set[str] = set()
        else:
            select = set(columns) if limit is None else set(limit)
        expected[table] = {
            "select": select,
            "update": set(ownership.updates[user].get(table, frozenset())),
            "insert": table in ownership.inserts[user],
            "delete": False,
        }
    return expected


def _show_grants(port_db: PortDatabase, grantee: str) -> list[str]:
    root = port_db.root()
    try:
        with root.cursor() as cursor:
            cursor.execute(f"SHOW GRANTS FOR {grantee}")
            return [row[0] for row in cursor.fetchall()]
    finally:
        root.close()


@pytest.mark.parametrize("part", PARTS, ids=str)
def test_each_role_holds_exactly_the_published_matrix(
    part: WorkerPart, port_db: PortDatabase, ownership: Ownership
) -> None:
    """Exact for every privilege, including those the probes below can't see (TRIGGER, FILE)."""
    user, role = ACCOUNTS[part]
    actual = parse_role_grants(_show_grants(port_db, f"'{role}'"), port_db.name)
    assert actual == expected_role_grants(ownership, user)


@pytest.mark.parametrize("part", PARTS, ids=str)
def test_each_account_holds_only_its_role(part: WorkerPart, port_db: PortDatabase) -> None:
    user, role = ACCOUNTS[part]
    assert _show_grants(port_db, f"'{user}'") == [
        f"GRANT USAGE ON *.* TO `{user}`@`%`",
        f"GRANT `{role}`@`%` TO `{user}`@`%`",
    ]


def test_the_schema_has_the_tables_the_matrix_expects(
    schema: SchemaFacts, ownership: Ownership
) -> None:
    assert len(schema.columns) == 100
    hidden_by_grant = set(schema.columns) - set(ownership.readable)
    assert ownership.hidden <= hidden_by_grant
    assert len(hidden_by_grant) == len(ownership.hidden) + LARAVEL_TABLES
    assert set(ownership.readable) <= set(schema.columns)


@pytest.mark.parametrize("account", PARTS, indirect=True, ids=str)
def test_each_worker_logs_in_as_itself_with_only_its_role(
    account: WorkerConnection, request: pytest.FixtureRequest
) -> None:
    part = request.node.callspec.params["account"]
    user, role = ACCOUNTS[part]
    cursor = account.cursor()
    cursor.execute("SELECT CURRENT_USER(), CURRENT_ROLE()")
    current_user, current_role = cursor.fetchone()
    cursor.close()
    assert current_user == f"{user}@%"
    assert current_role == f"`{role}`@`%`"


def _login_without_tls(port_db: PortDatabase) -> None:
    conn = pymysql.connect(
        host=port_db.service.mysql_host,
        port=port_db.service.mysql_port,
        user="w_part1",
        password=port_db.passwords[WorkerPart.PART1],
        database=port_db.name,
        ssl_disabled=True,
    )
    conn.close()


def _forget_cached_logins(port_db: PortDatabase) -> None:
    root = port_db.root()
    try:
        with root.cursor() as cursor:
            cursor.execute("FLUSH PRIVILEGES")
    finally:
        root.close()


@pytest.mark.parametrize("account", [WorkerPart.PART1], indirect=True, ids=str)
def test_a_worker_session_uses_tls_when_the_server_offers_it(account: WorkerConnection) -> None:
    # PyMySQL asks for TLS by default, without checking the certificate (AI-090 decides on that).
    cursor = account.cursor()
    cursor.execute("SHOW SESSION STATUS LIKE 'Ssl_cipher'")
    assert cursor.fetchone()[1] != ""
    cursor.close()


@pytest.mark.xfail(
    strict=True,
    raises=AttributeError,
    reason="PyMySQL 1.2.3: caching_sha2_password_auth drops the packet after the RSA exchange",
)
def test_a_first_login_without_tls_uses_cryptography(port_db: PortDatabase) -> None:
    """Strict: once a fixed PyMySQL makes this pass, the test fails until this mark is removed."""
    _forget_cached_logins(port_db)
    _login_without_tls(port_db)


def test_a_login_without_tls_works_once_the_server_has_cached_it(port_db: PortDatabase) -> None:
    _forget_cached_logins(port_db)
    with contextlib.suppress(AttributeError):
        _login_without_tls(port_db)
    _login_without_tls(port_db)


def test_a_wrong_password_is_refused(port_db: PortDatabase) -> None:
    env = port_db.worker_env(WorkerPart.PART1) | {"AI_DB_PASSWORD_PART1": "wrong"}
    with pytest.raises(Exception, match="Access denied"):
        connect_worker(load_env_settings(env, WorkerPart.PART1))


@pytest.mark.parametrize("account", PARTS, indirect=True, ids=str)
def test_the_server_allows_exactly_the_published_matrix(
    account: WorkerConnection,
    request: pytest.FixtureRequest,
    schema: SchemaFacts,
    ownership: Ownership,
) -> None:
    user = ACCOUNTS[request.node.callspec.params["account"]][0]
    actual = _rights(account, schema)
    expected = _expected(user, schema, ownership)
    differences = {
        (table, right): (actual[table][right], expected[table][right])
        for table in schema.columns
        for right in ("select", "update", "insert", "delete")
        if actual[table][right] != expected[table][right]
    }
    assert differences == {}


@pytest.mark.parametrize("account", PARTS, indirect=True, ids=str)
@pytest.mark.parametrize(
    "table",
    ["audit_logs", "notification_logs", "recommendation_reviews", "user_devices", "migrations"],
)
def test_hidden_tables_refuse_every_operation(table: str, account: WorkerConnection) -> None:
    for sql in (
        f"SELECT * FROM `{table}` LIMIT 0",  # noqa: S608
        f"DELETE FROM `{table}` WHERE 1 = 0",  # noqa: S608
        f"UPDATE `{table}` SET id = NULL WHERE 1 = 0",  # noqa: S608
        f"INSERT INTO `{table}` () VALUES ()",  # noqa: S608
    ):
        assert not _allowed(account, sql), sql


@pytest.mark.parametrize("account", PARTS, indirect=True, ids=str)
@pytest.mark.parametrize(
    "sql",
    [
        "SELECT email FROM users LIMIT 0",
        "SELECT * FROM users LIMIT 0",
        "SELECT * FROM license_states LIMIT 0",
    ],
)
def test_hidden_columns_are_refused(sql: str, account: WorkerConnection) -> None:
    assert not _allowed(account, sql)


@pytest.mark.parametrize("account", PARTS, indirect=True, ids=str)
@pytest.mark.parametrize(
    "sql",
    [
        "CREATE TABLE ai013_probe (id INT)",
        "CREATE TEMPORARY TABLE ai013_probe (id INT)",
        "DROP TABLE vessels",
        "ALTER TABLE vessels ADD COLUMN ai013_probe INT",
        "TRUNCATE TABLE vessels",
        "CREATE INDEX ai013_probe ON vessels (name)",
        "DROP INDEX imo_number ON vessels",
        "RENAME TABLE vessels TO ai013_probe",
        "CREATE VIEW ai013_probe AS SELECT 1",
        "CREATE PROCEDURE ai013_probe() SELECT 1",
        "LOCK TABLES vessels WRITE",
        "CREATE DATABASE ai013_probe",
        "CREATE USER 'ai013_probe'@'%'",
        "GRANT SELECT ON vessels TO 'w_validate'@'%'",
        "FLUSH PRIVILEGES",
        "SET GLOBAL max_connections = 100",
    ],
)
def test_ddl_and_administration_are_refused(sql: str, account: WorkerConnection) -> None:
    assert not _allowed(account, sql, _ADMIN_REFUSED)
