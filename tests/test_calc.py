import math

import pytest

from kosmo import SelectionError, aggregate, apply_mode, calculate, calculate_all_scenarios


def test_apply_mode_fire_a(case):
    row = apply_mode(case.lots["FIRE"], case.modes["A"])
    assert row.c0 == pytest.approx(336.0)
    assert row.opex == pytest.approx(89.25)
    assert row.vpub == pytest.approx(560.0)
    assert row.anchor_cash == pytest.approx(75.0)
    assert row.commercial_cash == pytest.approx(8.75)
    assert row.cash == pytest.approx(83.75)
    assert row.opex_gap == pytest.approx(5.5)
    assert row.public_core is True
    assert row.t_rep == 0.68


def test_apply_mode_arctic_c(case):
    row = apply_mode(case.lots["ARCTIC"], case.modes["C"])
    assert row.c0 == pytest.approx(460 * 0.98)
    assert row.opex == pytest.approx(140 * 0.95)
    assert row.vpub == pytest.approx(470 * 0.62)
    assert row.cash == pytest.approx(85 * 0.45 + 135 * 0.95)
    assert row.public_core is False
    assert row.capability_set == ("PNT/InSAR", "SATCOM")


def test_portfolio_v1_aggregation(case, v1):
    result = calculate(case, v1, "BASE")
    metrics = result.metrics
    assert metrics.selected_lots == 4
    assert metrics.c0 == pytest.approx(1165.5)
    assert metrics.opex == pytest.approx(320.25)
    assert metrics.vpub == pytest.approx(1370.0)
    assert metrics.cash == pytest.approx(288.75)
    assert metrics.anchor_cash == pytest.approx(205.0)
    assert metrics.commercial_cash == pytest.approx(83.75)
    assert metrics.kcash == pytest.approx(288.75 / 320.25)
    assert metrics.opex_gap == pytest.approx(31.5)
    assert metrics.t_rep == pytest.approx(0.73)
    assert metrics.readiness == pytest.approx(4.525)
    assert metrics.resilience == pytest.approx(4.05)
    assert metrics.scale == pytest.approx(4.675)
    assert metrics.territorial_archetypes == 4
    assert metrics.capability_groups == 2
    assert metrics.capability_set == ("EO", "PNT/InSAR")
    assert metrics.public_core_lots == 4
    assert result.feasible
    assert result.failed_checks == ()


def test_federal_lot_excluded_from_territorial_count(case, v4):
    metrics = calculate(case, v4, "BASE").metrics
    assert metrics.territorial_archetypes == 3
    assert metrics.capability_set == ("EO", "PNT/InSAR", "SSA")
    assert metrics.capability_groups == 3
    assert metrics.c0 == pytest.approx(1176.0)


def test_mixed_modes_v5(case, v5):
    metrics = calculate(case, v5, "BASE").metrics
    assert metrics.public_core_lots == 2
    assert metrics.c0 == pytest.approx((320 + 310) * 1.05 + (260 + 250) * 1.0)
    assert metrics.cash == pytest.approx((75 + 55) * 1.0 + (35 + 105) * 0.25 + (30 + 45) * 0.8 + (120 + 95) * 0.7)
    assert metrics.kcash > 1.0


def test_v3_fails_only_c0_in_stress(case, v3):
    results = calculate_all_scenarios(case, v3)
    assert results["BASE"].feasible
    assert not results["STRESS"].feasible
    assert results["STRESS"].failed_checks == ("c0_limit",)
    c0_check = next(check for check in results["STRESS"].checks if check.code == "c0_limit")
    assert c0_check.actual == pytest.approx(1249.5)
    assert c0_check.threshold == 1180
    assert c0_check.margin == pytest.approx(-69.5)
    assert c0_check.status == "нарушено"


def test_scenarios_differ_only_by_c0_limit(case, v1):
    results = calculate_all_scenarios(case, v1)
    assert results["BASE"].metrics == results["STRESS"].metrics
    base = {check.code: check.threshold for check in results["BASE"].checks}
    stress = {check.code: check.threshold for check in results["STRESS"].checks}
    assert base.pop("c0_limit") == 1300
    assert stress.pop("c0_limit") == 1180
    assert base == stress


def test_result_is_json_ready(case, v1):
    payload = calculate(case, v1, "BASE").to_dict()
    assert payload["scenario"] == "BASE"
    assert payload["selection"][0] == {"lot_id": "FIRE", "mode_id": "A"}
    assert len(payload["lots"]) == 4
    assert len(payload["checks"]) == 9
    assert payload["checks"][4]["code"] == "c0_limit"
    assert payload["checks"][4]["status"] == "выполнено"
    assert payload["feasible"] is True
    assert {note["code"] for note in payload["notes"]} >= {"c0_funding", "opex_gap", "anchor_payer"}


def test_aggregate_of_nothing_has_nan_ratios():
    metrics = aggregate([])
    assert metrics.selected_lots == 0
    assert math.isnan(metrics.kcash)
    assert math.isnan(metrics.t_rep)


def test_dict_selection_is_accepted(case, v1):
    as_dicts = [{"lot_id": lot_id, "mode_id": mode_id} for lot_id, mode_id in v1]
    assert calculate(case, as_dicts, "BASE").metrics == calculate(case, v1, "BASE").metrics


def test_unknown_scenario_is_rejected(case, v1):
    with pytest.raises(SelectionError, match="неизвестный сценарий"):
        calculate(case, v1, "CRISIS")
