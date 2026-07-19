"""Dashboard, analytics, and report-export routes.

Registered on the shared ``router`` from ``app.modules.business.router``.
Moved verbatim per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md; paths and
handler behaviour are unchanged. The report-building helpers _resolve_org_name
and _build_business_report moved here with the handlers.
"""
from datetime import date
from decimal import Decimal

from fastapi import Depends, Header, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import (
    AccountingNotFoundError,
    AccountingValidationError,
    _financial_year_start,
    get_balance_sheet,
    get_business_dashboard,
    get_ledger_lines,
    get_profit_loss,
    get_trial_balance,
)
from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.tenants.service import get_tenant
from app.db.postgres import get_async_session
from app.modules.business import allocation_service
from app.modules.business import data_health as data_health_module
from app.modules.business import export_governance
from app.modules.business import financial_health
from app.modules.business import mis as mis_module
from app.modules.business import report_export
from app.modules.business import statements
from app.modules.business import tally_xml
from app.modules.business.service import (
    get_invoice_settings,
    party_wise_ledger,
    preview_itc_reversals,
)
from app.modules.business.router import _alloc_context, router


@router.get("/dashboard")
async def business_dashboard(
    as_of: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Live executive dashboard (KPIs, balances, 6-month trend) from the ledger."""
    context = _alloc_context(current_user, x_tenant_id, x_app_key, "dashboard")
    return await get_business_dashboard(
        session, tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id, as_of=as_of,
    )


@router.get("/financial-health")
async def business_financial_health(
    as_of: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    narrate: bool = Query(default=True),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """CFO-Insight Financial Health: ledger-backed KPIs, charts and alerts, plus an
    optional AI narrative.

    Every figure is computed deterministically from the posted ledger (see
    ``financial_health.assemble_financial_health``); the response is a fixed
    chart-spec vocabulary the frontend renders directly. The AI narrative only
    rewrites those figures into prose and never invents numbers."""
    context = _alloc_context(current_user, x_tenant_id, x_app_key, "financial health")
    try:
        return await financial_health.build_financial_health(
            session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, as_of=as_of, narrate=narrate,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/mis/kpis")
async def business_mis_kpis(
    as_of: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Source-backed MIS KPI contract for trends, top parties and overdue views."""
    context = _alloc_context(current_user, x_tenant_id, x_app_key, "MIS KPI contracts")
    try:
        return await mis_module.build_mis_kpis(
            session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, as_of=as_of,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/data-health")
async def business_data_health(
    as_of: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Read-only Data Health Score for tenant-scoped MitraBooks records."""
    context = _alloc_context(current_user, x_tenant_id, x_app_key, "data health")
    return await data_health_module.build_data_health_score(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id, as_of=as_of,
    )


# ===================== Report export (CSV / XLSX / PDF) =====================


async def _resolve_org_name(tenant_id: str, app_key: str, accounting_entity_id: str) -> str | None:
    """Company name for report headers: invoice-settings business name, else the
    tenant's display name."""
    try:
        settings = await get_invoice_settings(
            tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        )
        name = ((settings or {}).get("branding") or {}).get("business_name")
        if name and str(name).strip():
            return str(name).strip()
    except Exception:
        pass
    try:
        tenant = await get_tenant(tenant_id)
        name = (tenant or {}).get("display_name")
        if name and str(name).strip():
            return str(name).strip()
    except Exception:
        pass
    return None


async def _build_business_report(
    report: str, *, session, tenant_id, app_key, accounting_entity_id, kind, as_of,
    account_id=None, from_date=None, to_date=None, party_id=None,
) -> dict:
    """Assemble (title, columns, rows, footer, meta, org_name, filename_base) for a report."""
    as_of_str = (as_of or date.today()).isoformat()
    org_name = await _resolve_org_name(tenant_id, app_key, accounting_entity_id)

    if report == "party_ledger":
        data = await party_wise_ledger(
            session, tenant_id=tenant_id, app_key=app_key,
            accounting_entity_id=accounting_entity_id, kind=kind, as_of=as_of,
        )
        title = "Sundry Debtors" if kind == "receivable" else "Sundry Creditors"
        spec = {
            "title": title,
            "columns": [{"key": "party_name", "label": "Party"},
                        {"key": "balance", "label": "Balance", "numeric": True}],
            "rows": data["items"],
            "footer": {"party_name": "Total", "balance": data.get("total_balance")},
            "meta": [("As of", as_of_str), ("Type", kind)],
            "filename_base": f"{'debtors' if kind == 'receivable' else 'creditors'}_{as_of_str}",
        }

    elif report == "aging":
        data = await allocation_service.ar_ap_aging(
            tenant_id=tenant_id, app_key=app_key,
            accounting_entity_id=accounting_entity_id, kind=kind, as_of=as_of,
        )
        order = data["buckets_order"]
        columns = [{"key": "party_name", "label": "Party"}]
        columns += [{"key": b, "label": b, "numeric": True} for b in order]
        columns += [{"key": "total", "label": "Total", "numeric": True}]
        rows = [{"party_name": r.get("party_name") or "Unallocated",
                 **r["buckets"], "total": r["total"]} for r in data["by_party"]]
        footer = {"party_name": "Total", **data["totals"], "total": data["grand_total"]}
        title = "Receivables Aging" if kind == "receivable" else "Payables Aging"
        spec = {
            "title": title, "columns": columns, "rows": rows, "footer": footer,
            "meta": [("As of", as_of_str), ("Type", kind)],
            "filename_base": f"aging_{kind}_{as_of_str}",
        }

    elif report == "itc_reversals":
        data = await preview_itc_reversals(
            tenant_id=tenant_id, app_key=app_key,
            accounting_entity_id=accounting_entity_id, as_of=as_of,
        )
        data = data if isinstance(data, dict) else data.model_dump()
        spec = {
            "title": "ITC Reversals (GST Rule 37)",
            "columns": [
                {"key": "bill_number", "label": "Bill No."},
                {"key": "vendor_name", "label": "Vendor"},
                {"key": "bill_date", "label": "Bill Date"},
                {"key": "days_overdue", "label": "Days Overdue", "numeric": True},
                {"key": "itc_total", "label": "ITC Total", "numeric": True},
                {"key": "interest_amount", "label": "Interest", "numeric": True},
            ],
            "rows": data.get("candidates", []),
            "footer": {"bill_number": "Total", "itc_total": data.get("total_itc"),
                       "interest_amount": data.get("total_interest")},
            "meta": [("As of", as_of_str)],
            "filename_base": f"itc_reversals_{as_of_str}",
        }

    elif report == "balance_sheet":
        assets, liabilities, equity, total_assets, total_liabilities, total_equity = await get_balance_sheet(
            session, tenant_id=tenant_id, as_of=(as_of or date.today()),
            app_key=app_key, accounting_entity_id=accounting_entity_id,
        )

        def _bs_section(section_label, items, subtotal_label, subtotal_value):
            section_rows = [{
                "section": section_label,
                "account_code": item.get("account_code"),
                "account_name": item.get("account_name"),
                "amount": item.get("balance"),
            } for item in items]
            section_rows.append({
                "section": "", "account_code": "", "account_name": subtotal_label, "amount": subtotal_value,
            })
            return section_rows

        rows = (
            _bs_section("Assets", assets, "Total Assets", total_assets)
            + _bs_section("Liabilities", liabilities, "Total Liabilities", total_liabilities)
            + _bs_section("Equity", equity, "Total Equity", total_equity)
        )
        spec = {
            "title": "Balance Sheet",
            "columns": [
                {"key": "section", "label": "Section"},
                {"key": "account_code", "label": "Code"},
                {"key": "account_name", "label": "Account"},
                {"key": "amount", "label": "Amount", "numeric": True},
            ],
            "rows": rows,
            "footer": {"account_name": "Total Liabilities + Equity",
                       "amount": total_liabilities + total_equity},
            "meta": [("As of", as_of_str)],
            "filename_base": f"balance_sheet_{as_of_str}",
        }

    elif report == "profit_loss":
        pnl_from = from_date or _financial_year_start(as_of or date.today())
        pnl_to = to_date or as_of or date.today()
        lines, income_total, expense_total, net_profit = await get_profit_loss(
            session, tenant_id=tenant_id, from_date=pnl_from, to_date=pnl_to,
            app_key=app_key, accounting_entity_id=accounting_entity_id,
        )
        income_lines = [l for l in lines if l.get("account_type") == "income"]
        expense_lines = [l for l in lines if l.get("account_type") == "expense"]

        def _pnl_section(section_label, items, subtotal_label, subtotal_value):
            section_rows = [{
                "section": section_label,
                "account_code": item.get("account_code"),
                "account_name": item.get("account_name"),
                "amount": item.get("net_amount"),
            } for item in items]
            section_rows.append({
                "section": "", "account_code": "", "account_name": subtotal_label, "amount": subtotal_value,
            })
            return section_rows

        rows = (
            _pnl_section("Income", income_lines, "Total Income", income_total)
            + _pnl_section("Expenses", expense_lines, "Total Expenses", expense_total)
        )
        spec = {
            "title": "Profit and Loss",
            "columns": [
                {"key": "section", "label": "Section"},
                {"key": "account_code", "label": "Code"},
                {"key": "account_name", "label": "Account"},
                {"key": "amount", "label": "Amount", "numeric": True},
            ],
            "rows": rows,
            "footer": {"account_name": "Net Profit", "amount": net_profit},
            "meta": [("From", pnl_from.isoformat()), ("To", pnl_to.isoformat())],
            "filename_base": f"profit_loss_{pnl_from.isoformat()}_{pnl_to.isoformat()}",
        }

    elif report == "trial_balance":
        lines, _total_debit, _total_credit = await get_trial_balance(
            session, tenant_id=tenant_id, as_of=(as_of or date.today()),
            app_key=app_key, accounting_entity_id=accounting_entity_id,
        )
        # Match the on-screen Trial Balance: show each account's NET in its natural
        # column (Dr if positive, Cr if negative) — not raw debit + credit + net.
        rows = []
        net_debit_total = Decimal("0.00")
        net_credit_total = Decimal("0.00")
        for line in lines:
            net = line.get("net_balance")
            net = Decimal(str(net if net is not None
                             else Decimal(str(line.get("debit_total") or 0)) - Decimal(str(line.get("credit_total") or 0))))
            debit_cell = net if net > 0 else None
            credit_cell = -net if net < 0 else None
            if debit_cell:
                net_debit_total += debit_cell
            if credit_cell:
                net_credit_total += credit_cell
            rows.append({
                "account_code": line.get("account_code"),
                "account_name": line.get("account_name"),
                "debit": debit_cell,
                "credit": credit_cell,
            })
        spec = {
            "title": "Trial Balance",
            "columns": [
                {"key": "account_code", "label": "Code"},
                {"key": "account_name", "label": "Account"},
                {"key": "debit", "label": "Debit", "numeric": True},
                {"key": "credit", "label": "Credit", "numeric": True},
            ],
            "rows": rows,
            "footer": {"account_name": "Total", "debit": net_debit_total, "credit": net_credit_total},
            "meta": [("As of", as_of_str)],
            "filename_base": f"trial_balance_{as_of_str}",
        }

    elif report == "general_ledger":
        if not account_id:
            raise AccountingValidationError("account_id is required for the general ledger export")
        account, lines = await get_ledger_lines(
            session, tenant_id=tenant_id, account_id=int(account_id),
            app_key=app_key, accounting_entity_id=accounting_entity_id,
        )
        total_debit = sum((Decimal(str(l["debit"] or 0)) for l in lines), Decimal("0.00"))
        total_credit = sum((Decimal(str(l["credit"] or 0)) for l in lines), Decimal("0.00"))
        closing = lines[-1]["running_balance"] if lines else Decimal("0.00")
        rows = [{
            "entry_date": l["entry_date"],
            "description": l["description"],
            "reference": l["reference"],
            "debit": l["debit"] or None,
            "credit": l["credit"] or None,
            "running_balance": l["running_balance"],
        } for l in lines]
        spec = {
            "title": "General Ledger",
            "columns": [
                {"key": "entry_date", "label": "Date"},
                {"key": "description", "label": "Particulars"},
                {"key": "reference", "label": "Reference"},
                {"key": "debit", "label": "Debit", "numeric": True},
                {"key": "credit", "label": "Credit", "numeric": True},
                {"key": "running_balance", "label": "Balance", "numeric": True},
            ],
            "rows": rows,
            "footer": {"description": "Total", "debit": total_debit, "credit": total_credit, "running_balance": closing},
            "meta": [("Account", f"{account.code} - {account.name}"), ("As of", as_of_str)],
            "filename_base": f"general_ledger_{account.code}_{as_of_str}",
        }

    elif report == "statement":
        if not party_id:
            raise AccountingValidationError("party_id is required for the statement export")
        data = await statements.build_party_statement(
            session, tenant_id=tenant_id, app_key=app_key,
            accounting_entity_id=accounting_entity_id, party_id=party_id,
            kind=kind, from_date=from_date, to_date=to_date or as_of,
        )
        rows = [{
            "entry_date": r["entry_date"], "document_type": r["document_type"],
            "reference": r["reference"], "description": r["description"],
            "debit": r["debit"] if Decimal(str(r["debit"] or 0)) else None,
            "credit": r["credit"] if Decimal(str(r["credit"] or 0)) else None,
            "balance": r["balance"],
        } for r in data["transactions"]]
        rows.insert(0, {"entry_date": data["from_date"], "document_type": "",
                        "reference": "", "description": "Opening balance",
                        "debit": None, "credit": None, "balance": data["opening_balance"]})
        spec = {
            "title": f"Statement of Account — {data['party']['party_name']}",
            "columns": [
                {"key": "entry_date", "label": "Date"},
                {"key": "document_type", "label": "Document"},
                {"key": "reference", "label": "Reference"},
                {"key": "description", "label": "Particulars"},
                {"key": "debit", "label": "Debit", "numeric": True},
                {"key": "credit", "label": "Credit", "numeric": True},
                {"key": "balance", "label": "Balance", "numeric": True},
            ],
            "rows": rows,
            "footer": {"description": "Closing balance", "debit": data["total_debit"],
                       "credit": data["total_credit"], "balance": data["closing_balance"]},
            "meta": [("Party", data["party"]["party_name"]), ("Type", kind),
                     ("From", data["from_date"]), ("To", data["to_date"])],
            "filename_base": f"statement_{party_id}_{data['to_date']}",
        }

    else:
        raise AccountingValidationError(
            "report must be one of: party_ledger, aging, itc_reversals, trial_balance, general_ledger, statement"
        )

    spec["org_name"] = org_name
    return spec


@router.get("/reports/export")
async def export_business_report(
    report: str = Query(..., pattern="^(party_ledger|aging|itc_reversals|trial_balance|general_ledger|balance_sheet|profit_loss|statement)$"),
    format: str = Query("csv", pattern="^(csv|xlsx|pdf|json)$"),
    kind: str = Query(default="receivable", pattern="^(receivable|payable)$"),
    as_of: date | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    account_id: int | None = Query(default=None),
    party_id: str | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = _alloc_context(current_user, x_tenant_id, x_app_key, "report export")
    export_format = export_governance.validate_export_format(format, allowed={"csv", "xlsx", "pdf", "json"})
    export_governance.require_export_permission(current_user, export_type="business_report")
    try:
        spec = await _build_business_report(
            report, session=session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, kind=kind, as_of=as_of, account_id=account_id,
            from_date=from_date, to_date=to_date, party_id=party_id,
        )
        response = report_export.export_report(export_format, **spec)
        return await export_governance.govern_export_response(
            response,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            current_user=current_user,
            export_type="business_report",
            export_format=export_format,
            report_key=report,
            filters={
                "kind": kind,
                "as_of": as_of.isoformat() if as_of else None,
                "from_date": from_date.isoformat() if from_date else None,
                "to_date": to_date.isoformat() if to_date else None,
                "account_id": account_id,
                "party_id": party_id,
            },
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/tally/xml-export")
async def export_business_tally_xml(
    as_of: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Proof-of-concept Tally XML export for posted trial-balance ledger masters."""
    context = _alloc_context(current_user, x_tenant_id, x_app_key, "Tally XML export")
    export_governance.require_export_permission(current_user, export_type="tally_xml")
    try:
        spec = await _build_business_report(
            "trial_balance", session=session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, kind="receivable", as_of=as_of,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    as_of_str = (as_of or date.today()).isoformat()
    xml_bytes = tally_xml.build_trial_balance_tally_xml(spec=spec, company_name=spec.get("org_name"), as_of=as_of_str)
    response = Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="tally_trial_balance_{as_of_str}.xml"'},
    )
    return await export_governance.govern_export_response(
        response,
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        current_user=current_user,
        export_type="tally_xml",
        export_format="xml",
        report_key="trial_balance",
        filters={"as_of": as_of_str},
    )
