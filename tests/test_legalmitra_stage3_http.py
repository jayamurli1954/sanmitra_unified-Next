"""HTTP integration tests for LegalMitra Stage 3 practice routes.

Patches Mongo collections + tenant lookup so no live database is required.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.auth.security import create_access_token
from app.core.modules import dependencies as module_deps
from app.main import app
from app.modules.legal import custody_service, practice_service
from app.modules.legal import proactive_service


class _Cursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, field, direction=1):
        reverse = direction < 0
        self._docs.sort(key=lambda row: row.get(field) or "", reverse=reverse)
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

    async def create_index(self, *_args, **_kwargs):
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
                matched = True
                break
        if not matched and upsert:
            new_doc = dict(flt)
            new_doc.update(update.get("$set", {}))
            new_doc.update(update.get("$setOnInsert", {}))
            self.docs.append(new_doc)

    async def find_one_and_update(self, filters, update, **_kwargs):
        self.seq += int(update.get("$inc", {}).get("seq", 1))
        return {**filters, "seq": self.seq}


def _auth_headers(tenant_id: str = "tenant-a", *, app_key: str = "legalmitra") -> dict[str, str]:
    token = create_access_token(
        {
            "sub": "legal-user-stage3",
            "email": "legal.stage3@example.com",
            "role": "tenant_admin",
            "tenant_id": tenant_id,
            "app_key": app_key,
        }
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-App-Key": app_key,
    }


@pytest.fixture
def practice_http(monkeypatch):
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

    async def fake_extend(*, tenant_id, app_key, base_dashboard):
        return {
            **base_dashboard,
            "open_alerts": 0,
            "practice_health_score": 80,
            "practice_health_label": "stable",
            "priority_alerts": [],
        }

    monkeypatch.setattr(module_deps, "get_tenant", fake_get_tenant)
    monkeypatch.setattr(practice_service, "get_collection", _get)
    monkeypatch.setattr(practice_service, "log_audit_event", fake_audit)
    monkeypatch.setattr(custody_service, "get_collection", _get)
    monkeypatch.setattr(custody_service, "log_audit_event", fake_audit)
    monkeypatch.setattr(proactive_service, "extend_dashboard_proactive", fake_extend)
    return cols


def test_stage3_http_client_matter_brief_dashboard_roundtrip(practice_http) -> None:
    client = TestClient(app)
    headers = _auth_headers("tenant-a")

    created_client = client.post(
        "/api/v1/legal/clients",
        headers=headers,
        json={
            "display_name": "Acme Traders Pvt Ltd",
            "client_type": "organization",
            "pan": "ABCDE1234F",
        },
    )
    assert created_client.status_code == 200, created_client.text
    client_id = created_client.json()["client_id"]

    created_matter = client.post(
        "/api/v1/legal/matters",
        headers=headers,
        json={
            "client_id": client_id,
            "title": "GST SCN reply — FY 2024-25",
            "practice_area": "gst",
            "status": "pending",
            "next_deadline_date": "2026-08-20",
        },
    )
    assert created_matter.status_code == 200, created_matter.text
    matter = created_matter.json()
    assert matter["matter_number"].startswith("GST-")
    matter_id = matter["matter_id"]

    brief = client.post(
        f"/api/v1/legal/matters/{matter_id}/brief",
        headers=headers,
        json={},
    )
    assert brief.status_code == 200, brief.text
    body = brief.json()
    assert body["sections"]["human_review_required"] is True
    assert "matter_overview" in body["sections"]

    latest = client.get(
        f"/api/v1/legal/matters/{matter_id}/brief",
        headers=headers,
    )
    assert latest.status_code == 200
    assert latest.json()["brief_id"] == body["brief_id"]

    dash = client.get("/api/v1/legal/practice/dashboard?limit=5", headers=headers)
    assert dash.status_code == 200, dash.text
    payload = dash.json()
    assert payload["data_source"] == "live"
    assert payload["pending_matters"] >= 1
    assert payload["recent_clients"]
    assert any(item.get("matter_id") == matter_id for item in payload["upcoming_deadlines"])


def test_stage3_http_tenant_isolation(practice_http) -> None:
    client = TestClient(app)
    headers_a = _auth_headers("tenant-a")
    headers_b = _auth_headers("tenant-b")

    created = client.post(
        "/api/v1/legal/clients",
        headers=headers_a,
        json={"display_name": "Only Tenant A", "client_type": "organization"},
    )
    assert created.status_code == 200
    client_id = created.json()["client_id"]

    listed_b = client.get("/api/v1/legal/clients", headers=headers_b)
    assert listed_b.status_code == 200
    assert listed_b.json()["items"] == []

    missing = client.get(f"/api/v1/legal/clients/{client_id}", headers=headers_b)
    assert missing.status_code == 404
