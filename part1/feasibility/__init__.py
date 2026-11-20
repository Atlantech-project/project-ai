"""A4 threshold feasibility (AI-044): environmental limits per time step, strictest wins."""

from part1.feasibility.evaluate import assess, blocked_periods
from part1.feasibility.model import (
    AssessmentScope,
    BlockedPeriod,
    Category,
    Comparator,
    ConstraintType,
    EnvironmentStep,
    Failure,
    Reason,
    SafetyConstraint,
    Series,
    SeriesUnits,
    StepResult,
)
from part1.feasibility.scope import applies, resolve_limit
from part1.feasibility.series import DEFAULT_REGISTRY, CodeRegistry

__all__ = [
    "DEFAULT_REGISTRY",
    "AssessmentScope",
    "BlockedPeriod",
    "Category",
    "CodeRegistry",
    "Comparator",
    "ConstraintType",
    "EnvironmentStep",
    "Failure",
    "Reason",
    "SafetyConstraint",
    "Series",
    "SeriesUnits",
    "StepResult",
    "applies",
    "assess",
    "blocked_periods",
    "resolve_limit",
]
