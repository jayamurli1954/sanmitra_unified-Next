// ====================================================================
// SECTION: GRUHAMITRA WORKSPACE
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initGruhamitra(...).
// ====================================================================

import { apiRequest, renderJson } from "../../../shared/api-client.js";

export let activeGruhaWorkspace = "overview";
export let lastGruhaData = null;

/** @type {Record<string, Function> | null} */
let deps = null;

export function initGruhamitra(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initGruhamitra() must be called before using GruhaMitra helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function formatCurrency(value) { return requireDeps().formatCurrency(value); }
function resultRows(result) { return requireDeps().resultRows(result); }
function resultPayload(result, fallback) { return requireDeps().resultPayload(result, fallback); }
function renderStatCards(stats) { return requireDeps().renderStatCards(stats); }
function renderStatusBlock(title, result) { return requireDeps().renderStatusBlock(title, result); }
function renderSimpleTable(rows, columns, emptyText) { return requireDeps().renderSimpleTable(rows, columns, emptyText); }
function renderActivity(items) { return requireDeps().renderActivity(items); }
function renderAccountingDrilldownPanel(...args) { return requireDeps().renderAccountingDrilldownPanel(...args); }
function gruhaNavigationItems() { return requireDeps().gruhaNavigationItems(); }
function currentBillingPeriodQuery() { return requireDeps().currentBillingPeriodQuery(); }
function loadAccountingDrilldownResult() { return requireDeps().loadAccountingDrilldownResult(); }
function renderDashboardPreview(config) { return requireDeps().renderDashboardPreview(config); }
function syncGruhaNavActiveState() { return requireDeps().syncGruhaNavActiveState(); }
function getExperienceConfig() { return requireDeps().getExperienceConfig(); }
function getDashboardPreview() { return requireDeps().getDashboardPreview(); }
function getApiOutput() { return requireDeps().getApiOutput(); }

export function renderGruhaDashboard(config, payload) {
  const data = payload || {};
  const flats = resultRows(data.flats);
  const members = resultRows(data.members);
  const complaints = resultRows(data.complaints);
  const bills = resultRows(data.bills);
  const rooms = resultRows(data.rooms);
  const meetings = resultRows(data.meetings);
  const assets = resultRows(data.assets);
  const financialYears = resultRows(data.financialYears);
  const settings = resultPayload(data.settings, {});
  const openComplaints = complaints.filter((row) => !["closed", "resolved", "completed"].includes(String(row.status || "").toLowerCase())).length;
  const pendingBills = bills.filter((row) => !["paid", "posted", "closed"].includes(String(row.status || "").toLowerCase()));
  const pendingDues = pendingBills.reduce((sum, row) => sum + Number(row.balance_due || row.due_amount || row.total_amount || row.amount || 0), 0);
  const stats = [
    ["Flats", flats.length, "tenant-scoped units"],
    ["Members", members.length, "owners and residents"],
    ["Pending Dues", formatCurrency(pendingDues), `${pendingBills.length} bills`],
    ["Complaints Open", openComplaints, "service desk"],
  ];
  const societyName = settings?.society_name || settings?.name || "GruhaMitra Society";

  return `
    <div class="legacy-dashboard gruha-dashboard">
      <div class="society-header-preview">
        <img src="${config.logo}" alt="GruhaMitra">
        <div>
          <h3>${escapeHtml(societyName)}</h3>
          <p>Housing operations inside MitraBooks Unified ERP</p>
        </div>
        <span class="pill">HOUSING</span>
      </div>
      ${renderStatusBlock("GruhaMitra data", data.summary)}
      <div class="metric-grid four">${renderStatCards(stats)}</div>
      ${renderGruhaWorkspace({
        flats,
        members,
        complaints,
        bills,
        rooms,
        meetings,
        assets,
        financialYears,
        settings,
        config,
      })}
    </div>
  `;
}


export function renderGruhaWorkspace(data) {
  if (activeGruhaWorkspace === "maintenance") {
    return `
      <div class="dashboard-main-grid">
        <article>
          <h4>Maintenance Bills</h4>
          ${renderSimpleTable(data.bills, [
            { label: "Bill", value: (row) => row.bill_number || row.id || row.bill_id || "-" },
            { label: "Flat", value: (row) => row.flat_number || row.flat_id || "-" },
            { label: "Amount", value: (row) => formatCurrency(row.total_amount || row.amount || row.balance_due) },
            { label: "Status", value: (row) => row.status || "-" },
          ], "No maintenance bills returned by the compatibility API.")}
        </article>
        <article>
          <h4>Accounting Boundary</h4>
          <p class="muted">Maintenance collections use the unified `/api/v1/housing/maintenance-collections` route, which posts through the MitraBooks accounting service with tenant and app-key context.</p>
          <div class="grouped-nav-preview">
            <article><strong>Billing</strong><span>Use legacy bill generation endpoints for existing GruhaMitra behavior.</span></article>
            <article><strong>Collections</strong><span>Post through MitraBooks accounting; do not duplicate ledger logic in housing.</span></article>
          </div>
        </article>
      </div>
    `;
  }
  if (activeGruhaWorkspace === "members") {
    return renderSimpleTable(data.members, [
      { label: "Name", value: (row) => row.name || row.full_name || "-" },
      { label: "Flat", value: (row) => row.flat_number || row.unit_label || "-" },
      { label: "Type", value: (row) => row.member_type || row.role || "-" },
      { label: "Status", value: (row) => row.status || "-" },
    ], "No members found for this tenant/app context.");
  }
  if (activeGruhaWorkspace === "flats") {
    return renderSimpleTable(data.flats, [
      { label: "Flat", value: (row) => row.flat_number || row.id || "-" },
      { label: "Block", value: (row) => row.block || "-" },
      { label: "Floor", value: (row) => row.floor ?? "-" },
      { label: "Status", value: (row) => row.status || "-" },
    ], "No flats found. Configure society blocks or import flats.");
  }
  if (activeGruhaWorkspace === "complaints") {
    return renderSimpleTable(data.complaints, [
      { label: "Complaint", value: (row) => row.title || row.subject || row.id || "-" },
      { label: "Flat", value: (row) => row.flat_number || row.flat_id || "-" },
      { label: "Category", value: (row) => row.category || "-" },
      { label: "Status", value: (row) => row.status || "-" },
    ], "No complaints found for this society.");
  }
  if (activeGruhaWorkspace === "messages") {
    return renderSimpleTable(data.rooms, [
      { label: "Room", value: (row) => row.name || row.id || "-" },
      { label: "Type", value: (row) => row.type || "-" },
      { label: "Audience", value: (row) => row.audience_type || "public" },
      { label: "Updated", value: (row) => row.last_message_at || row.updated_at || "-" },
    ], "No message rooms found.");
  }
  if (activeGruhaWorkspace === "meetings") {
    return renderSimpleTable(data.meetings, [
      { label: "Meeting", value: (row) => row.meeting_title || row.title || row.id || "-" },
      { label: "Date", value: (row) => row.meeting_date || "-" },
      { label: "Type", value: (row) => row.meeting_type || "-" },
      { label: "Status", value: (row) => row.status || "-" },
    ], "No meetings found.");
  }
  if (activeGruhaWorkspace === "assets") {
    return renderSimpleTable(data.assets, [
      { label: "Asset", value: (row) => row.name || row.asset_code || "-" },
      { label: "Category", value: (row) => row.category || "-" },
      { label: "Location", value: (row) => row.location || "-" },
      { label: "Accounting", value: (row) => row.accounting_posting_status || "not_posted" },
    ], "No society assets found.");
  }
  if (activeGruhaWorkspace === "accounting" || activeGruhaWorkspace === "reports") {
    return renderAccountingDrilldownPanel();
  }
  if (activeGruhaWorkspace === "settings") {
    const blocks = Array.isArray(data.settings?.blocks_config) ? data.settings.blocks_config : [];
    return `
      <div class="dashboard-main-grid">
        <article>
          <h4>Society Settings</h4>
          ${renderSimpleTable(blocks, [
            { label: "Block", value: (row) => row.name || "-" },
            { label: "Floors", value: (row) => row.floors ?? "-" },
            { label: "Flats/Floor", value: (row) => row.flatsPerFloor ?? "-" },
          ], "No block configuration found.")}
        </article>
        <article>
          <h4>Financial Years</h4>
          ${renderSimpleTable(data.financialYears, [
            { label: "Year", value: (row) => row.year_name || row.id || "-" },
            { label: "Start", value: (row) => row.start_date || "-" },
            { label: "End", value: (row) => row.end_date || "-" },
            { label: "Status", value: (row) => row.status || "-" },
          ], "No financial years found.")}
        </article>
      </div>
    `;
  }
  return `
    <div class="dashboard-main-grid">
      <article>
        <h4>Quick Actions</h4>
        <div class="quick-grid">
          ${gruhaNavigationItems().filter((item) => item.gruhaWorkspace !== "overview").map((item) => `
            <button class="quick-tile" type="button" data-gruha-action="workspace-view" data-workspace-view="${escapeHtml(item.gruhaWorkspace)}">
              <span class="quick-icon">${escapeHtml(item.icon)}</span>
              <span>${escapeHtml(item.label)}</span>
            </button>
          `).join("")}
        </div>
      </article>
      <article>
        <h4>Integration Status</h4>
        <ul class="activity-list">
          ${renderActivity([
            "Legacy GruhaMitra compatibility routes are mounted under /api/v1",
            "Tenant, app-key, and module registry checks stay in the unified backend",
            "Accounting remains delegated to MitraBooks shared journal posting",
          ])}
        </ul>
      </article>
    </div>
    <article class="trend-panel">
      <h4>Reports</h4>
      ${renderAccountingDrilldownPanel()}
    </article>
  `;
}


export async function loadGruhaDashboard() {
  const billingPeriodQuery = currentBillingPeriodQuery();
  const [
    settings,
    flats,
    members,
    complaints,
    bills,
    rooms,
    meetings,
    assets,
    financialYears,
    accountingDrilldown,
  ] = await Promise.all([
    apiRequest("gruhamitra", "/api/v1/settings/society", { method: "GET" }),
    apiRequest("gruhamitra", "/api/v1/flats", { method: "GET" }),
    apiRequest("gruhamitra", "/api/v1/member-onboarding", { method: "GET" }),
    apiRequest("gruhamitra", "/api/v1/complaints/", { method: "GET" }),
    apiRequest("gruhamitra", `/api/v1/maintenance/bills?${billingPeriodQuery}`, { method: "GET" }),
    apiRequest("gruhamitra", "/api/v1/messages/rooms", { method: "GET" }),
    apiRequest("gruhamitra", "/api/v1/meetings", { method: "GET" }),
    apiRequest("gruhamitra", "/api/v1/assets", { method: "GET" }),
    apiRequest("gruhamitra", "/api/v1/financial-years/", { method: "GET" }),
    loadAccountingDrilldownResult(),
  ]);
  lastGruhaData = {
    settings,
    flats,
    members,
    complaints,
    bills,
    rooms,
    meetings,
    assets,
    financialYears,
    accountingDrilldown,
    summary: [settings, flats, members, complaints, bills, rooms, meetings, assets, financialYears].find((result) => !result.ok) || null,
  };
  renderJson(getApiOutput(), { gruhamitra: lastGruhaData });
  getDashboardPreview().innerHTML = renderDashboardPreview(getExperienceConfig().gruha);
  syncGruhaNavActiveState();
}


export async function setGruhaWorkspace(view) {
  const allowedViews = new Set([
    "overview",
    "maintenance",
    "members",
    "flats",
    "complaints",
    "messages",
    "meetings",
    "assets",
    "accounting",
    "reports",
    "settings",
  ]);
  if (!allowedViews.has(view)) {
    return;
  }
  activeGruhaWorkspace = view;
  syncGruhaNavActiveState();
  if (!lastGruhaData) {
    await loadGruhaDashboard();
  } else {
    getDashboardPreview().innerHTML = renderDashboardPreview(getExperienceConfig().gruha);
  }
  document.querySelector(".content")?.scrollTo({ top: 0, behavior: "smooth" });
}

