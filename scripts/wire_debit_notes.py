"""Wire debit-notes module into app.js and remove inlined block."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "mitrabooks-erp" / "app.js"
HTML = ROOT / "frontend" / "mitrabooks-erp" / "index.html"
BASELINE = ROOT / "scripts" / "file_size_baseline.json"

IMPORT_BLOCK = '''\
import {
  initDebitNotes,
  debitUi,
  loadDebitNotes,
  syncDnFormFromDom,
  updateDnTotalsDisplay,
  setDebitNoteView,
  openDebitNoteCreate,
  addDnLine,
  removeDnLine,
  submitDebitNote,
  openDebitNoteDetail,
  cancelDebitNote,
  renderBusinessDebitNoteWorkspace,
  rerenderDebitNoteIfActive,
} from "./modules/documents/debit-notes.js";
'''

INIT_BLOCK = '''\
// Wire debit notes workspace (avoids import cycle with app.js)
initDebitNotes({
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

    marker = '} from "./modules/documents/credit-notes.js";\n'
    if marker not in text:
        raise SystemExit("credit-notes import marker not found")
    if "debit-notes.js" not in text:
        text = text.replace(marker, marker + "\n" + IMPORT_BLOCK)

    start = text.find("// ========== Business Module: Debit Notes (purchase GST adjustment) ==========")
    end = text.find("// ========== Business Module: Typed Vouchers ==========")
    if start < 0 or end < 0:
        raise SystemExit(f"debit block markers missing start={start} end={end}")
    text = text[:start] + text[end:]

    text = text.replace('debitNoteView = "list"', 'debitUi.view = "list"')
    text = text.replace(
        'activeBusinessWorkspace === "debit-notes" && debitNoteView === "create"',
        'activeBusinessWorkspace === "debit-notes" && debitUi.view === "create"',
    )
    text = text.replace("dnReverseOpen = true", "debitUi.reverseOpen = true")
    text = text.replace("dnReverseOpen = false", "debitUi.reverseOpen = false")
    text = text.replace("lastDebitNoteDetail", "debitUi.detail")
    text = text.replace("lastDebitNotes", "debitUi.notes")

    # Insert init after credit notes init
    credit_marker = "initCreditNotes({"
    idx = text.find(credit_marker)
    if idx < 0:
        raise SystemExit("initCreditNotes not found")
    end_idx = text.find("});\n", idx)
    if end_idx < 0:
        raise SystemExit("credit init end not found")
    insert_at = end_idx + len("});\n")
    if "initDebitNotes(" not in text:
        text = text[:insert_at] + "\n" + INIT_BLOCK + text[insert_at:]

    APP.write_text(text, encoding="utf-8")

    html = HTML.read_text(encoding="utf-8")
    html2 = html.replace("app.js?v=mitrabooks-erp-v47", "app.js?v=mitrabooks-erp-v48")
    if html2 == html:
        raise SystemExit("cache bump marker v47 not found")
    HTML.write_text(html2, encoding="utf-8")

    n = sum(1 for _ in APP.open(encoding="utf-8"))
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    old = data.get("frontend/mitrabooks-erp/app.js")
    data["frontend/mitrabooks-erp/app.js"] = n
    dn_n = sum(1 for _ in (ROOT / "frontend/mitrabooks-erp/modules/documents/debit-notes.js").open(encoding="utf-8"))
    if dn_n > 800:
        data["frontend/mitrabooks-erp/modules/documents/debit-notes.js"] = dn_n
    ordered = dict(sorted(data.items(), key=lambda kv: (-kv[1], kv[0])))
    BASELINE.write_text(json.dumps(ordered, indent=2) + "\n", encoding="utf-8")
    print(f"app.js {old} -> {n}; debit-notes.js {dn_n}")


if __name__ == "__main__":
    main()
