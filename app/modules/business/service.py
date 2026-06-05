from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models.entities import Account
from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import (
    AccountingNotFoundError,
    AccountingValidationError,
    initialize_default_chart_of_accounts,
    post_journal_entry,
    reverse_journal_entry,
)
from app.core.audit.service import log_audit_event
from app.db.mongo import get_collection
from app.modules.business.schemas import PartyCreateRequest, PartyUpdateRequest, TypedVoucherCreateRequest, TypedVoucherReversalRequest

PARTIES_COLLECTION = "business_parties"
VOUCHERS_COLLECTION = "business_vouchers"
VOUCHER_COUNTERS_COLLECTION = "business_voucher_counters"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _money(value: Decimal) -> str:
    return str(Decimal(value).quantize(Decimal("0.01")))


def _json_safe_doc(doc: dict) -> dict:
    return {key: value for key, value in doc.items() if key != "_id"}


def _voucher_response_doc(doc: dict, *, created: bool = False) -> dict:
    result = _json_safe_doc(doc)
    result.setdefault("created", created)
    return result


def _voucher_prefix(voucher_type: str) -> str:
    return {
        "payment": "PV",
        "receipt": "RV",
        "contra": "CV",
        "journal": "JV",
    }.get(str(voucher_type or "").strip().lower(), "BV")


async def _audit_business_event(
    *,
    tenant_id: str,
    app_key: str,
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    old_value: dict | None = None,
    new_value: dict | None = None,
) -> None:
    try:
        await log_audit_event(
            tenant_id=tenant_id,
            user_id=user_id,
            product=app_key,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
        )
    except Exception:
        # Audit writes are best-effort here because accounting/domain writes may
        # already be committed by the time this hook runs.
        pass


async def _resolve_voucher_account_id(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    account_id: int | None,
    account_code: str | None,
    side: str,
) -> int:
    if account_id:
        account = (
            await session.execute(
                select(Account).where(
                    Account.id == account_id,
                    Account.tenant_id == tenant_id,
                    Account.app_key == app_key,
                    Account.accounting_entity_id == accounting_entity_id,
                )
            )
        ).scalar_one_or_none()
        if account is not None:
            return int(account.id)

    code = str(account_code or "").strip()
    if code:
        account = (
            await session.execute(
                select(Account).where(
                    Account.tenant_id == tenant_id,
                    Account.app_key == app_key,
                    Account.accounting_entity_id == accounting_entity_id,
                    Account.code == code,
                )
            )
        ).scalar_one_or_none()
        if account is not None:
            return int(account.id)

    raise AccountingNotFoundError(f"{side.capitalize()} account not found for this tenant")


async def _ensure_business_chart_for_voucher_codes(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    payload: TypedVoucherCreateRequest,
) -> None:
    if not payload.debit_account_code and not payload.credit_account_code:
        return
    if app_key != "mitrabooks":
        return

    await initialize_default_chart_of_accounts(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        organization_type="BUSINESS",
    )


async def ensure_business_indexes() -> None:
    parties = get_collection(PARTIES_COLLECTION)
    await parties.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("party_code", 1)], unique=True)
    await parties.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("party_type", 1)])
    vouchers = get_collection(VOUCHERS_COLLECTION)
    await vouchers.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("entry_date", -1)])
    await vouchers.create_index([("tenant_id", 1), ("app_key", 1), ("voucher_id", 1)], unique=True)
    await vouchers.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("idempotency_key", 1)], unique=True, sparse=True)


async def create_party(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    created_by: str,
    payload: PartyCreateRequest,
) -> dict:
    party_id = str(uuid4())
    now = _now()
    code = str(payload.party_code or f"P-{party_id[:8].upper()}").strip()
    opening_balance = _money(payload.opening_balance)
    doc = {
        "party_id": party_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "party_name": payload.party_name.strip(),
        "party_type": payload.party_type,
        "party_code": code,
        "gstin": payload.gstin,
        "email": payload.email,
        "phone": payload.phone,
        "billing_address": payload.billing_address,
        "opening_balance": opening_balance,
        "current_balance": opening_balance,
        "is_active": True,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    await get_collection(PARTIES_COLLECTION).insert_one(doc)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="business_party_created",
        entity_type="business_party",
        entity_id=party_id,
        new_value=_json_safe_doc(doc),
    )
    return _json_safe_doc(doc)


async def list_parties(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    party_type: str | None = None,
    limit: int = 100,
) -> dict:
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "is_active": True,
    }
    if party_type:
        filters["party_type"] = party_type

    safe_limit = max(1, min(int(limit or 100), 500))
    rows = (
        await get_collection(PARTIES_COLLECTION)
        .find(filters)
        .sort("party_name", 1)
        .limit(safe_limit)
        .to_list(length=safe_limit)
    )
    return {"items": [_json_safe_doc(row) for row in rows], "total": len(rows)}


async def get_party(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    party_id: str,
) -> dict | None:
    row = await get_collection(PARTIES_COLLECTION).find_one(
        {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "accounting_entity_id": accounting_entity_id,
            "party_id": party_id,
        }
    )
    return _json_safe_doc(row) if row else None


async def update_party(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    party_id: str,
    updated_by: str,
    payload: PartyUpdateRequest,
) -> dict | None:
    existing = await get_party(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        party_id=party_id,
    )
    if existing is None:
        return None

    patch = payload.model_dump(exclude_unset=True)
    if "party_name" in patch and patch["party_name"] is not None:
        patch["party_name"] = str(patch["party_name"]).strip()
    patch = {key: value for key, value in patch.items() if value is not None}
    patch["updated_by"] = updated_by
    patch["updated_at"] = _now()
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "party_id": party_id,
    }
    parties = get_collection(PARTIES_COLLECTION)
    await parties.update_one(filters, {"$set": patch})
    updated = await get_party(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        party_id=party_id,
    )
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=updated_by,
        action="business_party_updated",
        entity_type="business_party",
        entity_id=party_id,
        old_value=existing,
        new_value=updated,
    )
    return updated


async def deactivate_party(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    party_id: str,
    deactivated_by: str,
) -> dict | None:
    existing = await get_party(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        party_id=party_id,
    )
    if existing is None:
        return None

    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "party_id": party_id,
    }
    patch = {
        "is_active": False,
        "deactivated_by": deactivated_by,
        "deactivated_at": _now(),
        "updated_by": deactivated_by,
        "updated_at": _now(),
    }
    parties = get_collection(PARTIES_COLLECTION)
    await parties.update_one(filters, {"$set": patch})
    updated = await get_party(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        party_id=party_id,
    )
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=deactivated_by,
        action="business_party_deactivated",
        entity_type="business_party",
        entity_id=party_id,
        old_value=existing,
        new_value=updated,
    )
    return updated


async def _reserve_voucher_number(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    voucher_type: str,
    entry_date,
) -> str:
    financial_year = f"{entry_date.year}-{entry_date.year + 1}" if entry_date.month >= 4 else f"{entry_date.year - 1}-{entry_date.year}"
    counter_id = f"{tenant_id}:{app_key}:{accounting_entity_id}:{voucher_type}:{financial_year}"
    counters = get_collection(VOUCHER_COUNTERS_COLLECTION)
    try:
        from pymongo import ReturnDocument

        counter = await counters.find_one_and_update(
            {"_id": counter_id},
            {
                "$inc": {"seq": 1},
                "$setOnInsert": {
                    "tenant_id": tenant_id,
                    "app_key": app_key,
                    "accounting_entity_id": accounting_entity_id,
                    "voucher_type": voucher_type,
                    "financial_year": financial_year,
                    "created_at": _now(),
                },
                "$set": {"updated_at": _now()},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        seq = int((counter or {}).get("seq") or 1)
    except Exception:
        existing = await get_collection(VOUCHERS_COLLECTION).count_documents(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "accounting_entity_id": accounting_entity_id,
                "voucher_type": voucher_type,
            }
        )
        seq = int(existing) + 1
    return f"{_voucher_prefix(voucher_type)}-{financial_year}-{seq:06d}"


async def list_vouchers(
    *,
    session: AsyncSession | None = None,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    voucher_type: str | None = None,
    limit: int = 100,
) -> dict:
    del session  # Voucher headers are stored in Mongo; posted accounting rows remain linked by journal_entry_id.
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
    }
    if voucher_type:
        filters["voucher_type"] = voucher_type

    safe_limit = max(1, min(int(limit or 100), 500))
    rows = (
        await get_collection(VOUCHERS_COLLECTION)
        .find(filters)
        .sort("entry_date", -1)
        .limit(safe_limit)
        .to_list(length=safe_limit)
    )
    return {"items": [_voucher_response_doc(row) for row in rows], "total": len(rows)}


async def get_voucher(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    voucher_id: str,
) -> dict | None:
    row = await get_collection(VOUCHERS_COLLECTION).find_one(
        {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "accounting_entity_id": accounting_entity_id,
            "voucher_id": voucher_id,
        }
    )
    return _voucher_response_doc(row) if row else None


async def reverse_typed_voucher(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    voucher_id: str,
    created_by: str,
    payload: TypedVoucherReversalRequest,
    idempotency_key: str | None,
) -> dict:
    vouchers = get_collection(VOUCHERS_COLLECTION)
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "voucher_id": voucher_id,
    }
    voucher = await vouchers.find_one(filters)
    if voucher is None:
        raise AccountingNotFoundError("Business voucher not found")

    if voucher.get("status") == "reversed" and voucher.get("reversal_journal_entry_id"):
        doc = _json_safe_doc(voucher)
        doc["created"] = False
        return doc

    journal_entry_id = voucher.get("journal_entry_id")
    if not journal_entry_id:
        raise AccountingValidationError("Business voucher is not linked to a posted journal entry")
    if voucher.get("status") != "posted":
        raise AccountingValidationError("Only posted business vouchers can be reversed")

    old_voucher = _json_safe_doc(voucher)
    reversal_key = idempotency_key or f"business-voucher-reversal:{voucher_id}"
    reversal, created = await reverse_journal_entry(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        created_by=created_by,
        journal_id=int(journal_entry_id),
        reversal_date=payload.reversal_date or date.today(),
        reason=payload.reason,
        idempotency_key=reversal_key,
    )
    update = {
        "status": "reversed",
        "reversal_journal_entry_id": reversal.id,
        "reversal_reason": payload.reason,
        "reversed_at": _now(),
        "updated_at": _now(),
    }
    await vouchers.update_one(filters, {"$set": update})
    voucher.update(update)
    doc = _json_safe_doc(voucher)
    doc["created"] = created
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="business_voucher_reversed",
        entity_type="business_voucher",
        entity_id=voucher_id,
        old_value=old_voucher,
        new_value=doc,
    )
    return doc


async def post_typed_voucher(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    created_by: str,
    payload: TypedVoucherCreateRequest,
    idempotency_key: str | None,
) -> dict:
    amount = Decimal(payload.amount).quantize(Decimal("0.01"))
    await _ensure_business_chart_for_voucher_codes(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        payload=payload,
    )
    debit_account_id = await _resolve_voucher_account_id(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        account_id=payload.debit_account_id,
        account_code=payload.debit_account_code,
        side="debit",
    )
    credit_account_id = await _resolve_voucher_account_id(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        account_id=payload.credit_account_id,
        account_code=payload.credit_account_code,
        side="credit",
    )
    if debit_account_id == credit_account_id:
        raise AccountingValidationError("Debit and credit accounts must be different")

    if idempotency_key:
        existing = await get_collection(VOUCHERS_COLLECTION).find_one(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "accounting_entity_id": payload.accounting_entity_id,
                "idempotency_key": idempotency_key,
            }
        )
        if existing is not None:
            doc = _json_safe_doc(existing)
            doc["created"] = False
            return doc

    voucher_id = str(uuid4())
    voucher_number = payload.reference or await _reserve_voucher_number(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        voucher_type=payload.voucher_type,
        entry_date=payload.entry_date,
    )
    reference = voucher_number
    now = _now()
    doc = {
        "voucher_id": voucher_id,
        "voucher_number": voucher_number,
        "voucher_type": payload.voucher_type,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "party_id": payload.party_id,
        "amount": _money(amount),
        "entry_date": payload.entry_date.isoformat(),
        "debit_account_id": debit_account_id,
        "credit_account_id": credit_account_id,
        "description": payload.description,
        "reference": reference,
        "status": "posting",
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    if idempotency_key:
        doc["idempotency_key"] = idempotency_key
    vouchers = get_collection(VOUCHERS_COLLECTION)
    await vouchers.insert_one(doc)

    try:
        journal_entry, created = await post_journal_entry(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=payload.accounting_entity_id,
            created_by=created_by,
            payload=JournalPostRequest(
                entry_date=payload.entry_date,
                description=payload.description,
                reference=reference,
                lines=[
                    JournalLineIn(account_id=debit_account_id, debit=amount, credit=Decimal("0")),
                    JournalLineIn(account_id=credit_account_id, debit=Decimal("0"), credit=amount),
                ],
            ),
            idempotency_key=idempotency_key or f"business-voucher:{voucher_id}",
        )
    except Exception:
        await vouchers.delete_one({"tenant_id": tenant_id, "app_key": app_key, "voucher_id": voucher_id})
        raise

    update = {"status": "posted", "journal_entry_id": journal_entry.id, "updated_at": _now()}
    await vouchers.update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "voucher_id": voucher_id},
        {"$set": update},
    )
    doc.update(update)
    doc["created"] = created
    result = _json_safe_doc(doc)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="business_voucher_posted",
        entity_type="business_voucher",
        entity_id=voucher_id,
        new_value=result,
    )
    return result
