# ATLANTECH — UML Context

This file explains every UML diagram of ATLANTECH in words, so that a person or an AI model can understand each flow in full detail without seeing the pictures. It covers 3 use case diagrams, 35 sequence diagrams, 20 activity diagrams and 6 state machine diagrams, grouped in the same three categories used by all the diagram files.

**How to use it.** Sections 1 to 7 give the shared context: the system, the actors, the status vocabularies, the rules that apply everywhere, the answer codes, the notation and the category map. Sections 8 to 11 add the project background, the architecture, the requirements (FR and NFR) and the known differences between the project documents and the diagrams. Then each category lists its diagrams. For every diagram you get its purpose, its participants (or lanes, or states), a plain-language story, and a complete structured walk-through generated from the diagram code itself (messages in order, activity steps with every branch, or the full transition table). Diagram identifiers are the ones printed in the PDFs: `1.1`–`3.4` for sequence diagrams, `AD-1`–`AD-20` for activity diagrams, `SM-1`–`SM-6` for state machines and `UC-1`–`UC-3` for the three use case diagrams.

**Source files.** All paths are under the project folder:

| Diagram type | Mermaid code (code only) | Branded PDF with stories |
|---|---|---|
| Use case | `use-case-diagrams/ATLANTECH_Use_Case_Diagrams.md` | `use-case-diagrams/ATLANTECH_Use_Case_Diagrams.pdf` |
| Sequence | `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md` | `sequence-diagrams/ATLANTECH_Sequence_Diagrams.pdf` |
| Activity | `activity-diagrams-v3/ATLANTECH_Activity_Diagrams.md` | `activity-diagrams-v3/ATLANTECH_Activity_Diagrams.pdf` |
| State machine | `state-diagrams/ATLANTECH_State_Diagrams.md` | `state-diagrams/ATLANTECH_State_Diagrams.pdf` |

The project documents summarised in sections 8 to 11 are the graduation proposal, the business model canvas, the system architecture, the Functional Requirements Document and the Non-Functional Requirements specification. The decisions behind the content are recorded in `uml-edits/UML_CONTENT_EDITS.md` (decision register GR-1…GR-11 and R-01…R-21). The diagrams themselves carry no decision or use case identifiers.

## 1. The system in brief

ATLANTECH is a port operations platform that plans how vessels enter a port and berth: the safe entry-time window, the berth, the tugs and the marine pilot, and, for container vessels, where containers go in the yard. It has two sides.

- **Central SaaS** (run by ATLANTECH). The SaaS Admin manages admin accounts, plan parameters, the governorate list, the registry of ports, the annual licenses and the billing records. A Check-in API answers the ports' daily license check-in, and a License Signer signs license tokens with a key held in a KMS. The SaaS never sees a port's operational data.
- **Port Server** (one per port, installed on premises in the port's LAN). It runs the API and web dashboard, the port database, Redis queues, a realtime server (Reverb: SSE to the web dashboard, WebSocket to the mobile app), the EDI Parser for BAPLIE files, a scheduler, and three Python AI workers:
  - **AI Part 1 — Predictive and Environmental**: fetches weather, wave and sea-level data (primary and secondary provider, every 6 hours), computes the astronomical tide daily, and proposes feasible entry-time windows. It never allocates a berth, tug or pilot.
  - **AI Part 2 — AI Engine**: predicts service time and delay risk and solves the berth, tug and pilot allocation with CP-SAT; on a technical solver failure it builds a FIFO fallback plan. It also generates yard placement recommendations.
  - **AI Part 3 — Feedback Loop**: evaluates outcomes on trusted data, watches model drift, applies forecast bias correction and retrains models under guard.
- **Mobile app** for field users (pilots, tug masters, terminal supervisors). It is offline-first: every change is written to a local Outbox and synchronized later. Phones are managed devices (MDM) and reach the server from outside the port through a per-app always-on VPN; the fixed address `app.atlantech.io` resolves to the port server through split DNS.

The port server contacts the Central SaaS only for the license (daily check-in), or receives a manual token file when it has no internet. Operational and training data never leave the port.

## 2. Actors

| Actor | Side | Role in the diagrams |
|---|---|---|
| SaaS Admin | Central | Runs the platform: admins, plans, governorates, port registry and lifecycle, licenses, tokens, billing records, fleet monitoring. Signs in with password and email one-time code. |
| ATLANTECH Support Engineer | Central | Deploys the signed build, validates and signs the port's TLS certificate with the offline Root CA, bootstraps the port instance, gives remote support within an approved ticket. |
| Port IT Administrator | Port | Prepares the network, firewall, split DNS, VPN and MDM; generates the server key and CSR; installs certificates; opens and closes onboarding and support sessions; enrolls and revokes devices. |
| Port Admin | Port | Application administrator: users, roles, devices and tokens, port profile, terminals and berths; installs or uploads the license token; triggers a check-in; the only one who can use the safety exception; reviews rejected model candidates. |
| Port Authority Staff | Port | Handle each vessel call: berthing request, approvals, Customs, entry window, BAPLIE, recommendation review and plan confirmation, deviations. |
| Department managers and administrators | Port | Tug and Pilotage Department Managers keep fleets and rosters; CT Administrator keeps cranes, equipment and yard; NCT Administrator keeps NCT storage; Marine Safety Officer sets safety constraints, environmental limits, chart datum and under-keel clearance. |
| Pilotage and Tug Department Officers | Port | Confirm or replace the proposed pilot, tug master and tug, and assign the components. |
| Marine Pilot, Tug Master | Port (field) | Receive tasks, acknowledge them and report actual status from the mobile app. |
| CT Operation Planner | Port | Reviews, adjusts, accepts or rejects yard placement and enters the plan into the terminal's TOS. |
| Office User, Mobile User, Field User | Port | Generic users of the web dashboard and of the mobile app (remote field user outside port Wi-Fi, on-site field user inside the terminal). |
| System actors | Both | Scheduler, KMS / License Signer, Check-in Client and API, EDI Parser, AI Part 1/2/3, weather and marine data providers, Realtime Server, MDM platform, VPN gateway, managed device. |

There is no external berthing-request source, no payment gateway and no TOS integration: requests are entered by staff, payment happens outside the system and is only recorded, and the TOS receives the yard plan by hand.

## 3. Status vocabularies

All statuses are written in capitals exactly as stored.

| Object | Values |
|---|---|
| License (central) | `PENDING`, `ACTIVE`, `SUSPENDED`, `EXPIRED`, `REVOKED`. At most one `ACTIVE` license per port. A `PENDING` renewal can be `on_hold` while the current license is suspended. |
| Port lifecycle (central) | `ONBOARDING`, `ACTIVE`, `SUSPENDED`, `OFFBOARDED` (final). |
| Port-side license mode | `SETUP` (port `ONBOARDING`), `FULL` (port `ACTIVE`, license `ACTIVE`, token valid), `READ_ONLY` (any other case, always with a reason). |
| Signing key | `PREPARED`, active, retired. |
| Billing transaction | `PENDING`, `FAILED`, `PAID`, `REFUNDED`, `CANCELLED`. `PENDING`, `FAILED` and `PAID` are "live" for a license period. |
| Berthing request | `SUBMITTED`, `NEEDS_REVISION`, `PRELIMINARY_APPROVED`, `CUSTOMS_APPROVED`, `ENTRY_WINDOW_CONFIRMED`, `RECOMMENDATION_GENERATED`, `PLAN_CONFIRMED`, `PLAN_CANCELLED`, `COMPLETED`, `REJECTED`, `CANCELLED`. |
| Outcomes (not states) | Part 1 run: `WINDOWS_FOUND`, `NO_FEASIBLE_WINDOW` (with the limiting factor), `ENV_DATA_UNAVAILABLE` (no usable environmental data). Part 2: `NO_FEASIBLE_PLAN` (nothing passes the hard constraints). |
| Recommendation version | `PENDING_REVIEW` (source `AI` or `FIFO`), `MODIFIED_BY_STAFF` (override), `CONFIRMED` (its plan is confirmed), `REPLACED` (replaced by a newer version). A version has purpose `INITIAL` or `DELAY_REPLAN`. |
| Operational plan | `CONFIRMED`, `COMPLETED`, `CANCELLED`; inside `CONFIRMED` three regions: pilot and tug (`UNASSIGNED` → `ASSIGNED` → `STARTED` → `DONE`) and yard (`YARD_PENDING` → `YARD_ACCEPTED` → `YARD_DONE`, or `YARD_NOT_APPLICABLE`). Acknowledged is read from the notification, not a state. |
| Yard recommendation | `YARD_REC_REQUESTED`, `YARD_REC_GENERATED`, `GENERATION_FAILED`, `YARD_REC_ACCEPTED`, `YARD_REC_REJECTED`, `EXPORTED_TO_TOS`. |
| BAPLIE file | file `STAGED`, `ACTIVE`, `REPLACED`, `WITHDRAWN`; `parse_status` `PENDING`, `PARSED`, `QUARANTINED` (payload kept as staged data) or `FAILED` (file cannot be read, no staged data). |
| Outbox event (phone) | `PENDING`, `SENDING`, `DONE`, `REJECTED`; `DONE` and `REJECTED` are purged after 30 days. |
| Data quality flags | environmental data `data_stale`, `pull_type` `MANUAL`; field event `clock_skew_suspect`; a record is trusted when `clock_skew_suspect` = 0. |
| Device | enrolled, revoked, `WIPE_PENDING`. |
| Audit entry types | `ADMIN` (human admin action), `SYSTEM` (scheduled job), `SAFETY_EXCEPTION`. |

## 4. Rules that apply everywhere

1. **Write chain.** Every request from web, mobile or API passes, in this order: authentication (401), role and terminal scope (403), minimum app version for mobile (426), license mode and port status (423, or setup restriction), record version (`updated_at`, 409), business rules (409 or 422), plan limits (422). A saved write is stored together with its audit entry; every refused attempt is audited.
2. **Read-only allowlist.** In `READ_ONLY` new writes return `423 LICENSE_READ_ONLY`. Still allowed: status updates and acknowledgements on running work, rejecting or returning a request, rejecting all entry windows, rejecting a yard recommendation, deactivating a user, revoking tokens, uploading a manual license token, and the Port Admin safety exception. Master-data edits, user creation, approvals, confirmations, overrides, regenerations, BAPLIE upload, correction and withdraw are blocked.
3. **Setup allowlist.** While the port is `ONBOARDING` (mode `SETUP`) only the first Port Admin, setup users, port configuration, berths and resources can be written; never operational records. The setup allowlist ends at `ACTIVE` and never applies in `READ_ONLY`; `SETUP` is never re-entered from `READ_ONLY`.
4. **Mode decision.** At every check-in, manual token upload and periodic local check, the port decides its mode in two stages: first the port status (`OFFBOARDED` or `SUSPENDED` → `READ_ONLY`; `ONBOARDING` → `SETUP`), then, for an `ACTIVE` port, the license (`ACTIVE` with a valid token → `FULL`; anything else → `READ_ONLY` with the reason). A suspended license is never shown as onboarding. Token acceptance is separate from permission: a valid token is stored even while the port is `ONBOARDING`.
5. **Tokens.** Signed lazily: at the first check-in after the license is `ACTIVE`, or as a manual token file (only for an `ACTIVE` license, otherwise 422), delivered out of band. Claims include port id, port status, plan limits, key id (`kid`), not-before, issued-at (`iat`), expiry and token id. The port verifies signature, `kid`, port id, dates and `iat`; it ignores a token older than the stored one, refuses one issued before a known suspension or revocation, refuses everything once `OFFBOARDED`, and detects clock rollback with a trusted clock reset at each check-in. An existing token is reused at check-in while more than 14 days remain; a banner warns at 14 days or less.
6. **Plan limits.** Adding a user (tug master and pilot accounts count as users), a terminal or a berth beyond the license limits returns `422 PLAN_LIMIT_EXCEEDED` and nothing is saved.
7. **No delete.** Users and admins are deactivated, roles end with `active_to`, tokens get `revoked_at`, ports are offboarded with the record kept. Nobody can deactivate themselves or the last active admin or Port Admin.
8. **Mobile writes.** Every mobile change goes to the Outbox first with an idempotency key; the server applies each event exactly once. A sync cycle starts on a connectivity change or manual sync, pings with backoff (2 s doubling, max 60 s, 5 tries), sends in order, and ends on a send failure. Creation events are rejected in `READ_ONLY`; status updates and acknowledgements are applied. An event whose `received_at` minus `client_sent_at` is more than 5 minutes is applied but flagged `clock_skew_suspect`; it is never used for training and there is no automatic correction.
9. **Notifications.** SSE to the web dashboard and WebSocket events to the mobile app, sent only after the database commit; there is no push service. Delivery is not acknowledgement. Unacknowledged tasks are re-sent at T+10 and T+20 minutes and escalated at T+30 with an `ACK_ESCALATION` notification to the assigning officer and the department manager. Pre-execution reminders are separate.
10. **AI guard rails.** Hard safety and feasibility constraints are never relaxed by any model. FIFO is only a fallback for a technical solver failure and also passes the hard filter. Part 3 uses trusted data only; a candidate model is deployed only if it is not worse on MAE and override rate, and the previous model is kept for rollback. Staff overrides are a signal, not a retraining trigger.
11. **Plans change by version.** A resource change regenerates only pending recommendations; a confirmed plan is changed by a delay re-plan (proposal, then confirm in one transaction) or cancelled. After any component has started, only the Port Admin safety exception can cancel.
12. **Audit.** Every state change and every refused write is audited. Central admin actions are `ADMIN`, scheduled changes `SYSTEM`.

## 5. Answer codes

| Code | Meaning |
|---|---|
| 401 | Not signed in, or the session or token is no longer valid (also a revoked token). |
| 403 | Signed in but not allowed: role, terminal scope, or `ACCOUNT_DISABLED`. |
| 409 | Conflict with the current state: duplicate BAPLIE, edit after approval, stale record version, regenerate on a confirmed plan, cancel after start. |
| 422 | Invalid input or business rule: no matching request, plan limit exceeded, live billing transaction exists, manual token for a non-active license. |
| 423 | `LICENSE_READ_ONLY`: the current license mode does not allow the action. |
| 426 | The mobile app is below `min_app_version`. |
| 503 | Token signing failed and no still-valid token exists (check-in). |

## 6. Notation

- **Use case diagrams**: stick-figure actors (human in navy, system actors in teal), use cases as ovals grouped in packages, plain lines for associations, dashed arrows labelled «include» or «extend».
- **Sequence diagrams**: actor = person; boundary = user interface; control = API, service, worker or scheduler; database = data store; queue = Redis queue; plain rectangle = external system. Solid arrow = call, dashed arrow = reply. `alt`, `opt`, `loop`, `par` frames. No numbering; order is top to bottom.
- **Activity diagrams**: swimlanes per participant, rounded rectangles for actions, diamonds for decisions (answers on the outgoing arrows), bars for fork and join, filled circle with ring for final nodes (a diagram may have several), beige boxes for notes. A diamond `READ_ONLY?` asks whether the port is in read-only mode.
- **State machines**: `event [guard] / action` on transitions; `[FULL]` means the transition is refused in read-only mode; a state box with a lower compartment lists internal transitions; dashed regions inside a composite state run in parallel.

## 7. Category map

| Category | Use case | Sequence | Activity | State |
|---|---|---|---|---|
| 1. Central SaaS, Licensing and Billing | UC-1 | 1.1–1.14 | AD-1–AD-7, AD-20 | SM-1 License, SM-2 Port lifecycle, SM-3 Port-side license mode |
| 2. Port Setup, Operations and Recommendation | UC-2 | 2.1–2.17 | AD-8–AD-14, AD-18, AD-19 | SM-4 Berthing request, SM-5 Operational plan |
| 3. Execution Feedback and Model Learning | UC-3 | 3.1–3.4 | AD-15, AD-16, AD-17 | SM-6 Outbox event |

The end-to-end story across the categories: a port is registered, provisioned and licensed (category 1); it sets up its users and master data, receives a vessel's berthing request and BAPLIE, gets an entry window from AI Part 1 and a recommendation from AI Part 2, confirms the plan, dispatches pilots and tugs and plans the yard (category 2); field crews report what really happens from offline-capable phones, deviations trigger re-plans, and AI Part 3 learns from trusted outcomes (category 3). Every day, underneath, the port checks its license and decides whether it may write.

## 8. Project background

This section and the next three summarise the project documents (graduation proposal, business model canvas, system architecture, functional requirements and non-functional requirements) so the diagrams can be read against them. Where a document and the diagrams differ, section 11 says which one the diagrams follow.

**Why ATLANTECH exists.** A port is a group of independently run parties: the port authority, the pilotage and tug departments, container terminals (CT) and non-container terminals (NCT). Each plans its own resources but all compete for the same berths, navigation channel, tugs and pilots. The proposal names three root causes: isolated planning, no visibility of upcoming demand, and berthing that ignores tide, surge, wind, waves and visibility. The results are vessel waiting, missed tidal windows, re-handling, cascading delay and eroded safety margins.

**What it is.** A port-wide advisory, recommendation and coordination layer. Its defining rule: *ATLANTECH recommends and coordinates; existing terminal and port systems execute.* It never replaces a TOS (such as Navis N4) or a PMIS (such as SPS-Harbor), never controls equipment, and every recommendation needs human approval before dispatch.

**The coordination loop.** Data ingestion (BAPLIE, berthing requests, weather) → unified operational state → recommendation (AI Part 1 entry window, AI Part 2 allocation) → human review (approve or override) → plan confirmation and dispatch → actual status from the field → deviation tracking (plan vs actual) → operational feedback (AI Part 3, port-local) → updated state.

**Reference port.** Damietta Port: 8 terminals, 36 berths, about 26 vessels a day. It is a case study only; the product must work for any port through configuration (from 1 terminal and 5 berths up to 10 terminals and 50 berths) without code changes.

**Scope.** In scope: coordinated berth, tug and pilot allocation across terminals; environmental feasibility windows and entry-time recommendation; container-yard placement and timing for CT; storage, equipment and sequencing for NCT (built after CT); BAPLIE ingestion; human review; status tracking, deviations and notifications. Out of scope: vessel-to-terminal assignment (fixed by commercial contracts), customs systems (customs approval is only recorded by hand), ERP functions, direct equipment control, detailed mooring or bunkering, AIS or telemetry, and any sharing of data or AI models between ports.

**Business model.** B2G2B. The primary buyer is the port authority (through ministry tenders), secondary buyers are CT and NCT operators, end users are pilots, tug masters, planners and safety officers. Revenue: a one-time setup and integration fee, an annual core port license (3 to 5 year contracts, tiered by port size), optional annual terminal add-ons (container yard module, bulk and tank storage module) and an enterprise support SLA. There are no monthly subscriptions; all billing is annual. This is why the central SaaS keeps annual licenses and yearly billing records (category 1 diagrams).

**Evaluation.** Against a manual-planning baseline: conflicts detected and resolved, resource utilisation, avoidable idle time, estimated operating cost, feasibility and quality of recommendations, and downstream impact. The key target is whether the port can handle more than its current ~26 vessels a day.

## 9. Architecture and technology

| Layer | Technology | Notes |
|---|---|---|
| Clients | Vue.js web dashboard; Flutter mobile app | Web over HTTPS with SSE; mobile over HTTPS and WebSocket, offline-first. |
| Entry | NGINX | Load balancer and TLS termination (TLS 1.3 only). |
| Application | Laravel modular monolith (one or more app instances) | Domain modules with one-way dependencies; terminal modules never import each other. |
| Cache and jobs | Redis | Cache, hot state, and separate job queues per worker (`queue:part1`, `queue:part2`, `queue:edi`). |
| Workers | Python satellites: EDI Parser (BAPLIE D.17A, deterministic, not AI), AI Part 1, AI Part 2 (OR-Tools CP-SAT), AI Part 3 | Read state from and write results to the database. |
| Data | MySQL primary (writes) and replica (reads); dedicated file volume for BAPLIE files | Two fully separate databases: Central SaaS registry DB and the port operational DB. |
| Central SaaS | Vue.js SaaS dashboard, Laravel SaaS API, MySQL registry DB | Licenses, plans, billing, port registry only. No runtime calls into ports, no operational data, no AI models. |

**Isolation policy.** Every port is a full, dedicated installation of the same system on its own server and network. No operational data, model weights or learning updates ever move between ports or between a port and the SaaS; the only link is license verification. Cross-port (federated) learning was explicitly rejected. Inside one port, competing terminals are separated by terminal-level row security: a terminal user cannot see another terminal's cargo, stowage, yard plans or costs (answer 403).

**Roles.** One hierarchy repeats in every domain: Administrator or Manager (master data) → Officer or Planner (receives and dispatches recommendations) → Supervisor or Field Executor (reports actual status). Plus the SaaS Admin (platform only, no port data) and the Marine Safety Officer (safety constraints before recommendation).

**AI in three parts.** Part 1 (predictive and environmental) is mostly physics and rules and outputs only constraints: feasible entry-time windows. Part 2 (AI Engine) is the only allocation authority: rule-based filtering plus CP-SAT, fed by two ML predictions (service time and delay risk), with template-based rationale (not an LLM). Part 3 (feedback loop) evaluates real outcomes and retrains the models under human-approved, local-only governance. A Vision module was designed but is excluded from the current scope.

**Team workflow.** Three repositories under the `Atlantech-project` GitHub organisation: `project-backend`, `project-frontend`, `project-mobile`. Each task is a `feature/<task-name>` branch from `develop`, merged back to `develop` by pull request.

## 10. Requirements

Every diagram section below has a **Requirements** line listing the functional (FR) and non-functional (NFR) requirements it shows. FR numbers follow the Functional Requirements Document; NFR numbers follow the Non-Functional Requirements specification (ISO/IEC 25010).

**Functional requirement groups**

| Group | Subject | Main diagrams |
|---|---|---|
| FR-0.1–0.6 | Central SaaS: port registry, license plans, licenses, billing, platform audit, no operational data | Category 1 (UC-1, 1.1–1.14, AD-1–AD-7, SM-1, SM-2) |
| FR-1.1–1.9 | Port and resource master data: berths, tugs and tug masters, pilot roster (shift-aware), channel and waypoints, unified model, change history | 2.4–2.6, AD-18 |
| FR-2.1–2.6 | BAPLIE upload, parsing, vessel record, diagnostics without partial commit, manual correction, file hash and status | 2.7, 2.8, AD-8 |
| FR-3.1–3.11 | Berthing request: creation, review, preliminary approval, status lifecycle with logged transitions, release of resources on cancel | 2.9–2.11, 2.14, AD-9, AD-10, AD-12, SM-4 |
| FR-4.1–4.9 | Recommendation engine: sequencing, berth, tug and pilot recommendations from actual state, review, override with reason, regeneration, metadata and rationale | 2.13, 2.14, AD-11, AD-12 |
| FR-5.1–5.4 | Plan dispatch to pilots and tug masters; field status from the mobile app | 2.15, 3.1–3.3, AD-13, AD-15 |
| FR-6.1–6.4 | State tracking and deviations: plan vs actual, deviation records, browsing | 3.3, AD-16 |
| FR-7.1–7.3 | Notifications at execution time, reminders with lead time, delivery status | 2.15, AD-13 |
| FR-8.1–8.10 | Container terminal: equipment, yard zones, blocks and slots, yard placement, TOS-usable format, planner accept, reject or adjust | 2.6, 2.16, AD-14 |
| FR-9.1–9.6 | Non-container terminal: storage facilities, allocation, gas and petrochemical resources, Marine Safety Officer constraints | 2.6 (master data only) |
| FR-10.1–10.8 | Configuration and extensibility: per-port terminals and resources, terminal types, shared recommendation interface and output contract, pre-recommendation safety point | 2.4, 2.6, 2.10, AD-18 |
| FR-11.1–11.6 | Access control: role hierarchy, SaaS Admin without port data, attributable writes, backend enforcement, terminal scope, commercial confidentiality | 2.1–2.3, AD-18, rule 1 in section 4 |

**Non-functional requirements**

| NFR | Requirement (key figure) | Where it shows in the diagrams |
|---|---|---|
| NFR-PERF-1 | Recommendation latency p50 ≤ 3 s, p95 ≤ 8 s, p99 ≤ 15 s with 15 concurrent pipelines | 2.13, AD-11 |
| NFR-ENG-1 | Solver deadline 10 s, then deterministic FIFO fallback flagged suboptimal, total ≤ 12 s | 2.13, AD-11 (FIFO fallback on technical solver failure) |
| NFR-PERF-2 | BAPLIE parsing ≤ 3 s / 10 s / 25 s for small, medium, large calls | 2.7, AD-8 |
| NFR-PERF-3 | API p95: read ≤ 500 ms, list ≤ 1,200 ms, write ≤ 800 ms, field update ≤ 500 ms | all request flows |
| NFR-PERF-4 | Dashboard update via SSE ≤ 5 s after commit | 2.15, 3.2, AD-13, AD-15 |
| NFR-CAP-1–3 | 1 terminal / 5 berths up to 10 / 50 without code change; ≥ 50 web sessions, ≥ 30 field connections, ≥ 5 parallel solver runs; peak data volumes | 2.4, AD-18 |
| NFR-REL-1–3 | Availability ≥ 99 % in evaluation, restart ≤ 60 s, RTO ≤ 15 min, RPO ≤ 5 min | not drawn (deployment) |
| NFR-REL-4 | Graceful degradation: malformed BAPLIE rejected with no partial commit; work continues if TOS is offline; notification retries | 2.7, AD-8, 2.15, AD-13 |
| NFR-REL-5 | Multi-entity changes in one ACID transaction, full rollback on error | 2.14, AD-11, AD-12 |
| NFR-CONC-1 | Version token on mutable records; stale write answered 409 within 200 ms | rule 1 in section 4 (record version, 409) |
| NFR-SYNC-1 | Field updates follow a monotonic state machine; offline updates that conflict with server changes are rejected, flagged and logged as deviations | 3.2, AD-15, SM-5, SM-6 |
| NFR-SEC-1, SEC-7 | Port-to-port separation; terminal-level isolation, manifest data stripped for other terminals (403) | 2.2, 2.8, section 9 |
| NFR-SEC-2 | RBAC at the API layer; field workers see only their own tasks | 2.2, AD-18 |
| NFR-SEC-3 | Token authentication, short web and mobile sessions, lockout after repeated failures, immediate invalidation | 1.1, 2.1, 2.2, AD-7, AD-17 |
| NFR-SEC-4, SEC-5 | TLS 1.3 in transit; AES-256 at rest, keys outside the code | 1.5, AD-1, AD-20 |
| NFR-SEC-6 | Append-only audit log (no update or delete) | rule 12 in section 4; 1.2, 2.6 |
| NFR-INT-1 | BAPLIE D.17A segments; unknown segments give warnings, valid slots still load | 2.7, AD-8 |
| NFR-INT-2 | REST with RFC 9457 errors, pagination, OpenAPI 3.0 | answer codes, section 5 |
| NFR-INT-3 | Berthing request adapters (REST, CSV, Excel, manual form) | see section 11 |
| NFR-INT-4 | Engine works with TOS or PMIS disconnected; human-readable export for manual entry | 2.16, AD-14 |
| NFR-INT-5 | IMO FAL data elements; national single window via pluggable adapter | not drawn |
| NFR-UX-1 | Inline rationale with constraints, resource logic, alternatives and confidence | 2.13, AD-11 |
| NFR-UX-2 | Execution alerts ± 60 s; reminders with configurable lead time (default 2 h); deviation alerts ≤ 3 min; virtual clock for testing | 2.15, AD-13, 3.3 |
| NFR-UX-3 | Field status in ≤ 3 taps, ≥ 16 sp text, offline task cache, sync badge ≤ 3 s after reconnect | 3.1, 3.2, AD-15, AD-17 |
| NFR-UX-4 | Specific, actionable, safe, bilingual (Arabic and English) error messages | 2.7, AD-8 and all refusals |
| NFR-EXT-1–5 | Port onboarding without code change (≤ 4 h by template, ≤ 24 h by UI); pluggable terminal modules; no circular module dependencies; test coverage gates; business rules changeable at runtime | 2.4, 2.6, AD-1, AD-18 |

## 11. Where the documents and the diagrams differ

The diagrams follow the decision register (`uml-edits/UML_CONTENT_EDITS.md`), which is newer than the documents below. An AI or reader should treat the diagrams as the current design and these points as known differences, not errors in the diagrams.

| Topic | Document says | Diagrams show |
|---|---|---|
| Solver failure | Master context D15: no fallback. NFR-ENG-1: FIFO fallback after a 10 s deadline. | FIFO fallback on technical solver failure, also passing the hard safety filter (agrees with NFR-ENG-1). |
| Berthing request statuses | FRD FR-3.9: received, needing revision, rejected, preliminary approved, recommendation generated, plan confirmed, completed, cancelled. Architecture: `RECEIVED_FROM_EXTERNAL`. | `SUBMITTED`, `NEEDS_REVISION`, `PRELIMINARY_APPROVED`, `CUSTOMS_APPROVED`, `ENTRY_WINDOW_CONFIRMED`, `RECOMMENDATION_GENERATED`, `PLAN_CONFIRMED`, `PLAN_CANCELLED`, `COMPLETED`, `REJECTED`, `CANCELLED` (SM-4). |
| Request intake | FR-3.2, FR-3.3 and NFR-INT-3: external API and CSV, Excel adapters as well as manual entry. | Requests are entered by Port Authority Staff only; there is no external request source. |
| TOS link | NFR-REL-4 and NFR-INT-4: outbound adapters, buffered when the TOS is offline. | The CT Operation Planner exports the yard plan and enters it into the TOS by hand (the human-readable fallback of NFR-INT-4). |
| Notifications | NFR-REL-4: push notification retries with backoff. | No push service: SSE and WebSocket after commit, re-send at T+10 and T+20 minutes, escalation at T+30. |
| Field task states | NFR-SYNC-1 example: `ASSIGNED` → `STARTED` → `COMPLETED`. | `UNASSIGNED` → `ASSIGNED` → `STARTED` → `DONE` inside the confirmed plan (SM-5). |
| Login lockout | NFR-SEC-3: lock for at least 15 minutes after 5 failed attempts. | SaaS Admin sign-in: a failed attempt is denied and audited, with no lockout in this release. |
| Marine Safety Officer scope | NFR-SEC-2: non-container scope. FR-9.6: gas carrier constraints for NCT. | Sets safety constraints, environmental limits, chart datum and under-keel clearance for the port's entry decisions. |
| License pricing | FR-0.2: price per month. | Annual licenses and yearly billing records, matching the business model (no monthly billing). |
| Environmental windows and AI feedback | Not in the FRD (only in the proposal, architecture and master context). | Drawn in full: entry-window assessment (2.10–2.12, AD-10) and guarded retraining (3.4, AD-16). |
| License modes and tokens | Not in the FRD or NFR. | Drawn in full from the master context decisions (category 1, SM-3). |
| FR numbering in the NFR document | NFR traceability uses another numbering (for example FR-1.4.1). | This file uses the FRD numbering (FR-0.1 … FR-11.6). |
| National single window | NFR-INT-5 and its glossary name EMSW; the corrected business model canvas names Nafeza. | Not drawn (out of scope). |

## Category 1 — Central SaaS, Licensing and Billing

### UC-1 — Use case diagram: How a port joins ATLANTECH and keeps its license

**Code:** `use-case-diagrams/ATLANTECH_Use_Case_Diagrams.md`, diagram 1. **System boundary:** ATLANTECH: Central SaaS, Licensing and Billing. **Requirements:** FR-0.1–FR-0.6, FR-11.2; NFR-SEC-3, NFR-SEC-4, NFR-SEC-6.

This diagram covers the central side of ATLANTECH: the people who run the platform, the steps that bring a new port online, the annual license that lets the port work, and the yearly billing record. It also shows the small part of licensing that runs on the port's own server every day. Read it as the story of one port, from the day it is registered to the day it could be offboarded.

**Actors**

- **SaaS Admin**: Runs the central platform: admin accounts, ports, licenses and billing records.
- **Support Engineer**: ATLANTECH's technical person. Installs the signed build, signs the port's TLS certificate with the offline Root CA, bootstraps the server and gives remote support.
- **Port IT Administrator**: The port's own IT person. Prepares the server, creates the certificate request, installs certificates and opens or closes the support session.
- **Port Admin**: The port's application administrator. Installs the license, triggers a check-in and views the license status.
- **Port User**: Any port user who sees the license banner or tries a restricted action.
- **System actors**: Scheduler, KMS / License Signer, Port Check-in Client, Central SaaS Check-in API and VPN Gateway. These are machines, drawn in teal.

**Story**

*1. Running the platform.* The SaaS Admin signs in with an email and password and then a one-time code sent by email. From there the admin manages other admin accounts, the plan parameters, the governorate list, reads the platform audit log and watches the fleet of ports and their license status. Every change to accounts, plans or governorates records a platform audit entry. An admin can never deactivate themselves or the last active admin, and plans are edited in place because each license keeps its own copy of the limits and price.

*2. Registering a new port.* The SaaS Admin registers the port deployment, which also issues the port's API credential. The registry record can be updated later, and the credential can be rotated. The port starts in the ONBOARDING state.

*3. Preparing the port server.* Port IT opens a time-boxed onboarding session. Inside it the Support Engineer provisions the port server with the signed build; the build's signature is verified before it runs. Port IT generates the server key and certificate request, and the Support Engineer signs the certificate with the offline Root CA. The Support Engineer then bootstraps the instance: the TLS certificate is installed, the initial license is installed and checked, and the first Port Admin account is created with a one-time password that must be changed at the first login. Every session is audited, and it closes when the port becomes ACTIVE or when its time runs out. The same session is used later for remote support, within the scope of an approved ticket.

*4. Activating the port.* When the Port Admin confirms the port is ready, the SaaS Admin activates it. Activation needs a checklist: a valid token installed, the essential settings, berth and resource data, and a Port Admin account. The Port Admin's confirmation is recorded in the audit. The same action, Activate or Reinstate Port, brings a suspended port back.

*5. Issuing the license.* The SaaS Admin issues one annual license per port, or renews it early; a renewal starts when the current license ends. No token is signed at this moment. The license token is signed later, either at the port's first check-in after the license is ACTIVE or when the SaaS Admin generates a manual token file for a port without internet; that file is delivered out of band. A scheduler updates license states every day by date. The admin can suspend a license, reinstate it, or revoke it together with its token, and can rotate the signing key; the new public key reaches ports with the next application update.

*6. Paying for the year.* Payment itself happens outside ATLANTECH. The SaaS Admin creates a billing transaction when a license is issued or renewed, then records the outcome: paid (with an external reference), failed (and retried on the same transaction), refunded or cancelled. There are no automatic reminders and a failed payment never suspends a license by itself.

*7. Every day on the port server.* The port server checks in with the Central SaaS once a day, or immediately when the Port Admin presses Check In Now. A port without internet uploads the manual token instead. Each token is validated (signature, key, port, dates, and the clock is checked for rollback), and then the license mode is decided in two steps: first the port's lifecycle, then the license. The result is FULL, SETUP while the port is still onboarding, or READ_ONLY with a reason. Any restricted write action passes through two guards: Enforce Read-Only Mode, which returns 423 when the mode does not allow it, and Enforce Plan Limits, which refuses a new user, terminal or berth over the plan limit. A banner warns users 14 days before the token expires or tells them the system is read-only. When a new valid token arrives, full mode is restored.

*8. When things change.* Suspending or reinstating a port does not touch its licenses or tokens; the port simply reads its new status at the next check-in. Offboarding a port revokes its licenses and their tokens. Suspending a license keeps its token, but the port works in read-only mode until the license is reinstated.

**Use cases by package** (actor associations in brackets; related sequence · activity · state diagrams after the package name)

- **Platform Administration** — 1.1, 1.2 · AD-7
  - Authenticate SaaS Admin with Email OTP (SaaS Admin)
  - Manage SaaS Admin Accounts (SaaS Admin)
  - Manage Plan Parameters (SaaS Admin)
  - Manage Governorate List (SaaS Admin)
  - View Platform Audit Log (SaaS Admin)
  - Record Platform Audit Entry (reached only through include or extend)
  - Monitor Port Fleet and License Status (SaaS Admin)
- **Port Registry and Lifecycle** — 1.3, 1.4 · AD-1, AD-3 · SM-2
  - Register Port Deployment (SaaS Admin)
  - Update Registry Record (SaaS Admin)
  - Issue Port API Credential (reached only through include or extend)
  - Rotate Port API Credential (SaaS Admin)
  - Activate or Reinstate Port (SaaS Admin)
  - Suspend Port (SaaS Admin)
  - Offboard Port (SaaS Admin)
- **Provisioning and Certificates** — 1.5 · AD-1, AD-20
  - Provision Port Server with Signed Build (Support Engineer)
  - Deploy Build and Verify Signature (Port IT Administrator)
  - Bootstrap Port Instance (Support Engineer)
  - Install Initial License (Port Admin)
  - Install Port TLS Certificate (Port IT Administrator)
  - Generate Key and CSR (Port IT Administrator)
  - Sign Port TLS Certificate with Root CA (Support Engineer)
  - Renew Port TLS Certificate (Port IT Administrator)
- **Onboarding and Support Access** — 1.5 · AD-1, AD-20
  - Open Onboarding Session (Port IT Administrator, VPN Gateway)
  - Perform Remote Install or Support Session (Support Engineer)
  - Close Session at Activation or Expiry (Port IT Administrator, VPN Gateway)
  - Audit Session (Port IT Administrator)
- **License Management** — 1.6–1.11 · AD-2, AD-3 · SM-1
  - Issue License (SaaS Admin)
  - Renew License Early (SaaS Admin)
  - Enforce One Active License per Port (reached only through include or extend)
  - Suspend License (SaaS Admin)
  - Reinstate License (SaaS Admin)
  - Revoke License (SaaS Admin)
  - Revoke License Token (SaaS Admin)
  - Update License Status by Date (Scheduler)
  - Sign and Issue License Token (KMS / License Signer)
  - Generate Manual Token File (SaaS Admin)
  - Deliver Token File to Port (SaaS Admin)
  - Process Port Check-in (Port Check-in Client)
  - Authenticate Check-in (reached only through include or extend)
  - Rotate Signing Key (SaaS Admin, KMS / License Signer)
- **Billing** — 1.12 · AD-4
  - Create Billing Transaction (SaaS Admin)
  - Record Payment Outcome (SaaS Admin)
  - Handle Failed Payment (SaaS Admin)
  - Refund Payment (SaaS Admin)
  - Cancel Billing Transaction (SaaS Admin)
  - Review Billing History (SaaS Admin)
- **License on the Port Server** — 1.13, 1.14 · AD-5, AD-6 · SM-3
  - Perform Daily Check-in (Scheduler, Central SaaS Check-in API)
  - Check In Now (Port Admin)
  - Upload Manual Token (Port Admin)
  - Validate License Token (reached only through include or extend)
  - Detect Clock Rollback (reached only through include or extend)
  - Determine License Mode (reached only through include or extend)
  - Display Token Expiry or Read-Only Banner (Port User)
  - Restore Full Mode (reached only through include or extend)
  - View License Status (Port Admin)
  - Perform Restricted Write Action (Port User)
  - Enforce Read-Only Mode (reached only through include or extend)
  - Enforce Plan Limits (reached only through include or extend)

**Include and extend relations** (read "A includes B" as: A always performs B; "A extends B" as: A optionally adds to B)

- Manage SaaS Admin Accounts **includes** Record Platform Audit Entry
- Manage Plan Parameters **includes** Record Platform Audit Entry
- Manage Governorate List **includes** Record Platform Audit Entry
- Register Port Deployment **includes** Issue Port API Credential
- Offboard Port **includes** Revoke License
- Provision Port Server with Signed Build **includes** Open Onboarding Session
- Provision Port Server with Signed Build **includes** Deploy Build and Verify Signature
- Bootstrap Port Instance **includes** Open Onboarding Session
- Bootstrap Port Instance **includes** Install Port TLS Certificate
- Bootstrap Port Instance **includes** Install Initial License
- Install Initial License **includes** Validate License Token
- Renew Port TLS Certificate **includes** Generate Key and CSR
- Renew Port TLS Certificate **includes** Sign Port TLS Certificate with Root CA
- Perform Remote Install or Support Session **includes** Open Onboarding Session
- Perform Remote Install or Support Session **includes** Audit Session
- Close Session at Activation or Expiry **extends** Open Onboarding Session
- Renew License Early **includes** Issue License
- Issue License **includes** Enforce One Active License per Port
- Reinstate License **extends** Suspend License
- Revoke License Token **extends** Revoke License
- Generate Manual Token File **includes** Sign and Issue License Token
- Process Port Check-in **includes** Authenticate Check-in
- Process Port Check-in **includes** Sign and Issue License Token
- Create Billing Transaction **extends** Issue License
- Create Billing Transaction **extends** Renew License Early
- Handle Failed Payment **extends** Record Payment Outcome
- Refund Payment **extends** Record Payment Outcome
- Check In Now **includes** Perform Daily Check-in
- Perform Daily Check-in **includes** Validate License Token
- Perform Daily Check-in **includes** Determine License Mode
- Upload Manual Token **includes** Validate License Token
- Upload Manual Token **includes** Determine License Mode
- Detect Clock Rollback **extends** Validate License Token
- Display Token Expiry or Read-Only Banner **extends** Determine License Mode
- Restore Full Mode **extends** Perform Daily Check-in
- Restore Full Mode **extends** Upload Manual Token
- Perform Restricted Write Action **includes** Enforce Read-Only Mode
- Perform Restricted Write Action **includes** Enforce Plan Limits

### Sequence diagrams of category 1

#### 1.1 — SaaS Admin sign-in

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 1.1. **Related:** AD-7. **Requirements:** FR-0.5; NFR-SEC-3, NFR-SEC-6.

**Participants**

- **SaaS Admin**: actor (person)
- **SaaS Admin Dashboard**: boundary (user interface)
- **Authentication Service**: control (service, API, worker or scheduler)
- **SaaS Database**: database (data store)
- **Session and Cache Store**: database (data store)

**Story**

This is how a SaaS Admin gets into the central ATLANTECH platform. Sign-in has two factors: a password, then a one-time code sent to the admin's email.

The admin enters an email and password on the SaaS Admin Dashboard. The Authentication Service looks the account up, checks the password against the stored hash and checks that the account is active. If anything is wrong, the admin sees one generic error that does not say which part failed.

When the password is right, the service stores a short-lived one-time code in the session and cache store (not in the SaaS database) and emails it to the admin. The admin types the code in. A wrong or expired code is refused and the admin can ask for a new one. A correct code opens a session and the Platform Dashboard appears.

From then on every request carries the session token. When the session is no longer valid the platform answers 401 and the admin signs in again. There is no lockout counter in this release.

**Message flow, top to bottom**

- SaaS Admin → SaaS Admin Dashboard: Enter email and password
- SaaS Admin Dashboard → Authentication Service: Authenticate (email, password)
- Authentication Service → SaaS Database: Find admin account by email
- SaaS Database → Authentication Service (reply): Account or none
- Authentication Service (internal): Verify password hash and is_active
- **Alternative paths — case: Wrong credentials or inactive account**
  - Authentication Service → SaaS Admin Dashboard (reply): Authentication failed (generic message)
  - SaaS Admin Dashboard → SaaS Admin (reply): Show error
- **Otherwise — case: Password valid**
  - Authentication Service → Session and Cache Store: Store one-time code (hashed, short expiry)
  - Authentication Service → SaaS Admin (reply): Send one-time code by email
  - SaaS Admin → SaaS Admin Dashboard: Enter the code
  - SaaS Admin Dashboard → Authentication Service: Verify code
  - Authentication Service → Session and Cache Store: Read stored code
  - Session and Cache Store → Authentication Service (reply): Code and expiry
  - **Alternative paths — case: Code wrong or expired**
    - Authentication Service → SaaS Admin Dashboard (reply): Verification failed
    - SaaS Admin Dashboard → SaaS Admin (reply): Show error and offer a new code
  - **Otherwise — case: Code valid**
    - Authentication Service → Session and Cache Store: Create session
    - Authentication Service → SaaS Admin Dashboard (reply): Session token
    - SaaS Admin Dashboard → SaaS Admin (reply): Show Platform Dashboard
- *Note:* Every later request carries the session token. An invalid or expired session returns 401 and the admin signs in again.

#### 1.2 — Platform administration

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 1.2. **Related:** AD-7. **Requirements:** FR-0.2, FR-0.5, FR-0.6, FR-11.2; NFR-SEC-6.

**Participants**

- **SaaS Admin**: actor (person)
- **SaaS Admin Dashboard**: boundary (user interface)
- **Platform Administration API**: control (service, API, worker or scheduler)
- **Platform Audit Service**: control (service, API, worker or scheduler)
- **SaaS Database**: database (data store)

**Story**

After signing in, the SaaS Admin runs the platform from one dashboard. Each request first passes a session check; a request without a valid session gets 401.

Admin accounts. The admin creates or edits other admin accounts. Each account carries a logical role field (Platform, License or Billing); there is no separate role table. The email must be unique. Deactivating is guarded by two rules: you cannot deactivate yourself, and you cannot deactivate the last active admin. Both return 409. A successful deactivation also ends that admin's open sessions.

License plans. A plan holds the limits (terminals, berths, users) and the annual price. Plans are edited in place; there is no retire or version step, because every license copies the plan values at issue time and is not affected by later edits.

Governorates, audit log and fleet. The admin keeps the governorate list, reads the platform audit log with filters, and watches the fleet of ports. The fleet view highlights ports that have not checked in recently, licenses close to expiry and suspended or revoked licenses.

Every write is saved together with its audit entry in the same database transaction, so a change is never stored without its record.

**Message flow, top to bottom**

- SaaS Admin → SaaS Admin Dashboard: Choose an operation
- SaaS Admin Dashboard → Platform Administration API: Request with session token
- Platform Administration API (internal): Validate session (401 if invalid)
- **Alternative paths — case: Create or update an admin account**
  - SaaS Admin → SaaS Admin Dashboard: Enter name, email, initial password and logical role (Platform, License or Billing)
  - SaaS Admin Dashboard → Platform Administration API: Save admin account
  - Platform Administration API → SaaS Database: Check the email is unique
  - **Alternative paths — case: Email already used**
    - Platform Administration API → SaaS Admin Dashboard (reply): 422 Duplicate email
  - **Otherwise — case: Email unique**
    - Platform Administration API → SaaS Database: Insert or update the account (is_active = true)
    - Platform Administration API → Platform Audit Service: Record audit entry (same transaction)
    - Platform Administration API → SaaS Admin Dashboard (reply): Account saved
- **Otherwise — case: Deactivate an admin account**
  - SaaS Admin → SaaS Admin Dashboard: Select account and deactivate
  - SaaS Admin Dashboard → Platform Administration API: Deactivate account
  - Platform Administration API → SaaS Database: Read target and count active admins
  - **Alternative paths — case: Target is the current admin**
    - Platform Administration API → SaaS Admin Dashboard (reply): 409 You cannot deactivate yourself
  - **Otherwise — case: Target is the last active admin**
    - Platform Administration API → SaaS Admin Dashboard (reply): 409 Last active admin
  - **Otherwise — case: Allowed**
    - Platform Administration API → SaaS Database: Set is_active = false and end its sessions
    - Platform Administration API → Platform Audit Service: Record audit entry (same transaction)
    - Platform Administration API → SaaS Admin Dashboard (reply): Account deactivated
- **Otherwise — case: Save a license plan**
  - SaaS Admin → SaaS Admin Dashboard: Enter plan name, max terminals, berths, users, annual price, currency
  - SaaS Admin Dashboard → Platform Administration API: Save plan
  - Platform Administration API (internal): Validate positive values and unique name
  - **Alternative paths — case: Invalid**
    - Platform Administration API → SaaS Admin Dashboard (reply): 422 Validation error
  - **Otherwise — case: Valid**
    - Platform Administration API → SaaS Database: Insert or update the plan in place
    - Platform Administration API → Platform Audit Service: Record audit entry (same transaction)
    - Platform Administration API → SaaS Admin Dashboard (reply): Plan saved
  - *Note:* Existing licenses keep their own snapshot of limits and price
- **Otherwise — case: Save a governorate**
  - SaaS Admin → SaaS Admin Dashboard: Enter governorate
  - SaaS Admin Dashboard → Platform Administration API: Save governorate
  - **Alternative paths — case: Name already exists**
    - Platform Administration API → SaaS Admin Dashboard (reply): 422 Duplicate governorate
  - **Otherwise — case: Valid**
    - Platform Administration API → SaaS Database: Insert or update governorate
    - Platform Administration API → Platform Audit Service: Record audit entry (same transaction)
    - Platform Administration API → SaaS Admin Dashboard (reply): Governorate saved
- **Otherwise — case: View the platform audit log**
  - SaaS Admin → SaaS Admin Dashboard: Set filters (actor, action, port, dates)
  - SaaS Admin Dashboard → Platform Administration API: Get audit log page
  - Platform Administration API → SaaS Database: Read entries, newest first
  - Platform Administration API → SaaS Admin Dashboard (reply): Entries and paging
- **Otherwise — case: Monitor the port fleet**
  - SaaS Admin → SaaS Admin Dashboard: Open Port Fleet Monitor
  - SaaS Admin Dashboard → Platform Administration API: Get fleet status
  - Platform Administration API → SaaS Database: Read ports, license status, last check-in, token delivery
  - Platform Administration API (internal): Flag ports with no recent check-in, near expiry, suspended or revoked
  - Platform Administration API → SaaS Admin Dashboard (reply): Fleet status with flags
- SaaS Admin Dashboard → SaaS Admin (reply): Show the result

#### 1.3 — Port registry and API credential

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 1.3. **Related:** AD-1, SM-2. **Requirements:** FR-0.1, FR-0.5.

**Participants**

- **SaaS Admin**: actor (person)
- **SaaS Admin Dashboard**: boundary (user interface)
- **Platform Administration API**: control (service, API, worker or scheduler)
- **Platform Audit Service**: control (service, API, worker or scheduler)
- **SaaS Database**: database (data store)

**Story**

Before a port can use ATLANTECH it must exist in the central registry. This diagram shows the three registry actions of the SaaS Admin.

Registering a port. The admin enters the port's name, UN/LOCODE, governorate and server endpoint. The API checks the fields, that the governorate exists and that the UN/LOCODE is not already used. It then creates a public id and a strong API secret for the port. Only a hash of the secret is stored. The port starts in the ONBOARDING state, and the secret is shown to the admin once so it can be passed to the port through a secure channel.

Updating a record. The admin can correct registry fields such as the server endpoint. The public id never changes.

Rotating the credential. If the secret may have leaked, the admin rotates it. The new hash replaces the old one in one step, so the old secret stops working immediately. An offboarded port cannot get a new credential.

Each change is written with its audit entry in the same transaction.

**Message flow, top to bottom**

- *Note:* The admin is signed in. Every request passes the session check.
- **Alternative paths — case: Register a port deployment**
  - SaaS Admin → SaaS Admin Dashboard: Enter port name, UN/LOCODE, governorate, server endpoint
  - SaaS Admin Dashboard → Platform Administration API: Register port
  - Platform Administration API → SaaS Database: Check required fields, governorate exists, UN/LOCODE unique
  - **Alternative paths — case: Invalid**
    - Platform Administration API → SaaS Admin Dashboard (reply): 422 Validation error
  - **Otherwise — case: Valid**
    - Platform Administration API (internal): Generate public_id and a strong API secret
    - Platform Administration API (internal): Hash the secret (only the hash is stored)
    - Platform Administration API → SaaS Database: Insert port with status ONBOARDING and the credential hash
    - Platform Administration API → Platform Audit Service: Record audit entry (same transaction)
    - Platform Administration API → SaaS Admin Dashboard (reply): Port registered and API secret
    - SaaS Admin Dashboard → SaaS Admin (reply): Show the secret once
- **Otherwise — case: Update a registry record**
  - SaaS Admin → SaaS Admin Dashboard: Edit port fields (for example the server endpoint)
  - SaaS Admin Dashboard → Platform Administration API: Update port
  - Platform Administration API (internal): Validate input (public_id cannot change)
  - **Alternative paths — case: Invalid**
    - Platform Administration API → SaaS Admin Dashboard (reply): 422 Validation error
  - **Otherwise — case: Valid**
    - Platform Administration API → SaaS Database: Update the registry record
    - Platform Administration API → Platform Audit Service: Record audit entry (same transaction)
    - Platform Administration API → SaaS Admin Dashboard (reply): Port updated
- **Otherwise — case: Rotate the port API credential**
  - SaaS Admin → SaaS Admin Dashboard: Select port and rotate
  - SaaS Admin Dashboard → Platform Administration API: Rotate credential
  - Platform Administration API → SaaS Database: Read port status
  - **Alternative paths — case: Port is OFFBOARDED**
    - Platform Administration API → SaaS Admin Dashboard (reply): 422 Port is offboarded
  - **Otherwise — case: Allowed**
    - Platform Administration API (internal): Generate and hash a new secret
    - Platform Administration API → SaaS Database: Replace the credential hash (old one stops working at once)
    - Platform Administration API → Platform Audit Service: Record audit entry (same transaction)
    - Platform Administration API → SaaS Admin Dashboard (reply): New API secret
    - SaaS Admin Dashboard → SaaS Admin (reply): Show the secret once
- *Note:* The secret goes to the port through a secure channel

#### 1.4 — Port status changes

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 1.4. **Related:** AD-3, SM-2, SM-3. **Requirements:** FR-0.1, FR-0.5.

**Participants**

- **SaaS Admin**: actor (person)
- **SaaS Admin Dashboard**: boundary (user interface)
- **Platform Administration API**: control (service, API, worker or scheduler)
- **Platform Audit Service**: control (service, API, worker or scheduler)
- **SaaS Database**: database (data store)

**Story**

A port moves through four lifecycle states: ONBOARDING, ACTIVE, SUSPENDED and OFFBOARDED. This diagram shows how the SaaS Admin moves it, and what each move touches.

Activate and Reinstate are the same action. Activate takes a new port from ONBOARDING to ACTIVE; Reinstate brings a suspended port back to ACTIVE. Both need a readiness checklist: a valid token installed, the essential settings, berth and resource data, and a Port Admin account. If anything is missing the admin gets 422 with the list. The SaaS checks that the Port Admin's readiness confirmation, which the SaaS Admin receives out of band, is recorded in the audit; it does not store the checklist itself.

Suspend sets the port to SUSPENDED (the reason goes in the audit details) and nothing else. Port and license are separate gates, so the port's licenses and tokens stay as they are.

Offboard is final. It sets OFFBOARDED, revokes the port's licenses and their tokens, and writes an audit entry for each change. No row is deleted.

The SaaS never calls the port. The port learns about any of these changes at its next check-in, which returns its port_status and no new token, and the port decides its own mode from that status.

**Message flow, top to bottom**

- SaaS Admin → SaaS Admin Dashboard: Select port and action
- SaaS Admin Dashboard → Platform Administration API: Change port status
- Platform Administration API → SaaS Database: Read current status
- SaaS Database → Platform Administration API (reply): Current status
- **Alternative paths — case: Transition not allowed (OFFBOARDED is final)**
  - Platform Administration API → SaaS Admin Dashboard (reply): 422 Invalid status transition
- **Otherwise — case: Activate (ONBOARDING to ACTIVE) or Reinstate (SUSPENDED to ACTIVE)**
  - Platform Administration API → Platform Audit Service: Check the Port Admin readiness confirmation is recorded
  - *Note:* The Port Admin confirms the checklist (valid token installed, essential settings, berths and resources, a Port Admin account). The SaaS checks the recorded confirmation, not the checklist itself.
  - **Alternative paths — case: Checklist incomplete**
    - Platform Administration API → SaaS Admin Dashboard (reply): 422 with the missing items
  - **Otherwise — case: Checklist complete**
    - Platform Administration API → Platform Audit Service: Record the Port Admin readiness confirmation
    - Platform Administration API → SaaS Database: Set status ACTIVE
    - Platform Administration API → Platform Audit Service: Record audit entry (same transaction)
    - Platform Administration API → SaaS Admin Dashboard (reply): Port is ACTIVE
- **Otherwise — case: Suspend (ACTIVE to SUSPENDED)**
  - Platform Administration API → SaaS Database: Set status SUSPENDED (reason in the audit details)
  - Platform Administration API → Platform Audit Service: Record audit entry (same transaction)
  - Platform Administration API → SaaS Admin Dashboard (reply): Port suspended
  - *Note:* Licenses and tokens are not changed
- **Otherwise — case: Offboard (to OFFBOARDED)**
  - Platform Administration API → SaaS Database: Set status OFFBOARDED
  - Platform Administration API → SaaS Database: Revoke the port's licenses and their tokens
  - Platform Administration API → Platform Audit Service: Record one audit entry per change (same transaction)
  - Platform Administration API → SaaS Admin Dashboard (reply): Port offboarded
- SaaS Admin Dashboard → SaaS Admin (reply): Show the result
- *Note:* Later check-ins return 200 with port_status and no new token. The port computes its mode from port_status.

#### 1.5 — Server provisioning and certificates

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 1.5. **Related:** AD-1, AD-20. **Requirements:** NFR-SEC-4 (server provisioning is deployment work with no FRD item).

**Participants**

- **Support Engineer**: actor (person)
- **Port IT Administrator**: actor (person)
- **Port Admin**: actor (person)
- **Port VPN Gateway**: external system
- **Port Server**: control (service, API, worker or scheduler)
- **SaaS Registry**: database (data store)
- **ATLANTECH Root CA (offline)**: external system

**Story**

This is the technical setup of a new port server. Two people do the work: the port's own IT administrator, who owns the network and the machine, and the ATLANTECH Support Engineer, who installs the software and signs the certificate.

The Support Engineer signs the release build and prepares the bootstrap values. Port IT prepares the VPN, firewall, split DNS and the server operating system, then opens a time-boxed onboarding session. Only inside that session can the Support Engineer reach the intranet-only server.

The Support Engineer deploys the signed build and the server checks its signature before running it. A build with a bad signature is rejected and deployed again correctly.

Next comes the TLS certificate. Port IT generates the key pair and certificate request on the server itself, so the private key never leaves it. The Support Engineer checks the request against the registry: the hostname, the port's status, and that it really came from the registered Port IT contact (kept outside ATLANTECH). If all three pass, the offline ATLANTECH Root CA signs a two-year certificate and the signer and signing date are recorded in the support log (FW-07). Port IT installs it and confirms DNS and the Root CA trust on office PCs.

Finally the Support Engineer bootstraps the instance and seeds the first Port Admin account with a one-time password, which is handed to the Port Admin outside the system. At first login the Port Admin must change it. The onboarding session closes on its own when the port is activated or its time runs out, and its audit record stays. Every two years Port IT renews the certificate with the same checks, without opening a session.

**Message flow, top to bottom**

- *Note:* The port is registered and has a license. Hostname is fixed (app.atlantech.io) with split DNS, one build for all ports.
- Support Engineer (internal): Sign the release build and prepare bootstrap values
- Port IT Administrator (internal): Prepare VPN, firewall, split DNS and server OS
- Port IT Administrator → Port VPN Gateway: Open a time-boxed onboarding session
- Support Engineer → Port VPN Gateway: Connect with the temporary account
- Port VPN Gateway → Port Server: Tunnel to the intranet-only server
- Support Engineer → Port Server: Deploy the signed build
- Port Server (internal): Verify the release signature
- **Alternative paths — case: Signature invalid**
  - Port Server → Support Engineer (reply): Build rejected with reason
  - Support Engineer → Port Server: Re-deploy a correctly signed build
- **Otherwise — case: Signature valid**
  - Port Server → Support Engineer (reply): Server is up (no certificate, no license yet)
- **Loop: Until a certificate is signed**
  - Port IT Administrator → Port Server: Generate key pair and CSR
  - Port Server → Port IT Administrator (reply): CSR (the private key never leaves the server)
  - Port IT Administrator → Support Engineer: Send CSR to ATLANTECH
  - Support Engineer → SaaS Registry: Read port status (Port IT contact kept outside ATLANTECH)
  - SaaS Registry → Support Engineer (reply): Status
  - **Alternative paths — case: Wrong hostname, port not ONBOARDING or ACTIVE, or sender is not the registered contact**
    - Support Engineer → Port IT Administrator (reply): CSR rejected with reason
  - **Otherwise — case: All checks pass**
    - Support Engineer → ATLANTECH Root CA (offline): Sign the CSR (offline step)
    - ATLANTECH Root CA (offline) → Support Engineer (reply): Port certificate, valid 2 years
    - Support Engineer (internal): Record signer and signing date in the support log (FW-07)
    - Support Engineer → Port IT Administrator (reply): Signed certificate
- Port IT Administrator → Port Server: Install the certificate on NGINX
- Port IT Administrator (internal): Confirm split DNS and Root CA trust on office PCs
- Support Engineer → Port Server: Bootstrap instance (port_public_id, license public key, API credential)
- Support Engineer → Port Server: Seed the first Port Admin with a one-time password
- Support Engineer → Port Admin (reply): Hand over the one-time password out of band
- Port Admin → Port Server: First login
- Port Server → Port Admin (reply): Password change required before anything else
- Port VPN Gateway (internal): Session closes at activation or when its time box ends
- Port VPN Gateway → Port IT Administrator (reply): Session audit record kept
- **Optional — only when: Certificate renewal every 2 years (no onboarding session)**
  - Port IT Administrator → Port Server: Generate a new key pair and CSR
  - Port IT Administrator → Support Engineer: Send CSR
  - Support Engineer → SaaS Registry: Repeat the same checks
  - Support Engineer → ATLANTECH Root CA (offline): Sign the CSR (offline step)
  - ATLANTECH Root CA (offline) → Support Engineer (reply): New certificate
  - Support Engineer → Port IT Administrator (reply): Signed certificate
  - Port IT Administrator → Port Server: Install the new certificate

#### 1.6 — Initial license and activation

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 1.6. **Related:** AD-1, AD-2, SM-1. **Requirements:** FR-0.1, FR-0.3.

**Participants**

- **Port Admin**: actor (person)
- **Port License Module**: control (service, API, worker or scheduler)
- **Local License Store**: database (data store)
- **Central SaaS Check-in API**: control (service, API, worker or scheduler)
- **SaaS Admin**: actor (person)

**Story**

This diagram follows a new port from its first license token to full operation. The SaaS never calls the port: every network arrow starts at the port.

Getting the first token. A token is never signed when a license is issued. If the port has internet, the Port Admin presses Check in now. The port sends its public id and API credential; the SaaS authenticates it, signs the first token for the ACTIVE license and returns it with the port's status (ONBOARDING) and the server time. If the port has no internet, the SaaS Admin generates a manual token file for the ACTIVE license and hands it over outside the system, and the Port Admin uploads it.

Installing it. The port's license module checks the signature, key id, port and expiry. A bad token is rejected and nothing changes. A good one is stored with the port status and the plan limits, and the port enters SETUP mode. In SETUP only setup work is allowed: the first Port Admin and setup users, the port configuration, berths and resources. Operational records are not.

Going live. When the port is ready, the Port Admin confirms this to the SaaS Admin outside the system. The SaaS Admin activates the port, which runs the readiness checklist and records the confirmation in the audit. The port learns it is ACTIVE at its next check-in, or, if it is offline, from a fresh manual token whose port_status claim says ACTIVE. The license module stores the new status and switches to FULL mode.

**Message flow, top to bottom**

- *Note:* Port is ONBOARDING and its license is ACTIVE. No token was signed at issue. All network calls go from the port to the SaaS.
- **Alternative paths — case: Port has internet**
  - Port Admin → Port License Module: Check in now
  - Port License Module → Central SaaS Check-in API: POST /api/v1/ports/check-in (public_id, API credential)
  - Central SaaS Check-in API (internal): Authenticate the credential
  - **Alternative paths — case: Bad credential**
    - Central SaaS Check-in API → Port License Module (reply): 401 Unauthorized
    - Port License Module → Port Admin (reply): Check-in failed, verify the credential
  - **Otherwise — case: Credential valid**
    - Central SaaS Check-in API (internal): Sign the first token for the ACTIVE license
    - Central SaaS Check-in API → Port License Module (reply): 200 token, port_status ONBOARDING, server_time
- **Otherwise — case: No internet**
  - SaaS Admin → Central SaaS Check-in API: Generate a manual token for the ACTIVE license
  - Central SaaS Check-in API → SaaS Admin (reply): Token file (carries port_status)
  - SaaS Admin → Port Admin (reply): Deliver the file out of band
  - Port Admin → Port License Module: Upload the token file
- **Optional — only when: A token was received**
  - Port License Module (internal): Verify signature, key id, port and expiry
  - **Alternative paths — case: Token invalid**
    - Port License Module → Port Admin (reply): Rejected with reason, previous state kept
  - **Otherwise — case: Token valid**
    - Port License Module → Local License Store: Store token, port_status and limits
    - Port License Module (internal): Mode = SETUP
    - Port License Module → Port Admin (reply): License installed, mode SETUP
    - *Note:* SETUP allows only setup work: first Port Admin and setup users, port configuration, berths and resources
- Port Admin → SaaS Admin (reply): Readiness confirmation (out of band)
- SaaS Admin → Central SaaS Check-in API: Activate port (checklist, confirmation recorded in audit)
- Central SaaS Check-in API (internal): Port status = ACTIVE
- **Alternative paths — case: Online port**
  - Port License Module → Central SaaS Check-in API: Next check-in
  - Central SaaS Check-in API → Port License Module (reply): 200 token, port_status ACTIVE, server_time
- **Otherwise — case: Offline port**
  - SaaS Admin → Port Admin (reply): Fresh manual token with port_status ACTIVE
  - Port Admin → Port License Module: Upload the token file
- Port License Module → Local License Store: Store port_status ACTIVE
- Port License Module (internal): Mode = FULL
- Port License Module → Port Admin (reply): Full mode

#### 1.7 — Issue and renew a license

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 1.7. **Related:** AD-2, SM-1. **Requirements:** FR-0.2, FR-0.3, FR-0.5.

**Participants**

- **SaaS Admin**: actor (person)
- **SaaS Admin Dashboard**: boundary (user interface)
- **Licensing API**: control (service, API, worker or scheduler)
- **Platform Audit Service**: control (service, API, worker or scheduler)
- **SaaS Database**: database (data store)

**Story**

Each port works under one annual license. This diagram shows how the SaaS Admin issues the first license and renews it.

Issuing. The admin picks the port, the plan and the dates. The port must not be offboarded and the end date must come after the start. The license copies the plan's limits, price and currency at this moment, so later plan edits do not affect it. If the start date has already passed the license is ACTIVE at once, which is only allowed when the port has no other ACTIVE license; otherwise it starts as PENDING.

Renewing. A renewal can be created early. It starts exactly when the current license ends, so it is always created as PENDING and never overlaps the ACTIVE one. The scheduler turns it ACTIVE on its start date.

Neither action signs a token. Token signing is lazy: the token is produced at the port's first check-in after the license is ACTIVE, or when the admin generates a manual token. A signing-service outage therefore never blocks issuing or renewing.

**Message flow, top to bottom**

- *Note:* The admin is signed in. Every request passes the session check.
- **Alternative paths — case: Issue a license**
  - SaaS Admin → SaaS Admin Dashboard: Select port, plan, valid_from, expires_at
  - SaaS Admin Dashboard → Licensing API: Issue license
  - Licensing API → SaaS Database: Read port and plan
  - Licensing API (internal): Validate port not OFFBOARDED and expires_at after valid_from
  - **Alternative paths — case: Invalid**
    - Licensing API → SaaS Admin Dashboard (reply): 422 Validation error
  - **Otherwise — case: Valid**
    - Licensing API (internal): Copy limits, price and currency from the plan
    - Licensing API (internal): Status = ACTIVE if valid_from has passed, otherwise PENDING
    - **Optional — only when: Status is ACTIVE**
      - Licensing API → SaaS Database: Check the port has no other ACTIVE license
    - **Alternative paths — case: Another ACTIVE license exists**
      - Licensing API → SaaS Admin Dashboard (reply): 422 One ACTIVE license per port
    - **Otherwise — case: No conflict**
      - Licensing API → SaaS Database: Insert license with its snapshot
      - Licensing API → Platform Audit Service: Record audit entry (same transaction)
      - Licensing API → SaaS Admin Dashboard (reply): License issued
- **Otherwise — case: Renew a license early**
  - SaaS Admin → SaaS Admin Dashboard: Select the current license, new expires_at and plan
  - SaaS Admin Dashboard → Licensing API: Renew license
  - Licensing API → SaaS Database: Read current license and plan
  - Licensing API (internal): valid_from = current license expires_at
  - **Alternative paths — case: Current license not ACTIVE, or expires_at not after valid_from**
    - Licensing API → SaaS Admin Dashboard (reply): 422 Validation error
  - **Otherwise — case: Valid**
    - Licensing API (internal): Copy limits, price and currency from the plan
    - Licensing API → SaaS Database: Insert renewal with status PENDING
    - Licensing API → Platform Audit Service: Record audit entry (same transaction)
    - Licensing API → SaaS Admin Dashboard (reply): Renewal created as PENDING
- SaaS Admin Dashboard → SaaS Admin (reply): Show the result
- *Note:* No token is signed here. The token is signed at the first check-in or as a manual token.

#### 1.8 — Suspend, reinstate and revoke a license

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 1.8. **Related:** AD-3, SM-1. **Requirements:** FR-0.3, FR-0.5.

**Participants**

- **SaaS Admin**: actor (person)
- **SaaS Admin Dashboard**: boundary (user interface)
- **Licensing API**: control (service, API, worker or scheduler)
- **Platform Audit Service**: control (service, API, worker or scheduler)
- **SaaS Database**: database (data store)

**Story**

After a license is issued, the SaaS Admin can pause it, bring it back or cancel it for good.

Suspend works only on an ACTIVE license. It sets the license to SUSPENDED and sets on_hold on the port's PENDING renewal, so the scheduler will not quietly activate the renewal while the port is suspended. The token is not revoked. The port sees the new status at its next check-in and works in read-only mode.

Reinstate releases a suspension. If the suspended license is still within its dates and the port has no other ACTIVE license, it becomes ACTIVE again and on_hold is cleared on the renewal. If the suspended license has already expired, the admin clears on_hold directly and the scheduler activates the renewal on its date. Reinstating never issues a new token; the port returns to full mode at its next check-in.

Revoke ends a license that is PENDING, ACTIVE or SUSPENDED. If tokens were already signed for it, they are revoked too.

**Message flow, top to bottom**

- SaaS Admin → SaaS Admin Dashboard: Select license and action
- SaaS Admin Dashboard → Licensing API: Change license status
- Licensing API → SaaS Database: Read the license and the port's other licenses
- **Alternative paths — case: Suspend**
  - **Alternative paths — case: License not ACTIVE**
    - Licensing API → SaaS Admin Dashboard (reply): 422 Invalid status transition
  - **Otherwise — case: License ACTIVE**
    - Licensing API → SaaS Database: Set status SUSPENDED
    - Licensing API → SaaS Database: Set on_hold on the PENDING renewal
    - Licensing API → Platform Audit Service: Record audit entry (same transaction)
    - Licensing API → SaaS Admin Dashboard (reply): License suspended
    - *Note:* The token is kept. The port reads the status at its next check-in.
- **Otherwise — case: Reinstate**
  - **Alternative paths — case: Suspended license still valid and no other ACTIVE license**
    - Licensing API → SaaS Database: Set status ACTIVE
    - Licensing API → SaaS Database: Clear on_hold on the PENDING renewal
    - Licensing API → Platform Audit Service: Record audit entry (same transaction)
    - Licensing API → SaaS Admin Dashboard (reply): License reinstated
  - **Otherwise — case: Suspended license already expired**
    - Licensing API → SaaS Database: Clear on_hold on the PENDING renewal
    - Licensing API → Platform Audit Service: Record audit entry (same transaction)
    - Licensing API → SaaS Admin Dashboard (reply): Hold released, the scheduler activates the renewal
  - **Otherwise — case: Not allowed**
    - Licensing API → SaaS Admin Dashboard (reply): 422 Cannot reinstate
  - *Note:* No new token is issued
- **Otherwise — case: Revoke**
  - **Alternative paths — case: Status not PENDING, ACTIVE or SUSPENDED**
    - Licensing API → SaaS Admin Dashboard (reply): 422 Invalid status transition
  - **Otherwise — case: Allowed**
    - Licensing API → SaaS Database: Set status REVOKED
    - **Optional — only when: The license has tokens**
      - Licensing API → SaaS Database: Set revoked_at on its tokens
    - Licensing API → Platform Audit Service: Record audit entry (same transaction)
    - Licensing API → SaaS Admin Dashboard (reply): License revoked
- SaaS Admin Dashboard → SaaS Admin (reply): Show the result

#### 1.9 — Manual token and signing key rotation

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 1.9. **Related:** AD-2. **Requirements:** FR-0.3.

**Participants**

- **SaaS Admin**: actor (person)
- **Port Admin**: actor (person)
- **SaaS Admin Dashboard**: boundary (user interface)
- **Licensing API**: control (service, API, worker or scheduler)
- **License Signer (KMS)**: external system
- **Platform Audit Service**: control (service, API, worker or scheduler)
- **SaaS Database**: database (data store)

**Story**

Two admin-side token jobs live here: producing a token file for a port without internet, and changing the key that signs all tokens.

Manual token. Manual tokens exist only for ACTIVE licenses; any other status returns 422 LICENSE_NOT_ACTIVE. The API builds the claims, including the port's lifecycle status (port_status) and the issue time (iat) that ports use to order tokens, and asks the License Signer to sign them. If the signer is down, no token is issued. The signed token is stored as MANUAL and downloaded as a file. The SaaS Admin delivers it to the Port Admin through any secure channel outside the system, and when the Port Admin confirms receipt, the SaaS Admin marks it delivered, which sets delivered_at.

Key rotation runs in three separate steps so that a port always trusts a key before anything is signed with it. Prepare creates a new key version that is not used yet; its public key ships to every port inside the next application update. Activate makes the new key the signing key once the ports have that update, so new tokens carry the new key id. Retire switches the old key off, but only when no valid token still depends on it.

**Message flow, top to bottom**

- **Alternative paths — case: Generate a manual token file**
  - SaaS Admin → SaaS Admin Dashboard: Request a manual token for a license
  - SaaS Admin Dashboard → Licensing API: Generate manual token
  - Licensing API → SaaS Database: Read license and port
  - **Alternative paths — case: License not ACTIVE**
    - Licensing API → SaaS Admin Dashboard (reply): 422 LICENSE_NOT_ACTIVE
  - **Otherwise — case: License ACTIVE**
    - Licensing API (internal): Build claims (port_public_id, port_status, limits, kid, nbf, iat, exp, jti)
    - Licensing API → License Signer (KMS): Sign with the active key
    - **Alternative paths — case: Signer unavailable**
      - License Signer (KMS) → Licensing API (reply): Error
      - Licensing API → SaaS Admin Dashboard (reply): 503 No token issued
    - **Otherwise — case: Signed**
      - License Signer (KMS) → Licensing API (reply): Signed token
      - Licensing API → SaaS Database: Store token (MANUAL, delivered_at empty)
      - Licensing API → Platform Audit Service: Record audit entry (same transaction)
      - Licensing API → SaaS Admin Dashboard (reply): Token file
      - SaaS Admin → Port Admin (reply): Deliver the file through a secure out-of-band channel
      - Port Admin → SaaS Admin (reply): Confirm receipt
      - SaaS Admin → SaaS Admin Dashboard: Mark as delivered
      - SaaS Admin Dashboard → Licensing API: Set delivered_at
      - Licensing API → SaaS Database: Save delivered_at
- **Otherwise — case: Rotate the signing key**
  - **Alternative paths — case: Step 1 Prepare**
    - SaaS Admin → SaaS Admin Dashboard: Prepare a new key
    - SaaS Admin Dashboard → Licensing API: Prepare key
    - Licensing API → License Signer (KMS): Create key version (PREPARED, not used yet)
    - License Signer (KMS) → Licensing API (reply): kid and public key
    - Licensing API → Platform Audit Service: Record audit entry
    - Licensing API → SaaS Admin Dashboard (reply): Public key to ship
    - *Note:* The public key reaches every port with the next application update
  - **Otherwise — case: Step 2 Activate**
    - SaaS Admin → SaaS Admin Dashboard: Confirm ports have the update, then activate
    - SaaS Admin Dashboard → Licensing API: Activate key
    - Licensing API → License Signer (KMS): Make the new key the signing key (ACTIVE)
    - Licensing API → Platform Audit Service: Record audit entry
    - Licensing API → SaaS Admin Dashboard (reply): New tokens carry the new kid
  - **Otherwise — case: Step 3 Retire**
    - SaaS Admin → SaaS Admin Dashboard: Retire the old key
    - SaaS Admin Dashboard → Licensing API: Retire key
    - Licensing API → SaaS Database: Find unexpired, unrevoked tokens with the old kid
    - **Alternative paths — case: Tokens still use it**
      - Licensing API → SaaS Admin Dashboard (reply): 422 Key still in use
    - **Otherwise — case: None**
      - Licensing API → License Signer (KMS): Retire the old key (RETIRED)
      - Licensing API → Platform Audit Service: Record audit entry
      - Licensing API → SaaS Admin Dashboard (reply): Old key retired

#### 1.10 — Port check-in on the SaaS side

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 1.10. **Related:** AD-5, 1.13. **Requirements:** FR-0.6; NFR-SEC-4.

**Participants**

- **Port Server Check-in Client**: control (service, API, worker or scheduler)
- **Licensing API**: control (service, API, worker or scheduler)
- **License Signer (KMS)**: external system
- **Platform Audit Service**: control (service, API, worker or scheduler)
- **SaaS Database**: database (data store)

**Story**

Every port checks in with the central SaaS once a day. The port always starts the call; the SaaS only answers. This diagram shows what the SaaS does with each check-in.

First it identifies the port by its public id and checks the API credential against the stored hash. A failed check-in is audited as a system event and answered with 401; the port keeps its current token and tries again next cycle. A successful check-in only updates last_check_in_at and is not audited.

If the port itself is suspended or offboarded, the SaaS answers 200 with the statuses and the server time but no token. The same happens when the license is not ACTIVE. The port uses these statuses to switch to read-only mode.

If the license is ACTIVE, the SaaS reuses the latest token while it has more than 14 days left. With 14 days or less, or no token at all, it signs a new one. Because the refresh threshold equals the banner threshold, a port that checks in daily never sees the expiry warning. If the signer is down, the port gets its existing token, or 503 if it has none.

Every successful answer carries port_status and server_time, which the port uses for its mode and its clock check.

**Message flow, top to bottom**

- Port Server Check-in Client → Licensing API: POST /api/v1/ports/check-in (public_id, API credential)
- Licensing API → SaaS Database: Find port and verify the credential hash
- **Alternative paths — case: Unknown port or bad credential**
  - Licensing API → Platform Audit Service: Record failed check-in (SYSTEM)
  - Licensing API → Port Server Check-in Client (reply): 401 Unauthorized
  - Port Server Check-in Client (internal): Keep the current token, retry next cycle
- **Otherwise — case: Credential valid**
  - Licensing API → SaaS Database: Update last_check_in_at
  - **Alternative paths — case: Port SUSPENDED or OFFBOARDED**
    - Licensing API → Port Server Check-in Client (reply): 200 port_status, license_status, server_time (no token)
  - **Otherwise — case: Port ONBOARDING or ACTIVE**
    - Licensing API → SaaS Database: Find the port's current license
    - **Alternative paths — case: License not ACTIVE (SUSPENDED, REVOKED, EXPIRED)**
      - Licensing API → Port Server Check-in Client (reply): 200 port_status, license_status, server_time (no token)
    - **Otherwise — case: License ACTIVE**
      - Licensing API → SaaS Database: Find the latest valid token
      - **Alternative paths — case: Valid token with more than 14 days left**
        - Licensing API (internal): Reuse it
        - Licensing API → Port Server Check-in Client (reply): 200 token, port_status, license_status, server_time
      - **Otherwise — case: No token, or 14 days or less left**
        - Licensing API → License Signer (KMS): Sign a new token (claims carry port_status and iat)
        - **Alternative paths — case: Signer unavailable**
          - Licensing API → Port Server Check-in Client (reply): Existing token if any, otherwise 503
        - **Otherwise — case: Signed**
          - License Signer (KMS) → Licensing API (reply): Signed token
          - Licensing API → SaaS Database: Store token (PULL) and set delivered_at
          - Licensing API → Port Server Check-in Client (reply): 200 token, port_status, license_status, server_time

#### 1.11 — Daily license status roll-over

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 1.11. **Related:** AD-2, SM-1. **Requirements:** FR-0.3, FR-0.5.

**Participants**

- **Scheduler**: control (service, API, worker or scheduler)
- **Licensing API**: control (service, API, worker or scheduler)
- **Platform Audit Service**: control (service, API, worker or scheduler)
- **SaaS Database**: database (data store)

**Story**

Once a day a scheduler on the SaaS side brings every license status in line with its dates. There is no admin session; the audit entries are written as SYSTEM.

Step one expires licenses. Any ACTIVE, SUSPENDED or PENDING license whose end date has passed becomes EXPIRED. Expiring first means the old license is gone before its renewal starts, so a port never has two ACTIVE licenses.

Step two activates renewals. Each PENDING license whose start date has arrived becomes ACTIVE, unless on_hold is set because the current license was suspended, or the port still has another ACTIVE license. A blocked activation is recorded with its reason and tried again the next day.

The scheduler never calls the License Signer. The port receives a token for the new license at its next check-in. Each query only matches licenses still in their old status, so running the job again does no harm.

**Message flow, top to bottom**

- Scheduler → Licensing API: Run the daily license status update
- *Note:* Step 1 expires first, so two ACTIVE licenses never exist for one port
- Licensing API → SaaS Database: Find ACTIVE, SUSPENDED or PENDING licenses with expires_at passed
- SaaS Database → Licensing API (reply): Licenses to expire
- **Loop: Each license**
  - Licensing API → SaaS Database: Set status EXPIRED
  - Licensing API → Platform Audit Service: Record audit entry (SYSTEM, same transaction)
- *Note:* Step 2 activates renewals that reached their start date
- Licensing API → SaaS Database: Find PENDING licenses with valid_from passed
- SaaS Database → Licensing API (reply): Candidates
- **Loop: Each candidate**
  - **Alternative paths — case: on_hold set (cleared by Reinstate)**
    - Licensing API → Platform Audit Service: Record activation blocked (held by suspension)
  - **Otherwise — case: Another ACTIVE license exists**
    - Licensing API → Platform Audit Service: Record activation blocked (active conflict)
  - **Otherwise — case: Free to activate**
    - Licensing API → SaaS Database: Set status ACTIVE
    - Licensing API → Platform Audit Service: Record audit entry (SYSTEM, same transaction)
- Licensing API → Scheduler (reply): Done
- *Note:* No token is signed here. Running the job twice is safe.

#### 1.12 — Annual billing records

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 1.12. **Related:** AD-4. **Requirements:** FR-0.4, FR-0.5.

**Participants**

- **SaaS Admin**: actor (person)
- **Billing Dashboard**: boundary (user interface)
- **Billing API**: control (service, API, worker or scheduler)
- **Platform Audit Service**: control (service, API, worker or scheduler)
- **SaaS Database**: database (data store)

**Story**

ATLANTECH keeps a simple yearly billing record per license. The money itself moves outside ATLANTECH; there is no payment gateway or bank in the system. The SaaS Admin creates the record and later types in what happened.

Creating. The admin picks a license and a subscription year. Only one live transaction (PENDING, FAILED or PAID) may exist for the same license and period; a second one returns 422. The amount and currency come from the license's own snapshot.

Recording the outcome. A paid outcome needs the external reference of the real payment, otherwise it is refused. A failed outcome marks the transaction FAILED, and the same transaction can be paid later.

Refund and cancel. A paid transaction can be refunded, an unpaid one cancelled. Both free the period, so a new transaction can be created for it.

Billing never changes the license. A failed payment does not suspend anything; suspension stays a separate decision of the SaaS Admin. There are no automatic reminders.

**Message flow, top to bottom**

- *Note:* Payment happens outside ATLANTECH. The admin only records the outcome.
- **Alternative paths — case: Create a billing transaction**
  - SaaS Admin → Billing Dashboard: Select license and subscription year
  - Billing Dashboard → Billing API: Create transaction
  - Billing API → SaaS Database: Read license and check live transactions (PENDING, FAILED, PAID) for that period
  - **Alternative paths — case: A live transaction exists**
    - Billing API → Billing Dashboard (reply): 422 DUPLICATE_LIVE_TRANSACTION
  - **Otherwise — case: Period free**
    - Billing API → SaaS Database: Insert transaction PENDING (amount and currency from the license)
    - Billing API → Platform Audit Service: Record audit entry (same transaction)
    - Billing API → Billing Dashboard (reply): Transaction created
- **Otherwise — case: Record a payment outcome**
  - SaaS Admin → Billing Dashboard: Enter outcome and external reference
  - Billing Dashboard → Billing API: Record outcome
  - Billing API → SaaS Database: Read transaction
  - **Alternative paths — case: Status not PENDING or FAILED**
    - Billing API → Billing Dashboard (reply): 422 Invalid status transition
  - **Otherwise — case: Paid without external_reference**
    - Billing API → Billing Dashboard (reply): 422 External reference required
  - **Otherwise — case: Paid**
    - Billing API → SaaS Database: Set PAID, paid_at, external_reference
    - Billing API → Platform Audit Service: Record audit entry (same transaction)
    - Billing API → Billing Dashboard (reply): Payment recorded
  - **Otherwise — case: Failed**
    - Billing API → SaaS Database: Set FAILED (can be retried on the same transaction)
    - Billing API → Platform Audit Service: Record audit entry (same transaction)
    - Billing API → Billing Dashboard (reply): Marked as failed
  - *Note:* A failed payment never suspends the license. Suspension is a separate manual action.
- **Otherwise — case: Refund or cancel**
  - SaaS Admin → Billing Dashboard: Select transaction and refund (PAID) or cancel (PENDING, FAILED)
  - Billing Dashboard → Billing API: Refund or cancel
  - Billing API → SaaS Database: Read transaction
  - **Alternative paths — case: Status does not allow it**
    - Billing API → Billing Dashboard (reply): 422 Invalid status transition
  - **Otherwise — case: Allowed**
    - Billing API → SaaS Database: Set REFUNDED or CANCELLED
    - Billing API → Platform Audit Service: Record audit entry (same transaction)
    - Billing API → Billing Dashboard (reply): Done, the period is free again
- **Otherwise — case: Review billing history**
  - SaaS Admin → Billing Dashboard: Filter by port, license, status, period
  - Billing Dashboard → Billing API: Get transactions
  - Billing API → SaaS Database: Query transactions
  - Billing API → Billing Dashboard (reply): Billing history
- Billing Dashboard → SaaS Admin (reply): Show the result

#### 1.13 — Port license check-in and token upload

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 1.13. **Related:** AD-5, AD-6, SM-3, 1.10. **Requirements:** FR-0.6; NFR-SEC-4.

**Participants**

- **Port Scheduler**: control (service, API, worker or scheduler)
- **Port Admin**: actor (person)
- **Web Dashboard**: boundary (user interface)
- **Port API**: control (service, API, worker or scheduler)
- **License Module**: control (service, API, worker or scheduler)
- **Local License Store**: database (data store)
- **Central SaaS Check-in API**: control (service, API, worker or scheduler)

**Story**

This is the port side of licensing: how the port server gets a token, decides whether to trust it, and works out its mode.

Three things start the flow. A scheduler checks in once a night at a random time. The Port Admin can press Check in now. Or the Port Admin uploads a manual token file. The two admin buttons pass authentication and the Port Admin role check, and they work even in read-only mode because they are how a port recovers.

Check-in. The port calls the SaaS. If there is no answer, or a 401 or 503, the port keeps its token and mode and tries again next time. A 200 answer gives the port's status, the license status, the server time and maybe a new token. The port stores the statuses and resets its trusted clock to the server time.

Accepting a token, in order. The signature, key id, port and expiry must be right. A port stored as OFFBOARDED rejects every token. A token older than the stored one (by issue time) is ignored. A manual token that was issued before the port learned of a suspension or revocation is rejected, so an old file cannot undo a suspension. Otherwise the token is stored, even while the port is still ONBOARDING; accepting a token is separate from permission to operate.

Deciding the mode, in two stages. First the port lifecycle: OFFBOARDED or SUSPENDED gives READ_ONLY, ONBOARDING gives SETUP. Then, for an ACTIVE port, the license: an ACTIVE license with a valid token and no clock rollback gives FULL, anything else gives READ_ONLY with the reason. The result is shown to the Port Admin when the flow started from the dashboard.

**Message flow, top to bottom**

- *Note:* The port works fully offline. A failed check-in only delays the update.
- **Alternative paths — case: Daily check-in**
  - Port Scheduler → License Module: Trigger at a random overnight time
- **Otherwise — case: Check in now**
  - Port Admin → Web Dashboard: Press Check in now
  - Web Dashboard → Port API: POST /admin/license/check-now
  - Port API (internal): Auth and RBAC (Port Admin), allowed in READ_ONLY
  - Port API → License Module: Run check-in
- **Otherwise — case: Manual token upload**
  - Port Admin → Web Dashboard: Upload token file
  - Web Dashboard → Port API: POST /admin/license/upload
  - Port API (internal): Auth and RBAC (Port Admin), allowed in READ_ONLY
  - Port API → License Module: Process the token file
- **Optional — only when: Check-in**
  - License Module → Central SaaS Check-in API: POST /api/v1/ports/check-in
  - **Alternative paths — case: No response, 401 or 503**
    - License Module (internal): Keep token and mode, retry next cycle
  - **Otherwise — case: 200**
    - Central SaaS Check-in API → License Module (reply): port_status, license_status, server_time, token if issued
    - License Module → Local License Store: Store port_status, license_status, status_received_at
    - License Module → Local License Store: Re-baseline max_seen_time to server_time
- **Optional — only when: A token is in hand**
  - License Module → Local License Store: Read stored token, statuses and max_seen_time
  - **Alternative paths — case: Bad signature, unknown kid, another port or expired**
    - License Module (internal): Rejected
  - **Otherwise — case: Stored port_status is OFFBOARDED**
    - License Module (internal): Rejected
  - **Otherwise — case: Token iat older than the stored token**
    - License Module (internal): Ignored
  - **Otherwise — case: Manual token issued before a stored SUSPENDED or REVOKED status**
    - License Module (internal): Rejected
  - **Otherwise — case: Accepted**
    - License Module → Local License Store: Store token, iat, limits and expiry dates (also while ONBOARDING)
    - **Optional — only when: Manual token**
      - License Module → Local License Store: Store port_status from the token claim
- License Module (internal): Trusted time = later of clock and max_seen_time, rollback beyond T flagged
- **Alternative paths — case: Port OFFBOARDED or SUSPENDED**
  - License Module → Local License Store: Mode READ_ONLY (reason: port status)
- **Otherwise — case: Port ONBOARDING**
  - License Module → Local License Store: Mode SETUP
- **Otherwise — case: Port ACTIVE, license ACTIVE, token valid, no rollback**
  - License Module → Local License Store: Mode FULL
- **Otherwise — case: Port ACTIVE, anything else**
  - License Module → Local License Store: Mode READ_ONLY (reason: license, token expiry or clock)
- **Optional — only when: Started from the dashboard**
  - License Module → Port API (reply): Result (accepted, ignored or rejected with reason) and mode
  - Port API → Web Dashboard (reply): Result
  - Web Dashboard → Port Admin (reply): Show result and current mode
- *Note:* Rollback tolerance T is configurable (default 10 min). An offline port clears a stale status with a manual token.

#### 1.14 — Read-only enforcement, limits and license status

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 1.14. **Related:** AD-6, SM-3. **Requirements:** FR-0.2, FR-11.4; NFR-SEC-2.

**Participants**

- **Port User**: actor (person)
- **Port Admin**: actor (person)
- **Web Dashboard**: boundary (user interface)
- **Mobile App**: boundary (user interface)
- **Port API**: control (service, API, worker or scheduler)
- **License Module**: control (service, API, worker or scheduler)
- **Local License Store**: database (data store)
- **Port Database**: database (data store)

**Story**

Once the port has a mode, every request respects it. This diagram shows the guard on each request, the plan limits, the banner and the Port Admin's status page.

The guard. Every request passes the same chain: authentication, role check, app version (mobile), then license mode. The license module computes a trusted time that a rolled-back clock cannot fool, and returns the mode. In READ_ONLY, only actions on one shared allowlist pass: reads and reports, license recovery, login, status updates and acknowledgements on running work, the reject and return actions, actions that remove access, and the Port Admin's safety exception. Everything else gets 423. In SETUP only the setup allowlist passes.

Plan limits. Creating a user, terminal or berth also checks the limit carried in the token. Over the limit, the request fails with 422 PLAN_LIMIT_EXCEEDED and nothing is saved.

The banner. The web dashboard asks GET /api/v1/license/state; the mobile app reads the same values from /system/info, together with the port name and the minimum app version. In READ_ONLY both show a read-only banner and the app hides its create buttons. In FULL mode, when the token has 14 days or less left, both show how many days remain.

License status. The Port Admin can open a status page with the mode, the statuses, the limits, the token expiry and the license expiry, and from there press Check in now or upload a token.

**Message flow, top to bottom**

- Port User → Web Dashboard: Perform an action
- Web Dashboard → Port API: Request
- Port API (internal): auth, RBAC, app-version, then license-mode
- Port API → License Module: Get current mode
- License Module → Local License Store: Read mode, statuses, token expiry, max_seen_time
- License Module (internal): Trusted time and rollback check (T default 10 min)
- License Module → Port API (reply): Mode
- **Alternative paths — case: READ_ONLY and action not on the read-only allowlist**
  - Port API → Web Dashboard (reply): 423 LICENSE_READ_ONLY
- **Otherwise — case: SETUP and action not on the setup allowlist**
  - Port API → Web Dashboard (reply): 423 Port still in setup
- **Otherwise — case: Allowed**
  - Port API (internal): Continue to the controller
- *Note:* Read-only allowlist: reads and reports, license recovery, login, status updates and acknowledgements, reject and return actions, removing access, Port Admin safety exception
- **Optional — only when: Action creates a user, terminal or berth**
  - Port API → License Module: Check the plan limit
  - License Module → Local License Store: Read the limit from the token
  - License Module → Port Database: Count active records
  - **Alternative paths — case: Limit reached**
    - Port API → Web Dashboard (reply): 422 PLAN_LIMIT_EXCEEDED (nothing saved)
  - **Otherwise — case: Within the limit**
    - Port API (internal): Continue the creation
- **Alternative paths — case: Web dashboard loads**
  - Web Dashboard → Port API: GET /api/v1/license/state
  - Port API → License Module: Mode and token_warning_days_left
  - Port API → Web Dashboard (reply): mode, token_warning_days_left
- **Otherwise — case: Mobile app launches or syncs**
  - Mobile App → Port API: GET /api/v1/system/info
  - Port API → License Module: Mode and token_warning_days_left
  - Port API → Mobile App (reply): port_public_id, port name, license_mode, token_warning_days_left, min_app_version
- **Alternative paths — case: READ_ONLY**
  - Web Dashboard → Port User (reply): Read-only banner
  - Mobile App → Port User (reply): Read-only banner, create buttons hidden
- **Otherwise — case: FULL and token expires in 14 days or less**
  - Web Dashboard → Port User (reply): Token expires in X days, check the connection or upload a token
  - Mobile App → Port User (reply): Same warning
- Port Admin → Web Dashboard: Open License Status
- Web Dashboard → Port API: Get license status (Port Admin)
- Port API → License Module: Read license data
- License Module → Local License Store: Mode, statuses, limits, token and license expiry, last check-in
- Port API → Web Dashboard (reply): License status
- Web Dashboard → Port Admin (reply): Status with Check in now and Upload token

### Activity diagrams of category 1

#### AD-1 — Port onboarding and provisioning

**Code:** `activity-diagrams-v3/ATLANTECH_Activity_Diagrams.md`, diagram AD-1. **Related:** 1.3, 1.5, 1.6, SM-2, SM-3. **Requirements:** FR-0.1, FR-0.3; NFR-SEC-4, NFR-EXT-1.

**Swimlanes:** SaaS Admin, ATLANTECH Support Engineer, Port IT Administrator, Port Admin, Port Server, Central SaaS.

**Story**

This activity diagram follows a new port from its registration to the moment it can operate. Five lanes share the work: the SaaS Admin, the ATLANTECH Support Engineer, the port's IT administrator, the Port Admin, the port server and the central SaaS.

The SaaS Admin registers the port in ONBOARDING, issues its API credential (only a hash is kept), hands the bootstrap values over through a secure channel and issues the first license. No token is signed at that moment.

Two branches then run in parallel. Port IT prepares the network, firewall, split DNS, VPN and MDM. In the other branch Port IT opens a time-boxed onboarding session; the Support Engineer deploys the signed build, and a build whose signature fails is re-deployed. Port IT generates the key and CSR on the server and submits it; the Support Engineer validates it and signs it with the offline Root CA, records the certificate in the support log outside ATLANTECH, and Port IT installs it. A bad CSR is fixed and regenerated.

When both branches are done, the Support Engineer bootstraps the instance and seeds the first Port Admin with a one-time password. The port gets its first token by check-in or by manual upload. A valid token is stored even though the port is still ONBOARDING, and the port enters SETUP mode: the Port Admin signs in, must change the password, and sets up users, configuration, berths and resources, but no operational records.

When ready, the Port Admin confirms readiness to the SaaS Admin, who runs the activation checklist. Missing items keep the port ONBOARDING until Port IT completes them. A complete checklist sets the port ACTIVE, records the confirmation in the audit, enables operations, and Port IT closes the onboarding session.

**Step-by-step flow** (each step lists where it goes next; END is a final node)

- **START** start → A1 "Register port: ONBOARDING, public_id, UN/LOCODE, governorate, server endpoint"
- **A1** [SaaS Admin] Register port: ONBOARDING, public_id, UN/LOCODE, governorate, server endpoint → A2 "Issue port API credential - only its hash is stored"
- **A2** [SaaS Admin] Issue port API credential - only its hash is stored → A12 "Hand over credential and bootstrap values through a secure out-of-band channel"
- **A12** [SaaS Admin] Hand over credential and bootstrap values through a secure out-of-band channel → A3 "Issue first license - AD-2 (no token at issue)"
- **A3** [SaaS Admin] Issue first license - AD-2 (no token at issue) → FK1 (fork/join bar)
- **FK1** Fork: in parallel → P1 "Prepare LAN, firewall, split DNS, VPN and MDM - AD-19"; P7 "Open time-boxed onboarding session"
- **P1** [Port IT Administrator] Prepare LAN, firewall, split DNS, VPN and MDM - AD-19 → JN1 (fork/join bar)
- **P7** [Port IT Administrator] Open time-boxed onboarding session → P0 "Deploy the signed build"
- **JN1** Join: waits for P1, P3 → E3 "Bootstrap instance: port_public_id, license public key, API credential; seed the first Port Admin with a one-time password, handed over out of band"
- **P0** [ATLANTECH Support Engineer] Deploy the signed build → DS "Signature valid?"
- **E3** [ATLANTECH Support Engineer] Bootstrap instance: port_public_id, license public key, API credential; seed the first Port Admin with a one-time password, handed over out of band → D1 "Outbound internet available?"
- **DS** [ATLANTECH Support Engineer] Decision "Signature valid?": "No" → P8 "Re-deploy a correctly signed build"; "Yes" → P2 "Generate server private key and CSR on the server"
- **D1** [Port Admin] Decision "Outbound internet available?": "Yes" → A4 "Initial check-in while port is ONBOARDING - AD-5"; "No" → A5 "Upload manual token file - AD-6"
- **P8** [ATLANTECH Support Engineer] Re-deploy a correctly signed build → P0 "Deploy the signed build"
- **P2** [Port IT Administrator] Generate server private key and CSR on the server → P4 "Submit CSR to ATLANTECH"
- **A4** [Port Server] Initial check-in while port is ONBOARDING - AD-5 → A6 "Validate token: signature, kid, port, nbf and expiry, iat - AD-6"
- **A5** [Port Admin] Upload manual token file - AD-6 → A6 "Validate token: signature, kid, port, nbf and expiry, iat - AD-6"
- **P4** [Port IT Administrator] Submit CSR to ATLANTECH → V1 "Validate CSR and port identity"
- **A6** [Port Server] Validate token: signature, kid, port, nbf and expiry, iat - AD-6 → D2 "Token valid?"
- **V1** [ATLANTECH Support Engineer] Validate CSR and port identity → DV "CSR and identity valid?"
- **D2** [Port Server] Decision "Token valid?": "No" → A10 "Reject token and show reason"; "Yes" → A7 "Store token - also while ONBOARDING; mode SETUP"
- **DV** [ATLANTECH Support Engineer] Decision "CSR and identity valid?": "No" → P5 "Fix and regenerate CSR"; "Yes" → E2 "Sign CSR with the offline Root CA"
- **A10** [Port Server] Reject token and show reason → D1 "Outbound internet available?"
- **A7** [Port Server] Store token - also while ONBOARDING; mode SETUP → A8 "Sign in with the one-time password; forced password change on first login; set up users, port config, berths and resources"
- **P5** [Port IT Administrator] Fix and regenerate CSR → P2 "Generate server private key and CSR on the server"
- **E2** [ATLANTECH Support Engineer] Sign CSR with the offline Root CA → E4 "Record certificate ID, signer and date in the support log (outside ATLANTECH, FW-07)"
- **A8** [Port Admin] Sign in with the one-time password; forced password change on first login; set up users, port config, berths and resources → R3 "Confirm port readiness to the SaaS Admin (out of band)"
- **E4** [ATLANTECH Support Engineer] Record certificate ID, signer and date in the support log (outside ATLANTECH, FW-07) → P3 "Install signed TLS certificate on the server"
- **R3** [Port Admin] Confirm port readiness to the SaaS Admin (out of band) → R4 "Run the activation checklist: token installed, essential settings, berths and resources, Port Admin account"
- **P3** [Port IT Administrator] Install signed TLS certificate on the server → JN1 (fork/join bar)
- **R4** [SaaS Admin] Run the activation checklist: token installed, essential settings, berths and resources, Port Admin account → D8 "Checklist complete?"
- **D8** [Central SaaS] Decision "Checklist complete?": "No" → A11 "Keep port ONBOARDING and show the missing items"; "Yes" → A9 "Set port ACTIVE; record the Port Admin readiness confirmation in the audit"
- **A11** [Central SaaS] Keep port ONBOARDING and show the missing items → P6 "Complete the missing onboarding items"
- **A9** [Central SaaS] Set port ACTIVE; record the Port Admin readiness confirmation in the audit → A13 "Enable operational use - mode FULL at the next check-in"
- **P6** [Port IT Administrator] Complete the missing onboarding items → R4 "Run the activation checklist: token installed, essential settings, berths and resources, Port Admin account"
- **A13** [Central SaaS] Enable operational use - mode FULL at the next check-in → P9 "Close the onboarding session"
- **P9** [Port IT Administrator] Close the onboarding session → END

**Rules stated as notes**

- The registry record can be updated later, for example the server endpoint (attached to A1)
- Central signing is done by the Support Engineer with the offline Root CA (attached to E2)
- No secret is stored as recoverable plaintext (attached to E3)
- License validity and port lifecycle are separate: operations start only after ACTIVE (attached to A7)
- SETUP allows only first Port Admin and setup users, port configuration, berths and resources - no operational records (attached to A8)

#### AD-2 — License issue, renewal and token signing

**Code:** `activity-diagrams-v3/ATLANTECH_Activity_Diagrams.md`, diagram AD-2. **Related:** 1.6, 1.7, 1.9, 1.11, SM-1. **Requirements:** FR-0.2, FR-0.3, FR-0.5.

**Swimlanes:** SaaS Admin, Central SaaS, License Signer / KMS, Scheduler.

**Story**

This diagram has four entry points: an admin action, a token request, the daily schedule, and a key rotation.

Admin action. The SaaS Admin picks a port and a plan. A second PENDING license, or a second ACTIVE one when issuing, is rejected. The plan limits, price and currency are copied into the license as its own snapshot, and the dates are set; a renewal always starts when the current license ends. Invalid dates are rejected. An issued license is ACTIVE if its start has passed, otherwise PENDING; a renewal is always PENDING. The license and its audit entry are saved in one transaction, and no token is signed. Every rejected attempt is audited, and the admin may retry. Billing is created separately and manually.

Token request. When the check-in flow (AD-5) or a manual token (AD-6) needs a token, the License Signer builds the claims (port id, port status, limits, key id, not-before, issued-at, expiry and token id) and signs them with the key kept in the KMS. If signing fails, no token is issued and the license is not touched.

Daily schedule. The scheduler first expires ACTIVE, SUSPENDED and PENDING licenses whose end date has passed, then activates PENDING licenses whose start has arrived, provided they are not on hold and the port has no other ACTIVE license. Every change is a SYSTEM audit entry.

Key rotation. A new key pair is created as PREPARED and its public key ships to ports with the next application update. Once ports run that update, the new key becomes active and signs new tokens. The old key is retired only when no valid token still uses it.

**Step-by-step flow** (each step lists where it goes next; END is a final node)

- **START** start → D0 "Triggering event?"
- **D0** Decision "Triggering event?": "Admin action" → A1 "Select port and plan"; "Token requested by AD-5 check-in or AD-6 manual token" → K1 "Build claims: port_public_id, port_status, limits, kid, nbf, iat, exp, jti"; "Daily schedule" → S1 "Run daily license roll-over"; "Key rotation" → R1 "Start signing-key rotation"
- **A1** [SaaS Admin] Select port and plan → D8 "Another PENDING license for the port?"
- **K1** [License Signer / KMS] Build claims: port_public_id, port_status, limits, kid, nbf, iat, exp, jti → K2 "Sign with the Ed25519 private key held in the KMS"
- **S1** [Scheduler] Run daily license roll-over → C1 "Daily date check on all licenses"
- **R1** [SaaS Admin] Start signing-key rotation → R5 "Create new key pair with a new kid"
- **D8** [Central SaaS] Decision "Another PENDING license for the port?": "Yes" → A2 "Reject the conflicting license"; "No" → D1 "Operation?"
- **K2** [License Signer / KMS] Sign with the Ed25519 private key held in the KMS → D6 "Signing succeeded?"
- **C1** [Central SaaS] Daily date check on all licenses → C3 "Expire ACTIVE, SUSPENDED and PENDING licenses past expires_at"
- **R5** [License Signer / KMS] Create new key pair with a new kid → R4 "Key PREPARED - public key ships with the next application update"
- **A2** [Central SaaS] Reject the conflicting license → A15 "Audit the rejected attempt - state unchanged"
- **D1** [SaaS Admin] Decision "Operation?": "Issue" → D2 "Port already has an ACTIVE license?"; "Renew early" → A3 "Snapshot the package limits, annual price and currency"
- **D6** [License Signer / KMS] Decision "Signing succeeded?": "No" → K3 "No token issued - return error to the caller; license unchanged"; "Yes" → K4 "Return signed token to the caller"
- **C3** [Central SaaS] Expire ACTIVE, SUSPENDED and PENDING licenses past expires_at → D10 "PENDING license ready to activate?"
- **R4** [License Signer / KMS] Key PREPARED - public key ships with the next application update → R6 "Activate the new key once ports run the update"
- **A15** [Central SaaS] Audit the rejected attempt - state unchanged → D9 "Retry later?"
- **D2** [Central SaaS] Decision "Port already has an ACTIVE license?": "Yes" → A2 "Reject the conflicting license"; "No" → A3 "Snapshot the package limits, annual price and currency"
- **A3** [Central SaaS] Snapshot the package limits, annual price and currency → A4 "Set valid_from and expires_at; a renewal starts at the current license's expires_at"
- **K3** [License Signer / KMS] No token issued - return error to the caller; license unchanged → END
- **K4** [License Signer / KMS] Return signed token to the caller → END
- **D10** [Central SaaS] Decision "PENDING license ready to activate?": "Yes" → C2 "Set ACTIVE"; "No" → C5 "No change - log the skipped transition"
- **R6** [SaaS Admin] Activate the new key once ports run the update → R2 "Sign new tokens with the new key and its kid"
- **D9** [SaaS Admin] Decision "Retry later?": "Yes" → A1 "Select port and plan"; "No" → END
- **A4** [Central SaaS] Set valid_from and expires_at; a renewal starts at the current license's expires_at → D3 "expires_at after valid_from?"
- **C2** [Central SaaS] Set ACTIVE → C4 "Record SYSTEM audit entry"
- **C5** [Central SaaS] No change - log the skipped transition → C4 "Record SYSTEM audit entry"
- **R2** [Central SaaS] Sign new tokens with the new key and its kid → R7 "Retire the old key when no valid token uses its kid"
- **D3** [Central SaaS] Decision "expires_at after valid_from?": "No" → A5 "Return validation error"; "Yes" → D4 "Operation?"
- **C4** [Central SaaS] Record SYSTEM audit entry → END
- **R7** [SaaS Admin] Retire the old key when no valid token uses its kid → R3 "Record platform audit entry"
- **A5** [Central SaaS] Return validation error → A15 "Audit the rejected attempt - state unchanged"
- **D4** [Central SaaS] Decision "Operation?": "Issue" → D5 "valid_from in the future?"; "Renew early" → A6 "Target status PENDING"
- **R3** [Central SaaS] Record platform audit entry → END
- **D5** [Central SaaS] Decision "valid_from in the future?": "Yes" → A6 "Target status PENDING"; "No" → A7 "Target status ACTIVE"
- **A6** [Central SaaS] Target status PENDING → A11 "In one transaction: save license and audit entry - no token"
- **A7** [Central SaaS] Target status ACTIVE → A11 "In one transaction: save license and audit entry - no token"
- **A11** [Central SaaS] In one transaction: save license and audit entry - no token → END

**Rules stated as notes**

- Token expiry is never after the license expiry (attached to K1)
- Each licence keeps one plan snapshot - no plan switching or proration during a licence (attached to A1)
- The port verifies kid, signature, port, nbf, expiry and iat - AD-5, AD-6 (attached to K2)
- Ready = valid_from reached, not on hold and no other ACTIVE license. A held PENDING license waits for Reinstate - AD-3 (attached to D10)
- The billing transaction is created manually by the SaaS Admin - AD-4 (attached to A11)

#### AD-3 — License and port status changes

**Code:** `activity-diagrams-v3/ATLANTECH_Activity_Diagrams.md`, diagram AD-3. **Related:** 1.4, 1.8, SM-1, SM-2. **Requirements:** FR-0.1, FR-0.3, FR-0.5.

**Swimlanes:** SaaS Admin, Central SaaS, Port Server.

**Story**

The SaaS Admin can change the status of a license or of a whole port. This diagram shows each action and how the port finds out.

Every action is first checked against the allowed transitions; a forbidden one is rejected and audited.

License actions. Suspend sets the license SUSPENDED and sets on_hold on any PENDING renewal. Reinstate needs the license to be within its dates with no other ACTIVE license; it sets ACTIVE and clears on_hold. Revoke sets REVOKED and revokes the license's tokens. A single token can also be revoked on its own as a security action; the reason is recorded in the platform audit details.

Port actions. Suspend sets the port SUSPENDED and does not touch its licenses or tokens. Reinstate brings it back to ACTIVE through the activation checklist. Offboard sets OFFBOARDED, keeps the record, and revokes the port's licenses and tokens. Rotating the API credential creates a new secret that is delivered to the port.

Every change is audited and travels to the port only on the port's own next check-in. The port then recomputes its mode: a suspended port or license, or a revoked license, gives READ_ONLY with the reason; OFFBOARDED is stored and blocks new operations while history stays visible; FULL is kept or restored only when both the license and the port are ACTIVE.

**Step-by-step flow** (each step lists where it goes next; END is a final node)

- **START** start → A1 "Choose status action for a port or license"
- **A1** [SaaS Admin] Choose status action for a port or license → S0 "Validate current state and requested transition"
- **S0** [Central SaaS] Validate current state and requested transition → D4 "Transition allowed?"
- **D4** [Central SaaS] Decision "Transition allowed?": "No" → A13 "Reject with reason and record audit entry"; "Yes" → D1 "Action?"
- **A13** [Central SaaS] Reject with reason and record audit entry → END
- **D1** [SaaS Admin] Decision "Action?": "Suspend license" → A2 "Set license SUSPENDED; set on_hold on the port's PENDING renewal"; "Reinstate license" → D5 "Within validity dates, no other ACTIVE license?"; "Revoke license" → A4 "Set license REVOKED and revoke its tokens"; "Revoke a specific token" → A5 "Set revoked_at on that specific token and record the security reason in the platform audit details"; "Suspend port" → A6 "Set port SUSPENDED"; "Reinstate port" → A15 "Set port back to ACTIVE - Reinstate via the activation checklist"; "Offboard port" → A7 "Set port OFFBOARDED - record is never deleted"; "Rotate API credential" → A8 "Generate new API credential and store its hash"
- **A2** [Central SaaS] Set license SUSPENDED; set on_hold on the port's PENDING renewal → A9 "Record platform audit entry"
- **D5** [Central SaaS] Decision "Within validity dates, no other ACTIVE license?": "No - renew instead" → A13 "Reject with reason and record audit entry"; "Yes" → A3 "Set license back to ACTIVE and clear on_hold on the PENDING renewal"
- **A4** [Central SaaS] Set license REVOKED and revoke its tokens → A9 "Record platform audit entry"
- **A5** [Central SaaS] Set revoked_at on that specific token and record the security reason in the platform audit details → A9 "Record platform audit entry"
- **A6** [Central SaaS] Set port SUSPENDED → A9 "Record platform audit entry"
- **A15** [Central SaaS] Set port back to ACTIVE - Reinstate via the activation checklist → A9 "Record platform audit entry"
- **A7** [Central SaaS] Set port OFFBOARDED - record is never deleted → A14 "Revoke the port's licenses and their tokens; check-in still answered with OFFBOARDED"
- **A8** [Central SaaS] Generate new API credential and store its hash → A12 "Deliver new credential to the port"
- **A9** [Central SaaS] Record platform audit entry → A10 "Return the new status and reason at the port's next check-in"
- **A3** [Central SaaS] Set license back to ACTIVE and clear on_hold on the PENDING renewal → A9 "Record platform audit entry"
- **A14** [Central SaaS] Revoke the port's licenses and their tokens; check-in still answered with OFFBOARDED → A9 "Record platform audit entry"
- **A12** [SaaS Admin] Deliver new credential to the port → P5 "Configure new credential for future check-ins"
- **A10** [Central SaaS] Return the new status and reason at the port's next check-in → P1 "Port initiates check-in and receives status - within 1 day, or at token expiry if offline"
- **P5** [Port Server] Configure new credential for future check-ins → END
- **P1** [Port Server] Port initiates check-in and receives status - within 1 day, or at token expiry if offline → P2 "Recompute mode - AD-5"
- **P2** [Port Server] Recompute mode - AD-5 → D3 "New status?"
- **D3** [Port Server] Decision "New status?": "Port or license SUSPENDED, or license REVOKED" → P3 "Switch to READ_ONLY with reason - the stored token cannot authorize new writes"; "OFFBOARDED" → P6 "Persist OFFBOARDED: block new operations, keep history viewable for audit"; "License and port ACTIVE" → P4 "Stay in or restore FULL mode - only when license and port are both ACTIVE"
- **P3** [Port Server] Switch to READ_ONLY with reason - the stored token cannot authorize new writes → END
- **P6** [Port Server] Persist OFFBOARDED: block new operations, keep history viewable for audit → END
- **P4** [Port Server] Stay in or restore FULL mode - only when license and port are both ACTIVE → END

**Rules stated as notes**

- Suspend and reinstate never touch tokens, for a license or a port. Offboarding and license revoke do revoke tokens. (attached to A5)
- Suspension is always a manual SaaS Admin action - no billing-driven suspension (attached to A2)
- Expiry is handled in AD-5 and shown as a different reason from admin suspension (attached to D3)
- The SaaS never connects into the port - status travels only on port-initiated check-in (attached to P1)

#### AD-4 — Annual subscription billing

**Code:** `activity-diagrams-v3/ATLANTECH_Activity_Diagrams.md`, diagram AD-4. **Related:** 1.12. **Requirements:** FR-0.4, FR-0.5.

**Swimlanes:** SaaS Admin, Central SaaS.

**Story**

Billing in ATLANTECH is a record of payments that happen outside the system. There is no bank or gateway in the flow, no scheduler and no reminders.

Create. The SaaS Admin creates a transaction for a license and a subscription year. If a live one (PENDING, FAILED or PAID) already exists for the same period, the request is rejected with 422. Otherwise it is saved as PENDING with the period, amount and currency.

Outcome. When the payment result is known, the admin enters it. A PAID outcome needs the external reference of the real payment, or it is rejected. A FAILED outcome is stored and the same transaction can later be paid.

Cancel and refund. An unpaid transaction can be cancelled and a paid one refunded. Both free the period, so a new transaction can be created for it.

Every change is audited. Billing never changes the license: paying does not activate it and a failed payment does not suspend it.

**Step-by-step flow** (each step lists where it goes next; END is a final node)

- **START** start → D0 "Triggering event?"
- **D0** Decision "Triggering event?": "Create" → A1 "Create billing transaction for the subscription year"; "Enter outcome" → A4 "Enter the payment outcome received outside ATLANTECH"; "Cancel" → A8 "Cancel transaction before payment"; "Refund" → A7 "Refund a paid transaction"; "Review history" → A10 "Review billing history by port and license"
- **A1** [SaaS Admin] Create billing transaction for the subscription year → D1 "Live transaction for this license and period?"
- **A4** [SaaS Admin] Enter the payment outcome received outside ATLANTECH → D2 "Outcome?"
- **A8** [SaaS Admin] Cancel transaction before payment → A12 "Set CANCELLED"
- **A7** [SaaS Admin] Refund a paid transaction → A9 "Set REFUNDED"
- **A10** [SaaS Admin] Review billing history by port and license → END
- **D1** [Central SaaS] Decision "Live transaction for this license and period?": "Yes" → A2 "Reject with 422"; "No" → A3 "Save transaction PENDING: period_start, period_end, amount, currency"
- **D2** [Central SaaS] Decision "Outcome?": "PAID" → D12 "external_reference entered?"; "FAILED" → A11 "Set FAILED - may be retried on the same transaction"
- **A12** [Central SaaS] Set CANCELLED → A14 "Record platform audit entry"
- **A9** [Central SaaS] Set REFUNDED → A14 "Record platform audit entry"
- **A2** [Central SaaS] Reject with 422 → END
- **A3** [Central SaaS] Save transaction PENDING: period_start, period_end, amount, currency → A14 "Record platform audit entry"
- **D12** [Central SaaS] Decision "external_reference entered?": "No" → A20 "Reject with 422"; "Yes" → A6 "Set PAID, paid_at and external_reference"
- **A11** [Central SaaS] Set FAILED - may be retried on the same transaction → A14 "Record platform audit entry"
- **A14** [Central SaaS] Record platform audit entry → END
- **A20** [Central SaaS] Reject with 422 → END
- **A6** [Central SaaS] Set PAID, paid_at and external_reference → A14 "Record platform audit entry"

**Rules stated as notes**

- Billing status is separate from license status - PAID never activates a license and FAILED never suspends one (attached to A6)
- Refunded or cancelled transactions free the period for a new transaction (attached to A9)

#### AD-5 — Daily license check-in and license mode

**Code:** `activity-diagrams-v3/ATLANTECH_Activity_Diagrams.md`, diagram AD-5. **Related:** 1.10, 1.13, SM-3. **Requirements:** FR-0.6; NFR-SEC-4.

**Swimlanes:** Port Admin, Port Server, Central SaaS.

**Story**

This diagram shows how a port keeps its license up to date and how it decides its mode.

Local check. Every protected request, and a periodic local check, verifies the stored token and statuses against a trusted clock. If the token is valid and both the port and the license are ACTIVE, the request goes on. Otherwise it is blocked and the mode is recomputed.

Check-in. A scheduler fires once a night at a random time, or the Port Admin presses Check now. The port calls the SaaS. If the SaaS cannot be reached, the port keeps everything and tries again; losing internet alone never stops work. The SaaS authenticates the credential, and a failure returns 401 and is audited. An offboarded or suspended port gets its status and the server time, but no token. Otherwise the SaaS finds the license in effect: a non-active license returns its status only, and a PENDING one returns its start date. For an ACTIVE license the existing token is reused when more than 14 days remain; otherwise a token is signed lazily, and if signing fails the port gets its still-valid token or 503.

Accepting the answer. The port verifies the signature, the key and the port id, ignores a token older than the stored one, resets its trusted time to the server time, and stores the token, limits, port_status, license_status and status_received_at.

Deciding the mode, port first. OFFBOARDED or SUSPENDED gives READ_ONLY (reason PORT_OFFBOARDED or PORT_SUSPENDED). ONBOARDING gives SETUP. For an ACTIVE port the license decides: expired, suspended, revoked or not yet in effect gives READ_ONLY with that reason (TOKEN_EXPIRED, SUSPENDED, REVOKED or LICENSE_NOT_YET_IN_EFFECT); ACTIVE and valid gives FULL, restored if it was read-only before. A banner shows the read-only reason, or a warning when the token has 14 days or less left.

**Step-by-step flow** (each step lists where it goes next; END is a final node)

- **START** start → D0 "Triggering event?"
- **D0** Decision "Triggering event?": "Protected request or local periodic check" → L1 "Validate stored token and stored statuses locally against trusted time"; "Daily schedule" → A2 "Scheduler fires at a randomised overnight time"; "Admin check now" → A1 "Press Check now"
- **L1** [Port Server] Validate stored token and stored statuses locally against trusted time → D10 "Token valid, port and license ACTIVE?"
- **A2** [Port Server] Scheduler fires at a randomised overnight time → A3 "Port sends outbound check-in with its API credential"
- **A1** [Port Admin] Press Check now → A3 "Port sends outbound check-in with its API credential"
- **D10** [Port Server] Decision "Token valid, port and license ACTIVE?": "Yes" → END; "No - request blocked" → D13 "Port lifecycle?"
- **A3** [Port Server] Port sends outbound check-in with its API credential → D1 "SaaS reachable?"
- **D13** [Port Server] Decision "Port lifecycle?": "OFFBOARDED" → A25 "READ_ONLY, reason PORT_OFFBOARDED; history stays viewable"; "SUSPENDED" → A29 "READ_ONLY, reason PORT_SUSPENDED"; "ONBOARDING" → A26 "Mode SETUP - setup allowlist only"; "ACTIVE" → D6 "License state?"
- **D1** [Port Server] Decision "SaaS reachable?": "No" → A4 "Keep current token and statuses, retry next cycle"; "Yes" → A5 "Authenticate port credential"
- **A25** [Port Server] READ_ONLY, reason PORT_OFFBOARDED; history stays viewable → A18 "Show read-only banner with the reason"
- **A29** [Port Server] READ_ONLY, reason PORT_SUSPENDED → A18 "Show read-only banner with the reason"
- **A26** [Port Server] Mode SETUP - setup allowlist only → A20 "View license status, mode, reason and last check-in"
- **D6** [Port Server] Decision "License state?": "EXPIRED or token expired" → A14 "READ_ONLY, reason TOKEN_EXPIRED"; "SUSPENDED or REVOKED" → A21 "READ_ONLY, reason SUSPENDED or REVOKED"; "PENDING not yet in effect" → A27 "READ_ONLY, reason LICENSE_NOT_YET_IN_EFFECT"; "ACTIVE and valid" → D7 "Was READ_ONLY before?"
- **A4** [Port Server] Keep current token and statuses, retry next cycle → L1 "Validate stored token and stored statuses locally against trusted time"
- **A5** [Central SaaS] Authenticate port credential → D2 "Credential valid?"
- **A18** [Port Server] Show read-only banner with the reason → A20 "View license status, mode, reason and last check-in"
- **A20** [Port Admin] View license status, mode, reason and last check-in → END
- **A14** [Port Server] READ_ONLY, reason TOKEN_EXPIRED → A18 "Show read-only banner with the reason"
- **A21** [Port Server] READ_ONLY, reason SUSPENDED or REVOKED → A18 "Show read-only banner with the reason"
- **A27** [Port Server] READ_ONLY, reason LICENSE_NOT_YET_IN_EFFECT → A18 "Show read-only banner with the reason"
- **D7** [Port Server] Decision "Was READ_ONLY before?": "Yes" → A15 "Restore FULL mode"; "No" → A16 "Keep FULL mode"
- **D2** [Central SaaS] Decision "Credential valid?": "No" → A6 "Return 401 and record SYSTEM audit entry"; "Yes" → D12 "Port status?"
- **A15** [Port Server] Restore FULL mode → D8 "14 days or less to token expiry?"
- **A16** [Port Server] Keep FULL mode → D8 "14 days or less to token expiry?"
- **A6** [Central SaaS] Return 401 and record SYSTEM audit entry → END
- **D12** [Central SaaS] Decision "Port status?": "OFFBOARDED" → A24 "Return port_status OFFBOARDED, server_time - no token"; "SUSPENDED" → A22 "Return status and reason, server_time - no token"; "ONBOARDING or ACTIVE" → A7 "Find the license in effect; update last_check_in_at"
- **D8** [Port Server] Decision "14 days or less to token expiry?": "Yes" → A17 "Show token-expiry warning banner"; "No" → A20 "View license status, mode, reason and last check-in"
- **A24** [Central SaaS] Return port_status OFFBOARDED, server_time - no token → A23 "Persist port_status, license_status and status_received_at"
- **A22** [Central SaaS] Return status and reason, server_time - no token → A23 "Persist port_status, license_status and status_received_at"
- **A7** [Central SaaS] Find the license in effect; update last_check_in_at → D11 "License in effect?"
- **A17** [Port Server] Show token-expiry warning banner → A20 "View license status, mode, reason and last check-in"
- **A23** [Port Server] Persist port_status, license_status and status_received_at → D13 "Port lifecycle?"
- **D11** [Central SaaS] Decision "License in effect?": "SUSPENDED, REVOKED or EXPIRED" → A22 "Return status and reason, server_time - no token"; "Only PENDING before valid_from" → A28 "Return PENDING status and valid_from - no token"; "ACTIVE" → D3 "Valid token, over 14 days left?"
- **A28** [Central SaaS] Return PENDING status and valid_from - no token → A23 "Persist port_status, license_status and status_received_at"
- **D3** [Central SaaS] Decision "Valid token, over 14 days left?": "Yes" → A19 "Return token, license status, port_status and server_time"; "No" → A8 "Sign token lazily - first token of an ACTIVE license, or refresh - AD-2"
- **A19** [Central SaaS] Return token, license status, port_status and server_time → A9 "Verify Ed25519 signature with the key for its kid"
- **A8** [Central SaaS] Sign token lazily - first token of an ACTIVE license, or refresh - AD-2 → D14 "Signing succeeded?"
- **A9** [Port Server] Verify Ed25519 signature with the key for its kid → D4 "Signature and port_public_id valid?"
- **D14** [Central SaaS] Decision "Signing succeeded?": "Yes" → A19 "Return token, license status, port_status and server_time"; "No" → A30 "Return existing token if still valid, else 503"
- **D4** [Port Server] Decision "Signature and port_public_id valid?": "No" → A10 "Discard token, log it, keep current token"; "Yes" → D9 "iat newer than the stored token?"
- **A30** [Central SaaS] Return existing token if still valid, else 503 → END
- **A10** [Port Server] Discard token, log it, keep current token → END
- **D9** [Port Server] Decision "iat newer than the stored token?": "No" → A10 "Discard token, log it, keep current token"; "Yes" → A12 "Re-baseline trusted time to server_time and advance max_seen_time"
- **A12** [Port Server] Re-baseline trusted time to server_time and advance max_seen_time → A13 "Persist token, iat, limits, token_expires_at, last successful check-in"
- **A13** [Port Server] Persist token, iat, limits, token_expires_at, last successful check-in → A23 "Persist port_status, license_status and status_received_at"

**Rules stated as notes**

- Internet loss alone never stops work; token expiry forces READ_ONLY (attached to A4)
- FULL needs license ACTIVE and port ACTIVE; a suspended port is reinstated through the activation checklist (attached to D13)

#### AD-6 — Manual license token and read-only enforcement

**Code:** `activity-diagrams-v3/ATLANTECH_Activity_Diagrams.md`, diagram AD-6. **Related:** 1.13, 1.14, SM-3. **Requirements:** FR-0.2, FR-11.4; NFR-SEC-2.

**Swimlanes:** SaaS Admin, Port Admin, Office or Mobile User, Port Server.

**Story**

Two things are covered here: how a port without internet gets a license token, and how read-only mode is enforced on every request.

Manual token. The SaaS Admin can generate a manual token only for an ACTIVE license; any other status is refused with 422. The token carries the port's lifecycle status. The admin delivers the file through a secure channel outside the system and marks it delivered when the Port Admin confirms receipt. The Port Admin uploads it, even in read-only mode, because this is how an offline port recovers.

Validating it. The port checks the signature, the key, the port id and the dates. It refuses a token older than the one it already has, a token issued before a suspension or revocation it already knows about, and any token at all if the port is stored as OFFBOARDED. A rejected upload is audited with its reason. An accepted token is stored even while the port is ONBOARDING.

Mode after upload. FULL is restored or kept only when the stored port status and the license are ACTIVE and the clock has not been rolled back. Otherwise the token is kept but new operations stay blocked with the reason.

Enforcement. Every request from web, mobile or API passes the same middleware: authentication, role, app version, license mode and port status. In read-only mode only actions on one server-side allowlist pass; everything else returns 423 and the user sees a read-only message. The setup allowlist of an onboarding port is separate and never applies in read-only mode.

**Step-by-step flow** (each step lists where it goes next; END is a final node)

- **START** start → D0 "Triggering event?"
- **D0** Decision "Triggering event?": "Port has no outbound internet" → A1 "Generate manual token for an ACTIVE license (else 422) - token carries port_status"; "Any API request" → U1 "Send a request from web or mobile"
- **A1** [SaaS Admin] Generate manual token for an ACTIVE license (else 422) - token carries port_status → A2 "Deliver token file to the port out of band"
- **U1** [Office or Mobile User] Send a request from web or mobile → M1 "Middleware: auth, RBAC, app version, license mode and port status"
- **A2** [SaaS Admin] Deliver token file to the port out of band → A3 "Upload the token file"
- **M1** [Port Server] Middleware: auth, RBAC, app version, license mode and port status → D3 "Mode READ_ONLY?"
- **A3** [Port Admin] Upload the token file → A4 "Validate token: signature, kid, port_public_id, nbf and expiry; iat newer than the stored token; iat after status_received_at for a stored SUSPENDED or REVOKED status; reject if stored port status is OFFBOARDED"
- **D3** [Port Server] Decision "Mode READ_ONLY?": "No" → M2 "Pass to controller"; "Yes" → D4 "On the server-side allowlist?"
- **A4** [Port Server] Validate token: signature, kid, port_public_id, nbf and expiry; iat newer than the stored token; iat after status_received_at for a stored SUSPENDED or REVOKED status; reject if stored port status is OFFBOARDED → D1 "Token valid?"
- **M2** [Port Server] Pass to controller → END
- **D4** [Port Server] Decision "On the server-side allowlist?": "Yes" → M2 "Pass to controller"; "No" → M3 "Return 423 LICENSE_READ_ONLY"
- **D1** [Port Server] Decision "Token valid?": "No" → A5 "Reject with reason: forged, other port, expired, old or issued before a suspension"; "Yes" → A6 "Accept and store token and iat - also while ONBOARDING"
- **M3** [Port Server] Return 423 LICENSE_READ_ONLY → U2 "See read-only message - mobile hides create buttons"
- **A5** [Port Server] Reject with reason: forged, other port, expired, old or issued before a suspension → A9 "Record audit entry"
- **A6** [Port Server] Accept and store token and iat - also while ONBOARDING → A9 "Record audit entry"
- **U2** [Office or Mobile User] See read-only message - mobile hides create buttons → END
- **A9** [Port Server] Record audit entry → D5 "Port and license ACTIVE, no clock rollback?"
- **D5** [Port Server] Decision "Port and license ACTIVE, no clock rollback?": "No" → A10 "Token kept; new operations stay blocked with the reason"; "Yes" → D2 "Was READ_ONLY?"
- **A10** [Port Server] Token kept; new operations stay blocked with the reason → END
- **D2** [Port Server] Decision "Was READ_ONLY?": "Yes" → A7 "Restore FULL mode"; "No" → A8 "Keep FULL mode"
- **A7** [Port Server] Restore FULL mode → END
- **A8** [Port Server] Keep FULL mode → END

**Rules stated as notes**

- The SaaS Admin uses a secure out-of-band channel and sets delivered_at when the Port Admin confirms receipt (attached to A2)
- Upload is allowed in READ_ONLY - it is the recovery path (attached to A3)
- Allowed in READ_ONLY: reads and reports, license recovery, login, status updates and acknowledgements, reject and return actions, access removal, Port Admin safety exception (attached to D4)
- Blocked: every action not on the allowlist - 423 (attached to M3)
- The ONBOARDING setup allowlist is separate and never applies in READ_ONLY (attached to M3)

#### AD-7 — SaaS platform administration

**Code:** `activity-diagrams-v3/ATLANTECH_Activity_Diagrams.md`, diagram AD-7. **Related:** 1.1, 1.2. **Requirements:** FR-0.1, FR-0.2, FR-0.5, FR-11.2; NFR-SEC-3, NFR-SEC-6.

**Swimlanes:** SaaS Admin, Central SaaS, Scheduler - SYSTEM.

**Story**

This is the daily work of the SaaS Admin on the central platform, plus the system jobs that also write to the platform audit.

Sign-in uses a password and then a one-time code sent by email. A failed attempt is denied and audited; there is no lockout.

After sign-in the admin picks a task: admin accounts, license plans, governorates, the audit log, fleet monitoring, or log out. Every change is checked against the admin's logical role (Platform, License or Billing). A refused action is audited.

Admin accounts are disabled, never deleted, and the admin cannot disable themselves or the last active admin. Disabling an account ends its sessions. Plans are edited in place, because each license keeps its own copy of the limits and price. Every saved change gets an immutable ADMIN audit entry.

The fleet view shows each port's status, last check-in and license status so the admin can spot ports that stopped checking in or are close to expiry. The SaaS Admin never sees port operational data. System jobs such as the license roll-over write SYSTEM audit entries.

**Step-by-step flow** (each step lists where it goes next; END is a final node)

- **START** start → D0 "Triggering event?"
- **D0** Decision "Triggering event?": "Admin session" → A1 "Log in with email and password, then the one-time code sent by email"; "System event" → J1 "System job changes state, for example license roll-over"
- **A1** [SaaS Admin] Log in with email and password, then the one-time code sent by email → S1 "Verify password and email one-time code"
- **J1** [Scheduler - SYSTEM] System job changes state, for example license roll-over → S6 "Record SYSTEM audit entry"
- **S1** [Central SaaS] Verify password and email one-time code → D1 "Valid?"
- **S6** [Central SaaS] Record SYSTEM audit entry → END
- **D1** [Central SaaS] Decision "Valid?": "No" → S2 "Deny login and audit the failure - no lockout"; "Yes" → A2 "Choose a task"
- **S2** [Central SaaS] Deny login and audit the failure - no lockout → A1 "Log in with email and password, then the one-time code sent by email"
- **A2** [SaaS Admin] Choose a task → D2 "Task?"
- **D2** [SaaS Admin] Decision "Task?": "Admin accounts" → A3 "Create or disable a SaaS admin account - never delete"; "License plans" → A4 "Edit plan parameters in place: limits, annual price"; "Governorates" → A5 "Manage governorate reference list"; "Audit log" → A6 "View platform audit log"; "Monitor ports" → S5 "Show port fleet: status, last check-in, license status"; "Log out" → A9 "Log out"
- **A3** [SaaS Admin] Create or disable a SaaS admin account - never delete → S7 "Check the role for this task"
- **A4** [SaaS Admin] Edit plan parameters in place: limits, annual price → S7 "Check the role for this task"
- **A5** [SaaS Admin] Manage governorate reference list → S7 "Check the role for this task"
- **A6** [SaaS Admin] View platform audit log → A2 "Choose a task"
- **S5** [Central SaaS] Show port fleet: status, last check-in, license status → A8 "Spot ports that stopped checking in or are near expiry"
- **A9** [SaaS Admin] Log out → END
- **S7** [Central SaaS] Check the role for this task → D3 "Role permits the task?"
- **A8** [SaaS Admin] Spot ports that stopped checking in or are near expiry → A2 "Choose a task"
- **D3** [Central SaaS] Decision "Role permits the task?": "No" → S8 "Reject the action"; "Yes, admin account" → D4 "Self or last active admin?"; "Yes, plan or governorate" → S3 "Save change"
- **S8** [Central SaaS] Reject the action → S11 "Record rejected attempt in the audit"
- **D4** [Central SaaS] Decision "Self or last active admin?": "Yes" → S8 "Reject the action"; "No" → S3 "Save change"
- **S3** [Central SaaS] Save change → D6 "Account disabled?"
- **S11** [Central SaaS] Record rejected attempt in the audit → A2 "Choose a task"
- **D6** [Central SaaS] Decision "Account disabled?": "Yes" → S10 "Revoke the account's sessions"; "No" → S4 "Record ADMIN audit entry - immutable"
- **S10** [Central SaaS] Revoke the account's sessions → S4 "Record ADMIN audit entry - immutable"
- **S4** [Central SaaS] Record ADMIN audit entry - immutable → A2 "Choose a task"

**Rules stated as notes**

- The SaaS Admin never accesses port operational data (attached to A2)
- Logical roles Platform, License and Billing are an attribute of the admin account; one person may hold several (attached to S7)

#### AD-20 — TLS certificate renewal and remote support

**Code:** `activity-diagrams-v3/ATLANTECH_Activity_Diagrams.md`, diagram AD-20. **Related:** 1.5. **Requirements:** NFR-SEC-4, NFR-SEC-6 (certificate renewal and remote support are deployment work with no FRD item).

**Swimlanes:** Port IT Administrator, ATLANTECH Support Engineer, VPN Gateway.

**Story**

Two technical support flows between the port's IT team and ATLANTECH.

Certificate renewal. Every two years, before the port's TLS certificate expires, Port IT generates a new key and CSR on the server. The ATLANTECH Support Engineer validates it and signs it with the offline Root CA, and Port IT installs the renewed certificate.

Remote support. There is no standing access into a port. When help is needed, Port IT raises a support request with an approved ticket and scope and opens a temporary, time-boxed VPN account. The named Support Engineer verifies with MFA and connects. The VPN gateway checks the identity, MFA, ticket, scope and time box; any failure refuses the connection and is audited.

The Support Engineer works only within the ticket's scope. The session ends when Port IT closes it or when the time box runs out; either way the connection is terminated, the support account is revoked and the session is recorded in the audit.

**Step-by-step flow** (each step lists where it goes next; END is a final node)

- **START** start → D0 "Triggering event?"
- **D0** Decision "Triggering event?": "TLS certificate near its 2-year expiry" → C1 "Generate new key and CSR on the server"; "Support needed" → S1 "Raise support request with an approved ticket and scope"
- **C1** [Port IT Administrator] Generate new key and CSR on the server → C2 "Validate the CSR and sign it with the offline Root CA"
- **S1** [Port IT Administrator] Raise support request with an approved ticket and scope → S2 "Open temporary, time-boxed support VPN account for the approved scope"
- **C2** [ATLANTECH Support Engineer] Validate the CSR and sign it with the offline Root CA → C3 "Install renewed TLS certificate"
- **S2** [Port IT Administrator] Open temporary, time-boxed support VPN account for the approved scope → S10 "Identify the named Support Engineer and verify MFA"
- **C3** [Port IT Administrator] Install renewed TLS certificate → END
- **S10** [ATLANTECH Support Engineer] Identify the named Support Engineer and verify MFA → S3 "Connect through the support VPN"
- **S3** [ATLANTECH Support Engineer] Connect through the support VPN → S4 "Check Support Engineer identity, MFA, ticket, scope and time box"
- **S4** [VPN Gateway] Check Support Engineer identity, MFA, ticket, scope and time box → D2 "All checks pass?"
- **D2** [VPN Gateway] Decision "All checks pass?": "No" → S6 "Refuse connection and audit the attempt"; "Yes" → S5 "Work within the approved scope"
- **S6** [VPN Gateway] Refuse connection and audit the attempt → END
- **S5** [ATLANTECH Support Engineer] Work within the approved scope → D3 "How does the session end?"
- **D3** [VPN Gateway] Decision "How does the session end?": "Time box expires" → S8 "Terminate connection and revoke the support account"; "Work done" → S7 "Close support access manually"
- **S8** [VPN Gateway] Terminate connection and revoke the support account → S9 "Record support session in audit"
- **S7** [Port IT Administrator] Close support access manually → S8 "Terminate connection and revoke the support account"
- **S9** [VPN Gateway] Record support session in audit → END

**Rules stated as notes**

- Only the steps that involve ATLANTECH are shown (attached to C1)
- Default is no access - no standing inbound path (attached to S4)
- Remote support scope = the approved support ticket; onboarding sessions follow AD-1 and close at ACTIVE (attached to S5)

### State machine diagrams of category 1

#### SM-1 — License (central SaaS)

**Code:** `state-diagrams/ATLANTECH_State_Diagrams.md`, diagram SM-1. **Related:** AD-2, AD-3, 1.6–1.8, 1.11. **Requirements:** FR-0.3, FR-0.5.

**States:** ACTIVE, PENDING, EXPIRED, REVOKED, SUSPENDED.

**Story**

This state machine follows one license record in the central SaaS database, from the moment it is issued until it ends.

Issue and renew. When the SaaS Admin issues or renews a license, the dates are validated and the plan limits and price are copied into the license. No token is signed at this point. If the license already starts and the port has no other active license, it becomes ACTIVE; if it starts in the future it waits as PENDING.

Daily roll-over. A scheduler runs every day. A PENDING license becomes ACTIVE when its start date is reached, it is not on hold and the port has no other active license. Any PENDING, ACTIVE or SUSPENDED license whose end date has passed becomes EXPIRED. These automatic changes are audited as SYSTEM.

Suspend and reinstate. The SaaS Admin can suspend an ACTIVE license manually. The port keeps its token, and on_hold is set on any PENDING renewal so it cannot activate behind the suspension. Reinstating returns the license to ACTIVE, if no other license is active, and clears on_hold; no new token is issued.

Revoke. A PENDING, ACTIVE or SUSPENDED license can be revoked; any token it has is revoked too. Offboarding a port revokes all its licenses. EXPIRED and REVOKED are final.

Tokens are not states of the license. A token is signed the first time the port checks in, or when a manual token is requested, and it is refreshed at check-in when 14 days or less remain. At most one license per port is ACTIVE at any time.

**Transitions** (event [guard] / action)

| From | To | Event [guard] / action |
|---|---|---|
| initial | license_choice | Issue or renew license / validate dates, snapshot plan limits and price, audit |
| license_choice | ACTIVE | [valid_from <= now and no other ACTIVE license] / audit, no token |
| license_choice | PENDING | [valid_from > now] / audit, no token |
| PENDING | ACTIVE | daily scheduler [now >= valid_from and not on_hold and no other ACTIVE license] / audit SYSTEM |
| PENDING | EXPIRED | daily scheduler [now >= expires_at] / audit SYSTEM |
| PENDING | REVOKED | revoke / audit |
| ACTIVE | EXPIRED | daily scheduler [now >= expires_at] / audit SYSTEM |
| ACTIVE | SUSPENDED | suspend / token kept, PENDING renewal on_hold, audit |
| ACTIVE | REVOKED | revoke / revoke token if any, audit |
| SUSPENDED | ACTIVE | reinstate [no other ACTIVE license] / release on_hold, no new token, audit |
| SUSPENDED | EXPIRED | daily scheduler [now >= expires_at] / audit SYSTEM |
| SUSPENDED | REVOKED | revoke / revoke token if any, audit |
| EXPIRED | final | (automatic) |
| REVOKED | final | (automatic) |

**Notes on the diagram**

- On ACTIVE: At most one ACTIVE license per port. The token is signed lazily, at the first check-in or as a manual token. It is refreshed at check-in when 14 days or less remain. No status change.
- On PENDING: Billing records are created manually by the SaaS Admin. No transition is driven by billing. Offboarding the port revokes its licenses.
- On REVOKED: Every transition is audited: admin actions as ADMIN, roll-overs as SYSTEM.

#### SM-2 — Port lifecycle (central SaaS)

**Code:** `state-diagrams/ATLANTECH_State_Diagrams.md`, diagram SM-2. **Related:** AD-1, AD-3, 1.3, 1.4. **Requirements:** FR-0.1, FR-0.5.

**States:** ONBOARDING, ACTIVE, SUSPENDED, OFFBOARDED.

**Story**

Besides its license, every port has its own lifecycle in the central SaaS. This machine is drawn from the agreed rules so that the port-side mode in the next diagram can be read against it.

Onboarding. The SaaS Admin registers a port in ONBOARDING, with its public id and an API credential of which only a hash is kept. While the port is being set up, it can already receive and store a valid token; the port server is then in SETUP mode.

Activation. The SaaS Admin activates the port only when the activation checklist is complete: token installed, essential settings, berths and resources, and a Port Admin account. The Port Admin's readiness confirmation is recorded in the audit.

Suspend, reinstate and offboard. An ACTIVE port can be suspended with a reason and reinstated later. From any of these states the port can be offboarded, which revokes its licenses and tokens. OFFBOARDED is final.

Port status and license status are independent: a port can be ACTIVE with a suspended license, and the other way round. Operations need both to be ACTIVE.

**Transitions** (event [guard] / action)

| From | To | Event [guard] / action |
|---|---|---|
| initial | ONBOARDING | SaaS Admin registers the port / public_id, API credential hash, audit |
| ONBOARDING | ACTIVE | activate [activation checklist complete] / Port Admin readiness recorded, audit |
| ACTIVE | SUSPENDED | suspend port / reason, audit |
| SUSPENDED | ACTIVE | reinstate port / audit |
| ONBOARDING | OFFBOARDED | offboard / revoke licenses and tokens, audit |
| ACTIVE | OFFBOARDED | offboard / revoke licenses and tokens, audit |
| SUSPENDED | OFFBOARDED | offboard / revoke licenses and tokens, audit |
| OFFBOARDED | final | (automatic) |

**Notes on the diagram**

- On ONBOARDING: Checklist: token installed, essential settings, berths and resources, Port Admin account. A valid token may already be stored here: the port server runs in SETUP mode.
- On SUSPENDED: Port status and license status are separate. Operations need both to be ACTIVE. The port server learns the port status at check-in.

#### SM-3 — Port-side license mode

**Code:** `state-diagrams/ATLANTECH_State_Diagrams.md`, diagram SM-3. **Related:** AD-5, AD-6, 1.13, 1.14. **Requirements:** FR-0.6, FR-11.4; NFR-SEC-2.

**States:** SETUP, FULL, READ_ONLY.

**Story**

The port server does not run the central license machine itself. It derives its own mode from three facts it stores: the port status, the license status and its token. This machine shows that mode.

How the mode is decided. Whenever a token is stored or the state is checked (at check-in, after a manual token upload, or in a periodic local check), the server first looks at the port status and only then at the license. A port still ONBOARDING is in SETUP. A port that is ACTIVE with an ACTIVE license and a valid token is in FULL. Every other case is READ_ONLY, always with the reason shown; a suspended license is never shown as onboarding.

SETUP. The port can only be set up: the first Port Admin, setup users, port configuration, berths and resources. No operational record can be created. When the port becomes ACTIVE, the mode becomes FULL if the license is active and the token valid, otherwise READ_ONLY.

FULL and READ_ONLY. Any loss of a condition (port suspended or offboarded, license not active, token missing, expired, revoked or invalid) moves FULL to READ_ONLY, where new writes return 423. Running work can still be reported and acknowledged, requests can still be rejected or returned, users deactivated, tokens revoked, and the Port Admin can use the safety exception. A valid token received by check-in or manual upload, with port and license active, brings back FULL. SETUP is never re-entered from READ_ONLY.

**Transitions** (event [guard] / action)

| From | To | Event [guard] / action |
|---|---|---|
| initial | mode_choice | token stored or state checked / port state decided first, then license state |
| mode_choice | SETUP | [port ONBOARDING] |
| mode_choice | FULL | [port ACTIVE and license ACTIVE and token valid] |
| mode_choice | READ_ONLY | [any other case] / reason shown |
| SETUP | FULL | port becomes ACTIVE [license ACTIVE and token valid] |
| SETUP | READ_ONLY | port leaves ONBOARDING [license not ACTIVE or token not valid] / reason shown |
| FULL | READ_ONLY | port SUSPENDED or OFFBOARDED, license not ACTIVE, or token missing, expired, revoked or invalid / reason shown, new writes return 423 |
| READ_ONLY | FULL | valid token by check-in or manual upload [port ACTIVE and license ACTIVE] |

**Notes on the diagram**

- On SETUP: Only the first Port Admin, setup users, port configuration, berths and resources. Never operational records.
- On READ_ONLY: SETUP is never entered from READ_ONLY. Allowed: status updates, acknowledgements, reject and return, deactivate user, revoke tokens, Port Admin safety exception.
- On FULL: Recalculated at every check-in, manual token upload and local periodic check, from the last stored port and license state.

## Category 2 — Port Setup, Operations and Recommendation

### UC-2 — Use case diagram: From an empty port to a confirmed operational plan

**Code:** `use-case-diagrams/ATLANTECH_Use_Case_Diagrams.md`, diagram 2. **System boundary:** ATLANTECH: Port Setup, Operations and Recommendation. **Requirements:** FR-1.1–FR-1.9, FR-2.1–FR-2.6, FR-3.1–FR-3.11, FR-4.1–FR-4.9, FR-5.1, FR-5.2, FR-7.1–FR-7.3, FR-8.1–FR-8.8, FR-9.1, FR-9.6, FR-10.1–FR-10.8, FR-11.1–FR-11.6; NFR-PERF-1, NFR-ENG-1, NFR-PERF-2, NFR-SEC-1, NFR-SEC-2, NFR-INT-1, NFR-INT-4, NFR-UX-1, NFR-UX-2.

This diagram covers everything that happens inside the port: setting up users and master data, receiving a vessel's berthing request, computing a safe entry window, producing and reviewing the AI recommendation, confirming the plan and dispatching it to the pilots, tugs and container yard. It also covers the devices and network that the port's IT team manages.

**Actors**

- **Port Admin**: Manages users, roles, devices, the port profile, terminals and berths. Can also cancel a started plan as a safety exception.
- **Port Authority Staff**: Handle each vessel call: requests, approvals, the entry window, the cargo manifest and the plan.
- **Department managers and administrators**: Tug and Pilotage managers keep their fleets and rosters. The CT Administrator keeps cranes, equipment and the yard. The Marine Safety Officer sets the safety and environmental limits.
- **Officers and field crew**: Pilotage and Tug officers assign the work; Marine Pilots and Tug Masters acknowledge it; the CT Operation Planner handles the yard plan.
- **Office User and Mobile User**: Any staff member who logs in on the web or on the mobile app.
- **Port IT Administrator**: Manages devices, the VPN, firewall, internal DNS and office PCs.
- **System actors**: EDI Parser, AI Part 1 and Part 2 engines, weather providers, Scheduler, MDM platform, VPN gateway and the managed device.

**Story**

*1. Access and users.* Office users log in on the web dashboard and mobile users on the app. Every request is authorized by role and terminal, and the mobile app must meet the minimum version. A user who logged out offline signs in again and the app resumes its pending events. The Port Admin creates and deactivates users, assigns or ends roles and manages devices. A user cannot deactivate themselves or the last Port Admin, and the first login with a one-time password forces a password change.

*2. Port master data.* Before operations start, the port is described: the Port Admin keeps the port profile, terminals and berths and reads the history and audit log; the Tug and Pilotage managers keep the tug fleet, tug masters and pilot roster; the CT Administrator keeps the cranes, equipment and container yard; the Marine Safety Officer defines the safety constraints and environmental limits. When a resource changes, only pending recommendations are regenerated; a confirmed plan is not touched.

*3. A vessel asks to berth.* Port Authority Staff create the berthing request with the vessel's full data; the vessel is found or created by its IMO number. While the request is SUBMITTED or NEEDS_REVISION it can be edited or cancelled. Staff then record preliminary approval, or return the request for revision, or reject it. Customs approval starts AI Part 1, which computes the entry-time window using weather and sea-level data and the astronomical tide. If no recent weather data covers the request, staff submit manual environmental data. Staff then confirm one window, reject all windows with a reason, or reopen a confirmed window.

*4. Weather and tide.* A scheduler polls the weather providers every six hours. If the primary provider fails, the secondary is used and an alert is raised; if both fail, the stored data is marked stale. Office users can view the current conditions.

*5. The cargo manifest.* For container vessels, staff upload the BAPLIE file against its berthing request. The EDI Parser validates it. Staff review the diagnostics, correct the staged data if needed, or withdraw an upload made by mistake.

*6. Recommendation and plan.* With the window confirmed, AI Part 2 generates a port-wide recommendation for berth, tug and pilot. Staff review it with its rationale, may override a component with a reason, or re-generate it. After confirmation, a significant delay produces a delay re-plan proposal instead. Confirming the plan books the resources in one transaction. A plan can be cancelled with its resources released; once any part has started, only the Port Admin can cancel it, as a safety exception.

*7. Dispatch and the yard.* The pilotage and tug officers assign the pilot and the tug the system proposes, or replace them. Notifications go out with retries and escalation if nobody acknowledges, and the pilot or tug master acknowledges from the app. For container vessels, AI Part 2 generates a yard placement; the planner accepts, adjusts or rejects it, then takes the TOS-ready plan and records that it was entered into the terminal's TOS.

*8. Devices and network.* Port IT enrolls each field phone in the MDM, which issues its certificate and installs the app and the VPN profile. The phone keeps an always-on VPN, and the gateway validates its certificate. A lost phone has its certificate revoked and is wiped; Port IT then informs the Port Admin, who revokes its API tokens. Port IT also manages the firewall, the internal DNS, the Root CA on office PCs, and troubleshoots connectivity.

*Rule that applies to the whole diagram.* Every write action shown here includes Enforce Read-Only Mode from Diagram 1. Rejecting or returning a request, rejecting all windows, rejecting a yard plan, acknowledging, deactivating a user, revoking tokens and the Port Admin's safety exception stay allowed in read-only mode. Adding a user, terminal or berth also includes Enforce Plan Limits.

**Use cases by package** (actor associations in brackets; related sequence · activity · state diagrams after the package name)

- **Access and Users** — 2.1–2.3 · AD-18, AD-17
  - Log in to Web Dashboard (Office User)
  - Log in to Mobile App (Mobile User)
  - Log Out (Office User, Mobile User)
  - Authorize Request by Role (reached only through include or extend)
  - Re-authenticate and Resume Outbox (Mobile User)
  - Enforce Minimum App Version (reached only through include or extend)
  - Manage Port Users (Port Admin)
  - Assign Roles and Terminal Scope (Port Admin)
  - Manage Devices and Revoke Tokens (Port Admin)
- **Port Master Data** — 2.4–2.6 · AD-18
  - Manage Port Profile and Channel (Port Admin)
  - Manage Terminals (Port Admin)
  - Manage Berths (Port Admin)
  - Manage Tugboat Fleet (Tug Dept. Manager)
  - Manage Tug Masters (Tug Dept. Manager)
  - Manage Pilot Roster (Pilotage Dept. Manager)
  - Manage CT Equipment and Cranes (CT Administrator)
  - Manage Container Yard (CT Administrator)
  - Manage NCT Storage (NCT Administrator)
  - Define Safety Constraints and Environmental Limits (Marine Safety Officer)
  - View Master-Data History (Port Admin)
  - View Port Audit Log (Port Admin)
- **BAPLIE Cargo Manifest** — 2.7, 2.8 · AD-8
  - Upload BAPLIE File (Port Authority Staff)
  - Parse and Validate BAPLIE (EDI Parser)
  - Review BAPLIE Diagnostics (Port Authority Staff)
  - Correct Staged BAPLIE Data (Port Authority Staff)
  - Withdraw BAPLIE Upload (Port Authority Staff)
- **Berthing Request and Entry Window** — 2.9–2.11 · AD-9, AD-10 · SM-4
  - Create Berthing Request (Port Authority Staff)
  - Edit or Cancel Request (Port Authority Staff)
  - Record Preliminary Approval (Port Authority Staff)
  - Return or Reject Request (Port Authority Staff)
  - Record Customs Approval (Port Authority Staff)
  - Compute Entry-Time Window (AI Part 1 Engine)
  - Confirm, Reject All or Reopen Entry Window (Port Authority Staff)
  - Submit Manual Environmental Data (Port Authority Staff)
- **Weather and Tide** — 2.12 · AD-10
  - Poll Weather Data Every 6 Hours (Weather and Sea-Level Providers, Scheduler)
  - Handle Weather Source Failure (reached only through include or extend)
  - Fetch Weather and Sea Level on Demand (AI Part 1 Engine, Weather and Sea-Level Providers)
  - Compute Astronomical Tide (AI Part 1 Engine)
  - View Environmental Conditions (Office User)
- **Recommendation and Operational Plan** — 2.13, 2.14 · AD-11, AD-12 · SM-4, SM-5
  - Generate Port-wide Recommendations (AI Part 2 Engine)
  - Review Recommendation and Rationale (Port Authority Staff)
  - Override Component (Port Authority Staff)
  - Re-generate Recommendation or Delay Re-plan (AI Part 2 Engine)
  - Confirm Operational Plan (Port Authority Staff)
  - Cancel Plan and Release Resources (Port Admin, Port Authority Staff)
  - View Unified Port State (Office User)
- **Dispatch and Container Yard** — 2.15, 2.16 · AD-13, AD-14 · SM-5
  - Assign Pilotage Component (Pilotage Dept. Officer)
  - Assign Tug Component (Tug Dept. Officer)
  - Send Task Notifications and Escalations (Scheduler)
  - Acknowledge Notification (Marine Pilot / Tug Master)
  - Generate Yard Placement Recommendation (AI Part 2 Engine)
  - Accept, Adjust or Reject Yard Recommendation (CT Operation Planner)
  - Present TOS-Ready Plan and Record Export (CT Operation Planner)
- **Devices and VPN** — 2.17 · AD-19
  - Enroll Device in MDM (Port IT Administrator)
  - Issue Device Certificate (MDM Platform)
  - Distribute App and VPN Profile (MDM Platform, Managed Mobile Device)
  - Revoke Certificate and Selective Wipe (Port IT Administrator, MDM Platform)
  - Establish Always-on VPN (Remote Field User)
  - Validate Device Certificate (VPN Gateway)
  - Manage VPN Gateway (Port IT Administrator, VPN Gateway)
- **Port Network and Edge** — 2.17 · AD-19
  - Manage Firewall Rules (Port IT Administrator)
  - Manage Internal Split DNS (Port IT Administrator)
  - Trust Root CA on Office PCs (Port IT Administrator)
  - Troubleshoot Connectivity (Port IT Administrator)

**Include and extend relations** (read "A includes B" as: A always performs B; "A extends B" as: A optionally adds to B)

- Log in to Web Dashboard **includes** Authorize Request by Role
- Log in to Mobile App **includes** Authorize Request by Role
- Log in to Mobile App **includes** Enforce Minimum App Version
- Re-authenticate and Resume Outbox **extends** Log in to Mobile App
- Upload BAPLIE File **includes** Parse and Validate BAPLIE
- Correct Staged BAPLIE Data **includes** Parse and Validate BAPLIE
- Review BAPLIE Diagnostics **extends** Upload BAPLIE File
- Correct Staged BAPLIE Data **extends** Review BAPLIE Diagnostics
- Return or Reject Request **extends** Record Preliminary Approval
- Record Customs Approval **includes** Compute Entry-Time Window
- Compute Entry-Time Window **includes** Fetch Weather and Sea Level on Demand
- Compute Entry-Time Window **includes** Compute Astronomical Tide
- Submit Manual Environmental Data **extends** Compute Entry-Time Window
- Handle Weather Source Failure **extends** Poll Weather Data Every 6 Hours
- Override Component **extends** Review Recommendation and Rationale
- Re-generate Recommendation or Delay Re-plan **extends** Generate Port-wide Recommendations
- Confirm Operational Plan **includes** Review Recommendation and Rationale
- Assign Pilotage Component **includes** Send Task Notifications and Escalations
- Assign Tug Component **includes** Send Task Notifications and Escalations
- Present TOS-Ready Plan and Record Export **extends** Accept, Adjust or Reject Yard Recommendation
- Enroll Device in MDM **includes** Issue Device Certificate
- Enroll Device in MDM **includes** Distribute App and VPN Profile
- Establish Always-on VPN **includes** Validate Device Certificate

**Note on the diagram:** Every write action in this diagram includes Enforce Read-Only Mode (Diagram 1). Adding a user, terminal or berth also includes Enforce Plan Limits (Diagram 1).

### Sequence diagrams of category 2

#### 2.1 — Web and mobile sign-in

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 2.1. **Related:** AD-18, AD-17. **Requirements:** FR-11.1, FR-11.3; NFR-SEC-3.

**Participants**

- **Port User**: actor (person)
- **Web Dashboard**: boundary (user interface)
- **Mobile App**: boundary (user interface)
- **Port API**: control (service, API, worker or scheduler)
- **Auth Module (Sanctum)**: control (service, API, worker or scheduler)
- **Port Database**: database (data store)

**Story**

Port staff sign in on the web dashboard and field staff on the mobile app. Both reach the same port API and the same authentication module.

Web. The browser first gets a CSRF cookie, then posts the identifier and password. Missing fields return 422, a wrong identifier or password returns 401, and an account that was deactivated returns 403 ACCOUNT_DISABLED. A valid user gets a fresh session and a profile with roles and terminal scope, and the dashboard shows the menus for those roles. Hiding menus is only for comfort; the server checks every request anyway.

Mobile. On first launch the app reads /system/info from the fixed server address and learns the port's id and name, the license mode, the token warning days and the minimum app version. Sign-in sends the device id, platform and app version. Besides the same 401 and 403 answers, an app below the minimum version gets 426 and no token. A valid user gets a device token that slides over 30 days, the device is registered (user_device), and the app caches the user's tasks so it can work offline.

A user with must_change_password set (a new user with the one-time password set by an administrator) must change the password before anything else; saving the new password clears the flag.

**Message flow, top to bottom**

- **Alternative paths — case: Web sign-in**
  - Port User → Web Dashboard: Enter identifier and password
  - Web Dashboard → Port API: GET /sanctum/csrf-cookie
  - Port API → Web Dashboard (reply): XSRF cookie
  - Web Dashboard → Port API: POST login
  - Port API → Auth Module (Sanctum): Authenticate
  - Auth Module (Sanctum) → Port Database: Find user, password hash, is_active
  - **Alternative paths — case: Missing fields**
    - Port API → Web Dashboard (reply): 422 Unprocessable
  - **Otherwise — case: Unknown user or wrong password**
    - Port API → Web Dashboard (reply): 401 Unauthorized
  - **Otherwise — case: Account inactive**
    - Port API → Web Dashboard (reply): 403 ACCOUNT_DISABLED
  - **Otherwise — case: Valid**
    - Auth Module (Sanctum) → Port Database: Load roles and terminal scope
    - Auth Module (Sanctum) (internal): Start session (new session id)
    - Port API → Web Dashboard (reply): 200 session cookie and profile
    - Web Dashboard → Port User (reply): Dashboard with menus for the user's roles
- **Otherwise — case: Mobile sign-in**
  - **Optional — only when: First launch**
    - Mobile App → Port API: GET /system/info
    - Port API → Mobile App (reply): port_public_id, port name, license_mode, token_warning_days_left, min_app_version
  - Port User → Mobile App: Enter identifier and password
  - Mobile App → Port API: POST /auth/login (device_id, platform, app_version)
  - Port API → Auth Module (Sanctum): Authenticate
  - Auth Module (Sanctum) → Port Database: Find user, password hash, is_active
  - **Alternative paths — case: Unknown user or wrong password**
    - Port API → Mobile App (reply): 401 Unauthorized
  - **Otherwise — case: Account inactive**
    - Port API → Mobile App (reply): 403 ACCOUNT_DISABLED
  - **Otherwise — case: App below the minimum version**
    - Port API → Mobile App (reply): 426 Upgrade Required (no token)
  - **Otherwise — case: Valid**
    - Auth Module (Sanctum) → Port Database: Create device token (30-day sliding) and register the device (user_device)
    - Port API → Mobile App (reply): 200 token, profile, roles, scope
    - Mobile App (internal): Keep the token in secure storage
    - Mobile App → Port API: Get assigned tasks
    - Port API → Mobile App (reply): Tasks
    - Mobile App (internal): Cache tasks locally
    - Mobile App → Port User (reply): Home screen
- **Optional — only when: must_change_password set**
  - Port API → Port User (reply): Password change required
  - Port User → Port API: Set a new password
  - Port API → Port Database: Save the new password hash, clear must_change_password

#### 2.2 — Request checks, re-authentication and logout

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 2.2. **Related:** AD-18, AD-17. **Requirements:** FR-11.4, FR-11.5; NFR-SEC-2, NFR-SEC-3, NFR-CONC-1.

**Participants**

- **Port User**: actor (person)
- **Web Dashboard**: boundary (user interface)
- **Mobile App**: boundary (user interface)
- **Port API**: control (service, API, worker or scheduler)
- **Auth Module (Sanctum)**: control (service, API, worker or scheduler)
- **Port Database**: database (data store)

**Story**

Every protected request passes the same chain of checks in the same order. The diagram shows that chain once, then two related flows: signing in again on the phone, and logging out.

The chain. First authentication: no valid session or token, or a deactivated user, gives 401. Then the role and terminal scope: not allowed gives 403. For the mobile app, the app version: too old gives 426. Then the license mode: an action the current mode does not allow gives 423 LICENSE_READ_ONLY. Only then does the controller run its own checks, answering 422 for bad input or 409 for a state conflict. A successful write is executed inside the user's terminal scope and recorded in the audit log.

Re-authentication. A phone token can expire while the user is offline, or an administrator can revoke it. The next sync gets 401 and no event is processed. The app keeps all its events and asks the user to sign in again. Pending events are sent only when the same user signs back in; they are never sent under another person's account.

Logout. On the web the session ends. On the phone, when online, the server marks the device token revoked; nothing is deleted. When offline, the app forgets its token and the server copy expires or is revoked later.

**Message flow, top to bottom**

- Port User → Web Dashboard: Perform an action (the mobile app gets the same answers)
- Web Dashboard → Port API: Request with session or token
- Port API → Auth Module (Sanctum): Validate session or token and is_active
- **Alternative paths — case: Not authenticated**
  - Port API → Web Dashboard (reply): 401 Unauthorized
- **Otherwise — case: Role or terminal scope not allowed**
  - Port API → Web Dashboard (reply): 403 Forbidden
- **Otherwise — case: Mobile app below the minimum version**
  - Port API → Mobile App (reply): 426 Upgrade Required
- **Otherwise — case: License mode blocks the action**
  - Port API → Web Dashboard (reply): 423 LICENSE_READ_ONLY
- **Otherwise — case: Passed**
  - Port API (internal): Controller validates input and state
  - **Alternative paths — case: Invalid input**
    - Port API → Web Dashboard (reply): 422 Unprocessable
  - **Otherwise — case: State conflict**
    - Port API → Web Dashboard (reply): 409 Conflict
  - **Otherwise — case: OK**
    - Port API → Port Database: Execute within terminal scope, with audit entry for writes
    - Port API → Web Dashboard (reply): 200 Result
- **Optional — only when: Mobile re-authentication**
  - Mobile App → Port API: POST /sync/events with an expired or revoked token
  - Port API → Mobile App (reply): 401 (no event processed)
  - Mobile App → Port User (reply): Please sign in again (events stay PENDING)
  - Port User → Mobile App: Enter credentials
  - Mobile App → Port API: POST /auth/login
  - Port API → Mobile App (reply): New token
  - **Alternative paths — case: Same user as the pending events**
    - Mobile App → Port API: Send the pending events
  - **Otherwise — case: Different user**
    - Mobile App → Port User (reply): Pending events are not sent under another account
- **Optional — only when: Logout**
  - **Alternative paths — case: Web**
    - Port User → Web Dashboard: Log out
    - Web Dashboard → Port API: POST logout
    - Port API → Port Database: End the session
  - **Otherwise — case: Mobile online**
    - Port User → Mobile App: Log out
    - Mobile App → Port API: POST logout
    - Port API → Port Database: Set revoked_at on this device token
  - **Otherwise — case: Mobile offline**
    - Mobile App (internal): Delete the local token, the server token expires or is revoked later

#### 2.3 — Users, roles and devices

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 2.3. **Related:** AD-18, AD-19. **Requirements:** FR-1.3, FR-1.9, FR-11.1; NFR-SEC-2.

**Participants**

- **Port Admin**: actor (person)
- **Web Dashboard**: boundary (user interface)
- **Port API**: control (service, API, worker or scheduler)
- **License Module**: control (service, API, worker or scheduler)
- **Port Database**: database (data store)

**Story**

The Port Admin manages who can use the port system and from which devices. All five actions here pass the normal request checks.

Creating a user. The admin enters the person's name, username, phone and a one-time password; the user is created with must_change_password set and must change it at first login. The plan's user limit is checked first; over the limit the answer is 422 PLAN_LIMIT_EXCEEDED and nothing is saved. Creating users is blocked in read-only mode.

Deactivating a user. Users are never deleted, only deactivated, and the change takes effect on that user's next request. The port must always keep an active Port Admin, so a Port Admin cannot deactivate themselves or the last active Port Admin; both return 409. The count is read under a lock so that two admins cannot remove each other at the same moment. Deactivation stays allowed in read-only mode because it only removes access.

Roles. A role is assigned with its terminal when the role is terminal-scoped. Removing a role does not delete it: the assignment gets an end date (active_to). The same 409 rule protects the last Port Admin role.

Devices. The admin can see a user's devices and revoke one or all of them. The server marks the device tokens revoked and the next request from that phone gets 401. This does not close the phone's VPN; revoking the device certificate is Port IT's job in the MDM.

**Message flow, top to bottom**

- *Note:* Every request passes the check chain. Create user and assign role are blocked in READ_ONLY (423). Deactivate and revoke stay allowed.
- **Alternative paths — case: Create a user**
  - Port Admin → Web Dashboard: Enter name, username, phone, one-time password
  - Web Dashboard → Port API: POST /users
  - Port API → License Module: Check max_users
  - **Alternative paths — case: Limit reached**
    - Port API → Web Dashboard (reply): 422 PLAN_LIMIT_EXCEEDED
  - **Otherwise — case: Within the limit**
    - Port API → Port Database: Insert user (must_change_password = 1) and audit entry
    - Port API → Web Dashboard (reply): 201 Created
- **Otherwise — case: Deactivate a user**
  - Port Admin → Web Dashboard: Deactivate user
  - Web Dashboard → Port API: POST /users/:id/deactivate
  - Port API → Port Database: Lock and count other active Port Admins
  - **Alternative paths — case: Target is yourself, or the last active Port Admin**
    - Port API → Web Dashboard (reply): 409 Conflict
  - **Otherwise — case: Allowed**
    - Port API → Port Database: Set is_active = false and audit entry
    - Port API → Web Dashboard (reply): 200 (applies on the user's next request)
- **Otherwise — case: Assign a role**
  - Port Admin → Web Dashboard: Assign role (and terminal for terminal roles)
  - Web Dashboard → Port API: POST /users/:id/roles
  - **Alternative paths — case: Terminal missing or not expected for this role**
    - Port API → Web Dashboard (reply): 422 Unprocessable
  - **Otherwise — case: Valid**
    - Port API → Port Database: Insert role assignment and audit entry
    - Port API → Web Dashboard (reply): 200
- **Otherwise — case: Remove a role**
  - Port Admin → Web Dashboard: Remove role
  - Web Dashboard → Port API: End role assignment
  - **Alternative paths — case: Port Admin role of yourself, or of the last active Port Admin**
    - Port API → Web Dashboard (reply): 409 Conflict
  - **Otherwise — case: Allowed**
    - Port API → Port Database: Set active_to = now on the assignment and audit entry
    - Port API → Web Dashboard (reply): 200
- **Otherwise — case: Revoke a device**
  - Port Admin → Web Dashboard: Open the user's devices
  - Web Dashboard → Port API: GET /users/:id/devices
  - Port API → Web Dashboard (reply): Devices (platform, app version, last seen)
  - Port Admin → Web Dashboard: Revoke one device or all sessions
  - Web Dashboard → Port API: POST revoke
  - Port API → Port Database: Set revoked_at on the tokens, mark devices revoked, audit entry
  - Port API → Web Dashboard (reply): 200 Sessions revoked
- Web Dashboard → Port Admin (reply): Show the result
- *Note:* Revoking tokens does not close the VPN. Port IT revokes the device certificate in the MDM separately.

#### 2.4 — Port profile, terminals and berths

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 2.4. **Related:** AD-18. **Requirements:** FR-1.1, FR-1.7, FR-1.8, FR-1.9, FR-10.1, FR-10.2, FR-10.4; NFR-CAP-1, NFR-EXT-1.

**Participants**

- **Port Admin**: actor (person)
- **Web Dashboard**: boundary (user interface)
- **Port API (Master Data)**: control (service, API, worker or scheduler)
- **License Module**: control (service, API, worker or scheduler)
- **Port Database**: database (data store)

**Story**

Before the first vessel arrives, the Port Admin describes the port: its profile and boundary, the navigation channel with its waypoints, the terminals and the berths.

Every save passes the request checks and input validation, and every save is a write, so read-only mode returns 423.

Profile and channel. The admin keeps the port profile, the navigation channel (its depth is stated on the chart datum) and the ordered channel waypoints. Each change is audited with its before and after values.

Terminals and berths. A new terminal or berth counts against the plan limit carried in the license token; over the limit returns 422 PLAN_LIMIT_EXCEEDED. Updating or deactivating keeps the row, because history points to it; inactive resources simply stop appearing in selection lists and engine candidates.

When a berth changes, the system regenerates only the pending recommendations that use it. A confirmed plan is never changed by a master-data edit; staff handle it through plan cancellation or a delay re-plan.

**Message flow, top to bottom**

- Port Admin → Web Dashboard: Open master data and save a change
- Web Dashboard → Port API (Master Data): Save
- Port API (Master Data) (internal): Check chain and input validation (422)
- Port API (Master Data) → License Module: Check license mode
- **Alternative paths — case: READ_ONLY**
  - Port API (Master Data) → Web Dashboard (reply): 423 LICENSE_READ_ONLY
- **Otherwise — case: Port profile, navigation channel or waypoints**
  - Port API (Master Data) → Port Database: Create or update profile, channel (depth on chart datum) or waypoint
  - Port API (Master Data) → Port Database: Audit entry (before and after)
  - Port API (Master Data) → Web Dashboard (reply): Saved
- **Otherwise — case: New terminal or berth**
  - Port API (Master Data) → License Module: Check max_terminals or max_berths
  - **Alternative paths — case: Limit reached**
    - Port API (Master Data) → Web Dashboard (reply): 422 PLAN_LIMIT_EXCEEDED
  - **Otherwise — case: Within the limit**
    - Port API (Master Data) → Port Database: Create terminal (CT or NCT) or berth (code, length, depth, max LOA)
    - Port API (Master Data) → Port Database: Audit entry (before and after)
    - Port API (Master Data) → Web Dashboard (reply): Saved
- **Otherwise — case: Update or deactivate a terminal or berth**
  - Port API (Master Data) → Port Database: Update data or status (deactivation keeps the row)
  - Port API (Master Data) → Port Database: Audit entry (before and after)
  - **Optional — only when: Berth changed**
    - Port API (Master Data) (internal): Regenerate pending recommendations that use this berth
  - Port API (Master Data) → Web Dashboard (reply): Saved
- Web Dashboard → Port Admin (reply): Show the result
- *Note:* Confirmed plans are never changed by a master-data edit. Staff use cancel or delay re-plan for them.

#### 2.5 — Tugs, tug masters and pilots

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 2.5. **Related:** AD-18. **Requirements:** FR-1.2–FR-1.6, FR-1.9.

**Participants**

- **Tug Dept. Manager**: actor (person)
- **Pilotage Dept. Manager**: actor (person)
- **Web Dashboard**: boundary (user interface)
- **Port API (Master Data)**: control (service, API, worker or scheduler)
- **License Module**: control (service, API, worker or scheduler)
- **Port Database**: database (data store)

**Story**

The marine departments keep their own resources: the Tug Department Manager owns the tug fleet and the tug masters, and the Pilotage Department Manager owns the pilot roster. Every save passes the request checks and is blocked in read-only mode.

Tugs. The manager adds, edits or deactivates tugs. Deactivation keeps the row and only removes the tug from new planning.

Tug masters. A tug master is a user, so creating one counts against the plan's user limit. Deactivating a tug master also clears the link to their tug in the same transaction. A tug can have only one tug master; linking a second one is refused.

Pilots. The Pilotage manager adds, edits, promotes or deactivates pilots and sets their shift availability. New pilots count against the user limit too.

Whenever a tug, tug master or pilot changes in a way that affects planning, only the pending recommendations that use that resource are regenerated. Confirmed plans are not touched automatically.

**Message flow, top to bottom**

- *Note:* Every save passes the check chain. In READ_ONLY every save returns 423.
- **Alternative paths — case: Tugboat fleet**
  - Tug Dept. Manager → Web Dashboard: Create, update or deactivate a tug
  - Web Dashboard → Port API (Master Data): Save tug
  - Port API (Master Data) → Port Database: Save tug data or set it inactive (row kept)
  - Port API (Master Data) → Port Database: Audit entry
  - **Optional — only when: Tug deactivated**
    - Port API (Master Data) (internal): Regenerate pending recommendations that use this tug
- **Otherwise — case: Tug masters**
  - Tug Dept. Manager → Web Dashboard: Create, update or deactivate a tug master
  - Web Dashboard → Port API (Master Data): Save tug master
  - **Alternative paths — case: New tug master**
    - Port API (Master Data) → License Module: Check max_users
    - **Alternative paths — case: Limit reached**
      - Port API (Master Data) → Web Dashboard (reply): 422 PLAN_LIMIT_EXCEEDED
    - **Otherwise — case: Within the limit**
      - Port API (Master Data) → Port Database: Create user, profile and Tug Master role, audit entry
  - **Otherwise — case: Deactivate**
    - Port API (Master Data) → Port Database: Set is_active = false and clear the tug link, one transaction
    - Port API (Master Data) → Port Database: Audit entry
    - Port API (Master Data) (internal): Regenerate pending recommendations of the linked tug
  - **Otherwise — case: Update**
    - Port API (Master Data) → Port Database: Update user and profile, audit entry
- **Otherwise — case: Link a tug master to a tug**
  - Tug Dept. Manager → Web Dashboard: Assign or unassign a tug
  - Web Dashboard → Port API (Master Data): Save tug assignment
  - Port API (Master Data) → Port Database: Check the tug has no other tug master
  - **Alternative paths — case: Tug already has a tug master**
    - Port API (Master Data) → Web Dashboard (reply): 422 One tug master per tug
  - **Otherwise — case: Allowed**
    - Port API (Master Data) → Port Database: Save the link, audit entry
- **Otherwise — case: Pilot roster**
  - Pilotage Dept. Manager → Web Dashboard: Create, update, promote or deactivate a pilot, or set shifts
  - Web Dashboard → Port API (Master Data): Save pilot
  - **Alternative paths — case: New pilot**
    - Port API (Master Data) → License Module: Check max_users
    - **Alternative paths — case: Limit reached**
      - Port API (Master Data) → Web Dashboard (reply): 422 PLAN_LIMIT_EXCEEDED
    - **Otherwise — case: Within the limit**
      - Port API (Master Data) → Port Database: Create user, pilot profile and Marine Pilot role, audit entry
  - **Otherwise — case: Update, promote, deactivate or change availability**
    - Port API (Master Data) → Port Database: Save pilot data, status or shift range, audit entry
    - Port API (Master Data) (internal): Regenerate pending recommendations that use this pilot
- Port API (Master Data) → Web Dashboard (reply): Saved

#### 2.6 — Terminal equipment, yard, safety limits and audit

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 2.6. **Related:** AD-18. **Requirements:** FR-1.9, FR-8.1–FR-8.3, FR-9.1, FR-9.6, FR-10.8; NFR-SEC-6, NFR-EXT-5.

**Participants**

- **CT Administrator**: actor (person)
- **Marine Safety Officer**: actor (person)
- **Port Admin**: actor (person)
- **Web Dashboard**: boundary (user interface)
- **Port API (Master Data)**: control (service, API, worker or scheduler)
- **Port Database**: database (data store)

**Story**

The remaining master data comes from three owners, and the Port Admin can review all of it afterwards.

Container terminal. The CT Administrator, limited to their own terminal, keeps the equipment and cranes with their quantities, maintenance and blocked quantities and capabilities, and the container yard structure: zones, blocks and slots. The available quantity and the zone capacity are computed, never typed in. When equipment availability goes down, the pending recommendations that rely on it are regenerated.

Safety. The Marine Safety Officer defines the safety constraints and the environmental operating limits for wind, gust, visibility, waves, tide and under-keel clearance, plus the chart datum and UKC parameters. Port-wide limits are stored with no terminal. These limits feed the safety filter before every recommendation and the entry-window assessment. The AI learning loop never relaxes them.

Audit. The Port Admin can browse the whole port audit log, filtered by entity, actor and dates, with the before and after values of each change. Master-data history is this log filtered by master-data entities.

As with all master data, every save passes the request checks and is blocked in read-only mode.

**Message flow, top to bottom**

- *Note:* Every save passes the check chain. In READ_ONLY every save returns 423.
- **Alternative paths — case: CT equipment and cranes**
  - CT Administrator → Web Dashboard: Create or update equipment or a crane (own terminal only)
  - Web Dashboard → Port API (Master Data): Save equipment
  - Port API (Master Data) → Port Database: Save category, quantity, maintenance and blocked quantity, capabilities (available quantity is computed)
  - Port API (Master Data) → Port Database: Audit entry
  - **Optional — only when: Availability reduced**
    - Port API (Master Data) (internal): Regenerate pending recommendations that use it
- **Otherwise — case: Container yard structure**
  - CT Administrator → Web Dashboard: Create or update a zone, block or slot
  - Web Dashboard → Port API (Master Data): Save yard structure
  - Port API (Master Data) → Port Database: Save zone type, block, bay, row, tier (zone capacity is computed from slots)
  - Port API (Master Data) → Port Database: Audit entry
- **Otherwise — case: Safety constraints and environmental limits**
  - Marine Safety Officer → Web Dashboard: Open constraints and limits
  - Web Dashboard → Port API (Master Data): Load
  - Port API (Master Data) → Port Database: Read constraints, limits, chart datum and UKC
  - Marine Safety Officer → Web Dashboard: Save a constraint, a limit (wind, gust, visibility, wave, tide, UKC) or the datum and UKC parameters
  - Web Dashboard → Port API (Master Data): Save
  - Port API (Master Data) → Port Database: Save in safety_constraint (port-wide limits have no terminal)
  - Port API (Master Data) → Port Database: Audit entry (before and after)
  - *Note:* The Marine Safety Officer owns port-wide limits. AI Part 3 never changes them.
- **Otherwise — case: Change history and audit log**
  - Port Admin → Web Dashboard: Filter by entity, actor, dates
  - Web Dashboard → Port API (Master Data): Get records
  - Port API (Master Data) → Port Database: Read the port audit log (filter master-data entities)
  - Port API (Master Data) → Web Dashboard (reply): Records (who, what, when, before and after)
- Web Dashboard → CT Administrator (reply): Show the result

#### 2.7 — BAPLIE upload and parsing

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 2.7. **Related:** AD-8. **Requirements:** FR-2.1–FR-2.4, FR-2.6; NFR-PERF-2, NFR-INT-1, NFR-REL-4, NFR-UX-4.

**Participants**

- **Port Authority Staff**: actor (person)
- **Web Dashboard**: boundary (user interface)
- **Port API (BAPLIE)**: control (service, API, worker or scheduler)
- **BAPLIE File Volume**: database (data store)
- **Redis Queue**: queue (Redis)
- **EDI Parser**: control (service, API, worker or scheduler)
- **Port Database**: database (data store)

**Story**

For a container vessel, staff upload its BAPLIE stowage file. The file always belongs to a berthing request; a file with no request is not accepted.

Linking the request. Staff can select the request, or leave it empty. Then the system looks for open requests with the same IMO number as the file and an ETA within 24 hours. Exactly one match links it; none or several returns 422 and staff select the request themselves. Uploading is blocked in read-only mode.

Duplicates. The same file uploaded again for the same request returns 409. The same file for a different request is allowed.

Parsing. The file is stored, a record is created with status STAGED and parse status PENDING, and a job is queued for the EDI Parser. The parser reads the file against the EDIFACT and SMDG standards. If the IMO in the file does not match the request's vessel, the file is marked QUARANTINED and blocked. A valid file is committed in one transaction: the vessel is found or created by IMO and only its empty fields are filled, the previous active file of the same request becomes REPLACED, and containers and stowage are stored; the parse status becomes PARSED. An invalid file keeps its extracted data and diagnostics as staged data with parse status QUARANTINED, and nothing reaches operational tables. A file that cannot be read at all gets parse status FAILED and no staged data.

The API reads the result from the database and pushes it to the dashboard over SSE.

**Message flow, top to bottom**

- Port Authority Staff → Web Dashboard: Upload BAPLIE file, select the berthing request or leave it empty
- Web Dashboard → Port API (BAPLIE): Upload
- Port API (BAPLIE) (internal): Check chain
- **Alternative paths — case: READ_ONLY**
  - Port API (BAPLIE) → Web Dashboard (reply): 423 LICENSE_READ_ONLY
- **Otherwise — case: Request left empty**
  - Port API (BAPLIE) → Port Database: Match by IMO in the file and ETA within 24 h among open requests
  - **Alternative paths — case: Zero or several matches**
    - Port API (BAPLIE) → Web Dashboard (reply): 422 Select the request
  - **Otherwise — case: Exactly one match**
    - Port API (BAPLIE) (internal): Link that request
- **Optional — only when: Request linked**
  - Port API (BAPLIE) → Port Database: Check file hash for this request (non-withdrawn files)
  - **Alternative paths — case: Same file already uploaded for this request**
    - Port API (BAPLIE) → Web Dashboard (reply): 409 Duplicate file
  - **Otherwise — case: New file**
    - Port API (BAPLIE) → BAPLIE File Volume: Store the file
    - Port API (BAPLIE) → Port Database: Create baplie_file (request linked, status STAGED, parse_status PENDING)
    - Port API (BAPLIE) → Redis Queue: Push parse job
    - Port API (BAPLIE) → Web Dashboard (reply): Accepted, processing
- Redis Queue → EDI Parser: Deliver parse job
- EDI Parser → BAPLIE File Volume: Read the file
- EDI Parser (internal): Parse and validate (EDIFACT D.17A, SMDG 2019)
- EDI Parser → Port Database: Read the request's vessel
- **Alternative paths — case: IMO differs from the request**
  - EDI Parser → Port Database: parse_status QUARANTINED (blocking mismatch)
- **Otherwise — case: Valid**
  - EDI Parser → Port Database: Find or create the vessel by IMO, fill empty fields only
  - EDI Parser → Port Database: Mark the earlier ACTIVE file of this request REPLACED
  - EDI Parser → Port Database: Store containers and stowage, file ACTIVE, parse_status PARSED
  - *Note:* One transaction. Data from the request form is never overwritten.
- **Otherwise — case: Invalid or incomplete**
  - EDI Parser → Port Database: Save staged payload and diagnostics, parse_status QUARANTINED
  - *Note:* Nothing reaches operational data
- **Otherwise — case: File unreadable**
  - EDI Parser → Port Database: parse_status FAILED (no staged data)
- Port API (BAPLIE) → Port Database: Read parse_status
- Port API (BAPLIE) → Web Dashboard (reply): SSE update
- Web Dashboard → Port Authority Staff (reply): Processed, or errors to review

#### 2.8 — BAPLIE correction, withdraw and vessel data

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 2.8. **Related:** AD-8. **Requirements:** FR-2.3, FR-2.5; NFR-SEC-6, NFR-SEC-7.

**Participants**

- **Port Authority Staff**: actor (person)
- **Web Dashboard**: boundary (user interface)
- **Port API (BAPLIE)**: control (service, API, worker or scheduler)
- **Port Database**: database (data store)

**Story**

After parsing, staff can fix a file that had errors, take back a file uploaded by mistake, or correct the vessel's data. All three are writes and are blocked in read-only mode.

Correcting. Staff open the diagnostics, which list the errors field by field on the staged data. They correct the data and submit it. The same rule set the parser uses checks it again. If it is still invalid nothing is committed. If it is valid, the commit is the same single transaction as a successful parse, and the file is marked as corrected by that staff member.

Withdrawing. A file can be withdrawn unless a confirmed plan used it; then the plan must be cancelled first and the answer is 409. Withdrawing deletes nothing. If the withdrawn file was the active one, the most recent replaced file of the same request becomes active again.

Vessel data. Staff can edit the vessel's particulars at any time outside read-only mode. Because the request form already requires the vessel dimensions, there is no incomplete-vessel state to wait for.

**Message flow, top to bottom**

- *Note:* Every write passes the check chain. Correction, withdraw and vessel edit return 423 in READ_ONLY.
- **Alternative paths — case: Review and correct a file with errors**
  - Port Authority Staff → Web Dashboard: Open diagnostics
  - Web Dashboard → Port API (BAPLIE): Get diagnostics
  - Port API (BAPLIE) → Port Database: Read staged payload and errors per field
  - Port API (BAPLIE) → Web Dashboard (reply): Diagnostics
  - Port Authority Staff → Web Dashboard: Correct the staged data
  - Web Dashboard → Port API (BAPLIE): Submit correction
  - Port API (BAPLIE) (internal): Validate with the shared rule set
  - **Alternative paths — case: Still invalid**
    - Port API (BAPLIE) → Web Dashboard (reply): Remaining errors, nothing committed
  - **Otherwise — case: Valid**
    - Port API (BAPLIE) → Port Database: Find or create vessel by IMO, fill empty fields only
    - Port API (BAPLIE) → Port Database: Earlier ACTIVE file REPLACED, store containers, file ACTIVE, parse_status PARSED
    - Port API (BAPLIE) → Port Database: Mark corrected_by and audit entry
    - *Note:* One transaction
    - Port API (BAPLIE) → Web Dashboard (reply): Corrected
- **Otherwise — case: Withdraw a file uploaded by mistake**
  - Port Authority Staff → Web Dashboard: Withdraw file
  - Web Dashboard → Port API (BAPLIE): Withdraw
  - Port API (BAPLIE) → Port Database: Read file and plans that used it
  - **Alternative paths — case: Already WITHDRAWN**
    - Port API (BAPLIE) → Web Dashboard (reply): 422 Invalid status transition
  - **Otherwise — case: A PLAN_CONFIRMED plan used it**
    - Port API (BAPLIE) → Web Dashboard (reply): 409 Cancel the plan first
  - **Otherwise — case: Allowed**
    - Port API (BAPLIE) → Port Database: Set WITHDRAWN (nothing deleted)
    - **Optional — only when: It was the ACTIVE file**
      - Port API (BAPLIE) → Port Database: Make the latest REPLACED file of the request ACTIVE again
    - Port API (BAPLIE) → Port Database: Audit entry
    - Port API (BAPLIE) → Web Dashboard (reply): Withdrawn
- **Otherwise — case: Edit vessel data**
  - Port Authority Staff → Web Dashboard: Edit vessel particulars
  - Web Dashboard → Port API (BAPLIE): Save vessel
  - **Alternative paths — case: Invalid**
    - Port API (BAPLIE) → Web Dashboard (reply): 422 Validation error
  - **Otherwise — case: Valid**
    - Port API (BAPLIE) → Port Database: Update vessel and audit entry
    - Port API (BAPLIE) → Web Dashboard (reply): Saved
- Web Dashboard → Port Authority Staff (reply): Show the result

#### 2.9 — Berthing request: create, change and review

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 2.9. **Related:** AD-9, SM-4. **Requirements:** FR-3.1, FR-3.4, FR-3.5, FR-3.7–FR-3.10; NFR-CONC-1.

**Participants**

- **Port Authority Staff**: actor (person)
- **Web Dashboard**: boundary (user interface)
- **Port API (Berthing)**: control (service, API, worker or scheduler)
- **Port Database**: database (data store)

**Story**

A vessel's call starts with a berthing request that Port Authority Staff create by hand. There is no automatic feed from outside systems.

Creating. The form asks for the vessel's identity and every particular the AI needs later: IMO, name, length, beam, maximum and arrival draft, block coefficient, deadweight and gross tonnage, plus the ETA and terminal. The vessel is found by its IMO number or created from the form. The request starts as SUBMITTED. Creation is blocked in read-only mode.

Changing. While the request is SUBMITTED or NEEDS_REVISION, staff can still edit it or cancel it with a reason. After preliminary approval, editing or cancelling returns 409.

Reviewing. A reviewer then decides. Approval moves the request to PRELIMINARY_APPROVED and needs full mode. Returning it for revision, with a reason, moves it to NEEDS_REVISION; the creator edits and resubmits, and it goes back to SUBMITTED. Rejecting, with a reason, ends it as REJECTED. Returning and rejecting are allowed even in read-only mode.

Every status change is written to the request's status history and to the audit log.

**Message flow, top to bottom**

- *Note:* Every request is created manually by staff. Each status change writes status history and an audit entry.
- Port Authority Staff → Web Dashboard: Fill the request (IMO, name, LOA, beam, max draft, arrival draft, block coefficient, DWT, GT, ETA, terminal)
- Web Dashboard → Port API (Berthing): POST /berthing-requests
- **Alternative paths — case: READ_ONLY**
  - Port API (Berthing) → Web Dashboard (reply): 423 LICENSE_READ_ONLY
- **Otherwise — case: Invalid values**
  - Port API (Berthing) → Web Dashboard (reply): 422 Validation error
- **Otherwise — case: Valid**
  - Port API (Berthing) → Port Database: Find or create the vessel by IMO with the form data
  - Port API (Berthing) → Port Database: Insert request SUBMITTED
  - Port API (Berthing) → Web Dashboard (reply): 201 Created
- **Optional — only when: Modify or cancel before preliminary approval**
  - Port Authority Staff → Web Dashboard: Edit, or cancel with a reason
  - Web Dashboard → Port API (Berthing): Update or cancel
  - **Alternative paths — case: READ_ONLY**
    - Port API (Berthing) → Web Dashboard (reply): 423 LICENSE_READ_ONLY
  - **Otherwise — case: Status not SUBMITTED or NEEDS_REVISION**
    - Port API (Berthing) → Web Dashboard (reply): 409 Conflict
  - **Otherwise — case: Cancel without a reason**
    - Port API (Berthing) → Web Dashboard (reply): 422 Reason required
  - **Otherwise — case: Allowed**
    - Port API (Berthing) → Port Database: Save the change, or set CANCELLED
    - Port API (Berthing) → Web Dashboard (reply): 200
- **Alternative paths — case: Approve**
  - Port Authority Staff → Web Dashboard: Record preliminary approval
  - Web Dashboard → Port API (Berthing): Approve
  - **Alternative paths — case: READ_ONLY**
    - Port API (Berthing) → Web Dashboard (reply): 423 LICENSE_READ_ONLY
  - **Otherwise — case: FULL**
    - Port API (Berthing) → Port Database: Status PRELIMINARY_APPROVED
    - Port API (Berthing) → Web Dashboard (reply): 200
- **Otherwise — case: Return for revision (allowed in READ_ONLY)**
  - Port Authority Staff → Web Dashboard: Return with a reason
  - Web Dashboard → Port API (Berthing): Return
  - Port API (Berthing) → Port Database: Status NEEDS_REVISION with the reason
  - Port API (Berthing) → Web Dashboard (reply): 200
  - **Optional — only when: Creator edits and resubmits**
    - Port Authority Staff → Web Dashboard: Edit and resubmit
    - Web Dashboard → Port API (Berthing): Resubmit
    - Port API (Berthing) → Port Database: Status SUBMITTED
- **Otherwise — case: Reject (allowed in READ_ONLY)**
  - Port Authority Staff → Web Dashboard: Reject with a reason
  - Web Dashboard → Port API (Berthing): Reject
  - Port API (Berthing) → Port Database: Status REJECTED with the reason
  - Port API (Berthing) → Web Dashboard (reply): 200

#### 2.10 — Customs approval and entry-window assessment

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 2.10. **Related:** AD-10, SM-4. **Requirements:** FR-3.6, FR-3.8, FR-10.8.

**Participants**

- **Port Authority Staff**: actor (person)
- **Port API (Berthing)**: control (service, API, worker or scheduler)
- **Port Database**: database (data store)
- **Part 1 Queue**: queue (Redis)
- **AI Part 1 Worker**: control (service, API, worker or scheduler)
- **Weather Providers**: external system

**Story**

Customs approval is the trigger for the first AI step. Part 1 works out when the vessel can safely enter the port.

Staff record customs approval on a preliminarily approved request. This needs full mode. The request becomes CUSTOMS_APPROVED, a Part 1 run is created as QUEUED and enqueued, and the answer comes back later over SSE.

Getting data. The Part 1 worker loads the request, the vessel's particulars, the channel and the safety limits. It asks the primary weather provider for wind, gust, visibility, waves and sea level. If the primary fails, an alert is logged in the application log and the secondary is tried. If both fail, stored data can be used only if it was measured within the last 48 hours and covers the request's time horizon.

Assessing. With usable data, the worker takes the astronomical tide (computing any missing hours), derives the surge as sea level minus tide, and checks wind, visibility, waves, tide and surge, under-keel clearance and squat against the approved limits. The outcome is either WINDOWS_FOUND, a set of feasible entry windows with the blocked periods, or NO_FEASIBLE_WINDOW with the limiting factor. A new run replaces the earlier one. Without usable data the outcome is ENV_DATA_UNAVAILABLE, which means the data is missing, not that conditions are unsafe.

A run that fails technically is retried up to three times.

**Message flow, top to bottom**

- Port Authority Staff → Port API (Berthing): Record customs approval
- **Alternative paths — case: READ_ONLY**
  - Port API (Berthing) → Port Authority Staff (reply): 423 LICENSE_READ_ONLY
- **Otherwise — case: Status not PRELIMINARY_APPROVED**
  - Port API (Berthing) → Port Authority Staff (reply): 409 Conflict
- **Otherwise — case: Valid**
  - Port API (Berthing) → Port Database: Status CUSTOMS_APPROVED
  - Port API (Berthing) → Port Database: Create part1_run QUEUED
  - Port API (Berthing) → Part 1 Queue: Enqueue Part 1 run
  - Port API (Berthing) → Port Authority Staff (reply): 202 Accepted, result by SSE
- Part 1 Queue → AI Part 1 Worker: Run (QUEUED to RUNNING)
- AI Part 1 Worker → Port Database: Load request, vessel particulars, channel and limits
- **Alternative paths — case: Request no longer CUSTOMS_APPROVED**
  - AI Part 1 Worker (internal): Discard the run
- **Otherwise — case: Eligible**
  - AI Part 1 Worker → Weather Providers: Weather and sea level from the primary provider
  - **Alternative paths — case: Primary fails**
    - AI Part 1 Worker (internal): Log an alert (application log)
    - AI Part 1 Worker → Weather Providers: Try the secondary provider
  - **Alternative paths — case: Fresh data received**
    - AI Part 1 Worker → Port Database: Store forecast
  - **Otherwise — case: Both providers fail**
    - AI Part 1 Worker → Port Database: Read stored data
    - AI Part 1 Worker (internal): Usable only if measured within 48 h and covering the horizon
  - **Alternative paths — case: Usable environmental data**
    - AI Part 1 Worker → Port Database: Read astronomical tide (compute missing hours)
    - AI Part 1 Worker (internal): Surge = sea level minus tide
    - AI Part 1 Worker (internal): Check wind, visibility, waves, tide and surge, UKC and squat against the limits
    - **Alternative paths — case: Feasible windows**
      - AI Part 1 Worker → Port Database: Store windows and blocked periods, outcome WINDOWS_FOUND (run DONE, earlier run REPLACED)
    - **Otherwise — case: NO_FEASIBLE_WINDOW**
      - AI Part 1 Worker → Port Database: Store blocked periods with the limiting factor, outcome NO_FEASIBLE_WINDOW
  - **Otherwise — case: No usable data**
    - AI Part 1 Worker → Port Database: Outcome ENV_DATA_UNAVAILABLE
- *Note:* A failed run is retried up to 3 times, then marked FAILED
- Port API (Berthing) → Port Authority Staff (reply): SSE update with the outcome

#### 2.11 — Entry-window decision

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 2.11. **Related:** AD-10, SM-4. **Requirements:** FR-3.8, FR-10.8.

**Participants**

- **Port Authority Staff**: actor (person)
- **Web Dashboard**: boundary (user interface)
- **Port API (Berthing)**: control (service, API, worker or scheduler)
- **Port Database**: database (data store)
- **Part 1 Queue**: queue (Redis)
- **Part 2 Queue**: queue (Redis)

**Story**

Part 1 suggests; staff decide. This is the first human gate.

No data. If the outcome was ENV_DATA_UNAVAILABLE, staff can enter environmental data by hand. It is checked for completeness and coverage, stored with pull_type MANUAL, provider_rank MANUAL and submitted_by, and a recompute is queued. The manual data is still validated like any other data; it never overrides a window. This is blocked in read-only mode.

NO_FEASIBLE_WINDOW. Staff press Recompute later, when conditions may have changed.

Feasible windows. Staff confirm one window or reject them all. Confirming needs full mode. The server checks that the window belongs to the latest result and still passes; if not, it answers 409 with the reason and staff recompute. There is no manual editing of a window and no override. A confirmed window moves the request to ENTRY_WINDOW_CONFIRMED and queues the Part 2 recommendation. Rejecting all windows, with a reason, is allowed in read-only mode: the proposal becomes REJECTED with rejection_reason and rejected_by, and the request stays CUSTOMS_APPROVED and waits for a new assessment.

Reopening. If a confirmed window can no longer be used and no plan is confirmed, staff can reopen it with a reason. The request goes back to CUSTOMS_APPROVED and Part 1 runs again.

**Message flow, top to bottom**

- Port Authority Staff → Web Dashboard: Open the Part 1 result
- Web Dashboard → Port API (Berthing): Get latest result
- Port API (Berthing) → Port Database: Read windows, blocked periods, data sources
- Port API (Berthing) → Web Dashboard (reply): Result
- **Alternative paths — case: ENV_DATA_UNAVAILABLE**
  - Port Authority Staff → Web Dashboard: Enter manual environmental data
  - Web Dashboard → Port API (Berthing): Submit manual data
  - **Alternative paths — case: READ_ONLY**
    - Port API (Berthing) → Web Dashboard (reply): 423 LICENSE_READ_ONLY
  - **Otherwise — case: Invalid or not covering the horizon**
    - Port API (Berthing) → Web Dashboard (reply): 422 Validation error
  - **Otherwise — case: Valid**
    - Port API (Berthing) → Port Database: Store data (pull_type MANUAL, provider_rank MANUAL, submitted_by)
    - Port API (Berthing) → Part 1 Queue: Recompute
- **Otherwise — case: NO_FEASIBLE_WINDOW**
  - Port Authority Staff → Web Dashboard: Recompute later
  - Web Dashboard → Port API (Berthing): Recompute
  - Port API (Berthing) → Part 1 Queue: New Part 1 run (423 in READ_ONLY)
- **Otherwise — case: Feasible windows**
  - **Alternative paths — case: Confirm one window**
    - Port Authority Staff → Web Dashboard: Select a window
    - Web Dashboard → Port API (Berthing): Confirm window
    - **Alternative paths — case: READ_ONLY**
      - Port API (Berthing) → Web Dashboard (reply): 423 LICENSE_READ_ONLY
    - **Otherwise — case: Window not in the latest result, or server check fails**
      - Port API (Berthing) → Web Dashboard (reply): 409 with the reason, press Recompute
    - **Otherwise — case: Valid**
      - Port API (Berthing) → Port Database: Status ENTRY_WINDOW_CONFIRMED, store the window
      - Port API (Berthing) → Part 2 Queue: Enqueue Part 2 recommendation
      - Port API (Berthing) → Web Dashboard (reply): 200 Window confirmed
  - **Otherwise — case: Reject all windows (allowed in READ_ONLY)**
    - Port Authority Staff → Web Dashboard: Reject all with a reason
    - Web Dashboard → Port API (Berthing): Reject all windows
    - Port API (Berthing) → Port Database: Proposal REJECTED with rejection_reason and rejected_by, request stays CUSTOMS_APPROVED
    - Port API (Berthing) → Web Dashboard (reply): 200 Waiting for a new assessment
- **Optional — only when: Reopen a confirmed window**
  - Port Authority Staff → Web Dashboard: Reopen with a reason
  - Web Dashboard → Port API (Berthing): Reopen window
  - **Alternative paths — case: READ_ONLY**
    - Port API (Berthing) → Web Dashboard (reply): 423 LICENSE_READ_ONLY
  - **Otherwise — case: Not ENTRY_WINDOW_CONFIRMED, or a plan is confirmed**
    - Port API (Berthing) → Web Dashboard (reply): 409 Conflict
  - **Otherwise — case: Allowed**
    - Port API (Berthing) → Port Database: Status CUSTOMS_APPROVED
    - Port API (Berthing) → Part 1 Queue: New Part 1 run
    - Port API (Berthing) → Web Dashboard (reply): 200 Reopened

#### 2.12 — Weather and environmental data

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 2.12. **Related:** AD-10. **Requirements:** NFR-REL-4 (environmental data comes from the proposal and master context; the FRD has no item for it).

**Participants**

- **Office User**: actor (person)
- **Part 1 Scheduler**: control (service, API, worker or scheduler)
- **AI Part 1 Worker**: control (service, API, worker or scheduler)
- **Weather Providers**: external system
- **Port Database**: database (data store)
- **Port API**: control (service, API, worker or scheduler)

**Story**

Part 1 needs weather, sea level and tide. This diagram shows how the port keeps that data, independently of any vessel.

Polling. Every six hours the Part 1 scheduler pulls weather and sea level from the primary provider. If the primary fails, the failure and an alert are logged in the application log and the secondary provider is tried. If both fail, the last data is kept but marked stale. All calls go out from the port; providers never call in.

Tide. Once a day the worker computes the astronomical tide from published harmonic constants with pyTMD, in-house. No external tide service is used. A failed computation keeps the existing predictions.

Using it. Stored data counts as usable for an assessment only if it was measured within the last 48 hours and covers the request's time horizon. Otherwise the assessment ends as ENV_DATA_UNAVAILABLE, as shown in the entry-window diagrams.

Viewing. Any office user can see the current conditions, with the surge derived on the fly, the source and the age of the data. Stale, partial or manual data is shown with a clear warning.

**Message flow, top to bottom**

- *Note:* All provider calls go out from the port. The port exposes no inbound endpoint.
- **Loop: Every 6 hours**
  - Part 1 Scheduler → AI Part 1 Worker: Pull weather and sea level
  - AI Part 1 Worker → Weather Providers: Request from the primary provider
  - **Alternative paths — case: Primary data valid**
    - AI Part 1 Worker → Port Database: Store forecast (PRIMARY, data_stale false)
  - **Otherwise — case: Primary fails**
    - AI Part 1 Worker (internal): Log the failure and an alert (application log)
    - AI Part 1 Worker → Weather Providers: Request from the secondary provider
    - **Alternative paths — case: Secondary data valid**
      - AI Part 1 Worker → Port Database: Store forecast (SECONDARY, data_stale false)
    - **Otherwise — case: Both fail**
      - AI Part 1 Worker → Port Database: Keep the last data, set data_stale true
- Part 1 Scheduler → AI Part 1 Worker: Daily tide job
- AI Part 1 Worker (internal): Compute astronomical tide from harmonic constants (pyTMD)
- **Alternative paths — case: Computed**
  - AI Part 1 Worker → Port Database: Store hourly tide predictions
- **Otherwise — case: Error**
  - AI Part 1 Worker → Port Database: Keep existing predictions, log the failure
- *Note:* For an assessment, stored data is usable only if measured within 48 h and covering the horizon. Otherwise the outcome is ENV_DATA_UNAVAILABLE.
- Office User → Port API: View environmental conditions
- Port API → Port Database: Read latest weather, sea level, tide, source, age
- Port API (internal): Surge = sea level minus tide
- **Alternative paths — case: Data fresh**
  - Port API → Office User (reply): Conditions with source and last update
- **Otherwise — case: Stale, partial or manual**
  - Port API → Office User (reply): Conditions with a stale-data warning, age and source

#### 2.13 — Recommendation generation and review

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 2.13. **Related:** AD-11, AD-12, SM-4. **Requirements:** FR-4.1–FR-4.9; NFR-PERF-1, NFR-ENG-1, NFR-UX-1, NFR-CAP-2.

**Participants**

- **Port Authority Staff**: actor (person)
- **Port API (Berthing)**: control (service, API, worker or scheduler)
- **Port Database**: database (data store)
- **Part 2 Queue**: queue (Redis)
- **AI Part 2 Worker**: control (service, API, worker or scheduler)

**Story**

With the entry window confirmed, AI Part 2 proposes one port-wide plan: which berth, which tugs and which pilot, and when.

Generating. The Part 2 worker loads the confirmed window, the Part 1 constraints, the cargo manifest, the live availability of berths, tugs and pilots, and the safety constraints. It first removes every option that breaks a hard safety rule, estimates service time and delay risk, and runs the solver. Three outcomes are possible. Solved: a recommendation version PENDING_REVIEW with source AI, ranked options and a rationale. Solver error or timeout: a simple first-in-first-out plan with source FIFO, passed through the same safety filter; the failure reason is stored in solver_run.result_detail. Infeasible: NO_FEASIBLE_PLAN with the constraints that blocked it, stored in solver_run.result_detail; no FIFO plan is made, the request stays ENTRY_WINDOW_CONFIRMED, and staff may regenerate later.

Reviewing. Staff see each option with its berth, times, tugs, pilot, service-time estimates, delay risk and rationale. The system records who reviewed which version (recommendation_review). While versions change, the request itself stays RECOMMENDATION_GENERATED.

Override. Staff can replace one component with a reason. The new value is checked against availability and safety constraints. A valid override creates a new version marked MODIFIED_BY_STAFF.

Regenerate. Staff can ask Part 2 to solve again with updated context. A successful re-solve creates a new version and the previous one becomes REPLACED. If it fails, or read-only mode blocks it, the previous version stays current. On a confirmed plan, regenerate returns 409.

**Message flow, top to bottom**

- Part 2 Queue → AI Part 2 Worker: Run after ENTRY_WINDOW_CONFIRMED
- AI Part 2 Worker → Port Database: Load confirmed window, Part 1 constraints, manifest, live berth, tug and pilot state, safety constraints
- AI Part 2 Worker (internal): Hard safety filter, service time, delay risk, solve
- **Alternative paths — case: Solved**
  - AI Part 2 Worker → Port Database: Store recommendation version PENDING_REVIEW, source AI (ranked options with rationale)
  - Port API (Berthing) → Port Authority Staff (reply): SSE ranked options ready
- **Otherwise — case: Solver error or timeout**
  - AI Part 2 Worker → Port Database: Store FIFO plan with source FIFO (same hard filter), failure reason in solver_run.result_detail
  - Port API (Berthing) → Port Authority Staff (reply): SSE fallback plan ready
- **Otherwise — case: Infeasible**
  - AI Part 2 Worker → Port Database: Outcome NO_FEASIBLE_PLAN, binding constraints in solver_run.result_detail
  - Port API (Berthing) → Port Authority Staff (reply): SSE no feasible plan, request stays ENTRY_WINDOW_CONFIRMED
- *Note:* The request stays RECOMMENDATION_GENERATED while versions change
- Port Authority Staff → Port API (Berthing): Review the recommendation
- Port API (Berthing) → Port Database: Read options, record who viewed which version (recommendation_review)
- Port API (Berthing) → Port Authority Staff (reply): Berth, start, end, tugs, pilot, service time, delay risk, rationale
- **Optional — only when: Override a component**
  - Port Authority Staff → Port API (Berthing): Override with a new value and a reason
  - **Alternative paths — case: READ_ONLY**
    - Port API (Berthing) → Port Authority Staff (reply): 423 LICENSE_READ_ONLY
  - **Otherwise — case: Version outdated or plan confirmed**
    - Port API (Berthing) → Port Authority Staff (reply): 409 Review the latest version
  - **Otherwise — case: New value breaks a constraint**
    - Port API (Berthing) → Port Authority Staff (reply): 422 Override rejected with reason
  - **Otherwise — case: Valid**
    - Port API (Berthing) → Port Database: Save override, new version MODIFIED_BY_STAFF
    - Port API (Berthing) → Port Authority Staff (reply): 200 Updated recommendation
- **Optional — only when: Regenerate**
  - Port Authority Staff → Port API (Berthing): Regenerate with context changes
  - **Alternative paths — case: READ_ONLY**
    - Port API (Berthing) → Port Authority Staff (reply): 423, the current version stays
  - **Otherwise — case: Plan already confirmed**
    - Port API (Berthing) → Port Authority Staff (reply): 409 Use cancel or delay re-plan
  - **Otherwise — case: Accepted**
    - Port API (Berthing) → Part 2 Queue: Enqueue re-solve
    - Part 2 Queue → AI Part 2 Worker: Re-solve with live state
    - **Alternative paths — case: Success**
      - AI Part 2 Worker → Port Database: New version, previous version REPLACED
    - **Otherwise — case: Failure or infeasible**
      - AI Part 2 Worker → Port Database: Record failure, previous version stays current
    - Port API (Berthing) → Port Authority Staff (reply): SSE result

#### 2.14 — Plan confirmation, cancellation and delay re-plan

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 2.14. **Related:** AD-11, AD-12, SM-4, SM-5. **Requirements:** FR-3.11, FR-4.6–FR-4.8; NFR-REL-5, NFR-CONC-1.

**Participants**

- **Port Authority Staff**: actor (person)
- **Port Admin**: actor (person)
- **Port API (Berthing)**: control (service, API, worker or scheduler)
- **Port Database**: database (data store)
- **Part 2 Queue**: queue (Redis)
- **AI Part 2 Worker**: control (service, API, worker or scheduler)

**Story**

Confirming the plan is the second human gate. This diagram also covers the ways a confirmed plan can change afterwards.

Confirming. Staff confirm a reviewed, current version in full mode. In one transaction the server locks and re-checks that the berth, tugs and pilot are still free, books them, creates the operational plan as CONFIRMED, sets the version CONFIRMED and moves the request to PLAN_CONFIRMED. If anything was taken in the meantime, everything rolls back and staff regenerate. The confirmed plan is what dispatch works from.

Cancelling. Staff can cancel a confirmed plan with a reason as long as no part of it has started. Resources are released and the request becomes PLAN_CANCELLED. If the vessel's call continues, the request goes back to ENTRY_WINDOW_CONFIRMED and a new recommendation is made and reviewed again; if not, PLAN_CANCELLED is its last state.

Safety exception. Once any component has started, normal cancellation returns 409. Only the Port Admin can then cancel the remaining work, with a mandatory reason, as a recorded safety exception. This is allowed even in read-only mode.

Delay re-plan. When execution tracking reports a significant delay, Part 2 prepares a proposal version with purpose DELAY_REPLAN while the current plan stays confirmed. Nothing changes until staff confirm it. Then, in one transaction, new resources are reserved, unused ones released, started components kept as they are, the old version becomes REPLACED, the proposal becomes the INITIAL version and changed components go back to assignment. If this fails, everything rolls back.

**Message flow, top to bottom**

- Port Authority Staff → Port API (Berthing): Confirm the plan (version)
- **Alternative paths — case: READ_ONLY**
  - Port API (Berthing) → Port Authority Staff (reply): 423 LICENSE_READ_ONLY
- **Otherwise — case: Version outdated or not reviewed**
  - Port API (Berthing) → Port Authority Staff (reply): 409 Review the latest version
- **Otherwise — case: Write allowed**
  - Port API (Berthing) → Port Database: Lock and re-check berth, tugs and pilot
  - **Alternative paths — case: All still free**
    - Port API (Berthing) → Port Database: Book resources, create operational plan CONFIRMED, request PLAN_CONFIRMED, set version CONFIRMED
    - *Note:* One transaction
    - Port API (Berthing) → Port Authority Staff (reply): 200 Plan confirmed
  - **Otherwise — case: A resource was taken**
    - Port API (Berthing) → Port Database: Roll back
    - Port API (Berthing) → Port Authority Staff (reply): 409 Resources changed, regenerate
- **Optional — only when: Cancel a confirmed plan**
  - Port Authority Staff → Port API (Berthing): Cancel with a reason
  - **Alternative paths — case: READ_ONLY**
    - Port API (Berthing) → Port Authority Staff (reply): 423 LICENSE_READ_ONLY
  - **Otherwise — case: A component already STARTED**
    - Port API (Berthing) → Port Authority Staff (reply): 409 Only the Port Admin safety exception
  - **Otherwise — case: Allowed**
    - Port API (Berthing) → Port Database: Plan CANCELLED, release resources, request PLAN_CANCELLED
    - Port API (Berthing) → Port Authority Staff (reply): 200 Cancelled
    - **Optional — only when: The call continues**
      - Port API (Berthing) → Port Database: Request back to ENTRY_WINDOW_CONFIRMED
      - Port API (Berthing) → Part 2 Queue: New recommendation (review and confirmation again)
- **Optional — only when: Safety exception after work has started**
  - Port Admin → Port API (Berthing): Cancel remaining components with a reason (allowed in READ_ONLY)
  - Port API (Berthing) → Port Database: Plan CANCELLED, request PLAN_CANCELLED, release unused resources
  - Port API (Berthing) → Port Database: Audit entry SAFETY_EXCEPTION
  - Port API (Berthing) → Port Admin (reply): 200
- **Optional — only when: Significant delay reported by execution tracking**
  - Port API (Berthing) → Part 2 Queue: Enqueue delay re-plan
  - Part 2 Queue → AI Part 2 Worker: Re-plan on the rolling horizon
  - AI Part 2 Worker → Port Database: Store a proposal version with purpose DELAY_REPLAN (the plan stays CONFIRMED)
  - Port API (Berthing) → Port Authority Staff (reply): SSE proposal ready
  - Port Authority Staff → Port API (Berthing): Confirm the proposal
  - Port API (Berthing) → Port Database: Reserve new resources, release unused ones, keep STARTED components
  - Port API (Berthing) → Port Database: Old version REPLACED, changed components back to assignment
  - *Note:* One transaction. On failure everything rolls back and the old version stays confirmed.
  - Port API (Berthing) → Port Authority Staff (reply): 200 Re-plan confirmed

#### 2.15 — Dispatch, notifications and acknowledgement

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 2.15. **Related:** AD-13, SM-5. **Requirements:** FR-5.1, FR-5.2, FR-7.1–FR-7.3; NFR-UX-2, NFR-PERF-4.

**Participants**

- **Pilotage Officer**: actor (person)
- **Tug Officer**: actor (person)
- **Pilot or Tug Master**: actor (person)
- **Port API (Dispatch)**: control (service, API, worker or scheduler)
- **Port Database**: database (data store)
- **Reminder Scheduler**: control (service, API, worker or scheduler)
- **Realtime Server (Reverb)**: control (service, API, worker or scheduler)

**Story**

Once the plan is confirmed, the pilotage and tug officers turn it into real assignments. The two departments work in parallel.

Assigning. The plan already proposes a pilot and a tug. The officer confirms the proposal or replaces it. A replacement is checked for availability, qualification and conflicts, and is logged against the plan. Assigning needs full mode and a confirmed plan. A valid assignment is saved, acknowledgement retries are scheduled, and the realtime server pushes the new task to the pilot's or tug master's phone.

Acknowledging. The field user acknowledges from the app. The acknowledgement goes through the phone's Outbox, so it works even without coverage and reaches the server when the phone syncs. It marks the notification ACKNOWLEDGED; the plan's own state does not change. Remaining retries are cancelled and the officer sees it live.

Retries and escalation. If nobody acknowledges, the task is sent again 10 and 20 minutes after the first send. At 30 minutes the system sends an ACK_ESCALATION notification to the officer who assigned it and to the department manager.

**Message flow, top to bottom**

- *Note:* The confirmed plan proposes the pilot and the tug. The officer confirms or replaces them.
- **In parallel — branch: Pilotage**
  - Pilotage Officer → Port API (Dispatch): Confirm or replace the proposed pilot and boarding time
- **And in parallel: Tug**
  - Tug Officer → Port API (Dispatch): Confirm or replace the proposed tug and time
- **Alternative paths — case: READ_ONLY**
  - Port API (Dispatch) → Pilotage Officer (reply): 423 LICENSE_READ_ONLY
- **Otherwise — case: No confirmed plan**
  - Port API (Dispatch) → Pilotage Officer (reply): 409 Conflict
- **Otherwise — case: Not available, not qualified or in conflict**
  - Port API (Dispatch) → Pilotage Officer (reply): 422 Rejected with reason
- **Otherwise — case: Valid**
  - Port API (Dispatch) → Port Database: Save assignment (replacement logged against the plan), audit entry
  - Port API (Dispatch) → Reminder Scheduler: Schedule acknowledgement retries at T+10 and T+20
  - Port API (Dispatch) → Realtime Server (Reverb): Push task notification
  - Realtime Server (Reverb) → Pilot or Tug Master (reply): New task
  - Port API (Dispatch) → Pilotage Officer (reply): 200 Assigned and notified
- **Loop: Until acknowledged**
  - **Alternative paths — case: Field user acknowledges**
    - Pilot or Tug Master → Port API (Dispatch): Acknowledge (sent through the phone Outbox)
    - Port API (Dispatch) → Port Database: Mark the notification ACKNOWLEDGED
    - Port API (Dispatch) → Reminder Scheduler: Cancel remaining retries
    - Port API (Dispatch) → Pilotage Officer (reply): SSE task acknowledged
  - **Otherwise — case: Retry due (T+10, T+20)**
    - Reminder Scheduler → Port API (Dispatch): Retry due
    - Port API (Dispatch) → Port Database: Still not acknowledged
    - Port API (Dispatch) → Realtime Server (Reverb): Push retry
    - Realtime Server (Reverb) → Pilot or Tug Master (reply): Retry
  - **Otherwise — case: No answer at T+30**
    - Reminder Scheduler → Port API (Dispatch): Escalation due
    - Port API (Dispatch) → Pilotage Officer (reply): ACK_ESCALATION to the assigning officer and the department manager

#### 2.16 — Yard placement and TOS hand-off

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 2.16. **Related:** AD-14, SM-5. **Requirements:** FR-8.5–FR-8.8; NFR-INT-4, NFR-SEC-7.

**Participants**

- **CT Operation Planner**: actor (person)
- **Port API (Container Terminal)**: control (service, API, worker or scheduler)
- **Port Database**: database (data store)
- **Part 2 Queue**: queue (Redis)
- **AI Part 2 Worker**: control (service, API, worker or scheduler)

**Story**

For a container vessel, Part 2 also suggests where its containers should go in the yard. This is advice to the terminal planner; it does not allocate anything.

Generating. When a plan is confirmed for a container vessel that has an active BAPLIE, the yard recommendation is requested automatically. Part 2 loads the containers, the yard structure and the schedule and produces placements with a rationale and confidence. If generation fails, the planner is told and can request it again or reject it.

Deciding. The planner accepts the recommendation, accepts it with adjustments, or rejects it with a reason. Accepting is a decision only: no slots are reserved and no occupancy is checked. Accepting needs full mode; rejecting is allowed in read-only mode. After a rejection the plan's yard part stays pending until a new recommendation is accepted.

Hand-off. ATLANTECH has no automatic link to the terminal's TOS. It shows a TOS-ready version of the accepted plan; the planner types it into the TOS outside ATLANTECH and then records that it was exported. Nothing comes back from the TOS.

**Message flow, top to bottom**

- *Note:* Requested automatically when a plan is confirmed for a container vessel with an ACTIVE BAPLIE
- Port API (Container Terminal) → Port Database: Yard recommendation YARD_REC_REQUESTED
- Port API (Container Terminal) → Part 2 Queue: Enqueue yard job
- Part 2 Queue → AI Part 2 Worker: Generate placement
- AI Part 2 Worker → Port Database: Load containers, yard structure and schedule
- **Alternative paths — case: Produced**
  - AI Part 2 Worker → Port Database: Store placements, rationale, confidence (YARD_REC_GENERATED)
  - Port API (Container Terminal) → CT Operation Planner (reply): SSE recommendation ready
- **Otherwise — case: Error or timeout**
  - AI Part 2 Worker → Port Database: GENERATION_FAILED with reason
  - Port API (Container Terminal) → CT Operation Planner (reply): SSE generation failed, request again or reject
- CT Operation Planner → Port API (Container Terminal): Open the recommendation
- Port API (Container Terminal) → CT Operation Planner (reply): Placements, rationale, confidence
- **Alternative paths — case: Accept, or accept with adjustments**
  - CT Operation Planner → Port API (Container Terminal): Accept
  - **Alternative paths — case: READ_ONLY**
    - Port API (Container Terminal) → CT Operation Planner (reply): 423 LICENSE_READ_ONLY
  - **Otherwise — case: FULL**
    - Port API (Container Terminal) → Port Database: YARD_REC_ACCEPTED (decision only, no slot reservation)
    - Port API (Container Terminal) → CT Operation Planner (reply): 200
- **Otherwise — case: Reject (allowed in READ_ONLY)**
  - CT Operation Planner → Port API (Container Terminal): Reject with a reason
  - Port API (Container Terminal) → Port Database: YARD_REC_REJECTED, plan yard stays YARD_PENDING
  - Port API (Container Terminal) → CT Operation Planner (reply): 200, request a new one when ready
- **Optional — only when: Hand-off to the terminal TOS**
  - CT Operation Planner → Port API (Container Terminal): Get the TOS-ready plan
  - Port API (Container Terminal) → CT Operation Planner (reply): TOS-ready payload
  - CT Operation Planner (internal): Enter it into the TOS outside ATLANTECH
  - CT Operation Planner → Port API (Container Terminal): Record EXPORTED_TO_TOS (allowed in READ_ONLY)
  - Port API (Container Terminal) → Port Database: EXPORTED_TO_TOS, audit entry

#### 2.17 — Device enrollment, VPN and lost devices

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 2.17. **Related:** AD-19. **Requirements:** NFR-SEC-4 (devices and VPN come from the master context; the FRD has no item for them).

**Participants**

- **Port IT Administrator**: actor (person)
- **Remote Field User**: actor (person)
- **Port Admin**: actor (person)
- **MDM Platform**: external system
- **Managed Device**: external system
- **VPN Gateway**: external system
- **Port API**: control (service, API, worker or scheduler)

**Story**

Field phones reach the port server only through the port's VPN. Port IT manages the phones and the network with the port's own tools; ATLANTECH has no device-management component of its own.

Enrollment. Port IT enrolls each phone in the MDM and assigns its user; the phone never enrolls itself. The MDM issues the device certificate and installs it together with the app and the VPN profile. A failed installation is reported so Port IT can retry.

VPN. Port IT can change the gateway's routes, address pools and policy at any time; a rejected change keeps the old settings. When a field user opens the app, the always-on VPN connects and the gateway checks the device certificate. A valid certificate opens the tunnel to the port server; an invalid, expired or revoked one is refused.

Lost device. Port IT revokes the certificate in the MDM, which closes the tunnel, and orders a selective wipe, which happens at once or at the phone's next check-in. Port IT then tells the Port Admin, who revokes the device's API tokens in ATLANTECH. Any events that were still waiting in that phone's Outbox are lost.

**Message flow, top to bottom**

- *Note:* MDM and VPN gateway are port infrastructure managed by Port IT
- Port IT Administrator → MDM Platform: Enroll the device and assign its user
- MDM Platform (internal): Issue the device certificate
- MDM Platform → Managed Device: Install certificate, app and VPN profile
- **Alternative paths — case: Installed**
  - Managed Device → MDM Platform (reply): Done
  - MDM Platform → Port IT Administrator (reply): Device ready
- **Otherwise — case: Installation failed**
  - Managed Device → MDM Platform (reply): Error
  - MDM Platform → Port IT Administrator (reply): Enrollment incomplete, retry
- **Optional — only when: Manage the VPN gateway**
  - Port IT Administrator → VPN Gateway: Update routes, address pools, policy
  - VPN Gateway → Port IT Administrator (reply): Applied, or rejected with the old settings kept
- Remote Field User → Managed Device: Open the app
- Managed Device → VPN Gateway: Connect through the always-on VPN
- VPN Gateway (internal): Validate the device certificate
- **Alternative paths — case: Valid**
  - VPN Gateway → Managed Device (reply): Tunnel open, port server reachable
- **Otherwise — case: Invalid, expired or revoked**
  - VPN Gateway → Managed Device (reply): Rejected
  - Managed Device → Remote Field User (reply): Contact Port IT
- **Optional — only when: Device lost or stolen**
  - Port IT Administrator → MDM Platform: Revoke the certificate and selective wipe
  - MDM Platform → VPN Gateway: Certificate revoked, tunnel closed
  - **Alternative paths — case: Device reachable**
    - MDM Platform → Managed Device: Wipe
  - **Otherwise — case: Device offline**
    - MDM Platform (internal): Wipe on next check-in
  - Port IT Administrator → Port Admin (reply): Inform the Port Admin
  - Port Admin → Port API: Revoke the device API tokens
  - Port API (internal): Set revoked_at on the tokens, audit entry
  - *Note:* Outbox events not yet sent from a wiped device are lost

### Activity diagrams of category 2

#### AD-8 — BAPLIE upload, parsing and correction

**Code:** `activity-diagrams-v3/ATLANTECH_Activity_Diagrams.md`, diagram AD-8. **Related:** 2.7, 2.8. **Requirements:** FR-2.1–FR-2.6; NFR-PERF-2, NFR-INT-1, NFR-REL-4, NFR-UX-4.

**Swimlanes:** Port Authority Staff, Port Server, EDI Parser.

**Story**

This diagram shows how a vessel's BAPLIE stowage file enters the system, how errors are handled and how a file is withdrawn. Three lanes take part: Port Authority Staff, the port server and the EDI parser.

Upload. Staff pick the berthing request the file belongs to, or leave it empty so the server can match it. The server refuses the upload in read-only mode. It stores the file and its SHA-256 hash and creates the record as STAGED with parse status PENDING, then makes sure the request is known: either it was selected, or exactly one request matches the vessel's IMO number with an ETA within 24 hours; otherwise it answers 422 and staff must select the request. The same file (same hash) uploaded again for the same request is refused with 409, unless the earlier copy was withdrawn.

Parsing. The EDI parser reads the file according to EDIFACT D.17A and the SMDG 2019 guide and validates it. If the vessel's IMO in the file does not match the request, or parsing fails, it writes specific diagnostics. Nothing partial is published: the extracted payload and the diagnostics are kept as staged data with parse status QUARANTINED. A file that cannot be read at all gets parse status FAILED and no staged data.

Fixing errors. Staff read the diagnostics and choose: correct the staged data (validated again, blocked in read-only mode), upload a corrected file, withdraw the file, or leave it for later.

Success. A valid file is committed in one transaction: the vessel is found or created by IMO (only empty fields are filled), the request's previous active file becomes REPLACED, the containers are saved and the new file becomes ACTIVE. The parse status becomes PARSED and the dashboard is updated live.

Withdraw. A file can be withdrawn unless a confirmed plan uses it (then the plan must be cancelled first, 409). Withdrawing makes the latest replaced file of the request active again and is audited. Upload, correction and withdraw are all blocked in read-only mode.

**Step-by-step flow** (each step lists where it goes next; END is a final node)

- **START** start → D0 "Triggering event?"
- **D0** Decision "Triggering event?": "Upload" → A1 "Select the Berthing Request, or leave it empty for auto-match, and upload the BAPLIE file"; "Withdraw" → W0 "Withdraw a BAPLIE file"
- **A1** [Port Authority Staff] Select the Berthing Request, or leave it empty for auto-match, and upload the BAPLIE file → D1 "READ_ONLY?"
- **W0** [Port Authority Staff] Withdraw a BAPLIE file → DWR "READ_ONLY?"
- **D1** [Port Server] Decision "READ_ONLY?": "Yes" → A2 "Reject with 423 LICENSE_READ_ONLY"; "No" → A3 "Store the file, compute its SHA-256 hash, create the record: status STAGED, parse_status PENDING"
- **DWR** [Port Server] Decision "READ_ONLY?": "Yes" → A2 "Reject with 423 LICENSE_READ_ONLY"; "No" → DW "File used by a PLAN_CONFIRMED plan?"
- **A2** [Port Server] Reject with 423 LICENSE_READ_ONLY → END
- **A3** [Port Server] Store the file, compute its SHA-256 hash, create the record: status STAGED, parse_status PENDING → DM "Request selected or auto-matched?"
- **DW** [Port Server] Decision "File used by a PLAN_CONFIRMED plan?": "Yes" → W3 "Return 409 - cancel the plan first"; "No" → W2 "Set WITHDRAWN; the latest REPLACED file of the request becomes ACTIVE; audit entry"
- **DM** [Port Server] Decision "Request selected or auto-matched?": "No" → AM "Reject 422 - select the request"; "Yes" → D2 "Duplicate file for this request?"
- **W3** [Port Server] Return 409 - cancel the plan first → END
- **W2** [Port Server] Set WITHDRAWN; the latest REPLACED file of the request becomes ACTIVE; audit entry → END
- **AM** [Port Server] Reject 422 - select the request → END
- **D2** [Port Server] Decision "Duplicate file for this request?": "Yes" → A4 "Reject 409 duplicate"; "No" → A5 "Queue parse job for the EDI Parser"
- **A4** [Port Server] Reject 409 duplicate → END
- **A5** [Port Server] Queue parse job for the EDI Parser → A6 "Parse BAPLIE per D.17A and SMDG 2019"
- **A6** [EDI Parser] Parse BAPLIE per D.17A and SMDG 2019 → DR "File readable?"
- **DR** [EDI Parser] Decision "File readable?": "No" → A21 "File cannot be read - parse_status FAILED, no staged data"; "Yes" → A7 "Validate content"
- **A21** [EDI Parser] File cannot be read - parse_status FAILED, no staged data → A10 "Review the error message and diagnostics"
- **A7** [EDI Parser] Validate content → DI "Vessel IMO matches the request?"
- **A10** [Port Authority Staff] Review the error message and diagnostics → D5 "Next step?"
- **DI** [EDI Parser] Decision "Vessel IMO matches the request?": "No" → A8 "Write specific diagnostics - blocking"; "Yes" → D3 "Parsing and validation successful?"
- **D5** [Port Authority Staff] Decision "Next step?": "Correct staged data" → A15 "Correct or supplement the staged data"; "Upload a corrected file" → A1 "Select the Berthing Request, or leave it empty for auto-match, and upload the BAPLIE file"; "Withdraw the file" → W0 "Withdraw a BAPLIE file"; "Leave it" → END
- **A8** [EDI Parser] Write specific diagnostics - blocking → A9 "Save extracted payload and diagnostics as staged data"
- **D3** [EDI Parser] Decision "Parsing and validation successful?": "No" → A8 "Write specific diagnostics - blocking"; "Yes" → A11 "Extract vessel configuration, container manifest, stowage and timing"
- **A15** [Port Authority Staff] Correct or supplement the staged data → DC "READ_ONLY?"
- **A9** [EDI Parser] Save extracted payload and diagnostics as staged data → A19 "parse_status QUARANTINED (staged data kept) and log the reason"
- **A11** [EDI Parser] Extract vessel configuration, container manifest, stowage and timing → A12 "In one transaction: find-or-create vessel by IMO (fill empty fields only), previous ACTIVE file of the request becomes REPLACED, save containers, file ACTIVE"
- **DC** [Port Server] Decision "READ_ONLY?": "Yes" → A2 "Reject with 423 LICENSE_READ_ONLY"; "No" → V1 "Validate the corrected data"
- **A19** [EDI Parser] parse_status QUARANTINED (staged data kept) and log the reason → A10 "Review the error message and diagnostics"
- **A12** [EDI Parser] In one transaction: find-or-create vessel by IMO (fill empty fields only), previous ACTIVE file of the request becomes REPLACED, save containers, file ACTIVE → D7 "Committed?"
- **V1** [Port Server] Validate the corrected data → DV "Corrected data valid?"
- **D7** [EDI Parser] Decision "Committed?": "No - rolled back" → A9 "Save extracted payload and diagnostics as staged data"; "Yes" → A20 "parse_status PARSED"
- **DV** [Port Server] Decision "Corrected data valid?": "No" → A10 "Review the error message and diagnostics"; "Yes" → A12 "In one transaction: find-or-create vessel by IMO (fill empty fields only), previous ACTIVE file of the request becomes REPLACED, save containers, file ACTIVE"
- **A20** [Port Server] parse_status PARSED → A13 "Notify dashboard via SSE"
- **A13** [Port Server] Notify dashboard via SSE → A14 "Review parsed vessel and cargo data"
- **A14** [Port Authority Staff] Review parsed vessel and cargo data → END

**Rules stated as notes**

- BAPLIE upload is a new write and is blocked in READ_ONLY. Duplicate = same SHA-256 hash for the same request, earlier copy not WITHDRAWN (attached to D1)
- Correction, withdraw and vessel edit are blocked in READ_ONLY (423) (attached to DC)
- A failed import is never published downstream as a partial result (attached to A9)
- Auto-match needs exactly one request with the same IMO and an ETA within 24 h (attached to DM)

#### AD-9 — Berthing request lifecycle

**Code:** `activity-diagrams-v3/ATLANTECH_Activity_Diagrams.md`, diagram AD-9. **Related:** 2.9, SM-4. **Requirements:** FR-3.1, FR-3.4, FR-3.5, FR-3.7–FR-3.10; NFR-CONC-1.

**Swimlanes:** Port Authority Staff, Port Server.

**Story**

A berthing request is the port's record of a vessel that wants to come alongside. This diagram follows it from entry to preliminary approval. All requests are entered by Port Authority Staff; there is no external submission channel.

Entry. Staff enter the vessel's IMO number, name and main particulars (length, beam, maximum and arrival draft, block coefficient, DWT, GT), the ETA, the cargo and the target terminal. New requests are refused in read-only mode. After validation, the request is created as SUBMITTED, the vessel is found or created by IMO, and the status history starts.

Review. Staff then choose an action. Edit and cancel are only possible while the request is SUBMITTED or NEEDS_REVISION; after approval they get 409. Cancelling needs a reason. Returning a request sets NEEDS_REVISION with comments; its creator edits it and resubmits it as SUBMITTED, and it comes back for review. Rejecting records a reason and ends the request.

Approval. Approving sets PRELIMINARY_APPROVED, records history and audit, and tells the dashboard that the request is ready for Customs approval. Approval, entry, edit and cancel are writes that are blocked in read-only mode; rejecting and returning for revision stay allowed so that staff can still close or send back requests.

**Step-by-step flow** (each step lists where it goes next; END is a final node)

- **START** start → A1 "Enter berthing request: vessel IMO, name, LOA, beam, max draft, arrival draft, block coefficient, DWT, GT, ETA, cargo, target terminal"
- **A1** [Port Authority Staff] Enter berthing request: vessel IMO, name, LOA, beam, max draft, arrival draft, block coefficient, DWT, GT, ETA, cargo, target terminal → D2 "READ_ONLY?"
- **D2** [Port Server] Decision "READ_ONLY?": "Yes" → A2 "Reject with 423 LICENSE_READ_ONLY"; "No" → A19 "Validate required fields and data format"
- **A2** [Port Server] Reject with 423 LICENSE_READ_ONLY → END
- **A19** [Port Server] Validate required fields and data format → D8 "Data complete and valid?"
- **D8** [Port Server] Decision "Data complete and valid?": "No" → A20 "See validation errors and correct the entry"; "Yes" → A5 "Create request with status SUBMITTED"
- **A20** [Port Authority Staff] See validation errors and correct the entry → A1 "Enter berthing request: vessel IMO, name, LOA, beam, max draft, arrival draft, block coefficient, DWT, GT, ETA, cargo, target terminal"
- **A5** [Port Server] Create request with status SUBMITTED → A6 "Find-or-create vessel by IMO and associate cargo data"
- **A6** [Port Server] Find-or-create vessel by IMO and associate cargo data → A7 "Record status history entry"
- **A7** [Port Server] Record status history entry → A8 "Review the berthing request"
- **A8** [Port Authority Staff] Review the berthing request → D3 "Action?"
- **D3** [Port Authority Staff] Decision "Action?": "Edit" → A9 "Edit request details"; "Cancel" → AC "Request cancellation with a reason"; "Return for revision" → A11 "Set status NEEDS_REVISION with comments"; "Reject" → A12 "Set status REJECTED and record the reason"; "Approve" → D4 "READ_ONLY?"
- **A9** [Port Authority Staff] Edit request details → DE1 "READ_ONLY?"
- **AC** [Port Authority Staff] Request cancellation with a reason → DC1 "READ_ONLY?"
- **A11** [Port Server] Set status NEEDS_REVISION with comments → AR "Creator edits and resubmits"
- **A12** [Port Server] Set status REJECTED and record the reason → END
- **D4** [Port Server] Decision "READ_ONLY?": "Yes" → A2 "Reject with 423 LICENSE_READ_ONLY"; "No" → A15 "Set status PRELIMINARY_APPROVED"
- **DE1** [Port Server] Decision "READ_ONLY?": "Yes" → A2 "Reject with 423 LICENSE_READ_ONLY"; "No" → DE2 "Still editable?"
- **DC1** [Port Server] Decision "READ_ONLY?": "Yes" → A2 "Reject with 423 LICENSE_READ_ONLY"; "No" → DC2 "Still editable?"
- **AR** [Port Authority Staff] Creator edits and resubmits → DR1 "READ_ONLY?"
- **A15** [Port Server] Set status PRELIMINARY_APPROVED → A16 "Record status history and audit entry"
- **DE2** [Port Server] Decision "Still editable?": "No" → A409 "Return 409 - request already approved"; "Yes" → AS "Save the changes"
- **DC2** [Port Server] Decision "Still editable?": "No" → A409 "Return 409 - request already approved"; "Yes" → A10 "Set status CANCELLED"
- **DR1** [Port Server] Decision "READ_ONLY?": "Yes" → A2 "Reject with 423 LICENSE_READ_ONLY"; "No" → AR2 "Set status SUBMITTED"
- **A16** [Port Server] Record status history and audit entry → A17 "Notify dashboard via SSE - ready for Customs Approval, AD-10"
- **A409** [Port Server] Return 409 - request already approved → END
- **AS** [Port Server] Save the changes → A7 "Record status history entry"
- **A10** [Port Server] Set status CANCELLED → END
- **AR2** [Port Server] Set status SUBMITTED → A7 "Record status history entry"
- **A17** [Port Server] Notify dashboard via SSE - ready for Customs Approval, AD-10 → END

**Rules stated as notes**

- Status vocabulary: SUBMITTED, NEEDS_REVISION, PRELIMINARY_APPROVED, REJECTED, CANCELLED (later states in AD-10 to AD-12) (attached to A5)
- Editable = SUBMITTED or NEEDS_REVISION. Edit and cancel only before Preliminary Approval; afterwards 409 (attached to DE2)
- Reject and return for revision stay allowed in READ_ONLY; approve is blocked (attached to D4)

#### AD-10 — Customs approval, entry window and environmental data

**Code:** `activity-diagrams-v3/ATLANTECH_Activity_Diagrams.md`, diagram AD-10. **Related:** 2.10, 2.11, 2.12, SM-4. **Requirements:** FR-3.6, FR-3.8, FR-10.8; NFR-REL-4.

**Swimlanes:** Port Authority Staff, Port Server, AI Part 1 - Predictive and Environmental, Weather and Marine Data Providers.

**Story**

After preliminary approval, the request needs Customs approval and a safe entry window. AI Part 1 proposes the windows from environmental data; staff make the decision.

Scheduled data. Independently of any request, Part 1 runs its own scheduler. Every six hours it pulls weather, wave and surge data from the primary provider; if that fails it raises an alert and tries the secondary provider; if both fail it keeps the last stored data, marks it data_stale and logs the failure. In parallel, once a day, it computes the astronomical tide for several days ahead.

Customs and the Part 1 run. Staff record the Customs approval on a preliminarily approved request (blocked in read-only mode). The request becomes CUSTOMS_APPROVED and a Part 1 run is created as QUEUED and enqueued; it is retried three times before it is marked FAILED. Part 1 fetches fresh data for this request. If that fails it may use stored data only if it was measured within 48 hours and covers the request's horizon, shown with a stale-data warning. Otherwise the outcome is ENV_DATA_UNAVAILABLE and staff can enter manual environmental data, which is stored as a forecast run with pull_type MANUAL, provider_rank MANUAL and submitted_by, and goes through the same safety constraints.

Windows. Part 1 aggregates demand and congestion and checks the environmental and operational constraints. If no window is feasible the outcome is NO_FEASIBLE_WINDOW and it shows the blocked periods and limiting factors. Otherwise the outcome is WINDOWS_FOUND and it writes the feasible windows; Part 1 never allocates a berth, tug or pilot.

Decision. Staff cannot edit a window by hand. They confirm one window, reject all windows with a reason (allowed in read-only mode; the proposal becomes REJECTED with rejection_reason and the request stays CUSTOMS_APPROVED) or ask for a recompute. On confirmation the server re-checks the status and the constraints; a failed check returns 409 with the reason. A confirmed window sets ENTRY_WINDOW_CONFIRMED and is handed to Part 2.

Reopening. As long as no plan is confirmed, staff can reopen a confirmed window with a reason. The request goes back to CUSTOMS_APPROVED and a new Part 1 run starts.

**Step-by-step flow** (each step lists where it goes next; END is a final node)

- **START** start → D0 "Triggering event?"
- **D0** Decision "Triggering event?": "Schedule: 6-hourly weather or daily tide" → S1 "Scheduled job fires in Part 1"; "Staff records Customs Approval" → A1 "Open a PRELIMINARY_APPROVED berthing request"; "Staff reopens the window" → RO1 "Reopen a confirmed entry window with a reason - no confirmed plan yet"
- **S1** [AI Part 1 - Predictive and Environmental] Scheduled job fires in Part 1 → FK2 (fork/join bar)
- **A1** [Port Authority Staff] Open a PRELIMINARY_APPROVED berthing request → A2 "Record Customs Approval"
- **RO1** [Port Authority Staff] Reopen a confirmed entry window with a reason - no confirmed plan yet → DRO "READ_ONLY?"
- **FK2** Fork: in parallel → S2 "Pull weather, wave and surge data - every 6 h"; S6 "Compute astronomical tide for a multi-day horizon - daily"
- **A2** [Port Authority Staff] Record Customs Approval → D1 "READ_ONLY?"
- **DRO** [Port Server] Decision "READ_ONLY?": "Yes" → A3 "Reject with 423 LICENSE_READ_ONLY"; "No" → RO2 "Set status CUSTOMS_APPROVED"
- **S2** [AI Part 1 - Predictive and Environmental] Pull weather, wave and surge data - every 6 h → D6 "Primary provider reachable?"
- **S6** [AI Part 1 - Predictive and Environmental] Compute astronomical tide for a multi-day horizon - daily → S7 "Store tide data"
- **D1** [Port Server] Decision "READ_ONLY?": "Yes" → A3 "Reject with 423 LICENSE_READ_ONLY"; "No" → A4 "Set status CUSTOMS_APPROVED"
- **A3** [Port Server] Reject with 423 LICENSE_READ_ONLY → END
- **RO2** [Port Server] Set status CUSTOMS_APPROVED → A5 "Create a Part 1 run QUEUED and enqueue it - 3 retries, then FAILED"
- **D6** [AI Part 1 - Predictive and Environmental] Decision "Primary provider reachable?": "Yes" → S3 "Return weather, wave and surge data"; "No" → S8 "Raise an alert and try the secondary provider"
- **S7** [AI Part 1 - Predictive and Environmental] Store tide data → JN2 (fork/join bar)
- **A4** [Port Server] Set status CUSTOMS_APPROVED → A5 "Create a Part 1 run QUEUED and enqueue it - 3 retries, then FAILED"
- **A5** [Port Server] Create a Part 1 run QUEUED and enqueue it - 3 retries, then FAILED → A6 "Fetch environmental data for this request and compute tide in-house"
- **S3** [Weather and Marine Data Providers] Return weather, wave and surge data → S4 "Store forecast run with provider_rank PRIMARY or SECONDARY and its timestamp"
- **S8** [AI Part 1 - Predictive and Environmental] Raise an alert and try the secondary provider → D6b "Secondary provider reachable?"
- **JN2** Join: waits for S4, S5, S7 → END
- **A6** [AI Part 1 - Predictive and Environmental] Fetch environmental data for this request and compute tide in-house → D2 "Fresh retrieval successful?"
- **S4** [AI Part 1 - Predictive and Environmental] Store forecast run with provider_rank PRIMARY or SECONDARY and its timestamp → JN2 (fork/join bar)
- **D6b** [AI Part 1 - Predictive and Environmental] Decision "Secondary provider reachable?": "Yes" → S3 "Return weather, wave and surge data"; "No" → S5 "Keep last stored data, mark data_stale, log the source failure"
- **D2** [AI Part 1 - Predictive and Environmental] Decision "Fresh retrieval successful?": "Yes" → A7 "Return weather, wave and sea-level data"; "No" → D7 "Stored data recent enough?"
- **S5** [AI Part 1 - Predictive and Environmental] Keep last stored data, mark data_stale, log the source failure → JN2 (fork/join bar)
- **A7** [Weather and Marine Data Providers] Return weather, wave and sea-level data → A8 "Attach the retrieved data and its timestamp to this request"
- **D7** [AI Part 1 - Predictive and Environmental] Decision "Stored data recent enough?": "Yes" → A9 "Use stored data with a stale-data warning and its timestamp"; "No" → A24 "Outcome ENV_DATA_UNAVAILABLE - staff submit manual data"
- **A8** [AI Part 1 - Predictive and Environmental] Attach the retrieved data and its timestamp to this request → A14 "Aggregate demand and peak congestion from open requests"
- **A9** [AI Part 1 - Predictive and Environmental] Use stored data with a stale-data warning and its timestamp → A14 "Aggregate demand and peak congestion from open requests"
- **A24** [AI Part 1 - Predictive and Environmental] Outcome ENV_DATA_UNAVAILABLE - staff submit manual data → D8 "Staff action?"
- **A14** [AI Part 1 - Predictive and Environmental] Aggregate demand and peak congestion from open requests → D9 "All constraints satisfied?"
- **D8** [Port Authority Staff] Decision "Staff action?": "Enter manual data" → A28 "Enter manual environmental data"; "Not yet - request held" → END
- **D9** [AI Part 1 - Predictive and Environmental] Decision "All constraints satisfied?": "No" → A18 "Outcome NO_FEASIBLE_WINDOW: show blocked periods and limiting factors"; "Yes" → A15 "Outcome WINDOWS_FOUND: write feasible windows and constraints"
- **A28** [Port Authority Staff] Enter manual environmental data → DM "READ_ONLY?"
- **A18** [AI Part 1 - Predictive and Environmental] Outcome NO_FEASIBLE_WINDOW: show blocked periods and limiting factors → END
- **A15** [AI Part 1 - Predictive and Environmental] Outcome WINDOWS_FOUND: write feasible windows and constraints → A16 "Notify dashboard via SSE"
- **DM** [Port Server] Decision "READ_ONLY?": "Yes" → A3 "Reject with 423 LICENSE_READ_ONLY"; "No" → A29 "Store manual data as a forecast run with pull_type MANUAL, provider_rank MANUAL and submitted_by; audit entry"
- **A16** [Port Server] Notify dashboard via SSE → A17 "Review proposed windows, blocked periods, conditions and data timestamp"
- **A29** [Port Server] Store manual data as a forecast run with pull_type MANUAL, provider_rank MANUAL and submitted_by; audit entry → A14 "Aggregate demand and peak congestion from open requests"
- **A17** [Port Authority Staff] Review proposed windows, blocked periods, conditions and data timestamp → D5 "Decision?"
- **D5** [Port Authority Staff] Decision "Decision?": "Confirm" → D11 "READ_ONLY?"; "Reject all windows" → AR "Proposal REJECTED with rejection_reason; request stays CUSTOMS_APPROVED"; "Recompute" → DRC "READ_ONLY?"
- **D11** [Port Server] Decision "READ_ONLY?": "Yes" → A3 "Reject with 423 LICENSE_READ_ONLY"; "No" → A20 "Confirm window - server re-checks status and constraints"
- **AR** [Port Server] Proposal REJECTED with rejection_reason; request stays CUSTOMS_APPROVED → END
- **DRC** [Port Server] Decision "READ_ONLY?": "Yes" → A3 "Reject with 423 LICENSE_READ_ONLY"; "No" → A5 "Create a Part 1 run QUEUED and enqueue it - 3 retries, then FAILED"
- **A20** [Port Server] Confirm window - server re-checks status and constraints → DX "Re-check passed?"
- **DX** [Port Server] Decision "Re-check passed?": "No" → A409 "Return 409 with the reason"; "Yes" → A21 "Set status ENTRY_WINDOW_CONFIRMED"
- **A409** [Port Server] Return 409 with the reason → A17 "Review proposed windows, blocked periods, conditions and data timestamp"
- **A21** [Port Server] Set status ENTRY_WINDOW_CONFIRMED → A22 "Hand the confirmed window and constraints to Part 2 - AD-11"
- **A22** [Port Server] Hand the confirmed window and constraints to Part 2 - AD-11 → END

**Rules stated as notes**

- Each request uses its own data - never another request's result (attached to A6)
- Part 1 never allocates berth, tug or pilot (attached to A15)
- The scheduler runs in Part 1, not in the web application (attached to S1)
- Stored data counts only if measured within 48 h and covering the request horizon (attached to D7)
- Manual data passes the same safety constraints - no bypass (attached to A29)

#### AD-11 — Recommendation to confirmed operational plan

**Code:** `activity-diagrams-v3/ATLANTECH_Activity_Diagrams.md`, diagram AD-11. **Related:** 2.13, 2.14, SM-4, SM-5. **Requirements:** FR-4.1–FR-4.7, FR-4.9; NFR-PERF-1, NFR-ENG-1, NFR-UX-1, NFR-REL-5.

**Swimlanes:** Port Server, AI Part 2 - AI Engine, Port Authority Staff.

**Story**

With a confirmed entry window, AI Part 2 recommends who and what will serve the vessel: berth, tugs and pilot. Staff review the recommendation and confirm the operational plan.

Generation. In read-only mode no new plan is generated. Otherwise a Part 2 job loads the BAPLIE data, the confirmed window, the Part 1 constraints, the actual resource state and the competing requests. It predicts service time and delay risk and solves the allocation with the CP-SAT solver. The solver has three outcomes. Solved: the candidates go on. Technical failure (an error or a timeout): a FIFO plan is built by arrival order and gets source FIFO; the failure reason is stored in solver_run.result_detail. Infeasible: the outcome is NO_FEASIBLE_PLAN.

Safety filter. Every candidate, including the FIFO one, passes the hard safety and feasibility filter. If nothing is left, the outcome is NO_FEASIBLE_PLAN, with the binding constraints in solver_run.result_detail: the request stays ENTRY_WINDOW_CONFIRMED and staff can regenerate later or wait. Otherwise the options are ranked by time urgency, then by financial impact when time is close, and written as a PENDING_REVIEW recommendation version with its source (AI or FIFO) and rationale. The request becomes RECOMMENDATION_GENERATED.

Review and override. Staff review the options. They can select the recommended option or override a component; overrides are blocked in read-only mode, need a reason and are checked against the hard constraints. An accepted override creates a MODIFIED_BY_STAFF version, and override data later feeds AI Part 3.

Confirmation. Confirming the plan is blocked in read-only mode. Otherwise one transaction re-checks availability, books the berth, tugs and pilot, creates the operational plan as CONFIRMED, sets the request PLAN_CONFIRMED and sets the version CONFIRMED. If the booking fails, everything is rolled back and the conflict is shown. Once committed, the pilotage and tug components go to the officers for assignment, and for a container vessel a yard recommendation is requested.

**Step-by-step flow** (each step lists where it goes next; END is a final node)

- **START** start → A1 "Receive request in ENTRY_WINDOW_CONFIRMED"
- **A1** [Port Server] Receive request in ENTRY_WINDOW_CONFIRMED → D0 "READ_ONLY?"
- **D0** [Port Server] Decision "READ_ONLY?": "Yes" → A34 "Reject with 423 LICENSE_READ_ONLY - no new plan"; "No" → A2 "Enqueue job on the Part 2 queue"
- **A34** [Port Server] Reject with 423 LICENSE_READ_ONLY - no new plan → END
- **A2** [Port Server] Enqueue job on the Part 2 queue → A3 "Load BAPLIE data, confirmed window, Part 1 constraints, resource state and competing requests"
- **A3** [AI Part 2 - AI Engine] Load BAPLIE data, confirmed window, Part 1 constraints, resource state and competing requests → A5 "Predict service time and delay risk"
- **A5** [AI Part 2 - AI Engine] Predict service time and delay risk → A6 "Solve berth, tug and pilot allocation with CP-SAT"
- **A6** [AI Part 2 - AI Engine] Solve berth, tug and pilot allocation with CP-SAT → D1 "Solver result?"
- **D1** [AI Part 2 - AI Engine] Decision "Solver result?": "Solved" → A4 "Apply the hard safety and feasibility filter - discard violating candidates"; "Technical failure: error or timeout" → A30 "Build FIFO fallback plan by arrival order"; "Infeasible" → A7 "Outcome NO_FEASIBLE_PLAN, binding constraints in solver_run.result_detail - request stays ENTRY_WINDOW_CONFIRMED"
- **A4** [AI Part 2 - AI Engine] Apply the hard safety and feasibility filter - discard violating candidates → D3 "Feasible candidate left?"
- **A30** [AI Part 2 - AI Engine] Build FIFO fallback plan by arrival order → A31 "Set source FIFO; store the failure reason in solver_run.result_detail"
- **A7** [AI Part 2 - AI Engine] Outcome NO_FEASIBLE_PLAN, binding constraints in solver_run.result_detail - request stays ENTRY_WINDOW_CONFIRMED → A24 "Show the no-feasible-plan reason to staff"
- **D3** [AI Part 2 - AI Engine] Decision "Feasible candidate left?": "No" → A7 "Outcome NO_FEASIBLE_PLAN, binding constraints in solver_run.result_detail - request stays ENTRY_WINDOW_CONFIRMED"; "Yes" → A8 "Rank by time urgency, then financial impact when time priority is close or tied"
- **A31** [AI Part 2 - AI Engine] Set source FIFO; store the failure reason in solver_run.result_detail → A4 "Apply the hard safety and feasibility filter - discard violating candidates"
- **A24** [Port Server] Show the no-feasible-plan reason to staff → D6 "Next step?"
- **A8** [AI Part 2 - AI Engine] Rank by time urgency, then financial impact when time priority is close or tied → A9 "Write recommendation version PENDING_REVIEW with source AI or FIFO and template rationale"
- **D6** [Port Authority Staff] Decision "Next step?": "Regenerate - AD-12" → D0 "READ_ONLY?"; "Wait" → END
- **A9** [AI Part 2 - AI Engine] Write recommendation version PENDING_REVIEW with source AI or FIFO and template rationale → A11 "Set status RECOMMENDATION_GENERATED"
- **A11** [Port Server] Set status RECOMMENDATION_GENERATED → A12 "Notify dashboard via SSE"
- **A12** [Port Server] Notify dashboard via SSE → A13 "Review ranked options and rationale against the unified port state"
- **A13** [Port Authority Staff] Review ranked options and rationale against the unified port state → D2 "Override a component?"
- **D2** [Port Authority Staff] Decision "Override a component?": "Yes" → DO "READ_ONLY?"; "No" → A17 "Select the recommended option"
- **DO** [Port Server] Decision "READ_ONLY?": "Yes" → A19 "Reject with 423 LICENSE_READ_ONLY"; "No" → A14 "Change the berth, tug or pilot component"
- **A17** [Port Authority Staff] Select the recommended option → A18 "Confirm the operational plan"
- **A19** [Port Server] Reject with 423 LICENSE_READ_ONLY → END
- **A14** [Port Authority Staff] Change the berth, tug or pilot component → A15 "Enter the override reason"
- **A18** [Port Authority Staff] Confirm the operational plan → D4 "READ_ONLY?"
- **A15** [Port Authority Staff] Enter the override reason → A32 "Check the override against hard safety and feasibility constraints"
- **D4** [Port Server] Decision "READ_ONLY?": "Yes" → A19 "Reject with 423 LICENSE_READ_ONLY"; "No" → A20 "In one transaction: re-check availability, book berth, tug and pilot, create operational plan CONFIRMED, set request PLAN_CONFIRMED, set version CONFIRMED"
- **A32** [AI Part 2 - AI Engine] Check the override against hard safety and feasibility constraints → D5 "Override passes?"
- **A20** [Port Server] In one transaction: re-check availability, book berth, tug and pilot, create operational plan CONFIRMED, set request PLAN_CONFIRMED, set version CONFIRMED → D7 "Committed?"
- **D5** [AI Part 2 - AI Engine] Decision "Override passes?": "No" → A33 "Reject the override and show the violated constraint"; "Yes" → A16 "Create a MODIFIED_BY_STAFF version and record the override reason"
- **D7** [Port Server] Decision "Committed?": "No" → A35 "Roll back - plan stays unconfirmed, show the resource conflict"; "Yes" → A23 "Send pilotage and tug components for assignment - AD-13; request a yard recommendation for a container vessel - AD-14"
- **A33** [AI Part 2 - AI Engine] Reject the override and show the violated constraint → A14 "Change the berth, tug or pilot component"
- **A16** [Port Server] Create a MODIFIED_BY_STAFF version and record the override reason → A18 "Confirm the operational plan"
- **A35** [Port Server] Roll back - plan stays unconfirmed, show the resource conflict → A13 "Review ranked options and rationale against the unified port state"
- **A23** [Port Server] Send pilotage and tug components for assignment - AD-13; request a yard recommendation for a container vessel - AD-14 → END

**Rules stated as notes**

- FIFO is only a fallback for a technical solver failure and never bypasses hard constraints (attached to A30)
- Override data feeds AI Part 3 - AD-16 (attached to A15)
- Generation, review and confirmation are separate steps (attached to A12)
- The plan counts as confirmed only after the booking commits (attached to D7)

#### AD-12 — Regenerate recommendation, delay re-plan and cancel plan

**Code:** `activity-diagrams-v3/ATLANTECH_Activity_Diagrams.md`, diagram AD-12. **Related:** 2.13, 2.14, SM-4, SM-5. **Requirements:** FR-3.11, FR-4.8; NFR-REL-5, NFR-CONC-1.

**Swimlanes:** Port Server, AI Part 2 - AI Engine, Port Authority Staff.

**Story**

Plans change. This diagram covers the four ways a recommendation or a confirmed plan is revisited: a resource changes, staff ask to regenerate, a significant deviation needs a re-plan, or staff cancel the plan.

Resource change. When a berth, tug or pilot changes state, the server looks only for pending recommendations, not yet confirmed, that use it. In read-only mode nothing is regenerated and the previous version stays current. Otherwise Part 2 re-runs the same pipeline as in the recommendation diagram. On success the new version is written as PENDING_REVIEW and the previous one becomes REPLACED; staff review it as usual. On failure the previous version stays current and staff may retry.

Staff regenerate. Staff can ask for a new recommendation before a plan is confirmed. On a confirmed plan the answer is 409: use a delay re-plan or cancel instead.

Delay re-plan. When execution tracking reports a significant deviation, Part 2 builds a proposal version with purpose DELAY_REPLAN (none in read-only mode; staff are told). Staff review it. If they confirm, one transaction reserves the new resources, releases unused ones, keeps the components that already STARTED, marks the old version REPLACED, makes the proposal the INITIAL version and sends changed components back to assignment. If the commit fails, the old version stays confirmed.

Cancel. Staff request the cancellation with a reason and say whether the vessel's call continues. It is blocked in read-only mode. If execution has already started, a normal cancellation is refused with 409: only the Port Admin safety exception can stop it. Otherwise one transaction cancels the plan, releases the berth, tug and pilot and sets the request PLAN_CANCELLED; officers and field users are notified. If the call continues, the request goes back to ENTRY_WINDOW_CONFIRMED for a new plan; otherwise it stays PLAN_CANCELLED. The released resources count as a resource change, and any offline field events for the cancelled plan are later rejected with a reason.

**Step-by-step flow** (each step lists where it goes next; END is a final node)

- **START** start → D1 "Triggering event?"
- **D1** Decision "Triggering event?": "Resource state changed" → A1 "Detect resource-state change: berth, tug or pilot"; "Staff asks to regenerate" → G1 "Ask to regenerate the recommendation"; "Significant deviation - AD-16" → DR1 "READ_ONLY?"; "Staff cancels the plan" → A10 "Request cancellation with a reason and answer: does the call continue?"
- **A1** [Port Server] Detect resource-state change: berth, tug or pilot → A2 "Find pending recommendations that use the affected resource"
- **G1** [Port Authority Staff] Ask to regenerate the recommendation → DG "Plan already confirmed?"
- **DR1** [Port Server] Decision "READ_ONLY?": "Yes" → R0 "No proposal; staff notified"; "No" → R1 "Build a delay re-plan proposal version with purpose DELAY_REPLAN"
- **A10** [Port Authority Staff] Request cancellation with a reason and answer: does the call continue? → DC2 "READ_ONLY?"
- **A2** [Port Server] Find pending recommendations that use the affected resource → D2 "Any found?"
- **DG** [Port Server] Decision "Plan already confirmed?": "Yes" → G2 "Return 409 - use delay re-plan or cancel"; "No" → D8 "READ_ONLY?"
- **R0** [Port Server] No proposal; staff notified → END
- **R1** [AI Part 2 - AI Engine] Build a delay re-plan proposal version with purpose DELAY_REPLAN → R2 "Review the delay re-plan proposal"
- **DC2** [Port Server] Decision "READ_ONLY?": "Yes" → A423 "Reject with 423 LICENSE_READ_ONLY"; "No" → A17 "Check the current plan and operation state"
- **D2** [Port Server] Decision "Any found?": "No" → END; "Yes" → D8 "READ_ONLY?"
- **G2** [Port Server] Return 409 - use delay re-plan or cancel → END
- **D8** [Port Server] Decision "READ_ONLY?": "Yes" → A21 "Do not regenerate in READ_ONLY - previous version stays current"; "No" → A4 "Enqueue regeneration on the Part 2 queue"
- **R2** [Port Authority Staff] Review the delay re-plan proposal → DR2 "Confirm the proposal?"
- **A423** [Port Server] Reject with 423 LICENSE_READ_ONLY → END
- **A17** [Port Server] Check the current plan and operation state → D4 "Execution already started?"
- **A21** [Port Server] Do not regenerate in READ_ONLY - previous version stays current → END
- **A4** [Port Server] Enqueue regeneration on the Part 2 queue → A5 "Re-run generation with updated inputs - same pipeline as AD-11"
- **DR2** [Port Authority Staff] Decision "Confirm the proposal?": "No" → R5 "Proposal discarded - current plan stays"; "Yes" → R3 "In one transaction: reserve new resources, release unused ones, keep STARTED components, old version REPLACED, proposal becomes the INITIAL version, changed components back to assignment - AD-13"
- **D4** [Port Server] Decision "Execution already started?": "Yes" → A18 "Return 409 - Port Admin safety exception only, AD-13"; "No" → A11 "In one transaction: plan CANCELLED, release berth, tug and pilot, request PLAN_CANCELLED"
- **A5** [AI Part 2 - AI Engine] Re-run generation with updated inputs - same pipeline as AD-11 → D3 "Regeneration successful?"
- **R5** [Port Authority Staff] Proposal discarded - current plan stays → END
- **R3** [Port Server] In one transaction: reserve new resources, release unused ones, keep STARTED components, old version REPLACED, proposal becomes the INITIAL version, changed components back to assignment - AD-13 → DR3 "Committed?"
- **A18** [Port Server] Return 409 - Port Admin safety exception only, AD-13 → END
- **A11** [Port Server] In one transaction: plan CANCELLED, release berth, tug and pilot, request PLAN_CANCELLED → D5 "Committed?"
- **D3** [AI Part 2 - AI Engine] Decision "Regeneration successful?": "No" → A6 "Show regeneration failure - previous version stays current"; "Yes" → A7 "Write the new version (PENDING_REVIEW); previous version REPLACED"
- **DR3** [Port Server] Decision "Committed?": "No" → R4 "Roll back - old version stays confirmed"; "Yes" → A16 "Notify affected officers and field users"
- **D5** [Port Server] Decision "Committed?": "No" → A19 "Roll back, keep the previous state and show the error"; "Yes" → A16 "Notify affected officers and field users"
- **A6** [Port Server] Show regeneration failure - previous version stays current → D6 "Retry regeneration?"
- **A7** [AI Part 2 - AI Engine] Write the new version (PENDING_REVIEW); previous version REPLACED → A8 "Notify staff via SSE"
- **R4** [Port Server] Roll back - old version stays confirmed → END
- **A16** [Port Server] Notify affected officers and field users → DC "Call continues?"
- **A19** [Port Server] Roll back, keep the previous state and show the error → D7 "Retry cancellation?"
- **D6** [Port Authority Staff] Decision "Retry regeneration?": "Yes" → D8 "READ_ONLY?"; "No" → END
- **A8** [Port Server] Notify staff via SSE → A9 "Review the new recommendation - continues in AD-11"
- **DC** [Port Server] Decision "Call continues?": "Yes" → C1 "Re-plan: request back to ENTRY_WINDOW_CONFIRMED - AD-11"; "No" → C2 "Request stays PLAN_CANCELLED"
- **D7** [Port Authority Staff] Decision "Retry cancellation?": "Yes" → A11 "In one transaction: plan CANCELLED, release berth, tug and pilot, request PLAN_CANCELLED"; "No" → END
- **A9** [Port Authority Staff] Review the new recommendation - continues in AD-11 → END
- **C1** [Port Server] Re-plan: request back to ENTRY_WINDOW_CONFIRMED - AD-11 → END
- **C2** [Port Server] Request stays PLAN_CANCELLED → END

**Rules stated as notes**

- Triggers: resource-state change (pending recommendations only), staff regenerate before confirmation, significant deviation (delay re-plan) (attached to D1)
- Released resources count as a resource-state change (attached to A16)
- Field events queued offline for a cancelled plan are later rejected with a reason - AD-15 (attached to A11)

#### AD-13 — Dispatch, notification and acknowledgement

**Code:** `activity-diagrams-v3/ATLANTECH_Activity_Diagrams.md`, diagram AD-13. **Related:** 2.15, SM-5. **Requirements:** FR-5.1, FR-5.2, FR-7.1–FR-7.3; NFR-UX-2, NFR-PERF-4.

**Swimlanes:** Port Server, Port Authority Staff, Pilotage Department Officer, Tug Department Officer, Marine Pilot or Tug Master, Scheduler, Port Admin.

**Story**

A confirmed plan becomes work for real people. This diagram shows how the pilotage and tug parts are assigned, how the field crew are notified and how the system makes sure they have seen it.

Assignment. The server splits the plan into a pilotage component and a tug component and proposes a pilot, a tug master and a tug from current availability. The two paths run in parallel and independently. Each department officer reviews the proposal and confirms it or picks someone else. The server checks the operation state, the read-only policy, availability and eligibility. An unavailable or ineligible choice is refused and the officer chooses again; read-only mode or an invalid operation state stops the assignment and is audited as REJECTED_ATTEMPT, and choosing someone else cannot get around it.

Notification. Each recorded assignment schedules a reminder at the configured lead time and sends the task at T+0: live to the web, and as a WebSocket event to the mobile app, which then fetches the task. There is no push service, so if delivery fails the task appears the next time the app opens. Delivery is not acknowledgement: the pilot or tug master acknowledges in the app, the acknowledgement goes through the Outbox and, when synced, the notification is marked ACKNOWLEDGED and pending retries are cancelled.

Follow-up. Acknowledgement checks run at T+10, T+20 and T+30 after the first send. At T+10 and T+20 an unacknowledged task is re-sent through the same channels; at T+30 an ACK_ESCALATION notification goes to the assigning officer and the department manager. Separately, the pre-execution reminder is sent only if the task is still active.

Cancellation. A cancellation before execution starts cancels the assignments and reminders and informs everyone. Once execution has started, normal cancellation is blocked. Only the Port Admin, for a serious safety exception and with a mandatory reason, can cancel the remaining components: the plan becomes CANCELLED, the request PLAN_CANCELLED, unused resources are released and the action is audited as SAFETY_EXCEPTION. This exception is allowed even in read-only mode.

**Step-by-step flow** (each step lists where it goes next; END is a final node)

- **START** start → D0 "Triggering event?"
- **D0** Decision "Triggering event?": "Plan confirmed" → A1 "Split the PLAN_CONFIRMED plan into pilotage and tug components"; "Acknowledgement check time" → Q1 "Acknowledgement check time reached"; "Reminder time" → S1 "Reminder time reached"; "Cancellation requested" → K1 "Request cancellation of the operation"
- **A1** [Port Server] Split the PLAN_CONFIRMED plan into pilotage and tug components → A0 "Propose pilot and tug from availability"
- **Q1** [Scheduler] Acknowledgement check time reached → D8 "Acknowledged?"
- **S1** [Scheduler] Reminder time reached → S3 "Check the actual task state"
- **K1** [Port Authority Staff] Request cancellation of the operation → C1 "Check the operation state"
- **A0** [Port Server] Propose pilot and tug from availability → FK1 (fork/join bar)
- **D8** [Scheduler] Decision "Acknowledged?": "Yes" → END; "No" → D9 "Which check?"
- **S3** [Scheduler] Check the actual task state → D7 "Task still active?"
- **C1** [Port Server] Check the operation state → D5 "Execution already started?"
- **FK1** Fork: in parallel → P1 "Review the pilotage component"; T1 "Review the tug component"
- **D9** [Scheduler] Decision "Which check?": "T+10 or T+20" → Q2 "Send a retry through the same channels and record it (T+10, T+20)"; "T+30" → Q3 "At T+30 send ACK_ESCALATION to the assigning officer and the department manager"
- **D7** [Scheduler] Decision "Task still active?": "Yes" → S2 "Send the pre-execution reminder"; "No - cancelled or done" → END
- **D5** [Port Server] Decision "Execution already started?": "No" → C2 "Cancel pilot and tug assignments and pending reminders"; "Yes" → C4 "Block normal cancellation"
- **P1** [Pilotage Department Officer] Review the pilotage component → P2 "Review the proposed Marine Pilot; confirm or replace"
- **T1** [Tug Department Officer] Review the tug component → T2 "Review the proposed Tug Master and tug; confirm or replace"
- **Q2** [Scheduler] Send a retry through the same channels and record it (T+10, T+20) → END
- **Q3** [Scheduler] At T+30 send ACK_ESCALATION to the assigning officer and the department manager → END
- **S2** [Scheduler] Send the pre-execution reminder → M4 "Receive the pre-execution reminder"
- **C2** [Port Server] Cancel pilot and tug assignments and pending reminders → C3 "Notify assigned officers and field users of the cancellation"
- **C4** [Port Server] Block normal cancellation → D6 "Serious safety exception?"
- **P2** [Pilotage Department Officer] Review the proposed Marine Pilot; confirm or replace → V1 "Check operation state, READ_ONLY policy, pilot availability and eligibility"
- **T2** [Tug Department Officer] Review the proposed Tug Master and tug; confirm or replace → V2 "Check operation state, READ_ONLY policy, tug availability and eligibility"
- **M4** [Marine Pilot or Tug Master] Receive the pre-execution reminder → END
- **C3** [Port Server] Notify assigned officers and field users of the cancellation → END
- **D6** [Port Admin] Decision "Serious safety exception?": "No - request refused" → END; "Yes" → K2 "Enter the exception reason"
- **V1** [Port Server] Check operation state, READ_ONLY policy, pilot availability and eligibility → DV1 "Check result?"
- **V2** [Port Server] Check operation state, READ_ONLY policy, tug availability and eligibility → DV2 "Check result?"
- **K2** [Port Admin] Enter the exception reason → C5 "Cancel the remaining components with reason: plan CANCELLED, request PLAN_CANCELLED, release unused resources, audit SAFETY_EXCEPTION - allowed in READ_ONLY"
- **DV1** [Port Server] Decision "Check result?": "Unavailable or not eligible" → P4 "See the rejection reason and choose again"; "READ_ONLY or invalid operation state" → A26 "Stop this assignment: show the reason, 423 LICENSE_READ_ONLY or invalid operation state, and audit REJECTED_ATTEMPT"; "Passed" → P3 "Assign the pilotage component to the Marine Pilot"
- **DV2** [Port Server] Decision "Check result?": "Unavailable or not eligible" → T4 "See the rejection reason and choose again"; "READ_ONLY or invalid operation state" → A26 "Stop this assignment: show the reason, 423 LICENSE_READ_ONLY or invalid operation state, and audit REJECTED_ATTEMPT"; "Passed" → T3 "Assign the tug component to the Tug Master"
- **C5** [Port Admin] Cancel the remaining components with reason: plan CANCELLED, request PLAN_CANCELLED, release unused resources, audit SAFETY_EXCEPTION - allowed in READ_ONLY → END
- **P4** [Pilotage Department Officer] See the rejection reason and choose again → P2 "Review the proposed Marine Pilot; confirm or replace"
- **A26** [Port Server] Stop this assignment: show the reason, 423 LICENSE_READ_ONLY or invalid operation state, and audit REJECTED_ATTEMPT → END
- **P3** [Pilotage Department Officer] Assign the pilotage component to the Marine Pilot → A2 "Record the assignment and audit entry"
- **T4** [Tug Department Officer] See the rejection reason and choose again → T2 "Review the proposed Tug Master and tug; confirm or replace"
- **T3** [Tug Department Officer] Assign the tug component to the Tug Master → A2 "Record the assignment and audit entry"
- **A2** [Port Server] Record the assignment and audit entry → A24 "Schedule the reminder at the configured lead time"
- **A24** [Port Server] Schedule the reminder at the configured lead time → A3 "Send task notification at T+0: SSE to web, WS event to mobile; record the send"
- **A3** [Port Server] Send task notification at T+0: SSE to web, WS event to mobile; record the send → A25 "Start acknowledgement checks at T+10, T+20 and T+30 from the first send"
- **A25** [Port Server] Start acknowledgement checks at T+10, T+20 and T+30 from the first send → D1 "Delivered?"
- **D1** [Port Server] Decision "Delivered?": "Yes" → M1 "Receive WS event and fetch the task via REST"; "No" → A4 "Record delivery state failed"
- **M1** [Marine Pilot or Tug Master] Receive WS event and fetch the task via REST → M3 "Acknowledge notification - written to the Outbox, synced by AD-15"
- **A4** [Port Server] Record delivery state failed → M2 "See the task on next app open via REST catch-up"
- **M3** [Marine Pilot or Tug Master] Acknowledge notification - written to the Outbox, synced by AD-15 → A5 "Mark the notification ACKNOWLEDGED; cancel pending retries"
- **M2** [Marine Pilot or Tug Master] See the task on next app open via REST catch-up → M3 "Acknowledge notification - written to the Outbox, synced by AD-15"
- **A5** [Port Server] Mark the notification ACKNOWLEDGED; cancel pending retries → END

**Rules stated as notes**

- No push service: a closed app receives nothing until it is reopened (attached to A4)
- Reminder lead time comes from configurable operational settings (attached to A24)
- Pilot and tug paths are independent: each assignment continues on its own (attached to A2)
- The safety exception is a Port Admin action with a mandatory reason and audit (attached to C5)
- Acknowledgement retries are separate from the pre-execution reminder (attached to Q1)
- Delivery is never acknowledgement - only the recipient acknowledges (attached to D1)
- Choosing another pilot or tug cannot bypass READ_ONLY (attached to A26)

#### AD-14 — Yard placement recommendation

**Code:** `activity-diagrams-v3/ATLANTECH_Activity_Diagrams.md`, diagram AD-14. **Related:** 2.16, SM-5. **Requirements:** FR-8.5–FR-8.8; NFR-INT-4, NFR-SEC-7.

**Swimlanes:** Port Server, AI Part 2 - AI Engine, CT Operation Planner.

**Story**

For container vessels, ATLANTECH also recommends where the containers should go in the yard. It coordinates with the terminal's own TOS but does not integrate with it.

Request. When a plan is confirmed for a container vessel that has an active BAPLIE, a yard recommendation is requested automatically (YARD_REC_REQUESTED). In read-only mode nothing is generated and the planner is told why.

Generation. AI Part 2 loads the yard capacity and the terminal equipment set up by the CT Admin, the destinations and the stowage, and proposes a placement for containers and container groups. It validates the yard constraints; no LIFO rule is assumed. If generation fails, or the job errors, the result is GENERATION_FAILED with its failure_reason, the planner is notified (YARD_RECOMMENDATION_FAILED) and can request again or reject. A valid result is written as YARD_REC_GENERATED and the planner is notified (YARD_RECOMMENDATION_READY).

Decision. The planner accepts the placement, adjusts it (every adjustment is re-validated), or rejects it with a reason. Accepting or adjusting is blocked in read-only mode; rejecting is allowed and the planner may request again later. An accepted placement is recorded as YARD_REC_ACCEPTED without reserving any slot.

Hand-off. The server then presents a TOS-ready payload. The planner enters the plan into the TOS outside ATLANTECH, and the system records EXPORTED_TO_TOS. Nothing comes back from the TOS.

**Step-by-step flow** (each step lists where it goes next; END is a final node)

- **START** start → A1 "Plan confirmed for a container vessel with an ACTIVE BAPLIE: YARD_REC_REQUESTED, automatic"
- **A1** [Port Server] Plan confirmed for a container vessel with an ACTIVE BAPLIE: YARD_REC_REQUESTED, automatic → D6 "READ_ONLY?"
- **D6** [Port Server] Decision "READ_ONLY?": "Yes" → A21 "Do not generate: record reason 423 LICENSE_READ_ONLY and notify the planner"; "No" → A2 "Enqueue the yard placement job"
- **A21** [Port Server] Do not generate: record reason 423 LICENSE_READ_ONLY and notify the planner → END
- **A2** [Port Server] Enqueue the yard placement job → A3 "Load yard capacity and CT equipment, destinations and stowage"
- **A3** [AI Part 2 - AI Engine] Load yard capacity and CT equipment, destinations and stowage → A4 "Generate placement for containers and container groups"
- **A4** [AI Part 2 - AI Engine] Generate placement for containers and container groups → V1 "Validate yard constraints"
- **V1** [AI Part 2 - AI Engine] Validate yard constraints → D0 "Generated within constraints?"
- **D0** [AI Part 2 - AI Engine] Decision "Generated within constraints?": "No, or job error" → AG "GENERATION_FAILED with failure_reason; notify YARD_RECOMMENDATION_FAILED"; "Yes" → A5 "Write yard placement output - YARD_REC_GENERATED, with template rationale"
- **AG** [Port Server] GENERATION_FAILED with failure_reason; notify YARD_RECOMMENDATION_FAILED → D3 "Request again or reject?"
- **A5** [AI Part 2 - AI Engine] Write yard placement output - YARD_REC_GENERATED, with template rationale → A6 "Notify the planner (YARD_RECOMMENDATION_READY)"
- **D3** [CT Operation Planner] Decision "Request again or reject?": "Request again" → D6 "READ_ONLY?"; "Reject" → A10 "Reject with a reason"
- **A6** [Port Server] Notify the planner (YARD_RECOMMENDATION_READY) → A7 "Review the yard placement recommendation"
- **A10** [CT Operation Planner] Reject with a reason → A11 "Record YARD_REC_REJECTED with the reason - allowed in READ_ONLY; the planner may request again"
- **A7** [CT Operation Planner] Review the yard placement recommendation → D1 "Planner decision?"
- **A11** [Port Server] Record YARD_REC_REJECTED with the reason - allowed in READ_ONLY; the planner may request again → END
- **D1** [CT Operation Planner] Decision "Planner decision?": "Accept" → DA "READ_ONLY?"; "Adjust" → A8 "Adjust the placement"; "Reject" → A10 "Reject with a reason"
- **DA** [Port Server] Decision "READ_ONLY?": "Yes" → A22 "Reject with 423 LICENSE_READ_ONLY"; "No" → AC "Record YARD_REC_ACCEPTED - no slot reservation"
- **A8** [CT Operation Planner] Adjust the placement → A17 "Re-validate yard constraints for the adjusted placement"
- **A22** [Port Server] Reject with 423 LICENSE_READ_ONLY → END
- **AC** [Port Server] Record YARD_REC_ACCEPTED - no slot reservation → AP "Present the TOS-ready payload"
- **A17** [AI Part 2 - AI Engine] Re-validate yard constraints for the adjusted placement → D4 "Adjusted placement valid?"
- **AP** [Port Server] Present the TOS-ready payload → A15 "Enter the plan into the TOS outside ATLANTECH"
- **D4** [AI Part 2 - AI Engine] Decision "Adjusted placement valid?": "No" → A18 "Show the violated constraint"; "Yes" → DA "READ_ONLY?"
- **A15** [CT Operation Planner] Enter the plan into the TOS outside ATLANTECH → AE "Record EXPORTED_TO_TOS"
- **A18** [AI Part 2 - AI Engine] Show the violated constraint → A8 "Adjust the placement"
- **AE** [Port Server] Record EXPORTED_TO_TOS → END

**Rules stated as notes**

- Coordination only - nothing comes back from the TOS (attached to A15)
- No LIFO rule is assumed (attached to V1)
- Every adjustment is re-validated against yard constraints (attached to A17)

#### AD-18 — Web login, roles and port administration

**Code:** `activity-diagrams-v3/ATLANTECH_Activity_Diagrams.md`, diagram AD-18. **Related:** 2.1–2.6. **Requirements:** FR-1.1–FR-1.9, FR-8.1, FR-9.1, FR-10.1, FR-10.2, FR-11.1–FR-11.5; NFR-SEC-2, NFR-SEC-3, NFR-CAP-1.

**Swimlanes:** Office User - Port Admin, Department Manager, CT Admin, Marine Safety Officer, Port Server.

**Story**

This diagram covers everything office users do on the web dashboard of a port: signing in, and the checks every request goes through before data is shown or changed.

Sign-in. Wrong credentials return 401; an inactive account gets 403 ACCOUNT_DISABLED. A valid sign-in starts a web session. When must_change_password is set, the user must change the password first.

Actions. Users view data, and depending on their role manage users (Port Admin), edit master data, manage devices and tokens (Port Admin), or log out. The Marine Safety Officer maintains the port-wide environmental limits, chart datum and under-keel clearance.

Checks for every request. The API authorizes each request by role and terminal ownership; hiding buttons is never the protection. Reads return data within the user's scope. A write must then pass, in order: the setup allowlist while the port is still in SETUP mode; the read-only allowlist, under which master-data edits and user creation are blocked but deactivating a user and revoking tokens stay allowed; an unchanged updated_at version token (otherwise 409); the rule that nobody can deactivate themselves or the last active Port Admin, or remove that role from them; and the license limits for users (including tug master and pilot accounts), terminals and berths, where going over returns 422 PLAN_LIMIT_EXCEEDED and nothing is saved.

Saving. Nothing is deleted: ending a role sets its active_to date, and deactivating a user sets revoked_at on their tokens and ends their sessions. Every change is recorded in the audit log with its before and after state (master-data history is this log filtered by entity); every rejected attempt is audited as REJECTED_ATTEMPT. A change to a resource regenerates only pending recommendations.

**Step-by-step flow** (each step lists where it goes next; END is a final node)

- **START** start → U1 "Open the web dashboard and enter credentials"
- **U1** [Office User - Port Admin, Department Manager, CT Admin, Marine Safety Officer] Open the web dashboard and enter credentials → S1 "Verify credentials"
- **S1** [Port Server] Verify credentials → D2 "Result?"
- **D2** [Port Server] Decision "Result?": "Wrong credentials" → S2 "Return 401"; "Account inactive" → S2b "Return 403 ACCOUNT_DISABLED"; "Valid" → S3 "Start web session"
- **S2** [Port Server] Return 401 → U1 "Open the web dashboard and enter credentials"
- **S2b** [Port Server] Return 403 ACCOUNT_DISABLED → END
- **S3** [Port Server] Start web session → DF "must_change_password set?"
- **DF** [Port Server] Decision "must_change_password set?": "Yes" → UF "Change the password - forced on first login"; "No" → U2 "Choose an action"
- **UF** [Office User - Port Admin, Department Manager, CT Admin, Marine Safety Officer] Change the password - forced on first login → U2 "Choose an action"
- **U2** [Office User - Port Admin, Department Manager, CT Admin, Marine Safety Officer] Choose an action → D1 "Action?"
- **D1** [Office User - Port Admin, Department Manager, CT Admin, Marine Safety Officer] Decision "Action?": "View" → S5 "Authorize the request: role and terminal ownership"; "Manage users" → U4 "Port Admin: create, edit or deactivate user; assign or end roles and terminal scope"; "Edit master data" → U5 "Edit master data: port, channel, terminals, berths, tugs, tug masters, pilots, CT equipment, yard, NCT storage, safety constraints; Marine Safety Officer: environmental limits, chart datum and UKC"; "Manage devices" → U6 "Port Admin: view registered devices and revoke tokens"; "Log out" → U7 "Log out"
- **S5** [Port Server] Authorize the request: role and terminal ownership → D3 "Allowed?"
- **U4** [Office User - Port Admin, Department Manager, CT Admin, Marine Safety Officer] Port Admin: create, edit or deactivate user; assign or end roles and terminal scope → S5 "Authorize the request: role and terminal ownership"
- **U5** [Office User - Port Admin, Department Manager, CT Admin, Marine Safety Officer] Edit master data: port, channel, terminals, berths, tugs, tug masters, pilots, CT equipment, yard, NCT storage, safety constraints; Marine Safety Officer: environmental limits, chart datum and UKC → S5 "Authorize the request: role and terminal ownership"
- **U6** [Office User - Port Admin, Department Manager, CT Admin, Marine Safety Officer] Port Admin: view registered devices and revoke tokens → S5 "Authorize the request: role and terminal ownership"
- **U7** [Office User - Port Admin, Department Manager, CT Admin, Marine Safety Officer] Log out → S11 "End session - token revoked_at"
- **D3** [Port Server] Decision "Allowed?": "No" → S6 "Return 403"; "Yes, read" → S4 "Return data within role and terminal scope"; "Yes, write" → DB "SETUP mode and not on setup allowlist?"
- **S11** [Port Server] End session - token revoked_at → END
- **S6** [Port Server] Return 403 → S15 "Audit REJECTED_ATTEMPT"
- **S4** [Port Server] Return data within role and terminal scope → U3 "View data: port state, port audit log, master-data history (audit log filtered by entity)"
- **DB** [Port Server] Decision "SETUP mode and not on setup allowlist?": "Yes" → S16 "Reject - the port is not ready for operations until ACTIVE"; "No" → D4 "READ_ONLY and not on allowlist?"
- **S15** [Port Server] Audit REJECTED_ATTEMPT → U8 "Refresh and review the latest data"
- **U3** [Office User - Port Admin, Department Manager, CT Admin, Marine Safety Officer] View data: port state, port audit log, master-data history (audit log filtered by entity) → U2 "Choose an action"
- **S16** [Port Server] Reject - the port is not ready for operations until ACTIVE → S15 "Audit REJECTED_ATTEMPT"
- **D4** [Port Server] Decision "READ_ONLY and not on allowlist?": "Yes" → S7 "Return 423 LICENSE_READ_ONLY"; "No" → D7 "updated_at unchanged?"
- **U8** [Office User - Port Admin, Department Manager, CT Admin, Marine Safety Officer] Refresh and review the latest data → U2 "Choose an action"
- **S7** [Port Server] Return 423 LICENSE_READ_ONLY → S15 "Audit REJECTED_ATTEMPT"
- **D7** [Port Server] Decision "updated_at unchanged?": "No" → S12 "Return 409 Conflict"; "Yes" → D8 "Self or last active Port Admin?"
- **S12** [Port Server] Return 409 Conflict → S15 "Audit REJECTED_ATTEMPT"
- **D8** [Port Server] Decision "Self or last active Port Admin?": "Yes" → S13 "Reject - you cannot deactivate yourself or the last active Port Admin, or remove that role"; "No" → D5 "Adds a user, terminal or berth?"
- **S13** [Port Server] Reject - you cannot deactivate yourself or the last active Port Admin, or remove that role → S15 "Audit REJECTED_ATTEMPT"
- **D5** [Port Server] Decision "Adds a user, terminal or berth?": "No" → S9 "Save the change - ending a role sets active_to"; "Yes" → D6 "Within license limits?"
- **S9** [Port Server] Save the change - ending a role sets active_to → D9 "User deactivated?"
- **D6** [Port Server] Decision "Within license limits?": "No" → S8 "Reject 422 PLAN_LIMIT_EXCEEDED - nothing saved; tug master and pilot accounts count as users"; "Yes" → S9 "Save the change - ending a role sets active_to"
- **D9** [Port Server] Decision "User deactivated?": "Yes" → S14 "Set revoked_at on the user's tokens and end sessions"; "No" → S10 "Record audit entry (before and after state)"
- **S8** [Port Server] Reject 422 PLAN_LIMIT_EXCEEDED - nothing saved; tug master and pilot accounts count as users → S15 "Audit REJECTED_ATTEMPT"
- **S14** [Port Server] Set revoked_at on the user's tokens and end sessions → S10 "Record audit entry (before and after state)"
- **S10** [Port Server] Record audit entry (before and after state) → U2 "Choose an action"

**Rules stated as notes**

- Authorization and terminal isolation are enforced by the API, not by hiding UI (attached to S5)
- Token revoke is independent of the MDM certificate revoke - AD-19 (attached to U6)
- READ_ONLY allowlist: master-data edits and user creation blocked; deactivating a user and revoking tokens allowed (attached to D4)
- Setup allowlist: first Port Admin and setup users, port configuration, berths and resources - never operational records; ends at ACTIVE (attached to DB)
- A resource change regenerates pending recommendations only - AD-12 (attached to S10)

#### AD-19 — Device enrollment, VPN and device revocation

**Code:** `activity-diagrams-v3/ATLANTECH_Activity_Diagrams.md`, diagram AD-19. **Related:** 2.3, 2.17. **Requirements:** NFR-SEC-4 (devices and VPN come from the master context; the FRD has no item for them).

**Swimlanes:** Port IT Administrator, MDM Platform, Field User - Managed Device, VPN Gateway, Port Admin, Port Server.

**Story**

Field phones reach the port server from outside the port only through a managed device and a VPN. This diagram covers enrolment, daily connectivity and what happens when a phone is lost or its user leaves.

Enrolment. The port's IT administrator enrols the phone in the MDM as an Android Enterprise device or a supervised iPhone; the device does not request it. The MDM checks the device identity, issues a per-device certificate and pushes the app, a per-app always-on VPN profile and the DNS settings. The local database on the phone is encrypted.

Daily use. When the phone leaves the port Wi-Fi, the per-app VPN starts (WireGuard on UDP 51820 or IPsec). Without mobile data the user keeps working offline and events wait in the Outbox. With data, the VPN gateway checks the device certificate, refuses revoked or invalid ones, points app.atlantech.io to the server's LAN address and routes only the app's traffic through the tunnel. The server still applies normal login and role checks, and the queued events sync. The gateway is the only part of the port facing the internet.

Revocation. If a phone is lost or its user leaves, Port IT revokes it in the MDM. In parallel the certificate is revoked and any active VPN connection is cut. The MDM wipes the device selectively, or records WIPE_PENDING and retries when the phone reconnects; any events not yet synced on that phone are lost. Port IT then informs the Port Admin, who revokes the device's API tokens: the server sets revoked_at on them and ends their sessions. The two controls are independent and both are needed.

**Step-by-step flow** (each step lists where it goes next; END is a final node)

- **START** start → D0 "Triggering event?"
- **D0** Decision "Triggering event?": "New device" → A1 "Enroll the device in the MDM: Android Enterprise or supervised iPhone"; "Field user off Wi-Fi" → A5 "Phone leaves the port Wi-Fi"; "Device lost or user leaves" → A10 "Revoke the device in the MDM"
- **A1** [Port IT Administrator] Enroll the device in the MDM: Android Enterprise or supervised iPhone → E1 "Validate the enrollment request and device identity"
- **A5** [Field User - Managed Device] Phone leaves the port Wi-Fi → A6 "Start per-app always-on VPN - WireGuard UDP 51820 or IPsec"
- **A10** [Port IT Administrator] Revoke the device in the MDM → FK1 (fork/join bar)
- **E1** [MDM Platform] Validate the enrollment request and device identity → DE "Device identity valid?"
- **A6** [Field User - Managed Device] Start per-app always-on VPN - WireGuard UDP 51820 or IPsec → D1 "Mobile data available?"
- **FK1** Fork: in parallel → A15 "Revoke the device certificate"; A19 "Terminate the device's active VPN connection"
- **DE** [MDM Platform] Decision "Device identity valid?": "No" → E2 "Reject enrollment and record audit entry"; "Yes" → A2 "Issue a per-device certificate"
- **D1** [Field User - Managed Device] Decision "Mobile data available?": "No" → A7 "Work offline: record events in the Outbox - AD-15"; "Yes" → A8 "Validate the MDM-issued device certificate"
- **A15** [MDM Platform] Revoke the device certificate → JN1 (fork/join bar)
- **A19** [VPN Gateway] Terminate the device's active VPN connection → JN1 (fork/join bar)
- **E2** [MDM Platform] Reject enrollment and record audit entry → END
- **A2** [MDM Platform] Issue a per-device certificate → A3 "Push the app via managed Play or ABM, the per-app always-on VPN profile and DNS"
- **A7** [Field User - Managed Device] Work offline: record events in the Outbox - AD-15 → A21 "Device reconnects: back on the port LAN, or in coverage"
- **A8** [VPN Gateway] Validate the MDM-issued device certificate → D2 "Certificate valid and not revoked?"
- **JN1** Join: waits for A15, A19 → DW "Device online?"
- **A3** [MDM Platform] Push the app via managed Play or ABM, the per-app always-on VPN profile and DNS → A4 "Device ready for field work - local DB encrypted"
- **A21** [Field User - Managed Device] Device reconnects: back on the port LAN, or in coverage → D3 "Connected how?"
- **D2** [VPN Gateway] Decision "Certificate valid and not revoked?": "No" → A9 "Refuse the tunnel"; "Yes" → A12 "Push DNS: app.atlantech.io to the server LAN IP"
- **DW** [MDM Platform] Decision "Device online?": "Yes" → A11 "Selective wipe of the device"; "No" → A16 "Record WIPE_PENDING"
- **A4** [Field User - Managed Device] Device ready for field work - local DB encrypted → A18 "Record the enrollment in audit"
- **D3** [Field User - Managed Device] Decision "Connected how?": "Port LAN" → A22 "Sync queued events with the server - AD-15"; "Mobile coverage" → A6 "Start per-app always-on VPN - WireGuard UDP 51820 or IPsec"
- **A9** [VPN Gateway] Refuse the tunnel → END
- **A12** [VPN Gateway] Push DNS: app.atlantech.io to the server LAN IP → A13 "Route only ATLANTECH app traffic into the tunnel"
- **A11** [MDM Platform] Selective wipe of the device → A18b "Record revocation and wipe outcome in audit"
- **A16** [MDM Platform] Record WIPE_PENDING → A17 "Retry the wipe when the device reconnects"
- **A18** [MDM Platform] Record the enrollment in audit → END
- **A22** [Field User - Managed Device] Sync queued events with the server - AD-15 → END
- **A13** [VPN Gateway] Route only ATLANTECH app traffic into the tunnel → A14 "Serve API requests - normal login and role checks still apply"
- **A18b** [MDM Platform] Record revocation and wipe outcome in audit → PI1 "Inform the Port Admin"
- **A17** [MDM Platform] Retry the wipe when the device reconnects → A11 "Selective wipe of the device"
- **A14** [Port Server] Serve API requests - normal login and role checks still apply → A22 "Sync queued events with the server - AD-15"
- **PI1** [Port IT Administrator] Inform the Port Admin → PA1 "Revoke the device's API tokens"
- **PA1** [Port Admin] Revoke the device's API tokens → A20 "Set revoked_at on the device's tokens and end its sessions"
- **A20** [Port Server] Set revoked_at on the device's tokens and end its sessions → END

**Rules stated as notes**

- Port IT revokes the certificate in the MDM; the Port Admin revokes the API tokens (attached to A10)
- Un-synced Outbox events on a wiped device are lost (attached to A11)
- The gateway is the only internet-facing port component (attached to A8)
- Outbox events are preserved through app updates (attached to A4)

### State machine diagrams of category 2

#### SM-4 — Berthing request

**Code:** `state-diagrams/ATLANTECH_State_Diagrams.md`, diagram SM-4. **Related:** AD-9–AD-12, 2.9–2.14. **Requirements:** FR-3.6, FR-3.8–FR-3.11.

**States:** SUBMITTED, PRELIMINARY_APPROVED, NEEDS_REVISION, REJECTED, CANCELLED, CUSTOMS_APPROVED, ENTRY_WINDOW_CONFIRMED, RECOMMENDATION_GENERATED, PLAN_CONFIRMED, PLAN_CANCELLED, COMPLETED.

**Story**

This is the life of a berthing request, from entry by staff to the end of the vessel's call. [FULL] on a transition means it is refused in read-only mode.

Before approval. A request is created as SUBMITTED and its vessel is found or created by IMO. While it is SUBMITTED or NEEDS_REVISION it can be edited or cancelled with a reason. Staff can return it for revision; its creator edits and resubmits it. Staff can reject it with a reason, which ends it. Preliminary approval moves it on.

Customs and the entry window. Recording Customs approval sets CUSTOMS_APPROVED and starts an AI Part 1 run. Staff may reject all proposed windows (the proposal becomes REJECTED with its reason; the request stays) or ask for a recompute, which replaces the old run. Confirming a window, after the server re-checks it, sets ENTRY_WINDOW_CONFIRMED and starts AI Part 2. Missing environmental data (ENV_DATA_UNAVAILABLE) and NO_FEASIBLE_WINDOW are Part 1 run outcomes, not states. As long as no plan is confirmed, the window can be reopened, back to CUSTOMS_APPROVED.

Recommendation and plan. When Part 2 produces a version (from the solver or the FIFO fallback), the request is RECOMMENDATION_GENERATED. Regenerating creates a new PENDING_REVIEW version and replaces the previous one; an override creates a MODIFIED_BY_STAFF version. If no feasible plan exists the request stays ENTRY_WINDOW_CONFIRMED and the vessel waits. Confirming the plan, after an availability re-check, books the berth, tugs and pilot, sets the version CONFIRMED and sets PLAN_CONFIRMED.

After confirmation. A confirmed delay re-plan keeps the request in PLAN_CONFIRMED but replaces the plan version. The plan can be cancelled normally if no component has started, or by the Port Admin's safety exception with a reason. A cancelled plan goes back to ENTRY_WINDOW_CONFIRMED if the call continues, or ends. When every component is completed, the request is COMPLETED. Requests never expire automatically.

**Transitions** (event [guard] / action)

| From | To | Event [guard] / action |
|---|---|---|
| initial | SUBMITTED | create request [FULL] / find-or-create vessel by IMO |
| SUBMITTED | PRELIMINARY_APPROVED | preliminary approval [FULL] |
| SUBMITTED | NEEDS_REVISION | return for revision / reason |
| SUBMITTED | REJECTED | reject / reason |
| SUBMITTED | CANCELLED | cancel [FULL] / reason |
| NEEDS_REVISION | SUBMITTED | creator resubmits [FULL] |
| NEEDS_REVISION | CANCELLED | cancel [FULL] / reason |
| PRELIMINARY_APPROVED | CUSTOMS_APPROVED | customs approval [FULL] / enqueue Part 1 run |
| CUSTOMS_APPROVED | ENTRY_WINDOW_CONFIRMED | confirm window [FULL and server checks pass] / enqueue Part 2 |
| ENTRY_WINDOW_CONFIRMED | CUSTOMS_APPROVED | reopen entry window [FULL and no confirmed plan] / reason, new Part 1 run |
| ENTRY_WINDOW_CONFIRMED | RECOMMENDATION_GENERATED | Part 2 produced a version (solver or FIFO) |
| RECOMMENDATION_GENERATED | PLAN_CONFIRMED | confirm plan [FULL and availability re-check passes] / book berth, tug, pilot, version CONFIRMED |
| PLAN_CONFIRMED | PLAN_CANCELLED | cancel plan [FULL and no component STARTED] / release resources |
| PLAN_CONFIRMED | PLAN_CANCELLED | Port Admin safety exception [reason given] / cancel remaining components, audit |
| PLAN_CONFIRMED | COMPLETED | all components completed |
| PLAN_CANCELLED | ENTRY_WINDOW_CONFIRMED | re-plan [call continues and FULL] |
| PLAN_CANCELLED | final | call does not continue |
| COMPLETED | final | (automatic) |
| REJECTED | final | (automatic) |
| CANCELLED | final | (automatic) |

**Internal transitions** (handled without leaving the state)

- SUBMITTED: edit request [FULL]
- NEEDS_REVISION: edit request [FULL]
- CUSTOMS_APPROVED: reject all windows / reason recorded; recompute [FULL] / new Part 1 run, old run REPLACED
- RECOMMENDATION_GENERATED: regenerate [FULL] / new version PENDING_REVIEW, previous REPLACED; override [FULL] / MODIFIED_BY_STAFF version
- PLAN_CONFIRMED: delay re-plan confirmed [FULL] / reserve new, release unused, keep STARTED, old version REPLACED

**Notes on the diagram**

- On CUSTOMS_APPROVED: ENV_DATA_UNAVAILABLE and NO_FEASIBLE_WINDOW are Part 1 run outcomes, not states: staff submit manual environmental data and recompute.
- On ENTRY_WINDOW_CONFIRMED: NO_FEASIBLE_PLAN is an outcome: the request stays here (the vessel waits) and staff may regenerate.
- On SUBMITTED: Reject, return, reject all windows and the safety exception are allowed in READ_ONLY. No automatic expiry of requests.

#### SM-5 — Operational plan

**Code:** `state-diagrams/ATLANTECH_State_Diagrams.md`, diagram SM-5. **Related:** AD-11–AD-14, 2.14–2.16, 3.3. **Requirements:** FR-3.11, FR-5.1–FR-5.4, FR-8.8; NFR-SYNC-1, NFR-CONC-1.

**States:** CONFIRMED, PILOT_UNASSIGNED, PILOT_ASSIGNED, PILOT_STARTED, PILOT_DONE, TUG_UNASSIGNED, TUG_ASSIGNED, TUG_STARTED, TUG_DONE, YARD_PENDING, YARD_NOT_APPLICABLE, YARD_ACCEPTED, YARD_DONE, COMPLETED, CANCELLED.

**Story**

Once confirmed, an operational plan has its own record with three statuses: CONFIRMED, COMPLETED and CANCELLED. Inside CONFIRMED, three parts progress in parallel: pilotage, tug and yard.

Creation. Confirming the plan creates it as CONFIRMED, books the berth, tugs and pilot, sets the request to PLAN_CONFIRMED and sends the components to the officers. For a container terminal it also requests a yard recommendation.

Pilot and tug regions. Each component starts UNASSIGNED. The system proposes a pilot or a tug master and tug; the department officer confirms or replaces the proposal, and the crew member is notified. Field status updates move the component to STARTED and then DONE. Acknowledgement is read from the notification; it is not a separate state.

Yard region. For a container terminal the yard part starts as YARD_PENDING; otherwise it is NOT_APPLICABLE. Generated, failed or rejected recommendations all stay YARD_PENDING. An accepted or adjusted recommendation, including one exported to the TOS, is YARD_ACCEPTED, and the terminal's reported status makes it YARD_DONE.

Change and end. A confirmed delay re-plan keeps the plan CONFIRMED: changed components go back to UNASSIGNED and started ones are kept. The plan becomes COMPLETED when pilot and tug are done and the yard is done or not applicable, which completes the request. It is CANCELLED either normally, if nothing has started, or by the Port Admin's safety exception with a reason; in both cases the request becomes PLAN_CANCELLED and unused resources are released.

**Transitions** (event [guard] / action)

| From | To | Event [guard] / action |
|---|---|---|
| initial | CONFIRMED | plan confirmed [FULL] / create plan, book berth, tug, pilot, request PLAN_CONFIRMED, send components, request yard recommendation if container terminal |
| initial (inside CONFIRMED, region 1) | PILOT_UNASSIGNED | (automatic) |
| PILOT_UNASSIGNED (inside CONFIRMED, region 1) | PILOT_ASSIGNED | officer confirms or replaces the proposal / notify pilot |
| PILOT_ASSIGNED (inside CONFIRMED, region 1) | PILOT_STARTED | status started |
| PILOT_STARTED (inside CONFIRMED, region 1) | PILOT_DONE | status completed |
| initial (inside CONFIRMED, region 2) | TUG_UNASSIGNED | (automatic) |
| TUG_UNASSIGNED (inside CONFIRMED, region 2) | TUG_ASSIGNED | officer confirms or replaces the proposal / notify Tug Master |
| TUG_ASSIGNED (inside CONFIRMED, region 2) | TUG_STARTED | status started |
| TUG_STARTED (inside CONFIRMED, region 2) | TUG_DONE | status completed |
| initial (inside CONFIRMED, region 3) | YARD_PENDING | [container terminal] |
| initial (inside CONFIRMED, region 3) | YARD_NOT_APPLICABLE | [otherwise] |
| YARD_PENDING (inside CONFIRMED, region 3) | YARD_ACCEPTED | yard recommendation accepted or adjusted |
| YARD_ACCEPTED (inside CONFIRMED, region 3) | YARD_DONE | terminal status reported |
| CONFIRMED | COMPLETED | last component completed [pilot DONE and tug DONE and yard DONE or NOT_APPLICABLE] / request COMPLETED |
| CONFIRMED | CANCELLED | cancel [FULL and no component STARTED] / release resources, request PLAN_CANCELLED |
| CONFIRMED | CANCELLED | Port Admin safety exception [reason given] / cancel remaining, release unused, request PLAN_CANCELLED, audit |
| COMPLETED | final | (automatic) |
| CANCELLED | final | (automatic) |

**Notes on the diagram**

- On CONFIRMED: Internal transition: delay re-plan confirmed / changed components back to UNASSIGNED, STARTED components kept; plan stays CONFIRMED. Acknowledged is read from the notification, not a state. A rejected yard recommendation keeps YARD_PENDING. A significant deviation leads to a delay re-plan proposal; thresholds are Port Admin settings.

## Category 3 — Execution Feedback and Model Learning

### UC-3 — Use case diagram: What really happened, and how the AI learns from it

**Code:** `use-case-diagrams/ATLANTECH_Use_Case_Diagrams.md`, diagram 3. **System boundary:** ATLANTECH: Execution Feedback and Model Learning. **Requirements:** FR-5.3, FR-5.4, FR-6.1–FR-6.4, FR-8.9, FR-8.10, FR-9.4; NFR-SYNC-1, NFR-UX-3, NFR-PERF-4.

This diagram starts where Diagram 2 ends. The plan is running: field crews report what actually happens from their phones, even without coverage, the office sees it live, and the system compares the plan with reality. Those differences feed AI Part 3, which evaluates the models and retrains them under control.

**Actors**

- **Mobile User**: Anyone using the field app. The Remote Field User (pilot, tug master) works outside port Wi-Fi; the On-site Field User works inside the terminal.
- **Office User**: Watches the dashboard update live.
- **Port Authority Staff**: Browse deviations and review suspicious events.
- **Port Admin**: Reviews a model candidate that was flagged.
- **System actors**: Port Server Sync Endpoint, Realtime Server and the AI Part 3 Engine.

**Story**

*1. Opening the app.* On first launch the app identifies the port from the fixed server address. The user sees assigned tasks, keeps working offline from the local data, and the app shows clearly which actions are blocked when the port is in read-only mode.

*2. Reporting what happens.* Pilots, tug masters and terminal supervisors update the actual status of each task. Every update, and every acknowledgement from Diagram 2, is first written to the Outbox on the phone, online or offline. When an actual time differs from the plan, the deviation is recorded; a significant one triggers a delay re-plan proposal in Diagram 2.

*3. Offline sync.* When connectivity returns, or when the user asks, the app synchronizes the Outbox. It first checks real connectivity and retries the check with backoff. The server applies each event once, using its idempotency key. An invalid event is rejected with a reason the user can see, and an event whose device clock looks wrong is flagged. A user who must sign in again, or an app below the minimum version, pauses the sync until it is fixed.

*4. Live updates.* The realtime server pushes updates to phones and to the office dashboard. A phone that reconnects catches up on what it missed, and Android keeps the connection alive in the background during an active task.

*5. Learning from deviations.* Staff browse deviations and review clock-skew-suspect events; a suspect event stays untrusted and is never used for training. AI Part 3 evaluates outcomes, drift and forecast bias on trusted data, retrains a candidate model and deploys it only if it is not worse than the current one. A flagged candidate goes to the Port Admin for review. Nothing in this loop ever relaxes a safety constraint.

**Use cases by package** (actor associations in brackets; related sequence · activity · state diagrams after the package name)

- **Mobile App Basics** — 3.1 · AD-17
  - Identify Port on First Launch (Mobile User)
  - View Assigned Tasks (Mobile User)
  - Show Read-Only Restrictions (reached only through include or extend)
  - Work Offline with Local Data (Mobile User)
- **Execution Tracking** — 3.3 · AD-15, AD-16 · SM-5
  - Update Actual Task Status (Remote Field User, On-site Field User)
  - Update Terminal Actual Status (On-site Field User)
  - Queue Event in Outbox (reached only through include or extend)
  - Detect and Record Deviation (reached only through include or extend)
- **Offline Sync** — 3.2 · AD-15 · SM-6
  - Synchronize Outbox (Mobile User)
  - Check Real Connectivity (reached only through include or extend)
  - Retry Connectivity Check with Backoff (reached only through include or extend)
  - Apply Event Idempotently (Port Server Sync Endpoint)
  - Reject Invalid Event and Show Reason (reached only through include or extend)
  - Flag Clock-skew-suspect Event (reached only through include or extend)
- **Model Learning** — 3.4 · AD-16
  - Browse Deviations (Port Authority Staff)
  - Review Clock-skew-suspect Events (Port Authority Staff)
  - Evaluate Outcomes, Drift and Forecast Bias (AI Part 3 Engine)
  - Retrain and Conditionally Deploy Model (AI Part 3 Engine)
  - Review Flagged Model Candidate (Port Admin)
- **Realtime Updates** — 3.2 · AD-15
  - Receive Realtime Update (Mobile User, Realtime Server)
  - Reconnect and Catch Up (reached only through include or extend)
  - Keep Realtime Alive in Background (Remote Field User)
  - Receive Live Dashboard Updates (Office User, Realtime Server)
- Reference to another diagram: Acknowledge Notification (Diagram 2)
- Reference to another diagram: Re-generate Recommendation or Delay Re-plan (Diagram 2)
- Reference to another diagram: Re-authenticate and Resume Outbox (Diagram 2)
- Reference to another diagram: Enforce Minimum App Version (Diagram 2)

**Include and extend relations** (read "A includes B" as: A always performs B; "A extends B" as: A optionally adds to B)

- Show Read-Only Restrictions **extends** View Assigned Tasks
- Queue Event in Outbox **extends** Update Actual Task Status
- Queue Event in Outbox **extends** Update Terminal Actual Status
- Queue Event in Outbox **extends** Acknowledge Notification (Diagram 2)
- Detect and Record Deviation **extends** Update Actual Task Status
- Detect and Record Deviation **extends** Update Terminal Actual Status
- Detect and Record Deviation **triggers** Re-generate Recommendation or Delay Re-plan (Diagram 2)
- Synchronize Outbox **includes** Apply Event Idempotently
- Synchronize Outbox **includes** Check Real Connectivity
- Retry Connectivity Check with Backoff **extends** Check Real Connectivity
- Reject Invalid Event and Show Reason **extends** Apply Event Idempotently
- Flag Clock-skew-suspect Event **extends** Apply Event Idempotently
- Re-authenticate and Resume Outbox (Diagram 2) **extends** Synchronize Outbox
- Enforce Minimum App Version (Diagram 2) **extends** Synchronize Outbox
- Review Clock-skew-suspect Events **extends** Browse Deviations
- Retrain and Conditionally Deploy Model **includes** Evaluate Outcomes, Drift and Forecast Bias
- Review Flagged Model Candidate **extends** Retrain and Conditionally Deploy Model
- Reconnect and Catch Up **extends** Receive Realtime Update
- Keep Realtime Alive in Background **extends** Receive Realtime Update

### Sequence diagrams of category 3

#### 3.1 — Mobile first launch and offline work

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 3.1. **Related:** AD-17, AD-15. **Requirements:** FR-5.3, FR-5.4; NFR-UX-3, NFR-SEC-3.

**Participants**

- **Field User**: actor (person)
- **Mobile App**: boundary (user interface)
- **Local DB and Outbox**: database (data store)
- **Port API (Mobile Sync)**: control (service, API, worker or scheduler)

**Story**

Field users work where coverage is poor, so the app is built to work offline first. This diagram covers the first launch and how every change is captured on the phone.

First launch. The app always talks to the same fixed address, app.atlantech.io, which the port's split DNS points to its own server. With no token yet, it reads /system/info and stores the port's id, name, license mode, token warning days and minimum app version. If the server cannot be reached, the user is told to check the network.

Working offline. The user's assigned tasks come from the local cache, with the time of the last sync. If the port is in read-only mode the app shows a banner and makes clear which actions are blocked; status updates and acknowledgements on running work stay possible.

Capturing changes. Every write, whether online or offline, goes the same way: the app checks it, stamps the device time, saves it locally and adds an event to the Outbox with its own id and idempotency key. The event waits as PENDING until the next sync, shown in the next diagram.

**Message flow, top to bottom**

- Field User → Mobile App: Open the app for the first time
- Mobile App → Port API (Mobile Sync): GET /system/info (fixed address app.atlantech.io, no token)
- **Alternative paths — case: Server reachable**
  - Port API (Mobile Sync) → Mobile App (reply): port_public_id, port name, license_mode, token_warning_days_left, min_app_version
  - Mobile App → Local DB and Outbox: Store port configuration
  - Mobile App → Field User (reply): Port configured, sign in
- **Otherwise — case: Unreachable**
  - Mobile App → Field User (reply): Cannot reach the port server, check the network
- Field User → Mobile App: View assigned tasks
- Mobile App → Local DB and Outbox: Read task cache
- **Alternative paths — case: Cached tasks**
  - Mobile App → Field User (reply): Tasks with last-synced time
- **Otherwise — case: Cache empty**
  - Mobile App → Field User (reply): Sync required
- **Optional — only when: Port is READ_ONLY**
  - Mobile App → Field User (reply): Read-only banner, blocked actions shown clearly
- Field User → Mobile App: Update a task status or acknowledge (online or offline)
- Mobile App (internal): Validate and stamp device time
- Mobile App → Local DB and Outbox: Save the change locally
- Mobile App → Local DB and Outbox: Add Outbox event (id, idempotency key, device time) PENDING
- Mobile App → Field User (reply): Saved, waiting to sync

#### 3.2 — Outbox synchronization and catch-up

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 3.2. **Related:** AD-15, SM-6. **Requirements:** FR-5.3, FR-5.4, FR-6.1; NFR-SYNC-1, NFR-UX-3, NFR-PERF-4.

**Participants**

- **Field User**: actor (person)
- **Mobile App**: boundary (user interface)
- **Local DB and Outbox**: database (data store)
- **Port API (Mobile Sync)**: control (service, API, worker or scheduler)
- **Port Database**: database (data store)
- **Realtime Server (Reverb)**: control (service, API, worker or scheduler)

**Story**

This is how events waiting on the phone reach the port server, and how the phone catches up with what changed meanwhile.

Connectivity. A sync starts when the network changes or when the user taps sync. The app first checks that the server is really reachable with a ping, retrying with a growing delay (from 2 seconds, doubling, up to 60) for at most five tries in one cycle. If it still fails, events stay PENDING for the next cycle. There is no limit on how long an event can wait.

Opening the sync. An expired or revoked token gets 401 and the user signs in again; an app below the minimum version gets 426 and must update. In both cases nothing is lost; sync just pauses.

Sending. Events go one by one, in order. Each is marked SENDING; if no answer comes back it returns to PENDING and the cycle ends. The server applies each event exactly once thanks to its idempotency key (stored as client_event_id), so a resent event is simply confirmed. An event whose received_at minus client_sent_at is more than five minutes is applied but flagged as clock-skew suspect. An invalid event, or a create event while the port is read-only, is REJECTED with a reason the user can read. Status updates and acknowledgements are accepted even in read-only mode.

Catching up. The app then asks for all changes since its last sync token and refreshes its task cache. While connected, the realtime server pushes changes live, and after a reconnect the app catches up on what it missed. Finished and rejected events are purged from the phone after 30 days.

**Message flow, top to bottom**

- *Note:* Sync starts when connectivity changes or the user syncs manually
- **Loop: Up to 5 tries in this cycle (backoff from 2 s, doubling, max 60 s)**
  - Mobile App → Port API (Mobile Sync): GET /system/ping
  - Port API (Mobile Sync) → Mobile App (reply): Pong, or no answer
- **Alternative paths — case: No answer after 5 tries**
  - Mobile App → Field User (reply): Sync pending, events kept PENDING
- **Otherwise — case: Online**
  - Mobile App → Port API (Mobile Sync): Open sync (token, app version)
  - **Alternative paths — case: 401 token expired or revoked**
    - Port API (Mobile Sync) → Mobile App (reply): 401
    - Mobile App → Field User (reply): Sign in again, sync paused
  - **Otherwise — case: 426 app too old**
    - Port API (Mobile Sync) → Mobile App (reply): 426
    - Mobile App → Field User (reply): Update required, sync paused
  - **Otherwise — case: Session open**
    - **Loop: Each PENDING event in order**
      - Mobile App → Local DB and Outbox: Mark SENDING
      - Mobile App → Port API (Mobile Sync): Send event (idempotency key, client_sent_at)
      - **Alternative paths — case: No answer**
        - Mobile App → Local DB and Outbox: Back to PENDING, end this cycle
      - **Otherwise — case: Applied or duplicate**
        - Port API (Mobile Sync) → Port Database: Apply once (or find already applied), audit entry
        - **Optional — only when: received_at minus client_sent_at over 5 min**
          - Port API (Mobile Sync) → Port Database: Flag clock-skew suspect
        - Port API (Mobile Sync) → Mobile App (reply): Applied
        - Mobile App → Local DB and Outbox: DONE
      - **Otherwise — case: Invalid, or a create event in READ_ONLY**
        - Port API (Mobile Sync) → Mobile App (reply): Rejected with reason
        - Mobile App → Local DB and Outbox: REJECTED, shown to the user
    - Mobile App → Port API (Mobile Sync): GET /api/v1/sync/changes?since=lastSyncToken
    - Port API (Mobile Sync) → Port Database: Changes in the user's scope
    - Port API (Mobile Sync) → Mobile App (reply): Changes and new sync token
    - Mobile App → Local DB and Outbox: Update task cache
    - Mobile App → Field User (reply): Summary (applied, rejected, flagged)
- **Optional — only when: Live updates while connected**
  - Realtime Server (Reverb) → Mobile App (reply): Push task changes
  - Realtime Server (Reverb) → Mobile App (reply): After reconnect, catch up on missed changes
- *Note:* DONE and REJECTED events are purged from the phone after 30 days

#### 3.3 — Execution tracking and deviations

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 3.3. **Related:** AD-16, AD-12, SM-5. **Requirements:** FR-6.1–FR-6.4, FR-8.9, FR-8.10, FR-9.4; NFR-SYNC-1, NFR-UX-2.

**Participants**

- **Field User**: actor (person)
- **Port Authority Staff**: actor (person)
- **Mobile App**: boundary (user interface)
- **Port API (Tracking)**: control (service, API, worker or scheduler)
- **Port Database**: database (data store)
- **Part 2 Queue**: queue (Redis)

**Story**

While the plan runs, the people in the field report what really happens, and the system compares it with what was planned.

Reporting. Pilots, tug masters and terminal supervisors update the actual status of each task on their phones. As with every mobile write, the update goes into the Outbox and reaches the server at the next sync. The server stores it once, whatever the number of retries, and audits it.

Comparing. The server reads the planned values for the task. If the actual time differs, it classifies the deviation by type and size and records it. A significant deviation, judged against thresholds the Port Admin sets per operation type, queues a delay re-plan for Part 2 and alerts staff live. The re-plan itself is shown in the plan confirmation diagram.

Reviewing. Staff can browse all deviations. Events whose device clock looked wrong are marked. Staff can review them and record a resolution note, but there is no automatic correction: a suspect event stays untrusted and is never used to train the models.

**Message flow, top to bottom**

- Field User → Mobile App: Update the actual status of a task
- Mobile App (internal): Save locally and queue in the Outbox
- Mobile App → Port API (Tracking): Event delivered at the next sync
- Port API (Tracking) → Port Database: Store the actual status once (idempotent), audit entry
- Port API (Tracking) → Port Database: Read planned values for the task
- **Optional — only when: Actual differs from plan**
  - Port API (Tracking) (internal): Classify deviation type and size
  - Port API (Tracking) → Port Database: Insert deviation
  - **Optional — only when: Deviation is significant**
    - Port API (Tracking) → Part 2 Queue: Enqueue delay re-plan
    - Port API (Tracking) → Port Authority Staff (reply): SSE significant deviation, re-plan requested
- Port API (Tracking) → Mobile App (reply): Accepted
- Port Authority Staff → Port API (Tracking): Browse deviations
- Port API (Tracking) → Port Database: Read deviations and clock-skew flags
- Port API (Tracking) → Port Authority Staff (reply): Deviations with suspect indicator
- **Optional — only when: Review clock-skew-suspect events**
  - Port Authority Staff → Port API (Tracking): Open suspect events
  - Port API (Tracking) → Port Authority Staff (reply): Device time, server time, difference
  - Port Authority Staff → Port API (Tracking): Record a resolution note
  - **Alternative paths — case: READ_ONLY**
    - Port API (Tracking) → Port Authority Staff (reply): 423 LICENSE_READ_ONLY
  - **Otherwise — case: FULL**
    - Port API (Tracking) → Port Database: Save the note, audit entry
    - Port API (Tracking) → Port Authority Staff (reply): 200
  - *Note:* A suspect event stays untrusted and is never used for training

#### 3.4 — Model evaluation and guarded retraining

**Code:** `sequence-diagrams/ATLANTECH_Sequence_Diagrams.md`, diagram 3.4. **Related:** AD-16. **Requirements:** none (AI Part 3 retraining comes from the architecture and master context; the FRD and NFR have no item for it).

**Participants**

- **Port Admin**: actor (person)
- **Part 3 Scheduler**: control (service, API, worker or scheduler)
- **AI Part 3 Worker**: control (service, API, worker or scheduler)
- **Port Database**: database (data store)
- **Port API**: control (service, API, worker or scheduler)

**Story**

The last step closes the loop: AI Part 3 learns from what actually happened, under strict guards.

Evaluating. On a schedule, Part 3 loads the outcomes: plan against actual, deviations, staff overrides and waiting times, using only trusted events. It computes accuracy measures such as the mean absolute error, the override rate, waiting time and how accurate the entry windows were. It checks the service-time, demand and delay-risk models for drift; drift above the threshold raises a DRIFT_ALERT notification to the Port Admin; otherwise the drift measurement is stored as not drifted. It also stores a new forecast bias correction, which Part 1 applies when reading forecasts; the provider's raw data is never overwritten.

Retraining. If there is enough trusted data, Part 3 trains a candidate model on a time-based split and compares it with the current one. The candidate is deployed automatically only if it is not worse on both the error and the override rate, and the previous model is kept for rollback. A candidate that is worse is not deployed; it is flagged and the Port Admin can review it. Staff overrides are treated as a signal to analyse, never as a silent trigger.

Nothing in this loop ever relaxes a safety constraint or an environmental limit.

**Message flow, top to bottom**

- *Note:* Runs on a schedule. Only trusted events are used. Part 3 never changes safety limits.
- Part 3 Scheduler → AI Part 3 Worker: Periodic evaluation
- AI Part 3 Worker → Port Database: Load outcomes (plan vs actual, deviations, overrides, waiting times)
- AI Part 3 Worker (internal): Compute MAE, override rate, waiting time, window accuracy
- AI Part 3 Worker → Port Database: Store evaluation
- AI Part 3 Worker (internal): Drift check on service time, demand and delay-risk models
- **Alternative paths — case: Drift above threshold**
  - AI Part 3 Worker → Port Database: Drift alert (DRIFT_ALERT notification), audit entry
  - Port API → Port Admin (reply): SSE drift alert
- **Otherwise — case: Healthy**
  - AI Part 3 Worker → Port Database: Store drift measurement (is_drifted false)
- AI Part 3 Worker → Port Database: Store forecast bias correction (new version, provider data untouched)
- Part 3 Scheduler → AI Part 3 Worker: Periodic retraining
- AI Part 3 Worker → Port Database: Load trusted training data
- **Alternative paths — case: Not enough data**
  - AI Part 3 Worker → Port Database: Retraining skipped, current model stays
- **Otherwise — case: Enough data**
  - AI Part 3 Worker (internal): Train a candidate on a time-based split
  - AI Part 3 Worker (internal): Compare with the current model on MAE and override rate
  - **Alternative paths — case: Candidate not worse on both**
    - AI Part 3 Worker → Port Database: Deploy candidate, keep the previous model for rollback, audit entry
    - Port API → Port Admin (reply): SSE new model deployed with its metrics
  - **Otherwise — case: Candidate worse**
    - AI Part 3 Worker → Port Database: Candidate flagged, current model stays, audit entry
    - Port API → Port Admin (reply): SSE candidate flagged for review

### Activity diagrams of category 3

#### AD-15 — Field status update, Outbox sync and realtime

**Code:** `activity-diagrams-v3/ATLANTECH_Activity_Diagrams.md`, diagram AD-15. **Related:** 3.1, 3.2, SM-6. **Requirements:** FR-5.3, FR-5.4, FR-6.1, FR-8.9, FR-9.4; NFR-SYNC-1, NFR-UX-3, NFR-PERF-4.

**Swimlanes:** Field User - Pilot, Tug Master, CT Supervisor, Mobile App, Port Server, Office User.

**Story**

This diagram follows a single field update, from the tap on the phone to the live update on the office dashboard, including everything that can go wrong on the way.

Capture. A pilot, tug master or CT supervisor opens an assigned task from the local cache and sets its actual status, or acknowledges a notification. The app writes an event to the Outbox with an idempotency key, the recorded time and the user, marks it PENDING and shows it as not yet synced. When the app restarts, entries left in SENDING are reset to PENDING.

Starting a sync. A sync starts when connectivity changes or when the user syncs manually. Without a valid token the Outbox is held and the user must sign in again. The app pings the server; if it does not answer it waits with a growing delay (from 2 seconds, doubling, up to 60) and tries again, and after five tries the cycle ends and the events stay PENDING.

Sending. The next PENDING entries are marked SENDING and sent in order. If the server answers 401 or 426, or does not answer, the entries go back to PENDING: after 401 the user signs in again, after 426 the app must be updated, and after a send failure the cycle simply ends. Pending entries survive app updates and network failures.

On the server. Each event is processed on its own. A known client_event_id returns the earlier result, so a resend is harmless. In read-only mode creation events are rejected with 423, while status updates and acknowledgements are applied. An event that no longer makes sense, for example on a cancelled plan, is rejected with a reason. A valid event is applied and its client_event_id, reported_at, client_sent_at and received_at are stored. If the phone's sending time is more than five minutes away from the server's receiving time, the event is still applied but flagged clock_skew_suspect, which only keeps it out of evaluation and training. After the database commit, the deviation check runs and a realtime event is published.

Results. In parallel, the dashboard updates live, other phones receive the event and fetch the details, and the sender gets its answer. The entry becomes DONE, or REJECTED with its reason kept in a list the user can read. Both are purged from the phone after 30 days. Phones that were disconnected catch up through the sync/changes endpoint.

**Step-by-step flow** (each step lists where it goes next; END is a final node)

- **START** start → D0 "Triggering event?"
- **D0** Decision "Triggering event?": "Field update" → F1 "Open an assigned task"; "App restart" → A0 "On restart: reset stale SENDING entries to PENDING"
- **F1** [Field User - Pilot, Tug Master, CT Supervisor] Open an assigned task → A1 "Load the task from the local cache"
- **A0** [Mobile App] On restart: reset stale SENDING entries to PENDING → A4 "Sync trigger: connectivity change or manual sync"
- **A1** [Mobile App] Load the task from the local cache → F2 "Set the actual status or acknowledge a notification"
- **A4** [Mobile App] Sync trigger: connectivity change or manual sync → D8 "Signed in with a valid token?"
- **F2** [Field User - Pilot, Tug Master, CT Supervisor] Set the actual status or acknowledge a notification → A2 "Write event to the Outbox: idempotency_key, recorded_at, user_id, state PENDING"
- **D8** [Mobile App] Decision "Signed in with a valid token?": "No" → A8 "Hold the Outbox unsent and ask the user to sign in again - AD-17"; "Yes" → A5 "Ping /system/ping"
- **A2** [Mobile App] Write event to the Outbox: idempotency_key, recorded_at, user_id, state PENDING → A3 "Show the update locally as not yet synced"
- **A8** [Mobile App] Hold the Outbox unsent and ask the user to sign in again - AD-17 → END
- **A5** [Mobile App] Ping /system/ping → D1 "Server reachable?"
- **A3** [Mobile App] Show the update locally as not yet synced → A4 "Sync trigger: connectivity change or manual sync"
- **D1** [Mobile App] Decision "Server reachable?": "No" → DT "Fewer than 5 tries in this cycle?"; "Yes" → A13 "Mark the next PENDING entries SENDING"
- **DT** [Mobile App] Decision "Fewer than 5 tries in this cycle?": "Yes" → A10 "Wait with backoff: 2 s, doubling, max 60 s"; "No" → A6 "End the cycle - keep working offline, events stay PENDING"
- **A13** [Mobile App] Mark the next PENDING entries SENDING → A7 "Send the batch in order to POST /sync/events with idempotency_key and client_sent_at"
- **A10** [Mobile App] Wait with backoff: 2 s, doubling, max 60 s → A5 "Ping /system/ping"
- **A6** [Mobile App] End the cycle - keep working offline, events stay PENDING → END
- **A7** [Mobile App] Send the batch in order to POST /sync/events with idempotency_key and client_sent_at → D2 "Request result?"
- **D2** [Port Server] Decision "Request result?": "401" → A21 "Return SENDING entries to PENDING"; "426" → A21 "Return SENDING entries to PENDING"; "No answer or transient error" → A21 "Return SENDING entries to PENDING"; "200: per-event processing" → D3 "client_event_id already stored?"
- **A21** [Mobile App] Return SENDING entries to PENDING → "after 401" → A8 "Hold the Outbox unsent and ask the user to sign in again - AD-17"; "after 426" → A9 "Stop sync and show update required - Outbox preserved"; "after a send failure" → A6 "End the cycle - keep working offline, events stay PENDING"
- **D3** [Port Server] Decision "client_event_id already stored?": "Yes" → S1 "Return the previous result: duplicate"; "No" → DR "READ_ONLY and a creation event?"
- **A9** [Mobile App] Stop sync and show update required - Outbox preserved → END
- **S1** [Port Server] Return the previous result: duplicate → A11 "Mark entry DONE and show the synced confirmation"
- **DR** [Port Server] Decision "READ_ONLY and a creation event?": "Yes" → S3r "Reject with 423"; "No" → S2 "Validate the event"
- **A11** [Mobile App] Mark entry DONE and show the synced confirmation → END
- **S3r** [Port Server] Reject with 423 → A12 "Mark entry REJECTED and keep the reason in the rejected list"
- **S2** [Port Server] Validate the event → D4 "Event still logical?"
- **A12** [Mobile App] Mark entry REJECTED and keep the reason in the rejected list → END
- **D4** [Port Server] Decision "Event still logical?": "No" → S3 "Reject with reason, e.g. plan cancelled"; "Yes" → S4 "Apply the event, update resource state, store client_event_id, reported_at, client_sent_at and received_at"
- **S3** [Port Server] Reject with reason, e.g. plan cancelled → A12 "Mark entry REJECTED and keep the reason in the rejected list"
- **S4** [Port Server] Apply the event, update resource state, store client_event_id, reported_at, client_sent_at and received_at → D5 "Clock gap over 5 min?"
- **D5** [Port Server] Decision "Clock gap over 5 min?": "Yes" → S5 "Mark clock_skew_suspect: received_at minus client_sent_at over 5 min - still applied now"; "No" → S9 "Commit the DB transaction"
- **S5** [Port Server] Mark clock_skew_suspect: received_at minus client_sent_at over 5 min - still applied now → S9 "Commit the DB transaction"
- **S9** [Port Server] Commit the DB transaction → S6 "Run the deviation check - AD-16"
- **S6** [Port Server] Run the deviation check - AD-16 → S7 "Publish the realtime event id"
- **S7** [Port Server] Publish the realtime event id → FK1 (fork/join bar)
- **FK1** Fork: in parallel → O1 "Dashboard receives the live update via SSE"; W1 "Other devices: receive the WS event id and GET the details"; S8 "Return applied"
- **O1** [Office User] Dashboard receives the live update via SSE → JN1 (fork/join bar)
- **W1** [Mobile App] Other devices: receive the WS event id and GET the details → JN1 (fork/join bar)
- **S8** [Port Server] Return applied → JN1 (fork/join bar)
- **JN1** Join: waits for O1, W1, S8 → A11 "Mark entry DONE and show the synced confirmation"

**Rules stated as notes**

- Android keeps the WS alive with a foreground service during an active task; iOS has no background WS (attached to W1)
- Pending entries survive app updates and network failures (attached to A21)
- In READ_ONLY, status updates and acknowledgements are applied; only creation events are rejected (attached to DR)
- Notifications are sent only after the DB commit (attached to S9)
- A suspect event still changes operational state; its untrusted label only excludes it from evaluation and training (attached to S5)
- Other devices and reconnecting apps catch up with GET /api/v1/sync/changes?since=lastSyncToken (attached to W1)
- DONE and REJECTED entries are purged after 30 days (attached to A11)

#### AD-16 — Deviation detection and AI feedback loop

**Code:** `activity-diagrams-v3/ATLANTECH_Activity_Diagrams.md`, diagram AD-16. **Related:** 3.3, 3.4, AD-12. **Requirements:** FR-6.2–FR-6.4; NFR-UX-2.

**Swimlanes:** Port Server, Port Authority Staff, AI Part 3 - Feedback Loop, Port Admin.

**Story**

This diagram closes the loop between what was planned and what really happened. The port server detects deviations, staff review them, and AI Part 3 learns only from trustworthy data.

Detecting. Each applied actual status is compared with the plan using reported_at, the time it was recorded on the phone. If the difference is within the threshold the Port Admin set for that operation type, only the outcome is stored. Otherwise a deviation is recorded and staff are notified live. A significant deviation also requests a delay re-plan proposal, handled in the re-plan diagram.

Reviewing. Staff browse and filter deviations, review them and enter an override or a correction. A record with clock_skew_suspect set stays untrusted and is excluded from evaluation; otherwise it is trusted. Manual corrections are not marked untrusted in the MVP. There is no automatic clock correction. Staff can review untrusted events and record a resolution note, but the record stays untrusted. A clock-skew event has already changed the operational state; the label only keeps it out of evaluation and training.

Learning. On a schedule, Part 3 takes trusted data only and evaluates outcomes on the mean absolute error and the override rate. It watches the service-time, demand and delay-risk models for drift and applies a forecast bias correction to Part 1's inputs. It trains a candidate on a time-based split and compares it with the approved baseline. A candidate that is not worse on both measures is adopted, with the previous version kept for rollback if a problem appears; otherwise it is rejected and the Port Admin reviews it. Every decision is logged with the model version.

Throughout, no data leaves the port, overrides are a signal to analyse rather than a retraining trigger, and no model ever relaxes a hard safety constraint.

**Step-by-step flow** (each step lists where it goes next; END is a final node)

- **START** start → D0 "Triggering event?"
- **D0** Decision "Triggering event?": "Actual status received" → A1 "Actual status applied - from AD-15"; "Periodic evaluation" → P0 "Select trusted data only"
- **A1** [Port Server] Actual status applied - from AD-15 → A2 "Compare planned and actual using reported_at"
- **P0** [AI Part 3 - Feedback Loop] Select trusted data only → P1 "Evaluate outcomes on MAE and override rate"
- **A2** [Port Server] Compare planned and actual using reported_at → D1 "Over the threshold?"
- **P1** [AI Part 3 - Feedback Loop] Evaluate outcomes on MAE and override rate → P2 "Monitor drift on the service time, demand and delay-risk models"
- **D1** [Port Server] Decision "Over the threshold?": "No" → A3 "Store the actual outcome"; "Yes" → A4 "Record the deviation in the deviation log"
- **P2** [AI Part 3 - Feedback Loop] Monitor drift on the service time, demand and delay-risk models → P3 "Apply forecast bias correction to Part 1 inputs"
- **A3** [Port Server] Store the actual outcome → END
- **A4** [Port Server] Record the deviation in the deviation log → DS "Significant deviation?"
- **P3** [AI Part 3 - Feedback Loop] Apply forecast bias correction to Part 1 inputs → P4 "Build a time-based train and test split"
- **DS** [Port Server] Decision "Significant deviation?": "Yes" → AR "Request a delay re-plan proposal - AD-12"; "No" → A5 "Notify staff via SSE"
- **P4** [AI Part 3 - Feedback Loop] Build a time-based train and test split → P5 "Train a candidate model"
- **AR** [Port Server] Request a delay re-plan proposal - AD-12 → A5 "Notify staff via SSE"
- **A5** [Port Server] Notify staff via SSE → S1 "Browse and filter deviations by vessel, terminal, resource type and date"
- **P5** [AI Part 3 - Feedback Loop] Train a candidate model → P6 "Compare candidate and approved baseline on MAE and override rate, held-out data"
- **S1** [Port Authority Staff] Browse and filter deviations by vessel, terminal, resource type and date → S3 "Review the deviation and enter an override or correction"
- **P6** [AI Part 3 - Feedback Loop] Compare candidate and approved baseline on MAE and override rate, held-out data → D3 "Candidate not worse on both?"
- **S3** [Port Authority Staff] Review the deviation and enter an override or correction → A7 "Record override, correction and observed result"
- **D3** [AI Part 3 - Feedback Loop] Decision "Candidate not worse on both?": "Yes" → P7 "Adopt the candidate and keep the previous version for rollback"; "No" → P8 "Reject the candidate and keep the current model"
- **A7** [Port Server] Record override, correction and observed result → D2 "clock_skew_suspect?"
- **P7** [AI Part 3 - Feedback Loop] Adopt the candidate and keep the previous version for rollback → D4 "Problem after adoption?"
- **P8** [AI Part 3 - Feedback Loop] Reject the candidate and keep the current model → R1 "Review the rejected model candidate"
- **D2** [Port Authority Staff] Decision "clock_skew_suspect?": "Yes" → A8 "Record stays untrusted - excluded from evaluation"; "No" → A9 "Record is trusted"
- **D4** [AI Part 3 - Feedback Loop] Decision "Problem after adoption?": "Yes" → P10 "Roll back to the previous model version"; "No" → P9 "Log evaluation, decision and model version"
- **R1** [Port Admin] Review the rejected model candidate → P9 "Log evaluation, decision and model version"
- **A8** [Port Server] Record stays untrusted - excluded from evaluation → S2 "Review untrusted events and record a resolution note - the record stays untrusted"
- **A9** [Port Server] Record is trusted → END
- **P10** [AI Part 3 - Feedback Loop] Roll back to the previous model version → P9 "Log evaluation, decision and model version"
- **P9** [AI Part 3 - Feedback Loop] Log evaluation, decision and model version → END
- **S2** [Port Authority Staff] Review untrusted events and record a resolution note - the record stays untrusted → END

**Rules stated as notes**

- Thresholds are set per operation type by the Port Admin (attached to D1)
- Human review records a note only; it never makes a record trusted (attached to S2)
- A clock-skew event already updated operational state in AD-15; the untrusted label does not undo that (attached to A8)
- Nothing leaves the port (attached to P1)
- Hard safety constraints are never relaxed by a model (attached to P7)
- Overrides are analysed as a signal, not an automatic retraining trigger (attached to A7)

#### AD-17 — Mobile first launch, login and re-authentication

**Code:** `activity-diagrams-v3/ATLANTECH_Activity_Diagrams.md`, diagram AD-17. **Related:** 3.1, 2.1, 2.2. **Requirements:** FR-5.3, FR-5.4, FR-11.3; NFR-SEC-3, NFR-UX-3.

**Swimlanes:** Mobile User, Mobile App, Port Server.

**Story**

This diagram shows how a field user gets from opening the app to their task list, and how the app behaves when its token runs out. The mobile app is for field users only; staff features are on the web.

First launch. The app calls /system/info on the fixed address app.atlantech.io, which the port's DNS points to its own server. It receives the port's id and name, the license mode, the days left before the token warning and the minimum app version, and shows the port name.

Stored token. With a valid token the user goes straight to the tasks. Without one, the user signs in. If the token expired while the phone was offline, the app keeps working with cached data and keeps the Outbox pending, because a token is never renewed offline; the user signs in when the network is back.

Sign-in. Wrong credentials return 401 and an inactive account returns 403 ACCOUNT_DISABLED; in both cases the Outbox stays unsent. An app below the minimum version gets 426 and must be updated, with the Outbox preserved. Otherwise the server issues a 30-day sliding token named by the device id and registers the device. If must_change_password is set, the user must change the password first.

After sign-in. The token goes into secure storage, assigned tasks are pre-fetched, and any pending Outbox events for this user are sent with their idempotency keys. If the license is read-only, or the token expires in 14 days or less, a banner is shown and create buttons are hidden. If a later request returns 401, for example because the Port Admin revoked the token, sync and protected actions pause until the user signs in again.

**Step-by-step flow** (each step lists where it goes next; END is a final node)

- **START** start → U1 "Open the app"
- **U1** [Mobile User] Open the app → D0 "First launch?"
- **D0** [Mobile App] Decision "First launch?": "Yes" → A1 "Call GET /system/info on the fixed base URL app.atlantech.io"; "No" → D2 "Stored token state?"
- **A1** [Mobile App] Call GET /system/info on the fixed base URL app.atlantech.io → S1 "Return port_public_id, port name, license_mode, token_warning_days_left, min_app_version"
- **D2** [Mobile App] Decision "Stored token state?": "Valid" → D7 "READ_ONLY or token expiry within 14 days?"; "None" → U2 "Enter username and password"; "Expired while offline" → A3 "Keep the Outbox pending - a token is never renewed offline"
- **S1** [Port Server] Return port_public_id, port name, license_mode, token_warning_days_left, min_app_version → A2 "Show the port name and tag logs with port_public_id"
- **D7** [Mobile App] Decision "READ_ONLY or token expiry within 14 days?": "Yes" → A11 "Show a banner and hide create buttons"; "No" → A12 "Show assigned tasks"
- **U2** [Mobile User] Enter username and password → A5 "Call POST /auth/login"
- **A3** [Mobile App] Keep the Outbox pending - a token is never renewed offline → A4 "Work offline with cached data"
- **A2** [Mobile App] Show the port name and tag logs with port_public_id → D2 "Stored token state?"
- **A11** [Mobile App] Show a banner and hide create buttons → A12 "Show assigned tasks"
- **A12** [Mobile App] Show assigned tasks → D8 "A later protected request returns 401?"
- **A5** [Mobile App] Call POST /auth/login → D4 "Credentials?"
- **A4** [Mobile App] Work offline with cached data → D3 "Network back?"
- **D8** [Mobile App] Decision "A later protected request returns 401?": "Yes" → A13 "Pause sync and protected actions"; "No" → END
- **D4** [Port Server] Decision "Credentials?": "Wrong" → S2 "Return 401"; "Account inactive" → S2b "Return 403 ACCOUNT_DISABLED"; "Valid" → D5 "App version at least min_app_version?"
- **D3** [Mobile App] Decision "Network back?": "No" → A4 "Work offline with cached data"; "Yes" → U2 "Enter username and password"
- **A13** [Mobile App] Pause sync and protected actions → U2 "Enter username and password"
- **S2** [Port Server] Return 401 → A6 "Show the login error - the Outbox stays unsent"
- **S2b** [Port Server] Return 403 ACCOUNT_DISABLED → A6 "Show the login error - the Outbox stays unsent"
- **D5** [Port Server] Decision "App version at least min_app_version?": "No" → S3 "Return 426"; "Yes" → S4 "Issue a token named by device id, 30-day sliding"
- **A6** [Mobile App] Show the login error - the Outbox stays unsent → U2 "Enter username and password"
- **S3** [Port Server] Return 426 → A7 "Block sync and show update required - Outbox preserved"
- **S4** [Port Server] Issue a token named by device id, 30-day sliding → S5 "Register or update the device: id, platform, app version, last seen"
- **A7** [Mobile App] Block sync and show update required - Outbox preserved → END
- **S5** [Port Server] Register or update the device: id, platform, app version, last seen → DF "must_change_password set?"
- **DF** [Port Server] Decision "must_change_password set?": "Yes" → UF "Change the password - forced on first login"; "No" → A8 "Store the token in secure storage"
- **UF** [Mobile User] Change the password - forced on first login → A8 "Store the token in secure storage"
- **A8** [Mobile App] Store the token in secure storage → A9 "Pre-fetch assigned tasks to the local cache"
- **A9** [Mobile App] Pre-fetch assigned tasks to the local cache → D6 "Pending Outbox for this user?"
- **D6** [Mobile App] Decision "Pending Outbox for this user?": "Yes" → A10 "Resume queued events with their idempotency keys - AD-15"; "No" → D7 "READ_ONLY or token expiry within 14 days?"
- **A10** [Mobile App] Resume queued events with their idempotency keys - AD-15 → D7 "READ_ONLY or token expiry within 14 days?"

**Rules stated as notes**

- The Outbox is never sent before authentication succeeds (attached to A6)
- A token revoked by the Port Admin also returns 401 and forces a new login (attached to A13)
- The mobile app is for field users only; staff features are web only (attached to U1)

### State machine diagrams of category 3

#### SM-6 — Outbox event (mobile app)

**Code:** `state-diagrams/ATLANTECH_State_Diagrams.md`, diagram SM-6. **Related:** AD-15, 3.1, 3.2. **Requirements:** FR-5.3, FR-5.4; NFR-SYNC-1.

**States:** PENDING, SENDING, DONE, REJECTED.

**Story**

Every change a field user makes on the phone becomes an Outbox event. This machine shows the life of one event on the phone.

PENDING. The user's action (a status update, an acknowledgement or a field record) is written to the Outbox first, with an idempotency key, its type, payload, the time it was recorded and the user. It waits as PENDING.

Sending. A sync cycle starts when connectivity changes or the user syncs manually. The event is sent only if the ping succeeded within the cycle's limit, the session is valid and the event belongs to the signed-in user. If the ping fails, the app retries with a growing delay (2 seconds, doubling, up to 60) and ends the cycle after five tries; the event stays PENDING.

Results. If the server applies the event, or recognises it as a duplicate, it becomes DONE. A validation error, or a creation event while the port is read-only (423), makes it REJECTED with the reason kept in a list the user can read; status updates and acknowledgements are still accepted in read-only mode. If the send fails, times out or the app restarts, the event goes back to PENDING with the same idempotency key and the cycle ends. There is no attempt limit.

End. DONE and REJECTED events are purged from the phone after 30 days. Events that were never sent from a wiped or lost device are lost and must be entered again.

**Transitions** (event [guard] / action)

| From | To | Event [guard] / action |
|---|---|---|
| initial | PENDING | user action (status update, acknowledge, field record) / write to the Outbox first: idempotency_key, type, payload, recorded_at, user_id |
| PENDING | SENDING | sync cycle (connectivity change or manual) [ping OK within the cycle limit and session valid and user_id = current user] / send in order |
| SENDING | DONE | server reply: applied or duplicate |
| SENDING | REJECTED | validation error, or 423 for a creation event / keep the reason in the rejected list |
| SENDING | PENDING | send failed, timeout or app restarted / keep idempotency_key, end the cycle |
| DONE | final | purged after 30 days |
| REJECTED | final | purged after 30 days |

**Internal transitions** (handled without leaving the state)

- PENDING: ping failed / backoff 2 s doubling, max 60 s, after 5 tries end the cycle

**Notes on the diagram**

- On SENDING: READ_ONLY: status updates and acknowledgements are applied; only creation events are rejected. Events have no attempt limit.
- On PENDING: Events not yet sent from a wiped or lost device are lost; the user enters them again.
