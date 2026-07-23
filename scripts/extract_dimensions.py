#!/usr/bin/env python3
"""Extract ACCOUNTING DIMENSIONS section into modules/workspaces/dimensions.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/dimensions.js"

HEADER = '''\
// ====================================================================
// SECTION: ACCOUNTING DIMENSIONS (cost centre / project)
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initDimensions(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastDimensions = null;
export let lastDimensionReport = null;
export let lastBranchConsolidatedReport = null;
export let dimensionReportType = "cost_centre";

/** @type {Record<string, Function> | null} */
let deps = null;

export function initDimensions(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initDimensions() must be called before using dimension helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function reportUnavailablePanel(title, payload) { return requireDeps().reportUnavailablePanel(title, payload); }
function rerenderBusinessReportsIfActive() { return requireDeps().rerenderBusinessReportsIfActive(); }
function downloadApiFile(appKey, path, filename, opts) { return requireDeps().downloadApiFile(appKey, path, filename, opts); }
function getApiOutput() { return requireDeps().getApiOutput(); }

'''

FUNCS = [
    "loadDimensions",
    "dimensionOptions",
    "voucherDimensionPayload",
    "createDimensionFromForm",
    "deactivateDimension",
    "loadDimensionReport",
    "loadBranchConsolidatedReport",
    "downloadDimensionReport",
    "renderDimensionsPanel",
]


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next(i for i, l in enumerate(lines) if "SECTION: ACCOUNTING DIMENSIONS" in l)
    # include the short banner line above if present
    if start >= 1 and "Accounting dimensions" in lines[start - 1]:
        start -= 1
    if start >= 1 and lines[start - 1].strip().startswith("// ----"):
        start -= 1
    end = next(i for i, l in enumerate(lines) if i > start and "SECTION: INVENTORY" in l)
    # include inventory banner separator? stop before inventory ---- comment
    if end >= 1 and lines[end - 1].strip().startswith("// ----"):
        end -= 1
    while end > start and lines[end - 1].strip() == "":
        end -= 1

    body = "".join(lines[start:end])
    # Export functions (avoid double-export)
    for name in FUNCS:
        body = re.sub(
            rf"(?m)^(async )?function {name}\b",
            rf"export \1function {name}",
            body,
            count=1,
        )
    # Fix accidental "export export"
    body = body.replace("export export ", "export ")

    # apiOutput -> getApiOutput()
    body = re.sub(r"\bapiOutput\b", "getApiOutput()", body)

    module = HEADER + body
    if not module.endswith("\n"):
        module += "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(module, encoding="utf-8", newline="\n")

    # Remove state lets from app.js clustered block
    text = "".join(lines[:start] + lines[end:])
    for decl in (
        "let lastDimensions = null;       // masters cache (also feeds the form selects)\n",
        "let lastDimensionReport = null;\n",
        "let lastBranchConsolidatedReport = null;\n",
        'let dimensionReportType = "cost_centre";\n',
    ):
        text = text.replace(decl, "", 1)

    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({module.count(chr(10))+1} lines)")
    print(f"Removed app.js lines {start+1}-{end}")


if __name__ == "__main__":
    main()
