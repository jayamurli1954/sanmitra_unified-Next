// ====================================================================
// SECTION: CONTEXT + MANDIR LIST PATH HELPERS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initContextPathHelpers(...).
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

export function initContextPathHelpers(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initContextPathHelpers() must be called before using context/path helpers");
  }
  return deps;
}

function apiRequest(...args) { return requireDeps().apiRequest(...args); }
function loadModules(...args) { return requireDeps().loadModules(...args); }
function setLastBusinessPartiesResult(...args) { return requireDeps().setLastBusinessPartiesResult(...args); }
function setLastBusinessParties(...args) { return requireDeps().setLastBusinessParties(...args); }
function getLastModuleContext() { return requireDeps().getLastModuleContext(); }
function setLastModuleContext(value) { requireDeps().setLastModuleContext(value); }
function getMandirListState() { return requireDeps().getMandirListState(); }
function getMandirListPageSize() { return requireDeps().getMandirListPageSize(); }

export function isBusinessModuleEnabled(context) {
  const modules = Array.isArray(context?.enabled_modules) ? context.enabled_modules : [];
  return modules.some((module) => {
    const key = typeof module === "string" ? module : module?.module_key;
    return key === "business";
  });
}

export function enabledModuleKeys(context = null) {
  if (context == null) context = getLastModuleContext();
  const modules = Array.isArray(context?.enabled_modules) ? context.enabled_modules : [];
  return new Set(modules
    .map((module) => typeof module === "string" ? module : module?.module_key)
    .map((key) => String(key || "").trim().toLowerCase())
    .filter(Boolean));
}

export function isPlatformOwnerContext(context = null) {
  if (context == null) context = getLastModuleContext();
  const tenantId = String(context?.tenant_id || "").trim().toLowerCase();
  const role = String(context?.role || context?.user_role || "").trim().toLowerCase();
  const organizationType = String(context?.organization_type || "").trim().toUpperCase();
  return context?.is_platform_owner === true
    || role === "super_admin"
    || tenantId === "platform"
    || organizationType === "PLATFORM";
}

export function isBusinessTenantContext(context = null) {
  if (context == null) context = getLastModuleContext();
  const organizationType = String(context?.organization_type || "").trim().toUpperCase();
  return organizationType === "BUSINESS" && !isPlatformOwnerContext(context) && isBusinessModuleEnabled(context);
}

export async function loadBusinessPartiesForHealth() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/parties?offset=0&limit=20", { method: "GET" });
  setLastBusinessPartiesResult(result);
  if (result.ok) {
    setLastBusinessParties(Array.isArray(result.payload?.items) ? result.payload.items : Array.isArray(result.payload) ? result.payload : []);
  }
  return result;
}

export async function loadModuleContextForAccounts() {
  if (getLastModuleContext()) return getLastModuleContext();
  const result = await loadModules("mitrabooks");
  if (result.ok) {
    setLastModuleContext(result.payload);
  }
  return getLastModuleContext();
}

export function buildQueryString(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      query.set(key, String(value).trim());
    }
  });
  return query.toString();
}

export function mandirListPath(kind) {
  const state = getMandirListState()[kind] || {};
  const path = kind === "sevas" ? "/api/v1/sevas/bookings" : "/api/v1/donations";
  const query = buildQueryString({
    limit: getMandirListPageSize(),
    offset: state.offset || 0,
    q: state.q,
    from_date: state.from_date,
    to_date: state.to_date,
    payment_mode: kind === "donations" ? state.payment_mode : "",
    status: kind === "sevas" ? state.status : "",
  });
  return `${path}?${query}`;
}

export function mandirPublicPaymentsPath() {
  const state = getMandirListState().payments;
  const query = buildQueryString({
    limit: getMandirListPageSize(),
    offset: state.offset || 0,
    q: state.q,
    status: state.status || "pending",
    payment_type: state.payment_type,
  });
  return `/api/v1/public-payments?${query}`;
}

export function mandirPublicPaymentExceptionsPath() {
  const state = getMandirListState().exceptions;
  const query = buildQueryString({
    older_than_hours: 24,
    limit: getMandirListPageSize(),
    offset: state.offset || 0,
    q: state.q,
    reason: state.reason,
    status: state.status,
    payment_type: state.payment_type,
  });
  return `/api/v1/public-payments/exceptions?${query}`;
}

export function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}

