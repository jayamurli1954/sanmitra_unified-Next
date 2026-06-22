"""HR PDFs (Step 7) — salary slip and F&F statement render through the shared
documents layer to valid PDF bytes."""
from __future__ import annotations

from decimal import Decimal as D

from app.modules.hr.documents import (
    build_fnf_spec,
    build_salary_slip_spec,
    render_fnf_pdf,
    render_salary_slip_pdf,
)

_BRANDING = {"business_name": "Acme Pvt Ltd", "address": "Bengaluru", "gstin": "29ABCDE1234F1Z5"}
_EMP = {"full_name": "Asha Rao", "designation": "Analyst", "department": "Finance", "employee_id": "A"}

_SLIP = {
    "period": "2026-02", "employee_id": "A", "payment_days": D("28"), "lop_days": D("0"),
    "earnings": {"BASIC": D("62500.00"), "HRA": D("31250.00"), "SPECIAL": D("31250.00")},
    "earned_gross": D("125000.00"),
    "deductions": {"epf_employee": D("1800.00"), "esi_employee": D("0"),
                   "professional_tax": D("200.00"), "tds": D("8125.00"), "total": D("10125.00")},
    "net_pay": D("114875.00"),
}

_FNF = {
    "fnf_id": "abcd1234", "employee_id": "A", "last_working_day": "2026-01-01",
    "completed_years": 8, "status": "draft",
    "settlement": {"gratuity": "173076.92", "leave_encashment": "20000.00", "other_payouts": "0.00",
                   "gross_payout": "193076.92", "notice_recovery": "0.00", "other_recoveries": "0.00",
                   "total_recovery": "0.00", "net_settlement": "193076.92", "eligible_for_gratuity": True},
}


def test_salary_slip_spec_structure():
    spec = build_salary_slip_spec(_SLIP, _EMP, _BRANDING)
    assert spec.title == "Salary Slip"
    # 3 earnings + 3 non-zero deductions (esi_employee=0 dropped, total excluded).
    assert len(spec.lines) == 6
    assert spec.totals[-1].label == "Net Pay" and spec.totals[-1].emphasize


def test_salary_slip_pdf_renders():
    pdf = render_salary_slip_pdf(_SLIP, _EMP, _BRANDING)
    assert pdf[:4] == b"%PDF" and len(pdf) > 1000


def test_fnf_spec_and_pdf():
    spec = build_fnf_spec(_FNF, _EMP, _BRANDING)
    assert spec.title == "Full & Final Settlement"
    assert spec.totals[-1].label == "Net Settlement"
    pdf = render_fnf_pdf(_FNF, _EMP, _BRANDING)
    assert pdf[:4] == b"%PDF" and len(pdf) > 1000
