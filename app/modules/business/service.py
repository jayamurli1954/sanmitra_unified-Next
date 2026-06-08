from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
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
from app.modules.business.schemas import (
    CaDocumentCreateRequest,
    CaDocumentUpdateRequest,
    INVOICE_STANDARD_FIELDS,
    InvoiceSettings,
    InvoiceSettingsUpdateRequest,
    PartyCreateRequest,
    PartyUpdateRequest,
    SalesInvoiceCancelRequest,
    SalesInvoiceCreateRequest,
    TypedVoucherCreateRequest,
    TypedVoucherReversalRequest,
)

PARTIES_COLLECTION = "business_parties"
VOUCHERS_COLLECTION = "business_vouchers"
VOUCHER_COUNTERS_COLLECTION = "business_voucher_counters"
SALES_INVOICES_COLLECTION = "business_sales_invoices"
INVOICE_SETTINGS_COLLECTION = "business_invoice_settings"
CA_DOCUMENTS_COLLECTION = "business_ca_document_metadata"

# Default Output-GST and receivable account codes from the BUSINESS chart of accounts.
SALES_RECEIVABLE_CODE = "12001"  # Sundry Debtors
OUTPUT_CGST_CODE = "22001"
OUTPUT_SGST_CODE = "22002"
OUTPUT_IGST_CODE = "22003"
CA_DOCUMENT_DEFAULT_NEXT_ACTION = {
    "uploaded": "Classify document and assign reviewer",
    "under_review": "Review support and raise query if needed",
    "query_raised": "Await client clarification",
    "reviewed": "Ready for voucher or return posting",
    "posted": "Linked to posted voucher or return reference",
}


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
    ca_documents = get_collection(CA_DOCUMENTS_COLLECTION)
    await ca_documents.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("updated_at", -1)])
    await ca_documents.create_index([("tenant_id", 1), ("app_key", 1), ("document_id", 1)], unique=True)
    invoices = get_collection(SALES_INVOICES_COLLECTION)
    await invoices.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("invoice_date", -1)])
    await invoices.create_index([("tenant_id", 1), ("app_key", 1), ("invoice_id", 1)], unique=True)
    await invoices.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("idempotency_key", 1)], unique=True, sparse=True)
    invoice_settings = get_collection(INVOICE_SETTINGS_COLLECTION)
    await invoice_settings.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1)], unique=True)


def _ca_document_response_doc(doc: dict) -> dict:
    result = _json_safe_doc(doc)
    result.setdefault("next_action", CA_DOCUMENT_DEFAULT_NEXT_ACTION.get(str(result.get("status") or "uploaded"), "Review document metadata"))
    return result


async def create_ca_document_metadata(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    created_by: str,
    payload: CaDocumentCreateRequest,
) -> dict:
    document_id = str(uuid4())
    now = _now()
    doc = {
        "document_id": document_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "client_name": payload.client_name.strip(),
        "document_type": payload.document_type.strip(),
        "period": payload.period.strip(),
        "status": "uploaded",
        "assigned_to": payload.assigned_to,
        "original_file_name": payload.original_file_name,
        "next_action": CA_DOCUMENT_DEFAULT_NEXT_ACTION["uploaded"],
        "posting_reference": None,
        "notes": payload.notes,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    await get_collection(CA_DOCUMENTS_COLLECTION).insert_one(doc)
    result = _ca_document_response_doc(doc)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="business_ca_document_metadata_created",
        entity_type="business_ca_document_metadata",
        entity_id=document_id,
        new_value=result,
    )
    return result


async def list_ca_document_metadata(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    status: str | None = None,
    limit: int = 100,
) -> dict:
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
    }
    if status:
        filters["status"] = status

    safe_limit = max(1, min(int(limit or 100), 500))
    rows = (
        await get_collection(CA_DOCUMENTS_COLLECTION)
        .find(filters)
        .sort("updated_at", -1)
        .limit(safe_limit)
        .to_list(length=safe_limit)
    )
    return {"items": [_ca_document_response_doc(row) for row in rows], "total": len(rows)}


async def update_ca_document_metadata(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    document_id: str,
    updated_by: str,
    payload: CaDocumentUpdateRequest,
) -> dict | None:
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "document_id": document_id,
    }
    collection = get_collection(CA_DOCUMENTS_COLLECTION)
    existing = await collection.find_one(filters)
    if existing is None:
        return None

    patch = payload.model_dump(exclude_unset=True)
    patch.pop("accounting_entity_id", None)
    patch = {key: value for key, value in patch.items() if value is not None}
    status = patch.get("status")
    if status and not patch.get("next_action"):
        patch["next_action"] = CA_DOCUMENT_DEFAULT_NEXT_ACTION.get(str(status), "Review document metadata")
    patch["updated_by"] = updated_by
    patch["updated_at"] = _now()

    await collection.update_one(filters, {"$set": patch})
    updated = await collection.find_one(filters)
    result = _ca_document_response_doc(updated)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=updated_by,
        action="business_ca_document_metadata_updated",
        entity_type="business_ca_document_metadata",
        entity_id=document_id,
        old_value=_ca_document_response_doc(existing),
        new_value=result,
    )
    return result


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


# ===================== Sales Invoices (GST) =====================


def _q2(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _invoice_response_doc(doc: dict, *, created: bool = False) -> dict:
    result = _json_safe_doc(doc)
    result.setdefault("created", created)
    return result


def _compute_invoice_lines(payload: SalesInvoiceCreateRequest):
    """Compute per-line taxable + GST split and roll up invoice totals.

    Each monetary value is quantized to 2dp; totals are sums of rounded line
    values so debits and credits stay balanced. For intra-state supply GST is
    split CGST/SGST (with the remainder assigned to SGST to avoid rounding
    drift); for inter-state it posts fully to IGST.
    """
    lines: list[dict] = []
    taxable_total = Decimal("0.00")
    cgst_total = Decimal("0.00")
    sgst_total = Decimal("0.00")
    igst_total = Decimal("0.00")
    for item in payload.line_items:
        taxable = _q2(Decimal(item.quantity) * Decimal(item.rate))
        gst_amount = _q2(taxable * Decimal(item.gst_rate) / Decimal("100"))
        if payload.is_inter_state:
            cgst = Decimal("0.00")
            sgst = Decimal("0.00")
            igst = gst_amount
        else:
            cgst = _q2(gst_amount / Decimal("2"))
            sgst = _q2(gst_amount - cgst)
            igst = Decimal("0.00")
        line_total = _q2(taxable + cgst + sgst + igst)
        lines.append({
            "description": item.description.strip(),
            "hsn_sac": item.hsn_sac,
            "quantity": str(Decimal(item.quantity)),
            "rate": _money(item.rate),
            "gst_rate": str(Decimal(item.gst_rate)),
            "taxable_amount": str(taxable),
            "cgst": str(cgst),
            "sgst": str(sgst),
            "igst": str(igst),
            "line_total": str(line_total),
        })
        taxable_total += taxable
        cgst_total += cgst
        sgst_total += sgst
        igst_total += igst
    gst_total = cgst_total + sgst_total + igst_total
    invoice_total = taxable_total + gst_total
    return lines, taxable_total, cgst_total, sgst_total, igst_total, gst_total, invoice_total


def _financial_year_strings(invoice_date):
    if invoice_date.month >= 4:
        start, end = invoice_date.year, invoice_date.year + 1
    else:
        start, end = invoice_date.year - 1, invoice_date.year
    full = f"{start}-{end}"
    short = f"{start}-{str(end)[-2:]}"
    return full, short


def _format_invoice_number(numbering, *, financial_year: str, fy_short: str, seq: int) -> str:
    padded = str(seq).zfill(int(getattr(numbering, "seq_padding", 6) or 6))
    return (
        str(getattr(numbering, "number_format", "{PREFIX}-{FY}-{SEQ}") or "{PREFIX}-{FY}-{SEQ}")
        .replace("{PREFIX}", str(getattr(numbering, "prefix", "INV") or "INV"))
        .replace("{FYSHORT}", fy_short)
        .replace("{FY}", financial_year)
        .replace("{SEQ}", padded)
    )


def _validate_required_invoice_fields(payload: SalesInvoiceCreateRequest, settings: dict) -> None:
    """Enforce 'required' rules an admin set on standard optional fields."""
    field_config = settings.get("field_config") or {}
    labels = {
        "due_date": "Due date",
        "place_of_supply": "Place of supply",
        "reference": "Reference / PO",
        "notes": "Notes",
    }
    for key in ("due_date", "place_of_supply", "reference", "notes"):
        rule = field_config.get(key) or {}
        if rule.get("required") and not getattr(payload, key, None):
            raise AccountingValidationError(f"{labels[key]} is required by this business's invoice settings")
    hsn_rule = field_config.get("hsn_sac") or {}
    if hsn_rule.get("required"):
        for item in payload.line_items:
            if not (item.hsn_sac and str(item.hsn_sac).strip()):
                raise AccountingValidationError("HSN/SAC is required on every line by this business's invoice settings")


async def _reserve_invoice_number(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    invoice_date,
    numbering,
) -> str:
    financial_year, fy_short = _financial_year_strings(invoice_date)
    reset_yearly = bool(getattr(numbering, "reset_yearly", True))
    scope = financial_year if reset_yearly else "all"
    counter_id = f"{tenant_id}:{app_key}:{accounting_entity_id}:sales_invoice:{scope}"
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
                    "voucher_type": "sales_invoice",
                    "financial_year": financial_year,
                    "created_at": _now(),
                },
                "$set": {"updated_at": _now()},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        raw_seq = int((counter or {}).get("seq") or 1)
    except Exception:
        existing = await get_collection(SALES_INVOICES_COLLECTION).count_documents(
            {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
        )
        raw_seq = int(existing) + 1
    # Honor a custom starting number: first invoice == start_number.
    seq = int(getattr(numbering, "start_number", 1) or 1) + raw_seq - 1
    return _format_invoice_number(numbering, financial_year=financial_year, fy_short=fy_short, seq=seq)


async def get_invoice_settings(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
) -> dict:
    row = await get_collection(INVOICE_SETTINGS_COLLECTION).find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
    )
    if row is None:
        settings = InvoiceSettings()
        result = settings.model_dump()
    else:
        # Re-validate stored doc through the model so missing/new keys get defaults.
        stored = {k: v for k, v in row.items() if k in {"field_config", "numbering", "custom_fields", "branding"}}
        result = InvoiceSettings(**stored).model_dump()
    # Backfill any standard field missing from a partially-saved config so the
    # form and required-field validation always have a complete rule set.
    field_config = result.get("field_config") or {}
    for key in INVOICE_STANDARD_FIELDS:
        field_config.setdefault(key, {"visible": True, "required": False})
    result["field_config"] = field_config
    result.update({
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "updated_by": (row or {}).get("updated_by"),
        "updated_at": (row or {}).get("updated_at"),
    })
    return result


async def save_invoice_settings(
    *,
    tenant_id: str,
    app_key: str,
    updated_by: str,
    payload: InvoiceSettingsUpdateRequest,
) -> dict:
    accounting_entity_id = payload.accounting_entity_id
    settings = InvoiceSettings(
        field_config=payload.field_config,
        numbering=payload.numbering,
        custom_fields=payload.custom_fields,
        branding=payload.branding,
    )
    doc = settings.model_dump()
    doc.update({"updated_by": updated_by, "updated_at": _now()})
    filters = {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
    await get_collection(INVOICE_SETTINGS_COLLECTION).update_one(
        filters,
        {"$set": doc, "$setOnInsert": {**filters, "created_at": _now()}},
        upsert=True,
    )
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=updated_by,
        action="business_invoice_settings_updated",
        entity_type="business_invoice_settings",
        entity_id=accounting_entity_id,
        new_value=doc,
    )
    return await get_invoice_settings(tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id)


async def list_sales_invoices(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    status: str | None = None,
    limit: int = 100,
) -> dict:
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
    }
    if status:
        filters["status"] = status
    safe_limit = max(1, min(int(limit or 100), 500))
    rows = (
        await get_collection(SALES_INVOICES_COLLECTION)
        .find(filters)
        .sort("invoice_date", -1)
        .limit(safe_limit)
        .to_list(length=safe_limit)
    )
    return {"items": [_invoice_response_doc(row) for row in rows], "total": len(rows)}


async def get_sales_invoice(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    invoice_id: str,
) -> dict | None:
    row = await get_collection(SALES_INVOICES_COLLECTION).find_one(
        {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "accounting_entity_id": accounting_entity_id,
            "invoice_id": invoice_id,
        }
    )
    return _invoice_response_doc(row) if row else None


async def create_sales_invoice(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    created_by: str,
    payload: SalesInvoiceCreateRequest,
    idempotency_key: str | None,
) -> dict:
    if app_key == "mitrabooks":
        await initialize_default_chart_of_accounts(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=payload.accounting_entity_id,
            organization_type="BUSINESS",
        )

    if idempotency_key:
        existing = await get_collection(SALES_INVOICES_COLLECTION).find_one(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "accounting_entity_id": payload.accounting_entity_id,
                "idempotency_key": idempotency_key,
            }
        )
        if existing is not None:
            return _invoice_response_doc(existing, created=False)

    customer = await get_party(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        party_id=payload.customer_party_id,
    )
    if customer is None:
        raise AccountingValidationError("Customer party not found for this tenant")

    settings = await get_invoice_settings(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
    )
    _validate_required_invoice_fields(payload, settings)

    lines, taxable_total, cgst_total, sgst_total, igst_total, gst_total, invoice_total = _compute_invoice_lines(payload)
    if invoice_total <= Decimal("0"):
        raise AccountingValidationError("Invoice total must be greater than zero")

    receivable_id = await _resolve_voucher_account_id(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        account_id=None,
        account_code=SALES_RECEIVABLE_CODE,
        side="receivable",
    )
    income_id = await _resolve_voucher_account_id(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        account_id=None,
        account_code=payload.income_account_code,
        side="income",
    )

    journal_lines = [
        JournalLineIn(account_id=receivable_id, debit=invoice_total, credit=Decimal("0")),
        JournalLineIn(account_id=income_id, debit=Decimal("0"), credit=taxable_total),
    ]
    for gst_amount, code in (
        (cgst_total, OUTPUT_CGST_CODE),
        (sgst_total, OUTPUT_SGST_CODE),
        (igst_total, OUTPUT_IGST_CODE),
    ):
        if gst_amount > Decimal("0"):
            gst_account_id = await _resolve_voucher_account_id(
                session,
                tenant_id=tenant_id,
                app_key=app_key,
                accounting_entity_id=payload.accounting_entity_id,
                account_id=None,
                account_code=code,
                side="output GST",
            )
            journal_lines.append(JournalLineIn(account_id=gst_account_id, debit=Decimal("0"), credit=gst_amount))

    invoice_id = str(uuid4())
    numbering = InvoiceSettings(**{k: settings[k] for k in ("field_config", "numbering", "custom_fields", "branding") if k in settings}).numbering
    invoice_number = await _reserve_invoice_number(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        invoice_date=payload.invoice_date,
        numbering=numbering,
    )
    description = f"Sales Invoice {invoice_number} - {customer.get('party_name') or payload.customer_party_id}"
    now = _now()
    doc = {
        "invoice_id": invoice_id,
        "invoice_number": invoice_number,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "customer_party_id": payload.customer_party_id,
        "customer_name": customer.get("party_name"),
        "customer_gstin": customer.get("gstin"),
        "invoice_date": payload.invoice_date.isoformat(),
        "due_date": payload.due_date.isoformat() if payload.due_date else None,
        "is_inter_state": payload.is_inter_state,
        "place_of_supply": payload.place_of_supply,
        "income_account_code": payload.income_account_code,
        "reference": payload.reference,
        "notes": payload.notes,
        "line_items": lines,
        "taxable_total": str(taxable_total),
        "cgst_total": str(cgst_total),
        "sgst_total": str(sgst_total),
        "igst_total": str(igst_total),
        "gst_total": str(gst_total),
        "invoice_total": str(invoice_total),
        "status": "posting",
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    if idempotency_key:
        doc["idempotency_key"] = idempotency_key
    invoices = get_collection(SALES_INVOICES_COLLECTION)
    await invoices.insert_one(doc)

    try:
        journal_entry, created = await post_journal_entry(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=payload.accounting_entity_id,
            created_by=created_by,
            payload=JournalPostRequest(
                entry_date=payload.invoice_date,
                description=description,
                reference=invoice_number,
                source_module="business",
                source_document_type="sales_invoice",
                source_document_id=invoice_id,
                lines=journal_lines,
            ),
            idempotency_key=idempotency_key or f"sales-invoice:{invoice_id}",
        )
    except Exception:
        await invoices.delete_one({"tenant_id": tenant_id, "app_key": app_key, "invoice_id": invoice_id})
        raise

    update = {"status": "posted", "journal_entry_id": journal_entry.id, "updated_at": _now()}
    await invoices.update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "invoice_id": invoice_id},
        {"$set": update},
    )
    doc.update(update)
    result = _invoice_response_doc(doc, created=created)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="business_sales_invoice_posted",
        entity_type="business_sales_invoice",
        entity_id=invoice_id,
        new_value=result,
    )
    return result


async def cancel_sales_invoice(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    invoice_id: str,
    created_by: str,
    payload: SalesInvoiceCancelRequest,
    idempotency_key: str | None,
) -> dict:
    invoices = get_collection(SALES_INVOICES_COLLECTION)
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "invoice_id": invoice_id,
    }
    invoice = await invoices.find_one(filters)
    if invoice is None:
        raise AccountingNotFoundError("Sales invoice not found")

    if invoice.get("status") == "cancelled" and invoice.get("reversal_journal_entry_id"):
        return _invoice_response_doc(invoice, created=False)

    journal_entry_id = invoice.get("journal_entry_id")
    if not journal_entry_id:
        raise AccountingValidationError("Sales invoice is not linked to a posted journal entry")
    if invoice.get("status") != "posted":
        raise AccountingValidationError("Only posted sales invoices can be cancelled")

    old_invoice = _invoice_response_doc(invoice)
    reversal_key = idempotency_key or f"sales-invoice-cancel:{invoice_id}"
    reversal, created = await reverse_journal_entry(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        created_by=created_by,
        journal_id=int(journal_entry_id),
        reversal_date=payload.cancel_date or date.today(),
        reason=payload.reason,
        idempotency_key=reversal_key,
    )
    update = {
        "status": "cancelled",
        "reversal_journal_entry_id": reversal.id,
        "cancel_reason": payload.reason,
        "cancelled_at": _now(),
        "updated_at": _now(),
    }
    await invoices.update_one(filters, {"$set": update})
    invoice.update(update)
    result = _invoice_response_doc(invoice, created=created)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="business_sales_invoice_cancelled",
        entity_type="business_sales_invoice",
        entity_id=invoice_id,
        old_value=old_invoice,
        new_value=result,
    )
    return result
