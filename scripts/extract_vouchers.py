#!/usr/bin/env python3
"""Extract vouchers CRUD + list helpers into modules/workspaces/vouchers.js."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/vouchers.js"

HEADER = '''\
// ====================================================================
// SECTION: VOUCHERS — CRUD + list + create dialog
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initVouchers(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastBusinessVouchers = [];
export let lastVoucherApprovalQueue = [];

/** @type {Record<string, Function> | null} */
let deps = null;

export function initVouchers(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initVouchers() must be called before using voucher helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function getBusinessListState() { return requireDeps().getBusinessListState(); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function renderBusinessWorkspace() { return requireDeps().renderBusinessWorkspace(); }
function getApiOutput() { return requireDeps().getApiOutput(); }
function getLastBusinessParties() { return requireDeps().getLastBusinessParties(); }
function getLastBusinessAccounts() { return requireDeps().getLastBusinessAccounts(); }
function getLastDimensions() { return requireDeps().getLastDimensions(); }
function loadBusinessAccounts() { return requireDeps().loadBusinessAccounts(); }
function loadBusinessParties() { return requireDeps().loadBusinessParties(); }
function loadDimensions() { return requireDeps().loadDimensions(); }
function renderAccountSelectorComponent(fieldId) { return requireDeps().renderAccountSelectorComponent(fieldId); }
function dimensionOptions(kind) { return requireDeps().dimensionOptions(kind); }
function addVoucherLine() { return requireDeps().addVoucherLine(); }
function updateVoucherBalance() { return requireDeps().updateVoucherBalance(); }
function clearVoucherForm() { return requireDeps().clearVoucherForm(); }
function loadVoucherPartyOutstanding(partyId, voucherType) { return requireDeps().loadVoucherPartyOutstanding(partyId, voucherType); }
function createBusinessVoucherByType(voucherType, date) { return requireDeps().createBusinessVoucherByType(voucherType, date); }
function getBusinessVoucherCreateForm() { return requireDeps().getBusinessVoucherCreateForm(); }
function getBusinessVoucherCreateDialog() { return requireDeps().getBusinessVoucherCreateDialog(); }

export function setLastBusinessVouchers(value) { lastBusinessVouchers = Array.isArray(value) ? value : []; }
export function setLastVoucherApprovalQueue(value) { lastVoucherApprovalQueue = Array.isArray(value) ? value : []; }
export function clearVoucherListState() {
  lastBusinessVouchers = [];
  lastVoucherApprovalQueue = [];
}

'''

EXPORT_FUNCS = [
    "loadBusinessVouchers",
    "loadVoucherApprovalQueue",
    "reviewBusinessVoucher",
    "reverseBusinessVoucher",
    "renderVoucherTypeForm",
    "updateVoucherTypeForm",
    "focusFirstVoucherField",
    "submitVoucherDialogFromKeyboard",
    "handleVoucherDialogKeyboard",
    "openBusinessCreateVoucherDialog",
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
        "async function loadBusinessVouchers",
        "async function loadVoucherApprovalQueue",
        "async function reviewBusinessVoucher",
        "async function reverseBusinessVoucher",
        "function renderVoucherTypeForm",
        "function updateVoucherTypeForm",
        "function focusFirstVoucherField",
        "function submitVoucherDialogFromKeyboard",
        "function handleVoucherDialogKeyboard",
        "async function openBusinessCreateVoucherDialog",
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
    body = re.sub(r"\bbusinessListState\b", "getBusinessListState()", body)
    body = re.sub(r"\bcurrentExperience\b", "getCurrentExperience()", body)
    body = re.sub(r"\bactiveBusinessWorkspace\b", "getActiveBusinessWorkspace()", body)
    body = re.sub(r"\bdashboardPreview\b", "getDashboardPreview()", body)
    body = re.sub(r"\blastBusinessParties\b", "getLastBusinessParties()", body)
    body = re.sub(r"\blastBusinessAccounts\b", "getLastBusinessAccounts()", body)
    body = re.sub(r"\blastDimensions\b", "getLastDimensions()", body)

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
    # Remove state declarations now owned by the module
    for name in ("lastBusinessVouchers", "lastVoucherApprovalQueue"):
        text, n = re.subn(rf"(?m)^let {name} = \[\];\n", "", text, count=1)
        if n != 1:
            raise SystemExit(f"failed to remove state {name} n={n}")

    # Drop orphaned section banner if present
    text = re.sub(
        r"\n// ═{10,}\n// SECTION: VOUCHERS — CRUD \+ list\n"
        r"// API[^\n]*\n// NOTE[^\n]*\n// ═{10,}\n+",
        "\n",
        text,
        count=1,
    )

    # Clear sites that assigned the moved arrays
    text = text.replace(
        "lastBusinessVouchers = [];\n  lastVoucherApprovalQueue = [];",
        "clearVoucherListState();",
    )
    # Any remaining solo clears
    text = re.sub(r"(?m)^(\s*)lastBusinessVouchers = \[\];\n", r"\1setLastBusinessVouchers([]);\n", text)
    text = re.sub(r"(?m)^(\s*)lastVoucherApprovalQueue = \[\];\n", r"\1setLastVoucherApprovalQueue([]);\n", text)

    APP.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(module.splitlines())} lines)")
    print(f"Updated {APP.relative_to(ROOT)} ({len(text.splitlines())} lines)")


if __name__ == "__main__":
    main()
