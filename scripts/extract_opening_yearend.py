#!/usr/bin/env python3
"""Extract OPENING BALANCES + YEAR-END CLOSE into modules/workspaces/opening-yearend.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/opening-yearend.js"

HEADER = '''\
// ====================================================================
// SECTION: OPENING BALANCES + YEAR-END CLOSE (+ bulk voucher import)
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initOpeningYearEnd(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastObPreview = null;
export let obCsvText = "";
export let lastViPreview = null;
export let viCsvText = "";
export let lastYePreview = null;
export let yeFy = "";

/** @type {Record<string, Function> | null} */
let deps = null;

export function initOpeningYearEnd(injected) {
  deps = injected;
  if (!yeFy) {
    yeFy = deps.currentFinancialYear();
  }
}

function requireDeps() {
  if (!deps) {
    throw new Error("initOpeningYearEnd() must be called before using opening/year-end helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function reportUnavailablePanel(title, payload) { return requireDeps().reportUnavailablePanel(title, payload); }
function rerenderBusinessReportsIfActive() { return requireDeps().rerenderBusinessReportsIfActive(); }
function isBusinessAdmin() { return requireDeps().isBusinessAdmin(); }
function recentFinancialYears(count = 4) { return requireDeps().recentFinancialYears(count); }
function downloadApiFile(appKey, path, filename, options) { return requireDeps().downloadApiFile(appKey, path, filename, options); }
function getApiOutput() { return requireDeps().getApiOutput(); }

'''

EXPORT_FUNCS = [
    "downloadObTemplate",
    "previewOpeningBalances",
    "postOpeningBalances",
    "downloadObExport",
    "downloadViTemplate",
    "previewBulkVouchers",
    "postBulkVouchers",
    "previewYearEnd",
    "postYearEndClose",
    "renderOpeningBalancesSection",
    "renderBulkImportVouchersSection",
    "renderYearEndSection",
    "renderOpeningYearEndPanel",
]


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next(i for i, l in enumerate(lines) if "async function downloadObTemplate" in l)
    end = next(
        i
        for i, l in enumerate(lines)
        if i > start and "function rerenderBusinessReportsIfActive" in l
    )
    while end > start and lines[end - 1].strip() == "":
        end -= 1

    body = "".join(lines[start:end])
    for name in EXPORT_FUNCS:
        body = re.sub(
            rf"(?m)^(async )?function {name}\b",
            rf"export \1function {name}",
            body,
            count=1,
        )
    body = body.replace("export export ", "export ")
    body = re.sub(r"\bapiOutput\b", "getApiOutput()", body)

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in body and f"export async function {name}" not in body:
            raise SystemExit(f"export missing for {name}")
    if "function rerenderBusinessReportsIfActive" in body:
        raise SystemExit("must not move rerenderBusinessReportsIfActive")

    module = HEADER + body
    if not module.endswith("\n"):
        module += "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(module, encoding="utf-8", newline="\n")

    text = "".join(lines[:start] + lines[end:])
    for decl in (
        "let lastObPreview = null;\n",
        'let obCsvText = "";\n',
        "let lastViPreview = null;\n",
        'let viCsvText = "";\n',
        "let lastYePreview = null;\n",
        "let yeFy = currentFinancialYear();\n",
    ):
        if decl not in text:
            raise SystemExit(f"missing decl to remove: {decl!r}")
        text = text.replace(decl, "", 1)

    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({module.count(chr(10)) + 1} lines)")
    print(f"Removed app.js body {start + 1}-{end}")


if __name__ == "__main__":
    main()
