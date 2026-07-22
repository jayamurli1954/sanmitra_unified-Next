// ====================================================================
// SECTION: PURCHASE BILLS WORKSPACE
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initPurchaseBills(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";
import { computeInvoiceLine, invoiceStatusPill } from "./sales-invoices.js";

export const purchaseUi = {
  view: "list", // list | create | detail
  bills: [],
  detail: null,
  lineSeq: 0,
  formLines: [],
  header: {
    vendor_party_id: "",
    bill_number: "",
    bill_date: "",
    due_date: "",
    is_inter_state: false,
    is_reverse_charge: false,
    expense_account_code: "51001",
    place_of_supply: "",
    notes: "",
    tds_section: "",
    cost_centre_id: "",
    project_id: "",
  },
  reverseOpen: false,
  attachments: [],
  attachmentsLoading: false,
};

/** @type {Record<string, Function> | null} */
let deps = null;

export function initPurchaseBills(injected) {
  deps = injected;
  purchaseUi.header.bill_date = injected.todayIsoDate();
}

function requireDeps() {
  if (!deps) {
    throw new Error("initPurchaseBills() must be called before using purchase bill helpers");
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
function renderBusinessAttachmentPanel(opts) { return requireDeps().renderBusinessAttachmentPanel(opts); }
function listBusinessAttachments(ownerType, ownerId) { return requireDeps().listBusinessAttachments(ownerType, ownerId); }
function getApiOutput() { return requireDeps().getApiOutput(); }



export function rerenderPurchaseIfActive() {
  if (getCurrentExperience() === "mitrabooks" && getActiveBusinessWorkspace() === "bills") {
    getDashboardPreview().innerHTML = renderBusinessWorkspace();
    if (purchaseUi.view === "create") {
      focusBusinessEntryField("[data-bill-form] select[name='vendor_party_id']");
    }
  }
}

export async function loadBusinessBills() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/bills?limit=100", { method: "GET" });
  if (result.ok) {
    purchaseUi.bills = Array.isArray(result.payload?.items) ? result.payload.items : [];
  } else {
    purchaseUi.bills = [];
    setLoginStatus("danger", "Unable to load bills", statusDetailText(result.payload?.detail) || `Bill list request failed with HTTP ${result.status}.`);
  }
  rerenderPurchaseIfActive();
  renderJson(getApiOutput(), { bills: { ok: result.ok, status: result.status, count: purchaseUi.bills.length } });
}

export function vendorPartyOptions() {
  return (Array.isArray(getLastBusinessParties()) ? getLastBusinessParties() : [])
    .filter((p) => ["vendor", "both"].includes(String(p.party_type || "").toLowerCase()));
}

export function expenseAccountOptions() {
  return businessAccountsForSelection().filter((acc) => String(acc.code || "").startsWith("5"));
}

export function syncBillFormFromDom() {
  const form = document.querySelector("[data-bill-form]");
  if (!form) return;
  const val = (sel) => form.querySelector(sel)?.value ?? "";
  purchaseUi.header.vendor_party_id = val("select[name='vendor_party_id']");
  purchaseUi.header.bill_number = val("input[name='bill_number']");
  purchaseUi.header.bill_date = val("input[name='bill_date']") || todayIsoDate();
  purchaseUi.header.due_date = val("input[name='due_date']");
  purchaseUi.header.is_inter_state = !!form.querySelector("input[name='is_inter_state']")?.checked;
  purchaseUi.header.is_reverse_charge = !!form.querySelector("input[name='is_reverse_charge']")?.checked;
  purchaseUi.header.expense_account_code = val("select[name='expense_account_code']") || "51001";
  purchaseUi.header.place_of_supply = val("input[name='place_of_supply']");
  purchaseUi.header.notes = val("textarea[name='notes']");
  purchaseUi.header.tds_section = val("select[name='tds_section']");
  purchaseUi.header.cost_centre_id = val("select[name='cost_centre_id']");
  purchaseUi.header.project_id = val("select[name='project_id']");
  purchaseUi.formLines = Array.from(form.querySelectorAll("[data-bill-line]")).map((row) => ({
    id: row.getAttribute("data-bill-line"),
    description: row.querySelector("input[name='description']")?.value || "",
    item_id: row.querySelector("select[name='item_id']")?.value || "",
    hsn_sac: row.querySelector("input[name='hsn_sac']")?.value || "",
    quantity: row.querySelector("input[name='quantity']")?.value || "",
    rate: row.querySelector("input[name='rate']")?.value || "",
    gst_rate: row.querySelector("input[name='gst_rate']")?.value || "",
    cost_centre_id: row.querySelector("select[name='line_cost_centre_id']")?.value || "",
    project_id: row.querySelector("select[name='line_project_id']")?.value || "",
  }));
}

export function updateBillTotalsDisplay() {
  const form = document.querySelector("[data-bill-form]");
  if (!form) return;
  const inter = !!form.querySelector("input[name='is_inter_state']")?.checked;
  let taxableTotal = 0, cgstTotal = 0, sgstTotal = 0, igstTotal = 0;
  form.querySelectorAll("[data-bill-line]").forEach((row) => {
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
  const billTotal = round2(taxableTotal + gstTotal);
  // TDS is deducted on the GST-exclusive taxable value (Circular 23/2017).
  const tdsSection = form.querySelector("select[name='tds_section']")?.value || "";
  const tdsAmount = tdsSection ? round2(taxableTotal * tdsSectionRate("tds", tdsSection) / 100) : 0;
  // Under RCM the vendor is owed the taxable value only; the GST is our own
  // (cash-only) liability shown on its own row.
  const isRcm = !!form.querySelector("input[name='is_reverse_charge']")?.checked;
  const vendorOwed = isRcm ? taxableTotal : billTotal;
  const set = (sel, v) => { const el = form.querySelector(sel); if (el) el.textContent = formatCurrency(v); };
  set("[data-total-taxable]", taxableTotal);
  set("[data-total-cgst]", cgstTotal);
  set("[data-total-sgst]", sgstTotal);
  set("[data-total-igst]", igstTotal);
  set("[data-total-bill]", billTotal);
  set("[data-total-rcm]", gstTotal);
  set("[data-total-tds]", tdsAmount);
  set("[data-total-net-payable]", round2(vendorOwed - tdsAmount));
  const rcmRow = form.querySelector("[data-row-rcm]");
  const tdsRow = form.querySelector("[data-row-tds]");
  const netRow = form.querySelector("[data-row-net-payable]");
  if (rcmRow) rcmRow.hidden = !isRcm;
  if (tdsRow) tdsRow.hidden = !tdsSection;
  if (netRow) netRow.hidden = !(tdsSection || isRcm);
  const cgstRow = form.querySelector("[data-row-cgst]");
  const sgstRow = form.querySelector("[data-row-sgst]");
  const igstRow = form.querySelector("[data-row-igst]");
  if (cgstRow && sgstRow && igstRow) {
    cgstRow.hidden = inter;
    sgstRow.hidden = inter;
    igstRow.hidden = !inter;
  }
}

export function setBusinessPurchaseView(view) {
  purchaseUi.view = view;
  purchaseUi.reverseOpen = false;
  rerenderPurchaseIfActive();
  if (view === "create") {
    updateBillTotalsDisplay();
    focusBusinessEntryField("[data-bill-form] select[name='vendor_party_id']");
  }
}

export function openBillCreate() {
  purchaseUi.formLines = [{ id: `bl-${++purchaseUi.lineSeq}`, description: "", hsn_sac: "", quantity: "1", rate: "", gst_rate: "18", cost_centre_id: "", project_id: "" }];
  purchaseUi.header.vendor_party_id = "";
  purchaseUi.header.bill_number = "";
  purchaseUi.header.bill_date = todayIsoDate();
  purchaseUi.header.due_date = "";
  purchaseUi.header.is_inter_state = false;
  purchaseUi.header.is_reverse_charge = false;
  purchaseUi.header.expense_account_code = "51001";
  purchaseUi.header.place_of_supply = "";
  purchaseUi.header.notes = "";
  purchaseUi.header.tds_section = "";
  purchaseUi.header.cost_centre_id = "";
  purchaseUi.header.project_id = "";
  if (!Array.isArray(getLastBusinessParties()) || getLastBusinessParties().length === 0) loadBusinessParties();
  if (!hasLoadedBusinessAccounts()) loadBusinessAccounts();
  if (!hasTdsSectionsCache()) loadTdsSections().then(() => rerenderPurchaseIfActive());
  if (!getLastDimensions()) loadDimensions().then(() => rerenderPurchaseIfActive());
  if (!getLastInventoryItems()) loadInventoryItems().then(() => rerenderPurchaseIfActive());
  setBusinessPurchaseView("create");
}

export function addBillLine() {
  syncBillFormFromDom();
  purchaseUi.formLines.push({ id: `bl-${++purchaseUi.lineSeq}`, description: "", hsn_sac: "", quantity: "1", rate: "", gst_rate: "18", cost_centre_id: "", project_id: "" });
  rerenderPurchaseIfActive();
  updateBillTotalsDisplay();
}

export function removeBillLine(lineId) {
  syncBillFormFromDom();
  purchaseUi.formLines = purchaseUi.formLines.filter((l) => l.id !== lineId);
  if (purchaseUi.formLines.length === 0) {
    purchaseUi.formLines.push({ id: `bl-${++purchaseUi.lineSeq}`, description: "", hsn_sac: "", quantity: "1", rate: "", gst_rate: "18", cost_centre_id: "", project_id: "" });
  }
  rerenderPurchaseIfActive();
  updateBillTotalsDisplay();
}

export async function submitBill() {
  syncBillFormFromDom();
  if (!purchaseUi.header.vendor_party_id) {
    setLoginStatus("warn", "Vendor required", "Select a vendor for this bill.");
    return;
  }
  if (!String(purchaseUi.header.bill_number || "").trim()) {
    setLoginStatus("warn", "Bill number required", "Enter the supplier's bill/invoice number.");
    return;
  }
  const lineItems = purchaseUi.formLines
    .filter((l) => String(l.description).trim() && Number(l.quantity) > 0)
    .map((l) => ({
      description: String(l.description).trim(),
      item_id: String(l.item_id || "").trim() || null,
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
    vendor_party_id: purchaseUi.header.vendor_party_id,
    bill_number: String(purchaseUi.header.bill_number).trim(),
    bill_date: purchaseUi.header.bill_date || todayIsoDate(),
    due_date: purchaseUi.header.due_date || null,
    is_inter_state: !!purchaseUi.header.is_inter_state,
    is_reverse_charge: !!purchaseUi.header.is_reverse_charge,
    expense_account_code: purchaseUi.header.expense_account_code || "51001",
    place_of_supply: String(purchaseUi.header.place_of_supply || "").trim() || null,
    notes: String(purchaseUi.header.notes || "").trim() || null,
    line_items: lineItems,
    tds_section: purchaseUi.header.tds_section || null,
    cost_centre_id: purchaseUi.header.cost_centre_id || null,
    project_id: purchaseUi.header.project_id || null,
  };
  const result = await apiRequest("mitrabooks", "/api/v1/business/bills", {
    method: "POST",
    headers: { "X-Idempotency-Key": `purchase-bill-${Date.now()}` },
    body: JSON.stringify(body),
  });
  if (result.ok) {
    setLoginStatus("ok", "Bill posted", `${result.payload?.bill_number || "Bill"} posted to the ledger.`);
    await loadBusinessBills();
    setBusinessPurchaseView("list");
  } else {
    setLoginStatus("danger", "Bill posting failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { create_bill: { ok: result.ok, status: result.status, detail: result.payload?.detail || null } });
}

export async function openBillDetail(billId) {
  purchaseUi.attachmentsLoading = true;
  purchaseUi.attachments = [];
  const result = await apiRequest("mitrabooks", `/api/v1/business/bills/${encodeURIComponent(billId)}`, { method: "GET" });
  if (result.ok) {
    purchaseUi.detail = result.payload;
    setBusinessPurchaseView("detail");
    await loadBillAttachments(billId);
  } else {
    purchaseUi.attachmentsLoading = false;
    setLoginStatus("danger", "Unable to load bill", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { bill_detail: { ok: result.ok, status: result.status } });
}

export async function loadBillAttachments(billId) {
  if (!billId) {
    purchaseUi.attachments = [];
    purchaseUi.attachmentsLoading = false;
    rerenderPurchaseIfActive();
    return { ok: false, status: 0, payload: { detail: "Missing bill id." } };
  }
  purchaseUi.attachmentsLoading = true;
  rerenderPurchaseIfActive();
  const result = await listBusinessAttachments("purchase_bill", billId);
  purchaseUi.attachments = result.ok ? (Array.isArray(result.payload?.items) ? result.payload.items : []) : [];
  purchaseUi.attachmentsLoading = false;
  if (!result.ok) {
    setLoginStatus("warn", "Unable to load bill files", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  rerenderPurchaseIfActive();
  renderJson(getApiOutput(), { bill_attachments: { ok: result.ok, status: result.status, count: purchaseUi.attachments.length } });
  return result;
}

export async function cancelBill(billId, reversalDate) {
  const body = { reason: "Reversal" };
  if (reversalDate) body.cancel_date = reversalDate;
  const result = await apiRequest("mitrabooks", `/api/v1/business/bills/${encodeURIComponent(billId)}/cancel`, {
    method: "POST",
    headers: { "X-Idempotency-Key": `purchase-bill-cancel-${billId}-${reversalDate || "today"}` },
    body: JSON.stringify(body),
  });
  if (result.ok) {
    purchaseUi.reverseOpen = false;
    setLoginStatus("ok", "Bill reversed", "A reversing journal entry was posted.");
    await loadBusinessBills();
    if (purchaseUi.detail && purchaseUi.detail.bill_id === billId) {
      purchaseUi.detail = result.payload;
    }
    rerenderPurchaseIfActive();
  } else {
    setLoginStatus("danger", "Reverse failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { cancel_bill: { ok: result.ok, status: result.status } });
}

export function renderBillListTable() {
  const rows = purchaseUi.bills;
  return `
    <div class="table-preview compact-table">
      <table>
        <thead>
          <tr>
            <th>Bill #</th>
            <th>Date</th>
            <th>Vendor</th>
            <th class="amount">Taxable</th>
            <th class="amount">ITC</th>
            <th class="amount">Total</th>
            <th>Status</th>
            <th>Open</th>
          </tr>
        </thead>
        <tbody>
          ${rows.length ? rows.map((b) => `
            <tr>
              <td>${escapeHtml(b.bill_number || "")}</td>
              <td>${escapeHtml(b.bill_date || "")}</td>
              <td>${escapeHtml(b.vendor_name || b.vendor_party_id || "")}</td>
              <td class="amount">${escapeHtml(formatCurrency(b.taxable_total || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(b.gst_total || 0))}</td>
              <td class="amount">${escapeHtml(formatCurrency(b.bill_total || 0))}</td>
              <td>${invoiceStatusPill(b.status)}</td>
              <td><button class="secondary" type="button" data-business-action="view-bill" data-bill-id="${escapeHtml(b.bill_id)}">View</button></td>
            </tr>
          `).join("") : `<tr><td colspan="8" class="muted">No bills yet. Record your first vendor bill.</td></tr>`}
        </tbody>
      </table>
    </div>
  `;
}

export function renderBillCreateForm() {
  const vendors = vendorPartyOptions();
  const expenseAccounts = expenseAccountOptions();
  const itemSelectable = !!inventoryItemOptions("");
  const lineCostCentreOptions = (selected) => dimensionOptions("cost_centre", selected || "");
  const lineProjectOptions = (selected) => dimensionOptions("project", selected || "");
  const hasLineDimensions = !!(lineCostCentreOptions("") || lineProjectOptions(""));
  const lineRows = purchaseUi.formLines.map((l) => `
    <tr data-bill-line="${escapeHtml(l.id)}">
      <td><input type="text" name="description" value="${escapeHtml(l.description)}" placeholder="Item / service"></td>
      ${itemSelectable ? `<td><select name="item_id" style="min-width:110px;">${inventoryItemOptions(l.item_id || "")}</select></td>` : ""}
      <td><input type="text" name="hsn_sac" value="${escapeHtml(l.hsn_sac)}" placeholder="HSN/SAC"></td>
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
      <td><button class="secondary" type="button" data-business-action="remove-bill-line" data-line-id="${escapeHtml(l.id)}">✕</button></td>
    </tr>
  `).join("");

  return `
    <div class="verification-panel erp-workspace-panel" data-bill-form>
      <div class="preview-heading compact">
        <div>
          <h4>New Purchase Bill</h4>
          <p>Record a vendor bill. It posts to expenses, input GST (ITC), and accounts payable automatically.</p>
        </div>
        <button class="secondary" type="button" data-business-action="bill-back">← Back to list</button>
      </div>
      <div class="invoice-form-grid">
        <label>Vendor
          <select name="vendor_party_id">
            <option value="">Select vendor</option>
            ${vendors.map((v) => `<option value="${escapeHtml(v.party_id)}" ${v.party_id === purchaseUi.header.vendor_party_id ? "selected" : ""}>${escapeHtml(v.party_name)}${v.gstin ? ` (${escapeHtml(v.gstin)})` : ""}</option>`).join("")}
          </select>
        </label>
        <label>Supplier bill no. *
          <input type="text" name="bill_number" value="${escapeHtml(purchaseUi.header.bill_number)}" placeholder="Vendor's invoice number">
        </label>
        <label>Bill date
          <input type="date" name="bill_date" value="${escapeHtml(purchaseUi.header.bill_date)}">
        </label>
        <label>Due date
          <input type="date" name="due_date" value="${escapeHtml(purchaseUi.header.due_date)}">
        </label>
        <label>Expense account
          <select name="expense_account_code">
            ${expenseAccounts.length ? expenseAccounts.map((a) => `<option value="${escapeHtml(a.code)}" ${a.code === purchaseUi.header.expense_account_code ? "selected" : ""}>${escapeHtml(`${a.code} - ${a.name}`)}</option>`).join("") : `<option value="51001" selected>51001 - Purchases</option>`}
          </select>
        </label>
        <label>Place of supply
          <input type="text" name="place_of_supply" value="${escapeHtml(purchaseUi.header.place_of_supply)}" placeholder="State / code">
        </label>
        <label>TDS (income-tax, on taxable value)
          <select name="tds_section">${tdsSectionOptions("tds", purchaseUi.header.tds_section)}</select>
        </label>
        ${dimensionOptions("cost_centre", purchaseUi.header.cost_centre_id) ? `<label>Cost centre
          <select name="cost_centre_id">${dimensionOptions("cost_centre", purchaseUi.header.cost_centre_id)}</select>
        </label>` : ""}
        ${dimensionOptions("project", purchaseUi.header.project_id) ? `<label>Project
          <select name="project_id">${dimensionOptions("project", purchaseUi.header.project_id)}</select>
        </label>` : ""}
        <label class="invoice-inter-toggle">
          <input type="checkbox" name="is_inter_state" ${purchaseUi.header.is_inter_state ? "checked" : ""}>
          Inter-state supply (IGST)
        </label>
        <label class="invoice-inter-toggle">
          <input type="checkbox" name="is_reverse_charge" ${purchaseUi.header.is_reverse_charge ? "checked" : ""}>
          Reverse charge (RCM) — you pay the GST, not the vendor
        </label>
      </div>

      <div class="table-preview compact-table invoice-lines">
        <table>
          <thead>
            <tr>
              <th>Description</th>
              ${itemSelectable ? `<th>Item</th>` : ""}
              <th>HSN/SAC</th>
              <th>Qty</th>
              <th>Rate</th>
              <th>GST %</th>
              ${hasLineDimensions ? `<th>Line dimensions</th>` : ""}
              <th class="amount">Taxable</th>
              <th class="amount">ITC</th>
              <th class="amount">Total</th>
              <th></th>
            </tr>
          </thead>
          <tbody>${lineRows}</tbody>
        </table>
      </div>
      <button class="secondary" type="button" data-business-action="add-bill-line" aria-keyshortcuts="Alt+L">+ Add line</button>

      <div class="invoice-totals">
        <div><span>Taxable</span><strong data-total-taxable>${formatCurrency(0)}</strong></div>
        <div data-row-cgst ${purchaseUi.header.is_inter_state ? "hidden" : ""}><span>Input CGST</span><strong data-total-cgst>${formatCurrency(0)}</strong></div>
        <div data-row-sgst ${purchaseUi.header.is_inter_state ? "hidden" : ""}><span>Input SGST</span><strong data-total-sgst>${formatCurrency(0)}</strong></div>
        <div data-row-igst ${purchaseUi.header.is_inter_state ? "" : "hidden"}><span>Input IGST</span><strong data-total-igst>${formatCurrency(0)}</strong></div>
        <div class="invoice-grand"><span>Bill total</span><strong data-total-bill>${formatCurrency(0)}</strong></div>
        <div data-row-rcm ${purchaseUi.header.is_reverse_charge ? "" : "hidden"}><span>GST payable under RCM (cash)</span><strong data-total-rcm>${formatCurrency(0)}</strong></div>
        <div data-row-tds ${purchaseUi.header.tds_section ? "" : "hidden"}><span>TDS deducted</span><strong data-total-tds>${formatCurrency(0)}</strong></div>
        <div class="invoice-grand" data-row-net-payable ${(purchaseUi.header.tds_section || purchaseUi.header.is_reverse_charge) ? "" : "hidden"}><span>Net payable to vendor</span><strong data-total-net-payable>${formatCurrency(0)}</strong></div>
      </div>

      <label class="invoice-notes">Notes
        <textarea name="notes" rows="2" placeholder="Optional notes">${escapeHtml(purchaseUi.header.notes)}</textarea>
      </label>

      <div class="invoice-form-actions">
        <button class="primary" type="button" data-business-action="save-bill" aria-keyshortcuts="Control+Enter">Post Bill</button>
        <button class="secondary" type="button" data-business-action="bill-back">Cancel</button>
      </div>
    </div>
  `;
}

export function renderBillDetail() {
  const b = purchaseUi.detail;
  if (!b) {
    return `<div class="verification-panel erp-workspace-panel"><p class="muted">Bill not found.</p></div>`;
  }
  const lines = Array.isArray(b.line_items) ? b.line_items : [];
  const taxRow = b.is_inter_state
    ? `<div><span>Input IGST</span><strong>${formatCurrency(b.igst_total || 0)}</strong></div>`
    : `<div><span>Input CGST</span><strong>${formatCurrency(b.cgst_total || 0)}</strong></div><div><span>Input SGST</span><strong>${formatCurrency(b.sgst_total || 0)}</strong></div>`;
  return `
    <div class="verification-panel erp-workspace-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Bill ${escapeHtml(b.bill_number || "")} ${invoiceStatusPill(b.status)}</h4>
          <p>${escapeHtml(b.vendor_name || b.vendor_party_id || "")}${b.vendor_gstin ? ` · ${escapeHtml(b.vendor_gstin)}` : ""} · ${escapeHtml(b.bill_date || "")}${b.due_date ? ` · due ${escapeHtml(b.due_date)}` : ""}</p>
        </div>
        <div class="invoice-detail-actions">
          <button class="secondary" type="button" data-business-action="bill-back">← Back to list</button>
          ${String(b.status).toLowerCase() === "posted" && !purchaseUi.reverseOpen ? `<button class="secondary" type="button" data-business-action="begin-reverse-bill">Reverse Bill</button>` : ""}
        </div>
      </div>
      ${String(b.status).toLowerCase() === "posted" && purchaseUi.reverseOpen ? reversalPanel("bill", b.bill_id, b.bill_date) : ""}
      <p class="muted">${escapeHtml(b.is_inter_state ? "Inter-state supply (IGST input)" : "Intra-state supply (CGST + SGST input)")}${b.is_reverse_charge ? ` · <strong>Reverse charge</strong> — GST self-assessed, payable in cash` : ""}</p>
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
        <div><span>Taxable</span><strong>${formatCurrency(b.taxable_total || 0)}</strong></div>
        ${taxRow}
        <div class="invoice-grand"><span>Bill total</span><strong>${formatCurrency(b.bill_total || 0)}</strong></div>
        ${b.is_reverse_charge ? `
        <div><span>GST payable under RCM (cash)</span><strong>${formatCurrency(b.rcm_payable || 0)}</strong></div>` : ""}
        ${Number(b.tds_amount || 0) > 0 ? `
        <div><span>TDS ${escapeHtml(b.tds_section || "")} @ ${escapeHtml(String(b.tds_rate || 0))}%</span><strong>${formatCurrency(b.tds_amount || 0)}</strong></div>` : ""}
        ${(b.is_reverse_charge || Number(b.tds_amount || 0) > 0) ? `
        <div class="invoice-grand"><span>Net payable to vendor</span><strong>${formatCurrency(b.net_payable || b.bill_total || 0)}</strong></div>` : ""}
      </div>
      ${renderBusinessAttachmentPanel({
        ownerType: "purchase_bill",
        ownerId: b.bill_id || "",
        items: purchaseUi.attachments,
        loading: purchaseUi.attachmentsLoading,
        title: "Bill attachments",
        emptyCopy: "Upload supplier scans, supporting bills, or compliance evidence for this purchase bill.",
        uploadButtonLabel: "Upload bill files",
      })}
      ${b.deductee_pan_missing ? `<p class="muted">⚠ Vendor PAN missing — section 206AA prescribes deduction at 20%. Capture the PAN on the party record.</p>` : ""}
      ${b.notes ? `<p class="muted">${escapeHtml(b.notes)}</p>` : ""}
      ${String(b.status).toLowerCase() === "cancelled" ? `<p class="muted">Reversed${b.cancel_reason ? `: ${escapeHtml(b.cancel_reason)}` : ""}. Reversing journal entry #${escapeHtml(b.reversal_journal_entry_id || "")} posted.</p>` : ""}
    </div>
  `;
}



export function renderBusinessPurchaseWorkspace() {
  if (purchaseUi.view === "create") {
    return renderBillCreateForm();
  }
  if (purchaseUi.view === "detail") {
    return renderBillDetail();
  }
  return `
    <div class="verification-panel erp-workspace-panel">
      <div class="preview-heading compact">
        <div>
          <h4>Purchase Bills</h4>
          <p>Vendor bills with input GST. Each posting updates expenses, ITC, and accounts payable.</p>
        </div>
        <button class="secondary" type="button" data-business-action="open-create-bill" aria-keyshortcuts="Control+Alt+B">+ New Bill</button>
      </div>
      ${renderBillListTable()}
    </div>
  `;
}
