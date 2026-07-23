#!/usr/bin/env python3
"""Extract Financial Health workspace into modules/workspaces/financial-health.js (Phase 3 seam 35)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/financial-health.js"

HEADER = '''\
// ====================================================================
// SECTION: FINANCIAL HEALTH WORKSPACE
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initFinancialHealth(...).
// API: GET /api/v1/business/financial-health — AI narrative is advisory only.
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastFinancialHealth = null;
export let financialHealthLoadInFlight = false;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initFinancialHealth(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initFinancialHealth() must be called before using Financial Health helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function getApiOutput() { return requireDeps().getApiOutput(); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function renderBusinessWorkspace() { return requireDeps().renderBusinessWorkspace(); }

export function setLastFinancialHealth(value) {
  lastFinancialHealth = value;
}

export function resetFinancialHealthState() {
  lastFinancialHealth = null;
  financialHealthLoadInFlight = false;
}

'''

EXPORT_FUNCS = [
    "fhKpiDisplay",
    "renderFhKpiCard",
    "renderFhBarChart",
    "renderFhAlert",
    "fhFormatNarrative",
    "renderFinancialHealthWorkspace",
    "loadFinancialHealth",
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
        sig = f"function {name}" if name != "loadFinancialHealth" else "async function loadFinancialHealth"
        # find_fn_block matches startswith function/async function and signature in line
        start, end = find_fn_block(lines, f"function {name}")
        spans.append((start, end, name))
    spans.sort(key=lambda s: s[0], reverse=True)
    chunks: dict[str, str] = {}
    for start, end, name in spans:
        chunks[name] = "".join(lines[start:end])
        del lines[start:end]
    ordered = "".join(chunks[name] for name in names)
    return ordered, lines


def main() -> None:
    if OUT.exists() and "export function renderFinancialHealthWorkspace" in OUT.read_text(encoding="utf-8"):
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

    # Use live module state (already export let)
    # Remove orphaned SECTION banner that may remain between helpers and parties
    text = "".join(lines)
    text = re.sub(
        r"(?ms)^// ═+\n// SECTION: FINANCIAL HEALTH WORKSPACE\n.*?^// ═+\n\n+",
        "",
        text,
        count=1,
    )
    text, n1 = re.subn(r"(?m)^let lastFinancialHealth = null;\n", "", text, count=1)
    text, n2 = re.subn(r"(?m)^let financialHealthLoadInFlight = false;\n", "", text, count=1)
    if n1 != 1 or n2 != 1:
        raise SystemExit(f"state removal failed n1={n1} n2={n2}")

    # Assignments in remaining app.js should use setters if any remain
    # loadFinancialHealth moved, so only external writes — check shell-ui etc later

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in block and f"export async function {name}" not in block:
            raise SystemExit(f"export missing for {name}")

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
