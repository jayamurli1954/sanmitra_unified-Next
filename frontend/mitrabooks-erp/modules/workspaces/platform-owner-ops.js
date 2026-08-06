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
let entitlementDisplayName;
let entitlementOrgType;
let entitlementAppKey;
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
  entitlementDisplayName = document.getElementById("entitlement-display-name");
  entitlementOrgType = document.getElementById("entitlement-org-type");
  entitlementAppKey = document.getElementById("entitlement-app-key");
  entitlementPlan = injected.entitlementPlan;
  entitlementStatus = injected.entitlementStatus;
  entitlementModules = injected.entitlementModules;
  if (entitlementOrgType && !entitlementOrgType.dataset.bound) {
    entitlementOrgType.dataset.bound = "1";
    entitlementOrgType.addEventListener("change", () => {
      const org = String(entitlementOrgType.value || "").toUpperCase();
      if (entitlementAppKey) {
        const defaults = {
          TEMPLE: "mandirmitra",
          HOUSING: "gruhamitra",
          LEGAL: "legalmitra",
          BUSINESS: "mitrabooks",
          PROFESSIONAL: "mitrabooks",
        };
        entitlementAppKey.value = defaults[org] || "mitrabooks";
      }
      renderEntitlementModules(org, new Set());
    });
  }
}

const DEFAULT_MODULES_BY_ORG = {
  TEMPLE: ["temple", "accounting", "audit", "office_ai"],
  HOUSING: ["housing", "accounting", "audit", "office_ai"],
  LEGAL: ["legal", "rag", "compliance", "audit", "office_ai"],
  BUSINESS: ["business", "accounting", "gst", "inventory", "audit", "office_ai"],
  PROFESSIONAL: ["professional", "accounting", "billing", "audit", "office_ai"],
};

function renderEntitlementModules(organizationType, currentModules) {
  const org = String(organizationType || "").toUpperCase();
  const availableModules = getEntitlementModulesByOrgType()[org]
    || DEFAULT_MODULES_BY_ORG[org]
    || Array.from(currentModules);
  const selected = currentModules.size
    ? currentModules
    : new Set(DEFAULT_MODULES_BY_ORG[org] || availableModules);
  const isBusiness = org === "BUSINESS";
  const hrAddonAvailable = entitlementModules.dataset.hrInitial === "1";
  const costCentreAddonAvailable = entitlementModules.dataset.costCentreInitial === "1";
  const manufacturingAddonAvailable = entitlementModules.dataset.manufacturingInitial === "1";
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
      <input type="checkbox" value="${escapeHtml(moduleKey)}" ${selected.has(moduleKey) ? "checked" : ""}>
      <span>${escapeHtml(moduleKey)}</span>
    </label>
  `).join("") + enterpriseAddonToggles;
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
  const organizationType = String(button.getAttribute("data-organization-type") || "BUSINESS").toUpperCase();
  const currentPlan = button.getAttribute("data-subscription-plan") || "free";
  const currentModules = new Set(
    String(button.getAttribute("data-enabled-modules") || "")
      .split(",")
      .map((item) => item.trim().toLowerCase())
      .filter(Boolean)
  );
  const currentAppKey = String(button.getAttribute("data-app-keys") || "")
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean)[0] || "";

  entitlementTenantId.value = tenantId;
  entitlementTenantLabel.textContent = `${tenantLabel} (${organizationType || "tenant"})`;
  if (entitlementDisplayName) {
    entitlementDisplayName.value = tenantLabel;
  }
  if (entitlementOrgType) {
    entitlementOrgType.value = organizationType;
  }
  if (entitlementAppKey) {
    const defaults = {
      TEMPLE: "mandirmitra",
      HOUSING: "gruhamitra",
      LEGAL: "legalmitra",
      BUSINESS: "mitrabooks",
      PROFESSIONAL: "mitrabooks",
    };
    entitlementAppKey.value = currentAppKey || defaults[organizationType] || "mitrabooks";
  }
  entitlementPlan.value = currentPlan;
  entitlementStatus.value = currentStatus;
  entitlementStatus.dataset.currentStatus = currentStatus;
  entitlementModules.dataset.hrInitial = button.getAttribute("data-hr-addon-available") === "1" ? "1" : "0";
  entitlementModules.dataset.costCentreInitial = button.getAttribute("data-cost-centre-addon-available") === "1" ? "1" : "0";
  entitlementModules.dataset.manufacturingInitial = button.getAttribute("data-manufacturing-addon-available") === "1" ? "1" : "0";
  renderEntitlementModules(organizationType, currentModules);

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
      display_name: entitlementDisplayName ? String(entitlementDisplayName.value || "").trim() : undefined,
      organization_type: entitlementOrgType ? String(entitlementOrgType.value || "").trim().toUpperCase() : undefined,
      app_keys: entitlementAppKey && entitlementAppKey.value
        ? [String(entitlementAppKey.value).trim().toLowerCase()]
        : undefined,
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

