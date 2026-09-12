from __future__ import annotations

import math
from dataclasses import dataclass

from .case import Constraints, Scenario

TOLERANCE = 1e-9

LABELS = {
    "exact_lot_count": "Ровно четыре уникальных лота",
    "territorial_archetypes": "Территориальные архетипы среди нефедеральных лотов",
    "capability_groups": "Разные группы космических возможностей",
    "public_core_lots": "Лоты в режиме с public core",
    "c0_limit": "Стартовые затраты портфеля",
    "opex_limit": "Годовые эксплуатационные расходы портфеля",
    "vpub_floor": "Годовая общественная ценность портфеля",
    "kcash_floor": "Покрытие OPEX денежными поступлениями",
    "t_rep_floor": "Средний t_rep по портфелю",
}

UNITS = {
    "exact_lot_count": "шт.",
    "territorial_archetypes": "шт.",
    "capability_groups": "шт.",
    "public_core_lots": "шт.",
    "c0_limit": "млн руб.",
    "opex_limit": "млн руб./год",
    "vpub_floor": "млн руб./год",
    "kcash_floor": "доля",
    "t_rep_floor": "индекс",
}


@dataclass(frozen=True)
class Check:
    code: str
    label: str
    metric: str
    operator: str
    threshold: float
    actual: float
    unit: str
    scope: str
    passed: bool
    margin: float

    @property
    def status(self) -> str:
        return "выполнено" if self.passed else "нарушено"

    def describe(self) -> str:
        return f"{self.label}: {self.metric} = {format_value(self.actual)} {self.operator} {format_value(self.threshold)} {self.unit} — {self.status}"


def format_value(value: float) -> str:
    if isinstance(value, float) and math.isnan(value):
        return "n/a"
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def build_check(code: str, metric: str, operator: str, threshold: float, actual: float, scope: str) -> Check:
    if operator == "==":
        passed = actual == threshold
        margin = -abs(actual - threshold)
    elif operator == ">=":
        passed = actual >= threshold - TOLERANCE
        margin = actual - threshold
    elif operator == "<=":
        passed = actual <= threshold + TOLERANCE
        margin = threshold - actual
    else:
        raise ValueError(f"unsupported operator {operator!r}")
    return Check(
        code=code,
        label=LABELS[code],
        metric=metric,
        operator=operator,
        threshold=float(threshold),
        actual=float(actual),
        unit=UNITS[code],
        scope=scope,
        passed=bool(passed),
        margin=float(margin),
    )


def run_checks(metrics, constraints: Constraints, scenario: Scenario) -> tuple:
    return (
        build_check("exact_lot_count", "selected_lots", "==", constraints.selected_lots_exactly, metrics.selected_lots, "common"),
        build_check("territorial_archetypes", "territorial_archetypes", ">=", constraints.min_territorial_archetypes, metrics.territorial_archetypes, "common"),
        build_check("capability_groups", "capability_groups", ">=", constraints.min_capability_groups, metrics.capability_groups, "common"),
        build_check("public_core_lots", "public_core_lots", ">=", constraints.min_public_core_lots, metrics.public_core_lots, "common"),
        build_check("c0_limit", "c0", "<=", scenario.c0_max, metrics.c0, scenario.scenario_id),
        build_check("opex_limit", "opex", "<=", constraints.opex_max, metrics.opex, "common"),
        build_check("vpub_floor", "vpub", ">=", constraints.vpub_min, metrics.vpub, "common"),
        build_check("kcash_floor", "kcash", ">=", constraints.kcash_min, metrics.kcash, "common"),
        build_check("t_rep_floor", "t_rep", ">=", constraints.t_rep_min, metrics.t_rep, "common"),
    )
