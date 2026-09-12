import hashlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend import ingest, payload  # noqa: E402

TESTDATA = Path(__file__).resolve().parents[1] / "testdata"
SELECTED = "FIRE:A|AGRI:B|TRANS:B|ENV:A"

INVALID = {
    "09-invalid-missing-column": ("lots.csv", "нет столбцов: t_rep"),
    "10-invalid-not-a-number": ("lots.csv", "FLOOD: c0_mrub не число"),
    "11-invalid-duplicate-lot": ("lots.csv", "повторяющиеся lot_id: FIRE"),
    "12-invalid-json": ("case_config.json", "не JSON"),
    "13-three-lots": ("lots.csv", "лотов 3, портфель требует 4"),
}

EXPECTED = {
    "01-original": dict(totals=(5670, 1031, 143), c0=1140.0, ok=(True, True), failed=(), rank=3, modes="ABC"),
    "02-stress-1130": dict(totals=(5670, 1031, 13), c0=1140.0, ok=(True, False), failed=("c0_limit",), rank=None, modes="ABC"),
    "03-opex-310": dict(totals=(5670, 35, 35), c0=1140.0, ok=(False, False), failed=("opex_limit",), rank=None, modes="ABC"),
    "04-kcash-1.2": dict(totals=(5670, 143, 28), c0=1140.0, ok=(False, False), failed=("kcash_floor",), rank=None, modes="ABC"),
    "05-boundary-1180": dict(totals=(5670, 945, 35), c0=1180.0, ok=(True, True), failed=(), rank=10, modes="ABC"),
    "06-fire-plus-10pct": dict(totals=(5670, 907, 97), c0=1173.6, ok=(True, True), failed=(), rank=28, modes="ABC"),
    "07-nine-lots": dict(totals=(10206, 2044, 486), c0=1140.0, ok=(True, True), failed=(), rank=3, modes="ABC"),
    "08-mode-d": dict(totals=(17920, 2061, 491), c0=1140.0, ok=(True, True), failed=(), rank=18, modes="ABCD"),
    "14-nothing-feasible": dict(totals=(5670, 0, 0), c0=1140.0, ok=(False, False), failed=("vpub_floor",), rank=None, modes="ABC"),
}


def read_set(name):
    return {file: (TESTDATA / name / file).read_text(encoding="utf-8") for file in ingest.FILES}


class TestData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)
        payload.reset_cache()

    def root_for(self, name):
        root = self.tmp / name
        for file, relative in ingest.FILES.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text((TESTDATA / name / file).read_text(encoding="utf-8"), encoding="utf-8")
        return root

    def test_every_folder_is_documented(self):
        folders = sorted(p.name for p in TESTDATA.iterdir() if p.is_dir())
        self.assertEqual(folders, sorted(set(EXPECTED) | set(INVALID)))
        readme = (TESTDATA / "README.md").read_text(encoding="utf-8")
        for name in folders:
            self.assertIn(f"`{name}`", readme)
            self.assertEqual(sorted(p.name for p in (TESTDATA / name).iterdir()), sorted(ingest.FILES))

    def test_original_set_is_byte_equal_to_the_case_files(self):
        repo = TESTDATA.parents[1]
        for file, relative in ingest.FILES.items():
            self.assertEqual((TESTDATA / "01-original" / file).read_bytes(), (repo / relative).read_bytes(), file)
        digest = hashlib.sha256((TESTDATA / "01-original" / "lots.csv").read_bytes()).hexdigest()
        self.assertTrue(digest.startswith("8e2b6244"))

    def test_invalid_sets_are_rejected_with_the_documented_message(self):
        for name, (file, message) in INVALID.items():
            report = ingest.validate(read_set(name))
            self.assertFalse(report[file]["ok"], name)
            self.assertTrue(any(message in error for error in report[file]["errors"]), (name, report[file]["errors"]))
            others = [other for other in ingest.FILES if other != file]
            self.assertTrue(all(report[other]["ok"] for other in others), name)

    def test_valid_sets_produce_the_documented_dashboard(self):
        for name, expected in EXPECTED.items():
            with self.subTest(name=name):
                report = ingest.validate(read_set(name))
                self.assertTrue(all(r["ok"] for r in report.values()), (name, report))
                dashboard = payload.build_dashboard(None, root=self.root_for(name))
                totals = dashboard["meta"]["totals"]
                self.assertEqual((totals["combinations"], totals["base_feasible"], totals["stress_feasible"]), expected["totals"])
                self.assertEqual(dashboard["selected"], SELECTED)
                combo = dashboard["combinations"][SELECTED]
                self.assertAlmostEqual(combo["metrics"]["c0"], expected["c0"])
                self.assertEqual((combo["ok"]["BASE"], combo["ok"]["STRESS"]), expected["ok"])
                failed = tuple(check["id"] for check in combo["checks"]["STRESS"] if not check["ok"])
                self.assertEqual(failed, expected["failed"])
                self.assertEqual(combo["rank"], expected["rank"])
                self.assertEqual("".join(sorted(dashboard["modes"])), expected["modes"])
                self.assertIn(SELECTED, dashboard["suggestions"])
                self.assertFalse(dashboard["meta"]["engine"]["verified"])
                self.assertEqual(dashboard["meta"]["dataset"]["source"], "загружено")

    def test_boundary_set_passes_with_zero_margin(self):
        dashboard = payload.build_dashboard(None, root=self.root_for("05-boundary-1180"))
        check = next(c for c in dashboard["combinations"][SELECTED]["checks"]["STRESS"] if c["id"] == "c0_limit")
        self.assertEqual((check["fact"], check["threshold"], check["ok"]), (1180.0, 1180.0, True))

    def test_new_lot_and_new_mode_reach_the_screens(self):
        nine = payload.build_dashboard(None, root=self.root_for("07-nine-lots"))
        self.assertIn("HYDRO", nine["lots"])
        self.assertIsNone(nine["lots"]["HYDRO"]["card"])
        self.assertTrue(any("HYDRO" in cid for cid in nine["combinations"]))
        mode_d = payload.build_dashboard(None, root=self.root_for("08-mode-d"))
        self.assertEqual(mode_d["modes"]["D"]["k_c0"], 0.9)
        self.assertFalse(mode_d["modes"]["D"]["custom"])
        self.assertEqual(mode_d["meta"]["allowed_modes"], ["A", "B", "C"])
        self.assertFalse(any(":D" in cid for cid in mode_d["suggestions"]))


if __name__ == "__main__":
    unittest.main()
