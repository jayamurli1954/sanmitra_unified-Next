"""Wire credit-notes module into app.js and remove inlined block."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "mitrabooks-erp" / "app.js"
HTML = ROOT / "frontend" / "mitrabooks-erp" / "index.html"
BASELINE = ROOT / "scripts" / "file_size_baseline.json"

IMPORT_BLOCK = '''\
import {
  initCreditNotes,
  creditUi,
  loadCreditNotes,
  syncCnFormFromDom,
  updateCnTotalsDisplay,
  setCreditNoteView,
  openCreditNoteCreate,
  addCnLine,
  removeCnLine,
  submitCreditNote,
  openCreditNoteDetail,
  cancelCreditNote,
  renderBusinessCreditNoteWorkspace,
  rerenderCreditNoteIfActive,
} from "./modules/documents/credit-notes.js";
'''

INIT_BLOCK = '''\
// Wire credit notes workspace (avoids import cycle with app.js)
initCreditNotes({
  escapeHtml,
  formatCurrency,
  todayIsoDate,
  setLoginStatus,
  statusDetailText,
  round2,
  reversalPanel,
  focusBusinessEntryField,
  getCurrentExperience: () => currentExperience,
  getActiveBusinessWorkspace: () => activeBusinessWorkspace,
  getDashboardPreview: () => dashboardPreview,
  renderBusinessWorkspace: () => renderBusinessWorkspace(),
  getLastBusinessParties: () => lastBusinessParties,
  loadBusinessParties,
  hasLoadedBusinessAccounts,
  loadBusinessAccounts,
  dimensionOptions,
  getLastDimensions: () => lastDimensions,
  loadDimensions,
  getApiOutput: () => apiOutput,
});
'''


def main() -> None:
    text = APP.read_text(encoding="utf-8")

    marker = '} from "./modules/documents/purchase-bills.js";\n'
    if marker not in text:
        raise SystemExit("purchase-bills import marker not found")
    if "credit-notes.js" not in text:
        text = text.replace(marker, marker + "\n" + IMPORT_BLOCK)

    start = text.find("// ========== Business Module: Credit Notes (sales GST adjustment) ==========")
    end = text.find("// ========== Business Module: Debit Notes (purchase GST adjustment) ==========")
    if start < 0 or end < 0:
        raise SystemExit(f"credit block markers missing start={start} end={end}")
    text = text[:start] + text[end:]

    text = text.replace('creditNoteView = "list"', 'creditUi.view = "list"')
    text = text.replace(
        'activeBusinessWorkspace === "credit-notes" && creditNoteView === "create"',
        'activeBusinessWorkspace === "credit-notes" && creditUi.view === "create"',
    )
    text = text.replace("cnReverseOpen = true", "creditUi.reverseOpen = true")
    text = text.replace("cnReverseOpen = false", "creditUi.reverseOpen = false")
    text = text.replace("lastCreditNoteDetail", "creditUi.detail")
    text = text.replace("lastCreditNotes", "creditUi.notes")

    sales_init_end = "hasTdsSectionsCache: () => !!tdsSectionsCache,\n});\n"
    # Prefer inserting after purchase init if present
    purchase_marker = "initPurchaseBills({"
    if purchase_marker in text:
        # Find end of purchase init block
        idx = text.find(purchase_marker)
        end_idx = text.find("});\n", idx)
        if end_idx < 0:
            raise SystemExit("purchase init end not found")
        insert_at = end_idx + len("});\n")
        if "initCreditNotes(" not in text:
            text = text[:insert_at] + "\n" + INIT_BLOCK + text[insert_at:]
    else:
        raise SystemExit("initPurchaseBills not found")

    APP.write_text(text, encoding="utf-8")

    html = HTML.read_text(encoding="utf-8")
    html2 = html.replace("app.js?v=mitrabooks-erp-v46", "app.js?v=mitrabooks-erp-v47")
    if html2 == html:
        raise SystemExit("cache bump marker v46 not found")
    HTML.write_text(html2, encoding="utf-8")

    n = sum(1 for _ in APP.open(encoding="utf-8"))
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    old = data.get("frontend/mitrabooks-erp/app.js")
    data["frontend/mitrabooks-erp/app.js"] = n
    cn_n = sum(1 for _ in (ROOT / "frontend/mitrabooks-erp/modules/documents/credit-notes.js").open(encoding="utf-8"))
    if cn_n > 800:
        data["frontend/mitrabooks-erp/modules/documents/credit-notes.js"] = cn_n
    ordered = dict(sorted(data.items(), key=lambda kv: (-kv[1], kv[0])))
    BASELINE.write_text(json.dumps(ordered, indent=2) + "\n", encoding="utf-8")
    print(f"app.js {old} -> {n}; credit-notes.js {cn_n}")


if __name__ == "__main__":
    main()
