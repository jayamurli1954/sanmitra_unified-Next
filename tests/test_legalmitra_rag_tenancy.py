"""LegalMitra RAG must not use the MandirMitra temple seed tenant."""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.auth import registration_policy as policy
from app.modules.legal_compat.tenancy import (
    DEFAULT_LEGAL_DEMO_TENANT_ID,
    TEMPLE_SEED_TENANT_ID,
    legalmitra_corpus_tenant_id,
    require_legalmitra_ingest_tenant,
)


class _Settings:
    DEMO_LEGAL_TENANT_ID = "demo-legal-firm"
    DEMO_MANDIR_TENANT_ID = "demo-mandir-tenant"
    LEGAL_INGEST_TENANT_ID = ""
    ALLOW_OPEN_REGISTRATION = True


def test_corpus_tenant_is_legal_demo_not_temple(monkeypatch):
    monkeypatch.setattr(
        "app.modules.legal_compat.tenancy.get_settings",
        lambda: _Settings(),
    )
    tenant_id = legalmitra_corpus_tenant_id()
    assert tenant_id == "demo-legal-firm"
    assert tenant_id != TEMPLE_SEED_TENANT_ID


def test_require_legal_ingest_rejects_temple_seed():
    with pytest.raises(ValueError, match="MandirMitra/temple"):
        require_legalmitra_ingest_tenant(TEMPLE_SEED_TENANT_ID, settings=_Settings())


def test_require_legal_ingest_rejects_mandir_demo():
    with pytest.raises(ValueError, match="MandirMitra/temple"):
        require_legalmitra_ingest_tenant("demo-mandir-tenant", settings=_Settings())


def test_legalmitra_open_registration_uses_legal_demo(monkeypatch):
    monkeypatch.setattr(policy, "get_settings", lambda: _Settings())
    tenant_id = asyncio.run(
        policy.resolve_self_service_tenant_id(
            requested_tenant_id=None,
            app_key="legalmitra",
        )
    )
    assert tenant_id == "demo-legal-firm"
    assert tenant_id != TEMPLE_SEED_TENANT_ID


def test_legalmitra_open_registration_remaps_temple_seed(monkeypatch):
    monkeypatch.setattr(policy, "get_settings", lambda: _Settings())
    tenant_id = asyncio.run(
        policy.resolve_self_service_tenant_id(
            requested_tenant_id=TEMPLE_SEED_TENANT_ID,
            app_key="legalmitra",
        )
    )
    assert tenant_id == "demo-legal-firm"


def test_mandirmitra_open_registration_keeps_temple_seed(monkeypatch):
    monkeypatch.setattr(policy, "get_settings", lambda: _Settings())
    tenant_id = asyncio.run(
        policy.resolve_self_service_tenant_id(
            requested_tenant_id=None,
            app_key="mandirmitra",
        )
    )
    assert tenant_id == TEMPLE_SEED_TENANT_ID


def test_public_acts_catalog_uses_legal_demo_tenant(monkeypatch):
    captured: dict[str, str] = {}

    async def fake_list_documents(*, tenant_id, app_key, limit=50):
        captured["tenant_id"] = tenant_id
        captured["app_key"] = app_key
        captured["limit"] = str(limit)
        return [
            {
                "title": "CGST Act",
                "legal_metadata": {"act_name": "CGST Act", "doc_date": "2017-07-01"},
            }
        ]

    monkeypatch.setattr("app.modules.rag.router.list_documents", fake_list_documents)
    monkeypatch.setattr(
        "app.modules.rag.router.legalmitra_corpus_tenant_id",
        lambda: DEFAULT_LEGAL_DEMO_TENANT_ID,
    )
    from app.main import app

    client = TestClient(app)
    response = client.get("/api/v1/rag/acts", headers={"X-App-Key": "legalmitra"})
    assert response.status_code == 200
    body = response.json()
    assert captured["tenant_id"] == DEFAULT_LEGAL_DEMO_TENANT_ID
    assert captured["app_key"] == "legalmitra"
    assert body["count"] == 1
    assert body["acts"][0]["name"] == "CGST Act"


def test_public_acts_catalog_empty_for_non_legal_app(monkeypatch):
    called = {"list": False}

    async def fake_list_documents(**_kwargs):
        called["list"] = True
        return []

    monkeypatch.setattr("app.modules.rag.router.list_documents", fake_list_documents)
    from app.main import app

    client = TestClient(app)
    response = client.get("/api/v1/rag/acts", headers={"X-App-Key": "mandirmitra"})
    assert response.status_code == 200
    assert response.json() == {"acts": [], "count": 0}
    assert called["list"] is False
