"""Extract Sales Invoices workspace from mitrabooks-erp/app.js (Phase 3 seam 8).

Moves only sales-specific decls; shared helpers (TDS options, isBusinessAdmin,
round2, reversalPanel, focusBusinessEntryField, voucher filters, admin settings)
stay in app.js.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "mitrabooks-erp" / "app.js"
OUT = ROOT / "frontend" / "mitrabooks-erp" / "modules" / "documents" / "sales-invoices.js"

MOVE_FUNCS = {
    "invoiceFieldRule",
    "invoiceFieldVisible",
    "invoiceFieldRequired",
    "loadInvoiceSettings",
    "rerenderSalesIfActive",
    "loadBusinessInvoices",
    "customerPartyOptions",
    "incomeAccountOptions",
    "computeInvoiceLine",
    "syncSalesFormFromDom",
    "updateInvoiceTotalsDisplay",
    "setBusinessSalesView",
    "openInvoiceCreate",
    "addInvoiceLine",
    "removeInvoiceLine",
    "submitInvoice",
    "downloadInvoicePdf",
    "openInvoiceDetail",
    "loadInvoiceAttachments",
    "cancelInvoice",
    "invoiceStatusPill",
    "renderInvoiceListTable",
    "invoiceFieldLabel",
    "invoiceNumberPreview",
    "renderInvoiceCreateForm",
    "renderInvoiceDetail",
    "openInvoiceSettings",
    "saveInvoiceSettings",
    "renderInvoiceSettingsPanel",
    "renderBusinessSalesWorkspace",
}

MOVE_STATE_STARTS = (
    "let salesView =",
    "let lastBusinessInvoices =",
    "let lastInvoiceDetail =",
    "let lastInvoiceSettings =",
    "let invoiceLineSeq =",
    "let invoiceFormLines =",
    "const salesFormHeader =",
    "const INVOICE_STANDARD_FIELD_LABELS =",
    "let invoiceReverseOpen =",
)

STATE_REPLACEMENTS = [
    ("lastInvoiceAttachments", "salesUi.attachments"),
    ("invoiceAttachmentsLoading", "salesUi.attachmentsLoading"),
    ("lastBusinessInvoices", "salesUi.invoices"),
    ("lastInvoiceDetail", "salesUi.detail"),
    ("lastInvoiceSettings", "salesUi.settings"),
    ("invoiceLineSeq", "salesUi.lineSeq"),
    ("invoiceFormLines", "salesUi.formLines"),
    ("salesFormHeader", "salesUi.header"),
    ("invoiceReverseOpen", "salesUi.reverseOpen"),
    ("salesView", "salesUi.view"),
]

HEADER = '''// ====================================================================
// SECTION: SALES INVOICES WORKSPACE
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initSalesInvoices(...).
// ====================================================================

import { apiRequest, downloadApiFile, renderJson } from "../../../shared/api-client.js";

export const salesUi = {
  view: "list", // list | create | detail | settings
  invoices: [],
  detail: null,
  settings: null,
  lineSeq: 0,
  formLines: [],
  header: {
    customer_party_id: "",
    invoice_date: "",
    due_date: "",
    is_inter_state: false,
    income_account_code: "41001",
    place_of_supply: "",
    reference: "",
    notes: "",
    tcs_section: "",
    cost_centre_id: "",
    project_id: "",
  },
  reverseOpen: false,
  attachments: [],
  attachmentsLoading: false,
};

/** @type {Record<string, Function> | null} */
let deps = null;

export function initSalesInvoices(injected) {
  deps = injected;
  salesUi.header.invoice_date = injected.todayIsoDate();
}

function requireDeps() {
  if (!deps) {
    throw new Error("initSalesInvoices() must be called before using sales invoice helpers");
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
function isBusinessAdmin() { return requireDeps().isBusinessAdmin(); }
function reversalPanel(kind, id, isoDate) { return requireDeps().reversalPanel(kind, id, isoDate); }
function focusBusinessEntryField(selector) { requireDeps().focusBusinessEntryField(selector); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function renderBusinessWorkspace() { return requireDeps().renderBusinessWorkspace(); }
function getLastBusinessParties() { return requireDeps().getLastBusinessParties(); }
function businessAccountsForSelection() { return requireDeps().businessAccountsForSelection(); }
function dimensionOptions(kind, selected) { return requireDeps().dimensionOptions(kind, selected); }
function getLastInventoryItems() { return requireDeps().getLastInventoryItems(); }
function loadInventoryItems() { return requireDeps().loadInventoryItems(); }
function inventoryItemOptions(selected) { return requireDeps().inventoryItemOptions(selected); }
function renderEinvoiceSection(inv) { return requireDeps().renderEinvoiceSection(inv); }
function loadEinvoiceView(invoiceId) { return requireDeps().loadEinvoiceView(invoiceId); }
function clearEinvoiceView() { requireDeps().clearEinvoiceView(); }
function renderBusinessAttachmentPanel(opts) { return requireDeps().renderBusinessAttachmentPanel(opts); }
function listBusinessAttachments(ownerType, ownerId) { return requireDeps().listBusinessAttachments(ownerType, ownerId); }
function getApiOutput() { return requireDeps().getApiOutput(); }

'''


def top_level_ranges(lines: list[str]) -> list[tuple[int, int, str]]:
    """Return (start, end_exclusive, first_line) for each top-level decl (0-based)."""
    ranges: list[tuple[int, int, str]] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if (
            line.startswith("function ")
            or line.startswith("async function ")
            or line.startswith("let ")
            or line.startswith("const ")
        ):
            start = i
            # brace/paren balance for multi-line const/let objects and functions
            depth_brace = 0
            depth_paren = 0
            depth_bracket = 0
            j = i
            while j < n:
                for ch in lines[j]:
                    if ch == "{":
                        depth_brace += 1
                    elif ch == "}":
                        depth_brace -= 1
                    elif ch == "(":
                        depth_paren += 1
                    elif ch == ")":
                        depth_paren -= 1
                    elif ch == "[":
                        depth_bracket += 1
                    elif ch == "]":
                        depth_bracket -= 1
                # single-line let/const without braces ends at ;
                if j == start and depth_brace == 0 and depth_paren == 0 and depth_bracket == 0 and lines[j].rstrip().endswith(";"):
                    j += 1
                    break
                j += 1
                if depth_brace == 0 and depth_paren == 0 and depth_bracket == 0 and j > start + 1:
                    # function body closed
                    if lines[start].startswith("function ") or lines[start].startswith("async function "):
                        break
                    # object/array assignment closed
                    if lines[j - 1].rstrip().endswith(";") or lines[j - 1].rstrip().endswith("},") is False:
                        if lines[j - 1].rstrip().endswith(";") or (lines[start].startswith("const ") and depth_brace == 0):
                            break
            # refine: for functions, stop after closing brace line
            if lines[start].startswith("function ") or lines[start].startswith("async function "):
                depth = 0
                j = start
                while j < n:
                    depth += lines[j].count("{") - lines[j].count("}")
                    j += 1
                    if depth == 0 and j > start:
                        break
            elif lines[start].startswith("const ") or lines[start].startswith("let "):
                depth = 0
                j = start
                started = False
                while j < n:
                    depth += lines[j].count("{") - lines[j].count("}")
                    depth += lines[j].count("[") - lines[j].count("]")
                    if "{" in lines[j] or "[" in lines[j]:
                        started = True
                    j += 1
                    if (started and depth == 0) or (not started and lines[j - 1].rstrip().endswith(";")):
                        break
            ranges.append((start, j, lines[start]))
            i = j
            continue
        i += 1
    return ranges


def func_name(first_line: str) -> str | None:
    m = re.match(r"(?:async\s+)?function\s+(\w+)", first_line)
    return m.group(1) if m else None


def should_move(first_line: str) -> bool:
    name = func_name(first_line)
    if name and name in MOVE_FUNCS:
        return True
    return any(first_line.startswith(s) for s in MOVE_STATE_STARTS)


def apply_state_replacements(text: str) -> str:
    for old, new in STATE_REPLACEMENTS:
        text = re.sub(rf"\b{old}\b", new, text)
    return text


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    ranges = top_level_ranges(lines)

    move_ranges = [(s, e) for s, e, first in ranges if should_move(first)]
    if not move_ranges:
        raise SystemExit("No sales decls found to move")

    # Extract body in original order
    body_parts: list[str] = []
    for s, e in move_ranges:
        chunk = "".join(lines[s:e])
        body_parts.append(chunk)

    body = "".join(body_parts)
    body = apply_state_replacements(body)
    # Drop moved state decls (now in salesUi)
    body = re.sub(r"^let salesUi\.view = .*?\n", "", body, flags=re.M)
    body = re.sub(r"^let salesUi\.invoices = .*?\n", "", body, flags=re.M)
    body = re.sub(r"^let salesUi\.detail = .*?\n", "", body, flags=re.M)
    body = re.sub(r"^let salesUi\.settings = .*?\n", "", body, flags=re.M)
    body = re.sub(r"^let salesUi\.lineSeq = .*?\n", "", body, flags=re.M)
    body = re.sub(r"^let salesUi\.formLines = .*?\n", "", body, flags=re.M)
    body = re.sub(r"^let salesUi\.reverseOpen = .*?\n", "", body, flags=re.M)
    body = re.sub(
        r"^const salesUi\.header = \{.*?\n\};\n",
        "",
        body,
        count=1,
        flags=re.M | re.S,
    )
    # Fix broken const rename for INVOICE labels - keep as-is
    body = body.replace("const salesUi.header =", "const salesFormHeaderREMOVED =")  # safety

    for name in sorted(MOVE_FUNCS, key=len, reverse=True):
        body = body.replace(f"async function {name}", f"export async function {name}")
        body = body.replace(f"function {name}", f"export function {name}")
        # Avoid double-prefixing if async already exported
        body = body.replace(f"export async export function {name}", f"export async function {name}")
        body = body.replace(f"export export function {name}", f"export function {name}")

    # Fix shell refs inside module
    body = body.replace("currentExperience", "getCurrentExperience()")
    body = body.replace("activeBusinessWorkspace", "getActiveBusinessWorkspace()")
    body = body.replace("dashboardPreview", "getDashboardPreview()")
    body = body.replace("lastBusinessParties", "getLastBusinessParties()")
    body = body.replace("lastInventoryItems", "getLastInventoryItems()")
    body = body.replace("lastEinvoiceView = null", "clearEinvoiceView()")
    body = body.replace("renderJson(apiOutput,", "renderJson(getApiOutput(),")

    # Avoid double-call if already functions somehow
    body = body.replace("getCurrentExperience()()", "getCurrentExperience()")
    body = body.replace("getActiveBusinessWorkspace()()", "getActiveBusinessWorkspace()")
    body = body.replace("getDashboardPreview()()", "getDashboardPreview()")
    body = body.replace("getLastBusinessParties()()", "getLastBusinessParties()")
    body = body.replace("getLastInventoryItems()()", "getLastInventoryItems()")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(HEADER + body, encoding="utf-8")
    print(f"Wrote {OUT} ({sum(1 for _ in OUT.open(encoding='utf-8'))} lines)")

    # Remove moved ranges from app.js (from bottom so indices stay valid)
    remove = set()
    for s, e in move_ranges:
        remove.update(range(s, e))
    new_lines = [line for i, line in enumerate(lines) if i not in remove]
    text = "".join(new_lines)

    # Remove orphaned sales banner / comment if now dangling near purchase
    text = text.replace(
        "\n// ========== Business Module: Sales Invoices (GST) ==========\n\n",
        "\n",
    )
    text = re.sub(
        r"\n// ═+\n// SECTION: SALES INVOICES WORKSPACE\n// API.*?\n// NOTE.*?\n// ═+\n\n",
        "\n",
        text,
        count=1,
        flags=re.S,
    )

    # Remove invoice attachment state from CA area (moved into salesUi)
    text = text.replace("let lastInvoiceAttachments = [];\n", "")
    text = text.replace("let invoiceAttachmentsLoading = false;\n", "")

    APP.write_text(text, encoding="utf-8")
    print(f"Trimmed {APP} ({text.count(chr(10)) + 1} lines) — run patch script next")


if __name__ == "__main__":
    main()
