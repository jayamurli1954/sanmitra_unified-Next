// ====================================================================
// SECTION: MANDIR — receipt / donation / seva tables
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initMandirTables(...).
// ====================================================================

export const MANDIR_LIST_PAGE_SIZE = 8;

export const mandirListState = {
  donations: {
    offset: 0,
    q: "",
    from_date: "",
    to_date: "",
    payment_mode: "",
  },
  sevas: {
    offset: 0,
    q: "",
    from_date: "",
    to_date: "",
    status: "",
  },
  payments: {
    offset: 0,
    q: "",
    status: "pending",
    payment_type: "",
  },
  exceptions: {
    offset: 0,
    q: "",
    reason: "",
    status: "",
    payment_type: "",
  },
};

/** @type {{ escapeHtml: (v: string) => string, formatCurrency: (v: number | string) => string } | null} */
let deps = null;

export function initMandirTables({ escapeHtml, formatCurrency }) {
  deps = { escapeHtml, formatCurrency };
}

function requireDeps() {
  if (!deps) {
    throw new Error("initMandirTables() must be called before using Mandir table renderers");
  }
  return deps;
}

function escapeHtml(value) {
  return requireDeps().escapeHtml(value);
}

function formatCurrency(value) {
  return requireDeps().formatCurrency(value);
}

export function renderMandirPublicPaymentsTable(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `<p class="muted">No pending public payments.</p>`;
  }
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Payment</th>
            <th>Type</th>
            <th>Devotee</th>
            <th class="amount">Amount</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows.slice(0, 8).map((row) => {
            const paymentId = row.id || row.full_payment_id || row.payment_id || "";
            const shortId = String(row.payment_id || paymentId).slice(0, 8).toUpperCase();
            return `
              <tr>
                <td>${escapeHtml(shortId)}</td>
                <td>${escapeHtml(row.payment_type || row.payment_purpose || "payment")}</td>
                <td>${escapeHtml(row.devotee_name || row.name || "Devotee")}</td>
                <td class="amount">${escapeHtml(formatCurrency(row.amount || row.amount_paid || 0))}</td>
                <td>
                  <button
                    class="secondary"
                    type="button"
                    data-mandir-action="verify-public-payment"
                    data-payment-id="${escapeHtml(paymentId)}"
                    data-payment-label="${escapeHtml(shortId)}"
                    data-payment-type="${escapeHtml(row.payment_type || row.payment_purpose || "payment")}"
                    data-devotee-name="${escapeHtml(row.devotee_name || row.name || "Devotee")}"
                    data-payment-amount="${escapeHtml(row.amount || row.amount_paid || 0)}"
                  >Verify</button>
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

export function formatMandirExceptionReasons(reasons = []) {
  if (!Array.isArray(reasons) || reasons.length === 0) {
    return "needs review";
  }
  return reasons.map((reason) => String(reason).replace(/_/g, " ")).join(", ");
}

export function renderMandirExceptionsTable(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `<p class="muted">No payment exceptions returned.</p>`;
  }
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Payment</th>
            <th>Reason</th>
            <th>Devotee</th>
            <th class="amount">Amount</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows.slice(0, 8).map((row) => {
            const paymentId = row.id || row.full_payment_id || row.payment_id || "";
            const shortId = String(row.payment_id || paymentId).slice(0, 8).toUpperCase();
            const canVerify = Number(row.amount || 0) > 0 && row.devotee_phone;
            return `
              <tr>
                <td>${escapeHtml(shortId)}</td>
                <td>${escapeHtml(formatMandirExceptionReasons(row.exception_reasons))}</td>
                <td>${escapeHtml(row.devotee_name || row.name || "Devotee")}</td>
                <td class="amount">${escapeHtml(formatCurrency(row.amount || row.amount_paid || 0))}</td>
                <td>
                  <div class="action-row">
                    ${canVerify ? `
                      <button
                        class="secondary"
                        type="button"
                        data-mandir-action="verify-public-payment"
                        data-payment-id="${escapeHtml(paymentId)}"
                        data-payment-label="${escapeHtml(shortId)}"
                        data-payment-type="${escapeHtml(row.payment_type || row.payment_purpose || "payment")}"
                        data-devotee-name="${escapeHtml(row.devotee_name || row.name || "Devotee")}"
                        data-payment-amount="${escapeHtml(row.amount || row.amount_paid || 0)}"
                      >Verify</button>
                    ` : `
                      <button
                        class="secondary"
                        type="button"
                        data-mandir-action="correct-public-payment"
                        data-payment-id="${escapeHtml(paymentId)}"
                        data-payment-label="${escapeHtml(shortId)}"
                        data-payment-type="${escapeHtml(row.payment_type || "donation")}"
                        data-devotee-phone="${escapeHtml(row.devotee_phone || "")}"
                        data-payment-purpose="${escapeHtml(row.seva_name || row.category || "")}"
                        data-payment-amount="${escapeHtml(row.amount || row.amount_paid || 0)}"
                      >Correct</button>
                    `}
                    <button
                      class="secondary"
                      type="button"
                      data-mandir-action="reject-public-payment"
                      data-payment-id="${escapeHtml(paymentId)}"
                      data-payment-label="${escapeHtml(shortId)}"
                    >Reject</button>
                  </div>
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

export function mandirReceiptRowsFromLists(donations = [], sevaBookings = []) {
  const donationRows = donations.map((row) => ({
    type: "Donation",
    id: row.donation_id || row.id || "",
    receipt_number: row.receipt_number || row.donation_id || row.id || "",
    party: row.devotee_name || row.donor_name || row.name || "Devotee",
    date: row.donation_date || row.created_at || "",
    amount: row.amount || 0,
    receipt_pdf_url: row.receipt_pdf_url,
    status: row.status || "posted",
    cancel_url: row.donation_id || row.id ? `/api/v1/donations/${encodeURIComponent(row.donation_id || row.id)}/cancel` : "",
  }));
  const sevaRows = sevaBookings.map((row) => ({
    type: "Seva",
    id: row.id || row.booking_id || "",
    receipt_number: row.receipt_number || row.id || row.booking_id || "",
    party: row.devotee_name || row.devotee_names || row.name || "Devotee",
    date: row.booking_date || row.created_at || "",
    amount: row.amount_paid || row.amount || 0,
    receipt_pdf_url: row.receipt_pdf_url,
    status: row.status || "confirmed",
    cancel_url: row.id || row.booking_id ? `/api/v1/sevas/bookings/${encodeURIComponent(row.id || row.booking_id)}/cancel` : "",
  }));
  return [...donationRows, ...sevaRows]
    .filter((row) => row.receipt_pdf_url)
    .sort((a, b) => String(b.date || "").localeCompare(String(a.date || "")))
    .slice(0, 8);
}

export function renderMandirReceiptHistoryTable(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `<p class="muted">No recent receipts returned.</p>`;
  }
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Receipt</th>
            <th>Type</th>
            <th>Devotee</th>
            <th class="amount">Amount</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((row) => {
            const receiptLabel = row.receipt_number || row.id || "Receipt";
            const filename = `${String(receiptLabel).replace(/[^a-z0-9_-]+/gi, "_") || "receipt"}.pdf`;
            const status = String(row.status || "posted").toLowerCase();
            const reversed = status === "reversed" || status === "cancelled";
            return `
              <tr>
                <td>
                  <strong>${escapeHtml(receiptLabel)}</strong>
                  <small><span class="pill ${reversed ? "warn" : "ok"}">${escapeHtml(status)}</span></small>
                </td>
                <td>${escapeHtml(row.type)}</td>
                <td>${escapeHtml(row.party)}</td>
                <td class="amount">${escapeHtml(formatCurrency(row.amount))}</td>
                <td>
                  <div class="action-row">
                    <button
                      class="secondary"
                      type="button"
                      data-mandir-action="preview-receipt"
                      data-receipt-url="${escapeHtml(row.receipt_pdf_url)}"
                      data-receipt-label="${escapeHtml(receiptLabel)}"
                    >Preview</button>
                    <button
                      type="button"
                      data-mandir-action="download-receipt"
                      data-receipt-url="${escapeHtml(row.receipt_pdf_url)}"
                      data-receipt-filename="${escapeHtml(filename)}"
                    >Download</button>
                    ${row.cancel_url && !reversed ? `
                      <button
                        class="danger"
                        type="button"
                        data-mandir-action="cancel-receipt"
                        data-cancel-url="${escapeHtml(row.cancel_url)}"
                        data-receipt-label="${escapeHtml(receiptLabel)}"
                      >Cancel</button>
                    ` : reversed ? `<button class="secondary" type="button" disabled>Reversed</button>` : ""}
                  </div>
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

export function renderMandirReceiptActions(row, label) {
  if (!row.receipt_pdf_url) {
    return `<span class="muted">No receipt</span>`;
  }
  const receiptLabel = label || row.receipt_number || row.id || "Receipt";
  const filename = `${String(receiptLabel).replace(/[^a-z0-9_-]+/gi, "_") || "receipt"}.pdf`;
  const status = String(row.status || "").toLowerCase();
  const reversed = status === "reversed" || status === "cancelled";
  const donationId = row.donation_id || (row.receipt_pdf_url?.includes("/donations/") ? row.id : "");
  const bookingId = row.booking_id || (row.receipt_pdf_url?.includes("/sevas/bookings/") ? row.id : "");
  const cancelUrl = donationId
    ? `/api/v1/donations/${encodeURIComponent(donationId)}/cancel`
    : (bookingId ? `/api/v1/sevas/bookings/${encodeURIComponent(bookingId)}/cancel` : "");
  return `
    <div class="action-row">
      <button
        class="secondary"
        type="button"
        data-mandir-action="preview-receipt"
        data-receipt-url="${escapeHtml(row.receipt_pdf_url)}"
        data-receipt-label="${escapeHtml(receiptLabel)}"
      >Preview</button>
      <button
        type="button"
        data-mandir-action="download-receipt"
        data-receipt-url="${escapeHtml(row.receipt_pdf_url)}"
        data-receipt-filename="${escapeHtml(filename)}"
      >Download</button>
      ${cancelUrl && !reversed ? `
        <button
          class="danger"
          type="button"
          data-mandir-action="cancel-receipt"
          data-cancel-url="${escapeHtml(cancelUrl)}"
          data-receipt-label="${escapeHtml(receiptLabel)}"
        >Cancel</button>
      ` : reversed ? `<button class="secondary" type="button" disabled>Reversed</button>` : ""}
    </div>
  `;
}

export function renderMandirDonationsTable(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `<p class="muted">No recent donations returned.</p>`;
  }
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Devotee</th>
            <th>Category</th>
            <th class="amount">Amount</th>
            <th>Receipt</th>
          </tr>
        </thead>
        <tbody>
          ${rows.slice(0, 8).map((row) => {
            const receiptLabel = row.receipt_number || row.donation_id || row.id || "Receipt";
            const itemParts = [row.in_kind_item_name, row.in_kind_quantity].filter(Boolean).join(" / ");
            const typeLabel = row.donation_type === "in_kind" ? `In-kind${itemParts ? `: ${itemParts}` : ""}` : "Cash";
            return `
              <tr>
                <td>${escapeHtml(String(row.donation_date || row.created_at || "").slice(0, 10))}</td>
                <td>${escapeHtml(row.devotee_name || row.donor_name || row.name || "Devotee")}</td>
                <td>
                  <strong>${escapeHtml(row.category || "Donation")}</strong>
                  <small>${escapeHtml(typeLabel)}</small>
                </td>
                <td class="amount">${escapeHtml(formatCurrency(row.amount))}</td>
                <td>${renderMandirReceiptActions(row, receiptLabel)}</td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

export function renderMandirSevaBookingsTable(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `<p class="muted">No recent seva bookings returned.</p>`;
  }
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Devotee</th>
            <th>Seva</th>
            <th class="amount">Amount</th>
            <th>Receipt</th>
          </tr>
        </thead>
        <tbody>
          ${rows.slice(0, 8).map((row) => {
            const receiptLabel = row.receipt_number || row.id || row.booking_id || "Receipt";
            return `
              <tr>
                <td>${escapeHtml(String(row.booking_date || row.created_at || "").slice(0, 10))}</td>
                <td>${escapeHtml(row.devotee_name || row.devotee_names || row.name || "Devotee")}</td>
                <td>${escapeHtml(row.seva_name || row.seva || "Seva")}</td>
                <td class="amount">${escapeHtml(formatCurrency(row.amount_paid || row.amount))}</td>
                <td>${renderMandirReceiptActions(row, receiptLabel)}</td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

export function renderMandirWorkspaceTabs(activeWorkspace) {
  const tabs = [
    ["overview", "Overview"],
    ["donations", "Donations"],
    ["sevas", "Sevas"],
    ["payments", "Public Payments"],
    ["exceptions", "Exceptions"],
    ["receipts", "Receipts"],
    ["panchang", "Panchang"],
    ["reports", "Reports"],
    ["accounting", "Accounting"],
  ];
  return `
    <div class="workspace-tabs mandir-workspace-tabs" aria-label="MandirMitra workspace views">
      ${tabs.map(([key, label]) => `
        <button
          class="${activeWorkspace === key ? "active" : ""}"
          type="button"
          data-mandir-action="workspace-view"
          data-workspace-view="${escapeHtml(key)}"
        >${escapeHtml(label)}</button>
      `).join("")}
    </div>
  `;
}

export function renderMandirListFilters(kind, rowsLength) {
  const state = mandirListState[kind] || {};
  const isDonations = kind === "donations";
  const offset = Number(state.offset || 0);
  const startRow = rowsLength > 0 ? offset + 1 : 0;
  const endRow = rowsLength > 0 ? offset + rowsLength : 0;
  const nextDisabled = rowsLength < MANDIR_LIST_PAGE_SIZE ? "disabled" : "";
  const prevDisabled = offset <= 0 ? "disabled" : "";
  const modeOptions = isDonations
    ? [
        ["", "All modes"],
        ["cash", "Cash"],
        ["bank", "Bank"],
        ["upi", "UPI"],
      ]
    : [
        ["", "All statuses"],
        ["confirmed", "Confirmed"],
        ["cancelled", "Cancelled"],
        ["reschedule_pending", "Reschedule pending"],
      ];
  const selectName = isDonations ? "payment_mode" : "status";
  const selectLabel = isDonations ? "Mode" : "Status";

  return `
    <div class="list-filter-panel" data-mandir-list="${escapeHtml(kind)}">
      <div class="list-filter-bar">
        <label class="field">
          <span>Search</span>
          <input name="q" type="search" value="${escapeHtml(state.q || "")}" placeholder="${isDonations ? "Devotee or receipt" : "Devotee or seva"}">
        </label>
        <label class="field">
          <span>From</span>
          <input name="from_date" type="date" value="${escapeHtml(state.from_date || "")}">
        </label>
        <label class="field">
          <span>To</span>
          <input name="to_date" type="date" value="${escapeHtml(state.to_date || "")}">
        </label>
        <label class="field">
          <span>${selectLabel}</span>
          <select name="${selectName}">
            ${modeOptions.map(([value, label]) => `
              <option value="${escapeHtml(value)}" ${String(state[selectName] || "") === value ? "selected" : ""}>${escapeHtml(label)}</option>
            `).join("")}
          </select>
        </label>
        <div class="list-filter-actions">
          <button type="button" data-mandir-action="apply-list-filter" data-list-kind="${escapeHtml(kind)}">Apply</button>
          <button class="secondary" type="button" data-mandir-action="reset-list-filter" data-list-kind="${escapeHtml(kind)}">Reset</button>
        </div>
      </div>
      <div class="paging-row">
        <span class="muted">Showing ${escapeHtml(startRow)}-${escapeHtml(endRow)}</span>
        <button class="secondary" type="button" data-mandir-action="page-list" data-list-kind="${escapeHtml(kind)}" data-page-direction="prev" ${prevDisabled}>Prev</button>
        <button class="secondary" type="button" data-mandir-action="page-list" data-list-kind="${escapeHtml(kind)}" data-page-direction="next" ${nextDisabled}>Next</button>
      </div>
    </div>
  `;
}

export function renderMandirPublicPaymentFilters(rowsLength) {
  const state = mandirListState.payments;
  const offset = Number(state.offset || 0);
  const startRow = rowsLength > 0 ? offset + 1 : 0;
  const endRow = rowsLength > 0 ? offset + rowsLength : 0;
  const nextDisabled = rowsLength < MANDIR_LIST_PAGE_SIZE ? "disabled" : "";
  const prevDisabled = offset <= 0 ? "disabled" : "";
  const statusOptions = [
    ["pending", "Pending"],
    ["verified", "Verified"],
    ["rejected", "Rejected"],
    ["failed", "Failed"],
    ["all", "All statuses"],
  ];
  const typeOptions = [
    ["", "All types"],
    ["donation", "Donation"],
    ["seva", "Seva"],
  ];

  return `
    <div class="list-filter-panel" data-mandir-list="payments">
      <div class="list-filter-bar">
        <label class="field">
          <span>Search</span>
          <input name="q" type="search" value="${escapeHtml(state.q || "")}" placeholder="Devotee, phone, UTR, seva">
        </label>
        <label class="field">
          <span>Status</span>
          <select name="status">
            ${statusOptions.map(([value, label]) => `
              <option value="${escapeHtml(value)}" ${String(state.status || "pending") === value ? "selected" : ""}>${escapeHtml(label)}</option>
            `).join("")}
          </select>
        </label>
        <label class="field">
          <span>Type</span>
          <select name="payment_type">
            ${typeOptions.map(([value, label]) => `
              <option value="${escapeHtml(value)}" ${String(state.payment_type || "") === value ? "selected" : ""}>${escapeHtml(label)}</option>
            `).join("")}
          </select>
        </label>
        <div class="list-filter-actions">
          <button type="button" data-mandir-action="apply-list-filter" data-list-kind="payments">Apply</button>
          <button class="secondary" type="button" data-mandir-action="reset-list-filter" data-list-kind="payments">Reset</button>
        </div>
      </div>
      <div class="paging-row">
        <span class="muted">Showing ${escapeHtml(startRow)}-${escapeHtml(endRow)}</span>
        <button class="secondary" type="button" data-mandir-action="page-list" data-list-kind="payments" data-page-direction="prev" ${prevDisabled}>Prev</button>
        <button class="secondary" type="button" data-mandir-action="page-list" data-list-kind="payments" data-page-direction="next" ${nextDisabled}>Next</button>
      </div>
    </div>
  `;
}

export function renderMandirExceptionFilters(rowsLength) {
  const state = mandirListState.exceptions;
  const offset = Number(state.offset || 0);
  const startRow = rowsLength > 0 ? offset + 1 : 0;
  const endRow = rowsLength > 0 ? offset + rowsLength : 0;
  const nextDisabled = rowsLength < MANDIR_LIST_PAGE_SIZE ? "disabled" : "";
  const prevDisabled = offset <= 0 ? "disabled" : "";
  const reasonOptions = [
    ["", "All reasons"],
    ["stale_pending", "Stale pending"],
    ["invalid_amount", "Invalid amount"],
    ["missing_phone", "Missing phone"],
    ["invalid_payment_type", "Invalid type"],
    ["missing_seva", "Missing seva"],
    ["missing_donation_category", "Missing donation purpose"],
    ["failed", "Failed"],
    ["rejected", "Rejected"],
  ];
  const statusOptions = [
    ["", "All statuses"],
    ["pending", "Pending"],
    ["failed", "Failed"],
    ["rejected", "Rejected"],
    ["all", "All statuses"],
  ];
  const typeOptions = [
    ["", "All types"],
    ["donation", "Donation"],
    ["seva", "Seva"],
  ];

  return `
    <div class="list-filter-panel" data-mandir-list="exceptions">
      <div class="list-filter-bar">
        <label class="field">
          <span>Search</span>
          <input name="q" type="search" value="${escapeHtml(state.q || "")}" placeholder="Devotee, phone, UTR, seva">
        </label>
        <label class="field">
          <span>Reason</span>
          <select name="reason">
            ${reasonOptions.map(([value, label]) => `
              <option value="${escapeHtml(value)}" ${String(state.reason || "") === value ? "selected" : ""}>${escapeHtml(label)}</option>
            `).join("")}
          </select>
        </label>
        <label class="field">
          <span>Status</span>
          <select name="status">
            ${statusOptions.map(([value, label]) => `
              <option value="${escapeHtml(value)}" ${String(state.status || "") === value ? "selected" : ""}>${escapeHtml(label)}</option>
            `).join("")}
          </select>
        </label>
        <label class="field">
          <span>Type</span>
          <select name="payment_type">
            ${typeOptions.map(([value, label]) => `
              <option value="${escapeHtml(value)}" ${String(state.payment_type || "") === value ? "selected" : ""}>${escapeHtml(label)}</option>
            `).join("")}
          </select>
        </label>
        <div class="list-filter-actions">
          <button type="button" data-mandir-action="apply-list-filter" data-list-kind="exceptions">Apply</button>
          <button class="secondary" type="button" data-mandir-action="reset-list-filter" data-list-kind="exceptions">Reset</button>
        </div>
      </div>
      <div class="paging-row">
        <span class="muted">Showing ${escapeHtml(startRow)}-${escapeHtml(endRow)}</span>
        <button class="secondary" type="button" data-mandir-action="page-list" data-list-kind="exceptions" data-page-direction="prev" ${prevDisabled}>Prev</button>
        <button class="secondary" type="button" data-mandir-action="page-list" data-list-kind="exceptions" data-page-direction="next" ${nextDisabled}>Next</button>
      </div>
    </div>
  `;
}
