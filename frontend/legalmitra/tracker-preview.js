/* LegalMitra Tracker — signed-out preview profiles and sample field helpers.
   Not the practice system of record when authenticated. */

export const trackerProfiles = {
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

export function isCorruptedSample(value) {
  const text = String(value || "").trim();
  if (!text) return false;
  if (/structured field/i.test(text)) return true;
  if (/stru.*ctured/i.test(text)) return true;
  if (/^doen$/i.test(text)) return true;
  if (/ramkumar/i.test(text) && text !== "Ramkumar") return true;
  if (/high\s*c\s*ourt|banglaore|banglalore|banglaore/i.test(text)) return true;
  if (/[a-z][A-Z]{2,}/.test(text) && /[A-Z][a-z][A-Z]/.test(text)) return true;
  return false;
}

export function sanitizeSavedValues(saved) {
  const cleaned = {};
  Object.entries(saved || {}).forEach(([label, value]) => {
    if (!isCorruptedSample(value)) {
      cleaned[label] = value;
    }
  });
  return cleaned;
}

export function sampleValue(label) {
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

export function fieldValueFor(label, saved) {
  const raw = saved?.[label];
  if (raw == null || String(raw).trim() === "" || isCorruptedSample(raw)) {
    return sampleValue(label);
  }
  return String(raw);
}
