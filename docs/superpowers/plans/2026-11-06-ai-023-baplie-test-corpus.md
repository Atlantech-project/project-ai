# AI-023 BAPLIE Test Corpus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **ATLANTECH override:** no step commits, stages or pushes. Publishing happens only through `/atlantech-review-and-publish AI-023`.

**Goal:** Build a labelled, synthetic BAPLIE test corpus in `tests/edi_corpus/` (one `.edi` plus one `.expected.json` per case), with an index and a pytest integrity check, so AI-030 has parser inputs with expected outcomes.

**Architecture:** Static data files (not generated at test time) plus a test that checks the corpus against itself: pairs exist, the oracle schema is valid, the segment counts and container counts are right, and the check digits match what each oracle claims. No parser is written (that is AI-030). The test uses a small segment splitter and an ISO 6346 function that live in `tests/support/edi_corpus.py`.

**Tech Stack:** Python (pytest, per `pyproject.toml`, `testpaths = ["tests"]`), UN/EDIFACT text files.

**Spec:** no design document. The sources are the AI-023 backlog entry (`docs/tasks/ATLANTECH_AI_TASKS.md` §5), CT-12 v1.1 and CT-24 (PortHub `contracts/ATLANTECH_Contracts.md`), DEC-17, DEC-28 item 7, `PortHub/contracts/ai/baplie-corpus/` (README and the six starter files) and the user's decisions of 2026-11-06 listed below.

## Decisions taken by the user (2026-11-06)

1. CT-12, CT-24 and the DB schema are the reference. QA's `contracts/qa/baplie-corpus/` and `QA-AI2-baplie.md` are not adopted; every conflict goes to `qa-followup.md`.
2. LOC qualifiers follow CT-24 and DEC-28: `LOC+11` = load port, `LOC+12` = discharge port, with a TODO pointing at AI-030.
3. The corpus is the 18 CT-24 cases with CT-24's codes, plus new cases for OOG, missing full/empty and an unknown segment (NFR-INT-1).
4. A wrong check digit is a `WARNING` (CT-12). `REJECTED` is `DONE · REJECTED`; `FAILED` + `REJECTED` never appears.
5. Columns: only the current schema (`reefer_set_temperature`, `imdg_class`); no new columns.
6. TC-BAP-005 and TC-BAP-006 are out of scope.
7. Size classes (the AI-023 acceptance criterion "Size classes match the thresholds register"): **scope exception approved**. Basis: DEC-17 (NFR-PERF-2 removed), CT-24 README §3, thresholds register TR-08 (OUT OF MVP SCOPE, DEC-30 still Open).
8. **UPDATE 2026-11-07: decided, D.17A is NOT supported.** Case `25-unsupported-version-d17a` (REJECTED) was added; the marked parts below are now resolved. Original wording follows. **PENDING (D.17A):** the user will answer the BAPLIE version question (D.17A / SMDG 2019 versus CT-12's D.95B and D.13B) separately. Nothing below may depend on it. Every part waiting for that answer is marked **[PENDING D.17A]**.

## Global Constraints

- Supported versions in this corpus: `UNH` identifiers `BAPLIE:D:95B:UN:SMDG22` and `BAPLIE:D:13B:UN:SMDG31` only (CT-12 v1.1). Unsupported example: `BAPLIE:1:5:UN:SMDG15`.
- Oracle fields exactly as in the CT-24 starters: `file`, `expected_outcome`, `expected_parse_status`, `vessel_imo`, `containers`, `issues[]` (`severity`, `code`, `segment_ref`, `message`), `is_synthetic`. No other field is added.
- Outcome mapping: `PARSED`↔`PARSED`, `QUARANTINED`↔`QUARANTINED`, `REJECTED`↔`FAILED` (as `parse_status`; the run is `DONE · REJECTED`).
- Severities (CT-12): ERROR → `QUARANTINED`; WARNING → still `PARSED`. Wrong check digit, missing `full_empty`, missing `port_of_discharge`, vessel-name difference are WARNINGs.
- Every file is synthetic and labelled so: `is_synthetic: true` and a README provenance statement. No real shipping data. Every case assumes the request vessel IMO is `9811000`.
- All container numbers in files are valid ISO 6346 unless the case injects a mismatch. (Finding: the CT-24 starter `01-valid-221.edi` uses `MSCU1234565`, whose check digit should be 6; `04-imo-mismatch.edi` uses `MSCU7654321`, which should end in 9. Both go to `qa-followup.md`; this corpus uses valid numbers.)
- DB columns referenced anywhere (README, followup): `reefer_set_temperature`, `imdg_class` on `container_manifest_entries`/`containers` only, as in `docs/ref/db/schema.sql`.
- No change to `docs/ref/`, `PortHub/`, CLAUDE.md, the backlog or the thresholds register.

## Review Focus

- A file whose `UNT` segment count or `containers` value in the oracle is wrong would silently mislead AI-030. Tested by the integrity checks (Task 1) on every case.
- A "valid" file with a bad check digit would produce an unplanned WARNING. Tested: every container number is checked against its oracle (Task 1).
- Case 18 (corrupted syntax) must not look like a valid file with one segment dropped. Tested: the splitter must report unterminated or missing-`UNZ` structure for exactly the cases whose oracle is `CORRUPTED_SYNTAX` or `NOT_EDIFACT` (Task 1).
- An oracle added without its `.edi`, or the reverse. Tested: pair check, plus `INDEX.md` lists exactly the files present (Task 1).
- Unknown-segment case must stay `PARSED` and still count its valid containers (NFR-INT-1). Tested: oracle assertion in Task 2.

---

## File Structure

| Path | New/existing | Responsibility |
|---|---|---|
| `tests/edi_corpus/*.edi`, `*.expected.json` | new | The cases (2 files per case) |
| `tests/edi_corpus/INDEX.md` | new | Corpus index: case, version, what it injects, outcome, source; the AI-023 coverage map |
| `tests/edi_corpus/README.md` | new | Provenance (synthetic), assumptions (request IMO `9811000`), LOC TODO for AI-030, **[PENDING D.17A]** note, scope exception for size classes |
| `docs/followups/qa-followup.md` | new | Conflicts with `QA-AI2-baplie.md` and the QA corpus only (Task 5). **Plan change at approval (2026-11-06):** moved out of `tests/edi_corpus/` and split in two |
| `docs/followups/contracts-followup.md` | new | **Added at approval:** issues in the contracts themselves: wrong check digits in the CT-24 starters, `queue:c06` in `qa/ai-testing-guide.md` (four places: lines 49, 62, 79, 246), and the Proposed change to CT-24 for the three new codes with their severities. Not applied to any canonical file |
| `.gitattributes` | existing, one line added | **Added at the user's instruction (2026-11-07):** `*.edi -text`, so EDI files stay byte-exact on every machine |
| `tests/edi_corpus/25-unsupported-version-d17a.*` | new | **Added after the D.17A decision (2026-11-07):** well-formed D.17A file, REJECTED with `UNSUPPORTED_BAPLIE_VERSION` on `UNH`; the case list above has 24 rows because it predates this case |
| `tests/support/edi_corpus.py` | new | `iso6346_check_digit`, `split_segments`, `load_cases` |
| `tests/unit/edi_corpus/__init__.py`, `test_corpus_integrity.py` | new | The integrity test |
| `docs/tasks/status/AI-023.md`, `docs/tasks/WORK_STATUS.md` | new / existing (one row added) | Records |

## Case list

Cases 01–18 are CT-24's, with CT-24's names, versions, outcomes and codes. Containers are 1–3 per file unless noted. `segment_ref` is the offending segment text without the terminator, e.g. `EQD+CN+MSCU1234567`.

| # | Name | UNH | Outcome | Issues (severity · code) |
|---|---|---|---|---|
| 01 | `01-valid-221` | D.95B | PARSED | none |
| 02 | `02-valid-311` | D.13B | PARSED | none |
| 03 | `03-valid-with-warnings` | D.95B | PARSED | WARNING · `CHECK_DIGIT_MISMATCH` |
| 04 | `04-imo-mismatch` | D.95B | QUARANTINED | ERROR · `IMO_MISMATCH` (TDT IMO ≠ `9811000`) |
| 05 | `05-duplicate-container` | D.95B | QUARANTINED | ERROR · `DUPLICATE_CONTAINER_NUMBER` |
| 06 | `06-unknown-iso-size-type` | D.95B | QUARANTINED | ERROR · `UNKNOWN_SIZE_TYPE` (`45X9`) |
| 07 | `07-unknown-imdg-class` | D.95B | QUARANTINED | ERROR · `UNKNOWN_IMDG_CLASS` |
| 08 | `08-malformed-weight` | D.95B | QUARANTINED | ERROR · `MALFORMED_WEIGHT` (negative or non-numeric) |
| 09 | `09-malformed-unlocode` | D.95B | QUARANTINED | ERROR · `MALFORMED_UNLOCODE` |
| 10 | `10-temperature-out-of-range` | D.95B | QUARANTINED | ERROR · `TEMPERATURE_OUT_OF_RANGE` (outside −40…40) |
| 11 | `11-reefer-missing-temp` | D.95B | QUARANTINED | ERROR · `REEFER_MISSING_TEMPERATURE` |
| 12 | `12-invalid-stowage-coordinate` | D.95B | QUARANTINED | ERROR · `INVALID_STOWAGE_COORDINATE` |
| 13 | `13-missing-mandatory-segment` | D.95B | QUARANTINED | ERROR · `MISSING_MANDATORY_SEGMENT` (missing `LOC` or `MEA`) |
| 14 | `14-multiple-errors-composite` | D.95B | QUARANTINED | ERRORs: `IMO_MISMATCH`, `UNKNOWN_SIZE_TYPE`, `MALFORMED_WEIGHT` |
| 15 | `15-non-edifact-payload` | plain text/XML | REJECTED | ERROR · `NOT_EDIFACT` |
| 16 | `16-unsupported-version` | `BAPLIE:1:5:UN:SMDG15` | REJECTED | ERROR · `UNSUPPORTED_BAPLIE_VERSION`, `segment_ref` `UNH`, message per CT-12 |
| 17 | `17-wrong-message-type` | `COPRAR` | REJECTED | ERROR · `WRONG_MESSAGE_TYPE` |
| 18 | `18-corrupted-syntax` | D.95B | REJECTED | ERROR · `CORRUPTED_SYNTAX` (unterminated segment, no `UNZ`) |
| 19 | `19-valid-dangerous-goods` | D.95B | PARSED | none (valid `DGS`, IMDG class known) |
| 20 | `20-valid-reefer` | D.95B | PARSED | none (`TMP` −18 °C, reefer size code) |
| 21 | `21-valid-oog` | D.95B | PARSED | none (`DIM` segments for out-of-gauge; qualifiers **TODO: confirm in AI-030 against the SMDG guide**) |
| 22 | `22-missing-full-empty` | D.95B | PARSED | WARNING · `MISSING_FULL_EMPTY` (CT-12 WARNING; written NULL) |
| 23 | `23-unknown-segment` | D.95B | PARSED | WARNING · `UNKNOWN_SEGMENT`; the valid containers still count (NFR-INT-1) |
| 24 | `24-unreadable-file` | none (0 bytes / binary) | REJECTED | ERROR · `UNREADABLE_FILE` |

Cases 19–24 are new. The codes `MISSING_FULL_EMPTY`, `UNKNOWN_SEGMENT` and `UNREADABLE_FILE` are not in CT-24 or CT-12 (they name the behaviour CT-12 and NFR-INT-1 describe). They are **proposals**, listed in `qa-followup.md` and `README.md` for QA and AI-031 to confirm. Cases 19–21 are valid-cargo coverage the AI-023 outputs list names ("OOG, DG"); the "valid small/medium/large" outputs reduce to case 01 only (scope exception).

**[PENDING D.17A]:** no case 25+ for D.17A / SMDG 2019 is written. If the answer is "support D.17A", a valid D.17A case is added; if "not supported", a REJECTED D.17A case is added. Neither is built now.

Segment details every `.edi` must follow: `UNA:+.? '` first, the CT-24 starter shape (`UNB`, `UNH`, `BGM`, `DTM+137`, `TDT` with the vessel IMO in `…+++9811000::11:MSC ALEXANDRIA'`, then per container `LOC+147` stowage, `MEA+WT++KGM:<n>`, `EQD+CN+<number>+<size>+++5`, `LOC+11` load, `LOC+12` discharge, `UNT` with the real segment count, `UNZ`). Segment qualifiers other than `LOC+11/12` are carried from the starters and are unverified against the SMDG guides.

---

### Task 1: Support helpers and integrity test (failing first)

**Files:**
- Create: `tests/support/edi_corpus.py`, `tests/unit/edi_corpus/__init__.py`, `tests/unit/edi_corpus/test_corpus_integrity.py`

**Interfaces:**
- Produces:
  - `iso6346_check_digit(container_number: str) -> int` — check digit of the first 10 characters.
  - `split_segments(text: str) -> list[str]` — splits on unreleased `'`, drops the `UNA` line, strips CR/LF; raises `ValueError` when the last segment has no terminator.
  - `CorpusCase` (frozen dataclass: `name: str`, `edi_path: Path`, `oracle: dict`) and `load_cases(root: Path = CORPUS_ROOT) -> list[CorpusCase]`; `CORPUS_ROOT = Path(__file__).parents[1] / "edi_corpus"`.

- [ ] **Step 1: Write the test file.** Tests (each parametrised over `load_cases()` unless noted):
  - `test_iso6346_known_values`: `iso6346_check_digit("MSKU1234565") == 5`, `("MSCU1234567") == 6`, `("CMAU3456787") == 7`, `("MSCU1234566") == 6`.
  - `test_every_edi_has_an_oracle_and_the_reverse`: set of `.edi` stems equals set of `.expected.json` stems.
  - `test_oracle_schema`: exactly the keys listed in Global Constraints; `expected_outcome` in `PARSED/QUARANTINED/REJECTED`; mapping to `expected_parse_status` as in Global Constraints; each issue has `severity`, `code`, `segment_ref`, `message`; `is_synthetic is True`; `file` equals `<name>.edi`.
  - `test_severity_matches_outcome`: `PARSED` has no ERROR issue; `QUARANTINED` has at least one ERROR; `REJECTED` has `containers == 0` or issues only on envelope-level segments.
  - `test_parsed_and_quarantined_files_are_well_formed`: for outcomes `PARSED`/`QUARANTINED`: `split_segments` succeeds; `UNT+<n>` equals the segment count from `UNH` to `UNT` inclusive; ends with `UNZ`; the number of `EQD+CN+` segments equals `oracle["containers"]`; every `LOC+11`/`LOC+12` is followed by a `:139:6` qualifier shape.
  - `test_unsupported_unh_only_in_rejected_cases`: `UNH` identifier in `{BAPLIE:D:95B:UN:SMDG22, BAPLIE:D:13B:UN:SMDG31}` for all `PARSED`/`QUARANTINED` cases.
  - `test_check_digits_match_oracle`: the container numbers whose digit is wrong equal exactly the `segment_ref`s of `CHECK_DIGIT_MISMATCH` issues.
  - `test_rejected_cases_are_not_valid_edifact`: for `CORRUPTED_SYNTAX`, `split_segments` raises; for `NOT_EDIFACT` and `UNREADABLE_FILE`, the text does not start with `UNA`/`UNB`; for `UNSUPPORTED_BAPLIE_VERSION` and `WRONG_MESSAGE_TYPE`, it is well formed but the `UNH` identifier is not supported.
  - `test_ct24_cases_present`: names `01`…`18` from CT-24 (list in the Case list table) all exist, plus `19`…`24`.
  - `test_no_size_class_files`: no case name contains `small`, `medium` or `large`.
  - `test_index_lists_exactly_the_cases`: every case name appears in `INDEX.md` and no other `NN-` name does.
- [ ] **Step 2:** Run `uv run pytest tests/unit/edi_corpus -v`. Expected: FAIL (helpers, files and index missing).
- [ ] **Step 3:** Implement the three helpers in `tests/support/edi_corpus.py` (ISO 6346: letter values skip multiples of 11, weights 2^position, sum mod 11 mod 10). Run `uv run pytest tests/unit/edi_corpus -v -k iso6346`. Expected: PASS for that test only.

### Task 2: PARSED cases (01, 02, 03, 19–23)

**Files:** Create `tests/edi_corpus/<name>.edi` and `<name>.expected.json` for the eight names above.

**Interfaces:** Consumes `load_cases` from Task 1. Produces the files the Task 1 test checks.

- [ ] **Step 1:** Write the `.edi` and oracle for each case per the Case list table. Case 03 uses `MSCU1234567` (digit should be 6) with `segment_ref` `EQD+CN+MSCU1234567`. Case 23 includes one segment tag that is syntactically valid but not in the BAPLIE segment set (e.g. `XYZ+1+UNKNOWN'`), and 2 containers, `containers: 2`. Case 22 omits the full/empty element on the `EQD`. Containers use valid ISO 6346 numbers.
- [ ] **Step 2:** Run `uv run pytest tests/unit/edi_corpus -v`. Expected: the pair, schema, UNT/count and check-digit tests pass for these eight; other cases still missing.

### Task 3: QUARANTINED cases (04–14)

**Files:** Create the eleven pairs.

- [ ] **Step 1:** Write each pair per the Case list table. Case 04's TDT IMO is `9123456` (the starter's); `message` text as in the CT-24 starter: "Vessel IMO in BAPLIE file (9123456) does not match berthing request vessel IMO (9811000)". Case 14 combines IMO mismatch, size `45X9` and weight `-5` with three `issues`; `containers` is the number parsed.
- [ ] **Step 2:** Run the integrity test. Expected: PASS for these eleven.

### Task 4: REJECTED cases (15–18, 24)

**Files:** Create the five pairs. `15` is plain text; `17` has `UNH+1+COPRAR:D:95B:UN:SMDG22'`; `18` has an unterminated segment and no `UNZ`; `24` is a 0-byte `.edi` file.

- [ ] **Step 1:** Write the pairs. Oracle `containers` is `0`; `vessel_imo` follows the starter 16 pattern (`"9811000"`) where the file names a vessel, otherwise `null`.
- [ ] **Step 2:** Run the integrity test. Expected: PASS, including `test_rejected_cases_are_not_valid_edifact`.

### Task 5: Index, README and QA follow-up

**Files:** Create `tests/edi_corpus/INDEX.md`, `README.md`, `qa-followup.md`.

- [ ] **Step 1: `INDEX.md`:** one row per case (name, version, injected characteristic, outcome, issues) plus a table mapping each AI-023 "Expected outputs" item to a case number: valid small → 01 (medium/large: scope exception), IMO mismatch → 04, invalid segments → 13/18, unknown segments → 23, missing full/empty → 22, reefer without temperature → 11, OOG → 21, DG → 19, bad check digit → 03, unreadable file → 24.
- [ ] **Step 2: `README.md`:** states the corpus is synthetic; the request IMO `9811000` assumption; the LOC qualifiers (`LOC+11` load, `LOC+12` discharge) as CT-24/DEC-28 shows them with `TODO(AI-030): confirm against the SMDG BAPLIE implementation guides 2.2.1 and 3.1.1`, same TODO for the `DGS`, `TMP` and `DIM` qualifiers; the size-class scope exception (basis in Decisions section above); the **[PENDING D.17A]** note; the three proposed codes.
- [ ] **Step 3: `qa-followup.md`,** for the QA team, one numbered item each with evidence and the plan's resolution:
  1. SHA-256 in TC-BAP-001/005 (`203313e8…4199e`) ≠ the file's actual hash (`f87e111d43f253a8fc79c9d17db246a4a9a12c50dfe3800ec039830b5378926a`).
  2. `05_duplicate_payload_sample.edi` is byte-identical to `01_…` (it is the duplicate-upload fixture; ok as a Backend test, not a parser case).
  3. `qa/baplie-corpus/` has no `.expected.json` (CT-24 requires a pair per case).
  4. Case names differ from CT-24 (`01_valid_standard_discharge` vs `01-valid-221`); QA-AI2 has 6 test cases vs CT-24's 18.
  5. Issue codes differ (`MISSING_ISO_TYPE`, `INVALID_CHECK_DIGIT`, `MISSING_WEIGHT`, `BAPLIE_SYNTAX_ERROR` vs CT-24's `UNKNOWN_SIZE_TYPE`, `CHECK_DIGIT_MISMATCH`, `MALFORMED_WEIGHT`, `CORRUPTED_SYNTAX`).
  6. TC-BAP-003 expects `status=FAILED` + `outcome=REJECTED`; CT-12 has `DONE · REJECTED` and `chk_bpr_outcome` forbids an outcome unless `status = DONE`; `error_category=INVALID_ENVELOPE` is for technical failure.
  7. TC-BAP-002 expects columns that do not exist (`set_temperature`, `temperature_unit`, `ventilation`, `un_number`, `flashpoint`, `packing_group`, `proper_shipping_name`); schema has `reefer_set_temperature` and `imdg_class`; `is_reefer` is a generated column on the size-type table, not a container column.
  8. TC-BAP-004 treats a wrong check digit as ERROR; CT-12 says WARNING. Also "missing ISO type" and "missing weight" are not in CT-12's ERROR list.
  9. LOC qualifiers: QA files use `LOC+9` load / `LOC+11` discharge; CT-24/DEC-28 starters use `LOC+11` / `LOC+12`; unconfirmed (AI-030).
  10. C-06 (checked against the whole of CT-14 and `c06-completion.schema.json`): the queue is `queue:ai-results`, not `queue:c06`; `status` is `DONE` or `FAILED` only; BAPLIE outcomes are `PARSED`/`QUARANTINED`/`REJECTED`. `SUCCESS` appears only in `forecast_runs.status`; `PARTIAL_SUCCESS` and `error_code` appear nowhere in CT-14. `qa/ai-testing-guide.md` lines 49, 62 and 79 also say `queue:c06`.
  11. CT-24 starters: `01-valid-221.edi` uses `MSCU1234565` (should end in 6) and `04-imo-mismatch.edi` uses `MSCU7654321` (should end in 9), so "0 warnings" is wrong for 01; the 04 oracle gives `vessel_imo` `9123456` (the file's IMO) while the others give the request's.
  12. CT-24 in the contracts file still says "every size class"; CT-24 README §3 and DEC-17 say none.
  13. TC-BAP-005 and TC-BAP-006 are Backend/API tests, not parser cases (informational).
  14. New proposed codes `MISSING_FULL_EMPTY`, `UNKNOWN_SEGMENT`, `UNREADABLE_FILE`, to confirm.
  15. **[PENDING D.17A]** the QA files declare `BAPLIE:D:17A:UN:SMDG20`, which CT-12 v1.1 rejects. Text to be added once the user answers; **do not send the file to QA before this item is filled.**
- [ ] **Step 4:** Run the whole new test: `uv run pytest tests/unit/edi_corpus -v`. Expected: all pass, `test_ct24_cases_present` and `test_index_lists_exactly_the_cases` included.

### Task 6: Verification and records

**Files:** Create `docs/tasks/status/AI-023.md`; modify `docs/tasks/WORK_STATUS.md` (one new row).

- [ ] **Step 1:** Run, from the repo root, and record the actual output: `uv run pytest -v` (full suite), `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`, `git diff --check`, and `git status --short` (only the paths in File Structure appear).
- [ ] **Step 2:** Write the status record in the template of the task workflow: Status `IN PROGRESS` → `IN REVIEW` when Step 1 is clean; the plan path; `approved: yes` with the date and the user's wording once given; the scope exception (criterion 2, approved 2026-11-06); open items (D.17A, QA follow-ups, proposed codes, DEC-30 still Open); and the actual validation results. Add the AI-023 row to `WORK_STATUS.md`.
- [ ] **Step 3:** Stop. Direct the user to `/atlantech-review-and-publish AI-023`. No stage, commit or push.

---

## Dependencies

| Item | Status | Effect |
|---|---|---|
| Prerequisites of AI-023 | none | none |
| AI-008 / DEC-30 thresholds register | IN REVIEW / Open | no size values; TR-08 is OUT OF MVP SCOPE; scope exception approved |
| DEC-17 and CT-12 v1.1 | Closed / Approved | supported versions, outcomes, severities |
| CT-24 | owned by QA, reviewer AI | AI-023 corpus is a local AI-side copy and does not edit PortHub's `contracts/ai/baplie-corpus/`. Whether it later replaces or syncs with QA's copy is the user's call (PortHub wins on shared items per the sync policy) |
| D.17A decision | **pending the user** | Only the items marked [PENDING D.17A] |
| AI-030 | not started | consumes this corpus; owns the segment-qualifier TODOs |

## Contract / decision changes

None written. No `Proposed change` rows. Existing IDs touched read-only: DEC-17, DEC-28 (item 7), DEC-30/TR-08, CT-12, CT-14, CT-24. Everything for QA goes in `qa-followup.md`, not in the canonical files.

## Acceptance criteria mapped

| Criterion (quoted) | Verification |
|---|---|
| "Each case in the list has at least one file and an expected-result file" | `test_every_edi_has_an_oracle_and_the_reverse`, `test_ct24_cases_present`, the coverage map in `INDEX.md` |
| "Size classes match the thresholds register" | Not met as written. Scope exception approved by the user on 2026-11-06 (register TR-08 has no value; DEC-17); recorded in the status record, `README.md` and `INDEX.md`; `test_no_size_class_files` |

## Risks

- The segment qualifiers other than `LOC+11/12` are from the starters, not the SMDG guides, which are not in the workspace; AI-030 may need to correct files (TODOs recorded).
- Three issue codes are proposals. A different final name means renaming files in AI-030/AI-031.
- Two parallel corpora (this one and PortHub's `contracts/ai/baplie-corpus/`) can drift. The follow-up file reduces that; the sync decision is the user's.
- A synthetic corpus can pass a parser that fails on real files. Real files need confidentiality clearance (backlog note) and are not included.
