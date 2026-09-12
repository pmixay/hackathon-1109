"""Модель выбора команды: перебор, балл, предложения, действия в стрессе.

Всё, что здесь, — собственная модель команды поверх канонического расчёта.
Роль B меняет `make_scorer` (критерии, нормализация) и веса в
app/config/model.json; роль C — `stress_actions`. Канон не трогаем.
"""
from __future__ import annotations

import itertools

from . import evaluate as ev

MODES = ("A", "B", "C")


def combo_id(selection) -> str:
    return "|".join(f"{lot}:{mode}" for lot, mode in selection)


def parse_id(cid: str):
    return [tuple(part.split(":")) for part in cid.split("|")]


def enumerate_all(lots, modes, config, evaluate=ev.evaluate_portfolio, check=ev.check_details):
    """Все комбинации «4 лота × режимы». Возвращает dict id -> запись."""
    records = {}
    lot_ids = list(lots)
    for combo in itertools.combinations(lot_ids, 4):
        for mm in itertools.product(MODES, repeat=4):
            selection = list(zip(combo, mm))
            detail, metrics = evaluate(selection, lots, modes, config)
            checks = {s: check(metrics, config, s) for s in config["scenarios"]}
            rec = {
                "id": combo_id(selection),
                "selection": selection,
                "detail": detail,
                "metrics": metrics,
                "checks": checks,
                "ok": {s: all(r["ok"] for r in checks[s]) for s in checks},
            }
            records[rec["id"]] = rec
    return records


def make_scorer(records, weights, config, feasible_scenario="STRESS"):
    """Взвешенная сумма нормированных критериев; min–max по допустимым в STRESS."""
    stress_max = config["scenarios"][feasible_scenario]["c0_max_mrub"]
    criteria = {
        "vpub": (lambda m: m["vpub_mrub_per_year"], +1),
        "c0": (lambda m: m["c0_mrub"], -1),
        "kcash": (lambda m: m["kcash"], +1),
        "readiness": (lambda m: m["readiness_1_5"], +1),
        "resilience": (lambda m: m["resilience_1_5"], +1),
        "scale": (lambda m: m["scale_1_5"], +1),
        "stress_margin": (lambda m: stress_max - m["c0_mrub"], +1),
    }
    feasible = [r for r in records.values() if r["ok"][feasible_scenario]]
    lo, hi = {}, {}
    for key, (fn, _) in criteria.items():
        vals = [fn(r["metrics"]) for r in feasible]
        lo[key], hi[key] = min(vals), max(vals)

    def breakdown(rec):
        """Разложение балла по критериям: raw, нормированное z (0–1), вес, вклад w × z."""
        rows = []
        for key, (fn, direction) in criteria.items():
            w = float(weights.get(key, 0))
            raw = fn(rec["metrics"])
            span = hi[key] - lo[key]
            x = (raw - lo[key]) / span if span else 1.0
            x = max(0.0, min(1.0, x))
            z = x if direction > 0 else 1 - x
            rows.append({"key": key, "direction": "max" if direction > 0 else "min", "raw": raw, "lo": lo[key], "hi": hi[key], "z": z, "weight": w, "contribution": w * z})
        return rows

    def score(rec):
        return sum(r["contribution"] for r in breakdown(rec))

    score.breakdown = breakdown
    return score


def lot_set(rec):
    return frozenset(lot for lot, _ in rec["selection"])


def uses_only(rec, allowed_modes):
    return allowed_modes is None or all(mode in allowed_modes for _, mode in rec["selection"])


def suggest(records, score, selected_id, n=6, allowed_modes=None):
    """Предложенные комбинации: выбранная, лучший режим каждого допустимого
    набора лотов, режим A на всех лотах выбранного набора; топ-n по баллу.
    Плюс одна «отвергнутая»: максимум ценности среди проходящих BASE, но не STRESS."""
    feasible = [r for r in records.values() if r["ok"]["STRESS"] and uses_only(r, allowed_modes)]
    best_per_set = {}
    for r in feasible:
        key = lot_set(r)
        if key not in best_per_set or score(r) > score(best_per_set[key]):
            best_per_set[key] = r
    cand = {r["id"] for r in best_per_set.values()}
    sel = records[selected_id]
    cand.add(selected_id)
    all_a = combo_id([(lot, "A") for lot, _ in sel["selection"]])
    if all_a in records and records[all_a]["ok"]["STRESS"]:
        cand.add(all_a)
    ranked = sorted(cand, key=lambda cid: score(records[cid]), reverse=True)[:n]
    if selected_id not in ranked:
        ranked = [selected_id] + ranked[: n - 1]
    rejected = [r for r in records.values() if r["ok"]["BASE"] and not r["ok"]["STRESS"] and uses_only(r, allowed_modes)]
    rejected.sort(key=lambda r: r["metrics"]["vpub_mrub_per_year"], reverse=True)
    reject_id = rejected[0]["id"] if rejected else None
    return ranked, reject_id


def describe_change(base, other):
    """Отличие other от base словами: «FLOOD вместо FIRE · AGRI, TRANS → A»."""
    b = dict(base["selection"])
    o = dict(other["selection"])
    removed = [l for l in b if l not in o]
    added = [l for l in o if l not in b]
    parts = []
    for r, a in zip(removed, added):
        parts.append(f"{a} вместо {r}")
    by_mode: dict[str, list[str]] = {}
    for lot in o:
        if lot in b and o[lot] != b[lot]:
            by_mode.setdefault(o[lot], []).append(lot)
    for mode, lots_ in by_mode.items():
        parts.append(f"{', '.join(lots_)} → {mode}")
    return " · ".join(parts) if parts else "без изменений"


def stress_actions(records, failing_id, selected_id, score, config, allowed_modes=None):
    """Что можно сделать с комбинацией, не проходящей STRESS.
    Правило кейса: стоимость лотов не снижается, меняем только режим или состав."""
    failing = records[failing_id]
    stress_max = config["scenarios"]["STRESS"]["c0_max_mrub"]
    actions = [{"label": "Оставить как есть", "id": failing_id}]
    # один лот в режим B: тот, что даёт наибольшее снижение c0
    best_one = None
    for i, (lot, mode) in enumerate(failing["selection"]):
        if mode == "A":
            sel = list(failing["selection"])
            sel[i] = (lot, "B")
            cid = combo_id(sel)
            if best_one is None or records[cid]["metrics"]["c0_mrub"] < records[best_one[1]]["metrics"]["c0_mrub"]:
                best_one = (lot, cid)
    if best_one:
        actions.append({"label": f"{best_one[0]} в режим B", "id": best_one[1]})
    all_b = combo_id([(lot, "B") for lot, _ in failing["selection"]])
    if all_b in records and all_b != failing_id:
        actions.append({"label": "Все четыре лота в режим B", "id": all_b})
    # замена одного лота: лучшие по баллу допустимые комбинации, отличающиеся одним лотом
    fset = lot_set(failing)
    swaps = [r for r in records.values() if r["ok"]["STRESS"] and len(fset & lot_set(r)) == 3 and uses_only(r, allowed_modes)]
    swaps.sort(key=score, reverse=True)
    seen = {a["id"] for a in actions}
    for r in swaps[:3]:
        if r["id"] not in seen and r["id"] != selected_id:
            actions.append({"label": describe_change(failing, r), "id": r["id"]})
            seen.add(r["id"])
    if selected_id not in seen:
        actions.append({"label": describe_change(failing, records[selected_id]) + " (= выбранная)", "id": selected_id})
    for a in actions:
        a["margin"] = stress_max - records[a["id"]]["metrics"]["c0_mrub"]
    return actions
