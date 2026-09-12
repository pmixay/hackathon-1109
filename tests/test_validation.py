import pytest

from kosmo import SelectionError, calculate, normalize_selection, validate_selection


def test_duplicate_lot_is_rejected(case):
    with pytest.raises(SelectionError) as error:
        calculate(case, [("FIRE", "A"), ("FIRE", "A"), ("TRANS", "A"), ("ENV", "A")], "BASE")
    assert error.value.problems == ("позиция 2: лот FIRE выбран повторно",)


def test_unknown_lot_and_mode_are_reported_together(case):
    problems = validate_selection(case, normalize_selection([("FIRE", "A"), ("MOON", "A"), ("TRANS", "Z"), ("ENV", "A")]))
    assert problems == [
        "позиция 2: неизвестный лот 'MOON'",
        "позиция 3: неизвестный режим 'Z', доступны: A, B, C",
    ]


def test_wrong_count(case):
    assert validate_selection(case, normalize_selection([("FIRE", "A")])) == ["в портфеле должно быть ровно 4 лота, передано 1"]
    five = [("FIRE", "A"), ("AGRI", "A"), ("TRANS", "A"), ("ENV", "A"), ("SSA", "A")]
    assert validate_selection(case, normalize_selection(five)) == ["в портфеле должно быть ровно 4 лота, передано 5"]


def test_empty_positions(case):
    problems = validate_selection(case, normalize_selection([("", "A"), ("AGRI", None), ("TRANS", "A"), ("ENV", "A")]))
    assert problems == ["позиция 1: лот не выбран", "позиция 2: режим не выбран"]


def test_custom_mode_unknown_until_enabled(case):
    problems = validate_selection(case, normalize_selection([("FIRE", "D"), ("AGRI", "A"), ("TRANS", "A"), ("ENV", "A")]))
    assert problems == ["позиция 1: неизвестный режим 'D', доступны: A, B, C"]


def test_whitespace_is_tolerated(case):
    assert normalize_selection([(" FIRE ", "A "), {"lot_id": "AGRI", "mode_id": " B"}]) == (("FIRE", "A"), ("AGRI", "B"))


def test_valid_selection_has_no_problems(case, v1):
    assert validate_selection(case, normalize_selection(v1), "STRESS") == []


@pytest.mark.parametrize("selection", ["FA", "FIRE:A", 42, None, {"lot_id": "FIRE", "mode_id": "A"}])
def test_selection_must_be_a_list(selection):
    with pytest.raises(SelectionError, match="списком пар"):
        normalize_selection(selection)


def test_malformed_items_are_reported_by_position():
    with pytest.raises(SelectionError) as error:
        normalize_selection([("FIRE", "A"), "AB", ("TRANS", "A", "extra"), 7, ["ENV", "A"]])
    assert error.value.problems == (
        "позиция 2: ожидается пара (лот, режим), получено 'AB'",
        "позиция 3: ожидается пара (лот, режим), получено ('TRANS', 'A', 'extra')",
        "позиция 4: ожидается пара (лот, режим), получено 7",
    )


def test_error_payload_for_ui(case):
    with pytest.raises(SelectionError) as error:
        calculate(case, [("FIRE", "A"), ("FIRE", "B"), ("TRANS", "X")], "BASE")
    assert error.value.to_dict() == {
        "error": "invalid_selection",
        "problems": [
            "в портфеле должно быть ровно 4 лота, передано 3",
            "позиция 2: лот FIRE выбран повторно",
            "позиция 3: неизвестный режим 'X', доступны: A, B, C",
        ],
    }


def test_identifiers_are_case_sensitive(case):
    problems = validate_selection(case, normalize_selection([("fire", "A"), ("AGRI", "a"), ("TRANS", "A"), ("ENV", "A")]))
    assert problems == ["позиция 1: неизвестный лот 'fire'", "позиция 2: неизвестный режим 'a', доступны: A, B, C"]


def test_non_string_identifiers_are_stringified_not_crashed(case):
    pairs = normalize_selection([(1, "A"), ("AGRI", 2), ("TRANS", "A"), ("ENV", "A")])
    assert pairs[0] == ("1", "A") and pairs[1] == ("AGRI", "2")
    problems = validate_selection(case, pairs)
    assert problems == ["позиция 1: неизвестный лот '1'", "позиция 2: неизвестный режим '2', доступны: A, B, C"]


def test_generators_and_sets_of_pairs_are_accepted(case, v1):
    assert normalize_selection(iter(v1)) == v1
    assert normalize_selection(pair for pair in v1) == v1
    assert set(normalize_selection(set(v1))) == set(v1)


def test_dict_items_with_extra_keys_are_fine(case):
    pairs = normalize_selection([{"lot_id": "FIRE", "mode_id": "A", "comment": "x"}, {"lot_id": "AGRI", "mode_id": "A"}])
    assert pairs == (("FIRE", "A"), ("AGRI", "A"))


def test_dict_items_without_keys_become_empty_positions(case):
    pairs = normalize_selection([{"lot": "FIRE"}, {"lot_id": "AGRI", "mode_id": "A"}, {"lot_id": "TRANS", "mode_id": "A"}, {"lot_id": "ENV", "mode_id": "A"}])
    assert validate_selection(case, pairs) == ["позиция 1: лот не выбран", "позиция 1: режим не выбран"]


def test_all_problem_kinds_in_one_report(case):
    selection = [("", ""), ("MOON", "Z"), ("FIRE", "A"), ("FIRE", "B"), ("AGRI", "A")]
    problems = validate_selection(case, normalize_selection(selection), "CRISIS")
    assert problems == [
        "неизвестный сценарий 'CRISIS', доступны: BASE, STRESS",
        "в портфеле должно быть ровно 4 лота, передано 5",
        "позиция 1: лот не выбран",
        "позиция 1: режим не выбран",
        "позиция 2: неизвестный лот 'MOON'",
        "позиция 2: неизвестный режим 'Z', доступны: A, B, C",
        "позиция 4: лот FIRE выбран повторно",
    ]


def test_triple_duplicate_is_reported_at_each_repeat(case):
    problems = validate_selection(case, normalize_selection([("FIRE", "A"), ("FIRE", "A"), ("FIRE", "A"), ("ENV", "A")]))
    assert problems == ["позиция 2: лот FIRE выбран повторно", "позиция 3: лот FIRE выбран повторно"]


def test_empty_selection(case):
    assert validate_selection(case, normalize_selection([])) == ["в портфеле должно быть ровно 4 лота, передано 0"]


def test_problems_are_immutable_tuple_and_message_joins_them(case):
    with pytest.raises(SelectionError) as error:
        calculate(case, [("FIRE", "A")], "BASE")
    assert isinstance(error.value.problems, tuple)
    assert str(error.value) == "в портфеле должно быть ровно 4 лота, передано 1"
    assert isinstance(error.value, ValueError)
