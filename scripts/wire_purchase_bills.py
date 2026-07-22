"""Wire purchase-bills module into app.js and remove inlined block."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "mitrabooks-erp" / "app.js"
HTML = ROOT / "frontend" / "mitrabooks-erp" / "index.html"

IMPORT_BLOCK = '''\
import {
  initPurchaseBills,
  purchaseUi,
  loadBusinessBills,
  syncBillFormFromDom,
  updateBillTotalsDisplay,
  setBusinessPurchaseView,
  openBillCreate,
  addBillLine,
  removeBillLine,
  submitBill,
  openBillDetail,
  loadBillAttachments,
  cancelBill,
  renderBusinessPurchaseWorkspace,
  rerenderPurchaseIfActive,
  vendorPartyOptions,
  expenseAccountOptions,
} from "./modules/documents/purchase-bills.js";
'''

INIT_BLOCK = '''\
// Wire purchase bills workspace (avoids import cycle with app.js)
initPurchaseBills({
  escapeHtml,
  formatCurrency,
  todayIsoDate,
  setLoginStatus,
  statusDetailText,
  round2,
  tdsSectionOptions,
  tdsSectionRate,
  loadTdsSections,
  isBusinessAdmin,
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
  businessAccountsForSelection,
  dimensionOptions,
  getLastDimensions: () => lastDimensions,
  loadDimensions,
  getLastInventoryItems: () => lastInventoryItems,
  loadInventoryItems,
  inventoryItemOptions,
  renderBusinessAttachmentPanel,
  listBusinessAttachments,
  getApiOutput: () => apiOutput,
  hasTdsSectionsCache: () => !!tdsSectionsCache,
});
'''


def main() -> None:
    text = APP.read_text(encoding="utf-8")
    lines = text.splitlines(True)

    # Insert import after sales-invoices import block (ends with sales-invoices.js";)
    marker = '} from "./modules/documents/sales-invoices.js";\n'
    if marker not in text:
        raise SystemExit("sales-invoices import marker not found")
    if "purchase-bills.js" not in text:
        text = text.replace(marker, marker + "\n" + IMPORT_BLOCK)

    # Remove attachment state near CA docs
    text = text.replace(
        "let lastBillAttachments = [];\nlet billAttachmentsLoading = false;\n",
        "",
    )
    # Remove billReverseOpen
    text = text.replace("let billReverseOpen = false;\n\n", "")

    # Remove purchase bills body (lines 10113-10670 in original; re-find by markers)
    start = text.find("// ========== Business Module: Purchase Bills (Input GST / ITC) ==========")
    end = text.find("// ========== Business Module: Credit Notes (sales GST adjustment) ==========")
    if start < 0 or end < 0:
        raise SystemExit(f"purchase block markers missing start={start} end={end}")
    text = text[:start] + text[end:]

    # Call-site renames for remaining app.js references
    text = text.replace("purchaseView = \"list\"", "purchaseUi.view = \"list\"")
    text = text.replace(
        'activeBusinessWorkspace === "bills" && purchaseView === "create"',
        'activeBusinessWorkspace === "bills" && purchaseUi.view === "create"',
    )
    text = text.replace("billReverseOpen = true", "purchaseUi.reverseOpen = true")
    text = text.replace("billReverseOpen = false", "purchaseUi.reverseOpen = false")
    text = text.replace("lastBusinessBills", "purchaseUi.bills")

    # Insert init after sales init block
    sales_init_end = text.find("hasTdsSectionsCache: () => !!tdsSectionsCache,\n});\n")
    if sales_init_end < 0:
        raise SystemExit("sales init end marker not found")
    insert_at = sales_init_end + len("hasTdsSectionsCache: () => !!tdsSectionsCache,\n});\n")
    if "initPurchaseBills(" not in text:
        text = text[:insert_at] + "\n" + INIT_BLOCK + text[insert_at:]

    APP.write_text(text, encoding="utf-8")

    html = HTML.read_text(encoding="utf-8")
    html2 = html.replace("app.js?v=mitrabooks-erp-v45", "app.js?v=mitrabooks-erp-v46")
    if html2 == html:
        raise SystemExit("cache bump marker v45 not found")
    HTML.write_text(html2, encoding="utf-8")

    # baseline
    baseline_path = ROOT / "scripts" / "file_size_baseline.json"
    import json
    n = sum(1 for _ in APP.open(encoding="utf-8"))
    data = json.loads(baseline_path.read_text(encoding="utf-8"))
    old = data.get("frontend/mitrabooks-erp/app.js")
    data["frontend/mitrabooks-erp/app.js"] = n
    # grandfather new module if over 800
    pb_n = sum(1 for _ in (ROOT / "frontend/mitrabooks-erp/modules/documents/purchase-bills.js").open(encoding="utf-8"))
    if pb_n > 800:
        data["frontend/mitrabooks-erp/modules/documents/purchase-bills.js"] = pb_n
    ordered = dict(sorted(data.items(), key=lambda kv: (-kv[1], kv[0])))
    baseline_path.write_text(json.dumps(ordered, indent=2) + "\n", encoding="utf-8")
    print(f"app.js {old} -> {n}; purchase-bills.js {pb_n}")


if __name__ == "__main__":
    main()
