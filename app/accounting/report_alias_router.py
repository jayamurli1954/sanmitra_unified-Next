from datetime import date
from decimal import Decimal
from io import BytesIO
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.context import AccountingContext, resolve_accounting_context
from app.accounting.models import Account
from app.accounting.router import (
    balance_sheet_endpoint,
    enforce_accounting_route_tenant,
    income_expenditure_endpoint,
    receipts_payments_endpoint,
    trial_balance_endpoint,
)
from app.accounting.service import AccountingNotFoundError, get_ledger_lines
from app.core.auth.dependencies import get_current_user
from app.core.tenants.context import resolve_app_key, resolve_tenant_id
from app.db.mongo import get_collection
from app.db.postgres import get_async_session
from app.modules.housing_compat.pdf_branding import (
    draw_society_pdf_header,
    get_housing_society_branding,
    society_contact_line,
)

router = APIRouter(prefix="/reports", tags=["accounting-report-compat"])


def _money_float(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01")))


def _safe_money(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0")).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0.00")


def _bill_is_reversed(row: dict[str, Any]) -> bool:
    return str(row.get("status") or "").strip().lower() == "reversed" or bool(row.get("is_reversed"))


def _bill_paid_amount(row: dict[str, Any]) -> Decimal:
    status = str(row.get("payment_status") or row.get("status") or "").strip().lower()
    if status in {"paid", "collected", "settled"}:
        return _safe_money(row.get("amount"))
    return _safe_money(row.get("paid_amount") or row.get("amount_paid") or row.get("collected_amount"))


def _as_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except Exception:
        return None


def _bill_date(row: dict[str, Any]) -> date | None:
    return _as_date(row.get("bill_date") or row.get("created_at") or row.get("updated_at"))


def _active_member_name(row: dict[str, Any]) -> str:
    return str(row.get("owner_name") or row.get("member_name") or row.get("name") or "").strip()


def _flat_key(value: Any) -> str:
    return str(value or "").strip().upper()


def _name_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in text)
    words = [word for word in cleaned.split() if word not in {"mr", "mrs", "ms", "miss", "shri", "smt", "dr"}]
    return " ".join(words)


def _find_flat_by_member_name(name: Any, member_name_to_flat: dict[str, str]) -> str:
    key = _name_key(name)
    if not key:
        return ""
    if key in member_name_to_flat:
        return member_name_to_flat[key]
    for member_key, flat_number in member_name_to_flat.items():
        if key and member_key and (key in member_key or member_key in key):
            return flat_number
    return ""


def _transaction_posts_to_member_dues(txn: dict[str, Any]) -> bool:
    if str(txn.get("voucher_type") or "").strip().lower() != "receipt":
        return False
    if str(txn.get("status") or "").strip().lower() != "posted":
        return False
    if str(txn.get("account_code") or txn.get("accountCode") or "").strip() == "1100":
        return True
    for line in txn.get("lines") or []:
        if (
            str(line.get("account_code") or line.get("accountCode") or "").strip() == "1100"
            and _safe_money(line.get("credit") or line.get("credit_amount") or line.get("creditAmount")) > Decimal("0.00")
        ):
            return True
    return False


async def _member_due_receipt_allocations(
    *,
    tenant_id: str,
    app_key: str,
    member_by_flat: dict[str, dict[str, Any]],
    to_date: date | None = None,
) -> dict[str, dict[str, Any]]:
    flats = await get_collection("housing_flats").find(
        {"tenant_id": tenant_id, "app_key": app_key}
    ).to_list(length=5000)
    flat_by_id = {
        str(flat.get("id") or flat.get("_id") or "").strip(): _flat_key(flat.get("flat_number"))
        for flat in flats
        if _flat_key(flat.get("flat_number"))
    }
    flat_by_number = {_flat_key(flat.get("flat_number")): _flat_key(flat.get("flat_number")) for flat in flats}
    member_name_to_flat = {
        _name_key(_active_member_name(member)): flat_number
        for flat_number, member in member_by_flat.items()
        if _name_key(_active_member_name(member))
    }

    txns = await get_collection("mb_transactions").find(
        {"tenant_id": tenant_id, "app_key": app_key, "status": "posted"}
    ).to_list(length=5000)

    allocations: dict[str, dict[str, Any]] = {}
    for txn in txns:
        if not _transaction_posts_to_member_dues(txn):
            continue
        txn_date = _as_date(txn.get("voucher_date") or txn.get("date") or txn.get("created_at"))
        if to_date and txn_date and txn_date > to_date:
            continue

        flat_number = ""
        raw_flat = str(
            txn.get("flat_number")
            or txn.get("flatNumber")
            or txn.get("unit_number")
            or txn.get("unitNumber")
            or ""
        ).strip()
        if raw_flat:
            flat_number = flat_by_number.get(_flat_key(raw_flat), _flat_key(raw_flat))
        if not flat_number:
            flat_id = str(txn.get("flat_id") or txn.get("flatId") or "").strip()
            flat_number = flat_by_id.get(flat_id) or flat_by_number.get(_flat_key(flat_id), "")
        if not flat_number:
            flat_number = _find_flat_by_member_name(txn.get("received_from") or txn.get("receivedFrom"), member_name_to_flat)
        if not flat_number:
            continue

        amount = _safe_money(txn.get("amount") or txn.get("total_credit") or txn.get("totalCredit"))
        if amount <= Decimal("0.00"):
            continue
        current = allocations.setdefault(flat_number, {"amount": Decimal("0.00"), "last_payment_date": None})
        current["amount"] += amount
        if txn_date:
            current_last = _as_date(current.get("last_payment_date"))
            if current_last is None or txn_date > current_last:
                current["last_payment_date"] = txn_date.isoformat()
    return allocations


async def _member_dues_payload(
    *,
    tenant_id: str,
    app_key: str,
    from_date: date | None = None,
    to_date: date | None = None,
) -> dict[str, Any]:
    bills = await get_collection("housing_maintenance_bills").find(
        {"tenant_id": tenant_id, "app_key": app_key}
    ).to_list(length=5000)
    members = await get_collection("housing_members").find(
        {"tenant_id": tenant_id, "app_key": app_key}
    ).to_list(length=5000)

    member_by_flat: dict[str, dict[str, Any]] = {}
    for member in members:
        status = str(member.get("status") or "active").strip().lower()
        if status in {"moved_out", "inactive", "closed", "rejected"}:
            continue
        flat_number = str(member.get("flat_number") or "").strip().upper()
        if not flat_number:
            continue
        current = member_by_flat.get(flat_number)
        if current is None or bool(member.get("is_primary")):
            member_by_flat[flat_number] = member

    receipt_allocations = await _member_due_receipt_allocations(
        tenant_id=tenant_id,
        app_key=app_key,
        member_by_flat=member_by_flat,
        to_date=to_date,
    )

    grouped: dict[str, dict[str, Any]] = {}
    for bill in bills:
        if _bill_is_reversed(bill):
            continue
        bill_date = _bill_date(bill)
        if to_date and bill_date and bill_date > to_date:
            continue
        if from_date and bill_date and bill_date < from_date:
            continue
        flat_number = str(bill.get("flat_number") or "").strip().upper()
        if not flat_number:
            continue

        amount = _safe_money(bill.get("amount"))
        paid = min(_bill_paid_amount(bill), amount)

        member = member_by_flat.get(flat_number, {})
        row = grouped.setdefault(
            flat_number,
            {
                "flat_number": flat_number,
                "member_name": _active_member_name(member),
                "owner_name": _active_member_name(member),
                "outstanding_amount": Decimal("0.00"),
                "total_billed": Decimal("0.00"),
                "total_paid": Decimal("0.00"),
                "_bill_paid_total": Decimal("0.00"),
                "bill_count": 0,
                "last_payment_date": None,
            },
        )
        row["total_billed"] += amount
        row["_bill_paid_total"] += paid
        row["bill_count"] += 1
        last_payment_date = _as_date(bill.get("last_payment_date") or bill.get("paid_at") or bill.get("payment_date"))
        if last_payment_date:
            current_last = _as_date(row.get("last_payment_date"))
            if current_last is None or last_payment_date > current_last:
                row["last_payment_date"] = last_payment_date.isoformat()

    rows = []
    for flat_number, row in grouped.items():
        receipt = receipt_allocations.get(flat_number, {})
        receipt_paid = _safe_money(receipt.get("amount"))
        paid = min(max(row.pop("_bill_paid_total", Decimal("0.00")), receipt_paid), row["total_billed"])
        row["total_paid"] = paid
        row["outstanding_amount"] = max(row["total_billed"] - paid, Decimal("0.00"))
        receipt_last = _as_date(receipt.get("last_payment_date"))
        if receipt_last:
            current_last = _as_date(row.get("last_payment_date"))
            if current_last is None or receipt_last > current_last:
                row["last_payment_date"] = receipt_last.isoformat()
        if row["outstanding_amount"] > Decimal("0.00"):
            rows.append(row)

    rows = sorted(rows, key=lambda item: str(item.get("flat_number") or ""))
    total_outstanding = sum((row["outstanding_amount"] for row in rows), Decimal("0.00"))
    for row in rows:
        row["outstanding_amount"] = _money_float(row["outstanding_amount"])
        row["outstanding"] = row["outstanding_amount"]
        row["total_billed"] = _money_float(row["total_billed"])
        row["total_paid"] = _money_float(row["total_paid"])

    return {
        "report_type": "member_dues",
        "from_date": from_date.isoformat() if from_date else None,
        "to_date": to_date.isoformat() if to_date else None,
        "members": rows,
        "total_outstanding": _money_float(total_outstanding),
    }


def _ledger_report_payload(account: Account, raw_lines: list[dict], *, from_date: date, to_date: date) -> dict:
    opening = Decimal("0")
    entries: list[dict] = []
    running = Decimal("0")
    total_debit = Decimal("0")
    total_credit = Decimal("0")

    for line in raw_lines:
        entry_date = date.fromisoformat(str(line.get("entry_date"))[:10])
        debit = Decimal(line.get("debit") or 0)
        credit = Decimal(line.get("credit") or 0)
        if entry_date < from_date:
            opening += debit - credit

    running = opening
    for line in raw_lines:
        entry_date = date.fromisoformat(str(line.get("entry_date"))[:10])
        if entry_date < from_date or entry_date > to_date:
            continue
        debit = Decimal(line.get("debit") or 0)
        credit = Decimal(line.get("credit") or 0)
        running += debit - credit
        total_debit += debit
        total_credit += credit
        entries.append(
            {
                "journal_entry_id": line.get("journal_id"),
                "date": entry_date.isoformat(),
                "description": line.get("description") or "",
                "reference": line.get("reference"),
                "debit": _money_float(debit),
                "credit": _money_float(credit),
                "balance": _money_float(running),
                "has_attachment": False,
            }
        )

    return {
        "account_code": account.code,
        "account_name": account.name,
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "opening_balance": _money_float(opening),
        "closing_balance": _money_float(running),
        "total_debit": _money_float(total_debit),
        "total_credit": _money_float(total_credit),
        "entries": entries,
    }


def _pdf_text(value) -> str:
    return str(value or "").encode("latin-1", "replace").decode("latin-1")


def _footer_text(branding: dict | None) -> str:
    society_name = str((branding or {}).get("society_name") or "GruhaMitra Society").strip()
    return f"Generated by {society_name} / MitraBooks accounting"


def _ledger_pdf_bytes(report: dict, *, branding: dict | None = None) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    left = 42
    right = width - 42
    y = draw_society_pdf_header(pdf, title="General Ledger Statement", branding=branding, margin_x=left)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(left, y, _pdf_text(f"Period: {report.get('from_date')} to {report.get('to_date')}"))
    y -= 24

    ledgers = report.get("ledgers") or [report]
    for ledger in ledgers:
        if y < 160:
            pdf.showPage()
            y = draw_society_pdf_header(pdf, title="General Ledger Statement", branding=branding, margin_x=left)
            pdf.setFont("Helvetica", 9)
            pdf.drawString(left, y, _pdf_text(f"Period: {report.get('from_date')} to {report.get('to_date')}"))
            y -= 24

        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(left, y, _pdf_text(f"{ledger.get('account_code')} - {ledger.get('account_name')}")[:90])
        y -= 15
        pdf.setFont("Helvetica", 8)
        pdf.drawString(
            left,
            y,
            _pdf_text(
                f"Opening: {ledger.get('opening_balance'):,.2f}   "
                f"Debit: {ledger.get('total_debit'):,.2f}   "
                f"Credit: {ledger.get('total_credit'):,.2f}   "
                f"Closing: {ledger.get('closing_balance'):,.2f}"
            ),
        )
        y -= 14
        pdf.line(left, y, right, y)
        y -= 11
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(left, y, "Date")
        pdf.drawString(left + 70, y, "Description")
        pdf.drawString(right - 210, y, "Reference")
        pdf.drawRightString(right - 90, y, "Debit")
        pdf.drawRightString(right - 35, y, "Credit")
        pdf.drawRightString(right, y, "Balance")
        y -= 8
        pdf.line(left, y, right, y)
        y -= 11
        pdf.setFont("Helvetica", 7)

        for entry in ledger.get("entries") or []:
            if y < 70:
                pdf.showPage()
                y = draw_society_pdf_header(pdf, title="General Ledger Statement", branding=branding, margin_x=left)
                pdf.setFont("Helvetica", 7)
            pdf.drawString(left, y, _pdf_text(entry.get("date"))[:10])
            pdf.drawString(left + 70, y, _pdf_text(entry.get("description"))[:58])
            pdf.drawString(right - 210, y, _pdf_text(entry.get("reference"))[:24])
            pdf.drawRightString(right - 90, y, f"{entry.get('debit') or 0:,.2f}" if entry.get("debit") else "-")
            pdf.drawRightString(right - 35, y, f"{entry.get('credit') or 0:,.2f}" if entry.get("credit") else "-")
            pdf.drawRightString(right, y, f"{entry.get('balance') or 0:,.2f}")
            y -= 11
        y -= 18

    pdf.setFont("Helvetica", 8)
    pdf.drawString(left, 34, _pdf_text(_footer_text(branding))[:110])
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()


def _plain_value(value) -> str:
    if isinstance(value, Decimal):
        return f"{value.quantize(Decimal('0.01'))}"
    if isinstance(value, date):
        return value.isoformat()
    return "" if value is None else str(value)


def _model_to_dict(report) -> dict:
    if hasattr(report, "model_dump"):
        return report.model_dump()
    if hasattr(report, "dict"):
        return report.dict()
    return dict(report)


def _report_lines(report: dict) -> list[dict]:
    if "lines" in report:
        return list(report.get("lines") or [])
    rows: list[dict] = []
    for section in ("assets", "liabilities", "equity"):
        for line in report.get(section) or []:
            row = dict(line)
            row["section"] = section.title()
            rows.append(row)
    return rows


def _report_pdf_bytes(title: str, report, *, branding: dict | None = None) -> bytes:
    data = _model_to_dict(report)
    rows = _report_lines(data)
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    left = 42
    right = width - 42
    y = draw_society_pdf_header(pdf, title=title, branding=branding, margin_x=left)
    pdf.setFont("Helvetica", 9)
    period = data.get("as_of") or f"{data.get('from_date')} to {data.get('to_date')}"
    pdf.drawString(left, y, _pdf_text(f"Period: {period}"))
    y -= 24

    pdf.setFont("Helvetica-Bold", 8)
    headers = ["Code", "Account", "Debit", "Credit", "Balance"]
    x_positions = [left, left + 80, right - 185, right - 105, right - 25]
    for header, x in zip(headers, x_positions):
        pdf.drawString(x, y, header)
    y -= 8
    pdf.line(left, y, right, y)
    y -= 13
    pdf.setFont("Helvetica", 8)

    for row in rows:
        if y < 65:
            pdf.showPage()
            y = draw_society_pdf_header(pdf, title=title, branding=branding, margin_x=left)
            pdf.setFont("Helvetica", 8)
        debit = row.get("debit_total") or row.get("debit") or row.get("receipts") or ""
        credit = row.get("credit_total") or row.get("credit") or row.get("payments") or ""
        balance = row.get("net_balance") or row.get("net_amount") or row.get("net_receipts") or row.get("balance") or ""
        pdf.drawString(left, y, _pdf_text(row.get("account_code"))[:14])
        pdf.drawString(left + 80, y, _pdf_text(row.get("account_name"))[:48])
        pdf.drawRightString(right - 120, y, _pdf_text(_plain_value(debit))[:18] or "-")
        pdf.drawRightString(right - 45, y, _pdf_text(_plain_value(credit))[:18] or "-")
        pdf.drawRightString(right, y, _pdf_text(_plain_value(balance))[:18] or "-")
        y -= 12

    pdf.setFont("Helvetica", 8)
    pdf.drawString(left, 34, _pdf_text(_footer_text(branding))[:110])
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()


def _report_excel_bytes(title: str, report, *, branding: dict | None = None) -> bytes:
    data = _model_to_dict(report)
    rows = _report_lines(data)
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]
    branding = branding or {}
    society_name = str(branding.get("society_name") or "GruhaMitra Society").strip()
    locality = ", ".join(
        part
        for part in [
            str(branding.get("city") or "").strip(),
            str(branding.get("state") or "").strip(),
            str(branding.get("pin_code") or "").strip(),
        ]
        if part
    )
    address = str(branding.get("society_address") or "").strip()
    ws.append([society_name])
    if address:
        ws.append([address])
    if locality:
        ws.append([locality])
    contact = society_contact_line(branding)
    if contact:
        ws.append(["Contact", contact])
    ws.append([title])
    ws.append(["Period", _plain_value(data.get("as_of") or data.get("from_date")), _plain_value(data.get("to_date"))])
    ws.append([])
    ws.append(["Section", "Account Code", "Account Name", "Debit", "Credit", "Balance"])
    for row in rows:
        ws.append(
            [
                row.get("section") or "",
                row.get("account_code") or "",
                row.get("account_name") or "",
                _plain_value(row.get("debit_total") or row.get("debit") or row.get("receipts")),
                _plain_value(row.get("credit_total") or row.get("credit") or row.get("payments")),
                _plain_value(row.get("net_balance") or row.get("net_amount") or row.get("net_receipts") or row.get("balance")),
            ]
        )
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def _download_response(content: bytes, *, filename: str, media_type: str) -> StreamingResponse:
    return StreamingResponse(
        BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/trial-balance")
async def trial_balance_legacy_endpoint(
    as_on_date: date | None = Query(default=None),
    as_of: date | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    report_date = as_of or as_on_date
    if report_date is None:
        raise HTTPException(status_code=422, detail="as_on_date or as_of is required")

    return await trial_balance_endpoint(
        as_of=report_date,
        session=session,
        current_user=current_user,
        accounting_context=accounting_context,
    )


@router.get("/balance-sheet")
async def balance_sheet_legacy_endpoint(
    as_on_date: date | None = Query(default=None),
    as_of: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    report_date = as_of or as_on_date or to_date
    if report_date is None:
        raise HTTPException(status_code=422, detail="as_on_date, as_of, or to_date is required")
    return await balance_sheet_endpoint(as_of=report_date, session=session, accounting_context=accounting_context)


@router.get("/income-and-expenditure")
async def income_expenditure_legacy_endpoint(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    return await income_expenditure_endpoint(
        from_date=from_date,
        to_date=to_date,
        session=session,
        accounting_context=accounting_context,
    )


@router.get("/receipts-and-payments")
async def receipts_payments_legacy_endpoint(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    return await receipts_payments_endpoint(
        from_date=from_date,
        to_date=to_date,
        session=session,
        accounting_context=accounting_context,
    )


@router.get("/member-dues")
async def member_dues_legacy_endpoint(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    return await _member_dues_payload(
        tenant_id=tenant_id,
        app_key=app_key,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/ledger")
async def ledger_legacy_endpoint(
    from_date: date = Query(...),
    to_date: date = Query(...),
    account_code: str = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    if from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must be on or before to_date")

    if account_code.strip().lower() == "all":
        accounts = (
            await session.execute(
                select(Account)
                .where(
                    Account.app_key == accounting_context.app_key,
                    Account.tenant_id == accounting_context.tenant_id,
                    Account.accounting_entity_id == accounting_context.accounting_entity_id,
                )
                .order_by(Account.code.asc().nullslast(), Account.name.asc())
            )
        ).scalars().all()
        ledgers = []
        for account in accounts:
            try:
                _account, raw_lines = await get_ledger_lines(
                    session,
                    app_key=accounting_context.app_key,
                    tenant_id=accounting_context.tenant_id,
                    accounting_entity_id=accounting_context.accounting_entity_id,
                    account_id=account.id,
                )
            except AccountingNotFoundError:
                continue
            payload = _ledger_report_payload(account, raw_lines, from_date=from_date, to_date=to_date)
            if payload["entries"] or payload["opening_balance"] != 0 or payload["closing_balance"] != 0:
                ledgers.append(payload)
        return {
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "ledgers": ledgers,
        }

    account = (
        await session.execute(
            select(Account).where(
                Account.app_key == accounting_context.app_key,
                Account.tenant_id == accounting_context.tenant_id,
                Account.accounting_entity_id == accounting_context.accounting_entity_id,
                Account.code == account_code.strip(),
            )
        )
    ).scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail=f"Account not found for code {account_code}")

    try:
        _account, raw_lines = await get_ledger_lines(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
            account_id=account.id,
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _ledger_report_payload(account, raw_lines, from_date=from_date, to_date=to_date)


@router.get("/general-ledger/export/pdf")
async def general_ledger_pdf_export_endpoint(
    from_date: date = Query(...),
    to_date: date = Query(...),
    account_code: str = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    report = await ledger_legacy_endpoint(
        from_date=from_date,
        to_date=to_date,
        account_code=account_code,
        session=session,
        current_user=current_user,
        accounting_context=accounting_context,
    )
    branding = await get_housing_society_branding(
        tenant_id=accounting_context.tenant_id,
        app_key=accounting_context.app_key,
    )
    pdf_bytes = _ledger_pdf_bytes(report, branding=branding)
    filename = f"general_ledger_{from_date.isoformat()}_{to_date.isoformat()}.pdf"
    return _download_response(pdf_bytes, filename=filename, media_type="application/pdf")


@router.get("/general-ledger/export/excel")
async def general_ledger_excel_export_endpoint(
    from_date: date = Query(...),
    to_date: date = Query(...),
    account_code: str = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    report = await ledger_legacy_endpoint(
        from_date=from_date,
        to_date=to_date,
        account_code=account_code,
        session=session,
        current_user=current_user,
        accounting_context=accounting_context,
    )
    branding = await get_housing_society_branding(
        tenant_id=accounting_context.tenant_id,
        app_key=accounting_context.app_key,
    )
    content = _report_excel_bytes("General Ledger", report, branding=branding)
    return _download_response(
        content,
        filename=f"general_ledger_{from_date.isoformat()}_{to_date.isoformat()}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/trial-balance/export/pdf")
async def trial_balance_pdf_export_endpoint(
    as_on_date: date | None = Query(default=None),
    as_of: date | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    report = await trial_balance_legacy_endpoint(as_on_date, as_of, session, current_user, accounting_context)
    branding = await get_housing_society_branding(
        tenant_id=accounting_context.tenant_id,
        app_key=accounting_context.app_key,
    )
    return _download_response(
        _report_pdf_bytes("Trial Balance", report, branding=branding),
        filename=f"trial_balance_{(as_of or as_on_date).isoformat()}.pdf",
        media_type="application/pdf",
    )


@router.get("/trial-balance/export/excel")
async def trial_balance_excel_export_endpoint(
    as_on_date: date | None = Query(default=None),
    as_of: date | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    report = await trial_balance_legacy_endpoint(as_on_date, as_of, session, current_user, accounting_context)
    branding = await get_housing_society_branding(
        tenant_id=accounting_context.tenant_id,
        app_key=accounting_context.app_key,
    )
    return _download_response(
        _report_excel_bytes("Trial Balance", report, branding=branding),
        filename=f"trial_balance_{(as_of or as_on_date).isoformat()}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/balance-sheet/export/pdf")
async def balance_sheet_pdf_export_endpoint(
    as_on_date: date | None = Query(default=None),
    as_of: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    report = await balance_sheet_legacy_endpoint(as_on_date, as_of, to_date, session, accounting_context)
    report_date = as_of or as_on_date or to_date
    branding = await get_housing_society_branding(
        tenant_id=accounting_context.tenant_id,
        app_key=accounting_context.app_key,
    )
    return _download_response(
        _report_pdf_bytes("Balance Sheet", report, branding=branding),
        filename=f"balance_sheet_{report_date.isoformat()}.pdf",
        media_type="application/pdf",
    )


@router.get("/balance-sheet/export/excel")
async def balance_sheet_excel_export_endpoint(
    as_on_date: date | None = Query(default=None),
    as_of: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    report = await balance_sheet_legacy_endpoint(as_on_date, as_of, to_date, session, accounting_context)
    report_date = as_of or as_on_date or to_date
    branding = await get_housing_society_branding(
        tenant_id=accounting_context.tenant_id,
        app_key=accounting_context.app_key,
    )
    return _download_response(
        _report_excel_bytes("Balance Sheet", report, branding=branding),
        filename=f"balance_sheet_{report_date.isoformat()}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/income-and-expenditure/export/pdf")
async def income_expenditure_pdf_export_endpoint(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    report = await income_expenditure_legacy_endpoint(from_date, to_date, session, accounting_context)
    branding = await get_housing_society_branding(
        tenant_id=accounting_context.tenant_id,
        app_key=accounting_context.app_key,
    )
    return _download_response(
        _report_pdf_bytes("Income and Expenditure", report, branding=branding),
        filename=f"income_and_expenditure_{from_date.isoformat()}_{to_date.isoformat()}.pdf",
        media_type="application/pdf",
    )


@router.get("/income-and-expenditure/export/excel")
async def income_expenditure_excel_export_endpoint(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    report = await income_expenditure_legacy_endpoint(from_date, to_date, session, accounting_context)
    branding = await get_housing_society_branding(
        tenant_id=accounting_context.tenant_id,
        app_key=accounting_context.app_key,
    )
    return _download_response(
        _report_excel_bytes("Income and Expenditure", report, branding=branding),
        filename=f"income_and_expenditure_{from_date.isoformat()}_{to_date.isoformat()}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/receipts-and-payments/export/pdf")
async def receipts_payments_pdf_export_endpoint(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    report = await receipts_payments_legacy_endpoint(from_date, to_date, session, accounting_context)
    branding = await get_housing_society_branding(
        tenant_id=accounting_context.tenant_id,
        app_key=accounting_context.app_key,
    )
    return _download_response(
        _report_pdf_bytes("Receipts and Payments", report, branding=branding),
        filename=f"receipts_and_payments_{from_date.isoformat()}_{to_date.isoformat()}.pdf",
        media_type="application/pdf",
    )


@router.get("/receipts-and-payments/export/excel")
async def receipts_payments_excel_export_endpoint(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    report = await receipts_payments_legacy_endpoint(from_date, to_date, session, accounting_context)
    branding = await get_housing_society_branding(
        tenant_id=accounting_context.tenant_id,
        app_key=accounting_context.app_key,
    )
    return _download_response(
        _report_excel_bytes("Receipts and Payments", report, branding=branding),
        filename=f"receipts_and_payments_{from_date.isoformat()}_{to_date.isoformat()}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
