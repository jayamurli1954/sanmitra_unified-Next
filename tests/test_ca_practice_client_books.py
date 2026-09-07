"""CA Practice: one practice tenant, many client books, book-level isolation."""
from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import (
    apply_header_accounting_entity,
    accounting_entity_allowlist,
    resolve_business_app_tenant,
)
from app.main import app
from app.modules.business.schemas import CaClientCreateRequest, CaDocumentCreateRequest
import app.core.modules.dependencies as module_deps
import app.modules.business.service as business_service

from tests.test_business_phase2 import FakeCollection


class _EntityPayload(BaseModel):
    accounting_entity_id: str = "primary"


@pytest.mark.asyncio
async def test_create_ca_client_allocates_unique_book_and_initializes_coa(monkeypatch):
    clients = FakeCollection()
    coa_calls = []

    monkeypatch.setattr(business_service, "get_collection", lambda _name: clients)

    async def fake_log_audit_event(**_k):
        return None

    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    async def fake_coa(_session, **kwargs):
        coa_calls.append(kwargs)

    monkeypatch.setattr(business_service, "initialize_default_chart_of_accounts", fake_coa)

    first = await business_service.create_ca_client(
        tenant_id="practice-1",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        created_by="partner-1",
        payload=CaClientCreateRequest(client_name="Acme Traders"),
        session=object(),
        organization_type="BUSINESS",
    )
    second = await business_service.create_ca_client(
        tenant_id="practice-1",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        created_by="partner-1",
        payload=CaClientCreateRequest(client_name="Beta Mills"),
        session=object(),
    )

    assert first["accounting_entity_id"] != "primary"
    assert second["accounting_entity_id"] != "primary"
    assert first["accounting_entity_id"] != second["accounting_entity_id"]
    assert first["accounting_entity_id"].startswith("client-")
    assert second["accounting_entity_id"].startswith("client-")
    assert {call["accounting_entity_id"] for call in coa_calls} == {
        first["accounting_entity_id"],
        second["accounting_entity_id"],
    }

    roster = await business_service.list_ca_clients(
        tenant_id="practice-1",
        app_key="mitrabooks",
    )
    assert roster["total"] == 2
    primary_only = await business_service.list_ca_clients(
        tenant_id="practice-1",
        app_key="mitrabooks",
        accounting_entity_id="primary",
    )
    assert primary_only["total"] == 0

    staff_view = await business_service.list_ca_clients(
        tenant_id="practice-1",
        app_key="mitrabooks",
        allowed_entity_ids={first["accounting_entity_id"]},
    )
    assert staff_view["total"] == 1
    assert staff_view["items"][0]["client_name"] == "Acme Traders"


@pytest.mark.asyncio
async def test_ca_documents_stay_on_client_book(monkeypatch):
    clients = FakeCollection()
    documents = FakeCollection()

    def fake_get_collection(name):
        return {
            business_service.CA_CLIENTS_COLLECTION: clients,
            business_service.CA_DOCUMENTS_COLLECTION: documents,
        }[name]

    monkeypatch.setattr(business_service, "get_collection", fake_get_collection)

    async def fake_log_audit_event(**_k):
        return None

    monkeypatch.setattr(business_service, "log_audit_event", fake_log_audit_event)

    client_a = await business_service.create_ca_client(
        tenant_id="practice-1",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        created_by="partner-1",
        payload=CaClientCreateRequest(client_name="Client A Co"),
    )
    client_b = await business_service.create_ca_client(
        tenant_id="practice-1",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        created_by="partner-1",
        payload=CaClientCreateRequest(client_name="Client B Co"),
    )

    doc_a = await business_service.create_ca_document_metadata(
        tenant_id="practice-1",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        created_by="staff-1",
        payload=CaDocumentCreateRequest(
            client_id=client_a["client_id"],
            client_name="Client A Co",
            document_type="Bank statement",
            period="May 2026",
        ),
    )
    doc_b = await business_service.create_ca_document_metadata(
        tenant_id="practice-1",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        created_by="staff-1",
        payload=CaDocumentCreateRequest(
            client_id=client_b["client_id"],
            client_name="Client B Co",
            document_type="GST working",
            period="May 2026",
        ),
    )

    assert doc_a["accounting_entity_id"] == client_a["accounting_entity_id"]
    assert doc_b["accounting_entity_id"] == client_b["accounting_entity_id"]

    listed_a = await business_service.list_ca_document_metadata(
        tenant_id="practice-1",
        app_key="mitrabooks",
        accounting_entity_id=client_a["accounting_entity_id"],
    )
    listed_b = await business_service.list_ca_document_metadata(
        tenant_id="practice-1",
        app_key="mitrabooks",
        accounting_entity_id=client_b["accounting_entity_id"],
    )
    assert listed_a["total"] == 1
    assert listed_a["items"][0]["client_name"] == "Client A Co"
    assert listed_b["total"] == 1
    assert listed_b["items"][0]["client_name"] == "Client B Co"


def test_header_accounting_entity_overrides_payload_default() -> None:
    payload = apply_header_accounting_entity(
        _EntityPayload(),
        x_accounting_entity_id="client-acme-abc123",
    )
    assert payload.accounting_entity_id == "client-acme-abc123"
    unchanged = apply_header_accounting_entity(
        _EntityPayload(accounting_entity_id="client-keep"),
        x_accounting_entity_id=None,
    )
    assert unchanged.accounting_entity_id == "client-keep"


def test_staff_allowlist_and_practice_roster_resolver() -> None:
    staff = {
        "sub": "staff-1",
        "tenant_id": "practice-1",
        "app_key": "mitrabooks",
        "role": "staff",
        "accounting_entity_ids": ["client-a"],
    }
    assert accounting_entity_allowlist(staff) == {"client-a"}
    admin = {
        "sub": "owner-1",
        "tenant_id": "practice-1",
        "app_key": "mitrabooks",
        "role": "tenant_admin",
    }
    assert accounting_entity_allowlist(admin) is None

    with pytest.raises(HTTPException) as exc:
        resolve_business_app_tenant(
            current_user=staff,
            x_tenant_id=None,
            x_app_key="mitrabooks",
            expected_app_key="mitrabooks",
            operation="read",
            x_accounting_entity_id="client-b",
        )
    assert exc.value.status_code == 403

    context = resolve_business_app_tenant(
        current_user=staff,
        x_tenant_id=None,
        x_app_key="mitrabooks",
        expected_app_key="mitrabooks",
        operation="CA client listing",
        x_accounting_entity_id="client-b",
        enforce_entity_allowlist=False,
    )
    assert context.tenant_id == "practice-1"
    assert context.accounting_entity_id == "client-b"


def test_http_ca_client_roster_does_not_require_primary_for_staff(monkeypatch) -> None:
    async def fake_get_tenant(tenant_id: str):
        return {
            "tenant_id": tenant_id,
            "status": "active",
            "organization_type": "BUSINESS",
            "enabled_modules": ["business", "audit"],
        }

    store = FakeCollection()

    monkeypatch.setattr(module_deps, "get_tenant", fake_get_tenant)
    monkeypatch.setattr(business_service, "get_collection", lambda _name: store)

    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "staff-1",
        "tenant_id": "practice-1",
        "app_key": "mitrabooks",
        "role": "accountant",
        "accounting_entity_ids": ["client-a"],
    }
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/business/ca-clients?active_only=true&limit=10",
                headers={"X-App-Key": "mitrabooks"},
            )
        assert response.status_code == 200
        assert response.json()["total"] == 0
    finally:
        app.dependency_overrides.pop(get_current_user, None)
