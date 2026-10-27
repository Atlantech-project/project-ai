# ATLANTECH — Team Contracts

This file lists every contract that two or more teams must agree on. For each contract it states:

- **Between:** who delivers and who receives.
- **Owner:** the team that writes the contract and keeps it current.
- **Reviewers:** the receiving teams, who must approve it.
- **Output:** the file or format that is delivered, with an example.

All contracts are written and approved in **Sprint 1**. Each contract has a task with the same ID (`CT-01` …). Any change after approval needs both sides to agree, an entry in the decision log, and a new version number.

**Proposed location:** a `contracts/` folder in the `PortHub` repository. Every OpenAPI file and JSON Schema in that folder is the single source of truth.

## Summary

| ID | Contract | From (owner) | To (receiver) | Related decision |
| --- | --- | --- | --- | --- |
| CT-01 | Port API conventions | Backend | Frontend · Mobile · QA | DEC-13 |
| CT-02 | Port API OpenAPI file | Backend | Frontend · Mobile · QA | DEC-13 |
| CT-03 | Web sign-in and session | Backend | Frontend | DEC-35 |
| CT-04 | Mobile sign-in and system info | Backend | Mobile | DEC-35 |
| CT-05 | Web SSE events | Backend | Frontend | DEC-05 |
| CT-06 | Mobile WebSocket events (Reverb) | Backend | Mobile | — |
| CT-07 | Mobile sync (Outbox) | Backend | Mobile | DEC-39 · DEC-40 |
| CT-08 | AI job envelope | AI (schema) · Backend (sending) | AI workers | DEC-04 |
| CT-09 | C-01 · Part 1 run | Backend | AI | DEC-14 |
| CT-10 | C-02 · Part 2 solve | Backend | AI | DEC-15 |
| CT-11 | C-03 · Yard placement | Backend | AI | DEC-16 |
| CT-12 | C-04 · BAPLIE parse | Backend | AI | DEC-17 |
| CT-13 | C-05 · Validation (FastAPI) | AI | Backend | DEC-03 · DEC-18 |
| CT-14 | C-06 · Completion message | AI | Backend | DEC-01 · DEC-19 |
| CT-15 | AI result tables and write ownership | AI | Backend | DEC-02 |
| CT-16 | FastAPI internal API | AI | Backend | DEC-10 |
| CT-17 | Database schema (migrations) | Backend | AI | DEC-08 |
| CT-18 | AI seed data and `port_setting` keys | AI | Backend | DEC-12 · DEC-23 |
| CT-19 | Mock worker behaviour | Backend | Frontend · Mobile · QA | — |
| CT-20 | AI result read endpoints | Backend | Frontend | DEC-43 |
| CT-21 | Shared status vocabulary | Backend | Frontend · Mobile · AI · QA | — |
| CT-22 | Screen design hand-off | UI/UX | Frontend · Mobile | — |
| CT-23 | API readiness pack (per FRR) | Backend | Frontend · Mobile · QA | DEC-13 |
| CT-24 | BAPLIE test corpus | QA | AI | DEC-17 |
| CT-25 | Reference data and thresholds inputs | QA | AI | DEC-30 · DEC-33 |
| CT-26 | QA report and defect format | QA | All teams | — |

---

## CT-01 · Port API conventions

| | |
| --- | --- |
| Between | Backend → Frontend · Mobile · QA |
| Owner | Backend Team |
| Reviewers | Frontend Team · Mobile Team · QA Team |
| Output | `contracts/api-conventions.md` |

**Content:**

- **Base path:** `/api/v1`. All times are ISO 8601 in UTC.
- **Headers:**
  - Web: cookie + `X-XSRF-TOKEN`.
  - Mobile: `Authorization: Bearer <token>`, `X-App-Version` and `X-Device-Id`.
  - Every mobile write carries an `Idempotency-Key`.
- **Version token:** every editable record returns a `version` (the `updated_at` value). Every update must send it back; a stale version returns 409.
- **Errors:** RFC 9457 format with a stable `code` and a `message_key`.
- **Error codes:** 401 · 403 · 409 · 422 · 426 · 503.
- **Pagination:** `?page=&per_page=`.

**Error example:**

```json
{
  "type": "https://atlantech.io/errors/version-conflict",
  "title": "Record changed",
  "status": 409,
  "code": "VERSION_CONFLICT",
  "message_key": "errors.version_conflict",
  "detail": "The berth was changed by another user.",
  "current": { "id": 12, "version": "2026-11-02T10:15:04Z" }
}
```

**422 example:**

```json
{
  "status": 422,
  "code": "VALIDATION_FAILED",
  "message_key": "errors.validation_failed",
  "errors": { "max_vessel_loa": ["errors.berth.loa_exceeds_length"] }
}
```

**Pagination example:**

```json
{ "data": [ { "id": 1 } ], "meta": { "page": 1, "per_page": 25, "total": 132 } }
```

---

## CT-02 · Port API OpenAPI file

| | |
| --- | --- |
| Between | Backend → Frontend · Mobile · QA |
| Owner | Backend Team (single owner, DEC-13) |
| Reviewers | Frontend Team · Mobile Team |
| Output | `contracts/openapi/port-api.yaml` (OpenAPI 3.0), updated in the same PR that changes an endpoint |

**Example:**

```yaml
paths:
  /api/v1/berthing-requests:
    post:
      summary: Create a berthing request
      tags: [Berthing]
      security: [{ cookieAuth: [] }]
      requestBody:
        content:
          application/json:
            schema: { $ref: '#/components/schemas/BerthingRequestCreate' }
      responses:
        '201': { content: { application/json: { schema: { $ref: '#/components/schemas/BerthingRequest' } } } }
        '403': { $ref: '#/components/responses/Forbidden' }
        '422': { $ref: '#/components/responses/ValidationFailed' }
components:
  schemas:
    BerthingRequestCreate:
      type: object
      required: [imo_number, requested_terminal_id, requested_eta, arrival_draft]
      properties:
        imo_number: { type: string, pattern: '^[0-9]{7}$' }
        requested_terminal_id: { type: integer }
        requested_eta: { type: string, format: date-time }
        arrival_draft: { type: number }
        cargo_lines: { type: array, items: { $ref: '#/components/schemas/CargoLine' } }
```

---

## CT-03 · Web sign-in and session

| | |
| --- | --- |
| Between | Backend → Frontend |
| Owner | Backend Team |
| Reviewers | Frontend Team |
| Output | Auth section of `port-api.yaml` + the flow steps in `contracts/auth-web.md` |

**Flow:**

1. `GET /sanctum/csrf-cookie`
2. `POST /api/v1/auth/login`
3. If `must_change_password = true`: `POST /api/v1/auth/change-password`
4. `POST /api/v1/auth/logout`

The sign-in identifier is set by DEC-35 (proposed: username).

```json
// POST /api/v1/auth/login
{ "username": "staff.ahmed", "password": "••••••••" }

// 200
{
  "id": 41,
  "name": "Port Staff",
  "role": "PORT_AUTHORITY_STAFF",
  "terminal_ids": [],
  "must_change_password": false
}

// 403
{ "status": 403, "code": "ACCOUNT_DISABLED", "message_key": "errors.account_disabled" }
```

---

## CT-04 · Mobile sign-in and system info

| | |
| --- | --- |
| Between | Backend → Mobile |
| Owner | Backend Team |
| Reviewers | Mobile Team |
| Output | Mobile auth section of `port-api.yaml` |

```json
// GET /api/v1/system/info
{ "port_id": "EGDAM", "port_name": "Damietta Port", "min_app_version": "1.0.0" }

// POST /api/v1/auth/mobile/login
{ "username": "pilot.k", "password": "••••••••", "device_id": "a1b2c3", "platform": "android", "app_version": "1.0.0" }

// 200
{
  "token": "<opaque>",
  "expires_at": "2026-12-02T10:00:00Z",
  "user": { "id": 77, "name": "Marine Pilot", "role": "MARINE_PILOT", "must_change_password": true }
}

// 426
{ "status": 426, "code": "APP_UPDATE_REQUIRED", "min_app_version": "1.1.0" }
```

---

## CT-05 · Web SSE events

| | |
| --- | --- |
| Between | Backend → Frontend |
| Owner | Backend Team |
| Reviewers | Frontend Team |
| Output | `contracts/realtime-sse.md`: the event list and the shape of each event |

`GET /api/v1/events` (`text/event-stream`):

- Events are filtered by role and terminal.
- After a dropped connection, `Last-Event-ID` replays the missed events.
- An event only says that something changed; the Frontend fetches the details over REST.

**Events:**
`REQUEST_STATUS_CHANGED` · `BAPLIE_PARSED` · `ENTRY_WINDOW_READY` · `RECOMMENDATION_READY` · `PLAN_CONFIRMED` · `PLAN_CANCELLED` · `ASSIGNMENT_CHANGED` · `NOTIFICATION_CREATED` · `NOTIFICATION_ACKNOWLEDGED` · `DEVIATION_DETECTED` · `REPLAN_PROPOSED` · `YARD_RECOMMENDATION_READY` · `YARD_RECOMMENDATION_FAILED` · `DRIFT_ALERT` · `RUN_FAILED`

```
id: 9f2c-0001
event: RECOMMENDATION_READY
data: {"entity":"berthing_request","id":1550,"recommendation_id":880,"status":"RECOMMENDATION_GENERATED","at":"2026-11-02T10:02:14Z"}
```

---

## CT-06 · Mobile WebSocket events (Reverb)

| | |
| --- | --- |
| Between | Backend → Mobile |
| Owner | Backend Team |
| Reviewers | Mobile Team |
| Output | `contracts/realtime-mobile.md` |

- **Channel:** `private-user.{user_id}`.
- **Event:** carries only the `event_id` and its type; the app fetches the details over REST.
- **Duplicates:** the app ignores any `event_id` it has already seen.
- **After every reconnect:** the app calls `GET /sync/changes`.

```json
{ "event_id": "e-77-000231", "type": "TASK_UPDATED", "entity": "plan_component", "entity_id": 5012 }
```

---

## CT-07 · Mobile sync (Outbox)

| | |
| --- | --- |
| Between | Mobile ↔ Backend |
| Owner | Backend Team (endpoints) · Mobile Team (event shape) |
| Reviewers | Mobile Team · Backend Team |
| Output | Sync section of `port-api.yaml` + `contracts/sync-events.md` |

**Event types:**

| Type | Payload | Note |
| --- | --- | --- |
| `STATUS_UPDATE` | `{ plan_component_id, new_status }` | In progress / Executed only (DEC-39) |
| `ACKNOWLEDGE` | `{ notification_id }` | DEC-40 |

```json
// POST /api/v1/sync/events
{
  "events": [
    {
      "client_event_id": "2c1f6a7e-1d0b-4c11-9a51-7f1e2b3c4d5e",
      "type": "STATUS_UPDATE",
      "payload": { "plan_component_id": 5012, "new_status": "STARTED" },
      "recorded_at": "2026-11-02T11:40:00Z",
      "client_sent_at": "2026-11-02T11:52:10Z",
      "sync_source": "TABLET"
    }
  ]
}

// 200: one result per event, in the same order
{
  "results": [
    { "client_event_id": "2c1f6a7e-…", "result": "APPLIED" },
    { "client_event_id": "8d9e…", "result": "REJECTED", "reason_code": "PLAN_CANCELLED" }
  ]
}

// GET /api/v1/sync/changes?since=tok_118
{ "tasks": [ ], "notifications": [ ], "removed": [ { "entity": "plan_component", "id": 5003 } ], "sync_token": "tok_131" }
```

`result` values: `APPLIED` · `DUPLICATE` · `REJECTED`.

---

## CT-08 · AI job envelope

| | |
| --- | --- |
| Between | Backend → AI |
| Owner | AI Team (JSON Schema) · Backend Team (sending with RPUSH) |
| Reviewers | Backend Team · AI Team |
| Output | `contracts/ai/envelope.schema.json` |

- **Queues:** `queue:part1` · `queue:part2` · `queue:edi`.
- **`job_type`:** `PART1_RUN` · `PART2_SOLVE` · `YARD_PLACEMENT` · `BAPLIE_PARSE`.
- **Idempotency:** the worker claims the run with a conditional update (QUEUED → RUNNING), so a second delivery of the same run is ignored.

**Error categories:**
`INVALID_ENVELOPE` · `PRECONDITION_FAILED` · `DATA_UNAVAILABLE` · `CONFIGURATION_ERROR` · `INFEASIBLE` · `SOLVER_ERROR` · `TIMEOUT` · `INTERNAL_ERROR`

```json
{
  "contract_version": "1.0",
  "job_type": "PART2_SOLVE",
  "job_id": "a2c9d1f0-1b77-4c2e-8f44-5d6e7f809a1b",
  "run_id": 2301,
  "enqueued_at": "2026-11-02T10:02:11Z",
  "triggered_by_user_id": 41,
  "payload": { }
}
```

---

## CT-09 · C-01 · Part 1 run

| | |
| --- | --- |
| Between | Backend → AI (Part 1) |
| Owner | Backend Team (sending) on the AI Team schema |
| Reviewers | AI Team |
| Output | `contracts/ai/c01-part1-run.schema.json` |

```json
{
  "contract_version": "1.0",
  "job_type": "PART1_RUN",
  "job_id": "3f6b2c1e-8a1d-4a51-9f1e-2b0c7d9e4a10",
  "run_id": 812,
  "enqueued_at": "2026-11-02T09:15:04Z",
  "triggered_by_user_id": 41,
  "payload": { "berthing_request_id": 1550, "reason": "CUSTOMS_APPROVAL" }
}
```

- **`reason` values:** `CUSTOMS_APPROVAL` · `RECOMPUTE` · `MANUAL_DATA` · `REOPEN`.
- With `MANUAL_DATA`, the payload also carries `manual_forecast_run_id`.
- **Result in the database:**
  - `part1_run`: status and outcome (`WINDOWS_FOUND` · `NO_FEASIBLE_WINDOW` · `ENV_DATA_UNAVAILABLE`).
  - `entry_window_proposal`, `feasible_window` and `blocked_period`.

---

## CT-10 · C-02 · Part 2 solve

| | |
| --- | --- |
| Between | Backend → AI (Part 2) |
| Owner | Backend Team (sending) on the AI Team schema |
| Reviewers | AI Team |
| Output | `contracts/ai/c02-part2-solve.schema.json` |

```json
{
  "contract_version": "1.0",
  "job_type": "PART2_SOLVE",
  "job_id": "b81e…",
  "run_id": 2302,
  "enqueued_at": "2026-11-02T12:20:00Z",
  "triggered_by_user_id": null,
  "payload": {
    "trigger_type": "RESOURCE_CHANGE",
    "berthing_request_ids": [1550, 1553],
    "purpose": "INITIAL",
    "changed_resource": { "type": "TUG", "id": 7 }
  }
}
```

- **`trigger_type` values:** `NEW_REQUEST` · `MANUAL` · `RESOURCE_CHANGE` · `REPLAN`.
- With `REPLAN`, the payload carries `operational_plan_id` and `purpose = DELAY_REPLAN`.

**`solver_run.result_detail` (written by the AI):**

```json
{
  "outcome": "NO_FEASIBLE_PLAN",
  "request_ids": [1550],
  "failure_reason": null,
  "binding_constraints": [
    { "request_id": 1550, "constraint_type_code": "MAX_LOA", "detail": "No berth accepts LOA 366 m" }
  ]
}
```

---

## CT-11 · C-03 · Yard placement

| | |
| --- | --- |
| Between | Backend → AI (Part 2) |
| Owner | Backend Team (sending) on the AI Team schema |
| Reviewers | AI Team |
| Output | `contracts/ai/c03-yard.schema.json` |

```json
{
  "contract_version": "1.0",
  "job_type": "YARD_PLACEMENT",
  "job_id": "c4d…",
  "run_id": 640,
  "enqueued_at": "2026-11-02T13:00:00Z",
  "triggered_by_user_id": null,
  "payload": { "terminal_recommendation_id": 640, "operational_plan_id": 311 }
}
```

- **Result:** `terminal_recommendation.lifecycle_status` becomes `YARD_REC_GENERATED` (with `confidence`) or `GENERATION_FAILED` (with `failure_reason`).
- `yard_placement_item` rows: block required, slot optional.
- The worker never reserves a slot.

---

## CT-12 · C-04 · BAPLIE parse

| | |
| --- | --- |
| Between | Backend → AI (EDI Parser) |
| Owner | Backend Team (sending) on the AI Team schema |
| Reviewers | AI Team |
| Output | `contracts/ai/c04-baplie.schema.json` |

```json
{
  "contract_version": "1.0",
  "job_type": "BAPLIE_PARSE",
  "job_id": "d9a…",
  "run_id": 205,
  "enqueued_at": "2026-11-02T08:05:00Z",
  "triggered_by_user_id": 41,
  "payload": { "baplie_file_id": 205 }
}
```

- **Result:** `parse_status` becomes `PARSED`, `QUARANTINED` or `FAILED`.
- On `PARSED`: the worker writes `container` and `container_manifest_entry`, and fills empty fields in `vessel`.
- On issues: `baplie_parse_issue` rows.
- The commit is all or nothing.

---

## CT-13 · C-05 · Validation (FastAPI)

| | |
| --- | --- |
| Between | AI → Backend |
| Owner | AI Team |
| Reviewers | Backend Team |
| Output | Validate section of `contracts/openapi/ai-internal.yaml` |

- **Override and yard adjustment:** synchronous request with an immediate answer (DEC-03).
- **BAPLIE correction:** asynchronous on `queue:edi` with the same fields; the result comes back through C-06.
- **If the FastAPI service is unreachable:** the Backend refuses the change (fail closed).

```json
// POST /internal/v1/validate
{
  "validation_type": "OVERRIDE",
  "subject_id": 9031,
  "proposed_change": { "component_type": "BERTH", "new_value": 14 }
}

// 200
{
  "valid": false,
  "violations": [
    { "constraint_type_code": "MAX_DRAFT", "message_key": "validation.berth.draft_exceeded", "detail": "Draft 14.2 m > berth depth 13.5 m" }
  ]
}
```

---

## CT-14 · C-06 · Completion message

| | |
| --- | --- |
| Between | AI → Backend |
| Owner | AI Team |
| Reviewers | Backend Team |
| Output | `contracts/ai/c06-completion.schema.json`; the list is named `queue:ai-results` |

```json
{
  "contract_version": "1.0",
  "job_type": "PART2_SOLVE",
  "run_id": 2301,
  "status": "DONE",
  "outcome": "SOLVED",
  "error_category": null,
  "finished_at": "2026-11-02T10:02:14Z"
}
```

- Part 3 uses the same message with `job_type = PART3_EVALUATION`, `outcome = DRIFT_DETECTED` and `drift_measurement_id`.
- On receipt, the Backend performs the request transition, writes the audit entry, and sends the notification and the SSE event.

---

## CT-15 · AI result tables and write ownership

| | |
| --- | --- |
| Between | AI → Backend |
| Owner | AI Team |
| Reviewers | Backend Team |
| Output | `contracts/ai/table-ownership.md` |

| Table | Created by | Completed by |
| --- | --- | --- |
| `part1_run` | Backend (QUEUED) | AI (status, outcome, retries) |
| `entry_window_proposal` · `feasible_window` · `blocked_period` | AI | Backend (confirm or reject) |
| `forecast_run` · `environment_forecast_point` | AI (scheduled and on-demand) · Backend (manual) | — |
| `tide_prediction_run` · `tide_prediction_point` · `demand_forecast_slot` | AI | — |
| `solver_run` | Backend (QUEUED) | AI |
| `recommendation` · `recommendation_option` · `recommendation_option_tug` · `recommendation_rationale_factor` | AI | Backend (CONFIRMED, MODIFIED_BY_STAFF, REPLACED) |
| `terminal_recommendation` · `yard_placement_item` | Backend (request) · AI (result) | Backend (decision and export) |
| `baplie_file` (status fields) · `baplie_parse_issue` · `container` · `container_manifest_entry` | Backend (file) · AI (parsing) | — |
| `evaluation_metric` · `drift_measurement` | AI | — |
| `berthing_request` · `audit_log` · `notification_log` | Backend only | — |

---

## CT-16 · FastAPI internal API

| | |
| --- | --- |
| Between | AI → Backend |
| Owner | AI Team |
| Reviewers | Backend Team |
| Output | `contracts/openapi/ai-internal.yaml`, the OpenAPI file generated by FastAPI |

The FastAPI service is internal to the port server and is not exposed to the web or the mobile app. Authentication uses `X-Service-Token` (DEC-10).

| Endpoint | Purpose |
| --- | --- |
| `GET /internal/v1/health` | Service health and DB / Redis connectivity |
| `GET /internal/v1/workers` | Status and last heartbeat of each worker |
| `GET /internal/v1/runs/{job_type}/{run_id}` | Run status for diagnosis |
| `POST /internal/v1/validate` | CT-13 |

```json
// GET /internal/v1/workers
{
  "workers": [
    { "name": "part2", "status": "UP", "last_heartbeat": "2026-11-02T10:05:00Z", "queue_depth": 0, "version": "0.6.0" },
    { "name": "edi", "status": "UP", "last_heartbeat": "2026-11-02T10:04:58Z", "queue_depth": 1, "version": "0.6.0" }
  ]
}
```

---

## CT-17 · Database schema (migrations)

| | |
| --- | --- |
| Between | Backend → AI |
| Owner | Backend Team (single owner of migrations) |
| Reviewers | AI Team |
| Output | Migrations in `project-backend`, and `contracts/db/schema.sql` updated with every new migration |

- The AI Team builds its test schema from `schema.sql`.
- Any change to a table the AI writes to is requested through the Backend and needs AI Team approval.

```sql
-- contracts/db/schema.sql (excerpt)
CREATE TABLE part1_run (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  berthing_request_id BIGINT UNSIGNED NOT NULL,
  status ENUM('QUEUED','RUNNING','DONE','FAILED','REPLACED') NOT NULL,
  outcome ENUM('WINDOWS_FOUND','NO_FEASIBLE_WINDOW','ENV_DATA_UNAVAILABLE') NULL,
  retry_count TINYINT UNSIGNED NOT NULL DEFAULT 0,
  entry_window_proposal_id BIGINT UNSIGNED NULL
);
```

---

## CT-18 · AI seed data and `port_setting` keys

| | |
| --- | --- |
| Between | AI → Backend |
| Owner | AI Team |
| Reviewers | Backend Team (writes the seeders) |
| Output | `contracts/ai/seed-spec.json` |

```json
{
  "constraint_type": [ { "code": "MAX_WIND_KN", "category": "ENVIRONMENT", "unit": "kn", "comparator": "<=", "is_hard_safety_limit": true } ],
  "objective_term": [ { "code": "WAITING_TIME", "weight": 1.0 }, { "code": "RESOURCE_UTILISATION", "weight": 0.2 } ],
  "rationale_template": [ { "code": "BEST_WAIT", "version": 1, "text": "Lowest waiting time for {vessel} at berth {berth}." } ],
  "ml_model": [ { "key": "B3_SERVICE_TIME", "phase": 1 } ],
  "port_setting": [ { "key": "solver_time_limit_seconds", "type": "int", "value": 10 } ]
}
```

---

## CT-19 · Mock worker behaviour

| | |
| --- | --- |
| Between | Backend → Frontend · Mobile · QA |
| Owner | Backend Team |
| Reviewers | Frontend Team · QA Team |
| Output | `contracts/mock-workers.md`: for each queue, the results it returns and how to choose a scenario |

- Mocks write contract-shaped rows and send C-06, so the Frontend cannot tell them apart from the real workers.
- The scenario is selected with the `mock_scenario` key in `port_setting`, or with a tag in the vessel name.

| Queue | Scenarios |
| --- | --- |
| `queue:part1` | `WINDOWS_FOUND` · `NO_FEASIBLE_WINDOW` · `ENV_DATA_UNAVAILABLE` · `FAILED` |
| `queue:part2` | `SOLVED` · `FIFO_FALLBACK` · `NO_FEASIBLE_PLAN` · `GENERATION_FAILED` |
| `queue:edi` | `PARSED` · `QUARANTINED` · `FAILED` |
| yard | `YARD_REC_GENERATED` · `GENERATION_FAILED` |

---

## CT-20 · AI result read endpoints

| | |
| --- | --- |
| Between | Backend → Frontend |
| Owner | Backend Team |
| Reviewers | Frontend Team |
| Output | AI results section of `port-api.yaml` |

| Endpoint | Returns | Role |
| --- | --- | --- |
| `GET /api/v1/berthing-requests/{id}/part1-result` | Outcome, windows, blocked periods, data sources and their age | Port Authority Staff |
| `GET /api/v1/berthing-requests/{id}/recommendation` | Current version, options, tugs, rationale and binding constraints | Port Authority Staff |
| `GET /api/v1/terminal-recommendations/{id}` | Yard placements, rationale and confidence | CT Operation Planner (own terminal) |
| `GET /api/v1/environment/conditions` | Weather, tide, surge, source and data age | All office users |
| `GET /api/v1/ai/evaluation` · `GET /api/v1/ai/drift` | Metrics and drift | Port Admin |

```json
// GET /api/v1/berthing-requests/1550/recommendation
{
  "recommendation_id": 880,
  "version": 2,
  "status": "PENDING_REVIEW",
  "source": "AI",
  "purpose": "INITIAL",
  "options": [
    {
      "id": 9031, "rank": 1, "berth": { "id": 12, "code": "B12" },
      "start": "2026-11-03T06:00:00Z", "end": "2026-11-03T18:30:00Z",
      "pilot": { "id": 4 }, "tugs": [ { "id": 7 }, { "id": 9 } ],
      "service_time_hours": 12.5, "delay_risk": null,
      "objective_score": 0.82, "rationale": "Lowest waiting time for MSC Aurora at berth B12."
    }
  ]
}
```

---

## CT-21 · Shared status vocabulary

| | |
| --- | --- |
| Between | Backend → Frontend · Mobile · AI · QA |
| Owner | Backend Team (from the PHP enums) |
| Reviewers | All teams |
| Output | `contracts/status-vocabulary.json`, generated automatically from the enums |

```json
{
  "berthing_request.status": ["SUBMITTED","NEEDS_REVISION","PRELIMINARY_APPROVED","CUSTOMS_APPROVED","ENTRY_WINDOW_CONFIRMED","RECOMMENDATION_GENERATED","PLAN_CONFIRMED","PLAN_CANCELLED","COMPLETED","REJECTED","CANCELLED"],
  "plan_component.status": ["UNASSIGNED","ASSIGNED","STARTED","DONE"],
  "recommendation.status": ["PENDING_REVIEW","MODIFIED_BY_STAFF","CONFIRMED","REPLACED"],
  "notification.status": ["SENT","FAILED","ESCALATED"],
  "terminal_recommendation.lifecycle_status": ["YARD_REC_REQUESTED","YARD_REC_GENERATED","GENERATION_FAILED","ACCEPTED","REJECTED","EXPORTED_TO_TOS"]
}
```

---

## CT-22 · Screen design hand-off

| | |
| --- | --- |
| Between | UI/UX → Frontend · Mobile |
| Owner | UI/UX Team |
| Reviewers | Frontend Team · Mobile Team |
| Output | A Figma file where every frame is named by its Page ID with all its states next to it, plus the tokens in `contracts/design/tokens.json` |

**Rules:**

- Frame names follow the pattern `P-38 / Recommendation Review / Default`, with the states next to it: `/ Loading`, `/ Empty`, `/ Error`, `/ Conflict`.
- Web and tablet are separate frames.

```json
{
  "color": {
    "navy": "#083A4F", "gold": "#A58D66", "teal-light": "#C0D5D6",
    "teal-mid": "#407E8C", "off-white": "#E5E1DD"
  },
  "font": { "heading": "Montserrat", "body": "Inter" },
  "radius": { "sm": 4, "md": 8 },
  "space": [4, 8, 12, 16, 24, 32]
}
```

---

## CT-23 · API readiness pack (per FRR)

| | |
| --- | --- |
| Between | Backend → Frontend · Mobile · QA |
| Owner | Backend Team |
| Reviewers | Frontend Team · Mobile Team · QA Team at the FRR |
| Output | `contracts/readiness/FT-xx.md` for each feature |

```markdown
# FT-06 Berthing requests and BAPLIE — API readiness pack
- Endpoints (merged to develop): POST /api/v1/berthing-requests, GET /api/v1/berthing-requests, ...
- OpenAPI diff: link to the PR
- Examples: requests and responses for 201, 403, 409, 422
- Seed data on the dev server: 5 requests in every status, 2 BAPLIE files (parsed, quarantined)
- Events: REQUEST_STATUS_CHANGED, BAPLIE_PARSED
- Behind it: mock worker for queue:edi (scenario PARSED)
- Known gaps: none
```

---

## CT-24 · BAPLIE test corpus

| | |
| --- | --- |
| Between | QA → AI |
| Owner | QA Team |
| Reviewers | AI Team |
| Output | Folder `contracts/ai/baplie-corpus/`: every `.edi` file with an `.expected.json` file next to it |

```json
// valid-small-01.expected.json
{
  "file": "valid-small-01.edi",
  "expected_parse_status": "PARSED",
  "containers": 212,
  "issues": [],
  "vessel_imo": "9811000"
}
```

Scenarios that must be covered: a valid file, a file with a different IMO (`QUARANTINED`), a file with invalid values (`QUARANTINED` with diagnostics), an unreadable file (`FAILED`), and every size class.

---

## CT-25 · Reference data and thresholds inputs

| | |
| --- | --- |
| Between | QA → AI |
| Owner | QA Team |
| Reviewers | AI Team |
| Output | `contracts/ai/reference-data/*.csv`, with a `source` column and an `is_synthetic` column on every row |

```csv
berth_code,terminal_code,length_m,depth_m,max_loa_m,source,is_synthetic
B12,DCT,350,14.5,345,"Damietta Port published berth list",false
B13,DCT,350,14.5,345,"Generated to complete terminal",true
```

---

## CT-26 · QA report and defect format

| | |
| --- | --- |
| Between | QA → All teams |
| Owner | QA Team |
| Reviewers | Leads Council |
| Output | `contracts/qa/release-report-template.md` and the defect template in GitHub Issues |

```markdown
# Release test report — v0.N.0
- Repositories and commits tested: backend@abc123, frontend@def456, mobile@..., ai@...
- Features tested (from FRR): FT-xx, FT-yy
- Result: PASS / PASS WITH NOTES / FAIL
- Blocking defects: #123, #130
- Sign-off: QA Team
```

**Defect fields:** `ID` · `Feature` · `Page ID / Endpoint` · `Steps` · `Expected` · `Actual` · `Severity (Blocker / Major / Minor)` · `Repository` · `Found on (release branch)`.
