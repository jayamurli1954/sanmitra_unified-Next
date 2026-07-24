#!/usr/bin/env python3
"""Extract platform dashboard + dashboard preview shell (Phase 3 seam 54)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/dashboard-preview-shell.js"

HEADER = '''\
// ====================================================================
// SECTION: PLATFORM DASHBOARD + DASHBOARD PREVIEW SHELL
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initDashboardPreviewShell(...).
// Shared formatCurrency / formatCountLabel remain in app.js.
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

export function initDashboardPreviewShell(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initDashboardPreviewShell() must be called before using dashboard preview helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function formatCountMap(value) { return requireDeps().formatCountMap(value); }
function renderStatCards(stats) { return requireDeps().renderStatCards(stats); }
function renderActivity(items) { return requireDeps().renderActivity(items); }
function renderPlatformTable(...args) { return requireDeps().renderPlatformTable(...args); }
function renderPendingApprovalsTable(rows) { return requireDeps().renderPendingApprovalsTable(rows); }
function getActivePlatformWorkspace() { return requireDeps().getActivePlatformWorkspace(); }
function getLastPlatformOwnerDashboard() { return requireDeps().getLastPlatformOwnerDashboard(); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getLastGruhaData() { return requireDeps().getLastGruhaData(); }
function getLastBusinessDashboardStats() { return requireDeps().getLastBusinessDashboardStats(); }
function activeOrgSelectorType(...args) { return requireDeps().activeOrgSelectorType(...args); }
function renderGruhaDashboard(...args) { return requireDeps().renderGruhaDashboard(...args); }
function renderBusinessWorkspace(...args) { return requireDeps().renderBusinessWorkspace(...args); }
function renderSelectedOrgWorkspace(...args) { return requireDeps().renderSelectedOrgWorkspace(...args); }
function renderBusinessExecutiveDashboard(...args) { return requireDeps().renderBusinessExecutiveDashboard(...args); }

'''

EXPORT_FUNCS = [
    "renderRecentTenantsTable",
    "renderPlatformRecentOnboardingTable",
    "renderPlatformSubscriptionsTable",
    "emptyPlatformDashboardPayload",
    "renderPlatformDashboard",
    "renderDashboardPreview",
]


def find_fn_block(lines: list[str], name: str) -> tuple[int, int]:
    start = next(
        i
        for i, l in enumerate(lines)
        if re.match(rf"^(async )?function {re.escape(name)}\b", l.lstrip())
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
        raise SystemExit(f"unterminated function for {name}")
    while end < len(lines) and lines[end].strip() == "":
        end += 1
    return start, end


def rewrite_block(block: str) -> str:
    block = block.replace("activePlatformWorkspace", "getActivePlatformWorkspace()")
    block = block.replace("lastPlatformOwnerDashboard", "getLastPlatformOwnerDashboard()")
    block = block.replace("currentExperience", "getCurrentExperience()")
    block = block.replace("activeBusinessWorkspace", "getActiveBusinessWorkspace()")
    block = block.replace("lastGruhaData", "getLastGruhaData()")
    block = block.replace("lastBusinessDashboardStats", "getLastBusinessDashboardStats()")
    for name in (
        "ActivePlatformWorkspace",
        "LastPlatformOwnerDashboard",
        "CurrentExperience",
        "ActiveBusinessWorkspace",
        "LastGruhaData",
        "LastBusinessDashboardStats",
    ):
        block = block.replace(f"get{name}()()", f"get{name}()")
    return block


def main() -> None:
    if OUT.exists() and "export function renderDashboardPreview" in OUT.read_text(encoding="utf-8"):
        print("Already extracted")
        return

    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    spans: list[tuple[int, int, str]] = []
    for name in EXPORT_FUNCS:
        start, end = find_fn_block(lines, name)
        spans.append((start, end, name))
    spans.sort(key=lambda s: s[0], reverse=True)
    chunks: dict[str, str] = {}
    for start, end, name in spans:
        chunks[name] = "".join(lines[start:end])
        del lines[start:end]

    block = "".join(chunks[name] for name in EXPORT_FUNCS)
    for name in EXPORT_FUNCS:
        block = re.sub(
            rf"(?m)^(async )?function {name}\b",
            rf"export \1function {name}",
            block,
            count=1,
        )
    block = block.replace("export export ", "export ")
    block = rewrite_block(block)

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in block and f"export async function {name}" not in block:
            raise SystemExit(f"export missing for {name}")

    text = "".join(lines)
    text = re.sub(
        r"(?ms)^// ═+\n// SECTION: DASHBOARD PREVIEW SHELL\n.*?^// ═+\n\n+",
        "// Platform dashboard + dashboard preview shell live in modules/workspaces/dashboard-preview-shell.js\n\n",
        text,
        count=1,
    )
    # Clarify leftover shared formatters under the stale Mandir reports banner.
    text = text.replace(
        "// SECTION: MANDIR — financial reports (TB / I&E / B&P / BS)\n"
        "// API   : GET /api/v1/mandir/reports/...\n"
        "// NOTE  : renderMandirTrialBalance, renderMandirIncomeExpenditureReport, renderMandirBalanceSheetReport\n",
        "// Shared money/count formatters (used across workspaces)\n",
        1,
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
