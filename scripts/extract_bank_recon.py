#!/usr/bin/env python3
"""Extract BANK RECONCILIATION (+ bank/cash book) into modules/workspaces/bank-recon.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/bank-recon.js"

HEADER = '''\
// ====================================================================
// SECTION: BANK RECONCILIATION (+ bank/cash book)
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initBankRecon(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastBankRecon = null;
export let bankReconAccountId = "";
export let lastBankCashBook = null;
export let bankCashBookType = "all";

/** @type {Record<string, Function> | null} */
let deps = null;

export function initBankRecon(injected) {
  deps = injected;
}

/** Used by app.js report filters (imported let binding is read-only). */
export function setBankCashBookType(value) {
  bankCashBookType = String(value || "all");
}

function requireDeps() {
  if (!deps) {
    throw new Error("initBankRecon() must be called before using bank-recon helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function reportUnavailablePanel(title, payload) { return requireDeps().reportUnavailablePanel(title, payload); }
function rerenderBusinessReportsIfActive() { return requireDeps().rerenderBusinessReportsIfActive(); }
function businessAccountsForSelection() { return requireDeps().businessAccountsForSelection(); }
function renderStatCards(stats) { return requireDeps().renderStatCards(stats); }
function getBusinessReportState() { return requireDeps().getBusinessReportState(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

'''

FUNCS = [
    "bankAccountOptions",
    "loadBankCashBook",
    "loadBankReconciliation",
    "uploadBankStatementFile",
    "confirmBankReconMatch",
    "reverseBankReconMatch",
    "renderBankCashBookPanel",
    "postBankReconStatementVoucher",
    "renderBankReconPanel",
]


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next(i for i, l in enumerate(lines) if "SECTION: BANK RECONCILIATION" in l)
    if start >= 1 and lines[start - 1].strip().startswith("// ----"):
        start -= 1

    end = next(i for i, l in enumerate(lines) if i > start and "SECTION: TDS" in l)
    while end > start and (
        lines[end - 1].strip().startswith("// ----")
        or "TDS / TCS" in lines[end - 1]
        or lines[end - 1].strip() == ""
    ):
        end -= 1

    body = "".join(lines[start:end])
    for name in FUNCS:
        body = re.sub(
            rf"(?m)^(async )?function {name}\b",
            rf"export \1function {name}",
            body,
            count=1,
        )
    body = body.replace("export export ", "export ")
    body = re.sub(r"\bapiOutput\b", "getApiOutput()", body)
    # businessReportState.x -> getBusinessReportState().x
    body = re.sub(r"\bbusinessReportState\b", "getBusinessReportState()", body)

    module = HEADER + body
    if not module.endswith("\n"):
        module += "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(module, encoding="utf-8", newline="\n")

    text = "".join(lines[:start] + lines[end:])
    for decl in (
        "let lastBankRecon = null;\n",
        'let bankReconAccountId = "";\n',
        "let lastBankCashBook = null;\n",
        'let bankCashBookType = "all";\n',
    ):
        text = text.replace(decl, "", 1)

    # External assignment in applyBusinessReportFilter
    text = text.replace(
        "if (bookType && bookType.value) bankCashBookType = bookType.value;",
        "if (bookType && bookType.value) setBankCashBookType(bookType.value);",
        1,
    )

    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({module.count(chr(10))+1} lines)")
    print(f"Removed app.js lines {start+1}-{end}")


if __name__ == "__main__":
    main()
