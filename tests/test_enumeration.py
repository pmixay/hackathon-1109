import pytest

from kosmo import enumerate_portfolios, failure_counts, feasible_in, lot_frequency, lot_set_summary, single_step_repairs


@pytest.fixture(scope="module")
def portfolios(case):
    return enumerate_portfolios(case)


def test_counts_match_organizers_tool(portfolios):
    assert len(portfolios) == 5670
    assert len(feasible_in(portfolios, "BASE")) == 1031
    assert len(feasible_in(portfolios, "STRESS")) == 143


def test_failure_counts_match_organizers_tool(portfolios):
    assert dict(failure_counts(portfolios, "BASE")) == {
        "public_core_lots": 3360,
        "c0_limit": 2665,
        "opex_limit": 2714,
        "vpub_floor": 642,
        "t_rep_floor": 81,
    }


def test_every_stress_feasible_is_base_feasible(portfolios):
    for portfolio in feasible_in(portfolios, "STRESS"):
        assert portfolio.feasible["BASE"]


def test_arctic_never_survives_stress(portfolios):
    assert lot_frequency(feasible_in(portfolios, "STRESS"))["ARCTIC"] == 0


def test_lot_set_summary_uses_only_admissible_assignments(portfolios):
    summary = lot_set_summary(portfolios, ["BASE", "STRESS"])
    leader = summary[0]
    assert leader["lots"] == ("FIRE", "AGRI", "TRANS", "ENV")
    assert leader["BASE"] == 33 and leader["STRESS"] == 33
    assert leader["c0_min_BASE"] == pytest.approx(1123.5)
    assert leader["vpub_max_BASE"] == pytest.approx(1370.0)
    with_ssa = next(row for row in summary if row["lots"] == ("AGRI", "INFRA", "TRANS", "SSA"))
    assert with_ssa["BASE"] == 8 and with_ssa["STRESS"] == 0
    assert with_ssa["c0_min_BASE"] == pytest.approx(1182.0)
    assert with_ssa["vpub_max_STRESS"] is None and with_ssa["c0_min_STRESS"] is None
    for row in summary:
        for scenario_id in ("BASE", "STRESS"):
            admissible = [p for p in portfolios if p.lots == row["lots"] and p.feasible[scenario_id]]
            if admissible:
                assert row[f"c0_min_{scenario_id}"] == min(p.metrics.c0 for p in admissible)
                assert row[f"vpub_max_{scenario_id}"] == max(p.metrics.vpub for p in admissible)


def test_custom_mode_extends_search_space(case):
    from kosmo import parse_custom_mode
    extended = case.with_custom_mode(parse_custom_mode({
        "mode_id": "D", "k_c0": 1.0, "k_opex": 1.0, "k_vpub": 0.9, "k_anchor": 0.9, "k_commercial": 0.5,
        "public_core": True, "rationale": "гибрид",
    }))
    assert len(enumerate_portfolios(extended)) == 70 * 4 ** 4


def test_single_step_repairs_for_v3(case, v3):
    repairs = single_step_repairs(case, v3, "STRESS")
    assert repairs
    assert all(repair.feasible["STRESS"] for repair in repairs)
    assert all(repair.change == "lot" for repair in repairs)
    assert repairs[0].selection == (("FIRE", "A"), ("AGRI", "A"), ("TRANS", "A"), ("ENV", "A"))
    assert repairs[0].delta_c0 == pytest.approx(-84.0)
    assert repairs[0].delta_vpub == pytest.approx(-370.0)


def test_mode_subset_shrinks_the_search_space(case):
    only_a = enumerate_portfolios(case, mode_ids=("A",))
    assert len(only_a) == 70
    assert all(portfolio.modes == ("A", "A", "A", "A") for portfolio in only_a)
    survivors = [portfolio.lots for portfolio in feasible_in(only_a, "STRESS")]
    assert survivors == [("FIRE", "AGRI", "TRANS", "ENV"), ("AGRI", "INFRA", "TRANS", "ENV"), ("AGRI", "TRANS", "ENV", "SSA")]


def test_lot_set_summary_totals(portfolios):
    summary = lot_set_summary(portfolios, ["BASE", "STRESS"])
    assert len(summary) == 70
    assert all(row["assignments"] == 81 for row in summary)
    assert sum(row["BASE"] for row in summary) == 1031
    assert sum(row["STRESS"] for row in summary) == 143
    counts = [(row["BASE"], row["STRESS"]) for row in summary]
    assert counts == sorted(counts, reverse=True)
    assert all(row["STRESS"] <= row["BASE"] for row in summary)


def test_lot_frequency_counts_every_portfolio_once(portfolios):
    frequency = lot_frequency(portfolios)
    assert set(frequency) == {"FIRE", "FLOOD", "AGRI", "INFRA", "ARCTIC", "TRANS", "ENV", "SSA"}
    assert all(count == 5670 * 4 // 8 for count in frequency.values())


def test_failure_counts_in_stress_only_grow_on_c0(portfolios):
    base = failure_counts(portfolios, "BASE")
    stress = failure_counts(portfolios, "STRESS")
    for code in base:
        if code == "c0_limit":
            assert stress[code] > base[code]
        else:
            assert stress[code] == base[code]
    assert set(stress) - set(base) == set()
