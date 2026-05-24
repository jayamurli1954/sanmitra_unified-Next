export const ACTIVE_TEMPLE_STORAGE_KEY = "active_temple_id_v1";
export const ACTIVE_TENANT_STORAGE_KEY = "active_tenant_id_v1";
export const ACTIVE_TEMPLE_EVENT = "active-temple-changed";
export const ACTIVE_TEMPLE_HEADER = "X-Temple-Id";
export const ACTIVE_APP_KEY_HEADER = "X-App-Key";
export const ACTIVE_TENANT_HEADER = "X-Tenant-ID";

function getAppKey() {
  return (process.env.REACT_APP_APP_KEY || "mandirmitra").trim();
}

export function getActiveTempleId() {
  const raw = localStorage.getItem(ACTIVE_TEMPLE_STORAGE_KEY);
  if (!raw) {
    return null;
  }
  const parsed = Number.parseInt(raw, 10);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

export function getActiveTenantId() {
  return (localStorage.getItem(ACTIVE_TENANT_STORAGE_KEY) || "").trim() || null;
}

export function setActiveTempleId(templeId, tenantId = null) {
  if (!templeId) {
    localStorage.removeItem(ACTIVE_TEMPLE_STORAGE_KEY);
    localStorage.removeItem(ACTIVE_TENANT_STORAGE_KEY);
    return;
  }
  localStorage.setItem(ACTIVE_TEMPLE_STORAGE_KEY, String(templeId));
  if (tenantId) {
    localStorage.setItem(ACTIVE_TENANT_STORAGE_KEY, String(tenantId));
  } else {
    localStorage.removeItem(ACTIVE_TENANT_STORAGE_KEY);
  }
}

export function emitActiveTempleChanged(templeId, tenantId = null) {
  window.dispatchEvent(new CustomEvent(ACTIVE_TEMPLE_EVENT, {
    detail: { templeId, tenantId },
  }));
}

export function buildActiveTempleHeaders(headers = {}) {
  const appKey = getAppKey();
  const templeId = getActiveTempleId();
  const tenantId = getActiveTenantId();
  const merged = { ...headers };

  if (appKey && !merged[ACTIVE_APP_KEY_HEADER]) {
    merged[ACTIVE_APP_KEY_HEADER] = appKey;
  }

  if (templeId && !merged[ACTIVE_TEMPLE_HEADER]) {
    merged[ACTIVE_TEMPLE_HEADER] = String(templeId);
  }

  if (tenantId && !merged[ACTIVE_TENANT_HEADER]) {
    merged[ACTIVE_TENANT_HEADER] = tenantId;
  }

  return merged;
}
