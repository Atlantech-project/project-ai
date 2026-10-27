"""Connection settings for the CI MySQL and Redis service containers, read from the environment."""

from collections.abc import Mapping
from dataclasses import dataclass

_REQUIRED_KEYS = (
    "MYSQL_HOST",
    "MYSQL_PORT",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MYSQL_DATABASE",
    "REDIS_URL",
)


@dataclass(frozen=True)
class ServiceSettings:
    mysql_host: str
    mysql_port: int
    mysql_user: str
    mysql_password: str
    mysql_database: str
    redis_url: str


def load_service_settings(env: Mapping[str, str]) -> ServiceSettings | None:
    """Return the settings, or None when no services are configured (none of the keys set).

    A partial configuration is a mistake, not "no services", so it raises.
    """
    missing = [key for key in _REQUIRED_KEYS if key not in env]
    if len(missing) == len(_REQUIRED_KEYS):
        return None
    if missing:
        raise ValueError(f"Missing service settings: {', '.join(missing)}")
    try:
        port = int(env["MYSQL_PORT"])
    except ValueError:
        raise ValueError(f"MYSQL_PORT must be an integer, got {env['MYSQL_PORT']!r}") from None
    return ServiceSettings(
        mysql_host=env["MYSQL_HOST"],
        mysql_port=port,
        mysql_user=env["MYSQL_USER"],
        mysql_password=env["MYSQL_PASSWORD"],
        mysql_database=env["MYSQL_DATABASE"],
        redis_url=env["REDIS_URL"],
    )


def services_required(env: Mapping[str, str]) -> bool:
    """True in CI, where a missing service must fail the run instead of skipping."""
    return env.get("ATLANTECH_REQUIRE_SERVICES") == "1"
