import json
import logging
import os
import signal
import subprocess
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import pytest

from common.config import EnvSettings
from common.runtime.envelope import JobType
from common.runtime.logs import LOGGER, configure_logging
from common.runtime.worker import JobContext, JobResult, WorkerDefinition, run_worker

REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_DIR = REPO_ROOT / "docs" / "ref" / "ai-payloads"
ENV = {
    "AI_DB_HOST": "db.internal",
    "AI_DB_PORT": "3306",
    "AI_DB_NAME": "portsync",
    "AI_DB_USER_PART1": "w_part1",
    "AI_DB_PASSWORD_PART1": "not-a-real-password",
    "AI_REDIS_URL": "redis://redis.internal:6379/0",
    "AI_SCHEMA_DIR": str(SCHEMA_DIR),
}


class _Cursor:
    rowcount = 0

    def __init__(self, rows: Sequence[tuple[str, str, str]]) -> None:
        self._rows = rows

    def execute(self, query: str, args: object = None) -> int:
        return 0

    def fetchall(self) -> Sequence[Sequence[Any]]:
        return self._rows

    def fetchone(self) -> None:
        return None

    def close(self) -> None:
        pass


class _Connection:
    def __init__(self, rows: Sequence[tuple[str, str, str]]) -> None:
        self._rows = rows

    def cursor(self) -> _Cursor:
        return _Cursor(self._rows)

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass


class _Redis:
    def ping(self) -> bool:
        return True

    def blpop(self, keys: Any, timeout: Any = 0) -> None:
        signal.raise_signal(signal.SIGTERM)

    def rpush(self, name: Any, *values: Any) -> None:
        raise AssertionError("nothing should be sent")


def _handler(_context: JobContext) -> JobResult:
    raise AssertionError("no job should run")


def _definition() -> WorkerDefinition:
    used = ("part1_max_retries", "drift_psi_threshold")
    return WorkerDefinition(JobType.PART1_RUN, _handler, used, "0.1.0")


def _connect(rows: Sequence[tuple[str, str, str]]) -> Any:
    def connect(_settings: EnvSettings) -> _Connection:
        return _Connection(rows)

    return connect


@pytest.fixture(autouse=True)
def _restore_process_state() -> Iterator[None]:
    handlers = {name: signal.getsignal(name) for name in (signal.SIGTERM, signal.SIGINT)}
    log_state = (list(LOGGER.handlers), LOGGER.propagate, LOGGER.level)
    yield
    for name, handler in handlers.items():
        signal.signal(name, handler)
    LOGGER.handlers[:], LOGGER.propagate, LOGGER.level = (
        log_state[0],
        log_state[1],
        log_state[2],
    )


GOOD_ROWS = [("part1_max_retries", "3", "INT")]


def test_clean_startup_runs_and_exits_zero_on_sigterm() -> None:
    code = run_worker(_definition(), _connect(GOOD_ROWS), lambda _url: _Redis(), ENV)
    assert code == 0


def test_a_pending_key_doesnt_stop_startup() -> None:
    assert "drift_psi_threshold" in _definition().used_setting_keys
    code = run_worker(_definition(), _connect(GOOD_ROWS), lambda _url: _Redis(), ENV)
    assert code == 0


def test_missing_environment_exits_non_zero(capsys: pytest.CaptureFixture[str]) -> None:
    env = {key: value for key, value in ENV.items() if key != "AI_DB_HOST"}
    code = run_worker(_definition(), _connect(GOOD_ROWS), lambda _url: _Redis(), env)
    assert code == 1
    line = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert line["event"] == "startup_failed"
    assert "AI_DB_HOST" in line["reason"]


def test_missing_approved_key_exits_non_zero(capsys: pytest.CaptureFixture[str]) -> None:
    code = run_worker(_definition(), _connect([]), lambda _url: _Redis(), ENV)
    assert code == 1
    assert "part1_max_retries" in capsys.readouterr().out


def test_missing_schema_dir_exits_non_zero(tmp_path: Path) -> None:
    env = {**ENV, "AI_SCHEMA_DIR": str(tmp_path / "nowhere")}
    assert run_worker(_definition(), _connect(GOOD_ROWS), lambda _url: _Redis(), env) == 1


def test_outside_a_checkout_the_schema_dir_is_required(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    env = {key: value for key, value in ENV.items() if key != "AI_SCHEMA_DIR"}
    code = run_worker(_definition(), _connect(GOOD_ROWS), lambda _url: _Redis(), env, tmp_path)
    assert code == 1
    assert "AI_SCHEMA_DIR" in capsys.readouterr().out


def test_the_checkout_default_is_logged_as_a_warning(capsys: pytest.CaptureFixture[str]) -> None:
    env = {key: value for key, value in ENV.items() if key != "AI_SCHEMA_DIR"}
    code = run_worker(_definition(), _connect(GOOD_ROWS), lambda _url: _Redis(), env, REPO_ROOT)
    assert code == 0
    assert "schema_dir_defaulted" in capsys.readouterr().out


def test_an_unreachable_database_exits_non_zero() -> None:
    def connect(_settings: EnvSettings) -> _Connection:
        raise OSError("can't connect")

    assert run_worker(_definition(), connect, lambda _url: _Redis(), ENV) == 1


def test_configuring_logs_twice_keeps_one_handler() -> None:
    configure_logging()
    configure_logging()
    assert len(LOGGER.handlers) == 1
    assert LOGGER.level == logging.INFO


def test_a_real_process_exits_non_zero_without_environment() -> None:
    env = {key: value for key, value in os.environ.items() if not key.startswith("AI_")}
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "tests.integration.fake_worker"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 1
    assert "AI_DB_HOST" in result.stdout
    assert "not-a-real-password" not in result.stdout
