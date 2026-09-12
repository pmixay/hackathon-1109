import math
import sys
from itertools import combinations, product

import pytest

from kosmo import calculate_all_scenarios

pandas = pytest.importorskip("pandas")

NUMERIC = ("c0_mrub", "opex_mrub_per_year", "vpub_mrub_per_year", "cash_mrub_per_year", "kcash", "t_rep", "readiness_1_5", "resilience_1_5", "scale_1_5")
COUNTS = ("selected_lots", "territorial_archetypes", "capability_groups", "public_core_lots")
OWN_NAMES = {
    "c0_mrub": "c0", "opex_mrub_per_year": "opex", "vpub_mrub_per_year": "vpub", "cash_mrub_per_year": "cash",
    "kcash": "kcash", "t_rep": "t_rep", "readiness_1_5": "readiness", "resilience_1_5": "resilience", "scale_1_5": "scale",
    "selected_lots": "selected_lots", "territorial_archetypes": "territorial_archetypes",
    "capability_groups": "capability_groups", "public_core_lots": "public_core_lots",
}


@pytest.fixture(scope="module")
def canonical(root):
    sys.path.insert(0, str(root / "src"))
    import case_core
    lots, modes, config = case_core.load_case(root)
    return case_core, lots, modes, config


def assert_same_as_canonical(case, canonical, selection):
    case_core, lots, modes, config = canonical
    detail, expected = case_core.evaluate_portfolio(list(selection), lots, modes, config)
    results = calculate_all_scenarios(case, selection)
    metrics = results["BASE"].metrics
    for name in NUMERIC:
        ours = getattr(metrics, OWN_NAMES[name])
        theirs = expected[name]
        if math.isnan(theirs):
            assert math.isnan(ours), name
        else:
            assert math.isclose(ours, theirs, rel_tol=1e-12, abs_tol=1e-12), (name, ours, theirs, selection)
    for name in COUNTS:
        assert getattr(metrics, OWN_NAMES[name]) == expected[name], (name, selection)
    assert list(metrics.capability_set) == expected["capability_set"]
    for row, (_, theirs) in zip(results["BASE"].lots, detail.iterrows()):
        assert row.lot_id == theirs.lot_id and row.mode_id == theirs.mode_id
        assert math.isclose(row.c0, theirs.c0_mrub, rel_tol=1e-12)
        assert math.isclose(row.opex, theirs.opex_mrub_per_year, rel_tol=1e-12)
        assert math.isclose(row.vpub, theirs.vpub_mrub_per_year, rel_tol=1e-12)
        assert math.isclose(row.cash, theirs.cash_mrub_per_year, rel_tol=1e-12)
        assert row.public_core == bool(theirs.public_core)
    for scenario_id, result in results.items():
        verdicts = case_core.check_constraints(expected, config, scenario=scenario_id)
        theirs = dict(zip(verdicts.constraint, verdicts.ok))
        ours = {check.code: check.passed for check in result.checks}
        assert ours == theirs, (scenario_id, selection)


def test_every_combination_matches_case_core(case, canonical):
    lot_ids = list(case.lots)
    mode_ids = list(case.modes)
    count = 0
    for lots in combinations(lot_ids, 4):
        for modes in product(mode_ids, repeat=4):
            assert_same_as_canonical(case, canonical, tuple(zip(lots, modes)))
            count += 1
    assert count == 5670


def test_smoke_example_from_organizers_readme(canonical):
    case_core, lots, modes, config = canonical
    detail, metrics = case_core.evaluate_portfolio([("FIRE", "A")], lots, modes, config)
    verdicts = case_core.check_constraints(metrics, config, scenario="BASE")
    assert not bool(verdicts.set_index("constraint").ok["exact_lot_count"])
