import json
from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]


def _csp_for_source(source: str) -> str:
    config = json.loads((REPO_ROOT / "frontend" / "vercel.json").read_text(encoding="utf-8"))
    for rule in config["headers"]:
        if rule.get("source") != source:
            continue
        for header in rule.get("headers", []):
            if header.get("key") == "Content-Security-Policy":
                return header["value"]
    raise AssertionError(f"CSP header missing for {source}")


def _directive(policy: str, name: str) -> str:
    for directive in policy.split(";"):
        directive = directive.strip()
        if directive == name or directive.startswith(f"{name} "):
            return directive
    raise AssertionError(f"{name} missing from CSP")


def test_deployed_frontends_block_inline_script_attributes() -> None:
    for source in ("/:path*", "/mitrabooks-erp/:path*", "/legalmitra/:path*", "/gruhamitra/:path*"):
        policy = _csp_for_source(source)
        assert _directive(policy, "script-src-attr") == "script-src-attr 'none'"
        assert "object-src 'none'" in policy
        assert "base-uri 'self'" in policy
        assert "frame-ancestors 'none'" in policy


def test_active_frontend_csps_do_not_allow_inline_scripts() -> None:
    for source in ("/:path*", "/mitrabooks-erp/:path*", "/legalmitra/:path*", "/gruhamitra/:path*"):
        script_policy = _directive(_csp_for_source(source), "script-src")
        assert "'unsafe-inline'" not in script_policy


def test_gruhamitra_bootstrap_is_external_and_uses_safe_dom_rendering() -> None:
    html_sources = (
        REPO_ROOT / "frontend" / "gruhamitra" / "index.html",
        REPO_ROOT / "frontend" / "gruhamitra" / "public" / "index.html",
    )
    for path in html_sources:
        source = path.read_text(encoding="utf-8")
        assert '<script defer src="/gruhamitra/bootstrap.js"></script>' in source
        assert "<script>" not in source

    bootstrap = (REPO_ROOT / "frontend" / "gruhamitra" / "public" / "bootstrap.js").read_text(encoding="utf-8")
    assert "root.replaceChildren();" in bootstrap
    assert "node.textContent =" in bootstrap
    assert 'reloadButton.addEventListener("click"' in bootstrap
    assert "innerHTML" not in bootstrap
    assert "insertAdjacentHTML" not in bootstrap

    entrypoint = (REPO_ROOT / "frontend" / "gruhamitra" / "src" / "index.jsx").read_text(encoding="utf-8")
    assert "const errorMessage = escapeHtml(" in entrypoint
    assert "const errorStack = escapeHtml(" in entrypoint


def test_active_legacy_sources_have_no_inline_event_handler_attributes() -> None:
    frontend = REPO_ROOT / "frontend"
    excluded_parts = {"build", "e2e", "test-results", "outputs", "node_modules"}
    violations = []
    for suffix in ("*.html", "*.js"):
        for path in frontend.rglob(suffix):
            if excluded_parts.intersection(path.parts):
                continue
            source = path.read_text(encoding="utf-8")
            if re.search(r"<[^>\n]*\son[a-z]+\s*=", source):
                violations.append(str(path.relative_to(REPO_ROOT)))
    assert violations == []


def test_backend_module_metadata_is_escaped_before_legacy_html_rendering() -> None:
    for relative_path in ("frontend/mitrabooks-erp/app.js", "frontend/legalmitra/app.js"):
        source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert "<strong>${module.display_name}</strong>" not in source
        assert '<span class="muted">${module.module_key}' not in source
        assert "${escapeHtml(module.display_name)}" in source
        assert "${escapeHtml(module.module_key)}" in source


def test_public_backend_error_text_is_escaped_before_html_rendering() -> None:
    mandir_public = (REPO_ROOT / "frontend" / "mandir-public" / "app.js").read_text(encoding="utf-8")
    legal = (REPO_ROOT / "frontend" / "legalmitra" / "app.js").read_text(encoding="utf-8")

    assert '${escapeHtml(result.payload?.detail || "Public UPI is not configured.")}' in mandir_public
    assert '${escapeHtml(result.payload?.detail || result.payload?.message || "Check backend logs and try again.")}' in legal
    assert "function renderLegalMarkdown(text)" in legal
    assert "return escapeHtml(value)" in legal


def test_auth_tokens_are_tab_scoped_with_legacy_cleanup() -> None:
    shared_client = (REPO_ROOT / "frontend" / "shared" / "api-client.js").read_text(encoding="utf-8")
    mandir_storage = (REPO_ROOT / "frontend" / "src" / "utils" / "authStorage.js").read_text(encoding="utf-8")
    gruha_storage = (REPO_ROOT / "frontend" / "gruhamitra" / "src" / "utils" / "storage.js").read_text(encoding="utf-8")
    legal_login = (REPO_ROOT / "frontend" / "legalmitra" / "login.js").read_text(encoding="utf-8")

    assert "return window.sessionStorage;" in shared_client
    assert "localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);" in shared_client
    assert "localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);" in shared_client
    assert "localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY" not in shared_client
    assert "localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY" not in shared_client

    assert "sessionStore?.setItem(key, value);" in mandir_storage
    assert "localStore?.removeItem(key);" in mandir_storage
    assert "sessionStore()?.setItem(key, value);" in gruha_storage
    assert "localStore()?.removeItem(key);" in gruha_storage
    assert "sessionStorage.setItem(SESSION_KEY" in legal_login
    assert "localStorage.removeItem(SESSION_KEY);" in legal_login
    assert "localStorage.setItem(SESSION_KEY" not in legal_login
