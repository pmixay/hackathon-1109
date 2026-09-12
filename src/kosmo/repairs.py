from __future__ import annotations

from dataclasses import dataclass

from .calc import PortfolioMetrics, calculate_all_scenarios
from .case import Case
from .validation import require_valid_selection


@dataclass(frozen=True)
class Repair:
    change: str
    description: str
    selection: tuple
    metrics: PortfolioMetrics
    feasible: dict
    delta_c0: float
    delta_opex: float
    delta_vpub: float
    delta_cash: float


def mode_changes(case: Case, pairs) -> list:
    changes = []
    for index, (lot_id, mode_id) in enumerate(pairs):
        for alternative in case.modes:
            if alternative == mode_id:
                continue
            updated = list(pairs)
            updated[index] = (lot_id, alternative)
            changes.append(("mode", f"{lot_id}: режим {mode_id} → {alternative}", tuple(updated)))
    return changes


def lot_swaps(case: Case, pairs) -> list:
    used = {lot_id for lot_id, _ in pairs}
    swaps = []
    for index, (lot_id, mode_id) in enumerate(pairs):
        for alternative in case.lots:
            if alternative in used:
                continue
            for mode in case.modes:
                updated = list(pairs)
                updated[index] = (alternative, mode)
                swaps.append(("lot", f"{lot_id}/{mode_id} → {alternative}/{mode}", tuple(updated)))
    return swaps


def single_step_repairs(case: Case, selection, scenario_id: str = "STRESS") -> list:
    pairs = require_valid_selection(case, selection, scenario_id)
    original = calculate_all_scenarios(case, pairs)[scenario_id].metrics
    repairs = []
    for change, description, updated in mode_changes(case, pairs) + lot_swaps(case, pairs):
        results = calculate_all_scenarios(case, updated)
        if not results[scenario_id].feasible:
            continue
        metrics = results[scenario_id].metrics
        repairs.append(Repair(
            change=change,
            description=description,
            selection=updated,
            metrics=metrics,
            feasible={name: result.feasible for name, result in results.items()},
            delta_c0=metrics.c0 - original.c0,
            delta_opex=metrics.opex - original.opex,
            delta_vpub=metrics.vpub - original.vpub,
            delta_cash=metrics.cash - original.cash,
        ))
    repairs.sort(key=lambda repair: (-repair.metrics.vpub, repair.metrics.c0, repair.description))
    return repairs
