#!/usr/bin/env python3
"""Extract Mandir create forms + posting dialogs (Phase 3 seam 50)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/mandir-create-forms.js"

HEADER = '''\
// ====================================================================
// SECTION: MANDIR — CREATE FORMS + POSTING DIALOGS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initMandirCreateForms(...).
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

/** DOM refs bound once during init (same elements the shell owns). */
let mandirVerificationDialog;
let mandirVerificationPaymentId;
let mandirVerificationLabel;
let mandirVerificationUtr;
let mandirVerificationDate;
let mandirVerificationBankAccount;
let mandirRejectionDialog;
let mandirRejectionPaymentId;
let mandirRejectionLabel;
let mandirRejectionReason;
let mandirCorrectionDialog;
let mandirCorrectionForm;
let mandirCorrectionPaymentId;
let mandirCorrectionLabel;
let mandirCorrectionAmount;
let mandirCorrectionPhone;
let mandirCorrectionType;
let mandirCorrectionPurpose;
let mandirCancelReceiptDialog;
let mandirCancelReceiptUrl;
let mandirCancelReceiptLabel;
let mandirCancelReceiptReason;
let mandirCancelRefundMode;
let mandirCancelRefundReference;
let mandirCancelReceiptSubmit;
let receiptPreviewDialog;
let receiptPreviewFrame;
let receiptPreviewLabel;
let dashboardPreview;
let apiOutput;

export function initMandirCreateForms(injected) {
  deps = injected;
  mandirVerificationDialog = injected.mandirVerificationDialog;
  mandirVerificationPaymentId = injected.mandirVerificationPaymentId;
  mandirVerificationLabel = injected.mandirVerificationLabel;
  mandirVerificationUtr = injected.mandirVerificationUtr;
  mandirVerificationDate = injected.mandirVerificationDate;
  mandirVerificationBankAccount = injected.mandirVerificationBankAccount;
  mandirRejectionDialog = injected.mandirRejectionDialog;
  mandirRejectionPaymentId = injected.mandirRejectionPaymentId;
  mandirRejectionLabel = injected.mandirRejectionLabel;
  mandirRejectionReason = injected.mandirRejectionReason;
  mandirCorrectionDialog = injected.mandirCorrectionDialog;
  mandirCorrectionForm = injected.mandirCorrectionForm;
  mandirCorrectionPaymentId = injected.mandirCorrectionPaymentId;
  mandirCorrectionLabel = injected.mandirCorrectionLabel;
  mandirCorrectionAmount = injected.mandirCorrectionAmount;
  mandirCorrectionPhone = injected.mandirCorrectionPhone;
  mandirCorrectionType = injected.mandirCorrectionType;
  mandirCorrectionPurpose = injected.mandirCorrectionPurpose;
  mandirCancelReceiptDialog = injected.mandirCancelReceiptDialog;
  mandirCancelReceiptUrl = injected.mandirCancelReceiptUrl;
  mandirCancelReceiptLabel = injected.mandirCancelReceiptLabel;
  mandirCancelReceiptReason = injected.mandirCancelReceiptReason;
  mandirCancelRefundMode = injected.mandirCancelRefundMode;
  mandirCancelRefundReference = injected.mandirCancelRefundReference;
  mandirCancelReceiptSubmit = injected.mandirCancelReceiptSubmit;
  receiptPreviewDialog = injected.receiptPreviewDialog;
  receiptPreviewFrame = injected.receiptPreviewFrame;
  receiptPreviewLabel = injected.receiptPreviewLabel;
  dashboardPreview = injected.dashboardPreview;
  apiOutput = injected.apiOutput;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initMandirCreateForms() must be called before using Mandir create-form helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function todayIsoDate() { return requireDeps().todayIsoDate(); }
function apiRequest(...args) { return requireDeps().apiRequest(...args); }
function renderJson(...args) { return requireDeps().renderJson(...args); }
function loadMandirDashboard(...args) { return requireDeps().loadMandirDashboard(...args); }
function downloadApiFile(...args) { return requireDeps().downloadApiFile(...args); }
function fetchApiFileObjectUrl(...args) { return requireDeps().fetchApiFileObjectUrl(...args); }
function syncMandirNavActiveState() { return requireDeps().syncMandirNavActiveState(); }
function getLastMandirPaymentAccounts() { return requireDeps().getLastMandirPaymentAccounts(); }
function getLastMandirAccounts() { return requireDeps().getLastMandirAccounts(); }
function getLastMandirFormResult() { return requireDeps().getLastMandirFormResult(); }
function setLastMandirFormResult(value) { requireDeps().setLastMandirFormResult(value); }
function getLastMandirReceipt() { return requireDeps().getLastMandirReceipt(); }
function setLastMandirReceipt(value) { requireDeps().setLastMandirReceipt(value); }
function setLastMandirComplianceConfig(value) { requireDeps().setLastMandirComplianceConfig(value); }
function getMandirReportState() { return requireDeps().getMandirReportState(); }
function getMandirListState() { return requireDeps().getMandirListState(); }
function getMandirListPageSize() { return requireDeps().getMandirListPageSize(); }
function setActiveMandirWorkspace(view) { requireDeps().setActiveMandirWorkspace(view); }
function getActiveReceiptPreviewObjectUrl() { return requireDeps().getActiveReceiptPreviewObjectUrl(); }
function setActiveReceiptPreviewObjectUrl(value) { requireDeps().setActiveReceiptPreviewObjectUrl(value); }

'''

EXPORT_FUNCS = [
    "renderBankAccountOptions",
    "mandirAccountOptionValue",
    "mandirAccountOptionLabel",
    "renderMandirAccountOptions",
    "mandirPaymentAccountOptions",
    "mandirExpenseAccountOptions",
    "renderMandirCreateForms",
    "openMandirVerificationDialog",
    "mandirReceiptFromVerifyPayload",
    "submitMandirPublicPaymentVerification",
    "openMandirRejectionDialog",
    "submitMandirPublicPaymentRejection",
    "openMandirCorrectionDialog",
    "submitMandirPublicPaymentCorrection",
    "downloadMandirReceipt",
    "closeReceiptPreview",
    "previewMandirReceipt",
    "openMandirCancelReceiptDialog",
    "submitMandirCancelReceipt",
    "compactOptionalPhone",
    "formNumber",
    "formText",
    "setMandirFormResult",
    "mandirReceiptFromCreatePayload",
    "submitMandirDonationForm",
    "submitMandirComplianceForm",
    "submitMandirSevaForm",
    "submitMandirExpenseForm",
    "submitMandirCreateForm",
    "readMandirListFilterValues",
    "applyMandirListFilter",
    "resetMandirListFilter",
    "pageMandirList",
    "setMandirWorkspace",
]


def find_fn_block(lines: list[str], name: str) -> tuple[int, int]:
    start = next(
        i
        for i, l in enumerate(lines)
        if re.match(rf"^(async )?function {re.escape(name)}\b", l.lstrip())
    )
    depth = 0
    started = False
    end = start
    for i in range(start, len(lines)):
        line = lines[i]
        if "{" in line or "}" in line:
            depth += line.count("{") - line.count("}")
            started = True
        if started and depth <= 0:
            end = i + 1
            break
    else:
        raise SystemExit(f"unterminated function for {name}")
    while end < len(lines) and lines[end].strip() == "":
        end += 1
    return start, end


def rewrite_block(block: str) -> str:
    block = block.replace(
        "paymentAccounts = lastMandirPaymentAccounts",
        "paymentAccounts = getLastMandirPaymentAccounts()",
    )
    block = block.replace(
        "accounts = lastMandirAccounts",
        "accounts = getLastMandirAccounts()",
    )
    block = block.replace(
        "payload.form_result || lastMandirFormResult",
        "payload.form_result || getLastMandirFormResult()",
    )
    block = block.replace(
        "lastMandirFormResult = { ok, title, detail };",
        "setLastMandirFormResult({ ok, title, detail });",
    )
    block = block.replace(
        "lastMandirReceipt = mandirReceiptFromVerifyPayload(result.payload);",
        "setLastMandirReceipt(mandirReceiptFromVerifyPayload(result.payload));",
    )
    block = block.replace(
        "lastMandirReceipt = mandirReceiptFromCreatePayload(result.payload, \"donation\") || lastMandirReceipt;",
        "setLastMandirReceipt(mandirReceiptFromCreatePayload(result.payload, \"donation\") || getLastMandirReceipt());",
    )
    block = block.replace(
        "lastMandirReceipt = mandirReceiptFromCreatePayload(result.payload, \"seva\") || lastMandirReceipt;",
        "setLastMandirReceipt(mandirReceiptFromCreatePayload(result.payload, \"seva\") || getLastMandirReceipt());",
    )
    block = block.replace(
        "lastMandirComplianceConfig = result.payload || { enable_80g: false, enable_fcra: false };",
        "setLastMandirComplianceConfig(result.payload || { enable_80g: false, enable_fcra: false });",
    )
    block = block.replace("mandirReportState.expenses", "getMandirReportState().expenses")
    block = block.replace("mandirListState", "getMandirListState()")
    # Fix double-call if already getter-style after replace of mandirListState[kind]
    block = block.replace("getMandirListState()[kind]", "getMandirListState()[kind]")
    block = block.replace("MANDIR_LIST_PAGE_SIZE", "getMandirListPageSize()")
    block = block.replace("activeMandirWorkspace = view;", "setActiveMandirWorkspace(view);")
    block = block.replace("activeReceiptPreviewObjectUrl", "ACTIVE_RECEIPT_PREVIEW_PLACEHOLDER")
    # Restore reads/writes via getters/setters
    block = re.sub(
        r"if \(ACTIVE_RECEIPT_PREVIEW_PLACEHOLDER\) \{",
        "if (getActiveReceiptPreviewObjectUrl()) {",
        block,
    )
    block = block.replace(
        "window.URL.revokeObjectURL(ACTIVE_RECEIPT_PREVIEW_PLACEHOLDER);",
        "window.URL.revokeObjectURL(getActiveReceiptPreviewObjectUrl());",
    )
    block = block.replace(
        'ACTIVE_RECEIPT_PREVIEW_PLACEHOLDER = "";',
        "setActiveReceiptPreviewObjectUrl(\"\");",
    )
    block = block.replace(
        "ACTIVE_RECEIPT_PREVIEW_PLACEHOLDER = result.payload.object_url;",
        "setActiveReceiptPreviewObjectUrl(result.payload.object_url);",
    )
    block = block.replace(
        "receiptPreviewFrame.src = ACTIVE_RECEIPT_PREVIEW_PLACEHOLDER;",
        "receiptPreviewFrame.src = getActiveReceiptPreviewObjectUrl();",
    )
    if "ACTIVE_RECEIPT_PREVIEW_PLACEHOLDER" in block:
        raise SystemExit("unrewritten activeReceiptPreviewObjectUrl usage remains")
    return block


def main() -> None:
    if OUT.exists() and "export function renderMandirCreateForms" in OUT.read_text(encoding="utf-8"):
        print("Already extracted")
        return

    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    spans: list[tuple[int, int, str]] = []
    for name in EXPORT_FUNCS:
        start, end = find_fn_block(lines, name)
        spans.append((start, end, name))
    spans.sort(key=lambda s: s[0], reverse=True)
    chunks: dict[str, str] = {}
    for start, end, name in spans:
        chunks[name] = "".join(lines[start:end])
        del lines[start:end]

    block = "".join(chunks[name] for name in EXPORT_FUNCS)
    for name in EXPORT_FUNCS:
        block = re.sub(
            rf"(?m)^(async )?function {name}\b",
            rf"export \1function {name}",
            block,
            count=1,
        )
    block = block.replace("export export ", "export ")
    block = rewrite_block(block)

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in block and f"export async function {name}" not in block:
            raise SystemExit(f"export missing for {name}")

    text = "".join(lines)
    text = re.sub(
        r"(?ms)^// ═+\n// SECTION: MANDIR — account options / create forms / posting dialogs\n.*?^// ═+\n\n+",
        "// Mandir create forms + posting dialogs live in modules/workspaces/mandir-create-forms.js\n\n",
        text,
        count=1,
    )

    module = HEADER + block
    if not module.endswith("\n"):
        module += "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(module, encoding="utf-8", newline="\n")
    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(module.splitlines())} lines)")
    print(f"Updated {APP.relative_to(ROOT)} ({len(text.splitlines())} lines)")


if __name__ == "__main__":
    main()
