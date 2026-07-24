// ====================================================================
// SECTION: PARTIES / VOUCHERS LIST TABLE RENDERERS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initBusinessListTables(...).
// List filter apply/reset/page handlers remain in app.js.
// ====================================================================

/** @type {Record<string, Function> | null} */
let deps = null;

export function initBusinessListTables(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initBusinessListTables() must be called before using business list table helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function getBusinessListState() { return requireDeps().getBusinessListState(); }

export function renderBusinessPartiesTable(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `
      <div class="empty-state">
        <strong>No parties found</strong>
        <span>Add a customer or vendor to use party context in vouchers.</span>
      </div>
    `;
  }
  return `
    <div class="table-preview compact-table erp-table">
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>GSTIN</th>
            <th>Balance Source</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows.slice(0, 20).map((row) => {
            const isInactive = row.is_inactive || row.status === "inactive";
            const partyName = row.party_name || row.name || "Unnamed";
            const balanceSource = row.balance_source === "ledger_reports" ? "Ledger reports" : "Profile";
            return `
              <tr>
                <td>
                  <strong>${escapeHtml(partyName)}</strong>
                  <span class="row-subtext">${escapeHtml(row.party_code || row.code || "")}</span>
                </td>
                <td><span class="type-chip">${escapeHtml(row.party_type || row.type || "unknown")}</span></td>
                <td>${escapeHtml(row.gstin || "-")}</td>
                <td><span class="row-subtext">${escapeHtml(balanceSource)}</span></td>
                <td><span class="pill ${isInactive ? "warn" : "ok"}">${isInactive ? "Inactive" : "Active"}</span></td>
                <td>
                  <div class="action-row">
                    <button
                      class="secondary"
                      type="button"
                      data-business-action="edit-party"
                      data-party-id="${escapeHtml(row.party_id || row.id || "")}"
                      data-party-name="${escapeHtml(partyName)}"
                      data-party-type="${escapeHtml(row.party_type || "customer")}"
                      data-party-gstin="${escapeHtml(row.gstin || "")}"
                      data-party-pan="${escapeHtml(row.pan || "")}"
                      data-party-city="${escapeHtml(row.city || "")}"
                      data-party-state="${escapeHtml(row.state || "")}"
                      data-party-pincode="${escapeHtml(row.pincode || "")}"
                    >Edit</button>
                    ${!isInactive ? `
                      <button
                        class="secondary"
                        type="button"
                        data-business-action="deactivate-party"
                        data-party-id="${escapeHtml(row.party_id || row.id || "")}"
                      >Deactivate</button>
                    ` : ""}
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

export function renderBusinessPartiesListFilters(rowsLength) {
  const state = getBusinessListState().parties;
  const offset = Number(state.offset || 0);
  const startRow = rowsLength > 0 ? offset + 1 : 0;
  const endRow = rowsLength > 0 ? offset + Math.min(rowsLength, 20) : 0;
  const nextDisabled = rowsLength < 20 ? "disabled" : "";
  const prevDisabled = offset <= 0 ? "disabled" : "";

  return `
    <div class="list-filter-panel" data-business-list="parties">
      <div class="list-filter-bar">
        <label class="field">
          <span>Search</span>
          <input name="q" type="search" value="${escapeHtml(state.q || "")}" placeholder="Name or GSTIN">
        </label>
        <label class="field">
          <span>Type</span>
          <select name="party_type">
            <option value="">All types</option>
            <option value="customer" ${state.party_type === "customer" ? "selected" : ""}>Customer</option>
            <option value="vendor" ${state.party_type === "vendor" ? "selected" : ""}>Vendor</option>
            <option value="both" ${state.party_type === "both" ? "selected" : ""}>Both</option>
          </select>
        </label>
        <div class="list-filter-actions">
          <button type="button" data-business-action="apply-list-filter" data-list-kind="parties">Apply</button>
          <button class="secondary" type="button" data-business-action="reset-list-filter" data-list-kind="parties">Reset</button>
        </div>
      </div>
      <div class="paging-row">
        <span class="muted">Showing ${escapeHtml(startRow)}-${escapeHtml(endRow)}</span>
        <button class="secondary" type="button" data-business-action="page-list" data-list-kind="parties" data-page-direction="prev" ${prevDisabled}>Prev</button>
        <button class="secondary" type="button" data-business-action="page-list" data-list-kind="parties" data-page-direction="next" ${nextDisabled}>Next</button>
      </div>
    </div>
  `;
}


export function renderBusinessVouchersTable(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `
      <div class="empty-state">
        <strong>No vouchers posted yet</strong>
        <span>Post a balanced journal voucher after the chart of accounts is available.</span>
      </div>
    `;
  }
  return `
    <div class="table-preview compact-table erp-table">
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Reference</th>
            <th>Type</th>
            <th>Amount</th>
            <th>Narration</th>
            <th>Status</th>
            <th>Approval</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows.slice(0, 20).map((row) => {
            const status = row.status || "posted";
            const isReversed = status === "reversed";
            const approvalStatus = row.approval_status || "not_submitted";
            const reviewer = row.approval_decided_by || row.reviewed_by || "";
            const canApprove = status === "pending_approval";
            const canReject = status === "pending_approval";
            return `
              <tr>
                <td>${escapeHtml(String(row.entry_date || row.created_at || "").slice(0, 10))}</td>
                <td>${escapeHtml(row.reference || row.cheque_number || "-")}</td>
                <td>${escapeHtml(row.voucher_type || "journal")}</td>
                <td class="amount">${escapeHtml(formatCurrency(row.total_debit || row.amount || 0))}</td>
                <td>${escapeHtml((row.description || row.narration || "").slice(0, 40))}</td>
                <td><span class="pill ${isReversed ? "warn" : "ok"}">${escapeHtml(status)}</span></td>
                <td>
                  <span class="pill ${approvalStatus === "rejected" ? "warn" : approvalStatus === "approved" ? "ok" : ""}">${escapeHtml(approvalStatus)}</span>
                  <span class="row-subtext">${escapeHtml(reviewer || "Unreviewed")}</span>
                </td>
                <td>
                  <div class="action-row">
                    ${canApprove ? `
                      <button
                        type="button"
                        data-business-action="review-voucher-approve"
                        data-voucher-id="${escapeHtml(row.voucher_id || row.id || "")}"
                      >Approve</button>
                    ` : ""}
                    ${canReject ? `
                      <button
                        class="secondary"
                        type="button"
                        data-business-action="review-voucher-reject"
                        data-voucher-id="${escapeHtml(row.voucher_id || row.id || "")}"
                      >Reject</button>
                    ` : ""}
                    ${!isReversed ? `
                      <button
                        class="secondary"
                        type="button"
                        data-business-action="reverse-voucher"
                        data-voucher-id="${escapeHtml(row.voucher_id || row.id || "")}"
                      >Reverse</button>
                    ` : `
                      <button class="secondary" type="button" disabled>Reversed</button>
                    `}
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

export function renderBusinessVouchersListFilters(rowsLength) {
  const state = getBusinessListState().vouchers;
  const offset = Number(state.offset || 0);
  const startRow = rowsLength > 0 ? offset + 1 : 0;
  const endRow = rowsLength > 0 ? offset + Math.min(rowsLength, 20) : 0;
  const nextDisabled = rowsLength < 20 ? "disabled" : "";
  const prevDisabled = offset <= 0 ? "disabled" : "";

  return `
    <div class="list-filter-panel" data-business-list="vouchers">
      <div class="list-filter-bar">
        <label class="field">
          <span>Type</span>
          <select name="voucher_type">
            <option value="">All types</option>
            <option value="payment" ${state.voucher_type === "payment" ? "selected" : ""}>Payment</option>
            <option value="receipt" ${state.voucher_type === "receipt" ? "selected" : ""}>Receipt</option>
            <option value="contra" ${state.voucher_type === "contra" ? "selected" : ""}>Contra</option>
            <option value="journal" ${state.voucher_type === "journal" ? "selected" : ""}>Journal</option>
          </select>
        </label>
        <label class="field">
          <span>Status</span>
          <select name="status">
            <option value="">All statuses</option>
            <option value="posted" ${state.status === "posted" ? "selected" : ""}>Posted</option>
            <option value="reversed" ${state.status === "reversed" ? "selected" : ""}>Reversed</option>
            <option value="posting" ${state.status === "posting" ? "selected" : ""}>Posting</option>
          </select>
        </label>
        <label class="field">
          <span>Approval</span>
          <select name="approval_status">
            <option value="">All approvals</option>
            <option value="auto_posted" ${state.approval_status === "auto_posted" ? "selected" : ""}>Auto-posted</option>
            <option value="approved" ${state.approval_status === "approved" ? "selected" : ""}>Approved</option>
            <option value="rejected" ${state.approval_status === "rejected" ? "selected" : ""}>Rejected</option>
            <option value="pending_approval" ${state.approval_status === "pending_approval" ? "selected" : ""}>Pending approval</option>
          </select>
        </label>
        <div class="list-filter-actions">
          <button type="button" data-business-action="apply-list-filter" data-list-kind="vouchers">Apply</button>
          <button class="secondary" type="button" data-business-action="reset-list-filter" data-list-kind="vouchers">Reset</button>
        </div>
      </div>
      <div class="paging-row">
        <span class="muted">Showing ${escapeHtml(startRow)}-${escapeHtml(endRow)}</span>
        <button class="secondary" type="button" data-business-action="page-list" data-list-kind="vouchers" data-page-direction="prev" ${prevDisabled}>Prev</button>
        <button class="secondary" type="button" data-business-action="page-list" data-list-kind="vouchers" data-page-direction="next" ${nextDisabled}>Next</button>
      </div>
    </div>
  `;
}

export function renderVoucherApprovalQueuePanel(items) {
  const rows = Array.isArray(items) ? items : [];
  const openItems = rows.filter((row) => ["pending_approval", "rejected"].includes(row.approval_status || "not_submitted"));
  const rejectedCount = openItems.filter((row) => row.approval_status === "rejected").length;
  const pendingCount = openItems.filter((row) => row.approval_status === "pending_approval").length;

  if (openItems.length === 0) {
    return `
      <div class="verification-panel">
        <div class="preview-heading compact">
          <div>
            <h5>Voucher review queue</h5>
            <p>No voucher reviews are pending in the current tenant context.</p>
          </div>
          <button class="secondary" type="button" data-business-action="voucher-queue-refresh">Refresh</button>
        </div>
      </div>
    `;
  }

  return `
    <div class="verification-panel">
      <div class="preview-heading compact">
        <div>
          <h5>Voucher review queue</h5>
          <p>${escapeHtml(String(openItems.length))} voucher(s) still need explicit review visibility.</p>
        </div>
        <button class="secondary" type="button" data-business-action="voucher-queue-refresh">Refresh</button>
      </div>
      <div class="stats-grid">
        <div class="stat-card"><span>Open items</span><strong>${escapeHtml(String(openItems.length))}</strong></div>
        <div class="stat-card"><span>Pending</span><strong>${escapeHtml(String(pendingCount))}</strong></div>
        <div class="stat-card"><span>Rejected</span><strong>${escapeHtml(String(rejectedCount))}</strong></div>
      </div>
      <div class="table-preview compact-table erp-table">
        <table>
          <thead>
            <tr>
              <th>Voucher</th>
              <th>Date</th>
              <th>Amount</th>
              <th>Approval</th>
            </tr>
          </thead>
          <tbody>
            ${openItems.slice(0, 10).map((row) => `
              <tr>
                <td>
                  <strong>${escapeHtml(row.document_number || row.document_id || "-")}</strong>
                  <span class="row-subtext">${escapeHtml(row.document_type || "voucher")}</span>
                </td>
                <td>${escapeHtml(String(row.document_date || row.created_at || "").slice(0, 10))}</td>
                <td class="amount">${escapeHtml(formatCurrency(row.amount || 0))}</td>
                <td><span class="pill ${row.approval_status === "rejected" ? "warn" : ""}">${escapeHtml(row.approval_status || "not_submitted")}</span></td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}






