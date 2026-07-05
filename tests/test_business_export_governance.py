import json

import pytest
from fastapi import HTTPException

from app.modules.business import export_governance, report_export
from app.modules.business import router as business_router


@pytest.mark.asyncio
async def test_report_export_json_is_governed_and_audited(monkeypatch):
    audit_events = []

    async def fake_build_report(*_args, **_kwargs):
        return {
            "title": "Trial Balance",
            "columns": [{"key": "account", "label": "Account"}, {"key": "amount", "label": "Amount", "numeric": True}],
            "rows": [{"account": "Cash", "amount": "100.00"}],
            "footer": {"account": "Total", "amount": "100.00"},
            "meta": [("As of", "2026-06-30")],
            "filename_base": "trial_balance_2026-06-30",
            "org_name": "Acme",
        }

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)
        return "audit-1"

    monkeypatch.setattr(business_router, "_build_business_report", fake_build_report)
    monkeypatch.setattr(export_governance, "log_audit_event", fake_log_audit_event)

    response = await business_router.export_business_report(
        report="trial_balance",
        format="json",
        kind="receivable",
        as_of=None,
        from_date=None,
        to_date=None,
        account_id=None,
        party_id=None,
        accounting_entity_id="primary",
        _module_context={},
        session=None,
        current_user={"tenant_id": "business-tenant", "app_key": "mitrabooks", "role": "accountant", "sub": "user-1"},
        x_tenant_id=None,
        x_app_key="mitrabooks",
    )

    assert response.media_type == "application/json"
    assert response.headers["X-SanMitra-Export-Governed"] == "true"
    assert response.headers["X-SanMitra-Export-Format"] == "json"
    assert response.headers["X-SanMitra-Export-Type"] == "business_report"
    assert audit_events[0]["tenant_id"] == "business-tenant"
    assert audit_events[0]["product"] == "mitrabooks"
    assert audit_events[0]["action"] == "business_export_downloaded"
    assert audit_events[0]["new_value"]["report_key"] == "trial_balance"
    assert audit_events[0]["new_value"]["format"] == "json"


@pytest.mark.asyncio
async def test_report_export_cashier_denied_before_report_build(monkeypatch):
    called = False

    async def fake_build_report(*_args, **_kwargs):
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(business_router, "_build_business_report", fake_build_report)

    with pytest.raises(HTTPException) as exc:
        await business_router.export_business_report(
            report="trial_balance",
            format="csv",
            kind="receivable",
            as_of=None,
            from_date=None,
            to_date=None,
            account_id=None,
            party_id=None,
            accounting_entity_id="primary",
            _module_context={},
            session=None,
            current_user={"tenant_id": "business-tenant", "app_key": "mitrabooks", "role": "cashier", "sub": "cashier-1"},
            x_tenant_id=None,
            x_app_key="mitrabooks",
        )

    assert exc.value.status_code == 403
    assert called is False


def test_generic_report_exporter_supports_json_format():
    response = report_export.export_report(
        "json",
        title="Aging",
        columns=[{"key": "party", "label": "Party"}, {"key": "balance", "label": "Balance", "numeric": True}],
        rows=[{"party": "Customer A", "balance": "10.00"}],
        footer={"party": "Total", "balance": "10.00"},
        meta=[("As of", "2026-06-30")],
        org_name="Acme",
        filename_base="aging_receivable",
    )
    chunks = []

    async def _collect():
        async for chunk in response.body_iterator:
            chunks.append(chunk)

    import asyncio
    asyncio.run(_collect())
    payload = json.loads(b"".join(chunks).decode("utf-8"))

    assert response.media_type == "application/json"
    assert payload["title"] == "Aging"
    assert payload["rows"][0]["party"] == "Customer A"
    assert payload["footer"]["balance"] == "10.00"
