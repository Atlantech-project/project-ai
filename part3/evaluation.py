"""C1 outcome evaluation (AI-071): `evaluation_metrics` rows, as far as the sources define them.

Architecture §9.1 (C1) names four metrics; the schema fixes their shape and scope:

- `chk_em_scope`: `MAE` needs a model version; `OVERRIDE_RATE` and `WAIT_TIME` must have none
  (system-level metrics); `WINDOW_ACCURACY` may have either.
- `chk_em_period`: `period_end > period_start`. `metric_value` is `decimal(14,5)`.

Only `MAE` has a formula in the sources (mean absolute error, computed by AI-072's `rolling_mae`
on the pairs the caller passes). `OVERRIDE_RATE` and `WAIT_TIME` have no written numerator,
denominator or row selection (R9), and `WINDOW_ACCURACY` is DEC-30 TR-11, DEFERRED (OD-16), so no
function here computes them. A caller can still store such a row once its definition is approved;
the scope rules hold for it.

No data is no metric: an empty sample gives no row, never a zero. The module reads nothing; the
caller passes trusted values (AI-074's `part3/trusted.py` is the only read of field events).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Final

from common.db.repository import WorkerRepository
from part3.drift import QUANTUM, rolling_mae

VALUE_LIMIT: Final = Decimal("1e9")  # `decimal(14,5)`: below 10^9 in absolute value


class MetricName(StrEnum):
    """`evaluation_metrics.metric_name`."""

    MAE = "MAE"
    OVERRIDE_RATE = "OVERRIDE_RATE"
    WAIT_TIME = "WAIT_TIME"
    WINDOW_ACCURACY = "WINDOW_ACCURACY"


class DatasetType(StrEnum):
    """`evaluation_metrics.dataset_type`."""

    HOLDOUT = "HOLDOUT"
    ROLLING = "ROLLING"
    PRODUCTION = "PRODUCTION"


MODEL_METRICS: Final = frozenset({MetricName.MAE})  # model version required
SYSTEM_METRICS: Final = frozenset({MetricName.OVERRIDE_RATE, MetricName.WAIT_TIME})  # forbidden


@dataclass(frozen=True)
class EvaluationMetric:
    """One `evaluation_metrics` row. Checks the schema's rules before the database does."""

    metric_name: MetricName
    dataset_type: DatasetType
    metric_value: Decimal
    period_start: datetime
    period_end: datetime
    computed_at: datetime
    model_version_id: int | None = None
    retraining_run_id: int | None = None

    def __post_init__(self) -> None:
        if self.metric_name in MODEL_METRICS and self.model_version_id is None:
            raise ValueError(f"{self.metric_name} needs a model version (chk_em_scope)")
        if self.metric_name in SYSTEM_METRICS and self.model_version_id is not None:
            raise ValueError(f"{self.metric_name} is system-level: no model version (chk_em_scope)")
        for name in ("period_start", "period_end", "computed_at"):
            if getattr(self, name).utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.period_end <= self.period_start:
            raise ValueError("period_end must be after period_start (chk_em_period)")
        if not self.metric_value.is_finite():
            raise ValueError(f"metric_value must be finite: {self.metric_value}")
        rounded = self.metric_value.quantize(QUANTUM)
        if abs(rounded) >= VALUE_LIMIT:
            raise ValueError(f"metric_value does not fit decimal(14,5): {self.metric_value}")
        if rounded != self.metric_value:
            raise ValueError(f"metric_value has more than 5 decimals: {self.metric_value}")

    def row(self) -> dict[str, object]:
        return {
            "model_version_id": self.model_version_id,
            "retraining_run_id": self.retraining_run_id,
            "metric_name": self.metric_name.value,
            "dataset_type": self.dataset_type.value,
            "metric_value": self.metric_value,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "computed_at": self.computed_at,
        }


def mae_metric(
    model_version_id: int,
    actual: Sequence[float],
    predicted: Sequence[float],
    dataset_type: DatasetType,
    period: tuple[datetime, datetime],
    computed_at: datetime,
) -> EvaluationMetric | None:
    """The `MAE` row of one model version over the pairs given, or None when there are none.

    Pairs must be finite and of equal length (`rolling_mae` raises otherwise). The caller chooses
    which pairs belong to the period; the unit is the model's own (hours for M2).
    """
    if len(actual) != len(predicted):
        raise ValueError(f"{len(actual)} actual values but {len(predicted)} predictions")
    if not actual:
        return None
    return EvaluationMetric(
        MetricName.MAE,
        dataset_type,
        rolling_mae(actual, predicted),
        period[0],
        period[1],
        computed_at,
        model_version_id=model_version_id,
    )


def write_metrics(repo: WorkerRepository, rows: Sequence[EvaluationMetric]) -> None:
    """Insert the rows (`w_part3` INSERT on `evaluation_metrics`). The caller commits."""
    if rows:
        repo.insert_many("evaluation_metrics", [m.row() for m in rows])
