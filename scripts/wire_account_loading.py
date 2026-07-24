#!/usr/bin/env python3
"""Wire account-loading module into app.js; bump cache v74→v75; update baseline."""
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
  initAccountLoading,
  lastBusinessAccounts,
  lastBusinessAccountsResult,
  lastBusinessDashboardStats,
  lastBusinessMisKpis,
  lastBusinessDataHealth,
  businessDashboardLoadInFlight,
  businessMisLoadInFlight,
  businessDataHealthLoadInFlight,
  setLastBusinessAccounts,
  loadBusinessAccounts,
  loadBusinessDashboardStats,
  loadBusinessMisKpis,
  loadBusinessDataHealth,
  filterBusinessAccountsByQuery,
} from "./modules/workspaces/account-loading.js";
'''

INIT = '''\
// Wire account/dashboard loaders (avoids import cycle with app.js)
initAccountLoading({
  setLoginStatus,
  statusDetailText,
  accountRowsFromPayload,
  loadModuleContextForAccounts,
  isBusinessModuleEnabled,
  refreshVoucherAccountSelects,
  updateVoucherAccountsStatus,
  hasTrustedSession,
  getCurrentExperience: () => currentExperience,
  getDashboardPreview: () => dashboardPreview,
  getExperienceConfig: () => experienceConfig,
  renderDashboardPreview: (config) => renderDashboardPreview(config),
  getApiOutput: () => apiOutput,
  getDefaultMitraBooksLoginEmail: () => DEFAULT_MITRABOOKS_LOGIN_EMAIL,
  businessAccountsForSelection,
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if "modules/workspaces/account-loading.js" in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/voucher-form.js";\n'
    if marker not in app:
        raise SystemExit("voucher-form import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    # voucher-form still needs lastBusinessAccounts from account-loading — ensure init order:
    # initAccountLoading before initVoucherForm so deps work; both only store refs.
    idx = app.find("initVoucherForm({")
    if idx < 0:
        raise SystemExit("initVoucherForm not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v74",
        "app.js?v=mitrabooks-erp-v75",
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
    print(f"Wired account-loading; app.js={app_lines}; cache=v75")


if __name__ == "__main__":
    main()
