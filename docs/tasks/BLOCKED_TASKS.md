# Blocked AI tasks

Setup record (not in the backlog), for whoever plans the next AI-track work. One row per task that cannot start or cannot be closed today, with what unblocks it. "Merge" means a PR of this session must be merged into `develop` first; the branches are listed in [AUTONOMOUS_EXECUTION_PLAN.md](AUTONOMOUS_EXECUTION_PLAN.md) §1. Updated 2026-11-21 (after the first merge round).

| Task | Blocker | Owner of the blocker | Needed deliverable | Partial work possible? | Next action |
|---|---|---|---|---|---|
| AI-055 (close) | AI-045 must exist before AI-055 is `DONE` (user's ruling with AI-051) | AI Team / user | AI-045 merged | Yes: AI-055 is implemented and pushed | Decide the AI-045 path (DECISION_RECOMMENDATIONS R3) |
| AI-045 | Prerequisite AI-043 not done (needs AI-041, AI-042 and real data); flag X | AI Team (decision), domain experts | Either AI-043, or a ruling to build A5 on labelled synthetic series like DEC-34 | Yes, under such a ruling (synthetic, labelled) | User decision R3 |
| AI-073 | DEC-31 (Part 3 scheduling host) is Open | AI Team (owner) | Closed DEC-31 | No: the host decides the design | User decision R2 |
| AI-007 | DEC-07 and DEC-24 are Open | AI Team (owner), Backend | Closed DEC-07 and DEC-24 | No | User decision R4 |
| AI-047, AI-046, AI-048 | AI-007 (above); AI-048 also needs AI-041, AI-045 | AI Team | AI-007 closed | No | After R4 |
| AI-032 (criterion 3) | The backlog asks the worker to set the previous ACTIVE file to REPLACED, but CT-12 step 5 and DEC-08 give `baplie_files.status` to the Backend | Backend Team (CT-12 owner) | Nothing new: the Backend does it on `PARSED` (CT-12 step 5) | Yes: everything else in AI-032 | Recorded in the AI-032 task decision |
| AI-057 | Rationale template texts are not seeded (AI-009 criterion 3, domain review) and the rationale language is open | AI Team, domain reviewer | Approved `rationale_templates` rows | Yes: rendering and factor engine without real texts | Seed the templates (AI-009) |
| AI-058 | AI-056, AI-057; merge gate: CT-10 Proposed change approved (INT-B1) | AI Team; Backend Team | Both tasks merged; CT-10 approved | Yes, up to the merge | INT-B1 |
| AI-060 (handler) | No DB loader for B2's `FilterContext` (constraint types, vessel-type ids, AI-054 inputs) | AI Team | One shared loader (also needed by AI-056/AI-058) | Yes: service merged first | Build the loader with AI-056 |
| AI-071 | AI-074 not merged yet; evaluation definitions per metric (DEC-30 baselines) | User (merge), AI Team | AI-074 merged | No | After AI-074 merges |
| AI-072 | PSI and MAE thresholds come from the register (DEC-30) and no model version rows exist (OD-17); M2/M3/M4 have no champion yet | AI Team (DEC-30), Leads | Thresholds and a model to watch | Yes: PSI/MAE computation on synthetic data | After DEC-30 thresholds |
| AI-070 (registration) | No worker may write `ml_model_versions` (DEC-08) | Backend Team (CT-17 grants) | INT-B6 | Read side done | With AI-104 |
| AI-066 | AI-032, AI-058 (merges and tasks); Backend G-01, G-02, G-04 (INT-B3); dwell and time-limit values (INT-L1, INT-L2) | AI Team, Backend Team, Terminal operations | As listed | Demo yard only (G-03) until G-02 | After AI-058 |
| AI-020, AI-021, AI-022, AI-024, AI-042 | Missing data (flag D): provider selection and access, tidal constants, reference-port master data, historical data | Leads Council, domain experts | The datasets | No real-data work; synthetic fixtures exist (AI-015) | Leads Council |
| AI-100 to AI-106 | Data-gated ML (Phase 2) | Leads Council | Enough trusted history (AI-024) | No | Later phase |
| AI-031 (case 12) | No upper stowage bounds | QA Team / Leads | INT-Q1 | Rest of AI-031 done | INT-Q1 |
