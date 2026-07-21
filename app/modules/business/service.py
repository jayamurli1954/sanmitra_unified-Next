"""MitraBooks business service facade.

Domain implementations live under app/modules/business/services/*.py.
This module keeps collection constants, quarantined compensation/voucher-number
helpers (LARGE_FILE_MODULARIZATION_PLAN.md §6), and re-exports for compatibility.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import (
    AccountingNotFoundError as AccountingNotFoundError,
    AccountingValidationError as AccountingValidationError,
    initialize_default_chart_of_accounts as initialize_default_chart_of_accounts,
    post_journal_entry as post_journal_entry,
    reverse_journal_entry as reverse_journal_entry,
)
from app.modules.business.dimensions import validate_dimension_refs as validate_dimension_refs
from app.core.audit.service import log_audit_event as log_audit_event
from app.db.mongo import get_collection
from app.modules.business.schemas import (
    ApprovalReviewRequest as ApprovalReviewRequest,
    GstPeriodLockUpdateRequest,
    TypedVoucherCreateRequest as TypedVoucherCreateRequest,
    TypedVoucherReversalRequest as TypedVoucherReversalRequest,
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


# Shared helpers moved to services/common.py
from app.modules.business.services.common import (  # noqa: E402
    _apply_approval_defaults as _apply_approval_defaults,
    _audit_business_event as _audit_business_event,
    _ensure_business_chart_for_voucher_codes as _ensure_business_chart_for_voucher_codes,
    _json_safe_doc as _json_safe_doc,
    _money as _money,
    _now as _now,
    _resolve_voucher_account_id as _resolve_voucher_account_id,
    _voucher_response_doc as _voucher_response_doc,
)


# ════════════════════════════════════════════════════════════════════════
# QUARANTINED (LARGE_FILE_MODULARIZATION_PLAN.md §6): compensation + voucher
# number reservation stay in the facade module. Pure-move extraction only.
# ════════════════════════════════════════════════════════════════════════

def _voucher_prefix(voucher_type: str) -> str:
    return {
        "payment": "PV",
        "receipt": "RV",
        "contra": "CV",
        "journal": "JV",
    }.get(str(voucher_type or "").strip().lower(), "BV")


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


# Mongo index bootstrap moved to services/indexes.py
from app.modules.business.services.indexes import (  # noqa: E402
    ensure_business_indexes as ensure_business_indexes,
)

# Typed vouchers moved to services/vouchers.py
from app.modules.business.services.vouchers import (  # noqa: E402
    _approve_typed_voucher_document as _approve_typed_voucher_document,
    get_voucher as get_voucher,
    list_vouchers as list_vouchers,
    post_typed_voucher as post_typed_voucher,
    reverse_typed_voucher as reverse_typed_voucher,
    review_typed_voucher as review_typed_voucher,
)

# Party master CRUD moved to services/parties.py
from app.modules.business.services.parties import (  # noqa: E402
    create_party as create_party,
    deactivate_party as deactivate_party,
    get_party as get_party,
    list_parties as list_parties,
    update_party as update_party,
)

# Invoice line computation / numbering moved to services/invoice_computation.py
from app.modules.business.services.invoice_computation import (  # noqa: E402
    _compute_invoice_lines as _compute_invoice_lines,
    _invoice_response_doc as _invoice_response_doc,
    _q2 as _q2,
    _reserve_invoice_number as _reserve_invoice_number,
    _validate_required_invoice_fields as _validate_required_invoice_fields,
)

# Invoice / admin settings moved to services/invoice_settings.py
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
from app.modules.business.services.gst_period_locks import (  # noqa: E402
    _period_key as _period_key,
    _period_label as _period_label,
    _validate_reversal_period as _validate_reversal_period,
    is_gst_period_locked as is_gst_period_locked,
    list_gst_period_locks as list_gst_period_locks,
    set_gst_period_lock as set_gst_period_lock,
)

# Credit/debit note sequence numbers moved to services/document_numbering.py
from app.modules.business.services.document_numbering import (  # noqa: E402
    _reserve_sequence_number as _reserve_sequence_number,
)

# Credit Notes moved to services/credit_notes.py
from app.modules.business.services.credit_notes import (  # noqa: E402
    cancel_credit_note as cancel_credit_note,
    create_credit_note as create_credit_note,
    get_credit_note as get_credit_note,
    list_credit_notes as list_credit_notes,
    review_credit_note as review_credit_note,
)

# Debit Notes moved to services/debit_notes.py
from app.modules.business.services.debit_notes import (  # noqa: E402
    cancel_debit_note as cancel_debit_note,
    create_debit_note as create_debit_note,
    get_debit_note as get_debit_note,
    list_debit_notes as list_debit_notes,
    review_debit_note as review_debit_note,
)

# GST Settlement moved to services/gst_settlement.py
from app.modules.business.services.gst_settlement import (  # noqa: E402
    _compute_gst_setoff as _compute_gst_setoff,
    _gst_period_balances as _gst_period_balances,
    _period_bounds as _period_bounds,
    create_gst_settlement as create_gst_settlement,
    preview_gst_settlement as preview_gst_settlement,
    reverse_gst_settlement as reverse_gst_settlement,
)

# Party sub-ledger reads moved to services/party_ledger.py
from app.modules.business.services.party_ledger import (  # noqa: E402
    party_outstanding_summary as party_outstanding_summary,
    party_wise_ledger as party_wise_ledger,
)

# Purchase Bill documents moved to services/purchase_bills.py
from app.modules.business.services.purchase_bills import (  # noqa: E402
    cancel_purchase_bill as cancel_purchase_bill,
    create_purchase_bill as create_purchase_bill,
    get_purchase_bill as get_purchase_bill,
    list_purchase_bills as list_purchase_bills,
    review_purchase_bill as review_purchase_bill,
)

# Rule 37 ITC reversal/reclaim moved to services/itc_reversal.py
from app.modules.business.services.itc_reversal import (  # noqa: E402
    _compute_itc_interest as _compute_itc_interest,
    mark_bill_payment as mark_bill_payment,
    preview_itc_reversals as preview_itc_reversals,
    reclaim_itc_for_bill as reclaim_itc_for_bill,
    reverse_itc_for_bill as reverse_itc_for_bill,
)

# Sales Invoice documents moved to services/sales_invoices.py
from app.modules.business.services.sales_invoices import (  # noqa: E402
    cancel_sales_invoice as cancel_sales_invoice,
    create_sales_invoice as create_sales_invoice,
    get_sales_invoice as get_sales_invoice,
    list_sales_invoices as list_sales_invoices,
    review_sales_invoice as review_sales_invoice,
)

# CA client / document-metadata CRUD moved to services/ca_clients.py
from app.modules.business.services.ca_clients import (  # noqa: E402
    create_ca_client as create_ca_client,
    create_ca_document_metadata as create_ca_document_metadata,
    list_ca_clients as list_ca_clients,
    list_ca_document_metadata as list_ca_document_metadata,
    update_ca_client as update_ca_client,
    update_ca_document_metadata as update_ca_document_metadata,
)

# Document attachment upload/list/download moved to services/document_attachments.py
from app.modules.business.services.document_attachments import (  # noqa: E402
    create_business_document_attachment as create_business_document_attachment,
    download_business_document_attachment as download_business_document_attachment,
    list_business_document_attachments as list_business_document_attachments,
)

# Approval queue listing moved to services/approval_queue.py
from app.modules.business.services.approval_queue import (  # noqa: E402
    list_documents_for_approval_queue as list_documents_for_approval_queue,
)
