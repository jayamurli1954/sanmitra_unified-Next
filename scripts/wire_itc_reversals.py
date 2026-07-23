#!/usr/bin/env python3
"""Wire ITC reversals module into app.js; bump cache v57→v58; update baseline."""
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
  initItcReversals,
  itcReversalAsOf,
  loadItcReversalPreview,
  previewItcReversalsFromInput,
  reverseItcForBill,
  reclaimItcForBill,
  markBillPaidFull,
  renderItcReversalPanel,
} from "./modules/workspaces/itc-reversals.js";
'''

INIT = '''\
// Wire ITC reversals / reclaim (avoids import cycle with app.js)
initItcReversals({
  escapeHtml,
  formatCurrency,
  setLoginStatus,
  statusDetailText,
  rerenderBusinessReportsIfActive,
  isBusinessAdmin,
  todayIsoDate,
  getApiOutput: () => apiOutput,
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if "modules/workspaces/itc-reversals.js" in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/tds.js";\n'
    if marker not in app:
        raise SystemExit("tds import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initTds({")
    if idx < 0:
        raise SystemExit("initTds not found")
    end = app.find("});\n", idx)
    if end < 0:
        raise SystemExit("initTds close not found")
    end += len("});\n")
    app = app[:end] + "\n" + INIT + app[end:]
    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v57",
        "app.js?v=mitrabooks-erp-v58",
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
    print(f"Wired itc-reversals; cache v58; app.js={app_lines}")


if __name__ == "__main__":
    main()
