import json

import pytest

from kosmo import SelectionError, Variant, VariantStore, calculate_all_scenarios, load_portfolio, load_variants, parse_custom_mode
from kosmo.variants import slug


def test_repo_portfolio_and_alternatives_load(root, case):
    portfolio = load_portfolio(root / "config" / "portfolio.json")
    assert portfolio.name == "FINAL"
    assert portfolio.selection == (("FIRE", "A"), ("ENV", "A"), ("AGRI", "B"), ("TRANS", "B"))
    assert calculate_all_scenarios(case, portfolio.selection)["STRESS"].feasible
    alternatives = load_variants(root / "config" / "alternatives.json")
    assert [variant.name for variant in alternatives] == ["FINAL", "V1", "V2", "V3", "V4", "V5", "V6"]
    assert alternatives[0].selection == portfolio.selection


def test_save_load_recompute_identical(case, v1, tmp_path):
    store = VariantStore(tmp_path / "variants")
    path = store.save(case, Variant(name="Вариант 1", selection=v1, note="тест"))
    assert path.name == "вариант-1.json"
    snapshot = store.load("Вариант 1")
    assert snapshot["variant"]["selection"][0] == {"lot_id": "FIRE", "mode_id": "A"}
    assert snapshot["case"]["checksums"] == case.checksums
    assert set(snapshot["results"]) == {"BASE", "STRESS"}
    assert snapshot["results"]["BASE"]["metrics"]["c0"] == 1165.5
    stored, fresh, identical = store.recompute(case, "Вариант 1")
    assert identical
    assert store.names() == ["Вариант 1"]


def test_custom_mode_is_stored_with_variant(case, tmp_path):
    raw = {
        "mode_id": "D", "k_c0": 1.0, "k_opex": 1.0, "k_vpub": 0.9, "k_anchor": 0.9, "k_commercial": 0.5,
        "public_core": True, "rationale": "гибрид", "name": "D",
    }
    extended = case.with_custom_mode(parse_custom_mode(raw))
    store = VariantStore(tmp_path)
    store.save(extended, Variant(name="with-d", selection=(("FIRE", "D"), ("AGRI", "A"), ("TRANS", "A"), ("ENV", "A"))))
    snapshot = store.load("with-d")
    assert snapshot["custom_modes"] == [dict(raw, name="D")]
    stored, fresh, identical = store.recompute(case, "with-d")
    assert identical


def test_recompute_detects_changed_inputs(case, v1, tmp_path):
    store = VariantStore(tmp_path)
    path = store.save(case, Variant(name="v1", selection=v1))
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    snapshot["results"]["BASE"]["metrics"]["c0"] = 1.0
    path.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
    stored, fresh, identical = store.recompute(case, "v1")
    assert not identical
    assert fresh["results"]["BASE"]["metrics"]["c0"] == 1165.5


def test_missing_variant(case, tmp_path):
    with pytest.raises(FileNotFoundError):
        VariantStore(tmp_path).load("nope")


def test_colliding_names_do_not_overwrite(case, v1, v3, tmp_path):
    store = VariantStore(tmp_path)
    store.save(case, Variant(name="A/B", selection=v1))
    with pytest.raises(FileExistsError, match="already holds variant 'A/B'"):
        store.save(case, Variant(name="A B", selection=v3))
    store.save(case, Variant(name="A/B", selection=v3))
    assert store.load("A/B")["variant"]["selection"][1]["lot_id"] == "FLOOD"


def test_malformed_variant_files(tmp_path):
    path = tmp_path / "alternatives.json"
    path.write_text('{"variants": {"name": "x"}}', encoding="utf-8")
    with pytest.raises(SelectionError, match="список вариантов"):
        load_variants(path)
    path.write_text('[{"selection": []}]', encoding="utf-8")
    with pytest.raises(SelectionError, match="имя"):
        load_variants(path)
    path.write_text("42", encoding="utf-8")
    with pytest.raises(SelectionError, match="объектом JSON"):
        load_portfolio(path)


def test_slug():
    assert slug("V1") == "v1"
    assert slug("Пожары + агро (A/B)") == "пожары-агро-a-b"
    assert slug("///") == "variant"


def test_snapshot_is_pure_json_types(case, v1, tmp_path):
    from kosmo.variants import variant_snapshot
    snapshot = variant_snapshot(case, Variant(name="x", selection=v1))
    assert json.loads(json.dumps(snapshot, allow_nan=False)) == snapshot
    assert snapshot["format_version"] == 1
    assert isinstance(snapshot["results"]["BASE"]["metrics"]["capability_set"], list)
    assert isinstance(snapshot["results"]["BASE"]["notes"][0]["lots"], list)


def test_snapshot_written_and_read_back_are_identical(case, v1, tmp_path):
    from kosmo.variants import variant_snapshot
    store = VariantStore(tmp_path)
    store.save(case, Variant(name="x", selection=v1, note="заметка"))
    assert store.load("x") == variant_snapshot(case, Variant(name="x", selection=v1, note="заметка"))


def test_foreign_json_in_store_is_reported(case, tmp_path):
    (tmp_path / "readme.json").write_text('{"purpose": "notes"}', encoding="utf-8")
    store = VariantStore(tmp_path)
    with pytest.raises(SelectionError, match="readme.json: это не сохранённый вариант"):
        store.names()


def test_unknown_snapshot_format_is_rejected(case, v1, tmp_path):
    store = VariantStore(tmp_path)
    path = store.save(case, Variant(name="v1", selection=v1))
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    snapshot["format_version"] = 2
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    with pytest.raises(SelectionError, match="формат снимка 2 не поддерживается"):
        store.load("v1")


def test_snapshot_without_results_is_rejected(case, v1, tmp_path):
    store = VariantStore(tmp_path)
    path = store.save(case, Variant(name="v1", selection=v1))
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    del snapshot["results"]
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    with pytest.raises(SelectionError, match="нет результатов"):
        store.recompute(case, "v1")


def test_saving_same_name_twice_overwrites(case, v1, v3, tmp_path):
    store = VariantStore(tmp_path)
    store.save(case, Variant(name="draft", selection=v1))
    store.save(case, Variant(name="draft", selection=v3))
    assert store.names() == ["draft"]
    assert store.load("draft")["variant"]["selection"][1]["lot_id"] == "FLOOD"


def test_names_are_sorted_by_file_name(case, v1, tmp_path):
    store = VariantStore(tmp_path)
    for name in ("Zeta", "alpha", "Мой"):
        store.save(case, Variant(name=name, selection=v1))
    assert store.names() == ["alpha", "Zeta", "Мой"]


def test_empty_store_lists_nothing(tmp_path):
    assert VariantStore(tmp_path / "nothing").names() == []


def test_recompute_with_stale_custom_mode_uses_the_saved_definition(case, tmp_path):
    raw = {"mode_id": "D", "k_c0": 1.0, "k_opex": 1.0, "k_vpub": 0.9, "k_anchor": 0.9, "k_commercial": 0.5, "public_core": True, "rationale": "старое"}
    old_case = case.with_custom_mode(parse_custom_mode(raw))
    store = VariantStore(tmp_path)
    store.save(old_case, Variant(name="d", selection=(("FIRE", "D"), ("AGRI", "A"), ("TRANS", "A"), ("ENV", "A"))))
    new_case = case.with_custom_mode(parse_custom_mode(dict(raw, k_vpub=0.5, rationale="новое")))
    stored, fresh, identical = store.recompute(new_case, "d")
    assert identical
    assert fresh["custom_modes"][0]["rationale"] == "старое"


def test_variant_from_dict_normalizes_whitespace_and_note():
    variant = Variant.from_dict({"name": "  V9 ", "selection": [[" FIRE", "A "]], "note": None})
    assert variant.name == "V9"
    assert variant.selection == (("FIRE", "A"),)
    assert variant.note == ""


def test_variant_to_dict_roundtrip(v1):
    variant = Variant(name="V1", selection=v1, note="n")
    assert Variant.from_dict(variant.to_dict()) == variant


def test_load_variants_accepts_bare_list(tmp_path):
    path = tmp_path / "alternatives.json"
    path.write_text(json.dumps([{"name": "X", "selection": [{"lot_id": "FIRE", "mode_id": "A"}]}]), encoding="utf-8")
    assert [variant.name for variant in load_variants(path)] == ["X"]
