
// ══════════════════════════════════════════════════════════════════════
// SECTION: MODULE BOOTSTRAP — MitraBooks ERP app.js
// NOTE  : 15K-line vanilla ES-module. Split trigger: >18K lines or second developer joins.
// Use Ctrl+F '// SECTION:' to jump between sections.
// ══════════════════════════════════════════════════════════════════════

import {
  clearAccessToken,
  clearAllTokens,
  apiRequest,
  downloadApiFile,
  fetchApiFileObjectUrl,
  getAccessToken,
  getRefreshToken,
  getConfiguredApiBaseUrl,
  loadHealth,
  loadModules,
  moduleItemsFromPayload,
  renderModuleState,
  renderJson,
  setAccessToken,
  setRefreshToken,
  setConfiguredApiBaseUrl,
  statusLabel,
} from "../shared/api-client.js";

// ============================================
// THEME MANAGEMENT (PWA-Compatible)
// ============================================

const THEME_STORAGE_KEY = "mitrabooks-theme";


// ══════════════════════════════════════════════════════════════════════
// SECTION: NAVIGATION GROUPS + ITEMS
// NOTE  : businessNavigationGroups — sidebar structure for MitraBooks ERP
// ══════════════════════════════════════════════════════════════════════

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
        { label: "Chart of Accounts", businessWorkspace: "coa", icon: "CA", module: { module_key: "accounting", frontend_path: "/accounting/coa", enabled: true } },
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
        { label: "Bank Reconciliation", businessWorkspace: "bank-recon", icon: "BR", module: { module_key: "banking", frontend_path: "/business/bank-recon", enabled: true } },
        { label: "UPI / QR Payments", businessWorkspace: "upi-payments", icon: "UP", module: { module_key: "payments", frontend_path: "/business/upi-payments", enabled: false } },
        { label: "Reconciliation", businessWorkspace: "reconciliation", icon: "RC", module: { module_key: "accounting", frontend_path: "/accounting/reconciliation", enabled: true } },
      ],
    },
    {
      name: "Taxes & Compliance",
      items: [
        { label: "GST Returns", businessWorkspace: "gst-returns", icon: "GT", module: { module_key: "gst", frontend_path: "/gst/returns", enabled: true } },
        { label: "TDS / TCS", businessWorkspace: "tds-tcs", icon: "TD", module: { module_key: "tax", frontend_path: "/tax/tds-tcs", enabled: true } },
        { label: "CA Practice Portal", businessWorkspace: "ca-access", icon: "CA", module: { module_key: "ca_access", frontend_path: "/business/ca-access", enabled: true } },
      ],
    },
    {
      name: "Intelligence & Reports",
      items: [
        { label: "Financial Statements", businessWorkspace: "reports", icon: "FS", module: { module_key: "accounting", frontend_path: "/accounting/reports", enabled: true } },
        { label: "Financial Health", businessWorkspace: "financial-health", icon: "FH", module: { module_key: "analytics", frontend_path: "/business/financial-health", enabled: true } },
        { label: "Analytics", businessWorkspace: "analytics", icon: "AN", module: { module_key: "analytics", frontend_path: "/business/analytics", enabled: false } },
      ],
    },
    {
      name: "Configuration & Extensions",
      items: [
        { label: "Settings", businessWorkspace: "settings", icon: "ST", module: { module_key: "business", frontend_path: "/business/settings", enabled: true } },
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

// ══════════════════════════════════════════════════════════════════════
// SECTION: THEME (dark / light)
// NOTE  : setTheme, getTheme, initializeTheme, updateThemeButtons
// ══════════════════════════════════════════════════════════════════════

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


// ══════════════════════════════════════════════════════════════════════
// SECTION: WIDGET SYSTEM (dashboard widget collapse / visibility / settings)
// NOTE  : getWidgetStates, toggleWidgetCollapse, createWidgetWrapper, openWidgetSettings
// ══════════════════════════════════════════════════════════════════════

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


// ══════════════════════════════════════════════════════════════════════
// SECTION: EXPERIENCE DETECTION + PRODUCT SHELL
// NOTE  : isMandirHost, isGruhaHost, isProductionShell, initialExperience, experienceConfig
// ══════════════════════════════════════════════════════════════════════

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
    statusTitle: "Professional workspace active",
    statusCopy: "Using the signed-in MitraBooks tenant context for billing, client accounts, receipts, and reports.",
  },
  CA_PRACTICE: {
    label: "CA Practice Portal",
    subtitle: "Client document workflow",
    statusTitle: "CA Practice Portal active",
    statusCopy: "Using tenant-scoped document metadata, review queue, staff assignment, and compliance tracking.",
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
let coaTypeFilter = "";
let lastCaDocuments = [];
let lastCaDocumentsResult = null;
let caAccessUsers = [];
let caAccessLoading = false;
let caInviteError = "";
let caInviteSuccess = "";
let caPracticeFilters = {
  status: "",
  client_name: "",
  assigned_to: "",
  priority: "",
};
const CA_DOCUMENT_WORKFLOW = ["uploaded", "under_review", "query_raised", "reviewed", "posted"];
const CA_DOCUMENT_LABELS = {
  uploaded: "Uploaded",
  under_review: "Under review",
  query_raised: "Query raised",
  reviewed: "Reviewed",
  posted: "Posted",
};
const CA_DOCUMENT_PRIORITY_LABELS = {
  low: "Low",
  normal: "Normal",
  high: "High",
  urgent: "Urgent",
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


// ══════════════════════════════════════════════════════════════════════
// SECTION: EXPERIENCE + MODULE CONFIG
// NOTE  : renderModules, mandirNavigationItems, gruhaNavigationItems, loadAndRenderGroupedNav
// ══════════════════════════════════════════════════════════════════════

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

  // On a fresh page load / refresh the dashboard overview must fetch its live
  // KPIs. The nav-click and org-select paths call this, but the boot render
  // (renderModules) did not — so a refresh showed Rs 0 until you navigated.
  if (hasTrustedSession() && currentExperience === "mitrabooks" && activeBusinessWorkspace === "overview"
      && activeOrgSelectorType() === "BUSINESS") {
    loadBusinessDashboardStats();
  }

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

// ══════════════════════════════════════════════════════════════════════
// SECTION: NAVIGATION RENDERING
// NOTE  : renderGroupedNav, renderGroupedNavFromItems — builds sidebar from nav group config
// ══════════════════════════════════════════════════════════════════════

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
    // Hide not-yet-built items (enabled:false roadmap stubs) so the sidebar shows
    // only working features. Config is left intact — flip a stub to enabled:true
    // when it ships and it reappears. Groups with nothing built are skipped.
    const visibleItems = group.items.filter((item) => item.module.enabled !== false);
    if (visibleItems.length === 0) return;

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
    visibleItems.forEach(item => {
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


// ══════════════════════════════════════════════════════════════════════
// SECTION: STAT CARDS + ACTIVITY + RECENT VOUCHERS
// NOTE  : renderStatCards, renderActionTiles, renderActivity, renderBusinessRecentVoucherRows
// ══════════════════════════════════════════════════════════════════════

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


// ══════════════════════════════════════════════════════════════════════
// SECTION: CA PRACTICE PORTAL + DOCUMENT INTAKE
// API   : GET/POST /api/v1/business/ca-documents
// NOTE  : renderCaDocumentTable, renderCaDocumentIntake, caPracticeSummary
// ══════════════════════════════════════════════════════════════════════

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

function caDocumentPriorityLabel(priority) {
  return CA_DOCUMENT_PRIORITY_LABELS[priority] || "Normal";
}

function caPracticeSummary(rows) {
  const safeRows = Array.isArray(rows) ? rows : [];
  const clients = new Set();
  const assignees = new Map();
  const compliance = new Map();
  let clientAccess = 0;
  let urgent = 0;
  safeRows.forEach((row) => {
    if (row.client_name) {
      clients.add(row.client_name);
    }
    const owner = row.assigned_to || "Unassigned";
    assignees.set(owner, (assignees.get(owner) || 0) + 1);
    const area = row.compliance_area || "General";
    compliance.set(area, (compliance.get(area) || 0) + 1);
    if (row.client_access_enabled) {
      clientAccess += 1;
    }
    if (row.priority === "urgent" || row.priority === "high") {
      urgent += 1;
    }
  });
  return {
    clientCount: clients.size,
    clientAccess,
    urgent,
    assignees: Array.from(assignees.entries()).sort((a, b) => b[1] - a[1]),
    compliance: Array.from(compliance.entries()).sort((a, b) => b[1] - a[1]),
  };
}

function renderCaPracticeFilters() {
  return `
    <form class="ca-practice-filter-panel" data-ca-filter-form>
      <label>
        <span>Status</span>
        <select name="status">
          <option value="">All statuses</option>
          ${CA_DOCUMENT_WORKFLOW.map((status) => `
            <option value="${escapeHtml(status)}" ${caPracticeFilters.status === status ? "selected" : ""}>${escapeHtml(caDocumentStatusLabel(status))}</option>
          `).join("")}
        </select>
      </label>
      <label>
        <span>Client</span>
        <input name="client_name" type="search" maxlength="160" value="${escapeHtml(caPracticeFilters.client_name)}" placeholder="Client or company">
      </label>
      <label>
        <span>Assigned to</span>
        <input name="assigned_to" type="search" maxlength="120" value="${escapeHtml(caPracticeFilters.assigned_to)}" placeholder="Staff or partner">
      </label>
      <label>
        <span>Priority</span>
        <select name="priority">
          <option value="">All priorities</option>
          ${Object.entries(CA_DOCUMENT_PRIORITY_LABELS).map(([value, label]) => `
            <option value="${escapeHtml(value)}" ${caPracticeFilters.priority === value ? "selected" : ""}>${escapeHtml(label)}</option>
          `).join("")}
        </select>
      </label>
      <div class="ca-practice-filter-actions">
        <button type="submit" class="secondary">Apply Filters</button>
        <button type="button" class="secondary" data-business-action="ca-doc-clear-filters">Clear</button>
      </div>
    </form>
  `;
}

function renderCaPracticeOperations(rows) {
  const summary = caPracticeSummary(rows);
  const assigneeRows = summary.assignees.length ? summary.assignees : [["Unassigned", 0]];
  const complianceRows = summary.compliance.length ? summary.compliance : [["General", 0]];
  return `
    <div class="ca-practice-operations-grid">
      <article>
        <span>Client Tracking</span>
        <strong>${escapeHtml(String(summary.clientCount))}</strong>
        <small>Client books represented in this tenant queue.</small>
      </article>
      <article>
        <span>Client Access</span>
        <strong>${escapeHtml(String(summary.clientAccess))}</strong>
        <small>Metadata records flagged for client visibility when access rules are enabled.</small>
      </article>
      <article>
        <span>Priority Work</span>
        <strong>${escapeHtml(String(summary.urgent))}</strong>
        <small>High or urgent records needing staff attention.</small>
      </article>
    </div>
    <div class="ca-practice-workload-grid">
      <section>
        <h5>Staff Assignment</h5>
        ${assigneeRows.map(([name, count]) => `
          <div class="ca-practice-row">
            <span>${escapeHtml(name)}</span>
            <strong>${escapeHtml(String(count))}</strong>
          </div>
        `).join("")}
      </section>
      <section>
        <h5>Compliance Dashboard</h5>
        ${complianceRows.map(([name, count]) => `
          <div class="ca-practice-row">
            <span>${escapeHtml(name)}</span>
            <strong>${escapeHtml(String(count))}</strong>
          </div>
        `).join("")}
      </section>
    </div>
  `;
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
            <th>Owner / Staff</th>
            <th>Priority</th>
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
                <td>
                  <strong>${escapeHtml(row.client_owner || "-")}</strong>
                  <span class="row-subtext">${escapeHtml(row.assigned_to || "Unassigned")}</span>
                </td>
                <td>
                  <span class="pill ${row.priority === "urgent" || row.priority === "high" ? "warn" : ""}">${escapeHtml(caDocumentPriorityLabel(row.priority))}</span>
                  <span class="row-subtext">${escapeHtml(row.due_date || "No due date")}</span>
                </td>
                <td><span class="pill">${escapeHtml(caDocumentStatusLabel(row.status))}</span></td>
                <td>
                  ${escapeHtml(row.next_action || "-")}
                  <span class="row-subtext">${escapeHtml(row.compliance_area || "General")} ${row.client_access_enabled ? " | Client access flagged" : ""}</span>
                </td>
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
              <span>Client owner</span>
              <input name="client_owner" type="text" maxlength="120" placeholder="Partner or manager">
            </label>
            <label>
              <span>Priority</span>
              <select name="priority">
                <option value="normal">Normal</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
                <option value="low">Low</option>
              </select>
            </label>
            <label>
              <span>Due date</span>
              <input name="due_date" type="date">
            </label>
            <label>
              <span>Compliance area</span>
              <select name="compliance_area">
                <option value="">General</option>
                <option>GST</option>
                <option>TDS</option>
                <option>Income tax</option>
                <option>Audit</option>
                <option>ROC</option>
                <option>Bookkeeping</option>
              </select>
            </label>
            <label>
              <span>Original file name</span>
              <input name="original_file_name" type="text" maxlength="240" placeholder="metadata only, no upload yet">
            </label>
            <label>
              <span>Notes</span>
              <input name="notes" type="text" maxlength="500" placeholder="Review notes or client instruction">
            </label>
            <label class="ca-checkbox-field">
              <input name="client_access_enabled" type="checkbox" value="true">
              <span>Flag for future client access</span>
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

      ${renderCaPracticeFilters()}
      ${renderCaPracticeOperations(lastCaDocuments)}

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
      eyebrow: "Client document workflow",
      lead: "Practice-level workspace for client document intake, review status tracking, staff assignment, client-access flags, and compliance metadata.",
      kpis: [
        ["Client Tracking", "Active", "Tenant-scoped client document metadata"],
        ["Review Queue", "Active", "Document review status workflow"],
        ["Compliance", "Active", "GST, TDS, audit, ROC, and bookkeeping metadata"],
      ],
      modules: [
        ["Client document tracking", "Track each client book through tenant-scoped metadata before any future client tenant switching.", "Active"],
        ["GST and TDS metadata", "Tag documents by compliance area, due date, priority, and reviewer.", "Active"],
        ["Review queue", "Move uploaded metadata through under review, query raised, reviewed, and posted states.", "Active"],
        ["Workload summary", "Summarize client counts, staff assignment, priority work, and compliance areas from the current queue.", "Active"],
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
      note: "Current state: tenant-scoped document metadata and review workflow are active. Deferred scope: file storage, OCR, client tenant switching, voucher posting, and filing links.",
    };
  }

  return {
    label: "Professional Suite",
    eyebrow: "Billing and invoicing",
    lead: "Service-business workspace for billing, receipts, professional client accounts, and revenue tracking using the active MitraBooks tenant context.",
    kpis: [
      ["Billing", "Active", "Service invoices through Sales"],
      ["Receivables", "Active", "Client accounts through Parties and ledger reports"],
      ["Reports", "Active", "Financial statements and health summaries"],
    ],
    modules: [
      ["Client billing", "Create service invoices with GST through the active Sales workspace.", "Active"],
      ["Client accounts", "Maintain professional clients in Parties and review balances from ledger-backed reports.", "Active"],
      ["Receipts", "Record client receipts with journal posting from the existing voucher workflow.", "Active"],
      ["Professional reports", "Use financial statements, receivables, and health summaries for practice reporting.", "Active"],
    ],
    note: "Current state: Professional Suite reuses active MitraBooks billing, parties, vouchers, and reports. Deferred scope: separate professional-only tenant context and retainer-specific automation.",
  };
}

function renderSelectedOrgWorkspace() {
  const orgType = activeOrgSelectorType();
  if (orgType === "CA_PRACTICE") {
    return renderCaPracticePortalWorkspace();
  }
  if (orgType === "PROFESSIONAL") {
    return renderProfessionalSuiteWorkspace();
  }
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

let businessDashboardLoadInFlight = false;


// ══════════════════════════════════════════════════════════════════════
// SECTION: BUSINESS EXECUTIVE DASHBOARD
// API   : GET /api/v1/business/dashboard/stats
// NOTE  : renderBusinessExecutiveDashboard — KPI cards, quick actions, data-health panel
// ══════════════════════════════════════════════════════════════════════

function renderBusinessExecutiveDashboard() {
  const voucherCount = lastAccountingDrilldown?.summary?.voucher_count ?? 0;
  const partyCount = Array.isArray(lastBusinessParties) ? lastBusinessParties.length : 0;
  const accountCount = Array.isArray(lastBusinessAccounts) ? lastBusinessAccounts.length : 0;

  // Live dashboard data from GET /business/dashboard (computed from the ledger).
  // No hard-coded fallbacks: before data loads or with an empty ledger we show
  // real zeros rather than invented figures.
  const dashboardData = lastBusinessDashboardStats || {};
  const hasDashboard = !!lastBusinessDashboardStats;

  // Lazy self-heal: whenever the KPI dashboard renders without data (boot,
  // refresh, or any path that didn't fetch), kick off the load. Deferred so we
  // don't re-enter during the current innerHTML render; guarded so it fires once.
  if (hasTrustedSession() && !hasDashboard && !businessDashboardLoadInFlight) {
    setTimeout(() => { loadBusinessDashboardStats(); }, 0);
  }

  // KPI values (Rupees). FYTD = financial-year-to-date.
  const incomeVal = Number(dashboardData.income?.fytd || 0);
  const expenseVal = Number(dashboardData.expenses?.fytd || 0);
  const netVal = Number(dashboardData.net_position?.profit_loss || 0);
  const incomeGrowth = Number(dashboardData.income?.ytd_growth || 0);
  const cashVal = Number(dashboardData.cash_and_bank || 0);
  const receivablesVal = Number(dashboardData.receivables || 0);
  const payablesVal = Number(dashboardData.payables || 0);
  const gstStatus = dashboardData.gst?.status || "—";

  const incomeDisplay = formatCurrency(incomeVal);
  const expenseDisplay = formatCurrency(expenseVal);
  const netDisplay = formatCurrency(netVal);

  // 6-month income-vs-expense trend (lakhs) from the ledger; empty when no activity.
  const months = Array.isArray(dashboardData.monthly_trend) ? dashboardData.monthly_trend : [];
  const trendValues = months.flatMap(([, income, expense]) => [Number(income) || 0, Number(expense) || 0]);
  const maxValue = trendValues.length ? Math.max(...trendValues, 0.0001) : 1;
  const bars = months.length
    ? months.map(([label, income, expense]) => {
        const inc = Number(income) || 0;
        const exp = Number(expense) || 0;
        const incomeHeight = Math.max(4, Math.round((inc / maxValue) * 132));
        const expenseHeight = Math.max(4, Math.round((exp / maxValue) * 132));
        return `
      <div class="finance-bar-group">
        <div class="finance-bars" aria-label="${escapeHtml(label)} income Rs. ${inc}L and expenses Rs. ${exp}L">
          <span class="income-bar" style="height: ${incomeHeight}px"></span>
          <span class="expense-bar" style="height: ${expenseHeight}px"></span>
        </div>
        <small>${escapeHtml(label)}</small>
      </div>
    `;
      }).join("")
    : `<p class="muted">${hasDashboard ? "No ledger activity in the last 6 months." : "Loading ledger activity…"}</p>`;

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
          <small>Income − Expenses (FYTD)</small>
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

  // Widget 3: CEO Panel — real metrics derived from the live ledger figures above.
  const coverage = payablesVal > 0 ? cashVal / payablesVal : null;
  const coverageRow = coverage != null
    ? `<strong>${coverage.toFixed(1)}x coverage</strong><span>Cash & bank (${formatCurrency(cashVal)}) against vendor dues (${formatCurrency(payablesVal)}).</span>`
    : `<strong>${escapeHtml(formatCurrency(cashVal))}</strong><span>Cash & bank on hand. No outstanding vendor dues.</span>`;
  const ceoPanelContent = `
    <div class="preview-heading compact">
      <div class="ceo-title-block">
        <span class="ceo-orbit" aria-hidden="true"></span>
        <span class="ai-badge">Live from ledger</span>
        <p>Key operating figures computed from posted entries (as of ${escapeHtml(dashboardData.as_of || todayIsoDate())}).</p>
      </div>
    </div>
    <div class="ceo-insight-list" role="list">
      <div class="ceo-insight-row" role="listitem">
        <span class="insight-spark" aria-hidden="true"></span>
        <div class="ceo-insight-copy">${coverageRow}</div>
      </div>
      <div class="ceo-insight-row" role="listitem">
        <span class="insight-spark" aria-hidden="true"></span>
        <div class="ceo-insight-copy">
          <strong>${escapeHtml(formatCurrency(receivablesVal))}</strong>
          <span>Outstanding from customers (open receivables).</span>
        </div>
      </div>
      <div class="ceo-insight-row" role="listitem">
        <span class="insight-spark" aria-hidden="true"></span>
        <div class="ceo-insight-copy">
          <strong>${escapeHtml(formatCurrency(netVal))}</strong>
          <span>Net position this financial year (income − expenses).</span>
        </div>
      </div>
    </div>
    <p class="ceo-footnote">${voucherCount} posted voucher(s), ${partyCount} party record(s), and ${accountCount} account(s) in this dashboard context. GST: ${escapeHtml(gstStatus)}.</p>
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


// ══════════════════════════════════════════════════════════════════════
// SECTION: SHARED UTILITIES
// NOTE  : escapeHtml, formatCurrency, formatCountLabel, setLoginStatus, statusDetailText, delay
// ══════════════════════════════════════════════════════════════════════

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


// ══════════════════════════════════════════════════════════════════════
// SECTION: AUTH + SESSION
// API   : POST /api/v1/auth/login  POST /api/v1/auth/change-password
// NOTE  : signInWithPassword, signOutAndReturnToLogin, hasTrustedSession, updateSessionUi
// ══════════════════════════════════════════════════════════════════════

let pendingForcedPasswordChange = false;

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
  const rt = getRefreshToken();
  if (rt) {
    const appKey = EXPERIENCE_APP_KEYS[currentExperience] || APP_KEY;
    apiRequest(appKey, "/api/v1/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: rt }),
    }).catch(() => {});
  }
  clearAllTokens();
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
  _clearPasswordError();
  if (passwordStatus && pendingForcedPasswordChange) {
    const field = document.getElementById("password-error-field");
    if (field) field.style.display = "block";
    passwordStatus.className = "module-state warn";
    passwordStatus.innerHTML = "<strong>Temporary password in use</strong><span>Change the temporary password before opening the MitraBooks workspace.</span>";
  }
  passwordDialog?.showModal();
}

async function loadCurrentUserProfile(appKey) {
  const token = getAccessToken();
  if (!token) {
    return null;
  }
  const result = await apiRequest(appKey, "/api/v1/users/me", {
    method: "GET",
    timeoutMs: LOGIN_REQUEST_TIMEOUT_MS,
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return result.ok ? (result.payload || null) : null;
}

async function completeWorkspaceSignIn(appKey) {
  if (currentExperience === "mitrabooks") {
    loadAndRenderGroupedNav(appKey).catch(err => {
      console.error("[Login] Failed to load grouped nav:", err);
    });
  }

  await showMandirSplash();
  try {
    await Promise.all([runChecks(), delay(1400)]);
  } finally {
    hideMandirSplash();
  }
}

function _showPasswordError(msg) {
  const field = document.getElementById("password-error-field");
  if (field) field.style.display = "block";
  if (passwordStatus) {
    passwordStatus.className = "module-state danger";
    passwordStatus.innerHTML = msg;
  }
}

function _clearPasswordError() {
  const field = document.getElementById("password-error-field");
  if (field) field.style.display = "none";
  if (passwordStatus) {
    passwordStatus.className = "module-state";
    passwordStatus.textContent = "";
  }
}

async function updateCurrentPassword() {
  const currentPassword = String(currentPasswordInput?.value || "");
  const newPassword = String(newPasswordInput?.value || "");
  const confirmPassword = String(confirmNewPasswordInput?.value || "");
  const submitButton = document.getElementById("change-password-submit");

  if (!currentPassword || currentPassword.length < 6) {
    _showPasswordError("<strong>Current password required</strong><span>Enter the current account password first.</span>");
    return;
  }
  if (!newPassword || newPassword.length < 6) {
    _showPasswordError("<strong>New password too short</strong><span>Use at least 6 characters.</span>");
    return;
  }
  if (newPassword !== confirmPassword) {
    _showPasswordError("<strong>Passwords do not match</strong><span>Confirm the new password again.</span>");
    return;
  }
  _clearPasswordError();

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
    const wasForcedPasswordChange = pendingForcedPasswordChange;
    pendingForcedPasswordChange = false;
    passwordForm?.reset();
    if (passwordStatus) {
      passwordStatus.className = "module-state ok";
      passwordStatus.innerHTML = "<strong>Password updated</strong><span>Use the new password for your next sign-in.</span>";
    }
    passwordDialog?.close();
    if (wasForcedPasswordChange) {
      setLoginStatus("ok", "Password updated", "Password changed. Loading your MitraBooks workspace.");
      await completeWorkspaceSignIn(EXPERIENCE_APP_KEYS[currentExperience] || APP_KEY);
    } else {
      setLoginStatus("ok", "Password updated", "Use the new password for your next sign-in.");
    }
  } else {
    _showPasswordError(`<strong>Password update failed</strong><span>${escapeHtml(statusDetailText(result.payload?.detail) || statusDetailText(result.payload) || "Try again.")}</span>`);
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
    setRefreshToken(result.payload?.refresh_token || "");
    window.localStorage.setItem(LOGIN_EMAIL_STORAGE_KEY, email);

    // Clear password for security
    if (loginPassword) {
      loginPassword.value = "";
    }

    updateSessionUi();
    renderJson(apiOutput, { login: { ok: true, status: result.status, token_type: result.payload?.token_type || "bearer" } });
    const currentUser = await loadCurrentUserProfile(appKey);
    pendingForcedPasswordChange = Boolean(currentUser?.must_change_password);
    if (pendingForcedPasswordChange) {
      setLoginStatus("warn", "Temporary password in use", "Change the temporary password to continue into the MitraBooks workspace.");
      openPasswordDialog();
      return;
    }
    setLoginStatus("ok", "Signed in", "Tenant workspace is loading.");
    await completeWorkspaceSignIn(appKey);
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


// ══════════════════════════════════════════════════════════════════════
// SECTION: MANDIR — receipt / donation / seva tables
// NOTE  : renderMandirDonationsTable, renderMandirSevaBookingsTable, renderMandirReceiptHistoryTable
// ══════════════════════════════════════════════════════════════════════

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


// ══════════════════════════════════════════════════════════════════════
// SECTION: MANDIR — financial reports (TB / I&E / B&P / BS)
// API   : GET /api/v1/mandir/reports/...
// NOTE  : renderMandirTrialBalance, renderMandirIncomeExpenditureReport, renderMandirBalanceSheetReport
// ══════════════════════════════════════════════════════════════════════

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


// ══════════════════════════════════════════════════════════════════════
// SECTION: MANDIR — panchang + operational reports
// API   : GET /api/v1/mandir/panchang  GET /api/v1/mandir/reports/operational
// NOTE  : renderMandirPanchang, renderMandirOperationalReports, renderMandirDevoteesView
// ══════════════════════════════════════════════════════════════════════

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


// ══════════════════════════════════════════════════════════════════════
// SECTION: MANDIR — dashboard home + workspace tabs
// API   : GET /api/v1/mandir/dashboard
// NOTE  : renderMandirDashboardHome, renderMandirDashboard, renderMandirSettings
// ══════════════════════════════════════════════════════════════════════

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


// ══════════════════════════════════════════════════════════════════════
// SECTION: DASHBOARD PREVIEW SHELL
// NOTE  : renderDashboardPreview — outermost wrapper rendered into dashboardPreview element
// ══════════════════════════════════════════════════════════════════════

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
    const ds = lastBusinessDashboardStats || {};
    const cashMetric = formatCurrency(Number(ds.cash_and_bank || 0));
    const recvMetric = formatCurrency(Number(ds.receivables || 0));
    const payMetric = formatCurrency(Number(ds.payables || 0));
    const gstMetric = ds.gst?.status || "—";
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
            <strong class="metric-value">${escapeHtml(cashMetric)}</strong>
            <small class="metric-sub">available balance</small>
          </div>
          <div class="metric-item">
            <span class="metric-label">Receivables</span>
            <strong class="metric-value">${escapeHtml(recvMetric)}</strong>
            <small class="metric-sub">open invoices</small>
          </div>
          <div class="metric-item">
            <span class="metric-label">Payables</span>
            <strong class="metric-value">${escapeHtml(payMetric)}</strong>
            <small class="metric-sub">vendor dues</small>
          </div>
          <div class="metric-item">
            <span class="metric-label">GST Filing</span>
            <strong class="metric-value">${escapeHtml(gstMetric)}</strong>
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
let activeSettingsDetailId = "";
const MITRABOOKS_SETTINGS_GROUPS = [
  {
    title: "Core Settings",
    description: "Always visible for MitraBooks business tenants.",
    items: [
      { title: "Organization", status: "Planned", detail: "Legal name, trade name, GSTIN, PAN, TAN, CIN/LLPIN, address, contact details, financial year, currency, time zone, and logo.", visibility: "Owner, Admin, CA Partner" },
      { title: "Branches", status: "Planned", detail: "Branch code, GST registration per branch, address, contact details, warehouse mapping, and cost centre mapping.", visibility: "Multi-location businesses" },
      { title: "Users & Roles", status: "Planned", detail: "Invite, disable, and manage Super Admin, Admin, Accountant, Cashier, Auditor, and Viewer roles.", visibility: "Owner, Admin" },
      { title: "Permissions", status: "Planned", detail: "Granular access for vouchers, inventory, banking, approvals, reports, and payment controls.", visibility: "Owner, Admin" },
      { title: "Chart of Accounts", status: "Implemented", detail: "Default business chart, protected system accounts, ledger drill-down, and opening balances through journal posting.", visibility: "Accounting users", workspace: "accounting" },
      { title: "Tax & Compliance", status: "Implemented", detail: "GST registration mode, GST reports, GSTR preparation, TDS/TCS sections, period locks, and reconciliation workflows.", visibility: "Accountant, CA", workspace: "gst-returns" },
      { title: "Voucher Configuration", status: "Partial", detail: "Journal, receipt, payment, and contra posting exists. Numbering and approval matrix are planned.", visibility: "Owner, Admin, Accountant", workspace: "vouchers" },
      { title: "Security", status: "Planned", detail: "MFA, password policy, login history, device management, and session controls.", visibility: "Owner, Admin" },
    ],
  },
  {
    title: "Module Settings",
    description: "Visible when the corresponding MitraBooks module or business mode is enabled.",
    items: [
      { title: "Invoice Settings", status: "Implemented", detail: "Sales invoice fields, numbering pattern, GST registration type, composition category, and inventory accounting toggle.", visibility: "Admin", workspace: "sales" },
      { title: "Inventory", status: "Partial", detail: "Item master and stock register exist. UOM, godowns, valuation policy, and stock approvals are planned.", visibility: "Inventory businesses", workspace: "reports" },
      { title: "Banking", status: "Partial", detail: "Manual bank reconciliation exists. Bank account setup, gateway mapping, and bank API sync are planned.", visibility: "Banking users", workspace: "bank-recon" },
      { title: "Financial Controls", status: "Partial", detail: "Posted-entry immutability and reversals exist. Voucher locking, backdated-entry approval, and closing controls need explicit settings.", visibility: "Owner, Auditor", workspace: "audit" },
      { title: "Templates", status: "Planned", detail: "Invoice, receipt, payment voucher, statement, and report templates with tenant branding.", visibility: "Owner, Admin" },
      { title: "Notifications", status: "Planned", detail: "Email, SMS, WhatsApp, due-date, approval, and compliance reminder rules.", visibility: "Owner, Admin" },
    ],
  },
  {
    title: "Professional Practice Settings",
    description: "For CA firms and bookkeepers handling many client companies from one login.",
    items: [
      { title: "Client Management", status: "Planned", detail: "Add clients, capture GSTIN/PAN/contact person, and classify engagement type.", visibility: "CA Partner, Practice Admin" },
      { title: "Multi-Company Dashboard", status: "Planned", detail: "Switch between client companies such as traders, manufacturers, societies, and trusts.", visibility: "CA Partner, Staff" },
      { title: "Client Access Control", status: "Planned", detail: "Client-level permissions for view only, data entry, full access, and restricted filing visibility.", visibility: "CA Partner" },
      { title: "Compliance Tracking", status: "Planned", detail: "GST, TDS, income tax, audit due dates, assignment status, and exception queue.", visibility: "CA Partner, Staff" },
      { title: "Work Assignment", status: "Planned", detail: "Assign clients and tasks to staff for bookkeeping, GST filing, TDS, audit, and review.", visibility: "Practice Admin" },
    ],
  },
  {
    title: "Platform Settings",
    description: "Controlled settings for subscription, integrations, audit, and AI enablement.",
    items: [
      { title: "Subscription & Billing", status: "Planned", detail: "Plan, renewals, invoices, usage metrics, limits, and upgrade path.", visibility: "Owner, Platform Admin" },
      { title: "Integrations", status: "Planned", detail: "GST portal, banking APIs, WhatsApp, email, payment gateway, UPI, and import/export connectors.", visibility: "Owner, Admin" },
      { title: "Audit & Logs", status: "Implemented", detail: "Party, voucher, account, document, and lifecycle events are visible through audit trail.", visibility: "Owner, Auditor", workspace: "audit" },
      { title: "AI Settings", status: "Planned", detail: "AI MIS, document upload, OCR extraction, categorization, reconciliation, and forecasting controls. Human review required before posting.", visibility: "Owner, Admin" },
    ],
  },
];

const MITRABOOKS_COMPLETION_PHASES = [
  ["Phase 2A", "Jun 12-14", "Landing pricing, shared SanMitra Razorpay configuration, billing metadata"],
  ["Phase 2B", "Jun 15-21", "Core settings backend contracts and tenant-scoped saves"],
  ["Phase 2C", "Jun 22-30", "CA practice client onboarding, multi-company access, and work queues"],
  ["Phase 2D", "Jul 1-12", "Integrations, document storage, OCR, AI settings, and provider controls"],
  ["Phase 2E", "Jul 13-19", "Browser E2E, tenant isolation, accounting guardrails, and staging validation"],
];

function settingsItemId(item) {
  return String(item.title || "")
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function allMitraBooksSettingsItems() {
  return MITRABOOKS_SETTINGS_GROUPS.flatMap((group) =>
    group.items.map((item) => ({ ...item, groupTitle: group.title })),
  );
}

function findMitraBooksSettingsItem(settingId) {
  return allMitraBooksSettingsItems().find((item) => settingsItemId(item) === settingId) || null;
}

const businessListState = {
  parties: {
    offset: 0,
    q: "",
    party_type: "",
    from_date: "",
    to_date: "",
  },
};


// ══════════════════════════════════════════════════════════════════════
// SECTION: PARTIES TABLE RENDERER
// NOTE  : renderBusinessPartiesTable, renderBusinessPartiesListFilters — list view only
// ══════════════════════════════════════════════════════════════════════

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


// ══════════════════════════════════════════════════════════════════════
// SECTION: VOUCHERS TABLE RENDERER
// NOTE  : renderBusinessVouchersTable — list view only; full CRUD at SECTION: VOUCHERS CRUD
// ══════════════════════════════════════════════════════════════════════

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

function settingsStatusClass(status) {
  const normalized = String(status || "").toLowerCase();
  if (normalized === "implemented") return "ok";
  if (normalized === "partial") return "warn";
  return "neutral";
}

function renderMitraBooksSettingsCard(item) {
  const settingId = settingsItemId(item);
  const action = item.workspace
    ? `<button class="secondary" type="button" data-business-action="workspace-view" data-workspace-view="${escapeHtml(item.workspace)}">Open Related Area</button>`
    : `<button class="secondary" type="button" data-business-action="settings-detail" data-settings-id="${escapeHtml(settingId)}">View Setup</button>`;
  return `
    <article class="settings-menu-card" data-settings-card="${escapeHtml(settingId)}">
      <div class="settings-card-head">
        <h5>${escapeHtml(item.title)}</h5>
        <span class="pill ${settingsStatusClass(item.status)}">${escapeHtml(item.status)}</span>
      </div>
      <p>${escapeHtml(item.detail)}</p>
      <div class="settings-card-meta">
        <span>${escapeHtml(item.visibility)}</span>
        ${action}
      </div>
    </article>
  `;
}

function renderMitraBooksSettingsDetail() {
  const item = findMitraBooksSettingsItem(activeSettingsDetailId);
  if (!item) return "";
  const isReady = String(item.status || "").toLowerCase() === "implemented";
  const action = item.workspace
    ? `<button class="primary" type="button" data-business-action="workspace-view" data-workspace-view="${escapeHtml(item.workspace)}">Open ${escapeHtml(item.title)}</button>`
    : `<button class="secondary" type="button" disabled>Backend contract pending</button>`;
  const evidence = item.workspace
    ? "Available through the linked MitraBooks workspace with existing tenant-scoped route checks."
    : "Documented as planned target scope; not yet backed by a tenant-scoped save API.";
  return `
    <section class="settings-detail-panel" data-settings-detail="${escapeHtml(activeSettingsDetailId)}">
      <div class="preview-heading compact">
        <div>
          <h5>${escapeHtml(item.title)}</h5>
          <p>${escapeHtml(item.groupTitle || "Settings")} · ${escapeHtml(item.visibility || "")}</p>
        </div>
        <span class="pill ${settingsStatusClass(item.status)}">${escapeHtml(item.status)}</span>
      </div>
      <div class="settings-detail-grid">
        <article>
          <strong>Current state</strong>
          <p>${escapeHtml(item.detail || "")}</p>
        </article>
        <article>
          <strong>${isReady ? "Verification" : "Gap"}</strong>
          <p>${escapeHtml(evidence)}</p>
        </article>
        <article>
          <strong>Deferred scope</strong>
          <p>${escapeHtml(isReady ? "No direct ledger mutation from settings; financial changes continue through controlled posting workflows." : "Final forms, permissions, audit events, and persistence will be added under the relevant backend contract.")}</p>
        </article>
      </div>
      <div class="settings-detail-actions">
        ${action}
        <button class="secondary" type="button" data-business-action="settings-back">Back to Settings</button>
      </div>
    </section>
  `;
}

function renderMitraBooksSettingsWorkspace() {
  const detail = activeSettingsDetailId ? renderMitraBooksSettingsDetail() : "";
  return `
    <div class="verification-panel erp-workspace-panel mitrabooks-settings-workspace">
      <div class="preview-heading compact">
        <div>
          <h4>MitraBooks Settings</h4>
          <p>Business-only settings for accounting, compliance, controls, CA practice management, billing, integrations, and AI readiness.</p>
        </div>
        <span class="pill ok">Business suite</span>
      </div>
      <div class="settings-roadmap-strip" aria-label="MitraBooks completion roadmap">
        ${MITRABOOKS_COMPLETION_PHASES.map(([phase, date, scope]) => `
          <article>
            <strong>${escapeHtml(phase)}</strong>
            <span>${escapeHtml(date)}</span>
            <small>${escapeHtml(scope)}</small>
          </article>
        `).join("")}
      </div>
      <div class="settings-visibility-strip">
        <span><strong>Core</strong> everyone sees</span>
        <span><strong>Module</strong> shown by enabled workflow</span>
        <span><strong>Platform</strong> owner/admin controlled</span>
      </div>
      ${detail}
      ${MITRABOOKS_SETTINGS_GROUPS.map((group) => `
        <section class="settings-menu-section">
          <div class="settings-section-heading">
            <h5>${escapeHtml(group.title)}</h5>
            <p>${escapeHtml(group.description)}</p>
          </div>
          <div class="settings-menu-grid">
            ${group.items.map(renderMitraBooksSettingsCard).join("")}
          </div>
        </section>
      `).join("")}
      <div class="settings-boundary-note">
        <strong>Accounting guardrail:</strong>
        Live financial balances, opening balances, posted entries, tax reports, and reconciliations must continue to come from posted journals and controlled workflows. Settings must not directly mutate ledger balances.
      </div>
    </div>
  `;
}

function renderCaStatusPill(status) {
  const map = { pending: "warn", invited: "warn", accepted: "ok", revoked: "err" };
  const label = { pending: "Pending", invited: "Credentials Sent", accepted: "Active", revoked: "Revoked" };
  return `<span class="pill ${map[status] || "warn"}">${label[status] || escapeHtml(status)}</span>`;
}

function renderCaAccessManagementSection() {
  const loading = caAccessLoading ? `<p class="settings-boundary-note">Loading CA users…</p>` : "";
  const rows = caAccessUsers.length === 0 && !caAccessLoading
    ? `<tr><td colspan="5" style="text-align:center;opacity:.6">No CA users yet. Send an invite below.</td></tr>`
    : caAccessUsers.map(u => `
      <tr>
        <td>${escapeHtml(u.full_name || "—")}</td>
        <td>${escapeHtml(u.email)}</td>
        <td>${renderCaStatusPill(u.status)}</td>
        <td style="font-size:.75rem;opacity:.7">${u.invited_at ? new Date(u.invited_at).toLocaleDateString("en-IN") : "—"}</td>
        <td style="white-space:nowrap;display:flex;gap:.35rem;align-items:center">
          ${(u.status === "accepted" || u.status === "invited") && u.user_id ? `
            <button class="secondary small" type="button"
              data-coa-action="ca-resend" data-ca-email="${escapeHtml(u.email)}"
              data-ca-name="${escapeHtml(u.full_name || "")}">Resend</button>
            <button class="secondary small" type="button"
              data-coa-action="ca-revoke" data-ca-user-id="${escapeHtml(u.user_id)}"
              data-ca-email="${escapeHtml(u.email)}">Revoke</button>
          ` : u.status === "revoked" && u.user_id ? `
            <button class="secondary small" type="button"
              data-coa-action="ca-reinstate" data-ca-user-id="${escapeHtml(u.user_id)}"
              data-ca-email="${escapeHtml(u.email)}">Reinstate</button>
          ` : ""}
          ${u.invite_id ? `
            <button class="secondary small" type="button" style="color:var(--err,#f55);border-color:var(--err,#f55)"
              data-coa-action="ca-delete" data-ca-invite-id="${escapeHtml(u.invite_id)}"
              data-ca-email="${escapeHtml(u.email)}">Cancel</button>
          ` : ""}
        </td>
      </tr>`).join("");

  const successMsg = caInviteSuccess ? `<div class="pill ok" style="margin-bottom:.5rem">${escapeHtml(caInviteSuccess)}</div>` : "";
  const errMsg = caInviteError ? `<div class="pill err" style="margin-bottom:.5rem">${escapeHtml(caInviteError)}</div>` : "";

  return `
    <section class="erp-panel" style="margin-bottom:1.5rem">
      <div class="preview-heading compact" style="margin-bottom:1rem">
        <div>
          <h5>CA Access — Invited Users</h5>
          <p>CAs you invite get read-only access to financial statements, GST returns, TDS register, and bank reconciliation.</p>
        </div>
      </div>
      ${loading}
      <table class="erp-table" style="margin-bottom:1.25rem">
        <thead><tr><th>Name</th><th>Email</th><th>Status</th><th>Invited</th><th></th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="settings-section-heading" style="margin-bottom:.5rem"><h6>Invite a CA</h6></div>
      ${successMsg}${errMsg}
      <form data-ca-invite-form style="display:grid;grid-template-columns:1fr 1fr auto;gap:.5rem;align-items:end">
        <label style="display:flex;flex-direction:column;gap:.25rem;font-size:.8rem">
          CA Name
          <input name="full_name" type="text" placeholder="e.g. CA Suresh Kumar" required maxlength="120" />
        </label>
        <label style="display:flex;flex-direction:column;gap:.25rem;font-size:.8rem">
          CA Email
          <input name="email" type="email" placeholder="ca@example.com" required maxlength="120" />
        </label>
        <button type="button" data-coa-action="ca-invite-submit">Send Invite</button>
      </form>
      <p style="font-size:.75rem;opacity:.6;margin-top:.5rem">The CA will receive an email with a temporary password and the MitraBooks login link. Use <strong>Resend</strong> on an existing CA to regenerate and email fresh credentials.</p>
    </section>`;
}

function renderCaViewerPortal() {
  const reportLinks = [
    ["Financial Statements", "reports", "Trial Balance, P&L, Balance Sheet, General Ledger"],
    ["GST Returns", "gst-returns", "GSTR-1, GSTR-3B, GSTR-2B ITC Reconciliation"],
    ["TDS / TCS Register", "tds-tcs", "Quarterly TDS/TCS register, section-wise"],
    ["Bank Reconciliation", "bank-recon", "Statement matching and BRS"],
  ];
  return `
    <div class="verification-panel erp-workspace-panel ca-practice-workspace">
      <div class="preview-heading compact">
        <div>
          <span class="workbench-kicker">Read-only access</span>
          <h4>CA Portal</h4>
          <p>You have read-only access to financial data for this business. Use the links below to navigate.</p>
        </div>
        <span class="pill ok">CA Viewer</span>
      </div>
      <div class="planned-org-module-grid">
        ${reportLinks.map(([title, workspace, copy]) => `
          <article>
            <div>
              <h4>${escapeHtml(title)}</h4>
              <button class="secondary" type="button"
                data-business-action="workspace-view"
                data-workspace-view="${escapeHtml(workspace)}">Open</button>
            </div>
            <p>${escapeHtml(copy)}</p>
          </article>`).join("")}
      </div>
    </div>`;
}

function renderCaPracticePortalWorkspace() {
  if (isCaViewer()) {
    return renderCaViewerPortal();
  }

  const model = plannedOrgWorkspaceModel("CA_PRACTICE");
  const summary = caPracticeSummary(lastCaDocuments);
  return `
    <div class="verification-panel erp-workspace-panel ca-practice-workspace">
      <div class="preview-heading compact">
        <div>
          <span class="workbench-kicker">Practice workbench</span>
          <h4>CA Practice Portal</h4>
          <p>Manage CA access to your books and track client document workflow.</p>
        </div>
        <span class="pill ok">Active</span>
      </div>
      ${isBusinessAdmin() ? renderCaAccessManagementSection() : ""}
      <div class="planned-org-kpis" style="margin-top:1rem">
        <article>
          <span>Client Tracking</span>
          <strong>${escapeHtml(String(summary.clientCount))}</strong>
          <small>Client books in this tenant queue.</small>
        </article>
        <article>
          <span>Review Queue</span>
          <strong>${escapeHtml(String(lastCaDocuments.length))}</strong>
          <small>Document metadata entries.</small>
        </article>
        <article>
          <span>Compliance</span>
          <strong>${escapeHtml(String(summary.compliance.length))}</strong>
          <small>Compliance areas tracked.</small>
        </article>
      </div>
      ${renderCaDocumentIntake(model.documentIntake)}
    </div>
  `;
}

function renderProfessionalSuiteWorkspace() {
  const model = plannedOrgWorkspaceModel("PROFESSIONAL");
  const cards = [
    ["Client Billing", "Create GST-ready service invoices in the active Sales workspace.", "sales", "Open Sales"],
    ["Client Accounts", "Maintain professional clients and vendors in Parties.", "parties", "Open Parties"],
    ["Receipts", "Record client receipts and journal entries through the voucher workflow.", "vouchers", "Open Vouchers"],
    ["Professional Reports", "Review ledger-backed financial statements and receivables.", "reports", "Open Reports"],
  ];
  return `
    <div class="verification-panel erp-workspace-panel professional-suite-workspace">
      <div class="preview-heading compact">
        <div>
          <span class="workbench-kicker">${escapeHtml(model.eyebrow)}</span>
          <h4>Professional Suite</h4>
          <p>${escapeHtml(model.lead)}</p>
        </div>
        <span class="pill ok">MitraBooks workflow active</span>
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
        ${cards.map(([title, copy, workspace, action]) => `
          <article>
            <div>
              <h4>${escapeHtml(title)}</h4>
              <button class="secondary" type="button" data-business-action="workspace-view" data-workspace-view="${escapeHtml(workspace)}">${escapeHtml(action)}</button>
            </div>
            <p>${escapeHtml(copy)}</p>
          </article>
        `).join("")}
      </div>
      <div class="settings-boundary-note">
        <strong>Current state:</strong>
        Professional Suite uses the active MitraBooks tenant for billing, parties, receipts, and reports. Deferred scope: retainer-specific automation and separate professional-only tenant context.
      </div>
    </div>
  `;
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: BUSINESS WORKSPACE DISPATCHER
// NOTE  : renderBusinessWorkspace — top-level if/else dispatches to each workspace render function
// ══════════════════════════════════════════════════════════════════════

function renderBusinessWorkspace() {
  if (activeBusinessWorkspace === "settings") {
    return renderMitraBooksSettingsWorkspace();
  }
  if (activeBusinessWorkspace === "ca-access") {
    return renderCaPracticePortalWorkspace();
  }
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
  // "gst-returns", "reconciliation" and "tds-tcs" are sidebar shortcuts into the
  // reports workspace (which hosts those tabs); the tab is pre-selected in setBusinessWorkspace.
  if (activeBusinessWorkspace === "reports"
      || activeBusinessWorkspace === "gst-returns"
      || activeBusinessWorkspace === "reconciliation"
      || activeBusinessWorkspace === "tds-tcs"
      || activeBusinessWorkspace === "bank-recon") {
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
  if (activeBusinessWorkspace === "coa") {
    return renderBusinessCoaWorkspace();
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

// Financial Health (CFO Insight) — every figure is computed server-side from the
// posted ledger (see app/modules/business/financial_health.py). The frontend only
// renders the trusted KPI/chart/alert payload; it never derives figures itself.

function fhKpiDisplay(kpi) {
  const unit = kpi.unit || "";
  const value = kpi.value;
  if (value === "—" || value === null || value === undefined || value === "") return "—";
  if (unit === "₹") return formatCurrency(value);
  if (unit === "%") return `${value}%`;
  if (unit === "x") return `${value}×`;
  return `${value}${unit ? " " + unit : ""}`;
}

function renderFhKpiCard(kpi) {
  return `
    <article class="fh-kpi fh-tone-${escapeHtml(kpi.tone || "neutral")}">
      <span class="fh-kpi-label">${escapeHtml(kpi.label)}</span>
      <strong class="fh-kpi-value">${escapeHtml(fhKpiDisplay(kpi))}</strong>
      <small class="fh-kpi-hint">${escapeHtml(kpi.hint || "")}</small>
    </article>
  `;
}

function renderFhBarChart(chart) {
  const series = Array.isArray(chart.series) ? chart.series : [];
  const labels = Array.isArray(chart.x) ? chart.x : [];
  const all = series.flatMap((s) => (s.data || []).map((v) => Math.abs(Number(v) || 0)));
  const maxValue = all.length ? Math.max(...all, 0.0001) : 1;
  const seriesClass = ["fh-bar-a", "fh-bar-b"];

  const groups = labels.map((label, i) => {
    const bars = series.map((s, si) => {
      const raw = Number((s.data || [])[i]) || 0;
      const height = Math.max(3, Math.round((Math.abs(raw) / maxValue) * 120));
      const neg = raw < 0 ? " fh-bar-neg" : "";
      return `<span class="fh-bar ${seriesClass[si] || "fh-bar-a"}${neg}" style="height:${height}px" title="${escapeHtml(s.name)}: ${escapeHtml(raw)}"></span>`;
    }).join("");
    return `
      <div class="fh-bar-group">
        <div class="fh-bars">${bars}</div>
        <small>${escapeHtml(label)}</small>
      </div>`;
  }).join("");

  const legend = series.length > 1
    ? `<div class="fh-legend">${series.map((s, si) =>
        `<span><i class="fh-dot ${seriesClass[si] || "fh-bar-a"}"></i>${escapeHtml(s.name)}</span>`).join("")}</div>`
    : "";

  return `
    <article class="fh-chart-card">
      <div class="fh-chart-head"><h5>${escapeHtml(chart.title)}</h5><span class="fh-unit">${escapeHtml(chart.unit || "")}</span></div>
      <div class="fh-chart" role="img" aria-label="${escapeHtml(chart.title)}">${groups || '<p class="muted">No data.</p>'}</div>
      ${legend}
    </article>`;
}

function renderFhAlert(alert) {
  return `
    <li class="fh-alert fh-alert-${escapeHtml(alert.severity || "info")}">
      <strong>${escapeHtml(alert.title || "")}</strong>
      <span>${escapeHtml(alert.message || "")}</span>
    </li>`;
}

// Render the model's plain-text narrative safely: escape everything, then turn
// blank-line-separated blocks into paragraphs and "-"/"•" lines into list items.
function fhFormatNarrative(text) {
  const lines = String(text || "").split(/\r?\n/);
  const out = [];
  let listItems = [];
  const flushList = () => {
    if (listItems.length) { out.push(`<ul>${listItems.join("")}</ul>`); listItems = []; }
  };
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) { flushList(); continue; }
    const bullet = line.match(/^[-*•]\s+(.*)$/);
    if (bullet) {
      listItems.push(`<li>${escapeHtml(bullet[1])}</li>`);
    } else {
      flushList();
      out.push(`<p>${escapeHtml(line)}</p>`);
    }
  }
  flushList();
  return out.join("");
}

// ══════════════════════════════════════════════════════════════════════
// SECTION: CHART OF ACCOUNTS (COA) WORKSPACE
// API   : GET /api/v1/accounting/accounts  POST .../accounts  PATCH .../accounts/{code}
// NOTE  : renderBusinessCoaWorkspace — name-edit only, codes are permanent, type filter dropdown
// ══════════════════════════════════════════════════════════════════════


// ── Chart of Accounts workspace ─────────────────────────────────────────────

const COA_TYPE_META = {
  asset:     { label: "Asset",     pillClass: "pill ok" },
  liability: { label: "Liability", pillClass: "pill danger" },
  equity:    { label: "Equity",    pillClass: "pill neutral" },
  income:    { label: "Income",    pillClass: "pill ok" },
  expense:   { label: "Expense",   pillClass: "pill warn" },
};
const COA_CLASS_LABELS = {
  personal: "Personal", real: "Real", nominal: "Nominal",
};

function coaTypePill(type) {
  const m = COA_TYPE_META[type] || { label: (type || "—"), pillClass: "pill" };
  return `<span class="${m.pillClass}">${m.label}</span>`;
}

function renderBusinessCoaWorkspace() {
  const accounts = Array.isArray(lastBusinessAccounts) ? lastBusinessAccounts : [];
  const filtered = coaTypeFilter ? accounts.filter((a) => a.type === coaTypeFilter) : accounts;

  const typeOptions = Object.entries(COA_TYPE_META)
    .map(([v, m]) => `<option value="${v}">${m.label}</option>`).join("");
  const classOptions = Object.entries(COA_CLASS_LABELS)
    .map(([v, l]) => `<option value="${v}">${l}</option>`).join("");
  const filterOptions = Object.entries(COA_TYPE_META)
    .map(([v, m]) => `<option value="${v}" ${coaTypeFilter === v ? "selected" : ""}>${m.label}</option>`).join("");

  const rows = filtered.length === 0
    ? `<tr><td colspan="6" class="empty-state-cell" style="text-align:center;padding:1.5rem">No accounts match the selected filter.</td></tr>`
    : filtered.map((a) => {
        const isSystem = a.is_cash_bank || a.is_receivable || a.is_payable;
        const systemBadge = isSystem ? `<span class="pill neutral" style="font-size:.72rem">System</span>` : "";
        return `
          <tr data-coa-code="${escapeHtml(a.code || "")}">
            <td class="mono-code">${escapeHtml(a.code || "—")}</td>
            <td class="coa-name-cell">
              <strong class="coa-name-display">${escapeHtml(a.name)}</strong>
              <input class="coa-name-input" type="text" value="${escapeHtml(a.name)}" style="display:none;width:100%" maxlength="200" />
            </td>
            <td>${coaTypePill(a.type)}</td>
            <td>${systemBadge}</td>
            <td><span class="pill ok" style="font-size:.72rem">Active</span></td>
            <td style="text-align:right;white-space:nowrap">
              <button class="secondary small" type="button" data-coa-action="edit-name" title="Edit name">&#9998;</button>
              <button class="secondary small" type="button" data-coa-action="save-name" style="display:none" title="Save">&#10003;</button>
              <button class="secondary small" type="button" data-coa-action="cancel-name" style="display:none" title="Cancel">&#10005;</button>
            </td>
          </tr>`;
      }).join("");

  return `
    <div class="verification-panel erp-workspace-panel" id="coa-workspace">
      <div class="preview-heading compact">
        <div>
          <h4>Chart of Accounts</h4>
          <p>${accounts.length} account${accounts.length !== 1 ? "s" : ""} in the ledger — account codes are permanent, only names can be edited.</p>
        </div>
        <button class="secondary" type="button" data-coa-action="toggle-add-form">+ Add Account</button>
      </div>

      <div id="coa-add-form" style="display:none" class="erp-form-inline">
        <h5 style="margin:0 0 .75rem">New Account</h5>
        <div style="display:grid;grid-template-columns:1fr 2fr 1fr 1fr;gap:.5rem .75rem;align-items:end">
          <label class="field-label">Code (optional)<input id="coa-new-code" type="text" maxlength="30" placeholder="e.g. 53099" /></label>
          <label class="field-label">Account Name *<input id="coa-new-name" type="text" maxlength="200" placeholder="e.g. Petty Cash" required /></label>
          <label class="field-label">Type *<select id="coa-new-type"><option value="">Select…</option>${typeOptions}</select></label>
          <label class="field-label">Classification *<select id="coa-new-class"><option value="">Select…</option>${classOptions}</select></label>
        </div>
        <div style="display:flex;gap:.5rem;margin-top:.75rem;align-items:center">
          <button class="primary small" type="button" data-coa-action="submit-add">Create Account</button>
          <button class="secondary small" type="button" data-coa-action="toggle-add-form">Cancel</button>
          <span id="coa-add-msg" style="font-size:.8rem;margin-left:.5rem"></span>
        </div>
      </div>

      <div style="display:flex;align-items:center;gap:1rem;margin-bottom:.75rem;flex-wrap:wrap">
        <label class="field-label" style="margin:0;display:flex;align-items:center;gap:.5rem;flex-direction:row">
          <span style="white-space:nowrap;font-size:.82rem">Filter by Type</span>
          <select id="coa-type-filter" style="min-width:140px">
            <option value="" ${coaTypeFilter === "" ? "selected" : ""}>All Types</option>
            ${filterOptions}
          </select>
        </label>
        <span class="pill neutral" style="font-size:.75rem">${filtered.length} of ${accounts.length} account${accounts.length !== 1 ? "s" : ""}</span>
        ${coaTypeFilter ? `<button class="secondary small" type="button" data-coa-action="clear-filter">Clear filter</button>` : ""}
        <div id="coa-msg" style="font-size:.82rem;margin-left:auto"></div>
      </div>

      <div class="table-preview compact-table erp-table">
        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Account Name</th>
              <th>Type</th>
              <th>System</th>
              <th>Status</th>
              <th style="text-align:right">Actions</th>
            </tr>
          </thead>
          <tbody id="coa-tbody">
            ${rows}
          </tbody>
        </table>
      </div>
    </div>`;
}

function coaShowMsg(el, text, ok) {
  if (!el) return;
  el.textContent = text;
  el.style.color = ok ? "var(--color-success, green)" : "var(--color-danger, red)";
  if (ok) setTimeout(() => { el.textContent = ""; }, 3000);
}

async function coaHandleAddSubmit() {
  const code = document.getElementById("coa-new-code")?.value.trim() || null;
  const name = document.getElementById("coa-new-name")?.value.trim() || "";
  const type = document.getElementById("coa-new-type")?.value;
  const classification = document.getElementById("coa-new-class")?.value;
  const msg = document.getElementById("coa-add-msg");

  if (!name || !type || !classification) {
    coaShowMsg(msg, "Name, Type and Classification are required.", false);
    return;
  }

  const body = { name, type, classification };
  if (code) body.code = code;

  const result = await apiRequest("mitrabooks", "/api/v1/accounting/accounts", {
    method: "POST",
    body: JSON.stringify(body),
  });

  if (!result.ok) {
    coaShowMsg(msg, statusDetailText(result.payload?.detail) || `Error creating account.`, false);
    return;
  }
  coaShowMsg(msg, "Account created.", true);
  ["coa-new-code", "coa-new-name"].forEach((id) => { const el = document.getElementById(id); if (el) el.value = ""; });
  ["coa-new-type", "coa-new-class"].forEach((id) => { const el = document.getElementById(id); if (el) el.value = ""; });
  await loadBusinessAccounts();
  dashboardPreview.innerHTML = renderBusinessWorkspace();
}

async function coaHandleSaveName(row) {
  const code = row.dataset.coaCode;
  const input = row.querySelector(".coa-name-input");
  const name = input?.value.trim() || "";
  const msg = document.getElementById("coa-msg");

  if (!name || name.length < 2) {
    coaShowMsg(msg, "Name must be at least 2 characters.", false);
    return;
  }

  const result = await apiRequest("mitrabooks", `/api/v1/accounting/accounts/${encodeURIComponent(code)}`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });

  if (!result.ok) {
    coaShowMsg(msg, statusDetailText(result.payload?.detail) || `Error updating account.`, false);
    return;
  }
  coaShowMsg(msg, `"${escapeHtml(name)}" saved.`, true);
  await loadBusinessAccounts();
  dashboardPreview.innerHTML = renderBusinessWorkspace();
}

function coaEnterEditMode(row) {
  row.querySelector(".coa-name-display").style.display = "none";
  row.querySelector(".coa-name-input").style.display = "";
  row.querySelector("[data-coa-action='edit-name']").style.display = "none";
  row.querySelector("[data-coa-action='save-name']").style.display = "";
  row.querySelector("[data-coa-action='cancel-name']").style.display = "";
  row.querySelector(".coa-name-input").focus();
}

function coaExitEditMode(row) {
  const original = row.querySelector(".coa-name-display").textContent;
  row.querySelector(".coa-name-input").value = original;
  row.querySelector(".coa-name-display").style.display = "";
  row.querySelector(".coa-name-input").style.display = "none";
  row.querySelector("[data-coa-action='edit-name']").style.display = "";
  row.querySelector("[data-coa-action='save-name']").style.display = "none";
  row.querySelector("[data-coa-action='cancel-name']").style.display = "none";
}

// ── End Chart of Accounts workspace ─────────────────────────────────────────


// ══════════════════════════════════════════════════════════════════════
// SECTION: FINANCIAL HEALTH WORKSPACE
// API   : GET /api/v1/business/financial-health?narrate=
// NOTE  : renderFinancialHealthWorkspace, fhFormatNarrative — AI narrative is advisory only
// ══════════════════════════════════════════════════════════════════════

function renderFinancialHealthWorkspace() {
  const data = lastFinancialHealth;

  // Lazy self-heal: fetch once whenever we render without data.
  if (!data && !financialHealthLoadInFlight) {
    setTimeout(() => { loadFinancialHealth(); }, 0);
  }

  if (!data) {
    return `
      <section class="financial-health-workspace erp-workspace-panel" aria-label="Financial Health">
        <div class="preview-heading compact">
          <div><h4>Financial Health</h4><p>Loading ledger-backed insights…</p></div>
        </div>
      </section>`;
  }

  const kpis = (data.kpis || []).map(renderFhKpiCard).join("");
  const charts = (data.charts || []).map(renderFhBarChart).join("");
  const alerts = (data.alerts || []).map(renderFhAlert).join("");

  // AI narrative is advisory prose over the same trusted figures; render the
  // model's text as paragraphs/bullets with a clear "AI-generated" disclaimer.
  const narrativeCard = data.narrative
    ? `
      <div class="fh-narrative">
        <div class="fh-narrative-head"><span class="pill ok">AI summary</span><small>Generated from the figures below — verify before acting.</small></div>
        <div class="fh-narrative-body">${fhFormatNarrative(data.narrative)}</div>
      </div>`
    : "";

  return `
    <section class="financial-health-workspace erp-workspace-panel" aria-label="Financial Health">
      <div class="preview-heading compact">
        <div>
          <h4>Financial Health</h4>
          <p>${escapeHtml(data.summary || "")}</p>
        </div>
        <button class="secondary" type="button" data-business-action="refresh-financial-health">Refresh</button>
      </div>
      ${narrativeCard}
      <div class="fh-kpi-grid">${kpis}</div>
      <div class="fh-section">
        <h5 class="fh-section-title">Alerts &amp; signals</h5>
        <ul class="fh-alerts">${alerts}</ul>
      </div>
      <div class="fh-charts-grid">${charts}</div>
      <p class="fh-footnote">As of ${escapeHtml(data.as_of || "")} · financial year from ${escapeHtml(data.financial_year_start || "")}. All figures computed from the posted ledger.</p>
    </section>
  `;
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: PARTIES — CRUD + dialogs
// API   : GET/POST /api/v1/business/parties  PATCH .../deactivate
// NOTE  : loadBusinessParties, createBusinessParty, updateBusinessParty
// ══════════════════════════════════════════════════════════════════════

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
    pan: data.pan?.trim().toUpperCase() || null,
    city: data.city?.trim() || null,
    state: data.state?.trim() || null,
    pincode: data.pincode?.trim() || null,
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
  const params = new URLSearchParams({ limit: "100" });
  Object.entries(caPracticeFilters).forEach(([key, value]) => {
    const normalized = String(value || "").trim();
    if (normalized) {
      params.set(key, normalized);
    }
  });
  const result = await apiRequest("mitrabooks", `/api/v1/business/ca-documents?${params.toString()}`, { method: "GET" });
  lastCaDocumentsResult = result;
  if (result.ok) {
    lastCaDocuments = Array.isArray(result.payload?.items) ? result.payload.items : [];
    if (currentExperience === "mitrabooks" && (activeOrgSelectorType() === "CA_PRACTICE" || activeBusinessWorkspace === "ca-access")) {
      dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig.mitrabooks);
      if (activeBusinessWorkspace === "ca-access") {
        dashboardPreview.innerHTML = renderBusinessWorkspace();
      }
    }
  } else {
    lastCaDocuments = [];
    setLoginStatus("warn", "Unable to load CA documents", statusDetailText(result.payload?.detail) || `Document metadata request failed with HTTP ${result.status}.`);
    if (currentExperience === "mitrabooks" && (activeOrgSelectorType() === "CA_PRACTICE" || activeBusinessWorkspace === "ca-access")) {
      dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig.mitrabooks);
      if (activeBusinessWorkspace === "ca-access") {
        dashboardPreview.innerHTML = renderBusinessWorkspace();
      }
    }
  }
  renderJson(apiOutput, { ca_documents: { ok: result.ok, status: result.status, count: lastCaDocuments.length, detail: result.payload?.detail || null } });
  return result;
}

async function loadCaAccessUsers() {
  caAccessLoading = true;
  if (activeBusinessWorkspace === "ca-access") {
    dashboardPreview.innerHTML = renderBusinessWorkspace();
  }
  const result = await apiRequest("mitrabooks", "/api/v1/business/ca/users", { method: "GET" });
  caAccessLoading = false;
  if (result.ok) {
    caAccessUsers = Array.isArray(result.payload?.ca_users) ? result.payload.ca_users : [];
  } else {
    caAccessUsers = [];
  }
  if (activeBusinessWorkspace === "ca-access") {
    dashboardPreview.innerHTML = renderBusinessWorkspace();
  }
  return result;
}

async function createCaPracticeDocument(form) {
  const formData = new FormData(form);
  const payload = {
    client_name: String(formData.get("client_name") || "").trim(),
    document_type: String(formData.get("document_type") || "").trim(),
    period: String(formData.get("period") || "").trim(),
    assigned_to: String(formData.get("assigned_to") || "").trim() || null,
    client_owner: String(formData.get("client_owner") || "").trim() || null,
    priority: String(formData.get("priority") || "normal").trim() || "normal",
    due_date: String(formData.get("due_date") || "").trim() || null,
    compliance_area: String(formData.get("compliance_area") || "").trim() || null,
    client_access_enabled: formData.get("client_access_enabled") === "true",
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
    pan: data.pan?.trim().toUpperCase() || null,
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
    method: "POST",
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
  const partyPan = button.getAttribute("data-party-pan") || "";
  const partyCity = button.getAttribute("data-party-city") || "";
  const partyState = button.getAttribute("data-party-state") || "";
  const partyPincode = button.getAttribute("data-party-pincode") || "";

  document.getElementById("business-party-edit-id").value = partyId;
  const editTypeSelect = document.getElementById("business-party-edit-type");
  if (editTypeSelect) editTypeSelect.value = partyType;
  document.getElementById("business-party-edit-name").value = partyName;
  document.getElementById("business-party-edit-gstin").value = partyGstin;
  const editPanInput = document.getElementById("business-party-edit-pan");
  if (editPanInput) editPanInput.value = partyPan;
  document.getElementById("business-party-edit-city").value = partyCity;
  document.getElementById("business-party-edit-state").value = partyState;
  document.getElementById("business-party-edit-pincode").value = partyPincode;
  document.getElementById("business-party-edit-label").textContent = `Editing ${partyName}`;

  dialog?.showModal();
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: BUSINESS WORKSPACE ROUTER — state + navigation
// NOTE  : setBusinessWorkspace, syncBusinessNavActiveState — drives activeBusinessWorkspace
// ══════════════════════════════════════════════════════════════════════

function setBusinessWorkspace(workspace) {
  if (currentExperience === "mitrabooks" && activeOrgSelectorType() !== "BUSINESS") {
    selectedOrgType = "BUSINESS";
    updateTrustedContextUi();
  }
  if (workspace !== "settings") {
    activeSettingsDetailId = "";
  }
  activeBusinessWorkspace = workspace;
  syncBusinessNavActiveState();
  dashboardPreview.innerHTML = workspace === "overview"
    ? renderDashboardPreview(experienceConfig.mitrabooks)
    : renderBusinessWorkspace();
  if (workspace === "overview" && hasTrustedSession()) {
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
  } else if (workspace === "reports" || workspace === "gst-returns" || workspace === "reconciliation" || workspace === "tds-tcs" || workspace === "bank-recon") {
    // Sidebar shortcuts open the reports workspace on a specific tab.
    if (workspace === "gst-returns") businessReportState.tab = "gst-returns";
    else if (workspace === "reconciliation") businessReportState.tab = "payment-allocation";
    else if (workspace === "tds-tcs") businessReportState.tab = "tds";
    else if (workspace === "bank-recon") businessReportState.tab = "bank-recon";
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
  } else if (workspace === "coa") {
    coaTypeFilter = "";
    loadBusinessAccounts();
  } else if (workspace === "ca-access") {
    lastCaDocumentsResult = null;
    lastCaDocuments = [];
    caAccessUsers = [];
    caInviteError = "";
    caInviteSuccess = "";
    if (isBusinessAdmin()) {
      loadCaAccessUsers();
    }
    loadCaPracticeDocuments();
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
      "gst-returns": "GST Returns",
      "reconciliation": "Reconciliation",
      "tds-tcs": "TDS / TCS",
      "bank-recon": "Bank Reconciliation",
      "ca-access": "CA Practice Portal",
      coa: "Chart of Accounts",
      settings: "Settings",
    };
    const plannedMeta = orgSelectorMeta[selectorOrgType];
    const label = isPlannedOrgWorkspace
      ? plannedMeta?.label || "Planned Workspace"
      : labels[activeBusinessWorkspace] || "Dashboard";
    topbarCurrent.textContent = label;
    updatePageHeader("MitraBooks", label, `${label} Workspace`);
  }
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: BUSINESS LIST FILTERING + PAGINATION
// NOTE  : applyBusinessListFilter, resetBusinessListFilter, pageBusinessList
// ══════════════════════════════════════════════════════════════════════

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
  { id: "aging", label: "AR/AP Aging" },
  { id: "statements", label: "Statements" },
  { id: "payment-allocation", label: "Payment Allocation" },
  { id: "gst-settlement", label: "GST Settlement" },
  { id: "gst-returns", label: "GST Returns" },
  { id: "tds", label: "TDS / TCS" },
  { id: "bank-recon", label: "Bank Reconciliation" },
  { id: "opening-yearend", label: "Opening & Year-End" },
  { id: "fixed-assets", label: "Fixed Assets" },
  { id: "dimensions", label: "Dimensions" },
  { id: "inventory", label: "Inventory" },
  { id: "itc-reversals", label: "ITC Reversals" },
  { id: "period-locks", label: "Period Locks" },
];

let lastPeriodLocks = [];
let lastGstSettlement = null;
let gstSettlementPeriod = todayIsoDate().slice(0, 7);
let lastGstr3b = null;
let lastGstr1 = null;
let lastCmp08 = null;
let lastGstr4 = null;
let lastGstr2bRecon = null;
let gstReturnType = "gstr3b";   // "gstr3b" | "gstr1" | "cmp08" | "gstr4" | "gstr2b"
let gstr3bPeriod = todayIsoDate().slice(0, 7);
let cmp08Quarter = currentFyQuarter();
let gstr4Fy = currentFinancialYear();
let lastItcReversal = null;
let lastTdsRegister = null;
let tdsQuarter = currentFyQuarter();
let lastBankRecon = null;
let bankReconAccountId = "";
let lastPartyStatement = null;
let statementPartyId = "";
let statementKind = "receivable";
let statementFromDate = "";
let statementToDate = "";
let lastObPreview = null;
let obCsvText = "";
let lastYePreview = null;
let yeFy = currentFinancialYear();
let lastFixedAssets = null;
let lastDepPreview = null;
let depFy = currentFinancialYear();
let faFormOpen = false;
let lastDimensions = null;       // masters cache (also feeds the form selects)
let lastDimensionReport = null;
let dimensionReportType = "cost_centre";
let lastEinvoiceView = null;     // e-invoice readiness/payload for the open invoice
let lastInventoryItems = null;   // item master cache (also feeds the line selects)
let lastStockRegister = null;
let lastClosingStockEntries = null;


// ══════════════════════════════════════════════════════════════════════
// SECTION: E-INVOICING (IRN foundation, credential-free)
// API   : GET /api/v1/business/invoices/{id}/einvoice  POST .../record
// NOTE  : loadEinvoiceView, recordEinvoiceIrn, renderEinvoiceSection — INV-01 v1.1 payload
// ══════════════════════════════════════════════════════════════════════

async function loadEinvoiceView(invoiceId) {
  const result = await apiRequest("mitrabooks", `/api/v1/business/invoices/${encodeURIComponent(invoiceId)}/einvoice`, { method: "GET" });
  lastEinvoiceView = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderSalesIfActive();
  renderJson(apiOutput, { einvoice_view: { ok: result.ok, invoice_id: invoiceId } });
}

function downloadInv01Json() {
  const v = lastEinvoiceView;
  if (!v?.payload) { setLoginStatus("warn", "Not ready", "Fix the readiness errors first."); return; }
  const blob = new Blob([JSON.stringify(v.payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `einvoice_${v.invoice_number || v.invoice_id}.json`;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
  renderJson(apiOutput, { einvoice_download: { invoice_id: v.invoice_id } });
}

async function recordEinvoiceIrn() {
  const v = lastEinvoiceView;
  if (!v) return;
  const irn = document.querySelector("[data-einv-irn]")?.value || "";
  const ackNo = document.querySelector("[data-einv-ackno]")?.value || "";
  const ackDate = document.querySelector("[data-einv-ackdate]")?.value || "";
  if (!irn.trim()) {
    setLoginStatus("warn", "IRN required", "Paste the 64-character IRN the portal returned.");
    return;
  }
  const result = await apiRequest("mitrabooks", `/api/v1/business/invoices/${encodeURIComponent(v.invoice_id)}/einvoice/record`, {
    method: "POST",
    body: JSON.stringify({ irn: irn.trim(), ack_no: ackNo.trim() || null, ack_date: ackDate || null }),
  });
  if (result.ok) {
    setLoginStatus("ok", "IRN recorded", "The invoice is marked e-invoice registered.");
    await loadEinvoiceView(v.invoice_id);
  } else {
    setLoginStatus("danger", "Could not record", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { einvoice_record: { ok: result.ok, status: result.status } });
}

function renderEinvoiceSection(inv) {
  if (String(inv.status).toLowerCase() !== "posted") return "";
  const v = lastEinvoiceView;
  if (!v) return `<div class="table-preview compact-table"><h4>e-Invoice (IRN)</h4><p class="muted">Checking e-invoice readiness...</p></div>`;
  if (v.ok === false) return `<div class="table-preview compact-table"><h4>e-Invoice (IRN)</h4><p class="muted">${escapeHtml(v.detail || "Unavailable.")}</p></div>`;
  const e = v.einvoice || {};
  if (e.status === "registered") {
    return `
      <div class="table-preview compact-table">
        <h4>e-Invoice (IRN) <span class="pill ok">registered</span></h4>
        <p class="muted">IRN: <code style="word-break:break-all;">${escapeHtml(e.irn || "")}</code><br>
        ${e.ack_no ? `Ack no. ${escapeHtml(e.ack_no)}` : ""}${e.ack_date ? ` · Ack date ${escapeHtml(e.ack_date)}` : ""} · recorded by ${escapeHtml(e.recorded_by || "")} ${escapeHtml(String(e.recorded_at || "").slice(0, 10))}</p>
      </div>`;
  }
  if (!v.eligible) {
    return `
      <div class="table-preview compact-table">
        <h4>e-Invoice (IRN) <span class="pill warn">not ready</span></h4>
        <ul class="muted" style="margin:6px 0 0 18px;">${(v.errors || []).map((err) => `<li>${escapeHtml(err)}</li>`).join("")}</ul>
      </div>`;
  }
  return `
    <div class="table-preview compact-table">
      <h4>e-Invoice (IRN) <span class="pill">payload ready</span></h4>
      <div class="report-date-controls">
        <button class="secondary" type="button" data-business-action="einv-download">Download INV-01 JSON</button>
        <span class="muted">Upload it on the e-invoice portal / offline utility, then record the result:</span>
      </div>
      <div class="report-date-controls">
        <label>IRN <input type="text" data-einv-irn maxlength="64" placeholder="64-character hash" style="min-width:260px;"></label>
        <label>Ack no. <input type="text" data-einv-ackno maxlength="30" style="width:130px;"></label>
        <label>Ack date <input type="date" data-einv-ackdate></label>
        <button class="primary" type="button" data-business-action="einv-record">Record IRN</button>
      </div>
      ${(v.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}
    </div>`;
}

// Current Indian financial year as "YYYY-YY" (FY starts April).
function currentFinancialYear() {
  const d = new Date();
  const startYear = d.getMonth() >= 3 ? d.getFullYear() : d.getFullYear() - 1;
  return `${startYear}-${String(startYear + 1).slice(-2)}`;
}

function recentFinancialYears(count = 4) {
  let startYear = Number(currentFinancialYear().slice(0, 4));
  const out = [];
  for (let i = 0; i < count; i++) {
    out.push(`${startYear}-${String(startYear + 1).slice(-2)}`);
    startYear -= 1;
  }
  return out;
}

// Current Indian-FY quarter as "YYYY-Q[1-4]" (FY starts April; Q1 = Apr-Jun).
function currentFyQuarter() {
  const d = new Date();
  const m = d.getMonth(); // 0-11
  const y = d.getFullYear();
  if (m >= 3 && m <= 5) return `${y}-Q1`;
  if (m >= 6 && m <= 8) return `${y}-Q2`;
  if (m >= 9 && m <= 11) return `${y}-Q3`;
  return `${y - 1}-Q4`;       // Jan-Mar belongs to the FY that started the prior April
}

// A handful of recent FY quarters for the CMP-08 picker.
function recentFyQuarters(count = 6) {
  const cur = currentFyQuarter();
  let [fy, q] = cur.split("-Q").map((x, i) => (i === 0 ? Number(x) : Number(x)));
  const out = [];
  for (let i = 0; i < count; i++) {
    out.push(`${fy}-Q${q}`);
    q -= 1;
    if (q < 1) { q = 4; fy -= 1; }
  }
  return out;
}
let lastItcReversedBills = [];
let itcReversalAsOf = todayIsoDate();

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
  agingKind: "receivable",
};

let lastBusinessTrialBalance = null;
let lastBusinessProfitLoss = null;
let lastBusinessBalanceSheet = null;
let lastBusinessReceivables = null;
let lastBusinessPayables = null;
let lastBusinessGeneralLedger = null;
let lastBusinessAging = null;

// Payment Allocation workflow state (open-item AR/AP matching).
const allocationState = {
  kind: "receivable",
  selectedPaymentId: "",
  lines: {},        // open_item_id -> entered amount (string)
  busy: false,
};
let lastUnallocatedPayments = null;
let lastAllocationOpenItems = null;
let lastAllocationReconciliation = null;
let lastAllocationResult = null;


// ══════════════════════════════════════════════════════════════════════
// SECTION: FINANCIAL REPORTS — workspace renderer + report framework
// API   : GET /api/v1/business/reports/... (all report tabs)
// NOTE  : refreshCurrentBusinessReport, reportResultPayload — dispatches to tab-specific renderers
// ══════════════════════════════════════════════════════════════════════

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
  } else if (tab === "aging") {
    await loadBusinessAging();
  } else if (tab === "payment-allocation") {
    await loadUnallocatedPayments();
    await loadAllocationReconciliation();
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
  } else if (tab === "gst-settlement") {
    await loadGstSettlementPreview(gstSettlementPeriod);
  } else if (tab === "gst-returns") {
    if (gstReturnType === "gstr1") { await loadGstr1(gstr3bPeriod); }
    else if (gstReturnType === "cmp08") { await loadCmp08(cmp08Quarter); }
    else if (gstReturnType === "gstr4") { await loadGstr4(gstr4Fy); }
    else if (gstReturnType === "gstr2b") { rerenderBusinessReportsIfActive(); }  // upload-driven
    else { await loadGstr3b(gstr3bPeriod); }
  } else if (tab === "itc-reversals") {
    await loadItcReversalPreview(itcReversalAsOf);
  } else if (tab === "tds") {
    await loadTdsRegister(tdsQuarter);
  } else if (tab === "bank-recon") {
    if (!hasLoadedBusinessAccounts()) await loadBusinessAccounts();
    if (bankReconAccountId) await loadBankReconciliation(bankReconAccountId);
    else rerenderBusinessReportsIfActive();
  } else if (tab === "statements") {
    if (!Array.isArray(lastBusinessParties) || lastBusinessParties.length === 0) await loadBusinessParties();
    if (statementPartyId) await loadPartyStatement();
    else rerenderBusinessReportsIfActive();
  } else if (tab === "opening-yearend") {
    // Workflow tab — both halves load on demand (Preview buttons).
    rerenderBusinessReportsIfActive();
  } else if (tab === "fixed-assets") {
    if (!hasLoadedBusinessAccounts()) await loadBusinessAccounts();
    await loadFixedAssets();
  } else if (tab === "dimensions") {
    await loadDimensions();
    await loadDimensionReport();
  } else if (tab === "inventory") {
    await loadInventoryItems();
    if (lastInventoryItems?.inventory_enabled) {
      await loadStockRegister();
      await loadClosingStockEntries();
    } else {
      rerenderBusinessReportsIfActive();
    }
  }
}

// ══════════════════════════════════════════════════════════════════════
// SECTION: GST SETTLEMENT (liability posting)
// API   : GET /api/v1/business/gst-settlement/preview  POST /api/v1/business/gst-settlement
// NOTE  : loadGstSettlementPreview, postGstSettlement, renderGstSettlementPanel
// ══════════════════════════════════════════════════════════════════════


async function loadGstSettlementPreview(period) {
  gstSettlementPeriod = period || gstSettlementPeriod;
  const result = await apiRequest("mitrabooks", `/api/v1/business/gst-settlement/preview?period=${encodeURIComponent(gstSettlementPeriod)}`, { method: "GET" });
  lastGstSettlement = result.ok ? result.payload : null;
  if (!result.ok) setLoginStatus("warn", "GST preview unavailable", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { gst_settlement_preview: { ok: result.ok, period: gstSettlementPeriod } });
}

function previewGstSettlementFromInput() {
  const input = document.querySelector("[data-gst-period]");
  loadGstSettlementPreview(input?.value || gstSettlementPeriod);
}

async function postGstSettlement() {
  const periodInput = document.querySelector("[data-gst-period]");
  const lockInput = document.querySelector("[data-gst-lock]");
  const period = periodInput?.value || gstSettlementPeriod;
  const result = await apiRequest("mitrabooks", "/api/v1/business/gst-settlement", {
    method: "POST",
    body: JSON.stringify({ period, lock_period: !!lockInput?.checked, accounting_entity_id: "primary" }),
  });
  if (result.ok) {
    lastGstSettlement = result.payload;
    setLoginStatus("ok", "GST settled", `Settlement posted for ${period}.`);
    rerenderBusinessReportsIfActive();
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can post a GST settlement.");
  } else {
    setLoginStatus("danger", "Settlement failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { gst_settlement: { ok: result.ok, status: result.status } });
}

function renderGstSettlementPanel() {
  const admin = isBusinessAdmin();
  const s = lastGstSettlement;
  const num = (v) => formatCurrency(Number(v || 0));
  const heads = [["IGST", "igst"], ["CGST", "cgst"], ["SGST", "sgst"]];
  let body = `<p class="muted">Select a month and preview the output-vs-input set-off before posting.</p>`;
  if (s && s.period === gstSettlementPeriod) {
    const posted = String(s.status) === "posted";
    const rows = heads.map(([label, key]) => `
      <tr>
        <td>${label}</td>
        <td class="amount">${num(s.output?.[key])}</td>
        <td class="amount">${num(s.input_credit?.[key])}</td>
        <td class="amount">${num(s.utilized?.[key])}</td>
        <td class="amount">${num(s.cash_payable?.[key])}</td>
        <td class="amount">${num(s.itc_carry_forward?.[key])}</td>
      </tr>
    `).join("");
    body = `
      <div class="preview-heading compact">
        <div><p>Set-off for ${escapeHtml(gstSettlementPeriod)} (statutory order: IGST credit first).</p></div>
        ${posted ? `<span class="pill ok">settled${s.period_locked ? " · period locked" : ""}</span>` : `<span class="pill warn">not settled</span>`}
      </div>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr><th>Head</th><th class="amount">Output (liability)</th><th class="amount">Input (ITC)</th><th class="amount">ITC used</th><th class="amount">Cash payable</th><th class="amount">ITC c/f</th></tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <div class="invoice-totals">
        <div><span>Total output GST</span><strong>${num(s.total_output)}</strong></div>
        <div><span>Total input GST (ITC)</span><strong>${num(s.total_input)}</strong></div>
        <div class="invoice-grand"><span>Net cash payable</span><strong>${num(s.net_cash_payable)}</strong></div>
      </div>
      ${s.note ? `<p class="muted">${escapeHtml(s.note)}</p>` : ""}
      ${posted ? `<p class="muted">Settled by ${escapeHtml(s.settled_by || "")}. Journal entry #${escapeHtml(s.journal_entry_id || "")} posted.</p>`
        : (admin && Number(s.total_output || 0) > 0 ? `
        <div class="report-date-controls">
          <label class="invoice-inter-toggle"><input type="checkbox" data-gst-lock checked> Lock this period after settlement</label>
          <button class="primary" type="button" data-business-action="gst-post">Post Settlement</button>
        </div>
        <p class="muted reversal-scope-note">Posts the set-off entry: Dr Output GST, Cr Input GST (utilised), Cr GST Payable (net cash).</p>
        ` : (admin ? "" : `<p class="muted">Only a tenant admin can post the settlement.</p>`))}
    `;
  }
  return `
    <div class="report-date-controls">
      <label>GST month <input type="month" data-gst-period value="${escapeHtml(gstSettlementPeriod)}"></label>
      <button class="secondary" type="button" data-business-action="gst-preview">Preview</button>
    </div>
    ${body}
  `;
}

// ---- GSTR-3B monthly summary return ------------------------------------- //

// ══════════════════════════════════════════════════════════════════════
// SECTION: GSTR-3B (monthly summary return)
// API   : GET /api/v1/business/returns/gstr-3b?period=
// NOTE  : loadGstr3b, renderGstr3bPanel, downloadGstr3bJson
// ══════════════════════════════════════════════════════════════════════

async function loadGstr3b(period) {
  gstr3bPeriod = period || gstr3bPeriod;
  const result = await apiRequest("mitrabooks", `/api/v1/business/returns/gstr-3b?period=${encodeURIComponent(gstr3bPeriod)}`, { method: "GET" });
  lastGstr3b = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { gstr3b: { ok: result.ok, period: gstr3bPeriod } });
}

function previewGstr3bFromInput() {
  const input = document.querySelector("[data-gstr3b-period]");
  loadGstr3b(input?.value || gstr3bPeriod);
}

function downloadGstr3bJson() {
  const j = lastGstr3b?.gstn_json;
  if (!j) { setLoginStatus("warn", "Nothing to download", "Load a GSTR-3B period first."); return; }
  const blob = new Blob([JSON.stringify(j, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `gstr3b_${gstr3bPeriod}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  renderJson(apiOutput, { gstr3b_download: { period: gstr3bPeriod } });
}

function renderGstr3bPanel() {
  const period = gstr3bPeriod;
  const controls = `
    <div class="report-date-controls">
      <label>Return month <input type="month" data-gstr3b-period value="${escapeHtml(period)}"></label>
      <button class="secondary" type="button" data-business-action="gstr3b-load">Load</button>
      <button class="secondary" type="button" data-business-action="gstr3b-download-json">Download GSTN JSON</button>
    </div>`;
  const r = lastGstr3b;
  if (!r) {
    return `${controls}<p class="muted">Loading GSTR-3B...</p>`;
  }
  if (r.ok === false) {
    return `${controls}${reportUnavailablePanel("GSTR-3B", r)}`;
  }
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const heads = [["IGST", "igst"], ["CGST", "cgst"], ["SGST", "sgst"]];
  const out = r.outward_supplies?.taxable || {};
  const itc = r.itc || {};
  const pay = r.tax_payment || {};
  const totals = r.totals || {};

  const itcRows = heads.map(([label, key]) => `
    <tr>
      <td>${label}</td>
      <td class="amount">${num(itc.available_rcm?.[key])}</td>
      <td class="amount">${num(itc.available_all_other?.[key])}</td>
      <td class="amount">${num(itc.reversed_others?.[key])}</td>
      <td class="amount"><strong>${num(itc.net_available?.[key])}</strong></td>
    </tr>`).join("");
  const rcm = r.outward_supplies?.inward_reverse_charge || {};
  const hasRcm = Number(rcm.taxable_value || 0) > 0
    || ["igst", "cgst", "sgst"].some((k) => Number(rcm[k] || 0) > 0);
  const payRows = heads.map(([label, key]) => `
    <tr>
      <td>${label}</td>
      <td class="amount">${num(pay[key]?.tax_payable)}</td>
      <td class="amount">${num(pay[key]?.paid_through_itc)}</td>
      <td class="amount">${num(pay[key]?.paid_in_cash)}</td>
    </tr>`).join("");

  return `
    ${controls}
    <div class="preview-heading compact">
      <div><p>GSTR-3B summary for ${escapeHtml(period)}${r.gstin ? ` · GSTIN ${escapeHtml(r.gstin)}` : ""}. Tax heads from the ledger; taxable value from posted invoices.</p></div>
      <span class="pill">Net cash ${num(totals.total_cash_payable)}</span>
    </div>

    <div class="table-preview compact-table">
      <h4>3.1 Outward taxable supplies</h4>
      <table>
        <thead><tr><th>Taxable value</th><th class="amount">IGST</th><th class="amount">CGST</th><th class="amount">SGST</th></tr></thead>
        <tbody><tr>
          <td class="amount">${num(out.taxable_value)}</td>
          <td class="amount">${num(out.igst)}</td>
          <td class="amount">${num(out.cgst)}</td>
          <td class="amount">${num(out.sgst)}</td>
        </tr></tbody>
      </table>
    </div>

    ${hasRcm ? `
    <div class="table-preview compact-table">
      <h4>3.1(d) Inward supplies liable to reverse charge</h4>
      <table>
        <thead><tr><th>Taxable value</th><th class="amount">IGST</th><th class="amount">CGST</th><th class="amount">SGST</th></tr></thead>
        <tbody><tr>
          <td class="amount">${num(rcm.taxable_value)}</td>
          <td class="amount">${num(rcm.igst)}</td>
          <td class="amount">${num(rcm.cgst)}</td>
          <td class="amount">${num(rcm.sgst)}</td>
        </tr></tbody>
      </table>
      <p class="muted">RCM liability of ${num(r.rcm_cash_payable)} must be paid in cash (account 22005) — it cannot be set off against ITC.</p>
    </div>` : ""}

    <div class="table-preview compact-table">
      <h4>4. Eligible ITC</h4>
      <table>
        <thead><tr><th>Head</th><th class="amount">RCM (4A3)</th><th class="amount">All other (4A5)</th><th class="amount">Reversed (4B)</th><th class="amount">Net (4C)</th></tr></thead>
        <tbody>${itcRows}</tbody>
      </table>
    </div>

    <div class="table-preview compact-table">
      <h4>6.1 Payment of tax</h4>
      <table>
        <thead><tr><th>Head</th><th class="amount">Tax payable</th><th class="amount">Paid via ITC</th><th class="amount">Paid in cash</th></tr></thead>
        <tbody>${payRows}</tbody>
      </table>
    </div>

    <div class="invoice-totals">
      <div><span>Total output tax</span><strong>${num(totals.total_output_tax)}</strong></div>
      <div><span>Net ITC</span><strong>${num(totals.total_itc_net)}</strong></div>
      <div class="invoice-grand"><span>Net cash payable</span><strong>${num(totals.total_cash_payable)}</strong></div>
    </div>
    ${(r.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}
  `;
}

// Wrapper: choose the return (GSTR-3B summary vs GSTR-1 outward detail).

// ══════════════════════════════════════════════════════════════════════
// SECTION: GST RETURNS — workspace switcher (3B / 1 / 2B / CMP-08 / GSTR-4)
// NOTE  : renderGstReturns, gstReturnType state variable
// ══════════════════════════════════════════════════════════════════════

function renderGstReturns() {
  const tabBtn = (id, label) => `
    <button class="report-tab ${gstReturnType === id ? "active" : ""}" type="button"
      data-business-action="gst-return-type" data-return-type="${id}">${label}</button>`;
  const toggle = `<div class="report-tabs" role="tablist" style="margin:0 0 10px;">
    ${tabBtn("gstr3b", "GSTR-3B (summary)")}${tabBtn("gstr1", "GSTR-1 (outward)")}${tabBtn("cmp08", "CMP-08 (composition)")}${tabBtn("gstr4", "GSTR-4 (annual)")}${tabBtn("gstr2b", "GSTR-2B (ITC recon)")}
  </div>`;
  let panel;
  if (gstReturnType === "gstr1") panel = renderGstr1Panel();
  else if (gstReturnType === "cmp08") panel = renderCmp08Panel();
  else if (gstReturnType === "gstr4") panel = renderGstr4Panel();
  else if (gstReturnType === "gstr2b") panel = renderGstr2bPanel();
  else panel = renderGstr3bPanel();
  return `${toggle}${panel}`;
}

// ---- GSTR-2B / ITC reconciliation (upload the portal JSON) --------------- //

// ══════════════════════════════════════════════════════════════════════
// SECTION: GSTR-2B RECONCILIATION
// API   : POST /api/v1/business/returns/gstr-2b/reconcile?period=
// NOTE  : reconcileGstr2b, renderGstr2bPanel — file-upload JSON match
// ══════════════════════════════════════════════════════════════════════

async function reconcileGstr2b() {
  const fileInput = document.querySelector("[data-gstr2b-file]");
  const periodInput = document.querySelector("[data-gstr2b-period]");
  const period = periodInput?.value || gstr3bPeriod;
  const file = fileInput?.files?.[0];
  if (!file) {
    setLoginStatus("warn", "Choose a file", "Upload the GSTR-2B JSON downloaded from the GST portal.");
    return;
  }
  let parsed;
  try {
    parsed = JSON.parse(await file.text());
  } catch (_e) {
    setLoginStatus("danger", "Invalid JSON", "Could not parse the uploaded file as JSON.");
    return;
  }
  gstr3bPeriod = period;
  const result = await apiRequest(
    "mitrabooks",
    `/api/v1/business/returns/gstr-2b/reconcile?period=${encodeURIComponent(period)}`,
    { method: "POST", body: JSON.stringify(parsed) },
  );
  lastGstr2bRecon = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { gstr2b_recon: { ok: result.ok, period } });
}

function renderGstr2bPanel() {
  const controls = `
    <div class="report-date-controls">
      <label>Return month <input type="month" data-gstr2b-period value="${escapeHtml(gstr3bPeriod)}"></label>
      <label>GSTR-2B JSON <input type="file" accept="application/json,.json" data-gstr2b-file></label>
      <button class="secondary" type="button" data-business-action="gstr2b-reconcile">Reconcile</button>
    </div>
    <p class="muted">Download GSTR-2B for the month from the GST portal and upload the JSON. It is matched against the input GST booked on your purchase bills.</p>`;
  const r = lastGstr2bRecon;
  if (!r) return controls;
  if (r.ok === false) return `${controls}${reportUnavailablePanel("GSTR-2B reconciliation", r)}`;
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const s = r.summary || {};

  const cards = [
    ["ITC as per 2B", s.itc_as_per_2b, "Total ITC the portal shows available"],
    ["ITC as per books", s.itc_as_per_books, "Input GST you have booked"],
    ["Matched", s.matched_itc, `${s.matched_count || 0} invoice(s) agree`],
    ["Available, not booked", s.available_not_booked, `${s.available_not_booked_count || 0} in 2B, missing in books`],
    ["At risk (not in 2B)", s.at_risk_not_in_2b, `${s.at_risk_count || 0} booked, absent from 2B`],
  ].map(([title, val, sub]) => `
    <article>
      <h4>${escapeHtml(title)}</h4>
      <div class="invoice-totals"><div class="invoice-grand"><span>${escapeHtml(sub)}</span><strong>${num(val)}</strong></div></div>
    </article>`).join("");

  const mismatchRows = (r.mismatch || []).map((m) => `
    <tr><td>${escapeHtml(m.gstin)}</td><td>${escapeHtml(m.invoice_number)}</td><td class="amount">${num(m.itc_2b)}</td><td class="amount">${num(m.itc_books)}</td><td class="amount">${num(m.difference)}</td></tr>`).join("");
  const only2bRows = (r.in_2b_not_in_books || []).map((g) => `
    <tr><td>${escapeHtml(g.gstin)}</td><td>${escapeHtml(g.invoice_number)}</td><td class="amount">${num(g.tax_total)}</td></tr>`).join("");
  const onlyBookRows = (r.in_books_not_in_2b || []).map((b) => `
    <tr><td>${escapeHtml(b.gstin)}</td><td>${escapeHtml(b.invoice_number)}</td><td class="amount">${num(b.tax_total)}</td></tr>`).join("");

  return `
    ${controls}
    <div class="preview-heading compact">
      <div><p>GSTR-2B reconciliation for ${escapeHtml(r.period || gstr3bPeriod)}.</p></div>
      <span class="pill ${Number(s.at_risk_not_in_2b || 0) > 0 ? "warn" : "ok"}">${Number(s.at_risk_not_in_2b || 0) > 0 ? "ITC at risk" : "clean"}</span>
    </div>
    <div class="dashboard-main-grid platform-grid">${cards}</div>

    <div class="table-preview compact-table">
      <h4>Mismatches (in both, amounts differ)</h4>
      <table>
        <thead><tr><th>Supplier GSTIN</th><th>Invoice</th><th class="amount">ITC (2B)</th><th class="amount">ITC (books)</th><th class="amount">Difference</th></tr></thead>
        <tbody>${mismatchRows || `<tr><td colspan="5" class="muted">No mismatches.</td></tr>`}</tbody>
      </table>
    </div>

    <div class="table-preview compact-table">
      <h4>In 2B, not in books (ITC available you may have missed)</h4>
      <table>
        <thead><tr><th>Supplier GSTIN</th><th>Invoice</th><th class="amount">ITC</th></tr></thead>
        <tbody>${only2bRows || `<tr><td colspan="3" class="muted">Nothing unbooked.</td></tr>`}</tbody>
      </table>
    </div>

    <div class="table-preview compact-table">
      <h4>In books, not in 2B (ITC at risk — Section 16(2)(aa))</h4>
      <table>
        <thead><tr><th>Supplier GSTIN</th><th>Invoice</th><th class="amount">ITC</th></tr></thead>
        <tbody>${onlyBookRows || `<tr><td colspan="3" class="muted">All booked ITC is reflected in 2B.</td></tr>`}</tbody>
      </table>
    </div>
    ${(r.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}
  `;
}

// ---- GSTR-4 annual composition return ----------------------------------- //

// ══════════════════════════════════════════════════════════════════════
// SECTION: GSTR-4 (composition annual return)
// API   : GET /api/v1/business/returns/gstr-4?financial_year=
// NOTE  : loadGstr4, renderGstr4Panel, downloadGstr4Json
// ══════════════════════════════════════════════════════════════════════

async function loadGstr4(fy) {
  gstr4Fy = fy || gstr4Fy;
  const result = await apiRequest("mitrabooks", `/api/v1/business/returns/gstr-4?financial_year=${encodeURIComponent(gstr4Fy)}`, { method: "GET" });
  lastGstr4 = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { gstr4: { ok: result.ok, fy: gstr4Fy } });
}

function previewGstr4FromInput() {
  const input = document.querySelector("[data-gstr4-fy]");
  loadGstr4(input?.value || gstr4Fy);
}

function downloadGstr4Json() {
  const j = lastGstr4?.gstn_json;
  if (!j) { setLoginStatus("warn", "Nothing to download", "Load a GSTR-4 financial year first."); return; }
  const blob = new Blob([JSON.stringify(j, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `gstr4_${gstr4Fy}.json`;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
  renderJson(apiOutput, { gstr4_download: { fy: gstr4Fy } });
}

function renderGstr4Panel() {
  const fyOpts = recentFinancialYears(4).map((fy) =>
    `<option value="${fy}" ${fy === gstr4Fy ? "selected" : ""}>FY ${fy}</option>`).join("");
  const controls = `
    <div class="report-date-controls">
      <label>Financial year <select data-gstr4-fy>${fyOpts}</select></label>
      <button class="secondary" type="button" data-business-action="gstr4-load">Load</button>
      <button class="secondary" type="button" data-business-action="gstr4-download-json">Download GSTN JSON</button>
    </div>`;
  const r = lastGstr4;
  if (!r) return `${controls}<p class="muted">Loading GSTR-4...</p>`;
  if (r.ok === false) return `${controls}${reportUnavailablePanel("GSTR-4", r)}`;
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const s = r.cmp08_summary || {};
  const out = r.outward_supplies || {};
  const inw = r.inward_supplies || {};
  const rateLabel = r.composition_rate != null ? `${escapeHtml(String(r.composition_rate))}%` : "—";

  const qRows = (s.quarters || []).map((q) => `
    <tr><td>${escapeHtml(q.quarter)}</td><td class="amount">${num(q.turnover)}</td><td class="amount">${num(q.cgst)}</td><td class="amount">${num(q.sgst)}</td><td class="amount">${num(q.total_tax)}</td></tr>`).join("");
  const inwRows = (kind, block) => (block?.rows || []).map((row) => `
    <tr><td>${escapeHtml(kind)}</td><td class="amount">${escapeHtml(String(row.rate ?? ""))}%</td><td class="amount">${num(row.taxable_value)}</td><td class="amount">${num(row.igst)}</td><td class="amount">${num(row.cgst)}</td><td class="amount">${num(row.sgst)}</td></tr>`).join("");
  const inwardBody = `${inwRows("Registered", inw.registered)}${inwRows("Unregistered", inw.unregistered)}`;

  return `
    ${controls}
    <div class="preview-heading compact">
      <div><p>GSTR-4 annual return for FY ${escapeHtml(r.financial_year || gstr4Fy)}${r.gstin ? ` · GSTIN ${escapeHtml(r.gstin)}` : ""} · ${escapeHtml(r.composition_category || "composition")} @ ${rateLabel}.</p></div>
      <span class="pill">Annual tax ${num(out.total_tax)}</span>
    </div>

    <div class="table-preview compact-table">
      <h4>Table 5 — self-assessed liability (CMP-08, quarter-wise)</h4>
      <table>
        <thead><tr><th>Quarter</th><th class="amount">Turnover</th><th class="amount">CGST</th><th class="amount">SGST</th><th class="amount">Tax</th></tr></thead>
        <tbody>${qRows}</tbody>
        <tfoot><tr><th>Total</th><td class="amount">${num(s.total_turnover)}</td><td class="amount">${num(s.cgst)}</td><td class="amount">${num(s.sgst)}</td><td class="amount"><strong>${num(s.total_tax)}</strong></td></tr></tfoot>
      </table>
    </div>

    <div class="table-preview compact-table">
      <h4>Table 6 — outward supplies (composition liability)</h4>
      <table>
        <thead><tr><th class="amount">Turnover</th><th class="amount">Rate</th><th class="amount">CGST</th><th class="amount">SGST</th><th class="amount">Tax</th></tr></thead>
        <tbody><tr><td class="amount">${num(out.turnover)}</td><td class="amount">${rateLabel}</td><td class="amount">${num(out.cgst)}</td><td class="amount">${num(out.sgst)}</td><td class="amount"><strong>${num(out.total_tax)}</strong></td></tr></tbody>
      </table>
    </div>

    <div class="table-preview compact-table">
      <h4>Table 4 — inward supplies (purchases)</h4>
      <table>
        <thead><tr><th>Supplier</th><th class="amount">Rate</th><th class="amount">Taxable</th><th class="amount">IGST</th><th class="amount">CGST</th><th class="amount">SGST</th></tr></thead>
        <tbody>${inwardBody || `<tr><td colspan="6" class="muted">No inward supplies recorded.</td></tr>`}</tbody>
      </table>
    </div>
    ${(r.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}
  `;
}

// ---- CMP-08 quarterly composition statement ----------------------------- //
async function loadCmp08(quarter) {
  cmp08Quarter = quarter || cmp08Quarter;
  const result = await apiRequest("mitrabooks", `/api/v1/business/returns/cmp-08?quarter=${encodeURIComponent(cmp08Quarter)}`, { method: "GET" });
  lastCmp08 = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { cmp08: { ok: result.ok, quarter: cmp08Quarter } });
}

function previewCmp08FromInput() {
  const input = document.querySelector("[data-cmp08-quarter]");
  loadCmp08(input?.value || cmp08Quarter);
}

function downloadCmp08Json() {
  const j = lastCmp08?.gstn_json;
  if (!j) { setLoginStatus("warn", "Nothing to download", "Load a CMP-08 quarter first."); return; }
  const blob = new Blob([JSON.stringify(j, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `cmp08_${cmp08Quarter}.json`;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
  renderJson(apiOutput, { cmp08_download: { quarter: cmp08Quarter } });
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: GST COMPOSITION — CMP-08 (quarterly statement)
// API   : GET /api/v1/business/returns/cmp-08?quarter=
// NOTE  : renderCmp08Panel, previewCmp08FromInput, postCmp08Liability
// ══════════════════════════════════════════════════════════════════════

function renderCmp08Panel() {
  const quarterOpts = recentFyQuarters(6).map((q) =>
    `<option value="${q}" ${q === cmp08Quarter ? "selected" : ""}>${q.replace("-Q", " · Q")}</option>`).join("");
  const controls = `
    <div class="report-date-controls">
      <label>Quarter <select data-cmp08-quarter>${quarterOpts}</select></label>
      <button class="secondary" type="button" data-business-action="cmp08-load">Load</button>
      <button class="secondary" type="button" data-business-action="cmp08-download-json">Download GSTN JSON</button>
    </div>`;
  const r = lastCmp08;
  if (!r) return `${controls}<p class="muted">Loading CMP-08...</p>`;
  if (r.ok === false) return `${controls}${reportUnavailablePanel("CMP-08", r)}`;
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const out = r.outward_supplies || {};
  const pay = r.tax_payable || {};
  const rateLabel = r.composition_rate != null ? `${escapeHtml(String(r.composition_rate))}%` : "—";
  return `
    ${controls}
    <div class="preview-heading compact">
      <div><p>CMP-08 for ${escapeHtml(r.quarter || cmp08Quarter)}${r.gstin ? ` · GSTIN ${escapeHtml(r.gstin)}` : ""} · ${escapeHtml(r.composition_category || "composition")} @ ${rateLabel}.</p></div>
      <span class="pill">Payable ${num(pay.total)}</span>
    </div>
    <div class="table-preview compact-table">
      <h4>Table 3 — self-assessed liability</h4>
      <table>
        <thead><tr><th>Particulars</th><th class="amount">Value</th><th class="amount">IGST</th><th class="amount">CGST</th><th class="amount">SGST</th></tr></thead>
        <tbody>
          <tr><td>Outward supplies (incl. composition turnover)</td><td class="amount">${num(out.turnover)}</td><td class="amount">${num(out.igst)}</td><td class="amount">${num(out.cgst)}</td><td class="amount">${num(out.sgst)}</td></tr>
          <tr><td>Inward supplies (reverse charge)</td><td class="amount">—</td><td class="amount">${num(r.inward_reverse_charge?.igst)}</td><td class="amount">${num(r.inward_reverse_charge?.cgst)}</td><td class="amount">${num(r.inward_reverse_charge?.sgst)}</td></tr>
        </tbody>
        <tfoot><tr><th colspan="2">Tax payable (incl. interest ${num(pay.interest)})</th><td class="amount">${num(pay.igst)}</td><td class="amount">${num(pay.cgst)}</td><td class="amount">${num(pay.sgst)}</td></tr></tfoot>
      </table>
    </div>
    <div class="invoice-totals">
      <div class="invoice-grand"><span>Total tax payable</span><strong>${num(pay.total)}</strong></div>
    </div>
    ${(r.liability_posting || []).length ? `
    <p class="muted">✓ Liability posted: journal entry #${escapeHtml(String(r.liability_posting[0].journal_entry_id))} dated ${escapeHtml(r.liability_posting[0].entry_date)}. Reverse it to redo.</p>`
    : (Number(out.total_tax || 0) > 0 && isBusinessAdmin() ? `
    <div class="report-date-controls">
      <button class="primary" type="button" data-business-action="cmp08-post">Post liability to ledger</button>
      <span class="muted">Dr 54007 GST Expense (Composition) / Cr 22004 GST Payable — outward levy only; RCM is already booked per bill.</span>
    </div>` : "")}
    ${(r.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}
  `;
}

async function postCmp08Liability() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/returns/cmp-08/post", {
    method: "POST",
    headers: { "X-Idempotency-Key": `cmp08-${cmp08Quarter}` },
    body: JSON.stringify({ quarter: cmp08Quarter }),
  });
  if (result.ok) {
    setLoginStatus("ok", "Liability posted", `CMP-08 ${cmp08Quarter}: ${formatCurrency(Number(result.payload?.amount || 0))} — journal entry #${result.payload?.journal_entry_id}.`);
    await loadCmp08(cmp08Quarter);
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can post the composition liability.");
  } else {
    setLoginStatus("danger", "Posting failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { cmp08_post: { ok: result.ok, status: result.status } });
}

// ---- GSTR-1 outward-supplies return ------------------------------------- //
// ---- Opening balances (CSV import) + year-end close ----------------------- //
async function downloadObTemplate() {
  const result = await downloadApiFile("mitrabooks", "/api/v1/business/opening-balances/template", "opening_balances_template.csv");
  renderJson(apiOutput, { ob_template: { ok: result.ok } });
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: OPENING BALANCES + YEAR-END CLOSE
// API   : POST /api/v1/business/opening-balances  POST /api/v1/business/year-end/close
// NOTE  : previewOpeningBalances, postOpeningBalances, previewYearEnd, postYearEndClose
// ══════════════════════════════════════════════════════════════════════

async function previewOpeningBalances() {
  const fileInput = document.querySelector("[data-ob-file]");
  const asOfInput = document.querySelector("[data-ob-asof]");
  const file = fileInput?.files?.[0];
  if (!file && !obCsvText) {
    setLoginStatus("warn", "Choose a file", "Upload the opening-balance CSV (download the template for the format).");
    return;
  }
  if (file) obCsvText = await file.text();
  const body = { csv: obCsvText };
  if (asOfInput?.value) body.as_of = asOfInput.value;
  const result = await apiRequest("mitrabooks", "/api/v1/business/opening-balances/preview", {
    method: "POST", body: JSON.stringify(body),
  });
  lastObPreview = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { ob_preview: { ok: result.ok, status: result.status } });
}

async function postOpeningBalances() {
  if (!obCsvText || !lastObPreview || lastObPreview.ok === false || !lastObPreview.can_post) {
    setLoginStatus("warn", "Preview first", "Upload and preview a clean file (zero errors) before posting.");
    return;
  }
  const allowDup = !!document.querySelector("[data-ob-allow-duplicate]")?.checked;
  const body = { csv: obCsvText, as_of: lastObPreview.as_of, allow_duplicate: allowDup };
  const result = await apiRequest("mitrabooks", "/api/v1/business/opening-balances", {
    method: "POST",
    headers: { "X-Idempotency-Key": `opening-balance-${Date.now()}` },
    body: JSON.stringify(body),
  });
  if (result.ok) {
    setLoginStatus("ok", "Opening balances posted", `Journal entry #${result.payload?.journal_entry_id} with ${result.payload?.line_count} line(s).`);
    obCsvText = "";
    lastObPreview = null;
    rerenderBusinessReportsIfActive();
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can post opening balances.");
  } else {
    setLoginStatus("danger", "Posting failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { ob_post: { ok: result.ok, status: result.status } });
}

async function previewYearEnd() {
  const fySel = document.querySelector("[data-ye-fy]");
  yeFy = fySel?.value || yeFy;
  const result = await apiRequest("mitrabooks", `/api/v1/business/year-end/preview?financial_year=${encodeURIComponent(yeFy)}`, { method: "GET" });
  lastYePreview = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { ye_preview: { ok: result.ok, fy: yeFy } });
}

async function postYearEndClose() {
  if (!lastYePreview || lastYePreview.ok === false || !lastYePreview.can_post) {
    setLoginStatus("warn", "Preview first", "Load a year-end preview that is ready to close.");
    return;
  }
  const result = await apiRequest("mitrabooks", "/api/v1/business/year-end/close", {
    method: "POST",
    headers: { "X-Idempotency-Key": `year-end-${yeFy}` },
    body: JSON.stringify({ financial_year: yeFy }),
  });
  if (result.ok) {
    setLoginStatus("ok", "Year closed", `FY ${yeFy} closed — journal entry #${result.payload?.journal_entry_id}, net result ${formatCurrency(Number(result.payload?.net_profit || 0))}.`);
    await previewYearEnd();
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can post the year-end close.");
  } else {
    setLoginStatus("danger", "Close failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { ye_close: { ok: result.ok, status: result.status } });
}

function renderOpeningBalancesSection() {
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const controls = `
    <div class="report-date-controls">
      <label>Opening date <input type="date" data-ob-asof value="${escapeHtml(lastObPreview?.as_of || "")}" placeholder="FY start"></label>
      <label>Balances CSV <input type="file" accept=".csv,text/csv" data-ob-file></label>
      <button class="secondary" type="button" data-business-action="ob-preview">Preview</button>
      <button class="secondary" type="button" data-business-action="ob-template">Download template</button>
    </div>
    <p class="muted">Upload account-wise opening balances (party-wise for Sundry Debtors/Creditors). Nothing posts until you confirm the preview. Leave the date empty for the financial-year start.</p>`;
  const r = lastObPreview;
  if (!r) return `${controls}`;
  if (r.ok === false) return `${controls}${reportUnavailablePanel("Opening balances", r)}`;

  const errorRows = (r.errors || []).map((e) => `
    <tr><td>${escapeHtml(String(e.row_number || ""))}</td><td>${escapeHtml(e.account || "")}</td><td>${escapeHtml((e.problems || []).join("; "))}</td></tr>`).join("");
  const lineRows = (r.lines || []).map((l) => `
    <tr>
      <td>${escapeHtml(`${l.account_code} - ${l.account_name}`)}</td>
      <td>${escapeHtml(l.party_name || "")}</td>
      <td class="amount">${Number(l.debit || 0) ? num(l.debit) : ""}</td>
      <td class="amount">${Number(l.credit || 0) ? num(l.credit) : ""}</td>
    </tr>`).join("");
  const bal = r.balancing_line;
  const existing = r.existing_opening_entries || [];

  return `
    ${controls}
    <div class="preview-heading compact">
      <div><p>${escapeHtml(String(r.line_count))} line(s) resolved as of ${escapeHtml(r.as_of)} · debit ${num(r.total_debit)} · credit ${num(r.total_credit)}.</p></div>
      <span class="pill ${r.can_post ? "ok" : "warn"}">${r.can_post ? "ready to post" : `${escapeHtml(String(r.error_count))} error(s)`}</span>
    </div>
    ${errorRows ? `
    <div class="table-preview compact-table">
      <h4>Fix these rows and re-upload</h4>
      <table><thead><tr><th>CSV row</th><th>Account</th><th>Problem</th></tr></thead><tbody>${errorRows}</tbody></table>
    </div>` : ""}
    <div class="table-preview compact-table">
      <h4>Opening journal preview</h4>
      <table>
        <thead><tr><th>Account</th><th>Party</th><th class="amount">Debit</th><th class="amount">Credit</th></tr></thead>
        <tbody>
          ${lineRows}
          ${bal ? `<tr><td><em>${escapeHtml(`${bal.account_code} - ${bal.account_name}`)} (balancing)</em></td><td></td><td class="amount">${Number(bal.debit || 0) ? num(bal.debit) : ""}</td><td class="amount">${Number(bal.credit || 0) ? num(bal.credit) : ""}</td></tr>` : ""}
        </tbody>
      </table>
    </div>
    ${existing.length ? `<p class="muted">⚠ Opening journal already posted: entry #${escapeHtml(String(existing[0].journal_entry_id))} dated ${escapeHtml(existing[0].entry_date)}. Reverse it first, or tick the override.
      <label style="display:inline-flex;gap:4px;align-items:center;margin-left:8px;"><input type="checkbox" data-ob-allow-duplicate> Post anyway</label></p>` : ""}
    ${r.can_post && isBusinessAdmin() ? `
    <div class="report-date-controls">
      <button class="primary" type="button" data-business-action="ob-post">Post opening balances</button>
    </div>` : (r.can_post ? `<p class="muted">Only a tenant admin can post opening balances.</p>` : "")}
    ${(r.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}
  `;
}

function renderYearEndSection() {
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const fyOpts = recentFinancialYears(4).map((fy) =>
    `<option value="${fy}" ${fy === yeFy ? "selected" : ""}>FY ${fy}</option>`).join("");
  const controls = `
    <div class="report-date-controls">
      <label>Financial year <select data-ye-fy>${fyOpts}</select></label>
      <button class="secondary" type="button" data-business-action="ye-preview">Preview close</button>
    </div>
    <p class="muted">Closing zeroes the year's income and expense accounts into Retained Earnings on 31 March. Post all adjustments (depreciation, provisions) first.</p>`;
  const r = lastYePreview;
  if (!r) return controls;
  if (r.ok === false) return `${controls}${reportUnavailablePanel("Year-end close", r)}`;

  const lineRows = (r.closing_lines || []).map((l) => `
    <tr>
      <td>${escapeHtml(`${l.account_code} - ${l.account_name}`)}</td>
      <td>${escapeHtml(l.account_type || "")}</td>
      <td class="amount">${Number(l.debit || 0) ? num(l.debit) : ""}</td>
      <td class="amount">${Number(l.credit || 0) ? num(l.credit) : ""}</td>
    </tr>`).join("");
  const re = r.retained_earnings || {};
  const closed = (r.already_closed || []).length > 0;
  const profit = Number(r.net_profit || 0) >= 0;

  return `
    ${controls}
    <div class="preview-heading compact">
      <div><p>FY ${escapeHtml(r.financial_year)} (${escapeHtml(r.from_date)} → ${escapeHtml(r.to_date)}): income ${num(r.income_total)} − expenses ${num(r.expense_total)} = <strong>${profit ? "profit" : "loss"} ${num(r.net_profit)}</strong>.</p></div>
      <span class="pill ${closed ? "warn" : (r.can_post ? "ok" : "")}">${closed ? "already closed" : (r.can_post ? "ready to close" : "no activity")}</span>
    </div>
    ${closed ? `<p class="muted">⚠ FY ${escapeHtml(r.financial_year)} was closed by journal entry #${escapeHtml(String(r.already_closed[0].journal_entry_id))}. Reverse that entry to reopen the year.</p>` : ""}
    <div class="table-preview compact-table">
      <h4>Closing journal preview (31 March)</h4>
      <table>
        <thead><tr><th>Account</th><th>Type</th><th class="amount">Debit</th><th class="amount">Credit</th></tr></thead>
        <tbody>
          ${lineRows || `<tr><td colspan="4" class="muted">No income or expense activity this year.</td></tr>`}
          ${(Number(re.debit || 0) || Number(re.credit || 0)) ? `<tr><td><em>${escapeHtml(`${re.account_code} - ${re.account_name}`)}</em></td><td>equity</td><td class="amount">${Number(re.debit || 0) ? num(re.debit) : ""}</td><td class="amount">${Number(re.credit || 0) ? num(re.credit) : ""}</td></tr>` : ""}
        </tbody>
      </table>
    </div>
    ${r.can_post && isBusinessAdmin() ? `
    <div class="report-date-controls">
      <button class="primary" type="button" data-business-action="ye-post">Post year-end close</button>
    </div>` : (r.can_post ? `<p class="muted">Only a tenant admin can post the year-end close.</p>` : "")}
    ${(r.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}
  `;
}

function renderOpeningYearEndPanel() {
  return `
    <div class="table-preview compact-table"><h4>Opening balances (CSV import)</h4></div>
    ${renderOpeningBalancesSection()}
    <hr style="margin:18px 0;border:none;border-top:1px solid var(--line,#ddd);">
    <div class="table-preview compact-table"><h4>Year-end close</h4></div>
    ${renderYearEndSection()}
  `;
}

// ---- Fixed assets register + depreciation --------------------------------- //

// ══════════════════════════════════════════════════════════════════════
// SECTION: FIXED ASSETS + DEPRECIATION
// API   : GET/POST /api/v1/business/fixed-assets  POST /api/v1/business/depreciation/run
// NOTE  : loadFixedAssets, createFixedAssetFromForm, renderFixedAssetsPanel
// ══════════════════════════════════════════════════════════════════════

function fixedAssetAccountOptions() {
  // Fixed-asset accounts live in the 16xxx subclass (16099 is the contra).
  return businessAccountsForSelection().filter((acc) =>
    String(acc.code || "").startsWith("16") && String(acc.code) !== "16099");
}

async function loadFixedAssets() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/fixed-assets", { method: "GET" });
  lastFixedAssets = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { fixed_assets: { ok: result.ok, count: result.payload?.count || 0 } });
}

async function createFixedAssetFromForm() {
  const form = document.querySelector("[data-fa-form]");
  if (!form) return;
  const val = (sel) => form.querySelector(sel)?.value ?? "";
  const method = val("select[name='fa_method']") || "slm";
  const body = {
    asset_name: val("input[name='fa_name']").trim(),
    asset_account_code: val("select[name='fa_account']") || "16001",
    purchase_date: val("input[name='fa_date']"),
    cost: val("input[name='fa_cost']"),
    salvage_value: val("input[name='fa_salvage']") || "0",
    method,
    useful_life_years: method === "slm" ? val("input[name='fa_life']") : null,
    depreciation_rate: method === "wdv" ? val("input[name='fa_rate']") : null,
    opening_accumulated_depreciation: val("input[name='fa_opening_acc']") || "0",
    notes: val("input[name='fa_notes']").trim() || null,
  };
  if (!body.asset_name || !body.purchase_date || !Number(body.cost)) {
    setLoginStatus("warn", "Fill the asset details", "Name, purchase date and cost are required.");
    return;
  }
  const result = await apiRequest("mitrabooks", "/api/v1/business/fixed-assets", {
    method: "POST", body: JSON.stringify(body),
  });
  if (result.ok) {
    setLoginStatus("ok", "Asset registered", `${result.payload?.asset_name} added to the register.`);
    faFormOpen = false;
    await loadFixedAssets();
  } else {
    setLoginStatus("danger", "Could not register", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { fixed_asset_create: { ok: result.ok, status: result.status } });
}

async function previewDepreciation() {
  const fySel = document.querySelector("[data-dep-fy]");
  depFy = fySel?.value || depFy;
  const result = await apiRequest("mitrabooks", `/api/v1/business/depreciation/preview?financial_year=${encodeURIComponent(depFy)}`, { method: "GET" });
  lastDepPreview = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { depreciation_preview: { ok: result.ok, fy: depFy } });
}

async function postDepreciationRun() {
  if (!lastDepPreview || lastDepPreview.ok === false || !lastDepPreview.can_post) {
    setLoginStatus("warn", "Preview first", "Load a depreciation preview that is ready to post.");
    return;
  }
  const result = await apiRequest("mitrabooks", "/api/v1/business/depreciation/run", {
    method: "POST",
    headers: { "X-Idempotency-Key": `depreciation-${depFy}` },
    body: JSON.stringify({ financial_year: depFy }),
  });
  if (result.ok) {
    setLoginStatus("ok", "Depreciation posted", `FY ${depFy}: ${formatCurrency(Number(result.payload?.total_depreciation || 0))} — journal entry #${result.payload?.journal_entry_id}.`);
    await previewDepreciation();
    await loadFixedAssets();
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can post the depreciation run.");
  } else {
    setLoginStatus("danger", "Run failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { depreciation_run: { ok: result.ok, status: result.status } });
}

function renderFixedAssetForm() {
  const accountOpts = fixedAssetAccountOptions().map((a) =>
    `<option value="${escapeHtml(a.code)}">${escapeHtml(`${a.code} - ${a.name}`)}</option>`).join("")
    || `<option value="16001">16001 - Furniture and Fixtures</option>`;
  return `
    <div class="invoice-form-grid" data-fa-form>
      <label>Asset name <input type="text" name="fa_name" maxlength="160" placeholder="e.g. Delivery van"></label>
      <label>Asset account <select name="fa_account">${accountOpts}</select></label>
      <label>Purchase date <input type="date" name="fa_date" value="${escapeHtml(todayIsoDate())}"></label>
      <label>Cost <input type="number" name="fa_cost" min="0" step="0.01" placeholder="0.00"></label>
      <label>Salvage value <input type="number" name="fa_salvage" min="0" step="0.01" value="0"></label>
      <label>Method <select name="fa_method">
        <option value="slm">SLM (straight line)</option>
        <option value="wdv">WDV (written down value)</option>
      </select></label>
      <label>Useful life (years, SLM) <input type="number" name="fa_life" min="0" step="1" placeholder="e.g. 5"></label>
      <label>Rate % (WDV) <input type="number" name="fa_rate" min="0" max="100" step="0.01" placeholder="e.g. 15"></label>
      <label>Already depreciated (migrated assets) <input type="number" name="fa_opening_acc" min="0" step="0.01" value="0"></label>
      <label>Notes <input type="text" name="fa_notes" maxlength="200" placeholder="Optional"></label>
    </div>
    <div class="report-date-controls">
      <button class="primary" type="button" data-business-action="fa-create">Register asset</button>
      <button class="secondary" type="button" data-business-action="fa-toggle-form">Cancel</button>
    </div>
    <p class="muted">Registering only records the asset — book its purchase via a bill/voucher to the chosen 16xxx account as usual.</p>`;
}

function renderFixedAssetsPanel() {
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const r = lastFixedAssets;
  let registerBody;
  if (!r) {
    registerBody = `<p class="muted">Loading the asset register...</p>`;
  } else if (r.ok === false) {
    registerBody = reportUnavailablePanel("Fixed Assets", r);
  } else {
    const rows = (r.items || []).map((a) => `
      <tr>
        <td>${escapeHtml(a.asset_name || "")}${a.status !== "active" ? ` <span class="pill warn">${escapeHtml(a.status)}</span>` : ""}</td>
        <td>${escapeHtml(a.asset_account_code || "")}</td>
        <td>${escapeHtml(a.purchase_date || "")}</td>
        <td>${escapeHtml(String(a.method || "").toUpperCase())}${a.useful_life_years ? ` ${escapeHtml(a.useful_life_years)}y` : ""}${a.depreciation_rate ? ` ${escapeHtml(a.depreciation_rate)}%` : ""}</td>
        <td class="amount">${num(a.cost)}</td>
        <td class="amount">${num(a.accumulated_depreciation)}</td>
        <td class="amount">${num(a.book_value)}</td>
      </tr>`).join("");
    registerBody = `
      <div class="table-preview compact-table">
        <table>
          <thead><tr><th>Asset</th><th>Account</th><th>Purchased</th><th>Method</th><th class="amount">Cost</th><th class="amount">Acc. depreciation</th><th class="amount">Book value</th></tr></thead>
          <tbody>${rows || `<tr><td colspan="7" class="muted">No assets registered yet.</td></tr>`}</tbody>
          ${rows ? `<tfoot><tr><th colspan="4">Total</th><td class="amount">${num(r.total_cost)}</td><td></td><td class="amount"><strong>${num(r.total_book_value)}</strong></td></tr></tfoot>` : ""}
        </table>
      </div>`;
  }

  const fyOpts = recentFinancialYears(4).map((fy) =>
    `<option value="${fy}" ${fy === depFy ? "selected" : ""}>FY ${fy}</option>`).join("");
  const d = lastDepPreview;
  let depBody = "";
  if (d && d.ok === false) {
    depBody = reportUnavailablePanel("Depreciation", d);
  } else if (d) {
    const rows = (d.rows || []).map((row) => `
      <tr>
        <td>${escapeHtml(row.asset_name || "")}</td>
        <td>${escapeHtml(String(row.method || "").toUpperCase())}</td>
        <td class="amount">${num(row.opening_book_value)}</td>
        <td class="amount">${num(row.depreciation)}</td>
        <td class="amount">${num(row.closing_book_value)}</td>
      </tr>`).join("");
    depBody = `
      <div class="preview-heading compact">
        <div><p>FY ${escapeHtml(d.financial_year)} charge: <strong>${num(d.total_depreciation)}</strong> across ${escapeHtml(String(d.asset_count))} asset(s).</p></div>
        <span class="pill ${d.already_run ? "warn" : (d.can_post ? "ok" : "")}">${d.already_run ? "already posted" : (d.can_post ? "ready to post" : "nothing to post")}</span>
      </div>
      ${d.already_run ? `<p class="muted">⚠ FY ${escapeHtml(d.financial_year)} depreciation was posted (journal entry #${escapeHtml(String(d.existing_run?.journal_entry_id || ""))}).</p>` : ""}
      <div class="table-preview compact-table">
        <table>
          <thead><tr><th>Asset</th><th>Method</th><th class="amount">Opening book value</th><th class="amount">Depreciation</th><th class="amount">Closing book value</th></tr></thead>
          <tbody>${rows || `<tr><td colspan="5" class="muted">No active assets to depreciate.</td></tr>`}</tbody>
        </table>
      </div>
      ${d.can_post && isBusinessAdmin() ? `
      <div class="report-date-controls">
        <button class="primary" type="button" data-business-action="dep-post">Post depreciation</button>
      </div>` : (d.can_post ? `<p class="muted">Only a tenant admin can post the depreciation run.</p>` : "")}
      ${(d.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}`;
  }

  return `
    <div class="preview-heading compact">
      <div><h4>Fixed-asset register</h4><p>${r && r.ok !== false ? `${escapeHtml(String(r.count || 0))} asset(s) on the books.` : ""}</p></div>
      <button class="secondary" type="button" data-business-action="fa-toggle-form">${faFormOpen ? "Close form" : "+ Register asset"}</button>
    </div>
    ${faFormOpen ? renderFixedAssetForm() : ""}
    ${registerBody}
    <hr style="margin:18px 0;border:none;border-top:1px solid var(--line,#ddd);">
    <div class="table-preview compact-table"><h4>Depreciation run</h4></div>
    <div class="report-date-controls">
      <label>Financial year <select data-dep-fy>${fyOpts}</select></label>
      <button class="secondary" type="button" data-business-action="dep-preview">Preview depreciation</button>
    </div>
    ${depBody}
  `;
}

// ---- Accounting dimensions (cost centres / projects) ----------------------- //

// ══════════════════════════════════════════════════════════════════════
// SECTION: ACCOUNTING DIMENSIONS (cost centre / project)
// API   : GET/POST /api/v1/business/dimensions  GET .../report
// NOTE  : loadDimensions, createDimensionFromForm, deactivateDimension, renderDimensionsPanel
// ══════════════════════════════════════════════════════════════════════

async function loadDimensions() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/dimensions", { method: "GET" });
  lastDimensions = result.ok ? result.payload : null;
  renderJson(apiOutput, { dimensions: { ok: result.ok, count: result.payload?.count || 0 } });
  return lastDimensions;
}

function dimensionOptions(kind, selected) {
  const rows = (kind === "cost_centre" ? lastDimensions?.cost_centres : lastDimensions?.projects) || [];
  if (!rows.length) return null;  // no masters -> hide the select entirely
  const none = `<option value="">No ${kind === "cost_centre" ? "cost centre" : "project"}</option>`;
  return none + rows.map((d) =>
    `<option value="${escapeHtml(d.dimension_id)}" ${d.dimension_id === selected ? "selected" : ""}>${escapeHtml(`${d.code} - ${d.name}`)}</option>`).join("");
}

async function createDimensionFromForm() {
  const form = document.querySelector("[data-dim-form]");
  if (!form) return;
  const body = {
    dimension_type: form.querySelector("select[name='dim_type']")?.value || "cost_centre",
    code: form.querySelector("input[name='dim_code']")?.value || "",
    name: form.querySelector("input[name='dim_name']")?.value || "",
  };
  if (!body.name.trim()) {
    setLoginStatus("warn", "Name required", "Give the cost centre / project a name.");
    return;
  }
  const result = await apiRequest("mitrabooks", "/api/v1/business/dimensions", {
    method: "POST", body: JSON.stringify(body),
  });
  if (result.ok) {
    setLoginStatus("ok", "Dimension created", `${result.payload?.code} — ${result.payload?.name}`);
    await loadDimensions();
    await loadDimensionReport();
  } else {
    setLoginStatus("danger", "Create failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { dimension_create: { ok: result.ok, status: result.status } });
}

async function deactivateDimension(dimensionId) {
  const result = await apiRequest("mitrabooks", `/api/v1/business/dimensions/${encodeURIComponent(dimensionId)}/deactivate`, { method: "PATCH" });
  if (result.ok) {
    setLoginStatus("ok", "Dimension deactivated", "Existing documents keep the tag; new ones stop offering it.");
    await loadDimensions();
    await loadDimensionReport();
  } else {
    setLoginStatus("danger", "Deactivate failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { dimension_deactivate: { ok: result.ok, status: result.status } });
}

async function loadDimensionReport() {
  const typeSel = document.querySelector("[data-dim-report-type]");
  const fromInput = document.querySelector("[data-dim-from]");
  const toInput = document.querySelector("[data-dim-to]");
  if (typeSel) dimensionReportType = typeSel.value || dimensionReportType;
  const params = new URLSearchParams({ dimension_type: dimensionReportType });
  if (fromInput?.value) params.set("from_date", fromInput.value);
  if (toInput?.value) params.set("to_date", toInput.value);
  const result = await apiRequest("mitrabooks", `/api/v1/business/dimensions/report?${params.toString()}`, { method: "GET" });
  lastDimensionReport = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { dimension_report: { ok: result.ok, type: dimensionReportType } });
}

function renderDimensionsPanel() {
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const dims = lastDimensions;
  const masterRows = (dims?.items || []).map((d) => `
    <tr>
      <td>${escapeHtml(d.dimension_type === "cost_centre" ? "Cost centre" : "Project")}</td>
      <td>${escapeHtml(d.code || "")}</td>
      <td>${escapeHtml(d.name || "")}</td>
      <td><button class="secondary" type="button" data-business-action="dim-deactivate" data-dimension-id="${escapeHtml(d.dimension_id)}">Deactivate</button></td>
    </tr>`).join("");

  const manage = `
    <div class="report-date-controls" data-dim-form>
      <label>Type <select name="dim_type">
        <option value="cost_centre">Cost centre</option>
        <option value="project">Project</option>
      </select></label>
      <label>Code <input type="text" name="dim_code" maxlength="20" placeholder="e.g. BLR" style="width:90px;text-transform:uppercase;"></label>
      <label>Name <input type="text" name="dim_name" maxlength="120" placeholder="e.g. Bengaluru branch"></label>
      <button class="primary" type="button" data-business-action="dim-create">Add</button>
    </div>
    <div class="table-preview compact-table">
      <table>
        <thead><tr><th>Type</th><th>Code</th><th>Name</th><th></th></tr></thead>
        <tbody>${masterRows || `<tr><td colspan="4" class="muted">No dimensions yet — add a cost centre or project above. They then appear as tags on the invoice and bill forms.</td></tr>`}</tbody>
      </table>
    </div>`;

  const r = lastDimensionReport;
  let reportBody = "";
  if (r && r.ok === false) {
    reportBody = reportUnavailablePanel("Dimension report", r);
  } else if (r) {
    const rows = (r.rows || []).map((row) => `
      <tr>
        <td>${escapeHtml(`${row.code} - ${row.name}`)}</td>
        <td class="amount">${num(row.income)}</td>
        <td class="amount">${num(row.expense)}</td>
        <td class="amount"><strong>${num(row.net)}</strong></td>
      </tr>`).join("");
    const u = r.untagged || {};
    const t = r.totals || {};
    reportBody = `
      <div class="preview-heading compact">
        <div><p>${escapeHtml(r.from_date)} → ${escapeHtml(r.to_date)} · ${escapeHtml(String(r.document_counts?.invoices || 0))} invoice(s), ${escapeHtml(String(r.document_counts?.bills || 0))} bill(s).</p></div>
        <span class="pill">Net ${num(t.net)}</span>
      </div>
      <div class="table-preview compact-table">
        <table>
          <thead><tr><th>${dimensionReportType === "cost_centre" ? "Cost centre" : "Project"}</th><th class="amount">Income</th><th class="amount">Expense</th><th class="amount">Net</th></tr></thead>
          <tbody>
            ${rows || `<tr><td colspan="4" class="muted">No tagged documents in this period.</td></tr>`}
            <tr><td><em>Untagged</em></td><td class="amount">${num(u.income)}</td><td class="amount">${num(u.expense)}</td><td class="amount">${num(u.net)}</td></tr>
          </tbody>
          <tfoot><tr><th>Total</th><td class="amount">${num(t.income)}</td><td class="amount">${num(t.expense)}</td><td class="amount"><strong>${num(t.net)}</strong></td></tr></tfoot>
        </table>
      </div>
      ${(r.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}`;
  }

  return `
    <div class="table-preview compact-table"><h4>Cost centres &amp; projects</h4></div>
    ${manage}
    <hr style="margin:18px 0;border:none;border-top:1px solid var(--line,#ddd);">
    <div class="table-preview compact-table"><h4>Income / expense by dimension</h4></div>
    <div class="report-date-controls">
      <label>View by <select data-dim-report-type>
        <option value="cost_centre" ${dimensionReportType === "cost_centre" ? "selected" : ""}>Cost centre</option>
        <option value="project" ${dimensionReportType === "project" ? "selected" : ""}>Project</option>
      </select></label>
      <label>From <input type="date" data-dim-from></label>
      <label>To <input type="date" data-dim-to></label>
      <button class="secondary" type="button" data-business-action="dim-report-load">Load</button>
    </div>
    ${reportBody || `<p class="muted">Loading dimension report...</p>`}
  `;
}

// ---- Inventory (opt-in): items, stock register, closing stock ------------- //

// ══════════════════════════════════════════════════════════════════════
// SECTION: INVENTORY (opt-in, periodic method)
// API   : GET/POST /api/v1/business/inventory/items  GET .../stock-register
// NOTE  : loadInventoryItems, createInventoryItemFromForm, postClosingStock, renderInventoryPanel
// ══════════════════════════════════════════════════════════════════════

async function loadInventoryItems() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/inventory/items", { method: "GET" });
  lastInventoryItems = result.ok ? result.payload : { ok: false, inventory_enabled: false, items: [], detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { inventory_items: { ok: result.ok, count: result.payload?.count || 0, enabled: !!result.payload?.inventory_enabled } });
  return lastInventoryItems;
}

function inventoryItemOptions(selected) {
  if (!lastInventoryItems?.inventory_enabled) return null;
  const rows = lastInventoryItems?.items || [];
  if (!rows.length) return null;
  return `<option value="">No item</option>` + rows.map((it) =>
    `<option value="${escapeHtml(it.item_id)}" ${it.item_id === selected ? "selected" : ""}>${escapeHtml(`${it.code} - ${it.name}`)}</option>`).join("");
}

async function createInventoryItemFromForm() {
  const form = document.querySelector("[data-item-form]");
  if (!form) return;
  const val = (sel) => form.querySelector(sel)?.value ?? "";
  const body = {
    code: val("input[name='item_code']"),
    name: val("input[name='item_name']"),
    uqc: val("input[name='item_uqc']") || "NOS",
    hsn_sac: val("input[name='item_hsn']") || null,
    gst_rate: val("input[name='item_gst']") || "0",
    opening_qty: val("input[name='item_open_qty']") || "0",
    opening_value: val("input[name='item_open_val']") || "0",
  };
  if (!body.name.trim()) {
    setLoginStatus("warn", "Name required", "Give the item a name.");
    return;
  }
  const result = await apiRequest("mitrabooks", "/api/v1/business/inventory/items", {
    method: "POST", body: JSON.stringify(body),
  });
  if (result.ok) {
    setLoginStatus("ok", "Item created", `${result.payload?.code} — ${result.payload?.name}`);
    await loadInventoryItems();
    await loadStockRegister();
  } else {
    setLoginStatus("danger", "Create failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { item_create: { ok: result.ok, status: result.status } });
}

async function deactivateInventoryItem(itemId) {
  const result = await apiRequest("mitrabooks", `/api/v1/business/inventory/items/${encodeURIComponent(itemId)}/deactivate`, { method: "PATCH" });
  if (result.ok) {
    setLoginStatus("ok", "Item deactivated", "Existing documents keep the tag.");
    await loadInventoryItems();
    await loadStockRegister();
  } else {
    setLoginStatus("danger", "Deactivate failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { item_deactivate: { ok: result.ok, status: result.status } });
}

async function loadStockRegister() {
  const asOf = document.querySelector("[data-stock-asof]")?.value || "";
  const params = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  const result = await apiRequest("mitrabooks", `/api/v1/business/inventory/stock-register${params}`, { method: "GET" });
  lastStockRegister = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { stock_register: { ok: result.ok } });
}

async function loadClosingStockEntries() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/inventory/closing-stock/entries", { method: "GET" });
  lastClosingStockEntries = result.ok ? (result.payload?.items || []) : [];
  rerenderBusinessReportsIfActive();
}

async function postClosingStock() {
  const r = lastStockRegister;
  if (!r || r.ok === false) { setLoginStatus("warn", "Load the register first", "Load the stock register before posting."); return; }
  const result = await apiRequest("mitrabooks", "/api/v1/business/inventory/closing-stock", {
    method: "POST",
    headers: { "X-Idempotency-Key": `closing-stock-${r.as_of}` },
    body: JSON.stringify({ as_of: r.as_of }),
  });
  if (result.ok) {
    setLoginStatus("ok", "Closing stock posted", `${formatCurrency(Number(result.payload?.closing_stock_value || 0))} — journal entry #${result.payload?.journal_entry_id}.`);
    await loadClosingStockEntries();
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can post the closing stock.");
  } else {
    setLoginStatus("danger", "Posting failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { closing_stock_post: { ok: result.ok, status: result.status } });
}

function renderInventoryPanel() {
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const inv = lastInventoryItems;
  if (!inv) return `<p class="muted">Loading inventory...</p>`;
  if (!inv.inventory_enabled) {
    return `
      <div class="table-preview compact-table">
        <h4>Inventory accounting is OFF for this business</h4>
        <p class="muted">This business is set up without stock keeping — purchases stay pure expense and no inventory entries are ever posted. That is the right setting for service businesses.</p>
        <p class="muted">To enable it: <strong>Sales → Invoice Settings → Inventory accounting</strong> (tenant admin). The item master, stock register and closing-stock journal will then appear here.</p>
      </div>`;
  }

  const itemRows = (inv.items || []).map((it) => `
    <tr>
      <td>${escapeHtml(it.code || "")}</td>
      <td>${escapeHtml(it.name || "")}</td>
      <td>${escapeHtml(it.uqc || "")}</td>
      <td>${escapeHtml(it.hsn_sac || "")}</td>
      <td class="amount">${escapeHtml(it.opening_qty || "0")}</td>
      <td class="amount">${num(it.opening_value)}</td>
      <td><button class="secondary" type="button" data-business-action="item-deactivate" data-item-id="${escapeHtml(it.item_id)}">Deactivate</button></td>
    </tr>`).join("");

  const manage = `
    <div class="invoice-form-grid" data-item-form>
      <label>Code <input type="text" name="item_code" maxlength="20" placeholder="e.g. WIDGET-A" style="text-transform:uppercase;"></label>
      <label>Name <input type="text" name="item_name" maxlength="160" placeholder="Item name"></label>
      <label>UQC <input type="text" name="item_uqc" maxlength="10" value="NOS" style="text-transform:uppercase;"></label>
      <label>HSN/SAC <input type="text" name="item_hsn" maxlength="8" placeholder="4-8 digits"></label>
      <label>GST % <input type="number" name="item_gst" min="0" max="100" step="any" placeholder="18"></label>
      <label>Opening qty <input type="number" name="item_open_qty" min="0" step="any" value="0"></label>
      <label>Opening value <input type="number" name="item_open_val" min="0" step="0.01" value="0"></label>
    </div>
    <div class="report-date-controls">
      <button class="primary" type="button" data-business-action="item-create">Add item</button>
    </div>
    <div class="table-preview compact-table">
      <table>
        <thead><tr><th>Code</th><th>Name</th><th>UQC</th><th>HSN</th><th class="amount">Opening qty</th><th class="amount">Opening value</th><th></th></tr></thead>
        <tbody>${itemRows || `<tr><td colspan="7" class="muted">No items yet — add your stock items above, then tag them on invoice and bill lines.</td></tr>`}</tbody>
      </table>
    </div>`;

  const r = lastStockRegister;
  let registerBody = "";
  if (r && r.ok === false) {
    registerBody = reportUnavailablePanel("Stock register", r);
  } else if (r) {
    const rows = (r.rows || []).map((row) => `
      <tr ${row.negative_stock ? 'style="background:#fff5f5;"' : ""}>
        <td>${escapeHtml(`${row.code} - ${row.name}`)}${row.negative_stock ? ` <span class="pill warn">negative</span>` : ""}</td>
        <td>${escapeHtml(row.uqc || "")}</td>
        <td class="amount">${escapeHtml(row.opening_qty)}</td>
        <td class="amount">${escapeHtml(row.purchased_qty)}</td>
        <td class="amount">${escapeHtml(row.sold_qty)}</td>
        <td class="amount">${escapeHtml(row.closing_qty)}</td>
        <td class="amount">${num(row.avg_cost)}</td>
        <td class="amount">${num(row.closing_value)}</td>
      </tr>`).join("");
    const lastEntry = (lastClosingStockEntries || [])[0];
    registerBody = `
      <div class="preview-heading compact">
        <div><p>Stock as of ${escapeHtml(r.as_of)} · ${escapeHtml(String(r.item_count))} item(s)${Number(r.untracked_purchase_value || 0) > 0 ? ` · untracked purchases ${num(r.untracked_purchase_value)}` : ""}.</p></div>
        <span class="pill ${r.negative_stock_items ? "warn" : "ok"}">${r.negative_stock_items ? `${escapeHtml(String(r.negative_stock_items))} negative` : `closing ${num(r.total_closing_value)}`}</span>
      </div>
      <div class="table-preview compact-table">
        <table>
          <thead><tr><th>Item</th><th>UQC</th><th class="amount">Opening</th><th class="amount">In</th><th class="amount">Out</th><th class="amount">Closing</th><th class="amount">Avg cost</th><th class="amount">Value</th></tr></thead>
          <tbody>${rows || `<tr><td colspan="8" class="muted">No items to report.</td></tr>`}</tbody>
          ${rows ? `<tfoot><tr><th colspan="7">Total closing stock</th><td class="amount"><strong>${num(r.total_closing_value)}</strong></td></tr></tfoot>` : ""}
        </table>
      </div>
      ${lastEntry ? `<p class="muted">Last closing-stock journal: entry #${escapeHtml(String(lastEntry.journal_entry_id))} dated ${escapeHtml(lastEntry.entry_date)}. Reverse it before posting a new position.</p>` : ""}
      ${Number(r.total_closing_value || 0) > 0 && !r.negative_stock_items && !lastEntry && isBusinessAdmin() ? `
      <div class="report-date-controls">
        <button class="primary" type="button" data-business-action="closing-stock-post">Post closing stock (Dr 13001 / Cr 51002)</button>
      </div>` : ""}
      ${(r.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}`;
  }

  return `
    <div class="table-preview compact-table"><h4>Item master</h4></div>
    ${manage}
    <hr style="margin:18px 0;border:none;border-top:1px solid var(--line,#ddd);">
    <div class="table-preview compact-table"><h4>Stock register &amp; closing stock</h4></div>
    <div class="report-date-controls">
      <label>As of <input type="date" data-stock-asof value="${escapeHtml(r?.as_of || "")}"></label>
      <button class="secondary" type="button" data-business-action="stock-register-load">Load register</button>
    </div>
    ${registerBody || `<p class="muted">Loading stock register...</p>`}
  `;
}

// ---- Customer/vendor statements + dunning (Phase D) ----------------------- //

// ══════════════════════════════════════════════════════════════════════
// SECTION: CUSTOMER STATEMENTS + DUNNING
// API   : GET /api/v1/business/statements/{party_id}  POST .../dunning
// NOTE  : loadPartyStatement, recordDunningSent, renderStatementsPanel
// ══════════════════════════════════════════════════════════════════════

async function loadPartyStatement() {
  const partySel = document.querySelector("[data-stmt-party]");
  const kindSel = document.querySelector("[data-stmt-kind]");
  const fromInput = document.querySelector("[data-stmt-from]");
  const toInput = document.querySelector("[data-stmt-to]");
  if (partySel) statementPartyId = partySel.value || statementPartyId;
  if (kindSel) statementKind = kindSel.value || statementKind;
  if (fromInput) statementFromDate = fromInput.value || "";
  if (toInput) statementToDate = toInput.value || "";
  if (!statementPartyId) { rerenderBusinessReportsIfActive(); return; }
  const params = new URLSearchParams({ kind: statementKind });
  if (statementFromDate) params.set("from_date", statementFromDate);
  if (statementToDate) params.set("to_date", statementToDate);
  const result = await apiRequest("mitrabooks", `/api/v1/business/statements/${encodeURIComponent(statementPartyId)}?${params.toString()}`, { method: "GET" });
  lastPartyStatement = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { party_statement: { ok: result.ok, party_id: statementPartyId, kind: statementKind } });
}

async function recordDunningSent() {
  const s = lastPartyStatement;
  const suggestion = s?.dunning?.suggestion;
  if (!suggestion || !suggestion.level) {
    setLoginStatus("warn", "Nothing to record", "No overdue invoices — no reminder is suggested.");
    return;
  }
  const note = document.querySelector("[data-dunning-note]")?.value || "";
  const result = await apiRequest("mitrabooks", `/api/v1/business/statements/${encodeURIComponent(statementPartyId)}/dunning`, {
    method: "POST",
    body: JSON.stringify({ level: suggestion.level, note, overdue_total: suggestion.overdue_total }),
  });
  if (result.ok) {
    setLoginStatus("ok", "Reminder recorded", `${suggestion.label} logged for this party.`);
    await loadPartyStatement();
  } else {
    setLoginStatus("danger", "Could not record", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { dunning_record: { ok: result.ok, status: result.status } });
}

function copyDunningLetter() {
  const letter = lastPartyStatement?.dunning?.letter || "";
  if (!letter) { setLoginStatus("warn", "No letter", "Load a party with overdue invoices first."); return; }
  navigator.clipboard?.writeText(letter).then(
    () => setLoginStatus("ok", "Letter copied", "Paste it into your email/WhatsApp and send."),
    () => setLoginStatus("warn", "Copy failed", "Select the letter text and copy manually."),
  );
}

function renderStatementsPanel() {
  const parties = Array.isArray(lastBusinessParties) ? lastBusinessParties : [];
  const options = `<option value="">Select party</option>` + parties.map((p) =>
    `<option value="${escapeHtml(p.party_id)}" ${p.party_id === statementPartyId ? "selected" : ""}>${escapeHtml(p.party_name)} (${escapeHtml(p.party_type || "")})</option>`).join("");
  const controls = `
    <div class="report-date-controls">
      <label>Party <select data-stmt-party>${options}</select></label>
      <label>Side <select data-stmt-kind>
        <option value="receivable" ${statementKind === "receivable" ? "selected" : ""}>Receivable (customer)</option>
        <option value="payable" ${statementKind === "payable" ? "selected" : ""}>Payable (vendor)</option>
      </select></label>
      <label>From <input type="date" data-stmt-from value="${escapeHtml(statementFromDate)}"></label>
      <label>To <input type="date" data-stmt-to value="${escapeHtml(statementToDate)}"></label>
      <button class="secondary" type="button" data-business-action="stmt-load">Load</button>
    </div>
    <p class="muted">Dates default to the current financial year. The statement is built from the posted party sub-ledger.</p>`;
  if (!statementPartyId) return `${controls}<p class="muted">Select a customer or vendor to generate their statement of account.</p>`;
  const r = lastPartyStatement;
  if (!r) return `${controls}<p class="muted">Loading statement...</p>`;
  if (r.ok === false) return `${controls}${reportUnavailablePanel("Statement of Account", r)}`;
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));

  const txnRows = (r.transactions || []).map((t) => `
    <tr>
      <td>${escapeHtml(t.entry_date || "")}</td>
      <td>${escapeHtml(t.document_type || "")}</td>
      <td>${escapeHtml(t.reference || "")}</td>
      <td>${escapeHtml(t.description || "")}</td>
      <td class="amount">${Number(t.debit || 0) ? num(t.debit) : ""}</td>
      <td class="amount">${Number(t.credit || 0) ? num(t.credit) : ""}</td>
      <td class="amount">${num(t.balance)}</td>
    </tr>`).join("");

  const openRows = (r.open_items || []).map((i) => `
    <tr>
      <td>${escapeHtml(i.open_item_number || "")}</td>
      <td>${escapeHtml(i.item_date || "")}</td>
      <td>${escapeHtml(i.due_date || "—")}</td>
      <td class="amount">${num(i.total)}</td>
      <td class="amount">${num(i.outstanding)}</td>
      <td class="amount">${escapeHtml(String(i.days_overdue ?? 0))}</td>
    </tr>`).join("");

  const d = r.dunning || {};
  const sug = d.suggestion || {};
  const dunningMessage = sug.level
    ? `Suggested: <strong>${escapeHtml(sug.label || "")}</strong> — oldest invoice ${escapeHtml(String(sug.max_days_overdue || 0))} days overdue, ${escapeHtml(String(sug.overdue_count || 0))} invoice(s), total ${num(sug.overdue_total)}.`
    : (sug.label === "Allocation required" ? "Allocation required — the ledger is settled or differs from open-item allocation, so no reminder is generated." : "Nothing overdue — no reminder needed.");
  const logRows = (d.log || []).map((l) => `
    <tr>
      <td>${escapeHtml(String(l.created_at || "").slice(0, 10))}</td>
      <td>${escapeHtml(l.label || `Level ${l.level}`)}</td>
      <td class="amount">${l.overdue_total ? num(l.overdue_total) : ""}</td>
      <td>${escapeHtml(l.note || "")}</td>
      <td>${escapeHtml(l.created_by || "")}</td>
    </tr>`).join("");

  const dunningPanel = r.kind !== "receivable" ? "" : `
    <div class="table-preview compact-table">
      <h4>Payment reminders (dunning)</h4>
      <div class="preview-heading compact">
        <div><p>${dunningMessage}</p></div>
        <span class="pill ${sug.level >= 3 ? "warn" : sug.level ? "" : "ok"}">${escapeHtml(sug.level ? `Level ${sug.level}` : "clear")}</span>
      </div>
      ${d.letter ? `
      <pre style="white-space:pre-wrap;border:1px solid var(--line,#ddd);border-radius:6px;padding:10px;font-size:12px;max-height:280px;overflow:auto;">${escapeHtml(d.letter)}</pre>
      <div class="report-date-controls">
        <button class="secondary" type="button" data-business-action="dunning-copy">Copy letter</button>
        <label>Note <input type="text" data-dunning-note placeholder="e.g. emailed to accounts@..." maxlength="200"></label>
        <button class="primary" type="button" data-business-action="dunning-record">Record reminder sent</button>
      </div>` : ""}
      <h4 style="margin-top:12px;">Reminder history</h4>
      <table>
        <thead><tr><th>Date</th><th>Level</th><th class="amount">Overdue then</th><th>Note</th><th>By</th></tr></thead>
        <tbody>${logRows || `<tr><td colspan="5" class="muted">No reminders recorded yet.</td></tr>`}</tbody>
      </table>
    </div>`;

  return `
    ${controls}
    <div class="preview-heading compact">
      <div><p>Statement for <strong>${escapeHtml(r.party?.party_name || "")}</strong> (${escapeHtml(r.kind)}) · ${escapeHtml(r.from_date)} → ${escapeHtml(r.to_date)} · from ${escapeHtml(r.business_name || "")}.</p></div>
      <span class="pill">Closing ${num(r.closing_balance)}</span>
    </div>

    <div class="table-preview compact-table">
      <h4>Statement of account</h4>
      <table>
        <thead><tr><th>Date</th><th>Document</th><th>Reference</th><th>Particulars</th><th class="amount">Debit</th><th class="amount">Credit</th><th class="amount">Balance</th></tr></thead>
        <tbody>
          <tr><td>${escapeHtml(r.from_date)}</td><td></td><td></td><td><em>Opening balance</em></td><td class="amount"></td><td class="amount"></td><td class="amount">${num(r.opening_balance)}</td></tr>
          ${txnRows || `<tr><td colspan="7" class="muted">No transactions in this period.</td></tr>`}
        </tbody>
        <tfoot><tr><th colspan="4">Closing balance</th><td class="amount">${num(r.total_debit)}</td><td class="amount">${num(r.total_credit)}</td><td class="amount"><strong>${num(r.closing_balance)}</strong></td></tr></tfoot>
      </table>
    </div>

    <div class="table-preview compact-table">
      <h4>Open items (${escapeHtml(String((r.open_items || []).length))})</h4>
      <table>
        <thead><tr><th>Document</th><th>Date</th><th>Due</th><th class="amount">Total</th><th class="amount">Outstanding</th><th class="amount">Days overdue</th></tr></thead>
        <tbody>${openRows || `<tr><td colspan="6" class="muted">Nothing outstanding — the account is settled.</td></tr>`}</tbody>
      </table>
    </div>
    ${dunningPanel}
    ${(r.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}
  `;
}

// ---- Bank reconciliation (statement CSV vs bank-account ledger) ---------- //

// ══════════════════════════════════════════════════════════════════════
// SECTION: BANK RECONCILIATION
// API   : POST /api/v1/business/bank-recon/statement  GET /api/v1/business/bank-recon
// NOTE  : loadBankReconciliation, uploadBankStatementFile, confirmBankReconMatch
// ══════════════════════════════════════════════════════════════════════

function bankAccountOptions() {
  // Cash/bank accounts live in the 11xxx subclass of the business COA.
  return businessAccountsForSelection().filter((acc) => String(acc.code || "").startsWith("11"));
}

async function loadBankReconciliation(accountId) {
  bankReconAccountId = String(accountId || bankReconAccountId || "");
  if (!bankReconAccountId) { rerenderBusinessReportsIfActive(); return; }
  const result = await apiRequest("mitrabooks", `/api/v1/business/bank-recon?account_id=${encodeURIComponent(bankReconAccountId)}`, { method: "GET" });
  lastBankRecon = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { bank_recon: { ok: result.ok, account_id: bankReconAccountId } });
}

async function uploadBankStatementFile() {
  const accountSel = document.querySelector("[data-bankrecon-account]");
  const fileInput = document.querySelector("[data-bankrecon-file]");
  const accountId = accountSel?.value || bankReconAccountId;
  if (!accountId) {
    setLoginStatus("warn", "Pick a bank account", "Choose which ledger bank account this statement belongs to.");
    return;
  }
  const file = fileInput?.files?.[0];
  if (!file) {
    setLoginStatus("warn", "Choose a file", "Upload the bank statement CSV exported from net banking.");
    return;
  }
  const csvText = await file.text();
  bankReconAccountId = accountId;
  const result = await apiRequest(
    "mitrabooks",
    `/api/v1/business/bank-recon/statement?account_id=${encodeURIComponent(accountId)}`,
    { method: "POST", body: JSON.stringify({ csv: csvText }) },
  );
  if (result.ok) {
    const r = result.payload || {};
    setLoginStatus("ok", "Statement imported", `${r.inserted || 0} line(s) added, ${r.skipped_duplicates || 0} duplicate(s) skipped.`);
    await loadBankReconciliation(accountId);
  } else {
    setLoginStatus("danger", "Import failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { bank_statement_upload: { ok: result.ok, status: result.status } });
}

async function confirmBankReconMatch(statementLineId, lineId) {
  const result = await apiRequest("mitrabooks", "/api/v1/business/bank-recon/match", {
    method: "POST",
    body: JSON.stringify({
      account_id: Number(bankReconAccountId),
      statement_line_id: statementLineId,
      line_id: Number(lineId),
    }),
  });
  if (result.ok) {
    setLoginStatus("ok", "Matched", "Statement line matched to the book entry.");
    await loadBankReconciliation(bankReconAccountId);
  } else {
    setLoginStatus("danger", "Match failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { bank_recon_match: { ok: result.ok, status: result.status } });
}

async function reverseBankReconMatch(matchId) {
  const result = await apiRequest("mitrabooks", `/api/v1/business/bank-recon/match/${encodeURIComponent(matchId)}/reverse`, { method: "POST" });
  if (result.ok) {
    setLoginStatus("ok", "Unmatched", "The match was reversed; both lines are open again.");
    await loadBankReconciliation(bankReconAccountId);
  } else {
    setLoginStatus("danger", "Unmatch failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { bank_recon_unmatch: { ok: result.ok, status: result.status } });
}

function renderBankReconPanel() {
  const accounts = bankAccountOptions();
  const options = `<option value="">Select bank account</option>` + accounts.map((a) =>
    `<option value="${escapeHtml(String(a.id))}" ${String(a.id) === String(bankReconAccountId) ? "selected" : ""}>${escapeHtml(`${a.code} - ${a.name}`)}</option>`).join("");
  const controls = `
    <div class="report-date-controls">
      <label>Bank account <select data-bankrecon-account>${options}</select></label>
      <button class="secondary" type="button" data-business-action="bankrecon-load">Load</button>
      <label>Statement CSV <input type="file" accept=".csv,text/csv" data-bankrecon-file></label>
      <button class="secondary" type="button" data-business-action="bankrecon-upload">Import statement</button>
    </div>
    <p class="muted">Export the account statement as CSV from net banking and import it here. Lines are matched against the posted ledger; confirming a match never changes the books.</p>`;
  if (!bankReconAccountId) return `${controls}<p class="muted">Select a bank account to begin.</p>`;
  const r = lastBankRecon;
  if (!r) return `${controls}<p class="muted">Loading bank reconciliation...</p>`;
  if (r.ok === false) return `${controls}${reportUnavailablePanel("Bank Reconciliation", r)}`;
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const s = r.summary || {};
  const diff = s.difference;
  const clean = diff !== null && diff !== undefined && Number(diff) === 0;

  const cards = [
    ["Balance as per books", s.book_balance, `${s.book_lines_total || 0} ledger line(s)`],
    ["Balance as per bank", s.statement_balance, `${s.statement_lines_total || 0} statement line(s)`],
    ["Expected bank balance", s.expected_statement_balance, "books + reconciling items"],
    ["Difference", diff, clean ? "fully reconciled" : "investigate unmatched lines"],
  ].map(([title, val, sub]) => `
    <article>
      <h4>${escapeHtml(title)}</h4>
      <div class="invoice-totals"><div class="invoice-grand"><span>${escapeHtml(sub)}</span><strong>${val === null || val === undefined ? "—" : num(val)}</strong></div></div>
    </article>`).join("");

  const suggestionRows = (r.suggestions || []).map((g) => `
    <tr>
      <td>${escapeHtml(g.statement?.txn_date || "")}</td>
      <td>${escapeHtml(g.statement?.description || g.statement?.ref || "")}</td>
      <td>${escapeHtml(g.book?.entry_date || "")}</td>
      <td>${escapeHtml(g.book?.reference || g.book?.description || "")}</td>
      <td class="amount">${num(g.amount)}</td>
      <td><span class="pill ${g.confidence === "ref" ? "ok" : ""}">${escapeHtml(g.confidence === "ref" ? "reference" : `±${g.date_diff_days}d`)}</span></td>
      <td><button class="primary" type="button" data-business-action="bankrecon-match" data-stmt-id="${escapeHtml(g.statement_line_id || "")}" data-line-id="${escapeHtml(String(g.line_id || ""))}">Match</button></td>
    </tr>`).join("");

  const bankOnlyRows = (r.in_bank_not_in_books || []).map((l) => `
    <tr>
      <td>${escapeHtml(l.txn_date || "")}</td>
      <td>${escapeHtml(l.description || "")}</td>
      <td>${escapeHtml(l.ref || "")}</td>
      <td class="amount">${Number(l.deposit || 0) > 0 ? num(l.deposit) : ""}</td>
      <td class="amount">${Number(l.withdrawal || 0) > 0 ? num(l.withdrawal) : ""}</td>
    </tr>`).join("");

  const bookOnlyRows = (r.in_books_not_in_bank || []).map((l) => `
    <tr>
      <td>${escapeHtml(l.entry_date || "")}</td>
      <td>${escapeHtml(l.reference || "")}</td>
      <td>${escapeHtml(l.description || "")}</td>
      <td class="amount">${Number(l.debit || 0) > 0 ? num(l.debit) : ""}</td>
      <td class="amount">${Number(l.credit || 0) > 0 ? num(l.credit) : ""}</td>
    </tr>`).join("");

  const matchedRows = (r.matched || []).map((m) => `
    <tr>
      <td>${escapeHtml(m.statement_txn_date || "")}</td>
      <td>${escapeHtml(m.book_entry_date || "")}</td>
      <td>${escapeHtml(m.side || "")}</td>
      <td class="amount">${num(m.amount)}</td>
      <td><button class="secondary" type="button" data-business-action="bankrecon-unmatch" data-match-id="${escapeHtml(m.match_id || "")}">Unmatch</button></td>
    </tr>`).join("");

  return `
    ${controls}
    <div class="preview-heading compact">
      <div><p>${escapeHtml(`${r.account?.code || ""} - ${r.account?.name || ""}`)} as of ${escapeHtml(r.as_of || "")} · ${escapeHtml(String(s.matched_count || 0))} matched.</p></div>
      <span class="pill ${clean ? "ok" : "warn"}">${clean ? "reconciled" : (diff === null || diff === undefined ? "no statement balance" : "difference " + formatCurrency(Number(diff)))}</span>
    </div>
    <div class="dashboard-main-grid platform-grid">${cards}</div>

    <div class="table-preview compact-table">
      <h4>Suggested matches (confirm each — nothing is applied automatically)</h4>
      <table>
        <thead><tr><th>Bank date</th><th>Bank narration</th><th>Book date</th><th>Book entry</th><th class="amount">Amount</th><th>Basis</th><th></th></tr></thead>
        <tbody>${suggestionRows || `<tr><td colspan="7" class="muted">No suggestions — nothing left that agrees on amount within the date window.</td></tr>`}</tbody>
      </table>
    </div>

    <div class="table-preview compact-table">
      <h4>In bank, not in books (${escapeHtml(String((r.in_bank_not_in_books || []).length))}) — post these (charges, interest, direct credits)</h4>
      <table>
        <thead><tr><th>Date</th><th>Narration</th><th>Ref</th><th class="amount">Deposit</th><th class="amount">Withdrawal</th></tr></thead>
        <tbody>${bankOnlyRows || `<tr><td colspan="5" class="muted">Every bank line is matched or suggested.</td></tr>`}</tbody>
      </table>
    </div>

    <div class="table-preview compact-table">
      <h4>In books, not in bank (${escapeHtml(String((r.in_books_not_in_bank || []).length))}) — uncleared cheques / deposits in transit</h4>
      <table>
        <thead><tr><th>Date</th><th>Reference</th><th>Description</th><th class="amount">Debit</th><th class="amount">Credit</th></tr></thead>
        <tbody>${bookOnlyRows || `<tr><td colspan="5" class="muted">Every book line is reflected in the bank statement.</td></tr>`}</tbody>
      </table>
    </div>

    <div class="table-preview compact-table">
      <h4>Matched (${escapeHtml(String((r.matched || []).length))})</h4>
      <table>
        <thead><tr><th>Bank date</th><th>Book date</th><th>Side</th><th class="amount">Amount</th><th></th></tr></thead>
        <tbody>${matchedRows || `<tr><td colspan="5" class="muted">No confirmed matches yet.</td></tr>`}</tbody>
      </table>
    </div>
    ${(r.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}
  `;
}

// ---- TDS / TCS quarterly register (Form 26Q / 27EQ working paper) -------- //

// ══════════════════════════════════════════════════════════════════════
// SECTION: TDS / TCS MODULE
// API   : GET /api/v1/business/tds/register?quarter=
// NOTE  : loadTdsRegister, renderTdsRegisterPanel, renderTdsRegisterSide
// ══════════════════════════════════════════════════════════════════════

async function loadTdsRegister(quarter) {
  tdsQuarter = quarter || tdsQuarter;
  const result = await apiRequest("mitrabooks", `/api/v1/business/tds/register?quarter=${encodeURIComponent(tdsQuarter)}`, { method: "GET" });
  lastTdsRegister = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { tds_register: { ok: result.ok, quarter: tdsQuarter } });
}

function previewTdsRegisterFromInput() {
  const input = document.querySelector("[data-tds-quarter]");
  loadTdsRegister(input?.value || tdsQuarter);
}

function renderTdsRegisterSide(side, kindLabel, partyHeading) {
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  if (!side || !side.entry_count) {
    return `<div class="table-preview compact-table"><h4>${escapeHtml(kindLabel)}</h4><p class="muted">No ${escapeHtml(kindLabel)} entries this quarter.</p></div>`;
  }
  const sections = (side.sections || []).map((sec) => {
    const rows = (sec.entries || []).map((e) => `
      <tr>
        <td>${escapeHtml(e.doc_date || "")}</td>
        <td>${escapeHtml(e.doc_number || "")}</td>
        <td>${escapeHtml(e.party_name || "")}</td>
        <td>${e.pan_missing ? `<span class="pill warn">PAN missing</span>` : escapeHtml(e.pan || "")}</td>
        <td class="amount">${num(e.base_amount)}</td>
        <td class="amount">${escapeHtml(String(e.rate ?? ""))}%</td>
        <td class="amount">${num(e.tax_amount)}</td>
      </tr>`).join("");
    return `
      <div class="table-preview compact-table">
        <h4>${escapeHtml(`${sec.section} — ${sec.label}`)}</h4>
        <table>
          <thead><tr><th>Date</th><th>Document</th><th>${escapeHtml(partyHeading)}</th><th>PAN</th><th class="amount">Base</th><th class="amount">Rate</th><th class="amount">${escapeHtml(kindLabel)}</th></tr></thead>
          <tbody>${rows}</tbody>
          <tfoot><tr><th colspan="4">Section total</th><td class="amount">${num(sec.total_base)}</td><td></td><td class="amount"><strong>${num(sec.total_tax)}</strong></td></tr></tfoot>
        </table>
      </div>`;
  }).join("");
  return sections;
}

function renderTdsRegisterPanel() {
  const quarterOpts = recentFyQuarters(6).map((q) =>
    `<option value="${q}" ${q === tdsQuarter ? "selected" : ""}>${q}</option>`).join("");
  const controls = `
    <div class="report-date-controls">
      <label>Quarter <select data-tds-quarter>${quarterOpts}</select></label>
      <button class="secondary" type="button" data-business-action="tds-load">Load</button>
    </div>`;
  const r = lastTdsRegister;
  if (!r) return `${controls}<p class="muted">Loading TDS/TCS register...</p>`;
  if (r.ok === false) return `${controls}${reportUnavailablePanel("TDS/TCS register", r)}`;
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const panMissing = Number(r.tds?.pan_missing_count || 0) + Number(r.tcs?.pan_missing_count || 0);

  const cards = [
    ["TDS deducted (26Q)", r.tds?.total_tax, `${r.tds?.entry_count || 0} document(s) · base ${formatCurrency(Number(r.tds?.total_base || 0))}`],
    ["TCS collected (27EQ)", r.tcs?.total_tax, `${r.tcs?.entry_count || 0} document(s) · base ${formatCurrency(Number(r.tcs?.total_base || 0))}`],
  ].map(([title, val, sub]) => `
    <article>
      <h4>${escapeHtml(title)}</h4>
      <div class="invoice-totals"><div class="invoice-grand"><span>${escapeHtml(sub)}</span><strong>${num(val)}</strong></div></div>
    </article>`).join("");

  return `
    ${controls}
    <div class="preview-heading compact">
      <div><p>TDS/TCS register for ${escapeHtml(r.quarter || tdsQuarter)} (${escapeHtml(r.period_start || "")} → ${escapeHtml(r.period_end || "")}). Section-wise working paper for Form 26Q / 27EQ.</p></div>
      <span class="pill ${panMissing > 0 ? "warn" : "ok"}">${panMissing > 0 ? `${panMissing} PAN missing` : "PANs complete"}</span>
    </div>
    <div class="dashboard-main-grid platform-grid">${cards}</div>
    <h4 style="margin:14px 0 6px;">TDS on purchases (Form 26Q)</h4>
    ${renderTdsRegisterSide(r.tds, "TDS", "Deductee (vendor)")}
    <h4 style="margin:14px 0 6px;">TCS on sales (Form 27EQ)</h4>
    ${renderTdsRegisterSide(r.tcs, "TCS", "Collectee (customer)")}
    ${(r.generated_notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}
  `;
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: GSTR-1 (Outward Supplies)
// API   : GET /api/v1/business/returns/gstr-1?period=
// NOTE  : loadGstr1, renderGstr1Panel, downloadGstr1Json
// ══════════════════════════════════════════════════════════════════════

async function loadGstr1(period) {
  gstr3bPeriod = period || gstr3bPeriod;
  const result = await apiRequest("mitrabooks", `/api/v1/business/returns/gstr-1?period=${encodeURIComponent(gstr3bPeriod)}`, { method: "GET" });
  lastGstr1 = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { gstr1: { ok: result.ok, period: gstr3bPeriod } });
}

function previewGstr1FromInput() {
  const input = document.querySelector("[data-gstr1-period]");
  loadGstr1(input?.value || gstr3bPeriod);
}

function downloadGstr1Json() {
  const j = lastGstr1?.gstn_json;
  if (!j) { setLoginStatus("warn", "Nothing to download", "Load a GSTR-1 period first."); return; }
  const blob = new Blob([JSON.stringify(j, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `gstr1_${gstr3bPeriod}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  renderJson(apiOutput, { gstr1_download: { period: gstr3bPeriod } });
}

function renderGstr1Panel() {
  const period = gstr3bPeriod;
  const controls = `
    <div class="report-date-controls">
      <label>Return month <input type="month" data-gstr1-period value="${escapeHtml(period)}"></label>
      <button class="secondary" type="button" data-business-action="gstr1-load">Load</button>
      <button class="secondary" type="button" data-business-action="gstr1-download-json">Download GSTN JSON</button>
    </div>`;
  const r = lastGstr1;
  if (!r) { return `${controls}<p class="muted">Loading GSTR-1...</p>`; }
  if (r.ok === false) { return `${controls}${reportUnavailablePanel("GSTR-1", r)}`; }
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const s = r.sections || {};

  const sectionCards = [
    ["B2B (4A)", `${s.b2b?.invoices || 0} inv · ${s.b2b?.recipients || 0} GSTIN`, s.b2b?.taxable_value, s.b2b?.tax],
    ["B2C Large (5)", `${s.b2cl?.invoices || 0} inv`, s.b2cl?.taxable_value, s.b2cl?.tax],
    ["B2C Small (7)", `${s.b2cs?.rows || 0} rows`, s.b2cs?.taxable_value, s.b2cs?.tax],
    ["Exports/SEZ (6A)", `${s.exp?.invoices || 0} inv · zero-rated`, s.exp?.taxable_value, s.exp?.tax],
    ["Credit Notes (9B)", `${s.cdnr?.notes || 0} notes`, s.cdnr?.taxable_value, s.cdnr?.tax],
    ["HSN (12)", `${s.hsn?.rows || 0} rows`, s.hsn?.taxable_value, s.hsn?.tax],
  ].map(([title, sub, txval, tax]) => `
    <article>
      <h4>${escapeHtml(title)}</h4>
      <p class="muted">${escapeHtml(sub)}</p>
      <div class="invoice-totals">
        <div><span>Taxable</span><strong>${num(txval)}</strong></div>
        <div><span>Tax</span><strong>${num(tax)}</strong></div>
      </div>
    </article>`).join("");

  const b2csRows = (r.b2cs_rows || []).map((row) => `
    <tr>
      <td>${escapeHtml(row.pos || "")}</td>
      <td>${escapeHtml(row.supply_type || "")}</td>
      <td class="amount">${escapeHtml(String(row.rate ?? ""))}%</td>
      <td class="amount">${num(row.taxable_value)}</td>
      <td class="amount">${num(row.igst)}</td>
      <td class="amount">${num(row.cgst)}</td>
      <td class="amount">${num(row.sgst)}</td>
    </tr>`).join("");
  const hsnRows = (r.hsn_rows || []).map((row) => `
    <tr>
      <td>${escapeHtml(row.hsn_sac || "")}</td>
      <td>${escapeHtml(row.uqc || "")}</td>
      <td class="amount">${escapeHtml(String(row.rate ?? ""))}%</td>
      <td class="amount">${escapeHtml(String(row.quantity ?? ""))}</td>
      <td class="amount">${num(row.taxable_value)}</td>
      <td class="amount">${num(row.igst)}</td>
      <td class="amount">${num(row.cgst)}</td>
      <td class="amount">${num(row.sgst)}</td>
    </tr>`).join("");

  return `
    ${controls}
    <div class="preview-heading compact">
      <div><p>GSTR-1 outward supplies for ${escapeHtml(period)}${r.gstin ? ` · GSTIN ${escapeHtml(r.gstin)}` : ""}. Built from posted invoices and credit notes. Docs ${escapeHtml(String(s.docs?.total || 0))} (${escapeHtml(s.docs?.from || "-")} → ${escapeHtml(s.docs?.to || "-")}).</p></div>
    </div>
    <div class="dashboard-main-grid platform-grid">${sectionCards}</div>

    <div class="table-preview compact-table">
      <h4>B2C Small (7) — rate-wise by place of supply</h4>
      <table>
        <thead><tr><th>Place of supply</th><th>Type</th><th class="amount">Rate</th><th class="amount">Taxable</th><th class="amount">IGST</th><th class="amount">CGST</th><th class="amount">SGST</th></tr></thead>
        <tbody>${b2csRows || `<tr><td colspan="7" class="muted">No B2C-small supplies.</td></tr>`}</tbody>
      </table>
    </div>

    <div class="table-preview compact-table">
      <h4>HSN summary (12)</h4>
      <table>
        <thead><tr><th>HSN/SAC</th><th>UQC</th><th class="amount">Rate</th><th class="amount">Qty</th><th class="amount">Taxable</th><th class="amount">IGST</th><th class="amount">CGST</th><th class="amount">SGST</th></tr></thead>
        <tbody>${hsnRows || `<tr><td colspan="8" class="muted">No HSN data.</td></tr>`}</tbody>
      </table>
    </div>
    ${(r.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}
  `;
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: ITC REVERSALS (Rule 37 / Re-claim)
// API   : GET /api/v1/business/itc/reversals  POST /api/v1/business/itc/reverse|reclaim
// NOTE  : loadItcReversalPreview, reverseItcForBill, reclaimItcForBill, renderItcReversalPanel
// ══════════════════════════════════════════════════════════════════════

async function loadItcReversalPreview(asOf) {
  itcReversalAsOf = asOf || itcReversalAsOf;
  const result = await apiRequest("mitrabooks", `/api/v1/business/itc-reversals/preview?as_of=${encodeURIComponent(itcReversalAsOf)}`, { method: "GET" });
  lastItcReversal = result.ok ? result.payload : null;
  if (!result.ok) setLoginStatus("warn", "ITC preview unavailable", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  // Also load reversed-but-not-yet-reclaimed bills so the user can reclaim once paid.
  const bills = await apiRequest("mitrabooks", "/api/v1/business/bills?status=posted&limit=500", { method: "GET" });
  lastItcReversedBills = bills.ok && Array.isArray(bills.payload?.items)
    ? bills.payload.items.filter((b) => b.itc_reversed && !b.itc_reclaimed)
    : [];
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { itc_reversal_preview: { ok: result.ok, as_of: itcReversalAsOf, count: lastItcReversal?.count ?? 0 } });
}

function previewItcReversalsFromInput() {
  const input = document.querySelector("[data-itc-asof]");
  loadItcReversalPreview(input?.value || itcReversalAsOf);
}

async function reverseItcForBill(billId) {
  if (!billId) return;
  const result = await apiRequest("mitrabooks", `/api/v1/business/bills/${encodeURIComponent(billId)}/itc-reversal`, {
    method: "POST",
    body: JSON.stringify({ reversal_date: itcReversalAsOf, accounting_entity_id: "primary" }),
  });
  if (result.ok) {
    setLoginStatus("ok", "ITC reversed", `Rule 37 reversal posted for bill ${result.payload?.bill_number || billId}.`);
    await loadItcReversalPreview(itcReversalAsOf);
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can reverse ITC.");
  } else {
    setLoginStatus("danger", "Reversal failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { itc_reversal: { ok: result.ok, status: result.status } });
}

async function reclaimItcForBill(billId) {
  if (!billId) return;
  const result = await apiRequest("mitrabooks", `/api/v1/business/bills/${encodeURIComponent(billId)}/itc-reclaim`, {
    method: "POST",
    body: JSON.stringify({ reclaim_date: todayIsoDate(), accounting_entity_id: "primary" }),
  });
  if (result.ok) {
    setLoginStatus("ok", "ITC reclaimed", `Reversed ITC re-availed for bill ${result.payload?.bill_number || billId}.`);
    await loadItcReversalPreview(itcReversalAsOf);
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can reclaim ITC.");
  } else {
    setLoginStatus("danger", "Reclaim failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { itc_reclaim: { ok: result.ok, status: result.status } });
}

async function markBillPaidFull(billId, amount) {
  if (!billId) return;
  const result = await apiRequest("mitrabooks", `/api/v1/business/bills/${encodeURIComponent(billId)}/payment`, {
    method: "POST",
    body: JSON.stringify({ paid_amount: String(amount || "0"), paid_date: todayIsoDate(), accounting_entity_id: "primary" }),
  });
  if (result.ok) {
    setLoginStatus("ok", "Payment recorded", `Bill ${result.payload?.bill_number || billId} marked paid.`);
    await loadItcReversalPreview(itcReversalAsOf);
  } else {
    setLoginStatus("danger", "Update failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(apiOutput, { bill_payment: { ok: result.ok, status: result.status } });
}

function renderItcReversalPanel() {
  const admin = isBusinessAdmin();
  const num = (v) => formatCurrency(Number(v || 0));
  const data = lastItcReversal;
  let flagged = `<p class="muted">No bills are overdue beyond 180 days as of this date.</p>`;
  if (data && Array.isArray(data.candidates) && data.candidates.length) {
    const rows = data.candidates.map((c) => `
      <tr>
        <td>${escapeHtml(c.bill_number || "")}</td>
        <td>${escapeHtml(c.vendor_name || c.vendor_party_id || "")}</td>
        <td>${escapeHtml(c.bill_date || "")}</td>
        <td>${escapeHtml(c.due_date || "")}</td>
        <td class="amount">${escapeHtml(String(c.days_overdue ?? ""))}</td>
        <td class="amount">${num(c.itc_total)}</td>
        <td class="amount">${num(c.interest_amount)}</td>
        <td><span class="pill warn">${escapeHtml(c.payment_status || "unpaid")}</span></td>
        <td>${escapeHtml(c.gstr3b_ref || "4(B)(2)")}</td>
        <td>
          <button class="secondary" type="button" data-business-action="bill-mark-paid" data-bill-id="${escapeHtml(c.bill_id || "")}" data-bill-amount="${escapeHtml(c.net_payable || c.bill_total || "0")}">Mark paid</button>
          ${admin ? `<button class="primary" type="button" data-business-action="itc-reverse" data-bill-id="${escapeHtml(c.bill_id || "")}">Reverse ITC</button>` : ""}
        </td>
      </tr>
    `).join("");
    flagged = `
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr><th>Bill #</th><th>Vendor</th><th>Bill date</th><th>Due (180d)</th><th class="amount">Days overdue</th><th class="amount">ITC</th><th class="amount">Interest @18%</th><th>Payment</th><th>GSTR-3B</th><th>Action</th></tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <div class="invoice-totals">
        <div><span>Total ITC to reverse</span><strong>${num(data.total_itc)}</strong></div>
        <div class="invoice-grand"><span>Total interest @18%</span><strong>${num(data.total_interest)}</strong></div>
      </div>
      <p class="muted reversal-scope-note">Reversal posts: Dr ITC Reversed (Recoverable), Cr Input GST; plus Dr Interest on GST, Cr Interest Payable. Crediting Input GST raises that month's net GST payable. Reported in GSTR-3B Table 4(B)(2).</p>
    `;
  }

  let reclaimable = "";
  if (Array.isArray(lastItcReversedBills) && lastItcReversedBills.length) {
    const rows = lastItcReversedBills.map((b) => {
      const paid = b.payment_status === "paid";
      return `
      <tr>
        <td>${escapeHtml(b.bill_number || "")}</td>
        <td>${escapeHtml(b.vendor_name || b.vendor_party_id || "")}</td>
        <td>${escapeHtml(b.itc_reversal_date || "")}</td>
        <td class="amount">${num(b.gst_total)}</td>
        <td class="amount">${num(b.itc_interest_amount)}</td>
        <td><span class="pill ${paid ? "ok" : "warn"}">${escapeHtml(b.payment_status || "unpaid")}</span></td>
        <td>
          ${paid
            ? (admin ? `<button class="primary" type="button" data-business-action="itc-reclaim" data-bill-id="${escapeHtml(b.bill_id || "")}">Reclaim ITC</button>` : `<span class="muted">admin only</span>`)
            : `<button class="secondary" type="button" data-business-action="bill-mark-paid" data-bill-id="${escapeHtml(b.bill_id || "")}" data-bill-amount="${escapeHtml(b.net_payable || b.bill_total || "0")}">Mark paid</button>`}
        </td>
      </tr>`;
    }).join("");
    reclaimable = `
      <h4 class="itc-subhead">Reversed — awaiting reclaim</h4>
      <p class="muted">Once the vendor is paid, re-avail the reversed ITC (GSTR-3B Table 4(D)(1)). Interest already charged is not reclaimable.</p>
      <div class="table-preview compact-table">
        <table>
          <thead><tr><th>Bill #</th><th>Vendor</th><th>Reversed on</th><th class="amount">ITC</th><th class="amount">Interest</th><th>Payment</th><th>Action</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  }

  return `
    <div class="report-date-controls">
      <label>As of <input type="date" data-itc-asof value="${escapeHtml(itcReversalAsOf)}"></label>
      <button class="secondary" type="button" data-business-action="itc-preview">Refresh</button>
    </div>
    <div class="preview-heading compact"><div><p>Bills unpaid beyond 180 days require ITC reversal under GST Rule 37.</p></div></div>
    ${flagged}
    ${reclaimable}
  `;
}

async function loadPeriodLocks() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/gst-period-locks", { method: "GET" });
  lastPeriodLocks = result.ok && Array.isArray(result.payload?.items) ? result.payload.items : [];
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { period_locks: { ok: result.ok, count: lastPeriodLocks.length } });
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: GST PERIOD LOCKS
// API   : POST /api/v1/business/gst-period-lock
// NOTE  : setGstPeriodLock, lockGstPeriodFromInput, rerenderBusinessReportsIfActive
// ══════════════════════════════════════════════════════════════════════

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
  const reportWorkspaces = ["reports", "gst-returns", "reconciliation", "tds-tcs", "bank-recon"];
  if (currentExperience === "mitrabooks" && reportWorkspaces.includes(activeBusinessWorkspace)) {
    dashboardPreview.innerHTML = renderBusinessWorkspace();
  }
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: FINANCIAL REPORT LOADERS (TB / P&L / BS / R&P)
// API   : GET /api/v1/business/reports/...
// NOTE  : loadBusinessTrialBalance, loadBusinessProfitLoss, loadBusinessBalanceSheet
// ══════════════════════════════════════════════════════════════════════

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
  // Party-wise Sundry Debtors / Creditors; totals tie to the matching Trial Balance account.
  const asOf = encodeURIComponent(businessReportState.as_of);
  const [arResult, apResult] = await Promise.all([
    apiRequest("mitrabooks", `/api/v1/business/party-ledger?kind=receivable&as_of=${asOf}`, { method: "GET" }),
    apiRequest("mitrabooks", `/api/v1/business/party-ledger?kind=payable&as_of=${asOf}`, { method: "GET" }),
  ]);
  lastBusinessReceivables = reportResultPayload(arResult);
  lastBusinessPayables = reportResultPayload(apResult);
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { receivables: { ok: arResult.ok }, payables: { ok: apResult.ok } });
}

// ---- AR/AP Aging (Phase B backend) -------------------------------------- //

// ══════════════════════════════════════════════════════════════════════
// SECTION: PAYMENT ALLOCATION + AR/AP AGING
// API   : GET /api/v1/business/aging  POST /api/v1/business/allocation
// NOTE  : loadBusinessAging, setAllocationKind, applyFifoSuggestion, submitAllocation
// ══════════════════════════════════════════════════════════════════════

async function loadBusinessAging() {
  const kind = businessReportState.agingKind === "payable" ? "payable" : "receivable";
  const asOf = encodeURIComponent(businessReportState.as_of);
  const result = await apiRequest("mitrabooks", `/api/v1/business/allocations/aging?kind=${kind}&as_of=${asOf}`, { method: "GET" });
  lastBusinessAging = reportResultPayload(result, { kind });
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { aging: { ok: result.ok, kind } });
}

function setAgingKind(kind) {
  businessReportState.agingKind = kind === "payable" ? "payable" : "receivable";
  rerenderBusinessReportsIfActive();
  loadBusinessAging();
}

// ---- Payment Allocation (Phase A backend) ------------------------------- //
async function loadUnallocatedPayments() {
  const kind = allocationState.kind === "payable" ? "payable" : "receivable";
  const result = await apiRequest("mitrabooks", `/api/v1/business/allocations/unallocated-payments?kind=${kind}`, { method: "GET" });
  lastUnallocatedPayments = reportResultPayload(result, { kind });
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { unallocated_payments: { ok: result.ok, kind } });
}

function setAllocationKind(kind) {
  allocationState.kind = kind === "payable" ? "payable" : "receivable";
  allocationState.selectedPaymentId = "";
  allocationState.lines = {};
  lastAllocationOpenItems = null;
  lastAllocationReconciliation = null;
  lastAllocationResult = null;
  rerenderBusinessReportsIfActive();
  loadUnallocatedPayments();
}

async function selectAllocationPayment(paymentId) {
  allocationState.selectedPaymentId = String(paymentId || "");
  allocationState.lines = {};
  lastAllocationResult = null;
  if (!allocationState.selectedPaymentId) {
    lastAllocationOpenItems = null;
    rerenderBusinessReportsIfActive();
    return;
  }
  const kind = allocationState.kind === "payable" ? "payable" : "receivable";
  const asOf = encodeURIComponent(businessReportState.as_of);
  lastAllocationOpenItems = { loading: true };
  rerenderBusinessReportsIfActive();
  // Open items to match against, plus a FIFO suggestion to pre-fill amounts.
  const [openResult, fifoResult] = await Promise.all([
    apiRequest("mitrabooks", `/api/v1/business/allocations/open-items?kind=${kind}&as_of=${asOf}`, { method: "GET" }),
    apiRequest("mitrabooks", `/api/v1/business/allocations/fifo-suggestion?kind=${kind}&payment_id=${encodeURIComponent(allocationState.selectedPaymentId)}&as_of=${asOf}`, { method: "GET" }),
  ]);
  lastAllocationOpenItems = reportResultPayload(openResult, { kind });
  if (fifoResult.ok && Array.isArray(fifoResult.payload?.allocations)) {
    for (const line of fifoResult.payload.allocations) {
      allocationState.lines[line.open_item_id] = String(line.allocated_amount);
    }
  }
  rerenderBusinessReportsIfActive();
  renderJson(apiOutput, { open_items: { ok: openResult.ok }, fifo: { ok: fifoResult.ok } });
}

function setAllocationLineAmount(openItemId, value) {
  if (!openItemId) return;
  const cleaned = String(value || "").trim();
  if (cleaned === "" || Number(cleaned) <= 0) {
    delete allocationState.lines[openItemId];
  } else {
    allocationState.lines[openItemId] = cleaned;
  }
}

function applyFifoSuggestion() {
  // Re-fetch FIFO from current unallocated balance and overwrite the line inputs.
  selectAllocationPayment(allocationState.selectedPaymentId);
}

async function submitAllocation() {
  const paymentId = allocationState.selectedPaymentId;
  if (!paymentId) {
    setLoginStatus("warn", "Select a payment", "Choose an unallocated payment first.");
    return;
  }
  const allocations = Object.entries(allocationState.lines)
    .map(([open_item_id, amount]) => ({ open_item_id, allocated_amount: Number(amount) }))
    .filter((a) => a.allocated_amount > 0);
  if (!allocations.length) {
    setLoginStatus("warn", "Nothing to allocate", "Enter at least one allocation amount.");
    return;
  }
  allocationState.busy = true;
  rerenderBusinessReportsIfActive();
  const result = await apiRequest("mitrabooks", "/api/v1/business/allocations", {
    method: "POST",
    body: JSON.stringify({ kind: allocationState.kind, payment_id: paymentId, allocations }),
  });
  allocationState.busy = false;
  if (result.ok) {
    lastAllocationResult = result.payload;
    setLoginStatus("ok", "Allocation posted", `Matched ${result.payload?.count || allocations.length} open item(s).`);
    allocationState.selectedPaymentId = "";
    allocationState.lines = {};
    lastAllocationOpenItems = null;
    await loadUnallocatedPayments();
    await loadAllocationReconciliation();
  } else {
    setLoginStatus("danger", "Allocation failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
    rerenderBusinessReportsIfActive();
  }
  renderJson(apiOutput, { allocation: { ok: result.ok, status: result.status } });
}

async function loadAllocationReconciliation() {
  const kind = allocationState.kind === "payable" ? "payable" : "receivable";
  const asOf = encodeURIComponent(businessReportState.as_of);
  const result = await apiRequest("mitrabooks", `/api/v1/business/allocations/reconciliation?kind=${kind}&as_of=${asOf}`, { method: "GET" });
  lastAllocationReconciliation = result.ok ? result.payload : null;
  rerenderBusinessReportsIfActive();
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
  const asOfTabs = ["trial-balance", "balance-sheet", "receivables-payables", "aging"];
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

function reportExportToolbar(reportKey, { kind = "", label = "" } = {}) {
  const kAttr = kind ? ` data-report-kind="${escapeHtml(kind)}"` : "";
  const key = escapeHtml(reportKey);
  const lbl = label ? `<span class="export-label muted">${escapeHtml(label)}</span>` : "";
  return `
    <div class="report-export-toolbar" style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:8px 0;">
      ${lbl}
      <button class="secondary" type="button" data-business-action="export-report" data-report-key="${key}" data-report-format="csv"${kAttr}>CSV</button>
      <button class="secondary" type="button" data-business-action="export-report" data-report-key="${key}" data-report-format="xlsx"${kAttr}>Excel</button>
      <button class="secondary" type="button" data-business-action="export-report" data-report-key="${key}" data-report-format="pdf"${kAttr}>PDF</button>
      <button class="secondary" type="button" data-business-action="print-report" title="Open a printable view">Print</button>
    </div>`;
}

// Export/print toolbars per report tab. Backend supports CSV/XLSX/PDF for the
// core set (trial_balance, party_ledger, itc_reversals, aging, balance_sheet,
// profit_loss); other tabs get Print only for now.
function businessReportExports() {
  const tab = businessReportState.tab;
  if (tab === "trial-balance") return reportExportToolbar("trial_balance");
  if (tab === "balance-sheet") return reportExportToolbar("balance_sheet");
  if (tab === "pnl") return reportExportToolbar("profit_loss");
  if (tab === "aging") return reportExportToolbar("aging", { kind: businessReportState.agingKind });
  if (tab === "payment-allocation") return "";  // workflow screen has its own controls
  if (tab === "itc-reversals") return reportExportToolbar("itc_reversals");
  if (tab === "statements") {
    return statementPartyId ? reportExportToolbar("statement", { kind: statementKind }) : "";
  }
  if (tab === "receivables-payables") {
    return `
      ${reportExportToolbar("party_ledger", { kind: "receivable", label: "Debtors:" })}
      ${reportExportToolbar("party_ledger", { kind: "payable", label: "Creditors:" })}`;
  }
  if (tab === "general-ledger") {
    const acc = businessReportState.ledgerAccountId;
    if (acc && acc !== "__all_nonzero__") {
      return reportExportToolbar("general_ledger");
    }
    return `
      <div class="report-export-toolbar" style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:8px 0;">
        <span class="muted">Select a single account to download (CSV/Excel/PDF). "All Ledger Accounts" supports Print only.</span>
        <button class="secondary" type="button" data-business-action="print-report" title="Open a printable view">Print</button>
      </div>`;
  }
  return `
    <div class="report-export-toolbar" style="display:flex;gap:6px;align-items:center;margin:8px 0;">
      <button class="secondary" type="button" data-business-action="print-report" title="Open a printable view">Print</button>
    </div>`;
}

async function downloadBusinessReport(reportKey, format, kind) {
  if (!reportKey) return;
  const params = new URLSearchParams();
  params.set("report", reportKey);
  params.set("format", format || "csv");
  if (kind) params.set("kind", kind);
  if (businessReportState.as_of) params.set("as_of", businessReportState.as_of);
  if (reportKey === "profit_loss") {
    if (businessReportState.from_date) params.set("from_date", businessReportState.from_date);
    if (businessReportState.to_date) params.set("to_date", businessReportState.to_date);
  }
  if (reportKey === "general_ledger") {
    const acc = businessReportState.ledgerAccountId;
    if (!acc || acc === "__all_nonzero__") {
      renderJson(apiOutput, { export_error: { report: reportKey, detail: "Select a single ledger account before downloading." } });
      return;
    }
    params.set("account_id", acc);
  }
  if (reportKey === "statement") {
    if (!statementPartyId) {
      renderJson(apiOutput, { export_error: { report: reportKey, detail: "Select a party before downloading the statement." } });
      return;
    }
    params.set("party_id", statementPartyId);
    params.set("kind", statementKind);
    if (statementFromDate) params.set("from_date", statementFromDate);
    if (statementToDate) params.set("to_date", statementToDate);
  }
  const periodStamp = reportKey === "profit_loss"
    ? `${businessReportState.from_date}_${businessReportState.to_date}`
    : businessReportState.as_of;
  const filename = `${reportKey}${kind ? "_" + kind : ""}_${periodStamp}.${format || "csv"}`;
  const path = `/api/v1/business/reports/export?${params.toString()}`;
  const result = await downloadApiFile("mitrabooks", path, filename, { timeoutMs: 30000 });
  if (result.ok) {
    renderJson(apiOutput, { export: { report: reportKey, format, kind: kind || null, filename } });
  } else {
    renderJson(apiOutput, { export_error: { report: reportKey, format, status: result.status, detail: result.payload?.detail || result.payload } });
  }
}

// Print the currently rendered report by cloning its HTML into a clean window —
// avoids fighting the app's global/screen CSS and works across browsers
// (the user picks "Save as PDF" there too if they prefer a browser-rendered PDF).
function printBusinessReport() {
  const node = document.getElementById("business-report-printable");
  if (!node) { window.print(); return; }
  const win = window.open("", "_blank", "width=940,height=720");
  if (!win) { window.print(); return; }
  win.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>Financial Report</title>
    <style>
      body{font-family:Arial,Helvetica,sans-serif;color:#111;margin:24px;}
      h3,h4{margin:0 0 6px;}
      table{border-collapse:collapse;width:100%;font-size:12px;margin:8px 0 18px;}
      th,td{border:1px solid #ccc;padding:4px 8px;text-align:left;}
      td.amount,th.amount,.amount,.num,td.right{text-align:right;}
      .muted{color:#666;font-size:11px;}
      button,.report-export-toolbar,.report-tabs,.report-date-controls,input,select{display:none!important;}
    </style></head><body>${node.innerHTML}</body></html>`);
  win.document.close();
  win.focus();
  setTimeout(() => { try { win.print(); } catch (_e) {} }, 300);
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
  } else if (businessReportState.tab === "aging") {
    body = renderBusinessAging();
  } else if (businessReportState.tab === "payment-allocation") {
    body = renderPaymentAllocation();
  } else if (businessReportState.tab === "period-locks") {
    body = renderPeriodLocksPanel();
  } else if (businessReportState.tab === "gst-settlement") {
    body = renderGstSettlementPanel();
  } else if (businessReportState.tab === "gst-returns") {
    body = renderGstReturns();
  } else if (businessReportState.tab === "itc-reversals") {
    body = renderItcReversalPanel();
  } else if (businessReportState.tab === "tds") {
    body = renderTdsRegisterPanel();
  } else if (businessReportState.tab === "bank-recon") {
    body = renderBankReconPanel();
  } else if (businessReportState.tab === "statements") {
    body = renderStatementsPanel();
  } else if (businessReportState.tab === "opening-yearend") {
    body = renderOpeningYearEndPanel();
  } else if (businessReportState.tab === "fixed-assets") {
    body = renderFixedAssetsPanel();
  } else if (businessReportState.tab === "dimensions") {
    body = renderDimensionsPanel();
  } else if (businessReportState.tab === "inventory") {
    body = renderInventoryPanel();
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
      ${businessReportExports()}
      <div id="business-report-printable">${body}</div>
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
  // Show the NET balance per account in its natural column (Dr if positive, Cr if negative).
  // Totals are the sums of those nets, which still balance.
  let netDebitTotal = 0;
  let netCreditTotal = 0;
  const bodyRows = rows.map((row) => {
    const net = Number(row.net_balance != null ? row.net_balance : (Number(row.debit_total || 0) - Number(row.credit_total || 0)));
    const debitCell = net >= 0 ? net : 0;
    const creditCell = net < 0 ? -net : 0;
    netDebitTotal += debitCell;
    netCreditTotal += creditCell;
    return `
      <tr>
        <td>${escapeHtml(row.account_code || "")}</td>
        <td>${escapeHtml(row.account_name || "")}</td>
        <td class="amount">${debitCell ? escapeHtml(formatCurrency(debitCell)) : ""}</td>
        <td class="amount">${creditCell ? escapeHtml(formatCurrency(creditCell)) : ""}</td>
        <td>
          <button class="secondary" type="button" data-business-action="report-ledger" data-account-id="${escapeHtml(row.account_id || "")}">Open</button>
        </td>
      </tr>`;
  }).join("");
  return `
    <div class="preview-heading compact">
      <div><p>As of ${escapeHtml(payload.as_of || businessReportState.as_of)}. Net balance per account; debit and credit totals must match.</p></div>
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
          ${rows.length ? bodyRows : `
            <tr><td colspan="5" class="muted">No posted balances found for this tenant.</td></tr>
          `}
        </tbody>
        <tfoot>
          <tr>
            <th colspan="2">Total</th>
            <th class="amount">${escapeHtml(formatCurrency(netDebitTotal))}</th>
            <th class="amount">${escapeHtml(formatCurrency(netCreditTotal))}</th>
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
  const assets = Array.isArray(payload.assets) ? payload.assets : [];
  const liabilities = Array.isArray(payload.liabilities) ? payload.liabilities : [];
  const equity = Array.isArray(payload.equity) ? payload.equity : [];
  const totalAssets = Number(payload.total_assets || 0);
  const liabPlusEquity = Number(payload.total_liabilities || 0) + Number(payload.total_equity || 0);

  const bsRows = (rows) => rows.length
    ? rows.map((line) => `
        <tr>
          <td>${escapeHtml(line.account_code || "")}</td>
          <td>${escapeHtml(line.account_name || "")}</td>
          <td class="amount">${escapeHtml(formatCurrency(line.balance || 0))}</td>
        </tr>`).join("")
    : `<tr><td colspan="3" class="muted">No rows.</td></tr>`;
  const subHead = (label) => `<tr><td colspan="3" style="font-weight:600;padding-top:8px;">${escapeHtml(label)}</td></tr>`;
  const totalRow = (label, value) => `
    <tr style="font-weight:700;border-top:2px solid var(--border, #3a3f4b);">
      <td colspan="2">${escapeHtml(label)}</td>
      <td class="amount">${escapeHtml(formatCurrency(value))}</td>
    </tr>`;
  const sideTable = (title, bodyHtml) => `
    <div class="table-preview compact-table">
      <h4>${escapeHtml(title)}</h4>
      <table>
        <thead><tr><th>Code</th><th>Account</th><th class="amount">Amount</th></tr></thead>
        <tbody>${bodyHtml}</tbody>
      </table>
    </div>`;

  // Standard two-sided balance sheet: Liabilities & Equity on the left, Assets on
  // the right; each side totals to the same figure when balanced. The grid
  // auto-stacks to one column on narrow screens so it always fits.
  return `
    <div class="preview-heading compact">
      <div><p>As of ${escapeHtml(payload.as_of || businessReportState.as_of)}. Assets = Liabilities + Equity.</p></div>
      <span class="pill ${payload.balanced ? "ok" : "warn"}">${payload.balanced ? "balanced" : "not balanced"}</span>
    </div>
    <div class="bs-tformat" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;align-items:start;">
      ${sideTable("Liabilities & Equity",
        subHead("Capital & Reserves (Equity)") + bsRows(equity) +
        subHead("Liabilities") + bsRows(liabilities) +
        totalRow("Total Liabilities + Equity", liabPlusEquity))}
      ${sideTable("Assets",
        bsRows(assets) + totalRow("Total Assets", totalAssets))}
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
  // Party-wise rows from /business/party-ledger (items: party_name + balance);
  // falls back to legacy account-level "lines" if present.
  const lines = Array.isArray(payload.items) ? payload.items : (Array.isArray(payload.lines) ? payload.lines : []);
  return `
    <article>
      <h4>${escapeHtml(title)} <span class="pill">${escapeHtml(formatCurrency(payload.total_balance || 0))}</span></h4>
      <p class="muted">${escapeHtml(subtitle)}</p>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr><th>Party</th><th class="amount">Balance</th></tr>
          </thead>
          <tbody>
            ${lines.length ? lines.map((line) => `
              <tr>
                <td>${escapeHtml(line.party_name || line.account_name || "")}</td>
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
      <div><p>Party-wise outstanding as of ${escapeHtml(businessReportState.as_of)}. Totals tie to the Sundry Debtors / Creditors balances in the Trial Balance.</p></div>
    </div>
    <div class="dashboard-main-grid platform-grid">
      ${renderReceivablesPayablesSection("Sundry Debtors", "Amounts owed by customers, party-wise. 'Unallocated' = direct entries with no party tag.", lastBusinessReceivables)}
      ${renderReceivablesPayablesSection("Sundry Creditors", "Amounts owed to vendors, party-wise. 'Unallocated' = direct entries with no party tag.", lastBusinessPayables)}
    </div>
  `;
}

// Kind toggle (receivable/payable) reused by the Aging and Allocation screens.
function kindToggle(activeKind, action) {
  const btn = (k, label) => `
    <button class="report-tab ${activeKind === k ? "active" : ""}" type="button"
      data-business-action="${action}" data-alloc-kind="${k}">${label}</button>`;
  return `<div class="report-tabs" role="tablist" style="margin:0 0 10px;">
    ${btn("receivable", "Receivable (Debtors)")}${btn("payable", "Payable (Creditors)")}
  </div>`;
}

function renderBusinessAging() {
  const payload = lastBusinessAging;
  const toggle = kindToggle(businessReportState.agingKind, "aging-kind");
  if (!payload) {
    return `${toggle}<p class="muted">Loading aging report...</p>`;
  }
  if (payload.ok === false) {
    return `${toggle}${reportUnavailablePanel("AR/AP Aging", payload)}`;
  }
  const order = Array.isArray(payload.buckets_order) ? payload.buckets_order : [];
  const rows = Array.isArray(payload.by_party) ? payload.by_party : [];
  const totals = payload.totals || {};
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const headCols = order.map((b) => `<th class="amount">${escapeHtml(b)}</th>`).join("");
  const totalCols = order.map((b) => `<td class="amount">${num(totals[b])}</td>`).join("");
  const bodyRows = rows.length ? rows.map((r) => {
    const buckets = r.buckets || {};
    const cells = order.map((b) => `<td class="amount">${num(buckets[b])}</td>`).join("");
    return `<tr>
      <td>${escapeHtml(r.party_name || "Unallocated")}</td>
      ${cells}
      <td class="amount"><strong>${num(r.total)}</strong></td>
    </tr>`;
  }).join("") : `<tr><td colspan="${order.length + 2}" class="muted">No outstanding ${escapeHtml(payload.kind || "")} balances.</td></tr>`;
  const label = (payload.kind === "payable") ? "Payables" : "Receivables";
  return `
    ${toggle}
    <div class="preview-heading compact">
      <div><p>${escapeHtml(label)} aging as of ${escapeHtml(payload.as_of || businessReportState.as_of)}, by party and overdue bucket. Grand total ties to the matching control account.</p></div>
      <span class="pill">${num(payload.grand_total)}</span>
    </div>
    <div class="table-preview compact-table">
      <table>
        <thead><tr><th>Party</th>${headCols}<th class="amount">Total</th></tr></thead>
        <tbody>${bodyRows}</tbody>
        <tfoot><tr><th>Total</th>${totalCols}<td class="amount"><strong>${num(payload.grand_total)}</strong></td></tr></tfoot>
      </table>
    </div>
  `;
}

function renderPaymentAllocation() {
  const toggle = kindToggle(allocationState.kind, "alloc-kind");
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const payments = lastUnallocatedPayments;
  const partyLabel = allocationState.kind === "payable" ? "Payments made (to vendors)" : "Receipts collected (from customers)";

  let paymentsBlock;
  if (!payments) {
    paymentsBlock = `<p class="muted">Loading unallocated payments...</p>`;
  } else if (payments.ok === false) {
    paymentsBlock = reportUnavailablePanel("Unallocated Payments", payments);
  } else {
    const items = Array.isArray(payments.items) ? payments.items : [];
    paymentsBlock = `
      <h4>Unallocated ${escapeHtml(allocationState.kind === "payable" ? "Payments" : "Receipts")}
        <span class="pill">${num(payments.total_unallocated)}</span></h4>
      <p class="muted">${escapeHtml(partyLabel)} with an unmatched balance. Pick one to allocate against open items.</p>
      <div class="table-preview compact-table">
        <table>
          <thead><tr><th>Number</th><th>Date</th><th class="amount">Amount</th><th class="amount">Unallocated</th><th></th></tr></thead>
          <tbody>
            ${items.length ? items.map((p) => `
              <tr class="${p.payment_id === allocationState.selectedPaymentId ? "active-row" : ""}">
                <td>${escapeHtml(p.payment_number || p.payment_id)}</td>
                <td>${escapeHtml(p.payment_date || "")}</td>
                <td class="amount">${num(p.amount)}</td>
                <td class="amount">${num(p.unallocated)}</td>
                <td><button class="secondary" type="button" data-business-action="alloc-select-payment" data-payment-id="${escapeHtml(p.payment_id)}">${p.payment_id === allocationState.selectedPaymentId ? "Selected" : "Allocate"}</button></td>
              </tr>
            `).join("") : `<tr><td colspan="5" class="muted">No unallocated payments. Everything is matched.</td></tr>`}
          </tbody>
        </table>
      </div>`;
  }

  let matchBlock = "";
  if (allocationState.selectedPaymentId) {
    const open = lastAllocationOpenItems;
    if (open && open.loading) {
      matchBlock = `<p class="muted">Loading open items...</p>`;
    } else if (open && open.ok === false) {
      matchBlock = reportUnavailablePanel("Open Items", open);
    } else if (open) {
      const items = Array.isArray(open.items) ? open.items : [];
      const entered = Object.entries(allocationState.lines)
        .reduce((sum, [, v]) => sum + (Number(v) || 0), 0);
      const rows = items.length ? items.map((it) => {
        const val = allocationState.lines[it.open_item_id] || "";
        const overdue = Number(it.days_overdue || 0) > 0;
        return `
          <tr>
            <td>${escapeHtml(it.open_item_number || it.open_item_id)}</td>
            <td>${escapeHtml(it.due_date || it.item_date || "")}${overdue ? ` <span class="pill warn">${escapeHtml(String(it.days_overdue))}d</span>` : ""}</td>
            <td class="amount">${num(it.total)}</td>
            <td class="amount">${num(it.outstanding)}</td>
            <td class="amount"><input type="number" step="0.01" min="0" max="${escapeHtml(String(it.outstanding))}" value="${escapeHtml(val)}" data-alloc-line="${escapeHtml(it.open_item_id)}" style="width:120px;text-align:right;"></td>
          </tr>`;
      }).join("") : `<tr><td colspan="5" class="muted">No open items to match for this party.</td></tr>`;
      matchBlock = `
        <h4>Match against open items</h4>
        <p class="muted">Amounts pre-filled oldest-first (FIFO). Adjust as needed, then allocate. Allocation records the match as metadata — it posts no new ledger entries.</p>
        <div class="table-preview compact-table">
          <table>
            <thead><tr><th>Item</th><th>Due</th><th class="amount">Total</th><th class="amount">Outstanding</th><th class="amount">Allocate</th></tr></thead>
            <tbody>${rows}</tbody>
            <tfoot><tr><th colspan="4">Total to allocate</th><td class="amount"><strong>${num(entered)}</strong></td></tr></tfoot>
          </table>
        </div>
        <div style="display:flex;gap:8px;margin-top:10px;">
          <button class="secondary" type="button" data-business-action="alloc-fifo">Re-apply FIFO</button>
          <button type="button" data-business-action="alloc-submit" ${allocationState.busy ? "disabled" : ""}>${allocationState.busy ? "Posting..." : "Post Allocation"}</button>
        </div>`;
    }
  } else {
    matchBlock = `<p class="muted">Select a payment above to begin matching.</p>`;
  }

  let reconBlock = "";
  const recon = lastAllocationReconciliation;
  if (recon) {
    reconBlock = `
      <div class="preview-heading compact" style="margin-top:14px;">
        <div><p>Reconciliation: open items ${num(recon.open_items_outstanding)} − unallocated ${num(recon.unallocated_payments)} = computed ${num(recon.computed_net)} vs ledger ${num(recon.ledger_balance)}.</p></div>
        <span class="pill ${recon.balanced ? "ok" : "warn"}">${recon.balanced ? "reconciled" : "off by " + num(recon.difference)}</span>
      </div>`;
  }

  return `
    ${toggle}
    ${paymentsBlock}
    <hr style="margin:16px 0;border:none;border-top:1px solid #e5e7eb;">
    ${matchBlock}
    ${reconBlock}
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
  tcs_section: "",
  cost_centre_id: "",
  project_id: "",
};

// TDS/TCS section masters from GET /business/tds/sections (cached per session).
let tdsSectionsCache = null;
async function loadTdsSections() {
  if (tdsSectionsCache) return tdsSectionsCache;
  const result = await apiRequest("mitrabooks", "/api/v1/business/tds/sections", { method: "GET" });
  if (result.ok) tdsSectionsCache = result.payload;
  return tdsSectionsCache;
}

function tdsSectionRate(kind, section) {
  const rows = tdsSectionsCache?.[kind] || [];
  const hit = rows.find((r) => r.section === section);
  return hit ? Number(hit.rate) : 0;
}

function tdsSectionOptions(kind, selected) {
  const rows = tdsSectionsCache?.[kind] || [];
  const none = `<option value="">No ${kind === "tds" ? "TDS" : "TCS"}</option>`;
  return none + rows.map((r) =>
    `<option value="${escapeHtml(r.section)}" ${r.section === selected ? "selected" : ""}>${escapeHtml(`${r.section} · ${r.label} @ ${r.rate}%`)}</option>`
  ).join("");
}

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

function isCaViewer() {
  const role = String(lastModuleContext?.role || lastModuleContext?.user_role || "").trim().toLowerCase();
  return role === "ca_viewer";
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
  salesFormHeader.tcs_section = val("select[name='tcs_section']");
  salesFormHeader.cost_centre_id = val("select[name='cost_centre_id']");
  salesFormHeader.project_id = val("select[name='project_id']");
  invoiceFormLines = Array.from(form.querySelectorAll("[data-invoice-line]")).map((row) => ({
    id: row.getAttribute("data-invoice-line"),
    description: row.querySelector("input[name='description']")?.value || "",
    item_id: row.querySelector("select[name='item_id']")?.value || "",
    hsn_sac: row.querySelector("input[name='hsn_sac']")?.value || "",
    uqc: row.querySelector("input[name='uqc']")?.value || "",
    supply_type: row.querySelector("select[name='supply_type']")?.value || "taxable",
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
    // Zero-rated (export/SEZ under LUT) lines carry no tax regardless of rate.
    const supplyType = row.querySelector("select[name='supply_type']")?.value || "taxable";
    const gstRate = supplyType === "zero_rated" ? 0 : row.querySelector("input[name='gst_rate']")?.value;
    const c = computeInvoiceLine(qty, rate, gstRate, inter);
    row.querySelector("[data-line-taxable]").textContent = formatCurrency(c.taxable);
    row.querySelector("[data-line-gst]").textContent = formatCurrency(c.cgst + c.sgst + c.igst);
    row.querySelector("[data-line-total]").textContent = formatCurrency(c.total);
    taxableTotal += c.taxable; cgstTotal += c.cgst; sgstTotal += c.sgst; igstTotal += c.igst;
  });
  const gstTotal = round2(cgstTotal + sgstTotal + igstTotal);
  const invoiceTotal = round2(taxableTotal + gstTotal);
  // TCS (206C) is computed on the GST-inclusive invoice total.
  const tcsSection = form.querySelector("select[name='tcs_section']")?.value || "";
  const tcsAmount = tcsSection ? round2(invoiceTotal * tdsSectionRate("tcs", tcsSection) / 100) : 0;
  const set = (sel, v) => { const el = form.querySelector(sel); if (el) el.textContent = formatCurrency(v); };
  set("[data-total-taxable]", taxableTotal);
  set("[data-total-cgst]", cgstTotal);
  set("[data-total-sgst]", sgstTotal);
  set("[data-total-igst]", igstTotal);
  set("[data-total-invoice]", invoiceTotal);
  set("[data-total-tcs]", tcsAmount);
  set("[data-total-grand]", round2(invoiceTotal + tcsAmount));
  const tcsRow = form.querySelector("[data-row-tcs]");
  const grandRow = form.querySelector("[data-row-grand]");
  if (tcsRow) tcsRow.hidden = !tcsSection;
  if (grandRow) grandRow.hidden = !tcsSection;
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
  invoiceFormLines = [{ id: `il-${++invoiceLineSeq}`, description: "", hsn_sac: "", uqc: "", supply_type: "taxable", quantity: "1", rate: "", gst_rate: "18" }];
  salesFormHeader.customer_party_id = "";
  salesFormHeader.invoice_date = todayIsoDate();
  salesFormHeader.due_date = "";
  salesFormHeader.is_inter_state = false;
  salesFormHeader.income_account_code = "41001";
  salesFormHeader.place_of_supply = "";
  salesFormHeader.reference = "";
  salesFormHeader.notes = "";
  salesFormHeader.tcs_section = "";
  salesFormHeader.cost_centre_id = "";
  salesFormHeader.project_id = "";
  // Make sure customers, accounts, and settings are available for the form.
  if (!Array.isArray(lastBusinessParties) || lastBusinessParties.length === 0) loadBusinessParties();
  if (!hasLoadedBusinessAccounts()) loadBusinessAccounts();
  if (!lastInvoiceSettings) loadInvoiceSettings();
  if (!tdsSectionsCache) loadTdsSections().then(() => rerenderSalesIfActive());
  if (!lastDimensions) loadDimensions().then(() => rerenderSalesIfActive());
  if (!lastInventoryItems) loadInventoryItems().then(() => rerenderSalesIfActive());
  setBusinessSalesView("create");
}

function addInvoiceLine() {
  syncSalesFormFromDom();
  invoiceFormLines.push({ id: `il-${++invoiceLineSeq}`, description: "", hsn_sac: "", uqc: "", supply_type: "taxable", quantity: "1", rate: "", gst_rate: "18" });
  rerenderSalesIfActive();
  updateInvoiceTotalsDisplay();
}

function removeInvoiceLine(lineId) {
  syncSalesFormFromDom();
  invoiceFormLines = invoiceFormLines.filter((l) => l.id !== lineId);
  if (invoiceFormLines.length === 0) {
    invoiceFormLines.push({ id: `il-${++invoiceLineSeq}`, description: "", hsn_sac: "", uqc: "", supply_type: "taxable", quantity: "1", rate: "", gst_rate: "18" });
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
      item_id: String(l.item_id || "").trim() || null,
      hsn_sac: String(l.hsn_sac || "").trim() || null,
      uqc: String(l.uqc || "").trim().toUpperCase() || null,
      supply_type: l.supply_type || "taxable",
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
    tcs_section: salesFormHeader.tcs_section || null,
    cost_centre_id: salesFormHeader.cost_centre_id || null,
    project_id: salesFormHeader.project_id || null,
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
    lastEinvoiceView = null;
    loadEinvoiceView(invoiceId);  // async — the section fills in when it lands
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
  const itemSelectable = !!inventoryItemOptions("");
  const lineRows = invoiceFormLines.map((l) => `
    <tr data-invoice-line="${escapeHtml(l.id)}">
      <td><input type="text" name="description" value="${escapeHtml(l.description)}" placeholder="Item / service"></td>
      ${itemSelectable ? `<td><select name="item_id" style="min-width:110px;">${inventoryItemOptions(l.item_id || "")}</select></td>` : ""}
      ${hsnVisible ? `<td><input type="text" name="hsn_sac" value="${escapeHtml(l.hsn_sac)}" placeholder="HSN/SAC"></td>` : ""}
      ${hsnVisible ? `<td><input type="text" name="uqc" value="${escapeHtml(l.uqc || "")}" placeholder="UQC" style="width:70px;"></td>` : ""}
      <td><select name="supply_type" style="min-width:96px;">
        ${[["taxable", "Taxable"], ["zero_rated", "Zero-rated (exp/SEZ)"], ["exempt", "Exempt"], ["nil_rated", "Nil-rated"], ["non_gst", "Non-GST"]].map(([v, t]) =>
          `<option value="${v}" ${(l.supply_type || "taxable") === v ? "selected" : ""}>${t}</option>`).join("")}
      </select></td>
      <td><input type="number" name="quantity" value="${escapeHtml(l.quantity)}" min="0" step="any"></td>
      <td><input type="number" name="rate" value="${escapeHtml(l.rate)}" min="0" step="any" placeholder="0.00"></td>
      <td><input type="number" name="gst_rate" value="${escapeHtml(l.gst_rate)}" min="0" max="100" step="any"></td>
      <td class="amount" data-line-taxable>—</td>
      <td class="amount" data-line-gst>—</td>
      <td class="amount" data-line-total>—</td>
      <td><button class="secondary" type="button" data-business-action="remove-invoice-line" data-line-id="${escapeHtml(l.id)}">✕</button></td>
    </tr>
  `).join("");

  const isComposition = (lastInvoiceSettings?.branding?.gst_registration_type === "composition");
  const docTitle = isComposition ? "New Bill of Supply" : "New Sales Invoice";
  const docSubtitle = isComposition
    ? `Next number: <strong>${escapeHtml(invoiceNumberPreview())}</strong> · composition dealer — no GST is collected; posts to receivables and income only.`
    : `Next number: <strong>${escapeHtml(invoiceNumberPreview())}</strong> · posts to receivables, sales income, and output GST automatically.`;
  const compositionBanner = isComposition
    ? `<p class="muted" style="padding:8px 10px;border:1px solid #f59e0b;border-radius:6px;background:#fffbeb;">⚠ Composition taxable person, not eligible to collect tax on supplies. GST rates entered below are ignored; inter-state sales are blocked.</p>`
    : "";
  return `
    <div class="verification-panel erp-workspace-panel" data-invoice-form>
      <div class="preview-heading compact">
        <div>
          <h4>${escapeHtml(docTitle)}</h4>
          <p>${docSubtitle}</p>
        </div>
        <button class="secondary" type="button" data-business-action="invoice-back">← Back to list</button>
      </div>
      ${compositionBanner}
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
        <label>TCS (income-tax, on sale consideration)
          <select name="tcs_section">${tdsSectionOptions("tcs", salesFormHeader.tcs_section)}</select>
        </label>
        ${dimensionOptions("cost_centre", salesFormHeader.cost_centre_id) ? `<label>Cost centre
          <select name="cost_centre_id">${dimensionOptions("cost_centre", salesFormHeader.cost_centre_id)}</select>
        </label>` : ""}
        ${dimensionOptions("project", salesFormHeader.project_id) ? `<label>Project
          <select name="project_id">${dimensionOptions("project", salesFormHeader.project_id)}</select>
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
              ${itemSelectable ? `<th>Item</th>` : ""}
              ${hsnVisible ? `<th>HSN/SAC${hsnRequired ? " *" : ""}</th>` : ""}
              ${hsnVisible ? `<th>UQC</th>` : ""}
              <th>Type</th>
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
        <div data-row-tcs ${salesFormHeader.tcs_section ? "" : "hidden"}><span>TCS</span><strong data-total-tcs>${formatCurrency(0)}</strong></div>
        <div class="invoice-grand" data-row-grand ${salesFormHeader.tcs_section ? "" : "hidden"}><span>Amount receivable</span><strong data-total-grand>${formatCurrency(0)}</strong></div>
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
          <h4>${escapeHtml(inv.is_composition || inv.document_type === "bill_of_supply" ? "Bill of Supply" : "Invoice")} ${escapeHtml(inv.invoice_number || "")} ${invoiceStatusPill(inv.status)}${inv.is_composition || inv.document_type === "bill_of_supply" ? ` <span class="pill">composition</span>` : ""}</h4>
          <p>${escapeHtml(inv.customer_name || inv.customer_party_id || "")}${inv.customer_gstin ? ` · ${escapeHtml(inv.customer_gstin)}` : ""} · ${escapeHtml(inv.invoice_date || "")}${inv.due_date ? ` · due ${escapeHtml(inv.due_date)}` : ""}</p>
        </div>
        <div class="invoice-detail-actions">
          <button class="secondary" type="button" data-business-action="invoice-back">← Back to list</button>
          ${String(inv.status).toLowerCase() === "posted" && !invoiceReverseOpen ? `<button class="secondary" type="button" data-business-action="begin-reverse-invoice">Reverse Invoice</button>` : ""}
        </div>
      </div>
      ${String(inv.status).toLowerCase() === "posted" && invoiceReverseOpen ? reversalPanel("invoice", inv.invoice_id, inv.invoice_date) : ""}
      <p class="muted">${escapeHtml(inv.is_composition || inv.document_type === "bill_of_supply" ? "Composition taxable person, not eligible to collect tax on supplies" : (inv.is_inter_state ? "Inter-state supply (IGST)" : "Intra-state supply (CGST + SGST)"))}${inv.reference ? ` · Ref: ${escapeHtml(inv.reference)}` : ""}</p>
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
        ${Number(inv.tcs_amount || 0) > 0 ? `
        <div><span>TCS ${escapeHtml(inv.tcs_section || "")} @ ${escapeHtml(String(inv.tcs_rate || 0))}%</span><strong>${formatCurrency(inv.tcs_amount || 0)}</strong></div>
        <div class="invoice-grand"><span>Amount receivable</span><strong>${formatCurrency(inv.grand_total || inv.invoice_total || 0)}</strong></div>` : ""}
      </div>
      ${inv.collectee_pan_missing ? `<p class="muted">⚠ Customer PAN missing — section 206AA prescribes a higher TCS rate. Capture the PAN on the party record.</p>` : ""}
      ${renderEinvoiceSection(inv)}
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
  // Merge the GST registration choices into branding, preserving other fields.
  const regType = panel.querySelector("[data-gst-reg='type']")?.value === "composition" ? "composition" : "regular";
  const regCategory = panel.querySelector("[data-gst-reg='category']")?.value || "goods";
  const branding = {
    ...((lastInvoiceSettings && lastInvoiceSettings.branding) || {}),
    gst_registration_type: regType,
    composition_category: regType === "composition" ? regCategory : null,
  };
  const inventoryToggle = panel.querySelector("[data-inventory-enabled]");
  const body = {
    field_config,
    numbering,
    // Preserve sections managed in Phase 2 (custom fields).
    custom_fields: (lastInvoiceSettings && lastInvoiceSettings.custom_fields) || [],
    branding,
    inventory_enabled: inventoryToggle ? !!inventoryToggle.checked : !!lastInvoiceSettings?.inventory_enabled,
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

      <h5 class="settings-section-title">GST registration</h5>
      <p class="muted">Composition dealers (Section 10) issue a <strong>Bill of Supply</strong>, do not collect GST, and cannot claim ITC. Inter-state sales are not allowed.</p>
      <div class="invoice-form-grid">
        <label>Registration type
          <select data-gst-reg="type">
            <option value="regular" ${(s.branding?.gst_registration_type || "regular") !== "composition" ? "selected" : ""}>Regular (collect GST, claim ITC)</option>
            <option value="composition" ${s.branding?.gst_registration_type === "composition" ? "selected" : ""}>Composition (Bill of Supply)</option>
          </select>
        </label>
        <label>Composition category
          <select data-gst-reg="category">
            <option value="goods" ${(s.branding?.composition_category || "goods") === "goods" ? "selected" : ""}>Manufacturer / Trader — 1%</option>
            <option value="restaurant" ${s.branding?.composition_category === "restaurant" ? "selected" : ""}>Restaurant (non-alcoholic) — 5%</option>
            <option value="services" ${s.branding?.composition_category === "services" ? "selected" : ""}>Other services — 6%</option>
          </select>
        </label>
      </div>

      <h5 class="settings-section-title">Inventory accounting</h5>
      <p class="muted">Optional. Service businesses and traders who don't keep stock should leave this OFF — nothing changes for them. When ON, the item master, stock register and the period-end closing-stock journal appear under Financial Statements → Inventory.</p>
      <label class="invoice-inter-toggle">
        <input type="checkbox" data-inventory-enabled ${s.inventory_enabled ? "checked" : ""}>
        Enable inventory accounting (item master, stock register, closing stock)
      </label>

      <p class="muted settings-coming-soon">Custom fields and invoice branding / print template are coming in the next update.</p>

      <div class="invoice-form-actions">
        <button class="primary" type="button" data-business-action="save-invoice-settings">Save Settings</button>
        <button class="secondary" type="button" data-business-action="invoice-back">Cancel</button>
      </div>
    </div>
  `;
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: SALES INVOICES WORKSPACE
// API   : GET /api/v1/business/invoices  POST /api/v1/business/invoices
// NOTE  : loadBusinessInvoices, submitInvoice, renderBusinessSalesWorkspace; e-invoice section included
// ══════════════════════════════════════════════════════════════════════

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
  is_reverse_charge: false,
  expense_account_code: "51001",
  place_of_supply: "",
  notes: "",
  tds_section: "",
  cost_centre_id: "",
  project_id: "",
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
  billFormHeader.is_reverse_charge = !!form.querySelector("input[name='is_reverse_charge']")?.checked;
  billFormHeader.expense_account_code = val("select[name='expense_account_code']") || "51001";
  billFormHeader.place_of_supply = val("input[name='place_of_supply']");
  billFormHeader.notes = val("textarea[name='notes']");
  billFormHeader.tds_section = val("select[name='tds_section']");
  billFormHeader.cost_centre_id = val("select[name='cost_centre_id']");
  billFormHeader.project_id = val("select[name='project_id']");
  billFormLines = Array.from(form.querySelectorAll("[data-bill-line]")).map((row) => ({
    id: row.getAttribute("data-bill-line"),
    description: row.querySelector("input[name='description']")?.value || "",
    item_id: row.querySelector("select[name='item_id']")?.value || "",
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
  // TDS is deducted on the GST-exclusive taxable value (Circular 23/2017).
  const tdsSection = form.querySelector("select[name='tds_section']")?.value || "";
  const tdsAmount = tdsSection ? round2(taxableTotal * tdsSectionRate("tds", tdsSection) / 100) : 0;
  // Under RCM the vendor is owed the taxable value only; the GST is our own
  // (cash-only) liability shown on its own row.
  const isRcm = !!form.querySelector("input[name='is_reverse_charge']")?.checked;
  const vendorOwed = isRcm ? taxableTotal : billTotal;
  const set = (sel, v) => { const el = form.querySelector(sel); if (el) el.textContent = formatCurrency(v); };
  set("[data-total-taxable]", taxableTotal);
  set("[data-total-cgst]", cgstTotal);
  set("[data-total-sgst]", sgstTotal);
  set("[data-total-igst]", igstTotal);
  set("[data-total-bill]", billTotal);
  set("[data-total-rcm]", gstTotal);
  set("[data-total-tds]", tdsAmount);
  set("[data-total-net-payable]", round2(vendorOwed - tdsAmount));
  const rcmRow = form.querySelector("[data-row-rcm]");
  const tdsRow = form.querySelector("[data-row-tds]");
  const netRow = form.querySelector("[data-row-net-payable]");
  if (rcmRow) rcmRow.hidden = !isRcm;
  if (tdsRow) tdsRow.hidden = !tdsSection;
  if (netRow) netRow.hidden = !(tdsSection || isRcm);
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
  billFormHeader.is_reverse_charge = false;
  billFormHeader.expense_account_code = "51001";
  billFormHeader.place_of_supply = "";
  billFormHeader.notes = "";
  billFormHeader.tds_section = "";
  billFormHeader.cost_centre_id = "";
  billFormHeader.project_id = "";
  if (!Array.isArray(lastBusinessParties) || lastBusinessParties.length === 0) loadBusinessParties();
  if (!hasLoadedBusinessAccounts()) loadBusinessAccounts();
  if (!tdsSectionsCache) loadTdsSections().then(() => rerenderPurchaseIfActive());
  if (!lastDimensions) loadDimensions().then(() => rerenderPurchaseIfActive());
  if (!lastInventoryItems) loadInventoryItems().then(() => rerenderPurchaseIfActive());
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
      item_id: String(l.item_id || "").trim() || null,
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
    is_reverse_charge: !!billFormHeader.is_reverse_charge,
    expense_account_code: billFormHeader.expense_account_code || "51001",
    place_of_supply: String(billFormHeader.place_of_supply || "").trim() || null,
    notes: String(billFormHeader.notes || "").trim() || null,
    line_items: lineItems,
    tds_section: billFormHeader.tds_section || null,
    cost_centre_id: billFormHeader.cost_centre_id || null,
    project_id: billFormHeader.project_id || null,
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
  const itemSelectable = !!inventoryItemOptions("");
  const lineRows = billFormLines.map((l) => `
    <tr data-bill-line="${escapeHtml(l.id)}">
      <td><input type="text" name="description" value="${escapeHtml(l.description)}" placeholder="Item / service"></td>
      ${itemSelectable ? `<td><select name="item_id" style="min-width:110px;">${inventoryItemOptions(l.item_id || "")}</select></td>` : ""}
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
        <label>TDS (income-tax, on taxable value)
          <select name="tds_section">${tdsSectionOptions("tds", billFormHeader.tds_section)}</select>
        </label>
        ${dimensionOptions("cost_centre", billFormHeader.cost_centre_id) ? `<label>Cost centre
          <select name="cost_centre_id">${dimensionOptions("cost_centre", billFormHeader.cost_centre_id)}</select>
        </label>` : ""}
        ${dimensionOptions("project", billFormHeader.project_id) ? `<label>Project
          <select name="project_id">${dimensionOptions("project", billFormHeader.project_id)}</select>
        </label>` : ""}
        <label class="invoice-inter-toggle">
          <input type="checkbox" name="is_inter_state" ${billFormHeader.is_inter_state ? "checked" : ""}>
          Inter-state supply (IGST)
        </label>
        <label class="invoice-inter-toggle">
          <input type="checkbox" name="is_reverse_charge" ${billFormHeader.is_reverse_charge ? "checked" : ""}>
          Reverse charge (RCM) — you pay the GST, not the vendor
        </label>
      </div>

      <div class="table-preview compact-table invoice-lines">
        <table>
          <thead>
            <tr>
              <th>Description</th>
              ${itemSelectable ? `<th>Item</th>` : ""}
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
        <div data-row-rcm ${billFormHeader.is_reverse_charge ? "" : "hidden"}><span>GST payable under RCM (cash)</span><strong data-total-rcm>${formatCurrency(0)}</strong></div>
        <div data-row-tds ${billFormHeader.tds_section ? "" : "hidden"}><span>TDS deducted</span><strong data-total-tds>${formatCurrency(0)}</strong></div>
        <div class="invoice-grand" data-row-net-payable ${(billFormHeader.tds_section || billFormHeader.is_reverse_charge) ? "" : "hidden"}><span>Net payable to vendor</span><strong data-total-net-payable>${formatCurrency(0)}</strong></div>
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
      <p class="muted">${escapeHtml(b.is_inter_state ? "Inter-state supply (IGST input)" : "Intra-state supply (CGST + SGST input)")}${b.is_reverse_charge ? ` · <strong>Reverse charge</strong> — GST self-assessed, payable in cash` : ""}</p>
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
        ${b.is_reverse_charge ? `
        <div><span>GST payable under RCM (cash)</span><strong>${formatCurrency(b.rcm_payable || 0)}</strong></div>` : ""}
        ${Number(b.tds_amount || 0) > 0 ? `
        <div><span>TDS ${escapeHtml(b.tds_section || "")} @ ${escapeHtml(String(b.tds_rate || 0))}%</span><strong>${formatCurrency(b.tds_amount || 0)}</strong></div>` : ""}
        ${(b.is_reverse_charge || Number(b.tds_amount || 0) > 0) ? `
        <div class="invoice-grand"><span>Net payable to vendor</span><strong>${formatCurrency(b.net_payable || b.bill_total || 0)}</strong></div>` : ""}
      </div>
      ${b.deductee_pan_missing ? `<p class="muted">⚠ Vendor PAN missing — section 206AA prescribes deduction at 20%. Capture the PAN on the party record.</p>` : ""}
      ${b.notes ? `<p class="muted">${escapeHtml(b.notes)}</p>` : ""}
      ${String(b.status).toLowerCase() === "cancelled" ? `<p class="muted">Reversed${b.cancel_reason ? `: ${escapeHtml(b.cancel_reason)}` : ""}. Reversing journal entry #${escapeHtml(b.reversal_journal_entry_id || "")} posted.</p>` : ""}
    </div>
  `;
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: PURCHASE BILLS WORKSPACE
// API   : GET /api/v1/business/bills  POST /api/v1/business/bills
// NOTE  : loadBusinessBills, submitBill, renderBusinessPurchaseWorkspace
// ══════════════════════════════════════════════════════════════════════

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
    uqc: row.querySelector("input[name='uqc']")?.value || "",
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
  cnFormLines = [{ id: `cn-${++cnLineSeq}`, description: "", hsn_sac: "", uqc: "", quantity: "1", rate: "", gst_rate: "18" }];
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
  cnFormLines.push({ id: `cn-${++cnLineSeq}`, description: "", hsn_sac: "", uqc: "", quantity: "1", rate: "", gst_rate: "18" });
  rerenderCreditNoteIfActive();
  updateCnTotalsDisplay();
}

function removeCnLine(lineId) {
  syncCnFormFromDom();
  cnFormLines = cnFormLines.filter((l) => l.id !== lineId);
  if (cnFormLines.length === 0) {
    cnFormLines.push({ id: `cn-${++cnLineSeq}`, description: "", hsn_sac: "", uqc: "", quantity: "1", rate: "", gst_rate: "18" });
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
      uqc: String(l.uqc || "").trim().toUpperCase() || null,
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
      <td><input type="text" name="uqc" value="${escapeHtml(l.uqc || "")}" placeholder="UQC" style="width:70px;"></td>
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
              <th>Description</th><th>HSN/SAC</th><th>UQC</th><th>Qty</th><th>Rate</th><th>GST %</th>
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


// ══════════════════════════════════════════════════════════════════════
// SECTION: CREDIT NOTES WORKSPACE
// API   : GET /api/v1/business/credit-notes  POST /api/v1/business/credit-notes
// NOTE  : loadCreditNotes, submitCreditNote, renderBusinessCreditNoteWorkspace
// ══════════════════════════════════════════════════════════════════════

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


// ══════════════════════════════════════════════════════════════════════
// SECTION: DEBIT NOTES WORKSPACE
// API   : GET /api/v1/business/debit-notes  POST /api/v1/business/debit-notes
// NOTE  : loadDebitNotes, submitDebitNote, renderBusinessDebitNoteWorkspace
// ══════════════════════════════════════════════════════════════════════

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
let lastFinancialHealth = null;
let financialHealthLoadInFlight = false;

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


// ══════════════════════════════════════════════════════════════════════
// SECTION: ACCOUNT HELPERS + DATA HEALTH
// NOTE  : normalizeBusinessAccount, businessAccountsForSelection, renderBusinessDataHealthPanel
// ══════════════════════════════════════════════════════════════════════

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


// ══════════════════════════════════════════════════════════════════════
// SECTION: VOUCHER FORM HELPERS
// NOTE  : renderVoucherLineItem, updateVoucherBalance, addVoucherLine, clearVoucherForm
// ══════════════════════════════════════════════════════════════════════

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


// ══════════════════════════════════════════════════════════════════════
// SECTION: ACCOUNT LOADING + FINANCIAL HEALTH LOADER
// API   : GET /api/v1/accounting/accounts  GET /api/v1/business/financial-health
// NOTE  : loadBusinessAccounts, loadFinancialHealth, loadBusinessDashboardStats
// ══════════════════════════════════════════════════════════════════════

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
  if (!hasTrustedSession()) {
    return;
  }
  const appKey = "mitrabooks";
  businessDashboardLoadInFlight = true;
  let result;
  try {
    result = await apiRequest(appKey, "/api/v1/business/dashboard", { method: "GET" });
  } finally {
    businessDashboardLoadInFlight = false;
  }

  // A valid dashboard payload always carries the income block; guard against an
  // empty/partial body (e.g. a transient 0-byte response during a service-worker
  // swap) so it can't blank out good data we already rendered.
  const hasValidPayload = result.ok && result.payload && typeof result.payload === "object" && result.payload.income;

  if (hasValidPayload) {
    lastBusinessDashboardStats = result.payload;
    // Re-render whenever we're in the MitraBooks experience; renderDashboardPreview
    // itself routes to the right view (overview vs other workspaces).
    if (currentExperience === "mitrabooks") {
      dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig.mitrabooks);
    }
  } else if (!lastBusinessDashboardStats) {
    // Only surface "unavailable" when we have no prior good data — never clobber a
    // working dashboard with a transient failure.
    setLoginStatus(
      "warn",
      "Dashboard data unavailable",
      "Live dashboard figures could not be loaded; showing zeros until the ledger responds."
    );
  }

  renderJson(apiOutput, { dashboard: { ok: result.ok, hasData: !!lastBusinessDashboardStats } });
}

async function loadFinancialHealth() {
  const appKey = "mitrabooks";
  financialHealthLoadInFlight = true;
  let result;
  try {
    result = await apiRequest(appKey, "/api/v1/business/financial-health", { method: "GET" });
  } finally {
    financialHealthLoadInFlight = false;
  }

  // A valid payload always carries the kpis array; guard against an empty/partial
  // body so a transient failure can't blank out data we already rendered.
  const hasValidPayload = result.ok && result.payload && typeof result.payload === "object"
    && Array.isArray(result.payload.kpis);

  if (hasValidPayload) {
    lastFinancialHealth = result.payload;
    if (currentExperience === "mitrabooks" && activeBusinessWorkspace === "financial-health") {
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  } else if (!lastFinancialHealth) {
    setLoginStatus(
      "warn",
      "Financial Health unavailable",
      result.payload?.detail || "Live financial-health figures could not be loaded.",
    );
  }

  renderJson(apiOutput, { financialHealth: { ok: result.ok, hasData: !!lastFinancialHealth } });
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

// ══════════════════════════════════════════════════════════════════════
// SECTION: ACCOUNT SELECTOR COMPONENT
// NOTE  : renderAccountSelectorComponent, selectBusinessAccount — inline searchable dropdown
// ══════════════════════════════════════════════════════════════════════

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
  // Payment-allocation amount inputs: update state silently (no re-render) so
  // the field keeps focus while typing. The total is recomputed on next render.
  const allocLine = event.target.closest("[data-alloc-line]");
  if (allocLine) {
    setAllocationLineAmount(allocLine.getAttribute("data-alloc-line"), allocLine.value);
    return;
  }

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
  if (event.target && event.target.id === "business-voucher-party") {
    loadVoucherPartyOutstanding(event.target.value, event.target.getAttribute("data-voucher-type") || "");
    return;
  }
  const accountSelect = event.target.closest(".account-picker-select");
  if (!accountSelect) {
    return;
  }
  const fieldId = accountSelect.getAttribute("data-field-id");
  if (fieldId && accountSelect.value) {
    selectBusinessAccount(fieldId, accountSelect.value);
  }
});


// ══════════════════════════════════════════════════════════════════════
// SECTION: VOUCHERS — creation helpers (party / contra / journal)
// API   : POST /api/v1/business/vouchers/...
// NOTE  : createSimplePartyVoucher, createContraVoucher, createJournalVoucher
// ══════════════════════════════════════════════════════════════════════

async function loadVoucherPartyOutstanding(partyId, voucherType) {
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


// ══════════════════════════════════════════════════════════════════════
// SECTION: VOUCHERS — CRUD + list
// API   : GET /api/v1/business/vouchers  POST /api/v1/business/vouchers/{type}
// NOTE  : loadBusinessVouchers, reverseBusinessVoucher, openBusinessCreateVoucherDialog
// ══════════════════════════════════════════════════════════════════════

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
          <div id="business-voucher-outstanding" class="muted voucher-outstanding" data-voucher-type="${voucherType}"></div>
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
          <div id="business-voucher-outstanding" class="muted voucher-outstanding" data-voucher-type="${voucherType}"></div>
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


// ══════════════════════════════════════════════════════════════════════
// SECTION: AUDIT TRAIL
// API   : GET /api/v1/business/audit-log
// NOTE  : renderAuditEventsTable, loadAuditEvents, applyAuditFilters
// ══════════════════════════════════════════════════════════════════════

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


// ══════════════════════════════════════════════════════════════════════
// SECTION: GRUHAMITRA WORKSPACE
// API   : GET /api/v1/gruha/...
// NOTE  : renderGruhaDashboard, renderGruhaWorkspace
// ══════════════════════════════════════════════════════════════════════

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
    clearAllTokens();
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


// ══════════════════════════════════════════════════════════════════════
// SECTION: ACCOUNTING DRILLDOWN (shared MandirMitra + MitraBooks)
// API   : GET /api/v1/accounting/drilldown/...
// NOTE  : loadAccountingVoucherDetail, renderAccountingDrilldownPanel
// ══════════════════════════════════════════════════════════════════════

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


// ══════════════════════════════════════════════════════════════════════
// SECTION: MANDIR — account options / create forms / posting dialogs
// API   : POST /api/v1/mandir/... (receipts, seva bookings, expenses, contra)
// ══════════════════════════════════════════════════════════════════════

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


// ══════════════════════════════════════════════════════════════════════
// SECTION: MANDIR — dialogs: drilldown / verification / rejection / cancel
// NOTE  : openMandirVerificationDialog, openMandirCancelReceiptDialog, drillAccountingReport
// ══════════════════════════════════════════════════════════════════════

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
  let _loginInProgress = false;
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (_loginInProgress) return;
    _loginInProgress = true;
    try {
      await signInWithPassword();
    } finally {
      _loginInProgress = false;
    }
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

// Fired by api-client when silent token refresh fails — show clean login screen
window.addEventListener("auth-session-expired", () => {
  lastModuleContext = null;
  lastBusinessAccounts = [];
  lastBusinessParties = [];
  lastBusinessVouchers = [];
  lastAccountingDrilldown = null;
  clearAllTokens();
  if (loginPassword) loginPassword.value = "";
  dashboardPreview.innerHTML = "";
  renderModules();
  updateSessionUi();
  setLoginStatus("warn", "Session expired", "Your session has expired. Please sign in again.");
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

// ══════════════════════════════════════════════════════════════════════
// SECTION: EVENT HANDLERS — click / change / input / keydown
// NOTE  : Single delegated listener on dashboardPreview for all workspace actions
// ══════════════════════════════════════════════════════════════════════

dashboardPreview.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-platform-action], [data-mandir-action], [data-gruha-action], [data-accounting-action], [data-business-action], [data-coa-action]");
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
  } else if (businessAction === "settings-detail") {
    activeSettingsDetailId = button.getAttribute("data-settings-id") || "";
    dashboardPreview.innerHTML = renderBusinessWorkspace();
  } else if (businessAction === "settings-back") {
    activeSettingsDetailId = "";
    dashboardPreview.innerHTML = renderBusinessWorkspace();
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
  } else if (businessAction === "ca-doc-clear-filters") {
    caPracticeFilters = { status: "", client_name: "", assigned_to: "", priority: "" };
    loadCaPracticeDocuments();
  } else if (businessAction === "refresh-financial-health") {
    loadFinancialHealth();
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
  } else if (businessAction === "aging-kind") {
    setAgingKind(button.getAttribute("data-alloc-kind") || "receivable");
  } else if (businessAction === "alloc-kind") {
    setAllocationKind(button.getAttribute("data-alloc-kind") || "receivable");
  } else if (businessAction === "alloc-select-payment") {
    selectAllocationPayment(button.getAttribute("data-payment-id") || "");
  } else if (businessAction === "alloc-fifo") {
    applyFifoSuggestion();
  } else if (businessAction === "alloc-submit") {
    submitAllocation();
  } else if (businessAction === "export-report") {
    downloadBusinessReport(
      button.getAttribute("data-report-key") || "",
      button.getAttribute("data-report-format") || "csv",
      button.getAttribute("data-report-kind") || "",
    );
  } else if (businessAction === "print-report") {
    printBusinessReport();
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
  } else if (businessAction === "gst-preview") {
    previewGstSettlementFromInput();
  } else if (businessAction === "gst-post") {
    postGstSettlement();
  } else if (businessAction === "gstr3b-load") {
    previewGstr3bFromInput();
  } else if (businessAction === "gstr3b-download-json") {
    downloadGstr3bJson();
  } else if (businessAction === "gst-return-type") {
    const rt = button.getAttribute("data-return-type");
    gstReturnType = ["gstr1", "cmp08", "gstr4", "gstr2b"].includes(rt) ? rt : "gstr3b";
    rerenderBusinessReportsIfActive();
    refreshCurrentBusinessReport();
  } else if (businessAction === "gstr1-load") {
    previewGstr1FromInput();
  } else if (businessAction === "gstr1-download-json") {
    downloadGstr1Json();
  } else if (businessAction === "cmp08-load") {
    previewCmp08FromInput();
  } else if (businessAction === "cmp08-download-json") {
    downloadCmp08Json();
  } else if (businessAction === "cmp08-post") {
    postCmp08Liability();
  } else if (businessAction === "gstr4-load") {
    previewGstr4FromInput();
  } else if (businessAction === "gstr4-download-json") {
    downloadGstr4Json();
  } else if (businessAction === "gstr2b-reconcile") {
    reconcileGstr2b();
  } else if (businessAction === "tds-load") {
    previewTdsRegisterFromInput();
  } else if (businessAction === "bankrecon-load") {
    loadBankReconciliation(document.querySelector("[data-bankrecon-account]")?.value || "");
  } else if (businessAction === "bankrecon-upload") {
    uploadBankStatementFile();
  } else if (businessAction === "bankrecon-match") {
    confirmBankReconMatch(button.getAttribute("data-stmt-id") || "", button.getAttribute("data-line-id") || "");
  } else if (businessAction === "bankrecon-unmatch") {
    reverseBankReconMatch(button.getAttribute("data-match-id") || "");
  } else if (businessAction === "stmt-load") {
    loadPartyStatement();
  } else if (businessAction === "dunning-record") {
    recordDunningSent();
  } else if (businessAction === "dunning-copy") {
    copyDunningLetter();
  } else if (businessAction === "ob-template") {
    downloadObTemplate();
  } else if (businessAction === "ob-preview") {
    previewOpeningBalances();
  } else if (businessAction === "ob-post") {
    postOpeningBalances();
  } else if (businessAction === "ye-preview") {
    previewYearEnd();
  } else if (businessAction === "ye-post") {
    postYearEndClose();
  } else if (businessAction === "fa-toggle-form") {
    faFormOpen = !faFormOpen;
    rerenderBusinessReportsIfActive();
  } else if (businessAction === "fa-create") {
    createFixedAssetFromForm();
  } else if (businessAction === "dep-preview") {
    previewDepreciation();
  } else if (businessAction === "dep-post") {
    postDepreciationRun();
  } else if (businessAction === "dim-create") {
    createDimensionFromForm();
  } else if (businessAction === "dim-deactivate") {
    deactivateDimension(button.getAttribute("data-dimension-id") || "");
  } else if (businessAction === "dim-report-load") {
    loadDimensionReport();
  } else if (businessAction === "einv-download") {
    downloadInv01Json();
  } else if (businessAction === "einv-record") {
    recordEinvoiceIrn();
  } else if (businessAction === "item-create") {
    createInventoryItemFromForm();
  } else if (businessAction === "item-deactivate") {
    deactivateInventoryItem(button.getAttribute("data-item-id") || "");
  } else if (businessAction === "stock-register-load") {
    loadStockRegister();
  } else if (businessAction === "closing-stock-post") {
    postClosingStock();
  } else if (businessAction === "itc-preview") {
    previewItcReversalsFromInput();
  } else if (businessAction === "itc-reverse") {
    reverseItcForBill(button.getAttribute("data-bill-id") || "");
  } else if (businessAction === "itc-reclaim") {
    reclaimItcForBill(button.getAttribute("data-bill-id") || "");
  } else if (businessAction === "bill-mark-paid") {
    markBillPaidFull(button.getAttribute("data-bill-id") || "", button.getAttribute("data-bill-amount") || "0");
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

  // COA actions use their own attribute to avoid collisions with businessAction
  const coaAction = button.getAttribute("data-coa-action");
  if (coaAction === "toggle-add-form") {
    const form = document.getElementById("coa-add-form");
    if (form) form.style.display = form.style.display === "none" ? "" : "none";
  } else if (coaAction === "submit-add") {
    coaHandleAddSubmit();
  } else if (coaAction === "edit-name") {
    const row = button.closest("tr[data-coa-code]");
    if (row) coaEnterEditMode(row);
  } else if (coaAction === "save-name") {
    const row = button.closest("tr[data-coa-code]");
    if (row) coaHandleSaveName(row);
  } else if (coaAction === "cancel-name") {
    const row = button.closest("tr[data-coa-code]");
    if (row) coaExitEditMode(row);
  } else if (coaAction === "clear-filter") {
    coaTypeFilter = "";
    dashboardPreview.innerHTML = renderBusinessWorkspace();
  } else if (coaAction === "ca-invite-submit") {
    const form = button.closest("[data-ca-invite-form]");
    if (!form) return;
    const email = (form.querySelector("[name=email]")?.value || "").trim();
    const full_name = (form.querySelector("[name=full_name]")?.value || "").trim();
    if (!email || !full_name) {
      caInviteError = "Please fill in both name and email.";
      caInviteSuccess = "";
      dashboardPreview.innerHTML = renderBusinessWorkspace();
      return;
    }
    button.disabled = true;
    const result = await apiRequest("mitrabooks", "/api/v1/business/ca/invite", {
      method: "POST",
      body: JSON.stringify({ email, full_name }),
      timeoutMs: 30000,
    });
    button.disabled = false;
    if (result.ok) {
      const payload = result.payload || {};
      if (payload.email_sent) {
        const pwLine = payload.temp_password ? ` Temporary password: ${payload.temp_password}` : "";
        caInviteSuccess = `${payload.resent ? "Credentials resent" : "Credentials sent"} to ${email}.${pwLine}`;
        caInviteError = "";
      } else {
        caInviteSuccess = "";
        caInviteError = `CA account was provisioned, but the credential email was not delivered: ${payload.email_error || "SMTP delivery failed."}`;
      }
      form.reset();
      loadCaAccessUsers();
    } else {
      caInviteError = result.payload?.detail || `Failed to send invite (HTTP ${result.status}).`;
      caInviteSuccess = "";
      dashboardPreview.innerHTML = renderBusinessWorkspace();
    }
  } else if (coaAction === "ca-resend") {
    const email = button.getAttribute("data-ca-email");
    const full_name = button.getAttribute("data-ca-name") || "";
    if (!email) return;
    if (!confirm(`Resend login credentials to ${email}? A new temporary password will be generated and emailed.`)) return;
    button.disabled = true;
    const result = await apiRequest("mitrabooks", "/api/v1/business/ca/invite", {
      method: "POST",
      body: JSON.stringify({ email, full_name }),
      timeoutMs: 30000,
    });
    button.disabled = false;
    if (result.ok) {
      const payload = result.payload || {};
      if (payload.email_sent) {
        const pwLine = payload.temp_password ? ` Temporary password: ${payload.temp_password}` : "";
        caInviteSuccess = `New temporary password sent to ${email}.${pwLine}`;
        caInviteError = "";
      } else {
        caInviteSuccess = "";
        caInviteError = `Account refreshed but email delivery failed: ${payload.email_error || "SMTP not configured."}`;
      }
      loadCaAccessUsers();
    } else {
      alert(result.payload?.detail || `Resend failed (HTTP ${result.status}).`);
    }
  } else if (coaAction === "ca-delete") {
    const inviteId = button.getAttribute("data-ca-invite-id");
    const email = button.getAttribute("data-ca-email");
    if (!inviteId) return;
    if (!confirm(`Permanently delete the CA record for ${email}? This cannot be undone.`)) return;
    button.disabled = true;
    const result = await apiRequest("mitrabooks", `/api/v1/business/ca/invite/${encodeURIComponent(inviteId)}/cancel`, {
      method: "POST",
    });
    button.disabled = false;
    if (result.ok) {
      loadCaAccessUsers();
    } else {
      alert(result.payload?.detail || `Delete failed (HTTP ${result.status}).`);
    }
  } else if (coaAction === "ca-reinstate") {
    const userId = button.getAttribute("data-ca-user-id");
    const email = button.getAttribute("data-ca-email");
    if (!userId) return;
    if (!confirm(`Reinstate CA access for ${email}? They will be able to log in again.`)) return;
    button.disabled = true;
    const result = await apiRequest("mitrabooks", `/api/v1/business/ca/${encodeURIComponent(userId)}/reinstate`, {
      method: "POST",
    });
    button.disabled = false;
    if (result.ok) {
      loadCaAccessUsers();
    } else {
      alert(result.payload?.detail || `Reinstate failed (HTTP ${result.status}).`);
    }
  } else if (coaAction === "ca-revoke") {
    const userId = button.getAttribute("data-ca-user-id");
    const email = button.getAttribute("data-ca-email");
    if (!userId) return;
    if (!confirm(`Revoke CA access for ${email}? They will no longer be able to log in.`)) return;
    button.disabled = true;
    const result = await apiRequest("mitrabooks", `/api/v1/business/ca/${encodeURIComponent(userId)}/revoke`, {
      method: "POST",
    });
    button.disabled = false;
    if (result.ok) {
      loadCaAccessUsers();
    } else {
      alert(result.payload?.detail || `Revoke failed (HTTP ${result.status}).`);
    }
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
  if (event.target.id === "coa-type-filter") {
    coaTypeFilter = event.target.value;
    dashboardPreview.innerHTML = renderBusinessWorkspace();
    return;
  }
  if (!["is_inter_state", "is_reverse_charge", "tds_section", "tcs_section", "supply_type"].includes(event.target.name)) {
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
  const caFilterForm = event.target.closest("[data-ca-filter-form]");
  if (!mandirForm && !caDocumentForm && !caFilterForm) {
    return;
  }
  event.preventDefault();
  if (mandirForm) {
    submitMandirCreateForm(mandirForm);
  } else if (caDocumentForm) {
    createCaPracticeDocument(caDocumentForm);
  } else if (caFilterForm) {
    const formData = new FormData(caFilterForm);
    caPracticeFilters = {
      status: String(formData.get("status") || "").trim(),
      client_name: String(formData.get("client_name") || "").trim(),
      assigned_to: String(formData.get("assigned_to") || "").trim(),
      priority: String(formData.get("priority") || "").trim(),
    };
    loadCaPracticeDocuments();
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
    const pan = document.getElementById("business-party-pan")?.value || "";
    const city = document.getElementById("business-party-city")?.value || "";
    const state = document.getElementById("business-party-state")?.value || "";
    const pincode = document.getElementById("business-party-pincode")?.value || "";
    if (!name.trim()) {
      setLoginStatus("warn", "Party name required", "Enter a name for the party.");
      return;
    }

    createBusinessParty({ name, party_type, gstin, pan, city, state, pincode });
  });
}

if (businessPartyEditForm) {
  businessPartyEditForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const partyId = document.getElementById("business-party-edit-id")?.value || "";
    const name = document.getElementById("business-party-edit-name")?.value || "";
    const party_type = document.getElementById("business-party-edit-type")?.value || "customer";
    const gstin = document.getElementById("business-party-edit-gstin")?.value || "";
    const pan = document.getElementById("business-party-edit-pan")?.value || "";
    const city = document.getElementById("business-party-edit-city")?.value || "";
    const state = document.getElementById("business-party-edit-state")?.value || "";
    const pincode = document.getElementById("business-party-edit-pincode")?.value || "";
    if (!name.trim()) {
      setLoginStatus("warn", "Party name required", "Enter a name for the party.");
      return;
    }

    updateBusinessParty(partyId, { name, party_type, gstin, pan, city, state, pincode });
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
    if (orgType === "BUSINESS" || orgType === "PROFESSIONAL" || orgType === "CA_PRACTICE") {
      setLoginStatus("ok", selectorMeta.statusTitle, selectorMeta.statusCopy);
    } else {
      setLoginStatus("warn", selectorMeta.statusTitle, selectorMeta.statusCopy);
    }
    updateTrustedContextUi();
    if (currentExperience === "mitrabooks") {
      activeBusinessWorkspace = "overview";
      syncBusinessNavActiveState();
      dashboardPreview.innerHTML = renderDashboardPreview(experienceConfig.mitrabooks);
      if (orgType === "BUSINESS" && hasTrustedSession()) {
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

// ══════════════════════════════════════════════════════════════════════
// SECTION: BOOKS HEALTH WIDGET
// NOTE  : updateHealthWidget / refreshBooksHealthWidget / initializeHealthWidget
// ══════════════════════════════════════════════════════════════════════

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

