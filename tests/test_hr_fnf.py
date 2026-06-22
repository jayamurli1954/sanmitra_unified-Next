"""Full & Final settlement (Step 6) — F&F math + tenure-driven gratuity +
draft->approved->paid lifecycle."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

import app.modules.hr.fnf as fnf
import app.modules.hr.service as hr_service
from app.modules.hr.payroll_engine import compute_fnf, compute_leave_encashment, compute_notice_recovery

D = Decimal


# ── pure math ─────────────────────────────────────────────────────────────────

def test_leave_encashment_and_notice_recovery():
    assert compute_leave_encashment(D("30000"), D("10")) == D("10000.00")   # 30000/30*10
    assert compute_notice_recovery(D("30000"), D("15")) == D("15000.00")    # 30000/30*15


def test_compute_fnf_nets_payouts_and_recoveries():
    out = compute_fnf(
        last_drawn_basic=D("50000"), years_of_service=6,
        unutilized_leaves=D("12"), unpaid_notice_days=D("10"), other_recoveries=D("5000"),
    )
    assert out["gratuity"] == D("173076.92")          # 50000*15*6/26
    assert out["leave_encashment"] == D("20000.00")   # 50000/30*12
    assert out["notice_recovery"] == D("16666.67")    # 50000/30*10
    assert out["total_recovery"] == D("21666.67")     # 16666.67 + 5000
    assert out["net_settlement"] == D("171410.25")    # 193076.92 - 21666.67
    assert out["eligible_for_gratuity"] is True


# ── service: fake mongo ───────────────────────────────────────────────────────

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
        class _C:
            def __init__(s, docs):
                s._docs = docs

            async def to_list(s, length=None):
                return list(s._docs)
        return _C([dict(d) for d in self.docs if self._match(d, flt)])

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def update_one(self, flt, update, upsert=False):
        for d in self.docs:
            if self._match(d, flt):
                d.update(update.get("$set", {}))
                return


SCOPE = {"tenant_id": "t1", "app_key": "mitrabooks"}


@pytest.fixture
def db(monkeypatch):
    cols: dict[str, FakeCollection] = {}

    def _col(name):
        return cols.setdefault(name, FakeCollection())

    monkeypatch.setattr(fnf, "get_collection", _col)
    monkeypatch.setattr(hr_service, "get_collection", _col)
    cols.setdefault("hr_employees", FakeCollection()).docs.append(
        {**SCOPE, "employee_id": "A", "status": "active", "date_of_joining": "2018-01-01"}
    )
    return cols


@pytest.mark.asyncio
async def test_fnf_lifecycle_exits_employee(db):
    settlement = await fnf.create_fnf(
        **SCOPE, created_by="hr", employee_id="A", last_working_day=date(2026, 1, 1),
        last_drawn_basic=D("50000"), unutilized_leaves=D("12"),
    )
    assert settlement["status"] == "draft"
    assert settlement["completed_years"] == 8  # 2018-01 -> 2026-01
    assert settlement["settlement"]["eligible_for_gratuity"] is True

    fnf_id = settlement["fnf_id"]
    approved = await fnf.transition_fnf(**SCOPE, actor="hr", fnf_id=fnf_id, target="approved")
    assert approved["status"] == "approved"
    paid = await fnf.transition_fnf(**SCOPE, actor="hr", fnf_id=fnf_id, target="paid")
    assert paid["status"] == "paid"

    # Employee is now exited.
    emp = await db["hr_employees"].find_one({**SCOPE, "employee_id": "A"})
    assert emp["status"] == "exited"


@pytest.mark.asyncio
async def test_invalid_transition_rejected(db):
    s = await fnf.create_fnf(
        **SCOPE, created_by="hr", employee_id="A", last_working_day=date(2026, 1, 1),
        last_drawn_basic=D("50000"),
    )
    # draft -> paid is not allowed (must approve first).
    with pytest.raises(hr_service.HrValidationError):
        await fnf.transition_fnf(**SCOPE, actor="hr", fnf_id=s["fnf_id"], target="paid")


@pytest.mark.asyncio
async def test_under_five_years_no_gratuity(db):
    db["hr_employees"].docs.append(
        {**SCOPE, "employee_id": "B", "status": "active", "date_of_joining": "2023-06-01"}
    )
    s = await fnf.create_fnf(
        **SCOPE, created_by="hr", employee_id="B", last_working_day=date(2026, 1, 1),
        last_drawn_basic=D("50000"),
    )
    assert s["settlement"]["gratuity"] == "0.00"
    assert s["settlement"]["eligible_for_gratuity"] is False
