# Blocked AI tasks

Setup record (not in the backlog), for whoever plans the next AI-track work. One row per task that cannot start or cannot be closed today, with what unblocks it. "Merge" means a PR of this session must be merged into `develop` first; the branches are listed in [AUTONOMOUS_EXECUTION_PLAN.md](AUTONOMOUS_EXECUTION_PLAN.md) §1. Updated 2026-11-22 (after the round-3 merges, PRs #48 to #54).

| Task | Blocker | Owner of the blocker | Needed deliverable | Partial work possible? | Next action |
|---|---|---|---|---|---|
| AI-055 (close) | AI-045 must exist before AI-055 is `DONE` (user's ruling with AI-051) | AI Team / user | AI-045 merged | Yes: AI-055 is implemented and pushed | Decide the AI-045 path (DECISION_RECOMMENDATIONS R3) |
| AI-045 | Prerequisite AI-043 not done (needs AI-041, AI-042 and real data); flag X | AI Team (decision), domain experts | Either AI-043, or a ruling to build A5 on labelled synthetic series like DEC-34 | Yes, under such a ruling (synthetic, labelled) | User decision R3 |
| AI-073 | DEC-31 (Part 3 scheduling host) is Open | AI Team (owner) | Closed DEC-31 | No: the host decides the design | User decision R2 |
| AI-007 | DEC-07 and DEC-24 are Open | AI Team (owner), Backend | Closed DEC-07 and DEC-24 | No | User decision R4 |
| AI-047, AI-046, AI-048 | AI-007 (above); AI-048 also needs AI-041, AI-045 | AI Team | AI-007 closed | No | After R4 |
| AI-032 (criterion 3) | The backlog asks the worker to set the previous ACTIVE file to REPLACED, but CT-12 step 5 and DEC-08 give `baplie_files.status` to the Backend | User (R6), Backend Team (CT-12 owner) | R6 accepted, and the Backend test of CT-12 step 5 (INT-B10) | Done: everything else merged (PR #51) | User decision R6; INT-B10 |
| AI-057 | Rationale template texts are not seeded (AI-009 criterion 3, domain review) and the rationale language is open | AI Team, domain reviewer | Approved `rationale_templates` rows | Yes: rendering and factor engine without real texts | Seed the templates (AI-009) |
| AI-058 | AI-057 (AI-056 merged, PR #49); merge gate: CT-10 Proposed change approved (INT-B1) | AI Team; Backend Team | AI-057 done; CT-10 approved | No: the rationale fields come from AI-057 | After INT-Q4 and AI-057 |
| AI-071 | Metric definitions: `OVERRIDE_RATE` and `WAIT_TIME` are named but not defined in any source here; `WINDOW_ACCURACY` is DEC-30 TR-11 (DEFERRED, OD-16); `MAE` needs a model version (none exists, OD-17). AI-074 merged (PR #50) | AI Team (TR-11 owner), user | Written definitions (numerator, denominator, period, which rows) | Only the trusted-data reads, already in AI-074 | User decision R9 |
| AI-070 (registration) | No worker may write `ml_model_versions` (DEC-08) | Backend Team (CT-17 grants) | INT-B6 | Read side done | With AI-104 |
| AI-066 | AI-058 (AI-032 merged, PR #51; AI-065 mapping Proposed); Backend G-01, G-02, G-04 (INT-B3); dwell and time-limit values (INT-L1, INT-L2) | AI Team, Backend Team, Terminal operations | As listed | Demo yard only (G-03) until G-02 | After AI-058 |
| AI-020, AI-021, AI-022, AI-024, AI-042 | Missing data (flag D): provider selection and access, tidal constants, reference-port master data, historical data | Leads Council, domain experts | The datasets | No real-data work; synthetic fixtures exist (AI-015) | Leads Council |
| AI-100 to AI-106 | Data-gated ML (Phase 2) | Leads Council | Enough trusted history (AI-024) | No | Later phase |
| AI-031 (case 12) | No upper stowage bounds | QA Team / Leads | INT-Q1 | Rest of AI-031 done | INT-Q1 |
| AI-065 (close) | Its constraint-to-table mapping is a Proposed AI task decision (merged, PR #48) | AI Team (owner) | Approval of the AI-065 entry | Done | Confirm with R7 |
| AI-033 | `DEFERRED (DEC-17)`: NFR-PERF-2 removed from the MVP (Leads Council, 2026-10-27); DEC-30 TR-08 out of MVP scope; CT-12 has no size classes | Leads Council | A Leads ruling that brings NFR-PERF-2 back, with size classes | No | None in the MVP |
| AI-072 (production use) | DEC-30 TR-01 / TR-02 values and a model version to watch (OD-17); task DONE (PR #52) | AI Team (DEC-30), Leads | Seeded thresholds through CT-18; a champion version | Done | R8 |
