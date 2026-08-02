from fastapi.testclient import TestClient

from app.core.auth.security import create_access_token
from app.main import app


def test_legal_practice_dashboard_requires_login() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/legal/practice/dashboard")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing authorization header"


def test_legal_morning_brief_requires_login() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/legal/practice/morning-brief")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing authorization header"


def test_legal_clients_requires_login() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/legal/clients")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing authorization header"


def test_legal_matters_requires_login() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/legal/matters",
        json={
            "client_id": "00000000-0000-0000-0000-000000000001",
            "title": "Sample Matter",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing authorization header"



def test_legal_cases_post_requires_login() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/legal/cases",
        json={
            "case_title": "Sample Case",
            "client_name": "Sample Client",
            "status": "open",
            "notes": "test",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing authorization header"


def test_legal_cases_rejects_header_tenant_without_token_tenant_for_non_superadmin() -> None:
    client = TestClient(app)
    token = create_access_token(
        {
            "sub": "user-1",
            "email": "user1@example.com",
            "role": "tenant_admin",
            "tenant_id": None,
        }
    )
    response = client.get(
        "/api/v1/legal/cases",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": "tenant-from-header",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Tenant context missing"


def test_legal_v2_templates_requires_login() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/v2/templates")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing authorization header"


def test_legal_v2_templates_rejects_cross_tenant_header() -> None:
    client = TestClient(app)
    token = create_access_token(
        {
            "sub": "legal-user-1",
            "email": "legal.user@example.com",
            "role": "tenant_admin",
            "tenant_id": "tenant-a",
        }
    )

    response = client.get(
        "/api/v1/v2/templates",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": "tenant-b",
            "X-App-Key": "legalmitra",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant override not allowed"


def test_legal_v2_official_forms_rejects_cross_tenant_header() -> None:
    client = TestClient(app)
    token = create_access_token(
        {
            "sub": "legal-user-1",
            "email": "legal.user@example.com",
            "role": "tenant_admin",
            "tenant_id": "tenant-a",
        }
    )

    response = client.get(
        "/api/v1/v2/official-forms",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": "tenant-b",
            "X-App-Key": "legalmitra",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant override not allowed"


def test_legal_news_requires_login() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/legal/news", params={"query": "tenant eviction"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing authorization header"


def test_legal_judgements_requires_login() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/legal/judgements", params={"query": "rera compliance"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing authorization header"


def test_legal_web_search_rag_requires_login() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/legal/web-search-rag", params={"query": "latest tenancy law"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing authorization header"


def test_rag_query_rejects_cross_tenant_header_before_retrieval(monkeypatch) -> None:
    async def active_tenant(_tenant_id: str | None) -> None:
        return None

    async def legal_tenant(tenant_id: str) -> dict:
        return {
            "tenant_id": tenant_id,
            "organization_type": "LEGAL",
            "enabled_modules": ["legal", "rag", "compliance", "audit"],
        }

    monkeypatch.setattr("app.core.auth.dependencies.ensure_tenant_is_active", active_tenant)
    monkeypatch.setattr("app.core.modules.dependencies.get_tenant", legal_tenant)
    client = TestClient(app)
    token = create_access_token(
        {
            "sub": "legal-user-1",
            "role": "viewer",
            "tenant_id": "tenant-a",
            "app_key": "legalmitra",
        }
    )

    response = client.post(
        "/api/v1/rag/query",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": "tenant-b",
            "X-App-Key": "legalmitra",
        },
        json={"query": "Explain tenant eviction safeguards"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant override not allowed"


def test_rag_documents_rejects_cross_app_header_before_listing(monkeypatch) -> None:
    async def active_tenant(_tenant_id: str | None) -> None:
        return None

    monkeypatch.setattr("app.core.auth.dependencies.ensure_tenant_is_active", active_tenant)
    client = TestClient(app)
    token = create_access_token(
        {
            "sub": "legal-user-1",
            "role": "viewer",
            "tenant_id": "tenant-a",
            "app_key": "legalmitra",
        }
    )

    response = client.get(
        "/api/v1/rag/documents",
        headers={
            "Authorization": f"Bearer {token}",
            "X-App-Key": "mandirmitra",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "App key override not allowed"


def test_rag_query_rejects_tenant_without_rag_module(monkeypatch) -> None:
    async def active_tenant(_tenant_id: str | None) -> None:
        return None

    async def tenant_without_rag(tenant_id: str) -> dict:
        return {
            "tenant_id": tenant_id,
            "organization_type": "LEGAL",
            "enabled_modules": ["legal", "compliance", "audit"],
        }

    monkeypatch.setattr("app.core.auth.dependencies.ensure_tenant_is_active", active_tenant)
    monkeypatch.setattr("app.core.modules.dependencies.get_tenant", tenant_without_rag)
    client = TestClient(app)
    token = create_access_token(
        {
            "sub": "legal-user-no-rag",
            "role": "viewer",
            "tenant_id": "tenant-without-rag",
            "app_key": "legalmitra",
        }
    )

    response = client.post(
        "/api/v1/rag/query",
        headers={
            "Authorization": f"Bearer {token}",
            "X-App-Key": "legalmitra",
        },
        json={"query": "Explain tenant eviction safeguards"},
    )

    assert response.status_code == 403
    assert "not enabled" in response.json()["detail"]


def test_rag_query_repeated_malformed_tokens_remain_fail_closed() -> None:
    client = TestClient(app)

    for _ in range(5):
        response = client.post(
            "/api/v1/rag/query",
            headers={
                "Authorization": "Bearer malformed.not-a-valid-token",
                "X-App-Key": "legalmitra",
            },
            json={"query": "Explain tenant eviction safeguards"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid token"


def test_legal_rag_web_proxy_returns_429_after_abuse_threshold(monkeypatch) -> None:
    from app.core.rate_limiting import limiter

    async def active_tenant(_tenant_id: str | None) -> None:
        return None

    async def legal_tenant(tenant_id: str) -> dict:
        return {
            "tenant_id": tenant_id,
            "organization_type": "LEGAL",
            "enabled_modules": ["legal", "rag", "compliance", "audit"],
        }

    monkeypatch.setattr("app.core.auth.dependencies.ensure_tenant_is_active", active_tenant)
    monkeypatch.setattr("app.core.modules.dependencies.get_tenant", legal_tenant)
    monkeypatch.setattr(
        "app.modules.legal.router.legal_web_search.enrich_rag_context",
        lambda query: {"success": True, "context": query, "num_sources": 0},
    )
    token = create_access_token(
        {
            "sub": "legal-user-rate-test",
            "role": "viewer",
            "tenant_id": "tenant-legal-rate-test",
            "app_key": "legalmitra",
        }
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-App-Key": "legalmitra",
    }

    limiter.reset()
    try:
        client = TestClient(app)
        responses = [
            client.get(
                "/api/v1/legal/web-search-rag",
                params={"query": "tenant eviction safeguards"},
                headers=headers,
            )
            for _ in range(11)
        ]

        assert [response.status_code for response in responses[:10]] == [200] * 10
        assert responses[10].status_code == 429
        assert "Rate limit exceeded" in responses[10].json()["error"]
    finally:
        limiter.reset()


def test_legal_demo_user_bootstrap_and_login(monkeypatch) -> None:
    from app.core.auth.security import hash_password

    async def mock_get_user(email: str):
        if email.strip().lower() == "legal.demo@sanmitra.local":
            return {
                "user_id": "demo-legal-user-1",
                "email": "legal.demo@sanmitra.local",
                "full_name": "Demo LegalMitra Advocate",
                "tenant_id": "demo-legal-firm",
                "app_key": "legalmitra",
                "role": "tenant_admin",
                "hashed_password": hash_password("LocalAdmin123"),
                "is_active": True,
            }
        return None

    class MockCollection:
        async def find_one(self, *args, **kwargs):
            return None
        async def insert_one(self, *args, **kwargs):
            return None
        async def update_one(self, *args, **kwargs):
            return None
        async def create_index(self, *args, **kwargs):
            return None

    async def mock_ensure_active(tenant_id: str):
        return True

    monkeypatch.setattr("app.core.auth.service.get_user_by_email", mock_get_user)
    monkeypatch.setattr("app.core.auth.service._refresh_collection", lambda: MockCollection())
    monkeypatch.setattr("app.core.auth.service.ensure_tenant_is_active", mock_ensure_active)

    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/login",
        headers={"X-App-Key": "legalmitra", "Content-Type": "application/json"},
        json={"email": "legal.demo@sanmitra.local", "password": "LocalAdmin123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"






