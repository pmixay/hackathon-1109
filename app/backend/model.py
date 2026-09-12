from __future__ import annotations

import math
from dataclasses import replace
from itertools import combinations, product

from kosmo import Case, SelectionModel, display_rationale, display_weights, run_team_checks, score_variants
from kosmo.selection import criterion_value

from . import evaluate as ev


def combo_id(selection) -> str:
    return "|".join(f"{lot}:{mode}" for lot, mode in selection)


def parse_id(cid: str):
    return [tuple(part.split(":")) for part in cid.split("|")]


def canonical_id(case: Case, selection) -> str:
    order = {lot_id: index for index, lot_id in enumerate(case.lots)}
    pairs = sorted(((str(lot).strip(), str(mode).strip()) for lot, mode in selection), key=lambda pair: order.get(pair[0], len(order)))
    return combo_id(pairs)


def record(case: Case, selection) -> dict:
    selection = list(selection)
    results = ev.evaluate_portfolio(selection, case)
    first = next(iter(results.values()))
    return {
        "id": combo_id(selection),
        "selection": selection,
        "results": results,
        "detail": first.lots,
        "metrics": first.metrics,
        "checks": {scenario: ev.check_details(result) for scenario, result in results.items()},
        "ok": {scenario: result.feasible for scenario, result in results.items()},
    }


def admit(records: dict, model: SelectionModel, feasible_scenario: str = "STRESS") -> dict:
    for rec in records.values():
        gates = run_team_checks(rec["metrics"], model.gates)
        rec["gates"] = ev.gate_details(gates)
        rec["admitted"] = bool(rec["ok"][feasible_scenario] and all(check.passed for check in gates))
    return records


def enumerate_all(case: Case, mode_ids=None) -> dict:
    mode_ids = tuple(mode_ids) if mode_ids is not None else tuple(case.canonical_modes)
    size = case.constraints.selected_lots_exactly
    records = {}
    for lots in combinations(tuple(case.lots), size):
        for modes in product(mode_ids, repeat=size):
            rec = record(case, zip(lots, modes))
            records[rec["id"]] = rec
    return records


def ui_weights(model: SelectionModel) -> dict:
    return display_weights(model)


def ui_rationale(model: SelectionModel) -> dict:
    return display_rationale(model)


def make_scorer(records: dict, model: SelectionModel, feasible_scenario: str = "STRESS"):
    model = replace(model, feasibility_scenario=feasible_scenario)
    scored = {item.name: item for item in score_variants({cid: rec["results"] for cid, rec in records.items()}, model)}
    ranked_items = [item for item in scored.values() if item.rank is not None]
    if not ranked_items:
        return (lambda rec: 0.0), {}
    bounds = {}
    for criterion in model.criteria:
        values = [item.values[criterion.key] for item in ranked_items]
        bounds[criterion.key] = (min(values), max(values))
    total = model.total_weight

    def score(rec) -> float:
        item = scored[rec["id"]]
        if item.score is not None:
            return item.score
        acc = 0.0
        for criterion in model.criteria:
            low, high = bounds[criterion.key]
            value = criterion_value(rec["results"], criterion.key, feasible_scenario)
            x = 1.0 if math.isclose(low, high) else max(0.0, min(1.0, (value - low) / (high - low)))
            acc += criterion.weight * (x if criterion.direction == "max" else 1.0 - x)
        return acc / total

    rank = {name: item.rank for name, item in scored.items() if item.rank is not None}
    return score, rank


def lot_set(rec):
    return frozenset(lot for lot, _ in rec["selection"])


def uses_only(rec, allowed_modes):
    return allowed_modes is None or all(mode in allowed_modes for _, mode in rec["selection"])


def is_admitted(rec) -> bool:
    return bool(rec.get("admitted", rec["ok"]["STRESS"]))


def suggest(records, score, selected_id, n=6, allowed_modes=None, pinned=()):
    feasible = [r for r in records.values() if is_admitted(r) and uses_only(r, allowed_modes)]
    best_per_set = {}
    for r in feasible:
        key = lot_set(r)
        if key not in best_per_set or score(r) > score(best_per_set[key]):
            best_per_set[key] = r
    cand = {r["id"] for r in best_per_set.values()}
    sel = records[selected_id]
    all_a = combo_id([(lot, "A") for lot, _ in sel["selection"]])
    if all_a in records and is_admitted(records[all_a]):
        cand.add(all_a)
    keep = [cid for cid in dict.fromkeys((selected_id, *pinned)) if cid in records]
    by_score = lambda cid: score(records[cid])
    rest = [cid for cid in sorted(cand, key=by_score, reverse=True) if cid not in keep]
    chosen = keep + rest[: max(0, n - len(keep))]
    for r in sorted(feasible, key=score, reverse=True):
        if len(chosen) >= n:
            break
        if r["id"] not in chosen:
            chosen.append(r["id"])
    ranked = sorted(chosen, key=by_score, reverse=True)
    rejected = [r for r in records.values() if r["ok"]["BASE"] and not r["ok"]["STRESS"] and uses_only(r, allowed_modes)]
    rejected.sort(key=lambda r: r["metrics"].vpub, reverse=True)
    reject_id = rejected[0]["id"] if rejected else None
    gated = [r for r in records.values() if r["ok"]["STRESS"] and not is_admitted(r) and uses_only(r, allowed_modes) and r["id"] not in ranked]
    gated.sort(key=score, reverse=True)
    gate_reject_id = gated[0]["id"] if gated else None
    return ranked, reject_id, gate_reject_id


def describe_change(base, other):
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


def stress_actions(records, failing_id, selected_id, score, case: Case, allowed_modes=None):
    failing = records[failing_id]
    stress_max = case.scenarios["STRESS"].c0_max
    actions = [{"label": "Оставить как есть", "id": failing_id}]
    best_one = None
    for i, (lot, mode) in enumerate(failing["selection"]):
        if mode == "A":
            sel = list(failing["selection"])
            sel[i] = (lot, "B")
            cid = combo_id(sel)
            if cid in records and (best_one is None or records[cid]["metrics"].c0 < records[best_one[1]]["metrics"].c0):
                best_one = (lot, cid)
    if best_one:
        actions.append({"label": f"{best_one[0]} в режим B", "id": best_one[1]})
    all_b = combo_id([(lot, "B") for lot, _ in failing["selection"]])
    if all_b in records and all_b != failing_id:
        actions.append({"label": "Все четыре лота в режим B", "id": all_b})
    fset = lot_set(failing)
    swaps = [r for r in records.values() if is_admitted(r) and len(fset & lot_set(r)) == 3 and uses_only(r, allowed_modes)]
    swaps.sort(key=score, reverse=True)
    seen = {a["id"] for a in actions}
    for r in swaps[:3]:
        if r["id"] not in seen and r["id"] != selected_id:
            actions.append({"label": describe_change(failing, r), "id": r["id"]})
            seen.add(r["id"])
    if selected_id not in seen:
        actions.append({"label": describe_change(failing, records[selected_id]) + " (= выбранная)", "id": selected_id})
    for a in actions:
        a["margin"] = stress_max - records[a["id"]]["metrics"].c0
    return actions
