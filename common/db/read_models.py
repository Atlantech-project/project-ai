"""Typed reads of what workers use today: requests with vessels, tugboats, run rows.

Every read comes from the primary, the only host a worker knows (DEC-08). A row holding an ENUM
value this code doesn't know logs a warning and is skipped; it never crashes the worker (CT-17 §6).
Callers own commit or rollback.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa

from common.config import WorkerPart
from common.db.connection import core_of
from common.db.rights import WRITE_RIGHTS
from common.db.tables import BERTHING_REQUESTS, TUGBOATS, VESSEL_TYPES, VESSELS, KnownEnum, metadata
from common.runtime.logs import log_event
from common.runtime.runs import Connection


@dataclass(frozen=True)
class RequestWithVessel:
    request_id: int
    status: str
    requested_terminal_id: int
    requested_eta: datetime
    arrival_draft: Decimal
    block_coefficient: Decimal
    gross_tonnage: int
    deadweight_tonnes: int
    vessel_id: int
    vessel_name: str
    vessel_type_code: str
    loa: Decimal
    beam: Decimal
    max_draft: Decimal


@dataclass(frozen=True)
class Tugboat:
    id: int
    name: str
    tug_power: Decimal
    tug_power_unit: str
    status: str


@dataclass(frozen=True)
class RunRow:
    id: int
    status: str
    outcome: str | None
    retry_count: int | None
    started_at: datetime | None
    finished_at: datetime | None


def _is_known(row: sa.RowMapping, columns: Sequence[sa.Column[Any]]) -> bool:
    for column in columns:
        value = row[column]
        if (
            isinstance(column.type, KnownEnum)
            and value is not None
            and value not in column.type.values
        ):
            log_event(
                logging.WARNING,
                "unknown_enum_value_skipped",
                {"table": column.table.name, "column": column.key, "value": value},
            )
            return False
    return True


def read_request_with_vessel(connection: Connection, request_id: int) -> RequestWithVessel | None:
    """One berthing request with its vessel. None: no such request, or an unknown ENUM value."""
    columns = (
        BERTHING_REQUESTS.c.id,
        BERTHING_REQUESTS.c.status,
        BERTHING_REQUESTS.c.requested_terminal_id,
        BERTHING_REQUESTS.c.requested_eta,
        BERTHING_REQUESTS.c.arrival_draft,
        BERTHING_REQUESTS.c.block_coefficient,
        BERTHING_REQUESTS.c.gross_tonnage,
        BERTHING_REQUESTS.c.deadweight_tonnes,
        VESSELS.c.id,
        VESSELS.c.name,
        VESSEL_TYPES.c.code,
        VESSELS.c.loa,
        VESSELS.c.beam,
        VESSELS.c.max_draft,
    )
    statement = (
        sa.select(*columns)
        .select_from(
            BERTHING_REQUESTS.join(VESSELS, BERTHING_REQUESTS.c.vessel_id == VESSELS.c.id).join(
                VESSEL_TYPES, VESSELS.c.vessel_type_id == VESSEL_TYPES.c.id
            )
        )
        .where(BERTHING_REQUESTS.c.id == request_id)
    )
    row = core_of(connection).execute(statement).mappings().first()
    if row is None or not _is_known(row, columns):
        return None
    return RequestWithVessel(*(row[column] for column in columns))


def read_tugboats(connection: Connection) -> list[Tugboat]:
    """The whole fleet, in id order. Availability is the caller's to judge (DEC-32)."""
    columns = (
        TUGBOATS.c.id,
        TUGBOATS.c.name,
        TUGBOATS.c.tug_power,
        TUGBOATS.c.tug_power_unit,
        TUGBOATS.c.status,
    )
    rows = core_of(connection).execute(sa.select(*columns).order_by(TUGBOATS.c.id)).mappings()
    return [
        Tugboat(*(row[column] for column in columns)) for row in rows if _is_known(row, columns)
    ]


def read_run(connection: Connection, part: WorkerPart, run_id: int) -> RunRow | None:
    """This worker's own run. None: no such run, or an unknown ENUM value."""
    run_table = WRITE_RIGHTS[part].run_table
    if run_table is None:
        raise ValueError(f"{part} has no runs")
    table = metadata.tables[run_table]
    # `solver_runs` has neither `outcome` nor `retry_count`.
    optional = [table.c[name] for name in ("outcome", "retry_count") if name in table.c]
    columns = [table.c.id, table.c.status, table.c.started_at, table.c.finished_at, *optional]
    statement = sa.select(*columns).where(table.c.id == run_id)
    row = core_of(connection).execute(statement).mappings().first()
    if row is None or not _is_known(row, columns):
        return None
    return RunRow(
        id=row[table.c.id],
        status=row[table.c.status],
        outcome=row[table.c.outcome] if "outcome" in table.c else None,
        retry_count=row[table.c.retry_count] if "retry_count" in table.c else None,
        started_at=row[table.c.started_at],
        finished_at=row[table.c.finished_at],
    )
