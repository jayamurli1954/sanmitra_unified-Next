#!/usr/bin/env python3
"""Extract voucher form helpers into modules/workspaces/voucher-form.js (Phase 3 seam 37)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/voucher-form.js"

HEADER = '''\
// ====================================================================
// SECTION: VOUCHER FORM HELPERS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initVoucherForm(...).
// ====================================================================

export let voucherLineCounter = 0;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initVoucherForm(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initVoucherForm() must be called before using voucher form helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function normalizeBusinessAccount(acc) { return requireDeps().normalizeBusinessAccount(acc); }
function businessAccountLabel(account) { return requireDeps().businessAccountLabel(account); }
function renderAccountSelectorComponent(fieldId, selectedAccountId = null) {
  return requireDeps().renderAccountSelectorComponent(fieldId, selectedAccountId);
}
function refreshVoucherAccountDatalist() { return requireDeps().refreshVoucherAccountDatalist(); }
function updateVoucherAccountsStatus() { return requireDeps().updateVoucherAccountsStatus(); }
function populateVoucherAccountSelect(select, selectedId = "") {
  return requireDeps().populateVoucherAccountSelect(select, selectedId);
}
function getLastBusinessAccounts() { return requireDeps().getLastBusinessAccounts(); }

export function setVoucherLineCounter(value) {
  voucherLineCounter = Number(value) || 0;
}

'''

EXPORT_FUNCS = [
    "syncVoucherAccountFromText",
    "renderVoucherLineItem",
    "updateVoucherBalance",
    "updateVoucherBalanceState",
    "addVoucherLine",
    "removeVoucherLine",
    "clearVoucherForm",
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
        start, end = find_fn_block(lines, f"function {name}")
        spans.append((start, end, name))
    spans.sort(key=lambda s: s[0], reverse=True)
    chunks: dict[str, str] = {}
    for start, end, name in spans:
        chunks[name] = "".join(lines[start:end])
        del lines[start:end]
    return "".join(chunks[name] for name in names), lines


def main() -> None:
    if OUT.exists() and "export function addVoucherLine" in OUT.read_text(encoding="utf-8"):
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
    block = block.replace("lastBusinessAccounts", "getLastBusinessAccounts()")

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in block and f"export async function {name}" not in block:
            raise SystemExit(f"export missing for {name}")

    text = "".join(lines)
    text = re.sub(
        r"(?ms)^// ═+\n// SECTION: VOUCHER FORM HELPERS\n.*?^// ═+\n\n+",
        "",
        text,
        count=1,
    )
    text, n = re.subn(r"(?m)^let voucherLineCounter = 0;\n", "", text, count=1)
    if n != 1:
        raise SystemExit(f"voucherLineCounter removal failed n={n}")

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
