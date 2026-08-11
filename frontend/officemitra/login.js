import { apiRequest, clearAccessToken, getAccessToken, setAccessToken } from "../shared/api-client.js";

const APP_KEY = "officemitra";
const SESSION_KEY = "OFFICEMITRA_AUTH_SESSION";

const statusNode = document.getElementById("login-status");
const form = document.getElementById("login-form");
const emailInput = document.getElementById("login-email");
const passwordInput = document.getElementById("login-password");

function showStatus(message, tone = "ok") {
  statusNode.textContent = message;
  statusNode.className = `om-status ${tone === "err" ? "err" : "ok"}`;
}

function persistSession(payload) {
  setAccessToken(payload?.access_token || "");
  sessionStorage.setItem(SESSION_KEY, JSON.stringify({
    access_token: payload?.access_token || "",
    refresh_token: payload?.refresh_token || "",
    token_type: payload?.token_type || "bearer",
    user: payload?.user || null,
    saved_at: new Date().toISOString(),
  }));
}

async function hasValidSession() {
  if (!getAccessToken()) return false;
  const result = await apiRequest(APP_KEY, "/api/v1/auth/validate", { method: "GET" });
  if (result.ok) return true;
  clearAccessToken();
  sessionStorage.removeItem(SESSION_KEY);
  return false;
}

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  showStatus("Signing in…", "ok");
  try {
    const result = await apiRequest(APP_KEY, "/api/v1/auth/login", {
      method: "POST",
      timeoutMs: 20000,
      body: JSON.stringify({
        email: String(emailInput.value || "").trim(),
        password: String(passwordInput.value || ""),
      }),
    });
    if (!result.ok) {
      throw new Error(result.payload?.detail || result.payload?.message || `Login failed (${result.status})`);
    }
    persistSession(result.payload || {});
    window.location.assign("./index.html");
  } catch (err) {
    showStatus(err?.message || "Login failed", "err");
  }
});

(async () => {
  if (await hasValidSession()) {
    window.location.assign("./index.html");
  }
})();
