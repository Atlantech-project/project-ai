"""B5 CP-SAT joint allocation with ranked options (AI-055)."""

from part2.solver.cpsat import FLAG_ALTERNATIVES_TIME_LIMIT, SolverInvariantError, solve
from part2.solver.model import (
    TERM_RESOURCE_COST,
    TERM_WAITING_TIME,
    Pin,
    RankedOption,
    RequestSolution,
    SolveResult,
    SolverSettings,
    SolveStatus,
    TermValue,
    Unscheduled,
)

__all__ = [
    "FLAG_ALTERNATIVES_TIME_LIMIT",
    "TERM_RESOURCE_COST",
    "TERM_WAITING_TIME",
    "Pin",
    "RankedOption",
    "RequestSolution",
    "SolveResult",
    "SolveStatus",
    "SolverInvariantError",
    "SolverSettings",
    "TermValue",
    "Unscheduled",
    "solve",
]
