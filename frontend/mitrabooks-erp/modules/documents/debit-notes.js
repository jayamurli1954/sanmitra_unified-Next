// ====================================================================
// SECTION: DEBIT NOTES WORKSPACE
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initDebitNotes(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";
import { computeInvoiceLine, invoiceStatusPill } from "./sales-invoices.js";
import {
  purchaseUi,
  loadBusinessBills,
  vendorPartyOptions,
  expenseAccountOptions,
} from "./purchase-bills.js";

export const debitUi = {
  view: "list", // list | create | detail
  notes: [],
  detail: null,
  lineSeq: 0,
  formLines: [],
  reverseOpen: false,
  reasons: [
    ["purchase_return", "Purchase return"],
    ["rejected_goods", "Rejected goods"],
    ["price_revision", "Price revision (downward)"],
    ["deficiency", "Deficiency in service/goods"],
    ["other", "Other"],
  ],
  header: {
    vendor_party_id: "",
    note_date: "",
    original_bill_id: "",
    original_bill_number: "",
    reason: "purchase_return",
    is_inter_state: false,
    expense_account_code: "51001",
    place_of_supply: "",
    notes: "",
    cost_centre_id: "",
    project_id: "",
  },
};

/** @type {Record<string, Function> | null} */
let deps = null;

export function initDebitNotes(injected) {
  deps = injected;
  debitUi.header.note_date = injected.todayIsoDate();
}

function requireDeps() {
  if (!deps) {
    throw new Error("initDebitNotes() must be called before using debit note helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function todayIsoDate() { return requireDeps().todayIsoDate(); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function round2(value) { return requireDeps().round2(value); }
function reversalPanel(kind, id, isoDate) { return requireDeps().reversalPanel(kind, id, isoDate); }
function focusBusinessEntryField(selector) { requireDeps().focusBusinessEntryField(selector); }
function getCurrentExperience() { return requireDeps().getCurrentExperience(); }
function getActiveBusinessWorkspace() { return requireDeps().getActiveBusinessWorkspace(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function renderBusinessWorkspace() { return requireDeps().renderBusinessWorkspace(); }
function getLastBusinessParties() { return requireDeps().getLastBusinessParties(); }
function loadBusinessParties() { return requireDeps().loadBusinessParties(); }
function hasLoadedBusinessAccounts() { return requireDeps().hasLoadedBusinessAccounts(); }
function loadBusinessAccounts() { return requireDeps().loadBusinessAccounts(); }
function dimensionOptions(kind, selected) { return requireDeps().dimensionOptions(kind, selected); }
function getLastDimensions() { return requireDeps().getLastDimensions(); }
function loadDimensions() { return requireDeps().loadDimensions(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

export function rerenderDebitNoteIfActive() {
  if (getCurrentExperience() === "mitrabooks" && getActiveBusinessWorkspace() === "debit-notes") {
    getDashboardPreview().innerHTML = renderBusinessWorkspace();
    if (debitUi.view === "create") {
      focusBusinessEntryField("[data-dn-form] select[name='vendor_party_id']");
    }
  }
}

export async function loadDebitNotes() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/debit-notes?limit=100", { method: "GET" });
  debitUi.notes = result.ok && Array.isArray(result.payload?.items) ? result.payload.items : [];
  if (!result.ok) setLoginStatus("danger", "Unable to load debit notes", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  rerenderDebitNoteIfActive();
  renderJson(getApiOutput(), { debit_notes: { ok: result.ok, count: debitUi.notes.length } });
}

export function resolveDebitNoteSourceBill(billId) {
  return (Array.isArray(purchaseUi.bills) ? purchaseUi.bills : [])
    .find((bill) => String(bill.bill_id || "") === String(billId || ""));
}

export function debitNoteSourceBillOptions(selectedId) {
  const bills = Array.isArray(purchaseUi.bills) ? purchaseUi.bills : [];
  if (!bills.length) {
    return `<option value="">Load or create a source bill first</option>`;
  }
  return [
    `<option value="">Select source bill</option>`,
    ...bills.map((bill) => {
      const id = String(bill.bill_id || "");
      const number = String(bill.bill_number || id || "");
      const vendor = String(bill.vendor_name || bill.vendor_party_id || "");
      const total = formatCurrency(bill.bill_total || bill.net_payable || 0);
      const selected = id && id === String(selectedId || "") ? "selected" : "";
      return `<option value="${escapeHtml(id)}" ${selected}>${escapeHtml(number)} - ${escapeHtml(vendor)} - ${escapeHtml(total)}</option>`;
    }),
  ].join("");
}

export function syncDnFormFromDom() {
  const form = document.querySelector("[data-dn-form]");
  if (!form) return;
  const val = (sel) => form.querySelector(sel)?.value ?? "";
  debitUi.header.vendor_party_id = val("select[name='vendor_party_id']");
  debitUi.header.note_date = val("input[name='note_date']") || todayIsoDate();
  debitUi.header.original_bill_id = val("select[name='original_bill_id']");
  const selectedBill = resolveDebitNoteSourceBill(debitUi.header.original_bill_id);
  debitUi.header.original_bill_number = selectedBill?.bill_number || "";
  debitUi.header.reason = val("select[name='reason']") || "purchase_return";
  debitUi.header.is_inter_state = !!form.querySelector("input[name='is_inter_state']")?.checked;
  debitUi.header.expense_account_code = val("select[name='expense_account_code']") || "51001";
  debitUi.header.place_of_supply = val("input[name='place_of_supply']");
  debitUi.header.notes = val("textarea[name='notes']");
  debitUi.header.cost_centre_id = val("select[name='cost_centre_id']");
  debitUi.header.project_id = val("select[name='project_id']");
  debitUi.formLines = Array.from(form.querySelectorAll("[data-dn-line]")).map((row) => ({
    id: row.getAttribute("data-dn-line"),
    description: row.querySelector("input[name='description']")?.value || "",
    hsn_sac: row.querySelector("input[name='hsn_sac']")?.value || "",
    quantity: row.querySelector("input[name='quantity']")?.value || "",
    rate: row.querySelector("input[name='rate']")?.value || "",
    gst_rate: row.querySelector("input[name='gst_rate']")?.value || "",
    cost_centre_id: row.querySelector("select[name='line_cost_centre_id']")?.value || "",
    project_id: row.querySelector("select[name='line_project_id']")?.value || "",
  }));
}

export function updateDnTotalsDisplay() {
  const form = document.querySelector("[data-dn-form]");
  if (!form) return;
  const inter = !!form.querySelector("input[name='is_inter_state']")?.checked;
  let taxableTotal = 0, cgstTotal = 0, sgstTotal = 0, igstTotal = 0;
  form.querySelectorAll("[data-dn-line]").forEach((row) => {
    const c = computeInvoiceLine(
      row.querySelector("input[name='quantity']")?.value,
      row.querySelector("input[name='rate']")?.value,
      row.querySelector("input[name='gst_rate']")?.value,
      inter,
    );
    row.querySelector("[data-line-taxable]").textContent = formatCurrency(c.taxable);
    row.querySelector("[data-line-gst]").textContent = formatCurrency(c.cgst + c.sgst + c.igst);
    row.querySelector("[data-line-total]").textContent = formatCurrency(c.total);
    taxableTotal += c.taxable; cgstTotal += c.cgst; sgstTotal += c.sgst; igstTotal += c.igst;
  });
  const gstTotal = round2(cgstTotal + sgstTotal + igstTotal);
  const noteTotal = round2(taxableTotal + gstTotal);
  const set = (sel, v) => { const el = form.querySelector(sel); if (el) el.textContent = formatCurrency(v); };
  set("[data-total-taxable]", taxableTotal);
  set("[data-total-cgst]", cgstTotal);
  set("[data-total-sgst]", sgstTotal);
  set("[data-total-igst]", igstTotal);
  set("[data-total-note]", noteTotal);
  const cgstRow = form.querySelector("[data-row-cgst]");
  const sgstRow = form.querySelector("[data-row-sgst]");
  const igstRow = form.querySelector("[data-row-igst]");
  if (cgstRow && sgstRow && igstRow) {
    cgstRow.hidden = inter;
    sgstRow.hidden = inter;
    igstRow.hidden = !inter;
  }
}

export function setDebitNoteView(view) {
  debitUi.view = view;
  debitUi.reverseOpen = false;
  rerenderDebitNoteIfActive();
  if (view === "create") {
    updateDnTotalsDisplay();
    focusBusinessEntryField("[data-dn-form] select[name='vendor_party_id']");
  }
}

export function openDebitNoteCreate() {
  debitUi.formLines = [{ id: `dn-${++debitUi.lineSeq}`, description: "", hsn_sac: "", quantity: "1", rate: "", gst_rate: "18", cost_centre_id: "", project_id: "" }];
  debitUi.header.vendor_party_id = "";
  debitUi.header.note_date = todayIsoDate();
  debitUi.header.original_bill_id = "";
  debitUi.header.original_bill_number = "";
  debitUi.header.reason = "purchase_return";
  debitUi.header.is_inter_state = false;
  debitUi.header.expense_account_code = "51001";
  debitUi.header.place_of_supply = "";
  debitUi.header.notes = "";
  debitUi.header.cost_centre_id = "";
  debitUi.header.project_id = "";
  if (!Array.isArray(getLastBusinessParties()) || getLastBusinessParties().length === 0) loadBusinessParties();
  if (!hasLoadedBusinessAccounts()) loadBusinessAccounts();
  if (!Array.isArray(purchaseUi.bills) || purchaseUi.bills.length === 0) loadBusinessBills();
  if (!getLastDimensions()) loadDimensions().then(() => rerenderDebitNoteIfActive());
  setDebitNoteView("create");
}

export function addDnLine() {
  syncDnFormFromDom();
  debitUi.formLines.push({ id: `dn-${++debitUi.lineSeq}`, description: "", hsn_sac: "", quantity: "1", rate: "", gst_rate: "18", cost_centre_id: "", project_id: "" });
  rerenderDebitNoteIfActive();
  updateDnTotalsDisplay();
}

export function removeDnLine(lineId) {
  syncDnFormFromDom();
  debitUi.formLines = debitUi.formLines.filter((l) => l.id !== lineId);
  if (debitUi.formLines.length === 0) {
    debitUi.formLines.push({ id: `dn-${++debitUi.lineSeq}`, description: "", hsn_sac: "", quantity: "1", rate: "", gst_rate: "18", cost_centre_id: "", project_id: "" });
  }
  rerenderDebitNoteIfActive();
  updateDnTotalsDisplay();
}

export async function submitDebitNote() {
  syncDnFormFromDom();
  if (!debitUi.header.vendor_party_id) {
    setLoginStatus("warn", "Vendor required", "Select the vendor for this debit note.");
    return;
  }
  const sourceBill = resolveDebitNoteSourceBill(debitUi.header.original_bill_id);
  if (!sourceBill) {
    setLoginStatus("warn", "Source bill required", "Select the supplier bill this debit note adjusts.");
    return;
  }
  const lineItems = debitUi.formLines
    .filter((l) => String(l.description).trim() && Number(l.quantity) > 0)
    .map((l) => ({
      description: String(l.description).trim(),
      hsn_sac: String(l.hsn_sac || "").trim() || null,
      quantity: String(Number(l.quantity)),
      rate: String(Number(l.rate || 0)),
      gst_rate: String(Number(l.gst_rate || 0)),
      cost_centre_id: String(l.cost_centre_id || "").trim() || null,
      project_id: String(l.project_id || "").trim() || null,
    }));
  if (lineItems.length === 0) {
    setLoginStatus("warn", "Add a line item", "Enter at least one line with a description and quantity.");
    return;
  }
  const body = {
    vendor_party_id: debitUi.header.vendor_party_id,
    note_date: debitUi.header.note_date || todayIsoDate(),
    original_bill_id: debitUi.header.original_bill_id || null,
    original_bill_number: String(debitUi.header.original_bill_number || "").trim() || null,
    reason: debitUi.header.reason || "purchase_return",
    is_inter_state: !!debitUi.header.is_inter_state,
    expense_account_code: debitUi.header.expense_account_code || "51001",
    place_of_supply: String(debitUi.header.place_of_supply || "").trim() || null,
    notes: String(debitUi.header.notes || "").trim() || null,
    cost_centre_id: debitUi.header.cost_centre_id || null,
    project_id: debitUi.header.project_id || null,
    line_items: lineItems,
  };
  const result = await apiRequest("mitrabooks", "/api/v1/business/debit-notes", {
    method: "POST",
    headers: { "X-Idempotency-Key": `debit-note-${Date.now()}` },
    body: JSON.stringify(body),
  });
  if (result.ok) {
    setLoginStatus("ok", "Debit note posted", `${result.payload?.debit_note_number || "Debit note"} posted to the ledger.`);
    await loadDebitNotes();
    setDebitNoteView("list");
  } else {
    setLoginStatus("danger", "Debit note failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { create_debit_note: { ok: result.ok, status: result.status, detail: result.payload?.detail || null } });
}

export async function openDebitNoteDetail(noteId) {
  const result = await apiRequest("mitrabooks", `/api/v1/business/debit-notes/${encodeURIComponent(noteId)}`, { method: "GET" });
  if (result.ok) {
    debitUi.detail = result.payload;
    setDebitNoteView("detail");
  } else {
    setLoginStatus("danger", "Unable to load debit note", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { debit_note_detail: { ok: result.ok, status: result.status } });
}

export async function cancelDebitNote(noteId, reversalDate) {
  const body = { reason: "Reversal" };
  if (reversalDate) body.cancel_date = reversalDate;
  const result = await apiRequest("mitrabooks", `/api/v1/business/debit-notes/${encodeURIComponent(noteId)}/cancel`, {
    method: "POST",
    headers: { "X-Idempotency-Key": `debit-note-cancel-${noteId}-${reversalDate || "today"}` },
    body: JSON.stringify(body),
  });
  if (result.ok) {
    debitUi.reverseOpen = false;
    setLoginStatus("ok", "Debit note reversed", "A reversing journal entry was posted.");
    await loadDebitNotes();
    if (debitUi.detail && debitUi.detail.debit_note_id === noteId) {
      debitUi.detail = result.payload;
    }
    rerenderDebitNoteIfActive();
  } else {
    setLoginStatus("danger", "Reverse failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { cancel_debit_note: { ok: result.ok, status: result.status } });
}

export function dnReasonLabel(value) {
  const found = debitUi.reasons.find((r) => r[0] === value);
  return found ? found[1] : (value || "");
}

export function renderDnListTable() {
  const rows = debitUi.notes;
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Debit Note #</th><th>Date</th><th>Vendor</th><th>Against</th>
            <th class="amount">Taxable</th><th class="amount">ITC</th><th class="amount">Total</th><th>Status</th><th>Open</th>
          </tr>
        </thead>
        <tbody>
          ${rows.length ? rows.map((n) => `
            <tr>
              <td>${escapeHtml(n.debit_note_number || "")}</td>
              <td>${escapeHtml(n.note_date || "")}</td>
              <td>${escapeHtml(n.vendor_name || n.vendor_party_id || "")}</td>
              <td>${escapeHtml(n.original_bill_number || "—")}</td>
              <td class="amount">${escapeHtml(formatCurrency(n.taxable_total || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(n.gst_total || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(n.note_total || 0))}</td>
              <td>${invoiceStatusPill(n.status)}</td>
              <td><button class="secondary" type="button" data-business-action="view-debit-note" data-dn-id="${escapeHtml(n.debit_note_id)}">View</button></td>
            </tr>
          `).join("") : `<tr><td colspan="9" class="muted">No debit notes yet.</td></tr>`}
        </tbody>
      </table>
    </div>
  `;
}

export function renderDebitNoteCreateForm() {
  const vendors = vendorPartyOptions();
  const expenseAccounts = expenseAccountOptions();
  const lineCostCentreOptions = (selected) => dimensionOptions("cost_centre", selected || "");
  const lineProjectOptions = (selected) => dimensionOptions("project", selected || "");
  const lineRows = debitUi.formLines.map((l) => `
    <tr data-dn-line="${escapeHtml(l.id)}">
      <td><input type="text" name="description" value="${escapeHtml(l.description)}" placeholder="Item / service"></td>
      <td><input type="text" name="hsn_sac" value="${escapeHtml(l.hsn_sac)}" placeholder="HSN/SAC"></td>
      <td><input type="number" name="quantity" value="${escapeHtml(l.quantity)}" min="0" step="any"></td>
      <td><input type="number" name="rate" value="${escapeHtml(l.rate)}" min="0" step="any" placeholder="0.00"></td>
      <td><input type="number" name="gst_rate" value="${escapeHtml(l.gst_rate)}" min="0" max="100" step="any"></td>
      <td>
        ${lineCostCentreOptions(l.cost_centre_id) ? `<select name="line_cost_centre_id" aria-label="Line cost centre">${lineCostCentreOptions(l.cost_centre_id)}</select>` : ""}
        ${lineProjectOptions(l.project_id) ? `<select name="line_project_id" aria-label="Line project">${lineProjectOptions(l.project_id)}</select>` : ""}
      </td>
      <td class="amount" data-line-taxable>—</td>
      <td class="amount" data-line-gst>—</td>
      <td class="amount" data-line-total>—</td>
      <td><button class="secondary" type="button" data-business-action="remove-dn-line" data-line-id="${escapeHtml(l.id)}">✕</button></td>
    </tr>
  `).join("");

  return `
    <div class="verification-panel erp-workspace-panel" data-dn-form>
      <div class="preview-heading compact">
        <div>
          <h4>New Debit Note</h4>
          <p>Reduce a vendor bill (return, rejected goods, or price revision). Reduces input GST (ITC) and payables.</p>
        </div>
        <button class="secondary" type="button" data-business-action="dn-back">← Back to list</button>
      </div>
      <div class="invoice-form-grid">
        <label>Vendor
          <select name="vendor_party_id">
            <option value="">Select vendor</option>
            ${vendors.map((v) => `<option value="${escapeHtml(v.party_id)}" ${v.party_id === debitUi.header.vendor_party_id ? "selected" : ""}>${escapeHtml(v.party_name)}${v.gstin ? ` (${escapeHtml(v.gstin)})` : ""}</option>`).join("")}
          </select>
        </label>
        <label>Note date
          <input type="date" name="note_date" value="${escapeHtml(debitUi.header.note_date)}">
        </label>
        <label>Against bill #
          <select name="original_bill_id" required data-source-document="purchase_bill">
            ${debitNoteSourceBillOptions(debitUi.header.original_bill_id)}
          </select>
        </label>
        <label>Reason
          <select name="reason">
            ${debitUi.reasons.map(([v, lbl]) => `<option value="${escapeHtml(v)}" ${v === debitUi.header.reason ? "selected" : ""}>${escapeHtml(lbl)}</option>`).join("")}
          </select>
        </label>
        <label>Expense account
          <select name="expense_account_code">
            ${expenseAccounts.length ? expenseAccounts.map((a) => `<option value="${escapeHtml(a.code)}" ${a.code === debitUi.header.expense_account_code ? "selected" : ""}>${escapeHtml(`${a.code} - ${a.name}`)}</option>`).join("") : `<option value="51001" selected>51001 - Purchases</option>`}
          </select>
        </label>
        <label>Place of supply
          <input type="text" name="place_of_supply" value="${escapeHtml(debitUi.header.place_of_supply)}" placeholder="State / code">
        </label>
        ${dimensionOptions("cost_centre", debitUi.header.cost_centre_id) ? `<label>Cost centre
          <select name="cost_centre_id">${dimensionOptions("cost_centre", debitUi.header.cost_centre_id)}</select>
        </label>` : ""}
        ${dimensionOptions("project", debitUi.header.project_id) ? `<label>Project
          <select name="project_id">${dimensionOptions("project", debitUi.header.project_id)}</select>
        </label>` : ""}
        <label class="invoice-inter-toggle">
          <input type="checkbox" name="is_inter_state" ${debitUi.header.is_inter_state ? "checked" : ""}>
          Inter-state supply (IGST)
        </label>
      </div>

      <div class="table-preview compact-table invoice-lines">
        <table>
          <thead>
            <tr>
              <th>Description</th><th>HSN/SAC</th><th>Qty</th><th>Rate</th><th>GST %</th><th>Line tags</th>
              <th class="amount">Taxable</th><th class="amount">ITC</th><th class="amount">Total</th><th></th>
            </tr>
          </thead>
          <tbody>${lineRows}</tbody>
        </table>
      </div>
      <button class="secondary" type="button" data-business-action="add-dn-line" aria-keyshortcuts="Alt+L">+ Add line</button>

      <div class="invoice-totals">
        <div><span>Taxable</span><strong data-total-taxable>${formatCurrency(0)}</strong></div>
        <div data-row-cgst ${debitUi.header.is_inter_state ? "hidden" : ""}><span>Input CGST</span><strong data-total-cgst>${formatCurrency(0)}</strong></div>
        <div data-row-sgst ${debitUi.header.is_inter_state ? "hidden" : ""}><span>Input SGST</span><strong data-total-sgst>${formatCurrency(0)}</strong></div>
        <div data-row-igst ${debitUi.header.is_inter_state ? "" : "hidden"}><span>Input IGST</span><strong data-total-igst>${formatCurrency(0)}</strong></div>
        <div class="invoice-grand"><span>Debit note total</span><strong data-total-note>${formatCurrency(0)}</strong></div>
      </div>

      <label class="invoice-notes">Notes
        <textarea name="notes" rows="2" placeholder="Optional notes">${escapeHtml(debitUi.header.notes)}</textarea>
      </label>

      <div class="invoice-form-actions">
        <button class="primary" type="button" data-business-action="save-debit-note" aria-keyshortcuts="Control+Enter">Post Debit Note</button>
        <button class="secondary" type="button" data-business-action="dn-back">Cancel</button>
      </div>
    </div>
  `;
}

export function renderDebitNoteDetail() {
  const n = debitUi.detail;
  if (!n) {
    return `<div class="verification-panel erp-workspace-panel"><p class="muted">Debit note not found.</p></div>`;
  }
  const lines = Array.isArray(n.line_items) ? n.line_items : [];
  const taxRow = n.is_inter_state
    ? `<div><span>Input IGST</span><strong>${formatCurrency(n.igst_total || 0)}</strong></div>`
    : `<div><span>Input CGST</span><strong>${formatCurrency(n.cgst_total || 0)}</strong></div><div><span>Input SGST</span><strong>${formatCurrency(n.sgst_total || 0)}</strong></div>`;
  return `
    <div class="verification-panel erp-workspace-panel" data-debit-note-printable>
      <div class="preview-heading compact">
        <div>
          <h4>Debit Note ${escapeHtml(n.debit_note_number || "")} ${invoiceStatusPill(n.status)}</h4>
          <p>${escapeHtml(n.vendor_name || n.vendor_party_id || "")}${n.vendor_gstin ? ` · ${escapeHtml(n.vendor_gstin)}` : ""} · ${escapeHtml(n.note_date || "")}${n.original_bill_number ? ` · against ${escapeHtml(n.original_bill_number)}` : ""}</p>
        </div>
        <div class="invoice-detail-actions">
          <button class="secondary" type="button" data-business-action="dn-back">← Back to list</button>
          <button class="secondary" type="button" data-business-action="print-debit-note">Print</button>
          <button class="secondary" type="button" data-business-action="export-debit-note-json">Export JSON</button>
          ${String(n.status).toLowerCase() === "posted" && !debitUi.reverseOpen ? `<button class="secondary" type="button" data-business-action="begin-reverse-dn">Reverse</button>` : ""}
        </div>
      </div>
      ${String(n.status).toLowerCase() === "posted" && debitUi.reverseOpen ? reversalPanel("dn", n.debit_note_id, n.note_date) : ""}
      <p class="muted">${escapeHtml(dnReasonLabel(n.reason))}${n.is_inter_state ? " · Inter-state (IGST input)" : " · Intra-state (CGST + SGST input)"}</p>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr><th>Description</th><th>HSN/SAC</th><th class="amount">Qty</th><th class="amount">Rate</th><th class="amount">GST %</th><th class="amount">Taxable</th><th class="amount">Total</th></tr>
          </thead>
          <tbody>
            ${lines.map((l) => `
              <tr>
                <td>${escapeHtml(l.description || "")}</td>
                <td>${escapeHtml(l.hsn_sac || "")}</td>
                <td class="amount">${escapeHtml(l.quantity || "")}</td>
                <td class="amount">${escapeHtml(formatCurrency(l.rate || 0))}</td>
                <td class="amount">${escapeHtml(String(l.gst_rate || 0))}%</td>
                <td class="amount">${escapeHtml(formatCurrency(l.taxable_amount || 0))}</td>
                <td class="amount">${escapeHtml(formatCurrency(l.line_total || 0))}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
      <div class="invoice-totals">
        <div><span>Taxable</span><strong>${formatCurrency(n.taxable_total || 0)}</strong></div>
        ${taxRow}
        <div class="invoice-grand"><span>Debit note total</span><strong>${formatCurrency(n.note_total || 0)}</strong></div>
      </div>
      ${n.notes ? `<p class="muted">${escapeHtml(n.notes)}</p>` : ""}
      ${String(n.status).toLowerCase() === "cancelled" ? `<p class="muted">Reversed${n.cancel_reason ? `: ${escapeHtml(n.cancel_reason)}` : ""}. Reversing journal entry #${escapeHtml(n.reversal_journal_entry_id || "")} posted.</p>` : ""}
    </div>
  `;
}



export function renderBusinessDebitNoteWorkspace() {
  if (debitUi.view === "create") {
    return renderDebitNoteCreateForm();
  }
  if (debitUi.view === "detail") {
    return renderDebitNoteDetail();
  }
  return `
    <div class="verification-panel erp-workspace-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Debit Notes</h4>
          <p>Purchase-side GST adjustments against vendor bills (returns, rejected goods, price revisions).</p>
        </div>
        <button class="secondary" type="button" data-business-action="open-create-debit-note" aria-keyshortcuts="Control+Alt+D">+ New Debit Note</button>
      </div>
      ${renderDnListTable()}
    </div>
  `;
}

