#!/usr/bin/env python3
"""Extract GST PERIOD LOCKS into modules/workspaces/period-locks.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/period-locks.js"

HEADER = '''\
// ====================================================================
// SECTION: GST PERIOD LOCKS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initPeriodLocks(...).
// NOTE: rerenderBusinessReportsIfActive stays in app.js (shared helper).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastPeriodLocks = [];

/** @type {Record<string, Function> | null} */
let deps = null;

export function initPeriodLocks(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initPeriodLocks() must be called before using period-lock helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function rerenderBusinessReportsIfActive() { return requireDeps().rerenderBusinessReportsIfActive(); }
function isBusinessAdmin() { return requireDeps().isBusinessAdmin(); }
function todayIsoDate() { return requireDeps().todayIsoDate(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

'''

EXPORT_FUNCS = [
    "loadPeriodLocks",
    "setGstPeriodLock",
    "lockGstPeriodFromInput",
    "renderPeriodLocksPanel",
]


def main() -> None:
    lines = APP.read_text(encoding="utf-8").splitlines(keepends=True)
    # loadPeriodLocks sits just above the SECTION banner
    load_fn = next(i for i, l in enumerate(lines) if "async function loadPeriodLocks" in l)
    section = next(i for i, l in enumerate(lines) if "SECTION: GST PERIOD LOCKS" in l)
    start = min(load_fn, section)
    while start > 0 and (
        lines[start - 1].strip().startswith("// ═")
        or lines[start - 1].strip() == ""
    ):
        # Prefer including blank line before loadPeriodLocks only if it follows year-end panel
        if lines[start - 1].strip().startswith("// ═"):
            start -= 1
            continue
        if lines[start - 1].strip() == "" and start == load_fn:
            start -= 1
            continue
        break
    # Canonical start: loadPeriodLocks (include SECTION banner as part of body)
    start = load_fn
    # Prepend section banner into module via body from loadPeriodLocks;
    # also grab SECTION header lines that sit between loadPeriodLocks and setGstPeriodLock
    # Actually body from load_fn through before rerenderBusinessReportsIfActive includes SECTION mid-block — fine.

    end = next(
        i
        for i, l in enumerate(lines)
        if i > load_fn and "function rerenderBusinessReportsIfActive" in l
    )
    while end > start and lines[end - 1].strip() == "":
        end -= 1

    body = "".join(lines[start:end])
    for name in EXPORT_FUNCS:
        body = re.sub(
            rf"(?m)^(async )?function {name}\b",
            rf"export \1function {name}",
            body,
            count=1,
        )
    body = body.replace("export export ", "export ")
    body = re.sub(r"\bapiOutput\b", "getApiOutput()", body)

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in body and f"export async function {name}" not in body:
            raise SystemExit(f"export missing for {name}")
    if "function rerenderBusinessReportsIfActive" in body:
        raise SystemExit("must not move rerenderBusinessReportsIfActive into period-locks")

    module = HEADER + body
    if not module.endswith("\n"):
        module += "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(module, encoding="utf-8", newline="\n")

    text = "".join(lines[:start] + lines[end:])
    decl = "let lastPeriodLocks = [];\n"
    if decl not in text:
        raise SystemExit("missing lastPeriodLocks decl")
    text = text.replace(decl, "", 1)

    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({module.count(chr(10)) + 1} lines)")
    print(f"Removed app.js body {start + 1}-{end}")


if __name__ == "__main__":
    main()
