#!/usr/bin/env python3
"""Browser smoke for MandirMitra Stage 3 inside MitraBooks ERP.

Prerequisites:
- Backend running at http://127.0.0.1:8000
- Frontend running at http://127.0.0.1:3300/mitrabooks-erp/#
- Python Playwright installed:
  pip install playwright
  python -m playwright install chromium
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_API_BASE = "http://127.0.0.1:8000"
DEFAULT_FRONTEND_URL = "http://127.0.0.1:3300/mitrabooks-erp/#"


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def require_playwright():
    try:
        from playwright.sync_api import Error, TimeoutError, sync_playwright
    except ImportError as exc:
        raise SystemExit(
            "Python Playwright is not installed. Run from repo root:\n"
            "  pip install playwright\n"
            "  python -m playwright install chromium"
        ) from exc
    return sync_playwright, TimeoutError, Error


def assert_contains(haystack: str, needle: str, label: str) -> None:
    if needle not in haystack:
        fail(f"Missing UI text for {label}: {needle!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MandirMitra Stage 3 browser smoke.")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--frontend-url", default=DEFAULT_FRONTEND_URL)
    parser.add_argument("--email", default="admin@sanmitra.local")
    parser.add_argument("--password", default="admin123")
    parser.add_argument("--headed", action="store_true", help="Show Chromium window.")
    parser.add_argument("--slow-mo", type=int, default=0, help="Playwright slow motion in ms.")
    parser.add_argument("--screenshot", default=str(ROOT / "tmp" / "mandir-stage3-browser-smoke.png"))
    args = parser.parse_args()

    sync_playwright, PlaywrightTimeoutError, PlaywrightError = require_playwright()

    screenshot_path = Path(args.screenshot)
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=not args.headed, slow_mo=args.slow_mo)
        except PlaywrightError as exc:
            raise SystemExit(
                "Chromium is not installed for Playwright. Run:\n"
                "  python -m playwright install chromium"
            ) from exc

        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        api_context = p.request.new_context(
            base_url=args.api_base,
            extra_http_headers={"X-App-Key": "mandirmitra"},
        )

        login = api_context.post(
            "/api/v1/auth/local-login",
            data={"email": args.email, "password": args.password},
        )
        if not login.ok:
            fail(f"Login failed: HTTP {login.status} {login.text()}")
        token = login.json().get("access_token")
        if not token:
            fail("Login response did not include access_token")

        modules = api_context.get(
            "/api/v1/modules/me",
            headers={"Authorization": f"Bearer {token}", "X-App-Key": "mandirmitra"},
        )
        if not modules.ok:
            fail(f"modules/me failed: HTTP {modules.status} {modules.text()}")
        modules_payload = modules.json()
        enabled = {item.get("module_key") for item in modules_payload.get("enabled_modules", [])}
        if modules_payload.get("organization_type") != "TEMPLE":
            fail(f"Expected TEMPLE organization_type, got {modules_payload.get('organization_type')!r}")
        for module_key in ("temple", "accounting", "audit"):
            if module_key not in enabled:
                fail(f"Missing enabled module: {module_key}")

        page.goto(args.frontend_url, wait_until="networkidle")
        page.evaluate(
            """([token, apiBase]) => {
                localStorage.setItem('sanmitra_frontend_access_token', token);
                localStorage.setItem('sanmitra_frontend_api_base_url', apiBase);
            }""",
            [token, args.api_base],
        )
        page.reload(wait_until="networkidle")

        page.locator("#mode-mandir").click()
        page.locator("#run-checks").click()

        try:
            page.wait_for_function(
                "() => document.body.innerText.includes('Trial Balance')",
                timeout=15000,
            )
        except PlaywrightTimeoutError:
            page.screenshot(path=str(screenshot_path), full_page=True)
            fail("Timed out waiting for MandirMitra live dashboard after Run checks")

        text = page.locator("body").inner_text(timeout=5000)
        checks = {
            "mandir workspace": "MandirMitra",
            "public payments": "Public Payments",
            "receipts": "Receipts",
            "panchang tab": "Panchang",
            "reports tab": "Reports",
            "trial balance": "Trial Balance",
            "donations": "Donations",
            "sevas": "Sevas",
        }
        for label, needle in checks.items():
            assert_contains(text, needle, label)

        if "MandirMitra live data unavailable" in text:
            fail("Frontend still reports MandirMitra live data unavailable")
        if "access denied" in text.lower():
            fail("Frontend contains access denied text")

        page.locator('.mandir-workspace-tabs [data-workspace-view="receipts"]').click()
        try:
            page.wait_for_function(
                """() => {
                    const active = document.querySelector('.mandir-workspace-tabs button.active');
                    const text = document.body.innerText;
                    const hasReceiptRows = text.includes('DON-') || text.includes('SEV-');
                    const hasCancelAction = Boolean(document.querySelector('[data-mandir-action="cancel-receipt"]'));
                    return active?.textContent?.trim() === 'Receipts'
                        && text.includes('Recent Receipts')
                        && (!hasReceiptRows || hasCancelAction);
                }""",
                timeout=10000,
            )
        except PlaywrightTimeoutError:
            page.screenshot(path=str(screenshot_path), full_page=True)
            fail("Timed out waiting for MandirMitra Receipts workspace with cancellation action")

        page.locator('.mandir-workspace-tabs [data-workspace-view="panchang"]').click()
        try:
            page.wait_for_function(
                """() => {
                    const active = document.querySelector('.mandir-workspace-tabs button.active');
                    return active?.textContent?.trim() === 'Panchang'
                        && document.body.innerText.includes('Today Panchang')
                        && document.body.innerText.includes('Tithi');
                }""",
                timeout=10000,
            )
        except PlaywrightTimeoutError:
            page.screenshot(path=str(screenshot_path), full_page=True)
            fail("Timed out waiting for MandirMitra Panchang workspace")

        page.locator('.mandir-workspace-tabs [data-workspace-view="reports"]').click()
        try:
            page.wait_for_function(
                """() => {
                    const active = document.querySelector('.mandir-workspace-tabs button.active');
                    const text = document.body.innerText;
                    return active?.textContent?.trim() === 'Reports'
                        && text.includes('MandirMitra Reports')
                        && text.includes('Donation Category Report')
                        && text.includes('Detailed Sevas')
                        && text.includes('Recent Devotees');
                }""",
                timeout=10000,
            )
        except PlaywrightTimeoutError:
            page.screenshot(path=str(screenshot_path), full_page=True)
            fail("Timed out waiting for MandirMitra Reports workspace")

        page.screenshot(path=str(screenshot_path), full_page=True)
        browser.close()

    result = {
        "status": "passed",
        "frontend_url": args.frontend_url,
        "api_base": args.api_base,
        "organization_type": modules_payload.get("organization_type"),
        "enabled_modules": sorted(enabled),
        "screenshot": str(screenshot_path),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
