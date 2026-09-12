import json

import pytest

from kosmo import CaseFormatError, CaseIntegrityError, load_case
from kosmo.case import SOURCE_FILES, file_sha256, parse_bool, split_capabilities
from kosmo import calculate_all_scenarios


def test_source_copies_match_organizers_files(root):
    originals = {
        "data/lots.csv": root / "cases" / "case02" / "data" / "lots.csv",
        "data/access_modes.csv": root / "cases" / "case02" / "data" / "access_modes.csv",
        "config/case_config.json": root / "cases" / "case02" / "config" / "case_config.json",
        "src/case_core.py": root / "cases" / "case02" / "case_core.py",
    }
    for name, original in originals.items():
        assert (root / name).read_bytes() == original.read_bytes(), name


def test_checksums_are_fixed_and_verified(root, case):
    expected = json.loads((root / "config" / "case_checksums.json").read_text(encoding="utf-8"))
    assert set(expected) == set(SOURCE_FILES)
    assert case.verified
    for name in SOURCE_FILES:
        assert case.checksums[name] == expected[name] == file_sha256(root / name)


def test_case_shape(case):
    assert case.case_id == "SEP-KOSMOS-INFRA-2026"
    assert case.version == "1.1"
    assert list(case.lots) == ["FIRE", "FLOOD", "AGRI", "INFRA", "ARCTIC", "TRANS", "ENV", "SSA"]
    assert list(case.modes) == ["A", "B", "C"]
    assert list(case.scenarios) == ["BASE", "STRESS"]
    assert case.scenarios["BASE"].c0_max == 1300
    assert case.scenarios["STRESS"].c0_max == 1180
    assert case.constraints.selected_lots_exactly == 4
    assert case.constraints.opex_max == 360
    assert case.constraints.vpub_min == 1000
    assert case.constraints.kcash_min == 0.6
    assert case.constraints.t_rep_min == 0.63


def test_lot_values_are_read_verbatim(case):
    fire = case.lots["FIRE"]
    assert (fire.c0, fire.opex, fire.anchor_cash, fire.commercial_cash, fire.vpub) == (320, 85, 75, 35, 560)
    assert (fire.t_rep, fire.readiness, fire.resilience, fire.scale) == (0.68, 4.3, 3.5, 4.5)
    assert fire.federal is False
    assert case.lots["SSA"].federal is True


def test_mode_coefficients(case):
    a, b, c = case.modes["A"], case.modes["B"], case.modes["C"]
    assert (a.k_c0, a.k_opex, a.k_vpub, a.k_anchor, a.k_commercial, a.public_core) == (1.05, 1.05, 1.0, 1.0, 0.25, True)
    assert (b.k_c0, b.k_opex, b.k_vpub, b.k_anchor, b.k_commercial, b.public_core) == (1.0, 1.0, 0.82, 0.8, 0.7, False)
    assert (c.k_c0, c.k_opex, c.k_vpub, c.k_anchor, c.k_commercial, c.public_core) == (0.98, 0.95, 0.62, 0.45, 0.95, False)


def test_capability_normalization(case):
    assert split_capabilities("EO;PNT/InSAR") == ("EO", "PNT/InSAR")
    assert split_capabilities(" PNT ; InSAR ;") == ("PNT", "InSAR")
    assert case.lots["AGRI"].capability_set == frozenset({"EO", "PNT/InSAR"})
    assert case.lots["ARCTIC"].capability_set == frozenset({"SATCOM", "PNT/InSAR"})
    assert case.lots["TRANS"].capability_set == frozenset({"PNT/InSAR", "EO"})


def test_modified_source_file_is_rejected(case_root):
    tmp_path = case_root
    lots = tmp_path / "data" / "lots.csv"
    lots.write_text(lots.read_text(encoding="utf-8").replace("FIRE,Siberian,Siberian forest fire monitoring,EO,320", "FIRE,Siberian,Siberian forest fire monitoring,EO,300"), encoding="utf-8")
    with pytest.raises(CaseIntegrityError, match="data/lots.csv"):
        load_case(tmp_path)


def test_case_without_checksums_loads_unverified(case_root):
    tmp_path = case_root
    (tmp_path / "config" / "case_checksums.json").unlink()
    assert load_case(tmp_path).verified is False


def test_partial_checksums_file_is_rejected(case_root):
    tmp_path = case_root
    checksums = tmp_path / "config" / "case_checksums.json"
    expected = json.loads(checksums.read_text(encoding="utf-8"))
    expected.pop("data/lots.csv")
    checksums.write_text(json.dumps(expected), encoding="utf-8")
    with pytest.raises(CaseIntegrityError, match="does not cover: data/lots.csv"):
        load_case(tmp_path)


def test_missing_fixed_file_is_rejected(case_root):
    tmp_path = case_root
    (tmp_path / "src" / "case_core.py").unlink()
    with pytest.raises(CaseIntegrityError, match="missing: src/case_core.py"):
        load_case(tmp_path)


def test_bom_and_padded_headers_are_tolerated(case_root):
    tmp_path = case_root
    (tmp_path / "config" / "case_checksums.json").unlink()
    lots = tmp_path / "data" / "lots.csv"
    text = lots.read_text(encoding="utf-8")
    lots.write_bytes(b"\xef\xbb\xbf" + text.replace("lot_id,", "lot_id ,", 1).encode("utf-8"))
    assert load_case(tmp_path).lots["FIRE"].c0 == 320


def test_missing_column_is_reported(case_root):
    tmp_path = case_root
    (tmp_path / "config" / "case_checksums.json").unlink()
    modes = tmp_path / "data" / "access_modes.csv"
    lines = modes.read_text(encoding="utf-8").splitlines()
    lines[0] = lines[0].replace("public_core", "public")
    modes.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(CaseFormatError, match="access_modes.csv: missing columns public_core"):
        load_case(tmp_path)


@pytest.mark.parametrize("bad_value", ["", "abc", "inf", "nan"])
def test_non_finite_or_empty_numbers_are_rejected(case_root, bad_value):
    tmp_path = case_root
    (tmp_path / "config" / "case_checksums.json").unlink()
    lots = tmp_path / "data" / "lots.csv"
    lots.write_text(lots.read_text(encoding="utf-8").replace("EO,320,85,", f"EO,{bad_value},85,"), encoding="utf-8")
    with pytest.raises(CaseFormatError, match="FIRE.c0_mrub"):
        load_case(tmp_path)


def test_duplicate_lot_is_rejected(case_root):
    tmp_path = case_root
    (tmp_path / "config" / "case_checksums.json").unlink()
    lots = tmp_path / "data" / "lots.csv"
    text = lots.read_text(encoding="utf-8")
    lines = text.splitlines()
    lines.append(lines[1])
    lots.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(CaseFormatError, match="duplicate lot_id FIRE"):
        load_case(tmp_path)
