// ====================================================================
// SECTION: VOUCHERS — creation helpers (party / contra / journal)
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initVoucherCreate(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

/** @type {Record<string, Function> | null} */
let deps = null;

export function initVoucherCreate(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initVoucherCreate() must be called before using voucher-create helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function findBusinessAccountById(accountId) { return requireDeps().findBusinessAccountById(accountId); }
function accountIdForVoucherPayload(account) { return requireDeps().accountIdForVoucherPayload(account); }
function voucherDimensionPayload() { return requireDeps().voucherDimensionPayload(); }
function clearVoucherForm() { return requireDeps().clearVoucherForm(); }
function loadBusinessVouchers(filters) { return requireDeps().loadBusinessVouchers(filters); }
function loadVoucherApprovalQueue(includeReviewed, options) { return requireDeps().loadVoucherApprovalQueue(includeReviewed, options); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function renderBusinessWorkspace() { return requireDeps().renderBusinessWorkspace(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

export async function loadVoucherPartyOutstanding(partyId, voucherType) {
  const box = document.getElementById("business-voucher-outstanding");
  if (!box) return;
  if (!partyId) { box.textContent = ""; return; }
  box.textContent = "Loading outstanding…";
  const result = await apiRequest("mitrabooks", `/api/v1/business/parties/${encodeURIComponent(partyId)}/outstanding`, { method: "GET" });
  if (!result.ok) { box.textContent = ""; return; }
  const recv = Number(result.payload?.receivable || 0);
  const pay = Number(result.payload?.payable || 0);
  // Emphasise the side relevant to the voucher: receipt → receivable, payment → payable.
  const primary = voucherType === "payment"
    ? `Outstanding payable: <strong>${escapeHtml(formatCurrency(pay))}</strong>`
    : `Outstanding receivable: <strong>${escapeHtml(formatCurrency(recv))}</strong>`;
  const secondary = voucherType === "payment"
    ? `receivable ${escapeHtml(formatCurrency(recv))}`
    : `payable ${escapeHtml(formatCurrency(pay))}`;
  box.innerHTML = `${primary} <span class="muted">(${secondary})</span>`;
}


export async function createBusinessVoucherByType(voucherType, date) {
  const appKey = "mitrabooks";

  try {
    if (voucherType === "payment" || voucherType === "receipt") {
      await createSimplePartyVoucher(appKey, voucherType, date);
    } else if (voucherType === "contra") {
      await createContraVoucher(appKey, date);
    } else if (voucherType === "journal") {
      await createJournalVoucher(appKey, date);
    } else {
      setLoginStatus("warn", "Unknown voucher type", `Voucher type '${voucherType}' is not supported.`);
    }
  } catch (error) {
    setLoginStatus("danger", "Voucher creation failed", error.message || "An unexpected error occurred.");
  }
}


export async function createSimplePartyVoucher(appKey, voucherType, date) {
  const partyId = document.getElementById("business-voucher-party")?.value || "";
  const amount = document.getElementById("business-voucher-amount")?.value || "0";
  const debitAccountIdInput = document.querySelector(".account-id-input[data-field-id='business-voucher-debit-account']");
  const creditAccountIdInput = document.querySelector(".account-id-input[data-field-id='business-voucher-credit-account']");
  const debitAccountId = debitAccountIdInput?.value || "";
  const creditAccountId = creditAccountIdInput?.value || "";
  const debitAccount = findBusinessAccountById(debitAccountId);
  const creditAccount = findBusinessAccountById(creditAccountId);
  const description = document.getElementById("business-voucher-description")?.value || "";
  const reference = document.getElementById("business-voucher-reference")?.value || "";

  if (!partyId) {
    setLoginStatus("warn", "Party required", "Select a party for this voucher.");
    return;
  }

  if (!debitAccount || !creditAccount) {
    setLoginStatus("warn", "Debit and credit accounts required", "Select both sides of the voucher before posting.");
    return;
  }

  if (String(debitAccount.id) === String(creditAccount.id) || debitAccount.code === creditAccount.code) {
    setLoginStatus("warn", "Different accounts required", "Debit and credit accounts cannot be the same ledger account.");
    return;
  }

  const amountVal = Number(amount);
  if (amountVal <= 0) {
    setLoginStatus("warn", "Invalid amount", "Amount must be greater than zero.");
    return;
  }

  const payload = {
    voucher_type: voucherType,
    entry_date: date,
    amount: amountVal.toFixed(2),
    debit_account_id: accountIdForVoucherPayload(debitAccount),
    credit_account_id: accountIdForVoucherPayload(creditAccount),
    debit_account_code: debitAccount.code,
    credit_account_code: creditAccount.code,
    description: description || `${voucherType} voucher`,
    reference: reference || null,
    party_id: partyId,
    ...voucherDimensionPayload(),
  };

  const result = await apiRequest(appKey, "/api/v1/business/vouchers", {
    method: "POST",
    headers: {
      "X-Idempotency-Key": `business-voucher-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    },
    body: JSON.stringify(payload),
  });

  if (result.ok) {
    setLoginStatus("ok", "Voucher submitted", `${voucherType.toUpperCase()} voucher sent for approval.`);
    document.getElementById("business-voucher-create-dialog")?.close();
    await loadBusinessVouchers();
    await loadVoucherApprovalQueue(true, { surfaceErrors: false });
    if (getActiveBusinessWorkspace() === "vouchers") {
      getDashboardPreview().innerHTML = renderBusinessWorkspace();
    }
  } else {
    setLoginStatus("danger", "Create voucher failed", statusDetailText(result.payload?.detail) || "Check entries and try again.");
  }
  renderJson(getApiOutput(), { create_voucher: result });
}


export async function createContraVoucher(appKey, date) {
  const fromAccountIdInput = document.querySelector(".account-id-input[data-field-id='business-voucher-from-account']");
  const toAccountIdInput = document.querySelector(".account-id-input[data-field-id='business-voucher-to-account']");
  const fromAccountId = fromAccountIdInput?.value || "";
  const toAccountId = toAccountIdInput?.value || "";
  const fromAccount = findBusinessAccountById(fromAccountId);
  const toAccount = findBusinessAccountById(toAccountId);
  const amount = document.getElementById("business-voucher-amount")?.value || "0";
  const description = document.getElementById("business-voucher-description")?.value || "Bank transfer";

  if (!fromAccount || !toAccount) {
    setLoginStatus("warn", "Accounts required", "Select both From and To accounts.");
    return;
  }

  if (String(fromAccount.id) === String(toAccount.id) || fromAccount.code === toAccount.code) {
    setLoginStatus("warn", "Same account", "From and To accounts must be different.");
    return;
  }

  const amountVal = Number(amount);
  if (amountVal <= 0) {
    setLoginStatus("warn", "Invalid amount", "Amount must be greater than zero.");
    return;
  }

  const payload = {
    voucher_type: "contra",
    entry_date: date,
    amount: amountVal.toFixed(2),
    debit_account_id: accountIdForVoucherPayload(toAccount),
    credit_account_id: accountIdForVoucherPayload(fromAccount),
    debit_account_code: toAccount.code,
    credit_account_code: fromAccount.code,
    description: description,
    reference: null,
    ...voucherDimensionPayload(),
  };

  const result = await apiRequest(appKey, "/api/v1/business/vouchers", {
    method: "POST",
    headers: {
      "X-Idempotency-Key": `business-voucher-contra-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    },
    body: JSON.stringify(payload),
  });

  if (result.ok) {
    setLoginStatus("ok", "Voucher submitted", "Contra voucher sent for approval.");
    document.getElementById("business-voucher-create-dialog")?.close();
    await loadBusinessVouchers();
    await loadVoucherApprovalQueue(true, { surfaceErrors: false });
    if (getActiveBusinessWorkspace() === "vouchers") {
      getDashboardPreview().innerHTML = renderBusinessWorkspace();
    }
  } else {
    setLoginStatus("danger", "Create voucher failed", statusDetailText(result.payload?.detail) || "Check entries and try again.");
  }
  renderJson(getApiOutput(), { create_voucher: result });
}


export async function createJournalVoucher(appKey, date) {
  const description = document.getElementById("business-voucher-description")?.value || "";

  const debitLines = [];
  const creditLines = [];
  document.querySelectorAll(".voucher-line").forEach((lineEl) => {
    const accountIdInput = lineEl.querySelector(".account-id-input");
    const debitInput = lineEl.querySelector(".voucher-debit");
    const creditInput = lineEl.querySelector(".voucher-credit");

    const accountId = accountIdInput?.value || "";
    const account = findBusinessAccountById(accountId);
    const debit = Number(debitInput?.value) || 0;
    const credit = Number(creditInput?.value) || 0;

    if (account && (debit > 0 || credit > 0)) {
      const lineAccount = {
        account_id: accountIdForVoucherPayload(account),
        account_code: account.code,
        amount: "",
      };
      if (debit > 0) debitLines.push({ ...lineAccount, amount: debit.toFixed(2) });
      if (credit > 0) creditLines.push({ ...lineAccount, amount: credit.toFixed(2) });
    }
  });

  if (debitLines.length !== 1 || creditLines.length !== 1) {
    setLoginStatus("warn", "One debit and one credit required", "Phase 1 supports one debit and one credit account per entry.");
    return;
  }

  const debitTotal = Number(debitLines[0].amount);
  const creditTotal = Number(creditLines[0].amount);
  if (Math.abs(debitTotal - creditTotal) >= 0.01) {
    setLoginStatus("warn", "Voucher is not balanced", "Debit amount must equal credit amount.");
    return;
  }

  const payload = {
    voucher_type: "journal",
    entry_date: date,
    amount: debitTotal.toFixed(2),
    debit_account_id: debitLines[0].account_id,
    credit_account_id: creditLines[0].account_id,
    debit_account_code: debitLines[0].account_code,
    credit_account_code: creditLines[0].account_code,
    description: description || "Journal entry",
    reference: null,
    ...voucherDimensionPayload(),
  };

  const result = await apiRequest(appKey, "/api/v1/business/vouchers", {
    method: "POST",
    headers: {
      "X-Idempotency-Key": `business-voucher-journal-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    },
    body: JSON.stringify(payload),
  });

  if (result.ok) {
    setLoginStatus("ok", "Voucher submitted", "Journal entry sent for approval.");
    document.getElementById("business-voucher-create-dialog")?.close();
    await loadBusinessVouchers();
    await loadVoucherApprovalQueue(true, { surfaceErrors: false });
    if (getActiveBusinessWorkspace() === "vouchers") {
      getDashboardPreview().innerHTML = renderBusinessWorkspace();
    }
  } else {
    setLoginStatus("danger", "Create voucher failed", statusDetailText(result.payload?.detail) || "Check entries and try again.");
  }
  renderJson(getApiOutput(), { create_voucher: result });
}


async function createBusinessVoucherByType(voucherType, date) {
  const appKey = "mitrabooks";

  try {
    if (voucherType === "payment" || voucherType === "receipt") {
      await createSimplePartyVoucher(appKey, voucherType, date);
    } else if (voucherType === "contra") {
      await createContraVoucher(appKey, date);
    } else if (voucherType === "journal") {
      await createJournalVoucher(appKey, date);
    } else {
      setLoginStatus("warn", "Unknown voucher type", `Voucher type '${voucherType}' is not supported.`);
    }
  } catch (error) {
    setLoginStatus("danger", "Voucher creation failed", error.message || "An unexpected error occurred.");
  }
}

