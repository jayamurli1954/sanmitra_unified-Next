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
import os
import re
import sys
from datetime import datetime, timezone
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
    parser.add_argument("--email", default=os.getenv("MANDIRMITRA_SMOKE_EMAIL", "admin@sanmitra.local"))
    parser.add_argument(
        "--password",
        default=None,
        help="Login password. Prefer the MANDIRMITRA_SMOKE_PASSWORD environment variable.",
    )
    parser.add_argument("--headed", action="store_true", help="Show Chromium window.")
    parser.add_argument("--slow-mo", type=int, default=0, help="Playwright slow motion in ms.")
    parser.add_argument("--screenshot", default=str(ROOT / "tmp" / "mandir-stage3-browser-smoke.png"))
    parser.add_argument("--evidence", default=str(ROOT / "tmp" / "mandir-stage3-browser-smoke.json"))
    args = parser.parse_args()

    password = args.password or os.getenv("MANDIRMITRA_SMOKE_PASSWORD")
    if not password:
        fail("Set MANDIRMITRA_SMOKE_PASSWORD; the smoke runner has no embedded password default")

    sync_playwright, PlaywrightTimeoutError, PlaywrightError = require_playwright()

    screenshot_path = Path(args.screenshot)
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path = Path(args.evidence)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)

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
            data={"email": args.email, "password": password},
        )
        if not login.ok:
            fail(f"Login failed: HTTP {login.status}")
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

        authorized_headers = {
            "Authorization": f"Bearer {token}",
            "X-App-Key": "mandirmitra",
        }
        compliance = api_context.get(
            "/api/v1/compliance/donations/config",
            headers=authorized_headers,
        )
        if not compliance.ok:
            fail(f"Donation compliance config failed: HTTP {compliance.status}")
        compliance_payload = compliance.json()
        enable_80g = compliance_payload.get("enable_80g") is True
        enable_fcra = compliance_payload.get("enable_fcra") is True
        if enable_80g:
            required_80g = ("institution_pan", "approval_number", "approval_valid_from", "approval_valid_to")
            if any(not compliance_payload.get(field) for field in required_80g):
                fail("80G is enabled without complete dated approval evidence")
        if enable_fcra:
            required_fcra = (
                "fcra_registration_number",
                "fcra_valid_from",
                "fcra_valid_to",
                "fcra_designated_account_id",
            )
            if any(not compliance_payload.get(field) for field in required_fcra):
                fail("FCRA is enabled without complete dated approval and designated-account evidence")

        readiness_80g = api_context.get(
            "/api/v1/reports/compliance/80g",
            headers=authorized_headers,
            params={"from_date": datetime.now(timezone.utc).date().isoformat(), "to_date": datetime.now(timezone.utc).date().isoformat()},
        )
        readiness_fcra = api_context.get(
            "/api/v1/reports/compliance/fcra",
            headers=authorized_headers,
            params={"from_date": datetime.now(timezone.utc).date().isoformat(), "to_date": datetime.now(timezone.utc).date().isoformat()},
        )
        if not readiness_80g.ok or not readiness_fcra.ok:
            fail(
                "Compliance readiness report failed: "
                f"80G HTTP {readiness_80g.status}; FCRA HTTP {readiness_fcra.status}"
            )
        readiness_80g_payload = readiness_80g.json()
        readiness_fcra_payload = readiness_fcra.json()
        if readiness_80g_payload.get("filing_artifact") is not False:
            fail("80G readiness response must explicitly declare filing_artifact=false")
        if readiness_fcra_payload.get("filing_artifact") is not False:
            fail("FCRA readiness response must explicitly declare filing_artifact=false")
        for row in readiness_80g_payload.get("items", []):
            if row.get("donor_pan"):
                fail("80G readiness response exposed an unmasked donor PAN field")
            masked_pan = str(row.get("donor_pan_masked") or "")
            if masked_pan and not re.fullmatch(r"\*{5}[0-9A-Z]{4}", masked_pan):
                fail("80G readiness response returned an invalid PAN mask")

        page.goto(args.frontend_url, wait_until="networkidle")
        try:
            page.wait_for_function(
                "() => document.documentElement.dataset.mitrabooksShellReady === '1'",
                timeout=30000,
            )
        except PlaywrightTimeoutError:
            page.screenshot(path=str(screenshot_path), full_page=True)
            fail("Timed out waiting for MitraBooks shell bootstrap before Mandir smoke")

        page.evaluate(
            """([token, apiBase]) => {
                sessionStorage.setItem('sanmitra_frontend_access_token', token);
                localStorage.setItem('sanmitra_frontend_api_base_url', apiBase);
            }""",
            [token, args.api_base],
        )

        # Stay on the current page: a reload boots MitraBooks first and can clear a
        # Mandir-scoped token before the smoke switches app context.
        page.locator("#mode-mandir").dispatch_event("click")

        try:
            page.wait_for_function(
                """() => {
                    const text = document.body.innerText;
                    return text.includes('MandirMitra')
                        && text.includes('Dashboard Workspace')
                        && text.includes('Donations');
                }""",
                timeout=45000,
            )
        except PlaywrightTimeoutError:
            page.screenshot(path=str(screenshot_path), full_page=True)
            fail("Timed out waiting for MandirMitra live dashboard after mode switch")

        text = page.locator("body").inner_text(timeout=5000)
        checks = {
            "mandir workspace": "MandirMitra",
            "public payments": "Public Payments",
            "receipts": "Receipts",
            "panchang tab": "Panchang",
            "reports tab": "Reports",
            "trial balance": "Accounting Reports",
            "donations": "Donations",
            "sevas": "Sevas",
        }
        for label, needle in checks.items():
            assert_contains(text, needle, label)

        if "MandirMitra live data unavailable" in text:
            fail("Frontend still reports MandirMitra live data unavailable")
        if "access denied" in text.lower():
            fail("Frontend contains access denied text")

        page.locator('nav#nav a[data-mandir-workspace="settings"]').click()
        page.get_by_role("heading", name="Donation Compliance").wait_for(timeout=10000)
        if page.locator('[data-mandir-compliance-form] input[name="enable_80g"]').is_checked() != enable_80g:
            fail("80G UI toggle does not match trusted tenant configuration")
        if page.locator('[data-mandir-compliance-form] input[name="enable_fcra"]').is_checked() != enable_fcra:
            fail("FCRA UI toggle does not match trusted tenant configuration")

        page.locator('.mandir-workspace-tabs [data-workspace-view="donations"]').click()
        request_80g = page.locator('[data-mandir-create-form="donation"] input[name="request_80g"]')
        foreign_contribution = page.locator(
            '[data-mandir-create-form="donation"] input[name="is_foreign_contribution"]'
        )
        if request_80g.is_disabled() != (not enable_80g):
            fail("80G donation-entry control does not fail closed with tenant configuration")
        if foreign_contribution.is_disabled() != (not enable_fcra):
            fail("FCRA donation-entry control does not fail closed with tenant configuration")

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

        first_cancel = page.locator('[data-mandir-action="cancel-receipt"]').first
        if first_cancel.count() > 0:
            first_cancel.click()
            try:
                page.wait_for_function(
                    """() => {
                        const dialog = document.querySelector('#mandir-cancel-receipt-dialog');
                        return dialog?.open
                            && document.body.innerText.includes('Cancel Receipt')
                            && document.body.innerText.includes('Reverse Receipt');
                    }""",
                    timeout=5000,
                )
            except PlaywrightTimeoutError:
                page.screenshot(path=str(screenshot_path), full_page=True)
                fail("Timed out waiting for MandirMitra receipt cancellation dialog")
            page.locator("#mandir-cancel-receipt-cancel").click()

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
                        && text.includes('Fund and Inventory Drill-down')
                        && text.includes('Inventory Stock Valuation')
                        && text.includes('Recent Devotees');
                }""",
                timeout=10000,
            )
        except PlaywrightTimeoutError:
            page.screenshot(path=str(screenshot_path), full_page=True)
            fail("Timed out waiting for MandirMitra Reports workspace")

        reports_text = page.locator(".mandir-dashboard").inner_text(timeout=5000)
        assert_contains(reports_text, "80G Readiness", "80G readiness report")
        assert_contains(reports_text, "FCRA Readiness", "FCRA readiness report")
        assert_contains(reports_text, "Fund Subledger", "accounting-backed fund subledger")
        assert_contains(reports_text, "Inventory Stock Valuation", "fixed-precision inventory valuation")
        assert_contains(reports_text, "Inventory Audit Trail", "append-only inventory movement history")
        assert_contains(
            reports_text,
            "not an official certificate or filing",
            "80G non-filing disclaimer",
        )
        assert_contains(reports_text, "not an official filing", "FCRA non-filing disclaimer")

        page.screenshot(path=str(screenshot_path), full_page=True)
        browser.close()

    result = {
        "gate": "mandirmitra_stage3_browser_smoke",
        "status": "passed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "frontend_url": args.frontend_url,
        "api_base": args.api_base,
        "tenant_id": modules_payload.get("tenant_id"),
        "organization_type": modules_payload.get("organization_type"),
        "app_key": "mandirmitra",
        "enabled_modules": sorted(enabled),
        "compliance": {
            "enable_80g": enable_80g,
            "enable_fcra": enable_fcra,
            "readiness_80g_rows": len(readiness_80g_payload.get("items", [])),
            "readiness_fcra_rows": len(readiness_fcra_payload.get("items", [])),
            "filing_artifact": False,
            "pan_masking_checked": True,
        },
        "screenshot": str(screenshot_path),
        "evidence": str(evidence_path),
    }
    evidence_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
