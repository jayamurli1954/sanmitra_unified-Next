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
  bindComplimentaryPlanHandlers();
}

// ── Complimentary plans (delegated: the panel is re-rendered on every refresh) ──
let complimentaryHandlersBound = false;

function showComplimentaryResult(html) {
  const box = document.getElementById("complimentary-plan-result");
  if (box) box.innerHTML = html;
}

function bindComplimentaryPlanHandlers() {
  if (complimentaryHandlersBound) return;
  complimentaryHandlersBound = true;

  document.addEventListener("submit", async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || form.id !== "complimentary-plan-form") return;
    event.preventDefault();
    const data = new FormData(form);
    const body = {
      email: String(data.get("email") || "").trim(),
      full_name: String(data.get("full_name") || "").trim() || null,
      organization_name: String(data.get("organization_name") || "").trim() || null,
      app_key: String(data.get("app_key") || "legalmitra"),
      tier: String(data.get("tier") || "pro"),
      days: Number(data.get("days") || 90),
      note: String(data.get("note") || "").trim() || null,
      send_email: data.get("send_email") === "on",
    };
    const submit = form.querySelector('button[type="submit"]');
    if (submit) submit.disabled = true;
    showComplimentaryResult('<p class="muted">Granting access…</p>');
    const result = await apiRequest(getAppKey(), "/api/v1/platform-owner/complimentary-plans", {
      method: "POST",
      body: JSON.stringify(body),
    });
    if (submit) submit.disabled = false;
    if (!result.ok) {
      const detail = result.payload?.detail || result.error || "Request failed";
      showComplimentaryResult(`<p class="pill warn">Could not grant access: ${escapeHtml(typeof detail === "string" ? detail : JSON.stringify(detail))}</p>`);
      return;
    }
    const grant = result.payload || {};
    const until = grant.subscription_expires_at ? new Date(grant.subscription_expires_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "";
    const lines = [
      `<strong>${escapeHtml(grant.email)}</strong> now has ${escapeHtml(grant.tier)} on ${escapeHtml(grant.app_key)} until ${escapeHtml(until)}.`,
    ];
    if (grant.account_created) {
      lines.push(`New account created. Login ID: <code>${escapeHtml(grant.email)}</code> · Temporary password: <code>${escapeHtml(grant.temporary_password || "")}</code> (shown once; they must change it at first login).`);
    }
    lines.push(grant.email_sent
      ? "Login details were emailed."
      : `Email not sent${grant.email_error ? ` (${escapeHtml(grant.email_error)})` : ""} — share the details yourself.`);
    form.reset();
    await loadPlatformOwnerDashboard();
    showComplimentaryResult(`<div class="pill ok" style="display:block;white-space:normal;padding:10px">${lines.join("<br>")}</div>`);
  });

  document.addEventListener("click", async (event) => {
    const button = event.target instanceof Element ? event.target.closest('[data-comp-action="revoke"]') : null;
    if (!button) return;
    const email = button.getAttribute("data-comp-email") || "";
    if (!email || !window.confirm(`End the complimentary plan for ${email} now? They will drop to the free plan.`)) return;
    button.disabled = true;
    const result = await apiRequest(getAppKey(), `/api/v1/platform-owner/complimentary-plans/${encodeURIComponent(email)}`, { method: "DELETE" });
    if (!result.ok) {
      button.disabled = false;
      const detail = result.payload?.detail || result.error || "Request failed";
      showComplimentaryResult(`<p class="pill warn">Could not end the plan: ${escapeHtml(String(detail))}</p>`);
      return;
    }
    await loadPlatformOwnerDashboard();
    showComplimentaryResult(`<p class="pill ok">Complimentary plan ended for ${escapeHtml(email)}.</p>`);
  });
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

