#!/usr/bin/env python3
"""Wire fixed-assets module into app.js; bump cache v51→v52; update baseline."""
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
  initFixedAssets,
  setFaFormOpen,
  faFormOpen,
  lastFixedAssets,
  loadFixedAssets,
  createFixedAssetFromForm,
  previewDepreciation,
  postDepreciationRun,
  disposeFixedAsset,
  renderFixedAssetsPanel,
} from "./modules/workspaces/fixed-assets.js";
'''

INIT = '''\
// Wire fixed assets + depreciation (avoids import cycle with app.js)
initFixedAssets({
  escapeHtml,
  formatCurrency,
  todayIsoDate,
  setLoginStatus,
  statusDetailText,
  reportUnavailablePanel,
  rerenderBusinessReportsIfActive,
  businessAccountsForSelection,
  bankAccountOptions,
  isBusinessAdmin,
  recentFinancialYears,
  currentFinancialYear,
  getApiOutput: () => apiOutput,
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if "modules/workspaces/fixed-assets.js" in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/dimensions.js";\n'
    if marker not in app:
        raise SystemExit("dimensions import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initDimensions({")
    if idx < 0:
        raise SystemExit("initDimensions not found")
    end = app.find("});\n", idx)
    if end < 0:
        raise SystemExit("initDimensions close not found")
    end += len("});\n")
    app = app[:end] + "\n" + INIT + app[end:]

    # Ensure setter uses setFaFormOpen if extract didn't catch it
    app = app.replace(
        "set faFormOpen(v) { faFormOpen = v; },",
        "set faFormOpen(v) { setFaFormOpen(v); },",
        1,
    )

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v51",
        "app.js?v=mitrabooks-erp-v52",
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
    print(f"Wired fixed-assets; cache v52; app.js={app_lines}")


if __name__ == "__main__":
    main()
