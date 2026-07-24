#!/usr/bin/env python3
"""Wire voucher-form module into app.js; bump cache v73→v74; update baseline."""
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
  initVoucherForm,
  voucherLineCounter,
  setVoucherLineCounter,
  syncVoucherAccountFromText,
  renderVoucherLineItem,
  updateVoucherBalance,
  updateVoucherBalanceState,
  addVoucherLine,
  removeVoucherLine,
  clearVoucherForm,
} from "./modules/workspaces/voucher-form.js";
'''

INIT = '''\
// Wire voucher form helpers (avoids import cycle with app.js)
initVoucherForm({
  escapeHtml,
  formatCurrency,
  normalizeBusinessAccount,
  businessAccountLabel,
  renderAccountSelectorComponent,
  refreshVoucherAccountDatalist,
  updateVoucherAccountsStatus,
  populateVoucherAccountSelect,
  getLastBusinessAccounts: () => lastBusinessAccounts,
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if "modules/workspaces/voucher-form.js" in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/accounting-drilldown.js";\n'
    if marker not in app:
        raise SystemExit("accounting-drilldown import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initAccountingDrilldown({")
    if idx < 0:
        raise SystemExit("initAccountingDrilldown not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v73",
        "app.js?v=mitrabooks-erp-v74",
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
    print(f"Wired voucher-form; app.js={app_lines}; cache=v74")


if __name__ == "__main__":
    main()
