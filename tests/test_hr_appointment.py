"""Auto employee-code generation, appointment config, and letter PDF."""
from __future__ import annotations

import pytest

import app.modules.hr.service as hr_service
from app.modules.hr.schemas import AppointmentConfig, EmployeeCreateRequest


class _Cursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, *_a, **_k):
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    async def to_list(self, length=None):
        return list(self._docs)


class FakeCollection:
    def __init__(self):
        self.docs: list[dict] = []

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

    def find(self, flt):
        return _Cursor([dict(d) for d in self.docs if self._match(d, flt)])

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def count_documents(self, flt):
        return sum(1 for d in self.docs if self._match(d, flt))

    async def update_one(self, flt, update, upsert=False):
        for d in self.docs:
            if self._match(d, flt):
                d.update(update.get("$set", {}))
                return
        if upsert:
            new = dict(flt)
            new.update(update.get("$set", {}))
            new.update(update.get("$setOnInsert", {}))
            self.docs.append(new)

    async def find_one_and_update(self, flt, update, upsert=False, return_document=None):
        for d in self.docs:
            if self._match(d, flt):
                d["seq"] = d.get("seq", 0) + update.get("$inc", {}).get("seq", 0)
                return dict(d)
        if upsert:
            new = dict(flt)
            new["seq"] = update.get("$inc", {}).get("seq", 0)
            self.docs.append(new)
            return dict(new)
        return None


SCOPE = {"tenant_id": "t1", "app_key": "mitrabooks"}


@pytest.fixture
def db(monkeypatch):
    cols: dict[str, FakeCollection] = {}
    monkeypatch.setattr(hr_service, "get_collection", lambda name: cols.setdefault(name, FakeCollection()))
    return cols


def _payload(**over):
    base = dict(full_name="Narayan", date_of_joining="2024-04-01")
    base.update(over)
    return EmployeeCreateRequest(**base)


@pytest.mark.asyncio
async def test_offer_has_no_code_then_minted_on_join(db):
    a = await hr_service.create_employee(**SCOPE, created_by="hr", payload=_payload())
    assert a["status"] == "offered"
    assert a["employee_code"] is None      # no code at the offer stage

    joined = await hr_service.mark_employee_joined(
        **SCOPE, actor="hr", employee_id=a["employee_id"], joining_date="2024-04-15"
    )
    assert joined["status"] == "active"
    assert joined["employee_code"] == "EMP-0001"   # minted on join
    assert joined["joining_date"] == "2024-04-15"

    # second hire joins -> next sequential code
    b = await hr_service.create_employee(**SCOPE, created_by="hr", payload=_payload(full_name="Asha"))
    jb = await hr_service.mark_employee_joined(**SCOPE, actor="hr", employee_id=b["employee_id"], joining_date="2024-05-01")
    assert jb["employee_code"] == "EMP-0002"


@pytest.mark.asyncio
async def test_declined_offer_never_gets_a_code(db):
    a = await hr_service.create_employee(**SCOPE, created_by="hr", payload=_payload())
    d = await hr_service.mark_employee_declined(**SCOPE, actor="hr", employee_id=a["employee_id"])
    assert d["status"] == "declined" and d["employee_code"] is None
    # a declined candidate cannot then be joined
    with pytest.raises(hr_service.HrValidationError):
        await hr_service.mark_employee_joined(**SCOPE, actor="hr", employee_id=a["employee_id"], joining_date="2024-04-15")


@pytest.mark.asyncio
async def test_explicit_user_id_respected(db):
    a = await hr_service.create_employee(**SCOPE, created_by="hr", payload=_payload(user_id="login-42"))
    assert a["user_id"] == "login-42"
    assert a["status"] == "offered" and a["employee_code"] is None


@pytest.mark.asyncio
async def test_appointment_config_defaults_and_save(db):
    cfg = await hr_service.get_appointment_config(**SCOPE)
    assert cfg["probation_months"] == 6 and cfg["notice_days"] == 30
    assert cfg["clauses"]["ip_assignment"] is True and cfg["clauses"]["cash_handling"] is False

    saved = await hr_service.save_appointment_config(
        **SCOPE, updated_by="hr",
        payload=AppointmentConfig(probation_months=3, notice_days=60, clauses={"cash_handling": True}),
    )
    assert saved["probation_months"] == 3 and saved["notice_days"] == 60
    assert saved["clauses"]["cash_handling"] is True
    # round-trips from storage
    again = await hr_service.get_appointment_config(**SCOPE)
    assert again["probation_months"] == 3 and again["clauses"]["cash_handling"] is True
