from fastapi.testclient import TestClient

import pytest

import app.core.platform_owner.router as platform_owner_router
import app.core.platform_owner.service as platform_owner_service
from app.core.auth.dependencies import get_current_user
from app.main import app


@pytest.mark.asyncio
async def test_platform_owner_dashboard_contract_counts_tenants_and_onboarding(monkeypatch):
    async def fake_list_tenants(*, limit: int = 500, status: str | None = None):
        assert limit == 500
        assert status is None
        return [
            {
                "tenant_id": "temple-1",
                "display_name": "Temple One",
                "status": "active",
                "organization_type": "TEMPLE",
                "enabled_modules": ["temple", "accounting", "audit"],
                "app_keys": ["mandirmitra"],
                "subscription_plan": "free",
            },
            {
                "tenant_id": "society-1",
                "display_name": "Society One",
                "status": "inactive",
                "organization_type": "HOUSING",
                "enabled_modules": ["housing", "accounting", "audit"],
                "app_keys": ["gruhamitra"],
                "subscription_plan": "pro",
            },
            {
                "tenant_id": "business-1",
                "display_name": "Business One",
                "status": "active",
                "organization_type": "BUSINESS",
                "enabled_modules": ["business", "accounting", "gst", "inventory", "audit"],
                "app_keys": ["mitrabooks"],
                "subscription_plan": "trial",
            },
        ]

    async def fake_list_onboarding_requests(*, limit: int = 500, status: str | None = None, app_key: str | None = None):
        assert limit == 500
        assert status is None
        assert app_key is None
        return [
            {
                "request_id": "req-mandir-pending",
                "status": "pending",
                "app_key": "mandirmitra",
                "tenant_name": "Temple Two",
                "admin_email": "temple@example.com",
                "submitted_at": "2026-05-19T10:00:00+05:30",
            },
            {
                "request_id": "req-gruha-approved",
                "status": "approved",
                "app_key": "gruhamitra",
                "tenant_name": "Society Two",
                "admin_email": "society@example.com",
                "approved_tenant_id": "society-2",
            },
            {
                "request_id": "req-mitra-rejected",
                "status": "rejected",
                "app_key": "mitrabooks",
                "tenant_name": "Business Two",
                "admin_email": "business@example.com",
                "rejection_reason": "Incomplete documents",
            },
        ]

    async def fake_list_billing_transactions(*, limit: int = 500):
        assert limit == 500
        return [
            {
                "record_type": "billing_transaction",
                "display_name": "Jayanthi M Rao",
                "payer_email": "jayanthi@example.com",
                "app_key": "legalmitra",
                "app_keys": ["legalmitra"],
                "subscription_plan": "basic",
                "subscription_status": "active",
                "billing_cycle": "monthly",
            }
        ]

    monkeypatch.setattr(platform_owner_service, "list_tenants", fake_list_tenants)
    monkeypatch.setattr(platform_owner_service, "list_onboarding_requests", fake_list_onboarding_requests)
    monkeypatch.setattr(platform_owner_service, "list_billing_transactions", fake_list_billing_transactions)

    dashboard = await platform_owner_service.get_platform_owner_dashboard(limit=10)

    assert dashboard["summary"]["onboarding"]["total"] == 3
    assert dashboard["summary"]["onboarding"]["by_status"] == {
        "pending": 1,
        "payment_pending": 0,
        "payment_received": 0,
        "under_review": 0,
        "approved": 1,
        "rejected": 1,
    }
    assert dashboard["summary"]["onboarding"]["by_app_key"]["mandirmitra"]["pending"] == 1
    assert dashboard["summary"]["tenants"]["total"] == 3
    assert dashboard["summary"]["tenants"]["by_status"] == {"active": 2, "inactive": 1}
    assert dashboard["summary"]["tenants"]["by_app_key"] == {"mandirmitra": 1, "gruhamitra": 1, "mitrabooks": 1}
    assert dashboard["summary"]["subscriptions"]["by_plan"] == {"free": 1, "pro": 1, "trial": 1, "basic": 1}
    assert {"module_key": "accounting", "tenant_count": 3} in dashboard["module_status"]
    assert dashboard["pending_approvals"][0]["request_id"] == "req-mandir-pending"
    assert any(row["display_name"] == "Jayanthi M Rao" for row in dashboard["subscription_records"])


@pytest.mark.asyncio
async def test_platform_owner_dashboard_dedupes_duplicate_billing_subscription_records(monkeypatch):
    async def fake_list_tenants(*, limit: int = 500, status: str | None = None):
        return []

    async def fake_list_onboarding_requests(*, limit: int = 500, status: str | None = None, app_key: str | None = None):
        return []

    async def fake_list_billing_transactions(*, limit: int = 500):
        return [
            {
                "record_type": "billing_transaction",
                "display_name": "jayanthimr56@gmail.com",
                "payer_email": "jayanthimr56@gmail.com",
                "app_key": "legalmitra",
                "app_keys": ["legalmitra"],
                "subscription_plan": "basic",
                "subscription_status": "active",
                "billing_cycle": "monthly",
                "razorpay_payment_id": "pay_1",
            },
            {
                "record_type": "billing_transaction",
                "display_name": "jayanthimr56@gmail.com",
                "payer_email": "jayanthimr56@gmail.com",
                "app_key": "legalmitra",
                "app_keys": ["legalmitra"],
                "subscription_plan": "basic",
                "subscription_status": "active",
                "billing_cycle": "monthly",
                "razorpay_payment_id": "pay_1",
            },
        ]

    monkeypatch.setattr(platform_owner_service, "list_tenants", fake_list_tenants)
    monkeypatch.setattr(platform_owner_service, "list_onboarding_requests", fake_list_onboarding_requests)
    monkeypatch.setattr(platform_owner_service, "list_billing_transactions", fake_list_billing_transactions)

    dashboard = await platform_owner_service.get_platform_owner_dashboard(limit=10)

    matching = [
        row
        for row in dashboard["subscription_records"]
        if row.get("payer_email") == "jayanthimr56@gmail.com"
    ]
    assert len(matching) == 1
    assert dashboard["summary"]["subscriptions"]["by_plan"] == {"basic": 1}


def test_platform_owner_dashboard_allows_super_admin(monkeypatch):
    async def fake_dashboard(*, limit: int):
        return {
            "generated_at": "2026-05-19T10:00:00+05:30",
            "summary": {},
            "app_status": [],
            "module_status": [],
            "pending_approvals": [],
            "recent_onboarding_requests": [],
            "recent_tenants": [],
        }

    monkeypatch.setattr(platform_owner_router, "get_platform_owner_dashboard", fake_dashboard)
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "owner@example.com",
        "role": "super_admin",
        "tenant_id": "platform",
        "app_key": "mitrabooks",
    }

    try:
        client = TestClient(app)
        response = client.get("/api/v1/platform-owner/dashboard")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json()["summary"] == {}


def test_platform_owner_dashboard_rejects_tenant_admin(monkeypatch):
    async def fake_dashboard(*, limit: int):
        raise AssertionError("Tenant admin must not reach dashboard service")

    monkeypatch.setattr(platform_owner_router, "get_platform_owner_dashboard", fake_dashboard)
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "tenant@example.com",
        "role": "tenant_admin",
        "tenant_id": "tenant-1",
        "app_key": "mandirmitra",
    }

    try:
        client = TestClient(app)
        response = client.get("/api/v1/platform-owner/dashboard")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403
    assert response.json()["detail"] == "Only super admins can view platform owner dashboard"
