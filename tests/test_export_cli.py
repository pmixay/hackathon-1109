import csv
import json

from kosmo import Variant, calculate_all_scenarios, load_selection_model, load_variants, score_variants, single_step_repairs, weight_sensitivity, parameter_sensitivity
from kosmo.cli import main
from kosmo.export import write_alternatives, write_repairs, write_scenario_results, write_scored, write_sensitivity


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_scenario_results_files(case, v1, tmp_path):
    written = write_scenario_results(case, Variant(name="V1", selection=v1), tmp_path)
    assert set(written) == {"BASE", "STRESS"}
    payload = json.loads(written["STRESS"].read_text(encoding="utf-8"))
    assert payload["scenario"] == "STRESS"
    assert payload["case"]["version"] == "1.1"
    assert payload["case"]["verified"] is True
    assert payload["portfolio"]["name"] == "V1"
    assert payload["metrics"]["c0"] == 1165.5
    assert payload["checks"][4]["threshold"] == 1180
    assert payload["custom_modes"] == []
    assert "generated_at" in payload


def test_alternatives_csv(case, root, tmp_path):
    variants = load_variants(root / "config" / "alternatives.json")
    rows = read_csv(write_alternatives(case, variants, tmp_path / "alternatives.csv"))
    assert len(rows) == 18
    v3_stress = next(row for row in rows if row["variant"] == "V3" and row["scenario"] == "STRESS")
    assert v3_stress["feasible"] == "False"
    assert v3_stress["failed_checks"] == "c0_limit"
    assert float(v3_stress["c0"]) == 1249.5


def test_scores_and_sensitivity_csv(case, root, tmp_path):
    variants = load_variants(root / "config" / "alternatives.json")
    evaluated = {variant.name: calculate_all_scenarios(case, variant.selection) for variant in variants}
    model = load_selection_model(root / "config" / "weights.json")
    scored = read_csv(write_scored(score_variants(evaluated, model), tmp_path / "scores.csv"))
    assert scored[0]["rank"] == "1"
    assert "z_vpub" in scored[0]
    rows = read_csv(write_sensitivity(weight_sensitivity(evaluated, model), parameter_sensitivity(case, variants[0].selection), tmp_path / "sensitivity.csv"))
    assert sum(1 for row in rows if row["kind"] == "weight") == 14
    assert sum(1 for row in rows if row["kind"] == "parameter") == 8


def test_repairs_csv(case, v3, tmp_path):
    scenarios = list(case.scenarios)
    rows = read_csv(write_repairs(single_step_repairs(case, v3, "STRESS"), scenarios, tmp_path / "repairs.csv"))
    assert rows and rows[0]["feasible_STRESS"] == "True"
    empty_path = write_repairs([], scenarios, tmp_path / "empty.csv")
    assert read_csv(empty_path) == []
    with empty_path.open(encoding="utf-8") as handle:
        header = handle.readline().strip().split(",")
    with (tmp_path / "repairs.csv").open(encoding="utf-8") as handle:
        assert handle.readline().strip().split(",") == header


def test_cli_calc_exit_codes(root, capsys):
    assert main(["--root", str(root), "calc", "--lots", "FIRE:A", "AGRI:A", "TRANS:A", "ENV:A", "--scenario", "BASE"]) == 0
    assert "ВЫПОЛНЕНО" in capsys.readouterr().out
    assert main(["--root", str(root), "calc", "--lots", "FIRE:A", "FLOOD:A", "TRANS:A", "ENV:A", "--scenario", "STRESS"]) == 1
    assert "c0_limit" in capsys.readouterr().out
    assert main(["--root", str(root), "calc", "--lots", "FIRE:A", "FIRE:A", "TRANS:A", "ENV:A"]) == 2
    assert "выбран повторно" in capsys.readouterr().err


def test_cli_json_output(root, capsys):
    assert main(["--root", str(root), "calc", "--scenario", "all", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert set(payload) == {"BASE", "STRESS"}
    assert payload["BASE"]["metrics"]["c0"] == 1140.0
    assert payload["BASE"]["selection"] == [{"lot_id": "FIRE", "mode_id": "A"}, {"lot_id": "ENV", "mode_id": "A"}, {"lot_id": "AGRI", "mode_id": "B"}, {"lot_id": "TRANS", "mode_id": "B"}]
    assert main(["--root", str(root), "calc", "--lots", "FIRE:A", "FLOOD:A", "TRANS:A", "ENV:A", "--scenario", "STRESS", "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["STRESS"]["failed_checks"] == ["c0_limit"]


def test_cli_reports_broken_config_cleanly(root, tmp_path, capsys):
    broken = tmp_path / "portfolio.json"
    broken.write_text("[1, 2, 3", encoding="utf-8")
    assert main(["--root", str(root), "calc", "--portfolio", str(broken)]) == 4
    assert "некорректный JSON" in capsys.readouterr().err
    broken.write_text("[1, 2, 3]", encoding="utf-8")
    assert main(["--root", str(root), "calc", "--portfolio", str(broken)]) == 2
    assert "объектом JSON" in capsys.readouterr().err
    assert main(["--root", str(root), "calc", "--portfolio", str(tmp_path / "missing.json")]) == 4
    assert "файл не найден" in capsys.readouterr().err


def test_cli_variant_roundtrip(root, tmp_path, capsys):
    directory = str(tmp_path / "variants")
    assert main(["--root", str(root), "variant", "save", "demo", "--lots", "FIRE:A", "AGRI:A", "TRANS:A", "ENV:A", "--directory", directory]) == 0
    assert main(["--root", str(root), "variant", "check", "demo", "--directory", directory]) == 0
    assert "совпадает" in capsys.readouterr().out
    assert main(["--root", str(root), "variant", "list", "--directory", directory]) == 0
    assert capsys.readouterr().out.strip() == "demo"


def test_csv_quotes_commas_and_cyrillic_in_notes(case, v1, tmp_path):
    variant = Variant(name="V1, черновик", selection=v1, note="пожары, агро; \"кавычки\"")
    rows = read_csv(write_alternatives(case, [variant], tmp_path / "alternatives.csv"))
    assert rows[0]["variant"] == "V1, черновик"
    assert rows[0]["note"] == variant.note
    assert rows[0]["lots"] == "FIRE+AGRI+TRANS+ENV" and rows[0]["modes"] == "AAAA"


def test_scored_csv_leaves_normalized_columns_empty_for_infeasible(case, root, tmp_path):
    from kosmo import parse_selection_model
    variants = load_variants(root / "config" / "alternatives.json")
    evaluated = {variant.name: calculate_all_scenarios(case, variant.selection) for variant in variants}
    model = parse_selection_model({"feasibility_scenario": "STRESS", "criteria": [{"key": "vpub", "direction": "max", "weight": 1}]})
    rows = read_csv(write_scored(score_variants(evaluated, model), tmp_path / "scores.csv"))
    v3 = next(row for row in rows if row["variant"] == "V3")
    assert v3["feasible"] == "False" and v3["rank"] == "" and v3["score"] == "" and v3["z_vpub"] == ""
    assert float(v3["vpub"]) == 1740.0


def test_alternatives_csv_columns_are_stable(case, v1, tmp_path):
    with write_alternatives(case, [Variant(name="V1", selection=v1)], tmp_path / "a.csv").open(encoding="utf-8") as handle:
        header = handle.readline().strip().split(",")
    assert header == [
        "variant", "scenario", "lots", "modes", "feasible", "failed_checks",
        "c0", "opex", "vpub", "cash", "anchor_cash", "commercial_cash", "kcash", "anchor_kcash", "opex_gap",
        "t_rep", "readiness", "resilience", "scale", "territorial_archetypes", "capability_groups", "public_core_lots", "note",
    ]


def test_generated_at_is_utc_iso_timestamp():
    from datetime import datetime
    from kosmo.export import timestamp
    value = timestamp()
    parsed = datetime.fromisoformat(value)
    assert parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0
    assert value.endswith("+00:00")


def test_scenario_results_directory_is_created(case, v1, tmp_path):
    written = write_scenario_results(case, Variant(name="V1", selection=v1), tmp_path / "deep" / "results")
    assert all(path.exists() for path in written.values())
    assert sorted(path.name for path in written.values()) == ["base.json", "stress.json"]
