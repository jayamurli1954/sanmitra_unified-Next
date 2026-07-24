#!/usr/bin/env python3
"""Extract account selector helpers into modules/workspaces/account-selector.js (Phase 3 seam 39).

Event listeners that also handle payment-allocation stay in app.js.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/account-selector.js"

HEADER = '''\
// ====================================================================
// SECTION: ACCOUNT SELECTOR COMPONENT
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initAccountSelector(...).
// Mixed document listeners (payment-allocation + voucher amounts) remain in app.js.
// ====================================================================

/** @type {Record<string, Function> | null} */
let deps = null;

export function initAccountSelector(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initAccountSelector() must be called before using account selector helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function businessAccountsForSelection() { return requireDeps().businessAccountsForSelection(); }
function getLastBusinessAccounts() { return requireDeps().getLastBusinessAccounts(); }
function filterBusinessAccountsByQuery(query) { return requireDeps().filterBusinessAccountsByQuery(query); }
function populateAccountPickerSelect(fieldId, accounts, selectedId = "") {
  return requireDeps().populateAccountPickerSelect(fieldId, accounts, selectedId);
}
function normalizeBusinessAccount(acc) { return requireDeps().normalizeBusinessAccount(acc); }
function updateVoucherBalance() { return requireDeps().updateVoucherBalance(); }

'''

EXPORT_FUNCS = [
    "renderAccountSelectorComponent",
    "updateAccountSuggestions",
    "selectAccountFromSuggestion",
    "selectBusinessAccount",
    "closeAllAccountSuggestions",
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
    if OUT.exists() and "export function renderAccountSelectorComponent" in OUT.read_text(encoding="utf-8"):
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
    # Keep SECTION banner but note listeners remain; or replace with listeners-only note
    text = re.sub(
        r"(?ms)^// ═+\n// SECTION: ACCOUNT SELECTOR COMPONENT\n.*?^// ═+\n\n+",
        "// Account selector helpers live in modules/workspaces/account-selector.js\n"
        "// Mixed document listeners (allocation + voucher amounts) remain below.\n\n",
        text,
        count=1,
    )
    # Drop orphan JSDoc that sat above render function if left behind
    text = re.sub(
        r"(?ms)^/\*\*\n \* Render account selector HTML.*?\*/\n+",
        "",
        text,
        count=1,
    )
    text = re.sub(
        r"(?ms)^/\*\*\n \* Update account selector suggestions.*?\*/\n+",
        "",
        text,
        count=1,
    )
    text = re.sub(
        r"(?ms)^/\*\*\n \* Select an account from suggestions.*?\*/\n+",
        "",
        text,
        count=1,
    )
    text = re.sub(
        r"(?ms)^/\*\*\n \* Close all account suggestions dropdowns.*?\*/\n+",
        "",
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
