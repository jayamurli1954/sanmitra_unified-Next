"""HTTP routes for the MitraBooks HR / Payroll add-on (v1 foundation)."""
from __future__ import annotations

import re
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, File, Form, Header, HTTPException, Query, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import AppTenantContext, resolve_business_app_tenant
from app.core.tenants.service import get_tenant
from app.db.postgres import get_async_session
from app.modules.hr import analytics as analytics_module
from app.modules.hr import documents as hr_documents
from app.modules.hr import fnf as fnf_module
from app.modules.hr import leave as leave_module
from app.modules.hr import tax as tax_module
from app.modules.hr.gating import HR_MANAGE_ROLES, require_hr_context, resolve_hr_access
from app.modules.hr.payroll_run import get_slip, list_payroll_runs, list_run_slips, run_payroll
from app.modules.hr.schemas import (
    EmployeeCreateRequest,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeUpdateRequest,
    LeaveAllocationRequest,
    LeaveApplicationListResponse,
    LeaveApplicationRequest,
    LeaveApplicationResponse,
    LeaveBalancesResponse,
    LeaveTypeCreateRequest,
    LeaveTypeListResponse,
    LeaveTypeResponse,
    AppointmentConfig,
    AppointmentConfigResponse,
    EffectiveDeductionsResponse,
    FnfCreateRequest,
    FnfListResponse,
    FnfResponse,
    TaxDeclarationCreateRequest,
    TaxDeclarationListResponse,
    TaxDeclarationResponse,
    TaxProofResponse,
    TaxVerifyRequest,
    PayrollRunListResponse,
    PayrollRunRequest,
    PayrollRunResponse,
    SalaryAssignmentRequest,
    SalaryAssignmentResponse,
    SalarySlipResponse,
    SalaryStructureCreateRequest,
    SalaryStructureListResponse,
    SalaryStructureResponse,
)
from app.modules.hr.service import (
    HrConflictError,
    HrNotFoundError,
    HrValidationError,
    create_employee,
    create_salary_structure,
    get_appointment_config,
    get_employee,
    get_salary_assignment,
    get_salary_structure,
    list_employees,
    list_salary_structures,
    save_appointment_config,
    update_employee,
    upsert_salary_assignment,
)

# Namespaced under MitraBooks (/business) rather than a global /hr — the unprefixed
# mandir_compat router already serves stub /hr/* paths, and HR is a MitraBooks
# add-on, so /business/hr keeps it clearly scoped and collision-free.
router = APIRouter(prefix="/business/hr", tags=["hr"])


def _actor(current_user: dict) -> str:
    return str(
        current_user.get("sub")
        or current_user.get("user_id")
        or current_user.get("email")
        or "system"
    )


async def _branding(context: AppTenantContext) -> dict:
    from app.modules.business.service import get_invoice_settings

    settings = await get_invoice_settings(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=context.accounting_entity_id,
    )
    return (settings or {}).get("branding") or {}


def _pdf_response(content: bytes, filename: str) -> Response:
    safe = re.sub(r"[\x00-\x1f\x7f]", "", filename)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(safe)}"},
    )


@router.get("/access")
async def hr_access(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_accounting_entity_id: str | None = Header(default=None, alias="X-Accounting-Entity-ID"),
):
    """Entitlement probe for the dashboard — never 403s on a disabled add-on.
    The frontend uses this to decide whether to render the HR menu and which
    actions to expose."""
    return await resolve_hr_access(
        current_user=current_user, x_tenant_id=x_tenant_id,
        x_app_key=x_app_key, x_accounting_entity_id=x_accounting_entity_id,
    )


@router.put("/enabled")
async def hr_set_enabled(
    enabled: bool = Body(..., embed=True),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_accounting_entity_id: str | None = Header(default=None, alias="X-Accounting-Entity-ID"),
):
    """Tenant-admin toggle for hr_enabled. Cannot use the normal HR gate (that
    requires hr_enabled already true), so it checks provisioning + role here."""
    from app.modules.business.service import set_hr_enabled

    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="HR enable toggle",
        x_accounting_entity_id=x_accounting_entity_id,
    )
    tenant = await get_tenant(context.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if not tenant.get("hr_addon_available"):
        raise HTTPException(status_code=403, detail="HR add-on is not provisioned for this tenant")
    if str(current_user.get("role") or "").strip() not in HR_MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Only an admin can enable HR")

    await set_hr_enabled(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=context.accounting_entity_id,
        enabled=bool(enabled), updated_by=_actor(current_user),
    )
    return {"enabled": bool(enabled)}


@router.post("/employees", response_model=EmployeeResponse)
async def hr_create_employee(
    payload: EmployeeCreateRequest,
    context: AppTenantContext = Depends(require_hr_context("employee creation", roles=HR_MANAGE_ROLES)),
    current_user: dict = Depends(get_current_user),
):
    try:
        return await create_employee(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            created_by=_actor(current_user),
            payload=payload,
        )
    except HrConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/employees", response_model=EmployeeListResponse)
async def hr_list_employees(
    status: str | None = Query(default=None, pattern="^(onboarding|active|exited)$"),
    limit: int = Query(default=100, ge=1, le=500),
    context: AppTenantContext = Depends(require_hr_context("employee listing")),
):
    return await list_employees(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        status=status,
        limit=limit,
    )


@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
async def hr_get_employee(
    employee_id: str,
    context: AppTenantContext = Depends(require_hr_context("employee lookup")),
):
    try:
        return await get_employee(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            employee_id=employee_id,
        )
    except HrNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/employees/{employee_id}", response_model=EmployeeResponse)
async def hr_update_employee(
    employee_id: str,
    payload: EmployeeUpdateRequest,
    context: AppTenantContext = Depends(require_hr_context("employee update", roles=HR_MANAGE_ROLES)),
    current_user: dict = Depends(get_current_user),
):
    try:
        return await update_employee(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            updated_by=_actor(current_user),
            employee_id=employee_id,
            payload=payload,
        )
    except HrNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── salary structures ─────────────────────────────────────────────────────────

@router.post("/salary-structures", response_model=SalaryStructureResponse)
async def hr_create_salary_structure(
    payload: SalaryStructureCreateRequest,
    context: AppTenantContext = Depends(require_hr_context("salary structure creation", roles=HR_MANAGE_ROLES)),
    current_user: dict = Depends(get_current_user),
):
    return await create_salary_structure(
        tenant_id=context.tenant_id, app_key=context.app_key,
        created_by=_actor(current_user), payload=payload,
    )


@router.get("/salary-structures", response_model=SalaryStructureListResponse)
async def hr_list_salary_structures(
    context: AppTenantContext = Depends(require_hr_context("salary structure listing")),
):
    return await list_salary_structures(tenant_id=context.tenant_id, app_key=context.app_key)


@router.get("/salary-structures/{structure_id}", response_model=SalaryStructureResponse)
async def hr_get_salary_structure(
    structure_id: str,
    context: AppTenantContext = Depends(require_hr_context("salary structure lookup")),
):
    try:
        return await get_salary_structure(
            tenant_id=context.tenant_id, app_key=context.app_key, structure_id=structure_id
        )
    except HrNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── salary assignment (one per employee) ──────────────────────────────────────

@router.put("/employees/{employee_id}/salary", response_model=SalaryAssignmentResponse)
async def hr_set_salary_assignment(
    employee_id: str,
    payload: SalaryAssignmentRequest,
    context: AppTenantContext = Depends(require_hr_context("salary assignment", roles=HR_MANAGE_ROLES)),
    current_user: dict = Depends(get_current_user),
):
    try:
        return await upsert_salary_assignment(
            tenant_id=context.tenant_id, app_key=context.app_key,
            updated_by=_actor(current_user), employee_id=employee_id, payload=payload,
        )
    except HrNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/employees/{employee_id}/salary", response_model=SalaryAssignmentResponse)
async def hr_get_salary_assignment(
    employee_id: str,
    context: AppTenantContext = Depends(require_hr_context("salary assignment lookup")),
):
    try:
        return await get_salary_assignment(
            tenant_id=context.tenant_id, app_key=context.app_key, employee_id=employee_id
        )
    except HrNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── appointment letter (config + PDF) ─────────────────────────────────────────

@router.get("/appointment-settings", response_model=AppointmentConfigResponse)
async def hr_get_appointment_settings(
    context: AppTenantContext = Depends(require_hr_context("appointment settings")),
):
    return await get_appointment_config(tenant_id=context.tenant_id, app_key=context.app_key)


@router.put("/appointment-settings", response_model=AppointmentConfigResponse)
async def hr_save_appointment_settings(
    payload: AppointmentConfig,
    context: AppTenantContext = Depends(require_hr_context("appointment settings", roles=HR_MANAGE_ROLES)),
    current_user: dict = Depends(get_current_user),
):
    return await save_appointment_config(
        tenant_id=context.tenant_id, app_key=context.app_key,
        updated_by=_actor(current_user), payload=payload,
    )


@router.get("/employees/{employee_id}/appointment-letter")
async def hr_appointment_letter_pdf(
    employee_id: str,
    context: AppTenantContext = Depends(require_hr_context("appointment letter")),
):
    from decimal import Decimal

    from app.modules.hr.payroll_engine import PayrollInput, compute_payroll
    from app.modules.hr.payroll_run import _components_from_structure

    try:
        employee = await get_employee(tenant_id=context.tenant_id, app_key=context.app_key, employee_id=employee_id)
        assignment = await get_salary_assignment(tenant_id=context.tenant_id, app_key=context.app_key, employee_id=employee_id)
    except HrNotFoundError as exc:
        # No salary assigned -> the letter has no compensation to state.
        raise HTTPException(status_code=422, detail="Assign a salary to this employee before generating the appointment letter") from exc
    try:
        structure = await get_salary_structure(
            tenant_id=context.tenant_id, app_key=context.app_key, structure_id=assignment["structure_id"]
        )
    except HrNotFoundError as exc:
        raise HTTPException(status_code=422, detail="The employee's salary structure no longer exists") from exc

    breakdown = compute_payroll(PayrollInput(
        monthly_gross=Decimal(str(assignment["monthly_gross"])),
        components=_components_from_structure(structure),
        payment_days=Decimal("30"), total_days=Decimal("30"),
        regime=assignment.get("regime", "new"),
        pf_eligible=bool(employee.get("is_pf_eligible", True)),
        esi_eligible=bool(employee.get("is_esic_eligible", False)),
        pt_state=employee.get("state_for_professional_tax"),
    ))
    config = await get_appointment_config(tenant_id=context.tenant_id, app_key=context.app_key)
    pdf = hr_documents.render_appointment_letter_pdf(
        employee=employee, monthly_gross=assignment["monthly_gross"],
        breakdown=breakdown, branding=await _branding(context), config=config,
    )
    return _pdf_response(pdf, f"appointment-letter-{employee.get('user_id') or employee_id}.pdf")


# ── payroll run ───────────────────────────────────────────────────────────────

@router.post("/payroll/run", response_model=PayrollRunResponse)
async def hr_run_payroll(
    payload: PayrollRunRequest,
    context: AppTenantContext = Depends(require_hr_context("payroll run", roles=HR_MANAGE_ROLES)),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        return await run_payroll(
            session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=context.accounting_entity_id,
            created_by=_actor(current_user),
            year=payload.year,
            month=payload.month,
            total_days=payload.total_days,
        )
    except HrConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except HrValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/payroll/runs", response_model=PayrollRunListResponse)
async def hr_list_payroll_runs(
    context: AppTenantContext = Depends(require_hr_context("payroll run listing")),
):
    return await list_payroll_runs(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=context.accounting_entity_id,
    )


@router.get("/payroll/runs/{run_id}/slips", response_model=list[SalarySlipResponse])
async def hr_list_run_slips(
    run_id: str,
    context: AppTenantContext = Depends(require_hr_context("payroll slip listing")),
):
    return await list_run_slips(tenant_id=context.tenant_id, app_key=context.app_key, run_id=run_id)


@router.get("/payroll/slips/{slip_id}/pdf")
async def hr_salary_slip_pdf(
    slip_id: str,
    context: AppTenantContext = Depends(require_hr_context("salary slip PDF")),
):
    try:
        slip = await get_slip(tenant_id=context.tenant_id, app_key=context.app_key, slip_id=slip_id)
        employee = await get_employee(
            tenant_id=context.tenant_id, app_key=context.app_key, employee_id=slip["employee_id"]
        )
    except HrNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    pdf = hr_documents.render_salary_slip_pdf(slip, employee, await _branding(context))
    return _pdf_response(pdf, f"salary-slip-{slip['period']}-{slip['employee_id']}.pdf")


# ── leave types ───────────────────────────────────────────────────────────────

@router.post("/leave-types", response_model=LeaveTypeResponse)
async def hr_create_leave_type(
    payload: LeaveTypeCreateRequest,
    context: AppTenantContext = Depends(require_hr_context("leave type creation", roles=HR_MANAGE_ROLES)),
    current_user: dict = Depends(get_current_user),
):
    try:
        return await leave_module.create_leave_type(
            tenant_id=context.tenant_id, app_key=context.app_key, created_by=_actor(current_user),
            code=payload.code, name=payload.name, is_lwp=payload.is_lwp,
        )
    except HrValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/leave-types", response_model=LeaveTypeListResponse)
async def hr_list_leave_types(
    context: AppTenantContext = Depends(require_hr_context("leave type listing")),
):
    return await leave_module.list_leave_types(tenant_id=context.tenant_id, app_key=context.app_key)


# ── leave allocation + balances ───────────────────────────────────────────────

@router.post("/employees/{employee_id}/leave-allocations")
async def hr_allocate_leave(
    employee_id: str,
    payload: LeaveAllocationRequest,
    context: AppTenantContext = Depends(require_hr_context("leave allocation", roles=HR_MANAGE_ROLES)),
    current_user: dict = Depends(get_current_user),
):
    try:
        return await leave_module.allocate_leave(
            tenant_id=context.tenant_id, app_key=context.app_key, allocated_by=_actor(current_user),
            employee_id=employee_id, leave_type_id=payload.leave_type_id, days=payload.days,
        )
    except HrNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HrValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/employees/{employee_id}/leave-balances", response_model=LeaveBalancesResponse)
async def hr_leave_balances(
    employee_id: str,
    context: AppTenantContext = Depends(require_hr_context("leave balance lookup")),
):
    return await leave_module.list_leave_balances(
        tenant_id=context.tenant_id, app_key=context.app_key, employee_id=employee_id
    )


# ── leave applications ────────────────────────────────────────────────────────

@router.post("/leave-applications", response_model=LeaveApplicationResponse)
async def hr_apply_leave(
    payload: LeaveApplicationRequest,
    context: AppTenantContext = Depends(require_hr_context("leave application", roles=HR_MANAGE_ROLES)),
    current_user: dict = Depends(get_current_user),
):
    try:
        return await leave_module.apply_leave(
            tenant_id=context.tenant_id, app_key=context.app_key, applied_by=_actor(current_user),
            employee_id=payload.employee_id, leave_type_id=payload.leave_type_id,
            from_date=payload.from_date, to_date=payload.to_date,
        )
    except HrNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HrValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/leave-applications/{application_id}/approve", response_model=LeaveApplicationResponse)
async def hr_approve_leave(
    application_id: str,
    context: AppTenantContext = Depends(require_hr_context("leave approval", roles=HR_MANAGE_ROLES)),
    current_user: dict = Depends(get_current_user),
):
    try:
        return await leave_module.approve_leave(
            tenant_id=context.tenant_id, app_key=context.app_key,
            approved_by=_actor(current_user), application_id=application_id,
        )
    except HrNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HrValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/leave-applications/{application_id}/reject", response_model=LeaveApplicationResponse)
async def hr_reject_leave(
    application_id: str,
    context: AppTenantContext = Depends(require_hr_context("leave rejection", roles=HR_MANAGE_ROLES)),
    current_user: dict = Depends(get_current_user),
):
    try:
        return await leave_module.reject_leave(
            tenant_id=context.tenant_id, app_key=context.app_key,
            rejected_by=_actor(current_user), application_id=application_id,
        )
    except HrNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HrValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/leave-applications", response_model=LeaveApplicationListResponse)
async def hr_list_leave_applications(
    employee_id: str | None = Query(default=None),
    context: AppTenantContext = Depends(require_hr_context("leave application listing")),
):
    return await leave_module.list_leave_applications(
        tenant_id=context.tenant_id, app_key=context.app_key, employee_id=employee_id
    )


# ── Form 12BB tax declarations ────────────────────────────────────────────────

@router.post("/tax-declarations", response_model=TaxDeclarationResponse)
async def hr_create_tax_declaration(
    payload: TaxDeclarationCreateRequest,
    context: AppTenantContext = Depends(require_hr_context("tax declaration", roles=HR_MANAGE_ROLES)),
    current_user: dict = Depends(get_current_user),
):
    try:
        return await tax_module.create_declaration(
            tenant_id=context.tenant_id, app_key=context.app_key, created_by=_actor(current_user),
            employee_id=payload.employee_id, financial_year=payload.financial_year,
            section_code=payload.section_code, investment_name=payload.investment_name,
            declared_amount=payload.declared_amount,
        )
    except HrNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HrValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/tax-declarations", response_model=TaxDeclarationListResponse)
async def hr_list_tax_declarations(
    employee_id: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    context: AppTenantContext = Depends(require_hr_context("tax declaration listing")),
):
    return await tax_module.list_declarations(
        tenant_id=context.tenant_id, app_key=context.app_key,
        employee_id=employee_id, financial_year=financial_year,
    )


@router.post("/tax-declarations/{declaration_id}/verify", response_model=TaxDeclarationResponse)
async def hr_verify_tax_declaration(
    declaration_id: str,
    payload: TaxVerifyRequest,
    context: AppTenantContext = Depends(require_hr_context("tax verification", roles=HR_MANAGE_ROLES)),
    current_user: dict = Depends(get_current_user),
):
    try:
        return await tax_module.verify_declaration(
            tenant_id=context.tenant_id, app_key=context.app_key, verified_by=_actor(current_user),
            declaration_id=declaration_id, verified_amount=payload.verified_amount,
            approve=payload.approve, rejection_reason=payload.rejection_reason,
        )
    except HrNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HrValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/tax-declarations/{declaration_id}/proof", response_model=TaxProofResponse)
async def hr_upload_tax_proof(
    declaration_id: str,
    file: UploadFile = File(...),
    context: AppTenantContext = Depends(require_hr_context("tax proof upload", roles=HR_MANAGE_ROLES)),
    current_user: dict = Depends(get_current_user),
):
    # Chunked read so an oversized upload is rejected without buffering it whole.
    data = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > tax_module.MAX_PROOF_BYTES:
            raise HTTPException(status_code=413, detail="Proof file exceeds the 10 MB limit")
    try:
        return await tax_module.add_proof(
            tenant_id=context.tenant_id, app_key=context.app_key, uploaded_by=_actor(current_user),
            declaration_id=declaration_id, file_name=file.filename or "proof",
            content_type=(file.content_type or "").lower(), payload=bytes(data),
        )
    except HrNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HrValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/tax-proofs/{proof_id}/download")
async def hr_download_tax_proof(
    proof_id: str,
    context: AppTenantContext = Depends(require_hr_context("tax proof download")),
):
    try:
        proof = await tax_module.get_proof(
            tenant_id=context.tenant_id, app_key=context.app_key, proof_id=proof_id
        )
    except HrNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    safe_name = re.sub(r"[\x00-\x1f\x7f]", "", proof.get("file_name") or "proof")
    encoded = quote(safe_name)
    return Response(
        content=bytes(proof["payload"]),
        media_type=proof.get("content_type") or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


@router.get("/employees/{employee_id}/effective-deductions", response_model=EffectiveDeductionsResponse)
async def hr_effective_deductions(
    employee_id: str,
    financial_year: str = Query(..., min_length=4, max_length=9),
    context: AppTenantContext = Depends(require_hr_context("effective deductions")),
):
    return await tax_module.compute_effective_deductions(
        tenant_id=context.tenant_id, app_key=context.app_key,
        employee_id=employee_id, financial_year=financial_year,
    )


# ── Full & Final settlement ───────────────────────────────────────────────────

@router.post("/fnf", response_model=FnfResponse)
async def hr_create_fnf(
    payload: FnfCreateRequest,
    context: AppTenantContext = Depends(require_hr_context("F&F settlement", roles=HR_MANAGE_ROLES)),
    current_user: dict = Depends(get_current_user),
):
    try:
        return await fnf_module.create_fnf(
            tenant_id=context.tenant_id, app_key=context.app_key, created_by=_actor(current_user),
            employee_id=payload.employee_id, last_working_day=payload.last_working_day,
            last_drawn_basic=payload.last_drawn_basic, unutilized_leaves=payload.unutilized_leaves,
            unpaid_notice_days=payload.unpaid_notice_days, other_payouts=payload.other_payouts,
            other_recoveries=payload.other_recoveries,
        )
    except HrNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HrValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/fnf", response_model=FnfListResponse)
async def hr_list_fnf(
    employee_id: str | None = Query(default=None),
    context: AppTenantContext = Depends(require_hr_context("F&F listing")),
):
    return await fnf_module.list_fnf(
        tenant_id=context.tenant_id, app_key=context.app_key, employee_id=employee_id
    )


@router.get("/fnf/{fnf_id}", response_model=FnfResponse)
async def hr_get_fnf(
    fnf_id: str,
    context: AppTenantContext = Depends(require_hr_context("F&F lookup")),
):
    try:
        return await fnf_module.get_fnf(tenant_id=context.tenant_id, app_key=context.app_key, fnf_id=fnf_id)
    except HrNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/fnf/{fnf_id}/pdf")
async def hr_fnf_pdf(
    fnf_id: str,
    context: AppTenantContext = Depends(require_hr_context("F&F PDF")),
):
    try:
        settlement = await fnf_module.get_fnf(tenant_id=context.tenant_id, app_key=context.app_key, fnf_id=fnf_id)
        employee = await get_employee(
            tenant_id=context.tenant_id, app_key=context.app_key, employee_id=settlement["employee_id"]
        )
    except HrNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    pdf = hr_documents.render_fnf_pdf(settlement, employee, await _branding(context))
    return _pdf_response(pdf, f"fnf-{settlement['employee_id']}.pdf")


@router.post("/fnf/{fnf_id}/approve", response_model=FnfResponse)
async def hr_approve_fnf(
    fnf_id: str,
    context: AppTenantContext = Depends(require_hr_context("F&F approval", roles=HR_MANAGE_ROLES)),
    current_user: dict = Depends(get_current_user),
):
    try:
        return await fnf_module.transition_fnf(
            tenant_id=context.tenant_id, app_key=context.app_key,
            actor=_actor(current_user), fnf_id=fnf_id, target="approved",
        )
    except HrNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HrValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/fnf/{fnf_id}/pay", response_model=FnfResponse)
async def hr_pay_fnf(
    fnf_id: str,
    context: AppTenantContext = Depends(require_hr_context("F&F payment", roles=HR_MANAGE_ROLES)),
    current_user: dict = Depends(get_current_user),
):
    try:
        return await fnf_module.transition_fnf(
            tenant_id=context.tenant_id, app_key=context.app_key,
            actor=_actor(current_user), fnf_id=fnf_id, target="paid",
        )
    except HrNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HrValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ── analytics dashboard ───────────────────────────────────────────────────────

@router.get("/analytics/dashboard")
async def hr_analytics_dashboard(
    months: int = Query(default=6, ge=1, le=24),
    context: AppTenantContext = Depends(require_hr_context("analytics dashboard")),
):
    return await analytics_module.compile_dashboard(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=context.accounting_entity_id, months=months,
    )
