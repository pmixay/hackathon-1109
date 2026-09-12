"""Собрать dashboard.json для интерфейса и (по флагу) results/ для записки.

    python app/build.py                 # app/static/data/dashboard.json
    python app/build.py --export        # + results/ движком kosmo (как python -m kosmo export)
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
    ap.add_argument("--selected", help="id выбранной комбинации, по умолчанию из config/portfolio.json")
    ap.add_argument("--out", default=str(APP / "static" / "data" / "dashboard.json"))
    ap.add_argument("--export", action="store_true", help="записать results/ движком kosmo")
    ap.add_argument("--enumeration", action="store_true", help="вместе с --export записать results/enumeration.csv")
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
        written = payload.export_results(dash, REPO / "results", with_enumeration=args.enumeration)
        print(f"{REPO / 'results'}: " + ", ".join(sorted(Path(p).name for p in written.values())))


if __name__ == "__main__":
    main()
