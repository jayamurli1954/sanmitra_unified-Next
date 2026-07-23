// ====================================================================
// SECTION: CA PRACTICE — state + loaders
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initCaPractice(...).
// Includes CA practice renderers (Phase 3 seam 34).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastCaDocuments = [];
export let lastCaDocumentsResult = null;
export let lastCaClients = [];
export let lastCaClientsResult = null;
export let caAccessUsers = [];
export let caAccessLoading = false;
export let caInviteError = "";
export let caInviteSuccess = "";
export let caClientDraft = {
  client_name: "",
  gstin: "",
  pan: "",
  contact_person: "",
  assigned_to: "",
  client_owner: "",
  engagement_type: "",
  access_level: "view_only",
  compliance_tracks: "",
  notes: "",
};
export let caPracticeFilters = {
  status: "",
  client_name: "",
  assigned_to: "",
  priority: "",
};
export let caDocumentAttachmentState = {
  document_id: "",
  client_name: "",
  items: [],
  loading: false,
};

export const CA_DOCUMENT_WORKFLOW = ["uploaded", "under_review", "query_raised", "reviewed", "posted"];
export const CA_DOCUMENT_LABELS = {
  uploaded: "Uploaded",
  under_review: "Under review",
  query_raised: "Query raised",
  reviewed: "Reviewed",
  posted: "Posted",
};
export const CA_DOCUMENT_PRIORITY_LABELS = {
  low: "Low",
  normal: "Normal",
  high: "High",
  urgent: "Urgent",
};

/** @type {Record<string, Function> | null} */
let deps = null;

export function initCaPractice(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initCaPractice() must be called before using CA practice helpers");
  }
  return deps;
}

function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function getApiOutput() { return requireDeps().getApiOutput(); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function renderBusinessWorkspace() { return requireDeps().renderBusinessWorkspace(); }
function listBusinessAttachments(ownerType, ownerId) { return requireDeps().listBusinessAttachments(ownerType, ownerId); }

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function renderBusinessAttachmentPanel(opts) { return requireDeps().renderBusinessAttachmentPanel(opts); }
function uploadBusinessAttachmentFiles(ownerType, ownerId, files) {
  return requireDeps().uploadBusinessAttachmentFiles(ownerType, ownerId, files);
}
function isCaViewer() { return requireDeps().isCaViewer(); }
function isBusinessAdmin() { return requireDeps().isBusinessAdmin(); }
function plannedOrgWorkspaceModel(orgType) { return requireDeps().plannedOrgWorkspaceModel(orgType); }


export function setCaInviteError(value) { caInviteError = value; }
export function setCaInviteSuccess(value) { caInviteSuccess = value; }
export function setCaClientDraft(value) { caClientDraft = value; }
export function setCaPracticeFilters(value) { caPracticeFilters = value; }
export function setCaDocumentAttachmentState(value) { caDocumentAttachmentState = value; }
export function setCaAccessLoading(value) { caAccessLoading = !!value; }
export function setCaAccessUsers(value) { caAccessUsers = Array.isArray(value) ? value : []; }
export function setLastCaDocuments(value) { lastCaDocuments = Array.isArray(value) ? value : []; }
export function setLastCaDocumentsResult(value) { lastCaDocumentsResult = value; }
export function setLastCaClients(value) { lastCaClients = Array.isArray(value) ? value : []; }
export function setLastCaClientsResult(value) { lastCaClientsResult = value; }
export function resetCaPracticeWorkspaceState() {
  lastCaDocuments = [];
  lastCaDocumentsResult = null;
  lastCaClients = [];
  lastCaClientsResult = null;
  caAccessUsers = [];
  caInviteError = "";
  caInviteSuccess = "";
}

export async function loadCaPracticeDocuments(options = {}) {
  const rerender = options?.rerender !== false;
  const params = new URLSearchParams({ limit: "100" });
  Object.entries(caPracticeFilters).forEach(([key, value]) => {
    const normalized = String(value || "").trim();
    if (normalized) {
      params.set(key, normalized);
    }
  });
  const result = await apiRequest("mitrabooks", `/api/v1/business/ca-documents?${params.toString()}`, { method: "GET" });
  lastCaDocumentsResult = result;
  if (result.ok) {
    lastCaDocuments = Array.isArray(result.payload?.items) ? result.payload.items : [];
    if (caDocumentAttachmentState.document_id) {
      const selected = lastCaDocuments.find((row) => row.document_id === caDocumentAttachmentState.document_id);
      if (selected) {
        caDocumentAttachmentState = {
          ...caDocumentAttachmentState,
          client_name: selected.client_name || caDocumentAttachmentState.client_name,
        };
      } else {
        caDocumentAttachmentState = { document_id: "", client_name: "", items: [], loading: false };
      }
    }
    if (rerender && getCurrentExperience() === "mitrabooks" && (activeOrgSelectorType() === "CA_PRACTICE" || getActiveBusinessWorkspace() === "ca-access")) {
      getDashboardPreview().innerHTML = renderDashboardPreview(experienceConfig.mitrabooks);
      if (getActiveBusinessWorkspace() === "ca-access") {
        getDashboardPreview().innerHTML = renderBusinessWorkspace();
      }
    }
  } else {
    lastCaDocuments = [];
    setLoginStatus("warn", "Unable to load CA documents", statusDetailText(result.payload?.detail) || `Document metadata request failed with HTTP ${result.status}.`);
    if (rerender && getCurrentExperience() === "mitrabooks" && (activeOrgSelectorType() === "CA_PRACTICE" || getActiveBusinessWorkspace() === "ca-access")) {
      getDashboardPreview().innerHTML = renderDashboardPreview(experienceConfig.mitrabooks);
      if (getActiveBusinessWorkspace() === "ca-access") {
        getDashboardPreview().innerHTML = renderBusinessWorkspace();
      }
    }
  }
  renderJson(getApiOutput(), { ca_documents: { ok: result.ok, status: result.status, count: lastCaDocuments.length, detail: result.payload?.detail || null } });
  return result;
}


export async function loadCaClients(options = {}) {
  const rerender = options?.rerender !== false;
  const result = await apiRequest("mitrabooks", "/api/v1/business/ca-clients?active_only=true&limit=100", { method: "GET" });
  lastCaClientsResult = result;
  if (result.ok) {
    lastCaClients = Array.isArray(result.payload?.items) ? result.payload.items : [];
  } else {
    lastCaClients = [];
    setLoginStatus("warn", "Unable to load CA clients", statusDetailText(result.payload?.detail) || `CA client request failed with HTTP ${result.status}.`);
  }
  if (rerender) {
    rerenderCaPracticeIfActive();
  }
  return result;
}


export function rerenderCaPracticeIfActive() {
  if (getCurrentExperience() === "mitrabooks" && getActiveBusinessWorkspace() === "ca-access") {
    getDashboardPreview().innerHTML = renderBusinessWorkspace();
  }
}


export async function loadCaAccessUsers(options = {}) {
  const rerender = options?.rerender !== false;
  caAccessLoading = true;
  if (rerender && getActiveBusinessWorkspace() === "ca-access") {
    getDashboardPreview().innerHTML = renderBusinessWorkspace();
  }
  const result = await apiRequest("mitrabooks", "/api/v1/business/ca/users", { method: "GET" });
  caAccessLoading = false;
  if (result.ok) {
    caAccessUsers = Array.isArray(result.payload?.ca_users) ? result.payload.ca_users : [];
  } else {
    caAccessUsers = [];
  }
  if (rerender && getActiveBusinessWorkspace() === "ca-access") {
    getDashboardPreview().innerHTML = renderBusinessWorkspace();
  }
  return result;
}


export async function createCaPracticeDocument(form) {
  const formData = new FormData(form);
  const selectedFiles = Array.from(form.querySelector("[name='ca_attachments']")?.files || []);
  const selectedClientId = String(formData.get("client_id") || "").trim();
  const selectedClient = caClientById(selectedClientId);
  const payload = {
    client_id: selectedClientId || null,
    client_name: String(formData.get("client_name") || selectedClient?.client_name || "").trim(),
    document_type: String(formData.get("document_type") || "").trim(),
    period: String(formData.get("period") || "").trim(),
    assigned_to: String(formData.get("assigned_to") || "").trim() || null,
    client_owner: String(formData.get("client_owner") || "").trim() || null,
    priority: String(formData.get("priority") || "normal").trim() || "normal",
    due_date: String(formData.get("due_date") || "").trim() || null,
    compliance_area: String(formData.get("compliance_area") || "").trim() || null,
    client_access_enabled: formData.get("client_access_enabled") === "true",
    original_file_name: String(formData.get("original_file_name") || "").trim() || selectedFiles[0]?.name || null,
    notes: String(formData.get("notes") || "").trim() || null,
  };
  const result = await apiRequest("mitrabooks", "/api/v1/business/ca-documents", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (result.ok) {
    form.reset();
    const documentId = result.payload?.document_id || "";
    if (documentId) {
      caDocumentAttachmentState = {
        document_id: documentId,
        client_name: result.payload?.client_name || payload.client_name,
        items: [],
        loading: false,
      };
    }
    await loadCaPracticeDocuments();
    let uploadResults = [];
    if (documentId) {
      if (selectedFiles.length) {
        uploadResults = await uploadBusinessAttachmentFiles("ca_document", documentId, selectedFiles);
        await loadCaPracticeDocuments({ rerender: false });
      }
      await loadCaDocumentAttachments(documentId, result.payload?.client_name || payload.client_name);
    }
    const successCount = uploadResults.filter((item) => item.ok).length;
    const failureCount = uploadResults.length - successCount;
    if (!uploadResults.length) {
      setLoginStatus("ok", "Document metadata added", `${result.payload?.client_name || "Client"} is now in the CA review queue.`);
    } else if (failureCount === 0) {
      setLoginStatus("ok", "Document metadata added", `${result.payload?.client_name || "Client"} was created with ${successCount} attachment(s).`);
    } else if (successCount > 0) {
      setLoginStatus("warn", "Document added with partial file upload", `${successCount} attachment(s) uploaded and ${failureCount} failed. Refresh the file panel for details.`);
    } else {
      setLoginStatus("warn", "Document added but files failed", `${result.payload?.client_name || "Client"} was created, but the attachment upload failed.`);
    }
  } else {
    setLoginStatus("danger", "Document create failed", statusDetailText(result.payload?.detail) || "Check the required fields and try again.");
  }
  renderJson(getApiOutput(), { create_ca_document: result });
}


export async function createCaClient(form) {
  const formData = new FormData(form);
  const complianceTracks = String(formData.get("compliance_tracks") || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  const payload = {
    client_name: String(formData.get("client_name") || "").trim(),
    gstin: String(formData.get("gstin") || "").trim() || null,
    pan: String(formData.get("pan") || "").trim() || null,
    contact_person: String(formData.get("contact_person") || "").trim() || null,
    assigned_to: String(formData.get("assigned_to") || "").trim() || null,
    client_owner: String(formData.get("client_owner") || "").trim() || null,
    engagement_type: String(formData.get("engagement_type") || "").trim() || null,
    access_level: String(formData.get("access_level") || "view_only").trim() || "view_only",
    compliance_tracks: complianceTracks,
    notes: String(formData.get("notes") || "").trim() || null,
  };
  const result = await apiRequest("mitrabooks", "/api/v1/business/ca-clients", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (result.ok) {
    caClientDraft = {
      client_name: "",
      gstin: "",
      pan: "",
      contact_person: "",
      assigned_to: "",
      client_owner: "",
      engagement_type: "",
      access_level: "view_only",
      compliance_tracks: "",
      notes: "",
    };
    form.reset();
    await loadCaClients();
    setLoginStatus("ok", "CA client added", `${result.payload?.client_name || "Client"} is now available in the CA practice workspace.`);
  } else {
    setLoginStatus("danger", "CA client create failed", statusDetailText(result.payload?.detail) || "Check the required fields and try again.");
  }
  renderJson(getApiOutput(), { create_ca_client: result });
}


export async function loadCaDocumentAttachments(documentId, clientName = "") {
  if (!documentId) {
    caDocumentAttachmentState = { document_id: "", client_name: "", items: [], loading: false };
    rerenderCaPracticeIfActive();
    return { ok: false, status: 0, payload: { detail: "Missing document id." } };
  }
  caDocumentAttachmentState = {
    document_id: documentId,
    client_name: clientName || caDocumentAttachmentState.client_name,
    items: caDocumentAttachmentState.document_id === documentId ? caDocumentAttachmentState.items : [],
    loading: true,
  };
  rerenderCaPracticeIfActive();
  const result = await listBusinessAttachments("ca_document", documentId);
  caDocumentAttachmentState = {
    document_id: documentId,
    client_name: clientName || caDocumentAttachmentState.client_name,
    items: result.ok ? (Array.isArray(result.payload?.items) ? result.payload.items : []) : [],
    loading: false,
  };
  if (!result.ok) {
    setLoginStatus("warn", "Unable to load CA document files", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  rerenderCaPracticeIfActive();
  renderJson(getApiOutput(), { ca_document_attachments: { ok: result.ok, status: result.status, count: caDocumentAttachmentState.items.length } });
  return result;
}


export async function updateCaPracticeDocumentStatus(documentId, status) {
  if (!documentId || !status) {
    return;
  }
  const result = await apiRequest("mitrabooks", `/api/v1/business/ca-documents/${encodeURIComponent(documentId)}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
  if (result.ok) {
    setLoginStatus("ok", "Document status updated", `${result.payload?.client_name || "Document"} marked ${caDocumentStatusLabel(status)}.`);
    await loadCaPracticeDocuments();
  } else {
    setLoginStatus("danger", "Status update failed", statusDetailText(result.payload?.detail) || "Try again.");
  }
  renderJson(getApiOutput(), { update_ca_document: result });
}


// --- CA practice renderers (seam 34) ---

export function caDocumentStatusLabel(status) {
  return CA_DOCUMENT_LABELS[status] || String(status || "Uploaded");
}

export function nextCaDocumentStatus(status) {
  const index = CA_DOCUMENT_WORKFLOW.indexOf(status || "uploaded");
  if (index < 0 || index >= CA_DOCUMENT_WORKFLOW.length - 1) {
    return "";
  }
  return CA_DOCUMENT_WORKFLOW[index + 1];
}

export function caDocumentMetrics(rows) {
  const counts = CA_DOCUMENT_WORKFLOW.reduce((acc, status) => {
    acc[status] = 0;
    return acc;
  }, {});
  (Array.isArray(rows) ? rows : []).forEach((row) => {
    const status = row.status || "uploaded";
    counts[status] = (counts[status] || 0) + 1;
  });
  return [
    ["Uploaded", String(counts.uploaded || 0), "Awaiting classification"],
    ["Under review", String(counts.under_review || 0), "Staff review in progress"],
    ["Reviewed", String(counts.reviewed || 0), "Ready for posting"],
    ["Posted", String(counts.posted || 0), "Linked to vouchers or returns"],
    ["Query raised", String(counts.query_raised || 0), "Needs client clarification"],
  ];
}

export function caDocumentPriorityLabel(priority) {
  return CA_DOCUMENT_PRIORITY_LABELS[priority] || "Normal";
}

export function caPracticeSummary(rows) {
  const safeRows = Array.isArray(rows) ? rows : [];
  const clients = new Set();
  const assignees = new Map();
  const compliance = new Map();
  let clientAccess = 0;
  let urgent = 0;
  safeRows.forEach((row) => {
    if (row.client_name) {
      clients.add(row.client_name);
    }
    const owner = row.assigned_to || "Unassigned";
    assignees.set(owner, (assignees.get(owner) || 0) + 1);
    const area = row.compliance_area || "General";
    compliance.set(area, (compliance.get(area) || 0) + 1);
    if (row.client_access_enabled) {
      clientAccess += 1;
    }
    if (row.priority === "urgent" || row.priority === "high") {
      urgent += 1;
    }
  });
  return {
    clientCount: clients.size,
    clientAccess,
    urgent,
    assignees: Array.from(assignees.entries()).sort((a, b) => b[1] - a[1]),
    compliance: Array.from(compliance.entries()).sort((a, b) => b[1] - a[1]),
  };
}

export function caClientComplianceLabel(tracks) {
  const items = Array.isArray(tracks) ? tracks.filter(Boolean) : [];
  return items.length ? items.join(", ") : "General";
}

export function caClientSwitchRows() {
  if (Array.isArray(lastCaClients) && lastCaClients.length) {
    return lastCaClients
      .filter((row) => row.active !== false)
      .map((row) => ({
        client: row.client_name || "Unnamed client",
        count: lastCaDocuments.filter((doc) => (doc.client_name || "") === (row.client_name || "")).length,
        owner: row.client_owner || "",
        access_level: row.access_level || "view_only",
        compliance: caClientComplianceLabel(row.compliance_tracks),
      }));
  }
  return caPracticeClientBreakdown(lastCaDocuments);
}

export function caClientById(clientId) {
  return (Array.isArray(lastCaClients) ? lastCaClients : [])
    .find((row) => String(row.client_id || "") === String(clientId || "")) || null;
}

export function caPracticeClientBreakdown(rows) {
  const counts = new Map();
  (Array.isArray(rows) ? rows : []).forEach((row) => {
    const key = String(row.client_name || "Unassigned client").trim() || "Unassigned client";
    counts.set(key, (counts.get(key) || 0) + 1);
  });
  return Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([client, count]) => ({ client, count }));
}


export function renderCaPracticeFilters() {
  return `
    <form class="ca-practice-filter-panel" data-ca-filter-form>
      <label>
        <span>Status</span>
        <select name="status">
          <option value="">All statuses</option>
          ${CA_DOCUMENT_WORKFLOW.map((status) => `
            <option value="${escapeHtml(status)}" ${caPracticeFilters.status === status ? "selected" : ""}>${escapeHtml(caDocumentStatusLabel(status))}</option>
          `).join("")}
        </select>
      </label>
      <label>
        <span>Client</span>
        <input name="client_name" type="search" maxlength="160" value="${escapeHtml(caPracticeFilters.client_name)}" placeholder="Client or company">
      </label>
      <label>
        <span>Assigned to</span>
        <input name="assigned_to" type="search" maxlength="120" value="${escapeHtml(caPracticeFilters.assigned_to)}" placeholder="Staff or partner">
      </label>
      <label>
        <span>Priority</span>
        <select name="priority">
          <option value="">All priorities</option>
          ${Object.entries(CA_DOCUMENT_PRIORITY_LABELS).map(([value, label]) => `
            <option value="${escapeHtml(value)}" ${caPracticeFilters.priority === value ? "selected" : ""}>${escapeHtml(label)}</option>
          `).join("")}
        </select>
      </label>
      <div class="ca-practice-filter-actions">
        <button type="submit" class="secondary">Apply Filters</button>
        <button type="button" class="secondary" data-business-action="ca-doc-clear-filters">Clear</button>
      </div>
    </form>
  `;
}

export function renderCaClientMaster() {
  const rows = Array.isArray(lastCaClients) ? lastCaClients : [];
  return `
    <section class="erp-panel" style="margin-bottom:1rem">
      <div class="preview-heading compact" style="margin-bottom:1rem">
        <div>
          <h5>Client Master</h5>
          <p>Tenant-scoped client/company records for CA practice access, assignment, and compliance routing.</p>
        </div>
      </div>
      <form data-ca-client-form class="ca-practice-filter-panel" style="margin-bottom:1rem">
        <label>
          <span>Client name</span>
          <input name="client_name" type="text" maxlength="160" value="${escapeHtml(caClientDraft.client_name)}" placeholder="Client book or company name" required>
        </label>
        <label>
          <span>GSTIN</span>
          <input name="gstin" type="text" maxlength="20" value="${escapeHtml(caClientDraft.gstin)}" placeholder="Optional GSTIN">
        </label>
        <label>
          <span>PAN</span>
          <input name="pan" type="text" maxlength="20" value="${escapeHtml(caClientDraft.pan)}" placeholder="Optional PAN">
        </label>
        <label>
          <span>Contact person</span>
          <input name="contact_person" type="text" maxlength="120" value="${escapeHtml(caClientDraft.contact_person)}" placeholder="Owner or finance contact">
        </label>
        <label>
          <span>Assigned to</span>
          <input name="assigned_to" type="text" maxlength="120" value="${escapeHtml(caClientDraft.assigned_to)}" placeholder="Reviewer or staff">
        </label>
        <label>
          <span>Client owner</span>
          <input name="client_owner" type="text" maxlength="120" value="${escapeHtml(caClientDraft.client_owner)}" placeholder="Partner or manager">
        </label>
        <label>
          <span>Engagement type</span>
          <input name="engagement_type" type="text" maxlength="80" value="${escapeHtml(caClientDraft.engagement_type)}" placeholder="Bookkeeping / GST / Audit">
        </label>
        <label>
          <span>Access level</span>
          <select name="access_level">
            <option value="view_only" ${caClientDraft.access_level === "view_only" ? "selected" : ""}>View only</option>
            <option value="data_entry" ${caClientDraft.access_level === "data_entry" ? "selected" : ""}>Data entry</option>
            <option value="full_access" ${caClientDraft.access_level === "full_access" ? "selected" : ""}>Full access</option>
            <option value="restricted_filing" ${caClientDraft.access_level === "restricted_filing" ? "selected" : ""}>Restricted filing</option>
          </select>
        </label>
        <label>
          <span>Compliance tracks</span>
          <input name="compliance_tracks" type="text" maxlength="240" value="${escapeHtml(caClientDraft.compliance_tracks)}" placeholder="GST, TDS, Audit">
        </label>
        <label>
          <span>Notes</span>
          <input name="notes" type="text" maxlength="500" value="${escapeHtml(caClientDraft.notes)}" placeholder="Optional notes">
        </label>
        <div class="ca-practice-filter-actions">
          <button type="submit">Add Client</button>
          <button type="button" class="secondary" data-business-action="ca-client-refresh">Refresh</button>
        </div>
      </form>
      ${rows.length ? `
        <div class="table-preview compact-table erp-table">
          <table>
            <thead>
              <tr>
                <th>Client</th>
                <th>Contact</th>
                <th>Owner / Staff</th>
                <th>Access</th>
                <th>Compliance</th>
              </tr>
            </thead>
            <tbody>
              ${rows.map((row) => `
                <tr>
                  <td>
                    <strong>${escapeHtml(row.client_name || "-")}</strong>
                    <span class="row-subtext">${escapeHtml(row.engagement_type || "General engagement")}</span>
                  </td>
                  <td>
                    <strong>${escapeHtml(row.contact_person || "-")}</strong>
                    <span class="row-subtext">${escapeHtml(row.gstin || row.pan || "No GSTIN/PAN")}</span>
                  </td>
                  <td>
                    <strong>${escapeHtml(row.client_owner || "-")}</strong>
                    <span class="row-subtext">${escapeHtml(row.assigned_to || "Unassigned")}</span>
                  </td>
                  <td><span class="pill">${escapeHtml(String(row.access_level || "view_only").replaceAll("_", " "))}</span></td>
                  <td>${escapeHtml(caClientComplianceLabel(row.compliance_tracks))}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      ` : `
        <div class="empty-state compact">
          <strong>No CA client records yet</strong>
          <span>Create client books here, then use the review queue below for document operations.</span>
        </div>
      `}
    </section>
  `;
}

export function renderCaPracticeOperations(rows) {
  const summary = caPracticeSummary(rows);
  const assigneeRows = summary.assignees.length ? summary.assignees : [["Unassigned", 0]];
  const complianceRows = summary.compliance.length ? summary.compliance : [["General", 0]];
  return `
    <div class="ca-practice-operations-grid">
      <article>
        <span>Client Tracking</span>
        <strong>${escapeHtml(String(summary.clientCount))}</strong>
        <small>Client books represented in this tenant queue.</small>
      </article>
      <article>
        <span>Client Access</span>
        <strong>${escapeHtml(String(summary.clientAccess))}</strong>
        <small>Metadata records flagged for client visibility when access rules are enabled.</small>
      </article>
      <article>
        <span>Priority Work</span>
        <strong>${escapeHtml(String(summary.urgent))}</strong>
        <small>High or urgent records needing staff attention.</small>
      </article>
    </div>
    <div class="ca-practice-workload-grid">
      <section>
        <h5>Staff Assignment</h5>
        ${assigneeRows.map(([name, count]) => `
          <div class="ca-practice-row">
            <span>${escapeHtml(name)}</span>
            <strong>${escapeHtml(String(count))}</strong>
          </div>
        `).join("")}
      </section>
      <section>
        <h5>Compliance Dashboard</h5>
        ${complianceRows.map(([name, count]) => `
          <div class="ca-practice-row">
            <span>${escapeHtml(name)}</span>
            <strong>${escapeHtml(String(count))}</strong>
          </div>
        `).join("")}
      </section>
    </div>
  `;
}

export function renderCaDocumentTable(rows) {
  if (!lastCaDocumentsResult) {
    return `
      <div class="empty-state">
        <strong>Loading document metadata</strong>
        <span>Tenant-scoped CA practice records will appear here.</span>
      </div>
    `;
  }
  if (!Array.isArray(rows) || rows.length === 0) {
    return `
      <div class="empty-state">
        <strong>No CA document metadata yet</strong>
        <span>Add a client document record and upload supporting files into the tenant-scoped review queue.</span>
      </div>
    `;
  }
  return `
    <div class="table-preview compact-table erp-table ca-document-status-table">
      <table>
        <thead>
          <tr>
            <th>Client</th>
            <th>Document type</th>
            <th>Period</th>
            <th>Owner / Staff</th>
            <th>Priority</th>
            <th>Status</th>
            <th>Next action</th>
            <th>Posting ref</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((row) => {
            const nextStatus = nextCaDocumentStatus(row.status);
            return `
              <tr>
                <td>
                  <strong>${escapeHtml(row.client_name || "-")}</strong>
                  <span class="row-subtext">${escapeHtml(row.original_file_name || "No file uploaded")}</span>
                  <span class="row-subtext">Book ${escapeHtml(row.book_id || row.accounting_entity_id || "primary")}${row.client_id ? ` | Client ${escapeHtml(row.client_id)}` : ""}</span>
                </td>
                <td>${escapeHtml(row.document_type || "-")}</td>
                <td>${escapeHtml(row.period || "-")}</td>
                <td>
                  <strong>${escapeHtml(row.client_owner || "-")}</strong>
                  <span class="row-subtext">${escapeHtml(row.assigned_to || "Unassigned")}</span>
                </td>
                <td>
                  <span class="pill ${row.priority === "urgent" || row.priority === "high" ? "warn" : ""}">${escapeHtml(caDocumentPriorityLabel(row.priority))}</span>
                  <span class="row-subtext">${escapeHtml(row.due_date || "No due date")}</span>
                </td>
                <td><span class="pill">${escapeHtml(caDocumentStatusLabel(row.status))}</span></td>
                <td>
                  ${escapeHtml(row.next_action || "-")}
                  <span class="row-subtext">${escapeHtml(row.compliance_area || "General")} ${row.client_access_enabled ? " | Client access flagged" : ""}</span>
                  <span class="row-subtext">${escapeHtml(String(row.attachment_count || 0))} attachment(s)${row.reviewed_at ? ` | Reviewed ${escapeHtml(String(row.reviewed_at).slice(0, 10))}` : ""}</span>
                </td>
                <td>${escapeHtml(row.posting_reference || "-")}</td>
                <td>
                  <div class="invoice-detail-actions">
                    <button
                      class="secondary"
                      type="button"
                      data-business-action="ca-doc-files"
                      data-document-id="${escapeHtml(row.document_id || "")}"
                      data-client-name="${escapeHtml(row.client_name || "")}"
                    >Files</button>
                    ${nextStatus ? `
                      <button
                        class="secondary"
                        type="button"
                        data-business-action="ca-doc-status"
                        data-document-id="${escapeHtml(row.document_id || "")}"
                        data-status="${escapeHtml(nextStatus)}"
                      >${escapeHtml(caDocumentStatusLabel(nextStatus))}</button>
                    ` : `<button class="secondary" type="button" disabled>Posted</button>`}
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

export function renderCaDocumentIntake(documentIntake) {
  const metrics = caDocumentMetrics(lastCaDocuments);
  return `
    <div class="ca-document-intake">
      <div class="ca-document-upload-card">
        <form data-ca-document-form>
          <span class="workbench-kicker">Document Metadata</span>
          <h4>${escapeHtml(documentIntake.title)}</h4>
          <p>${escapeHtml(documentIntake.copy)}</p>
          <div class="ca-upload-field-grid">
            <label>
              <span>Client book</span>
              <select name="client_id">
                <option value="">Manual client name</option>
                ${(Array.isArray(lastCaClients) ? lastCaClients : []).filter((row) => row.active !== false).map((row) => `
                  <option value="${escapeHtml(row.client_id || "")}">${escapeHtml(row.client_name || row.client_id || "")} | ${escapeHtml(row.accounting_entity_id || "primary")}</option>
                `).join("")}
              </select>
            </label>
            <label>
              <span>Client</span>
              <input name="client_name" type="text" maxlength="160" placeholder="Client book or company name" list="ca-client-name-options" required>
            </label>
            <label>
              <span>Document type</span>
              <select name="document_type" required>
                <option value="">Select type</option>
                <option>Bank statement</option>
                <option>Purchase bills</option>
                <option>Sales invoices</option>
                <option>GST return</option>
                <option>TDS file</option>
                <option>Supporting document</option>
              </select>
            </label>
            <label>
              <span>Period</span>
              <input name="period" type="text" maxlength="80" placeholder="May 2026 / FY 2026-27" required>
            </label>
            <label>
              <span>Assigned to</span>
              <input name="assigned_to" type="text" maxlength="120" placeholder="Reviewer or partner">
            </label>
            <label>
              <span>Client owner</span>
              <input name="client_owner" type="text" maxlength="120" placeholder="Partner or manager">
            </label>
            <label>
              <span>Priority</span>
              <select name="priority">
                <option value="normal">Normal</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
                <option value="low">Low</option>
              </select>
            </label>
            <label>
              <span>Due date</span>
              <input name="due_date" type="date">
            </label>
            <label>
              <span>Compliance area</span>
              <select name="compliance_area">
                <option value="">General</option>
                <option>GST</option>
                <option>TDS</option>
                <option>Income tax</option>
                <option>Audit</option>
                <option>ROC</option>
                <option>Bookkeeping</option>
              </select>
            </label>
            <label>
              <span>Original file name</span>
              <input name="original_file_name" type="text" maxlength="240" placeholder="Optional override for the first uploaded file">
            </label>
            <label>
              <span>Notes</span>
              <input name="notes" type="text" maxlength="500" placeholder="Review notes or client instruction">
            </label>
            <label>
              <span>Attachments</span>
              <input name="ca_attachments" type="file" multiple>
            </label>
            <label class="ca-checkbox-field">
              <input name="client_access_enabled" type="checkbox" value="true">
              <span>Flag for future client access</span>
            </label>
          </div>
          <div class="ca-document-actions">
            <button type="submit">Add Document Metadata</button>
            <button class="secondary" type="button" data-business-action="ca-doc-refresh">Refresh</button>
          </div>
          <datalist id="ca-client-name-options">
            ${(Array.isArray(lastCaClients) ? lastCaClients : []).map((row) => `
              <option value="${escapeHtml(row.client_name || "")}"></option>
            `).join("")}
          </datalist>
        </form>
      </div>

      <div class="ca-document-workflow" aria-label="Document review workflow">
        ${CA_DOCUMENT_WORKFLOW.map((status, index) => `
          <span class="${index === 0 ? "active" : ""}">${escapeHtml(caDocumentStatusLabel(status))}</span>
        `).join("")}
      </div>

      <div class="ca-document-status-grid">
        ${metrics.map(([label, value, copy]) => `
          <article>
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(value)}</strong>
            <small>${escapeHtml(copy)}</small>
          </article>
        `).join("")}
      </div>

      ${renderCaPracticeFilters()}
      ${renderCaPracticeOperations(lastCaDocuments)}

      ${renderCaDocumentTable(lastCaDocuments)}
      ${caDocumentAttachmentState.document_id ? renderBusinessAttachmentPanel({
        ownerType: "ca_document",
        ownerId: caDocumentAttachmentState.document_id,
        items: caDocumentAttachmentState.items,
        loading: caDocumentAttachmentState.loading,
        title: `CA document files${caDocumentAttachmentState.client_name ? ` · ${caDocumentAttachmentState.client_name}` : ""}`,
        emptyCopy: "Upload client source documents, statements, or review papers for this CA record.",
        uploadButtonLabel: "Upload files",
      }) : ""}

      <div class="ca-document-note">
        Current state: metadata records and supporting files are tenant-scoped and stored through the MitraBooks business API. Deferred scope: OCR, voucher posting, and return filing links are not enabled yet.
      </div>
    </div>
  `;
}

export function renderCaStatusPill(status) {
  const map = { pending: "warn", invited: "warn", accepted: "ok", revoked: "err" };
  const label = { pending: "Pending", invited: "Credentials Sent", accepted: "Active", revoked: "Revoked" };
  return `<span class="pill ${map[status] || "warn"}">${label[status] || escapeHtml(status)}</span>`;
}

export function renderCaAccessManagementSection() {
  const loading = caAccessLoading ? `<p class="settings-boundary-note">Loading CA users…</p>` : "";
  const rows = caAccessUsers.length === 0 && !caAccessLoading
    ? `<tr><td colspan="5" style="text-align:center;opacity:.6">No CA users yet. Send an invite below.</td></tr>`
    : caAccessUsers.map(u => `
      <tr>
        <td>${escapeHtml(u.full_name || "—")}</td>
        <td>${escapeHtml(u.email)}</td>
        <td>${renderCaStatusPill(u.status)}</td>
        <td style="font-size:.75rem;opacity:.7">${u.invited_at ? new Date(u.invited_at).toLocaleDateString("en-IN") : "—"}</td>
        <td style="white-space:nowrap;display:flex;gap:.35rem;align-items:center">
          ${(u.status === "accepted" || u.status === "invited") && u.user_id ? `
            <button class="secondary small" type="button"
              data-coa-action="ca-resend" data-ca-email="${escapeHtml(u.email)}"
              data-ca-name="${escapeHtml(u.full_name || "")}">Resend</button>
            <button class="secondary small" type="button"
              data-coa-action="ca-revoke" data-ca-user-id="${escapeHtml(u.user_id)}"
              data-ca-email="${escapeHtml(u.email)}">Revoke</button>
          ` : u.status === "revoked" && u.user_id ? `
            <button class="secondary small" type="button"
              data-coa-action="ca-reinstate" data-ca-user-id="${escapeHtml(u.user_id)}"
              data-ca-email="${escapeHtml(u.email)}">Reinstate</button>
          ` : ""}
          ${u.invite_id ? `
            <button class="secondary small" type="button" style="color:var(--err,#f55);border-color:var(--err,#f55)"
              data-coa-action="ca-delete" data-ca-invite-id="${escapeHtml(u.invite_id)}"
              data-ca-email="${escapeHtml(u.email)}">Cancel</button>
          ` : ""}
        </td>
      </tr>`).join("");

  const successMsg = caInviteSuccess ? `<div class="pill ok" style="margin-bottom:.5rem">${escapeHtml(caInviteSuccess)}</div>` : "";
  const errMsg = caInviteError ? `<div class="pill err" style="margin-bottom:.5rem">${escapeHtml(caInviteError)}</div>` : "";

  return `
    <section class="erp-panel" style="margin-bottom:1.5rem">
      <div class="preview-heading compact" style="margin-bottom:1rem">
        <div>
          <h5>CA Access — Invited Users</h5>
          <p>CAs you invite get read-only access to financial statements, GST returns, TDS register, and bank reconciliation.</p>
        </div>
      </div>
      ${loading}
      <table class="erp-table" style="margin-bottom:1.25rem">
        <thead><tr><th>Name</th><th>Email</th><th>Status</th><th>Invited</th><th></th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="settings-section-heading" style="margin-bottom:.5rem"><h6>Invite a CA</h6></div>
      ${successMsg}${errMsg}
      <form data-ca-invite-form style="display:grid;grid-template-columns:1fr 1fr auto;gap:.5rem;align-items:end">
        <label style="display:flex;flex-direction:column;gap:.25rem;font-size:.8rem">
          CA Name
          <input name="full_name" type="text" placeholder="e.g. CA Suresh Kumar" required maxlength="120" />
        </label>
        <label style="display:flex;flex-direction:column;gap:.25rem;font-size:.8rem">
          CA Email
          <input name="email" type="email" placeholder="ca@example.com" required maxlength="120" />
        </label>
        <button type="button" data-coa-action="ca-invite-submit">Send Invite</button>
      </form>
      <p style="font-size:.75rem;opacity:.6;margin-top:.5rem">The CA receives a token-based invite email and sets the password on first use. Use <strong>Resend</strong> to issue a fresh invite link when needed.</p>
    </section>`;
}

export function renderCaViewerPortal() {
  const reportLinks = [
    ["Financial Statements", "reports", "Trial Balance, P&L, Balance Sheet, General Ledger"],
    ["GST Returns", "gst-returns", "GSTR-1, GSTR-3B, GSTR-2B ITC Reconciliation"],
    ["TDS / TCS Register", "tds-tcs", "Quarterly TDS/TCS register, section-wise"],
    ["Bank Reconciliation", "bank-recon", "Statement matching and BRS"],
  ];
  return `
    <div class="verification-panel erp-workspace-panel ca-practice-workspace">
      <div class="preview-heading compact">
        <div>
          <span class="workbench-kicker">Read-only access</span>
          <h4>CA Portal</h4>
          <p>You have read-only access to financial data for this business. Use the links below to navigate.</p>
        </div>
        <span class="pill ok">CA Viewer</span>
      </div>
      <div class="planned-org-module-grid">
        ${reportLinks.map(([title, workspace, copy]) => `
          <article>
            <div>
              <h4>${escapeHtml(title)}</h4>
              <button class="secondary" type="button"
                data-business-action="workspace-view"
                data-workspace-view="${escapeHtml(workspace)}">Open</button>
            </div>
            <p>${escapeHtml(copy)}</p>
          </article>`).join("")}
      </div>
    </div>`;
}

export function renderCaPracticePortalWorkspace() {
  if (isCaViewer()) {
    return renderCaViewerPortal();
  }

  const model = plannedOrgWorkspaceModel("CA_PRACTICE");
  const summary = caPracticeSummary(lastCaDocuments);
  const clients = caClientSwitchRows().slice(0, 8);
  return `
    <div class="verification-panel erp-workspace-panel ca-practice-workspace">
      <div class="preview-heading compact">
        <div>
          <span class="workbench-kicker">Practice workbench</span>
          <h4>CA Practice Portal</h4>
          <p>Manage CA access to your books and track client document workflow.</p>
        </div>
        <span class="pill ok">Active</span>
      </div>
      ${isBusinessAdmin() ? renderCaAccessManagementSection() : ""}
      <div class="planned-org-kpis" style="margin-top:1rem">
        <article>
          <span>Client Tracking</span>
          <strong>${escapeHtml(String(summary.clientCount))}</strong>
          <small>Client books in this tenant queue.</small>
        </article>
        <article>
          <span>Review Queue</span>
          <strong>${escapeHtml(String(lastCaDocuments.length))}</strong>
          <small>Document metadata entries.</small>
        </article>
        <article>
          <span>Compliance</span>
          <strong>${escapeHtml(String(summary.compliance.length))}</strong>
          <small>Compliance areas tracked.</small>
        </article>
      </div>
      ${renderCaClientMaster()}
      <div class="planned-org-module-grid" style="margin-top:1rem">
        ${clients.map((row) => `
          <article>
            <div>
              <h4>${escapeHtml(row.client)}</h4>
              <button class="secondary" type="button" data-business-action="ca-client-filter" data-client-name="${escapeHtml(row.client)}">Switch</button>
            </div>
            <p>${escapeHtml(String(row.count || 0))} document(s) in the current client queue.${caPracticeFilters.client_name === row.client ? " Active company filter." : ""}</p>
            ${row.owner || row.compliance ? `<span class="row-subtext">${escapeHtml([row.owner, row.compliance].filter(Boolean).join(" · "))}</span>` : ""}
          </article>
        `).join("")}
      </div>
      ${caPracticeFilters.client_name ? `
      <div class="settings-boundary-note" style="margin-top:1rem">
        <strong>Company switch:</strong>
        Viewing CA queue for <strong>${escapeHtml(caPracticeFilters.client_name)}</strong>.
        <button class="secondary" type="button" data-business-action="ca-client-filter-clear" style="margin-left:.5rem">Clear</button>
      </div>` : ""}
      ${renderCaDocumentIntake(model.documentIntake)}
    </div>
  `;
}

