// ====================================================================
// SECTION: AUDIT TRAIL
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initAuditTrail(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastAuditEvents = [];
export const auditListState = {
  offset: 0,
  q: "",
  entity_type: "",
  action: "",
  from_date: "",
  to_date: "",
};

/** @type {Record<string, Function> | null} */
let deps = null;

export function initAuditTrail(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initAuditTrail() must be called before using audit-trail helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function renderBusinessWorkspace() { return requireDeps().renderBusinessWorkspace(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

function formatTimestampIST(utcTimestamp) {
  if (!utcTimestamp) return "-";
  try {
    // Parse UTC timestamp and convert to IST (UTC+5:30)
    const date = new Date(utcTimestamp.includes('Z') ? utcTimestamp : utcTimestamp + 'Z');
    const istDate = new Date(date.getTime() + (5.5 * 60 * 60 * 1000)); // Add 5.5 hours for IST
    const year = istDate.getUTCFullYear();
    const month = String(istDate.getUTCMonth() + 1).padStart(2, '0');
    const day = String(istDate.getUTCDate()).padStart(2, '0');
    const hours = String(istDate.getUTCHours()).padStart(2, '0');
    const minutes = String(istDate.getUTCMinutes()).padStart(2, '0');
    const seconds = String(istDate.getUTCSeconds()).padStart(2, '0');
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds} IST`;
  } catch (e) {
    return utcTimestamp.slice(0, 19);
  }
}


// ══════════════════════════════════════════════════════════════════════
// SECTION: AUDIT TRAIL
// API   : GET /api/v1/business/audit-log
// NOTE  : renderAuditEventsTable, loadAuditEvents, applyAuditFilters
// ══════════════════════════════════════════════════════════════════════

export function renderAuditEventsTable(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `
      <div class="empty-state">
        <strong>No audit events found</strong>
        <span>Audit entries will appear here after party, voucher, or account activity.</span>
      </div>
    `;
  }
  return `
    <div class="table-preview compact-table erp-table audit-table">
      <table>
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Entity</th>
            <th>Action</th>
            <th>Actor</th>
            <th>Detail</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows.slice(0, 30).map((row) => {
            const detail = row.description || row.detail || row.entity_id || "-";
            const detailShort = detail.length > 30 ? detail.slice(0, 27) + "..." : detail;
            return `
              <tr>
                <td style="font-size: 12px;">${escapeHtml(formatTimestampIST(row.timestamp || row.created_at || ""))}</td>
                <td>${escapeHtml(row.entity_type || row.entity || "-")}</td>
                <td><span class="pill">${escapeHtml(row.action || "unknown")}</span></td>
                <td>${escapeHtml(row.actor || row.user || "-")}</td>
                <td style="font-size: 12px;">${escapeHtml(detailShort)}</td>
                <td>
                  <button
                    class="secondary"
                    type="button"
                    data-business-action="view-audit-event"
                    data-event-id="${escapeHtml(row.event_id || row.id || "")}"
                  >View</button>
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

export function renderAuditListFilters(rowsLength) {
  const state = auditListState;
  const offset = Number(state.offset || 0);
  const startRow = rowsLength > 0 ? offset + 1 : 0;
  const endRow = rowsLength > 0 ? offset + Math.min(rowsLength, 30) : 0;
  const nextDisabled = rowsLength < 30 ? "disabled" : "";
  const prevDisabled = offset <= 0 ? "disabled" : "";

  return `
    <div class="list-filter-panel" data-business-list="audit">
      <div class="list-filter-bar">
        <label class="field">
          <span>Entity</span>
          <select name="entity_type">
            <option value="">All entities</option>
            <option value="party" ${state.entity_type === "party" ? "selected" : ""}>Party</option>
            <option value="voucher" ${state.entity_type === "voucher" ? "selected" : ""}>Voucher</option>
            <option value="account" ${state.entity_type === "account" ? "selected" : ""}>Account</option>
          </select>
        </label>
        <label class="field">
          <span>Action</span>
          <select name="action">
            <option value="">All actions</option>
            <option value="create" ${state.action === "create" ? "selected" : ""}>Create</option>
            <option value="update" ${state.action === "update" ? "selected" : ""}>Update</option>
            <option value="post" ${state.action === "post" ? "selected" : ""}>Post</option>
            <option value="reverse" ${state.action === "reverse" ? "selected" : ""}>Reverse</option>
            <option value="deactivate" ${state.action === "deactivate" ? "selected" : ""}>Deactivate</option>
          </select>
        </label>
        <label class="field">
          <span>From</span>
          <input name="from_date" type="date" value="${escapeHtml(state.from_date || "")}">
        </label>
        <label class="field">
          <span>To</span>
          <input name="to_date" type="date" value="${escapeHtml(state.to_date || "")}">
        </label>
        <div class="list-filter-actions">
          <button type="button" data-business-action="apply-audit-filter">Apply</button>
          <button class="secondary" type="button" data-business-action="reset-audit-filter">Reset</button>
        </div>
      </div>
      <div class="paging-row">
        <span class="muted">Showing ${escapeHtml(startRow)}-${escapeHtml(endRow)}</span>
        <button class="secondary" type="button" data-business-action="page-audit" data-page-direction="prev" ${prevDisabled}>Prev</button>
        <button class="secondary" type="button" data-business-action="page-audit" data-page-direction="next" ${nextDisabled}>Next</button>
      </div>
    </div>
  `;
}

export async function loadAuditEvents(filters = {}) {
  const appKey = "mitrabooks";
  const state = auditListState;
  const params = new URLSearchParams();

  if (state.entity_type) params.append("entity_type", state.entity_type);
  if (state.action) params.append("action", state.action);
  if (state.from_date) params.append("from_date", state.from_date);
  if (state.to_date) params.append("to_date", state.to_date);
  params.append("offset", state.offset || 0);
  params.append("limit", 30);

  const queryString = params.toString();
  const url = `/api/v1/audit/events${queryString ? "?" + queryString : ""}`;

  const result = await apiRequest(appKey, url, { method: "GET" });
  if (result.ok) {
    lastAuditEvents = Array.isArray(result.payload?.items) ? result.payload.items : Array.isArray(result.payload) ? result.payload : [];
    if (getCurrentExperience() === "mitrabooks" && getActiveBusinessWorkspace() === "audit") {
      getDashboardPreview().innerHTML = renderBusinessWorkspace();
    }
  } else {
    lastAuditEvents = [];
    setLoginStatus("warn", "Unable to load audit events", result.payload?.detail || "Check connection and try again.");
  }
  renderJson(getApiOutput(), { audit_events: { ok: result.ok, count: lastAuditEvents.length } });
}

export function openAuditEventDetailDialog(eventId) {
  const dialog = document.getElementById("audit-event-detail-dialog");
  if (!dialog) return;

  const event = lastAuditEvents.find((e) => (e.event_id || e.id) === eventId);
  if (!event) {
    setLoginStatus("warn", "Event not found", "The event may have been deleted.");
    return;
  }

  document.getElementById("audit-event-entity").textContent = event.entity_type || "-";
  document.getElementById("audit-event-action").textContent = event.action || "-";
  document.getElementById("audit-event-actor").textContent = event.actor || event.user || "-";
  document.getElementById("audit-event-timestamp").textContent = String(event.timestamp || event.created_at || "-").slice(0, 19);
  document.getElementById("audit-event-detail-label").textContent = `${event.entity_type || "Event"} · ${event.action || "unknown"}`;

  const payload = event.payload || event.details || {};
  document.getElementById("audit-event-payload").textContent = JSON.stringify(payload, null, 2);

  dialog.showModal();
}

export function applyAuditFilters() {
  const panel = document.querySelector("[data-business-list='audit']");
  if (!panel) return;

  const entityInput = panel.querySelector("select[name='entity_type']");
  const actionInput = panel.querySelector("select[name='action']");
  const fromInput = panel.querySelector("input[name='from_date']");
  const toInput = panel.querySelector("input[name='to_date']");

  auditListState.entity_type = entityInput?.value || "";
  auditListState.action = actionInput?.value || "";
  auditListState.from_date = fromInput?.value || "";
  auditListState.to_date = toInput?.value || "";
  auditListState.offset = 0;

  loadAuditEvents();
}

export function resetAuditFilters() {
  auditListState.offset = 0;
  auditListState.entity_type = "";
  auditListState.action = "";
  auditListState.from_date = "";
  auditListState.to_date = "";
  loadAuditEvents();
}

export function pageAuditList(direction) {
  const offset = Number(auditListState.offset || 0);
  auditListState.offset = direction === "next" ? offset + 30 : Math.max(0, offset - 30);
  loadAuditEvents();
}
