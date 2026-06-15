"""Insert section markers into frontend/mitrabooks-erp/app.js (one-shot, bottom-up)."""
import pathlib

FILE = pathlib.Path("frontend/mitrabooks-erp/app.js")
lines = FILE.read_text(encoding="utf-8").splitlines(keepends=True)

def marker(title, apis="", note=""):
    bar = "═" * 70
    parts = [f"\n// {bar}\n", f"// SECTION: {title}\n"]
    if apis:
        parts.append(f"// API   : {apis}\n")
    if note:
        parts.append(f"// NOTE  : {note}\n")
    parts.append(f"// {bar}\n\n")
    return "".join(parts)

# (insert_before_line_1indexed, title, apis, note)
SECTIONS = [
    (15138, "BOOKS HEALTH WIDGET",
     "",
     "updateHealthWidget / refreshBooksHealthWidget / initializeHealthWidget"),

    (14461, "EVENT HANDLERS — click / change / input / keydown",
     "",
     "Single delegated listener on dashboardPreview for all workspace actions"),

    (14265, "MANDIR — dialogs: drilldown / verification / rejection / cancel",
     "",
     "openMandirVerificationDialog, openMandirCancelReceiptDialog, drillAccountingReport"),

    (13364, "MANDIR — account options / create forms / posting dialogs",
     "POST /api/v1/mandir/... (receipts, seva bookings, expenses, contra)",
     ""),

    (13210, "ACCOUNTING DRILLDOWN (shared MandirMitra + MitraBooks)",
     "GET /api/v1/accounting/drilldown/...",
     "loadAccountingVoucherDetail, renderAccountingDrilldownPanel"),

    (12880, "GRUHAMITRA WORKSPACE",
     "GET /api/v1/gruha/...",
     "renderGruhaDashboard, renderGruhaWorkspace"),

    (12694, "AUDIT TRAIL",
     "GET /api/v1/business/audit-log",
     "renderAuditEventsTable, loadAuditEvents, applyAuditFilters"),

    (12397, "VOUCHERS — CRUD + list",
     "GET /api/v1/business/vouchers  POST /api/v1/business/vouchers/{type}",
     "loadBusinessVouchers, reverseBusinessVoucher, openBusinessCreateVoucherDialog"),

    (12064, "VOUCHERS — creation helpers (party / contra / journal)",
     "POST /api/v1/business/vouchers/...",
     "createSimplePartyVoucher, createContraVoucher, createJournalVoucher"),

    (11873, "ACCOUNT SELECTOR COMPONENT",
     "",
     "renderAccountSelectorComponent, selectBusinessAccount — inline searchable dropdown"),

    (11735, "ACCOUNT LOADING + FINANCIAL HEALTH LOADER",
     "GET /api/v1/accounting/accounts  GET /api/v1/business/financial-health",
     "loadBusinessAccounts, loadFinancialHealth, loadBusinessDashboardStats"),

    (11562, "VOUCHER FORM HELPERS",
     "",
     "renderVoucherLineItem, updateVoucherBalance, addVoucherLine, clearVoucherForm"),

    (11147, "ACCOUNT HELPERS + DATA HEALTH",
     "",
     "normalizeBusinessAccount, businessAccountsForSelection, renderBusinessDataHealthPanel"),

    (11101, "DEBIT NOTES WORKSPACE",
     "GET /api/v1/business/debit-notes  POST /api/v1/business/debit-notes",
     "loadDebitNotes, submitDebitNote, renderBusinessDebitNoteWorkspace"),

    (10683, "CREDIT NOTES WORKSPACE",
     "GET /api/v1/business/credit-notes  POST /api/v1/business/credit-notes",
     "loadCreditNotes, submitCreditNote, renderBusinessCreditNoteWorkspace"),

    (10255, "PURCHASE BILLS WORKSPACE",
     "GET /api/v1/business/bills  POST /api/v1/business/bills",
     "loadBusinessBills, submitBill, renderBusinessPurchaseWorkspace"),

    (9746, "SALES INVOICES WORKSPACE",
     "GET /api/v1/business/invoices  POST /api/v1/business/invoices",
     "loadBusinessInvoices, submitInvoice, renderBusinessSalesWorkspace; e-invoice section included"),

    (8095, "PAYMENT ALLOCATION + AR/AP AGING",
     "GET /api/v1/business/aging  POST /api/v1/business/allocation",
     "loadBusinessAging, setAllocationKind, applyFifoSuggestion, submitAllocation"),

    (8060, "FINANCIAL REPORT LOADERS (TB / P&L / BS / R&P)",
     "GET /api/v1/business/reports/...",
     "loadBusinessTrialBalance, loadBusinessProfitLoss, loadBusinessBalanceSheet"),

    (7993, "GST PERIOD LOCKS",
     "POST /api/v1/business/gst-period-lock",
     "setGstPeriodLock, lockGstPeriodFromInput, rerenderBusinessReportsIfActive"),

    (7836, "ITC REVERSALS (Rule 37 / Re-claim)",
     "GET /api/v1/business/itc/reversals  POST /api/v1/business/itc/reverse|reclaim",
     "loadItcReversalPreview, reverseItcForBill, reclaimItcForBill, renderItcReversalPanel"),

    (7729, "GSTR-1 (Outward Supplies)",
     "GET /api/v1/business/returns/gstr-1?period=",
     "loadGstr1, renderGstr1Panel, downloadGstr1Json"),

    (7649, "TDS / TCS MODULE",
     "GET /api/v1/business/tds/register?quarter=",
     "loadTdsRegister, renderTdsRegisterPanel, renderTdsRegisterSide"),

    (7462, "BANK RECONCILIATION",
     "POST /api/v1/business/bank-recon/statement  GET /api/v1/business/bank-recon",
     "loadBankReconciliation, uploadBankStatementFile, confirmBankReconMatch"),

    (7303, "CUSTOMER STATEMENTS + DUNNING",
     "GET /api/v1/business/statements/{party_id}  POST .../dunning",
     "loadPartyStatement, recordDunningSent, renderStatementsPanel"),

    (7116, "INVENTORY (opt-in, periodic method)",
     "GET/POST /api/v1/business/inventory/items  GET .../stock-register",
     "loadInventoryItems, createInventoryItemFromForm, postClosingStock, renderInventoryPanel"),

    (6971, "ACCOUNTING DIMENSIONS (cost centre / project)",
     "GET/POST /api/v1/business/dimensions  GET .../report",
     "loadDimensions, createDimensionFromForm, deactivateDimension, renderDimensionsPanel"),

    (6785, "FIXED ASSETS + DEPRECIATION",
     "GET/POST /api/v1/business/fixed-assets  POST /api/v1/business/depreciation/run",
     "loadFixedAssets, createFixedAssetFromForm, renderFixedAssetsPanel"),

    (6593, "OPENING BALANCES + YEAR-END CLOSE",
     "POST /api/v1/business/opening-balances  POST /api/v1/business/year-end/close",
     "previewOpeningBalances, postOpeningBalances, previewYearEnd, postYearEndClose"),

    (6522, "GST COMPOSITION — CMP-08 (quarterly statement)",
     "GET /api/v1/business/returns/cmp-08?quarter=",
     "renderCmp08Panel, previewCmp08FromInput, postCmp08Liability"),

    (6412, "GSTR-4 (composition annual return)",
     "GET /api/v1/business/returns/gstr-4?financial_year=",
     "loadGstr4, renderGstr4Panel, downloadGstr4Json"),

    (6316, "GSTR-2B RECONCILIATION",
     "POST /api/v1/business/returns/gstr-2b/reconcile?period=",
     "reconcileGstr2b, renderGstr2bPanel — file-upload JSON match"),

    (6299, "GST RETURNS — workspace switcher (3B / 1 / 2B / CMP-08 / GSTR-4)",
     "",
     "renderGstReturns, gstReturnType state variable"),

    (6169, "GSTR-3B (monthly summary return)",
     "GET /api/v1/business/returns/gstr-3b?period=",
     "loadGstr3b, renderGstr3bPanel, downloadGstr3bJson"),

    (6077, "GST SETTLEMENT (liability posting)",
     "GET /api/v1/business/gst-settlement/preview  POST /api/v1/business/gst-settlement",
     "loadGstSettlementPreview, postGstSettlement, renderGstSettlementPanel"),

    (6006, "FINANCIAL REPORTS — workspace renderer + report framework",
     "GET /api/v1/business/reports/... (all report tabs)",
     "refreshCurrentBusinessReport, reportResultPayload — dispatches to tab-specific renderers"),

    (5847, "E-INVOICING (IRN foundation, credential-free)",
     "GET /api/v1/business/invoices/{id}/einvoice  POST .../record",
     "loadEinvoiceView, recordEinvoiceIrn, renderEinvoiceSection — INV-01 v1.1 payload"),

    (5749, "BUSINESS LIST FILTERING + PAGINATION",
     "",
     "applyBusinessListFilter, resetBusinessListFilter, pageBusinessList"),

    (5643, "BUSINESS WORKSPACE ROUTER — state + navigation",
     "",
     "setBusinessWorkspace, syncBusinessNavActiveState — drives activeBusinessWorkspace"),

    (5424, "PARTIES — CRUD + dialogs",
     "GET/POST /api/v1/business/parties  PATCH .../deactivate",
     "loadBusinessParties, createBusinessParty, updateBusinessParty"),

    (5372, "FINANCIAL HEALTH WORKSPACE",
     "GET /api/v1/business/financial-health?narrate=",
     "renderFinancialHealthWorkspace, fhFormatNarrative — AI narrative is advisory only"),

    (5177, "CHART OF ACCOUNTS (COA) WORKSPACE",
     "GET /api/v1/accounting/accounts  POST .../accounts  PATCH .../accounts/{code}",
     "renderBusinessCoaWorkspace — name-edit only, codes are permanent, type filter dropdown"),

    (4950, "BUSINESS WORKSPACE DISPATCHER",
     "",
     "renderBusinessWorkspace — top-level if/else dispatches to each workspace render function"),

    (4696, "VOUCHERS TABLE RENDERER",
     "",
     "renderBusinessVouchersTable — list view only; full CRUD at SECTION: VOUCHERS CRUD"),

    (4587, "PARTIES TABLE RENDERER",
     "",
     "renderBusinessPartiesTable, renderBusinessPartiesListFilters — list view only"),

    (4370, "DASHBOARD PREVIEW SHELL",
     "",
     "renderDashboardPreview — outermost wrapper rendered into dashboardPreview element"),

    (4053, "MANDIR — dashboard home + workspace tabs",
     "GET /api/v1/mandir/dashboard",
     "renderMandirDashboardHome, renderMandirDashboard, renderMandirSettings"),

    (3735, "MANDIR — panchang + operational reports",
     "GET /api/v1/mandir/panchang  GET /api/v1/mandir/reports/operational",
     "renderMandirPanchang, renderMandirOperationalReports, renderMandirDevoteesView"),

    (3121, "MANDIR — financial reports (TB / I&E / B&P / BS)",
     "GET /api/v1/mandir/reports/...",
     "renderMandirTrialBalance, renderMandirIncomeExpenditureReport, renderMandirBalanceSheetReport"),

    (2778, "MANDIR — receipt / donation / seva tables",
     "",
     "renderMandirDonationsTable, renderMandirSevaBookingsTable, renderMandirReceiptHistoryTable"),

    (2454, "AUTH + SESSION",
     "POST /api/v1/auth/login  POST /api/v1/auth/change-password",
     "signInWithPassword, signOutAndReturnToLogin, hasTrustedSession, updateSessionUi"),

    (2037, "SHARED UTILITIES",
     "",
     "escapeHtml, formatCurrency, formatCountLabel, setLoginStatus, statusDetailText, delay"),

    (1675, "BUSINESS EXECUTIVE DASHBOARD",
     "GET /api/v1/business/dashboard/stats",
     "renderBusinessExecutiveDashboard — KPI cards, quick actions, data-health panel"),

    (1213, "CA PRACTICE PORTAL + DOCUMENT INTAKE",
     "GET/POST /api/v1/business/ca-documents",
     "renderCaDocumentTable, renderCaDocumentIntake, caPracticeSummary"),

    (1146, "STAT CARDS + ACTIVITY + RECENT VOUCHERS",
     "",
     "renderStatCards, renderActionTiles, renderActivity, renderBusinessRecentVoucherRows"),

    (1050, "NAVIGATION RENDERING",
     "",
     "renderGroupedNav, renderGroupedNavFromItems — builds sidebar from nav group config"),

    (789, "EXPERIENCE + MODULE CONFIG",
     "",
     "renderModules, mandirNavigationItems, gruhaNavigationItems, loadAndRenderGroupedNav"),

    (420, "EXPERIENCE DETECTION + PRODUCT SHELL",
     "",
     "isMandirHost, isGruhaHost, isProductionShell, initialExperience, experienceConfig"),

    (160, "WIDGET SYSTEM (dashboard widget collapse / visibility / settings)",
     "",
     "getWidgetStates, toggleWidgetCollapse, createWidgetWrapper, openWidgetSettings"),

    (101, "THEME (dark / light)",
     "",
     "setTheme, getTheme, initializeTheme, updateThemeButtons"),

    (24, "NAVIGATION GROUPS + ITEMS",
     "",
     "businessNavigationGroups — sidebar structure for MitraBooks ERP"),

    (1,  "MODULE BOOTSTRAP — MitraBooks ERP app.js",
     "",
     "15K-line vanilla ES-module. Split trigger: >18K lines or second developer joins.\n// Use Ctrl+F '// SECTION:' to jump between sections."),
]

# Insert bottom-up so earlier line numbers stay valid
for (line1, title, apis, note) in sorted(SECTIONS, key=lambda x: -x[0]):
    idx = line1 - 1
    insert_text = marker(title, apis, note)
    lines.insert(idx, insert_text)

FILE.write_text("".join(lines), encoding="utf-8")
print(f"Done — inserted {len(SECTIONS)} section markers into {FILE}")
