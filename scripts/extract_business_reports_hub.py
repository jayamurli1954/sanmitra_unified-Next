#!/usr/bin/env python3
"""Extract business financial-reports hub from app.js (Phase 3 seam 51)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/business-reports-hub.js"

HEADER = '''\
// ====================================================================
// SECTION: BUSINESS REPORTS HUB — workspace + export/print framework
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initBusinessReportsHub(...).
// Tab-specific loaders/renderers remain in financial-reports.js and sibling modules.
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

export function initBusinessReportsHub(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initBusinessReportsHub() must be called before using business reports hub helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function todayIsoDate() { return requireDeps().todayIsoDate(); }
function renderJson(...args) { return requireDeps().renderJson(...args); }
function downloadApiFile(...args) { return requireDeps().downloadApiFile(...args); }
function getApiOutput() { return requireDeps().getApiOutput(); }
function getBusinessReportState() { return requireDeps().getBusinessReportState(); }
function getBusinessReportTabs() { return requireDeps().getBusinessReportTabs(); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function renderBusinessWorkspace() { return requireDeps().renderBusinessWorkspace(); }
function getGstReturnState() { return requireDeps().getGstReturnState(); }
function getItcReversalAsOf() { return requireDeps().getItcReversalAsOf(); }
function getTdsQuarter() { return requireDeps().getTdsQuarter(); }
function getBankReconAccountId() { return requireDeps().getBankReconAccountId(); }
function getStatementPartyId() { return requireDeps().getStatementPartyId(); }
function getStatementKind() { return requireDeps().getStatementKind(); }
function getStatementFromDate() { return requireDeps().getStatementFromDate(); }
function getStatementToDate() { return requireDeps().getStatementToDate(); }
function getLastBusinessParties() { return requireDeps().getLastBusinessParties(); }
function getLastInventoryItems() { return requireDeps().getLastInventoryItems(); }
function getCreditUi() { return requireDeps().getCreditUi(); }
function getDebitUi() { return requireDeps().getDebitUi(); }
function hasLoadedBusinessAccounts() { return requireDeps().hasLoadedBusinessAccounts(); }
function loadBusinessAccounts(...args) { return requireDeps().loadBusinessAccounts(...args); }
function loadBusinessParties(...args) { return requireDeps().loadBusinessParties(...args); }
function loadBusinessTrialBalance(...args) { return requireDeps().loadBusinessTrialBalance(...args); }
function loadBusinessProfitLoss(...args) { return requireDeps().loadBusinessProfitLoss(...args); }
function loadBusinessBalanceSheet(...args) { return requireDeps().loadBusinessBalanceSheet(...args); }
function loadBusinessReceivablesPayables(...args) { return requireDeps().loadBusinessReceivablesPayables(...args); }
function loadBusinessAging(...args) { return requireDeps().loadBusinessAging(...args); }
function loadUnallocatedPayments(...args) { return requireDeps().loadUnallocatedPayments(...args); }
function loadAllocationReconciliation(...args) { return requireDeps().loadAllocationReconciliation(...args); }
function loadBusinessAllLedgers(...args) { return requireDeps().loadBusinessAllLedgers(...args); }
function loadBusinessGeneralLedger(...args) { return requireDeps().loadBusinessGeneralLedger(...args); }
function loadPeriodLocks(...args) { return requireDeps().loadPeriodLocks(...args); }
function loadGstSettlementPreview(...args) { return requireDeps().loadGstSettlementPreview(...args); }
function loadGstr1(...args) { return requireDeps().loadGstr1(...args); }
function loadCmp08(...args) { return requireDeps().loadCmp08(...args); }
function loadGstr4(...args) { return requireDeps().loadGstr4(...args); }
function loadGstr3b(...args) { return requireDeps().loadGstr3b(...args); }
function loadItcReversalPreview(...args) { return requireDeps().loadItcReversalPreview(...args); }
function loadTdsRegister(...args) { return requireDeps().loadTdsRegister(...args); }
function loadBankReconciliation(...args) { return requireDeps().loadBankReconciliation(...args); }
function loadBankCashBook(...args) { return requireDeps().loadBankCashBook(...args); }
function loadPartyStatement(...args) { return requireDeps().loadPartyStatement(...args); }
function loadFixedAssets(...args) { return requireDeps().loadFixedAssets(...args); }
function loadDimensions(...args) { return requireDeps().loadDimensions(...args); }
function loadDimensionReport(...args) { return requireDeps().loadDimensionReport(...args); }
function loadBranchConsolidatedReport(...args) { return requireDeps().loadBranchConsolidatedReport(...args); }
function loadInventoryItems(...args) { return requireDeps().loadInventoryItems(...args); }
function loadInventoryPolicy(...args) { return requireDeps().loadInventoryPolicy(...args); }
function loadStockMovements(...args) { return requireDeps().loadStockMovements(...args); }
function loadStockRegister(...args) { return requireDeps().loadStockRegister(...args); }
function loadClosingStockEntries(...args) { return requireDeps().loadClosingStockEntries(...args); }
function reportDateControls(...args) { return requireDeps().reportDateControls(...args); }
function renderBusinessTrialBalance(...args) { return requireDeps().renderBusinessTrialBalance(...args); }
function renderBusinessProfitLoss(...args) { return requireDeps().renderBusinessProfitLoss(...args); }
function renderBusinessBalanceSheet(...args) { return requireDeps().renderBusinessBalanceSheet(...args); }
function renderBusinessGeneralLedger(...args) { return requireDeps().renderBusinessGeneralLedger(...args); }
function renderBusinessReceivablesPayables(...args) { return requireDeps().renderBusinessReceivablesPayables(...args); }
function renderBusinessAging(...args) { return requireDeps().renderBusinessAging(...args); }
function renderPaymentAllocation(...args) { return requireDeps().renderPaymentAllocation(...args); }
function renderPeriodLocksPanel(...args) { return requireDeps().renderPeriodLocksPanel(...args); }
function renderGstSettlementPanel(...args) { return requireDeps().renderGstSettlementPanel(...args); }
function renderGstReturns(...args) { return requireDeps().renderGstReturns(...args); }
function renderItcReversalPanel(...args) { return requireDeps().renderItcReversalPanel(...args); }
function renderTdsRegisterPanel(...args) { return requireDeps().renderTdsRegisterPanel(...args); }
function renderBankReconPanel(...args) { return requireDeps().renderBankReconPanel(...args); }
function renderBankCashBookPanel(...args) { return requireDeps().renderBankCashBookPanel(...args); }
function renderStatementsPanel(...args) { return requireDeps().renderStatementsPanel(...args); }
function renderOpeningYearEndPanel(...args) { return requireDeps().renderOpeningYearEndPanel(...args); }
function renderFixedAssetsPanel(...args) { return requireDeps().renderFixedAssetsPanel(...args); }
function renderDimensionsPanel(...args) { return requireDeps().renderDimensionsPanel(...args); }
function renderInventoryPanel(...args) { return requireDeps().renderInventoryPanel(...args); }

'''

EXPORT_FUNCS = [
    "reportResultPayload",
    "refreshCurrentBusinessReport",
    "rerenderBusinessReportsIfActive",
    "reportExportToolbar",
    "businessReportExports",
    "downloadBusinessReport",
    "downloadTallyXmlExport",
    "printBusinessReport",
    "downloadJsonObject",
    "printBusinessDocumentDetail",
    "downloadCreditNoteJson",
    "downloadDebitNoteJson",
    "printCreditNoteDetail",
    "printDebitNoteDetail",
    "renderBusinessReportsWorkspace",
    "reportUnavailablePanel",
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


def rewrite_block(block: str) -> str:
    block = block.replace("businessReportState", "getBusinessReportState()")
    block = block.replace("BUSINESS_REPORT_TABS", "getBusinessReportTabs()")
    block = block.replace("currentExperience", "getCurrentExperience()")
    block = block.replace("activeBusinessWorkspace", "getActiveBusinessWorkspace()")
    block = block.replace("dashboardPreview.innerHTML", "getDashboardPreview().innerHTML")
    block = block.replace("gstReturnState", "getGstReturnState()")
    block = block.replace("itcReversalAsOf", "getItcReversalAsOf()")
    block = block.replace("tdsQuarter", "getTdsQuarter()")
    block = block.replace("bankReconAccountId", "getBankReconAccountId()")
    block = block.replace("statementPartyId", "getStatementPartyId()")
    block = block.replace("statementKind", "getStatementKind()")
    block = block.replace("statementFromDate", "getStatementFromDate()")
    block = block.replace("statementToDate", "getStatementToDate()")
    block = block.replace("lastBusinessParties", "getLastBusinessParties()")
    block = block.replace("lastInventoryItems", "getLastInventoryItems()")
    block = block.replace("creditUi", "getCreditUi()")
    block = block.replace("debitUi", "getDebitUi()")
    block = block.replace("renderJson(apiOutput,", "renderJson(getApiOutput(),")
    # Avoid double-wrapping getters already rewritten
    block = block.replace("getGet", "get")  # safety noop if any
    # Fix accidental double calls from chained replaces on already-wrapped names
    for name in (
        "BusinessReportState",
        "BusinessReportTabs",
        "CurrentExperience",
        "ActiveBusinessWorkspace",
        "DashboardPreview",
        "GstReturnState",
        "ItcReversalAsOf",
        "TdsQuarter",
        "BankReconAccountId",
        "StatementPartyId",
        "StatementKind",
        "StatementFromDate",
        "StatementToDate",
        "LastBusinessParties",
        "LastInventoryItems",
        "CreditUi",
        "DebitUi",
        "ApiOutput",
    ):
        block = block.replace(f"get{name}()()", f"get{name}()")
    return block


def main() -> None:
    if OUT.exists() and "export function refreshCurrentBusinessReport" in OUT.read_text(encoding="utf-8"):
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
    block = rewrite_block(block)

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in block and f"export async function {name}" not in block:
            raise SystemExit(f"export missing for {name}")

    text = "".join(lines)
    text = re.sub(
        r"(?ms)^// ═+\n// SECTION: FINANCIAL REPORTS — workspace renderer \+ report framework\n.*?^// ═+\n\n+",
        "// Business reports hub lives in modules/workspaces/business-reports-hub.js\n\n",
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
