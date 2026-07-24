#!/usr/bin/env python3
"""Wire business-list-tables into app.js; bump cache v78→v79; update baseline."""
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
  initBusinessListTables,
  renderBusinessPartiesTable,
  renderBusinessPartiesListFilters,
  renderBusinessVouchersTable,
  renderBusinessVouchersListFilters,
  renderVoucherApprovalQueuePanel,
} from "./modules/workspaces/business-list-tables.js";
'''

INIT = '''\
// Wire parties/vouchers list table renderers (avoids import cycle with app.js)
initBusinessListTables({
  escapeHtml,
  formatCurrency,
  getBusinessListState: () => businessListState,
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if 'from "./modules/workspaces/business-list-tables.js"' in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/executive-dashboard.js";\n'
    if marker not in app:
        raise SystemExit("executive-dashboard import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initExecutiveDashboard({")
    if idx < 0:
        raise SystemExit("initExecutiveDashboard not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v78",
        "app.js?v=mitrabooks-erp-v79",
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
    print(f"Wired business-list-tables; app.js={app_lines}; cache=v79")


if __name__ == "__main__":
    main()
