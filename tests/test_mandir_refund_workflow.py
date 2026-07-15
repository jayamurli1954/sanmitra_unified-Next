from datetime import date, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import app.modules.mandir_compat.router as mandir_router


class FakeCursor:
    def __init__(self, docs):
        self.docs = list(docs)

    def sort(self, *_args):
        return self

    async def to_list(self, length=None):
        return list(self.docs if length is None else self.docs[:length])


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])
        self.fail_next_update = False

    @staticmethod
    def matches(row, query):
        return all(row.get(key) == value for key, value in query.items())

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def find_one(self, query):
        return next((dict(row) for row in self.docs if self.matches(row, query)), None)

    def find(self, query):
        return FakeCursor([dict(row) for row in self.docs if self.matches(row, query)])

    async def update_one(self, query, update, **_kwargs):
        if self.fail_next_update:
            self.fail_next_update = False
            raise RuntimeError("mongo unavailable")
        for row in self.docs:
            if self.matches(row, query):
                row.update(update.get("$set", {}))
                return SimpleNamespace(modified_count=1)
        return SimpleNamespace(modified_count=0)


@pytest.fixture()
def store(monkeypatch):
    collections = {
        "mandir_donations": FakeCollection([
            {
                "id": "don-1", "donation_id": "don-1", "tenant_id": "temple-1",
                "app_key": "mandirmitra", "status": "posted", "donation_type": "cash",
                "amount": "100.25", "currency": "INR", "receipt_number": "DON-0000001",
            },
            {
                "id": "other-don", "donation_id": "other-don", "tenant_id": "temple-2",
                "app_key": "mandirmitra", "status": "posted", "donation_type": "cash",
                "amount": "50.00", "currency": "INR", "receipt_number": "DON-OTHER",
            },
        ]),
        "mandir_seva_bookings": FakeCollection([
            {
                "id": "seva-1", "tenant_id": "temple-1", "app_key": "mandirmitra",
                "status": "confirmed", "payment_status": "paid", "amount_paid": "75.50",
                "currency": "INR", "receipt_number": "SEV-0000001",
            }
        ]),
        "mandir_refund_requests": FakeCollection(),
    }
    monkeypatch.setattr(mandir_router, "get_collection", lambda name: collections[name])
    async def audit(**_kwargs):
        return None
    monkeypatch.setattr(mandir_router, "_audit_mandir_refund_event", audit)
    return collections


def actor(user_id, tenant_id="temple-1"):
    return {"sub": user_id, "tenant_id": tenant_id, "app_key": "mandirmitra", "role": "tenant_admin"}


@pytest.mark.asyncio
async def test_refund_request_maker_checker_settlement_and_retry(store, monkeypatch):
    with pytest.raises(HTTPException) as exc:
        await mandir_router.create_mandir_refund_request(
            {"source_kind": "donation", "source_id": "don-1", "amount": "99.00", "reason": "Wrong amount"},
            actor("maker-1"), None, "mandirmitra",
        )
    assert exc.value.status_code == 409

    refund = await mandir_router.create_mandir_refund_request(
        {
            "source_kind": "donation", "source_id": "don-1", "amount": "100.25",
            "reason": "Duplicate counter receipt", "refund_mode": "UPI",
        },
        actor("maker-1"), None, "mandirmitra",
    )
    assert refund["status"] == "pending_approval"
    assert refund["amount"] == "100.25"

    with pytest.raises(HTTPException) as exc:
        await mandir_router.approve_mandir_refund_request(
            refund["id"], actor("maker-1"), None, "mandirmitra"
        )
    assert exc.value.status_code == 409

    approved = await mandir_router.approve_mandir_refund_request(
        refund["id"], actor("approver-1"), None, "mandirmitra"
    )
    assert approved["status"] == "approved_pending_settlement"
    assert approved["approved_by"] != refund["created_by"]

    seen = {}

    async def reverse(_session, **kwargs):
        seen["reverse"] = kwargs
        return SimpleNamespace(id=2001), True

    async def audit(**_kwargs):
        return None

    monkeypatch.setattr(mandir_router, "_reverse_mandir_source_journal", reverse)
    monkeypatch.setattr(mandir_router, "log_audit_event", audit)

    with pytest.raises(HTTPException) as exc:
        await mandir_router.settle_mandir_refund_request(
            refund["id"], {"refund_mode": "UPI"}, SimpleNamespace(),
            actor("cashier-1"), None, "mandirmitra",
        )
    assert exc.value.status_code == 400

    store["mandir_refund_requests"].fail_next_update = True
    with pytest.raises(RuntimeError):
        await mandir_router.settle_mandir_refund_request(
            refund["id"],
            {"refund_mode": "UPI", "refund_reference": "UPI-RFD-1", "settlement_date": "2026-07-13"},
            SimpleNamespace(), actor("cashier-1"), None, "mandirmitra",
        )
    assert store["mandir_donations"].docs[0]["status"] == "reversed"
    assert seen["reverse"]["source_key"] == "don_don-1"

    settled = await mandir_router.settle_mandir_refund_request(
        refund["id"],
        {"refund_mode": "UPI", "refund_reference": "UPI-RFD-1", "settlement_date": "2026-07-13"},
        SimpleNamespace(), actor("cashier-1"), None, "mandirmitra",
    )
    assert settled["status"] == "settled"
    assert settled["reversal_journal_id"] == 2001
    assert settled["refund_reference"] == "UPI-RFD-1"

    repeated = await mandir_router.settle_mandir_refund_request(
        refund["id"], {"refund_mode": "UPI", "refund_reference": "UPI-RFD-1"},
        SimpleNamespace(), actor("cashier-1"), None, "mandirmitra",
    )
    assert repeated["_idempotent"] is True


@pytest.mark.asyncio
async def test_refund_rejection_and_cross_tenant_isolation(store):
    with pytest.raises(HTTPException) as exc:
        await mandir_router.create_mandir_refund_request(
            {"source_kind": "donation", "source_id": "other-don", "reason": "Invalid tenant"},
            actor("maker-1"), None, "mandirmitra",
        )
    assert exc.value.status_code == 404

    refund = await mandir_router.create_mandir_refund_request(
        {"source_kind": "seva", "source_id": "seva-1", "reason": "Devotee cancelled"},
        actor("maker-1"), None, "mandirmitra",
    )
    rejected = await mandir_router.reject_mandir_refund_request(
        refund["id"], {"reason": "Service already performed"}, actor("reviewer-1"), None, "mandirmitra"
    )
    assert rejected["status"] == "rejected"
    assert store["mandir_seva_bookings"].docs[0]["status"] == "confirmed"

    repeated = await mandir_router.reject_mandir_refund_request(
        refund["id"], {"reason": "Repeated"}, actor("reviewer-1"), None, "mandirmitra"
    )
    assert repeated["_idempotent"] is True


@pytest.mark.asyncio
async def test_refund_report_and_csv_are_tenant_scoped(store):
    local = await mandir_router.create_mandir_refund_request(
        {"source_kind": "seva", "source_id": "seva-1", "reason": "Schedule conflict"},
        actor("maker-1"), None, "mandirmitra",
    )
    store["mandir_refund_requests"].docs.append({
        **local, "id": "other-refund", "tenant_id": "temple-2", "receipt_number": "OTHER-RECEIPT",
    })
    # Report filters by refund created_at date; use the live stamp from create.
    today = datetime.fromisoformat(str(local["created_at"]).replace("Z", "+00:00")).date()
    report = await mandir_router.mandir_report_refunds(
        today, today, actor("admin-1"), None, "mandirmitra"
    )
    assert report["count"] == 1
    assert report["amount_by_status"]["pending_approval"] == 75.5
    assert all(row["tenant_id"] == "temple-1" for row in report["items"])

    exported = await mandir_router.mandir_export_refunds_csv(
        today, today, actor("admin-1"), None, "mandirmitra"
    )
    body = exported.body.decode("utf-8")
    assert "SEV-0000001" in body
    assert "OTHER-RECEIPT" not in body
