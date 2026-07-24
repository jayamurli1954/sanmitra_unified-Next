#!/usr/bin/env python3
"""Wire mandir-dashboard into app.js; bump cache v85→v86; update baseline."""
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
  initMandirDashboard,
  renderMandirDashboardHome,
  renderMandirDashboard,
  renderMandirSettings,
  renderMandirImplementationChecks,
  renderMandirPlatformOwnerShortcut,
} from "./modules/workspaces/mandir-dashboard.js";
'''

INIT = '''\
// Wire Mandir dashboard home + tabs (avoids import cycle with app.js)
initMandirDashboard({
  escapeHtml,
  formatCurrency,
  formatCountLabel,
  renderStatCards,
  renderActivity,
  isProductionShell,
  isMandirHost,
  renderMandirWorkspaceTabs,
  renderMandirOperationResult,
  renderMandirCreateForms,
  renderMandirListFilters,
  renderMandirDonationsTable,
  renderMandirSevaBookingsTable,
  mandirPublicPaymentPageUrl,
  renderMandirPublicPaymentFilters,
  renderMandirPublicPaymentsTable,
  renderMandirExceptionFilters,
  renderMandirExceptionsTable,
  renderMandirReceiptHistoryTable,
  renderMandirPanchang,
  renderMandirOperationalReports,
  renderMandirDevoteesView,
  renderAccountingDrilldownPanel,
  renderMandirTrialBalance,
  renderMandirFinancialReports,
  renderMandirExpensesTable,
  getActiveMandirWorkspace: () => activeMandirWorkspace,
  getMandirReportState: () => mandirReportState,
  getLastMandirPanchang: () => lastMandirPanchang,
  getLastMandirOperationalReports: () => lastMandirOperationalReports,
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if 'from "./modules/workspaces/mandir-dashboard.js"' in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/mandir-operational-reports.js";\n'
    if marker not in app:
        raise SystemExit("mandir-operational-reports import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initMandirOperationalReports({")
    if idx < 0:
        raise SystemExit("initMandirOperationalReports not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v85",
        "app.js?v=mitrabooks-erp-v86",
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
    print(f"Wired mandir-dashboard; app.js={app_lines}; cache=v86")


if __name__ == "__main__":
    main()
