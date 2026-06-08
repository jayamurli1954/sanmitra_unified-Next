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
        { label: "Sales", businessWorkspace: "sales", icon: "SL", module: { module_key: "sales", frontend_path: "/business/sales", enabled: true } },
        { label: "Credit Notes", businessWorkspace: "credit-notes", icon: "CN", module: { module_key: "sales", frontend_path: "/business/credit-notes", enabled: true } },
      ],
    },
    {
      name: "Expenses (Purchases)",
      items: [
        { label: "Bills (Vendor)", businessWorkspace: "bills", icon: "BL", module: { module_key: "purchase", frontend_path: "/business/bills", enabled: true } },
        { label: "Purchase Orders", businessWorkspace: "purchase-orders", icon: "PO", module: { module_key: "purchase", frontend_path: "/business/purchase-orders", enabled: false } },
        { label: "Debit Notes", businessWorkspace: "debit-notes", icon: "DN", module: { module_key: "purchase", frontend_path: "/business/debit-notes", enabled: true } },
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
        { label: "Financial Statements", businessWorkspace: "reports", icon: "FS", module: { module_key: "accounting", frontend_path: "/accounting/reports", enabled: true } },
        { label: "Financial Health", businessWorkspace: "financial-health", icon: "FH", module: { module_key: "analytics", frontend_path: "/business/financial-health", enabled: true }, badge: "Preview" },
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

// ============================================
// DASHBOARD WIDGET STATE MANAGEMENT (Phase 2C.2-2C.3)
// ============================================

const WIDGET_STATES_STORAGE_KEY = "mitrabooks-widget-states";
const DEFAULT_WIDGET_STATES = {
  "kpi-strip": { visible: true, collapsed: false, order: 1 },
  "finance-chart": { visible: true, collapsed: false, order: 2 },
  "ceo-panel": { visible: true, collapsed: false, order: 3 }
};

/**
 * Get all widget states from localStorage
 */
function getWidgetStates() {
  try {
    const saved = localStorage.getItem(WIDGET_STATES_STORAGE_KEY);
    return saved ? JSON.parse(saved) : JSON.parse(JSON.stringify(DEFAULT_WIDGET_STATES));
  } catch (e) {
    console.warn("Failed to parse widget states, using defaults", e);
    return JSON.parse(JSON.stringify(DEFAULT_WIDGET_STATES));
  }
}

/**
 * Save widget states to localStorage
 */
function saveWidgetStates(states) {
  try {
    localStorage.setItem(WIDGET_STATES_STORAGE_KEY, JSON.stringify(states));
  } catch (e) {
    console.warn("Failed to save widget states", e);
  }
}

/**
 * Get state of a specific widget
 */
function getWidgetState(widgetId) {
  const states = getWidgetStates();
  return states[widgetId] || { visible: true, collapsed: false };
}

/**
 * Toggle collapse state of a widget
 */
function toggleWidgetCollapse(widgetId) {
  const states = getWidgetStates();
  if (states[widgetId]) {
    states[widgetId].collapsed = !states[widgetId].collapsed;
    saveWidgetStates(states);
    applyWidgetCollapse(widgetId, states[widgetId].collapsed);
  }
}

/**
 * Toggle visibility of a widget and re-render the settings panel + dashboard
 */
function toggleWidgetVisibility(widgetId) {
  const states = getWidgetStates();
  if (states[widgetId]) {
    states[widgetId].visible = !states[widgetId].visible;
    saveWidgetStates(states);
    // Refresh the settings panel checkboxes in-place
    const panel = document.getElementById("widget-settings-panel");
    if (panel) {
      const checkbox = panel.querySelector(`input[data-widget-id="${widgetId}"]`);
      if (checkbox) checkbox.checked = states[widgetId].visible;
    }
    // Re-render dashboard widgets in place
    if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "overview") {
      const execDash = document.querySelector(".executive-dashboard");
      if (execDash) {
        const tmp = document.createElement("div");
        tmp.innerHTML = renderBusinessExecutiveDashboard();
        execDash.replaceWith(tmp.firstElementChild);
      }
    }
  }
}

/**
 * Reset all widgets to default state
 */
function resetWidgetStates() {
  saveWidgetStates(JSON.parse(JSON.stringify(DEFAULT_WIDGET_STATES)));
  closeWidgetSettings();
  if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "overview") {
    const execDash = document.querySelector(".executive-dashboard");
    if (execDash) {
      const tmp = document.createElement("div");
      tmp.innerHTML = renderBusinessExecutiveDashboard();
      execDash.replaceWith(tmp.firstElementChild);
    }
  }
}

/**
 * Open the widget customization settings panel
 */
function openWidgetSettings() {
  const existing = document.getElementById("widget-settings-overlay");
  if (existing) { existing.remove(); return; }

  const overlay = document.createElement("div");
  overlay.id = "widget-settings-overlay";
  overlay.className = "widget-settings-overlay";
  overlay.setAttribute("role", "dialog");
  overlay.setAttribute("aria-modal", "true");
  overlay.setAttribute("aria-label", "Dashboard widget settings");

  overlay.innerHTML = renderWidgetSettingsPanel();
  document.body.appendChild(overlay);

  // Close on click outside the panel
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) { closeWidgetSettings(); return; }
    const btn = e.target.closest("[data-widget-action]");
    if (!btn) return;
    const action = btn.getAttribute("data-widget-action");
    if (action === "close-settings") closeWidgetSettings();
    else if (action === "reset-widgets") resetWidgetStates();
  });

  // Toggle visibility on checkbox change
  overlay.addEventListener("change", (e) => {
    const input = e.target.closest("input[data-widget-action='toggle-visibility']");
    if (input) toggleWidgetVisibility(input.getAttribute("data-widget-id") || "");
  });

  // Close on Escape key
  const onKey = (e) => {
    if (e.key === "Escape") { closeWidgetSettings(); document.removeEventListener("keydown", onKey); }
  };
  document.addEventListener("keydown", onKey);

  const firstFocus = overlay.querySelector("button, input");
  if (firstFocus) firstFocus.focus();
}

/**
 * Close the widget settings panel
 */
function closeWidgetSettings() {
  const overlay = document.getElementById("widget-settings-overlay");
  if (overlay) overlay.remove();
}

/**
 * Render the widget settings panel HTML
 */
function renderWidgetSettingsPanel() {
  const states = getWidgetStates();
  const widgetLabels = {
    "kpi-strip":     "Key Performance Indicators",
    "finance-chart": "Sales & Expenses Trend",
    "ceo-panel":     "CEO Insights"
  };

  const rows = Object.entries(widgetLabels).map(([id, label]) => {
    const visible = states[id]?.visible !== false;
    return `
      <label class="widget-settings-row">
        <span class="widget-settings-label">${escapeHtml(label)}</span>
        <input
          type="checkbox"
          class="widget-settings-toggle"
          data-widget-action="toggle-visibility"
          data-widget-id="${id}"
          ${visible ? "checked" : ""}
          aria-label="Show ${escapeHtml(label)}"
        >
        <span class="widget-settings-switch" aria-hidden="true"></span>
      </label>
    `;
  }).join("");

  return `
    <div id="widget-settings-panel" class="widget-settings-panel">
      <div class="widget-settings-header">
        <h4>Dashboard Widgets</h4>
        <button class="widget-settings-close" data-widget-action="close-settings" aria-label="Close settings">✕</button>
      </div>
      <p class="widget-settings-hint">Toggle which widgets appear on your executive dashboard.</p>
      <div class="widget-settings-list">
        ${rows}
      </div>
      <div class="widget-settings-footer">
        <button class="secondary" type="button" data-widget-action="reset-widgets">Reset to Defaults</button>
      </div>
    </div>
  `;
}

/**
 * Apply collapse/expand animation to widget
 */
function applyWidgetCollapse(widgetId, isCollapsed) {
  const widget = document.getElementById(`widget-${widgetId}`);
  const btn = document.getElementById(`collapse-btn-${widgetId}`);

  if (widget) {
    widget.classList.toggle("collapsed", isCollapsed);
  }
  if (btn) {
    btn.textContent = isCollapsed ? "⌄" : "⌃";
    btn.setAttribute("aria-label", isCollapsed ? "Expand widget" : "Collapse widget");
  }
}

/**
 * Create widget wrapper HTML with header controls
 */
function createWidgetWrapper(widgetId, title, content, showControls = true) {
  const state = getWidgetState(widgetId);
  const isCollapsed = state.collapsed;
  const isVisible = state.visible !== false;

  if (!isVisible) {
    return ""; // Don't render hidden widgets
  }

  const collapseBtnHtml = showControls ? `
    <button
      id="collapse-btn-${widgetId}"
      class="widget-collapse-btn"
      data-business-action="widget-collapse"
      data-widget-id="${widgetId}"
      aria-label="${isCollapsed ? 'Expand widget' : 'Collapse widget'}"
      title="${isCollapsed ? 'Expand' : 'Collapse'}"
    >
      ${isCollapsed ? "⌄" : "⌃"}
    </button>
  ` : "";

  return `
    <div id="widget-${widgetId}" class="dashboard-widget ${isCollapsed ? 'collapsed' : ''}" data-widget-id="${widgetId}">
      <div class="widget-header">
        <h4>${escapeHtml(title)}</h4>
        ${showControls ? `<div class="widget-header-controls">${collapseBtnHtml}</div>` : ""}
      </div>
      <div class="widget-content">
        ${content}
      </div>
    </div>
  `;
}

const APP_KEY = "mitrabooks";
const DEFAULT_DEPLOYED_API_BASE_URL = "https://sanmitra-unified-next-staging-sg.onrender.com";
const DEFAULT_MITRABOOKS_LOGIN_EMAIL = "business.admin@sanmitra.local";
const LOGIN_EMAIL_STORAGE_KEY = "sanmitra_mitrabooks_login_email";
const LOGIN_REQUEST_TIMEOUT_MS = 20000;
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

const orgSelectorMeta = {
  BUSINESS: {
    label: "Business Suite",
    subtitle: "SME and accounting",
    statusTitle: "Business workspace active",
    statusCopy: "Using the signed-in business tenant context.",
  },
  PROFESSIONAL: {
    label: "Professional Suite",
    subtitle: "Billing and invoicing",
    statusTitle: "Professional workspace planned",
    statusCopy: "This selector is ready in the shell; backend tenant context and modules are not enabled yet.",
  },
  CA_PRACTICE: {
    label: "CA Practice Portal",
    subtitle: "Planned multi-client books",
    statusTitle: "CA Practice Portal planned",
    statusCopy: "Multi-client books will be enabled after the backend exposes the CA practice tenant context.",
  },
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
let selectedOrgType = null;
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
let lastBusinessParties = [];
let lastBusinessAccounts = [];
let lastCaDocuments = [];
let lastCaDocumentsResult = null;
const CA_DOCUMENT_WORKFLOW = ["uploaded", "under_review", "query_raised", "reviewed", "posted"];
const CA_DOCUMENT_LABELS = {
  uploaded: "Uploaded",
  under_review: "Under review",
  query_raised: "Query raised",
  reviewed: "Reviewed",
  posted: "Posted",
};

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
const topbarControlStrip = document.querySelector(".topbar-control-strip");
const accountMenuTrigger = document.getElementById("account-menu-trigger");
const accountMenuPanel = document.getElementById("account-menu-panel");
const passwordDialog = document.getElementById("change-password-dialog");
const passwordForm = document.getElementById("change-password-form");
const passwordStatus = document.getElementById("password-error-message");
const currentPasswordInput = document.getElementById("current-password");
const newPasswordInput = document.getElementById("new-password");
const confirmNewPasswordInput = document.getElementById("confirm-password");

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
  if (topbarControlStrip) {
    topbarControlStrip.hidden = currentExperience !== "mitrabooks";
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
  console.log("[Nav] loadAndRenderGroupedNav called with appKey:", appKey);

  if (appKey === "mitrabooks") {
    console.log("[Nav] Using hardcoded MitraBooks navigation");
    const groups = businessNavigationGroups();
    console.log("[Nav] businessNavigationGroups returned", groups.length, "groups");
    console.log("[Nav] Groups:", groups.map(g => g.name));
    renderGroupedNav(groups);
    console.log("[Nav] renderGroupedNav completed");
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
  console.log("[Nav] renderGroupedNav called with", groups.length, "groups");
  const nav = document.getElementById("nav");
  if (!nav) {
    console.error("[Nav] ERROR: nav element not found in DOM!");
    return;
  }

  console.log("[Nav] Found nav element, clearing and populating...");
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

function renderBusinessRecentVoucherRows(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `
      <div class="empty-state compact">
        <strong>No posted vouchers yet</strong>
        <span>Post the first balanced journal to start the operational timeline.</span>
      </div>
    `;
  }
  return `
    <div class="table-preview compact-table erp-table business-recent-table">
      <table>
        <thead>
          <tr>
            <th>Reference</th>
            <th>Date</th>
            <th>Type</th>
            <th>Amount</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          ${rows.slice(0, 5).map((row) => {
            const status = String(row.status || "posted");
            const isReversed = status === "reversed";
            return `
              <tr>
                <td>
                  <strong>${escapeHtml(row.reference || row.cheque_number || "-")}</strong>
                  <span class="row-subtext">${escapeHtml((row.description || row.narration || "").slice(0, 42))}</span>
                </td>
                <td>${escapeHtml(String(row.entry_date || row.created_at || "").slice(0, 10))}</td>
                <td>${escapeHtml(row.voucher_type || "journal")}</td>
                <td class="amount">${escapeHtml(formatCurrency(row.total_debit || row.amount || 0))}</td>
                <td><span class="pill ${isReversed ? "warn" : "ok"}">${escapeHtml(status)}</span></td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function caDocumentStatusLabel(status) {
  return CA_DOCUMENT_LABELS[status] || String(status || "Uploaded");
}

function nextCaDocumentStatus(status) {
  const index = CA_DOCUMENT_WORKFLOW.indexOf(status || "uploaded");
  if (index < 0 || index >= CA_DOCUMENT_WORKFLOW.length - 1) {
    return "";
  }
  return CA_DOCUMENT_WORKFLOW[index + 1];
}

function caDocumentMetrics(rows) {
  const counts = CA_DOCUMENT_WORKFLOW.reduce((acc, status) => {
    acc[status] = 0;
    return acc;
  }, {});
  (Array.isArray(rows) ? rows : []).forEach((row) => {
    const status = row.status || "uploaded";
    counts[status] = (counts[status] || 0) + 1;
  });
  return [
    ["Uploaded", String(counts.uploaded || 0), "Awaiting classification"],
    ["Under review", String(counts.under_review || 0), "Staff review in progress"],
    ["Reviewed", String(counts.reviewed || 0), "Ready for posting"],
    ["Posted", String(counts.posted || 0), "Linked to vouchers or returns"],
    ["Query raised", String(counts.query_raised || 0), "Needs client clarification"],
  ];
}

function renderCaDocumentTable(rows) {
  if (!lastCaDocumentsResult) {
    return `
      <div class="empty-state">
        <strong>Loading document metadata</strong>
        <span>Tenant-scoped CA practice records will appear here.</span>
      </div>
    `;
  }
  if (!Array.isArray(rows) || rows.length === 0) {
    return `
      <div class="empty-state">
        <strong>No CA document metadata yet</strong>
        <span>Add a client document record. File storage is intentionally deferred.</span>
      </div>
    `;
  }
  return `
    <div class="table-preview compact-table erp-table ca-document-status-table">
      <table>
        <thead>
          <tr>
            <th>Client</th>
            <th>Document type</th>
            <th>Period</th>
            <th>Status</th>
            <th>Next action</th>
            <th>Posting ref</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((row) => {
            const nextStatus = nextCaDocumentStatus(row.status);
            return `
              <tr>
                <td>
                  <strong>${escapeHtml(row.client_name || "-")}</strong>
                  <span class="row-subtext">${escapeHtml(row.original_file_name || "metadata only")}</span>
                </td>
                <td>${escapeHtml(row.document_type || "-")}</td>
                <td>${escapeHtml(row.period || "-")}</td>
                <td><span class="pill">${escapeHtml(caDocumentStatusLabel(row.status))}</span></td>
                <td>${escapeHtml(row.next_action || "-")}</td>
                <td>${escapeHtml(row.posting_reference || "-")}</td>
                <td>
                  ${nextStatus ? `
                    <button
                      class="secondary"
                      type="button"
                      data-business-action="ca-doc-status"
                      data-document-id="${escapeHtml(row.document_id || "")}"
                      data-status="${escapeHtml(nextStatus)}"
                    >${escapeHtml(caDocumentStatusLabel(nextStatus))}</button>
                  ` : `<button class="secondary" type="button" disabled>Posted</button>`}
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderCaDocumentIntake(documentIntake) {
  const metrics = caDocumentMetrics(lastCaDocuments);
  return `
    <div class="ca-document-intake">
      <div class="ca-document-upload-card">
        <form data-ca-document-form>
          <span class="workbench-kicker">Document Metadata</span>
          <h4>${escapeHtml(documentIntake.title)}</h4>
          <p>${escapeHtml(documentIntake.copy)}</p>
          <div class="ca-upload-field-grid">
            <label>
              <span>Client</span>
              <input name="client_name" type="text" maxlength="160" placeholder="Client book or company name" required>
            </label>
            <label>
              <span>Document type</span>
              <select name="document_type" required>
                <option value="">Select type</option>
                <option>Bank statement</option>
                <option>Purchase bills</option>
                <option>Sales invoices</option>
                <option>GST return</option>
                <option>TDS file</option>
                <option>Supporting document</option>
              </select>
            </label>
            <label>
              <span>Period</span>
              <input name="period" type="text" maxlength="80" placeholder="May 2026 / FY 2026-27" required>
            </label>
            <label>
              <span>Assigned to</span>
              <input name="assigned_to" type="text" maxlength="120" placeholder="Reviewer or partner">
            </label>
            <label>
              <span>Original file name</span>
              <input name="original_file_name" type="text" maxlength="240" placeholder="metadata only, no upload yet">
            </label>
            <label>
              <span>Notes</span>
              <input name="notes" type="text" maxlength="500" placeholder="Review notes or client instruction">
            </label>
          </div>
          <div class="ca-document-actions">
            <button type="submit">Add Document Metadata</button>
            <button class="secondary" type="button" data-business-action="ca-doc-refresh">Refresh</button>
          </div>
        </form>
        <label class="ca-upload-placeholder" aria-disabled="true">
          <span>Upload placeholder</span>
          <strong>File storage deferred</strong>
          <small>Only document metadata is saved in this phase.</small>
          <input type="file" multiple disabled>
        </label>
      </div>

      <div class="ca-document-workflow" aria-label="Document review workflow">
        ${CA_DOCUMENT_WORKFLOW.map((status, index) => `
          <span class="${index === 0 ? "active" : ""}">${escapeHtml(caDocumentStatusLabel(status))}</span>
        `).join("")}
      </div>

      <div class="ca-document-status-grid">
        ${metrics.map(([label, value, copy]) => `
          <article>
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(value)}</strong>
            <small>${escapeHtml(copy)}</small>
          </article>
        `).join("")}
      </div>

      ${renderCaDocumentTable(lastCaDocuments)}

      <div class="ca-document-note">
        Current state: metadata records are tenant-scoped and stored through the MitraBooks business API. Deferred scope: file storage, OCR, voucher posting, and return filing links are not enabled yet.
      </div>
    </div>
  `;
}

function plannedOrgWorkspaceModel(orgType) {
  if (orgType === "CA_PRACTICE") {
    return {
      label: "CA Practice Portal",
      eyebrow: "Planned multi-client books",
      lead: "Practice-level workspace for client books, compliance reviews, and consolidated reporting. This shell is visible now; backend tenant switching is still planned.",
      kpis: [
        ["Client Books", "Planned", "Multi-client ledger access"],
        ["Review Queue", "Planned", "Voucher and return review workflow"],
        ["Compliance", "Planned", "GST, TDS, and filing calendar"],
      ],
      modules: [
        ["Client ledger access", "Open each client book with tenant-safe context before showing accounting data.", "Planned"],
        ["GST and TDS workbench", "Track return status, due dates, reconciliation, and filing readiness.", "Planned"],
        ["Review queue", "Route vouchers, invoices, and adjustments for partner review before final posting.", "Planned"],
        ["Consolidated reports", "Practice-wide receivables, workload, client health, and team productivity.", "Planned"],
      ],
      documentIntake: {
        title: "Client document intake",
        copy: "Placeholder for uploading client bank statements, purchase bills, sales invoices, GST returns, TDS files, and supporting documents before review and posting.",
        uploadFields: [
          ["Client", "Select client book"],
          ["Document type", "Bank statement, invoice, GST, TDS"],
          ["Period", "FY 2026-27 / month"],
          ["Assigned to", "Reviewer or partner"],
        ],
        workflow: ["Uploaded", "Under review", "Query raised", "Reviewed", "Posted"],
        metrics: [
          ["Uploaded", "18", "Awaiting classification"],
          ["Under review", "7", "Staff review in progress"],
          ["Reviewed", "5", "Ready for posting"],
          ["Posted", "9", "Linked to vouchers"],
          ["Query raised", "4", "Needs client clarification"],
        ],
        rows: [
          ["Jayam Publications", "Bank statement", "May 2026", "Under review", "Reconciliation check", "-"],
          ["Kartik Enterprises", "Purchase bills", "May 2026", "Posted", "Voucher batch ready", "JV-2026-00012"],
          ["Power & Light Corp", "GST working", "Q1 2026", "Query raised", "Missing invoice support", "-"],
          ["Stellar Logistics", "Sales invoices", "May 2026", "Reviewed", "Ready for posting", "-"],
        ],
      },
      note: "No accounting data is posted from this planned workspace until the backend exposes CA practice module access.",
    };
  }

  return {
    label: "Professional Suite",
    eyebrow: "Planned billing and invoicing",
    lead: "Service-business workspace for billing, receipts, professional client accounts, and revenue tracking. This shell is visible now; backend modules are not enabled yet.",
    kpis: [
      ["Billing", "Planned", "Service invoices and retainers"],
      ["Receivables", "Planned", "Client dues and follow-ups"],
      ["Reports", "Planned", "Practice performance summaries"],
    ],
    modules: [
      ["Client billing", "Create professional service invoices with GST and accounting posting.", "Planned"],
      ["Retainers and advances", "Track advance receipts separately from final service revenue recognition.", "Planned"],
      ["Receivables follow-up", "Age client balances and route overdue reminders.", "Planned"],
      ["Professional reports", "Monthly revenue, collections, margins, and client-wise performance.", "Planned"],
    ],
    note: "No backend tenant context has changed; this is a planned workspace preview inside the MitraBooks shell.",
  };
}

function renderSelectedOrgWorkspace() {
  const orgType = activeOrgSelectorType();
  const model = plannedOrgWorkspaceModel(orgType);
  return `
    <div class="planned-org-workspace erp-workspace-panel">
      <div class="planned-org-hero">
        <div>
          <span class="workbench-kicker">${escapeHtml(model.eyebrow)}</span>
          <h3>${escapeHtml(model.label)} Workspace</h3>
          <p>${escapeHtml(model.lead)}</p>
        </div>
        <span class="pill warn">Planned</span>
      </div>

      <div class="planned-org-kpis">
        ${model.kpis.map(([title, value, copy]) => `
          <article>
            <span>${escapeHtml(title)}</span>
            <strong>${escapeHtml(value)}</strong>
            <small>${escapeHtml(copy)}</small>
          </article>
        `).join("")}
      </div>

      <div class="planned-org-module-grid">
        ${model.modules.map(([title, copy, status]) => `
          <article>
            <div>
              <h4>${escapeHtml(title)}</h4>
              <span class="pill">${escapeHtml(status)}</span>
            </div>
            <p>${escapeHtml(copy)}</p>
          </article>
        `).join("")}
      </div>

      ${model.documentIntake ? `
        ${renderCaDocumentIntake(model.documentIntake)}
      ` : ""}

      <div class="planned-org-note">
        <strong>Implementation status</strong>
        <span>${escapeHtml(model.note)}</span>
      </div>
    </div>
  `;
}

function renderBusinessExecutiveDashboard() {
  const voucherCount = lastAccountingDrilldown?.summary?.voucher_count ?? 0;
  const partyCount = Array.isArray(lastBusinessParties) ? lastBusinessParties.length : 0;
  const accountCount = Array.isArray(lastBusinessAccounts) ? lastBusinessAccounts.length : 0;

  // Use live dashboard data if available, otherwise use defaults
  const dashboardData = lastBusinessDashboardStats || {};

  // Extract KPI values (in Rupees, not Lakhs)
  const incomeVal = Number(dashboardData.income?.current_month || 1280000);
  const expenseVal = Number(dashboardData.expenses?.current_month || 740000);
  const netVal = Number(dashboardData.net_position?.profit_loss || 540000);
  const incomeGrowth = Number(dashboardData.income?.ytd_growth || 18);

  // Format values for display (convert to Lakhs if needed)
  const incomeDisplay = formatCurrency(incomeVal);
  const expenseDisplay = formatCurrency(expenseVal);
  const netDisplay = formatCurrency(netVal);

  // Chart data - use from API if available, else defaults
  const months = dashboardData.monthly_trend || [
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

  // Widget 1: KPI Strip (Phase 2C.2-C.3: Collapsible & Customizable)
  const kpiStripContent = `
    <div class="executive-hero kpi-widget-hero">
      <div class="executive-kpi-strip">
        <article>
          <span>Income</span>
          <strong>${escapeHtml(incomeDisplay)}</strong>
          <small>${incomeGrowth > 0 ? "+" : ""}${incomeGrowth.toFixed(1)}% vs last month</small>
        </article>
        <article>
          <span>Expenses</span>
          <strong>${escapeHtml(expenseDisplay)}</strong>
          <small>Office, purchases, vendor bills</small>
        </article>
        <article>
          <span>Net Position</span>
          <strong>${escapeHtml(netDisplay)}</strong>
          <small>Before tax provisions</small>
        </article>
      </div>
    </div>
  `;

  // Widget 2: Finance Chart (Phase 2C.2-C.3: Collapsible & Customizable)
  const financeChartContent = `
    <div class="preview-heading compact">
      <div>
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
  `;

  // Widget 3: CEO Panel (Phase 2C.2-C.3: Collapsible & Customizable)
  const ceoPanelContent = `
    <div class="preview-heading compact">
      <div class="ceo-title-block">
        <span class="ceo-orbit" aria-hidden="true"></span>
        <span class="ai-badge">AI Enabled</span>
        <p>Real-time ledger analytics and operating summaries.</p>
      </div>
    </div>
    <div class="ceo-insight-list" role="list">
      <div class="ceo-insight-row" role="listitem">
        <span class="insight-spark" aria-hidden="true"></span>
        <div class="ceo-insight-copy">
          <strong>65.1x coverage</strong>
          <span>Cash flow is covering pending vendor obligations comfortably.</span>
        </div>
      </div>
      <div class="ceo-insight-row" role="listitem">
        <span class="insight-spark" aria-hidden="true"></span>
        <div class="ceo-insight-copy">
          <strong>28 days</strong>
          <span>Receivables collection time has tightened and liquidity has improved.</span>
        </div>
      </div>
      <div class="ceo-insight-row" role="listitem">
        <span class="insight-spark" aria-hidden="true"></span>
        <div class="ceo-insight-copy">
          <strong>4.2x</strong>
          <span>Consumables inventory is turning at a healthy operating cadence.</span>
        </div>
      </div>
    </div>
    <div class="ceo-ask-row">
      <input type="text" value="" placeholder="Ask AI: 'What is our GST exposure?' or 'Rent balance?'" aria-label="Ask AI for ledger insight">
      <button type="button">Ask</button>
    </div>
    <p class="ceo-footnote">${voucherCount} posted voucher(s), ${partyCount} party record(s), and ${accountCount} account(s) are available for the current dashboard context.</p>
  `;

  // Build dashboard with wrapped widgets (Phase 2C.2-C.3)
  const kpiWidget = createWidgetWrapper("kpi-strip", "Key Performance Indicators", kpiStripContent, true);
  const chartWidget = createWidgetWrapper("finance-chart", "Sales & Expenses Trend", financeChartContent, true);
  const ceoWidget = createWidgetWrapper("ceo-panel", "CEO Insights", ceoPanelContent, true);

  return `
    <section class="executive-dashboard" aria-label="MitraBooks executive dashboard">
      <div class="dashboard-toolbar">
        <button
          class="dashboard-customize-btn"
          type="button"
          data-business-action="open-widget-settings"
          aria-label="Customize dashboard widgets"
          title="Customize widgets"
        >⚙ Customize</button>
      </div>
      ${kpiWidget}
      <div class="finance-dashboard-grid-wrapper">
        ${chartWidget}
        ${ceoWidget}
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
    <div class="table-preview compact-table erp-table">
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
    <div class="table-preview compact-table erp-table">
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
    topbarUser.textContent = compactAccountLabel(savedEmail || "Signed in");
    topbarUser.title = savedEmail || "Signed in";
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

  // Update user credentials display in topbar
  const emailDisplay = document.getElementById("topbar-email-display");
  const menuEmailDisplay = document.getElementById("menu-email-display");
  const menuTenantDisplay = document.getElementById("menu-tenant-display");
  if (emailDisplay) {
    emailDisplay.textContent = savedEmail || "Not signed in";
  }
  if (menuEmailDisplay) {
    menuEmailDisplay.textContent = savedEmail || "Not signed in";
  }
  if (menuTenantDisplay && lastModuleContext?.tenant_id) {
    menuTenantDisplay.textContent = lastModuleContext.tenant_id;
  }

  document.getElementById("topbar-actions")?.toggleAttribute("hidden", !signedIn);
  document.getElementById("sidebar-logout")?.toggleAttribute("hidden", !signedIn);
  if (loginEmail && !loginEmail.value) {
    loginEmail.value = savedEmail || DEFAULT_MITRABOOKS_LOGIN_EMAIL;
  }
  if (tokenInput) {
    tokenInput.value = getAccessToken();
  }
  const publicLink = document.getElementById("mandir-public-link");
  if (publicLink) {
    publicLink.href = mandirPublicPaymentPageUrl();
  }
}

function compactAccountLabel(email) {
  const value = String(email || "").trim();
  if (!value.includes("@")) {
    return value || "Account";
  }
  const [name, domain] = value.split("@");
  const shortName = name.length > 12 ? `${name.slice(0, 10)}...` : name;
  const shortDomain = String(domain || "").split(".")[0] || domain;
  return `${shortName}@${shortDomain}`;
}

function signOutAndReturnToLogin() {
  clearAccessToken();
  lastModuleContext = null;
  lastBusinessAccounts = [];
  lastBusinessParties = [];
  lastBusinessVouchers = [];
  lastAccountingDrilldown = null;
  if (tokenInput) {
    tokenInput.value = "";
  }
  if (loginPassword) {
    loginPassword.value = "";
  }
  setLoginStatus("", "", "");
  dashboardPreview.innerHTML = "";
  renderJson(apiOutput, {});
  renderModuleState(moduleState);
  currentExperience = initialExperience();
  document.querySelectorAll(".module-switch button").forEach((button) => button.classList.remove("active"));
  document.getElementById(`mode-${currentExperience}`)?.classList.add("active");
  renderModules();
  updateSessionUi();
}

function closeAccountMenu() {
  if (accountMenuPanel) {
    accountMenuPanel.hidden = true;
  }
  accountMenuTrigger?.setAttribute("aria-expanded", "false");
}

function openPasswordDialog() {
  closeAccountMenu();
  passwordForm?.reset();
  if (passwordStatus) {
    passwordStatus.className = "module-state";
    passwordStatus.textContent = "";
  }
  passwordDialog?.showModal();
}

async function updateCurrentPassword() {
  const currentPassword = String(currentPasswordInput?.value || "");
  const newPassword = String(newPasswordInput?.value || "");
  const confirmPassword = String(confirmNewPasswordInput?.value || "");
  const submitButton = document.getElementById("change-password-submit");

  if (!currentPassword || currentPassword.length < 6) {
    if (passwordStatus) {
      passwordStatus.className = "module-state danger";
      passwordStatus.innerHTML = "<strong>Current password required</strong><span>Enter the current account password first.</span>";
    }
    return;
  }
  if (!newPassword || newPassword.length < 6) {
    if (passwordStatus) {
      passwordStatus.className = "module-state danger";
      passwordStatus.innerHTML = "<strong>New password too short</strong><span>Use at least 6 characters.</span>";
    }
    return;
  }
  if (newPassword !== confirmPassword) {
    if (passwordStatus) {
      passwordStatus.className = "module-state danger";
      passwordStatus.innerHTML = "<strong>Passwords do not match</strong><span>Confirm the new password again.</span>";
    }
    return;
  }

  if (submitButton) {
    submitButton.disabled = true;
    submitButton.textContent = "Updating...";
  }
  const result = await apiRequest(APP_KEY, "/api/v1/auth/change-password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
  if (submitButton) {
    submitButton.disabled = false;
    submitButton.textContent = "Update Password";
  }

  if (result.ok) {
    passwordForm?.reset();
    if (passwordStatus) {
      passwordStatus.className = "module-state ok";
      passwordStatus.innerHTML = "<strong>Password updated</strong><span>Use the new password for your next sign-in.</span>";
    }
    setLoginStatus("ok", "Password updated", "Use the new password for your next sign-in.");
  } else if (passwordStatus) {
    passwordStatus.className = "module-state danger";
    passwordStatus.innerHTML = `<strong>Password update failed</strong><span>${escapeHtml(statusDetailText(result.payload?.detail) || statusDetailText(result.payload) || "Try again.")}</span>`;
  }
  renderJson(apiOutput, { change_password: { ok: result.ok, status: result.status, detail: result.payload?.detail } });
}

function activeOrgSelectorType(context = lastModuleContext) {
  const organizationType = String(context?.organization_type || "").toUpperCase();
  return selectedOrgType || organizationType || "BUSINESS";
}

function syncOrgSelectorOptions(orgType) {
  document.querySelectorAll(".org-option").forEach((option) => {
    option.classList.toggle("active", option.getAttribute("data-org") === orgType);
  });
}

function updateTrustedContextUi(context = lastModuleContext) {
  const organizationType = String(context?.organization_type || "").toUpperCase();
  const selectorOrgType = activeOrgSelectorType(context);
  const selectorMeta = orgSelectorMeta[selectorOrgType] || orgSelectorMeta.BUSINESS;
  const tenantLabel = context?.tenant_name || context?.organization_name || context?.tenant_id || "";
  const enabledCount = Array.isArray(context?.enabled_modules)
    ? context.enabled_modules.length
    : Array.isArray(context?.modules)
      ? context.modules.filter((module) => module.enabled !== false).length
      : 0;

  if (currentOrgType) {
    currentOrgType.textContent = selectorMeta.label;
  }
  if (currentOrgTenant) {
    currentOrgTenant.textContent = selectorOrgType === "BUSINESS"
      ? tenantLabel || selectorMeta.subtitle
      : selectorMeta.subtitle;
  }
  syncOrgSelectorOptions(selectorOrgType);
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
      timeoutMs: LOGIN_REQUEST_TIMEOUT_MS,
      body: JSON.stringify({ email, password }),
    });

    if (!result.ok) {
      clearAccessToken();
      updateSessionUi();
      const detail = statusDetailText(result.payload?.detail) ||
        statusDetailText(result.payload) ||
        "Unable to sign in with these credentials.";

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
    if (activeOrgSelectorType() !== "BUSINESS") {
      return renderSelectedOrgWorkspace();
    }
    return `
      <div class="business-dashboard-clean">
        ${renderBusinessExecutiveDashboard()}

        <div class="business-quick-actions-clean">
          <button class="quick-action-btn" type="button" data-business-action="open-create-voucher" title="Post a journal entry">
            <span class="quick-icon">📝</span>
            <span>Journal</span>
          </button>
          <button class="quick-action-btn" type="button" data-business-action="open-create-party" title="Add a new party">
            <span class="quick-icon">👤</span>
            <span>Party</span>
          </button>
          <button class="quick-action-btn" type="button" data-business-action="workspace-view" data-workspace-view="accounting" title="View trial balance">
            <span class="quick-icon">📊</span>
            <span>Trial Balance</span>
          </button>
          <button class="quick-action-btn" type="button" data-business-action="workspace-view" data-workspace-view="audit" title="View audit trail">
            <span class="quick-icon">📋</span>
            <span>Audit</span>
          </button>
        </div>

        <div class="business-bottom-metrics">
          <div class="metric-item">
            <span class="metric-label">Cash and Bank</span>
            <strong class="metric-value">Rs. 8.4L</strong>
            <small class="metric-sub">available balance</small>
          </div>
          <div class="metric-item">
            <span class="metric-label">Receivables</span>
            <strong class="metric-value">Rs. 2.1L</strong>
            <small class="metric-sub">open invoices</small>
          </div>
          <div class="metric-item">
            <span class="metric-label">Payables</span>
            <strong class="metric-value">Rs. 96K</strong>
            <small class="metric-sub">vendor dues</small>
          </div>
          <div class="metric-item">
            <span class="metric-label">GST Filing</span>
            <strong class="metric-value">Ready</strong>
            <small class="metric-sub">current period</small>
          </div>
        </div>

        <div class="business-recent-activity-clean">
          <h4>Recent Activity</h4>
          <ul class="activity-list">${renderActivity(dashboard.activity || [])}</ul>
        </div>
      </div>
    `;
}
}

// ========== Business Module: Party Master ==========

let activeBusinessWorkspace = "overview";
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
                      data-party-type="${escapeHtml(row.party_type || "customer")}"
                      data-party-gstin="${escapeHtml(row.gstin || "")}"
                      data-party-city="${escapeHtml(row.city || "")}"
                      data-party-state="${escapeHtml(row.state || "")}"
                      data-party-pincode="${escapeHtml(row.pincode || "")}"
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
  if (activeBusinessWorkspace === "reports") {
    return renderBusinessReportsWorkspace();
  }
  if (activeBusinessWorkspace === "sales") {
    return renderBusinessSalesWorkspace();
  }
  if (activeBusinessWorkspace === "bills") {
    return renderBusinessPurchaseWorkspace();
  }
  if (activeBusinessWorkspace === "credit-notes") {
    return renderBusinessCreditNoteWorkspace();
  }
  if (activeBusinessWorkspace === "debit-notes") {
    return renderBusinessDebitNoteWorkspace();
  }
  if (activeBusinessWorkspace === "financial-health") {
    return renderFinancialHealthWorkspace();
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

function financialHealthFeatureList(items) {
  return items.map((item) => `
    <li>
      <strong>${escapeHtml(item[0])}</strong>
      <span>${escapeHtml(item[1])}</span>
    </li>
  `).join("");
}

function renderFinancialHealthWorkspace() {
  const charts = [
    ["Cash flow", "Operating inflow/outflow trend from posted ledger entries."],
    ["Receivables aging", "Customer balances grouped by overdue bucket."],
    ["Payables aging", "Vendor obligations grouped by due bucket."],
    ["Revenue vs expenses", "Monthly income and cost comparison."],
    ["Profit trend", "Gross and net profit movement over time."],
  ];
  const kpis = [
    ["Gross margin", "Revenue less direct costs as a percentage of revenue."],
    ["Net profit", "Posted revenue minus posted expenses."],
    ["Cash runway", "Available cash divided by average monthly burn."],
    ["Debtor days", "Average collection period for receivables."],
    ["Creditor days", "Average payment period for payables."],
    ["Inventory turnover", "COGS or consumption compared with average inventory."],
  ];
  const reports = [
    ["Monthly financial summary", "Income, expense, cash, receivables, payables, and margin snapshot."],
    ["Branch/company performance", "Segmented performance once branch/company dimensions are available."],
  ];
  const alerts = [
    ["Low cash", "Cash balance or runway below configured threshold."],
    ["Overdue receivables", "Invoices crossing due-date buckets."],
    ["High expenses", "Expense variance above period baseline."],
    ["Negative margins", "Gross or net margin below zero."],
  ];

  return `
    <section class="financial-health-workspace erp-workspace-panel" aria-label="Financial Health Dashboard preview">
      <div class="preview-heading compact">
        <div>
          <h4>Financial Health Dashboard</h4>
          <p>Preview workspace for value-added financial intelligence inside MitraBooks ERP.</p>
        </div>
        <span class="pill warn">Preview</span>
      </div>
      <div class="financial-health-status-grid">
        <article>
          <span>Current state</span>
          <strong>Workspace shell added</strong>
          <p>Navigation and preview sections are available in Intelligence & Reports.</p>
        </article>
        <article>
          <span>Target state</span>
          <strong>Ledger-backed dashboard</strong>
          <p>KPIs, charts, alerts, exports, and AI summary should be generated from posted accounting data.</p>
        </article>
        <article>
          <span>Gap</span>
          <strong>Backend aggregation APIs</strong>
          <p>Financial health endpoints, export generation, thresholds, and branch/company dimensions are not yet implemented.</p>
        </article>
      </div>
      <div class="financial-health-grid">
        <article>
          <h5>Graphs</h5>
          <ul>${financialHealthFeatureList(charts)}</ul>
        </article>
        <article>
          <h5>KPIs</h5>
          <ul>${financialHealthFeatureList(kpis)}</ul>
        </article>
        <article>
          <h5>Reports</h5>
          <ul>${financialHealthFeatureList(reports)}</ul>
        </article>
        <article>
          <h5>Alerts</h5>
          <ul>${financialHealthFeatureList(alerts)}</ul>
        </article>
      </div>
      <div class="financial-health-roadmap">
        <h5>Implementation sequence</h5>
        <ol>
          <li>Backend: add tenant-scoped financial aggregation APIs from posted ledgers.</li>
          <li>Frontend: replace preview cards with live charts and KPI widgets.</li>
          <li>Export service: generate PDF, Excel, and PPT from reviewed report templates.</li>
          <li>Optional AI layer: financial health summary with risks, assumptions, and recommendations.</li>
        </ol>
        <p>Deferred scope: this preview does not calculate live financial health, export files, or generate AI advice yet.</p>
      </div>
    </section>
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
    city: data.city?.trim() || null,
    state: data.state?.trim() || null,
    pincode: data.pincode?.trim() || null,
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

async function loadCaPracticeDocuments() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/ca-documents?limit=100", { method: "GET" });
  lastCaDocumentsResult = result;
  if (result.ok) {
    lastCaDocuments = Array.isArray(result.payload?.items) ? result.payload.items : [];
    if (currentExperience === "mitrabooks" && activeOrgSelectorType() === "CA_PRACTICE") {
      dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig.mitrabooks);
    }
  } else {
    lastCaDocuments = [];
    setLoginStatus("warn", "Unable to load CA documents", statusDetailText(result.payload?.detail) || `Document metadata request failed with HTTP ${result.status}.`);
    if (currentExperience === "mitrabooks" && activeOrgSelectorType() === "CA_PRACTICE") {
      dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig.mitrabooks);
    }
  }
  renderJson(apiOutput, { ca_documents: { ok: result.ok, status: result.status, count: lastCaDocuments.length, detail: result.payload?.detail || null } });
  return result;
}

async function createCaPracticeDocument(form) {
  const formData = new FormData(form);
  const payload = {
    client_name: String(formData.get("client_name") || "").trim(),
    document_type: String(formData.get("document_type") || "").trim(),
    period: String(formData.get("period") || "").trim(),
    assigned_to: String(formData.get("assigned_to") || "").trim() || null,
    original_file_name: String(formData.get("original_file_name") || "").trim() || null,
    notes: String(formData.get("notes") || "").trim() || null,
  };
  const result = await apiRequest("mitrabooks", "/api/v1/business/ca-documents", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (result.ok) {
    form.reset();
    setLoginStatus("ok", "Document metadata added", `${result.payload?.client_name || "Client"} is now in the CA review queue.`);
    await loadCaPracticeDocuments();
  } else {
    setLoginStatus("danger", "Document metadata failed", statusDetailText(result.payload?.detail) || "Check the required fields and try again.");
  }
  renderJson(apiOutput, { create_ca_document: result });
}

async function updateCaPracticeDocumentStatus(documentId, status) {
  if (!documentId || !status) {
    return;
  }
  const result = await apiRequest("mitrabooks", `/api/v1/business/ca-documents/${encodeURIComponent(documentId)}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
  if (result.ok) {
    setLoginStatus("ok", "Document status updated", `${result.payload?.client_name || "Document"} marked ${caDocumentStatusLabel(status)}.`);
    await loadCaPracticeDocuments();
  } else {
    setLoginStatus("danger", "Status update failed", statusDetailText(result.payload?.detail) || "Try again.");
  }
  renderJson(apiOutput, { update_ca_document: result });
}

async function updateBusinessParty(partyId, data) {
  const appKey = "mitrabooks";
  const payload = {
    party_name: data.name,
    gstin: data.gstin || null,
    city: data.city?.trim() || null,
    state: data.state?.trim() || null,
    pincode: data.pincode?.trim() || null,
  };
  if (data.party_type) {
    payload.party_type = data.party_type;
  }

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
  const partyType = button.getAttribute("data-party-type") || "customer";
  const partyGstin = button.getAttribute("data-party-gstin") || "";
  const partyCity = button.getAttribute("data-party-city") || "";
  const partyState = button.getAttribute("data-party-state") || "";
  const partyPincode = button.getAttribute("data-party-pincode") || "";
  const openingBalance = button.getAttribute("data-party-opening-balance") || "0";

  document.getElementById("business-party-edit-id").value = partyId;
  const editTypeSelect = document.getElementById("business-party-edit-type");
  if (editTypeSelect) editTypeSelect.value = partyType;
  document.getElementById("business-party-edit-name").value = partyName;
  document.getElementById("business-party-edit-gstin").value = partyGstin;
  document.getElementById("business-party-edit-city").value = partyCity;
  document.getElementById("business-party-edit-state").value = partyState;
  document.getElementById("business-party-edit-pincode").value = partyPincode;
  document.getElementById("business-party-edit-opening-balance").value = openingBalance;
  document.getElementById("business-party-edit-label").textContent = `Editing ${partyName}`;

  dialog?.showModal();
}

function setBusinessWorkspace(workspace) {
  if (currentExperience === "mitrabooks" && activeOrgSelectorType() !== "BUSINESS") {
    selectedOrgType = "BUSINESS";
    updateTrustedContextUi();
  }
  activeBusinessWorkspace = workspace;
  syncBusinessNavActiveState();
  dashboardPreview.innerHTML = workspace === "overview"
    ? renderDashboardPreview(experienceConfig.mitrabooks)
    : renderBusinessWorkspace();
  if (workspace === "overview") {
    loadBusinessDashboardStats();
  } else if (workspace === "parties") {
    loadBusinessParties();
  } else if (workspace === "vouchers") {
    loadBusinessAccounts();
    loadBusinessVouchers();
  } else if (workspace === "audit") {
    loadAuditEvents();
  } else if (workspace === "accounting") {
    refreshCurrentAccountingDrilldown();
  } else if (workspace === "reports") {
    loadBusinessAccounts();
    refreshCurrentBusinessReport();
  } else if (workspace === "sales") {
    salesView = "list";
    loadBusinessParties();
    loadBusinessAccounts();
    loadInvoiceSettings();
    loadBusinessInvoices();
  } else if (workspace === "bills") {
    purchaseView = "list";
    loadBusinessParties();
    loadBusinessAccounts();
    loadBusinessBills();
  } else if (workspace === "credit-notes") {
    creditNoteView = "list";
    loadBusinessParties();
    loadBusinessAccounts();
    loadCreditNotes();
  } else if (workspace === "debit-notes") {
    debitNoteView = "list";
    loadBusinessParties();
    loadBusinessAccounts();
    loadDebitNotes();
  }
}

function syncBusinessNavActiveState() {
  const selectorOrgType = activeOrgSelectorType();
  const isPlannedOrgWorkspace = currentExperience === "mitrabooks"
    && activeBusinessWorkspace === "overview"
    && selectorOrgType !== "BUSINESS";
  nav.querySelectorAll("a").forEach((link) => {
    const workspace = link.dataset.businessWorkspace || "";
    const isActive = currentExperience === "mitrabooks"
      && !isPlannedOrgWorkspace
      && workspace
      && workspace === activeBusinessWorkspace;
    link.classList.toggle("active", isActive);
  });
  if (topbarCurrent && currentExperience === "mitrabooks") {
    const labels = {
      overview: "Dashboard",
      parties: "Parties",
      vouchers: "Vouchers",
      audit: "Audit Trail",
      accounting: "Accounting",
      reports: "Financial Reports",
      sales: "Sales Invoices",
      bills: "Purchase Bills",
      "credit-notes": "Credit Notes",
      "debit-notes": "Debit Notes",
      "financial-health": "Financial Health",
    };
    const plannedMeta = orgSelectorMeta[selectorOrgType];
    const label = isPlannedOrgWorkspace
      ? plannedMeta?.label || "Planned Workspace"
      : labels[activeBusinessWorkspace] || "Dashboard";
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

// ========== Business Module: Financial Reports ==========

const BUSINESS_REPORT_TABS = [
  { id: "trial-balance", label: "Trial Balance" },
  { id: "pnl", label: "Profit & Loss" },
  { id: "balance-sheet", label: "Balance Sheet" },
  { id: "general-ledger", label: "General Ledger" },
  { id: "receivables-payables", label: "Receivables / Payables" },
  { id: "period-locks", label: "Period Locks" },
];

let lastPeriodLocks = [];

function financialYearStartIso() {
  const now = new Date();
  // Indian financial year starts April 1. Jan-Mar (month index 0-2) belong to the prior FY.
  const year = now.getMonth() < 3 ? now.getFullYear() - 1 : now.getFullYear();
  return `${year}-04-01`;
}

const businessReportState = {
  tab: "trial-balance",
  as_of: todayIsoDate(),
  from_date: financialYearStartIso(),
  to_date: todayIsoDate(),
  ledgerAccountId: "",
};

let lastBusinessTrialBalance = null;
let lastBusinessProfitLoss = null;
let lastBusinessBalanceSheet = null;
let lastBusinessReceivables = null;
let lastBusinessPayables = null;
let lastBusinessGeneralLedger = null;

function reportResultPayload(result, extra = {}) {
  if (result.ok) {
    return { ok: true, ...(result.payload || {}), ...extra };
  }
  return { ok: false, status: result.status, detail: result.payload?.detail || null, ...extra };
}

async function refreshCurrentBusinessReport() {
  const tab = businessReportState.tab;
  if (tab === "trial-balance") {
    await loadBusinessTrialBalance();
  } else if (tab === "pnl") {
    await loadBusinessProfitLoss();
  } else if (tab === "balance-sheet") {
    await loadBusinessBalanceSheet();
  } else if (tab === "receivables-payables") {
    await loadBusinessReceivablesPayables();
  } else if (tab === "general-ledger") {
    if (businessReportState.ledgerAccountId === "__all_nonzero__") {
      await loadBusinessAllLedgers();
    } else if (businessReportState.ledgerAccountId) {
      await loadBusinessGeneralLedger(businessReportState.ledgerAccountId);
    } else {
      rerenderBusinessReportsIfActive();
    }
  } else if (tab === "period-locks") {
    await loadPeriodLocks();
  }
}

async function loadPeriodLocks() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/gst-period-locks", { method: "GET" });
  lastPeriodLocks = result.ok && Array.isArray(result.payload?.items) ? result.payload.items : [];
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { period_locks: { ok: result.ok, count: lastPeriodLocks.length } });
}

async function setGstPeriodLock(period, locked) {
  if (!period) {
    setLoginStatus("warn", "Period required", "Enter a month to lock (YYYY-MM).");
    return;
  }
  const result = await apiRequest("mitrabooks", "/api/v1/business/gst-period-locks", {
    method: "PUT",
    body: JSON.stringify({ period, locked, accounting_entity_id: "primary" }),
  });
  if (result.ok) {
    setLoginStatus("ok", locked ? "Period locked" : "Period unlocked", `${period} is now ${locked ? "finalised" : "open"}.`);
    await loadPeriodLocks();
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can finalise GST periods.");
  } else {
    setLoginStatus("danger", "Update failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { set_period_lock: { ok: result.ok, status: result.status } });
}

function lockGstPeriodFromInput() {
  const input = document.querySelector("[data-period-lock-input]");
  const value = input?.value || "";
  setGstPeriodLock(value, true);
}

function renderPeriodLocksPanel() {
  const admin = isBusinessAdmin();
  const rows = (Array.isArray(lastPeriodLocks) ? lastPeriodLocks : []).filter((p) => p.locked);
  const nowMonth = todayIsoDate().slice(0, 7);
  return `
    <div class="preview-heading compact">
      <div><p>Finalise a month after filing its GST return. Reversals and back-dated postings into a locked month are blocked.</p></div>
    </div>
    ${admin ? `
      <div class="report-date-controls">
        <label>Finalise month
          <input type="month" data-period-lock-input value="${escapeHtml(nowMonth)}">
        </label>
        <button class="secondary" type="button" data-business-action="lock-period">Lock month</button>
      </div>
    ` : `<p class="muted">Only a tenant admin can finalise or unlock periods.</p>`}
    <div class="table-preview compact-table">
      <table>
        <thead><tr><th>Period</th><th>Status</th><th>Updated by</th>${admin ? "<th>Action</th>" : ""}</tr></thead>
        <tbody>
          ${rows.length ? rows.map((p) => `
            <tr>
              <td>${escapeHtml(p.period || "")}</td>
              <td><span class="pill warn">finalised</span></td>
              <td>${escapeHtml(p.updated_by || "")}</td>
              ${admin ? `<td><button class="secondary" type="button" data-business-action="unlock-period" data-period="${escapeHtml(p.period)}">Unlock</button></td>` : ""}
            </tr>
          `).join("") : `<tr><td colspan="${admin ? 4 : 3}" class="muted">No periods finalised yet.</td></tr>`}
        </tbody>
      </table>
    </div>
  `;
}

function rerenderBusinessReportsIfActive() {
  if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "reports") {
    dashboardPreview.innerHTML = renderBusinessWorkspace();
  }
}

async function loadBusinessTrialBalance() {
  const result = await apiRequest("mitrabooks", `/api/v1/accounting/reports/trial-balance?as_of=${encodeURIComponent(businessReportState.as_of)}`, { method: "GET" });
  lastBusinessTrialBalance = reportResultPayload(result);
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { trial_balance: { ok: result.ok, status: result.status } });
}

async function loadBusinessProfitLoss() {
  const result = await apiRequest("mitrabooks", `/api/v1/accounting/reports/pnl?from_date=${encodeURIComponent(businessReportState.from_date)}&to_date=${encodeURIComponent(businessReportState.to_date)}`, { method: "GET" });
  lastBusinessProfitLoss = reportResultPayload(result);
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { profit_loss: { ok: result.ok, status: result.status } });
}

async function loadBusinessBalanceSheet() {
  const result = await apiRequest("mitrabooks", `/api/v1/accounting/reports/balance-sheet?as_of=${encodeURIComponent(businessReportState.as_of)}`, { method: "GET" });
  lastBusinessBalanceSheet = reportResultPayload(result);
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { balance_sheet: { ok: result.ok, status: result.status } });
}

async function loadBusinessReceivablesPayables() {
  const [arResult, apResult] = await Promise.all([
    apiRequest("mitrabooks", `/api/v1/accounting/reports/accounts-receivable?as_of=${encodeURIComponent(businessReportState.as_of)}`, { method: "GET" }),
    apiRequest("mitrabooks", `/api/v1/accounting/reports/accounts-payable?as_of=${encodeURIComponent(businessReportState.as_of)}`, { method: "GET" }),
  ]);
  lastBusinessReceivables = reportResultPayload(arResult);
  lastBusinessPayables = reportResultPayload(apResult);
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { receivables: { ok: arResult.ok }, payables: { ok: apResult.ok } });
}

async function loadBusinessGeneralLedger(accountId) {
  businessReportState.ledgerAccountId = String(accountId || "");
  const account = findBusinessAccountById(accountId);
  const label = account ? `${account.code} - ${account.name}` : String(accountId);
  lastBusinessGeneralLedger = { loading: true, account_label: label };
  rerenderBusinessReportsIfActive();
  const result = await apiRequest("mitrabooks", `/api/v1/accounting/ledger/${encodeURIComponent(accountId)}`, { method: "GET" });
  if (result.ok) {
    const lines = Array.isArray(result.payload) ? result.payload : accountRowsFromPayload(result.payload);
    lastBusinessGeneralLedger = { ok: true, account_id: accountId, account_label: label, lines };
  } else {
    lastBusinessGeneralLedger = { ok: false, account_id: accountId, account_label: label, detail: result.payload?.detail || null };
  }
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { general_ledger: { ok: result.ok, status: result.status, account_id: accountId } });
}

function reportDateControls() {
  const tab = businessReportState.tab;
  const asOfTabs = ["trial-balance", "balance-sheet", "receivables-payables"];
  if (tab === "pnl") {
    return `
      <div class="report-date-controls" data-business-report-filters>
        <label>From <input type="date" name="from_date" value="${escapeHtml(businessReportState.from_date)}"></label>
        <label>To <input type="date" name="to_date" value="${escapeHtml(businessReportState.to_date)}"></label>
        <button class="secondary" type="button" data-business-action="apply-report-filter">Apply</button>
      </div>
    `;
  }
  if (asOfTabs.includes(tab)) {
    return `
      <div class="report-date-controls" data-business-report-filters>
        <label>As of <input type="date" name="as_of" value="${escapeHtml(businessReportState.as_of)}"></label>
        <button class="secondary" type="button" data-business-action="apply-report-filter">Apply</button>
      </div>
    `;
  }
  return "";
}

function renderBusinessReportsWorkspace() {
  const tabs = BUSINESS_REPORT_TABS.map((tab) => `
    <button
      class="report-tab ${businessReportState.tab === tab.id ? "active" : ""}"
      type="button"
      data-business-action="report-tab"
      data-report-tab="${escapeHtml(tab.id)}"
    >${escapeHtml(tab.label)}</button>
  `).join("");

  let body = "";
  if (businessReportState.tab === "trial-balance") {
    body = renderBusinessTrialBalance();
  } else if (businessReportState.tab === "pnl") {
    body = renderBusinessProfitLoss();
  } else if (businessReportState.tab === "balance-sheet") {
    body = renderBusinessBalanceSheet();
  } else if (businessReportState.tab === "general-ledger") {
    body = renderBusinessGeneralLedger();
  } else if (businessReportState.tab === "receivables-payables") {
    body = renderBusinessReceivablesPayables();
  } else if (businessReportState.tab === "period-locks") {
    body = renderPeriodLocksPanel();
  }

  return `
    <div class="verification-panel erp-workspace-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Financial Reports</h4>
          <p>Live reports from posted ledger entries for this tenant.</p>
        </div>
      </div>
      <div class="report-tabs" role="tablist">${tabs}</div>
      ${reportDateControls()}
      ${body}
    </div>
  `;
}

function reportUnavailablePanel(title, payload) {
  const detail = payload?.detail || "Report unavailable. Check accounting access and try again.";
  return `
    <div class="table-preview compact-table">
      <h4>${escapeHtml(title)}</h4>
      <p class="muted">${escapeHtml(detail)}</p>
    </div>
  `;
}

function renderBusinessTrialBalance() {
  const payload = lastBusinessTrialBalance;
  if (!payload) {
    return `<p class="muted">Loading trial balance...</p>`;
  }
  if (payload.ok === false) {
    return reportUnavailablePanel("Trial Balance", payload);
  }
  const rows = Array.isArray(payload.lines) ? payload.lines : [];
  return `
    <div class="preview-heading compact">
      <div><p>As of ${escapeHtml(payload.as_of || businessReportState.as_of)}. Debits and credits must match.</p></div>
      <span class="pill ${payload.balanced ? "ok" : "warn"}">${payload.balanced ? "balanced" : "not balanced"}</span>
    </div>
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Code</th>
            <th>Account</th>
            <th class="amount">Debit</th>
            <th class="amount">Credit</th>
            <th>Ledger</th>
          </tr>
        </thead>
        <tbody>
          ${rows.length ? rows.map((row) => `
            <tr>
              <td>${escapeHtml(row.account_code || "")}</td>
              <td>${escapeHtml(row.account_name || "")}</td>
              <td class="amount">${escapeHtml(formatCurrency(row.debit_total || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(row.credit_total || 0))}</td>
              <td>
                <button class="secondary" type="button" data-business-action="report-ledger" data-account-id="${escapeHtml(row.account_id || "")}">Open</button>
              </td>
            </tr>
          `).join("") : `
            <tr><td colspan="5" class="muted">No posted balances found for this tenant.</td></tr>
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
  `;
}

function renderBusinessProfitLoss() {
  const payload = lastBusinessProfitLoss;
  if (!payload) {
    return `<p class="muted">Loading profit & loss...</p>`;
  }
  if (payload.ok === false) {
    return reportUnavailablePanel("Profit & Loss", payload);
  }
  const lines = Array.isArray(payload.lines) ? payload.lines : [];
  return `
    <div class="preview-heading compact">
      <div><p>${escapeHtml(payload.from_date || businessReportState.from_date)} to ${escapeHtml(payload.to_date || businessReportState.to_date)}</p></div>
      <span class="pill ${Number(payload.net_profit || 0) >= 0 ? "ok" : "warn"}">${escapeHtml(formatCurrency(payload.net_profit || 0))}</span>
    </div>
    <div class="metric-grid three">
      ${renderStatCards([
        ["Income", formatCurrency(payload.income_total || 0), "posted income"],
        ["Expenses", formatCurrency(payload.expense_total || 0), "posted expenses"],
        ["Net Profit", formatCurrency(payload.net_profit || 0), "income less expense"],
      ])}
    </div>
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Code</th>
            <th>Account</th>
            <th>Type</th>
            <th class="amount">Debit</th>
            <th class="amount">Credit</th>
            <th class="amount">Net</th>
          </tr>
        </thead>
        <tbody>
          ${lines.length ? lines.map((line) => `
            <tr>
              <td>${escapeHtml(line.account_code || "")}</td>
              <td>${escapeHtml(line.account_name || "")}</td>
              <td>${escapeHtml(line.account_type || "")}</td>
              <td class="amount">${escapeHtml(formatCurrency(line.debit_total || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(line.credit_total || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(line.net_amount || 0))}</td>
            </tr>
          `).join("") : `
            <tr><td colspan="6" class="muted">No income or expense rows found for this period.</td></tr>
          `}
        </tbody>
      </table>
    </div>
  `;
}

function renderBusinessBalanceSheet() {
  const payload = lastBusinessBalanceSheet;
  if (!payload) {
    return `<p class="muted">Loading balance sheet...</p>`;
  }
  if (payload.ok === false) {
    return reportUnavailablePanel("Balance Sheet", payload);
  }
  const sections = [
    ["Assets", Array.isArray(payload.assets) ? payload.assets : []],
    ["Liabilities", Array.isArray(payload.liabilities) ? payload.liabilities : []],
    ["Equity", Array.isArray(payload.equity) ? payload.equity : []],
  ];
  return `
    <div class="preview-heading compact">
      <div><p>As of ${escapeHtml(payload.as_of || businessReportState.as_of)}. Assets should equal liabilities plus equity.</p></div>
      <span class="pill ${payload.balanced ? "ok" : "warn"}">${payload.balanced ? "balanced" : "not balanced"}</span>
    </div>
    <div class="metric-grid three">
      ${renderStatCards([
        ["Assets", formatCurrency(payload.total_assets || 0), "resources"],
        ["Liabilities", formatCurrency(payload.total_liabilities || 0), "obligations"],
        ["Equity", formatCurrency(payload.total_equity || 0), "owner funds"],
      ])}
    </div>
    <div class="dashboard-main-grid platform-grid">
      ${sections.map(([title, rows]) => `
        <article>
          <h4>${escapeHtml(title)}</h4>
          <div class="table-preview compact-table">
            <table>
              <thead>
                <tr><th>Code</th><th>Account</th><th class="amount">Balance</th></tr>
              </thead>
              <tbody>
                ${rows.length ? rows.map((line) => `
                  <tr>
                    <td>${escapeHtml(line.account_code || "")}</td>
                    <td>${escapeHtml(line.account_name || "")}</td>
                    <td class="amount">${escapeHtml(formatCurrency(line.balance || 0))}</td>
                  </tr>
                `).join("") : `<tr><td colspan="3" class="muted">No rows.</td></tr>`}
              </tbody>
            </table>
          </div>
        </article>
      `).join("")}
    </div>
  `;
}

function renderBusinessGeneralLedger() {
  const accounts = businessAccountsForSelection();
  const selector = `
    <div class="report-date-controls" data-business-report-ledger>
      <label>Account
        <select name="ledger_account" aria-label="Select ledger account">
          <option value="">Select an account</option>
          <option value="__all_nonzero__" ${businessReportState.ledgerAccountId === "__all_nonzero__" ? "selected" : ""}>All Ledger Accounts &gt; 0</option>
          ${accounts.map((acc) => `
            <option value="${escapeHtml(acc.id)}" ${String(acc.id) === String(businessReportState.ledgerAccountId) ? "selected" : ""}>
              ${escapeHtml(`${acc.code} - ${acc.name}`)}
            </option>
          `).join("")}
        </select>
      </label>
      <button class="secondary" type="button" data-business-action="load-report-ledger">View Ledger</button>
    </div>
  `;

  const payload = lastBusinessGeneralLedger;
  let trace = "";
  if (!payload) {
    trace = `<p class="muted">Select an account to view its posted ledger entries.</p>`;
  } else if (payload.loading) {
    trace = `<p class="muted">Loading ledger for ${escapeHtml(payload.account_label || "selected account")}...</p>`;
  } else if (payload.ok === false) {
    trace = reportUnavailablePanel(`Ledger: ${payload.account_label || ""}`, payload);
  } else if (payload.multi) {
    const ledgers = Array.isArray(payload.ledgers) ? payload.ledgers : [];
    trace = ledgers.length
      ? ledgers.map((l) => renderLedgerTraceTable(l.account_label, l.lines, l.ok === false ? l.detail : null)).join("")
      : `<p class="muted">No accounts with posted movement as of ${escapeHtml(businessReportState.as_of)}.</p>`;
  } else {
    trace = renderLedgerTraceTable(payload.account_label, payload.lines);
  }
  return selector + trace;
}

function renderLedgerTraceTable(label, lines, errorDetail = null) {
  if (errorDetail) {
    return `
      <div class="table-preview compact-table">
        <h4>Ledger: ${escapeHtml(label || "")}</h4>
        <p class="muted">${escapeHtml(errorDetail)}</p>
      </div>
    `;
  }
  const rows = Array.isArray(lines) ? lines : [];
  return `
    <div class="table-preview compact-table">
      <h4>Ledger: ${escapeHtml(label || "")}</h4>
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Reference</th>
            <th>Description</th>
            <th class="amount">Debit</th>
            <th class="amount">Credit</th>
            <th class="amount">Balance</th>
          </tr>
        </thead>
        <tbody>
          ${rows.length ? rows.map((line) => `
            <tr>
              <td>${escapeHtml(line.entry_date || "")}</td>
              <td>${escapeHtml(line.reference || "")}</td>
              <td>${escapeHtml(line.description || "")}</td>
              <td class="amount">${escapeHtml(formatCurrency(line.debit || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(line.credit || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(line.running_balance || 0))}</td>
            </tr>
          `).join("") : `<tr><td colspan="6" class="muted">No posted entries for this account.</td></tr>`}
        </tbody>
      </table>
    </div>
  `;
}

async function loadBusinessAllLedgers() {
  businessReportState.ledgerAccountId = "__all_nonzero__";
  lastBusinessGeneralLedger = { loading: true, account_label: "All Ledger Accounts > 0" };
  rerenderBusinessReportsIfActive();

  const tbResult = await apiRequest("mitrabooks", `/api/v1/accounting/reports/trial-balance?as_of=${encodeURIComponent(businessReportState.as_of)}`, { method: "GET" });
  if (!tbResult.ok) {
    lastBusinessGeneralLedger = { ok: false, account_label: "All Ledger Accounts > 0", detail: tbResult.payload?.detail || "Could not load account list." };
    rerenderBusinessReportsIfActive();
    return;
  }
  const lines = Array.isArray(tbResult.payload?.lines) ? tbResult.payload.lines : [];
  const active = lines.filter((l) => (Number(l.debit_total || 0) + Number(l.credit_total || 0)) > 0);

  lastBusinessGeneralLedger = { loading: true, account_label: `All Ledger Accounts > 0 (${active.length})` };
  rerenderBusinessReportsIfActive();

  const ledgers = [];
  for (const l of active) {
    const r = await apiRequest("mitrabooks", `/api/v1/accounting/ledger/${encodeURIComponent(l.account_id)}`, { method: "GET" });
    ledgers.push({
      account_id: l.account_id,
      account_label: `${l.account_code || ""} - ${l.account_name || ""}`.trim(),
      ok: r.ok,
      lines: r.ok ? (Array.isArray(r.payload) ? r.payload : accountRowsFromPayload(r.payload)) : [],
      detail: r.ok ? null : (r.payload?.detail || "Ledger unavailable."),
    });
  }
  lastBusinessGeneralLedger = { ok: true, multi: true, account_label: "All Ledger Accounts > 0", ledgers };
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { general_ledger_all: { ok: true, accounts: ledgers.length } });
}

function renderReceivablesPayablesSection(title, subtitle, payload) {
  if (!payload) {
    return `
      <article>
        <h4>${escapeHtml(title)}</h4>
        <p class="muted">Loading...</p>
      </article>
    `;
  }
  if (payload.ok === false) {
    return `
      <article>
        <h4>${escapeHtml(title)}</h4>
        <p class="muted">${escapeHtml(payload.detail || "Report unavailable. Check accounting access and try again.")}</p>
      </article>
    `;
  }
  const lines = Array.isArray(payload.lines) ? payload.lines : [];
  return `
    <article>
      <h4>${escapeHtml(title)} <span class="pill">${escapeHtml(formatCurrency(payload.total_balance || 0))}</span></h4>
      <p class="muted">${escapeHtml(subtitle)}</p>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr><th>Account</th><th class="amount">Balance</th></tr>
          </thead>
          <tbody>
            ${lines.length ? lines.map((line) => `
              <tr>
                <td>${escapeHtml(line.account_name || "")}</td>
                <td class="amount">${escapeHtml(formatCurrency(line.balance || 0))}</td>
              </tr>
            `).join("") : `<tr><td colspan="2" class="muted">No outstanding balances.</td></tr>`}
          </tbody>
        </table>
      </div>
    </article>
  `;
}

function renderBusinessReceivablesPayables() {
  return `
    <div class="preview-heading compact">
      <div><p>Outstanding customer and vendor balances as of ${escapeHtml(businessReportState.as_of)}.</p></div>
    </div>
    <div class="dashboard-main-grid platform-grid">
      ${renderReceivablesPayablesSection("Receivables", "Amounts owed by customers (debit balances on receivable accounts).", lastBusinessReceivables)}
      ${renderReceivablesPayablesSection("Payables", "Amounts owed to vendors (credit balances on payable accounts).", lastBusinessPayables)}
    </div>
  `;
}

function setBusinessReportTab(tab) {
  if (!BUSINESS_REPORT_TABS.some((t) => t.id === tab)) {
    return;
  }
  businessReportState.tab = tab;
  rerenderBusinessReportsIfActive();
  refreshCurrentBusinessReport();
}

function applyBusinessReportFilter() {
  const panel = document.querySelector("[data-business-report-filters]");
  if (panel) {
    const asOf = panel.querySelector("input[name='as_of']");
    const fromDate = panel.querySelector("input[name='from_date']");
    const toDate = panel.querySelector("input[name='to_date']");
    if (asOf && asOf.value) businessReportState.as_of = asOf.value;
    if (fromDate && fromDate.value) businessReportState.from_date = fromDate.value;
    if (toDate && toDate.value) businessReportState.to_date = toDate.value;
  }
  refreshCurrentBusinessReport();
}

function loadBusinessReportLedgerFromSelect() {
  const panel = document.querySelector("[data-business-report-ledger]");
  const select = panel?.querySelector("select[name='ledger_account']");
  const accountId = select?.value || "";
  if (!accountId) {
    setLoginStatus("warn", "Select an account", "Choose an account to view its ledger.");
    return;
  }
  if (accountId === "__all_nonzero__") {
    loadBusinessAllLedgers();
    return;
  }
  loadBusinessGeneralLedger(accountId);
}

// ========== Business Module: Sales Invoices (GST) ==========

let salesView = "list"; // list | create | detail | settings
let lastBusinessInvoices = [];
let lastInvoiceDetail = null;
let lastInvoiceSettings = null;
let invoiceLineSeq = 0;
let invoiceFormLines = [];
const salesFormHeader = {
  customer_party_id: "",
  invoice_date: todayIsoDate(),
  due_date: "",
  is_inter_state: false,
  income_account_code: "41001",
  place_of_supply: "",
  reference: "",
  notes: "",
};

const INVOICE_STANDARD_FIELD_LABELS = {
  due_date: "Due date",
  place_of_supply: "Place of supply",
  reference: "Reference / PO",
  notes: "Notes",
  hsn_sac: "HSN/SAC (line column)",
};

function isBusinessAdmin() {
  const role = String(lastModuleContext?.role || lastModuleContext?.user_role || "").trim().toLowerCase();
  // Show settings to admins; when role is unknown the backend still enforces access on save.
  return role === "" || role === "tenant_admin" || role === "super_admin";
}

function invoiceFieldRule(key) {
  const fc = (lastInvoiceSettings && lastInvoiceSettings.field_config) || {};
  return fc[key] || { visible: true, required: false };
}

function invoiceFieldVisible(key) {
  return invoiceFieldRule(key).visible !== false;
}

function invoiceFieldRequired(key) {
  return !!invoiceFieldRule(key).required;
}

async function loadInvoiceSettings() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/invoice-settings", { method: "GET" });
  if (result.ok) {
    lastInvoiceSettings = result.payload;
  } else if (!lastInvoiceSettings) {
    // Fall back to permissive defaults so the form still renders.
    lastInvoiceSettings = {
      field_config: { due_date: { visible: true, required: false }, place_of_supply: { visible: true, required: false }, reference: { visible: true, required: false }, notes: { visible: true, required: false }, hsn_sac: { visible: true, required: false } },
      numbering: { prefix: "INV", number_format: "{PREFIX}-{FY}-{SEQ}", seq_padding: 6, start_number: 1, reset_yearly: true },
      custom_fields: [],
      branding: {},
    };
  }
  rerenderSalesIfActive();
}

function round2(value) {
  const n = Number(value);
  if (!isFinite(n)) return 0;
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

let invoiceReverseOpen = false;
let billReverseOpen = false;

// Reversal must stay within the document's GST month. Returns the date input
// bounds + a sensible default (today if in-month, else month end).
function reversalDateBounds(isoDate) {
  const d = String(isoDate || todayIsoDate());
  const ym = d.slice(0, 7);
  const [y, m] = ym.split("-").map(Number);
  const lastDay = new Date(y, m, 0).getDate();
  const start = `${ym}-01`;
  const end = `${ym}-${String(lastDay).padStart(2, "0")}`;
  const today = todayIsoDate();
  const inMonth = today.slice(0, 7) === ym;
  return { min: start, max: inMonth ? today : end, def: inMonth ? today : end, label: ym };
}

function reversalPanel(kind, id, isoDate) {
  const b = reversalDateBounds(isoDate);
  return `
    <div class="reversal-panel">
      <label>Reversal date
        <input type="date" data-reversal-date value="${escapeHtml(b.def)}" min="${escapeHtml(b.min)}" max="${escapeHtml(b.max)}">
      </label>
      <div class="reversal-panel-actions">
        <button class="primary" type="button" data-business-action="confirm-reverse-${kind}" data-${kind}-id="${escapeHtml(id)}">Confirm reverse</button>
        <button class="secondary" type="button" data-business-action="cancel-reverse-${kind}">Cancel</button>
      </div>
      <p class="muted">Must be dated within the document's GST month (${escapeHtml(b.label)}). A reversing journal entry will be posted on this date.</p>
      <p class="muted reversal-scope-note">Use reverse only to correct an entry made in error in the open period. For returns, price changes, or ITC reversal, raise a ${kind === "bill" ? "debit note" : "credit note"} instead (coming soon).</p>
    </div>
  `;
}

function rerenderSalesIfActive() {
  if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "sales") {
    dashboardPreview.innerHTML = renderBusinessWorkspace();
  }
}

async function loadBusinessInvoices() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/invoices?limit=100", { method: "GET" });
  if (result.ok) {
    lastBusinessInvoices = Array.isArray(result.payload?.items) ? result.payload.items : [];
  } else {
    lastBusinessInvoices = [];
    setLoginStatus("danger", "Unable to load invoices", statusDetailText(result.payload?.detail) || `Invoice list request failed with HTTP ${result.status}.`);
  }
  rerenderSalesIfActive();
  renderJson(apiOutput, { invoices: { ok: result.ok, status: result.status, count: lastBusinessInvoices.length } });
}

function customerPartyOptions() {
  return (Array.isArray(lastBusinessParties) ? lastBusinessParties : [])
    .filter((p) => ["customer", "both"].includes(String(p.party_type || "").toLowerCase()));
}

function incomeAccountOptions() {
  return businessAccountsForSelection().filter((acc) => String(acc.code || "").startsWith("4"));
}

function computeInvoiceLine(qty, rate, gstRate, inter) {
  const taxable = round2(Number(qty || 0) * Number(rate || 0));
  const gst = round2(taxable * Number(gstRate || 0) / 100);
  let cgst = 0, sgst = 0, igst = 0;
  if (inter) {
    igst = gst;
  } else {
    cgst = round2(gst / 2);
    sgst = round2(gst - cgst);
  }
  return { taxable, cgst, sgst, igst, total: round2(taxable + cgst + sgst + igst) };
}

function syncSalesFormFromDom() {
  const form = document.querySelector("[data-invoice-form]");
  if (!form) return;
  const val = (sel) => form.querySelector(sel)?.value ?? "";
  salesFormHeader.customer_party_id = val("select[name='customer_party_id']");
  salesFormHeader.invoice_date = val("input[name='invoice_date']") || todayIsoDate();
  salesFormHeader.due_date = val("input[name='due_date']");
  salesFormHeader.is_inter_state = !!form.querySelector("input[name='is_inter_state']")?.checked;
  salesFormHeader.income_account_code = val("select[name='income_account_code']") || "41001";
  salesFormHeader.place_of_supply = val("input[name='place_of_supply']");
  salesFormHeader.reference = val("input[name='reference']");
  salesFormHeader.notes = val("textarea[name='notes']");
  invoiceFormLines = Array.from(form.querySelectorAll("[data-invoice-line]")).map((row) => ({
    id: row.getAttribute("data-invoice-line"),
    description: row.querySelector("input[name='description']")?.value || "",
    hsn_sac: row.querySelector("input[name='hsn_sac']")?.value || "",
    quantity: row.querySelector("input[name='quantity']")?.value || "",
    rate: row.querySelector("input[name='rate']")?.value || "",
    gst_rate: row.querySelector("input[name='gst_rate']")?.value || "",
  }));
}

function updateInvoiceTotalsDisplay() {
  const form = document.querySelector("[data-invoice-form]");
  if (!form) return;
  const inter = !!form.querySelector("input[name='is_inter_state']")?.checked;
  let taxableTotal = 0, cgstTotal = 0, sgstTotal = 0, igstTotal = 0;
  form.querySelectorAll("[data-invoice-line]").forEach((row) => {
    const qty = row.querySelector("input[name='quantity']")?.value;
    const rate = row.querySelector("input[name='rate']")?.value;
    const gstRate = row.querySelector("input[name='gst_rate']")?.value;
    const c = computeInvoiceLine(qty, rate, gstRate, inter);
    row.querySelector("[data-line-taxable]").textContent = formatCurrency(c.taxable);
    row.querySelector("[data-line-gst]").textContent = formatCurrency(c.cgst + c.sgst + c.igst);
    row.querySelector("[data-line-total]").textContent = formatCurrency(c.total);
    taxableTotal += c.taxable; cgstTotal += c.cgst; sgstTotal += c.sgst; igstTotal += c.igst;
  });
  const gstTotal = round2(cgstTotal + sgstTotal + igstTotal);
  const invoiceTotal = round2(taxableTotal + gstTotal);
  const set = (sel, v) => { const el = form.querySelector(sel); if (el) el.textContent = formatCurrency(v); };
  set("[data-total-taxable]", taxableTotal);
  set("[data-total-cgst]", cgstTotal);
  set("[data-total-sgst]", sgstTotal);
  set("[data-total-igst]", igstTotal);
  set("[data-total-invoice]", invoiceTotal);
  // Toggle CGST/SGST vs IGST total rows based on supply type
  const cgstRow = form.querySelector("[data-row-cgst]");
  const sgstRow = form.querySelector("[data-row-sgst]");
  const igstRow = form.querySelector("[data-row-igst]");
  if (cgstRow && sgstRow && igstRow) {
    cgstRow.hidden = inter;
    sgstRow.hidden = inter;
    igstRow.hidden = !inter;
  }
}

function setBusinessSalesView(view) {
  salesView = view;
  invoiceReverseOpen = false;
  rerenderSalesIfActive();
  if (view === "create") {
    updateInvoiceTotalsDisplay();
  }
}

function openInvoiceCreate() {
  invoiceFormLines = [{ id: `il-${++invoiceLineSeq}`, description: "", hsn_sac: "", quantity: "1", rate: "", gst_rate: "18" }];
  salesFormHeader.customer_party_id = "";
  salesFormHeader.invoice_date = todayIsoDate();
  salesFormHeader.due_date = "";
  salesFormHeader.is_inter_state = false;
  salesFormHeader.income_account_code = "41001";
  salesFormHeader.place_of_supply = "";
  salesFormHeader.reference = "";
  salesFormHeader.notes = "";
  // Make sure customers, accounts, and settings are available for the form.
  if (!Array.isArray(lastBusinessParties) || lastBusinessParties.length === 0) loadBusinessParties();
  if (!hasLoadedBusinessAccounts()) loadBusinessAccounts();
  if (!lastInvoiceSettings) loadInvoiceSettings();
  setBusinessSalesView("create");
}

function addInvoiceLine() {
  syncSalesFormFromDom();
  invoiceFormLines.push({ id: `il-${++invoiceLineSeq}`, description: "", hsn_sac: "", quantity: "1", rate: "", gst_rate: "18" });
  rerenderSalesIfActive();
  updateInvoiceTotalsDisplay();
}

function removeInvoiceLine(lineId) {
  syncSalesFormFromDom();
  invoiceFormLines = invoiceFormLines.filter((l) => l.id !== lineId);
  if (invoiceFormLines.length === 0) {
    invoiceFormLines.push({ id: `il-${++invoiceLineSeq}`, description: "", hsn_sac: "", quantity: "1", rate: "", gst_rate: "18" });
  }
  rerenderSalesIfActive();
  updateInvoiceTotalsDisplay();
}

async function submitInvoice() {
  syncSalesFormFromDom();
  if (!salesFormHeader.customer_party_id) {
    setLoginStatus("warn", "Customer required", "Select a customer for this invoice.");
    return;
  }
  // Client-side enforcement of admin-configured required fields (backend re-validates).
  for (const key of ["due_date", "place_of_supply", "reference", "notes"]) {
    if (invoiceFieldRequired(key) && !String(salesFormHeader[key] || "").trim()) {
      setLoginStatus("warn", `${INVOICE_STANDARD_FIELD_LABELS[key]} required`, "This field is required by your invoice settings.");
      return;
    }
  }
  const lineItems = invoiceFormLines
    .filter((l) => String(l.description).trim() && Number(l.quantity) > 0)
    .map((l) => ({
      description: String(l.description).trim(),
      hsn_sac: String(l.hsn_sac || "").trim() || null,
      quantity: String(Number(l.quantity)),
      rate: String(Number(l.rate || 0)),
      gst_rate: String(Number(l.gst_rate || 0)),
    }));
  if (lineItems.length === 0) {
    setLoginStatus("warn", "Add a line item", "Enter at least one line with a description and quantity.");
    return;
  }
  const body = {
    customer_party_id: salesFormHeader.customer_party_id,
    invoice_date: salesFormHeader.invoice_date || todayIsoDate(),
    due_date: salesFormHeader.due_date || null,
    is_inter_state: !!salesFormHeader.is_inter_state,
    income_account_code: salesFormHeader.income_account_code || "41001",
    place_of_supply: String(salesFormHeader.place_of_supply || "").trim() || null,
    reference: String(salesFormHeader.reference || "").trim() || null,
    notes: String(salesFormHeader.notes || "").trim() || null,
    line_items: lineItems,
  };
  const result = await apiRequest("mitrabooks", "/api/v1/business/invoices", {
    method: "POST",
    headers: { "X-Idempotency-Key": `sales-invoice-${Date.now()}` },
    body: JSON.stringify(body),
  });
  if (result.ok) {
    setLoginStatus("ok", "Invoice posted", `${result.payload?.invoice_number || "Invoice"} posted to the ledger.`);
    await loadBusinessInvoices();
    setBusinessSalesView("list");
  } else {
    setLoginStatus("danger", "Invoice posting failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { create_invoice: { ok: result.ok, status: result.status, detail: result.payload?.detail || null } });
}

async function openInvoiceDetail(invoiceId) {
  const result = await apiRequest("mitrabooks", `/api/v1/business/invoices/${encodeURIComponent(invoiceId)}`, { method: "GET" });
  if (result.ok) {
    lastInvoiceDetail = result.payload;
    setBusinessSalesView("detail");
  } else {
    setLoginStatus("danger", "Unable to load invoice", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { invoice_detail: { ok: result.ok, status: result.status } });
}

async function cancelInvoice(invoiceId, reversalDate) {
  const body = { reason: "Reversal" };
  if (reversalDate) body.cancel_date = reversalDate;
  const result = await apiRequest("mitrabooks", `/api/v1/business/invoices/${encodeURIComponent(invoiceId)}/cancel`, {
    method: "POST",
    headers: { "X-Idempotency-Key": `sales-invoice-cancel-${invoiceId}-${reversalDate || "today"}` },
    body: JSON.stringify(body),
  });
  if (result.ok) {
    invoiceReverseOpen = false;
    setLoginStatus("ok", "Invoice reversed", "A reversing journal entry was posted.");
    await loadBusinessInvoices();
    if (lastInvoiceDetail && lastInvoiceDetail.invoice_id === invoiceId) {
      lastInvoiceDetail = result.payload;
    }
    rerenderSalesIfActive();
  } else {
    setLoginStatus("danger", "Reverse failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { cancel_invoice: { ok: result.ok, status: result.status } });
}

function invoiceStatusPill(status) {
  const s = String(status || "").toLowerCase();
  // Backend marks a reversed document as "cancelled"; display it as "reversed"
  // to match the accounting action (a reversing journal entry was posted).
  if (s === "cancelled") return `<span class="pill warn">reversed</span>`;
  if (s === "posted") return `<span class="pill ok">posted</span>`;
  return `<span class="pill">${escapeHtml(status || "")}</span>`;
}

function renderInvoiceListTable() {
  const rows = lastBusinessInvoices;
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Invoice #</th>
            <th>Date</th>
            <th>Customer</th>
            <th class="amount">Taxable</th>
            <th class="amount">GST</th>
            <th class="amount">Total</th>
            <th>Status</th>
            <th>Open</th>
          </tr>
        </thead>
        <tbody>
          ${rows.length ? rows.map((inv) => `
            <tr>
              <td>${escapeHtml(inv.invoice_number || "")}</td>
              <td>${escapeHtml(inv.invoice_date || "")}</td>
              <td>${escapeHtml(inv.customer_name || inv.customer_party_id || "")}</td>
              <td class="amount">${escapeHtml(formatCurrency(inv.taxable_total || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(inv.gst_total || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(inv.invoice_total || 0))}</td>
              <td>${invoiceStatusPill(inv.status)}</td>
              <td><button class="secondary" type="button" data-business-action="view-invoice" data-invoice-id="${escapeHtml(inv.invoice_id)}">View</button></td>
            </tr>
          `).join("") : `<tr><td colspan="8" class="muted">No invoices yet. Create your first sales invoice.</td></tr>`}
        </tbody>
      </table>
    </div>
  `;
}

function invoiceFieldLabel(base, key) {
  return `${base}${invoiceFieldRequired(key) ? " *" : ""}`;
}

function invoiceNumberPreview() {
  const n = (lastInvoiceSettings && lastInvoiceSettings.numbering) || {};
  const now = new Date();
  const year = now.getMonth() < 3 ? now.getFullYear() - 1 : now.getFullYear();
  const fy = `${year}-${year + 1}`;
  const fyShort = `${year}-${String(year + 1).slice(-2)}`;
  const seq = String(n.start_number || 1).padStart(Number(n.seq_padding || 6), "0");
  return String(n.number_format || "{PREFIX}-{FY}-{SEQ}")
    .replace("{PREFIX}", n.prefix || "INV")
    .replace("{FYSHORT}", fyShort)
    .replace("{FY}", fy)
    .replace("{SEQ}", seq);
}

function renderInvoiceCreateForm() {
  const customers = customerPartyOptions();
  const incomeAccounts = incomeAccountOptions();
  const hsnVisible = invoiceFieldVisible("hsn_sac");
  const hsnRequired = invoiceFieldRequired("hsn_sac");
  const colspan = hsnVisible ? 9 : 8;
  const lineRows = invoiceFormLines.map((l) => `
    <tr data-invoice-line="${escapeHtml(l.id)}">
      <td><input type="text" name="description" value="${escapeHtml(l.description)}" placeholder="Item / service"></td>
      ${hsnVisible ? `<td><input type="text" name="hsn_sac" value="${escapeHtml(l.hsn_sac)}" placeholder="HSN/SAC"></td>` : ""}
      <td><input type="number" name="quantity" value="${escapeHtml(l.quantity)}" min="0" step="any"></td>
      <td><input type="number" name="rate" value="${escapeHtml(l.rate)}" min="0" step="any" placeholder="0.00"></td>
      <td><input type="number" name="gst_rate" value="${escapeHtml(l.gst_rate)}" min="0" max="100" step="any"></td>
      <td class="amount" data-line-taxable>—</td>
      <td class="amount" data-line-gst>—</td>
      <td class="amount" data-line-total>—</td>
      <td><button class="secondary" type="button" data-business-action="remove-invoice-line" data-line-id="${escapeHtml(l.id)}">✕</button></td>
    </tr>
  `).join("");

  return `
    <div class="verification-panel erp-workspace-panel" data-invoice-form>
      <div class="preview-heading compact">
        <div>
          <h4>New Sales Invoice</h4>
          <p>Next number: <strong>${escapeHtml(invoiceNumberPreview())}</strong> · posts to receivables, sales income, and output GST automatically.</p>
        </div>
        <button class="secondary" type="button" data-business-action="invoice-back">← Back to list</button>
      </div>
      <div class="invoice-form-grid">
        <label>Customer
          <select name="customer_party_id">
            <option value="">Select customer</option>
            ${customers.map((c) => `<option value="${escapeHtml(c.party_id)}" ${c.party_id === salesFormHeader.customer_party_id ? "selected" : ""}>${escapeHtml(c.party_name)}${c.gstin ? ` (${escapeHtml(c.gstin)})` : ""}</option>`).join("")}
          </select>
        </label>
        <label>Invoice date
          <input type="date" name="invoice_date" value="${escapeHtml(salesFormHeader.invoice_date)}">
        </label>
        ${invoiceFieldVisible("due_date") ? `<label>${escapeHtml(invoiceFieldLabel("Due date", "due_date"))}
          <input type="date" name="due_date" value="${escapeHtml(salesFormHeader.due_date)}">
        </label>` : ""}
        <label>Income account
          <select name="income_account_code">
            ${incomeAccounts.length ? incomeAccounts.map((a) => `<option value="${escapeHtml(a.code)}" ${a.code === salesFormHeader.income_account_code ? "selected" : ""}>${escapeHtml(`${a.code} - ${a.name}`)}</option>`).join("") : `<option value="41001" selected>41001 - Sales</option>`}
          </select>
        </label>
        ${invoiceFieldVisible("place_of_supply") ? `<label>${escapeHtml(invoiceFieldLabel("Place of supply", "place_of_supply"))}
          <input type="text" name="place_of_supply" value="${escapeHtml(salesFormHeader.place_of_supply)}" placeholder="State / code">
        </label>` : ""}
        ${invoiceFieldVisible("reference") ? `<label>${escapeHtml(invoiceFieldLabel("Reference / PO", "reference"))}
          <input type="text" name="reference" value="${escapeHtml(salesFormHeader.reference)}" placeholder="${invoiceFieldRequired("reference") ? "Required" : "Optional"}">
        </label>` : ""}
        <label class="invoice-inter-toggle">
          <input type="checkbox" name="is_inter_state" ${salesFormHeader.is_inter_state ? "checked" : ""}>
          Inter-state supply (IGST)
        </label>
      </div>

      <div class="table-preview compact-table invoice-lines">
        <table>
          <thead>
            <tr>
              <th>Description</th>
              ${hsnVisible ? `<th>HSN/SAC${hsnRequired ? " *" : ""}</th>` : ""}
              <th>Qty</th>
              <th>Rate</th>
              <th>GST %</th>
              <th class="amount">Taxable</th>
              <th class="amount">GST</th>
              <th class="amount">Total</th>
              <th></th>
            </tr>
          </thead>
          <tbody>${lineRows}</tbody>
        </table>
      </div>
      <button class="secondary" type="button" data-business-action="add-invoice-line">+ Add line</button>

      <div class="invoice-totals">
        <div><span>Taxable</span><strong data-total-taxable>${formatCurrency(0)}</strong></div>
        <div data-row-cgst ${salesFormHeader.is_inter_state ? "hidden" : ""}><span>CGST</span><strong data-total-cgst>${formatCurrency(0)}</strong></div>
        <div data-row-sgst ${salesFormHeader.is_inter_state ? "hidden" : ""}><span>SGST</span><strong data-total-sgst>${formatCurrency(0)}</strong></div>
        <div data-row-igst ${salesFormHeader.is_inter_state ? "" : "hidden"}><span>IGST</span><strong data-total-igst>${formatCurrency(0)}</strong></div>
        <div class="invoice-grand"><span>Invoice total</span><strong data-total-invoice>${formatCurrency(0)}</strong></div>
      </div>

      ${invoiceFieldVisible("notes") ? `<label class="invoice-notes">${escapeHtml(invoiceFieldLabel("Notes", "notes"))}
        <textarea name="notes" rows="2" placeholder="${invoiceFieldRequired("notes") ? "Required" : "Optional notes shown on the invoice"}">${escapeHtml(salesFormHeader.notes)}</textarea>
      </label>` : ""}

      <div class="invoice-form-actions">
        <button class="primary" type="button" data-business-action="save-invoice">Post Invoice</button>
        <button class="secondary" type="button" data-business-action="invoice-back">Cancel</button>
      </div>
    </div>
  `;
}

function renderInvoiceDetail() {
  const inv = lastInvoiceDetail;
  if (!inv) {
    return `<div class="verification-panel erp-workspace-panel"><p class="muted">Invoice not found.</p></div>`;
  }
  const lines = Array.isArray(inv.line_items) ? inv.line_items : [];
  const taxRow = inv.is_inter_state
    ? `<div data-row-igst><span>IGST</span><strong>${formatCurrency(inv.igst_total || 0)}</strong></div>`
    : `<div><span>CGST</span><strong>${formatCurrency(inv.cgst_total || 0)}</strong></div><div><span>SGST</span><strong>${formatCurrency(inv.sgst_total || 0)}</strong></div>`;
  return `
    <div class="verification-panel erp-workspace-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Invoice ${escapeHtml(inv.invoice_number || "")} ${invoiceStatusPill(inv.status)}</h4>
          <p>${escapeHtml(inv.customer_name || inv.customer_party_id || "")}${inv.customer_gstin ? ` · ${escapeHtml(inv.customer_gstin)}` : ""} · ${escapeHtml(inv.invoice_date || "")}${inv.due_date ? ` · due ${escapeHtml(inv.due_date)}` : ""}</p>
        </div>
        <div class="invoice-detail-actions">
          <button class="secondary" type="button" data-business-action="invoice-back">← Back to list</button>
          ${String(inv.status).toLowerCase() === "posted" && !invoiceReverseOpen ? `<button class="secondary" type="button" data-business-action="begin-reverse-invoice">Reverse Invoice</button>` : ""}
        </div>
      </div>
      ${String(inv.status).toLowerCase() === "posted" && invoiceReverseOpen ? reversalPanel("invoice", inv.invoice_id, inv.invoice_date) : ""}
      <p class="muted">${escapeHtml(inv.is_inter_state ? "Inter-state supply (IGST)" : "Intra-state supply (CGST + SGST)")}${inv.reference ? ` · Ref: ${escapeHtml(inv.reference)}` : ""}</p>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr>
              <th>Description</th>
              <th>HSN/SAC</th>
              <th class="amount">Qty</th>
              <th class="amount">Rate</th>
              <th class="amount">GST %</th>
              <th class="amount">Taxable</th>
              <th class="amount">Total</th>
            </tr>
          </thead>
          <tbody>
            ${lines.map((l) => `
              <tr>
                <td>${escapeHtml(l.description || "")}</td>
                <td>${escapeHtml(l.hsn_sac || "")}</td>
                <td class="amount">${escapeHtml(l.quantity || "")}</td>
                <td class="amount">${escapeHtml(formatCurrency(l.rate || 0))}</td>
                <td class="amount">${escapeHtml(String(l.gst_rate || 0))}%</td>
                <td class="amount">${escapeHtml(formatCurrency(l.taxable_amount || 0))}</td>
                <td class="amount">${escapeHtml(formatCurrency(l.line_total || 0))}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
      <div class="invoice-totals">
        <div><span>Taxable</span><strong>${formatCurrency(inv.taxable_total || 0)}</strong></div>
        ${taxRow}
        <div class="invoice-grand"><span>Invoice total</span><strong>${formatCurrency(inv.invoice_total || 0)}</strong></div>
      </div>
      ${inv.notes ? `<p class="muted">${escapeHtml(inv.notes)}</p>` : ""}
      ${String(inv.status).toLowerCase() === "cancelled" ? `<p class="muted">Reversed${inv.cancel_reason ? `: ${escapeHtml(inv.cancel_reason)}` : ""}. Reversing journal entry #${escapeHtml(inv.reversal_journal_entry_id || "")} posted.</p>` : ""}
    </div>
  `;
}

function openInvoiceSettings() {
  if (!lastInvoiceSettings) loadInvoiceSettings();
  setBusinessSalesView("settings");
}

async function saveInvoiceSettings() {
  const panel = document.querySelector("[data-invoice-settings-form]");
  if (!panel) return;
  const field_config = {};
  Object.keys(INVOICE_STANDARD_FIELD_LABELS).forEach((key) => {
    const visible = panel.querySelector(`input[data-field-visible='${key}']`);
    const required = panel.querySelector(`input[data-field-required='${key}']`);
    field_config[key] = { visible: !!visible?.checked, required: !!required?.checked };
  });
  const numVal = (name) => panel.querySelector(`[data-numbering='${name}']`)?.value;
  const numbering = {
    prefix: (numVal("prefix") || "INV").trim() || "INV",
    number_format: (numVal("number_format") || "{PREFIX}-{FY}-{SEQ}").trim() || "{PREFIX}-{FY}-{SEQ}",
    seq_padding: Math.max(1, Math.min(12, Number(numVal("seq_padding") || 6))),
    start_number: Math.max(1, Number(numVal("start_number") || 1)),
    reset_yearly: !!panel.querySelector("[data-numbering='reset_yearly']")?.checked,
  };
  const body = {
    field_config,
    numbering,
    // Preserve sections managed in Phase 2 (custom fields / branding).
    custom_fields: (lastInvoiceSettings && lastInvoiceSettings.custom_fields) || [],
    branding: (lastInvoiceSettings && lastInvoiceSettings.branding) || {},
  };
  const result = await apiRequest("mitrabooks", "/api/v1/business/invoice-settings", {
    method: "PUT",
    body: JSON.stringify(body),
  });
  if (result.ok) {
    lastInvoiceSettings = result.payload;
    setLoginStatus("ok", "Invoice settings saved", "New invoices will use these settings.");
    setBusinessSalesView("list");
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can change invoice settings.");
  } else {
    setLoginStatus("danger", "Save failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { save_invoice_settings: { ok: result.ok, status: result.status } });
}

function renderInvoiceSettingsPanel() {
  const s = lastInvoiceSettings || {};
  const fc = s.field_config || {};
  const n = s.numbering || {};
  const fieldRows = Object.entries(INVOICE_STANDARD_FIELD_LABELS).map(([key, label]) => {
    const rule = fc[key] || { visible: true, required: false };
    return `
      <tr>
        <td>${escapeHtml(label)}</td>
        <td><label class="inline-check"><input type="checkbox" data-field-visible="${key}" ${rule.visible !== false ? "checked" : ""}> Visible</label></td>
        <td><label class="inline-check"><input type="checkbox" data-field-required="${key}" ${rule.required ? "checked" : ""}> Required</label></td>
      </tr>
    `;
  }).join("");

  return `
    <div class="verification-panel erp-workspace-panel" data-invoice-settings-form>
      <div class="preview-heading compact">
        <div>
          <h4>Invoice Settings</h4>
          <p>Configure the sales invoice form for this business. Applies to all users.</p>
        </div>
        <button class="secondary" type="button" data-business-action="invoice-back">← Back to list</button>
      </div>

      <h5 class="settings-section-title">Form fields</h5>
      <p class="muted">Show, hide, or require the optional fields on the invoice form.</p>
      <div class="table-preview compact-table">
        <table>
          <thead><tr><th>Field</th><th>Show on form</th><th>Make mandatory</th></tr></thead>
          <tbody>${fieldRows}</tbody>
        </table>
      </div>

      <h5 class="settings-section-title">Invoice numbering</h5>
      <p class="muted">Tokens: <code>{PREFIX}</code> <code>{FY}</code> (2026-2027) <code>{FYSHORT}</code> (2026-27) <code>{SEQ}</code></p>
      <div class="invoice-form-grid">
        <label>Prefix<input type="text" data-numbering="prefix" value="${escapeHtml(n.prefix || "INV")}"></label>
        <label>Number format<input type="text" data-numbering="number_format" value="${escapeHtml(n.number_format || "{PREFIX}-{FY}-{SEQ}")}"></label>
        <label>Sequence digits<input type="number" data-numbering="seq_padding" min="1" max="12" value="${escapeHtml(n.seq_padding || 6)}"></label>
        <label>Start number<input type="number" data-numbering="start_number" min="1" value="${escapeHtml(n.start_number || 1)}"></label>
        <label class="invoice-inter-toggle"><input type="checkbox" data-numbering="reset_yearly" ${n.reset_yearly !== false ? "checked" : ""}> Reset sequence each financial year</label>
      </div>
      <p class="muted">Preview: <strong>${escapeHtml(invoiceNumberPreview())}</strong></p>

      <p class="muted settings-coming-soon">Custom fields and invoice branding / print template are coming in the next update.</p>

      <div class="invoice-form-actions">
        <button class="primary" type="button" data-business-action="save-invoice-settings">Save Settings</button>
        <button class="secondary" type="button" data-business-action="invoice-back">Cancel</button>
      </div>
    </div>
  `;
}

function renderBusinessSalesWorkspace() {
  if (salesView === "create") {
    return renderInvoiceCreateForm();
  }
  if (salesView === "detail") {
    return renderInvoiceDetail();
  }
  if (salesView === "settings") {
    return renderInvoiceSettingsPanel();
  }
  return `
    <div class="verification-panel erp-workspace-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Sales Invoices</h4>
          <p>GST invoices for customers. Each posting updates receivables, income, and output GST.</p>
        </div>
        <div class="invoice-detail-actions">
          ${isBusinessAdmin() ? `<button class="secondary" type="button" data-business-action="open-invoice-settings">⚙ Settings</button>` : ""}
          <button class="secondary" type="button" data-business-action="open-create-invoice">+ New Invoice</button>
        </div>
      </div>
      ${renderInvoiceListTable()}
    </div>
  `;
}

// ========== Business Module: Purchase Bills (Input GST / ITC) ==========

let purchaseView = "list"; // list | create | detail
let lastBusinessBills = [];
let lastBillDetail = null;
let billLineSeq = 0;
let billFormLines = [];
const billFormHeader = {
  vendor_party_id: "",
  bill_number: "",
  bill_date: todayIsoDate(),
  due_date: "",
  is_inter_state: false,
  expense_account_code: "51001",
  place_of_supply: "",
  notes: "",
};

function rerenderPurchaseIfActive() {
  if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "bills") {
    dashboardPreview.innerHTML = renderBusinessWorkspace();
  }
}

async function loadBusinessBills() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/bills?limit=100", { method: "GET" });
  if (result.ok) {
    lastBusinessBills = Array.isArray(result.payload?.items) ? result.payload.items : [];
  } else {
    lastBusinessBills = [];
    setLoginStatus("danger", "Unable to load bills", statusDetailText(result.payload?.detail) || `Bill list request failed with HTTP ${result.status}.`);
  }
  rerenderPurchaseIfActive();
  renderJson(apiOutput, { bills: { ok: result.ok, status: result.status, count: lastBusinessBills.length } });
}

function vendorPartyOptions() {
  return (Array.isArray(lastBusinessParties) ? lastBusinessParties : [])
    .filter((p) => ["vendor", "both"].includes(String(p.party_type || "").toLowerCase()));
}

function expenseAccountOptions() {
  return businessAccountsForSelection().filter((acc) => String(acc.code || "").startsWith("5"));
}

function syncBillFormFromDom() {
  const form = document.querySelector("[data-bill-form]");
  if (!form) return;
  const val = (sel) => form.querySelector(sel)?.value ?? "";
  billFormHeader.vendor_party_id = val("select[name='vendor_party_id']");
  billFormHeader.bill_number = val("input[name='bill_number']");
  billFormHeader.bill_date = val("input[name='bill_date']") || todayIsoDate();
  billFormHeader.due_date = val("input[name='due_date']");
  billFormHeader.is_inter_state = !!form.querySelector("input[name='is_inter_state']")?.checked;
  billFormHeader.expense_account_code = val("select[name='expense_account_code']") || "51001";
  billFormHeader.place_of_supply = val("input[name='place_of_supply']");
  billFormHeader.notes = val("textarea[name='notes']");
  billFormLines = Array.from(form.querySelectorAll("[data-bill-line]")).map((row) => ({
    id: row.getAttribute("data-bill-line"),
    description: row.querySelector("input[name='description']")?.value || "",
    hsn_sac: row.querySelector("input[name='hsn_sac']")?.value || "",
    quantity: row.querySelector("input[name='quantity']")?.value || "",
    rate: row.querySelector("input[name='rate']")?.value || "",
    gst_rate: row.querySelector("input[name='gst_rate']")?.value || "",
  }));
}

function updateBillTotalsDisplay() {
  const form = document.querySelector("[data-bill-form]");
  if (!form) return;
  const inter = !!form.querySelector("input[name='is_inter_state']")?.checked;
  let taxableTotal = 0, cgstTotal = 0, sgstTotal = 0, igstTotal = 0;
  form.querySelectorAll("[data-bill-line]").forEach((row) => {
    const c = computeInvoiceLine(
      row.querySelector("input[name='quantity']")?.value,
      row.querySelector("input[name='rate']")?.value,
      row.querySelector("input[name='gst_rate']")?.value,
      inter,
    );
    row.querySelector("[data-line-taxable]").textContent = formatCurrency(c.taxable);
    row.querySelector("[data-line-gst]").textContent = formatCurrency(c.cgst + c.sgst + c.igst);
    row.querySelector("[data-line-total]").textContent = formatCurrency(c.total);
    taxableTotal += c.taxable; cgstTotal += c.cgst; sgstTotal += c.sgst; igstTotal += c.igst;
  });
  const gstTotal = round2(cgstTotal + sgstTotal + igstTotal);
  const billTotal = round2(taxableTotal + gstTotal);
  const set = (sel, v) => { const el = form.querySelector(sel); if (el) el.textContent = formatCurrency(v); };
  set("[data-total-taxable]", taxableTotal);
  set("[data-total-cgst]", cgstTotal);
  set("[data-total-sgst]", sgstTotal);
  set("[data-total-igst]", igstTotal);
  set("[data-total-bill]", billTotal);
  const cgstRow = form.querySelector("[data-row-cgst]");
  const sgstRow = form.querySelector("[data-row-sgst]");
  const igstRow = form.querySelector("[data-row-igst]");
  if (cgstRow && sgstRow && igstRow) {
    cgstRow.hidden = inter;
    sgstRow.hidden = inter;
    igstRow.hidden = !inter;
  }
}

function setBusinessPurchaseView(view) {
  purchaseView = view;
  billReverseOpen = false;
  rerenderPurchaseIfActive();
  if (view === "create") {
    updateBillTotalsDisplay();
  }
}

function openBillCreate() {
  billFormLines = [{ id: `bl-${++billLineSeq}`, description: "", hsn_sac: "", quantity: "1", rate: "", gst_rate: "18" }];
  billFormHeader.vendor_party_id = "";
  billFormHeader.bill_number = "";
  billFormHeader.bill_date = todayIsoDate();
  billFormHeader.due_date = "";
  billFormHeader.is_inter_state = false;
  billFormHeader.expense_account_code = "51001";
  billFormHeader.place_of_supply = "";
  billFormHeader.notes = "";
  if (!Array.isArray(lastBusinessParties) || lastBusinessParties.length === 0) loadBusinessParties();
  if (!hasLoadedBusinessAccounts()) loadBusinessAccounts();
  setBusinessPurchaseView("create");
}

function addBillLine() {
  syncBillFormFromDom();
  billFormLines.push({ id: `bl-${++billLineSeq}`, description: "", hsn_sac: "", quantity: "1", rate: "", gst_rate: "18" });
  rerenderPurchaseIfActive();
  updateBillTotalsDisplay();
}

function removeBillLine(lineId) {
  syncBillFormFromDom();
  billFormLines = billFormLines.filter((l) => l.id !== lineId);
  if (billFormLines.length === 0) {
    billFormLines.push({ id: `bl-${++billLineSeq}`, description: "", hsn_sac: "", quantity: "1", rate: "", gst_rate: "18" });
  }
  rerenderPurchaseIfActive();
  updateBillTotalsDisplay();
}

async function submitBill() {
  syncBillFormFromDom();
  if (!billFormHeader.vendor_party_id) {
    setLoginStatus("warn", "Vendor required", "Select a vendor for this bill.");
    return;
  }
  if (!String(billFormHeader.bill_number || "").trim()) {
    setLoginStatus("warn", "Bill number required", "Enter the supplier's bill/invoice number.");
    return;
  }
  const lineItems = billFormLines
    .filter((l) => String(l.description).trim() && Number(l.quantity) > 0)
    .map((l) => ({
      description: String(l.description).trim(),
      hsn_sac: String(l.hsn_sac || "").trim() || null,
      quantity: String(Number(l.quantity)),
      rate: String(Number(l.rate || 0)),
      gst_rate: String(Number(l.gst_rate || 0)),
    }));
  if (lineItems.length === 0) {
    setLoginStatus("warn", "Add a line item", "Enter at least one line with a description and quantity.");
    return;
  }
  const body = {
    vendor_party_id: billFormHeader.vendor_party_id,
    bill_number: String(billFormHeader.bill_number).trim(),
    bill_date: billFormHeader.bill_date || todayIsoDate(),
    due_date: billFormHeader.due_date || null,
    is_inter_state: !!billFormHeader.is_inter_state,
    expense_account_code: billFormHeader.expense_account_code || "51001",
    place_of_supply: String(billFormHeader.place_of_supply || "").trim() || null,
    notes: String(billFormHeader.notes || "").trim() || null,
    line_items: lineItems,
  };
  const result = await apiRequest("mitrabooks", "/api/v1/business/bills", {
    method: "POST",
    headers: { "X-Idempotency-Key": `purchase-bill-${Date.now()}` },
    body: JSON.stringify(body),
  });
  if (result.ok) {
    setLoginStatus("ok", "Bill posted", `${result.payload?.bill_number || "Bill"} posted to the ledger.`);
    await loadBusinessBills();
    setBusinessPurchaseView("list");
  } else {
    setLoginStatus("danger", "Bill posting failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { create_bill: { ok: result.ok, status: result.status, detail: result.payload?.detail || null } });
}

async function openBillDetail(billId) {
  const result = await apiRequest("mitrabooks", `/api/v1/business/bills/${encodeURIComponent(billId)}`, { method: "GET" });
  if (result.ok) {
    lastBillDetail = result.payload;
    setBusinessPurchaseView("detail");
  } else {
    setLoginStatus("danger", "Unable to load bill", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { bill_detail: { ok: result.ok, status: result.status } });
}

async function cancelBill(billId, reversalDate) {
  const body = { reason: "Reversal" };
  if (reversalDate) body.cancel_date = reversalDate;
  const result = await apiRequest("mitrabooks", `/api/v1/business/bills/${encodeURIComponent(billId)}/cancel`, {
    method: "POST",
    headers: { "X-Idempotency-Key": `purchase-bill-cancel-${billId}-${reversalDate || "today"}` },
    body: JSON.stringify(body),
  });
  if (result.ok) {
    billReverseOpen = false;
    setLoginStatus("ok", "Bill reversed", "A reversing journal entry was posted.");
    await loadBusinessBills();
    if (lastBillDetail && lastBillDetail.bill_id === billId) {
      lastBillDetail = result.payload;
    }
    rerenderPurchaseIfActive();
  } else {
    setLoginStatus("danger", "Reverse failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { cancel_bill: { ok: result.ok, status: result.status } });
}

function renderBillListTable() {
  const rows = lastBusinessBills;
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Bill #</th>
            <th>Date</th>
            <th>Vendor</th>
            <th class="amount">Taxable</th>
            <th class="amount">ITC</th>
            <th class="amount">Total</th>
            <th>Status</th>
            <th>Open</th>
          </tr>
        </thead>
        <tbody>
          ${rows.length ? rows.map((b) => `
            <tr>
              <td>${escapeHtml(b.bill_number || "")}</td>
              <td>${escapeHtml(b.bill_date || "")}</td>
              <td>${escapeHtml(b.vendor_name || b.vendor_party_id || "")}</td>
              <td class="amount">${escapeHtml(formatCurrency(b.taxable_total || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(b.gst_total || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(b.bill_total || 0))}</td>
              <td>${invoiceStatusPill(b.status)}</td>
              <td><button class="secondary" type="button" data-business-action="view-bill" data-bill-id="${escapeHtml(b.bill_id)}">View</button></td>
            </tr>
          `).join("") : `<tr><td colspan="8" class="muted">No bills yet. Record your first vendor bill.</td></tr>`}
        </tbody>
      </table>
    </div>
  `;
}

function renderBillCreateForm() {
  const vendors = vendorPartyOptions();
  const expenseAccounts = expenseAccountOptions();
  const lineRows = billFormLines.map((l) => `
    <tr data-bill-line="${escapeHtml(l.id)}">
      <td><input type="text" name="description" value="${escapeHtml(l.description)}" placeholder="Item / service"></td>
      <td><input type="text" name="hsn_sac" value="${escapeHtml(l.hsn_sac)}" placeholder="HSN/SAC"></td>
      <td><input type="number" name="quantity" value="${escapeHtml(l.quantity)}" min="0" step="any"></td>
      <td><input type="number" name="rate" value="${escapeHtml(l.rate)}" min="0" step="any" placeholder="0.00"></td>
      <td><input type="number" name="gst_rate" value="${escapeHtml(l.gst_rate)}" min="0" max="100" step="any"></td>
      <td class="amount" data-line-taxable>—</td>
      <td class="amount" data-line-gst>—</td>
      <td class="amount" data-line-total>—</td>
      <td><button class="secondary" type="button" data-business-action="remove-bill-line" data-line-id="${escapeHtml(l.id)}">✕</button></td>
    </tr>
  `).join("");

  return `
    <div class="verification-panel erp-workspace-panel" data-bill-form>
      <div class="preview-heading compact">
        <div>
          <h4>New Purchase Bill</h4>
          <p>Record a vendor bill. It posts to expenses, input GST (ITC), and accounts payable automatically.</p>
        </div>
        <button class="secondary" type="button" data-business-action="bill-back">← Back to list</button>
      </div>
      <div class="invoice-form-grid">
        <label>Vendor
          <select name="vendor_party_id">
            <option value="">Select vendor</option>
            ${vendors.map((v) => `<option value="${escapeHtml(v.party_id)}" ${v.party_id === billFormHeader.vendor_party_id ? "selected" : ""}>${escapeHtml(v.party_name)}${v.gstin ? ` (${escapeHtml(v.gstin)})` : ""}</option>`).join("")}
          </select>
        </label>
        <label>Supplier bill no. *
          <input type="text" name="bill_number" value="${escapeHtml(billFormHeader.bill_number)}" placeholder="Vendor's invoice number">
        </label>
        <label>Bill date
          <input type="date" name="bill_date" value="${escapeHtml(billFormHeader.bill_date)}">
        </label>
        <label>Due date
          <input type="date" name="due_date" value="${escapeHtml(billFormHeader.due_date)}">
        </label>
        <label>Expense account
          <select name="expense_account_code">
            ${expenseAccounts.length ? expenseAccounts.map((a) => `<option value="${escapeHtml(a.code)}" ${a.code === billFormHeader.expense_account_code ? "selected" : ""}>${escapeHtml(`${a.code} - ${a.name}`)}</option>`).join("") : `<option value="51001" selected>51001 - Purchases</option>`}
          </select>
        </label>
        <label>Place of supply
          <input type="text" name="place_of_supply" value="${escapeHtml(billFormHeader.place_of_supply)}" placeholder="State / code">
        </label>
        <label class="invoice-inter-toggle">
          <input type="checkbox" name="is_inter_state" ${billFormHeader.is_inter_state ? "checked" : ""}>
          Inter-state supply (IGST)
        </label>
      </div>

      <div class="table-preview compact-table invoice-lines">
        <table>
          <thead>
            <tr>
              <th>Description</th>
              <th>HSN/SAC</th>
              <th>Qty</th>
              <th>Rate</th>
              <th>GST %</th>
              <th class="amount">Taxable</th>
              <th class="amount">ITC</th>
              <th class="amount">Total</th>
              <th></th>
            </tr>
          </thead>
          <tbody>${lineRows}</tbody>
        </table>
      </div>
      <button class="secondary" type="button" data-business-action="add-bill-line">+ Add line</button>

      <div class="invoice-totals">
        <div><span>Taxable</span><strong data-total-taxable>${formatCurrency(0)}</strong></div>
        <div data-row-cgst ${billFormHeader.is_inter_state ? "hidden" : ""}><span>Input CGST</span><strong data-total-cgst>${formatCurrency(0)}</strong></div>
        <div data-row-sgst ${billFormHeader.is_inter_state ? "hidden" : ""}><span>Input SGST</span><strong data-total-sgst>${formatCurrency(0)}</strong></div>
        <div data-row-igst ${billFormHeader.is_inter_state ? "" : "hidden"}><span>Input IGST</span><strong data-total-igst>${formatCurrency(0)}</strong></div>
        <div class="invoice-grand"><span>Bill total</span><strong data-total-bill>${formatCurrency(0)}</strong></div>
      </div>

      <label class="invoice-notes">Notes
        <textarea name="notes" rows="2" placeholder="Optional notes">${escapeHtml(billFormHeader.notes)}</textarea>
      </label>

      <div class="invoice-form-actions">
        <button class="primary" type="button" data-business-action="save-bill">Post Bill</button>
        <button class="secondary" type="button" data-business-action="bill-back">Cancel</button>
      </div>
    </div>
  `;
}

function renderBillDetail() {
  const b = lastBillDetail;
  if (!b) {
    return `<div class="verification-panel erp-workspace-panel"><p class="muted">Bill not found.</p></div>`;
  }
  const lines = Array.isArray(b.line_items) ? b.line_items : [];
  const taxRow = b.is_inter_state
    ? `<div><span>Input IGST</span><strong>${formatCurrency(b.igst_total || 0)}</strong></div>`
    : `<div><span>Input CGST</span><strong>${formatCurrency(b.cgst_total || 0)}</strong></div><div><span>Input SGST</span><strong>${formatCurrency(b.sgst_total || 0)}</strong></div>`;
  return `
    <div class="verification-panel erp-workspace-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Bill ${escapeHtml(b.bill_number || "")} ${invoiceStatusPill(b.status)}</h4>
          <p>${escapeHtml(b.vendor_name || b.vendor_party_id || "")}${b.vendor_gstin ? ` · ${escapeHtml(b.vendor_gstin)}` : ""} · ${escapeHtml(b.bill_date || "")}${b.due_date ? ` · due ${escapeHtml(b.due_date)}` : ""}</p>
        </div>
        <div class="invoice-detail-actions">
          <button class="secondary" type="button" data-business-action="bill-back">← Back to list</button>
          ${String(b.status).toLowerCase() === "posted" && !billReverseOpen ? `<button class="secondary" type="button" data-business-action="begin-reverse-bill">Reverse Bill</button>` : ""}
        </div>
      </div>
      ${String(b.status).toLowerCase() === "posted" && billReverseOpen ? reversalPanel("bill", b.bill_id, b.bill_date) : ""}
      <p class="muted">${escapeHtml(b.is_inter_state ? "Inter-state supply (IGST input)" : "Intra-state supply (CGST + SGST input)")}</p>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr>
              <th>Description</th>
              <th>HSN/SAC</th>
              <th class="amount">Qty</th>
              <th class="amount">Rate</th>
              <th class="amount">GST %</th>
              <th class="amount">Taxable</th>
              <th class="amount">Total</th>
            </tr>
          </thead>
          <tbody>
            ${lines.map((l) => `
              <tr>
                <td>${escapeHtml(l.description || "")}</td>
                <td>${escapeHtml(l.hsn_sac || "")}</td>
                <td class="amount">${escapeHtml(l.quantity || "")}</td>
                <td class="amount">${escapeHtml(formatCurrency(l.rate || 0))}</td>
                <td class="amount">${escapeHtml(String(l.gst_rate || 0))}%</td>
                <td class="amount">${escapeHtml(formatCurrency(l.taxable_amount || 0))}</td>
                <td class="amount">${escapeHtml(formatCurrency(l.line_total || 0))}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
      <div class="invoice-totals">
        <div><span>Taxable</span><strong>${formatCurrency(b.taxable_total || 0)}</strong></div>
        ${taxRow}
        <div class="invoice-grand"><span>Bill total</span><strong>${formatCurrency(b.bill_total || 0)}</strong></div>
      </div>
      ${b.notes ? `<p class="muted">${escapeHtml(b.notes)}</p>` : ""}
      ${String(b.status).toLowerCase() === "cancelled" ? `<p class="muted">Reversed${b.cancel_reason ? `: ${escapeHtml(b.cancel_reason)}` : ""}. Reversing journal entry #${escapeHtml(b.reversal_journal_entry_id || "")} posted.</p>` : ""}
    </div>
  `;
}

function renderBusinessPurchaseWorkspace() {
  if (purchaseView === "create") {
    return renderBillCreateForm();
  }
  if (purchaseView === "detail") {
    return renderBillDetail();
  }
  return `
    <div class="verification-panel erp-workspace-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Purchase Bills</h4>
          <p>Vendor bills with input GST. Each posting updates expenses, ITC, and accounts payable.</p>
        </div>
        <button class="secondary" type="button" data-business-action="open-create-bill">+ New Bill</button>
      </div>
      ${renderBillListTable()}
    </div>
  `;
}

// ========== Business Module: Credit Notes (sales GST adjustment) ==========

let creditNoteView = "list"; // list | create | detail
let lastCreditNotes = [];
let lastCreditNoteDetail = null;
let cnLineSeq = 0;
let cnFormLines = [];
let cnReverseOpen = false;
const CN_REASONS = [
  ["sales_return", "Sales return"],
  ["discount", "Post-sale discount"],
  ["price_revision", "Price revision (downward)"],
  ["deficiency", "Deficiency in service/goods"],
  ["other", "Other"],
];
const cnFormHeader = {
  customer_party_id: "",
  note_date: todayIsoDate(),
  original_invoice_number: "",
  reason: "sales_return",
  is_inter_state: false,
  income_account_code: "41001",
  place_of_supply: "",
  notes: "",
};

function rerenderCreditNoteIfActive() {
  if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "credit-notes") {
    dashboardPreview.innerHTML = renderBusinessWorkspace();
  }
}

async function loadCreditNotes() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/credit-notes?limit=100", { method: "GET" });
  lastCreditNotes = result.ok && Array.isArray(result.payload?.items) ? result.payload.items : [];
  if (!result.ok) setLoginStatus("danger", "Unable to load credit notes", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  rerenderCreditNoteIfActive();
  renderJson(apiOutput, { credit_notes: { ok: result.ok, count: lastCreditNotes.length } });
}

function syncCnFormFromDom() {
  const form = document.querySelector("[data-cn-form]");
  if (!form) return;
  const val = (sel) => form.querySelector(sel)?.value ?? "";
  cnFormHeader.customer_party_id = val("select[name='customer_party_id']");
  cnFormHeader.note_date = val("input[name='note_date']") || todayIsoDate();
  cnFormHeader.original_invoice_number = val("input[name='original_invoice_number']");
  cnFormHeader.reason = val("select[name='reason']") || "sales_return";
  cnFormHeader.is_inter_state = !!form.querySelector("input[name='is_inter_state']")?.checked;
  cnFormHeader.income_account_code = val("select[name='income_account_code']") || "41001";
  cnFormHeader.place_of_supply = val("input[name='place_of_supply']");
  cnFormHeader.notes = val("textarea[name='notes']");
  cnFormLines = Array.from(form.querySelectorAll("[data-cn-line]")).map((row) => ({
    id: row.getAttribute("data-cn-line"),
    description: row.querySelector("input[name='description']")?.value || "",
    hsn_sac: row.querySelector("input[name='hsn_sac']")?.value || "",
    quantity: row.querySelector("input[name='quantity']")?.value || "",
    rate: row.querySelector("input[name='rate']")?.value || "",
    gst_rate: row.querySelector("input[name='gst_rate']")?.value || "",
  }));
}

function updateCnTotalsDisplay() {
  const form = document.querySelector("[data-cn-form]");
  if (!form) return;
  const inter = !!form.querySelector("input[name='is_inter_state']")?.checked;
  let taxableTotal = 0, cgstTotal = 0, sgstTotal = 0, igstTotal = 0;
  form.querySelectorAll("[data-cn-line]").forEach((row) => {
    const c = computeInvoiceLine(
      row.querySelector("input[name='quantity']")?.value,
      row.querySelector("input[name='rate']")?.value,
      row.querySelector("input[name='gst_rate']")?.value,
      inter,
    );
    row.querySelector("[data-line-taxable]").textContent = formatCurrency(c.taxable);
    row.querySelector("[data-line-gst]").textContent = formatCurrency(c.cgst + c.sgst + c.igst);
    row.querySelector("[data-line-total]").textContent = formatCurrency(c.total);
    taxableTotal += c.taxable; cgstTotal += c.cgst; sgstTotal += c.sgst; igstTotal += c.igst;
  });
  const gstTotal = round2(cgstTotal + sgstTotal + igstTotal);
  const noteTotal = round2(taxableTotal + gstTotal);
  const set = (sel, v) => { const el = form.querySelector(sel); if (el) el.textContent = formatCurrency(v); };
  set("[data-total-taxable]", taxableTotal);
  set("[data-total-cgst]", cgstTotal);
  set("[data-total-sgst]", sgstTotal);
  set("[data-total-igst]", igstTotal);
  set("[data-total-note]", noteTotal);
  const cgstRow = form.querySelector("[data-row-cgst]");
  const sgstRow = form.querySelector("[data-row-sgst]");
  const igstRow = form.querySelector("[data-row-igst]");
  if (cgstRow && sgstRow && igstRow) {
    cgstRow.hidden = inter;
    sgstRow.hidden = inter;
    igstRow.hidden = !inter;
  }
}

function setCreditNoteView(view) {
  creditNoteView = view;
  cnReverseOpen = false;
  rerenderCreditNoteIfActive();
  if (view === "create") {
    updateCnTotalsDisplay();
  }
}

function openCreditNoteCreate() {
  cnFormLines = [{ id: `cn-${++cnLineSeq}`, description: "", hsn_sac: "", quantity: "1", rate: "", gst_rate: "18" }];
  cnFormHeader.customer_party_id = "";
  cnFormHeader.note_date = todayIsoDate();
  cnFormHeader.original_invoice_number = "";
  cnFormHeader.reason = "sales_return";
  cnFormHeader.is_inter_state = false;
  cnFormHeader.income_account_code = "41001";
  cnFormHeader.place_of_supply = "";
  cnFormHeader.notes = "";
  if (!Array.isArray(lastBusinessParties) || lastBusinessParties.length === 0) loadBusinessParties();
  if (!hasLoadedBusinessAccounts()) loadBusinessAccounts();
  setCreditNoteView("create");
}

function addCnLine() {
  syncCnFormFromDom();
  cnFormLines.push({ id: `cn-${++cnLineSeq}`, description: "", hsn_sac: "", quantity: "1", rate: "", gst_rate: "18" });
  rerenderCreditNoteIfActive();
  updateCnTotalsDisplay();
}

function removeCnLine(lineId) {
  syncCnFormFromDom();
  cnFormLines = cnFormLines.filter((l) => l.id !== lineId);
  if (cnFormLines.length === 0) {
    cnFormLines.push({ id: `cn-${++cnLineSeq}`, description: "", hsn_sac: "", quantity: "1", rate: "", gst_rate: "18" });
  }
  rerenderCreditNoteIfActive();
  updateCnTotalsDisplay();
}

async function submitCreditNote() {
  syncCnFormFromDom();
  if (!cnFormHeader.customer_party_id) {
    setLoginStatus("warn", "Customer required", "Select the customer for this credit note.");
    return;
  }
  const lineItems = cnFormLines
    .filter((l) => String(l.description).trim() && Number(l.quantity) > 0)
    .map((l) => ({
      description: String(l.description).trim(),
      hsn_sac: String(l.hsn_sac || "").trim() || null,
      quantity: String(Number(l.quantity)),
      rate: String(Number(l.rate || 0)),
      gst_rate: String(Number(l.gst_rate || 0)),
    }));
  if (lineItems.length === 0) {
    setLoginStatus("warn", "Add a line item", "Enter at least one line with a description and quantity.");
    return;
  }
  const body = {
    customer_party_id: cnFormHeader.customer_party_id,
    note_date: cnFormHeader.note_date || todayIsoDate(),
    original_invoice_number: String(cnFormHeader.original_invoice_number || "").trim() || null,
    reason: cnFormHeader.reason || "sales_return",
    is_inter_state: !!cnFormHeader.is_inter_state,
    income_account_code: cnFormHeader.income_account_code || "41001",
    place_of_supply: String(cnFormHeader.place_of_supply || "").trim() || null,
    notes: String(cnFormHeader.notes || "").trim() || null,
    line_items: lineItems,
  };
  const result = await apiRequest("mitrabooks", "/api/v1/business/credit-notes", {
    method: "POST",
    headers: { "X-Idempotency-Key": `credit-note-${Date.now()}` },
    body: JSON.stringify(body),
  });
  if (result.ok) {
    setLoginStatus("ok", "Credit note posted", `${result.payload?.credit_note_number || "Credit note"} posted to the ledger.`);
    await loadCreditNotes();
    setCreditNoteView("list");
  } else {
    setLoginStatus("danger", "Credit note failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { create_credit_note: { ok: result.ok, status: result.status, detail: result.payload?.detail || null } });
}

async function openCreditNoteDetail(noteId) {
  const result = await apiRequest("mitrabooks", `/api/v1/business/credit-notes/${encodeURIComponent(noteId)}`, { method: "GET" });
  if (result.ok) {
    lastCreditNoteDetail = result.payload;
    setCreditNoteView("detail");
  } else {
    setLoginStatus("danger", "Unable to load credit note", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { credit_note_detail: { ok: result.ok, status: result.status } });
}

async function cancelCreditNote(noteId, reversalDate) {
  const body = { reason: "Reversal" };
  if (reversalDate) body.cancel_date = reversalDate;
  const result = await apiRequest("mitrabooks", `/api/v1/business/credit-notes/${encodeURIComponent(noteId)}/cancel`, {
    method: "POST",
    headers: { "X-Idempotency-Key": `credit-note-cancel-${noteId}-${reversalDate || "today"}` },
    body: JSON.stringify(body),
  });
  if (result.ok) {
    cnReverseOpen = false;
    setLoginStatus("ok", "Credit note reversed", "A reversing journal entry was posted.");
    await loadCreditNotes();
    if (lastCreditNoteDetail && lastCreditNoteDetail.credit_note_id === noteId) {
      lastCreditNoteDetail = result.payload;
    }
    rerenderCreditNoteIfActive();
  } else {
    setLoginStatus("danger", "Reverse failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { cancel_credit_note: { ok: result.ok, status: result.status } });
}

function cnReasonLabel(value) {
  const found = CN_REASONS.find((r) => r[0] === value);
  return found ? found[1] : (value || "");
}

function renderCnListTable() {
  const rows = lastCreditNotes;
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Credit Note #</th>
            <th>Date</th>
            <th>Customer</th>
            <th>Against</th>
            <th class="amount">Taxable</th>
            <th class="amount">GST</th>
            <th class="amount">Total</th>
            <th>Status</th>
            <th>Open</th>
          </tr>
        </thead>
        <tbody>
          ${rows.length ? rows.map((n) => `
            <tr>
              <td>${escapeHtml(n.credit_note_number || "")}</td>
              <td>${escapeHtml(n.note_date || "")}</td>
              <td>${escapeHtml(n.customer_name || n.customer_party_id || "")}</td>
              <td>${escapeHtml(n.original_invoice_number || "—")}</td>
              <td class="amount">${escapeHtml(formatCurrency(n.taxable_total || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(n.gst_total || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(n.note_total || 0))}</td>
              <td>${invoiceStatusPill(n.status)}</td>
              <td><button class="secondary" type="button" data-business-action="view-credit-note" data-cn-id="${escapeHtml(n.credit_note_id)}">View</button></td>
            </tr>
          `).join("") : `<tr><td colspan="9" class="muted">No credit notes yet.</td></tr>`}
        </tbody>
      </table>
    </div>
  `;
}

function renderCreditNoteCreateForm() {
  const customers = customerPartyOptions();
  const incomeAccounts = incomeAccountOptions();
  const lineRows = cnFormLines.map((l) => `
    <tr data-cn-line="${escapeHtml(l.id)}">
      <td><input type="text" name="description" value="${escapeHtml(l.description)}" placeholder="Item / service"></td>
      <td><input type="text" name="hsn_sac" value="${escapeHtml(l.hsn_sac)}" placeholder="HSN/SAC"></td>
      <td><input type="number" name="quantity" value="${escapeHtml(l.quantity)}" min="0" step="any"></td>
      <td><input type="number" name="rate" value="${escapeHtml(l.rate)}" min="0" step="any" placeholder="0.00"></td>
      <td><input type="number" name="gst_rate" value="${escapeHtml(l.gst_rate)}" min="0" max="100" step="any"></td>
      <td class="amount" data-line-taxable>—</td>
      <td class="amount" data-line-gst>—</td>
      <td class="amount" data-line-total>—</td>
      <td><button class="secondary" type="button" data-business-action="remove-cn-line" data-line-id="${escapeHtml(l.id)}">✕</button></td>
    </tr>
  `).join("");

  return `
    <div class="verification-panel erp-workspace-panel" data-cn-form>
      <div class="preview-heading compact">
        <div>
          <h4>New Credit Note</h4>
          <p>Reduce a customer's invoice (return, discount, or price revision). Reduces output GST and receivables.</p>
        </div>
        <button class="secondary" type="button" data-business-action="cn-back">← Back to list</button>
      </div>
      <div class="invoice-form-grid">
        <label>Customer
          <select name="customer_party_id">
            <option value="">Select customer</option>
            ${customers.map((c) => `<option value="${escapeHtml(c.party_id)}" ${c.party_id === cnFormHeader.customer_party_id ? "selected" : ""}>${escapeHtml(c.party_name)}${c.gstin ? ` (${escapeHtml(c.gstin)})` : ""}</option>`).join("")}
          </select>
        </label>
        <label>Note date
          <input type="date" name="note_date" value="${escapeHtml(cnFormHeader.note_date)}">
        </label>
        <label>Against invoice #
          <input type="text" name="original_invoice_number" value="${escapeHtml(cnFormHeader.original_invoice_number)}" placeholder="Original invoice number">
        </label>
        <label>Reason
          <select name="reason">
            ${CN_REASONS.map(([v, lbl]) => `<option value="${escapeHtml(v)}" ${v === cnFormHeader.reason ? "selected" : ""}>${escapeHtml(lbl)}</option>`).join("")}
          </select>
        </label>
        <label>Income account
          <select name="income_account_code">
            ${incomeAccounts.length ? incomeAccounts.map((a) => `<option value="${escapeHtml(a.code)}" ${a.code === cnFormHeader.income_account_code ? "selected" : ""}>${escapeHtml(`${a.code} - ${a.name}`)}</option>`).join("") : `<option value="41001" selected>41001 - Sales</option>`}
          </select>
        </label>
        <label>Place of supply
          <input type="text" name="place_of_supply" value="${escapeHtml(cnFormHeader.place_of_supply)}" placeholder="State / code">
        </label>
        <label class="invoice-inter-toggle">
          <input type="checkbox" name="is_inter_state" ${cnFormHeader.is_inter_state ? "checked" : ""}>
          Inter-state supply (IGST)
        </label>
      </div>

      <div class="table-preview compact-table invoice-lines">
        <table>
          <thead>
            <tr>
              <th>Description</th><th>HSN/SAC</th><th>Qty</th><th>Rate</th><th>GST %</th>
              <th class="amount">Taxable</th><th class="amount">GST</th><th class="amount">Total</th><th></th>
            </tr>
          </thead>
          <tbody>${lineRows}</tbody>
        </table>
      </div>
      <button class="secondary" type="button" data-business-action="add-cn-line">+ Add line</button>

      <div class="invoice-totals">
        <div><span>Taxable</span><strong data-total-taxable>${formatCurrency(0)}</strong></div>
        <div data-row-cgst ${cnFormHeader.is_inter_state ? "hidden" : ""}><span>CGST</span><strong data-total-cgst>${formatCurrency(0)}</strong></div>
        <div data-row-sgst ${cnFormHeader.is_inter_state ? "hidden" : ""}><span>SGST</span><strong data-total-sgst>${formatCurrency(0)}</strong></div>
        <div data-row-igst ${cnFormHeader.is_inter_state ? "" : "hidden"}><span>IGST</span><strong data-total-igst>${formatCurrency(0)}</strong></div>
        <div class="invoice-grand"><span>Credit note total</span><strong data-total-note>${formatCurrency(0)}</strong></div>
      </div>

      <label class="invoice-notes">Notes
        <textarea name="notes" rows="2" placeholder="Optional notes">${escapeHtml(cnFormHeader.notes)}</textarea>
      </label>

      <div class="invoice-form-actions">
        <button class="primary" type="button" data-business-action="save-credit-note">Post Credit Note</button>
        <button class="secondary" type="button" data-business-action="cn-back">Cancel</button>
      </div>
    </div>
  `;
}

function renderCreditNoteDetail() {
  const n = lastCreditNoteDetail;
  if (!n) {
    return `<div class="verification-panel erp-workspace-panel"><p class="muted">Credit note not found.</p></div>`;
  }
  const lines = Array.isArray(n.line_items) ? n.line_items : [];
  const taxRow = n.is_inter_state
    ? `<div><span>IGST</span><strong>${formatCurrency(n.igst_total || 0)}</strong></div>`
    : `<div><span>CGST</span><strong>${formatCurrency(n.cgst_total || 0)}</strong></div><div><span>SGST</span><strong>${formatCurrency(n.sgst_total || 0)}</strong></div>`;
  return `
    <div class="verification-panel erp-workspace-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Credit Note ${escapeHtml(n.credit_note_number || "")} ${invoiceStatusPill(n.status)}</h4>
          <p>${escapeHtml(n.customer_name || n.customer_party_id || "")}${n.customer_gstin ? ` · ${escapeHtml(n.customer_gstin)}` : ""} · ${escapeHtml(n.note_date || "")}${n.original_invoice_number ? ` · against ${escapeHtml(n.original_invoice_number)}` : ""}</p>
        </div>
        <div class="invoice-detail-actions">
          <button class="secondary" type="button" data-business-action="cn-back">← Back to list</button>
          ${String(n.status).toLowerCase() === "posted" && !cnReverseOpen ? `<button class="secondary" type="button" data-business-action="begin-reverse-cn">Reverse</button>` : ""}
        </div>
      </div>
      ${String(n.status).toLowerCase() === "posted" && cnReverseOpen ? reversalPanel("cn", n.credit_note_id, n.note_date) : ""}
      <p class="muted">${escapeHtml(cnReasonLabel(n.reason))}${n.is_inter_state ? " · Inter-state (IGST)" : " · Intra-state (CGST + SGST)"}</p>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr><th>Description</th><th>HSN/SAC</th><th class="amount">Qty</th><th class="amount">Rate</th><th class="amount">GST %</th><th class="amount">Taxable</th><th class="amount">Total</th></tr>
          </thead>
          <tbody>
            ${lines.map((l) => `
              <tr>
                <td>${escapeHtml(l.description || "")}</td>
                <td>${escapeHtml(l.hsn_sac || "")}</td>
                <td class="amount">${escapeHtml(l.quantity || "")}</td>
                <td class="amount">${escapeHtml(formatCurrency(l.rate || 0))}</td>
                <td class="amount">${escapeHtml(String(l.gst_rate || 0))}%</td>
                <td class="amount">${escapeHtml(formatCurrency(l.taxable_amount || 0))}</td>
                <td class="amount">${escapeHtml(formatCurrency(l.line_total || 0))}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
      <div class="invoice-totals">
        <div><span>Taxable</span><strong>${formatCurrency(n.taxable_total || 0)}</strong></div>
        ${taxRow}
        <div class="invoice-grand"><span>Credit note total</span><strong>${formatCurrency(n.note_total || 0)}</strong></div>
      </div>
      ${n.notes ? `<p class="muted">${escapeHtml(n.notes)}</p>` : ""}
      ${String(n.status).toLowerCase() === "cancelled" ? `<p class="muted">Reversed${n.cancel_reason ? `: ${escapeHtml(n.cancel_reason)}` : ""}. Reversing journal entry #${escapeHtml(n.reversal_journal_entry_id || "")} posted.</p>` : ""}
    </div>
  `;
}

function renderBusinessCreditNoteWorkspace() {
  if (creditNoteView === "create") {
    return renderCreditNoteCreateForm();
  }
  if (creditNoteView === "detail") {
    return renderCreditNoteDetail();
  }
  return `
    <div class="verification-panel erp-workspace-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Credit Notes</h4>
          <p>Sales-side GST adjustments against invoices (returns, discounts, price revisions).</p>
        </div>
        <button class="secondary" type="button" data-business-action="open-create-credit-note">+ New Credit Note</button>
      </div>
      ${renderCnListTable()}
    </div>
  `;
}

// ========== Business Module: Debit Notes (purchase GST adjustment) ==========

let debitNoteView = "list"; // list | create | detail
let lastDebitNotes = [];
let lastDebitNoteDetail = null;
let dnLineSeq = 0;
let dnFormLines = [];
let dnReverseOpen = false;
const DN_REASONS = [
  ["purchase_return", "Purchase return"],
  ["rejected_goods", "Rejected goods"],
  ["price_revision", "Price revision (downward)"],
  ["deficiency", "Deficiency in service/goods"],
  ["other", "Other"],
];
const dnFormHeader = {
  vendor_party_id: "",
  note_date: todayIsoDate(),
  original_bill_number: "",
  reason: "purchase_return",
  is_inter_state: false,
  expense_account_code: "51001",
  place_of_supply: "",
  notes: "",
};

function rerenderDebitNoteIfActive() {
  if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "debit-notes") {
    dashboardPreview.innerHTML = renderBusinessWorkspace();
  }
}

async function loadDebitNotes() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/debit-notes?limit=100", { method: "GET" });
  lastDebitNotes = result.ok && Array.isArray(result.payload?.items) ? result.payload.items : [];
  if (!result.ok) setLoginStatus("danger", "Unable to load debit notes", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  rerenderDebitNoteIfActive();
  renderJson(apiOutput, { debit_notes: { ok: result.ok, count: lastDebitNotes.length } });
}

function syncDnFormFromDom() {
  const form = document.querySelector("[data-dn-form]");
  if (!form) return;
  const val = (sel) => form.querySelector(sel)?.value ?? "";
  dnFormHeader.vendor_party_id = val("select[name='vendor_party_id']");
  dnFormHeader.note_date = val("input[name='note_date']") || todayIsoDate();
  dnFormHeader.original_bill_number = val("input[name='original_bill_number']");
  dnFormHeader.reason = val("select[name='reason']") || "purchase_return";
  dnFormHeader.is_inter_state = !!form.querySelector("input[name='is_inter_state']")?.checked;
  dnFormHeader.expense_account_code = val("select[name='expense_account_code']") || "51001";
  dnFormHeader.place_of_supply = val("input[name='place_of_supply']");
  dnFormHeader.notes = val("textarea[name='notes']");
  dnFormLines = Array.from(form.querySelectorAll("[data-dn-line]")).map((row) => ({
    id: row.getAttribute("data-dn-line"),
    description: row.querySelector("input[name='description']")?.value || "",
    hsn_sac: row.querySelector("input[name='hsn_sac']")?.value || "",
    quantity: row.querySelector("input[name='quantity']")?.value || "",
    rate: row.querySelector("input[name='rate']")?.value || "",
    gst_rate: row.querySelector("input[name='gst_rate']")?.value || "",
  }));
}

function updateDnTotalsDisplay() {
  const form = document.querySelector("[data-dn-form]");
  if (!form) return;
  const inter = !!form.querySelector("input[name='is_inter_state']")?.checked;
  let taxableTotal = 0, cgstTotal = 0, sgstTotal = 0, igstTotal = 0;
  form.querySelectorAll("[data-dn-line]").forEach((row) => {
    const c = computeInvoiceLine(
      row.querySelector("input[name='quantity']")?.value,
      row.querySelector("input[name='rate']")?.value,
      row.querySelector("input[name='gst_rate']")?.value,
      inter,
    );
    row.querySelector("[data-line-taxable]").textContent = formatCurrency(c.taxable);
    row.querySelector("[data-line-gst]").textContent = formatCurrency(c.cgst + c.sgst + c.igst);
    row.querySelector("[data-line-total]").textContent = formatCurrency(c.total);
    taxableTotal += c.taxable; cgstTotal += c.cgst; sgstTotal += c.sgst; igstTotal += c.igst;
  });
  const gstTotal = round2(cgstTotal + sgstTotal + igstTotal);
  const noteTotal = round2(taxableTotal + gstTotal);
  const set = (sel, v) => { const el = form.querySelector(sel); if (el) el.textContent = formatCurrency(v); };
  set("[data-total-taxable]", taxableTotal);
  set("[data-total-cgst]", cgstTotal);
  set("[data-total-sgst]", sgstTotal);
  set("[data-total-igst]", igstTotal);
  set("[data-total-note]", noteTotal);
  const cgstRow = form.querySelector("[data-row-cgst]");
  const sgstRow = form.querySelector("[data-row-sgst]");
  const igstRow = form.querySelector("[data-row-igst]");
  if (cgstRow && sgstRow && igstRow) {
    cgstRow.hidden = inter;
    sgstRow.hidden = inter;
    igstRow.hidden = !inter;
  }
}

function setDebitNoteView(view) {
  debitNoteView = view;
  dnReverseOpen = false;
  rerenderDebitNoteIfActive();
  if (view === "create") {
    updateDnTotalsDisplay();
  }
}

function openDebitNoteCreate() {
  dnFormLines = [{ id: `dn-${++dnLineSeq}`, description: "", hsn_sac: "", quantity: "1", rate: "", gst_rate: "18" }];
  dnFormHeader.vendor_party_id = "";
  dnFormHeader.note_date = todayIsoDate();
  dnFormHeader.original_bill_number = "";
  dnFormHeader.reason = "purchase_return";
  dnFormHeader.is_inter_state = false;
  dnFormHeader.expense_account_code = "51001";
  dnFormHeader.place_of_supply = "";
  dnFormHeader.notes = "";
  if (!Array.isArray(lastBusinessParties) || lastBusinessParties.length === 0) loadBusinessParties();
  if (!hasLoadedBusinessAccounts()) loadBusinessAccounts();
  setDebitNoteView("create");
}

function addDnLine() {
  syncDnFormFromDom();
  dnFormLines.push({ id: `dn-${++dnLineSeq}`, description: "", hsn_sac: "", quantity: "1", rate: "", gst_rate: "18" });
  rerenderDebitNoteIfActive();
  updateDnTotalsDisplay();
}

function removeDnLine(lineId) {
  syncDnFormFromDom();
  dnFormLines = dnFormLines.filter((l) => l.id !== lineId);
  if (dnFormLines.length === 0) {
    dnFormLines.push({ id: `dn-${++dnLineSeq}`, description: "", hsn_sac: "", quantity: "1", rate: "", gst_rate: "18" });
  }
  rerenderDebitNoteIfActive();
  updateDnTotalsDisplay();
}

async function submitDebitNote() {
  syncDnFormFromDom();
  if (!dnFormHeader.vendor_party_id) {
    setLoginStatus("warn", "Vendor required", "Select the vendor for this debit note.");
    return;
  }
  const lineItems = dnFormLines
    .filter((l) => String(l.description).trim() && Number(l.quantity) > 0)
    .map((l) => ({
      description: String(l.description).trim(),
      hsn_sac: String(l.hsn_sac || "").trim() || null,
      quantity: String(Number(l.quantity)),
      rate: String(Number(l.rate || 0)),
      gst_rate: String(Number(l.gst_rate || 0)),
    }));
  if (lineItems.length === 0) {
    setLoginStatus("warn", "Add a line item", "Enter at least one line with a description and quantity.");
    return;
  }
  const body = {
    vendor_party_id: dnFormHeader.vendor_party_id,
    note_date: dnFormHeader.note_date || todayIsoDate(),
    original_bill_number: String(dnFormHeader.original_bill_number || "").trim() || null,
    reason: dnFormHeader.reason || "purchase_return",
    is_inter_state: !!dnFormHeader.is_inter_state,
    expense_account_code: dnFormHeader.expense_account_code || "51001",
    place_of_supply: String(dnFormHeader.place_of_supply || "").trim() || null,
    notes: String(dnFormHeader.notes || "").trim() || null,
    line_items: lineItems,
  };
  const result = await apiRequest("mitrabooks", "/api/v1/business/debit-notes", {
    method: "POST",
    headers: { "X-Idempotency-Key": `debit-note-${Date.now()}` },
    body: JSON.stringify(body),
  });
  if (result.ok) {
    setLoginStatus("ok", "Debit note posted", `${result.payload?.debit_note_number || "Debit note"} posted to the ledger.`);
    await loadDebitNotes();
    setDebitNoteView("list");
  } else {
    setLoginStatus("danger", "Debit note failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { create_debit_note: { ok: result.ok, status: result.status, detail: result.payload?.detail || null } });
}

async function openDebitNoteDetail(noteId) {
  const result = await apiRequest("mitrabooks", `/api/v1/business/debit-notes/${encodeURIComponent(noteId)}`, { method: "GET" });
  if (result.ok) {
    lastDebitNoteDetail = result.payload;
    setDebitNoteView("detail");
  } else {
    setLoginStatus("danger", "Unable to load debit note", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { debit_note_detail: { ok: result.ok, status: result.status } });
}

async function cancelDebitNote(noteId, reversalDate) {
  const body = { reason: "Reversal" };
  if (reversalDate) body.cancel_date = reversalDate;
  const result = await apiRequest("mitrabooks", `/api/v1/business/debit-notes/${encodeURIComponent(noteId)}/cancel`, {
    method: "POST",
    headers: { "X-Idempotency-Key": `debit-note-cancel-${noteId}-${reversalDate || "today"}` },
    body: JSON.stringify(body),
  });
  if (result.ok) {
    dnReverseOpen = false;
    setLoginStatus("ok", "Debit note reversed", "A reversing journal entry was posted.");
    await loadDebitNotes();
    if (lastDebitNoteDetail && lastDebitNoteDetail.debit_note_id === noteId) {
      lastDebitNoteDetail = result.payload;
    }
    rerenderDebitNoteIfActive();
  } else {
    setLoginStatus("danger", "Reverse failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { cancel_debit_note: { ok: result.ok, status: result.status } });
}

function dnReasonLabel(value) {
  const found = DN_REASONS.find((r) => r[0] === value);
  return found ? found[1] : (value || "");
}

function renderDnListTable() {
  const rows = lastDebitNotes;
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Debit Note #</th><th>Date</th><th>Vendor</th><th>Against</th>
            <th class="amount">Taxable</th><th class="amount">ITC</th><th class="amount">Total</th><th>Status</th><th>Open</th>
          </tr>
        </thead>
        <tbody>
          ${rows.length ? rows.map((n) => `
            <tr>
              <td>${escapeHtml(n.debit_note_number || "")}</td>
              <td>${escapeHtml(n.note_date || "")}</td>
              <td>${escapeHtml(n.vendor_name || n.vendor_party_id || "")}</td>
              <td>${escapeHtml(n.original_bill_number || "—")}</td>
              <td class="amount">${escapeHtml(formatCurrency(n.taxable_total || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(n.gst_total || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(n.note_total || 0))}</td>
              <td>${invoiceStatusPill(n.status)}</td>
              <td><button class="secondary" type="button" data-business-action="view-debit-note" data-dn-id="${escapeHtml(n.debit_note_id)}">View</button></td>
            </tr>
          `).join("") : `<tr><td colspan="9" class="muted">No debit notes yet.</td></tr>`}
        </tbody>
      </table>
    </div>
  `;
}

function renderDebitNoteCreateForm() {
  const vendors = vendorPartyOptions();
  const expenseAccounts = expenseAccountOptions();
  const lineRows = dnFormLines.map((l) => `
    <tr data-dn-line="${escapeHtml(l.id)}">
      <td><input type="text" name="description" value="${escapeHtml(l.description)}" placeholder="Item / service"></td>
      <td><input type="text" name="hsn_sac" value="${escapeHtml(l.hsn_sac)}" placeholder="HSN/SAC"></td>
      <td><input type="number" name="quantity" value="${escapeHtml(l.quantity)}" min="0" step="any"></td>
      <td><input type="number" name="rate" value="${escapeHtml(l.rate)}" min="0" step="any" placeholder="0.00"></td>
      <td><input type="number" name="gst_rate" value="${escapeHtml(l.gst_rate)}" min="0" max="100" step="any"></td>
      <td class="amount" data-line-taxable>—</td>
      <td class="amount" data-line-gst>—</td>
      <td class="amount" data-line-total>—</td>
      <td><button class="secondary" type="button" data-business-action="remove-dn-line" data-line-id="${escapeHtml(l.id)}">✕</button></td>
    </tr>
  `).join("");

  return `
    <div class="verification-panel erp-workspace-panel" data-dn-form>
      <div class="preview-heading compact">
        <div>
          <h4>New Debit Note</h4>
          <p>Reduce a vendor bill (return, rejected goods, or price revision). Reduces input GST (ITC) and payables.</p>
        </div>
        <button class="secondary" type="button" data-business-action="dn-back">← Back to list</button>
      </div>
      <div class="invoice-form-grid">
        <label>Vendor
          <select name="vendor_party_id">
            <option value="">Select vendor</option>
            ${vendors.map((v) => `<option value="${escapeHtml(v.party_id)}" ${v.party_id === dnFormHeader.vendor_party_id ? "selected" : ""}>${escapeHtml(v.party_name)}${v.gstin ? ` (${escapeHtml(v.gstin)})` : ""}</option>`).join("")}
          </select>
        </label>
        <label>Note date
          <input type="date" name="note_date" value="${escapeHtml(dnFormHeader.note_date)}">
        </label>
        <label>Against bill #
          <input type="text" name="original_bill_number" value="${escapeHtml(dnFormHeader.original_bill_number)}" placeholder="Original supplier bill number">
        </label>
        <label>Reason
          <select name="reason">
            ${DN_REASONS.map(([v, lbl]) => `<option value="${escapeHtml(v)}" ${v === dnFormHeader.reason ? "selected" : ""}>${escapeHtml(lbl)}</option>`).join("")}
          </select>
        </label>
        <label>Expense account
          <select name="expense_account_code">
            ${expenseAccounts.length ? expenseAccounts.map((a) => `<option value="${escapeHtml(a.code)}" ${a.code === dnFormHeader.expense_account_code ? "selected" : ""}>${escapeHtml(`${a.code} - ${a.name}`)}</option>`).join("") : `<option value="51001" selected>51001 - Purchases</option>`}
          </select>
        </label>
        <label>Place of supply
          <input type="text" name="place_of_supply" value="${escapeHtml(dnFormHeader.place_of_supply)}" placeholder="State / code">
        </label>
        <label class="invoice-inter-toggle">
          <input type="checkbox" name="is_inter_state" ${dnFormHeader.is_inter_state ? "checked" : ""}>
          Inter-state supply (IGST)
        </label>
      </div>

      <div class="table-preview compact-table invoice-lines">
        <table>
          <thead>
            <tr>
              <th>Description</th><th>HSN/SAC</th><th>Qty</th><th>Rate</th><th>GST %</th>
              <th class="amount">Taxable</th><th class="amount">ITC</th><th class="amount">Total</th><th></th>
            </tr>
          </thead>
          <tbody>${lineRows}</tbody>
        </table>
      </div>
      <button class="secondary" type="button" data-business-action="add-dn-line">+ Add line</button>

      <div class="invoice-totals">
        <div><span>Taxable</span><strong data-total-taxable>${formatCurrency(0)}</strong></div>
        <div data-row-cgst ${dnFormHeader.is_inter_state ? "hidden" : ""}><span>Input CGST</span><strong data-total-cgst>${formatCurrency(0)}</strong></div>
        <div data-row-sgst ${dnFormHeader.is_inter_state ? "hidden" : ""}><span>Input SGST</span><strong data-total-sgst>${formatCurrency(0)}</strong></div>
        <div data-row-igst ${dnFormHeader.is_inter_state ? "" : "hidden"}><span>Input IGST</span><strong data-total-igst>${formatCurrency(0)}</strong></div>
        <div class="invoice-grand"><span>Debit note total</span><strong data-total-note>${formatCurrency(0)}</strong></div>
      </div>

      <label class="invoice-notes">Notes
        <textarea name="notes" rows="2" placeholder="Optional notes">${escapeHtml(dnFormHeader.notes)}</textarea>
      </label>

      <div class="invoice-form-actions">
        <button class="primary" type="button" data-business-action="save-debit-note">Post Debit Note</button>
        <button class="secondary" type="button" data-business-action="dn-back">Cancel</button>
      </div>
    </div>
  `;
}

function renderDebitNoteDetail() {
  const n = lastDebitNoteDetail;
  if (!n) {
    return `<div class="verification-panel erp-workspace-panel"><p class="muted">Debit note not found.</p></div>`;
  }
  const lines = Array.isArray(n.line_items) ? n.line_items : [];
  const taxRow = n.is_inter_state
    ? `<div><span>Input IGST</span><strong>${formatCurrency(n.igst_total || 0)}</strong></div>`
    : `<div><span>Input CGST</span><strong>${formatCurrency(n.cgst_total || 0)}</strong></div><div><span>Input SGST</span><strong>${formatCurrency(n.sgst_total || 0)}</strong></div>`;
  return `
    <div class="verification-panel erp-workspace-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Debit Note ${escapeHtml(n.debit_note_number || "")} ${invoiceStatusPill(n.status)}</h4>
          <p>${escapeHtml(n.vendor_name || n.vendor_party_id || "")}${n.vendor_gstin ? ` · ${escapeHtml(n.vendor_gstin)}` : ""} · ${escapeHtml(n.note_date || "")}${n.original_bill_number ? ` · against ${escapeHtml(n.original_bill_number)}` : ""}</p>
        </div>
        <div class="invoice-detail-actions">
          <button class="secondary" type="button" data-business-action="dn-back">← Back to list</button>
          ${String(n.status).toLowerCase() === "posted" && !dnReverseOpen ? `<button class="secondary" type="button" data-business-action="begin-reverse-dn">Reverse</button>` : ""}
        </div>
      </div>
      ${String(n.status).toLowerCase() === "posted" && dnReverseOpen ? reversalPanel("dn", n.debit_note_id, n.note_date) : ""}
      <p class="muted">${escapeHtml(dnReasonLabel(n.reason))}${n.is_inter_state ? " · Inter-state (IGST input)" : " · Intra-state (CGST + SGST input)"}</p>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr><th>Description</th><th>HSN/SAC</th><th class="amount">Qty</th><th class="amount">Rate</th><th class="amount">GST %</th><th class="amount">Taxable</th><th class="amount">Total</th></tr>
          </thead>
          <tbody>
            ${lines.map((l) => `
              <tr>
                <td>${escapeHtml(l.description || "")}</td>
                <td>${escapeHtml(l.hsn_sac || "")}</td>
                <td class="amount">${escapeHtml(l.quantity || "")}</td>
                <td class="amount">${escapeHtml(formatCurrency(l.rate || 0))}</td>
                <td class="amount">${escapeHtml(String(l.gst_rate || 0))}%</td>
                <td class="amount">${escapeHtml(formatCurrency(l.taxable_amount || 0))}</td>
                <td class="amount">${escapeHtml(formatCurrency(l.line_total || 0))}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
      <div class="invoice-totals">
        <div><span>Taxable</span><strong>${formatCurrency(n.taxable_total || 0)}</strong></div>
        ${taxRow}
        <div class="invoice-grand"><span>Debit note total</span><strong>${formatCurrency(n.note_total || 0)}</strong></div>
      </div>
      ${n.notes ? `<p class="muted">${escapeHtml(n.notes)}</p>` : ""}
      ${String(n.status).toLowerCase() === "cancelled" ? `<p class="muted">Reversed${n.cancel_reason ? `: ${escapeHtml(n.cancel_reason)}` : ""}. Reversing journal entry #${escapeHtml(n.reversal_journal_entry_id || "")} posted.</p>` : ""}
    </div>
  `;
}

function renderBusinessDebitNoteWorkspace() {
  if (debitNoteView === "create") {
    return renderDebitNoteCreateForm();
  }
  if (debitNoteView === "detail") {
    return renderDebitNoteDetail();
  }
  return `
    <div class="verification-panel erp-workspace-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Debit Notes</h4>
          <p>Purchase-side GST adjustments against vendor bills (returns, rejected goods, price revisions).</p>
        </div>
        <button class="secondary" type="button" data-business-action="open-create-debit-note">+ New Debit Note</button>
      </div>
      ${renderDnListTable()}
    </div>
  `;
}

// ========== Business Module: Typed Vouchers ==========

let lastBusinessVouchers = [];
let lastBusinessAccountsResult = null;
let lastModuleContext = null;
let voucherLineCounter = 0;
let lastBusinessDashboardStats = null;

const voucherLineState = [];

const MITRABOOKS_FALLBACK_ACCOUNTS = [
  { account_id: 11001, account_code: "11001", account_name: "Cash in Hand", account_type: "asset" },
  { account_id: 11010, account_code: "11010", account_name: "Bank Account", account_type: "asset" },
  { account_id: 12001, account_code: "12001", account_name: "Sundry Debtors", account_type: "asset" },
  { account_id: 13002, account_code: "13002", account_name: "Advance to Suppliers", account_type: "asset" },
  { account_id: 21001, account_code: "21001", account_name: "Sundry Creditors", account_type: "liability" },
  { account_id: 24001, account_code: "24001", account_name: "Advance from Customers", account_type: "liability" },
  { account_id: 41001, account_code: "41001", account_name: "Sales", account_type: "income" },
  { account_id: 41002, account_code: "41002", account_name: "Service Income", account_type: "income" },
  { account_id: 53004, account_code: "53004", account_name: "Office Expense", account_type: "expense" },
  { account_id: 54001, account_code: "54001", account_name: "Bank Charges", account_type: "expense" },
];

function normalizeBusinessAccount(acc) {
  const id = acc.account_id
    ?? acc.id
    ?? acc.accountId
    ?? acc.accountID
    ?? acc.ledger_id
    ?? acc.ledgerId
    ?? acc._id
    ?? acc.account_code
    ?? acc.code
    ?? "";
  const code = acc.account_code
    ?? acc.code
    ?? acc.accountCode
    ?? acc.ledger_code
    ?? acc.ledgerCode
    ?? acc.gl_code
    ?? acc.glCode
    ?? acc.number
    ?? acc.account_number
    ?? id
    ?? "";
  const name = acc.account_name
    ?? acc.name
    ?? acc.accountName
    ?? acc.ledger_name
    ?? acc.ledgerName
    ?? acc.title
    ?? "";
  return {
    id: String(id),
    code: String(code),
    name: String(name),
  };
}

function businessAccountLabel(account) {
  return `${account.code}${account.name ? " - " + account.name : ""}`.trim();
}

function businessAccountsForSelection() {
  const loaded = Array.isArray(lastBusinessAccounts) ? lastBusinessAccounts : [];
  const source = loaded.length > 0 ? loaded : MITRABOOKS_FALLBACK_ACCOUNTS;
  return source
    .map(normalizeBusinessAccount)
    .filter((acc) => acc.id && (acc.code || acc.name));
}

function hasLoadedBusinessAccounts() {
  return Array.isArray(lastBusinessAccounts) && lastBusinessAccounts.length > 0;
}

function findBusinessAccountById(accountId) {
  return businessAccountsForSelection()
    .find((acc) => String(acc.id) === String(accountId)) || null;
}

function accountIdForVoucherPayload(account) {
  if (!account || !hasLoadedBusinessAccounts()) return null;
  const parsed = Number(account.id);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function populateVoucherAccountSelect(select, selectedId = "") {
  if (!select) return;
  const accounts = businessAccountsForSelection();
  select.innerHTML = `<option value="">Select account code</option>`;
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

function populateAccountPickerSelect(fieldId, accounts, selectedId = "") {
  const select = document.querySelector(`.account-picker-select[data-field-id="${fieldId}"]`);
  if (!select) return;
  const rows = Array.isArray(accounts) && accounts.length > 0 ? accounts : businessAccountsForSelection();
  const currentValue = selectedId || select.value || "";
  select.innerHTML = `<option value="">${rows.length === 0 ? "No matching account code" : "Select account code"}</option>`;
  rows.forEach((account) => {
    const normalized = normalizeBusinessAccount(account);
    const option = document.createElement("option");
    option.value = normalized.id;
    option.textContent = businessAccountLabel(normalized);
    if (String(currentValue) === String(normalized.id)) {
      option.selected = true;
    }
    select.appendChild(option);
  });
}

function refreshVoucherAccountDatalist() {
  const datalist = document.getElementById("business-voucher-account-options");
  if (!datalist) return;
  const accounts = businessAccountsForSelection();
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
    status.textContent = "No tenant chart loaded. Showing default MitraBooks account codes until the chart of accounts API returns rows.";
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
  document.querySelectorAll(".account-picker-select").forEach((select) => {
    populateVoucherAccountSelect(select, select.value);
  });
}

function accountRowsFromPayload(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.items)) return payload.items;
  if (Array.isArray(payload?.accounts)) return payload.accounts;
  if (Array.isArray(payload?.data)) return payload.data;
  if (Array.isArray(payload?.rows)) return payload.rows;
  if (Array.isArray(payload?.result)) return payload.result;
  if (Array.isArray(payload?.data?.items)) return payload.data.items;
  if (Array.isArray(payload?.data?.accounts)) return payload.data.accounts;
  if (Array.isArray(payload?.data?.rows)) return payload.data.rows;
  if (Array.isArray(payload?.result?.items)) return payload.result.items;
  if (Array.isArray(payload?.result?.accounts)) return payload.result.accounts;
  if (Array.isArray(payload?.payload?.items)) return payload.payload.items;
  if (Array.isArray(payload?.payload?.accounts)) return payload.payload.accounts;
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

function isPlatformOwnerContext(context = lastModuleContext) {
  const tenantId = String(context?.tenant_id || "").trim().toLowerCase();
  const role = String(context?.role || context?.user_role || "").trim().toLowerCase();
  const organizationType = String(context?.organization_type || "").trim().toUpperCase();
  return context?.is_platform_owner === true
    || role === "super_admin"
    || tenantId === "platform"
    || organizationType === "PLATFORM";
}

function isBusinessTenantContext(context = lastModuleContext) {
  const organizationType = String(context?.organization_type || "").trim().toUpperCase();
  return organizationType === "BUSINESS" && !isPlatformOwnerContext(context) && isBusinessModuleEnabled(context);
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
    isBusinessTenant: isBusinessTenantContext(),
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

function updateVoucherBalance() {
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
          `Current tenant is ${context?.organization_type || "unknown"} (${context?.tenant_id || "unknown"}). Sign in as ${DEFAULT_MITRABOOKS_LOGIN_EMAIL} for voucher posting.`
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

// ========== Business Dashboard Data Loading ==========

/**
 * Load dashboard statistics from API
 * Fetches live KPI data: income, expenses, net position, GST, cash, receivables, payables
 */
async function loadBusinessDashboardStats() {
  const appKey = "mitrabooks";
  const result = await apiRequest(appKey, "/api/v1/business/dashboard", { method: "GET" });

  if (result.ok && result.payload) {
    lastBusinessDashboardStats = result.payload;

    // Re-render dashboard with new data if we're on the business overview
    if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "overview") {
      dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig.mitrabooks);
    }
  } else {
    lastBusinessDashboardStats = null;
    setLoginStatus(
      "warn",
      "Dashboard data unavailable",
      "Business dashboard stats could not be loaded. Using default values."
    );
  }

  renderJson(apiOutput, { dashboard: { ok: result.ok, hasData: !!lastBusinessDashboardStats } });
}

// ========== Account Selector Component (Searchable) ==========

/**
 * Filter accounts by search query (min 3 chars)
 * Returns array of matching accounts with code and name
 */
function filterBusinessAccountsByQuery(query) {
  const q = String(query || "").trim().toLowerCase();

  // Min 3 characters to filter
  if (q.length < 3) {
    return [];
  }

  const matches = businessAccountsForSelection().filter((normalized) => {
    const code = normalized.code.toLowerCase();
    const name = normalized.name.toLowerCase();
    const type = String(normalized.account_type || normalized.type || "").toLowerCase();

    return (
      code.includes(q) ||
      name.includes(q) ||
      type.includes(q)
    );
  });

  // Return max 20 results
  return matches.slice(0, 20);
}

/**
 * Render account selector HTML (searchable input + suggestions)
 * @param {string} fieldId - Unique ID for this selector (e.g., "debit-account", "credit-account")
 * @param {number} selectedAccountId - Currently selected account ID (optional)
 * @returns {string} HTML for the account selector component
 */
function renderAccountSelectorComponent(fieldId, selectedAccountId = null) {
  const accounts = businessAccountsForSelection();
  const selectedAccount = accounts.find((acc) => String(acc.id) === String(selectedAccountId));
  const usingFallbackAccounts = !Array.isArray(lastBusinessAccounts) || lastBusinessAccounts.length === 0;

  const displayText = selectedAccount
    ? `${selectedAccount.code} - ${selectedAccount.name}`
    : "";

  return `
    <div class="account-selector-component" data-field-id="${escapeHtml(fieldId)}">
      <span class="account-selector-caption">Account code dropdown</span>
      <div class="account-input-wrapper">
        <select
          class="account-picker-select"
          data-field-id="${escapeHtml(fieldId)}"
          aria-label="Select account"
        >
          <option value="">Select account code</option>
          ${accounts.map((account) => `
            <option value="${escapeHtml(account.id)}" ${String(account.id) === String(selectedAccountId || "") ? "selected" : ""}>
              ${escapeHtml(`${account.code} - ${account.name}`)}
            </option>
          `).join("")}
        </select>
        <input
          type="text"
          class="account-search-input"
          data-field-id="${escapeHtml(fieldId)}"
          placeholder="Type 3+ characters to filter account codes"
          value="${escapeHtml(displayText)}"
          autocomplete="off"
        >
        <input
          type="hidden"
          class="account-id-input"
          data-field-id="${escapeHtml(fieldId)}"
          value="${escapeHtml(selectedAccountId || "")}"
        >
      </div>
      <ul class="account-suggestions" data-field-id="${escapeHtml(fieldId)}" hidden>
        <!-- Populated on input -->
      </ul>
      ${usingFallbackAccounts ? `<p class="account-selector-note">Using default account codes. Load tenant chart of accounts to replace these defaults.</p>` : ""}
    </div>
  `;
}

/**
 * Update account selector suggestions as user types
 */
function updateAccountSuggestions(fieldId) {
  const input = document.querySelector(`.account-search-input[data-field-id="${fieldId}"]`);
  const suggestionsList = document.querySelector(`.account-suggestions[data-field-id="${fieldId}"]`);

  if (!input || !suggestionsList) return;

  const query = input.value.trim();
  const matches = filterBusinessAccountsByQuery(query);

  if (query.length < 3) {
    populateAccountPickerSelect(fieldId, businessAccountsForSelection());
    suggestionsList.hidden = true;
    suggestionsList.innerHTML = "";
    return;
  }

  populateAccountPickerSelect(fieldId, matches);

  if (matches.length === 0) {
    suggestionsList.hidden = false;
    suggestionsList.innerHTML = `<li class="account-suggestion-empty">No matching account code</li>`;
    return;
  }

  suggestionsList.innerHTML = matches
    .map((acc) => {
      const normalized = normalizeBusinessAccount(acc);
      const displayText = `${normalized.code} - ${normalized.name}`;
      return `
        <li
          class="account-suggestion-item"
          data-account-id="${escapeHtml(normalized.id)}"
          data-field-id="${escapeHtml(fieldId)}"
          title="${escapeHtml(displayText)}"
        >
          <strong>${escapeHtml(normalized.code)}</strong>
          <span>${escapeHtml(normalized.name)}</span>
        </li>
      `;
    })
    .join("");

  suggestionsList.hidden = false;
}

/**
 * Select an account from suggestions
 */
function selectAccountFromSuggestion(suggestionElement) {
  const fieldId = suggestionElement.getAttribute("data-field-id");
  const accountId = suggestionElement.getAttribute("data-account-id");

  selectBusinessAccount(fieldId, accountId);
}

function selectBusinessAccount(fieldId, accountId) {
  const account = businessAccountsForSelection()
    .find((acc) => String(acc.id) === String(accountId));
  if (!account) return;

  const input = document.querySelector(`.account-search-input[data-field-id="${fieldId}"]`);
  const idInput = document.querySelector(`.account-id-input[data-field-id="${fieldId}"]`);
  const select = document.querySelector(`.account-picker-select[data-field-id="${fieldId}"]`);
  const suggestionsList = document.querySelector(`.account-suggestions[data-field-id="${fieldId}"]`);

  if (input) {
    input.value = `${account.code} - ${account.name}`;
  }
  if (idInput) {
    idInput.value = account.id;
  }
  if (select) {
    select.value = account.id;
  }
  if (suggestionsList) {
    suggestionsList.hidden = true;
    suggestionsList.innerHTML = "";
  }

  // Trigger balance check if this is a voucher form
  updateVoucherBalance();
}

/**
 * Close all account suggestions dropdowns
 */
function closeAllAccountSuggestions() {
  document.querySelectorAll(".account-suggestions").forEach((list) => {
    list.hidden = true;
  });
}

// ========== Account Selector Event Handlers ==========

document.addEventListener("input", (event) => {
  // Handle account selector input
  const accountInput = event.target.closest(".account-search-input");
  if (accountInput) {
    const fieldId = accountInput.getAttribute("data-field-id");
    if (fieldId) {
      updateAccountSuggestions(fieldId);
    }
    return;
  }

  if (event.target?.id === "business-voucher-amount") {
    updateVoucherBalance();
    return;
  }

  // Handle debit/credit input changes - update balance
  const amountInput = event.target.closest(".voucher-debit, .voucher-credit");
  if (amountInput) {
    updateVoucherBalance();
  }
});

document.addEventListener("change", (event) => {
  const accountSelect = event.target.closest(".account-picker-select");
  if (!accountSelect) {
    return;
  }
  const fieldId = accountSelect.getAttribute("data-field-id");
  if (fieldId && accountSelect.value) {
    selectBusinessAccount(fieldId, accountSelect.value);
  }
});

document.addEventListener("click", (event) => {
  const suggestion = event.target.closest(".account-suggestion-item");
  if (suggestion) {
    selectAccountFromSuggestion(suggestion);
    return;
  }

  // Close suggestions if clicking outside
  const component = event.target.closest(".account-selector-component");
  if (!component) {
    closeAllAccountSuggestions();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeAllAccountSuggestions();
  }
});

// ========== Voucher Form Integration ==========

/**
 * Create voucher by type - handles Payment, Receipt, Contra, Journal
 */
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

/**
 * Create Payment or Receipt voucher (simple: one party, one bank/cash account)
 */
async function createSimplePartyVoucher(appKey, voucherType, date) {
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
  };

  const result = await apiRequest(appKey, "/api/v1/business/vouchers", {
    method: "POST",
    headers: {
      "X-Idempotency-Key": `business-voucher-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    },
    body: JSON.stringify(payload),
  });

  if (result.ok) {
    setLoginStatus("ok", "Voucher posted", `${voucherType.toUpperCase()} voucher created successfully.`);
    document.getElementById("business-voucher-create-dialog")?.close();
    await loadBusinessVouchers();
    if (activeBusinessWorkspace === "vouchers") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  } else {
    setLoginStatus("danger", "Post voucher failed", statusDetailText(result.payload?.detail) || "Check entries and try again.");
  }
  renderJson(apiOutput, { create_voucher: result });
}

/**
 * Create Contra voucher (bank to bank transfer)
 */
async function createContraVoucher(appKey, date) {
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
  };

  const result = await apiRequest(appKey, "/api/v1/business/vouchers", {
    method: "POST",
    headers: {
      "X-Idempotency-Key": `business-voucher-contra-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    },
    body: JSON.stringify(payload),
  });

  if (result.ok) {
    setLoginStatus("ok", "Voucher posted", "Contra voucher created successfully.");
    document.getElementById("business-voucher-create-dialog")?.close();
    await loadBusinessVouchers();
    if (activeBusinessWorkspace === "vouchers") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  } else {
    setLoginStatus("danger", "Post voucher failed", statusDetailText(result.payload?.detail) || "Check entries and try again.");
  }
  renderJson(apiOutput, { create_voucher: result });
}

/**
 * Create Journal voucher (custom debit/credit lines)
 */
async function createJournalVoucher(appKey, date) {
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
  };

  const result = await apiRequest(appKey, "/api/v1/business/vouchers", {
    method: "POST",
    headers: {
      "X-Idempotency-Key": `business-voucher-journal-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    },
    body: JSON.stringify(payload),
  });

  if (result.ok) {
    setLoginStatus("ok", "Voucher posted", "Journal entry posted successfully.");
    document.getElementById("business-voucher-create-dialog")?.close();
    await loadBusinessVouchers();
    if (activeBusinessWorkspace === "vouchers") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  } else {
    setLoginStatus("danger", "Post voucher failed", statusDetailText(result.payload?.detail) || "Check entries and try again.");
  }
  renderJson(apiOutput, { create_voucher: result });
}

async function createBusinessVoucher(voucherData) {
  const appKey = "mitrabooks";

  const debitLines = [];
  const creditLines = [];
  document.querySelectorAll(".voucher-line").forEach((lineEl) => {
    // Read account ID from hidden input in account selector component
    const accountIdInput = lineEl.querySelector(".account-id-input");
    const debitInput = lineEl.querySelector(".voucher-debit");
    const creditInput = lineEl.querySelector(".voucher-credit");

    const accountId = accountIdInput?.value || "";
    const debit = Number(debitInput?.value) || 0;
    const credit = Number(creditInput?.value) || 0;

    if (accountId && (debit > 0 || credit > 0)) {
      if (debit > 0) debitLines.push({ account_id: Number(accountId), amount: debit.toFixed(2) });
      if (credit > 0) creditLines.push({ account_id: Number(accountId), amount: credit.toFixed(2) });
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

/**
 * Render form fields for specific voucher type
 */
function renderVoucherTypeForm(voucherType) {
  const accountSelector = (fieldId) => renderAccountSelectorComponent(fieldId);

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
            ${Array.isArray(lastBusinessParties) ? lastBusinessParties.map(p =>
              `<option value="${escapeHtml(p.party_id)}">${escapeHtml(p.party_name)} (${p.party_type})</option>`
            ).join('') : ''}
          </select>
        </div>
        <div class="field">
          <label for="business-voucher-amount">Amount (₹)</label>
          <input id="business-voucher-amount" type="number" placeholder="0.00" min="0.01" step="0.01" required>
        </div>
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
            ${Array.isArray(lastBusinessParties) ? lastBusinessParties.map(p =>
              `<option value="${escapeHtml(p.party_id)}">${escapeHtml(p.party_name)} (${p.party_type})</option>`
            ).join('') : ''}
          </select>
        </div>
        <div class="field">
          <label for="business-voucher-amount">Amount (₹)</label>
          <input id="business-voucher-amount" type="number" placeholder="0.00" min="0.01" step="0.01" required>
        </div>
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
          <button class="secondary" type="button" id="business-voucher-add-line">+ Add Line</button>
        </div>
        <div class="voucher-balance-panel">
          <strong>Balance Check:</strong>
          <span id="business-voucher-balance" style="font-weight: bold; margin-left: 8px;">Debit: ₹0 | Credit: ₹0</span>
        </div>
      </div>
    `;
  }

  return `<p class="muted">Select a voucher type to proceed.</p>`;
}

/**
 * Update form when voucher type changes
 */
function updateVoucherTypeForm(voucherType) {
  const container = document.getElementById("business-voucher-form-container");
  if (!container) return;

  container.innerHTML = renderVoucherTypeForm(voucherType);

  // For journal entries, add initial lines
  if (voucherType === "journal") {
    addVoucherLine();
    addVoucherLine();
  }

  // Re-attach event listeners for new elements
  updateVoucherBalance();
}

async function openBusinessCreateVoucherDialog() {
  const dialog = document.getElementById("business-voucher-create-dialog");
  if (!dialog) return;

  if (!Array.isArray(lastBusinessAccounts) || lastBusinessAccounts.length === 0) {
    await loadBusinessAccounts();
  }
  if (!Array.isArray(lastBusinessParties) || lastBusinessParties.length === 0) {
    await loadBusinessParties();
  }

  // Reset form
  document.getElementById("business-voucher-type-select").value = "";
  document.getElementById("business-voucher-form-container").innerHTML = "";
  document.getElementById("business-voucher-date").valueAsDate = new Date();

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
    return `
      <div class="empty-state">
        <strong>No audit events found</strong>
        <span>Audit entries will appear here after party, voucher, or account activity.</span>
      </div>
    `;
  }
  return `
    <div class="table-preview compact-table erp-table audit-table">
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

  if (modules.ok && currentExperience === "mitrabooks" && isPlatformOwnerContext(modules.payload)) {
    currentExperience = "platform";
    document.querySelectorAll(".module-switch button").forEach((button) => button.classList.remove("active"));
    document.getElementById("mode-platform")?.classList.add("active");
    renderModules();
    setLoginStatus("ok", "Platform owner signed in", "Showing the platform-owner workspace. Business tenant data remains tenant-scoped.");
    updateSessionUi();
    await loadPlatformOwnerDashboard();
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
  signOutAndReturnToLogin();
});
document.getElementById("topbar-logout")?.addEventListener("click", () => {
  signOutAndReturnToLogin();
});
document.getElementById("sidebar-logout")?.addEventListener("click", () => {
  signOutAndReturnToLogin();
});
accountMenuTrigger?.addEventListener("click", () => {
  const isOpen = accountMenuPanel && !accountMenuPanel.hidden;
  if (accountMenuPanel) {
    accountMenuPanel.hidden = isOpen;
  }
  accountMenuTrigger.setAttribute("aria-expanded", String(!isOpen));
});
document.getElementById("topbar-update-password")?.addEventListener("click", openPasswordDialog);
document.getElementById("change-password-close")?.addEventListener("click", () => passwordDialog?.close());
document.getElementById("change-password-cancel")?.addEventListener("click", () => passwordDialog?.close());
passwordForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  await updateCurrentPassword();
});
document.addEventListener("click", (event) => {
  if (!accountMenuPanel || accountMenuPanel.hidden) {
    return;
  }
  if (!event.target.closest(".account-menu")) {
    closeAccountMenu();
  }
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
  } else if (businessAction === "ca-doc-refresh") {
    loadCaPracticeDocuments();
  } else if (businessAction === "ca-doc-status") {
    updateCaPracticeDocumentStatus(
      button.getAttribute("data-document-id") || "",
      button.getAttribute("data-status") || "",
    );
  } else if (businessAction === "widget-collapse") {
    toggleWidgetCollapse(button.getAttribute("data-widget-id") || "");
  } else if (businessAction === "open-widget-settings") {
    openWidgetSettings();
  } else if (businessAction === "report-tab") {
    setBusinessReportTab(button.getAttribute("data-report-tab") || "trial-balance");
  } else if (businessAction === "apply-report-filter") {
    applyBusinessReportFilter();
  } else if (businessAction === "report-ledger") {
    setBusinessReportTab("general-ledger");
    loadBusinessGeneralLedger(button.getAttribute("data-account-id") || "");
  } else if (businessAction === "load-report-ledger") {
    loadBusinessReportLedgerFromSelect();
  } else if (businessAction === "open-create-invoice") {
    openInvoiceCreate();
  } else if (businessAction === "add-invoice-line") {
    addInvoiceLine();
  } else if (businessAction === "remove-invoice-line") {
    removeInvoiceLine(button.getAttribute("data-line-id") || "");
  } else if (businessAction === "save-invoice") {
    submitInvoice();
  } else if (businessAction === "invoice-back") {
    setBusinessSalesView("list");
  } else if (businessAction === "view-invoice") {
    openInvoiceDetail(button.getAttribute("data-invoice-id") || "");
  } else if (businessAction === "begin-reverse-invoice") {
    invoiceReverseOpen = true;
    rerenderSalesIfActive();
  } else if (businessAction === "cancel-reverse-invoice") {
    invoiceReverseOpen = false;
    rerenderSalesIfActive();
  } else if (businessAction === "confirm-reverse-invoice") {
    const invoiceId = button.getAttribute("data-invoice-id") || "";
    const dateInput = document.querySelector("[data-reversal-date]");
    cancelInvoice(invoiceId, dateInput?.value || "");
  } else if (businessAction === "open-invoice-settings") {
    openInvoiceSettings();
  } else if (businessAction === "save-invoice-settings") {
    saveInvoiceSettings();
  } else if (businessAction === "open-create-bill") {
    openBillCreate();
  } else if (businessAction === "add-bill-line") {
    addBillLine();
  } else if (businessAction === "remove-bill-line") {
    removeBillLine(button.getAttribute("data-line-id") || "");
  } else if (businessAction === "save-bill") {
    submitBill();
  } else if (businessAction === "bill-back") {
    setBusinessPurchaseView("list");
  } else if (businessAction === "view-bill") {
    openBillDetail(button.getAttribute("data-bill-id") || "");
  } else if (businessAction === "begin-reverse-bill") {
    billReverseOpen = true;
    rerenderPurchaseIfActive();
  } else if (businessAction === "cancel-reverse-bill") {
    billReverseOpen = false;
    rerenderPurchaseIfActive();
  } else if (businessAction === "confirm-reverse-bill") {
    const billId = button.getAttribute("data-bill-id") || "";
    const dateInput = document.querySelector("[data-reversal-date]");
    cancelBill(billId, dateInput?.value || "");
  } else if (businessAction === "lock-period") {
    lockGstPeriodFromInput();
  } else if (businessAction === "unlock-period") {
    setGstPeriodLock(button.getAttribute("data-period") || "", false);
  } else if (businessAction === "open-create-credit-note") {
    openCreditNoteCreate();
  } else if (businessAction === "add-cn-line") {
    addCnLine();
  } else if (businessAction === "remove-cn-line") {
    removeCnLine(button.getAttribute("data-line-id") || "");
  } else if (businessAction === "save-credit-note") {
    submitCreditNote();
  } else if (businessAction === "cn-back") {
    setCreditNoteView("list");
  } else if (businessAction === "view-credit-note") {
    openCreditNoteDetail(button.getAttribute("data-cn-id") || "");
  } else if (businessAction === "begin-reverse-cn") {
    cnReverseOpen = true;
    rerenderCreditNoteIfActive();
  } else if (businessAction === "cancel-reverse-cn") {
    cnReverseOpen = false;
    rerenderCreditNoteIfActive();
  } else if (businessAction === "confirm-reverse-cn") {
    const noteId = button.getAttribute("data-cn-id") || "";
    const dateInput = document.querySelector("[data-reversal-date]");
    cancelCreditNote(noteId, dateInput?.value || "");
  } else if (businessAction === "open-create-debit-note") {
    openDebitNoteCreate();
  } else if (businessAction === "add-dn-line") {
    addDnLine();
  } else if (businessAction === "remove-dn-line") {
    removeDnLine(button.getAttribute("data-line-id") || "");
  } else if (businessAction === "save-debit-note") {
    submitDebitNote();
  } else if (businessAction === "dn-back") {
    setDebitNoteView("list");
  } else if (businessAction === "view-debit-note") {
    openDebitNoteDetail(button.getAttribute("data-dn-id") || "");
  } else if (businessAction === "begin-reverse-dn") {
    dnReverseOpen = true;
    rerenderDebitNoteIfActive();
  } else if (businessAction === "cancel-reverse-dn") {
    dnReverseOpen = false;
    rerenderDebitNoteIfActive();
  } else if (businessAction === "confirm-reverse-dn") {
    const noteId = button.getAttribute("data-dn-id") || "";
    const dateInput = document.querySelector("[data-reversal-date]");
    cancelDebitNote(noteId, dateInput?.value || "");
  }
});
dashboardPreview.addEventListener("input", (event) => {
  if (event.target.closest("[data-invoice-form]")) {
    updateInvoiceTotalsDisplay();
  } else if (event.target.closest("[data-bill-form]")) {
    updateBillTotalsDisplay();
  } else if (event.target.closest("[data-cn-form]")) {
    updateCnTotalsDisplay();
  } else if (event.target.closest("[data-dn-form]")) {
    updateDnTotalsDisplay();
  }
});
dashboardPreview.addEventListener("change", (event) => {
  if (event.target.name !== "is_inter_state") {
    return;
  }
  if (event.target.closest("[data-invoice-form]")) {
    updateInvoiceTotalsDisplay();
  } else if (event.target.closest("[data-bill-form]")) {
    updateBillTotalsDisplay();
  } else if (event.target.closest("[data-cn-form]")) {
    updateCnTotalsDisplay();
  } else if (event.target.closest("[data-dn-form]")) {
    updateDnTotalsDisplay();
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
  const mandirForm = event.target.closest("[data-mandir-create-form]");
  const caDocumentForm = event.target.closest("[data-ca-document-form]");
  if (!mandirForm && !caDocumentForm) {
    return;
  }
  event.preventDefault();
  if (mandirForm) {
    submitMandirCreateForm(mandirForm);
  } else if (caDocumentForm) {
    createCaPracticeDocument(caDocumentForm);
  }
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
    const city = document.getElementById("business-party-city")?.value || "";
    const state = document.getElementById("business-party-state")?.value || "";
    const pincode = document.getElementById("business-party-pincode")?.value || "";
    const opening_balance = document.getElementById("business-party-opening-balance")?.value || "0";

    if (!name.trim()) {
      setLoginStatus("warn", "Party name required", "Enter a name for the party.");
      return;
    }

    createBusinessParty({ name, party_type, gstin, city, state, pincode, opening_balance });
  });
}

if (businessPartyEditForm) {
  businessPartyEditForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const partyId = document.getElementById("business-party-edit-id")?.value || "";
    const name = document.getElementById("business-party-edit-name")?.value || "";
    const party_type = document.getElementById("business-party-edit-type")?.value || "customer";
    const gstin = document.getElementById("business-party-edit-gstin")?.value || "";
    const city = document.getElementById("business-party-edit-city")?.value || "";
    const state = document.getElementById("business-party-edit-state")?.value || "";
    const pincode = document.getElementById("business-party-edit-pincode")?.value || "";
    const opening_balance = document.getElementById("business-party-edit-opening-balance")?.value || "0";

    if (!name.trim()) {
      setLoginStatus("warn", "Party name required", "Enter a name for the party.");
      return;
    }

    updateBusinessParty(partyId, { name, party_type, gstin, city, state, pincode, opening_balance });
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
    const voucherType = document.getElementById("business-voucher-type-select")?.value || "";
    const date = document.getElementById("business-voucher-date")?.value || "";

    if (!voucherType) {
      setLoginStatus("warn", "Voucher type required", "Select a voucher type.");
      return;
    }

    if (!date) {
      setLoginStatus("warn", "Date required", "Enter the voucher date.");
      return;
    }

    createBusinessVoucherByType(voucherType, date);
  });

  // Add event listener for voucher type selector
  document.getElementById("business-voucher-type-select")?.addEventListener("change", (event) => {
    const voucherType = event.target.value;
    updateVoucherTypeForm(voucherType);
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
    const selectorMeta = orgSelectorMeta[orgType] || orgSelectorMeta.BUSINESS;
    selectedOrgType = orgType;
    syncOrgSelectorOptions(orgType);
    orgMenu.hidden = true;
    orgSelector.classList.remove("open");
    if (orgType !== "BUSINESS") {
      setLoginStatus("warn", selectorMeta.statusTitle, selectorMeta.statusCopy);
    } else {
      setLoginStatus("ok", selectorMeta.statusTitle, selectorMeta.statusCopy);
    }
    updateTrustedContextUi();
    if (currentExperience === "mitrabooks") {
      activeBusinessWorkspace = "overview";
      syncBusinessNavActiveState();
      dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig.mitrabooks);
      if (orgType === "BUSINESS") {
        loadBusinessDashboardStats();
      } else if (orgType === "CA_PRACTICE") {
        lastCaDocumentsResult = null;
        lastCaDocuments = [];
        loadCaPracticeDocuments();
      }
    }
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

// Load grouped navigation for MitraBooks if already signed in (Phase 1D)
if (currentExperience === "mitrabooks" && getAccessToken()) {
  const appKey = EXPERIENCE_APP_KEYS[currentExperience] || APP_KEY;
  loadAndRenderGroupedNav(appKey).catch(err => {
    console.error("[Init] Failed to load grouped nav on page load:", err);
  });
}

renderModuleState(moduleState);
runChecks();
