// ====================================================================
// SECTION: MITRABOOKS SETTINGS WORKSPACE
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initSettingsWorkspace(...).
// ====================================================================

import { apiRequest } from "../../../shared/api-client.js";

export let activeSettingsDetailId = "";
export let lastBusinessAdminSettings = null;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initSettingsWorkspace(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initSettingsWorkspace() must be called before using settings workspace helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function setLoginStatus(kind, title, detail = "") { return requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function renderBusinessDataHealthPanel() { return requireDeps().renderBusinessDataHealthPanel(); }
function plannedOrgWorkspaceModel(orgType) { return requireDeps().plannedOrgWorkspaceModel(orgType); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function renderBusinessWorkspace() { return requireDeps().renderBusinessWorkspace(); }

export function setActiveSettingsDetailId(value) {
  activeSettingsDetailId = String(value || "");
}

export function setLastBusinessAdminSettings(value) {
  lastBusinessAdminSettings = value;
}

const MITRABOOKS_SETTINGS_GROUPS = [
  {
    title: "Core Settings",
      description: "Always visible for MitraBooks business tenants.",
      items: [
      { title: "Organization", status: "Implemented", detail: "Tenant-scoped legal name, trade name, tax IDs, contact details, financial year, currency, time zone, and logo settings save through MitraBooks admin settings.", visibility: "Owner, Admin, CA Partner" },
      { title: "Branches", status: "Implemented", detail: "Branch code, GST registration per branch, address, warehouse mapping, and cost centre mapping now save in tenant-scoped MitraBooks admin settings.", visibility: "Multi-location businesses" },
      { title: "Users & Roles", status: "Implemented", detail: "Tenant-scoped role templates for Owner, Admin, Accountant, Cashier, Auditor, and Viewer now save through MitraBooks admin settings.", visibility: "Owner, Admin" },
      { title: "Permissions", status: "Implemented", detail: "Tenant-scoped module and action permission templates for approvals, reports, banking, inventory, and settings now save through MitraBooks admin settings.", visibility: "Owner, Admin" },
      { title: "Chart of Accounts", status: "Implemented", detail: "Default business chart, protected system accounts, ledger drill-down, and opening balances through journal posting.", visibility: "Accounting users", workspace: "accounting" },
      { title: "Tax & Compliance", status: "Implemented", detail: "GST registration mode, GST reports, GSTR preparation, TDS/TCS sections, period locks, and reconciliation workflows.", visibility: "Accountant, CA", workspace: "gst-returns" },
      { title: "Voucher Configuration", status: "Implemented", detail: "Voucher prefixes, approval threshold, and default approver role now save in tenant-scoped MitraBooks admin settings, while posting workflows remain in the vouchers workspace.", visibility: "Owner, Admin, Accountant" },
      { title: "Security", status: "Implemented", detail: "MFA requirement, password policy floor, session timeout, concurrent-session rule, and login alert email now save in tenant-scoped MitraBooks admin settings.", visibility: "Owner, Admin" },
    ],
  },
  {
    title: "Module Settings",
    description: "Visible when the corresponding MitraBooks module or business mode is enabled.",
    items: [
      { title: "Invoice Settings", status: "Implemented", detail: "Sales invoice fields, numbering pattern, GST registration type, composition category, and inventory accounting toggle.", visibility: "Admin", workspace: "sales" },
      { title: "Inventory", status: "Partial", detail: "Item master and stock register exist. UOM, godowns, valuation policy, and stock approvals are planned.", visibility: "Inventory businesses", workspace: "reports" },
      { title: "Banking", status: "Partial", detail: "Manual bank reconciliation exists. Bank account setup, gateway mapping, and bank API sync are planned.", visibility: "Banking users", workspace: "bank-recon" },
      { title: "Financial Controls", status: "Implemented", detail: "Voucher lock date, backdated-entry approval, locked-period override policy, and period-close note now save in tenant-scoped MitraBooks admin settings.", visibility: "Owner, Auditor" },
      { title: "Templates", status: "Implemented", detail: "Invoice, receipt, payment voucher, statement, and report template choices with footer branding now save in tenant-scoped MitraBooks admin settings.", visibility: "Owner, Admin" },
      { title: "Notifications", status: "Implemented", detail: "Email, SMS, WhatsApp, due-date, approval, and compliance reminder rules now save in tenant-scoped MitraBooks admin settings.", visibility: "Owner, Admin" },
    ],
  },
  {
    title: "Professional Practice Settings",
    description: "For CA firms and bookkeepers handling many client companies from one login.",
    items: [
      { title: "Client Management", status: "Implemented", detail: "Tenant-scoped CA client records capture GSTIN/PAN, contact person, engagement type, notes, and active status through the CA Practice Portal.", visibility: "CA Partner, Practice Admin", workspace: "ca-access" },
      { title: "Multi-Company Dashboard", status: "Implemented", detail: "CA Practice Portal lists client books and supports quick company switching into the filtered review queue.", visibility: "CA Partner, Staff", workspace: "ca-access" },
      { title: "Client Access Control", status: "Implemented", detail: "Client records save scoped access levels such as view only, data entry, full access, and restricted filing visibility.", visibility: "CA Partner", workspace: "ca-access" },
      { title: "Compliance Tracking", status: "Implemented", detail: "CA client records plus document metadata track GST, TDS, income tax, audit, ROC, and bookkeeping compliance queues.", visibility: "CA Partner, Staff", workspace: "ca-access" },
      { title: "Work Assignment", status: "Implemented", detail: "Clients and CA document metadata both capture owner and assignee fields for practice workload routing.", visibility: "Practice Admin", workspace: "ca-access" },
    ],
  },
  {
    title: "Platform Settings",
    description: "Controlled settings for subscription, integrations, audit, and AI enablement.",
    items: [
      { title: "Subscription & Billing", status: "Implemented", detail: "Billing contacts, invoice delivery email, renewal mode, and payment provider preference now save in tenant-scoped MitraBooks admin settings.", visibility: "Owner, Platform Admin" },
      { title: "Integrations", status: "Implemented", detail: "Tenant-scoped integration shells now save payment gateway, GST portal, bank feed, WhatsApp, email, and document storage settings without exposing provider secrets to the frontend.", visibility: "Owner, Admin" },
      { title: "Audit & Logs", status: "Implemented", detail: "Party, voucher, account, document, and lifecycle events are visible through audit trail.", visibility: "Owner, Auditor", workspace: "audit" },
      { title: "AI Settings", status: "Implemented", detail: "Tenant-scoped AI/OCR controls now save review-first settings for OCR, categorization, reconciliation assistance, MIS, and forecasting. Auto-post to ledger remains disabled.", visibility: "Owner, Admin" },
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

const BUSINESS_ADMIN_SETTINGS_SECTION_KEYS = {
  "organization": "organization",
  "branches": "branches",
  "users-and-roles": "roles",
  "permissions": "permissions",
  "voucher-configuration": "voucher_configuration",
  "financial-controls": "financial_controls",
  "security": "security",
  "templates": "templates",
  "notifications": "notifications",
  "subscription-and-billing": "subscription_billing",
  "integrations": "integrations",
  "ai-settings": "ai_settings",
};

export function settingsItemId(item) {
  return String(item.title || "")
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function allMitraBooksSettingsItems() {
  return MITRABOOKS_SETTINGS_GROUPS.flatMap((group) =>
    group.items.map((item) => ({ ...item, groupTitle: group.title })),
  );
}

export function findMitraBooksSettingsItem(settingId) {
  return allMitraBooksSettingsItems().find((item) => settingsItemId(item) === settingId) || null;
}


export function businessAdminSettingsSectionKey(settingId) {
  return BUSINESS_ADMIN_SETTINGS_SECTION_KEYS[settingId] || "";
}

export function buildBusinessAdminSettingsPayload(source = {}) {
  return {
    organization: source.organization || {},
    branches: Array.isArray(source.branches) ? source.branches : [],
    roles: Array.isArray(source.roles) ? source.roles : [],
    permissions: source.permissions || { module_permissions: {}, action_permissions: {} },
    voucher_configuration: source.voucher_configuration || {},
    financial_controls: source.financial_controls || {},
    security: source.security || {},
    templates: source.templates || {},
    notifications: source.notifications || {},
    subscription_billing: source.subscription_billing || {},
    integrations: source.integrations || {},
    ai_settings: source.ai_settings || {},
    accounting_entity_id: "primary",
  };
}

export function settingsStatusClass(status) {
  const normalized = String(status || "").toLowerCase();
  if (normalized === "implemented") return "ok";
  if (normalized === "partial") return "warn";
  return "neutral";
}

export function renderMitraBooksSettingsCard(item) {
  const settingId = settingsItemId(item);
  const sectionKey = businessAdminSettingsSectionKey(settingId);
  const action = item.workspace
    ? `<button class="secondary" type="button" data-business-action="workspace-view" data-workspace-view="${escapeHtml(item.workspace)}">Open Related Area</button>`
    : sectionKey
      ? `<button class="secondary" type="button" data-business-action="settings-detail" data-settings-id="${escapeHtml(settingId)}">Open Setup</button>`
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

export function renderBusinessAdminSettingsEditor(item, sectionKey) {
  const sectionValue = lastBusinessAdminSettings?.[sectionKey];
  const prettyValue = JSON.stringify(
    sectionValue ?? buildBusinessAdminSettingsPayload()[sectionKey] ?? {},
    null,
    2,
  );
  return `
    <article class="settings-json-editor">
      <strong>Tenant-scoped setup</strong>
      <p>Edit the JSON for this settings section and save it to the current MitraBooks tenant.</p>
      <textarea class="json-textarea" data-settings-json="${escapeHtml(sectionKey)}" spellcheck="false">${escapeHtml(prettyValue)}</textarea>
      <div class="settings-detail-actions">
        <button class="primary" type="button" data-business-action="save-settings-section" data-settings-section="${escapeHtml(sectionKey)}">Save ${escapeHtml(item.title)}</button>
      </div>
    </article>
  `;
}

export function renderMitraBooksSettingsDetail() {
  const item = findMitraBooksSettingsItem(activeSettingsDetailId);
  if (!item) return "";
  const sectionKey = businessAdminSettingsSectionKey(activeSettingsDetailId);
  const isReady = String(item.status || "").toLowerCase() === "implemented";
  const action = item.workspace
    ? `<button class="primary" type="button" data-business-action="workspace-view" data-workspace-view="${escapeHtml(item.workspace)}">Open ${escapeHtml(item.title)}</button>`
    : sectionKey
      ? ""
      : `<button class="secondary" type="button" disabled>Backend contract pending</button>`;
  const evidence = item.workspace
    ? "Available through the linked MitraBooks workspace with existing tenant-scoped route checks."
    : sectionKey
      ? "Backed by the tenant-scoped MitraBooks admin settings API."
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
      ${sectionKey ? renderBusinessAdminSettingsEditor(item, sectionKey) : ""}
      <div class="settings-detail-actions">
        ${action}
        <button class="secondary" type="button" data-business-action="settings-back">Back to Settings</button>
      </div>
    </section>
  `;
}

export function renderMitraBooksSettingsWorkspace() {
  const detail = activeSettingsDetailId ? renderMitraBooksSettingsDetail() : "";
  const settingsHealthPanel = activeSettingsDetailId ? "" : renderBusinessDataHealthPanel();
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
      ${settingsHealthPanel}
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

export function renderProfessionalSuiteWorkspace() {
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


export async function loadBusinessAdminSettings() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/admin-settings", { method: "GET" });
  if (result.ok) {
    setLastBusinessAdminSettings(result.payload || buildBusinessAdminSettingsPayload());
  } else if (!lastBusinessAdminSettings) {
    setLastBusinessAdminSettings(buildBusinessAdminSettingsPayload());
    setLoginStatus("danger", "Unable to load admin settings", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  if (getCurrentExperience() === "mitrabooks" && getActiveBusinessWorkspace() === "settings") {
    getDashboardPreview().innerHTML = renderBusinessWorkspace();
  }
}

export async function saveBusinessAdminSettingsSection(sectionKey) {
  const editor = document.querySelector(`[data-settings-json="${sectionKey}"]`);
  if (!editor) return;
  let parsed = {};
  try {
    parsed = JSON.parse(editor.value || "{}");
  } catch (error) {
    setLoginStatus("warn", "Invalid settings JSON", error?.message || "Fix the JSON before saving.");
    return;
  }
  const payload = buildBusinessAdminSettingsPayload(lastBusinessAdminSettings || {});
  payload[sectionKey] = parsed;
  const result = await apiRequest("mitrabooks", "/api/v1/business/admin-settings", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  if (result.ok) {
    setLastBusinessAdminSettings(result.payload || payload);
    setLoginStatus("ok", "Settings saved", "The selected settings section was saved for the current MitraBooks tenant.");
    if (getCurrentExperience() === "mitrabooks" && getActiveBusinessWorkspace() === "settings") {
      getDashboardPreview().innerHTML = renderBusinessWorkspace();
    }
  } else {
    setLoginStatus("danger", "Save failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
}

