#!/usr/bin/env python3
"""Extract INVENTORY section into modules/workspaces/inventory.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/inventory.js"

HEADER = '''\
// ====================================================================
// SECTION: INVENTORY (opt-in, periodic method)
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initInventory(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastInventoryItems = null;
export let lastStockRegister = null;
export let lastClosingStockEntries = null;
export let lastInventoryPolicy = null;
export let lastStockMovements = null;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initInventory(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initInventory() must be called before using inventory helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function todayIsoDate() { return requireDeps().todayIsoDate(); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function reportUnavailablePanel(title, payload) { return requireDeps().reportUnavailablePanel(title, payload); }
function rerenderBusinessReportsIfActive() { return requireDeps().rerenderBusinessReportsIfActive(); }
function isBusinessAdmin() { return requireDeps().isBusinessAdmin(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

'''

FUNCS = [
    "loadInventoryItems",
    "inventoryItemOptions",
    "inventoryMovementItemOptions",
    "createInventoryItemFromForm",
    "deactivateInventoryItem",
    "loadInventoryPolicy",
    "loadStockMovements",
    "createStockMovementFromForm",
    "loadStockRegister",
    "loadClosingStockEntries",
    "postClosingStock",
    "renderInventoryPanel",
]


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next(i for i, l in enumerate(lines) if "SECTION: INVENTORY" in l)
    if start >= 1 and lines[start - 1].strip().startswith("// ----"):
        start -= 1
    # drop stale fixed-assets leftover banner if present
    if start >= 1 and "Fixed assets" in lines[start - 1]:
        start -= 1
        if start >= 1 and lines[start - 1].strip().startswith("// ----"):
            start -= 1

    end = next(i for i, l in enumerate(lines) if i > start and "SECTION: CUSTOMER STATEMENTS" in l)
    while end > start and (
        lines[end - 1].strip().startswith("// ----")
        or "Customer/vendor statements" in lines[end - 1]
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

    module = HEADER + body
    if not module.endswith("\n"):
        module += "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(module, encoding="utf-8", newline="\n")

    text = "".join(lines[:start] + lines[end:])
    for decl in (
        "let lastInventoryItems = null;   // item master cache (also feeds the line selects)\n",
        "let lastStockRegister = null;\n",
        "let lastClosingStockEntries = null;\n",
        "let lastInventoryPolicy = null;\n",
        "let lastStockMovements = null;\n",
    ):
        text = text.replace(decl, "", 1)

    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({module.count(chr(10))+1} lines)")
    print(f"Removed app.js lines {start+1}-{end}")


if __name__ == "__main__":
    main()
