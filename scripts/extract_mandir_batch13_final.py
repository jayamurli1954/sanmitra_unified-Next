"""Final mandir_compat router slim-down: panchang-only body + facade footer.

Run: python scripts/extract_mandir_batch13_final.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "app/modules/mandir_compat/router.py"

SLIM_HEADER = '''\
"""MandirMitra compat router.

Panchang display-settings and on-date routes live here. All other MandirMitra
handlers are registered via side-effect imports in the facade block at the end
of this module (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.permissions.rbac import Role, require_roles
from app.core.tenants.context import resolve_app_key, resolve_tenant_id
from app.db.mongo import get_collection
from app.services.panchang import PanchangService

router = APIRouter(tags=["mandir-compat"])
_MANDIR_WRITE_ROUTE_DEPS = [
    Depends(require_enabled_module("temple")),
    Depends(require_roles([Role.operator, Role.accountant, Role.tenant_admin, Role.super_admin])),
]
_MANDIR_ADMIN_ROUTE_DEPS = [
    Depends(require_enabled_module("temple")),
    Depends(require_roles([Role.tenant_admin, Role.super_admin])),
]
logger = logging.getLogger(__name__)

'''

FACADE_PREFIX = '''
# ════════════════════════════════════════════════════════════════════════
# FACADE: infrastructure + helper re-exports for routes/*.py and tests
# ════════════════════════════════════════════════════════════════════════

from app.accounting.service import (
    AccountingValidationError as AccountingValidationError,
    create_account as create_account,
    get_accounts_payable as get_accounts_payable,
    get_accounts_receivable as get_accounts_receivable,
    get_balance_sheet as get_balance_sheet,
    get_cost_centre_ledger_pl as get_cost_centre_ledger_pl,
    get_journal_drilldown as get_journal_drilldown,
    get_ledger_lines as get_ledger_lines,
    get_profit_loss as get_profit_loss,
    get_receipts_payments as get_receipts_payments,
    get_trial_balance as get_trial_balance,
    list_accounts as list_accounts,
    post_journal_entry as post_journal_entry,
    reverse_journal_entry as reverse_journal_entry,
    validate_cash_balance_for_journal_lines as validate_cash_balance_for_journal_lines,
)
from app.accounting.schemas import JournalLineIn as JournalLineIn, JournalPostRequest as JournalPostRequest
from app.core.audit.service import log_audit_event as log_audit_event
from app.core.rate_limiting import limiter as limiter
from app.core.tenants.app_resolvers import resolve_mandir_tenant as resolve_mandir_tenant
from app.core.tenants.context import resolve_app_key as resolve_app_key, resolve_tenant_id as resolve_tenant_id
from app.db.postgres import get_async_session as get_async_session
from app.modules.business.dimensions import create_dimension as create_dimension, deactivate_dimension as deactivate_dimension
from app.modules.mandir_compat.donation_compliance import (
    classify_donation_compliance as classify_donation_compliance,
    compliance_public_fields as compliance_public_fields,
    donation_compliance_config_view as donation_compliance_config_view,
    donation_compliance_receipt_note as donation_compliance_receipt_note,
    mask_pan as mask_pan,
    validate_donation_compliance_config as validate_donation_compliance_config,
)
from app.modules.mandir_compat.report_helpers import (
    accounts_payable_report as accounts_payable_report,
    accounts_receivable_report as accounts_receivable_report,
    balance_sheet_report as balance_sheet_report,
    bank_book_report as bank_book_report,
    cash_book_report as cash_book_report,
    category_income_report as category_income_report,
    day_book_report as day_book_report,
    detailed_donation_report as detailed_donation_report,
    detailed_seva_report as detailed_seva_report,
    donation_category_wise_report as donation_category_wise_report,
    donation_daily_report as donation_daily_report,
    donation_monthly_report as donation_monthly_report,
    journal_entries_report as journal_entries_report,
    ledger_report as ledger_report,
    posted_donations as posted_donations,
    posted_sevas as posted_sevas,
    profit_loss_report as profit_loss_report,
    receipts_payments_report as receipts_payments_report,
    seva_schedule_report as seva_schedule_report,
    top_donors_report as top_donors_report,
    trial_balance_report as trial_balance_report,
)
from app.modules.mandir_compat.service import (
    create_mandir_first_login_onboarding as create_mandir_first_login_onboarding,
    ensure_temple_numeric_id as ensure_temple_numeric_id,
    list_mandir_temples as list_mandir_temples,
    resolve_tenant_by_temple_id as resolve_tenant_by_temple_id,
)

from app.modules.mandir_compat.helpers.account_categories import (
    _MANDIR_CANONICAL_INCOME_CODES as _MANDIR_CANONICAL_INCOME_CODES,
    _MANDIR_INCOME_BUCKET_ALIASES as _MANDIR_INCOME_BUCKET_ALIASES,
    _MANDIR_INCOME_LEGACY_CODES as _MANDIR_INCOME_LEGACY_CODES,
    _MANDIR_LEGACY_ACCOUNT_CODE_MAP as _MANDIR_LEGACY_ACCOUNT_CODE_MAP,
    _MANDIR_SPONSORSHIP_CATEGORY_MARKERS as _MANDIR_SPONSORSHIP_CATEGORY_MARKERS,
    _MANDIR_UTR_REFERENCE_PATTERN as _MANDIR_UTR_REFERENCE_PATTERN,
    _is_mandir_sponsorship_category as _is_mandir_sponsorship_category,
    _mandir_cash_income_category as _mandir_cash_income_category,
    _mandir_in_kind_debit_account_target as _mandir_in_kind_debit_account_target,
    _mandir_in_kind_income_category as _mandir_in_kind_income_category,
    _mandir_income_bucket_for_account as _mandir_income_bucket_for_account,
    _normalize_income_category as _normalize_income_category,
    _normalize_mandir_account_code as _normalize_mandir_account_code,
    _normalize_public_payment_utr_reference as _normalize_public_payment_utr_reference,
)
from app.modules.mandir_compat.helpers.mandir_actor import _mandir_actor_id as _mandir_actor_id
from app.modules.mandir_compat.helpers.public_defaults import (
    _DEFAULT_PUBLIC_DONATION_CATEGORIES as _DEFAULT_PUBLIC_DONATION_CATEGORIES,
)
from app.modules.mandir_compat.helpers.receipt_sequencing import (
    _MANDIR_COUNTERS_COLLECTION as _MANDIR_COUNTERS_COLLECTION,
    _MANDIR_JOURNAL_ENTRY_PREFIX as _MANDIR_JOURNAL_ENTRY_PREFIX,
    _MANDIR_RECEIPT_PREFIX_BY_KIND as _MANDIR_RECEIPT_PREFIX_BY_KIND,
    _MANDIR_RECEIPT_WIDTH as _MANDIR_RECEIPT_WIDTH,
)

'''


def find_index(lines: list[str], predicate) -> int:
    for i, line in enumerate(lines):
        if predicate(line):
            return i
    raise RuntimeError("Anchor not found")


def main() -> None:
    lines = ROUTER.read_text(encoding="utf-8").splitlines(keepends=True)
    original = len(lines)

    const_start = find_index(lines, lambda l: l.startswith("_PANCHANG_DEFAULT_LOCATION = {"))
    city_options_start = find_index(lines, lambda l: l.startswith("_PANCHANG_CITY_OPTIONS"))
    city_options_end = find_index(lines[city_options_start:], lambda l: l.strip() == ")") + city_options_start + 1

    helpers_start = find_index(lines, lambda l: l.startswith("def _panchang_city_options("))
    helpers_end = find_index(lines, lambda l: l.strip().startswith("# Panchang (today) route moved"))
    routes_start = find_index(lines, lambda l: l.startswith('@router.get("/panchang/display-settings")'))
    routes_end = find_index(lines, lambda l: l.strip() == "# Pincode route moved to routes/pincode.py")
    footer_start = find_index(
        lines,
        lambda l: l.strip().startswith("from app.modules.mandir_compat.routes.refunds import"),
    )
    # Include the two-line comment immediately above the refunds import block.
    while footer_start > 0 and lines[footer_start - 1].strip().startswith("#"):
        footer_start -= 1

    panchang_constants = "".join(lines[const_start:city_options_end])
    panchang_helpers = "".join(lines[helpers_start:helpers_end])
    panchang_routes = "".join(lines[routes_start:routes_end])
    footer = "".join(lines[footer_start:])

    body = (
        SLIM_HEADER
        + "\n# Panchang constants, helpers, and display/on-date routes (quarantined in router.py).\n\n"
        + panchang_constants
        + "\n"
        + panchang_helpers
        + panchang_routes
        + FACADE_PREFIX
        + footer
    )
    ROUTER.write_text(body, encoding="utf-8")
    updated = len(ROUTER.read_text(encoding="utf-8").splitlines())
    print(f"router.py: {original} -> {updated} lines")


if __name__ == "__main__":
    main()
