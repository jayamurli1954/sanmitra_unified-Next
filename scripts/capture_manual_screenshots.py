#!/usr/bin/env python3
"""Capture updated high-resolution screenshots for docs/MitraBooks_User_Manual.docx."""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
IMG_DIR = ROOT / "docs" / "User_manual_screenshots"
IMG_DIR.mkdir(parents=True, exist_ok=True)

URL = "http://127.0.0.1:3300/mitrabooks-erp/index.html"
MIS_PACK_ID = "pack-manual-demo-1"

MIS_FACTS = [
    {"entity_type": "kpi", "dimensions": {"kpi": "Revenue", "unit": "INR"}, "value": 12500000, "period": "2026-07"},
    {"entity_type": "kpi", "dimensions": {"kpi": "PAT", "unit": "INR"}, "value": 890000, "period": "2026-07"},
    {"entity_type": "kpi", "dimensions": {"kpi": "GrossMarginPct", "unit": "percent"}, "value": 38.5, "period": "2026-07"},
    {"entity_type": "kpi", "dimensions": {"kpi": "CashAndBank", "unit": "INR"}, "value": 2100000, "period": "2026-07"},
    {"entity_type": "kpi", "dimensions": {"kpi": "DSO", "unit": "days"}, "value": 42, "period": "2026-07"},
    {"entity_type": "kpi", "dimensions": {"kpi": "DPO", "unit": "days"}, "value": 35, "period": "2026-07"},
    {"entity_type": "kpi", "dimensions": {"kpi": "CurrentRatio", "unit": "ratio"}, "value": 1.8, "period": "2026-07"},
    {"entity_type": "kpi", "dimensions": {"kpi": "CashRunwayMonths", "unit": "months"}, "value": 8, "period": "2026-07"},
    {"entity_type": "pnl_line", "dimensions": {"line": "Revenue"}, "amount_decimal": "12500000", "period": "2026-07"},
    {"entity_type": "pnl_line", "dimensions": {"line": "COGS"}, "amount_decimal": "7687500", "period": "2026-07"},
    {"entity_type": "pnl_line", "dimensions": {"line": "Gross Profit"}, "amount_decimal": "4812500", "period": "2026-07"},
    {"entity_type": "pnl_line", "dimensions": {"line": "Operating Expenses"}, "amount_decimal": "3200000", "period": "2026-07"},
    {"entity_type": "pnl_line", "dimensions": {"line": "EBIT"}, "amount_decimal": "1612500", "period": "2026-07"},
    {"entity_type": "pnl_line", "dimensions": {"line": "Tax"}, "amount_decimal": "402500", "period": "2026-07"},
    {"entity_type": "pnl_line", "dimensions": {"line": "PAT"}, "amount_decimal": "890000", "period": "2026-07"},
    {"entity_type": "cash_summary", "dimensions": {"line": "Operating"}, "amount_decimal": "1450000", "period": "2026-07"},
    {"entity_type": "cash_summary", "dimensions": {"line": "Investing"}, "amount_decimal": "-320000", "period": "2026-07"},
    {"entity_type": "cash_summary", "dimensions": {"line": "Financing"}, "amount_decimal": "-180000", "period": "2026-07"},
    {"entity_type": "cash_summary", "dimensions": {"line": "Net Change"}, "amount_decimal": "950000", "period": "2026-07"},
    {"entity_type": "aging_bucket", "dimensions": {"side": "AR", "bucket": "Current"}, "amount_decimal": "820000", "period": "2026-07"},
    {"entity_type": "aging_bucket", "dimensions": {"side": "AR", "bucket": "1-30"}, "amount_decimal": "410000", "period": "2026-07"},
    {"entity_type": "aging_bucket", "dimensions": {"side": "AR", "bucket": "31-60"}, "amount_decimal": "180000", "period": "2026-07"},
    {"entity_type": "aging_bucket", "dimensions": {"side": "AP", "bucket": "Current"}, "amount_decimal": "520000", "period": "2026-07"},
    {"entity_type": "aging_bucket", "dimensions": {"side": "AP", "bucket": "1-30"}, "amount_decimal": "260000", "period": "2026-07"},
    {"entity_type": "aging_bucket", "dimensions": {"side": "AP", "bucket": "31-60"}, "amount_decimal": "90000", "period": "2026-07"},
]


def json_res(route, data):
    route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(data),
    )


def start_frontend_server():
    proc = subprocess.Popen(
        [PY, "scripts/serve_frontends.py", "--host", "127.0.0.1", "--port", "3300"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(40):
        try:
            urllib.request.urlopen(URL, timeout=1)
            print("+ frontend server ready on 127.0.0.1:3300")
            return proc
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.5)
    proc.terminate()
    raise RuntimeError("Timed out waiting for scripts/serve_frontends.py on port 3300")


def mock_officemitra_routes(page):
    page.route("**/api/v1/officemitra/ping**", lambda r: json_res(r, {
        "module": "office_ai",
        "writeback_enabled": True,
        "workflows_enabled": False,
        "mis_enabled": True,
        "mis_capabilities": {"import": True, "export": True},
    }))
    page.route("**/api/v1/officemitra/tasks**", lambda r: json_res(r, {
        "items": [
            {"id": "task-1", "title": "Follow up GST filing checklist", "status": "open", "source": "manual"},
            {"id": "task-2", "title": "Review vendor payment batch", "status": "open", "source": "ai"},
            {"id": "task-3", "title": "Send MIS pack to client CFO", "status": "done", "source": "manual"},
        ],
    }))
    page.route("**/api/v1/officemitra/emails**", lambda r: json_res(r, {
        "items": [
            {"summary": "Client requested July MIS pack by Friday; attach PPT after checker approval."},
        ],
    }))
    page.route("**/api/v1/officemitra/briefs/today**", lambda r: json_res(r, {
        "item": {
            "content": (
                "Today — Demo Business Tenant\n\n"
                "• 3 open tasks (1 AI-suggested)\n"
                "• GST filing checklist due in 4 days\n"
                "• Board call at 11:00 UTC\n\n"
                "Advisory only — review before acting."
            ),
            "generation_id": "brief-manual-demo",
            "prompt_version": "daily_brief_v1",
        },
    }))
    page.route("**/api/v1/officemitra/calendar/today**", lambda r: json_res(r, {
        "items": [
            {
                "title": "Board call",
                "starts_at": "2026-08-12T11:00:00+00:00",
                "location": "Zoom",
                "source": "manual",
            },
        ],
    }))
    page.route("**/api/v1/officemitra/meeting-notes**", lambda r: json_res(r, {"items": []}))
    page.route("**/api/v1/officemitra/notifications**", lambda r: json_res(r, {
        "items": [
            {
                "id": "n1",
                "title": "Today: Board call",
                "kind": "calendar_due",
                "created_at": "2026-08-12T08:00:00+00:00",
            },
        ],
        "unread_count": 1,
        "count": 1,
    }))
    page.route("**/api/v1/officemitra/proposals**", lambda r: json_res(r, {
        "items": [
            {
                "id": "prop-1",
                "action_type": "create_task",
                "status": "pending",
                "confidence": 0.82,
                "payload": {"title": "Email client MIS export link"},
            },
            {
                "id": "prop-2",
                "action_type": "mis_export_ppt",
                "status": "awaiting_checker",
                "confidence": 0.91,
                "payload": {"pack_id": MIS_PACK_ID},
            },
        ],
    }))
    page.route("**/api/v1/officemitra/mis/pack-catalog**", lambda r: json_res(r, {
        "items": [
            {"pack_key": "manufacturing", "display_name": "Manufacturing MIS", "enabled_for_tenant": True},
            {"pack_key": "sme_general", "display_name": "SME General", "enabled_for_tenant": True},
        ],
    }))
    page.route("**/api/v1/officemitra/mis/packs**", lambda r: json_res(r, {
        "items": [
            {
                "id": MIS_PACK_ID,
                "pack_key": "manufacturing",
                "display_name": "Manufacturing MIS",
                "period": "2026-07",
                "status": "pending_reconcile",
                "data_quality_score": None,
                "immutable": False,
            },
        ],
    }))

    def mis_facts_handler(route):
        if MIS_PACK_ID not in route.request.url:
            return json_res(route, {"items": []})
        return json_res(route, {"items": MIS_FACTS})

    page.route("**/api/v1/officemitra/mis/packs/*/facts**", mis_facts_handler)


def mock_routes(page):
    # Mock Auth & Tenant session
    page.route("**/api/v1/auth/session**", lambda r: json_res(r, {
        "authenticated": True,
        "user": {"email": "businessadmin@sanmitra.local", "name": "Business Admin", "role": "tenant_admin"},
        "tenant": {"id": "demo-mitrabooks-business", "name": "Demo Business Tenant", "app_key": "mitrabooks"}
    }))

    page.route("**/api/v1/tenants/current**", lambda r: json_res(r, {
        "tenant_id": "demo-mitrabooks-business",
        "name": "Demo Business Tenant",
        "organization_type": "BUSINESS",
        "enabled_modules": [
            "mitrabooks",
            "office_ai",
            "office_ai.mis",
            "office_ai.mis.import",
            "office_ai.mis.export",
            "office_ai.writeback",
            "hr",
            "manufacturing",
        ],
    }))

    page.route("**/health**", lambda r: json_res(r, {"status": "ok"}))
    page.route("**/api/v1/modules/me**", lambda r: json_res(r, {
        "tenant_id": "demo-mitrabooks-business",
        "tenant_name": "Demo Business Tenant",
        "organization_type": "BUSINESS",
        "role": "tenant_admin",
        "enabled_modules": [
            {"module_key": "business", "display_name": "MitraBooks Business Operations", "frontend_path": "/business", "enabled": True},
            {"module_key": "accounting", "display_name": "MitraBooks Accounting Engine", "frontend_path": "/accounting", "enabled": True},
            {"module_key": "office_ai", "display_name": "OfficeMitra AI", "frontend_path": "/business/office-ai", "enabled": True},
            {"module_key": "hr", "display_name": "HR & Payroll", "frontend_path": "/business/hr", "enabled": True},
            {"module_key": "manufacturing", "display_name": "Manufacturing & Cost Centres", "frontend_path": "/business/manufacturing", "enabled": True},
        ],
        "available_modules": [],
    }))

    mock_officemitra_routes(page)

    # Mock HR add-on so the HR workspace shows actual Employees/Payroll/Analytics tabs.
    page.route("**/api/v1/business/hr/access**", lambda r: json_res(r, {
        "entitled": True,
        "available": True,
        "can_manage": True,
        "can_enable": False,
    }))
    page.route("**/api/v1/business/hr/salary-structures**", lambda r: json_res(r, {
        "structures": [
            {
                "structure_id": "st-1",
                "name": "Standard (Non-metro)",
                "components": [
                    {"abbr": "BASIC"},
                    {"abbr": "HRA"},
                ],
            }
        ]
    }))
    page.route("**/api/v1/business/hr/appointment-settings**", lambda r: json_res(r, {
        "probation_months": 6,
        "notice_days": 30,
        "work_hours": "9:30 AM to 6:30 PM, Monday to Friday",
        "signatory_name": "HR Head",
        "signatory_title": "Authorised Signatory",
        "clauses": {
            "background_check": True,
            "confidentiality_nda": True,
            "ip_assignment": False,
            "data_privacy": True,
            "code_of_conduct": True,
            "cash_handling": False,
            "relocation": False,
        },
    }))
    page.route("**/api/v1/business/hr/employees**", lambda r: json_res(r, {
        "employees": [
            {
                "employee_id": "emp-1",
                "employee_code": "EMP-001",
                "full_name": "Asha Rao",
                "designation": "HR Executive",
                "status": "active",
            }
        ]
    }))
    page.route("**/api/v1/business/hr/payroll/runs**", lambda r: json_res(r, {
        "runs": [],
    }))
    page.route("**/api/v1/business/hr/analytics/dashboard**", lambda r: json_res(r, {
        "summary": {
            "active_employees": 1,
            "exited_employees": 0,
            "latest_period": "2026-06",
            "latest_net_payout": 123456.78,
            "latest_tds": 3456.0,
        },
        "labels": ["2026-04", "2026-05", "2026-06"],
        "datasets": {
            "net_disbursed": [100000, 110000, 123456.78],
            "tds_liability": [3000, 3200, 3456.0],
        }
    }))

    # Mock Chart of Accounts (COA) / Core Ledger
    page.route("**/api/v1/accounting/accounts**", lambda r: json_res(r, [
        {"account_id": 101, "code": "11001", "name": "Cash in Hand", "type": "Asset", "balance": "1400.00"},
        {"account_id": 102, "code": "11010", "name": "HDFC Bank Account", "type": "Asset", "balance": "587770.00"},
        {"account_id": 103, "code": "12001", "name": "Sundry Debtors", "type": "Asset", "balance": "313970.00"},
        {"account_id": 104, "code": "21001", "name": "Sundry Creditors", "type": "Liability", "balance": "176440.00"},
        {"account_id": 105, "code": "41001", "name": "Sales Revenue", "type": "Revenue", "balance": "381500.00"},
        {"account_id": 106, "code": "51001", "name": "Purchase Expenses", "type": "Expense", "balance": "236350.00"}
    ]))

    # Mock Accounting Drilldown endpoint
    page.route("**/api/v1/accounting/reports/drilldown**", lambda r: json_res(r, {
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
    }))

    # Mock Manufacturing add-on so the Manufacturing workspace shows Cost Centres + hierarchy.
    page.route("**/api/v1/business/mfg/access**", lambda r: json_res(r, {
        "cost_centre_active": True,
        "cost_centre_available": True,
        "manufacturing_active": True,
        "can_manage_cost_centre": True,
        "can_manage_manufacturing": True,
        "can_enable_cost_centre": False,
        "can_enable_manufacturing": False,
    }))
    page.route("**/api/v1/business/dimensions**", lambda r: json_res(r, {
        "cost_centres": [
            {
                "dimension_id": "dim-cc-blr",
                "dimension_type": "cost_centre",
                "code": "BLR",
                "name": "Bengaluru",
                "parent_code": "",
                "is_active": True,
            }
        ]
    }))
    page.route("**/api/v1/business/mfg/cost-centre/tree**", lambda r: json_res(r, {
        "roots": [
            {
                "code": "BLR",
                "name": "Bengaluru",
                "is_active": True,
                "children": [],
            }
        ],
    }))
    page.route("**/api/v1/business/mfg/cost-centre/budgets**", lambda r: json_res(r, {
        "items": [],
    }))
    page.route("**/api/v1/business/inventory/items**", lambda r: json_res(r, {
        "items": [
            {"item_id": "item-1", "code": "WIDGET-A", "name": "Widget A", "is_active": True}
        ]
    }))
    page.route("**/api/v1/business/mfg/boms**", lambda r: json_res(r, {
        "items": [],
    }))
    page.route("**/api/v1/business/mfg/work-orders**", lambda r: json_res(r, {
        "items": [],
    }))

    # Mock Parties Master
    page.route("**/api/v1/parties**", lambda r: json_res(r, [
        {"party_id": "P001", "name": "Zenith Manufacturing Ltd", "party_type": "customer", "gstin": "29ABCDE1234F1Z5", "city": "Bengaluru", "outstanding": "125000.00"},
        {"party_id": "P002", "name": "Blue Ocean Exports Pvt Ltd", "party_type": "customer", "gstin": "29BCDEF2345G2Z6", "city": "Mumbai", "outstanding": "85000.00"},
        {"party_id": "P003", "name": "Bengaluru Electronics Hub", "party_type": "vendor", "gstin": "29CDEFG3456H3Z7", "city": "Bengaluru", "outstanding": "66080.00"}
    ]))

    # Mock Sales Invoices
    page.route("**/api/v1/business/sales/invoices**", lambda r: json_res(r, [
        {"invoice_id": "INV-001", "invoice_number": "INV-2026-001", "party_name": "Zenith Manufacturing Ltd", "date": "2026-06-10", "total_amount": "125000.00", "status": "posted"},
        {"invoice_id": "INV-002", "invoice_number": "INV-2026-002", "party_name": "Blue Ocean Exports Pvt Ltd", "date": "2026-06-12", "total_amount": "85000.00", "status": "posted"}
    ]))

    # Mock Vouchers List
    page.route("**/api/v1/vouchers**", lambda r: json_res(r, [
        {"voucher_id": "V001", "voucher_number": "PV-2026-001", "voucher_type": "payment", "date": "2026-06-01", "amount": "45000.00", "status": "posted"},
        {"voucher_id": "V002", "voucher_number": "RV-2026-008", "voucher_type": "receipt", "date": "2026-06-05", "amount": "125000.00", "status": "posted"}
    ]))

    # Mock Trial Balance / Financial Reports
    page.route("**/api/v1/accounting/reports/trial-balance**", lambda r: json_res(r, {
        "as_of": "2026-06-30",
        "balanced": True,
        "lines": [
            {"account_code": "11001", "account_name": "Cash in Hand", "debit_total": "1400.00", "credit_total": "0.00", "net_balance": "1400.00"},
            {"account_code": "11010", "account_name": "HDFC Bank Account", "debit_total": "587770.00", "credit_total": "0.00", "net_balance": "587770.00"},
            {"account_code": "12001", "account_name": "Sundry Debtors", "debit_total": "313970.00", "credit_total": "0.00", "net_balance": "313970.00"},
            {"account_code": "21001", "account_name": "Sundry Creditors", "debit_total": "0.00", "credit_total": "176440.00", "net_balance": "-176440.00"},
            {"account_code": "41001", "account_name": "Sales Revenue", "debit_total": "0.00", "credit_total": "381500.00", "net_balance": "-381500.00"},
            {"account_code": "51001", "account_name": "Purchase Expenses", "debit_total": "236350.00", "credit_total": "0.00", "net_balance": "236350.00"}
        ]
    }))


def ensure_shell_visible(page):
    """Static-shell mocks may not flip signed-in; unhide ERP chrome for screenshots."""
    page.evaluate(
        """() => {
          const app = document.querySelector('.app');
          if (app) {
            app.classList.add('signed-in');
            app.classList.remove('signed-out');
          }
        }"""
    )


def open_office_ai_workspace(page):
    page.evaluate("() => window.setBusinessWorkspace && window.setBusinessWorkspace('office-ai')")
    page.wait_for_selector("#dashboard-preview [data-office-ai-root]", state="attached", timeout=30000)
    ensure_shell_visible(page)
    time.sleep(2.0)


def screenshot_office_ai_panel(page, filename: str):
    ensure_shell_visible(page)
    preview = page.locator("#dashboard-preview")
    preview.screenshot(path=str(IMG_DIR / filename))


def click_office_ai_tab(page, tab_id: str):
    page.locator(f"[data-office-ai-action='tab'][data-tab='{tab_id}']").click()
    page.wait_for_selector("#dashboard-preview [data-office-ai-root]", state="attached", timeout=15000)
    time.sleep(1.0)


def capture_office_ai_screenshots(page):
    print("Capturing OfficeMitra AI manual screenshots...")
    open_office_ai_workspace(page)
    screenshot_office_ai_panel(page, "24-office-ai-workspace.png")

    click_office_ai_tab(page, "email")
    page.locator("[data-office-ai-field='emailText']").fill(
        "Subject: July MIS pack\n\nPlease share the reconciled MIS pack and PPT after checker approval by Friday."
    )
    screenshot_office_ai_panel(page, "24-3-email-summary.png")

    click_office_ai_tab(page, "proposals")
    screenshot_office_ai_panel(page, "24-8-proposals.png")

    click_office_ai_tab(page, "mis")
    screenshot_office_ai_panel(page, "24-9-mis-packs.png")

    click_office_ai_tab(page, "brief")
    screenshot_office_ai_panel(page, "24-7-brief.png")


def capture_screenshots():
    auth_init = """() => {
            window.sessionStorage.setItem('sanmitra_frontend_access_token', 'static-shell-token');
            window.localStorage.setItem('sanmitra_mitrabooks_login_email', 'businessadmin@sanmitra.local');
            window.localStorage.removeItem('mitrabooks-widget-states');
            window.localStorage.removeItem('sanmitra_frontend_api_base_url');
            window.SANMITRA_API_BASE_URL = window.location.origin;
        }"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=2)
        context.add_init_script(auth_init)

        # Login page (unsigned)
        login_page = context.new_page()
        login_page.goto(URL)
        login_page.wait_for_selector("#access-panel", timeout=15000)
        print("Capturing 02-1-login.png...")
        login_page.screenshot(path=str(IMG_DIR / "02-1-login.png"), full_page=False)
        login_page.close()

        page = context.new_page()
        mock_routes(page)
        page.goto(URL)
        page.wait_for_selector(".dashboard-quick-execution-bar", state="attached", timeout=30000)
        time.sleep(2.0)
        # Our route-mocking does not always flip the app's signed-in state; force
        # it so the manual screenshots are from the actual workspaces (not login).
        ensure_shell_visible(page)

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
        # Use the app's workspace switcher to avoid fragile DOM selectors.
        page.evaluate("() => window.setBusinessWorkspace && window.setBusinessWorkspace('hr')")
        page.wait_for_function(
            """() => {
              const el = document.querySelector('#dashboard-preview h4');
              return !!el && (el.textContent || '').includes('HR & Payroll');
            }""",
            timeout=30000,
        )
        time.sleep(1.5)
        page.screenshot(path=str(IMG_DIR / "22-hr-workspace.png"), full_page=False)

        # 11. Manufacturing (23-mfg-workspace.png)
        print("Capturing 23-mfg-workspace.png...")
        page.evaluate("() => window.setBusinessWorkspace && window.setBusinessWorkspace('manufacturing')")
        page.wait_for_function(
            """() => {
              const el = document.querySelector('#dashboard-preview h4');
              return !!el && (el.textContent || '').includes('Manufacturing & Cost Centres');
            }""",
            timeout=30000,
        )
        time.sleep(1.5)
        page.screenshot(path=str(IMG_DIR / "23-mfg-workspace.png"), full_page=False)

        capture_office_ai_screenshots(page)

        browser.close()


if __name__ == "__main__":
    server = start_frontend_server()
    try:
        capture_screenshots()
        print("All screenshots successfully captured!")
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
