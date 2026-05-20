from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

import app.modules.temple.service as temple_service
from app.modules.temple.schemas import DonationCreateRequest, SevaCollectionCreateRequest


class FakeDonationsCollection:
    def __init__(self):
        self.inserted = []
        self.deleted = []

    async def insert_one(self, doc):
        self.inserted.append(doc)
        return SimpleNamespace(inserted_id="mongo-id")

    async def delete_one(self, query):
        self.deleted.append(query)
        return SimpleNamespace(deleted_count=1)


@pytest.mark.asyncio
async def test_record_donation_posts_journal_with_mitrabooks_erp_app_key(monkeypatch):
    donations = FakeDonationsCollection()
    captured = {}

    monkeypatch.setattr(temple_service, "get_collection", lambda name: donations)
    monkeypatch.setattr(temple_service, "uuid4", lambda: "donation-1")

    async def fake_post_journal_entry(session, **kwargs):
        captured["session"] = session
        captured.update(kwargs)
        return SimpleNamespace(id=77), True

    monkeypatch.setattr(temple_service, "post_journal_entry", fake_post_journal_entry)

    payload = DonationCreateRequest(
        amount=Decimal("501.00"),
        donor_name="ERP Donor",
        payment_mode="bank",
        donated_on=date(2026, 5, 19),
        reference="ERP-DON-1",
        bank_account_id=101,
        donation_income_account_id=202,
    )

    result = await temple_service.record_donation(
        session=object(),
        tenant_id="tenant-temple",
        app_key="mitrabooks",
        created_by="user-1",
        payload=payload,
    )

    assert captured["app_key"] == "mitrabooks"
    assert captured["tenant_id"] == "tenant-temple"
    assert captured["idempotency_key"] == "donation:donation-1"
    assert result["app_key"] == "mitrabooks"
    assert donations.inserted[0]["app_key"] == "mitrabooks"
    assert donations.inserted[0]["amount"] == "501.00"
    assert donations.deleted == []


@pytest.mark.asyncio
async def test_record_donation_rolls_back_domain_record_when_journal_post_fails(monkeypatch):
    donations = FakeDonationsCollection()

    monkeypatch.setattr(temple_service, "get_collection", lambda name: donations)
    monkeypatch.setattr(temple_service, "uuid4", lambda: "donation-rollback")

    async def fake_post_journal_entry(_session, **_kwargs):
        raise RuntimeError("journal failed")

    monkeypatch.setattr(temple_service, "post_journal_entry", fake_post_journal_entry)

    payload = DonationCreateRequest(
        amount=Decimal("101.00"),
        donor_name="Rollback Donor",
        payment_mode="bank",
        donated_on=date(2026, 5, 19),
        reference="ERP-DON-ROLLBACK",
        bank_account_id=101,
        donation_income_account_id=202,
    )

    with pytest.raises(RuntimeError, match="journal failed"):
        await temple_service.record_donation(
            session=object(),
            tenant_id="tenant-temple",
            app_key="mitrabooks",
            created_by="user-1",
            payload=payload,
        )

    assert donations.deleted == [
        {"donation_id": "donation-rollback", "tenant_id": "tenant-temple"}
    ]


@pytest.mark.asyncio
async def test_record_seva_collection_posts_journal_with_mitrabooks_erp_app_key(monkeypatch):
    seva_collections = FakeDonationsCollection()
    captured = {}

    monkeypatch.setattr(temple_service, "get_collection", lambda name: seva_collections)
    monkeypatch.setattr(temple_service, "uuid4", lambda: "seva-collection-1")

    async def fake_post_journal_entry(session, **kwargs):
        captured["session"] = session
        captured.update(kwargs)
        return SimpleNamespace(id=88), True

    monkeypatch.setattr(temple_service, "post_journal_entry", fake_post_journal_entry)

    payload = SevaCollectionCreateRequest(
        amount=Decimal("1001.00"),
        seva_name="Archana",
        devotee_name="ERP Devotee",
        payment_mode="bank",
        collected_on=date(2026, 5, 19),
        reference="ERP-SEVA-1",
        bank_account_id=101,
        seva_income_account_id=303,
    )

    result = await temple_service.record_seva_collection(
        session=object(),
        tenant_id="tenant-temple",
        app_key="mitrabooks",
        created_by="user-1",
        payload=payload,
    )

    assert captured["app_key"] == "mitrabooks"
    assert captured["tenant_id"] == "tenant-temple"
    assert captured["idempotency_key"] == "seva:seva-collection-1"
    assert result["app_key"] == "mitrabooks"
    assert result["journal_entry_id"] == 88
    assert seva_collections.inserted[0]["app_key"] == "mitrabooks"
    assert seva_collections.inserted[0]["seva_name"] == "Archana"
    assert seva_collections.inserted[0]["amount"] == "1001.00"
    assert seva_collections.deleted == []


@pytest.mark.asyncio
async def test_record_seva_collection_rolls_back_domain_record_when_journal_post_fails(monkeypatch):
    seva_collections = FakeDonationsCollection()

    monkeypatch.setattr(temple_service, "get_collection", lambda name: seva_collections)
    monkeypatch.setattr(temple_service, "uuid4", lambda: "seva-rollback")

    async def fake_post_journal_entry(_session, **_kwargs):
        raise RuntimeError("journal failed")

    monkeypatch.setattr(temple_service, "post_journal_entry", fake_post_journal_entry)

    payload = SevaCollectionCreateRequest(
        amount=Decimal("251.00"),
        seva_name="Kumkumarchane",
        devotee_name="Rollback Devotee",
        payment_mode="bank",
        collected_on=date(2026, 5, 19),
        reference="ERP-SEVA-ROLLBACK",
        bank_account_id=101,
        seva_income_account_id=303,
    )

    with pytest.raises(RuntimeError, match="journal failed"):
        await temple_service.record_seva_collection(
            session=object(),
            tenant_id="tenant-temple",
            app_key="mitrabooks",
            created_by="user-1",
            payload=payload,
        )

    assert seva_collections.deleted == [
        {"seva_collection_id": "seva-rollback", "tenant_id": "tenant-temple"}
    ]
