import { apiRequest, getAccessToken } from "../shared/api-client.js";
import { createCustodyController } from "./tracker-custody.js";
import { createDocumentRegisterController } from "./tracker-register.js";
import {
  createPracticeWorkspaceController,
  filterDashboardByPersona,
} from "./tracker-practice.js";
import {
  createProactiveController,
  parsePracticeDeepLink,
} from "./tracker-proactive.js";
import {
  fieldValueFor,
  sanitizeSavedValues,
  trackerProfiles,
} from "./tracker-preview.js";

const APP_KEY = "legalmitra";

let currentRole = "advocate";
let currentCard = "case-master";
let editingRowIndex = null;
let livePractice = null;
let livePracticeLoadError = false;
let morningBrief = null;
let activeWorkflowRun = null;
let feeSummary = null;
let feeInvoices = [];
const storageKey = "legalmitra-tracker-drafts-v2";
const rowStorageKey = "legalmitra-tracker-work-items-v2";
const registerCardOrder = ["case-master", "clients", "fee-ledger"];

const custody = createCustodyController({
  apiRequest,
  getAccessToken,
  appKey: APP_KEY,
  getLivePractice: () => livePractice,
  setLivePracticeDocCustody: (summary) => {
    if (livePractice) livePractice.doc_custody = summary;
  },
});

const documentRegister = createDocumentRegisterController({
  apiRequest,
  getAccessToken,
  appKey: APP_KEY,
  getCustodyMode: () =>
    livePractice?.doc_custody?.doc_custody_mode ||
    "cloud_minimized",
});

const practiceWorkspace = createPracticeWorkspaceController({
  apiRequest,
  getAccessToken,
  appKey: APP_KEY,
  getLivePractice: () => livePractice,
  getCurrentRole: () => currentRole,
  onPracticeMutated: async () => {
    await loadLivePractice();
  },
});

async function openMatterActInPlace(matterId, focus = "matter-brief") {
  if (!matterId || !getAccessToken()) return;
  if (focus === "document-register") {
    await documentRegister.selectMatter(matterId);
    return;
  }
  await practiceWorkspace.openMatterActInPlace(matterId, focus || "matter-brief");
}

const proactive = createProactiveController({
  apiRequest,
  getAccessToken,
  appKey: APP_KEY,
  getCurrentRole: () => currentRole,
  getMorningBrief: () => morningBrief,
  setMorningBrief: (value) => {
    morningBrief = value;
  },
  onStartWorkflow: (item, button) => startRecommendedWorkflow(item, button),
  onOpenMatter: openMatterActInPlace,
  onPracticeMutated: async () => {
    await loadLivePractice({ skipProactive: true });
  },
});

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
      matter_id: "",
      practice_area: "",
    };
  }
  return {
    date: String(row?.date || ""),
    reference: String(row?.reference || ""),
    authority: String(row?.authority || ""),
    purpose: String(row?.purpose || ""),
    status: String(row?.status || "pending").toLowerCase(),
    matter_id: String(row?.matter_id || ""),
    practice_area: String(row?.practice_area || ""),
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

    if (row.matter_id && getAccessToken()) {
      const openBrief = document.createElement("button");
      openBrief.type = "button";
      openBrief.dataset.rowAction = "brief";
      openBrief.dataset.matterId = row.matter_id;
      openBrief.setAttribute("aria-label", "Open matter brief");
      openBrief.textContent = "Open brief";
      actions.append(openBrief);
    } else {
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
    }
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

function liveMatterRows(role = currentRole) {
  if (!livePractice) return null;
  const filtered = filterDashboardByPersona(livePractice, role) || livePractice;
  const hearings = (filtered.upcoming_hearings || []).map((item) => ({
    date: formatPracticeDate(item.next_hearing_date),
    reference: item.matter_number || item.matter_id || "",
    authority: item.court || "—",
    purpose: item.title || "Hearing",
    status: item.status || "pending",
    matter_id: item.matter_id || "",
    practice_area: item.practice_area || "",
  }));
  const deadlines = (filtered.upcoming_deadlines || []).map((item) => ({
    date: formatPracticeDate(item.next_deadline_date),
    reference: item.matter_number || item.matter_id || "",
    authority: "Compliance deadline",
    purpose: item.title || "Deadline",
    status: item.status || "pending",
    matter_id: item.matter_id || "",
    practice_area: item.practice_area || "",
  }));
  return [...hearings, ...deadlines];
}

function getRoleRows(role = currentRole) {
  if (getAccessToken()) {
    if (livePractice) return liveMatterRows(role).map(normalizeRow);
    return [];
  }
  const stored = getStoredRows();
  const savedRows = Array.isArray(stored[role]) ? stored[role].map(normalizeRow) : [];
  if (savedRows.length) return savedRows;
  return (trackerProfiles[role]?.rows || trackerProfiles.advocate.rows).map(normalizeRow);
}

function updatePracticeBanner() {
  const banner = document.querySelector(".legal-tracker-preview-banner");
  if (!banner) return;
  if (livePractice) {
    const hearings = (livePractice.upcoming_hearings || []).length;
    const deadlines = (livePractice.upcoming_deadlines || []).length;
    if (!hearings && !deadlines && !(livePractice.active_matters || livePractice.pending_matters)) {
      banner.textContent =
        "Live practice workspace — no hearings or deadlines yet. Add a client and matter below; browser preview rows are disabled while signed in.";
    } else {
      banner.textContent =
        "Live practice workspace — metrics and boards come from your tenant clients and matters. Persona switch filters the board by practice area.";
    }
  } else if (getAccessToken()) {
    banner.textContent = livePracticeLoadError
      ? "Signed in, but the practice API did not respond. The board stays empty so browser demo rows are never mistaken for live records."
      : "Signed in — loading live practice data…";
  } else {
    banner.textContent =
      "Preview workspace — sign in to load tenant-backed clients, matters, hearings, Morning Brief, and fee records. Browser-only rows are not the system of record.";
  }
}

async function loadLivePractice(options = {}) {
  const { skipProactive = false } = options;
  if (!getAccessToken()) {
    livePractice = null;
    livePracticeLoadError = false;
    morningBrief = null;
    custody.clearCustodySettings();
    practiceWorkspace.showSignedInPanels(false);
    updatePracticeBanner();
    renderMorningBrief();
    renderRows(getRoleRows());
    updateMetricsForRows();
    practiceWorkspace.renderLiveWidgets();
    await proactive.refreshAll();
    return;
  }
  livePracticeLoadError = false;
  try {
    const result = await apiRequest(APP_KEY, "/api/v1/legal/practice/dashboard?limit=8", {
      method: "GET",
      timeoutMs: 12000,
    });
    if (result?.ok && result.payload) {
      livePractice = result.payload;
    } else {
      livePractice = null;
      livePracticeLoadError = true;
    }
  } catch (_error) {
    livePractice = null;
    livePracticeLoadError = true;
  }
  updatePracticeBanner();
  updateMetricsForRows();
  renderRows(getRoleRows());
  await Promise.all([
    skipProactive ? Promise.resolve() : proactive.refreshAll(),
    loadFeeLedger(),
    custody.loadCustodySettings(livePractice),
    documentRegister.loadMatters(),
    practiceWorkspace.refreshClientsAndMatters(),
  ]);
  practiceWorkspace.renderLiveWidgets();
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
  proactive.renderMorningBrief();
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

  const addBtn = (label, onClick) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = label;
    btn.addEventListener("click", onClick);
    actionsEl.appendChild(btn);
  };
  const awaiting = steps.find((s) => s.status === "awaiting_human");
  if (awaiting) {
    addBtn(`Approve ${awaiting.step_key}`, () => approveWorkflowStep(run.run_id, awaiting.step_id));
    addBtn(`Reject ${awaiting.step_key}`, () => rejectWorkflowStep(run.run_id, awaiting.step_id));
  }
  const retryable = steps.find(
    (s) =>
      s.status === "rejected" ||
      s.status === "failed" ||
      (s.status === "awaiting_human" && s.failure_class === "requires_human"),
  );
  const open = run.status !== "cancelled" && run.status !== "completed";
  if (retryable && open) addBtn(`Retry ${retryable.step_key}`, () => retryWorkflowStep(run.run_id, retryable.step_id));
  if (open) addBtn("Cancel run", () => cancelWorkflowRun(run.run_id));
  if (run.status === "completed" && !run.ready_to_file) {
    addBtn("Mark ready to file (does not file)", () => markReadyToFile(run.run_id));
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
function workflowErrorDetail(result) {
  const payload = result?.payload;
  if (typeof payload === "string" && payload.trim()) return payload;
  if (payload && typeof payload === "object") {
    if (typeof payload.detail === "string") return payload.detail;
    if (Array.isArray(payload.detail)) {
      return payload.detail
        .map((row) => (typeof row === "string" ? row : row?.msg || JSON.stringify(row)))
        .join("; ");
    }
    if (payload.message) return String(payload.message);
    return JSON.stringify(payload);
  }
  return `HTTP ${result?.status || 0}`;
}

function workflowStepUrl(runId, stepId, action) {
  return `/api/v1/legal/workflows/runs/${encodeURIComponent(runId)}/steps/${encodeURIComponent(stepId)}/${action}`;
}

async function runWorkflowMutation(busyText, failText, path, opts = {}) {
  const statusEl = document.getElementById("workflow-run-status");
  if (statusEl) statusEl.textContent = busyText;
  const result = await apiRequest(APP_KEY, path, { method: "POST", timeoutMs: 45000, ...opts });
  if (!result?.ok) {
    if (statusEl) statusEl.textContent = `${failText}: ${workflowErrorDetail(result)}`;
    return;
  }
  activeWorkflowRun = result.payload;
  renderWorkflowRun();
}

async function approveWorkflowStep(runId, stepId) {
  await runWorkflowMutation(
    "Approving step…",
    "Could not approve step",
    workflowStepUrl(runId, stepId, "approve"),
  );
}

async function rejectWorkflowStep(runId, stepId) {
  const reason = window.prompt("Rejection reason (required for audit):", "Needs revision");
  if (!reason || reason.trim().length < 2) return;
  await runWorkflowMutation(
    "Rejecting step…",
    "Could not reject step",
    workflowStepUrl(runId, stepId, "reject"),
    { timeoutMs: 20000, body: JSON.stringify({ reason: reason.trim() }) },
  );
}

async function retryWorkflowStep(runId, stepId) {
  await runWorkflowMutation(
    "Retrying step…",
    "Could not retry step",
    workflowStepUrl(runId, stepId, "retry"),
    { body: JSON.stringify({}) },
  );
}

async function cancelWorkflowRun(runId) {
  await runWorkflowMutation(
    "Cancelling run…",
    "Could not cancel run",
    `/api/v1/legal/workflows/runs/${encodeURIComponent(runId)}/cancel`,
    { timeoutMs: 15000, body: JSON.stringify({}) },
  );
}

async function markReadyToFile(runId) {
  await runWorkflowMutation(
    "Marking ready to file…",
    "Could not mark ready to file",
    `/api/v1/legal/workflows/runs/${encodeURIComponent(runId)}/ready-to-file`,
    { timeoutMs: 15000, body: JSON.stringify({ ready_to_file: true, confirm: true }) },
  );
}

async function loadMorningBrief(forceRefresh) {
  await proactive.loadMorningBrief(forceRefresh);
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
  practiceWorkspace.renderLiveWidgets();
  practiceWorkspace.refreshClientsAndMatters();

  document.querySelectorAll("[data-tracker-role]").forEach((button) => {
    const active = button.getAttribute("data-tracker-role") === role;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });

  if (getAccessToken()) {
    loadMorningBrief(false);
    proactive.loadAlerts();
  }
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

function setSaveStatus(message) {
  const target = document.getElementById("tracker-save-status");
  if (target) target.textContent = message;
}

function saveCurrentDetail() {
  if (getAccessToken()) {
    setSaveStatus(
      "Signed in — practice clients and matters are saved through the live forms above, not browser draft fields.",
    );
    return;
  }
  const drafts = getDrafts();
  drafts[currentRole] = drafts[currentRole] || {};
  drafts[currentRole][currentCard] = {};

  document.querySelectorAll("[data-tracker-field]").forEach((input) => {
    drafts[currentRole][currentCard][input.getAttribute("data-tracker-label")] = input.value.trim();
  });

  localStorage.setItem(storageKey, JSON.stringify(drafts));
  setSaveStatus("Saved in this browser for preview only. Sign in to use tenant-backed clients and matters.");
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
  if (getAccessToken()) {
    practiceWorkspace.openNewMatterForm();
    setSaveStatus("Use New matter to create a tenant-backed engagement. Preview work-item edits stay available only when signed out.");
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
  if (getAccessToken()) {
    setSaveStatus("Signed-in boards are live practice data — delete preview rows only when signed out.");
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
  if (getAccessToken()) {
    setSaveStatus("Signed in — register sample fields are presentation labels only. Use Clients and matters above for real records.");
    renderDetail(currentCard, { scroll: false, syncTab: false });
    return;
  }
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
  const action = target.getAttribute("data-row-action");
  if (action === "brief") {
    const matterId = target.getAttribute("data-matter-id");
    if (matterId) {
      document.getElementById("matter-brief-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
      practiceWorkspace.loadBriefForMatter(matterId, { generate: false });
    }
    return;
  }
  const index = Number(target.getAttribute("data-row-index"));
  if (!Number.isInteger(index)) return;
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

practiceWorkspace.bindEvents();
proactive.bindEvents();
setRole("advocate");
updateActiveTab("daily-board");
updatePracticeBanner();
custody.renderCustodyPanel();
documentRegister.bindEvents();
loadLivePractice().then(async () => {
  const deep = parsePracticeDeepLink();
  if (deep.matterId && getAccessToken()) {
    await openMatterActInPlace(deep.matterId, deep.focus || "matter-brief");
  }
});
document.getElementById("morning-brief-refresh")?.addEventListener("click", () => {
  loadMorningBrief(true);
});
document.getElementById("custody-save")?.addEventListener("click", () => {
  custody.saveCustodySettings().then(() => documentRegister.renderEmptyCopy());
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
