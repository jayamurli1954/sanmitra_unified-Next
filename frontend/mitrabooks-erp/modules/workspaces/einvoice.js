// ====================================================================
// SECTION: E-INVOICING (IRN foundation, credential-free)
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initEinvoice(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let lastEinvoiceView = null;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initEinvoice(injected) {
  deps = injected;
}

/** Used by sales-invoices workspace (imported let binding is read-only). */
export function clearEinvoiceView() {
  lastEinvoiceView = null;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initEinvoice() must be called before using einvoice helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function setLoginStatus(kind, title, detail = "") { requireDeps().setLoginStatus(kind, title, detail); }
function statusDetailText(detail) { return requireDeps().statusDetailText(detail); }
function rerenderSalesIfActive() { return requireDeps().rerenderSalesIfActive(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

// ══════════════════════════════════════════════════════════════════════
// SECTION: E-INVOICING (IRN foundation, credential-free)
// API   : GET /api/v1/business/invoices/{id}/einvoice  POST .../record
// NOTE  : loadEinvoiceView, recordEinvoiceIrn, renderEinvoiceSection — INV-01 v1.1 payload
// ══════════════════════════════════════════════════════════════════════

export async function loadEinvoiceView(invoiceId) {
  const result = await apiRequest("mitrabooks", `/api/v1/business/invoices/${encodeURIComponent(invoiceId)}/einvoice`, { method: "GET" });
  lastEinvoiceView = result.ok ? result.payload : { ok: false, detail: result.payload?.detail || `HTTP ${result.status}.` };
  rerenderSalesIfActive();
  renderJson(getApiOutput(), { einvoice_view: { ok: result.ok, invoice_id: invoiceId } });
}

export function downloadInv01Json() {
  const v = lastEinvoiceView;
  if (!v?.payload) { setLoginStatus("warn", "Not ready", "Fix the readiness errors first."); return; }
  const blob = new Blob([JSON.stringify(v.payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `einvoice_${v.invoice_number || v.invoice_id}.json`;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
  renderJson(getApiOutput(), { einvoice_download: { invoice_id: v.invoice_id } });
}

export async function recordEinvoiceIrn() {
  const v = lastEinvoiceView;
  if (!v) return;
  const irn = document.querySelector("[data-einv-irn]")?.value || "";
  const ackNo = document.querySelector("[data-einv-ackno]")?.value || "";
  const ackDate = document.querySelector("[data-einv-ackdate]")?.value || "";
  if (!irn.trim()) {
    setLoginStatus("warn", "IRN required", "Paste the 64-character IRN the portal returned.");
    return;
  }
  const result = await apiRequest("mitrabooks", `/api/v1/business/invoices/${encodeURIComponent(v.invoice_id)}/einvoice/record`, {
    method: "POST",
    body: JSON.stringify({ irn: irn.trim(), ack_no: ackNo.trim() || null, ack_date: ackDate || null }),
  });
  if (result.ok) {
    setLoginStatus("ok", "IRN recorded", "The invoice is marked e-invoice registered.");
    await loadEinvoiceView(v.invoice_id);
  } else {
    setLoginStatus("danger", "Could not record", statusDetailText(result.payload?.detail) || `HTTP ${result.status}.`);
  }
  renderJson(getApiOutput(), { einvoice_record: { ok: result.ok, status: result.status } });
}

export function renderEinvoiceSection(inv) {
  if (String(inv.status).toLowerCase() !== "posted") return "";
  const v = lastEinvoiceView;
  if (!v) return `<div class="table-preview compact-table"><h4>e-Invoice (IRN)</h4><p class="muted">Checking e-invoice readiness...</p></div>`;
  if (v.ok === false) return `<div class="table-preview compact-table"><h4>e-Invoice (IRN)</h4><p class="muted">${escapeHtml(v.detail || "Unavailable.")}</p></div>`;
  const e = v.einvoice || {};
  if (e.status === "registered") {
    return `
      <div class="table-preview compact-table">
        <h4>e-Invoice (IRN) <span class="pill ok">registered</span></h4>
        <p class="muted">IRN: <code style="word-break:break-all;">${escapeHtml(e.irn || "")}</code><br>
        ${e.ack_no ? `Ack no. ${escapeHtml(e.ack_no)}` : ""}${e.ack_date ? ` · Ack date ${escapeHtml(e.ack_date)}` : ""} · recorded by ${escapeHtml(e.recorded_by || "")} ${escapeHtml(String(e.recorded_at || "").slice(0, 10))}</p>
      </div>`;
  }
  if (!v.eligible) {
    return `
      <div class="table-preview compact-table">
        <h4>e-Invoice (IRN) <span class="pill warn">not ready</span></h4>
        <ul class="muted" style="margin:6px 0 0 18px;">${(v.errors || []).map((err) => `<li>${escapeHtml(err)}</li>`).join("")}</ul>
      </div>`;
  }
  return `
    <div class="table-preview compact-table">
      <h4>e-Invoice (IRN) <span class="pill">payload ready</span></h4>
      <div class="report-date-controls">
        <button class="secondary" type="button" data-business-action="einv-download">Download INV-01 JSON</button>
        <span class="muted">Upload it on the e-invoice portal / offline utility, then record the result:</span>
      </div>
      <div class="report-date-controls">
        <label>IRN <input type="text" data-einv-irn maxlength="64" placeholder="64-character hash" style="min-width:260px;"></label>
        <label>Ack no. <input type="text" data-einv-ackno maxlength="30" style="width:130px;"></label>
        <label>Ack date <input type="date" data-einv-ackdate></label>
        <button class="primary" type="button" data-business-action="einv-record">Record IRN</button>
      </div>
      ${(v.notes || []).map((n) => `<p class="muted">${escapeHtml(n)}</p>`).join("")}
    </div>`;
}
