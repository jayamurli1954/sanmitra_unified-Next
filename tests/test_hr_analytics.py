"""Payroll analytics (Step 8) — trend assembly from stored run totals + headcount."""
from __future__ import annotations

import pytest

import app.modules.hr.analytics as analytics
import app.modules.hr.service as hr_service
import app.modules.hr.payroll_run as pr


class _Cursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, key, direction):
        self._docs.sort(key=lambda d: d.get(key) or "", reverse=direction < 0)
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    async def to_list(self, length=None):
        return list(self._docs)


class FakeCollection:
    def __init__(self):
        self.docs = []

    @staticmethod
    def _match(doc, flt):
        return all(doc.get(k) == v for k, v in flt.items())

    def find(self, flt):
        return _Cursor([dict(d) for d in self.docs if self._match(d, flt)])

    async def count_documents(self, flt):
        return sum(1 for d in self.docs if self._match(d, flt))


SCOPE = {"tenant_id": "t1", "app_key": "mitrabooks"}


@pytest.fixture
def db(monkeypatch):
    cols = {}

    def _col(name):
        return cols.setdefault(name, FakeCollection())

    monkeypatch.setattr(analytics, "get_collection", _col)
    return cols


@pytest.mark.asyncio
async def test_dashboard_builds_chronological_trend(db):
    runs = db.setdefault("hr_payroll_runs", FakeCollection())
    for period, tds, net, count in [("2026-01", "5000", "100000", 2), ("2026-02", "8125", "131660", 3)]:
        runs.docs.append({**SCOPE, "accounting_entity_id": "primary", "period": period,
                          "employee_count": count,
                          "totals": {"tds": tds, "epf": "5760", "net": net}})
    emps = db.setdefault("hr_employees", FakeCollection())
    emps.docs += [{**SCOPE, "status": "active"}, {**SCOPE, "status": "active"}, {**SCOPE, "status": "exited"}]

    out = await analytics.compile_dashboard(**SCOPE, accounting_entity_id="primary", months=6)
    assert out["labels"] == ["2026-01", "2026-02"]            # chronological
    assert out["datasets"]["tds_liability"] == [5000.0, 8125.0]
    assert out["datasets"]["net_disbursed"] == [100000.0, 131660.0]
    assert out["datasets"]["headcount"] == [2, 3]
    assert out["summary"]["active_employees"] == 2
    assert out["summary"]["exited_employees"] == 1
    assert out["summary"]["latest_period"] == "2026-02"
    assert out["summary"]["latest_tds"] == 8125.0


@pytest.mark.asyncio
async def test_dashboard_empty_when_no_runs(db):
    db.setdefault("hr_payroll_runs", FakeCollection())
    db.setdefault("hr_employees", FakeCollection())
    out = await analytics.compile_dashboard(**SCOPE, accounting_entity_id="primary")
    assert out["labels"] == []
    assert out["summary"]["latest_period"] is None
