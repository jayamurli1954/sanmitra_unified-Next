// ====================================================================
// SECTION: FINANCIAL REPORTS (TB / P&L / BS / GL / R&P)
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initFinancialReports(...).
// Hub (refreshCurrentBusinessReport / renderBusinessReportsWorkspace) stays in app.js.
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastBusinessTrialBalance = null;
export let lastBusinessProfitLoss = null;
export let lastBusinessBalanceSheet = null;
export let lastBusinessReceivables = null;
export let lastBusinessPayables = null;
export let lastBusinessGeneralLedger = null;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initFinancialReports(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initFinancialReports() must be called before using financial-report helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function reportUnavailablePanel(title, payload) { return requireDeps().reportUnavailablePanel(title, payload); }
function reportResultPayload(result, extra = {}) { return requireDeps().reportResultPayload(result, extra); }
function rerenderBusinessReportsIfActive() { return requireDeps().rerenderBusinessReportsIfActive(); }
function findBusinessAccountById(accountId) { return requireDeps().findBusinessAccountById(accountId); }
function accountRowsFromPayload(payload) { return requireDeps().accountRowsFromPayload(payload); }
function businessAccountsForSelection() { return requireDeps().businessAccountsForSelection(); }
function renderStatCards(stats) { return requireDeps().renderStatCards(stats); }
function isBusinessReportTab(tab) { return requireDeps().isBusinessReportTab(tab); }
function setBankCashBookType(value) { return requireDeps().setBankCashBookType(value); }
function getBankCashBookType() { return requireDeps().getBankCashBookType(); }
function getBusinessReportState() { return requireDeps().getBusinessReportState(); }
function refreshCurrentBusinessReport() { return requireDeps().refreshCurrentBusinessReport(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

export async function loadBusinessTrialBalance() {
  const result = await apiRequest("mitrabooks", `/api/v1/accounting/reports/trial-balance?as_of=${encodeURIComponent(getBusinessReportState().as_of)}`, { method: "GET" });
  lastBusinessTrialBalance = reportResultPayload(result);
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { trial_balance: { ok: result.ok, status: result.status } });
}


export async function loadBusinessProfitLoss() {
  const result = await apiRequest("mitrabooks", `/api/v1/accounting/reports/pnl?from_date=${encodeURIComponent(getBusinessReportState().from_date)}&to_date=${encodeURIComponent(getBusinessReportState().to_date)}`, { method: "GET" });
  lastBusinessProfitLoss = reportResultPayload(result);
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { profit_loss: { ok: result.ok, status: result.status } });
}


export async function loadBusinessBalanceSheet() {
  const result = await apiRequest("mitrabooks", `/api/v1/accounting/reports/balance-sheet?as_of=${encodeURIComponent(getBusinessReportState().as_of)}`, { method: "GET" });
  lastBusinessBalanceSheet = reportResultPayload(result);
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { balance_sheet: { ok: result.ok, status: result.status } });
}


export async function loadBusinessReceivablesPayables() {
  // Party-wise Sundry Debtors / Creditors; totals tie to the matching Trial Balance account.
  const asOf = encodeURIComponent(getBusinessReportState().as_of);
  const [arResult, apResult] = await Promise.all([
    apiRequest("mitrabooks", `/api/v1/business/party-ledger?kind=receivable&as_of=${asOf}`, { method: "GET" }),
    apiRequest("mitrabooks", `/api/v1/business/party-ledger?kind=payable&as_of=${asOf}`, { method: "GET" }),
  ]);
  lastBusinessReceivables = reportResultPayload(arResult);
  lastBusinessPayables = reportResultPayload(apResult);
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { receivables: { ok: arResult.ok }, payables: { ok: apResult.ok } });
}



export async function loadBusinessGeneralLedger(accountId) {
  getBusinessReportState().ledgerAccountId = String(accountId || "");
  const account = findBusinessAccountById(accountId);
  const label = account ? `${account.code} - ${account.name}` : String(accountId);
  lastBusinessGeneralLedger = { loading: true, account_label: label };
  rerenderBusinessReportsIfActive();
  const result = await apiRequest("mitrabooks", `/api/v1/accounting/ledger/${encodeURIComponent(accountId)}`, { method: "GET" });
  if (result.ok) {
    const lines = Array.isArray(result.payload) ? result.payload : accountRowsFromPayload(result.payload);
    lastBusinessGeneralLedger = { ok: true, account_id: accountId, account_label: label, lines };
  } else {
    lastBusinessGeneralLedger = { ok: false, account_id: accountId, account_label: label, detail: result.payload?.detail || null };
  }
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { general_ledger: { ok: result.ok, status: result.status, account_id: accountId } });
}


export function reportDateControls() {
  const tab = getBusinessReportState().tab;
  const asOfTabs = ["trial-balance", "balance-sheet", "receivables-payables", "aging"];
  if (tab === "pnl" || tab === "bank-cash-book") {
    const bookTypeControl = tab === "bank-cash-book"
      ? `<label>Book
          <select name="book_type">
            <option value="all" ${getBankCashBookType() === "all" ? "selected" : ""}>All cash/bank</option>
            <option value="cash" ${getBankCashBookType() === "cash" ? "selected" : ""}>Cash book</option>
            <option value="bank" ${getBankCashBookType() === "bank" ? "selected" : ""}>Bank book</option>
          </select>
        </label>`
      : "";
    return `
      <div class="report-date-controls" data-business-report-filters>
        <label>From <input type="date" name="from_date" value="${escapeHtml(getBusinessReportState().from_date)}"></label>
        <label>To <input type="date" name="to_date" value="${escapeHtml(getBusinessReportState().to_date)}"></label>
        ${bookTypeControl}
        <button class="secondary" type="button" data-business-action="apply-report-filter">Apply</button>
      </div>
    `;
  }
  if (asOfTabs.includes(tab)) {
    return `
      <div class="report-date-controls" data-business-report-filters>
        <label>As of <input type="date" name="as_of" value="${escapeHtml(getBusinessReportState().as_of)}"></label>
        <button class="secondary" type="button" data-business-action="apply-report-filter">Apply</button>
      </div>
    `;
  }
  return "";
}


export function renderBusinessTrialBalance() {
  const payload = lastBusinessTrialBalance;
  if (!payload) {
    return `<p class="muted">Loading trial balance...</p>`;
  }
  if (payload.ok === false) {
    return reportUnavailablePanel("Trial Balance", payload);
  }
  const rows = Array.isArray(payload.lines) ? payload.lines : [];
  // Show the NET balance per account in its natural column (Dr if positive, Cr if negative).
  // Totals are the sums of those nets, which still balance.
  let netDebitTotal = 0;
  let netCreditTotal = 0;
  const bodyRows = rows.map((row) => {
    const net = Number(row.net_balance != null ? row.net_balance : (Number(row.debit_total || 0) - Number(row.credit_total || 0)));
    const debitCell = net >= 0 ? net : 0;
    const creditCell = net < 0 ? -net : 0;
    netDebitTotal += debitCell;
    netCreditTotal += creditCell;
    return `
      <tr>
        <td>${escapeHtml(row.account_code || "")}</td>
        <td>${escapeHtml(row.account_name || "")}</td>
        <td class="amount">${debitCell ? escapeHtml(formatCurrency(debitCell)) : ""}</td>
        <td class="amount">${creditCell ? escapeHtml(formatCurrency(creditCell)) : ""}</td>
        <td>
          <button class="secondary" type="button" data-business-action="report-ledger" data-account-id="${escapeHtml(row.account_id || "")}">Open</button>
        </td>
      </tr>`;
  }).join("");
  return `
    <div class="preview-heading compact">
      <div><p>As of ${escapeHtml(payload.as_of || getBusinessReportState().as_of)}. Net balance per account; debit and credit totals must match.</p></div>
      <span class="pill ${payload.balanced ? "ok" : "warn"}">${payload.balanced ? "balanced" : "not balanced"}</span>
    </div>
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Code</th>
            <th>Account</th>
            <th class="amount">Debit</th>
            <th class="amount">Credit</th>
            <th>Ledger</th>
          </tr>
        </thead>
        <tbody>
          ${rows.length ? bodyRows : `
            <tr><td colspan="5" class="muted">No posted balances found for this tenant.</td></tr>
          `}
        </tbody>
        <tfoot>
          <tr>
            <th colspan="2">Total</th>
            <th class="amount">${escapeHtml(formatCurrency(netDebitTotal))}</th>
            <th class="amount">${escapeHtml(formatCurrency(netCreditTotal))}</th>
            <th></th>
          </tr>
        </tfoot>
      </table>
    </div>
  `;
}


export function renderBusinessProfitLoss() {
  const payload = lastBusinessProfitLoss;
  if (!payload) {
    return `<p class="muted">Loading profit & loss...</p>`;
  }
  if (payload.ok === false) {
    return reportUnavailablePanel("Profit & Loss", payload);
  }
  const lines = Array.isArray(payload.lines) ? payload.lines : [];
  return `
    <div class="preview-heading compact">
      <div><p>${escapeHtml(payload.from_date || getBusinessReportState().from_date)} to ${escapeHtml(payload.to_date || getBusinessReportState().to_date)}</p></div>
      <span class="pill ${Number(payload.net_profit || 0) >= 0 ? "ok" : "warn"}">${escapeHtml(formatCurrency(payload.net_profit || 0))}</span>
    </div>
    <div class="metric-grid three">
      ${renderStatCards([
        ["Income", formatCurrency(payload.income_total || 0), "posted income"],
        ["Expenses", formatCurrency(payload.expense_total || 0), "posted expenses"],
        ["Net Profit", formatCurrency(payload.net_profit || 0), "income less expense"],
      ])}
    </div>
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Code</th>
            <th>Account</th>
            <th>Type</th>
            <th class="amount">Debit</th>
            <th class="amount">Credit</th>
            <th class="amount">Net</th>
          </tr>
        </thead>
        <tbody>
          ${lines.length ? lines.map((line) => `
            <tr>
              <td>${escapeHtml(line.account_code || "")}</td>
              <td>${escapeHtml(line.account_name || "")}</td>
              <td>${escapeHtml(line.account_type || "")}</td>
              <td class="amount">${escapeHtml(formatCurrency(line.debit_total || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(line.credit_total || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(line.net_amount || 0))}</td>
            </tr>
          `).join("") : `
            <tr><td colspan="6" class="muted">No income or expense rows found for this period.</td></tr>
          `}
        </tbody>
      </table>
    </div>
  `;
}


export function renderBusinessBalanceSheet() {
  const payload = lastBusinessBalanceSheet;
  if (!payload) {
    return `<p class="muted">Loading balance sheet...</p>`;
  }
  if (payload.ok === false) {
    return reportUnavailablePanel("Balance Sheet", payload);
  }
  const assets = Array.isArray(payload.assets) ? payload.assets : [];
  const liabilities = Array.isArray(payload.liabilities) ? payload.liabilities : [];
  const equity = Array.isArray(payload.equity) ? payload.equity : [];
  const totalAssets = Number(payload.total_assets || 0);
  const liabPlusEquity = Number(payload.total_liabilities || 0) + Number(payload.total_equity || 0);

  const bsRows = (rows) => rows.length
    ? rows.map((line) => `
        <tr>
          <td>${escapeHtml(line.account_code || "")}</td>
          <td>${escapeHtml(line.account_name || "")}</td>
          <td class="amount">${escapeHtml(formatCurrency(line.balance || 0))}</td>
        </tr>`).join("")
    : `<tr><td colspan="3" class="muted">No rows.</td></tr>`;
  const subHead = (label) => `<tr><td colspan="3" style="font-weight:600;padding-top:8px;">${escapeHtml(label)}</td></tr>`;
  const totalRow = (label, value) => `
    <tr style="font-weight:700;border-top:2px solid var(--border, #3a3f4b);">
      <td colspan="2">${escapeHtml(label)}</td>
      <td class="amount">${escapeHtml(formatCurrency(value))}</td>
    </tr>`;
  const sideTable = (title, bodyHtml) => `
    <div class="table-preview compact-table">
      <h4>${escapeHtml(title)}</h4>
      <table>
        <thead><tr><th>Code</th><th>Account</th><th class="amount">Amount</th></tr></thead>
        <tbody>${bodyHtml}</tbody>
      </table>
    </div>`;

  // Standard two-sided balance sheet: Liabilities & Equity on the left, Assets on
  // the right; each side totals to the same figure when balanced. The grid
  // auto-stacks to one column on narrow screens so it always fits.
  return `
    <div class="preview-heading compact">
      <div><p>As of ${escapeHtml(payload.as_of || getBusinessReportState().as_of)}. Assets = Liabilities + Equity.</p></div>
      <span class="pill ${payload.balanced ? "ok" : "warn"}">${payload.balanced ? "balanced" : "not balanced"}</span>
    </div>
    <div class="bs-tformat" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;align-items:start;">
      ${sideTable("Liabilities & Equity",
        subHead("Capital & Reserves (Equity)") + bsRows(equity) +
        subHead("Liabilities") + bsRows(liabilities) +
        totalRow("Total Liabilities + Equity", liabPlusEquity))}
      ${sideTable("Assets",
        bsRows(assets) + totalRow("Total Assets", totalAssets))}
    </div>
  `;
}


export function renderBusinessGeneralLedger() {
  const accounts = businessAccountsForSelection();
  const selector = `
    <div class="report-date-controls" data-business-report-ledger>
      <label>Account
        <select name="ledger_account" aria-label="Select ledger account">
          <option value="">Select an account</option>
          <option value="__all_nonzero__" ${getBusinessReportState().ledgerAccountId === "__all_nonzero__" ? "selected" : ""}>All Ledger Accounts &gt; 0</option>
          ${accounts.map((acc) => `
            <option value="${escapeHtml(acc.id)}" ${String(acc.id) === String(getBusinessReportState().ledgerAccountId) ? "selected" : ""}>
              ${escapeHtml(`${acc.code} - ${acc.name}`)}
            </option>
          `).join("")}
        </select>
      </label>
      <button class="secondary" type="button" data-business-action="load-report-ledger">View Ledger</button>
    </div>
  `;

  const payload = lastBusinessGeneralLedger;
  let trace = "";
  if (!payload) {
    trace = `<p class="muted">Select an account to view its posted ledger entries.</p>`;
  } else if (payload.loading) {
    trace = `<p class="muted">Loading ledger for ${escapeHtml(payload.account_label || "selected account")}...</p>`;
  } else if (payload.ok === false) {
    trace = reportUnavailablePanel(`Ledger: ${payload.account_label || ""}`, payload);
  } else if (payload.multi) {
    const ledgers = Array.isArray(payload.ledgers) ? payload.ledgers : [];
    trace = ledgers.length
      ? ledgers.map((l) => renderLedgerTraceTable(l.account_label, l.lines, l.ok === false ? l.detail : null)).join("")
      : `<p class="muted">No accounts with posted movement as of ${escapeHtml(getBusinessReportState().as_of)}.</p>`;
  } else {
    trace = renderLedgerTraceTable(payload.account_label, payload.lines);
  }
  return selector + trace;
}


export function renderLedgerTraceTable(label, lines, errorDetail = null) {
  if (errorDetail) {
    return `
      <div class="table-preview compact-table">
        <h4>Ledger: ${escapeHtml(label || "")}</h4>
        <p class="muted">${escapeHtml(errorDetail)}</p>
      </div>
    `;
  }
  const rows = Array.isArray(lines) ? lines : [];
  return `
    <div class="table-preview compact-table">
      <h4>Ledger: ${escapeHtml(label || "")}</h4>
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Reference</th>
            <th>Description</th>
            <th class="amount">Debit</th>
            <th class="amount">Credit</th>
            <th class="amount">Balance</th>
          </tr>
        </thead>
        <tbody>
          ${rows.length ? rows.map((line) => `
            <tr>
              <td>${escapeHtml(line.entry_date || "")}</td>
              <td>${escapeHtml(line.reference || "")}</td>
              <td>${escapeHtml(line.description || "")}</td>
              <td class="amount">${escapeHtml(formatCurrency(line.debit || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(line.credit || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(line.running_balance || 0))}</td>
            </tr>
          `).join("") : `<tr><td colspan="6" class="muted">No posted entries for this account.</td></tr>`}
        </tbody>
      </table>
    </div>
  `;
}


export async function loadBusinessAllLedgers() {
  getBusinessReportState().ledgerAccountId = "__all_nonzero__";
  lastBusinessGeneralLedger = { loading: true, account_label: "All Ledger Accounts > 0" };
  rerenderBusinessReportsIfActive();

  const tbResult = await apiRequest("mitrabooks", `/api/v1/accounting/reports/trial-balance?as_of=${encodeURIComponent(getBusinessReportState().as_of)}`, { method: "GET" });
  if (!tbResult.ok) {
    lastBusinessGeneralLedger = { ok: false, account_label: "All Ledger Accounts > 0", detail: tbResult.payload?.detail || "Could not load account list." };
    rerenderBusinessReportsIfActive();
    return;
  }
  const lines = Array.isArray(tbResult.payload?.lines) ? tbResult.payload.lines : [];
  const active = lines.filter((l) => (Number(l.debit_total || 0) + Number(l.credit_total || 0)) > 0);

  lastBusinessGeneralLedger = { loading: true, account_label: `All Ledger Accounts > 0 (${active.length})` };
  rerenderBusinessReportsIfActive();

  const ledgers = [];
  for (const l of active) {
    const r = await apiRequest("mitrabooks", `/api/v1/accounting/ledger/${encodeURIComponent(l.account_id)}`, { method: "GET" });
    ledgers.push({
      account_id: l.account_id,
      account_label: `${l.account_code || ""} - ${l.account_name || ""}`.trim(),
      ok: r.ok,
      lines: r.ok ? (Array.isArray(r.payload) ? r.payload : accountRowsFromPayload(r.payload)) : [],
      detail: r.ok ? null : (r.payload?.detail || "Ledger unavailable."),
    });
  }
  lastBusinessGeneralLedger = { ok: true, multi: true, account_label: "All Ledger Accounts > 0", ledgers };
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { general_ledger_all: { ok: true, accounts: ledgers.length } });
}


export function renderReceivablesPayablesSection(title, subtitle, payload) {
  if (!payload) {
    return `
      <article>
        <h4>${escapeHtml(title)}</h4>
        <p class="muted">Loading...</p>
      </article>
    `;
  }
  if (payload.ok === false) {
    return `
      <article>
        <h4>${escapeHtml(title)}</h4>
        <p class="muted">${escapeHtml(payload.detail || "Report unavailable. Check accounting access and try again.")}</p>
      </article>
    `;
  }
  // Party-wise rows from /business/party-ledger (items: party_name + balance);
  // falls back to legacy account-level "lines" if present.
  const lines = Array.isArray(payload.items) ? payload.items : (Array.isArray(payload.lines) ? payload.lines : []);
  return `
    <article>
      <h4>${escapeHtml(title)} <span class="pill">${escapeHtml(formatCurrency(payload.total_balance || 0))}</span></h4>
      <p class="muted">${escapeHtml(subtitle)}</p>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr><th>Party</th><th class="amount">Balance</th></tr>
          </thead>
          <tbody>
            ${lines.length ? lines.map((line) => `
              <tr>
                <td>${escapeHtml(line.party_name || line.account_name || "")}</td>
                <td class="amount">${escapeHtml(formatCurrency(line.balance || 0))}</td>
              </tr>
            `).join("") : `<tr><td colspan="2" class="muted">No outstanding balances.</td></tr>`}
          </tbody>
        </table>
      </div>
    </article>
  `;
}


export function renderBusinessReceivablesPayables() {
  return `
    <div class="preview-heading compact">
      <div><p>Party-wise outstanding as of ${escapeHtml(getBusinessReportState().as_of)}. Totals tie to the Sundry Debtors / Creditors balances in the Trial Balance.</p></div>
    </div>
    <div class="dashboard-main-grid platform-grid">
      ${renderReceivablesPayablesSection("Sundry Debtors", "Amounts owed by customers, party-wise. 'Unallocated' = direct entries with no party tag.", lastBusinessReceivables)}
      ${renderReceivablesPayablesSection("Sundry Creditors", "Amounts owed to vendors, party-wise. 'Unallocated' = direct entries with no party tag.", lastBusinessPayables)}
    </div>
  `;
}



export function setBusinessReportTab(tab) {
  if (!isBusinessReportTab(tab)) {
    return;
  }
  getBusinessReportState().tab = tab;
  rerenderBusinessReportsIfActive();
  refreshCurrentBusinessReport();
}


export function applyBusinessReportFilter() {
  const panel = document.querySelector("[data-business-report-filters]");
  if (panel) {
    const asOf = panel.querySelector("input[name='as_of']");
    const fromDate = panel.querySelector("input[name='from_date']");
    const toDate = panel.querySelector("input[name='to_date']");
    const bookType = panel.querySelector("select[name='book_type']");
    if (asOf && asOf.value) getBusinessReportState().as_of = asOf.value;
    if (fromDate && fromDate.value) getBusinessReportState().from_date = fromDate.value;
    if (toDate && toDate.value) getBusinessReportState().to_date = toDate.value;
    if (bookType && bookType.value) setBankCashBookType(bookType.value);
  }
  refreshCurrentBusinessReport();
}


export function loadBusinessReportLedgerFromSelect() {
  const panel = document.querySelector("[data-business-report-ledger]");
  const select = panel?.querySelector("select[name='ledger_account']");
  const accountId = select?.value || "";
  if (!accountId) {
    setLoginStatus("warn", "Select an account", "Choose an account to view its ledger.");
    return;
  }
  if (accountId === "__all_nonzero__") {
    loadBusinessAllLedgers();
    return;
  }
  loadBusinessGeneralLedger(accountId);
}


