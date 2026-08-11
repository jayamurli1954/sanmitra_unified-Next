"""Static contract checks for the OfficeMitra standalone shell."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_officemitra_standalone_shell_uses_officemitra_app_key():
    app_js = (REPO_ROOT / "frontend" / "officemitra" / "app.js").read_text(encoding="utf-8")
    login_js = (REPO_ROOT / "frontend" / "officemitra" / "login.js").read_text(encoding="utf-8")
    shared = (REPO_ROOT / "frontend" / "shared" / "office-ai-workspace.js").read_text(encoding="utf-8")
    erp_shim = (
        REPO_ROOT / "frontend" / "mitrabooks-erp" / "modules" / "workspaces" / "office-ai.js"
    ).read_text(encoding="utf-8")

    assert 'APP_KEY = "officemitra"' in app_js
    assert 'APP_KEY = "officemitra"' in login_js
    assert 'appKey: APP_KEY' in app_js
    assert "office-ai-workspace.js" in app_js
    assert "resolveAppKey()" in shared
    assert 'appKey || "mitrabooks"' in shared
    assert "office-ai-workspace.js" in erp_shim


def test_officemitra_vercel_host_and_rewrites_are_wired():
    vercel = (REPO_ROOT / "frontend" / "vercel.json").read_text(encoding="utf-8")
    assert "officemitra.sanmitratech.in" in vercel
    assert "staging.officemitra.sanmitratech.in" in vercel
    assert '"/officemitra/"' in vercel or '"/officemitra"' in vercel
    assert "/officemitra/index.html" in vercel
