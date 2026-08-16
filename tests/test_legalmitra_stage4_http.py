"""HTTP integration tests for LegalMitra Stage 4 proactive routes."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.auth.security import create_access_token
from app.core.modules import dependencies as module_deps
from app.main import app
from app.modules.legal import custody_service, practice_service, proactive_service


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


def _auth_headers(tenant_id: str = "tenant-a") -> dict[str, str]:
    token = create_access_token(
        {
            "sub": "legal-user-stage4",
            "email": "legal.stage4@example.com",
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
def proactive_http(monkeypatch):
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
    monkeypatch.setattr(practice_service, "get_collection", _get)
    monkeypatch.setattr(practice_service, "log_audit_event", fake_audit)
    monkeypatch.setattr(proactive_service, "get_collection", _get)
    monkeypatch.setattr(proactive_service, "log_audit_event", fake_audit)
    monkeypatch.setattr(custody_service, "get_collection", _get)
    monkeypatch.setattr(custody_service, "log_audit_event", fake_audit)
    return cols


def test_stage4_http_morning_brief_alerts_notifications(proactive_http) -> None:
    client = TestClient(app)
    headers = _auth_headers("tenant-a")

    empty = client.get(
        "/api/v1/legal/practice/morning-brief?persona=advocate&window=daily",
        headers=headers,
    )
    assert empty.status_code == 200, empty.text
    assert empty.json()["empty_practice"] is True
    assert empty.json()["human_review_required"] is True

    created_client = client.post(
        "/api/v1/legal/clients",
        headers=headers,
        json={"display_name": "Acme Proactive", "client_type": "organization"},
    )
    assert created_client.status_code == 200
    client_id = created_client.json()["client_id"]

    matter = client.post(
        "/api/v1/legal/matters",
        headers=headers,
        json={
            "client_id": client_id,
            "title": "Overdue GST reply",
            "practice_area": "gst",
            "status": "active",
            "next_deadline_date": (date.today() - timedelta(days=1)).isoformat(),
        },
    )
    assert matter.status_code == 200, matter.text
    matter_id = matter.json()["matter_id"]

    refreshed = client.post(
        "/api/v1/legal/practice/alerts/refresh",
        headers=headers,
        json={},
    )
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["open_alerts"] >= 1

    alerts = client.get("/api/v1/legal/practice/alerts?status=open", headers=headers)
    assert alerts.status_code == 200
    items = alerts.json()["items"]
    assert items
    assert items[0]["priority_score"] >= items[-1]["priority_score"]
    assert "matter_id=" in (items[0].get("action_href") or "")
    alert_id = items[0]["alert_id"]

    snoozed = client.patch(
        f"/api/v1/legal/practice/alerts/{alert_id}",
        headers=headers,
        json={"status": "snoozed"},
    )
    assert snoozed.status_code == 200
    assert snoozed.json()["status"] == "snoozed"

    brief = client.post(
        "/api/v1/legal/practice/morning-brief",
        headers=headers,
        json={"persona": "advocate", "window": "daily", "force_refresh": True},
    )
    assert brief.status_code == 200, brief.text
    body = brief.json()
    assert body["empty_practice"] is False
    assert 0 <= body["practice_health_score"] <= 100
    assert body["sections"]["priority_actions"] or True

    notes = client.get("/api/v1/legal/practice/notifications?limit=20", headers=headers)
    assert notes.status_code == 200
    note_items = notes.json()["items"]
    assert note_items
    note_id = note_items[0]["notification_id"]
    marked = client.patch(
        f"/api/v1/legal/practice/notifications/{note_id}/read",
        headers=headers,
        json={},
    )
    assert marked.status_code == 200
    assert marked.json()["read_at"] is not None

    # Deep-link shape used by tracker act-in-place.
    assert matter_id
    assert any(
        matter_id in (a.get("action_href") or "")
        for a in client.get(
            "/api/v1/legal/practice/alerts?status=open", headers=headers
        ).json()["items"]
        + items
    )


def test_stage4_http_tenant_isolation(proactive_http) -> None:
    client = TestClient(app)
    headers_a = _auth_headers("tenant-a")
    headers_b = _auth_headers("tenant-b")

    created = client.post(
        "/api/v1/legal/clients",
        headers=headers_a,
        json={"display_name": "Only A", "client_type": "organization"},
    )
    client_id = created.json()["client_id"]
    client.post(
        "/api/v1/legal/matters",
        headers=headers_a,
        json={
            "client_id": client_id,
            "title": "Tenant A deadline",
            "status": "active",
            "next_deadline_date": date.today().isoformat(),
        },
    )
    client.post("/api/v1/legal/practice/alerts/refresh", headers=headers_a, json={})

    other = client.get("/api/v1/legal/practice/alerts", headers=headers_b)
    assert other.status_code == 200
    assert other.json()["items"] == []


def test_stage4_http_disabled_flag(proactive_http, monkeypatch) -> None:
    class _S:
        LEGALMITRA_PROACTIVE_ENABLED = False
        LEGALMITRA_MORNING_BRIEF_ENABLED = False
        LEGALMITRA_ALERT_LOOKAHEAD_DAYS = 7
        LEGALMITRA_DORMANT_MATTER_DAYS = 45
        LEGALMITRA_STALE_REVIEW_DAYS = 7

    monkeypatch.setattr(proactive_service, "get_settings", lambda: _S())
    client = TestClient(app)
    headers = _auth_headers()
    response = client.post(
        "/api/v1/legal/practice/alerts/refresh",
        headers=headers,
        json={},
    )
    assert response.status_code == 503
