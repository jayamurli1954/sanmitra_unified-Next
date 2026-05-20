from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import post_journal_entry
from app.modules.temple.schemas import DonationCreateRequest, SevaCollectionCreateRequest
from app.db.mongo import get_collection

DONATIONS_COLLECTION = "temple_donations"
SEVA_COLLECTIONS_COLLECTION = "temple_seva_collections"
MONEY_QUANT = Decimal("0.01")


def _money(value: Decimal | str | int) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANT)


async def ensure_donations_indexes() -> None:
    donations = get_collection(DONATIONS_COLLECTION)
    await donations.create_index([("tenant_id", 1), ("donated_on", -1)])
    await donations.create_index("donation_id", unique=True)
    seva_collections = get_collection(SEVA_COLLECTIONS_COLLECTION)
    await seva_collections.create_index([("tenant_id", 1), ("collected_on", -1)])
    await seva_collections.create_index("seva_collection_id", unique=True)


async def record_donation(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    created_by: str,
    payload: DonationCreateRequest,
):
    donations = get_collection(DONATIONS_COLLECTION)

    donation_id = str(uuid4())
    amount = _money(payload.amount)
    donation_doc = {
        "donation_id": donation_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "amount": str(amount),
        "donor_name": payload.donor_name,
        "payment_mode": payload.payment_mode,
        "donated_on": payload.donated_on.isoformat(),
        "reference": payload.reference,
        "created_by": created_by,
        "created_at": datetime.now(timezone.utc),
    }

    await donations.insert_one(donation_doc)

    try:
        journal_payload = JournalPostRequest(
            entry_date=payload.donated_on,
            description=f"Donation receipt {donation_id}",
            reference=payload.reference or donation_id,
            lines=[
                JournalLineIn(
                    account_id=payload.bank_account_id,
                    debit=amount,
                    credit=Decimal("0"),
                ),
                JournalLineIn(
                    account_id=payload.donation_income_account_id,
                    debit=Decimal("0"),
                    credit=amount,
                ),
            ],
        )
        journal_entry, created = await post_journal_entry(
            session,
            app_key=app_key,
            tenant_id=tenant_id,
            created_by=created_by,
            payload=journal_payload,
            idempotency_key=f"donation:{donation_id}",
        )
    except Exception:
        # Compensating rollback for cross-DB write failure.
        await donations.delete_one({"donation_id": donation_id, "tenant_id": tenant_id})
        raise

    return {
        "donation_id": donation_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "amount": payload.amount,
        "journal_entry_id": journal_entry.id,
        "created": created,
    }


async def record_seva_collection(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    created_by: str,
    payload: SevaCollectionCreateRequest,
):
    seva_collections = get_collection(SEVA_COLLECTIONS_COLLECTION)

    seva_collection_id = str(uuid4())
    amount = _money(payload.amount)
    collection_doc = {
        "seva_collection_id": seva_collection_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "amount": str(amount),
        "seva_name": payload.seva_name,
        "devotee_name": payload.devotee_name,
        "payment_mode": payload.payment_mode,
        "collected_on": payload.collected_on.isoformat(),
        "reference": payload.reference,
        "created_by": created_by,
        "created_at": datetime.now(timezone.utc),
    }

    await seva_collections.insert_one(collection_doc)

    try:
        journal_payload = JournalPostRequest(
            entry_date=payload.collected_on,
            description=f"Seva collection {seva_collection_id}: {payload.seva_name}",
            reference=payload.reference or seva_collection_id,
            lines=[
                JournalLineIn(
                    account_id=payload.bank_account_id,
                    debit=amount,
                    credit=Decimal("0"),
                ),
                JournalLineIn(
                    account_id=payload.seva_income_account_id,
                    debit=Decimal("0"),
                    credit=amount,
                ),
            ],
        )
        journal_entry, created = await post_journal_entry(
            session,
            app_key=app_key,
            tenant_id=tenant_id,
            created_by=created_by,
            payload=journal_payload,
            idempotency_key=f"seva:{seva_collection_id}",
        )
    except Exception:
        # Compensating rollback for cross-DB write failure.
        await seva_collections.delete_one(
            {"seva_collection_id": seva_collection_id, "tenant_id": tenant_id}
        )
        raise

    return {
        "seva_collection_id": seva_collection_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "amount": payload.amount,
        "journal_entry_id": journal_entry.id,
        "created": created,
    }
