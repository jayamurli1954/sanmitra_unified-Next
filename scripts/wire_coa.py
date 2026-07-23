#!/usr/bin/env python3
"""Wire COA module into app.js; bump cache v68→v69; update baseline."""
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
  initCoa,
  coaTypeFilter,
  setCoaTypeFilter,
  renderBusinessCoaWorkspace,
  coaHandleAddSubmit,
  coaHandleSaveName,
  coaEnterEditMode,
  coaExitEditMode,
} from "./modules/workspaces/coa.js";
'''

INIT = '''\
// Wire Chart of Accounts workspace (avoids import cycle with app.js)
initCoa({
  escapeHtml,
  statusDetailText,
  getLastBusinessAccounts: () => lastBusinessAccounts,
  loadBusinessAccounts,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getDashboardPreview: () => dashboardPreview,
  renderBusinessWorkspace: () => renderBusinessWorkspace(),
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if "modules/workspaces/coa.js" in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/parties.js";\n'
    if marker not in app:
        raise SystemExit("parties import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    # events deps: coaTypeFilter setter
    old = "get coaTypeFilter() { return coaTypeFilter; },\n  set coaTypeFilter(v) { coaTypeFilter = v; },"
    new = "get coaTypeFilter() { return coaTypeFilter; },\n  set coaTypeFilter(v) { setCoaTypeFilter(v); },"
    if old not in app:
        raise SystemExit("coaTypeFilter events binding not found")
    app = app.replace(old, new, 1)

    idx = app.find("initParties({")
    if idx < 0:
        raise SystemExit("initParties not found")
    app = app[:idx] + INIT + "\n" + app[idx:]

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v68",
        "app.js?v=mitrabooks-erp-v69",
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
    print(f"Wired coa; cache v69; app.js baseline={app_lines}")


if __name__ == "__main__":
    main()
