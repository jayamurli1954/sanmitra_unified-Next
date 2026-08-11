// OfficeMitra AI workspace — Phase 1 + Phase 2 productivity tabs.
// Advisory AI only; figures come from connectors / user paste.

/** @type {Record<string, any> | null} */
let deps = null;

const state = {
  tab: "tasks", // tasks | email | brief | calendar | notes | notifications | proposals | mis | workflows
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
  misEnabled: false,
  misImportEnabled: false,
  misExportEnabled: false,
  misPacks: [],
  misCatalog: [],
  misSelectedPackId: "",
  misNewPackKey: "sme_general",
  misNewPeriod: "",
  misImportPersist: true,
  misReconcileScore: "",
  misLastImportReport: null,
  misPackFacts: [],
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
  const misPeriod = root.querySelector("[data-office-ai-field='misNewPeriod']");
  const misPackKey = root.querySelector("[data-office-ai-field='misNewPackKey']");
  const misScore = root.querySelector("[data-office-ai-field='misReconcileScore']");
  const misPersist = root.querySelector("[data-office-ai-field='misImportPersist']");
  if (draft) state.draftText = draft.value || "";
  if (email) state.emailText = email.value || "";
  if (calendar) state.calendarText = calendar.value || "";
  if (notes) state.notesText = notes.value || "";
  if (workflowName) state.workflowName = workflowName.value || "";
  if (workflowKey) state.workflowIdempotencyKey = workflowKey.value || "";
  if (misPeriod) state.misNewPeriod = misPeriod.value || "";
  if (misPackKey) state.misNewPackKey = misPackKey.value || "sme_general";
  if (misScore) state.misReconcileScore = misScore.value || "";
  if (misPersist) state.misImportPersist = misPersist.checked !== false;
}

function proposalSummary(proposal) {
  const action = String(proposal?.action_type || "").trim().toLowerCase();
  const payload = proposal?.payload && typeof proposal.payload === "object" ? proposal.payload : {};
  if (action === "reconcile_mis_pack") {
    const packId = String(payload.pack_id || "").trim();
    return packId ? `Reconcile MIS pack ${packId}` : "Reconcile MIS pack";
  }
  if (action.startsWith("export_mis_")) {
    const fmt = String(payload.export_format || action.replace("export_mis_", "")).trim();
    const packId = String(payload.pack_id || "").trim();
    return packId ? `Export ${fmt} — pack ${packId}` : `Export ${fmt}`;
  }
  return String(payload.title || proposal?.action_type || "(proposal)");
}

function formatMisPackStatus(status) {
  const key = String(status || "draft").toLowerCase();
  if (key === "pending_reconcile") return "Pending reconcile";
  if (key === "reconciled") return "Reconciled";
  if (key === "exported") return "Exported";
  return key.charAt(0).toUpperCase() + key.slice(1);
}

function misPackById(packId) {
  const id = String(packId || "").trim();
  return (state.misPacks || []).find((p) => String(p.id || "").trim() === id) || null;
}

function factDimensions(fact) {
  const dims = fact?.dimensions;
  return dims && typeof dims === "object" ? dims : {};
}

function formatMisAmount(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value ?? "—");
  return n.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function buildMisDashboard(facts) {
  const items = Array.isArray(facts) ? facts : [];
  const kpis = {};
  for (const fact of items) {
    if (String(fact.entity_type || "").toLowerCase() !== "kpi") continue;
    const name = String(factDimensions(fact).kpi || fact.source_id || "").trim();
    if (!name) continue;
    kpis[name] = {
      value: fact.value,
      unit: String(factDimensions(fact).unit || ""),
    };
  }

  const ageing = { AR: {}, AP: {} };
  for (const fact of items) {
    if (String(fact.entity_type || "").toLowerCase() !== "aging_bucket") continue;
    const dims = factDimensions(fact);
    const side = String(dims.side || "").toUpperCase();
    const bucket = String(dims.bucket || "").trim();
    if ((side !== "AR" && side !== "AP") || !bucket) continue;
    ageing[side][bucket] = Number(fact.amount_decimal || 0);
  }

  const pnl = {};
  for (const fact of items) {
    if (String(fact.entity_type || "").toLowerCase() !== "pnl_line") continue;
    const dims = factDimensions(fact);
    if (dims.trend) continue;
    const line = String(dims.line || "").trim();
    if (!line) continue;
    pnl[line] = Number(fact.amount_decimal || 0);
  }

  return { kpis, ageing, pnl };
}

function renderMisAgeingBars(side, buckets) {
  const order = ["Current", "1-30", "31-60", "61-90", "90+"];
  const values = order.map((b) => Number(buckets[b] || 0));
  const max = Math.max(...values, 1);
  const rows = order
    .map((bucket, idx) => {
      const amount = values[idx];
      const pct = Math.max(4, Math.round((amount / max) * 100));
      return `<div style="display:grid;grid-template-columns:4.5rem 1fr 6.5rem;gap:0.4rem;align-items:center;margin:0.25rem 0;">
        <span class="muted">${escapeHtml(bucket)}</span>
        <div style="background:rgba(0,0,0,0.06);height:0.55rem;border-radius:999px;overflow:hidden;">
          <div style="width:${pct}%;height:100%;background:${side === "AR" ? "#1f6feb" : "#0f766e"};"></div>
        </div>
        <span style="text-align:right;">${escapeHtml(formatMisAmount(amount))}</span>
      </div>`;
    })
    .join("");
  return `<div><h5 style="margin:0 0 0.35rem;">${side} ageing</h5>${rows}</div>`;
}

function renderMisDashboardStrip(facts) {
  const dash = buildMisDashboard(facts);
  const kpiOrder = [
    ["Revenue", "INR"],
    ["PAT", "INR"],
    ["GrossMarginPct", "%"],
    ["DSO", "days"],
    ["DPO", "days"],
    ["CurrentRatio", "x"],
    ["CashAndBank", "INR"],
    ["CashRunwayMonths", "mo"],
  ];
  const tiles = kpiOrder
    .map(([key, fallbackUnit]) => {
      const item = dash.kpis[key];
      if (!item) return "";
      const unit = item.unit === "percent" ? "%" : item.unit === "ratio" ? "x" : item.unit || fallbackUnit;
      const display = unit === "INR" || unit === "percent" || unit === "%"
        ? formatMisAmount(item.value)
        : String(item.value ?? "—");
      const suffix = unit && unit !== "INR" ? ` ${unit}` : "";
      return `<div style="min-width:7.5rem;padding:0.65rem 0.75rem;border:1px solid rgba(0,0,0,0.08);border-radius:8px;background:#fff;">
        <div class="muted" style="font-size:0.8rem;">${escapeHtml(key)}</div>
        <div style="font-size:1.1rem;font-weight:600;margin-top:0.15rem;">${escapeHtml(display)}${escapeHtml(suffix)}</div>
      </div>`;
    })
    .filter(Boolean)
    .join("");

  const hasAgeing = Object.keys(dash.ageing.AR).length || Object.keys(dash.ageing.AP).length;
  if (!tiles && !hasAgeing) {
    return `<p class="muted" style="margin-top:0.75rem;">Dashboard widgets appear after KPI / ageing facts are imported.</p>`;
  }

  return `
    <div style="margin-top:1rem;">
      <h5 style="margin:0 0 0.5rem;">Pack dashboard</h5>
      <p class="muted" style="margin:0 0 0.65rem;">Derived from imported MIS facts (not AI estimates).</p>
      ${tiles ? `<div style="display:flex;gap:0.5rem;flex-wrap:wrap;">${tiles}</div>` : ""}
      ${hasAgeing
        ? `<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(16rem,1fr));gap:1rem;margin-top:0.85rem;">
            ${renderMisAgeingBars("AR", dash.ageing.AR)}
            ${renderMisAgeingBars("AP", dash.ageing.AP)}
          </div>`
        : ""}
    </div>
  `;
}

function advisoryBanner() {
  return `<p class="muted" style="margin:0.5rem 0 0;">Advisory only — not final legal or financial advice. Review before acting.</p>`;
}

export function renderOfficeAiWorkspace() {
  const unread = Number(state.unreadCount || 0);
  const proposalsEnabled = !!(state.writebackEnabled || state.misEnabled);
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
  if (proposalsEnabled) {
    tabs.splice(1, 0, ["proposals", proposalLabel]);
  }
  let featureInsertAt = proposalsEnabled ? 2 : 1;
  if (state.misEnabled) {
    tabs.splice(featureInsertAt, 0, ["mis", "MIS Packs"]);
    featureInsertAt += 1;
  }
  if (state.workflowsEnabled) {
    tabs.splice(featureInsertAt, 0, ["workflows", "Workflows"]);
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
  else if (state.tab === "mis") body = renderMisPanel();
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
          ${state.misEnabled
            ? `<p class="muted" style="margin:0.35rem 0 0;">CA Analysis Pack (MIS) enabled: import Excel facts, reconcile with maker/checker, export when ready (ADR-014).</p>`
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
      const title = proposalSummary(proposal);
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
        <tbody>${rows || `<tr><td colspan="5" class="muted">No proposals yet. Generate tasks with write-back enabled, or submit MIS reconcile/export actions.</td></tr>`}</tbody>
      </table>
    </div>
  `;
}

function renderMisPanel() {
  const catalogOptions = (state.misCatalog || [])
    .map((entry) => {
      const key = String(entry.pack_key || "").trim();
      const label = String(entry.display_name || key);
      const enabled = entry.enabled_for_tenant !== false;
      const suffix = enabled ? "" : " (not enabled)";
      const selected = key === state.misNewPackKey ? " selected" : "";
      return `<option value="${escapeHtml(key)}"${selected}${enabled ? "" : " disabled"}>${escapeHtml(label)}${escapeHtml(suffix)}</option>`;
    })
    .join("");

  const packRows = (state.misPacks || [])
    .map((pack) => {
      const id = String(pack.id || "").trim();
      const selected = id === state.misSelectedPackId;
      const quality = pack.data_quality_score == null ? "—" : String(pack.data_quality_score);
      const rowClass = selected ? ' style="background:rgba(0,0,0,0.04)"' : "";
      return `<tr${rowClass}>
        <td>${escapeHtml(pack.display_name || pack.pack_key || "")}</td>
        <td>${escapeHtml(String(pack.period || ""))}</td>
        <td>${escapeHtml(formatMisPackStatus(pack.status))}</td>
        <td>${escapeHtml(quality)}</td>
        <td>
          <button class="${selected ? "primary" : "secondary"}" type="button" data-office-ai-action="mis-select-pack" data-pack-id="${escapeHtml(id)}">${selected ? "Selected" : "Select"}</button>
        </td>
      </tr>`;
    })
    .join("");

  const selected = misPackById(state.misSelectedPackId);
  const selectedStatus = selected ? formatMisPackStatus(selected.status) : "";
  const editableStatuses = ["draft", "pending_reconcile", "failed"];
  const selectedStatusKey = String(selected?.status || "draft").toLowerCase();
  const canEdit = selected && !selected.immutable && editableStatuses.includes(selectedStatusKey);
  const canReconcile = selected && !selected.immutable && !["reconciled", "exported"].includes(selectedStatusKey);
  const canExport = selected && ["reconciled", "exported"].includes(String(selected.status || "").toLowerCase());

  const factRows = (state.misPackFacts || [])
    .slice(0, 15)
    .map((fact) => `<tr>
      <td>${escapeHtml(String(fact.entity_type || ""))}</td>
      <td>${escapeHtml(String(fact.period || fact.as_of || ""))}</td>
      <td>${escapeHtml(String(fact.amount_decimal ?? fact.value ?? ""))}</td>
      <td>${escapeHtml(String(fact.source_system || ""))}</td>
    </tr>`)
    .join("");

  const report = state.misLastImportReport;
  const reportHtml = report
    ? `<div class="muted" style="margin-top:0.5rem;">
        Last import: ${escapeHtml(String(report.facts_previewed ?? 0))} valid row(s),
        ${escapeHtml(String((report.errors || []).length))} error(s),
        ${escapeHtml(String((report.warnings || []).length))} warning(s).
      </div>`
    : "";

  const importSection = state.misImportEnabled
    ? `<div class="stack-form" style="margin-top:1rem;">
        <h5>Import Excel</h5>
        <p class="muted">Upload SanMitra CA MIS template (.xlsx). Preview validates only; persist inserts valid facts.</p>
        <label style="display:block;">
          Excel file
          <input type="file" accept=".xlsx,.xls" data-office-ai-field="misImportFile" ${canEdit ? "" : "disabled"} />
        </label>
        <label style="display:flex;align-items:center;gap:0.35rem;">
          <input type="checkbox" data-office-ai-field="misImportPersist" ${state.misImportPersist ? "checked" : ""} ${canEdit ? "" : "disabled"} />
          Persist valid rows after validation
        </label>
        <button class="primary" type="button" data-office-ai-action="mis-import-excel" ${canEdit ? "" : "disabled"}>Import</button>
        ${reportHtml}
      </div>`
    : `<p class="muted" style="margin-top:1rem;">Excel import requires <code>office_ai.mis.import</code>.</p>`;

  const reconcileSection = canReconcile
    ? `<div class="stack-form" style="margin-top:1rem;">
        <h5>Reconcile (maker)</h5>
        <p class="muted">Locks the pack after checker approval. Optional quality score (0–100) for export gates.</p>
        <label>Data quality score (optional)
          <input type="number" min="0" max="100" data-office-ai-field="misReconcileScore" value="${escapeHtml(state.misReconcileScore || "")}" placeholder="e.g. 85" />
        </label>
        <button class="primary" type="button" data-office-ai-action="mis-reconcile">Submit reconcile</button>
      </div>`
    : selected
      ? `<p class="muted" style="margin-top:1rem;">Reconcile not available (status: ${escapeHtml(selectedStatus)}).</p>`
      : "";

  const exportSection = state.misExportEnabled && canExport
    ? `<div style="margin-top:1rem;display:flex;gap:0.5rem;flex-wrap:wrap;">
        <button class="secondary" type="button" data-office-ai-action="mis-export-excel">Export Excel</button>
        <button class="secondary" type="button" data-office-ai-action="mis-export-pdf">Export PDF summary</button>
        <button class="primary" type="button" data-office-ai-action="mis-export-ppt">Export PPT (checker)</button>
      </div>`
    : state.misExportEnabled && selected
      ? `<p class="muted" style="margin-top:1rem;">Export unlocks after reconcile. PPT requires quality score ≥ 70.</p>`
      : `<p class="muted" style="margin-top:1rem;">Export requires <code>office_ai.mis.export</code>.</p>`;

  return `
    <div class="stack-form">
      <p class="muted">CA Analysis Pack workflow: create pack → import facts → reconcile (maker/checker) → export. No journal or GST writes from MIS (ADR-014).</p>
      <button class="secondary" type="button" data-office-ai-action="mis-refresh">Refresh packs</button>

      <div class="stack-form" style="margin-top:1rem;">
        <h5>Create pack</h5>
        <label>Metric pack
          <select data-office-ai-field="misNewPackKey">${catalogOptions || `<option value="sme_general">SME General</option>`}</select>
        </label>
        <label>Period
          <input type="text" data-office-ai-field="misNewPeriod" value="${escapeHtml(state.misNewPeriod || "")}" placeholder="2026-07 or FY2025-26" />
        </label>
        <button class="primary" type="button" data-office-ai-action="mis-create-pack">Create draft pack</button>
      </div>

      <table class="data-table" style="margin-top:1rem;">
        <thead><tr><th>Pack</th><th>Period</th><th>Status</th><th>Quality</th><th></th></tr></thead>
        <tbody>${packRows || `<tr><td colspan="5" class="muted">No MIS packs yet.</td></tr>`}</tbody>
      </table>

      ${selected
        ? `<div style="margin-top:1rem;padding:0.75rem;border:1px solid rgba(0,0,0,0.08);border-radius:6px;">
            <h5>Selected: ${escapeHtml(selected.display_name || selected.pack_key || "")} — ${escapeHtml(String(selected.period || ""))}</h5>
            <p class="muted">Status: ${escapeHtml(selectedStatus)} · ID: ${escapeHtml(state.misSelectedPackId)}</p>
            ${renderMisDashboardStrip(state.misPackFacts)}
            ${importSection}
            ${reconcileSection}
            ${exportSection}
            <table class="data-table" style="margin-top:1rem;">
              <thead><tr><th>Entity</th><th>Period</th><th>Amount / value</th><th>Source</th></tr></thead>
              <tbody>${factRows || `<tr><td colspan="4" class="muted">No facts loaded.</td></tr>`}</tbody>
            </table>
          </div>`
        : `<p class="muted" style="margin-top:1rem;">Select a pack to import, reconcile, or export.</p>`}
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
    state.misEnabled = !!payload.mis_enabled;
    state.misImportEnabled = !!payload.mis_capabilities?.import;
    state.misExportEnabled = !!payload.mis_capabilities?.export;
    state.workflowsEnabled = !!payload.workflows_enabled;
  } catch (_err) {
    state.writebackEnabled = false;
    state.misEnabled = false;
    state.misImportEnabled = false;
    state.misExportEnabled = false;
    state.workflowsEnabled = false;
  }
}

async function refreshMisFacts(packId) {
  const id = String(packId || "").trim();
  if (!id) {
    state.misPackFacts = [];
    return;
  }
  const payload = unwrap(await apiRequest(`/api/v1/officemitra/mis/packs/${encodeURIComponent(id)}/facts?limit=500`));
  state.misPackFacts = payload.items || [];
}

async function refreshMisData() {
  if (!state.misEnabled) {
    state.misPacks = [];
    state.misCatalog = [];
    state.misPackFacts = [];
    return;
  }
  const [catalogRes, packsRes] = await Promise.all([
    unwrap(await apiRequest("/api/v1/officemitra/mis/pack-catalog")),
    unwrap(await apiRequest("/api/v1/officemitra/mis/packs?limit=50")),
  ]);
  state.misCatalog = catalogRes.items || [];
  state.misPacks = packsRes.items || [];
  if (state.misSelectedPackId && !misPackById(state.misSelectedPackId)) {
    state.misSelectedPackId = "";
    state.misPackFacts = [];
  }
  if (!state.misSelectedPackId && state.misPacks.length) {
    state.misSelectedPackId = String(state.misPacks[0]?.id || "").trim();
  }
  if (state.misSelectedPackId) {
    await refreshMisFacts(state.misSelectedPackId);
  }
}

async function refreshProposals() {
  if (!(state.writebackEnabled || state.misEnabled)) {
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
    else if (state.tab === "mis") await refreshMisData();
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
    if ((state.writebackEnabled || state.misEnabled) && state.tab !== "proposals") {
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
  const misSelectPackId = action === "mis-select-pack"
    ? String(el?.getAttribute("data-pack-id") || el?.dataset?.packId || "").trim()
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
      if (state.misEnabled) {
        try {
          await refreshMisData();
        } catch (_e) {
          /* optional */
        }
      }
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
      if (state.misEnabled) {
        try {
          await refreshMisData();
        } catch (_e) {
          /* optional */
        }
      }
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
    } else if (action === "mis-refresh") {
      await refreshMisData();
    } else if (action === "mis-select-pack") {
      if (!misSelectPackId) throw new Error("Missing pack id");
      state.misSelectedPackId = misSelectPackId;
      state.misLastImportReport = null;
      await refreshMisFacts(misSelectPackId);
    } else if (action === "mis-create-pack") {
      const period = (state.misNewPeriod || "").trim();
      if (!period) throw new Error("Enter a period (e.g. 2026-07)");
      const result = unwrap(await apiRequest("/api/v1/officemitra/mis/packs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pack_key: state.misNewPackKey || "sme_general",
          period,
          ingestion_path: "excel_import",
        }),
      }));
      state.misSelectedPackId = String(result?.item?.id || "").trim();
      state.notice = "MIS pack created.";
      await refreshMisData();
    } else if (action === "mis-import-excel") {
      const packId = state.misSelectedPackId;
      if (!packId) throw new Error("Select a pack first");
      const root = el?.closest?.("[data-office-ai-root]");
      const fileInput = root?.querySelector("[data-office-ai-field='misImportFile']");
      const file = fileInput?.files?.[0];
      if (!file) throw new Error("Choose an Excel file first");
      const formData = new FormData();
      formData.append("file", file);
      const persist = state.misImportPersist ? "true" : "false";
      const result = unwrap(await apiRequest(
        `/api/v1/officemitra/mis/packs/${encodeURIComponent(packId)}/import/excel?persist=${persist}`,
        { method: "POST", body: formData },
      ));
      state.misLastImportReport = result?.validation_report || null;
      const inserted = Number(result?.inserted || 0);
      const previewed = Number(result?.facts_previewed || 0);
      state.notice = state.misImportPersist
        ? `Import complete: ${inserted} fact(s) inserted (${previewed} previewed).`
        : `Validation only: ${previewed} row(s) previewed.`;
      await refreshMisFacts(packId);
      await refreshMisData();
    } else if (action === "mis-reconcile") {
      const packId = state.misSelectedPackId;
      if (!packId) throw new Error("Select a pack first");
      const body = {};
      const scoreRaw = (state.misReconcileScore || "").trim();
      if (scoreRaw) {
        const score = Number(scoreRaw);
        if (!Number.isFinite(score) || score < 0 || score > 100) {
          throw new Error("Quality score must be between 0 and 100");
        }
        body.data_quality_score = Math.round(score);
      }
      const result = unwrap(await apiRequest(`/api/v1/officemitra/mis/packs/${encodeURIComponent(packId)}/reconcile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }));
      const status = result?.proposal?.status || "";
      state.notice = status === "awaiting_checker"
        ? "Reconcile submitted — checker must approve in Proposals tab."
        : status === "applied"
          ? "Pack reconciled."
          : status === "failed"
            ? `Reconcile failed: ${result?.error || result?.proposal?.error_message || "unknown error"}`
            : "Reconcile proposal updated.";
      if (status === "awaiting_checker") state.tab = "proposals";
      await refreshMisData();
      await refreshProposals();
    } else if (action === "mis-export-excel" || action === "mis-export-pdf" || action === "mis-export-ppt") {
      const packId = state.misSelectedPackId;
      if (!packId) throw new Error("Select a pack first");
      const fmt = action === "mis-export-excel"
        ? "excel"
        : action === "mis-export-pdf"
          ? "pdf_summary"
          : "ppt";
      const result = unwrap(await apiRequest(`/api/v1/officemitra/mis/packs/${encodeURIComponent(packId)}/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ format: fmt }),
      }));
      const status = result?.proposal?.status || "";
      const fmtLabel = fmt === "pdf_summary" ? "PDF summary" : fmt.toUpperCase();
      state.notice = status === "awaiting_checker"
        ? `${fmtLabel} export submitted — checker must approve in Proposals tab.`
        : status === "applied"
          ? `${fmtLabel} export completed.`
          : status === "failed"
            ? `Export failed: ${result?.error || result?.proposal?.error_message || "unknown error"}`
            : `${fmtLabel} export proposal updated.`;
      if (status === "awaiting_checker") state.tab = "proposals";
      await refreshMisData();
      await refreshProposals();
    }
  } catch (err) {
    state.error = err?.message || "OfficeMitra AI action failed";
  } finally {
    state.loading = false;
    rerender();
  }
}
