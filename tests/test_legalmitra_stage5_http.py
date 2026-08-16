"""HTTP integration tests for LegalMitra Stage 5 workflow routes."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.auth.security import create_access_token
from app.core.modules import dependencies as module_deps
from app.main import app
from app.modules.legal import (
    custody_service,
    extract_service,
    practice_service,
    proactive_service,
    workflow_service,
)


class _Cursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, field, direction=1):
        reverse = direction < 0

        def _key(row):
            value = row.get(field)
            if value is None:
                return (1, 0, "")
            if isinstance(value, (int, float)):
                return (0, float(value), "")
            return (0, 0, str(value))

        self._docs.sort(key=_key, reverse=reverse)
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
                if "$inc" in update:
                    for k, v in update["$inc"].items():
                        d[k] = int(d.get(k) or 0) + int(v)
                matched = True
                break
        if not matched and upsert:
            new_doc = dict(flt)
            new_doc.update(update.get("$set", {}))
            self.docs.append(new_doc)

    async def find_one_and_update(self, filters, update, **_kwargs):
        self.seq += int(update.get("$inc", {}).get("seq", 1))
        return {**filters, "seq": self.seq}


def _auth_headers(tenant_id: str = "tenant-a") -> dict[str, str]:
    token = create_access_token(
        {
            "sub": "legal-user-stage5",
            "email": "legal.stage5@example.com",
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
def workflow_http(monkeypatch):
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
    for mod in (
        practice_service,
        proactive_service,
        workflow_service,
        extract_service,
        custody_service,
    ):
        monkeypatch.setattr(mod, "get_collection", _get)
        if hasattr(mod, "log_audit_event"):
            monkeypatch.setattr(mod, "log_audit_event", fake_audit)
    return cols


def test_stage5_http_run_approve_cancel_and_flag(workflow_http, monkeypatch) -> None:
    client = TestClient(app)
    headers = _auth_headers()

    created = client.post(
        "/api/v1/legal/clients",
        headers=headers,
        json={"display_name": "Stage5 Client", "client_type": "organization"},
    )
    assert created.status_code == 200
    matter = client.post(
        "/api/v1/legal/matters",
        headers=headers,
        json={
            "client_id": created.json()["client_id"],
            "title": "GST SCN reply",
            "practice_area": "gst",
            "status": "active",
            "jurisdiction": "India — CGST",
            "next_deadline_date": (date.today() + timedelta(days=3)).isoformat(),
        },
    )
    assert matter.status_code == 200, matter.text
    matter_id = matter.json()["matter_id"]

    started = client.post(
        "/api/v1/legal/workflows/runs",
        headers=headers,
        json={
            "workflow_key": "prepare_matter_response",
            "workflow_template": "gst_notice",
            "matter_id": matter_id,
            "recommended_from": "morning_brief",
        },
    )
    assert started.status_code == 200, started.text
    run = started.json()
    assert run["status"] == "awaiting_human"
    research = next(s for s in run["steps"] if s["step_key"] == "RESEARCH")
    assert research["status"] == "awaiting_human"

    approved = client.post(
        f"/api/v1/legal/workflows/runs/{run['run_id']}/steps/{research['step_id']}/approve",
        headers=headers,
        json={},
    )
    assert approved.status_code == 200, approved.text

    cancelled = client.post(
        f"/api/v1/legal/workflows/runs/{run['run_id']}/cancel",
        headers=headers,
        json={},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    class _S:
        LEGALMITRA_AGENTIC_ENABLED = False

    monkeypatch.setattr(workflow_service, "get_settings", lambda: _S())
    blocked = client.post(
        "/api/v1/legal/workflows/runs",
        headers=headers,
        json={"matter_id": matter_id, "workflow_key": "prepare_matter_response"},
    )
    assert blocked.status_code == 503


def test_stage5_http_tenant_isolation(workflow_http) -> None:
    client = TestClient(app)
    headers_a = _auth_headers("tenant-a")
    headers_b = _auth_headers("tenant-b")

    created = client.post(
        "/api/v1/legal/clients",
        headers=headers_a,
        json={"display_name": "Only A", "client_type": "organization"},
    )
    matter = client.post(
        "/api/v1/legal/matters",
        headers=headers_a,
        json={
            "client_id": created.json()["client_id"],
            "title": "Tenant A matter",
            "practice_area": "gst",
            "jurisdiction": "India",
            "status": "active",
        },
    )
    started = client.post(
        "/api/v1/legal/workflows/runs",
        headers=headers_a,
        json={
            "matter_id": matter.json()["matter_id"],
            "workflow_key": "prepare_matter_response",
        },
    )
    assert started.status_code == 200
    run_id = started.json()["run_id"]

    other = client.get(f"/api/v1/legal/workflows/runs/{run_id}", headers=headers_b)
    assert other.status_code in {403, 404}
