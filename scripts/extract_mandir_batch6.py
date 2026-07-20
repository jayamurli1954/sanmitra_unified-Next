"""Mechanical extraction for mandir_compat batch 6 (no panchang, no seva bookings).

Extracts journal routes/helpers, login/opening balances, role permissions,
temple management, UPI, public routes, and users.
Run: python scripts/extract_mandir_batch6.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "app/modules/mandir_compat/router.py"


def read_lines() -> list[str]:
    return ROUTER.read_text(encoding="utf-8").splitlines(keepends=True)


def slice_lines(lines: list[str], start: int, end: int) -> str:
    return "".join(lines[start - 1 : end])


def apply_replacements(body: str, replacements: list[tuple[str, str]]) -> str:
    for old, new in replacements:
        body = body.replace(old, new)
    return body


COMMON_REPLACEMENTS = [
    ("get_collection(", "mandir_router.get_collection("),
    ("_sanitize_mongo_doc(", "mandir_router._sanitize_mongo_doc("),
    ("resolve_app_key(", "mandir_router.resolve_app_key("),
    ("resolve_tenant_id(", "mandir_router.resolve_tenant_id("),
    ("await _ensure_default_mandir_sql_accounts_safe(", "await mandir_router._ensure_default_mandir_sql_accounts_safe("),
    ("await list_accounts(", "await mandir_router.list_accounts("),
    ("_mandir_actor_id(", "mandir_router._mandir_actor_id("),
    ("_safe_optional_str(", "mandir_router._safe_optional_str("),
    ("_safe_optional_int(", "mandir_router._safe_optional_int("),
    ("_safe_float(", "mandir_router._safe_float("),
    ("_normalize_mandir_account_code(", "mandir_router._normalize_mandir_account_code("),
    ("_normalize_phone(", "mandir_router._normalize_phone("),
    ("_parse_iso_datetime(", "mandir_router._parse_iso_datetime("),
    ("await post_journal_entry(", "await mandir_router.post_journal_entry("),
    ("await reverse_journal_entry(", "await mandir_router.reverse_journal_entry("),
    ("await _resolve_tenant_for_mandir_request(", "await mandir_router._resolve_tenant_for_mandir_request("),
    ("await _assert_platform_can_write_tenant(", "await mandir_router._assert_platform_can_write_tenant("),
    ("await ensure_temple_numeric_id(", "await mandir_router.ensure_temple_numeric_id("),
    ("await log_audit_event(", "await mandir_router.log_audit_event("),
    ("logger.", "mandir_router.logger."),
]

JOURNAL_REPLACEMENTS = COMMON_REPLACEMENTS + [
    ("await journal_entries_report(", "await mandir_router.journal_entries_report("),
    ("await validate_cash_balance_for_journal_lines(", "await mandir_router.validate_cash_balance_for_journal_lines("),
    ("await _next_journal_entry_number(", "await mandir_router._next_journal_entry_number("),
    ("await _normalize_mandir_journal_lines(", "await _normalize_mandir_journal_lines("),
    ("await _validate_mandir_journal_cash_balance(", "await _validate_mandir_journal_cash_balance("),
    ("await _resolve_sql_account_for_journal_line(", "await _resolve_sql_account_for_journal_line("),
    ("_mandir_journal_entry_view(", "_mandir_journal_entry_view("),
    ("_parse_journal_entry_date(", "_parse_journal_entry_date("),
]

LOGIN_REPLACEMENTS = COMMON_REPLACEMENTS + [
    ("await _parse_opening_balance_rows(", "await mandir_router._parse_opening_balance_rows("),
    ("await _find_or_create_opening_balance_offset_account(", "await mandir_router._find_or_create_opening_balance_offset_account("),
    ("await _current_opening_balance_net(", "await mandir_router._current_opening_balance_net("),
    ("_parse_opening_balance_decimal(", "mandir_router._parse_opening_balance_decimal("),
]

TEMPLES_REPLACEMENTS = COMMON_REPLACEMENTS + [
    ("await list_mandir_temples(", "await mandir_router.list_mandir_temples("),
    ("await resolve_tenant_by_temple_id(", "await mandir_router.resolve_tenant_by_temple_id("),
    ("await create_mandir_first_login_onboarding(", "await mandir_router.create_mandir_first_login_onboarding("),
    ("_is_platform_super_admin(", "mandir_router._is_platform_super_admin("),
    ("_ok(", "mandir_router._ok("),
    ("await posted_donations(", "await mandir_router.posted_donations("),
]

UPI_REPLACEMENTS = COMMON_REPLACEMENTS + [
    ("await resolve_tenant_by_temple_id(", "await mandir_router.resolve_tenant_by_temple_id("),
    ("_build_upi_intent_uri(", "mandir_router._build_upi_intent_uri("),
    ("_mandir_upi_payment_view(", "mandir_router._mandir_upi_payment_view("),
    ("_upi_receipt_number(", "mandir_router._upi_receipt_number("),
    ("await create_donation(", "await mandir_router.create_donation("),
    ("await create_seva_booking(", "await mandir_router.create_seva_booking("),
]

PUBLIC_REPLACEMENTS = COMMON_REPLACEMENTS + [
    ("await resolve_tenant_by_temple_id(", "await mandir_router.resolve_tenant_by_temple_id("),
    ("_normalize_public_donation_categories(", "_normalize_public_donation_categories("),
    ("_DEFAULT_PUBLIC_DONATION_CATEGORIES", "mandir_router._DEFAULT_PUBLIC_DONATION_CATEGORIES"),
    ("await create_donation(", "await mandir_router.create_donation("),
    ("await create_seva_booking(", "await mandir_router.create_seva_booking("),
    ("_normalize_public_payment_utr_reference(", "mandir_router._normalize_public_payment_utr_reference("),
    ("_serialize_seva_doc(", "mandir_router._serialize_seva_doc("),
]


def write_modules(lines: list[str]) -> None:
    journal_body = apply_replacements(slice_lines(lines, 2657, 3442), JOURNAL_REPLACEMENTS)
    login_body = apply_replacements(slice_lines(lines, 3447, 3686), LOGIN_REPLACEMENTS)
    role_body = apply_replacements(slice_lines(lines, 3930, 4012), COMMON_REPLACEMENTS)
    temples_body = apply_replacements(slice_lines(lines, 4019, 4500), TEMPLES_REPLACEMENTS)
    upi_body = apply_replacements(
        slice_lines(lines, 4503, 4516) + slice_lines(lines, 4525, 4648) + slice_lines(lines, 5591, 5740),
        UPI_REPLACEMENTS,
    )
    public_body = apply_replacements(slice_lines(lines, 4656, 5583), PUBLIC_REPLACEMENTS)
    users_body = apply_replacements(slice_lines(lines, 5749, 5804), COMMON_REPLACEMENTS)

    routes_dir = ROOT / "app/modules/mandir_compat/routes"

    (routes_dir / "journal_entries.py").write_text(
        f'''"""MandirMitra journal entry routes and financial report endpoints.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models.entities import Account
from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.report_helpers import (
    accounts_payable_report,
    accounts_receivable_report,
    balance_sheet_report,
    bank_book_report,
    cash_book_report,
    category_income_report,
    day_book_report,
    ledger_report,
    profit_loss_report,
    receipts_payments_report,
    top_donors_report,
    trial_balance_report,
)
from app.modules.mandir_compat.router import _MANDIR_WRITE_ROUTE_DEPS, router

{journal_body}
''',
        encoding="utf-8",
    )

    (routes_dir / "login_opening.py").write_text(
        f'''"""MandirMitra legacy login and opening balance import routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from fastapi import Depends, File, Header, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models.entities import Account
from app.core.auth.dependencies import get_current_user
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import router

{login_body}
''',
        encoding="utf-8",
    )

    (routes_dir / "role_permissions.py").write_text(
        f'''"""MandirMitra role permission routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, Header

from app.core.auth.dependencies import get_current_user
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import _MANDIR_ADMIN_ROUTE_DEPS, router

{role_body}
''',
        encoding="utf-8",
    )

    (routes_dir / "temples_mgmt.py").write_text(
        f'''"""MandirMitra setup wizard, temple admin, and compliance config routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from fastapi import Depends, Header, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.donation_compliance import (
    compliance_public_fields,
    donation_compliance_config_view,
    validate_donation_compliance_config,
)
from app.modules.mandir_compat.router import _MANDIR_ADMIN_ROUTE_DEPS, router
from app.modules.mandir_compat.schemas import MandirFirstLoginOnboardingRequest

{temples_body}
''',
        encoding="utf-8",
    )

    (routes_dir / "upi.py").write_text(
        f'''"""MandirMitra UPI config, intent, and quick-log routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import (
    _MANDIR_ADMIN_ROUTE_DEPS,
    _MANDIR_WRITE_ROUTE_DEPS,
    router,
)

{upi_body}
''',
        encoding="utf-8",
    )

    (routes_dir / "public.py").write_text(
        f'''"""MandirMitra public portal and public payment management routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.rate_limiting import limiter
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import _MANDIR_WRITE_ROUTE_DEPS, router

{public_body}
''',
        encoding="utf-8",
    )

    (routes_dir / "users.py").write_text(
        f'''"""MandirMitra user list and profile routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, Header, HTTPException

from app.core.auth.dependencies import get_current_user
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import router

{users_body}
''',
        encoding="utf-8",
    )


FOOTER = '''
import app.modules.mandir_compat.routes.journal_entries  # noqa: E402, F401
import app.modules.mandir_compat.routes.login_opening  # noqa: E402, F401
import app.modules.mandir_compat.routes.role_permissions  # noqa: E402, F401
import app.modules.mandir_compat.routes.temples_mgmt  # noqa: E402, F401
import app.modules.mandir_compat.routes.upi  # noqa: E402, F401
import app.modules.mandir_compat.routes.public  # noqa: E402, F401
import app.modules.mandir_compat.routes.users  # noqa: E402, F401
from app.modules.mandir_compat.routes.journal_entries import (
    _mandir_journal_entry_view as _mandir_journal_entry_view,
    _normalize_mandir_journal_lines as _normalize_mandir_journal_lines,
    _parse_journal_entry_date as _parse_journal_entry_date,
    _resolve_sql_account_for_journal_line as _resolve_sql_account_for_journal_line,
    _validate_mandir_journal_cash_balance as _validate_mandir_journal_cash_balance,
    mandir_cancel_journal_entry as mandir_cancel_journal_entry,
    mandir_create_journal_entry as mandir_create_journal_entry,
    mandir_journal_accounts_payable as mandir_journal_accounts_payable,
    mandir_journal_accounts_receivable as mandir_journal_accounts_receivable,
    mandir_journal_balance_sheet as mandir_journal_balance_sheet,
    mandir_journal_bank_book as mandir_journal_bank_book,
    mandir_journal_cash_book as mandir_journal_cash_book,
    mandir_journal_category_income as mandir_journal_category_income,
    mandir_journal_day_book as mandir_journal_day_book,
    mandir_journal_drilldown as mandir_journal_drilldown,
    mandir_journal_entries as mandir_journal_entries,
    mandir_journal_income_expenditure as mandir_journal_income_expenditure,
    mandir_journal_ledger as mandir_journal_ledger,
    mandir_journal_profit_loss as mandir_journal_profit_loss,
    mandir_journal_receipts_payments as mandir_journal_receipts_payments,
    mandir_journal_top_donors as mandir_journal_top_donors,
    mandir_journal_trial_balance as mandir_journal_trial_balance,
    mandir_post_journal_entry as mandir_post_journal_entry,
    mandir_update_journal_entry as mandir_update_journal_entry,
)
from app.modules.mandir_compat.routes.login_opening import (
    mandir_legacy_login as mandir_legacy_login,
    mandir_opening_balances_import as mandir_opening_balances_import,
    mandir_opening_balances_template as mandir_opening_balances_template,
)
from app.modules.mandir_compat.routes.role_permissions import (
    mandir_role_permissions as mandir_role_permissions,
    mandir_role_permissions_assignable as mandir_role_permissions_assignable,
    mandir_role_permissions_update as mandir_role_permissions_update,
)
from app.modules.mandir_compat.routes.temples_mgmt import (
    _mandir_compliance_report as _mandir_compliance_report,
    _mandir_temple_collection_counts as _mandir_temple_collection_counts,
    _mandir_tenant_app_query as _mandir_tenant_app_query,
    _resolve_temple_target_tenant as _resolve_temple_target_tenant,
    get_mandir_donation_compliance_config as get_mandir_donation_compliance_config,
    update_mandir_donation_compliance_config as update_mandir_donation_compliance_config,
    mandir_activate_temple as mandir_activate_temple,
    mandir_deactivate_temple as mandir_deactivate_temple,
    mandir_remove_temple as mandir_remove_temple,
    mandir_remove_temple_preview as mandir_remove_temple_preview,
    mandir_report_80g_readiness as mandir_report_80g_readiness,
    mandir_report_fcra_readiness as mandir_report_fcra_readiness,
    mandir_setup_wizard_status as mandir_setup_wizard_status,
    mandir_temples as mandir_temples,
    mandir_temples_module_config as mandir_temples_module_config,
    mandir_temples_module_config_update as mandir_temples_module_config_update,
    mandir_temples_onboard as mandir_temples_onboard,
    mandir_temples_upload as mandir_temples_upload,
)
from app.modules.mandir_compat.routes.upi import (
    _mandir_upi_config_view as _mandir_upi_config_view,
    mandir_public_upi_intent as mandir_public_upi_intent,
    mandir_upi_payments as mandir_upi_payments,
    mandir_upi_payments_config as mandir_upi_payments_config,
    mandir_upi_payments_config_update as mandir_upi_payments_config_update,
    mandir_upi_quick_log as mandir_upi_quick_log,
)
from app.modules.mandir_compat.routes.public import (
    _normalize_public_donation_categories as _normalize_public_donation_categories,
    mandir_correct_public_payment as mandir_correct_public_payment,
    mandir_get_version as mandir_get_version,
    mandir_list_public_payments as mandir_list_public_payments,
    mandir_public_create_seva_payment as mandir_public_create_seva_payment,
    mandir_public_devotee_autofill as mandir_public_devotee_autofill,
    mandir_public_donation_categories as mandir_public_donation_categories,
    mandir_public_list_temples as mandir_public_list_temples,
    mandir_public_payment_exceptions as mandir_public_payment_exceptions,
    mandir_public_payment_status as mandir_public_payment_status,
    mandir_public_pincode_lookup as mandir_public_pincode_lookup,
    mandir_public_temple_info as mandir_public_temple_info,
    mandir_public_temple_sevas as mandir_public_temple_sevas,
    mandir_reject_public_payment as mandir_reject_public_payment,
    mandir_verify_public_payment as mandir_verify_public_payment,
)
from app.modules.mandir_compat.routes.users import (
    mandir_update_user_profile as mandir_update_user_profile,
    mandir_users as mandir_users,
)

'''


def rewrite_router(lines: list[str]) -> str:
    chunks = [
        slice_lines(lines, 1, 2656),
        (
            "# Journal routes moved to routes/journal_entries.py\n"
            "# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.\n\n"
            "# Login and opening balance routes moved to routes/login_opening.py\n\n"
        ),
        slice_lines(lines, 3687, 3928),
        (
            "# Role permission routes moved to routes/role_permissions.py\n\n"
            "# Setup wizard and temple admin routes moved to routes/temples_mgmt.py\n\n"
            "# UPI routes moved to routes/upi.py\n\n"
            "# Public portal routes moved to routes/public.py\n\n"
            "# User routes moved to routes/users.py\n\n"
        ),
        slice_lines(lines, 5807, len(lines)),
    ]
    text = "".join(chunks)
    anchor = "import app.modules.mandir_compat.routes.donations_read"
    if anchor in text:
        text = text.replace(anchor, FOOTER + anchor, 1)
    else:
        text = text.rstrip() + FOOTER
    return text


def main() -> None:
    lines = read_lines()
    original = len(lines)
    write_modules(lines)
    ROUTER.write_text(rewrite_router(lines), encoding="utf-8")
    print(f"router.py: {original} -> {len(ROUTER.read_text(encoding='utf-8').splitlines())} lines")


if __name__ == "__main__":
    main()
