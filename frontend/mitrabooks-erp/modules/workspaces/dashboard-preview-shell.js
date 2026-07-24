// ====================================================================
// SECTION: PLATFORM DASHBOARD + DASHBOARD PREVIEW SHELL
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initDashboardPreviewShell(...).
// Shared formatCurrency / formatCountLabel remain in app.js.
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

export function initDashboardPreviewShell(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initDashboardPreviewShell() must be called before using dashboard preview helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function formatCountMap(value) { return requireDeps().formatCountMap(value); }
function renderStatCards(stats) { return requireDeps().renderStatCards(stats); }
function renderActivity(items) { return requireDeps().renderActivity(items); }
function renderPlatformTable(...args) { return requireDeps().renderPlatformTable(...args); }
function renderPendingApprovalsTable(rows) { return requireDeps().renderPendingApprovalsTable(rows); }
function getActivePlatformWorkspace() { return requireDeps().getActivePlatformWorkspace(); }
function getLastPlatformOwnerDashboard() { return requireDeps().getLastPlatformOwnerDashboard(); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getLastGruhaData() { return requireDeps().getLastGruhaData(); }
function getLastBusinessDashboardStats() { return requireDeps().getLastBusinessDashboardStats(); }
function activeOrgSelectorType(...args) { return requireDeps().activeOrgSelectorType(...args); }
function renderGruhaDashboard(...args) { return requireDeps().renderGruhaDashboard(...args); }
function renderBusinessWorkspace(...args) { return requireDeps().renderBusinessWorkspace(...args); }
function renderSelectedOrgWorkspace(...args) { return requireDeps().renderSelectedOrgWorkspace(...args); }
function renderBusinessExecutiveDashboard(...args) { return requireDeps().renderBusinessExecutiveDashboard(...args); }

export function renderRecentTenantsTable(rows) {
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
                    data-hr-addon-available="${row.hr_addon_available ? "1" : "0"}"
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

export function renderPlatformRecentOnboardingTable(rows) {
  return renderPlatformTable(rows, [
    { label: "Request", value: (row) => row.request_id || row.id || "" },
    { label: "App", value: (row) => row.app_key || "" },
    { label: "Status", value: (row) => row.status || "" },
    { label: "Payment", value: (row) => row.payment_status || "" },
    { label: "Documents", value: (row) => row.document_verification_status || "" },
    { label: "Admin Email", value: (row) => row.admin_email || "" },
  ], "No onboarding requests returned.");
}

export function renderPlatformSubscriptionsTable(rows) {
  return renderPlatformTable(rows, [
    { label: "Tenant / Payer", value: (row) => row.display_name || row.payer_email || row.tenant_id || "" },
    { label: "Product", value: (row) => row.app_key || (Array.isArray(row.app_keys) ? row.app_keys.join(", ") : "") },
    { label: "Plan", value: (row) => row.subscription_plan || "" },
    { label: "Status", value: (row) => row.subscription_status || row.status || "" },
    { label: "Modules / Cycle", value: (row) => Array.isArray(row.enabled_modules) ? row.enabled_modules.join(", ") : (row.billing_cycle || "") },
  ], "No subscription records returned.");
}

export function emptyPlatformDashboardPayload() {
  return {
    summary: {
      onboarding: { by_status: { pending: 0, payment_pending: 0, payment_received: 0, under_review: 0, approved: 0, rejected: 0 } },
      tenants: { by_status: { active: 0, inactive: 0 } },
      subscriptions: { by_plan: {} },
    },
    app_status: [
      { app_key: "legalmitra", onboarding: { pending: 0 }, tenant_count: 0 },
      { app_key: "mandirmitra", onboarding: { pending: 0 }, tenant_count: 0 },
      { app_key: "gruhamitra", onboarding: { pending: 0 }, tenant_count: 0 },
      { app_key: "mitrabooks", onboarding: { pending: 0 }, tenant_count: 0 },
    ],
    module_status: [],
    pending_approvals: [],
    recent_onboarding: [],
    recent_tenants: [],
    subscription_records: [],
  };
}

export function renderPlatformDashboard(payload) {
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
  const recentOnboarding = Array.isArray(payload?.recent_onboarding_requests)
    ? payload.recent_onboarding_requests
    : (Array.isArray(payload?.recent_onboarding) ? payload.recent_onboarding : []);
  const recentTenants = Array.isArray(payload?.recent_tenants) ? payload.recent_tenants : [];
  const subscriptionRecords = Array.isArray(payload?.subscription_records) ? payload.subscription_records : recentTenants;
  const workspace = getActivePlatformWorkspace() || "dashboard";

  if (workspace === "onboarding") {
    return `
      <div class="legacy-dashboard platform-dashboard">
        <div class="preview-heading">
          <div>
            <h3>Onboarding Requests</h3>
            <p>Review product onboarding requests, payment status, and document verification state.</p>
          </div>
          <span class="pill ok">super admin</span>
        </div>
        <article>
          <h4>Pending Review</h4>
          ${renderPendingApprovalsTable(pendingApprovals)}
        </article>
        <article>
          <h4>Recent Onboarding Requests</h4>
          ${renderPlatformRecentOnboardingTable(recentOnboarding)}
        </article>
      </div>
    `;
  }

  if (workspace === "tenants") {
    return `
      <div class="legacy-dashboard platform-dashboard">
        <div class="preview-heading">
          <div>
            <h3>Tenant Status</h3>
            <p>Inspect active and inactive tenants across LegalMitra, MandirMitra, GruhaMitra, and MitraBooks.</p>
          </div>
          <span class="pill ok">super admin</span>
        </div>
        <div class="metric-grid three">${renderStatCards([
          ["Active Tenants", active, "currently enabled"],
          ["Inactive Tenants", inactive, "needs review"],
          ["Tracked Apps", appStatus.length, "product contexts"],
        ])}</div>
        <article>
          <h4>Recent Tenants</h4>
          ${renderRecentTenantsTable(recentTenants)}
        </article>
      </div>
    `;
  }

  if (workspace === "subscriptions") {
    return `
      <div class="legacy-dashboard platform-dashboard">
        <div class="preview-heading">
          <div>
            <h3>Subscriptions</h3>
            <p>Check plan, subscription status, and enabled modules for tenant accounts.</p>
          </div>
          <span class="pill ok">super admin</span>
        </div>
        <div class="metric-grid two">${renderStatCards([
          ["Subscription Plans", planCount, formatCountMap(subscriptions.by_plan)],
          ["Subscription Records", subscriptionRecords.length, "tenants and paid billing records"],
        ])}</div>
        <article>
          <h4>Tenant Subscriptions</h4>
          ${renderPlatformSubscriptionsTable(subscriptionRecords)}
        </article>
      </div>
    `;
  }

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

export function renderDashboardPreview(config) {
  const dashboard = config.dashboard;
  if (!dashboard) {
    return "";
  }

  if (dashboard.type === "platform") {
    return renderPlatformDashboard(getLastPlatformOwnerDashboard() || emptyPlatformDashboardPayload());
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
    return renderGruhaDashboard(config, getLastGruhaData());
  }

  if (dashboard.type === "business" || getCurrentExperience() === "mitrabooks") {
    if (getActiveBusinessWorkspace() !== "overview") {
      return renderBusinessWorkspace();
    }
    if (activeOrgSelectorType() !== "BUSINESS") {
      return renderSelectedOrgWorkspace();
    }
    const ds = getLastBusinessDashboardStats() || {};
    const cashMetric = formatCurrency(Number(ds.cash_and_bank || 0));
    const recvMetric = formatCurrency(Number(ds.receivables || 0));
    const payMetric = formatCurrency(Number(ds.payables || 0));
    const gstMetric = ds.gst?.status || "—";
    return `
      <div class="business-dashboard-clean">
        ${renderBusinessExecutiveDashboard()}

        <div class="business-quick-actions-clean">
          <button class="quick-action-btn" type="button" data-business-action="open-create-voucher" title="Post a journal entry" aria-keyshortcuts="Control+Alt+V">
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

