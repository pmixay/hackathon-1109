import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend import evaluate as ev, model, payload  # noqa: E402

from kosmo import calculate, calculate_all_scenarios, load_portfolio, score_variants  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
SELECTED = "FIRE:A|AGRI:B|TRANS:B|ENV:A"

NOTEBOOK_SELECTION = [("FIRE", "A"), ("AGRI", "C"), ("TRANS", "C"), ("ENV", "A")]
NOTEBOOK_DETAIL = {
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
        cls.case = ev.load_case()

    def test_case_is_the_verified_team_copy(self):
        self.assertTrue(self.case.verified)
        self.assertEqual(ev.CASE_DIR, REPO)
        self.assertEqual(set(self.case.checksums), {"data/lots.csv", "data/access_modes.csv", "config/case_config.json", "src/case_core.py"})

    def test_selected_portfolio(self):
        results = ev.evaluate_portfolio(model.parse_id(SELECTED), self.case)
        m = results["BASE"].metrics
        self.assertAlmostEqual(m.c0, 1140.0)
        self.assertAlmostEqual(m.opex, 313.0)
        self.assertAlmostEqual(m.vpub, 1289.0)
        self.assertAlmostEqual(m.cash, 370.5)
        self.assertAlmostEqual(m.kcash, 370.5 / 313.0)
        self.assertAlmostEqual(m.t_rep, 0.73)
        self.assertEqual(m.public_core_lots, 2)
        self.assertEqual(m.capability_groups, 2)
        self.assertEqual(m.territorial_archetypes, 4)
        self.assertTrue(results["BASE"].feasible and results["STRESS"].feasible)

    def test_check_rows_follow_the_contract(self):
        result = calculate(self.case, model.parse_id(SELECTED), "STRESS")
        rows = ev.check_details(result)
        self.assertEqual([r["id"] for r in rows], ev.CHECK_ORDER)
        self.assertEqual({r["op"] for r in rows}, {"=", "<=", ">="})
        by_id = {r["id"]: r for r in rows}
        self.assertEqual(by_id["c0_limit"], {"id": "c0_limit", "ok": True, "fact": 1140.0, "op": "<=", "threshold": 1180.0})
        self.assertEqual(by_id["exact_lot_count"]["op"], "=")
        for r in rows:
            self.assertIsInstance(r["ok"], bool)
            self.assertIsInstance(r["fact"], float)
            self.assertIsInstance(r["threshold"], float)
        self.assertEqual([r["constraint"] for r in ev.check_constraints(result)], ev.CHECK_ORDER)

    def test_notebook_control_example(self):
        from kosmo.export import template_metrics

        results = ev.evaluate_portfolio(NOTEBOOK_SELECTION, self.case)
        for row, (c0, opex, vpub, cash, t_rep) in zip(results["BASE"].lots, NOTEBOOK_DETAIL.values()):
            self.assertAlmostEqual(row.c0, c0, places=3, msg=row.lot_id)
            self.assertAlmostEqual(row.opex, opex, places=3, msg=row.lot_id)
            self.assertAlmostEqual(row.vpub, vpub, places=3, msg=row.lot_id)
            self.assertAlmostEqual(row.cash, cash, places=3, msg=row.lot_id)
            self.assertAlmostEqual(row.t_rep, t_rep, places=3, msg=row.lot_id)
        metrics = template_metrics(results["BASE"].metrics)
        self.assertEqual(list(metrics), list(NOTEBOOK_METRICS))
        for key, expected in NOTEBOOK_METRICS.items():
            if isinstance(expected, float):
                self.assertAlmostEqual(metrics[key], expected, places=3, msg=key)
            else:
                self.assertEqual(metrics[key], expected, key)
        for scenario in ("BASE", "STRESS"):
            self.assertTrue(results[scenario].feasible, scenario)

    def test_boundaries_come_from_the_engine(self):
        base = calculate(self.case, [("FIRE", "A"), ("FLOOD", "A"), ("INFRA", "B"), ("ENV", "A")], "BASE")
        stress = calculate(self.case, [("FIRE", "A"), ("FLOOD", "A"), ("INFRA", "B"), ("ENV", "A")], "STRESS")
        self.assertTrue(base.feasible)
        self.assertFalse(stress.feasible)
        self.assertEqual([r["id"] for r in ev.check_details(stress) if not r["ok"]], ["c0_limit"])


class Model(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case, cls.records = payload._enumerated()

    def test_enumeration_totals(self):
        self.assertEqual(len(self.records), 5670)
        self.assertEqual(sum(r["ok"]["BASE"] for r in self.records.values()), 1031)
        self.assertEqual(sum(r["ok"]["STRESS"] for r in self.records.values()), 143)

    def test_canonical_id_orders_lots_as_in_lots_csv(self):
        portfolio = load_portfolio(REPO / "config" / "portfolio.json")
        self.assertEqual(model.canonical_id(self.case, portfolio.selection), SELECTED)
        self.assertEqual(model.canonical_id(self.case, [("ENV", "A"), ("TRANS", "B"), ("AGRI", "B"), ("FIRE", "A")]), SELECTED)

    def test_scores_match_the_engine_selection_model(self):
        sel_model = payload.selection_model()
        score, rank = model.make_scorer(self.records, sel_model, "STRESS")
        from dataclasses import replace

        engine = {item.name: item for item in score_variants({cid: r["results"] for cid, r in self.records.items()}, replace(sel_model, feasibility_scenario="STRESS"))}
        for cid, rec in self.records.items():
            if rec["ok"]["STRESS"]:
                self.assertAlmostEqual(score(rec), engine[cid].score, places=12)
                self.assertEqual(rank[cid], engine[cid].rank)
            else:
                self.assertNotIn(cid, rank)
                self.assertTrue(0.0 <= score(rec) <= 1.0)
        self.assertEqual(len(rank), 143)
        self.assertEqual(rank[SELECTED], 3)

    def test_dashboard_shape(self):
        d = payload.build_dashboard(SELECTED)
        self.assertEqual(d["selected"], SELECTED)
        self.assertIn(SELECTED, d["suggestions"])
        for cid in set(d["comparison"]) | {a["id"] for a in d["stress"]["actions"]}:
            c = d["combinations"][cid]
            self.assertEqual(len(c["checks"]["BASE"]), 9)
            self.assertEqual(len(c["checks"]["STRESS"]), 9)
            self.assertEqual(len(c["per_lot"]), 4)
            self.assertIsInstance(c["score"], float)
        s = d["combinations"][SELECTED]
        self.assertTrue(s["ok"]["BASE"] and s["ok"]["STRESS"])
        self.assertLessEqual(abs(sum(d["meta"]["weights"].values()) - 1.0), 1e-9)
        self.assertEqual(set(d["meta"]["weights"]), {"vpub", "c0", "kcash", "readiness", "resilience", "scale", "stress_margin"})
        for rid in d["rejected"]:
            self.assertFalse(d["combinations"][rid]["ok"]["STRESS"])
        self.assertEqual(d["meta"]["engine"]["name"], "kosmo")
        self.assertTrue(d["meta"]["engine"]["verified"])
        self.assertEqual(d["meta"]["engine"]["portfolio"], "FINAL")
        self.assertEqual(d["meta"]["totals"], {"combinations": 5670, "base_feasible": 1031, "stress_feasible": 143, "ranked": 143})
        self.assertEqual(d["meta"]["constraints"]["opex_max_mrub_per_year"], 360.0)
        self.assertEqual(d["meta"]["dataset"]["source"], "организаторы")
        json.dumps(d, ensure_ascii=False)

    def test_team_portfolio_stays_in_suggestions(self):
        d = payload.build_dashboard("FLOOD:A|AGRI:C|TRANS:B|ENV:A")
        self.assertIn(SELECTED, d["suggestions"])
        self.assertIn("FLOOD:A|AGRI:C|TRANS:B|ENV:A", d["suggestions"])
        scores = [d["combinations"][cid]["score"] for cid in d["suggestions"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(len(d["suggestions"]), 6)

    def test_default_selection_is_the_team_portfolio(self):
        d = payload.build_dashboard()
        self.assertEqual(d["selected"], SELECTED)
        self.assertEqual(d["selected"], d["meta"]["engine"]["portfolio_id"])
        self.assertEqual(payload.build_dashboard("ENV:A|TRANS:B|AGRI:B|FIRE:A")["selected"], SELECTED)

    def test_dashboard_numbers_equal_results_base_json(self):
        d = payload.build_dashboard(SELECTED)
        s = d["combinations"][SELECTED]
        base = json.loads((REPO / "results" / "base.json").read_text(encoding="utf-8"))
        stress = json.loads((REPO / "results" / "stress.json").read_text(encoding="utf-8"))
        keys = {"c0": "c0", "opex": "opex", "vpub": "vpub", "cash": "cash", "kcash": "kcash", "t_rep": "t_rep", "archetypes": "territorial_archetypes", "groups": "capability_groups", "public_core": "public_core_lots"}
        for ui_key, engine_key in keys.items():
            self.assertEqual(s["metrics"][ui_key], base["metrics"][engine_key], ui_key)
        by_lot = {lot["lot_id"]: lot for lot in base["lots"]}
        for row in s["per_lot"]:
            lot = by_lot[row["lot"]]
            for key in ("c0", "opex", "vpub", "cash", "anchor_cash", "commercial_cash", "opex_gap", "t_rep"):
                self.assertEqual(row[key], lot[key], (row["lot"], key))
            self.assertEqual(row["mode"], lot["mode_id"])
        for scenario, exported in (("BASE", base), ("STRESS", stress)):
            expected = [{"id": c["code"], "ok": c["passed"], "fact": c["actual"], "op": ev.OPERATORS[c["operator"]], "threshold": c["threshold"]} for c in exported["checks"]]
            self.assertEqual(s["checks"][scenario], expected)
            self.assertEqual([n["code"] for n in s["notes"][scenario]], [n["code"] for n in exported["notes"]])

    def test_every_dashboard_combination_equals_a_direct_engine_call(self):
        d = payload.build_dashboard(SELECTED)
        for cid, c in d["combinations"].items():
            results = calculate_all_scenarios(self.case, model.parse_id(cid))
            self.assertEqual(c["metrics"]["c0"], results["BASE"].metrics.c0)
            self.assertEqual(c["metrics"]["kcash"], results["BASE"].metrics.kcash)
            self.assertEqual(c["ok"], {sid: r.feasible for sid, r in results.items()})

    def test_lot_names_and_service_cards(self):
        d = payload.build_dashboard(SELECTED)
        self.assertEqual(d["lots"]["FIRE"]["name"], "Лесные пожары")
        self.assertEqual(d["lots"]["ENV"]["region"], "Волго-Каспийский регион")
        self.assertEqual(d["lots"]["AGRI"]["groups"], ["EO", "PNT/InSAR"])
        for lid, mode in [("FIRE", "A"), ("ENV", "A"), ("AGRI", "B"), ("TRANS", "B")]:
            card = d["lots"][lid]["card"]
            self.assertEqual(card["mode"], mode, lid)
            for key in ("description", "user", "access_base", "access_extra", "kpi", "on_failure"):
                self.assertTrue(card[key], (lid, key))
        self.assertIsNone(d["lots"]["FLOOD"]["card"])
        self.assertEqual(set(d["modes"]), {"A", "B", "C"})
        self.assertTrue(d["modes"]["A"]["public_core"])

    def test_unknown_selection(self):
        with self.assertRaises(ValueError):
            payload.build_dashboard("FIRE:A|FIRE:A|FIRE:A|FIRE:A")
        with self.assertRaises(ValueError):
            payload.build_dashboard("FIRE:A|AGRI:B|TRANS:B|ENV:Z")


class Export(unittest.TestCase):
    def test_export_writes_the_engine_bundle(self):
        d = payload.build_dashboard(SELECTED)
        with tempfile.TemporaryDirectory() as tmp:
            written = payload.export_results(d, Path(tmp))
            names = sorted(Path(p).name for p in written.values())
            self.assertEqual(names, ["alternatives.csv", "base.json", "portfolio_detail.csv", "portfolio_metrics.json", "repairs_base.csv", "repairs_stress.csv", "scores.csv", "sensitivity.csv", "stress.json", "team_decision_config.json"])
            fresh = json.loads((Path(tmp) / "base.json").read_text(encoding="utf-8"))
            committed = json.loads((REPO / "results" / "base.json").read_text(encoding="utf-8"))
            fresh.pop("generated_at")
            committed.pop("generated_at")
            self.assertEqual(fresh, committed)
            self.assertEqual(fresh["portfolio"]["name"], "FINAL")
            for name in ("portfolio_detail.csv", "portfolio_metrics.json", "team_decision_config.json"):
                self.assertEqual((Path(tmp) / name).read_bytes(), (REPO / "results" / name).read_bytes(), name)

    def test_export_matches_template_format(self):
        import csv

        from kosmo.export import TEMPLATE_DETAIL_COLUMNS

        d = payload.build_dashboard(SELECTED)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            payload.export_results(d, out)
            with open(out / "portfolio_detail.csv", encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(tuple(rows[0]), TEMPLATE_DETAIL_COLUMNS)
            self.assertEqual([(r["lot_id"], r["mode_id"]) for r in rows], [("FIRE", "A"), ("ENV", "A"), ("AGRI", "B"), ("TRANS", "B")])
            self.assertEqual(rows[0]["territorial_archetype"], "Siberian")
            self.assertEqual(rows[2]["capability_groups"], "EO;PNT/InSAR")
            metrics = json.loads((out / "portfolio_metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(set(metrics), set(NOTEBOOK_METRICS))
            self.assertAlmostEqual(metrics["c0_mrub"], d["combinations"][SELECTED]["metrics"]["c0"])
            card = json.loads((out / "team_decision_config.json").read_text(encoding="utf-8"))
            self.assertEqual(set(card), {"team", "decision_method", "strategy_thesis", "selection", "weights", "management"})
            self.assertEqual([tuple(p) for p in card["selection"]], [("FIRE", "A"), ("ENV", "A"), ("AGRI", "B"), ("TRANS", "B")])
            self.assertEqual(card["weights"], d["meta"]["weights"])
            self.assertEqual(set(card["management"]), {"payer_opex", "operator_model", "supplier_switch_rule", "replicable_core", "local_adaptation", "stress_decision"})
            self.assertTrue(card["management"]["operator_model"])

    def test_export_of_another_combination_keeps_team_alternatives(self):
        other = "FIRE:A|AGRI:C|TRANS:C|ENV:A"
        d = payload.build_dashboard(other)
        with tempfile.TemporaryDirectory() as tmp:
            written = payload.export_results(d, Path(tmp))
            out = Path(tmp) / "variants" / "fire-a-agri-c-trans-c-env-a"
            self.assertEqual({Path(p).parent for p in written.values()}, {out})
            self.assertFalse((Path(tmp) / "base.json").exists())
            base = json.loads((out / "base.json").read_text(encoding="utf-8"))
            self.assertEqual(base["portfolio"]["name"], other)
            self.assertEqual([f"{s['lot_id']}:{s['mode_id']}" for s in base["selection"]], other.split("|"))
            rows = (out / "alternatives.csv").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(rows), 1 + 2 * 8)
            self.assertTrue(rows[1].startswith(other))


if __name__ == "__main__":
    unittest.main()
