"""Smoke tests proving the CI MySQL and Redis services match the documented conventions."""

import uuid

import pymysql
import pytest
import redis

pytestmark = pytest.mark.integration


def _scalar(conn: pymysql.connections.Connection, sql: str) -> object:
    with conn.cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()
    assert row is not None
    return row[0]


def test_mysql_version_is_8_4(mysql_conn: pymysql.connections.Connection) -> None:
    version = _scalar(mysql_conn, "SELECT VERSION()")
    assert isinstance(version, str)
    assert version.startswith("8.4")


def test_mysql_session_is_utc(mysql_conn: pymysql.connections.Connection) -> None:
    assert _scalar(mysql_conn, "SELECT @@session.time_zone") == "+00:00"


def test_mysql_charset_is_utf8mb4(mysql_conn: pymysql.connections.Connection) -> None:
    assert _scalar(mysql_conn, "SELECT @@character_set_database") == "utf8mb4"
    assert _scalar(mysql_conn, "SELECT @@collation_database") == "utf8mb4_0900_ai_ci"


def test_mysql_session_charset_is_utf8mb4(mysql_conn: pymysql.connections.Connection) -> None:
    # The session itself, not only the schema defaults, must follow CT-17 §2.
    for variable in ("character_set_client", "character_set_connection", "character_set_results"):
        assert _scalar(mysql_conn, f"SELECT @@session.{variable}") == "utf8mb4", variable
    assert _scalar(mysql_conn, "SELECT @@session.collation_connection") == "utf8mb4_0900_ai_ci"


def test_redis_fifo_on_unprefixed_key(redis_client: redis.Redis) -> None:
    # CT-08: the Backend RPUSHes to an unprefixed key and the worker BLPOPs it.
    key = f"ci:smoke:{uuid.uuid4()}"
    try:
        redis_client.rpush(key, "first", "second")
        assert redis_client.blpop([key], timeout=1) == (key, "first")
        assert redis_client.blpop([key], timeout=1) == (key, "second")
        assert redis_client.blpop([key], timeout=1) is None
    finally:
        redis_client.delete(key)
