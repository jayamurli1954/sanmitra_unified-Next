"""Mechanical extraction for mandir_compat batch 7 (no panchang, no donation posting).

Extracts pincode lookup, seva bookings, seva reminders, and users/me.
Run: python scripts/extract_mandir_batch7.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "app/modules/mandir_compat/router.py"
USERS = ROOT / "app/modules/mandir_compat/routes/users.py"


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
    ("resolve_mandir_tenant(", "mandir_router.resolve_mandir_tenant("),
    ("await _ensure_default_mandir_sql_accounts_safe(", "await mandir_router._ensure_default_mandir_sql_accounts_safe("),
    ("_mandir_actor_id(", "mandir_router._mandir_actor_id("),
    ("_safe_float(", "mandir_router._safe_float("),
    ("_safe_optional_str(", "mandir_router._safe_optional_str("),
    ("_normalize_phone(", "mandir_router._normalize_phone("),
    ("await post_journal_entry(", "await mandir_router.post_journal_entry("),
    ("await reverse_journal_entry(", "await mandir_router.reverse_journal_entry("),
    ("logger.", "mandir_router.logger."),
]

SEVA_BOOKINGS_REPLACEMENTS = COMMON_REPLACEMENTS + [
    ("await _resolve_mandir_payment_account_id(", "await mandir_router._resolve_mandir_payment_account_id("),
    ("await _resolve_mandir_income_account(", "await mandir_router._resolve_mandir_income_account("),
    ("await _next_receipt_number(", "await mandir_router._next_receipt_number("),
    ("await _find_devotee_by_phone(", "await mandir_router._find_devotee_by_phone("),
    ("await _validate_seva_booking_capacity(", "await mandir_router._validate_seva_booking_capacity("),
    ("await _resolve_temple_receipt_profile(", "await mandir_router._resolve_temple_receipt_profile("),
    ("await _cancel_mandir_receipt_source(", "await mandir_router._cancel_mandir_receipt_source("),
    ("await create_donation(", "await mandir_router.create_donation("),
    ("await create_seva_booking(", "await mandir_router.create_seva_booking("),
    ("_parse_booking_date(", "mandir_router._parse_booking_date("),
    ("_validate_seva_booking_date(", "mandir_router._validate_seva_booking_date("),
    ("_mandir_seva_booking_view(", "mandir_router._mandir_seva_booking_view("),
    ("_mandir_filter_rows(", "mandir_router._mandir_filter_rows("),
    ("_receipt_number_for_seva(", "mandir_router._receipt_number_for_seva("),
    ("_generate_seva_receipt_pdf_bytes(", "mandir_router._generate_seva_receipt_pdf_bytes("),
]

PINCODE_REPLACEMENTS = [
    ("_normalize_pincode(", "mandir_router._normalize_pincode("),
    ("await _lookup_pincode_city_state(", "await mandir_router._lookup_pincode_city_state("),
]

SEVA_REMINDERS_REPLACEMENTS = COMMON_REPLACEMENTS


def write_modules(lines: list[str]) -> None:
    pincode_body = apply_replacements(slice_lines(lines, 2879, 2894), PINCODE_REPLACEMENTS)
    bookings_body = apply_replacements(slice_lines(lines, 2919, 3468), SEVA_BOOKINGS_REPLACEMENTS)
    reminders_body = apply_replacements(
        slice_lines(lines, 3480, 3628) + slice_lines(lines, 3635, 3657),
        SEVA_REMINDERS_REPLACEMENTS,
    )
    users_me_body = slice_lines(lines, 3471, 3473)

    routes_dir = ROOT / "app/modules/mandir_compat/routes"

    (routes_dir / "pincode.py").write_text(
        f'''"""MandirMitra pincode lookup route.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from fastapi import Depends, Query

from app.core.auth.dependencies import get_current_user
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import router

{pincode_body}
''',
        encoding="utf-8",
    )

    (routes_dir / "seva_bookings.py").write_text(
        f'''"""MandirMitra seva booking routes (create, list, receipt PDF, cancel, reschedule).

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from typing import Any
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.core.tenants.context import resolve_app_key, resolve_tenant_id
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import _MANDIR_WRITE_ROUTE_DEPS, router

{bookings_body}
''',
        encoding="utf-8",
    )

    (routes_dir / "seva_reminders.py").write_text(
        f'''"""MandirMitra seva reminder configuration and trigger routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, Header, HTTPException, Query

from app.core.auth.dependencies import get_current_user
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import _MANDIR_ADMIN_ROUTE_DEPS, router

{reminders_body}
''',
        encoding="utf-8",
    )

    users_text = USERS.read_text(encoding="utf-8")
    if "mandir_users_me" not in users_text:
        USERS.write_text(users_text.rstrip() + "\n\n" + users_me_body, encoding="utf-8")


FOOTER = '''
import app.modules.mandir_compat.routes.pincode  # noqa: E402, F401
import app.modules.mandir_compat.routes.seva_bookings  # noqa: E402, F401
import app.modules.mandir_compat.routes.seva_reminders  # noqa: E402, F401
from app.modules.mandir_compat.routes.pincode import (
    mandir_pincode_lookup as mandir_pincode_lookup,
)
from app.modules.mandir_compat.routes.seva_bookings import (
    cancel_seva_receipt as cancel_seva_receipt,
    create_quick_ticket as create_quick_ticket,
    create_seva_booking as create_seva_booking,
    get_seva_receipt_pdf as get_seva_receipt_pdf,
    mandir_approve_seva_reschedule as mandir_approve_seva_reschedule,
    mandir_request_seva_reschedule as mandir_request_seva_reschedule,
    mandir_seva_bookings as mandir_seva_bookings,
    mandir_seva_reschedule_pending as mandir_seva_reschedule_pending,
)
from app.modules.mandir_compat.routes.seva_reminders import (
    mandir_seva_reminder_config as mandir_seva_reminder_config,
    mandir_seva_reminders_trigger as mandir_seva_reminders_trigger,
    mandir_seva_reminders_upcoming as mandir_seva_reminders_upcoming,
    mandir_update_seva_reminder_config as mandir_update_seva_reminder_config,
)

'''


def rewrite_router(lines: list[str]) -> str:
    chunks = [
        slice_lines(lines, 1, 2873),
        (
            "# Pincode route moved to routes/pincode.py\n"
            "# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.\n\n"
        ),
        slice_lines(lines, 2896, 2918),
        (
            "# Seva booking routes moved to routes/seva_bookings.py\n\n"
            "# Seva reminder routes moved to routes/seva_reminders.py\n\n"
            "# GET /users/me moved to routes/users.py\n\n"
        ),
        slice_lines(lines, 3660, len(lines)),
    ]
    text = "".join(chunks)
    users_import = "from app.modules.mandir_compat.routes.users import ("
    if users_import in text:
        text = text.replace(
            users_import,
            FOOTER + users_import,
            1,
        )
        text = text.replace(
            "    mandir_users as mandir_users,\n)",
            "    mandir_users as mandir_users,\n    mandir_users_me as mandir_users_me,\n)",
            1,
        )
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
