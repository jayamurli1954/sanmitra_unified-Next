"""HTTP integration tests for LegalMitra Stage 6 practice billing routes."""
from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.auth.security import create_access_token
from app.core.modules import dependencies as module_deps
from app.main import app
from app.modules.legal import billing_service, practice_service


class _Cursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, *_a, **_k):
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    async def to_list(self, length=None):
        if length is None:
            return list(self._docs)
        return list(self._docs[:length])


class FakeCollection:
    def __init__(self):
        self.docs: list[dict] = []
        self.seq = 0

    async def create_index(self, *_a, **_k):
        return None

    @staticmethod
    def _match(doc, flt):
        return all(doc.get(k) == v for k, v in flt.items())

    async def find_one(self, flt):
        for d in self.docs:
            if self._match(d, flt):
                return dict(d)
        return None

    async def insert_one(self, doc):
        if "idempotency_key" in doc:
            for d in self.docs:
                if (
                    d.get("tenant_id") == doc.get("tenant_id")
                    and d.get("app_key") == doc.get("app_key")
                    and d.get("idempotency_key") == doc.get("idempotency_key")
                ):
                    raise RuntimeError("duplicate key")
        self.docs.append(dict(doc))

    def find(self, flt):
        return _Cursor([dict(d) for d in self.docs if self._match(d, flt)])

    async def count_documents(self, flt):
        return sum(1 for d in self.docs if self._match(d, flt))

    async def update_one(self, flt, update, upsert=False):
        matched = False
        for d in self.docs:
            if self._match(d, flt):
                d.update(update.get("$set", {}))
                for key, amount in (update.get("$inc") or {}).items():
                    d[key] = int(d.get(key) or 0) + int(amount)
                matched = True
                break
        if not matched and upsert:
            new_doc = dict(flt)
            new_doc.update(update.get("$set", {}))
            new_doc.update(update.get("$setOnInsert", {}))
            for key, amount in (update.get("$inc") or {}).items():
                new_doc[key] = int(amount)
            self.docs.append(new_doc)

    async def find_one_and_update(self, filters, update, **_kwargs):
        for d in self.docs:
            if self._match(d, filters):
                for key, amount in (update.get("$inc") or {}).items():
                    d[key] = int(d.get(key) or 0) + int(amount)
                d.update(update.get("$set", {}))
                return dict(d)
        new_doc = dict(filters)
        new_doc.update(update.get("$setOnInsert", {}))
        for key, amount in (update.get("$inc") or {}).items():
            new_doc[key] = int(amount)
        self.docs.append(new_doc)
        return dict(new_doc)


def _auth_headers(tenant_id: str = "tenant-a") -> dict[str, str]:
    token = create_access_token(
        {
            "sub": "legal-user-stage6",
            "email": "legal.stage6@example.com",
            "role": "tenant_admin",
            "tenant_id": tenant_id,
            "app_key": "legalmitra",
        }
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-App-Key": "legalmitra",
    }


@pytest.fixture
def billing_http(monkeypatch):
    cols: dict[str, FakeCollection] = {}

    def _get(name: str):
        return cols.setdefault(name, FakeCollection())

    async def fake_get_tenant(tenant_id: str):
        return {
            "tenant_id": tenant_id,
            "organization_type": "LEGAL",
            "enabled_modules": ["legal", "rag", "compliance", "audit"],
            "app_keys": ["legalmitra"],
        }

    async def fake_audit(**_kwargs):
        return "evt"

    monkeypatch.setattr(module_deps, "get_tenant", fake_get_tenant)
    for mod in (practice_service, billing_service):
        monkeypatch.setattr(mod, "get_collection", _get)
        if hasattr(mod, "log_audit_event"):
            monkeypatch.setattr(mod, "log_audit_event", fake_audit)

    class _Settings:
        LEGALMITRA_BILLING_ENABLED = True
        LEGALMITRA_MITRABOOKS_POSTING_ENABLED = False

    monkeypatch.setattr(billing_service, "get_settings", lambda: _Settings())
    return cols


def _seed_matter(client: TestClient, headers: dict) -> str:
    created = client.post(
        "/api/v1/legal/clients",
        headers=headers,
        json={"display_name": "Stage6 Client", "client_type": "organization"},
    )
    assert created.status_code == 200, created.text
    matter = client.post(
        "/api/v1/legal/matters",
        headers=headers,
        json={
            "client_id": created.json()["client_id"],
            "title": "Retainer advisory",
            "practice_area": "advisory",
            "status": "active",
            "jurisdiction": "India",
            "next_deadline_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    assert matter.status_code == 200, matter.text
    return matter.json()["matter_id"]


def test_stage6_http_issue_collect_void_and_flag(billing_http, monkeypatch) -> None:
    client = TestClient(app)
    headers = _auth_headers()
    matter_id = _seed_matter(client, headers)

    draft = client.post(
        "/api/v1/legal/practice/fees/invoices",
        headers=headers,
        json={
            "matter_id": matter_id,
            "lines": [
                {
                    "description": "Retainer",
                    "quantity": "1",
                    "unit_rate": "1000.00",
                    "tax_rate_percent": "0",
                }
            ],
        },
    )
    assert draft.status_code == 200, draft.text
    invoice_id = draft.json()["invoice_id"]
    assert draft.json()["status"] == "draft"

    issued = client.post(
        f"/api/v1/legal/practice/fees/invoices/{invoice_id}/issue",
        headers=headers,
    )
    assert issued.status_code == 200, issued.text
    assert issued.json()["status"] == "issued"

    collected = client.post(
        f"/api/v1/legal/practice/fees/invoices/{invoice_id}/collections",
        headers=headers,
        json={
            "amount": "400.00",
            "mode": "bank",
            "idempotency_key": f"http-collect-{uuid4()}",
            "post_to_mitrabooks": False,
            "confirm_post_to_mitrabooks": False,
        },
    )
    assert collected.status_code == 200, collected.text
    assert collected.json()["accounting_status"] == "not_posted"

    summary = client.get("/api/v1/legal/practice/fees/summary", headers=headers)
    assert summary.status_code == 200, summary.text
    assert float(summary.json()["fees_outstanding"]) == 600.0

    # Separate draft for void path
    void_draft = client.post(
        "/api/v1/legal/practice/fees/invoices",
        headers=headers,
        json={
            "matter_id": matter_id,
            "lines": [{"description": "Mistake", "unit_rate": "50.00"}],
        },
    )
    assert void_draft.status_code == 200
    voided = client.post(
        f"/api/v1/legal/practice/fees/invoices/{void_draft.json()['invoice_id']}/void",
        headers=headers,
        json={"reason": "Created in error", "confirm": True},
    )
    assert voided.status_code == 200, voided.text
    assert voided.json()["status"] == "void"

    class _Off:
        LEGALMITRA_BILLING_ENABLED = False
        LEGALMITRA_MITRABOOKS_POSTING_ENABLED = False

    monkeypatch.setattr(billing_service, "get_settings", lambda: _Off())
    disabled = client.get("/api/v1/legal/practice/fees/summary", headers=headers)
    assert disabled.status_code == 503


def test_stage6_http_tenant_isolation(billing_http) -> None:
    client = TestClient(app)
    headers_a = _auth_headers("tenant-a")
    headers_b = _auth_headers("tenant-b")
    matter_id = _seed_matter(client, headers_a)

    draft = client.post(
        "/api/v1/legal/practice/fees/invoices",
        headers=headers_a,
        json={
            "matter_id": matter_id,
            "lines": [{"description": "Fee", "unit_rate": "100.00"}],
        },
    )
    assert draft.status_code == 200
    invoice_id = draft.json()["invoice_id"]

    other = client.get(
        f"/api/v1/legal/practice/fees/invoices/{invoice_id}",
        headers=headers_b,
    )
    assert other.status_code == 404
