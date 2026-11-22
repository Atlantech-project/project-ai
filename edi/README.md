# edi

The EDI Parser worker: reads BAPLIE files into vessel, container and manifest data.

## Worker and queue

EDI Parser, consuming `queue:edi`. The Backend creates the `baplie_file` row before it enqueues the job.

## Components

| ID | Component | Status |
|---|---|---|
| B1 | BAPLIE parser: deterministic EDIFACT parser for SMDG BAPLIE 2.2.1 (UN/EDIFACT D.95B) and 3.1.1 (D.13B), per CT-12 v1.1; any other version, D.17A included, is rejected. Vessel, containers, stowage | MVP |

## Parser (AI-030)

`edi.parse_baplie(data: bytes) -> ParseResult` turns the bytes of one file into in-memory records. It is pure: no database, no file access, no clock.

- **`REJECTED`**: one ERROR issue, no vessel, no lines. Codes: `UNREADABLE_FILE`, `NOT_EDIFACT`, `CORRUPTED_SYNTAX`, `WRONG_MESSAGE_TYPE`, `UNSUPPORTED_BAPLIE_VERSION`. An unsupported version, a different message type and a non-EDIFACT file all get the CT-12 v1.1 issue: `segment_ref = "UNH"`, `"Unsupported BAPLIE version: <found>. Supported: SMDG 2.2.1 (D.95B), SMDG 3.1.1 (D.13B)"`. For a non-EDIFACT file, `<found>` is the first 3 characters of the file as read, or `none`.
- **`READ`**: a `ParsedVessel` (from `TDT+20`) and one `ParsedLine` per container. Field names follow the CT-12 `staged_payload` line. An unknown segment is skipped with a WARNING `UNKNOWN_SEGMENT`, and the other containers still load.
- **Values are kept as written.** A value that cannot be converted leaves the field `None` and keeps the raw element in `line.unconverted`. Each field's source segment is in `line.segment_refs`.
- A container line starts at `LOC+147` or `EQD+CN` when the current line already has one, so stowage-first and EQD-first files both work.

Where the parser stops:
- Content rules are `edi.rules` (AI-031, below).
- The worker job, reading the file, writing `staged_payload` and the commit are AI-032.

## Content rules (AI-031)

`edi.rules.validate(vessel, lines, reference) -> tuple[Finding, ...]` applies every CT-12 v1.1 content rule to the parser's records. `reference` (`edi.rules.Reference`) carries what the tables hold: the request vessel's IMO and name, `container_size_types` codes with `is_reefer`, `imdg_classes` codes, and the size types already stored for existing container numbers. `edi.rules.outcome(findings)` is `QUARANTINED` when any ERROR applies, otherwise `PARSED`.

- **ERROR:** `IMO_MISMATCH`, `DUPLICATE_CONTAINER_NUMBER`, `UNKNOWN_SIZE_TYPE`, `UNKNOWN_IMDG_CLASS`, `MALFORMED_WEIGHT`, `MISSING_MANDATORY_SEGMENT` (no weight), `MALFORMED_UNLOCODE`, `TEMPERATURE_OUT_OF_RANGE`, `MALFORMED_TEMPERATURE`, `REEFER_MISSING_TEMPERATURE`, `INVALID_STOWAGE_COORDINATE`, `MALFORMED_OOG`, `MALFORMED_CONTAINER_NUMBER`, `MALFORMED_CALL_SIGN`.
- **WARNING:** `CHECK_DIGIT_MISMATCH`, `MISSING_FULL_EMPTY`, `MISSING_PORT_OF_DISCHARGE`, `VESSEL_NAME_MISMATCH`, `SIZE_TYPE_CHANGED`.
- Codes, references and messages follow the AI-023 corpus oracles where a case exists; the others are Proposed in the AI-031 task decision.
- **Correction path (DEC-03, `source = STAGED_PAYLOAD`):** `edi.rules.validate_staged_payload(payload, reference)` reads a staff-corrected `staged_payload` back into the same records and calls the same `validate`. Issues then point at each line's `segment_ref`, because the payload carries no segment texts.
- **Stowage:** only the schema's bounds are enforced (bay > 0, row ≥ 0, tier > 0); no document gives upper bounds, so corpus case 12 is skipped until they are defined.
- **Storable range:** a weight, overhang or stowage value above 2,147,483,647 (the schema's `int` columns) is an ERROR under the rule's code, so the file is quarantined instead of failing the write. This is a storage limit, not an operational bound.
- **Call sign (R12):** a corrected `call_sign` longer than 10 characters (`vessels.call_sign` is `varchar(10)`) is an ERROR, `MALFORMED_CALL_SIGN`, so the file stays quarantined instead of failing the fill; so is a corrected call sign that is not text (reported with its raw text, not dropped). Only a correction can supply a call sign: the parser reads the IMO and name from TDT only. No call-sign format is checked (no source gives one).

**Unverified mapping (DEC-28 item 7).** The qualifiers and positions in `edi/mapping.py` follow the AI-023 corpus, CT-12 and DEC-28, not the SMDG implementation guides 2.2.1 and 3.1.1, which are not available. `mapping.py` is the one place to correct them.

## Writes

- `baplie_file` (status fields), `baplie_parse_issue`
- `container`, `container_manifest_entry`
- `vessel` (fill-empty)

## Never

- I-11: BAPLIE parsing is deterministic and all-or-nothing. It is not AI.

## Pending

- OQ-2: location of the AI-owned JSON Schemas (this repository or `PortHub/contracts/`).

## References

- `docs/ref/ATLANTECH_Contracts.md` CT-12 (versions, outcomes, `staged_payload`), CT-24 (corpus)
- `docs/ref/ATLANTECH_Decisions.md` DEC-17, DEC-28 item 7, AI-001 (component status) and AI-010 (module structure) task decisions
- `docs/ref/ATLANTECH_AI_ARCHITECTURE.md` §2, §6, §12.2 (§6 still names D.17A and SMDG 2019; CT-12 v1.1 supersedes it)
- `tests/edi_corpus/` (AI-023)
