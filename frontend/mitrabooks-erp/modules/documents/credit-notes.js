// ====================================================================
// SECTION: CREDIT NOTES WORKSPACE
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initCreditNotes(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";
import {
  computeInvoiceLine,
  invoiceStatusPill,
  customerPartyOptions,
  incomeAccountOptions,
  salesUi,
  loadBusinessInvoices,
} from "./sales-invoices.js";

export const creditUi = {
  view: "list", // list | create | detail
  notes: [],
  detail: null,
  lineSeq: 0,
  formLines: [],
  reverseOpen: false,
  reasons: [
    ["sales_return", "Sales return"],
    ["discount", "Post-sale discount"],
    ["price_revision", "Price revision (downward)"],
    ["deficiency", "Deficiency in service/goods"],
    ["other", "Other"],
  ],
  header: {
    customer_party_id: "",
    note_date: "",
    original_invoice_id: "",
    original_invoice_number: "",
    reason: "sales_return",
    is_inter_state: false,
    income_account_code: "41001",
    place_of_supply: "",
    notes: "",
    cost_centre_id: "",
    project_id: "",
  },
};

/** @type {Record<string, Function> | null} */
let deps = null;

export function initCreditNotes(injected) {
  deps = injected;
  creditUi.header.note_date = injected.todayIsoDate();
}

function requireDeps() {
  if (!deps) {
    throw new Error("initCreditNotes() must be called before using credit note helpers");
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

export function rerenderCreditNoteIfActive() {
  if (getCurrentExperience() === "mitrabooks" && getActiveBusinessWorkspace() === "credit-notes") {
    getDashboardPreview().innerHTML = renderBusinessWorkspace();
    if (creditUi.view === "create") {
      focusBusinessEntryField("[data-cn-form] select[name='customer_party_id']");
    }
  }
}

export async function loadCreditNotes() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/credit-notes?limit=100", { method: "GET" });
  creditUi.notes = result.ok && Array.isArray(result.payload?.items) ? result.payload.items : [];
  if (!result.ok) setLoginStatus("danger", "Unable to load credit notes", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  rerenderCreditNoteIfActive();
  renderJson(getApiOutput(), { credit_notes: { ok: result.ok, count: creditUi.notes.length } });
}

export function resolveCreditNoteSourceInvoice(invoiceId) {
  return (Array.isArray(salesUi.invoices) ? salesUi.invoices : [])
    .find((invoice) => String(invoice.invoice_id || "") === String(invoiceId || ""));
}

export function creditNoteSourceInvoiceOptions(selectedId) {
  const invoices = Array.isArray(salesUi.invoices) ? salesUi.invoices : [];
  if (!invoices.length) {
    return `<option value="">Load or create a source invoice first</option>`;
  }
  return [
    `<option value="">Select source invoice</option>`,
    ...invoices.map((invoice) => {
      const id = String(invoice.invoice_id || "");
      const number = String(invoice.invoice_number || id || "");
      const customer = String(invoice.customer_name || invoice.customer_party_id || "");
      const total = formatCurrency(invoice.invoice_total || invoice.grand_total || 0);
      const selected = id && id === String(selectedId || "") ? "selected" : "";
      return `<option value="${escapeHtml(id)}" ${selected}>${escapeHtml(number)} - ${escapeHtml(customer)} - ${escapeHtml(total)}</option>`;
    }),
  ].join("");
}

export function syncCnFormFromDom() {
  const form = document.querySelector("[data-cn-form]");
  if (!form) return;
  const val = (sel) => form.querySelector(sel)?.value ?? "";
  creditUi.header.customer_party_id = val("select[name='customer_party_id']");
  creditUi.header.note_date = val("input[name='note_date']") || todayIsoDate();
  creditUi.header.original_invoice_id = val("select[name='original_invoice_id']");
  const selectedInvoice = resolveCreditNoteSourceInvoice(creditUi.header.original_invoice_id);
  creditUi.header.original_invoice_number = selectedInvoice?.invoice_number || "";
  creditUi.header.reason = val("select[name='reason']") || "sales_return";
  creditUi.header.is_inter_state = !!form.querySelector("input[name='is_inter_state']")?.checked;
  creditUi.header.income_account_code = val("select[name='income_account_code']") || "41001";
  creditUi.header.place_of_supply = val("input[name='place_of_supply']");
  creditUi.header.notes = val("textarea[name='notes']");
  creditUi.header.cost_centre_id = val("select[name='cost_centre_id']");
  creditUi.header.project_id = val("select[name='project_id']");
  creditUi.formLines = Array.from(form.querySelectorAll("[data-cn-line]")).map((row) => ({
    id: row.getAttribute("data-cn-line"),
    description: row.querySelector("input[name='description']")?.value || "",
    hsn_sac: row.querySelector("input[name='hsn_sac']")?.value || "",
    uqc: row.querySelector("input[name='uqc']")?.value || "",
    quantity: row.querySelector("input[name='quantity']")?.value || "",
    rate: row.querySelector("input[name='rate']")?.value || "",
    gst_rate: row.querySelector("input[name='gst_rate']")?.value || "",
    cost_centre_id: row.querySelector("select[name='line_cost_centre_id']")?.value || "",
    project_id: row.querySelector("select[name='line_project_id']")?.value || "",
  }));
}

export function updateCnTotalsDisplay() {
  const form = document.querySelector("[data-cn-form]");
  if (!form) return;
  const inter = !!form.querySelector("input[name='is_inter_state']")?.checked;
  let taxableTotal = 0, cgstTotal = 0, sgstTotal = 0, igstTotal = 0;
  form.querySelectorAll("[data-cn-line]").forEach((row) => {
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

export function setCreditNoteView(view) {
  creditUi.view = view;
  creditUi.reverseOpen = false;
  rerenderCreditNoteIfActive();
  if (view === "create") {
    updateCnTotalsDisplay();
    focusBusinessEntryField("[data-cn-form] select[name='customer_party_id']");
  }
}

export function openCreditNoteCreate() {
  creditUi.formLines = [{ id: `cn-${++creditUi.lineSeq}`, description: "", hsn_sac: "", uqc: "", quantity: "1", rate: "", gst_rate: "18", cost_centre_id: "", project_id: "" }];
  creditUi.header.customer_party_id = "";
  creditUi.header.note_date = todayIsoDate();
  creditUi.header.original_invoice_id = "";
  creditUi.header.original_invoice_number = "";
  creditUi.header.reason = "sales_return";
  creditUi.header.is_inter_state = false;
  creditUi.header.income_account_code = "41001";
  creditUi.header.place_of_supply = "";
  creditUi.header.notes = "";
  creditUi.header.cost_centre_id = "";
  creditUi.header.project_id = "";
  if (!Array.isArray(getLastBusinessParties()) || getLastBusinessParties().length === 0) loadBusinessParties();
  if (!hasLoadedBusinessAccounts()) loadBusinessAccounts();
  if (!Array.isArray(salesUi.invoices) || salesUi.invoices.length === 0) loadBusinessInvoices();
  if (!getLastDimensions()) loadDimensions().then(() => rerenderCreditNoteIfActive());
  setCreditNoteView("create");
}

export function addCnLine() {
  syncCnFormFromDom();
  creditUi.formLines.push({ id: `cn-${++creditUi.lineSeq}`, description: "", hsn_sac: "", uqc: "", quantity: "1", rate: "", gst_rate: "18", cost_centre_id: "", project_id: "" });
  rerenderCreditNoteIfActive();
  updateCnTotalsDisplay();
}

export function removeCnLine(lineId) {
  syncCnFormFromDom();
  creditUi.formLines = creditUi.formLines.filter((l) => l.id !== lineId);
  if (creditUi.formLines.length === 0) {
    creditUi.formLines.push({ id: `cn-${++creditUi.lineSeq}`, description: "", hsn_sac: "", uqc: "", quantity: "1", rate: "", gst_rate: "18", cost_centre_id: "", project_id: "" });
  }
  rerenderCreditNoteIfActive();
  updateCnTotalsDisplay();
}

export async function submitCreditNote() {
  syncCnFormFromDom();
  if (!creditUi.header.customer_party_id) {
    setLoginStatus("warn", "Customer required", "Select the customer for this credit note.");
    return;
  }
  const sourceInvoice = resolveCreditNoteSourceInvoice(creditUi.header.original_invoice_id);
  if (!sourceInvoice) {
    setLoginStatus("warn", "Source invoice required", "Select the source invoice this credit note adjusts.");
    return;
  }
  const lineItems = creditUi.formLines
    .filter((l) => String(l.description).trim() && Number(l.quantity) > 0)
    .map((l) => ({
      description: String(l.description).trim(),
      hsn_sac: String(l.hsn_sac || "").trim() || null,
      uqc: String(l.uqc || "").trim().toUpperCase() || null,
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
    customer_party_id: creditUi.header.customer_party_id,
    note_date: creditUi.header.note_date || todayIsoDate(),
    original_invoice_id: creditUi.header.original_invoice_id || null,
    original_invoice_number: String(creditUi.header.original_invoice_number || "").trim() || null,
    reason: creditUi.header.reason || "sales_return",
    is_inter_state: !!creditUi.header.is_inter_state,
    income_account_code: creditUi.header.income_account_code || "41001",
    place_of_supply: String(creditUi.header.place_of_supply || "").trim() || null,
    notes: String(creditUi.header.notes || "").trim() || null,
    cost_centre_id: creditUi.header.cost_centre_id || null,
    project_id: creditUi.header.project_id || null,
    line_items: lineItems,
  };
  const result = await apiRequest("mitrabooks", "/api/v1/business/credit-notes", {
    method: "POST",
    headers: { "X-Idempotency-Key": `credit-note-${Date.now()}` },
    body: JSON.stringify(body),
  });
  if (result.ok) {
    setLoginStatus("ok", "Credit note posted", `${result.payload?.credit_note_number || "Credit note"} posted to the ledger.`);
    await loadCreditNotes();
    setCreditNoteView("list");
  } else {
    setLoginStatus("danger", "Credit note failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { create_credit_note: { ok: result.ok, status: result.status, detail: result.payload?.detail || null } });
}

export async function openCreditNoteDetail(noteId) {
  const result = await apiRequest("mitrabooks", `/api/v1/business/credit-notes/${encodeURIComponent(noteId)}`, { method: "GET" });
  if (result.ok) {
    creditUi.detail = result.payload;
    setCreditNoteView("detail");
  } else {
    setLoginStatus("danger", "Unable to load credit note", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { credit_note_detail: { ok: result.ok, status: result.status } });
}

export async function cancelCreditNote(noteId, reversalDate) {
  const body = { reason: "Reversal" };
  if (reversalDate) body.cancel_date = reversalDate;
  const result = await apiRequest("mitrabooks", `/api/v1/business/credit-notes/${encodeURIComponent(noteId)}/cancel`, {
    method: "POST",
    headers: { "X-Idempotency-Key": `credit-note-cancel-${noteId}-${reversalDate || "today"}` },
    body: JSON.stringify(body),
  });
  if (result.ok) {
    creditUi.reverseOpen = false;
    setLoginStatus("ok", "Credit note reversed", "A reversing journal entry was posted.");
    await loadCreditNotes();
    if (creditUi.detail && creditUi.detail.credit_note_id === noteId) {
      creditUi.detail = result.payload;
    }
    rerenderCreditNoteIfActive();
  } else {
    setLoginStatus("danger", "Reverse failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { cancel_credit_note: { ok: result.ok, status: result.status } });
}

export function cnReasonLabel(value) {
  const found = creditUi.reasons.find((r) => r[0] === value);
  return found ? found[1] : (value || "");
}

export function renderCnListTable() {
  const rows = creditUi.notes;
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Credit Note #</th>
            <th>Date</th>
            <th>Customer</th>
            <th>Against</th>
            <th class="amount">Taxable</th>
            <th class="amount">GST</th>
            <th class="amount">Total</th>
            <th>Status</th>
            <th>Open</th>
          </tr>
        </thead>
        <tbody>
          ${rows.length ? rows.map((n) => `
            <tr>
              <td>${escapeHtml(n.credit_note_number || "")}</td>
              <td>${escapeHtml(n.note_date || "")}</td>
              <td>${escapeHtml(n.customer_name || n.customer_party_id || "")}</td>
              <td>${escapeHtml(n.original_invoice_number || "—")}</td>
              <td class="amount">${escapeHtml(formatCurrency(n.taxable_total || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(n.gst_total || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(n.note_total || 0))}</td>
              <td>${invoiceStatusPill(n.status)}</td>
              <td><button class="secondary" type="button" data-business-action="view-credit-note" data-cn-id="${escapeHtml(n.credit_note_id)}">View</button></td>
            </tr>
          `).join("") : `<tr><td colspan="9" class="muted">No credit notes yet.</td></tr>`}
        </tbody>
      </table>
    </div>
  `;
}

export function renderCreditNoteCreateForm() {
  const customers = customerPartyOptions();
  const incomeAccounts = incomeAccountOptions();
  const lineCostCentreOptions = (selected) => dimensionOptions("cost_centre", selected || "");
  const lineProjectOptions = (selected) => dimensionOptions("project", selected || "");
  const lineRows = creditUi.formLines.map((l) => `
    <tr data-cn-line="${escapeHtml(l.id)}">
      <td><input type="text" name="description" value="${escapeHtml(l.description)}" placeholder="Item / service"></td>
      <td><input type="text" name="hsn_sac" value="${escapeHtml(l.hsn_sac)}" placeholder="HSN/SAC"></td>
      <td><input type="text" name="uqc" value="${escapeHtml(l.uqc || "")}" placeholder="UQC" style="width:70px;"></td>
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
      <td><button class="secondary" type="button" data-business-action="remove-cn-line" data-line-id="${escapeHtml(l.id)}">✕</button></td>
    </tr>
  `).join("");

  return `
    <div class="verification-panel erp-workspace-panel" data-cn-form>
      <div class="preview-heading compact">
        <div>
          <h4>New Credit Note</h4>
          <p>Reduce a customer's invoice (return, discount, or price revision). Reduces output GST and receivables.</p>
        </div>
        <button class="secondary" type="button" data-business-action="cn-back">← Back to list</button>
      </div>
      <div class="invoice-form-grid">
        <label>Customer
          <select name="customer_party_id">
            <option value="">Select customer</option>
            ${customers.map((c) => `<option value="${escapeHtml(c.party_id)}" ${c.party_id === creditUi.header.customer_party_id ? "selected" : ""}>${escapeHtml(c.party_name)}${c.gstin ? ` (${escapeHtml(c.gstin)})` : ""}</option>`).join("")}
          </select>
        </label>
        <label>Note date
          <input type="date" name="note_date" value="${escapeHtml(creditUi.header.note_date)}">
        </label>
        <label>Against invoice #
          <select name="original_invoice_id" required data-source-document="sales_invoice">
            ${creditNoteSourceInvoiceOptions(creditUi.header.original_invoice_id)}
          </select>
        </label>
        <label>Reason
          <select name="reason">
            ${creditUi.reasons.map(([v, lbl]) => `<option value="${escapeHtml(v)}" ${v === creditUi.header.reason ? "selected" : ""}>${escapeHtml(lbl)}</option>`).join("")}
          </select>
        </label>
        <label>Income account
          <select name="income_account_code">
            ${incomeAccounts.length ? incomeAccounts.map((a) => `<option value="${escapeHtml(a.code)}" ${a.code === creditUi.header.income_account_code ? "selected" : ""}>${escapeHtml(`${a.code} - ${a.name}`)}</option>`).join("") : `<option value="41001" selected>41001 - Sales</option>`}
          </select>
        </label>
        <label>Place of supply
          <input type="text" name="place_of_supply" value="${escapeHtml(creditUi.header.place_of_supply)}" placeholder="State / code">
        </label>
        ${dimensionOptions("cost_centre", creditUi.header.cost_centre_id) ? `<label>Cost centre
          <select name="cost_centre_id">${dimensionOptions("cost_centre", creditUi.header.cost_centre_id)}</select>
        </label>` : ""}
        ${dimensionOptions("project", creditUi.header.project_id) ? `<label>Project
          <select name="project_id">${dimensionOptions("project", creditUi.header.project_id)}</select>
        </label>` : ""}
        <label class="invoice-inter-toggle">
          <input type="checkbox" name="is_inter_state" ${creditUi.header.is_inter_state ? "checked" : ""}>
          Inter-state supply (IGST)
        </label>
      </div>

      <div class="table-preview compact-table invoice-lines">
        <table>
          <thead>
            <tr>
              <th>Description</th><th>HSN/SAC</th><th>UQC</th><th>Qty</th><th>Rate</th><th>GST %</th><th>Line tags</th>
              <th class="amount">Taxable</th><th class="amount">GST</th><th class="amount">Total</th><th></th>
            </tr>
          </thead>
          <tbody>${lineRows}</tbody>
        </table>
      </div>
      <button class="secondary" type="button" data-business-action="add-cn-line" aria-keyshortcuts="Alt+L">+ Add line</button>

      <div class="invoice-totals">
        <div><span>Taxable</span><strong data-total-taxable>${formatCurrency(0)}</strong></div>
        <div data-row-cgst ${creditUi.header.is_inter_state ? "hidden" : ""}><span>CGST</span><strong data-total-cgst>${formatCurrency(0)}</strong></div>
        <div data-row-sgst ${creditUi.header.is_inter_state ? "hidden" : ""}><span>SGST</span><strong data-total-sgst>${formatCurrency(0)}</strong></div>
        <div data-row-igst ${creditUi.header.is_inter_state ? "" : "hidden"}><span>IGST</span><strong data-total-igst>${formatCurrency(0)}</strong></div>
        <div class="invoice-grand"><span>Credit note total</span><strong data-total-note>${formatCurrency(0)}</strong></div>
      </div>

      <label class="invoice-notes">Notes
        <textarea name="notes" rows="2" placeholder="Optional notes">${escapeHtml(creditUi.header.notes)}</textarea>
      </label>

      <div class="invoice-form-actions">
        <button class="primary" type="button" data-business-action="save-credit-note" aria-keyshortcuts="Control+Enter">Post Credit Note</button>
        <button class="secondary" type="button" data-business-action="cn-back">Cancel</button>
      </div>
    </div>
  `;
}

export function renderCreditNoteDetail() {
  const n = creditUi.detail;
  if (!n) {
    return `<div class="verification-panel erp-workspace-panel"><p class="muted">Credit note not found.</p></div>`;
  }
  const lines = Array.isArray(n.line_items) ? n.line_items : [];
  const taxRow = n.is_inter_state
    ? `<div><span>IGST</span><strong>${formatCurrency(n.igst_total || 0)}</strong></div>`
    : `<div><span>CGST</span><strong>${formatCurrency(n.cgst_total || 0)}</strong></div><div><span>SGST</span><strong>${formatCurrency(n.sgst_total || 0)}</strong></div>`;
  return `
    <div class="verification-panel erp-workspace-panel" data-credit-note-printable>
      <div class="preview-heading compact">
        <div>
          <h4>Credit Note ${escapeHtml(n.credit_note_number || "")} ${invoiceStatusPill(n.status)}</h4>
          <p>${escapeHtml(n.customer_name || n.customer_party_id || "")}${n.customer_gstin ? ` · ${escapeHtml(n.customer_gstin)}` : ""} · ${escapeHtml(n.note_date || "")}${n.original_invoice_number ? ` · against ${escapeHtml(n.original_invoice_number)}` : ""}</p>
        </div>
        <div class="invoice-detail-actions">
          <button class="secondary" type="button" data-business-action="cn-back">← Back to list</button>
          <button class="secondary" type="button" data-business-action="print-credit-note">Print</button>
          <button class="secondary" type="button" data-business-action="export-credit-note-json">Export JSON</button>
          ${String(n.status).toLowerCase() === "posted" && !creditUi.reverseOpen ? `<button class="secondary" type="button" data-business-action="begin-reverse-cn">Reverse</button>` : ""}
        </div>
      </div>
      ${String(n.status).toLowerCase() === "posted" && creditUi.reverseOpen ? reversalPanel("cn", n.credit_note_id, n.note_date) : ""}
      <p class="muted">${escapeHtml(cnReasonLabel(n.reason))}${n.is_inter_state ? " · Inter-state (IGST)" : " · Intra-state (CGST + SGST)"}</p>
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
        <div class="invoice-grand"><span>Credit note total</span><strong>${formatCurrency(n.note_total || 0)}</strong></div>
      </div>
      ${n.notes ? `<p class="muted">${escapeHtml(n.notes)}</p>` : ""}
      ${String(n.status).toLowerCase() === "cancelled" ? `<p class="muted">Reversed${n.cancel_reason ? `: ${escapeHtml(n.cancel_reason)}` : ""}. Reversing journal entry #${escapeHtml(n.reversal_journal_entry_id || "")} posted.</p>` : ""}
    </div>
  `;
}



export function renderBusinessCreditNoteWorkspace() {
  if (creditUi.view === "create") {
    return renderCreditNoteCreateForm();
  }
  if (creditUi.view === "detail") {
    return renderCreditNoteDetail();
  }
  return `
    <div class="verification-panel erp-workspace-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Credit Notes</h4>
          <p>Sales-side GST adjustments against invoices (returns, discounts, price revisions).</p>
        </div>
        <button class="secondary" type="button" data-business-action="open-create-credit-note" aria-keyshortcuts="Control+Alt+C">+ New Credit Note</button>
      </div>
      ${renderCnListTable()}
    </div>
  `;
}

