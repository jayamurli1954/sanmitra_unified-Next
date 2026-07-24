// ====================================================================
// SECTION: MANDIR — CREATE FORMS + POSTING DIALOGS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initMandirCreateForms(...).
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

/** DOM refs bound once during init (same elements the shell owns). */
let mandirVerificationDialog;
let mandirVerificationPaymentId;
let mandirVerificationLabel;
let mandirVerificationUtr;
let mandirVerificationDate;
let mandirVerificationBankAccount;
let mandirRejectionDialog;
let mandirRejectionPaymentId;
let mandirRejectionLabel;
let mandirRejectionReason;
let mandirCorrectionDialog;
let mandirCorrectionForm;
let mandirCorrectionPaymentId;
let mandirCorrectionLabel;
let mandirCorrectionAmount;
let mandirCorrectionPhone;
let mandirCorrectionType;
let mandirCorrectionPurpose;
let mandirCancelReceiptDialog;
let mandirCancelReceiptUrl;
let mandirCancelReceiptLabel;
let mandirCancelReceiptReason;
let mandirCancelRefundMode;
let mandirCancelRefundReference;
let mandirCancelReceiptSubmit;
let receiptPreviewDialog;
let receiptPreviewFrame;
let receiptPreviewLabel;
let dashboardPreview;
let apiOutput;

export function initMandirCreateForms(injected) {
  deps = injected;
  mandirVerificationDialog = injected.mandirVerificationDialog;
  mandirVerificationPaymentId = injected.mandirVerificationPaymentId;
  mandirVerificationLabel = injected.mandirVerificationLabel;
  mandirVerificationUtr = injected.mandirVerificationUtr;
  mandirVerificationDate = injected.mandirVerificationDate;
  mandirVerificationBankAccount = injected.mandirVerificationBankAccount;
  mandirRejectionDialog = injected.mandirRejectionDialog;
  mandirRejectionPaymentId = injected.mandirRejectionPaymentId;
  mandirRejectionLabel = injected.mandirRejectionLabel;
  mandirRejectionReason = injected.mandirRejectionReason;
  mandirCorrectionDialog = injected.mandirCorrectionDialog;
  mandirCorrectionForm = injected.mandirCorrectionForm;
  mandirCorrectionPaymentId = injected.mandirCorrectionPaymentId;
  mandirCorrectionLabel = injected.mandirCorrectionLabel;
  mandirCorrectionAmount = injected.mandirCorrectionAmount;
  mandirCorrectionPhone = injected.mandirCorrectionPhone;
  mandirCorrectionType = injected.mandirCorrectionType;
  mandirCorrectionPurpose = injected.mandirCorrectionPurpose;
  mandirCancelReceiptDialog = injected.mandirCancelReceiptDialog;
  mandirCancelReceiptUrl = injected.mandirCancelReceiptUrl;
  mandirCancelReceiptLabel = injected.mandirCancelReceiptLabel;
  mandirCancelReceiptReason = injected.mandirCancelReceiptReason;
  mandirCancelRefundMode = injected.mandirCancelRefundMode;
  mandirCancelRefundReference = injected.mandirCancelRefundReference;
  mandirCancelReceiptSubmit = injected.mandirCancelReceiptSubmit;
  receiptPreviewDialog = injected.receiptPreviewDialog;
  receiptPreviewFrame = injected.receiptPreviewFrame;
  receiptPreviewLabel = injected.receiptPreviewLabel;
  dashboardPreview = injected.dashboardPreview;
  apiOutput = injected.apiOutput;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initMandirCreateForms() must be called before using Mandir create-form helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function todayIsoDate() { return requireDeps().todayIsoDate(); }
function apiRequest(...args) { return requireDeps().apiRequest(...args); }
function renderJson(...args) { return requireDeps().renderJson(...args); }
function loadMandirDashboard(...args) { return requireDeps().loadMandirDashboard(...args); }
function downloadApiFile(...args) { return requireDeps().downloadApiFile(...args); }
function fetchApiFileObjectUrl(...args) { return requireDeps().fetchApiFileObjectUrl(...args); }
function syncMandirNavActiveState() { return requireDeps().syncMandirNavActiveState(); }
function getLastMandirPaymentAccounts() { return requireDeps().getLastMandirPaymentAccounts(); }
function getLastMandirAccounts() { return requireDeps().getLastMandirAccounts(); }
function getLastMandirFormResult() { return requireDeps().getLastMandirFormResult(); }
function setLastMandirFormResult(value) { requireDeps().setLastMandirFormResult(value); }
function getLastMandirReceipt() { return requireDeps().getLastMandirReceipt(); }
function setLastMandirReceipt(value) { requireDeps().setLastMandirReceipt(value); }
function setLastMandirComplianceConfig(value) { requireDeps().setLastMandirComplianceConfig(value); }
function getMandirReportState() { return requireDeps().getMandirReportState(); }
function getMandirListState() { return requireDeps().getMandirListState(); }
function getMandirListPageSize() { return requireDeps().getMandirListPageSize(); }
function setActiveMandirWorkspace(view) { requireDeps().setActiveMandirWorkspace(view); }
function getActiveReceiptPreviewObjectUrl() { return requireDeps().getActiveReceiptPreviewObjectUrl(); }
function setActiveReceiptPreviewObjectUrl(value) { requireDeps().setActiveReceiptPreviewObjectUrl(value); }

export function renderBankAccountOptions(accounts = []) {
  const options = ['<option value="">Use backend default bank account</option>'];
  accounts.forEach((account) => {
    const accountId = account.account_id || account.id || "";
    if (!accountId) {
      return;
    }
    const accountCode = account.account_code ? `${account.account_code} - ` : "";
    const accountName = account.account_name || account.name || "Bank account";
    options.push(`<option value="${escapeHtml(accountId)}">${escapeHtml(`${accountCode}${accountName}`)}</option>`);
  });
  return options.join("");
}

export function mandirAccountOptionValue(account = {}) {
  return account.account_id || account.id || account.account_code || "";
}

export function mandirAccountOptionLabel(account = {}) {
  const code = account.account_code ? `${account.account_code} - ` : "";
  return `${code}${account.account_name || account.name || "Account"}`;
}

export function renderMandirAccountOptions(accounts = [], placeholder = "Select account") {
  const options = [`<option value="">${escapeHtml(placeholder)}</option>`];
  accounts.forEach((account) => {
    const value = mandirAccountOptionValue(account);
    if (!value) {
      return;
    }
    options.push(`<option value="${escapeHtml(value)}">${escapeHtml(mandirAccountOptionLabel(account))}</option>`);
  });
  return options.join("");
}

export function mandirPaymentAccountOptions(paymentAccounts = getLastMandirPaymentAccounts()) {
  return [
    ...(Array.isArray(paymentAccounts.cash_accounts) ? paymentAccounts.cash_accounts : []),
    ...(Array.isArray(paymentAccounts.bank_accounts) ? paymentAccounts.bank_accounts : []),
  ];
}

export function mandirExpenseAccountOptions(accounts = getLastMandirAccounts()) {
  return accounts.filter((account) => {
    const type = String(account.account_type || "").toLowerCase();
    const name = String(account.account_name || account.name || "").toLowerCase();
    return type === "expense" || name.includes("expense");
  });
}

export function renderMandirCreateForms(payload = {}) {
  const paymentOptions = renderMandirAccountOptions(
    mandirPaymentAccountOptions(payload.payment_accounts),
    "Use default cash/bank"
  );
  const expenseOptions = renderMandirAccountOptions(
    mandirExpenseAccountOptions(payload.accounts),
    "Select expense account"
  );
  const today = todayIsoDate();
  const result = payload.form_result || getLastMandirFormResult();
  const inventoryEnabled = Boolean(payload.module_config?.module_inventory_enabled);
  const complianceConfig = payload.compliance_config || {};
  const inKindAccountingLabel = inventoryEnabled
    ? "In-kind consumables debit inventory"
    : "In-kind consumables debit expense";
  return `
    <div class="quick-entry-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Daily Entry</h4>
          <p>Record donations, seva bookings, and temple expenses for the active temple tenant.</p>
        </div>
        <span class="pill technical-context">${escapeHtml(inKindAccountingLabel)}</span>
      </div>
      ${result ? `
        <div class="module-state ${result.ok ? "ok" : "warn"}">
          <strong>${escapeHtml(result.title || (result.ok ? "Entry saved" : "Entry failed"))}</strong>
          <span>${escapeHtml(result.detail || "")}</span>
        </div>
      ` : ""}
      <div class="entry-form-grid">
        <form class="entry-form" data-mandir-create-form="donation">
          <h5>Donation</h5>
          <label class="field">
            <span>Devotee</span>
            <input name="devotee_name" required maxlength="120" placeholder="Devotee name">
          </label>
          <label class="field">
            <span>Phone</span>
            <input name="devotee_phone" inputmode="numeric" maxlength="15" placeholder="Optional">
          </label>
          <label class="field">
            <span>Amount</span>
            <input name="amount" type="number" min="0.01" step="0.01" required placeholder="501">
          </label>
          <label class="field">
            <span>Category</span>
            <select name="category">
              <option value="General Donation">General Donation</option>
              <option value="Sponsorship">Sponsorship</option>
              <option value="Annadanam">Annadanam</option>
              <option value="Flower Decoration">Flower Decoration</option>
              <option value="Lighting Sponsorship">Lighting Sponsorship</option>
              <option value="Vastra Seva">Vastra Seva</option>
              <option value="Nitya Puja">Nitya Puja</option>
              <option value="Construction Fund">Construction Fund</option>
              <option value="Corpus Fund">Corpus Fund</option>
            </select>
          </label>
          <label class="field">
            <span>Donation type</span>
            <select name="donation_type">
              <option value="cash">Cash / bank</option>
              <option value="in_kind">In-kind valued</option>
            </select>
          </label>
          <label class="field">
            <span>Event / festival</span>
            <input name="event_name" maxlength="160" placeholder="Annadanam, Deepotsava">
          </label>
          <label class="field">
            <span>Item name</span>
            <input name="in_kind_item_name" maxlength="160" placeholder="Rice bags, gold ornament">
          </label>
          <label class="field">
            <span>Item type</span>
            <select name="in_kind_item_type">
              <option value="">Not applicable</option>
              <option value="rice">Rice / food grains</option>
              <option value="dal">Dal</option>
              <option value="oil">Oil / ghee</option>
              <option value="flower decoration">Flower decoration</option>
              <option value="lighting">Lighting</option>
              <option value="gold ornament">Gold ornament</option>
              <option value="silver article">Silver article</option>
              <option value="idol">Idol / vigraha</option>
              <option value="pooja material">Pooja material</option>
            </select>
          </label>
          <label class="field">
            <span>Quantity</span>
            <input name="in_kind_quantity" maxlength="80" placeholder="50 kg, 2 bags, 1 item">
          </label>
          <label class="field">
            <span>Valuation basis</span>
            <input name="in_kind_valuation_basis" maxlength="180" placeholder="Market value, invoice, trustee valuation">
          </label>
          <label class="field">
            <span>Payment mode</span>
            <select name="payment_mode">
              <option value="Cash">Cash</option>
              <option value="Bank">Bank</option>
              <option value="UPI">UPI</option>
            </select>
          </label>
          <label class="field">
            <span>Cash/bank account</span>
            <select name="payment_account_id">${paymentOptions}</select>
          </label>
          <label class="field">
            <span><input name="request_80g" type="checkbox" ${complianceConfig.enable_80g ? "" : "disabled"}> Request 80G eligibility review</span>
            <small>${complianceConfig.enable_80g ? "Requires donor PAN and tenant approval validity." : "80G is off for this tenant."}</small>
          </label>
          <label class="field">
            <span>Donor PAN</span>
            <input name="donor_pan" maxlength="10" pattern="[A-Za-z]{5}[0-9]{4}[A-Za-z]" placeholder="Required when 80G is requested" ${complianceConfig.enable_80g ? "" : "disabled"}>
          </label>
          <label class="field">
            <span><input name="is_foreign_contribution" type="checkbox" ${complianceConfig.enable_fcra ? "" : "disabled"}> Foreign contribution</span>
            <small>${complianceConfig.enable_fcra ? `Must use designated account ${escapeHtml(complianceConfig.fcra_designated_account_id || "configured by admin")}.` : "FCRA is off for this tenant."}</small>
          </label>
          <label class="field">
            <span>Donor country</span>
            <input name="donor_country" maxlength="100" placeholder="Required for foreign contribution" ${complianceConfig.enable_fcra ? "" : "disabled"}>
          </label>
          <label class="field">
            <span><input name="foreign_source_declaration" type="checkbox" ${complianceConfig.enable_fcra ? "" : "disabled"}> Foreign-source declaration confirmed</span>
          </label>
          <button type="submit">Create Donation</button>
        </form>

        <form class="entry-form" data-mandir-create-form="seva">
          <h5>Seva Booking</h5>
          <label class="field">
            <span>Devotee</span>
            <input name="devotee_name" required maxlength="120" placeholder="Devotee name">
          </label>
          <label class="field">
            <span>Phone</span>
            <input name="devotee_phone" inputmode="numeric" maxlength="15" placeholder="Optional">
          </label>
          <label class="field">
            <span>Seva</span>
            <input name="seva_name" required maxlength="160" placeholder="Archana">
          </label>
          <label class="field">
            <span>Booking date</span>
            <input name="booking_date" type="date" value="${escapeHtml(today)}" required>
          </label>
          <label class="field">
            <span>Amount</span>
            <input name="amount" type="number" min="0.01" step="0.01" required placeholder="301">
          </label>
          <label class="field">
            <span>Payment mode</span>
            <select name="payment_mode">
              <option value="Cash">Cash</option>
              <option value="Bank">Bank</option>
              <option value="UPI">UPI</option>
            </select>
          </label>
          <label class="field">
            <span>Cash/bank account</span>
            <select name="payment_account_id">${paymentOptions}</select>
          </label>
          <button type="submit">Create Seva Booking</button>
        </form>

        <form class="entry-form" data-mandir-create-form="expense">
          <h5>Quick Expense</h5>
          <label class="field">
            <span>Narration</span>
            <input name="narration" required maxlength="160" placeholder="Flowers and pooja material">
          </label>
          <label class="field">
            <span>Entry date</span>
            <input name="entry_date" type="date" value="${escapeHtml(today)}" required>
          </label>
          <label class="field">
            <span>Amount</span>
            <input name="amount" type="number" min="0.01" step="0.01" required placeholder="250">
          </label>
          <label class="field">
            <span>Expense account</span>
            <select name="expense_account_id" required>${expenseOptions}</select>
          </label>
          <label class="field">
            <span>Paid from</span>
            <select name="payment_account_id" required>${paymentOptions}</select>
          </label>
          <button type="submit">Create Expense</button>
        </form>
      </div>
    </div>
  `;
}

export async function openMandirVerificationDialog(button) {
  const paymentId = button.getAttribute("data-payment-id") || "";
  if (!paymentId) {
    return;
  }
  const paymentLabel = button.getAttribute("data-payment-label") || paymentId;
  const paymentType = button.getAttribute("data-payment-type") || "payment";
  const devoteeName = button.getAttribute("data-devotee-name") || "Devotee";
  const amount = formatCurrency(button.getAttribute("data-payment-amount") || 0);

  mandirVerificationPaymentId.value = paymentId;
  mandirVerificationUtr.value = "";
  mandirVerificationDate.value = todayIsoDate();
  mandirVerificationLabel.textContent = `${paymentLabel} | ${paymentType} | ${devoteeName} | ${amount}`;
  mandirVerificationBankAccount.innerHTML = '<option value="">Loading bank accounts...</option>';
  mandirVerificationDialog.showModal();

  const accounts = await apiRequest("mandirmitra", "/api/v1/donations/payment-accounts", { method: "GET" });
  if (accounts.ok) {
    const bankAccounts = Array.isArray(accounts.payload?.bank_accounts) ? accounts.payload.bank_accounts : [];
    mandirVerificationBankAccount.innerHTML = renderBankAccountOptions(bankAccounts);
  } else {
    mandirVerificationBankAccount.innerHTML = '<option value="">Use backend default bank account</option>';
    renderJson(apiOutput, { mandir_payment_accounts: accounts });
  }
}

export function mandirReceiptFromVerifyPayload(payload) {
  const receiptPdfUrl = String(payload?.receipt_pdf_url || "").trim();
  if (!receiptPdfUrl) {
    return null;
  }
  const receiptNumber = String(payload?.receipt_number || payload?.payment_id || "receipt").trim();
  const safeReceiptNumber = receiptNumber.replace(/[^a-z0-9_-]+/gi, "_") || "receipt";
  return {
    receipt_pdf_url: receiptPdfUrl,
    receipt_number: receiptNumber,
    source_id: payload?.source_id,
    source_type: payload?.source_type,
    filename: `${safeReceiptNumber}.pdf`,
  };
}

export async function submitMandirPublicPaymentVerification() {
  const paymentId = mandirVerificationPaymentId.value;
  if (!paymentId) {
    return;
  }
  const utrReference = mandirVerificationUtr.value.trim().replace(/\s+/g, " ");
  if (!/^[A-Za-z0-9][A-Za-z0-9 ._:/-]{3,79}$/.test(utrReference)) {
    mandirVerificationUtr.setCustomValidity("Enter a valid UTR/reference, 4-80 characters.");
    mandirVerificationUtr.reportValidity();
    return;
  }
  mandirVerificationUtr.setCustomValidity("");
  const payload = {
    utr_reference: utrReference,
    payment_date: mandirVerificationDate.value || todayIsoDate(),
  };
  if (mandirVerificationBankAccount.value) {
    payload.bank_account_id = mandirVerificationBankAccount.value;
  }

  const result = await apiRequest("mandirmitra", `/api/v1/public-payments/${encodeURIComponent(paymentId)}/verify`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  renderJson(apiOutput, { verify_mandir_public_payment: result });
  if (result.ok) {
    setLastMandirReceipt(mandirReceiptFromVerifyPayload(result.payload));
  }
  mandirVerificationDialog.close();
  await loadMandirDashboard();
}

export function openMandirRejectionDialog(button) {
  const paymentId = button.getAttribute("data-payment-id") || "";
  if (!paymentId) {
    return;
  }
  const paymentLabel = button.getAttribute("data-payment-label") || paymentId;
  mandirRejectionPaymentId.value = paymentId;
  mandirRejectionLabel.textContent = `Reject ${paymentLabel}`;
  mandirRejectionReason.value = "";
  mandirRejectionDialog.showModal();
}

export async function submitMandirPublicPaymentRejection() {
  const paymentId = mandirRejectionPaymentId.value;
  const reason = mandirRejectionReason.value.trim().replace(/\s+/g, " ");
  if (reason.length < 3) {
    mandirRejectionReason.setCustomValidity("Enter a rejection reason.");
    mandirRejectionReason.reportValidity();
    return;
  }
  mandirRejectionReason.setCustomValidity("");
  const result = await apiRequest("mandirmitra", `/api/v1/public-payments/${encodeURIComponent(paymentId)}/reject`, {
    method: "PATCH",
    body: JSON.stringify({ reason }),
  });
  renderJson(apiOutput, { reject_mandir_public_payment: result });
  mandirRejectionDialog.close();
  await loadMandirDashboard();
}

export function openMandirCorrectionDialog(button) {
  const paymentId = button.getAttribute("data-payment-id") || "";
  if (!paymentId) {
    return;
  }
  const paymentLabel = button.getAttribute("data-payment-label") || paymentId;
  mandirCorrectionPaymentId.value = paymentId;
  mandirCorrectionLabel.textContent = `Correct ${paymentLabel}`;
  mandirCorrectionAmount.value = button.getAttribute("data-payment-amount") || "";
  mandirCorrectionPhone.value = button.getAttribute("data-devotee-phone") || "";
  const type = button.getAttribute("data-payment-type") || "donation";
  mandirCorrectionType.value = ["donation", "seva"].includes(type) ? type : "donation";
  mandirCorrectionPurpose.value = button.getAttribute("data-payment-purpose") || "";
  mandirCorrectionDialog.showModal();
}

export async function submitMandirPublicPaymentCorrection() {
  const paymentId = mandirCorrectionPaymentId.value;
  const amount = Number(mandirCorrectionAmount.value || 0);
  const phone = mandirCorrectionPhone.value.replace(/\D/g, "").slice(-10);
  const purpose = mandirCorrectionPurpose.value.trim().replace(/\s+/g, " ");
  if (!paymentId || amount <= 0 || phone.length !== 10 || purpose.length < 1) {
    mandirCorrectionForm.reportValidity();
    return;
  }

  const result = await apiRequest("mandirmitra", `/api/v1/public-payments/${encodeURIComponent(paymentId)}/correction`, {
    method: "PATCH",
    body: JSON.stringify({
      amount,
      devotee_phone: phone,
      payment_type: mandirCorrectionType.value,
      seva_name: purpose,
    }),
  });
  renderJson(apiOutput, { correct_mandir_public_payment: result });
  mandirCorrectionDialog.close();
  await loadMandirDashboard();
}

export async function downloadMandirReceipt(button) {
  const receiptUrl = button.getAttribute("data-receipt-url") || "";
  if (!receiptUrl) {
    return;
  }
  const filename = button.getAttribute("data-receipt-filename") || "mandir-receipt.pdf";
  const result = await downloadApiFile("mandirmitra", receiptUrl, filename, { timeoutMs: 15000 });
  renderJson(apiOutput, { download_mandir_receipt: result });
}

export function closeReceiptPreview() {
  receiptPreviewDialog.close();
  receiptPreviewFrame.removeAttribute("src");
  if (getActiveReceiptPreviewObjectUrl()) {
    window.URL.revokeObjectURL(getActiveReceiptPreviewObjectUrl());
    setActiveReceiptPreviewObjectUrl("");
  }
}

export async function previewMandirReceipt(button) {
  const receiptUrl = button.getAttribute("data-receipt-url") || "";
  if (!receiptUrl) {
    return;
  }
  const receiptLabel = button.getAttribute("data-receipt-label") || "Receipt PDF";
  const result = await fetchApiFileObjectUrl("mandirmitra", receiptUrl, { timeoutMs: 15000 });
  renderJson(apiOutput, { preview_mandir_receipt: result.ok ? { ...result, payload: { content_type: result.payload.content_type } } : result });
  if (!result.ok) {
    return;
  }
  if (getActiveReceiptPreviewObjectUrl()) {
    window.URL.revokeObjectURL(getActiveReceiptPreviewObjectUrl());
  }
  setActiveReceiptPreviewObjectUrl(result.payload.object_url);
  receiptPreviewLabel.textContent = receiptLabel;
  receiptPreviewFrame.src = getActiveReceiptPreviewObjectUrl();
  receiptPreviewDialog.showModal();
}

export function openMandirCancelReceiptDialog(button) {
  const cancelUrl = button.getAttribute("data-cancel-url") || "";
  if (!cancelUrl) {
    return;
  }
  const receiptLabel = button.getAttribute("data-receipt-label") || "receipt";
  mandirCancelReceiptUrl.value = cancelUrl;
  mandirCancelReceiptLabel.textContent = `Reverse ${receiptLabel} without editing the original receipt.`;
  mandirCancelReceiptReason.value = "";
  mandirCancelRefundMode.value = "";
  mandirCancelRefundReference.value = "";
  mandirCancelReceiptSubmit.disabled = false;
  mandirCancelReceiptSubmit.textContent = "Reverse Receipt";
  mandirCancelReceiptDialog.showModal();
  mandirCancelReceiptReason.focus();
}

export async function submitMandirCancelReceipt() {
  const cancelUrl = mandirCancelReceiptUrl.value;
  const receiptLabel = mandirCancelReceiptLabel.textContent || "Receipt";
  const reason = String(mandirCancelReceiptReason.value || "").trim().replace(/\s+/g, " ");
  if (reason.length < 3) {
    return;
  }
  const refundMode = String(mandirCancelRefundMode.value || "").trim().replace(/\s+/g, " ");
  const refundReference = String(mandirCancelRefundReference.value || "").trim().replace(/\s+/g, " ");
  mandirCancelReceiptSubmit.disabled = true;
  mandirCancelReceiptSubmit.textContent = "Reversing...";
  mandirCancelReceiptDialog.close();
  setMandirFormResult(null, "Cancelling receipt", receiptLabel);
  await loadMandirDashboard();
  const result = await apiRequest("mandirmitra", cancelUrl, {
    method: "POST",
    timeoutMs: 20000,
    body: JSON.stringify({
      reason,
      refund_mode: refundMode || null,
      refund_reference: refundReference || null,
    }),
  });
  renderJson(apiOutput, { cancel_mandir_receipt: result });
  if (result.ok) {
    setMandirFormResult(true, "Receipt cancelled", result.payload?.receipt_number || receiptLabel);
    await loadMandirDashboard();
  } else {
    setMandirFormResult(false, "Receipt cancellation failed", result.payload?.detail || "Unable to cancel receipt");
    await loadMandirDashboard();
  }
  dashboardPreview.querySelector("#mandir-operation-result")?.scrollIntoView({ behavior: "smooth", block: "center" });
  mandirCancelReceiptSubmit.disabled = false;
  mandirCancelReceiptSubmit.textContent = "Reverse Receipt";
}

export function compactOptionalPhone(value) {
  return String(value || "").replace(/\D/g, "").slice(-10);
}

export function formNumber(formData, key) {
  return Number(formData.get(key) || 0);
}

export function formText(formData, key) {
  return String(formData.get(key) || "").trim().replace(/\s+/g, " ");
}

export function setMandirFormResult(ok, title, detail) {
  setLastMandirFormResult({ ok, title, detail });
}

export function mandirReceiptFromCreatePayload(payload, fallbackType = "receipt") {
  const receiptPdfUrl = String(payload?.receipt_pdf_url || "").trim();
  if (!receiptPdfUrl) {
    return null;
  }
  const receiptNumber = String(payload?.receipt_number || payload?.donation_id || payload?.id || fallbackType).trim();
  const safeReceiptNumber = receiptNumber.replace(/[^a-z0-9_-]+/gi, "_") || fallbackType;
  return {
    receipt_pdf_url: receiptPdfUrl,
    receipt_number: receiptNumber,
    source_id: payload?.donation_id || payload?.id,
    source_type: fallbackType,
    filename: `${safeReceiptNumber}.pdf`,
  };
}

export async function submitMandirDonationForm(form) {
  const formData = new FormData(form);
  const amount = formNumber(formData, "amount");
  const paymentAccountId = formText(formData, "payment_account_id");
  const payload = {
    devotee_name: formText(formData, "devotee_name"),
    devotee_phone: compactOptionalPhone(formData.get("devotee_phone")),
    amount,
    category: formText(formData, "category") || "General Donation",
    donation_type: formText(formData, "donation_type") || "cash",
    payment_mode: formText(formData, "payment_mode") || "Cash",
  };
  ["event_name", "in_kind_item_name", "in_kind_item_type", "in_kind_quantity", "in_kind_valuation_basis"].forEach((key) => {
    const value = formText(formData, key);
    if (value) {
      payload[key] = value;
    }
  });
  if (paymentAccountId) {
    payload.payment_account_id = paymentAccountId;
  }
  payload.request_80g = formData.has("request_80g");
  payload.is_foreign_contribution = formData.has("is_foreign_contribution");
  payload.foreign_source_declaration = formData.has("foreign_source_declaration");
  ["donor_pan", "donor_country"].forEach((key) => {
    const value = formText(formData, key);
    if (value) {
      payload[key] = value;
    }
  });

  const result = await apiRequest("mandirmitra", "/api/v1/donations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  renderJson(apiOutput, { create_mandir_donation: result });
  if (result.ok) {
    setLastMandirReceipt(mandirReceiptFromCreatePayload(result.payload, "donation") || getLastMandirReceipt());
    setMandirFormResult(true, "Donation created", result.payload?.receipt_number || result.payload?.donation_id || "Receipt generated");
    form.reset();
  } else {
    setMandirFormResult(false, "Donation failed", result.payload?.detail || "Unable to create donation");
  }
  await loadMandirDashboard();
}

export async function submitMandirComplianceForm(form) {
  const formData = new FormData(form);
  const payload = {
    enable_80g: formData.has("enable_80g"),
    institution_pan: formText(formData, "institution_pan").toUpperCase(),
    approval_number: formText(formData, "approval_number"),
    approval_valid_from: formText(formData, "approval_valid_from"),
    approval_valid_to: formText(formData, "approval_valid_to"),
    certificate_label: formText(formData, "certificate_label") || "Donation certificate",
    cash_eligibility_limit: formText(formData, "cash_eligibility_limit"),
    cash_rule_effective_from: formText(formData, "cash_rule_effective_from"),
    receipt_disclaimer: formText(formData, "receipt_disclaimer"),
    enable_fcra: formData.has("enable_fcra"),
    fcra_registration_type: formText(formData, "fcra_registration_type") || "registration",
    fcra_registration_number: formText(formData, "fcra_registration_number"),
    fcra_valid_from: formText(formData, "fcra_valid_from"),
    fcra_valid_to: formText(formData, "fcra_valid_to"),
    fcra_designated_account_id: formText(formData, "fcra_designated_account_id"),
  };
  const result = await apiRequest("mandirmitra", "/api/v1/compliance/donations/config", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  renderJson(apiOutput, { save_mandir_compliance_config: result });
  if (result.ok) {
    setLastMandirComplianceConfig(result.payload || { enable_80g: false, enable_fcra: false });
    setMandirFormResult(true, "Compliance configuration saved", "80G/FCRA controls remain governed by tenant approval evidence.");
  } else {
    setMandirFormResult(false, "Compliance configuration failed", result.payload?.detail || "Unable to save compliance settings");
  }
  await loadMandirDashboard();
}

export async function submitMandirSevaForm(form) {
  const formData = new FormData(form);
  const paymentAccountId = formText(formData, "payment_account_id");
  const payload = {
    devotee_name: formText(formData, "devotee_name"),
    devotee_phone: compactOptionalPhone(formData.get("devotee_phone")),
    seva_name: formText(formData, "seva_name"),
    booking_date: formText(formData, "booking_date") || todayIsoDate(),
    amount_paid: formNumber(formData, "amount"),
    payment_mode: formText(formData, "payment_mode") || "Cash",
  };
  if (paymentAccountId) {
    payload.payment_account_id = paymentAccountId;
  }

  const result = await apiRequest("mandirmitra", "/api/v1/sevas/bookings", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  renderJson(apiOutput, { create_mandir_seva_booking: result });
  if (result.ok) {
    setLastMandirReceipt(mandirReceiptFromCreatePayload(result.payload, "seva") || getLastMandirReceipt());
    setMandirFormResult(true, "Seva booking created", result.payload?.receipt_number || result.payload?.id || "Receipt generated");
    form.reset();
  } else {
    setMandirFormResult(false, "Seva booking failed", result.payload?.detail || "Unable to create seva booking");
  }
  await loadMandirDashboard();
}

export async function submitMandirExpenseForm(form) {
  const formData = new FormData(form);
  const amount = formNumber(formData, "amount");
  const narration = formText(formData, "narration");
  const expenseAccountId = formText(formData, "expense_account_id");
  const paymentAccountId = formText(formData, "payment_account_id");
  const entryPayload = {
    entry_date: formText(formData, "entry_date") || todayIsoDate(),
    narration,
    reference_type: "expense",
    journal_lines: [
      {
        account_id: expenseAccountId,
        debit_amount: amount,
        credit_amount: 0,
        description: narration,
      },
      {
        account_id: paymentAccountId,
        debit_amount: 0,
        credit_amount: amount,
        description: narration,
      },
    ],
  };

  const createResult = await apiRequest("mandirmitra", "/api/v1/journal-entries", {
    method: "POST",
    body: JSON.stringify(entryPayload),
  });
  if (!createResult.ok) {
    renderJson(apiOutput, { create_mandir_expense: createResult });
    setMandirFormResult(false, "Expense failed", createResult.payload?.detail || "Unable to create expense draft");
    await loadMandirDashboard();
    return;
  }

  const entryId = createResult.payload?.id;
  const postResult = await apiRequest("mandirmitra", `/api/v1/journal-entries/${encodeURIComponent(entryId)}/post`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  renderJson(apiOutput, { create_mandir_expense: createResult, post_mandir_expense: postResult });
  if (postResult.ok) {
    if (postResult.payload) {
      getMandirReportState().expenses = [
        postResult.payload,
        ...getMandirReportState().expenses.filter((expense) => String(expense.id || "") !== String(postResult.payload.id || "")),
      ].slice(0, 25);
    }
    setMandirFormResult(true, "Expense posted", postResult.payload?.entry_number || entryId || "Journal entry posted");
    form.reset();
  } else {
    setMandirFormResult(false, "Expense post failed", postResult.payload?.detail || "Expense draft was created but not posted");
  }
  await loadMandirDashboard();
}

export async function submitMandirCreateForm(form) {
  const formType = form.getAttribute("data-mandir-create-form") || "";
  if (!form.reportValidity()) {
    return;
  }
  if (formType === "donation") {
    await submitMandirDonationForm(form);
  } else if (formType === "seva") {
    await submitMandirSevaForm(form);
  } else if (formType === "expense") {
    await submitMandirExpenseForm(form);
  }
}

export function readMandirListFilterValues(kind) {
  const panel = dashboardPreview.querySelector(`[data-mandir-list="${kind}"]`);
  if (!panel) {
    return null;
  }
  const formData = new FormData();
  panel.querySelectorAll("input[name], select[name]").forEach((input) => {
    formData.set(input.name, input.value.trim());
  });
  if (kind === "payments") {
    return {
      q: String(formData.get("q") || ""),
      status: String(formData.get("status") || "pending"),
      payment_type: String(formData.get("payment_type") || ""),
    };
  }
  if (kind === "exceptions") {
    return {
      q: String(formData.get("q") || ""),
      reason: String(formData.get("reason") || ""),
      status: String(formData.get("status") || ""),
      payment_type: String(formData.get("payment_type") || ""),
    };
  }
  return {
    q: String(formData.get("q") || ""),
    from_date: String(formData.get("from_date") || ""),
    to_date: String(formData.get("to_date") || ""),
    payment_mode: kind === "donations" ? String(formData.get("payment_mode") || "") : "",
    status: kind === "sevas" ? String(formData.get("status") || "") : "",
  };
}

export async function applyMandirListFilter(kind) {
  if (!getMandirListState()[kind]) {
    return;
  }
  const values = readMandirListFilterValues(kind);
  if (!values) {
    return;
  }
  getMandirListState()[kind] = {
    ...getMandirListState()[kind],
    ...values,
    offset: 0,
  };
  await loadMandirDashboard();
}

export async function resetMandirListFilter(kind) {
  if (!getMandirListState()[kind]) {
    return;
  }
  Object.keys(getMandirListState()[kind]).forEach((key) => {
    getMandirListState()[kind][key] = key === "offset" ? 0 : "";
  });
  if (kind === "payments") {
    getMandirListState().payments.status = "pending";
  }
  await loadMandirDashboard();
}

export async function pageMandirList(kind, direction) {
  if (!getMandirListState()[kind]) {
    return;
  }
  const currentOffset = Number(getMandirListState()[kind].offset || 0);
  const delta = direction === "prev" ? -getMandirListPageSize() : getMandirListPageSize();
  getMandirListState()[kind].offset = Math.max(0, currentOffset + delta);
  await loadMandirDashboard();
}

export async function setMandirWorkspace(view) {
  const allowedViews = new Set([
    "overview",
    "donations",
    "sevas",
    "book-sevas",
    "seva-bookings",
    "seva-management",
    "reschedule-approval",
    "devotees",
    "payments",
    "exceptions",
    "receipts",
    "panchang",
    "reports",
    "accounting",
    "settings",
    "implementation",
    "platform-owners",
  ]);
  if (!allowedViews.has(view)) {
    return;
  }
  setActiveMandirWorkspace(view);
  syncMandirNavActiveState();
  await loadMandirDashboard();
  document.querySelector(".content")?.scrollTo({ top: 0, behavior: "smooth" });
}

