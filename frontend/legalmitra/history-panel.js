/** Personal LegalMitra chat / upload history sidebar. */
import { apiRequest, getAccessToken } from "../shared/api-client.js";

function formatHistoryDate(value) {
  const date = new Date(value || "");
  if (Number.isNaN(date.getTime())) {
    return "Saved chat";
  }
  return date.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function historyItemTitle(item) {
  const title = String(item?.title || item?.query || "").trim();
  if (title) return title;
  const preview = String(item?.preview || item?.response || "").trim();
  return preview ? preview.slice(0, 140) : "LegalMitra chat";
}

export function createHistoryPanel({
  appKey,
  historyList,
  historyStatus,
  uploadHistoryList,
  uploadHistoryStatus,
  refreshButton,
  queryInput,
  answerPanel,
  escapeHtml,
  renderLegalAnswer,
}) {
  function renderPersonalHistory(items) {
    if (!historyList || !historyStatus) return;
    if (!items.length) {
      historyStatus.textContent = getAccessToken()
        ? "No saved LegalMitra chats yet. Your new questions will appear here."
        : "Sign in to load your personal chat history.";
      historyList.innerHTML = "";
      return;
    }
    historyStatus.textContent = `${items.length} personal chat(s). Only your own history is shown.`;
    historyList.innerHTML = items.map((item) => {
      const title = historyItemTitle(item);
      const preview = String(item.preview || "").trim();
      return `
    <button type="button" data-history-id="${escapeHtml(item.record_id || "")}">
      <strong class="history-title">${escapeHtml(title)}</strong>
      ${preview && preview !== title ? `<em class="history-preview">${escapeHtml(preview)}</em>` : ""}
      <span>${escapeHtml(formatHistoryDate(item.created_at))} - expires in ${escapeHtml(String(item.retention_days || ""))} days</span>
    </button>`;
    }).join("");
    historyList.querySelectorAll("[data-history-id]").forEach((button) => {
      const row = items.find((item) => item.record_id === button.getAttribute("data-history-id"));
      button.addEventListener("click", () => {
        if (!row) return;
        if (queryInput) queryInput.value = String(row.query || row.title || "").trim();
        renderLegalAnswer({
          ok: true,
          status: 200,
          payload: {
            response: row.response || "",
            provider: row.provider || "legalmitra_history",
            strategy: row.strategy || "saved_history",
            citations: row.citations || [],
            confidence: row.confidence || "unknown",
            human_review_required: row.human_review_required !== false,
            answer_id: row.record_id,
            history_record_id: row.record_id,
          },
        });
        if (answerPanel) answerPanel.scrollTop = 0;
      });
    });
  }

  function renderPersonalUploads(items) {
    if (!uploadHistoryList || !uploadHistoryStatus) return;
    if (!items.length) {
      uploadHistoryStatus.textContent = getAccessToken()
        ? "No retained uploaded documents yet."
        : "Sign in to load your uploaded documents.";
      uploadHistoryList.innerHTML = "";
      return;
    }
    uploadHistoryStatus.textContent = `${items.length} personal upload(s). Only your own uploads are shown.`;
    uploadHistoryList.innerHTML = items.map((item) => `
    <button type="button" data-upload-id="${escapeHtml(item.upload_id || "")}">
      <strong>${escapeHtml(item.source_filename || "Uploaded document")}</strong>
      <span>${escapeHtml(formatHistoryDate(item.created_at))} - ${(Number(item.file_size_bytes || 0) / 1024 / 1024).toFixed(2)} MB - retention ${escapeHtml(String(item.retention_days || ""))} days</span>
    </button>`).join("");
  }

  async function loadPersonalHistory() {
    if (!historyList || !historyStatus) return;
    if (!getAccessToken()) {
      renderPersonalHistory([]);
      renderPersonalUploads([]);
      return;
    }
    historyStatus.textContent = "Loading your personal chat history...";
    if (uploadHistoryStatus) uploadHistoryStatus.textContent = "Loading your uploaded documents...";
    const result = await apiRequest(appKey, "/api/v1/legalmitra/history?limit=50", { method: "GET" });
    const uploadsResult = await apiRequest(appKey, "/api/v1/legalmitra/uploads?limit=50", { method: "GET" });
    if (!result.ok) {
      historyStatus.textContent = result.status === 401
        ? "Sign in to load your personal chat history."
        : "Could not load chat history.";
      historyList.innerHTML = "";
    } else {
      renderPersonalHistory(Array.isArray(result.payload?.items) ? result.payload.items : []);
    }
    if (!uploadsResult.ok) {
      if (uploadHistoryStatus) {
        uploadHistoryStatus.textContent = uploadsResult.status === 401
          ? "Sign in to load your uploaded documents."
          : "Could not load uploaded documents.";
      }
      if (uploadHistoryList) uploadHistoryList.innerHTML = "";
    } else {
      renderPersonalUploads(Array.isArray(uploadsResult.payload?.items) ? uploadsResult.payload.items : []);
    }
  }

  refreshButton?.addEventListener("click", loadPersonalHistory);
  return { loadPersonalHistory, renderPersonalHistory, renderPersonalUploads };
}
