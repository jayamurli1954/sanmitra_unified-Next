#!/usr/bin/env python3
"""Extract PAYMENT ALLOCATION + AR/AP AGING into modules/workspaces/payment-allocation.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/payment-allocation.js"

HEADER = '''\
// ====================================================================
// SECTION: PAYMENT ALLOCATION + AR/AP AGING
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initPaymentAllocation(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastBusinessAging = null;

/** Payment Allocation workflow state (open-item AR/AP matching). */
export const allocationState = {
  kind: "receivable",
  selectedPaymentId: "",
  lines: {},        // open_item_id -> entered amount (string)
  busy: false,
};
export let lastUnallocatedPayments = null;
export let lastAllocationOpenItems = null;
export let lastAllocationReconciliation = null;
export let lastAllocationResult = null;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initPaymentAllocation(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initPaymentAllocation() must be called before using payment-allocation helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function reportUnavailablePanel(title, payload) { return requireDeps().reportUnavailablePanel(title, payload); }
function rerenderBusinessReportsIfActive() { return requireDeps().rerenderBusinessReportsIfActive(); }
function reportResultPayload(result, extra = {}) { return requireDeps().reportResultPayload(result, extra); }
function getBusinessReportState() { return requireDeps().getBusinessReportState(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

'''

EXPORT_FUNCS = [
    "loadBusinessAging",
    "setAgingKind",
    "loadUnallocatedPayments",
    "setAllocationKind",
    "selectAllocationPayment",
    "setAllocationLineAmount",
    "applyFifoSuggestion",
    "submitAllocation",
    "loadAllocationReconciliation",
    "kindToggle",
    "renderBusinessAging",
    "renderPaymentAllocation",
]


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)

    # Block A: aging/allocation loaders (stop before loadBusinessGeneralLedger)
    a_start = next(i for i, l in enumerate(lines) if "SECTION: PAYMENT ALLOCATION + AR/AP AGING" in l)
    while a_start > 0 and (
        lines[a_start - 1].strip().startswith("// ═")
        or "AR/AP Aging" in lines[a_start - 1]
        or lines[a_start - 1].strip().startswith("// ----")
        or lines[a_start - 1].strip() == ""
    ):
        a_start -= 1
        if lines[a_start].strip().startswith("// ----") and "AR/AP Aging" in lines[a_start]:
            break

    a_end = next(i for i, l in enumerate(lines) if i > a_start and "async function loadBusinessGeneralLedger" in l)
    while a_end > a_start and lines[a_end - 1].strip() == "":
        a_end -= 1

    # Block B: kindToggle + aging/allocation renderers (stop before setBusinessReportTab)
    b_start = next(i for i, l in enumerate(lines) if "function kindToggle(" in l)
    # Include the comment above kindToggle if present
    if b_start > 0 and "Kind toggle" in lines[b_start - 1]:
        b_start -= 1
    b_end = next(i for i, l in enumerate(lines) if i > b_start and "function setBusinessReportTab" in l)
    while b_end > b_start and lines[b_end - 1].strip() == "":
        b_end -= 1

    body = "".join(lines[a_start:a_end] + ["\n"] + lines[b_start:b_end])
    body = body.replace("businessReportState", "getBusinessReportState()")
    # Avoid rewriting object keys accidentally — businessReportState only used as identifier access
    # Fix double-call if any: getBusinessReportState()() — shouldn't happen
    body = re.sub(r"getBusinessReportState\(\)\(\)", "getBusinessReportState()", body)

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

    # Remove later block first so indices for earlier block stay valid... actually we use slices:
    # remove b then a (higher index first)
    new_lines = lines[:b_start] + lines[b_end:]
    # Recompute a_start/a_end on original — if b was after a, a indices unchanged when we only remove b first from copy
    text_lines = lines[:a_start] + lines[a_end:b_start] + lines[b_end:]
    text = "".join(text_lines)

    # Remove state decls
    state_block = '''\
let lastBusinessAging = null;

// Payment Allocation workflow state (open-item AR/AP matching).
const allocationState = {
  kind: "receivable",
  selectedPaymentId: "",
  lines: {},        // open_item_id -> entered amount (string)
  busy: false,
};
let lastUnallocatedPayments = null;
let lastAllocationOpenItems = null;
let lastAllocationReconciliation = null;
let lastAllocationResult = null;

'''
    if state_block not in text:
        # try without blank line variants
        raise SystemExit("allocation state block not found for removal")
    text = text.replace(state_block, "", 1)

    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({module.count(chr(10)) + 1} lines)")
    print(f"Removed loaders {a_start + 1}-{a_end}; renderers {b_start + 1}-{b_end}")


if __name__ == "__main__":
    main()
