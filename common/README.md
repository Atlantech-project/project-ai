# common

Code shared by every worker (`edi`, `part1`, `part2`, `part3`). It holds no worker logic of its own.

## Worker and queue

None. `common` is not a worker and consumes no queue.

## Contents

- `units.py`: conversions between the PortSync speed and distance units; unknown units and cross-dimension conversions raise (AI-014)
- `time.py`: UTC ↔ port-local time and `port_shift` intervals, with errors for daylight-saving gaps and overlaps (AI-014). Shares the stdlib `time` name: import it as `common.time` and never run a script from inside `common/`.
- `datum.py`: datum consistency check across tide set, channel and berth; no datum conversion (DEC-27) (AI-014)
- `config.py`: environment and `port_settings` loading with typed parsing (AI-012)
- `runtime/`: the shared worker runtime: queue consumer, envelope validation, claim, retries, guarded completion, C-06, logs and graceful shutdown (AI-011)

The layout is Proposed by AI-014 and AI-011 (OQ-8): `common.<module>` imports, no packaging, and workers run as `python -m <module>` from the repository root.

## Planned contents

Later tasks add, among others (all PROPOSED in the backlog):

- db: data-access layer (AI-013)
- quality (AI-025), registry (AI-070), health (AI-091), observability (AI-092)

## Configuration (AI-012)

**Refresh rule:** workers read `port_settings` once per job with no cache (DEC-12, CT-18 §4), so a saved change applies from the next job with no redeploy. Use an autocommit connection, or commit or roll back after every read. PyMySQL connections default to non-autocommit, and on those the read itself opens a transaction, so with no `BEGIN` anywhere MySQL's default REPEATABLE READ keeps returning the startup values until it ends.

**When a problem stops what:**

| Problem | When | Result |
| --- | --- | --- |
| Missing database or Redis variable | Startup | The worker stops |
| Bad or missing key the worker uses, with an approved value today (`KEYS_WITH_APPROVED_VALUE`) | Startup | The worker stops |
| Key still ⟨AI⟩ in CT-18, or anything found during a job | When a job reads it | That job fails with `CONFIGURATION_ERROR`; the worker keeps running |

**Environment variables (Proposed, awaiting Backend confirmation):** `AI_DB_HOST`, `AI_DB_PORT`, `AI_DB_NAME`, `AI_DB_USER_<PART>`, `AI_DB_PASSWORD_<PART>`, `AI_REDIS_URL`, `AI_PROVIDER_PRIMARY_KEY`, `AI_PROVIDER_SECONDARY_KEY`, `AI_ARTIFACT_DIR`, `AI_BAPLIE_VOLUME`, `AI_SCHEMA_DIR`. `<PART>` is `PART1`, `PART2`, `YARD`, `EDI`, `VALIDATE` or `PART3`, one per DEC-08 account.

**Calling it from a worker:** `runtime.worker.run_worker` calls `load_env_settings` and `check_startup_settings` at startup and exits non-zero if they raise. Each job calls `read_port_settings` and `check_consistency`; handlers use the typed getters.

## Worker runtime (AI-011)

A worker gives `run_worker` a `WorkerDefinition` and a `connect_with` function. It follows CT-08 §6: `BLPOP`, validate, claim, run with retries, one guarded transaction, then C-06.

- **Handlers:** take a `JobContext`, write rows on `context.connection`, and return a `JobResult` or raise `JobError`. They must not commit: the runtime owns commit and rollback. A yard handler must itself re-check that its row is still `YARD_REC_REQUESTED` before finishing (CT-11).
- **Connections:** manual commit, with `time_zone = '+00:00'` (CT-17). AI-013 owns how they are created. One is opened before each `BLPOP`, so a database outage leaves messages on the queue. A lost connection is replaced, and the attempt counts as a failed one.
- **Redis:** use `connect_redis`, the default. redis-py's default socket timeout equals the `BLPOP` timeout, which can lose a message the server has popped. Redis is checked at startup.
- **Logs:** an exception is logged as its type and traceback location, never its text, which can hold a provider key or a URL.
- **Schemas:** loaded at startup from `AI_SCHEMA_DIR`. Inside a Git checkout (development and CI) it defaults to `docs/ref/ai-payloads/`, with a warning. A deployment must set it and ship the files (AI-090). A missing schema stops the worker.
- **A message on the wrong queue:** logged at ERROR and dropped, never claimed. This deviates from CT-08 §6 step 3, with a Proposed change on PortHub.
- **Retries:** immediate, with no delay. The delay is an open question.
- **`part1_max_retries`:** above 3 the job fails with `CONFIGURATION_ERROR`, because `chk_p1r_retry` can't record more. It isn't clamped. An `ai-request` to the Backend is needed.
- **Stale runs:** the Backend sweeps them. If it does so mid-job, the guarded update loses, everything rolls back and nothing is sent.

## Never

- Workers write only the tables listed for them in Architecture §12.2. CT-15 lists `berthing_request`, `audit_log` and `notification_log` as "Backend only"; Architecture §11 gives the Backend the audit of user actions and `notification_log`.

## Pending

- OQ-1: Python tooling, version, dependency management and environment.
- DEC-02: who writes status transitions, history, audit and run rows (Open; its recommendation is that the Backend writes every request transition, history row and audit entry). Note that Architecture §12.4 says `audit_log.actor_id` NULL means "system / AI worker", which DEC-02 needs to reconcile with CT-15.
- OQ-3: whether an internal FastAPI module exists, and where (DEC-10, Open).

## References

- `docs/ref/ATLANTECH_AI_ARCHITECTURE.md` §2, §11, §12.2, §12.4, §13
- `docs/ref/ATLANTECH_Contracts.md` CT-15
- `docs/tasks/ATLANTECH_AI_TASKS.md` AI-011 to AI-014
- `docs/ref/ATLANTECH_Decisions.md` AI-010 task decision (module structure)
