#!/usr/bin/env python3
"""Wire dimensions module into app.js; bump cache v50→v51; update baseline."""
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
  initDimensions,
  lastDimensions,
  loadDimensions,
  dimensionOptions,
  voucherDimensionPayload,
  createDimensionFromForm,
  deactivateDimension,
  loadDimensionReport,
  loadBranchConsolidatedReport,
  downloadDimensionReport,
  renderDimensionsPanel,
} from "./modules/workspaces/dimensions.js";
'''

INIT = '''\
// Wire accounting dimensions (avoids import cycle with app.js)
initDimensions({
  escapeHtml,
  formatCurrency,
  setLoginStatus,
  statusDetailText,
  reportUnavailablePanel,
  rerenderBusinessReportsIfActive,
  downloadApiFile,
  getApiOutput: () => apiOutput,
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if "modules/workspaces/dimensions.js" in app:
        print("Already wired")
        return

    marker = 'import { initShellUi } from "./modules/shell-ui.js";\n'
    if marker not in app:
        raise SystemExit("shell-ui import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    # Insert init after initShellUi block or after initDebitNotes
    if "initShellUi({" in app:
        # find closing of initShellUi
        idx = app.find("// Wire shell UI")
        if idx < 0:
            idx = app.find("initShellUi({")
        end = app.find("});\n", app.find("initShellUi({", idx))
        if end < 0:
            raise SystemExit("initShellUi close not found")
        end += len("});\n")
        app = app[:end] + "\n" + INIT + app[end:]
    else:
        raise SystemExit("initShellUi not found")

    # getLastDimensions already uses () => lastDimensions — live import binding works
    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v50",
        "app.js?v=mitrabooks-erp-v51",
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

    print(f"Wired dimensions; cache v51; app.js={app_lines}")


if __name__ == "__main__":
    main()
