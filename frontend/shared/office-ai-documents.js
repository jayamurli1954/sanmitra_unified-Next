// OfficeMitra Documents package (ADR-016/017). Staff CA queue + missing-doc tasks; no client portal.

export const DOCUMENTS_STATE_DEFAULTS = {
  documentsEnabled: false,
  documentsRequestsEnabled: false,
  documentsQueue: [],
  documentsQueueEnabled: true,
  documentsQueueReason: "",
  documentsBookId: "primary",
  documentsLinkNoteId: "",
  documentsLinkDocumentId: "",
  documentsGaps: [],
};

export function applyDocumentsPing(state, payload) {
  state.documentsEnabled = !!payload?.documents_enabled;
  state.documentsRequestsEnabled = !!payload?.documents_capabilities?.requests;
}

export function clearDocumentsPing(state) {
  state.documentsEnabled = false;
  state.documentsRequestsEnabled = false;
}

export function documentsBannerHtml(state) {
  if (!state.documentsEnabled) return "";
  const requests = state.documentsRequestsEnabled
    ? " Staff missing-document requests are on (ADR-017)."
    : "";
  return `<p class="muted" style="margin:0.35rem 0 0;">Documents package enabled: staff CA queue read + Review note links (ADR-016).${requests} Uploads stay in MitraBooks CA Practice.</p>`;
}

export function renderDocumentsPanel(state, escapeHtml) {
  const rows = (state.documentsQueue || [])
    .map((row) => {
      const id = String(row.document_id || "").trim();
      return `<tr>
        <td>${escapeHtml(String(row.client_name || ""))}</td>
        <td>${escapeHtml(String(row.document_type || ""))}</td>
        <td>${escapeHtml(String(row.period || ""))}</td>
        <td>${escapeHtml(String(row.status || ""))}</td>
        <td>${row.linked_to_review_note ? "Linked" : "—"}</td>
        <td><button class="secondary" type="button" data-office-ai-action="documents-use" data-document-id="${escapeHtml(id)}">Use id</button></td>
      </tr>`;
    })
    .join("");
  const noteOptions = (state.reviewNotes || [])
    .map((note) => {
      const id = String(note.id || "").trim();
      const selected = id === String(state.documentsLinkNoteId || "").trim() ? "selected" : "";
      const label = `${String(note.status || "open")} · ${String(note.description || "").slice(0, 48)}`;
      return `<option value="${escapeHtml(id)}" ${selected}>${escapeHtml(label)}</option>`;
    })
    .join("");
  const gapRows = (state.documentsGaps || [])
    .map((row) => {
      const type = String(row.document_type || "").trim();
      const present = !!row.present;
      const action = present
        ? "On queue"
        : `<button class="secondary" type="button" data-office-ai-action="documents-request" data-document-type="${escapeHtml(type)}">Request</button>`;
      return `<tr>
        <td>${escapeHtml(String(row.label || type))}</td>
        <td>${present ? "Present" : "Missing"}</td>
        <td>${action}</td>
      </tr>`;
    })
    .join("");
  const queueOff = state.documentsQueueEnabled === false;
  return `
    <div>
      <p class="muted">This tab lists the MitraBooks CA staff queue. It does not upload files, change status, or open a client portal. Open the CA Practice workspace (<code>ca-access</code>) to add documents.</p>
      ${queueOff ? `<p class="muted">Queue unavailable (${escapeHtml(String(state.documentsQueueReason || "business_module_off"))}). Standalone OfficeMitra without MitraBooks business fails soft.</p>` : ""}
      <p class="muted">Book: ${escapeHtml(String(state.documentsBookId || "primary"))}</p>
      <table class="data-table">
        <thead><tr><th>Client</th><th>Type</th><th>Period</th><th>Status</th><th>Review link</th><th></th></tr></thead>
        <tbody>${rows || `<tr><td colspan="6" class="muted">No CA documents on this book.</td></tr>`}</tbody>
      </table>
      ${state.documentsRequestsEnabled ? `
        <h5>Expected papers (staff request)</h5>
        <p class="muted">Raises an OfficeMitra task. Does not email the client or write the CA queue.</p>
        <table class="data-table">
          <thead><tr><th>Document</th><th>Queue</th><th></th></tr></thead>
          <tbody>${gapRows || `<tr><td colspan="3" class="muted">No checklist rows.</td></tr>`}</tbody>
        </table>
      ` : `<p class="muted">Enable office_ai.documents.requests to raise staff tasks for missing types.</p>`}
      ${state.reviewNotesEnabled ? `
        <h5>Link a Review note</h5>
        <div class="erp-inline-form">
          <select data-office-ai-field="documentsLinkNoteId">${noteOptions || `<option value="">No notes</option>`}</select>
          <input data-office-ai-field="documentsLinkDocumentId" placeholder="CA document id" value="${escapeHtml(state.documentsLinkDocumentId || "")}" />
          <button class="secondary" type="button" data-office-ai-action="documents-link">Link</button>
          <button class="secondary" type="button" data-office-ai-action="documents-unlink">Unlink</button>
        </div>
      ` : `<p class="muted">Enable office_ai.review.notes to attach a queue row to a Review note.</p>`}
    </div>
  `;
}

export function syncDocumentsFields(root, state) {
  const note = root.querySelector("[data-office-ai-field='documentsLinkNoteId']");
  const doc = root.querySelector("[data-office-ai-field='documentsLinkDocumentId']");
  if (note) state.documentsLinkNoteId = note.value || "";
  if (doc) state.documentsLinkDocumentId = doc.value || "";
}

export async function refreshDocumentsData(state, { apiRequest, unwrap }) {
  if (!state.documentsEnabled) {
    state.documentsQueue = [];
    state.documentsGaps = [];
    return;
  }
  const params = new URLSearchParams();
  if (state.reviewSelectedId) params.set("engagement_id", state.reviewSelectedId);
  const qs = params.toString();
  const payload = unwrap(await apiRequest(`/api/v1/officemitra/documents/queue${qs ? `?${qs}` : ""}`));
  state.documentsQueue = payload.items || [];
  state.documentsQueueEnabled = payload.enabled !== false;
  state.documentsQueueReason = payload.reason || payload.error || "";
  state.documentsBookId = payload.accounting_entity_id || "primary";
  if (state.documentsRequestsEnabled) {
    const gaps = unwrap(await apiRequest(`/api/v1/officemitra/documents/gaps${qs ? `?${qs}` : ""}`));
    state.documentsGaps = gaps.items || [];
  } else {
    state.documentsGaps = [];
  }
}

export async function handleDocumentsAction(action, el, ctx) {
  if (!String(action || "").startsWith("documents-")) return false;
  const { state, apiRequest, unwrap } = ctx;
  const helpers = { apiRequest, unwrap };
  if (action === "documents-use") {
    state.documentsLinkDocumentId = String(el?.getAttribute("data-document-id") || "").trim();
  } else if (action === "documents-link") {
    const noteId = String(state.documentsLinkNoteId || "").trim();
    const documentId = String(state.documentsLinkDocumentId || "").trim();
    if (!noteId) throw new Error("Select a Review note");
    if (!documentId) throw new Error("Enter or pick a CA document id");
    unwrap(await apiRequest(`/api/v1/officemitra/documents/notes/${encodeURIComponent(noteId)}/link`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_id: documentId }),
    }));
    state.notice = "Review note linked to CA document. MitraBooks queue was not changed.";
    await refreshDocumentsData(state, helpers);
  } else if (action === "documents-unlink") {
    const noteId = String(state.documentsLinkNoteId || "").trim();
    if (!noteId) throw new Error("Select a Review note");
    unwrap(await apiRequest(`/api/v1/officemitra/documents/notes/${encodeURIComponent(noteId)}/unlink`, { method: "POST" }));
    state.notice = "Review note unlinked. CA document remains in MitraBooks.";
    await refreshDocumentsData(state, helpers);
  } else if (action === "documents-request") {
    if (!state.documentsRequestsEnabled) throw new Error("Enable office_ai.documents.requests");
    const documentType = String(el?.getAttribute("data-document-type") || "").trim();
    if (!documentType) throw new Error("Missing document type");
    const body = { document_type: documentType };
    if (state.reviewSelectedId) body.engagement_id = state.reviewSelectedId;
    const result = unwrap(await apiRequest("/api/v1/officemitra/documents/requests", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }));
    state.notice = result?.created === false
      ? "Open staff task already exists for this missing type."
      : "Staff task created. Upload the paper in MitraBooks CA Practice. No client email was sent.";
    await refreshDocumentsData(state, helpers);
  } else {
    return false;
  }
  return true;
}
