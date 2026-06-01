from pathlib import Path


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

    assert "app.js?v=mitrabooks-erp-v9" in index_source
    assert "pwa-shell.js?v=mitrabooks-erp-v9" in index_source
    assert "app-shell.css?v=mitrabooks-erp-v9" in index_source
    assert 'CACHE_NAME = "sanmitra-frontends-v24"' in worker_source


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

    assert 'dashboardPreview.innerHTML = renderAccountingDrilldownPanel();' in workspace_switcher
    assert 'dashboardPreview.innerHTML = renderBusinessWorkspace();' in workspace_switcher
    assert 'document.getElementById("context-cards")' not in workspace_switcher


def test_business_party_payload_matches_backend_schema() -> None:
    app_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")
    create_start = app_source.index("async function createBusinessParty(data)")
    create_end = app_source.index("async function updateBusinessParty", create_start)
    create_block = app_source[create_start:create_end]
    update_end = app_source.index("async function deactivateBusinessParty", create_end)
    update_block = app_source[create_end:update_end]

    assert "party_name: data.name" in create_block
    assert "opening_balance: String(Number(data.opening_balance) || 0)" in create_block
    assert "opening_balance_paise" not in create_block
    assert "party_name: data.name" in update_block
    assert "opening_balance_paise" not in update_block


def test_business_loaders_refresh_active_workspace_panel() -> None:
    app_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")

    assert 'activeBusinessWorkspace === "parties"' in app_source
    assert 'activeBusinessWorkspace === "vouchers"' in app_source
    assert 'activeBusinessWorkspace === "audit"' in app_source
    assert app_source.count("dashboardPreview.innerHTML = renderBusinessWorkspace();") >= 3


def test_business_voucher_accounts_use_backend_account_contract() -> None:
    app_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")

    assert "function normalizeBusinessAccount(acc)" in app_source
    assert "acc.account_id ?? acc.id" in app_source
    assert "acc.account_code ?? acc.code" in app_source
    assert "acc.account_name ?? acc.name" in app_source
    assert "populateVoucherAccountSelect(select" in app_source
    assert "syncVoucherAccountFromText" in app_source
    assert 'list="business-voucher-account-options"' in app_source
    assert "updateVoucherAccountsStatus" in app_source
    assert "grid-column: 1 / -1" in app_source
    assert "Account code / name" in app_source
    assert "accountRowsFromPayload" in app_source
    assert "MitraBooks business tenant required" in app_source
    assert "businessadmin@sanmitra.local" in app_source
    assert 'await loadBusinessAccounts();' in app_source


def test_business_voucher_payload_matches_typed_voucher_api() -> None:
    app_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "app.js").read_text(encoding="utf-8")
    start = app_source.index("async function createBusinessVoucher(voucherData)")
    end = app_source.index("async function loadBusinessVouchers", start)
    create_block = app_source[start:end]

    assert 'voucher_type: "journal"' in create_block
    assert "amount: debitTotal.toFixed(2)" in create_block
    assert "debit_account_id: debitLines[0].account_id" in create_block
    assert "credit_account_id: creditLines[0].account_id" in create_block
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
