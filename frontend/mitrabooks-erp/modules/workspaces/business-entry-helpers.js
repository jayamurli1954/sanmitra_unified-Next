// ====================================================================
// SECTION: BUSINESS ENTRY HELPERS — TDS, roles, reversal, focus
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initBusinessEntryHelpers(...).
// ====================================================================

/** @type {Record<string, any> | null} */
let deps = null;

/** Cached TDS/TCS section masters from GET /business/tds/sections. */
let tdsSectionsCache = null;

export function initBusinessEntryHelpers(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initBusinessEntryHelpers() must be called before using business entry helpers");
  }
  return deps;
}

function apiRequest(...args) { return requireDeps().apiRequest(...args); }
function escapeHtml(...args) { return requireDeps().escapeHtml(...args); }
function todayIsoDate(...args) { return requireDeps().todayIsoDate(...args); }
function getLastModuleContext() { return requireDeps().getLastModuleContext(); }

export function hasTdsSectionsCache() {
  return !!tdsSectionsCache;
}

export async function loadTdsSections() {
  if (tdsSectionsCache) return tdsSectionsCache;
  const result = await apiRequest("mitrabooks", "/api/v1/business/tds/sections", { method: "GET" });
  if (result.ok) tdsSectionsCache = result.payload;
  return tdsSectionsCache;
}

export function tdsSectionRate(kind, section) {
  const rows = tdsSectionsCache?.[kind] || [];
  const hit = rows.find((r) => r.section === section);
  return hit ? Number(hit.rate) : 0;
}

export function tdsSectionOptions(kind, selected) {
  const rows = tdsSectionsCache?.[kind] || [];
  const none = `<option value="">No ${kind === "tds" ? "TDS" : "TCS"}</option>`;
  return none + rows.map((r) =>
    `<option value="${escapeHtml(r.section)}" ${r.section === selected ? "selected" : ""}>${escapeHtml(`${r.section} · ${r.label} @ ${r.rate}%`)}</option>`
  ).join("");
}

export function isBusinessAdmin() {
  const role = String(getLastModuleContext()?.role || getLastModuleContext()?.user_role || "").trim().toLowerCase();
  // Show settings to admins; when role is unknown the backend still enforces access on save.
  return role === "" || role === "tenant_admin" || role === "super_admin";
}

export function isCaViewer() {
  const role = String(getLastModuleContext()?.role || getLastModuleContext()?.user_role || "").trim().toLowerCase();
  return role === "ca_viewer";
}

export function round2(value) {
  const n = Number(value);
  if (!isFinite(n)) return 0;
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

export function reversalDateBounds(isoDate) {
  const d = String(isoDate || todayIsoDate());
  const ym = d.slice(0, 7);
  const [y, m] = ym.split("-").map(Number);
  const lastDay = new Date(y, m, 0).getDate();
  const start = `${ym}-01`;
  const end = `${ym}-${String(lastDay).padStart(2, "0")}`;
  const today = todayIsoDate();
  const inMonth = today.slice(0, 7) === ym;
  return { min: start, max: inMonth ? today : end, def: inMonth ? today : end, label: ym };
}

export function reversalPanel(kind, id, isoDate) {
  const b = reversalDateBounds(isoDate);
  return `
    <div class="reversal-panel">
      <label>Reversal date
        <input type="date" data-reversal-date value="${escapeHtml(b.def)}" min="${escapeHtml(b.min)}" max="${escapeHtml(b.max)}">
      </label>
      <div class="reversal-panel-actions">
        <button class="primary" type="button" data-business-action="confirm-reverse-${kind}" data-${kind}-id="${escapeHtml(id)}">Confirm reverse</button>
        <button class="secondary" type="button" data-business-action="cancel-reverse-${kind}">Cancel</button>
      </div>
      <p class="muted">Must be dated within the document's GST month (${escapeHtml(b.label)}). A reversing journal entry will be posted on this date.</p>
      <p class="muted reversal-scope-note">Use reverse only to correct an entry made in error in the open period. For returns, price changes, or ITC reversal, raise a ${kind === "bill" ? "debit note" : "credit note"} instead (coming soon).</p>
    </div>
  `;
}

export function focusBusinessEntryField(selector) {
  setTimeout(() => {
    const field = document.querySelector(selector);
    if (field) {
      field.focus();
    }
  }, 0);
}

