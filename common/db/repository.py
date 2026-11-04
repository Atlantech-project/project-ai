"""Column-checked writes for one worker, plus the rules MySQL grants can't enforce (CT-15, DEC-08).

The repository never commits. Under the runtime, the writes commit together with the guarded final
update; elsewhere, wrap them in `common.db.connection.transaction`.
"""

from collections.abc import Mapping, Sequence
from typing import Any, Final

import sqlalchemy as sa

from common.config import WorkerPart
from common.db.connection import core_of
from common.db.rights import BACKEND_ONLY_COLUMNS, WRITE_RIGHTS
from common.db.tables import (
    BAPLIE_FILES,
    CONTAINERS,
    TERMINAL_RECOMMENDATIONS,
    VESSELS,
    YARD_RUNS,
    metadata,
)
from common.runtime.runs import Connection

_WORKER_PULL_TYPES: Final = frozenset({"SCHEDULED", "ON_DEMAND"})
# CT-15 writes the first as GENERATED; the ENUM and CT-11 call it YARD_REC_GENERATED.
_WORKER_LIFECYCLE_STATUSES: Final = frozenset({"YARD_REC_GENERATED", "GENERATION_FAILED"})
_AWAITING_GENERATION: Final = "YARD_REC_REQUESTED"
# The only status a worker creates these rows in. CT-15 names PROPOSED. PENDING_REVIEW is Proposed
# (AI-013): CT-15 names no status, but DEC-06, CT-10 and CT-20 all treat it as the new version's.
_INITIAL_STATUS: Final = {
    "entry_window_proposals": "PROPOSED",
    "recommendations": "PENDING_REVIEW",
}


class WriteRefused(ValueError):
    """A write this worker may not make. Nothing was sent to the database."""


class WorkerRepository:
    """The tables one worker writes, scoped to its own run where it has one."""

    def __init__(self, connection: Connection, part: WorkerPart, run_id: int | None = None) -> None:
        self._core = core_of(connection)
        self._part = part
        self._rights = WRITE_RIGHTS[part]
        self._run_id = run_id

    def insert(self, table_name: str, row: Mapping[str, object]) -> int:
        """Insert one row; returns its AUTO_INCREMENT id, or 0 if the table has none."""
        table = self._insertable(table_name, [row])
        return int(self._core.execute(table.insert().values(**row)).lastrowid)

    def insert_many(self, table_name: str, rows: Sequence[Mapping[str, object]]) -> None:
        """Insert rows that all have the same columns."""
        if rows:
            table = self._insertable(table_name, rows)
            self._core.execute(table.insert(), [dict(row) for row in rows])

    def insert_new_containers(self, rows: Sequence[Mapping[str, object]]) -> dict[str, int]:
        """Insert only unknown container numbers (DEC-08); returns the id of every number given.

        A number another session adds meanwhile raises a duplicate-key error, and the job retries.
        """
        self._check_insert(CONTAINERS.name, rows)
        if any("container_number" not in row for row in rows):
            raise WriteRefused("every container needs a container_number")
        by_number = {str(row["container_number"]): row for row in rows}
        if len(by_number) != len(rows):
            raise WriteRefused("a container number appears twice")
        known = self._container_ids(by_number)
        fresh = [dict(row) for number, row in by_number.items() if number not in known]
        if not fresh:
            return known
        self._core.execute(CONTAINERS.insert(), fresh)
        return self._container_ids(by_number)

    def update_own_run(self, values: Mapping[str, object]) -> bool:
        """Update this worker's own run while it is RUNNING. False: it no longer is (CT-15)."""
        run_table = self._rights.run_table
        if run_table is None or self._run_id is None:
            raise WriteRefused(f"{self._part} has no run to update here")
        self._check_update(run_table, values)
        table = metadata.tables[run_table]
        statement = (
            table.update()
            .where(table.c.id == self._run_id, table.c.status == "RUNNING")
            .values(**values)
        )
        return self._updated_one(statement)

    def update_terminal_recommendation(
        self, recommendation_id: int, values: Mapping[str, object]
    ) -> bool:
        """Record a generation result on a row still awaiting one (CT-11, CT-15).

        False: the Backend reset or replaced the row, so roll back and send nothing.
        """
        table = TERMINAL_RECOMMENDATIONS
        self._check_update(table.name, values)
        if (
            "lifecycle_status" in values
            and values["lifecycle_status"] not in _WORKER_LIFECYCLE_STATUSES
        ):
            status = values["lifecycle_status"]
            raise WriteRefused(f"lifecycle_status {status} isn't a worker's to set (CT-15)")
        statement = (
            table.update()
            .where(
                table.c.id == recommendation_id, table.c.lifecycle_status == _AWAITING_GENERATION
            )
            .values(**values)
        )
        return self._updated_one(statement)

    def lock_yard_result(self, recommendation_id: int) -> bool:
        """Take the CT-17 §8 locks, in its order, on this run's own recommendation.

        False: roll back and send nothing.
        """
        if self._rights.run_table != YARD_RUNS.name or self._run_id is None:
            raise WriteRefused(f"{self._part} has no yard run to lock here")
        recommendation = self._core.execute(
            sa.select(TERMINAL_RECOMMENDATIONS.c.id)
            .where(TERMINAL_RECOMMENDATIONS.c.id == recommendation_id)
            .with_for_update()
        ).first()
        run = self._core.execute(
            sa.select(YARD_RUNS.c.id)
            .where(
                YARD_RUNS.c.id == self._run_id,
                YARD_RUNS.c.status == "RUNNING",
                YARD_RUNS.c.terminal_recommendation_id == recommendation_id,
            )
            .with_for_update()
        ).first()
        return recommendation is not None and run is not None

    def update_baplie_file(self, file_id: int, values: Mapping[str, object]) -> bool:
        """Set the parse result on a file. False: there is no such file."""
        self._check_update(BAPLIE_FILES.name, values)
        return self._updated_one(
            BAPLIE_FILES.update().where(BAPLIE_FILES.c.id == file_id).values(**values)
        )

    def fill_vessel_nulls(self, vessel_id: int, values: Mapping[str, object]) -> bool:
        """Fill `call_sign` or `flag_state` only where NULL (DEC-08). False: no such vessel."""
        self._check_update(VESSELS.name, values)
        filled: dict[str, Any] = {
            name: sa.func.coalesce(VESSELS.c[name], value) for name, value in values.items()
        }
        return self._updated_one(VESSELS.update().where(VESSELS.c.id == vessel_id).values(**filled))

    def _updated_one(self, statement: sa.Update) -> bool:
        # SQLAlchemy's PyMySQL dialect counts matched rows, so an unchanged row still counts.
        return self._core.execute(statement).rowcount == 1

    def _container_ids(self, numbers: Mapping[str, object]) -> dict[str, int]:
        found = self._core.execute(
            sa.select(CONTAINERS.c.container_number, CONTAINERS.c.id).where(
                CONTAINERS.c.container_number.in_(list(numbers))
            )
        )
        return {row.container_number: row.id for row in found}

    def _insertable(self, table_name: str, rows: Sequence[Mapping[str, object]]) -> sa.Table:
        if table_name == CONTAINERS.name:
            raise WriteRefused("use insert_new_containers for containers")
        self._check_insert(table_name, rows)
        if table_name == "forecast_runs":
            for row in rows:
                if row.get("pull_type") not in _WORKER_PULL_TYPES:
                    raise WriteRefused(f"pull_type {row.get('pull_type')} is the Backend's (CT-15)")
        initial = _INITIAL_STATUS.get(table_name)
        if initial is not None:
            for row in rows:
                if row.get("status", initial) != initial:
                    raise WriteRefused(f"{table_name} starts as {initial}, not {row['status']}")
        return metadata.tables[table_name]

    def _check_insert(self, table_name: str, rows: Sequence[Mapping[str, object]]) -> None:
        if table_name not in self._rights.insert:
            raise WriteRefused(f"{self._part} may not insert into {table_name}")
        table = metadata.tables[table_name]
        refused = BACKEND_ONLY_COLUMNS.get(table_name, frozenset())
        for row in rows:
            # SQLAlchemy builds the statement from the first row and drops other rows' extra keys.
            if row.keys() != rows[0].keys():
                raise WriteRefused(f"rows for {table_name} must all have the same columns")
            for name in row:
                if name not in table.c:
                    raise WriteRefused(f"{table_name} has no column {name}")
                if table.c[name].info.get("generated") or name in refused:
                    raise WriteRefused(f"{table_name}.{name} isn't a worker's to write")

    def _check_update(self, table_name: str, values: Mapping[str, object]) -> None:
        allowed = self._rights.update.get(table_name)
        if allowed is None:
            raise WriteRefused(f"{self._part} may not update {table_name}")
        if not values:
            raise WriteRefused(f"nothing to update on {table_name}")
        for name in values:
            if name not in allowed:
                raise WriteRefused(f"{self._part} may not update {table_name}.{name}")
