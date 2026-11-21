"""The `queue:validate` handler (AI-060, CT-13 v1.1, DEC-03).

Reads the option and its recommendation, the live port state (AI-050) and B2's context
(`part2.context`), validates the officer's change and returns C-06 `validation_result`. It writes
nothing. `YARD_ADJUSTMENT` is AI-067 and is refused as a configuration error until it exists.
"""

from datetime import datetime
from typing import Any, Final

import sqlalchemy as sa

from common.db.connection import core_of
from common.db.tables import RECOMMENDATION_OPTION_TUGS, RECOMMENDATION_OPTIONS, RECOMMENDATIONS
from common.runtime.envelope import JobType
from common.runtime.errors import ErrorCategory, JobError
from common.runtime.worker import JobContext, JobResult, WorkerDefinition
from part2.context import ContextError, load_filter_context
from part2.filter import Option
from part2.state.snapshot import load_port_state
from part2.validation.override import (
    OverrideMismatchError,
    apply_changes,
    parse_changes,
    validate_override,
)

WORKER_VERSION: Final = "validate-0.2.0"
EDITABLE: Final = frozenset({"PENDING_REVIEW", "MODIFIED_BY_STAFF"})  # CT-13 precondition


def read_option(connection: Any, option_id: int) -> tuple[Option, str]:
    """The option as B2 sees it, and its recommendation's status."""
    o, r, t = RECOMMENDATION_OPTIONS, RECOMMENDATIONS, RECOMMENDATION_OPTION_TUGS
    core = core_of(connection)
    row = (
        core.execute(
            sa.select(
                o.c.berth_id,
                o.c.planned_start,
                o.c.planned_end,
                o.c.pilot_user_id,
                r.c.berthing_request_id,
                r.c.status,
            )
            .select_from(o.join(r, r.c.id == o.c.recommendation_id))
            .where(o.c.id == option_id)
        )
        .mappings()
        .first()
    )
    if row is None:
        raise JobError(
            ErrorCategory.PRECONDITION_FAILED, f"no recommendation_options row {option_id}"
        )
    tugs = tuple(
        sorted(
            int(x[0])
            for x in core.execute(sa.select(t.c.tugboat_id).where(t.c.option_id == option_id))
        )
    )
    option = Option(
        request_id=int(row["berthing_request_id"]),
        berth_id=int(row["berth_id"]),
        start=row["planned_start"],
        end=row["planned_end"],
        pilot_user_id=row["pilot_user_id"],
        tug_ids=tugs,
    )
    return option, str(row["status"])


def handler(context: JobContext) -> JobResult:
    payload = context.envelope.payload
    if payload["validation_type"] != "OVERRIDE":
        raise JobError(
            ErrorCategory.CONFIGURATION_ERROR,
            "YARD_ADJUSTMENT validation is not built yet (AI-067)",
        )
    subject_id = int(payload["subject_id"])
    connection = context.connection
    try:
        option, status = read_option(connection, subject_id)
    finally:
        core_of(connection).rollback()  # load_port_state needs no open transaction
    if status not in EDITABLE:
        raise JobError(
            ErrorCategory.PRECONDITION_FAILED, f"the recommendation is {status}, not editable"
        )
    try:
        changes = parse_changes(payload["proposed_change"])
        changed = apply_changes(option, changes)
    except OverrideMismatchError as error:
        raise JobError(ErrorCategory.PRECONDITION_FAILED, str(error)) from error
    start: datetime = min(option.start, changed.start)
    end: datetime = max(option.end, changed.end)
    state = load_port_state(connection, [option.request_id], horizon_start=start, horizon_end=end)
    try:
        filter_context = load_filter_context(connection, state)
    except ContextError as error:
        raise JobError(ErrorCategory.DATA_UNAVAILABLE, str(error)) from error
    result = validate_override(state, subject_id, option, changes, filter_context)
    return JobResult(
        outcome=result.outcome,
        completion_fields={"validation_result": result.validation_result()},
    )


DEFINITION: Final = WorkerDefinition(JobType.VALIDATION, handler, (), WORKER_VERSION)
