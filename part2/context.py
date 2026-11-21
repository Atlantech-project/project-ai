"""B2's `FilterContext` read from the database (shared by the AI-060 handler and the Part 2 job).

AI-051 left the context as explicit inputs. This builds it from approved tables only:

- `constraint_types` (every row; all workers may read it, CT-15);
- `vessel_types` (code → id, because `safety_constraints` scope by id);
- the AI-054 tug requirement of each request in the port snapshot, from the snapshot's own
  request, vessel and tug rows and the DEC-20 rules file. The schema has no `pilot_requested`
  field, so it stays `None` (the table applies; unknown never means zero tugs, AI-054).

Reference rows are read in their own short read-only transaction after the port snapshot; they
change only through Backend administration, so a separate read does not mix two plan states.
"""

from collections.abc import Mapping

import sqlalchemy as sa

from common.db.connection import core_of
from common.db.tables import CONSTRAINT_TYPES, VESSEL_TYPES
from common.runtime.runs import Connection
from part1.feasibility import Category, Comparator, ConstraintType
from part2.filter import FilterContext
from part2.state.model import PortState
from part2.tugs import (
    Tug,
    TugRequest,
    TugRequirement,
    TugRules,
    compute_tug_requirement,
    load_rules,
)


class ContextError(RuntimeError):
    """A request's tug requirement can't be computed from the data (DEC-20: never guessed)."""


def read_constraint_types(connection: Connection) -> tuple[ConstraintType, ...]:
    c = CONSTRAINT_TYPES
    rows = core_of(connection).execute(
        sa.select(
            c.c.id, c.c.code, c.c.category, c.c.unit, c.c.comparator, c.c.is_hard_safety_limit
        ).order_by(c.c.id)
    )
    return tuple(
        ConstraintType(
            int(r.id),
            r.code,
            Category(r.category),
            r.unit,
            Comparator(r.comparator),
            bool(r.is_hard_safety_limit),
        )
        for r in rows
    )


def read_vessel_type_ids(connection: Connection) -> dict[str, int]:
    rows = core_of(connection).execute(sa.select(VESSEL_TYPES.c.code, VESSEL_TYPES.c.id))
    return {r.code: int(r.id) for r in rows}


def tug_requirements(state: PortState, rules: TugRules) -> dict[int, TugRequirement]:
    """AI-054 per request of the snapshot; a request whose data DEC-20 rejects raises."""
    tugs = [Tug(t.id, t.tug_power, t.tug_power_unit) for t in state.tugs]
    out: dict[int, TugRequirement] = {}
    for r in state.requests:
        request = TugRequest(
            loa=r.loa,
            beam=r.beam,
            arrival_draft=r.arrival_draft,
            max_draft=r.max_draft,
            gross_tonnage=r.gross_tonnage,
            vessel_type_code=r.vessel_type_code,
            block_coefficient=r.block_coefficient,
            pilot_requested=None,
        )
        try:
            out[r.request_id] = compute_tug_requirement(request, tugs, rules)
        except ValueError as error:
            raise ContextError(f"request {r.request_id}: {error}") from error
    return out


def load_filter_context(
    connection: Connection, state: PortState, rules: TugRules | None = None
) -> FilterContext:
    """The context for the requests in `state`. Leaves no transaction open."""
    core = core_of(connection)
    try:
        constraint_types = read_constraint_types(connection)
        vessel_type_ids: Mapping[str, int] = read_vessel_type_ids(connection)
    finally:
        core.rollback()  # read-only
    return FilterContext(
        constraint_types=constraint_types,
        vessel_type_ids=vessel_type_ids,
        tug_requirements=tug_requirements(state, rules if rules is not None else load_rules()),
    )
