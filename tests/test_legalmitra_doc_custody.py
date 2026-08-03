"""LegalMitra P0 — document custody settings (Personal Practice vs Chamber LAN)."""
from __future__ import annotations

import pytest

from app.modules.legal import custody_service as svc
from app.modules.legal.practice_schemas import DocCustodySettingsUpdateRequest


class FakeCollection:
    def __init__(self):
        self.docs: list[dict] = []

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

    async def update_one(self, flt, update, upsert=False):
        matched = False
        for d in self.docs:
            if self._match(d, flt):
                d.update(update.get("$set", {}))
                matched = True
                break
        if not matched and upsert:
            new_doc = dict(flt)
            new_doc.update(update.get("$setOnInsert", {}))
            new_doc.update(update.get("$set", {}))
            self.docs.append(new_doc)
        return type("R", (), {"matched_count": 1 if matched or upsert else 0})()


@pytest.fixture
def fake_db(monkeypatch):
    cols: dict[str, FakeCollection] = {}

    def _get(name: str):
        return cols.setdefault(name, FakeCollection())

    monkeypatch.setattr(svc, "get_collection", _get)
    return cols


@pytest.fixture
def captured_audit(monkeypatch):
    events: list[dict] = []

    async def _fake_log(**kwargs):
        events.append(kwargs)
        return "evt"

    monkeypatch.setattr(svc, "log_audit_event", _fake_log)
    return events


@pytest.mark.asyncio
async def test_custody_defaults_to_personal_practice(fake_db):
    settings = await svc.get_custody_settings(tenant_id="tenant-a", app_key="legalmitra")
    assert settings["doc_custody_mode"] == "cloud_minimized"
    assert settings["display_name"] == "Personal Practice"
    assert settings["doc_cloud_originals_opt_in"] is False
    assert settings["chamber_connector_enabled"] is False
    assert settings["onboarding_answered"] is False


@pytest.mark.asyncio
async def test_switch_to_chamber_lan_and_audit(fake_db, captured_audit):
    updated = await svc.update_custody_settings(
        tenant_id="tenant-a",
        app_key="legalmitra",
        payload=DocCustodySettingsUpdateRequest(
            doc_custody_mode="chamber_lan",
            onboarding_answered=True,
            chamber_connector_enabled=True,
        ),
        actor_user_id="admin-1",
    )
    assert updated["doc_custody_mode"] == "chamber_lan"
    assert updated["display_name"] == "Chamber LAN"
    assert updated["chamber_connector_enabled"] is True
    assert updated["onboarding_answered"] is True
    assert captured_audit
    assert captured_audit[-1]["action"] == "legal_doc_custody_settings_updated"
    assert captured_audit[-1]["tenant_id"] == "tenant-a"


@pytest.mark.asyncio
async def test_chamber_lan_rejects_cloud_originals_opt_in(fake_db):
    with pytest.raises(svc.CustodyValidationError, match="Chamber LAN"):
        await svc.update_custody_settings(
            tenant_id="tenant-a",
            app_key="legalmitra",
            payload=DocCustodySettingsUpdateRequest(
                doc_custody_mode="chamber_lan",
                doc_cloud_originals_opt_in=True,
            ),
            actor_user_id="admin-1",
        )


@pytest.mark.asyncio
async def test_personal_practice_rejects_connector(fake_db):
    with pytest.raises(svc.CustodyValidationError, match="Chamber Connector"):
        await svc.update_custody_settings(
            tenant_id="tenant-a",
            app_key="legalmitra",
            payload=DocCustodySettingsUpdateRequest(
                doc_custody_mode="cloud_minimized",
                chamber_connector_enabled=True,
            ),
            actor_user_id="admin-1",
        )


@pytest.mark.asyncio
async def test_enterprise_vault_not_available_yet(fake_db):
    current = await svc.get_custody_settings(tenant_id="t", app_key="legalmitra")

    class _FuturePayload:
        doc_custody_mode = type("M", (), {"value": "enterprise_vault"})()
        doc_cloud_originals_opt_in = None
        chamber_connector_enabled = None
        extract_retention_days = None
        onboarding_answered = True

    with pytest.raises(svc.CustodyValidationError, match="Enterprise Vault"):
        svc._validate_update(_FuturePayload(), current)


@pytest.mark.asyncio
async def test_tenant_isolation_of_custody_settings(fake_db, captured_audit):
    await svc.update_custody_settings(
        tenant_id="tenant-a",
        app_key="legalmitra",
        payload=DocCustodySettingsUpdateRequest(doc_custody_mode="chamber_lan"),
        actor_user_id="a1",
    )
    other = await svc.get_custody_settings(tenant_id="tenant-b", app_key="legalmitra")
    assert other["doc_custody_mode"] == "cloud_minimized"
    assert other["display_name"] == "Personal Practice"


@pytest.mark.asyncio
async def test_empty_patch_rejected(fake_db):
    with pytest.raises(svc.CustodyValidationError, match="No custody"):
        await svc.update_custody_settings(
            tenant_id="tenant-a",
            app_key="legalmitra",
            payload=DocCustodySettingsUpdateRequest(),
            actor_user_id="admin-1",
        )
