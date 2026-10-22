// ====================================================================
// SECTION: CASH FLOW FORECAST WORKSPACE
// Sibling of financial-health.js. Same compute→narrate→visualize contract:
// every figure comes from the ledger; the AI narrative is advisory prose only.
// API: GET /api/v1/business/cash-flow-forecast — reuses the fh-* CSS classes.
// Shell deps injected via initCashFlowForecast(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastCashFlowForecast = null;
export let cashFlowForecastLoadInFlight = false;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initCashFlowForecast(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initCashFlowForecast() must be called before using Cash Flow Forecast helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function getApiOutput() { return requireDeps().getApiOutput(); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function renderBusinessWorkspace() { return requireDeps().renderBusinessWorkspace(); }

export function setLastCashFlowForecast(value) {
  lastCashFlowForecast = value;
}

export function resetCashFlowForecastState() {
  lastCashFlowForecast = null;
  cashFlowForecastLoadInFlight = false;
}

function cfKpiDisplay(kpi) {
  const unit = kpi.unit || "";
  const value = kpi.value;
  if (value === "—" || value === null || value === undefined || value === "") return "—";
  if (unit === "₹") return formatCurrency(value);
  if (unit === "₹/mo") return `${formatCurrency(value)}/mo`;
  if (unit === "months") return value === "∞" ? "∞" : `${value} months`;
  return `${value}${unit ? " " + unit : ""}`;
}

function renderCfKpiCard(kpi) {
  return `
    <article class="fh-kpi fh-tone-${escapeHtml(kpi.tone || "neutral")}">
      <span class="fh-kpi-label">${escapeHtml(kpi.label)}</span>
      <strong class="fh-kpi-value">${escapeHtml(cfKpiDisplay(kpi))}</strong>
      <small class="fh-kpi-hint">${escapeHtml(kpi.hint || "")}</small>
    </article>
  `;
}

// Deterministic bar chart (reuses the Financial Health visual vocabulary). A line
// series renders as a bar-per-period, which reads fine for a cash projection.
function renderCfBarChart(chart) {
  const series = Array.isArray(chart.series) ? chart.series : [];
  const labels = Array.isArray(chart.x) ? chart.x : [];
  const all = series.flatMap((s) => (s.data || []).map((v) => Math.abs(Number(v) || 0)));
  const maxValue = all.length ? Math.max(...all, 0.0001) : 1;

  const groups = labels.map((label, i) => {
    const bars = series.map((s) => {
      const raw = Number((s.data || [])[i]) || 0;
      const height = Math.max(3, Math.round((Math.abs(raw) / maxValue) * 120));
      const neg = raw < 0 ? " fh-bar-neg" : "";
      return `<span class="fh-bar fh-bar-a${neg}" style="height:${height}px" title="${escapeHtml(s.name)}: ${escapeHtml(raw)}"></span>`;
    }).join("");
    return `
      <div class="fh-bar-group">
        <div class="fh-bars">${bars}</div>
        <small>${escapeHtml(label)}</small>
      </div>`;
  }).join("");

  return `
    <article class="fh-chart-card">
      <div class="fh-chart-head"><h5>${escapeHtml(chart.title)}</h5><span class="fh-unit">${escapeHtml(chart.unit || "")}</span></div>
      <div class="fh-chart" role="img" aria-label="${escapeHtml(chart.title)}">${groups || '<p class="muted">No data.</p>'}</div>
    </article>`;
}

function renderCfAlert(alert) {
  return `
    <li class="fh-alert fh-alert-${escapeHtml(alert.severity || "info")}">
      <strong>${escapeHtml(alert.title || "")}</strong>
      <span>${escapeHtml(alert.message || "")}</span>
    </li>`;
}

function renderCfProjectionTable(projection) {
  const rows = (projection || []).map((r) => `
    <tr>
      <td>${escapeHtml(r.label)}</td>
      <td class="num">${formatCurrency(r.opening)}</td>
      <td class="num">${formatCurrency(r.operating_cf)}</td>
      <td class="num">${formatCurrency(r.wc_unwind)}</td>
      <td class="num"><strong>${formatCurrency(r.closing)}</strong></td>
    </tr>`).join("");
  if (!rows) return "";
  return `
    <div class="fh-section">
      <h5 class="fh-section-title">Month-by-month projection</h5>
      <table class="erp-table compact cf-projection-table">
        <thead><tr><th>Month</th><th class="num">Opening</th><th class="num">Operating CF</th><th class="num">AR/AP unwind</th><th class="num">Closing cash</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function cfFormatNarrative(text) {
  const lines = String(text || "").split(/\r?\n/);
  const out = [];
  let listItems = [];
  const flushList = () => {
    if (listItems.length) { out.push(`<ul>${listItems.join("")}</ul>`); listItems = []; }
  };
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) { flushList(); continue; }
    const bullet = line.match(/^[-*•]\s+(.*)$/);
    if (bullet) {
      listItems.push(`<li>${escapeHtml(bullet[1])}</li>`);
    } else {
      flushList();
      out.push(`<p>${escapeHtml(line)}</p>`);
    }
  }
  flushList();
  return out.join("");
}

export function renderCashFlowForecastWorkspace() {
  const data = lastCashFlowForecast;

  // Lazy self-heal: fetch once whenever we render without data.
  if (!data && !cashFlowForecastLoadInFlight) {
    setTimeout(() => { loadCashFlowForecast(); }, 0);
  }

  if (!data) {
    return `
      <section class="cash-flow-forecast-workspace erp-workspace-panel" aria-label="Cash Flow Forecast">
        <div class="preview-heading compact">
          <div><h4>Cash Flow Forecast</h4><p>Loading ledger-backed projection…</p></div>
        </div>
      </section>`;
  }

  const kpis = (data.kpis || []).map(renderCfKpiCard).join("");
  const charts = (data.charts || []).map(renderCfBarChart).join("");
  const alerts = (data.alerts || []).map(renderCfAlert).join("");
  const projection = renderCfProjectionTable(data.projection);

  const narrativeCard = data.narrative
    ? `
      <div class="fh-narrative">
        <div class="fh-narrative-head"><span class="pill ok">AI summary</span><small>Generated from the figures below — this is an estimate, verify before acting.</small></div>
        <div class="fh-narrative-body">${cfFormatNarrative(data.narrative)}</div>
      </div>`
    : "";

  const assumptions = (data.assumptions || []).length
    ? `<ul class="cf-assumptions">${data.assumptions.map((a) => `<li>${escapeHtml(a)}</li>`).join("")}</ul>`
    : "";

  return `
    <section class="cash-flow-forecast-workspace erp-workspace-panel" aria-label="Cash Flow Forecast">
      <div class="preview-heading compact">
        <div>
          <h4>Cash Flow Forecast</h4>
          <p>${escapeHtml(data.summary || "")}</p>
        </div>
        <button class="secondary" type="button" data-business-action="refresh-cash-flow-forecast">Refresh</button>
      </div>
      ${narrativeCard}
      <div class="fh-kpi-grid">${kpis}</div>
      <div class="fh-section">
        <h5 class="fh-section-title">Alerts &amp; signals</h5>
        <ul class="fh-alerts">${alerts}</ul>
      </div>
      <div class="fh-charts-grid">${charts}</div>
      ${projection}
      <div class="fh-section">
        <h5 class="fh-section-title">How this is calculated</h5>
        ${assumptions}
      </div>
      <p class="fh-footnote">As of ${escapeHtml(data.as_of || "")} · ${escapeHtml(String(data.horizon_months || ""))}-month horizon. All figures computed from the posted ledger; the forecast is an estimate.</p>
    </section>
  `;
}

export async function loadCashFlowForecast() {
  const appKey = "mitrabooks";
  cashFlowForecastLoadInFlight = true;
  let result;
  try {
    result = await apiRequest(appKey, "/api/v1/business/cash-flow-forecast", { method: "GET" });
  } finally {
    cashFlowForecastLoadInFlight = false;
  }

  // A valid payload always carries the kpis array; guard against an empty/partial
  // body so a transient failure can't blank out data we already rendered.
  const hasValidPayload = result.ok && result.payload && typeof result.payload === "object"
    && Array.isArray(result.payload.kpis);

  if (hasValidPayload) {
    lastCashFlowForecast = result.payload;
    if (getCurrentExperience() === "mitrabooks" && getActiveBusinessWorkspace() === "cash-flow-forecast") {
      getDashboardPreview().innerHTML = renderBusinessWorkspace();
    }
  } else if (!lastCashFlowForecast) {
    setLoginStatus(
      "warn",
      "Cash Flow Forecast unavailable",
      result.payload?.detail || "Live cash-flow figures could not be loaded.",
    );
  }

  renderJson(getApiOutput(), { cashFlowForecast: { ok: result.ok, hasData: !!lastCashFlowForecast } });
}
