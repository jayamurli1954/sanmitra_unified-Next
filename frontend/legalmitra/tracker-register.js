/* LegalMitra Tracker — P1 document register (metadata only) */

const REGISTER_EMPTY = {
  cloud_minimized:
    "Register papers here. Prefer extracts over keeping every full file hot in cloud. Full PDFs are not uploaded in this step.",
  chamber_lan:
    "Document register (linked from chamber server). Full papers stay on your chamber server. LegalMitra holds metadata and extracts only — Connector sync is planned.",
};

export function createDocumentRegisterController({
  apiRequest,
  getAccessToken,
  appKey,
  getCustodyMode,
}) {
  let matters = [];
  let selectedMatterId = "";
  let documents = [];

  function panelEls() {
    return {
      panel: document.getElementById("document-register-panel"),
      empty: document.getElementById("document-register-empty"),
      matterSelect: document.getElementById("document-register-matter"),
      list: document.getElementById("document-register-list"),
      status: document.getElementById("document-register-status"),
      form: document.getElementById("document-register-form"),
      caseNumber: document.getElementById("document-register-case-number"),
      issues: document.getElementById("document-register-issues"),
      saveCaseCard: document.getElementById("document-register-save-case-card"),
    };
  }

  function setStatus(message) {
    const { status } = panelEls();
    if (status) status.textContent = message || "";
  }

  function renderEmptyCopy() {
    const { empty } = panelEls();
    if (!empty) return;
    const mode = getCustodyMode?.() || "cloud_minimized";
    empty.textContent = REGISTER_EMPTY[mode] || REGISTER_EMPTY.cloud_minimized;
  }

  function renderMatterOptions() {
    const { matterSelect } = panelEls();
    if (!matterSelect) return;
    const previous = selectedMatterId || matterSelect.value;
    matterSelect.textContent = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = matters.length
      ? "Select a live matter…"
      : "No live matters yet";
    matterSelect.appendChild(placeholder);
    matters.forEach((matter) => {
      const option = document.createElement("option");
      option.value = matter.matter_id;
      option.textContent = `${matter.matter_number || matter.matter_id} · ${matter.title || "Matter"}`;
      matterSelect.appendChild(option);
    });
    if (previous && matters.some((m) => m.matter_id === previous)) {
      matterSelect.value = previous;
      selectedMatterId = previous;
    } else {
      selectedMatterId = "";
      matterSelect.value = "";
    }
  }

  function renderDocumentList() {
    const { list } = panelEls();
    if (!list) return;
    list.textContent = "";
    if (!selectedMatterId) {
      const li = document.createElement("li");
      li.textContent = "Select a matter to view its document register.";
      list.appendChild(li);
      return;
    }
    if (!documents.length) {
      const li = document.createElement("li");
      li.textContent = "No documents registered for this matter yet.";
      list.appendChild(li);
      return;
    }
    documents.forEach((doc) => {
      const li = document.createElement("li");
      const actor = doc.created_by ? ` · by ${doc.created_by}` : "";
      const klass = doc.classification ? ` · ${doc.classification}` : "";
      const hash = doc.content_hash ? ` · hash ${String(doc.content_hash).slice(0, 10)}…` : "";
      li.textContent =
        `${doc.filename} (${doc.doc_type || "general"})${klass}` +
        ` · ${doc.custody_source || "manual_register"}${hash}${actor}`;
      list.appendChild(li);
    });
  }

  function fillCaseCardFields(matter) {
    const { caseNumber, issues } = panelEls();
    if (caseNumber) caseNumber.value = matter?.case_number || "";
    if (issues) {
      issues.value = Array.isArray(matter?.issues) ? matter.issues.join("\n") : "";
    }
  }

  async function loadMatters() {
    const { panel } = panelEls();
    if (!getAccessToken()) {
      if (panel) panel.hidden = true;
      matters = [];
      documents = [];
      return;
    }
    if (panel) panel.hidden = false;
    renderEmptyCopy();
    try {
      const result = await apiRequest(appKey, "/api/v1/legal/matters?limit=50", {
        method: "GET",
        timeoutMs: 12000,
      });
      matters = result?.ok ? result.payload?.items || [] : [];
    } catch (_error) {
      matters = [];
    }
    renderMatterOptions();
    if (selectedMatterId) {
      await loadDocumentsForMatter(selectedMatterId);
    } else {
      documents = [];
      renderDocumentList();
      fillCaseCardFields(null);
    }
  }

  async function loadDocumentsForMatter(matterId) {
    selectedMatterId = matterId || "";
    const matter = matters.find((m) => m.matter_id === selectedMatterId);
    fillCaseCardFields(matter || null);
    if (!selectedMatterId || !getAccessToken()) {
      documents = [];
      renderDocumentList();
      return;
    }
    setStatus("Loading register…");
    try {
      const result = await apiRequest(
        appKey,
        `/api/v1/legal/matters/${encodeURIComponent(selectedMatterId)}/documents?limit=50`,
        { method: "GET", timeoutMs: 12000 }
      );
      documents = result?.ok ? result.payload?.items || [] : [];
      setStatus(documents.length ? `${documents.length} registered document(s).` : "Register is empty.");
    } catch (_error) {
      documents = [];
      setStatus("Could not load document register.");
    }
    renderDocumentList();
  }

  async function saveCaseCard() {
    if (!selectedMatterId || !getAccessToken()) return;
    const { caseNumber, issues } = panelEls();
    const issueLines = String(issues?.value || "")
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .slice(0, 40);
    setStatus("Saving case card…");
    try {
      const result = await apiRequest(
        appKey,
        `/api/v1/legal/matters/${encodeURIComponent(selectedMatterId)}`,
        {
          method: "PATCH",
          timeoutMs: 12000,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            case_number: String(caseNumber?.value || "").trim() || null,
            issues: issueLines,
          }),
        }
      );
      if (!result?.ok) {
        const detail = result?.payload?.detail;
        throw new Error(
          Array.isArray(detail)
            ? detail.map((d) => d.msg || d).join("; ")
            : detail || "Could not save case card"
        );
      }
      const updated = result.payload;
      matters = matters.map((m) => (m.matter_id === selectedMatterId ? { ...m, ...updated } : m));
      fillCaseCardFields(updated);
      setStatus("Case card saved (case number / issues).");
    } catch (error) {
      setStatus(error?.message || "Could not save case card.");
    }
  }

  async function registerDocument(event) {
    event?.preventDefault?.();
    if (!selectedMatterId || !getAccessToken()) {
      setStatus("Select a live matter first.");
      return;
    }
    const form = document.getElementById("document-register-form");
    if (!form) return;
    const filename = String(form.filename?.value || "").trim();
    const docType = String(form.doc_type?.value || "general").trim() || "general";
    const notes = String(form.notes?.value || "").trim();
    const storageRef = String(form.storage_ref?.value || "").trim();
    const contentHash = String(form.content_hash?.value || "").trim();
    const classification = String(form.classification?.value || "").trim();
    if (!filename) {
      setStatus("Filename is required.");
      return;
    }
    setStatus("Registering document…");
    try {
      const result = await apiRequest(
        appKey,
        `/api/v1/legal/matters/${encodeURIComponent(selectedMatterId)}/documents`,
        {
          method: "POST",
          timeoutMs: 12000,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            filename,
            doc_type: docType,
            notes: notes || null,
            storage_ref: storageRef || null,
            content_hash: contentHash || null,
            classification: classification || null,
            custody_source: "manual_register",
          }),
        }
      );
      if (!result?.ok) {
        const detail = result?.payload?.detail;
        throw new Error(
          Array.isArray(detail)
            ? detail.map((d) => d.msg || d).join("; ")
            : detail || "Could not register document"
        );
      }
      form.reset();
      await loadDocumentsForMatter(selectedMatterId);
      setStatus(`Registered ${result.payload?.filename || filename}.`);
    } catch (error) {
      setStatus(error?.message || "Could not register document.");
    }
  }

  function bindEvents() {
    const els = panelEls();
    els.matterSelect?.addEventListener("change", () => {
      loadDocumentsForMatter(els.matterSelect.value);
    });
    els.form?.addEventListener("submit", registerDocument);
    els.saveCaseCard?.addEventListener("click", () => {
      saveCaseCard();
    });
  }

  return {
    loadMatters,
    renderEmptyCopy,
    bindEvents,
  };
}
