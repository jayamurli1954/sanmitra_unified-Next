// ====================================================================
// SECTION: VOUCHERS — CRUD + list + create dialog
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initVouchers(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastBusinessVouchers = [];
export let lastVoucherApprovalQueue = [];

/** @type {Record<string, Function> | null} */
let deps = null;

export function initVouchers(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initVouchers() must be called before using voucher helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function getBusinessListState() { return requireDeps().getBusinessListState(); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function renderBusinessWorkspace() { return requireDeps().renderBusinessWorkspace(); }
function getApiOutput() { return requireDeps().getApiOutput(); }
function getLastBusinessParties() { return requireDeps().getLastBusinessParties(); }
function getLastBusinessAccounts() { return requireDeps().getLastBusinessAccounts(); }
function getLastDimensions() { return requireDeps().getLastDimensions(); }
function loadBusinessAccounts() { return requireDeps().loadBusinessAccounts(); }
function loadBusinessParties() { return requireDeps().loadBusinessParties(); }
function loadDimensions() { return requireDeps().loadDimensions(); }
function renderAccountSelectorComponent(fieldId) { return requireDeps().renderAccountSelectorComponent(fieldId); }
function dimensionOptions(kind) { return requireDeps().dimensionOptions(kind); }
function addVoucherLine() { return requireDeps().addVoucherLine(); }
function updateVoucherBalance() { return requireDeps().updateVoucherBalance(); }
function clearVoucherForm() { return requireDeps().clearVoucherForm(); }
function loadVoucherPartyOutstanding(partyId, voucherType) { return requireDeps().loadVoucherPartyOutstanding(partyId, voucherType); }
function createBusinessVoucherByType(voucherType, date) { return requireDeps().createBusinessVoucherByType(voucherType, date); }
function getBusinessVoucherCreateForm() { return requireDeps().getBusinessVoucherCreateForm(); }
function getBusinessVoucherCreateDialog() { return requireDeps().getBusinessVoucherCreateDialog(); }

export function setLastBusinessVouchers(value) { lastBusinessVouchers = Array.isArray(value) ? value : []; }
export function setLastVoucherApprovalQueue(value) { lastVoucherApprovalQueue = Array.isArray(value) ? value : []; }
export function clearVoucherListState() {
  lastBusinessVouchers = [];
  lastVoucherApprovalQueue = [];
}

export async function loadBusinessVouchers(filters = {}) {
  const appKey = "mitrabooks";
  const params = new URLSearchParams();
  const state = getBusinessListState().vouchers;
  const merged = {
    offset: state.offset || 0,
    limit: 20,
    voucher_type: state.voucher_type || "",
    status: state.status || "",
    approval_status: state.approval_status || "",
    ...filters,
  };
  params.append("offset", merged.offset);
  params.append("limit", merged.limit);
  if (merged.voucher_type) params.append("voucher_type", merged.voucher_type);
  if (merged.status) params.append("status", merged.status);
  if (merged.approval_status) params.append("approval_status", merged.approval_status);

  const queryString = params.toString();
  const url = `/api/v1/business/vouchers${queryString ? "?" + queryString : ""}`;

  const result = await apiRequest(appKey, url, { method: "GET" });
  if (result.ok) {
    lastBusinessVouchers = Array.isArray(result.payload?.items) ? result.payload.items : Array.isArray(result.payload) ? result.payload : [];
    if (getCurrentExperience() === "mitrabooks" && getActiveBusinessWorkspace() === "vouchers") {
      getDashboardPreview().innerHTML = renderBusinessWorkspace();
    }
  } else {
    lastBusinessVouchers = [];
    setLoginStatus("danger", "Unable to load vouchers", statusDetailText(result.payload?.detail) || `Voucher list request failed with HTTP ${result.status}.`);
    if (getCurrentExperience() === "mitrabooks" && getActiveBusinessWorkspace() === "vouchers") {
      getDashboardPreview().innerHTML = renderBusinessWorkspace();
    }
  }
  renderJson(getApiOutput(), { vouchers: { ok: result.ok, status: result.status, count: lastBusinessVouchers.length, detail: result.payload?.detail || null } });
}


export async function loadVoucherApprovalQueue(includeReviewed = true, options = {}) {
  const appKey = "mitrabooks";
  const surfaceErrors = options?.surfaceErrors === true;
  const params = new URLSearchParams({
    document_type: "voucher",
    include_reviewed: includeReviewed ? "true" : "false",
    limit: "100",
  });
  const result = await apiRequest(appKey, `/api/v1/business/approval-queue?${params.toString()}`, { method: "GET" });

  if (result.ok) {
    const items = Array.isArray(result.payload?.items) ? result.payload.items : [];
    lastVoucherApprovalQueue = items;
    if (getCurrentExperience() === "mitrabooks" && getActiveBusinessWorkspace() === "vouchers") {
      getDashboardPreview().innerHTML = renderBusinessWorkspace();
    }
  } else {
    lastVoucherApprovalQueue = [];
    if (surfaceErrors) {
      setLoginStatus("danger", "Unable to load voucher review queue", statusDetailText(result.payload?.detail) || `Approval queue request failed with HTTP ${result.status}.`);
    }
  }
  renderJson(getApiOutput(), { approval_queue: { ok: result.ok, status: result.status, count: lastVoucherApprovalQueue.length, detail: result.payload?.detail || null } });
}


export async function reviewBusinessVoucher(voucherId, approve, notes, rejectionReason = "") {
  const appKey = "mitrabooks";
  const result = await apiRequest(appKey, `/api/v1/business/vouchers/${encodeURIComponent(voucherId)}/review`, {
    method: "POST",
    body: JSON.stringify({
      approve,
      notes,
      rejection_reason: rejectionReason || null,
      accounting_entity_id: "primary",
    }),
  });

  if (result.ok) {
    setLoginStatus("ok", approve ? "Voucher approved" : "Voucher rejected", approve ? "Voucher review recorded." : "Voucher rejection recorded.");
    await loadBusinessVouchers();
    await loadVoucherApprovalQueue(true, { surfaceErrors: false });
  } else {
    setLoginStatus("danger", approve ? "Voucher approval failed" : "Voucher rejection failed", statusDetailText(result.payload?.detail) || "Try again.");
  }
  renderJson(getApiOutput(), { review_voucher: result });
}


export async function reverseBusinessVoucher(voucherId) {
  const appKey = "mitrabooks";
  const result = await apiRequest(appKey, `/api/v1/business/vouchers/${encodeURIComponent(voucherId)}/reverse`, {
    method: "POST",
    headers: {
      "X-Idempotency-Key": `business-voucher-reversal-${voucherId}`,
    },
    body: JSON.stringify({
      reason: "Reversal",
    }),
  });

  if (result.ok) {
    setLoginStatus("ok", "Voucher reversed", "Reversal entry created.");
    await loadBusinessVouchers();
  } else {
    setLoginStatus("danger", "Reverse voucher failed", result.payload?.detail || "Try again.");
  }
  renderJson(getApiOutput(), { reverse_voucher: result });
}


export function renderVoucherTypeForm(voucherType) {
  const accountSelector = (fieldId) => renderAccountSelectorComponent(fieldId);
  const costCentreOptions = dimensionOptions("cost_centre");
  const projectOptions = dimensionOptions("project");
  const dimensionFields = (costCentreOptions || projectOptions) ? `
        <div class="report-date-controls voucher-dimension-fields">
          ${costCentreOptions ? `<label>Cost centre <select id="business-voucher-cost-centre">${costCentreOptions}</select></label>` : ""}
          ${projectOptions ? `<label>Project <select id="business-voucher-project">${projectOptions}</select></label>` : ""}
        </div>` : "";

  if (voucherType === "payment") {
    return `
      <div class="voucher-type-form">
        <div class="voucher-posting-map" aria-label="Payment voucher posting">
          <div>
            <span>Debit</span>
            <strong>Vendor / party ledger</strong>
          </div>
          <div>
            <span>Credit</span>
            <strong>Bank or cash account</strong>
          </div>
        </div>
        <div class="field">
          <label for="business-voucher-party">Party (Vendor/Customer)</label>
          <select id="business-voucher-party" required>
            <option value="">-- Select Party --</option>
            ${Array.isArray(getLastBusinessParties()) ? getLastBusinessParties().map(p =>
              `<option value="${escapeHtml(p.party_id)}">${escapeHtml(p.party_name)} (${p.party_type})</option>`
            ).join('') : ''}
          </select>
          <div id="business-voucher-outstanding" class="muted voucher-outstanding" data-voucher-type="${voucherType}"></div>
        </div>
        <div class="field">
          <label for="business-voucher-amount">Amount (₹)</label>
          <input id="business-voucher-amount" type="number" placeholder="0.00" min="0.01" step="0.01" required>
        </div>
        ${dimensionFields}
        <div class="voucher-entry-lines">
          <div class="voucher-entry-line debit-line">
            <div>
              <span>Debit</span>
              <strong>Party payable / expense ledger</strong>
            </div>
            ${accountSelector("business-voucher-debit-account")}
          </div>
          <div class="voucher-entry-line credit-line">
            <div>
              <span>Credit</span>
              <strong>Bank / cash ledger</strong>
            </div>
            ${accountSelector("business-voucher-credit-account")}
          </div>
        </div>
        <div class="voucher-balance-panel">
          <strong>Double-entry check</strong>
          <span id="business-voucher-balance" class="voucher-balance-status imbalanced">
            <span>Debit: Rs. 0.00</span>
            <span>Credit: Rs. 0.00</span>
            <strong>Debit must equal Credit</strong>
          </span>
        </div>
        <div class="field">
          <label for="business-voucher-description">Description</label>
          <textarea id="business-voucher-description" rows="2" maxlength="300" placeholder="Payment description"></textarea>
        </div>
        <div class="field">
          <label for="business-voucher-reference">Reference (Check #, UTR, etc.)</label>
          <input id="business-voucher-reference" type="text" maxlength="80" placeholder="Optional: check number or reference">
        </div>
      </div>
    `;
  }

  if (voucherType === "receipt") {
    return `
      <div class="voucher-type-form">
        <div class="voucher-posting-map" aria-label="Receipt voucher posting">
          <div>
            <span>Debit</span>
            <strong>Bank or cash account</strong>
          </div>
          <div>
            <span>Credit</span>
            <strong>Customer / party ledger</strong>
          </div>
        </div>
        <div class="field">
          <label for="business-voucher-party">Party (Customer/Vendor)</label>
          <select id="business-voucher-party" required>
            <option value="">-- Select Party --</option>
            ${Array.isArray(getLastBusinessParties()) ? getLastBusinessParties().map(p =>
              `<option value="${escapeHtml(p.party_id)}">${escapeHtml(p.party_name)} (${p.party_type})</option>`
            ).join('') : ''}
          </select>
          <div id="business-voucher-outstanding" class="muted voucher-outstanding" data-voucher-type="${voucherType}"></div>
        </div>
        <div class="field">
          <label for="business-voucher-amount">Amount (₹)</label>
          <input id="business-voucher-amount" type="number" placeholder="0.00" min="0.01" step="0.01" required>
        </div>
        ${dimensionFields}
        <div class="voucher-entry-lines">
          <div class="voucher-entry-line debit-line">
            <div>
              <span>Debit</span>
              <strong>Bank / cash ledger</strong>
            </div>
            ${accountSelector("business-voucher-debit-account")}
          </div>
          <div class="voucher-entry-line credit-line">
            <div>
              <span>Credit</span>
              <strong>Customer receivable / party ledger</strong>
            </div>
            ${accountSelector("business-voucher-credit-account")}
          </div>
        </div>
        <div class="voucher-balance-panel">
          <strong>Double-entry check</strong>
          <span id="business-voucher-balance" class="voucher-balance-status imbalanced">
            <span>Debit: Rs. 0.00</span>
            <span>Credit: Rs. 0.00</span>
            <strong>Debit must equal Credit</strong>
          </span>
        </div>
        <div class="field">
          <label for="business-voucher-description">Description</label>
          <textarea id="business-voucher-description" rows="2" maxlength="300" placeholder="Receipt description"></textarea>
        </div>
        <div class="field">
          <label for="business-voucher-reference">Reference (Invoice #, etc.)</label>
          <input id="business-voucher-reference" type="text" maxlength="80" placeholder="Optional: invoice number or reference">
        </div>
      </div>
    `;
  }

  if (voucherType === "contra") {
    return `
      <div class="voucher-type-form">
        <div class="field">
          <label>From Account</label>
          ${accountSelector("business-voucher-from-account")}
        </div>
        <div class="field">
          <label>To Account</label>
          ${accountSelector("business-voucher-to-account")}
        </div>
        <div class="field">
          <label for="business-voucher-amount">Amount (₹)</label>
          <input id="business-voucher-amount" type="number" placeholder="0.00" min="0.01" step="0.01" required>
        </div>
        ${dimensionFields}
        <div class="field">
          <label for="business-voucher-description">Description</label>
          <textarea id="business-voucher-description" rows="2" maxlength="300" placeholder="Transfer description (e.g., sweep to savings)"></textarea>
        </div>
      </div>
    `;
  }

  if (voucherType === "journal") {
    return `
      <div class="voucher-type-form">
        <div class="field">
          <label for="business-voucher-description">Description</label>
          <textarea id="business-voucher-description" rows="2" maxlength="300" placeholder="Journal entry description" required></textarea>
        </div>
        <div class="voucher-lines-panel">
          <h4>Debit/Credit Lines</h4>
          <p class="muted" id="business-voucher-accounts-status">Select accounts and enter amounts.</p>
          <div id="business-voucher-lines"></div>
          <button class="secondary" type="button" id="business-voucher-add-line" aria-keyshortcuts="Alt+L">+ Add Line</button>
        </div>
        ${dimensionFields}
        <div class="voucher-balance-panel">
          <strong>Balance Check:</strong>
          <span id="business-voucher-balance" style="font-weight: bold; margin-left: 8px;">Debit: ₹0 | Credit: ₹0</span>
        </div>
      </div>
    `;
  }

  return `<p class="muted">Select a voucher type to proceed.</p>`;
}


export function updateVoucherTypeForm(voucherType) {
  const container = document.getElementById("business-voucher-form-container");
  if (!container) return;

  container.innerHTML = renderVoucherTypeForm(voucherType);

  // For journal entries, add initial lines
  if (voucherType === "journal") {
    addVoucherLine();
    addVoucherLine();
  }

  document.getElementById("business-voucher-add-line")?.addEventListener("click", (event) => {
    event.preventDefault();
    addVoucherLine();
  });

  // Re-attach event listeners for new elements
  updateVoucherBalance();
}


export function focusFirstVoucherField() {
  const firstField = document.getElementById("business-voucher-type-select");
  if (firstField) {
    setTimeout(() => firstField.focus(), 0);
  }
}


export function submitVoucherDialogFromKeyboard() {
  const submitButton = document.getElementById("business-voucher-submit");
  if (!submitButton || submitButton.disabled) {
    return;
  }
  getBusinessVoucherCreateForm()?.requestSubmit();
}


export function handleVoucherDialogKeyboard(event) {
  if (!getBusinessVoucherCreateDialog()?.open) {
    return;
  }
  if (event.key === "Enter" && event.ctrlKey) {
    event.preventDefault();
    submitVoucherDialogFromKeyboard();
    return;
  }
  if (event.key.toLowerCase() === "l" && event.altKey) {
    const voucherType = document.getElementById("business-voucher-type-select")?.value || "";
    if (voucherType === "journal") {
      event.preventDefault();
      addVoucherLine();
    }
  }
}


export async function openBusinessCreateVoucherDialog() {
  const dialog = document.getElementById("business-voucher-create-dialog");
  if (!dialog) return;

  if (!Array.isArray(getLastBusinessAccounts()) || getLastBusinessAccounts().length === 0) {
    await loadBusinessAccounts();
  }
  if (!Array.isArray(getLastBusinessParties()) || getLastBusinessParties().length === 0) {
    await loadBusinessParties();
  }
  if (!getLastDimensions()) {
    await loadDimensions();
  }

  // Reset form
  document.getElementById("business-voucher-type-select").value = "";
  document.getElementById("business-voucher-form-container").innerHTML = "";
  document.getElementById("business-voucher-date").valueAsDate = new Date();

  if (!Array.isArray(getLastBusinessAccounts()) || getLastBusinessAccounts().length === 0) {
    setLoginStatus("warn", "Accounts unavailable", "Load the MitraBooks chart of accounts before posting a voucher.");
  }

  dialog.showModal();
  focusFirstVoucherField();
}


