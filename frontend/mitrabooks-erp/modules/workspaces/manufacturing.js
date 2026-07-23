// ====================================================================
// SECTION: MANUFACTURING & COST-CENTRE ADD-ON
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initManufacturing(...).
// ====================================================================

import { apiRequest } from "../../../shared/api-client.js";

export let mfgAccess = null;
export let mfgTab = "cost-centres";
export let mfgError = "";
export let mfgCostCentres = [];
export let mfgTree = [];
export let mfgBudgets = [];
export let mfgBudgetVsActual = null;
export let mfgBoms = [];
export let mfgWorkOrders = [];
export let mfgItems = [];
export let mfgPl = null;
export let mfgPlFrom = "";
export let mfgPlTo = "";
export let mfgBomDraft = [];
export let mfgWoActualDraft = [];
export let mfgCompleteFor = "";

/** @type {Record<string, Function> | null} */
let deps = null;

export function initManufacturing(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initManufacturing() must be called before using manufacturing helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function getLastBusinessAccounts() { return requireDeps().getLastBusinessAccounts(); }
function refreshMfgView() { return requireDeps().refreshMfgView(); }

export function setMfgTab(value) { mfgTab = value; }
export function setMfgError(value) { mfgError = value; }
export function setMfgBudgetVsActual(value) { mfgBudgetVsActual = value; }
export function setMfgCompleteFor(value) { mfgCompleteFor = value; }
export function setMfgPlFrom(value) { mfgPlFrom = value; }
export function setMfgPlTo(value) { mfgPlTo = value; }
export function setMfgWoActualDraft(value) { mfgWoActualDraft = value; }

// ══════════════════════════════════════════════════════════════════════
// MANUFACTURING & COST-CENTRE ADD-ON (enterprise, opt-in)
// Backend /api/v1/business/mfg/*. Menu always shows; content gates on
// GET /business/mfg/access (platform provisioning + tenant enable + role).
// Two independent layers: Cost-Centre Accounting and Manufacturing.
// ══════════════════════════════════════════════════════════════════════

let mfgAccess = null;            // GET /business/mfg/access
let mfgTab = "cost-centres";     // cost-centres | budgets | pl | boms | work-orders
let mfgError = "";
let mfgCostCentres = [];         // from /business/dimensions (cost_centres)
let mfgTree = [];                // hierarchy roots
let mfgBudgets = [];
let mfgBudgetVsActual = null;    // {budget_id, report}
let mfgBoms = [];
let mfgWorkOrders = [];
let mfgItems = [];               // inventory items for selects
let mfgPl = null;                // cost-centre P&L report
let mfgPlFrom = "";
let mfgPlTo = "";
let mfgBomDraft = [];            // [{item_id, qty, rate, scrap_pct}] while building a BOM
let mfgWoActualDraft = [];       // [{item_id, qty, rate}] while completing a work order
let mfgCompleteFor = "";         // wo_id being completed

export function mfgMoney(value) {
  const n = Number(value || 0);
  return "₹" + n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function mfgCanManage() {
  return !!(mfgAccess && mfgAccess.can_manage_cost_centre);
}

export function mfgCanManageMfg() {
  return !!(mfgAccess && mfgAccess.can_manage_manufacturing);
}

export async function loadMfgWorkspace() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/mfg/access", { method: "GET" });
  mfgAccess = res.ok ? res.payload : { cost_centre_active: false, cost_centre_available: false, error: res.payload?.detail };
  refreshMfgView();
  if (mfgAccess && mfgAccess.cost_centre_active) {
    loadMfgCostCentres();
    loadMfgTree();
    loadMfgBudgets();
    loadMfgItems();
    if (mfgAccess.manufacturing_active) {
      loadMfgBoms();
      loadMfgWorkOrders();
    }
  }
}

export async function loadMfgCostCentres() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/dimensions", { method: "GET" });
  mfgCostCentres = res.ok && Array.isArray(res.payload?.cost_centres) ? res.payload.cost_centres : [];
  refreshMfgView();
}

export async function loadMfgTree() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/mfg/cost-centre/tree", { method: "GET" });
  mfgTree = res.ok && Array.isArray(res.payload?.roots) ? res.payload.roots : [];
  refreshMfgView();
}

export async function loadMfgBudgets() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/mfg/cost-centre/budgets", { method: "GET" });
  mfgBudgets = res.ok && Array.isArray(res.payload?.items) ? res.payload.items : [];
  refreshMfgView();
}

export async function loadMfgItems() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/inventory/items", { method: "GET" });
  mfgItems = res.ok && Array.isArray(res.payload?.items) ? res.payload.items : [];
  refreshMfgView();
}

export async function loadMfgBoms() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/mfg/boms", { method: "GET" });
  mfgBoms = res.ok && Array.isArray(res.payload?.items) ? res.payload.items : [];
  refreshMfgView();
}

export async function loadMfgWorkOrders() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/mfg/work-orders", { method: "GET" });
  mfgWorkOrders = res.ok && Array.isArray(res.payload?.items) ? res.payload.items : [];
  refreshMfgView();
}

export async function loadMfgPl() {
  const qs = [];
  if (mfgPlFrom) qs.push("from_date=" + encodeURIComponent(mfgPlFrom));
  if (mfgPlTo) qs.push("to_date=" + encodeURIComponent(mfgPlTo));
  const res = await apiRequest("mitrabooks", "/api/v1/business/mfg/cost-centre/pl" + (qs.length ? "?" + qs.join("&") : ""), { method: "GET" });
  mfgPl = res.ok ? res.payload : null;
  mfgError = res.ok ? "" : (res.payload?.detail || "Could not load cost-centre P&L.");
  refreshMfgView();
}

// ---- enable toggles ----
export async function mfgEnableLayer(layer) {
  const path = layer === "manufacturing" ? "/manufacturing/enabled" : "/cost-centre/enabled";
  const res = await apiRequest("mitrabooks", "/api/v1/business/mfg" + path, {
    method: "PUT", body: JSON.stringify({ enabled: true }),
  });
  mfgError = res.ok ? "" : (res.payload?.detail || "Could not enable the module.");
  loadMfgWorkspace();
}

// ---- cost centres ----
export async function mfgCreateCostCentre() {
  const code = (document.getElementById("mfg-cc-code")?.value || "").trim();
  const name = (document.getElementById("mfg-cc-name")?.value || "").trim();
  const parent = (document.getElementById("mfg-cc-parent")?.value || "").trim();
  if (!name) { mfgError = "Cost centre needs a name."; refreshMfgView(); return; }
  const body = { dimension_type: "cost_centre", code, name };
  if (parent) body.parent_code = parent;
  const res = await apiRequest("mitrabooks", "/api/v1/business/dimensions", {
    method: "POST", body: JSON.stringify(body),
  });
  mfgError = res.ok ? "" : (res.payload?.detail || "Could not create cost centre.");
  await loadMfgCostCentres();
  await loadMfgTree();
}

// ---- budgets ----
export async function mfgCreateBudget() {
  const ccId = document.getElementById("mfg-bud-cc")?.value || "";
  const year = parseInt(document.getElementById("mfg-bud-year")?.value, 10);
  const monthRaw = document.getElementById("mfg-bud-month")?.value || "";
  const accountId = parseInt(document.getElementById("mfg-bud-account")?.value, 10);
  const amount = document.getElementById("mfg-bud-amount")?.value || "";
  if (!ccId || !year || !accountId || !amount) { mfgError = "Pick cost centre, year, account and amount."; refreshMfgView(); return; }
  const body = {
    cost_centre_id: ccId, fiscal_year: year,
    fiscal_month: monthRaw ? parseInt(monthRaw, 10) : null,
    lines: [{ account_id: accountId, allocated_amount: amount }],
  };
  const res = await apiRequest("mitrabooks", "/api/v1/business/mfg/cost-centre/budgets", {
    method: "POST", body: JSON.stringify(body),
  });
  mfgError = res.ok ? "" : (res.payload?.detail || "Could not create budget.");
  await loadMfgBudgets();
}

export async function mfgSetBudgetStatus(button) {
  const id = button.getAttribute("data-budget-id") || "";
  const status = button.getAttribute("data-status") || "";
  if (!id || !status) return;
  const res = await apiRequest("mitrabooks", `/api/v1/business/mfg/cost-centre/budgets/${encodeURIComponent(id)}/status`, {
    method: "PUT", body: JSON.stringify({ status }),
  });
  mfgError = res.ok ? "" : (res.payload?.detail || "Could not update budget status.");
  await loadMfgBudgets();
}

export async function mfgViewBudgetVsActual(button) {
  const id = button.getAttribute("data-budget-id") || "";
  if (!id) return;
  const res = await apiRequest("mitrabooks", `/api/v1/business/mfg/cost-centre/budgets/${encodeURIComponent(id)}/vs-actual`, { method: "GET" });
  mfgBudgetVsActual = res.ok ? res.payload : null;
  mfgError = res.ok ? "" : (res.payload?.detail || "Could not load budget vs actual.");
  refreshMfgView();
}

// ---- BOMs ----
export function mfgAddBomComponent() {
  const itemId = document.getElementById("mfg-bom-comp-item")?.value || "";
  const qty = document.getElementById("mfg-bom-comp-qty")?.value || "";
  const rate = document.getElementById("mfg-bom-comp-rate")?.value || "";
  const scrap = document.getElementById("mfg-bom-comp-scrap")?.value || "0";
  if (!itemId || !qty) { mfgError = "Component needs an item and quantity."; refreshMfgView(); return; }
  mfgBomDraft.push({ item_id: itemId, qty, rate: rate || "0", scrap_pct: scrap || "0" });
  mfgError = "";
  refreshMfgView();
}

export function mfgRemoveBomComponent(button) {
  const idx = parseInt(button.getAttribute("data-idx"), 10);
  if (!isNaN(idx)) mfgBomDraft.splice(idx, 1);
  refreshMfgView();
}

export async function mfgCreateBom() {
  const fgItemId = document.getElementById("mfg-bom-fg")?.value || "";
  const code = (document.getElementById("mfg-bom-code")?.value || "").trim();
  const outputQty = document.getElementById("mfg-bom-output")?.value || "1";
  if (!fgItemId) { mfgError = "Pick a finished good."; refreshMfgView(); return; }
  if (!mfgBomDraft.length) { mfgError = "Add at least one component."; refreshMfgView(); return; }
  const body = { fg_item_id: fgItemId, output_qty: outputQty, components: mfgBomDraft };
  if (code) body.code = code;
  const res = await apiRequest("mitrabooks", "/api/v1/business/mfg/boms", {
    method: "POST", body: JSON.stringify(body),
  });
  if (res.ok) { mfgBomDraft = []; mfgError = ""; }
  else { mfgError = res.payload?.detail || "Could not create BOM."; }
  await loadMfgBoms();
}

// ---- work orders ----
export async function mfgCreateWorkOrder() {
  const bomId = document.getElementById("mfg-wo-bom")?.value || "";
  const qty = document.getElementById("mfg-wo-qty")?.value || "";
  const ccId = document.getElementById("mfg-wo-cc")?.value || "";
  if (!bomId || !qty) { mfgError = "Pick a BOM and planned quantity."; refreshMfgView(); return; }
  const body = { bom_id: bomId, planned_qty: qty };
  if (ccId) body.cost_centre_id = ccId;
  const res = await apiRequest("mitrabooks", "/api/v1/business/mfg/work-orders", {
    method: "POST", body: JSON.stringify(body),
  });
  mfgError = res.ok ? "" : (res.payload?.detail || "Could not create work order.");
  await loadMfgWorkOrders();
}

export async function mfgSetWorkOrderStatus(button) {
  const id = button.getAttribute("data-wo-id") || "";
  const status = button.getAttribute("data-status") || "";
  if (!id || !status) return;
  const res = await apiRequest("mitrabooks", `/api/v1/business/mfg/work-orders/${encodeURIComponent(id)}/status`, {
    method: "PUT", body: JSON.stringify({ status }),
  });
  mfgError = res.ok ? "" : (res.payload?.detail || "Could not update work order.");
  await loadMfgWorkOrders();
}

export function mfgOpenComplete(button) {
  mfgCompleteFor = button.getAttribute("data-wo-id") || "";
  mfgWoActualDraft = [];
  mfgError = "";
  refreshMfgView();
}

export function mfgAddWoActual() {
  const itemId = document.getElementById("mfg-wo-act-item")?.value || "";
  const qty = document.getElementById("mfg-wo-act-qty")?.value || "";
  const rate = document.getElementById("mfg-wo-act-rate")?.value || "0";
  if (!itemId || !qty) { mfgError = "Actual line needs an item and quantity."; refreshMfgView(); return; }
  mfgWoActualDraft.push({ item_id: itemId, qty, rate: rate || "0" });
  mfgError = "";
  refreshMfgView();
}

export function mfgRemoveWoActual(button) {
  const idx = parseInt(button.getAttribute("data-idx"), 10);
  if (!isNaN(idx)) mfgWoActualDraft.splice(idx, 1);
  refreshMfgView();
}

export async function mfgCompleteWorkOrder() {
  const produced = document.getElementById("mfg-wo-produced")?.value || "";
  const overhead = document.getElementById("mfg-wo-overhead")?.value || "0";
  if (!mfgCompleteFor) return;
  if (!produced) { mfgError = "Enter produced quantity."; refreshMfgView(); return; }
  if (!mfgWoActualDraft.length) { mfgError = "Add actual material consumption."; refreshMfgView(); return; }
  const body = { produced_qty: produced, actual_overhead: overhead, actual_components: mfgWoActualDraft };
  const res = await apiRequest("mitrabooks", `/api/v1/business/mfg/work-orders/${encodeURIComponent(mfgCompleteFor)}/complete`, {
    method: "POST", body: JSON.stringify(body),
  });
  if (res.ok) { mfgCompleteFor = ""; mfgWoActualDraft = []; mfgError = ""; }
  else { mfgError = res.payload?.detail || "Could not complete work order."; }
  await loadMfgWorkOrders();
}

export function mfgItemName(itemId) {
  const it = mfgItems.find((i) => i.item_id === itemId);
  return it ? `${it.code} — ${it.name}` : itemId;
}

export function mfgItemOptions(selectedId) {
  return mfgItems.map((i) =>
    `<option value="${escapeHtml(i.item_id)}"${i.item_id === selectedId ? " selected" : ""}>${escapeHtml(i.code)} — ${escapeHtml(i.name)}</option>`
  ).join("");
}

export function mfgTabButton(key, label) {
  const active = mfgTab === key ? " active" : "";
  return `<button type="button" class="erp-tab${active}" data-business-action="mfg-tab" data-mfg-tab="${key}">${escapeHtml(label)}</button>`;
}

// ---- tab renderers ----
export function mfgRenderTreeNodes(nodes, depth) {
  return nodes.map((n) => `
    <div style="padding:4px 0 4px ${depth * 18}px;">
      <strong>${escapeHtml(n.code)}</strong> — ${escapeHtml(n.name)}${n.is_active === false ? ' <span class="muted">(inactive)</span>' : ""}
    </div>
    ${n.children && n.children.length ? mfgRenderTreeNodes(n.children, depth + 1) : ""}
  `).join("");
}

export function renderMfgCostCentresTab() {
  const createForm = mfgCanManage() ? `
    <div class="erp-inline-form" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;margin-bottom:14px;">
      <label>Code<input id="mfg-cc-code" placeholder="MFG-ASY-01" /></label>
      <label>Name<input id="mfg-cc-name" placeholder="Assembly Line 1" /></label>
      <label>Parent code<input id="mfg-cc-parent" placeholder="(optional)" /></label>
      <button class="primary" type="button" data-business-action="mfg-create-cc">+ Add Cost Centre</button>
    </div>` : "";
  const rows = mfgCostCentres.length
    ? mfgCostCentres.map((c) => `<tr><td>${escapeHtml(c.code)}</td><td>${escapeHtml(c.name)}</td><td>${escapeHtml(c.parent_code || "—")}</td><td>${c.is_active === false ? "Inactive" : "Active"}</td></tr>`).join("")
    : `<tr><td colspan="4" class="muted">No cost centres yet.</td></tr>`;
  const tree = mfgTree.length ? `
    <h5 style="margin-top:16px;">Hierarchy</h5>
    <div class="erp-tree">${mfgRenderTreeNodes(mfgTree, 0)}</div>` : "";
  return `
    ${createForm}
    <table class="erp-table"><thead><tr><th>Code</th><th>Name</th><th>Parent</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table>
    ${tree}`;
}

export function renderMfgBudgetsTab() {
  const ccOptions = mfgCostCentres.map((c) => `<option value="${escapeHtml(c.dimension_id)}">${escapeHtml(c.code)} — ${escapeHtml(c.name)}</option>`).join("");
  const acctOptions = (getLastBusinessAccounts() || []).map((a) => `<option value="${escapeHtml(a.id || a.account_id)}">${escapeHtml(a.code)} — ${escapeHtml(a.name)}</option>`).join("");
  const createForm = mfgCanManage() ? `
    <div class="erp-inline-form" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;margin-bottom:14px;">
      <label>Cost centre<select id="mfg-bud-cc">${ccOptions}</select></label>
      <label>Year<input id="mfg-bud-year" type="number" value="${new Date().getFullYear()}" style="width:90px;" /></label>
      <label>Month<select id="mfg-bud-month"><option value="">Annual</option>${[1,2,3,4,5,6,7,8,9,10,11,12].map((m) => `<option value="${m}">${m}</option>`).join("")}</select></label>
      <label>Account<select id="mfg-bud-account">${acctOptions}</select></label>
      <label>Amount<input id="mfg-bud-amount" type="number" placeholder="0.00" /></label>
      <button class="primary" type="button" data-business-action="mfg-create-budget">+ Add Budget</button>
    </div>` : "";
  const ccName = (id) => { const c = mfgCostCentres.find((x) => x.dimension_id === id); return c ? c.code : id; };
  const rows = mfgBudgets.length
    ? mfgBudgets.map((b) => {
        const actions = mfgCanManage()
          ? `${b.status === "DRAFT" ? `<button class="secondary" type="button" data-business-action="mfg-budget-status" data-budget-id="${escapeHtml(b.budget_id)}" data-status="APPROVED">Approve</button>` : ""}
             ${b.status === "APPROVED" ? `<button class="secondary" type="button" data-business-action="mfg-budget-status" data-budget-id="${escapeHtml(b.budget_id)}" data-status="LOCKED">Lock</button>` : ""}`
          : "";
        return `<tr>
          <td>${escapeHtml(ccName(b.cost_centre_id))}</td>
          <td>${escapeHtml(b.fiscal_year)}${b.fiscal_month ? "-" + escapeHtml(b.fiscal_month) : " (annual)"}</td>
          <td>${escapeHtml(b.status)}</td>
          <td>${(b.lines || []).length} line(s)</td>
          <td><button class="secondary" type="button" data-business-action="mfg-budget-vs-actual" data-budget-id="${escapeHtml(b.budget_id)}">Vs Actual</button> ${actions}</td>
        </tr>`;
      }).join("")
    : `<tr><td colspan="5" class="muted">No budgets yet.</td></tr>`;
  let vsActual = "";
  if (mfgBudgetVsActual) {
    const r = mfgBudgetVsActual;
    const vrows = (r.rows || []).map((x) => `<tr><td>${escapeHtml(x.code || "")}</td><td>${escapeHtml(x.name || "")}</td><td style="text-align:right;">${mfgMoney(x.allocated)}</td><td style="text-align:right;">${mfgMoney(x.actual)}</td><td style="text-align:right;">${mfgMoney(x.variance)}</td><td style="text-align:right;">${escapeHtml(x.burn_rate_pct)}%</td></tr>`).join("");
    vsActual = `
      <h5 style="margin-top:16px;">Budget vs Actual</h5>
      <table class="erp-table"><thead><tr><th>Account</th><th>Name</th><th style="text-align:right;">Allocated</th><th style="text-align:right;">Actual</th><th style="text-align:right;">Variance</th><th style="text-align:right;">Burn</th></tr></thead>
      <tbody>${vrows || `<tr><td colspan="6" class="muted">No data.</td></tr>`}</tbody>
      <tfoot><tr><td colspan="2"><strong>Total</strong></td><td style="text-align:right;"><strong>${mfgMoney(r.totals?.allocated)}</strong></td><td style="text-align:right;"><strong>${mfgMoney(r.totals?.actual)}</strong></td><td style="text-align:right;"><strong>${mfgMoney(r.totals?.variance)}</strong></td><td></td></tr></tfoot></table>`;
  }
  return `${createForm}
    <table class="erp-table"><thead><tr><th>Cost centre</th><th>Period</th><th>Status</th><th>Lines</th><th>Actions</th></tr></thead><tbody>${rows}</tbody></table>
    ${vsActual}`;
}

export function renderMfgPlTab() {
  const controls = `
    <div class="erp-inline-form" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;margin-bottom:14px;">
      <label>From<input id="mfg-pl-from" type="date" value="${escapeHtml(mfgPlFrom)}" /></label>
      <label>To<input id="mfg-pl-to" type="date" value="${escapeHtml(mfgPlTo)}" /></label>
      <button class="primary" type="button" data-business-action="mfg-pl-run">Run</button>
      <button class="secondary" type="button" data-business-action="mfg-pl-export" data-format="csv">Export CSV</button>
      <button class="secondary" type="button" data-business-action="mfg-pl-export" data-format="xlsx">Export Excel</button>
    </div>`;
  if (!mfgPl) return controls + `<p class="muted">Run the report to see cost-centre P&amp;L.</p>`;
  const rows = (mfgPl.rows || []).map((x) => `<tr><td>${escapeHtml(x.code)}</td><td>${escapeHtml(x.name)}</td><td style="text-align:right;">${mfgMoney(x.income)}</td><td style="text-align:right;">${mfgMoney(x.expense)}</td><td style="text-align:right;">${mfgMoney(x.net)}</td></tr>`).join("");
  const u = mfgPl.untagged || {};
  const t = mfgPl.totals || {};
  return controls + `
    <table class="erp-table"><thead><tr><th>Code</th><th>Cost centre</th><th style="text-align:right;">Income</th><th style="text-align:right;">Expense</th><th style="text-align:right;">Net</th></tr></thead>
    <tbody>${rows || `<tr><td colspan="5" class="muted">No tagged activity in this period.</td></tr>`}
    <tr><td></td><td>Untagged</td><td style="text-align:right;">${mfgMoney(u.income)}</td><td style="text-align:right;">${mfgMoney(u.expense)}</td><td style="text-align:right;">${mfgMoney(u.net)}</td></tr></tbody>
    <tfoot><tr><td colspan="2"><strong>Total</strong></td><td style="text-align:right;"><strong>${mfgMoney(t.income)}</strong></td><td style="text-align:right;"><strong>${mfgMoney(t.expense)}</strong></td><td style="text-align:right;"><strong>${mfgMoney(t.net)}</strong></td></tr></tfoot></table>`;
}

export function renderMfgBomsTab() {
  if (!mfgAccess || !mfgAccess.manufacturing_active) {
    return `<div class="module-state warn"><strong>Manufacturing layer is off</strong><span>Enable Manufacturing (it builds on Cost Centres) to define BOMs and work orders.</span></div>
      ${mfgAccess && mfgAccess.can_enable_manufacturing ? `<button class="primary" type="button" data-business-action="mfg-enable-manufacturing" style="margin-top:10px;">Enable Manufacturing</button>` : ""}`;
  }
  const draftRows = mfgBomDraft.map((c, i) => `<tr><td>${escapeHtml(mfgItemName(c.item_id))}</td><td>${escapeHtml(c.qty)}</td><td>${escapeHtml(c.rate)}</td><td>${escapeHtml(c.scrap_pct)}%</td><td><button class="secondary" type="button" data-business-action="mfg-bom-remove-comp" data-idx="${i}">✕</button></td></tr>`).join("");
  const createForm = mfgCanManageMfg() ? `
    <details style="margin-bottom:14px;"><summary><strong>+ New BOM</strong></summary>
      <div class="erp-inline-form" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;margin:10px 0;">
        <label>Finished good<select id="mfg-bom-fg">${mfgItemOptions("")}</select></label>
        <label>Code<input id="mfg-bom-code" placeholder="(auto)" /></label>
        <label>Output qty<input id="mfg-bom-output" type="number" value="1" style="width:90px;" /></label>
      </div>
      <div class="erp-inline-form" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;">
        <label>Component<select id="mfg-bom-comp-item">${mfgItemOptions("")}</select></label>
        <label>Qty<input id="mfg-bom-comp-qty" type="number" style="width:80px;" /></label>
        <label>Rate<input id="mfg-bom-comp-rate" type="number" style="width:90px;" /></label>
        <label>Scrap %<input id="mfg-bom-comp-scrap" type="number" value="0" style="width:70px;" /></label>
        <button class="secondary" type="button" data-business-action="mfg-bom-add-comp">Add line</button>
      </div>
      <table class="erp-table" style="margin-top:10px;"><thead><tr><th>Component</th><th>Qty</th><th>Rate</th><th>Scrap</th><th></th></tr></thead><tbody>${draftRows || `<tr><td colspan="5" class="muted">No components added.</td></tr>`}</tbody></table>
      <button class="primary" type="button" data-business-action="mfg-create-bom" style="margin-top:10px;">Save BOM</button>
    </details>` : "";
  const rows = mfgBoms.length
    ? mfgBoms.map((b) => `<tr><td>${escapeHtml(b.code)}</td><td>${escapeHtml(b.fg_item_name || b.fg_item_code || "")}</td><td>${escapeHtml(b.output_qty)}</td><td style="text-align:right;">${mfgMoney(b.standard_cost?.total_cost)}</td><td style="text-align:right;">${mfgMoney(b.standard_cost?.per_unit_cost)}</td></tr>`).join("")
    : `<tr><td colspan="5" class="muted">No BOMs yet.</td></tr>`;
  return `${createForm}
    <table class="erp-table"><thead><tr><th>BOM</th><th>Finished good</th><th>Output</th><th style="text-align:right;">Std cost</th><th style="text-align:right;">Per unit</th></tr></thead><tbody>${rows}</tbody></table>`;
}

export function renderMfgWorkOrdersTab() {
  if (!mfgAccess || !mfgAccess.manufacturing_active) {
    return `<div class="module-state warn"><strong>Manufacturing layer is off</strong><span>Enable Manufacturing to track work orders.</span></div>`;
  }
  const bomOptions = mfgBoms.map((b) => `<option value="${escapeHtml(b.bom_id)}">${escapeHtml(b.code)} — ${escapeHtml(b.fg_item_name || b.fg_item_code || "")}</option>`).join("");
  const ccOptions = `<option value="">(no cost centre)</option>` + mfgCostCentres.map((c) => `<option value="${escapeHtml(c.dimension_id)}">${escapeHtml(c.code)}</option>`).join("");
  const createForm = mfgCanManageMfg() ? `
    <div class="erp-inline-form" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;margin-bottom:14px;">
      <label>BOM<select id="mfg-wo-bom">${bomOptions}</select></label>
      <label>Planned qty<input id="mfg-wo-qty" type="number" style="width:100px;" /></label>
      <label>Cost centre<select id="mfg-wo-cc">${ccOptions}</select></label>
      <button class="primary" type="button" data-business-action="mfg-create-wo">+ Create Work Order</button>
    </div>` : "";
  const statusBtn = (wo, status, label) => `<button class="secondary" type="button" data-business-action="mfg-wo-status" data-wo-id="${escapeHtml(wo.wo_id)}" data-status="${status}">${label}</button>`;
  const rows = mfgWorkOrders.length
    ? mfgWorkOrders.map((wo) => {
        let actions = "";
        if (mfgCanManageMfg()) {
          if (wo.status === "draft") actions = statusBtn(wo, "released", "Release") + " " + statusBtn(wo, "cancelled", "Cancel");
          else if (wo.status === "released") actions = statusBtn(wo, "in_progress", "Start") + " " + `<button class="primary" type="button" data-business-action="mfg-wo-open-complete" data-wo-id="${escapeHtml(wo.wo_id)}">Complete</button>`;
          else if (wo.status === "in_progress") actions = `<button class="primary" type="button" data-business-action="mfg-wo-open-complete" data-wo-id="${escapeHtml(wo.wo_id)}">Complete</button>`;
        }
        const variance = wo.variance ? mfgMoney(wo.variance.variance) + (wo.variance.favourable ? " ✓" : "") : "—";
        return `<tr><td>${escapeHtml(wo.wo_number)}</td><td>${escapeHtml(wo.fg_item_name || wo.fg_item_code || "")}</td><td>${escapeHtml(wo.planned_qty)}</td><td>${escapeHtml(wo.status)}</td><td style="text-align:right;">${mfgMoney(wo.standard_cost?.total_cost)}</td><td style="text-align:right;">${variance}</td><td>${actions}</td></tr>`;
      }).join("")
    : `<tr><td colspan="7" class="muted">No work orders yet.</td></tr>`;
  let completeForm = "";
  if (mfgCompleteFor) {
    const draftRows = mfgWoActualDraft.map((c, i) => `<tr><td>${escapeHtml(mfgItemName(c.item_id))}</td><td>${escapeHtml(c.qty)}</td><td>${escapeHtml(c.rate)}</td><td><button class="secondary" type="button" data-business-action="mfg-wo-remove-actual" data-idx="${i}">✕</button></td></tr>`).join("");
    completeForm = `
      <div class="verification-panel" style="margin-top:14px;padding:14px;">
        <h5>Complete work order — actual consumption</h5>
        <div class="erp-inline-form" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;">
          <label>Produced qty<input id="mfg-wo-produced" type="number" style="width:100px;" /></label>
          <label>Actual overhead<input id="mfg-wo-overhead" type="number" value="0" style="width:110px;" /></label>
        </div>
        <div class="erp-inline-form" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;margin-top:8px;">
          <label>Material<select id="mfg-wo-act-item">${mfgItemOptions("")}</select></label>
          <label>Qty<input id="mfg-wo-act-qty" type="number" style="width:80px;" /></label>
          <label>Rate<input id="mfg-wo-act-rate" type="number" style="width:90px;" /></label>
          <button class="secondary" type="button" data-business-action="mfg-wo-add-actual">Add line</button>
        </div>
        <table class="erp-table" style="margin-top:8px;"><thead><tr><th>Material</th><th>Qty</th><th>Rate</th><th></th></tr></thead><tbody>${draftRows || `<tr><td colspan="4" class="muted">No actuals added.</td></tr>`}</tbody></table>
        <button class="primary" type="button" data-business-action="mfg-wo-complete" style="margin-top:10px;">Confirm Completion</button>
        <button class="secondary" type="button" data-business-action="mfg-wo-complete-cancel" style="margin-top:10px;">Cancel</button>
      </div>`;
  }
  return `${createForm}
    <table class="erp-table"><thead><tr><th>WO</th><th>Finished good</th><th>Qty</th><th>Status</th><th style="text-align:right;">Std cost</th><th style="text-align:right;">Variance</th><th>Actions</th></tr></thead><tbody>${rows}</tbody></table>
    ${completeForm}`;
}

export function renderMfgTab() {
  if (mfgTab === "budgets") return renderMfgBudgetsTab();
  if (mfgTab === "pl") return renderMfgPlTab();
  if (mfgTab === "boms") return renderMfgBomsTab();
  if (mfgTab === "work-orders") return renderMfgWorkOrdersTab();
  return renderMfgCostCentresTab();
}

export function renderManufacturingWorkspace() {
  let body;
  if (!mfgAccess) {
    body = `<p class="muted">Loading manufacturing workspace…</p>`;
  } else if (!mfgAccess.cost_centre_active) {
    if (mfgAccess.cost_centre_available === false) {
      body = `<div class="module-state warn"><strong>Manufacturing &amp; Cost Centres is not active</strong><span>This enterprise add-on has not been provisioned for your organization. Contact your platform administrator to enable it.</span></div>`;
    } else if (mfgAccess.can_enable_cost_centre) {
      body = `
        <div class="module-state warn">
          <strong>Cost-Centre Accounting is provisioned but turned off</strong>
          <span>Enable it to tag postings to cost centres and run departmental P&amp;L and budgets.</span>
        </div>
        <button class="primary" type="button" data-business-action="mfg-enable-cost-centre" style="margin-top:10px;">Enable Cost Centres</button>`;
    } else {
      body = `<div class="module-state warn"><strong>Manufacturing &amp; Cost Centres is turned off</strong><span>Ask an administrator to enable it in MitraBooks.</span></div>`;
    }
  } else {
    body = `
      ${mfgError ? `<div class="module-state danger"><span>${escapeHtml(mfgError)}</span></div>` : ""}
      <div class="erp-tabs" style="display:flex;gap:6px;margin-bottom:14px;flex-wrap:wrap;">
        ${mfgTabButton("cost-centres", "Cost Centres")}
        ${mfgTabButton("budgets", "Budgets")}
        ${mfgTabButton("pl", "Cost-Centre P&L")}
        ${mfgTabButton("boms", "BOMs")}
        ${mfgTabButton("work-orders", "Work Orders")}
      </div>
      <div class="erp-tab-content">${renderMfgTab()}</div>`;
  }
  return `
    <div class="verification-panel erp-workspace-panel">
      <div class="preview-heading compact">
        <div><h4>Manufacturing &amp; Cost Centres</h4><p>Cost-centre accounting, budgets, BOMs and work orders.</p></div>
        <button class="secondary" type="button" data-business-action="mfg-refresh">Refresh</button>
      </div>
      ${body}
    </div>`;
}

