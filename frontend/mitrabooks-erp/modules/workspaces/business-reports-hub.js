// ====================================================================
// SECTION: BUSINESS REPORTS HUB — workspace + export/print framework
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initBusinessReportsHub(...).
// Tab-specific loaders/renderers remain in financial-reports.js and sibling modules.
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

export function initBusinessReportsHub(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initBusinessReportsHub() must be called before using business reports hub helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function todayIsoDate() { return requireDeps().todayIsoDate(); }
function renderJson(...args) { return requireDeps().renderJson(...args); }
function downloadApiFile(...args) { return requireDeps().downloadApiFile(...args); }
function getApiOutput() { return requireDeps().getApiOutput(); }
function getBusinessReportState() { return requireDeps().getBusinessReportState(); }
function getBusinessReportTabs() { return requireDeps().getBusinessReportTabs(); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function renderBusinessWorkspace() { return requireDeps().renderBusinessWorkspace(); }
function getGstReturnState() { return requireDeps().getGstReturnState(); }
function getItcReversalAsOf() { return requireDeps().getItcReversalAsOf(); }
function getTdsQuarter() { return requireDeps().getTdsQuarter(); }
function getBankReconAccountId() { return requireDeps().getBankReconAccountId(); }
function getStatementPartyId() { return requireDeps().getStatementPartyId(); }
function getStatementKind() { return requireDeps().getStatementKind(); }
function getStatementFromDate() { return requireDeps().getStatementFromDate(); }
function getStatementToDate() { return requireDeps().getStatementToDate(); }
function getLastBusinessParties() { return requireDeps().getLastBusinessParties(); }
function getLastInventoryItems() { return requireDeps().getLastInventoryItems(); }
function getCreditUi() { return requireDeps().getCreditUi(); }
function getDebitUi() { return requireDeps().getDebitUi(); }
function hasLoadedBusinessAccounts() { return requireDeps().hasLoadedBusinessAccounts(); }
function loadBusinessAccounts(...args) { return requireDeps().loadBusinessAccounts(...args); }
function loadBusinessParties(...args) { return requireDeps().loadBusinessParties(...args); }
function loadBusinessTrialBalance(...args) { return requireDeps().loadBusinessTrialBalance(...args); }
function loadBusinessProfitLoss(...args) { return requireDeps().loadBusinessProfitLoss(...args); }
function loadBusinessBalanceSheet(...args) { return requireDeps().loadBusinessBalanceSheet(...args); }
function loadBusinessReceivablesPayables(...args) { return requireDeps().loadBusinessReceivablesPayables(...args); }
function loadBusinessAging(...args) { return requireDeps().loadBusinessAging(...args); }
function loadUnallocatedPayments(...args) { return requireDeps().loadUnallocatedPayments(...args); }
function loadAllocationReconciliation(...args) { return requireDeps().loadAllocationReconciliation(...args); }
function loadBusinessAllLedgers(...args) { return requireDeps().loadBusinessAllLedgers(...args); }
function loadBusinessGeneralLedger(...args) { return requireDeps().loadBusinessGeneralLedger(...args); }
function loadPeriodLocks(...args) { return requireDeps().loadPeriodLocks(...args); }
function loadGstSettlementPreview(...args) { return requireDeps().loadGstSettlementPreview(...args); }
function loadGstr1(...args) { return requireDeps().loadGstr1(...args); }
function loadCmp08(...args) { return requireDeps().loadCmp08(...args); }
function loadGstr4(...args) { return requireDeps().loadGstr4(...args); }
function loadGstr3b(...args) { return requireDeps().loadGstr3b(...args); }
function loadItcReversalPreview(...args) { return requireDeps().loadItcReversalPreview(...args); }
function loadTdsRegister(...args) { return requireDeps().loadTdsRegister(...args); }
function loadBankReconciliation(...args) { return requireDeps().loadBankReconciliation(...args); }
function loadBankCashBook(...args) { return requireDeps().loadBankCashBook(...args); }
function loadPartyStatement(...args) { return requireDeps().loadPartyStatement(...args); }
function loadFixedAssets(...args) { return requireDeps().loadFixedAssets(...args); }
function loadDimensions(...args) { return requireDeps().loadDimensions(...args); }
function loadDimensionReport(...args) { return requireDeps().loadDimensionReport(...args); }
function loadBranchConsolidatedReport(...args) { return requireDeps().loadBranchConsolidatedReport(...args); }
function loadInventoryItems(...args) { return requireDeps().loadInventoryItems(...args); }
function loadInventoryPolicy(...args) { return requireDeps().loadInventoryPolicy(...args); }
function loadStockMovements(...args) { return requireDeps().loadStockMovements(...args); }
function loadStockRegister(...args) { return requireDeps().loadStockRegister(...args); }
function loadClosingStockEntries(...args) { return requireDeps().loadClosingStockEntries(...args); }
function reportDateControls(...args) { return requireDeps().reportDateControls(...args); }
function renderBusinessTrialBalance(...args) { return requireDeps().renderBusinessTrialBalance(...args); }
function renderBusinessProfitLoss(...args) { return requireDeps().renderBusinessProfitLoss(...args); }
function renderBusinessBalanceSheet(...args) { return requireDeps().renderBusinessBalanceSheet(...args); }
function renderBusinessGeneralLedger(...args) { return requireDeps().renderBusinessGeneralLedger(...args); }
function renderBusinessReceivablesPayables(...args) { return requireDeps().renderBusinessReceivablesPayables(...args); }
function renderBusinessAging(...args) { return requireDeps().renderBusinessAging(...args); }
function renderPaymentAllocation(...args) { return requireDeps().renderPaymentAllocation(...args); }
function renderPeriodLocksPanel(...args) { return requireDeps().renderPeriodLocksPanel(...args); }
function renderGstSettlementPanel(...args) { return requireDeps().renderGstSettlementPanel(...args); }
function renderGstReturns(...args) { return requireDeps().renderGstReturns(...args); }
function renderItcReversalPanel(...args) { return requireDeps().renderItcReversalPanel(...args); }
function renderTdsRegisterPanel(...args) { return requireDeps().renderTdsRegisterPanel(...args); }
function renderBankReconPanel(...args) { return requireDeps().renderBankReconPanel(...args); }
function renderBankCashBookPanel(...args) { return requireDeps().renderBankCashBookPanel(...args); }
function renderStatementsPanel(...args) { return requireDeps().renderStatementsPanel(...args); }
function renderOpeningYearEndPanel(...args) { return requireDeps().renderOpeningYearEndPanel(...args); }
function renderFixedAssetsPanel(...args) { return requireDeps().renderFixedAssetsPanel(...args); }
function renderDimensionsPanel(...args) { return requireDeps().renderDimensionsPanel(...args); }
function renderInventoryPanel(...args) { return requireDeps().renderInventoryPanel(...args); }

export function reportResultPayload(result, extra = {}) {
  if (result.ok) {
    return { ok: true, ...(result.payload || {}), ...extra };
  }
  return { ok: false, status: result.status, detail: result.payload?.detail || null, ...extra };
}

export async function refreshCurrentBusinessReport() {
  const tab = getBusinessReportState().tab;
  if (tab === "trial-balance") {
    await loadBusinessTrialBalance();
  } else if (tab === "pnl") {
    await loadBusinessProfitLoss();
  } else if (tab === "balance-sheet") {
    await loadBusinessBalanceSheet();
  } else if (tab === "receivables-payables") {
    await loadBusinessReceivablesPayables();
  } else if (tab === "aging") {
    await loadBusinessAging();
  } else if (tab === "payment-allocation") {
    await loadUnallocatedPayments();
    await loadAllocationReconciliation();
  } else if (tab === "general-ledger") {
    if (getBusinessReportState().ledgerAccountId === "__all_nonzero__") {
      await loadBusinessAllLedgers();
    } else if (getBusinessReportState().ledgerAccountId) {
      await loadBusinessGeneralLedger(getBusinessReportState().ledgerAccountId);
    } else {
      rerenderBusinessReportsIfActive();
    }
  } else if (tab === "period-locks") {
    await loadPeriodLocks();
  } else if (tab === "gst-settlement") {
    await loadGstSettlementPreview(getGstReturnState().gstSettlementPeriod);
  } else if (tab === "gst-returns") {
    if (getGstReturnState().gstReturnType === "gstr1") { await loadGstr1(getGstReturnState().gstr3bPeriod); }
    else if (getGstReturnState().gstReturnType === "cmp08") { await loadCmp08(getGstReturnState().cmp08Quarter); }
    else if (getGstReturnState().gstReturnType === "gstr4") { await loadGstr4(getGstReturnState().gstr4Fy); }
    else if (getGstReturnState().gstReturnType === "gstr2b") { rerenderBusinessReportsIfActive(); }  // upload-driven
    else { await loadGstr3b(getGstReturnState().gstr3bPeriod); }
  } else if (tab === "itc-reversals") {
    await loadItcReversalPreview(getItcReversalAsOf());
  } else if (tab === "tds") {
    await loadTdsRegister(getTdsQuarter());
  } else if (tab === "bank-recon") {
    if (!hasLoadedBusinessAccounts()) await loadBusinessAccounts();
    if (getBankReconAccountId()) await loadBankReconciliation(getBankReconAccountId());
    else rerenderBusinessReportsIfActive();
  } else if (tab === "bank-cash-book") {
    await loadBankCashBook();
  } else if (tab === "statements") {
    if (!Array.isArray(getLastBusinessParties()) || getLastBusinessParties().length === 0) await loadBusinessParties();
    if (getStatementPartyId()) await loadPartyStatement();
    else rerenderBusinessReportsIfActive();
  } else if (tab === "opening-yearend") {
    // Workflow tab — both halves load on demand (Preview buttons).
    rerenderBusinessReportsIfActive();
  } else if (tab === "fixed-assets") {
    if (!hasLoadedBusinessAccounts()) await loadBusinessAccounts();
    await loadFixedAssets();
  } else if (tab === "dimensions") {
    await loadDimensions();
    await loadDimensionReport();
    await loadBranchConsolidatedReport();
  } else if (tab === "inventory") {
    await loadInventoryItems();
    if (getLastInventoryItems()?.inventory_enabled) {
      await loadInventoryPolicy();
      await loadStockMovements();
      await loadStockRegister();
      await loadClosingStockEntries();
    } else {
      rerenderBusinessReportsIfActive();
    }
  }
}

export function rerenderBusinessReportsIfActive() {
  const reportWorkspaces = ["reports", "gst-returns", "reconciliation", "tds-tcs", "bank-recon"];
  if (getCurrentExperience() === "mitrabooks" && reportWorkspaces.includes(getActiveBusinessWorkspace())) {
    getDashboardPreview().innerHTML = renderBusinessWorkspace();
  }
}

export function reportExportToolbar(reportKey, { kind = "", label = "" } = {}) {
  const kAttr = kind ? ` data-report-kind="${escapeHtml(kind)}"` : "";
  const key = escapeHtml(reportKey);
  const lbl = label ? `<span class="export-label muted">${escapeHtml(label)}</span>` : "";
  const tallyXml = reportKey === "trial_balance"
    ? `<button class="secondary" type="button" data-business-action="export-tally-xml">Tally XML</button>`
    : "";
  return `
    <div class="report-export-toolbar" style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:8px 0;">
      ${lbl}
      <button class="secondary" type="button" data-business-action="export-report" data-report-key="${key}" data-report-format="csv"${kAttr}>CSV</button>
      <button class="secondary" type="button" data-business-action="export-report" data-report-key="${key}" data-report-format="xlsx"${kAttr}>Excel</button>
      <button class="secondary" type="button" data-business-action="export-report" data-report-key="${key}" data-report-format="pdf"${kAttr}>PDF</button>
      <button class="secondary" type="button" data-business-action="export-report" data-report-key="${key}" data-report-format="json"${kAttr}>JSON</button>
      ${tallyXml}
      <button class="secondary" type="button" data-business-action="print-report" title="Open a printable view">Print</button>
    </div>`;
}

export function businessReportExports() {
  const tab = getBusinessReportState().tab;
  if (tab === "trial-balance") return reportExportToolbar("trial_balance");
  if (tab === "balance-sheet") return reportExportToolbar("balance_sheet");
  if (tab === "pnl") return reportExportToolbar("profit_loss");
  if (tab === "aging") return reportExportToolbar("aging", { kind: getBusinessReportState().agingKind });
  if (tab === "payment-allocation") return "";  // workflow screen has its own controls
  if (tab === "itc-reversals") return reportExportToolbar("itc_reversals");
  if (tab === "statements") {
    return getStatementPartyId() ? reportExportToolbar("statement", { kind: getStatementKind() }) : "";
  }
  if (tab === "receivables-payables") {
    return `
      ${reportExportToolbar("party_ledger", { kind: "receivable", label: "Debtors:" })}
      ${reportExportToolbar("party_ledger", { kind: "payable", label: "Creditors:" })}`;
  }
  if (tab === "general-ledger") {
    const acc = getBusinessReportState().ledgerAccountId;
    if (acc && acc !== "__all_nonzero__") {
      return reportExportToolbar("general_ledger");
    }
    return `
      <div class="report-export-toolbar" style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:8px 0;">
        <span class="muted">Select a single account to download (CSV/Excel/PDF). "All Ledger Accounts" supports Print only.</span>
        <button class="secondary" type="button" data-business-action="print-report" title="Open a printable view">Print</button>
      </div>`;
  }
  return `
    <div class="report-export-toolbar" style="display:flex;gap:6px;align-items:center;margin:8px 0;">
      <button class="secondary" type="button" data-business-action="print-report" title="Open a printable view">Print</button>
    </div>`;
}

export async function downloadBusinessReport(reportKey, format, kind) {
  if (!reportKey) return;
  const params = new URLSearchParams();
  params.set("report", reportKey);
  params.set("format", format || "csv");
  if (kind) params.set("kind", kind);
  if (getBusinessReportState().as_of) params.set("as_of", getBusinessReportState().as_of);
  if (reportKey === "profit_loss") {
    if (getBusinessReportState().from_date) params.set("from_date", getBusinessReportState().from_date);
    if (getBusinessReportState().to_date) params.set("to_date", getBusinessReportState().to_date);
  }
  if (reportKey === "general_ledger") {
    const acc = getBusinessReportState().ledgerAccountId;
    if (!acc || acc === "__all_nonzero__") {
      renderJson(getApiOutput(), { export_error: { report: reportKey, detail: "Select a single ledger account before downloading." } });
      return;
    }
    params.set("account_id", acc);
  }
  if (reportKey === "statement") {
    if (!getStatementPartyId()) {
      renderJson(getApiOutput(), { export_error: { report: reportKey, detail: "Select a party before downloading the statement." } });
      return;
    }
    params.set("party_id", getStatementPartyId());
    params.set("kind", getStatementKind());
    if (getStatementFromDate()) params.set("from_date", getStatementFromDate());
    if (getStatementToDate()) params.set("to_date", getStatementToDate());
  }
  const periodStamp = reportKey === "profit_loss"
    ? `${getBusinessReportState().from_date}_${getBusinessReportState().to_date}`
    : getBusinessReportState().as_of;
  const filename = `${reportKey}${kind ? "_" + kind : ""}_${periodStamp}.${format || "csv"}`;
  const path = `/api/v1/business/reports/export?${params.toString()}`;
  const result = await downloadApiFile("mitrabooks", path, filename, { timeoutMs: 30000 });
  if (result.ok) {
    renderJson(getApiOutput(), { export: { report: reportKey, format, kind: kind || null, filename } });
  } else {
    renderJson(getApiOutput(), { export_error: { report: reportKey, format, status: result.status, detail: result.payload?.detail || result.payload } });
  }
}

export async function downloadTallyXmlExport() {
  const params = new URLSearchParams();
  if (getBusinessReportState().as_of) params.set("as_of", getBusinessReportState().as_of);
  const filename = `tally_trial_balance_${getBusinessReportState().as_of || todayIsoDate()}.xml`;
  const result = await downloadApiFile("mitrabooks", `/api/v1/business/tally/xml-export?${params.toString()}`, filename, { timeoutMs: 30000 });
  if (result.ok) {
    renderJson(getApiOutput(), { tally_xml_export: { report: "trial_balance", filename } });
  } else {
    renderJson(getApiOutput(), { tally_xml_export_error: { status: result.status, detail: result.payload?.detail || result.payload } });
  }
}

export function printBusinessReport() {
  const node = document.getElementById("business-report-printable");
  if (!node) { window.print(); return; }
  const win = window.open("", "_blank", "width=940,height=720");
  if (!win) { window.print(); return; }
  win.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>Financial Report</title>
    <style>
      body{font-family:Arial,Helvetica,sans-serif;color:#111;margin:24px;}
      h3,h4{margin:0 0 6px;}
      table{border-collapse:collapse;width:100%;font-size:12px;margin:8px 0 18px;}
      th,td{border:1px solid #ccc;padding:4px 8px;text-align:left;}
      td.amount,th.amount,.amount,.num,td.right{text-align:right;}
      .muted{color:#666;font-size:11px;}
      button,.report-export-toolbar,.report-tabs,.report-date-controls,input,select{display:none!important;}
    </style></head><body>${node.innerHTML}</body></html>`);
  win.document.close();
  win.focus();
  setTimeout(() => { try { win.print(); } catch (_e) {} }, 300);
}

export function downloadJsonObject(payload, filename) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function printBusinessDocumentDetail(title, selector) {
  const node = document.querySelector(selector);
  if (!node) { window.print(); return; }
  const win = window.open("", "_blank", "width=940,height=720");
  if (!win) { window.print(); return; }
  win.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${escapeHtml(title)}</title>
    <style>
      body{font-family:Arial,Helvetica,sans-serif;color:#111;margin:24px;}
      h3,h4{margin:0 0 6px;}
      table{border-collapse:collapse;width:100%;font-size:12px;margin:8px 0 18px;}
      th,td{border:1px solid #ccc;padding:4px 8px;text-align:left;}
      td.amount,th.amount,.amount,.num,td.right{text-align:right;}
      .muted{color:#666;font-size:11px;}
      button,.invoice-detail-actions,.reversal-panel,input,select{display:none!important;}
    </style></head><body>${node.innerHTML}</body></html>`);
  win.document.close();
  win.focus();
  setTimeout(() => { try { win.print(); } catch (_e) {} }, 300);
}

export function downloadCreditNoteJson() {
  if (!getCreditUi().detail) {
    renderJson(getApiOutput(), { credit_note_export_error: { detail: "Open a credit note before exporting." } });
    return;
  }
  const filename = `${getCreditUi().detail.credit_note_number || getCreditUi().detail.credit_note_id || "credit_note"}.json`;
  downloadJsonObject(getCreditUi().detail, filename);
  renderJson(getApiOutput(), { credit_note_export: { format: "json", filename } });
}

export function downloadDebitNoteJson() {
  if (!getDebitUi().detail) {
    renderJson(getApiOutput(), { debit_note_export_error: { detail: "Open a debit note before exporting." } });
    return;
  }
  const filename = `${getDebitUi().detail.debit_note_number || getDebitUi().detail.debit_note_id || "debit_note"}.json`;
  downloadJsonObject(getDebitUi().detail, filename);
  renderJson(getApiOutput(), { debit_note_export: { format: "json", filename } });
}

export function printCreditNoteDetail() {
  printBusinessDocumentDetail("Credit Note", "[data-credit-note-printable]");
  renderJson(getApiOutput(), { credit_note_print: { ok: true } });
}

export function printDebitNoteDetail() {
  printBusinessDocumentDetail("Debit Note", "[data-debit-note-printable]");
  renderJson(getApiOutput(), { debit_note_print: { ok: true } });
}

export function renderBusinessReportsWorkspace() {
  const tabs = getBusinessReportTabs().map((tab) => `
    <button
      class="report-tab ${getBusinessReportState().tab === tab.id ? "active" : ""}"
      type="button"
      data-business-action="report-tab"
      data-report-tab="${escapeHtml(tab.id)}"
    >${escapeHtml(tab.label)}</button>
  `).join("");

  let body = "";
  if (getBusinessReportState().tab === "trial-balance") {
    body = renderBusinessTrialBalance();
  } else if (getBusinessReportState().tab === "pnl") {
    body = renderBusinessProfitLoss();
  } else if (getBusinessReportState().tab === "balance-sheet") {
    body = renderBusinessBalanceSheet();
  } else if (getBusinessReportState().tab === "general-ledger") {
    body = renderBusinessGeneralLedger();
  } else if (getBusinessReportState().tab === "receivables-payables") {
    body = renderBusinessReceivablesPayables();
  } else if (getBusinessReportState().tab === "aging") {
    body = renderBusinessAging();
  } else if (getBusinessReportState().tab === "payment-allocation") {
    body = renderPaymentAllocation();
  } else if (getBusinessReportState().tab === "period-locks") {
    body = renderPeriodLocksPanel();
  } else if (getBusinessReportState().tab === "gst-settlement") {
    body = renderGstSettlementPanel();
  } else if (getBusinessReportState().tab === "gst-returns") {
    body = renderGstReturns();
  } else if (getBusinessReportState().tab === "itc-reversals") {
    body = renderItcReversalPanel();
  } else if (getBusinessReportState().tab === "tds") {
    body = renderTdsRegisterPanel();
  } else if (getBusinessReportState().tab === "bank-recon") {
    body = renderBankReconPanel();
  } else if (getBusinessReportState().tab === "bank-cash-book") {
    body = renderBankCashBookPanel();
  } else if (getBusinessReportState().tab === "statements") {
    body = renderStatementsPanel();
  } else if (getBusinessReportState().tab === "opening-yearend") {
    body = renderOpeningYearEndPanel();
  } else if (getBusinessReportState().tab === "fixed-assets") {
    body = renderFixedAssetsPanel();
  } else if (getBusinessReportState().tab === "dimensions") {
    body = renderDimensionsPanel();
  } else if (getBusinessReportState().tab === "inventory") {
    body = renderInventoryPanel();
  }

  return `
    <div class="verification-panel erp-workspace-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Financial Reports</h4>
          <p>Live reports from posted ledger entries for this tenant.</p>
        </div>
      </div>
      <div class="report-tabs" role="tablist">${tabs}</div>
      ${reportDateControls()}
      ${businessReportExports()}
      <div id="business-report-printable">${body}</div>
    </div>
  `;
}

export function reportUnavailablePanel(title, payload) {
  const detail = payload?.detail || "Report unavailable. Check accounting access and try again.";
  return `
    <div class="table-preview compact-table">
      <h4>${escapeHtml(title)}</h4>
      <p class="muted">${escapeHtml(detail)}</p>
    </div>
  `;
}

