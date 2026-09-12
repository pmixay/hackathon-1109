import pytest

from kosmo import calculate, calculate_all_scenarios, parse_custom_mode


def codes(result):
    return [note.code for note in result.notes]


def note(result, code):
    return next(item for item in result.notes if item.code == code)


def test_c0_funding_is_always_asked_and_covers_all_lots(case, v1, v3, v5):
    for selection in (v1, v3, v5):
        for result in calculate_all_scenarios(case, selection).values():
            assert codes(result)[0] == "c0_funding"
            item = note(result, "c0_funding")
            assert item.lots == tuple(lot_id for lot_id, _ in selection)
            assert f"{result.metrics.c0:.1f}" in item.message


def test_opex_gap_note_lists_only_lots_with_a_gap(case, v1):
    result = calculate(case, v1, "BASE")
    item = note(result, "opex_gap")
    assert item.lots == tuple(row.lot_id for row in result.lots if row.opex_gap > 0)
    assert "31.5" in item.message
    assert "90%" in item.message


def test_no_opex_gap_note_when_cash_covers_opex(case, v5):
    result = calculate(case, v5, "BASE")
    assert result.metrics.kcash > 1.0
    assert "opex_gap" not in codes(result)


def test_anchor_payer_note_skips_lots_without_anchor_money(case):
    no_anchor = parse_custom_mode({
        "mode_id": "D", "k_c0": 1.0, "k_opex": 1.0, "k_vpub": 0.8, "k_anchor": 0.0, "k_commercial": 0.9,
        "public_core": False, "rationale": "чисто коммерческий доступ",
    })
    extended = case.with_custom_mode(no_anchor)
    result = calculate(extended, (("FIRE", "A"), ("AGRI", "D"), ("TRANS", "A"), ("ENV", "A")), "BASE")
    assert note(result, "anchor_payer").lots == ("FIRE", "TRANS", "ENV")
    assert note(result, "custom_mode").lots == ("AGRI",)
    assert "custom_mode_public_core" not in codes(result)
    assert note(result, "custom_mode_range").message.startswith("Коэффициент k_anchor=0.0")


def test_federal_note_only_with_ssa(case, v1, v4):
    assert "federal_lot" not in codes(calculate(case, v1, "BASE"))
    item = note(calculate(case, v4, "BASE"), "federal_lot")
    assert item.lots == ("SSA",)


def test_tight_c0_margin_is_flagged_only_when_it_is_tight(case, v1, v3):
    results = calculate_all_scenarios(case, v1)
    assert "c0_tight_margin" not in codes(results["BASE"])
    item = note(results["STRESS"], "c0_tight_margin")
    assert "STRESS" in item.message
    assert "14.5" in item.message
    assert "1.2%" in item.message
    failing = calculate(case, v3, "STRESS")
    assert "c0_tight_margin" not in codes(failing)


def test_tight_margin_boundary_is_five_percent(case):
    threshold = case.scenarios["BASE"].c0_max
    just_inside = calculate(case, (("AGRI", "A"), ("INFRA", "A"), ("TRANS", "A"), ("ENV", "A")), "BASE")
    share = (threshold - just_inside.metrics.c0) / threshold
    assert share > 0.05
    assert "c0_tight_margin" not in codes(just_inside)
    close = calculate(case, (("FIRE", "A"), ("FLOOD", "A"), ("TRANS", "A"), ("ENV", "A")), "BASE")
    share = (threshold - close.metrics.c0) / threshold
    assert share < 0.05
    assert "c0_tight_margin" in codes(close)


def test_custom_mode_notes_appear_only_when_the_mode_is_used(case):
    extended = case.with_custom_mode(parse_custom_mode({
        "mode_id": "D", "k_c0": 1.0, "k_opex": 1.0, "k_vpub": 0.9, "k_anchor": 0.9, "k_commercial": 0.5,
        "public_core": True, "rationale": "гибрид",
    }))
    unused = calculate(extended, (("FIRE", "A"), ("AGRI", "A"), ("TRANS", "A"), ("ENV", "A")), "BASE")
    assert not any(code.startswith("custom_mode") for code in codes(unused))
    used = calculate(extended, (("FIRE", "D"), ("AGRI", "D"), ("TRANS", "A"), ("ENV", "A")), "BASE")
    assert note(used, "custom_mode").lots == ("FIRE", "AGRI")
    assert "гибрид" in note(used, "custom_mode").message
    assert "k_vpub=0.9" in note(used, "custom_mode").message


def test_notes_are_the_same_in_both_scenarios_except_margin(case, v1):
    results = calculate_all_scenarios(case, v1)
    base = [n for n in results["BASE"].notes if n.code != "c0_tight_margin"]
    stress = [n for n in results["STRESS"].notes if n.code != "c0_tight_margin"]
    assert base == stress


def test_note_payload_shape(case, v1):
    payload = calculate(case, v1, "STRESS").to_dict()
    for item in payload["notes"]:
        assert set(item) == {"code", "message", "lots"}
        assert isinstance(item["lots"], list) and item["lots"]
        assert item["message"]
