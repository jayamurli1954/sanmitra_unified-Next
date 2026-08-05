// OfficeMitra AI workspace — Phase 1 + Phase 2 productivity tabs.
// Advisory AI only; figures come from connectors / user paste.

/** @type {Record<string, any> | null} */
let deps = null;

const state = {
  tab: "tasks", // tasks | email | brief | calendar | notes | notifications
  tasks: [],
  emails: [],
  brief: null,
  events: [],
  notes: [],
  notifications: [],
  unreadCount: 0,
  error: "",
  notice: "",
  loading: false,
  draftText: "",
  emailText: "",
  calendarText: "",
  notesText: "",
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

function apiRequest(path, options) {
  return requireDeps().apiRequest("mitrabooks", path, options);
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
  if (draft) state.draftText = draft.value || "";
  if (email) state.emailText = email.value || "";
  if (calendar) state.calendarText = calendar.value || "";
  if (notes) state.notesText = notes.value || "";
}

function advisoryBanner() {
  return `<p class="muted" style="margin:0.5rem 0 0;">Advisory only — not final legal or financial advice. Review before acting.</p>`;
}

export function renderOfficeAiWorkspace() {
  const unread = Number(state.unreadCount || 0);
  const notifLabel = unread > 0 ? `Notifications (${unread})` : "Notifications";
  const tabs = [
    ["tasks", "Tasks"],
    ["email", "Email Summary"],
    ["calendar", "Calendar"],
    ["notes", "Meeting Notes"],
    ["notifications", notifLabel],
    ["brief", "Today Brief"],
  ];
  const tabButtons = tabs
    .map(([id, label]) => {
      const active = state.tab === id ? "primary" : "secondary";
      return `<button class="${active}" type="button" data-office-ai-action="tab" data-tab="${id}">${label}</button>`;
    })
    .join(" ");

  let body = "";
  if (state.tab === "tasks") body = renderTasksPanel();
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

function rerender() {
  const preview = requireDeps().dashboardPreview;
  if (preview && requireDeps().getActiveBusinessWorkspace() === "office-ai") {
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

export async function loadOfficeAiWorkspace() {
  state.error = "";
  state.loading = true;
  rerender();
  try {
    if (state.tab === "tasks") await refreshTasks();
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
      const result = unwrap(await apiRequest("/api/v1/officemitra/tasks/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: state.draftText, persist: true }),
      }));
      state.notice = result?.ai_available === false
        ? `AI unavailable (${result?.error_code || "offline"}). No tasks generated.`
        : `Generated ${(result?.saved_tasks || []).length} task(s).`;
      await refreshTasks();
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
