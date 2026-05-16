const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const API_BASE_STORAGE_KEY = "sanmitra_frontend_api_base_url";
const ACCESS_TOKEN_STORAGE_KEY = "sanmitra_frontend_access_token";

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
  const response = await fetch(`${baseUrl}${normalizedPath}`, {
    ...options,
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
