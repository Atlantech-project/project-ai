# edi

The EDI Parser worker: reads BAPLIE files into vessel, container and manifest data.

## Worker and queue

EDI Parser, consuming `queue:edi`. The Backend creates the `baplie_file` row before it enqueues the job.

## Components

| ID | Component | Status |
|---|---|---|
| B1 | BAPLIE parser: deterministic EDIFACT parser, UN/EDIFACT D.17A and SMDG 2019; vessel, containers, stowage | MVP |

## Writes

- `baplie_file` (status fields), `baplie_parse_issue`
- `container`, `container_manifest_entry`
- `vessel` (fill-empty)

## Never

- I-11: BAPLIE parsing is deterministic and all-or-nothing. It is not AI.

## Pending

- OQ-1: Python tooling, version, dependency management and environment. No code or setup lives here until it is decided.
- OQ-2: location of the AI-owned JSON Schemas (this repository or `PortHub/contracts/`).

## References

- `docs/ref/ATLANTECH_AI_ARCHITECTURE.md` §2, §6, §12.2
- `docs/tasks/DECISION_LOG.md` DL-001 (component status), DL-002 (module structure)
