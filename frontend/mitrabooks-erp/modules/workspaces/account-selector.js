// ====================================================================
// SECTION: ACCOUNT SELECTOR COMPONENT
// Extracted from app.js per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
// Pure move: logic unchanged. Shell deps injected via initAccountSelector(...).
// Mixed document listeners (payment-allocation + voucher amounts) remain in app.js.
// ====================================================================

/** @type {Record<string, Function> | null} */
let deps = null;

export function initAccountSelector(injected) {
  deps = injected;
}

function requireDeps() {
  if (!deps) {
    throw new Error("initAccountSelector() must be called before using account selector helpers");
  }
  return deps;
}

function escapeHtml(value) { return requireDeps().escapeHtml(value); }
function businessAccountsForSelection() { return requireDeps().businessAccountsForSelection(); }
function getLastBusinessAccounts() { return requireDeps().getLastBusinessAccounts(); }
function filterBusinessAccountsByQuery(query) { return requireDeps().filterBusinessAccountsByQuery(query); }
function populateAccountPickerSelect(fieldId, accounts, selectedId = "") {
  return requireDeps().populateAccountPickerSelect(fieldId, accounts, selectedId);
}
function normalizeBusinessAccount(acc) { return requireDeps().normalizeBusinessAccount(acc); }
function updateVoucherBalance() { return requireDeps().updateVoucherBalance(); }

export function renderAccountSelectorComponent(fieldId, selectedAccountId = null) {
  const accounts = businessAccountsForSelection();
  const selectedAccount = accounts.find((acc) => String(acc.id) === String(selectedAccountId));
  const usingFallbackAccounts = !Array.isArray(getLastBusinessAccounts()) || getLastBusinessAccounts().length === 0;

  const displayText = selectedAccount
    ? `${selectedAccount.code} - ${selectedAccount.name}`
    : "";

  return `
    <div class="account-selector-component" data-field-id="${escapeHtml(fieldId)}">
      <span class="account-selector-caption">Account code dropdown</span>
      <div class="account-input-wrapper">
        <select
          class="account-picker-select"
          data-field-id="${escapeHtml(fieldId)}"
          aria-label="Select account"
        >
          <option value="">Select account code</option>
          ${accounts.map((account) => `
            <option value="${escapeHtml(account.id)}" ${String(account.id) === String(selectedAccountId || "") ? "selected" : ""}>
              ${escapeHtml(`${account.code} - ${account.name}`)}
            </option>
          `).join("")}
        </select>
        <input
          type="text"
          class="account-search-input"
          data-field-id="${escapeHtml(fieldId)}"
          placeholder="Type 3+ characters to filter account codes"
          value="${escapeHtml(displayText)}"
          autocomplete="off"
        >
        <input
          type="hidden"
          class="account-id-input"
          data-field-id="${escapeHtml(fieldId)}"
          value="${escapeHtml(selectedAccountId || "")}"
        >
      </div>
      <ul class="account-suggestions" data-field-id="${escapeHtml(fieldId)}" hidden>
        <!-- Populated on input -->
      </ul>
      ${usingFallbackAccounts ? `<p class="account-selector-note">Using default account codes. Load tenant chart of accounts to replace these defaults.</p>` : ""}
    </div>
  `;
}

export function updateAccountSuggestions(fieldId) {
  const input = document.querySelector(`.account-search-input[data-field-id="${fieldId}"]`);
  const suggestionsList = document.querySelector(`.account-suggestions[data-field-id="${fieldId}"]`);

  if (!input || !suggestionsList) return;

  const query = input.value.trim();
  const matches = filterBusinessAccountsByQuery(query);

  if (query.length < 3) {
    populateAccountPickerSelect(fieldId, businessAccountsForSelection());
    suggestionsList.hidden = true;
    suggestionsList.innerHTML = "";
    return;
  }

  populateAccountPickerSelect(fieldId, matches);

  if (matches.length === 0) {
    suggestionsList.hidden = false;
    suggestionsList.innerHTML = `<li class="account-suggestion-empty">No matching account code</li>`;
    return;
  }

  suggestionsList.innerHTML = matches
    .map((acc) => {
      const normalized = normalizeBusinessAccount(acc);
      const displayText = `${normalized.code} - ${normalized.name}`;
      return `
        <li
          class="account-suggestion-item"
          data-account-id="${escapeHtml(normalized.id)}"
          data-field-id="${escapeHtml(fieldId)}"
          title="${escapeHtml(displayText)}"
        >
          <strong>${escapeHtml(normalized.code)}</strong>
          <span>${escapeHtml(normalized.name)}</span>
        </li>
      `;
    })
    .join("");

  suggestionsList.hidden = false;
}

export function selectAccountFromSuggestion(suggestionElement) {
  const fieldId = suggestionElement.getAttribute("data-field-id");
  const accountId = suggestionElement.getAttribute("data-account-id");

  selectBusinessAccount(fieldId, accountId);
}

export function selectBusinessAccount(fieldId, accountId) {
  const account = businessAccountsForSelection()
    .find((acc) => String(acc.id) === String(accountId));
  if (!account) return;

  const input = document.querySelector(`.account-search-input[data-field-id="${fieldId}"]`);
  const idInput = document.querySelector(`.account-id-input[data-field-id="${fieldId}"]`);
  const select = document.querySelector(`.account-picker-select[data-field-id="${fieldId}"]`);
  const suggestionsList = document.querySelector(`.account-suggestions[data-field-id="${fieldId}"]`);

  if (input) {
    input.value = `${account.code} - ${account.name}`;
  }
  if (idInput) {
    idInput.value = account.id;
  }
  if (select) {
    select.value = account.id;
  }
  if (suggestionsList) {
    suggestionsList.hidden = true;
    suggestionsList.innerHTML = "";
  }

  // Trigger balance check if this is a voucher form
  updateVoucherBalance();
}

export function closeAllAccountSuggestions() {
  document.querySelectorAll(".account-suggestions").forEach((list) => {
    list.hidden = true;
  });
}

