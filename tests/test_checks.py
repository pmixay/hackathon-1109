import math
from dataclasses import replace

import pytest

from kosmo import calculate, run_checks
from kosmo.checks import TOLERANCE, format_value


def check(checks, code):
    return next(item for item in checks if item.code == code)


@pytest.fixture
def base_metrics(case, v1):
    return calculate(case, v1, "BASE").metrics


@pytest.mark.parametrize("scenario_id, value, passed", [
    ("BASE", 1300, True),
    ("BASE", 1300.01, False),
    ("BASE", 1299.99, True),
    ("STRESS", 1180, True),
    ("STRESS", 1180.01, False),
    ("STRESS", 1179.99, True),
    ("STRESS", 1180 + TOLERANCE / 2, True),
    ("STRESS", 1180 + 2 * TOLERANCE, False),
])
def test_c0_limit_boundaries(case, base_metrics, scenario_id, value, passed):
    checks = run_checks(replace(base_metrics, c0=value), case.constraints, case.scenarios[scenario_id])
    item = check(checks, "c0_limit")
    assert item.passed is passed
    assert item.threshold == case.scenarios[scenario_id].c0_max
    assert item.margin == pytest.approx(item.threshold - value)
    assert item.scope == scenario_id


@pytest.mark.parametrize("value, passed", [(360, True), (360.0001, False), (359.9999, True)])
def test_opex_limit_boundaries(case, base_metrics, value, passed):
    checks = run_checks(replace(base_metrics, opex=value), case.constraints, case.scenarios["BASE"])
    assert check(checks, "opex_limit").passed is passed


@pytest.mark.parametrize("value, passed", [(1000, True), (999.9999, False), (1000.0001, True)])
def test_vpub_floor_boundaries(case, base_metrics, value, passed):
    checks = run_checks(replace(base_metrics, vpub=value), case.constraints, case.scenarios["BASE"])
    assert check(checks, "vpub_floor").passed is passed


@pytest.mark.parametrize("value, passed", [(0.6, True), (0.5999999, False), (0.6000001, True), (math.nan, False)])
def test_kcash_floor_boundaries(case, base_metrics, value, passed):
    checks = run_checks(replace(base_metrics, kcash=value), case.constraints, case.scenarios["BASE"])
    assert check(checks, "kcash_floor").passed is passed


@pytest.mark.parametrize("value, passed", [(0.63, True), (0.6299999, False), (0.6300001, True)])
def test_t_rep_floor_boundaries(case, base_metrics, value, passed):
    checks = run_checks(replace(base_metrics, t_rep=value), case.constraints, case.scenarios["BASE"])
    assert check(checks, "t_rep_floor").passed is passed


def test_kcash_boundary_is_reachable_by_real_division(case, base_metrics):
    metrics = replace(base_metrics, opex=100.0, cash=60.0, kcash=60.0 / 100.0)
    assert check(run_checks(metrics, case.constraints, case.scenarios["BASE"]), "kcash_floor").passed
    metrics = replace(base_metrics, opex=300.0, cash=180.0, kcash=180.0 / 300.0)
    assert check(run_checks(metrics, case.constraints, case.scenarios["BASE"]), "kcash_floor").passed


@pytest.mark.parametrize("code, field, value, passed", [
    ("exact_lot_count", "selected_lots", 4, True),
    ("exact_lot_count", "selected_lots", 3, False),
    ("exact_lot_count", "selected_lots", 5, False),
    ("territorial_archetypes", "territorial_archetypes", 3, True),
    ("territorial_archetypes", "territorial_archetypes", 2, False),
    ("capability_groups", "capability_groups", 2, True),
    ("capability_groups", "capability_groups", 1, False),
    ("public_core_lots", "public_core_lots", 2, True),
    ("public_core_lots", "public_core_lots", 1, False),
])
def test_count_boundaries(case, base_metrics, code, field, value, passed):
    checks = run_checks(replace(base_metrics, **{field: value}), case.constraints, case.scenarios["BASE"])
    assert check(checks, code).passed is passed


def test_all_nine_checks_present_in_canonical_order(case, base_metrics):
    codes = [item.code for item in run_checks(base_metrics, case.constraints, case.scenarios["BASE"])]
    assert codes == [
        "exact_lot_count", "territorial_archetypes", "capability_groups", "public_core_lots",
        "c0_limit", "opex_limit", "vpub_floor", "kcash_floor", "t_rep_floor",
    ]


def test_check_description_is_readable(case, base_metrics):
    item = check(run_checks(replace(base_metrics, c0=1249.5), case.constraints, case.scenarios["STRESS"]), "c0_limit")
    assert item.describe() == "Стартовые затраты портфеля: c0 = 1249.5 <= 1180 млн руб. — нарушено"


def test_format_value():
    assert format_value(1300.0) == "1300"
    assert format_value(0.9016393) == "0.9016"
    assert format_value(math.nan) == "n/a"
