"""Map HR records into the shared document renderer (Step 7).

Reuses ``app/core/documents`` — the same PDF layer the MitraBooks invoice uses —
so a salary slip and an F&F statement render through one renderer with no new PDF
engine. Money uses the ₹ glyph; the renderer wraps it in a font that has it and
falls back to "Rs." otherwise.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.core.documents import (
    DocumentColumn,
    DocumentLine,
    DocumentParty,
    DocumentSpec,
    TotalRow,
    render_document_pdf,
)

# Human labels for the statutory deduction keys the engine emits.
_DEDUCTION_LABELS = {
    "epf_employee": "EPF (Employee)",
    "esi_employee": "ESI (Employee)",
    "professional_tax": "Professional Tax",
    "tds": "TDS",
}


def _dec(value) -> Decimal:
    try:
        return Decimal(str(value if value not in (None, "") else "0"))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def _money(value) -> str:
    return f"₹{_dec(value):,.2f}"


def _seller_from_branding(branding: dict) -> DocumentParty:
    branding = branding or {}
    name = str(branding.get("business_name") or "").strip() or "Your Business"
    address = str(branding.get("address") or "").strip()
    address_lines = [seg.strip() for seg in address.replace("\r", "").split("\n") if seg.strip()]
    return DocumentParty(name=name, address_lines=address_lines, gstin=branding.get("gstin") or None)


def _employee_party(employee: dict) -> DocumentParty:
    lines = []
    if employee.get("designation"):
        lines.append(str(employee["designation"]))
    if employee.get("department"):
        lines.append(str(employee["department"]))
    return DocumentParty(name=str(employee.get("full_name") or employee.get("employee_id") or "Employee"),
                         address_lines=lines)


def build_salary_slip_spec(slip: dict, employee: dict, branding: dict) -> DocumentSpec:
    columns = [
        DocumentColumn("component", "Component", align="left", weight=3),
        DocumentColumn("earnings", "Earnings", align="right", weight=1.5),
        DocumentColumn("deductions", "Deductions", align="right", weight=1.5),
    ]
    lines: list[DocumentLine] = []
    for abbr, amount in (slip.get("earnings") or {}).items():
        lines.append(DocumentLine({"component": abbr, "earnings": _money(amount), "deductions": ""}))
    for key, amount in (slip.get("deductions") or {}).items():
        if key == "total" or _dec(amount) == 0:
            continue
        lines.append(DocumentLine({"component": _DEDUCTION_LABELS.get(key, key), "earnings": "", "deductions": _money(amount)}))

    totals = [
        TotalRow("Gross Earnings", _money(slip.get("earned_gross"))),
        TotalRow("Total Deductions", _money((slip.get("deductions") or {}).get("total"))),
        TotalRow("Net Pay", _money(slip.get("net_pay")), emphasize=True),
    ]
    meta = [
        ("Pay Period", str(slip.get("period") or "")),
        ("Employee ID", str(slip.get("employee_id") or "")),
        ("Payable Days", str(slip.get("payment_days") or "")),
        ("LOP Days", str(slip.get("lop_days") or "")),
    ]
    return DocumentSpec(
        title="Salary Slip",
        number=str(slip.get("period") or slip.get("slip_id") or ""),
        seller=_seller_from_branding(branding),
        buyer=_employee_party(employee),
        buyer_heading="Employee",
        columns=columns,
        lines=lines,
        totals=totals,
        meta=meta,
        footer_note="This is a system-generated salary slip.",
    )


def render_salary_slip_pdf(slip: dict, employee: dict, branding: dict) -> bytes:
    return render_document_pdf(build_salary_slip_spec(slip, employee, branding))


def build_fnf_spec(fnf: dict, employee: dict, branding: dict) -> DocumentSpec:
    s = fnf.get("settlement") or {}
    columns = [
        DocumentColumn("item", "Item", align="left", weight=3),
        DocumentColumn("payout", "Payout", align="right", weight=1.5),
        DocumentColumn("recovery", "Recovery", align="right", weight=1.5),
    ]
    lines = [
        DocumentLine({"item": "Gratuity", "payout": _money(s.get("gratuity")), "recovery": ""}),
        DocumentLine({"item": "Leave Encashment", "payout": _money(s.get("leave_encashment")), "recovery": ""}),
        DocumentLine({"item": "Other Payouts", "payout": _money(s.get("other_payouts")), "recovery": ""}),
        DocumentLine({"item": "Notice Recovery", "payout": "", "recovery": _money(s.get("notice_recovery"))}),
        DocumentLine({"item": "Other Recoveries", "payout": "", "recovery": _money(s.get("other_recoveries"))}),
    ]
    totals = [
        TotalRow("Gross Payout", _money(s.get("gross_payout"))),
        TotalRow("Total Recovery", _money(s.get("total_recovery"))),
        TotalRow("Net Settlement", _money(s.get("net_settlement")), emphasize=True),
    ]
    meta = [
        ("Employee ID", str(fnf.get("employee_id") or "")),
        ("Last Working Day", str(fnf.get("last_working_day") or "")),
        ("Years of Service", str(fnf.get("completed_years") or "")),
        ("Status", str(fnf.get("status") or "")),
    ]
    return DocumentSpec(
        title="Full & Final Settlement",
        number=str(fnf.get("fnf_id") or "")[:8],
        seller=_seller_from_branding(branding),
        buyer=_employee_party(employee),
        buyer_heading="Employee",
        columns=columns,
        lines=lines,
        totals=totals,
        meta=meta,
        footer_note="This is a system-generated settlement statement.",
    )


def render_fnf_pdf(fnf: dict, employee: dict, branding: dict) -> bytes:
    return render_document_pdf(build_fnf_spec(fnf, employee, branding))
