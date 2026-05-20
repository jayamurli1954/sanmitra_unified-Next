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
