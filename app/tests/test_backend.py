"""Проверки расчётного слоя. Запуск: python -m unittest discover -s app/tests -v

Те же проверки роль A прогоняет после замены evaluate/check на case_core.py:
цифры обязаны совпасть.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend import evaluate as ev, model, payload  # noqa: E402

SELECTED = "FIRE:A|AGRI:B|TRANS:B|ENV:A"


class Evaluate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lots, cls.modes, cls.config = ev.load_case()

    def test_apply_mode_fire_a(self):
        r = ev.apply_mode(self.lots["FIRE"], self.modes["A"])
        self.assertAlmostEqual(r["c0_mrub"], 320 * 1.05)
        self.assertAlmostEqual(r["cash_mrub_per_year"], 75 * 1.0 + 35 * 0.25)
        self.assertTrue(r["public_core"])

    def test_selected_portfolio(self):
        _, m = ev.evaluate_portfolio(model.parse_id(SELECTED), self.lots, self.modes, self.config)
        self.assertAlmostEqual(m["c0_mrub"], 1140.0)
        self.assertAlmostEqual(m["opex_mrub_per_year"], 313.0)
        self.assertAlmostEqual(m["vpub_mrub_per_year"], 1289.0)
        self.assertAlmostEqual(m["cash_mrub_per_year"], 370.5)
        self.assertAlmostEqual(m["kcash"], 370.5 / 313.0)
        self.assertAlmostEqual(m["t_rep"], 0.73)
        self.assertEqual(m["public_core_lots"], 2)
        self.assertEqual(m["capability_groups"], 2)
        self.assertEqual(m["territorial_archetypes"], 4)

    def test_boundaries_inclusive(self):
        _, m = ev.evaluate_portfolio(model.parse_id(SELECTED), self.lots, self.modes, self.config)
        for c0, scenario, expected in [(1300, "BASE", True), (1300.01, "BASE", False), (1180, "STRESS", True), (1180.01, "STRESS", False)]:
            mm = dict(m, c0_mrub=c0)
            ok = {r["constraint"]: r["ok"] for r in ev.check_constraints(mm, self.config, scenario)}
            self.assertEqual(ok["c0_limit"], expected, (c0, scenario))
        ok = {r["constraint"]: r["ok"] for r in ev.check_constraints(dict(m, kcash=0.6, t_rep=0.63), self.config, "BASE")}
        self.assertTrue(ok["kcash_floor"] and ok["t_rep_floor"])
        self.assertFalse({r["constraint"]: r["ok"] for r in ev.check_constraints(dict(m, kcash=0.599), self.config, "BASE")}["kcash_floor"])

    def test_check_order_matches_case_core(self):
        _, m = ev.evaluate_portfolio(model.parse_id(SELECTED), self.lots, self.modes, self.config)
        self.assertEqual([r["constraint"] for r in ev.check_constraints(m, self.config)], ev.CHECK_ORDER)


class Model(unittest.TestCase):
    def test_enumeration_totals(self):
        lots, modes, config, records = payload._enumerated()
        self.assertEqual(len(records), 5670)
        self.assertEqual(sum(r["ok"]["BASE"] for r in records.values()), 1031)
        self.assertEqual(sum(r["ok"]["STRESS"] for r in records.values()), 143)

    def test_dashboard_shape(self):
        d = payload.build_dashboard(SELECTED)
        self.assertEqual(d["selected"], SELECTED)
        self.assertIn(SELECTED, d["suggestions"])
        for cid in set(d["comparison"]) | {a["id"] for a in d["stress"]["actions"]}:
            c = d["combinations"][cid]
            self.assertEqual(len(c["checks"]["BASE"]), 9)
            self.assertEqual(len(c["checks"]["STRESS"]), 9)
            self.assertEqual(len(c["per_lot"]), 4)
        s = d["combinations"][SELECTED]
        self.assertTrue(s["ok"]["BASE"] and s["ok"]["STRESS"])
        self.assertLessEqual(abs(sum(d["meta"]["weights"].values()) - 1.0), 1e-9)
        for rid in d["rejected"]:
            self.assertFalse(d["combinations"][rid]["ok"]["STRESS"])

    def test_unknown_selection(self):
        with self.assertRaises(ValueError):
            payload.build_dashboard("FIRE:A|FIRE:A|FIRE:A|FIRE:A")


if __name__ == "__main__":
    unittest.main()
