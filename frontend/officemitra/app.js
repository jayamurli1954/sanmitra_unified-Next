import { apiRequest, clearAccessToken, getAccessToken } from "../shared/api-client.js";
import {
  initOfficeAiWorkspace,
  loadOfficeAiWorkspace,
  renderOfficeAiWorkspace,
} from "../shared/office-ai-workspace.js?v=mis-narrative-1";

const APP_KEY = "officemitra";
const SESSION_KEY = "OFFICEMITRA_AUTH_SESSION";
const root = document.getElementById("officemitra-root");
const sessionLabel = document.getElementById("session-label");
const logoutBtn = document.getElementById("logout-btn");

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function readSessionUser() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    return parsed?.user || null;
  } catch (_err) {
    return null;
  }
}

function logout() {
  clearAccessToken();
  sessionStorage.removeItem(SESSION_KEY);
  window.location.assign("./login.html");
}

async function ensureSession() {
  if (!getAccessToken()) {
    logout();
    return false;
  }
  const result = await apiRequest(APP_KEY, "/api/v1/auth/validate", { method: "GET" });
  if (!result.ok) {
    logout();
    return false;
  }
  return true;
}

logoutBtn?.addEventListener("click", () => logout());

(async () => {
  if (!(await ensureSession())) return;

  const user = readSessionUser();
  if (sessionLabel) {
    sessionLabel.textContent = user?.email || user?.full_name || "Signed in";
  }

  initOfficeAiWorkspace({
    escapeHtml,
    apiRequest,
    dashboardPreview: root,
    appKey: APP_KEY,
  });

  if (root) {
    root.innerHTML = renderOfficeAiWorkspace();
  }
  await loadOfficeAiWorkspace();
})();
