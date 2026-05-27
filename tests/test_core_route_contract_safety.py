from app.main import app


def _route_keys() -> set[tuple[str, str]]:
    return {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
        if method not in {"HEAD", "OPTIONS"}
    }


def test_accounting_and_module_route_contracts_are_registered() -> None:
    routes = _route_keys()

    expected = {
        ("GET", "/api/v1/modules/me"),
        ("GET", "/api/v1/accounting/accounts"),
        ("POST", "/api/v1/accounting/accounts"),
        ("GET", "/api/v1/accounting/journal"),
        ("GET", "/api/v1/accounting/journal/{journal_id}"),
        ("POST", "/api/v1/accounting/journal"),
        ("POST", "/api/v1/accounting/journal/from-source"),
        ("POST", "/api/v1/accounting/journal/{journal_id}/reverse"),
        ("GET", "/api/v1/accounting/ledger/{account_id}"),
        ("GET", "/api/v1/accounting/reports/trial-balance"),
        ("GET", "/api/v1/accounting/reports/balance-sheet"),
        ("GET", "/api/v1/accounting/reports/drilldown"),
        ("GET", "/api/v1/accounting/reports/vouchers/{journal_id}"),
    }

    assert expected <= routes


def test_mandirmitra_route_contracts_are_registered() -> None:
    routes = _route_keys()

    expected = {
        ("GET", "/api/v1/dashboard/stats"),
        ("GET", "/api/v1/donations"),
        ("POST", "/api/v1/donations"),
        ("GET", "/api/v1/donations/{donation_id}/receipt/pdf"),
        ("POST", "/api/v1/donations/{donation_id}/cancel"),
        ("GET", "/api/v1/sevas"),
        ("GET", "/api/v1/sevas/bookings"),
        ("POST", "/api/v1/sevas/bookings"),
        ("GET", "/api/v1/sevas/bookings/{booking_id}/receipt/pdf"),
        ("POST", "/api/v1/sevas/bookings/{booking_id}/cancel"),
        ("GET", "/api/v1/public-payments"),
        ("PATCH", "/api/v1/public-payments/{payment_id}/verify"),
        ("PATCH", "/api/v1/public-payments/{payment_id}/reject"),
        ("PATCH", "/api/v1/public-payments/{payment_id}/correction"),
        ("GET", "/api/v1/reports/donations/detailed"),
        ("GET", "/api/v1/reports/sevas/detailed"),
    }

    assert expected <= routes


def test_gruhamitra_route_contracts_are_registered() -> None:
    routes = _route_keys()

    expected = {
        ("GET", "/api/v1/dashboard/summary"),
        ("GET", "/api/v1/flats"),
        ("GET", "/api/v1/flats/{flat_id}"),
        ("POST", "/api/v1/flats/"),
        ("PUT", "/api/v1/flats/{flat_id}"),
        ("POST", "/api/v1/journal"),
        ("GET", "/api/v1/member-onboarding"),
        ("GET", "/api/v1/society/{society_id}"),
        ("GET", "/api/v1/reports/balance-sheet"),
        ("GET", "/api/v1/reports/income-and-expenditure"),
        ("GET", "/api/v1/reports/receipts-and-payments"),
        ("GET", "/api/v1/transactions"),
        ("POST", "/api/v1/transactions/payment"),
        ("POST", "/api/v1/transactions/receipt"),
        ("GET", "/api/v1/transactions/vouchers/{journal_entry_id}/pdf"),
    }

    assert expected <= routes


def test_legalmitra_route_contracts_are_registered() -> None:
    routes = _route_keys()

    expected = {
        ("GET", "/api/v1/legal/cases"),
        ("POST", "/api/v1/legal/cases"),
        ("GET", "/api/v1/legal/news"),
        ("GET", "/api/v1/legal/judgements"),
        ("GET", "/api/v1/legal/web-search-rag"),
        ("POST", "/api/v1/legal-research"),
        ("GET", "/api/v1/legalmitra/history"),
        ("GET", "/api/v1/legalmitra/uploads"),
        ("POST", "/api/v1/rag/documents"),
        ("GET", "/api/v1/rag/documents"),
        ("POST", "/api/v1/rag/query"),
    }

    assert expected <= routes
