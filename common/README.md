# common

Code shared by every worker (`edi`, `part1`, `part2`, `part3`). It holds no worker logic of its own.

## Worker and queue

None. `common` is not a worker and consumes no queue.

## Planned contents

Nothing is created yet. Later tasks add, among others (all PROPOSED in the backlog):

- runtime: queue consumer, idempotent claim, retries, logging (AI-011)
- config: environment and `port_setting` loader (AI-012)
- db: data-access layer (AI-013)
- units and time: unit, datum and time utilities (AI-014)
- quality (AI-025), registry (AI-070), health (AI-091), observability (AI-092)

## Never

- Workers write only the tables listed for them in Architecture §12.2. CT-15 lists `berthing_request`, `audit_log` and `notification_log` as "Backend only"; Architecture §11 gives the Backend the audit of user actions and `notification_log`.

## Pending

- OQ-1: Python tooling, version, dependency management and environment.
- DEC-02: who writes status transitions, history, audit and run rows (Open; its recommendation is that the Backend writes every request transition, history row and audit entry). Note that Architecture §12.4 says `audit_log.actor_id` NULL means "system / AI worker", which DEC-02 needs to reconcile with CT-15.
- OQ-3: whether an internal FastAPI module exists, and where (DEC-10, Open).
- OQ-8: Python package and import layout.

## References

- `docs/ref/ATLANTECH_AI_ARCHITECTURE.md` §2, §11, §12.2, §12.4, §13
- `docs/tasks/ATLANTECH_Contracts.md` CT-15
- `docs/tasks/ATLANTECH_AI_TASKS.md` AI-011 to AI-014
- `docs/tasks/DECISION_LOG.md` DL-002 (module structure)
