"""Which `safety_constraints` rows apply, and which one is the strictest (AI-044).

A row applies when it is active at the moment, on the half-open UTC interval `[active_from,
active_to)`, and each scope column is NULL or matches. With no berth (the normal Part 1 case),
every berth-scoped row of the terminal applies, so the result is conservative; AI-051 calls the
same function with a candidate berth. Rows scoped to an equipment category never apply here:
AI-051 applies them. IMDG codes are classes ("2") or divisions ("2.1"): a row for a class covers
cargo of any of its divisions, and a row for a division covers only that division (conservative,
so a class limit is never skipped for division cargo). Among the applicable rows, the lowest value
wins for `MAX_ALLOWED` and the highest for `MIN_REQUIRED` (Architecture §7.5: "the strictest value
wins"); a tie goes to the lowest row id, so the result is deterministic.
"""

from collections.abc import Iterable
from datetime import datetime, timedelta

from part1.feasibility.model import AssessmentScope, Comparator, ConstraintType, SafetyConstraint


def require_utc(moment: datetime, what: str) -> None:
    """Raise unless `moment` is timezone-aware UTC."""
    if moment.tzinfo is None or moment.utcoffset() != timedelta(0):
        raise ValueError(f"{what} must be a timezone-aware UTC datetime, got {moment!r}")


def applies(row: SafetyConstraint, scope: AssessmentScope, at: datetime) -> bool:
    """Whether `row` applies to `scope` at the UTC moment `at`."""
    require_utc(at, "the moment")
    if row.equipment_category_id is not None:
        return False
    if at < row.active_from or (row.active_to is not None and at >= row.active_to):
        return False
    if row.terminal_id is not None and row.terminal_id != scope.terminal_id:
        return False
    if row.berth_id is not None and scope.berth_id is not None and row.berth_id != scope.berth_id:
        return False
    if row.vessel_type_id is not None and row.vessel_type_id != scope.vessel_type_id:
        return False
    return row.imdg_class is None or any(
        _imdg_covers(row.imdg_class, cargo) for cargo in scope.imdg_classes
    )


def _imdg_covers(row_class: str, cargo: str) -> bool:
    """A class row ("2") covers its divisions ("2.1"); a division row covers only itself."""
    return cargo == row_class or cargo.startswith(row_class + ".")


def resolve_limit(
    rows: Iterable[SafetyConstraint],
    constraint_type: ConstraintType,
    scope: AssessmentScope,
    at: datetime,
) -> SafetyConstraint | None:
    """The strictest row of `constraint_type` that applies to `scope` at `at`, or None."""
    candidates = [
        row
        for row in rows
        if row.constraint_type_id == constraint_type.id and applies(row, scope, at)
    ]
    if not candidates:
        return None
    if constraint_type.comparator is Comparator.MAX_ALLOWED:
        return min(candidates, key=lambda row: (row.value, row.id))
    return min(candidates, key=lambda row: (-row.value, row.id))
