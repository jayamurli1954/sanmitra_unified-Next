#!/usr/bin/env python3
"""Wire executive-dashboard module into app.js; bump cache v77→v78; update baseline."""
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
  initExecutiveDashboard,
  renderMisPartyRows,
  renderMisKpiContractPanel,
  renderBusinessExecutiveDashboard,
} from "./modules/workspaces/executive-dashboard.js";
'''

INIT = '''\
// Wire executive dashboard (avoids import cycle with app.js)
initExecutiveDashboard({
  escapeHtml,
  formatCurrency,
  todayIsoDate,
  renderStatCards,
  hasTrustedSession,
  getLastAccountingDrilldown: () => lastAccountingDrilldown,
  getLastBusinessParties: () => lastBusinessParties,
  getLastBusinessAccounts: () => lastBusinessAccounts,
  getLastBusinessDashboardStats: () => lastBusinessDashboardStats,
  getLastBusinessMisKpis: () => lastBusinessMisKpis,
  getBusinessDashboardLoadInFlight: () => businessDashboardLoadInFlight,
  getBusinessMisLoadInFlight: () => businessMisLoadInFlight,
  loadBusinessDashboardStats,
  loadBusinessMisKpis,
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if 'from "./modules/workspaces/executive-dashboard.js"' in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/account-helpers.js";\n'
    if marker not in app:
        raise SystemExit("account-helpers import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initAccountHelpers({")
    if idx < 0:
        raise SystemExit("initAccountHelpers not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v77",
        "app.js?v=mitrabooks-erp-v78",
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
    print(f"Wired executive-dashboard; app.js={app_lines}; cache=v78")


if __name__ == "__main__":
    main()
