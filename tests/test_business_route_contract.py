from app.core.route_contract import FrontendRouteUsage, extract_backend_routes, find_unmatched_frontend_routes


def test_business_phase2_target_routes_are_registered() -> None:
    usages = [
        FrontendRouteUsage("MitraBooksERP", "GET", "/api/v1/business/parties", "phase2-contract", 1),
        FrontendRouteUsage("MitraBooksERP", "POST", "/api/v1/business/parties", "phase2-contract", 1),
        FrontendRouteUsage("MitraBooksERP", "GET", "/api/v1/business/parties/{param}", "phase2-contract", 1),
        FrontendRouteUsage("MitraBooksERP", "PATCH", "/api/v1/business/parties/{param}", "phase2-contract", 1),
        FrontendRouteUsage("MitraBooksERP", "POST", "/api/v1/business/parties/{param}/deactivate", "phase2-contract", 1),
        FrontendRouteUsage("MitraBooksERP", "GET", "/api/v1/business/vouchers", "phase2-contract", 1),
        FrontendRouteUsage("MitraBooksERP", "POST", "/api/v1/business/vouchers", "phase2-contract", 1),
        FrontendRouteUsage("MitraBooksERP", "GET", "/api/v1/business/vouchers/{param}", "phase2-contract", 1),
        FrontendRouteUsage("MitraBooksERP", "POST", "/api/v1/business/vouchers/{param}/reverse", "phase2-contract", 1),
        FrontendRouteUsage("MitraBooksERP", "GET", "/api/v1/business/ca-documents", "phase2-contract", 1),
        FrontendRouteUsage("MitraBooksERP", "POST", "/api/v1/business/ca-documents", "phase2-contract", 1),
        FrontendRouteUsage("MitraBooksERP", "PATCH", "/api/v1/business/ca-documents/{param}", "phase2-contract", 1),
        FrontendRouteUsage("MitraBooksERP", "GET", "/api/v1/business/invoices", "phase2-contract", 1),
        FrontendRouteUsage("MitraBooksERP", "POST", "/api/v1/business/invoices", "phase2-contract", 1),
        FrontendRouteUsage("MitraBooksERP", "GET", "/api/v1/business/invoices/{param}", "phase2-contract", 1),
        FrontendRouteUsage("MitraBooksERP", "POST", "/api/v1/business/invoices/{param}/cancel", "phase2-contract", 1),
        FrontendRouteUsage("MitraBooksERP", "GET", "/api/v1/business/invoice-settings", "phase2-contract", 1),
        FrontendRouteUsage("MitraBooksERP", "PUT", "/api/v1/business/invoice-settings", "phase2-contract", 1),
        FrontendRouteUsage("MitraBooksERP", "GET", "/api/v1/audit/events", "phase2-contract", 1),
    ]

    unresolved = find_unmatched_frontend_routes(usages, extract_backend_routes())

    assert unresolved == []
