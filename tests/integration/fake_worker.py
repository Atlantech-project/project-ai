"""A real worker process for the process-level tests, with a handler that only waits."""

import sys
import time

from common.db.connection import connect_worker
from common.runtime.envelope import JobType
from common.runtime.worker import JobContext, JobResult, WorkerDefinition, run_worker

HANDLER_SECONDS = 2.0


def _handler(_context: JobContext) -> JobResult:
    time.sleep(HANDLER_SECONDS)
    return JobResult("WINDOWS_FOUND", completion_fields={"entry_window_proposal_id": 4})


if __name__ == "__main__":
    definition = WorkerDefinition(JobType.PART1_RUN, _handler, ("part1_max_retries",), "0.1.0")
    sys.exit(run_worker(definition, connect_worker))
