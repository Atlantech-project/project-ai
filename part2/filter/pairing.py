"""B2 before the solve: which berths a request may use, and why the others are out (AI-051).

A pure function over the AI-050 snapshot: no database, clock or solver. Every berth is kept or
removed with all its reasons, so a `NO_FEASIBLE_PLAN` can always say why (Architecture §8.5).

- Per berth: `TERMINAL_COMPATIBILITY`, `BERTH_UNAVAILABLE`, `MAX_LOA`, `MAX_DRAFT` (static: arrival
  draft against water depth; **UKC is not enforced until AI-045**), and Marine Safety Officer
  limits on B2-owned codes, the strictest row per candidate berth (A4's `resolve_limit`).
- Per request: `ENTRY_WINDOW` (no confirmed window), `PILOT_UNAVAILABLE` / `PILOT_RANK_LIMIT`
  (no active pilot, or none whose rank may take this LOA), `TUG_COUNT` (fewer eligible tugs in
  service than AI-054's `n_min`).
- A4-owned codes are not rechecked: Part 1 already applied them with every berth of the terminal,
  so a per-berth recheck could only loosen. Codes owned elsewhere (UKC: AI-045) are skipped.
  Equipment-scoped rows never apply here: the snapshot has no berth-equipment link (blocked).
"""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import replace
from decimal import Decimal
from typing import Final

from common.config import ConfigurationError
from common.db.read_models import RequestWithVessel
from common.units import UnitError, convert, dimension_of
from part1.feasibility import AssessmentScope, Comparator, ConstraintType, applies, resolve_limit
from part1.feasibility import SafetyConstraint as A4Row
from part2.filter.codes import VesselAttribute
from part2.filter.model import (
    BerthResult,
    BindingConstraint,
    Candidates,
    Code,
    FilterContext,
    Kind,
    Removal,
)
from part2.state.availability import BERTH_OUT_OF_SERVICE, TUG_OUT_OF_SERVICE
from part2.state.model import Berth, ConfirmedWindow, Pilot, PilotRankLimit, PortState
from part2.state.model import SafetyConstraint as SnapshotRow
from part2.tugs import FLAG_RULES_UNVALIDATED, TugRequirement

DETAIL_LIMIT: Final = 255  # CT-10 / CT-13 `detail`


def filter_candidates(state: PortState, request_id: int, context: FilterContext) -> Candidates:
    """B2 for one request: every berth of the snapshot, kept or removed with its reasons."""
    request = _request(state, request_id)
    window = confirmed_window(state, request_id)
    request_removals = [
        *_window_removals(window),
        *_pilot_removals(state, request),
        *_tug_removals(state, request, context),
    ]
    if not state.berths:
        request_removals.append(
            Removal(Kind.STRUCTURAL, Code.TERMINAL_COMPATIBILITY, "No berth in the port snapshot")
        )
    safety = _SafetyCheck(state, request, window, context)
    berths = tuple(
        BerthResult(
            berth.id,
            berth.code,
            tuple(sorted([*_berth_removals(berth, request), *safety.removals(berth)], key=_key)),
        )
        for berth in sorted(state.berths, key=lambda b: b.id)
    )
    return Candidates(request_id, tuple(sorted(request_removals, key=_key)), berths)


def binding_constraints(candidates: Candidates) -> tuple[BindingConstraint, ...]:
    """CT-10 `binding_constraints` for a request with no berth left; empty otherwise.

    One item per distinct reason: SAFETY first, then STRUCTURAL, each by code.
    """
    if candidates.feasible:
        return ()
    grouped: dict[tuple[Kind, str], list[Removal]] = defaultdict(list)
    for removal in candidates.request_removals:
        grouped[(removal.kind, removal.code)].append(removal)
    names = {b.berth_id: b.berth_code for b in candidates.berths}
    for berth in candidates.berths:
        for removal in berth.removals:
            grouped[(removal.kind, removal.code)].append(removal)
    items = []
    for (kind, code), removals in sorted(
        grouped.items(), key=lambda item: (item[0][0] is not Kind.SAFETY, item[0][1])
    ):
        request_wide = [r for r in removals if r.berth_id is None]
        if request_wide:
            detail = request_wide[0].detail
        else:
            listed = ", ".join(names[r.berth_id] for r in removals if r.berth_id is not None)
            detail = f"Berths {listed}: {removals[0].detail}"
        items.append(BindingConstraint(kind, code, truncate(detail)))
    return tuple(items)


def truncate(text: str) -> str:
    """At most `DETAIL_LIMIT` characters (CT-10 `detail`)."""
    return text if len(text) <= DETAIL_LIMIT else text[: DETAIL_LIMIT - 1] + "…"


def confirmed_window(state: PortState, request_id: int) -> ConfirmedWindow | None:
    windows = [w for w in state.confirmed_windows if w.berthing_request_id == request_id]
    if len(windows) > 1:
        raise ValueError(f"request {request_id} has {len(windows)} confirmed windows")
    return windows[0] if windows else None


def rank_allows(pilot: Pilot, loa: Decimal, limits: Iterable[PilotRankLimit]) -> bool:
    """The pilot's rank may take this LOA. A rank with no `pilot_rank_limits` row may not."""
    limit = next((row for row in limits if row.pilot_rank == pilot.rank), None)
    if limit is None:
        return False
    return limit.max_vessel_loa is None or loa <= limit.max_vessel_loa


def tug_requirement(context: FilterContext, request_id: int) -> TugRequirement:
    try:
        return context.tug_requirements[request_id]
    except KeyError:
        raise ConfigurationError(f"no tug requirement (AI-054) for request {request_id}") from None


def tug_count_detail(requirement: TugRequirement, have: int, what: str) -> str:
    """The TUG_COUNT detail; says so when AI-054's rules are not APPROVED (DEC-20 interim)."""
    unvalidated = FLAG_RULES_UNVALIDATED in requirement.flags
    note = " (unvalidated: DEC-20 interim tug rules)" if unvalidated else ""
    return f"{have} eligible {what}, {requirement.n_min} required{note}"


def _key(removal: Removal) -> tuple[str, str]:
    return (removal.kind.value, removal.code)


def _request(state: PortState, request_id: int) -> RequestWithVessel:
    for request in state.requests:
        if request.request_id == request_id:
            return request
    raise KeyError(f"request {request_id} is not in the port snapshot")


def _window_removals(window: ConfirmedWindow | None) -> list[Removal]:
    if window is not None:
        return []
    return [Removal(Kind.STRUCTURAL, Code.ENTRY_WINDOW, "No confirmed entry window (Part 1)")]


def _pilot_removals(state: PortState, request: RequestWithVessel) -> list[Removal]:
    active = [p for p in state.pilots if p.is_active and p.has_active_pilot_role]
    if not active:
        return [Removal(Kind.STRUCTURAL, Code.PILOT_UNAVAILABLE, "No active pilot")]
    if not any(rank_allows(p, request.loa, state.pilot_rank_limits) for p in active):
        detail = f"No active pilot's rank may pilot LOA {request.loa} m"
        return [Removal(Kind.STRUCTURAL, Code.PILOT_RANK_LIMIT, detail)]
    return []


def _tug_removals(
    state: PortState, request: RequestWithVessel, context: FilterContext
) -> list[Removal]:
    requirement = tug_requirement(context, request.request_id)
    in_service = sum(
        1
        for tug in state.tugs
        if tug.id in requirement.eligible_tugs and tug.status not in TUG_OUT_OF_SERVICE
    )
    if in_service >= requirement.n_min:
        return []
    detail = tug_count_detail(requirement, in_service, "tugs in service")
    return [Removal(Kind.STRUCTURAL, Code.TUG_COUNT, detail)]


def _berth_removals(berth: Berth, request: RequestWithVessel) -> list[Removal]:
    def out(code: Code, detail: str) -> Removal:
        return Removal(Kind.STRUCTURAL, code, detail, berth.id)

    removals = []
    if request.requested_terminal_id not in berth.terminal_ids:
        removals.append(
            out(
                Code.TERMINAL_COMPATIBILITY,
                f"Berth {berth.code} is not allowed for terminal {request.requested_terminal_id}",
            )
        )
    if berth.status in BERTH_OUT_OF_SERVICE:
        removals.append(out(Code.BERTH_UNAVAILABLE, f"Berth {berth.code} is {berth.status}"))
    if request.loa > berth.max_vessel_loa:
        removals.append(
            out(
                Code.MAX_LOA,
                f"LOA {request.loa} m exceeds berth {berth.code} limit {berth.max_vessel_loa} m",
            )
        )
    if request.arrival_draft > berth.water_depth:
        removals.append(
            out(
                Code.MAX_DRAFT,
                f"Arrival draft {request.arrival_draft} m exceeds berth {berth.code} depth "
                f"{berth.water_depth} m",
            )
        )
    return removals


class _SafetyCheck:
    """Marine Safety Officer limits on B2-owned codes, per candidate berth, over the window."""

    def __init__(
        self,
        state: PortState,
        request: RequestWithVessel,
        window: ConfirmedWindow | None,
        context: FilterContext,
    ) -> None:
        self._request = request
        self._window = window
        self._checks: list[tuple[ConstraintType, VesselAttribute, tuple[A4Row, ...]]] = []
        self._imdg = frozenset(
            e.imdg_class
            for e in state.manifest_entries
            if e.berthing_request_id == request.request_id and e.imdg_class is not None
        )
        self._vessel_type_id = context.vessel_type_ids.get(request.vessel_type_code)
        if window is None:
            return  # ENTRY_WINDOW already removes every berth
        types = {t.id: t for t in context.constraint_types}
        rows_by_type: dict[int, list[A4Row]] = defaultdict(list)
        for row in state.safety_constraints:
            if row.constraint_type_id not in types:
                raise ConfigurationError(
                    f"safety constraint {row.id} has unknown constraint type "
                    f"{row.constraint_type_id}"
                )
            rows_by_type[row.constraint_type_id].append(_a4_row(row))
        for type_id, rows in sorted(rows_by_type.items()):
            ctype = types[type_id]
            owner = context.registry.owner(ctype.code)
            if owner == "B2":
                attribute = context.registry.b2[ctype.code]
                _require_same_dimension(ctype, attribute)
                self._checks.append((ctype, attribute, tuple(rows)))
            elif owner is None and any(self._applies_during(row, window) for row in rows):
                raise ConfigurationError(
                    f"constraint type {ctype.code} is checked by neither B2 nor A4 and owned by "
                    "no other component; add it to the code lists",
                    keys=(ctype.code,),
                )
        self._checks.sort(key=lambda check: check[0].code)
        if self._checks and self._vessel_type_id is None:
            raise ConfigurationError(
                f"no vessel type id for {request.vessel_type_code!r}",
                keys=(request.vessel_type_code,),
            )

    def removals(self, berth: Berth) -> list[Removal]:
        window = self._window
        if not self._checks or self._vessel_type_id is None or window is None:
            return []
        scope = AssessmentScope(
            terminal_id=self._request.requested_terminal_id,
            vessel_type_id=self._vessel_type_id,
            berth_id=berth.id,
            imdg_classes=self._imdg,
        )
        removals = []
        for ctype, attribute, rows in self._checks:
            failed = self._first_failure(ctype, attribute, rows, scope, window)
            if failed is not None:
                value = getattr(self._request, attribute.value)
                detail = (
                    f"{attribute.value} {value} {attribute.unit} at berth {berth.code} breaks "
                    f"limit {failed.value} {ctype.unit} (safety constraint {failed.id})"
                )
                removals.append(Removal(Kind.SAFETY, ctype.code, truncate(detail), berth.id))
        return removals

    def _first_failure(
        self,
        ctype: ConstraintType,
        attribute: VesselAttribute,
        rows: Sequence[A4Row],
        scope: AssessmentScope,
        window: ConfirmedWindow,
    ) -> A4Row | None:
        """The strictest row the attribute breaks at any moment of the window, if any.

        The strictest row only changes where a row starts or ends, so those moments (and the window
        start) are the only ones to check; the window is half-open `[start, end)`.
        """
        start, end = window.start, window.end
        boundaries = {
            moment
            for row in rows
            for moment in (row.active_from, row.active_to)
            if moment is not None and start < moment < end
        }
        value = Decimal(getattr(self._request, attribute.value))
        for moment in sorted({start} | boundaries):
            row = resolve_limit(rows, ctype, scope, moment)
            if row is not None and not _passes(value, attribute.unit, row.value, ctype):
                return row
        return None

    def _applies_during(self, row: A4Row, window: ConfirmedWindow) -> bool:
        """The row applies to the request, for some berth, at some moment of the window.

        With no vessel type id the row's vessel-type scope is ignored, so it counts as a match.
        """
        moment = max(window.start, row.active_from)
        if moment >= window.end:
            return False
        probe = row if self._vessel_type_id is not None else replace(row, vessel_type_id=None)
        scope = AssessmentScope(
            terminal_id=self._request.requested_terminal_id,
            vessel_type_id=self._vessel_type_id if self._vessel_type_id is not None else 0,
            berth_id=None,
            imdg_classes=self._imdg,
        )
        return applies(probe, scope, moment)


def _passes(value: Decimal, unit: str, limit: Decimal, ctype: ConstraintType) -> bool:
    """Equal to the limit passes; no tolerance (I-6)."""
    if unit == ctype.unit:
        compared: Decimal | float = value
        bound: Decimal | float = limit
    else:
        compared = convert(float(value), unit, ctype.unit)
        bound = float(limit)
    if ctype.comparator is Comparator.MAX_ALLOWED:
        return compared <= bound
    return compared >= bound


def _require_same_dimension(ctype: ConstraintType, attribute: VesselAttribute) -> None:
    try:
        same = dimension_of(ctype.unit) is dimension_of(attribute.unit)
    except UnitError as error:
        raise ConfigurationError(f"{ctype.code}: {error}", keys=(ctype.code,)) from error
    if not same:
        raise ConfigurationError(
            f"{ctype.code} is in {ctype.unit} but {attribute.value} is in {attribute.unit}",
            keys=(ctype.code,),
        )


def _a4_row(row: SnapshotRow) -> A4Row:
    """An AI-050 `SafetyConstraint` as A4's row type (the same columns)."""
    return A4Row(
        id=row.id,
        constraint_type_id=row.constraint_type_id,
        value=row.value,
        active_from=row.active_from,
        active_to=row.active_to,
        terminal_id=row.terminal_id,
        berth_id=row.berth_id,
        vessel_type_id=row.vessel_type_id,
        imdg_class=row.imdg_class,
        equipment_category_id=row.equipment_category_id,
    )
