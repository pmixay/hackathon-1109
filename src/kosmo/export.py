from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from .calc import CalculationResult, calculate_all_scenarios
from .case import Case
from .custom_mode import custom_mode_to_dict
from .variants import Variant, used_custom_modes

METRIC_COLUMNS = (
    "c0", "opex", "vpub", "cash", "anchor_cash", "commercial_cash", "kcash", "opex_gap",
    "t_rep", "readiness", "resilience", "scale",
    "territorial_archetypes", "capability_groups", "public_core_lots",
)


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
    for item in scored:
        row = {"variant": item.name, "feasible": item.feasible, "score": item.score, "rank": item.rank}
        for key in keys:
            row[key] = item.values.get(key, "")
            row[f"z_{key}"] = item.normalized.get(key, "")
        rows.append(row)
    columns = ("variant", "feasible", "score", "rank") + tuple(keys) + tuple(f"z_{key}" for key in keys)
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
