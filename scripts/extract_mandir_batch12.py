"""Mechanical extraction for mandir_compat batch 12 (receipt sequencing helpers).

Pure move-and-re-import only:
- Moves receipt/journal sequence helpers from router.py into
  helpers/receipt_sequencing.py.
- Keeps sequencing constants (_MANDIR_RECEIPT_WIDTH, etc.) in router.py.
- Does NOT touch panchang code.

Run: python scripts/extract_mandir_batch12.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "app/modules/mandir_compat/router.py"
HELPER = ROOT / "app/modules/mandir_compat/helpers/receipt_sequencing.py"


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


RECEIPT_SEQUENCING_REPLACEMENTS = [
    ("get_collection(", "mandir_router.get_collection("),
    ("_MANDIR_RECEIPT_PREFIX_BY_KIND", "mandir_router._MANDIR_RECEIPT_PREFIX_BY_KIND"),
    ("_MANDIR_COUNTERS_COLLECTION", "mandir_router._MANDIR_COUNTERS_COLLECTION"),
    ("_MANDIR_JOURNAL_ENTRY_PREFIX", "mandir_router._MANDIR_JOURNAL_ENTRY_PREFIX"),
    ("_MANDIR_RECEIPT_WIDTH", "mandir_router._MANDIR_RECEIPT_WIDTH"),
]


HELPER_HEADER = '''"""MandirMitra receipt and journal entry sequence helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.

Important for tests:
- Constants and get_collection are resolved via `mandir_router.<name>` so
  monkeypatching `app.modules.mandir_compat.router.<name>` continues to work.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.modules.mandir_compat import router as mandir_router

'''


REEXPORT_BLOCK = [
    "\n",
    "# Receipt sequencing helpers moved to helpers/receipt_sequencing.py; re-exported for tests.\n",
    "from app.modules.mandir_compat.helpers.receipt_sequencing import (\n",
    "    _format_mandir_receipt_number as _format_mandir_receipt_number,\n",
    "    _format_mandir_sequence_number as _format_mandir_sequence_number,\n",
    "    _next_journal_entry_number as _next_journal_entry_number,\n",
    "    _next_receipt_number as _next_receipt_number,\n",
    ")\n",
]


def main() -> None:
    lines = read_lines()
    original = len(lines)

    start = find_index(lines, lambda l: l.strip().startswith("def _format_mandir_receipt_number"))
    end = find_index(lines, lambda l: l.strip() == "# Donation/seva view helpers moved to helpers/views.py")

    body = apply_replacements("".join(lines[start:end]), RECEIPT_SEQUENCING_REPLACEMENTS)
    HELPER.write_text(HELPER_HEADER + body, encoding="utf-8")

    replacement = (
        "# Receipt sequencing helpers moved to helpers/receipt_sequencing.py\n"
        "# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); re-exported at end of module.\n\n"
    )
    lines[start:end] = [replacement]

    insert_anchor = find_index(
        lines,
        lambda l: l.strip().startswith("from app.modules.mandir_compat.helpers.receipt_cancellation import"),
    )
    # Insert before receipt_cancellation import block
    lines[insert_anchor:insert_anchor] = REEXPORT_BLOCK

    ROUTER.write_text("".join(lines), encoding="utf-8")
    updated = len(ROUTER.read_text(encoding="utf-8").splitlines())
    print(f"router.py: {original} -> {updated} lines")
    print(f"helpers/receipt_sequencing.py: {len(HELPER.read_text(encoding='utf-8').splitlines())} lines")


if __name__ == "__main__":
    main()
