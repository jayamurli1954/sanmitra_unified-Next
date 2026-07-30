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
  const costCentreAddonAvailable = button.getAttribute("data-cost-centre-addon-available") === "1";
  const manufacturingAddonAvailable = button.getAttribute("data-manufacturing-addon-available") === "1";
  // Enterprise add-on provisioning toggles — MitraBooks (business) tenants only.
  const isBusiness = String(organizationType || "").toUpperCase() === "BUSINESS";
  const enterpriseAddonToggles = isBusiness ? `
    <div class="enterprise-addon-toggles" style="margin-top:10px;border-top:1px solid var(--border,#333);padding-top:10px;display:grid;gap:8px;">
      <label class="checkbox-option">
        <input type="checkbox" id="entitlement-hr-addon" ${hrAddonAvailable ? "checked" : ""}>
        <span><strong>HR &amp; Payroll add-on</strong> (enterprise) — provision for this tenant</span>
      </label>
      <label class="checkbox-option">
        <input type="checkbox" id="entitlement-cost-centre-addon" ${costCentreAddonAvailable ? "checked" : ""}>
        <span><strong>Cost-Centre Accounting add-on</strong> (enterprise) — provision for this tenant</span>
      </label>
      <label class="checkbox-option">
        <input type="checkbox" id="entitlement-manufacturing-addon" ${manufacturingAddonAvailable ? "checked" : ""}>
        <span><strong>Manufacturing add-on</strong> (enterprise) — provision for this tenant</span>
      </label>
    </div>` : "";
  entitlementModules.innerHTML = availableModules.map((moduleKey) => `
    <label class="checkbox-option">
      <input type="checkbox" value="${escapeHtml(moduleKey)}" ${currentModules.has(moduleKey) ? "checked" : ""}>
      <span>${escapeHtml(moduleKey)}</span>
    </label>
  `).join("") + enterpriseAddonToggles;
  entitlementModules.dataset.hrInitial = hrAddonAvailable ? "1" : "0";
  entitlementModules.dataset.costCentreInitial = costCentreAddonAvailable ? "1" : "0";
  entitlementModules.dataset.manufacturingInitial = manufacturingAddonAvailable ? "1" : "0";

  entitlementDialog.showModal();
}

export async function submitTenantEntitlements() {
  const tenantId = entitlementTenantId.value;
  const subscriptionPlan = entitlementPlan.value;
  const tenantStatus = entitlementStatus.value;
  const currentTenantStatus = entitlementStatus.dataset.currentStatus || "active";
  const enabledModules = Array.from(entitlementModules.querySelectorAll('input[type="checkbox"][value]:checked'))
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

  // Provision / revoke enterprise add-ons if toggles changed (super_admin only).
  let hrResult = null;
  let costCentreResult = null;
  let manufacturingResult = null;
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
  const costCentreCheckbox = document.getElementById("entitlement-cost-centre-addon");
  if (costCentreCheckbox) {
    const wanted = !!costCentreCheckbox.checked;
    const initial = entitlementModules.dataset.costCentreInitial === "1";
    if (wanted !== initial) {
      costCentreResult = await apiRequest(getAppKey(), `/api/v1/platform-owner/tenants/${encodeURIComponent(tenantId)}/addon/cost-centre`, {
        method: "PUT",
        body: JSON.stringify({ available: wanted }),
      });
    }
  }
  const manufacturingCheckbox = document.getElementById("entitlement-manufacturing-addon");
  if (manufacturingCheckbox) {
    const wanted = !!manufacturingCheckbox.checked;
    const initial = entitlementModules.dataset.manufacturingInitial === "1";
    if (wanted !== initial) {
      manufacturingResult = await apiRequest(getAppKey(), `/api/v1/platform-owner/tenants/${encodeURIComponent(tenantId)}/addon/manufacturing`, {
        method: "PUT",
        body: JSON.stringify({ available: wanted }),
      });
    }
  }

  renderJson(apiOutput, {
    update_tenant_status: statusResult,
    update_tenant_entitlements: result,
    hr_addon: hrResult,
    cost_centre_addon: costCentreResult,
    manufacturing_addon: manufacturingResult,
  });
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

