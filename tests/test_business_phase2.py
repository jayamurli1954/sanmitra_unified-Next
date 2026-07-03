from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.accounting.service import (
    AccountingNotFoundError,
    get_journal_voucher_detail,
    get_party_outstanding,
    get_trial_balance,
)
from app.modules.business import router as business_router
from app.modules.business import report_export
from app.modules.business.invoice_pdf import build_sales_invoice_pdf
from app.modules.business.statements import build_party_statement
import app.modules.business.service as business_service
from app.core.tenants.app_resolvers import resolve_business_app_tenant
from app.modules.business.schemas import (
    CaClientCreateRequest,
    CaClientUpdateRequest,
    CaDocumentCreateRequest,
    CaDocumentUpdateRequest,
    PartyCreateRequest,
    PartyUpdateRequest,
    CreditNoteCancelRequest,
    CreditNoteCreateRequest,
    CreditNoteLineItem,
    DebitNoteCancelRequest,
    DebitNoteCreateRequest,
    DebitNoteLineItem,
    PurchaseBillCancelRequest,
    PurchaseBillCreateRequest,
    PurchaseBillLineItem,
    BillPaymentUpdateRequest,
    ItcReclaimActionRequest,
    ItcReversalActionRequest,
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


class FailingUpdateCollection(FakeCollection):
    def __init__(self, *, fail_on_update_after_insert: bool = False):
        super().__init__()
        self.fail_on_update_after_insert = fail_on_update_after_insert
        self.insert_count = 0

    async def insert_one(self, doc):
        self.insert_count += 1
        await super().insert_one(doc)

    async def update_one(self, filters, update, upsert=False):
        if self.fail_on_update_after_insert and self.insert_count > 0:
            raise RuntimeError("simulated mongo update failure")
        await super().update_one(filters, update, upsert=upsert)


class AlwaysFailUpdateCollection(FakeCollection):
    async def update_one(self, filters, update, upsert=False):
        raise RuntimeError("simulated mongo update failure")


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
    assert result["opening_balance"] == "0.00"
    assert result["current_balance"] == "0.00"
    assert result["balance_source"] == "ledger_reports"
    assert parties.docs[0]["legacy_opening_balance_input"] == "125.50"
    assert "current_balance" not in parties.docs[0]
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
            "legacy_opening_balance_input": "125.50",
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
    assert result["opening_balance"] == "0.00"
    assert result["current_balance"] == "0.00"
    assert result["balance_source"] == "ledger_reports"
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

    assert result["status"] == "pending_approval"
    assert result["journal_entry_id"] is None
    assert result["voucher_number"] == "RV-1"
    assert result["approval_required"] is True
    assert result["approval_status"] == "pending_approval"
    assert vouchers.docs[0]["status"] == "pending_approval"
    assert audit_events[0]["tenant_id"] == "business-tenant"
    assert audit_events[0]["product"] == "mitrabooks"
    assert audit_events[0]["action"] == "business_voucher_created"
    assert audit_events[0]["new_value"]["journal_entry_id"] is None


@pytest.mark.asyncio
async def test_typed_voucher_creation_persists_pending_document_without_posting(monkeypatch):
    vouchers = FakeCollection()
    monkeypatch.setattr(business_service, "get_collection", lambda _name: vouchers)

    async def fake_resolve_voucher_account_id(_session, *, account_id, **_kwargs):
        return int(account_id)

    monkeypatch.setattr(business_service, "_resolve_voucher_account_id", fake_resolve_voucher_account_id)

    result = await business_service.post_typed_voucher(
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

    assert result["status"] == "pending_approval"
    assert result["approval_status"] == "pending_approval"
    assert len(vouchers.docs) == 1


@pytest.mark.asyncio
async def test_typed_voucher_approval_reverses_journal_when_status_update_fails(monkeypatch):
    vouchers = AlwaysFailUpdateCollection()
    captured = {}
    monkeypatch.setattr(business_service, "get_collection", lambda _name: vouchers)
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_k: _async_none())

    async def fake_post_journal_entry(_session, **_kwargs):
        return SimpleNamespace(id=78), True

    async def fake_reverse_journal_entry(_session, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id=88), True

    async def fake_resolve_voucher_account_id(_session, *, account_id, **_kwargs):
        return int(account_id)

    monkeypatch.setattr(business_service, "post_journal_entry", fake_post_journal_entry)
    monkeypatch.setattr(business_service, "reverse_journal_entry", fake_reverse_journal_entry)
    monkeypatch.setattr(business_service, "_resolve_voucher_account_id", fake_resolve_voucher_account_id)

    vouchers.docs = [{
        "voucher_id": "v-approve-1",
        "voucher_number": "RV-2",
        "voucher_type": "receipt",
        "tenant_id": "business-tenant",
        "app_key": "mitrabooks",
        "accounting_entity_id": "primary",
        "amount": "500.00",
        "entry_date": "2026-05-20",
        "debit_account_id": 10,
        "credit_account_id": 20,
        "description": "Receipt from customer",
        "reference": "RV-2",
        "status": "pending_approval",
        "approval_required": True,
        "approval_status": "pending_approval",
        "created_by": "owner-1",
        "created_at": business_service._now(),
        "updated_at": business_service._now(),
    }]

    with pytest.raises(business_service.AccountingValidationError, match="automatically reversed"):
        await business_service.review_typed_voucher(
            session=object(),
            tenant_id="business-tenant",
            app_key="mitrabooks",
            voucher_id="v-approve-1",
            reviewed_by="admin-1",
            payload=business_service.ApprovalReviewRequest(
                approve=True,
                notes="Approve and post",
                accounting_entity_id="primary",
            ),
        )

    assert captured["journal_id"] == 78
    assert captured["reason"].startswith("Compensation after business voucher approval persistence failure")
    assert captured["idempotency_key"].startswith("business-voucher-approve-compensate:")
    assert captured["tenant_id"] == "business-tenant"
    assert captured["app_key"] == "mitrabooks"
    assert captured["accounting_entity_id"] == "primary"


@pytest.mark.asyncio
async def test_review_typed_voucher_approval_posts_journal_and_updates_state(monkeypatch):
    vouchers = FakeCollection()
    captured = {}
    vouchers.docs = [
        {
            "voucher_id": "v-1",
            "voucher_number": "RV-1",
            "voucher_type": "receipt",
            "tenant_id": "business-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "amount": "500.00",
            "entry_date": "2026-05-20",
            "debit_account_id": 10,
            "credit_account_id": 20,
            "description": "Receipt from customer",
            "reference": "RV-1",
            "status": "pending_approval",
            "approval_required": True,
            "approval_status": "pending_approval",
            "created_by": "owner-1",
            "created_at": business_service._now(),
            "updated_at": business_service._now(),
        }
    ]
    audit_events = []
    monkeypatch.setattr(business_service, "get_collection", lambda _name: vouchers)

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    async def fake_post_journal_entry(_session, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id=77), True

    monkeypatch.setattr(business_service, "post_journal_entry", fake_post_journal_entry)

    result = await business_service.review_typed_voucher(
        session=object(),
        tenant_id="business-tenant",
        app_key="mitrabooks",
        voucher_id="v-1",
        reviewed_by="admin-1",
        payload=business_service.ApprovalReviewRequest(
            approve=True,
            notes="Voucher reviewed",
            accounting_entity_id="primary",
        ),
    )

    assert result["approval_required"] is True
    assert result["status"] == "posted"
    assert result["journal_entry_id"] == 77
    assert result["approval_status"] == "approved"
    assert result["approval_decided_by"] == "admin-1"
    assert result["approval_notes"] == "Voucher reviewed"
    assert captured["payload"].lines[0].debit == Decimal("500.00")
    assert captured["payload"].lines[1].credit == Decimal("500.00")
    assert audit_events[0]["action"] == "business_voucher_reviewed"


@pytest.mark.asyncio
async def test_review_typed_voucher_rejects_pending_document(monkeypatch):
    vouchers = FakeCollection()
    vouchers.docs = [
        {
            "voucher_id": "v-reject-1",
            "voucher_number": "PV-1",
            "voucher_type": "payment",
            "tenant_id": "business-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "amount": "200.00",
            "entry_date": "2026-05-20",
            "debit_account_id": 30,
            "credit_account_id": 40,
            "description": "Payment to vendor",
            "reference": "PV-1",
            "status": "pending_approval",
            "approval_required": True,
            "approval_status": "pending_approval",
            "created_by": "owner-1",
            "created_at": business_service._now(),
            "updated_at": business_service._now(),
        }
    ]
    monkeypatch.setattr(business_service, "get_collection", lambda _name: vouchers)
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_k: _async_none())

    result = await business_service.review_typed_voucher(
        session=object(),
        tenant_id="business-tenant",
        app_key="mitrabooks",
        voucher_id="v-reject-1",
        reviewed_by="admin-2",
        payload=business_service.ApprovalReviewRequest(
            approve=False,
            notes="Incorrect party mapping",
            rejection_reason="Incorrect party mapping",
            accounting_entity_id="primary",
        ),
    )

    assert result["status"] == "rejected"
    assert result["approval_status"] == "rejected"
    assert result["rejection_reason"] == "Incorrect party mapping"


@pytest.mark.asyncio
async def test_list_vouchers_filters_by_status_and_approval_state(monkeypatch):
    vouchers = FakeCollection()
    vouchers.docs = [
        {
            "voucher_id": "v-1",
            "voucher_number": "RV-1",
            "voucher_type": "receipt",
            "tenant_id": "business-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "amount": "500.00",
            "entry_date": "2026-05-20",
            "status": "posted",
            "approval_status": "approved",
        },
        {
            "voucher_id": "v-2",
            "voucher_number": "PV-1",
            "voucher_type": "payment",
            "tenant_id": "business-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "amount": "125.00",
            "entry_date": "2026-05-21",
            "status": "reversed",
            "approval_status": "rejected",
        },
        {
            "voucher_id": "v-3",
            "voucher_number": "JV-1",
            "voucher_type": "journal",
            "tenant_id": "business-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "amount": "75.00",
            "entry_date": "2026-05-22",
            "status": "pending_approval",
            "approval_status": "pending_approval",
        },
    ]
    monkeypatch.setattr(business_service, "get_collection", lambda _name: vouchers)

    result = await business_service.list_vouchers(
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        status="pending_approval",
        approval_status="pending_approval",
        limit=20,
    )

    assert result["total"] == 1
    assert result["items"][0]["voucher_id"] == "v-3"
    assert result["items"][0]["status"] == "pending_approval"
    assert result["items"][0]["approval_status"] == "pending_approval"


@pytest.mark.asyncio
async def test_typed_voucher_reuses_idempotent_business_record(monkeypatch):
    vouchers = FakeCollection()
    monkeypatch.setattr(business_service, "get_collection", lambda _name: vouchers)

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
    assert first["status"] == "pending_approval"
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

    created_doc = await business_service.create_sales_invoice(
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

    result = await business_service.review_sales_invoice(
        session=object(),
        tenant_id="business-tenant",
        app_key="mitrabooks",
        invoice_id=created_doc["invoice_id"],
        reviewed_by="admin-1",
        payload=business_service.ApprovalReviewRequest(approve=True, notes="ok", accounting_entity_id="primary"),
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

    assert created_doc["status"] == "pending_approval"
    assert created_doc["approval_status"] == "pending_approval"
    assert result["status"] == "posted"
    assert result["journal_entry_id"] == 501
    assert result["invoice_number"].startswith("INV-2026-2027-")
    assert result["taxable_total"] == "6000.00"
    assert result["cgst_total"] == "540.00"
    assert result["sgst_total"] == "540.00"
    assert result["igst_total"] == "0.00"
    assert result["invoice_total"] == "7080.00"
    assert result["approval_required"] is True
    assert result["approval_status"] == "approved"
    assert result["customer_name"] == "Acme Traders"
    assert audit_events[-1]["action"] == "business_sales_invoice_reviewed"


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

    created_doc = await business_service.create_sales_invoice(
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

    result = await business_service.review_sales_invoice(
        session=object(),
        tenant_id="business-tenant",
        app_key="mitrabooks",
        invoice_id=created_doc["invoice_id"],
        reviewed_by="admin-1",
        payload=business_service.ApprovalReviewRequest(approve=True, accounting_entity_id="primary"),
    )

    gst_lines = {line.account_id: line.credit for line in captured["payload"].lines[2:]}
    assert gst_lines == {_INVOICE_ACCOUNT_IDS["22003"]: Decimal("180.00")}
    assert result["igst_total"] == "180.00"
    assert result["cgst_total"] == "0.00"
    assert result["invoice_total"] == "1180.00"


@pytest.mark.asyncio
async def test_sales_invoice_deep_e2e_posts_reports_exports_and_reverses(async_session, monkeypatch):
    store = FakeCollection()
    _seed_customer(store)
    audit_events = []
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "log_audit_event", lambda **kwargs: audit_events.append(kwargs))
    monkeypatch.setattr("app.db.mongo.get_collection", lambda _name: store)

    async def fake_list_open_items(**_kwargs):
        return {"items": []}

    monkeypatch.setattr("app.modules.business.allocation_service.list_open_items", fake_list_open_items)

    created_doc = await business_service.create_sales_invoice(
        async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        created_by="owner-1",
        payload=SalesInvoiceCreateRequest(
            customer_party_id="cust-1",
            invoice_date=date(2026, 6, 8),
            due_date=date(2026, 6, 30),
            income_account_code="41001",
            place_of_supply="Karnataka",
            reference="PO-SI-DEEP-1",
            line_items=[
                SalesInvoiceLineItem(
                    description="Implementation service",
                    hsn_sac="9983",
                    quantity=Decimal("1"),
                    rate=Decimal("1000"),
                    gst_rate=Decimal("18"),
                )
            ],
        ),
        idempotency_key="sales-invoice-deep-create-1",
    )
    posted = await business_service.review_sales_invoice(
        session=async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        invoice_id=created_doc["invoice_id"],
        reviewed_by="admin-1",
        payload=business_service.ApprovalReviewRequest(approve=True, notes="Sales invoice deep E2E", accounting_entity_id="primary"),
    )

    assert posted["status"] == "posted"
    assert posted["journal_entry_id"]
    assert posted["invoice_total"] == "1180.00"
    assert posted["taxable_total"] == "1000.00"
    assert posted["cgst_total"] == "90.00"
    assert posted["sgst_total"] == "90.00"

    journal_detail = await get_journal_voucher_detail(
        async_session,
        app_key="mitrabooks",
        tenant_id="business-tenant",
        accounting_entity_id="primary",
        journal_id=posted["journal_entry_id"],
    )
    assert journal_detail["reference"] == posted["invoice_number"]
    assert journal_detail["total_debit"] == 1180.0
    assert journal_detail["total_credit"] == 1180.0
    line_by_code = {line["account_code"]: line for line in journal_detail["lines"]}
    assert line_by_code["12001"]["debit"] == 1180.0
    assert line_by_code["41001"]["credit"] == 1000.0
    assert line_by_code["22001"]["credit"] == 90.0
    assert line_by_code["22002"]["credit"] == 90.0

    trial_lines, trial_debit, trial_credit = await get_trial_balance(
        async_session,
        tenant_id="business-tenant",
        as_of=date(2026, 6, 30),
        app_key="mitrabooks",
        accounting_entity_id="primary",
    )
    assert trial_debit == trial_credit == Decimal("1180.00")
    trial_by_code = {line["account_code"]: line for line in trial_lines}
    assert trial_by_code["12001"]["net_balance"] == Decimal("1180.00")
    assert trial_by_code["41001"]["net_balance"] == Decimal("-1000.00")

    statement = await build_party_statement(
        async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        party_id="cust-1",
        kind="receivable",
        from_date=date(2026, 6, 1),
        to_date=date(2026, 6, 30),
    )
    assert statement["party"]["party_id"] == "cust-1"
    assert statement["closing_balance"] == "1180.00"
    assert statement["transactions"][0]["reference"] == posted["invoice_number"]
    assert statement["transactions"][0]["document_type"] == "Invoice"

    pdf_bytes = build_sales_invoice_pdf(posted, {})
    assert pdf_bytes.startswith(b"%PDF")
    export_response = report_export.export_report(
        "csv",
        title="Statement of Account",
        columns=[{"key": "reference", "label": "Reference"}, {"key": "balance", "label": "Balance", "numeric": True}],
        rows=statement["transactions"],
        filename_base="statement_cust_1",
        org_name=statement["business_name"],
    )
    assert export_response.media_type == "text/csv"

    cancelled = await business_service.cancel_sales_invoice(
        async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        invoice_id=posted["invoice_id"],
        created_by="admin-1",
        payload=SalesInvoiceCancelRequest(
            reason="Sales invoice deep E2E reversal",
            cancel_date=date(2026, 6, 8),
        ),
        idempotency_key="sales-invoice-deep-cancel-1",
    )
    assert cancelled["status"] == "cancelled"
    assert cancelled["reversal_journal_entry_id"]

    reversal_detail = await get_journal_voucher_detail(
        async_session,
        app_key="mitrabooks",
        tenant_id="business-tenant",
        accounting_entity_id="primary",
        journal_id=cancelled["reversal_journal_entry_id"],
    )
    assert reversal_detail["reversal_of_journal_id"] == posted["journal_entry_id"]
    reversal_by_code = {line["account_code"]: line for line in reversal_detail["lines"]}
    assert reversal_by_code["12001"]["credit"] == 1180.0
    assert reversal_by_code["41001"]["debit"] == 1000.0
    assert reversal_by_code["22001"]["debit"] == 90.0
    assert reversal_by_code["22002"]["debit"] == 90.0

    outstanding = await get_party_outstanding(
        async_session,
        tenant_id="business-tenant",
        party_id="cust-1",
        as_of=date(2026, 6, 30),
        app_key="mitrabooks",
        accounting_entity_id="primary",
    )
    assert outstanding["receivable"] == Decimal("0.00")

    post_reversal_statement = await build_party_statement(
        async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        party_id="cust-1",
        kind="receivable",
        from_date=date(2026, 6, 1),
        to_date=date(2026, 6, 30),
    )
    assert post_reversal_statement["closing_balance"] == "0.00"
    assert [row["document_type"] for row in post_reversal_statement["transactions"]] == ["Invoice", "journal_reversal"]

    with pytest.raises(AccountingNotFoundError):
        await get_journal_voucher_detail(
            async_session,
            app_key="mitrabooks",
            tenant_id="other-tenant",
            accounting_entity_id="primary",
            journal_id=posted["journal_entry_id"],
        )
    assert audit_events[-1]["action"] == "business_sales_invoice_cancelled"


@pytest.mark.asyncio
async def test_sales_invoice_approval_reverses_journal_when_status_update_fails(monkeypatch):
    store = FailingUpdateCollection(fail_on_update_after_insert=True)
    _seed_customer(store)
    captured = {}
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "initialize_default_chart_of_accounts", lambda *a, **k: _async_none())
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_k: _async_none())

    async def fake_resolve(_session, *, account_code, **_kwargs):
        return _INVOICE_ACCOUNT_IDS[account_code]

    async def fake_post_journal_entry(_session, **_kwargs):
        return SimpleNamespace(id=551), True

    async def fake_reverse_journal_entry(_session, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id=651), True

    monkeypatch.setattr(business_service, "_resolve_voucher_account_id", fake_resolve)
    monkeypatch.setattr(business_service, "post_journal_entry", fake_post_journal_entry)
    monkeypatch.setattr(business_service, "reverse_journal_entry", fake_reverse_journal_entry)

    created_doc = await business_service.create_sales_invoice(
        None,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        created_by="owner-1",
        payload=SalesInvoiceCreateRequest(
            customer_party_id="cust-1",
            invoice_date=date(2026, 6, 8),
            is_inter_state=False,
            line_items=[SalesInvoiceLineItem(description="Widget", quantity=Decimal("1"), rate=Decimal("100"), gst_rate=Decimal("18"))],
        ),
        idempotency_key="inv-comp-1",
    )

    with pytest.raises(business_service.AccountingValidationError, match="automatically reversed"):
        await business_service.review_sales_invoice(
            session=object(),
            tenant_id="business-tenant",
            app_key="mitrabooks",
            invoice_id=created_doc["invoice_id"],
            reviewed_by="admin-1",
            payload=business_service.ApprovalReviewRequest(approve=True, accounting_entity_id="primary"),
        )

    assert captured["journal_id"] == 551
    assert captured["reason"].startswith("Compensation after sales invoice approval persistence failure")
    assert captured["idempotency_key"].startswith("sales-invoice-approve-compensate:")
    assert captured["tenant_id"] == "business-tenant"
    assert captured["app_key"] == "mitrabooks"
    assert captured["accounting_entity_id"] == "primary"


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


@pytest.mark.asyncio
async def test_review_sales_invoice_updates_approval_state(monkeypatch):
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
    audit_events = []
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    result = await business_service.review_sales_invoice(
        session=None,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        invoice_id="inv-1",
        reviewed_by="admin-2",
        payload=business_service.ApprovalReviewRequest(
            approve=True,
            notes="Checked and approved",
            accounting_entity_id="primary",
        ),
    )

    assert result["approval_required"] is True
    assert result["approval_status"] == "approved"
    assert result["approval_decided_by"] == "admin-2"
    assert result["approval_notes"] == "Checked and approved"
    assert result["approval_submitted_by"] == "owner-1"
    assert audit_events[0]["action"] == "business_sales_invoice_reviewed"


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

    created_doc = await business_service.create_purchase_bill(
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

    result = await business_service.review_purchase_bill(
        session=object(),
        tenant_id="business-tenant",
        app_key="mitrabooks",
        bill_id=created_doc["bill_id"],
        reviewed_by="admin-1",
        payload=business_service.ApprovalReviewRequest(approve=True, notes="ok", accounting_entity_id="primary"),
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

    assert created_doc["status"] == "pending_approval"
    assert created_doc["approval_status"] == "pending_approval"
    assert result["status"] == "posted"
    assert result["journal_entry_id"] == 801
    assert result["approval_required"] is True
    assert result["approval_status"] == "approved"
    assert result["bill_number"] == "SUP-2026-77"
    assert result["vendor_name"] == "Bharat Supplies"
    assert result["igst_total"] == "0.00"
    assert result["bill_total"] == "1180.00"
    assert audit_events[-1]["action"] == "business_purchase_bill_reviewed"


@pytest.mark.asyncio
async def test_purchase_bill_deep_e2e_posts_reports_payment_itc_and_reverses(async_session, monkeypatch):
    store = FakeCollection()
    _seed_vendor(store)
    audit_events = []
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "log_audit_event", lambda **kwargs: audit_events.append(kwargs))
    monkeypatch.setattr("app.db.mongo.get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "is_gst_period_locked", lambda **_kwargs: _async_none())

    async def fake_list_open_items(**_kwargs):
        return {"items": []}

    monkeypatch.setattr("app.modules.business.allocation_service.list_open_items", fake_list_open_items)

    created_doc = await business_service.create_purchase_bill(
        async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        created_by="owner-1",
        payload=PurchaseBillCreateRequest(
            vendor_party_id="vend-1",
            bill_number="SUP-DEEP-2026-001",
            bill_date=date(2026, 1, 1),
            due_date=date(2026, 1, 31),
            expense_account_code="51001",
            place_of_supply="Karnataka",
            line_items=[
                PurchaseBillLineItem(
                    description="Raw material purchase",
                    hsn_sac="4820",
                    quantity=Decimal("1"),
                    rate=Decimal("1000"),
                    gst_rate=Decimal("18"),
                )
            ],
        ),
        idempotency_key="purchase-bill-deep-create-1",
    )
    posted = await business_service.review_purchase_bill(
        session=async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        bill_id=created_doc["bill_id"],
        reviewed_by="admin-1",
        payload=business_service.ApprovalReviewRequest(approve=True, notes="Purchase bill deep E2E", accounting_entity_id="primary"),
    )

    assert posted["status"] == "posted"
    assert posted["journal_entry_id"]
    assert posted["bill_total"] == "1180.00"
    assert posted["taxable_total"] == "1000.00"
    assert posted["cgst_total"] == "90.00"
    assert posted["sgst_total"] == "90.00"
    assert posted["payment_status"] == "unpaid"

    journal_detail = await get_journal_voucher_detail(
        async_session,
        app_key="mitrabooks",
        tenant_id="business-tenant",
        accounting_entity_id="primary",
        journal_id=posted["journal_entry_id"],
    )
    assert journal_detail["reference"] == "SUP-DEEP-2026-001"
    assert journal_detail["total_debit"] == 1180.0
    assert journal_detail["total_credit"] == 1180.0
    line_by_code = {line["account_code"]: line for line in journal_detail["lines"]}
    assert line_by_code["51001"]["debit"] == 1000.0
    assert line_by_code["14001"]["debit"] == 90.0
    assert line_by_code["14002"]["debit"] == 90.0
    assert line_by_code["21001"]["credit"] == 1180.0

    trial_lines, trial_debit, trial_credit = await get_trial_balance(
        async_session,
        tenant_id="business-tenant",
        as_of=date(2026, 1, 31),
        app_key="mitrabooks",
        accounting_entity_id="primary",
    )
    assert trial_debit == trial_credit == Decimal("1180.00")
    trial_by_code = {line["account_code"]: line for line in trial_lines}
    assert trial_by_code["51001"]["net_balance"] == Decimal("1000.00")
    assert trial_by_code["14001"]["net_balance"] == Decimal("90.00")
    assert trial_by_code["14002"]["net_balance"] == Decimal("90.00")
    assert trial_by_code["21001"]["net_balance"] == Decimal("-1180.00")

    statement = await build_party_statement(
        async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        party_id="vend-1",
        kind="payable",
        from_date=date(2026, 1, 1),
        to_date=date(2026, 1, 31),
    )
    assert statement["party"]["party_id"] == "vend-1"
    assert statement["closing_balance"] == "1180.00"
    assert statement["transactions"][0]["reference"] == "SUP-DEEP-2026-001"
    assert statement["transactions"][0]["document_type"] == "Bill"

    export_response = report_export.export_report(
        "csv",
        title="Vendor Statement",
        columns=[{"key": "reference", "label": "Reference"}, {"key": "balance", "label": "Balance", "numeric": True}],
        rows=statement["transactions"],
        filename_base="statement_vend_1",
        org_name=statement["business_name"],
    )
    assert export_response.media_type == "text/csv"

    preview = await business_service.preview_itc_reversals(
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        as_of=date(2026, 7, 1),
    )
    assert preview["count"] == 1
    assert preview["candidates"][0]["bill_id"] == posted["bill_id"]
    assert preview["candidates"][0]["itc_total"] == "180.00"

    itc_reversed = await business_service.reverse_itc_for_bill(
        async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        bill_id=posted["bill_id"],
        created_by="admin-1",
        payload=ItcReversalActionRequest(reversal_date=date(2026, 7, 1)),
        idempotency_key="purchase-bill-deep-itc-reverse-1",
    )
    assert itc_reversed["itc_reversed"] is True
    assert itc_reversed["itc_reversal_journal_entry_id"]
    assert itc_reversed["itc_interest_amount"] == "16.07"

    itc_reversal_detail = await get_journal_voucher_detail(
        async_session,
        app_key="mitrabooks",
        tenant_id="business-tenant",
        accounting_entity_id="primary",
        journal_id=itc_reversed["itc_reversal_journal_entry_id"],
    )
    itc_reversal_by_code = {line["account_code"]: line for line in itc_reversal_detail["lines"]}
    assert itc_reversal_by_code["14004"]["debit"] == 180.0
    assert itc_reversal_by_code["54006"]["debit"] == 16.07
    assert itc_reversal_by_code["14001"]["credit"] == 90.0
    assert itc_reversal_by_code["14002"]["credit"] == 90.0
    assert itc_reversal_by_code["23003"]["credit"] == 16.07

    paid = await business_service.mark_bill_payment(
        tenant_id="business-tenant",
        app_key="mitrabooks",
        bill_id=posted["bill_id"],
        created_by="admin-1",
        payload=BillPaymentUpdateRequest(
            paid_amount=Decimal("1180.00"),
            paid_date=date(2026, 7, 2),
        ),
    )
    assert paid["payment_status"] == "paid"
    assert paid["paid_amount"] == "1180.00"

    itc_reclaimed = await business_service.reclaim_itc_for_bill(
        async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        bill_id=posted["bill_id"],
        created_by="admin-1",
        payload=ItcReclaimActionRequest(reclaim_date=date(2026, 7, 2)),
        idempotency_key="purchase-bill-deep-itc-reclaim-1",
    )
    assert itc_reclaimed["itc_reclaimed"] is True
    assert itc_reclaimed["itc_reclaim_journal_entry_id"]

    itc_reclaim_detail = await get_journal_voucher_detail(
        async_session,
        app_key="mitrabooks",
        tenant_id="business-tenant",
        accounting_entity_id="primary",
        journal_id=itc_reclaimed["itc_reclaim_journal_entry_id"],
    )
    itc_reclaim_by_code = {line["account_code"]: line for line in itc_reclaim_detail["lines"]}
    assert itc_reclaim_by_code["14001"]["debit"] == 90.0
    assert itc_reclaim_by_code["14002"]["debit"] == 90.0
    assert itc_reclaim_by_code["14004"]["credit"] == 180.0

    cancelled = await business_service.cancel_purchase_bill(
        async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        bill_id=posted["bill_id"],
        created_by="admin-1",
        payload=PurchaseBillCancelRequest(
            reason="Purchase bill deep E2E reversal",
            cancel_date=date(2026, 1, 1),
        ),
        idempotency_key="purchase-bill-deep-cancel-1",
    )
    assert cancelled["status"] == "cancelled"
    assert cancelled["reversal_journal_entry_id"]

    reversal_detail = await get_journal_voucher_detail(
        async_session,
        app_key="mitrabooks",
        tenant_id="business-tenant",
        accounting_entity_id="primary",
        journal_id=cancelled["reversal_journal_entry_id"],
    )
    assert reversal_detail["reversal_of_journal_id"] == posted["journal_entry_id"]
    reversal_by_code = {line["account_code"]: line for line in reversal_detail["lines"]}
    assert reversal_by_code["51001"]["credit"] == 1000.0
    assert reversal_by_code["14001"]["credit"] == 90.0
    assert reversal_by_code["14002"]["credit"] == 90.0
    assert reversal_by_code["21001"]["debit"] == 1180.0

    outstanding = await get_party_outstanding(
        async_session,
        tenant_id="business-tenant",
        party_id="vend-1",
        as_of=date(2026, 7, 31),
        app_key="mitrabooks",
        accounting_entity_id="primary",
    )
    assert outstanding["payable"] == Decimal("0.00")

    with pytest.raises(AccountingNotFoundError):
        await get_journal_voucher_detail(
            async_session,
            app_key="mitrabooks",
            tenant_id="other-tenant",
            accounting_entity_id="primary",
            journal_id=posted["journal_entry_id"],
        )
    assert audit_events[-1]["action"] == "business_purchase_bill_cancelled"


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


@pytest.mark.asyncio
async def test_review_purchase_bill_can_reject_document(monkeypatch):
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
    audit_events = []
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    result = await business_service.review_purchase_bill(
        session=None,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        bill_id="bill-1",
        reviewed_by="admin-3",
        payload=business_service.ApprovalReviewRequest(
            approve=False,
            notes="Need vendor clarification",
            rejection_reason="Mismatch with supplier support",
            accounting_entity_id="primary",
        ),
    )

    assert result["approval_required"] is True
    assert result["approval_status"] == "rejected"
    assert result["approval_decided_by"] == "admin-3"
    assert result["approval_notes"] == "Need vendor clarification"
    assert result["rejection_reason"] == "Mismatch with supplier support"
    assert audit_events[0]["action"] == "business_purchase_bill_reviewed"


@pytest.mark.asyncio
async def test_purchase_bill_approval_reverses_journal_when_status_update_fails(monkeypatch):
    store = FailingUpdateCollection(fail_on_update_after_insert=True)
    _seed_vendor(store)
    captured = {}
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "initialize_default_chart_of_accounts", lambda *a, **k: _async_none())
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_k: _async_none())

    async def fake_resolve(_session, *, account_code, **_kwargs):
        return _INVOICE_ACCOUNT_IDS[account_code]

    async def fake_post_journal_entry(_session, **_kwargs):
        return SimpleNamespace(id=851), True

    async def fake_reverse_journal_entry(_session, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id=951), True

    monkeypatch.setattr(business_service, "_resolve_voucher_account_id", fake_resolve)
    monkeypatch.setattr(business_service, "post_journal_entry", fake_post_journal_entry)
    monkeypatch.setattr(business_service, "reverse_journal_entry", fake_reverse_journal_entry)

    created_doc = await business_service.create_purchase_bill(
        None,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        created_by="owner-1",
        payload=PurchaseBillCreateRequest(
            vendor_party_id="vend-1",
            bill_number="SUP-2026-88",
            bill_date=date(2026, 6, 8),
            is_inter_state=False,
            line_items=[PurchaseBillLineItem(description="Raw material", quantity=Decimal("1"), rate=Decimal("100"), gst_rate=Decimal("18"))],
        ),
        idempotency_key="bill-comp-1",
    )

    with pytest.raises(business_service.AccountingValidationError, match="automatically reversed"):
        await business_service.review_purchase_bill(
            session=object(),
            tenant_id="business-tenant",
            app_key="mitrabooks",
            bill_id=created_doc["bill_id"],
            reviewed_by="admin-1",
            payload=business_service.ApprovalReviewRequest(approve=True, accounting_entity_id="primary"),
        )

    assert captured["journal_id"] == 851
    assert captured["reason"].startswith("Compensation after purchase bill approval persistence failure")
    assert captured["tenant_id"] == "business-tenant"
    assert captured["app_key"] == "mitrabooks"
    assert captured["accounting_entity_id"] == "primary"


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

    created_doc = await business_service.create_credit_note(
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
    result = await business_service.review_credit_note(
        session=object(),
        tenant_id="business-tenant",
        app_key="mitrabooks",
        credit_note_id=created_doc["credit_note_id"],
        reviewed_by="admin-1",
        payload=business_service.ApprovalReviewRequest(approve=True, accounting_entity_id="primary"),
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
    assert created_doc["status"] == "pending_approval"
    assert created_doc["approval_status"] == "pending_approval"
    assert result["status"] == "posted"
    assert result["approval_status"] == "approved"
    assert audit_events[-1]["action"] == "business_credit_note_reviewed"


@pytest.mark.asyncio
async def test_credit_note_deep_e2e_posts_reports_exports_and_reverses(async_session, monkeypatch):
    store = FakeCollection()
    _seed_customer(store)
    audit_events = []
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "log_audit_event", lambda **kwargs: audit_events.append(kwargs))
    monkeypatch.setattr("app.db.mongo.get_collection", lambda _name: store)

    async def fake_list_open_items(**_kwargs):
        return {"items": []}

    monkeypatch.setattr("app.modules.business.allocation_service.list_open_items", fake_list_open_items)

    invoice_doc = await business_service.create_sales_invoice(
        async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        created_by="owner-1",
        payload=SalesInvoiceCreateRequest(
            customer_party_id="cust-1",
            invoice_date=date(2026, 6, 8),
            due_date=date(2026, 6, 30),
            income_account_code="41001",
            place_of_supply="Karnataka",
            reference="PO-CN-DEEP-1",
            line_items=[
                SalesInvoiceLineItem(
                    description="Implementation service",
                    hsn_sac="9983",
                    quantity=Decimal("1"),
                    rate=Decimal("1000"),
                    gst_rate=Decimal("18"),
                )
            ],
        ),
        idempotency_key="credit-note-deep-invoice-create-1",
    )
    invoice = await business_service.review_sales_invoice(
        session=async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        invoice_id=invoice_doc["invoice_id"],
        reviewed_by="admin-1",
        payload=business_service.ApprovalReviewRequest(approve=True, notes="Credit note source invoice", accounting_entity_id="primary"),
    )

    created_doc = await business_service.create_credit_note(
        async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        created_by="owner-1",
        payload=CreditNoteCreateRequest(
            customer_party_id="cust-1",
            note_date=date(2026, 6, 20),
            original_invoice_id=invoice["invoice_id"],
            original_invoice_number=invoice["invoice_number"],
            reason="sales_return",
            income_account_code="41001",
            place_of_supply="Karnataka",
            line_items=[
                CreditNoteLineItem(
                    description="Returned implementation service",
                    hsn_sac="9983",
                    quantity=Decimal("1"),
                    rate=Decimal("1000"),
                    gst_rate=Decimal("18"),
                )
            ],
        ),
        idempotency_key="credit-note-deep-create-1",
    )
    posted = await business_service.review_credit_note(
        session=async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        credit_note_id=created_doc["credit_note_id"],
        reviewed_by="admin-1",
        payload=business_service.ApprovalReviewRequest(approve=True, notes="Credit note deep E2E", accounting_entity_id="primary"),
    )

    assert posted["status"] == "posted"
    assert posted["journal_entry_id"]
    assert posted["original_invoice_id"] == invoice["invoice_id"]
    assert posted["original_invoice_number"] == invoice["invoice_number"]
    assert posted["note_total"] == "1180.00"
    assert posted["taxable_total"] == "1000.00"
    assert posted["cgst_total"] == "90.00"
    assert posted["sgst_total"] == "90.00"

    journal_detail = await get_journal_voucher_detail(
        async_session,
        app_key="mitrabooks",
        tenant_id="business-tenant",
        accounting_entity_id="primary",
        journal_id=posted["journal_entry_id"],
    )
    assert journal_detail["reference"] == posted["credit_note_number"]
    assert journal_detail["total_debit"] == 1180.0
    assert journal_detail["total_credit"] == 1180.0
    line_by_code = {line["account_code"]: line for line in journal_detail["lines"]}
    assert line_by_code["41001"]["debit"] == 1000.0
    assert line_by_code["22001"]["debit"] == 90.0
    assert line_by_code["22002"]["debit"] == 90.0
    assert line_by_code["12001"]["credit"] == 1180.0

    trial_lines, trial_debit, trial_credit = await get_trial_balance(
        async_session,
        tenant_id="business-tenant",
        as_of=date(2026, 6, 30),
        app_key="mitrabooks",
        accounting_entity_id="primary",
    )
    assert trial_debit == trial_credit == Decimal("2360.00")
    trial_by_code = {line["account_code"]: line for line in trial_lines}
    assert trial_by_code["12001"]["net_balance"] == Decimal("0.00")
    assert trial_by_code["41001"]["net_balance"] == Decimal("0.00")
    assert trial_by_code["22001"]["net_balance"] == Decimal("0.00")
    assert trial_by_code["22002"]["net_balance"] == Decimal("0.00")

    statement = await build_party_statement(
        async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        party_id="cust-1",
        kind="receivable",
        from_date=date(2026, 6, 1),
        to_date=date(2026, 6, 30),
    )
    assert statement["party"]["party_id"] == "cust-1"
    assert statement["closing_balance"] == "0.00"
    assert [row["document_type"] for row in statement["transactions"]] == ["Invoice", "Credit Note"]
    assert statement["transactions"][1]["reference"] == posted["credit_note_number"]

    export_response = report_export.export_report(
        "csv",
        title="Credit Note Statement",
        columns=[{"key": "reference", "label": "Reference"}, {"key": "balance", "label": "Balance", "numeric": True}],
        rows=statement["transactions"],
        filename_base="statement_credit_note_cust_1",
        org_name=statement["business_name"],
    )
    assert export_response.media_type == "text/csv"

    cancelled = await business_service.cancel_credit_note(
        async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        credit_note_id=posted["credit_note_id"],
        created_by="admin-1",
        payload=CreditNoteCancelRequest(
            reason="Credit note deep E2E reversal",
            cancel_date=date(2026, 6, 20),
        ),
        idempotency_key="credit-note-deep-cancel-1",
    )
    assert cancelled["status"] == "cancelled"
    assert cancelled["reversal_journal_entry_id"]

    reversal_detail = await get_journal_voucher_detail(
        async_session,
        app_key="mitrabooks",
        tenant_id="business-tenant",
        accounting_entity_id="primary",
        journal_id=cancelled["reversal_journal_entry_id"],
    )
    assert reversal_detail["reversal_of_journal_id"] == posted["journal_entry_id"]
    reversal_by_code = {line["account_code"]: line for line in reversal_detail["lines"]}
    assert reversal_by_code["41001"]["credit"] == 1000.0
    assert reversal_by_code["22001"]["credit"] == 90.0
    assert reversal_by_code["22002"]["credit"] == 90.0
    assert reversal_by_code["12001"]["debit"] == 1180.0

    outstanding = await get_party_outstanding(
        async_session,
        tenant_id="business-tenant",
        party_id="cust-1",
        as_of=date(2026, 6, 30),
        app_key="mitrabooks",
        accounting_entity_id="primary",
    )
    assert outstanding["receivable"] == Decimal("1180.00")

    post_reversal_statement = await build_party_statement(
        async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        party_id="cust-1",
        kind="receivable",
        from_date=date(2026, 6, 1),
        to_date=date(2026, 6, 30),
    )
    assert post_reversal_statement["closing_balance"] == "1180.00"
    assert [row["document_type"] for row in post_reversal_statement["transactions"]] == ["Invoice", "Credit Note", "journal_reversal"]

    with pytest.raises(AccountingNotFoundError):
        await get_journal_voucher_detail(
            async_session,
            app_key="mitrabooks",
            tenant_id="other-tenant",
            accounting_entity_id="primary",
            journal_id=posted["journal_entry_id"],
        )
    assert audit_events[-1]["action"] == "business_credit_note_cancelled"


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
async def test_credit_note_reverses_journal_when_status_update_fails(monkeypatch):
    store = FailingUpdateCollection(fail_on_update_after_insert=True)
    _seed_customer(store)
    captured = {}
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "initialize_default_chart_of_accounts", lambda *a, **k: _async_none())
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_k: _async_none())

    async def fake_resolve(_session, *, account_code, **_kwargs):
        return _INVOICE_ACCOUNT_IDS[account_code]

    async def fake_post_journal_entry(_session, **_kwargs):
        return SimpleNamespace(id=1051), True

    async def fake_reverse_journal_entry(_session, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id=2051), True

    monkeypatch.setattr(business_service, "_resolve_voucher_account_id", fake_resolve)
    monkeypatch.setattr(business_service, "post_journal_entry", fake_post_journal_entry)
    monkeypatch.setattr(business_service, "reverse_journal_entry", fake_reverse_journal_entry)

    created_doc = await business_service.create_credit_note(
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
            line_items=[CreditNoteLineItem(description="Returned widget", quantity=Decimal("1"), rate=Decimal("100"), gst_rate=Decimal("18"))],
        ),
        idempotency_key="cn-comp-1",
    )

    with pytest.raises(business_service.AccountingValidationError, match="automatically reversed"):
        await business_service.review_credit_note(
            session=object(),
            tenant_id="business-tenant",
            app_key="mitrabooks",
            credit_note_id=created_doc["credit_note_id"],
            reviewed_by="admin-1",
            payload=business_service.ApprovalReviewRequest(approve=True, accounting_entity_id="primary"),
        )

    assert captured["journal_id"] == 1051
    assert captured["reason"].startswith("Compensation after credit note approval persistence failure")
    assert captured["tenant_id"] == "business-tenant"
    assert captured["app_key"] == "mitrabooks"
    assert captured["accounting_entity_id"] == "primary"


@pytest.mark.asyncio
async def test_cancel_credit_note_posts_reversal(monkeypatch):
    store = FakeCollection()
    store.docs.append({
        "tenant_id": "business-tenant",
        "app_key": "mitrabooks",
        "accounting_entity_id": "primary",
        "credit_note_id": "cn-1",
        "credit_note_number": "CN-2026-2027-000001",
        "customer_party_id": "cust-1",
        "customer_name": "Acme Customer",
        "note_date": date(2026, 6, 20),
        "original_invoice_number": "INV-2026-2027-000001",
        "reason": "sales_return",
        "is_inter_state": False,
        "income_account_code": "41001",
        "line_items": [],
        "taxable_total": Decimal("1000.00"),
        "cgst_total": Decimal("90.00"),
        "sgst_total": Decimal("90.00"),
        "igst_total": Decimal("0.00"),
        "gst_total": Decimal("180.00"),
        "note_total": Decimal("1180.00"),
        "status": "posted",
        "journal_entry_id": 1001,
        "created_by": "owner-1",
        "created_at": "2026-06-20T00:00:00Z",
        "updated_at": "2026-06-20T00:00:00Z",
    })
    captured = {}
    audit_events = []
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "_validate_reversal_period", lambda **_k: _async_none())

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    async def fake_reverse_journal_entry(_session, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id=2002), True

    monkeypatch.setattr(business_service, "reverse_journal_entry", fake_reverse_journal_entry)

    result = await business_service.cancel_credit_note(
        None,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        credit_note_id="cn-1",
        created_by="owner-1",
        payload=CreditNoteCancelRequest(cancel_date=date(2026, 6, 21), reason="Customer return confirmed"),
        idempotency_key="cn-cancel-1",
    )

    assert captured["journal_id"] == 1001
    assert captured["reversal_date"] == date(2026, 6, 21)
    assert captured["reason"] == "Customer return confirmed"
    assert captured["idempotency_key"] == "cn-cancel-1"
    assert result["status"] == "cancelled"
    assert result["reversal_journal_entry_id"] == 2002
    assert result["cancel_reason"] == "Customer return confirmed"
    assert store.docs[0]["status"] == "cancelled"
    assert audit_events[0]["action"] == "business_credit_note_cancelled"


@pytest.mark.asyncio
async def test_review_credit_note_can_reject_document(monkeypatch):
    store = FakeCollection()
    store.docs.append({
        "tenant_id": "business-tenant",
        "app_key": "mitrabooks",
        "accounting_entity_id": "primary",
        "credit_note_id": "cn-1",
        "credit_note_number": "CN-2026-2027-000001",
        "customer_party_id": "cust-1",
        "customer_name": "Acme Customer",
        "note_date": date(2026, 6, 20),
        "reason": "sales_return",
        "note_total": Decimal("1180.00"),
        "status": "pending_approval",
        "created_by": "owner-1",
        "created_at": business_service._now(),
        "updated_at": business_service._now(),
    })
    audit_events = []
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    result = await business_service.review_credit_note(
        session=None,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        credit_note_id="cn-1",
        reviewed_by="admin-4",
        payload=business_service.ApprovalReviewRequest(
            approve=False,
            notes="Support mismatch",
            rejection_reason="Return support incomplete",
            accounting_entity_id="primary",
        ),
    )

    assert result["approval_required"] is True
    assert result["approval_status"] == "rejected"
    assert result["approval_decided_by"] == "admin-4"
    assert result["rejection_reason"] == "Return support incomplete"
    assert audit_events[0]["action"] == "business_credit_note_reviewed"


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

    created_doc = await business_service.create_debit_note(
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
    result = await business_service.review_debit_note(
        session=object(),
        tenant_id="business-tenant",
        app_key="mitrabooks",
        debit_note_id=created_doc["debit_note_id"],
        reviewed_by="admin-1",
        payload=business_service.ApprovalReviewRequest(approve=True, accounting_entity_id="primary"),
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
    assert created_doc["status"] == "pending_approval"
    assert created_doc["approval_status"] == "pending_approval"
    assert result["status"] == "posted"
    assert result["approval_required"] is True
    assert result["approval_status"] == "approved"
    assert audit_events[-1]["action"] == "business_debit_note_reviewed"


@pytest.mark.asyncio
async def test_debit_note_deep_e2e_posts_reports_exports_and_reverses(async_session, monkeypatch):
    store = FakeCollection()
    _seed_vendor(store)
    audit_events = []
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "log_audit_event", lambda **kwargs: audit_events.append(kwargs))
    monkeypatch.setattr("app.db.mongo.get_collection", lambda _name: store)

    async def fake_list_open_items(**_kwargs):
        return {"items": []}

    monkeypatch.setattr("app.modules.business.allocation_service.list_open_items", fake_list_open_items)

    bill_doc = await business_service.create_purchase_bill(
        async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        created_by="owner-1",
        payload=PurchaseBillCreateRequest(
            vendor_party_id="vend-1",
            bill_number="SUP-DN-DEEP-2026-001",
            bill_date=date(2026, 6, 8),
            due_date=date(2026, 6, 30),
            expense_account_code="51001",
            place_of_supply="Karnataka",
            line_items=[
                PurchaseBillLineItem(
                    description="Raw material purchase",
                    hsn_sac="4820",
                    quantity=Decimal("1"),
                    rate=Decimal("1000"),
                    gst_rate=Decimal("18"),
                )
            ],
        ),
        idempotency_key="debit-note-deep-bill-create-1",
    )
    bill = await business_service.review_purchase_bill(
        session=async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        bill_id=bill_doc["bill_id"],
        reviewed_by="admin-1",
        payload=business_service.ApprovalReviewRequest(approve=True, notes="Debit note source bill", accounting_entity_id="primary"),
    )

    created_doc = await business_service.create_debit_note(
        async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        created_by="owner-1",
        payload=DebitNoteCreateRequest(
            vendor_party_id="vend-1",
            note_date=date(2026, 6, 20),
            original_bill_id=bill["bill_id"],
            original_bill_number=bill["bill_number"],
            reason="purchase_return",
            expense_account_code="51001",
            place_of_supply="Karnataka",
            line_items=[
                DebitNoteLineItem(
                    description="Returned raw material",
                    hsn_sac="4820",
                    quantity=Decimal("1"),
                    rate=Decimal("1000"),
                    gst_rate=Decimal("18"),
                )
            ],
        ),
        idempotency_key="debit-note-deep-create-1",
    )
    posted = await business_service.review_debit_note(
        session=async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        debit_note_id=created_doc["debit_note_id"],
        reviewed_by="admin-1",
        payload=business_service.ApprovalReviewRequest(approve=True, notes="Debit note deep E2E", accounting_entity_id="primary"),
    )

    assert posted["status"] == "posted"
    assert posted["journal_entry_id"]
    assert posted["original_bill_id"] == bill["bill_id"]
    assert posted["original_bill_number"] == bill["bill_number"]
    assert posted["note_total"] == "1180.00"
    assert posted["taxable_total"] == "1000.00"
    assert posted["cgst_total"] == "90.00"
    assert posted["sgst_total"] == "90.00"

    journal_detail = await get_journal_voucher_detail(
        async_session,
        app_key="mitrabooks",
        tenant_id="business-tenant",
        accounting_entity_id="primary",
        journal_id=posted["journal_entry_id"],
    )
    assert journal_detail["reference"] == posted["debit_note_number"]
    assert journal_detail["total_debit"] == 1180.0
    assert journal_detail["total_credit"] == 1180.0
    line_by_code = {line["account_code"]: line for line in journal_detail["lines"]}
    assert line_by_code["21001"]["debit"] == 1180.0
    assert line_by_code["51001"]["credit"] == 1000.0
    assert line_by_code["14001"]["credit"] == 90.0
    assert line_by_code["14002"]["credit"] == 90.0

    trial_lines, trial_debit, trial_credit = await get_trial_balance(
        async_session,
        tenant_id="business-tenant",
        as_of=date(2026, 6, 30),
        app_key="mitrabooks",
        accounting_entity_id="primary",
    )
    assert trial_debit == trial_credit == Decimal("2360.00")
    trial_by_code = {line["account_code"]: line for line in trial_lines}
    assert trial_by_code["21001"]["net_balance"] == Decimal("0.00")
    assert trial_by_code["51001"]["net_balance"] == Decimal("0.00")
    assert trial_by_code["14001"]["net_balance"] == Decimal("0.00")
    assert trial_by_code["14002"]["net_balance"] == Decimal("0.00")

    statement = await build_party_statement(
        async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        party_id="vend-1",
        kind="payable",
        from_date=date(2026, 6, 1),
        to_date=date(2026, 6, 30),
    )
    assert statement["party"]["party_id"] == "vend-1"
    assert statement["closing_balance"] == "0.00"
    assert [row["document_type"] for row in statement["transactions"]] == ["Bill", "Debit Note"]
    assert statement["transactions"][1]["reference"] == posted["debit_note_number"]

    export_response = report_export.export_report(
        "csv",
        title="Debit Note Vendor Statement",
        columns=[{"key": "reference", "label": "Reference"}, {"key": "balance", "label": "Balance", "numeric": True}],
        rows=statement["transactions"],
        filename_base="statement_debit_note_vend_1",
        org_name=statement["business_name"],
    )
    assert export_response.media_type == "text/csv"

    cancelled = await business_service.cancel_debit_note(
        async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        debit_note_id=posted["debit_note_id"],
        created_by="admin-1",
        payload=DebitNoteCancelRequest(
            reason="Debit note deep E2E reversal",
            cancel_date=date(2026, 6, 20),
        ),
        idempotency_key="debit-note-deep-cancel-1",
    )
    assert cancelled["status"] == "cancelled"
    assert cancelled["reversal_journal_entry_id"]

    reversal_detail = await get_journal_voucher_detail(
        async_session,
        app_key="mitrabooks",
        tenant_id="business-tenant",
        accounting_entity_id="primary",
        journal_id=cancelled["reversal_journal_entry_id"],
    )
    assert reversal_detail["reversal_of_journal_id"] == posted["journal_entry_id"]
    reversal_by_code = {line["account_code"]: line for line in reversal_detail["lines"]}
    assert reversal_by_code["21001"]["credit"] == 1180.0
    assert reversal_by_code["51001"]["debit"] == 1000.0
    assert reversal_by_code["14001"]["debit"] == 90.0
    assert reversal_by_code["14002"]["debit"] == 90.0

    outstanding = await get_party_outstanding(
        async_session,
        tenant_id="business-tenant",
        party_id="vend-1",
        as_of=date(2026, 6, 30),
        app_key="mitrabooks",
        accounting_entity_id="primary",
    )
    assert outstanding["payable"] == Decimal("1180.00")

    post_reversal_statement = await build_party_statement(
        async_session,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        party_id="vend-1",
        kind="payable",
        from_date=date(2026, 6, 1),
        to_date=date(2026, 6, 30),
    )
    assert post_reversal_statement["closing_balance"] == "1180.00"
    assert [row["document_type"] for row in post_reversal_statement["transactions"]] == ["Bill", "Debit Note", "journal_reversal"]

    with pytest.raises(AccountingNotFoundError):
        await get_journal_voucher_detail(
            async_session,
            app_key="mitrabooks",
            tenant_id="other-tenant",
            accounting_entity_id="primary",
            journal_id=posted["journal_entry_id"],
        )
    assert audit_events[-1]["action"] == "business_debit_note_cancelled"


@pytest.mark.asyncio
async def test_debit_note_reverses_journal_when_status_update_fails(monkeypatch):
    store = FailingUpdateCollection(fail_on_update_after_insert=True)
    _seed_vendor(store)
    captured = {}
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "initialize_default_chart_of_accounts", lambda *a, **k: _async_none())
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_k: _async_none())

    async def fake_resolve(_session, *, account_code, **_kwargs):
        return _INVOICE_ACCOUNT_IDS[account_code]

    async def fake_post_journal_entry(_session, **_kwargs):
        return SimpleNamespace(id=1151), True

    async def fake_reverse_journal_entry(_session, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id=2151), True

    monkeypatch.setattr(business_service, "_resolve_voucher_account_id", fake_resolve)
    monkeypatch.setattr(business_service, "post_journal_entry", fake_post_journal_entry)
    monkeypatch.setattr(business_service, "reverse_journal_entry", fake_reverse_journal_entry)

    created_doc = await business_service.create_debit_note(
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
            line_items=[DebitNoteLineItem(description="Returned material", quantity=Decimal("1"), rate=Decimal("100"), gst_rate=Decimal("18"))],
        ),
        idempotency_key="dn-comp-1",
    )

    with pytest.raises(business_service.AccountingValidationError, match="automatically reversed"):
        await business_service.review_debit_note(
            session=object(),
            tenant_id="business-tenant",
            app_key="mitrabooks",
            debit_note_id=created_doc["debit_note_id"],
            reviewed_by="admin-1",
            payload=business_service.ApprovalReviewRequest(approve=True, accounting_entity_id="primary"),
        )

    assert captured["journal_id"] == 1151
    assert captured["reason"].startswith("Compensation after debit note approval persistence failure")
    assert captured["tenant_id"] == "business-tenant"
    assert captured["app_key"] == "mitrabooks"
    assert captured["accounting_entity_id"] == "primary"


@pytest.mark.asyncio
async def test_cancel_debit_note_posts_reversal(monkeypatch):
    store = FakeCollection()
    store.docs.append({
        "tenant_id": "business-tenant",
        "app_key": "mitrabooks",
        "accounting_entity_id": "primary",
        "debit_note_id": "dn-1",
        "debit_note_number": "DN-2026-2027-000001",
        "vendor_party_id": "vend-1",
        "vendor_name": "Acme Vendor",
        "note_date": date(2026, 6, 20),
        "original_bill_number": "SUP-2026-77",
        "reason": "purchase_return",
        "is_inter_state": False,
        "expense_account_code": "51001",
        "line_items": [],
        "taxable_total": Decimal("1000.00"),
        "cgst_total": Decimal("90.00"),
        "sgst_total": Decimal("90.00"),
        "igst_total": Decimal("0.00"),
        "gst_total": Decimal("180.00"),
        "note_total": Decimal("1180.00"),
        "status": "posted",
        "journal_entry_id": 1101,
        "created_by": "owner-1",
        "created_at": "2026-06-20T00:00:00Z",
        "updated_at": "2026-06-20T00:00:00Z",
    })
    captured = {}
    audit_events = []
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "_validate_reversal_period", lambda **_k: _async_none())

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    async def fake_reverse_journal_entry(_session, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id=2102), True

    monkeypatch.setattr(business_service, "reverse_journal_entry", fake_reverse_journal_entry)

    result = await business_service.cancel_debit_note(
        None,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        debit_note_id="dn-1",
        created_by="owner-1",
        payload=DebitNoteCancelRequest(cancel_date=date(2026, 6, 21), reason="Vendor return confirmed"),
        idempotency_key="dn-cancel-1",
    )

    assert captured["journal_id"] == 1101
    assert captured["reversal_date"] == date(2026, 6, 21)
    assert captured["reason"] == "Vendor return confirmed"
    assert captured["idempotency_key"] == "dn-cancel-1"
    assert result["status"] == "cancelled"
    assert result["reversal_journal_entry_id"] == 2102
    assert result["cancel_reason"] == "Vendor return confirmed"
    assert store.docs[0]["status"] == "cancelled"
    assert audit_events[0]["action"] == "business_debit_note_cancelled"


@pytest.mark.asyncio
async def test_review_debit_note_updates_approval_state(monkeypatch):
    store = FakeCollection()
    store.docs.append({
        "tenant_id": "business-tenant",
        "app_key": "mitrabooks",
        "accounting_entity_id": "primary",
        "debit_note_id": "dn-1",
        "debit_note_number": "DN-2026-2027-000001",
        "vendor_party_id": "vend-1",
        "vendor_name": "Acme Vendor",
        "note_date": date(2026, 6, 20),
        "reason": "purchase_return",
        "note_total": Decimal("1180.00"),
        "status": "posted",
        "journal_entry_id": 1101,
        "created_by": "owner-1",
        "created_at": business_service._now(),
        "updated_at": business_service._now(),
    })
    audit_events = []
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    result = await business_service.review_debit_note(
        session=None,
        tenant_id="business-tenant",
        app_key="mitrabooks",
        debit_note_id="dn-1",
        reviewed_by="admin-5",
        payload=business_service.ApprovalReviewRequest(
            approve=True,
            notes="Debit note approved",
            accounting_entity_id="primary",
        ),
    )

    assert result["approval_required"] is True
    assert result["approval_status"] == "approved"
    assert result["approval_decided_by"] == "admin-5"
    assert result["approval_notes"] == "Debit note approved"
    assert audit_events[0]["action"] == "business_debit_note_reviewed"


@pytest.mark.asyncio
async def test_approval_queue_aggregates_unreviewed_documents(monkeypatch):
    vouchers = FakeCollection()
    vouchers.docs = [{
        "voucher_id": "v-1", "voucher_number": "RV-1", "voucher_type": "receipt",
        "tenant_id": "business-tenant", "app_key": "mitrabooks", "accounting_entity_id": "primary",
        "amount": "500.00", "entry_date": "2026-05-20", "status": "pending_approval",
        "approval_status": "pending_approval", "approval_required": True, "created_by": "owner-1",
        "created_at": business_service._now(), "updated_at": business_service._now(),
    }, {
        "voucher_id": "v-legacy", "voucher_number": "JV-LEGACY", "voucher_type": "journal",
        "tenant_id": "business-tenant", "app_key": "mitrabooks", "accounting_entity_id": "primary",
        "amount": "50.00", "entry_date": "2026-05-18", "status": "posted",
        "journal_entry_id": 222, "approval_required": False, "created_by": "owner-legacy",
        "created_at": business_service._now(), "updated_at": business_service._now(),
    }]
    invoices = FakeCollection()
    invoices.docs = [{
        "invoice_id": "inv-1", "invoice_number": "INV-1",
        "tenant_id": "business-tenant", "app_key": "mitrabooks", "accounting_entity_id": "primary",
        "customer_name": "Acme", "invoice_date": "2026-06-08", "invoice_total": "1180.00",
        "status": "posted", "journal_entry_id": 501, "approval_status": "approved", "approval_required": True,
        "created_by": "owner-1", "created_at": business_service._now(), "updated_at": business_service._now(),
    }]
    bills = FakeCollection()
    bills.docs = [{
        "bill_id": "bill-1", "bill_number": "BILL-1",
        "tenant_id": "business-tenant", "app_key": "mitrabooks", "accounting_entity_id": "primary",
        "vendor_name": "Vendor", "bill_date": "2026-06-08", "bill_total": "900.00",
        "status": "posted", "journal_entry_id": 801, "approval_status": "rejected", "approval_required": True,
        "created_by": "owner-2", "created_at": business_service._now(), "updated_at": business_service._now(),
    }]
    credit_notes = FakeCollection()
    credit_notes.docs = [{
        "credit_note_id": "cn-1", "credit_note_number": "CN-1",
        "tenant_id": "business-tenant", "app_key": "mitrabooks", "accounting_entity_id": "primary",
        "customer_name": "Acme", "note_date": "2026-06-20", "note_total": "200.00",
        "status": "pending_approval", "approval_status": "pending_approval", "approval_required": True,
        "created_by": "owner-3", "created_at": business_service._now(), "updated_at": business_service._now(),
    }]
    debit_notes = FakeCollection()
    debit_notes.docs = [{
        "debit_note_id": "dn-1", "debit_note_number": "DN-1",
        "tenant_id": "business-tenant", "app_key": "mitrabooks", "accounting_entity_id": "primary",
        "vendor_name": "Vendor", "note_date": "2026-06-21", "note_total": "150.00",
        "status": "pending_approval", "approval_status": "pending_approval", "approval_required": True,
        "created_by": "owner-4", "created_at": business_service._now(), "updated_at": business_service._now(),
    }, {
        "debit_note_id": "dn-2", "debit_note_number": "DN-2",
        "tenant_id": "business-tenant", "app_key": "mitrabooks", "accounting_entity_id": "primary",
        "vendor_name": "Vendor", "note_date": "2026-06-22", "note_total": "75.00",
        "status": "draft", "approval_status": "not_submitted", "approval_required": True,
        "created_by": "owner-5", "created_at": business_service._now(), "updated_at": business_service._now(),
    }]

    def fake_get_collection(name):
        return {
            business_service.VOUCHERS_COLLECTION: vouchers,
            business_service.SALES_INVOICES_COLLECTION: invoices,
            business_service.PURCHASE_BILLS_COLLECTION: bills,
            business_service.CREDIT_NOTES_COLLECTION: credit_notes,
            business_service.DEBIT_NOTES_COLLECTION: debit_notes,
        }[name]

    monkeypatch.setattr(business_service, "get_collection", fake_get_collection)

    result = await business_service.list_documents_for_approval_queue(
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        include_reviewed=False,
        limit=20,
    )

    types = {item["document_type"] for item in result["items"]}
    assert "sales_invoice" not in types
    assert {"voucher", "purchase_bill", "credit_note", "debit_note"} <= types
    assert any(
        item["document_type"] == "credit_note" and item["status"] == "pending_approval"
        for item in result["items"]
    )
    assert any(
        item["document_type"] == "debit_note" and item["status"] == "pending_approval"
        for item in result["items"]
    )
    assert all(item["status"] != "draft" for item in result["items"])
    assert all(item["approval_status"] != "approved" for item in result["items"])
    assert all(item["document_number"] != "JV-LEGACY" for item in result["items"])


@pytest.mark.asyncio
async def test_approval_queue_supports_voucher_only_filters(monkeypatch):
    vouchers = FakeCollection()
    vouchers.docs = [{
        "voucher_id": "v-1", "voucher_number": "RV-1", "voucher_type": "receipt",
        "tenant_id": "business-tenant", "app_key": "mitrabooks", "accounting_entity_id": "primary",
        "amount": "500.00", "entry_date": "2026-05-20", "status": "pending_approval",
        "approval_status": "pending_approval", "approval_required": True, "created_by": "owner-1",
        "created_at": business_service._now(), "updated_at": business_service._now(),
    }, {
        "voucher_id": "v-2", "voucher_number": "PV-2", "voucher_type": "payment",
        "tenant_id": "business-tenant", "app_key": "mitrabooks", "accounting_entity_id": "primary",
        "amount": "600.00", "entry_date": "2026-05-21", "status": "posted",
        "approval_status": "approved", "approval_required": True, "journal_entry_id": 900,
        "created_by": "owner-2", "created_at": business_service._now(), "updated_at": business_service._now(),
    }]

    def fake_get_collection(name):
        return {
            business_service.VOUCHERS_COLLECTION: vouchers,
            business_service.SALES_INVOICES_COLLECTION: FakeCollection(),
            business_service.PURCHASE_BILLS_COLLECTION: FakeCollection(),
            business_service.CREDIT_NOTES_COLLECTION: FakeCollection(),
            business_service.DEBIT_NOTES_COLLECTION: FakeCollection(),
        }[name]

    monkeypatch.setattr(business_service, "get_collection", fake_get_collection)

    result = await business_service.list_documents_for_approval_queue(
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        document_type="voucher",
        status="pending_approval",
        approval_status="pending_approval",
        include_reviewed=True,
        limit=20,
    )

    assert result["total"] == 1
    assert result["items"][0]["document_type"] == "voucher"
    assert result["items"][0]["document_number"] == "RV-1"
    assert result["items"][0]["status"] == "pending_approval"
    assert result["items"][0]["approval_status"] == "pending_approval"


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


@pytest.mark.asyncio
async def test_gst_settlement_reverses_journal_and_unlocks_period_when_persistence_fails(monkeypatch):
    from app.modules.business.schemas import GstSettlementCreateRequest

    settlements = AlwaysFailUpdateCollection()
    locks = FakeCollection()
    captured = {}

    def fake_get_collection(name):
        if name == business_service.GST_SETTLEMENTS_COLLECTION:
            return settlements
        if name == business_service.GST_PERIOD_LOCKS_COLLECTION:
            return locks
        return FakeCollection()

    monkeypatch.setattr(business_service, "get_collection", fake_get_collection)
    monkeypatch.setattr(business_service, "initialize_default_chart_of_accounts", lambda *a, **k: _async_none())
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_k: _async_none())

    async def fake_balances(session, **_kwargs):
        return {
            "output": {"igst": Decimal("100"), "cgst": Decimal("500"), "sgst": Decimal("500")},
            "credit": {"igst": Decimal("600"), "cgst": Decimal("200"), "sgst": Decimal("100")},
        }

    async def fake_resolve(_session, *, account_code, **_kwargs):
        return _INVOICE_ACCOUNT_IDS[account_code]

    async def fake_post_journal_entry(_session, **_kwargs):
        return SimpleNamespace(id=1251), True

    async def fake_reverse_journal_entry(_session, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id=2251), True

    monkeypatch.setattr(business_service, "_gst_period_balances", fake_balances)
    monkeypatch.setattr(business_service, "_resolve_voucher_account_id", fake_resolve)
    monkeypatch.setattr(business_service, "post_journal_entry", fake_post_journal_entry)
    monkeypatch.setattr(business_service, "reverse_journal_entry", fake_reverse_journal_entry)

    with pytest.raises(business_service.AccountingValidationError, match="period was unlocked"):
        await business_service.create_gst_settlement(
            None,
            tenant_id="business-tenant",
            app_key="mitrabooks",
            created_by="admin-1",
            payload=GstSettlementCreateRequest(period="2026-06", lock_period=True),
            idempotency_key="gst-comp-1",
        )

    assert captured["journal_id"] == 1251
    assert captured["reason"] == "Compensation after GST settlement persistence failure for 2026-06"
    assert captured["tenant_id"] == "business-tenant"
    assert captured["app_key"] == "mitrabooks"
    assert captured["accounting_entity_id"] == "primary"
    assert await business_service.is_gst_period_locked(
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        period="2026-06",
    ) is False


@pytest.mark.asyncio
async def test_gst_settlement_reverses_journal_when_lock_step_fails(monkeypatch):
    from app.modules.business.schemas import GstSettlementCreateRequest

    settlements = FakeCollection()
    locks = AlwaysFailUpdateCollection()
    captured = {}

    def fake_get_collection(name):
        if name == business_service.GST_SETTLEMENTS_COLLECTION:
            return settlements
        if name == business_service.GST_PERIOD_LOCKS_COLLECTION:
            return locks
        return FakeCollection()

    monkeypatch.setattr(business_service, "get_collection", fake_get_collection)
    monkeypatch.setattr(business_service, "initialize_default_chart_of_accounts", lambda *a, **k: _async_none())
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_k: _async_none())

    async def fake_balances(session, **_kwargs):
        return {
            "output": {"igst": Decimal("100"), "cgst": Decimal("500"), "sgst": Decimal("500")},
            "credit": {"igst": Decimal("600"), "cgst": Decimal("200"), "sgst": Decimal("100")},
        }

    async def fake_resolve(_session, *, account_code, **_kwargs):
        return _INVOICE_ACCOUNT_IDS[account_code]

    async def fake_post_journal_entry(_session, **_kwargs):
        return SimpleNamespace(id=1252), True

    async def fake_reverse_journal_entry(_session, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id=2252), True

    monkeypatch.setattr(business_service, "_gst_period_balances", fake_balances)
    monkeypatch.setattr(business_service, "_resolve_voucher_account_id", fake_resolve)
    monkeypatch.setattr(business_service, "post_journal_entry", fake_post_journal_entry)
    monkeypatch.setattr(business_service, "reverse_journal_entry", fake_reverse_journal_entry)

    with pytest.raises(business_service.AccountingValidationError, match="automatically reversed"):
        await business_service.create_gst_settlement(
            None,
            tenant_id="business-tenant",
            app_key="mitrabooks",
            created_by="admin-1",
            payload=GstSettlementCreateRequest(period="2026-06", lock_period=True),
            idempotency_key="gst-comp-2",
        )

    assert captured["journal_id"] == 1252
    assert captured["reason"] == "Compensation after GST settlement persistence failure for 2026-06"
    assert captured["tenant_id"] == "business-tenant"
    assert captured["app_key"] == "mitrabooks"
    assert captured["accounting_entity_id"] == "primary"
    assert settlements.docs == []


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
async def test_business_admin_settings_save_and_get_round_trip(monkeypatch):
    from app.modules.business.schemas import (
        BusinessAdminSettingsUpdateRequest,
        BusinessBranchSettingsItem,
        BusinessOrganizationSettings,
    )

    store = FakeCollection()
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_k: _async_none())

    payload = BusinessAdminSettingsUpdateRequest(
        organization=BusinessOrganizationSettings(
            legal_name="Acme Traders Private Limited",
            trade_name="Acme Traders",
            gstin="29ABCDE1234F1Z5",
            currency_code="INR",
            timezone="Asia/Calcutta",
        ),
        branches=[
            BusinessBranchSettingsItem(
                branch_code="BLR",
                branch_name="Bengaluru Head Office",
                gstin="29ABCDE1234F1Z5",
                warehouse_code="WH-BLR",
            )
        ],
    )
    saved = await business_service.save_business_admin_settings(
        tenant_id="business-tenant", app_key="mitrabooks", updated_by="admin-1", payload=payload,
    )
    assert saved["organization"]["legal_name"] == "Acme Traders Private Limited"
    assert saved["branches"][0]["branch_code"] == "BLR"
    assert saved["voucher_configuration"]["journal_prefix"] == "JV"
    assert saved["updated_by"] == "admin-1"

    fetched = await business_service.get_business_admin_settings(
        tenant_id="business-tenant", app_key="mitrabooks", accounting_entity_id="primary",
    )
    assert fetched["organization"]["trade_name"] == "Acme Traders"
    assert fetched["permissions"]["action_permissions"]["settings_manage"] == ["owner", "admin"]
    assert fetched["integrations"]["document_storage_provider"] == "local_filesystem"
    assert fetched["ai_settings"]["auto_post_to_ledger"] is False


@pytest.mark.asyncio
async def test_ca_client_records_are_tenant_scoped_and_updatable(monkeypatch):
    clients = FakeCollection()
    audit_events = []

    def fake_get_collection(_name):
        return clients

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(business_service, "get_collection", fake_get_collection)
    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    created = await business_service.create_ca_client(
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        created_by="partner-1",
        payload=CaClientCreateRequest(
            client_name="Jayam Publications",
            gstin="29ABCDE1234F1Z5",
            pan="ABCDE1234F",
            contact_person="Mr Jayam",
            assigned_to="Staff A",
            client_owner="Partner A",
            engagement_type="GST and bookkeeping",
            access_level="full_access",
            compliance_tracks=["GST", "TDS"],
            notes="Priority client",
        ),
    )

    clients.docs.append(
        {
            **clients.docs[0],
            "client_id": "other-client",
            "tenant_id": "other-tenant",
            "client_name": "Other Client",
        }
    )

    listed = await business_service.list_ca_clients(
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        q="jayam",
    )
    updated = await business_service.update_ca_client(
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        client_id=created["client_id"],
        updated_by="partner-2",
        payload=CaClientUpdateRequest(
            assigned_to="Staff B",
            access_level="restricted_filing",
            active=False,
            compliance_tracks=["GST", "Audit"],
        ),
    )

    assert created["tenant_id"] == "business-tenant"
    assert created["access_level"] == "full_access"
    assert listed["total"] == 1
    assert listed["items"][0]["client_name"] == "Jayam Publications"
    assert updated is not None
    assert updated["assigned_to"] == "Staff B"
    assert updated["access_level"] == "restricted_filing"
    assert updated["active"] is False
    assert updated["compliance_tracks"] == ["GST", "Audit"]
    assert audit_events[0]["action"] == "business_ca_client_created"
    assert audit_events[1]["action"] == "business_ca_client_updated"


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

    # With due_date -> creates a pending-approval invoice and uses the custom number format.
    result = await business_service.create_sales_invoice(
        None, tenant_id="business-tenant", app_key="mitrabooks", created_by="owner-1",
        payload=SalesInvoiceCreateRequest(due_date=date(2026, 7, 8), **base), idempotency_key=None,
    )
    assert result["invoice_number"] == "ACME/2026-27/0001"
    assert result["status"] == "pending_approval"
    assert result["approval_status"] == "pending_approval"


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
async def test_sales_invoice_pdf_requires_posted_status(monkeypatch):
    async def fake_get_sales_invoice(**_kwargs):
        return {
            "invoice_id": "inv-draft-1",
            "invoice_number": "INV-1",
            "status": "pending_approval",
        }

    monkeypatch.setattr(business_router, "get_sales_invoice", fake_get_sales_invoice)

    with pytest.raises(HTTPException) as exc:
        await business_router.get_business_sales_invoice_pdf(
            invoice_id="inv-draft-1",
            accounting_entity_id="primary",
            _module_context={},
            current_user={"tenant_id": "business-tenant", "app_key": "mitrabooks"},
            x_tenant_id=None,
            x_app_key="mitrabooks",
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Only posted sales invoices can be rendered or exported"


@pytest.mark.asyncio
async def test_sales_invoice_pdf_allows_posted_document(monkeypatch):
    async def fake_get_sales_invoice(**_kwargs):
        return {
            "invoice_id": "inv-posted-1",
            "invoice_number": "INV-1",
            "status": "posted",
        }

    async def fake_get_invoice_settings(**_kwargs):
        return {"branding": {"company_name": "Acme"}}

    monkeypatch.setattr(business_router, "get_sales_invoice", fake_get_sales_invoice)
    monkeypatch.setattr(business_router, "get_invoice_settings", fake_get_invoice_settings)
    monkeypatch.setattr(business_router, "build_sales_invoice_pdf", lambda invoice, branding: b"%PDF-test")

    response = await business_router.get_business_sales_invoice_pdf(
        invoice_id="inv-posted-1",
        accounting_entity_id="primary",
        _module_context={},
        current_user={"tenant_id": "business-tenant", "app_key": "mitrabooks"},
        x_tenant_id=None,
        x_app_key="mitrabooks",
    )

    assert response.media_type == "application/pdf"
    assert response.body == b"%PDF-test"


def test_posted_output_guard_rejects_missing_bill_document():
    with pytest.raises(HTTPException) as exc:
        business_router._require_posted_document_for_output(
            None,
            not_found_detail="Purchase bill not found",
            label="purchase bills",
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Purchase bill not found"


def test_posted_output_guard_rejects_unposted_bill_document():
    with pytest.raises(HTTPException) as exc:
        business_router._require_posted_document_for_output(
            {"bill_id": "bill-1", "status": "draft"},
            not_found_detail="Purchase bill not found",
            label="purchase bills",
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Only posted purchase bills can be rendered or exported"


@pytest.mark.asyncio
async def test_sales_invoice_attachment_upload_list_and_download_are_tenant_scoped(monkeypatch, tmp_path):
    invoices = FakeCollection()
    attachments = FakeCollection()
    invoices.docs = [
        {
            "invoice_id": "inv-1",
            "tenant_id": "business-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "invoice_number": "INV-1",
            "status": "draft",
        }
    ]
    audit_events = []

    def fake_get_collection(name):
        return {
            business_service.SALES_INVOICES_COLLECTION: invoices,
            business_service.BUSINESS_DOCUMENT_ATTACHMENTS_COLLECTION: attachments,
        }[name]

    async def fake_log_audit_event(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(business_service, "get_collection", fake_get_collection)
    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)
    monkeypatch.setattr(business_service, "BUSINESS_ATTACHMENT_STORAGE_DIR", tmp_path / "business-attachments")

    created = await business_service.create_business_document_attachment(
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        owner_type="sales_invoice",
        owner_id="inv-1",
        uploaded_by="owner-1",
        file_name="invoice-support.pdf",
        content_type="application/pdf",
        payload=b"%PDF-test",
    )

    attachments.docs.append(
        {
            **attachments.docs[0],
            "attachment_id": "other-tenant-attachment",
            "tenant_id": "other-tenant",
            "owner_id": "inv-2",
        }
    )

    listed = await business_service.list_business_document_attachments(
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        owner_type="sales_invoice",
        owner_id="inv-1",
    )
    downloaded = await business_service.download_business_document_attachment(
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        owner_type="sales_invoice",
        owner_id="inv-1",
        attachment_id=created["attachment_id"],
        downloaded_by="owner-2",
    )

    assert created["owner_type"] == "sales_invoice"
    assert created["file_name"] == "invoice-support.pdf"
    assert created["content_type"] == "application/pdf"
    assert listed["total"] == 1
    assert listed["items"][0]["attachment_id"] == created["attachment_id"]
    assert downloaded["payload"] == b"%PDF-test"
    assert audit_events[0]["action"] == "business_document_attachment_uploaded"
    assert audit_events[-1]["action"] == "business_document_attachment_downloaded"


@pytest.mark.asyncio
async def test_purchase_bill_attachment_validates_owner_and_file_type(monkeypatch, tmp_path):
    bills = FakeCollection()
    attachments = FakeCollection()

    def fake_get_collection(name):
        return {
            business_service.PURCHASE_BILLS_COLLECTION: bills,
            business_service.BUSINESS_DOCUMENT_ATTACHMENTS_COLLECTION: attachments,
        }[name]

    monkeypatch.setattr(business_service, "get_collection", fake_get_collection)
    monkeypatch.setattr(business_service, "BUSINESS_ATTACHMENT_STORAGE_DIR", tmp_path / "business-attachments")

    with pytest.raises(business_service.AccountingNotFoundError, match="Purchase bill not found"):
        await business_service.create_business_document_attachment(
            tenant_id="business-tenant",
            app_key="mitrabooks",
            accounting_entity_id="primary",
            owner_type="purchase_bill",
            owner_id="missing-bill",
            uploaded_by="owner-1",
            file_name="support.pdf",
            content_type="application/pdf",
            payload=b"%PDF-test",
        )

    bills.docs.append(
        {
            "bill_id": "bill-1",
            "tenant_id": "business-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "bill_number": "SUP-1",
            "status": "draft",
        }
    )

    with pytest.raises(business_service.AccountingValidationError, match="Unsupported attachment type"):
        await business_service.create_business_document_attachment(
            tenant_id="business-tenant",
            app_key="mitrabooks",
            accounting_entity_id="primary",
            owner_type="purchase_bill",
            owner_id="bill-1",
            uploaded_by="owner-1",
            file_name="support.exe",
            content_type="application/x-msdownload",
            payload=b"MZ",
        )


@pytest.mark.asyncio
async def test_ca_document_attachment_download_requires_matching_tenant_scope(monkeypatch, tmp_path):
    ca_documents = FakeCollection()
    attachments = FakeCollection()
    ca_documents.docs = [
        {
            "document_id": "doc-1",
            "tenant_id": "business-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "client_name": "Jayam Publications",
            "document_type": "GST working",
            "period": "May 2026",
            "status": "uploaded",
        }
    ]

    def fake_get_collection(name):
        return {
            business_service.CA_DOCUMENTS_COLLECTION: ca_documents,
            business_service.BUSINESS_DOCUMENT_ATTACHMENTS_COLLECTION: attachments,
        }[name]

    monkeypatch.setattr(business_service, "get_collection", fake_get_collection)
    monkeypatch.setattr(business_service, "log_audit_event", lambda **_kwargs: _async_none())
    monkeypatch.setattr(business_service, "BUSINESS_ATTACHMENT_STORAGE_DIR", tmp_path / "business-attachments")

    created = await business_service.create_business_document_attachment(
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        owner_type="ca_document",
        owner_id="doc-1",
        uploaded_by="reviewer-1",
        file_name="gst-working.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        payload=b"PK\x03\x04",
    )

    with pytest.raises(business_service.AccountingNotFoundError):
        await business_service.download_business_document_attachment(
            tenant_id="other-tenant",
            app_key="mitrabooks",
            accounting_entity_id="primary",
            owner_type="ca_document",
            owner_id="doc-1",
            attachment_id=created["attachment_id"],
            downloaded_by="reviewer-2",
        )


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
            client_owner="Partner A",
            priority="high",
            due_date="2026-06-20",
            compliance_area="GST",
            client_access_enabled=True,
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
    assert result["client_owner"] == "Partner A"
    assert result["priority"] == "high"
    assert result["due_date"] == "2026-06-20"
    assert result["compliance_area"] == "GST"
    assert result["client_access_enabled"] is True
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
            "client_owner": "Partner A",
            "priority": "normal",
            "due_date": None,
            "compliance_area": "GST",
            "client_access_enabled": False,
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
        payload=CaDocumentUpdateRequest(
            status="under_review",
            assigned_to="Staff B",
            priority="urgent",
            due_date="2026-06-18",
            client_access_enabled=True,
        ),
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
    assert result["assigned_to"] == "Staff B"
    assert result["priority"] == "urgent"
    assert result["due_date"] == "2026-06-18"
    assert result["client_access_enabled"] is True
    assert result["next_action"] == "Review support and raise query if needed"
    assert wrong_tenant is None


@pytest.mark.asyncio
async def test_list_ca_document_metadata_filters_inside_tenant_scope(monkeypatch):
    documents = FakeCollection()
    now = business_service._now()
    documents.docs = [
        {
            "document_id": "doc-high",
            "tenant_id": "business-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "client_name": "Jayam Publications",
            "document_type": "Bank statement",
            "period": "May 2026",
            "status": "under_review",
            "assigned_to": "Staff A",
            "client_owner": "Partner A",
            "priority": "high",
            "due_date": "2026-06-20",
            "compliance_area": "GST",
            "client_access_enabled": True,
            "original_file_name": "jayam-bank.pdf",
            "next_action": "Review support and raise query if needed",
            "posting_reference": None,
            "notes": None,
            "created_by": "reviewer-1",
            "created_at": now,
            "updated_at": now,
        },
        {
            "document_id": "doc-normal",
            "tenant_id": "business-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "client_name": "Other Books",
            "document_type": "Sales invoices",
            "period": "May 2026",
            "status": "uploaded",
            "assigned_to": "Staff B",
            "priority": "normal",
            "next_action": "Classify document and assign reviewer",
            "created_by": "reviewer-1",
            "created_at": now,
            "updated_at": now,
        },
        {
            "document_id": "doc-other-tenant",
            "tenant_id": "other-tenant",
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "client_name": "Jayam Publications",
            "document_type": "GST return",
            "period": "May 2026",
            "status": "under_review",
            "assigned_to": "Staff A",
            "priority": "high",
            "next_action": "Review support and raise query if needed",
            "created_by": "reviewer-1",
            "created_at": now,
            "updated_at": now,
        },
    ]
    monkeypatch.setattr(business_service, "get_collection", lambda _name: documents)

    result = await business_service.list_ca_document_metadata(
        tenant_id="business-tenant",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        status="under_review",
        client_name="jayam",
        assigned_to="Staff A",
        priority="high",
    )

    assert result["total"] == 1
    assert result["items"][0]["document_id"] == "doc-high"
    assert result["items"][0]["tenant_id"] == "business-tenant"


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
    created_doc = await business_service.create_sales_invoice(
        None, tenant_id="business-tenant", app_key="mitrabooks", created_by="owner-1",
        payload=SalesInvoiceCreateRequest(
            customer_party_id="cust-1", invoice_date=date(2026, 6, 8), is_inter_state=False,
            line_items=[SalesInvoiceLineItem(description="W", quantity=Decimal("1"), rate=Decimal("100"), gst_rate=Decimal("18"))],
        ),
        idempotency_key=None,
    )
    await business_service.review_sales_invoice(
        session=object(),
        tenant_id="business-tenant",
        app_key="mitrabooks",
        invoice_id=created_doc["invoice_id"],
        reviewed_by="admin-1",
        payload=business_service.ApprovalReviewRequest(approve=True, accounting_entity_id="primary"),
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
    created_doc = await business_service.create_purchase_bill(
        None, tenant_id="business-tenant", app_key="mitrabooks", created_by="owner-1",
        payload=PurchaseBillCreateRequest(
            vendor_party_id="vend-1", bill_number="B-1", bill_date=date(2026, 6, 8), is_inter_state=False,
            line_items=[PurchaseBillLineItem(description="G", quantity=Decimal("1"), rate=Decimal("100"), gst_rate=Decimal("18"))],
        ),
        idempotency_key=None,
    )
    await business_service.review_purchase_bill(
        session=object(),
        tenant_id="business-tenant",
        app_key="mitrabooks",
        bill_id=created_doc["bill_id"],
        reviewed_by="admin-1",
        payload=business_service.ApprovalReviewRequest(approve=True, accounting_entity_id="primary"),
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
    created_receipt = await business_service.post_typed_voucher(
        None, tenant_id="business-tenant", app_key="mitrabooks", created_by="owner-1",
        payload=TypedVoucherCreateRequest(
            voucher_type="receipt", entry_date=date(2026, 6, 8), amount=Decimal("500"),
            debit_account_id=10, credit_account_id=20, party_id="cust-1", reference="RV-9",
            description="Receipt from customer",
        ),
        idempotency_key=None,
    )
    await business_service.review_typed_voucher(
        session=object(),
        tenant_id="business-tenant",
        app_key="mitrabooks",
        voucher_id=created_receipt["voucher_id"],
        reviewed_by="admin-1",
        payload=business_service.ApprovalReviewRequest(approve=True, accounting_entity_id="primary"),
    )
    rlines = captured["payload"].lines
    assert rlines[0].party_id is None          # debit (bank) untagged
    assert rlines[1].party_id == "cust-1"      # credit (customer) tagged

    # Payment → party on the debit (vendor/payable) line.
    store2 = FakeCollection(); captured2 = {}
    _party_tag_mocks(monkeypatch, store2, captured2)
    created_payment = await business_service.post_typed_voucher(
        None, tenant_id="business-tenant", app_key="mitrabooks", created_by="owner-1",
        payload=TypedVoucherCreateRequest(
            voucher_type="payment", entry_date=date(2026, 6, 8), amount=Decimal("500"),
            debit_account_id=30, credit_account_id=40, party_id="vend-1", reference="PV-9",
            description="Payment to vendor",
        ),
        idempotency_key=None,
    )
    await business_service.review_typed_voucher(
        session=object(),
        tenant_id="business-tenant",
        app_key="mitrabooks",
        voucher_id=created_payment["voucher_id"],
        reviewed_by="admin-1",
        payload=business_service.ApprovalReviewRequest(approve=True, accounting_entity_id="primary"),
    )
    plines = captured2["payload"].lines
    assert plines[0].party_id == "vend-1"      # debit (vendor) tagged
    assert plines[1].party_id is None          # credit (bank) untagged
