from datetime import datetime, timezone
from decimal import Decimal
import logging
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models import Account
from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import post_journal_entry, reverse_journal_entry
from app.db.mongo import get_collection
from app.modules.housing.schemas import MaintenanceCollectionCreateRequest

MAINTENANCE_COLLECTIONS = "housing_maintenance_collections"
MAINTENANCE_BILLS = "housing_maintenance_bills"
MONEY_QUANT = Decimal("0.01")
DEFAULT_BANK_ACCOUNT_CODES = ("11010", "11001")
DEFAULT_MEMBER_DUES_ACCOUNT_CODE = "12001"
_logger = logging.getLogger(__name__)


def _money(value: Decimal | str | int) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANT)


def _bill_paid_amount(row: dict) -> Decimal:
    status = str(row.get("status") or row.get("payment_status") or "").strip().lower()
    if status in {"paid", "collected", "settled"}:
        return _money(row.get("amount") or 0)
    return _money(row.get("paid_amount") or row.get("amount_paid") or row.get("collected_amount") or 0)


async def _find_account_id_by_codes(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    codes: tuple[str, ...],
) -> int:
    result = await session.execute(
        select(Account.id)
        .where(
            Account.tenant_id == tenant_id,
            Account.app_key == app_key,
            Account.accounting_entity_id == "primary",
            Account.code.in_(codes),
        )
        .order_by(Account.code.asc())
        .limit(1)
    )
    account_id = result.scalar_one_or_none()
    if account_id is None:
        raise HTTPException(
            status_code=422,
            detail=f"Required GruhaMitra accounting account not found: one of {', '.join(codes)}",
        )
    return int(account_id)


async def ensure_maintenance_indexes() -> None:
    collections = get_collection(MAINTENANCE_COLLECTIONS)
    await collections.create_index([("tenant_id", 1), ("app_key", 1), ("collected_on", -1)])
    await collections.create_index([("tenant_id", 1), ("app_key", 1), ("collection_id", 1)], unique=True)


async def record_maintenance_collection(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    created_by: str,
    payload: MaintenanceCollectionCreateRequest,
):
    collections = get_collection(MAINTENANCE_COLLECTIONS)
    bills = get_collection(MAINTENANCE_BILLS)

    collection_id = str(uuid4())
    amount = _money(payload.amount)
    now = datetime.now(timezone.utc)
    bill_id = str(payload.bill_id or "").strip() or None
    new_paid_amount: Decimal | None = None
    outstanding_amount: Decimal | None = None
    bill_status: str | None = None

    if bill_id:
        bill = await bills.find_one({"tenant_id": tenant_id, "app_key": app_key, "id": bill_id})
        if not bill:
            raise HTTPException(status_code=404, detail="Maintenance bill not found")
        if str(bill.get("status") or "").strip().lower() == "reversed":
            raise HTTPException(status_code=400, detail="Cannot collect payment for a reversed bill")
        bill_flat = str(bill.get("flat_number") or "").strip().upper()
        requested_flat = str(payload.flat_number or "").strip().upper()
        if bill_flat and requested_flat and bill_flat != requested_flat:
            raise HTTPException(status_code=400, detail="Payment flat number does not match the selected bill")

        bill_amount = _money(bill.get("amount") or 0)
        paid_before = _bill_paid_amount(bill)
        outstanding_before = max(bill_amount - paid_before, Decimal("0.00"))
        if outstanding_before <= Decimal("0.00"):
            raise HTTPException(status_code=400, detail="Maintenance bill is already paid")
        if amount > outstanding_before:
            raise HTTPException(status_code=400, detail="Payment amount exceeds outstanding bill amount")

        new_paid_amount = (paid_before + amount).quantize(MONEY_QUANT)
        outstanding_amount = max(bill_amount - new_paid_amount, Decimal("0.00")).quantize(MONEY_QUANT)
        bill_status = "paid" if outstanding_amount == Decimal("0.00") else "partially_paid"

    bank_account_id = payload.bank_account_id
    credit_account_id = payload.maintenance_income_account_id
    if bank_account_id is None:
        bank_account_id = await _find_account_id_by_codes(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            codes=DEFAULT_BANK_ACCOUNT_CODES,
        )
    if credit_account_id is None:
        credit_account_id = await _find_account_id_by_codes(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            codes=(DEFAULT_MEMBER_DUES_ACCOUNT_CODE,) if bill_id else ("41001",),
        )

    doc = {
        "collection_id": collection_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "bill_id": bill_id,
        "amount": str(amount),
        "flat_number": payload.flat_number,
        "resident_name": payload.resident_name,
        "payment_mode": payload.payment_mode,
        "collected_on": payload.collected_on.isoformat(),
        "reference": payload.reference,
        "created_by": created_by,
        "created_at": now,
    }

    await collections.insert_one(doc)

    try:
        journal_payload = JournalPostRequest(
            entry_date=payload.collected_on,
            description=f"Maintenance collection {collection_id} for flat {payload.flat_number}",
            reference=payload.reference or collection_id,
            lines=[
                JournalLineIn(
                    account_id=bank_account_id,
                    debit=amount,
                    credit=Decimal("0"),
                ),
                JournalLineIn(
                    account_id=credit_account_id,
                    debit=Decimal("0"),
                    credit=amount,
                ),
            ],
        )
        journal_entry, created = await post_journal_entry(
            session,
            app_key=app_key,
            tenant_id=tenant_id,
            accounting_entity_id="primary",
            created_by=created_by,
            payload=journal_payload,
            idempotency_key=(
                f"maintenance-bill:{tenant_id}:{app_key}:{bill_id}:{payload.reference}"
                if bill_id and payload.reference
                else f"maintenance:{collection_id}"
            ),
        )
    except Exception:
        # Compensating rollback for cross-DB write failure.
        await collections.delete_one({"collection_id": collection_id, "tenant_id": tenant_id, "app_key": app_key})
        raise

    async def _compensate_after_posted_journal(failed_step: str) -> None:
        await collections.delete_one(
            {"collection_id": collection_id, "tenant_id": tenant_id, "app_key": app_key}
        )
        try:
            await reverse_journal_entry(
                session,
                tenant_id=tenant_id,
                journal_id=int(journal_entry.id),
                app_key=app_key,
                accounting_entity_id="primary",
                created_by=created_by,
                reason=f"Compensation after maintenance {failed_step} failure for {collection_id}",
                idempotency_key=f"maintenance-compensate:{collection_id}:{journal_entry.id}",
            )
        except Exception as reversal_exc:
            _logger.exception(
                "Maintenance compensation reversal failed for collection %s",
                collection_id,
            )
            raise HTTPException(
                status_code=500,
                detail=(
                    "Maintenance persistence failed after journal posting, and automatic "
                    "reversal also failed"
                ),
            ) from reversal_exc

    if bill_id and new_paid_amount is not None and outstanding_amount is not None and bill_status is not None:
        try:
            update_result = await bills.update_one(
                {"tenant_id": tenant_id, "app_key": app_key, "id": bill_id},
                {
                    "$set": {
                        "paid_amount": str(new_paid_amount),
                        "outstanding_amount": str(outstanding_amount),
                        "status": bill_status,
                        "payment_status": bill_status,
                        "last_collection_id": collection_id,
                        "last_collection_journal_entry_id": journal_entry.id,
                        "last_paid_at": now,
                        "updated_at": now,
                    },
                    "$push": {
                        "collection_ids": collection_id,
                        "collection_journal_entry_ids": journal_entry.id,
                    },
                },
            )
            if update_result.matched_count == 0:
                raise HTTPException(status_code=404, detail="Maintenance bill not found after accounting post")
        except Exception as exc:
            await _compensate_after_posted_journal("bill update")
            raise HTTPException(
                status_code=500,
                detail=(
                    "Maintenance bill update failed after journal posting; "
                    "the accounting entry was automatically reversed"
                ),
            ) from exc

    return {
        "collection_id": collection_id,
        "tenant_id": tenant_id,
        "amount": payload.amount,
        "journal_entry_id": journal_entry.id,
        "created": created,
        "bill_id": bill_id,
        "bill_status": bill_status,
        "paid_amount": new_paid_amount,
        "outstanding_amount": outstanding_amount,
    }
