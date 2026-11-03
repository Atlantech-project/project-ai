"""Valid messages for the worker runtime tests, one per job type (CT-08 to CT-13)."""

import json
import uuid
from typing import Any

from common.runtime.envelope import JobType

PAYLOADS: dict[JobType, dict[str, Any]] = {
    JobType.PART1_RUN: {"berthing_request_id": 7, "reason": "RECOMPUTE"},
    JobType.PART2_SOLVE: {
        "trigger_type": "NEW_REQUEST",
        "triggers": [{"trigger_type": "NEW_REQUEST", "berthing_request_ids": [7]}],
    },
    JobType.YARD_PLACEMENT: {"terminal_recommendation_id": 11, "operational_plan_id": 3},
    JobType.BAPLIE_PARSE: {"baplie_file_id": 21, "source": "FILE"},
    JobType.VALIDATION: {
        "validation_type": "OVERRIDE",
        "subject_id": 5,
        "proposed_change": {"changes": [{"component_type": "BERTH", "override_berth_id": 3}]},
    },
}


def envelope(job: JobType, run_id: int | None = 1, **overrides: Any) -> dict[str, Any]:
    message: dict[str, Any] = {
        "contract_version": "1.0",
        "job_type": job.value,
        "job_id": str(uuid.uuid4()),
        "run_id": None if job is JobType.VALIDATION else run_id,
        "enqueued_at": "2026-11-03T10:00:00Z",
        "triggered_by_user_id": 41 if job is JobType.VALIDATION else None,
        "payload": PAYLOADS[job],
    }
    message.update(overrides)
    return message


def raw(job: JobType, run_id: int | None = 1, **overrides: Any) -> bytes:
    return json.dumps(envelope(job, run_id, **overrides)).encode()
