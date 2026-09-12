import json
import math
import random
from dataclasses import replace
from itertools import combinations, permutations, product

import pytest

from kosmo import aggregate, apply_mode, calculate, calculate_all_scenarios, enumerate_portfolios
from kosmo.checks import TOLERANCE


@pytest.fixture(scope="module")
def all_results(case):
    results = {}
    for lots in combinations(tuple(case.lots), 4):
        for modes in product(tuple(case.modes), repeat=4):
            selection = tuple(zip(lots, modes))
            results[selection] = calculate_all_scenarios(case, selection)
    return results


def test_search_space_is_complete_and_unique(all_results):
    assert len(all_results) == 5670
    for selection in all_results:
        assert len({lot_id for lot_id, _ in selection}) == 4


def test_lot_formulas_hold_for_every_lot_and_mode(case):
    for lot in case.lots.values():
        for mode in case.modes.values():
            row = apply_mode(lot, mode)
            assert row.c0 == lot.c0 * mode.k_c0
            assert row.opex == lot.opex * mode.k_opex
            assert row.vpub == lot.vpub * mode.k_vpub
            assert row.anchor_cash == lot.anchor_cash * mode.k_anchor
            assert row.commercial_cash == lot.commercial_cash * mode.k_commercial
            assert row.cash == row.anchor_cash + row.commercial_cash
            assert row.opex_gap == row.opex - row.cash
            assert row.public_core is mode.public_core
            assert (row.t_rep, row.readiness, row.resilience, row.scale) == (lot.t_rep, lot.readiness, lot.resilience, lot.scale)


def test_portfolio_totals_are_sums_of_lot_rows(all_results):
    for selection, results in all_results.items():
        result = results["BASE"]
        rows = result.lots
        metrics = result.metrics
        assert metrics.c0 == pytest.approx(sum(row.c0 for row in rows))
        assert metrics.opex == pytest.approx(sum(row.opex for row in rows))
        assert metrics.vpub == pytest.approx(sum(row.vpub for row in rows))
        assert metrics.cash == pytest.approx(sum(row.cash for row in rows))
        assert metrics.anchor_cash + metrics.commercial_cash == pytest.approx(metrics.cash)
        assert metrics.kcash == pytest.approx(metrics.cash / metrics.opex)
        assert metrics.opex_gap == pytest.approx(metrics.opex - metrics.cash)
        assert metrics.t_rep == pytest.approx(sum(row.t_rep for row in rows) / 4)
        assert metrics.selected_lots == 4
        assert metrics.public_core_lots == sum(1 for row in rows if row.public_core)
        assert metrics.capability_groups == len(metrics.capability_set)
        assert metrics.territorial_archetypes == len({row.territorial_archetype for row in rows if not row.federal})


def test_cash_comes_only_from_anchor_and_commercial(case, all_results):
    for selection, results in all_results.items():
        metrics = results["BASE"].metrics
        expected = sum(
            case.lots[lot_id].anchor_cash * case.modes[mode_id].k_anchor + case.lots[lot_id].commercial_cash * case.modes[mode_id].k_commercial
            for lot_id, mode_id in selection
        )
        assert metrics.cash == pytest.approx(expected)


def test_vpub_change_does_not_move_cash(case, v1):
    baseline = calculate(case, v1, "BASE").metrics
    doubled = {lot_id: replace(lot, vpub=lot.vpub * 2) for lot_id, lot in case.lots.items()}
    metrics = calculate(replace(case, lots=doubled), v1, "BASE").metrics
    assert metrics.vpub == pytest.approx(baseline.vpub * 2)
    assert metrics.cash == baseline.cash
    assert metrics.kcash == baseline.kcash
    assert metrics.opex_gap == baseline.opex_gap


def test_feasible_flag_agrees_with_checks_and_margins(all_results):
    for results in all_results.values():
        for result in results.values():
            failed = [check.code for check in result.checks if not check.passed]
            assert result.failed_checks == tuple(failed)
            assert result.feasible is (not failed)
            for check in result.checks:
                if check.operator == "==":
                    assert check.passed is (check.margin == 0.0)
                else:
                    assert check.passed is (check.margin >= -TOLERANCE)


def test_scenarios_share_everything_except_c0_scope(all_results):
    for results in all_results.values():
        base, stress = results["BASE"], results["STRESS"]
        assert base.metrics == stress.metrics
        assert base.lots == stress.lots
        for left, right in zip(base.checks, stress.checks):
            if left.code == "c0_limit":
                assert (left.scope, right.scope) == ("BASE", "STRESS")
                assert (left.threshold, right.threshold) == (1300.0, 1180.0)
            else:
                assert left == right
                assert left.scope == "common"
        assert set(base.failed_checks) - {"c0_limit"} == set(stress.failed_checks) - {"c0_limit"}


def test_stress_is_strictly_harder(all_results):
    stress_only_failures = 0
    for results in all_results.values():
        if results["BASE"].feasible and not results["STRESS"].feasible:
            assert results["STRESS"].failed_checks == ("c0_limit",)
            stress_only_failures += 1
        if results["STRESS"].feasible:
            assert results["BASE"].feasible
    assert stress_only_failures == 1031 - 143


def test_order_of_pairs_does_not_change_the_answer(case, all_results):
    rng = random.Random(2026)
    sample = rng.sample(sorted(all_results), 150)
    for selection in sample:
        reference = all_results[selection]
        for shuffled in list(permutations(selection))[1:4]:
            results = calculate_all_scenarios(case, shuffled)
            for scenario_id in results:
                assert results[scenario_id].metrics == reference[scenario_id].metrics
                assert results[scenario_id].checks == reference[scenario_id].checks
                assert results[scenario_id].failed_checks == reference[scenario_id].failed_checks
                assert [row.lot_id for row in results[scenario_id].lots] == [lot_id for lot_id, _ in shuffled]


def test_every_result_serializes_to_strict_json(all_results):
    for results in all_results.values():
        for result in results.values():
            payload = result.to_dict()
            text = json.dumps(payload, ensure_ascii=False, allow_nan=False)
            restored = json.loads(text)
            assert restored["metrics"]["c0"] == result.metrics.c0
            assert len(restored["checks"]) == 9
            assert all(check["status"] in ("выполнено", "нарушено") for check in restored["checks"])


def test_mode_ordering_holds_for_every_lot(case):
    for lot in case.lots.values():
        a, b, c = (apply_mode(lot, case.modes[mode_id]) for mode_id in ("A", "B", "C"))
        assert a.c0 >= b.c0 >= c.c0
        assert a.opex >= b.opex >= c.opex
        assert a.vpub > b.vpub > c.vpub
        assert a.anchor_cash > b.anchor_cash > c.anchor_cash
        assert a.commercial_cash < b.commercial_cash < c.commercial_cash
        assert a.public_core and not b.public_core and not c.public_core


def test_federal_lot_never_counts_as_territory(all_results):
    for selection, results in all_results.items():
        lots = {lot_id for lot_id, _ in selection}
        metrics = results["BASE"].metrics
        others = [row.territorial_archetype for row in results["BASE"].lots if row.lot_id != "SSA"]
        if "SSA" in lots:
            assert metrics.territorial_archetypes == len(set(others)) == 3
            assert "SSA" in metrics.capability_set
        else:
            assert metrics.territorial_archetypes == 4


def test_real_portfolios_that_sit_exactly_on_count_thresholds_pass(case):
    exactly_two_public_core = calculate(case, (("FIRE", "A"), ("AGRI", "B"), ("INFRA", "A"), ("TRANS", "B")), "BASE")
    assert exactly_two_public_core.metrics.public_core_lots == 2
    assert next(check for check in exactly_two_public_core.checks if check.code == "public_core_lots").margin == 0.0
    exactly_three_territories = calculate(case, (("AGRI", "A"), ("TRANS", "A"), ("ENV", "A"), ("SSA", "A")), "BASE")
    assert exactly_three_territories.metrics.territorial_archetypes == 3
    exactly_two_groups = calculate(case, (("FIRE", "A"), ("AGRI", "A"), ("TRANS", "A"), ("ENV", "A")), "BASE")
    assert exactly_two_groups.metrics.capability_groups == 2
    for result in (exactly_two_public_core, exactly_three_territories, exactly_two_groups):
        assert result.feasible


def test_public_core_count_equals_number_of_a_modes(all_results):
    for selection, results in all_results.items():
        public_core = sum(1 for _, mode_id in selection if mode_id == "A")
        assert results["BASE"].metrics.public_core_lots == public_core
        assert ("public_core_lots" in results["BASE"].failed_checks) is (public_core < 2)


def test_aggregate_is_linear_in_lot_values(case, v1):
    rows = [apply_mode(case.lots[lot_id], case.modes[mode_id]) for lot_id, mode_id in v1]
    scaled = [
        replace(row, c0=row.c0 * 3, opex=row.opex * 3, cash=row.cash * 3, anchor_cash=row.anchor_cash * 3, commercial_cash=row.commercial_cash * 3, vpub=row.vpub * 3)
        for row in rows
    ]
    before, after = aggregate(rows), aggregate(scaled)
    assert after.c0 == pytest.approx(before.c0 * 3)
    assert after.opex == pytest.approx(before.opex * 3)
    assert after.vpub == pytest.approx(before.vpub * 3)
    assert after.cash == pytest.approx(before.cash * 3)
    assert after.kcash == pytest.approx(before.kcash)
    assert after.t_rep == before.t_rep


def test_enumeration_agrees_with_direct_calculation(case, all_results):
    for portfolio in enumerate_portfolios(case):
        selection = tuple(zip(portfolio.lots, portfolio.modes))
        results = all_results[selection]
        assert portfolio.metrics == results["BASE"].metrics
        assert portfolio.feasible == {scenario_id: result.feasible for scenario_id, result in results.items()}
        assert portfolio.failed == {scenario_id: result.failed_checks for scenario_id, result in results.items()}


def test_kcash_is_never_undefined_on_real_data(all_results):
    for results in all_results.values():
        assert not math.isnan(results["BASE"].metrics.kcash)
        assert results["BASE"].metrics.opex > 0
