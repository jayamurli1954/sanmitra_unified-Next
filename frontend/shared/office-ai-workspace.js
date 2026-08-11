// OfficeMitra AI workspace — Phase 1 + Phase 2 productivity tabs.
// Advisory AI only; figures come from connectors / user paste.

/** @type {Record<string, any> | null} */
let deps = null;

const state = {
  tab: "tasks", // tasks | email | brief | calendar | notes | notifications | proposals | workflows
  tasks: [],
  emails: [],
  brief: null,
  events: [],
  notes: [],
  notifications: [],
  proposals: [],
  workflowTemplates: [],
  workflowRuns: [],
  writebackEnabled: false,
  workflowsEnabled: false,
  unreadCount: 0,
  error: "",
  notice: "",
  loading: false,
  draftText: "",
  emailText: "",
  calendarText: "",
  notesText: "",
  workflowName: "Daily follow-up",
  workflowIdempotencyKey: "",
};

export function initOfficeAiWorkspace(injected) {
  deps = injected;
  const preview = injected?.dashboardPreview;
  if (preview && !preview.dataset.officeAiBound) {
    preview.dataset.officeAiBound = "1";
    preview.addEventListener("click", async (event) => {
      const button = event.target.closest("[data-office-ai-action]");
      if (!button) return;
      event.preventDefault();
      await handleOfficeAiAction(button.getAttribute("data-office-ai-action"), button);
    });
  }
}

function requireDeps() {
  if (!deps) {
    throw new Error("initOfficeAiWorkspace() must be called before use");
  }
  return deps;
}

function escapeHtml(value) {
  return requireDeps().escapeHtml(value);
}

function resolveAppKey() {
  return String(requireDeps().appKey || "mitrabooks").trim() || "mitrabooks";
}

function apiRequest(path, options) {
  return requireDeps().apiRequest(resolveAppKey(), path, options);
}

function unwrap(result) {
  if (!result?.ok) {
    const detail = result?.payload?.detail;
    throw new Error(typeof detail === "string" ? detail : "OfficeMitra AI request failed");
  }
  return result.payload || {};
}

export function getOfficeAiUi() {
  return state;
}

export function setOfficeAiTab(tab) {
  state.tab = tab;
}

function taskRecordId(task) {
  return String(task?.id || task?._id || task?.task_id || "").trim();
}

function formatTaskStatus(status) {
  const key = String(status || "open").toLowerCase();
  if (key === "done") return "Done";
  if (key === "cancelled") return "Cancelled";
  return "Open";
}

function normalizeTasks(items) {
  return (items || []).map((task) => ({
    ...task,
    id: taskRecordId(task),
    status: String(task?.status || "open").toLowerCase(),
  }));
}

function syncPasteFields(el) {
  const root = el?.closest?.("[data-office-ai-root]");
  if (!root) return;
  const draft = root.querySelector("[data-office-ai-field='draftText']");
  const email = root.querySelector("[data-office-ai-field='emailText']");
  const calendar = root.querySelector("[data-office-ai-field='calendarText']");
  const notes = root.querySelector("[data-office-ai-field='notesText']");
  const workflowName = root.querySelector("[data-office-ai-field='workflowName']");
  const workflowKey = root.querySelector("[data-office-ai-field='workflowIdempotencyKey']");
  if (draft) state.draftText = draft.value || "";
  if (email) state.emailText = email.value || "";
  if (calendar) state.calendarText = calendar.value || "";
  if (notes) state.notesText = notes.value || "";
  if (workflowName) state.workflowName = workflowName.value || "";
  if (workflowKey) state.workflowIdempotencyKey = workflowKey.value || "";
}

function advisoryBanner() {
  return `<p class="muted" style="margin:0.5rem 0 0;">Advisory only — not final legal or financial advice. Review before acting.</p>`;
}

export function renderOfficeAiWorkspace() {
  const unread = Number(state.unreadCount || 0);
  const pendingProposals = (state.proposals || []).filter((p) => {
    const s = String(p.status || "");
    return s === "pending" || s === "awaiting_checker";
  }).length;
  const notifLabel = unread > 0 ? `Notifications (${unread})` : "Notifications";
  const proposalLabel = pendingProposals > 0 ? `Proposals (${pendingProposals})` : "Proposals";
  const tabs = [
    ["tasks", "Tasks"],
    ["email", "Email Summary"],
    ["calendar", "Calendar"],
    ["notes", "Meeting Notes"],
    ["notifications", notifLabel],
    ["brief", "Today Brief"],
  ];
  if (state.writebackEnabled) {
    tabs.splice(1, 0, ["proposals", proposalLabel]);
  }
  if (state.workflowsEnabled) {
    const insertAt = state.writebackEnabled ? 2 : 1;
    tabs.splice(insertAt, 0, ["workflows", "Workflows"]);
  }
  const tabButtons = tabs
    .map(([id, label]) => {
      const active = state.tab === id ? "primary" : "secondary";
      return `<button class="${active}" type="button" data-office-ai-action="tab" data-tab="${id}">${label}</button>`;
    })
    .join(" ");

  let body = "";
  if (state.tab === "tasks") body = renderTasksPanel();
  else if (state.tab === "proposals") body = renderProposalsPanel();
  else if (state.tab === "workflows") body = renderWorkflowsPanel();
  else if (state.tab === "email") body = renderEmailPanel();
  else if (state.tab === "calendar") body = renderCalendarPanel();
  else if (state.tab === "notes") body = renderNotesPanel();
  else if (state.tab === "notifications") body = renderNotificationsPanel();
  else body = renderBriefPanel();

  return `
    <div class="verification-panel erp-workspace-panel" data-office-ai-root="1">
      <div class="preview-heading compact">
        <div>
          <h4>OfficeMitra AI</h4>
          <p>Tasks, email, calendar paste, meeting notes, notifications, and daily brief.</p>
          ${advisoryBanner()}
          ${state.writebackEnabled
            ? `<p class="muted" style="margin:0.35rem 0 0;">Write-back enabled: AI suggestions become proposals until you confirm.</p>`
            : ""}
          ${state.workflowsEnabled
            ? `<p class="muted" style="margin:0.35rem 0 0;">Workflows enabled: multi-step OfficeMitra actions via Action Executor (ADR-009).</p>`
            : ""}
        </div>
        <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">${tabButtons}</div>
      </div>
      ${state.error ? `<p class="error">${escapeHtml(state.error)}</p>` : ""}
      ${state.notice ? `<p class="muted">${escapeHtml(state.notice)}</p>` : ""}
      ${state.loading ? `<p class="muted">Working…</p>` : ""}
      ${body}
    </div>
  `;
}

function renderTasksPanel() {
  const rows = (state.tasks || [])
    .map((task) => {
      const taskId = taskRecordId(task);
      const source = task.source === "ai" ? "AI" : "Manual";
      const status = String(task.status || "open").toLowerCase();
      const actionCell = status === "open" && taskId
        ? `<button class="secondary" type="button" data-office-ai-action="complete-task" data-task-id="${escapeHtml(taskId)}">Done</button>`
        : `<span class="muted">${status === "open" ? "—" : "Completed"}</span>`;
      return `<tr>
        <td>${escapeHtml(task.title || "")}</td>
        <td>${escapeHtml(formatTaskStatus(status))}</td>
        <td>${escapeHtml(source)}</td>
        <td class="office-ai-task-action">${actionCell}</td>
      </tr>`;
    })
    .join("");
  return `
    <div class="stack-form">
      <label>Create or generate tasks
        <textarea data-office-ai-field="draftText" rows="4" placeholder="Paste notes or instructions…">${escapeHtml(state.draftText || "")}</textarea>
      </label>
      <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
        <button class="secondary" type="button" data-office-ai-action="create-task">Save as task</button>
        <button class="primary" type="button" data-office-ai-action="generate-tasks">Generate with AI</button>
        <button class="secondary" type="button" data-office-ai-action="refresh-tasks">Refresh</button>
      </div>
      <table class="data-table">
        <thead><tr><th>Title</th><th>Status</th><th>Source</th><th></th></tr></thead>
        <tbody>${rows || `<tr><td colspan="4" class="muted">No tasks yet.</td></tr>`}</tbody>
      </table>
    </div>
  `;
}

function renderProposalsPanel() {
  const rows = (state.proposals || [])
    .map((proposal) => {
      const id = String(proposal.id || "").trim();
      const status = String(proposal.status || "pending").toLowerCase();
      const title = proposal?.payload?.title || proposal?.action_type || "(proposal)";
      const confidence = proposal.confidence == null ? "—" : String(proposal.confidence);
      let actions = `<span class="muted">${escapeHtml(status)}</span>`;
      if (status === "pending" && id) {
        actions = `<button class="primary" type="button" data-office-ai-action="confirm-proposal" data-proposal-id="${escapeHtml(id)}">Confirm</button>
           <button class="secondary" type="button" data-office-ai-action="dismiss-proposal" data-proposal-id="${escapeHtml(id)}">Dismiss</button>`;
      } else if (status === "awaiting_checker" && id) {
        actions = `<button class="primary" type="button" data-office-ai-action="approve-proposal" data-proposal-id="${escapeHtml(id)}">Approve (checker)</button>
           <button class="secondary" type="button" data-office-ai-action="dismiss-proposal" data-proposal-id="${escapeHtml(id)}">Dismiss</button>`;
      }
      return `<tr>
        <td>${escapeHtml(title)}</td>
        <td>${escapeHtml(proposal.action_type || "")}</td>
        <td>${escapeHtml(confidence)}</td>
        <td>${escapeHtml(status)}</td>
        <td style="display:flex;gap:0.35rem;flex-wrap:wrap;">${actions}</td>
      </tr>`;
    })
    .join("");
  return `
    <div class="stack-form">
      <p class="muted">Pending AI proposals require policy-gated confirmation before any OfficeMitra write (ADR-008/012). Maker ≠ checker when maker-checker is required.</p>
      <button class="secondary" type="button" data-office-ai-action="refresh-proposals">Refresh proposals</button>
      <table class="data-table">
        <thead><tr><th>Summary</th><th>Action</th><th>Confidence</th><th>Status</th><th></th></tr></thead>
        <tbody>${rows || `<tr><td colspan="5" class="muted">No proposals yet. Generate tasks with write-back enabled.</td></tr>`}</tbody>
      </table>
    </div>
  `;
}

function renderWorkflowsPanel() {
  const templates = (state.workflowTemplates || [])
    .map((tpl) => {
      const id = String(tpl.id || "").trim();
      const steps = Array.isArray(tpl.steps) ? tpl.steps.length : 0;
      return `<tr>
        <td>${escapeHtml(tpl.name || tpl.template_key || "")}</td>
        <td>v${escapeHtml(String(tpl.version ?? ""))}</td>
        <td>${escapeHtml(String(steps))}</td>
        <td>${tpl.continue_on_failure ? "continue" : "stop"}</td>
        <td>${id
          ? `<button class="primary" type="button" data-office-ai-action="start-workflow" data-template-id="${escapeHtml(id)}">Start run</button>`
          : "—"}</td>
      </tr>`;
    })
    .join("");
  const runs = (state.workflowRuns || [])
    .map((run) => {
      const results = Array.isArray(run.step_results) ? run.step_results : [];
      const diag = results
        .map((s) => `${s.step_id || "?"}:${s.status || "?"} ${s.duration_ms != null ? `${s.duration_ms}ms` : ""}`)
        .join("; ");
      return `<tr>
        <td>${escapeHtml(run.template_key || run.template_id || "")}</td>
        <td>${escapeHtml(run.trigger_source || "")}</td>
        <td>${escapeHtml(run.status || "")}</td>
        <td>${escapeHtml(run.idempotency_key || "—")}</td>
        <td class="muted">${escapeHtml(diag || "—")}</td>
      </tr>`;
    })
    .join("");
  return `
    <div class="stack-form">
      <p class="muted">Templates are reusable; each Start creates a run with step diagnostics (ADR-009). Default stop-on-failure.</p>
      <label>Template name
        <input data-office-ai-field="workflowName" value="${escapeHtml(state.workflowName || "Daily follow-up")}" />
      </label>
      <label>Idempotency key (optional)
        <input data-office-ai-field="workflowIdempotencyKey" placeholder="tenant-taskfollowup-20260811" value="${escapeHtml(state.workflowIdempotencyKey || "")}" />
      </label>
      <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
        <button class="primary" type="button" data-office-ai-action="create-workflow-template">Create sample template</button>
        <button class="secondary" type="button" data-office-ai-action="refresh-workflows">Refresh</button>
      </div>
      <h5 style="margin:1rem 0 0.35rem;">Templates</h5>
      <table class="data-table">
        <thead><tr><th>Name</th><th>Version</th><th>Steps</th><th>On fail</th><th></th></tr></thead>
        <tbody>${templates || `<tr><td colspan="5" class="muted">No templates yet.</td></tr>`}</tbody>
      </table>
      <h5 style="margin:1rem 0 0.35rem;">Recent runs</h5>
      <table class="data-table">
        <thead><tr><th>Template</th><th>Trigger</th><th>Status</th><th>Idempotency</th><th>Steps</th></tr></thead>
        <tbody>${runs || `<tr><td colspan="5" class="muted">No runs yet.</td></tr>`}</tbody>
      </table>
    </div>
  `;
}

function renderEmailPanel() {
  return `
    <div class="stack-form">
      <label>Paste email
        <textarea data-office-ai-field="emailText" rows="8" placeholder="Paste the full email text…">${escapeHtml(state.emailText || "")}</textarea>
      </label>
      <button class="primary" type="button" data-office-ai-action="summarize-email">Summarize + suggest tasks</button>
      <div class="muted">Recent summaries: ${(state.emails || []).length}</div>
      <ul>
        ${(state.emails || [])
          .slice(0, 5)
          .map((email) => `<li>${escapeHtml(email.summary || "(no summary)")}</li>`)
          .join("")}
      </ul>
    </div>
  `;
}

function renderCalendarPanel() {
  const rows = (state.events || [])
    .map((ev) => `<tr>
      <td>${escapeHtml(ev.title || "")}</td>
      <td>${escapeHtml(ev.starts_at || "")}</td>
      <td>${escapeHtml(ev.location || "—")}</td>
      <td>${escapeHtml(ev.source || "")}</td>
    </tr>`)
    .join("");
  return `
    <div class="stack-form">
      <label>Paste calendar / agenda (ICS or lines like "10:00 Client review")
        <textarea data-office-ai-field="calendarText" rows="8" placeholder="Paste ICS or agenda lines…">${escapeHtml(state.calendarText || "")}</textarea>
      </label>
      <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
        <button class="primary" type="button" data-office-ai-action="parse-calendar">Parse + save events</button>
        <button class="secondary" type="button" data-office-ai-action="refresh-calendar">Refresh today</button>
      </div>
      <h5>Today’s events</h5>
      <table class="data-table">
        <thead><tr><th>Title</th><th>Starts</th><th>Location</th><th>Source</th></tr></thead>
        <tbody>${rows || `<tr><td colspan="4" class="muted">No events for today.</td></tr>`}</tbody>
      </table>
    </div>
  `;
}

function renderNotesPanel() {
  return `
    <div class="stack-form">
      <label>Paste meeting notes
        <textarea data-office-ai-field="notesText" rows="8" placeholder="Paste meeting notes…">${escapeHtml(state.notesText || "")}</textarea>
      </label>
      <button class="primary" type="button" data-office-ai-action="summarize-notes">Summarize + suggest tasks</button>
      <div class="muted">Recent notes: ${(state.notes || []).length}</div>
      <ul>
        ${(state.notes || [])
          .slice(0, 5)
          .map((note) => `<li>${escapeHtml(note.summary || "(no summary)")}</li>`)
          .join("")}
      </ul>
    </div>
  `;
}

function renderNotificationsPanel() {
  const rows = (state.notifications || [])
    .map((n) => {
      const id = String(n.id || "").trim();
      const read = !!n.read_at;
      return `<tr>
        <td>${escapeHtml(n.title || "")}</td>
        <td>${escapeHtml(n.kind || "")}</td>
        <td>${escapeHtml(n.created_at || "")}</td>
        <td>${read
          ? `<span class="muted">Read</span>`
          : `<button class="secondary" type="button" data-office-ai-action="mark-notification-read" data-notification-id="${escapeHtml(id)}">Mark read</button>`}
        </td>
      </tr>`;
    })
    .join("");
  return `
    <div class="stack-form">
      <div style="display:flex;gap:0.5rem;flex-wrap:wrap;align-items:center;">
        <button class="secondary" type="button" data-office-ai-action="refresh-notifications">Refresh</button>
        <span class="muted">Unread: ${escapeHtml(String(state.unreadCount || 0))}</span>
      </div>
      <table class="data-table">
        <thead><tr><th>Title</th><th>Kind</th><th>Created</th><th></th></tr></thead>
        <tbody>${rows || `<tr><td colspan="4" class="muted">No notifications yet.</td></tr>`}</tbody>
      </table>
    </div>
  `;
}

function renderBriefPanel() {
  const brief = state.brief || {};
  return `
    <div class="stack-form">
      <button class="primary" type="button" data-office-ai-action="generate-brief">Generate today’s brief</button>
      <button class="secondary" type="button" data-office-ai-action="refresh-brief">Load latest</button>
      ${brief.content
        ? `<pre class="code-block" style="white-space:pre-wrap;">${escapeHtml(brief.content)}</pre>
           <p class="muted">generation_id=${escapeHtml(brief.generation_id || "")} · prompt=${escapeHtml(brief.prompt_version || "")}</p>`
        : `<p class="muted">No brief generated yet for today.</p>`}
    </div>
  `;
}

function shouldRenderIntoPreview() {
  const d = requireDeps();
  if (typeof d.getActiveBusinessWorkspace === "function") {
    return d.getActiveBusinessWorkspace() === "office-ai";
  }
  // Standalone OfficeMitra shell owns the preview root full-time.
  return true;
}

function rerender() {
  const preview = requireDeps().dashboardPreview;
  if (preview && shouldRenderIntoPreview()) {
    preview.innerHTML = renderOfficeAiWorkspace();
  }
}

async function refreshTasks() {
  const payload = unwrap(await apiRequest("/api/v1/officemitra/tasks"));
  state.tasks = normalizeTasks(payload.items);
}

async function refreshEmails() {
  const payload = unwrap(await apiRequest("/api/v1/officemitra/emails"));
  state.emails = payload.items || [];
}

async function refreshBrief() {
  const payload = unwrap(await apiRequest("/api/v1/officemitra/briefs/today"));
  state.brief = payload.item || null;
}

async function refreshCalendar() {
  const payload = unwrap(await apiRequest("/api/v1/officemitra/calendar/today"));
  state.events = payload.items || [];
}

async function refreshNotes() {
  const payload = unwrap(await apiRequest("/api/v1/officemitra/meeting-notes"));
  state.notes = payload.items || [];
}

async function refreshNotifications() {
  const payload = unwrap(await apiRequest("/api/v1/officemitra/notifications"));
  state.notifications = payload.items || [];
  state.unreadCount = payload.unread_count || 0;
}

async function refreshWritebackFlag() {
  try {
    const payload = unwrap(await apiRequest("/api/v1/officemitra/ping"));
    state.writebackEnabled = !!payload.writeback_enabled;
    state.workflowsEnabled = !!payload.workflows_enabled;
  } catch (_err) {
    state.writebackEnabled = false;
    state.workflowsEnabled = false;
  }
}

async function refreshProposals() {
  if (!state.writebackEnabled) {
    state.proposals = [];
    return;
  }
  const payload = unwrap(await apiRequest("/api/v1/officemitra/proposals?status=open"));
  state.proposals = payload.items || [];
}

async function refreshWorkflows() {
  if (!state.workflowsEnabled) {
    state.workflowTemplates = [];
    state.workflowRuns = [];
    return;
  }
  const [templates, runs] = await Promise.all([
    unwrap(await apiRequest("/api/v1/officemitra/workflows/templates")),
    unwrap(await apiRequest("/api/v1/officemitra/workflows/runs")),
  ]);
  state.workflowTemplates = templates.items || [];
  state.workflowRuns = runs.items || [];
}

export async function loadOfficeAiWorkspace() {
  state.error = "";
  state.loading = true;
  rerender();
  try {
    await refreshWritebackFlag();
    if (state.tab === "tasks") await refreshTasks();
    else if (state.tab === "proposals") await refreshProposals();
    else if (state.tab === "workflows") await refreshWorkflows();
    else if (state.tab === "email") await refreshEmails();
    else if (state.tab === "calendar") await refreshCalendar();
    else if (state.tab === "notes") await refreshNotes();
    else if (state.tab === "notifications") await refreshNotifications();
    else await refreshBrief();
    // Keep unread badge fresh without blocking primary tab load failure.
    try {
      const n = unwrap(await apiRequest("/api/v1/officemitra/notifications?limit=1"));
      state.unreadCount = n.unread_count || 0;
    } catch (_e) {
      /* optional */
    }
    if (state.writebackEnabled && state.tab !== "proposals") {
      try {
        await refreshProposals();
      } catch (_e) {
        /* optional badge */
      }
    }
  } catch (err) {
    state.error = err?.message || "Failed to load OfficeMitra AI";
  } finally {
    state.loading = false;
    rerender();
  }
}

export async function handleOfficeAiAction(action, el) {
  syncPasteFields(el);

  state.error = "";
  state.notice = "";
  const completeTaskId = action === "complete-task"
    ? String(el?.getAttribute("data-task-id") || el?.dataset?.taskId || "").trim()
    : "";
  const notificationId = action === "mark-notification-read"
    ? String(el?.getAttribute("data-notification-id") || el?.dataset?.notificationId || "").trim()
    : "";
  const proposalId = (action === "confirm-proposal" || action === "dismiss-proposal" || action === "approve-proposal")
    ? String(el?.getAttribute("data-proposal-id") || el?.dataset?.proposalId || "").trim()
    : "";
  const templateId = action === "start-workflow"
    ? String(el?.getAttribute("data-template-id") || el?.dataset?.templateId || "").trim()
    : "";
  try {
    if (action === "tab") {
      state.tab = el?.dataset?.tab || "tasks";
      await loadOfficeAiWorkspace();
      return;
    }
    state.loading = true;
    rerender();
    if (action === "refresh-tasks") {
      await refreshTasks();
    } else if (action === "create-task") {
      const title = (state.draftText || "").trim().split("\n")[0];
      if (!title) throw new Error("Enter a task title");
      unwrap(await apiRequest("/api/v1/officemitra/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      }));
      state.draftText = "";
      state.notice = "Task saved.";
      await refreshTasks();
    } else if (action === "generate-tasks") {
      if (!(state.draftText || "").trim()) throw new Error("Paste text to generate tasks");
      await refreshWritebackFlag();
      const result = unwrap(await apiRequest("/api/v1/officemitra/tasks/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: state.draftText, persist: true }),
      }));
      if (result?.ai_available === false) {
        state.notice = `AI unavailable (${result?.error_code || "offline"}). No tasks generated.`;
      } else if (result?.writeback_enabled) {
        state.notice = `Created ${(result?.proposals || []).length} proposal(s) for review.`;
        state.tab = "proposals";
        await refreshProposals();
      } else {
        state.notice = `Generated ${(result?.saved_tasks || []).length} task(s).`;
        await refreshTasks();
      }
    } else if (action === "refresh-proposals") {
      await refreshProposals();
    } else if (action === "confirm-proposal") {
      if (!proposalId) throw new Error("Missing proposal id");
      const result = unwrap(await apiRequest(`/api/v1/officemitra/proposals/${encodeURIComponent(proposalId)}/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      }));
      const status = result?.proposal?.status || "";
      state.notice = status === "applied"
        ? "Proposal confirmed and applied."
        : status === "awaiting_checker"
          ? "Maker confirmed — waiting for a different checker to approve."
        : status === "failed"
          ? `Proposal failed: ${result?.error || result?.proposal?.error_message || "unknown error"}`
          : "Proposal updated.";
      await refreshProposals();
      await refreshTasks();
    } else if (action === "dismiss-proposal") {
      if (!proposalId) throw new Error("Missing proposal id");
      unwrap(await apiRequest(`/api/v1/officemitra/proposals/${encodeURIComponent(proposalId)}/dismiss`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      }));
      state.notice = "Proposal dismissed.";
      await refreshProposals();
    } else if (action === "approve-proposal") {
      if (!proposalId) throw new Error("Missing proposal id");
      const result = unwrap(await apiRequest(`/api/v1/officemitra/proposals/${encodeURIComponent(proposalId)}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      }));
      const status = result?.proposal?.status || "";
      state.notice = status === "applied"
        ? "Checker approved and applied."
        : status === "failed"
          ? `Approval failed: ${result?.error || result?.proposal?.error_message || "unknown error"}`
          : "Proposal updated.";
      await refreshProposals();
      await refreshTasks();
    } else if (action === "refresh-workflows") {
      await refreshWorkflows();
    } else if (action === "create-workflow-template") {
      const name = (state.workflowName || "Daily follow-up").trim() || "Daily follow-up";
      unwrap(await apiRequest("/api/v1/officemitra/workflows/templates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          description: "Sample: create task then notify",
          continue_on_failure: false,
          steps: [
            {
              step_id: "create-followup-task",
              action_type: "create_task",
              payload: { title: `${name} task`, notes: "Created by workflow" },
            },
            {
              step_id: "notify-owner",
              action_type: "create_notification",
              payload: {
                title: `${name} ready`,
                body: "Workflow completed a follow-up task.",
                kind: "workflow_ready",
              },
            },
          ],
        }),
      }));
      state.notice = "Workflow template created.";
      await refreshWorkflows();
    } else if (action === "start-workflow") {
      if (!templateId) throw new Error("Missing template id");
      const key = (state.workflowIdempotencyKey || "").trim() || undefined;
      const result = unwrap(await apiRequest("/api/v1/officemitra/workflows/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          template_id: templateId,
          trigger_source: "manual",
          idempotency_key: key,
        }),
      }));
      const replay = result?.idempotent_replay ? " (idempotent replay)" : "";
      state.notice = `Workflow run ${result?.run?.status || "finished"}${replay}.`;
      await refreshWorkflows();
      await refreshTasks();
      try {
        await refreshNotifications();
      } catch (_e) {
        /* optional */
      }
    } else if (action === "complete-task") {
      if (!completeTaskId) {
        throw new Error("Could not update task — missing task id. Click Refresh and try again.");
      }
      unwrap(await apiRequest(`/api/v1/officemitra/tasks/${encodeURIComponent(completeTaskId)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "done", change_reason: "Marked done in UI" }),
      }));
      state.notice = "Task marked done.";
      await refreshTasks();
    } else if (action === "summarize-email") {
      if (!(state.emailText || "").trim()) throw new Error("Paste an email first");
      const result = unwrap(await apiRequest("/api/v1/officemitra/emails/summarize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_text: state.emailText, persist: true, create_tasks: true }),
      }));
      state.notice = result?.ai_available === false
        ? `AI unavailable (${result?.error_code || "offline"}).`
        : "Email summarized; suggested tasks saved when available.";
      state.emailText = "";
      state.tab = "email";
      await refreshEmails();
      await refreshTasks();
    } else if (action === "parse-calendar") {
      if (!(state.calendarText || "").trim()) throw new Error("Paste calendar text first");
      const result = unwrap(await apiRequest("/api/v1/officemitra/calendar/parse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_text: state.calendarText, persist: true }),
      }));
      state.notice = `Saved ${(result?.saved_events || []).length} calendar event(s).`;
      state.calendarText = "";
      state.tab = "calendar";
      await refreshCalendar();
      await refreshNotifications();
    } else if (action === "refresh-calendar") {
      await refreshCalendar();
    } else if (action === "summarize-notes") {
      if (!(state.notesText || "").trim()) throw new Error("Paste meeting notes first");
      const result = unwrap(await apiRequest("/api/v1/officemitra/meeting-notes/summarize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_text: state.notesText, persist: true, create_tasks: true }),
      }));
      state.notice = result?.ai_available === false
        ? `AI unavailable (${result?.error_code || "offline"}). Notes saved.`
        : "Meeting notes summarized; suggested tasks saved when available.";
      state.notesText = "";
      state.tab = "notes";
      await refreshNotes();
      await refreshTasks();
      await refreshNotifications();
    } else if (action === "refresh-notifications") {
      await refreshNotifications();
    } else if (action === "mark-notification-read") {
      if (!notificationId) throw new Error("Missing notification id");
      unwrap(await apiRequest(`/api/v1/officemitra/notifications/${encodeURIComponent(notificationId)}/read`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      }));
      state.notice = "Notification marked read.";
      await refreshNotifications();
    } else if (action === "generate-brief") {
      const result = unwrap(await apiRequest("/api/v1/officemitra/briefs/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          include_tasks: true,
          include_emails: true,
          include_calendar: true,
          include_meeting_notes: true,
        }),
      }));
      state.brief = result?.brief || null;
      state.notice = result?.ai_available === false
        ? "Brief saved with deterministic fallback (AI unavailable)."
        : "Brief generated.";
      await refreshNotifications();
    } else if (action === "refresh-brief") {
      await refreshBrief();
    }
  } catch (err) {
    state.error = err?.message || "OfficeMitra AI action failed";
  } finally {
    state.loading = false;
    rerender();
  }
}
