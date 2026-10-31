# ATLANTECH — Team Contracts

This file lists every contract that two or more teams must agree on. For each contract it states:

- **Between:** who delivers and who receives.
- **Owner:** the team that writes the contract and keeps it current.
- **Reviewers:** the receiving teams, who must approve it.
- **Output:** the file or format that is delivered, with an example.

All contracts are written and approved in **Sprint 1**. Each contract has a task with the same ID (`CT-01` …). Any change after approval needs both sides to agree and a new version number, recorded directly in this file.

**Single source of truth.** This file is the only record of the contracts' text; there is no separate contract log. Changes are made in the contract they concern, never in a parallel copy:

- **Proposed.** A proposed change is a `Proposed change` row in the contract's table (date · task · change with the version bump · reason · evidence · awaiting whom). A new contract version is written as `Proposed vX.Y` in its Status row. Either way, it stays proposed until the Owner and Reviewers approve it.
- **Approved.** The approval is written into the Status row (`Approved vX.Y · date`), with who approved it, and the `Proposed change` row is removed.
- **No new IDs.** New `CT-` IDs are never assigned outside the team leads.

**Proposed location:** a `contracts/` folder in the `PortHub` repository. Every OpenAPI file and JSON Schema in that folder is the single source of truth.

**Local reference copies in `project-ai`:** `docs/ref/ai-payloads/` mirrors `contracts/ai/` (today the envelope, C-01 to C-06 and worker-heartbeat schemas, `table-ownership.md` and `contract-v1-record.md`). `docs/ref/db/` mirrors `contracts/db/` for `table-names.md` only; the schema snapshot `schema.sql` is not mirrored and is read from PortHub `contracts/db/schema.sql`. `api-conventions.md`, `error-codes.md`, `auth-web.md` and `openapi/port-api.yaml` are read from PortHub `contracts/`. The contract paths and the schemas' `$id` URLs below keep their `contracts/ai/` and `contracts/db/` names.

**Table names:** plural, as set by CT-17 (`users`, `solver_runs`, …); the full list is `contracts/db/table-names.md`. Column and foreign-key names stay singular (`vessel_id`).

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
| CT-13 | C-05 · Validation (`queue:validate`) | AI | Backend | DEC-03 · DEC-18 |
| CT-14 | C-06 · Completion message | AI | Backend | DEC-01 · DEC-19 |
| CT-15 | AI result tables and write ownership | AI | Backend | DEC-02 |
| CT-16 | Worker health over Redis | AI | Backend | DEC-10 |
| CT-17 | Database schema (migrations) | Backend | AI | DEC-08 |
| CT-18 | AI seed data and `port_settings` keys | AI | Backend | DEC-12 · DEC-23 |
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
| Reviewers | Frontend Team · Mobile Team, critical changes only (DEC-57) |
| Output | `contracts/api-conventions.md` |

**Full text:** PortHub `contracts/api-conventions.md` and PortHub `contracts/error-codes.md`. Those files win over this summary.

- **Base path:** `/api/v1`. All times are ISO 8601 in UTC with microseconds on output.
- **Headers:** web uses the cookie and `X-XSRF-TOKEN`; mobile uses `Authorization: Bearer <token>`, `X-App-Version`, `X-Device-Id` and, on writes, `Idempotency-Key`.
- **Version token:** every editable record returns `version` (the `updated_at` value) and every update sends it back; a stale value returns 409.
- **Errors:** RFC 9457 with a stable `code` and a `message_key` (DEC-57).
- **Pagination:** `?page=&per_page=` with `meta`.

---

## CT-02 · Port API OpenAPI file

| | |
| --- | --- |
| Between | Backend → Frontend · Mobile · QA |
| Owner | Backend Team (single owner, DEC-13) |
| Reviewers | Frontend Team · Mobile Team, critical changes only (DEC-57) |
| Status | Approved v1.0.0 · 2026-10-30 by Marwan (Backend lead), without team review |
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
| Status | Approved v1.0 · 2026-10-31 by Marwan (Backend lead), without team review |
| Output | Auth section of `port-api.yaml` + the flow steps in `contracts/auth-web.md` |

**Flow:**

1. `GET /sanctum/csrf-cookie`
2. `POST /api/v1/auth/login`
3. If `must_change_password = true`: `POST /api/v1/auth/change-password`
4. `POST /api/v1/auth/logout`

Full text: PortHub `contracts/auth-web.md`, which wins over this summary.

The sign-in identifier is `username` (DEC-35, closed); users have no email.

```json
// POST /api/v1/auth/login
{ "username": "staff.ahmed", "password": "••••••••" }

// 200
{
  "id": 41,
  "name": "Port Staff",
  "role": "PORT_STAFF",
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
| Status | Approved v1.0 · 2026-10-30 on Backend Team sign-off (DEC-04). Consolidates the envelope rules already approved in CT-09 to CT-14 and CT-16 |

The envelope is the outer JSON message for every job the Backend sends to an AI worker. Each job type's payload has its own schema (C-01 to C-05); this contract covers everything around it. The completion message going the other way is C-06 (CT-14).

### 1. Transport

- **Format:** one UTF-8 JSON object per Redis list element. No Laravel job classes, no PHP serialisation (DEC-04).
- **Send:** the Backend RPUSHes to an **unprefixed** key (no Laravel Redis prefix). **Receive:** the worker BLPOPs its own queue, so each queue is FIFO.
- **Time:** every timestamp is ISO 8601 in UTC with `Z` (CT-01).

### 2. Queues, job types and workers

| Queue | `job_type` | Worker account | `run_id` refers to | Payload schema | Retries (DEC-04) |
| --- | --- | --- | --- | --- | --- |
| `queue:part1` | `PART1_RUN` | `w_part1` | `part1_runs.id` | `c01-part1-run.schema.json` (CT-09) | Up to `part1_max_retries` (3) |
| `queue:part2` | `PART2_SOLVE` | `w_part2` | `solver_runs.id` | `c02-part2-solve.schema.json` (CT-10) | Once |
| `queue:yard` | `YARD_PLACEMENT` | `w_yard` | `yard_runs.id` | `c03-yard.schema.json` (CT-11) | Once |
| `queue:edi` | `BAPLIE_PARSE` | `w_edi` | `baplie_parse_runs.id` | `c04-baplie.schema.json` (CT-12) | Once |
| `queue:validate` | `VALIDATION` | `w_validate` | — (`run_id = null`) | `c05-validation.schema.json` (CT-13) | Never |
| `queue:ai-results` | — (C-06, worker → Backend) | — | — | `c06-completion.schema.json` (CT-14) | — |

- A worker consumes only its own queue. A `job_type` that does not match the queue it arrived on is `INVALID_ENVELOPE`.
- **Not envelope jobs:** `PART3_EVALUATION` (started by the Part 3 scheduler, DEC-31; it only sends C-06) and the Part 1 scheduled jobs `WEATHER_PULL` · `TIDE_COMPUTE` · `DEMAND_FORECAST` (internal to `w_part1`, reported only in the heartbeat, CT-16).

### 3. Fields

All seven fields are required; no other field is allowed (`additionalProperties: false`).

| Field | Type | Rule |
| --- | --- | --- |
| `contract_version` | string | Message format version, `"1.0"` in v1. Pattern `^1\.[0-9]+$` |
| `job_type` | enum | `PART1_RUN` · `PART2_SOLVE` · `YARD_PLACEMENT` · `BAPLIE_PARSE` · `VALIDATION` |
| `job_id` | string (UUID) | Generated by the Backend, unique per message. Correlation key in C-06; for `VALIDATION` it is the only key. A regeneration is a new run with a new `job_id` |
| `run_id` | integer ≥ 1 \| null | The run row the Backend created as QUEUED (table in §2). `null` only for `VALIDATION`, an integer for every other job type |
| `enqueued_at` | string (date-time, UTC) | Set by the Backend just before RPUSH |
| `triggered_by_user_id` | integer ≥ 1 \| null | The user who started the job, or `null` for an automatic trigger. Required non-null for `VALIDATION`. Per-type rules below |
| `payload` | object | Validated against the job type's payload schema (§2) |

**`triggered_by_user_id` by job type:**

| `job_type` | Value |
| --- | --- |
| `PART1_RUN` | `null` for `CUSTOMS_APPROVAL`; the acting user otherwise (CT-09) |
| `PART2_SOLVE` | `requested_by_user_id` of the MANUAL entry (the last received if several), otherwise `null` (CT-10) |
| `YARD_PLACEMENT` | `null` for the automatic trigger; the user who pressed "Regenerate" otherwise (CT-11) |
| `BAPLIE_PARSE` | `uploaded_by` for `FILE`; the correcting user for `STAGED_PAYLOAD` (CT-12) |
| `VALIDATION` | The officer who proposed the change (CT-13) |

### 4. Versioning

- `contract_version` is the **message** version. It is independent of this document's revision: the v1.1 revisions of CT-09 to CT-16 (plural table names) did not change any message, so messages stay `"1.0"`.
- **Minor (1.x):** additive only: a new optional field, a new enum value, a new `binding_constraints` or `reason_code` code. Workers accept every `1.x`.
- **Major (2.0):** removing or renaming a field or value. Deployed together with the workers; a worker that receives an unsupported major version fails the job with `INVALID_ENVELOPE`.

### 5. Backend sending rules

1. Create the run row as QUEUED (and any other rows the job type's contract requires) and commit, **then** RPUSH. `VALIDATION` has no run row; its proposed change is stored in Redis under the `job_id` first (CT-13).
2. Validate the whole message (envelope + payload) against `envelope.schema.json` before RPUSH. A message that fails is a Backend bug and is never sent.
3. Never re-send a message for a run that is not QUEUED. Retries happen inside the worker (§6), not by re-enqueueing.
4. Per-type limits stay in each payload contract: one `PART2_SOLVE` at a time (CT-10), one active run per terminal recommendation (CT-11), one parse at a time per request (CT-12).

### 6. Worker rules

| Step | What the worker does |
| --- | --- |
| 1 | BLPOP its queue and parse the JSON |
| 2 | Validate against `envelope.schema.json` (envelope + payload). Check that `job_type` matches the queue and the major version is supported |
| 3 | If step 2 fails: when `run_id` (or, for `VALIDATION`, `job_id`) can be read, finish the job as FAILED / `INVALID_ENVELOPE` (claim and complete the run, then send C-06). When it cannot be read, log the raw message and drop it |
| 4 | **Claim:** `UPDATE <run table> SET status = 'RUNNING', started_at = UTC_TIMESTAMP() WHERE id = :run_id AND status = 'QUEUED'`. 0 rows → duplicate or replaced delivery: ignore silently, send nothing. `VALIDATION` has no claim; a duplicate delivery only produces a duplicate C-06, which the Backend de-duplicates by `job_id` (CT-14) |
| 5 | Run the job. Retry inside the worker per §2 for retriable categories (§7), incrementing `retry_count` on the run where that column is granted |
| 6 | Write the result in one transaction whose final run update is guarded by `AND status = 'RUNNING'`. 0 rows → the Backend replaced the run or the sweeper marked it FAILED: roll back everything and send nothing (DEC-08) |
| 7 | After commit, send one C-06 to `queue:ai-results` (CT-14) |

**Stale runs:** a run RUNNING longer than `run_stale_after_seconds` is marked FAILED / `TIMEOUT` by the Backend sweeper (DEC-04). The worker's guarded final update then finds no RUNNING row and rolls back (step 6). The AI Team sets the value as longest run × (`part1_max_retries` + 1) + margin (CT-18).

### 7. Error categories

`INVALID_ENVELOPE` · `PRECONDITION_FAILED` · `DATA_UNAVAILABLE` · `CONFIGURATION_ERROR` · `INFEASIBLE` · `SOLVER_ERROR` · `TIMEOUT` · `INTERNAL_ERROR`

| Category | Meaning | Retried |
| --- | --- | --- |
| `INVALID_ENVELOPE` | Message fails the schema, wrong queue, or unsupported major version | No |
| `PRECONDITION_FAILED` | The rows the job needs are missing or in the wrong state | No |
| `DATA_UNAVAILABLE` | An input source (weather, tide, stored data) cannot be read | Yes |
| `CONFIGURATION_ERROR` | Missing or inconsistent `port_settings`, seed or reference data, or an insert rejected by a CHECK constraint (CT-17) | No |
| `INFEASIBLE` | No valid result exists for the inputs | No |
| `SOLVER_ERROR` | CP-SAT failed | Part 2: no retry, falls back to FIFO (CT-10) |
| `TIMEOUT` | The job hit its time limit | Part 2: no retry, falls back to FIFO (CT-10). Others: yes |
| `INTERNAL_ERROR` | Unexpected worker error | Yes |

**Allowed by job type:**

| `job_type` | Categories |
| --- | --- |
| `PART1_RUN` | All except `INFEASIBLE` and `SOLVER_ERROR` (no feasible window is the DONE outcome `NO_FEASIBLE_WINDOW`) |
| `PART2_SOLVE` | All except `INFEASIBLE` (no plan is the DONE outcome `NO_FEASIBLE_PLAN`) |
| `YARD_PLACEMENT` | All except `SOLVER_ERROR` |
| `BAPLIE_PARSE` | All except `INFEASIBLE` and `SOLVER_ERROR` (unusable files are the DONE outcome `REJECTED`) |
| `VALIDATION` | All except `INFEASIBLE` and `SOLVER_ERROR` (broken constraints are the DONE outcome `VIOLATIONS`) |

### 8. Examples

```json
{
  "contract_version": "1.0",
  "job_type": "PART2_SOLVE",
  "job_id": "a2c9d1f0-1b77-4c2e-8f44-5d6e7f809a1b",
  "run_id": 2301,
  "enqueued_at": "2026-11-02T10:02:11Z",
  "triggered_by_user_id": 41,
  "payload": { "trigger_type": "MANUAL", "triggers": [ { "trigger_type": "MANUAL", "berthing_request_ids": [1548], "requested_by_user_id": 41 } ] }
}
```

```json
{
  "contract_version": "1.0",
  "job_type": "VALIDATION",
  "job_id": "7c1e4b2a-9d3f-4e8a-b6c5-1f2e3d4c5b6a",
  "run_id": null,
  "enqueued_at": "2026-11-02T10:20:00Z",
  "triggered_by_user_id": 41,
  "payload": { "validation_type": "OVERRIDE", "subject_id": 9031, "proposed_change": { "changes": [ { "component_type": "BERTH", "override_berth_id": 14 } ] } }
}
```

### 9. Impact on other contracts

- **CT-10:** its `failure_reason.error_category` list should add `INVALID_ENVELOPE` (minor change, 1.x), since §6 step 3 can fail a Part 2 run that way.
- **CT-15 / DEC-08:** `retry_count` (§6 step 5) is listed as an AI column on `baplie_parse_runs` but not granted to `w_edi`, and is neither listed nor granted for `yard_runs`. Settle the grants in the first `workers.sql`.
- **`part1_runs`** has no `error_category` column, so a failed Part 1 run's category lives only in its C-06.
- **DEC-11 (Redis persistence, Open):** a run committed as QUEUED whose RPUSH was lost stays QUEUED; nothing re-sends it today. The re-queue sweeper proposed in DEC-11 covers this.

---

## CT-09 · C-01 · Part 1 run

| | |
| --- | --- |
| Between | Backend → AI (Part 1) |
| Owner | Backend Team (sending) on the AI Team schema |
| Reviewers | AI Team |
| Output | `contracts/ai/c01-part1-run.schema.json` |
| Status | Approved v1.1 · 2026-10-27 (plural table names, CT-17) · v1.0 2026-10-26 (DEC-14) |

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
  - `part1_runs`: status and outcome (`WINDOWS_FOUND` · `NO_FEASIBLE_WINDOW` · `ENV_DATA_UNAVAILABLE`).
  - `entry_window_proposals`, `feasible_windows` and `blocked_periods`.

---

## CT-10 · C-02 · Part 2 solve

| | |
| --- | --- |
| Between | Backend → AI (Part 2) |
| Owner | Backend Team (sending) on the AI Team schema |
| Reviewers | AI Team |
| Output | `contracts/ai/c02-part2-solve.schema.json` (payload only) |
| Status | Approved v1.1 · 2026-10-27 (plural table names, CT-17) · v1.0 2026-10-26 (DEC-15) |

The schema describes the **payload only**. `envelope.schema.json` (CT-08) references it with `if job_type = PART2_SOLVE then payload: { $ref: c02-part2-solve.schema.json }`. C-01, C-03 and C-04 follow the same pattern.

```json
{
  "contract_version": "1.0",
  "job_type": "PART2_SOLVE",
  "job_id": "b81e…",
  "run_id": 2302,
  "enqueued_at": "2026-11-02T12:20:00Z",
  "triggered_by_user_id": 41,
  "payload": {
    "trigger_type": "REPLAN",
    "triggers": [
      { "trigger_type": "NEW_REQUEST", "berthing_request_ids": [1560, 1561] },
      {
        "trigger_type": "RESOURCE_CHANGE",
        "berthing_request_ids": [1550, 1553],
        "changed_resources": [ { "type": "TUG", "id": 7 }, { "type": "BERTH", "id": 12 } ]
      },
      {
        "trigger_type": "MANUAL",
        "berthing_request_ids": [1548],
        "requested_by_user_id": 41,
        "context_note": "Agent asked to regenerate after cargo update"
      },
      { "trigger_type": "REPLAN", "berthing_request_ids": [1540], "operational_plan_id": 311 }
    ]
  }
}
```

**Trigger entries:**

| `trigger_type` | Sent by the Backend when | `berthing_request_ids` | Extra fields |
| --- | --- | --- | --- |
| `NEW_REQUEST` | Part 1 finishes with `WINDOWS_FOUND` | Requests in `ENTRY_WINDOW_CONFIRMED` or `RECOMMENDATION_GENERATED` | — |
| `MANUAL` | A user presses "Regenerate" | Same as `NEW_REQUEST` | `requested_by_user_id` (required) |
| `RESOURCE_CHANGE` | A berth, tug or pilot becomes unavailable or available again | Pending requests whose current recommendation uses a changed resource, or whose window overlaps the change. The Backend computes this from `recommendation_options` and `recommendation_option_tugs` | `changed_resources` (required, `minItems: 1`) |
| `REPLAN` | A deviation is recorded on a confirmed plan | Exactly one: the request that owns the plan | `operational_plan_id` (required) |

- `changed_resources[].type`: `BERTH` · `TUG` · `PILOT` (closed enum for v1). `id` is `berths.id`, `tugboats.id` or the pilot's `users.id`. A tug master shift change is sent as `TUG` with the tug's id (DEC-32). The worker reads the current resource state from the database, so no "what changed" field is sent.
- `changed_resources` is forbidden outside `RESOURCE_CHANGE`; `operational_plan_id` is forbidden outside `REPLAN`; `requested_by_user_id` is forbidden outside `MANUAL`.
- `context_note`: optional on every entry, `string | null`, `maxLength: 500`. Logs only: not stored in result tables, not used by the solve, never in the rationale.
- `berthing_request_ids` has `minItems: 1` in every entry.
- `purpose` is not sent. The AI derives it per request and writes it to `recommendations.purpose`: `DELAY_REPLAN` for a request in a `REPLAN` entry, `INITIAL` otherwise.

**Backend sending rules:**

- **One solve at a time:** the Backend never enqueues a `PART2_SOLVE` while another is QUEUED or RUNNING. Triggers that arrive meanwhile are held and merged into one message sent when the current solve finishes.
- **`payload.trigger_type`** is the highest-precedence type in `triggers`: `REPLAN > RESOURCE_CHANGE > MANUAL > NEW_REQUEST`. The Backend writes it to `solver_runs.trigger_type`.
- **One entry per request:** a request id appears in at most one entry. If two triggers hit the same request, the higher-precedence entry wins; two `RESOURCE_CHANGE` entries merge their `changed_resources`.
- **No empty solves:** a resource change that affects no pending request is not enqueued.
- **Confirmed plans change only through `REPLAN`:** a resource change that hits a confirmed plan is sent as a `REPLAN` entry for that plan.
- **Envelope `triggered_by_user_id`:** the `requested_by_user_id` of the MANUAL entry if there is one, otherwise `null`. With several MANUAL entries, it is the user of the MANUAL trigger the Backend received last.
- The Backend validates every message against the schema before RPUSH.

**Solve scope (DEC-06, Option 2):** the variable set is the union of `berthing_request_ids` across all entries. Every confirmed plan and every other pending recommendation is fixed and treated as occupied capacity. When the Backend receives C-06, it marks REPLACED only the previous `PENDING_REVIEW` version of each request in the message that got a new recommendation.

**`solver_runs.result_detail` (written by the AI):**

```json
{
  "outcome": "PARTIALLY_SOLVED",
  "failure_reason": null,
  "requests": [
    { "request_id": 1550, "outcome": "SOLVED", "purpose": "INITIAL", "recommendation_id": 880, "options_count": 2, "binding_constraints": [] },
    {
      "request_id": 1553, "outcome": "NO_FEASIBLE_PLAN", "purpose": "INITIAL", "recommendation_id": null, "options_count": 0,
      "binding_constraints": [
        { "kind": "STRUCTURAL", "constraint_type_code": "MAX_LOA", "detail": "No berth in terminal DCT accepts LOA 366 m" }
      ]
    }
  ]
}
```

**Run-level `outcome`** (the same value is sent as `outcome` in C-06):

| `outcome` | `solver_runs.status` | Recommendations written |
| --- | --- | --- |
| `SOLVED` | `OPTIMAL` / `FEASIBLE` | For every request |
| `PARTIALLY_SOLVED` | `OPTIMAL` / `FEASIBLE` | For some requests; the others are `NO_FEASIBLE_PLAN` |
| `NO_FEASIBLE_PLAN` | `INFEASIBLE` | None. Requests stay `ENTRY_WINDOW_CONFIRMED` |
| `FIFO_FALLBACK` | `ERROR` | FIFO plans (`source = FIFO`) for the requests that pass the hard filter. C-06 carries `status = DONE` (plans were written) with the technical reason in `error_category`, while `solver_runs.status` stays `ERROR` (CT-14) |
| `GENERATION_FAILED` | `ERROR` | None |

- **Per-request `outcome`:** `SOLVED` · `FIFO_FALLBACK` · `NO_FEASIBLE_PLAN`.
- **`options_count`:** 1 to 3 when a recommendation is written, otherwise 0 (DEC-23). Options 2 and 3 are returned only within `solver_option_equivalence_pct` of option 1 (CT-18).
- **`binding_constraints`:** non-empty only when the per-request outcome is `NO_FEASIBLE_PLAN`. `detail` is an English diagnostic string, at most 255 characters.
  - `kind = "SAFETY"`: `constraint_type_code` is any `constraint_types.code` from the CT-18 seed (for example `MAX_WIND_KN`).
  - `kind = "STRUCTURAL"`: closed list for v1: `MAX_LOA` · `MAX_DRAFT` · `TERMINAL_COMPATIBILITY` · `BERTH_UNAVAILABLE` · `BERTH_OCCUPIED` · `TUG_UNAVAILABLE` · `PILOT_UNAVAILABLE` · `ENTRY_WINDOW`. Adding a code is a minor version change (1.x).
- **`failure_reason`:** non-null only when `solver_runs.status = ERROR` (`FIFO_FALLBACK` or `GENERATION_FAILED`):

```json
"failure_reason": { "error_category": "TIMEOUT", "message": "CP-SAT reached solver_time_limit_seconds (10) without a feasible solution" }
```

  - `error_category` (CT-08 list): `PRECONDITION_FAILED` · `DATA_UNAVAILABLE` · `CONFIGURATION_ERROR` · `SOLVER_ERROR` · `TIMEOUT` · `INTERNAL_ERROR`. `INFEASIBLE` is never used for Part 2. C-06 carries the same value.
  - `message`: diagnostic text, at most 1,000 characters, never shown to end users.

---

## CT-11 · C-03 · Yard placement

| | |
| --- | --- |
| Between | Backend → AI (yard worker) |
| Owner | Backend Team (sending) on the AI Team schema |
| Reviewers | AI Team |
| Output | `contracts/ai/c03-yard.schema.json` (payload only) |
| Status | Approved v1.1 · 2026-10-27 (plural table names, CT-17) · v1.0 2026-10-27 (DEC-16) |

The schema describes the **payload only**. `envelope.schema.json` (CT-08) references it with `if job_type = YARD_PLACEMENT`. The job runs on its own queue, **`queue:yard`**, served by a separate worker process (own DB account and grants per DEC-08, own heartbeat).

```json
{
  "contract_version": "1.0",
  "job_type": "YARD_PLACEMENT",
  "job_id": "c4d…",
  "run_id": 97,
  "enqueued_at": "2026-11-02T13:00:00Z",
  "triggered_by_user_id": null,
  "payload": { "terminal_recommendation_id": 640, "operational_plan_id": 311 }
}
```

- Both payload fields are required. `run_id` is `yard_runs.id`, not `terminal_recommendation_id`.
- `operational_plan_id` lets the worker check that the plan is still the confirmed plan of that recommendation.

**Backend sending rules:**

- **When:** once both hold: the `operational_plans` is CONFIRMED on a CONTAINER terminal, **and** the request has an ACTIVE `baplie_files` with `parse_status = PARSED`. Whichever happens last triggers the job.
- **One transaction before RPUSH:** set `terminal_recommendations` (`rec_type = YARD_PLACEMENT`, `lifecycle_status = YARD_REC_REQUESTED`) and insert `yard_runs` (QUEUED).
- **`triggered_by_user_id`:** `null` for the automatic trigger; the user who pressed "Regenerate" otherwise.
- **Regenerate:** offered when `lifecycle_status` is `GENERATION_FAILED` or `YARD_REC_REJECTED`. Because of `uq_tr_rec_type`, the same row is reused: reset to `YARD_REC_REQUESTED`, delete the old `yard_placement_items` rows, mark any QUEUED or RUNNING `yard_runs` of that row as `REPLACED`, then insert a new `yard_runs`.
- **Stale recommendation:** after a confirmed REPLAN or a BAPLIE revision becoming ACTIVE, the Backend regenerates automatically if the recommendation is not yet `YARD_REC_ACCEPTED`. If it is accepted, the Backend raises a notification only.
- **Incomplete lines:** the Backend blocks yard recommendations while any line of the ACTIVE file has a NULL `full_empty` **or** a NULL `port_of_discharge`.
- **No one-at-a-time rule:** different terminal recommendations may run in parallel; `uq_yr_active` allows one active run per terminal recommendation.
- The Backend validates every message against the schema before RPUSH.

**`yard_runs` table (added by the Backend through CT-17):**

```sql
CREATE TABLE `yard_runs` (
  `id` bigint PRIMARY KEY AUTO_INCREMENT,
  `terminal_recommendation_id` bigint NOT NULL,
  `triggered_by` bigint NULL,
  `status` ENUM ('QUEUED', 'RUNNING', 'DONE', 'FAILED', 'REPLACED') NOT NULL DEFAULT 'QUEUED',
  `outcome` ENUM ('YARD_REC_GENERATED', 'GENERATION_FAILED') NULL,
  `error_category` ENUM ('INVALID_ENVELOPE', 'PRECONDITION_FAILED', 'DATA_UNAVAILABLE',
                         'CONFIGURATION_ERROR', 'INFEASIBLE', 'TIMEOUT', 'INTERNAL_ERROR') NULL,
  `retry_count` tinyint NOT NULL DEFAULT 0,
  `result_detail` json NULL,
  `worker_version` varchar(40) NULL,
  `queued_at` datetime NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  `started_at` datetime NULL,
  `finished_at` datetime NULL,
  `active_key` bigint GENERATED ALWAYS AS
    (IF(status IN ('QUEUED', 'RUNNING'), terminal_recommendation_id, NULL)) STORED,
  UNIQUE KEY `uq_yr_active` (`active_key`),
  KEY `idx_yr_tr` (`terminal_recommendation_id`),
  CONSTRAINT `fk_yr_tr` FOREIGN KEY (`terminal_recommendation_id`) REFERENCES `terminal_recommendations` (`id`),
  CONSTRAINT `fk_yr_user` FOREIGN KEY (`triggered_by`) REFERENCES `users` (`id`),
  CONSTRAINT `chk_yr_finished` CHECK (status IN ('QUEUED', 'RUNNING', 'REPLACED') OR finished_at IS NOT NULL),
  CONSTRAINT `chk_yr_outcome` CHECK (
       (status = 'DONE'   AND outcome = 'YARD_REC_GENERATED')
    OR (status = 'FAILED' AND outcome = 'GENERATION_FAILED')
    OR (status IN ('QUEUED', 'RUNNING', 'REPLACED') AND outcome IS NULL)),
  CONSTRAINT `chk_yr_error` CHECK ((status = 'FAILED') = (error_category IS NOT NULL))
);
```

**Run flow:**

| Step | Who | What |
| --- | --- | --- |
| 1 | Backend | Sets `YARD_REC_REQUESTED`, inserts `yard_runs` (QUEUED), RPUSH with `run_id = yard_runs.id` |
| 2 | AI | Claims: `UPDATE yard_runs SET status='RUNNING', started_at=… WHERE id=? AND status='QUEUED'`. 0 rows → duplicate or replaced delivery, ignore |
| 3 | AI | One transaction: inserts `yard_placement_items` rows; on `terminal_recommendations` sets `lifecycle_status`, `confidence`, `rationale_template_id`, `rationale_params`, `failure_reason`; sets `yard_runs` to DONE or FAILED. Before commit it re-checks that the run is still RUNNING and the row still `YARD_REC_REQUESTED`; otherwise it rolls back and sends nothing |
| 4 | AI | Sends C-06 with `job_type = YARD_PLACEMENT` and `outcome = YARD_REC_GENERATED` or `GENERATION_FAILED` |

**Worker preconditions (in order):**

| # | Check | If it fails |
| --- | --- | --- |
| 1 | `yard_runs` is QUEUED (claim succeeds) | Ignore silently |
| 2 | `terminal_recommendations` exists, `rec_type = YARD_PLACEMENT`, `lifecycle_status = YARD_REC_REQUESTED` | `PRECONDITION_FAILED` |
| 3 | `operational_plans` exists, `status = CONFIRMED`, and its `recommendation_id` equals `terminal_recommendations.recommendation_id` | `PRECONDITION_FAILED` |
| 4 | Terminal type is `CONTAINER` | `PRECONDITION_FAILED` |
| 5 | The request has an ACTIVE `baplie_files` with `parse_status = PARSED` | `PRECONDITION_FAILED` |
| 6 | No line has a NULL `full_empty` or a NULL `port_of_discharge` | `PRECONDITION_FAILED` |
| 7 | At least one container is in scope | `PRECONDITION_FAILED` |
| 8 | The terminal has a container yard with active slots | `CONFIGURATION_ERROR` |

**Containers in scope:** `container_manifest_entries` rows of the request's ACTIVE `baplie_files` with `port_of_discharge = port_profiles.port_code`. Transshipment and empty containers are included; remain-on-board is excluded; export containers are not in the BAPLIE (DEC-28).

**Result:**

- **Partial placement:** if at least one container is placed, the outcome is `YARD_REC_GENERATED` and unplaced containers get no `yard_placement_items` row. If none can be placed, the outcome is `GENERATION_FAILED` with `INFEASIBLE`.
- **`yard_slot_id`:** always `NULL` in v1 (block level, FR-2.2.3). Nothing the worker writes is a reservation; any capacity check at accept or export time belongs to the Backend.
- **Capacity counting:** active slots with `container_id IS NULL`, minus capacity already given to other recommendations of the same terminal in `YARD_REC_GENERATED` or `YARD_REC_ACCEPTED` (not yet exported). Counted in TEU via `container_size_types.teu_factor`, 1 slot = 1 TEU.
- **`confidence`** = `preferred_zone_count / in_scope_count`, rounded to 3 decimals (DEC-29 Option A). Never null with `YARD_REC_GENERATED`, always null with `GENERATION_FAILED`. Reefer, DG and OOG containers can only go to their zone; general containers may overflow to a special zone and then count as not preferred.

**`yard_runs.result_detail`:**

```json
{
  "in_scope_count": 212,
  "placed_count": 208,
  "preferred_zone_count": 200,
  "unplaced": [
    { "manifest_entry_id": 99812, "reason_code": "NO_REEFER_CAPACITY" },
    { "manifest_entry_id": 99840, "reason_code": "NO_DG_ZONE" }
  ],
  "failure_reason": null
}
```

- **`unplaced[].reason_code`** (closed list for v1): `NO_REEFER_CAPACITY` · `NO_DG_ZONE` · `NO_OOG_ZONE` · `NO_CAPACITY`.
- **`failure_reason`:** `{ "error_category": "...", "message": "..." }`, same shape as C-02, non-null only when the run is FAILED. `terminal_recommendations.failure_reason` holds `"<ERROR_CATEGORY>: <message>"` truncated to 500 characters.
- **`error_category`** for yard: `INVALID_ENVELOPE` · `PRECONDITION_FAILED` · `CONFIGURATION_ERROR` (no container yard, no active slots or no active rationale template) · `DATA_UNAVAILABLE` · `INFEASIBLE` · `TIMEOUT` · `INTERNAL_ERROR`. `SOLVER_ERROR` is not used.

**Impact on other contracts:** CT-08 queue list becomes `queue:part1` · `queue:part2` · `queue:yard` · `queue:edi`. CT-17 adds `yard_runs`. CT-19 maps the mock yard row to `queue:yard`. CT-15 must record that the yard worker writes `lifecycle_status`, `confidence` and `failure_reason` on `terminal_recommendations` (DEC-02).

---

## CT-12 · C-04 · BAPLIE parse

| | |
| --- | --- |
| Between | Backend → AI (EDI parser) |
| Owner | Backend Team (sending) on the AI Team schema |
| Reviewers | AI Team |
| Output | `contracts/ai/c04-baplie.schema.json` (payload only) |
| Status | Approved v1.1 · 2026-10-27 (plural table names, CT-17) · v1.0 2026-10-27 (DEC-17) |

The schema describes the **payload only**, referenced from `envelope.schema.json` with `if job_type = BAPLIE_PARSE`.

```json
{
  "contract_version": "1.0",
  "job_type": "BAPLIE_PARSE",
  "job_id": "d9a…",
  "run_id": 318,
  "enqueued_at": "2026-11-02T08:05:00Z",
  "triggered_by_user_id": 41,
  "payload": { "baplie_file_id": 205, "source": "FILE" }
}
```

| Field | Type | Rule |
| --- | --- | --- |
| `baplie_file_id` | integer ≥ 1 | Required |
| `source` | `FILE` · `STAGED_PAYLOAD` | Required. `FILE` = parse the uploaded file. `STAGED_PAYLOAD` = re-validate and commit the staff-corrected `staged_payload` of a QUARANTINED file |

`additionalProperties: false`. `run_id` is `baplie_parse_runs.id`, not `baplie_file_id`.

**Backend sending rules:**

- **Upload:** the Backend stores the file and its SHA-256, inserts `baplie_files` (`STAGED`, `PENDING`) and `baplie_parse_runs` (QUEUED) in one transaction, then RPUSH. `triggered_by_user_id = uploaded_by`.
- **Upload limits:** max 10 MB; extensions `.edi` · `.txt` · `.baplie`.
- **Duplicate file:** same hash for the same request → 409 at upload (`uq_bf_request_live_hash`).
- **One parse at a time per request:** no new upload while a file of the same request is `PENDING` → 409.
- **Retries:** technical failures are retried once (DEC-04). `REJECTED` and `QUARANTINED` are never retried.
- The Backend validates every message against the schema before RPUSH.

**`baplie_parse_runs` table (added by the Backend through CT-17):**

```sql
CREATE TABLE `baplie_parse_runs` (
  `id` bigint PRIMARY KEY AUTO_INCREMENT,
  `baplie_file_id` bigint NOT NULL,
  `source` ENUM ('FILE', 'STAGED_PAYLOAD') NOT NULL DEFAULT 'FILE',
  `triggered_by` bigint NULL,
  `status` ENUM ('QUEUED', 'RUNNING', 'DONE', 'FAILED', 'REPLACED') NOT NULL DEFAULT 'QUEUED',
  `outcome` ENUM ('PARSED', 'QUARANTINED', 'REJECTED') NULL,
  `error_category` ENUM ('INVALID_ENVELOPE', 'PRECONDITION_FAILED', 'DATA_UNAVAILABLE',
                         'CONFIGURATION_ERROR', 'TIMEOUT', 'INTERNAL_ERROR') NULL,
  `retry_count` tinyint NOT NULL DEFAULT 0,
  `container_count` int NULL,
  `result_detail` json NULL,
  `worker_version` varchar(40) NULL,
  `queued_at` datetime NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  `started_at` datetime NULL,
  `finished_at` datetime NULL,
  `active_key` bigint GENERATED ALWAYS AS
    (IF(status IN ('QUEUED', 'RUNNING'), baplie_file_id, NULL)) STORED,
  UNIQUE KEY `uq_bpr_active` (`active_key`),
  KEY `idx_bpr_file` (`baplie_file_id`),
  CONSTRAINT `fk_bpr_file` FOREIGN KEY (`baplie_file_id`) REFERENCES `baplie_files` (`id`),
  CONSTRAINT `fk_bpr_user` FOREIGN KEY (`triggered_by`) REFERENCES `users` (`id`),
  CONSTRAINT `chk_bpr_finished` CHECK (status IN ('QUEUED', 'RUNNING', 'REPLACED') OR finished_at IS NOT NULL),
  CONSTRAINT `chk_bpr_outcome` CHECK (
       (status = 'DONE' AND outcome IS NOT NULL)
    OR (status <> 'DONE' AND outcome IS NULL)),
  CONSTRAINT `chk_bpr_error` CHECK ((status = 'FAILED') = (error_category IS NOT NULL))
);
```

**Run flow:**

| Step | Who | What |
| --- | --- | --- |
| 1 | Backend | Inserts `baplie_parse_runs` (QUEUED) and RPUSH, in one transaction with the upload or the correction save |
| 2 | AI | Claims: `UPDATE … SET status='RUNNING' WHERE id=? AND status='QUEUED'`. 0 rows → ignore |
| 3 | AI | One all-or-nothing transaction: data rows, `baplie_parse_issues` rows, `baplie_files.parse_status` (and `staged_payload` when QUARANTINED). The final run update is guarded by `AND status = 'RUNNING'`; 0 rows → roll back everything and send nothing |
| 4 | AI | Sends C-06 with `job_type = BAPLIE_PARSE` and the outcome |
| 5 | Backend | On `PARSED`, in one transaction: new file → `ACTIVE`, previous ACTIVE → `REPLACED`. On anything else the file stays `STAGED` and the previous ACTIVE file stays ACTIVE |

The worker never writes `baplie_files.status` (DEC-08). Between step 3 and step 5 the file is PARSED but still STAGED; Part 1 and yard read only the ACTIVE file.

**Outcomes:**

| Run result | `parse_status` | Meaning | What the user does |
| --- | --- | --- | --- |
| DONE · `PARSED` | `PARSED` | Data committed. May carry `WARNING` issues | Nothing, or fix incomplete lines |
| DONE · `QUARANTINED` | `QUARANTINED` | Readable BAPLIE with at least one `ERROR` issue. Nothing committed; extracted data in `staged_payload` | Correct on the quarantine screen |
| DONE · `REJECTED` | `FAILED` | Not a usable BAPLIE: not UN/EDIFACT, not a BAPLIE message, unsupported version, or corrupted | Upload a new file |
| FAILED · `error_category` | `FAILED` | Technical error. Retried once (DEC-04) | Retry, or contact support |

- **ERROR issues (→ QUARANTINED):** IMO in the file ≠ `vessels.imo_number` of the request · duplicate container number in the file · unknown ISO size type · unknown `imdg_class` · malformed value (weight, UN/LOCODE, temperature outside −40 … 40) · reefer without set temperature.
- **WARNING issues (→ still PARSED):** wrong container check digit · missing `full_empty` (written NULL) · missing `port_of_discharge` (written NULL) · vessel name differs from `vessels.name` · existing container with a different size type.
- The Backend blocks customs approval and yard recommendations while any line has a NULL `full_empty` or a NULL `port_of_discharge`.
- **Supported BAPLIE versions (v1.0):**

  | SMDG BAPLIE | UN/EDIFACT directory | `UNH` message identifier |
  | --- | --- | --- |
  | 2.2.1 (VGM) | D.95B | `BAPLIE:D:95B:UN:SMDG22` |
  | 3.1.1 (VGM) | D.13B | `BAPLIE:D:13B:UN:SMDG31` |

  The version is detected from the `UNH` segment (type, version, release, agency). The association code is read but not required to match: 2.x files of the D.95B family (2.1, 2.1.1, 2.2) are parsed with the 2.2.1 rules. Any other directory (for example BAPLIE 1.5), a version still in development (2.3, 3.2), a different message type or a non-EDIFACT file → `REJECTED` with one ERROR issue: `segment_ref = "UNH"`, `message = "Unsupported BAPLIE version: <found>. Supported: SMDG 2.2.1 (D.95B), SMDG 3.1.1 (D.13B)"`. Adding a version is a minor change (1.x).
  - Schema description text: *The EDI Parser accepts SMDG BAPLIE 2.2.1 (UN/EDIFACT D.95B) and SMDG BAPLIE 3.1.1 (UN/EDIFACT D.13B), detected from the UNH message identifier. Any other version, message type or non-EDIFACT file ends as outcome REJECTED (parse_status FAILED) with an ERROR issue on segment UNH.*

**Where failure reasons live:** parse problems (including `REJECTED` reasons) → `baplie_parse_issues` rows. Technical failures → `baplie_parse_runs.error_category` and `result_detail.failure_reason = { "error_category", "message" }`, same shape as C-02 and C-03. No column is added to `baplie_files`.

```json
{
  "container_count": 1840,
  "discharged_here_count": 612,
  "issue_counts": { "ERROR": 0, "WARNING": 3 },
  "vessel_fields_filled": ["call_sign"],
  "parse_time_ms": 4210,
  "failure_reason": null
}
```

**Quarantine and correction:**

`staged_payload` (written by the worker, edited on the quarantine screen):

```json
{
  "format_version": "1.0",
  "vessel": { "imo_number": "9811000", "name": "MSC EXAMPLE", "call_sign": "3FAB7" },
  "lines": [
    {
      "line_no": 1,
      "segment_ref": "LOC+147+0010282",
      "container_number": "MSCU1234565",
      "iso_size_type": "45G1",
      "full_empty": "FULL",
      "weight_kg": 24500,
      "imdg_class": null,
      "oog": { "front_cm": null, "back_cm": null, "right_cm": null, "left_cm": null, "height_cm": null },
      "reefer_set_temperature": null,
      "stowage": { "bay": 1, "row": 2, "tier": 82 },
      "port_of_load": "CNSHA",
      "port_of_discharge": "EGDAM",
      "issues": [ { "severity": "ERROR", "code": "UNKNOWN_SIZE_TYPE", "message": "Size type 45X9 not found" } ]
    }
  ]
}
```

1. Staff edit lines. The Backend saves the edited `staged_payload` and sets `is_manually_corrected`, `corrected_by`, `corrected_at` (audited).
2. The Backend enqueues a new run with `source = STAGED_PAYLOAD`.
3. The worker re-validates `staged_payload` with the same rules. Still has ERROR issues → QUARANTINED again with refreshed issues. Clean → commits exactly like a PARSED file.

All commit logic for `containers` / `container_manifest_entries` / `vessels` stays in the worker; the Backend never writes those rows from a BAPLIE. `staged_payload` is shown only to the owning agent and the terminal (§42 isolation).

**`containers` rows:** upsert by `container_number` (uppercase, no spaces). New number → insert with `size_type_id`. Existing number → no update; a different size type keeps the stored value and adds a WARNING.

**`vessels` rows:** the worker fills only NULL `call_sign` and `flag_state`; it never overwrites a value. `imo_number` mismatch → ERROR; `name` mismatch → WARNING. Filled columns are listed in `result_detail.vessel_fields_filled`.

**Performance:** no size classes in this contract. NFR-PERF-2 is removed from the MVP (Leads Council, 2026-10-27).

**Impact on other contracts:** CT-17 adds `baplie_parse_runs`. CT-13 / DEC-03: BAPLIE correction validation runs on the worker through `source = STAGED_PAYLOAD`. CT-14: C-06 for BAPLIE carries `outcome` = `PARSED` · `QUARANTINED` · `REJECTED`, or `error_category` on a FAILED run.

---

## CT-13 · C-05 · Validation (`queue:validate`)

| | |
| --- | --- |
| Between | Backend → AI (`w_validate`) → Backend |
| Owner | AI Team |
| Reviewers | Backend Team |
| Output | `contracts/ai/c05-validation.schema.json` (payload only) |
| Status | Approved v1.1 · 2026-10-27 (plural table names, CT-17) · v1.0 2026-10-27 (DEC-03 · DEC-18) |

FastAPI is cancelled (DEC-10), so validation is an async job. A result with violations is a **warning**: the officer can still confirm with a reason (DEC-03).

| Validation | Where |
| --- | --- |
| `OVERRIDE` (berth, pilot, tug, start time) | `queue:validate` → `w_validate` (this contract) |
| `YARD_ADJUSTMENT` | `queue:validate` → `w_validate` (this contract) |
| BAPLIE correction | `queue:edi` → `w_edi`, a `BAPLIE_PARSE` job with `source = STAGED_PAYLOAD` (CT-12) |
| Window re-check on confirm | Laravel (DEC-03) |

**Flow:**

| Step | Who | What |
| --- | --- | --- |
| 1 | Backend | Stores the proposed change under a new `job_id` in Redis (TTL `validation_result_ttl_seconds`), RPUSHes a `VALIDATION` job and answers **202** with the `job_id` |
| 2 | AI | `w_validate` reads port state from the primary and checks the change. It writes **nothing** to the DB |
| 3 | AI | Sends C-06 with `job_type = VALIDATION`, the same `job_id` and `validation_result` |
| 4 | Backend | Matches C-06 by `job_id`, keeps the result for `validation_result_ttl_seconds`, sends an SSE event to that officer |
| 5 | Officer | `VALID` → confirms. `VIOLATIONS` → sees each broken constraint and may still confirm with a reason |
| 6 | Backend | Applies the override only if the result exists, has not expired, and was produced for the **same proposed change** and the **same recommendation version**. An override with violations is audited with `action = SAFETY_EXCEPTION` |

- **Fail closed:** no result within `validation_timeout_seconds` (15) → "validation unavailable" and the change is refused. A missing check is not a checked warning.
- **Recommendation version (Backend):** `recommendations` has no version column, so the Backend stores with the job the recommendation `status` and the latest `recommendation_overrides.id` of that option; the result is valid only if both are unchanged at confirm time.

**Envelope:** `job_type = VALIDATION`, `run_id = null` (no run table; `job_id` is the correlation key), `triggered_by_user_id` = the officer, never retried (the Backend timeout covers a lost job).

```json
{
  "contract_version": "1.0",
  "job_type": "VALIDATION",
  "job_id": "7c1e4b2a-9d3f-4e8a-b6c5-1f2e3d4c5b6a",
  "run_id": null,
  "enqueued_at": "2026-11-02T10:20:00Z",
  "triggered_by_user_id": 41,
  "payload": {
    "validation_type": "OVERRIDE",
    "subject_id": 9031,
    "proposed_change": {
      "changes": [
        { "component_type": "BERTH", "override_berth_id": 14 },
        { "component_type": "TUG", "original_tugboat_id": 7, "override_tugboat_id": 11 }
      ]
    }
  }
}
```

```json
{
  "validation_type": "YARD_ADJUSTMENT",
  "subject_id": 640,
  "proposed_change": { "placements": [ { "manifest_entry_id": 99812, "yard_block_id": 31, "yard_slot_id": null } ] }
}
```

**Payload rules** (full schema in `c05-validation.schema.json`):

- `subject_id` = `recommendation_options.id` for `OVERRIDE`, `terminal_recommendations.id` for `YARD_ADJUSTMENT`.
- `OVERRIDE.changes`: 1 to 8 items, validated together as one plan. Items: `BERTH` (`override_berth_id`) · `PILOT` (`override_pilot_user_id`) · `TUG` (`original_tugboat_id`, `override_tugboat_id`; null original = added, null override = removed, never both null) · `START_TIME` (`override_start`).
- `YARD_ADJUSTMENT.placements`: only the changed containers, each with `manifest_entry_id`, `yard_block_id`, `yard_slot_id` (nullable).
- **Checked by the Backend before RPUSH** (the worker returns `INVALID_ENVELOPE` otherwise): at most one `BERTH`, one `PILOT` and one `START_TIME` item; a `manifest_entry_id` appears at most once.

**Preconditions** (C-06 `FAILED` / `PRECONDITION_FAILED`):

| `validation_type` | Check |
| --- | --- |
| `OVERRIDE` | `recommendation_options` exists and its recommendation is `PENDING_REVIEW` or `MODIFIED_BY_STAFF` |
| `YARD_ADJUSTMENT` | `terminal_recommendations` exists, `rec_type = YARD_PLACEMENT`, `lifecycle_status` is `YARD_REC_GENERATED` or `YARD_REC_ACCEPTED`; every `manifest_entry_id` belongs to the ACTIVE BAPLIE of that request; every block belongs to the terminal's yard |

**Result** (`validation_result` in C-06, defined in `c06-completion.schema.json`):

```json
{
  "validation_type": "OVERRIDE",
  "subject_id": 9031,
  "valid": false,
  "violations": [
    { "kind": "STRUCTURAL", "constraint_type_code": "MAX_DRAFT", "is_hard_safety_limit": false,
      "message_key": "validation.berth.draft_exceeded", "detail": "Arrival draft 14.2 m exceeds berth B14 depth 13.5 m",
      "change_index": 0, "manifest_entry_id": null },
    { "kind": "SAFETY", "constraint_type_code": "MIN_UKC_M", "is_hard_safety_limit": true,
      "message_key": "validation.ukc.below_minimum", "detail": "UKC 0.4 m at berth B14 on 2026-11-03 06:00 is below the minimum 0.8 m",
      "change_index": null, "manifest_entry_id": null }
  ]
}
```

- `kind = SAFETY`: `constraint_type_code` from the CT-18 seed; `is_hard_safety_limit` copied from that row. `kind = STRUCTURAL`: codes below; `is_hard_safety_limit` always `false`.
- `change_index`: index in `changes` (`null` when the problem comes from the combination). `manifest_entry_id`: the container concerned (yard).
- At most 500 violations; `violations_truncated = true` if there were more. `message_key` ≤ 120, `detail` ≤ 255 characters.
- **STRUCTURAL codes, `OVERRIDE`:** `MAX_LOA` · `MAX_DRAFT` · `TERMINAL_COMPATIBILITY` · `BERTH_UNAVAILABLE` · `BERTH_OCCUPIED` · `TUG_UNAVAILABLE` · `TUG_COUNT` (DEC-20) · `PILOT_UNAVAILABLE` (DEC-32) · `PILOT_RANK_LIMIT` · `ENTRY_WINDOW`.
- **STRUCTURAL codes, `YARD_ADJUSTMENT`:** `YARD_REEFER_PLUG` · `YARD_DG_CLASS` · `YARD_OOG_LIMIT` · `YARD_BLOCK_CAPACITY` (CT-11 counting rule) · `YARD_SLOT_OCCUPIED` · `YARD_SLOT_BLOCKED`.

**New `port_settings` keys (CT-18):** `validation_timeout_seconds` = 15 · `validation_result_ttl_seconds` = 600.

---

## CT-14 · C-06 · Completion message (`queue:ai-results`)

| | |
| --- | --- |
| Between | AI → Backend |
| Owner | AI Team (message shape, DEC-19) · Backend Team (delivery and handling, DEC-01) |
| Reviewers | Backend Team · AI Team |
| Output | `contracts/ai/c06-completion.schema.json` |
| Status | Approved v1.1 · 2026-10-27 (plural table names, CT-17) · v1.0 2026-10-27 (DEC-01 · DEC-19) |

**Delivery (worker side):**

- The worker RPUSHes to `queue:ai-results` (no Redis prefix, DEC-04) **after** its result transaction has committed. One message per run, after the last retry.
- A run that lost its final conditional update (REPLACED while running) rolls back and sends nothing (DEC-08).
- Delivery is at-least-once; the Backend de-duplicates.

**Handling (Backend side, DEC-01):**

- A supervised consumer, `php artisan ai:consume-results`, reads with BLPOP. Target: SSE and notifications within 5 s of the commit.
- **Poller safety net** every 30 s: runs that are DONE or FAILED with `result_handled_at IS NULL`, and `drift_measurements` rows with `is_drifted = 1` and `notified_at IS NULL`, are handled as if C-06 had arrived. `VALIDATION` has no poller; its timeout covers a lost message.
- **De-duplication:** run jobs are claimed with `UPDATE <run> SET result_handled_at = NOW() WHERE id = ? AND result_handled_at IS NULL` (0 rows → ignore). `VALIDATION` and `PART3_EVALUATION` are de-duplicated with a Redis key on `job_id`. `result_handled_at` and `drift_measurements.notified_at` are Backend-only columns (CT-17).
- On receipt the Backend performs the request transition, the audit entry, the notification and the SSE event, then closes old rows (REPLACED, ACTIVE) as agreed in DEC-08.
- **Stale runs:** the Backend sweeper marks a run RUNNING longer than `run_stale_after_seconds` as FAILED / `TIMEOUT` and handles it like a FAILED C-06.

**Fields by `job_type`:**

| `job_type` | `run_id` | `status = DONE` → `outcome` | `status = FAILED` → `outcome` | Extra field |
| --- | --- | --- | --- | --- |
| `PART1_RUN` | `part1_runs.id` | `WINDOWS_FOUND` · `NO_FEASIBLE_WINDOW` · `ENV_DATA_UNAVAILABLE` | `null` | `entry_window_proposal_id`: integer with `WINDOWS_FOUND` (and with `NO_FEASIBLE_WINDOW` if DEC-07 = Option 1), otherwise `null` |
| `PART2_SOLVE` | `solver_runs.id` | `SOLVED` · `PARTIALLY_SOLVED` · `NO_FEASIBLE_PLAN` · `FIFO_FALLBACK` | `GENERATION_FAILED` | Per-request detail in `solver_runs.result_detail` (CT-10) |
| `YARD_PLACEMENT` | `yard_runs.id` | `YARD_REC_GENERATED` | `GENERATION_FAILED` | `terminal_recommendation_id` |
| `BAPLIE_PARSE` | `baplie_parse_runs.id` | `PARSED` · `QUARANTINED` · `REJECTED` | `null` | `baplie_file_id` |
| `VALIDATION` | `null` | `VALID` · `VIOLATIONS` | `null` | `validation_result` (DONE only) |
| `PART3_EVALUATION` | `null` | `EVALUATED` · `DRIFT_DETECTED` | `null` | `drift_measurement_ids` (at least 1 with `DRIFT_DETECTED`) |

**`error_category`:** `null` with DONE, except `FIFO_FALLBACK`, which carries the technical reason (`SOLVER_ERROR` · `TIMEOUT` · `INTERNAL_ERROR`). Required with FAILED. `INFEASIBLE` is used only by `YARD_PLACEMENT`.

```json
{ "contract_version": "1.0", "job_type": "PART1_RUN", "job_id": "3f6b2c1e-8a1d-4a51-9f1e-2b0c7d9e4a10", "run_id": 812,
  "status": "DONE", "outcome": "WINDOWS_FOUND", "error_category": null, "entry_window_proposal_id": 455,
  "finished_at": "2026-11-02T09:15:41Z", "worker_version": "0.6.0" }
```

```json
{ "contract_version": "1.0", "job_type": "PART2_SOLVE", "job_id": "b81e0c2d-4f5a-4b6c-8d7e-9f0a1b2c3d4e", "run_id": 2302,
  "status": "DONE", "outcome": "FIFO_FALLBACK", "error_category": "TIMEOUT",
  "finished_at": "2026-11-02T12:20:13Z", "worker_version": "0.6.0" }
```

```json
{ "contract_version": "1.0", "job_type": "PART3_EVALUATION", "job_id": "5e4d3c2b-1a09-4f8e-9d7c-6b5a4f3e2d1c", "run_id": null,
  "status": "DONE", "outcome": "DRIFT_DETECTED", "error_category": null, "drift_measurement_ids": [41, 42],
  "finished_at": "2026-11-03T02:00:31Z", "worker_version": "0.6.0" }
```

- `job_id` is the envelope `job_id`; for `PART3_EVALUATION` (no envelope) the worker generates it.
- Every field outside a job type's row is forbidden for that job type (see the schema).

**What the Backend does on receipt:**

| `job_type` | Backend actions |
| --- | --- |
| `PART1_RUN` | Previous `entry_window_proposals` → REPLACED · request transition · audit · SSE `ENTRY_WINDOW_READY` or `RUN_FAILED` · notification |
| `PART2_SOLVE` | Previous PENDING_REVIEW recommendation of each solved request → REPLACED · request transitions · audit · SSE `RECOMMENDATION_READY` · sends the held triggers as the next solve (CT-10) |
| `YARD_PLACEMENT` | Audit · SSE `YARD_RECOMMENDATION_READY` / `YARD_RECOMMENDATION_FAILED` |
| `BAPLIE_PARSE` | On PARSED: new file ACTIVE, previous REPLACED · stale yard regeneration (CT-11) · audit · SSE `BAPLIE_PARSED` |
| `VALIDATION` | Stores the result for `validation_result_ttl_seconds` · SSE to the officer |
| `PART3_EVALUATION` | On DRIFT_DETECTED: SSE `DRIFT_ALERT` · notification · sets `drift_measurements.notified_at` |

---

## CT-15 · AI result tables and write ownership

| | |
| --- | --- |
| Between | AI ↔ Backend |
| Owner | AI Team (document) · Backend Team (DEC-02) |
| Reviewers | Backend Team |
| Output | `contracts/ai/table-ownership.md` |
| Status | Approved v1.1 · 2026-10-27 (plural table names, CT-17) · v1.0 2026-10-27 (DEC-02 · DEC-08) |

**Rules:**

- The worker inserts new rows and completes **only its own run**; every final run update is conditional on `status = 'RUNNING'`.
- The Backend creates runs and closes old rows (REPLACED, ACTIVE, CONFIRMED, REJECTED), and writes every request transition, history row and audit entry.
- No worker deletes anything. `VALIDATION` writes nothing (`w_validate` has SELECT only).

| Table | Created by | Completed / changed by | AI columns (UPDATE) |
| --- | --- | --- | --- |
| `part1_runs` | Backend (QUEUED) | AI: its own run. Backend: old run → REPLACED when it sends a new one | `status`, `outcome`, `retry_count`, `entry_window_proposal_id`, `started_at`, `finished_at` |
| `entry_window_proposals` | AI (PROPOSED) | Backend: CONFIRMED, REJECTED, REPLACED (on C-06) and the confirm / reject columns | — |
| `feasible_windows` · `blocked_periods` | AI | — | — |
| `forecast_runs` · `environment_forecast_points` | AI (SCHEDULED, ON_DEMAND; a failed pull inserts a FAILED run) · Backend (MANUAL) | — | — |
| `tide_prediction_runs` · `tide_prediction_points` · `demand_forecast_slots` | AI | — | — |
| `solver_runs` | Backend (QUEUED, `solver_version` from `port_settings`) | AI: its own run | `status`, `objective_value`, `solve_time_ms`, `solver_version`, `result_detail`, `started_at`, `finished_at` |
| `solver_run_model_versions` | AI | — | — |
| `recommendations` · `recommendation_options` · `recommendation_option_tugs` · `recommendation_rationale_factors` | AI | Backend: REPLACED, CONFIRMED, MODIFIED_BY_STAFF | — |
| `terminal_recommendations` (YARD_PLACEMENT) | Backend (YARD_REC_REQUESTED; reset on regeneration) | AI: generation result. Backend: decision, accept or reject, export | `lifecycle_status` (GENERATED / GENERATION_FAILED only), `confidence`, `rationale_template_id`, `rationale_params`, `failure_reason` |
| `yard_runs` | Backend (QUEUED; old run → REPLACED) | AI: its own run | `status`, `outcome`, `error_category`, `result_detail`, `worker_version`, `started_at`, `finished_at` |
| `yard_placement_items` | AI | Backend: deletes old items on regeneration | — |
| `baplie_files` | Backend (STAGED, PENDING) | AI: parse result. Backend: ACTIVE / REPLACED / WITHDRAWN, correction columns, edits `staged_payload` on correction | `parse_status`, `staged_payload` |
| `baplie_parse_runs` | Backend (QUEUED; old run → REPLACED) | AI: its own run | `status`, `outcome`, `error_category`, `retry_count`, `container_count`, `result_detail`, `worker_version`, `started_at`, `finished_at` |
| `baplie_parse_issues` · `containers` · `container_manifest_entries` | AI | — | — |
| `vessels` | Backend | AI: fills NULL columns only | `call_sign`, `flag_state` |
| `evaluation_metrics` · `drift_measurements` | AI (`w_part3`) | Backend: `drift_measurements.notified_at` | — |
| `result_handled_at` (all run tables) | — | Backend only | — |
| `terminal_recommendations` (TIMING / STORAGE_ALLOCATION) · `storage_allocation_items` | Nobody (DEC-55, future work) | — | — |
| `berthing_requests` (+ history) · `operational_plans` · `plan_components` · `recommendation_overrides` · `audit_logs` · `notification_logs` | Backend only | — | — |

---

## CT-16 · Worker health over Redis (replaces the FastAPI internal API)

| | |
| --- | --- |
| Between | AI → Backend |
| Owner | AI Team |
| Reviewers | Backend Team |
| Output | `contracts/ai/worker-heartbeat.schema.json` |
| Status | Approved v1.1 · 2026-10-27 (plural table names, CT-17) · v1.0 2026-10-27 (DEC-10) |

FastAPI is cancelled (DEC-10):

| Old endpoint | Replacement |
| --- | --- |
| `GET /internal/v1/health` | Heartbeat keys below |
| `GET /internal/v1/workers` | Heartbeat keys + `LLEN` of each queue (read by the Backend) |
| `GET /internal/v1/runs/{job_type}/{run_id}` | The Backend reads the run tables directly |
| `POST /internal/v1/validate` | CT-13 (`queue:validate`) |

**Heartbeat rules:**

- **Key:** `worker:{name}:heartbeat`, `name` = `part1` · `part2` · `yard` · `edi` · `validate` · `part3`. Written every 15 s with `SET … EX 60`.
- **DOWN:** key missing. **Stale:** `last_heartbeat` older than 45 s (warning). **DEGRADED:** running but a dependency fails (reason in `status_detail`). **DRAINING:** finishing the current job, taking no new ones (deploys).
- **Backend:** the admin worker-status page reads the keys and `LLEN` of each queue; an alert is raised when a worker is DOWN for more than 2 minutes.

```json
{
  "contract_version": "1.0",
  "name": "part1",
  "status": "UP",
  "status_detail": null,
  "version": "0.6.0",
  "host": "port-ai-01",
  "started_at": "2026-11-02T06:00:00Z",
  "last_heartbeat": "2026-11-02T10:05:00Z",
  "current_job": { "job_type": "PART1_RUN", "job_id": "3f6b2c1e-8a1d-4a51-9f1e-2b0c7d9e4a10", "run_id": 812, "started_at": "2026-11-02T10:04:58Z" },
  "processed_total": 120,
  "failed_total": 1,
  "schedules": { "last_weather_pull_at": "2026-11-02T06:00:12Z", "last_tide_compute_at": "2026-11-02T00:00:40Z", "last_demand_forecast_at": "2026-11-02T06:01:03Z" }
}
```

`current_job.job_type` also covers the scheduled jobs `WEATHER_PULL` · `TIDE_COMPUTE` · `DEMAND_FORECAST`. `schedules` is sent by `part1` and `part3` only.

---

## CT-17 · Database schema (migrations)

| | |
| --- | --- |
| Between | Backend → AI |
| Owner | Backend Team (single owner of migrations) |
| Reviewers | AI Team |
| Output | Migrations in `project-backend` · generated `contracts/db/schema.sql` · `contracts/db/table-names.md` |
| Status | Approved v1.0 · 2026-10-27 |

**1. Source of truth.** Until the first migration: `PortSync.sql` (DB Edit Sheet applied) + `PortSync_base_ddl_fixes.sql` + Report A + Report B + FCM SQL changes + the additions in point 7. From the first migration PR: the Laravel migrations in `project-backend`. `contracts/db/schema.sql` is always generated; nobody edits it by hand (a mismatch found by the AI Team is raised as `ai-request`).

**2. Physical conventions.**

| Topic | Rule |
| --- | --- |
| Engine | MySQL 8.4, InnoDB, `utf8mb4` / `utf8mb4_0900_ai_ci` |
| Table names | **Plural, Laravel convention**; models singular. Full list of the 92 tables in `contracts/db/table-names.md` (generated with `Str::plural`) |
| Column names | Unchanged. Foreign keys stay singular (`vessel_id`, `solver_run_id`, …). Constraint and index names unchanged |
| Ids | `BIGINT UNSIGNED` (`id()` / `foreignId()`). Workers map them with `mysql.BIGINT(unsigned=True)`; JSON schemas keep `integer` |
| Statuses | MySQL `ENUM` with the exact SQL names, 1:1 with PHP enums. Adding a value = minor version; removing or renaming one = major (2.0) |
| CHECK constraints and generated columns | Created with the table, named as in `PortSync_base_ddl_fixes.sql`. Workers never write generated columns. A worker insert rejected by a CHECK ends the run as FAILED with a suitable `error_category`, without retry |
| Time | Every `datetime` is UTC. Laravel and every worker connection set `time_zone = '+00:00'` (workers: `init_command` on the pool) |
| Deletes | No `ON DELETE CASCADE` on tables a worker writes; the Backend deletes explicitly |

**3. Laravel framework tables** (`cache`, `jobs`, `failed_jobs`, `sessions`, `personal_access_tokens`, `password_reset_tokens`, `migrations`) are Backend-only; no worker grants. Laravel's default `users` migration is replaced by the port `users` table.

**4. Migration layout.** One migration per table, ordered by module so foreign keys point to earlier tables. `…_create_<table>_table.php` / `…_alter_<table>_<change>.php`. After the first release, a `down()` must not drop **or rename** a column or table a worker uses.

**5. `contracts/db/schema.sql`.** Generated by `composer contracts:schema` (migrations on an empty DB, then `mysqldump --no-data --skip-comments --skip-dump-date`, which keeps CHECK constraints and generated columns, plus the grants script). Header: last migration name and contract version. Each change = a migration PR in `project-backend`, then a PortHub PR updating `schema.sql` and the submodule pointer.

**6. Change process.**

| Who | What |
| --- | --- |
| AI Team | Opens an `ai-request` issue in `project-backend` (table, column, reason, contract) |
| Backend | Writes the migration. A PR touching a table any worker **reads or writes** (including a new ENUM value on a table a worker only reads) carries `ai-impact` and needs one AI Team approval (target: one working day) |
| Backend | Updates `database/grants/workers.sql` in the same PR when a worker's tables or columns change (DEC-08) |
| Both | Additive change = minor (1.x); remove or rename = major (2.0), deployed together |

Workers treat an unknown ENUM value they read as a warning and skip the row; they never crash on it. The AI test database is built from `schema.sql` + the CT-18 seed; integration tests use the Backend's `docker compose`.

**7. First migration batch (additions to `PortSync`).**

| Change | From |
| --- | --- |
| New table `yard_runs` | CT-11 |
| New table `baplie_parse_runs` | CT-12 |
| `result_handled_at DATETIME NULL` on `part1_runs`, `solver_runs`, `yard_runs`, `baplie_parse_runs` (Backend-only, no worker UPDATE grant) | CT-14 / DEC-01 |
| `notified_at DATETIME NULL` on `drift_measurements` (Backend-only, no worker UPDATE grant) | CT-14 / DEC-01 |
| `rationale_params JSON NULL` on `recommendation_options` and `terminal_recommendations` (placeholder values written by the worker; the Backend renders the text) | CT-18 |
| Worker accounts and `database/grants/workers.sql` (6 accounts). New column grants: `w_part2` writes `rationale_params` through its existing INSERT on `recommendation_options`; `w_yard` gets UPDATE on `terminal_recommendations.rationale_params` | DEC-08 |
| `part1_runs.entry_window_proposal_id` comment → "set whenever a proposal is inserted" | Only if DEC-07 closes with Option 1 |

**8. Lock order for yard regeneration (with CT-11).** Both sides lock in the same order: `terminal_recommendations` row → `yard_runs` row → `yard_placement_items`.

- **Worker:** the result transaction starts with `SELECT … FROM terminal_recommendations … FOR UPDATE` and `SELECT … FROM yard_runs WHERE id = :run_id AND status = 'RUNNING' FOR UPDATE`; no row → roll back and send nothing. Then it inserts items and completes the run.
- **Backend:** in one transaction, locks the `terminal_recommendations` row, marks any QUEUED or RUNNING run REPLACED, deletes the old `yard_placement_items`, resets the row to `YARD_REC_REQUESTED`, inserts the new `yard_runs` row.
- **Late C-06:** the Backend ignores a C-06 whose `run_id` is not the latest run of that terminal recommendation.

---

## CT-18 · AI seed data and `port_settings` keys

| | |
| --- | --- |
| Between | AI → Backend |
| Owner | AI Team (`seed-spec.json`) · Backend Team (`reference-seed.json`, seeders) |
| Reviewers | Backend Team · AI Team (codes it depends on) |
| Output | `contracts/ai/seed-spec.json` · `contracts/db/reference-seed.json` |
| Status | Approved v1.0 · 2026-10-27 (DEC-12 · DEC-23). Values marked ⟨AI⟩ arrive with the `seed-spec.json` PR |

**1. Scope.**

| Data | Content owner | File |
| --- | --- | --- |
| `constraint_types` · `safety_constraints` (port-wide defaults from DEC-30 / CT-25) · `objective_terms` · `rationale_templates` · `ml_models` · `ml_model_versions` (initial CHAMPIONs) · AI `port_settings` keys | AI Team | `contracts/ai/seed-spec.json` |
| `imdg_classes` · `container_size_types` · `vessel_types` · `cargo_types` · `yard_zone_types` · `storage_types` · `capability_types` · `equipment_categories` · `status_types` · `external_systems` · Backend `port_settings` keys | Backend | `contracts/db/reference-seed.json`; the AI Team reviews ISO 6346 size types, IMDG classes, `vessel_types` and `equipment_categories` |

**2. Format.** Sections named after the tables; ENUM values and column names exactly as in the database (`ENVIRONMENTAL`, `KNOTS`, `MAX_ALLOWED`, `template_text`, `model_key`, `value_type` …). References between sections use codes, never ids. `spec_version`: new default values = minor (1.x); a new section or a shape change = major.

```json
{
  "spec_version": "1.0",
  "constraint_types": [
    { "code": "MAX_WIND_KN", "category": "ENVIRONMENTAL", "unit": "KNOTS", "comparator": "MAX_ALLOWED", "is_hard_safety_limit": true, "description": "Maximum sustained wind for entry" }
  ],
  "safety_constraints": [
    { "constraint_type_code": "MAX_WIND_KN", "value": 25.0, "terminal": null, "berth": null, "vessel_type_code": null, "imdg_class": null, "equipment_category_code": null }
  ],
  "objective_terms": [
    { "code": "WAITING_TIME", "name": "Vessel waiting time" },
    { "code": "RESOURCE_COST", "name": "Resource cost" }
  ],
  "rationale_templates": [
    { "code": "BEST_WAIT", "version": 1, "template_text": "Lowest waiting time for {vessel} at berth {berth}." }
  ],
  "ml_models": [
    { "model_key": "M2_SERVICE_TIME", "algorithm_family": "GRADIENT_BOOSTING", "description": "Berth service time (P50 / P90)" }
  ],
  "ml_model_versions": [
    { "model_key": "M2_SERVICE_TIME", "version_no": 1, "status": "CHAMPION", "artifact_path": "models/m2_service_time/v1.joblib", "trained_at": "2026-11-01T00:00:00Z", "hyperparameters": {} }
  ],
  "port_settings": [
    { "setting_key": "solver_time_limit_seconds", "value_type": "INT", "value": "10", "min": 1, "max": 120, "description": "CP-SAT time limit per solve" }
  ]
}
```

- `min` / `max` are optional and omitted for `STRING`, `JSON` and `BOOL`.
- `ml_model_versions` is seeded because `solver_run_model_versions` needs an existing version and `w_part3` cannot insert versions in the MVP (DEC-08). A model with no CHAMPION at go-live has no row; the worker uses the CT-10 fallback.

**3. Seeding rules (Backend).**

| Section | Rule |
| --- | --- |
| `constraint_types` · `objective_terms` · `ml_models` | Upsert by `code` / `model_key` |
| `rationale_templates` | New text = new row with `version + 1`; the old row gets `is_active = 0`. Never edited in place |
| `ml_model_versions` | Insert if `(model_key, version_no)` is missing |
| `safety_constraints` | Insert if no active row exists for the same scope |
| `port_settings` | Insert missing keys. Update `setting_value` to a new default **only while `updated_by IS NULL`**; never touch a value the PORT_GM changed. `min`, `max` and `description` are always updated (metadata) |

**4. `port_settings`.** Edited only by `PORT_GM` (DEC-12); every change fills `updated_by` / `updated_at` and is audited. The Backend enforces `min` / `max` and three cross-field rules on save: `part1_min_window_minutes` is a multiple of `part1_time_step_minutes`; `validation_result_ttl_seconds` > `validation_timeout_seconds`; `run_stale_after_seconds` ≥ the value computed by the AI Team. If a worker still meets inconsistent values, it fails the job with `CONFIGURATION_ERROR`. Workers read `port_settings` per job, without cache.

| Key | `value_type` | Value | min | max | Note |
| --- | --- | --- | --- | --- | --- |
| `weather_pull_hours` | INT | ⟨AI⟩ | ⟨AI⟩ | ⟨AI⟩ | |
| `tide_horizon_days` | INT | ⟨AI⟩ | ⟨AI⟩ | ⟨AI⟩ | |
| `part1_stored_data_max_age_hours` | INT | 48 | 1 | 168 | |
| `part1_assessment_horizon_hours` | INT | ⟨AI⟩ | | | DEC-24 |
| `part1_time_step_minutes` | INT | ⟨AI⟩ | | | DEC-24 |
| `part1_min_window_minutes` | INT | ⟨AI⟩ | | | DEC-24 · multiple of the time step |
| `demand_slot_minutes` | INT | ⟨AI⟩ | | | DEC-24 |
| `solver_time_limit_seconds` | INT | 10 | 1 | 120 | |
| `solver_options_per_request` | INT | 3 | 1 | 3 | Maximum (DEC-23) |
| `solver_option_equivalence_pct` | DECIMAL | 10 | 0 | 50 | DEC-23 |
| `objective_weight_waiting_time` | DECIMAL | 1.0 | 0 | 10 | DEC-23 |
| `objective_weight_resource` | DECIMAL | 1.0 | 0 | 10 | DEC-23 (`RESOURCE_COST`) |
| `part1_max_retries` | INT | 3 | 0 | 10 | DEC-04 |
| `run_stale_after_seconds` | INT | ⟨AI⟩ | | | Longest run × (`part1_max_retries` + 1) + margin; replaces `part1_run_timeout_seconds` |
| `validation_timeout_seconds` | INT | 15 | 5 | 60 | CT-13 |
| `validation_result_ttl_seconds` | INT | 600 | 60 | 3600 | CT-13 · greater than the timeout |
| `part3_evaluation_cron` | STRING | ⟨AI⟩ | — | — | DEC-31 · 5-field cron in UTC |
| `drift_psi_threshold` | DECIMAL | ⟨AI⟩ | | | DEC-30 |
| `drift_mae_threshold` | DECIMAL | ⟨AI⟩ | | | DEC-30 |

**5. Objective (DEC-23).** Terms `WAITING_TIME` and `RESOURCE_COST`. Each term is normalised to [0, 1] per request (divided by the worst possible value of that term in the request), multiplied by its weight and summed; the total is scaled by 1000 for CP-SAT. Equal weights therefore mean equal importance.

**6. Rationale rendering.** The worker writes `rationale_template_id` (a specific code + version row) and `rationale_params` (JSON placeholder values) on `recommendation_options` / `terminal_recommendations`. The Backend renders `template_text` of that version at display time (translation-ready, old recommendations keep their wording). Placeholders: `{vessel}` · `{berth}` · `{terminal}` · `{etb}` (UTC, converted by the Backend) · `{waiting_minutes}` · `{delta_minutes}` · `{tug_count}` · `{window_start}` · `{window_end}` · `{constraint}` · `{value}` · `{limit}` · `{unit}`. A placeholder outside this list is a seed error. The final list ships with the templates.

**7. Pending from the AI Team (with the `seed-spec.json` PR):** every ⟨AI⟩ value, `run_stale_after_seconds` with its calculation, the full `constraint_types` list (every SAFETY code used in CT-10 and CT-13), the `safety_constraints` defaults from DEC-30, and the models with a CHAMPION at go-live with their `artifact_path`.

---

## CT-19 · Mock worker behaviour

| | |
| --- | --- |
| Between | Backend → Frontend · Mobile · QA |
| Owner | Backend Team |
| Reviewers | Frontend Team · QA Team |
| Output | `contracts/mock-workers.md`: for each queue, the results it returns and how to choose a scenario |

- Mocks write contract-shaped rows and send C-06, so the Frontend cannot tell them apart from the real workers.
- The scenario is selected with the `mock_scenario` key in `port_settings`, or with a tag in the vessel name.

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
  "berthing_requests.status": ["SUBMITTED","NEEDS_REVISION","PRELIMINARY_APPROVED","CUSTOMS_APPROVED","ENTRY_WINDOW_CONFIRMED","RECOMMENDATION_GENERATED","PLAN_CONFIRMED","PLAN_CANCELLED","COMPLETED","REJECTED","CANCELLED"],
  "plan_components.status": ["UNASSIGNED","ASSIGNED","STARTED","DONE"],
  "recommendations.status": ["PENDING_REVIEW","MODIFIED_BY_STAFF","CONFIRMED","REPLACED"],
  "notification.status": ["SENT","FAILED","ESCALATED"],
  "terminal_recommendations.lifecycle_status": ["YARD_REC_REQUESTED","YARD_REC_GENERATED","GENERATION_FAILED","ACCEPTED","REJECTED","EXPORTED_TO_TOS"]
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
