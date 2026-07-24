#!/usr/bin/env python3
"""Wire dashboard-preview-shell into app.js; bump cache v90→v91; update baseline."""
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
  initDashboardPreviewShell,
  renderRecentTenantsTable,
  renderPlatformRecentOnboardingTable,
  renderPlatformSubscriptionsTable,
  emptyPlatformDashboardPayload,
  renderPlatformDashboard,
  renderDashboardPreview,
} from "./modules/workspaces/dashboard-preview-shell.js";
'''

INIT = '''\
// Wire platform dashboard + preview shell (avoids import cycle with app.js)
initDashboardPreviewShell({
  escapeHtml,
  formatCurrency,
  formatCountMap,
  renderStatCards,
  renderActivity,
  renderPlatformTable,
  renderPendingApprovalsTable,
  getActivePlatformWorkspace: () => activePlatformWorkspace,
  getLastPlatformOwnerDashboard: () => lastPlatformOwnerDashboard,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getLastGruhaData: () => lastGruhaData,
  getLastBusinessDashboardStats: () => lastBusinessDashboardStats,
  activeOrgSelectorType,
  renderGruhaDashboard,
  renderBusinessWorkspace,
  renderSelectedOrgWorkspace,
  renderBusinessExecutiveDashboard,
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if 'from "./modules/workspaces/dashboard-preview-shell.js"' in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/business-workspace.js";\n'
    if marker not in app:
        raise SystemExit("business-workspace import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initBusinessWorkspace({")
    if idx < 0:
        raise SystemExit("initBusinessWorkspace not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v90",
        "app.js?v=mitrabooks-erp-v91",
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
    print(f"Wired dashboard-preview-shell; app.js={app_lines}; cache=v91")


if __name__ == "__main__":
    main()
