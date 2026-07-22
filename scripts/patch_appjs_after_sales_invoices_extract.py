"""Patch app.js after sales invoices extraction."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "mitrabooks-erp" / "app.js"

IMPORT_BLOCK = '''import {
  initSalesInvoices,
  salesUi,
  loadInvoiceSettings,
  loadBusinessInvoices,
  syncSalesFormFromDom,
  updateInvoiceTotalsDisplay,
  computeInvoiceLine,
  invoiceStatusPill,
  customerPartyOptions,
  incomeAccountOptions,
  setBusinessSalesView,
  openInvoiceCreate,
  addInvoiceLine,
  removeInvoiceLine,
  submitInvoice,
  downloadInvoicePdf,
  openInvoiceDetail,
  cancelInvoice,
  openInvoiceSettings,
  saveInvoiceSettings,
  renderBusinessSalesWorkspace,
} from "./modules/documents/sales-invoices.js";
'''

INIT_BLOCK = '''
// Wire sales invoices workspace (avoids import cycle with app.js)
initSalesInvoices({
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
  businessAccountsForSelection,
  dimensionOptions,
  getLastInventoryItems: () => lastInventoryItems,
  loadInventoryItems,
  inventoryItemOptions,
  renderEinvoiceSection,
  loadEinvoiceView,
  clearEinvoiceView: () => { lastEinvoiceView = null; },
  renderBusinessAttachmentPanel,
  listBusinessAttachments,
  getApiOutput: () => apiOutput,
});
'''


def main() -> None:
    text = APP.read_text(encoding="utf-8")

    if 'from "./modules/documents/sales-invoices.js"' not in text:
        text = text.replace(
            '} from "./modules/workspaces/gst-returns.js";\n',
            '} from "./modules/workspaces/gst-returns.js";\n' + IMPORT_BLOCK,
        )

    if "initSalesInvoices({" not in text:
        text = text.replace(
            "  getApiOutput: () => apiOutput,\n});\n\n// Initialize theme on app load",
            "  getApiOutput: () => apiOutput,\n});" + INIT_BLOCK + "\n// Initialize theme on app load",
            1,
        )

    # External assignment sites
    text = text.replace('salesView = "list";', 'salesUi.view = "list";')

    APP.write_text(text, encoding="utf-8")
    print(f"Patched {APP} ({text.count(chr(10)) + 1} lines)")


if __name__ == "__main__":
    main()
