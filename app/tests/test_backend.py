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

# Вывод исполненных ячеек стартового notebook организаторов (округление до 3 знаков — как в display(...round(3))).
NOTEBOOK_SELECTION = [("FIRE", "A"), ("AGRI", "C"), ("TRANS", "C"), ("ENV", "A")]
NOTEBOOK_DETAIL = {  # lot: (c0, opex, vpub, cash, t_rep)
    "FIRE": (336.0, 89.25, 560.0, 83.75, 0.68),
    "AGRI": (254.8, 71.25, 142.6, 127.5, 0.74),
    "TRANS": (245.0, 66.5, 136.4, 110.5, 0.77),
    "ENV": (294.0, 78.75, 360.0, 76.25, 0.73),
}
NOTEBOOK_METRICS = {
    "selected_lots": 4, "c0_mrub": 1129.8, "opex_mrub_per_year": 305.75, "vpub_mrub_per_year": 1199.0,
    "cash_mrub_per_year": 398.0, "kcash": 1.302, "t_rep": 0.73, "readiness_1_5": 4.525, "resilience_1_5": 4.05,
    "scale_1_5": 4.675, "territorial_archetypes": 4, "capability_groups": 2, "capability_set": ["EO", "PNT/InSAR"],
    "public_core_lots": 2,
}


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

    def test_notebook_control_example(self):
        """Контрольный пример Т1: исполненный запуск стартового notebook организаторов
        (cases/case02/Космос_как_инфраструктура.ipynb, ячейка «Канонический расчет BASE/STRESS»)
        для FIRE:A, AGRI:C, TRANS:C, ENV:A. Цифры взяты из вывода ячейки как есть."""
        detail, m = ev.evaluate_portfolio(NOTEBOOK_SELECTION, self.lots, self.modes, self.config)
        for row, (c0, opex, vpub, cash, t_rep) in zip(detail, NOTEBOOK_DETAIL.values()):
            self.assertAlmostEqual(row["c0_mrub"], c0, places=3, msg=row["lot_id"])
            self.assertAlmostEqual(row["opex_mrub_per_year"], opex, places=3, msg=row["lot_id"])
            self.assertAlmostEqual(row["vpub_mrub_per_year"], vpub, places=3, msg=row["lot_id"])
            self.assertAlmostEqual(row["cash_mrub_per_year"], cash, places=3, msg=row["lot_id"])
            self.assertAlmostEqual(row["t_rep"], t_rep, places=3, msg=row["lot_id"])
        for key, expected in NOTEBOOK_METRICS.items():
            if isinstance(expected, float):
                self.assertAlmostEqual(m[key], expected, places=3, msg=key)
            else:
                self.assertEqual(m[key], expected, key)
        for scenario in ("BASE", "STRESS"):
            self.assertTrue(all(r["ok"] for r in ev.check_constraints(m, self.config, scenario)), scenario)


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

    def test_lot_names_and_service_cards(self):
        d = payload.build_dashboard(SELECTED)
        self.assertEqual(d["lots"]["FIRE"]["name"], "Лесные пожары")
        self.assertEqual(d["lots"]["ENV"]["region"], "Волго-Каспийский регион")
        for lid, mode in [("FIRE", "A"), ("ENV", "A"), ("AGRI", "B"), ("TRANS", "B")]:
            card = d["lots"][lid]["card"]
            self.assertEqual(card["mode"], mode, lid)
            for key in ("description", "user", "access_base", "access_extra", "kpi", "on_failure"):
                self.assertTrue(card[key], (lid, key))
        self.assertIsNone(d["lots"]["FLOOD"]["card"])

    def test_unknown_selection(self):
        with self.assertRaises(ValueError):
            payload.build_dashboard("FIRE:A|FIRE:A|FIRE:A|FIRE:A")

    def test_export_matches_template_format(self):
        """results/ содержит наши base/stress/alternatives и три файла в формате notebook организаторов."""
        import csv
        import json
        import tempfile

        d = payload.build_dashboard(SELECTED)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            payload.export_results(d, out)
            names = {p.name for p in out.iterdir()}
            self.assertEqual(names, {"base.json", "stress.json", "alternatives.csv",
                                     "portfolio_detail.csv", "portfolio_metrics.json", "team_decision_config.json"})
            with open(out / "portfolio_detail.csv", encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(list(rows[0]), payload.TEMPLATE_DETAIL_COLUMNS)
            self.assertEqual([(r["lot_id"], r["mode_id"]) for r in rows], model.parse_id(SELECTED))
            self.assertEqual(rows[0]["territorial_archetype"], "Siberian")
            with open(out / "portfolio_metrics.json", encoding="utf-8") as f:
                metrics = json.load(f)
            self.assertEqual(set(metrics), set(NOTEBOOK_METRICS))
            self.assertAlmostEqual(metrics["c0_mrub"], d["combinations"][SELECTED]["metrics"]["c0"])
            with open(out / "team_decision_config.json", encoding="utf-8") as f:
                card = json.load(f)
            self.assertEqual(set(card), {"team", "decision_method", "strategy_thesis", "selection", "weights", "management"})
            self.assertEqual([tuple(p) for p in card["selection"]], model.parse_id(SELECTED))
            self.assertEqual(card["weights"], d["meta"]["weights"])
            self.assertEqual(set(card["management"]), {"payer_opex", "operator_model", "supplier_switch_rule",
                                                       "replicable_core", "local_adaptation", "stress_decision"})


if __name__ == "__main__":
    unittest.main()
