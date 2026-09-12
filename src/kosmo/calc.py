from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from .case import AccessMode, Case, Lot
from .checks import run_checks
from .notes import management_notes
from .validation import require_valid_selection


@dataclass(frozen=True)
class LotResult:
    lot_id: str
    mode_id: str
    service: str
    territorial_archetype: str
    federal: bool
    capability_groups: tuple
    capability_set: tuple
    public_core: bool
    c0: float
    opex: float
    vpub: float
    anchor_cash: float
    commercial_cash: float
    cash: float
    opex_gap: float
    t_rep: float
    readiness: float
    resilience: float
    scale: float


@dataclass(frozen=True)
class PortfolioMetrics:
    selected_lots: int
    c0: float
    opex: float
    vpub: float
    cash: float
    anchor_cash: float
    commercial_cash: float
    kcash: float
    opex_gap: float
    t_rep: float
    readiness: float
    resilience: float
    scale: float
    territorial_archetypes: int
    capability_groups: int
    capability_set: tuple
    public_core_lots: int


@dataclass(frozen=True)
class CalculationResult:
    scenario: str
    selection: tuple
    lots: tuple
    metrics: PortfolioMetrics
    checks: tuple
    feasible: bool
    failed_checks: tuple
    notes: tuple

    def to_dict(self) -> dict:
        return plain({
            "scenario": self.scenario,
            "selection": [{"lot_id": lot_id, "mode_id": mode_id} for lot_id, mode_id in self.selection],
            "lots": [asdict(row) for row in self.lots],
            "metrics": asdict(self.metrics),
            "checks": [asdict(check) | {"status": check.status} for check in self.checks],
            "feasible": self.feasible,
            "failed_checks": self.failed_checks,
            "notes": [asdict(note) for note in self.notes],
        })


def plain(value):
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


def apply_mode(lot: Lot, mode: AccessMode) -> LotResult:
    opex = lot.opex * mode.k_opex
    anchor_cash = lot.anchor_cash * mode.k_anchor
    commercial_cash = lot.commercial_cash * mode.k_commercial
    cash = anchor_cash + commercial_cash
    return LotResult(
        lot_id=lot.lot_id,
        mode_id=mode.mode_id,
        service=lot.service,
        territorial_archetype=lot.territorial_archetype,
        federal=lot.federal,
        capability_groups=lot.capability_groups,
        capability_set=tuple(sorted(lot.capability_set)),
        public_core=mode.public_core,
        c0=lot.c0 * mode.k_c0,
        opex=opex,
        vpub=lot.vpub * mode.k_vpub,
        anchor_cash=anchor_cash,
        commercial_cash=commercial_cash,
        cash=cash,
        opex_gap=opex - cash,
        t_rep=lot.t_rep,
        readiness=lot.readiness,
        resilience=lot.resilience,
        scale=lot.scale,
    )


def mean(values) -> float:
    values = list(values)
    return math.fsum(values) / len(values) if values else math.nan


def coverage(cash: float, opex: float) -> float:
    return cash / opex if opex else math.nan


def aggregate(rows) -> PortfolioMetrics:
    rows = list(rows)
    opex = math.fsum(row.opex for row in rows)
    cash = math.fsum(row.cash for row in rows)
    capabilities = set()
    for row in rows:
        capabilities.update(row.capability_set)
    territories = {row.territorial_archetype for row in rows if not row.federal}
    return PortfolioMetrics(
        selected_lots=len({row.lot_id for row in rows}),
        c0=math.fsum(row.c0 for row in rows),
        opex=opex,
        vpub=math.fsum(row.vpub for row in rows),
        cash=cash,
        anchor_cash=math.fsum(row.anchor_cash for row in rows),
        commercial_cash=math.fsum(row.commercial_cash for row in rows),
        kcash=coverage(cash, opex),
        opex_gap=opex - cash,
        t_rep=mean(row.t_rep for row in rows),
        readiness=mean(row.readiness for row in rows),
        resilience=mean(row.resilience for row in rows),
        scale=mean(row.scale for row in rows),
        territorial_archetypes=len(territories),
        capability_groups=len(capabilities),
        capability_set=tuple(sorted(capabilities)),
        public_core_lots=sum(1 for row in rows if row.public_core),
    )


def evaluate(case: Case, pairs) -> tuple:
    rows = tuple(apply_mode(case.lots[lot_id], case.modes[mode_id]) for lot_id, mode_id in pairs)
    return rows, aggregate(rows)


def build_result(case: Case, pairs, rows, metrics, scenario_id: str) -> CalculationResult:
    checks = run_checks(metrics, case.constraints, case.scenarios[scenario_id])
    failed = tuple(check.code for check in checks if not check.passed)
    return CalculationResult(
        scenario=scenario_id,
        selection=tuple(pairs),
        lots=rows,
        metrics=metrics,
        checks=checks,
        feasible=not failed,
        failed_checks=failed,
        notes=management_notes(case, rows, metrics, checks),
    )


def calculate(case: Case, selection, scenario_id: str) -> CalculationResult:
    pairs = require_valid_selection(case, selection, scenario_id)
    rows, metrics = evaluate(case, pairs)
    return build_result(case, pairs, rows, metrics, scenario_id)


def calculate_all_scenarios(case: Case, selection) -> dict:
    pairs = require_valid_selection(case, selection)
    rows, metrics = evaluate(case, pairs)
    return {scenario_id: build_result(case, pairs, rows, metrics, scenario_id) for scenario_id in case.scenarios}
