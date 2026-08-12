// ====================================================================
// SECTION: BUSINESS EXECUTIVE DASHBOARD
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initExecutiveDashboard(...).
// Enhanced with Phase 3 UI/UX: Alert Ribbons, Quick Action Bar, and SVG Sparklines.
// ====================================================================

import { createWidgetWrapper } from "../widgets.js";
import { apiRequest } from "../../../shared/api-client.js";

/** @type {Record<string, Function> | null} */
let deps = null;

export let lastOfficeAiBrief = null;
export let officeAiBriefLoadInFlight = false;

export async function loadOfficeAiBriefData() {
  if (officeAiBriefLoadInFlight) return;
  officeAiBriefLoadInFlight = true;
  try {
    const result = await apiRequest("mitrabooks", "/api/v1/officemitra/brief", { method: "GET" });
    lastOfficeAiBrief = result.ok ? result.payload : { ok: false };
  } catch (_err) {
    lastOfficeAiBrief = { ok: false };
  } finally {
    officeAiBriefLoadInFlight = false;
  }
}

export function renderOfficeAiBriefWidget(briefData = lastOfficeAiBrief) {
  const briefItems = Array.isArray(briefData?.brief_items) ? briefData.brief_items : Array.isArray(briefData?.items) ? briefData.items : [];
  
  const content = briefItems.length > 0
    ? `
      <ul class="ai-brief-list">
        ${briefItems.slice(0, 4).map((item) => `
          <li class="ai-brief-item">
            <span class="ai-brief-bullet">⚡</span>
            <span>${escapeHtml(typeof item === "string" ? item : item.summary || item.text || "Operational item")}</span>
          </li>
        `).join("")}
      </ul>
    `
    : `
      <p class="muted">OfficeMitra AI advisory brief ready. Click below to launch your AI workspace and generate operational insights.</p>
    `;

  const widgetInner = `
    <div class="office-ai-brief-card">
      <div class="preview-heading compact">
        <div>
          <span class="ai-badge">🤖 OfficeMitra AI Brief</span>
          <p>AI-curated operational highlights & priority digests.</p>
        </div>
        <button class="secondary" type="button" data-business-action="workspace-view" data-workspace-view="office-ai">Open OfficeMitra AI →</button>
      </div>
      ${content}
    </div>
  `;

  return createWidgetWrapper("office-ai-brief", "OfficeMitra AI Briefing", widgetInner, true);
}

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
function getLastVoucherApprovalQueue() {
  return typeof requireDeps().getLastVoucherApprovalQueue === "function" ? requireDeps().getLastVoucherApprovalQueue() : [];
}
function getBusinessDashboardLoadInFlight() { return requireDeps().getBusinessDashboardLoadInFlight(); }
function getBusinessMisLoadInFlight() { return requireDeps().getBusinessMisLoadInFlight(); }
function loadBusinessDashboardStats() { return requireDeps().loadBusinessDashboardStats(); }
function loadBusinessMisKpis() { return requireDeps().loadBusinessMisKpis(); }

export function renderSvgSparkline(points = [], strokeColor = "#10b981") {
  if (!Array.isArray(points) || points.length === 0) {
    points = [12, 18, 14, 22, 28, 24, 32];
  }
  const min = Math.min(...points);
  const max = Math.max(...points) || 1;
  const range = max - min || 1;
  const width = 64;
  const height = 24;
  const step = width / Math.max(1, points.length - 1);
  const coords = points.map((val, idx) => {
    const x = Math.round(idx * step);
    const y = Math.round(height - ((val - min) / range) * (height - 4) - 2);
    return `${x},${y}`;
  }).join(" ");

  return `
    <div class="kpi-sparkline" aria-hidden="true">
      <svg viewBox="0 0 64 24" fill="none">
        <polyline points="${coords}" fill="none" stroke="${strokeColor}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </div>
  `;
}

export function renderExecutiveAlertRibbon(dashboardData = {}, approvalQueue = [], misData = null) {
  const overdue90 = misData?.overdue?.receivables?.over_90 || 0;
  const pendingVouchers = Array.isArray(approvalQueue) ? approvalQueue.length : 0;
  const gstStatus = dashboardData?.gst?.status || "";

  if (overdue90 > 0) {
    return `
      <div class="executive-alert-ribbon alert-warning animate-slide-down" role="alert">
        <div class="alert-ribbon-content">
          <span class="alert-ribbon-icon">⚠️</span>
          <div class="alert-ribbon-text">
            <strong>Receivables Alert</strong>
            <span>${escapeHtml(formatCurrency(overdue90))} overdue beyond 90 days requiring collection follow-up.</span>
          </div>
        </div>
        <button class="alert-action-btn" type="button" data-business-action="workspace-view" data-workspace-view="parties">Review Parties →</button>
      </div>
    `;
  }
  if (pendingVouchers > 0) {
    return `
      <div class="executive-alert-ribbon alert-info animate-slide-down" role="alert">
        <div class="alert-ribbon-content">
          <span class="alert-ribbon-icon">📑</span>
          <div class="alert-ribbon-text">
            <strong>Voucher Approvals Pending</strong>
            <span>${pendingVouchers} voucher(s) waiting in the approval queue.</span>
          </div>
        </div>
        <button class="alert-action-btn" type="button" data-business-action="workspace-view" data-workspace-view="vouchers">Open Vouchers →</button>
      </div>
    `;
  }
  if (gstStatus && gstStatus.toLowerCase() !== "ok" && gstStatus.toLowerCase() !== "filed") {
    return `
      <div class="executive-alert-ribbon alert-info animate-slide-down" role="alert">
        <div class="alert-ribbon-content">
          <span class="alert-ribbon-icon">📅</span>
          <div class="alert-ribbon-text">
            <strong>GST Compliance Check</strong>
            <span>Active GST status: ${escapeHtml(gstStatus)}. Check return filing status for the current tax period.</span>
          </div>
        </div>
        <button class="alert-action-btn" type="button" data-business-action="workspace-view" data-workspace-view="gst-returns">GST Hub →</button>
      </div>
    `;
  }
  return "";
}

export function renderQuickExecutionBar() {
  return `
    <div class="dashboard-quick-execution-bar" aria-label="Quick Execution Shortcuts">
      <button class="quick-action-chip" type="button" data-business-action="open-create-voucher" title="Create Voucher (Ctrl+Alt+V)">
        <span class="chip-icon">📄</span>
        <span class="chip-label">+ New Voucher</span>
        <span class="chip-shortcut">Ctrl+Alt+V</span>
      </button>
      <button class="quick-action-chip" type="button" data-business-action="open-create-party" title="Create Party">
        <span class="chip-icon">👤</span>
        <span class="chip-label">+ New Party</span>
      </button>
      <button class="quick-action-chip" type="button" data-business-action="workspace-view" data-workspace-view="vouchers" title="Open Vouchers List">
        <span class="chip-icon">📑</span>
        <span class="chip-label">Vouchers List</span>
      </button>
      <button class="quick-action-chip" type="button" data-business-action="workspace-view" data-workspace-view="parties" title="Open Parties Master">
        <span class="chip-icon">🏢</span>
        <span class="chip-label">Parties Master</span>
      </button>
      <button class="quick-action-chip" type="button" data-business-action="workspace-view" data-workspace-view="reports" title="Open Financial Reports">
        <span class="chip-icon">📈</span>
        <span class="chip-label">Financial Reports</span>
      </button>
      <button class="quick-action-chip" type="button" data-business-action="workspace-view" data-workspace-view="office-ai" title="Open OfficeMitra AI">
        <span class="chip-icon">🤖</span>
        <span class="chip-label">OfficeMitra AI</span>
      </button>
    </div>
  `;
}

export function renderMisPartyRows(rows = [], label) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `<tr><td colspan="4" class="muted">No ${escapeHtml(label)} outstanding in the open-item aging contract.</td></tr>`;
  }
  return rows.slice(0, 5).map((row, idx) => {
    const rankNum = row.rank || (idx + 1);
    const rankClass = rankNum <= 3 ? `rank-${rankNum}` : "";
    return `
      <tr>
        <td><span class="rank-badge ${rankClass}">#${escapeHtml(String(rankNum))}</span></td>
        <td><strong>${escapeHtml(row.party_name || row.party_id || "Unallocated")}</strong></td>
        <td class="amount">${escapeHtml(formatCurrency(row.outstanding || 0))}</td>
        <td class="amount">${row.overdue > 0 ? `<span class="pill warn">${escapeHtml(formatCurrency(row.overdue))}</span>` : `<span class="muted">-</span>`}</td>
      </tr>
    `;
  }).join("");
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
  const dashboardData = getLastBusinessDashboardStats() || {};
  const hasDashboard = !!getLastBusinessDashboardStats();
  const misData = getLastBusinessMisKpis();
  const approvalQueue = getLastVoucherApprovalQueue();

  // Lazy self-heal
  if (hasTrustedSession() && !hasDashboard && !getBusinessDashboardLoadInFlight()) {
    setTimeout(() => { loadBusinessDashboardStats(); }, 0);
  }
  if (hasTrustedSession() && !misData && !getBusinessMisLoadInFlight()) {
    setTimeout(() => { loadBusinessMisKpis(); }, 0);
  }
  if (hasTrustedSession() && !lastOfficeAiBrief && !officeAiBriefLoadInFlight) {
    setTimeout(() => { loadOfficeAiBriefData(); }, 0);
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
  const cashDisplay = formatCurrency(cashVal);

  // Profit margin calculation
  const netMarginPct = incomeVal > 0 ? ((netVal / incomeVal) * 100).toFixed(1) : "0.0";
  const netMarginBadgeClass = netVal >= 0 ? "kpi-badge-positive" : "kpi-badge-negative";
  const netMarginLabel = netVal >= 0 ? `+${netMarginPct}% margin` : `${netMarginPct}% margin`;

  // 6-month trend points for SVG sparkline
  const months = Array.isArray(dashboardData.monthly_trend) ? dashboardData.monthly_trend : [];
  const incomeTrendPoints = months.map(([, inc]) => Number(inc) || 0);
  const expenseTrendPoints = months.map(([, , exp]) => Number(exp) || 0);

  // 6-month income-vs-expense trend (lakhs) from the ledger; empty when no activity.
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
          <span class="income-bar" style="height: ${incomeHeight}px" title="Income: ${inc}L"></span>
          <span class="expense-bar" style="height: ${expenseHeight}px" title="Expenses: ${exp}L"></span>
        </div>
        <small>${escapeHtml(label)}</small>
      </div>
    `;
      }).join("")
    : `<p class="muted">${hasDashboard ? "No ledger activity in the last 6 months." : "Loading ledger activity…"}</p>`;

  // Enhanced 4-card KPI strip
  const kpiStripContent = `
    <div class="executive-hero kpi-widget-hero">
      <div class="executive-kpi-grid-enhanced">
        <article class="kpi-card-enhanced">
          <div class="kpi-head">
            <span class="kpi-title">Revenue (FYTD)</span>
            <span class="kpi-badge ${incomeGrowth >= 0 ? "kpi-badge-positive" : "kpi-badge-negative"}">
              ${incomeGrowth >= 0 ? "↗ +" : "↘ "}${incomeGrowth.toFixed(1)}%
            </span>
          </div>
          <div class="kpi-main-val">${escapeHtml(incomeDisplay)}</div>
          <div class="kpi-footer-row">
            <span class="kpi-subtext">Operating Inflow</span>
            ${renderSvgSparkline(incomeTrendPoints, "#10b981")}
          </div>
        </article>

        <article class="kpi-card-enhanced">
          <div class="kpi-head">
            <span class="kpi-title">Expenses (FYTD)</span>
            <span class="kpi-badge kpi-badge-neutral">Outflow</span>
          </div>
          <div class="kpi-main-val">${escapeHtml(expenseDisplay)}</div>
          <div class="kpi-footer-row">
            <span class="kpi-subtext">Office & Bills</span>
            ${renderSvgSparkline(expenseTrendPoints, "#3b82f6")}
          </div>
        </article>

        <article class="kpi-card-enhanced">
          <div class="kpi-head">
            <span class="kpi-title">Net Position</span>
            <span class="kpi-badge ${netMarginBadgeClass}">${netMarginLabel}</span>
          </div>
          <div class="kpi-main-val">${escapeHtml(netDisplay)}</div>
          <div class="kpi-footer-row">
            <span class="kpi-subtext">Income − Expenses</span>
            ${renderSvgSparkline(incomeTrendPoints.map((v, i) => v - (expenseTrendPoints[i] || 0)), netVal >= 0 ? "#10b981" : "#ef4444")}
          </div>
        </article>

        <article class="kpi-card-enhanced">
          <div class="kpi-head">
            <span class="kpi-title">Cash & Bank</span>
            <span class="kpi-badge kpi-badge-positive">Liquidity</span>
          </div>
          <div class="kpi-main-val">${escapeHtml(cashDisplay)}</div>
          <div class="kpi-footer-row">
            <span class="kpi-subtext">On Hand & Bank Accounts</span>
            ${renderSvgSparkline([cashVal * 0.8, cashVal * 0.85, cashVal * 0.9, cashVal * 0.95, cashVal], "#38bdf8")}
          </div>
        </article>
      </div>
    </div>
  `;

  // Finance Chart
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

  // CEO Panel — real metrics derived from the live ledger figures above.
  const coverage = payablesVal > 0 ? cashVal / payablesVal : null;
  const coverageRow = coverage != null
    ? `<strong>${coverage.toFixed(1)}x coverage</strong><span>Cash & bank (${formatCurrency(cashVal)}) against vendor dues (${formatCurrency(payablesVal)}).</span>`
    : `<strong>${escapeHtml(formatCurrency(cashVal))}</strong><span>Cash & bank on hand. No outstanding vendor dues.</span>`;
  const ceoPanelContent = `
    <div class="preview-heading compact">
      <div class="ceo-title-block">
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

  // Build dashboard with wrapped widgets
  const alertRibbon = renderExecutiveAlertRibbon(dashboardData, approvalQueue, misData);
  const quickBar = renderQuickExecutionBar();
  const officeAiWidget = renderOfficeAiBriefWidget(lastOfficeAiBrief);
  const kpiWidget = createWidgetWrapper("kpi-strip", "Key Performance Indicators", kpiStripContent, true);
  const chartWidget = createWidgetWrapper("finance-chart", "Sales & Expenses Trend", financeChartContent, true);
  const ceoWidget = createWidgetWrapper("ceo-panel", "CEO Insights", ceoPanelContent, true);
  const misWidget = createWidgetWrapper("mis-kpi-contracts", "MIS KPI Contracts", renderMisKpiContractPanel(misData), true);

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
      ${alertRibbon}
      ${quickBar}
      ${officeAiWidget}
      ${kpiWidget}
      <div class="finance-dashboard-grid-wrapper">
        ${chartWidget}
        ${ceoWidget}
      </div>
      ${misWidget}
    </section>
  `;
}



