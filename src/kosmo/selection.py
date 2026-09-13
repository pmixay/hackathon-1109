from __future__ import annotations

import json
import math
from dataclasses import dataclass, replace
from pathlib import Path

from .calc import coverage, evaluate
from .case import Case
from .checks import run_checks, run_team_checks
from .validation import InputError, require_valid_selection

DIRECTIONS = ("max", "min")
OPERATORS = ("==", "<=", ">=")
MARGIN_PREFIX = "margin:"


class WeightsError(InputError):
    kind = "invalid_weights"


@dataclass(frozen=True)
class Criterion:
    key: str
    direction: str
    weight: float
    rationale: str = ""


@dataclass(frozen=True)
class Gate:
    code: str
    metric: str
    operator: str
    threshold: float
    label: str = ""
    unit: str = ""
    rationale: str = ""


@dataclass(frozen=True)
class SelectionModel:
    method: str
    feasibility_scenario: str
    criteria: tuple
    gates: tuple = ()
    gates_filter: bool = False

    @property
    def total_weight(self) -> float:
        return sum(criterion.weight for criterion in self.criteria)

    def with_weight(self, key: str, weight: float) -> SelectionModel:
        criteria = tuple(replace(c, weight=weight) if c.key == key else c for c in self.criteria)
        return replace(self, criteria=criteria)


@dataclass(frozen=True)
class ScoredVariant:
    name: str
    feasible: bool
    gates: tuple
    admitted: bool
    values: dict
    normalized: dict
    score: float | None
    rank: int | None


@dataclass(frozen=True)
class WeightSensitivity:
    key: str
    factor: float
    weight: float
    leader: str | None
    leader_changed: bool
    ranking: tuple


@dataclass(frozen=True)
class ParameterSensitivity:
    parameter: str
    factor: float
    scenario: str
    feasible: bool
    failed_checks: tuple


def parse_selection_model(raw) -> SelectionModel:
    if not isinstance(raw, dict):
        raise WeightsError([f"описание модели выбора должно быть объектом JSON, получено {type(raw).__name__}"])
    items = raw.get("criteria")
    if not isinstance(items, list):
        raise WeightsError(["criteria: ожидается список критериев"])
    problems = []
    criteria = []
    seen = set()
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            problems.append(f"критерий {index}: ожидается объект с полями key, direction, weight")
            continue
        key = str(item.get("key") or "").strip()
        direction = str(item.get("direction") or "").strip()
        weight = item.get("weight")
        if not key:
            problems.append(f"критерий {index}: пустой key")
        elif key in seen:
            problems.append(f"критерий {index}: key {key} повторяется")
        seen.add(key)
        if direction not in DIRECTIONS:
            problems.append(f"критерий {key or index}: direction должен быть max или min, получено {direction!r}")
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(weight) or weight < 0:
            problems.append(f"критерий {key or index}: weight должен быть неотрицательным числом, получено {weight!r}")
            weight = 0.0
        criteria.append(Criterion(key=key, direction=direction, weight=float(weight), rationale=str(item.get("rationale") or "")))
    if not criteria:
        problems.append("список критериев пуст")
    elif sum(c.weight for c in criteria) <= 0:
        problems.append("сумма весов должна быть больше нуля")
    gates = parse_gates(raw.get("gates", []), problems)
    gates_filter = raw.get("gates_filter", False)
    if not isinstance(gates_filter, bool):
        problems.append(f"gates_filter: ожидается true или false, получено {gates_filter!r}")
        gates_filter = False
    if problems:
        raise WeightsError(problems)
    return SelectionModel(
        method=str(raw.get("method") or "weighted_sum_minmax"),
        feasibility_scenario=str(raw.get("feasibility_scenario") or "BASE"),
        criteria=tuple(criteria),
        gates=gates,
        gates_filter=gates_filter,
    )


def parse_gates(items, problems: list) -> tuple:
    if items is None:
        return ()
    if not isinstance(items, list):
        problems.append("gates: ожидается список проверок команды")
        return ()
    gates = []
    seen = set()
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            problems.append(f"проверка команды {index}: ожидается объект с полями code, metric, operator, threshold")
            continue
        code = str(item.get("code") or "").strip()
        metric = str(item.get("metric") or "").strip()
        operator = str(item.get("operator") or "").strip()
        threshold = item.get("threshold")
        if not code:
            problems.append(f"проверка команды {index}: пустой code")
        elif code in seen:
            problems.append(f"проверка команды {index}: code {code} повторяется")
        seen.add(code)
        if not metric:
            problems.append(f"проверка команды {code or index}: пустой metric")
        if operator not in OPERATORS:
            problems.append(f"проверка команды {code or index}: operator должен быть одним из {', '.join(OPERATORS)}, получено {operator!r}")
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(threshold):
            problems.append(f"проверка команды {code or index}: threshold должен быть числом, получено {threshold!r}")
            threshold = 0.0
        gates.append(Gate(
            code=code,
            metric=metric,
            operator=operator,
            threshold=float(threshold),
            label=str(item.get("label") or code),
            unit=str(item.get("unit") or ""),
            rationale=str(item.get("rationale") or ""),
        ))
    return tuple(gates)


def load_selection_model(path) -> SelectionModel:
    return parse_selection_model(json.loads(Path(path).read_text(encoding="utf-8")))


def criterion_value(results: dict, key: str, base_scenario: str) -> float:
    metrics = results[base_scenario].metrics
    if hasattr(metrics, key):
        return float(getattr(metrics, key))
    if key.startswith(MARGIN_PREFIX):
        _, scenario_id, code = key.split(":", 2)
        for check in results[scenario_id].checks:
            if check.code == code:
                return float(check.margin)
        raise KeyError(f"unknown check {code!r} for criterion {key!r}")
    raise KeyError(f"unknown criterion {key!r}")


def normalize(values: dict, direction: str) -> dict:
    if not values:
        return {}
    low, high = min(values.values()), max(values.values())
    if math.isclose(low, high):
        return {name: 1.0 for name in values}
    normalized = {name: (value - low) / (high - low) for name, value in values.items()}
    if direction == "min":
        normalized = {name: 1.0 - value for name, value in normalized.items()}
    return normalized


# Фронт Парето: недоминируемые комбинации по (ценность выше, c0 ниже, покрытие OPEX выше).
# Это отбор, а не новая формула: сравниваются метрики, уже посчитанные calculate().
PARETO_CRITERIA = (("vpub", "max"), ("c0", "min"), ("kcash", "max"))


def dominates(better, worse, criteria=PARETO_CRITERIA) -> bool:
    """better доминирует worse: не хуже ни по одному показателю и строго лучше хотя бы по одному."""
    strict = False
    for key, direction in criteria:
        a, b = float(getattr(better, key)), float(getattr(worse, key))
        if direction == "min":
            a, b = -a, -b
        if a < b and not math.isclose(a, b):
            return False
        if a > b and not math.isclose(a, b):
            strict = True
    return strict


def pareto_front(metrics: dict, criteria=PARETO_CRITERIA) -> tuple:
    """Имена комбинаций на фронте Парето. На вход — {имя: PortfolioMetrics} только допустимых вариантов."""
    return tuple(sorted(
        name for name, value in metrics.items()
        if not any(dominates(other, value, criteria) for other_name, other in metrics.items() if other_name != name)
    ))


def team_checks(results: dict, model: SelectionModel) -> tuple:
    return run_team_checks(results[model.feasibility_scenario].metrics, model.gates)


def admitted(results: dict, model: SelectionModel) -> bool:
    if not results[model.feasibility_scenario].feasible:
        return False
    return not model.gates_filter or all(check.passed for check in team_checks(results, model))


def score_variants(evaluated: dict, model: SelectionModel) -> list:
    scenario = model.feasibility_scenario
    candidates = [name for name, results in evaluated.items() if admitted(results, model)]
    values = {c.key: {name: criterion_value(evaluated[name], c.key, scenario) for name in candidates} for c in model.criteria}
    normalized = {c.key: normalize(values[c.key], c.direction) for c in model.criteria}
    total = model.total_weight
    scores = {name: sum(c.weight * normalized[c.key][name] for c in model.criteria) / total for name in candidates}
    order = sorted(candidates, key=lambda name: (-scores[name], name))
    ranks = {name: position for position, name in enumerate(order, start=1)}
    scored = []
    for name, results in evaluated.items():
        ranked = name in ranks
        scored.append(ScoredVariant(
            name=name,
            feasible=results[scenario].feasible,
            gates=team_checks(results, model),
            admitted=ranked,
            values={c.key: criterion_value(results, c.key, scenario) for c in model.criteria},
            normalized={c.key: normalized[c.key][name] for c in model.criteria} if ranked else {},
            score=scores[name] if ranked else None,
            rank=ranks.get(name),
        ))
    scored.sort(key=lambda item: (item.rank is None, item.rank or 0, item.name))
    return scored


def leader_of(scored) -> str | None:
    for item in scored:
        if item.rank == 1:
            return item.name
    return None


def ranking_of(scored) -> tuple:
    return tuple(item.name for item in scored if item.rank is not None)


def weight_sensitivity(evaluated: dict, model: SelectionModel, delta: float = 0.2) -> list:
    baseline = leader_of(score_variants(evaluated, model))
    rows = []
    for criterion in model.criteria:
        for factor in (1.0 - delta, 1.0 + delta):
            weight = criterion.weight * factor
            scored = score_variants(evaluated, model.with_weight(criterion.key, weight))
            leader = leader_of(scored)
            rows.append(WeightSensitivity(
                key=criterion.key,
                factor=factor,
                weight=weight,
                leader=leader,
                leader_changed=leader != baseline,
                ranking=ranking_of(scored),
            ))
    return rows


def perturb(metrics, parameter: str, factor: float):
    if parameter == "vpub":
        return replace(metrics, vpub=metrics.vpub * factor)
    if parameter == "cash":
        cash = metrics.cash * factor
        anchor_cash = metrics.anchor_cash * factor
        return replace(
            metrics,
            cash=cash,
            anchor_cash=anchor_cash,
            commercial_cash=metrics.commercial_cash * factor,
            kcash=coverage(cash, metrics.opex),
            anchor_kcash=coverage(anchor_cash, metrics.opex),
            opex_gap=metrics.opex - cash,
        )
    if parameter == "opex":
        opex = metrics.opex * factor
        return replace(
            metrics,
            opex=opex,
            kcash=coverage(metrics.cash, opex),
            anchor_kcash=coverage(metrics.anchor_cash, opex),
            opex_gap=opex - metrics.cash,
        )
    if parameter == "c0":
        return replace(metrics, c0=metrics.c0 * factor)
    raise KeyError(f"unsupported parameter {parameter!r}")


def parameter_sensitivity(case: Case, selection, parameters=("vpub", "cash"), delta: float = 0.2) -> list:
    pairs = require_valid_selection(case, selection)
    _, metrics = evaluate(case, pairs)
    rows = []
    for parameter in parameters:
        for factor in (1.0 - delta, 1.0 + delta):
            perturbed = perturb(metrics, parameter, factor)
            for scenario_id, scenario in case.scenarios.items():
                checks = run_checks(perturbed, case.constraints, scenario)
                failed = tuple(check.code for check in checks if not check.passed)
                rows.append(ParameterSensitivity(
                    parameter=parameter,
                    factor=factor,
                    scenario=scenario_id,
                    feasible=not failed,
                    failed_checks=failed,
                ))
    return rows
