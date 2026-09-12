import json

import pytest

from kosmo import CaseFormatError, CaseIntegrityError, calculate_all_scenarios, load_case
from kosmo.case import parse_bool


def unverified(case_root):
    (case_root / "config" / "case_checksums.json").unlink()
    return case_root


def rewrite_config(case_root, mutate):
    path = case_root / "config" / "case_config.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    mutate(raw)
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")


def rewrite_csv(path, transform):
    path.write_text(transform(path.read_text(encoding="utf-8")), encoding="utf-8")


@pytest.mark.parametrize("key", ["kcash_min", "opex_max_mrub_per_year", "selected_lots_exactly"])
def test_missing_constraint_key_is_a_format_error(case_root, key):
    rewrite_config(unverified(case_root), lambda raw: raw["constraints_common"].pop(key))
    with pytest.raises(CaseFormatError, match=f"case_config.json: missing key '{key}'"):
        load_case(case_root)


def test_missing_scenarios_block_is_a_format_error(case_root):
    rewrite_config(unverified(case_root), lambda raw: raw.pop("scenarios"))
    with pytest.raises(CaseFormatError, match="missing key 'scenarios'"):
        load_case(case_root)


def test_empty_scenarios_block_is_a_format_error(case_root):
    rewrite_config(unverified(case_root), lambda raw: raw.__setitem__("scenarios", {}))
    with pytest.raises(CaseFormatError, match="no scenarios defined"):
        load_case(case_root)


def test_config_that_is_not_an_object_is_a_format_error(case_root):
    unverified(case_root)
    (case_root / "config" / "case_config.json").write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(CaseFormatError, match="unexpected structure"):
        load_case(case_root)


def test_fractional_lot_count_is_rejected(case_root):
    rewrite_config(unverified(case_root), lambda raw: raw["constraints_common"].__setitem__("selected_lots_exactly", 4.5))
    with pytest.raises(CaseFormatError, match="expected an integer"):
        load_case(case_root)


def test_extra_scenario_flows_through_the_engine(case_root):
    rewrite_config(unverified(case_root), lambda raw: raw["scenarios"].__setitem__("CRISIS", {"c0_max_mrub": 1100}))
    case = load_case(case_root)
    assert list(case.scenarios) == ["BASE", "STRESS", "CRISIS"]
    results = calculate_all_scenarios(case, (("FIRE", "A"), ("AGRI", "A"), ("TRANS", "A"), ("ENV", "A")))
    assert set(results) == {"BASE", "STRESS", "CRISIS"}
    crisis = next(check for check in results["CRISIS"].checks if check.code == "c0_limit")
    assert crisis.scope == "CRISIS" and crisis.threshold == 1100 and not crisis.passed
    assert results["CRISIS"].failed_checks == ("c0_limit",)


def test_stricter_common_constraint_changes_verdicts(case_root):
    rewrite_config(unverified(case_root), lambda raw: raw["constraints_common"].__setitem__("vpub_min_mrub_per_year", 1400))
    case = load_case(case_root)
    results = calculate_all_scenarios(case, (("FIRE", "A"), ("AGRI", "A"), ("TRANS", "A"), ("ENV", "A")))
    assert results["BASE"].failed_checks == ("vpub_floor",)


@pytest.mark.parametrize("value, expected", [("true", True), ("TRUE", True), ("1", True), ("yes", True), ("False", False), ("0", False), (" no ", False)])
def test_boolean_spellings(value, expected):
    assert parse_bool(value, "federal", "X") is expected


@pytest.mark.parametrize("value", ["maybe", "", "2", "да"])
def test_unknown_boolean_spelling_is_rejected(value):
    with pytest.raises(CaseFormatError, match="expected a boolean"):
        parse_bool(value, "federal", "X")


def test_extra_access_mode_in_csv_becomes_selectable(case_root):
    unverified(case_root)
    rewrite_csv(case_root / "data" / "access_modes.csv", lambda text: text.rstrip("\n") + "\nX,1.0,1.0,0.5,0.5,0.5,false\n")
    case = load_case(case_root)
    assert list(case.modes) == ["A", "B", "C", "X"]
    assert case.modes["X"].custom is False
    results = calculate_all_scenarios(case, (("FIRE", "X"), ("AGRI", "A"), ("TRANS", "A"), ("ENV", "A")))
    assert results["BASE"].lots[0].vpub == 280.0


def test_extra_csv_column_is_ignored(case_root):
    unverified(case_root)
    rewrite_csv(case_root / "data" / "lots.csv", lambda text: "\n".join(line + ",comment" for line in text.splitlines()) + "\n")
    assert load_case(case_root).lots["FIRE"].c0 == 320


def test_empty_capability_cell_gives_no_groups(case_root):
    unverified(case_root)
    rewrite_csv(case_root / "data" / "lots.csv", lambda text: text.replace("Siberian forest fire monitoring,EO,", "Siberian forest fire monitoring,,"))
    fire = load_case(case_root).lots["FIRE"]
    assert fire.capability_groups == () and fire.capability_set == frozenset()


def test_pnt_and_insar_listed_separately_still_count_once(case_root):
    unverified(case_root)
    rewrite_csv(case_root / "data" / "lots.csv", lambda text: text.replace("Agricultural analytics,EO;PNT/InSAR,", "Agricultural analytics,PNT;InSAR,"))
    agri = load_case(case_root).lots["AGRI"]
    assert agri.capability_groups == ("PNT", "InSAR")
    assert agri.capability_set == frozenset({"PNT/InSAR"})


def test_checksums_file_must_be_an_object(case_root):
    (case_root / "config" / "case_checksums.json").write_text('["a", "b"]', encoding="utf-8")
    with pytest.raises(CaseIntegrityError, match="must map file names"):
        load_case(case_root)


def test_missing_lots_file_is_reported(case_root):
    unverified(case_root)
    (case_root / "data" / "lots.csv").unlink()
    with pytest.raises(FileNotFoundError):
        load_case(case_root)


def test_empty_lots_table_is_rejected(case_root):
    unverified(case_root)
    rewrite_csv(case_root / "data" / "lots.csv", lambda text: text.splitlines()[0] + "\n")
    with pytest.raises(CaseFormatError, match="no lots found"):
        load_case(case_root)


def test_boolean_in_numeric_column_is_rejected(case_root):
    unverified(case_root)
    rewrite_csv(case_root / "data" / "lots.csv", lambda text: text.replace("EO,320,85,", "EO,true,85,"))
    with pytest.raises(CaseFormatError, match="FIRE.c0_mrub"):
        load_case(case_root)


def test_changed_organizer_copy_of_case_core_is_detected(case_root):
    core = case_root / "src" / "case_core.py"
    core.write_text(core.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(CaseIntegrityError, match="src/case_core.py"):
        load_case(case_root)
