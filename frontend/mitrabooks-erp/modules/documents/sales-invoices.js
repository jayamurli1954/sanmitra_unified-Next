// ====================================================================
// SECTION: SALES INVOICES WORKSPACE
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initSalesInvoices(...).
// ====================================================================

import { apiRequest, downloadApiFile, renderJson } from "../../../shared/api-client.js";

export const salesUi = {
  view: "list", // list | create | detail | settings
  invoices: [],
  detail: null,
  settings: null,
  lineSeq: 0,
  formLines: [],
  header: {
    customer_party_id: "",
    invoice_date: "",
    due_date: "",
    is_inter_state: false,
    income_account_code: "41001",
    place_of_supply: "",
    reference: "",
    notes: "",
    tcs_section: "",
    cost_centre_id: "",
    project_id: "",
  },
  reverseOpen: false,
  attachments: [],
  attachmentsLoading: false,
};

/** @type {Record<string, Function> | null} */
let deps = null;

export function initSalesInvoices(injected) {
  deps = injected;
  salesUi.header.invoice_date = injected.todayIsoDate();
}

function requireDeps() {
  if (!deps) {
    throw new Error("initSalesInvoices() must be called before using sales invoice helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function todayIsoDate() { return requireDeps().todayIsoDate(); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function round2(value) { return requireDeps().round2(value); }
function tdsSectionOptions(kind, selected) { return requireDeps().tdsSectionOptions(kind, selected); }
function tdsSectionRate(kind, section) { return requireDeps().tdsSectionRate(kind, section); }
function loadTdsSections() { return requireDeps().loadTdsSections(); }
function hasTdsSectionsCache() { return requireDeps().hasTdsSectionsCache(); }
function isBusinessAdmin() { return requireDeps().isBusinessAdmin(); }
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
function businessAccountsForSelection() { return requireDeps().businessAccountsForSelection(); }
function dimensionOptions(kind, selected) { return requireDeps().dimensionOptions(kind, selected); }
function getLastDimensions() { return requireDeps().getLastDimensions(); }
function loadDimensions() { return requireDeps().loadDimensions(); }
function getLastInventoryItems() { return requireDeps().getLastInventoryItems(); }
function loadInventoryItems() { return requireDeps().loadInventoryItems(); }
function inventoryItemOptions(selected) { return requireDeps().inventoryItemOptions(selected); }
function renderEinvoiceSection(inv) { return requireDeps().renderEinvoiceSection(inv); }
function loadEinvoiceView(invoiceId) { return requireDeps().loadEinvoiceView(invoiceId); }
function clearEinvoiceView() { requireDeps().clearEinvoiceView(); }
function renderBusinessAttachmentPanel(opts) { return requireDeps().renderBusinessAttachmentPanel(opts); }
function listBusinessAttachments(ownerType, ownerId) { return requireDeps().listBusinessAttachments(ownerType, ownerId); }
function getApiOutput() { return requireDeps().getApiOutput(); }

const INVOICE_STANDARD_FIELD_LABELS = {
  due_date: "Due date",
  place_of_supply: "Place of supply",
  reference: "Reference / PO",
  notes: "Notes",
  hsn_sac: "HSN/SAC (line column)",
};
export function invoiceFieldRule(key) {
  const fc = (salesUi.settings && salesUi.settings.field_config) || {};
  return fc[key] || { visible: true, required: false };
}
export function invoiceFieldVisible(key) {
  return invoiceFieldRule(key).visible !== false;
}
export function invoiceFieldRequired(key) {
  return !!invoiceFieldRule(key).required;
}
export async function loadInvoiceSettings() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/invoice-settings", { method: "GET" });
  if (result.ok) {
    salesUi.settings = result.payload;
  } else if (!salesUi.settings) {
    // Fall back to permissive defaults so the form still renders.
    salesUi.settings = {
      field_config: { due_date: { visible: true, required: false }, place_of_supply: { visible: true, required: false }, reference: { visible: true, required: false }, notes: { visible: true, required: false }, hsn_sac: { visible: true, required: false } },
      numbering: { prefix: "INV", number_format: "{PREFIX}-{FY}-{SEQ}", seq_padding: 6, start_number: 1, reset_yearly: true },
      custom_fields: [],
      branding: {},
    };
  }
  rerenderSalesIfActive();
}
export function rerenderSalesIfActive() {
  if (getCurrentExperience() === "mitrabooks" && getActiveBusinessWorkspace() === "sales") {
    getDashboardPreview().innerHTML = renderBusinessWorkspace();
    if (salesUi.view === "create") {
      focusBusinessEntryField("[data-invoice-form] select[name='customer_party_id']");
    }
  }
}
export async function loadBusinessInvoices() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/invoices?limit=100", { method: "GET" });
  if (result.ok) {
    salesUi.invoices = Array.isArray(result.payload?.items) ? result.payload.items : [];
  } else {
    salesUi.invoices = [];
    setLoginStatus("danger", "Unable to load invoices", statusDetailText(result.payload?.detail) || `Invoice list request failed with HTTP ${result.status}.`);
  }
  rerenderSalesIfActive();
  renderJson(getApiOutput(), { invoices: { ok: result.ok, status: result.status, count: salesUi.invoices.length } });
}
export function customerPartyOptions() {
  return (Array.isArray(getLastBusinessParties()) ? getLastBusinessParties() : [])
    .filter((p) => ["customer", "both"].includes(String(p.party_type || "").toLowerCase()));
}
export function incomeAccountOptions() {
  return businessAccountsForSelection().filter((acc) => String(acc.code || "").startsWith("4"));
}
export function computeInvoiceLine(qty, rate, gstRate, inter) {
  const taxable = round2(Number(qty || 0) * Number(rate || 0));
  const gst = round2(taxable * Number(gstRate || 0) / 100);
  let cgst = 0, sgst = 0, igst = 0;
  if (inter) {
    igst = gst;
  } else {
    cgst = round2(gst / 2);
    sgst = round2(gst - cgst);
  }
  return { taxable, cgst, sgst, igst, total: round2(taxable + cgst + sgst + igst) };
}
export function syncSalesFormFromDom() {
  const form = document.querySelector("[data-invoice-form]");
  if (!form) return;
  const val = (sel) => form.querySelector(sel)?.value ?? "";
  salesUi.header.customer_party_id = val("select[name='customer_party_id']");
  salesUi.header.invoice_date = val("input[name='invoice_date']") || todayIsoDate();
  salesUi.header.due_date = val("input[name='due_date']");
  salesUi.header.is_inter_state = !!form.querySelector("input[name='is_inter_state']")?.checked;
  salesUi.header.income_account_code = val("select[name='income_account_code']") || "41001";
  salesUi.header.place_of_supply = val("input[name='place_of_supply']");
  salesUi.header.reference = val("input[name='reference']");
  salesUi.header.notes = val("textarea[name='notes']");
  salesUi.header.tcs_section = val("select[name='tcs_section']");
  salesUi.header.cost_centre_id = val("select[name='cost_centre_id']");
  salesUi.header.project_id = val("select[name='project_id']");
  salesUi.formLines = Array.from(form.querySelectorAll("[data-invoice-line]")).map((row) => ({
    id: row.getAttribute("data-invoice-line"),
    description: row.querySelector("input[name='description']")?.value || "",
    item_id: row.querySelector("select[name='item_id']")?.value || "",
    hsn_sac: row.querySelector("input[name='hsn_sac']")?.value || "",
    uqc: row.querySelector("input[name='uqc']")?.value || "",
    supply_type: row.querySelector("select[name='supply_type']")?.value || "taxable",
    quantity: row.querySelector("input[name='quantity']")?.value || "",
    rate: row.querySelector("input[name='rate']")?.value || "",
    gst_rate: row.querySelector("input[name='gst_rate']")?.value || "",
    cost_centre_id: row.querySelector("select[name='line_cost_centre_id']")?.value || "",
    project_id: row.querySelector("select[name='line_project_id']")?.value || "",
  }));
}
export function updateInvoiceTotalsDisplay() {
  const form = document.querySelector("[data-invoice-form]");
  if (!form) return;
  const inter = !!form.querySelector("input[name='is_inter_state']")?.checked;
  let taxableTotal = 0, cgstTotal = 0, sgstTotal = 0, igstTotal = 0;
  form.querySelectorAll("[data-invoice-line]").forEach((row) => {
    const qty = row.querySelector("input[name='quantity']")?.value;
    const rate = row.querySelector("input[name='rate']")?.value;
    // Zero-rated (export/SEZ under LUT) lines carry no tax regardless of rate.
    const supplyType = row.querySelector("select[name='supply_type']")?.value || "taxable";
    const gstRate = supplyType === "zero_rated" ? 0 : row.querySelector("input[name='gst_rate']")?.value;
    const c = computeInvoiceLine(qty, rate, gstRate, inter);
    row.querySelector("[data-line-taxable]").textContent = formatCurrency(c.taxable);
    row.querySelector("[data-line-gst]").textContent = formatCurrency(c.cgst + c.sgst + c.igst);
    row.querySelector("[data-line-total]").textContent = formatCurrency(c.total);
    taxableTotal += c.taxable; cgstTotal += c.cgst; sgstTotal += c.sgst; igstTotal += c.igst;
  });
  const gstTotal = round2(cgstTotal + sgstTotal + igstTotal);
  const invoiceTotal = round2(taxableTotal + gstTotal);
  // TCS (206C) is computed on the GST-inclusive invoice total.
  const tcsSection = form.querySelector("select[name='tcs_section']")?.value || "";
  const tcsAmount = tcsSection ? round2(invoiceTotal * tdsSectionRate("tcs", tcsSection) / 100) : 0;
  const set = (sel, v) => { const el = form.querySelector(sel); if (el) el.textContent = formatCurrency(v); };
  set("[data-total-taxable]", taxableTotal);
  set("[data-total-cgst]", cgstTotal);
  set("[data-total-sgst]", sgstTotal);
  set("[data-total-igst]", igstTotal);
  set("[data-total-invoice]", invoiceTotal);
  set("[data-total-tcs]", tcsAmount);
  set("[data-total-grand]", round2(invoiceTotal + tcsAmount));
  const tcsRow = form.querySelector("[data-row-tcs]");
  const grandRow = form.querySelector("[data-row-grand]");
  if (tcsRow) tcsRow.hidden = !tcsSection;
  if (grandRow) grandRow.hidden = !tcsSection;
  // Toggle CGST/SGST vs IGST total rows based on supply type
  const cgstRow = form.querySelector("[data-row-cgst]");
  const sgstRow = form.querySelector("[data-row-sgst]");
  const igstRow = form.querySelector("[data-row-igst]");
  if (cgstRow && sgstRow && igstRow) {
    cgstRow.hidden = inter;
    sgstRow.hidden = inter;
    igstRow.hidden = !inter;
  }
}
export function setBusinessSalesView(view) {
  salesUi.view = view;
  salesUi.reverseOpen = false;
  rerenderSalesIfActive();
  if (view === "create") {
    updateInvoiceTotalsDisplay();
    focusBusinessEntryField("[data-invoice-form] select[name='customer_party_id']");
  }
}
export function openInvoiceCreate() {
  salesUi.formLines = [{ id: `il-${++salesUi.lineSeq}`, description: "", hsn_sac: "", uqc: "", supply_type: "taxable", quantity: "1", rate: "", gst_rate: "18", cost_centre_id: "", project_id: "" }];
  salesUi.header.customer_party_id = "";
  salesUi.header.invoice_date = todayIsoDate();
  salesUi.header.due_date = "";
  salesUi.header.is_inter_state = false;
  salesUi.header.income_account_code = "41001";
  salesUi.header.place_of_supply = "";
  salesUi.header.reference = "";
  salesUi.header.notes = "";
  salesUi.header.tcs_section = "";
  salesUi.header.cost_centre_id = "";
  salesUi.header.project_id = "";
  // Make sure customers, accounts, and settings are available for the form.
  if (!Array.isArray(getLastBusinessParties()) || getLastBusinessParties().length === 0) loadBusinessParties();
  if (!hasLoadedBusinessAccounts()) loadBusinessAccounts();
  if (!salesUi.settings) loadInvoiceSettings();
  if (!hasTdsSectionsCache()) loadTdsSections().then(() => rerenderSalesIfActive());
  if (!getLastDimensions()) loadDimensions().then(() => rerenderSalesIfActive());
  if (!getLastInventoryItems()) loadInventoryItems().then(() => rerenderSalesIfActive());
  setBusinessSalesView("create");
}
export function addInvoiceLine() {
  syncSalesFormFromDom();
  salesUi.formLines.push({ id: `il-${++salesUi.lineSeq}`, description: "", hsn_sac: "", uqc: "", supply_type: "taxable", quantity: "1", rate: "", gst_rate: "18", cost_centre_id: "", project_id: "" });
  rerenderSalesIfActive();
  updateInvoiceTotalsDisplay();
}
export function removeInvoiceLine(lineId) {
  syncSalesFormFromDom();
  salesUi.formLines = salesUi.formLines.filter((l) => l.id !== lineId);
  if (salesUi.formLines.length === 0) {
    salesUi.formLines.push({ id: `il-${++salesUi.lineSeq}`, description: "", hsn_sac: "", uqc: "", supply_type: "taxable", quantity: "1", rate: "", gst_rate: "18", cost_centre_id: "", project_id: "" });
  }
  rerenderSalesIfActive();
  updateInvoiceTotalsDisplay();
}
export async function submitInvoice() {
  syncSalesFormFromDom();
  if (!salesUi.header.customer_party_id) {
    setLoginStatus("warn", "Customer required", "Select a customer for this invoice.");
    return;
  }
  // Client-side enforcement of admin-configured required fields (backend re-validates).
  for (const key of ["due_date", "place_of_supply", "reference", "notes"]) {
    if (invoiceFieldRequired(key) && !String(salesUi.header[key] || "").trim()) {
      setLoginStatus("warn", `${INVOICE_STANDARD_FIELD_LABELS[key]} required`, "This field is required by your invoice settings.");
      return;
    }
  }
  const lineItems = salesUi.formLines
    .filter((l) => String(l.description).trim() && Number(l.quantity) > 0)
    .map((l) => ({
      description: String(l.description).trim(),
      item_id: String(l.item_id || "").trim() || null,
      hsn_sac: String(l.hsn_sac || "").trim() || null,
      uqc: String(l.uqc || "").trim().toUpperCase() || null,
      supply_type: l.supply_type || "taxable",
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
    customer_party_id: salesUi.header.customer_party_id,
    invoice_date: salesUi.header.invoice_date || todayIsoDate(),
    due_date: salesUi.header.due_date || null,
    is_inter_state: !!salesUi.header.is_inter_state,
    income_account_code: salesUi.header.income_account_code || "41001",
    place_of_supply: String(salesUi.header.place_of_supply || "").trim() || null,
    reference: String(salesUi.header.reference || "").trim() || null,
    notes: String(salesUi.header.notes || "").trim() || null,
    line_items: lineItems,
    tcs_section: salesUi.header.tcs_section || null,
    cost_centre_id: salesUi.header.cost_centre_id || null,
    project_id: salesUi.header.project_id || null,
  };
  const result = await apiRequest("mitrabooks", "/api/v1/business/invoices", {
    method: "POST",
    headers: { "X-Idempotency-Key": `sales-invoice-${Date.now()}` },
    body: JSON.stringify(body),
  });
  if (result.ok) {
    setLoginStatus("ok", "Invoice posted", `${result.payload?.invoice_number || "Invoice"} posted to the ledger.`);
    await loadBusinessInvoices();
    setBusinessSalesView("list");
  } else {
    setLoginStatus("danger", "Invoice posting failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { create_invoice: { ok: result.ok, status: result.status, detail: result.payload?.detail || null } });
}
export async function downloadInvoicePdf(invoiceId, invoiceNumber) {
  if (!invoiceId) {
    return;
  }
  const result = await downloadApiFile(
    "mitrabooks",
    `/api/v1/business/invoices/${encodeURIComponent(invoiceId)}/pdf`,
    `${invoiceNumber || invoiceId}.pdf`,
  );
  if (!result.ok) {
    setLoginStatus("danger", "PDF download failed", statusDetailText(result.payload?.detail) || `Invoice PDF failed with HTTP ${result.status}.`);
  }
}
export async function openInvoiceDetail(invoiceId) {
  salesUi.attachmentsLoading = true;
  salesUi.attachments = [];
  const result = await apiRequest("mitrabooks", `/api/v1/business/invoices/${encodeURIComponent(invoiceId)}`, { method: "GET" });
  if (result.ok) {
    salesUi.detail = result.payload;
    clearEinvoiceView();
    loadEinvoiceView(invoiceId);  // async — the section fills in when it lands
    setBusinessSalesView("detail");
    await loadInvoiceAttachments(invoiceId);
  } else {
    salesUi.attachmentsLoading = false;
    setLoginStatus("danger", "Unable to load invoice", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { invoice_detail: { ok: result.ok, status: result.status } });
}
export async function loadInvoiceAttachments(invoiceId) {
  if (!invoiceId) {
    salesUi.attachments = [];
    salesUi.attachmentsLoading = false;
    rerenderSalesIfActive();
    return { ok: false, status: 0, payload: { detail: "Missing invoice id." } };
  }
  salesUi.attachmentsLoading = true;
  rerenderSalesIfActive();
  const result = await listBusinessAttachments("sales_invoice", invoiceId);
  salesUi.attachments = result.ok ? (Array.isArray(result.payload?.items) ? result.payload.items : []) : [];
  salesUi.attachmentsLoading = false;
  if (!result.ok) {
    setLoginStatus("warn", "Unable to load invoice files", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  rerenderSalesIfActive();
  renderJson(getApiOutput(), { invoice_attachments: { ok: result.ok, status: result.status, count: salesUi.attachments.length } });
  return result;
}
export async function cancelInvoice(invoiceId, reversalDate) {
  const body = { reason: "Reversal" };
  if (reversalDate) body.cancel_date = reversalDate;
  const result = await apiRequest("mitrabooks", `/api/v1/business/invoices/${encodeURIComponent(invoiceId)}/cancel`, {
    method: "POST",
    headers: { "X-Idempotency-Key": `sales-invoice-cancel-${invoiceId}-${reversalDate || "today"}` },
    body: JSON.stringify(body),
  });
  if (result.ok) {
    salesUi.reverseOpen = false;
    setLoginStatus("ok", "Invoice reversed", "A reversing journal entry was posted.");
    await loadBusinessInvoices();
    if (salesUi.detail && salesUi.detail.invoice_id === invoiceId) {
      salesUi.detail = result.payload;
    }
    rerenderSalesIfActive();
  } else {
    setLoginStatus("danger", "Reverse failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { cancel_invoice: { ok: result.ok, status: result.status } });
}
export function invoiceStatusPill(status) {
  const s = String(status || "").toLowerCase();
  // Backend marks a reversed document as "cancelled"; display it as "reversed"
  // to match the accounting action (a reversing journal entry was posted).
  if (s === "cancelled") return `<span class="pill warn">reversed</span>`;
  if (s === "posted") return `<span class="pill ok">posted</span>`;
  return `<span class="pill">${escapeHtml(status || "")}</span>`;
}
export function renderInvoiceListTable() {
  const rows = salesUi.invoices;
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Invoice #</th>
            <th>Date</th>
            <th>Customer</th>
            <th class="amount">Taxable</th>
            <th class="amount">GST</th>
            <th class="amount">Total</th>
            <th>Status</th>
            <th>Open</th>
          </tr>
        </thead>
        <tbody>
          ${rows.length ? rows.map((inv) => `
            <tr>
              <td>${escapeHtml(inv.invoice_number || "")}</td>
              <td>${escapeHtml(inv.invoice_date || "")}</td>
              <td>${escapeHtml(inv.customer_name || inv.customer_party_id || "")}</td>
              <td class="amount">${escapeHtml(formatCurrency(inv.taxable_total || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(inv.gst_total || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(inv.invoice_total || 0))}</td>
              <td>${invoiceStatusPill(inv.status)}</td>
              <td><button class="secondary" type="button" data-business-action="view-invoice" data-invoice-id="${escapeHtml(inv.invoice_id)}">View</button></td>
            </tr>
          `).join("") : `<tr><td colspan="8" class="muted">No invoices yet. Create your first sales invoice.</td></tr>`}
        </tbody>
      </table>
    </div>
  `;
}
export function invoiceFieldLabel(base, key) {
  return `${base}${invoiceFieldRequired(key) ? " *" : ""}`;
}
export function invoiceNumberPreview() {
  const n = (salesUi.settings && salesUi.settings.numbering) || {};
  const now = new Date();
  const year = now.getMonth() < 3 ? now.getFullYear() - 1 : now.getFullYear();
  const fy = `${year}-${year + 1}`;
  const fyShort = `${year}-${String(year + 1).slice(-2)}`;
  const seq = String(n.start_number || 1).padStart(Number(n.seq_padding || 6), "0");
  return String(n.number_format || "{PREFIX}-{FY}-{SEQ}")
    .replace("{PREFIX}", n.prefix || "INV")
    .replace("{FYSHORT}", fyShort)
    .replace("{FY}", fy)
    .replace("{SEQ}", seq);
}
export function renderInvoiceCreateForm() {
  const customers = customerPartyOptions();
  const incomeAccounts = incomeAccountOptions();
  const hsnVisible = invoiceFieldVisible("hsn_sac");
  const hsnRequired = invoiceFieldRequired("hsn_sac");
  const lineCostCentreOptions = (selected) => dimensionOptions("cost_centre", selected || "");
  const lineProjectOptions = (selected) => dimensionOptions("project", selected || "");
  const hasLineDimensions = !!(lineCostCentreOptions("") || lineProjectOptions(""));
  const colspan = (hsnVisible ? 9 : 8) + (hasLineDimensions ? 1 : 0);
  const itemSelectable = !!inventoryItemOptions("");
  const lineRows = salesUi.formLines.map((l) => `
    <tr data-invoice-line="${escapeHtml(l.id)}">
      <td><input type="text" name="description" value="${escapeHtml(l.description)}" placeholder="Item / service"></td>
      ${itemSelectable ? `<td><select name="item_id" style="min-width:110px;">${inventoryItemOptions(l.item_id || "")}</select></td>` : ""}
      ${hsnVisible ? `<td><input type="text" name="hsn_sac" value="${escapeHtml(l.hsn_sac)}" placeholder="HSN/SAC"></td>` : ""}
      ${hsnVisible ? `<td><input type="text" name="uqc" value="${escapeHtml(l.uqc || "")}" placeholder="UQC" style="width:70px;"></td>` : ""}
      <td><select name="supply_type" style="min-width:96px;">
        ${[["taxable", "Taxable"], ["zero_rated", "Zero-rated (exp/SEZ)"], ["exempt", "Exempt"], ["nil_rated", "Nil-rated"], ["non_gst", "Non-GST"]].map(([v, t]) =>
          `<option value="${v}" ${(l.supply_type || "taxable") === v ? "selected" : ""}>${t}</option>`).join("")}
      </select></td>
      <td><input type="number" name="quantity" value="${escapeHtml(l.quantity)}" min="0" step="any"></td>
      <td><input type="number" name="rate" value="${escapeHtml(l.rate)}" min="0" step="any" placeholder="0.00"></td>
      <td><input type="number" name="gst_rate" value="${escapeHtml(l.gst_rate)}" min="0" max="100" step="any"></td>
      ${hasLineDimensions ? `<td class="line-dimensions">
        ${lineCostCentreOptions(l.cost_centre_id) ? `<select name="line_cost_centre_id" aria-label="Line cost centre">${lineCostCentreOptions(l.cost_centre_id)}</select>` : ""}
        ${lineProjectOptions(l.project_id) ? `<select name="line_project_id" aria-label="Line project">${lineProjectOptions(l.project_id)}</select>` : ""}
      </td>` : ""}
      <td class="amount" data-line-taxable>—</td>
      <td class="amount" data-line-gst>—</td>
      <td class="amount" data-line-total>—</td>
      <td><button class="secondary" type="button" data-business-action="remove-invoice-line" data-line-id="${escapeHtml(l.id)}">✕</button></td>
    </tr>
  `).join("");

  const isComposition = (salesUi.settings?.branding?.gst_registration_type === "composition");
  const docTitle = isComposition ? "New Bill of Supply" : "New Sales Invoice";
  const docSubtitle = isComposition
    ? `Next number: <strong>${escapeHtml(invoiceNumberPreview())}</strong> · composition dealer — no GST is collected; posts to receivables and income only.`
    : `Next number: <strong>${escapeHtml(invoiceNumberPreview())}</strong> · posts to receivables, sales income, and output GST automatically.`;
  const compositionBanner = isComposition
    ? `<p class="muted" style="padding:8px 10px;border:1px solid #f59e0b;border-radius:6px;background:#fffbeb;">⚠ Composition taxable person, not eligible to collect tax on supplies. GST rates entered below are ignored; inter-state sales are blocked.</p>`
    : "";
  return `
    <div class="verification-panel erp-workspace-panel" data-invoice-form>
      <div class="preview-heading compact">
        <div>
          <h4>${escapeHtml(docTitle)}</h4>
          <p>${docSubtitle}</p>
        </div>
        <button class="secondary" type="button" data-business-action="invoice-back">← Back to list</button>
      </div>
      ${compositionBanner}
      <div class="invoice-form-grid">
        <label>Customer
          <select name="customer_party_id">
            <option value="">Select customer</option>
            ${customers.map((c) => `<option value="${escapeHtml(c.party_id)}" ${c.party_id === salesUi.header.customer_party_id ? "selected" : ""}>${escapeHtml(c.party_name)}${c.gstin ? ` (${escapeHtml(c.gstin)})` : ""}</option>`).join("")}
          </select>
        </label>
        <label>Invoice date
          <input type="date" name="invoice_date" value="${escapeHtml(salesUi.header.invoice_date)}">
        </label>
        ${invoiceFieldVisible("due_date") ? `<label>${escapeHtml(invoiceFieldLabel("Due date", "due_date"))}
          <input type="date" name="due_date" value="${escapeHtml(salesUi.header.due_date)}">
        </label>` : ""}
        <label>Income account
          <select name="income_account_code">
            ${incomeAccounts.length ? incomeAccounts.map((a) => `<option value="${escapeHtml(a.code)}" ${a.code === salesUi.header.income_account_code ? "selected" : ""}>${escapeHtml(`${a.code} - ${a.name}`)}</option>`).join("") : `<option value="41001" selected>41001 - Sales</option>`}
          </select>
        </label>
        ${invoiceFieldVisible("place_of_supply") ? `<label>${escapeHtml(invoiceFieldLabel("Place of supply", "place_of_supply"))}
          <input type="text" name="place_of_supply" value="${escapeHtml(salesUi.header.place_of_supply)}" placeholder="State / code">
        </label>` : ""}
        ${invoiceFieldVisible("reference") ? `<label>${escapeHtml(invoiceFieldLabel("Reference / PO", "reference"))}
          <input type="text" name="reference" value="${escapeHtml(salesUi.header.reference)}" placeholder="${invoiceFieldRequired("reference") ? "Required" : "Optional"}">
        </label>` : ""}
        <label>TCS (income-tax, on sale consideration)
          <select name="tcs_section">${tdsSectionOptions("tcs", salesUi.header.tcs_section)}</select>
        </label>
        ${dimensionOptions("cost_centre", salesUi.header.cost_centre_id) ? `<label>Cost centre
          <select name="cost_centre_id">${dimensionOptions("cost_centre", salesUi.header.cost_centre_id)}</select>
        </label>` : ""}
        ${dimensionOptions("project", salesUi.header.project_id) ? `<label>Project
          <select name="project_id">${dimensionOptions("project", salesUi.header.project_id)}</select>
        </label>` : ""}
        <label class="invoice-inter-toggle">
          <input type="checkbox" name="is_inter_state" ${salesUi.header.is_inter_state ? "checked" : ""}>
          Inter-state supply (IGST)
        </label>
      </div>

      <div class="table-preview compact-table invoice-lines">
        <table>
          <thead>
            <tr>
              <th>Description</th>
              ${itemSelectable ? `<th>Item</th>` : ""}
              ${hsnVisible ? `<th>HSN/SAC${hsnRequired ? " *" : ""}</th>` : ""}
              ${hsnVisible ? `<th>UQC</th>` : ""}
              <th>Type</th>
              <th>Qty</th>
              <th>Rate</th>
              <th>GST %</th>
              ${hasLineDimensions ? `<th>Line dimensions</th>` : ""}
              <th class="amount">Taxable</th>
              <th class="amount">GST</th>
              <th class="amount">Total</th>
              <th></th>
            </tr>
          </thead>
          <tbody>${lineRows}</tbody>
        </table>
      </div>
      <button class="secondary" type="button" data-business-action="add-invoice-line" aria-keyshortcuts="Alt+L">+ Add line</button>

      <div class="invoice-totals">
        <div><span>Taxable</span><strong data-total-taxable>${formatCurrency(0)}</strong></div>
        <div data-row-cgst ${salesUi.header.is_inter_state ? "hidden" : ""}><span>CGST</span><strong data-total-cgst>${formatCurrency(0)}</strong></div>
        <div data-row-sgst ${salesUi.header.is_inter_state ? "hidden" : ""}><span>SGST</span><strong data-total-sgst>${formatCurrency(0)}</strong></div>
        <div data-row-igst ${salesUi.header.is_inter_state ? "" : "hidden"}><span>IGST</span><strong data-total-igst>${formatCurrency(0)}</strong></div>
        <div class="invoice-grand"><span>Invoice total</span><strong data-total-invoice>${formatCurrency(0)}</strong></div>
        <div data-row-tcs ${salesUi.header.tcs_section ? "" : "hidden"}><span>TCS</span><strong data-total-tcs>${formatCurrency(0)}</strong></div>
        <div class="invoice-grand" data-row-grand ${salesUi.header.tcs_section ? "" : "hidden"}><span>Amount receivable</span><strong data-total-grand>${formatCurrency(0)}</strong></div>
      </div>

      ${invoiceFieldVisible("notes") ? `<label class="invoice-notes">${escapeHtml(invoiceFieldLabel("Notes", "notes"))}
        <textarea name="notes" rows="2" placeholder="${invoiceFieldRequired("notes") ? "Required" : "Optional notes shown on the invoice"}">${escapeHtml(salesUi.header.notes)}</textarea>
      </label>` : ""}

      <div class="invoice-form-actions">
        <button class="primary" type="button" data-business-action="save-invoice" aria-keyshortcuts="Control+Enter">Post Invoice</button>
        <button class="secondary" type="button" data-business-action="invoice-back">Cancel</button>
      </div>
    </div>
  `;
}
export function renderInvoiceDetail() {
  const inv = salesUi.detail;
  if (!inv) {
    return `<div class="verification-panel erp-workspace-panel"><p class="muted">Invoice not found.</p></div>`;
  }
  const lines = Array.isArray(inv.line_items) ? inv.line_items : [];
  const taxRow = inv.is_inter_state
    ? `<div data-row-igst><span>IGST</span><strong>${formatCurrency(inv.igst_total || 0)}</strong></div>`
    : `<div><span>CGST</span><strong>${formatCurrency(inv.cgst_total || 0)}</strong></div><div><span>SGST</span><strong>${formatCurrency(inv.sgst_total || 0)}</strong></div>`;
  return `
    <div class="verification-panel erp-workspace-panel">
      <div class="preview-heading compact">
        <div>
          <h4>${escapeHtml(inv.is_composition || inv.document_type === "bill_of_supply" ? "Bill of Supply" : "Invoice")} ${escapeHtml(inv.invoice_number || "")} ${invoiceStatusPill(inv.status)}${inv.is_composition || inv.document_type === "bill_of_supply" ? ` <span class="pill">composition</span>` : ""}</h4>
          <p>${escapeHtml(inv.customer_name || inv.customer_party_id || "")}${inv.customer_gstin ? ` · ${escapeHtml(inv.customer_gstin)}` : ""} · ${escapeHtml(inv.invoice_date || "")}${inv.due_date ? ` · due ${escapeHtml(inv.due_date)}` : ""}</p>
        </div>
        <div class="invoice-detail-actions">
          <button class="secondary" type="button" data-business-action="invoice-back">← Back to list</button>
          <button class="secondary" type="button" data-business-action="download-invoice-pdf" data-invoice-id="${escapeHtml(inv.invoice_id || "")}" data-invoice-number="${escapeHtml(inv.invoice_number || "")}">Download PDF</button>
          ${String(inv.status).toLowerCase() === "posted" && !salesUi.reverseOpen ? `<button class="secondary" type="button" data-business-action="begin-reverse-invoice">Reverse Invoice</button>` : ""}
        </div>
      </div>
      ${String(inv.status).toLowerCase() === "posted" && salesUi.reverseOpen ? reversalPanel("invoice", inv.invoice_id, inv.invoice_date) : ""}
      <p class="muted">${escapeHtml(inv.is_composition || inv.document_type === "bill_of_supply" ? "Composition taxable person, not eligible to collect tax on supplies" : (inv.is_inter_state ? "Inter-state supply (IGST)" : "Intra-state supply (CGST + SGST)"))}${inv.reference ? ` · Ref: ${escapeHtml(inv.reference)}` : ""}</p>
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr>
              <th>Description</th>
              <th>HSN/SAC</th>
              <th class="amount">Qty</th>
              <th class="amount">Rate</th>
              <th class="amount">GST %</th>
              <th class="amount">Taxable</th>
              <th class="amount">Total</th>
            </tr>
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
        <div><span>Taxable</span><strong>${formatCurrency(inv.taxable_total || 0)}</strong></div>
        ${taxRow}
        <div class="invoice-grand"><span>Invoice total</span><strong>${formatCurrency(inv.invoice_total || 0)}</strong></div>
        ${Number(inv.tcs_amount || 0) > 0 ? `
        <div><span>TCS ${escapeHtml(inv.tcs_section || "")} @ ${escapeHtml(String(inv.tcs_rate || 0))}%</span><strong>${formatCurrency(inv.tcs_amount || 0)}</strong></div>
        <div class="invoice-grand"><span>Amount receivable</span><strong>${formatCurrency(inv.grand_total || inv.invoice_total || 0)}</strong></div>` : ""}
      </div>
      ${inv.collectee_pan_missing ? `<p class="muted">⚠ Customer PAN missing — section 206AA prescribes a higher TCS rate. Capture the PAN on the party record.</p>` : ""}
      ${renderEinvoiceSection(inv)}
      ${renderBusinessAttachmentPanel({
        ownerType: "sales_invoice",
        ownerId: inv.invoice_id || "",
        items: salesUi.attachments,
        loading: salesUi.attachmentsLoading,
        title: "Invoice attachments",
        emptyCopy: "Upload supporting sales documents, signed copies, or customer references for this invoice.",
        uploadButtonLabel: "Upload invoice files",
      })}
      ${inv.notes ? `<p class="muted">${escapeHtml(inv.notes)}</p>` : ""}
      ${String(inv.status).toLowerCase() === "cancelled" ? `<p class="muted">Reversed${inv.cancel_reason ? `: ${escapeHtml(inv.cancel_reason)}` : ""}. Reversing journal entry #${escapeHtml(inv.reversal_journal_entry_id || "")} posted.</p>` : ""}
    </div>
  `;
}
export function openInvoiceSettings() {
  if (!salesUi.settings) loadInvoiceSettings();
  setBusinessSalesView("settings");
}
export async function saveInvoiceSettings() {
  const panel = document.querySelector("[data-invoice-settings-form]");
  if (!panel) return;
  const field_config = {};
  Object.keys(INVOICE_STANDARD_FIELD_LABELS).forEach((key) => {
    const visible = panel.querySelector(`input[data-field-visible='${key}']`);
    const required = panel.querySelector(`input[data-field-required='${key}']`);
    field_config[key] = { visible: !!visible?.checked, required: !!required?.checked };
  });
  const numVal = (name) => panel.querySelector(`[data-numbering='${name}']`)?.value;
  const numbering = {
    prefix: (numVal("prefix") || "INV").trim() || "INV",
    number_format: (numVal("number_format") || "{PREFIX}-{FY}-{SEQ}").trim() || "{PREFIX}-{FY}-{SEQ}",
    seq_padding: Math.max(1, Math.min(12, Number(numVal("seq_padding") || 6))),
    start_number: Math.max(1, Number(numVal("start_number") || 1)),
    reset_yearly: !!panel.querySelector("[data-numbering='reset_yearly']")?.checked,
  };
  // Merge the GST registration choices into branding, preserving other fields.
  const regType = panel.querySelector("[data-gst-reg='type']")?.value === "composition" ? "composition" : "regular";
  const regCategory = panel.querySelector("[data-gst-reg='category']")?.value || "goods";
  const branding = {
    ...((salesUi.settings && salesUi.settings.branding) || {}),
    gst_registration_type: regType,
    composition_category: regType === "composition" ? regCategory : null,
  };
  const inventoryToggle = panel.querySelector("[data-inventory-enabled]");
  const inventoryPolicy = panel.querySelector("[data-inventory-valuation-policy]")?.value || "weighted_average_periodic";
  const body = {
    field_config,
    numbering,
    // Preserve sections managed in Phase 2 (custom fields).
    custom_fields: (salesUi.settings && salesUi.settings.custom_fields) || [],
    branding,
    inventory_enabled: inventoryToggle ? !!inventoryToggle.checked : !!salesUi.settings?.inventory_enabled,
    inventory_valuation_policy: inventoryPolicy,
  };
  const result = await apiRequest("mitrabooks", "/api/v1/business/invoice-settings", {
    method: "PUT",
    body: JSON.stringify(body),
  });
  if (result.ok) {
    salesUi.settings = result.payload;
    setLoginStatus("ok", "Invoice settings saved", "New invoices will use these settings.");
    setBusinessSalesView("list");
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can change invoice settings.");
  } else {
    setLoginStatus("danger", "Save failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { save_invoice_settings: { ok: result.ok, status: result.status } });
}
export function renderInvoiceSettingsPanel() {
  const s = salesUi.settings || {};
  const fc = s.field_config || {};
  const n = s.numbering || {};
  const fieldRows = Object.entries(INVOICE_STANDARD_FIELD_LABELS).map(([key, label]) => {
    const rule = fc[key] || { visible: true, required: false };
    return `
      <tr>
        <td>${escapeHtml(label)}</td>
        <td><label class="inline-check"><input type="checkbox" data-field-visible="${key}" ${rule.visible !== false ? "checked" : ""}> Visible</label></td>
        <td><label class="inline-check"><input type="checkbox" data-field-required="${key}" ${rule.required ? "checked" : ""}> Required</label></td>
      </tr>
    `;
  }).join("");

  return `
    <div class="verification-panel erp-workspace-panel" data-invoice-settings-form>
      <div class="preview-heading compact">
        <div>
          <h4>Invoice Settings</h4>
          <p>Configure the sales invoice form for this business. Applies to all users.</p>
        </div>
        <button class="secondary" type="button" data-business-action="invoice-back">← Back to list</button>
      </div>

      <h5 class="settings-section-title">Form fields</h5>
      <p class="muted">Show, hide, or require the optional fields on the invoice form.</p>
      <div class="table-preview compact-table">
        <table>
          <thead><tr><th>Field</th><th>Show on form</th><th>Make mandatory</th></tr></thead>
          <tbody>${fieldRows}</tbody>
        </table>
      </div>

      <h5 class="settings-section-title">Invoice numbering</h5>
      <p class="muted">Tokens: <code>{PREFIX}</code> <code>{FY}</code> (2026-2027) <code>{FYSHORT}</code> (2026-27) <code>{SEQ}</code></p>
      <div class="invoice-form-grid">
        <label>Prefix<input type="text" data-numbering="prefix" value="${escapeHtml(n.prefix || "INV")}"></label>
        <label>Number format<input type="text" data-numbering="number_format" value="${escapeHtml(n.number_format || "{PREFIX}-{FY}-{SEQ}")}"></label>
        <label>Sequence digits<input type="number" data-numbering="seq_padding" min="1" max="12" value="${escapeHtml(n.seq_padding || 6)}"></label>
        <label>Start number<input type="number" data-numbering="start_number" min="1" value="${escapeHtml(n.start_number || 1)}"></label>
        <label class="invoice-inter-toggle"><input type="checkbox" data-numbering="reset_yearly" ${n.reset_yearly !== false ? "checked" : ""}> Reset sequence each financial year</label>
      </div>
      <p class="muted">Preview: <strong>${escapeHtml(invoiceNumberPreview())}</strong></p>

      <h5 class="settings-section-title">GST registration</h5>
      <p class="muted">Composition dealers (Section 10) issue a <strong>Bill of Supply</strong>, do not collect GST, and cannot claim ITC. Inter-state sales are not allowed.</p>
      <div class="invoice-form-grid">
        <label>Registration type
          <select data-gst-reg="type">
            <option value="regular" ${(s.branding?.gst_registration_type || "regular") !== "composition" ? "selected" : ""}>Regular (collect GST, claim ITC)</option>
            <option value="composition" ${s.branding?.gst_registration_type === "composition" ? "selected" : ""}>Composition (Bill of Supply)</option>
          </select>
        </label>
        <label>Composition category
          <select data-gst-reg="category">
            <option value="goods" ${(s.branding?.composition_category || "goods") === "goods" ? "selected" : ""}>Manufacturer / Trader — 1%</option>
            <option value="restaurant" ${s.branding?.composition_category === "restaurant" ? "selected" : ""}>Restaurant (non-alcoholic) — 5%</option>
            <option value="services" ${s.branding?.composition_category === "services" ? "selected" : ""}>Other services — 6%</option>
          </select>
        </label>
      </div>

      <h5 class="settings-section-title">Inventory accounting</h5>
      <p class="muted">Optional. Service businesses and traders who don't keep stock should leave this OFF — nothing changes for them. When ON, the item master, stock register and the period-end closing-stock journal appear under Financial Statements → Inventory.</p>
      <label class="invoice-inter-toggle">
        <input type="checkbox" data-inventory-enabled ${s.inventory_enabled ? "checked" : ""}>
        Enable inventory accounting (item master, stock register, closing stock)
      </label>
      <div class="invoice-form-grid">
        <label>Valuation policy
          <select data-inventory-valuation-policy>
            <option value="weighted_average_periodic" ${(s.inventory_valuation_policy || "weighted_average_periodic") === "weighted_average_periodic" ? "selected" : ""}>Weighted average (periodic)</option>
          </select>
        </label>
      </div>
      <p class="muted">The current local policy is locked to weighted-average periodic costing. Stock issues and adjustments affect the register; the financial impact is posted through the closing-stock journal.</p>

      <p class="muted settings-coming-soon">Custom fields and invoice branding / print template are coming in the next update.</p>

      <div class="invoice-form-actions">
        <button class="primary" type="button" data-business-action="save-invoice-settings">Save Settings</button>
        <button class="secondary" type="button" data-business-action="invoice-back">Cancel</button>
      </div>
    </div>
  `;
}
export function renderBusinessSalesWorkspace() {
  if (salesUi.view === "create") {
    return renderInvoiceCreateForm();
  }
  if (salesUi.view === "detail") {
    return renderInvoiceDetail();
  }
  if (salesUi.view === "settings") {
    return renderInvoiceSettingsPanel();
  }
  return `
    <div class="verification-panel erp-workspace-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Sales Invoices</h4>
          <p>GST invoices for customers. Each posting updates receivables, income, and output GST.</p>
        </div>
        <div class="invoice-detail-actions">
          ${isBusinessAdmin() ? `<button class="secondary" type="button" data-business-action="open-invoice-settings">⚙ Settings</button>` : ""}
          <button class="secondary" type="button" data-business-action="open-create-invoice" aria-keyshortcuts="Control+Alt+I">+ New Invoice</button>
        </div>
      </div>
      ${renderInvoiceListTable()}
    </div>
  `;
}
