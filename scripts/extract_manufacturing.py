#!/usr/bin/env python3
"""Extract Manufacturing & Cost-Centre add-on into modules/workspaces/manufacturing.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/manufacturing.js"

HEADER = '''\
// ====================================================================
// SECTION: MANUFACTURING & COST-CENTRE ADD-ON
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initManufacturing(...).
// ====================================================================

import { apiRequest } from "../../../shared/api-client.js";

export let mfgAccess = null;
export let mfgTab = "cost-centres";
export let mfgError = "";
export let mfgCostCentres = [];
export let mfgTree = [];
export let mfgBudgets = [];
export let mfgBudgetVsActual = null;
export let mfgBoms = [];
export let mfgWorkOrders = [];
export let mfgItems = [];
export let mfgPl = null;
export let mfgPlFrom = "";
export let mfgPlTo = "";
export let mfgBomDraft = [];
export let mfgWoActualDraft = [];
export let mfgCompleteFor = "";

/** @type {Record<string, Function> | null} */
let deps = null;

export function initManufacturing(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initManufacturing() must be called before using manufacturing helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function getLastBusinessAccounts() { return requireDeps().getLastBusinessAccounts(); }
function refreshMfgView() { return requireDeps().refreshMfgView(); }

export function setMfgTab(value) { mfgTab = value; }
export function setMfgError(value) { mfgError = value; }
export function setMfgBudgetVsActual(value) { mfgBudgetVsActual = value; }
export function setMfgCompleteFor(value) { mfgCompleteFor = value; }
export function setMfgPlFrom(value) { mfgPlFrom = value; }
export function setMfgPlTo(value) { mfgPlTo = value; }
export function setMfgWoActualDraft(value) { mfgWoActualDraft = value; }

'''

# Functions to export (all mfg* and renderMfg*/renderManufacturing*)
EXPORT_FUNCS = [
    "mfgMoney",
    "mfgCanManage",
    "mfgCanManageMfg",
    "loadMfgWorkspace",
    "loadMfgCostCentres",
    "loadMfgTree",
    "loadMfgBudgets",
    "loadMfgItems",
    "loadMfgBoms",
    "loadMfgWorkOrders",
    "loadMfgPl",
    "mfgEnableLayer",
    "mfgCreateCostCentre",
    "mfgCreateBudget",
    "mfgSetBudgetStatus",
    "mfgViewBudgetVsActual",
    "mfgAddBomComponent",
    "mfgRemoveBomComponent",
    "mfgCreateBom",
    "mfgCreateWorkOrder",
    "mfgSetWorkOrderStatus",
    "mfgOpenComplete",
    "mfgAddWoActual",
    "mfgRemoveWoActual",
    "mfgCompleteWorkOrder",
    "mfgItemName",
    "mfgItemOptions",
    "mfgTabButton",
    "mfgRenderTreeNodes",
    "renderMfgCostCentresTab",
    "renderMfgBudgetsTab",
    "renderMfgPlTab",
    "renderMfgBomsTab",
    "renderMfgWorkOrdersTab",
    "renderMfgTab",
    "renderManufacturingWorkspace",
]


def find_fn_block(lines: list[str], signature: str) -> tuple[int, int]:
    start = next(
        i
        for i, l in enumerate(lines)
        if signature in l and l.lstrip().startswith(("function ", "async function ", "let ", "const "))
    )
    # For let/const state we handle separately
    if lines[start].lstrip().startswith(("let ", "const ")):
        end = start + 1
        while end < len(lines) and lines[end].strip() == "":
            end += 1
        return start, end
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

    # Contiguous block: from MANUFACTURING banner through renderManufacturingWorkspace
    start = next(i for i, l in enumerate(lines) if "MANUFACTURING & COST-CENTRE ADD-ON" in l)
    # back up to section comment banner start
    while start > 0 and not lines[start].startswith("// ═"):
        start -= 1
    _, end = find_fn_block(lines, "function renderManufacturingWorkspace")

    block = "".join(lines[start:end])

    # Drop original state declarations (re-declared in HEADER)
    block = re.sub(
        r"(?ms)^// ═.*?^let mfgCompleteFor = \"\";\n+",
        "",
        block,
        count=1,
    )
    # Drop refreshMfgView — stays in app.js as shell glue
    block = re.sub(
        r"(?ms)^function refreshMfgView\(\) \{.*?\n\}\n+",
        "",
        block,
        count=1,
    )

    for name in EXPORT_FUNCS:
        block = re.sub(
            rf"(?m)^(async )?function {name}\b",
            rf"export \1function {name}",
            block,
            count=1,
        )
    block = block.replace("export export ", "export ")

    block = re.sub(r"\blastBusinessAccounts\b", "getLastBusinessAccounts()", block)

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in block and f"export async function {name}" not in block:
            raise SystemExit(f"export missing for {name}")

    module = HEADER + block
    if not module.endswith("\n"):
        module += "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(module, encoding="utf-8", newline="\n")

    del lines[start:end]
    APP.write_text("".join(lines), encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(module.splitlines())} lines)")
    print(f"Updated {APP.relative_to(ROOT)} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
