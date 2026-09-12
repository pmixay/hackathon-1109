"""Устойчивость выбора портфеля Кейса 02: насколько рекомендация зависит от весов
и допущений. Собственный анализ команды поверх канонических формул
(app/backend повторяет case_core.py один в один). Данные организаторов не меняются.

    python tools/case02_robustness.py
    python tools/case02_robustness.py --selected "FIRE:A|AGRI:C|TRANS:C|ENV:A" --draws 3000 --years 7

Что печатается (все цифры из docs/case02-unique-features.md берутся отсюда):
  1. место выбранной комбинации по баллу модели (app/config/model.json) среди допустимых в STRESS;
  2. фронт Парето по (ценность выше, c0 ниже, cash/OPEX выше);
  3. rank acceptability: доля случайных векторов весов, при которых комбинация первая (подход SMAA);
  4. интервалы устойчивости весов: в каких пределах один вес меняется так, что выбранная остаётся в топ-3;
  5. из чего складывается разница балла с лидером, по критериям;
  6. структура поступлений и стресс спроса S2: покрытие OPEX только якорными платежами;
  7. запас по c0 в STRESS: допустимое удорожание для выбранной и для каждого набора лотов;
  8. многолетняя картина без дисконтирования (допущение команды: горизонт --years);
  9. сверка с движком src/kosmo: та же модель выбора по config/alternatives.json, с добавлением
     двух лучших по перебору комбинаций из app (пропускается, если kosmo не импортируется).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "app"))
from backend import model, payload  # noqa: E402


def anchor_only_kcash(rec, lots, modes):
    """Покрытие OPEX одними якорными платежами: cash при нулевой коммерческой выручке / OPEX."""
    anchor = sum(float(lots[l]["anchor_cash_mrub_per_year"]) * float(modes[m]["k_anchor"]) for l, m in rec["selection"])
    return anchor / rec["metrics"]["opex_mrub_per_year"]


def commercial_cash(rec, lots, modes):
    return sum(float(lots[l]["commercial_cash_mrub_per_year"]) * float(modes[m]["k_commercial"]) for l, m in rec["selection"])


def rank_under(weights, records, feasible, config, target):
    sc = model.make_scorer(records, weights, config)
    ids = [r["id"] for r in sorted(feasible, key=sc, reverse=True)]
    return ids.index(target) + 1, ids[0]


def renorm(w):
    s = sum(w.values())
    return {k: v / s for k, v in w.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selected", help="id комбинации, по умолчанию из app/config/portfolio.json")
    ap.add_argument("--draws", type=int, default=3000, help="число случайных векторов весов")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--years", type=int, default=7, help="горизонт многолетней картины, лет (допущение команды)")
    ap.add_argument("--kcash-min-s2", type=float, default=None, help="порог покрытия OPEX якорем в S2; по умолчанию kcash_min кейса")
    args = ap.parse_args()

    lots, modes, config, records = payload._enumerated()
    weights = payload._load("model.json")["weights"]
    selected = args.selected or payload._load("portfolio.json")["selected"]
    if selected not in records:
        sys.exit(f"неизвестная комбинация: {selected}")
    stress_max = config["scenarios"]["STRESS"]["c0_max_mrub"]
    kmin = args.kcash_min_s2 if args.kcash_min_s2 is not None else config["constraints_common"]["kcash_min"]
    score = model.make_scorer(records, weights, config)
    feasible = sorted((r for r in records.values() if r["ok"]["STRESS"]), key=score, reverse=True)
    ids = [r["id"] for r in feasible]
    sel = records[selected]
    M = sel["metrics"]

    print(f"Комбинаций {len(records)}, допустимых в STRESS {len(feasible)}. Выбрана {selected}.")
    print(f"1. Балл {score(sel):.3f}, место {ids.index(selected) + 1} из {len(feasible)}. Лидер {ids[0]} ({score(feasible[0]):.3f}).")

    def dominated(a, b):
        A, B = a["metrics"], b["metrics"]
        ge = B["vpub_mrub_per_year"] >= A["vpub_mrub_per_year"] and B["c0_mrub"] <= A["c0_mrub"] and B["kcash"] >= A["kcash"]
        gt = B["vpub_mrub_per_year"] > A["vpub_mrub_per_year"] or B["c0_mrub"] < A["c0_mrub"] or B["kcash"] > A["kcash"]
        return ge and gt
    pareto = [r for r in feasible if not any(dominated(r, o) for o in feasible)]
    print(f"2. Фронт Парето (ценность, c0, cash/OPEX): {len(pareto)} недоминируемых из {len(feasible)}; "
          f"выбранная {'на фронте' if sel in pareto else 'доминируется'}.")

    rnd = random.Random(args.seed)
    keys = list(weights)
    wins: dict[str, int] = {}
    ranks: list[int] = []
    for _ in range(args.draws):
        w = renorm({k: rnd.expovariate(1.0) for k in keys})
        rk, leader = rank_under(w, records, feasible, config, selected)
        wins[leader] = wins.get(leader, 0) + 1
        ranks.append(rk)
    ranks.sort()
    print(f"3. Rank acceptability ({args.draws} случайных векторов весов, равномерно по симплексу):")
    for cid, n in sorted(wins.items(), key=lambda x: -x[1])[:5]:
        print(f"   {cid:32s} первая в {n / args.draws:6.1%}")
    print(f"   выбранная: медианное место {ranks[len(ranks) // 2]}, в топ-3 в {sum(1 for x in ranks if x <= 3) / len(ranks):.0%} случаев")

    print("4. Интервалы устойчивости весов (один вес × множитель, остальные пропорционально; выбранная в топ-3):")
    for k in keys:
        okf = [f / 100 for f in range(0, 301, 5)
               if rank_under(renorm({kk: (weights[kk] * (f / 100) if kk == k else weights[kk]) for kk in keys}), records, feasible, config, selected)[0] <= 3]
        span = f"[{min(okf):.2f}, {max(okf):.2f}]" if okf else "нигде"
        rk20 = [rank_under(renorm({kk: (weights[kk] * f if kk == k else weights[kk]) for kk in keys}), records, feasible, config, selected)[0] for f in (0.8, 1.2)]
        print(f"   {k:14s} вес {weights[k]:.2f}: топ-3 при множителе {span:14s} ±20 %: место {rk20[0]} / {rk20[1]}")

    top = feasible[0]
    print(f"5. Разница балла с лидером {top['id']} по критериям (вклад = вес × нормированное значение):")
    for k in keys:
        one = model.make_scorer(records, {k: weights[k]}, config)
        print(f"   {k:14s} {one(sel):.3f} − {one(top):.3f} = {one(sel) - one(top):+.3f}")

    anchor = anchor_only_kcash(sel, lots, modes) * M["opex_mrub_per_year"]
    comm = commercial_cash(sel, lots, modes)
    print(f"6. Поступления выбранной: якорные {anchor:.1f}, коммерческие {comm:.1f} млн руб./год "
          f"({anchor / (anchor + comm):.0%} / {comm / (anchor + comm):.0%}); OPEX {M['opex_mrub_per_year']:.1f}; cash/OPEX {M['kcash']:.3f}.")
    print(f"   S2 «коммерческая выручка = 0»: покрытие OPEX якорем {anchor / M['opex_mrub_per_year']:.3f} "
          f"({'проходит' if anchor / M['opex_mrub_per_year'] >= kmin - 1e-9 else 'не проходит'} порог {kmin}).")
    s2 = [r for r in feasible if anchor_only_kcash(r, lots, modes) >= kmin - 1e-9]
    print(f"   S2 проходят {len(s2)} из {len(feasible)} допустимых в STRESS; лучшие по баллу:")
    for r in s2[:5]:
        print(f"     {r['id']:32s} балл {score(r):.3f}, якорь/OPEX {anchor_only_kcash(r, lots, modes):.3f}, ценность {r['metrics']['vpub_mrub_per_year']:.0f}")
    if top not in s2:
        print(f"   лидер модели {top['id']} S2 не проходит: якорь/OPEX {anchor_only_kcash(top, lots, modes):.3f}.")
    if len(s2) > 1 and sel in s2:
        w2 = 0
        for _ in range(args.draws):
            w = renorm({k: rnd.expovariate(1.0) for k in keys})
            sc = model.make_scorer(records, w, config)
            w2 += max(s2, key=sc)["id"] == selected
        print(f"   среди проходящих S2 выбранная первая в {w2 / args.draws:.0%} случайных векторов весов.")
    for label, a_k, c_k in (("якорь −20 %", 0.8, 1.0), ("коммерция −50 %", 1.0, 0.5), ("якорь −20 % и коммерция −50 %", 0.8, 0.5)):
        print(f"   {label:30s} cash/OPEX {(anchor * a_k + comm * c_k) / M['opex_mrub_per_year']:.3f}")
    for k in (1.1, 1.15, 1.2):
        opex = M["opex_mrub_per_year"] * k
        print(f"   OPEX +{k - 1:.0%}: {opex:.1f} (лимит {config['constraints_common']['opex_max_mrub_per_year']}), cash/OPEX {M['cash_mrub_per_year'] / opex:.3f}")

    margin = stress_max - M["c0_mrub"]
    print(f"7. Запас по c0 в STRESS {margin:.1f} млн руб. = {margin / M['c0_mrub']:.1%} удорожания всего портфеля.")
    for l, m in sel["selection"]:
        c0 = float(lots[l]["c0_mrub"]) * float(modes[m]["k_c0"])
        print(f"   {l}:{m} c0 {c0:.1f}: ломает STRESS при удорожании этого лота на {margin / c0:.1%}")
    sets: dict[tuple, list] = {}
    for r in feasible:
        sets.setdefault(tuple(sorted(model.lot_set(r))), []).append(r)
    print("   максимум удорожания, который набор лотов выдерживает только сменой режимов:")
    for k, v in sorted(sets.items(), key=lambda kv: -max((stress_max - r["metrics"]["c0_mrub"]) / r["metrics"]["c0_mrub"] for r in kv[1])):
        best = max(v, key=lambda r: (stress_max - r["metrics"]["c0_mrub"]) / r["metrics"]["c0_mrub"])
        print(f"     {'+'.join(k):26s} {(stress_max - best['metrics']['c0_mrub']) / best['metrics']['c0_mrub']:5.1%} при {best['id']} (ценность {best['metrics']['vpub_mrub_per_year']:.0f})")

    y = args.years
    net = M["cash_mrub_per_year"] * y - M["c0_mrub"] - M["opex_mrub_per_year"] * y
    surplus = M["cash_mrub_per_year"] - M["opex_mrub_per_year"]
    print(f"8. Горизонт {y} лет без дисконтирования (допущение команды): c0 {M['c0_mrub']:.0f} + OPEX {M['opex_mrub_per_year'] * y:.0f} "
          f"против cash {M['cash_mrub_per_year'] * y:.0f}; сальдо {net:+.0f}; ценность {M['vpub_mrub_per_year'] * y:.0f} усл. млн руб. отдельно.")
    print(f"   годовой избыток cash над OPEX {surplus:+.1f}; простой срок возврата c0 "
          f"{(M['c0_mrub'] / surplus if surplus > 0 else float('inf')):.1f} лет (собственный показатель, не kcash).")

    try:
        sys.path.insert(0, str(REPO / "src"))
        from kosmo import calculate_all_scenarios as k_calc, load_case as k_load_case
        from kosmo.selection import load_selection_model, score_variants
    except Exception as e:  # движка нет в этой копии репозитория
        print(f"9. src/kosmo недоступен ({e.__class__.__name__}): сверка с движком пропущена.")
        return
    case = k_load_case(str(REPO))
    kmodel = load_selection_model(REPO / "config" / "weights.json")
    alt = json.loads((REPO / "config" / "alternatives.json").read_text(encoding="utf-8"))["variants"]
    variants = {v["name"]: [(p["lot_id"], p["mode_id"]) for p in v["selection"]] for v in alt}
    top2 = [r["id"] for r in feasible if r["id"] != selected][:2]
    extra = {f"app#{i + 1}": model.parse_id(cid) for i, cid in enumerate(top2)}

    def show(vs, label):
        ev = {n: k_calc(case, s) for n, s in vs.items()}
        print(f"   {label} (нормировка по допустимым в {kmodel.feasibility_scenario}):")
        for s in score_variants(ev, kmodel):
            m = ev[s.name]["BASE"].metrics
            a = m.anchor_cash / m.opex
            sc = f"{s.score:.3f}" if s.score is not None else "—"
            print(f"     {s.name:7s} место {s.rank} балл {sc} якорь/OPEX {a:.3f} S2 {'PASS' if a >= kmin - 1e-9 else 'FAIL'} "
                  f"STRESS {'PASS' if ev[s.name]['STRESS'].feasible else 'FAIL'}")

    print("9. Сверка с src/kosmo (config/weights.json, config/alternatives.json):")
    show(variants, "как в alternatives.json")
    show({**variants, **extra}, "плюс две лучшие по перебору app: " + ", ".join(f"{k} = {model.combo_id(v)}" for k, v in extra.items()))


if __name__ == "__main__":
    main()
