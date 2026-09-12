from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations, product

from .calc import PortfolioMetrics, calculate_all_scenarios
from .case import Case


@dataclass(frozen=True)
class EnumeratedPortfolio:
    lots: tuple
    modes: tuple
    metrics: PortfolioMetrics
    feasible: dict
    failed: dict


def enumerate_portfolios(case: Case, mode_ids=None) -> list:
    mode_ids = tuple(mode_ids) if mode_ids is not None else tuple(case.modes)
    size = case.constraints.selected_lots_exactly
    portfolios = []
    for lots in combinations(tuple(case.lots), size):
        for modes in product(mode_ids, repeat=size):
            results = calculate_all_scenarios(case, tuple(zip(lots, modes)))
            first = next(iter(results.values()))
            portfolios.append(EnumeratedPortfolio(
                lots=lots,
                modes=modes,
                metrics=first.metrics,
                feasible={scenario_id: result.feasible for scenario_id, result in results.items()},
                failed={scenario_id: result.failed_checks for scenario_id, result in results.items()},
            ))
    return portfolios


def feasible_in(portfolios, scenario_id: str) -> list:
    return [portfolio for portfolio in portfolios if portfolio.feasible[scenario_id]]


def failure_counts(portfolios, scenario_id: str) -> Counter:
    counter = Counter()
    for portfolio in portfolios:
        counter.update(portfolio.failed[scenario_id])
    return counter


def lot_frequency(portfolios) -> Counter:
    counter = Counter()
    for portfolio in portfolios:
        counter.update(portfolio.lots)
    return counter


def lot_set_summary(portfolios, scenario_ids) -> list:
    groups = {}
    for portfolio in portfolios:
        groups.setdefault(portfolio.lots, []).append(portfolio)
    summary = []
    for lots, members in groups.items():
        row = {"lots": lots, "assignments": len(members)}
        for scenario_id in scenario_ids:
            admissible = [member for member in members if member.feasible[scenario_id]]
            row[scenario_id] = len(admissible)
            row[f"vpub_max_{scenario_id}"] = max(member.metrics.vpub for member in admissible) if admissible else None
            row[f"c0_min_{scenario_id}"] = min(member.metrics.c0 for member in admissible) if admissible else None
        summary.append(row)
    first = scenario_ids[0]
    summary.sort(key=lambda row: tuple(-row[scenario_id] for scenario_id in scenario_ids) + (-(row[f"vpub_max_{first}"] or 0.0),))
    return summary
