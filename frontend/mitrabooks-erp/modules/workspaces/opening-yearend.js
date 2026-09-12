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
export let lastLegacyPreview = null;
export let legacyCsvText = "";
export let lastLegacyDecisions = [];

/** @type {Record<string, Function> | null} */
let deps = null;

export function dispatchOpeningYearEndAction(businessAction) {
  const action = String(businessAction || "");
  if (action === "ob-template") downloadObTemplate();
  else if (action === "ob-export") downloadObExport();
  else if (action === "ob-preview") previewOpeningBalances();
  else if (action === "ob-post") postOpeningBalances();
  else if (action === "legacy-coa-template") downloadLegacyCoaTemplate();
  else if (action === "legacy-coa-preview") previewLegacyCoa();
  else if (action === "legacy-coa-confirm") confirmLegacyCoa();
  else if (action === "legacy-coa-decisions") loadLegacyCoaDecisions();
  else if (action === "vi-template") downloadViTemplate();
  else if (action === "vi-preview") previewBulkVouchers();
  else if (action === "vi-post") postBulkVouchers();
  else if (action === "ye-preview") previewYearEnd();
  else if (action === "ye-post") postYearEndClose();
  else return false;
  return true;
}

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

export async function downloadLegacyCoaTemplate() {
  const result = await downloadApiFile(
    "mitrabooks",
    "/api/v1/accounting/coa/legacy-import/template",
    "legacy_coa_mapping_template.csv",
  );
  renderJson(getApiOutput(), { legacy_coa_template: { ok: result.ok } });
}

function defaultClassification(type) {
  if (type === "income" || type === "expense") return "nominal";
  if (type === "asset") return "real";
  return "personal";
}

export async function previewLegacyCoa() {
  const fileInput = document.querySelector("[data-legacy-coa-file]");
  const sourceSelect = document.querySelector("[data-legacy-coa-source]");
  const file = fileInput?.files?.[0];
  if (!file && !legacyCsvText) {
    setLoginStatus("warn", "Choose a file", "Upload unique legacy ledger codes and names (download the template).");
    return;
  }
  if (file) legacyCsvText = await file.text();
  const result = await apiRequest("mitrabooks", "/api/v1/accounting/coa/legacy-import/preview", {
    method: "POST",
    body: JSON.stringify({
      csv: legacyCsvText,
      source_system: sourceSelect?.value || "tally",
    }),
  });
  lastLegacyPreview = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { legacy_coa_preview: { ok: result.ok, status: result.status } });
}

export function collectLegacyCoaDecisions() {
  const preview = lastLegacyPreview;
  if (!preview || preview.ok === false || !Array.isArray(preview.rows)) {
    return [];
  }
  const decisions = [];
  for (const row of preview.rows) {
    const tr = Array.from(document.querySelectorAll("[data-legacy-row]")).find(
      (el) => el.getAttribute("data-legacy-row") === row.source_account_code,
    );
    if (!tr) continue;
    const action = tr.querySelector("[data-legacy-action]")?.value || "";
    if (!action) continue;
    const notes = tr.querySelector("[data-legacy-notes]")?.value?.trim() || "";
    const suggestion = row.suggestion
      ? {
          canonical_account_id: row.suggestion.canonical_account_id,
          canonical_account_name: row.suggestion.canonical_account_name,
          confidence: row.suggestion.confidence,
          reason: row.suggestion.reason,
        }
      : null;
    const base = {
      source_account_code: row.source_account_code,
      source_account_name: row.source_account_name,
      source_account_type: row.source_account_type || null,
      notes: notes || null,
      suggestion,
    };
    if (action === "map_existing") {
      const canonicalId = Number(tr.querySelector("[data-legacy-canonical]")?.value || 0);
      if (!canonicalId) continue;
      decisions.push({ ...base, action: "map_existing", canonical_account_id: canonicalId });
    } else if (action === "create_new") {
      const code = tr.querySelector("[data-legacy-new-code]")?.value?.trim() || "";
      const name = tr.querySelector("[data-legacy-new-name]")?.value?.trim() || row.source_account_name;
      const type = tr.querySelector("[data-legacy-new-type]")?.value || "";
      const classification = tr.querySelector("[data-legacy-new-class]")?.value || defaultClassification(type);
      if (!type || !classification || name.length < 2) continue;
      decisions.push({
        ...base,
        action: "create_new",
        create: { code: code || null, name, type, classification },
      });
    }
  }
  return decisions;
}

export async function confirmLegacyCoa() {
  const sourceSelect = document.querySelector("[data-legacy-coa-source]");
  const decisions = collectLegacyCoaDecisions();
  if (!decisions.length) {
    setLoginStatus("warn", "Select a decision", "Choose Map existing or Create new on each row you want to confirm. Unmatched rows stay on the list until you decide.");
    return;
  }
  const result = await apiRequest("mitrabooks", "/api/v1/accounting/coa/legacy-import/confirm", {
    method: "POST",
    body: JSON.stringify({
      source_system: sourceSelect?.value || lastLegacyPreview?.source_system || "tally",
      decisions,
    }),
  });
  if (result.ok) {
    setLoginStatus(
      "ok",
      "Legacy accounts confirmed",
      `${result.payload?.confirmed_count || 0} decision(s) saved (${result.payload?.mapped_existing_count || 0} mapped, ${result.payload?.created_account_count || 0} created). Each decision is audited.`,
    );
    lastLegacyDecisions = Array.isArray(result.payload?.decisions) ? result.payload.decisions : [];
    await previewLegacyCoa();
    await loadLegacyCoaDecisions();
  } else if (result.status === 403) {
    setLoginStatus("danger", "Not permitted", "Tenant admin or accountant can confirm mapping decisions.");
  } else {
    setLoginStatus("danger", "Confirm failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { legacy_coa_confirm: { ok: result.ok, status: result.status } });
}

export async function loadLegacyCoaDecisions() {
  const sourceSelect = document.querySelector("[data-legacy-coa-source]");
  const source = sourceSelect?.value || lastLegacyPreview?.source_system || "tally";
  const result = await apiRequest(
    "mitrabooks",
    `/api/v1/accounting/coa/legacy-import/decisions?source_system=${encodeURIComponent(source)}`,
    { method: "GET" },
  );
  lastLegacyDecisions = result.ok && Array.isArray(result.payload) ? result.payload : [];
  if (!result.ok) {
    setLoginStatus("warn", "Could not load mapping audit", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { legacy_coa_decisions: { ok: result.ok, count: lastLegacyDecisions.length } });
}

export function toggleLegacyCoaRowFields(selectEl) {
  const tr = selectEl?.closest("tr");
  if (!tr) return;
  const mapBox = tr.querySelector("[data-legacy-map-fields]");
  const createBox = tr.querySelector("[data-legacy-create-fields]");
  const action = selectEl.value;
  if (mapBox) mapBox.style.display = action === "map_existing" ? "block" : "none";
  if (createBox) createBox.style.display = action === "create_new" ? "block" : "none";
}

export function renderLegacyCoaSection() {
  const sourceVal = lastLegacyPreview?.source_system || "tally";
  const controls = `
    <div class="report-date-controls" style="flex-wrap: wrap; gap: 10px;">
      <label>Source
        <select data-legacy-coa-source>
          <option value="tally" ${sourceVal === "tally" ? "selected" : ""}>Tally</option>
          <option value="zoho" ${sourceVal === "zoho" ? "selected" : ""}>Zoho Books</option>
          <option value="csv" ${sourceVal === "csv" ? "selected" : ""}>Other CSV</option>
        </select>
      </label>
      <label>Legacy COA CSV <input type="file" accept=".csv,text/csv" data-legacy-coa-file></label>
      <button class="secondary" type="button" data-business-action="legacy-coa-preview">Match accounts</button>
      <button class="secondary" type="button" data-business-action="legacy-coa-template">Download template</button>
      <button class="secondary" type="button" data-business-action="legacy-coa-decisions">Load audit log</button>
    </div>
    <p class="muted">Upload unique legacy ledger codes and descriptions. MitraBooks suggests matches; you confirm Map to an existing account or Create a new MitraBooks account. Nothing posts until you confirm. Legacy codes stay searchable.</p>`;

  const r = lastLegacyPreview;
  let previewHtml = "";
  if (!r) {
    previewHtml = "";
  } else if (r.ok === false) {
    previewHtml = reportUnavailablePanel("Legacy chart of accounts", r);
  } else {
    const accounts = r.canonical_accounts || [];
    const rows = (r.rows || []).map((row) => {
      const suggestedId = row.mapped_account_id || row.suggestion?.canonical_account_id || "";
      const preselect = row.already_mapped || row.match_status === "suggested" ? "map_existing" : "";
      const pill = row.match_status === "already_mapped"
        ? "ok"
        : (row.match_status === "suggested" ? "ok" : "warn");
      const matchLabel = row.already_mapped
        ? `mapped → ${row.mapped_account_code || ""} ${row.mapped_account_name || ""}`
        : (row.suggestion
          ? `suggested ${row.suggestion.canonical_account_name} (${row.suggestion.reason}, ${row.suggestion.confidence ?? ""})`
          : "no match");
      const defaultClass = defaultClassification(row.source_account_type || "");
      const typeSelect = ["asset", "liability", "equity", "income", "expense"].map((t) =>
        `<option value="${t}" ${row.source_account_type === t ? "selected" : ""}>${t}</option>`
      ).join("");
      const classSelect = ["real", "personal", "nominal"].map((t) =>
        `<option value="${t}" ${defaultClass === t ? "selected" : ""}>${t}</option>`
      ).join("");
      return `
        <tr data-legacy-row="${escapeHtml(row.source_account_code)}">
          <td class="mono-code">${escapeHtml(row.source_account_code)}</td>
          <td>${escapeHtml(row.source_account_name)}</td>
          <td><span class="pill ${pill}">${escapeHtml(matchLabel)}</span></td>
          <td>
            <select data-legacy-action>
              <option value="" ${preselect === "" ? "selected" : ""}>Decide later</option>
              <option value="map_existing" ${preselect === "map_existing" ? "selected" : ""}>Map to existing</option>
              <option value="create_new">Create new MitraBooks account</option>
            </select>
            <div data-legacy-map-fields style="display:${preselect === "map_existing" ? "block" : "none"};margin-top:6px">
              <select data-legacy-canonical>
                <option value="">Select MitraBooks account</option>
                ${accounts.map((a) => `<option value="${escapeHtml(String(a.id))}" ${String(a.id) === String(suggestedId) ? "selected" : ""}>${escapeHtml(`${a.code || "—"} — ${a.name}`)}</option>`).join("")}
              </select>
            </div>
            <div data-legacy-create-fields style="display:none;margin-top:6px">
              <input type="text" data-legacy-new-code maxlength="30" placeholder="MitraBooks code" />
              <input type="text" data-legacy-new-name maxlength="200" value="${escapeHtml(row.source_account_name)}" placeholder="MitraBooks name" />
              <select data-legacy-new-type><option value="">Type</option>${typeSelect}</select>
              <select data-legacy-new-class><option value="">Class</option>${classSelect}</select>
            </div>
            <input type="text" data-legacy-notes maxlength="200" placeholder="Audit note (optional)" style="margin-top:6px;width:100%" />
          </td>
        </tr>`;
    }).join("");
    previewHtml = `
      <div class="preview-heading compact">
        <div><p>${escapeHtml(String(r.row_count))} unique legacy account(s) · ${escapeHtml(String(r.suggested_count))} suggested · ${escapeHtml(String(r.unmatched_count))} unmatched · ${escapeHtml(String(r.already_mapped_count))} already mapped.</p></div>
        <span class="pill ${r.unmatched_count ? "warn" : "ok"}">${r.unmatched_count ? "unmatched rows need a decision" : "all rows have a suggestion or mapping"}</span>
      </div>
      <div class="table-preview compact-table">
        <table>
          <thead><tr><th>Legacy code</th><th>Legacy name</th><th>Match</th><th>Your decision</th></tr></thead>
          <tbody>${rows || `<tr><td colspan="4" class="muted">No rows.</td></tr>`}</tbody>
        </table>
      </div>
      <div class="report-date-controls">
        <button class="primary" type="button" data-business-action="legacy-coa-confirm">Confirm selected decisions</button>
      </div>
      <p class="muted">Tenant admin or accountant can confirm. Suggested rows are pre-selected as Map existing. Confirm is still required. Create uses the same MitraBooks account fields as Chart of Accounts.</p>`;
  }

  const decisionRows = (lastLegacyDecisions || []).map((d) => `
    <tr>
      <td class="mono-code">${escapeHtml(d.source_account_code || "")}</td>
      <td>${escapeHtml(d.source_account_name || "")}</td>
      <td>${escapeHtml(d.action === "created_then_mapped" ? "created then mapped" : "mapped to existing")}</td>
      <td>${escapeHtml(`${d.canonical_account_code || ""} ${d.canonical_account_name || ""}`.trim())}</td>
      <td>${escapeHtml(d.decided_by || "")}</td>
      <td>${escapeHtml(String(d.decided_at || "").slice(0, 19).replace("T", " "))}</td>
    </tr>`).join("");

  return `
    ${controls}
    ${previewHtml}
    ${decisionRows ? `
    <div class="table-preview compact-table">
      <h4>Confirmed mapping audit</h4>
      <table>
        <thead><tr><th>Legacy code</th><th>Legacy name</th><th>Decision</th><th>MitraBooks account</th><th>By</th><th>When</th></tr></thead>
        <tbody>${decisionRows}</tbody>
      </table>
    </div>` : ""}
  `;
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
  if (target.matches("[data-legacy-action]")) {
    toggleLegacyCoaRowFields(target);
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
    <p class="muted">Bulk upload historical transactions/vouchers. Supports single-row double entry (debit_account, credit_account, amount) or multi-row ledger lines grouped by voucher_number. Confirmed legacy account codes from the mapping step above are accepted.</p>`;

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
    <div class="table-preview compact-table"><h4>Legacy chart of accounts (map or create)</h4></div>
    ${renderLegacyCoaSection()}
    <hr style="margin:18px 0;border:none;border-top:1px solid var(--line,#ddd);">
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
