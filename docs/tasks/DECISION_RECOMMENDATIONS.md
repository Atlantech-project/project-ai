# Decisions waiting for the user

Setup record (not in the backlog), written for the user as AI Team owner. Each item is a recommendation, not a decision: the canonical entries in `docs/ref/ATLANTECH_Decisions.md` stay `Open` or `Proposed` until approved there. IDs `R-x` are local labels only. Updated 2026-11-21.

| ID | Question | Recommendation | Status |
|---|---|---|---|
| R1 | Accept the seven AI task decisions written this session? | Yes, as written. The one with business weight is AI-055 item (1): `RESOURCE_COST` = tugs assigned ÷ `N_cap` | RECOMMENDED · REQUIRES OWNER CONFIRMATION |
| R2 | DEC-31: where does Part 3 scheduling run? | Option 1, a scheduler inside the Part 3 worker | RECOMMENDED |
| R3 | How does AI-045 (A5 UKC with squat) get built before AI-043 exists? | Build it on labelled synthetic series, as DEC-34 did for A4 | RECOMMENDED · needs a new decision text |
| R4 | Close DEC-07 (and DEC-24) so AI-007 can close? | DEC-07: Option 1, the recommendation the entry already marks "agreed" | RECOMMENDED |
| R5 | DEC-22: financial impact in ranking | Keep it Open; AI-055 ranks by DEC-23 only | No action |

## R1 · The AI task decisions of 2026-11-21

- **Entries:** AI-065, AI-055, AI-031, AI-060, AI-025, AI-070 and AI-092 in "AI task decisions", each `Proposed`, each on its own branch.
- **Recommendation:** accept them all. Every item is reversible and stays inside what Closed decisions allow.
- **Watch:** AI-055 item (1). The alternative, berth occupancy time, would be constant for every berth today, because B3's Phase 1 service time depends on the terminal (AI-052).
- **Impact:** AI-056, AI-057, AI-058, AI-066, AI-067 and AI-074 build on these rulings.
- **Risk:** low. A change later is a code change behind one function per item.
- **Owner:** AI Team. After you approve, each entry gets its Status, Decision and approver filled in on `develop`.

## R2 · DEC-31, Part 3 scheduling host (unblocks AI-073)

- **Options:** (1) a scheduler inside the Part 3 worker; (2) the Laravel scheduler enqueues, which needs a new queue.
- **Recommendation:** Option 1, the one the entry already recommends.
- **Why:**
  - There is no `queue:part3`, so Option 1 changes no contract.
  - AI-073 asks for "cadence from `port_setting`" and "overlapping runs prevented". A worker can read the cadence and hold a lock itself.
- **Alternative:** Option 2 would need a CT-08 queue addition and Backend work.
- **Risk:** the Part 3 worker must run on one host only, or take a DB lock. AI-073 would test that.
- **Owner:** AI Team.

## R3 · AI-045 on synthetic data (unblocks closing AI-055)

- **Context:** AI-045 depends on AI-043, which needs real provider and tide data (AI-020, AI-021, AI-042). The user ruled that AI-055 is not `DONE` before AI-045 exists.
- **Recommendation:** build and test A5 (UKC with Barrass squat) on labelled synthetic sea-level and depth series behind the interface the real pipeline will use. Keep DEC-34's gates:
  - real-data re-test before AI-048 is `DONE`;
  - hard limits never loosened;
  - synthetic data always labelled.
- **Alternative:** wait for real data. That keeps AI-055, and every Part 2 demo, open for several sprints.
- **Risk:** squat coefficients are domain values (flag X). They need a source, never a guess. If none exists, AI-045 stays blocked even on synthetic data.
- **How to record it:** a new decision needs an official ID from the team leads. Until then, write it as a `Proposed` AI-045 task decision.
- **Owner:** AI Team, with the domain experts for the coefficients.

## R4 · DEC-07 and DEC-24 (unblock AI-007, then AI-047 and AI-048)

- **DEC-07:** close it with Option 1, "a proposal with no windows, linked from the run". The entry already marks that option "(agreed)"; only its Status was never set. Backend coordination: a schema note change only.
- **DEC-24:** Part 1 horizon, time step, minimum window and slot. Its values come from the thresholds register (DEC-30). I have no source for them, so I have no value to recommend.
- **Owner:** AI Team, with the Backend Team for the schema note.
