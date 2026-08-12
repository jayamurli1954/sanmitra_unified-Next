#!/usr/bin/env python3
"""Capture updated high-resolution screenshots for docs/MitraBooks_User_Manual.docx."""
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
IMG_DIR = ROOT / "docs" / "User_manual_screenshots"
IMG_DIR.mkdir(parents=True, exist_ok=True)

URL = "http://127.0.0.1:3300/mitrabooks-erp/index.html"

def mock_routes(page):
    # Mock OfficeMitra AI Brief endpoint
    page.route("**/api/v1/officemitra/brief**", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({
            "success": True,
            "brief": {
                "summary": "AI-curated operational highlights & priority digests.",
                "pending_tasks": 3,
                "unread_emails": 2,
                "high_priority_items": ["GST Filing due in 4 days", "Vendor Payment pending approval"]
            }
        })
    ))

    # Mock Accounting Drilldown endpoint
    page.route("**/api/v1/accounting/reports/drilldown**", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({
            "success": True,
            "period": "FY 2026-27",
            "level": "month",
            "breadcrumbs": ["All Months", "June 2026"],
            "summary": {
                "total_debit": 381500.00,
                "total_credit": 381500.00,
                "net_balance": 0.00,
                "voucher_count": 14
            },
            "items": [
                {"date": "2026-06-01", "voucher_no": "PV-2026-001", "particulars": "Office Rent Payment", "debit": 45000, "credit": 0},
                {"date": "2026-06-05", "voucher_no": "RV-2026-008", "particulars": "Customer Receipt - Zenith", "debit": 0, "credit": 125000},
                {"date": "2026-06-12", "voucher_no": "JV-2026-012", "particulars": "Depreciation Adjustment", "debit": 12000, "credit": 12000}
            ]
        })
    ))

def capture_screenshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=2)
        page = context.new_page()
        mock_routes(page)

        # 1. Login Page Screenshot (02-1-login.png)
        print("Capturing 02-1-login.png...")
        page.goto(URL)
        page.wait_for_selector("#access-panel", timeout=15000)
        page.screenshot(path=str(IMG_DIR / "02-1-login.png"), full_page=False)

        # Authenticate Session
        page.add_init_script("""() => {
            window.sessionStorage.setItem('sanmitra_frontend_access_token', 'static-shell-token');
            window.localStorage.setItem('sanmitra_mitrabooks_login_email', 'businessadmin@sanmitra.local');
            window.localStorage.removeItem('mitrabooks-widget-states');
        }""")
        page.goto(URL)
        page.wait_for_selector(".dashboard-quick-execution-bar", state="attached", timeout=30000)
        time.sleep(2.0)

        # 2. Executive Dashboard (03-dashboard.png)
        print("Capturing 03-dashboard.png...")
        page.screenshot(path=str(IMG_DIR / "03-dashboard.png"), full_page=False)

        # 3. Getting Started / Workspace Layout (2.png & 02-2-workspace-layout.png)
        print("Capturing 2.png & 02-2-workspace-layout.png...")
        page.screenshot(path=str(IMG_DIR / "2.png"), full_page=False)
        page.screenshot(path=str(IMG_DIR / "02-2-workspace-layout.png"), full_page=False)

        # 4. Navigation Groups (2.3 Navigation Groups.png)
        print("Capturing 2.3 Navigation Groups.png...")
        sidebar = page.locator("aside.sidebar")
        if sidebar.is_visible():
            sidebar.screenshot(path=str(IMG_DIR / "2.3 Navigation Groups.png"))
        else:
            page.screenshot(path=str(IMG_DIR / "2.3 Navigation Groups.png"))

        # 5. Add Party Form (04-1-add-party.png)
        print("Capturing 04-1-add-party.png...")
        try:
            page.locator("[data-business-action='open-create-party']").click(force=True, timeout=5000)
        except Exception:
            page.evaluate("() => document.getElementById('business-party-create-dialog')?.showModal()")
        time.sleep(1)
        page.screenshot(path=str(IMG_DIR / "04-1-add-party.png"), full_page=False)
        page.evaluate("() => document.getElementById('business-party-create-dialog')?.close()")
        time.sleep(0.5)

        # 6. Create Voucher Form with Debit/Credit Balanced Status (12-2-journal-post.png)
        print("Capturing 12-2-journal-post.png...")
        try:
            page.locator("[data-business-action='open-create-voucher']").click(force=True, timeout=5000)
        except Exception:
            page.evaluate("() => document.getElementById('business-voucher-create-dialog')?.showModal()")
        time.sleep(1)
        page.select_option("#business-voucher-type-select", "payment")
        time.sleep(0.5)
        # Fill payment fields to trigger double-entry balance check
        if page.locator("#voucher-pv-amount").is_visible():
            page.fill("#voucher-pv-amount", "50000")
            page.dispatch_event("#voucher-pv-amount", "input")
        time.sleep(0.5)
        page.screenshot(path=str(IMG_DIR / "12-2-journal-post.png"), full_page=False)
        page.evaluate("() => document.getElementById('business-voucher-create-dialog')?.close()")
        time.sleep(0.5)

        # 7. Invoices List / Sales (05-1-create-invoice.png & 05-3-invoice-list.png)
        print("Capturing 05-1-create-invoice.png & 05-3-invoice-list.png...")
        page.evaluate("() => { document.querySelector('a[data-business-workspace=\"sales\"], a[data-module-key=\"sales\"]')?.click(); }")
        time.sleep(1.5)
        page.screenshot(path=str(IMG_DIR / "05-1-create-invoice.png"), full_page=False)
        page.screenshot(path=str(IMG_DIR / "05-3-invoice-list.png"), full_page=False)

        # 8. Core Ledger / Chart of Accounts (12-1-coa.png)
        print("Capturing 12-1-coa.png...")
        page.evaluate("() => { document.querySelector('a[data-business-workspace=\"coa\"], a[data-module-key=\"coa\"]')?.click(); }")
        time.sleep(1.5)
        page.screenshot(path=str(IMG_DIR / "12-1-coa.png"), full_page=False)

        # 9. Accounting Drill-Down Workspace (13-4-drilldown.png & 13-1-trial-balance.png)
        print("Capturing 13-1-trial-balance.png...")
        page.evaluate("() => { document.querySelector('a[data-business-workspace=\"accounting\"], a[data-module-key=\"accounting\"]')?.click(); }")
        time.sleep(1.5)
        page.screenshot(path=str(IMG_DIR / "13-1-trial-balance.png"), full_page=False)

        # 10. HR & Payroll (22-hr-workspace.png)
        print("Capturing 22-hr-workspace.png...")
        page.evaluate("() => { document.querySelector('a[data-business-workspace=\"hr\"], a[data-module-key=\"hr\"]')?.click(); }")
        time.sleep(1.5)
        page.screenshot(path=str(IMG_DIR / "22-hr-workspace.png"), full_page=False)

        # 11. Manufacturing (23-mfg-workspace.png)
        print("Capturing 23-mfg-workspace.png...")
        page.evaluate("() => { document.querySelector('a[data-business-workspace=\"manufacturing\"], a[data-module-key=\"manufacturing\"]')?.click(); }")
        time.sleep(1.5)
        page.screenshot(path=str(IMG_DIR / "23-mfg-workspace.png"), full_page=False)

        browser.close()

if __name__ == "__main__":
    capture_screenshots()
    print("All screenshots successfully captured!")
