#!/usr/bin/env python3
"""Extract business workspace dispatcher + router (Phase 3 seam 53)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend/mitrabooks-erp/app.js"
OUT = ROOT / "frontend/mitrabooks-erp/modules/workspaces/business-workspace.js"

HEADER = '''\
// ====================================================================
// SECTION: BUSINESS WORKSPACE DISPATCHER + ROUTER
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initBusinessWorkspace(...).
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

/** DOM refs bound once during init. */
let dashboardPreview;
let nav;
let topbarCurrent;

export function initBusinessWorkspace(injected) {
  deps = injected;
  dashboardPreview = injected.dashboardPreview;
  nav = injected.nav;
  topbarCurrent = injected.topbarCurrent;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initBusinessWorkspace() must be called before using business workspace helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function setActiveBusinessWorkspace(value) { requireDeps().setActiveBusinessWorkspace(value); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getSelectedOrgType() { return requireDeps().getSelectedOrgType(); }
function setSelectedOrgType(value) { requireDeps().setSelectedOrgType(value); }
function getOrgSelectorMeta() { return requireDeps().getOrgSelectorMeta(); }
function getExperienceConfig() { return requireDeps().getExperienceConfig(); }
function getBusinessReportState() { return requireDeps().getBusinessReportState(); }
function getLastBusinessParties() { return requireDeps().getLastBusinessParties(); }
function getLastBusinessVouchers() { return requireDeps().getLastBusinessVouchers(); }
function getLastBusinessAccounts() { return requireDeps().getLastBusinessAccounts(); }
function getLastVoucherApprovalQueue() { return requireDeps().getLastVoucherApprovalQueue(); }
function getLastAuditEvents() { return requireDeps().getLastAuditEvents(); }
function getSalesUi() { return requireDeps().getSalesUi(); }
function getPurchaseUi() { return requireDeps().getPurchaseUi(); }
function getCreditUi() { return requireDeps().getCreditUi(); }
function getDebitUi() { return requireDeps().getDebitUi(); }
function getHrUi() { return requireDeps().getHrUi(); }
function activeOrgSelectorType(...args) { return requireDeps().activeOrgSelectorType(...args); }
function updateTrustedContextUi(...args) { return requireDeps().updateTrustedContextUi(...args); }
function setActiveSettingsDetailId(...args) { return requireDeps().setActiveSettingsDetailId(...args); }
function hasTrustedSession(...args) { return requireDeps().hasTrustedSession(...args); }
function updatePageHeader(...args) { return requireDeps().updatePageHeader(...args); }
function renderMitraBooksSettingsWorkspace(...args) { return requireDeps().renderMitraBooksSettingsWorkspace(...args); }
function renderCaPracticePortalWorkspace(...args) { return requireDeps().renderCaPracticePortalWorkspace(...args); }
function renderBusinessPartiesListFilters(...args) { return requireDeps().renderBusinessPartiesListFilters(...args); }
function renderBusinessPartiesTable(...args) { return requireDeps().renderBusinessPartiesTable(...args); }
function renderVoucherApprovalQueuePanel(...args) { return requireDeps().renderVoucherApprovalQueuePanel(...args); }
function renderBusinessVouchersListFilters(...args) { return requireDeps().renderBusinessVouchersListFilters(...args); }
function renderBusinessVouchersTable(...args) { return requireDeps().renderBusinessVouchersTable(...args); }
function renderAuditListFilters(...args) { return requireDeps().renderAuditListFilters(...args); }
function renderAuditEventsTable(...args) { return requireDeps().renderAuditEventsTable(...args); }
function renderAccountingDrilldownPanel(...args) { return requireDeps().renderAccountingDrilldownPanel(...args); }
function renderBusinessReportsWorkspace(...args) { return requireDeps().renderBusinessReportsWorkspace(...args); }
function renderBusinessSalesWorkspace(...args) { return requireDeps().renderBusinessSalesWorkspace(...args); }
function renderBusinessPurchaseWorkspace(...args) { return requireDeps().renderBusinessPurchaseWorkspace(...args); }
function renderBusinessCreditNoteWorkspace(...args) { return requireDeps().renderBusinessCreditNoteWorkspace(...args); }
function renderBusinessDebitNoteWorkspace(...args) { return requireDeps().renderBusinessDebitNoteWorkspace(...args); }
function renderBusinessCoaWorkspace(...args) { return requireDeps().renderBusinessCoaWorkspace(...args); }
function renderFinancialHealthWorkspace(...args) { return requireDeps().renderFinancialHealthWorkspace(...args); }
function renderHrWorkspace(...args) { return requireDeps().renderHrWorkspace(...args); }
function renderManufacturingWorkspace(...args) { return requireDeps().renderManufacturingWorkspace(...args); }
function renderDashboardPreview(...args) { return requireDeps().renderDashboardPreview(...args); }
function loadBusinessDashboardStats(...args) { return requireDeps().loadBusinessDashboardStats(...args); }
function loadBusinessParties(...args) { return requireDeps().loadBusinessParties(...args); }
function loadBusinessAccounts(...args) { return requireDeps().loadBusinessAccounts(...args); }
function loadBusinessVouchers(...args) { return requireDeps().loadBusinessVouchers(...args); }
function loadVoucherApprovalQueue(...args) { return requireDeps().loadVoucherApprovalQueue(...args); }
function loadAuditEvents(...args) { return requireDeps().loadAuditEvents(...args); }
function refreshCurrentAccountingDrilldown(...args) { return requireDeps().refreshCurrentAccountingDrilldown(...args); }
function refreshCurrentBusinessReport(...args) { return requireDeps().refreshCurrentBusinessReport(...args); }
function loadInvoiceSettings(...args) { return requireDeps().loadInvoiceSettings(...args); }
function loadBusinessInvoices(...args) { return requireDeps().loadBusinessInvoices(...args); }
function loadBusinessAdminSettings(...args) { return requireDeps().loadBusinessAdminSettings(...args); }
function loadBusinessPartiesForHealth(...args) { return requireDeps().loadBusinessPartiesForHealth(...args); }
function loadAccountingDrilldownResult(...args) { return requireDeps().loadAccountingDrilldownResult(...args); }
function loadBusinessDataHealth(...args) { return requireDeps().loadBusinessDataHealth(...args); }
function loadBusinessBills(...args) { return requireDeps().loadBusinessBills(...args); }
function loadCreditNotes(...args) { return requireDeps().loadCreditNotes(...args); }
function loadDebitNotes(...args) { return requireDeps().loadDebitNotes(...args); }
function setCoaTypeFilter(...args) { return requireDeps().setCoaTypeFilter(...args); }
function resetCaPracticeWorkspaceState(...args) { return requireDeps().resetCaPracticeWorkspaceState(...args); }
function isBusinessAdmin(...args) { return requireDeps().isBusinessAdmin(...args); }
function loadCaAccessUsers(...args) { return requireDeps().loadCaAccessUsers(...args); }
function loadCaClients(...args) { return requireDeps().loadCaClients(...args); }
function loadCaPracticeDocuments(...args) { return requireDeps().loadCaPracticeDocuments(...args); }
function loadHrWorkspace(...args) { return requireDeps().loadHrWorkspace(...args); }
function setMfgTab(...args) { return requireDeps().setMfgTab(...args); }
function setMfgError(...args) { return requireDeps().setMfgError(...args); }
function loadMfgWorkspace(...args) { return requireDeps().loadMfgWorkspace(...args); }

'''

EXPORT_FUNCS = [
    "renderBusinessWorkspace",
    "setBusinessWorkspace",
    "syncBusinessNavActiveState",
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


def rewrite_block(block: str) -> str:
    block = block.replace("activeBusinessWorkspace", "getActiveBusinessWorkspace()")
    block = block.replace("currentExperience", "getCurrentExperience()")
    block = block.replace("selectedOrgType = \"BUSINESS\";", "setSelectedOrgType(\"BUSINESS\");")
    block = block.replace("orgSelectorMeta", "getOrgSelectorMeta()")
    block = block.replace("experienceConfig", "getExperienceConfig()")
    block = block.replace("businessReportState", "getBusinessReportState()")
    block = block.replace("lastBusinessParties", "getLastBusinessParties()")
    block = block.replace("lastBusinessVouchers", "getLastBusinessVouchers()")
    block = block.replace("lastBusinessAccounts", "getLastBusinessAccounts()")
    block = block.replace("lastVoucherApprovalQueue", "getLastVoucherApprovalQueue()")
    block = block.replace("lastAuditEvents", "getLastAuditEvents()")
    block = block.replace("salesUi", "getSalesUi()")
    block = block.replace("purchaseUi", "getPurchaseUi()")
    block = block.replace("creditUi", "getCreditUi()")
    block = block.replace("debitUi", "getDebitUi()")
    block = block.replace("hrUi", "getHrUi()")

    for name in (
        "ActiveBusinessWorkspace",
        "CurrentExperience",
        "OrgSelectorMeta",
        "ExperienceConfig",
        "BusinessReportState",
        "LastBusinessParties",
        "LastBusinessVouchers",
        "LastBusinessAccounts",
        "LastVoucherApprovalQueue",
        "LastAuditEvents",
        "SalesUi",
        "PurchaseUi",
        "CreditUi",
        "DebitUi",
        "HrUi",
    ):
        block = block.replace(f"get{name}()()", f"get{name}()")

    # Assignment after getter rewrite
    block = block.replace(
        "getActiveBusinessWorkspace() = workspace;",
        "setActiveBusinessWorkspace(workspace);",
    )
    return block


def main() -> None:
    if OUT.exists() and "export function renderBusinessWorkspace" in OUT.read_text(encoding="utf-8"):
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
    block = rewrite_block(block)

    for name in EXPORT_FUNCS:
        if f"export function {name}" not in block and f"export async function {name}" not in block:
            raise SystemExit(f"export missing for {name}")

    text = "".join(lines)
    text = re.sub(
        r"(?ms)^// ═+\n// SECTION: BUSINESS WORKSPACE DISPATCHER\n.*?^// ═+\n\n+",
        "// Business workspace dispatcher + router live in modules/workspaces/business-workspace.js\n\n",
        text,
        count=1,
    )
    text = re.sub(
        r"(?ms)^// ═+\n// SECTION: BUSINESS WORKSPACE ROUTER — state \+ navigation\n.*?^// ═+\n\n+",
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
