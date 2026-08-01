"""Tests for LegalMitra answer-feedback Stage 2 instrumentation."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.auth.security import create_access_token
from app.main import app


def _auth_headers(tenant_id: str = "tenant-a") -> dict[str, str]:
    token = create_access_token(
        {
            "sub": "legal-user-feedback",
            "email": "legal.feedback@example.com",
            "role": "tenant_admin",
            "tenant_id": tenant_id,
        }
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-App-Key": "legalmitra",
    }


def test_answer_feedback_requires_login() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/legalmitra/answer-feedback",
        json={
            "answer_id": "ans_1",
            "feedback_type": "rating",
            "value": "helpful",
        },
    )
    assert response.status_code == 401


def test_answer_feedback_rejects_cross_tenant_header() -> None:
    client = TestClient(app)
    headers = _auth_headers("tenant-a")
    headers["X-Tenant-ID"] = "tenant-b"
    response = client.post(
        "/api/v1/legalmitra/answer-feedback",
        headers=headers,
        json={
            "answer_id": "ans_1",
            "feedback_type": "rating",
            "value": "helpful",
            "query": "GST Section 54 refund timeline",
            "strategy": "offline_cgst_section_54_refund_fallback",
            "confidence": "medium",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant override not allowed"
