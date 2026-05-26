from io import BytesIO

from pypdf import PdfReader

from app.accounting.report_alias_router import _report_pdf_bytes
from app.main import app
from app.modules.mitrabooks_compat.router import _txn_doc, _voucher_pdf_bytes


def _route_keys() -> set[tuple[str, str]]:
    return {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
        if method not in {"HEAD", "OPTIONS"}
    }


def test_gruhamitra_dashboard_and_flat_aliases_are_registered():
    routes = _route_keys()

    assert ("GET", "/api/v1/dashboard/summary") in routes
    assert ("GET", "/api/v1/flats") in routes


def test_gruhamitra_frontend_aliases_are_registered():
    routes = _route_keys()

    expected = {
        ("POST", "/api/v1/journal"),
        ("PUT", "/api/v1/auth/me"),
        ("POST", "/api/v1/database/backup-on-logout"),
        ("GET", "/api/v1/users/"),
        ("PATCH", "/api/v1/users/{user_id}/role"),
        ("GET", "/api/v1/member-onboarding"),
        ("GET", "/api/v1/member-onboarding/debug"),
        ("GET", "/api/v1/member-onboarding/my-profile"),
        ("GET", "/api/v1/society/{society_id}"),
        ("POST", "/api/v1/v2/societies/{society_id}/join-requests"),
    }

    assert expected <= routes


def test_gruhamitra_file_and_import_compat_routes_are_registered():
    routes = _route_keys()

    expected = {
        ("POST", "/api/v1/attachments/upload/{journal_entry_id}"),
        ("GET", "/api/v1/attachments/journal/{journal_entry_id}"),
        ("GET", "/api/v1/attachments/{attachment_id}"),
        ("DELETE", "/api/v1/attachments/{attachment_id}"),
        ("POST", "/api/v1/resources/files/upload"),
        ("GET", "/api/v1/resources/files"),
        ("GET", "/api/v1/resources/files/{file_id}"),
        ("GET", "/api/v1/resources/files/{file_id}/download"),
        ("DELETE", "/api/v1/resources/files/{file_id}"),
        ("GET", "/api/v1/onboarding-imports/templates/{kind}.csv"),
        ("POST", "/api/v1/onboarding-imports/demo/import"),
        ("POST", "/api/v1/onboarding-imports/import/flats"),
        ("POST", "/api/v1/onboarding-imports/import/members"),
    }

    assert expected <= routes


def test_gruhamitra_accounting_report_aliases_are_registered():
    routes = _route_keys()

    expected = {
        ("GET", "/api/v1/reports/balance-sheet"),
        ("GET", "/api/v1/reports/income-and-expenditure"),
        ("GET", "/api/v1/reports/receipts-and-payments"),
        ("GET", "/api/v1/reports/trial-balance/export/pdf"),
        ("GET", "/api/v1/reports/trial-balance/export/excel"),
        ("GET", "/api/v1/reports/balance-sheet/export/pdf"),
        ("GET", "/api/v1/reports/balance-sheet/export/excel"),
        ("GET", "/api/v1/reports/income-and-expenditure/export/pdf"),
        ("GET", "/api/v1/reports/income-and-expenditure/export/excel"),
        ("GET", "/api/v1/reports/receipts-and-payments/export/pdf"),
        ("GET", "/api/v1/reports/receipts-and-payments/export/excel"),
        ("GET", "/api/v1/reports/general-ledger/export/pdf"),
        ("GET", "/api/v1/reports/general-ledger/export/excel"),
    }

    assert expected <= routes


def test_gruhamitra_voucher_pdf_route_is_registered():
    routes = _route_keys()

    assert ("GET", "/api/v1/transactions/vouchers/{journal_entry_id}/pdf") in routes


def _pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_gruhamitra_voucher_pdf_uses_society_branding():
    pdf = _voucher_pdf_bytes(
        {
            "id": 42,
            "entry_date": "2026-05-26",
            "reference": "PV-000001",
            "description": "Water supply payment",
            "total_debit": 15000,
            "total_credit": 15000,
            "lines": [
                {"account_code": "5060", "account_name": "Water Supply Expense", "debit": 15000, "credit": 0},
                {"account_code": "1010", "account_name": "HDFC Bank Current Account", "debit": 0, "credit": 15000},
            ],
        },
        branding={
            "society_name": "Green Heights RWA",
            "society_address": "12 Lake Road",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pin_code": "560001",
            "contact_phone": "9876543210",
            "contact_email": "office@greenheights.example",
        },
    )

    text = _pdf_text(pdf)
    assert "Green Heights RWA" in text
    assert "12 Lake Road" in text
    assert "9876543210" in text
    assert "office@greenheights.example" in text


def test_gruhamitra_accounting_report_pdf_uses_society_branding():
    pdf = _report_pdf_bytes(
        "Trial Balance",
        {
            "as_of": "2026-05-26",
            "lines": [
                {
                    "account_code": "1010",
                    "account_name": "HDFC Bank Current Account",
                    "debit_total": 100,
                    "credit_total": 0,
                    "net_balance": 100,
                }
            ],
        },
        branding={
            "society_name": "Green Heights RWA",
            "society_address": "12 Lake Road",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pin_code": "560001",
            "contact_phone": "9876543210",
            "contact_email": "office@greenheights.example",
        },
    )

    text = _pdf_text(pdf)
    assert "Green Heights RWA" in text
    assert "Trial Balance" in text
    assert "12 Lake Road" in text


def test_gruhamitra_payment_transaction_preserves_explicit_expense_month():
    doc = _txn_doc(
        {
            "voucher_type": "payment",
            "voucher_number": "PV-000003",
            "voucher_date": "2026-05-26",
            "expense_month": "April, 2026",
            "description": "Salary paid to watchman",
            "amount": 15000,
        },
        tenant_id="tenant-housing",
        app_key="gruhamitra",
        company_id=1,
        txn_id=3,
    )

    assert doc["expense_month"] == "April, 2026"
    assert doc["voucher_date"] == "2026-05-26"
