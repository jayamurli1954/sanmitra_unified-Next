// ====================================================================
// SECTION: GST RETURNS — settlement, GSTR-1/3B/2B/4, CMP-08
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initGstReturns(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export const gstReturnState = {
  lastGstSettlement: null,
  gstSettlementPeriod: "",
  lastGstr3b: null,
  lastGstr1: null,
  lastCmp08: null,
  lastGstr4: null,
  lastGstr2bRecon: null,
  gstReturnType: "gstr3b",
  gstr3bPeriod: "",
  cmp08Quarter: "",
  gstr4Fy: "",
};

/** @type {{
 *   escapeHtml: (v: string) => string,
 *   formatCurrency: (v: number | string) => string,
 *   setLoginStatus: (kind: string, title: string, detail?: string) => void,
 *   statusDetailText: (detail: unknown) => string,
 *   rerenderBusinessReportsIfActive: () => void,
 *   isBusinessAdmin: () => boolean,
 *   reportUnavailablePanel: (title: string, payload: unknown) => string,
 *   todayIsoDate: () => string,
 *   currentFinancialYear: () => string,
 *   currentFyQuarter: () => string,
 *   recentFinancialYears: (count?: number) => string[],
 *   recentFyQuarters: (count?: number) => string[],
 *   getApiOutput: () => HTMLElement | null,
 * } | null} */
let deps = null;

export function initGstReturns({
  escapeHtml,
  formatCurrency,
  setLoginStatus,
  statusDetailText,
  rerenderBusinessReportsIfActive,
  isBusinessAdmin,
  reportUnavailablePanel,
  todayIsoDate,
  currentFinancialYear,
  currentFyQuarter,
  recentFinancialYears,
  recentFyQuarters,
  getApiOutput,
}) {
  deps = {
    escapeHtml,
    formatCurrency,
    setLoginStatus,
    statusDetailText,
    rerenderBusinessReportsIfActive,
    isBusinessAdmin,
    reportUnavailablePanel,
    todayIsoDate,
    currentFinancialYear,
    currentFyQuarter,
    recentFinancialYears,
    recentFyQuarters,
    getApiOutput,
  };
  gstReturnState.gstSettlementPeriod = todayIsoDate().slice(0, 7);
  gstReturnState.gstr3bPeriod = todayIsoDate().slice(0, 7);
  gstReturnState.cmp08Quarter = currentFyQuarter();
  gstReturnState.gstr4Fy = currentFinancialYear();
}

function requireDeps() {
  if (!deps) {
    throw new Error("initGstReturns() must be called before using GST return helpers");
  }
  return deps;
}

function escapeHtml(value) {
  return requireDeps().escapeHtml(value);
}

function formatCurrency(value) {
  return requireDeps().formatCurrency(value);
}

function setLoginStatus(kind, title, detail = "") {
  requireDeps().setLoginStatus(kind, title, detail);
}

function statusDetailText(detail) {
  return requireDeps().statusDetailText(detail);
}

function rerenderBusinessReportsIfActive() {
  requireDeps().rerenderBusinessReportsIfActive();
}

function isBusinessAdmin() {
  return requireDeps().isBusinessAdmin();
}

function reportUnavailablePanel(title, payload) {
  return requireDeps().reportUnavailablePanel(title, payload);
}

function recentFinancialYears(count = 4) {
  return requireDeps().recentFinancialYears(count);
}

function recentFyQuarters(count = 6) {
  return requireDeps().recentFyQuarters(count);
}

function getApiOutput() {
  return requireDeps().getApiOutput();
}

// ══════════════════════════════════════════════════════════════════════
// SECTION: GST SETTLEMENT (liability posting)
// API   : GET /api/v1/business/gst-settlement/preview  POST /api/v1/business/gst-settlement
// NOTE  : loadGstSettlementPreview, postGstSettlement, renderGstSettlementPanel
// ══════════════════════════════════════════════════════════════════════


export async function loadGstSettlementPreview(period) {
  gstReturnState.gstSettlementPeriod = period || gstReturnState.gstSettlementPeriod;
  const result = await apiRequest("mitrabooks", `/api/v1/business/gst-settlement/preview?period=${encodeURIComponent(gstReturnState.gstSettlementPeriod)}`, { method: "GET" });
  gstReturnState.lastGstSettlement = result.ok ? result.payload : null;
  if (!result.ok) setLoginStatus("warn", "GST preview unavailable", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { gst_settlement_preview: { ok: result.ok, period: gstReturnState.gstSettlementPeriod } });
}

export function previewGstSettlementFromInput() {
  const input = document.querySelector("[data-gst-period]");
  loadGstSettlementPreview(input?.value || gstReturnState.gstSettlementPeriod);
}

export async function postGstSettlement() {
  const periodInput = document.querySelector("[data-gst-period]");
  const lockInput = document.querySelector("[data-gst-lock]");
  const period = periodInput?.value || gstReturnState.gstSettlementPeriod;
  const result = await apiRequest("mitrabooks", "/api/v1/business/gst-settlement", {
    method: "POST",
    body: JSON.stringify({ period, lock_period: !!lockInput?.checked, accounting_entity_id: "primary" }),
  });
  if (result.ok) {
    gstReturnState.lastGstSettlement = result.payload;
    setLoginStatus("ok", "GST settled", `Settlement posted for ${period}.`);
    rerenderBusinessReportsIfActive();
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can post a GST settlement.");
  } else {
    setLoginStatus("danger", "Settlement failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { gst_settlement: { ok: result.ok, status: result.status } });
}

export function renderGstSettlementPanel() {
  const admin = isBusinessAdmin();
  const s = gstReturnState.lastGstSettlement;
  const num = (v) => formatCurrency(Number(v || 0));
  const heads = [["IGST", "igst"], ["CGST", "cgst"], ["SGST", "sgst"]];
  let body = `<p class="muted">Select a month and preview the output-vs-input set-off before posting.</p>`;
  if (s && s.period === gstReturnState.gstSettlementPeriod) {
    const posted = String(s.status) === "posted";
    const rows = heads.map(([label, key]) => `
      <tr>
        <td>${label}</td>
        <td class="amount">${num(s.output?.[key])}</td>
        <td class="amount">${num(s.input_credit?.[key])}</td>
        <td class="amount">${num(s.utilized?.[key])}</td>
        <td class="amount">${num(s.cash_payable?.[key])}</td>
        <td class="amount">${num(s.itc_carry_forward?.[key])}</td>
      </tr>
    `).join("");
    body = `
      <div class="preview-heading compact">
        <div><p>Set-off for ${escapeHtml(gstReturnState.gstSettlementPeriod)} (statutory order: IGST credit first).</p></div>
        ${posted ? `<span class="pill ok">settled${s.period_locked ? " · period locked" : ""}</span>` : `<span class="pill warn">not settled</span>`}
      </div>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr><th>Head</th><th class="amount">Output (liability)</th><th class="amount">Input (ITC)</th><th class="amount">ITC used</th><th class="amount">Cash payable</th><th class="amount">ITC c/f</th></tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <div class="invoice-totals">
        <div><span>Total output GST</span><strong>${num(s.total_output)}</strong></div>
        <div><span>Total input GST (ITC)</span><strong>${num(s.total_input)}</strong></div>
        <div class="invoice-grand"><span>Net cash payable</span><strong>${num(s.net_cash_payable)}</strong></div>
      </div>
      ${s.note ? `<p class="muted">${escapeHtml(s.note)}</p>` : ""}
      ${posted ? `<p class="muted">Settled by ${escapeHtml(s.settled_by || "")}. Journal entry #${escapeHtml(s.journal_entry_id || "")} posted.</p>`
        : (admin && Number(s.total_output || 0) > 0 ? `
        <div class="report-date-controls">
          <label class="invoice-inter-toggle"><input type="checkbox" data-gst-lock checked> Lock this period after settlement</label>
          <button class="primary" type="button" data-business-action="gst-post">Post Settlement</button>
        </div>
        <p class="muted reversal-scope-note">Posts the set-off entry: Dr Output GST, Cr Input GST (utilised), Cr GST Payable (net cash).</p>
        ` : (admin ? "" : `<p class="muted">Only a tenant admin can post the settlement.</p>`))}
    `;
  }
  return `
    <div class="report-date-controls">
      <label>GST month <input type="month" data-gst-period value="${escapeHtml(gstReturnState.gstSettlementPeriod)}"></label>
      <button class="secondary" type="button" data-business-action="gst-preview">Preview</button>
    </div>
    ${body}
  `;
}

// ---- GSTR-3B monthly summary return ------------------------------------- //

// ══════════════════════════════════════════════════════════════════════
// SECTION: GSTR-3B (monthly summary return)
// API   : GET /api/v1/business/returns/gstr-3b?period=
// NOTE  : loadGstr3b, renderGstr3bPanel, downloadGstr3bJson
// ══════════════════════════════════════════════════════════════════════

export async function loadGstr3b(period) {
  gstReturnState.gstr3bPeriod = period || gstReturnState.gstr3bPeriod;
  const result = await apiRequest("mitrabooks", `/api/v1/business/returns/gstr-3b?period=${encodeURIComponent(gstReturnState.gstr3bPeriod)}`, { method: "GET" });
  gstReturnState.lastGstr3b = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { gstr3b: { ok: result.ok, period: gstReturnState.gstr3bPeriod } });
}

export function previewGstr3bFromInput() {
  const input = document.querySelector("[data-gstr3b-period]");
  loadGstr3b(input?.value || gstReturnState.gstr3bPeriod);
}

export function downloadGstr3bJson() {
  const j = gstReturnState.lastGstr3b?.gstn_json;
  if (!j) { setLoginStatus("warn", "Nothing to download", "Load a GSTR-3B period first."); return; }
  const blob = new Blob([JSON.stringify(j, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `gstr3b_${gstReturnState.gstr3bPeriod}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  renderJson(getApiOutput(), { gstr3b_download: { period: gstReturnState.gstr3bPeriod } });
}

export function renderGstr3bPanel() {
  const period = gstReturnState.gstr3bPeriod;
  const controls = `
    <div class="report-date-controls">
      <label>Return month <input type="month" data-gstr3b-period value="${escapeHtml(period)}"></label>
      <button class="secondary" type="button" data-business-action="gstr3b-load">Load</button>
      <button class="secondary" type="button" data-business-action="gstr3b-download-json">Download GSTN JSON</button>
    </div>`;
  const r = gstReturnState.lastGstr3b;
  if (!r) {
    return `${controls}<p class="muted">Loading GSTR-3B...</p>`;
  }
  if (r.ok === false) {
    return `${controls}${reportUnavailablePanel("GSTR-3B", r)}`;
  }
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const heads = [["IGST", "igst"], ["CGST", "cgst"], ["SGST", "sgst"]];
  const out = r.outward_supplies?.taxable || {};
  const itc = r.itc || {};
  const pay = r.tax_payment || {};
  const totals = r.totals || {};

  const itcRows = heads.map(([label, key]) => `
    <tr>
      <td>${label}</td>
      <td class="amount">${num(itc.available_rcm?.[key])}</td>
      <td class="amount">${num(itc.available_all_other?.[key])}</td>
      <td class="amount">${num(itc.reversed_others?.[key])}</td>
      <td class="amount"><strong>${num(itc.net_available?.[key])}</strong></td>
    </tr>`).join("");
  const rcm = r.outward_supplies?.inward_reverse_charge || {};
  const hasRcm = Number(rcm.taxable_value || 0) > 0
    || ["igst", "cgst", "sgst"].some((k) => Number(rcm[k] || 0) > 0);
  const payRows = heads.map(([label, key]) => `
    <tr>
      <td>${label}</td>
      <td class="amount">${num(pay[key]?.tax_payable)}</td>
      <td class="amount">${num(pay[key]?.paid_through_itc)}</td>
      <td class="amount">${num(pay[key]?.paid_in_cash)}</td>
    </tr>`).join("");

  return `
    ${controls}
    <div class="preview-heading compact">
      <div><p>GSTR-3B summary for ${escapeHtml(period)}${r.gstin ? ` · GSTIN ${escapeHtml(r.gstin)}` : ""}. Tax heads from the ledger; taxable value from posted invoices.</p></div>
      <span class="pill">Net cash ${num(totals.total_cash_payable)}</span>
    </div>

    <div class="table-preview compact-table">
      <h4>3.1 Outward taxable supplies</h4>
      <table>
        <thead><tr><th>Taxable value</th><th class="amount">IGST</th><th class="amount">CGST</th><th class="amount">SGST</th></tr></thead>
        <tbody><tr>
          <td class="amount">${num(out.taxable_value)}</td>
          <td class="amount">${num(out.igst)}</td>
          <td class="amount">${num(out.cgst)}</td>
          <td class="amount">${num(out.sgst)}</td>
        </tr></tbody>
      </table>
    </div>

    ${hasRcm ? `
    <div class="table-preview compact-table">
      <h4>3.1(d) Inward supplies liable to reverse charge</h4>
      <table>
        <thead><tr><th>Taxable value</th><th class="amount">IGST</th><th class="amount">CGST</th><th class="amount">SGST</th></tr></thead>
        <tbody><tr>
          <td class="amount">${num(rcm.taxable_value)}</td>
          <td class="amount">${num(rcm.igst)}</td>
          <td class="amount">${num(rcm.cgst)}</td>
          <td class="amount">${num(rcm.sgst)}</td>
        </tr></tbody>
      </table>
      <p class="muted">RCM liability of ${num(r.rcm_cash_payable)} must be paid in cash (account 22005) — it cannot be set off against ITC.</p>
    </div>` : ""}

    <div class="table-preview compact-table">
      <h4>4. Eligible ITC</h4>
      <table>
        <thead><tr><th>Head</th><th class="amount">RCM (4A3)</th><th class="amount">All other (4A5)</th><th class="amount">Reversed (4B)</th><th class="amount">Net (4C)</th></tr></thead>
        <tbody>${itcRows}</tbody>
      </table>
    </div>

    <div class="table-preview compact-table">
      <h4>6.1 Payment of tax</h4>
      <table>
        <thead><tr><th>Head</th><th class="amount">Tax payable</th><th class="amount">Paid via ITC</th><th class="amount">Paid in cash</th></tr></thead>
        <tbody>${payRows}</tbody>
      </table>
    </div>

    <div class="invoice-totals">
      <div><span>Total output tax</span><strong>${num(totals.total_output_tax)}</strong></div>
      <div><span>Net ITC</span><strong>${num(totals.total_itc_net)}</strong></div>
      <div class="invoice-grand"><span>Net cash payable</span><strong>${num(totals.total_cash_payable)}</strong></div>
    </div>
    ${(r.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}
  `;
}

// Wrapper: choose the return (GSTR-3B summary vs GSTR-1 outward detail).

// ══════════════════════════════════════════════════════════════════════
// SECTION: GST RETURNS — workspace switcher (3B / 1 / 2B / CMP-08 / GSTR-4)
// NOTE  : renderGstReturns, gstReturnState.gstReturnType state variable
// ══════════════════════════════════════════════════════════════════════

export function renderGstReturns() {
  const tabBtn = (id, label) => `
    <button class="report-tab ${gstReturnState.gstReturnType === id ? "active" : ""}" type="button"
      data-business-action="gst-return-type" data-return-type="${id}">${label}</button>`;
  const toggle = `<div class="report-tabs" role="tablist" style="margin:0 0 10px;">
    ${tabBtn("gstr3b", "GSTR-3B (summary)")}${tabBtn("gstr1", "GSTR-1 (outward)")}${tabBtn("cmp08", "CMP-08 (composition)")}${tabBtn("gstr4", "GSTR-4 (annual)")}${tabBtn("gstr2b", "GSTR-2B (ITC recon)")}
  </div>`;
  let panel;
  if (gstReturnState.gstReturnType === "gstr1") panel = renderGstr1Panel();
  else if (gstReturnState.gstReturnType === "cmp08") panel = renderCmp08Panel();
  else if (gstReturnState.gstReturnType === "gstr4") panel = renderGstr4Panel();
  else if (gstReturnState.gstReturnType === "gstr2b") panel = renderGstr2bPanel();
  else panel = renderGstr3bPanel();
  return `${toggle}${panel}`;
}

// ---- GSTR-2B / ITC reconciliation (upload the portal JSON) --------------- //

// ══════════════════════════════════════════════════════════════════════
// SECTION: GSTR-2B RECONCILIATION
// API   : POST /api/v1/business/returns/gstr-2b/reconcile?period=
// NOTE  : reconcileGstr2b, renderGstr2bPanel — file-upload JSON match
// ══════════════════════════════════════════════════════════════════════

export async function reconcileGstr2b() {
  const fileInput = document.querySelector("[data-gstr2b-file]");
  const periodInput = document.querySelector("[data-gstr2b-period]");
  const period = periodInput?.value || gstReturnState.gstr3bPeriod;
  const file = fileInput?.files?.[0];
  if (!file) {
    setLoginStatus("warn", "Choose a file", "Upload the GSTR-2B JSON downloaded from the GST portal.");
    return;
  }
  let parsed;
  try {
    parsed = JSON.parse(await file.text());
  } catch (_e) {
    setLoginStatus("danger", "Invalid JSON", "Could not parse the uploaded file as JSON.");
    return;
  }
  gstReturnState.gstr3bPeriod = period;
  const result = await apiRequest(
    "mitrabooks",
    `/api/v1/business/returns/gstr-2b/reconcile?period=${encodeURIComponent(period)}`,
    { method: "POST", body: JSON.stringify(parsed) },
  );
  gstReturnState.lastGstr2bRecon = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { gstr2b_recon: { ok: result.ok, period } });
}

export function renderGstr2bPanel() {
  const controls = `
    <div class="report-date-controls">
      <label>Return month <input type="month" data-gstr2b-period value="${escapeHtml(gstReturnState.gstr3bPeriod)}"></label>
      <label>GSTR-2B JSON <input type="file" accept="application/json,.json" data-gstr2b-file></label>
      <button class="secondary" type="button" data-business-action="gstr2b-reconcile">Reconcile</button>
    </div>
    <p class="muted">Download GSTR-2B for the month from the GST portal and upload the JSON. It is matched against the input GST booked on your purchase bills.</p>`;
  const r = gstReturnState.lastGstr2bRecon;
  if (!r) return controls;
  if (r.ok === false) return `${controls}${reportUnavailablePanel("GSTR-2B reconciliation", r)}`;
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const s = r.summary || {};

  const cards = [
    ["ITC as per 2B", s.itc_as_per_2b, "Total ITC the portal shows available"],
    ["ITC as per books", s.itc_as_per_books, "Input GST you have booked"],
    ["Matched", s.matched_itc, `${s.matched_count || 0} invoice(s) agree`],
    ["Available, not booked", s.available_not_booked, `${s.available_not_booked_count || 0} in 2B, missing in books`],
    ["At risk (not in 2B)", s.at_risk_not_in_2b, `${s.at_risk_count || 0} booked, absent from 2B`],
  ].map(([title, val, sub]) => `
    <article>
      <h4>${escapeHtml(title)}</h4>
      <div class="invoice-totals"><div class="invoice-grand"><span>${escapeHtml(sub)}</span><strong>${num(val)}</strong></div></div>
    </article>`).join("");

  const mismatchRows = (r.mismatch || []).map((m) => `
    <tr><td>${escapeHtml(m.gstin)}</td><td>${escapeHtml(m.invoice_number)}</td><td class="amount">${num(m.itc_2b)}</td><td class="amount">${num(m.itc_books)}</td><td class="amount">${num(m.difference)}</td></tr>`).join("");
  const only2bRows = (r.in_2b_not_in_books || []).map((g) => `
    <tr><td>${escapeHtml(g.gstin)}</td><td>${escapeHtml(g.invoice_number)}</td><td class="amount">${num(g.tax_total)}</td></tr>`).join("");
  const onlyBookRows = (r.in_books_not_in_2b || []).map((b) => `
    <tr><td>${escapeHtml(b.gstin)}</td><td>${escapeHtml(b.invoice_number)}</td><td class="amount">${num(b.tax_total)}</td></tr>`).join("");

  return `
    ${controls}
    <div class="preview-heading compact">
      <div><p>GSTR-2B reconciliation for ${escapeHtml(r.period || gstReturnState.gstr3bPeriod)}.</p></div>
      <span class="pill ${Number(s.at_risk_not_in_2b || 0) > 0 ? "warn" : "ok"}">${Number(s.at_risk_not_in_2b || 0) > 0 ? "ITC at risk" : "clean"}</span>
    </div>
    <div class="dashboard-main-grid platform-grid">${cards}</div>

    <div class="table-preview compact-table">
      <h4>Mismatches (in both, amounts differ)</h4>
      <table>
        <thead><tr><th>Supplier GSTIN</th><th>Invoice</th><th class="amount">ITC (2B)</th><th class="amount">ITC (books)</th><th class="amount">Difference</th></tr></thead>
        <tbody>${mismatchRows || `<tr><td colspan="5" class="muted">No mismatches.</td></tr>`}</tbody>
      </table>
    </div>

    <div class="table-preview compact-table">
      <h4>In 2B, not in books (ITC available you may have missed)</h4>
      <table>
        <thead><tr><th>Supplier GSTIN</th><th>Invoice</th><th class="amount">ITC</th></tr></thead>
        <tbody>${only2bRows || `<tr><td colspan="3" class="muted">Nothing unbooked.</td></tr>`}</tbody>
      </table>
    </div>

    <div class="table-preview compact-table">
      <h4>In books, not in 2B (ITC at risk — Section 16(2)(aa))</h4>
      <table>
        <thead><tr><th>Supplier GSTIN</th><th>Invoice</th><th class="amount">ITC</th></tr></thead>
        <tbody>${onlyBookRows || `<tr><td colspan="3" class="muted">All booked ITC is reflected in 2B.</td></tr>`}</tbody>
      </table>
    </div>
    ${(r.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}
  `;
}

// ---- GSTR-4 annual composition return ----------------------------------- //

// ══════════════════════════════════════════════════════════════════════
// SECTION: GSTR-4 (composition annual return)
// API   : GET /api/v1/business/returns/gstr-4?financial_year=
// NOTE  : loadGstr4, renderGstr4Panel, downloadGstr4Json
// ══════════════════════════════════════════════════════════════════════

export async function loadGstr4(fy) {
  gstReturnState.gstr4Fy = fy || gstReturnState.gstr4Fy;
  const result = await apiRequest("mitrabooks", `/api/v1/business/returns/gstr-4?financial_year=${encodeURIComponent(gstReturnState.gstr4Fy)}`, { method: "GET" });
  gstReturnState.lastGstr4 = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { gstr4: { ok: result.ok, fy: gstReturnState.gstr4Fy } });
}

export function previewGstr4FromInput() {
  const input = document.querySelector("[data-gstr4-fy]");
  loadGstr4(input?.value || gstReturnState.gstr4Fy);
}

export function downloadGstr4Json() {
  const j = gstReturnState.lastGstr4?.gstn_json;
  if (!j) { setLoginStatus("warn", "Nothing to download", "Load a GSTR-4 financial year first."); return; }
  const blob = new Blob([JSON.stringify(j, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `gstr4_${gstReturnState.gstr4Fy}.json`;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
  renderJson(getApiOutput(), { gstr4_download: { fy: gstReturnState.gstr4Fy } });
}

export function renderGstr4Panel() {
  const fyOpts = recentFinancialYears(4).map((fy) =>
    `<option value="${fy}" ${fy === gstReturnState.gstr4Fy ? "selected" : ""}>FY ${fy}</option>`).join("");
  const controls = `
    <div class="report-date-controls">
      <label>Financial year <select data-gstr4-fy>${fyOpts}</select></label>
      <button class="secondary" type="button" data-business-action="gstr4-load">Load</button>
      <button class="secondary" type="button" data-business-action="gstr4-download-json">Download GSTN JSON</button>
    </div>`;
  const r = gstReturnState.lastGstr4;
  if (!r) return `${controls}<p class="muted">Loading GSTR-4...</p>`;
  if (r.ok === false) return `${controls}${reportUnavailablePanel("GSTR-4", r)}`;
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const s = r.cmp08_summary || {};
  const out = r.outward_supplies || {};
  const inw = r.inward_supplies || {};
  const rateLabel = r.composition_rate != null ? `${escapeHtml(String(r.composition_rate))}%` : "—";

  const qRows = (s.quarters || []).map((q) => `
    <tr><td>${escapeHtml(q.quarter)}</td><td class="amount">${num(q.turnover)}</td><td class="amount">${num(q.cgst)}</td><td class="amount">${num(q.sgst)}</td><td class="amount">${num(q.total_tax)}</td></tr>`).join("");
  const inwRows = (kind, block) => (block?.rows || []).map((row) => `
    <tr><td>${escapeHtml(kind)}</td><td class="amount">${escapeHtml(String(row.rate ?? ""))}%</td><td class="amount">${num(row.taxable_value)}</td><td class="amount">${num(row.igst)}</td><td class="amount">${num(row.cgst)}</td><td class="amount">${num(row.sgst)}</td></tr>`).join("");
  const inwardBody = `${inwRows("Registered", inw.registered)}${inwRows("Unregistered", inw.unregistered)}`;

  return `
    ${controls}
    <div class="preview-heading compact">
      <div><p>GSTR-4 annual return for FY ${escapeHtml(r.financial_year || gstReturnState.gstr4Fy)}${r.gstin ? ` · GSTIN ${escapeHtml(r.gstin)}` : ""} · ${escapeHtml(r.composition_category || "composition")} @ ${rateLabel}.</p></div>
      <span class="pill">Annual tax ${num(out.total_tax)}</span>
    </div>

    <div class="table-preview compact-table">
      <h4>Table 5 — self-assessed liability (CMP-08, quarter-wise)</h4>
      <table>
        <thead><tr><th>Quarter</th><th class="amount">Turnover</th><th class="amount">CGST</th><th class="amount">SGST</th><th class="amount">Tax</th></tr></thead>
        <tbody>${qRows}</tbody>
        <tfoot><tr><th>Total</th><td class="amount">${num(s.total_turnover)}</td><td class="amount">${num(s.cgst)}</td><td class="amount">${num(s.sgst)}</td><td class="amount"><strong>${num(s.total_tax)}</strong></td></tr></tfoot>
      </table>
    </div>

    <div class="table-preview compact-table">
      <h4>Table 6 — outward supplies (composition liability)</h4>
      <table>
        <thead><tr><th class="amount">Turnover</th><th class="amount">Rate</th><th class="amount">CGST</th><th class="amount">SGST</th><th class="amount">Tax</th></tr></thead>
        <tbody><tr><td class="amount">${num(out.turnover)}</td><td class="amount">${rateLabel}</td><td class="amount">${num(out.cgst)}</td><td class="amount">${num(out.sgst)}</td><td class="amount"><strong>${num(out.total_tax)}</strong></td></tr></tbody>
      </table>
    </div>

    <div class="table-preview compact-table">
      <h4>Table 4 — inward supplies (purchases)</h4>
      <table>
        <thead><tr><th>Supplier</th><th class="amount">Rate</th><th class="amount">Taxable</th><th class="amount">IGST</th><th class="amount">CGST</th><th class="amount">SGST</th></tr></thead>
        <tbody>${inwardBody || `<tr><td colspan="6" class="muted">No inward supplies recorded.</td></tr>`}</tbody>
      </table>
    </div>
    ${(r.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}
  `;
}

// ---- CMP-08 quarterly composition statement ----------------------------- //
export async function loadCmp08(quarter) {
  gstReturnState.cmp08Quarter = quarter || gstReturnState.cmp08Quarter;
  const result = await apiRequest("mitrabooks", `/api/v1/business/returns/cmp-08?quarter=${encodeURIComponent(gstReturnState.cmp08Quarter)}`, { method: "GET" });
  gstReturnState.lastCmp08 = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { cmp08: { ok: result.ok, quarter: gstReturnState.cmp08Quarter } });
}

export function previewCmp08FromInput() {
  const input = document.querySelector("[data-cmp08-quarter]");
  loadCmp08(input?.value || gstReturnState.cmp08Quarter);
}

export function downloadCmp08Json() {
  const j = gstReturnState.lastCmp08?.gstn_json;
  if (!j) { setLoginStatus("warn", "Nothing to download", "Load a CMP-08 quarter first."); return; }
  const blob = new Blob([JSON.stringify(j, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `cmp08_${gstReturnState.cmp08Quarter}.json`;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
  renderJson(getApiOutput(), { cmp08_download: { quarter: gstReturnState.cmp08Quarter } });
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: GST COMPOSITION — CMP-08 (quarterly statement)
// API   : GET /api/v1/business/returns/cmp-08?quarter=
// NOTE  : renderCmp08Panel, previewCmp08FromInput, postCmp08Liability
// ══════════════════════════════════════════════════════════════════════

export function renderCmp08Panel() {
  const quarterOpts = recentFyQuarters(6).map((q) =>
    `<option value="${q}" ${q === gstReturnState.cmp08Quarter ? "selected" : ""}>${q.replace("-Q", " · Q")}</option>`).join("");
  const controls = `
    <div class="report-date-controls">
      <label>Quarter <select data-cmp08-quarter>${quarterOpts}</select></label>
      <button class="secondary" type="button" data-business-action="cmp08-load">Load</button>
      <button class="secondary" type="button" data-business-action="cmp08-download-json">Download GSTN JSON</button>
    </div>`;
  const r = gstReturnState.lastCmp08;
  if (!r) return `${controls}<p class="muted">Loading CMP-08...</p>`;
  if (r.ok === false) return `${controls}${reportUnavailablePanel("CMP-08", r)}`;
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const out = r.outward_supplies || {};
  const pay = r.tax_payable || {};
  const rateLabel = r.composition_rate != null ? `${escapeHtml(String(r.composition_rate))}%` : "—";
  return `
    ${controls}
    <div class="preview-heading compact">
      <div><p>CMP-08 for ${escapeHtml(r.quarter || gstReturnState.cmp08Quarter)}${r.gstin ? ` · GSTIN ${escapeHtml(r.gstin)}` : ""} · ${escapeHtml(r.composition_category || "composition")} @ ${rateLabel}.</p></div>
      <span class="pill">Payable ${num(pay.total)}</span>
    </div>
    <div class="table-preview compact-table">
      <h4>Table 3 — self-assessed liability</h4>
      <table>
        <thead><tr><th>Particulars</th><th class="amount">Value</th><th class="amount">IGST</th><th class="amount">CGST</th><th class="amount">SGST</th></tr></thead>
        <tbody>
          <tr><td>Outward supplies (incl. composition turnover)</td><td class="amount">${num(out.turnover)}</td><td class="amount">${num(out.igst)}</td><td class="amount">${num(out.cgst)}</td><td class="amount">${num(out.sgst)}</td></tr>
          <tr><td>Inward supplies (reverse charge)</td><td class="amount">—</td><td class="amount">${num(r.inward_reverse_charge?.igst)}</td><td class="amount">${num(r.inward_reverse_charge?.cgst)}</td><td class="amount">${num(r.inward_reverse_charge?.sgst)}</td></tr>
        </tbody>
        <tfoot><tr><th colspan="2">Tax payable (incl. interest ${num(pay.interest)})</th><td class="amount">${num(pay.igst)}</td><td class="amount">${num(pay.cgst)}</td><td class="amount">${num(pay.sgst)}</td></tr></tfoot>
      </table>
    </div>
    <div class="invoice-totals">
      <div class="invoice-grand"><span>Total tax payable</span><strong>${num(pay.total)}</strong></div>
    </div>
    ${(r.liability_posting || []).length ? `
    <p class="muted">✓ Liability posted: journal entry #${escapeHtml(String(r.liability_posting[0].journal_entry_id))} dated ${escapeHtml(r.liability_posting[0].entry_date)}. Reverse it to redo.</p>`
    : (Number(out.total_tax || 0) > 0 && isBusinessAdmin() ? `
    <div class="report-date-controls">
      <button class="primary" type="button" data-business-action="cmp08-post">Post liability to ledger</button>
      <span class="muted">Dr 54007 GST Expense (Composition) / Cr 22004 GST Payable — outward levy only; RCM is already booked per bill.</span>
    </div>` : "")}
    ${(r.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}
  `;
}

export async function postCmp08Liability() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/returns/cmp-08/post", {
    method: "POST",
    headers: { "X-Idempotency-Key": `cmp08-${gstReturnState.cmp08Quarter}` },
    body: JSON.stringify({ quarter: gstReturnState.cmp08Quarter }),
  });
  if (result.ok) {
    setLoginStatus("ok", "Liability posted", `CMP-08 ${gstReturnState.cmp08Quarter}: ${formatCurrency(Number(result.payload?.amount || 0))} — journal entry #${result.payload?.journal_entry_id}.`);
    await loadCmp08(gstReturnState.cmp08Quarter);
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can post the composition liability.");
  } else {
    setLoginStatus("danger", "Posting failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { cmp08_post: { ok: result.ok, status: result.status } });
}

// ══════════════════════════════════════════════════════════════════════
// SECTION: GSTR-1 (Outward Supplies)
// API   : GET /api/v1/business/returns/gstr-1?period=
// NOTE  : loadGstr1, renderGstr1Panel, downloadGstr1Json
// ══════════════════════════════════════════════════════════════════════

export async function loadGstr1(period) {
  gstReturnState.gstr3bPeriod = period || gstReturnState.gstr3bPeriod;
  const result = await apiRequest("mitrabooks", `/api/v1/business/returns/gstr-1?period=${encodeURIComponent(gstReturnState.gstr3bPeriod)}`, { method: "GET" });
  gstReturnState.lastGstr1 = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { gstr1: { ok: result.ok, period: gstReturnState.gstr3bPeriod } });
}

export function previewGstr1FromInput() {
  const input = document.querySelector("[data-gstr1-period]");
  loadGstr1(input?.value || gstReturnState.gstr3bPeriod);
}

export function downloadGstr1Json() {
  const j = gstReturnState.lastGstr1?.gstn_json;
  if (!j) { setLoginStatus("warn", "Nothing to download", "Load a GSTR-1 period first."); return; }
  const blob = new Blob([JSON.stringify(j, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `gstr1_${gstReturnState.gstr3bPeriod}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  renderJson(getApiOutput(), { gstr1_download: { period: gstReturnState.gstr3bPeriod } });
}

export function renderGstr1Panel() {
  const period = gstReturnState.gstr3bPeriod;
  const controls = `
    <div class="report-date-controls">
      <label>Return month <input type="month" data-gstr1-period value="${escapeHtml(period)}"></label>
      <button class="secondary" type="button" data-business-action="gstr1-load">Load</button>
      <button class="secondary" type="button" data-business-action="gstr1-download-json">Download GSTN JSON</button>
    </div>`;
  const r = gstReturnState.lastGstr1;
  if (!r) { return `${controls}<p class="muted">Loading GSTR-1...</p>`; }
  if (r.ok === false) { return `${controls}${reportUnavailablePanel("GSTR-1", r)}`; }
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const s = r.sections || {};

  const sectionCards = [
    ["B2B (4A)", `${s.b2b?.invoices || 0} inv · ${s.b2b?.recipients || 0} GSTIN`, s.b2b?.taxable_value, s.b2b?.tax],
    ["B2C Large (5)", `${s.b2cl?.invoices || 0} inv`, s.b2cl?.taxable_value, s.b2cl?.tax],
    ["B2C Small (7)", `${s.b2cs?.rows || 0} rows`, s.b2cs?.taxable_value, s.b2cs?.tax],
    ["Exports/SEZ (6A)", `${s.exp?.invoices || 0} inv · zero-rated`, s.exp?.taxable_value, s.exp?.tax],
    ["Credit Notes (9B)", `${s.cdnr?.notes || 0} notes`, s.cdnr?.taxable_value, s.cdnr?.tax],
    ["HSN (12)", `${s.hsn?.rows || 0} rows`, s.hsn?.taxable_value, s.hsn?.tax],
  ].map(([title, sub, txval, tax]) => `
    <article>
      <h4>${escapeHtml(title)}</h4>
      <p class="muted">${escapeHtml(sub)}</p>
      <div class="invoice-totals">
        <div><span>Taxable</span><strong>${num(txval)}</strong></div>
        <div><span>Tax</span><strong>${num(tax)}</strong></div>
      </div>
    </article>`).join("");

  const b2csRows = (r.b2cs_rows || []).map((row) => `
    <tr>
      <td>${escapeHtml(row.pos || "")}</td>
      <td>${escapeHtml(row.supply_type || "")}</td>
      <td class="amount">${escapeHtml(String(row.rate ?? ""))}%</td>
      <td class="amount">${num(row.taxable_value)}</td>
      <td class="amount">${num(row.igst)}</td>
      <td class="amount">${num(row.cgst)}</td>
      <td class="amount">${num(row.sgst)}</td>
    </tr>`).join("");
  const hsnRows = (r.hsn_rows || []).map((row) => `
    <tr>
      <td>${escapeHtml(row.hsn_sac || "")}</td>
      <td>${escapeHtml(row.uqc || "")}</td>
      <td class="amount">${escapeHtml(String(row.rate ?? ""))}%</td>
      <td class="amount">${escapeHtml(String(row.quantity ?? ""))}</td>
      <td class="amount">${num(row.taxable_value)}</td>
      <td class="amount">${num(row.igst)}</td>
      <td class="amount">${num(row.cgst)}</td>
      <td class="amount">${num(row.sgst)}</td>
    </tr>`).join("");

  return `
    ${controls}
    <div class="preview-heading compact">
      <div><p>GSTR-1 outward supplies for ${escapeHtml(period)}${r.gstin ? ` · GSTIN ${escapeHtml(r.gstin)}` : ""}. Built from posted invoices and credit notes. Docs ${escapeHtml(String(s.docs?.total || 0))} (${escapeHtml(s.docs?.from || "-")} → ${escapeHtml(s.docs?.to || "-")}).</p></div>
    </div>
    <div class="dashboard-main-grid platform-grid">${sectionCards}</div>

    <div class="table-preview compact-table">
      <h4>B2C Small (7) — rate-wise by place of supply</h4>
      <table>
        <thead><tr><th>Place of supply</th><th>Type</th><th class="amount">Rate</th><th class="amount">Taxable</th><th class="amount">IGST</th><th class="amount">CGST</th><th class="amount">SGST</th></tr></thead>
        <tbody>${b2csRows || `<tr><td colspan="7" class="muted">No B2C-small supplies.</td></tr>`}</tbody>
      </table>
    </div>

    <div class="table-preview compact-table">
      <h4>HSN summary (12)</h4>
      <table>
        <thead><tr><th>HSN/SAC</th><th>UQC</th><th class="amount">Rate</th><th class="amount">Qty</th><th class="amount">Taxable</th><th class="amount">IGST</th><th class="amount">CGST</th><th class="amount">SGST</th></tr></thead>
        <tbody>${hsnRows || `<tr><td colspan="8" class="muted">No HSN data.</td></tr>`}</tbody>
      </table>
    </div>
    ${(r.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}
  `;
}
