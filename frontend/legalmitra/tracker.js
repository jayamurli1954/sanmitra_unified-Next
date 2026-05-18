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
const storageKey = "legalmitra-tracker-drafts";

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderRows(rows) {
  const target = document.getElementById("tracker-rows");
  if (!target) return;
  target.innerHTML = rows.map(([date, reference, authority, purpose, status]) => `
    <tr>
      <td>${escapeHtml(date)}</td>
      <td>${escapeHtml(reference)}</td>
      <td>${escapeHtml(authority)}</td>
      <td>${escapeHtml(purpose)}</td>
      <td><span class="status ${escapeHtml(status)}">${escapeHtml(status)}</span></td>
      <td><button type="button" aria-label="Open action menu">...</button></td>
    </tr>
  `).join("");
}

function setRole(role) {
  const profile = trackerProfiles[role] || trackerProfiles.advocate;
  currentRole = role;

  profile.metrics.forEach(([label, value], index) => {
    document.getElementById(`metric-label-${index + 1}`).textContent = label;
    document.getElementById(`metric-value-${index + 1}`).textContent = value;
  });

  profile.registers.forEach(([title, copy], index) => {
    document.getElementById(`register-title-${index + 1}`).textContent = title;
    document.getElementById(`register-copy-${index + 1}`).textContent = copy;
  });

  renderRows(profile.rows);
  renderDetail(currentCard);

  document.querySelectorAll("[data-tracker-role]").forEach((button) => {
    const active = button.getAttribute("data-tracker-role") === role;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
}

function renderDetail(card) {
  currentCard = card || "case-master";
  const profile = trackerProfiles[currentRole] || trackerProfiles.advocate;
  const cardIndex = ["case-master", "clients", "fee-ledger"].indexOf(currentCard);
  const safeIndex = cardIndex >= 0 ? cardIndex : 0;
  const [title, copy] = profile.registers[safeIndex];
  const labels = profile.details[currentCard] || profile.details["case-master"];
  const saved = getSavedValues(currentRole, currentCard);

  document.getElementById("tracker-detail-kicker").textContent = document.querySelector(`[data-tracker-card="${currentCard}"] span`)?.textContent || "Register";
  document.getElementById("tracker-detail-title").textContent = title;
  document.getElementById("tracker-detail-copy").textContent = copy;
  document.getElementById("tracker-detail-list").innerHTML = labels.map((label, index) => `
    <label class="legal-diary-edit-field">
      <span>${escapeHtml(label)}</span>
      <input data-tracker-field="${index}" data-tracker-label="${escapeHtml(label)}" value="${escapeHtml(saved[label] || sampleValue(label))}">
    </label>
  `).join("");

  document.querySelectorAll("[data-tracker-card]").forEach((item) => {
    item.classList.toggle("active", item.getAttribute("data-tracker-card") === currentCard);
  });

  document.getElementById("tracker-detail")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
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
  setSaveStatus("Saved in this browser for local E2E testing.");
}

function resetCurrentDetail() {
  const drafts = getDrafts();
  if (drafts[currentRole]) {
    delete drafts[currentRole][currentCard];
  }
  localStorage.setItem(storageKey, JSON.stringify(drafts));
  renderDetail(currentCard);
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

setRole("advocate");
