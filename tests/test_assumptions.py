import json

import pytest

from kosmo import load_portfolio

SLA_FIELDS = {"service", "target_update_interval", "max_source_age", "delivery_latency", "recovery_time", "fallback", "evidence", "assumption_owner"}


@pytest.fixture(scope="module")
def assumptions(root):
    return json.loads((root / "config" / "assumptions.json").read_text(encoding="utf-8"))


def test_assumptions_cover_every_lot_of_the_final_portfolio(root, assumptions):
    portfolio = load_portfolio(root / "config" / "portfolio.json")
    assert assumptions["applies_to_portfolio"] == portfolio.name
    assert set(assumptions["service_sla"]) == {lot_id for lot_id, _ in portfolio.selection}


def test_every_service_sla_has_all_fields(assumptions):
    for lot_id, sla in assumptions["service_sla"].items():
        missing = SLA_FIELDS - set(sla)
        assert not missing, (lot_id, missing)
        assert all(str(sla[field]).strip() for field in SLA_FIELDS), lot_id
        assert "допущение" in sla["evidence"] or "данные кейса" in sla["evidence"], lot_id


def test_fire_sla_is_conditioned_on_coverage(assumptions):
    fire = assumptions["service_sla"]["FIRE"]
    assert "coverage_condition" in fire
    assert "высокоэллиптической" in fire["coverage_condition"]
    assert "геостационар" not in json.dumps(assumptions, ensure_ascii=False)
    assert "всей Сибири" in fire["coverage_condition"]


def test_assumptions_are_marked_as_not_implemented(assumptions):
    assert "не реализован" in assumptions["status"]
    assert "не реализовано" in assumptions["operations"]["implementation_status"]
    assert "не входит в vpub" in assumptions["kpi_from_event_fields"]["note"]


def test_event_fields_match_the_handover_note(assumptions):
    fields = " ".join(assumptions["event_fields"])
    for name in ("event_id", "lot_id", "source_updated_at", "provider_id", "processing_version", "confidence", "status", "decision_at", "access_class"):
        assert name in fields


def test_every_capability_group_has_two_sources(assumptions):
    for group in ("EO", "PNT/InSAR"):
        assert len(assumptions["data_sources"][group]) >= 2


def test_financing_block_agrees_with_results(root, assumptions):
    base = json.loads((root / "results" / "base.json").read_text(encoding="utf-8"))
    metrics = base["metrics"]
    block = assumptions["financing_and_contracts"]
    assert block["c0_funding"]["total"] == metrics["c0"]
    public = sum(lot["c0"] for lot in base["lots"] if lot["public_core"])
    assert block["c0_funding"]["public_budget"]["amount"] == public
    assert block["c0_funding"]["private_partner"]["amount"] == metrics["c0"] - public
    assert block["commercial_demand_risk"]["commercial_cash_per_year"] == metrics["commercial_cash"]
    assert block["commercial_demand_risk"]["anchor_cash_per_year"] == metrics["anchor_cash"]
    assert block["commercial_demand_risk"]["kcash_with_zero_commercial"] == pytest.approx(metrics["anchor_cash"] / metrics["opex"], abs=5e-4)
    assert block["commercial_demand_risk"]["opex_gap_with_zero_commercial"] == pytest.approx(metrics["opex"] - metrics["anchor_cash"])
    for lot in base["lots"]:
        assert block["pooling_of_flows"]["per_lot_kcash"][lot["lot_id"]] == pytest.approx(lot["cash"] / lot["opex"], abs=5e-4)
    gap = sum(lot["opex_gap"] for lot in base["lots"] if lot["opex_gap"] > 0)
    surplus = -sum(lot["opex_gap"] for lot in base["lots"] if lot["opex_gap"] < 0)
    assert block["pooling_of_flows"]["public_lots_gap_per_year"] == pytest.approx(gap)
    assert block["pooling_of_flows"]["commercial_lots_surplus_per_year"] == pytest.approx(surplus)
    assert metrics["anchor_cash"] / metrics["opex"] >= 0.6


def test_ppp_term_argument_holds(root, assumptions):
    base = json.loads((root / "results" / "base.json").read_text(encoding="utf-8"))
    term = assumptions["financing_and_contracts"]["c0_funding"]["ppp_term_years"]
    for lot in base["lots"]:
        if lot["public_core"]:
            continue
        net = lot["cash"] - lot["opex"]
        assert net > 0
        assert 7 * net < lot["c0"] < term * net
