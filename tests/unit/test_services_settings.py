import pytest

from tests.support.services import ServiceSettings, load_service_settings, services_required

COMPLETE_ENV = {
    "MYSQL_HOST": "127.0.0.1",
    "MYSQL_PORT": "3306",
    "MYSQL_USER": "root",
    "MYSQL_PASSWORD": "ci_only",
    "MYSQL_DATABASE": "ai_ci",
    "REDIS_URL": "redis://127.0.0.1:6379/0",
}


def test_complete_env_parses() -> None:
    assert load_service_settings(COMPLETE_ENV) == ServiceSettings(
        mysql_host="127.0.0.1",
        mysql_port=3306,
        mysql_user="root",
        mysql_password="ci_only",
        mysql_database="ai_ci",
        redis_url="redis://127.0.0.1:6379/0",
    )


def test_absent_env_returns_none() -> None:
    assert load_service_settings({}) is None


def test_partial_env_raises_naming_key() -> None:
    env = {k: v for k, v in COMPLETE_ENV.items() if k != "MYSQL_PASSWORD"}
    with pytest.raises(ValueError, match="MYSQL_PASSWORD"):
        load_service_settings(env)


def test_partial_env_without_mysql_host_raises() -> None:
    with pytest.raises(ValueError, match="MYSQL_HOST"):
        load_service_settings({"REDIS_URL": COMPLETE_ENV["REDIS_URL"]})


def test_bad_port_raises() -> None:
    with pytest.raises(ValueError, match="MYSQL_PORT"):
        load_service_settings({**COMPLETE_ENV, "MYSQL_PORT": "abc"})


@pytest.mark.parametrize(
    ("value", "expected"),
    [("1", True), ("0", False), ("true", False), ("", False), (None, False)],
)
def test_services_required_flag(value: str | None, expected: bool) -> None:
    env = {} if value is None else {"ATLANTECH_REQUIRE_SERVICES": value}
    assert services_required(env) is expected
