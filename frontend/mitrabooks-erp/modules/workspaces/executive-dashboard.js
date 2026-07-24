// ====================================================================
// SECTION: BUSINESS EXECUTIVE DASHBOARD
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initExecutiveDashboard(...).
// ====================================================================

import { createWidgetWrapper } from "../widgets.js";

/** @type {Record<string, Function> | null} */
let deps = null;

export function initExecutiveDashboard(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initExecutiveDashboard() must be called before using executive dashboard helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function todayIsoDate() { return requireDeps().todayIsoDate(); }
function renderStatCards(stats) { return requireDeps().renderStatCards(stats); }
function hasTrustedSession() { return requireDeps().hasTrustedSession(); }
function getLastAccountingDrilldown() { return requireDeps().getLastAccountingDrilldown(); }
function getLastBusinessParties() { return requireDeps().getLastBusinessParties(); }
function getLastBusinessAccounts() { return requireDeps().getLastBusinessAccounts(); }
function getLastBusinessDashboardStats() { return requireDeps().getLastBusinessDashboardStats(); }
function getLastBusinessMisKpis() { return requireDeps().getLastBusinessMisKpis(); }
function getBusinessDashboardLoadInFlight() { return requireDeps().getBusinessDashboardLoadInFlight(); }
function getBusinessMisLoadInFlight() { return requireDeps().getBusinessMisLoadInFlight(); }
function loadBusinessDashboardStats() { return requireDeps().loadBusinessDashboardStats(); }
function loadBusinessMisKpis() { return requireDeps().loadBusinessMisKpis(); }

export function renderMisPartyRows(rows = [], label) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `<tr><td colspan="4" class="muted">No ${escapeHtml(label)} outstanding in the open-item aging contract.</td></tr>`;
  }
  return rows.slice(0, 5).map((row) => `
    <tr>
      <td>${escapeHtml(row.rank || "")}</td>
      <td>${escapeHtml(row.party_name || row.party_id || "Unallocated")}</td>
      <td class="amount">${escapeHtml(formatCurrency(row.outstanding || 0))}</td>
      <td class="amount">${escapeHtml(formatCurrency(row.overdue || 0))}</td>
    </tr>
  `).join("");
}

export function renderMisKpiContractPanel(data) {
  if (!data) {
    return `<p class="muted">Loading source-backed MIS KPI contracts...</p>`;
  }

  const workingCapital = data.working_capital || {};
  const overdue = data.overdue || {};
  const receivables = overdue.receivables || {};
  const payables = overdue.payables || {};
  const trend = Array.isArray(data.monthly_sales_purchase_trend) ? data.monthly_sales_purchase_trend : [];
  const trendRows = trend.length ? trend.slice(-6).map((row) => `
    <tr>
      <td>${escapeHtml(row.month || "")}</td>
      <td class="amount">${escapeHtml(formatCurrency(row.sales || 0))}</td>
      <td class="amount">${escapeHtml(formatCurrency(row.purchases || 0))}</td>
      <td class="amount">${escapeHtml(formatCurrency(row.net || 0))}</td>
    </tr>
  `).join("") : `<tr><td colspan="4" class="muted">No monthly posted sales or purchase trend yet.</td></tr>`;

  return `
    <div class="preview-heading compact">
      <div>
        <p>${escapeHtml(data.financial_health?.summary || "Monthly trends, top parties, working capital, and overdue dashboards are source-backed.")}</p>
      </div>
      <span class="pill ok">as of ${escapeHtml(data.as_of || todayIsoDate())}</span>
    </div>
    <div class="metric-grid four">
      ${renderStatCards([
        ["Working capital", formatCurrency(workingCapital.net_working_capital || 0), `current ratio ${workingCapital.current_ratio ?? "--"}x`],
        ["Receivables overdue", formatCurrency(receivables.overdue || 0), `${formatCurrency(receivables.over_90 || 0)} over 90 days`],
        ["Payables overdue", formatCurrency(payables.overdue || 0), `${formatCurrency(payables.over_90 || 0)} over 90 days`],
        ["Source", "Posted ledger", "open-item aging"],
      ])}
    </div>
    <div class="dashboard-main-grid platform-grid">
      <article>
        <h4>Monthly Sales / Purchase Trend</h4>
        <div class="table-preview compact-table">
          <table>
            <thead><tr><th>Month</th><th>Sales</th><th>Purchases</th><th>Net</th></tr></thead>
            <tbody>${trendRows}</tbody>
          </table>
        </div>
      </article>
      <article>
        <h4>Top Customers</h4>
        <div class="table-preview compact-table">
          <table>
            <thead><tr><th>#</th><th>Customer</th><th>Outstanding</th><th>Overdue</th></tr></thead>
            <tbody>${renderMisPartyRows(data.top_customers, "customer")}</tbody>
          </table>
        </div>
      </article>
      <article>
        <h4>Top Vendors</h4>
        <div class="table-preview compact-table">
          <table>
            <thead><tr><th>#</th><th>Vendor</th><th>Outstanding</th><th>Overdue</th></tr></thead>
            <tbody>${renderMisPartyRows(data.top_vendors, "vendor")}</tbody>
          </table>
        </div>
      </article>
    </div>
  `;
}

export function renderBusinessExecutiveDashboard() {
  const voucherCount = getLastAccountingDrilldown()?.summary?.voucher_count ?? 0;
  const partyCount = Array.isArray(getLastBusinessParties()) ? getLastBusinessParties().length : 0;
  const accountCount = Array.isArray(getLastBusinessAccounts()) ? getLastBusinessAccounts().length : 0;

  // Live dashboard data from GET /business/dashboard (computed from the ledger).
  // No hard-coded fallbacks: before data loads or with an empty ledger we show
  // real zeros rather than invented figures.
  const dashboardData = getLastBusinessDashboardStats() || {};
  const hasDashboard = !!getLastBusinessDashboardStats();

  // Lazy self-heal: whenever the KPI dashboard renders without data (boot,
  // refresh, or any path that didn't fetch), kick off the load. Deferred so we
  // don't re-enter during the current innerHTML render; guarded so it fires once.
  if (hasTrustedSession() && !hasDashboard && !getBusinessDashboardLoadInFlight()) {
    setTimeout(() => { loadBusinessDashboardStats(); }, 0);
  }
  if (hasTrustedSession() && !getLastBusinessMisKpis() && !getBusinessMisLoadInFlight()) {
    setTimeout(() => { loadBusinessMisKpis(); }, 0);
  }

  // KPI values (Rupees). FYTD = financial-year-to-date.
  const incomeVal = Number(dashboardData.income?.fytd || 0);
  const expenseVal = Number(dashboardData.expenses?.fytd || 0);
  const netVal = Number(dashboardData.net_position?.profit_loss || 0);
  const incomeGrowth = Number(dashboardData.income?.ytd_growth || 0);
  const cashVal = Number(dashboardData.cash_and_bank || 0);
  const receivablesVal = Number(dashboardData.receivables || 0);
  const payablesVal = Number(dashboardData.payables || 0);
  const gstStatus = dashboardData.gst?.status || "—";

  const incomeDisplay = formatCurrency(incomeVal);
  const expenseDisplay = formatCurrency(expenseVal);
  const netDisplay = formatCurrency(netVal);

  // 6-month income-vs-expense trend (lakhs) from the ledger; empty when no activity.
  const months = Array.isArray(dashboardData.monthly_trend) ? dashboardData.monthly_trend : [];
  const trendValues = months.flatMap(([, income, expense]) => [Number(income) || 0, Number(expense) || 0]);
  const maxValue = trendValues.length ? Math.max(...trendValues, 0.0001) : 1;
  const bars = months.length
    ? months.map(([label, income, expense]) => {
        const inc = Number(income) || 0;
        const exp = Number(expense) || 0;
        const incomeHeight = Math.max(4, Math.round((inc / maxValue) * 132));
        const expenseHeight = Math.max(4, Math.round((exp / maxValue) * 132));
        return `
      <div class="finance-bar-group">
        <div class="finance-bars" aria-label="${escapeHtml(label)} income Rs. ${inc}L and expenses Rs. ${exp}L">
          <span class="income-bar" style="height: ${incomeHeight}px"></span>
          <span class="expense-bar" style="height: ${expenseHeight}px"></span>
        </div>
        <small>${escapeHtml(label)}</small>
      </div>
    `;
      }).join("")
    : `<p class="muted">${hasDashboard ? "No ledger activity in the last 6 months." : "Loading ledger activity…"}</p>`;

  // Widget 1: KPI Strip (Phase 2C.2-C.3: Collapsible & Customizable)
  const kpiStripContent = `
    <div class="executive-hero kpi-widget-hero">
      <div class="executive-kpi-strip">
        <article>
          <span>Income</span>
          <strong>${escapeHtml(incomeDisplay)}</strong>
          <small>${incomeGrowth > 0 ? "+" : ""}${incomeGrowth.toFixed(1)}% vs last month</small>
        </article>
        <article>
          <span>Expenses</span>
          <strong>${escapeHtml(expenseDisplay)}</strong>
          <small>Office, purchases, vendor bills</small>
        </article>
        <article>
          <span>Net Position</span>
          <strong>${escapeHtml(netDisplay)}</strong>
          <small>Income − Expenses (FYTD)</small>
        </article>
      </div>
    </div>
  `;

  // Widget 2: Finance Chart (Phase 2C.2-C.3: Collapsible & Customizable)
  const financeChartContent = `
    <div class="preview-heading compact">
      <div>
        <p>Scoped performance metrics for the active BUSINESS Suite.</p>
      </div>
      <span class="pill ok">CEO view</span>
    </div>
    <div class="finance-chart" role="img" aria-label="Monthly income and expense bar chart">
      ${bars}
    </div>
    <div class="chart-legend">
      <span><i class="income-dot"></i>Income</span>
      <span><i class="expense-dot"></i>Expenses</span>
    </div>
  `;

  // Widget 3: CEO Panel — real metrics derived from the live ledger figures above.
  const coverage = payablesVal > 0 ? cashVal / payablesVal : null;
  const coverageRow = coverage != null
    ? `<strong>${coverage.toFixed(1)}x coverage</strong><span>Cash & bank (${formatCurrency(cashVal)}) against vendor dues (${formatCurrency(payablesVal)}).</span>`
    : `<strong>${escapeHtml(formatCurrency(cashVal))}</strong><span>Cash & bank on hand. No outstanding vendor dues.</span>`;
  const ceoPanelContent = `
    <div class="preview-heading compact">
      <div class="ceo-title-block">
        <span class="ceo-orbit" aria-hidden="true"></span>
        <span class="ai-badge">Live from ledger</span>
        <p>Key operating figures computed from posted entries (as of ${escapeHtml(dashboardData.as_of || todayIsoDate())}).</p>
      </div>
    </div>
    <div class="ceo-insight-list" role="list">
      <div class="ceo-insight-row" role="listitem">
        <span class="insight-spark" aria-hidden="true"></span>
        <div class="ceo-insight-copy">${coverageRow}</div>
      </div>
      <div class="ceo-insight-row" role="listitem">
        <span class="insight-spark" aria-hidden="true"></span>
        <div class="ceo-insight-copy">
          <strong>${escapeHtml(formatCurrency(receivablesVal))}</strong>
          <span>Outstanding from customers (open receivables).</span>
        </div>
      </div>
      <div class="ceo-insight-row" role="listitem">
        <span class="insight-spark" aria-hidden="true"></span>
        <div class="ceo-insight-copy">
          <strong>${escapeHtml(formatCurrency(netVal))}</strong>
          <span>Net position this financial year (income − expenses).</span>
        </div>
      </div>
    </div>
    <p class="ceo-footnote">${voucherCount} posted voucher(s), ${partyCount} party record(s), and ${accountCount} account(s) in this dashboard context. GST: ${escapeHtml(gstStatus)}.</p>
  `;

  // Build dashboard with wrapped widgets (Phase 2C.2-C.3)
  const kpiWidget = createWidgetWrapper("kpi-strip", "Key Performance Indicators", kpiStripContent, true);
  const chartWidget = createWidgetWrapper("finance-chart", "Sales & Expenses Trend", financeChartContent, true);
  const ceoWidget = createWidgetWrapper("ceo-panel", "CEO Insights", ceoPanelContent, true);
  const misWidget = createWidgetWrapper("mis-kpi-contracts", "MIS KPI Contracts", renderMisKpiContractPanel(getLastBusinessMisKpis()), true);

  return `
    <section class="executive-dashboard" aria-label="MitraBooks executive dashboard">
      <div class="dashboard-toolbar">
        <button
          class="dashboard-customize-btn"
          type="button"
          data-business-action="open-widget-settings"
          aria-label="Customize dashboard widgets"
          title="Customize widgets"
        >⚙ Customize</button>
      </div>
      ${kpiWidget}
      <div class="finance-dashboard-grid-wrapper">
        ${chartWidget}
        ${ceoWidget}
      </div>
      ${misWidget}
    </section>
  `;
}

