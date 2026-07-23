#!/usr/bin/env python3
"""Extract voucher creation helpers into modules/workspaces/voucher-create.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/voucher-create.js"

HEADER = '''\
// ====================================================================
// SECTION: VOUCHERS — creation helpers (party / contra / journal)
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initVoucherCreate(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

/** @type {Record<string, Function> | null} */
let deps = null;

export function initVoucherCreate(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initVoucherCreate() must be called before using voucher-create helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function findBusinessAccountById(accountId) { return requireDeps().findBusinessAccountById(accountId); }
function accountIdForVoucherPayload(account) { return requireDeps().accountIdForVoucherPayload(account); }
function voucherDimensionPayload() { return requireDeps().voucherDimensionPayload(); }
function clearVoucherForm() { return requireDeps().clearVoucherForm(); }
function loadBusinessVouchers(filters) { return requireDeps().loadBusinessVouchers(filters); }
function loadVoucherApprovalQueue(includeReviewed, options) { return requireDeps().loadVoucherApprovalQueue(includeReviewed, options); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function renderBusinessWorkspace() { return requireDeps().renderBusinessWorkspace(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

'''

EXPORT_FUNCS = [
    "loadVoucherPartyOutstanding",
    "createBusinessVoucherByType",
    "createSimplePartyVoucher",
    "createContraVoucher",
    "createJournalVoucher",
    "createBusinessVoucher",
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

    sigs = [
        "async function loadVoucherPartyOutstanding",
        "async function createBusinessVoucherByType",
        "async function createSimplePartyVoucher",
        "async function createContraVoucher",
        "async function createJournalVoucher",
        "async function createBusinessVoucher",
    ]
    blocks = [find_fn_block(lines, s) for s in sigs]

    body = "\n".join("".join(lines[s:e]) for s, e in blocks)
    for name in EXPORT_FUNCS:
        body = re.sub(
            rf"(?m)^(async )?function {name}\b",
            rf"export \1function {name}",
            body,
            count=1,
        )
    body = body.replace("export export ", "export ")

    body = re.sub(r"\bapiOutput\b", "getApiOutput()", body)
    body = re.sub(r"\bactiveBusinessWorkspace\b", "getActiveBusinessWorkspace()", body)
    body = re.sub(r"\bdashboardPreview\b", "getDashboardPreview()", body)

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in body and f"export async function {name}" not in body:
            raise SystemExit(f"export missing for {name}")

    module = HEADER + body
    if not module.endswith("\n"):
        module += "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(module, encoding="utf-8", newline="\n")

    for start, end in sorted(blocks, key=lambda t: t[0], reverse=True):
        del lines[start:end]

    text = "".join(lines)
    # Drop orphaned section banner for creation helpers if still present
    text = re.sub(
        r"\n// ═{10,}\n// SECTION: VOUCHERS — creation helpers \(party / contra / journal\)\n"
        r"// API[^\n]*\n// NOTE[^\n]*\n// ═{10,}\n+",
        "\n",
        text,
        count=1,
    )
    # Clean leftover "Voucher Form Integration" comments before listeners / runChecks
    text = re.sub(
        r"\n// ========== Voucher Form Integration ==========\n+(?:/\*\*[\s\S]*?\*/\n+)*",
        "\n",
        text,
        count=1,
    )
    text = re.sub(
        r"\n/\*\*\n \* Render form fields for specific voucher type\n \*/\n/\*\*\n \* Update form when voucher type changes\n \*/\n",
        "\n",
        text,
        count=1,
    )

    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(module.splitlines())} lines)")
    print(f"Updated {APP.relative_to(ROOT)} ({len(text.splitlines())} lines)")


if __name__ == "__main__":
    main()
