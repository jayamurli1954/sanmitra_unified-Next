// ====================================================================
// SECTION: OPENING BALANCES + YEAR-END CLOSE (+ bulk voucher import)
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initOpeningYearEnd(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastObPreview = null;
export let obCsvText = "";
export let lastViPreview = null;
export let viCsvText = "";
export let lastYePreview = null;
export let yeFy = "";

/** @type {Record<string, Function> | null} */
let deps = null;

export function initOpeningYearEnd(injected) {
  deps = injected;
  if (!yeFy) {
    yeFy = deps.currentFinancialYear();
  }
}

function requireDeps() {
  if (!deps) {
    throw new Error("initOpeningYearEnd() must be called before using opening/year-end helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function reportUnavailablePanel(title, payload) { return requireDeps().reportUnavailablePanel(title, payload); }
function rerenderBusinessReportsIfActive() { return requireDeps().rerenderBusinessReportsIfActive(); }
function isBusinessAdmin() { return requireDeps().isBusinessAdmin(); }
function recentFinancialYears(count = 4) { return requireDeps().recentFinancialYears(count); }
function downloadApiFile(appKey, path, filename, options) { return requireDeps().downloadApiFile(appKey, path, filename, options); }
function getApiOutput() { return requireDeps().getApiOutput(); }

export async function downloadObTemplate() {
  const result = await downloadApiFile("mitrabooks", "/api/v1/business/opening-balances/template", "opening_balances_template.csv");
  renderJson(getApiOutput(), { ob_template: { ok: result.ok } });
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: OPENING BALANCES + YEAR-END CLOSE
// API   : POST /api/v1/business/opening-balances  POST /api/v1/business/year-end/close
// NOTE  : previewOpeningBalances, postOpeningBalances, previewYearEnd, postYearEndClose
// ══════════════════════════════════════════════════════════════════════

export async function previewOpeningBalances() {
  const fileInput = document.querySelector("[data-ob-file]");
  const asOfInput = document.querySelector("[data-ob-asof]");
  const presetSelect = document.querySelector("[data-ob-preset]");
  const file = fileInput?.files?.[0];
  if (!file && !obCsvText) {
    setLoginStatus("warn", "Choose a file", "Upload the opening-balance CSV (download the template for the format).");
    return;
  }
  if (file) obCsvText = await file.text();

  const preset = presetSelect?.value || null;
  let header_mapping = null;
  if (preset === "custom") {
    header_mapping = {
      account_code: document.querySelector("[data-ob-map-code]")?.value || "",
      account_name: document.querySelector("[data-ob-map-name]")?.value || "",
      debit: document.querySelector("[data-ob-map-debit]")?.value || "",
      credit: document.querySelector("[data-ob-map-credit]")?.value || "",
      balance: document.querySelector("[data-ob-map-balance]")?.value || "",
      party: document.querySelector("[data-ob-map-party]")?.value || "",
    };
    for (const k in header_mapping) {
      if (!header_mapping[k]) delete header_mapping[k];
    }
  }

  const body = { csv: obCsvText, preset, header_mapping };
  if (asOfInput?.value) body.as_of = asOfInput.value;
  const result = await apiRequest("mitrabooks", "/api/v1/business/opening-balances/preview", {
    method: "POST", body: JSON.stringify(body),
  });
  lastObPreview = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  if (result.ok && lastObPreview) {
    lastObPreview.preset = preset;
    lastObPreview.header_mapping = header_mapping;
  }
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { ob_preview: { ok: result.ok, status: result.status } });
}

export async function postOpeningBalances() {
  if (!obCsvText || !lastObPreview || lastObPreview.ok === false || !lastObPreview.can_post) {
    setLoginStatus("warn", "Preview first", "Upload and preview a clean file (zero errors) before posting.");
    return;
  }
  const allowDup = !!document.querySelector("[data-ob-allow-duplicate]")?.checked;
  const body = {
    csv: obCsvText,
    as_of: lastObPreview.as_of,
    allow_duplicate: allowDup,
    preset: lastObPreview.preset || null,
    header_mapping: lastObPreview.header_mapping || null
  };
  const result = await apiRequest("mitrabooks", "/api/v1/business/opening-balances", {
    method: "POST",
    headers: { "X-Idempotency-Key": `opening-balance-${Date.now()}` },
    body: JSON.stringify(body),
  });
  if (result.ok) {
    setLoginStatus("ok", "Opening balances posted", `Journal entry #${result.payload?.journal_entry_id} with ${result.payload?.line_count} line(s).`);
    obCsvText = "";
    lastObPreview = null;
    rerenderBusinessReportsIfActive();
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can post opening balances.");
  } else {
    setLoginStatus("danger", "Posting failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { ob_post: { ok: result.ok, status: result.status } });
}

export async function downloadObExport() {
  const result = await downloadApiFile("mitrabooks", "/api/v1/business/opening-balances/export", "opening_balances.csv");
  renderJson(getApiOutput(), { ob_export: { ok: result.ok } });
}

export async function downloadViTemplate() {
  const result = await downloadApiFile("mitrabooks", "/api/v1/business/vouchers/bulk-import/template", "vouchers_bulk_import_template.csv");
  renderJson(getApiOutput(), { vi_template: { ok: result.ok } });
}

export async function previewBulkVouchers() {
  const fileInput = document.querySelector("[data-vi-file]");
  const file = fileInput?.files?.[0];
  if (!file && !viCsvText) {
    setLoginStatus("warn", "Choose a file", "Upload the voucher CSV (download the template for the format).");
    return;
  }
  if (file) viCsvText = await file.text();
  const body = { csv: viCsvText };
  const result = await apiRequest("mitrabooks", "/api/v1/business/vouchers/bulk-import/preview", {
    method: "POST", body: JSON.stringify(body),
  });
  lastViPreview = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { vi_preview: { ok: result.ok, status: result.status } });
}

export async function postBulkVouchers() {
  if (!viCsvText || !lastViPreview || lastViPreview.ok === false || !lastViPreview.can_import) {
    setLoginStatus("warn", "Preview first", "Upload and preview a clean file (zero errors) before importing.");
    return;
  }
  const body = { csv: viCsvText };
  const result = await apiRequest("mitrabooks", "/api/v1/business/vouchers/bulk-import", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (result.ok) {
    setLoginStatus("ok", "Vouchers imported", `Successfully imported ${result.payload?.imported_count} voucher(s).`);
    viCsvText = "";
    lastViPreview = null;
    rerenderBusinessReportsIfActive();
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can perform bulk voucher imports.");
  } else {
    setLoginStatus("danger", "Import failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { vi_post: { ok: result.ok, status: result.status } });
}

window.toggleObCustomMappingView = function() {
  const preset = document.querySelector("[data-ob-preset]")?.value;
  const customDiv = document.getElementById("ob-custom-mapping-fields");
  if (customDiv) {
    customDiv.style.display = preset === "custom" ? "block" : "none";
  }
};

document.addEventListener("change", (event) => {
  const target = event.target instanceof Element ? event.target : null;
  if (!(target instanceof HTMLSelectElement)) {
    return;
  }
  if (target.matches("[data-ob-preset]")) {
    window.toggleObCustomMappingView();
  }
});

export async function previewYearEnd() {
  const fySel = document.querySelector("[data-ye-fy]");
  yeFy = fySel?.value || yeFy;
  const result = await apiRequest("mitrabooks", `/api/v1/business/year-end/preview?financial_year=${encodeURIComponent(yeFy)}`, { method: "GET" });
  lastYePreview = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { ye_preview: { ok: result.ok, fy: yeFy } });
}

export async function postYearEndClose() {
  if (!lastYePreview || lastYePreview.ok === false || !lastYePreview.can_post) {
    setLoginStatus("warn", "Preview first", "Load a year-end preview that is ready to close.");
    return;
  }
  const result = await apiRequest("mitrabooks", "/api/v1/business/year-end/close", {
    method: "POST",
    headers: { "X-Idempotency-Key": `year-end-${yeFy}` },
    body: JSON.stringify({ financial_year: yeFy }),
  });
  if (result.ok) {
    setLoginStatus("ok", "Year closed", `FY ${yeFy} closed — journal entry #${result.payload?.journal_entry_id}, net result ${formatCurrency(Number(result.payload?.net_profit || 0))}.`);
    await previewYearEnd();
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can post the year-end close.");
  } else {
    setLoginStatus("danger", "Close failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { ye_close: { ok: result.ok, status: result.status } });
}

export function renderOpeningBalancesSection() {
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const presetVal = lastObPreview?.preset || "";
  const displayMap = presetVal === "custom" ? "block" : "none";
  const controls = `
    <div class="report-date-controls" style="flex-wrap: wrap; gap: 10px;">
      <label>Opening date <input type="date" data-ob-asof value="${escapeHtml(lastObPreview?.as_of || "")}" placeholder="FY start"></label>
      <label>Balances CSV <input type="file" accept=".csv,text/csv" data-ob-file></label>
      <label>Format preset
        <select data-ob-preset>
          <option value="" ${presetVal === "" ? "selected" : ""}>Standard Template</option>
          <option value="tally" ${presetVal === "tally" ? "selected" : ""}>Tally Export</option>
          <option value="zoho" ${presetVal === "zoho" ? "selected" : ""}>Zoho Books Export</option>
          <option value="quickbooks" ${presetVal === "quickbooks" ? "selected" : ""}>QuickBooks Export</option>
          <option value="custom" ${presetVal === "custom" ? "selected" : ""}>Custom Mapping</option>
        </select>
      </label>
      <button class="secondary" type="button" data-business-action="ob-preview">Preview</button>
      <button class="secondary" type="button" data-business-action="ob-export">Export posted</button>
      <button class="secondary" type="button" data-business-action="ob-template">Download template</button>
    </div>
    <div id="ob-custom-mapping-fields" style="display:${displayMap}; margin-top:8px; padding:10px; border:1px solid var(--line,#ddd); border-radius:4px; background:rgba(255,255,255,0.05);">
      <p style="margin:0 0 8px 0; font-weight:bold;">Custom Column Header Names in CSV:</p>
      <div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap:10px;">
        <label>Account Code <input type="text" data-ob-map-code value="${escapeHtml(lastObPreview?.header_mapping?.account_code || "")}" placeholder="e.g. Code"></label>
        <label>Account Name <input type="text" data-ob-map-name value="${escapeHtml(lastObPreview?.header_mapping?.account_name || "")}" placeholder="e.g. Name"></label>
        <label>Debit Column <input type="text" data-ob-map-debit value="${escapeHtml(lastObPreview?.header_mapping?.debit || "")}" placeholder="e.g. Debit"></label>
        <label>Credit Column <input type="text" data-ob-map-credit value="${escapeHtml(lastObPreview?.header_mapping?.credit || "")}" placeholder="e.g. Credit"></label>
        <label>Single Balance <input type="text" data-ob-map-balance value="${escapeHtml(lastObPreview?.header_mapping?.balance || "")}" placeholder="e.g. Balance"></label>
        <label>Party Column <input type="text" data-ob-map-party value="${escapeHtml(lastObPreview?.header_mapping?.party || "")}" placeholder="e.g. Contact"></label>
      </div>
    </div>
    <p class="muted">Upload account-wise opening balances (party-wise for Sundry Debtors/Creditors). Nothing posts until you confirm the preview. Leave the date empty for the financial-year start.</p>`;
  const r = lastObPreview;
  if (!r) return `${controls}`;
  if (r.ok === false) return `${controls}${reportUnavailablePanel("Opening balances", r)}`;

  const errorRows = (r.errors || []).map((e) => `
    <tr><td>${escapeHtml(String(e.row_number || ""))}</td><td>${escapeHtml(e.account || "")}</td><td>${escapeHtml((e.problems || []).join("; "))}</td></tr>`).join("");
  const lineRows = (r.lines || []).map((l) => `
    <tr>
      <td>${escapeHtml(`${l.account_code} - ${l.account_name}`)}</td>
      <td>${escapeHtml(l.party_name || "")}</td>
      <td class="amount">${Number(l.debit || 0) ? num(l.debit) : ""}</td>
      <td class="amount">${Number(l.credit || 0) ? num(l.credit) : ""}</td>
    </tr>`).join("");
  const bal = r.balancing_line;
  const existing = r.existing_opening_entries || [];

  return `
    ${controls}
    <div class="preview-heading compact">
      <div><p>${escapeHtml(String(r.line_count))} line(s) resolved as of ${escapeHtml(r.as_of)} · debit ${num(r.total_debit)} · credit ${num(r.total_credit)}.</p></div>
      <span class="pill ${r.can_post ? "ok" : "warn"}">${r.can_post ? "ready to post" : `${escapeHtml(String(r.error_count))} error(s)`}</span>
    </div>
    ${errorRows ? `
    <div class="table-preview compact-table">
      <h4>Fix these rows and re-upload</h4>
      <table><thead><tr><th>CSV row</th><th>Account</th><th>Problem</th></tr></thead><tbody>${errorRows}</tbody></table>
    </div>` : ""}
    <div class="table-preview compact-table">
      <h4>Opening journal preview</h4>
      <table>
        <thead><tr><th>Account</th><th>Party</th><th class="amount">Debit</th><th class="amount">Credit</th></tr></thead>
        <tbody>
          ${lineRows}
          ${bal ? `<tr><td><em>${escapeHtml(`${bal.account_code} - ${bal.account_name}`)} (balancing)</em></td><td></td><td class="amount">${Number(bal.debit || 0) ? num(bal.debit) : ""}</td><td class="amount">${Number(bal.credit || 0) ? num(bal.credit) : ""}</td></tr>` : ""}
        </tbody>
      </table>
    </div>
    ${existing.length ? `<p class="muted">⚠ Opening journal already posted: entry #${escapeHtml(String(existing[0].journal_entry_id))} dated ${escapeHtml(existing[0].entry_date)}. Reverse it first, or tick the override.
      <label style="display:inline-flex;gap:4px;align-items:center;margin-left:8px;"><input type="checkbox" data-ob-allow-duplicate> Post anyway</label></p>` : ""}
    ${r.can_post && isBusinessAdmin() ? `
    <div class="report-date-controls">
      <button class="primary" type="button" data-business-action="ob-post">Post opening balances</button>
    </div>` : (r.can_post ? `<p class="muted">Only a tenant admin can post opening balances.</p>` : "")}
    ${(r.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}
  `;
}

export function renderBulkImportVouchersSection() {
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const controls = `
    <div class="report-date-controls">
      <label>Vouchers CSV <input type="file" accept=".csv,text/csv" data-vi-file></label>
      <button class="secondary" type="button" data-business-action="vi-preview">Preview Import</button>
      <button class="secondary" type="button" data-business-action="vi-template">Download template</button>
    </div>
    <p class="muted">Bulk upload historical transactions/vouchers. Supports single-row double entry (debit_account, credit_account, amount) or multi-row ledger lines grouped by voucher_number.</p>`;

  const r = lastViPreview;
  if (!r) return controls;
  if (r.ok === false) return `${controls}${reportUnavailablePanel("Bulk voucher import", r)}`;

  const errorRows = (r.errors || []).map((e) => `
    <tr><td>${escapeHtml(String(e.row_number || ""))}</td><td>${escapeHtml(e.voucher_number || "")}</td><td>${escapeHtml((e.problems || []).join("; "))}</td></tr>`).join("");

  let previewContent = "";
  if (r.format_type === "double_entry") {
    const lines = (r.vouchers || []).map((v) => `
      <tr>
        <td>${escapeHtml(v.date)}</td>
        <td>${escapeHtml(v.voucher_type)}</td>
        <td>${escapeHtml(v.voucher_number)}</td>
        <td>${escapeHtml(v.debit_account_code)}</td>
        <td>${escapeHtml(v.credit_account_code)}</td>
        <td class="amount">${num(v.amount)}</td>
        <td>${escapeHtml(v.description)}</td>
        <td>${escapeHtml(v.party_name || "")}</td>
      </tr>`).join("");
    previewContent = `
      <div class="table-preview compact-table">
        <h4>Double-Entry Vouchers Preview</h4>
        <table>
          <thead>
            <tr><th>Date</th><th>Type</th><th>Voucher No</th><th>Debit Account</th><th>Credit Account</th><th class="amount">Amount</th><th>Description</th><th>Party</th></tr>
          </thead>
          <tbody>${lines}</tbody>
        </table>
      </div>`;
  } else {
    const blocks = (r.vouchers || []).map((v) => {
      const linesHtml = (v.lines || []).map((l) => `
        <tr>
          <td>${escapeHtml(`${l.account_code} - ${l.account_name}`)}</td>
          <td>${escapeHtml(l.party_name || "")}</td>
          <td class="amount">${Number(l.debit || 0) ? num(l.debit) : ""}</td>
          <td class="amount">${Number(l.credit || 0) ? num(l.credit) : ""}</td>
        </tr>`).join("");
      return `
        <div style="margin-bottom:12px; padding:10px; border:1px solid var(--line,#ddd); border-radius:4px; background:rgba(255,255,255,0.02);">
          <p style="margin:0 0 6px 0;"><strong>Voucher ${escapeHtml(v.voucher_number)}</strong> (${escapeHtml(v.voucher_type)}) · Date: ${escapeHtml(v.date)} · Amount: ${num(v.amount)} · Description: <em>${escapeHtml(v.description)}</em></p>
          <table>
            <thead><tr><th>Account</th><th>Party</th><th class="amount">Debit</th><th class="amount">Credit</th></tr></thead>
            <tbody>${linesHtml}</tbody>
          </table>
        </div>`;
    }).join("");
    previewContent = `
      <div class="table-preview compact-table">
        <h4>Ledger-Lines Vouchers Preview</h4>
        ${blocks}
      </div>`;
  }

  return `
    ${controls}
    <div class="preview-heading compact">
      <div><p>Parsed ${escapeHtml(String(r.voucher_count))} voucher(s) successfully · Format: ${escapeHtml(r.format_type)}</p></div>
      <span class="pill ${r.can_import ? "ok" : "warn"}">${r.can_import ? "ready to import" : `${escapeHtml(String(r.error_count))} error(s)`}</span>
    </div>
    ${errorRows ? `
    <div class="table-preview compact-table">
      <h4>Fix these rows and re-upload</h4>
      <table><thead><tr><th>CSV row</th><th>Voucher No</th><th>Problem</th></tr></thead><tbody>${errorRows}</tbody></table>
    </div>` : ""}
    ${r.can_import ? previewContent : ""}
    ${r.can_import && isBusinessAdmin() ? `
    <div class="report-date-controls">
      <button class="primary" type="button" data-business-action="vi-post">Import vouchers</button>
    </div>` : (r.can_import ? `<p class="muted">Only a tenant admin can perform bulk voucher imports.</p>` : "")}
  `;
}

export function renderYearEndSection() {
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const fyOpts = recentFinancialYears(4).map((fy) =>
    `<option value="${fy}" ${fy === yeFy ? "selected" : ""}>FY ${fy}</option>`).join("");
  const controls = `
    <div class="report-date-controls">
      <label>Financial year <select data-ye-fy>${fyOpts}</select></label>
      <button class="secondary" type="button" data-business-action="ye-preview">Preview close</button>
    </div>
    <p class="muted">Closing zeroes the year's income and expense accounts into Retained Earnings on 31 March. Post all adjustments (depreciation, provisions) first.</p>`;
  const r = lastYePreview;
  if (!r) return controls;
  if (r.ok === false) return `${controls}${reportUnavailablePanel("Year-end close", r)}`;

  const lineRows = (r.closing_lines || []).map((l) => `
    <tr>
      <td>${escapeHtml(`${l.account_code} - ${l.account_name}`)}</td>
      <td>${escapeHtml(l.account_type || "")}</td>
      <td class="amount">${Number(l.debit || 0) ? num(l.debit) : ""}</td>
      <td class="amount">${Number(l.credit || 0) ? num(l.credit) : ""}</td>
    </tr>`).join("");
  const re = r.retained_earnings || {};
  const closed = (r.already_closed || []).length > 0;
  const profit = Number(r.net_profit || 0) >= 0;

  return `
    ${controls}
    <div class="preview-heading compact">
      <div><p>FY ${escapeHtml(r.financial_year)} (${escapeHtml(r.from_date)} → ${escapeHtml(r.to_date)}): income ${num(r.income_total)} − expenses ${num(r.expense_total)} = <strong>${profit ? "profit" : "loss"} ${num(r.net_profit)}</strong>.</p></div>
      <span class="pill ${closed ? "warn" : (r.can_post ? "ok" : "")}">${closed ? "already closed" : (r.can_post ? "ready to close" : "no activity")}</span>
    </div>
    ${closed ? `<p class="muted">⚠ FY ${escapeHtml(r.financial_year)} was closed by journal entry #${escapeHtml(String(r.already_closed[0].journal_entry_id))}. Reverse that entry to reopen the year.</p>` : ""}
    <div class="table-preview compact-table">
      <h4>Closing journal preview (31 March)</h4>
      <table>
        <thead><tr><th>Account</th><th>Type</th><th class="amount">Debit</th><th class="amount">Credit</th></tr></thead>
        <tbody>
          ${lineRows || `<tr><td colspan="4" class="muted">No income or expense activity this year.</td></tr>`}
          ${(Number(re.debit || 0) || Number(re.credit || 0)) ? `<tr><td>&lt;em&gt;${escapeHtml(`${re.account_code} - ${re.account_name}`)}&lt;/em&gt;</td><td>equity</td><td class="amount">${Number(re.debit || 0) ? num(re.debit) : ""}</td><td class="amount">${Number(re.credit || 0) ? num(re.credit) : ""}</td></tr>` : ""}
        </tbody>
      </table>
    </div>
    ${r.can_post && isBusinessAdmin() ? `
    <div class="report-date-controls">
      <button class="primary" type="button" data-business-action="ye-post">Post year-end close</button>
    </div>` : (r.can_post ? `<p class="muted">Only a tenant admin can post the year-end close.</p>` : "")}
    ${(r.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}
  `;
}

export function renderOpeningYearEndPanel() {
  return `
    <div class="table-preview compact-table"><h4>Opening balances (CSV import)</h4></div>
    ${renderOpeningBalancesSection()}
    <hr style="margin:18px 0;border:none;border-top:1px solid var(--line,#ddd);">
    <div class="table-preview compact-table"><h4>Bulk Voucher Import</h4></div>
    ${renderBulkImportVouchersSection()}
    <hr style="margin:18px 0;border:none;border-top:1px solid var(--line,#ddd);">
    <div class="table-preview compact-table"><h4>Year-end close</h4></div>
    ${renderYearEndSection()}
  `;
}
