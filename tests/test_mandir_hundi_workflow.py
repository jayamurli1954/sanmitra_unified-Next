from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import app.modules.mandir_compat.router as mandir_router


class FakeCursor:
    def __init__(self, docs): self.docs = list(docs)
    def sort(self, *_args): return self
    async def to_list(self, length=None): return list(self.docs if length is None else self.docs[:length])


class FakeCollection:
    def __init__(self): self.docs = []
    async def insert_one(self, doc): self.docs.append(dict(doc))
    async def find_one(self, query):
        return next((dict(row) for row in self.docs if all(row.get(k) == v for k, v in query.items())), None)
    def find(self, query):
        return FakeCursor([dict(row) for row in self.docs if all(row.get(k) == v for k, v in query.items())])
    async def update_one(self, query, update, **_kwargs):
        for row in self.docs:
            if all(row.get(k) == v for k, v in query.items()):
                row.update(update.get("$set", {}))
                return SimpleNamespace(modified_count=1)
        return SimpleNamespace(modified_count=0)


@pytest.fixture()
def store(monkeypatch):
    collections = {"mandir_hundi_masters": FakeCollection(), "mandir_hundi_openings": FakeCollection()}
    monkeypatch.setattr(mandir_router, "get_collection", lambda name: collections[name])
    return collections


def actor(user_id, role="tenant_admin"):
    return {"sub": user_id, "tenant_id": "temple-1", "app_key": "mandirmitra", "role": role}


@pytest.mark.asyncio
async def test_hundi_maker_checker_posts_balanced_journal_and_reverses(store, monkeypatch):
    master = await mandir_router.create_mandir_hundi_master(
        {"name": "Main Hundi"}, actor("admin-1"), None, "mandirmitra"
    )
    opening = await mandir_router.create_mandir_hundi_opening(
        {"hundi_id": master["id"], "amount": "1250.55", "counted_on": "2026-07-12", "witness": "Trustee Rao"},
        actor("maker-1", "operator"), None, "mandirmitra",
    )
    assert opening["status"] == "pending_approval"
    assert opening["amount"] == "1250.55"

    seen = {}
    async def noop(*_args, **_kwargs): return None
    async def debit(*_args, **_kwargs): return 11002
    async def income(*_args, **_kwargs): return 44002
    async def post(**kwargs):
        seen["post"] = kwargs
        return SimpleNamespace(id=701), True
    async def reverse(_session, **kwargs):
        seen["reverse"] = kwargs
        return SimpleNamespace(id=702), True

    monkeypatch.setattr(mandir_router, "_ensure_default_mandir_sql_accounts_safe", noop)
    monkeypatch.setattr(mandir_router, "_resolve_or_create_mandir_account", debit)
    monkeypatch.setattr(mandir_router, "_resolve_mandir_income_account", income)
    monkeypatch.setattr(mandir_router, "post_journal_entry", post)
    monkeypatch.setattr(mandir_router, "_reverse_mandir_source_journal", reverse)

    posted = await mandir_router.approve_mandir_hundi_opening(
        opening["id"], SimpleNamespace(), actor("admin-1"), None, "mandirmitra"
    )
    payload = seen["post"]["payload"]
    assert posted["status"] == "posted"
    assert payload.lines[0].debit == payload.lines[1].credit
    assert payload.lines[0].account_id == 11002
    assert payload.lines[1].account_id == 44002
    assert seen["post"]["idempotency_key"] == f"hundi_{opening['id']}"

    repeated = await mandir_router.approve_mandir_hundi_opening(
        opening["id"], SimpleNamespace(), actor("admin-1"), None, "mandirmitra"
    )
    assert repeated["_idempotent"] is True

    reversed_row = await mandir_router.cancel_mandir_hundi_opening(
        opening["id"], {"reason": "Counting correction"}, SimpleNamespace(), actor("admin-2"), None, "mandirmitra"
    )
    assert reversed_row["status"] == "reversed"
    assert reversed_row["reversal_journal_id"] == 702
    assert seen["reverse"]["source_key"] == f"hundi_{opening['id']}"

    repeated = await mandir_router.cancel_mandir_hundi_opening(
        opening["id"], {"reason": "Counting correction"}, SimpleNamespace(), actor("admin-2"), None, "mandirmitra"
    )
    assert repeated["_idempotent"] is True


@pytest.mark.asyncio
async def test_hundi_rejects_same_maker_checker_and_cross_tenant_master(store):
    store["mandir_hundi_openings"].docs.append({
        "id": "opening-1", "tenant_id": "temple-1", "app_key": "mandirmitra", "status": "pending_approval",
        "created_by": "admin-1", "amount": "100.00", "counted_on": "2026-07-12",
    })
    with pytest.raises(HTTPException) as exc:
        await mandir_router.approve_mandir_hundi_opening(
            "opening-1", SimpleNamespace(), actor("admin-1"), None, "mandirmitra"
        )
    assert exc.value.status_code == 409

    store["mandir_hundi_masters"].docs.append({
        "id": "other-hundi", "tenant_id": "temple-2", "app_key": "mandirmitra", "active": True,
    })
    with pytest.raises(HTTPException) as exc:
        await mandir_router.create_mandir_hundi_opening(
            {"hundi_id": "other-hundi", "amount": "10.00", "witness": "Trustee"},
            actor("maker-1", "operator"), None, "mandirmitra",
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_hundi_approval_compensates_when_mongo_update_fails(store, monkeypatch):
    store["mandir_hundi_openings"].docs.append({
        "id": "opening-2", "tenant_id": "temple-1", "app_key": "mandirmitra", "status": "pending_approval",
        "created_by": "maker-1", "amount": "75.25", "counted_on": "2026-07-12", "hundi_name": "Main Hundi",
        "reference": "HUN-OPENING2",
    })
    compensated = {}

    async def noop(*_args, **_kwargs): return None
    async def account(*_args, **_kwargs): return 11002
    async def income(*_args, **_kwargs): return 44002
    async def post(**_kwargs): return SimpleNamespace(id=801), True
    async def reverse(**kwargs):
        compensated.update(kwargs)
        return SimpleNamespace(id=802), True
    async def fail_update(*_args, **_kwargs): raise RuntimeError("mongo unavailable")

    monkeypatch.setattr(mandir_router, "_ensure_default_mandir_sql_accounts_safe", noop)
    monkeypatch.setattr(mandir_router, "_resolve_or_create_mandir_account", account)
    monkeypatch.setattr(mandir_router, "_resolve_mandir_income_account", income)
    monkeypatch.setattr(mandir_router, "post_journal_entry", post)
    monkeypatch.setattr(mandir_router, "reverse_journal_entry", reverse)
    monkeypatch.setattr(store["mandir_hundi_openings"], "update_one", fail_update)

    with pytest.raises(HTTPException) as exc:
        await mandir_router.approve_mandir_hundi_opening(
            "opening-2", SimpleNamespace(), actor("admin-1"), None, "mandirmitra"
        )

    assert exc.value.status_code == 500
    assert compensated["journal_id"] == 801
    assert compensated["idempotency_key"] == "hundi_opening-2_approval_compensation"
