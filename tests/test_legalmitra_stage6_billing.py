"""LegalMitra Stage 6 — practice billing service tests."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.legal import billing_service as billing
from app.modules.legal import practice_service as practice
from app.modules.legal.billing_schemas import (
    FeeCollectionCreateRequest,
    FeeInvoiceCreateRequest,
    FeeInvoiceVoidRequest,
    FeeLineIn,
    TimeEntryCreateRequest,
)
from app.modules.legal.practice_schemas import (
    ClientCreateRequest,
    MatterCreateRequest,
    MatterStatus,
)


class _Cursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, *_a, **_k):
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    async def to_list(self, length=None):
        if length is None:
            return list(self._docs)
        return list(self._docs[:length])


class FakeCollection:
    def __init__(self):
        self.docs: list[dict] = []
        self.seq = 0

    async def create_index(self, *_a, **_k):
        return None

    @staticmethod
    def _match(doc, flt):
        return all(doc.get(k) == v for k, v in flt.items())

    async def find_one(self, flt):
        for d in self.docs:
            if self._match(d, flt):
                return dict(d)
        return None

    async def insert_one(self, doc):
        # Simulate unique idempotency conflicts
        if "idempotency_key" in doc:
            for d in self.docs:
                if (
                    d.get("tenant_id") == doc.get("tenant_id")
                    and d.get("app_key") == doc.get("app_key")
                    and d.get("idempotency_key") == doc.get("idempotency_key")
                ):
                    raise RuntimeError("duplicate key")
        self.docs.append(dict(doc))

    def find(self, flt):
        return _Cursor([dict(d) for d in self.docs if self._match(d, flt)])

    async def count_documents(self, flt):
        return sum(1 for d in self.docs if self._match(d, flt))

    async def update_one(self, flt, update, upsert=False):
        matched = False
        for d in self.docs:
            if self._match(d, flt):
                d.update(update.get("$set", {}))
                for key, amount in (update.get("$inc") or {}).items():
                    d[key] = int(d.get(key) or 0) + int(amount)
                matched = True
                break
        if not matched and upsert:
            new_doc = dict(flt)
            new_doc.update(update.get("$set", {}))
            new_doc.update(update.get("$setOnInsert", {}))
            for key, amount in (update.get("$inc") or {}).items():
                new_doc[key] = int(amount)
            self.docs.append(new_doc)

    async def find_one_and_update(self, filters, update, **_kwargs):
        for d in self.docs:
            if self._match(d, filters):
                for key, amount in (update.get("$inc") or {}).items():
                    d[key] = int(d.get(key) or 0) + int(amount)
                d.update(update.get("$set", {}))
                return dict(d)
        new_doc = dict(filters)
        new_doc.update(update.get("$setOnInsert", {}))
        for key, amount in (update.get("$inc") or {}).items():
            new_doc[key] = int(amount)
        self.docs.append(new_doc)
        return dict(new_doc)


@pytest.fixture
def fake_db(monkeypatch):
    cols: dict[str, FakeCollection] = {}

    def _get(name: str):
        return cols.setdefault(name, FakeCollection())

    monkeypatch.setattr(practice, "get_collection", _get)
    monkeypatch.setattr(billing, "get_collection", _get)
    monkeypatch.setattr(practice, "log_audit_event", _noop_audit)
    monkeypatch.setattr(billing, "log_audit_event", _noop_audit)
    return cols


async def _noop_audit(**_kwargs):
    return "evt"


async def _seed_matter():
    client = await practice.create_client(
        tenant_id="tenant-a",
        app_key="legalmitra",
        created_by="user-1",
        payload=ClientCreateRequest(display_name="Acme Ltd"),
    )
    matter = await practice.create_matter(
        tenant_id="tenant-a",
        app_key="legalmitra",
        created_by="user-1",
        payload=MatterCreateRequest(
            client_id=client["client_id"],
            title="Advisory retainership",
            status=MatterStatus.ACTIVE,
            practice_area="advisory",
            jurisdiction="India",
            next_deadline_date=date.today() + timedelta(days=10),
        ),
    )
    return client, matter


@pytest.mark.asyncio
async def test_create_issue_collect_partial_and_paid(fake_db):
    _client, matter = await _seed_matter()
    invoice = await billing.create_fee_invoice(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        payload=FeeInvoiceCreateRequest(
            matter_id=matter["matter_id"],
            lines=[
                FeeLineIn(
                    description="Retainer",
                    quantity=Decimal("1"),
                    unit_rate=Decimal("10000.00"),
                    tax_rate_percent=Decimal("18"),
                )
            ],
        ),
    )
    assert invoice["status"] == "draft"
    assert invoice["grand_total"] == Decimal("11800.00")
    assert invoice["invoice_number"].startswith("FEE-")

    issued = await billing.issue_fee_invoice(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        invoice_id=invoice["invoice_id"],
    )
    assert issued["status"] == "issued"

    partial = await billing.record_fee_collection(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        invoice_id=invoice["invoice_id"],
        payload=FeeCollectionCreateRequest(
            amount=Decimal("5000.00"),
            idempotency_key=f"collect-{uuid4()}",
        ),
    )
    assert partial["accounting_status"] == "not_posted"
    after = await billing.get_fee_invoice(
        tenant_id="tenant-a",
        app_key="legalmitra",
        invoice_id=invoice["invoice_id"],
    )
    assert after["status"] == "partially_paid"
    assert after["amount_outstanding"] == Decimal("6800.00")

    await billing.record_fee_collection(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        invoice_id=invoice["invoice_id"],
        payload=FeeCollectionCreateRequest(
            amount=Decimal("6800.00"),
            idempotency_key=f"collect-{uuid4()}",
        ),
    )
    paid = await billing.get_fee_invoice(
        tenant_id="tenant-a",
        app_key="legalmitra",
        invoice_id=invoice["invoice_id"],
    )
    assert paid["status"] == "paid"
    assert paid["amount_outstanding"] == Decimal("0.00")

    summary = await billing.get_fee_summary(tenant_id="tenant-a", app_key="legalmitra")
    assert summary["fees_outstanding"] == Decimal("0.00")
    assert summary["total_collected"] == Decimal("11800.00")


@pytest.mark.asyncio
async def test_collection_idempotency(fake_db):
    _client, matter = await _seed_matter()
    invoice = await billing.create_fee_invoice(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        payload=FeeInvoiceCreateRequest(
            matter_id=matter["matter_id"],
            lines=[FeeLineIn(description="Opinion", unit_rate=Decimal("1000.00"))],
        ),
    )
    await billing.issue_fee_invoice(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        invoice_id=invoice["invoice_id"],
    )
    key = f"idem-{uuid4()}"
    first = await billing.record_fee_collection(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        invoice_id=invoice["invoice_id"],
        payload=FeeCollectionCreateRequest(amount=Decimal("1000.00"), idempotency_key=key),
    )
    second = await billing.record_fee_collection(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        invoice_id=invoice["invoice_id"],
        payload=FeeCollectionCreateRequest(amount=Decimal("1000.00"), idempotency_key=key),
    )
    assert first["collection_id"] == second["collection_id"]


@pytest.mark.asyncio
async def test_void_draft_and_block_void_with_collections(fake_db):
    _client, matter = await _seed_matter()
    draft = await billing.create_fee_invoice(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        payload=FeeInvoiceCreateRequest(
            matter_id=matter["matter_id"],
            lines=[FeeLineIn(description="Draft fee", unit_rate=Decimal("500.00"))],
        ),
    )
    voided = await billing.void_fee_invoice(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        invoice_id=draft["invoice_id"],
        payload=FeeInvoiceVoidRequest(reason="Created in error", confirm=True),
    )
    assert voided["status"] == "void"

    invoice = await billing.create_fee_invoice(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        payload=FeeInvoiceCreateRequest(
            matter_id=matter["matter_id"],
            lines=[FeeLineIn(description="Hearing", unit_rate=Decimal("2000.00"))],
        ),
    )
    await billing.issue_fee_invoice(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        invoice_id=invoice["invoice_id"],
    )
    await billing.record_fee_collection(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        invoice_id=invoice["invoice_id"],
        payload=FeeCollectionCreateRequest(
            amount=Decimal("500.00"), idempotency_key=f"c-{uuid4()}"
        ),
    )
    with pytest.raises(billing.BillingConflictError):
        await billing.void_fee_invoice(
            tenant_id="tenant-a",
            app_key="legalmitra",
            actor_id="user-1",
            invoice_id=invoice["invoice_id"],
            payload=FeeInvoiceVoidRequest(reason="Too late", confirm=True),
        )


@pytest.mark.asyncio
async def test_post_to_mitrabooks_requires_confirm_and_flag(fake_db, monkeypatch):
    _client, matter = await _seed_matter()
    invoice = await billing.create_fee_invoice(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        payload=FeeInvoiceCreateRequest(
            matter_id=matter["matter_id"],
            lines=[FeeLineIn(description="Fee", unit_rate=Decimal("100.00"))],
        ),
    )
    await billing.issue_fee_invoice(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        invoice_id=invoice["invoice_id"],
    )
    with pytest.raises(billing.BillingValidationError):
        await billing.record_fee_collection(
            tenant_id="tenant-a",
            app_key="legalmitra",
            actor_id="user-1",
            invoice_id=invoice["invoice_id"],
            payload=FeeCollectionCreateRequest(
                amount=Decimal("100.00"),
                idempotency_key=f"p-{uuid4()}",
                post_to_mitrabooks=True,
                confirm_post_to_mitrabooks=False,
            ),
        )

    class _Settings:
        LEGALMITRA_BILLING_ENABLED = True
        LEGALMITRA_MITRABOOKS_POSTING_ENABLED = False

    monkeypatch.setattr(billing, "get_settings", lambda: _Settings())
    monkeypatch.setattr(
        "app.modules.legal.billing_accounting.posting_enabled", lambda: False
    )
    with pytest.raises(billing.BillingValidationError):
        await billing.record_fee_collection(
            tenant_id="tenant-a",
            app_key="legalmitra",
            actor_id="user-1",
            invoice_id=invoice["invoice_id"],
            payload=FeeCollectionCreateRequest(
                amount=Decimal("100.00"),
                idempotency_key=f"p-{uuid4()}",
                post_to_mitrabooks=True,
                confirm_post_to_mitrabooks=True,
            ),
        )


@pytest.mark.asyncio
async def test_time_entry_and_tenant_isolation(fake_db):
    _client, matter = await _seed_matter()
    entry = await billing.create_time_entry(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        payload=TimeEntryCreateRequest(
            matter_id=matter["matter_id"],
            minutes=90,
            hourly_rate=Decimal("2000.00"),
            description="Draft reply",
        ),
    )
    assert entry["amount"] == Decimal("3000.00")

    invoice = await billing.create_fee_invoice(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        payload=FeeInvoiceCreateRequest(
            matter_id=matter["matter_id"],
            lines=[FeeLineIn(description="Fee", unit_rate=Decimal("10.00"))],
        ),
    )
    with pytest.raises(billing.BillingNotFoundError):
        await billing.get_fee_invoice(
            tenant_id="tenant-b",
            app_key="legalmitra",
            invoice_id=invoice["invoice_id"],
        )


@pytest.mark.asyncio
async def test_dashboard_fees_outstanding_from_billing(fake_db):
    _client, matter = await _seed_matter()
    invoice = await billing.create_fee_invoice(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        payload=FeeInvoiceCreateRequest(
            matter_id=matter["matter_id"],
            lines=[FeeLineIn(description="Fee", unit_rate=Decimal("2500.00"))],
        ),
    )
    await billing.issue_fee_invoice(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        invoice_id=invoice["invoice_id"],
    )
    dash = await practice.get_practice_dashboard(
        tenant_id="tenant-a", app_key="legalmitra", limit=8
    )
    assert "2,500.00" in dash["fees_outstanding"] or "2500.00" in dash["fees_outstanding"]


@pytest.mark.asyncio
async def test_billing_feature_flag(fake_db, monkeypatch):
    class _Settings:
        LEGALMITRA_BILLING_ENABLED = False

    monkeypatch.setattr(billing, "get_settings", lambda: _Settings())
    with pytest.raises(billing.BillingDisabledError):
        await billing.get_fee_summary(tenant_id="tenant-a", app_key="legalmitra")
