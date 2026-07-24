#!/usr/bin/env python3
"""Extract account helpers + data health + books-health widget (Phase 3 seam 40).

Context helpers (isPlatformOwnerContext / isBusinessTenantContext /
isBusinessModuleEnabled / enabledModuleKeys) stay in app.js.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/account-helpers.js"

HEADER = '''\
// ====================================================================
// SECTION: ACCOUNT HELPERS + DATA HEALTH + BOOKS HEALTH WIDGET
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initAccountHelpers(...).
// Context helpers (platform owner / business tenant) remain in app.js.
// ====================================================================

/** @type {Record<string, Function> | null} */
let deps = null;

export function initAccountHelpers(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initAccountHelpers() must be called before using account helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function getLastBusinessAccounts() { return requireDeps().getLastBusinessAccounts(); }
function getLastBusinessAccountsResult() { return requireDeps().getLastBusinessAccountsResult(); }
function getLastBusinessParties() { return requireDeps().getLastBusinessParties(); }
function getLastBusinessPartiesResult() { return requireDeps().getLastBusinessPartiesResult(); }
function getLastModuleContext() { return requireDeps().getLastModuleContext(); }
function getLastAccountingDrilldown() { return requireDeps().getLastAccountingDrilldown(); }
function getLastBusinessDataHealth() { return requireDeps().getLastBusinessDataHealth(); }
function getBusinessDataHealthLoadInFlight() { return requireDeps().getBusinessDataHealthLoadInFlight(); }
function loadBusinessDataHealth() { return requireDeps().loadBusinessDataHealth(); }
function hasTrustedSession() { return requireDeps().hasTrustedSession(); }
function enabledModuleKeys(context) { return requireDeps().enabledModuleKeys(context); }
function isBusinessTenantContext(context) { return requireDeps().isBusinessTenantContext(context); }

const MITRABOOKS_FALLBACK_ACCOUNTS = [
  { account_id: 11001, account_code: "11001", account_name: "Cash in Hand", account_type: "asset" },
  { account_id: 11010, account_code: "11010", account_name: "Bank Account", account_type: "asset" },
  { account_id: 12001, account_code: "12001", account_name: "Sundry Debtors", account_type: "asset" },
  { account_id: 13002, account_code: "13002", account_name: "Advance to Suppliers", account_type: "asset" },
  { account_id: 21001, account_code: "21001", account_name: "Sundry Creditors", account_type: "liability" },
  { account_id: 24001, account_code: "24001", account_name: "Advance from Customers", account_type: "liability" },
  { account_id: 41001, account_code: "41001", account_name: "Sales", account_type: "income" },
  { account_id: 41002, account_code: "41002", account_name: "Service Income", account_type: "income" },
  { account_id: 53004, account_code: "53004", account_name: "Office Expense", account_type: "expense" },
  { account_id: 54001, account_code: "54001", account_name: "Bank Charges", account_type: "expense" },
];

'''

EXPORT_FUNCS = [
    "normalizeBusinessAccount",
    "businessAccountLabel",
    "businessAccountsForSelection",
    "hasLoadedBusinessAccounts",
    "findBusinessAccountById",
    "accountIdForVoucherPayload",
    "populateVoucherAccountSelect",
    "populateAccountPickerSelect",
    "refreshVoucherAccountDatalist",
    "updateVoucherAccountsStatus",
    "refreshVoucherAccountSelects",
    "accountRowsFromPayload",
    "normalizedAccountRows",
    "hasBusinessAccount",
    "countPartiesMissingGstin",
    "dataHealthItem",
    "dataHealthAction",
    "renderBusinessDataHealthIssueList",
    "renderBusinessDataHealthActions",
    "getBusinessHealthState",
    "renderBusinessDataHealthPanel",
    "updateHealthWidget",
    "refreshBooksHealthWidget",
    "initializeHealthWidget",
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
    if OUT.exists() and "export function normalizeBusinessAccount" in OUT.read_text(encoding="utf-8"):
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

    # Rewrite shell state reads to deps getters (imported lets are read-only).
    replacements = [
        ("lastBusinessAccountsResult", "getLastBusinessAccountsResult()"),
        ("lastBusinessAccounts", "getLastBusinessAccounts()"),
        ("lastBusinessPartiesResult", "getLastBusinessPartiesResult()"),
        ("lastBusinessParties", "getLastBusinessParties()"),
        ("lastModuleContext", "getLastModuleContext()"),
        ("lastAccountingDrilldown", "getLastAccountingDrilldown()"),
        ("lastBusinessDataHealth", "getLastBusinessDataHealth()"),
        ("businessDataHealthLoadInFlight", "getBusinessDataHealthLoadInFlight()"),
    ]
    for old, new in replacements:
        block = block.replace(old, new)

    # Fix double-call if any getter was already wrapped incorrectly — none expected.
    # Fix default params that became getX()() from rows = lastX -> rows = getX()
    # countPartiesMissingGstin(rows = getLastBusinessParties()) is fine.
    # normalizedAccountRows(rows = getLastBusinessAccounts()) is fine.

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in block and f"export async function {name}" not in block:
            raise SystemExit(f"export missing for {name}")

    text = "".join(lines)

    # Drop fallback constant from shell (moved into module).
    text = re.sub(
        r"(?ms)^const MITRABOOKS_FALLBACK_ACCOUNTS = \[\n.*?\n\];\n\n+",
        "",
        text,
        count=1,
    )

    text = re.sub(
        r"(?ms)^// ═+\n// SECTION: ACCOUNT HELPERS \+ DATA HEALTH\n.*?^// ═+\n\n+",
        "// Account helpers + data health live in modules/workspaces/account-helpers.js\n"
        "// Context helpers (platform owner / business tenant) remain below.\n\n",
        text,
        count=1,
    )
    text = re.sub(
        r"(?ms)^// ═+\n// SECTION: BOOKS HEALTH WIDGET\n.*?^// ═+\n\n+",
        "// Books health widget lives in modules/workspaces/account-helpers.js\n\n",
        text,
        count=1,
    )
    # Drop orphan JSDoc above books health if left behind
    text = re.sub(
        r"(?ms)^/\*\*\n \* @param \{number\} percentage - Health percentage.*?\*/\n+",
        "",
        text,
        count=1,
    )
    text = re.sub(
        r"(?ms)^/\*\*\n \* Initialize health widget on page load\n \*/\n+",
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
