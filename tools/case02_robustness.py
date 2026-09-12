"""Устойчивость выбора портфеля Кейса 02: насколько рекомендация зависит от весов
и допущений. Собственный анализ команды поверх канонических формул
(src/kosmo сверен с case_core.py на всех 5670 комбинациях). Данные организаторов не меняются.

    python tools/case02_robustness.py
    python tools/case02_robustness.py --selected "FIRE:A|AGRI:C|TRANS:C|ENV:A" --draws 3000 --years 7

Что печатается (все цифры из docs/case02-unique-features.md берутся отсюда):
  1. место выбранной комбинации по баллу модели (config/weights.json) среди допустимых в STRESS;
  2. фронт Парето по (ценность выше, c0 ниже, cash/OPEX выше);
  3. rank acceptability: доля случайных векторов весов, при которых комбинация первая (подход SMAA);
  4. интервалы устойчивости весов: в каких пределах один вес меняется так, что выбранная остаётся в топ-3;
  5. из чего складывается разница балла с лидером, по критериям;
  6. структура поступлений и стресс спроса S2: покрытие OPEX только якорными платежами (диагностика, не gate);
  7. запас по c0 в STRESS: допустимое удорожание для выбранной и для каждого набора лотов;
  8. многолетняя картина без дисконтирования (допущение команды: горизонт --years);
  9. сверка с CLI движка: та же модель выбора по config/alternatives.json, с добавлением
     двух лучших по перебору комбинаций.
"""
from __future__ import annotations

import argparse
import random
import sys
from dataclasses import replace
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "app"))
from backend import model, payload  # noqa: E402
from kosmo import calculate_all_scenarios, load_variants, score_variants  # noqa: E402


def renorm(w):
    s = sum(w.values())
    return {k: v / s for k, v in w.items()}


def with_weights(sel_model, weights):
    return replace(sel_model, criteria=tuple(replace(c, weight=weights[c.key]) for c in sel_model.criteria))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selected", help="id комбинации, по умолчанию из config/portfolio.json")
    ap.add_argument("--draws", type=int, default=3000, help="число случайных векторов весов")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--years", type=int, default=7, help="горизонт многолетней картины, лет (допущение команды)")
    ap.add_argument("--kcash-min-s2", type=float, default=None, help="порог покрытия OPEX якорем в S2; по умолчанию kcash_min кейса")
    args = ap.parse_args()

    case, records = payload._enumerated()
    sel_model = replace(payload.selection_model(), feasibility_scenario="STRESS", gates_filter=False)
    model.admit(records, sel_model, "STRESS")
    weights = {c.key: c.weight for c in sel_model.criteria}
    keys = list(weights)
    selected = model.canonical_id(case, model.parse_id(args.selected)) if args.selected else model.canonical_id(case, payload.team_portfolio().selection)
    if selected not in records:
        sys.exit(f"неизвестная комбинация: {selected}")
    stress_max = case.scenarios["STRESS"].c0_max
    kmin = args.kcash_min_s2 if args.kcash_min_s2 is not None else case.constraints.kcash_min
    score, _ = model.make_scorer(records, sel_model, "STRESS")
    feasible = sorted((r for r in records.values() if r["ok"]["STRESS"]), key=score, reverse=True)
    ids = [r["id"] for r in feasible]
    sel = records[selected]
    M = sel["metrics"]
    z = {item.name: item.normalized for item in score_variants({r["id"]: r["results"] for r in feasible}, sel_model)}

    def rank_under(w, target):
        total = sum(w.values())
        scored = sorted(ids, key=lambda cid: (-sum(w[k] * z[cid][k] for k in keys) / total, cid))
        return scored.index(target) + 1, scored[0]

    print(f"Комбинаций {len(records)}, допустимых в STRESS {len(feasible)}. Выбрана {selected}.")
    print(f"1. Балл {score(sel):.3f}, место {ids.index(selected) + 1} из {len(feasible)}. Лидер {ids[0]} ({score(feasible[0]):.3f}).")

    def dominated(a, b):
        A, B = a["metrics"], b["metrics"]
        ge = B.vpub >= A.vpub and B.c0 <= A.c0 and B.kcash >= A.kcash
        gt = B.vpub > A.vpub or B.c0 < A.c0 or B.kcash > A.kcash
        return ge and gt
    pareto = [r for r in feasible if not any(dominated(r, o) for o in feasible)]
    print(f"2. Фронт Парето (ценность, c0, cash/OPEX): {len(pareto)} недоминируемых из {len(feasible)}; "
          f"выбранная {'на фронте' if sel in pareto else 'доминируется'}.")

    rnd = random.Random(args.seed)
    wins: dict[str, int] = {}
    ranks: list[int] = []
    for _ in range(args.draws):
        w = renorm({k: rnd.expovariate(1.0) for k in keys})
        rk, leader = rank_under(w, selected)
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
               if rank_under(renorm({kk: (weights[kk] * (f / 100) if kk == k else weights[kk]) for kk in keys}), selected)[0] <= 3]
        span = f"[{min(okf):.2f}, {max(okf):.2f}]" if okf else "нигде"
        rk20 = [rank_under(renorm({kk: (weights[kk] * f if kk == k else weights[kk]) for kk in keys}), selected)[0] for f in (0.8, 1.2)]
        print(f"   {k:22s} вес {weights[k]:.2f}: топ-3 при множителе {span:14s} ±20 %: место {rk20[0]} / {rk20[1]}")

    top = feasible[0]
    print(f"5. Разница балла с лидером {top['id']} по критериям (вклад = вес × нормированное значение):")
    for k in keys:
        a, b = weights[k] * z[selected][k], weights[k] * z[top["id"]][k]
        print(f"   {k:22s} {a:.3f} − {b:.3f} = {a - b:+.3f}")

    anchor, comm = M.anchor_cash, M.commercial_cash
    print(f"6. Поступления выбранной: якорные {anchor:.1f}, коммерческие {comm:.1f} млн руб./год "
          f"({anchor / (anchor + comm):.0%} / {comm / (anchor + comm):.0%}); OPEX {M.opex:.1f}; cash/OPEX {M.kcash:.3f}.")
    print(f"   S2 «коммерческая выручка = 0» (диагностика команды, на ранг не влияет): покрытие OPEX якорем {M.anchor_kcash:.3f} "
          f"({'проходит' if M.anchor_kcash >= kmin - 1e-9 else 'не проходит'} порог {kmin}).")
    s2 = [r for r in feasible if r["metrics"].anchor_kcash >= kmin - 1e-9]
    print(f"   S2 проходят {len(s2)} из {len(feasible)} допустимых в STRESS; лучшие по баллу:")
    for r in s2[:5]:
        print(f"     {r['id']:32s} балл {score(r):.3f}, якорь/OPEX {r['metrics'].anchor_kcash:.3f}, ценность {r['metrics'].vpub:.0f}")
    if top not in s2:
        print(f"   лидер модели {top['id']} S2 не проходит: якорь/OPEX {top['metrics'].anchor_kcash:.3f}.")
    if len(s2) > 1 and sel in s2:
        s2_ids = [r["id"] for r in s2]
        w2 = 0
        for _ in range(args.draws):
            w = renorm({k: rnd.expovariate(1.0) for k in keys})
            total = sum(w.values())
            w2 += max(s2_ids, key=lambda cid: (sum(w[k] * z[cid][k] for k in keys) / total, cid)) == selected
        print(f"   среди проходящих S2 выбранная первая в {w2 / args.draws:.0%} случайных векторов весов.")
    for label, a_k, c_k in (("якорь −20 %", 0.8, 1.0), ("коммерция −50 %", 1.0, 0.5), ("якорь −20 % и коммерция −50 %", 0.8, 0.5)):
        print(f"   {label:30s} cash/OPEX {(anchor * a_k + comm * c_k) / M.opex:.3f}")
    for k in (1.1, 1.15, 1.2):
        opex = M.opex * k
        print(f"   OPEX +{k - 1:.0%}: {opex:.1f} (лимит {case.constraints.opex_max}), cash/OPEX {M.cash / opex:.3f}")

    margin = stress_max - M.c0
    print(f"7. Запас по c0 в STRESS {margin:.1f} млн руб. = {margin / M.c0:.1%} удорожания всего портфеля.")
    for row in sel["detail"]:
        print(f"   {row.lot_id}:{row.mode_id} c0 {row.c0:.1f}: ломает STRESS при удорожании этого лота на {margin / row.c0:.1%}")
    sets: dict[tuple, list] = {}
    for r in feasible:
        sets.setdefault(tuple(sorted(model.lot_set(r))), []).append(r)
    print("   максимум удорожания, который набор лотов выдерживает только сменой режимов:")
    for k, v in sorted(sets.items(), key=lambda kv: -max((stress_max - r["metrics"].c0) / r["metrics"].c0 for r in kv[1])):
        best = max(v, key=lambda r: (stress_max - r["metrics"].c0) / r["metrics"].c0)
        print(f"     {'+'.join(k):26s} {(stress_max - best['metrics'].c0) / best['metrics'].c0:5.1%} при {best['id']} (ценность {best['metrics'].vpub:.0f})")

    y = args.years
    net = M.cash * y - M.c0 - M.opex * y
    surplus = M.cash - M.opex
    print(f"8. Горизонт {y} лет без дисконтирования (допущение команды): c0 {M.c0:.0f} + OPEX {M.opex * y:.0f} "
          f"против cash {M.cash * y:.0f}; сальдо {net:+.0f}; ценность {M.vpub * y:.0f} усл. млн руб. отдельно.")
    print(f"   годовой избыток cash над OPEX {surplus:+.1f}; простой срок возврата c0 "
          f"{(M.c0 / surplus if surplus > 0 else float('inf')):.1f} лет (собственный показатель, не kcash).")

    kmodel = payload.selection_model()
    variants = {v.name: list(v.selection) for v in load_variants(REPO / "config" / "alternatives.json")}
    top2 = [r["id"] for r in feasible if r["id"] != selected][:2]
    extra = {f"app#{i + 1}": model.parse_id(cid) for i, cid in enumerate(top2)}

    def show(vs, label):
        ev = {n: calculate_all_scenarios(case, s) for n, s in vs.items()}
        print(f"   {label} (нормировка по допустимым в {kmodel.feasibility_scenario}):")
        for s in score_variants(ev, kmodel):
            m = ev[s.name]["BASE"].metrics
            sc = f"{s.score:.3f}" if s.score is not None else "—"
            print(f"     {s.name:7s} место {s.rank} балл {sc} якорь/OPEX {m.anchor_kcash:.3f} S2 {'PASS' if m.anchor_kcash >= kmin - 1e-9 else 'FAIL'} "
                  f"STRESS {'PASS' if ev[s.name]['STRESS'].feasible else 'FAIL'}")

    print("9. Сверка с CLI движка (config/weights.json, config/alternatives.json):")
    show(variants, "как в alternatives.json")
    show({**variants, **extra}, "плюс две лучшие по перебору: " + ", ".join(f"{k} = {model.combo_id(v)}" for k, v in extra.items()))


if __name__ == "__main__":
    main()
