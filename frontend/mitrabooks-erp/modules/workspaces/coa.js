// ====================================================================
// SECTION: CHART OF ACCOUNTS (COA) WORKSPACE
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initCoa(...).
// ====================================================================

import { apiRequest } from "../../../shared/api-client.js";

export let coaTypeFilter = "";

export const COA_TYPE_META = {
  asset:     { label: "Asset",     pillClass: "pill ok" },
  liability: { label: "Liability", pillClass: "pill danger" },
  equity:    { label: "Equity",    pillClass: "pill neutral" },
  income:    { label: "Income",    pillClass: "pill ok" },
  expense:   { label: "Expense",   pillClass: "pill warn" },
};
export const COA_CLASS_LABELS = {
  personal: "Personal", real: "Real", nominal: "Nominal",
};

/** @type {Record<string, Function> | null} */
let deps = null;

export function initCoa(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initCoa() must be called before using COA helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function getLastBusinessAccounts() { return requireDeps().getLastBusinessAccounts(); }
function loadBusinessAccounts() { return requireDeps().loadBusinessAccounts(); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function renderBusinessWorkspace() { return requireDeps().renderBusinessWorkspace(); }

export function setCoaTypeFilter(value) {
  coaTypeFilter = String(value || "");
}

export function coaTypePill(type) {
  const m = COA_TYPE_META[type] || { label: (type || "—"), pillClass: "pill" };
  return `<span class="${m.pillClass}">${m.label}</span>`;
}

export function renderBusinessCoaWorkspace() {
  const accounts = Array.isArray(getLastBusinessAccounts()) ? getLastBusinessAccounts() : [];
  const filtered = coaTypeFilter ? accounts.filter((a) => a.type === coaTypeFilter) : accounts;

  const typeOptions = Object.entries(COA_TYPE_META)
    .map(([v, m]) => `<option value="${v}">${m.label}</option>`).join("");
  const classOptions = Object.entries(COA_CLASS_LABELS)
    .map(([v, l]) => `<option value="${v}">${l}</option>`).join("");
  const filterOptions = Object.entries(COA_TYPE_META)
    .map(([v, m]) => `<option value="${v}" ${coaTypeFilter === v ? "selected" : ""}>${m.label}</option>`).join("");

  const rows = filtered.length === 0
    ? `<tr><td colspan="6" class="empty-state-cell" style="text-align:center;padding:1.5rem">No accounts match the selected filter.</td></tr>`
    : filtered.map((a) => {
        const isSystem = a.is_cash_bank || a.is_receivable || a.is_payable;
        const systemBadge = isSystem ? `<span class="pill neutral" style="font-size:.72rem">System</span>` : "";
        return `
          <tr data-coa-code="${escapeHtml(a.code || "")}">
            <td class="mono-code">${escapeHtml(a.code || "—")}</td>
            <td class="coa-name-cell">
              <strong class="coa-name-display">${escapeHtml(a.name)}</strong>
              <input class="coa-name-input" type="text" value="${escapeHtml(a.name)}" style="display:none;width:100%" maxlength="200" />
            </td>
            <td>${coaTypePill(a.type)}</td>
            <td>${systemBadge}</td>
            <td><span class="pill ok" style="font-size:.72rem">Active</span></td>
            <td style="text-align:right;white-space:nowrap">
              <button class="secondary small" type="button" data-coa-action="edit-name" title="Edit name">&#9998;</button>
              <button class="secondary small" type="button" data-coa-action="save-name" style="display:none" title="Save">&#10003;</button>
              <button class="secondary small" type="button" data-coa-action="cancel-name" style="display:none" title="Cancel">&#10005;</button>
            </td>
          </tr>`;
      }).join("");

  return `
    <div class="verification-panel erp-workspace-panel" id="coa-workspace">
      <div class="preview-heading compact">
        <div>
          <h4>Chart of Accounts</h4>
          <p>${accounts.length} account${accounts.length !== 1 ? "s" : ""} in the ledger — account codes are permanent, only names can be edited.</p>
        </div>
        <button class="secondary" type="button" data-coa-action="toggle-add-form">+ Add Account</button>
      </div>

      <div id="coa-add-form" style="display:none" class="erp-form-inline">
        <h5 style="margin:0 0 .75rem">New Account</h5>
        <div style="display:grid;grid-template-columns:1fr 2fr 1fr 1fr;gap:.5rem .75rem;align-items:end">
          <label class="field-label">Code (optional)<input id="coa-new-code" type="text" maxlength="30" placeholder="e.g. 53099" /></label>
          <label class="field-label">Account Name *<input id="coa-new-name" type="text" maxlength="200" placeholder="e.g. Petty Cash" required /></label>
          <label class="field-label">Type *<select id="coa-new-type"><option value="">Select…</option>${typeOptions}</select></label>
          <label class="field-label">Classification *<select id="coa-new-class"><option value="">Select…</option>${classOptions}</select></label>
        </div>
        <div style="display:flex;gap:.5rem;margin-top:.75rem;align-items:center">
          <button class="primary small" type="button" data-coa-action="submit-add">Create Account</button>
          <button class="secondary small" type="button" data-coa-action="toggle-add-form">Cancel</button>
          <span id="coa-add-msg" style="font-size:.8rem;margin-left:.5rem"></span>
        </div>
      </div>

      <div style="display:flex;align-items:center;gap:1rem;margin-bottom:.75rem;flex-wrap:wrap">
        <label class="field-label" style="margin:0;display:flex;align-items:center;gap:.5rem;flex-direction:row">
          <span style="white-space:nowrap;font-size:.82rem">Filter by Type</span>
          <select id="coa-type-filter" style="min-width:140px">
            <option value="" ${coaTypeFilter === "" ? "selected" : ""}>All Types</option>
            ${filterOptions}
          </select>
        </label>
        <span class="pill neutral" style="font-size:.75rem">${filtered.length} of ${accounts.length} account${accounts.length !== 1 ? "s" : ""}</span>
        ${coaTypeFilter ? `<button class="secondary small" type="button" data-coa-action="clear-filter">Clear filter</button>` : ""}
        <div id="coa-msg" style="font-size:.82rem;margin-left:auto"></div>
      </div>

      <div class="table-preview compact-table erp-table">
        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Account Name</th>
              <th>Type</th>
              <th>System</th>
              <th>Status</th>
              <th style="text-align:right">Actions</th>
            </tr>
          </thead>
          <tbody id="coa-tbody">
            ${rows}
          </tbody>
        </table>
      </div>
    </div>`;
}

export function coaShowMsg(el, text, ok) {
  if (!el) return;
  el.textContent = text;
  el.style.color = ok ? "var(--color-success, green)" : "var(--color-danger, red)";
  if (ok) setTimeout(() => { el.textContent = ""; }, 3000);
}

export async function coaHandleAddSubmit() {
  const code = document.getElementById("coa-new-code")?.value.trim() || null;
  const name = document.getElementById("coa-new-name")?.value.trim() || "";
  const type = document.getElementById("coa-new-type")?.value;
  const classification = document.getElementById("coa-new-class")?.value;
  const msg = document.getElementById("coa-add-msg");

  if (!name || !type || !classification) {
    coaShowMsg(msg, "Name, Type and Classification are required.", false);
    return;
  }

  const body = { name, type, classification };
  if (code) body.code = code;

  const result = await apiRequest("mitrabooks", "/api/v1/accounting/accounts", {
    method: "POST",
    body: JSON.stringify(body),
  });

  if (!result.ok) {
    coaShowMsg(msg, statusDetailText(result.payload?.detail) || `Error creating account.`, false);
    return;
  }
  coaShowMsg(msg, "Account created.", true);
  ["coa-new-code", "coa-new-name"].forEach((id) => { const el = document.getElementById(id); if (el) el.value = ""; });
  ["coa-new-type", "coa-new-class"].forEach((id) => { const el = document.getElementById(id); if (el) el.value = ""; });
  await loadBusinessAccounts();
  getDashboardPreview().innerHTML = renderBusinessWorkspace();
}

export async function coaHandleSaveName(row) {
  const code = row.dataset.coaCode;
  const input = row.querySelector(".coa-name-input");
  const name = input?.value.trim() || "";
  const msg = document.getElementById("coa-msg");

  if (!name || name.length < 2) {
    coaShowMsg(msg, "Name must be at least 2 characters.", false);
    return;
  }

  const result = await apiRequest("mitrabooks", `/api/v1/accounting/accounts/${encodeURIComponent(code)}`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });

  if (!result.ok) {
    coaShowMsg(msg, statusDetailText(result.payload?.detail) || `Error updating account.`, false);
    return;
  }
  coaShowMsg(msg, `"${escapeHtml(name)}" saved.`, true);
  await loadBusinessAccounts();
  getDashboardPreview().innerHTML = renderBusinessWorkspace();
}

export function coaEnterEditMode(row) {
  row.querySelector(".coa-name-display").style.display = "none";
  row.querySelector(".coa-name-input").style.display = "";
  row.querySelector("[data-coa-action='edit-name']").style.display = "none";
  row.querySelector("[data-coa-action='save-name']").style.display = "";
  row.querySelector("[data-coa-action='cancel-name']").style.display = "";
  row.querySelector(".coa-name-input").focus();
}

export function coaExitEditMode(row) {
  const original = row.querySelector(".coa-name-display").textContent;
  row.querySelector(".coa-name-input").value = original;
  row.querySelector(".coa-name-display").style.display = "";
  row.querySelector(".coa-name-input").style.display = "none";
  row.querySelector("[data-coa-action='edit-name']").style.display = "";
  row.querySelector("[data-coa-action='save-name']").style.display = "none";
  row.querySelector("[data-coa-action='cancel-name']").style.display = "none";
}

