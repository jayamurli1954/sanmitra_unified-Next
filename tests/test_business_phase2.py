from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import app.modules.business.service as business_service
from app.core.tenants.app_resolvers import resolve_business_app_tenant
from app.modules.business.schemas import (
    CaDocumentCreateRequest,
    CaDocumentUpdateRequest,
    PartyCreateRequest,
    PartyUpdateRequest,
    CreditNoteCreateRequest,
    CreditNoteLineItem,
    DebitNoteCreateRequest,
    DebitNoteLineItem,
    PurchaseBillCancelRequest,
    PurchaseBillCreateRequest,
    PurchaseBillLineItem,
    SalesInvoiceCancelRequest,
    SalesInvoiceCreateRequest,
    SalesInvoiceLineItem,
    TypedVoucherCreateRequest,
    TypedVoucherReversalRequest,
)

# Account codes resolved by code in the BUSINESS chart of accounts.
_INVOICE_ACCOUNT_IDS = {
    "12001": 100, "41001": 200, "41002": 201, "22001": 301, "22002": 302, "22003": 303,
    # Purchase side: AP, expense/purchases, Input GST (ITC).
    "21001": 400, "51001": 500, "14001": 601, "14002": 602, "14003": 603,
    # GST Payable (net) clearing account.
    "22004": 700,
    # ITC reversal (Rule 37): recoverable parking, interest expense + payable.
    "14004": 604, "54006": 801, "23003": 802,
}


class FakeCollection:
    def __init__(self):
        self.docs = []
        self.deleted = []
        self.updated = []
        self.seq = 0

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def find_one(self, filters):
        for doc in self.docs:
            if all(doc.get(key) == value for key, value in filters.items()):
                return dict(doc)
        return None

    async def count_documents(self, filters):
        return sum(1 for doc in self.docs if all(doc.get(key) == value for key, value in filters.items()))

    async def find_one_and_update(self, filters, update, **_kwargs):
        self.seq += int(update.get("$inc", {}).get("seq", 1))
        return {**filters, "seq": self.seq}

    def find(self, filters):
        rows = [
            dict(doc)
            for doc in self.docs
            if all(doc.get(key) == value for key, value in filters.items())
        ]
        return FakeCursor(rows)

    async def delete_one(self, filters):
        self.deleted.append(dict(filters))
        self.docs = [
            doc
            for doc in self.docs
            if not all(doc.get(key) == value for key, value in filters.items())
        ]

    async def update_one(self, filters, update, upsert=False):
        self.updated.append((dict(filters), dict(update)))
        matched = False
        for doc in self.docs:
            if all(doc.get(key) == value for key, value in filters.items()):
                doc.update(update.get("$set", {}))
                matched = True
        if not matched and upsert:
            new_doc = dict(filters)
            new_doc.update(update.get("$setOnInsert", {}))
            new_doc.update(update.get("$set", {}))
            self.docs.append(new_doc)


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    def sort(self, field, direction):
        self.rows.sort(key=lambda row: row.get(field) or "", reverse=direction < 0)
        return self

    def limit(self, value):
        self.rows = self.rows[:value]
        return self

    async def to_list(self, length):
        return self.rows[:length]


@pytest.mark.asyncio
async def test_business_party_is_tenant_and_app_scoped(monkeypatch):
    parties = FakeCollection()
    audit_events = []
    monkeypatch.setattr(business_service, "get_collection", lambda _name: parties)

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    result = await business_service.create_party(
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        created_by="owner-1",
        payload=PartyCreateRequest(
            party_name="Acme Traders",
            party_type="customer",
            party_code="CUST-001",
            opening_balance=Decimal("125.50"),
        ),
    )

    assert result["tenant_id"] == "business-tenant"
    assert result["app_key"] == "mitrabooks"
    assert result["accounting_entity_id"] == "primary"
    assert result["party_code"] == "CUST-001"
    assert result["opening_balance"] == "125.50"
    assert parties.docs[0]["current_balance"] == "125.50"
    assert audit_events[0]["tenant_id"] == "business-tenant"
    assert audit_events[0]["product"] == "mitrabooks"
    assert audit_events[0]["action"] == "business_party_created"
    assert audit_events[0]["entity_id"] == result["party_id"]


@pytest.mark.asyncio
async def test_update_business_party_does_not_mutate_balances(monkeypatch):
    parties = FakeCollection()
    audit_events = []
    parties.docs = [
        {
            "party_id": "party-1",
            "tenant_id": "business-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "party_name": "Old Name",
            "party_type": "customer",
            "party_code": "CUST-001",
            "opening_balance": "125.50",
            "current_balance": "125.50",
            "is_active": True,
            "created_by": "owner-1",
            "created_at": business_service._now(),
            "updated_at": business_service._now(),
        }
    ]
    monkeypatch.setattr(business_service, "get_collection", lambda _name: parties)

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    result = await business_service.update_party(
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        party_id="party-1",
        updated_by="owner-2",
        payload=PartyUpdateRequest(
            party_name="New Name",
            party_type="both",
            phone="9999999999",
        ),
    )

    assert result["party_name"] == "New Name"
    assert result["party_type"] == "both"
    assert result["phone"] == "9999999999"
    assert result["opening_balance"] == "125.50"
    assert result["current_balance"] == "125.50"
    assert result["updated_by"] == "owner-2"
    assert audit_events[0]["action"] == "business_party_updated"
    assert audit_events[0]["old_value"]["party_name"] == "Old Name"
    assert audit_events[0]["new_value"]["party_name"] == "New Name"


@pytest.mark.asyncio
async def test_deactivate_business_party_is_soft_and_hidden_from_active_list(monkeypatch):
    parties = FakeCollection()
    audit_events = []
    parties.docs = [
        {
            "party_id": "party-1",
            "tenant_id": "business-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "party_name": "Acme Traders",
            "party_type": "customer",
            "party_code": "CUST-001",
            "opening_balance": "0.00",
            "current_balance": "0.00",
            "is_active": True,
            "created_by": "owner-1",
            "created_at": business_service._now(),
            "updated_at": business_service._now(),
        }
    ]
    monkeypatch.setattr(business_service, "get_collection", lambda _name: parties)

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    result = await business_service.deactivate_party(
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        party_id="party-1",
        deactivated_by="owner-2",
    )
    active = await business_service.list_parties(
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
    )

    assert result["is_active"] is False
    assert result["deactivated_by"] == "owner-2"
    assert active["total"] == 0
    assert parties.docs[0]["party_id"] == "party-1"
    assert audit_events[0]["action"] == "business_party_deactivated"
    assert audit_events[0]["old_value"]["is_active"] is True
    assert audit_events[0]["new_value"]["is_active"] is False


@pytest.mark.asyncio
async def test_typed_voucher_posts_balanced_journal(monkeypatch):
    vouchers = FakeCollection()
    captured = {}
    audit_events = []
    monkeypatch.setattr(business_service, "get_collection", lambda _name: vouchers)

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    async def fake_post_journal_entry(session, *, tenant_id, app_key, accounting_entity_id, created_by, payload, idempotency_key):
        captured.update(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "accounting_entity_id": accounting_entity_id,
                "created_by": created_by,
                "payload": payload,
                "idempotency_key": idempotency_key,
            }
        )
        return SimpleNamespace(id=77), True

    monkeypatch.setattr(business_service, "post_journal_entry", fake_post_journal_entry)

    async def fake_resolve_voucher_account_id(_session, *, account_id, **_kwargs):
        return int(account_id)

    monkeypatch.setattr(business_service, "_resolve_voucher_account_id", fake_resolve_voucher_account_id)

    result = await business_service.post_typed_voucher(
        None,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        created_by="owner-1",
        payload=TypedVoucherCreateRequest(
            voucher_type="receipt",
            entry_date=date(2026, 5, 20),
            amount=Decimal("500.00"),
            debit_account_id=10,
            credit_account_id=20,
            description="Receipt from customer",
            reference="RV-1",
        ),
        idempotency_key="idem-1",
    )

    assert captured["tenant_id"] == "business-tenant"
    assert captured["app_key"] == "mitrabooks"
    assert captured["accounting_entity_id"] == "primary"
    assert captured["idempotency_key"] == "idem-1"
    assert captured["payload"].lines[0].debit == Decimal("500.00")
    assert captured["payload"].lines[1].credit == Decimal("500.00")
    assert result["status"] == "posted"
    assert result["journal_entry_id"] == 77
    assert result["voucher_number"] == "RV-1"
    assert vouchers.docs[0]["status"] == "posted"
    assert audit_events[0]["tenant_id"] == "business-tenant"
    assert audit_events[0]["product"] == "mitrabooks"
    assert audit_events[0]["action"] == "business_voucher_posted"
    assert audit_events[0]["new_value"]["journal_entry_id"] == 77


@pytest.mark.asyncio
async def test_typed_voucher_rolls_back_domain_record_when_posting_fails(monkeypatch):
    vouchers = FakeCollection()
    monkeypatch.setattr(business_service, "get_collection", lambda _name: vouchers)

    async def fake_post_journal_entry(*_args, **_kwargs):
        raise ValueError("debits must equal credits")

    monkeypatch.setattr(business_service, "post_journal_entry", fake_post_journal_entry)

    async def fake_resolve_voucher_account_id(_session, *, account_id, **_kwargs):
        return int(account_id)

    monkeypatch.setattr(business_service, "_resolve_voucher_account_id", fake_resolve_voucher_account_id)

    with pytest.raises(ValueError):
        await business_service.post_typed_voucher(
            None,
            tenant_id="business-tenant",
            app_key="mitrabooks",
            created_by="owner-1",
            payload=TypedVoucherCreateRequest(
                voucher_type="payment",
                entry_date=date(2026, 5, 20),
                amount=Decimal("100.00"),
                debit_account_id=30,
                credit_account_id=40,
                description="Payment to vendor",
            ),
            idempotency_key=None,
        )

    assert vouchers.docs == []
    assert vouchers.deleted[0]["tenant_id"] == "business-tenant"
    assert vouchers.deleted[0]["app_key"] == "mitrabooks"


@pytest.mark.asyncio
async def test_typed_voucher_reuses_idempotent_business_record(monkeypatch):
    vouchers = FakeCollection()
    monkeypatch.setattr(business_service, "get_collection", lambda _name: vouchers)

    async def fake_post_journal_entry(*_args, **_kwargs):
        return SimpleNamespace(id=88), True

    monkeypatch.setattr(business_service, "post_journal_entry", fake_post_journal_entry)

    async def fake_resolve_voucher_account_id(_session, *, account_id, **_kwargs):
        return int(account_id)

    monkeypatch.setattr(business_service, "_resolve_voucher_account_id", fake_resolve_voucher_account_id)

    payload = TypedVoucherCreateRequest(
        voucher_type="journal",
        entry_date=date(2026, 5, 20),
        amount=Decimal("75.00"),
        debit_account_id=11,
        credit_account_id=12,
        description="Adjustment entry",
    )

    first = await business_service.post_typed_voucher(
        None,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        created_by="owner-1",
        payload=payload,
        idempotency_key="idem-voucher-1",
    )
    second = await business_service.post_typed_voucher(
        None,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        created_by="owner-1",
        payload=payload,
        idempotency_key="idem-voucher-1",
    )

    assert first["voucher_id"] == second["voucher_id"]
    assert first["voucher_number"] == second["voucher_number"]
    assert first["created"] is True
    assert second["created"] is False
    assert len(vouchers.docs) == 1


@pytest.mark.asyncio
async def test_list_vouchers_filters_by_type_and_scope(monkeypatch):
    vouchers = FakeCollection()
    vouchers.docs = [
        {
            "voucher_id": "v1",
            "voucher_number": "RV-2026-2027-000001",
            "voucher_type": "receipt",
            "tenant_id": "business-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "entry_date": "2026-05-20",
            "journal_entry_id": 77,
            "created_by": "owner-1",
            "created_at": "2026-05-20T10:00:00Z",
            "updated_at": "2026-05-20T10:00:00Z",
        },
        {
            "voucher_id": "v2",
            "voucher_number": "PV-2026-2027-000001",
            "voucher_type": "payment",
            "tenant_id": "business-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "entry_date": "2026-05-19",
        },
        {
            "voucher_id": "v3",
            "voucher_number": "RV-2026-2027-000002",
            "voucher_type": "receipt",
            "tenant_id": "other-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "entry_date": "2026-05-21",
        },
    ]
    monkeypatch.setattr(business_service, "get_collection", lambda _name: vouchers)

    result = await business_service.list_vouchers(
        session=object(),
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        voucher_type="receipt",
        limit=10,
    )

    assert result["total"] == 1
    assert result["items"][0]["voucher_id"] == "v1"
    assert result["items"][0]["tenant_id"] == "business-tenant"
    assert result["items"][0]["journal_entry_id"] == 77
    assert result["items"][0]["created"] is False


@pytest.mark.asyncio
async def test_reverse_typed_voucher_posts_accounting_reversal(monkeypatch):
    vouchers = FakeCollection()
    audit_events = []
    vouchers.docs = [
        {
            "voucher_id": "voucher-1",
            "voucher_number": "RV-2026-2027-000001",
            "voucher_type": "receipt",
            "tenant_id": "business-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "party_id": None,
            "amount": "500.00",
            "entry_date": "2026-05-20",
            "debit_account_id": 10,
            "credit_account_id": 20,
            "description": "Receipt from customer",
            "reference": "RV-2026-2027-000001",
            "journal_entry_id": 77,
            "status": "posted",
            "created_by": "owner-1",
            "created_at": business_service._now(),
            "updated_at": business_service._now(),
        }
    ]
    captured = {}
    monkeypatch.setattr(business_service, "get_collection", lambda _name: vouchers)

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    async def fake_reverse_journal_entry(session, *, tenant_id, app_key, accounting_entity_id, created_by, journal_id, reversal_date, reason, idempotency_key):
        captured.update(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "accounting_entity_id": accounting_entity_id,
                "created_by": created_by,
                "journal_id": journal_id,
                "reversal_date": reversal_date,
                "reason": reason,
                "idempotency_key": idempotency_key,
            }
        )
        return SimpleNamespace(id=99), True

    monkeypatch.setattr(business_service, "reverse_journal_entry", fake_reverse_journal_entry)

    result = await business_service.reverse_typed_voucher(
        None,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        voucher_id="voucher-1",
        created_by="owner-1",
        payload=TypedVoucherReversalRequest(
            reversal_date=date(2026, 5, 21),
            reason="Duplicate receipt",
        ),
        idempotency_key="reverse-voucher-1",
    )

    assert captured["tenant_id"] == "business-tenant"
    assert captured["app_key"] == "mitrabooks"
    assert captured["journal_id"] == 77
    assert captured["idempotency_key"] == "reverse-voucher-1"
    assert result["status"] == "reversed"
    assert result["reversal_journal_entry_id"] == 99
    assert result["created"] is True
    assert vouchers.docs[0]["status"] == "reversed"
    assert audit_events[0]["action"] == "business_voucher_reversed"
    assert audit_events[0]["old_value"]["status"] == "posted"
    assert audit_events[0]["new_value"]["status"] == "reversed"


@pytest.mark.asyncio
async def test_reverse_typed_voucher_is_idempotent_after_domain_status(monkeypatch):
    vouchers = FakeCollection()
    vouchers.docs = [
        {
            "voucher_id": "voucher-1",
            "tenant_id": "business-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "journal_entry_id": 77,
            "status": "reversed",
            "reversal_journal_entry_id": 99,
        }
    ]
    monkeypatch.setattr(business_service, "get_collection", lambda _name: vouchers)

    async def fail_reverse_journal_entry(*_args, **_kwargs):
        raise AssertionError("accounting reversal should not be called again")

    monkeypatch.setattr(business_service, "reverse_journal_entry", fail_reverse_journal_entry)

    result = await business_service.reverse_typed_voucher(
        None,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        voucher_id="voucher-1",
        created_by="owner-1",
        payload=TypedVoucherReversalRequest(reason="Duplicate receipt"),
        idempotency_key=None,
    )

    assert result["created"] is False
    assert result["reversal_journal_entry_id"] == 99


def _seed_customer(collection):
    collection.docs.append(
        {
            "party_id": "cust-1",
            "tenant_id": "business-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "party_name": "Acme Traders",
            "party_type": "customer",
            "party_code": "CUST-001",
            "gstin": "29ABCDE1234F1Z5",
            "is_active": True,
        }
    )


@pytest.mark.asyncio
async def test_sales_invoice_posts_balanced_gst_journal(monkeypatch):
    store = FakeCollection()
    _seed_customer(store)
    captured = {}
    audit_events = []
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)

    async def fake_init_coa(*_args, **_kwargs):
        return None

    monkeypatch.setattr(business_service, "initialize_default_chart_of_accounts", fake_init_coa)

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    async def fake_resolve(_session, *, account_code, **_kwargs):
        return _INVOICE_ACCOUNT_IDS[account_code]

    monkeypatch.setattr(business_service, "_resolve_voucher_account_id", fake_resolve)

    async def fake_post_journal_entry(session, *, payload, **kwargs):
        captured["payload"] = payload
        captured.update(kwargs)
        return SimpleNamespace(id=501), True

    monkeypatch.setattr(business_service, "post_journal_entry", fake_post_journal_entry)

    result = await business_service.create_sales_invoice(
        None,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        created_by="owner-1",
        payload=SalesInvoiceCreateRequest(
            customer_party_id="cust-1",
            invoice_date=date(2026, 6, 8),
            is_inter_state=False,
            line_items=[
                SalesInvoiceLineItem(description="Widget", quantity=Decimal("10"), rate=Decimal("100"), gst_rate=Decimal("18")),
                SalesInvoiceLineItem(description="Service", quantity=Decimal("1"), rate=Decimal("5000"), gst_rate=Decimal("18")),
            ],
        ),
        idempotency_key="inv-idem-1",
    )

    lines = captured["payload"].lines
    total_debit = sum(line.debit for line in lines)
    total_credit = sum(line.credit for line in lines)
    assert total_debit == total_credit == Decimal("7080.00")
    # AR debit carries the full invoice total.
    assert lines[0].account_id == _INVOICE_ACCOUNT_IDS["12001"]
    assert lines[0].debit == Decimal("7080.00")
    # Income credit is the taxable base; CGST + SGST credits carry the tax.
    assert lines[1].account_id == _INVOICE_ACCOUNT_IDS["41001"]
    assert lines[1].credit == Decimal("6000.00")
    gst_lines = {line.account_id: line.credit for line in lines[2:]}
    assert gst_lines == {_INVOICE_ACCOUNT_IDS["22001"]: Decimal("540.00"), _INVOICE_ACCOUNT_IDS["22002"]: Decimal("540.00")}
    assert captured["payload"].source_document_type == "sales_invoice"

    assert result["status"] == "posted"
    assert result["journal_entry_id"] == 501
    assert result["invoice_number"].startswith("INV-2026-2027-")
    assert result["taxable_total"] == "6000.00"
    assert result["cgst_total"] == "540.00"
    assert result["sgst_total"] == "540.00"
    assert result["igst_total"] == "0.00"
    assert result["invoice_total"] == "7080.00"
    assert result["customer_name"] == "Acme Traders"
    assert audit_events[0]["action"] == "business_sales_invoice_posted"


@pytest.mark.asyncio
async def test_sales_invoice_inter_state_uses_igst(monkeypatch):
    store = FakeCollection()
    _seed_customer(store)
    captured = {}
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "initialize_default_chart_of_accounts", lambda *a, **k: _async_none())
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_k: _async_none())

    async def fake_resolve(_session, *, account_code, **_kwargs):
        return _INVOICE_ACCOUNT_IDS[account_code]

    monkeypatch.setattr(business_service, "_resolve_voucher_account_id", fake_resolve)

    async def fake_post_journal_entry(session, *, payload, **kwargs):
        captured["payload"] = payload
        return SimpleNamespace(id=502), True

    monkeypatch.setattr(business_service, "post_journal_entry", fake_post_journal_entry)

    result = await business_service.create_sales_invoice(
        None,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        created_by="owner-1",
        payload=SalesInvoiceCreateRequest(
            customer_party_id="cust-1",
            invoice_date=date(2026, 6, 8),
            is_inter_state=True,
            line_items=[SalesInvoiceLineItem(description="Widget", quantity=Decimal("10"), rate=Decimal("100"), gst_rate=Decimal("18"))],
        ),
        idempotency_key=None,
    )

    gst_lines = {line.account_id: line.credit for line in captured["payload"].lines[2:]}
    assert gst_lines == {_INVOICE_ACCOUNT_IDS["22003"]: Decimal("180.00")}
    assert result["igst_total"] == "180.00"
    assert result["cgst_total"] == "0.00"
    assert result["invoice_total"] == "1180.00"


@pytest.mark.asyncio
async def test_cancel_sales_invoice_posts_reversal(monkeypatch):
    store = FakeCollection()
    store.docs = [
        {
            "invoice_id": "inv-1",
            "invoice_number": "INV-2026-2027-000001",
            "tenant_id": "business-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "customer_party_id": "cust-1",
            "invoice_date": "2026-06-08",
            "journal_entry_id": 501,
            "status": "posted",
            "invoice_total": "1180.00",
            "created_by": "owner-1",
            "created_at": business_service._now(),
            "updated_at": business_service._now(),
        }
    ]
    captured = {}
    audit_events = []
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    async def fake_reverse(session, *, journal_id, **kwargs):
        captured["journal_id"] = journal_id
        captured.update(kwargs)
        return SimpleNamespace(id=601), True

    monkeypatch.setattr(business_service, "reverse_journal_entry", fake_reverse)

    result = await business_service.cancel_sales_invoice(
        None,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        invoice_id="inv-1",
        created_by="owner-2",
        payload=SalesInvoiceCancelRequest(reason="Wrong customer", cancel_date=date(2026, 6, 20)),
        idempotency_key=None,
    )

    assert captured["journal_id"] == 501
    assert result["status"] == "cancelled"
    assert result["reversal_journal_entry_id"] == 601
    assert store.docs[0]["status"] == "cancelled"
    assert audit_events[0]["action"] == "business_sales_invoice_cancelled"


def _seed_vendor(collection):
    collection.docs.append(
        {
            "party_id": "vend-1",
            "tenant_id": "business-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "party_name": "Bharat Supplies",
            "party_type": "vendor",
            "party_code": "VEND-001",
            "gstin": "27AAACB1234C1Z9",
            "is_active": True,
        }
    )


@pytest.mark.asyncio
async def test_purchase_bill_posts_balanced_itc_journal(monkeypatch):
    store = FakeCollection()
    _seed_vendor(store)
    captured = {}
    audit_events = []
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "initialize_default_chart_of_accounts", lambda *a, **k: _async_none())

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    async def fake_resolve(_session, *, account_code, **_kwargs):
        return _INVOICE_ACCOUNT_IDS[account_code]

    monkeypatch.setattr(business_service, "_resolve_voucher_account_id", fake_resolve)

    async def fake_post_journal_entry(session, *, payload, **kwargs):
        captured["payload"] = payload
        return SimpleNamespace(id=801), True

    monkeypatch.setattr(business_service, "post_journal_entry", fake_post_journal_entry)

    result = await business_service.create_purchase_bill(
        None,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        created_by="owner-1",
        payload=PurchaseBillCreateRequest(
            vendor_party_id="vend-1",
            bill_number="SUP-2026-77",
            bill_date=date(2026, 6, 8),
            is_inter_state=False,
            line_items=[PurchaseBillLineItem(description="Raw material", quantity=Decimal("10"), rate=Decimal("100"), gst_rate=Decimal("18"))],
        ),
        idempotency_key=None,
    )

    lines = captured["payload"].lines
    total_debit = sum(line.debit for line in lines)
    total_credit = sum(line.credit for line in lines)
    assert total_debit == total_credit == Decimal("1180.00")
    # Expense debit = taxable; Input CGST/SGST debited (ITC asset).
    debits = {line.account_id: line.debit for line in lines if line.debit > 0}
    assert debits[_INVOICE_ACCOUNT_IDS["51001"]] == Decimal("1000.00")
    assert debits[_INVOICE_ACCOUNT_IDS["14001"]] == Decimal("90.00")
    assert debits[_INVOICE_ACCOUNT_IDS["14002"]] == Decimal("90.00")
    # Accounts Payable credited with the full bill total.
    credits = {line.account_id: line.credit for line in lines if line.credit > 0}
    assert credits == {_INVOICE_ACCOUNT_IDS["21001"]: Decimal("1180.00")}
    assert captured["payload"].source_document_type == "purchase_bill"

    assert result["status"] == "posted"
    assert result["journal_entry_id"] == 801
    assert result["bill_number"] == "SUP-2026-77"
    assert result["vendor_name"] == "Bharat Supplies"
    assert result["igst_total"] == "0.00"
    assert result["bill_total"] == "1180.00"
    assert audit_events[0]["action"] == "business_purchase_bill_posted"


@pytest.mark.asyncio
async def test_cancel_purchase_bill_posts_reversal(monkeypatch):
    store = FakeCollection()
    store.docs = [
        {
            "bill_id": "bill-1",
            "bill_number": "SUP-2026-77",
            "tenant_id": "business-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "vendor_party_id": "vend-1",
            "bill_date": "2026-06-08",
            "journal_entry_id": 801,
            "status": "posted",
            "bill_total": "1180.00",
            "created_by": "owner-1",
            "created_at": business_service._now(),
            "updated_at": business_service._now(),
        }
    ]
    captured = {}
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_k: _async_none())

    async def fake_reverse(session, *, journal_id, **kwargs):
        captured["journal_id"] = journal_id
        return SimpleNamespace(id=901), True

    monkeypatch.setattr(business_service, "reverse_journal_entry", fake_reverse)

    result = await business_service.cancel_purchase_bill(
        None,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        bill_id="bill-1",
        created_by="owner-2",
        payload=PurchaseBillCancelRequest(reason="Duplicate bill", cancel_date=date(2026, 6, 20)),
        idempotency_key=None,
    )

    assert captured["journal_id"] == 801
    assert result["status"] == "cancelled"
    assert result["reversal_journal_entry_id"] == 901
    assert store.docs[0]["status"] == "cancelled"


def _posted_invoice_doc():
    return {
        "invoice_id": "inv-9",
        "invoice_number": "INV-2026-2027-000009",
        "tenant_id": "business-tenant",
        "app_key": "mitrabooks",
        "accounting_entity_id": "primary",
        "customer_party_id": "cust-1",
        "invoice_date": "2026-06-08",
        "journal_entry_id": 501,
        "status": "posted",
        "invoice_total": "1180.00",
        "created_by": "owner-1",
        "created_at": business_service._now(),
        "updated_at": business_service._now(),
    }


@pytest.mark.asyncio
async def test_reversal_rejected_when_date_crosses_gst_period(monkeypatch):
    store = FakeCollection()
    store.docs = [_posted_invoice_doc()]
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_k: _async_none())

    async def fail_reverse(*_a, **_k):
        raise AssertionError("reverse_journal_entry must not run for a cross-period reversal")

    monkeypatch.setattr(business_service, "reverse_journal_entry", fail_reverse)

    with pytest.raises(business_service.AccountingValidationError, match="must be dated within June 2026"):
        await business_service.cancel_sales_invoice(
            None, tenant_id="business-tenant", app_key="mitrabooks", invoice_id="inv-9",
            created_by="owner-2",
            payload=SalesInvoiceCancelRequest(reason="x", cancel_date=date(2026, 7, 1)),
            idempotency_key=None,
        )


@pytest.mark.asyncio
async def test_reversal_rejected_when_period_is_locked(monkeypatch):
    store = FakeCollection()
    store.docs = [
        _posted_invoice_doc(),
        {"tenant_id": "business-tenant", "app_key": "mitrabooks", "accounting_entity_id": "primary", "period": "2026-06", "locked": True},
    ]
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_k: _async_none())

    async def fail_reverse(*_a, **_k):
        raise AssertionError("reverse_journal_entry must not run when the period is locked")

    monkeypatch.setattr(business_service, "reverse_journal_entry", fail_reverse)

    with pytest.raises(business_service.AccountingValidationError, match="finalised and locked"):
        await business_service.cancel_sales_invoice(
            None, tenant_id="business-tenant", app_key="mitrabooks", invoice_id="inv-9",
            created_by="owner-2",
            payload=SalesInvoiceCancelRequest(reason="x", cancel_date=date(2026, 6, 20)),
            idempotency_key=None,
        )


@pytest.mark.asyncio
async def test_gst_period_lock_blocks_then_unlock_allows(monkeypatch):
    from app.modules.business.schemas import GstPeriodLockUpdateRequest

    store = FakeCollection()
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_k: _async_none())

    await business_service.set_gst_period_lock(
        tenant_id="business-tenant", app_key="mitrabooks", updated_by="admin-1",
        payload=GstPeriodLockUpdateRequest(period="2026-06", locked=True),
    )
    assert await business_service.is_gst_period_locked(
        tenant_id="business-tenant", app_key="mitrabooks", accounting_entity_id="primary", period="2026-06",
    ) is True

    listed = await business_service.list_gst_period_locks(
        tenant_id="business-tenant", app_key="mitrabooks", accounting_entity_id="primary",
    )
    assert listed["items"][0]["period"] == "2026-06"
    assert listed["items"][0]["locked"] is True

    await business_service.set_gst_period_lock(
        tenant_id="business-tenant", app_key="mitrabooks", updated_by="admin-1",
        payload=GstPeriodLockUpdateRequest(period="2026-06", locked=False),
    )
    assert await business_service.is_gst_period_locked(
        tenant_id="business-tenant", app_key="mitrabooks", accounting_entity_id="primary", period="2026-06",
    ) is False


@pytest.mark.asyncio
async def test_credit_note_posts_mirror_of_invoice(monkeypatch):
    store = FakeCollection()
    _seed_customer(store)
    captured = {}
    audit_events = []
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "initialize_default_chart_of_accounts", lambda *a, **k: _async_none())

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    async def fake_resolve(_session, *, account_code, **_kwargs):
        return _INVOICE_ACCOUNT_IDS[account_code]

    monkeypatch.setattr(business_service, "_resolve_voucher_account_id", fake_resolve)

    async def fake_post_journal_entry(session, *, payload, **kwargs):
        captured["payload"] = payload
        return SimpleNamespace(id=1001), True

    monkeypatch.setattr(business_service, "post_journal_entry", fake_post_journal_entry)

    result = await business_service.create_credit_note(
        None,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        created_by="owner-1",
        payload=CreditNoteCreateRequest(
            customer_party_id="cust-1",
            note_date=date(2026, 6, 20),
            original_invoice_number="INV-2026-2027-000001",
            reason="sales_return",
            is_inter_state=False,
            line_items=[CreditNoteLineItem(description="Returned widget", quantity=Decimal("10"), rate=Decimal("100"), gst_rate=Decimal("18"))],
        ),
        idempotency_key=None,
    )

    lines = captured["payload"].lines
    assert sum(l.debit for l in lines) == sum(l.credit for l in lines) == Decimal("1180.00")
    # Mirror of invoice: income + output GST are DEBITED (reduced); receivable is CREDITED (reduced).
    debits = {l.account_id: l.debit for l in lines if l.debit > 0}
    assert debits[_INVOICE_ACCOUNT_IDS["41001"]] == Decimal("1000.00")
    assert debits[_INVOICE_ACCOUNT_IDS["22001"]] == Decimal("90.00")
    assert debits[_INVOICE_ACCOUNT_IDS["22002"]] == Decimal("90.00")
    credits = {l.account_id: l.credit for l in lines if l.credit > 0}
    assert credits == {_INVOICE_ACCOUNT_IDS["12001"]: Decimal("1180.00")}
    assert captured["payload"].source_document_type == "credit_note"
    assert result["credit_note_number"].startswith("CN-2026-2027-")
    assert result["note_total"] == "1180.00"
    assert result["status"] == "posted"
    assert audit_events[0]["action"] == "business_credit_note_posted"


@pytest.mark.asyncio
async def test_credit_note_blocked_in_locked_period(monkeypatch):
    store = FakeCollection()
    _seed_customer(store)
    store.docs.append({"tenant_id": "business-tenant", "app_key": "mitrabooks", "accounting_entity_id": "primary", "period": "2026-06", "locked": True})
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "initialize_default_chart_of_accounts", lambda *a, **k: _async_none())
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_k: _async_none())

    async def fail_post(*_a, **_k):
        raise AssertionError("must not post into a locked period")

    monkeypatch.setattr(business_service, "post_journal_entry", fail_post)

    with pytest.raises(business_service.AccountingValidationError, match="finalised and locked"):
        await business_service.create_credit_note(
            None, tenant_id="business-tenant", app_key="mitrabooks", created_by="owner-1",
            payload=CreditNoteCreateRequest(
                customer_party_id="cust-1", note_date=date(2026, 6, 20),
                line_items=[CreditNoteLineItem(description="x", quantity=Decimal("1"), rate=Decimal("100"), gst_rate=Decimal("18"))],
            ),
            idempotency_key=None,
        )


@pytest.mark.asyncio
async def test_debit_note_posts_mirror_of_bill(monkeypatch):
    store = FakeCollection()
    _seed_vendor(store)
    captured = {}
    audit_events = []
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "initialize_default_chart_of_accounts", lambda *a, **k: _async_none())

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    async def fake_resolve(_session, *, account_code, **_kwargs):
        return _INVOICE_ACCOUNT_IDS[account_code]

    monkeypatch.setattr(business_service, "_resolve_voucher_account_id", fake_resolve)

    async def fake_post_journal_entry(session, *, payload, **kwargs):
        captured["payload"] = payload
        return SimpleNamespace(id=1101), True

    monkeypatch.setattr(business_service, "post_journal_entry", fake_post_journal_entry)

    result = await business_service.create_debit_note(
        None,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        created_by="owner-1",
        payload=DebitNoteCreateRequest(
            vendor_party_id="vend-1",
            note_date=date(2026, 6, 20),
            original_bill_number="SUP-2026-77",
            reason="purchase_return",
            is_inter_state=False,
            line_items=[DebitNoteLineItem(description="Returned material", quantity=Decimal("10"), rate=Decimal("100"), gst_rate=Decimal("18"))],
        ),
        idempotency_key=None,
    )

    lines = captured["payload"].lines
    assert sum(l.debit for l in lines) == sum(l.credit for l in lines) == Decimal("1180.00")
    # Mirror of a purchase bill: payable DEBITED (reduced); expense + Input GST CREDITED (reduced).
    assert {l.account_id: l.debit for l in lines if l.debit > 0} == {_INVOICE_ACCOUNT_IDS["21001"]: Decimal("1180.00")}
    credits = {l.account_id: l.credit for l in lines if l.credit > 0}
    assert credits[_INVOICE_ACCOUNT_IDS["51001"]] == Decimal("1000.00")
    assert credits[_INVOICE_ACCOUNT_IDS["14001"]] == Decimal("90.00")
    assert credits[_INVOICE_ACCOUNT_IDS["14002"]] == Decimal("90.00")
    assert captured["payload"].source_document_type == "debit_note"
    assert result["debit_note_number"].startswith("DN-2026-2027-")
    assert result["note_total"] == "1180.00"
    assert result["status"] == "posted"
    assert audit_events[0]["action"] == "business_debit_note_posted"


def test_gst_setoff_follows_statutory_order():
    from decimal import Decimal as D
    util, cash, carry = business_service._compute_gst_setoff(
        {"igst": D("100"), "cgst": D("500"), "sgst": D("500")},
        {"igst": D("600"), "cgst": D("200"), "sgst": D("100")},
    )
    # IGST credit pays IGST then CGST; SGST credit pays SGST; CGST credit unused.
    assert util == {"igst": D("600"), "cgst": D("0"), "sgst": D("100")}
    assert cash == {"igst": D("0"), "cgst": D("0"), "sgst": D("400")}
    assert carry == {"igst": D("0"), "cgst": D("200"), "sgst": D("0")}


@pytest.mark.asyncio
async def test_gst_settlement_posts_balanced_setoff_entry(monkeypatch):
    from app.modules.business.schemas import GstSettlementCreateRequest

    store = FakeCollection()
    captured = {}
    audit_events = []
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "initialize_default_chart_of_accounts", lambda *a, **k: _async_none())

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    async def fake_balances(session, **_kwargs):
        return {
            "output": {"igst": Decimal("100"), "cgst": Decimal("500"), "sgst": Decimal("500")},
            "credit": {"igst": Decimal("600"), "cgst": Decimal("200"), "sgst": Decimal("100")},
        }

    monkeypatch.setattr(business_service, "_gst_period_balances", fake_balances)

    async def fake_resolve(_session, *, account_code, **_kwargs):
        return _INVOICE_ACCOUNT_IDS[account_code]

    monkeypatch.setattr(business_service, "_resolve_voucher_account_id", fake_resolve)

    async def fake_post_journal_entry(session, *, payload, **kwargs):
        captured["payload"] = payload
        return SimpleNamespace(id=1201), True

    monkeypatch.setattr(business_service, "post_journal_entry", fake_post_journal_entry)

    result = await business_service.create_gst_settlement(
        None,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        created_by="admin-1",
        payload=GstSettlementCreateRequest(period="2026-06", lock_period=True),
        idempotency_key=None,
    )

    lines = captured["payload"].lines
    assert sum(l.debit for l in lines) == sum(l.credit for l in lines) == Decimal("1100.00")
    # Output debited to clear; Input credited by utilized amounts; net cash to GST Payable.
    debits = {l.account_id: l.debit for l in lines if l.debit > 0}
    assert debits[_INVOICE_ACCOUNT_IDS["22001"]] == Decimal("500")  # output CGST
    assert debits[_INVOICE_ACCOUNT_IDS["22003"]] == Decimal("100")  # output IGST
    credits = {l.account_id: l.credit for l in lines if l.credit > 0}
    assert credits[_INVOICE_ACCOUNT_IDS["14003"]] == Decimal("600")  # input IGST utilized
    assert credits[_INVOICE_ACCOUNT_IDS["14002"]] == Decimal("100")  # input SGST utilized
    assert credits[_INVOICE_ACCOUNT_IDS["22004"]] == Decimal("400")  # net cash payable
    assert _INVOICE_ACCOUNT_IDS["14001"] not in credits  # CGST credit unused

    assert result["status"] == "posted"
    assert result["net_cash_payable"] == "400"
    assert result["period_locked"] is True
    assert result["journal_entry_id"] == 1201
    assert audit_events and audit_events[-1]["action"] == "business_gst_settlement_posted"
    # The period lock doc was written.
    assert any(d.get("period") == "2026-06" and d.get("locked") for d in store.docs)


def _async_none():
    async def _noop():
        return None
    return _noop()


@pytest.mark.asyncio
async def test_invoice_settings_save_and_get_round_trip(monkeypatch):
    from app.modules.business.schemas import InvoiceSettingsUpdateRequest, InvoiceNumberingConfig, InvoiceFieldRule

    store = FakeCollection()
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_k: _async_none())

    payload = InvoiceSettingsUpdateRequest(
        field_config={"due_date": InvoiceFieldRule(visible=True, required=True), "hsn_sac": InvoiceFieldRule(visible=False, required=False)},
        numbering=InvoiceNumberingConfig(prefix="ACME", number_format="{PREFIX}/{FYSHORT}/{SEQ}", seq_padding=4),
    )
    saved = await business_service.save_invoice_settings(
        tenant_id="business-tenant", app_key="mitrabooks", updated_by="admin-1", payload=payload,
    )
    assert saved["numbering"]["prefix"] == "ACME"
    assert saved["field_config"]["due_date"]["required"] is True
    assert saved["field_config"]["hsn_sac"]["visible"] is False
    # Unspecified standard fields fall back to defaults (visible).
    assert saved["field_config"]["reference"]["visible"] is True

    fetched = await business_service.get_invoice_settings(
        tenant_id="business-tenant", app_key="mitrabooks", accounting_entity_id="primary",
    )
    assert fetched["numbering"]["number_format"] == "{PREFIX}/{FYSHORT}/{SEQ}"
    assert fetched["updated_by"] == "admin-1"


@pytest.mark.asyncio
async def test_sales_invoice_uses_custom_numbering_and_enforces_required(monkeypatch):
    from app.modules.business.schemas import InvoiceSettingsUpdateRequest, InvoiceNumberingConfig, InvoiceFieldRule

    store = FakeCollection()
    _seed_customer(store)
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "initialize_default_chart_of_accounts", lambda *a, **k: _async_none())
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_k: _async_none())

    async def fake_resolve(_session, *, account_code, **_kwargs):
        return _INVOICE_ACCOUNT_IDS[account_code]

    monkeypatch.setattr(business_service, "_resolve_voucher_account_id", fake_resolve)

    async def fake_post_journal_entry(session, *, payload, **kwargs):
        return SimpleNamespace(id=701), True

    monkeypatch.setattr(business_service, "post_journal_entry", fake_post_journal_entry)

    # Admin configures custom numbering + makes due_date mandatory.
    await business_service.save_invoice_settings(
        tenant_id="business-tenant", app_key="mitrabooks", updated_by="admin-1",
        payload=InvoiceSettingsUpdateRequest(
            field_config={"due_date": InvoiceFieldRule(visible=True, required=True)},
            numbering=InvoiceNumberingConfig(prefix="ACME", number_format="{PREFIX}/{FYSHORT}/{SEQ}", seq_padding=4),
        ),
    )

    base = dict(
        customer_party_id="cust-1",
        invoice_date=date(2026, 6, 8),
        line_items=[SalesInvoiceLineItem(description="Widget", quantity=Decimal("1"), rate=Decimal("100"), gst_rate=Decimal("18"))],
    )

    # Missing required due_date -> rejected.
    with pytest.raises(business_service.AccountingValidationError):
        await business_service.create_sales_invoice(
            None, tenant_id="business-tenant", app_key="mitrabooks", created_by="owner-1",
            payload=SalesInvoiceCreateRequest(**base), idempotency_key=None,
        )

    # With due_date -> posts, and uses the custom number format.
    result = await business_service.create_sales_invoice(
        None, tenant_id="business-tenant", app_key="mitrabooks", created_by="owner-1",
        payload=SalesInvoiceCreateRequest(due_date=date(2026, 7, 8), **base), idempotency_key=None,
    )
    assert result["invoice_number"] == "ACME/2026-27/0001"
    assert result["status"] == "posted"


def test_business_resolver_rejects_wrong_app_key():
    with pytest.raises(HTTPException) as exc:
        resolve_business_app_tenant(
            current_user={"tenant_id": "business-tenant", "app_key": "mitrabooks"},
            x_tenant_id=None,
            x_app_key="mandirmitra",
            expected_app_key="mitrabooks",
            operation="voucher posting",
        )

    assert exc.value.status_code == 403


def test_business_resolver_blocks_default_tenant_for_writes():
    with pytest.raises(HTTPException) as exc:
        resolve_business_app_tenant(
            current_user={"tenant_id": "default", "app_key": "mitrabooks", "role": "super_admin"},
            x_tenant_id=None,
            x_app_key="mitrabooks",
            expected_app_key="mitrabooks",
            operation="voucher posting",
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_ca_document_metadata_is_tenant_and_app_scoped(monkeypatch):
    documents = FakeCollection()
    audit_events = []
    monkeypatch.setattr(business_service, "get_collection", lambda _name: documents)

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    result = await business_service.create_ca_document_metadata(
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        created_by="reviewer-1",
        payload=CaDocumentCreateRequest(
            client_name="Jayam Publications",
            document_type="Bank statement",
            period="May 2026",
            assigned_to="Staff A",
            original_file_name="jayam-bank-may.pdf",
            notes="For reconciliation",
        ),
    )

    documents.docs.append(
        {
            **documents.docs[0],
            "document_id": "other-tenant-doc",
            "tenant_id": "other-tenant",
            "client_name": "Other Client",
        }
    )

    listed = await business_service.list_ca_document_metadata(
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
    )

    assert result["tenant_id"] == "business-tenant"
    assert result["app_key"] == "mitrabooks"
    assert result["status"] == "uploaded"
    assert result["next_action"] == "Classify document and assign reviewer"
    assert [row["client_name"] for row in listed["items"]] == ["Jayam Publications"]
    assert audit_events[0]["action"] == "business_ca_document_metadata_created"
    assert audit_events[0]["tenant_id"] == "business-tenant"


@pytest.mark.asyncio
async def test_update_ca_document_metadata_advances_status_with_tenant_scope(monkeypatch):
    documents = FakeCollection()
    now = business_service._now()
    documents.docs = [
        {
            "document_id": "doc-1",
            "tenant_id": "business-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "client_name": "Kartik Enterprises",
            "document_type": "Purchase bills",
            "period": "May 2026",
            "status": "uploaded",
            "assigned_to": "Staff A",
            "original_file_name": "kartik-bills.zip",
            "next_action": "Classify document and assign reviewer",
            "posting_reference": None,
            "notes": None,
            "created_by": "reviewer-1",
            "created_at": now,
            "updated_at": now,
        }
    ]
    monkeypatch.setattr(business_service, "get_collection", lambda _name: documents)
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_kwargs: None)

    result = await business_service.update_ca_document_metadata(
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        document_id="doc-1",
        updated_by="partner-1",
        payload=CaDocumentUpdateRequest(status="under_review"),
    )
    wrong_tenant = await business_service.update_ca_document_metadata(
        tenant_id="other-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        document_id="doc-1",
        updated_by="partner-1",
        payload=CaDocumentUpdateRequest(status="posted"),
    )

    assert result is not None
    assert result["status"] == "under_review"
    assert result["next_action"] == "Review support and raise query if needed"
    assert wrong_tenant is None


# ===================== ITC Reversal (GST Rule 37) =====================


def _posted_bill_doc(**overrides):
    doc = {
        "bill_id": "bill-itc",
        "bill_number": "SUP-2026-90",
        "tenant_id": "business-tenant",
        "app_key": "mitrabooks",
        "accounting_entity_id": "primary",
        "vendor_party_id": "vend-1",
        "vendor_name": "Bharat Supplies",
        "bill_date": "2026-01-01",
        "journal_entry_id": 801,
        "status": "posted",
        "taxable_total": "1000.00",
        "cgst_total": "90.00",
        "sgst_total": "90.00",
        "igst_total": "0.00",
        "gst_total": "180.00",
        "bill_total": "1180.00",
        "payment_status": "unpaid",
        "created_by": "owner-1",
        "created_at": business_service._now(),
        "updated_at": business_service._now(),
    }
    doc.update(overrides)
    return doc


def test_itc_interest_computation():
    # 180 ITC, availed 2026-01-01, reversed 2026-07-01 (181 days) at 18% p.a.
    interest = business_service._compute_itc_interest(
        Decimal("180"), date(2026, 1, 1), date(2026, 7, 1)
    )
    assert interest == Decimal("16.07")
    # No interest when the as-of date precedes the bill date.
    assert business_service._compute_itc_interest(
        Decimal("180"), date(2026, 7, 1), date(2026, 1, 1)
    ) == Decimal("0")


@pytest.mark.asyncio
async def test_mark_bill_payment_sets_status(monkeypatch):
    from app.modules.business.schemas import BillPaymentUpdateRequest

    store = FakeCollection()
    store.docs = [_posted_bill_doc()]
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_k: _async_none())

    partial = await business_service.mark_bill_payment(
        tenant_id="business-tenant", app_key="mitrabooks", bill_id="bill-itc", created_by="owner-1",
        payload=BillPaymentUpdateRequest(paid_amount=Decimal("500")),
    )
    assert partial["payment_status"] == "partial"
    assert partial["paid_amount"] == "500.00"
    assert partial["paid_date"] is not None

    full = await business_service.mark_bill_payment(
        tenant_id="business-tenant", app_key="mitrabooks", bill_id="bill-itc", created_by="owner-1",
        payload=BillPaymentUpdateRequest(paid_amount=Decimal("1180"), paid_date=date(2026, 7, 10)),
    )
    assert full["payment_status"] == "paid"
    assert full["paid_date"] == "2026-07-10"

    with pytest.raises(business_service.AccountingValidationError):
        await business_service.mark_bill_payment(
            tenant_id="business-tenant", app_key="mitrabooks", bill_id="bill-itc", created_by="owner-1",
            payload=BillPaymentUpdateRequest(paid_amount=Decimal("2000")),
        )


@pytest.mark.asyncio
async def test_itc_reversal_candidate_detected_after_180_days(monkeypatch):
    store = FakeCollection()
    store.docs = [
        _posted_bill_doc(bill_id="bill-A", bill_number="A", bill_date="2026-01-01"),  # overdue, unpaid
        _posted_bill_doc(bill_id="bill-B", bill_number="B", bill_date="2026-06-01"),  # within 180 days
        _posted_bill_doc(bill_id="bill-C", bill_number="C", payment_status="paid"),    # paid
        _posted_bill_doc(bill_id="bill-D", bill_number="D", itc_reversed=True),        # already reversed
        _posted_bill_doc(bill_id="bill-E", bill_number="E", cgst_total="0.00", sgst_total="0.00", igst_total="0.00", gst_total="0.00"),  # no ITC
    ]
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)

    preview = await business_service.preview_itc_reversals(
        tenant_id="business-tenant", app_key="mitrabooks", accounting_entity_id="primary",
        as_of=date(2026, 7, 1),
    )
    assert preview["count"] == 1
    cand = preview["candidates"][0]
    assert cand["bill_id"] == "bill-A"
    assert cand["due_date"] == "2026-06-30"
    assert cand["days_overdue"] == 1
    assert cand["itc_total"] == "180.00"
    assert cand["interest_amount"] == "16.07"
    assert cand["gstr3b_ref"] == "4(B)(2)"
    assert preview["total_itc"] == "180.00"
    assert preview["total_interest"] == "16.07"


@pytest.mark.asyncio
async def test_itc_reversal_posts_balanced_entry_with_interest(monkeypatch):
    from app.modules.business.schemas import ItcReversalActionRequest

    store = FakeCollection()
    store.docs = [_posted_bill_doc()]
    captured = {}
    post_calls = {"n": 0}
    audit_events = []
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "initialize_default_chart_of_accounts", lambda *a, **k: _async_none())
    monkeypatch.setattr(business_service, "is_gst_period_locked", lambda **_k: _async_none())

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    async def fake_resolve(_session, *, account_code, **_kwargs):
        return _INVOICE_ACCOUNT_IDS[account_code]

    monkeypatch.setattr(business_service, "_resolve_voucher_account_id", fake_resolve)

    async def fake_post_journal_entry(session, *, payload, **kwargs):
        post_calls["n"] += 1
        captured["payload"] = payload
        return SimpleNamespace(id=1301), True

    monkeypatch.setattr(business_service, "post_journal_entry", fake_post_journal_entry)

    result = await business_service.reverse_itc_for_bill(
        None, tenant_id="business-tenant", app_key="mitrabooks", bill_id="bill-itc", created_by="admin-1",
        payload=ItcReversalActionRequest(reversal_date=date(2026, 7, 1)), idempotency_key=None,
    )

    lines = captured["payload"].lines
    assert sum(l.debit for l in lines) == sum(l.credit for l in lines) == Decimal("196.07")
    debits = {l.account_id: l.debit for l in lines if l.debit > 0}
    assert debits[_INVOICE_ACCOUNT_IDS["14004"]] == Decimal("180.00")  # recoverable parking
    assert debits[_INVOICE_ACCOUNT_IDS["54006"]] == Decimal("16.07")   # interest expense
    credits = {l.account_id: l.credit for l in lines if l.credit > 0}
    assert credits[_INVOICE_ACCOUNT_IDS["14001"]] == Decimal("90.00")  # input CGST reversed
    assert credits[_INVOICE_ACCOUNT_IDS["14002"]] == Decimal("90.00")  # input SGST reversed
    assert credits[_INVOICE_ACCOUNT_IDS["23003"]] == Decimal("16.07")  # interest payable
    assert captured["payload"].source_document_type == "itc_reversal"

    assert result["itc_reversed"] is True
    assert result["itc_interest_amount"] == "16.07"
    assert result["itc_reversal_journal_entry_id"] == 1301
    assert audit_events[-1]["action"] == "business_itc_reversed"

    # Idempotent: a second call returns the existing reversal without re-posting.
    again = await business_service.reverse_itc_for_bill(
        None, tenant_id="business-tenant", app_key="mitrabooks", bill_id="bill-itc", created_by="admin-1",
        payload=ItcReversalActionRequest(reversal_date=date(2026, 7, 1)), idempotency_key=None,
    )
    assert post_calls["n"] == 1
    assert again["itc_reversed"] is True


@pytest.mark.asyncio
async def test_itc_reclaim_restores_credit(monkeypatch):
    from app.modules.business.schemas import ItcReclaimActionRequest

    store = FakeCollection()
    store.docs = [
        _posted_bill_doc(
            payment_status="paid",
            itc_reversed=True,
            itc_reversal_journal_entry_id=1301,
            itc_reversed_amounts={"igst": "0.00", "cgst": "90.00", "sgst": "90.00"},
            itc_interest_amount="16.07",
        )
    ]
    captured = {}
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "initialize_default_chart_of_accounts", lambda *a, **k: _async_none())
    monkeypatch.setattr(business_service, "is_gst_period_locked", lambda **_k: _async_none())
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_k: _async_none())

    async def fake_resolve(_session, *, account_code, **_kwargs):
        return _INVOICE_ACCOUNT_IDS[account_code]

    monkeypatch.setattr(business_service, "_resolve_voucher_account_id", fake_resolve)

    async def fake_post_journal_entry(session, *, payload, **kwargs):
        captured["payload"] = payload
        return SimpleNamespace(id=1401), True

    monkeypatch.setattr(business_service, "post_journal_entry", fake_post_journal_entry)

    result = await business_service.reclaim_itc_for_bill(
        None, tenant_id="business-tenant", app_key="mitrabooks", bill_id="bill-itc", created_by="admin-1",
        payload=ItcReclaimActionRequest(reclaim_date=date(2026, 7, 15)), idempotency_key=None,
    )

    lines = captured["payload"].lines
    assert sum(l.debit for l in lines) == sum(l.credit for l in lines) == Decimal("180.00")
    debits = {l.account_id: l.debit for l in lines if l.debit > 0}
    assert debits[_INVOICE_ACCOUNT_IDS["14001"]] == Decimal("90.00")  # input CGST restored
    assert debits[_INVOICE_ACCOUNT_IDS["14002"]] == Decimal("90.00")  # input SGST restored
    credits = {l.account_id: l.credit for l in lines if l.credit > 0}
    assert credits[_INVOICE_ACCOUNT_IDS["14004"]] == Decimal("180.00")  # recoverable cleared
    assert captured["payload"].source_document_type == "itc_reclaim"
    assert result["itc_reclaimed"] is True
    assert result["itc_reclaim_journal_entry_id"] == 1401


@pytest.mark.asyncio
async def test_itc_reclaim_requires_paid_bill(monkeypatch):
    from app.modules.business.schemas import ItcReclaimActionRequest

    store = FakeCollection()
    store.docs = [
        _posted_bill_doc(
            itc_reversed=True,
            itc_reversal_journal_entry_id=1301,
            itc_reversed_amounts={"igst": "0.00", "cgst": "90.00", "sgst": "90.00"},
            payment_status="unpaid",
        )
    ]
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "is_gst_period_locked", lambda **_k: _async_none())

    with pytest.raises(business_service.AccountingValidationError):
        await business_service.reclaim_itc_for_bill(
            None, tenant_id="business-tenant", app_key="mitrabooks", bill_id="bill-itc", created_by="admin-1",
            payload=ItcReclaimActionRequest(reclaim_date=date(2026, 7, 15)), idempotency_key=None,
        )


# ===================== Party sub-ledger tagging at posting sites =====================


def _party_tag_mocks(monkeypatch, store, captured):
    async def fake_init_coa(*_a, **_k):
        return None
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "initialize_default_chart_of_accounts", fake_init_coa)
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_k: _async_none())

    async def fake_resolve(_session, *, account_id=None, account_code=None, **_kwargs):
        return int(account_id) if account_id is not None else _INVOICE_ACCOUNT_IDS[account_code]
    monkeypatch.setattr(business_service, "_resolve_voucher_account_id", fake_resolve)

    async def fake_post(session, *, payload, **kwargs):
        captured["payload"] = payload
        return SimpleNamespace(id=999), True
    monkeypatch.setattr(business_service, "post_journal_entry", fake_post)


@pytest.mark.asyncio
async def test_sales_invoice_tags_receivable_line_with_customer(monkeypatch):
    store = FakeCollection(); _seed_customer(store); captured = {}
    _party_tag_mocks(monkeypatch, store, captured)
    await business_service.create_sales_invoice(
        None, tenant_id="business-tenant", app_key="mitrabooks", created_by="owner-1",
        payload=SalesInvoiceCreateRequest(
            customer_party_id="cust-1", invoice_date=date(2026, 6, 8), is_inter_state=False,
            line_items=[SalesInvoiceLineItem(description="W", quantity=Decimal("1"), rate=Decimal("100"), gst_rate=Decimal("18"))],
        ),
        idempotency_key=None,
    )
    lines = captured["payload"].lines
    receivable = lines[0]  # Dr receivable is first
    assert receivable.account_id == _INVOICE_ACCOUNT_IDS["12001"]
    assert receivable.party_id == "cust-1"
    # Income/GST lines carry no party tag.
    assert all(l.party_id is None for l in lines[1:])


@pytest.mark.asyncio
async def test_purchase_bill_tags_payable_line_with_vendor(monkeypatch):
    store = FakeCollection(); _seed_vendor(store); captured = {}
    _party_tag_mocks(monkeypatch, store, captured)
    await business_service.create_purchase_bill(
        None, tenant_id="business-tenant", app_key="mitrabooks", created_by="owner-1",
        payload=PurchaseBillCreateRequest(
            vendor_party_id="vend-1", bill_number="B-1", bill_date=date(2026, 6, 8), is_inter_state=False,
            line_items=[PurchaseBillLineItem(description="G", quantity=Decimal("1"), rate=Decimal("100"), gst_rate=Decimal("18"))],
        ),
        idempotency_key=None,
    )
    lines = captured["payload"].lines
    payable = [l for l in lines if l.account_id == _INVOICE_ACCOUNT_IDS["21001"]][0]
    assert payable.credit == Decimal("118.00")
    assert payable.party_id == "vend-1"
    assert all(l.party_id is None for l in lines if l.account_id != _INVOICE_ACCOUNT_IDS["21001"])


@pytest.mark.asyncio
async def test_receipt_voucher_tags_credit_line_payment_tags_debit(monkeypatch):
    # Receipt → party on the credit (customer/receivable) line.
    store = FakeCollection(); captured = {}
    _party_tag_mocks(monkeypatch, store, captured)
    await business_service.post_typed_voucher(
        None, tenant_id="business-tenant", app_key="mitrabooks", created_by="owner-1",
        payload=TypedVoucherCreateRequest(
            voucher_type="receipt", entry_date=date(2026, 6, 8), amount=Decimal("500"),
            debit_account_id=10, credit_account_id=20, party_id="cust-1", reference="RV-9",
            description="Receipt from customer",
        ),
        idempotency_key=None,
    )
    rlines = captured["payload"].lines
    assert rlines[0].party_id is None          # debit (bank) untagged
    assert rlines[1].party_id == "cust-1"      # credit (customer) tagged

    # Payment → party on the debit (vendor/payable) line.
    store2 = FakeCollection(); captured2 = {}
    _party_tag_mocks(monkeypatch, store2, captured2)
    await business_service.post_typed_voucher(
        None, tenant_id="business-tenant", app_key="mitrabooks", created_by="owner-1",
        payload=TypedVoucherCreateRequest(
            voucher_type="payment", entry_date=date(2026, 6, 8), amount=Decimal("500"),
            debit_account_id=30, credit_account_id=40, party_id="vend-1", reference="PV-9",
            description="Payment to vendor",
        ),
        idempotency_key=None,
    )
    plines = captured2["payload"].lines
    assert plines[0].party_id == "vend-1"      # debit (vendor) tagged
    assert plines[1].party_id is None          # credit (bank) untagged
