"""SQLAlchemy Core definitions of the tables workers write, and the few they read through models.

Written from `docs/ref/db/schema.sql`; `tests/integration/test_db_layer.py` holds every column to
the real schema, so a Backend migration that changes one fails the tests. Foreign keys and CHECK
constraints stay in the database, which enforces them. Nothing here creates a table (CT-17 §1).
"""

from datetime import UTC, datetime
from typing import Final

import sqlalchemy as sa
from sqlalchemy.dialects import mysql


class KnownEnum(sa.types.TypeDecorator[str]):
    """An ENUM read as plain text: a value added later must warn and skip, not raise (CT-17 §6)."""

    impl = sa.String
    cache_ok = True

    def __init__(self, *values: str) -> None:
        super().__init__()
        self.values = values


class UtcDateTime(sa.types.TypeDecorator[datetime]):
    """Every datetime column holds UTC (CT-17 §2); the driver would just drop an offset.

    A value with an offset converts to UTC. One without is taken as UTC already, because that's how
    the database returns them. Workers create only aware values, with `datetime.now(UTC)`.
    """

    impl = mysql.DATETIME
    cache_ok = True

    def __init__(self, fsp: int | None = None) -> None:
        super().__init__(fsp=fsp)

    def process_bind_param(self, value: datetime | None, dialect: sa.Dialect) -> datetime | None:
        if isinstance(value, datetime) and value.utcoffset() is not None:
            return value.astimezone(UTC)
        return value


metadata: Final = sa.MetaData()
_ID: Final = mysql.BIGINT(unsigned=True)

# Generated columns the database computes; no worker may write them (CT-17 §2).
GENERATED_INFO: Final = {"generated": True}

BAPLIE_FILES: Final = sa.Table(
    "baplie_files",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("vessel_id", _ID, nullable=False),
    sa.Column("berthing_request_id", _ID, nullable=False),
    sa.Column("uploaded_by", _ID, nullable=False),
    sa.Column("file_hash_sha256", mysql.CHAR(64), nullable=False),
    sa.Column("live_hash_key", mysql.CHAR(64), info=GENERATED_INFO),
    sa.Column("storage_path", mysql.VARCHAR(255), nullable=False),
    sa.Column(
        "parse_status", KnownEnum("PENDING", "PARSED", "FAILED", "QUARANTINED"), nullable=False
    ),
    sa.Column("status", KnownEnum("STAGED", "ACTIVE", "REPLACED", "WITHDRAWN"), nullable=False),
    sa.Column("active_request_key", _ID, info=GENERATED_INFO),
    sa.Column("staged_payload", mysql.JSON(none_as_null=True)),
    sa.Column("is_manually_corrected", mysql.TINYINT(1), nullable=False),
    sa.Column("corrected_by", _ID),
    sa.Column("corrected_at", UtcDateTime()),
    sa.Column("uploaded_at", UtcDateTime(), nullable=False),
    sa.Column("updated_at", UtcDateTime(fsp=6), nullable=False),
)

BAPLIE_PARSE_ISSUES: Final = sa.Table(
    "baplie_parse_issues",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("baplie_file_id", _ID, nullable=False),
    sa.Column("severity", KnownEnum("ERROR", "WARNING"), nullable=False),
    sa.Column("segment_ref", mysql.VARCHAR(60)),
    sa.Column("message", mysql.VARCHAR(500), nullable=False),
)

BAPLIE_PARSE_RUNS: Final = sa.Table(
    "baplie_parse_runs",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("baplie_file_id", _ID, nullable=False),
    sa.Column("source", KnownEnum("FILE", "STAGED_PAYLOAD"), nullable=False),
    sa.Column("triggered_by", _ID),
    sa.Column(
        "status", KnownEnum("QUEUED", "RUNNING", "DONE", "FAILED", "REPLACED"), nullable=False
    ),
    sa.Column("outcome", KnownEnum("PARSED", "QUARANTINED", "REJECTED")),
    sa.Column(
        "error_category",
        KnownEnum(
            "INVALID_ENVELOPE",
            "PRECONDITION_FAILED",
            "DATA_UNAVAILABLE",
            "CONFIGURATION_ERROR",
            "TIMEOUT",
            "INTERNAL_ERROR",
        ),
    ),
    sa.Column("retry_count", mysql.TINYINT(), nullable=False),
    sa.Column("container_count", mysql.INTEGER()),
    sa.Column("result_detail", mysql.JSON(none_as_null=True)),
    sa.Column("worker_version", mysql.VARCHAR(40)),
    sa.Column("queued_at", UtcDateTime(), nullable=False),
    sa.Column("started_at", UtcDateTime()),
    sa.Column("finished_at", UtcDateTime()),
    sa.Column("active_key", _ID, info=GENERATED_INFO),
    sa.Column("result_handled_at", UtcDateTime()),
)

BERTHING_REQUESTS: Final = sa.Table(
    "berthing_requests",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("vessel_id", _ID, nullable=False),
    sa.Column("requested_terminal_id", _ID, nullable=False),
    sa.Column("source", KnownEnum("MANUAL", "EXTERNAL"), nullable=False),
    sa.Column("external_system_id", _ID),
    sa.Column("external_reference", mysql.VARCHAR(100)),
    sa.Column("submitted_by", _ID),
    sa.Column("requested_eta", UtcDateTime(), nullable=False),
    sa.Column("arrival_draft", mysql.DECIMAL(5, 2), nullable=False),
    sa.Column("departure_draft", mysql.DECIMAL(5, 2)),
    sa.Column("previous_port", mysql.CHAR(5)),
    sa.Column("next_port", mysql.CHAR(5)),
    sa.Column("draft_source", KnownEnum("MANUAL", "EGMSW_FEED", "REGISTRY"), nullable=False),
    sa.Column("eta_source", KnownEnum("MANUAL", "EGMSW_FEED", "REGISTRY"), nullable=False),
    sa.Column("ports_source", KnownEnum("MANUAL", "EGMSW_FEED", "REGISTRY"), nullable=False),
    sa.Column("block_coefficient", mysql.DECIMAL(4, 3), nullable=False),
    sa.Column("gross_tonnage", mysql.INTEGER(), nullable=False),
    sa.Column("deadweight_tonnes", mysql.INTEGER(), nullable=False),
    sa.Column(
        "status",
        KnownEnum(
            "SUBMITTED",
            "NEEDS_REVISION",
            "PRELIMINARY_APPROVED",
            "CUSTOMS_APPROVED",
            "ENTRY_WINDOW_CONFIRMED",
            "RECOMMENDATION_GENERATED",
            "PLAN_CONFIRMED",
            "PLAN_CANCELLED",
            "COMPLETED",
            "REJECTED",
            "CANCELLED",
        ),
        nullable=False,
    ),
    sa.Column("created_at", UtcDateTime(), nullable=False),
    sa.Column("updated_at", UtcDateTime(fsp=6), nullable=False),
)

BLOCKED_PERIODS: Final = sa.Table(
    "blocked_periods",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("proposal_id", _ID, nullable=False),
    sa.Column("period_start", UtcDateTime(), nullable=False),
    sa.Column("period_end", UtcDateTime(), nullable=False),
    sa.Column("limiting_constraint_type_id", _ID, nullable=False),
)

CONTAINER_MANIFEST_ENTRIES: Final = sa.Table(
    "container_manifest_entries",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("baplie_file_id", _ID, nullable=False),
    sa.Column("container_id", _ID, nullable=False),
    sa.Column("full_empty", KnownEnum("FULL", "EMPTY")),
    sa.Column("weight_kg", mysql.INTEGER()),
    sa.Column("imdg_class", mysql.VARCHAR(3)),
    sa.Column("oog_over_front_cm", mysql.INTEGER()),
    sa.Column("oog_over_back_cm", mysql.INTEGER()),
    sa.Column("oog_over_right_cm", mysql.INTEGER()),
    sa.Column("oog_over_left_cm", mysql.INTEGER()),
    sa.Column("oog_over_height_cm", mysql.INTEGER()),
    sa.Column("reefer_set_temperature", mysql.DECIMAL(5, 2)),
    sa.Column("stowage_bay", mysql.INTEGER()),
    sa.Column("stowage_row", mysql.INTEGER()),
    sa.Column("stowage_tier", mysql.INTEGER()),
    sa.Column("port_of_load", mysql.CHAR(5)),
    sa.Column("port_of_discharge", mysql.CHAR(5)),
)

CONTAINERS: Final = sa.Table(
    "containers",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("container_number", mysql.CHAR(11), nullable=False),
    sa.Column("size_type_id", _ID, nullable=False),
)

DEMAND_FORECAST_SLOTS: Final = sa.Table(
    "demand_forecast_slots",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("generated_at", UtcDateTime(), nullable=False),
    sa.Column("slot_start", UtcDateTime(), nullable=False),
    sa.Column("slot_end", UtcDateTime(), nullable=False),
    sa.Column("expected_arrivals", mysql.INTEGER(), nullable=False),
    sa.Column("congestion_score", mysql.DECIMAL(4, 3), nullable=False),
    sa.Column("method", KnownEnum("AGGREGATION", "LIGHTGBM"), nullable=False),
    sa.Column("model_version_id", _ID),
)

DRIFT_MEASUREMENTS: Final = sa.Table(
    "drift_measurements",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("model_version_id", _ID, nullable=False),
    sa.Column("metric_type", KnownEnum("PSI", "ROLLING_MAE"), nullable=False),
    sa.Column("feature_name", mysql.VARCHAR(60)),
    sa.Column("metric_value", mysql.DECIMAL(14, 5), nullable=False),
    sa.Column("threshold", mysql.DECIMAL(14, 5), nullable=False),
    sa.Column("is_drifted", mysql.TINYINT(1), info=GENERATED_INFO),
    sa.Column("measured_at", UtcDateTime(), nullable=False),
    sa.Column("notified_at", UtcDateTime()),
)

ENTRY_WINDOW_PROPOSALS: Final = sa.Table(
    "entry_window_proposals",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("berthing_request_id", _ID, nullable=False),
    sa.Column("forecast_run_id", _ID, nullable=False),
    sa.Column("tide_prediction_run_id", _ID, nullable=False),
    sa.Column("bias_correction_version_id", _ID),
    sa.Column("peak_congestion_score", mysql.DECIMAL(4, 3)),
    sa.Column("status", KnownEnum("PROPOSED", "CONFIRMED", "REPLACED", "REJECTED"), nullable=False),
    sa.Column("confirmed_key", _ID, info=GENERATED_INFO),
    sa.Column("generated_at", UtcDateTime(), nullable=False),
    sa.Column("confirmed_window_id", _ID),
    sa.Column("confirmed_by", _ID),
    sa.Column("confirmed_at", UtcDateTime()),
    sa.Column("rejection_reason", mysql.VARCHAR(500)),
    sa.Column("rejected_by", _ID),
    sa.Column("rejected_at", UtcDateTime()),
    sa.Column("updated_at", UtcDateTime(fsp=6), nullable=False),
)

ENVIRONMENT_FORECAST_POINTS: Final = sa.Table(
    "environment_forecast_points",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("forecast_run_id", _ID, nullable=False),
    sa.Column("valid_at", UtcDateTime(), nullable=False),
    sa.Column("wind_speed", mysql.DECIMAL(5, 2)),
    sa.Column("wind_gust", mysql.DECIMAL(5, 2)),
    sa.Column("wind_direction_deg", mysql.DECIMAL(4, 1)),
    sa.Column("visibility", mysql.DECIMAL(8, 2)),
    sa.Column("wave_height", mysql.DECIMAL(4, 2)),
    sa.Column("wave_period", mysql.DECIMAL(4, 1)),
    sa.Column("wave_direction_deg", mysql.DECIMAL(4, 1)),
    sa.Column("current_speed", mysql.DECIMAL(4, 2)),
    sa.Column("sea_level", mysql.DECIMAL(5, 3)),
)

EVALUATION_METRICS: Final = sa.Table(
    "evaluation_metrics",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("model_version_id", _ID),
    sa.Column("retraining_run_id", _ID),
    sa.Column(
        "metric_name",
        KnownEnum("MAE", "OVERRIDE_RATE", "WAIT_TIME", "WINDOW_ACCURACY"),
        nullable=False,
    ),
    sa.Column("dataset_type", KnownEnum("HOLDOUT", "ROLLING", "PRODUCTION"), nullable=False),
    sa.Column("metric_value", mysql.DECIMAL(14, 5), nullable=False),
    sa.Column("period_start", UtcDateTime(), nullable=False),
    sa.Column("period_end", UtcDateTime(), nullable=False),
    sa.Column("computed_at", UtcDateTime(), nullable=False),
)

FEASIBLE_WINDOWS: Final = sa.Table(
    "feasible_windows",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("proposal_id", _ID, nullable=False),
    sa.Column("window_start", UtcDateTime(), nullable=False),
    sa.Column("window_end", UtcDateTime(), nullable=False),
    sa.Column("confidence", mysql.DECIMAL(4, 3)),
)

FORECAST_RUNS: Final = sa.Table(
    "forecast_runs",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("source", mysql.VARCHAR(80), nullable=False),
    sa.Column("pull_type", KnownEnum("SCHEDULED", "ON_DEMAND", "MANUAL"), nullable=False),
    sa.Column("provider_rank", KnownEnum("PRIMARY", "SECONDARY", "MANUAL")),
    sa.Column("data_stale", mysql.TINYINT(1), nullable=False),
    sa.Column("berthing_request_id", _ID),
    sa.Column("submitted_by", _ID),
    sa.Column("status", KnownEnum("SUCCESS", "FAILED"), nullable=False),
    sa.Column("pulled_at", UtcDateTime(), nullable=False),
    sa.Column("horizon_start", UtcDateTime()),
    sa.Column("horizon_end", UtcDateTime()),
    sa.Column(
        "wind_speed_unit", KnownEnum("KNOTS", "METRES_PER_SECOND", "KM_PER_HOUR"), nullable=False
    ),
    sa.Column(
        "current_speed_unit", KnownEnum("KNOTS", "METRES_PER_SECOND", "KM_PER_HOUR"), nullable=False
    ),
    sa.Column(
        "visibility_unit", KnownEnum("NAUTICAL_MILES", "KILOMETRES", "METRES"), nullable=False
    ),
)

PART1_RUNS: Final = sa.Table(
    "part1_runs",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("berthing_request_id", _ID, nullable=False),
    sa.Column(
        "status", KnownEnum("QUEUED", "RUNNING", "DONE", "FAILED", "REPLACED"), nullable=False
    ),
    sa.Column("outcome", KnownEnum("WINDOWS_FOUND", "NO_FEASIBLE_WINDOW", "ENV_DATA_UNAVAILABLE")),
    sa.Column("retry_count", mysql.TINYINT(), nullable=False),
    sa.Column("entry_window_proposal_id", _ID),
    sa.Column("queued_at", UtcDateTime(), nullable=False),
    sa.Column("started_at", UtcDateTime()),
    sa.Column("finished_at", UtcDateTime()),
    sa.Column("result_handled_at", UtcDateTime()),
)

RECOMMENDATION_OPTION_TUGS: Final = sa.Table(
    "recommendation_option_tugs",
    metadata,
    sa.Column("option_id", _ID, primary_key=True, autoincrement=False),
    sa.Column("tugboat_id", _ID, primary_key=True, autoincrement=False),
)

RECOMMENDATION_OPTIONS: Final = sa.Table(
    "recommendation_options",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("recommendation_id", _ID, nullable=False),
    sa.Column("terminal_id", _ID, nullable=False),
    sa.Column("option_rank", mysql.INTEGER(), nullable=False),
    sa.Column("berth_id", _ID, nullable=False),
    sa.Column("planned_start", UtcDateTime(), nullable=False),
    sa.Column("planned_end", UtcDateTime(), nullable=False),
    sa.Column("pilot_user_id", _ID),
    sa.Column("service_time_method", KnownEnum("FORMULA", "ML"), nullable=False),
    sa.Column("service_time_p50_hours", mysql.DECIMAL(6, 2), nullable=False),
    sa.Column("service_time_p90_hours", mysql.DECIMAL(6, 2)),
    sa.Column("delay_risk", mysql.DECIMAL(4, 3)),
    sa.Column("objective_score", mysql.DECIMAL(14, 4)),
    sa.Column("rationale_template_id", _ID),
    sa.Column("rationale_params", mysql.JSON(none_as_null=True)),
)

RECOMMENDATION_RATIONALE_FACTORS: Final = sa.Table(
    "recommendation_rationale_factors",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("option_id", _ID, nullable=False),
    sa.Column("factor_type", KnownEnum("CONSTRAINT", "OBJECTIVE_TERM"), nullable=False),
    sa.Column("constraint_type_id", _ID),
    sa.Column("objective_term_id", _ID),
    sa.Column("factor_value", mysql.DECIMAL(14, 4)),
    sa.Column("display_order", mysql.INTEGER(), nullable=False),
)

RECOMMENDATIONS: Final = sa.Table(
    "recommendations",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("solver_run_id", _ID, nullable=False),
    sa.Column("berthing_request_id", _ID, nullable=False),
    sa.Column("terminal_id", _ID, nullable=False),
    sa.Column("entry_window_proposal_id", _ID, nullable=False),
    sa.Column(
        "status",
        KnownEnum(
            "PENDING_REVIEW",
            "CONFIRMED",
            "REJECTED",
            "INVALIDATED",
            "REPLACED",
            "MODIFIED_BY_STAFF",
        ),
        nullable=False,
    ),
    sa.Column("source", KnownEnum("AI", "FIFO"), nullable=False),
    sa.Column("purpose", KnownEnum("INITIAL", "DELAY_REPLAN"), nullable=False),
    sa.Column("active_key", _ID, info=GENERATED_INFO),
    sa.Column("generated_at", UtcDateTime(), nullable=False),
    sa.Column("updated_at", UtcDateTime(fsp=6), nullable=False),
)

SOLVER_RUN_MODEL_VERSIONS: Final = sa.Table(
    "solver_run_model_versions",
    metadata,
    sa.Column("solver_run_id", _ID, primary_key=True, autoincrement=False),
    sa.Column("model_version_id", _ID, primary_key=True, autoincrement=False),
)

SOLVER_RUNS: Final = sa.Table(
    "solver_runs",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column(
        "trigger_type",
        KnownEnum("NEW_REQUEST", "REPLAN", "RESOURCE_CHANGE", "MANUAL"),
        nullable=False,
    ),
    sa.Column("triggered_by", _ID),
    sa.Column("horizon_start", UtcDateTime(), nullable=False),
    sa.Column("horizon_end", UtcDateTime(), nullable=False),
    sa.Column(
        "status",
        KnownEnum("QUEUED", "RUNNING", "OPTIMAL", "FEASIBLE", "INFEASIBLE", "ERROR"),
        nullable=False,
    ),
    sa.Column("objective_value", mysql.DECIMAL(14, 4)),
    sa.Column("solve_time_ms", mysql.INTEGER()),
    sa.Column("solver_version", mysql.VARCHAR(40), nullable=False),
    sa.Column("result_detail", mysql.JSON(none_as_null=True)),
    sa.Column("queued_at", UtcDateTime(), nullable=False),
    sa.Column("started_at", UtcDateTime()),
    sa.Column("finished_at", UtcDateTime()),
    sa.Column("result_handled_at", UtcDateTime()),
)

TERMINAL_RECOMMENDATIONS: Final = sa.Table(
    "terminal_recommendations",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("recommendation_id", _ID, nullable=False),
    sa.Column("terminal_id", _ID, nullable=False),
    sa.Column("terminal_type", KnownEnum("CONTAINER", "NON_CONTAINER"), nullable=False),
    sa.Column(
        "rec_type", KnownEnum("TIMING", "YARD_PLACEMENT", "STORAGE_ALLOCATION"), nullable=False
    ),
    sa.Column("window_start", UtcDateTime()),
    sa.Column("window_end", UtcDateTime()),
    sa.Column("decision", KnownEnum("PENDING", "ACCEPTED", "REJECTED", "ADJUSTED"), nullable=False),
    sa.Column("decided_by", _ID),
    sa.Column("decided_at", UtcDateTime()),
    sa.Column("decision_note", mysql.VARCHAR(500)),
    sa.Column(
        "lifecycle_status",
        KnownEnum(
            "YARD_REC_REQUESTED",
            "YARD_REC_GENERATED",
            "GENERATION_FAILED",
            "YARD_REC_ACCEPTED",
            "YARD_REC_REJECTED",
            "EXPORTED_TO_TOS",
        ),
    ),
    sa.Column("failure_reason", mysql.VARCHAR(500)),
    sa.Column("exported_at", UtcDateTime()),
    sa.Column("exported_by", _ID),
    sa.Column("rationale_template_id", _ID),
    sa.Column("confidence", mysql.DECIMAL(4, 3)),
    sa.Column("rationale_params", mysql.JSON(none_as_null=True)),
    sa.Column("updated_at", UtcDateTime(fsp=6), nullable=False),
)

TIDE_PREDICTION_POINTS: Final = sa.Table(
    "tide_prediction_points",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("tide_prediction_run_id", _ID, nullable=False),
    sa.Column("valid_at", UtcDateTime(), nullable=False),
    sa.Column("height", mysql.DECIMAL(5, 3), nullable=False),
)

TIDE_PREDICTION_RUNS: Final = sa.Table(
    "tide_prediction_runs",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("constituent_set_id", _ID, nullable=False),
    sa.Column("computed_at", UtcDateTime(), nullable=False),
    sa.Column("horizon_start", UtcDateTime(), nullable=False),
    sa.Column("horizon_end", UtcDateTime(), nullable=False),
)

TUGBOATS: Final = sa.Table(
    "tugboats",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("name", mysql.VARCHAR(100), nullable=False),
    sa.Column("tug_power", mysql.DECIMAL(8, 2), nullable=False),
    sa.Column("tug_power_unit", KnownEnum("BOLLARD_PULL_TONNES", "HP", "KW"), nullable=False),
    sa.Column("capacity", mysql.DECIMAL(8, 2)),
    sa.Column("status", KnownEnum("AVAILABLE", "BUSY", "MAINTENANCE", "INACTIVE"), nullable=False),
    sa.Column("updated_at", UtcDateTime(fsp=6), nullable=False),
)

VESSEL_TYPES: Final = sa.Table(
    "vessel_types",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("code", mysql.VARCHAR(30), nullable=False),
    sa.Column("name", mysql.VARCHAR(80), nullable=False),
)

VESSELS: Final = sa.Table(
    "vessels",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("imo_number", mysql.CHAR(7), nullable=False),
    sa.Column("name", mysql.VARCHAR(120), nullable=False),
    sa.Column("vessel_type_id", _ID, nullable=False),
    sa.Column("loa", mysql.DECIMAL(7, 2), nullable=False),
    sa.Column("beam", mysql.DECIMAL(6, 2), nullable=False),
    sa.Column("max_draft", mysql.DECIMAL(5, 2), nullable=False),
    sa.Column("net_tonnage", mysql.INTEGER()),
    sa.Column("moulded_depth", mysql.DECIMAL(5, 2)),
    sa.Column("call_sign", mysql.VARCHAR(10)),
    sa.Column("flag_state", mysql.CHAR(2)),
    sa.Column("updated_at", UtcDateTime(fsp=6), nullable=False),
)

YARD_PLACEMENT_ITEMS: Final = sa.Table(
    "yard_placement_items",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("terminal_recommendation_id", _ID, nullable=False),
    sa.Column(
        "rec_type", KnownEnum("TIMING", "YARD_PLACEMENT", "STORAGE_ALLOCATION"), nullable=False
    ),
    sa.Column("manifest_entry_id", _ID, nullable=False),
    sa.Column("yard_block_id", _ID, nullable=False),
    sa.Column("yard_slot_id", _ID),
)

YARD_RUNS: Final = sa.Table(
    "yard_runs",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("terminal_recommendation_id", _ID, nullable=False),
    sa.Column("triggered_by", _ID),
    sa.Column(
        "status", KnownEnum("QUEUED", "RUNNING", "DONE", "FAILED", "REPLACED"), nullable=False
    ),
    sa.Column("outcome", KnownEnum("YARD_REC_GENERATED", "GENERATION_FAILED")),
    sa.Column(
        "error_category",
        KnownEnum(
            "INVALID_ENVELOPE",
            "PRECONDITION_FAILED",
            "DATA_UNAVAILABLE",
            "CONFIGURATION_ERROR",
            "INFEASIBLE",
            "TIMEOUT",
            "INTERNAL_ERROR",
        ),
    ),
    sa.Column("retry_count", mysql.TINYINT(), nullable=False),
    sa.Column("result_detail", mysql.JSON(none_as_null=True)),
    sa.Column("worker_version", mysql.VARCHAR(40)),
    sa.Column("queued_at", UtcDateTime(), nullable=False),
    sa.Column("started_at", UtcDateTime()),
    sa.Column("finished_at", UtcDateTime()),
    sa.Column("active_key", _ID, info=GENERATED_INFO),
    sa.Column("result_handled_at", UtcDateTime()),
)

# Tables the Part 2 port-state loader only reads (AI-050); the Backend owns them (CT-15).

BERTH_TERMINALS: Final = sa.Table(
    "berth_terminals",
    metadata,
    sa.Column("berth_id", _ID, primary_key=True, autoincrement=False),
    sa.Column("terminal_id", _ID, primary_key=True, autoincrement=False),
)

BERTHS: Final = sa.Table(
    "berths",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("code", mysql.VARCHAR(30), nullable=False),
    sa.Column("name", mysql.VARCHAR(80)),
    sa.Column("length", mysql.DECIMAL(7, 2), nullable=False),
    sa.Column("water_depth", mysql.DECIMAL(6, 2), nullable=False),
    sa.Column("depth_datum", mysql.VARCHAR(40), nullable=False),
    sa.Column("max_vessel_loa", mysql.DECIMAL(7, 2), nullable=False),
    sa.Column("status", KnownEnum("ACTIVE", "MAINTENANCE", "INACTIVE"), nullable=False),
    sa.Column("latitude", mysql.DECIMAL(9, 6)),
    sa.Column("longitude", mysql.DECIMAL(9, 6)),
    sa.Column("updated_at", UtcDateTime(fsp=6), nullable=False),
)

OPERATIONAL_PLANS: Final = sa.Table(
    "operational_plans",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("berthing_request_id", _ID, nullable=False),
    sa.Column("recommendation_id", _ID, nullable=False),
    sa.Column("recommendation_option_id", _ID, nullable=False),
    sa.Column("status", KnownEnum("CONFIRMED", "CANCELLED", "COMPLETED"), nullable=False),
    sa.Column("active_key", _ID, info=GENERATED_INFO),
    sa.Column("confirmed_by", _ID, nullable=False),
    sa.Column("confirmed_at", UtcDateTime(), nullable=False),
    sa.Column("updated_at", UtcDateTime(fsp=6), nullable=False),
)

PILOT_PROFILES: Final = sa.Table(
    "pilot_profiles",
    metadata,
    sa.Column("user_id", _ID, primary_key=True, autoincrement=False),
    sa.Column("pilot_rank", KnownEnum("FIRST", "SECOND", "THIRD"), nullable=False),
    sa.Column("updated_at", UtcDateTime(fsp=6), nullable=False),
)

PILOT_RANK_LIMITS: Final = sa.Table(
    "pilot_rank_limits",
    metadata,
    sa.Column(
        "pilot_rank", KnownEnum("FIRST", "SECOND", "THIRD"), primary_key=True, autoincrement=False
    ),
    sa.Column("max_vessel_loa", mysql.DECIMAL(7, 2)),
    sa.Column("updated_at", UtcDateTime(fsp=6), nullable=False),
)

PILOT_SCHEDULES: Final = sa.Table(
    "pilot_schedules",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("pilot_user_id", _ID, nullable=False),
    sa.Column("shift_date", mysql.DATE(), nullable=False),
    sa.Column("port_shift_id", _ID, nullable=False),
    sa.Column("created_by", _ID, nullable=False),
)

PLAN_COMPONENTS: Final = sa.Table(
    "plan_components",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("operational_plan_id", _ID, nullable=False),
    sa.Column("component_type", KnownEnum("BERTH", "PILOT", "TUG", "TERMINAL_OPS"), nullable=False),
    sa.Column("berth_id", _ID),
    sa.Column("tugboat_id", _ID),
    sa.Column("terminal_id", _ID),
    sa.Column("assigned_user_id", _ID),
    sa.Column("assigned_by", _ID),
    sa.Column("assigned_at", UtcDateTime()),
    sa.Column("planned_start", UtcDateTime(), nullable=False),
    sa.Column("planned_end", UtcDateTime(), nullable=False),
    sa.Column("reservation_state", KnownEnum("RESERVED", "RELEASED", "CONSUMED"), nullable=False),
    sa.Column("updated_at", UtcDateTime(fsp=6), nullable=False),
)

PORT_PROFILES: Final = sa.Table(
    "port_profiles",
    metadata,
    sa.Column("id", _ID, primary_key=True, autoincrement=False),
    sa.Column("public_id", mysql.CHAR(36), nullable=False),
    sa.Column("port_code", mysql.VARCHAR(10)),
    sa.Column("governorate_code", mysql.VARCHAR(6), nullable=False),
    sa.Column("name", mysql.VARCHAR(150), nullable=False),
    sa.Column("latitude", mysql.DECIMAL(9, 6), nullable=False),
    sa.Column("longitude", mysql.DECIMAL(9, 6), nullable=False),
    sa.Column("timezone", mysql.VARCHAR(64), nullable=False),
    sa.Column("boundary_coordinates", mysql.JSON(none_as_null=True)),
    sa.Column("created_at", UtcDateTime(), nullable=False),
    sa.Column("updated_at", UtcDateTime(fsp=6), nullable=False),
)

PORT_SHIFTS: Final = sa.Table(
    "port_shifts",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("code", mysql.VARCHAR(20), nullable=False),
    sa.Column("name", mysql.VARCHAR(60), nullable=False),
    sa.Column("start_time", mysql.TIME(), nullable=False),
    sa.Column("end_time", mysql.TIME(), nullable=False),
    sa.Column("is_active", mysql.TINYINT(1), nullable=False),
    sa.Column("updated_at", UtcDateTime(fsp=6), nullable=False),
)

SAFETY_CONSTRAINTS: Final = sa.Table(
    "safety_constraints",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("constraint_type_id", _ID, nullable=False),
    sa.Column("terminal_id", _ID),
    sa.Column("berth_id", _ID),
    sa.Column("vessel_type_id", _ID),
    sa.Column("imdg_class", mysql.VARCHAR(3)),
    sa.Column("equipment_category_id", _ID),
    sa.Column("value", mysql.DECIMAL(12, 3), nullable=False),
    sa.Column("created_by", _ID, nullable=False),
    sa.Column("active_from", UtcDateTime(), nullable=False),
    sa.Column("active_to", UtcDateTime()),
    sa.Column("updated_at", UtcDateTime(fsp=6), nullable=False),
)

TUG_MASTER_PROFILES: Final = sa.Table(
    "tug_master_profiles",
    metadata,
    sa.Column("user_id", _ID, primary_key=True, autoincrement=False),
    sa.Column("assigned_tugboat_id", _ID),
    sa.Column("updated_at", UtcDateTime(fsp=6), nullable=False),
)

TUG_MASTER_SCHEDULES: Final = sa.Table(
    "tug_master_schedules",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("tug_master_user_id", _ID, nullable=False),
    sa.Column("shift_date", mysql.DATE(), nullable=False),
    sa.Column("port_shift_id", _ID, nullable=False),
    sa.Column("created_by", _ID, nullable=False),
)

USER_ROLE_ASSIGNMENTS: Final = sa.Table(
    "user_role_assignments",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("user_id", _ID, nullable=False),
    sa.Column(
        "role",
        KnownEnum(
            "PORT_GM",
            "PORT_STAFF",
            "MARINE_SAFETY_OFFICER",
            "PILOTAGE_MANAGER",
            "PILOTAGE_OFFICER",
            "MARINE_PILOT",
            "TUG_MANAGER",
            "TUG_OFFICER",
            "TUG_MASTER",
            "TERMINAL_ADMIN",
            "TERMINAL_OFFICER",
            "TERMINAL_SUPERVISOR",
        ),
        nullable=False,
    ),
    sa.Column("organization_unit_id", _ID, nullable=False),
    sa.Column(
        "unit_type", KnownEnum("HARBOUR_AUTHORITY", "MARINE_SERVICES", "TERMINAL"), nullable=False
    ),
    sa.Column("active_from", UtcDateTime(), nullable=False),
    sa.Column("active_to", UtcDateTime()),
    sa.Column("active_assignment_key", mysql.TINYINT(), info=GENERATED_INFO),
)

USERS: Final = sa.Table(
    "users",
    metadata,
    sa.Column("id", _ID, primary_key=True),
    sa.Column("name", mysql.VARCHAR(120), nullable=False),
    sa.Column("username", mysql.VARCHAR(50), nullable=False),
    sa.Column("password_hash", mysql.VARCHAR(255), nullable=False),
    sa.Column("phone", mysql.VARCHAR(30)),
    sa.Column("is_active", mysql.TINYINT(1), nullable=False),
    sa.Column("must_change_password", mysql.TINYINT(1), nullable=False),
    sa.Column("created_at", UtcDateTime(), nullable=False),
    sa.Column("updated_at", UtcDateTime(fsp=6), nullable=False),
)
