"""HR leave (Step 4) — immutable ledger, application lifecycle, derived LOP, and
LOP flowing into the payroll run. Mongo and the journal posting are faked."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

import app.modules.hr.leave as leave
import app.modules.hr.payroll_run as pr
import app.modules.hr.service as hr_service

D = Decimal


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

    async def insert_many(self, docs):
        self.docs.extend(dict(d) for d in docs)

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


SCOPE = {"tenant_id": "t1", "app_key": "mitrabooks"}


@pytest.fixture
def db(monkeypatch):
    cols: dict[str, FakeCollection] = {}

    def _col(name):
        return cols.setdefault(name, FakeCollection())

    monkeypatch.setattr(leave, "get_collection", _col)
    monkeypatch.setattr(hr_service, "get_collection", _col)
    monkeypatch.setattr(pr, "get_collection", _col)
    # An employee to attach leave to.
    cols.setdefault("hr_employees", FakeCollection()).docs.append(
        {**SCOPE, "employee_id": "A", "status": "active", "is_pf_eligible": True,
         "is_esic_eligible": False, "state_for_professional_tax": "Karnataka"}
    )
    return cols


async def _casual_type(is_lwp=False, code="CL"):
    return await leave.create_leave_type(
        **SCOPE, created_by="hr", code=code, name="Casual", is_lwp=is_lwp
    )


# ── ledger + allocation ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_allocation_credits_ledger_balance(db):
    lt = await _casual_type()
    await leave.allocate_leave(**SCOPE, allocated_by="hr", employee_id="A",
                               leave_type_id=lt["leave_type_id"], days=D("10"))
    bal = await leave.get_leave_balance(**SCOPE, employee_id="A", leave_type_id=lt["leave_type_id"])
    assert bal == D("10")


@pytest.mark.asyncio
async def test_cannot_allocate_to_lwp(db):
    lwp = await _casual_type(is_lwp=True, code="LWP")
    with pytest.raises(hr_service.HrValidationError):
        await leave.allocate_leave(**SCOPE, allocated_by="hr", employee_id="A",
                                   leave_type_id=lwp["leave_type_id"], days=D("5"))


# ── application lifecycle + LOP derivation ────────────────────────────────────

@pytest.mark.asyncio
async def test_paid_leave_within_balance_no_lop(db):
    lt = await _casual_type()
    await leave.allocate_leave(**SCOPE, allocated_by="hr", employee_id="A",
                               leave_type_id=lt["leave_type_id"], days=D("10"))
    app_doc = await leave.apply_leave(**SCOPE, applied_by="A", employee_id="A",
                                      leave_type_id=lt["leave_type_id"],
                                      from_date=date(2026, 2, 10), to_date=date(2026, 2, 12))
    approved = await leave.approve_leave(**SCOPE, approved_by="hr", application_id=app_doc["application_id"])
    assert approved["paid_days"] == "3" and approved["lop_days"] == "0"
    bal = await leave.get_leave_balance(**SCOPE, employee_id="A", leave_type_id=lt["leave_type_id"])
    assert bal == D("7")


@pytest.mark.asyncio
async def test_paid_leave_overflow_becomes_lop(db):
    lt = await _casual_type()
    await leave.allocate_leave(**SCOPE, allocated_by="hr", employee_id="A",
                               leave_type_id=lt["leave_type_id"], days=D("2"))
    app_doc = await leave.apply_leave(**SCOPE, applied_by="A", employee_id="A",
                                      leave_type_id=lt["leave_type_id"],
                                      from_date=date(2026, 2, 10), to_date=date(2026, 2, 14))  # 5 days
    approved = await leave.approve_leave(**SCOPE, approved_by="hr", application_id=app_doc["application_id"])
    assert approved["paid_days"] == "2" and approved["lop_days"] == "3"
    # Balance floored at 0, not negative.
    bal = await leave.get_leave_balance(**SCOPE, employee_id="A", leave_type_id=lt["leave_type_id"])
    assert bal == D("0")


@pytest.mark.asyncio
async def test_lwp_application_is_all_lop(db):
    lwp = await _casual_type(is_lwp=True, code="LWP")
    app_doc = await leave.apply_leave(**SCOPE, applied_by="A", employee_id="A",
                                      leave_type_id=lwp["leave_type_id"],
                                      from_date=date(2026, 2, 5), to_date=date(2026, 2, 8))  # 4 days
    approved = await leave.approve_leave(**SCOPE, approved_by="hr", application_id=app_doc["application_id"])
    assert approved["lop_days"] == "4" and approved["paid_days"] == "0"


@pytest.mark.asyncio
async def test_rejected_leave_contributes_no_lop(db):
    lwp = await _casual_type(is_lwp=True, code="LWP")
    app_doc = await leave.apply_leave(**SCOPE, applied_by="A", employee_id="A",
                                      leave_type_id=lwp["leave_type_id"],
                                      from_date=date(2026, 2, 5), to_date=date(2026, 2, 8))
    await leave.reject_leave(**SCOPE, rejected_by="hr", application_id=app_doc["application_id"])
    lop = await leave.resolve_lop_days(**SCOPE, employee_id="A", year=2026, month=2)
    assert lop == D("0")


@pytest.mark.asyncio
async def test_leave_spanning_months_rejected(db):
    lt = await _casual_type()
    with pytest.raises(hr_service.HrValidationError):
        await leave.apply_leave(**SCOPE, applied_by="A", employee_id="A",
                                leave_type_id=lt["leave_type_id"],
                                from_date=date(2026, 2, 26), to_date=date(2026, 3, 2))


@pytest.mark.asyncio
async def test_resolve_lop_sums_period_only(db):
    lwp = await _casual_type(is_lwp=True, code="LWP")
    for frm, to in [(date(2026, 2, 5), date(2026, 2, 6)), (date(2026, 2, 20), date(2026, 2, 20))]:
        a = await leave.apply_leave(**SCOPE, applied_by="A", employee_id="A",
                                    leave_type_id=lwp["leave_type_id"], from_date=frm, to_date=to)
        await leave.approve_leave(**SCOPE, approved_by="hr", application_id=a["application_id"])
    # A March leave that should NOT count toward February.
    a = await leave.apply_leave(**SCOPE, applied_by="A", employee_id="A",
                                leave_type_id=lwp["leave_type_id"],
                                from_date=date(2026, 3, 3), to_date=date(2026, 3, 4))
    await leave.approve_leave(**SCOPE, approved_by="hr", application_id=a["application_id"])
    assert await leave.resolve_lop_days(**SCOPE, employee_id="A", year=2026, month=2) == D("3")


# ── integration: LOP flows into the payroll run ───────────────────────────────

@pytest.mark.asyncio
async def test_lop_reduces_pay_in_payroll_run(db, monkeypatch):
    # Salary structure + assignment for employee A.
    components = [
        {"name": "Basic", "abbr": "BASIC", "formula": "GROSS * 0.5", "statutory_kind": "basic", "depends_on_payment_days": True},
        {"name": "HRA", "abbr": "HRA", "formula": "BASIC * 0.5", "depends_on_payment_days": True},
        {"name": "Special", "abbr": "SPECIAL", "formula": "GROSS - BASIC - HRA", "depends_on_payment_days": True},
    ]
    db.setdefault("hr_salary_structures", FakeCollection()).docs.append({**SCOPE, "structure_id": "s1", "components": components})
    db.setdefault("hr_salary_assignments", FakeCollection()).docs.append(
        {**SCOPE, "employee_id": "A", "structure_id": "s1", "monthly_gross": "125000", "regime": "new", "chapter_via_deductions": "0"}
    )
    # 3 LOP days via an approved LWP application in Feb 2026.
    lwp = await _casual_type(is_lwp=True, code="LWP")
    a = await leave.apply_leave(**SCOPE, applied_by="A", employee_id="A",
                                leave_type_id=lwp["leave_type_id"],
                                from_date=date(2026, 2, 10), to_date=date(2026, 2, 12))
    await leave.approve_leave(**SCOPE, approved_by="hr", application_id=a["application_id"])

    # Fake the GL posting.
    async def _post(session, **kwargs):
        class _J:
            id = 7
        return _J(), True

    monkeypatch.setattr(pr, "post_journal_entry", _post)
    monkeypatch.setattr(pr, "initialize_default_chart_of_accounts", lambda *a, **k: _async_none())
    async def _ids(*a, **k):
        return {c: i for i, c in enumerate(["52001", "52002", "23005", "23006", "23007", "23008", "21003"], 1)}
    monkeypatch.setattr(pr, "_resolve_account_ids", _ids)

    result = await pr.run_payroll(
        object(), **SCOPE, accounting_entity_id="primary", created_by="hr",
        year=2026, month=2, total_days=28,
    )
    slips = await pr.list_run_slips(**SCOPE, run_id=result["run_id"])
    a_slip = next(s for s in slips if s["employee_id"] == "A")
    assert a_slip["lop_days"] == D("3")
    assert a_slip["payment_days"] == D("25")
    # 125000 * 25/28, prorated per component then summed = 111607.15
    assert a_slip["earned_gross"] == D("111607.15")


async def _async_none():
    return None
