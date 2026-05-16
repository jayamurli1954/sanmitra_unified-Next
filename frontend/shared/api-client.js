const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const API_BASE_STORAGE_KEY = "sanmitra_frontend_api_base_url";
const ACCESS_TOKEN_STORAGE_KEY = "sanmitra_frontend_access_token";
const REQUEST_TIMEOUT_MS = 5000;

export function getConfiguredApiBaseUrl() {
  const params = new URLSearchParams(window.location.search);
  const queryApi = String(params.get("api") || "").trim();
  if (queryApi) {
    localStorage.setItem(API_BASE_STORAGE_KEY, queryApi.replace(/\/+$/, ""));
    return queryApi.replace(/\/+$/, "");
  }

  return String(localStorage.getItem(API_BASE_STORAGE_KEY) || DEFAULT_API_BASE_URL).trim().replace(/\/+$/, "");
}

export function setConfiguredApiBaseUrl(value) {
  const normalized = String(value || "").trim().replace(/\/+$/, "");
  if (!normalized) {
    localStorage.removeItem(API_BASE_STORAGE_KEY);
    return DEFAULT_API_BASE_URL;
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
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(`${baseUrl}${normalizedPath}`, {
      ...options,
      signal: options.signal || controller.signal,
      headers: buildHeaders(appKey, options.headers || {}),
    });

    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
      ? await response.json()
      : await response.text();

    return {
      ok: response.ok,
      status: response.status,
      payload,
    };
  } catch (error) {
    const detail = error instanceof Error && error.name === "AbortError"
      ? `Request timed out after ${REQUEST_TIMEOUT_MS / 1000} seconds`
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
