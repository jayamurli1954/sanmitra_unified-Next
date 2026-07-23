#!/usr/bin/env python3
"""Wire statements module into app.js; bump cache v54→v55; update baseline."""
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
  initStatements,
  lastPartyStatement,
  statementPartyId,
  statementKind,
  statementFromDate,
  statementToDate,
  loadPartyStatement,
  recordDunningSent,
  copyDunningLetter,
  renderStatementsPanel,
} from "./modules/workspaces/statements.js";
'''

INIT = '''\
// Wire customer statements + dunning (avoids import cycle with app.js)
initStatements({
  escapeHtml,
  formatCurrency,
  setLoginStatus,
  statusDetailText,
  reportUnavailablePanel,
  rerenderBusinessReportsIfActive,
  getLastBusinessParties: () => lastBusinessParties,
  getApiOutput: () => apiOutput,
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if "modules/workspaces/statements.js" in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/bank-recon.js";\n'
    if marker not in app:
        raise SystemExit("bank-recon import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initBankRecon({")
    if idx < 0:
        raise SystemExit("initBankRecon not found")
    end = app.find("});\n", idx)
    if end < 0:
        raise SystemExit("initBankRecon close not found")
    end += len("});\n")
    app = app[:end] + "\n" + INIT + app[end:]
    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v54",
        "app.js?v=mitrabooks-erp-v55",
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
    print(f"Wired statements; cache v55; app.js={app_lines}")


if __name__ == "__main__":
    main()
