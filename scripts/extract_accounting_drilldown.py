#!/usr/bin/env python3
"""Extract Accounting Drilldown into modules/workspaces/accounting-drilldown.js (Phase 3 seam 36)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/accounting-drilldown.js"

HEADER = '''\
// ====================================================================
// SECTION: ACCOUNTING DRILLDOWN (shared MandirMitra + MitraBooks)
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initAccountingDrilldown(...).
// API: GET /api/v1/accounting/reports/drilldown and voucher detail.
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

const todayForReports = new Date();
const firstDayForReports = new Date(todayForReports.getFullYear(), todayForReports.getMonth(), 1);

export let accountingDrilldownState = {
  level: "month",
  from_date: firstDayForReports.toISOString().slice(0, 10),
  to_date: todayForReports.toISOString().slice(0, 10),
  month: "",
  week_start: "",
  day: "",
};
export let lastAccountingDrilldown = null;
export let lastAccountingVoucherDetail = null;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initAccountingDrilldown(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initAccountingDrilldown() must be called before using accounting drilldown helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function buildQueryString(params) { return requireDeps().buildQueryString(params); }
function getActiveAppKey() { return requireDeps().getActiveAppKey(); }
function getApiOutput() { return requireDeps().getApiOutput(); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function getExperienceConfig() { return requireDeps().getExperienceConfig(); }
function renderDashboardPreview(config) { return requireDeps().renderDashboardPreview(config); }
function loadMandirDashboard() { return requireDeps().loadMandirDashboard(); }

export function setLastAccountingDrilldown(value) {
  lastAccountingDrilldown = value;
}

export function setLastAccountingVoucherDetail(value) {
  lastAccountingVoucherDetail = value;
}

export function setAccountingDrilldownState(value) {
  accountingDrilldownState = value;
}

'''

EXPORT_FUNCS = [
    "accountingDrilldownTitle",
    "renderAccountingDrilldownRows",
    "renderAccountingVoucherDetail",
    "renderAccountingDrilldownPanel",
    "accountingDrilldownPath",
    "loadAccountingDrilldownResult",
    "loadAccountingVoucherDetail",
    "readAccountingDrilldownFilterValues",
    "refreshCurrentAccountingDrilldown",
    "applyAccountingDrilldownFilters",
    "resetAccountingDrilldown",
    "drillAccountingReport",
    "openAccountingVoucherDetail",
]


def find_fn_block(lines: list[str], signature: str) -> tuple[int, int]:
    start = next(
        i
        for i, l in enumerate(lines)
        if signature in l and l.lstrip().startswith(("function ", "async function "))
    )
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


def extract_blocks(lines: list[str], names: list[str]) -> tuple[str, list[str]]:
    spans: list[tuple[int, int, str]] = []
    for name in names:
        start, end = find_fn_block(lines, f"function {name}")
        spans.append((start, end, name))
    spans.sort(key=lambda s: s[0], reverse=True)
    chunks: dict[str, str] = {}
    for start, end, name in spans:
        chunks[name] = "".join(lines[start:end])
        del lines[start:end]
    return "".join(chunks[name] for name in names), lines


def rewrite_shell_refs(block: str) -> str:
    """Replace app.js shell identifiers with deps-backed locals."""
    # Order matters: longer / more specific first.
    replacements = [
        (
            "EXPERIENCE_APP_KEYS[currentExperience] || APP_KEY",
            "getActiveAppKey()",
        ),
        (
            "renderDashboardPreview(experienceConfig[currentExperience])",
            "renderDashboardPreview(getExperienceConfig()[getCurrentExperience()])",
        ),
        ("renderJson(apiOutput,", "renderJson(getApiOutput(),"),
        ("dashboardPreview.", "getDashboardPreview()."),
        ("currentExperience", "getCurrentExperience()"),
        ("activeBusinessWorkspace", "getActiveBusinessWorkspace()"),
    ]
    for old, new in replacements:
        block = block.replace(old, new)
    return block


def main() -> None:
    if OUT.exists() and "export function renderAccountingDrilldownPanel" in OUT.read_text(encoding="utf-8"):
        print("Already extracted")
        return

    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    block, lines = extract_blocks(lines, EXPORT_FUNCS)

    for name in EXPORT_FUNCS:
        block = re.sub(
            rf"(?m)^(async )?function {name}\b",
            rf"export \1function {name}",
            block,
            count=1,
        )
    block = block.replace("export export ", "export ")
    block = rewrite_shell_refs(block)

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in block and f"export async function {name}" not in block:
            raise SystemExit(f"export missing for {name}")

    text = "".join(lines)
    # Drop orphaned SECTION banners for drilldown
    text = re.sub(
        r"(?ms)^// ═+\n// SECTION: ACCOUNTING DRILLDOWN \(shared MandirMitra \+ MitraBooks\)\n.*?^// ═+\n\n+",
        "",
        text,
        count=1,
    )
    # Remove moved state declarations (keep today/firstDay only if still used — they won't be)
    text, n1 = re.subn(
        r"(?m)^const todayForReports = new Date\(\);\n"
        r"const firstDayForReports = new Date\(todayForReports\.getFullYear\(\), todayForReports\.getMonth\(\), 1\);\n"
        r"let accountingDrilldownState = \{\n"
        r"  level: \"month\",\n"
        r"  from_date: firstDayForReports\.toISOString\(\)\.slice\(0, 10\),\n"
        r"  to_date: todayForReports\.toISOString\(\)\.slice\(0, 10\),\n"
        r"  month: \"\",\n"
        r"  week_start: \"\",\n"
        r"  day: \"\",\n"
        r"\};\n"
        r"let lastAccountingDrilldown = null;\n"
        r"let lastAccountingVoucherDetail = null;\n",
        "",
        text,
        count=1,
    )
    if n1 != 1:
        raise SystemExit(f"state removal failed n1={n1}")

    # External clears in app.js
    text = text.replace(
        "lastAccountingDrilldown = null;",
        "setLastAccountingDrilldown(null);",
    )

    module = HEADER + block
    if not module.endswith("\n"):
        module += "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(module, encoding="utf-8", newline="\n")
    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(module.splitlines())} lines)")
    print(f"Updated {APP.relative_to(ROOT)} ({len(text.splitlines())} lines)")


if __name__ == "__main__":
    main()
