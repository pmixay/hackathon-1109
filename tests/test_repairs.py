import pytest

from kosmo import SelectionError, calculate, calculate_all_scenarios, single_step_repairs

HOPELESS = (("ARCTIC", "C"), ("SSA", "C"), ("INFRA", "C"), ("FLOOD", "C"))


def positions_changed(original, repaired):
    return [index for index, (before, after) in enumerate(zip(original, repaired)) if before != after]


@pytest.fixture(scope="module")
def v3_repairs(case):
    return single_step_repairs(case, (("FIRE", "A"), ("FLOOD", "A"), ("TRANS", "A"), ("ENV", "A")), "STRESS")


def test_every_repair_changes_exactly_one_position(v3, v3_repairs):
    for repair in v3_repairs:
        assert positions_changed(v3, repair.selection) == [next(i for i, pair in enumerate(repair.selection) if pair != v3[i])]
        assert len({lot_id for lot_id, _ in repair.selection}) == 4
        if repair.change == "mode":
            assert [lot_id for lot_id, _ in repair.selection] == [lot_id for lot_id, _ in v3]
        else:
            assert len(set(lot_id for lot_id, _ in repair.selection) ^ set(lot_id for lot_id, _ in v3)) == 2


def test_repairs_are_recomputed_through_the_shared_engine(case, v3_repairs):
    for repair in v3_repairs:
        results = calculate_all_scenarios(case, repair.selection)
        assert repair.metrics == results["STRESS"].metrics
        assert repair.feasible == {scenario_id: result.feasible for scenario_id, result in results.items()}
        assert results["STRESS"].feasible


def test_repair_deltas_match_metrics(case, v3, v3_repairs):
    original = calculate(case, v3, "STRESS").metrics
    for repair in v3_repairs:
        assert repair.delta_c0 == pytest.approx(repair.metrics.c0 - original.c0)
        assert repair.delta_opex == pytest.approx(repair.metrics.opex - original.opex)
        assert repair.delta_vpub == pytest.approx(repair.metrics.vpub - original.vpub)
        assert repair.delta_cash == pytest.approx(repair.metrics.cash - original.cash)


def test_repairs_are_sorted_by_value_then_cost(v3_repairs):
    keys = [(-repair.metrics.vpub, repair.metrics.c0, repair.description) for repair in v3_repairs]
    assert keys == sorted(keys)


def test_repairs_never_repeat_a_selection(v3_repairs):
    selections = [repair.selection for repair in v3_repairs]
    assert len(selections) == len(set(selections))


def test_mode_change_cannot_save_v3_in_stress(case, v3):
    for index in range(4):
        for mode_id in ("B", "C"):
            changed = list(v3)
            changed[index] = (v3[index][0], mode_id)
            assert not calculate(case, changed, "STRESS").feasible


def test_feasible_portfolio_lists_neighbours_that_stay_feasible(case, v1):
    repairs = single_step_repairs(case, v1, "STRESS")
    assert repairs
    assert all(repair.selection != v1 for repair in repairs)
    assert all(repair.feasible["STRESS"] and repair.feasible["BASE"] for repair in repairs)
    modes_only = [repair for repair in repairs if repair.change == "mode"]
    assert modes_only
    assert all(repair.delta_c0 < 0 for repair in modes_only)


def test_hopeless_portfolio_has_no_single_step_repair(case):
    original = calculate(case, HOPELESS, "STRESS")
    assert original.metrics.public_core_lots == 0
    assert single_step_repairs(case, HOPELESS, "STRESS") == []
    assert single_step_repairs(case, HOPELESS, "BASE") == []


def test_repairs_respect_scenario_argument(case, v3):
    base = single_step_repairs(case, v3, "BASE")
    stress = single_step_repairs(case, v3, "STRESS")
    assert len(base) > len(stress)
    assert any(repair.change == "mode" for repair in base)
    assert {repair.selection for repair in stress} <= {repair.selection for repair in base}


def test_repairs_validate_input(case):
    with pytest.raises(SelectionError, match="неизвестный сценарий"):
        single_step_repairs(case, (("FIRE", "A"), ("AGRI", "A"), ("TRANS", "A"), ("ENV", "A")), "CRISIS")
    with pytest.raises(SelectionError, match="ровно 4"):
        single_step_repairs(case, (("FIRE", "A"),), "STRESS")


def test_repair_search_space_size(case, v3):
    repairs = single_step_repairs(case, v3, "BASE")
    assert len(repairs) <= 4 * 2 + 4 * 4 * 3
