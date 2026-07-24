// ====================================================================
// SECTION: BUSINESS ATTACHMENTS
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initAttachments(...).
// ====================================================================

import { apiRequest } from "../../../shared/api-client.js";

/** @type {Record<string, Function> | null} */
let deps = null;

export function initAttachments(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initAttachments() must be called before using attachment helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function getAccessToken() { return requireDeps().getAccessToken(); }
function buildFrontendApiUrl(path) { return requireDeps().buildFrontendApiUrl(path); }

export function businessAttachmentPath(ownerType, ownerId, attachmentId = "") {
  const safeOwnerId = encodeURIComponent(ownerId || "");
  if (ownerType === "sales_invoice") {
    return attachmentId
      ? `/api/v1/business/invoices/${safeOwnerId}/attachments/${encodeURIComponent(attachmentId)}/download`
      : `/api/v1/business/invoices/${safeOwnerId}/attachments`;
  }
  if (ownerType === "purchase_bill") {
    return attachmentId
      ? `/api/v1/business/bills/${safeOwnerId}/attachments/${encodeURIComponent(attachmentId)}/download`
      : `/api/v1/business/bills/${safeOwnerId}/attachments`;
  }
  return attachmentId
    ? `/api/v1/business/ca-documents/${safeOwnerId}/attachments/${encodeURIComponent(attachmentId)}/download`
    : `/api/v1/business/ca-documents/${safeOwnerId}/attachments`;
}

export async function uploadBusinessAttachmentFiles(ownerType, ownerId, files) {
  const queue = Array.from(files || []).filter(Boolean);
  const results = [];
  for (const file of queue) {
    const headers = { "X-App-Key": "mitrabooks" };
    const token = getAccessToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    const formData = new FormData();
    formData.append("file", file);
    try {
      const response = await fetch(buildFrontendApiUrl(businessAttachmentPath(ownerType, ownerId)), {
        method: "POST",
        headers,
        body: formData,
      });
      const contentType = response.headers.get("content-type") || "";
      const payload = contentType.includes("application/json") ? await response.json() : await response.text();
      results.push({ ok: response.ok, status: response.status, payload });
    } catch (error) {
      results.push({
        ok: false,
        status: 0,
        payload: { detail: error instanceof Error ? error.message : "Attachment upload failed" },
      });
    }
  }
  return results;
}

export async function listBusinessAttachments(ownerType, ownerId) {
  return apiRequest("mitrabooks", `${businessAttachmentPath(ownerType, ownerId)}?limit=100`, { method: "GET" });
}

export function attachmentListSummary(items) {
  return Array.isArray(items) ? `${items.length} file(s)` : "0 file(s)";
}

export function renderBusinessAttachmentPanel({ ownerType, ownerId, items, loading, title, emptyCopy, uploadButtonLabel }) {
  const safeItems = Array.isArray(items) ? items : [];
  return `
    <div class="verification-panel" data-attachment-panel="${escapeHtml(ownerType)}">
      <div class="preview-heading compact">
        <div>
          <h5>${escapeHtml(title)}</h5>
          <p>${loading ? "Loading attachments…" : `${attachmentListSummary(safeItems)} for this document.`}</p>
        </div>
        <div class="invoice-detail-actions">
          <button class="secondary" type="button" data-business-action="refresh-attachments" data-owner-type="${escapeHtml(ownerType)}" data-owner-id="${escapeHtml(ownerId || "")}">Refresh</button>
        </div>
      </div>
      <div class="ca-document-actions">
        <input type="file" multiple data-attachment-input data-owner-type="${escapeHtml(ownerType)}" data-owner-id="${escapeHtml(ownerId || "")}">
        <button type="button" data-business-action="upload-attachments" data-owner-type="${escapeHtml(ownerType)}" data-owner-id="${escapeHtml(ownerId || "")}">${escapeHtml(uploadButtonLabel || "Upload files")}</button>
      </div>
      ${safeItems.length ? `
        <div class="table-preview compact-table erp-table">
          <table>
            <thead>
              <tr>
                <th>File</th>
                <th>Type</th>
                <th>Size</th>
                <th>Uploaded</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              ${safeItems.map((item) => `
                <tr>
                  <td>${escapeHtml(item.file_name || "attachment")}</td>
                  <td>${escapeHtml(item.content_type || "application/octet-stream")}</td>
                  <td>${escapeHtml(String(item.size_bytes || 0))} bytes</td>
                  <td>${escapeHtml(String(item.uploaded_at || "").slice(0, 10) || "-")}</td>
                  <td>
                    <button
                      class="secondary"
                      type="button"
                      data-business-action="download-attachment"
                      data-owner-type="${escapeHtml(ownerType)}"
                      data-owner-id="${escapeHtml(ownerId || "")}"
                      data-attachment-id="${escapeHtml(item.attachment_id || "")}"
                      data-file-name="${escapeHtml(item.file_name || "attachment")}"
                    >Download</button>
                  </td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      ` : `
        <div class="empty-state compact">
          <strong>No attachments yet</strong>
          <span>${escapeHtml(emptyCopy)}</span>
        </div>
      `}
    </div>
  `;
}

