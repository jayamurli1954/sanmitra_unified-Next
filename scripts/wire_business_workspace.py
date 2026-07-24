#!/usr/bin/env python3
"""Wire business-workspace into app.js; bump cache v89→v90; update baseline."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
INDEX = ROOT / "frontend/mitrabooks-erp/index.html"
BASELINE = ROOT / "scripts/file_size_baseline.json"

IMPORT = '''\
import {
  initBusinessWorkspace,
  renderBusinessWorkspace,
  setBusinessWorkspace,
  syncBusinessNavActiveState,
} from "./modules/workspaces/business-workspace.js";
'''

INIT = '''\
// Wire business workspace dispatcher + router (avoids import cycle with app.js)
initBusinessWorkspace({
  dashboardPreview,
  nav,
  topbarCurrent,
  escapeHtml,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  setActiveBusinessWorkspace: (value) => { activeBusinessWorkspace = value; },
  getCurrentExperience: () => currentExperience,
  getSelectedOrgType: () => selectedOrgType,
  setSelectedOrgType: (value) => { selectedOrgType = value; },
  getOrgSelectorMeta: () => orgSelectorMeta,
  getExperienceConfig: () => experienceConfig,
  getBusinessReportState: () => businessReportState,
  getLastBusinessParties: () => lastBusinessParties,
  getLastBusinessVouchers: () => lastBusinessVouchers,
  getLastBusinessAccounts: () => lastBusinessAccounts,
  getLastVoucherApprovalQueue: () => lastVoucherApprovalQueue,
  getLastAuditEvents: () => lastAuditEvents,
  getSalesUi: () => salesUi,
  getPurchaseUi: () => purchaseUi,
  getCreditUi: () => creditUi,
  getDebitUi: () => debitUi,
  getHrUi: () => hrUi,
  activeOrgSelectorType,
  updateTrustedContextUi,
  setActiveSettingsDetailId,
  hasTrustedSession,
  updatePageHeader,
  renderMitraBooksSettingsWorkspace,
  renderCaPracticePortalWorkspace,
  renderBusinessPartiesListFilters,
  renderBusinessPartiesTable,
  renderVoucherApprovalQueuePanel,
  renderBusinessVouchersListFilters,
  renderBusinessVouchersTable,
  renderAuditListFilters,
  renderAuditEventsTable,
  renderAccountingDrilldownPanel,
  renderBusinessReportsWorkspace,
  renderBusinessSalesWorkspace,
  renderBusinessPurchaseWorkspace,
  renderBusinessCreditNoteWorkspace,
  renderBusinessDebitNoteWorkspace,
  renderBusinessCoaWorkspace,
  renderFinancialHealthWorkspace,
  renderHrWorkspace,
  renderManufacturingWorkspace,
  renderDashboardPreview,
  loadBusinessDashboardStats,
  loadBusinessParties,
  loadBusinessAccounts,
  loadBusinessVouchers,
  loadVoucherApprovalQueue,
  loadAuditEvents,
  refreshCurrentAccountingDrilldown,
  refreshCurrentBusinessReport,
  loadInvoiceSettings,
  loadBusinessInvoices,
  loadBusinessAdminSettings,
  loadBusinessPartiesForHealth,
  loadAccountingDrilldownResult,
  loadBusinessDataHealth,
  loadBusinessBills,
  loadCreditNotes,
  loadDebitNotes,
  setCoaTypeFilter,
  resetCaPracticeWorkspaceState,
  isBusinessAdmin,
  loadCaAccessUsers,
  loadCaClients,
  loadCaPracticeDocuments,
  loadHrWorkspace,
  setMfgTab,
  setMfgError,
  loadMfgWorkspace,
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if 'from "./modules/workspaces/business-workspace.js"' in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/auth-session.js";\n'
    if marker not in app:
        raise SystemExit("auth-session import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initAuthSession({")
    if idx < 0:
        raise SystemExit("initAuthSession not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v89",
        "app.js?v=mitrabooks-erp-v90",
        html,
        count=1,
    )
    if n != 1:
        raise SystemExit(f"cache bump failed n={n}")
    INDEX.write_text(html2, encoding="utf-8", newline="\n")

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    app_lines = len(APP.read_text(encoding="utf-8").splitlines())
    baseline["frontend/mitrabooks-erp/app.js"] = app_lines
    BASELINE.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Wired business-workspace; app.js={app_lines}; cache=v90")


if __name__ == "__main__":
    main()
