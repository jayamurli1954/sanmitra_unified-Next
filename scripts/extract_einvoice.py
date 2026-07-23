#!/usr/bin/env python3
"""Extract E-INVOICING into modules/workspaces/einvoice.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/einvoice.js"

HEADER = '''\
// ====================================================================
// SECTION: E-INVOICING (IRN foundation, credential-free)
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initEinvoice(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastEinvoiceView = null;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initEinvoice(injected) {
  deps = injected;
}

/** Used by sales-invoices workspace (imported let binding is read-only). */
export function clearEinvoiceView() {
  lastEinvoiceView = null;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initEinvoice() must be called before using einvoice helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function rerenderSalesIfActive() { return requireDeps().rerenderSalesIfActive(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

'''

FUNCS = [
    "loadEinvoiceView",
    "downloadInv01Json",
    "recordEinvoiceIrn",
    "renderEinvoiceSection",
]


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    section = next(i for i, l in enumerate(lines) if "SECTION: E-INVOICING" in l)
    start = section
    while start > 0 and lines[start - 1].strip().startswith("// ═"):
        start -= 1

    # Stop before currentFinancialYear helper (not part of e-invoice)
    end = next(
        i
        for i, l in enumerate(lines)
        if i > section and (
            "function currentFinancialYear" in l
            or "SECTION: FINANCIAL REPORTS" in l
        )
    )
    while end > start:
        prev = lines[end - 1].strip()
        if prev == "" or prev.startswith("// Current Indian"):
            end -= 1
            continue
        break

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

    for name in FUNCS:
        if f"export function {name}" not in body and f"export async function {name}" not in body:
            raise SystemExit(f"export missing for {name}")

    module = HEADER + body
    if not module.endswith("\n"):
        module += "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(module, encoding="utf-8", newline="\n")

    text = "".join(lines[:start] + lines[end:])
    decl = "let lastEinvoiceView = null;     // e-invoice readiness/payload for the open invoice\n"
    if decl not in text:
        decl_alt = "let lastEinvoiceView = null;\n"
        if decl_alt not in text:
            raise SystemExit("missing lastEinvoiceView decl")
        text = text.replace(decl_alt, "", 1)
    else:
        text = text.replace(decl, "", 1)

    # Drop orphan blank lines left where state sat (keep one blank before next section)
    text = text.replace(
        "let yeFy = currentFinancialYear();\n\n\n\n// ═",
        "let yeFy = currentFinancialYear();\n\n\n// ═",
        1,
    )

    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({module.count(chr(10)) + 1} lines)")
    print(f"Removed app.js body {start + 1}-{end}")


if __name__ == "__main__":
    main()
