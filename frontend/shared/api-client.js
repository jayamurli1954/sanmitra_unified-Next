const LOCAL_API_BASE_URL = "http://127.0.0.1:8000";
const API_BASE_STORAGE_KEY = "sanmitra_frontend_api_base_url";
const ACCESS_TOKEN_STORAGE_KEY = "sanmitra_frontend_access_token";
const REFRESH_TOKEN_STORAGE_KEY = "sanmitra_frontend_refresh_token";
const REQUEST_TIMEOUT_MS = 5000;

function normalizeApiBaseUrl(value) {
  return String(value || "").trim().replace(/\/+$/, "");
}

function isLocalFrontendHost() {
  const host = String(window.location.hostname || "").toLowerCase();
  return !host || host === "localhost" || host === "127.0.0.1" || host === "::1";
}

function getRuntimeApiBaseUrl() {
  const globalValue = normalizeApiBaseUrl(window.SANMITRA_API_BASE_URL);
  if (globalValue) return globalValue;

  if (isLocalFrontendHost()) return LOCAL_API_BASE_URL;

  const metaValue = normalizeApiBaseUrl(document.querySelector("meta[name='sanmitra-api-base-url']")?.content);
  if (metaValue) return metaValue;

  return normalizeApiBaseUrl(window.location.origin) || LOCAL_API_BASE_URL;
}

export function getConfiguredApiBaseUrl() {
  const params = new URLSearchParams(window.location.search);
  const queryApi = String(params.get("api") || "").trim();
  if (queryApi) {
    localStorage.setItem(API_BASE_STORAGE_KEY, normalizeApiBaseUrl(queryApi));
    return normalizeApiBaseUrl(queryApi);
  }

  const runtimeApi = getRuntimeApiBaseUrl();
  const storedApi = normalizeApiBaseUrl(localStorage.getItem(API_BASE_STORAGE_KEY));
  if (!storedApi) {
    return runtimeApi;
  }

  const isProductionProxy = !isLocalFrontendHost() && runtimeApi === "/api";
  const isExternalOverride = /^https?:\/\//i.test(storedApi);
  if (isProductionProxy && isExternalOverride) {
    localStorage.removeItem(API_BASE_STORAGE_KEY);
    return runtimeApi;
  }

  return storedApi;
}

function buildApiUrl(baseUrl, path) {
  const normalizedBase = normalizeApiBaseUrl(baseUrl);
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  if (normalizedBase === "/api" && normalizedPath.startsWith("/api/")) {
    return normalizedPath;
  }

  if (normalizedBase.endsWith("/api") && normalizedPath.startsWith("/api/")) {
    return `${normalizedBase.slice(0, -4)}${normalizedPath}`;
  }

  return `${normalizedBase}${normalizedPath}`;
}

export function setConfiguredApiBaseUrl(value) {
  const normalized = normalizeApiBaseUrl(value);
  if (!normalized) {
    localStorage.removeItem(API_BASE_STORAGE_KEY);
    return getRuntimeApiBaseUrl();
  }
  localStorage.setItem(API_BASE_STORAGE_KEY, normalized);
  return normalized;
}

export function getAccessToken() {
  return String(localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY) || "").trim();
}

export function setAccessToken(value) {
  const token = String(value || "").trim();
  if (!token) {
    localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
    return "";
  }
  localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
  return token;
}

export function clearAccessToken() {
  localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
}

export function getRefreshToken() {
  return String(localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY) || "").trim();
}

export function setRefreshToken(value) {
  const token = String(value || "").trim();
  if (!token) {
    localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
    return "";
  }
  localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, token);
  return token;
}

export function clearRefreshToken() {
  localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
}

export function clearAllTokens() {
  localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
  localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
}

// Singleton in-flight promise so concurrent 401s don't fire multiple refresh calls
let _refreshInFlight = null;

async function _attemptSilentRefresh(appKey) {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    window.dispatchEvent(new CustomEvent("auth-session-expired"));
    return false;
  }
  try {
    const baseUrl = getConfiguredApiBaseUrl();
    const url = buildApiUrl(baseUrl, "/api/v1/auth/refresh");
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-App-Key": appKey || "mitrabooks" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) {
      clearAllTokens();
      window.dispatchEvent(new CustomEvent("auth-session-expired"));
      return false;
    }
    const data = await response.json();
    if (data.access_token) setAccessToken(data.access_token);
    if (data.refresh_token) setRefreshToken(data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

function _silentRefresh(appKey) {
  if (!_refreshInFlight) {
    _refreshInFlight = _attemptSilentRefresh(appKey).finally(() => { _refreshInFlight = null; });
  }
  return _refreshInFlight;
}

export function buildHeaders(appKey, extraHeaders = {}) {
  const headers = {
    "Content-Type": "application/json",
    "X-App-Key": appKey,
    ...extraHeaders,
  };
  const token = getAccessToken();
  if (token && !headers.Authorization) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

export async function apiRequest(appKey, path, options = {}) {
  const baseUrl = getConfiguredApiBaseUrl();
  const requestUrl = buildApiUrl(baseUrl, path);
  const controller = new AbortController();
  const timeoutMs = Number(options.timeoutMs || REQUEST_TIMEOUT_MS);
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  const { timeoutMs: _timeoutMs, _isRetry, ...fetchOptions } = options;
  try {
    const response = await fetch(requestUrl, {
      ...fetchOptions,
      signal: fetchOptions.signal || controller.signal,
      headers: buildHeaders(appKey, fetchOptions.headers || {}),
    });

    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
      ? await response.json()
      : await response.text();

    // On 401: attempt a silent token refresh then replay the request once.
    // Skip for auth endpoints to avoid infinite loops.
    if (response.status === 401 && !_isRetry && !path.includes("/api/v1/auth/")) {
      window.clearTimeout(timeout);
      const refreshed = await _silentRefresh(appKey);
      if (refreshed) {
        return apiRequest(appKey, path, { ...options, _isRetry: true });
      }
      return { ok: false, status: 401, payload };
    }

    return {
      ok: response.ok,
      status: response.status,
      payload,
    };
  } catch (error) {
    const detail = error instanceof Error && error.name === "AbortError"
      ? `Request timed out after ${timeoutMs / 1000} seconds`
      : error instanceof Error ? error.message : "Network request failed";
    return {
      ok: false,
      status: 0,
      payload: {
        detail,
      },
    };
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function downloadApiFile(appKey, path, filename, options = {}) {
  const baseUrl = getConfiguredApiBaseUrl();
  const requestUrl = buildApiUrl(baseUrl, path);
  const controller = new AbortController();
  const timeoutMs = Number(options.timeoutMs || REQUEST_TIMEOUT_MS);
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  const { timeoutMs: _timeoutMs, ...fetchOptions } = options;
  try {
    const response = await fetch(requestUrl, {
      ...fetchOptions,
      method: fetchOptions.method || "GET",
      signal: fetchOptions.signal || controller.signal,
      headers: buildHeaders(appKey, fetchOptions.headers || {}),
    });

    if (!response.ok) {
      const contentType = response.headers.get("content-type") || "";
      const payload = contentType.includes("application/json")
        ? await response.json()
        : await response.text();
      return { ok: false, status: response.status, payload };
    }

    const blob = await response.blob();
    const objectUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = filename || "receipt.pdf";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(objectUrl);
    return { ok: true, status: response.status, payload: { filename: link.download } };
  } catch (error) {
    const detail = error instanceof Error && error.name === "AbortError"
      ? `Request timed out after ${timeoutMs / 1000} seconds`
      : error instanceof Error ? error.message : "File download failed";
    return {
      ok: false,
      status: 0,
      payload: { detail },
    };
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function fetchApiFileObjectUrl(appKey, path, options = {}) {
  const baseUrl = getConfiguredApiBaseUrl();
  const requestUrl = buildApiUrl(baseUrl, path);
  const controller = new AbortController();
  const timeoutMs = Number(options.timeoutMs || REQUEST_TIMEOUT_MS);
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  const { timeoutMs: _timeoutMs, ...fetchOptions } = options;
  try {
    const response = await fetch(requestUrl, {
      ...fetchOptions,
      method: fetchOptions.method || "GET",
      signal: fetchOptions.signal || controller.signal,
      headers: buildHeaders(appKey, fetchOptions.headers || {}),
    });

    if (!response.ok) {
      const contentType = response.headers.get("content-type") || "";
      const payload = contentType.includes("application/json")
        ? await response.json()
        : await response.text();
      return { ok: false, status: response.status, payload };
    }

    const blob = await response.blob();
    const objectUrl = window.URL.createObjectURL(blob);
    return {
      ok: true,
      status: response.status,
      payload: {
        object_url: objectUrl,
        content_type: blob.type || response.headers.get("content-type") || "application/octet-stream",
      },
    };
  } catch (error) {
    const detail = error instanceof Error && error.name === "AbortError"
      ? `Request timed out after ${timeoutMs / 1000} seconds`
      : error instanceof Error ? error.message : "File preview failed";
    return {
      ok: false,
      status: 0,
      payload: { detail },
    };
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function loadHealth(appKey) {
  return apiRequest(appKey, "/health", { method: "GET" });
}

export async function loadModules(appKey) {
  return apiRequest(appKey, "/api/v1/modules/me", { method: "GET" });
}

export function renderJson(target, value) {
  target.textContent = JSON.stringify(value, null, 2);
}

export function statusLabel(result) {
  if (!result) {
    return "Not checked";
  }
  if (result.ok) {
    return `HTTP ${result.status}`;
  }
  return `HTTP ${result.status}`;
}

export function moduleItemsFromPayload(payload) {
  if (!payload || typeof payload !== "object") {
    return [];
  }
  return [
    ...(Array.isArray(payload.enabled_modules) ? payload.enabled_modules : []),
    ...(Array.isArray(payload.available_modules) ? payload.available_modules : []),
  ];
}

export function moduleStateSummary(result) {
  if (!result) {
    return {
      tone: "",
      title: "Not checked",
      copy: "Run checks to compare local preview modules with the backend module registry.",
    };
  }

  if (result.ok) {
    const enabledCount = Array.isArray(result.payload?.enabled_modules) ? result.payload.enabled_modules.length : 0;
    const availableCount = Array.isArray(result.payload?.available_modules) ? result.payload.available_modules.length : 0;
    return {
      tone: "ok",
      title: "Backend module contract loaded",
      copy: `${enabledCount} enabled module(s) and ${availableCount} available module(s) returned for this tenant/app context.`,
    };
  }

  if (result.status === 0) {
    return {
      tone: "danger",
      title: "Backend not reachable",
      copy: "The shell is showing local preview modules because the configured API base URL did not respond.",
    };
  }

  if (result.status === 401) {
    return {
      tone: "warn",
      title: "Tenant session required",
      copy: "The shell is showing local preview modules until a valid tenant-scoped access token is provided.",
    };
  }

  if (result.status === 403) {
    return {
      tone: "danger",
      title: "Module access denied",
      copy: "The backend rejected this app/module context. Do not expose working navigation for denied modules.",
    };
  }

  if (result.status === 404) {
    return {
      tone: "danger",
      title: "Tenant not found",
      copy: "The token resolved to a tenant that the backend could not load. The shell remains in preview mode.",
    };
  }

  return {
    tone: "warn",
    title: `Module contract unavailable: HTTP ${result.status}`,
    copy: "The shell is showing local preview modules and preserving backend error details in the API response panel.",
  };
}

export function renderModuleState(target, result) {
  if (!target) {
    return;
  }

  const summary = moduleStateSummary(result);
  target.className = `module-state ${summary.tone}`.trim();
  target.innerHTML = "";

  const title = document.createElement("strong");
  title.textContent = summary.title;

  const copy = document.createElement("span");
  copy.textContent = summary.copy;

  target.append(title, copy);
}
