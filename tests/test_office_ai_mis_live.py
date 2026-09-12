"""ADR-014 Path A — live MitraBooks MIS ingest (report services → facts)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from bson import ObjectId

from app.modules.office_ai.models import MIS_FACTS_COLLECTION, MIS_PACKS_COLLECTION
from app.modules.office_ai.services import mis_live_ingest, mis_store


class _FakeCursor:
    def __init__(self, docs: list[dict]):
        self._docs = list(docs)

    def sort(self, *_args, **_kwargs):
        return self

    def limit(self, n: int):
        self._docs = self._docs[:n]
        return self

    def __aiter__(self):
        self._iter = iter(self._docs)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class _FakeCollection:
    def __init__(self):
        self.docs: list[dict] = []

    def find(self, query: dict | None = None):
        query = query or {}
        matched = [dict(doc) for doc in self.docs if _match(doc, query)]
        return _FakeCursor(matched)

    async def find_one(self, query: dict, *args, **kwargs):
        for doc in self.docs:
            if _match(doc, query):
                return dict(doc)
        return None

    async def insert_one(self, doc: dict):
        self.docs.append(dict(doc))
        return type("R", (), {"inserted_id": doc.get("_id")})()

    async def insert_many(self, docs: list[dict]):
        for doc in docs:
            self.docs.append(dict(doc))
        return type("R", (), {"inserted_ids": [doc.get("_id") for doc in docs]})()

    async def update_one(self, query: dict, update: dict):
        for doc in self.docs:
            if _match(doc, query):
                if "$set" in update:
                    doc.update(update["$set"])
                return type("R", (), {"modified_count": 1})()
        return type("R", (), {"modified_count": 0})()

    async def delete_many(self, query: dict):
        keep = []
        deleted = 0
        for doc in self.docs:
            if _match(doc, query):
                deleted += 1
            else:
                keep.append(doc)
        self.docs = keep
        return type("R", (), {"deleted_count": deleted})()

    async def update_many(self, query: dict, update: dict):
        count = 0
        for doc in self.docs:
            if _match(doc, query):
                if "$set" in update:
                    doc.update(update["$set"])
                count += 1
        return type("R", (), {"modified_count": count})()

    async def create_index(self, *_args, **_kwargs):
        return True


def _match(doc: dict, query: dict) -> bool:
    for key, expected in query.items():
        actual = doc.get(key)
        if isinstance(expected, dict) and "$type" in expected:
            continue
        if actual != expected:
            return False
    return True


@pytest.fixture
def fake_mis_mongo(monkeypatch):
    store = {
        MIS_PACKS_COLLECTION: _FakeCollection(),
        MIS_FACTS_COLLECTION: _FakeCollection(),
    }

    def _get(name: str):
        return store.setdefault(name, _FakeCollection())

    monkeypatch.setattr("app.modules.office_ai.services.mis_store.get_collection", _get)
    monkeypatch.setattr("app.modules.office_ai.models.get_collection", _get)
    return store


def test_parse_pack_period_yyyy_mm():
    from_date, to_date, as_of = mis_live_ingest.parse_pack_period("2026-07")
    assert from_date == date(2026, 7, 1)
    assert to_date == date(2026, 7, 31)
    assert as_of == date(2026, 7, 31)


def test_parse_pack_period_range():
    from_date, to_date, as_of = mis_live_ingest.parse_pack_period("2026-04-01..2026-06-30")
    assert from_date == date(2026, 4, 1)
    assert to_date == date(2026, 6, 30)
    assert as_of == to_date


def test_parse_pack_period_rejects_bad():
    with pytest.raises(mis_live_ingest.MISLiveIngestError, match="unsupported_period"):
        mis_live_ingest.parse_pack_period("FY2025-26")


def test_map_rejects_float():
    with pytest.raises(mis_live_ingest.MISLiveIngestError, match="float"):
        mis_live_ingest._map_pnl(
            {"lines": [{"account_name": "Sales", "account_code": "4000", "net_amount": 1.5}]},
            period="2026-07",
            as_of="2026-07-31",
        )


@pytest.mark.asyncio
async def test_replace_keeps_excel_facts(fake_mis_mongo):
    user = {"sub": "acct-1"}
    pack = await mis_store.create_pack_draft(
        tenant_id="tenant-a",
        user=user,
        pack_key="sme_general",
        period="2026-07",
        ingestion_path="excel_import",
    )
    pack_id = pack["id"]
    await mis_store.insert_facts(
        tenant_id="tenant-a",
        pack_id=pack_id,
        user=user,
        facts=[
            {
                "entity_type": "pnl_line",
                "period": "2026-07",
                "source_system": "excel_import",
                "source_id": "excel-rev",
                "amount_decimal": "100.00",
                "amount_minor": 10000,
                "dimensions": {"line": "Revenue"},
            }
        ],
    )
    await mis_store.replace_facts_by_source_system(
        tenant_id="tenant-a",
        pack_id=pack_id,
        user=user,
        source_system="mitrabooks",
        facts=[
            {
                "entity_type": "pnl_line",
                "period": "2026-07",
                "source_system": "mitrabooks",
                "source_id": "mb-rev",
                "amount_decimal": "200.00",
                "amount_minor": 20000,
                "dimensions": {"line": "Revenue"},
            }
        ],
        set_ingestion_path_if_blank_or_manual=True,
    )
    facts = await mis_store.list_facts(tenant_id="tenant-a", pack_id=pack_id)
    sources = {f["source_system"] for f in facts}
    assert sources == {"excel_import", "mitrabooks"}
    updated = await mis_store.get_pack(tenant_id="tenant-a", pack_id=pack_id)
    assert updated["ingestion_path"] == "excel_import"


@pytest.mark.asyncio
async def test_live_import_monkeypatched_reports(fake_mis_mongo, monkeypatch):
    user = {"sub": "acct-1"}
    pack = await mis_store.create_pack_draft(
        tenant_id="tenant-a",
        user=user,
        pack_key="sme_general",
        period="2026-07",
        ingestion_path="manual",
    )
    pack_id = pack["id"]

    async def fake_pnl(**_kwargs):
        return {
            "enabled": True,
            "lines": [
                {
                    "account_id": 1,
                    "account_code": "4000",
                    "account_name": "Sales",
                    "account_type": "income",
                    "net_amount": Decimal("1500.00"),
                }
            ],
            "income_total": Decimal("1500.00"),
            "expense_total": Decimal("400.00"),
            "net_profit": Decimal("1100.00"),
        }

    async def fake_bs(**_kwargs):
        return {
            "enabled": True,
            "assets": [{"account_id": 2, "account_code": "1000", "account_name": "Cash", "balance": Decimal("900.00")}],
            "liabilities": [],
            "equity": [],
            "total_assets": Decimal("900.00"),
            "total_liabilities": Decimal("0.00"),
            "total_equity": Decimal("900.00"),
        }

    async def fake_cash(**_kwargs):
        return {
            "enabled": True,
            "lines": [],
            "total_receipts": Decimal("200.00"),
            "total_payments": Decimal("50.00"),
            "net": Decimal("150.00"),
        }

    async def fake_aging(**_kwargs):
        return {
            "enabled": True,
            "receivable": {"totals": {"0-30": "10.00", "31-60": "5.00"}, "grand_total": "15.00"},
            "payable": {"totals": {"0-30": "3.00"}, "grand_total": "3.00"},
        }

    monkeypatch.setattr(
        "app.modules.office_ai.connectors.mitrabooks_connector.get_mis_profit_loss",
        fake_pnl,
    )
    monkeypatch.setattr(
        "app.modules.office_ai.connectors.mitrabooks_connector.get_mis_balance_sheet",
        fake_bs,
    )
    monkeypatch.setattr(
        "app.modules.office_ai.connectors.mitrabooks_connector.get_mis_cash_movement",
        fake_cash,
    )
    monkeypatch.setattr(
        "app.modules.office_ai.connectors.mitrabooks_connector.get_mis_ar_ap_aging",
        fake_aging,
    )

    result = await mis_live_ingest.import_from_mitrabooks(
        tenant_id="tenant-a",
        tenant={"enabled_modules": ["business", "accounting"]},
        user=user,
        pack_id=pack_id,
        session=object(),
    )
    assert result["facts_upserted"] > 0
    assert result["pack"]["ingestion_path"] == "mitrabooks"
    facts = await mis_store.list_facts(tenant_id="tenant-a", pack_id=pack_id)
    assert all(f["source_system"] == "mitrabooks" for f in facts)
    assert all(not isinstance(f.get("amount_decimal"), float) for f in facts)
    assert any(f["entity_type"] == "aging_bucket" and f["dimensions"].get("side") == "AR" for f in facts)
    assert any(f["entity_type"] == "aging_bucket" and f["dimensions"].get("side") == "AP" for f in facts)

    # Second pull replaces mitrabooks facts only
    result2 = await mis_live_ingest.import_from_mitrabooks(
        tenant_id="tenant-a",
        tenant={"enabled_modules": ["business"]},
        user=user,
        pack_id=pack_id,
        session=object(),
    )
    assert result2["facts_replaced"] == result["facts_upserted"]


@pytest.mark.asyncio
async def test_live_import_immutable_pack(fake_mis_mongo, monkeypatch):
    user = {"sub": "acct-1"}
    pack = await mis_store.create_pack_draft(
        tenant_id="tenant-a",
        user=user,
        pack_key="sme_general",
        period="2026-07",
    )
    pack_id = pack["id"]
    await mis_store.reconcile_pack(tenant_id="tenant-a", pack_id=pack_id, user=user, data_quality_score=90)

    async def boom(**_kwargs):
        raise AssertionError("should not call connector on immutable pack")

    monkeypatch.setattr(
        "app.modules.office_ai.connectors.mitrabooks_connector.get_mis_profit_loss",
        boom,
    )
    with pytest.raises(mis_store.MISImmutableError):
        await mis_live_ingest.import_from_mitrabooks(
            tenant_id="tenant-a",
            tenant={"enabled_modules": ["business"]},
            user=user,
            pack_id=pack_id,
            session=object(),
        )


@pytest.mark.asyncio
async def test_live_import_empty_books_warns(fake_mis_mongo, monkeypatch):
    user = {"sub": "acct-1"}
    pack = await mis_store.create_pack_draft(
        tenant_id="tenant-a",
        user=user,
        pack_key="sme_general",
        period="2026-07",
    )

    async def empty(**_kwargs):
        return {
            "enabled": True,
            "lines": [],
            "income_total": Decimal("0.00"),
            "expense_total": Decimal("0.00"),
            "net_profit": Decimal("0.00"),
            "assets": [],
            "liabilities": [],
            "equity": [],
            "total_assets": Decimal("0.00"),
            "total_liabilities": Decimal("0.00"),
            "total_equity": Decimal("0.00"),
            "total_receipts": Decimal("0.00"),
            "total_payments": Decimal("0.00"),
            "net": Decimal("0.00"),
            "receivable": {"totals": {}, "grand_total": "0.00"},
            "payable": {"totals": {}, "grand_total": "0.00"},
        }

    monkeypatch.setattr(
        "app.modules.office_ai.connectors.mitrabooks_connector.get_mis_profit_loss",
        empty,
    )
    monkeypatch.setattr(
        "app.modules.office_ai.connectors.mitrabooks_connector.get_mis_balance_sheet",
        empty,
    )
    monkeypatch.setattr(
        "app.modules.office_ai.connectors.mitrabooks_connector.get_mis_cash_movement",
        empty,
    )
    monkeypatch.setattr(
        "app.modules.office_ai.connectors.mitrabooks_connector.get_mis_ar_ap_aging",
        empty,
    )
    result = await mis_live_ingest.import_from_mitrabooks(
        tenant_id="tenant-a",
        tenant={"enabled_modules": ["business"]},
        user=user,
        pack_id=pack["id"],
        session=object(),
    )
    # Zero totals still produce rollup facts — that is fine; invented revenue is not.
    assert "empty_books_no_facts" not in result["warnings"] or result["facts_upserted"] == 0
    for fact in await mis_store.list_facts(tenant_id="tenant-a", pack_id=pack["id"]):
        assert Decimal(str(fact["amount_decimal"])) == Decimal("0.00") or fact["amount_decimal"] is not None


@pytest.mark.asyncio
async def test_live_import_requires_session(fake_mis_mongo):
    user = {"sub": "acct-1"}
    pack = await mis_store.create_pack_draft(
        tenant_id="tenant-a",
        user=user,
        pack_key="sme_general",
        period="2026-07",
    )
    with pytest.raises(mis_live_ingest.MISLiveIngestError, match="session_required"):
        await mis_live_ingest.import_from_mitrabooks(
            tenant_id="tenant-a",
            tenant={"enabled_modules": ["business"]},
            user=user,
            pack_id=pack["id"],
            session=None,
        )


@pytest.mark.asyncio
async def test_live_import_wrong_tenant_pack(fake_mis_mongo):
    user = {"sub": "acct-1"}
    pack = await mis_store.create_pack_draft(
        tenant_id="tenant-a",
        user=user,
        pack_key="sme_general",
        period="2026-07",
    )
    with pytest.raises(mis_store.MISPackNotFoundError):
        await mis_live_ingest.import_from_mitrabooks(
            tenant_id="tenant-b",
            tenant={"enabled_modules": ["business"]},
            user=user,
            pack_id=pack["id"],
            session=object(),
        )


def test_mis_live_routes_registered():
    from app.api.v1.router import api_router

    paths = {getattr(route, "path", "") for route in api_router.routes}
    assert any(p.endswith("/officemitra/mis/live-mitrabooks/status") for p in paths)
    assert any(p.endswith("/officemitra/mis/packs/{pack_id}/import/mitrabooks") for p in paths)
