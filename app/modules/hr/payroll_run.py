"""Payroll run (Step 3): batch over employees -> salary slips -> ONE consolidated
journal entry into the MitraBooks ledger.

This is what makes HR a real ERP feature rather than a standalone calculator: a
run posts salary expense + employer cost on the debit side and the statutory
payables + net-pay liability on the credit side, using the same
``post_journal_entry`` path invoices and vouchers use.

LOP is resolved through ``_resolve_lop_days`` — a seam that returns 0 in Step 3
and is replaced by the leave-ledger reconciler in Step 4.
"""
from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models.entities import Account
from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import initialize_default_chart_of_accounts, post_journal_entry
from app.core.audit.service import log_audit_event
from app.db.mongo import get_collection
from app.modules.hr.payroll_engine import PayrollInput, SalaryComponent, compute_payroll, q
from app.modules.hr.service import (
    HR_ASSIGNMENTS_COLLECTION,
    HR_EMPLOYEES_COLLECTION,
    HR_RUNS_COLLECTION,
    HR_SLIPS_COLLECTION,
    HR_STRUCTURES_COLLECTION,
    HrConflictError,
    HrValidationError,
    _now,
)

# Account codes for the payroll journal (provisioned by the default business COA).
ACC_SALARIES_EXPENSE = "52001"      # Dr gross earnings
ACC_EMPLOYER_EXPENSE = "52002"      # Dr employer EPF/ESI
ACC_EPF_PAYABLE = "23005"           # Cr EPF (employee + employer)
ACC_ESI_PAYABLE = "23006"           # Cr ESI (employee + employer)
ACC_PT_PAYABLE = "23007"            # Cr professional tax
ACC_TDS_PAYABLE = "23008"           # Cr salary TDS
ACC_SALARIES_PAYABLE = "21003"      # Cr net pay


async def _resolve_lop_days(
    *, tenant_id: str, app_key: str, employee_id: str, year: int, month: int
) -> Decimal:
    """Loss-of-pay days for the period — derived (Step 4) from approved leave
    applications via the leave ledger; HR never types an LOP number."""
    from app.modules.hr.leave import resolve_lop_days

    return await resolve_lop_days(
        tenant_id=tenant_id, app_key=app_key, employee_id=employee_id, year=year, month=month
    )


def _fy_label(year: int, month: int) -> str:
    """Indian financial year label (e.g. Feb 2026 -> '2025-26')."""
    fy_start = year if month >= 4 else year - 1
    return f"{fy_start}-{str(fy_start + 1)[-2:]}"


async def _resolve_chapter_deductions(
    *, tenant_id: str, app_key: str, employee_id: str, year: int, month: int, fallback: Decimal
) -> Decimal:
    """Old-regime Chapter VI-A deductions: prefer HR-approved Form 12BB
    verified amounts; fall back to the assignment's manual estimate."""
    from app.modules.hr.tax import compute_effective_deductions

    result = await compute_effective_deductions(
        tenant_id=tenant_id, app_key=app_key, employee_id=employee_id,
        financial_year=_fy_label(year, month),
    )
    return result["total_deductions"] if result["has_declarations"] else fallback


async def _resolve_account_ids(
    session: AsyncSession, *, tenant_id: str, app_key: str, accounting_entity_id: str, codes: list[str]
) -> dict[str, int]:
    rows = (
        await session.execute(
            select(Account.code, Account.id).where(
                Account.tenant_id == tenant_id,
                Account.app_key == app_key,
                Account.accounting_entity_id == accounting_entity_id,
                Account.code.in_(codes),
            )
        )
    ).all()
    return {str(code): int(acc_id) for code, acc_id in rows}


def _components_from_structure(structure: dict) -> list[SalaryComponent]:
    return [
        SalaryComponent(
            name=c["name"],
            abbr=c["abbr"],
            formula=c["formula"],
            statutory_kind=c.get("statutory_kind"),
            depends_on_payment_days=c.get("depends_on_payment_days", True),
        )
        for c in structure.get("components", [])
    ]


async def run_payroll(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    created_by: str,
    year: int,
    month: int,
    total_days: int | None = None,
) -> dict:
    period = f"{year:04d}-{month:02d}"
    runs = get_collection(HR_RUNS_COLLECTION)

    existing = await runs.find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id, "period": period}
    )
    if existing is not None:
        raise HrConflictError(f"Payroll has already been run for {period}")

    calendar_days = calendar.monthrange(year, month)[1]
    period_days = Decimal(total_days or calendar_days)

    employees = (
        await get_collection(HR_EMPLOYEES_COLLECTION)
        .find({"tenant_id": tenant_id, "app_key": app_key, "status": "active"})
        .to_list(length=5000)
    )

    structure_cache: dict[str, dict] = {}
    run_id = str(uuid4())
    slips: list[dict] = []
    totals = {
        "gross": Decimal("0"), "employer": Decimal("0"), "epf": Decimal("0"),
        "esi": Decimal("0"), "pt": Decimal("0"), "tds": Decimal("0"), "net": Decimal("0"),
    }

    for emp in employees:
        employee_id = emp["employee_id"]
        assignment = await get_collection(HR_ASSIGNMENTS_COLLECTION).find_one(
            {"tenant_id": tenant_id, "app_key": app_key, "employee_id": employee_id}
        )
        if assignment is None:
            continue  # no salary assigned -> not payrolled

        structure_id = assignment["structure_id"]
        structure = structure_cache.get(structure_id)
        if structure is None:
            structure = await get_collection(HR_STRUCTURES_COLLECTION).find_one(
                {"tenant_id": tenant_id, "app_key": app_key, "structure_id": structure_id}
            )
            if structure is None:
                continue
            structure_cache[structure_id] = structure

        lop = await _resolve_lop_days(
            tenant_id=tenant_id, app_key=app_key, employee_id=employee_id, year=year, month=month
        )
        payment_days = max(Decimal("0"), period_days - lop)

        regime = assignment.get("regime", "new")
        deductions = Decimal(str(assignment.get("chapter_via_deductions", "0")))
        if regime == "old":
            deductions = await _resolve_chapter_deductions(
                tenant_id=tenant_id, app_key=app_key, employee_id=employee_id,
                year=year, month=month, fallback=deductions,
            )

        result = compute_payroll(
            PayrollInput(
                monthly_gross=Decimal(str(assignment["monthly_gross"])),
                components=_components_from_structure(structure),
                payment_days=payment_days,
                total_days=period_days,
                regime=regime,
                pf_eligible=bool(emp.get("is_pf_eligible", True)),
                esi_eligible=bool(emp.get("is_esic_eligible", False)),
                pt_state=emp.get("state_for_professional_tax"),
                chapter_via_deductions=deductions,
            )
        )

        ded = result["deductions"]
        emp_contrib = result["employer_contributions"]
        slip = {
            "slip_id": str(uuid4()),
            "run_id": run_id,
            "tenant_id": tenant_id,
            "app_key": app_key,
            "accounting_entity_id": accounting_entity_id,
            "employee_id": employee_id,
            "period": period,
            "payment_days": q(payment_days),
            "total_days": q(period_days),
            "lop_days": q(lop),
            "earnings": result["earnings"],
            "earned_gross": result["earned_gross"],
            "deductions": ded,
            "employer_contributions": emp_contrib,
            "net_pay": result["net_pay"],
            "created_at": _now(),
        }
        slips.append(slip)

        totals["gross"] += result["earned_gross"]
        totals["employer"] += emp_contrib["epf_employer"] + emp_contrib["esi_employer"]
        totals["epf"] += ded["epf_employee"] + emp_contrib["epf_employer"]
        totals["esi"] += ded["esi_employee"] + emp_contrib["esi_employer"]
        totals["pt"] += ded["professional_tax"]
        totals["tds"] += ded["tds"]
        totals["net"] += result["net_pay"]

    if not slips:
        raise HrValidationError("No active employees with a salary assignment to run payroll for")

    totals = {k: q(v) for k, v in totals.items()}

    # Provision the payroll COA accounts (idempotent), then resolve their ids.
    await initialize_default_chart_of_accounts(
        session, tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, organization_type="BUSINESS",
    )
    codes = [
        ACC_SALARIES_EXPENSE, ACC_EMPLOYER_EXPENSE, ACC_EPF_PAYABLE,
        ACC_ESI_PAYABLE, ACC_PT_PAYABLE, ACC_TDS_PAYABLE, ACC_SALARIES_PAYABLE,
    ]
    account_ids = await _resolve_account_ids(
        session, tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, codes=codes,
    )
    missing = [c for c in codes if c not in account_ids]
    if missing:
        raise HrValidationError(f"Payroll accounts missing from chart of accounts: {missing}")

    # Build journal lines, skipping zero amounts. Debits = gross + employer cost;
    # credits = statutory payables + net pay.
    debit_credit = [
        (ACC_SALARIES_EXPENSE, totals["gross"], Decimal("0")),
        (ACC_EMPLOYER_EXPENSE, totals["employer"], Decimal("0")),
        (ACC_EPF_PAYABLE, Decimal("0"), totals["epf"]),
        (ACC_ESI_PAYABLE, Decimal("0"), totals["esi"]),
        (ACC_PT_PAYABLE, Decimal("0"), totals["pt"]),
        (ACC_TDS_PAYABLE, Decimal("0"), totals["tds"]),
        (ACC_SALARIES_PAYABLE, Decimal("0"), totals["net"]),
    ]
    lines = [
        JournalLineIn(account_id=account_ids[code], debit=debit, credit=credit)
        for code, debit, credit in debit_credit
        if debit > 0 or credit > 0
    ]

    month_last = date(year, month, calendar_days)
    journal_entry, _created = await post_journal_entry(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        created_by=created_by,
        payload=JournalPostRequest(
            entry_date=month_last,
            description=f"Payroll {period}",
            reference=f"PAYROLL-{period}",
            source_module="hr_payroll",
            source_document_type="payroll_run",
            source_document_id=run_id,
            lines=lines,
        ),
        idempotency_key=f"hr-payroll:{tenant_id}:{accounting_entity_id}:{period}",
    )

    run_doc = {
        "run_id": run_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "period": period,
        "status": "posted",
        "employee_count": len(slips),
        "totals": {k: str(v) for k, v in totals.items()},
        "journal_entry_id": int(journal_entry.id),
        "created_by": created_by,
        "created_at": _now(),
    }
    await runs.insert_one(dict(run_doc))
    if slips:
        await get_collection(HR_SLIPS_COLLECTION).insert_many([dict(s) for s in slips])

    try:
        await log_audit_event(
            tenant_id=tenant_id, user_id=created_by, product=app_key,
            action="hr_payroll_run_posted", entity_type="hr_payroll_run", entity_id=run_id,
            new_value={"period": period, "employee_count": len(slips), "net_total": str(totals["net"])},
        )
    except Exception:
        pass

    return _serialize_run(run_doc, slips)


def _serialize_run(run_doc: dict, slips: list[dict]) -> dict:
    return {
        "run_id": run_doc["run_id"],
        "period": run_doc["period"],
        "status": run_doc["status"],
        "employee_count": run_doc["employee_count"],
        "totals": {k: Decimal(v) for k, v in run_doc["totals"].items()},
        "journal_entry_id": run_doc.get("journal_entry_id"),
        "slips": [_serialize_slip(s) for s in slips],
    }


def _serialize_slip(slip: dict) -> dict:
    return {
        "slip_id": slip["slip_id"],
        "run_id": slip["run_id"],
        "employee_id": slip["employee_id"],
        "period": slip["period"],
        "payment_days": slip["payment_days"],
        "total_days": slip["total_days"],
        "lop_days": slip["lop_days"],
        "earnings": slip["earnings"],
        "earned_gross": slip["earned_gross"],
        "deductions": slip["deductions"],
        "employer_contributions": slip["employer_contributions"],
        "net_pay": slip["net_pay"],
    }


async def list_payroll_runs(*, tenant_id: str, app_key: str, accounting_entity_id: str) -> dict:
    runs = get_collection(HR_RUNS_COLLECTION)
    filters = {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
    rows = await runs.find(filters).sort("period", -1).limit(200).to_list(length=200)
    total = await runs.count_documents(filters)
    return {"runs": [_serialize_run(r, []) for r in rows], "total": total}


async def list_run_slips(*, tenant_id: str, app_key: str, run_id: str) -> list[dict]:
    rows = (
        await get_collection(HR_SLIPS_COLLECTION)
        .find({"tenant_id": tenant_id, "app_key": app_key, "run_id": run_id})
        .to_list(length=5000)
    )
    return [_serialize_slip(r) for r in rows]


async def get_slip(*, tenant_id: str, app_key: str, slip_id: str) -> dict:
    from app.modules.hr.service import HrNotFoundError

    row = await get_collection(HR_SLIPS_COLLECTION).find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "slip_id": slip_id}
    )
    if row is None:
        raise HrNotFoundError("Salary slip not found")
    return _serialize_slip(row)
