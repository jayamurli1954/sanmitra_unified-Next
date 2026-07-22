// ====================================================================
// SECTION: HR / PAYROLL ADD-ON WORKSPACE
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initHrWorkspace(...).
// ====================================================================

import { apiRequest, downloadApiFile } from "../../../shared/api-client.js";

export const hrUi = {
  tab: "employees",
  showAddEmployee: false,
  assignFor: "",
  showLetterSettings: false,
  selectedRunId: "",
  runSlips: [],
  error: "",
};

let hrAccess = null;
let hrEmployees = [];
let hrRuns = [];
let hrAnalytics = null;
let hrLeaveTypes = [];
let hrLeaveApplications = [];
let hrDeclarations = [];
let hrFnf = [];
let hrStructures = [];
let hrAppointmentConfig = null;

/** @type {{ escapeHtml: (v: string) => string, refreshHrView: () => void } | null} */
let deps = null;

export function initHrWorkspace({ escapeHtml, refreshHrView }) {
  deps = { escapeHtml, refreshHrView };
}

function requireDeps() {
  if (!deps) {
    throw new Error("initHrWorkspace() must be called before using the HR workspace");
  }
  return deps;
}

function refreshHrView() {
  if (deps) {
    deps.refreshHrView();
  }
}

function escapeHtml(value) {
  return requireDeps().escapeHtml(value);
}

function hrMoney(value) {
  const n = Number(value || 0);
  return "₹" + n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function hrCanManage() {
  return !!(hrAccess && hrAccess.can_manage);
}

export async function loadHrWorkspace() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/hr/access", { method: "GET" });
  hrAccess = res.ok ? res.payload : { entitled: false, available: false, error: res.payload?.detail };
  refreshHrView();
  if (hrAccess && hrAccess.entitled) {
    loadHrEmployees();
    loadHrStructures();
    loadHrAppointmentConfig();
    loadHrRuns();
    loadHrAnalytics();
  }
}

async function loadHrStructures() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/hr/salary-structures", { method: "GET" });
  hrStructures = res.ok && Array.isArray(res.payload?.structures) ? res.payload.structures : [];
  refreshHrView();
}

async function loadHrAppointmentConfig() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/hr/appointment-settings", { method: "GET" });
  hrAppointmentConfig = res.ok ? res.payload : null;
  refreshHrView();
}

export function hrDownloadLetter(button) {
  const employeeId = button.getAttribute("data-emp-id") || "";
  if (!employeeId) return;
  downloadApiFile(
    "mitrabooks",
    `/api/v1/business/hr/employees/${encodeURIComponent(employeeId)}/appointment-letter`,
    `appointment-letter-${employeeId}.pdf`,
  );
}

export function hrDownloadJoiningLetter(button) {
  const employeeId = button.getAttribute("data-emp-id") || "";
  if (!employeeId) return;
  downloadApiFile(
    "mitrabooks",
    `/api/v1/business/hr/employees/${encodeURIComponent(employeeId)}/joining-letter`,
    `joining-letter-${employeeId}.pdf`,
  );
}

// Status-aware row actions for the onboarding lifecycle.
function hrEmployeeActions(e) {
  const id = escapeHtml(e.employee_id);
  const btn = (action, label) => `<button class="secondary" type="button" data-business-action="${action}" data-emp-id="${id}">${label}</button>`;
  const status = e.status || "";
  let out = btn("hr-assign-open", "Assign Salary") + " " + btn("hr-letter", "Appt Letter");
  if (status === "offered" || status === "onboarding") {
    out += " " + btn("hr-mark-joined", "Mark Joined") + " " + btn("hr-mark-declined", "Decline");
  } else if (status === "active") {
    out += " " + btn("hr-joining-letter", "Joining Letter");
  }
  return out;
}

export async function hrMarkJoined(button) {
  const id = button.getAttribute("data-emp-id") || "";
  if (!id) return;
  const today = new Date().toISOString().slice(0, 10);
  const when = window.prompt("Joining date (YYYY-MM-DD):", today);
  if (!when) return;
  const res = await apiRequest("mitrabooks", `/api/v1/business/hr/employees/${encodeURIComponent(id)}/join`, {
    method: "POST", body: JSON.stringify({ joining_date: when }),
  });
  if (!res.ok) { hrUi.error = res.payload?.detail || "Could not mark joined."; refreshHrView(); return; }
  hrUi.error = "";
  await loadHrEmployees();
}

export async function hrMarkDeclined(button) {
  const id = button.getAttribute("data-emp-id") || "";
  if (!id) return;
  if (!window.confirm("Mark this candidate as declined? No employee code will be assigned.")) return;
  const res = await apiRequest("mitrabooks", `/api/v1/business/hr/employees/${encodeURIComponent(id)}/decline`, { method: "POST" });
  if (!res.ok) { hrUi.error = res.payload?.detail || "Could not decline."; refreshHrView(); return; }
  hrUi.error = "";
  await loadHrEmployees();
}

export async function hrSaveLetterSettings() {
  const num = (id, d) => { const n = parseInt(document.getElementById(id)?.value, 10); return Number.isFinite(n) ? n : d; };
  const chk = (id) => !!document.getElementById(id)?.checked;
  const body = {
    probation_months: num("hr-ls-probation", 6),
    notice_days: num("hr-ls-notice", 30),
    work_hours: (document.getElementById("hr-ls-hours")?.value || "").trim() || "9:30 AM to 6:30 PM, Monday to Friday",
    signatory_name: (document.getElementById("hr-ls-signame")?.value || "").trim() || null,
    signatory_title: (document.getElementById("hr-ls-sigtitle")?.value || "").trim() || "Authorised Signatory",
    clauses: {
      background_check: chk("hr-ls-bg"), confidentiality_nda: chk("hr-ls-nda"),
      ip_assignment: chk("hr-ls-ip"), data_privacy: chk("hr-ls-data"),
      code_of_conduct: chk("hr-ls-conduct"), cash_handling: chk("hr-ls-cash"),
      relocation: chk("hr-ls-reloc"),
    },
  };
  const res = await apiRequest("mitrabooks", "/api/v1/business/hr/appointment-settings", { method: "PUT", body: JSON.stringify(body) });
  if (!res.ok) { hrUi.error = res.payload?.detail || "Could not save letter settings."; refreshHrView(); return; }
  hrUi.error = ""; hrUi.showLetterSettings = false; hrAppointmentConfig = res.payload;
  refreshHrView();
}

export async function hrEnable() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/hr/enabled", {
    method: "PUT", body: JSON.stringify({ enabled: true }),
  });
  if (!res.ok) {
    hrUi.error = res.payload?.detail || "Could not enable HR.";
    refreshHrView();
    return;
  }
  hrUi.error = "";
  loadHrWorkspace();  // re-probe access → tabs light up
}

async function loadHrEmployees() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/hr/employees", { method: "GET" });
  hrEmployees = res.ok && Array.isArray(res.payload?.employees) ? res.payload.employees : [];
  refreshHrView();
}

async function loadHrRuns() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/hr/payroll/runs", { method: "GET" });
  hrRuns = res.ok && Array.isArray(res.payload?.runs) ? res.payload.runs : [];
  refreshHrView();
}

async function loadHrAnalytics() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/hr/analytics/dashboard?months=6", { method: "GET" });
  hrAnalytics = res.ok ? res.payload : null;
  refreshHrView();
}

export async function loadHrRunSlips(runId) {
  hrUi.selectedRunId = runId;
  const res = await apiRequest(
    "mitrabooks",
    `/api/v1/business/hr/payroll/runs/${encodeURIComponent(runId)}/slips`,
    { method: "GET" },
  );
  hrUi.runSlips = res.ok && Array.isArray(res.payload) ? res.payload : [];
  refreshHrView();
}

export async function hrRunPayroll() {
  const year = parseInt(document.getElementById("hr-run-year")?.value, 10);
  const month = parseInt(document.getElementById("hr-run-month")?.value, 10);
  if (!year || !month) {
    hrUi.error = "Enter a valid year and month before running payroll.";
    refreshHrView();
    return;
  }
  hrUi.error = "";
  const res = await apiRequest("mitrabooks", "/api/v1/business/hr/payroll/run", {
    method: "POST",
    body: JSON.stringify({ year, month }),
  });
  hrUi.error = res.ok ? "" : (res.payload?.detail || "Payroll run failed.");
  await loadHrRuns();
  await loadHrAnalytics();
  refreshHrView();
}

export function hrDownloadSlipPdf(button) {
  const slipId = button.getAttribute("data-slip-id") || "";
  const period = button.getAttribute("data-period") || "slip";
  if (!slipId) return;
  downloadApiFile(
    "mitrabooks",
    `/api/v1/business/hr/payroll/slips/${encodeURIComponent(slipId)}/pdf`,
    `salary-slip-${period}.pdf`,
  );
}

// ── Leave ────────────────────────────────────────────────────────────────────
export async function loadHrLeave() {
  const [types, apps] = await Promise.all([
    apiRequest("mitrabooks", "/api/v1/business/hr/leave-types", { method: "GET" }),
    apiRequest("mitrabooks", "/api/v1/business/hr/leave-applications", { method: "GET" }),
  ]);
  hrLeaveTypes = types.ok && Array.isArray(types.payload?.leave_types) ? types.payload.leave_types : [];
  hrLeaveApplications = apps.ok && Array.isArray(apps.payload?.applications) ? apps.payload.applications : [];
  refreshHrView();
}

export async function hrCreateLeaveType() {
  const code = (document.getElementById("hr-lt-code")?.value || "").trim();
  const name = (document.getElementById("hr-lt-name")?.value || "").trim();
  const isLwp = !!document.getElementById("hr-lt-lwp")?.checked;
  if (!code || !name) { hrUi.error = "Leave type needs a code and name."; refreshHrView(); return; }
  const res = await apiRequest("mitrabooks", "/api/v1/business/hr/leave-types", {
    method: "POST", body: JSON.stringify({ code, name, is_lwp: isLwp }),
  });
  hrUi.error = res.ok ? "" : (res.payload?.detail || "Could not create leave type.");
  await loadHrLeave();
}

export async function hrAllocateLeave() {
  const employeeId = document.getElementById("hr-alloc-emp")?.value || "";
  const leaveTypeId = document.getElementById("hr-alloc-type")?.value || "";
  const days = parseFloat(document.getElementById("hr-alloc-days")?.value);
  if (!employeeId || !leaveTypeId || !days) { hrUi.error = "Pick employee, leave type and days."; refreshHrView(); return; }
  const res = await apiRequest("mitrabooks", `/api/v1/business/hr/employees/${encodeURIComponent(employeeId)}/leave-allocations`, {
    method: "POST", body: JSON.stringify({ leave_type_id: leaveTypeId, days }),
  });
  hrUi.error = res.ok ? "" : (res.payload?.detail || "Allocation failed.");
  refreshHrView();
}

export async function hrApplyLeave() {
  const employeeId = document.getElementById("hr-leave-emp")?.value || "";
  const leaveTypeId = document.getElementById("hr-leave-type")?.value || "";
  const fromDate = document.getElementById("hr-leave-from")?.value || "";
  const toDate = document.getElementById("hr-leave-to")?.value || "";
  if (!employeeId || !leaveTypeId || !fromDate || !toDate) { hrUi.error = "Fill all leave fields."; refreshHrView(); return; }
  const res = await apiRequest("mitrabooks", "/api/v1/business/hr/leave-applications", {
    method: "POST",
    body: JSON.stringify({ employee_id: employeeId, leave_type_id: leaveTypeId, from_date: fromDate, to_date: toDate }),
  });
  hrUi.error = res.ok ? "" : (res.payload?.detail || "Leave application failed.");
  await loadHrLeave();
}

export async function hrDecideLeave(button, decision) {
  const id = button.getAttribute("data-app-id") || "";
  if (!id) return;
  const res = await apiRequest("mitrabooks", `/api/v1/business/hr/leave-applications/${encodeURIComponent(id)}/${decision}`, { method: "POST" });
  hrUi.error = res.ok ? "" : (res.payload?.detail || `Could not ${decision} leave.`);
  await loadHrLeave();
}

// ── Form 12BB (tax) ──────────────────────────────────────────────────────────
export async function loadHrTax() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/hr/tax-declarations", { method: "GET" });
  hrDeclarations = res.ok && Array.isArray(res.payload?.declarations) ? res.payload.declarations : [];
  refreshHrView();
}

export async function hrCreateDeclaration() {
  const employeeId = document.getElementById("hr-decl-emp")?.value || "";
  const fy = (document.getElementById("hr-decl-fy")?.value || "").trim();
  const section = (document.getElementById("hr-decl-section")?.value || "").trim();
  const name = (document.getElementById("hr-decl-name")?.value || "").trim();
  const amount = parseFloat(document.getElementById("hr-decl-amount")?.value);
  if (!employeeId || !fy || !section || !name || !(amount >= 0)) { hrUi.error = "Fill all declaration fields."; refreshHrView(); return; }
  const res = await apiRequest("mitrabooks", "/api/v1/business/hr/tax-declarations", {
    method: "POST",
    body: JSON.stringify({ employee_id: employeeId, financial_year: fy, section_code: section, investment_name: name, declared_amount: amount }),
  });
  hrUi.error = res.ok ? "" : (res.payload?.detail || "Declaration failed.");
  await loadHrTax();
}

export async function hrVerifyDeclaration(button, approve) {
  const id = button.getAttribute("data-decl-id") || "";
  if (!id) return;
  let verified = 0;
  if (approve) {
    const declared = button.getAttribute("data-declared") || "0";
    const entry = window.prompt("Verified amount to allow:", declared);
    if (entry === null) return;
    verified = parseFloat(entry) || 0;
  }
  const res = await apiRequest("mitrabooks", `/api/v1/business/hr/tax-declarations/${encodeURIComponent(id)}/verify`, {
    method: "POST", body: JSON.stringify({ verified_amount: verified, approve }),
  });
  hrUi.error = res.ok ? "" : (res.payload?.detail || "Verification failed.");
  await loadHrTax();
}

// ── Full & Final ─────────────────────────────────────────────────────────────
export async function loadHrFnf() {
  const res = await apiRequest("mitrabooks", "/api/v1/business/hr/fnf", { method: "GET" });
  hrFnf = res.ok && Array.isArray(res.payload?.settlements) ? res.payload.settlements : [];
  refreshHrView();
}

export async function hrCreateFnf() {
  const employeeId = document.getElementById("hr-fnf-emp")?.value || "";
  const lwd = document.getElementById("hr-fnf-lwd")?.value || "";
  const basic = parseFloat(document.getElementById("hr-fnf-basic")?.value);
  const leaves = parseFloat(document.getElementById("hr-fnf-leaves")?.value) || 0;
  const notice = parseFloat(document.getElementById("hr-fnf-notice")?.value) || 0;
  if (!employeeId || !lwd || !(basic > 0)) { hrUi.error = "Employee, last working day and last basic are required."; refreshHrView(); return; }
  const res = await apiRequest("mitrabooks", "/api/v1/business/hr/fnf", {
    method: "POST",
    body: JSON.stringify({ employee_id: employeeId, last_working_day: lwd, last_drawn_basic: basic, unutilized_leaves: leaves, unpaid_notice_days: notice }),
  });
  hrUi.error = res.ok ? "" : (res.payload?.detail || "Could not create settlement.");
  await loadHrFnf();
}

export async function hrTransitionFnf(button, action) {
  const id = button.getAttribute("data-fnf-id") || "";
  if (!id) return;
  const res = await apiRequest("mitrabooks", `/api/v1/business/hr/fnf/${encodeURIComponent(id)}/${action}`, { method: "POST" });
  hrUi.error = res.ok ? "" : (res.payload?.detail || `Could not ${action} settlement.`);
  await loadHrFnf();
}

export function hrDownloadFnfPdf(button) {
  const id = button.getAttribute("data-fnf-id") || "";
  if (!id) return;
  downloadApiFile("mitrabooks", `/api/v1/business/hr/fnf/${encodeURIComponent(id)}/pdf`, `fnf-${id.slice(0, 8)}.pdf`);
}

export async function hrCreateEmployee() {
  const v = (id) => (document.getElementById(id)?.value || "").trim();
  const body = {
    user_id: v("hr-emp-userid") || null,   // blank -> backend auto-generates EMP-####
    full_name: v("hr-emp-name"),
    designation: v("hr-emp-designation") || null,
    department: v("hr-emp-department") || null,
    date_of_joining: v("hr-emp-doj"),
    state_for_professional_tax: v("hr-emp-ptstate") || null,
    is_pf_eligible: !!document.getElementById("hr-emp-pf")?.checked,
    is_esic_eligible: !!document.getElementById("hr-emp-esic")?.checked,
    status: "active",
  };
  if (!body.full_name || !body.date_of_joining) {
    hrUi.error = "Employee needs a Full Name and Date of Joining."; refreshHrView(); return;
  }
  const res = await apiRequest("mitrabooks", "/api/v1/business/hr/employees", { method: "POST", body: JSON.stringify(body) });
  if (!res.ok) { hrUi.error = res.payload?.detail || "Could not create employee."; refreshHrView(); return; }
  hrUi.error = ""; hrUi.showAddEmployee = false;
  await loadHrEmployees();
}

export async function hrCreateStructure() {
  const name = (document.getElementById("hr-struct-name")?.value || "").trim();
  const basic = (document.getElementById("hr-struct-basic")?.value || "GROSS * 0.5").trim();
  const hra = (document.getElementById("hr-struct-hra")?.value || "BASIC * 0.4").trim();
  if (!name) { hrUi.error = "Give the salary structure a name."; refreshHrView(); return; }
  const body = {
    name,
    components: [
      { name: "Basic", abbr: "BASIC", formula: basic, statutory_kind: "basic" },
      { name: "HRA", abbr: "HRA", formula: hra },
      { name: "Special Allowance", abbr: "SPECIAL", formula: "GROSS - BASIC - HRA" },
    ],
  };
  const res = await apiRequest("mitrabooks", "/api/v1/business/hr/salary-structures", { method: "POST", body: JSON.stringify(body) });
  if (!res.ok) { hrUi.error = res.payload?.detail || "Could not create structure."; refreshHrView(); return; }
  hrUi.error = "";
  await loadHrStructures();
}

export async function hrAssignSalary() {
  const employeeId = hrUi.assignFor;
  const structureId = document.getElementById("hr-assign-structure")?.value || "";
  const gross = (document.getElementById("hr-assign-gross")?.value || "").trim();
  const regime = document.getElementById("hr-assign-regime")?.value || "new";
  if (!structureId || !gross) { hrUi.error = "Pick a structure and enter monthly gross."; refreshHrView(); return; }
  const res = await apiRequest(
    "mitrabooks",
    `/api/v1/business/hr/employees/${encodeURIComponent(employeeId)}/salary`,
    { method: "PUT", body: JSON.stringify({ structure_id: structureId, monthly_gross: gross, regime }) },
  );
  if (!res.ok) { hrUi.error = res.payload?.detail || "Could not assign salary."; refreshHrView(); return; }
  hrUi.error = ""; hrUi.assignFor = "";
  refreshHrView();
}

function hrStructureOptions() {
  return hrStructures.map((s) => `<option value="${escapeHtml(s.structure_id)}">${escapeHtml(s.name)}</option>`).join("");
}

function hrEmployeeOptions(selectedId) {
  return hrEmployees.map((e) =>
    `<option value="${escapeHtml(e.employee_id)}"${e.employee_id === selectedId ? " selected" : ""}>${escapeHtml(e.full_name || e.employee_id)}</option>`,
  ).join("");
}

function hrLeaveTypeOptions() {
  return hrLeaveTypes.map((t) =>
    `<option value="${escapeHtml(t.leave_type_id)}">${escapeHtml(t.code)} — ${escapeHtml(t.name)}${t.is_lwp ? " (LWP)" : ""}</option>`,
  ).join("");
}

function hrTabButton(key, label) {
  const active = hrUi.tab === key ? " active" : "";
  return `<button type="button" class="erp-tab${active}" data-business-action="hr-tab" data-hr-tab="${key}">${escapeHtml(label)}</button>`;
}

function renderHrEmployeesTab() {
  const manage = hrCanManage();

  const addForm = (manage && hrUi.showAddEmployee) ? `
    <div class="hr-add-form" style="border:1px solid var(--border,#333);border-radius:8px;padding:12px;margin-bottom:14px;display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;">
      <label>User ID<br><input id="hr-emp-userid" type="text" placeholder="auto (EMP-####)" style="width:130px;"></label>
      <label>Full Name*<br><input id="hr-emp-name" type="text" style="width:150px;"></label>
      <label>Designation<br><input id="hr-emp-designation" type="text" style="width:120px;"></label>
      <label>Department<br><input id="hr-emp-department" type="text" style="width:120px;"></label>
      <label>Date of Joining*<br><input id="hr-emp-doj" type="date"></label>
      <label>PT State<br><input id="hr-emp-ptstate" type="text" placeholder="Karnataka" style="width:110px;"></label>
      <label style="display:flex;gap:4px;align-items:center;"><input id="hr-emp-pf" type="checkbox" checked> PF</label>
      <label style="display:flex;gap:4px;align-items:center;"><input id="hr-emp-esic" type="checkbox"> ESIC</label>
      <button class="primary" type="button" data-business-action="hr-create-employee">Save</button>
      <button class="secondary" type="button" data-business-action="hr-add-employee-cancel">Cancel</button>
    </div>` : "";

  const addBtn = (manage && !hrUi.showAddEmployee)
    ? `<button class="secondary" type="button" data-business-action="hr-add-employee-toggle" style="margin-bottom:12px;">+ Add Employee</button>
       <button class="secondary" type="button" data-business-action="hr-letter-settings-toggle" style="margin-bottom:12px;margin-left:6px;">⚙ Letter Settings</button>`
    : "";

  const c = (hrAppointmentConfig && hrAppointmentConfig.clauses) || {};
  const ck = (id, key, label) => `<label style="display:flex;gap:4px;align-items:center;"><input id="${id}" type="checkbox" ${c[key] ? "checked" : ""}> ${label}</label>`;
  const letterSettings = (manage && hrUi.showLetterSettings) ? `
    <div style="border:1px solid var(--border,#333);border-radius:8px;padding:12px;margin-bottom:14px;">
      <strong>Appointment-letter settings</strong>
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;margin-top:8px;">
        <label>Probation (months)<br><input id="hr-ls-probation" type="number" min="0" max="24" value="${hrAppointmentConfig?.probation_months ?? 6}" style="width:90px;"></label>
        <label>Notice (days)<br><input id="hr-ls-notice" type="number" min="0" max="180" value="${hrAppointmentConfig?.notice_days ?? 30}" style="width:90px;"></label>
        <label>Working hours<br><input id="hr-ls-hours" type="text" value="${escapeHtml(hrAppointmentConfig?.work_hours || "9:30 AM to 6:30 PM, Monday to Friday")}" style="width:230px;"></label>
        <label>Signatory name<br><input id="hr-ls-signame" type="text" value="${escapeHtml(hrAppointmentConfig?.signatory_name || "")}" style="width:140px;"></label>
        <label>Signatory title<br><input id="hr-ls-sigtitle" type="text" value="${escapeHtml(hrAppointmentConfig?.signatory_title || "Authorised Signatory")}" style="width:150px;"></label>
      </div>
      <div style="display:flex;gap:14px;flex-wrap:wrap;margin-top:10px;">
        ${ck("hr-ls-bg", "background_check", "Background check")}
        ${ck("hr-ls-nda", "confidentiality_nda", "Confidentiality / NDA")}
        ${ck("hr-ls-ip", "ip_assignment", "IP assignment")}
        ${ck("hr-ls-data", "data_privacy", "Data privacy")}
        ${ck("hr-ls-conduct", "code_of_conduct", "Code of conduct")}
        ${ck("hr-ls-cash", "cash_handling", "Cash/material handling")}
        ${ck("hr-ls-reloc", "relocation", "Shift/relocation")}
      </div>
      <div style="margin-top:10px;">
        <button class="primary" type="button" data-business-action="hr-save-letter-settings">Save Settings</button>
        <button class="secondary" type="button" data-business-action="hr-letter-settings-cancel">Cancel</button>
      </div>
    </div>` : "";

  const empBlock = hrEmployees.length ? `
    <table class="erp-table">
      <thead><tr><th>Emp Code</th><th>Name</th><th>Designation</th><th>Status</th>${manage ? "<th>Actions</th>" : ""}</tr></thead>
      <tbody>${hrEmployees.map((e) => `
        <tr>
          <td>${escapeHtml(e.employee_code || "—")}</td>
          <td>${escapeHtml(e.full_name || "")}</td>
          <td>${escapeHtml(e.designation || "—")}</td>
          <td><span class="status-pill">${escapeHtml(e.status || "")}</span></td>
          ${manage ? `<td style="white-space:nowrap;">${hrEmployeeActions(e)}</td>` : ""}
        </tr>`).join("")}</tbody>
    </table>` : `<p class="muted">No employees yet. Click "+ Add Employee" to create one.</p>`;

  const assignForm = (manage && hrUi.assignFor) ? `
    <div style="border:1px solid var(--border,#333);border-radius:8px;padding:12px;margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;">
      <strong style="width:100%;">Assign salary — ${escapeHtml(hrUi.assignFor)}</strong>
      <label>Structure<br><select id="hr-assign-structure" style="width:170px;">${hrStructureOptions()}</select></label>
      <label>Monthly Gross ₹<br><input id="hr-assign-gross" type="number" min="0" style="width:120px;"></label>
      <label>Regime<br><select id="hr-assign-regime"><option value="new">New</option><option value="old">Old</option></select></label>
      <button class="primary" type="button" data-business-action="hr-assign-submit">Assign</button>
      <button class="secondary" type="button" data-business-action="hr-assign-cancel">Cancel</button>
    </div>` : "";

  // Salary structures panel.
  const structForm = manage ? `
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;margin-bottom:10px;">
      <label>New structure name<br><input id="hr-struct-name" type="text" placeholder="Standard (Non-metro)" style="width:170px;"></label>
      <label>Basic formula<br><input id="hr-struct-basic" type="text" value="GROSS * 0.5" style="width:120px;"></label>
      <label>HRA formula<br><input id="hr-struct-hra" type="text" value="BASIC * 0.4" style="width:120px;"></label>
      <button class="secondary" type="button" data-business-action="hr-create-structure">Add Structure</button>
    </div>` : "";
  const structRows = hrStructures.length
    ? hrStructures.map((s) => `<tr><td>${escapeHtml(s.name)}</td><td>${escapeHtml((s.components || []).map((c) => c.abbr).join(", "))}</td></tr>`).join("")
    : `<tr><td colspan="2" class="muted">No salary structures yet — add one to assign salaries.</td></tr>`;

  return `
    ${addBtn}${addForm}${letterSettings}
    ${empBlock}
    ${assignForm}
    <h5 style="margin-top:18px;">Salary Structures</h5>
    ${structForm}
    <table class="erp-table"><thead><tr><th>Name</th><th>Components</th></tr></thead><tbody>${structRows}</tbody></table>`;
}

function renderHrPayrollTab() {
  const now = new Date();
  const runForm = hrCanManage() ? `
    <div class="hr-run-form" style="display:flex;gap:8px;align-items:flex-end;flex-wrap:wrap;margin-bottom:14px;">
      <label>Year<br><input id="hr-run-year" type="number" min="2000" max="2100" value="${now.getFullYear()}" style="width:90px;"></label>
      <label>Month<br>
        <select id="hr-run-month" style="width:120px;">
          ${Array.from({ length: 12 }, (_, i) => {
            const m = i + 1;
            const sel = m === now.getMonth() + 1 ? " selected" : "";
            return `<option value="${m}"${sel}>${m.toString().padStart(2, "0")}</option>`;
          }).join("")}
        </select>
      </label>
      <button class="primary" type="button" data-business-action="hr-run-payroll">Run Payroll</button>
    </div>` : `<p class="muted">Read-only access — payroll runs require an HR manager role.</p>`;

  const runRows = hrRuns.length ? hrRuns.map((r) => {
    const net = (r.totals && r.totals.net) || 0;
    return `
      <tr>
        <td>${escapeHtml(r.period || "")}</td>
        <td>${escapeHtml(String(r.employee_count ?? ""))}</td>
        <td class="num">${hrMoney(net)}</td>
        <td>${escapeHtml(String(r.journal_entry_id ?? "—"))}</td>
        <td><button class="secondary" type="button" data-business-action="hr-view-slips" data-run-id="${escapeHtml(r.run_id)}">View Slips</button></td>
      </tr>`;
  }).join("") : `<tr><td colspan="5" class="muted">No payroll runs yet.</td></tr>`;

  const slipsBlock = hrUi.selectedRunId ? `
    <h5 style="margin-top:18px;">Salary Slips — ${escapeHtml(hrUi.selectedRunId.slice(0, 8))}</h5>
    <table class="erp-table">
      <thead><tr><th>Employee</th><th>Period</th><th>Paid Days</th><th>LOP</th><th>Net Pay</th><th></th></tr></thead>
      <tbody>${
        hrUi.runSlips.length ? hrUi.runSlips.map((s) => `
          <tr>
            <td>${escapeHtml(s.employee_id || "")}</td>
            <td>${escapeHtml(s.period || "")}</td>
            <td class="num">${escapeHtml(String(s.payment_days ?? ""))}</td>
            <td class="num">${escapeHtml(String(s.lop_days ?? ""))}</td>
            <td class="num">${hrMoney(s.net_pay)}</td>
            <td><button class="secondary" type="button" data-business-action="hr-slip-pdf" data-slip-id="${escapeHtml(s.slip_id)}" data-period="${escapeHtml(s.period || "")}">PDF</button></td>
          </tr>`).join("") : `<tr><td colspan="6" class="muted">No slips for this run.</td></tr>`
      }</tbody>
    </table>` : "";

  return `
    ${runForm}
    <table class="erp-table">
      <thead><tr><th>Period</th><th>Employees</th><th>Net Payout</th><th>Journal #</th><th></th></tr></thead>
      <tbody>${runRows}</tbody>
    </table>
    ${slipsBlock}`;
}

function renderHrAnalyticsTab() {
  if (!hrAnalytics || !hrAnalytics.summary) {
    return `<p class="muted">No analytics yet — run payroll to populate the dashboard.</p>`;
  }
  const s = hrAnalytics.summary;
  const card = (label, value) => `
    <div class="kpi-card" style="padding:12px 16px;border:1px solid var(--border,#333);border-radius:8px;min-width:140px;">
      <div class="muted" style="font-size:12px;">${escapeHtml(label)}</div>
      <div style="font-size:20px;font-weight:600;">${value}</div>
    </div>`;
  const cards = `
    <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px;">
      ${card("Active Employees", escapeHtml(String(s.active_employees ?? 0)))}
      ${card("Exited", escapeHtml(String(s.exited_employees ?? 0)))}
      ${card("Latest Period", escapeHtml(s.latest_period || "—"))}
      ${card("Latest Net Payout", hrMoney(s.latest_net_payout))}
      ${card("Latest TDS", hrMoney(s.latest_tds))}
    </div>`;
  const labels = (hrAnalytics.labels || []);
  const tds = (hrAnalytics.datasets && hrAnalytics.datasets.tds_liability) || [];
  const net = (hrAnalytics.datasets && hrAnalytics.datasets.net_disbursed) || [];
  const trendRows = labels.map((lbl, i) => `
    <tr><td>${escapeHtml(lbl)}</td><td class="num">${hrMoney(net[i])}</td><td class="num">${hrMoney(tds[i])}</td></tr>`).join("");
  const trend = labels.length ? `
    <table class="erp-table">
      <thead><tr><th>Period</th><th>Net Disbursed</th><th>TDS Liability</th></tr></thead>
      <tbody>${trendRows}</tbody>
    </table>` : "";
  return cards + trend;
}

function renderHrLeaveTab() {
  const manage = hrCanManage();
  const typeForm = manage ? `
    <div style="display:flex;gap:8px;align-items:flex-end;flex-wrap:wrap;margin-bottom:10px;">
      <label>Code<br><input id="hr-lt-code" type="text" maxlength="20" style="width:90px;"></label>
      <label>Name<br><input id="hr-lt-name" type="text" maxlength="80" style="width:150px;"></label>
      <label style="display:flex;gap:4px;align-items:center;"><input id="hr-lt-lwp" type="checkbox"> Unpaid (LWP)</label>
      <button class="secondary" type="button" data-business-action="hr-create-leave-type">Add Type</button>
    </div>` : "";
  const typeRows = hrLeaveTypes.length
    ? hrLeaveTypes.map((t) => `<tr><td>${escapeHtml(t.code)}</td><td>${escapeHtml(t.name)}</td><td>${t.is_lwp ? "Unpaid" : "Paid"}</td></tr>`).join("")
    : `<tr><td colspan="3" class="muted">No leave types yet.</td></tr>`;

  const allocForm = manage && hrLeaveTypes.length ? `
    <div style="display:flex;gap:8px;align-items:flex-end;flex-wrap:wrap;margin:10px 0;">
      <label>Employee<br><select id="hr-alloc-emp" style="width:150px;">${hrEmployeeOptions()}</select></label>
      <label>Type<br><select id="hr-alloc-type" style="width:150px;">${hrLeaveTypeOptions()}</select></label>
      <label>Days<br><input id="hr-alloc-days" type="number" min="0" step="0.5" style="width:80px;"></label>
      <button class="secondary" type="button" data-business-action="hr-allocate-leave">Allocate</button>
    </div>` : "";

  const applyForm = manage && hrLeaveTypes.length ? `
    <div style="display:flex;gap:8px;align-items:flex-end;flex-wrap:wrap;margin:10px 0;">
      <label>Employee<br><select id="hr-leave-emp" style="width:150px;">${hrEmployeeOptions()}</select></label>
      <label>Type<br><select id="hr-leave-type" style="width:150px;">${hrLeaveTypeOptions()}</select></label>
      <label>From<br><input id="hr-leave-from" type="date"></label>
      <label>To<br><input id="hr-leave-to" type="date"></label>
      <button class="secondary" type="button" data-business-action="hr-apply-leave">Apply</button>
    </div>` : "";

  const appRows = hrLeaveApplications.length ? hrLeaveApplications.map((a) => {
    const actions = (manage && a.status === "pending")
      ? `<button class="secondary" type="button" data-business-action="hr-approve-leave" data-app-id="${escapeHtml(a.application_id)}">Approve</button>
         <button class="secondary" type="button" data-business-action="hr-reject-leave" data-app-id="${escapeHtml(a.application_id)}">Reject</button>`
      : "";
    return `<tr>
      <td>${escapeHtml(a.employee_id || "")}</td>
      <td>${escapeHtml(a.from_date || "")} → ${escapeHtml(a.to_date || "")}</td>
      <td class="num">${escapeHtml(String(a.days ?? ""))}</td>
      <td class="num">${escapeHtml(String(a.lop_days ?? ""))}</td>
      <td><span class="status-pill">${escapeHtml(a.status || "")}</span></td>
      <td>${actions}</td>
    </tr>`;
  }).join("") : `<tr><td colspan="6" class="muted">No leave applications.</td></tr>`;

  return `
    <h5>Leave Types</h5>
    ${typeForm}
    <table class="erp-table"><thead><tr><th>Code</th><th>Name</th><th>Kind</th></tr></thead><tbody>${typeRows}</tbody></table>
    ${allocForm}
    ${applyForm}
    <h5 style="margin-top:16px;">Leave Applications</h5>
    <table class="erp-table">
      <thead><tr><th>Employee</th><th>Dates</th><th>Days</th><th>LOP</th><th>Status</th><th></th></tr></thead>
      <tbody>${appRows}</tbody>
    </table>`;
}

function renderHrTaxTab() {
  const manage = hrCanManage();
  const form = manage ? `
    <div style="display:flex;gap:8px;align-items:flex-end;flex-wrap:wrap;margin-bottom:12px;">
      <label>Employee<br><select id="hr-decl-emp" style="width:150px;">${hrEmployeeOptions()}</select></label>
      <label>FY<br><input id="hr-decl-fy" type="text" placeholder="2025-26" style="width:90px;"></label>
      <label>Section<br><input id="hr-decl-section" type="text" placeholder="80C" style="width:90px;"></label>
      <label>Investment<br><input id="hr-decl-name" type="text" style="width:150px;"></label>
      <label>Declared ₹<br><input id="hr-decl-amount" type="number" min="0" style="width:110px;"></label>
      <button class="secondary" type="button" data-business-action="hr-create-declaration">Declare</button>
    </div>` : "";
  const rows = hrDeclarations.length ? hrDeclarations.map((d) => {
    const actions = (manage && d.status !== "approved" && d.status !== "rejected")
      ? `<button class="secondary" type="button" data-business-action="hr-approve-decl" data-decl-id="${escapeHtml(d.declaration_id)}" data-declared="${escapeHtml(String(d.declared_amount ?? "0"))}">Approve</button>
         <button class="secondary" type="button" data-business-action="hr-reject-decl" data-decl-id="${escapeHtml(d.declaration_id)}">Reject</button>`
      : "";
    return `<tr>
      <td>${escapeHtml(d.employee_id || "")}</td>
      <td>${escapeHtml(d.financial_year || "")}</td>
      <td>${escapeHtml(d.section_code || "")}</td>
      <td>${escapeHtml(d.investment_name || "")}</td>
      <td class="num">${hrMoney(d.declared_amount)}</td>
      <td class="num">${hrMoney(d.verified_amount)}</td>
      <td><span class="status-pill">${escapeHtml(d.status || "")}</span></td>
      <td>${actions}</td>
    </tr>`;
  }).join("") : `<tr><td colspan="8" class="muted">No declarations yet.</td></tr>`;
  return `
    ${form}
    <p class="muted" style="font-size:12px;">Proof files are uploaded via the API; this view manages declarations and HR verification.</p>
    <table class="erp-table">
      <thead><tr><th>Employee</th><th>FY</th><th>Section</th><th>Investment</th><th>Declared</th><th>Verified</th><th>Status</th><th></th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function renderHrFnfTab() {
  const manage = hrCanManage();
  const form = manage ? `
    <div style="display:flex;gap:8px;align-items:flex-end;flex-wrap:wrap;margin-bottom:12px;">
      <label>Employee<br><select id="hr-fnf-emp" style="width:150px;">${hrEmployeeOptions()}</select></label>
      <label>Last Working Day<br><input id="hr-fnf-lwd" type="date"></label>
      <label>Last Basic ₹<br><input id="hr-fnf-basic" type="number" min="0" style="width:110px;"></label>
      <label>Unused Leaves<br><input id="hr-fnf-leaves" type="number" min="0" step="0.5" style="width:90px;"></label>
      <label>Notice Shortfall<br><input id="hr-fnf-notice" type="number" min="0" style="width:90px;"></label>
      <button class="secondary" type="button" data-business-action="hr-create-fnf">Compute F&amp;F</button>
    </div>` : "";
  const rows = hrFnf.length ? hrFnf.map((f) => {
    const s = f.settlement || {};
    let actions = `<button class="secondary" type="button" data-business-action="hr-fnf-pdf" data-fnf-id="${escapeHtml(f.fnf_id)}">PDF</button>`;
    if (manage && f.status === "draft") actions += ` <button class="secondary" type="button" data-business-action="hr-fnf-approve" data-fnf-id="${escapeHtml(f.fnf_id)}">Approve</button>`;
    if (manage && f.status === "approved") actions += ` <button class="secondary" type="button" data-business-action="hr-fnf-pay" data-fnf-id="${escapeHtml(f.fnf_id)}">Mark Paid</button>`;
    return `<tr>
      <td>${escapeHtml(f.employee_id || "")}</td>
      <td>${escapeHtml(f.last_working_day || "")}</td>
      <td class="num">${escapeHtml(String(f.completed_years ?? ""))}</td>
      <td class="num">${hrMoney(s.gratuity)}</td>
      <td class="num">${hrMoney(s.net_settlement)}</td>
      <td><span class="status-pill">${escapeHtml(f.status || "")}</span></td>
      <td>${actions}</td>
    </tr>`;
  }).join("") : `<tr><td colspan="7" class="muted">No settlements yet.</td></tr>`;
  return `
    ${form}
    <table class="erp-table">
      <thead><tr><th>Employee</th><th>Last Day</th><th>Years</th><th>Gratuity</th><th>Net Settlement</th><th>Status</th><th></th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function renderHrTab() {
  if (hrUi.tab === "payroll") return renderHrPayrollTab();
  if (hrUi.tab === "leave") return renderHrLeaveTab();
  if (hrUi.tab === "tax") return renderHrTaxTab();
  if (hrUi.tab === "fnf") return renderHrFnfTab();
  if (hrUi.tab === "analytics") return renderHrAnalyticsTab();
  return renderHrEmployeesTab();
}

export function renderHrWorkspace() {
  let body;
  if (!hrAccess) {
    body = `<p class="muted">Loading HR workspace…</p>`;
  } else if (!hrAccess.entitled) {
    if (hrAccess.available === false) {
      body = `<div class="module-state warn"><strong>HR &amp; Payroll is not active</strong><span>The HR add-on has not been provisioned for your organization. Contact your platform administrator to enable it.</span></div>`;
    } else if (hrAccess.can_enable) {
      // Provisioned but the tenant hasn't switched it on yet — let an admin do it here.
      body = `
        <div class="module-state warn">
          <strong>HR &amp; Payroll is provisioned but turned off</strong>
          <span>Enable it to start managing employees, payroll, leave and settlements.</span>
        </div>
        <button class="primary" type="button" data-business-action="hr-enable" style="margin-top:10px;">Enable HR &amp; Payroll</button>`;
    } else {
      body = `<div class="module-state warn"><strong>HR &amp; Payroll is not active</strong><span>The HR module is turned off. Ask an administrator to enable it in MitraBooks Settings.</span></div>`;
    }
  } else {
    body = `
      ${hrUi.error ? `<div class="module-state danger"><span>${escapeHtml(hrUi.error)}</span></div>` : ""}
      <div class="erp-tabs" style="display:flex;gap:6px;margin-bottom:14px;flex-wrap:wrap;">
        ${hrTabButton("employees", "Employees")}
        ${hrTabButton("payroll", "Payroll")}
        ${hrTabButton("leave", "Leave")}
        ${hrTabButton("tax", "Form 12BB")}
        ${hrTabButton("fnf", "Full & Final")}
        ${hrTabButton("analytics", "Analytics")}
      </div>
      <div class="erp-tab-content">${renderHrTab()}</div>`;
  }
  return `
    <div class="verification-panel erp-workspace-panel">
      <div class="preview-heading compact">
        <div><h4>HR &amp; Payroll</h4><p>Employees, payroll runs, and statutory analytics.</p></div>
        <button class="secondary" type="button" data-business-action="hr-refresh">Refresh</button>
      </div>
      ${body}
    </div>`;
}
