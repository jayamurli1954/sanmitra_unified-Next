// ====================================================================
// SECTION: ACCOUNTING DIMENSIONS (cost centre / project)
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initDimensions(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastDimensions = null;
export let lastDimensionReport = null;
export let lastBranchConsolidatedReport = null;
export let dimensionReportType = "cost_centre";

/** @type {Record<string, Function> | null} */
let deps = null;

export function initDimensions(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initDimensions() must be called before using dimension helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function reportUnavailablePanel(title, payload) { return requireDeps().reportUnavailablePanel(title, payload); }
function rerenderBusinessReportsIfActive() { return requireDeps().rerenderBusinessReportsIfActive(); }
function downloadApiFile(appKey, path, filename, opts) { return requireDeps().downloadApiFile(appKey, path, filename, opts); }
function getApiOutput() { return requireDeps().getApiOutput(); }

// SECTION: ACCOUNTING DIMENSIONS (cost centre / project)
// API   : GET/POST /api/v1/business/dimensions  GET .../report
// NOTE  : loadDimensions, createDimensionFromForm, deactivateDimension, renderDimensionsPanel
// ══════════════════════════════════════════════════════════════════════

export async function loadDimensions() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/dimensions", { method: "GET" });
  lastDimensions = result.ok ? result.payload : null;
  renderJson(getApiOutput(), { dimensions: { ok: result.ok, count: result.payload?.count || 0 } });
  return lastDimensions;
}

export function dimensionOptions(kind, selected) {
  const rows = (kind === "cost_centre" ? lastDimensions?.cost_centres : lastDimensions?.projects) || [];
  if (!rows.length) return null;  // no masters -> hide the select entirely
  const none = `<option value="">No ${kind === "cost_centre" ? "cost centre" : "project"}</option>`;
  return none + rows.map((d) =>
    `<option value="${escapeHtml(d.dimension_id)}" ${d.dimension_id === selected ? "selected" : ""}>${escapeHtml(`${d.code} - ${d.name}`)}</option>`).join("");
}

export function voucherDimensionPayload() {
  const costCentre = document.getElementById("business-voucher-cost-centre")?.value || "";
  const project = document.getElementById("business-voucher-project")?.value || "";
  return {
    cost_centre_id: costCentre || null,
    project_id: project || null,
  };
}

export async function createDimensionFromForm() {
  const form = document.querySelector("[data-dim-form]");
  if (!form) return;
  const body = {
    dimension_type: form.querySelector("select[name='dim_type']")?.value || "cost_centre",
    code: form.querySelector("input[name='dim_code']")?.value || "",
    name: form.querySelector("input[name='dim_name']")?.value || "",
  };
  if (!body.name.trim()) {
    setLoginStatus("warn", "Name required", "Give the cost centre / project a name.");
    return;
  }
  const result = await apiRequest("mitrabooks", "/api/v1/business/dimensions", {
    method: "POST", body: JSON.stringify(body),
  });
  if (result.ok) {
    setLoginStatus("ok", "Dimension created", `${result.payload?.code} — ${result.payload?.name}`);
    await loadDimensions();
    await loadDimensionReport();
    await loadBranchConsolidatedReport();
  } else {
    setLoginStatus("danger", "Create failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { dimension_create: { ok: result.ok, status: result.status } });
}

export async function deactivateDimension(dimensionId) {
  const result = await apiRequest("mitrabooks", `/api/v1/business/dimensions/${encodeURIComponent(dimensionId)}/deactivate`, { method: "PATCH" });
  if (result.ok) {
    setLoginStatus("ok", "Dimension deactivated", "Existing documents keep the tag; new ones stop offering it.");
    await loadDimensions();
    await loadDimensionReport();
    await loadBranchConsolidatedReport();
  } else {
    setLoginStatus("danger", "Deactivate failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { dimension_deactivate: { ok: result.ok, status: result.status } });
}

export async function loadDimensionReport() {
  const typeSel = document.querySelector("[data-dim-report-type]");
  const fromInput = document.querySelector("[data-dim-from]");
  const toInput = document.querySelector("[data-dim-to]");
  if (typeSel) dimensionReportType = typeSel.value || dimensionReportType;
  const params = new URLSearchParams({ dimension_type: dimensionReportType });
  if (fromInput?.value) params.set("from_date", fromInput.value);
  if (toInput?.value) params.set("to_date", toInput.value);
  const result = await apiRequest("mitrabooks", `/api/v1/business/dimensions/report?${params.toString()}`, { method: "GET" });
  lastDimensionReport = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { dimension_report: { ok: result.ok, type: dimensionReportType } });
}

export async function loadBranchConsolidatedReport() {
  const fromInput = document.querySelector("[data-dim-from]");
  const toInput = document.querySelector("[data-dim-to]");
  const params = new URLSearchParams();
  if (fromInput?.value) params.set("from_date", fromInput.value);
  if (toInput?.value) params.set("to_date", toInput.value);
  const query = params.toString();
  const result = await apiRequest("mitrabooks", `/api/v1/business/dimensions/branch-report${query ? `?${query}` : ""}`, { method: "GET" });
  lastBranchConsolidatedReport = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { branch_consolidated_report: { ok: result.ok } });
}

export async function downloadDimensionReport(format) {
  const typeSel = document.querySelector("[data-dim-report-type]");
  const fromInput = document.querySelector("[data-dim-from]");
  const toInput = document.querySelector("[data-dim-to]");
  if (typeSel) dimensionReportType = typeSel.value || dimensionReportType;
  const params = new URLSearchParams({ dimension_type: dimensionReportType, format });
  if (fromInput?.value) params.set("from_date", fromInput.value);
  if (toInput?.value) params.set("to_date", toInput.value);
  const filename = `dimension_${dimensionReportType}.${format}`;
  const result = await downloadApiFile("mitrabooks", `/api/v1/business/dimensions/report/export?${params.toString()}`, filename, { timeoutMs: 30000 });
  renderJson(getApiOutput(), { dimension_report_export: { ok: result.ok, status: result.status, format } });
}

export function renderDimensionsPanel() {
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const dims = lastDimensions;
  const masterRows = (dims?.items || []).map((d) => `
    <tr>
      <td>${escapeHtml(d.dimension_type === "cost_centre" ? "Cost centre" : "Project")}</td>
      <td>${escapeHtml(d.code || "")}</td>
      <td>${escapeHtml(d.name || "")}</td>
      <td><button class="secondary" type="button" data-business-action="dim-deactivate" data-dimension-id="${escapeHtml(d.dimension_id)}">Deactivate</button></td>
    </tr>`).join("");

  const manage = `
    <div class="report-date-controls" data-dim-form>
      <label>Type <select name="dim_type">
        <option value="cost_centre">Cost centre</option>
        <option value="project">Project</option>
      </select></label>
      <label>Code <input type="text" name="dim_code" maxlength="20" placeholder="e.g. BLR" style="width:90px;text-transform:uppercase;"></label>
      <label>Name <input type="text" name="dim_name" maxlength="120" placeholder="e.g. Bengaluru branch"></label>
      <button class="primary" type="button" data-business-action="dim-create">Add</button>
    </div>
    <div class="table-preview compact-table">
      <table>
        <thead><tr><th>Type</th><th>Code</th><th>Name</th><th></th></tr></thead>
        <tbody>${masterRows || `<tr><td colspan="4" class="muted">No dimensions yet — add a cost centre or project above. They then appear as tags on the invoice and bill forms.</td></tr>`}</tbody>
      </table>
    </div>`;

  const r = lastDimensionReport;
  let reportBody = "";
  if (r && r.ok === false) {
    reportBody = reportUnavailablePanel("Dimension report", r);
  } else if (r) {
    const rows = (r.rows || []).map((row) => `
      <tr>
        <td>${escapeHtml(`${row.code} - ${row.name}`)}</td>
        <td class="amount">${num(row.income)}</td>
        <td class="amount">${num(row.expense)}</td>
        <td class="amount"><strong>${num(row.net)}</strong></td>
      </tr>`).join("");
    const u = r.untagged || {};
    const t = r.totals || {};
    reportBody = `
      <div class="preview-heading compact">
        <div><p>${escapeHtml(r.from_date)} → ${escapeHtml(r.to_date)} · ${escapeHtml(String(r.document_counts?.invoices || 0))} invoice(s), ${escapeHtml(String(r.document_counts?.bills || 0))} bill(s).</p></div>
        <span class="pill">Net ${num(t.net)}</span>
      </div>
      <div class="report-date-controls">
        <button class="secondary" type="button" data-business-action="dim-report-export" data-format="csv">CSV</button>
        <button class="secondary" type="button" data-business-action="dim-report-export" data-format="xlsx">Excel</button>
        <button class="secondary" type="button" data-business-action="dim-report-export" data-format="pdf">PDF</button>
        <button class="secondary" type="button" data-business-action="dim-report-export" data-format="json">JSON</button>
      </div>
      <div class="table-preview compact-table">
        <table>
          <thead><tr><th>${dimensionReportType === "cost_centre" ? "Cost centre" : "Project"}</th><th class="amount">Income</th><th class="amount">Expense</th><th class="amount">Net</th></tr></thead>
          <tbody>
            ${rows || `<tr><td colspan="4" class="muted">No tagged documents in this period.</td></tr>`}
            <tr><td><em>Untagged</em></td><td class="amount">${num(u.income)}</td><td class="amount">${num(u.expense)}</td><td class="amount">${num(u.net)}</td></tr>
          </tbody>
          <tfoot><tr><th>Total</th><td class="amount">${num(t.income)}</td><td class="amount">${num(t.expense)}</td><td class="amount"><strong>${num(t.net)}</strong></td></tr></tfoot>
        </table>
      </div>
      ${(r.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}`;
  }

  const br = lastBranchConsolidatedReport;
  let branchReportBody = "";
  if (br && br.ok === false) {
    branchReportBody = reportUnavailablePanel("Branch consolidated report", br);
  } else if (br) {
    const rows = (br.rows || []).map((row) => `
      <tr>
        <td>${escapeHtml(`${row.branch_code || ""} - ${row.branch_name || ""}`)}</td>
        <td>${escapeHtml(row.cost_centre_code || "Unmapped")}</td>
        <td class="amount">${num(row.income)}</td>
        <td class="amount">${num(row.expense)}</td>
        <td class="amount"><strong>${num(row.net)}</strong></td>
      </tr>`).join("");
    const u = br.unassigned || {};
    const t = br.totals || {};
    const unmatched = Array.isArray(u.unmatched_cost_centres) && u.unmatched_cost_centres.length
      ? `<p class="muted">Unmapped cost centres: ${u.unmatched_cost_centres.map((row) => escapeHtml(`${row.code || ""} - ${row.name || ""}`)).join(", ")}</p>`
      : "";
    branchReportBody = `
      <div class="preview-heading compact">
        <div><p>${escapeHtml(br.from_date || "")} â†’ ${escapeHtml(br.to_date || "")} Â· branch rollup from cost-centre tags.</p></div>
        <span class="pill">Net ${num(t.net)}</span>
      </div>
      <div class="table-preview compact-table">
        <table>
          <thead><tr><th>Branch</th><th>Cost centre</th><th class="amount">Income</th><th class="amount">Expense</th><th class="amount">Net</th></tr></thead>
          <tbody>
            ${rows || `<tr><td colspan="5" class="muted">No active branches are mapped in admin settings.</td></tr>`}
            <tr><td><em>Unassigned</em></td><td>Untagged / unmapped</td><td class="amount">${num(u.income)}</td><td class="amount">${num(u.expense)}</td><td class="amount">${num(u.net)}</td></tr>
          </tbody>
          <tfoot><tr><th>Total</th><td></td><td class="amount">${num(t.income)}</td><td class="amount">${num(t.expense)}</td><td class="amount"><strong>${num(t.net)}</strong></td></tr></tfoot>
        </table>
      </div>
      ${unmatched}
      ${(br.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}`;
  }

  return `
    <div class="table-preview compact-table"><h4>Cost centres &amp; projects</h4></div>
    ${manage}
    <hr style="margin:18px 0;border:none;border-top:1px solid var(--line,#ddd);">
    <div class="table-preview compact-table"><h4>Income / expense by dimension</h4></div>
    <div class="report-date-controls">
      <label>View by <select data-dim-report-type>
        <option value="cost_centre" ${dimensionReportType === "cost_centre" ? "selected" : ""}>Cost centre</option>
        <option value="project" ${dimensionReportType === "project" ? "selected" : ""}>Project</option>
      </select></label>
      <label>From <input type="date" data-dim-from></label>
      <label>To <input type="date" data-dim-to></label>
      <button class="secondary" type="button" data-business-action="dim-report-load">Load</button>
    </div>
    ${reportBody || `<p class="muted">Loading dimension report...</p>`}
    <hr style="margin:18px 0;border:none;border-top:1px solid var(--line,#ddd);">
    <div class="table-preview compact-table"><h4>Branch consolidated P&amp;L</h4></div>
    ${branchReportBody || `<p class="muted">Loading branch consolidated report...</p>`}
  `;
}

// ---- Inventory (opt-in): items, stock register, closing stock ------------- //

// ══════════════════════════════════════════════════════════════════════
