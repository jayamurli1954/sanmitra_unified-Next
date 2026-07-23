// ====================================================================
// SECTION: GST PERIOD LOCKS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initPeriodLocks(...).
// NOTE: rerenderBusinessReportsIfActive stays in app.js (shared helper).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastPeriodLocks = [];

/** @type {Record<string, Function> | null} */
let deps = null;

export function initPeriodLocks(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initPeriodLocks() must be called before using period-lock helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function rerenderBusinessReportsIfActive() { return requireDeps().rerenderBusinessReportsIfActive(); }
function isBusinessAdmin() { return requireDeps().isBusinessAdmin(); }
function todayIsoDate() { return requireDeps().todayIsoDate(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

export async function loadPeriodLocks() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/gst-period-locks", { method: "GET" });
  lastPeriodLocks = result.ok && Array.isArray(result.payload?.items) ? result.payload.items : [];
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { period_locks: { ok: result.ok, count: lastPeriodLocks.length } });
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: GST PERIOD LOCKS
// API   : POST /api/v1/business/gst-period-lock
// NOTE  : setGstPeriodLock, lockGstPeriodFromInput, rerenderBusinessReportsIfActive
// ══════════════════════════════════════════════════════════════════════

export async function setGstPeriodLock(period, locked) {
  if (!period) {
    setLoginStatus("warn", "Period required", "Enter a month to lock (YYYY-MM).");
    return;
  }
  const result = await apiRequest("mitrabooks", "/api/v1/business/gst-period-locks", {
    method: "PUT",
    body: JSON.stringify({ period, locked, accounting_entity_id: "primary" }),
  });
  if (result.ok) {
    setLoginStatus("ok", locked ? "Period locked" : "Period unlocked", `${period} is now ${locked ? "finalised" : "open"}.`);
    await loadPeriodLocks();
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can finalise GST periods.");
  } else {
    setLoginStatus("danger", "Update failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { set_period_lock: { ok: result.ok, status: result.status } });
}

export function lockGstPeriodFromInput() {
  const input = document.querySelector("[data-period-lock-input]");
  const value = input?.value || "";
  setGstPeriodLock(value, true);
}

export function renderPeriodLocksPanel() {
  const admin = isBusinessAdmin();
  const rows = (Array.isArray(lastPeriodLocks) ? lastPeriodLocks : []).filter((p) => p.locked);
  const nowMonth = todayIsoDate().slice(0, 7);
  return `
    <div class="preview-heading compact">
      <div><p>Finalise a month after filing its GST return. Reversals and back-dated postings into a locked month are blocked.</p></div>
    </div>
    ${admin ? `
      <div class="report-date-controls">
        <label>Finalise month
          <input type="month" data-period-lock-input value="${escapeHtml(nowMonth)}">
        </label>
        <button class="secondary" type="button" data-business-action="lock-period">Lock month</button>
      </div>
    ` : `<p class="muted">Only a tenant admin can finalise or unlock periods.</p>`}
    <div class="table-preview compact-table">
      <table>
        <thead><tr><th>Period</th><th>Status</th><th>Updated by</th>${admin ? "<th>Action</th>" : ""}</tr></thead>
        <tbody>
          ${rows.length ? rows.map((p) => `
            <tr>
              <td>${escapeHtml(p.period || "")}</td>
              <td><span class="pill warn">finalised</span></td>
              <td>${escapeHtml(p.updated_by || "")}</td>
              ${admin ? `<td><button class="secondary" type="button" data-business-action="unlock-period" data-period="${escapeHtml(p.period)}">Unlock</button></td>` : ""}
            </tr>
          `).join("") : `<tr><td colspan="${admin ? 4 : 3}" class="muted">No periods finalised yet.</td></tr>`}
        </tbody>
      </table>
    </div>
  `;
}
