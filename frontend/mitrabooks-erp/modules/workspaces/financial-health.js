// ====================================================================
// SECTION: FINANCIAL HEALTH WORKSPACE
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initFinancialHealth(...).
// API: GET /api/v1/business/financial-health — AI narrative is advisory only.
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastFinancialHealth = null;
export let financialHealthLoadInFlight = false;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initFinancialHealth(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initFinancialHealth() must be called before using Financial Health helpers");
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

export function setLastFinancialHealth(value) {
  lastFinancialHealth = value;
}

export function resetFinancialHealthState() {
  lastFinancialHealth = null;
  financialHealthLoadInFlight = false;
}

export function fhKpiDisplay(kpi) {
  const unit = kpi.unit || "";
  const value = kpi.value;
  if (value === "—" || value === null || value === undefined || value === "") return "—";
  if (unit === "₹") return formatCurrency(value);
  if (unit === "%") return `${value}%`;
  if (unit === "x") return `${value}×`;
  return `${value}${unit ? " " + unit : ""}`;
}

export function renderFhKpiCard(kpi) {
  return `
    <article class="fh-kpi fh-tone-${escapeHtml(kpi.tone || "neutral")}">
      <span class="fh-kpi-label">${escapeHtml(kpi.label)}</span>
      <strong class="fh-kpi-value">${escapeHtml(fhKpiDisplay(kpi))}</strong>
      <small class="fh-kpi-hint">${escapeHtml(kpi.hint || "")}</small>
    </article>
  `;
}

export function renderFhBarChart(chart) {
  const series = Array.isArray(chart.series) ? chart.series : [];
  const labels = Array.isArray(chart.x) ? chart.x : [];
  const all = series.flatMap((s) => (s.data || []).map((v) => Math.abs(Number(v) || 0)));
  const maxValue = all.length ? Math.max(...all, 0.0001) : 1;
  const seriesClass = ["fh-bar-a", "fh-bar-b"];

  const groups = labels.map((label, i) => {
    const bars = series.map((s, si) => {
      const raw = Number((s.data || [])[i]) || 0;
      const height = Math.max(3, Math.round((Math.abs(raw) / maxValue) * 120));
      const neg = raw < 0 ? " fh-bar-neg" : "";
      return `<span class="fh-bar ${seriesClass[si] || "fh-bar-a"}${neg}" style="height:${height}px" title="${escapeHtml(s.name)}: ${escapeHtml(raw)}"></span>`;
    }).join("");
    return `
      <div class="fh-bar-group">
        <div class="fh-bars">${bars}</div>
        <small>${escapeHtml(label)}</small>
      </div>`;
  }).join("");

  const legend = series.length > 1
    ? `<div class="fh-legend">${series.map((s, si) =>
        `<span><i class="fh-dot ${seriesClass[si] || "fh-bar-a"}"></i>${escapeHtml(s.name)}</span>`).join("")}</div>`
    : "";

  return `
    <article class="fh-chart-card">
      <div class="fh-chart-head"><h5>${escapeHtml(chart.title)}</h5><span class="fh-unit">${escapeHtml(chart.unit || "")}</span></div>
      <div class="fh-chart" role="img" aria-label="${escapeHtml(chart.title)}">${groups || '<p class="muted">No data.</p>'}</div>
      ${legend}
    </article>`;
}

export function renderFhAlert(alert) {
  return `
    <li class="fh-alert fh-alert-${escapeHtml(alert.severity || "info")}">
      <strong>${escapeHtml(alert.title || "")}</strong>
      <span>${escapeHtml(alert.message || "")}</span>
    </li>`;
}

export function fhFormatNarrative(text) {
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

export function renderFinancialHealthWorkspace() {
  const data = lastFinancialHealth;

  // Lazy self-heal: fetch once whenever we render without data.
  if (!data && !financialHealthLoadInFlight) {
    setTimeout(() => { loadFinancialHealth(); }, 0);
  }

  if (!data) {
    return `
      <section class="financial-health-workspace erp-workspace-panel" aria-label="Financial Health">
        <div class="preview-heading compact">
          <div><h4>Financial Health</h4><p>Loading ledger-backed insights…</p></div>
        </div>
      </section>`;
  }

  const kpis = (data.kpis || []).map(renderFhKpiCard).join("");
  const charts = (data.charts || []).map(renderFhBarChart).join("");
  const alerts = (data.alerts || []).map(renderFhAlert).join("");

  // AI narrative is advisory prose over the same trusted figures; render the
  // model's text as paragraphs/bullets with a clear "AI-generated" disclaimer.
  const narrativeCard = data.narrative
    ? `
      <div class="fh-narrative">
        <div class="fh-narrative-head"><span class="pill ok">AI summary</span><small>Generated from the figures below — verify before acting.</small></div>
        <div class="fh-narrative-body">${fhFormatNarrative(data.narrative)}</div>
      </div>`
    : "";

  return `
    <section class="financial-health-workspace erp-workspace-panel" aria-label="Financial Health">
      <div class="preview-heading compact">
        <div>
          <h4>Financial Health</h4>
          <p>${escapeHtml(data.summary || "")}</p>
        </div>
        <button class="secondary" type="button" data-business-action="refresh-financial-health">Refresh</button>
      </div>
      ${narrativeCard}
      <div class="fh-kpi-grid">${kpis}</div>
      <div class="fh-section">
        <h5 class="fh-section-title">Alerts &amp; signals</h5>
        <ul class="fh-alerts">${alerts}</ul>
      </div>
      <div class="fh-charts-grid">${charts}</div>
      <p class="fh-footnote">As of ${escapeHtml(data.as_of || "")} · financial year from ${escapeHtml(data.financial_year_start || "")}. All figures computed from the posted ledger.</p>
    </section>
  `;
}


export async function loadFinancialHealth() {
  const appKey = "mitrabooks";
  financialHealthLoadInFlight = true;
  let result;
  try {
    result = await apiRequest(appKey, "/api/v1/business/financial-health", { method: "GET" });
  } finally {
    financialHealthLoadInFlight = false;
  }

  // A valid payload always carries the kpis array; guard against an empty/partial
  // body so a transient failure can't blank out data we already rendered.
  const hasValidPayload = result.ok && result.payload && typeof result.payload === "object"
    && Array.isArray(result.payload.kpis);

  if (hasValidPayload) {
    lastFinancialHealth = result.payload;
    if (getCurrentExperience() === "mitrabooks" && getActiveBusinessWorkspace() === "financial-health") {
      getDashboardPreview().innerHTML = renderBusinessWorkspace();
    }
  } else if (!lastFinancialHealth) {
    setLoginStatus(
      "warn",
      "Financial Health unavailable",
      result.payload?.detail || "Live financial-health figures could not be loaded.",
    );
  }

  renderJson(getApiOutput(), { financialHealth: { ok: result.ok, hasData: !!lastFinancialHealth } });
}

