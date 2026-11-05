"""Worker database connections and the transaction helper (DEC-08, CT-17 §2).

Each worker logs in with its own account from `EnvSettings`, in manual commit, in UTC, against the
primary. `connect_worker` is the `connect_with` that workers give `run_worker`.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final, cast

import sqlalchemy as sa

from common.config import EnvSettings
from common.runtime.runs import Connection, Cursor

_TIME_ZONE_COMMAND: Final = "SET time_zone = '+00:00'"
# The runtime holds one connection at a time; the overflow only covers a replacement in progress.
_POOL_SIZE: Final = 1
_POOL_OVERFLOW: Final = 1
_engines: Final[dict[EnvSettings, sa.Engine]] = {}


class WorkerConnection:
    """One database session, for the runtime (DB-API) and the repositories (SQLAlchemy Core).

    Both use the same underlying connection and transaction. The runtime's raw cursors don't start
    SQLAlchemy's transaction, so `cursor` does, or `commit` would have nothing to commit.
    """

    def __init__(self, core: sa.Connection) -> None:
        self.core = core

    def cursor(self) -> Cursor:
        if not self.core.in_transaction():
            self.core.begin()
        return cast("Cursor", self.core.connection.cursor())

    def commit(self) -> None:
        if self.core.in_transaction():
            self.core.commit()
        else:
            # A raw cursor kept across an earlier commit writes outside SQLAlchemy's transaction.
            self.core.connection.commit()

    def rollback(self) -> None:
        # Not `in_transaction`: after a failed commit that is False, but SQLAlchemy still holds the
        # transaction and refuses new work until it's rolled back.
        if self.core.get_transaction() is not None:
            self.core.rollback()
        else:
            self.core.connection.rollback()

    def close(self) -> None:
        self.core.close()


def core_of(connection: Connection) -> sa.Connection:
    """The SQLAlchemy side of a connection made by `connect_worker`."""
    if not isinstance(connection, WorkerConnection):
        raise TypeError(f"needs a connection from connect_worker, got {type(connection).__name__}")
    return connection.core


def _engine(settings: EnvSettings) -> sa.Engine:
    engine = _engines.get(settings)
    if engine is None:
        engine = _engines[settings] = _create_engine(settings)
    return engine


def _create_engine(settings: EnvSettings) -> sa.Engine:
    url = sa.URL.create(
        "mysql+pymysql",
        username=settings.db_user,
        password=settings.db_password,
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        query={"charset": "utf8mb4"},
    )
    return sa.create_engine(
        url,
        pool_size=_POOL_SIZE,
        max_overflow=_POOL_OVERFLOW,
        # The runtime asks for a connection before each BLPOP; a dead one is replaced here.
        pool_pre_ping=True,
        connect_args={"init_command": _TIME_ZONE_COMMAND},
    )


def connect_worker(settings: EnvSettings) -> WorkerConnection:
    """Open a session under this worker's own account. The caller commits and closes it."""
    return WorkerConnection(_engine(settings).connect())


def dispose_engines() -> None:
    """Close every pooled connection, for a clean shutdown. Each session's state ends with it."""
    for engine in _engines.values():
        engine.dispose()
    _engines.clear()


@contextmanager
def transaction(connection: Connection) -> Iterator[None]:
    """Commit on success, roll back on any error: one result set, one transaction.

    For work outside the runtime, such as the schedulers. The runtime's handlers must not use it,
    because the runtime commits their writes together with the guarded final update.
    """
    try:
        yield
    except BaseException:
        connection.rollback()
        raise
    connection.commit()
