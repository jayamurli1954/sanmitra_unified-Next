from datetime import datetime, timezone

import pytest

import app.core.audit.router as audit_router
import app.core.audit.service as audit_service


class FakeAuditCollection:
    def __init__(self, rows):
        self.rows = rows

    def find(self, filters):
        rows = [
            dict(row)
            for row in self.rows
            if all(row.get(key) == value for key, value in filters.items())
        ]
        return FakeCursor(rows)


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    def sort(self, field, direction):
        self.rows.sort(key=lambda row: row.get(field), reverse=direction < 0)
        return self

    def limit(self, value):
        self.rows = self.rows[:value]
        return self

    async def to_list(self, length):
        return self.rows[:length]


@pytest.mark.asyncio
async def test_list_audit_events_filters_by_tenant_product_and_entity(monkeypatch):
    now = datetime.now(timezone.utc)
    collection = FakeAuditCollection(
        [
            {
                "_id": "mongo-id-1",
                "event_id": "event-1",
                "tenant_id": "tenant-a",
                "product": "mitrabooks",
                "action": "business_party_updated",
                "entity_type": "business_party",
                "entity_id": "party-1",
                "timestamp": now,
            },
            {
                "event_id": "event-2",
                "tenant_id": "tenant-a",
                "product": "mandirmitra",
                "action": "public_payment_rejected",
                "entity_type": "public_payment",
                "entity_id": "payment-1",
                "timestamp": now,
            },
            {
                "event_id": "event-3",
                "tenant_id": "tenant-b",
                "product": "mitrabooks",
                "action": "business_party_updated",
                "entity_type": "business_party",
                "entity_id": "party-1",
                "timestamp": now,
            },
        ]
    )
    monkeypatch.setattr(audit_service, "get_collection", lambda _name: collection)

    result = await audit_service.list_audit_events(
        tenant_id="tenant-a",
        product="mitrabooks",
        entity_type="business_party",
        entity_id="party-1",
    )

    assert result["total"] == 1
    assert result["items"][0]["event_id"] == "event-1"
    assert "_id" not in result["items"][0]


@pytest.mark.asyncio
async def test_audit_events_route_defaults_to_active_app_key(monkeypatch):
    captured = {}

    async def fake_list_audit_events(**kwargs):
        captured.update(kwargs)
        return {"items": [], "total": 0}

    monkeypatch.setattr(audit_router, "list_audit_events", fake_list_audit_events)

    result = await audit_router.list_events(
        product=None,
        entity_type=None,
        entity_id=None,
        action=None,
        limit=50,
        _module_context={},
        current_user={"tenant_id": "tenant-a", "role": "tenant_admin", "app_key": "mitrabooks"},
        x_tenant_id=None,
        x_app_key=None,
    )

    assert result == {"items": [], "total": 0}
    assert captured == {
        "tenant_id": "tenant-a",
        "product": "mitrabooks",
        "entity_type": None,
        "entity_id": None,
        "action": None,
        "limit": 50,
    }
