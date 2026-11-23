// ====================================================================
// SECTION: AI ASSISTANT CONNECTIONS (MCP access tokens)
// Lets a user create, list and revoke read-only personal access tokens for
// connecting Claude, ChatGPT, Cursor, Gemini CLI, Antigravity or any other
// MCP client to their MitraBooks books.
// API: /api/v1/mcp/tokens (GET, POST, DELETE /{id}); MCP endpoint /api/v1/mcp.
// Self-contained: renders into #ai-connections-panel and handles its own
// [data-ai-connect-action] clicks via one delegated listener (no inline handlers).
// ====================================================================

import { apiRequest, getConfiguredApiBaseUrl } from "../../../shared/api-client.js";

const APP_KEY = "mitrabooks";
const PANEL_ID = "ai-connections-panel";
const EXPIRY_OPTIONS = [30, 90, 180, 365];

const state = {
  tokens: [],
  loaded: false,
  loading: false,
  busy: false,
  error: "",
  newToken: null, // { name, token } — shown once, never stored
};

function esc(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function mcpUrl() {
  return `${String(getConfiguredApiBaseUrl() || "").replace(/\/+$/, "")}/api/v1/mcp`;
}

function fmtDate(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
}

function tokenStatus(token) {
  if (token.revoked_at) return { label: "Revoked", cls: "warn" };
  if (token.expires_at && new Date(token.expires_at) <= new Date()) return { label: "Expired", cls: "warn" };
  return { label: "Active", cls: "ok" };
}

function detailText(payload, fallback) {
  const detail = payload && typeof payload === "object" ? payload.detail : payload;
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg || "").filter(Boolean).join("; ") || fallback;
  return fallback;
}

function rerender() {
  const panel = document.getElementById(PANEL_ID);
  if (panel) panel.innerHTML = renderPanelBody();
}

async function loadTokens() {
  if (state.loading) return;
  state.loading = true;
  state.error = "";
  rerender();
  const result = await apiRequest(APP_KEY, "/api/v1/mcp/tokens");
  state.loading = false;
  state.loaded = true;
  if (result.ok) {
    state.tokens = Array.isArray(result.payload?.tokens) ? result.payload.tokens : [];
  } else {
    state.error = detailText(result.payload, "Could not load AI access tokens.");
  }
  rerender();
}

async function createToken() {
  const nameInput = document.getElementById("ai-connect-token-name");
  const expirySelect = document.getElementById("ai-connect-token-expiry");
  const name = String(nameInput?.value || "").trim();
  if (!name) {
    state.error = "Give the token a name, e.g. \"Claude on my laptop\".";
    rerender();
    return;
  }
  state.busy = true;
  state.error = "";
  rerender();
  const result = await apiRequest(APP_KEY, "/api/v1/mcp/tokens", {
    method: "POST",
    body: JSON.stringify({ name, expires_in_days: Number(expirySelect?.value || 90) }),
  });
  state.busy = false;
  if (result.ok) {
    state.newToken = { name, token: result.payload?.token || "" };
    await loadTokens();
  } else {
    state.error = detailText(result.payload, "Could not create the token.");
    rerender();
  }
}

async function revokeToken(tokenId, name) {
  if (!tokenId) return;
  // eslint-disable-next-line no-alert
  if (!window.confirm(`Revoke "${name}"? Any AI assistant using it loses access immediately.`)) return;
  state.busy = true;
  rerender();
  const result = await apiRequest(APP_KEY, `/api/v1/mcp/tokens/${encodeURIComponent(tokenId)}`, { method: "DELETE" });
  state.busy = false;
  if (!result.ok) state.error = detailText(result.payload, "Could not revoke the token.");
  await loadTokens();
}

async function copyText(value, button) {
  try {
    await navigator.clipboard.writeText(value);
    if (button) {
      const original = button.textContent;
      button.textContent = "Copied";
      window.setTimeout(() => { button.textContent = original; }, 1500);
    }
  } catch {
    // Clipboard blocked: the value is visible on screen to copy by hand.
  }
}

function renderNewToken() {
  if (!state.newToken) return "";
  return `
    <div class="settings-boundary-note" role="status">
      <strong>Copy this token now — it will not be shown again.</strong>
      <p>Token for “${esc(state.newToken.name)}”:</p>
      <code class="ai-connect-secret" style="display:block;word-break:break-all;padding:8px;margin:6px 0">${esc(state.newToken.token)}</code>
      <button class="primary" type="button" data-ai-connect-action="copy-token">Copy token</button>
      <button class="secondary" type="button" data-ai-connect-action="dismiss-token">I have saved it</button>
    </div>
  `;
}

function renderTokenRows() {
  if (state.loading && !state.loaded) return `<p>Loading tokens…</p>`;
  if (!state.tokens.length) return `<p>No tokens yet. Create one to connect an AI assistant.</p>`;
  return `
    <table class="data-table">
      <thead><tr><th>Name</th><th>Token</th><th>Created</th><th>Expires</th><th>Last used</th><th>Status</th><th></th></tr></thead>
      <tbody>
        ${state.tokens.map((t) => {
          const status = tokenStatus(t);
          const canRevoke = status.label === "Active";
          return `
            <tr>
              <td>${esc(t.name)}</td>
              <td><code>${esc(t.prefix)}…</code></td>
              <td>${esc(fmtDate(t.created_at))}</td>
              <td>${esc(fmtDate(t.expires_at))}</td>
              <td>${esc(fmtDate(t.last_used_at))}</td>
              <td><span class="pill ${status.cls}">${status.label}</span></td>
              <td>${canRevoke ? `<button class="secondary" type="button" data-ai-connect-action="revoke" data-token-id="${esc(t.token_id)}" data-token-name="${esc(t.name)}" ${state.busy ? "disabled" : ""}>Revoke</button>` : ""}</td>
            </tr>`;
        }).join("")}
      </tbody>
    </table>
  `;
}

function renderPanelBody() {
  const url = mcpUrl();
  return `
    <div class="settings-detail-grid">
      <article>
        <strong>What this is</strong>
        <p>Connect an AI assistant to your books so you can ask for your trial balance, GST returns, aging, bank reconciliation and health checks in plain language. Access is <strong>read-only</strong>: the assistant cannot post, edit or delete anything, and it sees only what your own login can see.</p>
      </article>
      <article>
        <strong>Server URL</strong>
        <p><code style="word-break:break-all">${esc(url)}</code></p>
        <button class="secondary" type="button" data-ai-connect-action="copy-url">Copy URL</button>
      </article>
      <article>
        <strong>How to connect</strong>
        <p>Add a remote MCP server (Streamable HTTP) with the URL above and the header <code>Authorization: Bearer &lt;your token&gt;</code>. Works with Claude Code, Claude Desktop, Cursor, VS Code, Gemini CLI, Antigravity and other MCP clients.</p>
      </article>
    </div>
    ${state.error ? `<p class="pill warn" role="alert">${esc(state.error)}</p>` : ""}
    ${renderNewToken()}
    <div class="settings-section-heading"><h5>Create a token</h5></div>
    <div class="form-grid" style="display:flex;gap:8px;flex-wrap:wrap;align-items:end">
      <label>Name
        <input id="ai-connect-token-name" type="text" maxlength="80" placeholder="e.g. Claude on my laptop" />
      </label>
      <label>Expires after
        <select id="ai-connect-token-expiry">
          ${EXPIRY_OPTIONS.map((d) => `<option value="${d}" ${d === 90 ? "selected" : ""}>${d} days</option>`).join("")}
        </select>
      </label>
      <button class="primary" type="button" data-ai-connect-action="create" ${state.busy ? "disabled" : ""}>Create token</button>
    </div>
    <div class="settings-section-heading"><h5>Your tokens</h5></div>
    ${renderTokenRows()}
  `;
}

/** Panel HTML for the settings detail view. Loads tokens on first render. */
export function renderAiConnectionsPanel() {
  if (!state.loaded && !state.loading) {
    window.setTimeout(loadTokens, 0);
  }
  return `<div id="${PANEL_ID}">${renderPanelBody()}</div>`;
}

/** Forget the shown-once token and cached list (e.g. on logout or tenant switch). */
export function resetAiConnectionsState() {
  state.tokens = [];
  state.loaded = false;
  state.loading = false;
  state.busy = false;
  state.error = "";
  state.newToken = null;
}

let listenerInstalled = false;
function installListener() {
  if (listenerInstalled || typeof document === "undefined") return;
  listenerInstalled = true;
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-ai-connect-action]");
    if (!button) return;
    const action = button.getAttribute("data-ai-connect-action");
    if (action === "create") createToken();
    else if (action === "revoke") revokeToken(button.getAttribute("data-token-id"), button.getAttribute("data-token-name") || "this token");
    else if (action === "copy-url") copyText(mcpUrl(), button);
    else if (action === "copy-token") copyText(state.newToken?.token || "", button);
    else if (action === "dismiss-token") { state.newToken = null; rerender(); }
  });
}
installListener();
