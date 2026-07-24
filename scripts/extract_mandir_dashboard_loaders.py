#!/usr/bin/env python3
"""Extract Mandir dashboard loaders (Phase 3 seam 57)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/mandir-dashboard-loaders.js"

HEADER = '''\
// ====================================================================
// SECTION: MANDIR — DASHBOARD LOADERS + SPLASH + TB LEDGER
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initMandirDashboardLoaders(...).
// ====================================================================

import { accountingDrilldownState } from "./accounting-drilldown.js";
import { mandirReportState } from "./mandir-financial-reports.js";
import { mandirReceiptRowsFromLists } from "./mandir-tables.js";
import { renderMandirDashboard } from "./mandir-dashboard.js";

/** @type {Record<string, any> | null} */
let deps = null;

/** DOM refs bound once during init. */
let mandirSplash;
let mandirSplashVideo;
let mandirSplashImage;
let brandSplashCopy;
let dashboardPreview;
let apiOutput;

export function initMandirDashboardLoaders(injected) {
  deps = injected;
  mandirSplash = injected.mandirSplash;
  mandirSplashVideo = injected.mandirSplashVideo;
  mandirSplashImage = injected.mandirSplashImage;
  brandSplashCopy = injected.brandSplashCopy;
  dashboardPreview = injected.dashboardPreview;
  apiOutput = injected.apiOutput;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initMandirDashboardLoaders() must be called before using Mandir dashboard loaders");
  }
  return deps;
}

function apiRequest(...args) { return requireDeps().apiRequest(...args); }
function renderJson(...args) { return requireDeps().renderJson(...args); }
function buildQueryString(...args) { return requireDeps().buildQueryString(...args); }
function todayIsoDate(...args) { return requireDeps().todayIsoDate(...args); }
function mandirListPath(...args) { return requireDeps().mandirListPath(...args); }
function mandirPublicPaymentsPath(...args) { return requireDeps().mandirPublicPaymentsPath(...args); }
function mandirPublicPaymentExceptionsPath(...args) { return requireDeps().mandirPublicPaymentExceptionsPath(...args); }
function loadAccountingDrilldownResult(...args) { return requireDeps().loadAccountingDrilldownResult(...args); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getLastMandirPaymentAccounts() { return requireDeps().getLastMandirPaymentAccounts(); }
function setLastMandirPaymentAccounts(value) { requireDeps().setLastMandirPaymentAccounts(value); }
function getLastMandirAccounts() { return requireDeps().getLastMandirAccounts(); }
function setLastMandirAccounts(value) { requireDeps().setLastMandirAccounts(value); }
function getLastMandirPanchang() { return requireDeps().getLastMandirPanchang(); }
function setLastMandirPanchang(value) { requireDeps().setLastMandirPanchang(value); }
function getLastMandirModuleConfig() { return requireDeps().getLastMandirModuleConfig(); }
function setLastMandirModuleConfig(value) { requireDeps().setLastMandirModuleConfig(value); }
function getLastMandirComplianceConfig() { return requireDeps().getLastMandirComplianceConfig(); }
function setLastMandirComplianceConfig(value) { requireDeps().setLastMandirComplianceConfig(value); }
function getLastMandirOperationalReports() { return requireDeps().getLastMandirOperationalReports(); }
function setLastMandirOperationalReports(value) { requireDeps().setLastMandirOperationalReports(value); }
function getLastMandirReceipt() { return requireDeps().getLastMandirReceipt(); }
function getLastMandirFormResult() { return requireDeps().getLastMandirFormResult(); }

'''

EXPORT_FUNCS = [
    "showMandirSplash",
    "hideMandirSplash",
    "loadMandirDashboard",
    "openMandirTrialBalanceLedger",
]


def find_fn_block(lines: list[str], name: str) -> tuple[int, int]:
    start = next(
        i
        for i, l in enumerate(lines)
        if re.match(rf"^(async )?function {re.escape(name)}\b", l)
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
    # Assignments first (before bare identifier rewrites).
    replacements = [
        ("lastMandirPaymentAccounts = ", "setLastMandirPaymentAccounts("),
        ("lastMandirAccounts = ", "setLastMandirAccounts("),
        ("lastMandirPanchang = ", "setLastMandirPanchang("),
        ("lastMandirModuleConfig = ", "setLastMandirModuleConfig("),
        ("lastMandirComplianceConfig = ", "setLastMandirComplianceConfig("),
        ("lastMandirOperationalReports = ", "setLastMandirOperationalReports("),
    ]
    # For assignment pattern `x = expr;` → `setX(expr);` — handle carefully after
    # converting prefix, we need closing paren before semicolon.
    # Simpler approach: replace reads with getters, then fix assignments.

    block = block.replace("currentExperience", "getCurrentExperience()")
    block = block.replace("getCurrentExperience()()", "getCurrentExperience()")

    # Readable getters for last* (assignment lines handled below)
    for name, getter, setter in (
        ("lastMandirPaymentAccounts", "getLastMandirPaymentAccounts()", "setLastMandirPaymentAccounts"),
        ("lastMandirAccounts", "getLastMandirAccounts()", "setLastMandirAccounts"),
        ("lastMandirPanchang", "getLastMandirPanchang()", "setLastMandirPanchang"),
        ("lastMandirModuleConfig", "getLastMandirModuleConfig()", "setLastMandirModuleConfig"),
        ("lastMandirComplianceConfig", "getLastMandirComplianceConfig()", "setLastMandirComplianceConfig"),
        ("lastMandirOperationalReports", "getLastMandirOperationalReports()", "setLastMandirOperationalReports"),
        ("lastMandirReceipt", "getLastMandirReceipt()", None),
        ("lastMandirFormResult", "getLastMandirFormResult()", None),
    ):
        # Fix accidental double-get after assignment rewrite attempts
        block = block.replace(name, getter)
        block = block.replace(f"{getter}()", getter)
        if setter:
            # getX() = expr  → setX(expr)  (expr ends at ; or , in rare cases — here always ;)
            block = re.sub(
                rf"{re.escape(getter)} = ([^;]+);",
                rf"{setter}(\1);",
                block,
            )

    return block


def main() -> None:
    if OUT.exists() and "export async function loadMandirDashboard" in OUT.read_text(encoding="utf-8"):
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

    text = "".join(lines)
    # Keep delay() in app.js; only note loaders moved near splash if comments remain.
    text = text.replace(
        "// Mandir dashboard home + tabs live in modules/workspaces/mandir-dashboard.js\n",
        "// Mandir dashboard home + tabs live in modules/workspaces/mandir-dashboard.js\n"
        "// Mandir dashboard loaders + splash live in modules/workspaces/mandir-dashboard-loaders.js\n",
        1,
    )

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

    # Sanity: no leftover assignment-to-getter
    if re.search(r"getLast\w+\(\) =", block):
        raise SystemExit("unfixed getter assignment remains")

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
