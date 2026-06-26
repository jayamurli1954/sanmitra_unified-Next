"""HR payroll run (Step 3) — batch compute -> salary slips -> balanced GL journal.
Mongo and the journal posting are faked; the statutory math is the real engine."""
from __future__ import annotations

from decimal import Decimal

import pytest

import app.modules.hr.leave as hr_leave
import app.modules.hr.payroll_run as pr
import app.modules.hr.service as hr_service

D = Decimal


# ── fake mongo ────────────────────────────────────────────────────────────────

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


class _Journal:
    id = 42


@pytest.fixture
def fake_db(monkeypatch):
    cols: dict[str, FakeCollection] = {}

    def _col(name):
        return cols.setdefault(name, FakeCollection())

    monkeypatch.setattr(pr, "get_collection", _col)
    monkeypatch.setattr(hr_service, "get_collection", _col)
    monkeypatch.setattr(hr_leave, "get_collection", _col)  # _resolve_lop_days -> leave
    return cols


@pytest.fixture
def captured_journal(monkeypatch):
    box = {}

    async def _fake_post(session, **kwargs):
        box["payload"] = kwargs["payload"]
        box["idempotency_key"] = kwargs["idempotency_key"]
        return _Journal(), True

    async def _noop_coa(*_a, **_k):
        return {}

    async def _ids(*_a, **_k):
        return {
            "52001": 1, "52002": 2, "23005": 3, "23006": 4,
            "23007": 5, "23008": 6, "21003": 7,
        }

    monkeypatch.setattr(pr, "post_journal_entry", _fake_post)
    monkeypatch.setattr(pr, "initialize_default_chart_of_accounts", _noop_coa)
    monkeypatch.setattr(pr, "_resolve_account_ids", _ids)
    return box


@pytest.fixture
def captured_reversal(monkeypatch):
    box = {}

    async def _fake_reverse(session, **kwargs):
        box.update(kwargs)
        return _Journal(), True

    monkeypatch.setattr(pr, "reverse_journal_entry", _fake_reverse)
    return box


def _seed(cols):
    emp = cols.setdefault("hr_employees", FakeCollection())
    asg = cols.setdefault("hr_salary_assignments", FakeCollection())
    st = cols.setdefault("hr_salary_structures", FakeCollection())
    scope = {"tenant_id": "t1", "app_key": "mitrabooks"}
    components = [
        {"name": "Basic", "abbr": "BASIC", "formula": "GROSS * 0.5", "statutory_kind": "basic", "depends_on_payment_days": True},
        {"name": "HRA", "abbr": "HRA", "formula": "BASIC * 0.5", "depends_on_payment_days": True},
        {"name": "Special", "abbr": "SPECIAL", "formula": "GROSS - BASIC - HRA", "depends_on_payment_days": True},
    ]
    st.docs.append({**scope, "structure_id": "s1", "components": components})
    # A: high earner, ESI not applicable
    emp.docs.append({**scope, "employee_id": "A", "status": "active", "is_pf_eligible": True, "is_esic_eligible": False, "state_for_professional_tax": "Karnataka"})
    asg.docs.append({**scope, "employee_id": "A", "structure_id": "s1", "monthly_gross": "125000", "regime": "new", "chapter_via_deductions": "0"})
    # B: low earner, ESI applicable
    emp.docs.append({**scope, "employee_id": "B", "status": "active", "is_pf_eligible": True, "is_esic_eligible": True, "state_for_professional_tax": "Karnataka"})
    asg.docs.append({**scope, "employee_id": "B", "structure_id": "s1", "monthly_gross": "18000", "regime": "new", "chapter_via_deductions": "0"})
    # C: active but no salary assignment -> skipped
    emp.docs.append({**scope, "employee_id": "C", "status": "active"})


@pytest.mark.asyncio
async def test_payroll_run_totals_and_balanced_journal(fake_db, captured_journal):
    _seed(fake_db)
    result = await pr.run_payroll(
        object(), tenant_id="t1", app_key="mitrabooks", accounting_entity_id="primary",
        created_by="admin", year=2026, month=2, total_days=28,
    )

    assert result["employee_count"] == 2  # C skipped
    t = result["totals"]
    assert t["gross"] == D("143000.00")
    assert t["employer"] == D("3465.00")
    assert t["epf"] == D("5760.00")
    assert t["esi"] == D("720.00")
    assert t["pt"] == D("200.00")
    assert t["tds"] == D("8125.00")
    assert t["net"] == D("131660.00")
    assert result["journal_entry_id"] == 42

    # The consolidated journal must balance.
    lines = captured_journal["payload"].lines
    total_debit = sum((ln.debit for ln in lines), D("0"))
    total_credit = sum((ln.credit for ln in lines), D("0"))
    assert total_debit == total_credit == D("146465.00")

    by_acct = {ln.account_id: (ln.debit, ln.credit) for ln in lines}
    assert by_acct[1] == (D("143000.00"), D("0"))   # 52001 salaries expense (Dr)
    assert by_acct[2] == (D("3465.00"), D("0"))     # 52002 employer cost (Dr)
    assert by_acct[3] == (D("0"), D("5760.00"))     # 23005 EPF payable (Cr)
    assert by_acct[7] == (D("0"), D("131660.00"))   # 21003 salaries payable (Cr)
    assert captured_journal["idempotency_key"] == "hr-payroll:t1:primary:2026-02"


@pytest.mark.asyncio
async def test_double_run_rejected(fake_db, captured_journal):
    _seed(fake_db)
    kwargs = dict(tenant_id="t1", app_key="mitrabooks", accounting_entity_id="primary",
                  created_by="admin", year=2026, month=2, total_days=28)
    await pr.run_payroll(object(), **kwargs)
    with pytest.raises(hr_service.HrConflictError):
        await pr.run_payroll(object(), **kwargs)


@pytest.mark.asyncio
async def test_run_with_no_assignments_raises(fake_db, captured_journal):
    # Active employee but no assignment anywhere.
    fake_db.setdefault("hr_employees", FakeCollection()).docs.append(
        {"tenant_id": "t1", "app_key": "mitrabooks", "employee_id": "Z", "status": "active"}
    )
    with pytest.raises(hr_service.HrValidationError):
        await pr.run_payroll(
            object(), tenant_id="t1", app_key="mitrabooks", accounting_entity_id="primary",
            created_by="admin", year=2026, month=3,
        )


@pytest.mark.asyncio
async def test_slips_persisted_and_listable(fake_db, captured_journal):
    _seed(fake_db)
    result = await pr.run_payroll(
        object(), tenant_id="t1", app_key="mitrabooks", accounting_entity_id="primary",
        created_by="admin", year=2026, month=2, total_days=28,
    )
    slips = await pr.list_run_slips(tenant_id="t1", app_key="mitrabooks", run_id=result["run_id"])
    assert len(slips) == 2
    a = next(s for s in slips if s["employee_id"] == "A")
    assert a["net_pay"] == D("114875.00")
    assert a["deductions"]["tds"] == D("8125.00")


@pytest.mark.asyncio
async def test_payroll_run_reverses_journal_when_mongo_persistence_fails(fake_db, captured_journal, captured_reversal):
    _seed(fake_db)

    runs = fake_db.setdefault("hr_payroll_runs", FakeCollection())

    async def _failing_insert_one(doc):
        raise RuntimeError("mongo write failed")

    runs.insert_one = _failing_insert_one

    with pytest.raises(hr_service.HrValidationError, match="automatically reversed"):
        await pr.run_payroll(
            object(), tenant_id="t1", app_key="mitrabooks", accounting_entity_id="primary",
            created_by="admin", year=2026, month=2, total_days=28,
        )

    assert captured_reversal["tenant_id"] == "t1"
    assert captured_reversal["journal_id"] == 42
    assert captured_reversal["app_key"] == "mitrabooks"
