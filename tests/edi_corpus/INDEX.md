# BAPLIE test corpus index (AI-023)

Synthetic cases 01 to 18 follow CT-24's case list, names, versions, outcomes and issue codes. Cases 19 to 25 are added for AI-023 coverage (25 is the D.17A rejection case). See [README.md](README.md) for provenance and assumptions.

| Case | BAPLIE version | Injected characteristic | Outcome | Expected issues |
| --- | --- | --- | --- | --- |
| `01-valid-221` | 2.2.1 (D.95B) | Clean valid file with VGM | PARSED | none |
| `02-valid-311` | 3.1.1 (D.13B) | Clean valid file with VGM | PARSED | none |
| `03-valid-with-warnings` | 2.2.1 (D.95B) | Container check digit mismatch | PARSED | WARNING `CHECK_DIGIT_MISMATCH` |
| `04-imo-mismatch` | 2.2.1 (D.95B) | Vessel IMO differs from request | QUARANTINED | ERROR `IMO_MISMATCH` |
| `05-duplicate-container` | 2.2.1 (D.95B) | Duplicate container number in file | QUARANTINED | ERROR `DUPLICATE_CONTAINER_NUMBER` |
| `06-unknown-iso-size-type` | 2.2.1 (D.95B) | Invalid ISO size/type code 45X9 | QUARANTINED | ERROR `UNKNOWN_SIZE_TYPE` |
| `07-unknown-imdg-class` | 2.2.1 (D.95B) | Unrecognised IMDG class 99 | QUARANTINED | ERROR `UNKNOWN_IMDG_CLASS` |
| `08-malformed-weight` | 2.2.1 (D.95B) | Negative weight | QUARANTINED | ERROR `MALFORMED_WEIGHT` |
| `09-malformed-unlocode` | 2.2.1 (D.95B) | Invalid port code syntax | QUARANTINED | ERROR `MALFORMED_UNLOCODE` |
| `10-temperature-out-of-range` | 2.2.1 (D.95B) | Reefer set temperature above +40 | QUARANTINED | ERROR `TEMPERATURE_OUT_OF_RANGE` |
| `11-reefer-missing-temp` | 2.2.1 (D.95B) | Reefer size code without set temperature | QUARANTINED | ERROR `REEFER_MISSING_TEMPERATURE` |
| `12-invalid-stowage-coordinate` | 2.2.1 (D.95B) | Stowage bay/row/tier out of bounds | QUARANTINED | ERROR `INVALID_STOWAGE_COORDINATE` |
| `13-missing-mandatory-segment` | 2.2.1 (D.95B) | Missing mandatory MEA segment | QUARANTINED | ERROR `MISSING_MANDATORY_SEGMENT` |
| `14-multiple-errors-composite` | 2.2.1 (D.95B) | Combined IMO + size + weight errors | QUARANTINED | ERROR `IMO_MISMATCH`, ERROR `UNKNOWN_SIZE_TYPE`, ERROR `MALFORMED_WEIGHT` |
| `15-non-edifact-payload` | plain text | Non-EDI formatted file | REJECTED | ERROR `NOT_EDIFACT` |
| `16-unsupported-version` | 1.5 | Outdated or unsupported version | REJECTED | ERROR `UNSUPPORTED_BAPLIE_VERSION` |
| `17-wrong-message-type` | COPRAR | Valid EDIFACT but wrong message type | REJECTED | ERROR `WRONG_MESSAGE_TYPE` |
| `18-corrupted-syntax` | 2.2.1 (D.95B), truncated | Truncated EDI, no UNZ | REJECTED | ERROR `CORRUPTED_SYNTAX` |
| `19-valid-dangerous-goods` | 2.2.1 (D.95B) | Valid dangerous goods (IMDG class 3) | PARSED | none |
| `20-valid-reefer` | 2.2.1 (D.95B) | Valid reefer with set temperature -18 C | PARSED | none |
| `21-valid-oog` | 2.2.1 (D.95B) | Out-of-gauge: front 20 cm, height 30 cm (`DIM` qualifiers unverified) | PARSED | none |
| `22-missing-full-empty` | 2.2.1 (D.95B) | Missing full/empty indicator | PARSED | WARNING `MISSING_FULL_EMPTY` **(proposed)** |
| `23-unknown-segment` | 2.2.1 (D.95B) | Unknown segment between containers (NFR-INT-1) | PARSED | WARNING `UNKNOWN_SEGMENT` **(proposed)** |
| `24-unreadable-file` | none (0 bytes) | Unreadable (empty) file | REJECTED | ERROR `UNREADABLE_FILE` **(proposed)** |
| `25-unsupported-version-d17a` | D.17A / SMDG 2019 (`BAPLIE:D:17A:UN:SMDG20`) | Otherwise well-formed file with an unsupported directory (D.17A is not supported) | REJECTED | ERROR `UNSUPPORTED_BAPLIE_VERSION` |

Outcome mapping: PARSED = `PARSED`; QUARANTINED = `QUARANTINED`; REJECTED = `parse_status` `FAILED`, and the run is `DONE` with outcome `REJECTED` (CT-12).

## Proposed codes, pending CT-24 approval

`MISSING_FULL_EMPTY` (WARNING), `UNKNOWN_SEGMENT` (WARNING) and `UNREADABLE_FILE` (ERROR) are **not in CT-24 or CT-12**. They are provisional names for behaviour that CT-12 and NFR-INT-1 describe. Cases 22, 23 and 24 use them until CT-24 approves or renames them. The proposed CT-24 change is in `docs/followups/contracts-followup.md`.

`UNSUPPORTED_BAPLIE_VERSION` (cases 16 and 25) is **not** proposed: it is the code already used by the CT-24 starter oracle `16-unsupported-version.expected.json` and listed for case 16 in the CT-24 README table. CT-12 defines `segment_ref` (`UNH`) and the message text for unsupported versions but no code name.

## AI-023 expected outputs mapped to cases

| AI-023 output | Case |
| --- | --- |
| Valid small | `01-valid-221` (medium and large: scope exception, see README) |
| IMO mismatch | `04-imo-mismatch` |
| Invalid segments | `13-missing-mandatory-segment`, `18-corrupted-syntax` |
| Unknown segments | `23-unknown-segment` |
| Missing full/empty | `22-missing-full-empty` |
| Reefer without temperature | `11-reefer-missing-temp` |
| OOG | `21-valid-oog` |
| DG | `19-valid-dangerous-goods` |
| Bad check digit | `03-valid-with-warnings` |
| Unreadable file | `24-unreadable-file` |
