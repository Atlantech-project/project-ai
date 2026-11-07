# BAPLIE test corpus (AI-023)

Parser test inputs with expected outcomes for the EDI Parser (AI-030 onwards). The case list is in [INDEX.md](INDEX.md).

## What this is

- **Synthetic.** Every file is generated for testing; no real shipping data. Every oracle has `is_synthetic: true`.
- **Pairs.** Each case is `<name>.edi` plus `<name>.expected.json`, in the shape of the CT-24 starter files (`file`, `expected_outcome`, `expected_parse_status`, `vessel_imo`, `containers`, `issues`, `is_synthetic`). `segment_ref` is omitted for envelope-level rejections.
- **Reference.** CT-12 v1.1 (versions, outcomes, severities), CT-24 (case list and codes), DEC-17, DEC-28 item 7, and the current DB schema (`reefer_set_temperature`, `imdg_class`).
- **Integrity test.** `tests/unit/edi_corpus/test_corpus_integrity.py` checks the corpus against itself (pairs, oracle shape, segment and container counts, check digits). It is not the parser.

## Assumptions

- The berthing request's vessel IMO is `9811000` for every case. A case whose `TDT` carries another IMO (04, 14) expects `IMO_MISMATCH`.
- A wrong container check digit is a WARNING and the file stays PARSED (CT-12).
- `containers` is the number of `EQD+CN+` segments in the file, also for QUARANTINED cases.
- All container numbers have valid ISO 6346 check digits except in case 03.

## TODOs for AI-030

- `TODO(AI-030)`: the port qualifiers `LOC+11` (load port) and `LOC+12` (discharge port) follow CT-24 and DEC-28. Confirm them against the SMDG BAPLIE message implementation guides 2.2.1 and 3.1.1. QA's own files use `LOC+9` and `LOC+11` instead; if the guides say so, correct this corpus and CT-12.
- `TODO(AI-030)`: confirm `DGS+IMD`, `TMP+2` and `DIM+5` / `DIM+13` (out-of-gauge) qualifiers against the guides. They are not verified.

## Scope exception: size classes

AI-023's second acceptance criterion ("Size classes match the thresholds register") is **not met as written, by approved exception** (user, 2026-11-06). The thresholds register row TR-08 is OUT OF MVP SCOPE with no value (DEC-30 still Open), DEC-17 removed NFR-PERF-2 from the MVP, and the CT-24 README section 3 says the corpus holds no size-class benchmarks. The corpus has no small, medium or large files.

## D.17A is not supported

The user decided on 2026-11-07 that UN/EDIFACT D.17A (SMDG 2019) is **not supported**. CT-12 v1.1 supports only SMDG 2.2.1 (D.95B) and 3.1.1 (D.13B) and rejects anything else, and this corpus follows CT-12. Case `25-unsupported-version-d17a` is a well-formed D.17A file that must end `REJECTED` with `UNSUPPORTED_BAPLIE_VERSION` on `UNH`. The wording "D.17A" in the AI-023 backlog title and in `docs/ref/` is not changed by this task (read-only sources).

## Proposed codes

`MISSING_FULL_EMPTY`, `UNKNOWN_SEGMENT` and `UNREADABLE_FILE` are provisional, pending CT-24 approval (see INDEX.md).
