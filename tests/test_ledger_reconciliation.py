"""SEC-07: MongoDB <-> PostgreSQL ledger reconciliation finds both kinds of drift."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from bson import ObjectId

from app.accounting.models import JournalEntry
from app.core.reconciliation import ledger_sync

NOW = datetime.now(timezone.utc)
OLD = NOW - timedelta(hours=2)  # older than the 15-minute grace


def _oid(at: datetime) -> ObjectId:
    return ObjectId.from_datetime(at)


class _Cursor:
    def __init__(self, docs):
        self.docs = docs

    def limit(self, n):
        self.docs = self.docs[:n]
        return self

    async def to_list(self, length):
        return self.docs[:length]


class _Coll:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    def _match(self, doc, query):
        for key, want in query.items():
            have = doc.get(key)
            if isinstance(want, dict):
                if "$gte" in want and not (have >= want["$gte"]):
                    return False
                if "$lte" in want and not (have <= want["$lte"]):
                    return False
            elif have != want:
                return False
        return True

    def find(self, query):
        return _Cursor([d for d in self.docs if self._match(d, query)])

    async def find_one(self, query):
        return next((d for d in self.docs if self._match(d, query)), None)

    async def insert_one(self, doc):
        self.docs.append(doc)


@pytest.fixture
def mongo(monkeypatch):
    collections: dict[str, _Coll] = {}

    def get(name):
        return collections.setdefault(name, _Coll())

    monkeypatch.setattr(ledger_sync, "get_collection", get)
    return get


def _journal(key, *, tenant="t-1", app="mandirmitra", entity="primary", at=OLD):
    return JournalEntry(
        app_key=app,
        tenant_id=tenant,
        accounting_entity_id=entity,
        entry_date=at.date(),
        description="test",
        idempotency_key=key,
        total_debit=Decimal("100.00"),
        total_credit=Decimal("100.00"),
        created_at=at,
    )


@pytest.mark.asyncio
async def test_reconciliation_reports_each_kind_of_drift(session, mongo):
    donations = mongo("mandir_donations")
    donations.docs += [
        # Posted correctly.
        {"_id": _oid(OLD), "donation_id": "d-ok", "tenant_id": "t-1", "app_key": "mandirmitra", "amount": "100", "donation_type": "cash"},
        # Crash after the Mongo insert, before the journal: missing journal.
        {"_id": _oid(OLD), "donation_id": "d-missing", "tenant_id": "t-1", "app_key": "mandirmitra", "amount": "250", "donation_type": "cash"},
        # In-kind donations do not need a journal.
        {"_id": _oid(OLD), "donation_id": "d-kind", "tenant_id": "t-1", "app_key": "mandirmitra", "amount": "0", "donation_type": "in_kind"},
        # Too recent: inside the grace window, not judged yet.
        {"_id": _oid(NOW), "donation_id": "d-new", "tenant_id": "t-1", "app_key": "mandirmitra", "amount": "50", "donation_type": "cash"},
    ]
    invoices = mongo("business_sales_invoices")
    invoices.docs += [
        # Journal posted, but the record never got marked posted.
        {"_id": _oid(OLD), "invoice_id": "inv-1", "tenant_id": "t-1", "app_key": "mitrabooks", "accounting_entity_id": "primary", "status": "pending_approval"},
        # Draft: no journal expected.
        {"_id": _oid(OLD), "invoice_id": "inv-2", "tenant_id": "t-1", "app_key": "mitrabooks", "accounting_entity_id": "primary", "status": "draft"},
    ]
    session.add_all(
        [
            _journal("don_d-ok"),
            _journal("don_d-gone"),  # record was deleted after posting: orphan journal
            _journal("don_d-other-tenant", tenant="t-2"),  # other tenant: same check, separate scope
            _journal("sales-invoice:inv-1", app="mitrabooks"),
            _journal("unrelated:123"),
        ]
    )
    await session.commit()

    report = await ledger_sync.reconcile_ledger(session, since=NOW - timedelta(days=1))
    don = report["sources"]["mandir_donation"]
    assert don["missing_journal"] == 1
    assert don["samples"]["missing_journal"][0]["record_id"] == "d-missing"
    assert don["samples"]["missing_journal"][0]["expected_idempotency_key"] == "don_d-missing"
    assert {s["idempotency_key"] for s in don["samples"]["orphan_journal"]} == {"don_d-gone", "don_d-other-tenant"}
    inv = report["sources"]["business_sales_invoice"]
    assert inv["missing_journal"] == 0
    assert inv["unmarked_posting"] == 1
    assert report["issue_count"] == 4

    scoped = await ledger_sync.reconcile_ledger(session, since=NOW - timedelta(days=1), tenant_id="t-2")
    assert scoped["sources"]["mandir_donation"]["orphan_journal"] == 1
    assert scoped["sources"]["mandir_donation"]["missing_journal"] == 0


@pytest.mark.asyncio
async def test_clean_books_report_no_issues(session, mongo):
    mongo("temple_donations").docs.append(
        {"_id": _oid(OLD), "donation_id": "t-don", "tenant_id": "t-1", "app_key": "mandirmitra", "amount": "10"}
    )
    mongo("housing_maintenance_collections").docs += [
        {"_id": _oid(OLD), "collection_id": "c-1", "tenant_id": "t-1", "app_key": "gruhamitra", "bill_id": None, "reference": None},
        {"_id": _oid(OLD), "collection_id": "c-2", "tenant_id": "t-1", "app_key": "gruhamitra", "bill_id": "b-9", "reference": "UTR42"},
    ]
    session.add_all(
        [
            _journal("donation:t-don"),
            _journal("maintenance:c-1", app="gruhamitra"),
            _journal("maintenance-bill:t-1:gruhamitra:b-9:UTR42", app="gruhamitra"),
        ]
    )
    await session.commit()
    report = await ledger_sync.reconcile_ledger(session, since=NOW - timedelta(days=1))
    assert report["issue_count"] == 0
    assert report["sources"]["housing_maintenance_collection"]["checked_records"] == 2
    assert report["sources"]["housing_maintenance_collection"]["checked_journals"] == 2


@pytest.mark.asyncio
async def test_platform_endpoint_is_super_admin_only(monkeypatch):
    from fastapi import HTTPException

    from app.core.platform_owner import router as owner_router

    with pytest.raises(HTTPException) as exc:
        await owner_router.ledger_reconciliation(days=7, tenant_id=None, current_user={"role": "tenant_admin"}, session=None)
    assert exc.value.status_code == 403

    async def fake_reconcile(session, *, since, tenant_id):
        return {"issue_count": 0, "tenant_id": tenant_id}

    async def fake_save(report):
        report["_id"] = "x"

    monkeypatch.setattr(owner_router, "reconcile_ledger", fake_reconcile)
    monkeypatch.setattr(owner_router, "save_report", fake_save)
    out = await owner_router.ledger_reconciliation(days=3, tenant_id="t-9", current_user={"role": "super_admin"}, session=None)
    assert out == {"issue_count": 0, "tenant_id": "t-9"}


@pytest.mark.asyncio
async def test_worker_is_off_when_interval_is_zero():
    assert await ledger_sync.start_ledger_reconciliation_worker(interval_hours=0, lookback_days=3) is False
