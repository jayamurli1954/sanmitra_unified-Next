#!/usr/bin/env python3
"""Extract core MitraBooks financial report loaders/renderers into financial-reports.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/financial-reports.js"

HEADER = '''\
// ====================================================================
// SECTION: FINANCIAL REPORTS (TB / P&L / BS / GL / R&P)
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initFinancialReports(...).
// Hub (refreshCurrentBusinessReport / renderBusinessReportsWorkspace) stays in app.js.
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastBusinessTrialBalance = null;
export let lastBusinessProfitLoss = null;
export let lastBusinessBalanceSheet = null;
export let lastBusinessReceivables = null;
export let lastBusinessPayables = null;
export let lastBusinessGeneralLedger = null;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initFinancialReports(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initFinancialReports() must be called before using financial-report helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function reportUnavailablePanel(title, payload) { return requireDeps().reportUnavailablePanel(title, payload); }
function reportResultPayload(result, extra = {}) { return requireDeps().reportResultPayload(result, extra); }
function rerenderBusinessReportsIfActive() { return requireDeps().rerenderBusinessReportsIfActive(); }
function findBusinessAccountById(accountId) { return requireDeps().findBusinessAccountById(accountId); }
function accountRowsFromPayload(payload) { return requireDeps().accountRowsFromPayload(payload); }
function businessAccountsForSelection() { return requireDeps().businessAccountsForSelection(); }
function renderStatCards(stats) { return requireDeps().renderStatCards(stats); }
function isBusinessReportTab(tab) { return requireDeps().isBusinessReportTab(tab); }
function setBankCashBookType(value) { return requireDeps().setBankCashBookType(value); }
function getBankCashBookType() { return requireDeps().getBankCashBookType(); }
function getBusinessReportState() { return requireDeps().getBusinessReportState(); }
function refreshCurrentBusinessReport() { return requireDeps().refreshCurrentBusinessReport(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

'''

EXPORT_FUNCS = [
    "loadBusinessTrialBalance",
    "loadBusinessProfitLoss",
    "loadBusinessBalanceSheet",
    "loadBusinessReceivablesPayables",
    "loadBusinessGeneralLedger",
    "reportDateControls",
    "renderBusinessTrialBalance",
    "renderBusinessProfitLoss",
    "renderBusinessBalanceSheet",
    "renderBusinessGeneralLedger",
    "renderLedgerTraceTable",
    "loadBusinessAllLedgers",
    "renderReceivablesPayablesSection",
    "renderBusinessReceivablesPayables",
    "setBusinessReportTab",
    "applyBusinessReportFilter",
    "loadBusinessReportLedgerFromSelect",
]

STATE_NAMES = [
    "lastBusinessTrialBalance",
    "lastBusinessProfitLoss",
    "lastBusinessBalanceSheet",
    "lastBusinessReceivables",
    "lastBusinessPayables",
    "lastBusinessGeneralLedger",
]


def find_fn_block(lines: list[str], signature: str) -> tuple[int, int]:
    start = next(i for i, l in enumerate(lines) if signature in l and l.lstrip().startswith(("function ", "async function ")))
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
        raise SystemExit(f"unterminated function for {signature}")
    while end < len(lines) and lines[end].strip() == "":
        end += 1
    return start, end


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)

    sigs = [
        "async function loadBusinessTrialBalance",
        "async function loadBusinessProfitLoss",
        "async function loadBusinessBalanceSheet",
        "async function loadBusinessReceivablesPayables",
        "async function loadBusinessGeneralLedger",
        "function reportDateControls",
        "function renderBusinessTrialBalance",
        "function renderBusinessProfitLoss",
        "function renderBusinessBalanceSheet",
        "function renderBusinessGeneralLedger",
        "function renderLedgerTraceTable",
        "async function loadBusinessAllLedgers",
        "function renderReceivablesPayablesSection",
        "function renderBusinessReceivablesPayables",
        "function setBusinessReportTab",
        "function applyBusinessReportFilter",
        "function loadBusinessReportLedgerFromSelect",
    ]
    blocks = [find_fn_block(lines, s) for s in sigs]

    body_parts = ["".join(lines[s:e]) for s, e in blocks]
    body = "\n".join(body_parts)
    for name in EXPORT_FUNCS:
        body = re.sub(
            rf"(?m)^(async )?function {name}\b",
            rf"export \1function {name}",
            body,
            count=1,
        )
    body = body.replace("export export ", "export ")

    # Live state + DOM refs via deps
    body = re.sub(r"\bapiOutput\b", "getApiOutput()", body)
    body = re.sub(r"\bbusinessReportState\b", "getBusinessReportState()", body)
    body = re.sub(r"\bbankCashBookType\b", "getBankCashBookType()", body)
    # setBusinessReportTab validates against BUSINESS_REPORT_TABS
    body = body.replace(
        "if (!BUSINESS_REPORT_TABS.some((t) => t.id === tab)) {",
        "if (!isBusinessReportTab(tab)) {",
    )

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in body and f"export async function {name}" not in body:
            raise SystemExit(f"export missing for {name}")

    module = HEADER + body
    if not module.endswith("\n"):
        module += "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(module, encoding="utf-8", newline="\n")

    # Remove extracted blocks from app.js (highest index first)
    remove_ranges = sorted(blocks, key=lambda t: t[0], reverse=True)
    for start, end in remove_ranges:
        del lines[start:end]

    # Remove state declarations now owned by the module
    text = "".join(lines)
    for name in STATE_NAMES:
        text, n = re.subn(rf"(?m)^let {name} = null;\n", "", text, count=1)
        if n != 1:
            raise SystemExit(f"failed to remove state {name} n={n}")

    # Drop the now-empty FINANCIAL REPORT LOADERS section banner if orphaned
    text = re.sub(
        r"\n// ═{10,}\n// SECTION: FINANCIAL REPORT LOADERS \(TB / P&L / BS / R&P\)\n"
        r"// API[^\n]*\n// NOTE[^\n]*\n// ═{10,}\n+",
        "\n",
        text,
        count=1,
    )

    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(module.splitlines())} lines)")
    print(f"Updated {APP.relative_to(ROOT)} ({len(text.splitlines())} lines)")


if __name__ == "__main__":
    main()
