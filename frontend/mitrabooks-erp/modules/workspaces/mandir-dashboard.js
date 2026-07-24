// ====================================================================
// SECTION: MANDIR — DASHBOARD HOME + WORKSPACE TABS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initMandirDashboard(...).
// ====================================================================

/** @type {Record<string, Function> | null} */
let deps = null;

export function initMandirDashboard(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initMandirDashboard() must be called before using Mandir dashboard helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function formatCountLabel(...args) { return requireDeps().formatCountLabel(...args); }
function renderStatCards(stats) { return requireDeps().renderStatCards(stats); }
function renderActivity(items) { return requireDeps().renderActivity(items); }
function isProductionShell() { return requireDeps().isProductionShell(); }
function isMandirHost() { return requireDeps().isMandirHost(); }
function renderMandirWorkspaceTabs(active) { return requireDeps().renderMandirWorkspaceTabs(active); }
function renderMandirOperationResult(result) { return requireDeps().renderMandirOperationResult(result); }
function renderMandirCreateForms(payload) { return requireDeps().renderMandirCreateForms(payload); }
function renderMandirListFilters(...args) { return requireDeps().renderMandirListFilters(...args); }
function renderMandirDonationsTable(rows) { return requireDeps().renderMandirDonationsTable(rows); }
function renderMandirSevaBookingsTable(rows) { return requireDeps().renderMandirSevaBookingsTable(rows); }
function mandirPublicPaymentPageUrl() { return requireDeps().mandirPublicPaymentPageUrl(); }
function renderMandirPublicPaymentFilters(n) { return requireDeps().renderMandirPublicPaymentFilters(n); }
function renderMandirPublicPaymentsTable(rows) { return requireDeps().renderMandirPublicPaymentsTable(rows); }
function renderMandirExceptionFilters(n) { return requireDeps().renderMandirExceptionFilters(n); }
function renderMandirExceptionsTable(rows) { return requireDeps().renderMandirExceptionsTable(rows); }
function renderMandirReceiptHistoryTable(rows) { return requireDeps().renderMandirReceiptHistoryTable(rows); }
function renderMandirPanchang(payload) { return requireDeps().renderMandirPanchang(payload); }
function renderMandirOperationalReports(reports) { return requireDeps().renderMandirOperationalReports(reports); }
function renderMandirDevoteesView(reports) { return requireDeps().renderMandirDevoteesView(reports); }
function renderAccountingDrilldownPanel(...args) { return requireDeps().renderAccountingDrilldownPanel(...args); }
function renderMandirTrialBalance(payload) { return requireDeps().renderMandirTrialBalance(payload); }
function renderMandirFinancialReports(reports) { return requireDeps().renderMandirFinancialReports(reports); }
function renderMandirExpensesTable(rows) { return requireDeps().renderMandirExpensesTable(rows); }
function getActiveMandirWorkspace() { return requireDeps().getActiveMandirWorkspace(); }
function getMandirReportState() { return requireDeps().getMandirReportState(); }
function getLastMandirPanchang() { return requireDeps().getLastMandirPanchang(); }
function getLastMandirOperationalReports() { return requireDeps().getLastMandirOperationalReports(); }

export function renderMandirDashboardHome(payload = {}) {
  const pendingPayments = Array.isArray(payload.pending_payments) ? payload.pending_payments : [];
  const paymentExceptions = Array.isArray(payload.payment_exceptions) ? payload.payment_exceptions : [];
  const recentReceipts = Array.isArray(payload.recent_receipts) ? payload.recent_receipts : [];
  const panchang = payload.panchang || null;
  const panchangPayload = panchang && panchang.ok !== false ? panchang : {};
  const gregorianDate = panchangPayload.date?.gregorian || {};
  const panchangData = panchangPayload.panchang || {};
  const sunMoon = panchangPayload.sun_moon || {};
  return `
    <div class="dashboard-main-grid platform-grid mandir-home-grid">
      <article>
        <h4>Quick Donation Entry</h4>
        <p class="muted">Use Donations for full receipt entry and sponsorship details.</p>
        <button type="button" data-workspace-view="donations">Open Donations</button>
      </article>
      <article class="panchang-card">
        <h4>Today's Panchang</h4>
        <p>${escapeHtml(gregorianDate.formatted || gregorianDate.date || "Today")}</p>
        <dl>
          <dt>Tithi</dt>
          <dd>${escapeHtml(panchangData.tithi?.full_name || panchangData.tithi?.name || "--")}</dd>
          <dt>Nakshatra</dt>
          <dd>${escapeHtml(panchangData.nakshatra?.name || "--")}</dd>
          <dt>Sunrise</dt>
          <dd>${escapeHtml(sunMoon.sunrise || "--")}</dd>
          <dt>Sunset</dt>
          <dd>${escapeHtml(sunMoon.sunset || "--")}</dd>
        </dl>
        <button type="button" class="secondary" data-workspace-view="panchang">View Full Panchang</button>
      </article>
      <article>
        <h4>Public Payment Review</h4>
        <div class="metric-grid two">${renderStatCards([
          ["Pending", pendingPayments.length, "UPI payments"],
          ["Exceptions", paymentExceptions.length, "need review"],
        ])}</div>
        <button type="button" class="secondary" data-workspace-view="payments">Open Public Payments</button>
      </article>
      <article>
        <h4>Recent Receipts</h4>
        <p class="muted">${formatCountLabel(recentReceipts.length, "receipt")} available in receipt history.</p>
        <button type="button" class="secondary" data-workspace-view="receipts">Open Receipts</button>
      </article>
    </div>
  `;
}

export function renderMandirDashboard(payload = {}) {
  const stats = payload.stats || {};
  const pendingPayments = Array.isArray(payload.pending_payments) ? payload.pending_payments : [];
  const receipt = payload.receipt || null;
  const formResult = payload.form_result || null;
  const recentReceipts = Array.isArray(payload.recent_receipts) ? payload.recent_receipts : [];
  const recentDonations = Array.isArray(payload.recent_donations) ? payload.recent_donations : [];
  const recentSevaBookings = Array.isArray(payload.recent_seva_bookings) ? payload.recent_seva_bookings : [];
  const recentExpenses = Array.isArray(payload.recent_expenses) ? payload.recent_expenses : [];
  const trialBalance = payload.trial_balance || getMandirReportState().trialBalance;
  const financialReports = payload.financial_reports || getMandirReportState().financialReports;
  const panchang = payload.panchang || getLastMandirPanchang();
  const operationalReports = payload.operational_reports || getLastMandirOperationalReports();
  const paymentExceptions = Array.isArray(payload.payment_exceptions) ? payload.payment_exceptions : [];
  const paymentExceptionSummary = payload.payment_exception_summary || {};
  const donations = stats.donations || {};
  const sevas = stats.sevas || {};
  const donationCards = [
    ["Today's Donation", formatCurrency(donations.today?.amount), formatCountLabel(donations.today?.count, "donation")],
    ["Cumulative for Month", formatCurrency(donations.month?.amount), formatCountLabel(donations.month?.count, "donation")],
    ["Cumulative for Year", formatCurrency(donations.year?.amount), formatCountLabel(donations.year?.count, "donation")],
  ];
  const sevaCards = [
    ["Today's Seva", formatCurrency(sevas.today?.amount), formatCountLabel(sevas.today?.count, "booking")],
    ["Cumulative for Month", formatCurrency(sevas.month?.amount), formatCountLabel(sevas.month?.count, "booking")],
    ["Cumulative for Year", formatCurrency(sevas.year?.amount), formatCountLabel(sevas.year?.count, "booking")],
  ];
  const showOverview = getActiveMandirWorkspace() === "overview";
  const showDonations = getActiveMandirWorkspace() === "donations";
  const showSevas = ["sevas", "book-sevas", "seva-bookings", "seva-management", "reschedule-approval"].includes(getActiveMandirWorkspace());
  const showDevotees = getActiveMandirWorkspace() === "devotees";
  const showPayments = getActiveMandirWorkspace() === "payments";
  const showExceptions = getActiveMandirWorkspace() === "exceptions";
  const showReceipts = getActiveMandirWorkspace() === "receipts";
  const showPanchang = getActiveMandirWorkspace() === "panchang";
  const showReports = getActiveMandirWorkspace() === "reports";
  const showAccounting = getActiveMandirWorkspace() === "accounting";
  const showSettings = getActiveMandirWorkspace() === "settings";
  const showImplementation = getActiveMandirWorkspace() === "implementation";
  const showPlatformOwners = getActiveMandirWorkspace() === "platform-owners";
  const pageMeta = {
    overview: ["Dashboard", "Donation, seva, public payment review, and today's panchang for the active temple tenant."],
    donations: ["Donations", "Record and review donation receipts for the active temple tenant."],
    sevas: ["Sevas", "Book and review seva receipts for the active temple tenant."],
    "book-sevas": ["Book Sevas", "Create seva bookings for devotees."],
    "seva-bookings": ["Seva Bookings / Reschedule", "Review bookings and reschedule requests."],
    "seva-management": ["Seva Management", "Manage seva definitions and temple service workflows."],
    "reschedule-approval": ["Reschedule Approval", "Approve or reject seva reschedule requests."],
    devotees: ["Devotees", "Tenant-scoped devotee records captured from donations, sevas, and public payments."],
    payments: ["Public Payments", "Verify no-login UPI payments before posting receipts and accounting."],
    exceptions: ["Payment Exceptions", "Review public payment records that need correction or rejection."],
    receipts: ["Receipts", "Preview, download, and reverse donation or seva receipts."],
    panchang: ["Panchang", "Temple calendar and panchang visibility."],
    reports: ["Reports", "Donation, seva, devotee, and operational reports."],
    accounting: ["Accounting", "Trial Balance, drill-down, financial reports, and temple expenses."],
    settings: ["Settings", "Tenant-level MandirMitra configuration and safety controls."],
    implementation: ["Implementation Checks", "First-live checklist and deployment readiness tracking."],
    "platform-owners": ["Platform Owners", "Privileged platform-owner administration shortcut."],
  }[getActiveMandirWorkspace()] || ["Dashboard", "MandirMitra temple workspace."];

  return `
    <div class="legacy-dashboard mandir-dashboard">
      <div class="preview-heading">
        <div>
          <h3>${escapeHtml(pageMeta[0])}</h3>
          <p>${escapeHtml(pageMeta[1])}</p>
        </div>
        <span class="pill ok technical-context">mandirmitra</span>
      </div>
      ${isProductionShell() && isMandirHost() ? "" : renderMandirWorkspaceTabs(getActiveMandirWorkspace())}
      ${renderMandirOperationResult(formResult)}
      ${(showOverview || getActiveMandirWorkspace() === "donations") ? `
        <h4>Donations</h4>
        <div class="metric-grid three">${renderStatCards(donationCards)}</div>
      ` : ""}
      ${(showOverview || showSevas) ? `
        <h4>Sevas</h4>
        <div class="metric-grid three">${renderStatCards(sevaCards)}</div>
      ` : ""}
      ${showOverview ? renderMandirDashboardHome({
        pending_payments: pendingPayments,
        payment_exceptions: paymentExceptions,
        recent_receipts: recentReceipts,
        panchang,
      }) : ""}
      ${(showDonations || showSevas) ? `
        ${renderMandirCreateForms({
          payment_accounts: payload.payment_accounts,
          accounts: payload.accounts,
          module_config: payload.module_config,
          compliance_config: payload.compliance_config,
          form_result: null,
        })}
        <div class="dashboard-main-grid ${showOverview ? "platform-grid" : ""}">
          ${showDonations ? `
        <article>
          <h4>${showOverview ? "Recent Donations" : "Donations"}</h4>
          ${renderMandirListFilters("donations", recentDonations.length)}
          ${renderMandirDonationsTable(recentDonations)}
        </article>
          ` : ""}
          ${showSevas ? `
        <article>
          <h4>${showOverview ? "Recent Seva Bookings" : "Seva Bookings"}</h4>
          ${renderMandirListFilters("sevas", recentSevaBookings.length)}
          ${renderMandirSevaBookingsTable(recentSevaBookings)}
        </article>
          ` : ""}
        </div>
      ` : ""}
      ${showDevotees ? renderMandirDevoteesView(operationalReports) : ""}
      ${showPayments ? `
      <div class="verification-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Public Payments Pending Verification</h4>
            <p>Verify UPI payments only after temple staff confirms the payment, then post receipt and accounting.</p>
          </div>
          <div class="action-row">
            <a class="button secondary" href="${escapeHtml(mandirPublicPaymentPageUrl())}" target="_blank" rel="noopener">Open Public Page</a>
            <span class="pill warn">${pendingPayments.length} pending</span>
          </div>
        </div>
        ${renderMandirPublicPaymentFilters(pendingPayments.length)}
        ${renderMandirPublicPaymentsTable(pendingPayments)}
      </div>
      ` : ""}
      ${showExceptions ? `
      <div class="verification-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Payment Exceptions</h4>
            <p>Old pending payments and invalid public payment records that need staff review.</p>
          </div>
          <span class="pill warn">${escapeHtml(paymentExceptionSummary.total || paymentExceptions.length)} flagged</span>
        </div>
        ${renderMandirExceptionFilters(paymentExceptions.length)}
        ${renderMandirExceptionsTable(paymentExceptions)}
      </div>
      ` : ""}
      ${showReceipts ? `
      <div class="verification-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Recent Receipts</h4>
            <p>Donation and seva receipts generated for this temple tenant.</p>
          </div>
          <span class="pill">${recentReceipts.length} shown</span>
        </div>
        ${renderMandirReceiptHistoryTable(recentReceipts)}
      </div>
      ` : ""}
      ${showReceipts && receipt ? `
        <div class="verification-panel">
          <div class="preview-heading compact">
            <div>
              <h4>Last Verified Receipt</h4>
              <p>${escapeHtml(receipt.receipt_number || receipt.source_id || "Receipt ready")}</p>
            </div>
            <div class="action-row">
              <button
                class="secondary"
                type="button"
                data-mandir-action="preview-receipt"
                data-receipt-url="${escapeHtml(receipt.receipt_pdf_url)}"
                data-receipt-label="${escapeHtml(receipt.receipt_number || receipt.source_id || "Receipt")}"
              >Preview</button>
              <button
                type="button"
                data-mandir-action="download-receipt"
                data-receipt-url="${escapeHtml(receipt.receipt_pdf_url)}"
                data-receipt-filename="${escapeHtml(receipt.filename)}"
              >Download Receipt</button>
            </div>
          </div>
        </div>
      ` : ""}
      ${showPanchang ? renderMandirPanchang(panchang) : ""}
      ${showReports ? renderMandirOperationalReports(operationalReports) : ""}
      ${showSettings ? renderMandirSettings(payload.module_config || {}, payload.compliance_config || {}) : ""}
      ${showImplementation ? renderMandirImplementationChecks() : ""}
      ${showPlatformOwners ? renderMandirPlatformOwnerShortcut() : ""}
      ${showAccounting ? renderAccountingDrilldownPanel() : ""}
      ${showAccounting ? renderMandirTrialBalance(trialBalance) : ""}
      ${showAccounting ? renderMandirFinancialReports(financialReports) : ""}
      ${showAccounting ? renderMandirExpensesTable(recentExpenses) : ""}
    </div>
  `;
}

export function renderMandirSettings(moduleConfig = {}, complianceConfig = {}) {
  const inventoryEnabled = Boolean(moduleConfig.module_inventory_enabled ?? moduleConfig.inventory_enabled);
  const flags = [
    ["Inventory accounting", inventoryEnabled ? "Enabled" : "Disabled", inventoryEnabled ? "In-kind consumables can debit inventory where configured." : "In-kind consumables debit expense unless the tenant enables inventory."],
    ["80G", moduleConfig.enable_80g ? "Enabled" : "Off", "Tenant-configured only; never default-on."],
    ["FCRA", moduleConfig.enable_fcra ? "Enabled" : "Off", "Tenant-configured only; never default-on."],
    ["Receipt reversal", "Enabled", "Corrections are handled by linked reversal journals."],
  ];
  return `
    <div class="dashboard-main-grid platform-grid">
      <article>
        <h4>Settings</h4>
        <div class="metric-grid two">
          ${flags.map(([label, value, subtext]) => `
            <article class="metric-tile">
              <span>${escapeHtml(label)}</span>
              <strong>${escapeHtml(value)}</strong>
              <small>${escapeHtml(subtext)}</small>
            </article>
          `).join("")}
        </div>
      </article>
      <article>
        <h4>Tenant Controls</h4>
        <ul class="activity-list">
          ${renderActivity([
            "UPI/payee visibility comes from temple configuration.",
            "Donation, seva, and expense postings go through MitraBooks accounting.",
            "Public payments remain pending until staff verification.",
            "Real trusts must not be used for destructive smoke tests.",
          ])}
        </ul>
      </article>
      <article class="verification-panel">
        <h4>Donation Compliance</h4>
        <p class="muted">Default-off tenant configuration. Save only after the trust's legal/compliance reviewer verifies the approval evidence.</p>
        <form class="entry-form" data-mandir-compliance-form>
          <label class="field"><span><input name="enable_80g" type="checkbox" ${complianceConfig.enable_80g ? "checked" : ""}> Enable 80G readiness</span></label>
          <label class="field"><span>Institution PAN</span><input name="institution_pan" maxlength="10" value="${escapeHtml(complianceConfig.institution_pan || "")}" placeholder="ABCDE1234F"></label>
          <label class="field"><span>Approval number</span><input name="approval_number" maxlength="120" value="${escapeHtml(complianceConfig.approval_number || "")}"></label>
          <label class="field"><span>Approval valid from</span><input name="approval_valid_from" type="date" value="${escapeHtml(complianceConfig.approval_valid_from || "")}"></label>
          <label class="field"><span>Approval valid to</span><input name="approval_valid_to" type="date" value="${escapeHtml(complianceConfig.approval_valid_to || "")}"></label>
          <label class="field"><span>Certificate label</span><input name="certificate_label" maxlength="120" value="${escapeHtml(complianceConfig.certificate_label || "Donation certificate")}"></label>
          <label class="field"><span>Cash eligibility limit</span><input name="cash_eligibility_limit" type="number" min="0.01" step="0.01" value="${escapeHtml(complianceConfig.cash_eligibility_limit || "")}"></label>
          <label class="field"><span>Cash rule effective from</span><input name="cash_rule_effective_from" type="date" value="${escapeHtml(complianceConfig.cash_rule_effective_from || "")}"></label>
          <label class="field"><span>Receipt disclaimer</span><textarea name="receipt_disclaimer" maxlength="500">${escapeHtml(complianceConfig.receipt_disclaimer || "")}</textarea></label>
          <label class="field"><span><input name="enable_fcra" type="checkbox" ${complianceConfig.enable_fcra ? "checked" : ""}> Enable FCRA readiness</span></label>
          <label class="field"><span>FCRA approval type</span><select name="fcra_registration_type"><option value="registration" ${complianceConfig.fcra_registration_type === "registration" ? "selected" : ""}>Registration</option><option value="prior_permission" ${complianceConfig.fcra_registration_type === "prior_permission" ? "selected" : ""}>Prior permission</option></select></label>
          <label class="field"><span>FCRA reference</span><input name="fcra_registration_number" maxlength="120" value="${escapeHtml(complianceConfig.fcra_registration_number || "")}"></label>
          <label class="field"><span>FCRA valid from</span><input name="fcra_valid_from" type="date" value="${escapeHtml(complianceConfig.fcra_valid_from || "")}"></label>
          <label class="field"><span>FCRA valid to</span><input name="fcra_valid_to" type="date" value="${escapeHtml(complianceConfig.fcra_valid_to || "")}"></label>
          <label class="field"><span>Designated account ID</span><input name="fcra_designated_account_id" maxlength="120" value="${escapeHtml(complianceConfig.fcra_designated_account_id || "")}" placeholder="Use this account during foreign donation entry"></label>
          <button type="submit">Save Compliance Configuration</button>
        </form>
      </article>
    </div>
  `;
}

export function renderMandirImplementationChecks() {
  return `
    <div class="dashboard-main-grid platform-grid">
      <article>
        <h4>Implementation Checks</h4>
        <ul class="activity-list">
          ${renderActivity([
            "Donation and seva receipt PDFs are generated and downloadable.",
            "Donation, seva, expense, sponsorship, and reversal postings use double-entry journals.",
            "Trial Balance, Income & Expenditure, Receipts & Payments, and Balance Sheet remain balanced.",
            "Tenant and app context come from the access token and X-App-Key.",
            "Public payment page is no-login, but posting requires staff verification.",
          ])}
        </ul>
      </article>
      <article>
        <h4>First-live Pending Areas</h4>
        <ul class="activity-list">
          ${renderActivity([
            "Full legacy screen-by-screen UI migration is still incremental.",
            "Production backup/restore and release rollback runbook must stay current.",
            "Panchang needs the next feature-complete pass after first-live shell stabilization.",
          ])}
        </ul>
      </article>
    </div>
  `;
}

export function renderMandirPlatformOwnerShortcut() {
  return `
    <div class="verification-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Platform Owners</h4>
          <p>Platform-owner administration remains a separate privileged workspace.</p>
        </div>
        <button type="button" class="secondary" data-platform-action="open-platform-owner">Open Platform Owner</button>
      </div>
      <p class="muted">Use this only with a super-admin token. Tenant admins should stay inside the MandirMitra workspace.</p>
    </div>
  `;
}

