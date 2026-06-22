"""Form 12BB (Step 5) — declaration lifecycle, capped effective deductions,
proof guardrails, and the old-regime TDS impact in a payroll run."""
from __future__ import annotations

from decimal import Decimal

import pytest

import app.modules.hr.leave as hr_leave
import app.modules.hr.payroll_run as pr
import app.modules.hr.service as hr_service
import app.modules.hr.tax as tax

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


SCOPE = {"tenant_id": "t1", "app_key": "mitrabooks"}


@pytest.fixture
def db(monkeypatch):
    cols: dict[str, FakeCollection] = {}

    def _col(name):
        return cols.setdefault(name, FakeCollection())

    monkeypatch.setattr(tax, "get_collection", _col)
    monkeypatch.setattr(hr_service, "get_collection", _col)
    monkeypatch.setattr(pr, "get_collection", _col)
    monkeypatch.setattr(hr_leave, "get_collection", _col)
    cols.setdefault("hr_employees", FakeCollection()).docs.append(
        {**SCOPE, "employee_id": "A", "status": "active", "is_pf_eligible": True,
         "is_esic_eligible": False, "state_for_professional_tax": "Karnataka"}
    )
    return cols


async def _declare(section="80C", amount="200000", fy="2025-26"):
    return await tax.create_declaration(
        **SCOPE, created_by="A", employee_id="A", financial_year=fy,
        section_code=section, investment_name="ELSS", declared_amount=D(amount),
    )


# ── lifecycle ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_declaration_lifecycle_and_cap(db):
    d = await _declare(section="80C", amount="200000")
    assert d["status"] == "declared"
    # Verify above the 80C cap; effective deduction is capped at 150000.
    await tax.verify_declaration(**SCOPE, verified_by="hr", declaration_id=d["declaration_id"],
                                 verified_amount=D("200000"), approve=True)
    eff = await tax.compute_effective_deductions(**SCOPE, employee_id="A", financial_year="2025-26")
    assert eff["breakdown"]["80C"] == D("150000")
    assert eff["total_deductions"] == D("150000")
    assert eff["has_declarations"] is True


@pytest.mark.asyncio
async def test_rejected_declaration_excluded(db):
    d = await _declare(section="80D", amount="25000")
    await tax.verify_declaration(**SCOPE, verified_by="hr", declaration_id=d["declaration_id"],
                                 verified_amount=D("0"), approve=False, rejection_reason="no proof")
    eff = await tax.compute_effective_deductions(**SCOPE, employee_id="A", financial_year="2025-26")
    assert eff["total_deductions"] == D("0")
    assert eff["has_declarations"] is False


@pytest.mark.asyncio
async def test_multiple_sections_sum(db):
    for sec, amt in [("80C", "150000"), ("80D", "25000"), ("24B", "200000")]:
        d = await _declare(section=sec, amount=amt)
        await tax.verify_declaration(**SCOPE, verified_by="hr", declaration_id=d["declaration_id"],
                                     verified_amount=D(amt), approve=True)
    eff = await tax.compute_effective_deductions(**SCOPE, employee_id="A", financial_year="2025-26")
    assert eff["total_deductions"] == D("375000")  # 150000 + 25000 + 200000


@pytest.mark.asyncio
async def test_unknown_section_rejected(db):
    with pytest.raises(hr_service.HrValidationError):
        await _declare(section="99Z", amount="1000")


# ── proof guardrails ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_proof_upload_moves_to_submitted_and_type_checked(db):
    d = await _declare()
    proof = await tax.add_proof(**SCOPE, uploaded_by="A", declaration_id=d["declaration_id"],
                                file_name="ppf.pdf", content_type="application/pdf", payload=b"%PDF-1.4 ...")
    assert proof["size_bytes"] > 0
    decls = await tax.list_declarations(**SCOPE, employee_id="A")
    assert decls["declarations"][0]["status"] == "submitted"

    with pytest.raises(hr_service.HrValidationError):
        await tax.add_proof(**SCOPE, uploaded_by="A", declaration_id=d["declaration_id"],
                            file_name="x.exe", content_type="application/x-msdownload", payload=b"MZ")


@pytest.mark.asyncio
async def test_serializer_never_leaks_proof_bytes(db):
    d = await _declare()
    await tax.add_proof(**SCOPE, uploaded_by="A", declaration_id=d["declaration_id"],
                        file_name="ppf.pdf", content_type="application/pdf", payload=b"secret-bytes")
    listing = await tax.list_declarations(**SCOPE, employee_id="A")
    assert all("payload" not in row for row in listing["declarations"])


# ── integration: old-regime TDS uses verified deductions ──────────────────────

@pytest.mark.asyncio
async def test_old_regime_run_uses_verified_deductions(db, monkeypatch):
    components = [
        {"name": "Basic", "abbr": "BASIC", "formula": "GROSS * 0.5", "statutory_kind": "basic", "depends_on_payment_days": True},
        {"name": "HRA", "abbr": "HRA", "formula": "BASIC * 0.5", "depends_on_payment_days": True},
        {"name": "Special", "abbr": "SPECIAL", "formula": "GROSS - BASIC - HRA", "depends_on_payment_days": True},
    ]
    db.setdefault("hr_salary_structures", FakeCollection()).docs.append({**SCOPE, "structure_id": "s1", "components": components})
    db.setdefault("hr_salary_assignments", FakeCollection()).docs.append(
        {**SCOPE, "employee_id": "A", "structure_id": "s1", "monthly_gross": "100000", "regime": "old", "chapter_via_deductions": "0"}
    )
    # Approved 80C of 150000 for FY 2025-26 (Feb 2026 run).
    d = await _declare(section="80C", amount="150000", fy="2025-26")
    await tax.verify_declaration(**SCOPE, verified_by="hr", declaration_id=d["declaration_id"],
                                 verified_amount=D("150000"), approve=True)

    async def _post(session, **kwargs):
        class _J:
            id = 9
        return _J(), True

    monkeypatch.setattr(pr, "post_journal_entry", _post)
    monkeypatch.setattr(pr, "initialize_default_chart_of_accounts", lambda *a, **k: _an())
    async def _ids(*a, **k):
        return {c: i for i, c in enumerate(["52001", "52002", "23005", "23006", "23007", "23008", "21003"], 1)}
    monkeypatch.setattr(pr, "_resolve_account_ids", _ids)

    result = await pr.run_payroll(object(), **SCOPE, accounting_entity_id="primary", created_by="hr",
                                  year=2026, month=2, total_days=28)
    slip = (await pr.list_run_slips(**SCOPE, run_id=result["run_id"]))[0]
    # Old regime: annual 1,200,000 - std 50,000 - 80C 150,000 = taxable 1,000,000.
    # Old slabs: 12,500 + 100,000 = 112,500; +4% cess = 117,000; /12 = 9,750.
    assert slip["deductions"]["tds"] == D("9750.00")


async def _an():
    return None
