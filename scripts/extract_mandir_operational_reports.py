#!/usr/bin/env python3
"""Extract Mandir panchang + operational report renderers (Phase 3 seam 48)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/mandir-operational-reports.js"

HEADER = '''\
// ====================================================================
// SECTION: MANDIR — PANCHANG + OPERATIONAL REPORTS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initMandirOperationalReports(...).
// ====================================================================

/** @type {Record<string, Function> | null} */
let deps = null;

export function initMandirOperationalReports(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initMandirOperationalReports() must be called before using Mandir operational report helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function renderStatCards(stats) { return requireDeps().renderStatCards(stats); }
function getLastMandirPanchang() { return requireDeps().getLastMandirPanchang(); }
function getLastMandirOperationalReports() { return requireDeps().getLastMandirOperationalReports(); }

'''

EXPORT_FUNCS = [
    "panchangTimeRange",
    "renderMandirPanchang",
    "reportPayload",
    "reportRows",
    "renderMandirOperationalReports",
    "renderMandirDevoteesView",
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


def main() -> None:
    if OUT.exists() and "export function renderMandirPanchang" in OUT.read_text(encoding="utf-8"):
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
    block = block.replace(
        "payload = lastMandirPanchang",
        "payload = getLastMandirPanchang()",
    )
    block = block.replace(
        "reports = lastMandirOperationalReports",
        "reports = getLastMandirOperationalReports()",
    )

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in block and f"export async function {name}" not in block:
            raise SystemExit(f"export missing for {name}")

    text = "".join(lines)
    text = re.sub(
        r"(?ms)^// ═+\n// SECTION: MANDIR — panchang \+ operational reports\n.*?^// ═+\n\n+",
        "// Mandir panchang + operational reports live in modules/workspaces/mandir-operational-reports.js\n\n",
        text,
        count=1,
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
