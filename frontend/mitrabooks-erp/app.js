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

// ============================================
// THEME MANAGEMENT (PWA-Compatible)
// ============================================

const THEME_STORAGE_KEY = "mitrabooks-theme";

function businessNavigationGroups() {
  return [
    {
      name: "Main Workspaces",
      items: [
        { label: "Dashboard", businessWorkspace: "overview", icon: "DB", module: { module_key: "business", frontend_path: "/business", enabled: true } },
        { label: "Parties", businessWorkspace: "parties", icon: "PT", module: { module_key: "business", frontend_path: "/business/parties", enabled: true } },
      ],
    },
    {
      name: "Core Ledger",
      items: [
        { label: "Core Ledger", businessWorkspace: "accounting", icon: "CL", module: { module_key: "accounting", frontend_path: "/accounting", enabled: true } },
        { label: "Journal Post", businessWorkspace: "vouchers", icon: "JP", module: { module_key: "business", frontend_path: "/business/vouchers", enabled: true } },
        { label: "Audit Trails", businessWorkspace: "audit", icon: "AT", module: { module_key: "audit", frontend_path: "/audit", enabled: true } },
      ],
    },
    {
      name: "Income (Sales)",
      items: [
        { label: "Sales", businessWorkspace: "sales", icon: "SL", module: { module_key: "sales", frontend_path: "/business/sales", enabled: false } },
        { label: "Credit Notes", businessWorkspace: "credit-notes", icon: "CN", module: { module_key: "sales", frontend_path: "/business/credit-notes", enabled: false } },
      ],
    },
    {
      name: "Expenses (Purchases)",
      items: [
        { label: "Bills (Vendor)", businessWorkspace: "bills", icon: "BL", module: { module_key: "purchase", frontend_path: "/business/bills", enabled: false } },
        { label: "Purchase Orders", businessWorkspace: "purchase-orders", icon: "PO", module: { module_key: "purchase", frontend_path: "/business/purchase-orders", enabled: false } },
        { label: "Debit Notes", businessWorkspace: "debit-notes", icon: "DN", module: { module_key: "purchase", frontend_path: "/business/debit-notes", enabled: false } },
        { label: "Expenses log", businessWorkspace: "expenses", icon: "EX", module: { module_key: "business", frontend_path: "/business/expenses", enabled: false } },
      ],
    },
    {
      name: "Banking & Treasury",
      items: [
        { label: "Bank Feeds", businessWorkspace: "bank-feeds", icon: "BF", module: { module_key: "banking", frontend_path: "/business/bank-feeds", enabled: false } },
        { label: "UPI / QR Payments", businessWorkspace: "upi-payments", icon: "UP", module: { module_key: "payments", frontend_path: "/business/upi-payments", enabled: false } },
        { label: "Reconciliation", businessWorkspace: "reconciliation", icon: "RC", module: { module_key: "accounting", frontend_path: "/accounting/reconciliation", enabled: false }, badge: "3" },
      ],
    },
    {
      name: "Taxes & Compliance",
      items: [
        { label: "GST Returns", businessWorkspace: "gst-returns", icon: "GT", module: { module_key: "gst", frontend_path: "/gst/returns", enabled: false } },
        { label: "TDS / TCS", businessWorkspace: "tds-tcs", icon: "TD", module: { module_key: "tax", frontend_path: "/tax/tds-tcs", enabled: false } },
        { label: "CA Access Portal", businessWorkspace: "ca-access", icon: "CA", module: { module_key: "ca_access", frontend_path: "/business/ca-access", enabled: false } },
      ],
    },
    {
      name: "Intelligence & Reports",
      items: [
        { label: "Financial Statements", businessWorkspace: "financial-statements", icon: "FS", module: { module_key: "accounting", frontend_path: "/accounting/reports", enabled: false } },
        { label: "Analytics", businessWorkspace: "analytics", icon: "AN", module: { module_key: "analytics", frontend_path: "/business/analytics", enabled: false } },
      ],
    },
    {
      name: "Configuration & Extensions",
      items: [
        { label: "Future Hub & Add-ons", businessWorkspace: "addons", icon: "FH", module: { module_key: "addons", frontend_path: "/business/addons", enabled: false }, badge: "New" },
        { label: "+ Custom Menu", businessWorkspace: "custom-menu", icon: "CM", module: { module_key: "custom_menu", frontend_path: "/business/custom-menu", enabled: false } },
      ],
    },
  ];
}

function businessNavigationItems() {
  return businessNavigationGroups().flatMap((group) => group.items);
}

/**
 * Set the app theme (dark or light)
 * Persists to localStorage for offline retention
 */
function setTheme(theme) {
  const validTheme = theme === "light" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", validTheme);
  localStorage.setItem(THEME_STORAGE_KEY, validTheme);
  updateThemeButtons(validTheme);
}

/**
 * Get the current theme or user preference
 */
function getTheme() {
  const saved = localStorage.getItem(THEME_STORAGE_KEY);
  if (saved) {
    return saved;
  }

  // Check system preference
  if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    return "dark";
  }

  return "dark"; // Default to dark
}

/**
 * Initialize theme on app load
 */
function initializeTheme() {
  const theme = getTheme();
  document.documentElement.setAttribute("data-theme", theme);
  updateThemeButtons(theme);
}

/**
 * Update UI buttons to show active theme
 */
function updateThemeButtons(theme) {
  const darkBtn = document.getElementById("theme-dark-btn");
  const lightBtn = document.getElementById("theme-light-btn");

  if (darkBtn) {
    darkBtn.classList.toggle("active", theme === "dark");
  }
  if (lightBtn) {
    lightBtn.classList.toggle("active", theme === "light");
  }
}

/**
 * Listen for system theme changes (respects user's OS preference)
 */
if (window.matchMedia) {
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
    if (!localStorage.getItem(THEME_STORAGE_KEY)) {
      setTheme(e.matches ? "dark" : "light");
    }
  });
}

const APP_KEY = "mitrabooks";
const DEFAULT_DEPLOYED_API_BASE_URL = "https://sanmitra-unified-next-staging-sg.onrender.com";
const LOGIN_EMAIL_STORAGE_KEY = "sanmitra_mitrabooks_login_email";
const EXPERIENCE_APP_KEYS = {
  mitrabooks: "mitrabooks",
  platform: "mitrabooks",
  mandir: "mandirmitra",
  gruha: "gruhamitra",
};

function isMandirHost() {
  const host = String(window.location.hostname || "").toLowerCase();
  return host === "mandirmitra.sanmitratech.in"
    || host === "www.mandirmitra.sanmitratech.in"
    || host.includes("mandirmitra");
}

function isGruhaHost() {
  const host = String(window.location.hostname || "").toLowerCase();
  return host === "gruhamitra.sanmitratech.in"
    || host === "www.gruhamitra.sanmitratech.in"
    || host.includes("gruhamitra");
}

function isProductionShell() {
  const host = String(window.location.hostname || "").toLowerCase();
  return host && host !== "localhost" && host !== "127.0.0.1" && host !== "::1";
}

function initialExperience() {
  if (isMandirHost()) {
    return "mandir";
  }
  if (isGruhaHost()) {
    return "gruha";
  }
  return "mitrabooks";
}
const entitlementModulesByOrgType = {
  TEMPLE: ["temple", "accounting", "audit"],
  HOUSING: ["housing", "accounting", "audit"],
  BUSINESS: ["business", "accounting", "gst", "inventory", "audit"],
  PROFESSIONAL: ["professional", "accounting", "billing", "audit"],
};

const experienceConfig = {
  mitrabooks: {
    title: "MitraBooks Pro",
    subtitle: "Unified Enterprise ERP",
    logo: "../assets/brand/mitrabooks-pro-logo.png",
    video: "../assets/brand/mitrabooks-pro-logo.mp4",
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
      { module_key: "temple", display_name: "Sevas", frontend_path: "/temple/sevas", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Donations", frontend_path: "/temple/donations", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Devotees", frontend_path: "/temple/devotees", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Public Payments", frontend_path: "/temple/public-payments", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Receipts", frontend_path: "/temple/receipts", nav_group: "Operations", enabled: true },
      { module_key: "audit", display_name: "Reports", frontend_path: "/temple/reports", nav_group: "Administration", enabled: true },
      { module_key: "temple", display_name: "Panchang", frontend_path: "/temple/panchang", nav_group: "Operations", enabled: true },
      { module_key: "temple", display_name: "Settings", frontend_path: "/temple/settings", nav_group: "Administration", enabled: true },
      { module_key: "audit", display_name: "Implementation Checks", frontend_path: "/temple/implementation-checks", nav_group: "Administration", enabled: true },
      { module_key: "platform_owner", display_name: "Platform Owners", frontend_path: "/platform-owner/dashboard", nav_group: "Administration", enabled: true },
      { module_key: "accounting", display_name: "Accounting", frontend_path: "/accounting", nav_group: "Finance", enabled: true },
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

let currentExperience = initialExperience();
let lastMandirReceipt = null;
let activeReceiptPreviewObjectUrl = "";
let activeMandirWorkspace = "overview";
let activeGruhaWorkspace = "overview";
let lastMandirPaymentAccounts = { cash_accounts: [], bank_accounts: [] };
let lastMandirAccounts = [];
let lastMandirFormResult = null;
let lastMandirExpenses = [];
let lastMandirTrialBalance = null;
let lastMandirLedger = null;
let lastMandirFinancialReports = {};
let lastMandirPanchang = null;
let lastMandirOperationalReports = {};
let lastMandirModuleConfig = {};
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
let lastGruhaData = null;

const appRoot = document.getElementById("app-root");
const brandLogo = document.getElementById("brand-logo");
const brandTitle = document.getElementById("brand-title");
const brandSubtitle = document.getElementById("brand-subtitle");
const topbarTitle = document.getElementById("topbar-title");
const topbarSubtitle = document.getElementById("topbar-subtitle");
const appKeyLabel = document.getElementById("app-key-label");
const sessionPill = document.getElementById("session-pill");
const loginStatus = document.getElementById("login-status");
const loginEmail = document.getElementById("login-email");
const loginPassword = document.getElementById("login-password");
const topbarCurrent = document.getElementById("topbar-current");
const topbarUser = document.getElementById("topbar-user");
const topbarAvatar = document.getElementById("topbar-avatar");
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
const sidebarAvatar = document.getElementById("sidebar-avatar");
const sidebarUserName = document.getElementById("sidebar-user-name");
const sidebarUserRole = document.getElementById("sidebar-user-role");
const currentOrgType = document.getElementById("current-org-type");
const currentOrgTenant = document.getElementById("current-org-tenant");
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
const mandirCancelReceiptDialog = document.getElementById("mandir-cancel-receipt-dialog");
const mandirCancelReceiptForm = document.getElementById("mandir-cancel-receipt-form");
const mandirCancelReceiptUrl = document.getElementById("mandir-cancel-receipt-url");
const mandirCancelReceiptLabel = document.getElementById("mandir-cancel-receipt-label");
const mandirCancelReceiptReason = document.getElementById("mandir-cancel-receipt-reason");
const mandirCancelRefundMode = document.getElementById("mandir-cancel-refund-mode");
const mandirCancelRefundReference = document.getElementById("mandir-cancel-refund-reference");
const mandirCancelReceiptSubmit = document.getElementById("mandir-cancel-receipt-submit");
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
const mandirSplash = document.getElementById("mandir-splash");
const mandirSplashVideo = document.getElementById("mandir-splash-video");
const mandirSplashImage = document.getElementById("mandir-splash-image");
const brandSplashCopy = document.getElementById("brand-splash-copy");

function renderModules(modules = experienceConfig[currentExperience].modules, options = {}) {
  const config = experienceConfig[currentExperience];
  const preview = options.preview !== false;
  appRoot.className = `app ${config.theme} ${isProductionShell() ? "production-shell" : ""} ${isMandirHost() ? "mandir-domain" : ""}`.trim();
  updateSessionUi();
  updateTrustedContextUi();
  if (appKeyLabel) {
    appKeyLabel.textContent = EXPERIENCE_APP_KEYS[currentExperience] || APP_KEY;
  }
  if (topbarTitle) {
    topbarTitle.textContent = currentExperience === "mandir" ? "MandirMitra Temple" : config.title;
  }
  if (topbarSubtitle) {
    topbarSubtitle.textContent = currentExperience === "mandir"
      ? "Temple / Trust Management & Accounting System"
      : config.subtitle;
  }
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

  const navItems = currentExperience === "mandir"
    ? mandirNavigationItems()
    : currentExperience === "gruha"
      ? gruhaNavigationItems()
      : currentExperience === "mitrabooks"
        ? businessNavigationItems()
        : modules.map((module) => ({
        label: `${module.nav_group || "Module"}: ${module.display_name}`,
        module,
        workspace: mandirWorkspaceFromModule(module),
        }));

  if (currentExperience === "mitrabooks") {
    renderGroupedNav(businessNavigationGroups());
  } else {
  navItems.forEach((item) => {
    const module = item.module || {};
    const link = document.createElement("a");
    link.href = "#";
    link.className = `${module.enabled === false ? "locked" : ""} ${item.child ? "child" : ""}`.trim();
    link.setAttribute("aria-disabled", module.enabled ? "false" : "true");
    link.dataset.moduleKey = module.module_key || "";
    link.dataset.frontendPath = module.frontend_path || "";
    const mandirWorkspace = item.workspace || mandirWorkspaceFromModule(module);
    if (mandirWorkspace) {
      link.dataset.mandirWorkspace = mandirWorkspace;
    }
    if (item.gruhaWorkspace) {
      link.dataset.gruhaWorkspace = item.gruhaWorkspace;
    }
    if (item.businessWorkspace) {
      link.dataset.businessWorkspace = item.businessWorkspace;
    }
    link.dataset.navIcon = item.icon || navIconForMandirWorkspace(mandirWorkspace);
    link.textContent = item.label;
    nav.appendChild(link);
  });
  }

  modules.forEach((module) => {
    const item = document.createElement("li");
    item.innerHTML = `
      <strong>${module.display_name}</strong>
      <span class="muted">${module.module_key} -> ${module.frontend_path || "no frontend path yet"}</span>
      <span class="pill ${module.enabled ? "ok" : "warn"}">${module.enabled ? "enabled" : preview ? "preview only" : "available or planned"}</span>
    `;
    moduleList.appendChild(item);
  });
  syncMandirNavActiveState();
  syncGruhaNavActiveState();
  syncBusinessNavActiveState();
}

function mandirNavigationItems() {
  return [
    { label: "Dashboard", workspace: "overview", icon: "▦", module: { module_key: "temple", frontend_path: "/temple/dashboard", enabled: true } },
    { label: "Sevas", workspace: "sevas", icon: "♜", module: { module_key: "temple", frontend_path: "/temple/sevas", enabled: true } },
    { label: "Book Sevas", workspace: "book-sevas", icon: "♜", child: true, module: { module_key: "temple", frontend_path: "/temple/sevas/book", enabled: true } },
    { label: "Seva Bookings / Reschedule", workspace: "seva-bookings", icon: "▤", child: true, module: { module_key: "temple", frontend_path: "/temple/sevas/bookings", enabled: true } },
    { label: "Seva Management", workspace: "seva-management", icon: "▤", child: true, module: { module_key: "temple", frontend_path: "/temple/sevas/manage", enabled: true } },
    { label: "Reschedule Approval", workspace: "reschedule-approval", icon: "✓", child: true, module: { module_key: "temple", frontend_path: "/temple/sevas/reschedule", enabled: true } },
    { label: "Donations", workspace: "donations", icon: "▰", module: { module_key: "temple", frontend_path: "/temple/donations", enabled: true } },
    { label: "Devotees", workspace: "devotees", icon: "●●", module: { module_key: "temple", frontend_path: "/temple/devotees", enabled: true } },
    { label: "Public Payments", workspace: "payments", icon: "▣", module: { module_key: "temple", frontend_path: "/temple/public-payments", enabled: true } },
    { label: "Payment Exceptions", workspace: "exceptions", icon: "!", child: true, module: { module_key: "temple", frontend_path: "/temple/payment-exceptions", enabled: true } },
    { label: "Receipts", workspace: "receipts", icon: "▤", module: { module_key: "temple", frontend_path: "/temple/receipts", enabled: true } },
    { label: "Reports", workspace: "reports", icon: "▥", module: { module_key: "audit", frontend_path: "/temple/reports", enabled: true } },
    { label: "Panchang", workspace: "panchang", icon: "□", module: { module_key: "temple", frontend_path: "/temple/panchang", enabled: true } },
    { label: "Settings", workspace: "settings", icon: "⚙", module: { module_key: "temple", frontend_path: "/temple/settings", enabled: true } },
    { label: "Implementation Checks", workspace: "implementation", icon: "☑", module: { module_key: "audit", frontend_path: "/temple/implementation-checks", enabled: true } },
    { label: "Platform Owners", workspace: "platform-owners", icon: "♜", module: { module_key: "platform_owner", frontend_path: "/platform-owner/dashboard", enabled: true } },
    { label: "Accounting", workspace: "accounting", icon: "▣", module: { module_key: "accounting", frontend_path: "/accounting", enabled: true } },
    { label: "Chart of Accounts", workspace: "accounting", icon: "▥", child: true, module: { module_key: "accounting", frontend_path: "/accounting/accounts", enabled: true } },
    { label: "Quick Expense", workspace: "accounting", icon: "₹", child: true, module: { module_key: "accounting", frontend_path: "/accounting/expenses", enabled: true } },
    { label: "Journal Entries", workspace: "accounting", icon: "▤", child: true, module: { module_key: "accounting", frontend_path: "/accounting/journals", enabled: true } },
    { label: "Bank Reconciliation", workspace: "accounting", icon: "▰", child: true, module: { module_key: "accounting", frontend_path: "/accounting/bank", enabled: true } },
    { label: "Financial Closing", workspace: "accounting", icon: "▣", child: true, module: { module_key: "accounting", frontend_path: "/accounting/closing", enabled: true } },
    { label: "UPI Payments", workspace: "payments", icon: "▭", child: true, module: { module_key: "temple", frontend_path: "/temple/upi-payments", enabled: true } },
    { label: "Accounting Reports", workspace: "accounting", icon: "▥", child: true, module: { module_key: "accounting", frontend_path: "/accounting/reports", enabled: true } },
  ];
}

function gruhaNavigationItems() {
  return [
    { label: "Dashboard", gruhaWorkspace: "overview", icon: "D", module: { module_key: "housing", frontend_path: "/housing/dashboard", enabled: true } },
    { label: "Maintenance", gruhaWorkspace: "maintenance", icon: "M", module: { module_key: "housing", frontend_path: "/housing/maintenance", enabled: true } },
    { label: "Members", gruhaWorkspace: "members", icon: "U", module: { module_key: "housing", frontend_path: "/housing/members", enabled: true } },
    { label: "Flats", gruhaWorkspace: "flats", icon: "F", child: true, module: { module_key: "housing", frontend_path: "/housing/flats", enabled: true } },
    { label: "Complaints", gruhaWorkspace: "complaints", icon: "C", module: { module_key: "housing", frontend_path: "/housing/complaints", enabled: true } },
    { label: "Messages", gruhaWorkspace: "messages", icon: "N", module: { module_key: "housing", frontend_path: "/housing/messages", enabled: true } },
    { label: "Meetings", gruhaWorkspace: "meetings", icon: "G", module: { module_key: "housing", frontend_path: "/housing/meetings", enabled: true } },
    { label: "Assets", gruhaWorkspace: "assets", icon: "A", module: { module_key: "housing", frontend_path: "/housing/assets", enabled: true } },
    { label: "Accounting", gruhaWorkspace: "accounting", icon: "L", module: { module_key: "accounting", frontend_path: "/accounting", enabled: true } },
    { label: "Reports", gruhaWorkspace: "reports", icon: "R", module: { module_key: "housing", frontend_path: "/housing/reports", enabled: true } },
    { label: "Settings", gruhaWorkspace: "settings", icon: "S", module: { module_key: "audit", frontend_path: "/housing/settings", enabled: true } },
  ];
}

function legacyBusinessNavigationItems() {
  return [
    { label: "Dashboard", businessWorkspace: "overview", icon: "▦", module: { module_key: "business", frontend_path: "/business", enabled: true } },
    { label: "Parties", businessWorkspace: "parties", icon: "●", module: { module_key: "business", frontend_path: "/business/parties", enabled: true } },
    { label: "Vouchers", businessWorkspace: "vouchers", icon: "▤", module: { module_key: "business", frontend_path: "/business/vouchers", enabled: true } },
    { label: "Audit Trail", businessWorkspace: "audit", icon: "⏱", module: { module_key: "audit", frontend_path: "/audit", enabled: true } },
    { label: "Accounting", businessWorkspace: "accounting", icon: "▣", module: { module_key: "accounting", frontend_path: "/accounting", enabled: true } },
  ];
}

/**
 * Load grouped navigation from /api/v1/modules/me (Phase 1D)
 * Groups modules by nav_group for professional accounting app layout
 */
async function loadAndRenderGroupedNav(appKey) {
  if (appKey === "mitrabooks") {
    renderGroupedNav(businessNavigationGroups());
    return;
  }
  try {
    const response = await loadModules(appKey);
    if (!response.ok) {
      console.log("[Nav] API returned status", response.status, "- using fallback");
      renderGroupedNavFromItems(businessNavigationItems());
      return;
    }

    const payload = response.payload || {};
    const modules = payload.enabled_modules || [];

    if (!Array.isArray(modules) || modules.length === 0) {
      console.log("[Nav] No modules in response - using fallback");
      renderGroupedNavFromItems(businessNavigationItems());
      return;
    }

    console.log("[Nav] Loaded", modules.length, "modules from API");

    // Group modules by nav_group field
    const grouped = {};
    const groupOrder = [
      "Main Workspaces",
      "Core Ledger",
      "Income (Sales)",
      "Expenses (Purchases)",
      "Banking & Treasury",
      "Taxes & Compliance",
      "Intelligence & Reports",
      "Configuration & Extensions",
    ];

    modules.forEach(module => {
      const group = module.nav_group || "Modules";
      if (!grouped[group]) {
        grouped[group] = [];
      }
      grouped[group].push({
        label: module.display_name,
        businessWorkspace: module.frontend_path?.split("/").pop() || "default",
        icon: module.icon || "●",
        module: {
          module_key: module.module_key,
          frontend_path: module.frontend_path,
          enabled: module.enabled !== false,
          display_name: module.display_name,
        },
      });
    });

    // Sort groups by predefined order
    const sortedGroups = [];
    groupOrder.forEach(group => {
      if (grouped[group]) {
        sortedGroups.push({ name: group, items: grouped[group] });
      }
    });

    // Add remaining groups not in predefined order
    Object.keys(grouped).forEach(group => {
      if (!groupOrder.includes(group)) {
        sortedGroups.push({ name: group, items: grouped[group] });
      }
    });

    if (sortedGroups.length === 0) {
      console.log("[Nav] No groups created - using fallback");
      renderGroupedNavFromItems(businessNavigationItems());
      return;
    }

    renderGroupedNav(sortedGroups);
    console.log("[Nav] Rendered grouped navigation with", sortedGroups.length, "groups");
  } catch (error) {
    console.error("[Nav] Error loading grouped navigation:", error);
    renderGroupedNavFromItems(businessNavigationItems());
  }
}

/**
 * Render navigation with group headers (Phase 1D)
 */
function renderGroupedNav(groups) {
  const nav = document.getElementById("nav");
  if (!nav) return;

  nav.innerHTML = "";

  groups.forEach((group, groupIndex) => {
    const groupId = `business-nav-group-${groupIndex}`;
    const header = document.createElement("button");
    header.className = "nav-group-toggle";
    header.type = "button";
    header.dataset.navGroupToggle = groupId;
    header.setAttribute("aria-expanded", "true");
    header.setAttribute("aria-controls", groupId);
    header.innerHTML = `<span>${escapeHtml(group.name)}</span><span aria-hidden="true">v</span>`;
    nav.appendChild(header);

    const panel = document.createElement("div");
    panel.className = "nav-group-items";
    panel.id = groupId;
    panel.dataset.navGroupItems = groupId;
    group.items.forEach(item => {
      const link = document.createElement("a");
      link.href = "#";
      link.className = item.module.enabled ? "erp-nav-link" : "erp-nav-link locked";
      link.setAttribute("aria-disabled", item.module.enabled ? "false" : "true");
      link.dataset.moduleKey = item.module.module_key || "";
      link.dataset.frontendPath = item.module.frontend_path || "";
      link.dataset.businessWorkspace = item.businessWorkspace || "";
      link.dataset.navIcon = item.icon;
      link.innerHTML = `
        <span class="nav-icon">${escapeHtml(item.icon || "")}</span>
        <span class="nav-label">${escapeHtml(item.label)}</span>
        ${item.badge ? `<span class="nav-badge">${escapeHtml(item.badge)}</span>` : ""}
      `;
      panel.appendChild(link);
    });
    nav.appendChild(panel);
  });

  syncBusinessNavActiveState();
}

/**
 * Fallback: Render hardcoded navigation items (no grouping, while backend adds nav_group)
 */
function renderGroupedNavFromItems(items) {
  const nav = document.getElementById("nav");
  if (!nav) return;

  nav.innerHTML = "";
  console.log("[Nav] Using fallback with", items.length, "hardcoded items");

  // Add a single "Main" group header for fallback
  const header = document.createElement("div");
  header.className = "nav-group-header";
  header.textContent = "Main";
  header.style.cssText = `
    font-size: 11px;
    font-weight: 700;
    color: var(--text-muted, #94a3b8);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 12px 16px 8px;
    margin-top: 0;
  `;
  nav.appendChild(header);

  items.forEach(item => {
    const link = document.createElement("a");
    link.href = "#";
    link.className = item.module.enabled === false ? "locked" : "";
    link.setAttribute("aria-disabled", item.module.enabled ? "false" : "true");
    link.dataset.moduleKey = item.module.module_key || "";
    link.dataset.frontendPath = item.module.frontend_path || "";
    link.dataset.businessWorkspace = item.businessWorkspace || "";
    link.dataset.navIcon = item.icon;
    link.textContent = item.label;
    nav.appendChild(link);
    console.log("[Nav]   - Main:", item.label);
  });

  syncBusinessNavActiveState();
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

function renderBusinessExecutiveDashboard() {
  const voucherCount = lastAccountingDrilldown?.summary?.voucher_count ?? 0;
  const partyCount = Array.isArray(lastBusinessParties) ? lastBusinessParties.length : 0;
  const accountCount = Array.isArray(lastBusinessAccounts) ? lastBusinessAccounts.length : 0;
  const months = [
    ["Apr", 8.2, 5.1],
    ["May", 10.4, 6.8],
    ["Jun", 12.8, 7.4],
    ["Jul", 11.6, 7.0],
    ["Aug", 14.2, 8.3],
    ["Sep", 15.8, 9.1],
  ];
  const maxValue = Math.max(...months.flatMap(([, income, expense]) => [income, expense]));
  const bars = months.map(([label, income, expense]) => {
    const incomeHeight = Math.max(16, Math.round((income / maxValue) * 132));
    const expenseHeight = Math.max(16, Math.round((expense / maxValue) * 132));
    return `
      <div class="finance-bar-group">
        <div class="finance-bars" aria-label="${label} income Rs. ${income}L and expenses Rs. ${expense}L">
          <span class="income-bar" style="height: ${incomeHeight}px"></span>
          <span class="expense-bar" style="height: ${expenseHeight}px"></span>
        </div>
        <small>${label}</small>
      </div>
    `;
  }).join("");

  return `
    <section class="executive-dashboard" aria-label="MitraBooks executive dashboard">
      <div class="executive-hero">
        <div>
          <span class="workbench-kicker">FY 2026-27 Operating View</span>
          <h3>Income, expenses, and cash movement</h3>
          <p>Use this area for the live business pulse: revenue trend, purchase pressure, collections, payables, and leadership actions.</p>
        </div>
        <div class="executive-kpi-strip">
          <article>
            <span>Income</span>
            <strong>Rs. 12.8L</strong>
            <small>+18% vs last month</small>
          </article>
          <article>
            <span>Expenses</span>
            <strong>Rs. 7.4L</strong>
            <small>Office, purchases, vendor bills</small>
          </article>
          <article>
            <span>Net Position</span>
            <strong>Rs. 5.4L</strong>
            <small>Before tax provisions</small>
          </article>
        </div>
      </div>

      <div class="finance-dashboard-grid">
        <article class="finance-chart-card">
          <div class="preview-heading compact">
            <div>
              <h4>Sales & Expenses Trend</h4>
              <p>Scoped performance metrics for the active BUSINESS Suite.</p>
            </div>
            <span class="pill ok">CEO view</span>
          </div>
          <div class="finance-chart" role="img" aria-label="Monthly income and expense bar chart">
            ${bars}
          </div>
          <div class="chart-legend">
            <span><i class="income-dot"></i>Income</span>
            <span><i class="expense-dot"></i>Expenses</span>
          </div>
        </article>

        <article class="ceo-panel">
          <div class="preview-heading compact">
            <div class="ceo-title-block">
              <span class="ceo-orbit" aria-hidden="true"></span>
              <h4>CEO Insights</h4>
              <span class="ai-badge">AI Enabled</span>
              <p>Real-time ledger analytics and operating summaries.</p>
            </div>
          </div>
          <div class="ceo-insight-list" role="list">
            <div class="ceo-insight-row" role="listitem">
              <span class="insight-spark" aria-hidden="true"></span>
              <span>Cash flow is highly robust with</span>
              <strong>65.1x coverage</strong>
              <span>on pending vendor obligations.</span>
            </div>
            <div class="ceo-insight-row" role="listitem">
              <span class="insight-spark" aria-hidden="true"></span>
              <span>Average receivables collections period has reduced to</span>
              <strong>28 days</strong>
              <span>, boosting liquidity.</span>
            </div>
            <div class="ceo-insight-row" role="listitem">
              <span class="insight-spark" aria-hidden="true"></span>
              <span>Inventory turnover rate for consumables is currently running at</span>
              <strong>4.2x</strong>
              <span>.</span>
            </div>
          </div>
          <div class="ceo-ask-row">
            <input type="text" value="" placeholder="Ask AI: 'What is our GST exposure?' or 'Rent balance?'" aria-label="Ask AI for ledger insight">
            <button type="button">Ask</button>
          </div>
          <p class="ceo-footnote">${voucherCount} posted voucher(s), ${partyCount} party record(s), and ${accountCount} account(s) are available for the current dashboard context.</p>
        </article>
      </div>
    </section>
  `;
}

function resultPayload(result, fallback) {
  return result && result.ok ? result.payload : fallback;
}

function resultRows(result) {
  const payload = resultPayload(result, []);
  if (Array.isArray(payload)) {
    return payload;
  }
  if (Array.isArray(payload?.items)) {
    return payload.items;
  }
  if (Array.isArray(payload?.rows)) {
    return payload.rows;
  }
  return [];
}

function statusDetailText(payload) {
  if (!payload) {
    return "";
  }
  if (typeof payload === "string") {
    return payload;
  }
  if (Array.isArray(payload)) {
    return payload.map(statusDetailText).filter(Boolean).join("; ");
  }
  if (typeof payload === "object") {
    const direct = payload.detail || payload.message || payload.error;
    if (direct) {
      return statusDetailText(direct);
    }
    const textValues = Object.values(payload)
      .map((value) => statusDetailText(value))
      .filter(Boolean);
    return textValues.slice(0, 3).join("; ");
  }
  return String(payload);
}

function renderStatusBlock(title, result) {
  if (!result || result.ok) {
    return "";
  }
  const detail = statusDetailText(result.payload);
  return `<div class="module-state warn"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(detail || "Unable to load this GruhaMitra compatibility endpoint.")}</span></div>`;
}

function currentBillingPeriodQuery() {
  const now = new Date();
  const month = now.getMonth() + 1;
  const year = now.getFullYear();
  return `month=${encodeURIComponent(month)}&year=${encodeURIComponent(year)}`;
}

function renderSimpleTable(rows, columns, emptyText) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `<p class="muted">${escapeHtml(emptyText)}</p>`;
  }
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>${columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join("")}</tr>
        </thead>
        <tbody>
          ${rows.slice(0, 12).map((row) => `
            <tr>
              ${columns.map((column) => `<td>${escapeHtml(column.value(row))}</td>`).join("")}
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function mandirWorkspaceFromModule(module = {}) {
  const path = String(module.frontend_path || "").toLowerCase();
  const displayName = String(module.display_name || "").toLowerCase();
  if (path.includes("/donations") || displayName.includes("donation")) {
    return "donations";
  }
  if (path.includes("/devotees") || displayName.includes("devotee")) {
    return "devotees";
  }
  if (path.includes("/sevas") || displayName.includes("seva")) {
    return "sevas";
  }
  if (path.includes("/public-payments") || displayName.includes("public payment")) {
    return "payments";
  }
  if (path.includes("/receipts") || displayName.includes("receipt")) {
    return "receipts";
  }
  if (path.includes("/panchang") || displayName.includes("panchang")) {
    return "panchang";
  }
  if (path.includes("/reports") || displayName.includes("report")) {
    return "reports";
  }
  if (path.includes("/settings") || displayName.includes("setting")) {
    return "settings";
  }
  if (path.includes("/implementation") || displayName.includes("implementation")) {
    return "implementation";
  }
  if (path.includes("/platform-owner") || displayName.includes("platform owner")) {
    return "platform-owners";
  }
  if (path.includes("/accounting") || displayName.includes("accounting")) {
    return "accounting";
  }
  if (path.includes("/dashboard") || displayName.includes("dashboard")) {
    return "overview";
  }
  return "";
}

function navIconForMandirWorkspace(workspace) {
  return ({
    overview: "▦",
    sevas: "♜",
    "book-sevas": "♜",
    "seva-bookings": "▤",
    "seva-management": "▤",
    "reschedule-approval": "✓",
    donations: "▰",
    devotees: "●●",
    payments: "▣",
    receipts: "▤",
    reports: "▥",
    panchang: "□",
    settings: "⚙",
    implementation: "☑",
    "platform-owners": "♜",
    accounting: "▣",
  }[workspace] || "");
}

function syncMandirNavActiveState() {
  nav.querySelectorAll("a").forEach((link) => {
    const workspace = link.dataset.mandirWorkspace || "";
    const isActive = currentExperience === "mandir" && workspace && workspace === activeMandirWorkspace;
    link.classList.toggle("active", isActive);
  });
  if (topbarCurrent) {
    const labels = {
      overview: "Dashboard",
      donations: "Donations",
      sevas: "Sevas",
      payments: "Public Payments",
      exceptions: "Exceptions",
      receipts: "Receipts",
      panchang: "Panchang",
      reports: "Reports",
      accounting: "Accounting",
      settings: "Settings",
      implementation: "Implementation Checks",
      "platform-owners": "Platform Owners",
    };
    const gruhaLabels = {
      overview: "Dashboard",
      maintenance: "Maintenance",
      members: "Members",
      flats: "Flats",
      complaints: "Complaints",
      messages: "Messages",
      meetings: "Meetings",
      assets: "Assets",
      accounting: "Accounting",
      reports: "Reports",
      settings: "Settings",
    };
    topbarCurrent.textContent = currentExperience === "mandir"
      ? labels[activeMandirWorkspace] || "Dashboard"
      : currentExperience === "gruha"
        ? gruhaLabels[activeGruhaWorkspace] || "Dashboard"
        : "Dashboard";
  }
}

function syncGruhaNavActiveState() {
  nav.querySelectorAll("a").forEach((link) => {
    const workspace = link.dataset.gruhaWorkspace || "";
    const isActive = currentExperience === "gruha" && workspace && workspace === activeGruhaWorkspace;
    link.classList.toggle("active", isActive);
  });
  if (topbarCurrent && currentExperience === "gruha") {
    const labels = {
      overview: "Dashboard",
      maintenance: "Maintenance",
      members: "Members",
      flats: "Flats",
      complaints: "Complaints",
      messages: "Messages",
      meetings: "Meetings",
      assets: "Assets",
      accounting: "Accounting",
      reports: "Reports",
      settings: "Settings",
    };
    topbarCurrent.textContent = labels[activeGruhaWorkspace] || "Dashboard";
  }
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

function renderMandirReceiptActions(row, label) {
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

function mandirPublicPaymentPageUrl() {
  const api = encodeURIComponent(getConfiguredApiBaseUrl());
  return `../mandir-public/?api=${api}`;
}

function renderMandirOperationResult(result) {
  if (!result) {
    return "";
  }
  return `
    <div class="module-state ${result.ok ? "ok" : "warn"}" id="mandir-operation-result">
      <strong>${escapeHtml(result.title || (result.ok ? "Operation completed" : "Operation failed"))}</strong>
      <span>${escapeHtml(result.detail || "")}</span>
    </div>
  `;
}

function setLoginStatus(kind, title, detail = "") {
  if (!loginStatus) {
    return;
  }
  loginStatus.className = `module-state ${kind || ""}`.trim();
  loginStatus.innerHTML = title
    ? `<strong>${escapeHtml(title)}</strong><span>${escapeHtml(detail)}</span>`
    : "";
}

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function showMandirSplash() {
  if (!mandirSplash) {
    return;
  }
  const splashConfig = currentExperience === "mandir"
    ? {
        video: "../assets/brand/mandirmitra-logo.mp4",
        image: "../assets/brand/mandirmitra-logo.jpeg",
        alt: "MandirMitra",
        copy: "Opening MandirMitra dashboard...",
      }
    : {
        video: "../assets/brand/mitrabooks-pro-logo.mp4",
        image: "../assets/brand/mitrabooks-pro-logo.png",
        alt: "MitraBooks",
        copy: "Opening MitraBooks dashboard...",
      };
  if (mandirSplashVideo) {
    mandirSplashVideo.src = splashConfig.video;
  }
  if (mandirSplashImage) {
    mandirSplashImage.src = splashConfig.image;
    mandirSplashImage.alt = splashConfig.alt;
  }
  if (brandSplashCopy) {
    brandSplashCopy.textContent = splashConfig.copy;
  }
  mandirSplash.classList.add("show");
  mandirSplash.setAttribute("aria-hidden", "false");
  if (mandirSplashVideo) {
    mandirSplashVideo.currentTime = 0;
    await mandirSplashVideo.play().catch(() => {});
  }
}

function hideMandirSplash() {
  if (!mandirSplash) {
    return;
  }
  mandirSplash.classList.remove("show");
  mandirSplash.setAttribute("aria-hidden", "true");
  mandirSplashVideo?.pause();
}

function hasTrustedSession() {
  if (!getAccessToken()) {
    return false;
  }
  if (currentExperience !== "mitrabooks") {
    return true;
  }
  return Boolean(lastModuleContext && typeof lastModuleContext === "object");
}

function updateSessionUi() {
  const signedIn = hasTrustedSession();
  appRoot.classList.toggle("signed-in", signedIn);
  appRoot.classList.toggle("signed-out", !signedIn);
  document.getElementById("access-panel")?.classList.toggle("signed-in", signedIn);
  document.getElementById("access-panel")?.classList.toggle("signed-out", !signedIn);
  if (sessionPill) {
    sessionPill.textContent = signedIn ? "Signed in" : "Not signed in";
    sessionPill.className = `pill ${signedIn ? "ok" : "warn"}`;
  }
  const savedEmail = window.localStorage.getItem(LOGIN_EMAIL_STORAGE_KEY) || "";
  if (topbarUser) {
    topbarUser.textContent = savedEmail || "Signed in";
  }
  if (topbarAvatar) {
    topbarAvatar.textContent = (savedEmail || "S").trim().charAt(0).toUpperCase();
  }
  if (sidebarAvatar) {
    sidebarAvatar.textContent = (savedEmail || "S").trim().charAt(0).toUpperCase();
  }
  if (sidebarUserName) {
    sidebarUserName.textContent = signedIn ? (savedEmail || "Signed in") : "Not signed in";
  }
  if (sidebarUserRole) {
    const role = lastModuleContext?.role || lastModuleContext?.user_role || "";
    sidebarUserRole.textContent = signedIn ? (role || "Tenant context pending") : "Sign in to load tenant";
  }
  if (loginEmail && !loginEmail.value && savedEmail) {
    loginEmail.value = savedEmail;
  }
  if (tokenInput) {
    tokenInput.value = getAccessToken();
  }
  const publicLink = document.getElementById("mandir-public-link");
  if (publicLink) {
    publicLink.href = mandirPublicPaymentPageUrl();
  }
}

function updateTrustedContextUi(context = lastModuleContext) {
  const organizationType = String(context?.organization_type || "").toUpperCase();
  const tenantLabel = context?.tenant_name || context?.organization_name || context?.tenant_id || "";
  const enabledCount = Array.isArray(context?.enabled_modules)
    ? context.enabled_modules.length
    : Array.isArray(context?.modules)
      ? context.modules.filter((module) => module.enabled !== false).length
      : 0;

  if (currentOrgType) {
    currentOrgType.textContent = organizationType === "BUSINESS"
      ? "Business Suite"
      : organizationType
        ? `${organizationType} workspace`
        : "Business Suite";
  }
  if (currentOrgTenant) {
    currentOrgTenant.textContent = tenantLabel || "Acme Corp Ltd";
  }
  if (sidebarUserRole && getAccessToken()) {
    const role = context?.role || context?.user_role || "";
    sidebarUserRole.textContent = role || (enabledCount ? `${enabledCount} enabled module(s)` : "Tenant context loaded");
  }
}

async function signInWithPassword() {
  const email = String(loginEmail?.value || "").trim().toLowerCase();
  const password = String(loginPassword?.value || "");
  const loginSubmitBtn = document.getElementById("login-submit");
  const errorField = document.getElementById("login-error-field");
  const errorMessage = document.getElementById("login-error-message");

  // Validate input
  if (!email || !password) {
    if (errorField && errorMessage) {
      errorField.hidden = false;
      errorMessage.textContent = "Email and password are required.";
    }
    setLoginStatus("warn", "Email and password required", "Enter your MitraBooks tenant admin login.");
    return;
  }

  // Validate email format
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    if (errorField && errorMessage) {
      errorField.hidden = false;
      errorMessage.textContent = "Please enter a valid email address.";
    }
    setLoginStatus("warn", "Invalid email", "Email must be a valid email address.");
    return;
  }

  // Clear previous errors
  if (errorField) {
    errorField.hidden = true;
  }

  // Disable button and show loading state
  if (loginSubmitBtn) {
    loginSubmitBtn.disabled = true;
    loginSubmitBtn.textContent = "Signing in...";
  }

  try {
    setLoginStatus("", "Signing in", "Checking your tenant access...");
    const appKey = EXPERIENCE_APP_KEYS[currentExperience] || APP_KEY;
    const result = await apiRequest(appKey, "/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });

    if (!result.ok) {
      clearAccessToken();
      updateSessionUi();
      const detail = result.payload?.detail || "Unable to sign in with these credentials.";

      // Show error message in form
      if (errorField && errorMessage) {
        errorField.hidden = false;
        errorMessage.textContent = detail;
      }

      setLoginStatus("danger", "Sign in failed", detail);
      renderJson(apiOutput, { login: { ok: result.ok, status: result.status, detail } });
      return;
    }

    // Successful login
    setAccessToken(result.payload?.access_token || "");
    window.localStorage.setItem(LOGIN_EMAIL_STORAGE_KEY, email);

    // Clear password for security
    if (loginPassword) {
      loginPassword.value = "";
    }

    updateSessionUi();
    setLoginStatus("ok", "Signed in", "Tenant workspace is loading.");
    renderJson(apiOutput, { login: { ok: true, status: result.status, token_type: result.payload?.token_type || "bearer" } });

    // Load grouped navigation after successful login (Phase 1D)
    if (currentExperience === "mitrabooks") {
      const appKey = EXPERIENCE_APP_KEYS[currentExperience] || APP_KEY;
      loadAndRenderGroupedNav(appKey).catch(err => {
        console.error("[Login] Failed to load grouped nav:", err);
      });
    }

    // Show splash and load dashboard
    await showMandirSplash();
    try {
      await Promise.all([runChecks(), delay(1400)]);
    } finally {
      hideMandirSplash();
    }
  } catch (error) {
    console.error("[Login] Error during sign in:", error);
    if (errorField && errorMessage) {
      errorField.hidden = false;
      errorMessage.textContent = "An unexpected error occurred. Please try again.";
    }
    setLoginStatus("danger", "Sign in error", "An unexpected error occurred. Please try again.");
  } finally {
    // Re-enable button
    if (loginSubmitBtn) {
      loginSubmitBtn.disabled = false;
      loginSubmitBtn.textContent = "Sign in";
    }
  }
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
  const reversedBy = Array.isArray(detail.reversed_by_journal_ids) ? detail.reversed_by_journal_ids : [];
  const isReversal = Boolean(detail.reversal_of_journal_id);
  const isReversed = reversedBy.length > 0;
  return `
    <div class="table-preview compact-table">
      <h4>Voucher ${escapeHtml(detail.reference || detail.id)}</h4>
      <p class="muted">${escapeHtml(detail.entry_date || "")} | ${escapeHtml(detail.description || "Posted journal voucher")}</p>
      <p class="muted">
        Journal #${escapeHtml(detail.id || "")}
        ${isReversal ? ` | Reversal of journal #${escapeHtml(detail.reversal_of_journal_id)}` : ""}
        ${isReversed ? ` | Reversed by journal #${escapeHtml(reversedBy.join(", #"))}` : ""}
        ${isReversal ? `<span class="pill warn">reversal</span>` : isReversed ? `<span class="pill warn">reversed</span>` : `<span class="pill ok">posted</span>`}
      </p>
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

function panchangTimeRange(value) {
  if (!value || typeof value !== "object") {
    return "--";
  }
  const start = value.start || value.start_time || "";
  const end = value.end || value.end_time || "";
  return start && end ? `${start} - ${end}` : start || end || "--";
}

function renderMandirPanchang(payload = lastMandirPanchang) {
  if (!payload) {
    return `
      <div class="verification-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Today Panchang</h4>
            <p class="muted">Run checks to load temple-location Panchang for the active tenant.</p>
          </div>
        </div>
      </div>
    `;
  }
  if (payload.ok === false) {
    const detail = payload.payload?.detail || payload.detail || "Panchang is unavailable for the active temple tenant.";
    return `
      <div class="verification-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Today Panchang</h4>
            <p class="muted">${escapeHtml(detail)}</p>
          </div>
        </div>
      </div>
    `;
  }

  const date = payload.date || {};
  const hinduDate = date.hindu || {};
  const gregorianDate = date.gregorian || {};
  const location = payload.location || {};
  const panchang = payload.panchang || {};
  const tithi = panchang.tithi || {};
  const nakshatra = panchang.nakshatra || {};
  const yoga = panchang.yoga || {};
  const karana = panchang.karana || {};
  const vara = panchang.vara || {};
  const sunMoon = payload.sun_moon || {};
  const kaala = payload.kaala || payload.inauspicious_times || {};
  const muhurat = payload.muhurat || payload.auspicious_times || {};
  const festivals = Array.isArray(payload.festivals) ? payload.festivals : [];
  const specialNotes = payload.special_notes || {};

  const limbCards = [
    ["Tithi", tithi.full_name || tithi.name || "--", tithi.end_time_formatted ? `ends ${tithi.end_time_formatted}` : ""],
    ["Nakshatra", nakshatra.name || "--", nakshatra.end_time_formatted ? `ends ${nakshatra.end_time_formatted}` : ""],
    ["Yoga", yoga.name || "--", yoga.end_time_formatted ? `ends ${yoga.end_time_formatted}` : ""],
    ["Karana", karana.current || karana.name || "--", karana.end_time_formatted ? `ends ${karana.end_time_formatted}` : ""],
  ];
  const timingRows = [
    ["Sunrise", sunMoon.sunrise || "--", "Sunset", sunMoon.sunset || "--"],
    ["Rahu Kaal", panchangTimeRange(kaala.rahu || kaala.rahu_kaal), "Yamaganda", panchangTimeRange(kaala.yamaganda)],
    ["Gulika", panchangTimeRange(kaala.gulika), "Abhijit", panchangTimeRange(muhurat.abhijit || muhurat.abhijit_muhurat)],
    ["Brahma Muhurat", panchangTimeRange(muhurat.brahma || muhurat.brahma_muhurat), "Amrita Kalam", panchangTimeRange(kaala.amrita || muhurat.amrita_kalam)],
  ];

  return `
    <div class="verification-panel" id="mandir-panchang-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Today Panchang</h4>
          <p>${escapeHtml(gregorianDate.formatted || gregorianDate.date || "")} | ${escapeHtml(location.city || "Temple location")}</p>
        </div>
        <span class="pill ok">${escapeHtml(vara.name || gregorianDate.day || "Today")}</span>
      </div>
      <div class="metric-grid four">${renderStatCards(limbCards)}</div>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr>
              <th>Timing</th>
              <th>Value</th>
              <th>Timing</th>
              <th>Value</th>
            </tr>
          </thead>
          <tbody>
            ${timingRows.map(([leftLabel, leftValue, rightLabel, rightValue]) => `
              <tr>
                <td>${escapeHtml(leftLabel)}</td>
                <td>${escapeHtml(leftValue)}</td>
                <td>${escapeHtml(rightLabel)}</td>
                <td>${escapeHtml(rightValue)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
      <div class="table-preview compact-table">
        <table>
          <tbody>
            <tr>
              <th>Samvatsara</th>
              <td>${escapeHtml(hinduDate.samvatsara_name || payload.samvatsara?.name || "--")}</td>
              <th>Paksha</th>
              <td>${escapeHtml(hinduDate.paksha || tithi.paksha || "--")}</td>
            </tr>
            <tr>
              <th>Lunar Month</th>
              <td>${escapeHtml(hinduDate.month || hinduDate.lunar_month_purnimanta || "--")}</td>
              <th>Festivals</th>
              <td>${escapeHtml(festivals.map((item) => item.name || item.title).filter(Boolean).join(", ") || "None")}</td>
            </tr>
            <tr>
              <th>Recommendation</th>
              <td colspan="3">${escapeHtml(specialNotes.summary || "No special note for today.")}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function reportPayload(value, fallback = {}) {
  if (!value) {
    return fallback;
  }
  if (value.ok === false) {
    return fallback;
  }
  return value;
}

function reportRows(value, key) {
  const payload = reportPayload(value);
  return Array.isArray(payload[key]) ? payload[key] : [];
}

function renderMandirOperationalReports(reports = lastMandirOperationalReports) {
  const donationCategory = reportPayload(reports.donation_category);
  const donationDetail = reportPayload(reports.donation_detail);
  const sevaDetail = reportPayload(reports.seva_detail);
  const sevaSchedule = reportPayload(reports.seva_schedule);
  const devotees = Array.isArray(reports.devotees) ? reports.devotees : [];
  const categoryRows = reportRows(donationCategory, "categories");
  const donationRows = reportRows(donationDetail, "donations");
  const sevaRows = reportRows(sevaDetail, "sevas");
  const scheduleRows = reportRows(sevaSchedule, "schedule");
  const totalDonation = donationDetail.total_amount ?? donationCategory.total_amount ?? 0;
  const totalSeva = sevaDetail.total_amount ?? 0;

  return `
    <div class="verification-panel">
      <div class="preview-heading compact">
        <div>
          <h4>MandirMitra Reports</h4>
          <p>Donation, seva, devotee, and schedule reports for the active temple tenant.</p>
        </div>
        <span class="pill">${escapeHtml(accountingDrilldownState.from_date)} to ${escapeHtml(accountingDrilldownState.to_date)}</span>
      </div>
      <div class="metric-grid four">${renderStatCards([
        ["Donation Total", formatCurrency(totalDonation), formatCountLabel(donationRows.length, "receipt")],
        ["Seva Total", formatCurrency(totalSeva), formatCountLabel(sevaRows.length, "booking")],
        ["Devotees", devotees.length, "recent records"],
        ["Schedule", scheduleRows.length, "upcoming sevas"],
      ])}</div>
      <div class="dashboard-main-grid platform-grid">
        <article>
          <h4>Donation Category Report</h4>
          <div class="table-preview compact-table">
            <table>
              <thead>
                <tr><th>Category</th><th class="amount">Amount</th><th>Count</th></tr>
              </thead>
              <tbody>
                ${categoryRows.length ? categoryRows.slice(0, 8).map((row) => `
                  <tr>
                    <td>${escapeHtml(row.category || "Uncategorized")}</td>
                    <td class="amount">${escapeHtml(formatCurrency(row.amount))}</td>
                    <td>${escapeHtml(row.count ?? row.transaction_count ?? 0)}</td>
                  </tr>
                `).join("") : `<tr><td colspan="3">No donation categories for this range.</td></tr>`}
              </tbody>
            </table>
          </div>
        </article>
        <article>
          <h4>Detailed Donations</h4>
          <div class="table-preview compact-table">
            <table>
              <thead>
                <tr><th>Date</th><th>Receipt</th><th>Devotee</th><th>Purpose</th><th class="amount">Amount</th></tr>
              </thead>
              <tbody>
                ${donationRows.length ? donationRows.slice(0, 8).map((row) => {
                  const itemParts = [row.in_kind_item_name, row.in_kind_quantity].filter(Boolean).join(" / ");
                  const purposeDetail = row.donation_type === "in_kind" ? itemParts || "In-kind" : row.payment_mode || "Cash";
                  return `
                    <tr>
                      <td>${escapeHtml(String(row.date || row.receipt_date || "").slice(0, 10))}</td>
                      <td>${escapeHtml(row.receipt_number || row.id || "")}</td>
                      <td>${escapeHtml(row.devotee_name || "Devotee")}</td>
                      <td>
                        <strong>${escapeHtml(row.category || "Donation")}</strong>
                        <small>${escapeHtml(purposeDetail)}</small>
                      </td>
                      <td class="amount">${escapeHtml(formatCurrency(row.amount))}</td>
                    </tr>
                  `;
                }).join("") : `<tr><td colspan="5">No donation receipts for this range.</td></tr>`}
              </tbody>
            </table>
          </div>
        </article>
        <article>
          <h4>Detailed Sevas</h4>
          <div class="table-preview compact-table">
            <table>
              <thead>
                <tr><th>Date</th><th>Seva</th><th>Devotee</th><th class="amount">Amount</th><th>Status</th></tr>
              </thead>
              <tbody>
                ${sevaRows.length ? sevaRows.slice(0, 8).map((row) => `
                  <tr>
                    <td>${escapeHtml(String(row.seva_date || row.booking_date || row.date || "").slice(0, 10))}</td>
                    <td>${escapeHtml(row.seva_name || "Seva")}</td>
                    <td>${escapeHtml(row.devotee_name || "Devotee")}</td>
                    <td class="amount">${escapeHtml(formatCurrency(row.amount))}</td>
                    <td>${escapeHtml(row.status || "")}</td>
                  </tr>
                `).join("") : `<tr><td colspan="5">No seva bookings for this range.</td></tr>`}
              </tbody>
            </table>
          </div>
        </article>
        <article>
          <h4>Seva Schedule</h4>
          <div class="table-preview compact-table">
            <table>
              <thead>
                <tr><th>Date</th><th>Seva</th><th>Devotee</th><th>Phone</th></tr>
              </thead>
              <tbody>
                ${scheduleRows.length ? scheduleRows.slice(0, 8).map((row) => `
                  <tr>
                    <td>${escapeHtml(String(row.date || row.booking_date || "").slice(0, 10))}</td>
                    <td>${escapeHtml(row.seva_name || "Seva")}</td>
                    <td>${escapeHtml(row.devotee_name || "Devotee")}</td>
                    <td>${escapeHtml(row.devotee_mobile || row.devotee_phone || "")}</td>
                  </tr>
                `).join("") : `<tr><td colspan="4">No upcoming seva schedule rows.</td></tr>`}
              </tbody>
            </table>
          </div>
        </article>
      </div>
      <div class="verification-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Recent Devotees</h4>
            <p>Tenant-scoped devotee records captured from donations, sevas, and public payments.</p>
          </div>
          <span class="pill">${devotees.length} shown</span>
        </div>
        <div class="table-preview compact-table">
          <table>
            <thead>
              <tr><th>Name</th><th>Phone</th><th>City</th><th>Updated</th></tr>
            </thead>
            <tbody>
              ${devotees.length ? devotees.slice(0, 12).map((row) => `
                <tr>
                  <td>${escapeHtml(row.name || row.first_name || "Devotee")}</td>
                  <td>${escapeHtml(row.phone || row.mobile || "")}</td>
                  <td>${escapeHtml(row.city || "")}</td>
                  <td>${escapeHtml(String(row.updated_at || row.created_at || "").slice(0, 10))}</td>
                </tr>
              `).join("") : `<tr><td colspan="4">No devotee records found.</td></tr>`}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

function renderMandirDevoteesView(reports = lastMandirOperationalReports) {
  const devotees = Array.isArray(reports.devotees) ? reports.devotees : [];
  return `
    <div class="verification-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Devotees</h4>
          <p>Tenant-scoped devotee records captured from donations, sevas, and public payments.</p>
        </div>
        <span class="pill">${devotees.length} shown</span>
      </div>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr><th>Name</th><th>Phone</th><th>City</th><th>Updated</th></tr>
          </thead>
          <tbody>
            ${devotees.length ? devotees.slice(0, 20).map((row) => `
              <tr>
                <td>${escapeHtml(row.name || row.first_name || "Devotee")}</td>
                <td>${escapeHtml(row.phone || row.mobile || "")}</td>
                <td>${escapeHtml(row.city || "")}</td>
                <td>${escapeHtml(String(row.updated_at || row.created_at || "").slice(0, 10))}</td>
              </tr>
            `).join("") : `<tr><td colspan="4">No devotee records found.</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderMandirDashboardHome(payload = {}) {
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
  const panchang = payload.panchang || lastMandirPanchang;
  const operationalReports = payload.operational_reports || lastMandirOperationalReports;
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
  const showDonations = activeMandirWorkspace === "donations";
  const showSevas = ["sevas", "book-sevas", "seva-bookings", "seva-management", "reschedule-approval"].includes(activeMandirWorkspace);
  const showDevotees = activeMandirWorkspace === "devotees";
  const showPayments = activeMandirWorkspace === "payments";
  const showExceptions = activeMandirWorkspace === "exceptions";
  const showReceipts = activeMandirWorkspace === "receipts";
  const showPanchang = activeMandirWorkspace === "panchang";
  const showReports = activeMandirWorkspace === "reports";
  const showAccounting = activeMandirWorkspace === "accounting";
  const showSettings = activeMandirWorkspace === "settings";
  const showImplementation = activeMandirWorkspace === "implementation";
  const showPlatformOwners = activeMandirWorkspace === "platform-owners";
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
  }[activeMandirWorkspace] || ["Dashboard", "MandirMitra temple workspace."];

  return `
    <div class="legacy-dashboard mandir-dashboard">
      <div class="preview-heading">
        <div>
          <h3>${escapeHtml(pageMeta[0])}</h3>
          <p>${escapeHtml(pageMeta[1])}</p>
        </div>
        <span class="pill ok technical-context">mandirmitra</span>
      </div>
      ${isProductionShell() && isMandirHost() ? "" : renderMandirWorkspaceTabs(activeMandirWorkspace)}
      ${renderMandirOperationResult(formResult)}
      ${(showOverview || activeMandirWorkspace === "donations") ? `
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
      ${showSettings ? renderMandirSettings(payload.module_config || {}) : ""}
      ${showImplementation ? renderMandirImplementationChecks() : ""}
      ${showPlatformOwners ? renderMandirPlatformOwnerShortcut() : ""}
      ${showAccounting ? renderAccountingDrilldownPanel() : ""}
      ${showAccounting ? renderMandirTrialBalance(trialBalance) : ""}
      ${showAccounting ? renderMandirFinancialReports(financialReports) : ""}
      ${showAccounting ? renderMandirExpensesTable(recentExpenses) : ""}
    </div>
  `;
}

function renderMandirSettings(moduleConfig = {}) {
  const inventoryEnabled = Boolean(moduleConfig.inventory_enabled);
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
    </div>
  `;
}

function renderMandirImplementationChecks() {
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

function renderMandirPlatformOwnerShortcut() {
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
    return renderGruhaDashboard(config, lastGruhaData);
  }

  if (dashboard.type === "business" || currentExperience === "mitrabooks") {
    if (activeBusinessWorkspace !== "overview") {
      return renderBusinessWorkspace();
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
        ${renderBusinessExecutiveDashboard()}
        <div class="metric-grid four">${renderStatCards(dashboard.stats || [])}</div>
        <div class="dashboard-main-grid">
          <article>
            <h4>Quick Actions</h4>
            <div class="quick-grid">${renderActionTiles(dashboard.actions || [])}</div>
          </article>
          <article>
            <h4>Recent Activity</h4>
            <ul class="activity-list">${renderActivity(dashboard.activity || [])}</ul>
          </article>
        </div>
        ${renderBusinessDataHealthPanel()}
        ${renderAccountingDrilldownPanel()}
    </div>
  `;
}
}

// ========== Business Module: Party Master ==========

let activeBusinessWorkspace = "overview";
let lastBusinessParties = [];
let lastBusinessPartiesResult = null;
const businessListState = {
  parties: {
    offset: 0,
    q: "",
    party_type: "",
    from_date: "",
    to_date: "",
  },
};

function renderBusinessPartiesTable(rows) {
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
            <th>Opening Balance</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows.slice(0, 20).map((row) => {
            const isInactive = row.is_inactive || row.status === "inactive";
            const partyName = row.party_name || row.name || "Unnamed";
            const openingBalance = Number(row.opening_balance ?? (row.opening_balance_paise ? row.opening_balance_paise / 100 : 0)) || 0;
            return `
              <tr>
                <td>
                  <strong>${escapeHtml(partyName)}</strong>
                  <span class="row-subtext">${escapeHtml(row.party_code || row.code || "")}</span>
                </td>
                <td><span class="type-chip">${escapeHtml(row.party_type || row.type || "unknown")}</span></td>
                <td>${escapeHtml(row.gstin || "-")}</td>
                <td class="amount">${escapeHtml(formatCurrency(openingBalance))}</td>
                <td><span class="pill ${isInactive ? "warn" : "ok"}">${isInactive ? "Inactive" : "Active"}</span></td>
                <td>
                  <div class="action-row">
                    <button
                      class="secondary"
                      type="button"
                      data-business-action="edit-party"
                      data-party-id="${escapeHtml(row.party_id || row.id || "")}"
                      data-party-name="${escapeHtml(partyName)}"
                      data-party-gstin="${escapeHtml(row.gstin || "")}"
                      data-party-opening-balance="${escapeHtml(openingBalance)}"
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

function renderBusinessPartiesListFilters(rowsLength) {
  const state = businessListState.parties;
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

function renderBusinessVouchersTable(rows) {
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
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows.slice(0, 20).map((row) => {
            const status = row.status || "posted";
            const isReversed = status === "reversed";
            return `
              <tr>
                <td>${escapeHtml(String(row.entry_date || row.created_at || "").slice(0, 10))}</td>
                <td>${escapeHtml(row.reference || row.cheque_number || "-")}</td>
                <td>${escapeHtml(row.voucher_type || "journal")}</td>
                <td class="amount">${escapeHtml(formatCurrency(row.total_debit || row.amount || 0))}</td>
                <td>${escapeHtml((row.description || row.narration || "").slice(0, 40))}</td>
                <td><span class="pill ${isReversed ? "warn" : "ok"}">${escapeHtml(status)}</span></td>
                <td>
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
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderBusinessWorkspace() {
  if (activeBusinessWorkspace === "parties") {
    return `
      <div class="verification-panel erp-workspace-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Parties</h4>
            <p>Customers and vendors for this business workspace.</p>
          </div>
          <button class="secondary" type="button" data-business-action="open-create-party">+ New Party</button>
        </div>
        ${renderBusinessPartiesListFilters(lastBusinessParties.length)}
        ${renderBusinessPartiesTable(lastBusinessParties)}
      </div>
    `;
  }
  if (activeBusinessWorkspace === "vouchers") {
    return `
      <div class="verification-panel erp-workspace-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Vouchers</h4>
            <p>Posted journal entries, payments, receipts, and contra vouchers.</p>
          </div>
          <button class="secondary" type="button" data-business-action="open-create-voucher">+ New Voucher</button>
        </div>
        ${renderBusinessVouchersTable(lastBusinessVouchers)}
      </div>
    `;
  }
  if (activeBusinessWorkspace === "audit") {
    return `
      <div class="verification-panel erp-workspace-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Audit Trail</h4>
            <p>All party, voucher, and account changes for compliance and troubleshooting.</p>
          </div>
        </div>
        ${renderAuditListFilters(lastAuditEvents.length)}
        ${renderAuditEventsTable(lastAuditEvents)}
      </div>
    `;
  }
  if (activeBusinessWorkspace === "accounting") {
    return `
      <div class="verification-panel erp-workspace-panel">
        <div class="preview-heading compact">
          <div>
            <h4>Accounting</h4>
            <p>Chart readiness, voucher drill-down, and posted ledger checks for the active tenant.</p>
          </div>
        </div>
        ${renderAccountingDrilldownPanel()}
      </div>
    `;
  }
  return `
    <div class="erp-workbench-grid">
      <article class="erp-workbench-card">
        <span class="workbench-kicker">Core Master</span>
        <h4>Parties</h4>
        <strong>${escapeHtml(lastBusinessParties.length)}</strong>
        <p>Customers and vendors available for business posting.</p>
        <button class="secondary" type="button" data-business-action="workspace-view" data-workspace-view="parties">Open Parties</button>
      </article>
      <article class="erp-workbench-card">
        <span class="workbench-kicker">Posting</span>
        <h4>Vouchers</h4>
        <strong>${escapeHtml(lastBusinessVouchers.length)}</strong>
        <p>Posted journal entries, receipts, payments, and reversals.</p>
        <button class="secondary" type="button" data-business-action="workspace-view" data-workspace-view="vouchers">Open Vouchers</button>
      </article>
      <article class="erp-workbench-card">
        <span class="workbench-kicker">Chart</span>
        <h4>Accounts</h4>
        <strong>${escapeHtml(lastBusinessAccounts.length)}</strong>
        <p>Tenant-owned chart of accounts loaded from accounting APIs.</p>
        <button class="secondary" type="button" data-business-action="workspace-view" data-workspace-view="accounting">Open Accounting</button>
      </article>
    </div>
  `;
  return `
    <div class="dashboard-main-grid erp-command-grid">
      <article>
        <h4>Quick Actions</h4>
        <div class="quick-grid">
          <button class="quick-tile" type="button" data-business-action="workspace-view" data-workspace-view="parties">
            <span class="quick-icon">●</span>
            <span>Parties</span>
          </button>
          <button class="quick-tile" type="button" data-business-action="workspace-view" data-workspace-view="vouchers">
            <span class="quick-icon">▤</span>
            <span>Vouchers</span>
          </button>
          <button class="quick-tile" type="button" data-business-action="workspace-view" data-workspace-view="audit">
            <span class="quick-icon">⏱</span>
            <span>Audit</span>
          </button>
        </div>
      </article>
    </div>
  `;
}

async function loadBusinessParties(filters = {}) {
  const appKey = "mitrabooks";
  const state = businessListState.parties;
  const params = new URLSearchParams();

  if (state.q) params.append("q", state.q);
  if (state.party_type) params.append("party_type", state.party_type);
  params.append("offset", state.offset || 0);
  params.append("limit", 20);

  const queryString = params.toString();
  const url = `/api/v1/business/parties${queryString ? "?" + queryString : ""}`;

  const result = await apiRequest(appKey, url, { method: "GET" });
  lastBusinessPartiesResult = result;
  if (result.ok) {
    lastBusinessParties = Array.isArray(result.payload?.items) ? result.payload.items : Array.isArray(result.payload) ? result.payload : [];
    if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "parties") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  } else {
    lastBusinessParties = [];
    setLoginStatus("warn", "Unable to load parties", result.payload?.detail || "Check connection and try again.");
  }
  renderJson(apiOutput, { parties: { ok: result.ok, count: lastBusinessParties.length } });
  return result;
}

async function createBusinessParty(data) {
  const appKey = "mitrabooks";
  const payload = {
    party_name: data.name,
    party_type: data.party_type,
    gstin: data.gstin || null,
    opening_balance: String(Number(data.opening_balance) || 0),
  };

  const result = await apiRequest(appKey, "/api/v1/business/parties", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  if (result.ok) {
    setLoginStatus("ok", "Party created", result.payload?.party_name || "New party added.");
    document.getElementById("business-party-create-dialog")?.close();
    await loadBusinessParties();
    // Force refresh of current workspace
    if (activeBusinessWorkspace === "parties") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  } else {
    setLoginStatus("danger", "Create party failed", statusDetailText(result.payload?.detail) || "Try again.");
  }
  renderJson(apiOutput, { create_party: result });
}

async function updateBusinessParty(partyId, data) {
  const appKey = "mitrabooks";
  const payload = {
    party_name: data.name,
    gstin: data.gstin || null,
  };

  const result = await apiRequest(appKey, `/api/v1/business/parties/${encodeURIComponent(partyId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });

  if (result.ok) {
    setLoginStatus("ok", "Party updated", result.payload?.party_name || "Changes saved.");
    document.getElementById("business-party-edit-dialog")?.close();
    await loadBusinessParties();
  } else {
    setLoginStatus("danger", "Update party failed", statusDetailText(result.payload?.detail) || "Try again.");
  }
  renderJson(apiOutput, { update_party: result });
}

async function deactivateBusinessParty(partyId) {
  const appKey = "mitrabooks";
  const result = await apiRequest(appKey, `/api/v1/business/parties/${encodeURIComponent(partyId)}/deactivate`, {
    method: "PATCH",
  });

  if (result.ok) {
    setLoginStatus("ok", "Party deactivated", "Party is now inactive.");
    await loadBusinessParties();
  } else {
    setLoginStatus("danger", "Deactivate party failed", result.payload?.detail || "Try again.");
  }
  renderJson(apiOutput, { deactivate_party: result });
}

function openBusinessCreatePartyDialog() {
  const dialog = document.getElementById("business-party-create-dialog");
  const form = document.getElementById("business-party-create-form");
  if (!form) return;

  form.reset();
  dialog?.showModal();
}

function openBusinessEditPartyDialog(button) {
  const dialog = document.getElementById("business-party-edit-dialog");
  const form = document.getElementById("business-party-edit-form");
  if (!form) return;

  const partyId = button.getAttribute("data-party-id") || "";
  const partyName = button.getAttribute("data-party-name") || "";
  const partyGstin = button.getAttribute("data-party-gstin") || "";
  const openingBalance = button.getAttribute("data-party-opening-balance") || "0";

  document.getElementById("business-party-edit-id").value = partyId;
  document.getElementById("business-party-edit-name").value = partyName;
  document.getElementById("business-party-edit-gstin").value = partyGstin;
  document.getElementById("business-party-edit-opening-balance").value = openingBalance;
  document.getElementById("business-party-edit-label").textContent = `Editing ${partyName}`;

  dialog?.showModal();
}

function setBusinessWorkspace(workspace) {
  activeBusinessWorkspace = workspace;
  syncBusinessNavActiveState();
  dashboardPreview.innerHTML = renderBusinessWorkspace();
  if (workspace === "parties") {
    loadBusinessParties();
  } else if (workspace === "vouchers") {
    loadBusinessAccounts();
    loadBusinessVouchers();
  } else if (workspace === "audit") {
    loadAuditEvents();
  } else if (workspace === "accounting") {
    refreshCurrentAccountingDrilldown();
  }
}

function syncBusinessNavActiveState() {
  nav.querySelectorAll("a").forEach((link) => {
    const workspace = link.dataset.businessWorkspace || "";
    const isActive = currentExperience === "mitrabooks" && workspace && workspace === activeBusinessWorkspace;
    link.classList.toggle("active", isActive);
  });
  if (topbarCurrent && currentExperience === "mitrabooks") {
    const labels = {
      overview: "Dashboard",
      parties: "Parties",
      vouchers: "Vouchers",
      audit: "Audit Trail",
      accounting: "Accounting",
    };
    const label = labels[activeBusinessWorkspace] || "Dashboard";
    topbarCurrent.textContent = label;
    updatePageHeader("MitraBooks", label, `${label} Workspace`);
  }
}

function applyBusinessListFilter(listKind) {
  if (listKind === "parties") {
    const panel = document.querySelector("[data-business-list='parties']");
    if (!panel) return;

    const qInput = panel.querySelector("input[name='q']");
    const typeInput = panel.querySelector("select[name='party_type']");

    businessListState.parties.q = qInput?.value || "";
    businessListState.parties.party_type = typeInput?.value || "";
    businessListState.parties.offset = 0;

    loadBusinessParties();
  }
}

function resetBusinessListFilter(listKind) {
  if (listKind === "parties") {
    businessListState.parties = {
      offset: 0,
      q: "",
      party_type: "",
      from_date: "",
      to_date: "",
    };
    loadBusinessParties();
  }
}

function pageBusinessList(listKind, direction) {
  if (listKind === "parties") {
    const offset = Number(businessListState.parties.offset || 0);
    businessListState.parties.offset = direction === "next" ? offset + 20 : Math.max(0, offset - 20);
    loadBusinessParties();
  }
}

// ========== Business Module: Typed Vouchers ==========

let lastBusinessVouchers = [];
let lastBusinessAccounts = [];
let lastBusinessAccountsResult = null;
let lastModuleContext = null;
let voucherLineCounter = 0;

const voucherLineState = [];

function normalizeBusinessAccount(acc) {
  return {
    id: String(acc.account_id ?? acc.id ?? ""),
    code: String(acc.account_code ?? acc.code ?? ""),
    name: String(acc.account_name ?? acc.name ?? ""),
  };
}

function businessAccountLabel(account) {
  return `${account.code} ${account.name}`.trim();
}

function populateVoucherAccountSelect(select, selectedId = "") {
  if (!select) return;
  const accounts = Array.isArray(lastBusinessAccounts) ? lastBusinessAccounts.map(normalizeBusinessAccount).filter((acc) => acc.id) : [];
  select.innerHTML = `<option value="">Select account</option>`;
  accounts.forEach((acc) => {
    const option = document.createElement("option");
    option.value = acc.id;
    option.textContent = businessAccountLabel(acc);
    if (String(selectedId) === acc.id) {
      option.selected = true;
    }
    select.appendChild(option);
  });
}

function refreshVoucherAccountDatalist() {
  const datalist = document.getElementById("business-voucher-account-options");
  if (!datalist) return;
  const accounts = Array.isArray(lastBusinessAccounts) ? lastBusinessAccounts.map(normalizeBusinessAccount).filter((acc) => acc.id) : [];
  datalist.innerHTML = "";
  accounts.forEach((acc) => {
    const option = document.createElement("option");
    option.value = businessAccountLabel(acc);
    datalist.appendChild(option);
  });
}

function updateVoucherAccountsStatus() {
  const status = document.getElementById("business-voucher-accounts-status");
  if (!status) return;
  const count = Array.isArray(lastBusinessAccounts) ? lastBusinessAccounts.length : 0;
  status.textContent = "";
  if (count <= 0) {
    status.textContent = "No accounts loaded. Refresh the workspace or check backend accounting access.";
    return;
  }
  const message = document.createElement("span");
  message.textContent = `${count} account(s) loaded. Examples: `;
  status.appendChild(message);
  const preview = document.createElement("strong");
  preview.textContent = lastBusinessAccounts
    .slice(0, 3)
    .map((acc) => businessAccountLabel(normalizeBusinessAccount(acc)))
    .filter(Boolean)
    .join(" | ");
  status.appendChild(preview);
}

function refreshVoucherAccountSelects() {
  refreshVoucherAccountDatalist();
  updateVoucherAccountsStatus();
  document.querySelectorAll(".voucher-account-select").forEach((select) => {
    populateVoucherAccountSelect(select, select.value);
  });
}

function accountRowsFromPayload(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.items)) return payload.items;
  if (Array.isArray(payload?.accounts)) return payload.accounts;
  if (Array.isArray(payload?.data)) return payload.data;
  return [];
}

function isBusinessModuleEnabled(context) {
  const modules = Array.isArray(context?.enabled_modules) ? context.enabled_modules : [];
  return modules.some((module) => {
    const key = typeof module === "string" ? module : module?.module_key;
    return key === "business";
  });
}

function enabledModuleKeys(context = lastModuleContext) {
  const modules = Array.isArray(context?.enabled_modules) ? context.enabled_modules : [];
  return new Set(modules
    .map((module) => typeof module === "string" ? module : module?.module_key)
    .map((key) => String(key || "").trim().toLowerCase())
    .filter(Boolean));
}

function normalizedAccountRows(rows = lastBusinessAccounts) {
  return Array.isArray(rows) ? rows.map((account) => {
    const normalized = normalizeBusinessAccount(account);
    return {
      ...normalized,
      type: String(account.account_type ?? account.type ?? "").toLowerCase(),
      nameKey: normalized.name.toLowerCase(),
    };
  }).filter((account) => account.id || account.code || account.name) : [];
}

function hasBusinessAccount(matchNames, matchTypes = []) {
  const names = matchNames.map((name) => name.toLowerCase());
  const types = matchTypes.map((type) => type.toLowerCase());
  return normalizedAccountRows().some((account) => {
    const nameMatch = names.some((name) => account.nameKey === name || account.nameKey.includes(name));
    const typeMatch = types.length === 0 || types.includes(account.type);
    return nameMatch && typeMatch;
  });
}

function countPartiesMissingGstin(rows = lastBusinessParties) {
  if (!Array.isArray(rows) || rows.length === 0) return 0;
  return rows.filter((row) => !String(row.gstin || "").trim()).length;
}

function dataHealthItem(label, ok, copy) {
  return `
    <li class="${ok ? "ok" : "warn"}">
      <span>${escapeHtml(label)}</span>
      <strong>${ok ? "Ready" : "Needs attention"}</strong>
      <small>${escapeHtml(copy)}</small>
    </li>
  `;
}

function dataHealthAction(priority, title, detail, actionText) {
  return `
    <li>
      <span>${escapeHtml(priority)}</span>
      <strong>${escapeHtml(title)}</strong>
      <small>${escapeHtml(detail)}</small>
      <em>${escapeHtml(actionText)}</em>
    </li>
  `;
}

function renderBusinessDataHealthActions(state) {
  const actions = [];

  if (!state.isBusinessTenant || !state.hasBusinessModule) {
    actions.push(dataHealthAction(
      "Access",
      "Fix MitraBooks tenant context",
      "Business workspaces need organization_type=BUSINESS and the business module enabled.",
      "Review tenant setup before adding more business records."
    ));
  }
  if (!state.hasAccountingModule || !state.accountsLoaded) {
    actions.push(dataHealthAction(
      "Setup",
      "Load the chart of accounts",
      state.accountsBlocked ? `Accounts request returned HTTP ${state.accountsStatus}.` : "The voucher form needs tenant-owned cash, bank, revenue, and expense ledgers.",
      "Open Accounting and confirm the business chart exists."
    ));
  }
  if (state.accountsLoaded && !state.hasCashBank) {
    actions.push(dataHealthAction(
      "Accounts",
      "Add cash or bank account",
      "Receipt, payment, and contra vouchers need an asset-side cash or bank ledger.",
      "Create or map Cash in Hand / Bank Account before payment workflows."
    ));
  }
  if (state.accountsLoaded && !state.hasRevenue) {
    actions.push(dataHealthAction(
      "Accounts",
      "Add revenue account",
      "Sales and service postings need an income/revenue ledger before invoice workflows are enabled.",
      "Create or map Sales / Service Income."
    ));
  }
  if (state.accountsLoaded && !state.hasExpense) {
    actions.push(dataHealthAction(
      "Accounts",
      "Add expense account",
      "Purchase and expense postings need an expense ledger before purchase workflows are enabled.",
      "Create or map Purchases / Office Expense / Rent Expense."
    ));
  }
  if (state.partiesLoaded && state.partiesMissingGstin > 0) {
    actions.push(dataHealthAction(
      "Parties",
      "Complete party GSTINs",
      `${state.partiesMissingGstin} visible party record(s) are missing GSTIN.`,
      "Open Parties and update GSTIN where the party is registered."
    ));
  }
  if (state.partiesBlocked) {
    actions.push(dataHealthAction(
      "Parties",
      "Reload party sample",
      "The dashboard could not read the visible party sample used for GSTIN checks.",
      "Open Parties after confirming the business module is enabled."
    ));
  }
  if (!state.drilldownReady) {
    actions.push(dataHealthAction(
      "Reports",
      "Verify voucher drill-down",
      "Accounting report drill-down must load before reports can be trusted for business review.",
      "Open Accounting and retry after posting a balanced voucher."
    ));
  }

  if (actions.length === 0) {
    actions.push(dataHealthAction(
      "Ready",
      "Core accounting data is ready",
      "Tenant context, modules, chart of accounts, party GSTIN sample, and drill-down are available.",
      "Continue with parties and balanced vouchers; keep GST/inventory depth deferred."
    ));
  }

  return `
    <div class="erp-health-actions">
      <div>
        <h5>Action Queue</h5>
        <p>Concrete next fixes before expanding into sales, purchases, GST, or inventory.</p>
      </div>
      <ol>${actions.join("")}</ol>
    </div>
  `;
}

function getBusinessHealthState() {
  const modules = enabledModuleKeys();
  const organizationType = String(lastModuleContext?.organization_type || "unknown").toUpperCase();
  const tenantId = lastModuleContext?.tenant_id || "not loaded";
  const accountsLoaded = Array.isArray(lastBusinessAccounts) && lastBusinessAccounts.length > 0;
  const accountsBlocked = lastBusinessAccountsResult && !lastBusinessAccountsResult.ok;
  const accountsStatus = lastBusinessAccountsResult?.status || "unknown";
  const partiesLoaded = Array.isArray(lastBusinessParties) && lastBusinessParties.length > 0;
  const partiesBlocked = lastBusinessPartiesResult && !lastBusinessPartiesResult.ok;
  const partiesMissingGstin = countPartiesMissingGstin();
  const partiesGstinReady = !partiesBlocked && (!partiesLoaded || partiesMissingGstin === 0);
  const partiesGstinCopy = partiesBlocked
    ? `Parties request returned HTTP ${lastBusinessPartiesResult.status}.`
    : partiesLoaded
      ? `${partiesMissingGstin} visible party record(s) missing GSTIN.`
      : "No visible parties yet; GSTIN checks start after party creation.";
  const drilldownReady = lastAccountingDrilldown && lastAccountingDrilldown.ok !== false;
  const voucherCount = lastAccountingDrilldown?.summary?.voucher_count ?? 0;
  const healthState = {
    isBusinessTenant: organizationType === "BUSINESS",
    hasBusinessModule: modules.has("business"),
    hasAccountingModule: modules.has("accounting"),
    accountsLoaded,
    accountsBlocked,
    accountsStatus,
    hasCashBank: hasBusinessAccount(["Cash in Hand", "Bank Account"], ["asset"]),
    hasRevenue: hasBusinessAccount(["Sales", "Service Income"], ["income", "revenue"]),
    hasExpense: hasBusinessAccount(["Purchases", "Office Expense", "Rent Expense"], ["expense"]),
    partiesLoaded,
    partiesBlocked,
    partiesMissingGstin,
    partiesGstinReady,
    drilldownReady,
  };

  return {
    healthState,
    organizationType,
    tenantId,
    partiesGstinCopy,
    voucherCount,
  };
}

function renderBusinessDataHealthPanel() {
  const { healthState, organizationType, tenantId, partiesGstinCopy, voucherCount } = getBusinessHealthState();

  const checks = [
    dataHealthItem("Business tenant context", healthState.isBusinessTenant, `organization_type=${organizationType}; tenant=${tenantId}`),
    dataHealthItem("Business module enabled", healthState.hasBusinessModule, "Required before parties and vouchers can return tenant data."),
    dataHealthItem("Accounting module enabled", healthState.hasAccountingModule, "Required for chart of accounts and drill-down reports."),
    dataHealthItem("Chart of accounts loaded", healthState.accountsLoaded, healthState.accountsBlocked ? `Accounts request returned HTTP ${lastBusinessAccountsResult.status}.` : `${lastBusinessAccounts.length} account(s) available.`),
    dataHealthItem("Cash and bank accounts", healthState.hasCashBank, "Required for receipt, payment, and contra voucher posting."),
    dataHealthItem("Revenue / income accounts", healthState.hasRevenue, "Required before sales or service income postings are introduced."),
    dataHealthItem("Expense accounts", healthState.hasExpense, "Required for purchase and expense postings."),
    dataHealthItem("Party GSTIN sample", healthState.partiesGstinReady, partiesGstinCopy),
    dataHealthItem("Voucher drill-down", healthState.drilldownReady, `Current period shows ${voucherCount} posted voucher(s).`),
  ];

  return `
    <section class="erp-health-panel" aria-label="MitraBooks data health">
      <div class="preview-heading compact">
        <div>
          <h4>Data Health</h4>
          <p>Tenant, module, chart, and drill-down readiness for the current MitraBooks context.</p>
        </div>
        <span class="pill ${healthState.accountsLoaded && healthState.hasBusinessModule && healthState.hasAccountingModule ? "ok" : "warn"}">Phase 2B</span>
      </div>
      <ul class="erp-health-list">${checks.join("")}</ul>
      ${renderBusinessDataHealthActions(healthState)}
    </section>
  `;
}

async function loadBusinessPartiesForHealth() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/parties?offset=0&limit=20", { method: "GET" });
  lastBusinessPartiesResult = result;
  if (result.ok) {
    lastBusinessParties = Array.isArray(result.payload?.items) ? result.payload.items : Array.isArray(result.payload) ? result.payload : [];
  }
  return result;
}

async function loadModuleContextForAccounts() {
  if (lastModuleContext) return lastModuleContext;
  const result = await loadModules("mitrabooks");
  if (result.ok) {
    lastModuleContext = result.payload;
  }
  return lastModuleContext;
}

function syncVoucherAccountFromText(lineEl) {
  const input = lineEl?.querySelector(".voucher-account");
  const select = lineEl?.querySelector(".voucher-account-select");
  const query = String(input?.value || "").trim().toLowerCase();
  if (!query || !select) return;
  const match = (Array.isArray(lastBusinessAccounts) ? lastBusinessAccounts : [])
    .map(normalizeBusinessAccount)
    .find((acc) => acc.code.toLowerCase().startsWith(query) || acc.name.toLowerCase().includes(query));
  if (match?.id) {
    select.value = match.id;
  }
}

function renderVoucherLineItem(lineId, voucherType) {
  return `
    <div class="voucher-line" data-line-id="${escapeHtml(lineId)}">
      <label class="field voucher-account-field">
        <span>Account code / name</span>
        <select
          class="voucher-account-select"
          data-line-id="${escapeHtml(lineId)}"
          title="Account code and name"
        >
          <option value="">Select account</option>
        </select>
      </label>
      <input
        class="voucher-account"
        type="text"
        placeholder="Search account code or name"
        list="business-voucher-account-options"
        data-line-id="${escapeHtml(lineId)}"
        autocomplete="off"
      >
      <input
        class="voucher-debit"
        type="number"
        placeholder="Debit"
        min="0"
        step="0.01"
        data-line-id="${escapeHtml(lineId)}"
      >
      <input
        class="voucher-credit"
        type="number"
        placeholder="Credit"
        min="0"
        step="0.01"
        data-line-id="${escapeHtml(lineId)}"
      >
      <button
        class="secondary"
        type="button"
        data-business-action="remove-voucher-line"
        data-line-id="${escapeHtml(lineId)}"
      >✕</button>
    </div>
  `;
}

function updateVoucherBalance() {
  let totalDebit = 0;
  let totalCredit = 0;

  document.querySelectorAll(".voucher-debit").forEach((input) => {
    totalDebit += Number(input.value) || 0;
  });

  document.querySelectorAll(".voucher-credit").forEach((input) => {
    totalCredit += Number(input.value) || 0;
  });

  const isBalanced = Math.abs(totalDebit - totalCredit) < 0.01;
  const balanceEl = document.getElementById("business-voucher-balance");
  if (balanceEl) {
    balanceEl.innerHTML = `Debit: ${formatCurrency(totalDebit)} | Credit: ${formatCurrency(totalCredit)} <span style="margin-left: 12px; ${isBalanced ? "color: green;" : "color: red;"}">${isBalanced ? "✓ Balanced" : "✗ Imbalanced"}</span>`;
  }

  const submitBtn = document.getElementById("business-voucher-submit");
  if (submitBtn) {
    submitBtn.disabled = !isBalanced;
  }
}

function updateVoucherBalanceState() {
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

function addVoucherLine() {
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
      const selected = normalizeBusinessAccount(lastBusinessAccounts.find((acc) => String(acc.account_id ?? acc.id ?? "") === select.value) || {});
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

function removeVoucherLine(lineId) {
  const lineEl = document.querySelector(`[data-line-id="${escapeHtml(lineId)}"]`);
  if (lineEl) {
    lineEl.remove();
    updateVoucherBalanceState();
  }
}

function clearVoucherForm() {
  voucherLineCounter = 0;
  document.getElementById("business-voucher-date").valueAsDate = new Date();
  document.getElementById("business-voucher-reference").value = "";
  document.getElementById("business-voucher-narration").value = "";
  document.getElementById("business-voucher-lines").innerHTML = "";
  updateVoucherBalanceState();
}

async function loadBusinessAccounts() {
  const appKey = "mitrabooks";
  const result = await apiRequest(appKey, "/api/v1/accounting/accounts", { method: "GET" });
  lastBusinessAccountsResult = result;

  if (result.ok) {
    lastBusinessAccounts = accountRowsFromPayload(result.payload);
    if (lastBusinessAccounts.length === 0) {
      const context = await loadModuleContextForAccounts();
      if (String(context?.organization_type || "").toUpperCase() !== "BUSINESS" || !isBusinessModuleEnabled(context)) {
        setLoginStatus(
          "warn",
          "MitraBooks business tenant required",
          `Current tenant is ${context?.organization_type || "unknown"} (${context?.tenant_id || "unknown"}). Sign in as businessadmin@sanmitra.local for voucher posting.`
        );
      } else {
        setLoginStatus("warn", "No chart of accounts found", "Initialize the MitraBooks chart of accounts before posting vouchers.");
      }
    }
    refreshVoucherAccountSelects();
  } else {
    lastBusinessAccounts = [];
    setLoginStatus("danger", "Unable to load accounts", statusDetailText(result.payload?.detail) || "Check accounting access and try again.");
    updateVoucherAccountsStatus();
  }
}

async function createBusinessVoucher(voucherData) {
  const appKey = "mitrabooks";

  const debitLines = [];
  const creditLines = [];
  document.querySelectorAll(".voucher-line").forEach((lineEl) => {
    const accountSelect = lineEl.querySelector(".voucher-account-select");
    const debitInput = lineEl.querySelector(".voucher-debit");
    const creditInput = lineEl.querySelector(".voucher-credit");

    const accountId = accountSelect?.value || "";
    const debit = Number(debitInput?.value) || 0;
    const credit = Number(creditInput?.value) || 0;

    if (accountId && (debit > 0 || credit > 0)) {
      if (debit > 0) debitLines.push({ account_id: Number(accountId), amount: debit });
      if (credit > 0) creditLines.push({ account_id: Number(accountId), amount: credit });
    }
  });

  if (debitLines.length !== 1 || creditLines.length !== 1) {
    setLoginStatus("warn", "One debit and one credit required", "Phase 1 voucher posting supports one debit account and one credit account.");
    return;
  }
  const debitTotal = debitLines[0].amount;
  const creditTotal = creditLines[0].amount;
  if (Math.abs(debitTotal - creditTotal) >= 0.01) {
    setLoginStatus("warn", "Voucher is not balanced", "Debit amount must equal credit amount.");
    return;
  }

  const payload = {
    voucher_type: "journal",
    entry_date: voucherData.date,
    amount: debitTotal.toFixed(2),
    debit_account_id: debitLines[0].account_id,
    credit_account_id: creditLines[0].account_id,
    description: voucherData.narration || voucherData.reference || "Business voucher",
    reference: voucherData.reference || null,
  };

  const result = await apiRequest(appKey, "/api/v1/business/vouchers", {
    method: "POST",
    headers: {
      "X-Idempotency-Key": `business-voucher-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    },
    body: JSON.stringify(payload),
  });

  if (result.ok) {
    setLoginStatus("ok", "Voucher posted", `Journal entry ${result.payload?.id || "created"} posted.`);
    document.getElementById("business-voucher-create-dialog")?.close();
    clearVoucherForm();
    await loadBusinessVouchers();
    // Force refresh of current workspace
    if (activeBusinessWorkspace === "vouchers") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  } else {
    setLoginStatus("danger", "Post voucher failed", statusDetailText(result.payload?.detail) || "Check entries and try again.");
  }
  renderJson(apiOutput, { create_voucher: result });
}

async function loadBusinessVouchers(filters = {}) {
  const appKey = "mitrabooks";
  const params = new URLSearchParams();
  params.append("offset", 0);
  params.append("limit", 20);

  const queryString = params.toString();
  const url = `/api/v1/business/vouchers${queryString ? "?" + queryString : ""}`;

  const result = await apiRequest(appKey, url, { method: "GET" });
  if (result.ok) {
    lastBusinessVouchers = Array.isArray(result.payload?.items) ? result.payload.items : Array.isArray(result.payload) ? result.payload : [];
    if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "vouchers") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  } else {
    lastBusinessVouchers = [];
    setLoginStatus("danger", "Unable to load vouchers", statusDetailText(result.payload?.detail) || `Voucher list request failed with HTTP ${result.status}.`);
    if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "vouchers") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  }
  renderJson(apiOutput, { vouchers: { ok: result.ok, status: result.status, count: lastBusinessVouchers.length, detail: result.payload?.detail || null } });
}

async function reverseBusinessVoucher(voucherId) {
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
  renderJson(apiOutput, { reverse_voucher: result });
}

async function openBusinessCreateVoucherDialog() {
  const dialog = document.getElementById("business-voucher-create-dialog");
  if (!dialog) return;

  if (!Array.isArray(lastBusinessAccounts) || lastBusinessAccounts.length === 0) {
    await loadBusinessAccounts();
  }
  clearVoucherForm();
  document.getElementById("business-voucher-date").valueAsDate = new Date();

  // Add initial line items
  addVoucherLine();
  addVoucherLine();
  if (!Array.isArray(lastBusinessAccounts) || lastBusinessAccounts.length === 0) {
    setLoginStatus("warn", "Accounts unavailable", "Load the MitraBooks chart of accounts before posting a voucher.");
  }

  dialog.showModal();
}

// ========== Business Module: Audit Trail ==========

let lastAuditEvents = [];
const auditListState = {
  offset: 0,
  q: "",
  entity_type: "",
  action: "",
  from_date: "",
  to_date: "",
};

function formatTimestampIST(utcTimestamp) {
  if (!utcTimestamp) return "-";
  try {
    // Parse UTC timestamp and convert to IST (UTC+5:30)
    const date = new Date(utcTimestamp.includes('Z') ? utcTimestamp : utcTimestamp + 'Z');
    const istDate = new Date(date.getTime() + (5.5 * 60 * 60 * 1000)); // Add 5.5 hours for IST
    const year = istDate.getUTCFullYear();
    const month = String(istDate.getUTCMonth() + 1).padStart(2, '0');
    const day = String(istDate.getUTCDate()).padStart(2, '0');
    const hours = String(istDate.getUTCHours()).padStart(2, '0');
    const minutes = String(istDate.getUTCMinutes()).padStart(2, '0');
    const seconds = String(istDate.getUTCSeconds()).padStart(2, '0');
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds} IST`;
  } catch (e) {
    return utcTimestamp.slice(0, 19);
  }
}

function renderAuditEventsTable(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `<p class="muted">No audit events found.</p>`;
  }
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Entity</th>
            <th>Action</th>
            <th>Actor</th>
            <th>Detail</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows.slice(0, 30).map((row) => {
            const detail = row.description || row.detail || row.entity_id || "-";
            const detailShort = detail.length > 30 ? detail.slice(0, 27) + "..." : detail;
            return `
              <tr>
                <td style="font-size: 12px;">${escapeHtml(formatTimestampIST(row.timestamp || row.created_at || ""))}</td>
                <td>${escapeHtml(row.entity_type || row.entity || "-")}</td>
                <td><span class="pill">${escapeHtml(row.action || "unknown")}</span></td>
                <td>${escapeHtml(row.actor || row.user || "-")}</td>
                <td style="font-size: 12px;">${escapeHtml(detailShort)}</td>
                <td>
                  <button
                    class="secondary"
                    type="button"
                    data-business-action="view-audit-event"
                    data-event-id="${escapeHtml(row.event_id || row.id || "")}"
                  >View</button>
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderAuditListFilters(rowsLength) {
  const state = auditListState;
  const offset = Number(state.offset || 0);
  const startRow = rowsLength > 0 ? offset + 1 : 0;
  const endRow = rowsLength > 0 ? offset + Math.min(rowsLength, 30) : 0;
  const nextDisabled = rowsLength < 30 ? "disabled" : "";
  const prevDisabled = offset <= 0 ? "disabled" : "";

  return `
    <div class="list-filter-panel" data-business-list="audit">
      <div class="list-filter-bar">
        <label class="field">
          <span>Entity</span>
          <select name="entity_type">
            <option value="">All entities</option>
            <option value="party" ${state.entity_type === "party" ? "selected" : ""}>Party</option>
            <option value="voucher" ${state.entity_type === "voucher" ? "selected" : ""}>Voucher</option>
            <option value="account" ${state.entity_type === "account" ? "selected" : ""}>Account</option>
          </select>
        </label>
        <label class="field">
          <span>Action</span>
          <select name="action">
            <option value="">All actions</option>
            <option value="create" ${state.action === "create" ? "selected" : ""}>Create</option>
            <option value="update" ${state.action === "update" ? "selected" : ""}>Update</option>
            <option value="post" ${state.action === "post" ? "selected" : ""}>Post</option>
            <option value="reverse" ${state.action === "reverse" ? "selected" : ""}>Reverse</option>
            <option value="deactivate" ${state.action === "deactivate" ? "selected" : ""}>Deactivate</option>
          </select>
        </label>
        <label class="field">
          <span>From</span>
          <input name="from_date" type="date" value="${escapeHtml(state.from_date || "")}">
        </label>
        <label class="field">
          <span>To</span>
          <input name="to_date" type="date" value="${escapeHtml(state.to_date || "")}">
        </label>
        <div class="list-filter-actions">
          <button type="button" data-business-action="apply-audit-filter">Apply</button>
          <button class="secondary" type="button" data-business-action="reset-audit-filter">Reset</button>
        </div>
      </div>
      <div class="paging-row">
        <span class="muted">Showing ${escapeHtml(startRow)}-${escapeHtml(endRow)}</span>
        <button class="secondary" type="button" data-business-action="page-audit" data-page-direction="prev" ${prevDisabled}>Prev</button>
        <button class="secondary" type="button" data-business-action="page-audit" data-page-direction="next" ${nextDisabled}>Next</button>
      </div>
    </div>
  `;
}

async function loadAuditEvents(filters = {}) {
  const appKey = "mitrabooks";
  const state = auditListState;
  const params = new URLSearchParams();

  if (state.entity_type) params.append("entity_type", state.entity_type);
  if (state.action) params.append("action", state.action);
  if (state.from_date) params.append("from_date", state.from_date);
  if (state.to_date) params.append("to_date", state.to_date);
  params.append("offset", state.offset || 0);
  params.append("limit", 30);

  const queryString = params.toString();
  const url = `/api/v1/audit/events${queryString ? "?" + queryString : ""}`;

  const result = await apiRequest(appKey, url, { method: "GET" });
  if (result.ok) {
    lastAuditEvents = Array.isArray(result.payload?.items) ? result.payload.items : Array.isArray(result.payload) ? result.payload : [];
    if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "audit") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  } else {
    lastAuditEvents = [];
    setLoginStatus("warn", "Unable to load audit events", result.payload?.detail || "Check connection and try again.");
  }
  renderJson(apiOutput, { audit_events: { ok: result.ok, count: lastAuditEvents.length } });
}

function openAuditEventDetailDialog(eventId) {
  const dialog = document.getElementById("audit-event-detail-dialog");
  if (!dialog) return;

  const event = lastAuditEvents.find((e) => (e.event_id || e.id) === eventId);
  if (!event) {
    setLoginStatus("warn", "Event not found", "The event may have been deleted.");
    return;
  }

  document.getElementById("audit-event-entity").textContent = event.entity_type || "-";
  document.getElementById("audit-event-action").textContent = event.action || "-";
  document.getElementById("audit-event-actor").textContent = event.actor || event.user || "-";
  document.getElementById("audit-event-timestamp").textContent = String(event.timestamp || event.created_at || "-").slice(0, 19);
  document.getElementById("audit-event-detail-label").textContent = `${event.entity_type || "Event"} · ${event.action || "unknown"}`;

  const payload = event.payload || event.details || {};
  document.getElementById("audit-event-payload").textContent = JSON.stringify(payload, null, 2);

  dialog.showModal();
}

function applyAuditFilters() {
  const panel = document.querySelector("[data-business-list='audit']");
  if (!panel) return;

  const entityInput = panel.querySelector("select[name='entity_type']");
  const actionInput = panel.querySelector("select[name='action']");
  const fromInput = panel.querySelector("input[name='from_date']");
  const toInput = panel.querySelector("input[name='to_date']");

  auditListState.entity_type = entityInput?.value || "";
  auditListState.action = actionInput?.value || "";
  auditListState.from_date = fromInput?.value || "";
  auditListState.to_date = toInput?.value || "";
  auditListState.offset = 0;

  loadAuditEvents();
}

function resetAuditFilters() {
  auditListState.offset = 0;
  auditListState.entity_type = "";
  auditListState.action = "";
  auditListState.from_date = "";
  auditListState.to_date = "";
  loadAuditEvents();
}

function pageAuditList(direction) {
  const offset = Number(auditListState.offset || 0);
  auditListState.offset = direction === "next" ? offset + 30 : Math.max(0, offset - 30);
  loadAuditEvents();
}

function renderGruhaDashboard(config, payload) {
  const data = payload || {};
  const flats = resultRows(data.flats);
  const members = resultRows(data.members);
  const complaints = resultRows(data.complaints);
  const bills = resultRows(data.bills);
  const rooms = resultRows(data.rooms);
  const meetings = resultRows(data.meetings);
  const assets = resultRows(data.assets);
  const financialYears = resultRows(data.financialYears);
  const settings = resultPayload(data.settings, {});
  const openComplaints = complaints.filter((row) => !["closed", "resolved", "completed"].includes(String(row.status || "").toLowerCase())).length;
  const pendingBills = bills.filter((row) => !["paid", "posted", "closed"].includes(String(row.status || "").toLowerCase()));
  const pendingDues = pendingBills.reduce((sum, row) => sum + Number(row.balance_due || row.due_amount || row.total_amount || row.amount || 0), 0);
  const stats = [
    ["Flats", flats.length, "tenant-scoped units"],
    ["Members", members.length, "owners and residents"],
    ["Pending Dues", formatCurrency(pendingDues), `${pendingBills.length} bills`],
    ["Complaints Open", openComplaints, "service desk"],
  ];
  const societyName = settings?.society_name || settings?.name || "GruhaMitra Society";

  return `
    <div class="legacy-dashboard gruha-dashboard">
      <div class="society-header-preview">
        <img src="${config.logo}" alt="GruhaMitra">
        <div>
          <h3>${escapeHtml(societyName)}</h3>
          <p>Housing operations inside MitraBooks Unified ERP</p>
        </div>
        <span class="pill">HOUSING</span>
      </div>
      ${renderStatusBlock("GruhaMitra data", data.summary)}
      <div class="metric-grid four">${renderStatCards(stats)}</div>
      ${renderGruhaWorkspace({
        flats,
        members,
        complaints,
        bills,
        rooms,
        meetings,
        assets,
        financialYears,
        settings,
        config,
      })}
    </div>
  `;
}

function renderGruhaWorkspace(data) {
  if (activeGruhaWorkspace === "maintenance") {
    return `
      <div class="dashboard-main-grid">
        <article>
          <h4>Maintenance Bills</h4>
          ${renderSimpleTable(data.bills, [
            { label: "Bill", value: (row) => row.bill_number || row.id || row.bill_id || "-" },
            { label: "Flat", value: (row) => row.flat_number || row.flat_id || "-" },
            { label: "Amount", value: (row) => formatCurrency(row.total_amount || row.amount || row.balance_due) },
            { label: "Status", value: (row) => row.status || "-" },
          ], "No maintenance bills returned by the compatibility API.")}
        </article>
        <article>
          <h4>Accounting Boundary</h4>
          <p class="muted">Maintenance collections use the unified `/api/v1/housing/maintenance-collections` route, which posts through the MitraBooks accounting service with tenant and app-key context.</p>
          <div class="grouped-nav-preview">
            <article><strong>Billing</strong><span>Use legacy bill generation endpoints for existing GruhaMitra behavior.</span></article>
            <article><strong>Collections</strong><span>Post through MitraBooks accounting; do not duplicate ledger logic in housing.</span></article>
          </div>
        </article>
      </div>
    `;
  }
  if (activeGruhaWorkspace === "members") {
    return renderSimpleTable(data.members, [
      { label: "Name", value: (row) => row.name || row.full_name || "-" },
      { label: "Flat", value: (row) => row.flat_number || row.unit_label || "-" },
      { label: "Type", value: (row) => row.member_type || row.role || "-" },
      { label: "Status", value: (row) => row.status || "-" },
    ], "No members found for this tenant/app context.");
  }
  if (activeGruhaWorkspace === "flats") {
    return renderSimpleTable(data.flats, [
      { label: "Flat", value: (row) => row.flat_number || row.id || "-" },
      { label: "Block", value: (row) => row.block || "-" },
      { label: "Floor", value: (row) => row.floor ?? "-" },
      { label: "Status", value: (row) => row.status || "-" },
    ], "No flats found. Configure society blocks or import flats.");
  }
  if (activeGruhaWorkspace === "complaints") {
    return renderSimpleTable(data.complaints, [
      { label: "Complaint", value: (row) => row.title || row.subject || row.id || "-" },
      { label: "Flat", value: (row) => row.flat_number || row.flat_id || "-" },
      { label: "Category", value: (row) => row.category || "-" },
      { label: "Status", value: (row) => row.status || "-" },
    ], "No complaints found for this society.");
  }
  if (activeGruhaWorkspace === "messages") {
    return renderSimpleTable(data.rooms, [
      { label: "Room", value: (row) => row.name || row.id || "-" },
      { label: "Type", value: (row) => row.type || "-" },
      { label: "Audience", value: (row) => row.audience_type || "public" },
      { label: "Updated", value: (row) => row.last_message_at || row.updated_at || "-" },
    ], "No message rooms found.");
  }
  if (activeGruhaWorkspace === "meetings") {
    return renderSimpleTable(data.meetings, [
      { label: "Meeting", value: (row) => row.meeting_title || row.title || row.id || "-" },
      { label: "Date", value: (row) => row.meeting_date || "-" },
      { label: "Type", value: (row) => row.meeting_type || "-" },
      { label: "Status", value: (row) => row.status || "-" },
    ], "No meetings found.");
  }
  if (activeGruhaWorkspace === "assets") {
    return renderSimpleTable(data.assets, [
      { label: "Asset", value: (row) => row.name || row.asset_code || "-" },
      { label: "Category", value: (row) => row.category || "-" },
      { label: "Location", value: (row) => row.location || "-" },
      { label: "Accounting", value: (row) => row.accounting_posting_status || "not_posted" },
    ], "No society assets found.");
  }
  if (activeGruhaWorkspace === "accounting" || activeGruhaWorkspace === "reports") {
    return renderAccountingDrilldownPanel();
  }
  if (activeGruhaWorkspace === "settings") {
    const blocks = Array.isArray(data.settings?.blocks_config) ? data.settings.blocks_config : [];
    return `
      <div class="dashboard-main-grid">
        <article>
          <h4>Society Settings</h4>
          ${renderSimpleTable(blocks, [
            { label: "Block", value: (row) => row.name || "-" },
            { label: "Floors", value: (row) => row.floors ?? "-" },
            { label: "Flats/Floor", value: (row) => row.flatsPerFloor ?? "-" },
          ], "No block configuration found.")}
        </article>
        <article>
          <h4>Financial Years</h4>
          ${renderSimpleTable(data.financialYears, [
            { label: "Year", value: (row) => row.year_name || row.id || "-" },
            { label: "Start", value: (row) => row.start_date || "-" },
            { label: "End", value: (row) => row.end_date || "-" },
            { label: "Status", value: (row) => row.status || "-" },
          ], "No financial years found.")}
        </article>
      </div>
    `;
  }
  return `
    <div class="dashboard-main-grid">
      <article>
        <h4>Quick Actions</h4>
        <div class="quick-grid">
          ${gruhaNavigationItems().filter((item) => item.gruhaWorkspace !== "overview").map((item) => `
            <button class="quick-tile" type="button" data-gruha-action="workspace-view" data-workspace-view="${escapeHtml(item.gruhaWorkspace)}">
              <span class="quick-icon">${escapeHtml(item.icon)}</span>
              <span>${escapeHtml(item.label)}</span>
            </button>
          `).join("")}
        </div>
      </article>
      <article>
        <h4>Integration Status</h4>
        <ul class="activity-list">
          ${renderActivity([
            "Legacy GruhaMitra compatibility routes are mounted under /api/v1",
            "Tenant, app-key, and module registry checks stay in the unified backend",
            "Accounting remains delegated to MitraBooks shared journal posting",
          ])}
        </ul>
      </article>
    </div>
    <article class="trend-panel">
      <h4>Reports</h4>
      ${renderAccountingDrilldownPanel()}
    </article>
  `;
}

async function runChecks() {
  const activeAppKey = EXPERIENCE_APP_KEYS[currentExperience] || APP_KEY;
  const health = await loadHealth(activeAppKey);
  healthPill.textContent = statusLabel(health);
  healthPill.className = `pill ${health.ok ? "ok" : "danger"}`;

  const modules = await loadModules(activeAppKey);
  if (modules.ok) {
    lastModuleContext = modules.payload;
    updateTrustedContextUi(lastModuleContext);
    updateSessionUi();
  }
  renderJson(apiOutput, { health, modules });
  renderModuleState(moduleState, modules);

  if (!modules.ok && modules.status === 401) {
    lastModuleContext = null;
    clearAccessToken();
    renderModules();
    setLoginStatus("warn", "Sign in required", "Enter your email and password to load tenant data.");
    updateSessionUi();
    return;
  }

  if (!modules.ok && currentExperience === "mitrabooks") {
    lastModuleContext = null;
    renderModules();
    setLoginStatus("warn", "Tenant session required", "Sign in to load your MitraBooks dashboard.");
    updateSessionUi();
    return;
  }

  if (modules.ok && currentExperience === "mitrabooks") {
    renderModules(moduleItemsFromPayload(modules.payload), { preview: false });
  } else {
    renderModules();
  }

  if (currentExperience === "platform") {
    await loadPlatformOwnerDashboard();
  } else if (currentExperience === "mandir") {
    await loadMandirDashboard();
  } else if (currentExperience === "gruha") {
    await loadGruhaDashboard();
  } else if (currentExperience === "mitrabooks") {
    await loadBusinessAccounts();
    await loadBusinessPartiesForHealth();
    const accountingDrilldown = await loadAccountingDrilldownResult();
    renderJson(apiOutput, { health, modules, accounting_drilldown: accountingDrilldown });
    refreshBooksHealthWidget();
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

async function loadGruhaDashboard() {
  const billingPeriodQuery = currentBillingPeriodQuery();
  const [
    settings,
    flats,
    members,
    complaints,
    bills,
    rooms,
    meetings,
    assets,
    financialYears,
    accountingDrilldown,
  ] = await Promise.all([
    apiRequest("gruhamitra", "/api/v1/settings/society", { method: "GET" }),
    apiRequest("gruhamitra", "/api/v1/flats", { method: "GET" }),
    apiRequest("gruhamitra", "/api/v1/member-onboarding", { method: "GET" }),
    apiRequest("gruhamitra", "/api/v1/complaints/", { method: "GET" }),
    apiRequest("gruhamitra", `/api/v1/maintenance/bills?${billingPeriodQuery}`, { method: "GET" }),
    apiRequest("gruhamitra", "/api/v1/messages/rooms", { method: "GET" }),
    apiRequest("gruhamitra", "/api/v1/meetings", { method: "GET" }),
    apiRequest("gruhamitra", "/api/v1/assets", { method: "GET" }),
    apiRequest("gruhamitra", "/api/v1/financial-years/", { method: "GET" }),
    loadAccountingDrilldownResult(),
  ]);
  lastGruhaData = {
    settings,
    flats,
    members,
    complaints,
    bills,
    rooms,
    meetings,
    assets,
    financialYears,
    accountingDrilldown,
    summary: [settings, flats, members, complaints, bills, rooms, meetings, assets, financialYears].find((result) => !result.ok) || null,
  };
  renderJson(apiOutput, { gruhamitra: lastGruhaData });
  dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig.gruha);
  syncGruhaNavActiveState();
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
  const panchang = await apiRequest("mandirmitra", "/api/v1/panchang/today", { method: "GET" });
  const moduleConfig = await apiRequest("mandirmitra", "/api/v1/temples/modules/config", { method: "GET" });
  const donationCategoryReport = await apiRequest("mandirmitra", `/api/v1/reports/donations/category-wise?${reportRangeQuery}`, { method: "GET" });
  const donationDetailReport = await apiRequest("mandirmitra", `/api/v1/reports/donations/detailed?${reportRangeQuery}`, { method: "GET" });
  const sevaDetailReport = await apiRequest("mandirmitra", `/api/v1/reports/sevas/detailed?${reportRangeQuery}`, { method: "GET" });
  const sevaScheduleReport = await apiRequest("mandirmitra", "/api/v1/reports/sevas/schedule?days=30", { method: "GET" });
  const devoteesReport = await apiRequest("mandirmitra", "/api/v1/devotees?limit=50", { method: "GET" });
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
  lastMandirPanchang = panchang.ok ? panchang.payload : panchang;
  lastMandirModuleConfig = moduleConfig.ok ? moduleConfig.payload : lastMandirModuleConfig;
  lastMandirOperationalReports = {
    donation_category: donationCategoryReport.ok ? donationCategoryReport.payload : donationCategoryReport,
    donation_detail: donationDetailReport.ok ? donationDetailReport.payload : donationDetailReport,
    seva_detail: sevaDetailReport.ok ? sevaDetailReport.payload : sevaDetailReport,
    seva_schedule: sevaScheduleReport.ok ? sevaScheduleReport.payload : sevaScheduleReport,
    devotees: devoteesReport.ok && Array.isArray(devoteesReport.payload) ? devoteesReport.payload : [],
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
    mandir_panchang: panchang,
    mandir_module_config: moduleConfig,
    mandir_donation_category_report: donationCategoryReport,
    mandir_donation_detail_report: donationDetailReport,
    mandir_seva_detail_report: sevaDetailReport,
    mandir_seva_schedule_report: sevaScheduleReport,
    mandir_devotees_report: devoteesReport,
    accounting_drilldown: accountingDrilldown,
  });
  const hasLiveData = stats.ok || pendingPayments.ok || paymentExceptions.ok || donations.ok || sevaBookings.ok;
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
    panchang: lastMandirPanchang,
    operational_reports: lastMandirOperationalReports,
    module_config: lastMandirModuleConfig,
    payment_accounts: paymentAccounts.ok ? paymentAccounts.payload : lastMandirPaymentAccounts,
    accounts: accounts.ok && Array.isArray(accounts.payload) ? accounts.payload : lastMandirAccounts,
    receipt: lastMandirReceipt,
    form_result: lastMandirFormResult,
    live_data_available: hasLiveData,
  });
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
  const inventoryEnabled = Boolean(payload.module_config?.module_inventory_enabled);
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

function openMandirCancelReceiptDialog(button) {
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

async function submitMandirCancelReceipt() {
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
  activeMandirWorkspace = view;
  syncMandirNavActiveState();
  await loadMandirDashboard();
  document.querySelector(".content")?.scrollTo({ top: 0, behavior: "smooth" });
}

async function setGruhaWorkspace(view) {
  const allowedViews = new Set([
    "overview",
    "maintenance",
    "members",
    "flats",
    "complaints",
    "messages",
    "meetings",
    "assets",
    "accounting",
    "reports",
    "settings",
  ]);
  if (!allowedViews.has(view)) {
    return;
  }
  activeGruhaWorkspace = view;
  syncGruhaNavActiveState();
  if (!lastGruhaData) {
    await loadGruhaDashboard();
  } else {
    dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig.gruha);
  }
  document.querySelector(".content")?.scrollTo({ top: 0, behavior: "smooth" });
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
  } else if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "accounting") {
    dashboardPreview.innerHTML = renderAccountingDrilldownPanel();
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
  document.getElementById(`mode-${nextExperience}`)?.classList.add("active");
  renderModules();
  if (nextExperience === "platform") {
    loadPlatformOwnerDashboard();
  } else if (nextExperience === "mandir") {
    loadMandirDashboard();
  } else if (nextExperience === "gruha") {
    loadGruhaDashboard();
  } else if (nextExperience === "mitrabooks") {
    const appKey = EXPERIENCE_APP_KEYS[nextExperience] || APP_KEY;
    loadAndRenderGroupedNav(appKey);
    loadAccountingDrilldownResult().then(() => {
      dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig[currentExperience]);
    });
  }
}

document.getElementById("save-config").addEventListener("click", () => {
  setConfiguredApiBaseUrl(apiBaseInput.value);
  setAccessToken(tokenInput.value);
  lastModuleContext = null;
  updateSessionUi();
  runChecks();
});

// Enhanced login form handling
const loginForm = document.getElementById("login-form");
if (loginForm) {
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await signInWithPassword();
  });
}

// Password visibility toggle
const togglePasswordBtn = document.getElementById("toggle-password");
if (togglePasswordBtn && loginPassword) {
  togglePasswordBtn.addEventListener("click", (event) => {
    event.preventDefault();
    const nextType = loginPassword.type === "password" ? "text" : "password";
    loginPassword.type = nextType;
    const isVisible = nextType === "text";
    togglePasswordBtn.classList.toggle("show", isVisible);
    togglePasswordBtn.setAttribute("aria-pressed", String(isVisible));
  });
}
document.getElementById("run-checks").addEventListener("click", runChecks);
document.getElementById("clear-token").addEventListener("click", () => {
  clearAccessToken();
  lastModuleContext = null;
  tokenInput.value = "";
  updateSessionUi();
  setLoginStatus("", "", "");
  runChecks();
});
document.getElementById("topbar-logout")?.addEventListener("click", () => {
  clearAccessToken();
  lastModuleContext = null;
  if (tokenInput) {
    tokenInput.value = "";
  }
  if (loginPassword) {
    loginPassword.value = "";
  }
  updateSessionUi();
  setLoginStatus("", "", "");
  runChecks();
});
nav.addEventListener("click", (event) => {
  const toggle = event.target.closest("[data-nav-group-toggle]");
  if (!toggle) {
    return;
  }
  event.preventDefault();
  const groupId = toggle.getAttribute("data-nav-group-toggle") || "";
  const panel = document.getElementById(groupId);
  const expanded = toggle.getAttribute("aria-expanded") !== "false";
  toggle.setAttribute("aria-expanded", expanded ? "false" : "true");
  if (panel) {
    panel.hidden = expanded;
  }
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
nav.addEventListener("click", (event) => {
  const link = event.target.closest("a[data-gruha-workspace]");
  if (!link || currentExperience !== "gruha") {
    return;
  }
  event.preventDefault();
  if (link.getAttribute("aria-disabled") === "true") {
    return;
  }
  setGruhaWorkspace(link.dataset.gruhaWorkspace || "overview");
});
nav.addEventListener("click", (event) => {
  const link = event.target.closest("a[data-business-workspace]");
  if (!link || currentExperience !== "mitrabooks") {
    return;
  }
  event.preventDefault();
  if (link.getAttribute("aria-disabled") === "true") {
    return;
  }
  setBusinessWorkspace(link.dataset.businessWorkspace || "overview");
});
dashboardPreview.addEventListener("click", (event) => {
  const button = event.target.closest("[data-platform-action], [data-mandir-action], [data-gruha-action], [data-accounting-action], [data-business-action]");
  if (!button) {
    return;
  }
  const requestId = button.getAttribute("data-request-id") || "";
  const action = button.getAttribute("data-platform-action");
  const mandirAction = button.getAttribute("data-mandir-action");
  const gruhaAction = button.getAttribute("data-gruha-action");
  const accountingAction = button.getAttribute("data-accounting-action");
  const businessAction = button.getAttribute("data-business-action");
  if (action === "approve") {
    approveOnboardingRequest(requestId);
  } else if (action === "reject") {
    rejectOnboardingRequest(requestId);
  } else if (action === "entitlements") {
    openTenantEntitlementsDialog(button);
  } else if (action === "open-platform-owner") {
    setExperience("platform");
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
  } else if (mandirAction === "cancel-receipt") {
    openMandirCancelReceiptDialog(button);
  } else if (mandirAction === "apply-list-filter") {
    applyMandirListFilter(button.getAttribute("data-list-kind") || "");
  } else if (mandirAction === "reset-list-filter") {
    resetMandirListFilter(button.getAttribute("data-list-kind") || "");
  } else if (mandirAction === "page-list") {
    pageMandirList(button.getAttribute("data-list-kind") || "", button.getAttribute("data-page-direction") || "next");
  } else if (mandirAction === "workspace-view") {
    setMandirWorkspace(button.getAttribute("data-workspace-view") || "overview");
  } else if (gruhaAction === "workspace-view") {
    setGruhaWorkspace(button.getAttribute("data-workspace-view") || "overview");
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
  } else if (businessAction === "open-create-party") {
    openBusinessCreatePartyDialog();
  } else if (businessAction === "edit-party") {
    openBusinessEditPartyDialog(button);
  } else if (businessAction === "deactivate-party") {
    const partyId = button.getAttribute("data-party-id") || "";
    if (confirm("Deactivate this party? It will no longer appear in new vouchers.")) {
      deactivateBusinessParty(partyId);
    }
  } else if (businessAction === "apply-list-filter") {
    applyBusinessListFilter(button.getAttribute("data-list-kind") || "");
  } else if (businessAction === "reset-list-filter") {
    resetBusinessListFilter(button.getAttribute("data-list-kind") || "");
  } else if (businessAction === "page-list") {
    pageBusinessList(button.getAttribute("data-list-kind") || "", button.getAttribute("data-page-direction") || "next");
  } else if (businessAction === "workspace-view") {
    setBusinessWorkspace(button.getAttribute("data-workspace-view") || "overview");
  } else if (businessAction === "open-create-voucher") {
    openBusinessCreateVoucherDialog();
  } else if (businessAction === "remove-voucher-line") {
    removeVoucherLine(button.getAttribute("data-line-id") || "");
  } else if (businessAction === "reverse-voucher") {
    const voucherId = button.getAttribute("data-voucher-id") || "";
    if (confirm("Reverse this voucher? A reversal entry will be created.")) {
      reverseBusinessVoucher(voucherId);
    }
  } else if (businessAction === "view-audit-event") {
    openAuditEventDetailDialog(button.getAttribute("data-event-id") || "");
  } else if (businessAction === "apply-audit-filter") {
    applyAuditFilters();
  } else if (businessAction === "reset-audit-filter") {
    resetAuditFilters();
  } else if (businessAction === "page-audit") {
    pageAuditList(button.getAttribute("data-page-direction") || "next");
  }
});
dashboardPreview.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") {
    return;
  }
  const input = event.target.closest("[data-mandir-list] input, [data-mandir-list] select, [data-business-list] input, [data-business-list] select");
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
  const mandirPanel = input.closest("[data-mandir-list]");
  const businessPanel = input.closest("[data-business-list]");
  if (mandirPanel) {
    applyMandirListFilter(mandirPanel.getAttribute("data-mandir-list") || "");
  } else if (businessPanel) {
    applyBusinessListFilter(businessPanel.getAttribute("data-business-list") || "");
  }
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
document.getElementById("mandir-cancel-receipt-close").addEventListener("click", () => mandirCancelReceiptDialog.close());
document.getElementById("mandir-cancel-receipt-cancel").addEventListener("click", () => mandirCancelReceiptDialog.close());
mandirCancelReceiptForm.addEventListener("submit", (event) => {
  event.preventDefault();
  submitMandirCancelReceipt();
});
receiptPreviewDialog.addEventListener("close", () => {
  receiptPreviewFrame.removeAttribute("src");
  if (activeReceiptPreviewObjectUrl) {
    window.URL.revokeObjectURL(activeReceiptPreviewObjectUrl);
    activeReceiptPreviewObjectUrl = "";
  }
});
const businessPartyCreateDialog = document.getElementById("business-party-create-dialog");
const businessPartyCreateForm = document.getElementById("business-party-create-form");
const businessPartyEditDialog = document.getElementById("business-party-edit-dialog");
const businessPartyEditForm = document.getElementById("business-party-edit-form");

if (businessPartyCreateForm) {
  businessPartyCreateForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const name = document.getElementById("business-party-name")?.value || "";
    const party_type = document.getElementById("business-party-type")?.value || "customer";
    const gstin = document.getElementById("business-party-gstin")?.value || "";
    const opening_balance = document.getElementById("business-party-opening-balance")?.value || "0";

    if (!name.trim()) {
      setLoginStatus("warn", "Party name required", "Enter a name for the party.");
      return;
    }

    createBusinessParty({ name, party_type, gstin, opening_balance });
  });
}

if (businessPartyEditForm) {
  businessPartyEditForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const partyId = document.getElementById("business-party-edit-id")?.value || "";
    const name = document.getElementById("business-party-edit-name")?.value || "";
    const gstin = document.getElementById("business-party-edit-gstin")?.value || "";
    const opening_balance = document.getElementById("business-party-edit-opening-balance")?.value || "0";

    if (!name.trim()) {
      setLoginStatus("warn", "Party name required", "Enter a name for the party.");
      return;
    }

    updateBusinessParty(partyId, { name, gstin, opening_balance });
  });
}

document.getElementById("business-party-create-close")?.addEventListener("click", () => businessPartyCreateDialog?.close());
document.getElementById("business-party-create-cancel")?.addEventListener("click", () => businessPartyCreateDialog?.close());
document.getElementById("business-party-edit-close")?.addEventListener("click", () => businessPartyEditDialog?.close());
document.getElementById("business-party-edit-cancel")?.addEventListener("click", () => businessPartyEditDialog?.close());

const businessVoucherCreateDialog = document.getElementById("business-voucher-create-dialog");
const businessVoucherCreateForm = document.getElementById("business-voucher-create-form");

if (businessVoucherCreateForm) {
  businessVoucherCreateForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const date = document.getElementById("business-voucher-date")?.value || "";
    const reference = document.getElementById("business-voucher-reference")?.value || "";
    const narration = document.getElementById("business-voucher-narration")?.value || "";

    if (!date) {
      setLoginStatus("warn", "Date required", "Enter the voucher date.");
      return;
    }

    createBusinessVoucher({ date, reference, narration });
  });
}

document.getElementById("business-voucher-create-close")?.addEventListener("click", () => businessVoucherCreateDialog?.close());
document.getElementById("business-voucher-create-cancel")?.addEventListener("click", () => businessVoucherCreateDialog?.close());

document.getElementById("business-voucher-add-line")?.addEventListener("click", (event) => {
  event.preventDefault();
  addVoucherLine();
});

const auditEventDetailDialog = document.getElementById("audit-event-detail-dialog");
document.getElementById("audit-event-detail-close")?.addEventListener("click", () => auditEventDetailDialog?.close());
document.getElementById("audit-event-detail-cancel")?.addEventListener("click", () => auditEventDetailDialog?.close());

dashboardPreview.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") {
    return;
  }
  const input = event.target.closest("[data-business-list='audit'] input, [data-business-list='audit'] select");
  if (!input) {
    return;
  }
  event.preventDefault();
  applyAuditFilters();
});

document.getElementById("mode-mitrabooks").addEventListener("click", () => setExperience("mitrabooks"));
document.getElementById("mode-platform").addEventListener("click", () => setExperience("platform"));
document.getElementById("mode-mandir").addEventListener("click", () => setExperience("mandir"));
document.getElementById("mode-gruha").addEventListener("click", () => setExperience("gruha"));

// Initialize theme on app load
initializeTheme();

// Theme toggle buttons (if they exist in the sidebar)
const themeDarkBtn = document.getElementById("theme-dark-btn");
const themeLightBtn = document.getElementById("theme-light-btn");

if (themeDarkBtn) {
  themeDarkBtn.addEventListener("click", () => setTheme("dark"));
}
if (themeLightBtn) {
  themeLightBtn.addEventListener("click", () => setTheme("light"));
}

// ============================================
// SIDEBAR UI INTERACTIONS (Phase 1C)
// ============================================

/**
 * Org Selector Dropdown Toggle
 */
const orgTrigger = document.getElementById("org-trigger");
const orgMenu = document.getElementById("org-menu");
const orgSelector = document.getElementById("org-selector");
const orgOptions = document.querySelectorAll(".org-option");

if (orgTrigger) {
  orgTrigger.addEventListener("click", () => {
    const isOpen = !orgMenu.hidden;
    orgMenu.hidden = isOpen;
    orgSelector.classList.toggle("open", !isOpen);
  });
}

// Close org dropdown when option is selected
orgOptions.forEach((option) => {
  option.addEventListener("click", (e) => {
    const orgType = e.currentTarget.getAttribute("data-org");
    orgOptions.forEach((o) => o.classList.remove("active"));
    e.currentTarget.classList.add("active");
    orgMenu.hidden = true;
    orgSelector.classList.remove("open");
    if (orgType !== "BUSINESS") {
      setLoginStatus("warn", "Planned workspace", "This selector is visual only until the backend exposes this tenant context.");
    }
    updateTrustedContextUi();
  });
});

/**
 * FY Selector Dropdown Toggle
 */
const fyTrigger = document.getElementById("fy-trigger");
const fyMenu = document.getElementById("fy-menu");
const fyOptions = document.querySelectorAll(".fy-option");

if (fyTrigger) {
  fyTrigger.addEventListener("click", () => {
    const isOpen = !fyMenu.hidden;
    fyMenu.hidden = isOpen;
  });
}

// Close FY dropdown when option is selected
fyOptions.forEach((option) => {
  option.addEventListener("click", (e) => {
    const fy = e.currentTarget.getAttribute("data-fy");
    fyOptions.forEach((o) => o.classList.remove("active"));
    e.currentTarget.classList.add("active");
    fyMenu.hidden = true;
    document.getElementById("current-fy").textContent = `FY ${fy}`;
  });
});

/**
 * Close dropdowns when clicking outside
 */
document.addEventListener("click", (e) => {
  // Close org dropdown if click is outside
  if (orgMenu && orgSelector && !orgSelector.contains(e.target)) {
    orgMenu.hidden = true;
    orgSelector.classList.remove("open");
  }
  // Close FY dropdown if click is outside
  if (fyMenu && fyTrigger && !fyTrigger.closest(".fy-selector").contains(e.target)) {
    fyMenu.hidden = true;
  }
});

// ============================================
// HEADER & HEALTH WIDGET (Phase 1C Step 7)
// ============================================

/**
 * Update health widget with data
 * @param {number} percentage - Health percentage (0-100)
 * @param {string} status - Status message
 */
function updateHealthWidget(percentage = null, status = "Run checks", tone = "pending") {
  const widget = document.getElementById("books-health-widget");
  const healthPercent = document.getElementById("health-percent-text");
  const healthBar = document.getElementById("health-circle-bar");
  const healthStatus = document.querySelector(".health-text span");
  const safePercentage = Number.isFinite(Number(percentage))
    ? Math.max(0, Math.min(100, Number(percentage)))
    : null;

  if (widget) {
    widget.classList.remove("pending", "warn", "ok");
    widget.classList.add(tone);
  }
  if (healthPercent) {
    healthPercent.textContent = safePercentage === null ? "--" : `${safePercentage}%`;
  }
  if (healthBar) {
    const dasharray = `${safePercentage ?? 0}, 100`;
    healthBar.setAttribute("stroke-dasharray", dasharray);
  }
  if (healthStatus) {
    healthStatus.textContent = status;
  }
}

function refreshBooksHealthWidget() {
  if (!lastModuleContext) {
    updateHealthWidget(null, "Run checks", "pending");
    return;
  }

  const { healthState } = getBusinessHealthState();
  const checks = [
    healthState.isBusinessTenant,
    healthState.hasBusinessModule,
    healthState.hasAccountingModule,
    healthState.accountsLoaded,
    healthState.hasCashBank,
    healthState.hasRevenue,
    healthState.hasExpense,
    healthState.partiesGstinReady,
    healthState.drilldownReady,
  ];
  const passed = checks.filter(Boolean).length;
  const percentage = Math.round((passed / checks.length) * 100);
  const ready = passed === checks.length;
  const blocked = healthState.accountsBlocked || healthState.partiesBlocked;
  updateHealthWidget(
    percentage,
    ready ? "Ready" : blocked ? "Needs review" : "In progress",
    ready ? "ok" : "warn"
  );
}

/**
 * Quick Action Buttons
 */
const btnQuickParty = document.getElementById("btn-quick-party");
const btnQuickJournal = document.getElementById("btn-quick-post-journal");

if (btnQuickParty) {
  btnQuickParty.addEventListener("click", () => {
    activeBusinessWorkspace = "parties";
    syncBusinessNavActiveState();
    dashboardPreview.innerHTML = renderBusinessWorkspace();
    openBusinessCreatePartyDialog();
  });
}

if (btnQuickJournal) {
  btnQuickJournal.addEventListener("click", async () => {
    activeBusinessWorkspace = "vouchers";
    syncBusinessNavActiveState();
    dashboardPreview.innerHTML = renderBusinessWorkspace();
    await openBusinessCreateVoucherDialog();
  });
}

/**
 * Update page title and breadcrumb based on current view
 * @param {string} parentName - Parent breadcrumb name
 * @param {string} currentName - Current breadcrumb name
 * @param {string} pageTitle - Full page title
 */
function updatePageHeader(parentName = "Workspaces", currentName = "Dashboard", pageTitle = "Dashboard Workspace") {
  const breadcrumbParent = document.getElementById("breadcrumb-parent");
  const breadcrumbCurrent = document.getElementById("breadcrumb-current");
  const viewTitle = document.getElementById("view-title");

  if (breadcrumbParent) breadcrumbParent.textContent = parentName;
  if (breadcrumbCurrent) breadcrumbCurrent.textContent = currentName;
  if (viewTitle) viewTitle.textContent = pageTitle;
}

/**
 * Initialize health widget on page load
 */
function initializeHealthWidget() {
  refreshBooksHealthWidget();
}

/**
 * Initialize header on page load
 */
function initializeHeader() {
  updatePageHeader("Workspaces", "Dashboard", "Dashboard Workspace");
  initializeHealthWidget();
}

// Call on app initialization
initializeHeader();

if (isProductionShell()) {
  const configuredApiBase = getConfiguredApiBaseUrl();
  const currentOrigin = String(window.location.origin || "").replace(/\/+$/, "");
  const pointsAtFrontend = configuredApiBase === currentOrigin
    || /mitrabooks-erp\.vercel\.app|mandirmitra\.sanmitratech\.in|gruhamitra\.sanmitratech\.in/i.test(configuredApiBase);
  if (!configuredApiBase || pointsAtFrontend) {
    setConfiguredApiBaseUrl(DEFAULT_DEPLOYED_API_BASE_URL);
  }
}
apiBaseInput.value = getConfiguredApiBaseUrl();
tokenInput.value = getAccessToken();
document.querySelectorAll(".module-switch button").forEach((button) => button.classList.remove("active"));
document.getElementById(`mode-${currentExperience}`)?.classList.add("active");
updateSessionUi();
renderModules();

renderModuleState(moduleState);
runChecks();
