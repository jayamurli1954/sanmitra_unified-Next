"""Bulk voucher/transaction import logic.

Supports importing historical vouchers from external sources.
Ensures double-entry integrity and tenant isolation.
"""
import csv
import io
import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import post_journal_entry, AccountingValidationError
from app.db.mongo import get_collection
from app.modules.business.service import VOUCHERS_COLLECTION, PARTIES_COLLECTION
from app.modules.business.opening_close import _account_lookups, _party_lookups, _norm_header, _parse_amount, _q2

_VOUCHER_HEADER_ALIASES = {
    "date": ["date", "entry date", "voucher date", "tx date", "transaction date"],
    "voucher_type": ["voucher type", "type", "tx type", "transaction type"],
    "voucher_number": ["voucher number", "voucher no", "voucher no.", "reference", "ref", "doc no", "document number"],
    "debit_account": ["debit account", "dr account", "debit gl", "debit ledger"],
    "credit_account": ["credit account", "cr account", "credit gl", "credit ledger"],
    "account": ["account", "account code", "account name", "ledger", "ledger name", "gl code", "code"],
    "debit": ["debit", "dr", "debit amount", "dr amount", "amount dr"],
    "credit": ["credit", "cr", "credit amount", "cr amount", "amount cr"],
    "amount": ["amount", "value", "net amount", "tx amount"],
    "description": ["description", "narration", "particulars", "remarks"],
    "party": ["party", "party code", "party name", "customer/vendor", "customer", "vendor", "party id"],
}


def voucher_csv_template() -> str:
    """Sample CSV for the bulk voucher import."""
    return (
        "date,voucher_type,voucher_number,debit_account,credit_account,amount,description,party\n"
        "2026-04-01,receipt,REC-001,11010,12001,15000.00,Received payment from customer,CUST-001\n"
        "2026-04-02,payment,PAY-001,21001,11010,5000.00,Office rent payment,VEND-007\n"
        "2026-04-03,journal,JV-001,13001,24002,12000.00,Inventory purchase adjustment,\n"
    )


def parse_vouchers_csv(csv_text: str) -> tuple[str, list[dict]]:
    """Parse the CSV text and determine the format type: 'double_entry' or 'ledger_lines'.

    Returns (format_type, list of parsed dicts).
    """
    text = (csv_text or "").lstrip("﻿")
    if not text.strip():
        raise ValueError("The uploaded file is empty")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("Could not read a CSV header row")

    normalized_fields = {_norm_header(name): name for name in reader.fieldnames if name}

    headers: dict[str, str] = {}
    for key, aliases in _VOUCHER_HEADER_ALIASES.items():
        for alias in aliases:
            norm_alias = _norm_header(alias)
            if norm_alias in normalized_fields:
                headers[key] = normalized_fields[norm_alias]
                break

    # Determine format
    is_double_entry = "debit_account" in headers or "credit_account" in headers
    format_type = "double_entry" if is_double_entry else "ledger_lines"

    # Validate minimal headers
    if "date" not in headers:
        raise ValueError("Could not find a date column (tried: date, entry date, tx date...)")
    if "voucher_type" not in headers:
        raise ValueError("Could not find a voucher type column (tried: voucher_type, type...)")

    if is_double_entry:
        if "debit_account" not in headers or "credit_account" not in headers:
            raise ValueError("Double-entry format requires both 'debit_account' and 'credit_account' columns")
        if "amount" not in headers:
            raise ValueError("Double-entry format requires an 'amount' column")
    else:
        if "account" not in headers:
            raise ValueError("Ledger-lines format requires an 'account' column")
        if "debit" not in headers and "credit" not in headers:
            raise ValueError("Ledger-lines format requires 'debit' and/or 'credit' columns")

    rows: list[dict] = []
    for line_no, row in enumerate(reader, start=2):
        # Date
        dt_val = str(row.get(headers["date"], "") or "").strip()
        if not dt_val:
            continue  # skip empty lines
        try:
            entry_date = date.fromisoformat(dt_val)
        except ValueError:
            entry_date = None

        # Voucher Type
        vtype = str(row.get(headers["voucher_type"], "") or "").strip().lower()
        if vtype not in {"receipt", "payment", "journal", "contra", "sales", "purchase"}:
            vtype = "journal"

        # Voucher No
        vnum = str(row.get(headers.get("voucher_number", ""), "") or "").strip()

        # Description
        desc = str(row.get(headers.get("description", ""), "") or "").strip()

        # Party
        party = str(row.get(headers.get("party", ""), "") or "").strip()

        if is_double_entry:
            amount = _parse_amount(row.get(headers["amount"], ""))
            if amount <= 0:
                continue
            rows.append({
                "row_number": line_no,
                "date": dt_val,
                "parsed_date": entry_date,
                "voucher_type": vtype,
                "voucher_number": vnum,
                "debit_account": str(row.get(headers["debit_account"], "") or "").strip(),
                "credit_account": str(row.get(headers["credit_account"], "") or "").strip(),
                "amount": str(amount),
                "description": desc,
                "party": party,
            })
        else:
            debit = _parse_amount(row.get(headers.get("debit", ""), ""))
            credit = _parse_amount(row.get(headers.get("credit", ""), ""))
            if debit == 0 and credit == 0:
                continue
            rows.append({
                "row_number": line_no,
                "date": dt_val,
                "parsed_date": entry_date,
                "voucher_type": vtype,
                "voucher_number": vnum,
                "account": str(row.get(headers["account"], "") or "").strip(),
                "debit": str(debit),
                "credit": str(credit),
                "description": desc,
                "party": party,
            })

    if not rows:
        raise ValueError("No valid rows could be parsed from the file")

    return format_type, rows


async def build_bulk_import_preview(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    csv_text: str,
) -> dict:
    """Validate and preview a bulk voucher CSV without posting."""
    format_type, rows = parse_vouchers_csv(csv_text)
    accounts_by_code, accounts_by_name = await _account_lookups(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    parties_by_code, parties_by_name = await _party_lookups(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )

    errors = []
    vouchers = []

    # Helper to resolve account
    def resolve_account(key: str, row_no: int):
        if not key:
            return None, f"Missing account code/name"
        acc = accounts_by_code.get(key) or accounts_by_name.get(key.lower())
        if not acc:
            return None, f"Unknown account '{key}'"
        return acc, None

    # Helper to resolve party
    def resolve_party(key: str, row_no: int):
        if not key:
            return None, None
        pt = (
            parties_by_code.get(key)
            or parties_by_code.get(key.upper())
            or parties_by_name.get(key.lower())
        )
        if not pt:
            return None, f"Unknown party '{key}'"
        return pt, None

    if format_type == "double_entry":
        for idx, r in enumerate(rows):
            problems = []
            if not r["parsed_date"]:
                problems.append(f"Invalid date format '{r['date']}' (expected YYYY-MM-DD)")

            debit_acc, err_deb = resolve_account(r["debit_account"], r["row_number"])
            if err_deb:
                problems.append(err_deb)
            credit_acc, err_cred = resolve_account(r["credit_account"], r["row_number"])
            if err_cred:
                problems.append(err_cred)

            if debit_acc and credit_acc and debit_acc["account_id"] == credit_acc["account_id"]:
                problems.append("Debit and credit accounts must be different")

            party_resolved, err_party = resolve_party(r["party"], r["row_number"])
            if err_party:
                problems.append(err_party)

            if problems:
                errors.append({
                    "row_number": r["row_number"],
                    "problems": problems,
                    "voucher_number": r["voucher_number"] or f"row-{r['row_number']}"
                })
            else:
                # Add to preview vouchers list
                vouchers.append({
                    "row_number": r["row_number"],
                    "date": r["date"],
                    "voucher_type": r["voucher_type"],
                    "voucher_number": r["voucher_number"] or f"AUTO-{idx+1}",
                    "debit_account_code": debit_acc["code"],
                    "debit_account_name": debit_acc["name"],
                    "debit_account_id": debit_acc["account_id"],
                    "credit_account_code": credit_acc["code"],
                    "credit_account_name": credit_acc["name"],
                    "credit_account_id": credit_acc["account_id"],
                    "amount": r["amount"],
                    "description": r["description"],
                    "party_id": party_resolved["party_id"] if party_resolved else None,
                    "party_name": party_resolved["party_name"] if party_resolved else None,
                })
    else:
        # Group rows by voucher number or sequential runs
        # If voucher number is empty, we throw an error for now
        groups = {}
        for r in rows:
            vnum = r["voucher_number"]
            if not vnum:
                errors.append({
                    "row_number": r["row_number"],
                    "problems": ["Voucher number is required for multi-line ledger uploads"],
                    "voucher_number": ""
                })
                continue
            groups.setdefault(vnum, []).append(r)

        for vnum, group_rows in groups.items():
            problems = []
            lines = []
            total_debit = Decimal("0.00")
            total_credit = Decimal("0.00")
            vtype = group_rows[0]["voucher_type"]
            vdate = group_rows[0]["date"]
            vdate_parsed = group_rows[0]["parsed_date"]
            description = group_rows[0]["description"]

            if not vdate_parsed:
                problems.append(f"Invalid date format '{vdate}' (expected YYYY-MM-DD)")

            for gr in group_rows:
                debit_val = Decimal(gr["debit"])
                credit_val = Decimal(gr["credit"])
                total_debit += debit_val
                total_credit += credit_val

                acc, err_acc = resolve_account(gr["account"], gr["row_number"])
                if err_acc:
                    problems.append(f"Row {gr['row_number']}: {err_acc}")
                
                party_resolved, err_party = resolve_party(gr["party"], gr["row_number"])
                if err_party:
                    problems.append(f"Row {gr['row_number']}: {err_party}")

                if acc:
                    lines.append({
                        "row_number": gr["row_number"],
                        "account_id": acc["account_id"],
                        "account_code": acc["code"],
                        "account_name": acc["name"],
                        "debit": gr["debit"],
                        "credit": gr["credit"],
                        "party_id": party_resolved["party_id"] if party_resolved else None,
                        "party_name": party_resolved["party_name"] if party_resolved else None,
                    })

            if total_debit != total_credit:
                problems.append(f"Voucher does not balance: Total Debits ({total_debit}) != Total Credits ({total_credit})")

            if problems:
                for gr in group_rows:
                    errors.append({
                        "row_number": gr["row_number"],
                        "problems": problems,
                        "voucher_number": vnum
                    })
            else:
                vouchers.append({
                    "row_number": group_rows[0]["row_number"],
                    "date": vdate,
                    "voucher_type": vtype,
                    "voucher_number": vnum,
                    "lines": lines,
                    "amount": str(total_debit),
                    "description": description,
                })

    return {
        "format_type": format_type,
        "vouchers": vouchers,
        "errors": errors,
        "voucher_count": len(vouchers),
        "error_count": len(errors),
        "can_import": len(errors) == 0 and len(vouchers) > 0,
    }


async def post_bulk_import_vouchers(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    csv_text: str,
    created_by: str,
) -> dict:
    """Perform the actual import of vouchers within a single transaction."""
    preview = await build_bulk_import_preview(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        csv_text=csv_text,
    )

    if not preview["can_import"]:
        raise AccountingValidationError(
            f"Cannot import: CSV has {preview['error_count']} row error(s). Review the preview first."
        )

    vouchers_col = get_collection(VOUCHERS_COLLECTION)
    imported_vouchers = []

    # Process all vouchers
    for v in preview["vouchers"]:
        voucher_id = str(uuid4())
        voucher_number = v["voucher_number"]
        entry_date = date.fromisoformat(v["date"])
        description = v["description"]

        if preview["format_type"] == "double_entry":
            debit_account_id = v["debit_account_id"]
            credit_account_id = v["credit_account_id"]
            amount = Decimal(v["amount"])

            # Determine party side
            debit_party = v["party_id"] if v["voucher_type"] == "payment" else None
            credit_party = v["party_id"] if v["voucher_type"] == "receipt" else None

            lines = [
                JournalLineIn(account_id=debit_account_id, debit=amount, credit=Decimal("0"), party_id=debit_party),
                JournalLineIn(account_id=credit_account_id, debit=Decimal("0"), credit=amount, party_id=credit_party),
            ]

            doc = {
                "voucher_id": voucher_id,
                "voucher_number": voucher_number,
                "voucher_type": v["voucher_type"],
                "tenant_id": tenant_id,
                "app_key": app_key,
                "accounting_entity_id": accounting_entity_id,
                "party_id": v["party_id"],
                "amount": str(amount),
                "entry_date": v["date"],
                "debit_account_id": debit_account_id,
                "credit_account_id": credit_account_id,
                "description": description,
                "reference": voucher_number,
                "status": "posted",
                "created_by": created_by,
            }

        else:
            # Ledger lines format
            lines = [
                JournalLineIn(
                    account_id=line["account_id"],
                    debit=Decimal(line["debit"]),
                    credit=Decimal(line["credit"]),
                    party_id=line["party_id"],
                )
                for line in v["lines"]
            ]
            amount = Decimal(v["amount"])

            doc = {
                "voucher_id": voucher_id,
                "voucher_number": voucher_number,
                "voucher_type": v["voucher_type"],
                "tenant_id": tenant_id,
                "app_key": app_key,
                "accounting_entity_id": accounting_entity_id,
                "amount": str(amount),
                "entry_date": v["date"],
                "description": description,
                "reference": voucher_number,
                "status": "posted",
                "created_by": created_by,
                # Store line details in MongoDB document as well for historical reference
                "lines": [
                    {
                        "account_id": line["account_id"],
                        "account_code": line["account_code"],
                        "debit": line["debit"],
                        "credit": line["credit"],
                        "party_id": line["party_id"],
                    }
                    for line in v["lines"]
                ]
            }

        # Post journal entry in PostgreSQL
        journal_entry, _ = await post_journal_entry(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=accounting_entity_id,
            created_by=created_by,
            payload=JournalPostRequest(
                entry_date=entry_date,
                description=description,
                reference=voucher_number,
                source_module="business",
                source_document_type="bulk_import_voucher",
                source_document_id=voucher_id,
                lines=lines,
            ),
            idempotency_key=f"bulk-import:{voucher_number}:{voucher_id}",
        )

        doc["journal_entry_id"] = journal_entry.id
        await vouchers_col.insert_one(doc)

        imported_vouchers.append({
            "voucher_id": voucher_id,
            "voucher_number": voucher_number,
            "journal_entry_id": journal_entry.id,
        })

    return {
        "success": True,
        "format_type": preview["format_type"],
        "imported_count": len(imported_vouchers),
        "vouchers": imported_vouchers,
    }
