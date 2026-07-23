// ====================================================================
// SECTION: TDS / TCS MODULE
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initTds(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastTdsRegister = null;
export let tdsQuarter = "";

/** @type {Record<string, Function> | null} */
let deps = null;

export function initTds(injected) {
  deps = injected;
  if (!tdsQuarter) {
    tdsQuarter = deps.currentFyQuarter();
  }
}

function requireDeps() {
  if (!deps) {
    throw new Error("initTds() must be called before using TDS helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function reportUnavailablePanel(title, payload) { return requireDeps().reportUnavailablePanel(title, payload); }
function rerenderBusinessReportsIfActive() { return requireDeps().rerenderBusinessReportsIfActive(); }
function recentFyQuarters(count = 6) { return requireDeps().recentFyQuarters(count); }
function getApiOutput() { return requireDeps().getApiOutput(); }

// ══════════════════════════════════════════════════════════════════════
// SECTION: TDS / TCS MODULE
// API   : GET /api/v1/business/tds/register?quarter=
// NOTE  : loadTdsRegister, renderTdsRegisterPanel, renderTdsRegisterSide
// ══════════════════════════════════════════════════════════════════════

export async function loadTdsRegister(quarter) {
  tdsQuarter = quarter || tdsQuarter;
  const result = await apiRequest("mitrabooks", `/api/v1/business/tds/register?quarter=${encodeURIComponent(tdsQuarter)}`, { method: "GET" });
  lastTdsRegister = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { tds_register: { ok: result.ok, quarter: tdsQuarter } });
}

export function previewTdsRegisterFromInput() {
  const input = document.querySelector("[data-tds-quarter]");
  loadTdsRegister(input?.value || tdsQuarter);
}

function renderTdsRegisterSide(side, kindLabel, partyHeading) {
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  if (!side || !side.entry_count) {
    return `<div class="table-preview compact-table"><h4>${escapeHtml(kindLabel)}</h4><p class="muted">No ${escapeHtml(kindLabel)} entries this quarter.</p></div>`;
  }
  const sections = (side.sections || []).map((sec) => {
    const rows = (sec.entries || []).map((e) => `
      <tr>
        <td>${escapeHtml(e.doc_date || "")}</td>
        <td>${escapeHtml(e.doc_number || "")}</td>
        <td>${escapeHtml(e.party_name || "")}</td>
        <td>${e.pan_missing ? `<span class="pill warn">PAN missing</span>` : escapeHtml(e.pan || "")}</td>
        <td class="amount">${num(e.base_amount)}</td>
        <td class="amount">${escapeHtml(String(e.rate ?? ""))}%</td>
        <td class="amount">${num(e.tax_amount)}</td>
      </tr>`).join("");
    return `
      <div class="table-preview compact-table">
        <h4>${escapeHtml(`${sec.section} — ${sec.label}`)}</h4>
        <table>
          <thead><tr><th>Date</th><th>Document</th><th>${escapeHtml(partyHeading)}</th><th>PAN</th><th class="amount">Base</th><th class="amount">Rate</th><th class="amount">${escapeHtml(kindLabel)}</th></tr></thead>
          <tbody>${rows}</tbody>
          <tfoot><tr><th colspan="4">Section total</th><td class="amount">${num(sec.total_base)}</td><td></td><td class="amount"><strong>${num(sec.total_tax)}</strong></td></tr></tfoot>
        </table>
      </div>`;
  }).join("");
  return sections;
}

export function renderTdsRegisterPanel() {
  const quarterOpts = recentFyQuarters(6).map((q) =>
    `<option value="${q}" ${q === tdsQuarter ? "selected" : ""}>${q}</option>`).join("");
  const controls = `
    <div class="report-date-controls">
      <label>Quarter <select data-tds-quarter>${quarterOpts}</select></label>
      <button class="secondary" type="button" data-business-action="tds-load">Load</button>
    </div>`;
  const r = lastTdsRegister;
  if (!r) return `${controls}<p class="muted">Loading TDS/TCS register...</p>`;
  if (r.ok === false) return `${controls}${reportUnavailablePanel("TDS/TCS register", r)}`;
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const panMissing = Number(r.tds?.pan_missing_count || 0) + Number(r.tcs?.pan_missing_count || 0);

  const cards = [
    ["TDS deducted (26Q)", r.tds?.total_tax, `${r.tds?.entry_count || 0} document(s) · base ${formatCurrency(Number(r.tds?.total_base || 0))}`],
    ["TCS collected (27EQ)", r.tcs?.total_tax, `${r.tcs?.entry_count || 0} document(s) · base ${formatCurrency(Number(r.tcs?.total_base || 0))}`],
  ].map(([title, val, sub]) => `
    <article>
      <h4>${escapeHtml(title)}</h4>
      <div class="invoice-totals"><div class="invoice-grand"><span>${escapeHtml(sub)}</span><strong>${num(val)}</strong></div></div>
    </article>`).join("");

  return `
    ${controls}
    <div class="preview-heading compact">
      <div><p>TDS/TCS register for ${escapeHtml(r.quarter || tdsQuarter)} (${escapeHtml(r.period_start || "")} → ${escapeHtml(r.period_end || "")}). Section-wise working paper for Form 26Q / 27EQ.</p></div>
      <span class="pill ${panMissing > 0 ? "warn" : "ok"}">${panMissing > 0 ? `${panMissing} PAN missing` : "PANs complete"}</span>
    </div>
    <div class="dashboard-main-grid platform-grid">${cards}</div>
    <h4 style="margin:14px 0 6px;">TDS on purchases (Form 26Q)</h4>
    ${renderTdsRegisterSide(r.tds, "TDS", "Deductee (vendor)")}
    <h4 style="margin:14px 0 6px;">TCS on sales (Form 27EQ)</h4>
    ${renderTdsRegisterSide(r.tcs, "TCS", "Collectee (customer)")}
    ${(r.generated_notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}
  `;
}
