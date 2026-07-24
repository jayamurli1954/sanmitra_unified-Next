// ====================================================================
// SECTION: PLATFORM OWNER — onboarding + entitlements + workspace switch
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initPlatformOwnerOps(...).
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

/** DOM refs bound once during init. */
let apiOutput;
let dashboardPreview;
let entitlementDialog;
let entitlementTenantId;
let entitlementTenantLabel;
let entitlementPlan;
let entitlementStatus;
let entitlementModules;

export function initPlatformOwnerOps(injected) {
  deps = injected;
  apiOutput = injected.apiOutput;
  dashboardPreview = injected.dashboardPreview;
  entitlementDialog = injected.entitlementDialog;
  entitlementTenantId = injected.entitlementTenantId;
  entitlementTenantLabel = injected.entitlementTenantLabel;
  entitlementPlan = injected.entitlementPlan;
  entitlementStatus = injected.entitlementStatus;
  entitlementModules = injected.entitlementModules;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initPlatformOwnerOps() must be called before using platform-owner ops helpers");
  }
  return deps;
}

function apiRequest(...args) { return requireDeps().apiRequest(...args); }
function renderJson(...args) { return requireDeps().renderJson(...args); }
function escapeHtml(...args) { return requireDeps().escapeHtml(...args); }
function loadPlatformOwnerDashboard(...args) { return requireDeps().loadPlatformOwnerDashboard(...args); }
function syncPlatformNavActiveState(...args) { return requireDeps().syncPlatformNavActiveState(...args); }
function renderPlatformDashboard(...args) { return requireDeps().renderPlatformDashboard(...args); }
function emptyPlatformDashboardPayload(...args) { return requireDeps().emptyPlatformDashboardPayload(...args); }
function getAppKey() { return requireDeps().getAppKey(); }
function getEntitlementModulesByOrgType() { return requireDeps().getEntitlementModulesByOrgType(); }
function getLastPlatformOwnerDashboard() { return requireDeps().getLastPlatformOwnerDashboard(); }
function setCurrentExperience(value) { requireDeps().setCurrentExperience(value); }
function setActivePlatformWorkspace(value) { requireDeps().setActivePlatformWorkspace(value); }

export async function approveOnboardingRequest(requestId) {
  if (!requestId) {
    return;
  }
  const confirmed = window.confirm(`Approve onboarding request ${requestId}?`);
  if (!confirmed) {
    return;
  }

  const result = await apiRequest(getAppKey(), `/api/v1/onboarding-requests/${encodeURIComponent(requestId)}/approve`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  renderJson(apiOutput, { approve_onboarding_request: result });
  await loadPlatformOwnerDashboard();
}

export async function rejectOnboardingRequest(requestId) {
  if (!requestId) {
    return;
  }
  const reason = String(window.prompt(`Reason for rejecting ${requestId}`) || "").trim();
  if (reason.length < 3) {
    return;
  }

  const result = await apiRequest(getAppKey(), `/api/v1/onboarding-requests/${encodeURIComponent(requestId)}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
  renderJson(apiOutput, { reject_onboarding_request: result });
  await loadPlatformOwnerDashboard();
}

export function openTenantEntitlementsDialog(button) {
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
  const availableModules = getEntitlementModulesByOrgType()[organizationType] || Array.from(currentModules);

  entitlementTenantId.value = tenantId;
  entitlementTenantLabel.textContent = `${tenantLabel} (${organizationType || "tenant"})`;
  entitlementPlan.value = currentPlan;
  entitlementStatus.value = currentStatus;
  entitlementStatus.dataset.currentStatus = currentStatus;
  const hrAddonAvailable = button.getAttribute("data-hr-addon-available") === "1";
  // Show the HR add-on provisioning toggle only for MitraBooks (business) tenants.
  const isBusiness = String(organizationType || "").toUpperCase() === "BUSINESS";
  const hrToggle = isBusiness ? `
    <label class="checkbox-option" style="margin-top:10px;border-top:1px solid var(--border,#333);padding-top:10px;">
      <input type="checkbox" id="entitlement-hr-addon" ${hrAddonAvailable ? "checked" : ""}>
      <span><strong>HR &amp; Payroll add-on</strong> (enterprise) — provision for this tenant</span>
    </label>` : "";
  entitlementModules.innerHTML = availableModules.map((moduleKey) => `
    <label class="checkbox-option">
      <input type="checkbox" value="${escapeHtml(moduleKey)}" ${currentModules.has(moduleKey) ? "checked" : ""}>
      <span>${escapeHtml(moduleKey)}</span>
    </label>
  `).join("") + hrToggle;
  entitlementModules.dataset.hrInitial = hrAddonAvailable ? "1" : "0";

  entitlementDialog.showModal();
}

export async function submitTenantEntitlements() {
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
    getAppKey(),
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

  const result = await apiRequest(getAppKey(), `/api/v1/tenants/${encodeURIComponent(tenantId)}/entitlements`, {
    method: "PATCH",
    body: JSON.stringify({
      subscription_plan: subscriptionPlan,
      enabled_modules: enabledModules,
    }),
  });

  // Provision / revoke the HR add-on if its toggle changed (super_admin only).
  let hrResult = null;
  const hrCheckbox = document.getElementById("entitlement-hr-addon");
  if (hrCheckbox) {
    const hrWanted = !!hrCheckbox.checked;
    const hrInitial = entitlementModules.dataset.hrInitial === "1";
    if (hrWanted !== hrInitial) {
      hrResult = await apiRequest(getAppKey(), `/api/v1/platform-owner/tenants/${encodeURIComponent(tenantId)}/hr-addon`, {
        method: "PUT",
        body: JSON.stringify({ available: hrWanted }),
      });
    }
  }

  renderJson(apiOutput, { update_tenant_status: statusResult, update_tenant_entitlements: result, hr_addon: hrResult });
  entitlementDialog.close();
  await loadPlatformOwnerDashboard();
}

export async function setPlatformWorkspace(workspace) {
  setCurrentExperience("platform");
  setActivePlatformWorkspace(workspace || "dashboard");
  syncPlatformNavActiveState();
  dashboardPreview.innerHTML = renderPlatformDashboard(getLastPlatformOwnerDashboard() || emptyPlatformDashboardPayload());
  await loadPlatformOwnerDashboard();
}

