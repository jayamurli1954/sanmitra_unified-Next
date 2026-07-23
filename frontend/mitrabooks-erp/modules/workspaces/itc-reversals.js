// ====================================================================
// SECTION: ITC REVERSALS (Rule 37 / Re-claim)
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initItcReversals(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastItcReversal = null;
export let lastItcReversedBills = [];
export let itcReversalAsOf = "";

/** @type {Record<string, Function> | null} */
let deps = null;

export function initItcReversals(injected) {
  deps = injected;
  if (!itcReversalAsOf) {
    itcReversalAsOf = deps.todayIsoDate();
  }
}

function requireDeps() {
  if (!deps) {
    throw new Error("initItcReversals() must be called before using ITC reversal helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function rerenderBusinessReportsIfActive() { return requireDeps().rerenderBusinessReportsIfActive(); }
function isBusinessAdmin() { return requireDeps().isBusinessAdmin(); }
function todayIsoDate() { return requireDeps().todayIsoDate(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

// ══════════════════════════════════════════════════════════════════════
// SECTION: ITC REVERSALS (Rule 37 / Re-claim)
// API   : GET /api/v1/business/itc/reversals  POST /api/v1/business/itc/reverse|reclaim
// NOTE  : loadItcReversalPreview, reverseItcForBill, reclaimItcForBill, renderItcReversalPanel
// ══════════════════════════════════════════════════════════════════════

export async function loadItcReversalPreview(asOf) {
  itcReversalAsOf = asOf || itcReversalAsOf;
  const result = await apiRequest("mitrabooks", `/api/v1/business/itc-reversals/preview?as_of=${encodeURIComponent(itcReversalAsOf)}`, { method: "GET" });
  lastItcReversal = result.ok ? result.payload : null;
  if (!result.ok) setLoginStatus("warn", "ITC preview unavailable", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  // Also load reversed-but-not-yet-reclaimed bills so the user can reclaim once paid.
  const bills = await apiRequest("mitrabooks", "/api/v1/business/bills?status=posted&limit=500", { method: "GET" });
  lastItcReversedBills = bills.ok && Array.isArray(bills.payload?.items)
    ? bills.payload.items.filter((b) => b.itc_reversed && !b.itc_reclaimed)
    : [];
  rerenderBusinessReportsIfActive();
  renderJson(getApiOutput(), { itc_reversal_preview: { ok: result.ok, as_of: itcReversalAsOf, count: lastItcReversal?.count ?? 0 } });
}

export function previewItcReversalsFromInput() {
  const input = document.querySelector("[data-itc-asof]");
  loadItcReversalPreview(input?.value || itcReversalAsOf);
}

export async function reverseItcForBill(billId) {
  if (!billId) return;
  const result = await apiRequest("mitrabooks", `/api/v1/business/bills/${encodeURIComponent(billId)}/itc-reversal`, {
    method: "POST",
    body: JSON.stringify({ reversal_date: itcReversalAsOf, accounting_entity_id: "primary" }),
  });
  if (result.ok) {
    setLoginStatus("ok", "ITC reversed", `Rule 37 reversal posted for bill ${result.payload?.bill_number || billId}.`);
    await loadItcReversalPreview(itcReversalAsOf);
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can reverse ITC.");
  } else {
    setLoginStatus("danger", "Reversal failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { itc_reversal: { ok: result.ok, status: result.status } });
}

export async function reclaimItcForBill(billId) {
  if (!billId) return;
  const result = await apiRequest("mitrabooks", `/api/v1/business/bills/${encodeURIComponent(billId)}/itc-reclaim`, {
    method: "POST",
    body: JSON.stringify({ reclaim_date: todayIsoDate(), accounting_entity_id: "primary" }),
  });
  if (result.ok) {
    setLoginStatus("ok", "ITC reclaimed", `Reversed ITC re-availed for bill ${result.payload?.bill_number || billId}.`);
    await loadItcReversalPreview(itcReversalAsOf);
  } else if (result.status === 403) {
    setLoginStatus("danger", "Admin only", "Only a tenant admin can reclaim ITC.");
  } else {
    setLoginStatus("danger", "Reclaim failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { itc_reclaim: { ok: result.ok, status: result.status } });
}

export async function markBillPaidFull(billId, amount) {
  if (!billId) return;
  const result = await apiRequest("mitrabooks", `/api/v1/business/bills/${encodeURIComponent(billId)}/payment`, {
    method: "POST",
    body: JSON.stringify({ paid_amount: String(amount || "0"), paid_date: todayIsoDate(), accounting_entity_id: "primary" }),
  });
  if (result.ok) {
    setLoginStatus("ok", "Payment recorded", `Bill ${result.payload?.bill_number || billId} marked paid.`);
    await loadItcReversalPreview(itcReversalAsOf);
  } else {
    setLoginStatus("danger", "Update failed", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { bill_payment: { ok: result.ok, status: result.status } });
}

export function renderItcReversalPanel() {
  const admin = isBusinessAdmin();
  const num = (v) => formatCurrency(Number(v || 0));
  const data = lastItcReversal;
  let flagged = `<p class="muted">No bills are overdue beyond 180 days as of this date.</p>`;
  if (data && Array.isArray(data.candidates) && data.candidates.length) {
    const rows = data.candidates.map((c) => `
      <tr>
        <td>${escapeHtml(c.bill_number || "")}</td>
        <td>${escapeHtml(c.vendor_name || c.vendor_party_id || "")}</td>
        <td>${escapeHtml(c.bill_date || "")}</td>
        <td>${escapeHtml(c.due_date || "")}</td>
        <td class="amount">${escapeHtml(String(c.days_overdue ?? ""))}</td>
        <td class="amount">${num(c.itc_total)}</td>
        <td class="amount">${num(c.interest_amount)}</td>
        <td><span class="pill warn">${escapeHtml(c.payment_status || "unpaid")}</span></td>
        <td>${escapeHtml(c.gstr3b_ref || "4(B)(2)")}</td>
        <td>
          <button class="secondary" type="button" data-business-action="bill-mark-paid" data-bill-id="${escapeHtml(c.bill_id || "")}" data-bill-amount="${escapeHtml(c.net_payable || c.bill_total || "0")}">Mark paid</button>
          ${admin ? `<button class="primary" type="button" data-business-action="itc-reverse" data-bill-id="${escapeHtml(c.bill_id || "")}">Reverse ITC</button>` : ""}
        </td>
      </tr>
    `).join("");
    flagged = `
      <div class="table-preview compact-table">
        <table>
          <thead>
            <tr><th>Bill #</th><th>Vendor</th><th>Bill date</th><th>Due (180d)</th><th class="amount">Days overdue</th><th class="amount">ITC</th><th class="amount">Interest @18%</th><th>Payment</th><th>GSTR-3B</th><th>Action</th></tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <div class="invoice-totals">
        <div><span>Total ITC to reverse</span><strong>${num(data.total_itc)}</strong></div>
        <div class="invoice-grand"><span>Total interest @18%</span><strong>${num(data.total_interest)}</strong></div>
      </div>
      <p class="muted reversal-scope-note">Reversal posts: Dr ITC Reversed (Recoverable), Cr Input GST; plus Dr Interest on GST, Cr Interest Payable. Crediting Input GST raises that month's net GST payable. Reported in GSTR-3B Table 4(B)(2).</p>
    `;
  }

  let reclaimable = "";
  if (Array.isArray(lastItcReversedBills) && lastItcReversedBills.length) {
    const rows = lastItcReversedBills.map((b) => {
      const paid = b.payment_status === "paid";
      return `
      <tr>
        <td>${escapeHtml(b.bill_number || "")}</td>
        <td>${escapeHtml(b.vendor_name || b.vendor_party_id || "")}</td>
        <td>${escapeHtml(b.itc_reversal_date || "")}</td>
        <td class="amount">${num(b.gst_total)}</td>
        <td class="amount">${num(b.itc_interest_amount)}</td>
        <td><span class="pill ${paid ? "ok" : "warn"}">${escapeHtml(b.payment_status || "unpaid")}</span></td>
        <td>
          ${paid
            ? (admin ? `<button class="primary" type="button" data-business-action="itc-reclaim" data-bill-id="${escapeHtml(b.bill_id || "")}">Reclaim ITC</button>` : `<span class="muted">admin only</span>`)
            : `<button class="secondary" type="button" data-business-action="bill-mark-paid" data-bill-id="${escapeHtml(b.bill_id || "")}" data-bill-amount="${escapeHtml(b.net_payable || b.bill_total || "0")}">Mark paid</button>`}
        </td>
      </tr>`;
    }).join("");
    reclaimable = `
      <h4 class="itc-subhead">Reversed — awaiting reclaim</h4>
      <p class="muted">Once the vendor is paid, re-avail the reversed ITC (GSTR-3B Table 4(D)(1)). Interest already charged is not reclaimable.</p>
      <div class="table-preview compact-table">
        <table>
          <thead><tr><th>Bill #</th><th>Vendor</th><th>Reversed on</th><th class="amount">ITC</th><th class="amount">Interest</th><th>Payment</th><th>Action</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  }

  return `
    <div class="report-date-controls">
      <label>As of <input type="date" data-itc-asof value="${escapeHtml(itcReversalAsOf)}"></label>
      <button class="secondary" type="button" data-business-action="itc-preview">Refresh</button>
    </div>
    <div class="preview-heading compact"><div><p>Bills unpaid beyond 180 days require ITC reversal under GST Rule 37.</p></div></div>
    ${flagged}
    ${reclaimable}
  `;
}
