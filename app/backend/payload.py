"""Сборка dashboard.json — единственного контракта между расчётом и интерфейсом.

Схема описана в app/CONTRACT.md. Интерфейс (app/static/app.js) не считает
ничего, кроме производных для отображения: разницы между комбинациями,
проценты от порога, графики.
"""
from __future__ import annotations

import datetime as dt
import json
from functools import lru_cache
from pathlib import Path

from . import evaluate as ev
from . import ingest
from . import model

APP = Path(__file__).resolve().parents[1]
CONFIG = APP / "config"


def _load(name):
    with open(CONFIG / name, encoding="utf-8") as f:
        return json.load(f)


# Карточки сервисов (app/config/lots_ui.csv, формат участника 5 — записка): русские заголовки как в файле → поля контракта.
UI_COLUMNS = {
    "Название для интерфейса": "name",
    "Короткое описание": "description",
    "Основной пользователь": "user",
    "Режим": "mode",
    "Базовый доступ": "access_base",
    "Дополнительный доступ": "access_extra",
    "Главный KPI": "kpi",
    "Что показать при сбое": "on_failure",
}


def _lots_ui() -> dict:
    """lot_id → карточка сервиса. Файл правит участник записки; лоты без строки получают card = null."""
    import csv

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
    lots, modes, config = ev.load_case(Path(root))
    records = model.enumerate_all(lots, modes, config)
    return lots, modes, config, records


def _enumerated():
    """Перебор для активного набора данных (файлы организаторов или загруженные)."""
    return _enumerated_for(str(ingest.active_root()))


def reset_cache():
    _enumerated_for.cache_clear()


def _combo_payload(rec, score, rank):
    m = rec["metrics"]
    return {
        "id": rec["id"],
        "selection": [{"lot": lot, "mode": mode} for lot, mode in rec["selection"]],
        "per_lot": [
            {
                "lot": r["lot_id"],
                "mode": r["mode_id"],
                "public_core": bool(r["public_core"]),
                "c0": r["c0_mrub"],
                "opex": r["opex_mrub_per_year"],
                "vpub": r["vpub_mrub_per_year"],
                "cash": r["cash_mrub_per_year"],
                "anchor_cash": r.get("anchor_cash_mrub_per_year"),
                "commercial_cash": r.get("commercial_cash_mrub_per_year"),
                "t_rep": r["t_rep"],
                "readiness": r["readiness_1_5"],
                "resilience": r["resilience_1_5"],
                "scale": r["scale_1_5"],
            }
            for r in rec["detail"]
        ],
        "metrics": {
            "c0": m["c0_mrub"],
            "opex": m["opex_mrub_per_year"],
            "vpub": m["vpub_mrub_per_year"],
            "cash": m["cash_mrub_per_year"],
            "kcash": m["kcash"],
            "t_rep": m["t_rep"],
            "readiness": m["readiness_1_5"],
            "resilience": m["resilience_1_5"],
            "scale": m["scale_1_5"],
            "archetypes": m["territorial_archetypes"],
            "groups": m["capability_groups"],
            "public_core": m["public_core_lots"],
        },
        "checks": rec["checks"],
        "ok": rec["ok"],
        "score": round(score(rec), 4),
        "rank": rank.get(rec["id"]),
    }


def build_dashboard(selected_id: str | None = None) -> dict:
    lots, modes, config, records = _enumerated()
    model_cfg = _load("model.json")
    ru = _load("lots_ru.json")
    ui = _lots_ui()
    selected_id = selected_id or _load("portfolio.json")["selected"]
    if selected_id not in records:
        raise ValueError(f"Неизвестная комбинация: {selected_id}")

    score = model.make_scorer(records, model_cfg["weights"], config)
    feasible = sorted((r for r in records.values() if r["ok"]["STRESS"]), key=score, reverse=True)
    rank = {r["id"]: i + 1 for i, r in enumerate(feasible)}

    allowed = model_cfg.get("allowed_modes")
    suggestions, rejected = model.suggest(records, score, selected_id, n=int(model_cfg.get("suggestions", 6)), allowed_modes=allowed)
    comparison = list(suggestions) + ([rejected] if rejected else [])
    actions = model.stress_actions(records, rejected, selected_id, score, config, allowed_modes=allowed) if rejected else []

    wanted = set(comparison) | {selected_id} | {a["id"] for a in actions}
    combos = {cid: _combo_payload(records[cid], score, rank) for cid in sorted(wanted)}  # стабильный порядок → маленькие диффы dashboard.json

    return {
        "meta": {
            "case_id": config.get("case_id"),
            "case_version": config.get("case_version"),
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "scenarios": {s: {"c0_max": v["c0_max_mrub"]} for s, v in config["scenarios"].items()},
            "constraints": config["constraints_common"],
            "weights": model_cfg["weights"],
            "rationale": model_cfg.get("rationale", {}),
            "thin_margin_pct": model_cfg.get("thin_margin_pct", 0.03),
            "allowed_modes": allowed,
            "dataset": {k: v for k, v in ingest.describe().items() if k in ("source", "root", "case_version", "activated_at")},
            "totals": {
                "combinations": len(records),
                "base_feasible": sum(1 for r in records.values() if r["ok"]["BASE"]),
                "stress_feasible": len(feasible),
            },
        },
        "lots": {
            lid: {
                "name": ui.get(lid, {}).get("name") or ru["lots"].get(lid, {}).get("name", row["service"]),
                "region": ru["lots"].get(lid, {}).get("region", row["territorial_archetype"]),
                "card": {k: v for k, v in ui[lid].items() if k != "name"} if lid in ui else None,
                "archetype": ru["archetypes"].get(row["territorial_archetype"], row["territorial_archetype"]),
                "groups": sorted(set().union(*[ev.normalize_capability(t) for t in row["capability_groups"].split(";")])),
                "federal": str(row["federal"]).lower() == "true",
            }
            for lid, row in lots.items()
        },
        "modes": {
            mid: {k: (float(v) if k != "mode_id" and k != "public_core" else v) for k, v in row.items() if k != "mode_id"}
            | {"public_core": str(row["public_core"]).lower() == "true"}
            for mid, row in modes.items()
        },
        "selected": selected_id,
        "suggestions": suggestions,
        "rejected": [rejected] if rejected else [],
        "comparison": comparison,
        "stress": {"failing": rejected, "actions": actions},
        "combinations": combos,
    }


def export_results(dashboard: dict, out_dir: Path):
    """results/base.json, results/stress.json, results/alternatives.csv — источник цифр для записки.

    Плюс три файла в формате стартового notebook организаторов (README организаторов, §8.8):
    portfolio_detail.csv, portfolio_metrics.json, team_decision_config.json — чтобы эксперт
    сравнил нашу выгрузку с выгрузкой template один в один.
    """
    import csv

    out_dir.mkdir(parents=True, exist_ok=True)
    sel = dashboard["combinations"][dashboard["selected"]]
    for scenario in ("BASE", "STRESS"):
        with open(out_dir / f"{scenario.lower()}.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "generated_at": dashboard["meta"]["generated_at"],
                    "case_version": dashboard["meta"]["case_version"],
                    "scenario": scenario,
                    "c0_max": dashboard["meta"]["scenarios"][scenario]["c0_max"],
                    "selection": sel["selection"],
                    "per_lot": sel["per_lot"],
                    "metrics": sel["metrics"],
                    "checks": sel["checks"][scenario],
                    "all_ok": sel["ok"][scenario],
                    "score": sel["score"],
                    "weights": dashboard["meta"]["weights"],
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
    with open(out_dir / "alternatives.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "lots", "modes", "c0", "opex", "vpub", "cash", "kcash", "t_rep", "public_core", "BASE", "STRESS", "score", "rank"])
        for cid in dashboard["comparison"]:
            c = dashboard["combinations"][cid]
            m = c["metrics"]
            w.writerow([
                cid,
                "+".join(s["lot"] for s in c["selection"]),
                "".join(s["mode"] for s in c["selection"]),
                round(m["c0"], 2), round(m["opex"], 2), round(m["vpub"], 2), round(m["cash"], 2),
                round(m["kcash"], 4), round(m["t_rep"], 4), m["public_core"],
                c["ok"]["BASE"], c["ok"]["STRESS"], c["score"], c["rank"],
            ])
    _export_template_format(dashboard, out_dir)


# Колонки detail из case_core.apply_mode — в том порядке, в каком их пишет notebook организаторов.
TEMPLATE_DETAIL_COLUMNS = [
    "lot_id", "mode_id", "c0_mrub", "opex_mrub_per_year", "vpub_mrub_per_year", "cash_mrub_per_year",
    "t_rep", "readiness_1_5", "resilience_1_5", "scale_1_5", "territorial_archetype", "federal",
    "capability_groups", "public_core",
]


def _export_template_format(dashboard: dict, out_dir: Path):
    """Те же имена файлов и поля, что у последней ячейки cases/case02/Космос_как_инфраструктура.ipynb."""
    import csv

    _, _, _, records = _enumerated()
    rec = records[dashboard["selected"]]
    with open(out_dir / "portfolio_detail.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(TEMPLATE_DETAIL_COLUMNS)
        for row in rec["detail"]:
            w.writerow([row[k] for k in TEMPLATE_DETAIL_COLUMNS])
    with open(out_dir / "portfolio_metrics.json", "w", encoding="utf-8") as f:
        json.dump(rec["metrics"], f, ensure_ascii=False, indent=2)
    team = _load("team.json") if (CONFIG / "team.json").exists() else {}
    summary = {
        "team": team.get("team_name", ""),
        "decision_method": team.get("decision_method", ""),
        "strategy_thesis": team.get("strategy_thesis", ""),
        "selection": [list(pair) for pair in rec["selection"]],
        "weights": dashboard["meta"]["weights"],
        "management": {
            key: (team.get("management") or {}).get(key, "")
            for key in ("payer_opex", "operator_model", "supplier_switch_rule", "replicable_core", "local_adaptation", "stress_decision")
        },
    }
    with open(out_dir / "team_decision_config.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
