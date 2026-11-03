"""Proves the AI-012 refresh rule and the AI_* environment mapping against real MySQL."""

import os
from collections.abc import Iterator

import pymysql
import pytest

from common.config import EnvSettings, WorkerPart, load_env_settings, read_port_settings
from tests.support.services import ServiceSettings, services_required

pytestmark = pytest.mark.integration

# CT-17 `port_settings`, without the foreign key to `users`, which doesn't exist here.
_CREATE_TABLE = """
CREATE TABLE port_settings (
  id bigint unsigned NOT NULL AUTO_INCREMENT,
  setting_key varchar(80) NOT NULL,
  setting_value varchar(255) NOT NULL,
  value_type enum('INT','DECIMAL','BOOL','STRING','JSON') NOT NULL,
  description varchar(255) DEFAULT NULL,
  updated_by bigint unsigned DEFAULT NULL,
  updated_at datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY setting_key (setting_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
"""


def _env_settings(part: WorkerPart) -> EnvSettings:
    if "AI_DB_HOST" not in os.environ:
        message = "AI_* variables not configured"
        if services_required(os.environ):
            pytest.fail(message, pytrace=False)
        pytest.skip(message)
    return load_env_settings(os.environ, part)


def _connect(settings: EnvSettings, *, autocommit: bool) -> pymysql.connections.Connection:
    return pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        charset="utf8mb4",
        autocommit=autocommit,
    )


def _set_value(conn: pymysql.connections.Connection, value: str) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE port_settings SET setting_value = %s WHERE setting_key = 'k'", (value,)
        )
    conn.commit()


@pytest.fixture
def writer(mysql_conn: pymysql.connections.Connection) -> Iterator[pymysql.connections.Connection]:
    with mysql_conn.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS port_settings")
        cursor.execute(_CREATE_TABLE)
        cursor.execute(
            "INSERT INTO port_settings (setting_key, setting_value, value_type) "
            "VALUES ('k', '5', 'INT')"
        )
    mysql_conn.commit()
    try:
        yield mysql_conn
    finally:
        with mysql_conn.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS port_settings")
        mysql_conn.commit()


@pytest.mark.parametrize("part", list(WorkerPart))
def test_ci_maps_every_part_to_the_service_container(
    part: WorkerPart, service_settings: ServiceSettings
) -> None:
    settings = _env_settings(part)
    assert settings.db_host == service_settings.mysql_host
    assert settings.db_port == service_settings.mysql_port
    assert settings.db_name == service_settings.mysql_database
    assert settings.db_user == service_settings.mysql_user
    assert settings.db_password == service_settings.mysql_password
    assert settings.redis_url == service_settings.redis_url


def test_changed_value_takes_effect_on_the_next_read(
    writer: pymysql.connections.Connection,
) -> None:
    worker = _connect(_env_settings(WorkerPart.PART2), autocommit=True)
    try:
        assert read_port_settings(worker).get_int("k") == 5
        _set_value(writer, "6")
        assert read_port_settings(worker).get_int("k") == 6
    finally:
        worker.close()


def test_non_autocommit_read_opens_a_snapshot_that_stays_stale_until_commit(
    writer: pymysql.connections.Connection,
) -> None:
    worker = _connect(_env_settings(WorkerPart.PART2), autocommit=False)
    try:
        assert read_port_settings(worker).get_int("k") == 5
        _set_value(writer, "6")
        assert read_port_settings(worker).get_int("k") == 5
        worker.commit()
        assert read_port_settings(worker).get_int("k") == 6
    finally:
        worker.close()
