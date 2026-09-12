"""Расчётное ядро без pandas: те же формулы и те же имена показателей, что в
cases/case02/case_core.py организаторов.

Зачем два ядра. Канон — case_core.py (pandas). Этот модуль повторяет его
один в один на стандартной библиотеке, чтобы интерфейс запускался без
зависимостей. Интеграция роли A: заменить `evaluate_portfolio` и
`check_constraints` на вызовы case_core (см. `core_backend()` ниже) и
подтвердить тестами, что цифры совпадают.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CASE_DIR = REPO / "cases" / "case02"

CHECK_ORDER = [
    "exact_lot_count",
    "territorial_archetypes",
    "capability_groups",
    "public_core_lots",
    "c0_limit",
    "opex_limit",
    "vpub_floor",
    "kcash_floor",
    "t_rep_floor",
]


def load_case(root: Path = CASE_DIR):
    """lots: dict lot_id -> row; modes: dict mode_id -> row; config: dict."""
    root = Path(root)
    with open(root / "data" / "lots.csv", encoding="utf-8") as f:
        lots = {r["lot_id"]: r for r in csv.DictReader(f)}
    with open(root / "data" / "access_modes.csv", encoding="utf-8") as f:
        modes = {r["mode_id"]: r for r in csv.DictReader(f)}
    with open(root / "config" / "case_config.json", encoding="utf-8") as f:
        config = json.load(f)
    return lots, modes, config


def normalize_capability(token: str) -> set[str]:
    token = token.strip()
    if token in {"PNT", "PNT/InSAR", "InSAR"}:
        return {"PNT/InSAR"}
    return {token} if token else set()


def apply_mode(lot: dict, mode: dict) -> dict:
    """Один лот × режим. Ключи как у case_core.apply_mode."""
    return {
        "lot_id": lot["lot_id"],
        "mode_id": mode["mode_id"],
        "c0_mrub": float(lot["c0_mrub"]) * float(mode["k_c0"]),
        "opex_mrub_per_year": float(lot["opex_mrub_per_year"]) * float(mode["k_opex"]),
        "vpub_mrub_per_year": float(lot["vpub_mrub_per_year"]) * float(mode["k_vpub"]),
        "cash_mrub_per_year": float(lot["anchor_cash_mrub_per_year"]) * float(mode["k_anchor"])
        + float(lot["commercial_cash_mrub_per_year"]) * float(mode["k_commercial"]),
        "anchor_cash_mrub_per_year": float(lot["anchor_cash_mrub_per_year"]) * float(mode["k_anchor"]),
        "commercial_cash_mrub_per_year": float(lot["commercial_cash_mrub_per_year"]) * float(mode["k_commercial"]),
        "t_rep": float(lot["t_rep"]),
        "readiness_1_5": float(lot["readiness_1_5"]),
        "resilience_1_5": float(lot["resilience_1_5"]),
        "scale_1_5": float(lot["scale_1_5"]),
        "territorial_archetype": lot["territorial_archetype"],
        "federal": str(lot["federal"]).lower() == "true",
        "capability_groups": lot["capability_groups"],
        "public_core": str(mode["public_core"]).lower() == "true",
    }


def evaluate_portfolio(selection, lots, modes, config):
    """selection: список (lot_id, mode_id). Возвращает (detail, metrics) как case_core."""
    detail = []
    for lot_id, mode_id in selection:
        if lot_id not in lots:
            raise ValueError(f"Unknown lot: {lot_id}")
        if mode_id not in modes:
            raise ValueError(f"Unknown mode: {mode_id}")
        detail.append(apply_mode(lots[lot_id], modes[mode_id]))
    if not detail:
        return detail, {"selected_lots": 0}
    capset: set[str] = set()
    for row in detail:
        for token in str(row["capability_groups"]).split(";"):
            capset |= normalize_capability(token)
    territorial = {r["territorial_archetype"] for r in detail if not r["federal"]}
    n = len(detail)
    opex = sum(r["opex_mrub_per_year"] for r in detail)
    cash = sum(r["cash_mrub_per_year"] for r in detail)
    metrics = {
        "selected_lots": len({r["lot_id"] for r in detail}),
        "c0_mrub": sum(r["c0_mrub"] for r in detail),
        "opex_mrub_per_year": opex,
        "vpub_mrub_per_year": sum(r["vpub_mrub_per_year"] for r in detail),
        "cash_mrub_per_year": cash,
        "kcash": cash / opex if opex else float("nan"),
        "t_rep": sum(r["t_rep"] for r in detail) / n,
        "readiness_1_5": sum(r["readiness_1_5"] for r in detail) / n,
        "resilience_1_5": sum(r["resilience_1_5"] for r in detail) / n,
        "scale_1_5": sum(r["scale_1_5"] for r in detail) / n,
        "territorial_archetypes": len(territorial),
        "capability_groups": len(capset),
        "capability_set": sorted(capset),
        "public_core_lots": sum(1 for r in detail if r["public_core"]),
    }
    return detail, metrics


def check_details(metrics, config, scenario="BASE"):
    """Девять проверок с фактом, знаком и порогом. Порядок и имена — как в case_core.check_constraints."""
    c = config["constraints_common"]
    sc = config["scenarios"][scenario]
    eps = 1e-9
    rows = [
        ("exact_lot_count", metrics.get("selected_lots", 0), "=", c["selected_lots_exactly"]),
        ("territorial_archetypes", metrics.get("territorial_archetypes", 0), ">=", c["min_territorial_archetypes"]),
        ("capability_groups", metrics.get("capability_groups", 0), ">=", c["min_capability_groups"]),
        ("public_core_lots", metrics.get("public_core_lots", 0), ">=", c["min_public_core_lots"]),
        ("c0_limit", metrics.get("c0_mrub", float("inf")), "<=", sc["c0_max_mrub"]),
        ("opex_limit", metrics.get("opex_mrub_per_year", float("inf")), "<=", c["opex_max_mrub_per_year"]),
        ("vpub_floor", metrics.get("vpub_mrub_per_year", -float("inf")), ">=", c["vpub_min_mrub_per_year"]),
        ("kcash_floor", metrics.get("kcash", -float("inf")), ">=", c["kcash_min"]),
        ("t_rep_floor", metrics.get("t_rep", -float("inf")), ">=", c["t_rep_min"]),
    ]
    out = []
    for cid, fact, op, thr in rows:
        if op == "=":
            ok = fact == thr
        elif op == "<=":
            ok = fact <= thr + eps
        else:
            ok = fact >= thr - eps
        out.append({"id": cid, "ok": bool(ok), "fact": fact, "op": op, "threshold": thr})
    return out


def check_constraints(metrics, config, scenario="BASE"):
    """Как case_core.check_constraints, но список словарей вместо DataFrame."""
    return [{"constraint": r["id"], "ok": r["ok"]} for r in check_details(metrics, config, scenario)]


def core_backend():
    """Точка интеграции роли A: вернуть функции канонического case_core.py.

    Пример замены в payload.build_dashboard:
        evaluate, check = core_backend()
    Требует pandas. Оставлено как функция, чтобы модуль импортировался без него.
    """
    import sys

    sys.path.insert(0, str(CASE_DIR))
    import case_core  # type: ignore

    def evaluate(selection, lots, modes, config):
        lots_df, modes_df, cfg = case_core.load_case(CASE_DIR)
        detail_df, metrics = case_core.evaluate_portfolio(list(selection), lots_df, modes_df, cfg)
        return detail_df.to_dict("records"), metrics

    def check(metrics, config, scenario="BASE"):
        df = case_core.check_constraints(metrics, config, scenario)
        return df.to_dict("records")

    return evaluate, check
