"""Mechanical extraction for mandir_compat batch 5 (no panchang, no donation posting).

Extracts donation read routes, misc compat stubs, hundi, inventory, and reports.
Run: python scripts/extract_mandir_batch5.py
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


ROUTE_REPLACEMENTS = [
    ("get_collection(", "mandir_router.get_collection("),
    ("_sanitize_mongo_doc(", "mandir_router._sanitize_mongo_doc("),
    ("resolve_app_key(", "mandir_router.resolve_app_key("),
    ("resolve_tenant_id(", "mandir_router.resolve_tenant_id("),
    ("await _payment_accounts(", "await mandir_router._payment_accounts("),
    ("_mandir_donation_view(", "mandir_router._mandir_donation_view("),
    ("_mandir_filter_rows(", "mandir_router._mandir_filter_rows("),
    ("_receipt_number_for_donation(", "mandir_router._receipt_number_for_donation("),
    ("await _resolve_temple_receipt_profile(", "await mandir_router._resolve_temple_receipt_profile("),
    ("_generate_donation_receipt_pdf_bytes(", "mandir_router._generate_donation_receipt_pdf_bytes("),
    ("await _ensure_default_mandir_sql_accounts_safe(", "await mandir_router._ensure_default_mandir_sql_accounts_safe("),
    ("await list_accounts(", "await mandir_router.list_accounts("),
    ("_mandir_actor_id(", "mandir_router._mandir_actor_id("),
    ("_safe_optional_str(", "mandir_router._safe_optional_str("),
    ("await post_journal_entry(", "await mandir_router.post_journal_entry("),
    ("await reverse_journal_entry(", "await mandir_router.reverse_journal_entry("),
    ("await _resolve_or_create_mandir_account(", "await mandir_router._resolve_or_create_mandir_account("),
    ("await _resolve_mandir_income_account(", "await mandir_router._resolve_mandir_income_account("),
    ("await _reverse_mandir_source_journal(", "await mandir_router._reverse_mandir_source_journal("),
    ("await _mandir_inventory_accounting_enabled(", "await mandir_router._mandir_inventory_accounting_enabled("),
    ("_normalize_income_category(", "mandir_router._normalize_income_category("),
    ("_parse_iso_datetime(", "mandir_router._parse_iso_datetime("),
    ("_resolve_report_date_window(", "mandir_router._resolve_report_date_window("),
    ("_resolve_export_window(", "mandir_router._resolve_export_window("),
    ("logger.", "mandir_router.logger."),
]

HUNDI_REPLACEMENTS = ROUTE_REPLACEMENTS

INVENTORY_REPLACEMENTS = ROUTE_REPLACEMENTS + [
    ("await _mandir_inventory_item_position(", "await _mandir_inventory_item_position("),
    ("await _mandir_inventory_item_balance(", "await _mandir_inventory_item_balance("),
]

REPORTS_REPLACEMENTS = ROUTE_REPLACEMENTS + [
    ("await posted_donations(", "await mandir_router.posted_donations("),
    ("await get_cost_centre_ledger_pl(", "await mandir_router.get_cost_centre_ledger_pl("),
]


def write_modules(lines: list[str]) -> None:
    donations_body = apply_replacements(
        slice_lines(lines, 2046, 2065)
        + slice_lines(lines, 2074, 2111)
        + slice_lines(lines, 2478, 2533),
        ROUTE_REPLACEMENTS,
    )
    misc_body = apply_replacements(slice_lines(lines, 2779, 3048), ROUTE_REPLACEMENTS)
    hundi_body = apply_replacements(slice_lines(lines, 3051, 3234), HUNDI_REPLACEMENTS)
    inventory_body = apply_replacements(slice_lines(lines, 3243, 3742), INVENTORY_REPLACEMENTS)
    reports_body = apply_replacements(slice_lines(lines, 5014, 5409), REPORTS_REPLACEMENTS)

    routes_dir = ROOT / "app/modules/mandir_compat/routes"

    (routes_dir / "donations_read.py").write_text(
        f'''"""MandirMitra donation read-only routes (list, categories, receipt PDF).

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from io import BytesIO
from typing import Any

from fastapi import Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.core.auth.dependencies import get_current_user
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import router

{donations_body}
''',
        encoding="utf-8",
    )

    (routes_dir / "misc_compat.py").write_text(
        f'''"""MandirMitra compatibility stub routes (assets, backup, bank, HR, etc.).

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import Depends, File, Header, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import (
    _MANDIR_ADMIN_ROUTE_DEPS,
    _MANDIR_WRITE_ROUTE_DEPS,
    router,
)


def _ok(name: str, **extra: Any) -> dict[str, Any]:
    return {{"status": "ok", "endpoint": name, **extra}}


{misc_body}
''',
        encoding="utf-8",
    )

    (routes_dir / "hundi.py").write_text(
        f'''"""MandirMitra hundi master and opening workflow routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import (
    _MANDIR_ADMIN_ROUTE_DEPS,
    _MANDIR_WRITE_ROUTE_DEPS,
    router,
)

{hundi_body}
''',
        encoding="utf-8",
    )

    (routes_dir / "inventory.py").write_text(
        f'''"""MandirMitra inventory items, movements, and consumption routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import uuid4

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import (
    _MANDIR_ADMIN_ROUTE_DEPS,
    _MANDIR_WRITE_ROUTE_DEPS,
    router,
)

{inventory_body}
''',
        encoding="utf-8",
    )

    (routes_dir / "reports.py").write_text(
        f'''"""MandirMitra donation, seva, and fund reporting routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.reports.cost_centre_ledger import get_cost_centre_ledger_pl
from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.reports import (
    detailed_donation_report,
    detailed_seva_report,
    donation_category_wise_report,
    donation_daily_report,
    donation_monthly_report,
    posted_donations,
    seva_schedule_report,
)
from app.modules.mandir_compat.router import router

{reports_body}
''',
        encoding="utf-8",
    )


FOOTER = '''
import app.modules.mandir_compat.routes.donations_read  # noqa: E402, F401
import app.modules.mandir_compat.routes.misc_compat  # noqa: E402, F401
import app.modules.mandir_compat.routes.hundi  # noqa: E402, F401
import app.modules.mandir_compat.routes.inventory  # noqa: E402, F401
import app.modules.mandir_compat.routes.reports  # noqa: E402, F401
from app.modules.mandir_compat.routes.donations_read import (
    donations_categories as donations_categories,
    donations_payment_accounts as donations_payment_accounts,
    get_donation_receipt_pdf as get_donation_receipt_pdf,
    list_donations as list_donations,
)
from app.modules.mandir_compat.routes.misc_compat import _ok as _ok
from app.modules.mandir_compat.routes.hundi import (
    approve_mandir_hundi_opening as approve_mandir_hundi_opening,
    cancel_mandir_hundi_opening as cancel_mandir_hundi_opening,
    create_mandir_hundi_master as create_mandir_hundi_master,
    create_mandir_hundi_opening as create_mandir_hundi_opening,
    mandir_hundi_masters as mandir_hundi_masters,
    mandir_hundi_openings as mandir_hundi_openings,
)
from app.modules.mandir_compat.routes.inventory import (
    _mandir_inventory_item_balance as _mandir_inventory_item_balance,
    _mandir_inventory_item_position as _mandir_inventory_item_position,
    approve_mandir_inventory_consumption as approve_mandir_inventory_consumption,
    cancel_mandir_inventory_consumption as cancel_mandir_inventory_consumption,
    create_mandir_inventory_consumption as create_mandir_inventory_consumption,
    list_mandir_inventory_consumptions as list_mandir_inventory_consumptions,
    list_mandir_inventory_movements as list_mandir_inventory_movements,
    mandir_create_inventory_item as mandir_create_inventory_item,
    mandir_delete_inventory_item as mandir_delete_inventory_item,
    mandir_inventory_items as mandir_inventory_items,
    mandir_inventory_stock_balances as mandir_inventory_stock_balances,
    mandir_inventory_summary as mandir_inventory_summary,
    mandir_update_inventory_item as mandir_update_inventory_item,
)
from app.modules.mandir_compat.routes.reports import (
    _mandir_donation_designation_report as _mandir_donation_designation_report,
    _mandir_fund_subledger_data as _mandir_fund_subledger_data,
    mandir_donations_daily_report as mandir_donations_daily_report,
    mandir_donations_export_excel as mandir_donations_export_excel,
    mandir_donations_export_pdf as mandir_donations_export_pdf,
    mandir_donations_monthly_report as mandir_donations_monthly_report,
    mandir_report_donations_category_wise as mandir_report_donations_category_wise,
    mandir_report_donations_detailed as mandir_report_donations_detailed,
    mandir_report_donations_festival_wise as mandir_report_donations_festival_wise,
    mandir_report_donations_fund_wise as mandir_report_donations_fund_wise,
    mandir_report_fund_subledger as mandir_report_fund_subledger,
    mandir_report_funds_as_of as mandir_report_funds_as_of,
    mandir_report_sevas_detailed as mandir_report_sevas_detailed,
    mandir_report_sevas_schedule as mandir_report_sevas_schedule,
)

'''


def rewrite_router(lines: list[str]) -> str:
    chunks = [
        slice_lines(lines, 1, 2045),
        (
            "# Donation read routes moved to routes/donations_read.py\n"
            "# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.\n\n"
        ),
        slice_lines(lines, 2114, 2477),
        slice_lines(lines, 2536, 2773),
        (
            "# Misc compat routes moved to routes/misc_compat.py\n\n"
            "# Hundi routes moved to routes/hundi.py\n\n"
            "# Inventory routes moved to routes/inventory.py\n\n"
        ),
        slice_lines(lines, 3745, 5009),
        (
            "# Reports routes moved to routes/reports.py\n"
            "# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.\n\n"
        ),
        slice_lines(lines, 5413, len(lines)),
    ]
    text = "".join(chunks)
    anchor = "import app.modules.mandir_compat.routes.dashboard"
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
