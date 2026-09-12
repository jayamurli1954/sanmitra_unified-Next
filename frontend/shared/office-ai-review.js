export { applyDocumentsPing, clearDocumentsPing, documentsBannerHtml, handleDocumentsAction, refreshDocumentsData, renderDocumentsPanel, syncDocumentsFields } from "./office-ai-documents.js";

export const REVIEW_STATE_DEFAULTS = {
  reviewEnabled: false,
  reviewPapersEnabled: false,
  reviewNotesEnabled: false,
  reviewEngagements: [],
  reviewSelectedId: "",
  reviewIssues: [],
  reviewPapers: [],
  reviewNotes: [],
  reviewPeriod: "",
  reviewPackId: "",
  reviewNoteText: "",
};

export function syncReviewFields(root, state) {
  const reviewPeriod = root.querySelector("[data-office-ai-field='reviewPeriod']");
  const reviewPackId = root.querySelector("[data-office-ai-field='reviewPackId']");
  const reviewNoteText = root.querySelector("[data-office-ai-field='reviewNoteText']");
  if (reviewPeriod) state.reviewPeriod = reviewPeriod.value || "";
  if (reviewPackId) state.reviewPackId = reviewPackId.value || "";
  if (reviewNoteText) state.reviewNoteText = reviewNoteText.value || "";
}

export function reviewBannerHtml(state) {
  if (!state.reviewEnabled) return "";
  return `<p class="muted" style="margin:0.35rem 0 0;">Review workspaces enabled: scan, working papers, and notes (ADR-015). Off by default for live ERP tenants.</p>`;
}

export function applyReviewPing(state, payload) {
  state.reviewEnabled = !!payload?.review_enabled;
  state.reviewPapersEnabled = !!payload?.review_capabilities?.working_papers;
  state.reviewNotesEnabled = !!payload?.review_capabilities?.notes;
}

export function clearReviewPing(state) {
  state.reviewEnabled = false;
  state.reviewPapersEnabled = false;
  state.reviewNotesEnabled = false;
}

function reviewEngagementById(state, id) {
  const key = String(id || "").trim();
  return (state.reviewEngagements || []).find((item) => String(item.id || "").trim() === key) || null;
}

export function renderReviewPanel(state, escapeHtml) {
  const selected = reviewEngagementById(state, state.reviewSelectedId);
  const engagementRows = (state.reviewEngagements || [])
    .map((item) => {
      const id = String(item.id || "").trim();
      const active = id === state.reviewSelectedId;
      return `<tr>
        <td>${escapeHtml(String(item.period || ""))}</td>
        <td>${escapeHtml(String(item.status || ""))}</td>
        <td>${item.engagement_risk_score == null ? "—" : escapeHtml(String(item.engagement_risk_score))}</td>
        <td>
          <button class="${active ? "primary" : "secondary"}" type="button" data-office-ai-action="review-select" data-engagement-id="${escapeHtml(id)}">${active ? "Selected" : "Select"}</button>
        </td>
      </tr>`;
    })
    .join("");
  const issueRows = (state.reviewIssues || [])
    .map((issue) => `<tr>
      <td>${escapeHtml(String(issue.finding_code || ""))}</td>
      <td>${escapeHtml(String(issue.severity || ""))}</td>
      <td>${escapeHtml(String(issue.description || ""))}</td>
    </tr>`)
    .join("");
  const paperRows = (state.reviewPapers || [])
    .map((paper) => {
      const id = String(paper.id || "").trim();
      const path = String(paper.download_path || "");
      return `<tr>
        <td>${escapeHtml(String(paper.type || ""))}</td>
        <td>${escapeHtml(String(paper.status || ""))}</td>
        <td>${escapeHtml(String(paper.content_hash || "").slice(0, 12))}</td>
        <td>
          ${path ? `<button class="secondary" type="button" data-office-ai-action="review-download-paper" data-paper-id="${escapeHtml(id)}" data-filename="${escapeHtml(String(paper.filename || "paper.xlsx"))}">Download</button>` : ""}
          ${paper.immutable ? "Closed" : `<button class="secondary" type="button" data-office-ai-action="review-close-paper" data-paper-id="${escapeHtml(id)}">Close</button>`}
        </td>
      </tr>`;
    })
    .join("");
  const noteRows = (state.reviewNotes || [])
    .map((note) => {
      const id = String(note.id || "").trim();
      const status = String(note.status || "");
      const closed = status === "closed";
      return `<tr>
      <td>${escapeHtml(status)}</td>
      <td>${escapeHtml(String(note.description || ""))}</td>
      <td>${escapeHtml(String(note.task_id || "—"))}</td>
      <td>${escapeHtml(String(note.ca_document_id || "—"))}</td>
      <td>
        ${closed ? "Closed" : `<button class="secondary" type="button" data-office-ai-action="review-close-note" data-note-id="${escapeHtml(id)}">Close</button>`}
      </td>
    </tr>`;
    })
    .join("");
  return `
    <div>
      <p class="muted">Review uses linked MIS packs. It does not post to the live MitraBooks ledger. Risk score is not the MIS data-quality score.</p>
      <div class="erp-inline-form">
        <input data-office-ai-field="reviewPeriod" placeholder="Period (e.g. 2026-07)" value="${escapeHtml(state.reviewPeriod || "")}" />
        <input data-office-ai-field="reviewPackId" placeholder="MIS pack id (optional)" value="${escapeHtml(state.reviewPackId || "")}" />
        <button class="primary" type="button" data-office-ai-action="review-create">Create engagement</button>
      </div>
      <table class="data-table">
        <thead><tr><th>Period</th><th>Status</th><th>Risk</th><th></th></tr></thead>
        <tbody>${engagementRows || `<tr><td colspan="4" class="muted">No engagements yet.</td></tr>`}</tbody>
      </table>
      ${selected ? `
        <p>Selected ${escapeHtml(selected.period || "")} · pack ${escapeHtml(String(selected.pack_id || "none"))} · risk ${selected.engagement_risk_score == null ? "—" : escapeHtml(String(selected.engagement_risk_score))}</p>
        <button class="primary" type="button" data-office-ai-action="review-scan">Scan</button>
        ${state.reviewPapersEnabled ? `<button class="secondary" type="button" data-office-ai-action="review-generate-papers">Generate working papers</button>` : ""}
        <h5>Findings</h5>
        <table class="data-table">
          <thead><tr><th>Code</th><th>Severity</th><th>Description</th></tr></thead>
          <tbody>${issueRows || `<tr><td colspan="3" class="muted">Run a scan.</td></tr>`}</tbody>
        </table>
        ${state.reviewPapersEnabled ? `
          <h5>Working papers</h5>
          <table class="data-table">
            <thead><tr><th>Type</th><th>Status</th><th>Hash</th><th></th></tr></thead>
            <tbody>${paperRows || `<tr><td colspan="4" class="muted">None generated.</td></tr>`}</tbody>
          </table>
        ` : ""}
        ${state.reviewNotesEnabled ? `
          <h5>Notes</h5>
          <textarea data-office-ai-field="reviewNoteText" rows="3">${escapeHtml(state.reviewNoteText || "")}</textarea>
          <button class="secondary" type="button" data-office-ai-action="review-create-note">Create note (creates a task)</button>
          <table class="data-table">
            <thead><tr><th>Status</th><th>Description</th><th>Task</th><th>CA doc</th><th></th></tr></thead>
            <tbody>${noteRows || `<tr><td colspan="5" class="muted">No notes.</td></tr>`}</tbody>
          </table>
        ` : ""}
      ` : ""}
    </div>
  `;
}

export async function refreshReviewSelection(state, { apiRequest, unwrap }) {
  const id = String(state.reviewSelectedId || "").trim();
  if (!id) {
    state.reviewIssues = [];
    state.reviewPapers = [];
    state.reviewNotes = [];
    return;
  }
  const issues = unwrap(await apiRequest(`/api/v1/officemitra/review/engagements/${encodeURIComponent(id)}/issues`));
  state.reviewIssues = issues.items || [];
  if (state.reviewPapersEnabled) {
    const papers = unwrap(await apiRequest(`/api/v1/officemitra/review/engagements/${encodeURIComponent(id)}/working-papers`));
    state.reviewPapers = papers.items || [];
  } else {
    state.reviewPapers = [];
  }
  if (state.reviewNotesEnabled) {
    const notes = unwrap(await apiRequest(`/api/v1/officemitra/review/engagements/${encodeURIComponent(id)}/notes`));
    state.reviewNotes = notes.items || [];
  } else {
    state.reviewNotes = [];
  }
}

export async function refreshReviewData(state, helpers) {
  if (!state.reviewEnabled) {
    state.reviewEngagements = [];
    state.reviewIssues = [];
    state.reviewPapers = [];
    state.reviewNotes = [];
    return;
  }
  const payload = helpers.unwrap(await helpers.apiRequest("/api/v1/officemitra/review/engagements?limit=50"));
  state.reviewEngagements = payload.items || [];
  if (state.reviewSelectedId && !reviewEngagementById(state, state.reviewSelectedId)) {
    state.reviewSelectedId = "";
  }
  if (!state.reviewSelectedId && state.reviewEngagements.length) {
    state.reviewSelectedId = String(state.reviewEngagements[0]?.id || "").trim();
  }
  await refreshReviewSelection(state, helpers);
}

export async function handleReviewAction(action, el, ctx) {
  if (!String(action || "").startsWith("review-")) return false;
  const { state, apiRequest, unwrap, formatApiDetail, resolveAppKey, requireDeps } = ctx;
  const reviewEngagementId = (action === "review-select" || action === "review-scan" || action === "review-generate-papers" || action === "review-create-note")
    ? String(el?.getAttribute("data-engagement-id") || el?.dataset?.engagementId || state.reviewSelectedId || "").trim()
    : "";
  const reviewPaperId = (action === "review-download-paper" || action === "review-close-paper")
    ? String(el?.getAttribute("data-paper-id") || el?.dataset?.paperId || "").trim()
    : "";
  const reviewNoteId = action === "review-close-note"
    ? String(el?.getAttribute("data-note-id") || el?.dataset?.noteId || "").trim()
    : "";
  const helpers = { apiRequest, unwrap };

  if (action === "review-select") {
    if (!reviewEngagementId) throw new Error("Select an engagement");
    state.reviewSelectedId = reviewEngagementId;
    await refreshReviewSelection(state, helpers);
  } else if (action === "review-create") {
    const period = (state.reviewPeriod || "").trim();
    if (!period) throw new Error("Enter a period");
    const body = { period, jurisdiction: "IN" };
    if ((state.reviewPackId || "").trim()) body.pack_id = state.reviewPackId.trim();
    const created = unwrap(await apiRequest("/api/v1/officemitra/review/engagements", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }));
    state.reviewSelectedId = String(created?.item?.id || "").trim();
    state.notice = "Engagement created.";
    await refreshReviewData(state, helpers);
  } else if (action === "review-scan") {
    const id = reviewEngagementId || state.reviewSelectedId;
    if (!id) throw new Error("Select an engagement");
    unwrap(await apiRequest(`/api/v1/officemitra/review/engagements/${encodeURIComponent(id)}/scan`, { method: "POST" }));
    state.notice = "Scan complete. Risk score is engagement risk, not MIS data quality.";
    await refreshReviewData(state, helpers);
  } else if (action === "review-generate-papers") {
    const id = reviewEngagementId || state.reviewSelectedId;
    if (!id) throw new Error("Select an engagement");
    unwrap(await apiRequest(`/api/v1/officemitra/review/engagements/${encodeURIComponent(id)}/working-papers`, { method: "POST" }));
    state.notice = "Working papers generated.";
    await refreshReviewData(state, helpers);
  } else if (action === "review-create-note") {
    const id = reviewEngagementId || state.reviewSelectedId;
    if (!id) throw new Error("Select an engagement");
    const description = (state.reviewNoteText || "").trim();
    if (!description) throw new Error("Enter a note");
    unwrap(await apiRequest(`/api/v1/officemitra/review/engagements/${encodeURIComponent(id)}/notes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ description }),
    }));
    state.reviewNoteText = "";
    state.notice = "Note created and linked to an OfficeMitra task.";
    await refreshReviewData(state, helpers);
  } else if (action === "review-close-paper") {
    if (!reviewPaperId) throw new Error("Missing working paper");
    unwrap(await apiRequest(`/api/v1/officemitra/review/working-papers/${encodeURIComponent(reviewPaperId)}/close`, { method: "POST" }));
    state.notice = "Working paper closed (immutable).";
    await refreshReviewData(state, helpers);
  } else if (action === "review-close-note") {
    if (!reviewNoteId) throw new Error("Missing review note");
    unwrap(await apiRequest(`/api/v1/officemitra/review/notes/${encodeURIComponent(reviewNoteId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "closed" }),
    }));
    state.notice = "Review note closed.";
    await refreshReviewData(state, helpers);
  } else if (action === "review-download-paper") {
    if (!reviewPaperId) throw new Error("Missing working paper");
    const filename = String(el?.getAttribute("data-filename") || "working-paper.xlsx");
    const downloadFn = requireDeps().downloadApiFile;
    if (typeof downloadFn !== "function") throw new Error("File download helper is not available in this shell");
    const result = await downloadFn(
      resolveAppKey(),
      `/api/v1/officemitra/review/working-papers/${encodeURIComponent(reviewPaperId)}/download`,
      filename,
      { timeoutMs: 60000 },
    );
    if (!result?.ok) throw new Error(formatApiDetail(result?.payload?.detail) || "Download failed");
  } else {
    return false;
  }
  return true;
}
