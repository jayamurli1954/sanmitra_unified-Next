from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_mitrabooks_destructive_spec_disables_credential_bearing_artifacts() -> None:
    spec = (
        REPO_ROOT / "frontend" / "e2e" / "mitrabooks-realstack-destructive.spec.js"
    ).read_text(encoding="utf-8")

    assert "trace: 'off'" in spec
    assert "video: 'off'" in spec
    assert "screenshot: 'off'" in spec
    # Prefer API login + session seed over brittle hosted UI password entry.
    assert "async function loginViaApi" in spec
    assert "/auth/login" in spec
    assert "window.sessionStorage.setItem('sanmitra_frontend_access_token'" in spec
    assert "window.sessionStorage.getItem('sanmitra_frontend_access_token')" in spec
    # Password must come from env and must not be hardcoded in the spec.
    assert "process.env.E2E_USER_PASSWORD" in spec
    assert "page.locator('#login-password').fill(password)" not in spec


def test_track0_runbook_forbids_raw_auth_and_browser_artifacts() -> None:
    runbook = (
        REPO_ROOT / "docs" / "operations" / "TRACK0_STAGING_CREDENTIALS_RUNBOOK.md"
    ).read_text(encoding="utf-8")

    assert "Do not use a raw `curl` login response as signoff evidence" in runbook
    assert "disables Playwright trace, video, and screenshots" in runbook
    assert "A failed partial run must be treated as" in runbook
