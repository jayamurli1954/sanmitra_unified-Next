// ====================================================================
// SECTION: CA PRACTICE — state + loaders
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initCaPractice(...).
// CA renderers remain in app.js for a later seam.
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

