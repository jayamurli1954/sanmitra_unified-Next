"""Extract Mandir financial report renderers from mitrabooks-erp/app.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "mitrabooks-erp" / "app.js"
OUT = ROOT / "frontend" / "mitrabooks-erp" / "modules" / "workspaces" / "mandir-financial-reports.js"

STATE_REPLACEMENTS = [
    ("lastMandirExpenses", "mandirReportState.expenses"),
    ("lastMandirTrialBalance", "mandirReportState.trialBalance"),
    ("lastMandirLedger", "mandirReportState.ledger"),
    ("lastMandirFinancialReports", "mandirReportState.financialReports"),
]

EXPORT_NAMES = [
    "renderMandirExpensesTable",
    "renderMandirTrialBalance",
    "renderMandirFinancialReports",
]

HEADER = '''// ====================================================================
// SECTION: MANDIR — financial reports (TB / I&E / B&P / BS)
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initMandirFinancialReports(...).
// ====================================================================

export const mandirReportState = {
  expenses: [],
  trialBalance: null,
  ledger: null,
  financialReports: {},
};

/** @type {{
 *   escapeHtml: (v: string) => string,
 *   formatCurrency: (v: number | string) => string,
 *   renderStatCards: (stats: unknown[]) => string,
 *   getDrilldownFromDate: () => string,
 *   getDrilldownToDate: () => string,
 *   todayIsoDate: () => string,
 * } | null} */
let deps = null;

export function initMandirFinancialReports({
  escapeHtml,
  formatCurrency,
  renderStatCards,
  getDrilldownFromDate,
  getDrilldownToDate,
  todayIsoDate,
}) {
  deps = {
    escapeHtml,
    formatCurrency,
    renderStatCards,
    getDrilldownFromDate,
    getDrilldownToDate,
    todayIsoDate,
  };
}

function requireDeps() {
  if (!deps) {
    throw new Error("initMandirFinancialReports() must be called before using Mandir report renderers");
  }
  return deps;
}

function escapeHtml(value) {
  return requireDeps().escapeHtml(value);
}

function formatCurrency(value) {
  return requireDeps().formatCurrency(value);
}

function renderStatCards(stats) {
  return requireDeps().renderStatCards(stats);
}

function accountingDrilldownFromDate() {
  return requireDeps().getDrilldownFromDate();
}

function accountingDrilldownToDate() {
  return requireDeps().getDrilldownToDate();
}

function todayIsoDate() {
  return requireDeps().todayIsoDate();
}

'''


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    body = "".join(lines[3867:4249])
    for old, new in STATE_REPLACEMENTS:
        body = re.sub(rf"\b{old}\b", new, body)
    body = body.replace("accountingDrilldownState.from_date", "accountingDrilldownFromDate()")
    body = body.replace("accountingDrilldownState.to_date", "accountingDrilldownToDate()")
    for name in EXPORT_NAMES:
        body = body.replace(f"function {name}", f"export function {name}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(HEADER + body, encoding="utf-8")
    print(f"Wrote {OUT} ({sum(1 for _ in OUT.open(encoding='utf-8'))} lines)")


if __name__ == "__main__":
    main()
