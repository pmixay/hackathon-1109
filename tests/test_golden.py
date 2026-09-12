from dataclasses import replace

import pytest

from kosmo import calculate, calculate_all_scenarios, load_variants

GOLDEN = {
    "FINAL": dict(c0=1140.0, opex=313.0, vpub=1289.0, cash=370.5, t_rep=0.73, public_core_lots=2, base=True, stress=True),
    "V1": dict(c0=1165.5, opex=320.25, vpub=1370.0, cash=288.75, t_rep=0.73, public_core_lots=4, base=True, stress=True),
    "V2": dict(c0=1174.0, opex=322.0, vpub=1370.4, cash=335.0, t_rep=0.715, public_core_lots=3, base=True, stress=True),
    "V3": dict(c0=1249.5, opex=336.0, vpub=1740.0, cash=325.0, t_rep=0.70, public_core_lots=4, base=True, stress=False),
    "V4": dict(c0=1176.0, opex=330.75, vpub=1150.0, cash=295.0, t_rep=0.72, public_core_lots=4, base=True, stress=True),
    "V5": dict(c0=1171.5, opex=318.25, vpub=1229.0, cash=375.5, t_rep=0.725, public_core_lots=2, base=True, stress=True),
    "V6": dict(c0=1155.0, opex=315.0, vpub=1110.0, cash=286.25, t_rep=0.7375, public_core_lots=4, base=True, stress=True),
    "V7": dict(c0=1129.8, opex=305.75, vpub=1199.0, cash=398.0, t_rep=0.73, public_core_lots=2, base=True, stress=True),
    "V8": dict(c0=1134.8, opex=309.25, vpub=1243.0, cash=390.0, t_rep=0.73, public_core_lots=2, base=True, stress=True),
}


@pytest.fixture(scope="module")
def alternatives(root):
    return {variant.name: variant for variant in load_variants(root / "config" / "alternatives.json")}


@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_hand_computed_numbers_for_each_alternative(case, alternatives, name):
    expected = GOLDEN[name]
    results = calculate_all_scenarios(case, alternatives[name].selection)
    metrics = results["BASE"].metrics
    assert metrics.c0 == pytest.approx(expected["c0"])
    assert metrics.opex == pytest.approx(expected["opex"])
    assert metrics.vpub == pytest.approx(expected["vpub"])
    assert metrics.cash == pytest.approx(expected["cash"])
    assert metrics.kcash == pytest.approx(expected["cash"] / expected["opex"])
    assert metrics.t_rep == pytest.approx(expected["t_rep"])
    assert metrics.public_core_lots == expected["public_core_lots"]
    assert results["BASE"].feasible is expected["base"]
    assert results["STRESS"].feasible is expected["stress"]


def test_v3_is_the_only_alternative_that_fails_stress(case, alternatives):
    failing = [name for name, variant in alternatives.items() if not calculate(case, variant.selection, "STRESS").feasible]
    assert failing == ["V3"]


def test_final_and_v5_sit_exactly_on_two_public_core(case, alternatives):
    counts = {name: calculate(case, variant.selection, "BASE").metrics.public_core_lots for name, variant in alternatives.items()}
    assert [name for name, count in counts.items() if count == 2] == ["FINAL", "V5", "V7", "V8"]
    assert all(count >= 2 for count in counts.values())


def test_stress_margins_of_alternatives(case, alternatives):
    margins = {}
    for name, variant in alternatives.items():
        check = next(item for item in calculate(case, variant.selection, "STRESS").checks if item.code == "c0_limit")
        margins[name] = check.margin
    assert margins == pytest.approx({"FINAL": 40.0, "V1": 14.5, "V2": 6.0, "V3": -69.5, "V4": 4.0, "V5": 8.5, "V6": 25.0, "V7": 50.2, "V8": 45.2})


def test_limit_reached_exactly_through_summation_passes(case):
    lots = dict(case.lots)
    lots["FIRE"] = replace(lots["FIRE"], c0=(1180 - 200) / 1.05)
    lots["AGRI"] = replace(lots["AGRI"], c0=100 / 1.05)
    lots["TRANS"] = replace(lots["TRANS"], c0=70 / 1.05)
    lots["ENV"] = replace(lots["ENV"], c0=30 / 1.05)
    tuned = replace(case, lots=lots)
    result = calculate(tuned, (("FIRE", "A"), ("AGRI", "A"), ("TRANS", "A"), ("ENV", "A")), "STRESS")
    check = next(item for item in result.checks if item.code == "c0_limit")
    assert check.actual == pytest.approx(1180.0)
    assert check.passed
    assert abs(check.margin) < 1e-9


def test_kcash_floor_reached_exactly_through_division_passes(case):
    lots = dict(case.lots)
    for lot_id in ("FIRE", "AGRI", "TRANS", "ENV"):
        lot = lots[lot_id]
        lots[lot_id] = replace(lot, opex=100.0 / 1.05, anchor_cash=60.0, commercial_cash=0.0)
    tuned = replace(case, lots=lots)
    result = calculate(tuned, (("FIRE", "A"), ("AGRI", "A"), ("TRANS", "A"), ("ENV", "A")), "BASE")
    check = next(item for item in result.checks if item.code == "kcash_floor")
    assert check.actual == pytest.approx(0.6)
    assert check.passed


def test_just_past_every_threshold_fails(case, v1):
    baseline = calculate(case, v1, "BASE").metrics
    limits = case.constraints
    lots = dict(case.lots)
    lots["FIRE"] = replace(lots["FIRE"], opex=(limits.opex_max + 0.01 - (baseline.opex - 89.25)) / 1.05)
    over_opex = calculate(replace(case, lots=lots), v1, "BASE")
    assert over_opex.failed_checks == ("opex_limit",)
    lots = dict(case.lots)
    lots["FIRE"] = replace(lots["FIRE"], vpub=560 - (baseline.vpub - limits.vpub_min) - 0.01)
    under_vpub = calculate(replace(case, lots=lots), v1, "BASE")
    assert under_vpub.failed_checks == ("vpub_floor",)
    lots = dict(case.lots)
    lots["FIRE"] = replace(lots["FIRE"], t_rep=0.68 - (baseline.t_rep - limits.t_rep_min) * 4 - 0.01)
    under_t_rep = calculate(replace(case, lots=lots), v1, "BASE")
    assert under_t_rep.failed_checks == ("t_rep_floor",)
