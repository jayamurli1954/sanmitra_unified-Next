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


# --------------------------------------------------------------------------- #
# Appointment letter — prose document (rendered directly with reportlab, since
# the shared DocumentSpec layer is line-item/totals shaped, not letter-shaped).
# --------------------------------------------------------------------------- #

# Standard Indian-SMB clause texts, toggled per tenant via AppointmentConfig.
_CLAUSE_TEXT = {
    "background_check": "This appointment is contingent upon successful completion of background verification, including verification of your educational qualifications, prior employment records and references. The Company reserves the right to withdraw this offer or terminate employment if any information furnished is found to be false or misleading.",
    "confidentiality_nda": "You shall maintain strict confidentiality of all proprietary and confidential information of the Company — including business strategies, financial data, client lists and trade secrets — both during and after your employment, and shall not disclose such information to any third party.",
    "ip_assignment": "All work product, inventions, designs, software code and intellectual property created by you in the course of your employment shall be the sole and exclusive property of the Company.",
    "data_privacy": "You shall handle all customer and Company data in accordance with applicable data-protection laws and Company privacy policies, and shall not misuse, copy or disclose any personal or sensitive data.",
    "code_of_conduct": "You shall adhere to the Company's Code of Conduct, Employee Handbook and all policies as amended from time to time, and maintain professional discipline and integrity at all times.",
    "cash_handling": "You shall be responsible and accountable for any cash, stock, inventory or Company property entrusted to you, and shall be liable for shortages, shrinkage or loss arising from negligence; such amounts may be recovered from your dues.",
    "relocation": "Based on operational requirements, the Company may change your shift timings or work location, or transfer you to any other branch, department or associate establishment.",
}
_CLAUSE_ORDER = [
    "background_check", "confidentiality_nda", "ip_assignment",
    "data_privacy", "code_of_conduct", "cash_handling", "relocation",
]


def _today_str() -> str:
    from datetime import date
    return date.today().strftime("%d %B %Y")


def render_appointment_letter_pdf(*, employee: dict, monthly_gross, breakdown: dict, branding: dict, config: dict) -> bytes:
    """Render a configurable appointment letter to PDF bytes.

    ``breakdown`` is a payroll-engine ``compute_payroll`` result (full month) used
    for the compensation table; ``config`` is the tenant's AppointmentConfig.
    """
    from io import BytesIO

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    body = ParagraphStyle("al-body", fontName="Helvetica", fontSize=10, leading=14, spaceAfter=6)
    h = ParagraphStyle("al-h", fontName="Helvetica-Bold", fontSize=14, leading=17, spaceAfter=2)
    sub = ParagraphStyle("al-sub", fontName="Helvetica", fontSize=8.5, leading=11, textColor=colors.HexColor("#555555"))
    bold = ParagraphStyle("al-bold", parent=body, fontName="Helvetica-Bold")

    branding = branding or {}
    config = config or {}
    clauses = config.get("clauses") or {}
    company = str(branding.get("business_name") or "Your Company")
    address = str(branding.get("address") or "").replace("\r", "")
    gstin = branding.get("gstin")

    def money(v):
        return "Rs. " + f"{_dec(v):,.2f}"

    earnings = breakdown.get("earnings") or {}
    ded = breakdown.get("deductions") or {}
    emp_contrib = breakdown.get("employer_contributions") or {}
    gross_m = _dec(breakdown.get("earned_gross") or monthly_gross)
    employer_m = _dec(emp_contrib.get("epf_employer")) + _dec(emp_contrib.get("esi_employer"))
    ctc_m = gross_m + employer_m

    def row(label, m):
        return [Paragraph(label, body), Paragraph(money(m), body), Paragraph(money(_dec(m) * 12), body)]

    comp_rows = [[Paragraph("Component", bold), Paragraph("Monthly", bold), Paragraph("Annual", bold)]]
    comp_rows.append(row("Basic", earnings.get("BASIC", 0)))
    comp_rows.append(row("HRA", earnings.get("HRA", 0)))
    comp_rows.append(row("Special Allowance", earnings.get("SPECIAL", 0)))
    comp_rows.append([Paragraph("Gross Salary", bold), Paragraph(money(gross_m), bold), Paragraph(money(gross_m * 12), bold)])
    comp_rows.append(row("Less: EPF (Employee)", ded.get("epf_employee", 0)))
    comp_rows.append(row("Less: ESI (Employee)", ded.get("esi_employee", 0)))
    comp_rows.append(row("Less: Professional Tax", ded.get("professional_tax", 0)))
    comp_rows.append(row("Less: TDS (estimated)", ded.get("tds", 0)))
    comp_rows.append([Paragraph("Net Take-home", bold), Paragraph(money(breakdown.get("net_pay", 0)), bold), Paragraph(money(_dec(breakdown.get("net_pay", 0)) * 12), bold)])
    comp_rows.append(row("Employer EPF/ESI", employer_m))
    comp_rows.append([Paragraph("Cost to Company (CTC)", bold), Paragraph(money(ctc_m), bold), Paragraph(money(ctc_m * 12), bold)])

    comp_table = Table(comp_rows, colWidths=[80 * mm, 45 * mm, 45 * mm])
    comp_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F0F0F0")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    story = [Paragraph(company, h)]
    for line in [seg.strip() for seg in address.split("\n") if seg.strip()]:
        story.append(Paragraph(line, sub))
    if gstin:
        story.append(Paragraph(f"GSTIN: {gstin}", sub))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Date: {_today_str()}", body))
    story.append(Paragraph(f"Ref: APPT/{employee.get('user_id') or employee.get('employee_id', '')[:8]}", sub))
    story.append(Spacer(1, 8))

    name = str(employee.get("full_name") or "Employee")
    designation = str(employee.get("designation") or "Employee")
    dept = employee.get("department")
    doj = str(employee.get("date_of_joining") or "")
    story.append(Paragraph(f"Dear {name},", body))
    story.append(Paragraph("<b>Subject: Letter of Appointment</b>", body))
    dept_txt = f" in the {dept} department" if dept else ""
    story.append(Paragraph(
        f"We are pleased to offer you the position of <b>{designation}</b>{dept_txt} at {company}. "
        f"Your employment will commence on <b>{doj}</b>. Your Employee ID is "
        f"<b>{employee.get('user_id') or employee.get('employee_id')}</b>.", body))

    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Compensation</b>", body))
    story.append(comp_table)
    story.append(Spacer(1, 6))

    probation = config.get("probation_months", 6)
    notice = config.get("notice_days", 30)
    work_hours = config.get("work_hours") or "as per Company policy"
    terms = [
        f"<b>Probation:</b> You will be on probation for {probation} months from your date of joining. Upon satisfactory performance your employment will be confirmed in writing.",
        f"<b>Notice Period:</b> After confirmation, either party may terminate this employment by giving {notice} days' written notice or salary in lieu thereof. The Company may terminate without notice in cases of misconduct, fraud, theft or breach of policy.",
        f"<b>Working Hours:</b> Your normal working hours will be {work_hours}.",
    ]
    n = 1
    for t in terms:
        story.append(Paragraph(f"{n}. {t}", body)); n += 1
    for key in _CLAUSE_ORDER:
        if clauses.get(key):
            story.append(Paragraph(f"{n}. {_CLAUSE_TEXT[key]}", body)); n += 1

    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Please sign and return a copy of this letter as a token of your acceptance of the terms and conditions stated above.", body))
    story.append(Spacer(1, 16))

    sig_name = config.get("signatory_name") or ""
    sig_title = config.get("signatory_title") or "Authorised Signatory"
    sig_table = Table([[
        Paragraph(f"For {company}<br/><br/><br/>_________________________<br/>{sig_name}<br/>{sig_title}", body),
        Paragraph(f"Accepted by<br/><br/><br/>_________________________<br/>{name}<br/>Date: ____________", body),
    ]], colWidths=[85 * mm, 85 * mm])
    sig_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(sig_table)

    buf = BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                      topMargin=16 * mm, bottomMargin=16 * mm).build(story)
    return buf.getvalue()
