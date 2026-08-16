/* LegalMitra Tracker — Stage 3 practice ops: clients, matters, briefs, persona filters */

const PERSONA_PRACTICE_AREAS = {
  advocate: new Set(["litigation", "contract", "advisory", "general", "compliance"]),
  ca: new Set(["gst", "income_tax", "advisory", "compliance", "general"]),
  cs: new Set(["secretarial", "compliance", "advisory", "general", "contract"]),
};

const BRIEF_SECTION_ORDER = [
  ["matter_overview", "Matter Overview"],
  ["key_facts", "Key Facts"],
  ["applicable_law", "Applicable Law"],
  ["important_dates", "Important Dates"],
  ["documents_reviewed", "Documents Reviewed"],
  ["current_status", "Current Status"],
  ["risks", "Risks"],
  ["suggested_next_actions", "Suggested Next Actions"],
  ["limitations", "Limitations"],
];

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatList(items) {
  if (!Array.isArray(items) || !items.length) return "<em>None recorded</em>";
  return `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

export function practiceAreasForPersona(role) {
  return PERSONA_PRACTICE_AREAS[role] || PERSONA_PRACTICE_AREAS.advocate;
}

export function matterMatchesPersona(matter, role) {
  if (!matter) return false;
  const areas = practiceAreasForPersona(role);
  const area = String(matter.practice_area || "general").trim().toLowerCase() || "general";
  return areas.has(area);
}

export function filterDashboardByPersona(livePractice, role) {
  if (!livePractice) return null;
  const filterItems = (items) =>
    (items || []).filter((item) => matterMatchesPersona(item, role));
  return {
    ...livePractice,
    upcoming_hearings: filterItems(livePractice.upcoming_hearings),
    upcoming_deadlines: filterItems(livePractice.upcoming_deadlines),
    recent_briefs: filterItems(livePractice.recent_briefs),
    recent_documents: filterItems(livePractice.recent_documents),
  };
}

export function createPracticeWorkspaceController({
  apiRequest,
  getAccessToken,
  appKey,
  getLivePractice,
  getCurrentRole,
  onPracticeMutated,
}) {
  let selectedMatterId = "";
  let clientsCache = [];
  let mattersCache = [];

  function els() {
    return {
      panel: document.getElementById("practice-ops-panel"),
      clientForm: document.getElementById("practice-client-form"),
      matterForm: document.getElementById("practice-matter-form"),
      clientSelect: document.getElementById("practice-matter-client"),
      status: document.getElementById("practice-ops-status"),
      widgets: document.getElementById("practice-live-widgets"),
      briefPanel: document.getElementById("matter-brief-panel"),
      briefTitle: document.getElementById("matter-brief-title"),
      briefMeta: document.getElementById("matter-brief-meta"),
      briefBody: document.getElementById("matter-brief-body"),
      briefStatus: document.getElementById("matter-brief-status"),
      briefGenerate: document.getElementById("matter-brief-generate"),
      briefMatterSelect: document.getElementById("matter-brief-matter"),
      addRowButton: document.getElementById("tracker-add-row"),
    };
  }

  function setStatus(message) {
    const { status } = els();
    if (status) status.textContent = message || "";
  }

  function setBriefStatus(message) {
    const { briefStatus } = els();
    if (briefStatus) briefStatus.textContent = message || "";
  }

  function showSignedInPanels(visible) {
    const { panel, briefPanel, widgets } = els();
    if (panel) panel.hidden = !visible;
    if (briefPanel) briefPanel.hidden = !visible;
    if (widgets) widgets.hidden = !visible;
    const { addRowButton } = els();
    if (addRowButton) {
      addRowButton.textContent = visible ? "+ New matter" : "+ Log Engagement";
    }
  }

  function renderClientOptions() {
    const { clientSelect, briefMatterSelect } = els();
    if (clientSelect) {
      const previous = clientSelect.value;
      clientSelect.textContent = "";
      const placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = clientsCache.length ? "Select client…" : "Create a client first";
      clientSelect.appendChild(placeholder);
      clientsCache.forEach((client) => {
        const option = document.createElement("option");
        option.value = client.client_id;
        option.textContent = client.display_name || client.client_id;
        clientSelect.appendChild(option);
      });
      if (previous && clientsCache.some((c) => c.client_id === previous)) {
        clientSelect.value = previous;
      }
    }
    if (briefMatterSelect) {
      const previous = selectedMatterId || briefMatterSelect.value;
      briefMatterSelect.textContent = "";
      const placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = mattersCache.length ? "Select matter…" : "No matters yet";
      briefMatterSelect.appendChild(placeholder);
      const role = getCurrentRole?.() || "advocate";
      mattersCache
        .filter((m) => matterMatchesPersona(m, role))
        .forEach((matter) => {
          const option = document.createElement("option");
          option.value = matter.matter_id;
          option.textContent = `${matter.matter_number || matter.matter_id} · ${matter.title || "Matter"}`;
          briefMatterSelect.appendChild(option);
        });
      if (previous && mattersCache.some((m) => m.matter_id === previous)) {
        briefMatterSelect.value = previous;
        selectedMatterId = previous;
      }
    }
  }

  function renderLiveWidgets() {
    const { widgets } = els();
    if (!widgets) return;
    const live = filterDashboardByPersona(getLivePractice?.(), getCurrentRole?.() || "advocate");
    if (!live) {
      widgets.innerHTML =
        "<p class=\"legal-practice-widget-empty\">Sign in to load live clients, matters awaiting review, briefs, and documents.</p>";
      return;
    }
    const awaiting = live.awaiting_review ?? 0;
    const clients = (live.recent_clients || [])
      .slice(0, 4)
      .map((c) => escapeHtml(c.display_name || c.client_id))
      .join(", ");
    const briefs = (live.recent_briefs || [])
      .slice(0, 3)
      .map((b) => escapeHtml(b.matter_number || b.matter_id || "Brief"))
      .join(", ");
    const docs = (live.recent_documents || [])
      .slice(0, 3)
      .map((d) => escapeHtml(d.filename || d.document_id || "Document"))
      .join(", ");
    widgets.innerHTML = `
      <article><span>Awaiting review</span><strong>${escapeHtml(String(awaiting))}</strong></article>
      <article><span>Recent clients</span><strong>${clients || "—"}</strong></article>
      <article><span>AI matter briefs</span><strong>${briefs || "—"}</strong></article>
      <article><span>Recent documents</span><strong>${docs || "—"}</strong></article>
    `;
  }

  function renderBrief(brief) {
    const { briefTitle, briefMeta, briefBody } = els();
    if (!brief) {
      if (briefTitle) briefTitle.textContent = "Matter Intelligence Brief";
      if (briefMeta) briefMeta.textContent = "Open a matter to generate or load a grounded brief.";
      if (briefBody) briefBody.innerHTML = "";
      return;
    }
    const sections = brief.sections || {};
    if (briefTitle) {
      briefTitle.textContent = `Brief · ${brief.matter_number || brief.matter_id || "Matter"}`;
    }
    if (briefMeta) {
      const confidence =
        sections.confidence == null ? "—" : String(sections.confidence);
      briefMeta.textContent = [
        brief.advisory_notice || "Advisory working summary — not final legal advice.",
        `Human review required: ${sections.human_review_required === false ? "no" : "yes"}`,
        `Confidence: ${confidence}`,
        brief.generation_strategy ? `Strategy: ${brief.generation_strategy}` : "",
      ]
        .filter(Boolean)
        .join(" · ");
    }
    if (briefBody) {
      const blocks = BRIEF_SECTION_ORDER.map(([key, label]) => {
        const value = sections[key];
        let body;
        if (Array.isArray(value)) body = formatList(value);
        else if (value == null || value === "") body = "<em>Not available</em>";
        else body = `<p>${escapeHtml(value)}</p>`;
        return `<section class="legal-matter-brief-section"><h3>${escapeHtml(label)}</h3>${body}</section>`;
      }).join("");
      briefBody.innerHTML = blocks;
    }
  }

  async function refreshClientsAndMatters() {
    if (!getAccessToken()) {
      clientsCache = [];
      mattersCache = [];
      showSignedInPanels(false);
      renderClientOptions();
      renderLiveWidgets();
      renderBrief(null);
      return;
    }
    showSignedInPanels(true);
    try {
      const [clientsRes, mattersRes] = await Promise.all([
        apiRequest(appKey, "/api/v1/legal/clients?limit=50", { method: "GET", timeoutMs: 12000 }),
        apiRequest(appKey, "/api/v1/legal/matters?limit=50", { method: "GET", timeoutMs: 12000 }),
      ]);
      clientsCache = clientsRes?.ok ? clientsRes.payload?.items || [] : [];
      mattersCache = mattersRes?.ok ? mattersRes.payload?.items || [] : [];
    } catch (_error) {
      clientsCache = [];
      mattersCache = [];
    }
    renderClientOptions();
    renderLiveWidgets();
  }

  async function loadBriefForMatter(matterId, { generate = false } = {}) {
    if (!matterId || !getAccessToken()) {
      setBriefStatus("Select a live matter first.");
      return;
    }
    selectedMatterId = matterId;
    const { briefMatterSelect } = els();
    if (briefMatterSelect) briefMatterSelect.value = matterId;
    setBriefStatus(generate ? "Generating grounded brief…" : "Loading latest brief…");
    const path = `/api/v1/legal/matters/${encodeURIComponent(matterId)}/brief`;
    try {
      const result = await apiRequest(appKey, path, {
        method: generate ? "POST" : "GET",
        timeoutMs: 25000,
        body: generate ? JSON.stringify({}) : undefined,
      });
      if (!result?.ok) {
        if (!generate && result?.status === 404) {
          setBriefStatus("No brief yet — generate one from this matter’s records.");
          renderBrief(null);
          return;
        }
        setBriefStatus(`Could not load brief (${result?.status || "error"}).`);
        return;
      }
      renderBrief(result.payload);
      setBriefStatus(generate ? "Brief generated from matter data. Human review required." : "Showing latest saved brief.");
      if (generate) await onPracticeMutated?.();
    } catch (_error) {
      setBriefStatus("Brief request failed. Try again.");
    }
  }

  async function handleCreateClient(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const payload = {
      display_name: String(data.get("display_name") || "").trim(),
      client_type: String(data.get("client_type") || "organization"),
      email: String(data.get("email") || "").trim() || null,
      phone: String(data.get("phone") || "").trim() || null,
      pan: String(data.get("pan") || "").trim() || null,
      gstin: String(data.get("gstin") || "").trim() || null,
    };
    if (payload.display_name.length < 2) {
      setStatus("Client name is required.");
      return;
    }
    setStatus("Creating client…");
    const result = await apiRequest(appKey, "/api/v1/legal/clients", {
      method: "POST",
      timeoutMs: 15000,
      body: JSON.stringify(payload),
    });
    if (!result?.ok) {
      setStatus(`Could not create client (${result?.status || "error"}).`);
      return;
    }
    form.reset();
    setStatus(`Client saved: ${result.payload.display_name}`);
    await refreshClientsAndMatters();
    await onPracticeMutated?.();
  }

  async function handleCreateMatter(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const payload = {
      client_id: String(data.get("client_id") || "").trim(),
      title: String(data.get("title") || "").trim(),
      practice_area: String(data.get("practice_area") || "general").trim(),
      matter_type: String(data.get("matter_type") || "engagement").trim(),
      status: String(data.get("status") || "draft").trim(),
      court: String(data.get("court") || "").trim() || null,
      next_hearing_date: String(data.get("next_hearing_date") || "").trim() || null,
      next_deadline_date: String(data.get("next_deadline_date") || "").trim() || null,
    };
    if (!payload.client_id || payload.title.length < 3) {
      setStatus("Client and matter title are required.");
      return;
    }
    setStatus("Creating matter…");
    const result = await apiRequest(appKey, "/api/v1/legal/matters", {
      method: "POST",
      timeoutMs: 15000,
      body: JSON.stringify(payload),
    });
    if (!result?.ok) {
      setStatus(`Could not create matter (${result?.status || "error"}).`);
      return;
    }
    form.reset();
    selectedMatterId = result.payload.matter_id;
    setStatus(`Matter ${result.payload.matter_number} created.`);
    await refreshClientsAndMatters();
    await onPracticeMutated?.();
    await loadBriefForMatter(selectedMatterId, { generate: false });
  }

  function bindEvents() {
    const {
      clientForm,
      matterForm,
      briefGenerate,
      briefMatterSelect,
    } = els();
    clientForm?.addEventListener("submit", handleCreateClient);
    matterForm?.addEventListener("submit", handleCreateMatter);
    briefGenerate?.addEventListener("click", () => {
      const matterId = briefMatterSelect?.value || selectedMatterId;
      loadBriefForMatter(matterId, { generate: true });
    });
    briefMatterSelect?.addEventListener("change", () => {
      const matterId = briefMatterSelect.value;
      if (matterId) loadBriefForMatter(matterId, { generate: false });
    });
  }

  function openNewMatterForm() {
    const { matterForm, panel } = els();
    if (panel) {
      panel.hidden = false;
      panel.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    matterForm?.querySelector('[name="title"]')?.focus();
  }

  return {
    bindEvents,
    refreshClientsAndMatters,
    renderLiveWidgets,
    loadBriefForMatter,
    openNewMatterForm,
    showSignedInPanels,
    getMattersCache: () => mattersCache,
    openMatterActInPlace: async (matterId, focus = "matter-brief") => {
      if (!matterId || !getAccessToken()) return;
      selectedMatterId = matterId;
      const { briefPanel, briefMatterSelect } = els();
      if (briefMatterSelect) briefMatterSelect.value = matterId;
      if (focus === "document-register") {
        // Document register selection is handled by caller via selectMatter.
        return;
      }
      if (briefPanel) {
        briefPanel.hidden = false;
        briefPanel.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      await loadBriefForMatter(matterId, { generate: false });
    },
  };
}
