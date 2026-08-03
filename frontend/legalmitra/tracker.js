import { apiRequest, getAccessToken } from "../shared/api-client.js";

const APP_KEY = "legalmitra";

const trackerProfiles = {
  advocate: {
    metrics: [
      ["Urgent items", "0"],
      ["Open items", "0"],
      ["Logged items", "0"],
      ["Fees outstanding", "—"],
    ],
    rows: [
      ["15 May 2024", "NI-138/Client-A", "JMFC Court", "Complaint limitation check", "urgent"],
      ["18 May 2024", "WP-226/2024", "High Court", "Affidavit and annexure review", "review"],
      ["22 May 2024", "CS-42/2024", "Civil Court", "Interim application filing", "pending"],
    ],
    registers: [
      ["Case and matter register", "Maintain case number, client, court, next date, filing stage, limitation status, documents, and responsible owner."],
      ["Client follow-up register", "Track client instructions, affidavit status, missing documents, settlement discussions, and last communication."],
      ["Fees and receivables", "Record retainers, appearance fees, drafting fees, filing expenses, collections, pending dues, and matter-wise billing notes."],
    ],
    details: {
      "case-master": ["Matter number", "Client name", "Court / forum", "Next date", "Filing stage", "Limitation status"],
      clients: ["Client contact", "Instruction status", "Documents pending", "Last follow-up", "Next reminder", "Escalation owner"],
      "fee-ledger": ["Retainer", "Drafting fee", "Appearance fee", "Expenses", "Amount received", "Balance due"],
    },
  },
  ca: {
    metrics: [
      ["Urgent items", "0"],
      ["Open items", "0"],
      ["Logged items", "0"],
      ["Fees outstanding", "—"],
    ],
    rows: [
      ["15 May 2024", "GST-SCN-2024-08", "GST Dept, Mumbai", "Notice reply filing", "urgent"],
      ["20 May 2024", "ITR-Client-32", "Income Tax Portal", "AIS/TIS reconciliation", "review"],
      ["30 May 2024", "GSTR-9C-Client-14", "GST Portal", "Annual return working papers", "pending"],
    ],
    registers: [
      ["Tax compliance register", "Track GST notices, income tax tasks, audit workings, return status, portal acknowledgements, and responsible staff."],
      ["Client document follow-up", "Monitor books, bank statements, invoices, reconciliations, DSC availability, and management approvals."],
      ["Professional fee ledger", "Record retainers, filing fees, audit fees, advisory invoices, collections, write-offs, and client-wise dues."],
    ],
    details: {
      "case-master": ["GSTIN / PAN", "Notice reference", "Assessment year", "Portal status", "Working paper owner", "Due date"],
      clients: ["Books received", "Bank statements", "Invoice dump", "DSC status", "Approval pending", "Reminder date"],
      "fee-ledger": ["Monthly retainer", "Return filing fee", "Audit fee", "Advisory fee", "Collections", "Outstanding"],
    },
  },
  cs: {
    metrics: [
      ["Urgent items", "0"],
      ["Open items", "0"],
      ["Logged items", "0"],
      ["Fees outstanding", "—"],
    ],
    rows: [
      ["16 May 2024", "LLP-F11-2026", "MCA Portal", "Partner data confirmation", "urgent"],
      ["24 May 2024", "DIR-3-KYC", "MCA Portal", "Director KYC follow-up", "pending"],
      ["30 May 2024", "BM-Notice-Client-9", "Board Secretariat", "Board notice and agenda circulation", "review"],
    ],
    registers: [
      ["Entity compliance register", "Track companies, LLPs, annual filings, board actions, registers, resolutions, and statutory due dates."],
      ["Director and partner follow-up", "Monitor KYC, DSC, DIN, contribution, shareholding, approvals, and pending confirmations."],
      ["Secretarial fee ledger", "Record annual retainers, form filing fees, certification fees, event-based billing, collections, and dues."],
    ],
    details: {
      "case-master": ["Entity name", "CIN / LLPIN", "Filing event", "Board action", "MCA form", "Due date"],
      clients: ["Director / partner", "DIN / DPIN", "DSC expiry", "KYC status", "Approval pending", "Escalation note"],
      "fee-ledger": ["Annual retainer", "Form filing fee", "Certification fee", "Event billing", "Collections", "Outstanding"],
    },
  },
};

let currentRole = "advocate";
let currentCard = "case-master";
let editingRowIndex = null;
let livePractice = null;
let morningBrief = null;
let activeWorkflowRun = null;
let feeSummary = null;
let feeInvoices = [];
const storageKey = "legalmitra-tracker-drafts-v2";
const rowStorageKey = "legalmitra-tracker-work-items-v2";
const registerCardOrder = ["case-master", "clients", "fee-ledger"];

const rowEditor = document.getElementById("tracker-row-editor");
const rowEditorKicker = document.getElementById("tracker-row-editor-kicker");
const rowEditorTitle = document.getElementById("tracker-row-editor-title");
const rowDateInput = document.getElementById("tracker-row-date");
const rowReferenceInput = document.getElementById("tracker-row-reference");
const rowAuthorityInput = document.getElementById("tracker-row-authority");
const rowPurposeInput = document.getElementById("tracker-row-purpose");
const rowStatusInput = document.getElementById("tracker-row-status");

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function normalizeRow(row) {
  if (Array.isArray(row)) {
    return {
      date: row[0] || "",
      reference: row[1] || "",
      authority: row[2] || "",
      purpose: row[3] || "",
      status: row[4] || "pending",
    };
  }
  return {
    date: String(row?.date || ""),
    reference: String(row?.reference || ""),
    authority: String(row?.authority || ""),
    purpose: String(row?.purpose || ""),
    status: String(row?.status || "pending").toLowerCase(),
  };
}

function getStoredRows() {
  try {
    const stored = JSON.parse(localStorage.getItem(rowStorageKey) || "{}");
    return stored && typeof stored === "object" ? stored : {};
  } catch {
    return {};
  }
}

function saveStoredRows(rowsByRole) {
  localStorage.setItem(rowStorageKey, JSON.stringify(rowsByRole));
}

function persistRoleRows(rows, role = currentRole) {
  const stored = getStoredRows();
  stored[role] = rows.map(normalizeRow);
  saveStoredRows(stored);
}

function renderRows(rows = getRoleRows()) {
  const target = document.getElementById("tracker-rows");
  if (!target) return;
  const normalizedRows = rows.map(normalizeRow);
  target.textContent = "";
  const fragment = document.createDocumentFragment();

  normalizedRows.forEach((row, index) => {
    const tr = document.createElement("tr");

    const dateTd = document.createElement("td");
    dateTd.textContent = row.date;
    tr.appendChild(dateTd);

    const referenceTd = document.createElement("td");
    referenceTd.textContent = row.reference;
    tr.appendChild(referenceTd);

    const authorityTd = document.createElement("td");
    authorityTd.textContent = row.authority;
    tr.appendChild(authorityTd);

    const purposeTd = document.createElement("td");
    purposeTd.textContent = row.purpose;
    tr.appendChild(purposeTd);

    const statusTd = document.createElement("td");
    const statusSpan = document.createElement("span");
    statusSpan.className = `status ${String(row.status || "").replace(/[^a-z0-9_-]/gi, "")}`;
    statusSpan.textContent = row.status;
    statusTd.appendChild(statusSpan);
    tr.appendChild(statusTd);

    const actionsTd = document.createElement("td");
    const actions = document.createElement("div");
    actions.className = "legal-diary-row-actions";

    const editButton = document.createElement("button");
    editButton.type = "button";
    editButton.dataset.rowAction = "edit";
    editButton.dataset.rowIndex = String(index);
    editButton.setAttribute("aria-label", "Edit work item");
    editButton.textContent = "Edit";

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.dataset.rowAction = "delete";
    deleteButton.dataset.rowIndex = String(index);
    deleteButton.setAttribute("aria-label", "Delete work item");
    deleteButton.textContent = "Delete";

    actions.append(editButton, deleteButton);
    actionsTd.appendChild(actions);
    tr.appendChild(actionsTd);

    fragment.appendChild(tr);
  });

  target.appendChild(fragment);
}

function updateMetricsForRows() {
  const profile = trackerProfiles[currentRole] || trackerProfiles.advocate;
  let metrics;
  if (livePractice) {
    const health = livePractice.practice_health_score;
    metrics = [
      ["Practice health", health == null ? "—" : String(health)],
      ["Open alerts", String(livePractice.open_alerts ?? 0)],
      ["Active matters", String(livePractice.active_matters ?? 0)],
      ["Fees outstanding", livePractice.fees_outstanding || "—"],
    ];
  } else {
    const rows = getRoleRows();
    const urgentCount = rows.filter((row) => row.status === "urgent").length;
    const pendingCount = rows.filter((row) => row.status !== "done").length;
    metrics = [
      ["Urgent items", String(urgentCount)],
      ["Open items", String(pendingCount)],
      ["Logged items", String(rows.length)],
      ["Fees outstanding", "—"],
    ];
    if (profile.metrics?.[0]?.[0]) {
      metrics[0][0] = profile.metrics[0][0];
    }
  }
  metrics.forEach(([label, value], index) => {
    const labelEl = document.getElementById(`metric-label-${index + 1}`);
    const valueEl = document.getElementById(`metric-value-${index + 1}`);
    if (labelEl) labelEl.textContent = label;
    if (valueEl) valueEl.textContent = value;
  });
}

function formatPracticeDate(value) {
  if (!value) return "";
  const text = String(value);
  return text.length >= 10 ? text.slice(0, 10) : text;
}

function liveMatterRows() {
  if (!livePractice) return null;
  const hearings = (livePractice.upcoming_hearings || []).map((item) => ({
    date: formatPracticeDate(item.next_hearing_date),
    reference: item.matter_number || item.matter_id || "",
    authority: item.court || "—",
    purpose: item.title || "Hearing",
    status: item.status || "pending",
  }));
  const deadlines = (livePractice.upcoming_deadlines || []).map((item) => ({
    date: formatPracticeDate(item.next_deadline_date),
    reference: item.matter_number || item.matter_id || "",
    authority: "Compliance deadline",
    purpose: item.title || "Deadline",
    status: item.status || "pending",
  }));
  return [...hearings, ...deadlines];
}

function getRoleRows(role = currentRole) {
  const liveRows = liveMatterRows();
  if (liveRows !== null) return liveRows.map(normalizeRow);
  const stored = getStoredRows();
  const savedRows = Array.isArray(stored[role]) ? stored[role].map(normalizeRow) : [];
  if (savedRows.length) return savedRows;
  return (trackerProfiles[role]?.rows || trackerProfiles.advocate.rows).map(normalizeRow);
}

function updatePracticeBanner() {
  const banner = document.querySelector(".legal-tracker-preview-banner");
  if (!banner) return;
  if (livePractice) {
    banner.textContent =
      "Live practice workspace — metrics and boards below come from your tenant clients and matters. Morning Brief, guided workflows, and the fee ledger load when practice data is available.";
  } else if (getAccessToken()) {
    banner.textContent =
      "Signed in, but live practice data could not be loaded. Showing browser preview rows until the practice API responds.";
  } else {
    banner.textContent =
      "Preview workspace — sign in to load tenant-backed clients, matters, hearings, Morning Brief, and fee records. Browser-only rows are not the system of record.";
  }
}

async function loadLivePractice() {
  if (!getAccessToken()) {
    livePractice = null;
    morningBrief = null;
    updatePracticeBanner();
    renderMorningBrief();
    return;
  }
  try {
    const result = await apiRequest(APP_KEY, "/api/v1/legal/practice/dashboard?limit=8", {
      method: "GET",
      timeoutMs: 12000,
    });
    if (result?.ok && result.payload) {
      livePractice = result.payload;
    } else {
      livePractice = null;
    }
  } catch (_error) {
    livePractice = null;
  }
  updatePracticeBanner();
  updateMetricsForRows();
  renderRows(getRoleRows());
  await Promise.all([loadMorningBrief(false), loadFeeLedger()]);
}

async function loadFeeLedger() {
  const panel = document.getElementById("fee-ledger-live");
  const listEl = document.getElementById("fee-ledger-live-list");
  const summaryEl = document.getElementById("fee-ledger-live-summary");
  if (!getAccessToken()) {
    feeSummary = null;
    feeInvoices = [];
    if (panel) panel.hidden = true;
    return;
  }
  try {
    const [summaryRes, invoicesRes] = await Promise.all([
      apiRequest(APP_KEY, "/api/v1/legal/practice/fees/summary", {
        method: "GET",
        timeoutMs: 12000,
      }),
      apiRequest(APP_KEY, "/api/v1/legal/practice/fees/invoices?limit=20", {
        method: "GET",
        timeoutMs: 12000,
      }),
    ]);
    feeSummary = summaryRes?.ok ? summaryRes.payload : null;
    feeInvoices = invoicesRes?.ok ? (invoicesRes.payload.items || []) : [];
  } catch (_error) {
    feeSummary = null;
    feeInvoices = [];
  }

  if (!panel || !listEl || !summaryEl) return;
  panel.hidden = false;
  if (feeSummary) {
    summaryEl.textContent =
      `Outstanding ${feeSummary.fees_outstanding_display || "₹0.00"} · ` +
      `billed ${feeSummary.total_billed ?? 0} · collected ${feeSummary.total_collected ?? 0}`;
    if (livePractice) {
      livePractice.fees_outstanding = feeSummary.fees_outstanding_display || livePractice.fees_outstanding;
      updateMetricsForRows();
    }
  } else {
    summaryEl.textContent = "Fee ledger unavailable.";
  }
  listEl.textContent = "";
  if (!feeInvoices.length) {
    const li = document.createElement("li");
    li.textContent = "No fee notes yet. Create an invoice via the practice fees API.";
    listEl.appendChild(li);
    return;
  }
  feeInvoices.slice(0, 12).forEach((inv) => {
    const li = document.createElement("li");
    li.textContent =
      `${inv.invoice_number || inv.invoice_id} · ${inv.status} · ` +
      `due ${inv.amount_outstanding ?? "—"} / total ${inv.grand_total ?? "—"}`;
    listEl.appendChild(li);
  });
}

function renderMorningBrief() {
  const panel = document.getElementById("morning-brief-panel");
  const healthEl = document.getElementById("morning-brief-health");
  const advisoryEl = document.getElementById("morning-brief-advisory");
  const actionsEl = document.getElementById("morning-brief-actions");
  if (!panel || !healthEl || !actionsEl) return;

  if (!getAccessToken()) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  actionsEl.textContent = "";

  if (!morningBrief) {
    healthEl.textContent = "Morning Brief unavailable. Refresh after practice data is loaded.";
    if (advisoryEl) advisoryEl.hidden = true;
    return;
  }

  const score = morningBrief.practice_health_score;
  const label = morningBrief.practice_health_label || "";
  healthEl.textContent = `Practice Health ${score}/100 — ${label}`;
  if (advisoryEl) {
    advisoryEl.hidden = false;
    advisoryEl.textContent = morningBrief.advisory_notice
      || "Advisory — human review required. Never invent hearings, statutes, or court dates.";
  }

  const actions = morningBrief.sections?.priority_actions || [];
  if (!actions.length) {
    const li = document.createElement("li");
    li.textContent = morningBrief.empty_practice
      ? "No practice data yet. Create a client and matter to activate Priority Actions."
      : "No open priority alerts for today.";
    actionsEl.appendChild(li);
    return;
  }

  actions.slice(0, 8).forEach((item) => {
    const li = document.createElement("li");
    const link = document.createElement("a");
    link.href = item.action_href || "./tracker.html#daily-board";
    link.textContent = item.title || item.summary || "Open matter";
    const meta = document.createElement("span");
    meta.textContent = ` · ${item.severity || "normal"} · score ${item.priority_score ?? "—"}`;
    const tip = document.createElement("div");
    tip.textContent = (item.suggested_actions || []).slice(0, 2).join(" · ");
    li.append(link, meta);
    if (tip.textContent) li.appendChild(tip);

    const wf = item.recommended_workflow;
    if (wf && item.matter_id) {
      const start = document.createElement("button");
      start.type = "button";
      start.className = "legal-workflow-start";
      start.textContent = `Start: ${wf.display_name || "Prepare Matter Response"}`;
      start.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        startRecommendedWorkflow(item, start);
      });
      li.appendChild(start);
    }
    actionsEl.appendChild(li);
  });
}

function latestStepByKey(steps) {
  const best = new Map();
  (steps || []).forEach((step) => {
    const prev = best.get(step.step_key);
    if (!prev || (step.attempt || 1) >= (prev.attempt || 1)) {
      best.set(step.step_key, step);
    }
  });
  return Array.from(best.values());
}

function renderWorkflowRun() {
  const panel = document.getElementById("workflow-run-panel");
  const statusEl = document.getElementById("workflow-run-status");
  const stepsEl = document.getElementById("workflow-run-steps");
  const actionsEl = document.getElementById("workflow-run-actions");
  if (!panel || !statusEl || !stepsEl || !actionsEl) return;

  if (!activeWorkflowRun) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  stepsEl.textContent = "";
  actionsEl.textContent = "";

  const run = activeWorkflowRun;
  statusEl.textContent =
    `Status: ${run.status} · template ${run.workflow_template || "general"}` +
    (run.ready_to_file ? " · ready-to-file marked (not filed)" : "");

  const steps = latestStepByKey(run.steps);
  steps.forEach((step) => {
    const li = document.createElement("li");
    const conf = step.confidence != null ? ` · confidence ${step.confidence}` : "";
    li.textContent =
      `${step.step_key}: ${step.status} (~${step.estimated_minutes || "?"} min)${conf}`;
    if (step.error) {
      const err = document.createElement("div");
      err.textContent = step.error;
      li.appendChild(err);
    }
    stepsEl.appendChild(li);
  });

  const awaiting = steps.find((s) => s.status === "awaiting_human");
  if (awaiting) {
    const approve = document.createElement("button");
    approve.type = "button";
    approve.textContent = `Approve ${awaiting.step_key}`;
    approve.addEventListener("click", () => approveWorkflowStep(run.run_id, awaiting.step_id));
    const reject = document.createElement("button");
    reject.type = "button";
    reject.textContent = `Reject ${awaiting.step_key}`;
    reject.addEventListener("click", () => rejectWorkflowStep(run.run_id, awaiting.step_id));
    actionsEl.append(approve, reject);
  }

  if (run.status === "completed" && !run.ready_to_file) {
    const mark = document.createElement("button");
    mark.type = "button";
    mark.textContent = "Mark ready to file (does not file)";
    mark.addEventListener("click", () => markReadyToFile(run.run_id));
    actionsEl.appendChild(mark);
  }
}

async function startRecommendedWorkflow(item, triggerButton = null) {
  if (!getAccessToken() || !item?.matter_id) return;

  const panel = document.getElementById("workflow-run-panel");
  const statusEl = document.getElementById("workflow-run-status");
  const stepsEl = document.getElementById("workflow-run-steps");
  const actionsEl = document.getElementById("workflow-run-actions");
  if (panel) panel.hidden = false;
  if (statusEl) statusEl.textContent = "Starting Prepare Matter Response…";
  if (stepsEl) stepsEl.textContent = "";
  if (actionsEl) actionsEl.textContent = "";
  if (triggerButton) {
    triggerButton.disabled = true;
    triggerButton.textContent = "Starting…";
  }

  const wf = item.recommended_workflow || {
    workflow_key: "prepare_matter_response",
    workflow_template: "general",
  };
  const result = await apiRequest(APP_KEY, "/api/v1/legal/workflows/runs", {
    method: "POST",
    timeoutMs: 45000,
    body: JSON.stringify({
      workflow_key: wf.workflow_key || "prepare_matter_response",
      workflow_template: wf.workflow_template || "general",
      matter_id: item.matter_id,
      alert_id: item.alert_id || null,
      recommended_from: "morning_brief",
      persona: currentRole === "ca" || currentRole === "cs" ? currentRole : "advocate",
    }),
  });

  if (triggerButton) {
    triggerButton.disabled = false;
    triggerButton.textContent = `Start: ${wf.display_name || "Prepare Matter Response"}`;
  }

  if (!result?.ok) {
    activeWorkflowRun = null;
    let detail = `HTTP ${result?.status || 0}`;
    const payload = result?.payload;
    if (typeof payload === "string" && payload.trim()) {
      detail = payload;
    } else if (payload && typeof payload === "object") {
      if (typeof payload.detail === "string") detail = payload.detail;
      else if (Array.isArray(payload.detail)) {
        detail = payload.detail
          .map((row) => (typeof row === "string" ? row : row?.msg || JSON.stringify(row)))
          .join("; ");
      } else if (payload.message) detail = String(payload.message);
      else detail = JSON.stringify(payload);
    }
    if (statusEl) {
      statusEl.textContent = `Could not start workflow: ${detail}`;
    }
    panel?.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }

  activeWorkflowRun = result.payload;
  renderWorkflowRun();
  document.getElementById("workflow-run-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function approveWorkflowStep(runId, stepId) {
  const result = await apiRequest(
    APP_KEY,
    `/api/v1/legal/workflows/runs/${encodeURIComponent(runId)}/steps/${encodeURIComponent(stepId)}/approve`,
    { method: "POST", timeoutMs: 30000 },
  );
  activeWorkflowRun = result?.ok ? result.payload : activeWorkflowRun;
  renderWorkflowRun();
}

async function rejectWorkflowStep(runId, stepId) {
  const reason = window.prompt("Rejection reason (required for audit):", "Needs revision");
  if (!reason || reason.trim().length < 2) return;
  const result = await apiRequest(
    APP_KEY,
    `/api/v1/legal/workflows/runs/${encodeURIComponent(runId)}/steps/${encodeURIComponent(stepId)}/reject`,
    {
      method: "POST",
      timeoutMs: 20000,
      body: JSON.stringify({ reason: reason.trim() }),
    },
  );
  activeWorkflowRun = result?.ok ? result.payload : activeWorkflowRun;
  renderWorkflowRun();
}

async function markReadyToFile(runId) {
  const result = await apiRequest(
    APP_KEY,
    `/api/v1/legal/workflows/runs/${encodeURIComponent(runId)}/ready-to-file`,
    {
      method: "POST",
      timeoutMs: 15000,
      body: JSON.stringify({ ready_to_file: true, confirm: true }),
    },
  );
  activeWorkflowRun = result?.ok ? result.payload : activeWorkflowRun;
  renderWorkflowRun();
}

async function loadMorningBrief(forceRefresh) {
  if (!getAccessToken()) {
    morningBrief = null;
    renderMorningBrief();
    return;
  }
  const persona = currentRole === "ca" || currentRole === "cs" ? currentRole : "advocate";
  try {
    const path = forceRefresh
      ? "/api/v1/legal/practice/morning-brief"
      : `/api/v1/legal/practice/morning-brief?persona=${encodeURIComponent(persona)}&window=daily`;
    const result = await apiRequest(APP_KEY, path, {
      method: forceRefresh ? "POST" : "GET",
      timeoutMs: 20000,
      body: forceRefresh
        ? JSON.stringify({ persona, window: "daily", force_refresh: true })
        : undefined,
    });
    morningBrief = result?.ok ? result.payload : null;
  } catch (_error) {
    morningBrief = null;
  }
  renderMorningBrief();
}

function setRole(role) {
  const profile = trackerProfiles[role] || trackerProfiles.advocate;
  currentRole = role;

  updateMetricsForRows();

  profile.registers.forEach(([title, copy], index) => {
    document.getElementById(`register-title-${index + 1}`).textContent = title;
    document.getElementById(`register-copy-${index + 1}`).textContent = copy;
  });

  renderRows(getRoleRows(role));
  renderDetail(currentCard);

  document.querySelectorAll("[data-tracker-role]").forEach((button) => {
    const active = button.getAttribute("data-tracker-role") === role;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
}

function renderDetail(card, options = {}) {
  const { scroll = true, syncTab = true } = options;
  currentCard = card || "case-master";
  const profile = trackerProfiles[currentRole] || trackerProfiles.advocate;
  const cardIndex = registerCardOrder.indexOf(currentCard);
  const safeIndex = cardIndex >= 0 ? cardIndex : 0;
  const [title, copy] = profile.registers[safeIndex];
  const labels = profile.details[currentCard] || profile.details["case-master"];
  const saved = sanitizeSavedValues(getSavedValues(currentRole, currentCard));
  // Drop corrupted browser drafts so Reset / reload show clean samples.
  const drafts = getDrafts();
  if (drafts?.[currentRole]?.[currentCard]) {
    drafts[currentRole][currentCard] = saved;
    localStorage.setItem(storageKey, JSON.stringify(drafts));
  }

  document.getElementById("tracker-detail-kicker").textContent = document.querySelector(`[data-tracker-card="${currentCard}"] span`)?.textContent || "Register";
  document.getElementById("tracker-detail-title").textContent = title;
  document.getElementById("tracker-detail-copy").textContent = copy;
  const detailList = document.getElementById("tracker-detail-list");
  detailList.textContent = "";
  const detailFragment = document.createDocumentFragment();
  labels.forEach((label, index) => {
    const field = document.createElement("label");
    field.className = "legal-diary-edit-field";

    const labelSpan = document.createElement("span");
    labelSpan.textContent = label;
    field.appendChild(labelSpan);

    const input = document.createElement("input");
    input.dataset.trackerField = String(index);
    input.dataset.trackerLabel = label;
    input.value = fieldValueFor(label, saved);
    input.placeholder = "Enter value (preview only)";
    field.appendChild(input);

    detailFragment.appendChild(field);
  });
  detailList.appendChild(detailFragment);

  document.querySelectorAll("[data-tracker-card]").forEach((item) => {
    item.classList.toggle("active", item.getAttribute("data-tracker-card") === currentCard);
  });
  if (syncTab) {
    updateActiveTab(currentCard);
  }

  if (scroll) {
    document.getElementById("tracker-detail")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

function updateActiveTab(tab) {
  document.querySelectorAll("[data-tracker-tab]").forEach((button) => {
    const active = button.getAttribute("data-tracker-tab") === tab;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
}

function getDrafts() {
  try {
    return JSON.parse(localStorage.getItem(storageKey) || "{}");
  } catch {
    return {};
  }
}

function getSavedValues(role, card) {
  return getDrafts()?.[role]?.[card] || {};
}

function isCorruptedSample(value) {
  const text = String(value || "").trim();
  if (!text) return false;
  // Known mangled preview drafts from typing inside "Structured field" / bad caps.
  if (/structured field/i.test(text)) return true;
  if (/stru.*ctured/i.test(text)) return true;
  if (/^doen$/i.test(text)) return true;
  if (/ramkumar/i.test(text) && text !== "Ramkumar") return true;
  if (/high\s*c\s*ourt|banglaore|banglalore|banglaore/i.test(text)) return true;
  // Mixed-case gibberish like rAMKUMAR / cOURT
  if (/[a-z][A-Z]{2,}/.test(text) && /[A-Z][a-z][A-Z]/.test(text)) return true;
  return false;
}

function sanitizeSavedValues(saved) {
  const cleaned = {};
  Object.entries(saved || {}).forEach(([label, value]) => {
    if (!isCorruptedSample(value)) {
      cleaned[label] = value;
    }
  });
  return cleaned;
}

function sampleValue(label) {
  const key = String(label || "").trim().toLowerCase();
  const samples = {
    "matter number": "OS/219-2024-25",
    "client name": "Ramkumar",
    "court / forum": "High Court, Bengaluru",
    "next date": "23-05-2026",
    "filing stage": "Done",
    "limitation status": "Within limitation",
    "client contact": "Client desk / mobile",
    "instruction status": "Awaiting affidavit",
    "documents pending": "Vakalatnama, annexures",
    "last follow-up": "15-05-2026",
    "next reminder": "20-05-2026",
    "escalation owner": "Chamber clerk",
    retainer: "Rs. 25,000",
    "drafting fee": "Rs. 7,500",
    "appearance fee": "Rs. 5,000",
    expenses: "Rs. 1,200",
    "amount received": "Rs. 20,000",
    "balance due": "Rs. 18,700",
    "gstin / pan": "29ABCDE1234F1Z5",
    "notice reference": "SCN/GST/2024/081",
    "assessment year": "2024-25",
    "portal status": "Reply pending",
    "working paper owner": "Tax manager",
    "due date": "30-05-2026",
    "entity name": "Acme Services LLP",
    "cin / llpin": "AAB-1234",
    "filing event": "Form 11 annual return",
    "board action": "Circulation approved",
    "mca form": "Form 11",
  };
  if (samples[key]) return samples[key];
  if (/date|due|reminder/i.test(label)) return "30-05-2026";
  if (/fee|retainer|received|balance|outstanding|collections|expenses/i.test(label)) {
    return "Rs. 0";
  }
  if (/status|stage|approval|pending/i.test(label)) return "Pending";
  if (/owner|contact|client|director|partner/i.test(label)) return "Assigned person";
  if (/court|forum|authority/i.test(label)) return "High Court, Bengaluru";
  return "";
}

function fieldValueFor(label, saved) {
  const raw = saved?.[label];
  if (raw == null || String(raw).trim() === "" || isCorruptedSample(raw)) {
    return sampleValue(label);
  }
  return String(raw);
}

function setSaveStatus(message) {
  const target = document.getElementById("tracker-save-status");
  if (target) target.textContent = message;
}

function saveCurrentDetail() {
  const drafts = getDrafts();
  drafts[currentRole] = drafts[currentRole] || {};
  drafts[currentRole][currentCard] = {};

  document.querySelectorAll("[data-tracker-field]").forEach((input) => {
    drafts[currentRole][currentCard][input.getAttribute("data-tracker-label")] = input.value.trim();
  });

  localStorage.setItem(storageKey, JSON.stringify(drafts));
  setSaveStatus("Saved in this browser for this signed-in workspace preview. Backend sync will be enabled in the tracker persistence phase.");
}

function setRowEditorVisible(visible) {
  if (!rowEditor) return;
  rowEditor.hidden = !visible;
  if (visible) {
    rowEditor.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function openRowEditor(rowIndex = null) {
  if (livePractice) {
    setSaveStatus("Live matter board is read-only here. Create or update matters through the practice APIs (Stage 3 foundation).");
    return;
  }
  const rows = getRoleRows();
  const row = rowIndex === null ? null : rows[rowIndex];
  editingRowIndex = rowIndex;
  if (rowEditorKicker) rowEditorKicker.textContent = row ? "Edit work item" : "New work item";
  if (rowEditorTitle) rowEditorTitle.textContent = row ? "Update compliance work" : "Log compliance work";
  if (rowDateInput) rowDateInput.value = row?.date || todayIso();
  if (rowReferenceInput) rowReferenceInput.value = row?.reference || "";
  if (rowAuthorityInput) rowAuthorityInput.value = row?.authority || "";
  if (rowPurposeInput) rowPurposeInput.value = row?.purpose || "";
  if (rowStatusInput) rowStatusInput.value = row?.status || "pending";
  setRowEditorVisible(true);
  rowReferenceInput?.focus();
}

function closeRowEditor() {
  editingRowIndex = null;
  rowEditor?.reset();
  setRowEditorVisible(false);
}

function saveRowFromEditor(event) {
  event.preventDefault();
  const isEditing = editingRowIndex !== null;
  const row = normalizeRow({
    date: rowDateInput?.value || todayIso(),
    reference: rowReferenceInput?.value,
    authority: rowAuthorityInput?.value,
    purpose: rowPurposeInput?.value,
    status: rowStatusInput?.value || "pending",
  });

  if (!row.reference || !row.authority || !row.purpose) {
    setSaveStatus("Please enter reference, authority/court, and purpose before saving the work item.");
    return;
  }

  const rows = getRoleRows();
  if (!isEditing) {
    rows.unshift(row);
  } else {
    rows[editingRowIndex] = row;
  }
  persistRoleRows(rows);
  renderRows(rows);
  updateMetricsForRows();
  closeRowEditor();
  setSaveStatus(isEditing ? "Work item updated." : "Work item saved.");
}

function deleteRow(rowIndex) {
  if (livePractice) {
    setSaveStatus("Live matter board is read-only here.");
    return;
  }
  const rows = getRoleRows();
  if (!rows[rowIndex]) return;
  rows.splice(rowIndex, 1);
  persistRoleRows(rows);
  renderRows(rows);
  updateMetricsForRows();
  closeRowEditor();
  setSaveStatus("Work item deleted.");
}

function resetCurrentDetail() {
  const drafts = getDrafts();
  if (drafts[currentRole]) {
    delete drafts[currentRole][currentCard];
  }
  localStorage.setItem(storageKey, JSON.stringify(drafts));
  renderDetail(currentCard, { scroll: false, syncTab: false });
  setSaveStatus("Reset to clean sample fields.");
}

document.querySelectorAll("[data-tracker-role]").forEach((button) => {
  button.addEventListener("click", () => setRole(button.getAttribute("data-tracker-role")));
});

document.querySelectorAll("[data-tracker-card]").forEach((card) => {
  card.addEventListener("click", () => renderDetail(card.getAttribute("data-tracker-card")));
  card.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      renderDetail(card.getAttribute("data-tracker-card"));
    }
  });
});

document.getElementById("tracker-save")?.addEventListener("click", saveCurrentDetail);
document.getElementById("tracker-reset")?.addEventListener("click", resetCurrentDetail);
document.getElementById("tracker-add-row")?.addEventListener("click", () => openRowEditor(null));
document.getElementById("tracker-row-cancel")?.addEventListener("click", closeRowEditor);
rowEditor?.addEventListener("submit", saveRowFromEditor);
document.getElementById("tracker-rows")?.addEventListener("click", (event) => {
  const target = event.target instanceof Element ? event.target.closest("[data-row-action]") : null;
  if (!(target instanceof HTMLElement)) return;
  const index = Number(target.getAttribute("data-row-index"));
  if (!Number.isInteger(index)) return;
  const action = target.getAttribute("data-row-action");
  if (action === "edit") {
    openRowEditor(index);
  } else if (action === "delete") {
    deleteRow(index);
  }
});

document.querySelectorAll("[data-tracker-tab]").forEach((button) => {
  button.addEventListener("click", () => {
    const tab = button.getAttribute("data-tracker-tab") || "daily-board";
    updateActiveTab(tab);
    if (tab === "daily-board") {
      document.getElementById("daily-board")?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    renderDetail(tab);
  });
});

setRole("advocate");
updateActiveTab("daily-board");
updatePracticeBanner();
loadLivePractice();
document.getElementById("morning-brief-refresh")?.addEventListener("click", () => {
  loadMorningBrief(true);
});
const initialTab = String(window.location.hash || "").replace("#", "");
if (initialTab && (initialTab === "daily-board" || registerCardOrder.includes(initialTab))) {
  if (initialTab === "daily-board") {
    updateActiveTab("daily-board");
    document.getElementById("daily-board")?.scrollIntoView({ behavior: "smooth", block: "start" });
  } else {
    renderDetail(initialTab);
  }
}
