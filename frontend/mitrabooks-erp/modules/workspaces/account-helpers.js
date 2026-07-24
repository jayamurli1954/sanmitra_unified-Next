// ====================================================================
// SECTION: ACCOUNT HELPERS + DATA HEALTH + BOOKS HEALTH WIDGET
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initAccountHelpers(...).
// Context helpers (platform owner / business tenant) remain in app.js.
// ====================================================================

/** @type {Record<string, Function> | null} */
let deps = null;

export function initAccountHelpers(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initAccountHelpers() must be called before using account helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function getLastBusinessAccounts() { return requireDeps().getLastBusinessAccounts(); }
function getLastBusinessAccountsResult() { return requireDeps().getLastBusinessAccountsResult(); }
function getLastBusinessParties() { return requireDeps().getLastBusinessParties(); }
function getLastBusinessPartiesResult() { return requireDeps().getLastBusinessPartiesResult(); }
function getLastModuleContext() { return requireDeps().getLastModuleContext(); }
function getLastAccountingDrilldown() { return requireDeps().getLastAccountingDrilldown(); }
function getLastBusinessDataHealth() { return requireDeps().getLastBusinessDataHealth(); }
function getBusinessDataHealthLoadInFlight() { return requireDeps().getBusinessDataHealthLoadInFlight(); }
function loadBusinessDataHealth() { return requireDeps().loadBusinessDataHealth(); }
function hasTrustedSession() { return requireDeps().hasTrustedSession(); }
function enabledModuleKeys(context) { return requireDeps().enabledModuleKeys(context); }
function isBusinessTenantContext(context) { return requireDeps().isBusinessTenantContext(context); }

const MITRABOOKS_FALLBACK_ACCOUNTS = [
  { account_id: 11001, account_code: "11001", account_name: "Cash in Hand", account_type: "asset" },
  { account_id: 11010, account_code: "11010", account_name: "Bank Account", account_type: "asset" },
  { account_id: 12001, account_code: "12001", account_name: "Sundry Debtors", account_type: "asset" },
  { account_id: 13002, account_code: "13002", account_name: "Advance to Suppliers", account_type: "asset" },
  { account_id: 21001, account_code: "21001", account_name: "Sundry Creditors", account_type: "liability" },
  { account_id: 24001, account_code: "24001", account_name: "Advance from Customers", account_type: "liability" },
  { account_id: 41001, account_code: "41001", account_name: "Sales", account_type: "income" },
  { account_id: 41002, account_code: "41002", account_name: "Service Income", account_type: "income" },
  { account_id: 53004, account_code: "53004", account_name: "Office Expense", account_type: "expense" },
  { account_id: 54001, account_code: "54001", account_name: "Bank Charges", account_type: "expense" },
];

export function normalizeBusinessAccount(acc) {
  const id = acc.account_id
    ?? acc.id
    ?? acc.accountId
    ?? acc.accountID
    ?? acc.ledger_id
    ?? acc.ledgerId
    ?? acc._id
    ?? acc.account_code
    ?? acc.code
    ?? "";
  const code = acc.account_code
    ?? acc.code
    ?? acc.accountCode
    ?? acc.ledger_code
    ?? acc.ledgerCode
    ?? acc.gl_code
    ?? acc.glCode
    ?? acc.number
    ?? acc.account_number
    ?? id
    ?? "";
  const name = acc.account_name
    ?? acc.name
    ?? acc.accountName
    ?? acc.ledger_name
    ?? acc.ledgerName
    ?? acc.title
    ?? "";
  return {
    id: String(id),
    code: String(code),
    name: String(name),
  };
}

export function businessAccountLabel(account) {
  return `${account.code}${account.name ? " - " + account.name : ""}`.trim();
}

export function businessAccountsForSelection() {
  const loaded = Array.isArray(getLastBusinessAccounts()) ? getLastBusinessAccounts() : [];
  const source = loaded.length > 0 ? loaded : MITRABOOKS_FALLBACK_ACCOUNTS;
  return source
    .map(normalizeBusinessAccount)
    .filter((acc) => acc.id && (acc.code || acc.name));
}

export function hasLoadedBusinessAccounts() {
  return Array.isArray(getLastBusinessAccounts()) && getLastBusinessAccounts().length > 0;
}

export function findBusinessAccountById(accountId) {
  return businessAccountsForSelection()
    .find((acc) => String(acc.id) === String(accountId)) || null;
}

export function accountIdForVoucherPayload(account) {
  if (!account || !hasLoadedBusinessAccounts()) return null;
  const parsed = Number(account.id);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

export function populateVoucherAccountSelect(select, selectedId = "") {
  if (!select) return;
  const accounts = businessAccountsForSelection();
  select.innerHTML = `<option value="">Select account code</option>`;
  accounts.forEach((acc) => {
    const option = document.createElement("option");
    option.value = acc.id;
    option.textContent = businessAccountLabel(acc);
    if (String(selectedId) === acc.id) {
      option.selected = true;
    }
    select.appendChild(option);
  });
}

export function populateAccountPickerSelect(fieldId, accounts, selectedId = "") {
  const select = document.querySelector(`.account-picker-select[data-field-id="${fieldId}"]`);
  if (!select) return;
  const rows = Array.isArray(accounts) && accounts.length > 0 ? accounts : businessAccountsForSelection();
  const currentValue = selectedId || select.value || "";
  select.innerHTML = `<option value="">${rows.length === 0 ? "No matching account code" : "Select account code"}</option>`;
  rows.forEach((account) => {
    const normalized = normalizeBusinessAccount(account);
    const option = document.createElement("option");
    option.value = normalized.id;
    option.textContent = businessAccountLabel(normalized);
    if (String(currentValue) === String(normalized.id)) {
      option.selected = true;
    }
    select.appendChild(option);
  });
}

export function refreshVoucherAccountDatalist() {
  const datalist = document.getElementById("business-voucher-account-options");
  if (!datalist) return;
  const accounts = businessAccountsForSelection();
  datalist.innerHTML = "";
  accounts.forEach((acc) => {
    const option = document.createElement("option");
    option.value = businessAccountLabel(acc);
    datalist.appendChild(option);
  });
}

export function updateVoucherAccountsStatus() {
  const status = document.getElementById("business-voucher-accounts-status");
  if (!status) return;
  const count = Array.isArray(getLastBusinessAccounts()) ? getLastBusinessAccounts().length : 0;
  status.textContent = "";
  if (count <= 0) {
    status.textContent = "No tenant chart loaded. Showing default MitraBooks account codes until the chart of accounts API returns rows.";
    return;
  }
  const message = document.createElement("span");
  message.textContent = `${count} account(s) loaded. Examples: `;
  status.appendChild(message);
  const preview = document.createElement("strong");
  preview.textContent = getLastBusinessAccounts()
    .slice(0, 3)
    .map((acc) => businessAccountLabel(normalizeBusinessAccount(acc)))
    .filter(Boolean)
    .join(" | ");
  status.appendChild(preview);
}

export function refreshVoucherAccountSelects() {
  refreshVoucherAccountDatalist();
  updateVoucherAccountsStatus();
  document.querySelectorAll(".voucher-account-select").forEach((select) => {
    populateVoucherAccountSelect(select, select.value);
  });
  document.querySelectorAll(".account-picker-select").forEach((select) => {
    populateVoucherAccountSelect(select, select.value);
  });
}

export function accountRowsFromPayload(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.items)) return payload.items;
  if (Array.isArray(payload?.accounts)) return payload.accounts;
  if (Array.isArray(payload?.data)) return payload.data;
  if (Array.isArray(payload?.rows)) return payload.rows;
  if (Array.isArray(payload?.result)) return payload.result;
  if (Array.isArray(payload?.data?.items)) return payload.data.items;
  if (Array.isArray(payload?.data?.accounts)) return payload.data.accounts;
  if (Array.isArray(payload?.data?.rows)) return payload.data.rows;
  if (Array.isArray(payload?.result?.items)) return payload.result.items;
  if (Array.isArray(payload?.result?.accounts)) return payload.result.accounts;
  if (Array.isArray(payload?.payload?.items)) return payload.payload.items;
  if (Array.isArray(payload?.payload?.accounts)) return payload.payload.accounts;
  return [];
}

export function normalizedAccountRows(rows = getLastBusinessAccounts()) {
  return Array.isArray(rows) ? rows.map((account) => {
    const normalized = normalizeBusinessAccount(account);
    return {
      ...normalized,
      type: String(account.account_type ?? account.type ?? "").toLowerCase(),
      nameKey: normalized.name.toLowerCase(),
    };
  }).filter((account) => account.id || account.code || account.name) : [];
}

export function hasBusinessAccount(matchNames, matchTypes = []) {
  const names = matchNames.map((name) => name.toLowerCase());
  const types = matchTypes.map((type) => type.toLowerCase());
  return normalizedAccountRows().some((account) => {
    const nameMatch = names.some((name) => account.nameKey === name || account.nameKey.includes(name));
    const typeMatch = types.length === 0 || types.includes(account.type);
    return nameMatch && typeMatch;
  });
}

export function countPartiesMissingGstin(rows = getLastBusinessParties()) {
  if (!Array.isArray(rows) || rows.length === 0) return 0;
  return rows.filter((row) => !String(row.gstin || "").trim()).length;
}

export function dataHealthItem(label, ok, copy) {
  return `
    <li class="${ok ? "ok" : "warn"}">
      <span>${escapeHtml(label)}</span>
      <strong>${ok ? "Ready" : "Needs attention"}</strong>
      <small>${escapeHtml(copy)}</small>
    </li>
  `;
}

export function dataHealthAction(priority, title, detail, actionText) {
  return `
    <li>
      <span>${escapeHtml(priority)}</span>
      <strong>${escapeHtml(title)}</strong>
      <small>${escapeHtml(detail)}</small>
      <em>${escapeHtml(actionText)}</em>
    </li>
  `;
}

export function renderBusinessDataHealthIssueList(dataHealth) {
  const issues = Array.isArray(dataHealth?.issues) ? dataHealth.issues : [];
  if (issues.length === 0) return "";
  return `
    <div class="erp-health-actions data-health-remediation">
      <div>
        <h5>Remediation Queue</h5>
        <p>Source-backed issues with direct links to the workspace where the record can be reviewed.</p>
      </div>
      <ol>
        ${issues.slice(0, 8).map((issue) => {
          const workspace = issue.workspace || "overview";
          return `
            <li data-data-health-issue="${escapeHtml(issue.issue_id || "")}">
              <span>${escapeHtml(issue.severity || "issue")}</span>
              <strong>${escapeHtml(issue.title || "Data-health issue")}</strong>
              <small>${escapeHtml(issue.entity_label || issue.description || "Affected record")}</small>
              <em>${escapeHtml(issue.action || "Review the affected record.")}</em>
              <button
                class="secondary"
                type="button"
                data-business-action="workspace-view"
                data-workspace-view="${escapeHtml(workspace)}"
                data-data-health-rule="${escapeHtml(issue.rule_key || "")}"
              >${escapeHtml(issue.action_label || "Open Workspace")}</button>
            </li>
          `;
        }).join("")}
      </ol>
    </div>
  `;
}

export function renderBusinessDataHealthActions(state) {
  const actions = [];
  const backendRules = Array.isArray(getLastBusinessDataHealth()?.rules) ? getLastBusinessDataHealth().rules : [];

  backendRules
    .filter((rule) => rule.status !== "pass")
    .slice(0, 5)
    .forEach((rule) => {
      actions.push(dataHealthAction(
        rule.severity || "Rule",
        rule.label || rule.key || "Data-health rule",
        rule.detail || `${rule.count || 0} issue(s) found.`,
        rule.action || "Review the affected records."
      ));
    });

  if (!state.isBusinessTenant || !state.hasBusinessModule) {
    actions.push(dataHealthAction(
      "Access",
      "Fix MitraBooks tenant context",
      "Business workspaces need organization_type=BUSINESS and the business module enabled.",
      "Review tenant setup before adding more business records."
    ));
  }
  if (!state.hasAccountingModule || !state.accountsLoaded) {
    actions.push(dataHealthAction(
      "Setup",
      "Load the chart of accounts",
      state.accountsBlocked ? `Accounts request returned HTTP ${state.accountsStatus}.` : "The voucher form needs tenant-owned cash, bank, revenue, and expense ledgers.",
      "Open Accounting and confirm the business chart exists."
    ));
  }
  if (state.accountsLoaded && !state.hasCashBank) {
    actions.push(dataHealthAction(
      "Accounts",
      "Add cash or bank account",
      "Receipt, payment, and contra vouchers need an asset-side cash or bank ledger.",
      "Create or map Cash in Hand / Bank Account before payment workflows."
    ));
  }
  if (state.accountsLoaded && !state.hasRevenue) {
    actions.push(dataHealthAction(
      "Accounts",
      "Add revenue account",
      "Sales and service postings need an income/revenue ledger before invoice workflows are enabled.",
      "Create or map Sales / Service Income."
    ));
  }
  if (state.accountsLoaded && !state.hasExpense) {
    actions.push(dataHealthAction(
      "Accounts",
      "Add expense account",
      "Purchase and expense postings need an expense ledger before purchase workflows are enabled.",
      "Create or map Purchases / Office Expense / Rent Expense."
    ));
  }
  if (state.partiesLoaded && state.partiesMissingGstin > 0) {
    actions.push(dataHealthAction(
      "Parties",
      "Complete party GSTINs",
      `${state.partiesMissingGstin} visible party record(s) are missing GSTIN.`,
      "Open Parties and update GSTIN where the party is registered."
    ));
  }
  if (state.partiesBlocked) {
    actions.push(dataHealthAction(
      "Parties",
      "Reload party sample",
      "The dashboard could not read the visible party sample used for GSTIN checks.",
      "Open Parties after confirming the business module is enabled."
    ));
  }
  if (!state.drilldownReady) {
    actions.push(dataHealthAction(
      "Reports",
      "Verify voucher drill-down",
      "Accounting report drill-down must load before reports can be trusted for business review.",
      "Open Accounting and retry after posting a balanced voucher."
    ));
  }

  if (actions.length === 0) {
    actions.push(dataHealthAction(
      "Ready",
      "Core accounting data is ready",
      "Tenant context, modules, chart of accounts, party GSTIN sample, and drill-down are available.",
      "Continue with parties and balanced vouchers; keep GST/inventory depth deferred."
    ));
  }

  return `
    <div class="erp-health-actions">
      <div>
        <h5>Action Queue</h5>
        <p>Concrete next fixes before expanding into sales, purchases, GST, or inventory.</p>
      </div>
      <ol>${actions.join("")}</ol>
    </div>
  `;
}

export function getBusinessHealthState() {
  const modules = enabledModuleKeys();
  const organizationType = String(getLastModuleContext()?.organization_type || "unknown").toUpperCase();
  const tenantId = getLastModuleContext()?.tenant_id || "not loaded";
  const accountsLoaded = Array.isArray(getLastBusinessAccounts()) && getLastBusinessAccounts().length > 0;
  const accountsBlocked = getLastBusinessAccountsResult() && !getLastBusinessAccountsResult().ok;
  const accountsStatus = getLastBusinessAccountsResult()?.status || "unknown";
  const partiesLoaded = Array.isArray(getLastBusinessParties()) && getLastBusinessParties().length > 0;
  const partiesBlocked = getLastBusinessPartiesResult() && !getLastBusinessPartiesResult().ok;
  const partiesMissingGstin = countPartiesMissingGstin();
  const partiesGstinReady = !partiesBlocked && (!partiesLoaded || partiesMissingGstin === 0);
  const partiesGstinCopy = partiesBlocked
    ? `Parties request returned HTTP ${getLastBusinessPartiesResult().status}.`
    : partiesLoaded
      ? `${partiesMissingGstin} visible party record(s) missing GSTIN.`
      : "No visible parties yet; GSTIN checks start after party creation.";
  const drilldownReady = getLastAccountingDrilldown() && getLastAccountingDrilldown().ok !== false;
  const voucherCount = getLastAccountingDrilldown()?.summary?.voucher_count ?? 0;
  const healthState = {
    isBusinessTenant: isBusinessTenantContext(),
    hasBusinessModule: modules.has("business"),
    hasAccountingModule: modules.has("accounting"),
    accountsLoaded,
    accountsBlocked,
    accountsStatus,
    hasCashBank: hasBusinessAccount(["Cash in Hand", "Bank Account"], ["asset"]),
    hasRevenue: hasBusinessAccount(["Sales", "Service Income"], ["income", "revenue"]),
    hasExpense: hasBusinessAccount(["Purchases", "Office Expense", "Rent Expense"], ["expense"]),
    partiesLoaded,
    partiesBlocked,
    partiesMissingGstin,
    partiesGstinReady,
    drilldownReady,
  };

  return {
    healthState,
    organizationType,
    tenantId,
    partiesGstinCopy,
    voucherCount,
  };
}

export function renderBusinessDataHealthPanel() {
  const { healthState, organizationType, tenantId, partiesGstinCopy, voucherCount } = getBusinessHealthState();
  if (hasTrustedSession() && !getLastBusinessDataHealth() && !getBusinessDataHealthLoadInFlight()) {
    setTimeout(() => { loadBusinessDataHealth(); }, 0);
  }
  const dataHealth = getLastBusinessDataHealth();
  const score = Number(dataHealth?.score ?? 0);
  const scoreLabel = dataHealth ? `${score}/100` : "Loading";
  const gradeLabel = dataHealth?.grade ? `Grade ${dataHealth.grade}` : "backend score";
  const backendRules = Array.isArray(dataHealth?.rules) ? dataHealth.rules : [];

  const checks = [
    dataHealthItem("Data Health Score", !!dataHealth && score >= 75, `${scoreLabel}; ${gradeLabel}`),
    dataHealthItem("Business tenant context", healthState.isBusinessTenant, `organization_type=${organizationType}; tenant=${tenantId}`),
    dataHealthItem("Business module enabled", healthState.hasBusinessModule, "Required before parties and vouchers can return tenant data."),
    dataHealthItem("Accounting module enabled", healthState.hasAccountingModule, "Required for chart of accounts and drill-down reports."),
    dataHealthItem("Chart of accounts loaded", healthState.accountsLoaded, healthState.accountsBlocked ? `Accounts request returned HTTP ${getLastBusinessAccountsResult().status}.` : `${getLastBusinessAccounts().length} account(s) available.`),
    dataHealthItem("Cash and bank accounts", healthState.hasCashBank, "Required for receipt, payment, and contra voucher posting."),
    dataHealthItem("Revenue / income accounts", healthState.hasRevenue, "Required before sales or service income postings are introduced."),
    dataHealthItem("Expense accounts", healthState.hasExpense, "Required for purchase and expense postings."),
    dataHealthItem("Party GSTIN sample", healthState.partiesGstinReady, partiesGstinCopy),
    dataHealthItem("Voucher drill-down", healthState.drilldownReady, `Current period shows ${voucherCount} posted voucher(s).`),
  ];
  backendRules.forEach((rule) => {
    checks.push(dataHealthItem(
      rule.label || rule.key || "Data-health rule",
      rule.status === "pass",
      `${rule.count || 0} issue(s); impact ${rule.score_impact || 0}`
    ));
  });

  return `
    <section class="erp-health-panel" aria-label="MitraBooks data health">
      <div class="preview-heading compact">
        <div>
          <h4>Data Health</h4>
          <p>${escapeHtml(dataHealth?.summary || "Tenant, module, chart, and drill-down readiness for the current MitraBooks context.")}</p>
        </div>
        <span class="pill ${dataHealth?.status === "ready" ? "ok" : "warn"}">${escapeHtml(scoreLabel)}</span>
      </div>
      <ul class="erp-health-list">${checks.join("")}</ul>
      ${renderBusinessDataHealthIssueList(dataHealth)}
      ${renderBusinessDataHealthActions(healthState)}
    </section>
  `;
}

export function updateHealthWidget(percentage = null, status = "Run checks", tone = "pending") {
  const widget = document.getElementById("books-health-widget");
  const healthPercent = document.getElementById("health-percent-text");
  const healthBar = document.getElementById("health-circle-bar");
  const healthStatus = document.querySelector(".health-text span");
  const safePercentage = Number.isFinite(Number(percentage))
    ? Math.max(0, Math.min(100, Number(percentage)))
    : null;

  if (widget) {
    widget.classList.remove("pending", "warn", "ok");
    widget.classList.add(tone);
  }
  if (healthPercent) {
    healthPercent.textContent = safePercentage === null ? "--" : `${safePercentage}%`;
  }
  if (healthBar) {
    const dasharray = `${safePercentage ?? 0}, 100`;
    healthBar.setAttribute("stroke-dasharray", dasharray);
  }
  if (healthStatus) {
    healthStatus.textContent = status;
  }
}

export function refreshBooksHealthWidget() {
  if (!getLastModuleContext()) {
    updateHealthWidget(null, "Run checks", "pending");
    return;
  }

  const { healthState } = getBusinessHealthState();
  const checks = [
    healthState.isBusinessTenant,
    healthState.hasBusinessModule,
    healthState.hasAccountingModule,
    healthState.accountsLoaded,
    healthState.hasCashBank,
    healthState.hasRevenue,
    healthState.hasExpense,
    healthState.partiesGstinReady,
    healthState.drilldownReady,
  ];
  const passed = checks.filter(Boolean).length;
  const percentage = Math.round((passed / checks.length) * 100);
  const ready = passed === checks.length;
  const blocked = healthState.accountsBlocked || healthState.partiesBlocked;
  updateHealthWidget(
    percentage,
    ready ? "Ready" : blocked ? "Needs review" : "In progress",
    ready ? "ok" : "warn"
  );
}

export function initializeHealthWidget() {
  refreshBooksHealthWidget();
}

