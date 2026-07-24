// ====================================================================
// SECTION: SHARED RENDER / FORMAT UTILS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Leaf module — no init; import getConfiguredApiBaseUrl.
// ====================================================================

import { getConfiguredApiBaseUrl } from "../../../shared/api-client.js";

export function buildFrontendApiUrl(path) {
  const baseUrl = String(getConfiguredApiBaseUrl() || "").trim().replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  if (baseUrl === "/api" && normalizedPath.startsWith("/api/")) {
    return normalizedPath;
  }
  if (baseUrl.endsWith("/api") && normalizedPath.startsWith("/api/")) {
    return `${baseUrl.slice(0, -4)}${normalizedPath}`;
  }
  return `${baseUrl}${normalizedPath}`;
}

export function resultPayload(result, fallback) {
  return result && result.ok ? result.payload : fallback;
}

export function resultRows(result) {
  const payload = resultPayload(result, []);
  if (Array.isArray(payload)) {
    return payload;
  }
  if (Array.isArray(payload?.items)) {
    return payload.items;
  }
  if (Array.isArray(payload?.rows)) {
    return payload.rows;
  }
  return [];
}

export function statusDetailText(payload) {
  if (!payload) {
    return "";
  }
  if (typeof payload === "string") {
    return payload;
  }
  if (Array.isArray(payload)) {
    return payload.map(statusDetailText).filter(Boolean).join("; ");
  }
  if (typeof payload === "object") {
    const direct = payload.detail || payload.message || payload.error;
    if (direct) {
      return statusDetailText(direct);
    }
    const textValues = Object.values(payload)
      .map((value) => statusDetailText(value))
      .filter(Boolean);
    return textValues.slice(0, 3).join("; ");
  }
  return String(payload);
}

export function renderStatusBlock(title, result) {
  if (!result || result.ok) {
    return "";
  }
  const detail = statusDetailText(result.payload);
  return `<div class="module-state warn"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(detail || "Unable to load this GruhaMitra compatibility endpoint.")}</span></div>`;
}

export function currentBillingPeriodQuery() {
  const now = new Date();
  const month = now.getMonth() + 1;
  const year = now.getFullYear();
  return `month=${encodeURIComponent(month)}&year=${encodeURIComponent(year)}`;
}

export function renderSimpleTable(rows, columns, emptyText) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `<p class="muted">${escapeHtml(emptyText)}</p>`;
  }
  return `
    <div class="table-preview compact-table erp-table">
      <table>
        <thead>
          <tr>${columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join("")}</tr>
        </thead>
        <tbody>
          ${rows.slice(0, 12).map((row) => `
            <tr>
              ${columns.map((column) => `<td>${escapeHtml(column.value(row))}</td>`).join("")}
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

export function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
  }[char]));
}

export function formatCountMap(value) {
  if (!value || typeof value !== "object") {
    return "none";
  }
  return Object.entries(value)
    .map(([key, count]) => `${escapeHtml(key)}: ${escapeHtml(count)}`)
    .join(", ") || "none";
}

export function renderPlatformTable(rows, columns, emptyText) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `<p class="muted">${emptyText}</p>`;
  }
  return `
    <div class="table-preview compact-table erp-table">
      <table>
        <thead>
          <tr>${columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join("")}</tr>
        </thead>
        <tbody>
          ${rows.map((row) => `
            <tr>
              ${columns.map((column) => `<td>${escapeHtml(column.value(row))}</td>`).join("")}
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

export function renderPendingApprovalsTable(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `<p class="muted">No pending onboarding approvals.</p>`;
  }
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Request</th>
            <th>App</th>
            <th>Organization</th>
            <th>Admin Email</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((row) => {
            const requestId = row.request_id || row.id || "";
            return `
              <tr>
                <td>${escapeHtml(requestId)}</td>
                <td>${escapeHtml(row.app_key)}</td>
                <td>${escapeHtml(row.organization_name || row.tenant_name)}</td>
                <td>${escapeHtml(row.admin_email)}</td>
                <td>
                  <div class="action-row">
                    <button type="button" data-platform-action="approve" data-request-id="${escapeHtml(requestId)}">Approve</button>
                    <button class="secondary" type="button" data-platform-action="reject" data-request-id="${escapeHtml(requestId)}">Reject</button>
                  </div>
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

export function mandirPublicPaymentPageUrl() {
  const api = encodeURIComponent(getConfiguredApiBaseUrl());
  return `../mandir-public/?api=${api}`;
}

export function renderMandirOperationResult(result) {
  if (!result) {
    return "";
  }
  return `
    <div class="module-state ${result.ok ? "ok" : "warn"}" id="mandir-operation-result">
      <strong>${escapeHtml(result.title || (result.ok ? "Operation completed" : "Operation failed"))}</strong>
      <span>${escapeHtml(result.detail || "")}</span>
    </div>
  `;
}

export function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export function formatCurrency(value) {
  const amount = Number(value || 0);
  return `Rs. ${amount.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatCountLabel(count, singular, plural = `${singular}s`) {
  const safeCount = Number(count || 0);
  return `${safeCount} ${safeCount === 1 ? singular : plural}`;
}

