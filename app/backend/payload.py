from __future__ import annotations

import csv
import datetime as dt
from dataclasses import replace
import json
from functools import lru_cache
from pathlib import Path

from kosmo import Variant, export_bundle, load_portfolio, load_selection_model, load_team_card, load_variants
from kosmo.variants import slug

from . import evaluate as ev
from . import ingest
from . import model

APP = Path(__file__).resolve().parents[1]
CONFIG = APP / "config"
TEAM_CONFIG = ev.REPO / "config"

UI_COLUMNS = {
    "Название для интерфейса": "name",
    "Короткое описание": "description",
    "Основной пользователь": "user",
    "Режим": "mode",
    "Базовый доступ": "access_base",
    "Дополнительный доступ": "access_extra",
    "Главный KPI": "kpi",
    "Что показать при сбое": "on_failure",
    "Проблема": "problem",
    "Предполагаемый плательщик": "payer",
    "Ключевой риск": "risk",
}

CONSTRAINT_KEYS = {
    "selected_lots_exactly": "selected_lots_exactly",
    "min_territorial_archetypes": "min_territorial_archetypes",
    "min_capability_groups": "min_capability_groups",
    "min_public_core_lots": "min_public_core_lots",
    "opex_max": "opex_max_mrub_per_year",
    "vpub_min": "vpub_min_mrub_per_year",
    "kcash_min": "kcash_min",
    "t_rep_min": "t_rep_min",
}


def _load(name):
    with open(CONFIG / name, encoding="utf-8") as f:
        return json.load(f)


def _lots_ui() -> dict:
    path = CONFIG / "lots_ui.csv"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out = {}
    for row in rows:
        lid = (row.get("lot_id") or "").strip()
        if lid:
            out[lid] = {UI_COLUMNS[k]: (row.get(k) or "").strip() for k in UI_COLUMNS if k in row}
    return out


@lru_cache(maxsize=4)
def _enumerated_for(root: str):
    case = ev.load_case(Path(root))
    return case, model.enumerate_all(case)


def _enumerated():
    return _enumerated_for(str(ingest.active_root()))


def reset_cache():
    _enumerated_for.cache_clear()


def team_portfolio() -> Variant:
    return load_portfolio(TEAM_CONFIG / "portfolio.json")


def _why_final(path: Path | None = None) -> dict:
    """Тексты экрана «Почему FINAL» (app/config/why_final.json, формулировки участника 3); нет файла — пустой словарь."""
    path = path or CONFIG / "why_final.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not str(k).startswith("_")} if isinstance(data, dict) else {}


def _alternatives(case, records: dict, path: Path | None = None) -> list:
    """Именованные варианты записки (config/alternatives.json): name, id в порядке лотов кейса, note.
    Неполные записи и варианты с лотами вне набора данных пропускаются; найденные считаются движком и добавляются в records."""
    path = path or TEAM_CONFIG / "alternatives.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    items = raw.get("variants") if isinstance(raw, dict) else raw
    out = []
    for v in items if isinstance(items, list) else []:
        if not isinstance(v, dict):
            continue
        name, parts = v.get("name"), v.get("selection") or []
        if not name or not parts or not all(isinstance(p, dict) and "lot_id" in p and "mode_id" in p for p in parts):
            continue  # неполная запись файла участника: пропускаем, не роняя сборку
        try:
            cid = model.canonical_id(case, [(p["lot_id"], p["mode_id"]) for p in parts])
            if cid not in records:
                records[cid] = model.record(case, model.parse_id(cid))
        except ValueError:
            continue  # лот или режим вне набора данных
        out.append({"name": str(name), "id": cid, "note": str(v.get("note", ""))})
    return out


def selection_model():
    return load_selection_model(TEAM_CONFIG / "weights.json")


def _combo_payload(rec, score, rank, kcash_min: float):
    m = rec["metrics"]
    breakdown = getattr(score, "breakdown", None)
    gate = next((g for g in rec.get("gates", []) if g.get("id") == "anchor_coverage"), None)
    return {
        "id": rec["id"],
        "selection": [{"lot": lot, "mode": mode} for lot, mode in rec["selection"]],
        "per_lot": [
            {
                "lot": r.lot_id,
                "mode": r.mode_id,
                "public_core": r.public_core,
                "c0": r.c0,
                "opex": r.opex,
                "vpub": r.vpub,
                "cash": r.cash,
                "anchor_cash": r.anchor_cash,
                "commercial_cash": r.commercial_cash,
                "opex_gap": r.opex_gap,
                "t_rep": r.t_rep,
                "readiness": r.readiness,
                "resilience": r.resilience,
                "scale": r.scale,
            }
            for r in rec["detail"]
        ],
        "metrics": {
            "c0": m.c0,
            "opex": m.opex,
            "vpub": m.vpub,
            "cash": m.cash,
            "anchor_cash": m.anchor_cash,
            "commercial_cash": m.commercial_cash,
            "kcash": m.kcash,
            "opex_gap": m.opex_gap,
            "t_rep": m.t_rep,
            "readiness": m.readiness,
            "resilience": m.resilience,
            "scale": m.scale,
            "archetypes": m.territorial_archetypes,
            "groups": m.capability_groups,
            "public_core": m.public_core_lots,
        },
        "checks": rec["checks"],
        "ok": rec["ok"],
        "gates": rec.get("gates", []),
        "admitted": bool(rec.get("admitted", rec["ok"]["STRESS"])),
        "notes": {scenario: [{"code": note.code, "message": note.message, "lots": list(note.lots)} for note in result.notes] for scenario, result in rec["results"].items()},
        "score": round(score(rec), 4),
        "rank": rank.get(rec["id"]),
        # дополнительный сценарий команды S2 «commercial cash = 0»: не официальный STRESS, только якорные поступления
        "s2": {"cash": m.anchor_cash, "kcash": (m.anchor_cash / m.opex) if m.opex else None, "opex_gap": m.opex - m.anchor_cash,
               "kcash_ok": bool(gate["ok"]) if gate else bool(m.opex and m.anchor_cash / m.opex >= kcash_min - 1e-9)},
        # разложение балла по критериям: raw, границы нормализации, z, вес, вклад; Σ contribution = score
        "breakdown": [dict(b, raw=round(b["raw"], 6), z=round(b["z"], 4), contribution=round(b["contribution"], 4)) for b in breakdown(rec)] if breakdown else None,
    }


def build_dashboard(selected_id: str | None = None, root: Path | None = None, gates_filter: bool | None = None) -> dict:
    root = Path(root) if root is not None else ingest.active_root()
    case, enumerated = _enumerated_for(str(root))
    records = dict(enumerated)  # копия: произвольные комбинации (конструктор, альтернативы записки) не попадают в кэш перебора
    ui_cfg = _load("model.json")
    ru = _load("lots_ru.json")
    ui = _lots_ui()
    portfolio = team_portfolio()
    default_id = model.canonical_id(case, portfolio.selection)
    selected_id = model.canonical_id(case, model.parse_id(selected_id)) if selected_id else default_id

    def ensure(cid: str, what: str):
        if cid not in records:
            try:
                records[cid] = model.record(case, model.parse_id(cid))
            except ValueError as error:
                raise ValueError(f"{what}: {cid} ({error})") from None

    ensure(default_id, "Портфель FINAL из config/portfolio.json отсутствует в наборе данных")
    ensure(selected_id, "Неизвестная комбинация")
    alternatives = _alternatives(case, records)   # до балла: экран «Почему FINAL» показывает их балл и место

    sel_model = selection_model()
    if gates_filter is not None:
        sel_model = replace(sel_model, gates_filter=gates_filter)
    feasible_scenario = ui_cfg.get("feasible_scenario", "STRESS")
    model.admit(records, sel_model, feasible_scenario)
    score, rank = model.make_scorer(records, sel_model, feasible_scenario)
    admitted = [r for r in enumerated.values() if r["admitted"]]

    allowed = ui_cfg.get("allowed_modes")
    suggestions, rejected, gate_rejected = model.suggest(records, score, selected_id, n=int(ui_cfg.get("suggestions", 6)), allowed_modes=allowed, pinned=(default_id,))
    rejected_ids = [cid for cid in (gate_rejected, rejected) if cid]
    comparison = list(suggestions) + rejected_ids
    actions = model.stress_actions(records, rejected, selected_id, score, case, allowed_modes=allowed) if rejected else []

    wanted = set(comparison) | {selected_id, default_id} | {a["id"] for a in actions} | {a["id"] for a in alternatives}
    combos = {cid: _combo_payload(records[cid], score, rank, float(case.constraints.kcash_min)) for cid in sorted(wanted)}

    return {
        "meta": {
            "case_id": case.case_id,
            "case_version": case.version,
            "engine": {
                "name": "kosmo",
                "verified": case.verified,
                "checksums": case.checksums,
                "portfolio": portfolio.name,
                "portfolio_id": default_id,
                "weights_file": "config/weights.json",
            },
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "scenarios": {sid: {"c0_max": scenario.c0_max} for sid, scenario in case.scenarios.items()},
            "constraints": {name: getattr(case.constraints, attr) for attr, name in CONSTRAINT_KEYS.items()},
            "weights": model.ui_weights(sel_model),
            "rationale": model.ui_rationale(sel_model),
            "gates": [{"id": gate.code, "label": gate.label, "metric": gate.metric, "op": ev.OPERATORS[gate.operator], "threshold": gate.threshold, "unit": gate.unit, "rationale": gate.rationale} for gate in sel_model.gates],
            "feasible_scenario": feasible_scenario,
            "gates_filter": sel_model.gates_filter,
            "thin_margin_pct": ui_cfg.get("thin_margin_pct", 0.03),
            "allowed_modes": allowed,
            "dataset": {k: v for k, v in ingest.describe(root).items() if k in ("source", "root", "case_version", "activated_at")},
            "totals": {
                "combinations": len(enumerated),
                "base_feasible": sum(1 for r in enumerated.values() if r["ok"]["BASE"]),
                "stress_feasible": sum(1 for r in enumerated.values() if r["ok"]["STRESS"]),
                "admitted": len(admitted),
                "ranked": len(admitted),
            },
        },
        "lots": {
            lid: {
                "name": ui.get(lid, {}).get("name") or ru["lots"].get(lid, {}).get("name", lot.service),
                "region": ru["lots"].get(lid, {}).get("region", lot.territorial_archetype),
                "card": {k: v for k, v in ui[lid].items() if k != "name"} if lid in ui else None,
                "archetype": ru["archetypes"].get(lot.territorial_archetype, lot.territorial_archetype),
                "groups": sorted(lot.capability_set),
                "federal": lot.federal,
            }
            for lid, lot in case.lots.items()
        },
        "modes": {
            mid: {
                "k_c0": mode.k_c0,
                "k_opex": mode.k_opex,
                "k_vpub": mode.k_vpub,
                "k_anchor": mode.k_anchor,
                "k_commercial": mode.k_commercial,
                "public_core": mode.public_core,
                "custom": mode.custom,
            }
            for mid, mode in case.modes.items()
        },
        "selected": selected_id,
        "final": default_id,                       # решение гейта (config/portfolio.json); selected может быть произвольным портфелем из конструктора
        "final_name": portfolio.name,
        "alternatives": alternatives,              # именованные варианты записки для экрана «Почему FINAL»
        "why_final": _why_final(),                 # формулировки участника 3 из app/config/why_final.json
        "suggestions": suggestions,
        "rejected": rejected_ids,
        "comparison": comparison,
        "stress": {"failing": rejected, "actions": actions},
        "combinations": combos,
    }


def selected_variant(dashboard: dict) -> Variant:
    case, _ = _enumerated()
    portfolio = team_portfolio()
    selected = dashboard["selected"]
    if selected == model.canonical_id(case, portfolio.selection):
        return portfolio
    return Variant(name=selected, selection=tuple(model.parse_id(selected)), note="выбрано в интерфейсе")


def export_dir(dashboard: dict, out_dir: Path, variant: Variant) -> Path:
    if variant.name == team_portfolio().name:
        return Path(out_dir)
    return Path(out_dir) / "variants" / slug(dashboard["selected"])


def export_results(dashboard: dict, out_dir: Path, with_enumeration: bool = False) -> dict:
    case, _ = _enumerated()
    variant = selected_variant(dashboard)
    written = export_bundle(
        case,
        variant,
        load_variants(TEAM_CONFIG / "alternatives.json"),
        selection_model(),
        export_dir(dashboard, out_dir, variant),
        with_enumeration=with_enumeration,
        team=load_team_card(TEAM_CONFIG / "team.json"),
    )
    return {key: str(path) for key, path in written.items()}
