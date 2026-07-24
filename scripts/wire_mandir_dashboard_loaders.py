#!/usr/bin/env python3
"""Wire mandir-dashboard-loaders into app.js; bump cache v94→v95; update baseline."""
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
  initMandirDashboardLoaders,
  showMandirSplash,
  hideMandirSplash,
  loadMandirDashboard,
  openMandirTrialBalanceLedger,
} from "./modules/workspaces/mandir-dashboard-loaders.js";
'''

INIT = '''\
// Wire Mandir dashboard loaders + splash (avoids import cycle with app.js)
initMandirDashboardLoaders({
  mandirSplash,
  mandirSplashVideo,
  mandirSplashImage,
  brandSplashCopy,
  dashboardPreview,
  apiOutput,
  apiRequest,
  renderJson,
  buildQueryString,
  todayIsoDate,
  mandirListPath,
  mandirPublicPaymentsPath,
  mandirPublicPaymentExceptionsPath,
  loadAccountingDrilldownResult,
  getCurrentExperience: () => currentExperience,
  getLastMandirPaymentAccounts: () => lastMandirPaymentAccounts,
  setLastMandirPaymentAccounts: (value) => { lastMandirPaymentAccounts = value; },
  getLastMandirAccounts: () => lastMandirAccounts,
  setLastMandirAccounts: (value) => { lastMandirAccounts = value; },
  getLastMandirPanchang: () => lastMandirPanchang,
  setLastMandirPanchang: (value) => { lastMandirPanchang = value; },
  getLastMandirModuleConfig: () => lastMandirModuleConfig,
  setLastMandirModuleConfig: (value) => { lastMandirModuleConfig = value; },
  getLastMandirComplianceConfig: () => lastMandirComplianceConfig,
  setLastMandirComplianceConfig: (value) => { lastMandirComplianceConfig = value; },
  getLastMandirOperationalReports: () => lastMandirOperationalReports,
  setLastMandirOperationalReports: (value) => { lastMandirOperationalReports = value; },
  getLastMandirReceipt: () => lastMandirReceipt,
  getLastMandirFormResult: () => lastMandirFormResult,
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if 'from "./modules/workspaces/mandir-dashboard-loaders.js"' in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/mandir-dashboard.js";\n'
    if marker not in app:
        raise SystemExit("mandir-dashboard import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initMandirDashboard({")
    if idx < 0:
        raise SystemExit("initMandirDashboard not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v94",
        "app.js?v=mitrabooks-erp-v95",
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
    print(f"Wired mandir-dashboard-loaders; app.js={app_lines}; cache=v95")


if __name__ == "__main__":
    main()
