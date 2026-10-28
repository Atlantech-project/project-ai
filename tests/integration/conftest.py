"""Fixtures for the MySQL and Redis service containers.

Without services configured, integration tests skip locally but fail in CI
(ATLANTECH_REQUIRE_SERVICES=1), so a missing service can never pass silently.
"""

import os
import time
from collections.abc import Callable, Iterator

import pymysql
import pytest
import redis

from tests.support.services import ServiceSettings, load_service_settings, services_required

_CONNECT_ATTEMPTS = 30
_CONNECT_DELAY_S = 1.0
# Only "server not up yet" errors are retried (2003 can't connect, 2013 lost connection);
# access denied or an unknown database fails at once with the real cause.
_TRANSIENT_MYSQL_ERRORS = {2003, 2013}


def _retry[T](connect: Callable[[], T]) -> T:
    last_error: Exception | None = None
    for _ in range(_CONNECT_ATTEMPTS):
        try:
            return connect()
        except pymysql.err.OperationalError as error:
            if error.args[0] not in _TRANSIENT_MYSQL_ERRORS:
                raise
            last_error = error
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as error:
            last_error = error
        time.sleep(_CONNECT_DELAY_S)
    raise RuntimeError(f"Service not reachable after {_CONNECT_ATTEMPTS} attempts") from last_error


@pytest.fixture(scope="session")
def service_settings() -> ServiceSettings:
    settings = load_service_settings(os.environ)
    if settings is None:
        message = "MySQL/Redis not configured (set MYSQL_* and REDIS_URL)"
        if services_required(os.environ):
            pytest.fail(message, pytrace=False)
        pytest.skip(message)
    return settings


@pytest.fixture
def mysql_conn(service_settings: ServiceSettings) -> Iterator[pymysql.connections.Connection]:
    # Same session rule as the workers: every connection runs in UTC (CT-17 §2).
    conn = _retry(
        lambda: pymysql.connect(
            host=service_settings.mysql_host,
            port=service_settings.mysql_port,
            user=service_settings.mysql_user,
            password=service_settings.mysql_password,
            database=service_settings.mysql_database,
            charset="utf8mb4",
            init_command="SET time_zone = '+00:00'",
        )
    )
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def redis_client(service_settings: ServiceSettings) -> Iterator[redis.Redis]:
    client: redis.Redis = redis.Redis.from_url(service_settings.redis_url, decode_responses=True)
    _retry(client.ping)
    try:
        yield client
    finally:
        client.close()
