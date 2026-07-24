#!/usr/bin/env python3
"""Wire account-helpers module into app.js; bump cache v76→v77; update baseline."""
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
  initAccountHelpers,
  normalizeBusinessAccount,
  businessAccountLabel,
  businessAccountsForSelection,
  hasLoadedBusinessAccounts,
  findBusinessAccountById,
  accountIdForVoucherPayload,
  populateVoucherAccountSelect,
  populateAccountPickerSelect,
  refreshVoucherAccountDatalist,
  updateVoucherAccountsStatus,
  refreshVoucherAccountSelects,
  accountRowsFromPayload,
  normalizedAccountRows,
  hasBusinessAccount,
  countPartiesMissingGstin,
  dataHealthItem,
  dataHealthAction,
  renderBusinessDataHealthIssueList,
  renderBusinessDataHealthActions,
  getBusinessHealthState,
  renderBusinessDataHealthPanel,
  updateHealthWidget,
  refreshBooksHealthWidget,
  initializeHealthWidget,
} from "./modules/workspaces/account-helpers.js";
'''

INIT = '''\
// Wire account helpers + data health + books health (avoids import cycle with app.js)
initAccountHelpers({
  escapeHtml,
  getLastBusinessAccounts: () => lastBusinessAccounts,
  getLastBusinessAccountsResult: () => lastBusinessAccountsResult,
  getLastBusinessParties: () => lastBusinessParties,
  getLastBusinessPartiesResult: () => lastBusinessPartiesResult,
  getLastModuleContext: () => lastModuleContext,
  getLastAccountingDrilldown: () => lastAccountingDrilldown,
  getLastBusinessDataHealth: () => lastBusinessDataHealth,
  getBusinessDataHealthLoadInFlight: () => businessDataHealthLoadInFlight,
  loadBusinessDataHealth,
  hasTrustedSession,
  enabledModuleKeys,
  isBusinessTenantContext,
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if 'from "./modules/workspaces/account-helpers.js"' in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/account-selector.js";\n'
    if marker not in app:
        raise SystemExit("account-selector import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initAccountSelector({")
    if idx < 0:
        raise SystemExit("initAccountSelector not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    # Drop orphan incomplete JSDoc left above books-health note
    app2, n = re.subn(
        r"(?ms)^/\*\*\n \* Update health widget with data\n \* @param \{number\} percentage - Health percentage \(0-100\)\n \* @param \{string\} status - Status message\n \*/\n\n",
        "",
        app,
        count=1,
    )
    if n != 1:
        print(f"warn: orphan JSDoc cleanup n={n}")
    else:
        app = app2

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v76",
        "app.js?v=mitrabooks-erp-v77",
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
    print(f"Wired account-helpers; app.js={app_lines}; cache=v77")


if __name__ == "__main__":
    main()
