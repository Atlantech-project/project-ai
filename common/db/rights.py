"""What each worker may write, from `contracts/ai/table-ownership.md` §5 (CT-15, DEC-08).

MySQL enforces this through the grants; checking first gives a clear error before a statement is
sent. `tests/unit/common/db/test_rights.py` holds this table to the published matrix.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Final

from common.config import WorkerPart


@dataclass(frozen=True)
class WriteRights:
    insert: frozenset[str] = frozenset()
    update: Mapping[str, frozenset[str]] = field(default_factory=dict)
    # The worker's own run table; None for workers without runs.
    run_table: str | None = None


WRITE_RIGHTS: Final[Mapping[WorkerPart, WriteRights]] = {
    WorkerPart.PART1: WriteRights(
        insert=frozenset(
            {
                "entry_window_proposals",
                "feasible_windows",
                "blocked_periods",
                "forecast_runs",
                "environment_forecast_points",
                "tide_prediction_runs",
                "tide_prediction_points",
                "demand_forecast_slots",
            }
        ),
        update={
            "part1_runs": frozenset(
                {
                    "status",
                    "outcome",
                    "retry_count",
                    "entry_window_proposal_id",
                    "started_at",
                    "finished_at",
                }
            )
        },
        run_table="part1_runs",
    ),
    WorkerPart.PART2: WriteRights(
        insert=frozenset(
            {
                "solver_run_model_versions",
                "recommendations",
                "recommendation_options",
                "recommendation_option_tugs",
                "recommendation_rationale_factors",
            }
        ),
        update={
            "solver_runs": frozenset(
                {
                    "status",
                    "objective_value",
                    "solve_time_ms",
                    "solver_version",
                    "result_detail",
                    "started_at",
                    "finished_at",
                }
            )
        },
        run_table="solver_runs",
    ),
    WorkerPart.YARD: WriteRights(
        insert=frozenset({"yard_placement_items"}),
        update={
            "yard_runs": frozenset(
                {
                    "status",
                    "outcome",
                    "error_category",
                    "retry_count",
                    "result_detail",
                    "worker_version",
                    "started_at",
                    "finished_at",
                }
            ),
            "terminal_recommendations": frozenset(
                {
                    "lifecycle_status",
                    "confidence",
                    "rationale_template_id",
                    "rationale_params",
                    "failure_reason",
                }
            ),
        },
        run_table="yard_runs",
    ),
    WorkerPart.EDI: WriteRights(
        insert=frozenset({"baplie_parse_issues", "containers", "container_manifest_entries"}),
        update={
            "baplie_parse_runs": frozenset(
                {
                    "status",
                    "outcome",
                    "error_category",
                    "retry_count",
                    "container_count",
                    "result_detail",
                    "worker_version",
                    "started_at",
                    "finished_at",
                }
            ),
            "baplie_files": frozenset({"parse_status", "staged_payload"}),
            "vessels": frozenset({"call_sign", "flag_state"}),
        },
        run_table="baplie_parse_runs",
    ),
    WorkerPart.VALIDATE: WriteRights(),
    WorkerPart.PART3: WriteRights(insert=frozenset({"evaluation_metrics", "drift_measurements"})),
}

# A table-level INSERT grant can't exclude a column, so these rules are only enforced here.
BACKEND_ONLY_COLUMNS: Final[Mapping[str, frozenset[str]]] = {
    "drift_measurements": frozenset({"notified_at"}),  # CT-17 §7
    # CT-15: the Backend owns "the confirm / reject columns".
    "entry_window_proposals": frozenset(
        {
            "confirmed_window_id",
            "confirmed_by",
            "confirmed_at",
            "rejection_reason",
            "rejected_by",
            "rejected_at",
        }
    ),
}
