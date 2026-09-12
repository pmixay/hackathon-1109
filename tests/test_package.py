import json
import os
import subprocess
import sys

import pytest

import kosmo
from kosmo.checks import LABELS, UNITS, build_check


def run_cli(root, *args):
    env = dict(os.environ, PYTHONPATH=str(root / "src"), PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, "-m", "kosmo", "--root", str(root), *args], capture_output=True, text=True, encoding="utf-8", env=env, cwd=str(root))


def test_every_public_name_resolves():
    for name in kosmo.__all__:
        assert getattr(kosmo, name) is not None
    assert len(kosmo.__all__) == len(set(kosmo.__all__))


def test_engine_has_no_third_party_imports(root):
    for path in (root / "src" / "kosmo").glob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                module = stripped.split()[1].split(".")[0]
                assert module in sys.stdlib_module_names or module in ("kosmo", ""), (path.name, line)


def test_module_help_runs_as_a_process(root):
    completed = run_cli(root, "--help")
    assert completed.returncode == 0
    assert "calc" in completed.stdout and "export" in completed.stdout


def test_documented_calc_command_runs_as_a_process(root):
    completed = run_cli(root, "calc", "--lots", "FIRE:A", "FLOOD:A", "TRANS:A", "ENV:A", "--scenario", "STRESS")
    assert completed.returncode == 1
    assert "НАРУШЕНО" in completed.stdout
    assert "c0_limit" in completed.stdout


def test_json_command_output_is_parseable_from_a_process(root):
    completed = run_cli(root, "calc", "--json", "--scenario", "BASE")
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["BASE"]["feasible"] is True


def test_check_labels_cover_every_code():
    assert set(LABELS) == set(UNITS) == {
        "exact_lot_count", "territorial_archetypes", "capability_groups", "public_core_lots",
        "c0_limit", "opex_limit", "vpub_floor", "kcash_floor", "t_rep_floor",
    }


def test_unknown_operator_is_rejected():
    with pytest.raises(ValueError, match="unsupported operator"):
        build_check("c0_limit", "c0", "<", 1300, 1200, "BASE")


def test_check_describe_for_a_passing_check():
    check = build_check("vpub_floor", "vpub", ">=", 1000, 1370, "common")
    assert check.describe() == "Годовая общественная ценность портфеля: vpub = 1370 >= 1000 млн руб./год — выполнено"
    assert check.margin == 370.0


def test_equality_check_margin_is_never_positive():
    assert build_check("exact_lot_count", "selected_lots", "==", 4, 4, "common").margin == 0.0
    assert build_check("exact_lot_count", "selected_lots", "==", 4, 5, "common").margin == -1.0
    assert build_check("exact_lot_count", "selected_lots", "==", 4, 3, "common").margin == -1.0


def test_results_dataclasses_are_immutable(case, v1):
    from dataclasses import FrozenInstanceError
    result = kosmo.calculate(case, v1, "BASE")
    with pytest.raises(FrozenInstanceError):
        result.metrics.c0 = 0
    with pytest.raises(FrozenInstanceError):
        result.checks[0].passed = False
    with pytest.raises(FrozenInstanceError):
        case.lots["FIRE"].c0 = 0
