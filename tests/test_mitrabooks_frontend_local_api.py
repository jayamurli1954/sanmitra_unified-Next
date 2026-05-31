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

    assert "app.js?v=mitrabooks-erp-v6" in index_source
    assert "pwa-shell.js?v=mitrabooks-erp-v6" in index_source
    assert "app-shell.css?v=mitrabooks-erp-v6" in index_source
    assert 'CACHE_NAME = "sanmitra-frontends-v21"' in worker_source


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
