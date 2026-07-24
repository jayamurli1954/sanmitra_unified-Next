#!/usr/bin/env python3
"""Extract Mandir dashboard home + workspace tabs (Phase 3 seam 49)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/mandir-dashboard.js"

HEADER = '''\
// ====================================================================
// SECTION: MANDIR — DASHBOARD HOME + WORKSPACE TABS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initMandirDashboard(...).
// ====================================================================

/** @type {Record<string, Function> | null} */
let deps = null;

export function initMandirDashboard(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initMandirDashboard() must be called before using Mandir dashboard helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function formatCountLabel(...args) { return requireDeps().formatCountLabel(...args); }
function renderStatCards(stats) { return requireDeps().renderStatCards(stats); }
function renderActivity(items) { return requireDeps().renderActivity(items); }
function isProductionShell() { return requireDeps().isProductionShell(); }
function isMandirHost() { return requireDeps().isMandirHost(); }
function renderMandirWorkspaceTabs(active) { return requireDeps().renderMandirWorkspaceTabs(active); }
function renderMandirOperationResult(result) { return requireDeps().renderMandirOperationResult(result); }
function renderMandirCreateForms(payload) { return requireDeps().renderMandirCreateForms(payload); }
function renderMandirListFilters(...args) { return requireDeps().renderMandirListFilters(...args); }
function renderMandirDonationsTable(rows) { return requireDeps().renderMandirDonationsTable(rows); }
function renderMandirSevaBookingsTable(rows) { return requireDeps().renderMandirSevaBookingsTable(rows); }
function mandirPublicPaymentPageUrl() { return requireDeps().mandirPublicPaymentPageUrl(); }
function renderMandirPublicPaymentFilters(n) { return requireDeps().renderMandirPublicPaymentFilters(n); }
function renderMandirPublicPaymentsTable(rows) { return requireDeps().renderMandirPublicPaymentsTable(rows); }
function renderMandirExceptionFilters(n) { return requireDeps().renderMandirExceptionFilters(n); }
function renderMandirExceptionsTable(rows) { return requireDeps().renderMandirExceptionsTable(rows); }
function renderMandirReceiptHistoryTable(rows) { return requireDeps().renderMandirReceiptHistoryTable(rows); }
function renderMandirPanchang(payload) { return requireDeps().renderMandirPanchang(payload); }
function renderMandirOperationalReports(reports) { return requireDeps().renderMandirOperationalReports(reports); }
function renderMandirDevoteesView(reports) { return requireDeps().renderMandirDevoteesView(reports); }
function renderAccountingDrilldownPanel(...args) { return requireDeps().renderAccountingDrilldownPanel(...args); }
function renderMandirTrialBalance(payload) { return requireDeps().renderMandirTrialBalance(payload); }
function renderMandirFinancialReports(reports) { return requireDeps().renderMandirFinancialReports(reports); }
function renderMandirExpensesTable(rows) { return requireDeps().renderMandirExpensesTable(rows); }
function getActiveMandirWorkspace() { return requireDeps().getActiveMandirWorkspace(); }
function getMandirReportState() { return requireDeps().getMandirReportState(); }
function getLastMandirPanchang() { return requireDeps().getLastMandirPanchang(); }
function getLastMandirOperationalReports() { return requireDeps().getLastMandirOperationalReports(); }

'''

EXPORT_FUNCS = [
    "renderMandirDashboardHome",
    "renderMandirDashboard",
    "renderMandirSettings",
    "renderMandirImplementationChecks",
    "renderMandirPlatformOwnerShortcut",
]


def find_fn_block(lines: list[str], name: str) -> tuple[int, int]:
    start = next(
        i
        for i, l in enumerate(lines)
        if re.match(rf"^(async )?function {re.escape(name)}\b", l.lstrip())
    )
    depth = 0
    started = False
    end = start
    for i in range(start, len(lines)):
        line = lines[i]
        if "{" in line or "}" in line:
            depth += line.count("{") - line.count("}")
            started = True
        if started and depth <= 0:
            end = i + 1
            break
    else:
        raise SystemExit(f"unterminated function for {name}")
    while end < len(lines) and lines[end].strip() == "":
        end += 1
    return start, end


def main() -> None:
    if OUT.exists() and "export function renderMandirDashboard" in OUT.read_text(encoding="utf-8"):
        print("Already extracted")
        return

    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    spans: list[tuple[int, int, str]] = []
    for name in EXPORT_FUNCS:
        start, end = find_fn_block(lines, name)
        spans.append((start, end, name))
    spans.sort(key=lambda s: s[0], reverse=True)
    chunks: dict[str, str] = {}
    for start, end, name in spans:
        chunks[name] = "".join(lines[start:end])
        del lines[start:end]

    block = "".join(chunks[name] for name in EXPORT_FUNCS)
    for name in EXPORT_FUNCS:
        block = re.sub(
            rf"(?m)^(async )?function {name}\b",
            rf"export \1function {name}",
            block,
            count=1,
        )
    block = block.replace("export export ", "export ")
    block = block.replace("mandirReportState.trialBalance", "getMandirReportState().trialBalance")
    block = block.replace("mandirReportState.financialReports", "getMandirReportState().financialReports")
    block = block.replace("payload.panchang || lastMandirPanchang", "payload.panchang || getLastMandirPanchang()")
    block = block.replace(
        "payload.operational_reports || lastMandirOperationalReports",
        "payload.operational_reports || getLastMandirOperationalReports()",
    )
    # Replace activeMandirWorkspace reads with getter (not assignment — none in these funcs).
    block = re.sub(r"\bactiveMandirWorkspace\b", "getActiveMandirWorkspace()", block)

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in block and f"export async function {name}" not in block:
            raise SystemExit(f"export missing for {name}")

    text = "".join(lines)
    text = re.sub(
        r"(?ms)^// ═+\n// SECTION: MANDIR — dashboard home \+ workspace tabs\n.*?^// ═+\n\n+",
        "// Mandir dashboard home + tabs live in modules/workspaces/mandir-dashboard.js\n\n",
        text,
        count=1,
    )

    module = HEADER + block
    if not module.endswith("\n"):
        module += "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(module, encoding="utf-8", newline="\n")
    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(module.splitlines())} lines)")
    print(f"Updated {APP.relative_to(ROOT)} ({len(text.splitlines())} lines)")


if __name__ == "__main__":
    main()
