"""Extract GST returns cluster from mitrabooks-erp/app.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "mitrabooks-erp" / "app.js"
OUT = ROOT / "frontend" / "mitrabooks-erp" / "modules" / "workspaces" / "gst-returns.js"

# 1-based inclusive line ranges in current app.js
SETTLEMENT_THROUGH_CMP08 = (6818, 7365)
GSTR1_BLOCK = (9104, 9215)

STATE_REPLACEMENTS = [
    ("lastGstr2bRecon", "gstReturnState.lastGstr2bRecon"),
    ("lastGstSettlement", "gstReturnState.lastGstSettlement"),
    ("gstSettlementPeriod", "gstReturnState.gstSettlementPeriod"),
    ("lastGstr3b", "gstReturnState.lastGstr3b"),
    ("lastGstr1", "gstReturnState.lastGstr1"),
    ("lastCmp08", "gstReturnState.lastCmp08"),
    ("lastGstr4", "gstReturnState.lastGstr4"),
    ("gstReturnType", "gstReturnState.gstReturnType"),
    ("gstr3bPeriod", "gstReturnState.gstr3bPeriod"),
    ("cmp08Quarter", "gstReturnState.cmp08Quarter"),
    ("gstr4Fy", "gstReturnState.gstr4Fy"),
]

EXPORT_NAMES = [
    "loadGstSettlementPreview",
    "previewGstSettlementFromInput",
    "postGstSettlement",
    "renderGstSettlementPanel",
    "loadGstr3b",
    "previewGstr3bFromInput",
    "downloadGstr3bJson",
    "renderGstr3bPanel",
    "renderGstReturns",
    "reconcileGstr2b",
    "renderGstr2bPanel",
    "loadGstr4",
    "previewGstr4FromInput",
    "downloadGstr4Json",
    "renderGstr4Panel",
    "loadCmp08",
    "previewCmp08FromInput",
    "downloadCmp08Json",
    "renderCmp08Panel",
    "postCmp08Liability",
    "loadGstr1",
    "previewGstr1FromInput",
    "downloadGstr1Json",
    "renderGstr1Panel",
]

HEADER = '''// ====================================================================
// SECTION: GST RETURNS — settlement, GSTR-1/3B/2B/4, CMP-08
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initGstReturns(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export const gstReturnState = {
  lastGstSettlement: null,
  gstSettlementPeriod: "",
  lastGstr3b: null,
  lastGstr1: null,
  lastCmp08: null,
  lastGstr4: null,
  lastGstr2bRecon: null,
  gstReturnType: "gstr3b",
  gstr3bPeriod: "",
  cmp08Quarter: "",
  gstr4Fy: "",
};

/** @type {{
 *   escapeHtml: (v: string) => string,
 *   formatCurrency: (v: number | string) => string,
 *   setLoginStatus: (kind: string, title: string, detail?: string) => void,
 *   statusDetailText: (detail: unknown) => string,
 *   rerenderBusinessReportsIfActive: () => void,
 *   isBusinessAdmin: () => boolean,
 *   reportUnavailablePanel: (title: string, payload: unknown) => string,
 *   todayIsoDate: () => string,
 *   currentFinancialYear: () => string,
 *   currentFyQuarter: () => string,
 *   recentFinancialYears: (count?: number) => string[],
 *   recentFyQuarters: (count?: number) => string[],
 *   getApiOutput: () => HTMLElement | null,
 * } | null} */
let deps = null;

export function initGstReturns({
  escapeHtml,
  formatCurrency,
  setLoginStatus,
  statusDetailText,
  rerenderBusinessReportsIfActive,
  isBusinessAdmin,
  reportUnavailablePanel,
  todayIsoDate,
  currentFinancialYear,
  currentFyQuarter,
  recentFinancialYears,
  recentFyQuarters,
  getApiOutput,
}) {
  deps = {
    escapeHtml,
    formatCurrency,
    setLoginStatus,
    statusDetailText,
    rerenderBusinessReportsIfActive,
    isBusinessAdmin,
    reportUnavailablePanel,
    todayIsoDate,
    currentFinancialYear,
    currentFyQuarter,
    recentFinancialYears,
    recentFyQuarters,
    getApiOutput,
  };
  gstReturnState.gstSettlementPeriod = todayIsoDate().slice(0, 7);
  gstReturnState.gstr3bPeriod = todayIsoDate().slice(0, 7);
  gstReturnState.cmp08Quarter = currentFyQuarter();
  gstReturnState.gstr4Fy = currentFinancialYear();
}

function requireDeps() {
  if (!deps) {
    throw new Error("initGstReturns() must be called before using GST return helpers");
  }
  return deps;
}

function escapeHtml(value) {
  return requireDeps().escapeHtml(value);
}

function formatCurrency(value) {
  return requireDeps().formatCurrency(value);
}

function setLoginStatus(kind, title, detail = "") {
  requireDeps().setLoginStatus(kind, title, detail);
}

function statusDetailText(detail) {
  return requireDeps().statusDetailText(detail);
}

function rerenderBusinessReportsIfActive() {
  requireDeps().rerenderBusinessReportsIfActive();
}

function isBusinessAdmin() {
  return requireDeps().isBusinessAdmin();
}

function reportUnavailablePanel(title, payload) {
  return requireDeps().reportUnavailablePanel(title, payload);
}

function recentFinancialYears(count = 4) {
  return requireDeps().recentFinancialYears(count);
}

function recentFyQuarters(count = 6) {
  return requireDeps().recentFyQuarters(count);
}

function getApiOutput() {
  return requireDeps().getApiOutput();
}

'''


def slice_lines(lines: list[str], start: int, end: int) -> str:
    return "".join(lines[start - 1 : end])


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    body = slice_lines(lines, *SETTLEMENT_THROUGH_CMP08) + "\n" + slice_lines(lines, *GSTR1_BLOCK)
    for old, new in STATE_REPLACEMENTS:
        body = re.sub(rf"\b{old}\b", new, body)
    body = body.replace("renderJson(apiOutput,", "renderJson(getApiOutput(),")
    for name in EXPORT_NAMES:
        body = body.replace(f"async function {name}", f"export async function {name}")
        body = body.replace(f"function {name}", f"export function {name}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(HEADER + body, encoding="utf-8")
    print(f"Wrote {OUT} ({sum(1 for _ in OUT.open(encoding='utf-8'))} lines)")


if __name__ == "__main__":
    main()
