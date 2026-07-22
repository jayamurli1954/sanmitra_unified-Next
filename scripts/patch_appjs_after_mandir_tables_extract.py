"""Patch app.js after Mandir tables extraction."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "mitrabooks-erp" / "app.js"

IMPORT_BLOCK = '''import {
  initMandirTables,
  MANDIR_LIST_PAGE_SIZE,
  mandirListState,
  renderMandirPublicPaymentsTable,
  formatMandirExceptionReasons,
  renderMandirExceptionsTable,
  mandirReceiptRowsFromLists,
  renderMandirReceiptHistoryTable,
  renderMandirReceiptActions,
  renderMandirDonationsTable,
  renderMandirSevaBookingsTable,
  renderMandirWorkspaceTabs,
  renderMandirListFilters,
  renderMandirPublicPaymentFilters,
  renderMandirExceptionFilters,
} from "./modules/workspaces/mandir-tables.js";
'''

INIT_BLOCK = '''
// Wire Mandir table renderers (avoids import cycle with app.js)
initMandirTables({
  escapeHtml,
  formatCurrency,
});
'''

STATE_START = "const MANDIR_LIST_PAGE_SIZE = 8;\n"


def line_is_mandir_shared_table_start(line: str) -> bool:
    return line.startswith("function renderMandirPublicPaymentsTable")


def line_is_mandir_shared_table_end(line: str) -> bool:
    return line.startswith("function mandirPublicPaymentPageUrl")


def line_is_mandir_receipt_section(line: str) -> bool:
    return "SECTION: MANDIR — receipt / donation / seva tables" in line


def line_is_mandir_receipt_table_start(line: str) -> bool:
    return line.startswith("function renderMandirDonationsTable")


def line_is_recent_tenants_start(line: str) -> bool:
    return line.startswith("function renderRecentTenantsTable")


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)

    # Remove MANDIR_LIST_PAGE_SIZE + mandirListState block
    out: list[str] = []
    skip_state = False
    for line in lines:
        if line == STATE_START:
            skip_state = True
            continue
        if skip_state:
            if line.startswith("const todayForReports"):
                skip_state = False
                out.append(line)
            continue
        out.append(line)
    lines = out

    # Remove shared-utilities Mandir table helpers
    out = []
    skip = False
    for line in lines:
        if line_is_mandir_shared_table_start(line):
            skip = True
            continue
        if skip and line_is_mandir_shared_table_end(line):
            skip = False
            out.append(line)
            continue
        if skip:
            continue
        out.append(line)
    lines = out

    # Remove mandir receipt section (banner + tables/filters), keep renderRecentTenantsTable
    out = []
    skip = False
    for i, line in enumerate(lines):
        if line_is_mandir_receipt_section(line):
            skip = True
            continue
        if skip and line_is_mandir_receipt_table_start(line):
            continue
        if skip and line_is_recent_tenants_start(line):
            skip = False
            out.append("\n")
            out.append(line)
            continue
        if skip:
            continue
        out.append(line)
    text = "".join(out)

    if 'from "./modules/workspaces/mandir-tables.js"' not in text:
        text = text.replace(
            '} from "./modules/workspaces/mandir-financial-reports.js";\n',
            '} from "./modules/workspaces/mandir-financial-reports.js";\n' + IMPORT_BLOCK,
        )

    if "initMandirTables({" not in text:
        text = text.replace(
            "  todayIsoDate,\n});\n\n// Initialize theme on app load",
            "  todayIsoDate,\n});" + INIT_BLOCK + "\n// Initialize theme on app load",
            1,
        )

    APP.write_text(text, encoding="utf-8")
    print(f"Patched {APP} ({text.count(chr(10)) + 1} lines)")


if __name__ == "__main__":
    main()
