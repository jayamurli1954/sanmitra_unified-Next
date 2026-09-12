#!/usr/bin/env python3
"""Capture OfficeMitra AI screenshots only (for manual section 24)."""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from capture_manual_screenshots import (  # noqa: E402
    URL,
    capture_office_ai_screenshots,
    mock_routes,
    start_frontend_server,
)


def main() -> None:
    auth_init = """() => {
        window.sessionStorage.setItem('sanmitra_frontend_access_token', 'static-shell-token');
        window.localStorage.setItem('sanmitra_mitrabooks_login_email', 'businessadmin@sanmitra.local');
        window.localStorage.removeItem('mitrabooks-widget-states');
        window.localStorage.removeItem('sanmitra_frontend_api_base_url');
        window.SANMITRA_API_BASE_URL = window.location.origin;
    }"""
    server = start_frontend_server()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=2)
            context.add_init_script(auth_init)
            page = context.new_page()
            mock_routes(page)
            page.goto(URL)
            page.wait_for_selector(".dashboard-quick-execution-bar", state="attached", timeout=30000)
            time.sleep(2.0)
            capture_office_ai_screenshots(page)
            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
    print("OfficeMitra manual screenshots captured.")


if __name__ == "__main__":
    main()
