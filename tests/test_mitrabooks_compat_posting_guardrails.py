from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.modules.mitrabooks_compat import router as mitrabooks_router


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    def sort(self, *_args, **_kwargs):
        return self

    def limit(self, length):
        self.rows = self.rows[:length]
        return self

    async def to_list(self, length=None):
        return self.rows if length is None else self.rows[:length]


class FakeCollection:
    def __init__(self):
        self.docs = []

    async def find_one(self, query):
        for doc in self.docs:
            if all(doc.get(key) == value for key, value in query.items()):
                return doc
        return None

    def find(self, query, *_args, **_kwargs):
        rows = [doc for doc in self.docs if all(doc.get(key) == value for key, value in query.items())]
        return FakeCursor(rows)

    async def insert_one(self, doc):
        doc.setdefault("_id", f"fake-{len(self.docs) + 1}")
        self.docs.append(doc)
        return SimpleNamespace(inserted_id=doc["_id"])

    async def update_one(self, query, update):
        doc = await self.find_one(query)
        if doc and "$set" in update:
            doc.update(update["$set"])
        return SimpleNamespace(modified_count=1 if doc else 0)

    async def delete_one(self, query):
        before = len(self.docs)
        self.docs = [doc for doc in self.docs if not all(doc.get(key) == value for key, value in query.items())]
        return SimpleNamespace(deleted_count=before - len(self.docs))


@pytest.mark.asyncio
async def test_create_transaction_rolls_back_mongo_when_accounting_post_fails(monkeypatch):
    collections = {
        "mb_transactions": FakeCollection(),
        "mb_voucher_counters": FakeCollection(),
    }

    monkeypatch.setattr(mitrabooks_router, "get_collection", lambda name: collections[name])

    async def fail_post_journal_entry(**_kwargs):
        raise RuntimeError("postgres unavailable")

    monkeypatch.setattr(mitrabooks_router, "post_journal_entry", fail_post_journal_entry)

    request = SimpleNamespace(url=SimpleNamespace(path="/api/v1/mitrabooks/transactions/receipt"))
    payload = {
        "amount": "1250.00",
        "bank_account_id": 101,
        "credit_account_id": 202,
        "description": "Society maintenance collection",
    }
    current_user = {
        "sub": "user-1",
        "user_id": "user-1",
        "role": "tenant_admin",
        "tenant_id": "tenant-1",
        "app_key": "mitrabooks",
    }

    with pytest.raises(HTTPException) as exc_info:
        await mitrabooks_router.create_transaction(
            payload=payload,
            request=request,
            current_user=current_user,
            x_tenant_id=None,
            x_app_key="mitrabooks",
            session=object(),
        )

    assert exc_info.value.status_code == 500
    assert "Failed to post transaction to accounting" in str(exc_info.value.detail)
    assert collections["mb_transactions"].docs == []


def _current_user():
    return {
        "sub": "user-1",
        "user_id": "user-1",
        "role": "tenant_admin",
        "tenant_id": "tenant-1",
        "app_key": "mitrabooks",
    }


@pytest.mark.asyncio
async def test_update_transaction_blocks_posted_compat_record(monkeypatch):
    transactions = FakeCollection()
    await transactions.insert_one({
        "id": 10,
        "tenant_id": "tenant-1",
        "app_key": "mitrabooks",
        "company_id": 1,
        "status": "posted",
        "journal_entry_id": 99,
    })
    monkeypatch.setattr(mitrabooks_router, "get_collection", lambda name: transactions)

    with pytest.raises(HTTPException) as exc_info:
        await mitrabooks_router.update_transaction(
            txn_id=10,
            payload={"description": "edited after posting"},
            company_id=1,
            current_user=_current_user(),
            x_tenant_id=None,
            x_app_key="mitrabooks",
        )

    assert exc_info.value.status_code == 409
    assert "description" not in transactions.docs[0]


@pytest.mark.asyncio
async def test_delete_invoice_blocks_posted_compat_record(monkeypatch):
    invoices = FakeCollection()
    await invoices.insert_one({
        "id": 7,
        "tenant_id": "tenant-1",
        "app_key": "mitrabooks",
        "company_id": 1,
        "status": "posted",
    })
    monkeypatch.setattr(mitrabooks_router, "get_collection", lambda name: invoices)

    with pytest.raises(HTTPException) as exc_info:
        await mitrabooks_router.delete_invoice(
            invoice_id=7,
            company_id=1,
            current_user=_current_user(),
            x_tenant_id=None,
            x_app_key="mitrabooks",
        )

    assert exc_info.value.status_code == 409
    assert len(invoices.docs) == 1


@pytest.mark.asyncio
async def test_compat_invoice_posting_is_blocked_without_accounting_entry():
    with pytest.raises(HTTPException) as exc_info:
        await mitrabooks_router.post_invoice(
            invoice_id=7,
            company_id=1,
            current_user=_current_user(),
            x_tenant_id=None,
            x_app_key="mitrabooks",
        )

    assert exc_info.value.status_code == 422
    assert "does not create accounting entries" in exc_info.value.detail


@pytest.mark.asyncio
async def test_post_transaction_compensates_when_mongo_update_fails_after_journal_post(monkeypatch):
    transactions = FakeCollection()
    await transactions.insert_one(
        {
            "id": 11,
            "tenant_id": "tenant-1",
            "app_key": "mitrabooks",
            "company_id": 1,
            "status": "draft",
            "voucher_date": "2026-07-08",
            "voucher_number": "JV-000011",
            "description": "Test posting",
            "lines": [
                {"account_id": 1001, "debit": "500.00", "credit": "0.00"},
                {"account_id": 2001, "debit": "0.00", "credit": "500.00"},
            ],
        }
    )
    collections = {"mb_transactions": transactions}

    def _get_collection(name: str):
        return collections[name]

    monkeypatch.setattr(mitrabooks_router, "get_collection", _get_collection)

    async def fake_post_journal_entry(**_kwargs):
        return SimpleNamespace(id=321), True

    compensated: dict[str, bool] = {"called": False}

    async def fake_reverse_journal_entry(*_args, **_kwargs):
        compensated["called"] = True
        return SimpleNamespace(id=654), True

    async def fail_update_one(_query, _update):
        raise RuntimeError("mongo unavailable")

    monkeypatch.setattr(mitrabooks_router, "post_journal_entry", fake_post_journal_entry)
    monkeypatch.setattr(mitrabooks_router, "reverse_journal_entry", fake_reverse_journal_entry)
    monkeypatch.setattr(transactions, "update_one", fail_update_one)

    with pytest.raises(HTTPException) as exc_info:
        await mitrabooks_router.post_transaction(
            txn_id=11,
            company_id=1,
            current_user=_current_user(),
            x_tenant_id=None,
            x_app_key="mitrabooks",
            session=object(),
        )

    assert exc_info.value.status_code == 500
    assert "Failed to persist posted transaction" in str(exc_info.value.detail)
    assert compensated["called"] is True


@pytest.mark.asyncio
async def test_create_transaction_compensates_when_mongo_mark_posted_fails(monkeypatch):
    collections = {
        "mb_transactions": FakeCollection(),
        "mb_voucher_counters": FakeCollection(),
    }

    monkeypatch.setattr(mitrabooks_router, "get_collection", lambda name: collections[name])

    async def fake_post_journal_entry(**_kwargs):
        return SimpleNamespace(id=4321), True

    compensated: dict[str, bool] = {"called": False}

    async def fake_reverse_journal_entry(*_args, **_kwargs):
        compensated["called"] = True
        return SimpleNamespace(id=9999), True

    async def fail_update_one(_query, _update):
        raise RuntimeError("mongo write failed")

    monkeypatch.setattr(mitrabooks_router, "post_journal_entry", fake_post_journal_entry)
    monkeypatch.setattr(mitrabooks_router, "reverse_journal_entry", fake_reverse_journal_entry)
    monkeypatch.setattr(collections["mb_transactions"], "update_one", fail_update_one)

    request = SimpleNamespace(url=SimpleNamespace(path="/api/v1/mitrabooks/transactions/journal"))
    payload = {
        "voucher_number": "JV-TEST-001",
        "voucher_date": "2026-07-08",
        "description": "Posting + mongo failure",
        "lines": [
            {"account_id": 101, "debit": "250.00", "credit": "0.00"},
            {"account_id": 202, "debit": "0.00", "credit": "250.00"},
        ],
    }

    with pytest.raises(HTTPException) as exc_info:
        await mitrabooks_router.create_transaction(
            payload=payload,
            request=request,
            current_user=_current_user(),
            x_tenant_id=None,
            x_app_key="mitrabooks",
            session=object(),
        )

    assert exc_info.value.status_code == 500
    assert "Failed to post transaction to accounting" in str(exc_info.value.detail)
    assert compensated["called"] is True
    assert collections["mb_transactions"].docs == []


@pytest.mark.asyncio
async def test_reverse_transaction_compensates_when_mongo_update_fails(monkeypatch):
    transactions = FakeCollection()
    await transactions.insert_one(
        {
            "id": 13,
            "tenant_id": "tenant-1",
            "app_key": "mitrabooks",
            "company_id": 1,
            "status": "posted",
            "voucher_date": "2026-07-08",
            "voucher_number": "RV-000013",
            "lines": [
                {"account_id": 1001, "debit": "700.00", "credit": "0.00"},
                {"account_id": 2001, "debit": "0.00", "credit": "700.00"},
            ],
            "total_debit": "700.00",
            "total_credit": "700.00",
        }
    )
    monkeypatch.setattr(mitrabooks_router, "get_collection", lambda _name: transactions)

    async def fake_post_journal_entry(**_kwargs):
        return SimpleNamespace(id=4567), True

    compensated: dict[str, bool] = {"called": False}

    async def fake_reverse_journal_entry(*_args, **_kwargs):
        compensated["called"] = True
        return SimpleNamespace(id=4568), True

    async def fail_update_one(_query, _update):
        raise RuntimeError("mongo update failed")

    monkeypatch.setattr(mitrabooks_router, "post_journal_entry", fake_post_journal_entry)
    monkeypatch.setattr(mitrabooks_router, "reverse_journal_entry", fake_reverse_journal_entry)
    monkeypatch.setattr(transactions, "update_one", fail_update_one)

    with pytest.raises(HTTPException) as exc_info:
        await mitrabooks_router.reverse_transaction(
            txn_id=13,
            payload={"reason": "operator request"},
            reason=None,
            company_id=1,
            current_user=_current_user(),
            x_tenant_id=None,
            x_app_key="mitrabooks",
            session=object(),
        )

    assert exc_info.value.status_code == 500
    assert "Failed to persist reversal metadata" in str(exc_info.value.detail)
    assert compensated["called"] is True
