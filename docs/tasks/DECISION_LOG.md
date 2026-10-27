# Decision log

Proposed decisions and proposed changes to existing decisions in `docs/tasks/ATLANTECH_Decisions.md` (`DEC-01`–`DEC-56`). That file stays the authoritative record; official `DEC-` IDs are assigned only when an item is added there.

- Entries are numbered `DL-001`, `DL-002`, … and name the `DEC-` (and any `CT-`) IDs they relate to. Don't assign a new `DEC-` ID here.
- Every entry starts as `PROPOSED`. It becomes `APPROVED` only when the decision's Owner has explicitly approved it, and the entry records who approved it and when.
- Each entry cites the evidence it rests on.

Entry template:

```
### DL-<nnn> · <title>
| Field | Value |
|---|---|
| Status | PROPOSED |
| Related | <task-id>, <DEC-/CT- IDs> |
| Owner | <team> |
| Reviewers | <teams or roles> |
| Proposed by / date | <name>, <YYYY-MM-DD> |
| Evidence | <documents, files or tests> |
| Change | <what is decided or changed> |
| Reason | <why it is needed> |
| Impact | <tasks, tables, teams affected> |
```

## Entries

### DL-001 · AI scope and component inventory (AI-001)
| Field | Value |
|---|---|
| Status | PROPOSED: the supplied record states `Closed`, approved by AI Lead · Team Lead, but its decision date is blank, so the approval date still needs confirmation before this entry's status can change |
| Related | AI-001, AI-010, DEC-21, DEC-25, DEC-29, DEC-31, DEC-55, OD-17, OD-23 |
| Owner | AI Team |
| Reviewers | AI Lead · Team Lead (as named in the supplied record) |
| Proposed by / date | Recorded by mostafa from the AI-001 decision record supplied in the AI-010 session, 2026-10-27 |
| Evidence | Supplied AI-001 record (Status `Closed`, Decided on `____`, Approved by AI Lead · Team Lead). Consistent with `ATLANTECH_AI_ARCHITECTURE.md` §4.3, §8.14, §9.5, §14, §15 and with `ATLANTECH_Decisions.md` DEC-55 (Closed) and the recommendations of DEC-25 and DEC-29. Recorder's note: the record's statement that AI Architecture v3 does not list B8 refers to the v3 source document; this repository's reference `ATLANTECH_AI_ARCHITECTURE.md` already lists B8 (§8.14, §14) |
| Change | Component inventory, as supplied. **MVP:** B1 BAPLIE parser (EDI Parser worker) · A1 data ingestion · A2 astronomical tide · A3 surge residual · A4 threshold feasibility · A5 UKC with Barrass squat · A7 demand aggregation (Phase 1) · B2 constraint filter · B3 service time (Phase 1 formula) · B4 delay risk (Phase 1 rule, or NULL until DEC-21 is approved) · B5 CP-SAT solver with FIFO fallback · B6 template rationale · B7 re-planning · B8 yard placement · C1 outcome evaluation · C2 drift monitor. **Data-gated:** M2 service time LightGBM (B3 Phase 2) · M3 demand LightGBM (A7 Phase 2) · M4 delay-risk LightGBM (B4) · C3 guarded retraining · C4 forecast bias correction. **Future work / out of scope:** A6 uncertainty margin (MVP uses zero margin and `confidence` = NULL, DEC-25) · TIMING terminal recommendations and NCT storage allocation (DEC-55) · Vision module · any cross-port or SaaS model sharing. **Notes:** B8 is a new identifier for Part 2 yard placement (UML assigns it to Part 2; AI Architecture v3 does not list it); its method is set by DEC-29. A data-gated model replaces its Phase 1 path only after passing its baseline comparison. The Part 3 scheduling host is set by DEC-31 |
| Reason | AI-001 requires a decision-log entry listing every component with status MVP, DATA-GATED or OUT-OF-SCOPE; no such entry existed in this repository |
| Impact | AI-010 module skeleton (which workers and components exist). Open record gaps: (1) decision date blank; (2) AI-001's acceptance asks for the yard component's label *and owner*: the label B8 is recorded, a named owner is not; (3) DEC-21, DEC-25, DEC-29 and DEC-31 are still `Open` in `ATLANTECH_Decisions.md`; (4) `Master_Context.md` §6.4 calls C3/C4 "future work", while this record and Architecture §9.5 call them data-gated |

### DL-002 · AI code repository location and module structure (AI-010)
| Field | Value |
|---|---|
| Status | PROPOSED |
| Related | AI-010, AI-001 (DL-001), AI-011–AI-016, DEC-10, DEC-31, CT-08, CT-13–CT-16, D18 |
| Owner | AI Team |
| Reviewers | AI Lead · Team Lead; organisation owner if a repository-level approval is required (backlog AI-010 note) |
| Proposed by / date | mostafa, 2026-10-27 |
| Evidence | `Master_Context.md` §5.4 lists `project-backend`, `project-frontend` and `project-mobile` but no AI repository; `Atlantech-project/project-ai` exists and is this repository's `origin`; `ATLANTECH_AI_ARCHITECTURE.md` I-5 and §4.3 (four separate workers: three queues, `queue:edi`, `queue:part1`, `queue:part2`, and Part 3 periodic with no user queue); backlog AI-010 expected outputs (modules `common, edi, part1, part2, part3`, marked PROPOSED) |
| Change | (1) AI code lives in `Atlantech-project/project-ai`, with `feature/<task>` branches from `develop` merged by PR. (2) Top-level modules: `common/` (shared by all workers), `edi/` (EDI Parser, B1, `queue:edi`), `part1/` (A1–A7, `queue:part1` plus internal scheduler), `part2/` (B2–B8, `queue:part2`), `part3/` (C1–C4, periodic). Each part is one deployable worker (D18). (3) Not decided here: Python tooling, version, dependency management and environment (OQ-1); schema location (OQ-2, `PortHub/contracts/` proposed in `ATLANTECH_Contracts.md`); FastAPI module (DEC-10); Part 3 scheduling host (DEC-31); test, tool and model-artefact locations (OQ-7) |
| Reason | The documented repositories don't include the Python workers (backlog AI-010) |
| Impact | AI-011–AI-016 place their code under these modules. `Master_Context.md` §5.4 would need its owner to add `project-ai`. Backend and QA reference `project-ai` commits (CT-26) |
