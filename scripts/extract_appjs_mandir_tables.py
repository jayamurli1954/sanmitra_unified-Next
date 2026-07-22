"""Extract Mandir receipt/donation/seva table renderers from mitrabooks-erp/app.js."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "mitrabooks-erp" / "app.js"
OUT = ROOT / "frontend" / "mitrabooks-erp" / "modules" / "workspaces" / "mandir-tables.js"

# 1-based inclusive line ranges in current app.js
SHARED_BLOCK = (2307, 2566)  # renderMandirPublicPaymentsTable .. renderMandirReceiptActions
RECEIPT_BLOCK = (3175, 3468)  # renderMandirDonationsTable .. renderMandirExceptionFilters
STATE_BLOCK = (315, 344)  # MANDIR_LIST_PAGE_SIZE + mandirListState

EXPORT_NAMES = [
    "renderMandirPublicPaymentsTable",
    "formatMandirExceptionReasons",
    "renderMandirExceptionsTable",
    "mandirReceiptRowsFromLists",
    "renderMandirReceiptHistoryTable",
    "renderMandirReceiptActions",
    "renderMandirDonationsTable",
    "renderMandirSevaBookingsTable",
    "renderMandirWorkspaceTabs",
    "renderMandirListFilters",
    "renderMandirPublicPaymentFilters",
    "renderMandirExceptionFilters",
]

HEADER = '''// ====================================================================
// SECTION: MANDIR — receipt / donation / seva tables
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initMandirTables(...).
// ====================================================================

export const MANDIR_LIST_PAGE_SIZE = 8;

export const mandirListState = {
  donations: {
    offset: 0,
    q: "",
    from_date: "",
    to_date: "",
    payment_mode: "",
  },
  sevas: {
    offset: 0,
    q: "",
    from_date: "",
    to_date: "",
    status: "",
  },
  payments: {
    offset: 0,
    q: "",
    status: "pending",
    payment_type: "",
  },
  exceptions: {
    offset: 0,
    q: "",
    reason: "",
    status: "",
    payment_type: "",
  },
};

/** @type {{ escapeHtml: (v: string) => string, formatCurrency: (v: number | string) => string } | null} */
let deps = null;

export function initMandirTables({ escapeHtml, formatCurrency }) {
  deps = { escapeHtml, formatCurrency };
}

function requireDeps() {
  if (!deps) {
    throw new Error("initMandirTables() must be called before using Mandir table renderers");
  }
  return deps;
}

function escapeHtml(value) {
  return requireDeps().escapeHtml(value);
}

function formatCurrency(value) {
  return requireDeps().formatCurrency(value);
}

'''


def slice_lines(lines: list[str], start: int, end: int) -> str:
    return "".join(lines[start - 1 : end])


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    body = slice_lines(lines, *SHARED_BLOCK) + "\n" + slice_lines(lines, *RECEIPT_BLOCK)
    for name in EXPORT_NAMES:
        body = body.replace(f"function {name}", f"export function {name}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(HEADER + body, encoding="utf-8")
    print(f"Wrote {OUT} ({sum(1 for _ in OUT.open(encoding='utf-8'))} lines)")


if __name__ == "__main__":
    main()
