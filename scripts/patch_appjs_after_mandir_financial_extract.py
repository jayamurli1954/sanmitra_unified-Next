"""Patch app.js after Mandir financial reports extraction."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "mitrabooks-erp" / "app.js"

IMPORT_BLOCK = '''import {
  initMandirFinancialReports,
  mandirReportState,
  renderMandirExpensesTable,
  renderMandirTrialBalance,
  renderMandirFinancialReports,
} from "./modules/workspaces/mandir-financial-reports.js";
'''

INIT_BLOCK = '''
// Wire Mandir financial report renderers (avoids import cycle with app.js)
initMandirFinancialReports({
  escapeHtml,
  formatCurrency,
  renderStatCards,
  getDrilldownFromDate: () => accountingDrilldownState.from_date,
  getDrilldownToDate: () => accountingDrilldownState.to_date,
  todayIsoDate,
});
'''

STATE_LINES = {
    "let lastMandirExpenses = [];\n",
    "let lastMandirTrialBalance = null;\n",
    "let lastMandirLedger = null;\n",
    "let lastMandirFinancialReports = {};\n",
}

REPLACEMENTS = [
    ("lastMandirExpenses", "mandirReportState.expenses"),
    ("lastMandirTrialBalance", "mandirReportState.trialBalance"),
    ("lastMandirLedger", "mandirReportState.ledger"),
    ("lastMandirFinancialReports", "mandirReportState.financialReports"),
]


def line_is_mandir_financial_start(line: str) -> bool:
    return line.startswith("function renderMandirExpensesTable")


def line_is_panchang_section(line: str) -> bool:
    return "SECTION: MANDIR — panchang" in line


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)

    out: list[str] = []
    for line in lines:
        if line in STATE_LINES:
            continue
        out.append(line)
    lines = out

    out = []
    skip = False
    for i, line in enumerate(lines):
        if line_is_mandir_financial_start(line):
            skip = True
            continue
        if skip and line_is_panchang_section(line):
            skip = False
            if i > 0 and lines[i - 1].strip().startswith("// ═"):
                out.append(lines[i - 1])
            out.append(line)
            continue
        if skip:
            continue
        out.append(line)
    text = "".join(out)

    if 'from "./modules/workspaces/mandir-financial-reports.js"' not in text:
        text = text.replace(
            '} from "./modules/workspaces/hr.js";\n',
            '} from "./modules/workspaces/hr.js";\n' + IMPORT_BLOCK,
        )

    if "initMandirFinancialReports({" not in text:
        text = text.replace(
            "});\n\n// Initialize theme on app load",
            "});" + INIT_BLOCK + "\n// Initialize theme on app load",
            1,
        )

    for old, new in REPLACEMENTS:
        text = text.replace(old, new)

    APP.write_text(text, encoding="utf-8")
    print(f"Patched {APP} ({text.count(chr(10)) + 1} lines)")


if __name__ == "__main__":
    main()
