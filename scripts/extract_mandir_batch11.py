"""Mechanical extraction for mandir_compat batch 11 (receipt cancellation helpers).

Pure move-and-re-import only:
- Moves shared receipt cancellation helpers from router.py into
  helpers/receipt_cancellation.py.
- Keeps _mandir_actor_id in router (general utility used across modules).
- Does NOT touch quarantined receipt sequencing or panchang code.

Run: python scripts/extract_mandir_batch11.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "app/modules/mandir_compat/router.py"
HELPER = ROOT / "app/modules/mandir_compat/helpers/receipt_cancellation.py"


def read_lines() -> list[str]:
    return ROUTER.read_text(encoding="utf-8").splitlines(keepends=True)


def find_index(lines: list[str], predicate) -> int:
    for i, line in enumerate(lines):
        if predicate(line):
            return i
    raise RuntimeError("Anchor not found")


def apply_replacements(body: str, replacements: list[tuple[str, str]]) -> str:
    for old, new in replacements:
        body = body.replace(old, new)
    return body


RECEIPT_CANCELLATION_REPLACEMENTS = [
    ("_safe_optional_str(", "mandir_router._safe_optional_str("),
    ("_mandir_actor_id(", "mandir_router._mandir_actor_id("),
    ("resolve_mandir_tenant(", "mandir_router.resolve_mandir_tenant("),
    ("get_collection(", "mandir_router.get_collection("),
    ("_mandir_donation_view(", "mandir_router._mandir_donation_view("),
    ("_mandir_seva_booking_view(", "mandir_router._mandir_seva_booking_view("),
    ("_mandir_inventory_item_balance(", "mandir_router._mandir_inventory_item_balance("),
    ("await _reverse_mandir_source_journal(", "await mandir_router._reverse_mandir_source_journal("),
    ("await log_audit_event(", "await mandir_router.log_audit_event("),
    ("logger.", "mandir_router.logger."),
]


HELPER_HEADER = '''"""MandirMitra shared receipt cancellation helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.

Used by donation, seva, and refund receipt cancellation flows.

Important for tests:
- These helpers call other symbols via `mandir_router.<name>` so monkeypatching
  `app.modules.mandir_compat.router.<name>` continues to affect runtime behavior.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models.entities import JournalEntry
from app.accounting.service import reverse_journal_entry
from app.modules.mandir_compat import router as mandir_router

'''


REEXPORT_BLOCK = [
    "\n",
    "# Receipt cancellation helpers moved to helpers/receipt_cancellation.py; re-exported for tests.\n",
    "from app.modules.mandir_compat.helpers.receipt_cancellation import (\n",
    "    _cancel_mandir_receipt_source as _cancel_mandir_receipt_source,\n",
    "    _mandir_receipt_cancellation_metadata as _mandir_receipt_cancellation_metadata,\n",
    "    _reverse_mandir_source_journal as _reverse_mandir_source_journal,\n",
    ")\n",
]


def main() -> None:
    lines = read_lines()
    original = len(lines)

    start = find_index(lines, lambda l: l.strip().startswith("def _mandir_receipt_cancellation_metadata"))
    end = find_index(lines, lambda l: l.strip() == "# Refund-request routes moved to routes/refunds.py")

    body = apply_replacements("".join(lines[start:end]), RECEIPT_CANCELLATION_REPLACEMENTS)
    HELPER.write_text(HELPER_HEADER + body, encoding="utf-8")

    replacement = (
        "# Receipt cancellation helpers moved to helpers/receipt_cancellation.py\n"
        "# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); re-exported at end of module.\n\n"
    )
    lines[start:end] = [replacement]

    insert_anchor = find_index(
        lines,
        lambda l: l.strip().startswith("from app.modules.mandir_compat.helpers.account_resolvers import"),
    )
    lines[insert_anchor:insert_anchor] = REEXPORT_BLOCK

    ROUTER.write_text("".join(lines), encoding="utf-8")
    updated = len(ROUTER.read_text(encoding="utf-8").splitlines())
    print(f"router.py: {original} -> {updated} lines")
    print(f"helpers/receipt_cancellation.py: {len(HELPER.read_text(encoding='utf-8').splitlines())} lines")


if __name__ == "__main__":
    main()
