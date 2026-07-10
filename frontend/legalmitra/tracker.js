const trackerProfiles = {
  advocate: {
    metrics: [
      ["Today's hearings", "0"],
      ["Pending tasks", "12"],
      ["Active cases", "48"],
      ["Fees outstanding", "Rs. 1,24,500"],
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
      ["GST notices due", "7"],
      ["Pending filings", "19"],
      ["Active clients", "86"],
      ["Fees outstanding", "Rs. 2,18,000"],
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
      ["Board actions due", "5"],
      ["MCA filings", "14"],
      ["Active entities", "62"],
      ["Fees outstanding", "Rs. 1,76,500"],
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
const storageKey = "legalmitra-tracker-drafts";
const rowStorageKey = "legalmitra-tracker-work-items";
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

function getRoleRows(role = currentRole) {
  const stored = getStoredRows();
  const savedRows = Array.isArray(stored[role]) ? stored[role].map(normalizeRow) : [];
  if (savedRows.length) return savedRows;
  return (trackerProfiles[role]?.rows || trackerProfiles.advocate.rows).map(normalizeRow);
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
  const rows = getRoleRows();
  const urgentCount = rows.filter((row) => row.status === "urgent").length;
  const pendingCount = rows.filter((row) => row.status !== "done").length;
  const metrics = [...profile.metrics];
  metrics[0] = [metrics[0][0], String(urgentCount)];
  metrics[1] = [metrics[1][0], String(pendingCount)];
  metrics.forEach(([label, value], index) => {
    document.getElementById(`metric-label-${index + 1}`).textContent = label;
    document.getElementById(`metric-value-${index + 1}`).textContent = value;
  });
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
  const saved = getSavedValues(currentRole, currentCard);

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
    input.value = saved[label] || sampleValue(label);
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
  setSaveStatus("Reset to sample fields.");
}

function sampleValue(label) {
  if (/date|due|reminder/i.test(label)) return "Track with reminder";
  if (/fee|retainer|received|balance|outstanding|collections|expenses/i.test(label)) return "Rs. mapped ledger";
  if (/status|stage|approval|pending/i.test(label)) return "Pending / Review / Done";
  if (/owner|contact|client|director|partner/i.test(label)) return "Assigned person";
  return "Structured field";
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
const initialTab = String(window.location.hash || "").replace("#", "");
if (initialTab && (initialTab === "daily-board" || registerCardOrder.includes(initialTab))) {
  if (initialTab === "daily-board") {
    updateActiveTab("daily-board");
    document.getElementById("daily-board")?.scrollIntoView({ behavior: "smooth", block: "start" });
  } else {
    renderDetail(initialTab);
  }
}
