"""Enumerate every 4-lot portfolio x mode assignment for Case 02 with the organizers'
canonical case_core.py and report which pass BASE and STRESS constraints.

Usage: python tools/case02_enumerate.py
This is a feasibility pre-screen, not a recommendation: the case explicitly leaves the
selection method and its justification to the team.
"""
import collections
import itertools
import sys
import warnings
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1] / "cases" / "case02"
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")
from case_core import check_constraints, evaluate_portfolio, load_case  # noqa: E402

lots, modes, config = load_case(ROOT)
ids, ms = list(lots.lot_id), list(modes.mode_id)
rows, fails = [], collections.Counter()
for combo in itertools.combinations(ids, 4):
    for mm in itertools.product(ms, repeat=4):
        _, m = evaluate_portfolio(list(zip(combo, mm)), lots, modes, config)
        cb, cs = check_constraints(m, config, "BASE"), check_constraints(m, config, "STRESS")
        for k, ok in zip(cb.constraint, cb.ok):
            if not ok:
                fails[k] += 1
        rows.append(dict(lots="+".join(combo), modes="".join(mm), c0=round(m["c0_mrub"], 1),
                         opex=round(m["opex_mrub_per_year"], 1), vpub=round(m["vpub_mrub_per_year"], 1),
                         cash=round(m["cash_mrub_per_year"], 1), kcash=round(m["kcash"], 3),
                         t_rep=round(m["t_rep"], 3), public_core=m["public_core_lots"],
                         BASE=bool(cb.ok.all()), STRESS=bool(cs.ok.all())))
df = pd.DataFrame(rows)
print(f"combinations: {len(df)}   BASE feasible: {df.BASE.sum()}   STRESS feasible: {df.STRESS.sum()}")
print("BASE failures per constraint:", dict(fails))
print("\nLot sets with at least one feasible mode assignment:")
print(df[df.BASE].groupby("lots").agg(base_ok=("modes", "count"), stress_ok=("STRESS", "sum"),
      vpub_max=("vpub", "max"), c0_min=("c0", "min")).sort_values(["stress_ok", "base_ok"], ascending=False).to_string())
print("\nTop STRESS-feasible by public value:")
print(df[df.STRESS].sort_values("vpub", ascending=False).head(10).to_string(index=False))
out = ROOT / "results_all_portfolios.csv"
df.to_csv(out, index=False)
print(f"\nfull table written to {out}")
