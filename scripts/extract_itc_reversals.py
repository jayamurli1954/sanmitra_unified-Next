#!/usr/bin/env python3
"""Extract ITC REVERSALS into modules/workspaces/itc-reversals.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/itc-reversals.js"

HEADER = '''\
// ====================================================================
// SECTION: ITC REVERSALS (Rule 37 / Re-claim)
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initItcReversals(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastItcReversal = null;
export let lastItcReversedBills = [];
export let itcReversalAsOf = "";

/** @type {Record<string, Function> | null} */
let deps = null;

export function initItcReversals(injected) {
  deps = injected;
  if (!itcReversalAsOf) {
    itcReversalAsOf = deps.todayIsoDate();
  }
}

function requireDeps() {
  if (!deps) {
    throw new Error("initItcReversals() must be called before using ITC reversal helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function rerenderBusinessReportsIfActive() { return requireDeps().rerenderBusinessReportsIfActive(); }
function isBusinessAdmin() { return requireDeps().isBusinessAdmin(); }
function todayIsoDate() { return requireDeps().todayIsoDate(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

'''

EXPORT_FUNCS = [
    "loadItcReversalPreview",
    "previewItcReversalsFromInput",
    "reverseItcForBill",
    "reclaimItcForBill",
    "markBillPaidFull",
    "renderItcReversalPanel",
]


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    section = next(i for i, l in enumerate(lines) if "SECTION: ITC REVERSALS" in l)
    start = section
    while start > 0 and lines[start - 1].strip().startswith("// ═"):
        start -= 1

    # Stop before loadPeriodLocks (belongs with GST period locks) or SECTION: GST PERIOD LOCKS
    end = next(
        i
        for i, l in enumerate(lines)
        if i > section
        and (
            "async function loadPeriodLocks" in l
            or "SECTION: GST PERIOD LOCKS" in l
        )
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

    module = HEADER + body
    if not module.endswith("\n"):
        module += "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(module, encoding="utf-8", newline="\n")

    text = "".join(lines[:start] + lines[end:])
    for decl in (
        "let lastItcReversal = null;\n",
        "let lastItcReversedBills = [];\n",
        "let itcReversalAsOf = todayIsoDate();\n",
    ):
        if decl not in text:
            raise SystemExit(f"missing decl to remove: {decl!r}")
        text = text.replace(decl, "", 1)

    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({module.count(chr(10)) + 1} lines)")
    print(f"Removed app.js body {start + 1}-{end}")


if __name__ == "__main__":
    main()
