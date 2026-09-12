import pytest

from kosmo import (
    WeightsError,
    calculate_all_scenarios,
    load_selection_model,
    load_variants,
    parameter_sensitivity,
    parse_selection_model,
    score_variants,
    weight_sensitivity,
)
from kosmo.selection import criterion_value, normalize


@pytest.fixture(scope="module")
def evaluated(case, root):
    return {variant.name: calculate_all_scenarios(case, variant.selection) for variant in load_variants(root / "config" / "alternatives.json")}


@pytest.fixture(scope="module")
def model(root):
    return load_selection_model(root / "config" / "weights.json")


def test_normalize_directions():
    values = {"a": 10.0, "b": 20.0, "c": 30.0}
    assert normalize(values, "max") == {"a": 0.0, "b": 0.5, "c": 1.0}
    assert normalize(values, "min") == {"a": 1.0, "b": 0.5, "c": 0.0}
    assert normalize({"a": 5.0, "b": 5.0}, "max") == {"a": 1.0, "b": 1.0}
    assert normalize({}, "max") == {}


def test_margin_criterion_reads_stress_check(evaluated):
    assert criterion_value(evaluated["V3"], "margin:STRESS:c0_limit", "BASE") == pytest.approx(-69.5)
    assert criterion_value(evaluated["V1"], "margin:STRESS:c0_limit", "BASE") == pytest.approx(14.5)
    assert criterion_value(evaluated["V1"], "vpub", "BASE") == 1370.0
    with pytest.raises(KeyError):
        criterion_value(evaluated["V1"], "profit", "BASE")


def test_scores_are_bounded_and_ranked(evaluated, model):
    scored = score_variants(evaluated, model)
    assert [item.name for item in scored][:3] == ["V8", "FINAL", "V7"]
    ranks = [item.rank for item in scored]
    assert ranks == [1, 2, 3, 4, 5, 6, 7, 8, None]
    for item in scored:
        if not item.feasible:
            assert item.score is None and item.normalized == {}
            continue
        assert 0.0 <= item.score <= 1.0
        for value in item.normalized.values():
            assert 0.0 <= value <= 1.0


def test_infeasible_variant_is_excluded_from_ranking(evaluated):
    model = parse_selection_model({"feasibility_scenario": "STRESS", "criteria": [{"key": "vpub", "direction": "max", "weight": 1.0}]})
    scored = score_variants(evaluated, model)
    v3 = next(item for item in scored if item.name == "V3")
    assert v3.feasible is False and v3.rank is None and v3.score is None
    assert scored[0].name == "V2"
    assert scored[-1].name == "V3"


def test_single_criterion_picks_extreme(evaluated):
    model = parse_selection_model({"criteria": [{"key": "c0", "direction": "min", "weight": 1.0}]})
    assert score_variants(evaluated, model)[0].name == "V7"
    model = parse_selection_model({"criteria": [{"key": "vpub", "direction": "max", "weight": 1.0}]})
    assert score_variants(evaluated, model)[0].name == "V3"


def test_weight_scaling_is_invariant(evaluated, model):
    doubled = parse_selection_model({
        "feasibility_scenario": model.feasibility_scenario,
        "criteria": [{"key": c.key, "direction": c.direction, "weight": c.weight * 2} for c in model.criteria],
    })
    original = {item.name: item.score for item in score_variants(evaluated, model)}
    scaled = {item.name: item.score for item in score_variants(evaluated, doubled)}
    for name in original:
        assert original[name] == pytest.approx(scaled[name])


def test_weight_sensitivity_shape(evaluated, model):
    rows = weight_sensitivity(evaluated, model)
    assert len(rows) == 2 * len(model.criteria)
    assert {row.factor for row in rows} == {0.8, 1.2}
    assert all(row.leader is not None for row in rows)


def test_parameter_sensitivity_v1(case, v1):
    rows = parameter_sensitivity(case, v1)
    assert len(rows) == 2 * 2 * 2
    cash_down_base = next(row for row in rows if row.parameter == "cash" and row.factor == 0.8 and row.scenario == "BASE")
    assert cash_down_base.feasible
    vpub_down = [row for row in rows if row.parameter == "vpub" and row.factor == 0.8]
    assert all(row.feasible for row in vpub_down)


def test_parameter_sensitivity_detects_broken_floor(case, v4):
    rows = parameter_sensitivity(case, v4, parameters=("vpub",), delta=0.2)
    down = next(row for row in rows if row.factor == 0.8 and row.scenario == "BASE")
    assert not down.feasible
    assert down.failed_checks == ("vpub_floor",)


@pytest.mark.parametrize("raw, fragment", [
    ([], "объектом JSON"),
    ({"criteria": {"key": "vpub"}}, "ожидается список критериев"),
    ({"criteria": ["vpub"]}, "ожидается объект с полями"),
    ({"criteria": []}, "список критериев пуст"),
    ({"criteria": [{"key": "vpub", "direction": "up", "weight": 1}]}, "direction должен быть max или min"),
    ({"criteria": [{"key": "vpub", "direction": "max", "weight": -1}]}, "weight должен быть неотрицательным"),
    ({"criteria": [{"key": "vpub", "direction": "max", "weight": 0}]}, "сумма весов должна быть больше нуля"),
    ({"criteria": [{"key": "vpub", "direction": "max", "weight": 1}, {"key": "vpub", "direction": "max", "weight": 1}]}, "повторяется"),
])
def test_invalid_weights(raw, fragment):
    with pytest.raises(WeightsError) as error:
        parse_selection_model(raw)
    assert any(fragment in problem for problem in error.value.problems)


def test_repo_weights_sum_to_one_and_rank_all_alternatives(model, evaluated):
    assert model.total_weight == pytest.approx(1.0)
    assert model.feasibility_scenario == "STRESS"
    scored = score_variants(evaluated, model)
    assert sorted(item.name for item in scored) == ["FINAL", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"]
    assert scored[0].name == "V8"
    assert [item.name for item in scored if item.rank in (1, 2, 3)] == ["V8", "FINAL", "V7"]
    assert next(item for item in scored if item.name == "V3").feasible is False
    feasible_scores = [item.score for item in scored if item.feasible]
    assert feasible_scores == sorted(feasible_scores, reverse=True)


def test_scores_and_values_are_consistent(model, evaluated):
    for item in score_variants(evaluated, model):
        if not item.feasible:
            assert item.score is None and item.normalized == {}
            continue
        expected = sum(c.weight * item.normalized[c.key] for c in model.criteria) / model.total_weight
        assert item.score == pytest.approx(expected)
        assert item.values["vpub"] == evaluated[item.name]["BASE"].metrics.vpub
        assert item.values["margin:STRESS:c0_limit"] == pytest.approx(1180 - evaluated[item.name]["BASE"].metrics.c0)


def test_identical_variants_tie_and_break_by_name(evaluated):
    twins = {"beta": evaluated["V1"], "alpha": evaluated["V1"], "V3": evaluated["V3"]}
    model = parse_selection_model({"criteria": [{"key": "vpub", "direction": "max", "weight": 1}, {"key": "c0", "direction": "min", "weight": 1}]})
    scored = score_variants(twins, model)
    alpha, beta = (next(item for item in scored if item.name == name) for name in ("alpha", "beta"))
    assert alpha.score == beta.score
    assert alpha.rank + 1 == beta.rank


def test_no_feasible_candidates_gives_no_ranks(evaluated):
    only_v3 = {"V3": evaluated["V3"]}
    model = parse_selection_model({"feasibility_scenario": "STRESS", "criteria": [{"key": "vpub", "direction": "max", "weight": 1}]})
    scored = score_variants(only_v3, model)
    assert scored[0].rank is None and scored[0].score is None and scored[0].normalized == {}
    assert weight_sensitivity(only_v3, model)[0].leader is None


def test_single_candidate_scores_one(evaluated, model):
    scored = score_variants({"V1": evaluated["V1"]}, model)
    assert scored[0].score == pytest.approx(1.0) and scored[0].rank == 1


def test_criterion_with_equal_values_does_not_break_ranking(evaluated):
    model = parse_selection_model({"criteria": [{"key": "selected_lots", "direction": "max", "weight": 1}, {"key": "vpub", "direction": "max", "weight": 1}]})
    scored = score_variants(evaluated, model)
    assert all(item.normalized["selected_lots"] == 1.0 for item in scored)
    assert scored[0].name == "V3"


def test_unknown_margin_scenario_or_check(evaluated):
    with pytest.raises(KeyError):
        criterion_value(evaluated["V1"], "margin:CRISIS:c0_limit", "BASE")
    with pytest.raises(KeyError, match="unknown check"):
        criterion_value(evaluated["V1"], "margin:STRESS:profit", "BASE")


def test_weight_sensitivity_rows_are_consistent(evaluated, model):
    baseline = score_variants(evaluated, model)[0].name
    for row in weight_sensitivity(evaluated, model):
        criterion = next(c for c in model.criteria if c.key == row.key)
        assert row.weight == pytest.approx(criterion.weight * row.factor)
        assert row.leader_changed is (row.leader != baseline)
        assert row.ranking[0] == row.leader
        assert sorted(row.ranking) == sorted(name for name in evaluated if evaluated[name][model.feasibility_scenario].feasible)


def test_single_criterion_is_immune_to_its_own_weight(evaluated):
    model = parse_selection_model({"criteria": [{"key": "c0", "direction": "min", "weight": 0.5}]})
    rows = weight_sensitivity(evaluated, model, delta=0.9)
    assert all(not row.leader_changed for row in rows)
    assert {row.ranking for row in rows} == {tuple(item.name for item in score_variants(evaluated, model) if item.rank)}


def test_parameter_sensitivity_opex_and_c0(case, v1):
    rows = parameter_sensitivity(case, v1, parameters=("opex", "c0"), delta=0.2)
    opex_up = [row for row in rows if row.parameter == "opex" and row.factor == 1.2]
    assert all(row.failed_checks == ("opex_limit",) for row in opex_up)
    c0_up = {row.scenario: row for row in rows if row.parameter == "c0" and row.factor == 1.2}
    assert c0_up["BASE"].failed_checks == ("c0_limit",) and c0_up["STRESS"].failed_checks == ("c0_limit",)
    c0_down = [row for row in rows if row.parameter == "c0" and row.factor == 0.8]
    assert all(row.feasible for row in c0_down)


def test_parameter_sensitivity_keeps_ratio_consistent(case, v1):
    from kosmo.selection import perturb
    from kosmo import calculate
    metrics = calculate(case, v1, "BASE").metrics
    cash_down = perturb(metrics, "cash", 0.5)
    assert cash_down.kcash == pytest.approx(metrics.kcash * 0.5)
    assert cash_down.opex_gap == pytest.approx(metrics.opex - metrics.cash * 0.5)
    assert cash_down.anchor_cash + cash_down.commercial_cash == pytest.approx(cash_down.cash)
    opex_up = perturb(metrics, "opex", 2.0)
    assert opex_up.kcash == pytest.approx(metrics.kcash / 2)
    assert opex_up.c0 == metrics.c0
    with pytest.raises(KeyError, match="unsupported parameter"):
        perturb(metrics, "vpub_per_capita", 1.0)


def test_parameter_sensitivity_validates_selection(case):
    from kosmo import SelectionError
    with pytest.raises(SelectionError):
        parameter_sensitivity(case, [("FIRE", "A")])


def test_with_weight_replaces_only_the_named_criterion(model):
    changed = model.with_weight("vpub", 0.9)
    assert next(c.weight for c in changed.criteria if c.key == "vpub") == 0.9
    assert [c.weight for c in changed.criteria if c.key != "vpub"] == [c.weight for c in model.criteria if c.key != "vpub"]
    assert model.with_weight("nope", 1.0) == model


def test_rationales_survive_parsing(model):
    assert all(c.rationale for c in model.criteria)
