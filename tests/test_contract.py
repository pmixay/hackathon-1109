import json

import pytest

from kosmo import SelectionError, Variant, calculate, calculate_all_scenarios, load_custom_mode
from kosmo.export import result_payload

RESULT_KEYS = {"scenario", "selection", "lots", "metrics", "checks", "feasible", "failed_checks", "notes"}
LOT_KEYS = {
    "lot_id", "mode_id", "service", "territorial_archetype", "federal", "capability_groups", "capability_set",
    "public_core", "c0", "opex", "vpub", "anchor_cash", "commercial_cash", "cash", "opex_gap",
    "t_rep", "readiness", "resilience", "scale",
}
METRIC_KEYS = {
    "selected_lots", "c0", "opex", "vpub", "cash", "anchor_cash", "commercial_cash", "kcash", "opex_gap",
    "t_rep", "readiness", "resilience", "scale", "territorial_archetypes", "capability_groups", "capability_set", "public_core_lots",
}
CHECK_KEYS = {"code", "label", "metric", "operator", "threshold", "actual", "unit", "scope", "passed", "margin", "status"}
PAYLOAD_KEYS = RESULT_KEYS | {"generated_at", "case", "portfolio", "custom_modes"}


def load(root, name):
    return json.loads((root / "examples" / name).read_text(encoding="utf-8"))


def test_example_response_is_what_the_engine_produces(root, case):
    request = load(root, "request.json")
    expected = load(root, "response.json")
    variant = Variant.from_dict(request["portfolio"])
    result = calculate(case, variant.selection, request["scenario"])
    payload = json.loads(json.dumps(result_payload(case, variant, result), ensure_ascii=False))
    payload["generated_at"] = expected["generated_at"]
    assert payload == expected


def test_example_error_is_what_the_engine_produces(root, case):
    request = load(root, "request_invalid.json")
    with pytest.raises(SelectionError) as error:
        calculate(case, request["portfolio"]["selection"], request["scenario"])
    assert error.value.to_dict() == load(root, "response_invalid.json")


def test_example_request_shape(root):
    request = load(root, "request.json")
    assert set(request) == {"portfolio", "scenario", "custom_mode"}
    assert set(request["portfolio"]) == {"name", "selection", "note"}
    assert all(set(pair) == {"lot_id", "mode_id"} for pair in request["portfolio"]["selection"])
    assert request["scenario"] in ("BASE", "STRESS")


def test_output_keys_are_fixed(case, v1):
    payload = calculate(case, v1, "STRESS").to_dict()
    assert set(payload) == RESULT_KEYS
    assert all(set(row) == LOT_KEYS for row in payload["lots"])
    assert set(payload["metrics"]) == METRIC_KEYS
    assert all(set(check) == CHECK_KEYS for check in payload["checks"])
    assert all(set(note) == {"code", "message", "lots"} for note in payload["notes"])


def test_exported_payload_keys_are_fixed(case, v1):
    variant = Variant(name="V1", selection=v1)
    payload = result_payload(case, variant, calculate(case, v1, "BASE"))
    assert set(payload) == PAYLOAD_KEYS
    assert set(payload["case"]) == {"case_id", "version", "verified", "checksums"}
    assert set(payload["case"]["checksums"]) == {"data/lots.csv", "data/access_modes.csv", "config/case_config.json", "src/case_core.py"}


def test_check_rows_are_condition_threshold_fact_verdict(case, v3):
    for check in calculate(case, v3, "STRESS").to_dict()["checks"]:
        assert check["operator"] in ("==", ">=", "<=")
        assert isinstance(check["threshold"], float) and isinstance(check["actual"], float)
        assert check["status"] == ("выполнено" if check["passed"] else "нарушено")
        assert check["label"] and check["unit"]
        assert check["scope"] in ("common", "BASE", "STRESS")


def test_selection_echo_preserves_input_order(case):
    selection = (("ENV", "A"), ("FIRE", "B"), ("TRANS", "A"), ("AGRI", "A"))
    payload = calculate(case, selection, "BASE").to_dict()
    assert [(pair["lot_id"], pair["mode_id"]) for pair in payload["selection"]] == list(selection)
    assert [row["lot_id"] for row in payload["lots"]] == ["ENV", "FIRE", "TRANS", "AGRI"]


def test_documented_python_usage_works(root, case):
    custom = load_custom_mode(root / "config" / "custom_mode.json")
    working = case if custom is None else case.with_custom_mode(custom)
    result = calculate(working, [("FIRE", "A"), ("AGRI", "A"), ("TRANS", "A"), ("ENV", "A")], "STRESS")
    assert result.to_dict()["feasible"] is True
    both = calculate_all_scenarios(working, [{"lot_id": "FIRE", "mode_id": "A"}, {"lot_id": "AGRI", "mode_id": "A"}, {"lot_id": "TRANS", "mode_id": "A"}, {"lot_id": "ENV", "mode_id": "A"}])
    assert set(both) == {"BASE", "STRESS"}


def test_results_folder_matches_current_engine(root, case):
    for scenario_id in ("BASE", "STRESS"):
        stored = json.loads((root / "results" / f"{scenario_id.lower()}.json").read_text(encoding="utf-8"))
        variant = Variant.from_dict(stored["portfolio"])
        fresh = json.loads(json.dumps(result_payload(case, variant, calculate(case, variant.selection, scenario_id)), ensure_ascii=False))
        fresh["generated_at"] = stored["generated_at"]
        assert fresh == stored
