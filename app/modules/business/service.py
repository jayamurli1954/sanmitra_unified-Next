from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models.entities import Account, JournalEntry, JournalLine
from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import (
    AccountingNotFoundError,
    AccountingValidationError,
    get_party_outstanding,
    get_party_wise_balances,
    initialize_default_chart_of_accounts,
    post_journal_entry,
    reverse_journal_entry,
)
from app.core.audit.service import log_audit_event
from app.db.mongo import get_collection
from app.modules.business.dimensions import validate_dimension_refs
from app.modules.business.inventory import validate_item_refs
from app.modules.business.tds import compute_tcs, compute_tds
from app.modules.business.schemas import (
    BillPaymentUpdateRequest,
    CaDocumentCreateRequest,
    CaDocumentUpdateRequest,
    CreditNoteCancelRequest,
    CreditNoteCreateRequest,
    DebitNoteCancelRequest,
    DebitNoteCreateRequest,
    GstPeriodLockUpdateRequest,
    GstSettlementCreateRequest,
    ItcReclaimActionRequest,
    ItcReversalActionRequest,
    INVOICE_STANDARD_FIELDS,
    InvoiceSettings,
    InvoiceSettingsUpdateRequest,
    PartyCreateRequest,
    PartyUpdateRequest,
    PurchaseBillCancelRequest,
    PurchaseBillCreateRequest,
    SalesInvoiceCancelRequest,
    SalesInvoiceCreateRequest,
    TypedVoucherCreateRequest,
    TypedVoucherReversalRequest,
)

PARTIES_COLLECTION = "business_parties"
VOUCHERS_COLLECTION = "business_vouchers"
VOUCHER_COUNTERS_COLLECTION = "business_voucher_counters"
SALES_INVOICES_COLLECTION = "business_sales_invoices"
PURCHASE_BILLS_COLLECTION = "business_purchase_bills"
INVOICE_SETTINGS_COLLECTION = "business_invoice_settings"
GST_PERIOD_LOCKS_COLLECTION = "business_gst_period_locks"
CREDIT_NOTES_COLLECTION = "business_credit_notes"
DEBIT_NOTES_COLLECTION = "business_debit_notes"
GST_SETTLEMENTS_COLLECTION = "business_gst_settlements"
CA_DOCUMENTS_COLLECTION = "business_ca_document_metadata"

GST_PAYABLE_CODE = "22004"

_MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

# Default Output-GST and receivable account codes from the BUSINESS chart of accounts.
SALES_RECEIVABLE_CODE = "12001"  # Sundry Debtors
OUTPUT_CGST_CODE = "22001"
OUTPUT_SGST_CODE = "22002"
OUTPUT_IGST_CODE = "22003"

# Purchase-side codes: Accounts Payable and Input GST (ITC, asset).
PURCHASE_PAYABLE_CODE = "21001"  # Sundry Creditors
INPUT_CGST_CODE = "14001"
INPUT_SGST_CODE = "14002"
INPUT_IGST_CODE = "14003"

# GST Rule 37 — ITC reversal on non-payment within 180 days.
ITC_REVERSAL_RECOVERABLE_CODE = "14004"  # Parked, reclaimable on later payment
GST_INTEREST_PAYABLE_CODE = "23003"
GST_INTEREST_EXPENSE_CODE = "54006"
ITC_REVERSAL_DAYS = 180
ITC_INTEREST_RATE = Decimal("0.18")  # 18% p.a. under Section 50

# Income-tax TDS/TCS statutory dues accounts.
TDS_PAYABLE_CODE = "23001"
TCS_PAYABLE_CODE = "23004"

# GST reverse charge (9(3)/9(4)) — recipient's own liability, cash-only.
RCM_PAYABLE_CODE = "22005"

# GST Composition Scheme (Section 10) — tax rate by category, on turnover.
# Manufacturers/traders 1%, restaurants 5%, other services 6%.
COMPOSITION_RATES = {
    "goods": Decimal("1"),
    "restaurant": Decimal("5"),
    "services": Decimal("6"),
}
COMPOSITION_DECLARATION = "Composition taxable person, not eligible to collect tax on supplies"
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


def _party_response_doc(doc: dict | None) -> dict | None:
    if doc is None:
        return None
    result = _json_safe_doc(doc)
    # Party master data is not the accounting source of truth. Real receivable
    # and payable balances come from posted journal lines via party-ledger and
    # outstanding endpoints.
    result["opening_balance"] = "0.00"
    result["current_balance"] = "0.00"
    result["balance_source"] = "ledger_reports"
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
    bills = get_collection(PURCHASE_BILLS_COLLECTION)
    await bills.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("bill_date", -1)])
    await bills.create_index([("tenant_id", 1), ("app_key", 1), ("bill_id", 1)], unique=True)
    await bills.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("idempotency_key", 1)], unique=True, sparse=True)
    period_locks = get_collection(GST_PERIOD_LOCKS_COLLECTION)
    await period_locks.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("period", 1)], unique=True)
    credit_notes = get_collection(CREDIT_NOTES_COLLECTION)
    await credit_notes.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("note_date", -1)])
    await credit_notes.create_index([("tenant_id", 1), ("app_key", 1), ("credit_note_id", 1)], unique=True)
    await credit_notes.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("idempotency_key", 1)], unique=True, sparse=True)
    debit_notes = get_collection(DEBIT_NOTES_COLLECTION)
    await debit_notes.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("note_date", -1)])
    await debit_notes.create_index([("tenant_id", 1), ("app_key", 1), ("debit_note_id", 1)], unique=True)
    await debit_notes.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("idempotency_key", 1)], unique=True, sparse=True)
    gst_settlements = get_collection(GST_SETTLEMENTS_COLLECTION)
    await gst_settlements.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("period", 1)], unique=True)
    payment_allocations = get_collection("business_payment_allocations")
    await payment_allocations.create_index([("tenant_id", 1), ("app_key", 1), ("allocation_id", 1)], unique=True)
    await payment_allocations.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("side", 1), ("status", 1)])
    await payment_allocations.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("open_item_id", 1)])
    await payment_allocations.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("payment_id", 1)])
    bank_stmt_lines = get_collection("business_bank_statement_lines")
    await bank_stmt_lines.create_index([("tenant_id", 1), ("app_key", 1), ("statement_line_id", 1)], unique=True)
    await bank_stmt_lines.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("account_id", 1), ("txn_date", 1)])
    await bank_stmt_lines.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("account_id", 1), ("dedupe_key", 1)], unique=True)
    bank_matches = get_collection("business_bank_recon_matches")
    await bank_matches.create_index([("tenant_id", 1), ("app_key", 1), ("match_id", 1)], unique=True)
    await bank_matches.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("account_id", 1), ("status", 1)])
    dunning_log = get_collection("business_dunning_log")
    await dunning_log.create_index([("tenant_id", 1), ("app_key", 1), ("dunning_id", 1)], unique=True)
    await dunning_log.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("party_id", 1), ("created_at", -1)])
    fixed_assets_col = get_collection("business_fixed_assets")
    await fixed_assets_col.create_index([("tenant_id", 1), ("app_key", 1), ("asset_id", 1)], unique=True)
    await fixed_assets_col.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("purchase_date", 1)])
    depreciation_runs = get_collection("business_depreciation_runs")
    await depreciation_runs.create_index([("tenant_id", 1), ("app_key", 1), ("run_id", 1)], unique=True)
    await depreciation_runs.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("financial_year", 1), ("status", 1)])
    dimensions_col = get_collection("business_dimensions")
    await dimensions_col.create_index([("tenant_id", 1), ("app_key", 1), ("dimension_id", 1)], unique=True)
    await dimensions_col.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("dimension_type", 1), ("code", 1)], unique=True)
    items_col = get_collection("business_items")
    await items_col.create_index([("tenant_id", 1), ("app_key", 1), ("item_id", 1)], unique=True)
    await items_col.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("code", 1)], unique=True)


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
        "pan": payload.pan,
        "email": payload.email,
        "phone": payload.phone,
        "billing_address": payload.billing_address,
        "city": payload.city,
        "state": payload.state,
        "pincode": payload.pincode,
        "legacy_opening_balance_input": opening_balance,
        "balance_source": "ledger_reports",
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
        new_value=_party_response_doc(doc),
    )
    return _party_response_doc(doc)


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
    return {"items": [_party_response_doc(row) for row in rows], "total": len(rows)}


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
    return _party_response_doc(row) if row else None


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
                    JournalLineIn(
                        account_id=debit_account_id, debit=amount, credit=Decimal("0"),
                        # Payment: debit line hits the vendor (payable) sub-ledger.
                        party_id=payload.party_id if payload.voucher_type == "payment" else None,
                    ),
                    JournalLineIn(
                        account_id=credit_account_id, debit=Decimal("0"), credit=amount,
                        # Receipt: credit line hits the customer (receivable) sub-ledger.
                        party_id=payload.party_id if payload.voucher_type == "receipt" else None,
                    ),
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


def _compute_invoice_lines(payload: SalesInvoiceCreateRequest, *, composition: bool = False):
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
        # Composition dealers issue a Bill of Supply — no GST is charged or split,
        # whatever rate is on the line. gst_amount of 0 zeroes every head below.
        # Zero-rated (export/SEZ under LUT) lines likewise carry no tax.
        is_zero_rated = getattr(item, "supply_type", "taxable") == "zero_rated"
        gst_amount = Decimal("0.00") if (composition or is_zero_rated) else _q2(taxable * Decimal(item.gst_rate) / Decimal("100"))
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
            "uqc": getattr(item, "uqc", None),
            "supply_type": getattr(item, "supply_type", "taxable"),
            "item_id": getattr(item, "item_id", None),
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


async def get_gst_profile(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
) -> dict:
    """The entity's GST regime, read from invoice-settings branding.

    Returns registration_type ("regular"|"composition"), the composition
    category, and the derived composition tax rate (None for regular dealers).
    """
    settings = await get_invoice_settings(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    branding = (settings or {}).get("branding") or {}
    reg_type = str(branding.get("gst_registration_type") or "regular")
    category = branding.get("composition_category")
    rate = COMPOSITION_RATES.get(category) if reg_type == "composition" else None
    return {
        "registration_type": reg_type,
        "composition_category": category,
        "composition_rate": rate,
        "is_composition": reg_type == "composition",
    }


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

    await validate_dimension_refs(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        cost_centre_id=payload.cost_centre_id, project_id=payload.project_id,
    )
    await validate_item_refs(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        line_items=payload.line_items,
    )

    profile = await get_gst_profile(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
    )
    is_composition = profile["is_composition"]
    if is_composition and payload.is_inter_state:
        raise AccountingValidationError(
            "Composition dealers cannot make inter-state outward supplies. "
            "Issue an intra-state Bill of Supply only."
        )

    lines, taxable_total, cgst_total, sgst_total, igst_total, gst_total, invoice_total = _compute_invoice_lines(
        payload, composition=is_composition,
    )
    if invoice_total <= Decimal("0"):
        raise AccountingValidationError("Invoice total must be greater than zero")

    # TCS (206C) is collected on the GST-inclusive consideration (Circular
    # 17/2020), so its base is the invoice total; the customer owes grand_total.
    tcs_rate = tcs_amount = None
    if payload.tcs_section:
        try:
            tcs_rate, tcs_amount = compute_tcs(payload.tcs_section, invoice_total, payload.tcs_rate)
        except ValueError as exc:
            raise AccountingValidationError(str(exc))
    grand_total = invoice_total + (tcs_amount or Decimal("0"))

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
        JournalLineIn(account_id=receivable_id, debit=grand_total, credit=Decimal("0"), party_id=payload.customer_party_id),
        JournalLineIn(account_id=income_id, debit=Decimal("0"), credit=taxable_total),
    ]
    if tcs_amount and tcs_amount > Decimal("0"):
        # Cr TCS Payable — collected from the customer, owed to the department.
        tcs_payable_id = await _resolve_voucher_account_id(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=payload.accounting_entity_id,
            account_id=None,
            account_code=TCS_PAYABLE_CODE,
            side="TCS payable",
        )
        journal_lines.append(JournalLineIn(account_id=tcs_payable_id, debit=Decimal("0"), credit=tcs_amount))
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
    doc_label = "Bill of Supply" if is_composition else "Sales Invoice"
    description = f"{doc_label} {invoice_number} - {customer.get('party_name') or payload.customer_party_id}"
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
        "document_type": "bill_of_supply" if is_composition else "tax_invoice",
        "is_composition": is_composition,
        "reference": payload.reference,
        "notes": payload.notes,
        "line_items": lines,
        "taxable_total": str(taxable_total),
        "cgst_total": str(cgst_total),
        "sgst_total": str(sgst_total),
        "igst_total": str(igst_total),
        "gst_total": str(gst_total),
        "invoice_total": str(invoice_total),
        # TCS collected on top of the invoice value (None section => none).
        "tcs_section": payload.tcs_section,
        "tcs_rate": str(tcs_rate) if tcs_rate is not None else None,
        "tcs_base_amount": str(invoice_total) if payload.tcs_section else None,
        "tcs_amount": str(tcs_amount) if tcs_amount is not None else "0",
        "grand_total": str(grand_total),
        "collectee_pan": customer.get("pan"),
        "collectee_pan_missing": bool(payload.tcs_section) and not customer.get("pan"),
        "cost_centre_id": payload.cost_centre_id,
        "project_id": payload.project_id,
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

    reversal_date = payload.cancel_date or date.today()
    await _validate_reversal_period(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        original_date=invoice.get("invoice_date"),
        reversal_date=reversal_date,
        document_label="invoice",
    )

    old_invoice = _invoice_response_doc(invoice)
    reversal_key = idempotency_key or f"sales-invoice-cancel:{invoice_id}"
    reversal, created = await reverse_journal_entry(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        created_by=created_by,
        journal_id=int(journal_entry_id),
        reversal_date=reversal_date,
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


# ===================== Purchase Bills (Input GST / ITC) =====================


def _bill_response_doc(doc: dict, *, created: bool = False) -> dict:
    result = _json_safe_doc(doc)
    result.setdefault("created", created)
    # Defaults so bills created before payment / ITC-reversal tracking render cleanly.
    result.setdefault("payment_status", "unpaid")
    result.setdefault("paid_amount", "0")
    result.setdefault("paid_date", None)
    result.setdefault("itc_reversed", False)
    result.setdefault("itc_interest_amount", "0")
    result.setdefault("itc_reclaimed", False)
    return result


async def list_purchase_bills(
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
        await get_collection(PURCHASE_BILLS_COLLECTION)
        .find(filters)
        .sort("bill_date", -1)
        .limit(safe_limit)
        .to_list(length=safe_limit)
    )
    return {"items": [_bill_response_doc(row) for row in rows], "total": len(rows)}


async def get_purchase_bill(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    bill_id: str,
) -> dict | None:
    row = await get_collection(PURCHASE_BILLS_COLLECTION).find_one(
        {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "accounting_entity_id": accounting_entity_id,
            "bill_id": bill_id,
        }
    )
    return _bill_response_doc(row) if row else None


async def create_purchase_bill(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    created_by: str,
    payload: PurchaseBillCreateRequest,
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
        existing = await get_collection(PURCHASE_BILLS_COLLECTION).find_one(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "accounting_entity_id": payload.accounting_entity_id,
                "idempotency_key": idempotency_key,
            }
        )
        if existing is not None:
            return _bill_response_doc(existing, created=False)

    vendor = await get_party(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        party_id=payload.vendor_party_id,
    )
    if vendor is None:
        raise AccountingValidationError("Vendor party not found for this tenant")

    await validate_dimension_refs(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        cost_centre_id=payload.cost_centre_id, project_id=payload.project_id,
    )
    await validate_item_refs(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        line_items=payload.line_items,
    )

    # GST line computation is identical to sales (reads line_items + is_inter_state).
    lines, taxable_total, cgst_total, sgst_total, igst_total, gst_total, bill_total = _compute_invoice_lines(payload)
    if bill_total <= Decimal("0"):
        raise AccountingValidationError("Bill total must be greater than zero")

    profile = await get_gst_profile(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
    )
    is_composition = profile["is_composition"]

    # TDS (Income-tax) — deducted at credit time on the GST-exclusive taxable
    # value (Circular 23/2017). For composition entities GST is part of cost,
    # so the books' taxable_total (pre-GST) is still the correct TDS base.
    tds_rate = tds_amount = None
    if payload.tds_section:
        try:
            tds_rate, tds_amount = compute_tds(payload.tds_section, taxable_total, payload.tds_rate)
        except ValueError as exc:
            raise AccountingValidationError(str(exc))
        if tds_amount >= bill_total:
            raise AccountingValidationError("TDS deduction cannot equal or exceed the bill total")
    # Under reverse charge the vendor is owed the taxable value only — the GST
    # is the recipient's own liability (Cr RCM Payable), settled in cash.
    is_rcm = bool(payload.is_reverse_charge)
    vendor_owed = taxable_total if is_rcm else bill_total
    net_payable = vendor_owed - (tds_amount or Decimal("0"))

    payable_id = await _resolve_voucher_account_id(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        account_id=None,
        account_code=PURCHASE_PAYABLE_CODE,
        side="payable",
    )
    expense_id = await _resolve_voucher_account_id(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        account_id=None,
        account_code=payload.expense_account_code,
        side="expense",
    )

    if is_composition:
        # Composition dealers cannot claim ITC — the vendor's GST is part of cost.
        # Dr expense (full bill incl. GST); Cr Accounts Payable. No Input-GST legs.
        # Under RCM the same holds: the self-assessed tax is also cost.
        journal_lines = [
            JournalLineIn(account_id=expense_id, debit=bill_total, credit=Decimal("0")),
        ]
    else:
        # Dr expense (taxable) + Dr Input GST (ITC, asset); Cr Accounts Payable (total).
        # Under RCM the ITC legs are unchanged (the recipient claims the credit of
        # the tax it self-pays); only the credit side moves from AP to RCM Payable.
        journal_lines = [
            JournalLineIn(account_id=expense_id, debit=taxable_total, credit=Decimal("0")),
        ]
        for gst_amount, code in (
            (cgst_total, INPUT_CGST_CODE),
            (sgst_total, INPUT_SGST_CODE),
            (igst_total, INPUT_IGST_CODE),
        ):
            if gst_amount > Decimal("0"):
                input_gst_id = await _resolve_voucher_account_id(
                    session,
                    tenant_id=tenant_id,
                    app_key=app_key,
                    accounting_entity_id=payload.accounting_entity_id,
                    account_id=None,
                    account_code=code,
                    side="input GST",
                )
                journal_lines.append(JournalLineIn(account_id=input_gst_id, debit=gst_amount, credit=Decimal("0")))
    if is_rcm and gst_total > Decimal("0"):
        # Cr GST Payable under RCM — discharged by cash challan, never by ITC.
        rcm_payable_id = await _resolve_voucher_account_id(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=payload.accounting_entity_id,
            account_id=None,
            account_code=RCM_PAYABLE_CODE,
            side="RCM payable",
        )
        journal_lines.append(JournalLineIn(account_id=rcm_payable_id, debit=Decimal("0"), credit=gst_total))
    if tds_amount and tds_amount > Decimal("0"):
        # Cr TDS Payable for the deduction; the vendor is only owed the net.
        tds_payable_id = await _resolve_voucher_account_id(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=payload.accounting_entity_id,
            account_id=None,
            account_code=TDS_PAYABLE_CODE,
            side="TDS payable",
        )
        journal_lines.append(JournalLineIn(account_id=tds_payable_id, debit=Decimal("0"), credit=tds_amount))
    journal_lines.append(JournalLineIn(account_id=payable_id, debit=Decimal("0"), credit=net_payable, party_id=payload.vendor_party_id))

    bill_id = str(uuid4())
    bill_number = payload.bill_number.strip()
    description = f"Purchase Bill {bill_number} - {vendor.get('party_name') or payload.vendor_party_id}"
    now = _now()
    doc = {
        "bill_id": bill_id,
        "bill_number": bill_number,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "vendor_party_id": payload.vendor_party_id,
        "vendor_name": vendor.get("party_name"),
        "vendor_gstin": vendor.get("gstin"),
        "bill_date": payload.bill_date.isoformat(),
        "due_date": payload.due_date.isoformat() if payload.due_date else None,
        "is_inter_state": payload.is_inter_state,
        "is_reverse_charge": is_rcm,
        "rcm_payable": str(gst_total) if is_rcm else "0",
        "place_of_supply": payload.place_of_supply,
        "expense_account_code": payload.expense_account_code,
        "notes": payload.notes,
        "line_items": lines,
        "taxable_total": str(taxable_total),
        "cgst_total": str(cgst_total),
        "sgst_total": str(sgst_total),
        "igst_total": str(igst_total),
        "gst_total": str(gst_total),
        "bill_total": str(bill_total),
        # TDS deducted at source (None section => no deduction, net == total).
        "tds_section": payload.tds_section,
        "tds_rate": str(tds_rate) if tds_rate is not None else None,
        "tds_base_amount": str(taxable_total) if payload.tds_section else None,
        "tds_amount": str(tds_amount) if tds_amount is not None else "0",
        "net_payable": str(net_payable),
        "deductee_pan": vendor.get("pan"),
        "deductee_pan_missing": bool(payload.tds_section) and not vendor.get("pan"),
        "cost_centre_id": payload.cost_centre_id,
        "project_id": payload.project_id,
        # Composition dealers capitalise input GST into cost (no ITC claimed).
        "itc_claimed": not is_composition,
        "status": "posting",
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    if idempotency_key:
        doc["idempotency_key"] = idempotency_key
    bills = get_collection(PURCHASE_BILLS_COLLECTION)
    await bills.insert_one(doc)

    try:
        journal_entry, created = await post_journal_entry(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=payload.accounting_entity_id,
            created_by=created_by,
            payload=JournalPostRequest(
                entry_date=payload.bill_date,
                description=description,
                reference=bill_number,
                source_module="business",
                source_document_type="purchase_bill",
                source_document_id=bill_id,
                lines=journal_lines,
            ),
            idempotency_key=idempotency_key or f"purchase-bill:{bill_id}",
        )
    except Exception:
        await bills.delete_one({"tenant_id": tenant_id, "app_key": app_key, "bill_id": bill_id})
        raise

    update = {"status": "posted", "journal_entry_id": journal_entry.id, "updated_at": _now()}
    await bills.update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "bill_id": bill_id},
        {"$set": update},
    )
    doc.update(update)
    result = _bill_response_doc(doc, created=created)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="business_purchase_bill_posted",
        entity_type="business_purchase_bill",
        entity_id=bill_id,
        new_value=result,
    )
    return result


async def cancel_purchase_bill(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    bill_id: str,
    created_by: str,
    payload: PurchaseBillCancelRequest,
    idempotency_key: str | None,
) -> dict:
    bills = get_collection(PURCHASE_BILLS_COLLECTION)
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "bill_id": bill_id,
    }
    bill = await bills.find_one(filters)
    if bill is None:
        raise AccountingNotFoundError("Purchase bill not found")

    if bill.get("status") == "cancelled" and bill.get("reversal_journal_entry_id"):
        return _bill_response_doc(bill, created=False)

    journal_entry_id = bill.get("journal_entry_id")
    if not journal_entry_id:
        raise AccountingValidationError("Purchase bill is not linked to a posted journal entry")
    if bill.get("status") != "posted":
        raise AccountingValidationError("Only posted purchase bills can be cancelled")

    reversal_date = payload.cancel_date or date.today()
    await _validate_reversal_period(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        original_date=bill.get("bill_date"),
        reversal_date=reversal_date,
        document_label="bill",
    )

    old_bill = _bill_response_doc(bill)
    reversal_key = idempotency_key or f"purchase-bill-cancel:{bill_id}"
    reversal, created = await reverse_journal_entry(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        created_by=created_by,
        journal_id=int(journal_entry_id),
        reversal_date=reversal_date,
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
    await bills.update_one(filters, {"$set": update})
    bill.update(update)
    result = _bill_response_doc(bill, created=created)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="business_purchase_bill_cancelled",
        entity_type="business_purchase_bill",
        entity_id=bill_id,
        old_value=old_bill,
        new_value=result,
    )
    return result


# ============== ITC Reversal (GST Rule 37 — 180-day non-payment) ==============


def _parse_iso_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _itc_split_for_bill(bill: dict) -> tuple[dict, Decimal]:
    """Input GST (ITC) per head as recorded on a posted bill."""
    split = {
        "cgst": Decimal(str(bill.get("cgst_total") or "0")),
        "sgst": Decimal(str(bill.get("sgst_total") or "0")),
        "igst": Decimal(str(bill.get("igst_total") or "0")),
    }
    total = split["cgst"] + split["sgst"] + split["igst"]
    return split, total


def _compute_itc_interest(itc_total: Decimal, bill_date: date | None, as_of: date) -> Decimal:
    """18% p.a. interest (Section 50), accruing from the ITC-availed (bill) date to
    the reversal/as-of date. Simple interest on a 365-day year, ROUND_HALF_UP."""
    if bill_date is None:
        return Decimal("0")
    days = (as_of - bill_date).days
    if days <= 0 or itc_total <= 0:
        return Decimal("0")
    interest = itc_total * ITC_INTEREST_RATE * Decimal(days) / Decimal("365")
    return interest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def mark_bill_payment(
    *,
    tenant_id: str,
    app_key: str,
    bill_id: str,
    created_by: str,
    payload: BillPaymentUpdateRequest,
) -> dict:
    """Record how much of a posted bill has been paid. Drives the Rule 37
    180-day non-payment test; the cash/bank movement itself is a separate voucher."""
    bills = get_collection(PURCHASE_BILLS_COLLECTION)
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "bill_id": bill_id,
    }
    bill = await bills.find_one(filters)
    if bill is None:
        raise AccountingNotFoundError("Purchase bill not found")
    if bill.get("status") != "posted":
        raise AccountingValidationError("Only posted purchase bills can record payments")

    bill_total = Decimal(str(bill.get("bill_total") or "0"))
    # With TDS the vendor is only owed the net; the deducted tax is discharged
    # via the TDS challan, so full settlement is reached at net_payable.
    settle_total = Decimal(str(bill.get("net_payable") or bill_total))
    paid_amount = Decimal(payload.paid_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if paid_amount < 0:
        raise AccountingValidationError("Paid amount cannot be negative")
    if paid_amount > settle_total:
        raise AccountingValidationError("Paid amount cannot exceed the amount payable on the bill")

    if paid_amount <= 0:
        payment_status = "unpaid"
    elif paid_amount >= settle_total:
        payment_status = "paid"
    else:
        payment_status = "partial"

    if payment_status == "unpaid":
        paid_date = None
    elif payload.paid_date:
        paid_date = payload.paid_date.isoformat()
    else:
        paid_date = date.today().isoformat()

    old_bill = _bill_response_doc(bill)
    update = {
        "payment_status": payment_status,
        "paid_amount": str(paid_amount),
        "paid_date": paid_date,
        "updated_at": _now(),
    }
    await bills.update_one(filters, {"$set": update})
    bill.update(update)
    result = _bill_response_doc(bill)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="business_bill_payment_updated",
        entity_type="business_purchase_bill",
        entity_id=bill_id,
        old_value=old_bill,
        new_value=result,
    )
    return result


async def preview_itc_reversals(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    as_of: date | None = None,
) -> dict:
    """Scan posted bills and flag those whose ITC must be reversed under Rule 37:
    unpaid (or partial) beyond 180 days from the bill date, not already reversed."""
    as_of = as_of or date.today()
    bills = get_collection(PURCHASE_BILLS_COLLECTION)
    rows = await (
        bills.find(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "accounting_entity_id": accounting_entity_id,
                "status": "posted",
            }
        ).to_list(length=2000)
    )

    candidates: list[dict] = []
    total_itc = Decimal("0")
    total_interest = Decimal("0")
    for bill in rows:
        if bill.get("itc_reversed"):
            continue
        if bill.get("is_reverse_charge"):
            # Rule 37 proviso: the 180-day payment test does not apply to
            # supplies taxed under reverse charge (the recipient paid the tax).
            continue
        if bill.get("payment_status") == "paid":
            continue
        bill_date = _parse_iso_date(bill.get("bill_date"))
        if bill_date is None:
            continue
        due_date = bill_date + timedelta(days=ITC_REVERSAL_DAYS)
        if due_date > as_of:
            continue  # still within the 180-day window
        split, itc_total = _itc_split_for_bill(bill)
        if itc_total <= 0:
            continue
        interest = _compute_itc_interest(itc_total, bill_date, as_of)
        total_itc += itc_total
        total_interest += interest
        candidates.append(
            {
                "bill_id": bill.get("bill_id"),
                "bill_number": bill.get("bill_number"),
                "vendor_party_id": bill.get("vendor_party_id"),
                "vendor_name": bill.get("vendor_name"),
                "bill_date": bill_date.isoformat(),
                "due_date": due_date.isoformat(),
                "days_overdue": (as_of - due_date).days,
                "payment_status": bill.get("payment_status", "unpaid"),
                "paid_amount": str(bill.get("paid_amount") or "0"),
                "bill_total": str(bill.get("bill_total") or "0"),
                # Full settlement target — net of TDS when the bill deducted any.
                "net_payable": str(bill.get("net_payable") or bill.get("bill_total") or "0"),
                "itc_amounts": {h: str(split[h]) for h in ("igst", "cgst", "sgst")},
                "itc_total": str(itc_total),
                "interest_amount": str(interest),
                "gstr3b_ref": "4(B)(2)",
            }
        )
    candidates.sort(key=lambda c: c["days_overdue"], reverse=True)
    return {
        "as_of": as_of.isoformat(),
        "accounting_entity_id": accounting_entity_id,
        "candidates": candidates,
        "total_itc": str(total_itc),
        "total_interest": str(total_interest),
        "count": len(candidates),
    }


async def reverse_itc_for_bill(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    bill_id: str,
    created_by: str,
    payload: ItcReversalActionRequest,
    idempotency_key: str | None,
) -> dict:
    """Post the Rule 37 ITC reversal for a bill: park the credit as recoverable and
    add 18% interest. Crediting Input GST raises the reversal period's net payable."""
    bills = get_collection(PURCHASE_BILLS_COLLECTION)
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "bill_id": bill_id,
    }
    bill = await bills.find_one(filters)
    if bill is None:
        raise AccountingNotFoundError("Purchase bill not found")
    if bill.get("status") != "posted":
        raise AccountingValidationError("Only posted purchase bills can have ITC reversed")
    if bill.get("itc_reversed") and bill.get("itc_reversal_journal_entry_id"):
        return _bill_response_doc(bill, created=False)
    if bill.get("payment_status") == "paid":
        raise AccountingValidationError("This bill is marked paid; its ITC need not be reversed")

    split, itc_total = _itc_split_for_bill(bill)
    if itc_total <= 0:
        raise AccountingValidationError("This bill carries no input GST to reverse")

    bill_date = _parse_iso_date(bill.get("bill_date"))
    reversal_date = payload.reversal_date or date.today()
    if bill_date and reversal_date < bill_date:
        raise AccountingValidationError("Reversal date cannot precede the bill date")

    reversal_period = _period_key(reversal_date)
    if await is_gst_period_locked(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        period=reversal_period,
    ):
        raise AccountingValidationError(
            f"The {_period_label(reversal_period)} GST period is finalised and locked. "
            f"Choose a reversal date in an open period."
        )

    if app_key == "mitrabooks":
        await initialize_default_chart_of_accounts(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=payload.accounting_entity_id,
            organization_type="BUSINESS",
        )

    interest = _compute_itc_interest(itc_total, bill_date, reversal_date)

    # Dr ITC Reversed (Recoverable); Cr Input CGST/SGST/IGST (reduce ITC -> raises net payable).
    recoverable_id = await _resolve_voucher_account_id(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        account_id=None, account_code=ITC_REVERSAL_RECOVERABLE_CODE, side="ITC reversal",
    )
    journal_lines = [JournalLineIn(account_id=recoverable_id, debit=itc_total, credit=Decimal("0"))]
    for head, code in (("cgst", INPUT_CGST_CODE), ("sgst", INPUT_SGST_CODE), ("igst", INPUT_IGST_CODE)):
        if split[head] > 0:
            acc = await _resolve_voucher_account_id(
                session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
                account_id=None, account_code=code, side="input GST",
            )
            journal_lines.append(JournalLineIn(account_id=acc, debit=Decimal("0"), credit=split[head]))
    # Interest (non-reclaimable): Dr Interest on GST (expense); Cr Interest Payable on GST.
    if interest > 0:
        interest_exp = await _resolve_voucher_account_id(
            session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
            account_id=None, account_code=GST_INTEREST_EXPENSE_CODE, side="interest expense",
        )
        interest_pay = await _resolve_voucher_account_id(
            session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
            account_id=None, account_code=GST_INTEREST_PAYABLE_CODE, side="interest payable",
        )
        journal_lines.append(JournalLineIn(account_id=interest_exp, debit=interest, credit=Decimal("0")))
        journal_lines.append(JournalLineIn(account_id=interest_pay, debit=Decimal("0"), credit=interest))

    bill_number = bill.get("bill_number")
    journal_entry, created = await post_journal_entry(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        created_by=created_by,
        payload=JournalPostRequest(
            entry_date=reversal_date,
            description=f"ITC reversal (Rule 37) - Bill {bill_number}",
            reference=f"ITC-REV-{bill_number}",
            source_module="business", source_document_type="itc_reversal", source_document_id=bill_id,
            lines=journal_lines,
        ),
        idempotency_key=idempotency_key or f"itc-reversal:{bill_id}",
    )

    update = {
        "itc_reversed": True,
        "itc_reversal_journal_entry_id": journal_entry.id,
        "itc_reversal_date": reversal_date.isoformat(),
        "itc_reversal_period": reversal_period,
        "itc_reversed_amounts": {h: str(split[h]) for h in ("igst", "cgst", "sgst")},
        "itc_interest_amount": str(interest),
        "updated_at": _now(),
    }
    await bills.update_one(filters, {"$set": update})
    bill.update(update)
    result = _bill_response_doc(bill, created=created)
    await _audit_business_event(
        tenant_id=tenant_id, app_key=app_key, user_id=created_by,
        action="business_itc_reversed", entity_type="business_purchase_bill", entity_id=bill_id, new_value=result,
    )
    return result


async def reclaim_itc_for_bill(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    bill_id: str,
    created_by: str,
    payload: ItcReclaimActionRequest,
    idempotency_key: str | None,
) -> dict:
    """Re-avail ITC previously reversed under Rule 37, once the bill is paid.
    Interest already charged is not reclaimable. GSTR-3B reference: 4(D)(1)."""
    bills = get_collection(PURCHASE_BILLS_COLLECTION)
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "bill_id": bill_id,
    }
    bill = await bills.find_one(filters)
    if bill is None:
        raise AccountingNotFoundError("Purchase bill not found")
    if not bill.get("itc_reversed"):
        raise AccountingValidationError("ITC was not reversed on this bill; nothing to reclaim")
    if bill.get("itc_reclaimed") and bill.get("itc_reclaim_journal_entry_id"):
        return _bill_response_doc(bill, created=False)
    if bill.get("payment_status") != "paid":
        raise AccountingValidationError("Mark the bill as paid before reclaiming the reversed ITC")

    reversed_amounts = bill.get("itc_reversed_amounts") or {}
    split = {h: Decimal(str(reversed_amounts.get(h) or "0")) for h in ("cgst", "sgst", "igst")}
    itc_total = split["cgst"] + split["sgst"] + split["igst"]
    if itc_total <= 0:
        raise AccountingValidationError("No reversed ITC recorded to reclaim")

    reclaim_date = payload.reclaim_date or date.today()
    reclaim_period = _period_key(reclaim_date)
    if await is_gst_period_locked(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        period=reclaim_period,
    ):
        raise AccountingValidationError(
            f"The {_period_label(reclaim_period)} GST period is finalised and locked. "
            f"Choose a reclaim date in an open period."
        )

    if app_key == "mitrabooks":
        await initialize_default_chart_of_accounts(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=payload.accounting_entity_id,
            organization_type="BUSINESS",
        )

    # Dr Input CGST/SGST/IGST (restore ITC); Cr ITC Reversed (Recoverable).
    journal_lines = []
    for head, code in (("cgst", INPUT_CGST_CODE), ("sgst", INPUT_SGST_CODE), ("igst", INPUT_IGST_CODE)):
        if split[head] > 0:
            acc = await _resolve_voucher_account_id(
                session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
                account_id=None, account_code=code, side="input GST",
            )
            journal_lines.append(JournalLineIn(account_id=acc, debit=split[head], credit=Decimal("0")))
    recoverable_id = await _resolve_voucher_account_id(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        account_id=None, account_code=ITC_REVERSAL_RECOVERABLE_CODE, side="ITC reversal",
    )
    journal_lines.append(JournalLineIn(account_id=recoverable_id, debit=Decimal("0"), credit=itc_total))

    bill_number = bill.get("bill_number")
    journal_entry, created = await post_journal_entry(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        created_by=created_by,
        payload=JournalPostRequest(
            entry_date=reclaim_date,
            description=f"ITC reclaim (Rule 37) - Bill {bill_number}",
            reference=f"ITC-RCL-{bill_number}",
            source_module="business", source_document_type="itc_reclaim", source_document_id=bill_id,
            lines=journal_lines,
        ),
        idempotency_key=idempotency_key or f"itc-reclaim:{bill_id}",
    )

    update = {
        "itc_reclaimed": True,
        "itc_reclaim_journal_entry_id": journal_entry.id,
        "itc_reclaim_date": reclaim_date.isoformat(),
        "updated_at": _now(),
    }
    await bills.update_one(filters, {"$set": update})
    bill.update(update)
    result = _bill_response_doc(bill, created=created)
    await _audit_business_event(
        tenant_id=tenant_id, app_key=app_key, user_id=created_by,
        action="business_itc_reclaimed", entity_type="business_purchase_bill", entity_id=bill_id, new_value=result,
    )
    return result


# ===================== GST Period Locks (finalised months) =====================


def _period_key(value) -> str:
    """Return the GST tax period 'YYYY-MM' for a date or ISO date string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value[:7]
    return f"{value.year:04d}-{value.month:02d}"


def _period_label(period: str) -> str:
    try:
        year, month = period.split("-")
        return f"{_MONTH_NAMES[int(month)]} {year}"
    except Exception:
        return period


async def is_gst_period_locked(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    period: str,
) -> bool:
    if not period:
        return False
    row = await get_collection(GST_PERIOD_LOCKS_COLLECTION).find_one(
        {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "accounting_entity_id": accounting_entity_id,
            "period": period,
        }
    )
    return bool(row and row.get("locked"))


async def _validate_reversal_period(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    original_date,
    reversal_date,
    document_label: str,
) -> None:
    """Enforce that a reversal stays in the original document's GST tax period and
    that the period has not been finalised (locked)."""
    original_period = _period_key(original_date)
    reversal_period = _period_key(reversal_date)
    if original_period and reversal_period and reversal_period != original_period:
        raise AccountingValidationError(
            f"Reversal must be dated within {_period_label(original_period)} "
            f"(the {document_label}'s GST period). Cross-period reversals are not allowed."
        )
    if await is_gst_period_locked(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        period=original_period,
    ):
        raise AccountingValidationError(
            f"The {_period_label(original_period)} GST period is finalised and locked. "
            f"Reversals into a filed period are not allowed; raise a credit/debit note in the open period instead."
        )


def _period_lock_response_doc(doc: dict) -> dict:
    return {
        "period": doc.get("period"),
        "locked": bool(doc.get("locked")),
        "note": doc.get("note"),
        "updated_by": doc.get("updated_by"),
        "updated_at": doc.get("updated_at"),
    }


async def list_gst_period_locks(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
) -> dict:
    rows = (
        await get_collection(GST_PERIOD_LOCKS_COLLECTION)
        .find({"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id})
        .sort("period", -1)
        .to_list(length=500)
    )
    return {"items": [_period_lock_response_doc(row) for row in rows], "total": len(rows)}


async def set_gst_period_lock(
    *,
    tenant_id: str,
    app_key: str,
    updated_by: str,
    payload: GstPeriodLockUpdateRequest,
) -> dict:
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "period": payload.period,
    }
    update_doc = {
        "locked": bool(payload.locked),
        "note": payload.note,
        "updated_by": updated_by,
        "updated_at": _now(),
    }
    await get_collection(GST_PERIOD_LOCKS_COLLECTION).update_one(
        filters,
        {"$set": update_doc, "$setOnInsert": {**filters, "created_at": _now()}},
        upsert=True,
    )
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=updated_by,
        action="business_gst_period_lock_updated",
        entity_type="business_gst_period_lock",
        entity_id=payload.period,
        new_value={**filters, **update_doc},
    )
    return _period_lock_response_doc({**filters, **update_doc})


# ===================== Credit Notes (sales-side GST adjustment) =====================


async def _reserve_sequence_number(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    doc_type: str,
    prefix: str,
    on_date,
    fallback_collection: str,
) -> str:
    financial_year = f"{on_date.year}-{on_date.year + 1}" if on_date.month >= 4 else f"{on_date.year - 1}-{on_date.year}"
    counter_id = f"{tenant_id}:{app_key}:{accounting_entity_id}:{doc_type}:{financial_year}"
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
                    "voucher_type": doc_type,
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
        existing = await get_collection(fallback_collection).count_documents(
            {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
        )
        seq = int(existing) + 1
    return f"{prefix}-{financial_year}-{seq:06d}"


def _credit_note_response_doc(doc: dict, *, created: bool = False) -> dict:
    result = _json_safe_doc(doc)
    result.setdefault("created", created)
    return result


async def list_credit_notes(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    status: str | None = None,
    limit: int = 100,
) -> dict:
    filters = {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
    if status:
        filters["status"] = status
    safe_limit = max(1, min(int(limit or 100), 500))
    rows = (
        await get_collection(CREDIT_NOTES_COLLECTION)
        .find(filters)
        .sort("note_date", -1)
        .limit(safe_limit)
        .to_list(length=safe_limit)
    )
    return {"items": [_credit_note_response_doc(row) for row in rows], "total": len(rows)}


async def get_credit_note(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    credit_note_id: str,
) -> dict | None:
    row = await get_collection(CREDIT_NOTES_COLLECTION).find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id, "credit_note_id": credit_note_id}
    )
    return _credit_note_response_doc(row) if row else None


async def create_credit_note(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    created_by: str,
    payload: CreditNoteCreateRequest,
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
        existing = await get_collection(CREDIT_NOTES_COLLECTION).find_one(
            {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": payload.accounting_entity_id, "idempotency_key": idempotency_key}
        )
        if existing is not None:
            return _credit_note_response_doc(existing, created=False)

    customer = await get_party(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id, party_id=payload.customer_party_id,
    )
    if customer is None:
        raise AccountingValidationError("Customer party not found for this tenant")

    # A credit note is posted in an open period; block if that month is finalised.
    if await is_gst_period_locked(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id, period=_period_key(payload.note_date),
    ):
        raise AccountingValidationError(
            f"The {_period_label(_period_key(payload.note_date))} GST period is finalised and locked. Choose a date in an open period."
        )

    lines, taxable_total, cgst_total, sgst_total, igst_total, gst_total, note_total = _compute_invoice_lines(payload)
    if note_total <= Decimal("0"):
        raise AccountingValidationError("Credit note total must be greater than zero")

    receivable_id = await _resolve_voucher_account_id(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        account_id=None, account_code=SALES_RECEIVABLE_CODE, side="receivable",
    )
    income_id = await _resolve_voucher_account_id(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        account_id=None, account_code=payload.income_account_code, side="income",
    )

    # Mirror of a sales invoice: Dr income (reduce) + Dr output GST (reduce liability); Cr receivable (reduce).
    journal_lines = [
        JournalLineIn(account_id=income_id, debit=taxable_total, credit=Decimal("0")),
    ]
    for gst_amount, code in ((cgst_total, OUTPUT_CGST_CODE), (sgst_total, OUTPUT_SGST_CODE), (igst_total, OUTPUT_IGST_CODE)):
        if gst_amount > Decimal("0"):
            gst_account_id = await _resolve_voucher_account_id(
                session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
                account_id=None, account_code=code, side="output GST",
            )
            journal_lines.append(JournalLineIn(account_id=gst_account_id, debit=gst_amount, credit=Decimal("0")))
    journal_lines.append(JournalLineIn(account_id=receivable_id, debit=Decimal("0"), credit=note_total, party_id=payload.customer_party_id))

    credit_note_id = str(uuid4())
    credit_note_number = await _reserve_sequence_number(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        doc_type="credit_note", prefix="CN", on_date=payload.note_date, fallback_collection=CREDIT_NOTES_COLLECTION,
    )
    ref_suffix = f" against {payload.original_invoice_number}" if payload.original_invoice_number else ""
    description = f"Credit Note {credit_note_number} - {customer.get('party_name') or payload.customer_party_id}{ref_suffix}"
    now = _now()
    doc = {
        "credit_note_id": credit_note_id,
        "credit_note_number": credit_note_number,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "customer_party_id": payload.customer_party_id,
        "customer_name": customer.get("party_name"),
        "customer_gstin": customer.get("gstin"),
        "note_date": payload.note_date.isoformat(),
        "original_invoice_id": payload.original_invoice_id,
        "original_invoice_number": payload.original_invoice_number,
        "reason": payload.reason,
        "is_inter_state": payload.is_inter_state,
        "place_of_supply": payload.place_of_supply,
        "income_account_code": payload.income_account_code,
        "notes": payload.notes,
        "line_items": lines,
        "taxable_total": str(taxable_total),
        "cgst_total": str(cgst_total),
        "sgst_total": str(sgst_total),
        "igst_total": str(igst_total),
        "gst_total": str(gst_total),
        "note_total": str(note_total),
        "status": "posting",
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    if idempotency_key:
        doc["idempotency_key"] = idempotency_key
    credit_notes = get_collection(CREDIT_NOTES_COLLECTION)
    await credit_notes.insert_one(doc)

    try:
        journal_entry, created = await post_journal_entry(
            session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
            created_by=created_by,
            payload=JournalPostRequest(
                entry_date=payload.note_date, description=description, reference=credit_note_number,
                source_module="business", source_document_type="credit_note", source_document_id=credit_note_id,
                lines=journal_lines,
            ),
            idempotency_key=idempotency_key or f"credit-note:{credit_note_id}",
        )
    except Exception:
        await credit_notes.delete_one({"tenant_id": tenant_id, "app_key": app_key, "credit_note_id": credit_note_id})
        raise

    update = {"status": "posted", "journal_entry_id": journal_entry.id, "updated_at": _now()}
    await credit_notes.update_one({"tenant_id": tenant_id, "app_key": app_key, "credit_note_id": credit_note_id}, {"$set": update})
    doc.update(update)
    result = _credit_note_response_doc(doc, created=created)
    await _audit_business_event(
        tenant_id=tenant_id, app_key=app_key, user_id=created_by,
        action="business_credit_note_posted", entity_type="business_credit_note", entity_id=credit_note_id, new_value=result,
    )
    return result


async def cancel_credit_note(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    credit_note_id: str,
    created_by: str,
    payload: CreditNoteCancelRequest,
    idempotency_key: str | None,
) -> dict:
    credit_notes = get_collection(CREDIT_NOTES_COLLECTION)
    filters = {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": payload.accounting_entity_id, "credit_note_id": credit_note_id}
    note = await credit_notes.find_one(filters)
    if note is None:
        raise AccountingNotFoundError("Credit note not found")
    if note.get("status") == "cancelled" and note.get("reversal_journal_entry_id"):
        return _credit_note_response_doc(note, created=False)
    journal_entry_id = note.get("journal_entry_id")
    if not journal_entry_id:
        raise AccountingValidationError("Credit note is not linked to a posted journal entry")
    if note.get("status") != "posted":
        raise AccountingValidationError("Only posted credit notes can be reversed")

    reversal_date = payload.cancel_date or date.today()
    await _validate_reversal_period(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        original_date=note.get("note_date"), reversal_date=reversal_date, document_label="credit note",
    )

    old_note = _credit_note_response_doc(note)
    reversal, created = await reverse_journal_entry(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        created_by=created_by, journal_id=int(journal_entry_id), reversal_date=reversal_date,
        reason=payload.reason, idempotency_key=idempotency_key or f"credit-note-cancel:{credit_note_id}",
    )
    update = {
        "status": "cancelled",
        "reversal_journal_entry_id": reversal.id,
        "cancel_reason": payload.reason,
        "cancelled_at": _now(),
        "updated_at": _now(),
    }
    await credit_notes.update_one(filters, {"$set": update})
    note.update(update)
    result = _credit_note_response_doc(note, created=created)
    await _audit_business_event(
        tenant_id=tenant_id, app_key=app_key, user_id=created_by,
        action="business_credit_note_cancelled", entity_type="business_credit_note", entity_id=credit_note_id,
        old_value=old_note, new_value=result,
    )
    return result


# ===================== Debit Notes (purchase-side GST adjustment) =====================


def _debit_note_response_doc(doc: dict, *, created: bool = False) -> dict:
    result = _json_safe_doc(doc)
    result.setdefault("created", created)
    return result


async def list_debit_notes(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    status: str | None = None,
    limit: int = 100,
) -> dict:
    filters = {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
    if status:
        filters["status"] = status
    safe_limit = max(1, min(int(limit or 100), 500))
    rows = (
        await get_collection(DEBIT_NOTES_COLLECTION)
        .find(filters)
        .sort("note_date", -1)
        .limit(safe_limit)
        .to_list(length=safe_limit)
    )
    return {"items": [_debit_note_response_doc(row) for row in rows], "total": len(rows)}


async def get_debit_note(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    debit_note_id: str,
) -> dict | None:
    row = await get_collection(DEBIT_NOTES_COLLECTION).find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id, "debit_note_id": debit_note_id}
    )
    return _debit_note_response_doc(row) if row else None


async def create_debit_note(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    created_by: str,
    payload: DebitNoteCreateRequest,
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
        existing = await get_collection(DEBIT_NOTES_COLLECTION).find_one(
            {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": payload.accounting_entity_id, "idempotency_key": idempotency_key}
        )
        if existing is not None:
            return _debit_note_response_doc(existing, created=False)

    vendor = await get_party(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id, party_id=payload.vendor_party_id,
    )
    if vendor is None:
        raise AccountingValidationError("Vendor party not found for this tenant")

    if await is_gst_period_locked(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id, period=_period_key(payload.note_date),
    ):
        raise AccountingValidationError(
            f"The {_period_label(_period_key(payload.note_date))} GST period is finalised and locked. Choose a date in an open period."
        )

    lines, taxable_total, cgst_total, sgst_total, igst_total, gst_total, note_total = _compute_invoice_lines(payload)
    if note_total <= Decimal("0"):
        raise AccountingValidationError("Debit note total must be greater than zero")

    payable_id = await _resolve_voucher_account_id(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        account_id=None, account_code=PURCHASE_PAYABLE_CODE, side="payable",
    )
    expense_id = await _resolve_voucher_account_id(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        account_id=None, account_code=payload.expense_account_code, side="expense",
    )

    # Mirror of a purchase bill: Dr payable (reduce); Cr expense (reduce) + Cr Input GST (reduce ITC).
    journal_lines = [
        JournalLineIn(account_id=payable_id, debit=note_total, credit=Decimal("0"), party_id=payload.vendor_party_id),
        JournalLineIn(account_id=expense_id, debit=Decimal("0"), credit=taxable_total),
    ]
    for gst_amount, code in ((cgst_total, INPUT_CGST_CODE), (sgst_total, INPUT_SGST_CODE), (igst_total, INPUT_IGST_CODE)):
        if gst_amount > Decimal("0"):
            input_gst_id = await _resolve_voucher_account_id(
                session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
                account_id=None, account_code=code, side="input GST",
            )
            journal_lines.append(JournalLineIn(account_id=input_gst_id, debit=Decimal("0"), credit=gst_amount))

    debit_note_id = str(uuid4())
    debit_note_number = await _reserve_sequence_number(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        doc_type="debit_note", prefix="DN", on_date=payload.note_date, fallback_collection=DEBIT_NOTES_COLLECTION,
    )
    ref_suffix = f" against {payload.original_bill_number}" if payload.original_bill_number else ""
    description = f"Debit Note {debit_note_number} - {vendor.get('party_name') or payload.vendor_party_id}{ref_suffix}"
    now = _now()
    doc = {
        "debit_note_id": debit_note_id,
        "debit_note_number": debit_note_number,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "vendor_party_id": payload.vendor_party_id,
        "vendor_name": vendor.get("party_name"),
        "vendor_gstin": vendor.get("gstin"),
        "note_date": payload.note_date.isoformat(),
        "original_bill_id": payload.original_bill_id,
        "original_bill_number": payload.original_bill_number,
        "reason": payload.reason,
        "is_inter_state": payload.is_inter_state,
        "place_of_supply": payload.place_of_supply,
        "expense_account_code": payload.expense_account_code,
        "notes": payload.notes,
        "line_items": lines,
        "taxable_total": str(taxable_total),
        "cgst_total": str(cgst_total),
        "sgst_total": str(sgst_total),
        "igst_total": str(igst_total),
        "gst_total": str(gst_total),
        "note_total": str(note_total),
        "status": "posting",
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    if idempotency_key:
        doc["idempotency_key"] = idempotency_key
    debit_notes = get_collection(DEBIT_NOTES_COLLECTION)
    await debit_notes.insert_one(doc)

    try:
        journal_entry, created = await post_journal_entry(
            session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
            created_by=created_by,
            payload=JournalPostRequest(
                entry_date=payload.note_date, description=description, reference=debit_note_number,
                source_module="business", source_document_type="debit_note", source_document_id=debit_note_id,
                lines=journal_lines,
            ),
            idempotency_key=idempotency_key or f"debit-note:{debit_note_id}",
        )
    except Exception:
        await debit_notes.delete_one({"tenant_id": tenant_id, "app_key": app_key, "debit_note_id": debit_note_id})
        raise

    update = {"status": "posted", "journal_entry_id": journal_entry.id, "updated_at": _now()}
    await debit_notes.update_one({"tenant_id": tenant_id, "app_key": app_key, "debit_note_id": debit_note_id}, {"$set": update})
    doc.update(update)
    result = _debit_note_response_doc(doc, created=created)
    await _audit_business_event(
        tenant_id=tenant_id, app_key=app_key, user_id=created_by,
        action="business_debit_note_posted", entity_type="business_debit_note", entity_id=debit_note_id, new_value=result,
    )
    return result


async def cancel_debit_note(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    debit_note_id: str,
    created_by: str,
    payload: DebitNoteCancelRequest,
    idempotency_key: str | None,
) -> dict:
    debit_notes = get_collection(DEBIT_NOTES_COLLECTION)
    filters = {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": payload.accounting_entity_id, "debit_note_id": debit_note_id}
    note = await debit_notes.find_one(filters)
    if note is None:
        raise AccountingNotFoundError("Debit note not found")
    if note.get("status") == "cancelled" and note.get("reversal_journal_entry_id"):
        return _debit_note_response_doc(note, created=False)
    journal_entry_id = note.get("journal_entry_id")
    if not journal_entry_id:
        raise AccountingValidationError("Debit note is not linked to a posted journal entry")
    if note.get("status") != "posted":
        raise AccountingValidationError("Only posted debit notes can be reversed")

    reversal_date = payload.cancel_date or date.today()
    await _validate_reversal_period(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        original_date=note.get("note_date"), reversal_date=reversal_date, document_label="debit note",
    )

    old_note = _debit_note_response_doc(note)
    reversal, created = await reverse_journal_entry(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        created_by=created_by, journal_id=int(journal_entry_id), reversal_date=reversal_date,
        reason=payload.reason, idempotency_key=idempotency_key or f"debit-note-cancel:{debit_note_id}",
    )
    update = {
        "status": "cancelled",
        "reversal_journal_entry_id": reversal.id,
        "cancel_reason": payload.reason,
        "cancelled_at": _now(),
        "updated_at": _now(),
    }
    await debit_notes.update_one(filters, {"$set": update})
    note.update(update)
    result = _debit_note_response_doc(note, created=created)
    await _audit_business_event(
        tenant_id=tenant_id, app_key=app_key, user_id=created_by,
        action="business_debit_note_cancelled", entity_type="business_debit_note", entity_id=debit_note_id,
        old_value=old_note, new_value=result,
    )
    return result


# ===================== GST Settlement (period-end set-off) =====================


def _period_bounds(period: str):
    """Return (first_day, last_day) date objects for a 'YYYY-MM' period."""
    year, month = (int(x) for x in period.split("-"))
    first = date(year, month, 1)
    if month == 12:
        last = date(year, 12, 31)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    return first, last


def _compute_gst_setoff(output: dict, credit: dict):
    """Apply the statutory ITC set-off order (Section 49 / Rule 88A).

    IGST credit -> IGST, then CGST, then SGST.
    CGST credit -> CGST, then IGST (never SGST).
    SGST credit -> SGST, then IGST (never CGST).
    Returns (utilized_by_credit_head, cash_payable_by_liab_head, itc_carry_by_credit_head).
    """
    liab = {h: Decimal(output.get(h, 0)) for h in ("igst", "cgst", "sgst")}
    cr = {h: Decimal(credit.get(h, 0)) for h in ("igst", "cgst", "sgst")}
    utilized = {h: Decimal("0") for h in ("igst", "cgst", "sgst")}

    def apply(credit_head, order):
        for liab_head in order:
            if cr[credit_head] <= 0:
                break
            amt = min(cr[credit_head], liab[liab_head])
            if amt > 0:
                cr[credit_head] -= amt
                liab[liab_head] -= amt
                utilized[credit_head] += amt

    apply("igst", ["igst", "cgst", "sgst"])
    apply("cgst", ["cgst", "igst"])
    apply("sgst", ["sgst", "igst"])

    cash_payable = {h: liab[h] for h in ("igst", "cgst", "sgst")}
    itc_carry = {h: cr[h] for h in ("igst", "cgst", "sgst")}
    return utilized, cash_payable, itc_carry


async def _gst_period_balances(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    period: str,
) -> dict:
    """Net GST accrued in the period per head: output (credit-debit on Output
    accounts) and input/ITC (debit-credit on Input accounts)."""
    first, last = _period_bounds(period)
    codes = {
        OUTPUT_IGST_CODE: ("output", "igst"), OUTPUT_CGST_CODE: ("output", "cgst"), OUTPUT_SGST_CODE: ("output", "sgst"),
        INPUT_IGST_CODE: ("input", "igst"), INPUT_CGST_CODE: ("input", "cgst"), INPUT_SGST_CODE: ("input", "sgst"),
    }
    stmt = (
        select(
            Account.code,
            func.coalesce(func.sum(JournalLine.debit), 0),
            func.coalesce(func.sum(JournalLine.credit), 0),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
        .join(Account, Account.id == JournalLine.account_id)
        .where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.app_key == app_key,
            JournalEntry.accounting_entity_id == accounting_entity_id,
            JournalEntry.entry_date >= first,
            JournalEntry.entry_date <= last,
            Account.code.in_(list(codes.keys())),
        )
        .group_by(Account.code)
    )
    output = {"igst": Decimal("0"), "cgst": Decimal("0"), "sgst": Decimal("0")}
    credit = {"igst": Decimal("0"), "cgst": Decimal("0"), "sgst": Decimal("0")}
    for code, debit_total, credit_total in (await session.execute(stmt)).all():
        kind, head = codes[code]
        debit = Decimal(debit_total or 0)
        cr = Decimal(credit_total or 0)
        if kind == "output":
            output[head] += (cr - debit)  # liability is a credit balance
        else:
            credit[head] += (debit - cr)  # ITC is a debit balance
    # Guard against tiny negatives from rounding.
    for d in (output, credit):
        for h in d:
            if d[h] < 0:
                d[h] = Decimal("0")
    return {"output": output, "credit": credit}


def _settlement_doc_to_response(doc: dict) -> dict:
    heads = ("igst", "cgst", "sgst")
    def amt(section):
        section = section or {}
        return {h: str(section.get(h, "0")) for h in heads}
    return {
        "period": doc.get("period"),
        "accounting_entity_id": doc.get("accounting_entity_id"),
        "output": amt(doc.get("output")),
        "input_credit": amt(doc.get("input_credit")),
        "utilized": amt(doc.get("utilized")),
        "cash_payable": amt(doc.get("cash_payable")),
        "itc_carry_forward": amt(doc.get("itc_carry_forward")),
        "net_cash_payable": str(doc.get("net_cash_payable", "0")),
        "total_output": str(doc.get("total_output", "0")),
        "total_input": str(doc.get("total_input", "0")),
        "status": doc.get("status", "preview"),
        "posted": bool(doc.get("posted")),
        "period_locked": bool(doc.get("period_locked")),
        "journal_entry_id": doc.get("journal_entry_id"),
        "note": doc.get("note"),
        "settled_by": doc.get("settled_by"),
        "settled_at": doc.get("settled_at"),
    }


async def _build_gst_settlement(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    period: str,
) -> dict:
    balances = await _gst_period_balances(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id, period=period,
    )
    output, credit = balances["output"], balances["credit"]
    utilized, cash_payable, itc_carry = _compute_gst_setoff(output, credit)
    net_cash = sum(cash_payable.values())
    total_output = sum(output.values())
    total_input = sum(credit.values())
    note = None
    if total_output == 0 and total_input > 0:
        note = "No output GST this period; input credit carries forward."
    return {
        "period": period,
        "accounting_entity_id": accounting_entity_id,
        "output": {h: str(output[h]) for h in output},
        "input_credit": {h: str(credit[h]) for h in credit},
        "utilized": {h: str(utilized[h]) for h in utilized},
        "cash_payable": {h: str(cash_payable[h]) for h in cash_payable},
        "itc_carry_forward": {h: str(itc_carry[h]) for h in itc_carry},
        "net_cash_payable": str(net_cash),
        "total_output": str(total_output),
        "total_input": str(total_input),
        "note": note,
        "_raw": {"output": output, "credit": credit, "utilized": utilized, "cash_payable": cash_payable, "net_cash": net_cash},
    }


async def preview_gst_settlement(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    period: str,
) -> dict:
    existing = await get_collection(GST_SETTLEMENTS_COLLECTION).find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id, "period": period}
    )
    if existing is not None and existing.get("status") == "posted":
        return _settlement_doc_to_response(existing)
    built = await _build_gst_settlement(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id, period=period,
    )
    built.pop("_raw", None)
    built["status"] = "preview"
    built["posted"] = False
    built["period_locked"] = await is_gst_period_locked(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id, period=period,
    )
    return _settlement_doc_to_response(built)


async def create_gst_settlement(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    created_by: str,
    payload: GstSettlementCreateRequest,
    idempotency_key: str | None,
) -> dict:
    period = payload.period
    settlements = get_collection(GST_SETTLEMENTS_COLLECTION)
    existing = await settlements.find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": payload.accounting_entity_id, "period": period}
    )
    if existing is not None and existing.get("status") == "posted":
        return _settlement_doc_to_response(existing)

    if app_key == "mitrabooks":
        await initialize_default_chart_of_accounts(
            session, tenant_id=tenant_id, app_key=app_key,
            accounting_entity_id=payload.accounting_entity_id, organization_type="BUSINESS",
        )

    built = await _build_gst_settlement(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id, period=period,
    )
    raw = built.pop("_raw")
    output, utilized, net_cash = raw["output"], raw["utilized"], raw["net_cash"]
    if sum(output.values()) <= 0:
        raise AccountingValidationError("No output GST to settle for this period; input credit simply carries forward.")

    # Build the set-off journal entry: Dr Output GST; Cr Input GST (utilized) + Cr GST Payable (net cash).
    journal_lines = []
    for head, code in (("cgst", OUTPUT_CGST_CODE), ("sgst", OUTPUT_SGST_CODE), ("igst", OUTPUT_IGST_CODE)):
        if output[head] > 0:
            acc = await _resolve_voucher_account_id(
                session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
                account_id=None, account_code=code, side="output GST",
            )
            journal_lines.append(JournalLineIn(account_id=acc, debit=output[head], credit=Decimal("0")))
    for head, code in (("cgst", INPUT_CGST_CODE), ("sgst", INPUT_SGST_CODE), ("igst", INPUT_IGST_CODE)):
        if utilized[head] > 0:
            acc = await _resolve_voucher_account_id(
                session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
                account_id=None, account_code=code, side="input GST",
            )
            journal_lines.append(JournalLineIn(account_id=acc, debit=Decimal("0"), credit=utilized[head]))
    if net_cash > 0:
        payable_acc = await _resolve_voucher_account_id(
            session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
            account_id=None, account_code=GST_PAYABLE_CODE, side="GST payable",
        )
        journal_lines.append(JournalLineIn(account_id=payable_acc, debit=Decimal("0"), credit=net_cash))

    _, last = _period_bounds(period)
    journal_entry, _created = await post_journal_entry(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        created_by=created_by,
        payload=JournalPostRequest(
            entry_date=last,
            description=f"GST settlement for {_period_label(period)}",
            reference=f"GST-{period}",
            source_module="business", source_document_type="gst_settlement", source_document_id=period,
            lines=journal_lines,
        ),
        idempotency_key=idempotency_key or f"gst-settlement:{tenant_id}:{payload.accounting_entity_id}:{period}",
    )

    period_locked = False
    if payload.lock_period:
        await set_gst_period_lock(
            tenant_id=tenant_id, app_key=app_key, updated_by=created_by,
            payload=GstPeriodLockUpdateRequest(period=period, locked=True, note=f"Auto-locked on GST settlement", accounting_entity_id=payload.accounting_entity_id),
        )
        period_locked = True

    doc = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        **built,
        "status": "posted",
        "posted": True,
        "period_locked": period_locked,
        "journal_entry_id": journal_entry.id,
        "settled_by": created_by,
        "settled_at": _now(),
        "created_at": _now(),
        "updated_at": _now(),
    }
    filters = {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": payload.accounting_entity_id, "period": period}
    await settlements.update_one(filters, {"$set": doc, "$setOnInsert": filters}, upsert=True)
    result = _settlement_doc_to_response(doc)
    await _audit_business_event(
        tenant_id=tenant_id, app_key=app_key, user_id=created_by,
        action="business_gst_settlement_posted", entity_type="business_gst_settlement", entity_id=period, new_value=result,
    )
    return result


# ============ Party sub-ledger (party-wise Debtors / Creditors) ============


async def party_wise_ledger(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    kind: str,
    as_of: date | None = None,
) -> dict:
    """Party-wise Sundry Debtors (receivable) / Creditors (payable), enriched with
    party names from Mongo. Ties to the matching Trial Balance account total."""
    as_of = as_of or date.today()
    lines, total = await get_party_wise_balances(
        session, tenant_id=tenant_id, as_of=as_of, kind=kind, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    party_ids = [l["party_id"] for l in lines if l["party_id"]]
    names: dict[str, str | None] = {}
    if party_ids:
        rows = await (
            get_collection(PARTIES_COLLECTION)
            .find({
                "tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id,
                "party_id": {"$in": party_ids},
            })
            .to_list(length=len(party_ids))
        )
        names = {r["party_id"]: r.get("party_name") for r in rows}

    items = []
    for l in lines:
        pid = l["party_id"]
        items.append({
            "party_id": pid,
            "party_name": (names.get(pid) or pid) if pid else "Unallocated (direct entries)",
            "balance": str(l["balance"]),
        })
    # Named parties first (largest balance on top); the Unallocated bucket last.
    items.sort(key=lambda x: (x["party_id"] is None, -Decimal(x["balance"])))
    return {
        "as_of": as_of.isoformat(),
        "kind": kind,
        "accounting_entity_id": accounting_entity_id,
        "items": items,
        "total_balance": str(total),
        "count": len(items),
    }


async def party_outstanding_summary(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    party_id: str,
    as_of: date | None = None,
) -> dict:
    """Net receivable and payable outstanding for one party (for the voucher form)."""
    as_of = as_of or date.today()
    party = await get_party(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id, party_id=party_id,
    )
    if party is None:
        raise AccountingNotFoundError("Party not found")
    balances = await get_party_outstanding(
        session, tenant_id=tenant_id, party_id=party_id, as_of=as_of, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    return {
        "party_id": party_id,
        "party_name": party.get("party_name"),
        "party_type": party.get("party_type"),
        "as_of": as_of.isoformat(),
        "receivable": str(balances["receivable"]),
        "payable": str(balances["payable"]),
    }
