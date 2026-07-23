#!/usr/bin/env python3
"""Extract Chart of Accounts workspace into modules/workspaces/coa.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/coa.js"

HEADER = '''\
// ====================================================================
// SECTION: CHART OF ACCOUNTS (COA) WORKSPACE
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initCoa(...).
// ====================================================================

import { apiRequest } from "../../../shared/api-client.js";

export let coaTypeFilter = "";

export const COA_TYPE_META = {
  asset:     { label: "Asset",     pillClass: "pill ok" },
  liability: { label: "Liability", pillClass: "pill danger" },
  equity:    { label: "Equity",    pillClass: "pill neutral" },
  income:    { label: "Income",    pillClass: "pill ok" },
  expense:   { label: "Expense",   pillClass: "pill warn" },
};
export const COA_CLASS_LABELS = {
  personal: "Personal", real: "Real", nominal: "Nominal",
};

/** @type {Record<string, Function> | null} */
let deps = null;

export function initCoa(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initCoa() must be called before using COA helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function getLastBusinessAccounts() { return requireDeps().getLastBusinessAccounts(); }
function loadBusinessAccounts() { return requireDeps().loadBusinessAccounts(); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function renderBusinessWorkspace() { return requireDeps().renderBusinessWorkspace(); }

export function setCoaTypeFilter(value) {
  coaTypeFilter = String(value || "");
}

'''

EXPORT_FUNCS = [
    "coaTypePill",
    "renderBusinessCoaWorkspace",
    "coaShowMsg",
    "coaHandleAddSubmit",
    "coaHandleSaveName",
    "coaEnterEditMode",
    "coaExitEditMode",
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


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)

    # Contiguous from COA section banner through coaExitEditMode / end comment
    start = next(i for i, l in enumerate(lines) if "SECTION: CHART OF ACCOUNTS (COA) WORKSPACE" in l)
    while start > 0 and not lines[start].startswith("// ═"):
        start -= 1
    _, end = find_fn_block(lines, "function coaExitEditMode")
    # include trailing end comment if present
    if end < len(lines) and "End Chart of Accounts" in lines[end]:
        end += 1
        while end < len(lines) and lines[end].strip() == "":
            end += 1

    block = "".join(lines[start:end])

    # Drop banner + const declarations (redeclared in HEADER) + decorative comments
    block = re.sub(
        r"(?ms)^// ═.*?^const COA_CLASS_LABELS = \{.*?\};\n+",
        "",
        block,
        count=1,
    )
    block = re.sub(r"(?m)^// ── Chart of Accounts workspace ─+\n+", "", block)
    block = re.sub(r"(?m)^// ── End Chart of Accounts workspace ─+\n*", "", block)

    for name in EXPORT_FUNCS:
        block = re.sub(
            rf"(?m)^(async )?function {name}\b",
            rf"export \1function {name}",
            block,
            count=1,
        )
    block = block.replace("export export ", "export ")

    block = re.sub(r"\blastBusinessAccounts\b", "getLastBusinessAccounts()", block)
    block = re.sub(r"\bdashboardPreview\b", "getDashboardPreview()", block)
    # Don't replace coaTypeFilter reads - it's local export let

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in block and f"export async function {name}" not in block:
            raise SystemExit(f"export missing for {name}")

    module = HEADER + block
    if not module.endswith("\n"):
        module += "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(module, encoding="utf-8", newline="\n")

    del lines[start:end]
    text = "".join(lines)

    text, n = re.subn(r"(?m)^let coaTypeFilter = \"\";\n", "", text, count=1)
    if n != 1:
        raise SystemExit(f"coaTypeFilter removal failed n={n}")

    text = re.sub(
        r'(?m)^(\s*)coaTypeFilter = "";\n',
        r'\1setCoaTypeFilter("");\n',
        text,
    )

    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(module.splitlines())} lines)")
    print(f"Updated {APP.relative_to(ROOT)} ({len(text.splitlines())} lines)")


if __name__ == "__main__":
    main()
