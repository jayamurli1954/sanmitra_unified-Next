#!/usr/bin/env python3
"""Wire bank-recon module into app.js; bump cache v53→v54; update baseline."""
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
  initBankRecon,
  setBankCashBookType,
  bankCashBookType,
  bankAccountOptions,
  loadBankCashBook,
  loadBankReconciliation,
  uploadBankStatementFile,
  confirmBankReconMatch,
  reverseBankReconMatch,
  postBankReconStatementVoucher,
  renderBankCashBookPanel,
  renderBankReconPanel,
} from "./modules/workspaces/bank-recon.js";
'''

INIT = '''\
// Wire bank reconciliation + cash book (avoids import cycle with app.js)
initBankRecon({
  escapeHtml,
  formatCurrency,
  setLoginStatus,
  statusDetailText,
  reportUnavailablePanel,
  rerenderBusinessReportsIfActive,
  businessAccountsForSelection,
  renderStatCards,
  getBusinessReportState: () => businessReportState,
  getApiOutput: () => apiOutput,
});
'''


def main() -> None:
    app = APP.read_text(encoding="utf-8")
    if "modules/workspaces/bank-recon.js" in app:
        print("Already wired")
        return

    marker = 'from "./modules/workspaces/inventory.js";\n'
    if marker not in app:
        raise SystemExit("inventory import marker not found")
    app = app.replace(marker, marker + "\n" + IMPORT, 1)

    idx = app.find("initInventory({")
    if idx < 0:
        raise SystemExit("initInventory not found")
    end = app.find("});\n", idx)
    if end < 0:
        raise SystemExit("initInventory close not found")
    end += len("});\n")
    app = app[:end] + "\n" + INIT + app[end:]

    # Safety: ensure setter rewrite happened
    app = app.replace(
        "if (bookType && bookType.value) bankCashBookType = bookType.value;",
        "if (bookType && bookType.value) setBankCashBookType(bookType.value);",
        1,
    )

    APP.write_text(app, encoding="utf-8", newline="\n")

    html = INDEX.read_text(encoding="utf-8")
    html2, n = re.subn(
        r"app\.js\?v=mitrabooks-erp-v53",
        "app.js?v=mitrabooks-erp-v54",
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
    print(f"Wired bank-recon; cache v54; app.js={app_lines}")


if __name__ == "__main__":
    main()
