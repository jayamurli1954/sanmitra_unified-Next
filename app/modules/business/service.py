import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
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
from app.modules.business.dimensions import validate_dimension_refs
from app.modules.business.schemas import (
    ApprovalReviewRequest,
    GstPeriodLockUpdateRequest,
    TypedVoucherCreateRequest,
    TypedVoucherReversalRequest,
)

PARTIES_COLLECTION = "business_parties"
VOUCHERS_COLLECTION = "business_vouchers"
VOUCHER_COUNTERS_COLLECTION = "business_voucher_counters"
SALES_INVOICES_COLLECTION = "business_sales_invoices"
PURCHASE_BILLS_COLLECTION = "business_purchase_bills"
INVOICE_SETTINGS_COLLECTION = "business_invoice_settings"
ADMIN_SETTINGS_COLLECTION = "business_admin_settings"
GST_PERIOD_LOCKS_COLLECTION = "business_gst_period_locks"
CREDIT_NOTES_COLLECTION = "business_credit_notes"
DEBIT_NOTES_COLLECTION = "business_debit_notes"
GST_SETTLEMENTS_COLLECTION = "business_gst_settlements"
CA_DOCUMENTS_COLLECTION = "business_ca_document_metadata"
CA_CLIENTS_COLLECTION = "business_ca_clients"
BUSINESS_DOCUMENT_ATTACHMENTS_COLLECTION = "business_document_attachments"

_logger = logging.getLogger(__name__)
BUSINESS_ATTACHMENT_STORAGE_DIR = Path(__file__).resolve().parent / "data" / "uploads" / "attachments"
MAX_BUSINESS_ATTACHMENT_BYTES = 10 * 1024 * 1024
ALLOWED_BUSINESS_ATTACHMENT_TYPES: dict[str, set[str]] = {
    "application/pdf": {".pdf"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
    "text/csv": {".csv"},
    "application/vnd.ms-excel": {".xls"},
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {".xlsx"},
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
}

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


def _apply_approval_defaults(result: dict) -> dict:
    result.setdefault("approval_required", False)
    result.setdefault("approval_status", "auto_posted")
    result.setdefault("approval_submitted_at", None)
    result.setdefault("approval_submitted_by", None)
    result.setdefault("approval_decided_at", None)
    result.setdefault("approval_decided_by", None)
    result.setdefault("approval_notes", None)
    result.setdefault("rejection_reason", None)
    return result


def _voucher_response_doc(doc: dict, *, created: bool = False) -> dict:
    result = _json_safe_doc(doc)
    _apply_approval_defaults(result)
    result.setdefault("journal_entry_id", None)
    result.setdefault("reversal_journal_entry_id", None)
    result.setdefault("reversal_reason", None)
    result.setdefault("reversed_at", None)
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


async def _reverse_after_domain_persistence_failure(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    created_by: str,
    journal_entry_id: int,
    document_label: str,
    document_id: str,
    reversal_reason: str,
    reversal_idempotency_key: str,
) -> None:
    try:
        await reverse_journal_entry(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=accounting_entity_id,
            created_by=created_by,
            journal_id=int(journal_entry_id),
            reason=reversal_reason,
            idempotency_key=reversal_idempotency_key,
        )
    except Exception as reversal_exc:
        _logger.exception(
            "Business compensation reversal failed for %s %s after persistence failure",
            document_label,
            document_id,
        )
        raise AccountingValidationError(
            f"{document_label} persistence failed after journal posting, and automatic reversal also failed"
        ) from reversal_exc


async def _compensate_gst_settlement_failure(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    created_by: str,
    period: str,
    journal_entry_id: int,
    unlock_period: bool,
    failure_label: str,
) -> None:
    unlock_failed = False
    reverse_failed = False

    if unlock_period:
        try:
            await set_gst_period_lock(
                tenant_id=tenant_id,
                app_key=app_key,
                updated_by=created_by,
                payload=GstPeriodLockUpdateRequest(
                    period=period,
                    locked=False,
                    note="Automatic unlock after GST settlement persistence failure",
                    accounting_entity_id=accounting_entity_id,
                ),
            )
        except Exception:
            unlock_failed = True
            _logger.exception("GST period unlock failed during settlement compensation for %s", period)

    try:
        await reverse_journal_entry(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=accounting_entity_id,
            created_by=created_by,
            journal_id=int(journal_entry_id),
            reason=f"Compensation after GST settlement persistence failure for {period}",
            idempotency_key=f"gst-settlement-compensate:{tenant_id}:{accounting_entity_id}:{period}:{journal_entry_id}",
        )
    except Exception:
        reverse_failed = True
        _logger.exception("GST settlement journal reversal failed during compensation for %s", period)

    if unlock_failed and reverse_failed:
        raise AccountingValidationError(
            f"{failure_label} after GST settlement journal posting, and automatic period unlock plus journal reversal both failed"
        )
    if unlock_failed:
        raise AccountingValidationError(
            f"{failure_label} after GST settlement journal posting; the accounting entry was automatically reversed, but automatic GST period unlock failed"
        )
    if reverse_failed:
        raise AccountingValidationError(
            f"{failure_label} after GST settlement journal posting; the GST period compensation ran, but automatic journal reversal failed"
        )


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
    ca_clients = get_collection(CA_CLIENTS_COLLECTION)
    await ca_clients.create_index([("tenant_id", 1), ("app_key", 1), ("client_id", 1)], unique=True)
    await ca_clients.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("client_name", 1)])
    attachments = get_collection(BUSINESS_DOCUMENT_ATTACHMENTS_COLLECTION)
    await attachments.create_index([("tenant_id", 1), ("app_key", 1), ("attachment_id", 1)], unique=True)
    await attachments.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("owner_type", 1), ("owner_id", 1), ("uploaded_at", -1)])
    invoices = get_collection(SALES_INVOICES_COLLECTION)
    await invoices.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("invoice_date", -1)])
    await invoices.create_index([("tenant_id", 1), ("app_key", 1), ("invoice_id", 1)], unique=True)
    await invoices.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("idempotency_key", 1)], unique=True, sparse=True)
    invoice_settings = get_collection(INVOICE_SETTINGS_COLLECTION)
    await invoice_settings.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1)], unique=True)
    admin_settings = get_collection(ADMIN_SETTINGS_COLLECTION)
    await admin_settings.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1)], unique=True)
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


# CA client / document-metadata CRUD moved to services/ca_clients.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md). The facade re-export lives at the
# bottom of this module (after shared helpers are defined).

# Party master CRUD moved to services/parties.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); re-exported here so later
# facades (credit/debit notes, sales invoices, purchase bills) can import get_party.
from app.modules.business.services.parties import (  # noqa: E402
    create_party as create_party,
    deactivate_party as deactivate_party,
    get_party as get_party,
    list_parties as list_parties,
    update_party as update_party,
)


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
    status: str | None = None,
    approval_status: str | None = None,
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
    if status:
        filters["status"] = status
    if approval_status:
        filters["approval_status"] = approval_status

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


async def review_typed_voucher(
    *,
    session: AsyncSession | None = None,
    tenant_id: str,
    app_key: str,
    voucher_id: str,
    reviewed_by: str,
    payload: ApprovalReviewRequest,
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
        raise AccountingNotFoundError("Voucher not found")
    old_value = _voucher_response_doc(voucher)
    current_status = str(voucher.get("status") or "").strip().lower()
    if current_status in {"draft", "pending_approval"}:
        if current_status == "draft":
            raise AccountingValidationError("Only submitted vouchers can be approved or rejected")
        if payload.approve:
            return await _approve_typed_voucher_document(
                session=session,
                tenant_id=tenant_id,
                app_key=app_key,
                reviewed_by=reviewed_by,
                voucher=voucher,
                old_value=old_value,
                approval_notes=payload.notes,
            )
        patch = {
            "status": "rejected",
            "approval_required": True,
            "approval_status": "rejected",
            "approval_decided_at": _now(),
            "approval_decided_by": reviewed_by,
            "approval_notes": payload.notes,
            "rejection_reason": payload.rejection_reason or "Rejected during manual review",
            "updated_at": _now(),
        }
        if voucher.get("approval_submitted_at") is None:
            patch["approval_submitted_at"] = voucher.get("created_at")
            patch["approval_submitted_by"] = voucher.get("created_by")
        await vouchers.update_one(filters, {"$set": patch})
        voucher.update(patch)
        result = _voucher_response_doc(voucher)
        await _audit_business_event(
            tenant_id=tenant_id,
            app_key=app_key,
            user_id=reviewed_by,
            action="business_voucher_reviewed",
            entity_type="business_voucher",
            entity_id=voucher_id,
            old_value=old_value,
            new_value=result,
        )
        return result
    if current_status != "posted":
        raise AccountingValidationError("Only posted or pending-approval vouchers can be reviewed")

    approval_status = "approved" if payload.approve else "rejected"
    patch = {
        "approval_required": True,
        "approval_status": approval_status,
        "approval_decided_at": _now(),
        "approval_decided_by": reviewed_by,
        "approval_notes": payload.notes,
        "rejection_reason": None if payload.approve else (payload.rejection_reason or "Rejected during manual review"),
        "updated_at": _now(),
    }
    if voucher.get("approval_submitted_at") is None:
        patch["approval_submitted_at"] = voucher.get("created_at")
        patch["approval_submitted_by"] = voucher.get("created_by")

    await vouchers.update_one(filters, {"$set": patch})
    voucher.update(patch)
    result = _voucher_response_doc(voucher)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=reviewed_by,
        action="business_voucher_reviewed",
        entity_type="business_voucher",
        entity_id=voucher_id,
        old_value=old_value,
        new_value=result,
    )
    return result


async def _approve_typed_voucher_document(
    *,
    session,
    tenant_id: str,
    app_key: str,
    reviewed_by: str,
    voucher: dict,
    old_value: dict,
    approval_notes: str | None,
) -> dict:
    if session is None:
        raise AccountingValidationError("Approval posting requires an active accounting session")

    voucher_id = str(voucher.get("voucher_id") or "")
    voucher_number = str(voucher.get("voucher_number") or voucher_id)
    accounting_entity_id = str(voucher.get("accounting_entity_id") or "primary")
    entry_date = date.fromisoformat(str(voucher.get("entry_date") or "")[:10])
    amount = Decimal(str(voucher.get("amount") or "0")).quantize(Decimal("0.01"))
    debit_account_id = int(voucher.get("debit_account_id"))
    credit_account_id = int(voucher.get("credit_account_id"))
    party_id = voucher.get("party_id")
    voucher_type = str(voucher.get("voucher_type") or "journal")
    description = str(voucher.get("description") or f"{voucher_type.title()} voucher")
    reference = str(voucher.get("reference") or voucher_number)
    vouchers = get_collection(VOUCHERS_COLLECTION)

    try:
        journal_entry, created = await post_journal_entry(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=accounting_entity_id,
            created_by=reviewed_by,
            payload=JournalPostRequest(
                entry_date=entry_date,
                description=description,
                reference=reference,
                source_module="business",
                source_document_type="voucher",
                source_document_id=voucher_id,
                lines=[
                    JournalLineIn(
                        account_id=debit_account_id,
                        debit=amount,
                        credit=Decimal("0"),
                        party_id=party_id if voucher_type == "payment" else None,
                    ),
                    JournalLineIn(
                        account_id=credit_account_id,
                        debit=Decimal("0"),
                        credit=amount,
                        party_id=party_id if voucher_type == "receipt" else None,
                    ),
                ],
            ),
            idempotency_key=f"business-voucher:{voucher_id}",
        )
    except Exception as exc:
        raise AccountingValidationError(f"Voucher approval posting failed: {exc}") from exc

    patch = {
        "status": "posted",
        "journal_entry_id": journal_entry.id,
        "approval_required": True,
        "approval_status": "approved",
        "approval_submitted_at": voucher.get("approval_submitted_at") or voucher.get("created_at"),
        "approval_submitted_by": voucher.get("approval_submitted_by") or voucher.get("created_by"),
        "approval_decided_at": _now(),
        "approval_decided_by": reviewed_by,
        "approval_notes": approval_notes or "Approved and posted",
        "rejection_reason": None,
        "updated_at": _now(),
    }
    try:
        await vouchers.update_one(
            {"tenant_id": tenant_id, "app_key": app_key, "voucher_id": voucher_id},
            {"$set": patch},
        )
    except Exception as exc:
        await _reverse_after_domain_persistence_failure(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=accounting_entity_id,
            created_by=reviewed_by,
            journal_entry_id=int(journal_entry.id),
            document_label="Business voucher",
            document_id=voucher_id,
            reversal_reason=f"Compensation after business voucher approval persistence failure for {voucher_number}",
            reversal_idempotency_key=f"business-voucher-approve-compensate:{voucher_id}:{journal_entry.id}",
        )
        raise AccountingValidationError(
            "Business voucher approval persistence failed after journal posting; the accounting entry was automatically reversed"
        ) from exc
    voucher.update(patch)
    result = _voucher_response_doc(voucher, created=created)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=reviewed_by,
        action="business_voucher_reviewed",
        entity_type="business_voucher",
        entity_id=voucher_id,
        old_value=old_value,
        new_value=result,
    )
    return result


# Document attachment upload/list/download moved to services/document_attachments.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md). The facade re-export lives at the
# bottom of this module.

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

    await validate_dimension_refs(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        cost_centre_id=payload.cost_centre_id,
        project_id=payload.project_id,
    )

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
        "cost_centre_id": payload.cost_centre_id,
        "project_id": payload.project_id,
        "amount": _money(amount),
        "entry_date": payload.entry_date.isoformat(),
        "debit_account_id": debit_account_id,
        "credit_account_id": credit_account_id,
        "description": payload.description,
        "reference": reference,
        "status": "pending_approval",
        "approval_required": True,
        "approval_status": "pending_approval",
        "approval_submitted_at": now,
        "approval_submitted_by": created_by,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    if idempotency_key:
        doc["idempotency_key"] = idempotency_key
    vouchers = get_collection(VOUCHERS_COLLECTION)
    await vouchers.insert_one(doc)

    result = _voucher_response_doc(doc, created=True)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="business_voucher_created",
        entity_type="business_voucher",
        entity_id=voucher_id,
        new_value=result,
    )
    return result


# ===================== Sales Invoices (GST) =====================


# Invoice line computation / numbering moved to services/invoice_computation.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); re-exported here so later
# facades (sales/purchase invoices, credit/debit notes) can import shared helpers.
from app.modules.business.services.invoice_computation import (  # noqa: E402
    _compute_invoice_lines as _compute_invoice_lines,
    _invoice_response_doc as _invoice_response_doc,
    _q2 as _q2,
    _reserve_invoice_number as _reserve_invoice_number,
    _validate_required_invoice_fields as _validate_required_invoice_fields,
)

# Invoice / admin settings moved to services/invoice_settings.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); re-exported here so later
# facades (sales/purchase invoices, GST returns) can import get_invoice_settings.
from app.modules.business.services.invoice_settings import (  # noqa: E402
    get_business_admin_settings as get_business_admin_settings,
    get_gst_profile as get_gst_profile,
    get_invoice_settings as get_invoice_settings,
    save_business_admin_settings as save_business_admin_settings,
    save_invoice_settings as save_invoice_settings,
    set_hr_enabled as set_hr_enabled,
    set_module_enabled as set_module_enabled,
)

# GST period locks moved to services/gst_period_locks.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); re-exported here so later
# facades (credit/debit notes, sales/purchase invoices, ITC, GST settlement) can
# import _validate_reversal_period / is_gst_period_locked.
from app.modules.business.services.gst_period_locks import (  # noqa: E402
    _period_key as _period_key,
    _period_label as _period_label,
    _validate_reversal_period as _validate_reversal_period,
    is_gst_period_locked as is_gst_period_locked,
    list_gst_period_locks as list_gst_period_locks,
    set_gst_period_lock as set_gst_period_lock,
)


# Sales Invoice documents moved to services/sales_invoices.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md). The facade re-export lives at the
# end of this module: sales_invoices imports GST-period helpers defined further below.


# ===================== Purchase Bills (Input GST / ITC) =====================


# Purchase Bill documents moved to services/purchase_bills.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md). The facade re-export lives at the
# end of this module: purchase_bills imports GST-period helpers defined further below.


# ============== ITC Reversal (GST Rule 37 — 180-day non-payment) ==============


# Rule 37 ITC reversal/reclaim moved to services/itc_reversal.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md). The facade re-export lives at the
# end of this module: itc_reversal imports the GST-period helpers re-exported above.


# ===================== Credit Notes (sales-side GST adjustment) =====================


# Credit/debit note sequence numbers moved to services/document_numbering.py
from app.modules.business.services.document_numbering import (  # noqa: E402
    _reserve_sequence_number as _reserve_sequence_number,
)

# Credit Notes moved to services/credit_notes.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); re-exported for compatibility.
from app.modules.business.services.credit_notes import (  # noqa: E402
    cancel_credit_note as cancel_credit_note,
    create_credit_note as create_credit_note,
    get_credit_note as get_credit_note,
    list_credit_notes as list_credit_notes,
    review_credit_note as review_credit_note,
)


# ===================== Debit Notes (purchase-side GST adjustment) =====================


# Debit Notes moved to services/debit_notes.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); re-exported for compatibility.
from app.modules.business.services.debit_notes import (  # noqa: E402
    cancel_debit_note as cancel_debit_note,
    create_debit_note as create_debit_note,
    get_debit_note as get_debit_note,
    list_debit_notes as list_debit_notes,
    review_debit_note as review_debit_note,
)


# ===================== GST Settlement (period-end set-off) =====================


# GST Settlement moved to services/gst_settlement.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); re-exported for compatibility.
from app.modules.business.services.gst_settlement import (  # noqa: E402
    _compute_gst_setoff as _compute_gst_setoff,
    _period_bounds as _period_bounds,
    create_gst_settlement as create_gst_settlement,
    preview_gst_settlement as preview_gst_settlement,
    reverse_gst_settlement as reverse_gst_settlement,
)


# Party sub-ledger reads were moved to services/party_ledger.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); re-exported for compatibility.
from app.modules.business.services.party_ledger import (  # noqa: E402
    party_outstanding_summary as party_outstanding_summary,
    party_wise_ledger as party_wise_ledger,
)


# Purchase Bill documents moved to services/purchase_bills.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); re-exported for compatibility.
# Placed before itc_reversal: itc_reversal imports _bill_response_doc from purchase_bills.
from app.modules.business.services.purchase_bills import (  # noqa: E402
    cancel_purchase_bill as cancel_purchase_bill,
    create_purchase_bill as create_purchase_bill,
    get_purchase_bill as get_purchase_bill,
    list_purchase_bills as list_purchase_bills,
    review_purchase_bill as review_purchase_bill,
)


# Rule 37 ITC reversal/reclaim moved to services/itc_reversal.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); re-exported for compatibility.
from app.modules.business.services.itc_reversal import (  # noqa: E402
    mark_bill_payment as mark_bill_payment,
    preview_itc_reversals as preview_itc_reversals,
    reclaim_itc_for_bill as reclaim_itc_for_bill,
    reverse_itc_for_bill as reverse_itc_for_bill,
)


# Sales Invoice documents moved to services/sales_invoices.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); re-exported for compatibility.
# Placed last: sales_invoices imports GST-period helpers defined above in this module.
from app.modules.business.services.sales_invoices import (  # noqa: E402
    cancel_sales_invoice as cancel_sales_invoice,
    create_sales_invoice as create_sales_invoice,
    get_sales_invoice as get_sales_invoice,
    list_sales_invoices as list_sales_invoices,
    review_sales_invoice as review_sales_invoice,
)

# CA client / document-metadata CRUD moved to services/ca_clients.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); re-exported for compatibility.
from app.modules.business.services.ca_clients import (  # noqa: E402
    create_ca_client as create_ca_client,
    create_ca_document_metadata as create_ca_document_metadata,
    list_ca_clients as list_ca_clients,
    list_ca_document_metadata as list_ca_document_metadata,
    update_ca_client as update_ca_client,
    update_ca_document_metadata as update_ca_document_metadata,
)

# Document attachment upload/list/download moved to services/document_attachments.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); re-exported for compatibility.
from app.modules.business.services.document_attachments import (  # noqa: E402
    create_business_document_attachment as create_business_document_attachment,
    download_business_document_attachment as download_business_document_attachment,
    list_business_document_attachments as list_business_document_attachments,
)

# Approval queue listing moved to services/approval_queue.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); re-exported for compatibility.
from app.modules.business.services.approval_queue import (  # noqa: E402
    list_documents_for_approval_queue as list_documents_for_approval_queue,
)
