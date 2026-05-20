from fastapi.testclient import TestClient

from app.core.auth.security import create_access_token
from app.main import app


def test_legal_cases_get_requires_login() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/legal/cases")
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
