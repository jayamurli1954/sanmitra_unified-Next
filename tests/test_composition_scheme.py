"""GST Composition Scheme (Section 10) — sales path issues a Bill of Supply with
no GST collected, and inter-state outward supply is blocked."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

import app.modules.business.service as business_service
from app.modules.business.service import (
    AccountingValidationError,
    COMPOSITION_RATES,
    _compute_invoice_lines,
)
from app.modules.business.schemas import (
    PurchaseBillCreateRequest,
    PurchaseBillLineItem,
    SalesInvoiceCreateRequest,
    SalesInvoiceLineItem,
)

# Reuse the in-memory collection + account-id map patterns from the phase-2 suite.
from tests.test_business_phase2 import (
    FakeCollection,
    _seed_customer,
    _seed_vendor,
    _INVOICE_ACCOUNT_IDS,
)


def _payload(*, is_inter_state=False):
    return SalesInvoiceCreateRequest(
        customer_party_id="cust-1",
        invoice_date=date(2026, 6, 8),
        is_inter_state=is_inter_state,
        line_items=[
            SalesInvoiceLineItem(description="Sweets", hsn_sac="2106", uqc="KGS",
                                 quantity=Decimal("10"), rate=Decimal("100"), gst_rate=Decimal("18")),
        ],
    )


# --------------------------------------------------------------------------- #
# Pure line computation
# --------------------------------------------------------------------------- #
def test_compute_invoice_lines_composition_has_no_gst():
    lines, taxable, cgst, sgst, igst, gst_total, total = _compute_invoice_lines(
        _payload(), composition=True,
    )
    assert taxable == Decimal("1000.00")
    assert (cgst, sgst, igst, gst_total) == (Decimal("0.00"),) * 4
    assert total == Decimal("1000.00")          # no tax added to a Bill of Supply
    assert lines[0]["cgst"] == "0.00" and lines[0]["igst"] == "0.00"


def test_composition_rates_table():
    assert COMPOSITION_RATES == {"goods": Decimal("1"), "restaurant": Decimal("5"), "services": Decimal("6")}


# --------------------------------------------------------------------------- #
# Sales path under composition
# --------------------------------------------------------------------------- #
def _patch_common(monkeypatch, store, captured, *, category="restaurant"):
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)

    async def _none(*_a, **_k):
        return None

    monkeypatch.setattr(business_service, "initialize_default_chart_of_accounts", _none)
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_k: _none())

    async def fake_profile(**_kwargs):
        return {"registration_type": "composition", "composition_category": category,
                "composition_rate": COMPOSITION_RATES[category], "is_composition": True}

    monkeypatch.setattr(business_service, "get_gst_profile", fake_profile)

    async def fake_resolve(_session, *, account_code, **_kwargs):
        return _INVOICE_ACCOUNT_IDS[account_code]

    monkeypatch.setattr(business_service, "_resolve_voucher_account_id", fake_resolve)

    async def fake_post(_session, *, payload, **kwargs):
        captured["payload"] = payload
        return SimpleNamespace(id=901), True

    monkeypatch.setattr(business_service, "post_journal_entry", fake_post)


@pytest.mark.asyncio
async def test_composition_sale_is_bill_of_supply_without_gst(monkeypatch):
    store = FakeCollection()
    _seed_customer(store)
    captured = {}
    _patch_common(monkeypatch, store, captured)

    result = await business_service.create_sales_invoice(
        None, tenant_id="business-tenant", app_key="mitrabooks", created_by="owner-1",
        payload=_payload(), idempotency_key="bos-1",
    )

    # Journal has only AR debit + income credit — no output-GST legs.
    lines = captured["payload"].lines
    assert len(lines) == 2
    assert lines[0].account_id == _INVOICE_ACCOUNT_IDS["12001"]
    assert lines[0].debit == Decimal("1000.00")
    assert lines[1].account_id == _INVOICE_ACCOUNT_IDS["41001"]
    assert lines[1].credit == Decimal("1000.00")
    assert sum(l.debit for l in lines) == sum(l.credit for l in lines) == Decimal("1000.00")

    assert result["document_type"] == "bill_of_supply"
    assert result["is_composition"] is True
    assert result["gst_total"] == "0.00"
    assert result["invoice_total"] == "1000.00"


@pytest.mark.asyncio
async def test_composition_blocks_inter_state_supply(monkeypatch):
    store = FakeCollection()
    _seed_customer(store)
    captured = {}
    _patch_common(monkeypatch, store, captured)

    with pytest.raises(AccountingValidationError, match="inter-state"):
        await business_service.create_sales_invoice(
            None, tenant_id="business-tenant", app_key="mitrabooks", created_by="owner-1",
            payload=_payload(is_inter_state=True), idempotency_key="bos-2",
        )


@pytest.mark.asyncio
async def test_composition_purchase_capitalises_gst_no_itc(monkeypatch):
    store = FakeCollection()
    _seed_vendor(store)
    captured = {}
    _patch_common(monkeypatch, store, captured, category="goods")

    result = await business_service.create_purchase_bill(
        None, tenant_id="business-tenant", app_key="mitrabooks", created_by="owner-1",
        payload=PurchaseBillCreateRequest(
            vendor_party_id="vend-1",
            bill_number="BILL-1",
            bill_date=date(2026, 6, 8),
            is_inter_state=False,
            line_items=[PurchaseBillLineItem(description="Raw material", quantity=Decimal("10"),
                                             rate=Decimal("100"), gst_rate=Decimal("18"))],
        ),
        idempotency_key="cbill-1",
    )

    # Composition: GST folded into expense, no Input-GST (ITC) legs.
    lines = captured["payload"].lines
    assert len(lines) == 2
    assert lines[0].account_id == _INVOICE_ACCOUNT_IDS["51001"]
    assert lines[0].debit == Decimal("1180.00")          # taxable 1000 + GST 180, all cost
    assert lines[1].account_id == _INVOICE_ACCOUNT_IDS["21001"]
    assert lines[1].credit == Decimal("1180.00")
    # No 14001/14002/14003 ITC asset lines.
    itc_ids = {_INVOICE_ACCOUNT_IDS["14001"], _INVOICE_ACCOUNT_IDS["14002"], _INVOICE_ACCOUNT_IDS["14003"]}
    assert not any(l.account_id in itc_ids for l in lines)
    assert result["itc_claimed"] is False
