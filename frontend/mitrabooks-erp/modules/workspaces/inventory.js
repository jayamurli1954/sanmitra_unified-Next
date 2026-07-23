// ====================================================================
// SECTION: INVENTORY (opt-in, periodic method)
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initInventory(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastInventoryItems = null;
export let lastStockRegister = null;
export let lastClosingStockEntries = null;
export let lastInventoryPolicy = null;
export let lastStockMovements = null;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initInventory(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initInventory() must be called before using inventory helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function todayIsoDate() { return requireDeps().todayIsoDate(); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function reportUnavailablePanel(title, payload) { return requireDeps().reportUnavailablePanel(title, payload); }
function rerenderBusinessReportsIfActive() { return requireDeps().rerenderBusinessReportsIfActive(); }
function isBusinessAdmin() { return requireDeps().isBusinessAdmin(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

// SECTION: INVENTORY (opt-in, periodic method)
// API   : GET/POST /api/v1/business/inventory/items  GET .../stock-register
// NOTE  : loadInventoryItems, createInventoryItemFromForm, postClosingStock, renderInventoryPanel
// ══════════════════════════════════════════════════════════════════════

export async function loadInventoryItems() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/inventory/items", { method: "GET" });
  lastInventoryItems = result.ok ? result.payload : { ok: false, inventory_enabled: false, items: [], detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { inventory_items: { ok: result.ok, count: result.payload?.count || 0, enabled: !!result.payload?.inventory_enabled } });
  return lastInventoryItems;
}

export function inventoryItemOptions(selected) {
  if (!lastInventoryItems?.inventory_enabled) return null;
  const rows = lastInventoryItems?.items || [];
  if (!rows.length) return null;
  return `<option value="">No item</option>` + rows.map((it) =>
    `<option value="${escapeHtml(it.item_id)}" ${it.item_id === selected ? "selected" : ""}>${escapeHtml(`${it.code} - ${it.name}`)}</option>`).join("");
}

export function inventoryMovementItemOptions(selected = "") {
  const rows = lastInventoryItems?.items || [];
  return `<option value="">Select item</option>` + rows.map((it) =>
    `<option value="${escapeHtml(it.item_id)}" ${it.item_id === selected ? "selected" : ""}>${escapeHtml(`${it.code} - ${it.name}`)}</option>`).join("");
}

export async function createInventoryItemFromForm() {
  const form = document.querySelector("[data-item-form]");
  if (!form) return;
  const val = (sel) => form.querySelector(sel)?.value ?? "";
  const body = {
    code: val("input[name='item_code']"),
    name: val("input[name='item_name']"),
    uqc: val("input[name='item_uqc']") || "NOS",
    hsn_sac: val("input[name='item_hsn']") || null,
    gst_rate: val("input[name='item_gst']") || "0",
    opening_qty: val("input[name='item_open_qty']") || "0",
    opening_value: val("input[name='item_open_val']") || "0",
  };
  if (!body.name.trim()) {
    setLoginStatus("warn", "Name required", "Give the item a name.");
    return;
  }
  const result = await apiRequest("mitrabooks", "/api/v1/business/inventory/items", {
    method: "POST", body: JSON.stringify(body),
  });
  if (result.ok) {
    setLoginStatus("ok", "Item created", `${result.payload?.code} — ${result.payload?.name}`);
    await loadInventoryItems();
    await loadStockRegister();
  } else {
    setLoginStatus("danger", "Create failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { item_create: { ok: result.ok, status: result.status } });
}

export async function deactivateInventoryItem(itemId) {
  const result = await apiRequest("mitrabooks", `/api/v1/business/inventory/items/${encodeURIComponent(itemId)}/deactivate`, { method: "PATCH" });
  if (result.ok) {
    setLoginStatus("ok", "Item deactivated", "Existing documents keep the tag.");
    await loadInventoryItems();
    await loadStockRegister();
  } else {
    setLoginStatus("danger", "Deactivate failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { item_deactivate: { ok: result.ok, status: result.status } });
}

export async function loadInventoryPolicy() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/inventory/policy", { method: "GET" });
  lastInventoryPolicy = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { inventory_policy: { ok: result.ok, policy: result.payload?.valuation_policy || null } });
}

export async function loadStockMovements() {
  const asOf = document.querySelector("[data-stock-asof]")?.value || "";
  const params = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  const result = await apiRequest("mitrabooks", `/api/v1/business/inventory/movements${params}`, { method: "GET" });
  lastStockMovements = result.ok ? (result.payload?.items || []) : [];
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { stock_movements: { ok: result.ok, count: lastStockMovements.length } });
}

export async function createStockMovementFromForm() {
  const form = document.querySelector("[data-stock-movement-form]");
  if (!form) return;
  const val = (sel) => form.querySelector(sel)?.value ?? "";
  const body = {
    movement_type: val("select[name='movement_type']") || "issue",
    item_id: val("select[name='item_id']"),
    movement_date: val("input[name='movement_date']") || todayIsoDate(),
    quantity: val("input[name='quantity']") || "0",
    value: val("input[name='value']") || "0",
    reason: val("input[name='reason']") || null,
    reference: val("input[name='reference']") || null,
  };
  if (!body.item_id) {
    setLoginStatus("warn", "Item required", "Select the stock item for this movement.");
    return;
  }
  const result = await apiRequest("mitrabooks", "/api/v1/business/inventory/movements", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (result.ok) {
    setLoginStatus("ok", "Stock movement recorded", `${result.payload?.movement_type || "Movement"} for ${result.payload?.item_code || "item"}.`);
    await loadStockMovements();
    await loadStockRegister();
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can record stock issues and adjustments.");
  } else {
    setLoginStatus("danger", "Movement failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { stock_movement_create: { ok: result.ok, status: result.status } });
}

export async function loadStockRegister() {
  const asOf = document.querySelector("[data-stock-asof]")?.value || "";
  const params = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  const result = await apiRequest("mitrabooks", `/api/v1/business/inventory/stock-register${params}`, { method: "GET" });
  lastStockRegister = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { stock_register: { ok: result.ok } });
}

export async function loadClosingStockEntries() {
  const result = await apiRequest("mitrabooks", "/api/v1/business/inventory/closing-stock/entries", { method: "GET" });
  lastClosingStockEntries = result.ok ? (result.payload?.items || []) : [];
  rerenderBusinessReportsIfActive();
}

export async function postClosingStock() {
  const r = lastStockRegister;
  if (!r || r.ok === false) { setLoginStatus("warn", "Load the register first", "Load the stock register before posting."); return; }
  const result = await apiRequest("mitrabooks", "/api/v1/business/inventory/closing-stock", {
    method: "POST",
    headers: { "X-Idempotency-Key": `closing-stock-${r.as_of}` },
    body: JSON.stringify({ as_of: r.as_of }),
  });
  if (result.ok) {
    setLoginStatus("ok", "Closing stock posted", `${formatCurrency(Number(result.payload?.closing_stock_value || 0))} — journal entry #${result.payload?.journal_entry_id}.`);
    await loadClosingStockEntries();
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can post the closing stock.");
  } else {
    setLoginStatus("danger", "Posting failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { closing_stock_post: { ok: result.ok, status: result.status } });
}

export function renderInventoryPanel() {
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const inv = lastInventoryItems;
  if (!inv) return `<p class="muted">Loading inventory...</p>`;
  if (!inv.inventory_enabled) {
    return `
      <div class="table-preview compact-table">
        <h4>Inventory accounting is OFF for this business</h4>
        <p class="muted">This business is set up without stock keeping — purchases stay pure expense and no inventory entries are ever posted. That is the right setting for service businesses.</p>
        <p class="muted">To enable it: <strong>Sales → Invoice Settings → Inventory accounting</strong> (tenant admin). The item master, stock register and closing-stock journal will then appear here.</p>
      </div>`;
  }

  const itemRows = (inv.items || []).map((it) => `
    <tr>
      <td>${escapeHtml(it.code || "")}</td>
      <td>${escapeHtml(it.name || "")}</td>
      <td>${escapeHtml(it.uqc || "")}</td>
      <td>${escapeHtml(it.hsn_sac || "")}</td>
      <td class="amount">${escapeHtml(it.opening_qty || "0")}</td>
      <td class="amount">${num(it.opening_value)}</td>
      <td><button class="secondary" type="button" data-business-action="item-deactivate" data-item-id="${escapeHtml(it.item_id)}">Deactivate</button></td>
    </tr>`).join("");

  const manage = `
    <div class="invoice-form-grid" data-item-form>
      <label>Code <input type="text" name="item_code" maxlength="20" placeholder="e.g. WIDGET-A" style="text-transform:uppercase;"></label>
      <label>Name <input type="text" name="item_name" maxlength="160" placeholder="Item name"></label>
      <label>UQC <input type="text" name="item_uqc" maxlength="10" value="NOS" style="text-transform:uppercase;"></label>
      <label>HSN/SAC <input type="text" name="item_hsn" maxlength="8" placeholder="4-8 digits"></label>
      <label>GST % <input type="number" name="item_gst" min="0" max="100" step="any" placeholder="18"></label>
      <label>Opening qty <input type="number" name="item_open_qty" min="0" step="any" value="0"></label>
      <label>Opening value <input type="number" name="item_open_val" min="0" step="0.01" value="0"></label>
    </div>
    <div class="report-date-controls">
      <button class="primary" type="button" data-business-action="item-create">Add item</button>
    </div>
    <div class="table-preview compact-table">
      <table>
        <thead><tr><th>Code</th><th>Name</th><th>UQC</th><th>HSN</th><th class="amount">Opening qty</th><th class="amount">Opening value</th><th></th></tr></thead>
        <tbody>${itemRows || `<tr><td colspan="7" class="muted">No items yet — add your stock items above, then tag them on invoice and bill lines.</td></tr>`}</tbody>
      </table>
    </div>`;

  const policy = lastInventoryPolicy;
  const policyPanel = policy ? `
    <div class="table-preview compact-table">
      <h4>Valuation policy</h4>
      <p class="muted"><strong>${escapeHtml(policy.display_name || "Weighted average (periodic)")}</strong>${policy.policy_locked ? " - locked for this local gate" : ""}</p>
      ${(policy.notes || []).map((note) => `<p class="muted">${escapeHtml(note)}</p>`).join("")}
    </div>` : "";

  const movementRows = (lastStockMovements || []).slice(0, 8).map((mv) => `
    <tr>
      <td>${escapeHtml(mv.movement_date || "")}</td>
      <td>${escapeHtml(mv.movement_type || "")}</td>
      <td>${escapeHtml(`${mv.item_code || ""} - ${mv.item_name || mv.item_id || ""}`)}</td>
      <td class="amount">${escapeHtml(mv.quantity || "0")}</td>
      <td class="amount">${num(mv.value)}</td>
      <td>${escapeHtml(mv.reason || mv.reference || "")}</td>
    </tr>`).join("");
  const movementPanel = `
    <div class="table-preview compact-table"><h4>Stock issues &amp; adjustments</h4></div>
    <div class="invoice-form-grid" data-stock-movement-form>
      <label>Type
        <select name="movement_type">
          <option value="issue">Stock issue / consumption</option>
          <option value="adjustment">Stock adjustment</option>
        </select>
      </label>
      <label>Item <select name="item_id">${inventoryMovementItemOptions()}</select></label>
      <label>Date <input type="date" name="movement_date" value="${todayIsoDate()}"></label>
      <label>Qty <input type="number" name="quantity" step="any" placeholder="Issue positive; adjustment can be negative"></label>
      <label>Value <input type="number" name="value" step="0.01" placeholder="Positive adjustment value only"></label>
      <label>Reason <input type="text" name="reason" maxlength="160" placeholder="Consumption, count correction"></label>
      <label>Reference <input type="text" name="reference" maxlength="80" placeholder="Optional reference"></label>
    </div>
    <div class="report-date-controls">
      <button class="primary" type="button" data-business-action="stock-movement-create">Record movement</button>
    </div>
    <div class="table-preview compact-table">
      <table>
        <thead><tr><th>Date</th><th>Type</th><th>Item</th><th class="amount">Qty</th><th class="amount">Value</th><th>Reason / ref</th></tr></thead>
        <tbody>${movementRows || `<tr><td colspan="6" class="muted">No stock issues or adjustments recorded yet.</td></tr>`}</tbody>
      </table>
    </div>`;

  const r = lastStockRegister;
  let registerBody = "";
  if (r && r.ok === false) {
    registerBody = reportUnavailablePanel("Stock register", r);
  } else if (r) {
    const rows = (r.rows || []).map((row) => `
      <tr ${row.negative_stock ? 'style="background:#fff5f5;"' : ""}>
        <td>${escapeHtml(`${row.code} - ${row.name}`)}${row.negative_stock ? ` <span class="pill warn">negative</span>` : ""}</td>
        <td>${escapeHtml(row.uqc || "")}</td>
        <td class="amount">${escapeHtml(row.opening_qty)}</td>
        <td class="amount">${escapeHtml(row.purchased_qty)}</td>
        <td class="amount">${escapeHtml(row.adjustment_in_qty || "0.000")}</td>
        <td class="amount">${escapeHtml(row.sold_qty)}</td>
        <td class="amount">${escapeHtml(row.adjustment_out_qty || "0.000")}</td>
        <td class="amount">${escapeHtml(row.closing_qty)}</td>
        <td class="amount">${num(row.avg_cost)}</td>
        <td class="amount">${num(row.closing_value)}</td>
      </tr>`).join("");
    const lastEntry = (lastClosingStockEntries || [])[0];
    registerBody = `
      <div class="preview-heading compact">
        <div><p>Stock as of ${escapeHtml(r.as_of)} · ${escapeHtml(String(r.item_count))} item(s)${Number(r.untracked_purchase_value || 0) > 0 ? ` · untracked purchases ${num(r.untracked_purchase_value)}` : ""}.</p></div>
        <span class="pill ${r.negative_stock_items ? "warn" : "ok"}">${r.negative_stock_items ? `${escapeHtml(String(r.negative_stock_items))} negative` : `closing ${num(r.total_closing_value)}`}</span>
      </div>
      <div class="table-preview compact-table">
        <table>
          <thead><tr><th>Item</th><th>UQC</th><th class="amount">Opening</th><th class="amount">Purchased</th><th class="amount">Adj in</th><th class="amount">Sold</th><th class="amount">Issued/adj out</th><th class="amount">Closing</th><th class="amount">Avg cost</th><th class="amount">Value</th></tr></thead>
          <tbody>${rows || `<tr><td colspan="10" class="muted">No items to report.</td></tr>`}</tbody>
          ${rows ? `<tfoot><tr><th colspan="9">Total closing stock</th><td class="amount"><strong>${num(r.total_closing_value)}</strong></td></tr></tfoot>` : ""}
        </table>
      </div>
      ${lastEntry ? `<p class="muted">Last closing-stock journal: entry #${escapeHtml(String(lastEntry.journal_entry_id))} dated ${escapeHtml(lastEntry.entry_date)}. Reverse it before posting a new position.</p>` : ""}
      ${Number(r.total_closing_value || 0) > 0 && !r.negative_stock_items && !lastEntry && isBusinessAdmin() ? `
      <div class="report-date-controls">
        <button class="primary" type="button" data-business-action="closing-stock-post">Post closing stock (Dr 13001 / Cr 51002)</button>
      </div>` : ""}
      ${(r.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}`;
  }

  return `
    <div class="table-preview compact-table"><h4>Item master</h4></div>
    ${policyPanel}
    ${manage}
    <hr style="margin:18px 0;border:none;border-top:1px solid var(--line,#ddd);">
    ${movementPanel}
    <hr style="margin:18px 0;border:none;border-top:1px solid var(--line,#ddd);">
    <div class="table-preview compact-table"><h4>Stock register &amp; closing stock</h4></div>
    <div class="report-date-controls">
      <label>As of <input type="date" data-stock-asof value="${escapeHtml(r?.as_of || "")}"></label>
      <button class="secondary" type="button" data-business-action="stock-register-load">Load register</button>
    </div>
    ${registerBody || `<p class="muted">Loading stock register...</p>`}
  `;
}

// ---- Customer/vendor statements + dunning (Phase D) ----------------------- //

// ══════════════════════════════════════════════════════════════════════
