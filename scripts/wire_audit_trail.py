#!/usr/bin/env python3
"""Wire audit-trail module into app.js; bump cache v61→v62; update baseline."""
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
  initAuditTrail,
  lastAuditEvents,
  loadAuditEvents,
  renderAuditEventsTable,
  renderAuditListFilters,
  openAuditEventDetailDialog,
  applyAuditFilters,
  resetAuditFilters,
  pageAuditList,
} from "./modules/workspaces/audit-trail.js";
'''

INIT = '''\
// Wire audit trail (avoids import cycle with app.js)
initAuditTrail({
  escapeHtml,
  setLoginStatus,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getDashboardPreview: () => dashboardPreview,
  renderBusinessWorkspace: () => renderBusinessWorkspace(),
  getApiOutput: () => apiOutput,
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if "modules/workspaces/audit-trail.js" in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/payment-allocation.js";\n'
    if marker not in app:
        raise SystemExit("payment-allocation import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initPaymentAllocation({")
    if idx < 0:
        raise SystemExit("initPaymentAllocation not found")
    end = app.find("});\n", idx)
    if end < 0:
        raise SystemExit("initPaymentAllocation close not found")
    end += len("});\n")
    app = app[:end] + "\n" + INIT + app[end:]
    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v61",
        "app.js?v=mitrabooks-erp-v62",
        html,
        count=1,
    )
    if n != 1:
        raise SystemExit(f"cache bump failed n={n}")
    INDEX.write_text(html2, encoding="utf-8", newline="\n")

    app_lines = sum(1 for _ in APP.open(encoding="utf-8"))
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    baseline["frontend/mitrabooks-erp/app.js"] = app_lines
    BASELINE.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Wired audit-trail; cache v62; app.js={app_lines}")


if __name__ == "__main__":
    main()
