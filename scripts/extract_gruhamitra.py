#!/usr/bin/env python3
"""Extract GruhaMitra workspace helpers into modules/workspaces/gruhamitra.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/gruhamitra.js"

HEADER = '''\
// ====================================================================
// SECTION: GRUHAMITRA WORKSPACE
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initGruhamitra(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let activeGruhaWorkspace = "overview";
export let lastGruhaData = null;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initGruhamitra(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initGruhamitra() must be called before using GruhaMitra helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function resultRows(result) { return requireDeps().resultRows(result); }
function resultPayload(result, fallback) { return requireDeps().resultPayload(result, fallback); }
function renderStatCards(stats) { return requireDeps().renderStatCards(stats); }
function renderStatusBlock(title, result) { return requireDeps().renderStatusBlock(title, result); }
function renderSimpleTable(rows, columns, emptyText) { return requireDeps().renderSimpleTable(rows, columns, emptyText); }
function renderActivity(items) { return requireDeps().renderActivity(items); }
function renderAccountingDrilldownPanel(...args) { return requireDeps().renderAccountingDrilldownPanel(...args); }
function gruhaNavigationItems() { return requireDeps().gruhaNavigationItems(); }
function currentBillingPeriodQuery() { return requireDeps().currentBillingPeriodQuery(); }
function loadAccountingDrilldownResult() { return requireDeps().loadAccountingDrilldownResult(); }
function renderDashboardPreview(config) { return requireDeps().renderDashboardPreview(config); }
function syncGruhaNavActiveState() { return requireDeps().syncGruhaNavActiveState(); }
function getExperienceConfig() { return requireDeps().getExperienceConfig(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

'''

EXPORT_FUNCS = [
    "renderGruhaDashboard",
    "renderGruhaWorkspace",
    "loadGruhaDashboard",
    "setGruhaWorkspace",
]


def find_fn_block(lines: list[str], signature: str) -> tuple[int, int]:
    start = next(i for i, l in enumerate(lines) if signature in l)
    # include blank line before if any? keep from function start
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

    blocks = [
        find_fn_block(lines, "function renderGruhaDashboard"),
        find_fn_block(lines, "function renderGruhaWorkspace"),
        find_fn_block(lines, "async function loadGruhaDashboard"),
        find_fn_block(lines, "async function setGruhaWorkspace"),
    ]

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
    body = re.sub(r"\bapiOutput\b", "getApiOutput()", body)
    body = re.sub(r"\bdashboardPreview\b", "getDashboardPreview()", body)
    body = re.sub(r"\bexperienceConfig\.gruha\b", "getExperienceConfig().gruha", body)

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in body and f"export async function {name}" not in body:
            raise SystemExit(f"export missing for {name}")

    module = HEADER + body
    if not module.endswith("\n"):
        module += "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(module, encoding="utf-8", newline="\n")

    # Remove blocks from highest index first
    for start, end in sorted(blocks, key=lambda p: p[0], reverse=True):
        lines = lines[:start] + lines[end:]

    text = "".join(lines)
    for decl in (
        'let activeGruhaWorkspace = "overview";\n',
        "let lastGruhaData = null;\n",
    ):
        if decl not in text:
            raise SystemExit(f"missing decl: {decl!r}")
        text = text.replace(decl, "", 1)

    # Drop orphaned GRUHAMITRA SECTION banner if it now sits before runChecks with only blanks
    text = re.sub(
        r"\n// ═+\n// SECTION: GRUHAMITRA WORKSPACE\n// API[^\n]*\n// NOTE[^\n]*\n// ═+\n\n+",
        "\n\n",
        text,
        count=1,
    )

    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({module.count(chr(10)) + 1} lines)")
    print(f"Removed blocks: {[(s + 1, e) for s, e in blocks]}")


if __name__ == "__main__":
    main()
