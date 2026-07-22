"""Extract credit notes workspace from app.js into modules/documents/credit-notes.js."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "mitrabooks-erp" / "app.js"
OUT = ROOT / "frontend" / "mitrabooks-erp" / "modules" / "documents" / "credit-notes.js"

HEADER = '''\
// ====================================================================
// SECTION: CREDIT NOTES WORKSPACE
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initCreditNotes(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";
import {
  computeInvoiceLine,
  invoiceStatusPill,
  customerPartyOptions,
  incomeAccountOptions,
  salesUi,
  loadBusinessInvoices,
} from "./sales-invoices.js";

export const creditUi = {
  view: "list", // list | create | detail
  notes: [],
  detail: null,
  lineSeq: 0,
  formLines: [],
  reverseOpen: false,
  reasons: [
    ["sales_return", "Sales return"],
    ["discount", "Post-sale discount"],
    ["price_revision", "Price revision (downward)"],
    ["deficiency", "Deficiency in service/goods"],
    ["other", "Other"],
  ],
  header: {
    customer_party_id: "",
    note_date: "",
    original_invoice_id: "",
    original_invoice_number: "",
    reason: "sales_return",
    is_inter_state: false,
    income_account_code: "41001",
    place_of_supply: "",
    notes: "",
    cost_centre_id: "",
    project_id: "",
  },
};

/** @type {Record<string, Function> | null} */
let deps = null;

export function initCreditNotes(injected) {
  deps = injected;
  creditUi.header.note_date = injected.todayIsoDate();
}

function requireDeps() {
  if (!deps) {
    throw new Error("initCreditNotes() must be called before using credit note helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function todayIsoDate() { return requireDeps().todayIsoDate(); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function round2(value) { return requireDeps().round2(value); }
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
function dimensionOptions(kind, selected) { return requireDeps().dimensionOptions(kind, selected); }
function getLastDimensions() { return requireDeps().getLastDimensions(); }
function loadDimensions() { return requireDeps().loadDimensions(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

'''

REPLACEMENTS = [
    ("CN_REASONS", "creditUi.reasons"),
    ("creditNoteView", "creditUi.view"),
    ("lastCreditNotes", "creditUi.notes"),
    ("lastCreditNoteDetail", "creditUi.detail"),
    ("cnLineSeq", "creditUi.lineSeq"),
    ("cnFormLines", "creditUi.formLines"),
    ("cnFormHeader", "creditUi.header"),
    ("cnReverseOpen", "creditUi.reverseOpen"),
    ("currentExperience", "getCurrentExperience()"),
    ("activeBusinessWorkspace", "getActiveBusinessWorkspace()"),
    ("dashboardPreview.innerHTML", "getDashboardPreview().innerHTML"),
    ("apiOutput", "getApiOutput()"),
    ("lastBusinessParties", "getLastBusinessParties()"),
    ("!lastDimensions", "!getLastDimensions()"),
    ("if (!lastDimensions)", "if (!getLastDimensions())"),
]


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(True)
    start = next(i for i, l in enumerate(lines) if "Business Module: Credit Notes" in l)
    end = next(i for i, l in enumerate(lines) if "Business Module: Debit Notes" in l)
    block_lines = lines[start:end]

    # Keep from first function onward (drop banner + local state decls)
    first_fn = next(i for i, l in enumerate(block_lines) if l.startswith("function ") or l.startswith("async function "))
    body = "".join(block_lines[first_fn:])

    # Drop duplicate SECTION banner lines that wrap renderBusinessCreditNoteWorkspace
    cleaned: list[str] = []
    for line in body.splitlines(True):
        stripped = line.lstrip()
        if (
            stripped.startswith("// ══")
            or stripped.startswith("// SECTION: CREDIT")
            or stripped.startswith("// API")
            or stripped.startswith("// NOTE  : loadCreditNotes")
        ):
            continue
        cleaned.append(line)
    body2 = "".join(cleaned)

    for old, new in REPLACEMENTS:
        body2 = body2.replace(old, new)

    export_names = [
        "rerenderCreditNoteIfActive",
        "loadCreditNotes",
        "resolveCreditNoteSourceInvoice",
        "creditNoteSourceInvoiceOptions",
        "syncCnFormFromDom",
        "updateCnTotalsDisplay",
        "setCreditNoteView",
        "openCreditNoteCreate",
        "addCnLine",
        "removeCnLine",
        "submitCreditNote",
        "openCreditNoteDetail",
        "cancelCreditNote",
        "cnReasonLabel",
        "renderCnListTable",
        "renderCreditNoteCreateForm",
        "renderCreditNoteDetail",
        "renderBusinessCreditNoteWorkspace",
    ]
    for name in export_names:
        body2 = body2.replace(f"async function {name}", f"__EXPORT_ASYNC__{name}")
        body2 = body2.replace(f"function {name}", f"__EXPORT_FN__{name}")
    body2 = body2.replace("__EXPORT_ASYNC__", "export async function ")
    body2 = body2.replace("__EXPORT_FN__", "export function ")

    OUT.write_text(HEADER + body2, encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} ({sum(1 for _ in OUT.open(encoding='utf-8'))} lines)")


if __name__ == "__main__":
    main()
