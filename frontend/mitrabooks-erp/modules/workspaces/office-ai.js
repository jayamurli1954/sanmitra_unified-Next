// OfficeMitra AI workspace (MVP) — MitraBooks ERP shell panel.
// Advisory AI only; figures come from connectors / user paste.

/** @type {Record<string, any> | null} */
let deps = null;

const state = {
  tab: "tasks", // tasks | email | brief
  tasks: [],
  emails: [],
  brief: null,
  error: "",
  notice: "",
  loading: false,
  draftText: "",
  emailText: "",
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

function advisoryBanner() {
  return `<p class="muted" style="margin:0.5rem 0 0;">Advisory only — not final legal or financial advice. Review before acting.</p>`;
}

export function renderOfficeAiWorkspace() {
  const tabs = [
    ["tasks", "Tasks"],
    ["email", "Email Summary"],
    ["brief", "Today Brief"],
  ];
  const tabButtons = tabs
    .map(([id, label]) => {
      const active = state.tab === id ? "primary" : "secondary";
      return `<button class="${active}" type="button" data-office-ai-action="tab" data-tab="${id}">${label}</button>`;
    })
    .join(" ");

  let body = "";
  if (state.tab === "tasks") {
    body = renderTasksPanel();
  } else if (state.tab === "email") {
    body = renderEmailPanel();
  } else {
    body = renderBriefPanel();
  }

  return `
    <div class="verification-panel erp-workspace-panel" data-office-ai-root="1">
      <div class="preview-heading compact">
        <div>
          <h4>OfficeMitra AI</h4>
          <p>Tasks, pasted email summaries, and a daily brief from connected MitraBooks data.</p>
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

export async function loadOfficeAiWorkspace() {
  state.error = "";
  state.loading = true;
  rerender();
  try {
    if (state.tab === "tasks") {
      await refreshTasks();
    } else if (state.tab === "email") {
      await refreshEmails();
    } else {
      await refreshBrief();
    }
  } catch (err) {
    state.error = err?.message || "Failed to load OfficeMitra AI";
  } finally {
    state.loading = false;
    rerender();
  }
}

export async function handleOfficeAiAction(action, el) {
  const field = el?.closest?.("[data-office-ai-root]")?.querySelector?.("[data-office-ai-field='draftText']");
  const emailField = el?.closest?.("[data-office-ai-root]")?.querySelector?.("[data-office-ai-field='emailText']");
  if (field) state.draftText = field.value || "";
  if (emailField) state.emailText = emailField.value || "";

  state.error = "";
  state.notice = "";
  const completeTaskId = action === "complete-task"
    ? String(el?.getAttribute("data-task-id") || el?.dataset?.taskId || "").trim()
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
    } else if (action === "generate-brief") {
      const result = unwrap(await apiRequest("/api/v1/officemitra/briefs/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ include_tasks: true, include_emails: true }),
      }));
      state.brief = result?.brief || null;
      state.notice = result?.ai_available === false
        ? "Brief saved with deterministic fallback (AI unavailable)."
        : "Brief generated.";
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
