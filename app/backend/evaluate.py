from __future__ import annotations

from pathlib import Path

from kosmo import Case, calculate_all_scenarios, load_case as _load_case, load_custom_mode

REPO = Path(__file__).resolve().parents[2]
CASE_DIR = REPO

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

OPERATORS = {"==": "=", "<=": "<=", ">=": ">="}


def load_case(root: Path = CASE_DIR) -> Case:
    root = Path(root)
    case = _load_case(root)
    custom = load_custom_mode(root / "config" / "custom_mode.json")
    if custom is not None:
        case = case.with_custom_mode(custom)
    return case


def evaluate_portfolio(selection, case: Case) -> dict:
    return calculate_all_scenarios(case, list(selection))


def check_details(result) -> list:
    return [
        {"id": check.code, "ok": check.passed, "fact": check.actual, "op": OPERATORS[check.operator], "threshold": check.threshold}
        for check in result.checks
    ]


def check_constraints(result) -> list:
    return [{"constraint": row["id"], "ok": row["ok"]} for row in check_details(result)]
