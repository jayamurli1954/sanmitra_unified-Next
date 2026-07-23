#!/usr/bin/env python3
"""Wire parties module into app.js; bump cache v67→v68; update baseline."""
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
  initParties,
  lastBusinessParties,
  lastBusinessPartiesResult,
  setLastBusinessParties,
  setLastBusinessPartiesResult,
  clearPartiesState,
  loadBusinessParties,
  createBusinessParty,
  updateBusinessParty,
  deactivateBusinessParty,
  openBusinessCreatePartyDialog,
  openBusinessEditPartyDialog,
} from "./modules/workspaces/parties.js";
'''

INIT = '''\
// Wire parties CRUD (avoids import cycle with app.js)
initParties({
  setLoginStatus,
  statusDetailText,
  getBusinessListState: () => businessListState,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getDashboardPreview: () => dashboardPreview,
  renderBusinessWorkspace: () => renderBusinessWorkspace(),
  getApiOutput: () => apiOutput,
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if "modules/workspaces/parties.js" in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/voucher-create.js";\n'
    if marker not in app:
        raise SystemExit("voucher-create import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initVoucherCreate({")
    if idx < 0:
        raise SystemExit("initVoucherCreate not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v67",
        "app.js?v=mitrabooks-erp-v68",
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
    print(f"Wired parties; cache v68; app.js baseline={app_lines}")


if __name__ == "__main__":
    main()
