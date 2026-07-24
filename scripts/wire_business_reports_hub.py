#!/usr/bin/env python3
"""Wire business-reports-hub into app.js; bump cache v87→v88; update baseline."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
INDEX = ROOT / "frontend/mitrabooks-erp/index.html"
BASELINE = ROOT / "scripts/file_size_baseline.json"
FIN_REPORTS = ROOT / "frontend/mitrabooks-erp/modules/workspaces/financial-reports.js"

IMPORT = '''\
import {
  initBusinessReportsHub,
  reportResultPayload,
  refreshCurrentBusinessReport,
  rerenderBusinessReportsIfActive,
  reportExportToolbar,
  businessReportExports,
  downloadBusinessReport,
  downloadTallyXmlExport,
  printBusinessReport,
  downloadJsonObject,
  printBusinessDocumentDetail,
  downloadCreditNoteJson,
  downloadDebitNoteJson,
  printCreditNoteDetail,
  printDebitNoteDetail,
  renderBusinessReportsWorkspace,
  reportUnavailablePanel,
} from "./modules/workspaces/business-reports-hub.js";
'''

INIT = '''\
// Wire business reports hub (avoids import cycle with app.js)
initBusinessReportsHub({
  escapeHtml,
  todayIsoDate,
  renderJson,
  downloadApiFile,
  getApiOutput: () => apiOutput,
  getBusinessReportState: () => businessReportState,
  getBusinessReportTabs: () => BUSINESS_REPORT_TABS,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getDashboardPreview: () => dashboardPreview,
  renderBusinessWorkspace: () => renderBusinessWorkspace(),
  getGstReturnState: () => gstReturnState,
  getItcReversalAsOf: () => itcReversalAsOf,
  getTdsQuarter: () => tdsQuarter,
  getBankReconAccountId: () => bankReconAccountId,
  getStatementPartyId: () => statementPartyId,
  getStatementKind: () => statementKind,
  getStatementFromDate: () => statementFromDate,
  getStatementToDate: () => statementToDate,
  getLastBusinessParties: () => lastBusinessParties,
  getLastInventoryItems: () => lastInventoryItems,
  getCreditUi: () => creditUi,
  getDebitUi: () => debitUi,
  hasLoadedBusinessAccounts,
  loadBusinessAccounts,
  loadBusinessParties,
  loadBusinessTrialBalance,
  loadBusinessProfitLoss,
  loadBusinessBalanceSheet,
  loadBusinessReceivablesPayables,
  loadBusinessAging,
  loadUnallocatedPayments,
  loadAllocationReconciliation,
  loadBusinessAllLedgers,
  loadBusinessGeneralLedger,
  loadPeriodLocks,
  loadGstSettlementPreview,
  loadGstr1,
  loadCmp08,
  loadGstr4,
  loadGstr3b,
  loadItcReversalPreview,
  loadTdsRegister,
  loadBankReconciliation,
  loadBankCashBook,
  loadPartyStatement,
  loadFixedAssets,
  loadDimensions,
  loadDimensionReport,
  loadBranchConsolidatedReport,
  loadInventoryItems,
  loadInventoryPolicy,
  loadStockMovements,
  loadStockRegister,
  loadClosingStockEntries,
  reportDateControls,
  renderBusinessTrialBalance,
  renderBusinessProfitLoss,
  renderBusinessBalanceSheet,
  renderBusinessGeneralLedger,
  renderBusinessReceivablesPayables,
  renderBusinessAging,
  renderPaymentAllocation,
  renderPeriodLocksPanel,
  renderGstSettlementPanel,
  renderGstReturns,
  renderItcReversalPanel,
  renderTdsRegisterPanel,
  renderBankReconPanel,
  renderBankCashBookPanel,
  renderStatementsPanel,
  renderOpeningYearEndPanel,
  renderFixedAssetsPanel,
  renderDimensionsPanel,
  renderInventoryPanel,
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if 'from "./modules/workspaces/business-reports-hub.js"' in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/financial-reports.js";\n'
    if marker not in app:
        raise SystemExit("financial-reports import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    # Fix latent missing import used by refreshCurrentBusinessReport bank-recon branch.
    if "bankReconAccountId," not in app.split("from \"./modules/workspaces/bank-recon.js\";")[0][-400:]:
        old = "  loadBankReconciliation,\n  uploadBankStatementFile,"
        new = "  loadBankReconciliation,\n  bankReconAccountId,\n  uploadBankStatementFile,"
        if old not in app:
            raise SystemExit("bank-recon import block not found for bankReconAccountId")
        app = app.replace(old, new, 1)

    idx = app.find("initFinancialReports({")
    if idx < 0:
        raise SystemExit("initFinancialReports not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v87",
        "app.js?v=mitrabooks-erp-v88",
        html,
        count=1,
    )
    if n != 1:
        raise SystemExit(f"cache bump failed n={n}")
    INDEX.write_text(html2, encoding="utf-8", newline="\n")

    fin = FIN_REPORTS.read_text(encoding="utf-8")
    fin2 = fin.replace(
        "// Hub (refreshCurrentBusinessReport / renderBusinessReportsWorkspace) stays in app.js.",
        "// Hub (refreshCurrentBusinessReport / renderBusinessReportsWorkspace) lives in business-reports-hub.js.",
    )
    FIN_REPORTS.write_text(fin2, encoding="utf-8", newline="\n")

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    app_lines = len(APP.read_text(encoding="utf-8").splitlines())
    baseline["frontend/mitrabooks-erp/app.js"] = app_lines
    BASELINE.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Wired business-reports-hub; app.js={app_lines}; cache=v88")


if __name__ == "__main__":
    main()
