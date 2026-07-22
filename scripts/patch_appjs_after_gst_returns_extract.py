"""Patch app.js after GST returns extraction."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "mitrabooks-erp" / "app.js"

IMPORT_BLOCK = '''import {
  initGstReturns,
  gstReturnState,
  loadGstSettlementPreview,
  previewGstSettlementFromInput,
  postGstSettlement,
  renderGstSettlementPanel,
  loadGstr3b,
  previewGstr3bFromInput,
  downloadGstr3bJson,
  renderGstReturns,
  reconcileGstr2b,
  loadGstr4,
  previewGstr4FromInput,
  downloadGstr4Json,
  loadCmp08,
  previewCmp08FromInput,
  downloadCmp08Json,
  postCmp08Liability,
  loadGstr1,
  previewGstr1FromInput,
  downloadGstr1Json,
} from "./modules/workspaces/gst-returns.js";
'''

INIT_BLOCK = '''
// Wire GST returns cluster (avoids import cycle with app.js)
initGstReturns({
  escapeHtml,
  formatCurrency,
  setLoginStatus,
  statusDetailText,
  rerenderBusinessReportsIfActive,
  isBusinessAdmin,
  reportUnavailablePanel,
  todayIsoDate,
  currentFinancialYear,
  currentFyQuarter,
  recentFinancialYears,
  recentFyQuarters,
  getApiOutput: () => apiOutput,
});
'''

STATE_LINES = {
    "let lastGstSettlement = null;\n",
    "let gstSettlementPeriod = todayIsoDate().slice(0, 7);\n",
    "let lastGstr3b = null;\n",
    "let lastGstr1 = null;\n",
    "let lastCmp08 = null;\n",
    "let lastGstr4 = null;\n",
    "let lastGstr2bRecon = null;\n",
    'let gstReturnType = "gstr3b";   // "gstr3b" | "gstr1" | "cmp08" | "gstr4" | "gstr2b"\n',
    "let gstr3bPeriod = todayIsoDate().slice(0, 7);\n",
    "let cmp08Quarter = currentFyQuarter();\n",
    "let gstr4Fy = currentFinancialYear();\n",
}

REPLACEMENTS = [
    ("lastGstr2bRecon", "gstReturnState.lastGstr2bRecon"),
    ("lastGstSettlement", "gstReturnState.lastGstSettlement"),
    ("gstSettlementPeriod", "gstReturnState.gstSettlementPeriod"),
    ("lastGstr3b", "gstReturnState.lastGstr3b"),
    ("lastGstr1", "gstReturnState.lastGstr1"),
    ("lastCmp08", "gstReturnState.lastCmp08"),
    ("lastGstr4", "gstReturnState.lastGstr4"),
    ("gstReturnType", "gstReturnState.gstReturnType"),
    ("gstr3bPeriod", "gstReturnState.gstr3bPeriod"),
    ("cmp08Quarter", "gstReturnState.cmp08Quarter"),
    ("gstr4Fy", "gstReturnState.gstr4Fy"),
]


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)

    out: list[str] = []
    for line in lines:
        if line in STATE_LINES:
            continue
        out.append(line)
    text = "".join(out)

    text = re.sub(
        r"\n// ═+\n// SECTION: GST SETTLEMENT.*?\nasync function downloadObTemplate\(\)",
        "\nasync function downloadObTemplate()",
        text,
        count=1,
        flags=re.DOTALL,
    )

    text = re.sub(
        r"\n// ═+\n// SECTION: GSTR-1 \(Outward Supplies\).*?\n\n\n// ═+\n// SECTION: ITC REVERSALS",
        "\n\n// ══════════════════════════════════════════════════════════════════════\n// SECTION: ITC REVERSALS",
        text,
        count=1,
        flags=re.DOTALL,
    )

    text = re.sub(
        r"\n// ---- GSTR-1 outward-supplies return.*?\n",
        "\n",
        text,
        count=1,
    )

    if 'from "./modules/workspaces/gst-returns.js"' not in text:
        text = text.replace(
            '} from "./modules/workspaces/mandir-tables.js";\n',
            '} from "./modules/workspaces/mandir-tables.js";\n' + IMPORT_BLOCK,
        )

    if "initGstReturns({" not in text:
        text = text.replace(
            "  formatCurrency,\n});\n\n// Initialize theme on app load",
            "  formatCurrency,\n});" + INIT_BLOCK + "\n// Initialize theme on app load",
            1,
        )

    for old, new in REPLACEMENTS:
        text = text.replace(old, new)

    APP.write_text(text, encoding="utf-8")
    print(f"Patched {APP} ({text.count(chr(10)) + 1} lines)")


if __name__ == "__main__":
    main()
