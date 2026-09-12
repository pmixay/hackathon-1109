import json
from dataclasses import replace

import pytest

from kosmo import CustomModeError, calculate, load_custom_mode, parse_custom_mode

VALID = {
    "mode_id": "D",
    "name": "гибрид",
    "k_c0": 1.02,
    "k_opex": 1.0,
    "k_vpub": 0.9,
    "k_anchor": 0.9,
    "k_commercial": 0.5,
    "public_core": True,
    "rationale": "бесплатный базовый слой, платные расширенные функции",
}


def test_parse_valid_custom_mode():
    mode = parse_custom_mode(VALID)
    assert mode.mode_id == "D"
    assert mode.custom is True
    assert mode.public_core is True
    assert (mode.k_c0, mode.k_opex, mode.k_vpub, mode.k_anchor, mode.k_commercial) == (1.02, 1.0, 0.9, 0.9, 0.5)


@pytest.mark.parametrize("field, value, fragment", [
    ("k_c0", None, "k_c0: коэффициент не задан"),
    ("k_opex", "1.0", "k_opex: ожидается конечное число"),
    ("k_vpub", 0, "k_vpub: коэффициент должен быть больше нуля"),
    ("k_anchor", -0.1, "k_anchor: коэффициент не может быть отрицательным"),
    ("k_commercial", float("inf"), "k_commercial: ожидается конечное число"),
    ("k_commercial", True, "k_commercial: ожидается конечное число"),
    ("public_core", "yes", "public_core: ожидается true или false"),
    ("rationale", "", "rationale: обоснование пользовательского режима обязательно"),
    ("mode_id", "A", "mode_id: A занят каноническим режимом"),
])
def test_invalid_custom_mode(field, value, fragment):
    raw = dict(VALID, **{field: value})
    with pytest.raises(CustomModeError) as error:
        parse_custom_mode(raw)
    assert any(fragment in problem for problem in error.value.problems)


def test_all_problems_reported_at_once():
    raw = dict(VALID, k_c0=None, k_opex=None, rationale="")
    with pytest.raises(CustomModeError) as error:
        parse_custom_mode(raw)
    assert len(error.value.problems) == 3


def test_missing_file_means_no_custom_mode(tmp_path):
    assert load_custom_mode(tmp_path / "custom_mode.json") is None


def test_disabled_file_means_no_custom_mode(tmp_path):
    path = tmp_path / "custom_mode.json"
    path.write_text(json.dumps(dict(VALID, enabled=False)), encoding="utf-8")
    assert load_custom_mode(path) is None


def test_example_file_parses(root):
    mode = load_custom_mode(root / "config" / "custom_mode.example.json")
    assert mode is not None and mode.mode_id == "D"


def test_custom_mode_participates_in_calculation(case):
    extended = case.with_custom_mode(parse_custom_mode(VALID))
    result = calculate(extended, [("FIRE", "D"), ("AGRI", "A"), ("TRANS", "A"), ("ENV", "A")], "BASE")
    fire = result.lots[0]
    assert fire.mode_id == "D"
    assert fire.c0 == pytest.approx(320 * 1.02)
    assert fire.vpub == pytest.approx(560 * 0.9)
    assert fire.cash == pytest.approx(75 * 0.9 + 35 * 0.5)
    assert result.metrics.public_core_lots == 4
    codes = [note.code for note in result.notes]
    assert "custom_mode" in codes
    assert "custom_mode_public_core" in codes
    assert "custom_mode_range" not in codes


def test_out_of_range_coefficient_is_flagged(case):
    extended = case.with_custom_mode(parse_custom_mode(dict(VALID, k_c0=0.9)))
    result = calculate(extended, [("FIRE", "D"), ("AGRI", "A"), ("TRANS", "A"), ("ENV", "A")], "BASE")
    ranges = [note for note in result.notes if note.code == "custom_mode_range"]
    assert len(ranges) == 1
    assert "k_c0=0.9" in ranges[0].message
    assert "[0.98; 1.05]" in ranges[0].message
    assert ranges[0].lots == ("FIRE",)


def test_canonical_mode_cannot_be_overridden(case):
    forged = replace(parse_custom_mode(VALID), mode_id="A")
    with pytest.raises(ValueError, match="canonical"):
        case.with_custom_mode(forged)
    with pytest.raises(ValueError, match="not marked as custom"):
        case.with_custom_mode(case.modes["B"])


def test_file_that_is_not_an_object_is_rejected(tmp_path):
    path = tmp_path / "custom_mode.json"
    path.write_text(json.dumps([VALID]), encoding="utf-8")
    with pytest.raises(CustomModeError, match="объектом JSON"):
        load_custom_mode(path)


@pytest.mark.parametrize("value", [False, 0, "false", "no", "0", ""])
def test_enabled_spellings_that_disable(tmp_path, value):
    path = tmp_path / "custom_mode.json"
    path.write_text(json.dumps(dict(VALID, enabled=value)), encoding="utf-8")
    assert load_custom_mode(path) is None


@pytest.mark.parametrize("value", [True, 1, "true", "yes"])
def test_enabled_spellings_that_enable(tmp_path, value):
    path = tmp_path / "custom_mode.json"
    path.write_text(json.dumps(dict(VALID, enabled=value)), encoding="utf-8")
    assert load_custom_mode(path).mode_id == "D"


def test_mode_id_is_stripped_and_defaults_to_d():
    assert parse_custom_mode(dict(VALID, mode_id=" D ")).mode_id == "D"
    raw = dict(VALID)
    raw.pop("mode_id")
    assert parse_custom_mode(raw).mode_id == "D"
    with pytest.raises(CustomModeError, match="пустой идентификатор"):
        parse_custom_mode(dict(VALID, mode_id="  "))


def test_missing_public_core_is_reported():
    raw = dict(VALID)
    raw.pop("public_core")
    with pytest.raises(CustomModeError, match="public_core: ожидается true или false"):
        parse_custom_mode(raw)


def test_integer_coefficients_are_accepted_as_floats():
    mode = parse_custom_mode(dict(VALID, k_c0=1, k_opex=1, k_vpub=1, k_anchor=1, k_commercial=0))
    assert (mode.k_c0, mode.k_commercial) == (1.0, 0.0)
    assert isinstance(mode.k_c0, float)


def test_zero_anchor_and_commercial_are_allowed(case):
    extended = case.with_custom_mode(parse_custom_mode(dict(VALID, k_anchor=0, k_commercial=0)))
    result = calculate(extended, [("FIRE", "D"), ("AGRI", "A"), ("TRANS", "A"), ("ENV", "A")], "BASE")
    assert result.lots[0].cash == 0.0
    assert result.lots[0].opex_gap == result.lots[0].opex


def test_coefficients_on_canonical_boundary_are_not_flagged(case):
    edge = dict(VALID, k_c0=1.05, k_opex=0.95, k_vpub=0.62, k_anchor=1.0, k_commercial=0.95)
    extended = case.with_custom_mode(parse_custom_mode(edge))
    result = calculate(extended, [("FIRE", "D"), ("AGRI", "A"), ("TRANS", "A"), ("ENV", "A")], "BASE")
    assert "custom_mode_range" not in [note.code for note in result.notes]


def test_every_out_of_range_coefficient_gets_its_own_note(case):
    wild = dict(VALID, k_c0=2.0, k_opex=0.5, k_vpub=1.5, k_anchor=0.1, k_commercial=1.2)
    extended = case.with_custom_mode(parse_custom_mode(wild))
    result = calculate(extended, [("FIRE", "D"), ("AGRI", "A"), ("TRANS", "A"), ("ENV", "A")], "BASE")
    flagged = sorted(note.message.split("=")[0].split()[-1] for note in result.notes if note.code == "custom_mode_range")
    assert flagged == ["k_anchor", "k_c0", "k_commercial", "k_opex", "k_vpub"]


def test_two_custom_modes_coexist(case):
    first = parse_custom_mode(VALID)
    second = parse_custom_mode(dict(VALID, mode_id="E", public_core=False, rationale="коммерческий гибрид"))
    extended = case.with_custom_mode(first).with_custom_mode(second)
    assert list(extended.modes) == ["A", "B", "C", "D", "E"]
    assert set(extended.custom_modes) == {"D", "E"}
    assert set(extended.canonical_modes) == {"A", "B", "C"}
    result = calculate(extended, [("FIRE", "D"), ("AGRI", "E"), ("TRANS", "A"), ("ENV", "A")], "BASE")
    assert result.metrics.public_core_lots == 3
    assert [note.lots for note in result.notes if note.code == "custom_mode"] == [("FIRE",), ("AGRI",)]


def test_custom_mode_can_be_replaced_by_a_newer_definition(case):
    older = case.with_custom_mode(parse_custom_mode(VALID))
    newer = older.with_custom_mode(parse_custom_mode(dict(VALID, k_vpub=0.7)))
    assert newer.modes["D"].k_vpub == 0.7
    assert len(newer.modes) == 4


def test_custom_mode_does_not_mutate_the_original_case(case):
    case.with_custom_mode(parse_custom_mode(VALID))
    assert list(case.modes) == ["A", "B", "C"]


def test_custom_mode_roundtrips_through_dict(case):
    from kosmo.custom_mode import custom_mode_to_dict
    mode = parse_custom_mode(VALID)
    again = parse_custom_mode(custom_mode_to_dict(mode))
    assert again == mode
