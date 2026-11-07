# AI-023 follow-up: issues in the contracts

From: AI Team (task AI-023) · 2026-11-06
Scope: problems found in contract and test-guide files, not in the QA test cases (those are in `qa-followup.md`).
Nothing here edits `docs/ref/ATLANTECH_Contracts.md` or anything under PortHub. CT-24 is owned by the QA Team (reviewer: AI Team), and PortHub is where it is maintained.

**Re-check 2026-11-07 (PortHub `main` at `3f21022`):** CT-12 is still Approved v1.1 with no Proposed change row and no D.17A (consistent with the decision that D.17A is not supported); CT-14 and CT-24 are unchanged; `contracts/ai/baplie-corpus/` has not changed since `ce01d00`.

| Item | Status 2026-11-07 |
| --- | --- |
| 1. Wrong check digits in the CT-24 starters | NOT RESOLVED |
| 2. `queue:c06` in `qa/ai-testing-guide.md` | NOT RESOLVED (still in four places: lines 49, 62, 79, 246) |
| 3. Proposed change to CT-24 (three new codes) | NOT RESOLVED. It is the AI Team's proposal and has not been submitted to PortHub; there is no Proposed row in CT-24 |
| 4. CT-24 "every size class" | NOT RESOLVED |
| 5. `.gitattributes` for `*.edi` in PortHub (new) | NOT RESOLVED. PortHub has no `.gitattributes` at all |

Note for item 3: `UNSUPPORTED_BAPLIE_VERSION` is already a CT-24 code (case 16); the new case 25 reuses it, so it adds no new code to the proposal.

## 1. Wrong check digits in the CT-24 starter files

Location: `contracts/ai/baplie-corpus/` (PortHub).

| File | Container | Check digit in file | Correct (ISO 6346) |
| --- | --- | --- | --- |
| `01-valid-221.edi` | `MSCU1234565` | 5 | 6 |
| `04-imo-mismatch.edi` | `MSCU7654321` | 1 | 9 |

Effect: `01-valid-221.expected.json` says "valid, 0 issues", but a parser applying CT-12 will raise a WARNING `CHECK_DIGIT_MISMATCH` for it, so the case does not produce a clean PARSED result. The CT-24 example `MSCU1234567` (digit 6, so a real mismatch) is consistent; the starters are not.
Suggested fix: use `MSCU1234566` in 01 and `MSCU7654329` in 04. The AI corpus uses valid numbers throughout (except case 03, on purpose).

## 2. `queue:c06` in `contracts/qa/ai-testing-guide.md`

The queue name in CT-14 is `queue:ai-results` (CT-14 delivery section, and `c06-completion.schema.json`). The guide says `queue:c06` in **four** places, not three: lines 49, 62, 79 and 246. All four should read `queue:ai-results`.

## 3. Proposed change to CT-24: three new issue codes

Row to add to the CT-24 entry (not applied; it stays proposed until the Owner and Reviewers approve):

| Proposed change | 2026-11-06 · AI-023 · add three issue codes to the CT-24 oracle vocabulary: `MISSING_FULL_EMPTY` (WARNING), `UNKNOWN_SEGMENT` (WARNING), `UNREADABLE_FILE` (ERROR, outcome `REJECTED`, `parse_status` `FAILED`) · Reason: CT-24's 18 cases do not cover three behaviours that CT-12 and the requirements describe, so AI-023 added provisional cases 22 to 24 with these codes · Evidence: CT-12 (WARNING issues: "missing `full_empty` (written NULL)"; unreadable file → `FAILED` with no staged data, UML 2.7), NFR-INT-1 (unknown segments give warnings, valid slots still load), `tests/edi_corpus/` cases 22, 23, 24 · Impact: AI-030 and AI-031 (code names), QA corpus and oracles, no schema or table change · Awaiting: QA Team (Owner), AI Team (Reviewer) |
| --- | --- |

| Code | Severity | Outcome | Basis | Used in |
| --- | --- | --- | --- | --- |
| `MISSING_FULL_EMPTY` | WARNING | PARSED (field written NULL) | CT-12 WARNING list | `22-missing-full-empty` |
| `UNKNOWN_SEGMENT` | WARNING | PARSED (valid containers still load) | NFR-INT-1 | `23-unknown-segment` |
| `UNREADABLE_FILE` | ERROR | REJECTED (`parse_status` FAILED, no staged data) | UML 2.7 "file unreadable" | `24-unreadable-file` |

Until approved the codes are marked **(proposed)** in `tests/edi_corpus/INDEX.md`.

## 4. CT-24 and "every size class"

The CT-24 entry in `ATLANTECH_Contracts.md` still says the corpus must cover "every size class". The CT-24 README (section 3), DEC-17 and CT-12 v1.0 say there are no size classes in the MVP. The AI corpus follows the README. Suggest the entry's sentence is reworded. (Also noted in AI-008.)

## 5. PortHub needs a `.gitattributes` for EDI files

PortHub has no `.gitattributes`. With `core.autocrlf=true` (the Windows default in Git for Windows), a checkout turns every `.edi` file under `contracts/qa/baplie-corpus/` and `contracts/ai/baplie-corpus/` into CRLF. File `01_valid_standard_discharge.edi` is 1,906 bytes and has SHA-256 `72abea92aacabb62768d5109788dfc5f244a793f0d7fe05091d79d5ba798f2f1` in git, but 1,989 bytes and `2446beff861bc6978f022931712aae64560134ce387806ae1f89a7f9146b4946` on a Windows checkout. The hash written in `QA-AI2-baplie.md` (TC-BAP-001, TC-BAP-005) holds only for the LF bytes, and the Backend hashes whatever bytes are uploaded.

Proposed repo-level fix (PortHub, not applied by the AI Team):

```
# EDI files stay byte-exact on every machine: a CRLF checkout changes their SHA-256.
*.edi -text
```

This is not a defect of the QA test cases; it is a repository setting. project-ai already has the same line in its `.gitattributes` (added in AI-023) and keeps `tests/edi_corpus/` as LF.
