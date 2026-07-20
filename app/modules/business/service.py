import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
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
    BusinessAdminSettings,
    BusinessAdminSettingsUpdateRequest,
    BusinessAiSettings,
    BusinessIntegrationSettings,
    GstPeriodLockUpdateRequest,
    INVOICE_STANDARD_FIELDS,
    InvoiceSettings,
    InvoiceSettingsUpdateRequest,
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


def _safe_attachment_file_name(file_name: str | None) -> str:
    raw = str(file_name or "attachment").strip().replace("\\", " ").replace("/", " ")
    cleaned = "".join(ch for ch in raw if ch >= " " and ch != "\x7f").strip().strip(".")
    return cleaned[:240] or "attachment"



def _normalize_attachment_content_type(content_type: str | None) -> str:
    return str(content_type or "").split(";")[0].strip().lower()


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


def _business_attachment_response_doc(doc: dict) -> dict:
    result = _json_safe_doc(doc)
    result.pop("stored_file_path", None)
    return result


async def _get_business_attachment_owner(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    owner_type: str,
    owner_id: str,
) -> tuple[dict, str]:
    normalized_owner_type = str(owner_type or "").strip().lower()
    owner_filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
    }
    if normalized_owner_type == "sales_invoice":
        owner = await get_collection(SALES_INVOICES_COLLECTION).find_one({**owner_filters, "invoice_id": owner_id})
        if owner is None:
            raise AccountingNotFoundError("Sales invoice not found")
        return owner, "invoice_id"
    if normalized_owner_type == "purchase_bill":
        owner = await get_collection(PURCHASE_BILLS_COLLECTION).find_one({**owner_filters, "bill_id": owner_id})
        if owner is None:
            raise AccountingNotFoundError("Purchase bill not found")
        return owner, "bill_id"
    if normalized_owner_type == "ca_document":
        owner = await get_collection(CA_DOCUMENTS_COLLECTION).find_one({**owner_filters, "document_id": owner_id})
        if owner is None:
            raise AccountingNotFoundError("CA document metadata not found")
        return owner, "document_id"
    raise AccountingValidationError(f"Unsupported business attachment owner type: {owner_type}")


async def create_business_document_attachment(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    owner_type: str,
    owner_id: str,
    uploaded_by: str,
    file_name: str,
    content_type: str | None,
    payload: bytes,
) -> dict:
    normalized_content_type = _normalize_attachment_content_type(content_type)
    if normalized_content_type not in ALLOWED_BUSINESS_ATTACHMENT_TYPES:
        raise AccountingValidationError(f"Unsupported attachment type: {normalized_content_type or 'unknown'}")
    if not payload:
        raise AccountingValidationError("Uploaded file is empty")
    if len(payload) > MAX_BUSINESS_ATTACHMENT_BYTES:
        raise AccountingValidationError("Attachment file exceeds the 10 MB limit")
    safe_name = _safe_attachment_file_name(file_name)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in ALLOWED_BUSINESS_ATTACHMENT_TYPES[normalized_content_type]:
        raise AccountingValidationError("Attachment filename extension does not match the supplied content type")

    owner, _owner_key = await _get_business_attachment_owner(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        owner_type=owner_type,
        owner_id=owner_id,
    )

    attachment_id = str(uuid4())
    now = _now()
    stored_file_path = (
        BUSINESS_ATTACHMENT_STORAGE_DIR
        / tenant_id
        / app_key
        / accounting_entity_id
        / f"{attachment_id}{suffix}"
    )
    stored_file_path.parent.mkdir(parents=True, exist_ok=True)
    stored_file_path.write_bytes(payload)

    doc = {
        "attachment_id": attachment_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "owner_type": str(owner_type).strip().lower(),
        "owner_id": owner_id,
        "file_name": safe_name,
        "content_type": normalized_content_type,
        "size_bytes": len(payload),
        "stored_file_path": str(stored_file_path),
        "uploaded_by": uploaded_by,
        "uploaded_at": now,
        "created_at": now,
        "updated_at": now,
    }
    await get_collection(BUSINESS_DOCUMENT_ATTACHMENTS_COLLECTION).insert_one(doc)
    if str(owner_type).strip().lower() == "ca_document":
        attachment_count = await get_collection(BUSINESS_DOCUMENT_ATTACHMENTS_COLLECTION).count_documents(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "accounting_entity_id": accounting_entity_id,
                "owner_type": "ca_document",
                "owner_id": owner_id,
            }
        )
        await get_collection(CA_DOCUMENTS_COLLECTION).update_one(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "accounting_entity_id": accounting_entity_id,
                "document_id": owner_id,
            },
            {
                "$set": {
                    "attachment_count": attachment_count,
                    "last_attachment_at": now,
                    "updated_at": now,
                }
            },
        )
    result = _business_attachment_response_doc(doc)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=uploaded_by,
        action="business_document_attachment_uploaded",
        entity_type="business_document_attachment",
        entity_id=attachment_id,
        new_value=result,
    )
    return result


async def list_business_document_attachments(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    owner_type: str,
    owner_id: str,
    limit: int = 100,
) -> dict:
    await _get_business_attachment_owner(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        owner_type=owner_type,
        owner_id=owner_id,
    )
    safe_limit = max(1, min(int(limit or 100), 500))
    rows = (
        await get_collection(BUSINESS_DOCUMENT_ATTACHMENTS_COLLECTION)
        .find(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "accounting_entity_id": accounting_entity_id,
                "owner_type": str(owner_type).strip().lower(),
                "owner_id": owner_id,
            }
        )
        .sort("uploaded_at", -1)
        .limit(safe_limit)
        .to_list(length=safe_limit)
    )
    return {"items": [_business_attachment_response_doc(row) for row in rows], "total": len(rows)}


async def download_business_document_attachment(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    owner_type: str,
    owner_id: str,
    attachment_id: str,
    downloaded_by: str,
) -> dict:
    await _get_business_attachment_owner(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        owner_type=owner_type,
        owner_id=owner_id,
    )
    doc = await get_collection(BUSINESS_DOCUMENT_ATTACHMENTS_COLLECTION).find_one(
        {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "accounting_entity_id": accounting_entity_id,
            "owner_type": str(owner_type).strip().lower(),
            "owner_id": owner_id,
            "attachment_id": attachment_id,
        }
    )
    if doc is None:
        raise AccountingNotFoundError("Business document attachment not found")
    stored_file_path = Path(str(doc.get("stored_file_path") or "")).resolve()
    try:
        payload = stored_file_path.read_bytes()
    except FileNotFoundError as exc:
        raise AccountingNotFoundError("Business document attachment file is missing") from exc
    result = _business_attachment_response_doc(doc)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=downloaded_by,
        action="business_document_attachment_downloaded",
        entity_type="business_document_attachment",
        entity_id=attachment_id,
        new_value=result,
    )
    return {**result, "payload": payload}


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


def _q2(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _invoice_response_doc(doc: dict, *, created: bool = False) -> dict:
    result = _json_safe_doc(doc)
    _apply_approval_defaults(result)
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
            "cost_centre_id": getattr(item, "cost_centre_id", None),
            "project_id": getattr(item, "project_id", None),
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
        stored = {
            k: v for k, v in row.items()
            if k in {"field_config", "numbering", "custom_fields", "branding", "inventory_enabled",
                     "inventory_valuation_policy", "hr_enabled", "cost_centre_enabled", "manufacturing_enabled"}
        }
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
        inventory_enabled=payload.inventory_enabled,
        inventory_valuation_policy=payload.inventory_valuation_policy,
        hr_enabled=payload.hr_enabled,
        cost_centre_enabled=payload.cost_centre_enabled,
        manufacturing_enabled=payload.manufacturing_enabled,
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


async def get_business_admin_settings(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
) -> dict:
    row = await get_collection(ADMIN_SETTINGS_COLLECTION).find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
    )
    if row is None:
        result = BusinessAdminSettings().model_dump()
    else:
        stored = {
            k: v for k, v in row.items()
            if k in {
                "organization",
                "branches",
                "roles",
                "permissions",
                "voucher_configuration",
                "financial_controls",
                "security",
                "templates",
                "notifications",
                "subscription_billing",
                "integrations",
                "ai_settings",
            }
        }
        result = BusinessAdminSettings(**stored).model_dump()
    result.update(
        {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "accounting_entity_id": accounting_entity_id,
            "updated_by": (row or {}).get("updated_by"),
            "updated_at": (row or {}).get("updated_at"),
        }
    )
    return result


async def save_business_admin_settings(
    *,
    tenant_id: str,
    app_key: str,
    updated_by: str,
    payload: BusinessAdminSettingsUpdateRequest,
) -> dict:
    accounting_entity_id = payload.accounting_entity_id
    settings = BusinessAdminSettings(
        organization=payload.organization,
        branches=payload.branches,
        roles=payload.roles,
        permissions=payload.permissions,
        voucher_configuration=payload.voucher_configuration,
        financial_controls=payload.financial_controls,
        security=payload.security,
        templates=payload.templates,
        notifications=payload.notifications,
        subscription_billing=payload.subscription_billing,
        integrations=BusinessIntegrationSettings(**payload.integrations.model_dump()),
        ai_settings=BusinessAiSettings(
            **{
                **payload.ai_settings.model_dump(),
                "auto_post_to_ledger": False,
                "document_review_required": True,
                "posting_review_required": True,
            }
        ),
    )
    doc = settings.model_dump(mode="json")
    doc.update({"updated_by": updated_by, "updated_at": _now()})
    filters = {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
    await get_collection(ADMIN_SETTINGS_COLLECTION).update_one(
        filters,
        {"$set": doc, "$setOnInsert": {**filters, "created_at": _now()}},
        upsert=True,
    )
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=updated_by,
        action="business_admin_settings_updated",
        entity_type="business_admin_settings",
        entity_id=accounting_entity_id,
        new_value=doc,
    )
    return await get_business_admin_settings(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
    )


async def set_hr_enabled(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, enabled: bool, updated_by: str
) -> bool:
    """Tenant-admin toggle for the HR add-on — flips just InvoiceSettings.hr_enabled
    (upserting the settings doc) without needing the full settings payload."""
    filters = {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
    await get_collection(INVOICE_SETTINGS_COLLECTION).update_one(
        filters,
        {"$set": {"hr_enabled": bool(enabled), "updated_by": updated_by, "updated_at": _now()},
         "$setOnInsert": {**filters, "created_at": _now()}},
        upsert=True,
    )
    await _audit_business_event(
        tenant_id=tenant_id, app_key=app_key, user_id=updated_by,
        action="business_hr_enabled_toggled", entity_type="business_invoice_settings",
        entity_id=accounting_entity_id, new_value={"hr_enabled": bool(enabled)},
    )
    return bool(enabled)


_MODULE_ENABLE_FLAGS = {"cost_centre_enabled", "manufacturing_enabled"}


async def set_module_enabled(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, flag: str, enabled: bool, updated_by: str,
) -> dict:
    """Tenant-admin toggle for an enterprise module flag on InvoiceSettings
    (cost_centre_enabled / manufacturing_enabled), upserting the settings doc.

    Manufacturing depends on cost centres, so enabling manufacturing implies
    cost centres ON, and disabling cost centres also disables manufacturing —
    the two flags can never end up in a contradictory state."""
    if flag not in _MODULE_ENABLE_FLAGS:
        raise ValueError(f"Unknown module flag '{flag}'")
    updates = {flag: bool(enabled)}
    if flag == "manufacturing_enabled" and enabled:
        updates["cost_centre_enabled"] = True
    if flag == "cost_centre_enabled" and not enabled:
        updates["manufacturing_enabled"] = False

    filters = {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
    await get_collection(INVOICE_SETTINGS_COLLECTION).update_one(
        filters,
        {"$set": {**updates, "updated_by": updated_by, "updated_at": _now()},
         "$setOnInsert": {**filters, "created_at": _now()}},
        upsert=True,
    )
    await _audit_business_event(
        tenant_id=tenant_id, app_key=app_key, user_id=updated_by,
        action="business_module_enabled_toggled", entity_type="business_invoice_settings",
        entity_id=accounting_entity_id, new_value=updates,
    )
    return updates


# Sales Invoice documents moved to services/sales_invoices.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md). The facade re-export lives at the
# end of this module: sales_invoices imports GST-period helpers defined further below.


# ===================== Purchase Bills (Input GST / ITC) =====================


def _bill_response_doc(doc: dict, *, created: bool = False) -> dict:
    result = _json_safe_doc(doc)
    _apply_approval_defaults(result)
    result.setdefault("created", created)
    # Defaults so bills created before payment / ITC-reversal tracking render cleanly.
    result.setdefault("payment_status", "unpaid")
    result.setdefault("paid_amount", "0")
    result.setdefault("paid_date", None)
    result.setdefault("itc_reversed", False)
    result.setdefault("itc_interest_amount", "0")
    result.setdefault("itc_reclaimed", False)
    return result


# Purchase Bill documents moved to services/purchase_bills.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md). The facade re-export lives at the
# end of this module: purchase_bills imports GST-period helpers defined further below.


# ============== ITC Reversal (GST Rule 37 — 180-day non-payment) ==============


# Rule 37 ITC reversal/reclaim moved to services/itc_reversal.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md). The facade re-export lives at the
# end of this module: itc_reversal imports the GST-period helpers defined further below.


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


def _approval_queue_item(
    *,
    document_type: str,
    document_id: str,
    document_number: str,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    party_name: str | None,
    document_date,
    amount,
    status: str,
    approval_status: str | None,
    approval_required: bool | None,
    journal_entry_id,
    created_by,
    created_at,
    updated_at,
) -> dict:
    return {
        "document_type": document_type,
        "document_id": document_id,
        "document_number": document_number,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "party_name": party_name,
        "document_date": document_date,
        "amount": amount,
        "status": status,
        "approval_status": approval_status or "auto_posted",
        "approval_required": bool(approval_required),
        "journal_entry_id": journal_entry_id,
        "created_by": created_by,
        "created_at": created_at,
        "updated_at": updated_at,
    }


async def list_documents_for_approval_queue(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    document_type: str | None = None,
    status: str | None = None,
    approval_status: str | None = None,
    include_reviewed: bool = False,
    limit: int = 100,
) -> dict:
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
    }
    safe_limit = max(1, min(int(limit or 100), 500))

    collections = [
        (VOUCHERS_COLLECTION, "voucher"),
        (SALES_INVOICES_COLLECTION, "sales_invoice"),
        (PURCHASE_BILLS_COLLECTION, "purchase_bill"),
        (CREDIT_NOTES_COLLECTION, "credit_note"),
        (DEBIT_NOTES_COLLECTION, "debit_note"),
    ]
    if document_type:
        collections = [item for item in collections if item[1] == document_type]
    rows_by_type: dict[str, list[dict]] = {}
    for collection_name, doc_type in collections:
        rows = (
            await get_collection(collection_name)
            .find(filters)
            .sort("updated_at", -1)
            .limit(safe_limit)
            .to_list(length=safe_limit)
        )
        rows = [
            row for row in rows
            if str(row.get("status") or "").strip().lower() in {"posted", "pending_approval"}
        ]
        rows = [
            row for row in rows
            if bool(row.get("approval_required")) or str(row.get("approval_status") or "").strip().lower() in {"pending_approval", "approved", "rejected"}
        ]
        if status:
            rows = [row for row in rows if str(row.get("status") or "").strip().lower() == status]
        if approval_status:
            rows = [row for row in rows if str(row.get("approval_status") or "auto_posted").strip().lower() == approval_status]
        if not include_reviewed:
            rows = [row for row in rows if str(row.get("approval_status") or "auto_posted") != "approved"]
        rows_by_type[doc_type] = rows

    items: list[dict] = []
    for row in rows_by_type.get("voucher", []):
        items.append(
            _approval_queue_item(
                document_type="voucher",
                document_id=str(row.get("voucher_id") or ""),
                document_number=str(row.get("voucher_number") or ""),
                tenant_id=tenant_id,
                app_key=app_key,
                accounting_entity_id=accounting_entity_id,
                party_name=None,
                document_date=row.get("entry_date"),
                amount=row.get("amount"),
                status=str(row.get("status") or ""),
                approval_status=row.get("approval_status"),
                approval_required=row.get("approval_required"),
                journal_entry_id=row.get("journal_entry_id"),
                created_by=row.get("created_by"),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
            )
        )
    for row in rows_by_type.get("sales_invoice", []):
        items.append(
            _approval_queue_item(
                document_type="sales_invoice",
                document_id=str(row.get("invoice_id") or ""),
                document_number=str(row.get("invoice_number") or ""),
                tenant_id=tenant_id,
                app_key=app_key,
                accounting_entity_id=accounting_entity_id,
                party_name=row.get("customer_name"),
                document_date=row.get("invoice_date"),
                amount=row.get("invoice_total"),
                status=str(row.get("status") or ""),
                approval_status=row.get("approval_status"),
                approval_required=row.get("approval_required"),
                journal_entry_id=row.get("journal_entry_id"),
                created_by=row.get("created_by"),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
            )
        )
    for row in rows_by_type.get("purchase_bill", []):
        items.append(
            _approval_queue_item(
                document_type="purchase_bill",
                document_id=str(row.get("bill_id") or ""),
                document_number=str(row.get("bill_number") or ""),
                tenant_id=tenant_id,
                app_key=app_key,
                accounting_entity_id=accounting_entity_id,
                party_name=row.get("vendor_name"),
                document_date=row.get("bill_date"),
                amount=row.get("bill_total"),
                status=str(row.get("status") or ""),
                approval_status=row.get("approval_status"),
                approval_required=row.get("approval_required"),
                journal_entry_id=row.get("journal_entry_id"),
                created_by=row.get("created_by"),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
            )
        )
    for row in rows_by_type.get("credit_note", []):
        items.append(
            _approval_queue_item(
                document_type="credit_note",
                document_id=str(row.get("credit_note_id") or ""),
                document_number=str(row.get("credit_note_number") or ""),
                tenant_id=tenant_id,
                app_key=app_key,
                accounting_entity_id=accounting_entity_id,
                party_name=row.get("customer_name"),
                document_date=row.get("note_date"),
                amount=row.get("note_total"),
                status=str(row.get("status") or ""),
                approval_status=row.get("approval_status"),
                approval_required=row.get("approval_required"),
                journal_entry_id=row.get("journal_entry_id"),
                created_by=row.get("created_by"),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
            )
        )
    for row in rows_by_type.get("debit_note", []):
        items.append(
            _approval_queue_item(
                document_type="debit_note",
                document_id=str(row.get("debit_note_id") or ""),
                document_number=str(row.get("debit_note_number") or ""),
                tenant_id=tenant_id,
                app_key=app_key,
                accounting_entity_id=accounting_entity_id,
                party_name=row.get("vendor_name"),
                document_date=row.get("note_date"),
                amount=row.get("note_total"),
                status=str(row.get("status") or ""),
                approval_status=row.get("approval_status"),
                approval_required=row.get("approval_required"),
                journal_entry_id=row.get("journal_entry_id"),
                created_by=row.get("created_by"),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
            )
        )

    items.sort(key=lambda row: row.get("updated_at") or "", reverse=True)
    items = items[:safe_limit]
    return {"items": items, "total": len(items)}


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


# GST Settlement moved to services/gst_settlement.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); re-exported for compatibility.
from app.modules.business.services.gst_settlement import (  # noqa: E402
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


# Rule 37 ITC reversal/reclaim moved to services/itc_reversal.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); re-exported for compatibility.
# Placed last: itc_reversal imports GST-period helpers defined above in this module.
from app.modules.business.services.itc_reversal import (  # noqa: E402
    mark_bill_payment as mark_bill_payment,
    preview_itc_reversals as preview_itc_reversals,
    reclaim_itc_for_bill as reclaim_itc_for_bill,
    reverse_itc_for_bill as reverse_itc_for_bill,
)


# Purchase Bill documents moved to services/purchase_bills.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); re-exported for compatibility.
# Placed last: purchase_bills imports GST-period helpers defined above in this module.
from app.modules.business.services.purchase_bills import (  # noqa: E402
    cancel_purchase_bill as cancel_purchase_bill,
    create_purchase_bill as create_purchase_bill,
    get_purchase_bill as get_purchase_bill,
    list_purchase_bills as list_purchase_bills,
    review_purchase_bill as review_purchase_bill,
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
