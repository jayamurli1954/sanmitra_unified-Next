#!/usr/bin/env python3
"""Extract CUSTOMER STATEMENTS + DUNNING into modules/workspaces/statements.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/statements.js"

HEADER = '''\
// ====================================================================
// SECTION: CUSTOMER STATEMENTS + DUNNING
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initStatements(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastPartyStatement = null;
export let statementPartyId = "";
export let statementKind = "receivable";
export let statementFromDate = "";
export let statementToDate = "";

/** @type {Record<string, Function> | null} */
let deps = null;

export function initStatements(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initStatements() must be called before using statement helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function reportUnavailablePanel(title, payload) { return requireDeps().reportUnavailablePanel(title, payload); }
function rerenderBusinessReportsIfActive() { return requireDeps().rerenderBusinessReportsIfActive(); }
function getLastBusinessParties() { return requireDeps().getLastBusinessParties(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

'''

FUNCS = [
    "loadPartyStatement",
    "recordDunningSent",
    "copyDunningLetter",
    "renderStatementsPanel",
]


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    section = next(i for i, l in enumerate(lines) if "SECTION: CUSTOMER STATEMENTS" in l)
    start = section
    while start > 0 and lines[start - 1].strip().startswith("// ═"):
        start -= 1

    tds = next(i for i, l in enumerate(lines) if i > section and "SECTION: TDS" in l)
    tds_header = tds
    while tds_header > 0 and lines[tds_header - 1].strip().startswith("// ═"):
        tds_header -= 1

    # Module body: statements section only (stop before blank/bank leftover)
    end = tds_header
    while end > start:
        prev = lines[end - 1]
        stripped = prev.strip()
        if stripped == "" or "Bank reconciliation" in prev or stripped.startswith("// ----"):
            end -= 1
            continue
        break

    # Drop stale Fixed assets leftover above statements (do not move into module)
    remove_start = start
    if remove_start >= 1 and "Fixed assets" in lines[remove_start - 1]:
        remove_start -= 1
        while remove_start > 0 and lines[remove_start - 1].strip() == "":
            remove_start -= 1

    body = "".join(lines[start:end])
    for name in FUNCS:
        body = re.sub(
            rf"(?m)^(async )?function {name}\b",
            rf"export \1function {name}",
            body,
            count=1,
        )
    body = body.replace("export export ", "export ")
    body = re.sub(r"\bapiOutput\b", "getApiOutput()", body)
    body = re.sub(r"\blastBusinessParties\b", "getLastBusinessParties()", body)

    for name in FUNCS:
        if f"export function {name}" not in body and f"export async function {name}" not in body:
            raise SystemExit(f"export missing for {name}")

    module = HEADER + body
    if not module.endswith("\n"):
        module += "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(module, encoding="utf-8", newline="\n")

    text = "".join(lines[:remove_start] + lines[tds_header:])
    for decl in (
        "let lastPartyStatement = null;\n",
        'let statementPartyId = "";\n',
        'let statementKind = "receivable";\n',
        'let statementFromDate = "";\n',
        'let statementToDate = "";\n',
    ):
        if decl not in text:
            raise SystemExit(f"missing decl to remove: {decl!r}")
        text = text.replace(decl, "", 1)

    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({module.count(chr(10)) + 1} lines)")
    print(f"Body {start + 1}-{end}; removed app.js {remove_start + 1}-{tds_header}")


if __name__ == "__main__":
    main()
