"""Extract purchase bills workspace from app.js into modules/documents/purchase-bills.js."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "mitrabooks-erp" / "app.js"
OUT = ROOT / "frontend" / "mitrabooks-erp" / "modules" / "documents" / "purchase-bills.js"

HEADER = '''\
// ====================================================================
// SECTION: PURCHASE BILLS WORKSPACE
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initPurchaseBills(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";
import { computeInvoiceLine, invoiceStatusPill } from "./sales-invoices.js";

export const purchaseUi = {
  view: "list", // list | create | detail
  bills: [],
  detail: null,
  lineSeq: 0,
  formLines: [],
  header: {
    vendor_party_id: "",
    bill_number: "",
    bill_date: "",
    due_date: "",
    is_inter_state: false,
    is_reverse_charge: false,
    expense_account_code: "51001",
    place_of_supply: "",
    notes: "",
    tds_section: "",
    cost_centre_id: "",
    project_id: "",
  },
  reverseOpen: false,
  attachments: [],
  attachmentsLoading: false,
};

/** @type {Record<string, Function> | null} */
let deps = null;

export function initPurchaseBills(injected) {
  deps = injected;
  purchaseUi.header.bill_date = injected.todayIsoDate();
}

function requireDeps() {
  if (!deps) {
    throw new Error("initPurchaseBills() must be called before using purchase bill helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function todayIsoDate() { return requireDeps().todayIsoDate(); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function round2(value) { return requireDeps().round2(value); }
function tdsSectionOptions(kind, selected) { return requireDeps().tdsSectionOptions(kind, selected); }
function tdsSectionRate(kind, section) { return requireDeps().tdsSectionRate(kind, section); }
function loadTdsSections() { return requireDeps().loadTdsSections(); }
function hasTdsSectionsCache() { return requireDeps().hasTdsSectionsCache(); }
function isBusinessAdmin() { return requireDeps().isBusinessAdmin(); }
function reversalPanel(kind, id, isoDate) { return requireDeps().reversalPanel(kind, id, isoDate); }
function focusBusinessEntryField(selector) { requireDeps().focusBusinessEntryField(selector); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function renderBusinessWorkspace() { return requireDeps().renderBusinessWorkspace(); }
function getLastBusinessParties() { return requireDeps().getLastBusinessParties(); }
function loadBusinessParties() { return requireDeps().loadBusinessParties(); }
function hasLoadedBusinessAccounts() { return requireDeps().hasLoadedBusinessAccounts(); }
function loadBusinessAccounts() { return requireDeps().loadBusinessAccounts(); }
function businessAccountsForSelection() { return requireDeps().businessAccountsForSelection(); }
function dimensionOptions(kind, selected) { return requireDeps().dimensionOptions(kind, selected); }
function getLastDimensions() { return requireDeps().getLastDimensions(); }
function loadDimensions() { return requireDeps().loadDimensions(); }
function getLastInventoryItems() { return requireDeps().getLastInventoryItems(); }
function loadInventoryItems() { return requireDeps().loadInventoryItems(); }
function inventoryItemOptions(selected) { return requireDeps().inventoryItemOptions(selected); }
function renderBusinessAttachmentPanel(opts) { return requireDeps().renderBusinessAttachmentPanel(opts); }
function listBusinessAttachments(ownerType, ownerId) { return requireDeps().listBusinessAttachments(ownerType, ownerId); }
function getApiOutput() { return requireDeps().getApiOutput(); }

'''

# Mapping of old names -> purchaseUi fields (simple textual replacements on body)
REPLACEMENTS = [
    ("purchaseView", "purchaseUi.view"),
    ("lastBusinessBills", "purchaseUi.bills"),
    ("lastBillDetail", "purchaseUi.detail"),
    ("billLineSeq", "purchaseUi.lineSeq"),
    ("billFormLines", "purchaseUi.formLines"),
    ("billFormHeader", "purchaseUi.header"),
    ("billReverseOpen", "purchaseUi.reverseOpen"),
    ("lastBillAttachments", "purchaseUi.attachments"),
    ("billAttachmentsLoading", "purchaseUi.attachmentsLoading"),
    ("currentExperience", "getCurrentExperience()"),
    ("activeBusinessWorkspace", "getActiveBusinessWorkspace()"),
    ("dashboardPreview.innerHTML", "getDashboardPreview().innerHTML"),
    ("apiOutput", "getApiOutput()"),
    ("lastBusinessParties", "getLastBusinessParties()"),
    ("!tdsSectionsCache", "!hasTdsSectionsCache()"),
    ("if (!tdsSectionsCache)", "if (!hasTdsSectionsCache())"),
    ("!lastDimensions", "!getLastDimensions()"),
    ("if (!lastDimensions)", "if (!getLastDimensions())"),
    ("!lastInventoryItems", "!getLastInventoryItems()"),
    ("if (!lastInventoryItems)", "if (!getLastInventoryItems())"),
]


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(True)
    # Lines 10113-10670 (1-based) = indices 10112:10670
    body = "".join(lines[10112:10670])

    # Drop the old local state declarations — moved into purchaseUi
    drop_prefixes = (
        "// ========== Business Module: Purchase Bills",
        "let purchaseView",
        "let lastBusinessBills",
        "let lastBillDetail",
        "let billLineSeq",
        "let billFormLines",
        "const billFormHeader",
    )
    out_lines: list[str] = []
    skipping_header_obj = False
    brace_depth = 0
    for line in body.splitlines(True):
        stripped = line.lstrip()
        if any(stripped.startswith(p) for p in drop_prefixes):
            if stripped.startswith("const billFormHeader"):
                skipping_header_obj = True
                brace_depth = line.count("{") - line.count("}")
                continue
            continue
        if skipping_header_obj:
            brace_depth += line.count("{") - line.count("}")
            if brace_depth <= 0:
                skipping_header_obj = False
            continue
        # Drop duplicate SECTION banner block comments that only wrap renderBusinessPurchaseWorkspace
        if stripped.startswith("// ══") or stripped.startswith("// SECTION: PURCHASE") or stripped.startswith("// API") or stripped.startswith("// NOTE  : loadBusinessBills"):
            continue
        out_lines.append(line)

    body2 = "".join(out_lines)
    for old, new in REPLACEMENTS:
        body2 = body2.replace(old, new)

    # Prefix exported functions
    export_names = [
        "rerenderPurchaseIfActive",
        "loadBusinessBills",
        "vendorPartyOptions",
        "expenseAccountOptions",
        "syncBillFormFromDom",
        "updateBillTotalsDisplay",
        "setBusinessPurchaseView",
        "openBillCreate",
        "addBillLine",
        "removeBillLine",
        "submitBill",
        "openBillDetail",
        "loadBillAttachments",
        "cancelBill",
        "renderBillListTable",
        "renderBillCreateForm",
        "renderBillDetail",
        "renderBusinessPurchaseWorkspace",
    ]
    for name in export_names:
        body2 = body2.replace(f"function {name}", f"export function {name}")
        body2 = body2.replace(f"async function {name}", f"export async function {name}")

    OUT.write_text(HEADER + body2, encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} ({sum(1 for _ in OUT.open(encoding='utf-8'))} lines)")


if __name__ == "__main__":
    main()
