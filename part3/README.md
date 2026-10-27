# part3

AI Part 3, the feedback loop: evaluates the AI against actual outcomes and improves it, on this port's server only.

## Worker and queue

AI Part 3, running periodically. It has no user queue and reads and writes MySQL locally.

## Components

| ID | Component | Status |
|---|---|---|
| C1 | Outcome evaluation | MVP |
| C2 | Drift monitor (PSI and rolling MAE on M2, M3, M4) | MVP |
| C3 | Guarded retraining (Champion vs Challenger) | DATA-GATED |
| C4 | Forecast bias correction | DATA-GATED |

## Writes

- `evaluation_metric`, `drift_measurement`
- `ml_model_version`, `retraining_run` (data-gated; the Backend writes the review fields)

## Never

- I-4: Part 3 learns locally. No model, weight, training data or update leaves the port server.
- I-6: hard safety limits are never changed automatically.
- I-13: Part 3 uses trusted data only (`clock_skew_suspect = 0`).

## Pending

- OQ-1: Python tooling, version, dependency management and environment.
- DEC-31: Part 3 scheduling host (Open).
- OQ-7: location of model-artefact tooling. Artefacts stay on the local file volume (`ml_model_version.artifact_path`, §9.4).

## References

- `docs/ref/ATLANTECH_AI_ARCHITECTURE.md` §2, §9, §10, §12.2
- `docs/ref/ATLANTECH_Decisions.md` AI-001 (component status) and AI-010 (module structure) task decisions
