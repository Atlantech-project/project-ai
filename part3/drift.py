"""C2 drift monitor (AI-072): PSI per feature and rolling MAE, as `drift_measurements` rows.

Architecture §9 (C2) and UML 3.4. A row is drifted when `metric_value > threshold`, the same
expression the schema stores in the generated `is_drifted`; the Backend sends the `DRIFT_ALERT`
notification from those rows and sets `notified_at` (CT-17 §7). Thresholds come only from the
CT-18 keys `drift_psi_threshold` and `drift_mae_threshold`; their values are DEFERRED in DEC-30
(TR-01, TR-02), so reading them fails until they are seeded. No value is assumed here.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

from common.config import PortSettings
from common.db.repository import WorkerRepository

KEY_PSI_THRESHOLD: Final = "drift_psi_threshold"
KEY_MAE_THRESHOLD: Final = "drift_mae_threshold"
PSI: Final = "PSI"
ROLLING_MAE: Final = "ROLLING_MAE"
BINS: Final = 10  # reference deciles
# Share given to an empty bin so ln(a / e) stays finite; it bounds one bin's PSI term.
EMPTY_BIN_SHARE: Final = 1e-4
QUANTUM: Final = Decimal("0.00001")  # `decimal(14,5)`


@dataclass(frozen=True)
class Thresholds:
    psi: Decimal
    mae: Decimal

    @classmethod
    def from_port_settings(cls, settings: PortSettings) -> Thresholds:
        """Raises `ConfigurationError` while a key is missing (DEC-30 TR-01 / TR-02 deferred)."""
        return cls(settings.get_decimal(KEY_PSI_THRESHOLD), settings.get_decimal(KEY_MAE_THRESHOLD))


@dataclass(frozen=True)
class Measurement:
    """One `drift_measurements` row (without `id`, `is_drifted` and `notified_at`)."""

    model_version_id: int
    metric_type: str
    feature_name: str | None  # PSI only (`chk_dm_feature`)
    metric_value: Decimal
    threshold: Decimal
    measured_at: datetime

    @property
    def is_drifted(self) -> bool:
        return self.metric_value > self.threshold

    def row(self) -> dict[str, object]:
        return {
            "model_version_id": self.model_version_id,
            "metric_type": self.metric_type,
            "feature_name": self.feature_name,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "measured_at": self.measured_at,
        }


def _finite(values: Sequence[float], name: str) -> list[float]:
    out = [float(v) for v in values]
    if not out:
        raise ValueError(f"{name} is empty")
    if not all(math.isfinite(v) for v in out):
        raise ValueError(f"{name} holds a value that is not finite")
    return out


def psi(reference: Sequence[float], current: Sequence[float], bins: int = BINS) -> Decimal:
    """Population stability index of `current` against `reference`.

    Bin edges are the reference quantiles (deciles by default); repeated edges merge, so a
    feature with few distinct values gets fewer bins. PSI = Σ (a − e) · ln(a / e), with an empty
    bin's share raised to `EMPTY_BIN_SHARE`.
    """
    ref = sorted(_finite(reference, "reference"))
    cur = _finite(current, "current")
    if bins < 2:
        raise ValueError("at least two bins are needed")
    edges = sorted({ref[min(len(ref) - 1, (len(ref) * k) // bins)] for k in range(1, bins)})

    def shares(values: Sequence[float]) -> list[float]:
        counts = [0] * (len(edges) + 1)
        for value in values:
            counts[sum(1 for edge in edges if value >= edge)] += 1
        return [max(c / len(values), EMPTY_BIN_SHARE) for c in counts]

    expected, actual = shares(ref), shares(cur)
    total = sum((a - e) * math.log(a / e) for a, e in zip(actual, expected, strict=True))
    return Decimal(repr(total)).quantize(QUANTUM, ROUND_HALF_UP)


def rolling_mae(actual: Sequence[float], predicted: Sequence[float]) -> Decimal:
    """Mean absolute error over the pairs given (the caller chooses the rolling window)."""
    a = _finite(actual, "actual")
    p = _finite(predicted, "predicted")
    if len(a) != len(p):
        raise ValueError(f"{len(a)} actual values but {len(p)} predictions")
    value = sum(abs(x - y) for x, y in zip(a, p, strict=True)) / len(a)
    return Decimal(repr(value)).quantize(QUANTUM, ROUND_HALF_UP)


def measure(
    model_version_id: int,
    features: Mapping[str, tuple[Sequence[float], Sequence[float]]],
    errors: tuple[Sequence[float], Sequence[float]] | None,
    thresholds: Thresholds,
    measured_at: datetime,
) -> tuple[Measurement, ...]:
    """One PSI row per feature (by name) and one ROLLING_MAE row when `errors` is given."""
    if measured_at.utcoffset() is None:
        raise ValueError("measured_at must be timezone-aware")
    if len(features) and any(len(name) > 60 or not name for name in features):
        raise ValueError("feature names must be 1 to 60 characters (`feature_name`)")
    rows = [
        Measurement(model_version_id, PSI, name, psi(ref, cur), thresholds.psi, measured_at)
        for name, (ref, cur) in sorted(features.items())
    ]
    if errors is not None:
        value = rolling_mae(*errors)
        rows.append(
            Measurement(model_version_id, ROLLING_MAE, None, value, thresholds.mae, measured_at)
        )
    return tuple(rows)


def write_measurements(repo: WorkerRepository, rows: Sequence[Measurement]) -> None:
    """Insert the rows (`w_part3` INSERT). The caller commits."""
    repo.insert_many("drift_measurements", [m.row() for m in rows])


def alerts(rows: Sequence[Measurement]) -> tuple[Measurement, ...]:
    """The rows the Backend turns into `DRIFT_ALERT` notifications."""
    return tuple(m for m in rows if m.is_drifted)
