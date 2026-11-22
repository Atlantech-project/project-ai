"""Trusted-data selection (AI-074): the only way Part 3 reads field events.

Architecture I-13 and UML rule 8: Part 3 (C1 to C4) uses trusted records only, and a record is
trusted when `clock_skew_suspect = 0`. Every read of `actual_status_updates` in Part 3 goes
through `trusted_status_updates`, which always carries that condition; there is no parameter to
include suspect rows, and nothing (a human review included) makes a suspect row trusted.
In-memory datasets built elsewhere are filtered with `filter_trusted` (AI-025's rule).
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import sqlalchemy as sa

from common.db.connection import core_of
from common.db.tables import ACTUAL_STATUS_UPDATES
from common.quality import TrustedRows, trusted_rows
from common.runtime.runs import Connection

_T = ACTUAL_STATUS_UPDATES


@dataclass(frozen=True)
class StatusUpdate:
    """One trusted `actual_status_updates` row (the fields evaluation and training use)."""

    id: int
    plan_component_id: int
    component_type: str
    status: str
    reported_at: datetime
    received_at: datetime


def trusted_select(*columns: sa.ColumnElement[Any]) -> sa.Select[Any]:
    """`SELECT <columns> FROM actual_status_updates WHERE clock_skew_suspect = 0`."""
    return sa.select(*columns).where(_T.c.clock_skew_suspect == 0)


def trusted_status_updates(
    connection: Connection,
    *,
    reported_from: datetime,
    reported_to: datetime,
    plan_component_ids: Sequence[int] | None = None,
) -> list[StatusUpdate]:
    """Trusted field events reported in `[reported_from, reported_to)`, by time then id."""
    for name, value in (("reported_from", reported_from), ("reported_to", reported_to)):
        if value.utcoffset() is None:
            raise ValueError(f"{name} must be timezone-aware: {value.isoformat()}")
    if reported_to <= reported_from:
        raise ValueError(f"the period must end after it starts: {reported_from} to {reported_to}")
    statement = trusted_select(
        _T.c.id,
        _T.c.plan_component_id,
        _T.c.component_type,
        _T.c.status,
        _T.c.reported_at,
        _T.c.received_at,
    ).where(_T.c.reported_at >= reported_from, _T.c.reported_at < reported_to)
    if plan_component_ids is not None:
        if not plan_component_ids:
            return []
        statement = statement.where(_T.c.plan_component_id.in_(list(plan_component_ids)))
    statement = statement.order_by(_T.c.reported_at, _T.c.id)
    rows = core_of(connection).execute(statement).mappings()
    return [
        StatusUpdate(
            id=row["id"],
            plan_component_id=row["plan_component_id"],
            component_type=row["component_type"],
            status=row["status"],
            reported_at=row["reported_at"],
            received_at=row["received_at"],
        )
        for row in rows
    ]


def filter_trusted[R](rows: Iterable[R]) -> TrustedRows[R]:
    """Split dataset rows (mappings with `clock_skew_suspect`) into trusted and excluded."""
    return trusted_rows(rows)
