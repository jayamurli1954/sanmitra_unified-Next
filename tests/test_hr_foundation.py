"""HR add-on v1 foundation — schema validation, Employee CRUD service, audit
redaction, and the two-level access gate. Uses an in-memory fake collection so
no real Mongo is needed."""
from __future__ import annotations

from datetime import date

import pytest

from app.modules.hr import service as hr_service
from app.modules.hr.schemas import EmployeeCreateRequest, EmployeeUpdateRequest


# ── in-memory fake Mongo collection ──────────────────────────────────────────

class _Cursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, *_args, **_kwargs):
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    async def to_list(self, length=None):
        return list(self._docs)


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

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    def find(self, flt):
        return _Cursor([dict(d) for d in self.docs if self._match(d, flt)])

    async def count_documents(self, flt):
        return sum(1 for d in self.docs if self._match(d, flt))

    async def update_one(self, flt, update):
        for d in self.docs:
            if self._match(d, flt):
                d.update(update.get("$set", {}))
                return
        raise AssertionError("no doc matched update")


@pytest.fixture
def fake_employees(monkeypatch):
    col = FakeCollection()
    monkeypatch.setattr(hr_service, "get_collection", lambda _name: col)
    return col


@pytest.fixture
def captured_audit(monkeypatch):
    events: list[dict] = []

    async def _fake_log(**kwargs):
        events.append(kwargs)
        return "evt"

    monkeypatch.setattr(hr_service, "log_audit_event", _fake_log)
    return events


def _payload(**over):
    base = dict(
        user_id="user-1",
        full_name="Asha Rao",
        date_of_joining=date(2024, 4, 1),
        pan_number="abcde1234f",
        ifsc_code="hdfc0001234",
        account_number="123456789012",
    )
    base.update(over)
    return EmployeeCreateRequest(**base)


# ── schema validation ────────────────────────────────────────────────────────

def test_statutory_validators_normalize_and_reject():
    e = _payload(uan_number="100000000001")
    assert e.pan_number == "ABCDE1234F"
    assert e.ifsc_code == "HDFC0001234"
    assert e.uan_number == "100000000001"

    for bad in (dict(pan_number="WRONG"), dict(ifsc_code="ZZ"), dict(uan_number="9")):
        with pytest.raises(ValueError):
            _payload(**bad)


def test_blank_statutory_fields_become_none():
    e = _payload(pan_number="", uan_number=None, ifsc_code="")
    assert e.pan_number is None and e.uan_number is None and e.ifsc_code is None


# ── service CRUD ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_list_get_update_roundtrip(fake_employees, captured_audit):
    created = await hr_service.create_employee(
        tenant_id="t1", app_key="mitrabooks", created_by="admin", payload=_payload()
    )
    assert created["employee_id"]
    assert created["tenant_id"] == "t1"
    # date stored BSON-safe as ISO string
    assert created["date_of_joining"] == "2024-04-01"

    listing = await hr_service.list_employees(tenant_id="t1", app_key="mitrabooks")
    assert listing["total"] == 1
    assert listing["employees"][0]["full_name"] == "Asha Rao"

    fetched = await hr_service.get_employee(
        tenant_id="t1", app_key="mitrabooks", employee_id=created["employee_id"]
    )
    assert fetched["pan_number"] == "ABCDE1234F"

    updated = await hr_service.update_employee(
        tenant_id="t1", app_key="mitrabooks", updated_by="admin",
        employee_id=created["employee_id"],
        payload=EmployeeUpdateRequest(status="active", designation="Analyst"),
    )
    assert updated["status"] == "active"
    assert updated["designation"] == "Analyst"


@pytest.mark.asyncio
async def test_duplicate_user_rejected(fake_employees, captured_audit):
    await hr_service.create_employee(
        tenant_id="t1", app_key="mitrabooks", created_by="admin", payload=_payload()
    )
    with pytest.raises(hr_service.HrConflictError):
        await hr_service.create_employee(
            tenant_id="t1", app_key="mitrabooks", created_by="admin", payload=_payload()
        )


@pytest.mark.asyncio
async def test_tenant_isolation_on_read(fake_employees, captured_audit):
    await hr_service.create_employee(
        tenant_id="t1", app_key="mitrabooks", created_by="admin", payload=_payload()
    )
    # Same user_id, different tenant must not collide and must not be visible.
    other = await hr_service.list_employees(tenant_id="t2", app_key="mitrabooks")
    assert other["total"] == 0


@pytest.mark.asyncio
async def test_missing_employee_raises(fake_employees, captured_audit):
    with pytest.raises(hr_service.HrNotFoundError):
        await hr_service.get_employee(tenant_id="t1", app_key="mitrabooks", employee_id="nope")


@pytest.mark.asyncio
async def test_audit_redacts_sensitive_fields(fake_employees, captured_audit):
    await hr_service.create_employee(
        tenant_id="t1", app_key="mitrabooks", created_by="admin", payload=_payload()
    )
    create_event = next(e for e in captured_audit if e["action"] == "hr_employee_created")
    new_value = create_event["new_value"]
    assert new_value["account_number"] == "******"
    assert new_value["pan_number"] == "******"
    # Non-sensitive fields stay readable.
    assert new_value["full_name"] == "Asha Rao"


# ── two-level gate ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gate_blocks_when_not_provisioned(monkeypatch):
    from fastapi import HTTPException

    from app.modules.hr import gating

    async def _tenant(_tid):
        return {"tenant_id": "t1", "hr_addon_available": False}

    monkeypatch.setattr(gating, "get_tenant", _tenant)
    dep = gating.require_hr_context("test")
    user = {"tenant_id": "t1", "app_key": "mitrabooks", "sub": "u1"}
    with pytest.raises(HTTPException) as exc:
        await dep(current_user=user, x_tenant_id="t1", x_app_key="mitrabooks", x_accounting_entity_id=None)
    assert exc.value.status_code == 403
    assert "not provisioned" in exc.value.detail


@pytest.mark.asyncio
async def test_gate_blocks_when_tenant_disabled(monkeypatch):
    from fastapi import HTTPException

    from app.modules.hr import gating
    import app.modules.business.service as business_service

    async def _tenant(_tid):
        return {"tenant_id": "t1", "hr_addon_available": True}

    async def _settings(**_kwargs):
        return {"hr_enabled": False}

    monkeypatch.setattr(gating, "get_tenant", _tenant)
    monkeypatch.setattr(business_service, "get_invoice_settings", _settings)
    dep = gating.require_hr_context("test")
    user = {"tenant_id": "t1", "app_key": "mitrabooks", "sub": "u1"}
    with pytest.raises(HTTPException) as exc:
        await dep(current_user=user, x_tenant_id="t1", x_app_key="mitrabooks", x_accounting_entity_id=None)
    assert exc.value.status_code == 403
    assert "disabled" in exc.value.detail


@pytest.mark.asyncio
async def test_gate_passes_when_both_flags_on(monkeypatch):
    from app.modules.hr import gating
    import app.modules.business.service as business_service

    async def _tenant(_tid):
        return {"tenant_id": "t1", "hr_addon_available": True}

    async def _settings(**_kwargs):
        return {"hr_enabled": True}

    monkeypatch.setattr(gating, "get_tenant", _tenant)
    monkeypatch.setattr(business_service, "get_invoice_settings", _settings)
    dep = gating.require_hr_context("test")
    user = {"tenant_id": "t1", "app_key": "mitrabooks", "sub": "u1"}
    context = await dep(current_user=user, x_tenant_id="t1", x_app_key="mitrabooks", x_accounting_entity_id=None)
    assert context.tenant_id == "t1"
    assert context.app_key == "mitrabooks"
