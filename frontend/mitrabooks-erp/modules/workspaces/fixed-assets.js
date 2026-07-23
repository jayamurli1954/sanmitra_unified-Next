// ====================================================================
// SECTION: FIXED ASSETS + DEPRECIATION
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initFixedAssets(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastFixedAssets = null;
export let lastDepPreview = null;
export let depFy = "";
export let faFormOpen = false;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initFixedAssets(injected) {
  deps = injected;
  if (!depFy) {
    depFy = injected.currentFinancialYear();
  }
}

/** Used by app.js event-handler deps setters (imported binding is read-only). */
export function setFaFormOpen(value) {
  faFormOpen = !!value;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initFixedAssets() must be called before using fixed-asset helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function todayIsoDate() { return requireDeps().todayIsoDate(); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function reportUnavailablePanel(title, payload) { return requireDeps().reportUnavailablePanel(title, payload); }
function rerenderBusinessReportsIfActive() { return requireDeps().rerenderBusinessReportsIfActive(); }
function businessAccountsForSelection() { return requireDeps().businessAccountsForSelection(); }
function bankAccountOptions() { return requireDeps().bankAccountOptions(); }
function isBusinessAdmin() { return requireDeps().isBusinessAdmin(); }
function recentFinancialYears(count) { return requireDeps().recentFinancialYears(count); }
function getApiOutput() { return requireDeps().getApiOutput(); }

// SECTION: FIXED ASSETS + DEPRECIATION
// API   : GET/POST /api/v1/business/fixed-assets  POST .../{asset_id}/dispose  POST /api/v1/business/depreciation/run
// NOTE  : loadFixedAssets, createFixedAssetFromForm, renderFixedAssetsPanel
// ══════════════════════════════════════════════════════════════════════

export function fixedAssetAccountOptions() {
  // Fixed-asset accounts live in the 16xxx subclass (16099 is the contra).
  return businessAccountsForSelection().filter((acc) =>
    String(acc.code || "").startsWith("16") && String(acc.code) !== "16099");
}

export async function loadFixedAssets() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/fixed-assets", { method: "GET" });
  lastFixedAssets = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { fixed_assets: { ok: result.ok, count: result.payload?.count || 0 } });
}

export async function createFixedAssetFromForm() {
  const form = document.querySelector("[data-fa-form]");
  if (!form) return;
  const val = (sel) => form.querySelector(sel)?.value ?? "";
  const method = val("select[name='fa_method']") || "slm";
  const body = {
    asset_name: val("input[name='fa_name']").trim(),
    asset_account_code: val("select[name='fa_account']") || "16001",
    purchase_date: val("input[name='fa_date']"),
    cost: val("input[name='fa_cost']"),
    salvage_value: val("input[name='fa_salvage']") || "0",
    method,
    useful_life_years: method === "slm" ? val("input[name='fa_life']") : null,
    depreciation_rate: method === "wdv" ? val("input[name='fa_rate']") : null,
    opening_accumulated_depreciation: val("input[name='fa_opening_acc']") || "0",
    notes: val("input[name='fa_notes']").trim() || null,
  };
  if (!body.asset_name || !body.purchase_date || !Number(body.cost)) {
    setLoginStatus("warn", "Fill the asset details", "Name, purchase date and cost are required.");
    return;
  }
  const result = await apiRequest("mitrabooks", "/api/v1/business/fixed-assets", {
    method: "POST", body: JSON.stringify(body),
  });
  if (result.ok) {
    setLoginStatus("ok", "Asset registered", `${result.payload?.asset_name} added to the register.`);
    faFormOpen = false;
    await loadFixedAssets();
  } else {
    setLoginStatus("danger", "Could not register", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { fixed_asset_create: { ok: result.ok, status: result.status } });
}

export async function previewDepreciation() {
  const fySel = document.querySelector("[data-dep-fy]");
  depFy = fySel?.value || depFy;
  const result = await apiRequest("mitrabooks", `/api/v1/business/depreciation/preview?financial_year=${encodeURIComponent(depFy)}`, { method: "GET" });
  lastDepPreview = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { depreciation_preview: { ok: result.ok, fy: depFy } });
}

export async function postDepreciationRun() {
  if (!lastDepPreview || lastDepPreview.ok === false || !lastDepPreview.can_post) {
    setLoginStatus("warn", "Preview first", "Load a depreciation preview that is ready to post.");
    return;
  }
  const result = await apiRequest("mitrabooks", "/api/v1/business/depreciation/run", {
    method: "POST",
    headers: { "X-Idempotency-Key": `depreciation-${depFy}` },
    body: JSON.stringify({ financial_year: depFy }),
  });
  if (result.ok) {
    setLoginStatus("ok", "Depreciation posted", `FY ${depFy}: ${formatCurrency(Number(result.payload?.total_depreciation || 0))} — journal entry #${result.payload?.journal_entry_id}.`);
    await previewDepreciation();
    await loadFixedAssets();
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can post the depreciation run.");
  } else {
    setLoginStatus("danger", "Run failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { depreciation_run: { ok: result.ok, status: result.status } });
}

export async function disposeFixedAsset(assetId, button) {
  const row = button?.closest("tr");
  const disposalDate = row?.querySelector("[data-fa-dispose-date]")?.value || todayIsoDate();
  const saleValue = row?.querySelector("[data-fa-dispose-sale]")?.value || "0";
  const bankCode = row?.querySelector("[data-fa-dispose-bank]")?.value || "11010";
  if (!assetId || !disposalDate) {
    setLoginStatus("warn", "Disposal details missing", "Choose an asset and disposal date.");
    return;
  }
  const result = await apiRequest("mitrabooks", `/api/v1/business/fixed-assets/${encodeURIComponent(assetId)}/dispose`, {
    method: "POST",
    headers: { "X-Idempotency-Key": `fixed-asset-disposal-${assetId}` },
    body: JSON.stringify({
      disposal_date: disposalDate,
      sale_value: saleValue || "0",
      cash_bank_account_code: Number(saleValue || 0) > 0 ? bankCode : null,
      reason: "Disposed from MitraBooks ERP shell",
    }),
  });
  if (result.ok) {
    const gainLoss = Number(result.payload?.gain || 0) > 0
      ? ` gain ${formatCurrency(Number(result.payload.gain || 0))}`
      : (Number(result.payload?.loss || 0) > 0 ? ` loss ${formatCurrency(Number(result.payload.loss || 0))}` : "");
    setLoginStatus("ok", "Asset disposed", `Journal entry #${result.payload?.journal_entry_id}${gainLoss}.`);
    await loadFixedAssets();
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can dispose fixed assets.");
  } else {
    setLoginStatus("danger", "Disposal failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { fixed_asset_disposal: { ok: result.ok, status: result.status, asset_id: assetId } });
}

export function renderFixedAssetForm() {
  const accountOpts = fixedAssetAccountOptions().map((a) =>
    `<option value="${escapeHtml(a.code)}">${escapeHtml(`${a.code} - ${a.name}`)}</option>`).join("")
    || `<option value="16001">16001 - Furniture and Fixtures</option>`;
  return `
    <div class="invoice-form-grid" data-fa-form>
      <label>Asset name <input type="text" name="fa_name" maxlength="160" placeholder="e.g. Delivery van"></label>
      <label>Asset account <select name="fa_account">${accountOpts}</select></label>
      <label>Purchase date <input type="date" name="fa_date" value="${escapeHtml(todayIsoDate())}"></label>
      <label>Cost <input type="number" name="fa_cost" min="0" step="0.01" placeholder="0.00"></label>
      <label>Salvage value <input type="number" name="fa_salvage" min="0" step="0.01" value="0"></label>
      <label>Method <select name="fa_method">
        <option value="slm">SLM (straight line)</option>
        <option value="wdv">WDV (written down value)</option>
      </select></label>
      <label>Useful life (years, SLM) <input type="number" name="fa_life" min="0" step="1" placeholder="e.g. 5"></label>
      <label>Rate % (WDV) <input type="number" name="fa_rate" min="0" max="100" step="0.01" placeholder="e.g. 15"></label>
      <label>Already depreciated (migrated assets) <input type="number" name="fa_opening_acc" min="0" step="0.01" value="0"></label>
      <label>Notes <input type="text" name="fa_notes" maxlength="200" placeholder="Optional"></label>
    </div>
    <div class="report-date-controls">
      <button class="primary" type="button" data-business-action="fa-create">Register asset</button>
      <button class="secondary" type="button" data-business-action="fa-toggle-form">Cancel</button>
    </div>
    <p class="muted">Registering only records the asset — book its purchase via a bill/voucher to the chosen 16xxx account as usual.</p>`;
}

export function renderFixedAssetsPanel() {
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const r = lastFixedAssets;
  let registerBody;
  if (!r) {
    registerBody = `<p class="muted">Loading the asset register...</p>`;
  } else if (r.ok === false) {
    registerBody = reportUnavailablePanel("Fixed Assets", r);
  } else {
    const bankOpts = bankAccountOptions().map((a) =>
      `<option value="${escapeHtml(a.code)}">${escapeHtml(`${a.code} - ${a.name}`)}</option>`).join("")
      || `<option value="11010">11010 - Bank Account</option>`;
    const rows = (r.items || []).map((a) => `
      <tr>
        <td>${escapeHtml(a.asset_name || "")}${a.status !== "active" ? ` <span class="pill warn">${escapeHtml(a.status)}</span>` : ""}</td>
        <td>${escapeHtml(a.asset_account_code || "")}</td>
        <td>${escapeHtml(a.purchase_date || "")}</td>
        <td>${escapeHtml(String(a.method || "").toUpperCase())}${a.useful_life_years ? ` ${escapeHtml(a.useful_life_years)}y` : ""}${a.depreciation_rate ? ` ${escapeHtml(a.depreciation_rate)}%` : ""}</td>
        <td class="amount">${num(a.cost)}</td>
        <td class="amount">${num(a.accumulated_depreciation)}</td>
        <td class="amount">${num(a.book_value)}</td>
        <td>${a.status === "active" && isBusinessAdmin() ? `
          <div class="report-date-controls compact">
            <input type="date" data-fa-dispose-date value="${escapeHtml(todayIsoDate())}" aria-label="Disposal date for ${escapeHtml(a.asset_name || "asset")}">
            <input type="number" data-fa-dispose-sale min="0" step="0.01" placeholder="Sale value" aria-label="Sale value for ${escapeHtml(a.asset_name || "asset")}">
            <select data-fa-dispose-bank aria-label="Bank account for asset sale">${bankOpts}</select>
            <button class="secondary" type="button" data-business-action="fa-dispose" data-asset-id="${escapeHtml(a.asset_id || "")}">Dispose</button>
          </div>` : (a.status === "disposed" ? `Journal #${escapeHtml(String(a.disposal_journal_entry_id || ""))}${a.disposal_gain && Number(a.disposal_gain) > 0 ? ` · Gain ${num(a.disposal_gain)}` : ""}${a.disposal_loss && Number(a.disposal_loss) > 0 ? ` · Loss ${num(a.disposal_loss)}` : ""}` : "")}</td>
      </tr>`).join("");
    registerBody = `
      <div class="table-preview compact-table">
        <table>
          <thead><tr><th>Asset</th><th>Account</th><th>Purchased</th><th>Method</th><th class="amount">Cost</th><th class="amount">Acc. depreciation</th><th class="amount">Book value</th><th>Disposal</th></tr></thead>
          <tbody>${rows || `<tr><td colspan="8" class="muted">No assets registered yet.</td></tr>`}</tbody>
          ${rows ? `<tfoot><tr><th colspan="4">Total</th><td class="amount">${num(r.total_cost)}</td><td></td><td class="amount"><strong>${num(r.total_book_value)}</strong></td><td></td></tr></tfoot>` : ""}
        </table>
      </div>`;
  }

  const fyOpts = recentFinancialYears(4).map((fy) =>
    `<option value="${fy}" ${fy === depFy ? "selected" : ""}>FY ${fy}</option>`).join("");
  const d = lastDepPreview;
  let depBody = "";
  if (d && d.ok === false) {
    depBody = reportUnavailablePanel("Depreciation", d);
  } else if (d) {
    const rows = (d.rows || []).map((row) => `
      <tr>
        <td>${escapeHtml(row.asset_name || "")}</td>
        <td>${escapeHtml(String(row.method || "").toUpperCase())}</td>
        <td class="amount">${num(row.opening_book_value)}</td>
        <td class="amount">${num(row.depreciation)}</td>
        <td class="amount">${num(row.closing_book_value)}</td>
      </tr>`).join("");
    depBody = `
      <div class="preview-heading compact">
        <div><p>FY ${escapeHtml(d.financial_year)} charge: <strong>${num(d.total_depreciation)}</strong> across ${escapeHtml(String(d.asset_count))} asset(s).</p></div>
        <span class="pill ${d.already_run ? "warn" : (d.can_post ? "ok" : "")}">${d.already_run ? "already posted" : (d.can_post ? "ready to post" : "nothing to post")}</span>
      </div>
      ${d.already_run ? `<p class="muted">⚠ FY ${escapeHtml(d.financial_year)} depreciation was posted (journal entry #${escapeHtml(String(d.existing_run?.journal_entry_id || ""))}).</p>` : ""}
      <div class="table-preview compact-table">
        <table>
          <thead><tr><th>Asset</th><th>Method</th><th class="amount">Opening book value</th><th class="amount">Depreciation</th><th class="amount">Closing book value</th></tr></thead>
          <tbody>${rows || `<tr><td colspan="5" class="muted">No active assets to depreciate.</td></tr>`}</tbody>
        </table>
      </div>
      ${d.can_post && isBusinessAdmin() ? `
      <div class="report-date-controls">
        <button class="primary" type="button" data-business-action="dep-post">Post depreciation</button>
      </div>` : (d.can_post ? `<p class="muted">Only a tenant admin can post the depreciation run.</p>` : "")}
      ${(d.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}`;
  }

  return `
    <div class="preview-heading compact">
      <div><h4>Fixed-asset register</h4><p>${r && r.ok !== false ? `${escapeHtml(String(r.count || 0))} asset(s) on the books.` : ""}</p></div>
      <button class="secondary" type="button" data-business-action="fa-toggle-form">${faFormOpen ? "Close form" : "+ Register asset"}</button>
    </div>
    ${faFormOpen ? renderFixedAssetForm() : ""}
    ${registerBody}
    <hr style="margin:18px 0;border:none;border-top:1px solid var(--line,#ddd);">
    <div class="table-preview compact-table"><h4>Depreciation run</h4></div>
    <div class="report-date-controls">
      <label>Financial year <select data-dep-fy>${fyOpts}</select></label>
      <button class="secondary" type="button" data-business-action="dep-preview">Preview depreciation</button>
    </div>
    ${depBody}
  `;
}

// ---- Accounting dimensions (cost centres / projects) ----------------------- //

// ══════════════════════════════════════════════════════════════════════
