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
