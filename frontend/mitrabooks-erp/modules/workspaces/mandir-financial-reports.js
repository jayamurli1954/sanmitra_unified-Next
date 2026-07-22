// ====================================================================
// SECTION: MANDIR — financial reports (TB / I&E / B&P / BS)
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initMandirFinancialReports(...).
// ====================================================================

export const mandirReportState = {
  expenses: [],
  trialBalance: null,
  ledger: null,
  financialReports: {},
};

/** @type {{
 *   escapeHtml: (v: string) => string,
 *   formatCurrency: (v: number | string) => string,
 *   renderStatCards: (stats: unknown[]) => string,
 *   getDrilldownFromDate: () => string,
 *   getDrilldownToDate: () => string,
 *   todayIsoDate: () => string,
 * } | null} */
let deps = null;

export function initMandirFinancialReports({
  escapeHtml,
  formatCurrency,
  renderStatCards,
  getDrilldownFromDate,
  getDrilldownToDate,
  todayIsoDate,
}) {
  deps = {
    escapeHtml,
    formatCurrency,
    renderStatCards,
    getDrilldownFromDate,
    getDrilldownToDate,
    todayIsoDate,
  };
}

function requireDeps() {
  if (!deps) {
    throw new Error("initMandirFinancialReports() must be called before using Mandir report renderers");
  }
  return deps;
}

function escapeHtml(value) {
  return requireDeps().escapeHtml(value);
}

function formatCurrency(value) {
  return requireDeps().formatCurrency(value);
}

function renderStatCards(stats) {
  return requireDeps().renderStatCards(stats);
}

function accountingDrilldownFromDate() {
  return requireDeps().getDrilldownFromDate();
}

function accountingDrilldownToDate() {
  return requireDeps().getDrilldownToDate();
}

function todayIsoDate() {
  return requireDeps().todayIsoDate();
}

export function renderMandirExpensesTable(rows = mandirReportState.expenses) {
  const expenses = Array.isArray(rows) ? rows : [];
  return `
    <div class="verification-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Recent Expenses</h4>
          <p>Posted quick expenses created from the MandirMitra accounting form.</p>
        </div>
        <span class="pill">${expenses.length} shown</span>
      </div>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr>
              <th>Entry</th>
              <th>Date</th>
              <th>Narration</th>
              <th class="amount">Amount</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${expenses.length ? expenses.map((expense) => `
              <tr>
                <td>${escapeHtml(expense.entry_number || expense.id || "")}</td>
                <td>${escapeHtml(expense.entry_date || "")}</td>
                <td>${escapeHtml(expense.narration || expense.description || "")}</td>
                <td class="amount">${escapeHtml(formatCurrency(expense.total_amount || expense.total_debit || 0))}</td>
                <td><span class="pill ${expense.status === "posted" ? "ok" : "warn"}">${escapeHtml(expense.status || "draft")}</span></td>
              </tr>
            `).join("") : `
              <tr>
                <td colspan="5" class="muted">No expense entries found for this tenant/app context.</td>
              </tr>
            `}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

export function renderMandirTrialBalance(payload = mandirReportState.trialBalance) {
  if (!payload) {
    return "";
  }
  if (payload.ok === false) {
    return `
      <div class="verification-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Trial Balance</h4>
            <p>Accounting report unavailable. Check backend accounting access and run checks again.</p>
          </div>
          <span class="pill warn">unavailable</span>
        </div>
      </div>
    `;
  }
  const rows = Array.isArray(payload.lines) ? payload.lines : Array.isArray(payload.accounts) ? payload.accounts : [];
  return `
    <div class="verification-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Trial Balance</h4>
          <p>As of ${escapeHtml(payload.as_of || todayIsoDate())}. Debits and credits must match.</p>
        </div>
        <span class="pill ${payload.balanced ? "ok" : "warn"}">${payload.balanced ? "balanced" : "not balanced"}</span>
      </div>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr>
              <th>Account</th>
              <th>Name</th>
              <th class="amount">Debit</th>
              <th class="amount">Credit</th>
              <th>Trace</th>
            </tr>
          </thead>
          <tbody>
            ${rows.length ? rows.map((row) => `
              <tr>
                <td>${escapeHtml(row.account_code || row.account_id || "")}</td>
                <td>${escapeHtml(row.account_name || row.name || "")}</td>
                <td class="amount">${escapeHtml(formatCurrency(row.debit_total || row.debit || 0))}</td>
                <td class="amount">${escapeHtml(formatCurrency(row.credit_total || row.credit || 0))}</td>
                <td>
                  <button
                    class="secondary"
                    type="button"
                    data-accounting-action="tb-ledger"
                    data-account-id="${escapeHtml(row.account_id || row.account_code || "")}"
                  >Open</button>
                </td>
              </tr>
            `).join("") : `
              <tr>
                <td colspan="5" class="muted">No posted accounting balances found for this tenant/app context.</td>
              </tr>
            `}
          </tbody>
          <tfoot>
            <tr>
              <th colspan="2">Total</th>
              <th class="amount">${escapeHtml(formatCurrency(payload.total_debit || 0))}</th>
              <th class="amount">${escapeHtml(formatCurrency(payload.total_credit || 0))}</th>
              <th></th>
            </tr>
          </tfoot>
        </table>
      </div>
      ${renderMandirLedgerTrace()}
    </div>
  `;
}

function renderMandirLedgerTrace(payload = mandirReportState.ledger) {
  if (!payload) {
    return "";
  }
  if (payload.loading) {
    return `
      <div class="table-preview compact-table" id="mandir-ledger-trace">
        <h4>Ledger Trace</h4>
        <p class="muted">Loading posted voucher lines for ${escapeHtml(payload.account_label || "selected account")}...</p>
      </div>
    `;
  }
  if (payload.ok === false) {
    const detail = payload.payload?.detail || payload.detail || "Ledger trace unavailable for the selected account.";
    return `
      <div class="table-preview compact-table" id="mandir-ledger-trace">
        <h4>Ledger Trace</h4>
        <p class="muted">${escapeHtml(detail)}</p>
      </div>
    `;
  }
  const entries = Array.isArray(payload.entries) ? payload.entries : Array.isArray(payload.transactions) ? payload.transactions : [];
  return `
    <div class="table-preview compact-table" id="mandir-ledger-trace">
      <h4>Ledger Trace: ${escapeHtml(`${payload.account_code || payload.account_id || ""} ${payload.account_name || ""}`.trim())}</h4>
      <p class="muted">${escapeHtml(payload.from_date || "")} to ${escapeHtml(payload.to_date || "")}. Posted voucher lines for this account.</p>
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Voucher</th>
            <th>Narration</th>
            <th class="amount">Debit</th>
            <th class="amount">Credit</th>
            <th class="amount">Balance</th>
          </tr>
        </thead>
        <tbody>
          ${entries.length ? entries.map((entry) => `
            <tr>
              <td>${escapeHtml(entry.date || entry.entry_date || "")}</td>
              <td>${escapeHtml(entry.entry_number || entry.reference || "")}</td>
              <td>${escapeHtml(entry.narration || entry.description || "")}</td>
              <td class="amount">${escapeHtml(formatCurrency(entry.debit_amount || entry.debit || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(entry.credit_amount || entry.credit || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(entry.running_balance || entry.balance || 0))}</td>
            </tr>
          `).join("") : `
            <tr>
              <td colspan="6" class="muted">No posted voucher lines found for this account.</td>
            </tr>
          `}
        </tbody>
      </table>
    </div>
  `;
}

function reportUnavailable(title, payload) {
  if (!payload || payload.ok !== false) {
    return "";
  }
  const detail = payload.payload?.detail || "Report unavailable. Check backend accounting access and run checks again.";
  return `
    <div class="verification-panel">
      <div class="preview-heading compact">
        <div>
          <h4>${escapeHtml(title)}</h4>
          <p>${escapeHtml(detail)}</p>
        </div>
        <span class="pill warn">unavailable</span>
      </div>
    </div>
  `;
}

function renderMandirIncomeExpenditureReport(payload) {
  if (!payload) {
    return "";
  }
  if (payload.ok === false) {
    return reportUnavailable("Income & Expenditure", payload);
  }
  const lines = Array.isArray(payload.lines) ? payload.lines : [];
  return `
    <div class="verification-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Income & Expenditure</h4>
          <p>${escapeHtml(payload.from_date || accountingDrilldownFromDate())} to ${escapeHtml(payload.to_date || accountingDrilldownToDate())}</p>
        </div>
        <span class="pill ${Number(payload.net_profit || 0) >= 0 ? "ok" : "warn"}">${escapeHtml(formatCurrency(payload.net_profit || 0))}</span>
      </div>
      <div class="metric-grid three">
        ${renderStatCards([
          ["Income", formatCurrency(payload.income_total || 0), "posted income"],
          ["Expenditure", formatCurrency(payload.expense_total || 0), "posted expenses"],
          ["Net", formatCurrency(payload.net_profit || 0), "income less expense"],
        ])}
      </div>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr>
              <th>Account</th>
              <th>Name</th>
              <th>Type</th>
              <th class="amount">Debit</th>
              <th class="amount">Credit</th>
              <th class="amount">Net</th>
            </tr>
          </thead>
          <tbody>
            ${lines.length ? lines.map((line) => `
              <tr>
                <td>${escapeHtml(line.account_code || line.account_id || "")}</td>
                <td>${escapeHtml(line.account_name || "")}</td>
                <td>${escapeHtml(line.account_type || "")}</td>
                <td class="amount">${escapeHtml(formatCurrency(line.debit_total || 0))}</td>
                <td class="amount">${escapeHtml(formatCurrency(line.credit_total || 0))}</td>
                <td class="amount">${escapeHtml(formatCurrency(line.net_amount || 0))}</td>
              </tr>
            `).join("") : `
              <tr>
                <td colspan="6" class="muted">No income or expenditure rows found for this period.</td>
              </tr>
            `}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderMandirReceiptsPaymentsReport(payload) {
  if (!payload) {
    return "";
  }
  if (payload.ok === false) {
    return reportUnavailable("Receipts & Payments", payload);
  }
  const lines = Array.isArray(payload.lines) ? payload.lines : [];
  return `
    <div class="verification-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Receipts & Payments</h4>
          <p>${escapeHtml(payload.from_date || accountingDrilldownFromDate())} to ${escapeHtml(payload.to_date || accountingDrilldownToDate())}</p>
        </div>
        <span class="pill">${escapeHtml(formatCurrency(payload.net_receipts || 0))}</span>
      </div>
      <div class="metric-grid three">
        ${renderStatCards([
          ["Receipts", formatCurrency(payload.total_receipts || 0), "cash/bank debit"],
          ["Payments", formatCurrency(payload.total_payments || 0), "cash/bank credit"],
          ["Net Receipts", formatCurrency(payload.net_receipts || 0), "receipts less payments"],
        ])}
      </div>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr>
              <th>Account</th>
              <th>Name</th>
              <th class="amount">Receipts</th>
              <th class="amount">Payments</th>
              <th class="amount">Net</th>
            </tr>
          </thead>
          <tbody>
            ${lines.length ? lines.map((line) => `
              <tr>
                <td>${escapeHtml(line.account_code || line.account_id || "")}</td>
                <td>${escapeHtml(line.account_name || "")}</td>
                <td class="amount">${escapeHtml(formatCurrency(line.receipts || 0))}</td>
                <td class="amount">${escapeHtml(formatCurrency(line.payments || 0))}</td>
                <td class="amount">${escapeHtml(formatCurrency(line.net_receipts || 0))}</td>
              </tr>
            `).join("") : `
              <tr>
                <td colspan="5" class="muted">No cash or bank movements found for this period.</td>
              </tr>
            `}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderBalanceSheetRows(rows = []) {
  return rows.length ? rows.map((line) => `
    <tr>
      <td>${escapeHtml(line.account_code || line.account_id || "")}</td>
      <td>${escapeHtml(line.account_name || "")}</td>
      <td class="amount">${escapeHtml(formatCurrency(line.balance || 0))}</td>
    </tr>
  `).join("") : `
    <tr>
      <td colspan="3" class="muted">No rows.</td>
    </tr>
  `;
}

function renderMandirBalanceSheetReport(payload) {
  if (!payload) {
    return "";
  }
  if (payload.ok === false) {
    return reportUnavailable("Balance Sheet", payload);
  }
  const assets = Array.isArray(payload.assets) ? payload.assets : [];
  const liabilities = Array.isArray(payload.liabilities) ? payload.liabilities : [];
  const equity = Array.isArray(payload.equity) ? payload.equity : [];
  return `
    <div class="verification-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Balance Sheet</h4>
          <p>As of ${escapeHtml(payload.as_of || todayIsoDate())}. Assets should equal liabilities plus equity.</p>
        </div>
        <span class="pill ${payload.balanced ? "ok" : "warn"}">${payload.balanced ? "balanced" : "not balanced"}</span>
      </div>
      <div class="metric-grid three">
        ${renderStatCards([
          ["Assets", formatCurrency(payload.total_assets || 0), "resources"],
          ["Liabilities", formatCurrency(payload.total_liabilities || 0), "obligations"],
          ["Equity", formatCurrency(payload.total_equity || 0), "fund balance"],
        ])}
      </div>
      <div class="dashboard-main-grid platform-grid">
        ${[
          ["Assets", assets],
          ["Liabilities", liabilities],
          ["Equity", equity],
        ].map(([title, rows]) => `
          <article>
            <h4>${escapeHtml(title)}</h4>
            <div class="table-preview compact-table">
              <table>
                <thead>
                  <tr>
                    <th>Account</th>
                    <th>Name</th>
                    <th class="amount">Balance</th>
                  </tr>
                </thead>
                <tbody>${renderBalanceSheetRows(rows)}</tbody>
              </table>
            </div>
          </article>
        `).join("")}
      </div>
    </div>
  `;
}

export function renderMandirFinancialReports(reports = mandirReportState.financialReports) {
  return `
    ${renderMandirIncomeExpenditureReport(reports.income_expenditure)}
    ${renderMandirReceiptsPaymentsReport(reports.receipts_payments)}
    ${renderMandirBalanceSheetReport(reports.balance_sheet)}
  `;
}
