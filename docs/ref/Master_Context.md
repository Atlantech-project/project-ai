# ATLANTECH — Master Project Context (Final)

## 0. How to Use This Document

This document is the project's stable knowledge: identity, problem, scope, architecture, AI design, data model and rules. It is written to be read together with:

| Document | Holds |
|---|---|
| `UML_Context.md` | Every diagram in words: actors, status vocabularies, global rules (write chain, read-only allowlist, tokens, plan limits, Outbox, notifications), answer codes, per-diagram flows, requirement groups and NFR figures |
| `ATLANTECH_FRD_v3` | Numbered functional requirements by feature area with priority (P1, P2, FW) and MVP flag; future-work list |
| `PortSync.sql` | Port operational database, 90 tables |
| `SaaS.sql` | Central SaaS database, 8 tables |
| Class diagrams | 6 views, 98 tables (8 SaaS + 90 Port) |

Nothing in this document repeats those files. Actors, statuses, flows, rules and answer codes are in `UML_Context.md`; requirement IDs are in the FRD; columns are in the SQL.

**Precedence.** Behaviour and vocabulary: the UML. Physical structure: the SQL. The SQL and class-diagram names are the vocabulary. The UML uses them (decided 20 October 2026). Older documents and the proposal never override either.

**Terminology.** Use ATLANTECH, Container Terminal (CT), Non-Container Terminal (NCT). Historical names PortMind AI and PortSync AI are history only (the SQL file keeps the name `PortSync.sql`).

---

## 1. Identity and Brand

- **Name:** ATLANTECH. **Positioning:** Intelligent Port Operations.
- **Title:** An AI-Driven Predictive Decision Support System for Port-Wide Coordination of Shared Marine and Terminal Resources.
- **Institution:** Mansoura University, Faculty of Computers and Information. Graduation Project 2026.
- **Brand:** Deep Navy `#083A4F`, Muted Gold `#A58D66`, Light Teal `#C0D5D6`, Mid Teal `#407E8C`, Off-White `#E5E1DD`. Montserrat (primary), Inter (secondary). Clean geometry, wave motif, open icons with rounded joins (about 2.4 pt stroke). Use the identity, not the logo; never recreate or insert the logo in diagrams or documents.

---

## 2. Vision and Problem

ATLANTECH is a **port-wide advisory, recommendation and coordination layer**. It builds a unified operational view, weighs competing demand for shared resources, produces coordinated recommendations, supports human decisions and takes in actual operational feedback.

> **ATLANTECH recommends and coordinates. Existing terminal and port systems execute.**

It sits above existing execution systems (TOS such as Navis N4, PMIS such as SPS-Harbor) and never replaces them. Human approval gates every plan.

**Problem.** A port is a cluster of independent parties (port authority, pilotage, tugs, container terminals, non-container terminals) that plan their own resources but depend on the same finite shared ones: berths, navigation channel, tugs, pilots. Each can execute correctly while the port suffers conflicts and cascading delay. Three root causes:

1. **Isolated planning.** Each party optimises its own local state.
2. **No visibility of the future.** Upcoming arrivals, cargo needs and cross-terminal demand are not anticipated, so conflicts appear only when they happen.
3. **Environment-blind berthing.** Tide, surge, wind, waves and visibility change safe under-keel clearance and manoeuvring limits hour by hour, yet berthing windows are rarely planned against forecasts.

Consequences: re-handling, vessel waiting, missed tidal windows, higher cost, cascading delay, eroded safety margins.

**Core principle.** Do not optimise each vessel in isolation when shared resources are involved. Overlapping requests are evaluated together against the current port state.

**Gap in existing systems.** SPS-Harbor (Damietta Port Authority) selects resources by rules with no multi-variable optimisation or cross-terminal reconciliation. Navis N4 (DCHC) executes inside one terminal. Rotterdam Digital Twin predicts berthing windows for one port. PSA Tuas plans within one operator's terminals. Portchain's Berth Optimisation Engine schedules berth windows per terminal with no tugs, pilots or cross-terminal view. None reconciles competing demand across independently operated terminals or reasons about upcoming demand across domains. ATLANTECH fills that gap and leaves execution systems untouched.

---

## 3. Scope

**In scope**
- Coordinated berth, pilot and tug allocation across terminals.
- Environmental feasibility windows (wind, visibility, waves, tide and surge) and an entry-time recommendation.
- Container-yard placement and timing recommendations for the Container Terminal.
- BAPLIE (EDI) ingestion of vessel and container data.
- Human review and approval before any plan is dispatched.
- Status tracking, deviation logging, notifications, audit.
- NCT master data (storage, warehouses, tanks, handling equipment, safety constraints). NCT recommendations come after the Container Terminal.

**Out of scope**
- Vessel-to-terminal assignment (fixed by commercial contracts).
- Customs systems (approval is recorded by hand only).
- ERP and administration (HR, procurement, port-service billing).
- Direct control of equipment or vehicles; mooring and bunkering execution.
- AIS and telemetry; fuel suppliers.
- Sharing operational data or AI models between ports (federated learning rejected).
- Vision module.
- Shipping Agent is not a system actor; River Berth is not in the model.

**Implementation scope.** The full AI architecture (Parts 1 to 3) is built for real, starting with the Container Terminal. The phased MVP, priorities and future work are in `ATLANTECH_FRD_v3` (baseline MVP-M).

**Terminal model.** Two categories, CT and NCT. Gas and petrochemical operations (tanks, pipelines, pumps) belong to NCT. The terminal model is generic and configurable.

**Assumption.** Ports onboard accurate, current infrastructure and resource data.

---

## 4. Reference Port, Evaluation and Business Model

**Reference port.** Damietta: 8 terminals, 36 berths, about 26 vessels per day (Port Authority daily bulletin). It is a case study; the product is port-agnostic and scales by configuration from 1 terminal and 5 berths to 10 terminals and 50 berths with no code change.

**Significance (proposal figures).** Transport and storage are about 5% of Egypt's GDP and 2.9M jobs (8.7% of the workforce); $9.4B foreign-currency receipts in 2024/2025; 17,288 vessel calls in 2025 (+6.6%); 11.1M TEU (+24.3%); 6.7M transit TEU (+36%).

**Evaluation.** The prototype is compared with a manual-planning baseline for the reference port on six indicators: conflicts detected and resolved; resource utilisation (berths, tugs, pilots, equipment); avoidable idle time; estimated operational cost; feasibility and quality of recommendations (executable and rationale-backed); downstream effect on re-handling where demonstrated. The key evaluated target is whether coordination lets the port handle more than about 26 vessels per day; it is assessed experimentally, not guaranteed.

**Business model (B2G2B).** Buyers are port authorities and ministries of transport (ministry tenders); secondary buyers are CT and NCT operators. Revenue: a one-time deployment fee; an annual Master Port Authority licence (3 to 5 year contracts, marine allocation); an annual modular terminal add-on licence (CT yard, NCT equipment); annual Enterprise Support and SLA (24/7). No monthly subscriptions, matching annual public budgets. This is why licences and billing are annual. Payment happens outside the system and is only recorded. Partners: port authorities and ministries, national single window (Nafeza, aligned with IMO FAL; integration not in this build), legacy TOS and PMIS vendors through adapters only.

---

## 5. System Architecture

(The technology table and layer list are in `UML_Context.md`; this section gives decisions and structure.)

### 5.1 Deployment
Every port gets the **same system** as a **dedicated installation on its own server in its own LAN**. Ports differ by configuration, terminals, resources, users and data, not by code. One build serves all ports; the fixed hostname `app.atlantech.io` resolves to the port server by split DNS.

### 5.2 Central SaaS
A registry only: platform admins, plans, governorates, port registry, annual licences, signed licence tokens, billing records, platform audit. It never stores or reads operational data, makes no runtime calls into ports, and **no AI model, weight or update ever crosses the Port to SaaS boundary**. The port starts every contact (daily licence check-in). `server_endpoint` is management metadata (for example a VPN address), not an app URL.

### 5.3 Port system structure (HLD v2.0)
```
Office users -> Web Dashboard (Vue.js)   --HTTPS, SSE-->  \
Field crews  -> Mobile App (Flutter)     --REST, WS---->   NGINX (load balancer)
                                                              |
                       Laravel modular monolith: App Instance 1, App Instance 2, Notifications (SSE, WebSocket)
                       Functional areas: Auth & RBAC, Marine, Terminals, Berthing Requests,
                                         Plans & Dispatch, Tracking & Deviations, Audit
                                                              |
                  BAPLIE file volume (dedicated)     Redis: cache + queue:edi, queue:part1, queue:part2
                                                              |
        Python satellites: EDI Parser | Part 1 Predictive & Env. | Part 2 AI Engine | Part 3 Feedback Loop
                                                              |
                         MySQL operational database: Primary (writes) -> Replica (reads)
External (adapters): Weather and sea level (every 6 h + on demand), Request Sources, Terminal Operating Systems
Isolated, no runtime calls, no data or AI models cross:  Central SaaS (Admin -> Dashboard -> API -> Registry DB)
```
- The Laravel codebase is one logical modular monolith (domain modules, one-way dependencies, terminal modules never import each other). It can run as several instances; "modular monolith" describes logical structure.
- Python satellites exist only because their runtime differs: EDI Parser, Part 1, Part 2, Part 3. Satellites **read port state and write results directly to MySQL**.
- **External systems.** Weather and sea level are pulled from providers by Part 1. The Request Sources and TOS adapter points in the HLD are **integration points reserved for later**. In the current build, berthing requests are entered by Port Authority Staff and recommendations reach the TOS by manual hand-off.

### 5.4 Protocols and infrastructure decisions
| Area | Decision |
|---|---|
| Web real-time | SSE from the realtime server |
| Mobile | WebSocket event, then REST fetch of the full payload. No push service (FCM/APNs) |
| Laravel to Python | Async Redis queue, **one queue per worker**: `queue:part1`, `queue:part2`, `queue:edi`. A long Part 2 solve never delays a Part 1 request someone waits for |
| Results to the dashboard | Python writes MySQL; Laravel pushes over the existing SSE. No other pub/sub channel |
| Periodic environmental pulls | A scheduler inside Part 1 (no Laravel scheduler, no Laravel call) |
| Files | BAPLIE files on a dedicated volume, separate from the code |
| TLS | NGINX, TLS 1.3 only; port certificate signed by the offline ATLANTECH Root CA |
| Mobile network | Managed phones (MDM) with per-app always-on VPN; MDM and VPN belong to the port IT team |
| Support access | No standing inbound path; time-boxed support VPN under an approved ticket |

**Production versus prototype.** Production: 2 Laravel instances behind NGINX, MySQL primary plus replica, SaaS and port on separate environments. Prototype: 1 instance, 1 MySQL primary, NGINX kept, SaaS and port may share one VPS. Same logical architecture.

**Data isolation inside a port.** Competing terminals are separated by terminal-level row security: a terminal user cannot see another terminal's cargo, stowage, yard plans or costs (403). Port Authority roles keep the shared port-wide context.

**Integration principle.** External systems connect through adapters; the core domain never depends on an external system's internal model.

**Repositories.** `Atlantech-project` GitHub organisation: `project-backend`, `project-frontend`, `project-mobile`; one `feature/<task>` branch per task from `develop`, merged by pull request.

---

## 6. AI Architecture (AI Architecture v3)

All AI learning stays on the port's own server. Runtime path for any AI request:

```
Staff action (dashboard) -> Laravel -> Redis queue (queue:part1 or queue:part2) -> Python worker (one per part)
-> result written to MySQL -> SSE to the dashboard.
Python scheduler (Part 1) does periodic pulls with no Laravel call. Part 3 reads and writes MySQL locally.
```

### 6.1 End-to-end AI flow
```
Berthing Request (Preliminary Approval) -> Customs Approval (new status, entered by staff)
   -> Part 1: constraints + entry-time proposal -> HUMAN GATE 1: staff confirms the entry window
      (ENTRY_WINDOW_CONFIRMED, becomes Part 2 input)
   -> Part 2: ranked options for berth, tug, pilot (+ yard) -> HUMAN GATE 2: staff confirms the plan
      or overrides a component (reason in recommendation_override) -> Operational Plan (PLAN_CONFIRMED)
   -> Execution by existing systems and people -> actual outcomes
      (actual_status_update, deviation_log, recommendation_override)
   -> Part 3: evaluation, drift, retraining, bias correction -> new model version / corrected inputs
      back to Part 2 / Part 1. Delay or cancel triggers re-planning in Part 2.
```

### 6.2 Part 1 — Predictive and Environmental
Produces constraints and an entry-time proposal. **Never allocates resources.** Trigger: Customs Approval enqueues a job on `queue:part1`.

| ID | Component | Method | Type |
|---|---|---|---|
| A1 | Data ingestion | Weather, wave and current every 6 h; on-demand weather and surge at Customs Approval; astronomical tide daily over a multi-day horizon; surge input follows the weather schedule; external marine data via adapter; writes `environment_forecast_point` and run tables | ETL |
| A2 | Astronomical tide | Harmonic model from published constants (pyTMD), computed in-house | Physics |
| A3 | Surge residual | `Surge(t) = SeaLevel(t) - Tide(t)`: a definition, not a prediction | Formula |
| A4 | Threshold feasibility | Wind, gust, visibility, wave, tide and surge against operating limits; exact, auditable rules | Rules |
| A5 | Under-keel clearance | UKC with Barrass squat, naval-architecture formulas | Physics |
| A6 | Uncertainty margin | Statistical margin or provider ensemble spread applied to limits | Statistics |
| A7 | Demand and peak forecast (M3) | Phase 1: aggregate open berthing requests plus history. Phase 2: LightGBM regressor | ML, Phase 2 |

All four environmental factors (wind, visibility, waves, tide/surge) are in scope because the product is port-agnostic and tidal strength differs by port. Stored data is usable only if measured within 48 hours and covering the request horizon. Hard safety limits (wind, wave, visibility, UKC) are fixed and never loosened automatically.

**Output:** `feasible_windows` (start, end, confidence); `blocked_periods` (start, end, limiting factor); `peak_congestion_score`; `data_versions` (weather and tide runs). Persisted to MySQL and pushed by SSE. If no window is feasible the outcome says so with the limiting factor; if data is missing the outcome is data-unavailable and staff may enter data manually.

### 6.3 Part 2 — AI Engine
The **sole authority** for shared-resource allocation (berth, tug, pilot) and for yard and storage recommendations. Trigger: window confirmed enqueues a job on `queue:part2`.

**Inputs:** confirmed window and Part 1 constraints; BAPLIE-derived vessel and cargo data; live (actual) berth, tug and pilot state; Marine Safety Officer constraints.

| ID | Component | Method | Type |
|---|---|---|---|
| B1 | BAPLIE parser (EDI Parser satellite) | Deterministic EDIFACT parser, UN/EDIFACT D.17A and SMDG 2019; vessel, containers, stowage; all-or-nothing commit | Deterministic |
| B2 | Constraint filter | LOA, draft, terminal type, safety-officer constraints, Part 1 windows | Rules |
| B3 | Service time (M2) | Phase 1: `Moves / ProductivityRate + FixedOverhead`. Phase 2: LightGBM quantile regression (P50, P90) | ML, Phase 2 |
| B4 | Delay risk (M4) | LightGBM classifier trained on deviation and override history. Before enough data exists, a rule-based score is used | ML |
| B5 | CP-SAT solver | Google OR-Tools, Berth Allocation Problem with tugs and pilots, port-wide joint solve | Optimisation |
| B6 | Rationale | Fixed, versioned templates tied to the binding constraints and objective terms; never an LLM | Template |
| B7 | Re-planning | Re-solve on a rolling horizon with updated inputs | Optimisation |

**Why a solver.** A solver guarantees a feasible solution when one exists and, at Damietta's scale (about 26 vessels a day, 36 berths), solves quickly without the data volume a learned allocator needs. ML is used only for service time, delay risk and demand.

**Solver outcomes.** Solved: ranked options. Technical failure (error or timeout): a FIFO plan by arrival order that passes the same hard filter, labelled as FIFO. Infeasible: final `NO_FEASIBLE_PLAN` with the binding constraints, no FIFO plan.

**Ranking and contention.** Options are ranked by time urgency, then by financial impact when time priority is close or tied. Competing vessels for the same pilot or tug in an overlapping window are resolved by the joint solve under the objective terms (`objective_term`). Part 1 constraints are hard; the solver never relaxes them.

**Output:** ranked options, each with `rank`, `berth_id`, start, end, `tugs`, `pilot_id`, service time P50 and P90, `delay_risk`, `rationale_text`. The final decision stays with Port Authority Staff.

### 6.4 Part 3 — Feedback Loop (local to this port)
| ID | Component | Method |
|---|---|---|
| C1 | Outcome evaluation | MAE, override rate, wait time, Part 1 window accuracy |
| C2 | Drift monitor | PSI and rolling MAE on M2, M3, M4 |
| C3 | Retraining pipeline | Time-based split; Champion versus Challenger; guarded automatic |
| C4 | Forecast bias correction | Regression or quantile mapping on the forecast-versus-actual gap; corrected inputs return to Part 1 |

**Guarded automatic retraining.** Retraining recurs periodically with no human approval. The Challenger replaces the Champion **only if not worse** on MAE and override rate on held-out, time-based data; otherwise the Champion keeps running and a flag is logged. Overrides are analysed as a signal, never a silent retraining trigger. Part 3 uses trusted data only (trusted = `clock_skew_suspect` = 0); the previous model is kept for rollback. **Hard safety limits never change automatically.** No model, weight or update ever leaves the server.

**Data volume.** About 26 vessels a day is about 9,500 a year, estimated enough for LightGBM after several months of real operation. Until then the formula and rule paths run. In the MVP, Part 3 delivers evaluation and drift monitoring; automatic retraining and bias correction are future work (see FRD).

### 6.5 Build versus buy
Build in-house what depends on private operational data (M2 to M4, BAPLIE parsing, the CP-SAT model). Consume externally what is a solved physical problem (raw weather and sea-level data from a primary and a secondary provider). Tide is the exception: built in-house.

### 6.6 AI decision record
| # | Decision |
|---|---|
| D1 | Customs approval is entered manually by Port Authority Staff |
| D2 | Part 1 outputs constraints and windows only; Part 2 is the only allocator |
| D3 | The staff-confirmed entry window becomes a Part 2 input |
| D4 | Customs approval is a regular berthing-request status |
| D5 | Part 1 covers wind, visibility, waves and tide/surge |
| D6 | Weather every 6 h plus on demand |
| D7 | Tide daily; surge follows the weather schedule |
| D8 | No cross-port model or update sharing |
| D9 | Laravel to Python over Redis queue, async |
| D10 | Tide computed in-house |
| D11 | Rationale from fixed templates, never an LLM |
| D12 | Guarded automatic retraining, hard safety limits never auto-changed |
| D13 | Part 1 constraints are hard; no feasible solution ends as `NO_FEASIBLE_PLAN` |
| D14 | Ranking by time urgency then financial impact; contention resolved by the joint solve |
| D15 | Solver failure: FIFO fallback on technical failure only; infeasible is final |
| D16 | Periodic scheduler lives in Part 1 |
| D17 | Everything is implemented for real, Container Terminal first |
| D18 | One Redis queue per part; results by MySQL plus SSE |

---

## 7. Data Model Map

Two separate databases; neither holds the other's data. Columns are in the SQL files.

### 7.1 Central SaaS (`SaaS.sql`, 8 tables)
`saas_admin`, `license_plan`, `governorate`, `platform_port_registry`, `license`, `license_token`, `billing_transaction`, `platform_audit_log`.

- Egypt-only; `governorate` holds the seaport governorates.
- `platform_port_registry.public_id` is a stable UUID shared with the port and carried in tokens; only a hash of the API credential is stored; ports are never deleted (`OFFBOARDED`).
- `license` snapshots plan limits, annual price and currency at issue. At most one `ACTIVE` licence per port (generated column plus unique index).
- `license_token` stores signed claims and the SHA-256 of the token; the signing key is not in the DB. Delivery `PULL` or `MANUAL`.
- `billing_transaction`: annual period per licence, one live transaction (PENDING, FAILED, PAID) per licence and period.
- `platform_audit_log`: append-only; actor `ADMIN` or `SYSTEM`.

### 7.2 Port operational database (`PortSync.sql`, 90 tables)
| Domain | Tables |
|---|---|
| Configuration and licence | `port_profile` (singleton), `port_setting`, `navigation_channel`, `channel_waypoint`, `license_state` |
| Organisation and people | `organization_unit`, `user`, `user_role_assignment`, `user_device`, `pilot_profile`, `pilot_rank_limit`, `pilot_schedule`, `port_shift`, `tug_master_profile`, `tug_master_schedule` |
| Terminals, berths, fleet | `terminal`, `berth`, `berth_terminal`, `tugboat` |
| Vessel and cargo reference | `vessel`, `vessel_type`, `container`, `container_size_type`, `cargo_type`, `imdg_class`, `terminal_cargo_type` |
| NCT storage | `storage_facility`, `storage_type`, `storage_facility_cargo_compatibility`, `storage_movement`, `tank_detail`, `warehouse_detail` |
| CT yard | `yard_zone`, `yard_zone_type`, `yard_block`, `yard_slot`, `reefer_zone_detail`, `oog_zone_detail`, `dg_zone_allowed_class` |
| Equipment | `equipment`, `equipment_category`, `equipment_capability`, `capability_type`, `equipment_cargo_compatibility` |
| Safety and productivity | `safety_constraint`, `constraint_type`, `terminal_productivity_profile` |
| Requests and manifest | `berthing_request`, `berthing_request_cargo`, `berthing_request_status_history`, `external_system`, `baplie_file`, `baplie_parse_issue`, `container_manifest_entry` |
| Environment and Part 1 | `environment_forecast_point`, `forecast_run`, `tide_constituent`, `tide_constituent_set`, `tide_prediction_run`, `tide_prediction_point`, `blocked_period`, `demand_forecast_slot`, `entry_window_proposal`, `feasible_window`, `part1_run` |
| Model registry | `ml_model`, `ml_model_version` |
| Part 2 | `rationale_template`, `recommendation`, `recommendation_option`, `recommendation_option_tug`, `recommendation_review`, `solver_run`, `solver_run_model_version`, `objective_term`, `recommendation_override`, `recommendation_rationale_factor`, `storage_allocation_item`, `terminal_recommendation`, `yard_placement_item` |
| Plan and execution | `operational_plan`, `plan_component`, `actual_status_update`, `deviation_log`, `status_type` |
| Part 3 | `drift_measurement`, `evaluation_metric`, `retraining_run` |
| Cross-cutting | `audit_log`, `notification_log` |

### 7.3 Design decisions in the SQL
- **Roles** are a fixed ENUM on `user_role_assignment` (`PORT_GM`, `PORT_STAFF`, `MARINE_SAFETY_OFFICER`, `PILOTAGE_MANAGER`, `PILOTAGE_OFFICER`, `MARINE_PILOT`, `TUG_MANAGER`, `TUG_OFFICER`, `TUG_MASTER`, `TERMINAL_ADMIN`, `TERMINAL_OFFICER`, `TERMINAL_SUPERVISOR`), held in an `organization_unit` (Harbour Authority, Marine Services, or one terminal; a TERMINAL unit is created with each terminal). Usernames are lowercase, at least 3 characters. The UML's Port Admin is the `PORT_GM` role; CT and NCT admin, planner and supervisor roles map to the `TERMINAL_*` roles within a CT or NCT unit.
- **Shared berths.** `berth_terminal` has one row per terminal allowed to use the berth; every berth has at least one row.
- **Vessel versus call.** `vessel` is identity; block coefficient, GT and DWT are per call on `berthing_request`. `container` is identity; weight, stowage and ports are per call in `container_manifest_entry`.
- **Berthing request** keeps its current `status` and a history row in the same transaction; the CUSTOMS_APPROVED history row records who and when.
- **BAPLIE.** One active file per request; replacing a revision is one transaction; a mistaken upload is withdrawn; parse issues are stored per file for diagnostics.
- **Environment.** `environment_forecast_point` keeps raw provider values; unit conversion and derived values such as surge are computed on the AI side. Forecast location is the port profile's coordinates. Tide is stored as constituents, runs and hourly prediction points.
- **Part 1 output.** `entry_window_proposal` with `feasible_window` and `blocked_period` rows; its data versions are the run foreign keys.
- **Safety constraints.** Overlap of the same type and scope is rejected by the backend; when several scopes apply, the strictest value wins.
- **Part 2.** `solver_run` records trigger (`NEW_REQUEST`, `REPLAN`, `RESOURCE_CHANGE`, `MANUAL`) and status; the selected option is the one `operational_plan` references; the number of tugs per option comes from the AI formula; rationale factors that drove a solve are stored per recommendation.
- **Reservation.** `plan_component` has one row per dispatched unit (one per tug) with `reservation_state` `RESERVED`, `RELEASED` or `CONSUMED`. Berth and tug occupancy is derived from RESERVED rows overlapping a window. Component types: `BERTH`, `PILOT`, `TUG`, `TERMINAL_OPS`. A new field status is an INSERT into `status_type`, not an ALTER.
- **Execution feedback.** `actual_status_update` stores device time (`reported_at`), send time (`client_sent_at`), server receipt time, `clock_skew_suspect` and `sync_source` (`MOBILE`, `TABLET`, `WEB`, `EXTERNAL`). `deviation_log` types: `DELAY`, `RESOURCE_CHANGED`, `STATE_MISMATCH`.
- **Part 3.** `retraining_run` keeps Champion versus Challenger with decision `PROMOTED`, `KEPT_CHAMPION` or `FAILED`; a champion version has a deployment time; the model registry keys are `M2_SERVICE_TIME`, `M3_DEMAND_FORECAST`, `M4_DELAY_RISK`, `FORECAST_BIAS_CORRECTION`.
- **Terminal recommendation** is the common output contract and is visible to its terminal only. Accepting a storage allocation adds its quantity to the facility's reserved capacity.
- **Yard.** Zone capacity and occupancy are derived from `yard_slot`; a blocked slot holds no container.
- **Audit.** `audit_log` is append-only (the application user has INSERT and SELECT only).
- **Licence in the port.** `license_state` is the local copy of the SaaS licence with mode SETUP, FULL or READ_ONLY and the last received port and licence statuses; the public key and API credential live in configuration.

### 7.4 Vocabulary
**Vocabulary.** The UML, the SQL and the class diagrams use the same values: request 11 values (SUBMITTED … CANCELLED); BAPLIE file STAGED, ACTIVE, REPLACED, WITHDRAWN; parse PENDING, PARSED, FAILED, QUARANTINED; entry-window proposal PROPOSED, CONFIRMED, REPLACED, REJECTED; recommendation PENDING_REVIEW, MODIFIED_BY_STAFF, CONFIRMED, REJECTED, INVALIDATED, REPLACED; operational plan CONFIRMED, CANCELLED, COMPLETED; licence mode SETUP, FULL, READ_ONLY.

---

## 8. Team

| Area | Member | Role |
|---|---|---|
| AI | Mostafa Mohamed Ragab Rashwan | AI Engineer and Team Lead (Section 8) |
| AI | Menna-Allah Gamal Mohamed Nasr | AI Engineer (Section 8) |
| Backend | Marwan Nabil Mohamed Motawea | Backend Engineer (Section 8) |
| Backend | Menna-Allah Mohamed Magdy Abd El-Kader | Backend Engineer (Section 8) |
| Backend | Mariem Mohamed Mansour Abd El-Gelel | Backend Engineer (Section 8) |
| Frontend | Mostafa Safy Mostafa Soliman | Frontend Engineer (Section 8) |
| Frontend | Mostafa El-Hassanen El-Hassanen El-Sharawey | Frontend Engineer (Section 8) |
| Mobile | Farouk Ahmed Farouk El-Balkiny | Mobile App Developer (Section 5 to 8, transferred) |
| UI/UX | Menna-Allah Maged Nabil Mohamed | UI/UX Designer (Section 8) |
| BA / QA | Mahmoud Wageh Mohamed El-Sayed | Business Analyst and QA Tester (Section 7) |

---

## 9. Rules for AI Sessions

1. ATLANTECH advises and coordinates; it never executes. Human approval gates every plan.
2. Every port is a dedicated deployment. The Central SaaS is licence and registry only. No AI artifact or operational data crosses the Port to SaaS boundary.
3. Part 1 gives windows and constraints; only Part 2 allocates; Part 3 learns locally. Keep Parts 1, 2, 3 and the EDI Parser separate.
4. Laravel to Python uses one Redis queue per worker; results return through MySQL and SSE; mobile uses WebSocket plus REST; there is no push service.
5. Rationale is template-based, tide is computed in-house, BAPLIE parsing is deterministic.
6. Hard safety limits are never relaxed automatically.
7. Licences and billing are annual.
8. Container Terminal first; NCT is master data only for now.
9. Out of the project: Shipping Agent actor, River Berth, fuel suppliers, AIS, Vision module, federated learning.
10. Use current terminology and never the logo.
11. Take actors, statuses, rules, answer codes and flows from `UML_Context.md`; requirements and priorities from `ATLANTECH_FRD_v3`; tables and columns from the SQL. Use the SQL and class-diagram names (section 7.4).
12. Do not invent business rules or technical decisions. Keep logical architecture separate from deployment topology, and Central SaaS data separate from port operational data.
