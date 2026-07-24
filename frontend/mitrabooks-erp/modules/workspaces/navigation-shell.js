// ====================================================================
// SECTION: NAVIGATION SHELL + MODULE BOOT RENDERERS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initNavigationShell(...).
// Business nav group config stays in modules/navigation.js.
// ====================================================================

import {
  businessNavigationGroups,
  businessNavigationItems,
} from "../navigation.js";

/** @type {Record<string, any> | null} */
let deps = null;

/** DOM refs bound once during init. */
let appRoot;
let appKeyLabel;
let topbarTitle;
let topbarSubtitle;
let topbarControlStrip;
let brandLogo;
let brandTitle;
let brandSubtitle;
let scopeTitle;
let scopeCopy;
let legacyTitle;
let legacyCopy;
let legacyVideo;
let legacyImage;
let dashboardPreview;
let nav;
let moduleList;

export function initNavigationShell(injected) {
  deps = injected;
  appRoot = injected.appRoot;
  appKeyLabel = injected.appKeyLabel;
  topbarTitle = injected.topbarTitle;
  topbarSubtitle = injected.topbarSubtitle;
  topbarControlStrip = injected.topbarControlStrip;
  brandLogo = injected.brandLogo;
  brandTitle = injected.brandTitle;
  brandSubtitle = injected.brandSubtitle;
  scopeTitle = injected.scopeTitle;
  scopeCopy = injected.scopeCopy;
  legacyTitle = injected.legacyTitle;
  legacyCopy = injected.legacyCopy;
  legacyVideo = injected.legacyVideo;
  legacyImage = injected.legacyImage;
  dashboardPreview = injected.dashboardPreview;
  nav = injected.nav;
  moduleList = injected.moduleList;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initNavigationShell() must be called before using navigation shell helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function getExperienceConfig() { return requireDeps().getExperienceConfig(); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getAppKey() { return requireDeps().getAppKey(); }
function getExperienceAppKeys() { return requireDeps().getExperienceAppKeys(); }
function isProductionShell(...args) { return requireDeps().isProductionShell(...args); }
function isMandirHost(...args) { return requireDeps().isMandirHost(...args); }
function updateSessionUi(...args) { return requireDeps().updateSessionUi(...args); }
function updateTrustedContextUi(...args) { return requireDeps().updateTrustedContextUi(...args); }
function getAccessToken(...args) { return requireDeps().getAccessToken(...args); }
function hasTrustedSession(...args) { return requireDeps().hasTrustedSession(...args); }
function activeOrgSelectorType(...args) { return requireDeps().activeOrgSelectorType(...args); }
function loadBusinessDashboardStats(...args) { return requireDeps().loadBusinessDashboardStats(...args); }
function renderDashboardPreview(...args) { return requireDeps().renderDashboardPreview(...args); }
function mandirWorkspaceFromModule(...args) { return requireDeps().mandirWorkspaceFromModule(...args); }
function navIconForMandirWorkspace(...args) { return requireDeps().navIconForMandirWorkspace(...args); }
function platformWorkspaceFromModule(...args) { return requireDeps().platformWorkspaceFromModule(...args); }
function syncMandirNavActiveState(...args) { return requireDeps().syncMandirNavActiveState(...args); }
function syncGruhaNavActiveState(...args) { return requireDeps().syncGruhaNavActiveState(...args); }
function syncPlatformNavActiveState(...args) { return requireDeps().syncPlatformNavActiveState(...args); }
function syncBusinessNavActiveState(...args) { return requireDeps().syncBusinessNavActiveState(...args); }
function loadModules(...args) { return requireDeps().loadModules(...args); }

export function renderModules(modules = getExperienceConfig()[getCurrentExperience()].modules, options = {}) {
  const config = getExperienceConfig()[getCurrentExperience()];
  const preview = options.preview !== false;
  appRoot.className = `app ${config.theme} ${isProductionShell() ? "production-shell" : ""} ${isMandirHost() ? "mandir-domain" : ""}`.trim();
  updateSessionUi();
  updateTrustedContextUi();
  if (appKeyLabel) {
    appKeyLabel.textContent = getExperienceAppKeys()[getCurrentExperience()] || getAppKey();
  }
  if (topbarTitle) {
    topbarTitle.textContent = getCurrentExperience() === "mandir" ? "MandirMitra Temple" : config.title;
  }
  if (topbarSubtitle) {
    topbarSubtitle.textContent = getCurrentExperience() === "mandir"
      ? "Temple / Trust Management & Accounting System"
      : config.subtitle;
  }
  if (topbarControlStrip) {
    topbarControlStrip.hidden = getCurrentExperience() !== "mitrabooks";
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
  if (hasTrustedSession() && getCurrentExperience() === "mitrabooks" && getActiveBusinessWorkspace() === "overview"
      && activeOrgSelectorType() === "BUSINESS") {
    loadBusinessDashboardStats();
  }

  const navItems = getCurrentExperience() === "mandir"
    ? mandirNavigationItems()
    : getCurrentExperience() === "gruha"
      ? gruhaNavigationItems()
      : getCurrentExperience() === "mitrabooks"
        ? businessNavigationItems()
        : getCurrentExperience() === "platform"
          ? platformNavigationItems(modules)
        : modules.map((module) => ({
        label: `${module.nav_group || "Module"}: ${module.display_name}`,
        module,
        workspace: mandirWorkspaceFromModule(module),
        }));

  if (getCurrentExperience() === "mitrabooks") {
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
    if (item.platformWorkspace) {
      link.dataset.platformWorkspace = item.platformWorkspace;
    }
    link.dataset.navIcon = item.icon || navIconForMandirWorkspace(mandirWorkspace);
    link.textContent = item.label;
    nav.appendChild(link);
  });
  }

  modules.forEach((module) => {
    const item = document.createElement("li");
    item.innerHTML = `
      <strong>${escapeHtml(module.display_name)}</strong>
      <span class="muted">${escapeHtml(module.module_key)} -> ${escapeHtml(module.frontend_path || "no frontend path yet")}</span>
      <span class="pill ${module.enabled ? "ok" : "warn"}">${module.enabled ? "enabled" : preview ? "preview only" : "available or planned"}</span>
    `;
    moduleList.appendChild(item);
  });
  syncMandirNavActiveState();
  syncGruhaNavActiveState();
  syncPlatformNavActiveState();
  syncBusinessNavActiveState();
}

export function mandirNavigationItems() {
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

export function gruhaNavigationItems() {
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

export function platformNavigationItems(modules = getExperienceConfig().platform.modules) {
  return modules.map((module) => ({
    label: `${module.nav_group || "Platform"}: ${module.display_name}`,
    platformWorkspace: platformWorkspaceFromModule(module),
    module,
  }));
}

export function legacyBusinessNavigationItems() {
  return [
    { label: "Dashboard", businessWorkspace: "overview", icon: "▦", module: { module_key: "business", frontend_path: "/business", enabled: true } },
    { label: "Parties", businessWorkspace: "parties", icon: "●", module: { module_key: "business", frontend_path: "/business/parties", enabled: true } },
    { label: "Vouchers", businessWorkspace: "vouchers", icon: "▤", module: { module_key: "business", frontend_path: "/business/vouchers", enabled: true } },
    { label: "Audit Trail", businessWorkspace: "audit", icon: "⏱", module: { module_key: "audit", frontend_path: "/audit", enabled: true } },
    { label: "Accounting", businessWorkspace: "accounting", icon: "▣", module: { module_key: "accounting", frontend_path: "/accounting", enabled: true } },
  ];
}

export async function loadAndRenderGroupedNav(appKey) {
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

export function renderGroupedNav(groups) {
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

export function renderGroupedNavFromItems(items) {
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

