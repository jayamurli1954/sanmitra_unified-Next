#!/usr/bin/env python3
"""Extract FIXED ASSETS + DEPRECIATION into modules/workspaces/fixed-assets.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/fixed-assets.js"

HEADER = '''\
// ====================================================================
// SECTION: FIXED ASSETS + DEPRECIATION
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initFixedAssets(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastFixedAssets = null;
export let lastDepPreview = null;
export let depFy = "";
export let faFormOpen = false;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initFixedAssets(injected) {
  deps = injected;
  if (!depFy) {
    depFy = injected.currentFinancialYear();
  }
}

/** Used by app.js event-handler deps setters (imported binding is read-only). */
export function setFaFormOpen(value) {
  faFormOpen = !!value;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initFixedAssets() must be called before using fixed-asset helpers");
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
function businessAccountsForSelection() { return requireDeps().businessAccountsForSelection(); }
function bankAccountOptions() { return requireDeps().bankAccountOptions(); }
function isBusinessAdmin() { return requireDeps().isBusinessAdmin(); }
function recentFinancialYears(count) { return requireDeps().recentFinancialYears(count); }
function getApiOutput() { return requireDeps().getApiOutput(); }

'''

FUNCS = [
    "fixedAssetAccountOptions",
    "loadFixedAssets",
    "createFixedAssetFromForm",
    "previewDepreciation",
    "postDepreciationRun",
    "disposeFixedAsset",
    "renderFixedAssetForm",
    "renderFixedAssetsPanel",
]


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next(i for i, l in enumerate(lines) if "SECTION: FIXED ASSETS + DEPRECIATION" in l)
    if start >= 1 and "Fixed assets" in lines[start - 1]:
        start -= 1
    if start >= 1 and lines[start - 1].strip().startswith("// ----"):
        start -= 1
    end = next(i for i, l in enumerate(lines) if i > start and "SECTION: INVENTORY" in l)
    # drop stale dimensions leftover banner if present before inventory
    while end > start and (
        "Accounting dimensions" in lines[end - 1]
        or lines[end - 1].strip().startswith("// ----")
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
        "let lastFixedAssets = null;\n",
        "let lastDepPreview = null;\n",
        "let depFy = currentFinancialYear();\n",
        "let faFormOpen = false;\n",
    ):
        text = text.replace(decl, "", 1)

    # Fix event-handler setter to use setFaFormOpen (import is read-only)
    text = text.replace(
        "set faFormOpen(v) { faFormOpen = v; },",
        "set faFormOpen(v) { setFaFormOpen(v); },",
        1,
    )

    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({module.count(chr(10))+1} lines)")
    print(f"Removed app.js lines {start+1}-{end}")


if __name__ == "__main__":
    main()
