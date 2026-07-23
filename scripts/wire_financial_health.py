#!/usr/bin/env python3
"""Wire financial-health module into app.js; bump cache v71→v72; update baseline."""
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
  initFinancialHealth,
  lastFinancialHealth,
  financialHealthLoadInFlight,
  setLastFinancialHealth,
  resetFinancialHealthState,
  renderFinancialHealthWorkspace,
  loadFinancialHealth,
} from "./modules/workspaces/financial-health.js";
'''

INIT = '''\
// Wire Financial Health (avoids import cycle with app.js)
initFinancialHealth({
  escapeHtml,
  formatCurrency,
  setLoginStatus,
  getApiOutput: () => apiOutput,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getDashboardPreview: () => dashboardPreview,
  renderBusinessWorkspace: () => renderBusinessWorkspace(),
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if "modules/workspaces/financial-health.js" in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/ca-practice.js";\n'
    if marker not in app:
        raise SystemExit("ca-practice import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initCaPractice({")
    if idx < 0:
        raise SystemExit("initCaPractice not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v71",
        "app.js?v=mitrabooks-erp-v72",
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
    print(f"Wired financial-health; app.js={app_lines}; cache=v72")


if __name__ == "__main__":
    main()
