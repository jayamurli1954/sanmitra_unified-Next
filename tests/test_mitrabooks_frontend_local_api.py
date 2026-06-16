from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_static_frontend_prefers_local_backend_before_staging_meta() -> None:
    api_client = REPO_ROOT / "frontend" / "shared" / "api-client.js"
    source = api_client.read_text(encoding="utf-8")

    local_default = "if (isLocalFrontendHost()) return LOCAL_API_BASE_URL;"
    staging_meta = "document.querySelector(\"meta[name='sanmitra-api-base-url']\")"

    assert source.index(local_default) < source.index(staging_meta)


def test_mitrabooks_shell_uses_current_asset_cache_version() -> None:
    index_html = REPO_ROOT / "frontend" / "mitrabooks-erp" / "index.html"
    service_worker = REPO_ROOT / "frontend" / "service-worker.js"

    index_source = index_html.read_text(encoding="utf-8")
    worker_source = service_worker.read_text(encoding="utf-8")

    assert "app.js?v=mitrabooks-erp-v32" in index_source
    assert "pwa-shell.js?v=mitrabooks-erp-v10" in index_source
    assert "app-shell.css?v=mitrabooks-erp-v10" in index_source
    assert "CACHE_NAME = 'mitrabooks-erp-v16'" in worker_source


def test_mitrabooks_login_invite_page_inline_script_parses() -> None:
    login_html = REPO_ROOT / "frontend" / "mitrabooks-erp" / "login.html"
    source = login_html.read_text(encoding="utf-8")
    script = source.split("<script>", 1)[1].split("</script>", 1)[0]

    result = subprocess.run(
        ["node", "-e", f"new Function({script!r});"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "/ca/invite/" in script
    assert "/preview" not in script


def test_local_frontend_server_disables_browser_cache() -> None:
    server_source = (REPO_ROOT / "scripts" / "serve_frontends.py").read_text(encoding="utf-8")

    assert "class LocalFrontendHandler(SimpleHTTPRequestHandler)" in server_source
    assert '"Cache-Control", "no-store, no-cache, must-revalidate, max-age=0"' in server_source
    assert "partial(LocalFrontendHandler" in server_source


def test_pwa_shell_unregisters_service_workers_on_localhost() -> None:
    pwa_source = (REPO_ROOT / "frontend" / "shared" / "pwa-shell.js").read_text(encoding="utf-8")

    assert 'host === "127.0.0.1"' in pwa_source
    assert "registration.unregister()" in pwa_source
    assert "caches.delete(key)" in pwa_source


def test_mitrabooks_dashboard_preview_closes_before_business_module() -> None:
    app_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")
    start = app_source.index("function renderDashboardPreview(config)")
    marker = app_source.index("// ========== Business Module: Party Master ==========", start)
    preview_block = app_source[start:marker].rstrip()

    assert preview_block.endswith("}\n}")


def test_business_workspace_menu_renders_main_preview_directly() -> None:
    app_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")
    start = app_source.index("function setBusinessWorkspace(workspace)")
    end = app_source.index("function syncBusinessNavActiveState()", start)
    workspace_switcher = app_source[start:end]

    assert 'workspace === "overview"' in workspace_switcher
    assert "renderBusinessWorkspace()" in workspace_switcher
    assert "refreshCurrentAccountingDrilldown();" in workspace_switcher
    assert 'document.getElementById("context-cards")' not in workspace_switcher


def test_mitrabooks_accounting_refresh_preserves_accounting_panel() -> None:
    app_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")
    start = app_source.index("async function refreshCurrentAccountingDrilldown()")
    end = app_source.index("async function applyAccountingDrilldownFilters()", start)
    refresh_block = app_source[start:end]

    assert 'currentExperience === "mitrabooks" && activeBusinessWorkspace === "accounting"' in refresh_block
    assert "dashboardPreview.innerHTML = renderAccountingDrilldownPanel();" in refresh_block


def test_business_party_payload_matches_backend_schema() -> None:
    app_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")
    create_start = app_source.index("async function createBusinessParty(data)")
    create_end = app_source.index("async function updateBusinessParty", create_start)
    create_block = app_source[create_start:create_end]
    update_end = app_source.index("async function deactivateBusinessParty", create_end)
    update_block = app_source[create_end:update_end]

    assert "party_name: data.name" in create_block
    assert "opening_balance: String(Number(data.opening_balance) || 0)" not in create_block
    assert "opening_balance_paise" not in create_block
    assert "party_name: data.name" in update_block
    assert "opening_balance_paise" not in update_block
    assert '/api/v1/business/parties/${encodeURIComponent(partyId)}/deactivate' in app_source
    deactivate_start = app_source.index("async function deactivateBusinessParty")
    deactivate_end = app_source.index("function openBusinessCreatePartyDialog", deactivate_start)
    deactivate_block = app_source[deactivate_start:deactivate_end]
    assert 'method: "POST"' in deactivate_block


def test_business_loaders_refresh_active_workspace_panel() -> None:
    app_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")

    assert 'activeBusinessWorkspace === "parties"' in app_source
    assert 'activeBusinessWorkspace === "vouchers"' in app_source
    assert 'activeBusinessWorkspace === "audit"' in app_source
    assert app_source.count("dashboardPreview.innerHTML = renderBusinessWorkspace();") >= 3


def test_mitrabooks_settings_menu_is_business_specific() -> None:
    app_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")

    assert 'businessWorkspace: "settings"' in app_source
    assert 'activeBusinessWorkspace === "settings"' in app_source
    assert "MitraBooks Settings" in app_source
    assert "Core Settings" in app_source
    assert "Module Settings" in app_source
    assert "Professional Practice Settings" in app_source
    assert 'data-business-action="settings-detail"' in app_source
    assert 'businessAction === "settings-detail"' in app_source
    assert 'businessAction === "settings-back"' in app_source
    assert "Backend contract pending" in app_source
    assert "Client Management" in app_source
    assert "Multi-Company Dashboard" in app_source
    assert "AI Settings" in app_source
    assert "MITRABOOKS_COMPLETION_PHASES" in app_source
    assert "Jun 15-21" in app_source
    assert "Jul 13-19" in app_source
    assert "Accounting guardrail:" in app_source
    assert "Housing Settings" not in app_source[app_source.index("const MITRABOOKS_SETTINGS_GROUPS"):app_source.index("const businessListState")]
    assert "Temple Settings" not in app_source[app_source.index("const MITRABOOKS_SETTINGS_GROUPS"):app_source.index("const businessListState")]


def test_mitrabooks_landing_page_covers_onboarding_pricing_and_limits() -> None:
    landing_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "landing.html").read_text(encoding="utf-8")

    assert "MitraBooks" in landing_source
    assert "Cloud ERP and double-entry accounting" in landing_source
    assert "./login.html" in landing_source
    assert "./onboarding.html?intent=register" in landing_source
    assert "./onboarding.html?intent=demo" in landing_source
    assert ">Register<" in landing_source
    assert ">Request Demo<" in landing_source
    assert ">Login<" in landing_source
    assert "GST-ready invoicing" in landing_source
    assert "Document upload and OCR extraction" in landing_source
    assert "Single User - Multi Company" in landing_source
    assert "Multi User - Multi Company" in landing_source
    assert "Regular Business Account" in landing_source
    assert "CA Practice / Bookkeepers" in landing_source
    assert "Free" in landing_source
    assert "Basic" in landing_source
    assert "Starter" in landing_source
    assert "Growth" in landing_source
    assert "Enterprise" in landing_source
    assert "Get Quote" in landing_source
    assert "plan=Enterprise%20custom%20quote" in landing_source
    assert "Rs. 1,499/mo" in landing_source
    assert "Rs. 2,999/mo" in landing_source
    assert "15 practice users" in landing_source
    assert "Yearly: Rs. 29,999." in landing_source
    assert "One-time implementation, migration, and training fee: get quote" in landing_source
    assert "SanMitra Technologies Razorpay account" in landing_source
    assert "not a live GST filing portal" in landing_source
    assert "Human review before ledger posting" in landing_source
    assert "./about.html" in landing_source
    assert "./contact.html" in landing_source
    assert "./privacy.html" in landing_source
    assert "./terms.html" in landing_source

    onboarding_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "onboarding.html").read_text(encoding="utf-8")
    assert 'data-app-key="mitrabooks"' in onboarding_source
    assert "Designation / Authority" in onboarding_source
    assert '<select id="authority_designation" name="authority_designation" required>' in onboarding_source
    assert '<option value="Other">Other</option>' in onboarding_source
    assert "authority_designation_other" in onboarding_source
    assert "OTP / Verification Channel" in onboarding_source
    assert "Enterprise custom quote" in onboarding_source
    assert "terms_accepted" in onboarding_source
    assert "Contact verification and plan/payment approval" in onboarding_source


def test_mitrabooks_public_pages_are_product_scoped() -> None:
    public_pages = ("about.html", "contact.html", "privacy.html", "terms.html")

    for page in public_pages:
        source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / page).read_text(encoding="utf-8")
        assert "MitraBooks" in source
        assert "SanMitra Platform" in source
        assert "./landing.html" in source
        assert "./login.html" in source
        assert "Privacy Policy" in source
        assert "Terms of Use" in source
        assert "GruhaMitra" not in source
        assert "MandirMitra" not in source

    terms_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "terms.html").read_text(encoding="utf-8")
    assert "One-time implementation, migration, and training fee: get quote" in terms_source

    contact_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "contact.html").read_text(encoding="utf-8")
    assert "contact@sanmitratech.in" in contact_source


def test_business_voucher_accounts_use_backend_account_contract() -> None:
    app_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")
    css_source = (REPO_ROOT / "frontend" / "shared" / "app-shell.css").read_text(encoding="utf-8")

    assert "function normalizeBusinessAccount(acc)" in app_source
    assert "acc.account_id ?? acc.id" in app_source
    assert "acc.account_code" in app_source
    assert "?? acc.code" in app_source
    assert "acc.account_name" in app_source
    assert "?? acc.name" in app_source
    assert "populateVoucherAccountSelect(select" in app_source
    assert "syncVoucherAccountFromText" in app_source
    assert "account-selector-component" in app_source
    assert "account-suggestions" in app_source
    assert "updateVoucherAccountsStatus" in app_source
    assert "grid-column: 1 / -1" in css_source
    assert "Account code dropdown" in app_source
    assert "accountRowsFromPayload" in app_source
    assert "MitraBooks business tenant required" in app_source
    assert "business.admin@sanmitra.local" in app_source
    assert 'await loadBusinessAccounts();' in app_source
    assert "function findBusinessAccountById(accountId)" in app_source
    assert "function accountIdForVoucherPayload(account)" in app_source
    assert "debit_account_code: debitAccount.code" in app_source
    assert "credit_account_code: creditAccount.code" in app_source


def test_mitrabooks_phase_1c_ui_polish_is_scoped_to_business_shell() -> None:
    app_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")
    css_source = (REPO_ROOT / "frontend" / "shared" / "app-shell.css").read_text(encoding="utf-8")

    assert "erp-workspace-panel" in app_source
    assert "erp-table" in app_source
    assert "voucher-line" in app_source
    assert "voucher-lines-panel" in app_source
    assert ".business-dashboard" in css_source
    assert ".voucher-balance-status.balanced" in css_source
    assert "const hasAmount = totalDebit > 0 || totalCredit > 0" in app_source
    assert "#business-voucher-create-dialog" in css_source
    # Sprint 2: Sales Invoices with GST are part of the business shell.
    assert "function renderBusinessSalesWorkspace()" in app_source
    assert "/api/v1/business/invoices" in app_source
    assert "function computeInvoiceLine(" in app_source


def test_mitrabooks_shell_has_global_logout_and_reachable_login() -> None:
    app_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")
    css_source = (REPO_ROOT / "frontend" / "shared" / "app-shell.css").read_text(encoding="utf-8")
    index_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "index.html").read_text(encoding="utf-8")

    assert 'id="topbar-logout"' in index_source
    assert 'id="sidebar-logout"' in index_source
    assert 'id="account-menu-trigger"' in index_source
    assert 'id="topbar-update-password"' in index_source
    assert 'id="password-dialog"' in index_source
    assert "function signOutAndReturnToLogin()" in app_source
    assert "function updateCurrentPassword()" in app_source
    assert "/api/v1/auth/change-password" in app_source
    assert 'document.getElementById("topbar-logout")?.addEventListener("click"' in app_source
    assert 'document.getElementById("sidebar-logout")?.addEventListener("click"' in app_source
    assert 'document.getElementById("topbar-update-password")?.addEventListener("click", openPasswordDialog)' in app_source
    assert 'topbarControlStrip.hidden = currentExperience !== "mitrabooks";' in app_source
    assert ".account-menu-trigger" in css_source
    assert ".account-menu-panel" in css_source
    assert ".app.signed-out .main" in css_source
    assert ".app.signed-out .topbar" in css_source
    assert ".app.signed-in .topbar-actions" in css_source


def test_mitrabooks_phase_2a_data_health_panel_uses_existing_contracts() -> None:
    app_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")
    css_source = (REPO_ROOT / "frontend" / "shared" / "app-shell.css").read_text(encoding="utf-8")
    run_start = app_source.index("async function runChecks()")
    run_end = app_source.index("async function loadPlatformOwnerDashboard()", run_start)
    run_block = app_source[run_start:run_end]

    assert "function renderBusinessDataHealthPanel()" in app_source
    assert "Tenant, module, chart, and drill-down readiness" in app_source
    assert "Business tenant context" in app_source
    assert "Chart of accounts loaded" in app_source
    assert "Cash and bank accounts" in app_source
    assert "Revenue / income accounts" in app_source
    assert "Expense accounts" in app_source
    assert "Party GSTIN sample" in app_source
    assert "Voucher drill-down" in app_source
    assert "function isPlatformOwnerContext" in app_source
    assert "function isBusinessTenantContext" in app_source
    assert 'currentExperience === "mitrabooks" && isPlatformOwnerContext(modules.payload)' in run_block
    assert run_block.index("isPlatformOwnerContext(modules.payload)") < run_block.index("await loadBusinessAccounts();")
    assert "await loadBusinessAccounts();" in run_block
    assert "await loadBusinessPartiesForHealth();" in run_block
    assert "/api/v1/accounting/accounts" in app_source
    assert "/api/v1/business/parties?offset=0&limit=20" in app_source
    assert "loadModules(activeAppKey)" in run_block
    assert ".erp-health-panel" in css_source
    assert ".erp-health-actions" in css_source


def test_mitrabooks_phase_2b_data_health_actions_are_actionable_not_future_scope() -> None:
    app_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")
    css_source = (REPO_ROOT / "frontend" / "shared" / "app-shell.css").read_text(encoding="utf-8")
    start = app_source.index("function renderBusinessDataHealthActions")
    end = app_source.index("function renderBusinessDataHealthPanel", start)
    actions_block = app_source[start:end]

    assert "Action Queue" in actions_block
    assert "Complete party GSTINs" in actions_block
    assert "Add cash or bank account" in actions_block
    assert "Add revenue account" in actions_block
    assert "Add expense account" in actions_block
    assert "Verify voucher drill-down" in actions_block
    assert "sales, purchases, GST, or inventory" in actions_block
    assert "Continue with parties and balanced vouchers; keep GST/inventory depth deferred." in actions_block
    assert "OCR" not in actions_block
    assert "GSTR-2B" not in actions_block
    assert ".erp-health-actions ol" in css_source


def test_business_voucher_payload_matches_typed_voucher_api() -> None:
    app_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")
    start = app_source.index("async function createBusinessVoucher(voucherData)")
    end = app_source.index("async function loadBusinessVouchers", start)
    create_block = app_source[start:end]

    assert 'voucher_type: "journal"' in create_block
    assert "amount: debitTotal.toFixed(2)" in create_block
    assert "debit_account_id: debitLines[0].account_id" in create_block
    assert "credit_account_id: creditLines[0].account_id" in create_block
    assert "debit_account_code: debitLines[0].account_code" in app_source
    assert "credit_account_code: creditLines[0].account_code" in app_source
    assert '"X-Idempotency-Key"' in create_block
    assert "lines:" not in create_block
    assert "debit_paise" not in create_block
    assert "credit_paise" not in create_block


def test_business_voucher_loader_surfaces_backend_errors() -> None:
    app_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")
    start = app_source.index("async function loadBusinessVouchers")
    end = app_source.index("async function reverseBusinessVoucher", start)
    load_block = app_source[start:end]

    assert 'setLoginStatus("danger", "Unable to load vouchers"' in load_block
    assert "statusDetailText(result.payload?.detail)" in load_block
    assert "renderJson(apiOutput, { vouchers:" in load_block


def test_business_voucher_reversal_uses_business_route_contract() -> None:
    app_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")
    start = app_source.index("async function reverseBusinessVoucher")
    end = app_source.index("async function openBusinessCreateVoucherDialog", start)
    reverse_block = app_source[start:end]

    assert "/api/v1/business/vouchers/${encodeURIComponent(voucherId)}/reverse" in reverse_block
    assert "/api/v1/accounting/reversals" not in reverse_block
    assert '"X-Idempotency-Key"' in reverse_block
    assert "original_voucher_id" not in reverse_block


def test_ca_practice_documents_use_metadata_api_without_file_upload() -> None:
    app_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")
    start = app_source.index("async function loadCaPracticeDocuments")
    end = app_source.index("async function updateBusinessParty", start)
    ca_block = app_source[start:end]

    assert 'new URLSearchParams({ limit: "100" })' in ca_block
    assert "/api/v1/business/ca-documents?${params.toString()}" in ca_block
    assert 'apiRequest("mitrabooks", "/api/v1/business/ca-documents"' in ca_block
    assert 'method: "PATCH"' in ca_block
    assert 'label: "CA Practice Portal"' in app_source
    assert 'businessWorkspace: "ca-access"' in app_source
    assert 'activeBusinessWorkspace === "ca-access"' in app_source
    assert 'module_key: "ca_access"' in app_source
    nav_start = app_source.index('businessWorkspace: "ca-access"')
    assert 'enabled: true' in app_source[nav_start:nav_start + 220]
    assert "File storage deferred" in app_source
    assert 'type="file" multiple disabled' in app_source
    assert "data-ca-document-form" in app_source
    assert "data-ca-filter-form" in app_source
    assert "client_owner" in ca_block
    assert "client_access_enabled" in ca_block
    assert "renderCaPracticeOperations" in app_source
    assert 'subtitle: "Client document workflow"' in app_source
    assert 'return renderCaPracticePortalWorkspace();' in app_source
    assert "CA Practice Portal planned" not in app_source
    assert "Planned multi-client books" not in app_source


def test_professional_suite_routes_to_active_workspace_without_planned_cards() -> None:
    app_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")
    index_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "index.html").read_text(encoding="utf-8")

    assert 'statusTitle: "Professional workspace active"' in app_source
    assert 'statusCopy: "Using the signed-in MitraBooks tenant context for billing, client accounts, receipts, and reports."' in app_source
    assert 'return renderProfessionalSuiteWorkspace();' in app_source
    assert 'function renderProfessionalSuiteWorkspace()' in app_source
    assert 'MitraBooks workflow active' in app_source
    assert '["Client Billing", "Create GST-ready service invoices in the active Sales workspace.", "sales", "Open Sales"]' in app_source
    assert '["Client Accounts", "Maintain professional clients and vendors in Parties.", "parties", "Open Parties"]' in app_source
    assert '["Receipts", "Record client receipts and journal entries through the voucher workflow.", "vouchers", "Open Vouchers"]' in app_source
    assert '["Professional Reports", "Review ledger-backed financial statements and receivables.", "reports", "Open Reports"]' in app_source
    assert "Professional workspace planned" not in app_source
    assert "Planned billing and invoicing" not in app_source
    assert "planned workspace preview" not in app_source
    assert "<strong>Professional Suite</strong><small>Billing and invoicing</small>" in index_source


def test_accounting_voucher_detail_surfaces_reversal_links() -> None:
    app_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")
    start = app_source.index("function renderAccountingVoucherDetail")
    end = app_source.index("function renderAccountingDrilldownPanel", start)
    detail_block = app_source[start:end]

    assert "reversed_by_journal_ids" in detail_block
    assert "reversal_of_journal_id" in detail_block
    assert "Reversal of journal #" in detail_block
    assert "Reversed by journal #" in detail_block
