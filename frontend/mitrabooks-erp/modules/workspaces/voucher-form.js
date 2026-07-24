// ====================================================================
// SECTION: VOUCHER FORM HELPERS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initVoucherForm(...).
// ====================================================================

export let voucherLineCounter = 0;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initVoucherForm(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initVoucherForm() must be called before using voucher form helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function normalizeBusinessAccount(acc) { return requireDeps().normalizeBusinessAccount(acc); }
function businessAccountLabel(account) { return requireDeps().businessAccountLabel(account); }
function renderAccountSelectorComponent(fieldId, selectedAccountId = null) {
  return requireDeps().renderAccountSelectorComponent(fieldId, selectedAccountId);
}
function refreshVoucherAccountDatalist() { return requireDeps().refreshVoucherAccountDatalist(); }
function updateVoucherAccountsStatus() { return requireDeps().updateVoucherAccountsStatus(); }
function populateVoucherAccountSelect(select, selectedId = "") {
  return requireDeps().populateVoucherAccountSelect(select, selectedId);
}
function getLastBusinessAccounts() { return requireDeps().getLastBusinessAccounts(); }

export function setVoucherLineCounter(value) {
  voucherLineCounter = Number(value) || 0;
}

export function syncVoucherAccountFromText(lineEl) {
  const input = lineEl?.querySelector(".voucher-account");
  const select = lineEl?.querySelector(".voucher-account-select");
  const query = String(input?.value || "").trim().toLowerCase();
  if (!query || !select) return;
  const match = (Array.isArray(getLastBusinessAccounts()) ? getLastBusinessAccounts() : [])
    .map(normalizeBusinessAccount)
    .find((acc) => acc.code.toLowerCase().startsWith(query) || acc.name.toLowerCase().includes(query));
  if (match?.id) {
    select.value = match.id;
  }
}

export function renderVoucherLineItem(lineId, voucherType) {
  const accountSelector = renderAccountSelectorComponent(`voucher-account-${lineId}`);

  return `
    <div class="voucher-line" data-line-id="${escapeHtml(lineId)}">
      <div class="voucher-line-grid">
        <div class="voucher-account-field">
          <label>Account</label>
          ${accountSelector}
        </div>
        <div class="voucher-amount-field">
          <label>Debit (₹)</label>
          <input
            class="voucher-debit"
            type="number"
            placeholder="0.00"
            min="0"
            step="0.01"
            data-line-id="${escapeHtml(lineId)}"
          >
        </div>
        <div class="voucher-amount-field">
          <label>Credit (₹)</label>
          <input
            class="voucher-credit"
            type="number"
            placeholder="0.00"
            min="0"
            step="0.01"
            data-line-id="${escapeHtml(lineId)}"
          >
        </div>
        <div class="voucher-action-field">
          <button
            class="secondary"
            type="button"
            data-business-action="remove-voucher-line"
            data-line-id="${escapeHtml(lineId)}"
          >Remove</button>
        </div>
      </div>
    </div>
  `;
}

export function updateVoucherBalance() {
  let totalDebit = 0;
  let totalCredit = 0;

  document.querySelectorAll(".voucher-debit").forEach((input) => {
    totalDebit += Number(input.value) || 0;
  });

  document.querySelectorAll(".voucher-credit").forEach((input) => {
    totalCredit += Number(input.value) || 0;
  });

  const simpleAmountInput = document.getElementById("business-voucher-amount");
  const isSimplePartyVoucher = simpleAmountInput && !document.querySelector(".voucher-debit, .voucher-credit");
  if (isSimplePartyVoucher) {
    const amount = Number(simpleAmountInput.value) || 0;
    totalDebit = amount;
    totalCredit = amount;
  }

  const hasAmount = totalDebit > 0 || totalCredit > 0;
  const isBalanced = hasAmount && Math.abs(totalDebit - totalCredit) < 0.01;
  const balanceEl = document.getElementById("business-voucher-balance");
  if (balanceEl) {
    balanceEl.className = isBalanced ? "voucher-balance-status balanced" : "voucher-balance-status imbalanced";
    balanceEl.innerHTML = `
      <span>Debit: ${formatCurrency(totalDebit)}</span>
      <span>Credit: ${formatCurrency(totalCredit)}</span>
      <strong>${isBalanced ? "Debit = Credit" : "Debit must equal Credit"}</strong>
    `;
  }

  const submitBtn = document.getElementById("business-voucher-submit");
  if (submitBtn) {
    submitBtn.disabled = !isBalanced;
  }
}

export function updateVoucherBalanceState() {
  let totalDebit = 0;
  let totalCredit = 0;

  document.querySelectorAll(".voucher-debit").forEach((input) => {
    totalDebit += Number(input.value) || 0;
  });
  document.querySelectorAll(".voucher-credit").forEach((input) => {
    totalCredit += Number(input.value) || 0;
  });

  const hasAmount = totalDebit > 0 || totalCredit > 0;
  const isBalanced = hasAmount && Math.abs(totalDebit - totalCredit) < 0.01;
  const balanceEl = document.getElementById("business-voucher-balance");
  if (balanceEl) {
    balanceEl.className = isBalanced ? "voucher-balance-status balanced" : "voucher-balance-status imbalanced";
    balanceEl.innerHTML = `
      <span>Debit: ${formatCurrency(totalDebit)}</span>
      <span>Credit: ${formatCurrency(totalCredit)}</span>
      <strong>${isBalanced ? "Balanced" : "Imbalanced"}</strong>
    `;
  }

  const submitBtn = document.getElementById("business-voucher-submit");
  if (submitBtn) {
    submitBtn.disabled = !isBalanced;
  }
}

export function addVoucherLine() {
  voucherLineCounter += 1;
  const lineId = `line-${voucherLineCounter}`;
  const container = document.getElementById("business-voucher-lines");
  if (!container) return;

  const lineHtml = renderVoucherLineItem(lineId);
  container.insertAdjacentHTML("beforeend", lineHtml);
  refreshVoucherAccountDatalist();
  updateVoucherAccountsStatus();

  const select = container.querySelector(`[data-line-id="${lineId}"].voucher-account-select`);
  populateVoucherAccountSelect(select);
  if (select) {
    select.addEventListener("change", () => {
      const selected = normalizeBusinessAccount(getLastBusinessAccounts().find((acc) => String(acc.account_id ?? acc.id ?? "") === select.value) || {});
      const accountInput = container.querySelector(`[data-line-id="${lineId}"].voucher-account`);
      if (accountInput && selected.id) {
        accountInput.value = businessAccountLabel(selected);
      }
    });
  }

  const accountInput = container.querySelector(`[data-line-id="${lineId}"].voucher-account`);
  const debitInput = container.querySelector(`[data-line-id="${lineId}"].voucher-debit`);
  const creditInput = container.querySelector(`[data-line-id="${lineId}"].voucher-credit`);
  if (accountInput) accountInput.addEventListener("input", () => syncVoucherAccountFromText(accountInput.closest(".voucher-line")));
  if (debitInput) debitInput.addEventListener("input", updateVoucherBalanceState);
  if (creditInput) creditInput.addEventListener("input", updateVoucherBalanceState);
}

export function removeVoucherLine(lineId) {
  const lineEl = Array.from(document.querySelectorAll(".voucher-line"))
    .find((candidate) => candidate.getAttribute("data-line-id") === lineId);
  if (lineEl) {
    lineEl.remove();
    updateVoucherBalanceState();
  }
}

export function clearVoucherForm() {
  voucherLineCounter = 0;
  document.getElementById("business-voucher-date").valueAsDate = new Date();
  document.getElementById("business-voucher-reference").value = "";
  document.getElementById("business-voucher-narration").value = "";
  document.getElementById("business-voucher-lines").innerHTML = "";
  updateVoucherBalanceState();
}


