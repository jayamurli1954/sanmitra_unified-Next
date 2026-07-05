import xml.etree.ElementTree as ET

import pytest
from fastapi import HTTPException

from app.modules.business import export_governance, tally_xml
from app.modules.business import router as business_router


def _trial_balance_spec():
    return {
        "org_name": "Acme Traders",
        "meta": [("As of", "2026-06-30")],
        "rows": [
            {"account_code": "11010", "account_name": "Bank Account", "debit": "150000.00", "credit": None},
            {"account_code": "21001", "account_name": "Sundry Creditors", "debit": None, "credit": "30000.00"},
            {"account_code": "31004", "account_name": "Opening Balance Equity", "debit": None, "credit": "120000.00"},
        ],
    }


def test_trial_balance_tally_xml_contains_ledger_masters_and_source_metadata():
    payload = tally_xml.build_trial_balance_tally_xml(spec=_trial_balance_spec(), as_of="2026-06-30")
    root = ET.fromstring(payload)
    ledgers = root.findall(".//LEDGER")

    assert root.findtext(".//TALLYREQUEST") == "Import Data"
    assert root.findtext(".//SVCURRENTCOMPANY") == "Acme Traders"
    assert root.findtext(".//SANMITRAEXPORT/SOURCE") == "trial_balance"
    assert root.findtext(".//SANMITRAEXPORT/ASOF") == "2026-06-30"
    assert [ledger.findtext("NAME") for ledger in ledgers] == [
        "Bank Account",
        "Sundry Creditors",
        "Opening Balance Equity",
    ]
    assert ledgers[0].findtext("PARENT") == "Bank Accounts"
    assert ledgers[1].findtext("OPENINGBALANCE") == "-30000.00"


@pytest.mark.asyncio
async def test_tally_xml_route_is_governed_and_audited(monkeypatch):
    audit_events = []

    async def fake_build_report(*_args, **_kwargs):
        return _trial_balance_spec()

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)
        return "audit-1"

    monkeypatch.setattr(business_router, "_build_business_report", fake_build_report)
    monkeypatch.setattr(export_governance, "log_audit_event", fake_log_audit_event)

    response = await business_router.export_business_tally_xml(
        as_of=None,
        accounting_entity_id="primary",
        _module_context={},
        session=None,
        current_user={"tenant_id": "business-tenant", "app_key": "mitrabooks", "role": "accountant", "sub": "user-1"},
        x_tenant_id=None,
        x_app_key="mitrabooks",
    )

    assert response.media_type == "application/xml"
    assert response.headers["X-SanMitra-Export-Governed"] == "true"
    assert response.headers["X-SanMitra-Export-Type"] == "tally_xml"
    assert response.headers["X-SanMitra-Export-Format"] == "xml"
    assert b"<REPORTNAME>All Masters</REPORTNAME>" in response.body
    assert audit_events[0]["action"] == "business_export_downloaded"
    assert audit_events[0]["new_value"]["report_key"] == "trial_balance"


@pytest.mark.asyncio
async def test_tally_xml_cashier_denied_before_report_build(monkeypatch):
    called = False

    async def fake_build_report(*_args, **_kwargs):
        nonlocal called
        called = True
        return _trial_balance_spec()

    monkeypatch.setattr(business_router, "_build_business_report", fake_build_report)

    with pytest.raises(HTTPException) as exc:
        await business_router.export_business_tally_xml(
            as_of=None,
            accounting_entity_id="primary",
            _module_context={},
            session=None,
            current_user={"tenant_id": "business-tenant", "app_key": "mitrabooks", "role": "cashier", "sub": "cashier-1"},
            x_tenant_id=None,
            x_app_key="mitrabooks",
        )

    assert exc.value.status_code == 403
    assert called is False
