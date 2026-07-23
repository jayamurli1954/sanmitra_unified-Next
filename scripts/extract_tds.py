#!/usr/bin/env python3
"""Extract TDS / TCS MODULE into modules/workspaces/tds.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/tds.js"

HEADER = '''\
// ====================================================================
// SECTION: TDS / TCS MODULE
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initTds(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastTdsRegister = null;
export let tdsQuarter = "";

/** @type {Record<string, Function> | null} */
let deps = null;

export function initTds(injected) {
  deps = injected;
  if (!tdsQuarter) {
    tdsQuarter = deps.currentFyQuarter();
  }
}

function requireDeps() {
  if (!deps) {
    throw new Error("initTds() must be called before using TDS helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function reportUnavailablePanel(title, payload) { return requireDeps().reportUnavailablePanel(title, payload); }
function rerenderBusinessReportsIfActive() { return requireDeps().rerenderBusinessReportsIfActive(); }
function recentFyQuarters(count = 6) { return requireDeps().recentFyQuarters(count); }
function getApiOutput() { return requireDeps().getApiOutput(); }

'''

FUNCS = [
    "loadTdsRegister",
    "previewTdsRegisterFromInput",
    "renderTdsRegisterSide",
    "renderTdsRegisterPanel",
]


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    section = next(i for i, l in enumerate(lines) if "SECTION: TDS / TCS" in l)
    start = section
    while start > 0 and lines[start - 1].strip().startswith("// ═"):
        start -= 1

    itc = next(i for i, l in enumerate(lines) if i > section and "SECTION: ITC REVERSALS" in l)
    itc_header = itc
    while itc_header > 0 and lines[itc_header - 1].strip().startswith("// ═"):
        itc_header -= 1

    end = itc_header
    while end > start:
        if lines[end - 1].strip() == "":
            end -= 1
            continue
        break

    body = "".join(lines[start:end])
    for name in FUNCS:
        # Only export public panel/loader helpers; keep renderTdsRegisterSide internal
        if name == "renderTdsRegisterSide":
            continue
        body = re.sub(
            rf"(?m)^(async )?function {name}\b",
            rf"export \1function {name}",
            body,
            count=1,
        )
    body = body.replace("export export ", "export ")
    body = re.sub(r"\bapiOutput\b", "getApiOutput()", body)

    for name in ("loadTdsRegister", "previewTdsRegisterFromInput", "renderTdsRegisterPanel"):
        if f"export function {name}" not in body and f"export async function {name}" not in body:
            raise SystemExit(f"export missing for {name}")

    module = HEADER + body
    if not module.endswith("\n"):
        module += "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(module, encoding="utf-8", newline="\n")

    text = "".join(lines[:start] + lines[itc_header:])
    for decl in (
        "let lastTdsRegister = null;\n",
        "let tdsQuarter = currentFyQuarter();\n",
    ):
        if decl not in text:
            raise SystemExit(f"missing decl to remove: {decl!r}")
        text = text.replace(decl, "", 1)

    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({module.count(chr(10)) + 1} lines)")
    print(f"Removed app.js body {start + 1}-{end}; strip through {itc_header}")


if __name__ == "__main__":
    main()
