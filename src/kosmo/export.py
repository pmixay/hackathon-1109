from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .calc import CalculationResult, calculate_all_scenarios
from .case import Case
from .custom_mode import custom_mode_to_dict
from .enumeration import enumerate_portfolios
from .repairs import single_step_repairs
from .selection import SelectionModel, parameter_sensitivity, score_variants, weight_sensitivity
from .variants import Variant, used_custom_modes

METRIC_COLUMNS = (
    "c0", "opex", "vpub", "cash", "anchor_cash", "commercial_cash", "kcash", "anchor_kcash", "opex_gap",
    "t_rep", "readiness", "resilience", "scale",
    "territorial_archetypes", "capability_groups", "public_core_lots",
)

TEMPLATE_DETAIL_COLUMNS = (
    "lot_id", "mode_id", "c0_mrub", "opex_mrub_per_year", "vpub_mrub_per_year", "cash_mrub_per_year",
    "t_rep", "readiness_1_5", "resilience_1_5", "scale_1_5", "territorial_archetype", "federal",
    "capability_groups", "public_core",
)

TEMPLATE_METRIC_KEYS = (
    ("selected_lots", "selected_lots"),
    ("c0_mrub", "c0"),
    ("opex_mrub_per_year", "opex"),
    ("vpub_mrub_per_year", "vpub"),
    ("cash_mrub_per_year", "cash"),
    ("kcash", "kcash"),
    ("t_rep", "t_rep"),
    ("readiness_1_5", "readiness"),
    ("resilience_1_5", "resilience"),
    ("scale_1_5", "scale"),
    ("territorial_archetypes", "territorial_archetypes"),
    ("capability_groups", "capability_groups"),
    ("capability_set", "capability_set"),
    ("public_core_lots", "public_core_lots"),
)

MANAGEMENT_FIELDS = ("payer_opex", "operator_model", "supplier_switch_rule", "replicable_core", "local_adaptation", "stress_decision")

DISPLAY_KEYS = {"margin:STRESS:c0_limit": "stress_margin"}


def display_weights(model: SelectionModel) -> dict:
    return {DISPLAY_KEYS.get(criterion.key, criterion.key): criterion.weight for criterion in model.criteria}


def display_rationale(model: SelectionModel) -> dict:
    return {DISPLAY_KEYS.get(criterion.key, criterion.key): criterion.rationale for criterion in model.criteria}


def load_team_card(path) -> dict:
    path = Path(path)
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def case_header(case: Case) -> dict:
    return {
        "case_id": case.case_id,
        "version": case.version,
        "verified": case.verified,
        "checksums": case.checksums,
    }


def result_payload(case: Case, variant: Variant, result: CalculationResult) -> dict:
    return {
        "generated_at": timestamp(),
        "case": case_header(case),
        "portfolio": variant.to_dict(),
        "custom_modes": [custom_mode_to_dict(mode) for mode in used_custom_modes(case, variant.selection)],
        **result.to_dict(),
    }


def write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_csv(path: Path, rows: list, columns: tuple) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    return path


def write_scenario_results(case: Case, variant: Variant, directory) -> dict:
    directory = Path(directory)
    written = {}
    for scenario_id, result in calculate_all_scenarios(case, variant.selection).items():
        path = directory / f"{scenario_id.lower()}.json"
        written[scenario_id] = write_json(path, result_payload(case, variant, result))
    return written


def alternative_row(case: Case, variant: Variant, results: dict) -> list:
    rows = []
    for scenario_id, result in results.items():
        row = {
            "variant": variant.name,
            "scenario": scenario_id,
            "lots": "+".join(lot_id for lot_id, _ in variant.selection),
            "modes": "".join(mode_id for _, mode_id in variant.selection),
            "feasible": result.feasible,
            "failed_checks": ";".join(result.failed_checks),
            "note": variant.note,
        }
        for column in METRIC_COLUMNS:
            row[column] = getattr(result.metrics, column)
        rows.append(row)
    return rows


def write_alternatives(case: Case, variants: list, path) -> Path:
    rows = []
    for variant in variants:
        rows.extend(alternative_row(case, variant, calculate_all_scenarios(case, variant.selection)))
    columns = ("variant", "scenario", "lots", "modes", "feasible", "failed_checks") + METRIC_COLUMNS + ("note",)
    return write_csv(Path(path), rows, columns)


def write_enumeration(portfolios: list, scenario_ids, path) -> Path:
    rows = []
    for portfolio in portfolios:
        row = {"lots": "+".join(portfolio.lots), "modes": "".join(portfolio.modes)}
        for column in METRIC_COLUMNS:
            row[column] = getattr(portfolio.metrics, column)
        for scenario_id in scenario_ids:
            row[f"feasible_{scenario_id}"] = portfolio.feasible[scenario_id]
            row[f"failed_{scenario_id}"] = ";".join(portfolio.failed[scenario_id])
        rows.append(row)
    scenario_columns = tuple(f"{prefix}_{scenario_id}" for scenario_id in scenario_ids for prefix in ("feasible", "failed"))
    return write_csv(Path(path), rows, ("lots", "modes") + METRIC_COLUMNS + scenario_columns)


def write_scored(scored: list, path) -> Path:
    rows = []
    keys = []
    for item in scored:
        for key in item.values:
            if key not in keys:
                keys.append(key)
    gate_columns = []
    for item in scored:
        for check in item.gates:
            for column in (f"gate_{check.code}", check.metric):
                if column not in gate_columns and column not in keys:
                    gate_columns.append(column)
    for item in scored:
        row = {"variant": item.name, "feasible": item.feasible, "admitted": item.admitted, "score": item.score, "rank": item.rank}
        for check in item.gates:
            row[f"gate_{check.code}"] = check.passed
            row.setdefault(check.metric, check.actual)
        for key in keys:
            row[key] = item.values.get(key, "")
            row[f"z_{key}"] = item.normalized.get(key, "")
        rows.append(row)
    columns = ("variant", "feasible", "admitted", "score", "rank") + tuple(gate_columns) + tuple(keys) + tuple(f"z_{key}" for key in keys)
    return write_csv(Path(path), rows, columns)


def write_sensitivity(weight_rows: list, parameter_rows: list, path) -> Path:
    rows = []
    for item in weight_rows:
        rows.append({
            "kind": "weight",
            "target": item.key,
            "factor": item.factor,
            "value": item.weight,
            "scenario": "",
            "leader": item.leader or "",
            "leader_changed": item.leader_changed,
            "feasible": "",
            "failed_checks": "",
            "ranking": ">".join(item.ranking),
        })
    for item in parameter_rows:
        rows.append({
            "kind": "parameter",
            "target": item.parameter,
            "factor": item.factor,
            "value": "",
            "scenario": item.scenario,
            "leader": "",
            "leader_changed": "",
            "feasible": item.feasible,
            "failed_checks": ";".join(item.failed_checks),
            "ranking": "",
        })
    columns = ("kind", "target", "factor", "value", "scenario", "leader", "leader_changed", "feasible", "failed_checks", "ranking")
    return write_csv(Path(path), rows, columns)


def write_repairs(repairs: list, scenario_ids, path) -> Path:
    rows = []
    for repair in repairs:
        row = {
            "change": repair.change,
            "description": repair.description,
            "lots": "+".join(lot_id for lot_id, _ in repair.selection),
            "modes": "".join(mode_id for _, mode_id in repair.selection),
            "delta_c0": repair.delta_c0,
            "delta_opex": repair.delta_opex,
            "delta_vpub": repair.delta_vpub,
            "delta_cash": repair.delta_cash,
        }
        for column in METRIC_COLUMNS:
            row[column] = getattr(repair.metrics, column)
        for scenario_id in scenario_ids:
            row[f"feasible_{scenario_id}"] = repair.feasible[scenario_id]
        rows.append(row)
    scenario_columns = tuple(f"feasible_{scenario_id}" for scenario_id in scenario_ids)
    columns = ("change", "description", "lots", "modes", "delta_c0", "delta_opex", "delta_vpub", "delta_cash") + METRIC_COLUMNS + scenario_columns
    return write_csv(Path(path), rows, columns)


def template_detail_row(row) -> dict:
    return {
        "lot_id": row.lot_id,
        "mode_id": row.mode_id,
        "c0_mrub": row.c0,
        "opex_mrub_per_year": row.opex,
        "vpub_mrub_per_year": row.vpub,
        "cash_mrub_per_year": row.cash,
        "t_rep": row.t_rep,
        "readiness_1_5": row.readiness,
        "resilience_1_5": row.resilience,
        "scale_1_5": row.scale,
        "territorial_archetype": row.territorial_archetype,
        "federal": row.federal,
        "capability_groups": ";".join(row.capability_groups),
        "public_core": row.public_core,
    }


def template_metrics(metrics) -> dict:
    out = {}
    for template_key, attribute in TEMPLATE_METRIC_KEYS:
        value = getattr(metrics, attribute)
        out[template_key] = list(value) if isinstance(value, tuple) else value
    return out


def team_decision_config(variant: Variant, model: SelectionModel, team: dict) -> dict:
    management = team.get("management") or {}
    return {
        "team": team.get("team_name", ""),
        "decision_method": team.get("decision_method", ""),
        "strategy_thesis": team.get("strategy_thesis", ""),
        "selection": [[lot_id, mode_id] for lot_id, mode_id in variant.selection],
        "weights": display_weights(model),
        "gates": [asdict(gate) for gate in model.gates],
        "management": {key: management.get(key, "") for key in MANAGEMENT_FIELDS},
    }


def write_template_format(case: Case, variant: Variant, model: SelectionModel, team: dict, directory) -> dict:
    directory = Path(directory)
    result = calculate_all_scenarios(case, variant.selection)[next(iter(case.scenarios))]
    rows = [template_detail_row(row) for row in result.lots]
    return {
        "portfolio_detail": write_csv(directory / "portfolio_detail.csv", rows, TEMPLATE_DETAIL_COLUMNS),
        "portfolio_metrics": write_json(directory / "portfolio_metrics.json", template_metrics(result.metrics)),
        "team_decision_config": write_json(directory / "team_decision_config.json", team_decision_config(variant, model, team)),
    }


def export_bundle(case: Case, portfolio: Variant, variants: list, model: SelectionModel, out, with_enumeration: bool = True, team: dict | None = None) -> dict:
    out = Path(out)
    scenario_ids = list(case.scenarios)
    written = dict(write_scenario_results(case, portfolio, out))
    written.update(write_template_format(case, portfolio, model, team or {}, out))
    variants = list(variants)
    if portfolio.name not in {variant.name for variant in variants}:
        variants.insert(0, portfolio)
    written["alternatives"] = write_alternatives(case, variants, out / "alternatives.csv")
    evaluated = {variant.name: calculate_all_scenarios(case, variant.selection) for variant in variants}
    written["scores"] = write_scored(score_variants(evaluated, model), out / "scores.csv")
    written["sensitivity"] = write_sensitivity(weight_sensitivity(evaluated, model), parameter_sensitivity(case, portfolio.selection), out / "sensitivity.csv")
    for scenario_id in scenario_ids:
        repairs = single_step_repairs(case, portfolio.selection, scenario_id)
        written[f"repairs_{scenario_id}"] = write_repairs(repairs, scenario_ids, out / f"repairs_{scenario_id.lower()}.csv")
    if with_enumeration:
        written["enumeration"] = write_enumeration(enumerate_portfolios(case), scenario_ids, out / "enumeration.csv")
    return written
