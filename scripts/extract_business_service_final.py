"""Mechanical extraction to finish business/service.py modularization.

Moves remaining non-quarantined code into:
- services/common.py      (shared helpers + account resolve)
- services/vouchers.py    (typed voucher CRUD / review / post / reverse)
- services/indexes.py     (ensure_business_indexes)

Leaves in service.py (plan §6 quarantine):
- _reverse_after_domain_persistence_failure
- _compensate_gst_settlement_failure
- _reserve_voucher_number (+ _voucher_prefix)

Run: python scripts/extract_business_service_final.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "app/modules/business/service.py"
COMMON = ROOT / "app/modules/business/services/common.py"
VOUCHERS = ROOT / "app/modules/business/services/vouchers.py"
INDEXES = ROOT / "app/modules/business/services/indexes.py"


def read_lines() -> list[str]:
    return SERVICE.read_text(encoding="utf-8").splitlines(keepends=True)


def find_index(lines: list[str], predicate) -> int:
    for i, line in enumerate(lines):
        if predicate(line):
            return i
    raise RuntimeError("Anchor not found")


def slice_text(lines: list[str], start: int, end: int) -> str:
    return "".join(lines[start:end])


COMMON_HEADER = '''"""Shared business service helpers.

Extracted verbatim from app/modules/business/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
Re-exported via the service.py facade for compatibility.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models.entities import Account
from app.accounting.service import AccountingNotFoundError
from app.core.audit.service import log_audit_event

'''

VOUCHERS_HEADER = '''"""Typed business voucher create / list / review / approve / reverse / post.

Extracted verbatim from app/modules/business/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.

Quarantined helpers (_reserve_voucher_number, _reverse_after_domain_persistence_failure)
are resolved at runtime via the service facade so monkeypatches keep working.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import (
    AccountingNotFoundError,
    AccountingValidationError,
    initialize_default_chart_of_accounts,
    post_journal_entry,
    reverse_journal_entry,
)
from app.db.mongo import get_collection
from app.modules.business.dimensions import validate_dimension_refs
from app.modules.business.schemas import (
    ApprovalReviewRequest,
    TypedVoucherCreateRequest,
    TypedVoucherReversalRequest,
)
from app.modules.business import service as business_service
from app.modules.business.services.common import (
    _apply_approval_defaults,
    _audit_business_event,
    _json_safe_doc,
    _money,
    _now,
    _resolve_voucher_account_id,
)

'''

INDEXES_HEADER = '''"""Mongo index bootstrap for MitraBooks business collections.

Extracted verbatim from app/modules/business/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from app.db.mongo import get_collection
from app.modules.business import service as business_service

'''


def main() -> None:
    lines = read_lines()
    original = len(lines)

    # Helpers: _now through _audit_business_event (before quarantine reverse_after)
    now_i = find_index(lines, lambda l: l.startswith("def _now("))
    reverse_i = find_index(lines, lambda l: l.startswith("async def _reverse_after_domain_persistence_failure("))
    helpers_block = slice_text(lines, now_i, reverse_i)

    # _resolve_voucher_account_id through end of _ensure_business_chart (before ensure_business_indexes)
    resolve_i = find_index(lines, lambda l: l.startswith("async def _resolve_voucher_account_id("))
    indexes_i = find_index(lines, lambda l: l.startswith("async def ensure_business_indexes("))
    resolve_block = slice_text(lines, resolve_i, indexes_i)

    # ensure_business_indexes body until CA comment / parties import
    parties_comment_i = find_index(
        lines,
        lambda l: l.strip().startswith("# CA client / document-metadata CRUD moved"),
    )
    indexes_block = slice_text(lines, indexes_i, parties_comment_i)

    # Voucher ops: list_vouchers through post_typed_voucher (after _reserve_voucher_number)
    list_i = find_index(lines, lambda l: l.startswith("async def list_vouchers("))
    sales_banner_i = find_index(lines, lambda l: l.strip() == "# ===================== Sales Invoices (GST) =====================")
    vouchers_block = slice_text(lines, list_i, sales_banner_i)

    # Rewrite helpers to stay as-is (they don't need business_service)
    COMMON.write_text(COMMON_HEADER + helpers_block + resolve_block, encoding="utf-8")

    # Indexes: replace get_collection(X) and collection constants with business_service.*
    indexes_body = indexes_block
    for name in (
        "PARTIES_COLLECTION",
        "VOUCHERS_COLLECTION",
        "CA_DOCUMENTS_COLLECTION",
        "CA_CLIENTS_COLLECTION",
        "BUSINESS_DOCUMENT_ATTACHMENTS_COLLECTION",
        "SALES_INVOICES_COLLECTION",
        "INVOICE_SETTINGS_COLLECTION",
        "ADMIN_SETTINGS_COLLECTION",
        "PURCHASE_BILLS_COLLECTION",
        "GST_PERIOD_LOCKS_COLLECTION",
        "CREDIT_NOTES_COLLECTION",
        "DEBIT_NOTES_COLLECTION",
        "GST_SETTLEMENTS_COLLECTION",
    ):
        indexes_body = indexes_body.replace(f"get_collection({name})", f"get_collection(business_service.{name})")
    # Also replace bare get_collection("literal") - already fine
    INDEXES.write_text(INDEXES_HEADER + indexes_body, encoding="utf-8")

    # Vouchers: route quarantine + collection lookups through business_service
    vouchers_body = vouchers_block
    vouchers_body = vouchers_body.replace("get_collection(VOUCHERS_COLLECTION)", "get_collection(business_service.VOUCHERS_COLLECTION)")
    vouchers_body = vouchers_body.replace("await _reserve_voucher_number(", "await business_service._reserve_voucher_number(")
    vouchers_body = vouchers_body.replace(
        "await _reverse_after_domain_persistence_failure(",
        "await business_service._reverse_after_domain_persistence_failure(",
    )
    # Remove attachment comment that sat between approve and reverse
    vouchers_body = vouchers_body.replace(
        "# Document attachment upload/list/download moved to services/document_attachments.py\n"
        "# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md). The facade re-export lives at the\n"
        "# bottom of this module.\n\n",
        "",
    )
    VOUCHERS.write_text(VOUCHERS_HEADER + vouchers_body, encoding="utf-8")

    # Rebuild service.py: keep header through CA_DOCUMENT_DEFAULT_NEXT_ACTION,
    # then quarantine (_voucher_prefix, reverse, compensate, reserve),
    # then facade re-exports.
    const_end = find_index(lines, lambda l: l.startswith("def _now("))
    header = slice_text(lines, 0, const_end)

    # Extract quarantine pieces from original
    voucher_prefix_i = find_index(lines, lambda l: l.startswith("def _voucher_prefix("))
    voucher_prefix_end = find_index(lines, lambda l: l.startswith("async def _audit_business_event("))
    prefix_fn = slice_text(lines, voucher_prefix_i, voucher_prefix_end)

    compensate_end = find_index(lines, lambda l: l.startswith("async def _resolve_voucher_account_id("))
    quarantine_comp = slice_text(lines, reverse_i, compensate_end)

    reserve_i = find_index(lines, lambda l: l.startswith("async def _reserve_voucher_number("))
    reserve_fn = slice_text(lines, reserve_i, list_i)

    # Existing facade from sales banner onward, but drop obsolete section banners/comments
    # that duplicate moved sections — keep the import block as-is from invoice_computation onward.
    facade_start = find_index(lines, lambda l: "from app.modules.business.services.invoice_computation import" in l)
    # Include a bit of comment before invoice_computation
    facade_comment_start = facade_start
    while facade_comment_start > 0 and (
        lines[facade_comment_start - 1].strip().startswith("#")
        or lines[facade_comment_start - 1].strip() == ""
        or "=====" in lines[facade_comment_start - 1]
    ):
        facade_comment_start -= 1
    # Also keep parties import that was mid-file
    parties_import_i = find_index(lines, lambda l: "from app.modules.business.services.parties import" in l)
    parties_block_start = parties_import_i
    while parties_block_start > 0 and (
        lines[parties_block_start - 1].strip().startswith("#")
        or lines[parties_block_start - 1].strip() == ""
    ):
        parties_block_start -= 1
    parties_block_end = find_index(lines[parties_import_i:], lambda l: l.strip() == ")") + parties_import_i + 1
    parties_block = slice_text(lines, parties_block_start, parties_block_end)

    rest_facade = slice_text(lines, facade_comment_start, len(lines))

    mid = '''
# Shared helpers moved to services/common.py
from app.modules.business.services.common import (  # noqa: E402
    _apply_approval_defaults as _apply_approval_defaults,
    _audit_business_event as _audit_business_event,
    _json_safe_doc as _json_safe_doc,
    _money as _money,
    _now as _now,
    _resolve_voucher_account_id as _resolve_voucher_account_id,
)

'''

    quarantine_note = '''
# ════════════════════════════════════════════════════════════════════════
# QUARANTINED (LARGE_FILE_MODULARIZATION_PLAN.md §6): compensation + voucher
# number reservation stay in the facade module. Pure-move extraction only.
# ════════════════════════════════════════════════════════════════════════

'''

    indexes_export = '''
# Mongo index bootstrap moved to services/indexes.py
from app.modules.business.services.indexes import (  # noqa: E402
    ensure_business_indexes as ensure_business_indexes,
)

# Typed vouchers moved to services/vouchers.py
from app.modules.business.services.vouchers import (  # noqa: E402
    _approve_typed_voucher_document as _approve_typed_voucher_document,
    _ensure_business_chart_for_voucher_codes as _ensure_business_chart_for_voucher_codes,
    _voucher_response_doc as _voucher_response_doc,
    get_voucher as get_voucher,
    list_vouchers as list_vouchers,
    post_typed_voucher as post_typed_voucher,
    reverse_typed_voucher as reverse_typed_voucher,
    review_typed_voucher as review_typed_voucher,
)

'''

    # Fix reserve_fn to still call _voucher_prefix and _now (both on this module / re-exported)
    new_service = (
        header
        + mid
        + quarantine_note
        + prefix_fn
        + quarantine_comp
        + reserve_fn
        + indexes_export
        + parties_block
        + "\n"
        + rest_facade
    )

    # Drop unused imports that only served extracted helpers if any remain unused —
    # keep accounting imports used by quarantine.
    SERVICE.write_text(new_service, encoding="utf-8")
    updated = len(SERVICE.read_text(encoding="utf-8").splitlines())
    print(f"service.py: {original} -> {updated} lines")
    print(f"common.py: {len(COMMON.read_text(encoding='utf-8').splitlines())} lines")
    print(f"vouchers.py: {len(VOUCHERS.read_text(encoding='utf-8').splitlines())} lines")
    print(f"indexes.py: {len(INDEXES.read_text(encoding='utf-8').splitlines())} lines")


if __name__ == "__main__":
    main()
