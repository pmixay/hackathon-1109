"""Собрать dashboard.json для интерфейса и (по флагу) results/ для записки.

    python app/build.py                 # app/static/data/dashboard.json
    python app/build.py --export        # + results/base.json, stress.json, alternatives.csv
    python app/build.py --selected "FIRE:A|AGRI:B|TRANS:B|ENV:A"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backend import payload  # noqa: E402

APP = Path(__file__).resolve().parent
REPO = APP.parent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selected", help="id выбранной комбинации, по умолчанию из app/config/portfolio.json")
    ap.add_argument("--out", default=str(APP / "static" / "data" / "dashboard.json"))
    ap.add_argument("--export", action="store_true", help="записать results/ (base.json, stress.json, alternatives.csv)")
    args = ap.parse_args()

    dash = payload.build_dashboard(args.selected)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(dash, f, ensure_ascii=False, indent=1)
    sel = dash["combinations"][dash["selected"]]
    print(f"{out}: выбрана {dash['selected']}, балл {sel['score']}, ранг {sel['rank']} из {dash['meta']['totals']['stress_feasible']}; "
          f"предложений {len(dash['suggestions'])}, в сравнении {len(dash['comparison'])}")
    if args.export:
        results = REPO / "results"
        payload.export_results(dash, results)
        print(f"{results}: base.json, stress.json, alternatives.csv")


if __name__ == "__main__":
    main()
