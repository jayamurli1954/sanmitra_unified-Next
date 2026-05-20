import {
  clearAccessToken,
  apiRequest,
  downloadApiFile,
  fetchApiFileObjectUrl,
  getAccessToken,
  getConfiguredApiBaseUrl,
  loadHealth,
  loadModules,
  moduleItemsFromPayload,
  renderModuleState,
  renderJson,
  setAccessToken,
  setConfiguredApiBaseUrl,
  statusLabel,
} from "../shared/api-client.js";

const APP_KEY = "mitrabooks";
const EXPERIENCE_APP_KEYS = {
  mitrabooks: "mitrabooks",
  platform: "mitrabooks",
  mandir: "mandirmitra",
  gruha: "gruhamitra",
};
const entitlementModulesByOrgType = {
  TEMPLE: ["temple", "accounting", "audit"],
  HOUSING: ["housing", "accounting", "audit"],
  BUSINESS: ["business", "accounting", "gst", "inventory", "audit"],
  PROFESSIONAL: ["professional", "accounting", "billing", "audit"],
};

const experienceConfig = {
  mitrabooks: {
    title: "MitraBooks ERP",
    subtitle: "Unified shell for accounting-heavy SanMitra modules",
    logo: "../assets/brand/mitrabooks-logo.jpg",
    video: "../assets/brand/mitrabooks-logo.mp4",
    theme: "",
    scopeTitle: "MitraBooks Business Workspace",
    scopeCopy: "Business, GST, inventory, parties, vouchers, and financial reports stay close to the old MitraBooks accounting layout.",
    legacyTitle: "MitraBooks workspace",
    legacyCopy: "Business, GST, inventory, parties, vouchers, and financial reports.",
    dashboard: {
      type: "business",
      stats: [
        ["Cash and Bank", "Rs. 8.4L", "available balance"],
        ["Receivables", "Rs. 2.1L", "open invoices"],
        ["Payables", "Rs. 96K", "vendor dues"],
        ["GST Filing", "Ready", "current period"],
      ],
      actions: ["Sales Voucher", "Purchase Entry", "Journal Entry", "Ledger Report", "Trial Balance", "GST Summary"],
      activity: ["Receipt posted from customer account", "Inventory purchase voucher drafted", "Month-end ledger review pending"],
    },
    modules: [
      { module_key: "business", display_name: "Dashboard", frontend_path: "/business", nav_group: "Operations", enabled: true },
      { module_key: "accounting", display_name: "Accounts", frontend_path: "/accounting", nav_group: "Finance", enabled: true },
      { module_key: "gst", display_name: "GST Compliance", frontend_path: "/gst", nav_group: "Compliance", enabled: true },
      { module_key: "inventory", display_name: "Inventory", frontend_path: "/inventory", nav_group: "Operations", enabled: true },
      { module_key: "audit", display_name: "Audit Log", frontend_path: "/audit", nav_group: "Administration", enabled: true },
    ],
  },
  platform: {
    title: "Platform Owner",
    subtitle: "Cross-module onboarding, tenant, subscription, and module status",
    logo: "../assets/brand/mitrabooks-logo.jpg",
    video: "",
    theme: "",
    scopeTitle: "Platform Owner Workspace",
    scopeCopy: "Read-only control view for MandirMitra, GruhaMitra, and MitraBooks onboarding, subscriptions, tenant status, and enabled modules.",
    legacyTitle: "Platform owner dashboard",
    legacyCopy: "Central review layer over module-wise onboarding. Approval actions are intentionally separate from this read-only view.",
    dashboard: {
      type: "platform",
      summary: [
        ["Pending Approvals", "0", "module-wise onboarding"],
        ["Active Tenants", "0", "all tracked apps"],
        ["Inactive Tenants", "0", "needs review"],
        ["Subscription Plans", "0", "configured plans"],
      ],
      appStatus: [
        ["MandirMitra", "0 pending", "0 tenants"],
        ["GruhaMitra", "0 pending", "0 tenants"],
        ["MitraBooks", "0 pending", "0 tenants"],
      ],
    },
    modules: [
      { module_key: "platform_owner", display_name: "Dashboard", frontend_path: "/platform-owner/dashboard", nav_group: "Administration", enabled: true },
      { module_key: "platform_owner", display_name: "Onboarding Requests", frontend_path: "/platform-owner/onboarding", nav_group: "Administration", enabled: true },
      { module_key: "platform_owner", display_name: "Tenant Status", frontend_path: "/platform-owner/tenants", nav_group: "Administration", enabled: true },
      { module_key: "platform_owner", display_name: "Subscriptions", frontend_path: "/platform-owner/subscriptions", nav_group: "Administration", enabled: true },
    ],
  },
  mandir: {
    title: "MandirMitra",
    subtitle: "Temple, trust, donation, seva, and accounting workflows",
    logo: "../assets/brand/mandirmitra-logo.jpeg",
    video: "../assets/brand/mandirmitra-logo.mp4",
    theme: "mandir-theme",
    scopeTitle: "MandirMitra Temple Workspace",
    scopeCopy: "Preserves the old temple layout pattern: dashboard, donations, devotees, sevas, panchang, reports, and accounting.",
    legacyTitle: "MandirMitra layout mode",
    legacyCopy: "Saffron/green visual treatment and temple-first navigation are retained for user familiarity.",
    dashboard: {
      type: "mandir",
      donations: [
        ["Today's Donation", "Rs. 24,500", "18 donations"],
        ["Cumulative for Month", "Rs. 6.8L", "412 donations"],
        ["Cumulative for Year", "Rs. 74.2L", "8,902 donations"],
      ],
      sevas: [
        ["Today's Seva", "Rs. 18,000", "27 bookings"],
        ["Cumulative for Month", "Rs. 4.2L", "685 bookings"],
        ["Cumulative for Year", "Rs. 38.5L", "6,430 bookings"],
      ],
      verification: [
        ["Public UPI Payments", "9 pending", "donation and seva confirmations"],
        ["Receipt Posting", "6 ready", "verified collections awaiting receipt"],
        ["Review Queue", "3 flagged", "amount or UTR needs checking"],
      ],
      groups: [
        ["Public Payments", "Review UPI confirmations, verify UTR, then post donation or seva receipt"],
        ["Sevas", "Book Sevas, Seva Bookings / Reschedule, Seva Management"],
        ["Accounting", "Chart of Accounts, Quick Expense, Journal Entries, Reports"],
      ],
    },
    modules: [
      { module_key: "temple", display_name: "Dashboard", frontend_path: "/temple/dashboard", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Donations", frontend_path: "/temple/donations", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Devotees", frontend_path: "/temple/devotees", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Sevas", frontend_path: "/temple/sevas", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Panchang", frontend_path: "/temple/panchang", nav_group: "Operations", enabled: true },
      { module_key: "accounting", display_name: "Accounting", frontend_path: "/accounting", nav_group: "Finance", enabled: true },
      { module_key: "audit", display_name: "Reports", frontend_path: "/temple/reports", nav_group: "Administration", enabled: true },
    ],
  },
  gruha: {
    title: "GruhaMitra",
    subtitle: "Housing society operations with shared MitraBooks accounting",
    logo: "../assets/brand/gruhamitra-logo.png",
    video: "../assets/brand/gruhamitra-logo.mp4",
    theme: "gruha-theme",
    scopeTitle: "GruhaMitra Housing Workspace",
    scopeCopy: "Preserves the old housing layout pattern: dashboard, maintenance, members, complaints, reports, assets, and settings.",
    legacyTitle: "GruhaMitra layout mode",
    legacyCopy: "Housing-first navigation mirrors the old web app while using the unified shell.",
    dashboard: {
      type: "gruha",
      stats: [
        ["Society Balance", "Rs. 12.6L", "cash and bank"],
        ["This Month Billing", "Rs. 4.8L", "maintenance cycle"],
        ["Dues Pending", "Rs. 1.2L", "42 units"],
        ["Complaints Open", "18", "service desk"],
      ],
      actions: ["Accounting", "Generate Bills", "Members", "Find Society", "My Memberships", "Join Requests", "Complaints", "Reports", "Message", "Meeting", "Society Assets", "Settings"],
      activity: ["Maintenance collection posted", "New member approval pending", "Lift complaint assigned to vendor"],
      trend: ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
    },
    modules: [
      { module_key: "housing", display_name: "Dashboard", frontend_path: "/housing/dashboard", nav_group: "Operations", enabled: true },
      { module_key: "housing", display_name: "Maintenance", frontend_path: "/housing/maintenance", nav_group: "Operations", enabled: true },
      { module_key: "housing", display_name: "Members", frontend_path: "/housing/members", nav_group: "Operations", enabled: true },
      { module_key: "housing", display_name: "Complaints", frontend_path: "/housing/complaints", nav_group: "Operations", enabled: true },
      { module_key: "accounting", display_name: "Accounting", frontend_path: "/accounting", nav_group: "Finance", enabled: true },
      { module_key: "housing", display_name: "Reports", frontend_path: "/housing/reports", nav_group: "Finance", enabled: true },
      { module_key: "audit", display_name: "Settings", frontend_path: "/housing/settings", nav_group: "Administration", enabled: true },
    ],
  },
};

let currentExperience = "mitrabooks";
let lastMandirReceipt = null;
let activeReceiptPreviewObjectUrl = "";
let activeMandirWorkspace = "overview";
let lastMandirPaymentAccounts = { cash_accounts: [], bank_accounts: [] };
let lastMandirAccounts = [];
let lastMandirFormResult = null;
let lastMandirExpenses = [];
let lastMandirTrialBalance = null;
let lastMandirLedger = null;
let lastMandirFinancialReports = {};
const MANDIR_LIST_PAGE_SIZE = 8;
const mandirListState = {
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
const todayForReports = new Date();
const firstDayForReports = new Date(todayForReports.getFullYear(), todayForReports.getMonth(), 1);
let accountingDrilldownState = {
  level: "month",
  from_date: firstDayForReports.toISOString().slice(0, 10),
  to_date: todayForReports.toISOString().slice(0, 10),
  month: "",
  week_start: "",
  day: "",
};
let lastAccountingDrilldown = null;
let lastAccountingVoucherDetail = null;

const appRoot = document.getElementById("app-root");
const brandLogo = document.getElementById("brand-logo");
const brandTitle = document.getElementById("brand-title");
const brandSubtitle = document.getElementById("brand-subtitle");
const appKeyLabel = document.getElementById("app-key-label");
const scopeTitle = document.getElementById("scope-title");
const scopeCopy = document.getElementById("scope-copy");
const legacyTitle = document.getElementById("legacy-title");
const legacyCopy = document.getElementById("legacy-copy");
const legacyVideo = document.getElementById("legacy-video");
const legacyImage = document.getElementById("legacy-image");
const dashboardPreview = document.getElementById("dashboard-preview");
const nav = document.getElementById("nav");
const moduleList = document.getElementById("module-list");
const apiOutput = document.getElementById("api-output");
const healthPill = document.getElementById("health-pill");
const moduleState = document.getElementById("module-state");
const apiBaseInput = document.getElementById("api-base");
const tokenInput = document.getElementById("access-token");
const entitlementDialog = document.getElementById("entitlement-dialog");
const entitlementForm = document.getElementById("entitlement-form");
const entitlementTenantId = document.getElementById("entitlement-tenant-id");
const entitlementTenantLabel = document.getElementById("entitlement-tenant-label");
const entitlementPlan = document.getElementById("entitlement-plan");
const entitlementStatus = document.getElementById("entitlement-status");
const entitlementModules = document.getElementById("entitlement-modules");
const mandirVerificationDialog = document.getElementById("mandir-verification-dialog");
const mandirVerificationForm = document.getElementById("mandir-verification-form");
const mandirVerificationPaymentId = document.getElementById("mandir-verification-payment-id");
const mandirVerificationLabel = document.getElementById("mandir-verification-label");
const mandirVerificationUtr = document.getElementById("mandir-verification-utr");
const mandirVerificationDate = document.getElementById("mandir-verification-date");
const mandirVerificationBankAccount = document.getElementById("mandir-verification-bank-account");
const receiptPreviewDialog = document.getElementById("receipt-preview-dialog");
const receiptPreviewFrame = document.getElementById("receipt-preview-frame");
const receiptPreviewLabel = document.getElementById("receipt-preview-label");
const mandirRejectionDialog = document.getElementById("mandir-rejection-dialog");
const mandirRejectionForm = document.getElementById("mandir-rejection-form");
const mandirRejectionPaymentId = document.getElementById("mandir-rejection-payment-id");
const mandirRejectionLabel = document.getElementById("mandir-rejection-label");
const mandirRejectionReason = document.getElementById("mandir-rejection-reason");
const mandirCorrectionDialog = document.getElementById("mandir-correction-dialog");
const mandirCorrectionForm = document.getElementById("mandir-correction-form");
const mandirCorrectionPaymentId = document.getElementById("mandir-correction-payment-id");
const mandirCorrectionLabel = document.getElementById("mandir-correction-label");
const mandirCorrectionAmount = document.getElementById("mandir-correction-amount");
const mandirCorrectionPhone = document.getElementById("mandir-correction-phone");
const mandirCorrectionType = document.getElementById("mandir-correction-type");
const mandirCorrectionPurpose = document.getElementById("mandir-correction-purpose");

function renderModules(modules = experienceConfig[currentExperience].modules, options = {}) {
  const config = experienceConfig[currentExperience];
  const preview = options.preview !== false;
  appRoot.className = `app ${config.theme}`.trim();
  appKeyLabel.textContent = EXPERIENCE_APP_KEYS[currentExperience] || APP_KEY;
  brandLogo.src = config.logo;
  brandLogo.alt = config.title;
  brandTitle.textContent = config.title;
  brandSubtitle.textContent = config.subtitle;
  scopeTitle.textContent = config.scopeTitle;
  scopeCopy.textContent = config.scopeCopy;
  legacyTitle.textContent = config.legacyTitle;
  legacyCopy.textContent = config.legacyCopy;
  legacyImage.src = config.logo;
  legacyImage.alt = config.title;
  if (config.video && getAccessToken()) {
    legacyVideo.src = config.video;
    legacyVideo.hidden = false;
    legacyImage.hidden = true;
    legacyVideo.play().catch(() => {});
  } else {
    legacyVideo.pause();
    legacyVideo.removeAttribute("src");
    legacyVideo.load();
    legacyVideo.hidden = true;
    legacyImage.hidden = false;
  }

  nav.innerHTML = "";
  moduleList.innerHTML = "";
  dashboardPreview.innerHTML = renderDashboardPreview(config);

  modules.forEach((module) => {
    const link = document.createElement("a");
    link.href = "#";
    link.className = module.enabled ? "" : "locked";
    link.setAttribute("aria-disabled", module.enabled ? "false" : "true");
    link.dataset.moduleKey = module.module_key || "";
    link.dataset.frontendPath = module.frontend_path || "";
    const mandirWorkspace = mandirWorkspaceFromModule(module);
    if (mandirWorkspace) {
      link.dataset.mandirWorkspace = mandirWorkspace;
    }
    link.textContent = `${module.nav_group || "Module"}: ${module.display_name}`;
    nav.appendChild(link);

    const item = document.createElement("li");
    item.innerHTML = `
      <strong>${module.display_name}</strong>
      <span class="muted">${module.module_key} -> ${module.frontend_path || "no frontend path yet"}</span>
      <span class="pill ${module.enabled ? "ok" : "warn"}">${module.enabled ? "enabled" : preview ? "preview only" : "available or planned"}</span>
    `;
    moduleList.appendChild(item);
  });
  syncMandirNavActiveState();
}

function renderStatCards(stats) {
  return stats.map(([label, value, subtext]) => `
    <article class="metric-tile">
      <span>${label}</span>
      <strong>${value}</strong>
      <small>${subtext}</small>
    </article>
  `).join("");
}

function renderActionTiles(actions) {
  return actions.map((action) => `
    <button class="quick-tile" type="button">
      <span class="quick-icon">${action.split(" ").map((part) => part[0]).join("").slice(0, 2)}</span>
      <span>${action}</span>
    </button>
  `).join("");
}

function renderActivity(items) {
  return items.map((item) => `<li><span class="activity-dot"></span><span>${item}</span></li>`).join("");
}

function mandirWorkspaceFromModule(module = {}) {
  const path = String(module.frontend_path || "").toLowerCase();
  const displayName = String(module.display_name || "").toLowerCase();
  if (path.includes("/donations") || displayName.includes("donation")) {
    return "donations";
  }
  if (path.includes("/sevas") || displayName.includes("seva")) {
    return "sevas";
  }
  if (path.includes("/reports") || displayName.includes("report")) {
    return "receipts";
  }
  if (path.includes("/accounting") || displayName.includes("accounting")) {
    return "accounting";
  }
  if (path.includes("/dashboard") || displayName.includes("dashboard")) {
    return "overview";
  }
  return "";
}

function syncMandirNavActiveState() {
  nav.querySelectorAll("a").forEach((link) => {
    const workspace = link.dataset.mandirWorkspace || "";
    const isActive = currentExperience === "mandir" && workspace && workspace === activeMandirWorkspace;
    link.classList.toggle("active", isActive);
  });
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
  }[char]));
}

function formatCountMap(value) {
  if (!value || typeof value !== "object") {
    return "none";
  }
  return Object.entries(value)
    .map(([key, count]) => `${escapeHtml(key)}: ${escapeHtml(count)}`)
    .join(", ") || "none";
}

function renderPlatformTable(rows, columns, emptyText) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `<p class="muted">${emptyText}</p>`;
  }
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>${columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join("")}</tr>
        </thead>
        <tbody>
          ${rows.map((row) => `
            <tr>
              ${columns.map((column) => `<td>${escapeHtml(column.value(row))}</td>`).join("")}
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderPendingApprovalsTable(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `<p class="muted">No pending onboarding approvals.</p>`;
  }
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Request</th>
            <th>App</th>
            <th>Organization</th>
            <th>Admin Email</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((row) => {
            const requestId = row.request_id || row.id || "";
            return `
              <tr>
                <td>${escapeHtml(requestId)}</td>
                <td>${escapeHtml(row.app_key)}</td>
                <td>${escapeHtml(row.organization_name || row.tenant_name)}</td>
                <td>${escapeHtml(row.admin_email)}</td>
                <td>
                  <div class="action-row">
                    <button type="button" data-platform-action="approve" data-request-id="${escapeHtml(requestId)}">Approve</button>
                    <button class="secondary" type="button" data-platform-action="reject" data-request-id="${escapeHtml(requestId)}">Reject</button>
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

function renderMandirPublicPaymentsTable(rows) {
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

function formatMandirExceptionReasons(reasons = []) {
  if (!Array.isArray(reasons) || reasons.length === 0) {
    return "needs review";
  }
  return reasons.map((reason) => String(reason).replace(/_/g, " ")).join(", ");
}

function renderMandirExceptionsTable(rows) {
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

function mandirReceiptRowsFromLists(donations = [], sevaBookings = []) {
  const donationRows = donations.map((row) => ({
    type: "Donation",
    id: row.donation_id || row.id || "",
    receipt_number: row.receipt_number || row.donation_id || row.id || "",
    party: row.devotee_name || row.donor_name || row.name || "Devotee",
    date: row.donation_date || row.created_at || "",
    amount: row.amount || 0,
    receipt_pdf_url: row.receipt_pdf_url,
  }));
  const sevaRows = sevaBookings.map((row) => ({
    type: "Seva",
    id: row.id || row.booking_id || "",
    receipt_number: row.receipt_number || row.id || row.booking_id || "",
    party: row.devotee_name || row.devotee_names || row.name || "Devotee",
    date: row.booking_date || row.created_at || "",
    amount: row.amount_paid || row.amount || 0,
    receipt_pdf_url: row.receipt_pdf_url,
  }));
  return [...donationRows, ...sevaRows]
    .filter((row) => row.receipt_pdf_url)
    .sort((a, b) => String(b.date || "").localeCompare(String(a.date || "")))
    .slice(0, 8);
}

function renderMandirReceiptHistoryTable(rows) {
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
            return `
              <tr>
                <td>${escapeHtml(receiptLabel)}</td>
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

function renderMandirReceiptActions(row, label) {
  if (!row.receipt_pdf_url) {
    return `<span class="muted">No receipt</span>`;
  }
  const receiptLabel = label || row.receipt_number || row.id || "Receipt";
  const filename = `${String(receiptLabel).replace(/[^a-z0-9_-]+/gi, "_") || "receipt"}.pdf`;
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
    </div>
  `;
}

function renderMandirDonationsTable(rows) {
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
            return `
              <tr>
                <td>${escapeHtml(String(row.donation_date || row.created_at || "").slice(0, 10))}</td>
                <td>${escapeHtml(row.devotee_name || row.donor_name || row.name || "Devotee")}</td>
                <td>${escapeHtml(row.category || "Donation")}</td>
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

function renderMandirSevaBookingsTable(rows) {
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

function renderMandirWorkspaceTabs(activeWorkspace) {
  const tabs = [
    ["overview", "Overview"],
    ["donations", "Donations"],
    ["sevas", "Sevas"],
    ["payments", "Public Payments"],
    ["exceptions", "Exceptions"],
    ["receipts", "Receipts"],
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

function renderMandirListFilters(kind, rowsLength) {
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

function renderMandirPublicPaymentFilters(rowsLength) {
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

function renderMandirExceptionFilters(rowsLength) {
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

function renderRecentTenantsTable(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `<p class="muted">No tenants returned.</p>`;
  }
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Tenant</th>
            <th>Status</th>
            <th>Org Type</th>
            <th>Plan</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((row) => {
            const tenantId = row.tenant_id || "";
            const modules = Array.isArray(row.enabled_modules) ? row.enabled_modules.join(",") : "";
            return `
              <tr>
                <td>${escapeHtml(row.display_name || tenantId)}</td>
                <td>${escapeHtml(row.status)}</td>
                <td>${escapeHtml(row.organization_type)}</td>
                <td>${escapeHtml(row.subscription_plan)}</td>
                <td>
                  <button
                    class="secondary"
                    type="button"
                    data-platform-action="entitlements"
                    data-tenant-id="${escapeHtml(tenantId)}"
                    data-tenant-label="${escapeHtml(row.display_name || tenantId)}"
                    data-tenant-status="${escapeHtml(row.status)}"
                    data-organization-type="${escapeHtml(row.organization_type)}"
                    data-subscription-plan="${escapeHtml(row.subscription_plan)}"
                    data-enabled-modules="${escapeHtml(modules)}"
                  >Entitlements</button>
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function formatCurrency(value) {
  const amount = Number(value || 0);
  return `Rs. ${amount.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatCountLabel(count, singular, plural = `${singular}s`) {
  const safeCount = Number(count || 0);
  return `${safeCount} ${safeCount === 1 ? singular : plural}`;
}

function renderPlatformDashboard(payload) {
  const summary = payload?.summary || {};
  const onboarding = summary.onboarding || {};
  const tenants = summary.tenants || {};
  const subscriptions = summary.subscriptions || {};
  const pending = onboarding.by_status?.pending || 0;
  const active = tenants.by_status?.active || 0;
  const inactive = tenants.by_status?.inactive || 0;
  const planCount = Object.keys(subscriptions.by_plan || {}).length;
  const appStatus = Array.isArray(payload?.app_status) ? payload.app_status : [];
  const moduleStatus = Array.isArray(payload?.module_status) ? payload.module_status : [];
  const pendingApprovals = Array.isArray(payload?.pending_approvals) ? payload.pending_approvals : [];
  const recentTenants = Array.isArray(payload?.recent_tenants) ? payload.recent_tenants : [];

  return `
    <div class="legacy-dashboard platform-dashboard">
      <div class="preview-heading">
        <div>
          <h3>Platform Owner Dashboard</h3>
          <p>Read-only cross-module status for onboarding, subscriptions, tenants, and enabled modules.</p>
        </div>
        <span class="pill ok">super admin</span>
      </div>
      <div class="metric-grid four">${renderStatCards([
        ["Pending Approvals", pending, "module-wise onboarding"],
        ["Active Tenants", active, "all tracked apps"],
        ["Inactive Tenants", inactive, "needs review"],
        ["Subscription Plans", planCount, formatCountMap(subscriptions.by_plan)],
      ])}</div>
      <div class="dashboard-main-grid platform-grid">
        <article>
          <h4>Pending Approvals</h4>
          ${renderPendingApprovalsTable(pendingApprovals)}
        </article>
        <article>
          <h4>App Status</h4>
          <ul class="status-list">
            ${appStatus.map((row) => `
              <li>
                <strong>${escapeHtml(row.app_key)}</strong>
                <span>${escapeHtml(row.onboarding?.pending || 0)} pending, ${escapeHtml(row.tenant_count || 0)} tenant(s)</span>
              </li>
            `).join("")}
          </ul>
        </article>
      </div>
      <div class="dashboard-main-grid platform-grid">
        <article>
          <h4>Recent Tenants</h4>
          ${renderRecentTenantsTable(recentTenants)}
        </article>
        <article>
          <h4>Enabled Modules</h4>
          <ul class="status-list">
            ${moduleStatus.map((row) => `
              <li>
                <strong>${escapeHtml(row.module_key)}</strong>
                <span>${escapeHtml(row.tenant_count || 0)} tenant(s)</span>
              </li>
            `).join("")}
          </ul>
        </article>
      </div>
    </div>
  `;
}

function accountingDrilldownTitle(level) {
  return {
    month: "Monthly Voucher Drill Down",
    week: "Weekly Voucher Drill Down",
    day: "Daily Voucher Drill Down",
    voucher: "Voucher Level",
  }[level] || "Accounting Drill Down";
}

function renderAccountingDrilldownRows(payload) {
  const rows = Array.isArray(payload?.items) ? payload.items : [];
  if (rows.length === 0) {
    return `<p class="muted">No posted vouchers returned for this period.</p>`;
  }
  const level = payload.level || accountingDrilldownState.level;
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Period / Voucher</th>
            <th>Vouchers</th>
            <th class="amount">Debit</th>
            <th class="amount">Credit</th>
            <th>Last Voucher</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((row) => {
            const period = row.month || row.week_start || row.day || row.reference || row.id || "";
            const lastVoucher = row.last_voucher || row;
            const nextLevel = level === "month" ? "week" : level === "week" ? "day" : level === "day" ? "voucher" : "";
            return `
              <tr>
                <td>${escapeHtml(row.label || period)}</td>
                <td>${escapeHtml(row.voucher_count || 1)}</td>
                <td class="amount">${escapeHtml(formatCurrency(row.total_debit))}</td>
                <td class="amount">${escapeHtml(formatCurrency(row.total_credit))}</td>
                <td>${escapeHtml(lastVoucher?.reference || lastVoucher?.idempotency_key || lastVoucher?.id || "")}</td>
                <td>
                  ${nextLevel ? `
                    <button
                      class="secondary"
                      type="button"
                      data-accounting-action="drill"
                      data-next-level="${escapeHtml(nextLevel)}"
                      data-month="${escapeHtml(row.month || accountingDrilldownState.month || "")}"
                      data-week-start="${escapeHtml(row.week_start || accountingDrilldownState.week_start || "")}"
                      data-day="${escapeHtml(row.day || accountingDrilldownState.day || "")}"
                    >Open</button>
                  ` : `
                    <button
                      class="secondary"
                      type="button"
                      data-accounting-action="voucher-detail"
                      data-journal-id="${escapeHtml(row.id || "")}"
                    >View</button>
                  `}
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderAccountingVoucherDetail(detail = lastAccountingVoucherDetail) {
  if (!detail) {
    return "";
  }
  if (detail.ok === false) {
    return `<p class="muted">Voucher detail unavailable.</p>`;
  }
  const lines = Array.isArray(detail.lines) ? detail.lines : [];
  return `
    <div class="table-preview compact-table">
      <h4>Voucher ${escapeHtml(detail.reference || detail.id)}</h4>
      <p class="muted">${escapeHtml(detail.entry_date || "")} | ${escapeHtml(detail.description || "Posted journal voucher")}</p>
      <table>
        <thead>
          <tr>
            <th>Account</th>
            <th>Type</th>
            <th class="amount">Debit</th>
            <th class="amount">Credit</th>
          </tr>
        </thead>
        <tbody>
          ${lines.map((line) => `
            <tr>
              <td>${escapeHtml(`${line.account_code || ""} ${line.account_name || ""}`.trim())}</td>
              <td>${escapeHtml(line.account_type || "")}</td>
              <td class="amount">${escapeHtml(formatCurrency(line.debit))}</td>
              <td class="amount">${escapeHtml(formatCurrency(line.credit))}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderAccountingDrilldownPanel(payload = lastAccountingDrilldown) {
  const state = accountingDrilldownState;
  const summary = payload?.summary || {};
  return `
    <div class="verification-panel accounting-drilldown-panel">
      <div class="preview-heading compact">
        <div>
          <h4>${escapeHtml(accountingDrilldownTitle(payload?.level || state.level))}</h4>
          <p>Drill from month to week to day and then to the posted voucher reference.</p>
        </div>
        <span class="pill">${escapeHtml(summary.voucher_count || 0)} vouchers</span>
      </div>
      <div class="list-filter-panel" data-accounting-drilldown>
        <div class="list-filter-bar">
          <label class="field">
            <span>From</span>
            <input name="from_date" type="date" value="${escapeHtml(state.from_date)}">
          </label>
          <label class="field">
            <span>To</span>
            <input name="to_date" type="date" value="${escapeHtml(state.to_date)}">
          </label>
          <label class="field">
            <span>Level</span>
            <select name="level">
              ${["month", "week", "day", "voucher"].map((level) => `<option value="${level}" ${state.level === level ? "selected" : ""}>${level}</option>`).join("")}
            </select>
          </label>
          <div class="list-filter-actions">
            <button type="button" data-accounting-action="apply-drilldown">Apply</button>
            <button class="secondary" type="button" data-accounting-action="reset-drilldown">Reset</button>
          </div>
        </div>
      </div>
      ${payload?.ok === false ? `<p class="muted">Accounting drill-down unavailable. Provide an access token with accounting access and run checks.</p>` : renderAccountingDrilldownRows(payload)}
      ${renderAccountingVoucherDetail()}
    </div>
  `;
}

function renderMandirExpensesTable(rows = lastMandirExpenses) {
  const expenses = Array.isArray(rows) ? rows : [];
  return `
    <div class="verification-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Recent Expenses</h4>
          <p>Posted quick expenses created from the MandirMitra accounting form.</p>
        </div>
        <span class="pill">${expenses.length} shown</span>
      </div>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr>
              <th>Entry</th>
              <th>Date</th>
              <th>Narration</th>
              <th class="amount">Amount</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${expenses.length ? expenses.map((expense) => `
              <tr>
                <td>${escapeHtml(expense.entry_number || expense.id || "")}</td>
                <td>${escapeHtml(expense.entry_date || "")}</td>
                <td>${escapeHtml(expense.narration || expense.description || "")}</td>
                <td class="amount">${escapeHtml(formatCurrency(expense.total_amount || expense.total_debit || 0))}</td>
                <td><span class="pill ${expense.status === "posted" ? "ok" : "warn"}">${escapeHtml(expense.status || "draft")}</span></td>
              </tr>
            `).join("") : `
              <tr>
                <td colspan="5" class="muted">No expense entries found for this tenant/app context.</td>
              </tr>
            `}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderMandirTrialBalance(payload = lastMandirTrialBalance) {
  if (!payload) {
    return "";
  }
  if (payload.ok === false) {
    return `
      <div class="verification-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Trial Balance</h4>
            <p>Accounting report unavailable. Check backend accounting access and run checks again.</p>
          </div>
          <span class="pill warn">unavailable</span>
        </div>
      </div>
    `;
  }
  const rows = Array.isArray(payload.lines) ? payload.lines : Array.isArray(payload.accounts) ? payload.accounts : [];
  return `
    <div class="verification-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Trial Balance</h4>
          <p>As of ${escapeHtml(payload.as_of || todayIsoDate())}. Debits and credits must match.</p>
        </div>
        <span class="pill ${payload.balanced ? "ok" : "warn"}">${payload.balanced ? "balanced" : "not balanced"}</span>
      </div>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr>
              <th>Account</th>
              <th>Name</th>
              <th class="amount">Debit</th>
              <th class="amount">Credit</th>
              <th>Trace</th>
            </tr>
          </thead>
          <tbody>
            ${rows.length ? rows.map((row) => `
              <tr>
                <td>${escapeHtml(row.account_code || row.account_id || "")}</td>
                <td>${escapeHtml(row.account_name || row.name || "")}</td>
                <td class="amount">${escapeHtml(formatCurrency(row.debit_total || row.debit || 0))}</td>
                <td class="amount">${escapeHtml(formatCurrency(row.credit_total || row.credit || 0))}</td>
                <td>
                  <button
                    class="secondary"
                    type="button"
                    data-accounting-action="tb-ledger"
                    data-account-id="${escapeHtml(row.account_id || row.account_code || "")}"
                  >Open</button>
                </td>
              </tr>
            `).join("") : `
              <tr>
                <td colspan="5" class="muted">No posted accounting balances found for this tenant/app context.</td>
              </tr>
            `}
          </tbody>
          <tfoot>
            <tr>
              <th colspan="2">Total</th>
              <th class="amount">${escapeHtml(formatCurrency(payload.total_debit || 0))}</th>
              <th class="amount">${escapeHtml(formatCurrency(payload.total_credit || 0))}</th>
              <th></th>
            </tr>
          </tfoot>
        </table>
      </div>
      ${renderMandirLedgerTrace()}
    </div>
  `;
}

function renderMandirLedgerTrace(payload = lastMandirLedger) {
  if (!payload) {
    return "";
  }
  if (payload.loading) {
    return `
      <div class="table-preview compact-table" id="mandir-ledger-trace">
        <h4>Ledger Trace</h4>
        <p class="muted">Loading posted voucher lines for ${escapeHtml(payload.account_label || "selected account")}...</p>
      </div>
    `;
  }
  if (payload.ok === false) {
    const detail = payload.payload?.detail || payload.detail || "Ledger trace unavailable for the selected account.";
    return `
      <div class="table-preview compact-table" id="mandir-ledger-trace">
        <h4>Ledger Trace</h4>
        <p class="muted">${escapeHtml(detail)}</p>
      </div>
    `;
  }
  const entries = Array.isArray(payload.entries) ? payload.entries : Array.isArray(payload.transactions) ? payload.transactions : [];
  return `
    <div class="table-preview compact-table" id="mandir-ledger-trace">
      <h4>Ledger Trace: ${escapeHtml(`${payload.account_code || payload.account_id || ""} ${payload.account_name || ""}`.trim())}</h4>
      <p class="muted">${escapeHtml(payload.from_date || "")} to ${escapeHtml(payload.to_date || "")}. Posted voucher lines for this account.</p>
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Voucher</th>
            <th>Narration</th>
            <th class="amount">Debit</th>
            <th class="amount">Credit</th>
            <th class="amount">Balance</th>
          </tr>
        </thead>
        <tbody>
          ${entries.length ? entries.map((entry) => `
            <tr>
              <td>${escapeHtml(entry.date || entry.entry_date || "")}</td>
              <td>${escapeHtml(entry.entry_number || entry.reference || "")}</td>
              <td>${escapeHtml(entry.narration || entry.description || "")}</td>
              <td class="amount">${escapeHtml(formatCurrency(entry.debit_amount || entry.debit || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(entry.credit_amount || entry.credit || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(entry.running_balance || entry.balance || 0))}</td>
            </tr>
          `).join("") : `
            <tr>
              <td colspan="6" class="muted">No posted voucher lines found for this account.</td>
            </tr>
          `}
        </tbody>
      </table>
    </div>
  `;
}

function reportUnavailable(title, payload) {
  if (!payload || payload.ok !== false) {
    return "";
  }
  const detail = payload.payload?.detail || "Report unavailable. Check backend accounting access and run checks again.";
  return `
    <div class="verification-panel">
      <div class="preview-heading compact">
        <div>
          <h4>${escapeHtml(title)}</h4>
          <p>${escapeHtml(detail)}</p>
        </div>
        <span class="pill warn">unavailable</span>
      </div>
    </div>
  `;
}

function renderMandirIncomeExpenditureReport(payload) {
  if (!payload) {
    return "";
  }
  if (payload.ok === false) {
    return reportUnavailable("Income & Expenditure", payload);
  }
  const lines = Array.isArray(payload.lines) ? payload.lines : [];
  return `
    <div class="verification-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Income & Expenditure</h4>
          <p>${escapeHtml(payload.from_date || accountingDrilldownState.from_date)} to ${escapeHtml(payload.to_date || accountingDrilldownState.to_date)}</p>
        </div>
        <span class="pill ${Number(payload.net_profit || 0) >= 0 ? "ok" : "warn"}">${escapeHtml(formatCurrency(payload.net_profit || 0))}</span>
      </div>
      <div class="metric-grid three">
        ${renderStatCards([
          ["Income", formatCurrency(payload.income_total || 0), "posted income"],
          ["Expenditure", formatCurrency(payload.expense_total || 0), "posted expenses"],
          ["Net", formatCurrency(payload.net_profit || 0), "income less expense"],
        ])}
      </div>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr>
              <th>Account</th>
              <th>Name</th>
              <th>Type</th>
              <th class="amount">Debit</th>
              <th class="amount">Credit</th>
              <th class="amount">Net</th>
            </tr>
          </thead>
          <tbody>
            ${lines.length ? lines.map((line) => `
              <tr>
                <td>${escapeHtml(line.account_code || line.account_id || "")}</td>
                <td>${escapeHtml(line.account_name || "")}</td>
                <td>${escapeHtml(line.account_type || "")}</td>
                <td class="amount">${escapeHtml(formatCurrency(line.debit_total || 0))}</td>
                <td class="amount">${escapeHtml(formatCurrency(line.credit_total || 0))}</td>
                <td class="amount">${escapeHtml(formatCurrency(line.net_amount || 0))}</td>
              </tr>
            `).join("") : `
              <tr>
                <td colspan="6" class="muted">No income or expenditure rows found for this period.</td>
              </tr>
            `}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderMandirReceiptsPaymentsReport(payload) {
  if (!payload) {
    return "";
  }
  if (payload.ok === false) {
    return reportUnavailable("Receipts & Payments", payload);
  }
  const lines = Array.isArray(payload.lines) ? payload.lines : [];
  return `
    <div class="verification-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Receipts & Payments</h4>
          <p>${escapeHtml(payload.from_date || accountingDrilldownState.from_date)} to ${escapeHtml(payload.to_date || accountingDrilldownState.to_date)}</p>
        </div>
        <span class="pill">${escapeHtml(formatCurrency(payload.net_receipts || 0))}</span>
      </div>
      <div class="metric-grid three">
        ${renderStatCards([
          ["Receipts", formatCurrency(payload.total_receipts || 0), "cash/bank debit"],
          ["Payments", formatCurrency(payload.total_payments || 0), "cash/bank credit"],
          ["Net Receipts", formatCurrency(payload.net_receipts || 0), "receipts less payments"],
        ])}
      </div>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr>
              <th>Account</th>
              <th>Name</th>
              <th class="amount">Receipts</th>
              <th class="amount">Payments</th>
              <th class="amount">Net</th>
            </tr>
          </thead>
          <tbody>
            ${lines.length ? lines.map((line) => `
              <tr>
                <td>${escapeHtml(line.account_code || line.account_id || "")}</td>
                <td>${escapeHtml(line.account_name || "")}</td>
                <td class="amount">${escapeHtml(formatCurrency(line.receipts || 0))}</td>
                <td class="amount">${escapeHtml(formatCurrency(line.payments || 0))}</td>
                <td class="amount">${escapeHtml(formatCurrency(line.net_receipts || 0))}</td>
              </tr>
            `).join("") : `
              <tr>
                <td colspan="5" class="muted">No cash or bank movements found for this period.</td>
              </tr>
            `}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderBalanceSheetRows(rows = []) {
  return rows.length ? rows.map((line) => `
    <tr>
      <td>${escapeHtml(line.account_code || line.account_id || "")}</td>
      <td>${escapeHtml(line.account_name || "")}</td>
      <td class="amount">${escapeHtml(formatCurrency(line.balance || 0))}</td>
    </tr>
  `).join("") : `
    <tr>
      <td colspan="3" class="muted">No rows.</td>
    </tr>
  `;
}

function renderMandirBalanceSheetReport(payload) {
  if (!payload) {
    return "";
  }
  if (payload.ok === false) {
    return reportUnavailable("Balance Sheet", payload);
  }
  const assets = Array.isArray(payload.assets) ? payload.assets : [];
  const liabilities = Array.isArray(payload.liabilities) ? payload.liabilities : [];
  const equity = Array.isArray(payload.equity) ? payload.equity : [];
  return `
    <div class="verification-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Balance Sheet</h4>
          <p>As of ${escapeHtml(payload.as_of || todayIsoDate())}. Assets should equal liabilities plus equity.</p>
        </div>
        <span class="pill ${payload.balanced ? "ok" : "warn"}">${payload.balanced ? "balanced" : "not balanced"}</span>
      </div>
      <div class="metric-grid three">
        ${renderStatCards([
          ["Assets", formatCurrency(payload.total_assets || 0), "resources"],
          ["Liabilities", formatCurrency(payload.total_liabilities || 0), "obligations"],
          ["Equity", formatCurrency(payload.total_equity || 0), "fund balance"],
        ])}
      </div>
      <div class="dashboard-main-grid platform-grid">
        ${[
          ["Assets", assets],
          ["Liabilities", liabilities],
          ["Equity", equity],
        ].map(([title, rows]) => `
          <article>
            <h4>${escapeHtml(title)}</h4>
            <div class="table-preview compact-table">
              <table>
                <thead>
                  <tr>
                    <th>Account</th>
                    <th>Name</th>
                    <th class="amount">Balance</th>
                  </tr>
                </thead>
                <tbody>${renderBalanceSheetRows(rows)}</tbody>
              </table>
            </div>
          </article>
        `).join("")}
      </div>
    </div>
  `;
}

function renderMandirFinancialReports(reports = lastMandirFinancialReports) {
  return `
    ${renderMandirIncomeExpenditureReport(reports.income_expenditure)}
    ${renderMandirReceiptsPaymentsReport(reports.receipts_payments)}
    ${renderMandirBalanceSheetReport(reports.balance_sheet)}
  `;
}

function renderMandirDashboard(payload = {}) {
  const stats = payload.stats || {};
  const pendingPayments = Array.isArray(payload.pending_payments) ? payload.pending_payments : [];
  const receipt = payload.receipt || null;
  const formResult = payload.form_result || null;
  const recentReceipts = Array.isArray(payload.recent_receipts) ? payload.recent_receipts : [];
  const recentDonations = Array.isArray(payload.recent_donations) ? payload.recent_donations : [];
  const recentSevaBookings = Array.isArray(payload.recent_seva_bookings) ? payload.recent_seva_bookings : [];
  const recentExpenses = Array.isArray(payload.recent_expenses) ? payload.recent_expenses : [];
  const trialBalance = payload.trial_balance || lastMandirTrialBalance;
  const financialReports = payload.financial_reports || lastMandirFinancialReports;
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
  const showOverview = activeMandirWorkspace === "overview";
  const showDonations = showOverview || activeMandirWorkspace === "donations";
  const showSevas = showOverview || activeMandirWorkspace === "sevas";
  const showPayments = showOverview || activeMandirWorkspace === "payments";
  const showExceptions = showOverview || activeMandirWorkspace === "exceptions";
  const showReceipts = showOverview || activeMandirWorkspace === "receipts";
  const showAccounting = showOverview || activeMandirWorkspace === "accounting";

  return `
    <div class="legacy-dashboard mandir-dashboard">
      <div class="preview-heading">
        <div>
          <h3>MandirMitra Dashboard</h3>
          <p>Donation, seva, and public UPI payment verification for the active temple tenant.</p>
        </div>
        <span class="pill ok">mandirmitra</span>
      </div>
      ${renderMandirWorkspaceTabs(activeMandirWorkspace)}
      ${(showOverview || showDonations || showSevas || showAccounting) ? renderMandirCreateForms({
        payment_accounts: payload.payment_accounts,
        accounts: payload.accounts,
        form_result: formResult,
      }) : ""}
      ${(showOverview || activeMandirWorkspace === "donations") ? `
        <h4>Donations</h4>
        <div class="metric-grid three">${renderStatCards(donationCards)}</div>
      ` : ""}
      ${(showOverview || activeMandirWorkspace === "sevas") ? `
        <h4>Sevas</h4>
        <div class="metric-grid three">${renderStatCards(sevaCards)}</div>
      ` : ""}
      ${(showDonations || showSevas) ? `
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
      ${showPayments ? `
      <div class="verification-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Public Payments Pending Verification</h4>
            <p>Verify UPI payments only after temple staff confirms the payment, then post receipt and accounting.</p>
          </div>
          <span class="pill warn">${pendingPayments.length} pending</span>
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
      ${(showOverview || showReceipts) && receipt ? `
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
      ${showAccounting ? renderAccountingDrilldownPanel() : ""}
      ${(showOverview || showAccounting) ? renderMandirTrialBalance(trialBalance) : ""}
      ${showAccounting ? renderMandirFinancialReports(financialReports) : ""}
      ${(showOverview || showAccounting) ? renderMandirExpensesTable(recentExpenses) : ""}
    </div>
  `;
}

function renderDashboardPreview(config) {
  const dashboard = config.dashboard;
  if (!dashboard) {
    return "";
  }

  if (dashboard.type === "platform") {
    return renderPlatformDashboard({
      summary: {
        onboarding: { by_status: { pending: 0 } },
        tenants: { by_status: { active: 0, inactive: 0 } },
        subscriptions: { by_plan: {} },
      },
      app_status: [
        { app_key: "mandirmitra", onboarding: { pending: 0 }, tenant_count: 0 },
        { app_key: "gruhamitra", onboarding: { pending: 0 }, tenant_count: 0 },
        { app_key: "mitrabooks", onboarding: { pending: 0 }, tenant_count: 0 },
      ],
      module_status: [],
      pending_approvals: [],
      recent_tenants: [],
    });
  }

  if (dashboard.type === "mandir") {
    return `
      <div class="legacy-dashboard mandir-dashboard">
        <div class="preview-heading">
          <div>
            <h3>Dashboard</h3>
            <p>Old MandirMitra pattern with separate donation, seva, and public payment verification summaries.</p>
          </div>
          <span class="pill ok">temple workspace</span>
        </div>
        <h4>Donations</h4>
        <div class="metric-grid three">${renderStatCards(dashboard.donations)}</div>
        <h4>Sevas</h4>
        <div class="metric-grid three">${renderStatCards(dashboard.sevas)}</div>
        <div class="verification-panel">
          <div class="preview-heading compact">
            <div>
              <h4>Public Payments Pending Verification</h4>
              <p>Devotee no-login UPI payments stay pending until temple staff verify and post them.</p>
            </div>
            <span class="pill warn">manual review</span>
          </div>
          <div class="metric-grid three">${renderStatCards(dashboard.verification)}</div>
        </div>
        <div class="grouped-nav-preview">
          ${dashboard.groups.map(([title, copy]) => `<article><strong>${title}</strong><span>${copy}</span></article>`).join("")}
        </div>
      </div>
    `;
  }

  if (dashboard.type === "gruha") {
    return `
      <div class="legacy-dashboard gruha-dashboard">
        <div class="society-header-preview">
          <img src="${config.logo}" alt="GruhaMitra">
          <div>
            <h3>GruhaMitra Demo Society</h3>
            <p>Your Society, Digitally Simplified</p>
          </div>
          <span class="pill">Admin</span>
        </div>
        <div class="metric-grid four">${renderStatCards(dashboard.stats)}</div>
        <div class="dashboard-main-grid">
          <article>
            <h4>Quick Actions</h4>
            <div class="quick-grid">${renderActionTiles(dashboard.actions)}</div>
          </article>
          <article>
            <h4>Recent Activity</h4>
            <ul class="activity-list">${renderActivity(dashboard.activity)}</ul>
          </article>
        </div>
        <article class="trend-panel">
          <h4>Monthly Collection Trend</h4>
          <div class="trend-bars">
            ${dashboard.trend.map((month, index) => `<span style="height: ${42 + index * 10}px"><em>${month}</em></span>`).join("")}
          </div>
        </article>
        ${renderAccountingDrilldownPanel()}
      </div>
    `;
  }

  return `
    <div class="legacy-dashboard business-dashboard">
      <div class="preview-heading">
        <div>
          <h3>MitraBooks Dashboard</h3>
          <p>Accounting-first business workspace with vouchers, ledgers, reports, and compliance shortcuts.</p>
        </div>
        <span class="pill ok">finance workspace</span>
      </div>
      <div class="metric-grid four">${renderStatCards(dashboard.stats)}</div>
      <div class="dashboard-main-grid">
        <article>
          <h4>Quick Actions</h4>
          <div class="quick-grid">${renderActionTiles(dashboard.actions)}</div>
        </article>
        <article>
          <h4>Recent Activity</h4>
          <ul class="activity-list">${renderActivity(dashboard.activity)}</ul>
        </article>
      </div>
      ${renderAccountingDrilldownPanel()}
    </div>
  `;
}

async function runChecks() {
  const activeAppKey = EXPERIENCE_APP_KEYS[currentExperience] || APP_KEY;
  const health = await loadHealth(activeAppKey);
  healthPill.textContent = statusLabel(health);
  healthPill.className = `pill ${health.ok ? "ok" : "danger"}`;

  const modules = await loadModules(activeAppKey);
  renderJson(apiOutput, { health, modules });
  renderModuleState(moduleState, modules);

  if (modules.ok && currentExperience === "mitrabooks") {
    renderModules(moduleItemsFromPayload(modules.payload), { preview: false });
  } else {
    renderModules();
  }

  if (currentExperience === "platform") {
    await loadPlatformOwnerDashboard();
  } else if (currentExperience === "mandir") {
    await loadMandirDashboard();
  } else if (currentExperience === "mitrabooks" || currentExperience === "gruha") {
    const accountingDrilldown = await loadAccountingDrilldownResult();
    renderJson(apiOutput, { health, modules, accounting_drilldown: accountingDrilldown });
    dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig[currentExperience]);
  }
}

async function loadPlatformOwnerDashboard() {
  const result = await apiRequest(APP_KEY, "/api/v1/platform-owner/dashboard", { method: "GET" });
  renderJson(apiOutput, { platform_owner_dashboard: result });
  if (result.ok) {
    dashboardPreview.innerHTML = renderPlatformDashboard(result.payload);
    return;
  }

  dashboardPreview.insertAdjacentHTML(
    "afterbegin",
    `<div class="module-state warn"><strong>Platform dashboard unavailable</strong><span>Provide a super-admin access token and run checks to load live platform-owner data.</span></div>`
  );
}

function buildQueryString(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      query.set(key, String(value).trim());
    }
  });
  return query.toString();
}

function mandirListPath(kind) {
  const state = mandirListState[kind] || {};
  const path = kind === "sevas" ? "/api/v1/sevas/bookings" : "/api/v1/donations";
  const query = buildQueryString({
    limit: MANDIR_LIST_PAGE_SIZE,
    offset: state.offset || 0,
    q: state.q,
    from_date: state.from_date,
    to_date: state.to_date,
    payment_mode: kind === "donations" ? state.payment_mode : "",
    status: kind === "sevas" ? state.status : "",
  });
  return `${path}?${query}`;
}

function mandirPublicPaymentsPath() {
  const state = mandirListState.payments;
  const query = buildQueryString({
    limit: MANDIR_LIST_PAGE_SIZE,
    offset: state.offset || 0,
    q: state.q,
    status: state.status || "pending",
    payment_type: state.payment_type,
  });
  return `/api/v1/public-payments?${query}`;
}

function mandirPublicPaymentExceptionsPath() {
  const state = mandirListState.exceptions;
  const query = buildQueryString({
    older_than_hours: 24,
    limit: MANDIR_LIST_PAGE_SIZE,
    offset: state.offset || 0,
    q: state.q,
    reason: state.reason,
    status: state.status,
    payment_type: state.payment_type,
  });
  return `/api/v1/public-payments/exceptions?${query}`;
}

function accountingDrilldownPath() {
  const state = accountingDrilldownState;
  const query = buildQueryString({
    from_date: state.from_date,
    to_date: state.to_date,
    level: state.level,
    month: state.month,
    week_start: state.week_start,
    day: state.day,
  });
  return `/api/v1/accounting/reports/drilldown?${query}`;
}

async function loadAccountingDrilldownResult() {
  const activeAppKey = EXPERIENCE_APP_KEYS[currentExperience] || APP_KEY;
  const result = await apiRequest(activeAppKey, accountingDrilldownPath(), { method: "GET" });
  lastAccountingDrilldown = result.ok ? result.payload : result;
  return result;
}

async function loadAccountingVoucherDetail(journalId) {
  if (!journalId) {
    return null;
  }
  const activeAppKey = EXPERIENCE_APP_KEYS[currentExperience] || APP_KEY;
  const result = await apiRequest(activeAppKey, `/api/v1/accounting/reports/vouchers/${encodeURIComponent(journalId)}`, { method: "GET" });
  lastAccountingVoucherDetail = result.ok ? result.payload : result;
  return result;
}

async function loadMandirDashboard() {
  const stats = await apiRequest("mandirmitra", "/api/v1/dashboard/stats", { method: "GET" });
  const pendingPayments = await apiRequest("mandirmitra", mandirPublicPaymentsPath(), { method: "GET" });
  const paymentExceptions = await apiRequest("mandirmitra", mandirPublicPaymentExceptionsPath(), { method: "GET" });
  const donations = await apiRequest("mandirmitra", mandirListPath("donations"), { method: "GET" });
  const sevaBookings = await apiRequest("mandirmitra", mandirListPath("sevas"), { method: "GET" });
  const paymentAccounts = await apiRequest("mandirmitra", "/api/v1/donations/payment-accounts", { method: "GET" });
  const accounts = await apiRequest("mandirmitra", "/api/v1/accounts", { method: "GET" });
  const expenses = await apiRequest("mandirmitra", "/api/v1/journal-entries?reference_type=expense&limit=25", { method: "GET" });
  const trialBalance = await apiRequest("mandirmitra", `/api/v1/journal-entries/reports/trial-balance?as_of=${encodeURIComponent(todayIsoDate())}`, { method: "GET" });
  const reportRangeQuery = buildQueryString({
    from_date: accountingDrilldownState.from_date,
    to_date: accountingDrilldownState.to_date,
  });
  const incomeExpenditure = await apiRequest("mandirmitra", `/api/v1/journal-entries/reports/income-expenditure?${reportRangeQuery}`, { method: "GET" });
  const receiptsPayments = await apiRequest("mandirmitra", `/api/v1/journal-entries/reports/receipts-payments?${reportRangeQuery}`, { method: "GET" });
  const balanceSheet = await apiRequest("mandirmitra", `/api/v1/journal-entries/reports/balance-sheet?as_of=${encodeURIComponent(todayIsoDate())}`, { method: "GET" });
  const accountingDrilldown = await loadAccountingDrilldownResult();
  if (paymentAccounts.ok) {
    lastMandirPaymentAccounts = paymentAccounts.payload || { cash_accounts: [], bank_accounts: [] };
  }
  if (accounts.ok && Array.isArray(accounts.payload)) {
    lastMandirAccounts = accounts.payload;
  }
  if (expenses.ok && Array.isArray(expenses.payload)) {
    lastMandirExpenses = expenses.payload;
  }
  lastMandirTrialBalance = trialBalance.ok ? trialBalance.payload : trialBalance;
  lastMandirFinancialReports = {
    income_expenditure: incomeExpenditure.ok ? incomeExpenditure.payload : incomeExpenditure,
    receipts_payments: receiptsPayments.ok ? receiptsPayments.payload : receiptsPayments,
    balance_sheet: balanceSheet.ok ? balanceSheet.payload : balanceSheet,
  };
  renderJson(apiOutput, {
    mandir_dashboard_stats: stats,
    mandir_pending_public_payments: pendingPayments,
    mandir_payment_exceptions: paymentExceptions,
    mandir_recent_donations: donations,
    mandir_recent_seva_bookings: sevaBookings,
    mandir_payment_accounts: paymentAccounts,
    mandir_accounts: accounts,
    mandir_recent_expenses: expenses,
    mandir_trial_balance: trialBalance,
    mandir_income_expenditure: incomeExpenditure,
    mandir_receipts_payments: receiptsPayments,
    mandir_balance_sheet: balanceSheet,
    accounting_drilldown: accountingDrilldown,
  });
  if (stats.ok || pendingPayments.ok || paymentExceptions.ok || donations.ok || sevaBookings.ok) {
    dashboardPreview.innerHTML = renderMandirDashboard({
      stats: stats.ok ? stats.payload : {},
      pending_payments: pendingPayments.ok && Array.isArray(pendingPayments.payload) ? pendingPayments.payload : [],
      payment_exceptions: paymentExceptions.ok && Array.isArray(paymentExceptions.payload?.items) ? paymentExceptions.payload.items : [],
      payment_exception_summary: paymentExceptions.ok ? paymentExceptions.payload?.summary : {},
      recent_receipts: mandirReceiptRowsFromLists(
        donations.ok && Array.isArray(donations.payload) ? donations.payload : [],
        sevaBookings.ok && Array.isArray(sevaBookings.payload) ? sevaBookings.payload : []
      ),
      recent_donations: donations.ok && Array.isArray(donations.payload) ? donations.payload : [],
      recent_seva_bookings: sevaBookings.ok && Array.isArray(sevaBookings.payload) ? sevaBookings.payload : [],
      recent_expenses: expenses.ok && Array.isArray(expenses.payload) ? expenses.payload : lastMandirExpenses,
      trial_balance: lastMandirTrialBalance,
      financial_reports: lastMandirFinancialReports,
      payment_accounts: paymentAccounts.ok ? paymentAccounts.payload : lastMandirPaymentAccounts,
      accounts: accounts.ok && Array.isArray(accounts.payload) ? accounts.payload : lastMandirAccounts,
      receipt: lastMandirReceipt,
      form_result: lastMandirFormResult,
    });
    return;
  }

  dashboardPreview.insertAdjacentHTML(
    "afterbegin",
    `<div class="module-state warn"><strong>MandirMitra live data unavailable</strong><span>Provide a tenant-scoped MandirMitra access token and run checks to load donations, sevas, and public payments.</span></div>`
  );
}

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}

function renderBankAccountOptions(accounts = []) {
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

function mandirAccountOptionValue(account = {}) {
  return account.account_id || account.id || account.account_code || "";
}

function mandirAccountOptionLabel(account = {}) {
  const code = account.account_code ? `${account.account_code} - ` : "";
  return `${code}${account.account_name || account.name || "Account"}`;
}

function renderMandirAccountOptions(accounts = [], placeholder = "Select account") {
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

function mandirPaymentAccountOptions(paymentAccounts = lastMandirPaymentAccounts) {
  return [
    ...(Array.isArray(paymentAccounts.cash_accounts) ? paymentAccounts.cash_accounts : []),
    ...(Array.isArray(paymentAccounts.bank_accounts) ? paymentAccounts.bank_accounts : []),
  ];
}

function mandirExpenseAccountOptions(accounts = lastMandirAccounts) {
  return accounts.filter((account) => {
    const type = String(account.account_type || "").toLowerCase();
    const name = String(account.account_name || account.name || "").toLowerCase();
    return type === "expense" || name.includes("expense");
  });
}

function renderMandirCreateForms(payload = {}) {
  const paymentOptions = renderMandirAccountOptions(
    mandirPaymentAccountOptions(payload.payment_accounts),
    "Use default cash/bank"
  );
  const expenseOptions = renderMandirAccountOptions(
    mandirExpenseAccountOptions(payload.accounts),
    "Select expense account"
  );
  const today = todayIsoDate();
  const result = payload.form_result || lastMandirFormResult;
  return `
    <div class="quick-entry-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Quick Entry</h4>
          <p>Create test donations, seva bookings, and expenses without Postman.</p>
        </div>
        <span class="pill">local test entry</span>
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
              <option value="Annadanam">Annadanam</option>
              <option value="Construction Fund">Construction Fund</option>
              <option value="Corpus Fund">Corpus Fund</option>
            </select>
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

async function openMandirVerificationDialog(button) {
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

function mandirReceiptFromVerifyPayload(payload) {
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

async function submitMandirPublicPaymentVerification() {
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
    lastMandirReceipt = mandirReceiptFromVerifyPayload(result.payload);
  }
  mandirVerificationDialog.close();
  await loadMandirDashboard();
}

function openMandirRejectionDialog(button) {
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

async function submitMandirPublicPaymentRejection() {
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

function openMandirCorrectionDialog(button) {
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

async function submitMandirPublicPaymentCorrection() {
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

async function downloadMandirReceipt(button) {
  const receiptUrl = button.getAttribute("data-receipt-url") || "";
  if (!receiptUrl) {
    return;
  }
  const filename = button.getAttribute("data-receipt-filename") || "mandir-receipt.pdf";
  const result = await downloadApiFile("mandirmitra", receiptUrl, filename, { timeoutMs: 15000 });
  renderJson(apiOutput, { download_mandir_receipt: result });
}

function closeReceiptPreview() {
  receiptPreviewDialog.close();
  receiptPreviewFrame.removeAttribute("src");
  if (activeReceiptPreviewObjectUrl) {
    window.URL.revokeObjectURL(activeReceiptPreviewObjectUrl);
    activeReceiptPreviewObjectUrl = "";
  }
}

async function previewMandirReceipt(button) {
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
  if (activeReceiptPreviewObjectUrl) {
    window.URL.revokeObjectURL(activeReceiptPreviewObjectUrl);
  }
  activeReceiptPreviewObjectUrl = result.payload.object_url;
  receiptPreviewLabel.textContent = receiptLabel;
  receiptPreviewFrame.src = activeReceiptPreviewObjectUrl;
  receiptPreviewDialog.showModal();
}

function compactOptionalPhone(value) {
  return String(value || "").replace(/\D/g, "").slice(-10);
}

function formNumber(formData, key) {
  return Number(formData.get(key) || 0);
}

function formText(formData, key) {
  return String(formData.get(key) || "").trim().replace(/\s+/g, " ");
}

function setMandirFormResult(ok, title, detail) {
  lastMandirFormResult = { ok, title, detail };
}

function mandirReceiptFromCreatePayload(payload, fallbackType = "receipt") {
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

async function submitMandirDonationForm(form) {
  const formData = new FormData(form);
  const amount = formNumber(formData, "amount");
  const paymentAccountId = formText(formData, "payment_account_id");
  const payload = {
    devotee_name: formText(formData, "devotee_name"),
    devotee_phone: compactOptionalPhone(formData.get("devotee_phone")),
    amount,
    category: formText(formData, "category") || "General Donation",
    payment_mode: formText(formData, "payment_mode") || "Cash",
  };
  if (paymentAccountId) {
    payload.payment_account_id = paymentAccountId;
  }

  const result = await apiRequest("mandirmitra", "/api/v1/donations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  renderJson(apiOutput, { create_mandir_donation: result });
  if (result.ok) {
    lastMandirReceipt = mandirReceiptFromCreatePayload(result.payload, "donation") || lastMandirReceipt;
    setMandirFormResult(true, "Donation created", result.payload?.receipt_number || result.payload?.donation_id || "Receipt generated");
    form.reset();
  } else {
    setMandirFormResult(false, "Donation failed", result.payload?.detail || "Unable to create donation");
  }
  await loadMandirDashboard();
}

async function submitMandirSevaForm(form) {
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
    lastMandirReceipt = mandirReceiptFromCreatePayload(result.payload, "seva") || lastMandirReceipt;
    setMandirFormResult(true, "Seva booking created", result.payload?.receipt_number || result.payload?.id || "Receipt generated");
    form.reset();
  } else {
    setMandirFormResult(false, "Seva booking failed", result.payload?.detail || "Unable to create seva booking");
  }
  await loadMandirDashboard();
}

async function submitMandirExpenseForm(form) {
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
      lastMandirExpenses = [
        postResult.payload,
        ...lastMandirExpenses.filter((expense) => String(expense.id || "") !== String(postResult.payload.id || "")),
      ].slice(0, 25);
    }
    setMandirFormResult(true, "Expense posted", postResult.payload?.entry_number || entryId || "Journal entry posted");
    form.reset();
  } else {
    setMandirFormResult(false, "Expense post failed", postResult.payload?.detail || "Expense draft was created but not posted");
  }
  await loadMandirDashboard();
}

async function submitMandirCreateForm(form) {
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

function readMandirListFilterValues(kind) {
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

async function applyMandirListFilter(kind) {
  if (!mandirListState[kind]) {
    return;
  }
  const values = readMandirListFilterValues(kind);
  if (!values) {
    return;
  }
  mandirListState[kind] = {
    ...mandirListState[kind],
    ...values,
    offset: 0,
  };
  await loadMandirDashboard();
}

async function resetMandirListFilter(kind) {
  if (!mandirListState[kind]) {
    return;
  }
  Object.keys(mandirListState[kind]).forEach((key) => {
    mandirListState[kind][key] = key === "offset" ? 0 : "";
  });
  if (kind === "payments") {
    mandirListState.payments.status = "pending";
  }
  await loadMandirDashboard();
}

async function pageMandirList(kind, direction) {
  if (!mandirListState[kind]) {
    return;
  }
  const currentOffset = Number(mandirListState[kind].offset || 0);
  const delta = direction === "prev" ? -MANDIR_LIST_PAGE_SIZE : MANDIR_LIST_PAGE_SIZE;
  mandirListState[kind].offset = Math.max(0, currentOffset + delta);
  await loadMandirDashboard();
}

async function setMandirWorkspace(view) {
  const allowedViews = new Set(["overview", "donations", "sevas", "payments", "exceptions", "receipts", "accounting"]);
  if (!allowedViews.has(view)) {
    return;
  }
  activeMandirWorkspace = view;
  syncMandirNavActiveState();
  await loadMandirDashboard();
}

function readAccountingDrilldownFilterValues() {
  const panel = dashboardPreview.querySelector("[data-accounting-drilldown]");
  if (!panel) {
    return null;
  }
  const formData = new FormData();
  panel.querySelectorAll("input[name], select[name]").forEach((input) => {
    formData.set(input.name, input.value.trim());
  });
  return {
    from_date: String(formData.get("from_date") || accountingDrilldownState.from_date),
    to_date: String(formData.get("to_date") || accountingDrilldownState.to_date),
    level: String(formData.get("level") || "month"),
    month: "",
    week_start: "",
    day: "",
  };
}

async function refreshCurrentAccountingDrilldown() {
  const result = await loadAccountingDrilldownResult();
  renderJson(apiOutput, { accounting_drilldown: result });
  if (currentExperience === "mandir") {
    await loadMandirDashboard();
  } else {
    dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig[currentExperience]);
  }
}

async function applyAccountingDrilldownFilters() {
  const values = readAccountingDrilldownFilterValues();
  if (!values) {
    return;
  }
  accountingDrilldownState = values;
  lastAccountingVoucherDetail = null;
  await refreshCurrentAccountingDrilldown();
}

async function resetAccountingDrilldown() {
  accountingDrilldownState = {
    level: "month",
    from_date: firstDayForReports.toISOString().slice(0, 10),
    to_date: todayForReports.toISOString().slice(0, 10),
    month: "",
    week_start: "",
    day: "",
  };
  lastAccountingVoucherDetail = null;
  await refreshCurrentAccountingDrilldown();
}

async function drillAccountingReport(button) {
  accountingDrilldownState = {
    ...accountingDrilldownState,
    level: button.getAttribute("data-next-level") || "month",
    month: button.getAttribute("data-month") || accountingDrilldownState.month || "",
    week_start: button.getAttribute("data-week-start") || "",
    day: button.getAttribute("data-day") || "",
  };
  lastAccountingVoucherDetail = null;
  await refreshCurrentAccountingDrilldown();
}

async function openAccountingVoucherDetail(button) {
  const journalId = button.getAttribute("data-journal-id") || "";
  const result = await loadAccountingVoucherDetail(journalId);
  renderJson(apiOutput, { accounting_voucher_detail: result });
  if (currentExperience === "mandir") {
    await loadMandirDashboard();
  } else {
    dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig[currentExperience]);
  }
}

async function openMandirTrialBalanceLedger(button) {
  const accountId = button.getAttribute("data-account-id") || "";
  if (!accountId) {
    lastMandirLedger = { ok: false, payload: { detail: "This Trial Balance row does not include an account reference." } };
    await loadMandirDashboard();
    return;
  }
  const accountLabel = button.closest("tr")?.querySelector("td:nth-child(2)")?.textContent?.trim() || accountId;
  lastMandirLedger = { loading: true, account_label: accountLabel };
  await loadMandirDashboard();
  document.getElementById("mandir-ledger-trace")?.scrollIntoView({ behavior: "smooth", block: "start" });
  const query = buildQueryString({
    from_date: accountingDrilldownState.from_date,
    to_date: accountingDrilldownState.to_date,
  });
  const result = await apiRequest(
    "mandirmitra",
    `/api/v1/journal-entries/reports/ledger/${encodeURIComponent(accountId)}?${query}`,
    { method: "GET" }
  );
  lastMandirLedger = result.ok ? result.payload : result;
  renderJson(apiOutput, { mandir_trial_balance_ledger: result });
  await loadMandirDashboard();
  document.getElementById("mandir-ledger-trace")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function approveOnboardingRequest(requestId) {
  if (!requestId) {
    return;
  }
  const confirmed = window.confirm(`Approve onboarding request ${requestId}?`);
  if (!confirmed) {
    return;
  }

  const result = await apiRequest(APP_KEY, `/api/v1/onboarding-requests/${encodeURIComponent(requestId)}/approve`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  renderJson(apiOutput, { approve_onboarding_request: result });
  await loadPlatformOwnerDashboard();
}

async function rejectOnboardingRequest(requestId) {
  if (!requestId) {
    return;
  }
  const reason = String(window.prompt(`Reason for rejecting ${requestId}`) || "").trim();
  if (reason.length < 3) {
    return;
  }

  const result = await apiRequest(APP_KEY, `/api/v1/onboarding-requests/${encodeURIComponent(requestId)}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
  renderJson(apiOutput, { reject_onboarding_request: result });
  await loadPlatformOwnerDashboard();
}

function openTenantEntitlementsDialog(button) {
  const tenantId = button.getAttribute("data-tenant-id") || "";
  if (!tenantId) {
    return;
  }
  const tenantLabel = button.getAttribute("data-tenant-label") || tenantId;
  const currentStatus = button.getAttribute("data-tenant-status") || "active";
  const organizationType = button.getAttribute("data-organization-type") || "";
  const currentPlan = button.getAttribute("data-subscription-plan") || "free";
  const currentModules = new Set(
    String(button.getAttribute("data-enabled-modules") || "")
      .split(",")
      .map((item) => item.trim().toLowerCase())
      .filter(Boolean)
  );
  const availableModules = entitlementModulesByOrgType[organizationType] || Array.from(currentModules);

  entitlementTenantId.value = tenantId;
  entitlementTenantLabel.textContent = `${tenantLabel} (${organizationType || "tenant"})`;
  entitlementPlan.value = currentPlan;
  entitlementStatus.value = currentStatus;
  entitlementStatus.dataset.currentStatus = currentStatus;
  entitlementModules.innerHTML = availableModules.map((moduleKey) => `
    <label class="checkbox-option">
      <input type="checkbox" value="${escapeHtml(moduleKey)}" ${currentModules.has(moduleKey) ? "checked" : ""}>
      <span>${escapeHtml(moduleKey)}</span>
    </label>
  `).join("");

  entitlementDialog.showModal();
}

async function submitTenantEntitlements() {
  const tenantId = entitlementTenantId.value;
  const subscriptionPlan = entitlementPlan.value;
  const tenantStatus = entitlementStatus.value;
  const currentTenantStatus = entitlementStatus.dataset.currentStatus || "active";
  const enabledModules = Array.from(entitlementModules.querySelectorAll("input:checked"))
    .map((input) => input.value)
    .filter(Boolean);
  if (!tenantId || enabledModules.length === 0) {
    return;
  }
  const statusResult = tenantStatus === currentTenantStatus ? null : await apiRequest(
    APP_KEY,
    `/api/v1/tenants/${encodeURIComponent(tenantId)}/status`,
    {
      method: "PATCH",
      body: JSON.stringify({ status: tenantStatus }),
    }
  );
  if (statusResult && !statusResult.ok) {
    renderJson(apiOutput, { update_tenant_status: statusResult });
    return;
  }

  const result = await apiRequest(APP_KEY, `/api/v1/tenants/${encodeURIComponent(tenantId)}/entitlements`, {
    method: "PATCH",
    body: JSON.stringify({
      subscription_plan: subscriptionPlan,
      enabled_modules: enabledModules,
    }),
  });
  renderJson(apiOutput, { update_tenant_status: statusResult, update_tenant_entitlements: result });
  entitlementDialog.close();
  await loadPlatformOwnerDashboard();
}

function setExperience(nextExperience) {
  currentExperience = nextExperience;
  document.querySelectorAll(".module-switch button").forEach((button) => button.classList.remove("active"));
  document.getElementById(`mode-${nextExperience}`).classList.add("active");
  renderModules();
  if (nextExperience === "platform") {
    loadPlatformOwnerDashboard();
  } else if (nextExperience === "mandir") {
    loadMandirDashboard();
  } else if (nextExperience === "mitrabooks" || nextExperience === "gruha") {
    loadAccountingDrilldownResult().then(() => {
      dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig[currentExperience]);
    });
  }
}

document.getElementById("save-config").addEventListener("click", () => {
  setConfiguredApiBaseUrl(apiBaseInput.value);
  setAccessToken(tokenInput.value);
  runChecks();
});

document.getElementById("run-checks").addEventListener("click", runChecks);
document.getElementById("clear-token").addEventListener("click", () => {
  clearAccessToken();
  tokenInput.value = "";
  runChecks();
});
nav.addEventListener("click", (event) => {
  const link = event.target.closest("a[data-mandir-workspace]");
  if (!link || currentExperience !== "mandir") {
    return;
  }
  event.preventDefault();
  if (link.getAttribute("aria-disabled") === "true") {
    return;
  }
  setMandirWorkspace(link.dataset.mandirWorkspace || "overview");
});
dashboardPreview.addEventListener("click", (event) => {
  const button = event.target.closest("[data-platform-action], [data-mandir-action], [data-accounting-action]");
  if (!button) {
    return;
  }
  const requestId = button.getAttribute("data-request-id") || "";
  const action = button.getAttribute("data-platform-action");
  const mandirAction = button.getAttribute("data-mandir-action");
  const accountingAction = button.getAttribute("data-accounting-action");
  if (action === "approve") {
    approveOnboardingRequest(requestId);
  } else if (action === "reject") {
    rejectOnboardingRequest(requestId);
  } else if (action === "entitlements") {
    openTenantEntitlementsDialog(button);
  } else if (mandirAction === "verify-public-payment") {
    openMandirVerificationDialog(button);
  } else if (mandirAction === "reject-public-payment") {
    openMandirRejectionDialog(button);
  } else if (mandirAction === "correct-public-payment") {
    openMandirCorrectionDialog(button);
  } else if (mandirAction === "download-receipt") {
    downloadMandirReceipt(button);
  } else if (mandirAction === "preview-receipt") {
    previewMandirReceipt(button);
  } else if (mandirAction === "apply-list-filter") {
    applyMandirListFilter(button.getAttribute("data-list-kind") || "");
  } else if (mandirAction === "reset-list-filter") {
    resetMandirListFilter(button.getAttribute("data-list-kind") || "");
  } else if (mandirAction === "page-list") {
    pageMandirList(button.getAttribute("data-list-kind") || "", button.getAttribute("data-page-direction") || "next");
  } else if (mandirAction === "workspace-view") {
    setMandirWorkspace(button.getAttribute("data-workspace-view") || "overview");
  } else if (accountingAction === "apply-drilldown") {
    applyAccountingDrilldownFilters();
  } else if (accountingAction === "reset-drilldown") {
    resetAccountingDrilldown();
  } else if (accountingAction === "drill") {
    drillAccountingReport(button);
  } else if (accountingAction === "voucher-detail") {
    openAccountingVoucherDetail(button);
  } else if (accountingAction === "tb-ledger") {
    openMandirTrialBalanceLedger(button);
  }
});
dashboardPreview.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") {
    return;
  }
  const input = event.target.closest("[data-mandir-list] input, [data-mandir-list] select");
  if (!input) {
    const accountingInput = event.target.closest("[data-accounting-drilldown] input, [data-accounting-drilldown] select");
    if (!accountingInput) {
      return;
    }
    event.preventDefault();
    applyAccountingDrilldownFilters();
    return;
  }
  event.preventDefault();
  const panel = input.closest("[data-mandir-list]");
  applyMandirListFilter(panel?.getAttribute("data-mandir-list") || "");
});
dashboardPreview.addEventListener("submit", (event) => {
  const form = event.target.closest("[data-mandir-create-form]");
  if (!form) {
    return;
  }
  event.preventDefault();
  submitMandirCreateForm(form);
});
entitlementForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitTenantEntitlements();
});
mandirVerificationForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitMandirPublicPaymentVerification();
});
mandirRejectionForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitMandirPublicPaymentRejection();
});
mandirCorrectionForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitMandirPublicPaymentCorrection();
});
document.getElementById("entitlement-close").addEventListener("click", () => entitlementDialog.close());
document.getElementById("entitlement-cancel").addEventListener("click", () => entitlementDialog.close());
document.getElementById("mandir-verification-close").addEventListener("click", () => mandirVerificationDialog.close());
document.getElementById("mandir-verification-cancel").addEventListener("click", () => mandirVerificationDialog.close());
document.getElementById("mandir-rejection-close").addEventListener("click", () => mandirRejectionDialog.close());
document.getElementById("mandir-rejection-cancel").addEventListener("click", () => mandirRejectionDialog.close());
document.getElementById("mandir-correction-close").addEventListener("click", () => mandirCorrectionDialog.close());
document.getElementById("mandir-correction-cancel").addEventListener("click", () => mandirCorrectionDialog.close());
document.getElementById("receipt-preview-close").addEventListener("click", closeReceiptPreview);
receiptPreviewDialog.addEventListener("close", () => {
  receiptPreviewFrame.removeAttribute("src");
  if (activeReceiptPreviewObjectUrl) {
    window.URL.revokeObjectURL(activeReceiptPreviewObjectUrl);
    activeReceiptPreviewObjectUrl = "";
  }
});
document.getElementById("mode-mitrabooks").addEventListener("click", () => setExperience("mitrabooks"));
document.getElementById("mode-platform").addEventListener("click", () => setExperience("platform"));
document.getElementById("mode-mandir").addEventListener("click", () => setExperience("mandir"));
document.getElementById("mode-gruha").addEventListener("click", () => setExperience("gruha"));

apiBaseInput.value = getConfiguredApiBaseUrl();
tokenInput.value = getAccessToken();
renderModules();
renderModuleState(moduleState);
runChecks();
