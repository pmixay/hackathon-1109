import csv
import json

import pytest

from kosmo.cli import main

CUSTOM_MODE = {
    "enabled": True,
    "mode_id": "D",
    "name": "гибрид",
    "k_c0": 1.02,
    "k_opex": 1.0,
    "k_vpub": 0.9,
    "k_anchor": 0.9,
    "k_commercial": 0.5,
    "public_core": True,
    "rationale": "бесплатный базовый слой",
}


def run(capsys, *argv):
    code = main([str(item) for item in argv])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def write_custom_mode(case_root, payload):
    (case_root / "config" / "custom_mode.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_calc_default_portfolio_prints_both_scenarios(root, capsys):
    code, out, err = run(capsys, "--root", root, "calc")
    assert code == 0 and err == ""
    assert out.count("Сценарий: ") == 2
    assert "Сценарий: BASE" in out and "Сценарий: STRESS" in out
    assert "Требует управленческого обоснования" in out
    assert "[c0_funding]" in out


def test_calc_rejects_bad_token_with_exit_2(root, capsys):
    code, out, err = run(capsys, "--root", root, "calc", "--lots", "FIRE-A", "AGRI:A", "TRANS", "ENV:A")
    assert code == 2
    assert "ожидается формат ЛОТ:РЕЖИМ, получено 'FIRE-A'" in err
    assert "получено 'TRANS'" in err


def test_calc_unknown_scenario_exit_2(root, capsys):
    code, out, err = run(capsys, "--root", root, "calc", "--scenario", "CRISIS")
    assert code == 2
    assert "неизвестный сценарий 'CRISIS'" in err


def test_calc_reports_all_problems_at_once(root, capsys):
    code, out, err = run(capsys, "--root", root, "calc", "--lots", "MOON:A", "FIRE:Z", "FIRE:A")
    assert code == 2
    lines = [line for line in err.splitlines() if line.startswith("ошибка входа")]
    assert len(lines) == 4


def test_calc_json_error_goes_to_stderr_only(root, capsys):
    code, out, err = run(capsys, "--root", root, "calc", "--json", "--lots", "FIRE:A")
    assert code == 2 and out == ""
    assert "ровно 4 лота, передано 1" in err


def test_custom_mode_file_enables_mode_d(case_root, capsys):
    write_custom_mode(case_root, CUSTOM_MODE)
    code, out, err = run(capsys, "--root", case_root, "calc", "--lots", "FIRE:D", "AGRI:A", "TRANS:A", "ENV:A", "--scenario", "BASE", "--json")
    assert code == 0, err
    payload = json.loads(out)["BASE"]
    assert payload["lots"][0]["mode_id"] == "D"
    assert payload["lots"][0]["c0"] == pytest.approx(320 * 1.02)
    assert {note["code"] for note in payload["notes"]} >= {"custom_mode", "custom_mode_public_core"}


def test_mode_d_is_unknown_without_the_file(case_root, capsys):
    code, out, err = run(capsys, "--root", case_root, "calc", "--lots", "FIRE:D", "AGRI:A", "TRANS:A", "ENV:A")
    assert code == 2
    assert "неизвестный режим 'D', доступны: A, B, C" in err


def test_disabled_custom_mode_file_is_ignored(case_root, capsys):
    write_custom_mode(case_root, dict(CUSTOM_MODE, enabled=False))
    code, out, err = run(capsys, "--root", case_root, "calc", "--lots", "FIRE:D", "AGRI:A", "TRANS:A", "ENV:A")
    assert code == 2 and "доступны: A, B, C" in err


def test_invalid_custom_mode_file_exit_2(case_root, capsys):
    write_custom_mode(case_root, dict(CUSTOM_MODE, k_vpub=-1, rationale=""))
    code, out, err = run(capsys, "--root", case_root, "calc")
    assert code == 2
    assert "k_vpub" in err and "rationale" in err


def test_custom_mode_file_that_is_a_list_exit_2(case_root, capsys):
    write_custom_mode(case_root, [CUSTOM_MODE])
    code, out, err = run(capsys, "--root", case_root, "calc")
    assert code == 2
    assert "объектом JSON" in err


def test_tampered_lots_file_exit_3(case_root, capsys):
    lots = case_root / "data" / "lots.csv"
    lots.write_text(lots.read_text(encoding="utf-8").replace("FIRE,Siberian", "FIRE,Sibir"), encoding="utf-8")
    code, out, err = run(capsys, "--root", case_root, "calc")
    assert code == 3
    assert "нарушена целостность" in err and "data/lots.csv" in err


def test_unreadable_case_csv_exit_3(case_root, capsys):
    (case_root / "config" / "case_checksums.json").unlink()
    modes = case_root / "data" / "access_modes.csv"
    modes.write_text(modes.read_text(encoding="utf-8").replace("A,1.05", "A,много"), encoding="utf-8")
    code, out, err = run(capsys, "--root", case_root, "calc")
    assert code == 3
    assert "не читаются" in err and "A.k_c0" in err


def test_compare_without_weights(root, capsys):
    code, out, err = run(capsys, "--root", root, "compare")
    assert code == 0
    for name in ("FINAL", "V1", "V2", "V3", "V4", "V5", "V6"):
        assert out.count(name) == 2
    assert "Модель выбора" not in out
    assert "c0_limit" in out


def test_compare_with_weights_prints_ranking_and_sensitivity(root, capsys):
    code, out, err = run(capsys, "--root", root, "compare", "--weights", "config/weights.json")
    assert code == 0
    assert "Модель выбора: weighted_sum_minmax, допустимость по сценарию STRESS" in out
    assert "Чувствительность к весам" in out
    assert "margin:STRESS:c0_limit" in out


def test_compare_with_broken_weights_exit_2(root, tmp_path, capsys):
    weights = tmp_path / "weights.json"
    weights.write_text(json.dumps({"criteria": [{"key": "vpub", "direction": "sideways", "weight": 1}]}), encoding="utf-8")
    code, out, err = run(capsys, "--root", root, "compare", "--weights", str(weights))
    assert code == 2
    assert "direction должен быть max или min" in err


def test_enumerate_prints_counts_and_writes_csv(root, tmp_path, capsys):
    out_path = tmp_path / "enumeration.csv"
    code, out, err = run(capsys, "--root", root, "enumerate", "--out", str(out_path))
    assert code == 0
    assert "комбинаций: 5670" in out
    assert "BASE: допустимы 1031" in out
    assert "STRESS: допустимы 143" in out
    assert "'ARCTIC'" not in out.split("Частота лотов")[1]
    rows = read_csv(out_path)
    assert len(rows) == 5670
    assert sum(1 for row in rows if row["feasible_STRESS"] == "True") == 143
    assert sum(1 for row in rows if row["feasible_BASE"] == "True") == 1031
    assert set(rows[0]) >= {"lots", "modes", "c0", "vpub", "kcash", "feasible_BASE", "failed_BASE", "feasible_STRESS", "failed_STRESS"}


def test_repairs_command_for_failing_portfolio(root, capsys):
    code, out, err = run(capsys, "--root", root, "repairs", "--lots", "FIRE:A", "FLOOD:A", "TRANS:A", "ENV:A", "--limit", "3")
    assert code == 0
    assert "нарушены: c0_limit" in out
    assert "Варианты с одним изменением, проходящие STRESS" in out
    assert "FLOOD/A → AGRI/A" in out


def test_repairs_command_for_passing_portfolio(root, capsys):
    code, out, err = run(capsys, "--root", root, "repairs", "--scenario", "BASE")
    assert code == 0
    assert "Портфель проходит BASE" in out


def test_export_writes_every_artifact(case_root, capsys):
    out_dir = case_root / "out"
    code, out, err = run(capsys, "--root", case_root, "export", "--out", "out", "--skip-enumeration")
    assert code == 0, err
    names = sorted(path.name for path in out_dir.iterdir())
    assert names == ["alternatives.csv", "base.json", "ranking_full.csv", "repairs_base.csv", "repairs_stress.csv", "scores.csv", "sensitivity.csv", "sensitivity_full.csv", "stress.json"]
    base = json.loads((out_dir / "base.json").read_text(encoding="utf-8"))
    assert base["portfolio"]["name"] == "FINAL" and base["scenario"] == "BASE"
    assert base["metrics"]["c0"] == 1140.0 and base["feasible"] is True
    assert len(read_csv(out_dir / "alternatives.csv")) == 18
    scores = read_csv(out_dir / "scores.csv")
    assert {row["variant"] for row in scores} == {"FINAL", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"}
    assert next(row for row in scores if row["variant"] == "V3")["rank"] == ""
    full = read_csv(out_dir / "ranking_full.csv")
    assert len(full) == 143
    assert full[0]["variant"] == "FIRE:A|AGRI:C|TRANS:C|ENV:A"
    assert next(row for row in full if row["variant"] == "FIRE:A|AGRI:B|TRANS:B|ENV:A")["rank"] == "3"


def test_export_with_enumeration(case_root, capsys):
    code, out, err = run(capsys, "--root", case_root, "export", "--out", "full")
    assert code == 0, err
    assert len(read_csv(case_root / "full" / "enumeration.csv")) == 5670


def test_export_adds_portfolio_when_it_is_not_among_alternatives(case_root, capsys):
    portfolio = case_root / "config" / "portfolio.json"
    portfolio.write_text(json.dumps({"name": "GATE", "selection": [{"lot_id": "FLOOD", "mode_id": "A"}, {"lot_id": "AGRI", "mode_id": "A"}, {"lot_id": "TRANS", "mode_id": "A"}, {"lot_id": "ENV", "mode_id": "A"}]}), encoding="utf-8")
    code, out, err = run(capsys, "--root", case_root, "export", "--out", "out", "--skip-enumeration")
    assert code == 0, err
    rows = read_csv(case_root / "out" / "alternatives.csv")
    assert [row["variant"] for row in rows][:2] == ["GATE", "GATE"]
    assert len(rows) == 20


def test_export_with_custom_mode_records_it(case_root, capsys):
    write_custom_mode(case_root, CUSTOM_MODE)
    portfolio = case_root / "config" / "portfolio.json"
    portfolio.write_text(json.dumps({"name": "D-test", "selection": [{"lot_id": "FIRE", "mode_id": "D"}, {"lot_id": "AGRI", "mode_id": "A"}, {"lot_id": "TRANS", "mode_id": "A"}, {"lot_id": "ENV", "mode_id": "A"}]}), encoding="utf-8")
    code, out, err = run(capsys, "--root", case_root, "export", "--out", "out", "--skip-enumeration")
    assert code == 0, err
    stress = json.loads((case_root / "out" / "stress.json").read_text(encoding="utf-8"))
    assert stress["custom_modes"][0]["mode_id"] == "D"
    assert stress["custom_modes"][0]["rationale"] == "бесплатный базовый слой"


def test_variant_name_collision_exit_4(root, tmp_path, capsys):
    directory = str(tmp_path / "variants")
    assert run(capsys, "--root", root, "variant", "save", "A/B", "--lots", "FIRE:A", "AGRI:A", "TRANS:A", "ENV:A", "--directory", directory)[0] == 0
    code, out, err = run(capsys, "--root", root, "variant", "save", "A B", "--lots", "FIRE:A", "FLOOD:A", "TRANS:A", "ENV:A", "--directory", directory)
    assert code == 4
    assert "конфликт имён" in err


def test_variant_check_detects_tampering(root, tmp_path, capsys):
    directory = tmp_path / "variants"
    run(capsys, "--root", root, "variant", "save", "v1", "--lots", "FIRE:A", "AGRI:A", "TRANS:A", "ENV:A", "--directory", str(directory))
    path = directory / "v1.json"
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    snapshot["results"]["STRESS"]["metrics"]["vpub"] = 9999
    snapshot["case"]["checksums"]["data/lots.csv"] = "0" * 64
    path.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
    code, out, err = run(capsys, "--root", root, "variant", "check", "v1", "--directory", str(directory))
    assert code == 1
    assert "ОТЛИЧАЕТСЯ" in out
    assert "контрольные суммы исходных файлов изменились" in out


def test_variant_check_missing_exit_4(root, tmp_path, capsys):
    code, out, err = run(capsys, "--root", root, "variant", "check", "ghost", "--directory", str(tmp_path))
    assert code == 4 and "файл не найден" in err


def test_variant_list_with_foreign_file_exit_2(root, tmp_path, capsys):
    (tmp_path / "notes.json").write_text('{"hello": "world"}', encoding="utf-8")
    code, out, err = run(capsys, "--root", root, "variant", "list", "--directory", str(tmp_path))
    assert code == 2
    assert "notes.json: это не сохранённый вариант" in err


def test_variant_save_with_custom_mode_and_check_from_plain_case(case_root, capsys):
    write_custom_mode(case_root, CUSTOM_MODE)
    directory = case_root / "variants"
    code, out, err = run(capsys, "--root", case_root, "variant", "save", "with-d", "--lots", "FIRE:D", "AGRI:A", "TRANS:A", "ENV:A", "--directory", str(directory))
    assert code == 0, err
    (case_root / "config" / "custom_mode.json").unlink()
    code, out, err = run(capsys, "--root", case_root, "variant", "check", "with-d", "--directory", str(directory))
    assert code == 0, err
    assert "совпадает" in out


def test_missing_subcommand_is_a_usage_error(root):
    with pytest.raises(SystemExit) as error:
        main(["--root", str(root)])
    assert error.value.code == 2
