// ====================================================================
// SECTION: ACCOUNT LOADING + DASHBOARD / MIS / DATA-HEALTH LOADERS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initAccountLoading(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastBusinessAccounts = [];
export let lastBusinessAccountsResult = null;
export let lastBusinessDashboardStats = null;
export let lastBusinessMisKpis = null;
export let lastBusinessDataHealth = null;
export let businessDashboardLoadInFlight = false;
export let businessMisLoadInFlight = false;
export let businessDataHealthLoadInFlight = false;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initAccountLoading(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initAccountLoading() must be called before using account loading helpers");
  }
  return deps;
}

function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function accountRowsFromPayload(payload) { return requireDeps().accountRowsFromPayload(payload); }
function loadModuleContextForAccounts() { return requireDeps().loadModuleContextForAccounts(); }
function isBusinessModuleEnabled(context) { return requireDeps().isBusinessModuleEnabled(context); }
function refreshVoucherAccountSelects() { return requireDeps().refreshVoucherAccountSelects(); }
function updateVoucherAccountsStatus() { return requireDeps().updateVoucherAccountsStatus(); }
function hasTrustedSession() { return requireDeps().hasTrustedSession(); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function getExperienceConfig() { return requireDeps().getExperienceConfig(); }
function renderDashboardPreview(config) { return requireDeps().renderDashboardPreview(config); }
function getApiOutput() { return requireDeps().getApiOutput(); }
function getDefaultMitraBooksLoginEmail() { return requireDeps().getDefaultMitraBooksLoginEmail(); }
function businessAccountsForSelection() { return requireDeps().businessAccountsForSelection(); }

export function setLastBusinessAccounts(value) {
  lastBusinessAccounts = Array.isArray(value) ? value : [];
}

export function setLastBusinessAccountsResult(value) {
  lastBusinessAccountsResult = value;
}

export function setLastBusinessDashboardStats(value) {
  lastBusinessDashboardStats = value;
}

export function setLastBusinessMisKpis(value) {
  lastBusinessMisKpis = value;
}

export function setLastBusinessDataHealth(value) {
  lastBusinessDataHealth = value;
}

export async function loadBusinessAccounts() {
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
          `Current tenant is ${context?.organization_type || "unknown"} (${context?.tenant_id || "unknown"}). Sign in as ${getDefaultMitraBooksLoginEmail()} for voucher posting.`
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

export async function loadBusinessDashboardStats() {
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
    if (getCurrentExperience() === "mitrabooks") {
      getDashboardPreview().innerHTML = renderDashboardPreview(getExperienceConfig().mitrabooks);
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

  renderJson(getApiOutput(), { dashboard: { ok: result.ok, hasData: !!lastBusinessDashboardStats } });
}

export async function loadBusinessMisKpis() {
  if (!hasTrustedSession()) {
    return;
  }
  const appKey = "mitrabooks";
  businessMisLoadInFlight = true;
  let result;
  try {
    result = await apiRequest(appKey, "/api/v1/business/mis/kpis", { method: "GET" });
  } finally {
    businessMisLoadInFlight = false;
  }

  const hasValidPayload = result.ok && result.payload && typeof result.payload === "object"
    && Array.isArray(result.payload.monthly_sales_purchase_trend);

  if (hasValidPayload) {
    lastBusinessMisKpis = result.payload;
    if (getCurrentExperience() === "mitrabooks") {
      getDashboardPreview().innerHTML = renderDashboardPreview(getExperienceConfig().mitrabooks);
    }
  } else if (!lastBusinessMisKpis) {
    setLoginStatus(
      "warn",
      "MIS KPIs unavailable",
      result.payload?.detail || "Source-backed MIS KPI contracts could not be loaded.",
    );
  }

  renderJson(getApiOutput(), { misKpis: { ok: result.ok, hasData: !!lastBusinessMisKpis } });
}

export async function loadBusinessDataHealth() {
  if (!hasTrustedSession()) {
    return;
  }
  businessDataHealthLoadInFlight = true;
  let result;
  try {
    result = await apiRequest("mitrabooks", "/api/v1/business/data-health", { method: "GET" });
  } finally {
    businessDataHealthLoadInFlight = false;
  }

  const hasValidPayload = result.ok && result.payload && typeof result.payload === "object"
    && Array.isArray(result.payload.rules);

  if (hasValidPayload) {
    lastBusinessDataHealth = result.payload;
    if (getCurrentExperience() === "mitrabooks") {
      getDashboardPreview().innerHTML = renderDashboardPreview(getExperienceConfig().mitrabooks);
    }
  } else if (!lastBusinessDataHealth) {
    setLoginStatus(
      "warn",
      "Data Health unavailable",
      result.payload?.detail || "Source-backed data-health rules could not be loaded.",
    );
  }

  renderJson(getApiOutput(), { dataHealth: { ok: result.ok, hasData: !!lastBusinessDataHealth } });
}

export function filterBusinessAccountsByQuery(query) {
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

