"""Mechanical extraction for mandir_compat batch 10 (donation posting routes).

Extracts donation POST/cancel/reconcile/cleanup routes into routes/donations_posting.py.
Does NOT move quarantined receipt sequencing/cancellation helpers or panchang code.
Run: python scripts/extract_mandir_batch10.py
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


DONATIONS_POSTING_REPLACEMENTS = [
    ("get_collection(", "mandir_router.get_collection("),
    ("resolve_app_key(", "mandir_router.resolve_app_key("),
    ("resolve_tenant_id(", "mandir_router.resolve_tenant_id("),
    ("resolve_mandir_tenant(", "mandir_router.resolve_mandir_tenant("),
    ("await _ensure_default_mandir_sql_accounts_safe(", "await mandir_router._ensure_default_mandir_sql_accounts_safe("),
    ("_mandir_actor_id(", "mandir_router._mandir_actor_id("),
    ("_safe_float(", "mandir_router._safe_float("),
    ("_safe_optional_str(", "mandir_router._safe_optional_str("),
    ("_normalize_phone(", "mandir_router._normalize_phone("),
    ("_to_positive_int(", "mandir_router._to_positive_int("),
    ("_mandir_cash_income_category(", "mandir_router._mandir_cash_income_category("),
    ("_mandir_in_kind_debit_account_target(", "mandir_router._mandir_in_kind_debit_account_target("),
    ("_mandir_in_kind_income_category(", "mandir_router._mandir_in_kind_income_category("),
    ("await post_journal_entry(", "await mandir_router.post_journal_entry("),
    ("await reverse_journal_entry(", "await mandir_router.reverse_journal_entry("),
    ("await _resolve_mandir_payment_account_id(", "await mandir_router._resolve_mandir_payment_account_id("),
    ("await _resolve_mandir_income_account(", "await mandir_router._resolve_mandir_income_account("),
    ("await _resolve_or_create_mandir_account(", "await mandir_router._resolve_or_create_mandir_account("),
    ("await _mandir_inventory_accounting_enabled(", "await mandir_router._mandir_inventory_accounting_enabled("),
    ("await _next_receipt_number(", "await mandir_router._next_receipt_number("),
    ("await _cancel_mandir_receipt_source(", "await mandir_router._cancel_mandir_receipt_source("),
    ("await _upsert_devotee_from_contribution(", "await mandir_router._upsert_devotee_from_contribution("),
    ("_mandir_donation_view(", "mandir_router._mandir_donation_view("),
    ("logger.", "mandir_router.logger."),
]


FOOTER = '''
import app.modules.mandir_compat.routes.donations_posting  # noqa: E402, F401
from app.modules.mandir_compat.routes.donations_posting import (
    approve_mandir_in_kind_valuation as approve_mandir_in_kind_valuation,
    cancel_donation_receipt as cancel_donation_receipt,
    cleanup_donation_entry as cleanup_donation_entry,
    create_donation as create_donation,
    reconcile_donation_posting as reconcile_donation_posting,
)

'''


def write_module(lines: list[str]) -> None:
    body = apply_replacements(slice_lines(lines, 581, 1164), DONATIONS_POSTING_REPLACEMENTS)
    routes_dir = ROOT / "app/modules/mandir_compat/routes"
    (routes_dir / "donations_posting.py").write_text(
        f'''"""MandirMitra donation posting routes (create, valuation approve, cancel, reconcile, cleanup).

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models.entities import JournalEntry
from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.donation_compliance import classify_donation_compliance
from app.modules.mandir_compat.router import _MANDIR_ADMIN_ROUTE_DEPS, _MANDIR_WRITE_ROUTE_DEPS, router

{body}
''',
        encoding="utf-8",
    )


def rewrite_router(lines: list[str]) -> str:
    chunks = [
        slice_lines(lines, 1, 580),
        (
            "# Donation posting routes moved to routes/donations_posting.py\n"
            "# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.\n\n"
        ),
        slice_lines(lines, 1167, len(lines)),
    ]
    text = "".join(chunks)
    anchor = "import app.modules.mandir_compat.routes.pincode"
    if anchor not in text:
        raise RuntimeError(f"Expected anchor not found: {anchor}")
    text = text.replace(anchor, FOOTER + anchor, 1)
    return text


def main() -> None:
    lines = read_lines()
    original = len(lines)
    write_module(lines)
    ROUTER.write_text(rewrite_router(lines), encoding="utf-8")
    print(f"router.py: {original} -> {len(ROUTER.read_text(encoding='utf-8').splitlines())} lines")


if __name__ == "__main__":
    main()
