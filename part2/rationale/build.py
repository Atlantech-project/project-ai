"""B6 rationale per option (AI-057): factor rows, template link and placeholder values.

Inputs are AI-056's `SolveOutcome` and the AI-050 snapshot; the module reads and writes nothing.
AI-058 resolves the codes to `objective_terms` / `constraint_types` ids and writes the rows.

- **AI options:** one `OBJECTIVE_TERM` factor per term the solve scored (DEC-23: `WAITING_TIME`,
  `RESOURCE_COST`). `factor_value` is the term's share of `objective_score`: normalised value ×
  weight × 1000 (CT-18 §5), 4 decimals. Largest share first.
- **FIFO options:** no rule says which factors explain a plan made by arrival order (R11 (a)).
  `fifo_factors` returns none and stays separate, so the rule can be added there alone.
- **Template:** which code goes with which option is not defined yet (no templates, INT-Q4). The
  caller passes a `TemplateSelector`; the default selects none, so the link and the parameters
  stay NULL.
- **Isolation:** every value comes from the option's own request, berth and confirmed window.
  Nothing from another request, terminal, manifest, stowage, yard or cost is read.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Final

from part2.filter import Option
from part2.outcomes import SOURCE_AI, SOURCE_FIFO, PlannedOption, RequestOutcome, SolveOutcome
from part2.rationale.templates import (
    EMPTY_CATALOG,
    RationaleTemplate,
    TemplateCatalog,
    TemplateError,
)
from part2.solver.model import SCORE_SCALE, TermValue
from part2.state.model import PortState

FACTOR_QUANTUM: Final = Decimal("0.0001")  # `factor_value` decimal(14,4)
MINUTE: Final = timedelta(minutes=1)

# The CT-18 §6 placeholders the worker can fill for a berth option today. The others have no
# source yet: `terminal` (the snapshot carries terminal ids, not names), `delta_minutes` (no
# definition), `constraint` · `value` · `limit` · `unit` (an option has no binding constraint).
OPTION_PLACEHOLDERS: Final = frozenset(
    {"vessel", "berth", "etb", "waiting_minutes", "tug_count", "window_start", "window_end"}
)


class FactorType(StrEnum):
    """`recommendation_rationale_factors.factor_type`."""

    CONSTRAINT = "CONSTRAINT"
    OBJECTIVE_TERM = "OBJECTIVE_TERM"


class RationaleError(ValueError):
    """The outcome and the snapshot disagree (an option without its request, berth or window)."""


@dataclass(frozen=True)
class Factor:
    """One `recommendation_rationale_factors` row before ids: `code` is an `objective_terms.code`
    or a `constraint_types.code`, by `factor_type` (chk_rrf_kind)."""

    factor_type: FactorType
    code: str
    factor_value: Decimal | None
    display_order: int


@dataclass(frozen=True)
class OptionRationale:
    """The B6 output of one option: factor rows, and the template link with its values."""

    request_id: int
    rank: int
    factors: tuple[Factor, ...]
    template: RationaleTemplate | None  # `rationale_template_id`; None until INT-Q4
    params: dict[str, object] | None  # `rationale_params`; None exactly when `template` is

    @property
    def rationale_template_id(self) -> int | None:
        return None if self.template is None else self.template.id


TemplateSelector = Callable[[str, RequestOutcome, PlannedOption], str | None]
"""(`recommendations.source`, the request's outcome, the option) → a template code, or None."""


def no_template(_source: str, _request: RequestOutcome, _option: PlannedOption) -> str | None:
    """The selector until templates and their selection rule exist (INT-Q4)."""
    return None


def objective_factors(terms: tuple[TermValue, ...]) -> tuple[Factor, ...]:
    """`OBJECTIVE_TERM` factors of an AI option, largest share of the score first, then by code."""
    shares = [
        (t.code, (SCORE_SCALE * t.normalised * t.weight).quantize(FACTOR_QUANTUM, ROUND_HALF_UP))
        for t in terms
    ]
    shares.sort(key=lambda share: (-share[1], share[0]))
    return tuple(
        Factor(FactorType.OBJECTIVE_TERM, code, value, order)
        for order, (code, value) in enumerate(shares, start=1)
    )


def fifo_factors(_option: PlannedOption) -> tuple[Factor, ...]:
    """Factors of a FIFO option: none until R11 (a) is decided. Kept apart from AI options."""
    return ()


def option_params(state: PortState, option: Option) -> dict[str, object]:
    """Every placeholder of `OPTION_PLACEHOLDERS`, from this option's own request only.

    - `etb`, `window_start`, `window_end`: UTC, ISO 8601 with `Z` (the Backend converts, CT-18).
    - `waiting_minutes`: whole minutes from the confirmed window's start to the option start, the
      minutes AI-055's `WAITING_TIME` term counts.
    - `tug_count`: tugs assigned to the option.
    """
    request = next((r for r in state.requests if r.request_id == option.request_id), None)
    berth = next((b for b in state.berths if b.id == option.berth_id), None)
    windows = [w for w in state.confirmed_windows if w.berthing_request_id == option.request_id]
    if request is None or berth is None or len(windows) != 1:
        raise RationaleError(
            f"option of request {option.request_id} at berth {option.berth_id}: the snapshot has "
            f"request={request is not None}, berth={berth is not None}, windows={len(windows)}"
        )
    window = windows[0]
    if option.start < window.start:
        raise RationaleError(f"option of request {option.request_id} starts before its window")
    return {
        "vessel": request.vessel_name,
        "berth": berth.code,
        "etb": _utc(option.start),
        "waiting_minutes": (option.start - window.start) // MINUTE,
        "tug_count": len(option.tug_ids),
        "window_start": _utc(window.start),
        "window_end": _utc(window.end),
    }


def build_rationales(
    state: PortState,
    outcome: SolveOutcome,
    catalog: TemplateCatalog = EMPTY_CATALOG,
    select: TemplateSelector = no_template,
) -> tuple[OptionRationale, ...]:
    """The rationale of every option of the outcome, by request id then rank."""
    built = []
    for request in sorted(outcome.requests, key=lambda r: r.request_id):
        for planned in request.options:
            factors = _factors(outcome.source, planned)
            code = select(outcome.source, request, planned)
            template = None if code is None else catalog.require(code)
            params = None if template is None else _params(state, planned, template)
            built.append(
                OptionRationale(request.request_id, planned.rank, factors, template, params)
            )
    return tuple(built)


def _factors(source: str, planned: PlannedOption) -> tuple[Factor, ...]:
    if source == SOURCE_FIFO:
        return fifo_factors(planned)
    if source != SOURCE_AI:
        raise RationaleError(f"unknown recommendation source {source!r}")
    if not planned.terms:
        raise RationaleError(
            f"AI option {planned.rank} of request {planned.option.request_id} "
            "has no objective terms"
        )
    return objective_factors(planned.terms)


def _params(
    state: PortState, planned: PlannedOption, template: RationaleTemplate
) -> dict[str, object]:
    unsupported = [name for name in template.placeholders if name not in OPTION_PLACEHOLDERS]
    if unsupported:
        raise TemplateError(
            f"template {template.code} v{template.version} uses {', '.join(unsupported)}, "
            "which the worker cannot fill for a berth option"
        )
    available = option_params(state, planned.option)
    return {name: available[name] for name in template.placeholders}


def _utc(value: datetime) -> str:
    if value.utcoffset() is None:
        raise RationaleError(f"naive datetime in the snapshot: {value!r}")
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
