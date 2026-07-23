// ====================================================================
// SECTION: PAYMENT ALLOCATION + AR/AP AGING
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initPaymentAllocation(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastBusinessAging = null;

/** Payment Allocation workflow state (open-item AR/AP matching). */
export const allocationState = {
  kind: "receivable",
  selectedPaymentId: "",
  lines: {},        // open_item_id -> entered amount (string)
  busy: false,
};
export let lastUnallocatedPayments = null;
export let lastAllocationOpenItems = null;
export let lastAllocationReconciliation = null;
export let lastAllocationResult = null;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initPaymentAllocation(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initPaymentAllocation() must be called before using payment-allocation helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function reportUnavailablePanel(title, payload) { return requireDeps().reportUnavailablePanel(title, payload); }
function rerenderBusinessReportsIfActive() { return requireDeps().rerenderBusinessReportsIfActive(); }
function reportResultPayload(result, extra = {}) { return requireDeps().reportResultPayload(result, extra); }
function getBusinessReportState() { return requireDeps().getBusinessReportState(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

// ---- AR/AP Aging (Phase B backend) -------------------------------------- //

// ══════════════════════════════════════════════════════════════════════
// SECTION: PAYMENT ALLOCATION + AR/AP AGING
// API   : GET /api/v1/business/aging  POST /api/v1/business/allocation
// NOTE  : loadBusinessAging, setAllocationKind, applyFifoSuggestion, submitAllocation
// ══════════════════════════════════════════════════════════════════════

export async function loadBusinessAging() {
  const kind = getBusinessReportState().agingKind === "payable" ? "payable" : "receivable";
  const asOf = encodeURIComponent(getBusinessReportState().as_of);
  const result = await apiRequest("mitrabooks", `/api/v1/business/allocations/aging?kind=${kind}&as_of=${asOf}`, { method: "GET" });
  lastBusinessAging = reportResultPayload(result, { kind });
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { aging: { ok: result.ok, kind } });
}

export function setAgingKind(kind) {
  getBusinessReportState().agingKind = kind === "payable" ? "payable" : "receivable";
  rerenderBusinessReportsIfActive();
  loadBusinessAging();
}

// ---- Payment Allocation (Phase A backend) ------------------------------- //
export async function loadUnallocatedPayments() {
  const kind = allocationState.kind === "payable" ? "payable" : "receivable";
  const result = await apiRequest("mitrabooks", `/api/v1/business/allocations/unallocated-payments?kind=${kind}`, { method: "GET" });
  lastUnallocatedPayments = reportResultPayload(result, { kind });
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { unallocated_payments: { ok: result.ok, kind } });
}

export function setAllocationKind(kind) {
  allocationState.kind = kind === "payable" ? "payable" : "receivable";
  allocationState.selectedPaymentId = "";
  allocationState.lines = {};
  lastAllocationOpenItems = null;
  lastAllocationReconciliation = null;
  lastAllocationResult = null;
  rerenderBusinessReportsIfActive();
  loadUnallocatedPayments();
}

export async function selectAllocationPayment(paymentId) {
  allocationState.selectedPaymentId = String(paymentId || "");
  allocationState.lines = {};
  lastAllocationResult = null;
  if (!allocationState.selectedPaymentId) {
    lastAllocationOpenItems = null;
    rerenderBusinessReportsIfActive();
    return;
  }
  const kind = allocationState.kind === "payable" ? "payable" : "receivable";
  const asOf = encodeURIComponent(getBusinessReportState().as_of);
  lastAllocationOpenItems = { loading: true };
  rerenderBusinessReportsIfActive();
  // Open items to match against, plus a FIFO suggestion to pre-fill amounts.
  const [openResult, fifoResult] = await Promise.all([
    apiRequest("mitrabooks", `/api/v1/business/allocations/open-items?kind=${kind}&as_of=${asOf}`, { method: "GET" }),
    apiRequest("mitrabooks", `/api/v1/business/allocations/fifo-suggestion?kind=${kind}&payment_id=${encodeURIComponent(allocationState.selectedPaymentId)}&as_of=${asOf}`, { method: "GET" }),
  ]);
  lastAllocationOpenItems = reportResultPayload(openResult, { kind });
  if (fifoResult.ok && Array.isArray(fifoResult.payload?.allocations)) {
    for (const line of fifoResult.payload.allocations) {
      allocationState.lines[line.open_item_id] = String(line.allocated_amount);
    }
  }
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { open_items: { ok: openResult.ok }, fifo: { ok: fifoResult.ok } });
}

export function setAllocationLineAmount(openItemId, value) {
  if (!openItemId) return;
  const cleaned = String(value || "").trim();
  if (cleaned === "" || Number(cleaned) <= 0) {
    delete allocationState.lines[openItemId];
  } else {
    allocationState.lines[openItemId] = cleaned;
  }
}

export function applyFifoSuggestion() {
  // Re-fetch FIFO from current unallocated balance and overwrite the line inputs.
  selectAllocationPayment(allocationState.selectedPaymentId);
}

export async function submitAllocation() {
  const paymentId = allocationState.selectedPaymentId;
  if (!paymentId) {
    setLoginStatus("warn", "Select a payment", "Choose an unallocated payment first.");
    return;
  }
  const allocations = Object.entries(allocationState.lines)
    .map(([open_item_id, amount]) => ({ open_item_id, allocated_amount: Number(amount) }))
    .filter((a) => a.allocated_amount > 0);
  if (!allocations.length) {
    setLoginStatus("warn", "Nothing to allocate", "Enter at least one allocation amount.");
    return;
  }
  allocationState.busy = true;
  rerenderBusinessReportsIfActive();
  const result = await apiRequest("mitrabooks", "/api/v1/business/allocations", {
    method: "POST",
    body: JSON.stringify({ kind: allocationState.kind, payment_id: paymentId, allocations }),
  });
  allocationState.busy = false;
  if (result.ok) {
    lastAllocationResult = result.payload;
    setLoginStatus("ok", "Allocation posted", `Matched ${result.payload?.count || allocations.length} open item(s).`);
    allocationState.selectedPaymentId = "";
    allocationState.lines = {};
    lastAllocationOpenItems = null;
    await loadUnallocatedPayments();
    await loadAllocationReconciliation();
  } else {
    setLoginStatus("danger", "Allocation failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
    rerenderBusinessReportsIfActive();
  }
  renderJson(getApiOutput(), { allocation: { ok: result.ok, status: result.status } });
}

export async function loadAllocationReconciliation() {
  const kind = allocationState.kind === "payable" ? "payable" : "receivable";
  const asOf = encodeURIComponent(getBusinessReportState().as_of);
  const result = await apiRequest("mitrabooks", `/api/v1/business/allocations/reconciliation?kind=${kind}&as_of=${asOf}`, { method: "GET" });
  lastAllocationReconciliation = result.ok ? result.payload : null;
  rerenderBusinessReportsIfActive();
}

// Kind toggle (receivable/payable) reused by the Aging and Allocation screens.
export function kindToggle(activeKind, action) {
  const btn = (k, label) => `
    <button class="report-tab ${activeKind === k ? "active" : ""}" type="button"
      data-business-action="${action}" data-alloc-kind="${k}">${label}</button>`;
  return `<div class="report-tabs" role="tablist" style="margin:0 0 10px;">
    ${btn("receivable", "Receivable (Debtors)")}${btn("payable", "Payable (Creditors)")}
  </div>`;
}

export function renderBusinessAging() {
  const payload = lastBusinessAging;
  const toggle = kindToggle(getBusinessReportState().agingKind, "aging-kind");
  if (!payload) {
    return `${toggle}<p class="muted">Loading aging report...</p>`;
  }
  if (payload.ok === false) {
    return `${toggle}${reportUnavailablePanel("AR/AP Aging", payload)}`;
  }
  const order = Array.isArray(payload.buckets_order) ? payload.buckets_order : [];
  const rows = Array.isArray(payload.by_party) ? payload.by_party : [];
  const totals = payload.totals || {};
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const headCols = order.map((b) => `<th class="amount">${escapeHtml(b)}</th>`).join("");
  const totalCols = order.map((b) => `<td class="amount">${num(totals[b])}</td>`).join("");
  const bodyRows = rows.length ? rows.map((r) => {
    const buckets = r.buckets || {};
    const cells = order.map((b) => `<td class="amount">${num(buckets[b])}</td>`).join("");
    return `<tr>
      <td>${escapeHtml(r.party_name || "Unallocated")}</td>
      ${cells}
      <td class="amount"><strong>${num(r.total)}</strong></td>
    </tr>`;
  }).join("") : `<tr><td colspan="${order.length + 2}" class="muted">No outstanding ${escapeHtml(payload.kind || "")} balances.</td></tr>`;
  const label = (payload.kind === "payable") ? "Payables" : "Receivables";
  return `
    ${toggle}
    <div class="preview-heading compact">
      <div><p>${escapeHtml(label)} aging as of ${escapeHtml(payload.as_of || getBusinessReportState().as_of)}, by party and overdue bucket. Grand total ties to the matching control account.</p></div>
      <span class="pill">${num(payload.grand_total)}</span>
    </div>
    <div class="table-preview compact-table">
      <table>
        <thead><tr><th>Party</th>${headCols}<th class="amount">Total</th></tr></thead>
        <tbody>${bodyRows}</tbody>
        <tfoot><tr><th>Total</th>${totalCols}<td class="amount"><strong>${num(payload.grand_total)}</strong></td></tr></tfoot>
      </table>
    </div>
  `;
}

export function renderPaymentAllocation() {
  const toggle = kindToggle(allocationState.kind, "alloc-kind");
  const num = (v) => escapeHtml(formatCurrency(Number(v || 0)));
  const payments = lastUnallocatedPayments;
  const partyLabel = allocationState.kind === "payable" ? "Payments made (to vendors)" : "Receipts collected (from customers)";

  let paymentsBlock;
  if (!payments) {
    paymentsBlock = `<p class="muted">Loading unallocated payments...</p>`;
  } else if (payments.ok === false) {
    paymentsBlock = reportUnavailablePanel("Unallocated Payments", payments);
  } else {
    const items = Array.isArray(payments.items) ? payments.items : [];
    paymentsBlock = `
      <h4>Unallocated ${escapeHtml(allocationState.kind === "payable" ? "Payments" : "Receipts")}
        <span class="pill">${num(payments.total_unallocated)}</span></h4>
      <p class="muted">${escapeHtml(partyLabel)} with an unmatched balance. Pick one to allocate against open items.</p>
      <div class="table-preview compact-table">
        <table>
          <thead><tr><th>Number</th><th>Date</th><th class="amount">Amount</th><th class="amount">Unallocated</th><th></th></tr></thead>
          <tbody>
            ${items.length ? items.map((p) => `
              <tr class="${p.payment_id === allocationState.selectedPaymentId ? "active-row" : ""}">
                <td>${escapeHtml(p.payment_number || p.payment_id)}</td>
                <td>${escapeHtml(p.payment_date || "")}</td>
                <td class="amount">${num(p.amount)}</td>
                <td class="amount">${num(p.unallocated)}</td>
                <td><button class="secondary" type="button" data-business-action="alloc-select-payment" data-payment-id="${escapeHtml(p.payment_id)}">${p.payment_id === allocationState.selectedPaymentId ? "Selected" : "Allocate"}</button></td>
              </tr>
            `).join("") : `<tr><td colspan="5" class="muted">No unallocated payments. Everything is matched.</td></tr>`}
          </tbody>
        </table>
      </div>`;
  }

  let matchBlock = "";
  if (allocationState.selectedPaymentId) {
    const open = lastAllocationOpenItems;
    if (open && open.loading) {
      matchBlock = `<p class="muted">Loading open items...</p>`;
    } else if (open && open.ok === false) {
      matchBlock = reportUnavailablePanel("Open Items", open);
    } else if (open) {
      const items = Array.isArray(open.items) ? open.items : [];
      const entered = Object.entries(allocationState.lines)
        .reduce((sum, [, v]) => sum + (Number(v) || 0), 0);
      const rows = items.length ? items.map((it) => {
        const val = allocationState.lines[it.open_item_id] || "";
        const overdue = Number(it.days_overdue || 0) > 0;
        return `
          <tr>
            <td>${escapeHtml(it.open_item_number || it.open_item_id)}</td>
            <td>${escapeHtml(it.due_date || it.item_date || "")}${overdue ? ` <span class="pill warn">${escapeHtml(String(it.days_overdue))}d</span>` : ""}</td>
            <td class="amount">${num(it.total)}</td>
            <td class="amount">${num(it.outstanding)}</td>
            <td class="amount"><input type="number" step="0.01" min="0" max="${escapeHtml(String(it.outstanding))}" value="${escapeHtml(val)}" data-alloc-line="${escapeHtml(it.open_item_id)}" style="width:120px;text-align:right;"></td>
          </tr>`;
      }).join("") : `<tr><td colspan="5" class="muted">No open items to match for this party.</td></tr>`;
      matchBlock = `
        <h4>Match against open items</h4>
        <p class="muted">Amounts pre-filled oldest-first (FIFO). Adjust as needed, then allocate. Allocation records the match as metadata — it posts no new ledger entries.</p>
        <div class="table-preview compact-table">
          <table>
            <thead><tr><th>Item</th><th>Due</th><th class="amount">Total</th><th class="amount">Outstanding</th><th class="amount">Allocate</th></tr></thead>
            <tbody>${rows}</tbody>
            <tfoot><tr><th colspan="4">Total to allocate</th><td class="amount"><strong>${num(entered)}</strong></td></tr></tfoot>
          </table>
        </div>
        <div style="display:flex;gap:8px;margin-top:10px;">
          <button class="secondary" type="button" data-business-action="alloc-fifo">Re-apply FIFO</button>
          <button type="button" data-business-action="alloc-submit" ${allocationState.busy ? "disabled" : ""}>${allocationState.busy ? "Posting..." : "Post Allocation"}</button>
        </div>`;
    }
  } else {
    matchBlock = `<p class="muted">Select a payment above to begin matching.</p>`;
  }

  let reconBlock = "";
  const recon = lastAllocationReconciliation;
  if (recon) {
    reconBlock = `
      <div class="preview-heading compact" style="margin-top:14px;">
        <div><p>Reconciliation: open items ${num(recon.open_items_outstanding)} − unallocated ${num(recon.unallocated_payments)} = computed ${num(recon.computed_net)} vs ledger ${num(recon.ledger_balance)}.</p></div>
        <span class="pill ${recon.balanced ? "ok" : "warn"}">${recon.balanced ? "reconciled" : "off by " + num(recon.difference)}</span>
      </div>`;
  }

  return `
    ${toggle}
    ${paymentsBlock}
    <hr style="margin:16px 0;border:none;border-top:1px solid #e5e7eb;">
    ${matchBlock}
    ${reconBlock}
  `;
}
