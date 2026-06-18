"""Opening balances (CSV import) + year-end close.

Opening balances
----------------
The books start (or migrate from another system) with a trial balance. The
accountant uploads a CSV of account-wise — and, for Sundry Debtors/Creditors,
party-wise — opening balances. The flow is preview → confirm (maker-checker):
the preview resolves every row against the chart of accounts and parties and
shows the balancing line; posting writes ONE opening journal entry, with any
debit/credit difference going to Opening Balance Equity. Party rows carry
party_id on the journal line, so party opening balances finally live in the
ledger (they previously sat only on the party document, outside every report).

Year-end close
--------------
At FY end the income and expense accounts are closed to Retained Earnings:
each income account is debited by its net credit balance, each expense account
credited by its net debit balance, and the net profit (loss) is credited
(debited) to Retained Earnings on 31 March. Posting is idempotent per
financial year; mistakes are corrected with the standard journal reversal.
"""
import csv
import io
import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

OPENING_BALANCE_EQUITY_CODE = "31004"
RETAINED_EARNINGS_CODE = "31003"

_CENT = Decimal("0.01")


def _q2(value) -> Decimal:
    return Decimal(str(value)).quantize(_CENT, rounding=ROUND_HALF_UP)


# --------------------------------------------------------------------------- #
# CSV parsing (pure).
# --------------------------------------------------------------------------- #

_HEADER_ALIASES = {
    "account_code": ["account code", "code", "gl code", "account no", "account number", "acct code"],
    "account_name": ["account name", "account", "ledger", "ledger name", "head", "account head"],
    "party": ["party", "party code", "party name", "customer/vendor", "customer", "vendor", "party id"],
    "debit": ["debit", "dr", "debit amount", "dr amount", "opening debit"],
    "credit": ["credit", "cr", "credit amount", "cr amount", "opening credit"],
}


def _norm_header(name: str) -> str:
    text = re.sub(r"[_\-.]+", " ", str(name or "").strip().lower())
    return re.sub(r"\s+", " ", re.sub(r"[^a-z/ ]", "", text)).strip()


def _parse_amount(value) -> Decimal:
    text = str(value if value is not None else "").strip()
    if not text or text in {"-", "--"}:
        return Decimal("0.00")
    negative = text.startswith("(") and text.endswith(")")
    text = re.sub(r"[^\d.\-]", "", text.replace(",", ""))
    if not text or text in {"-", "."}:
        return Decimal("0.00")
    try:
        amount = Decimal(text)
    except InvalidOperation:
        return Decimal("0.00")
    return _q2(-amount if negative else amount)


TALLY_PRESET = {
    "account_name": "name",
    "account_code": "alias",
    "balance": "opening balance",
    "party": "parent"
}

ZOHO_PRESET = {
    "account_name": "account name",
    "account_code": "account code",
    "debit": "debit",
    "credit": "credit",
    "balance": "balance",
    "party": "contact"
}

QUICKBOOKS_PRESET = {
    "account_name": "account",
    "account_code": "number",
    "debit": "debit",
    "credit": "credit",
    "balance": "balance"
}


def _parse_single_balance(value) -> tuple[Decimal, Decimal]:
    """Parse a single balance string (e.g. "10000.00 Dr" or "-5000") into (debit, credit)."""
    text = str(value if value is not None else "").strip()
    if not text or text in {"-", "--"}:
        return Decimal("0.00"), Decimal("0.00")
    
    text_clean = text.lower()
    is_dr = "dr" in text_clean
    is_cr = "cr" in text_clean
    
    # Strip Dr/Cr and other non-numeric chars except minus and decimal point
    clean_num = re.sub(r"[^\d.\-]", "", text.replace(",", ""))
    if not clean_num or clean_num in {"-", "."}:
        return Decimal("0.00"), Decimal("0.00")
        
    try:
        val = Decimal(clean_num)
    except InvalidOperation:
        return Decimal("0.00"), Decimal("0.00")
        
    val = _q2(val)
    if is_dr:
        return abs(val), Decimal("0.00")
    elif is_cr:
        return Decimal("0.00"), abs(val)
    else:
        # Standard positive/negative logic: positive is Debit, negative is Credit
        if val >= 0:
            return val, Decimal("0.00")
        else:
            return Decimal("0.00"), abs(val)


def parse_opening_balances_csv(
    csv_text: str,
    header_mapping: dict[str, str] | None = None,
    preset: str | None = None
) -> list[dict]:
    """Parse an opening-balance CSV into normalized rows:
    {row_number, account_code, account_name, party, debit, credit}.

    Supports dynamic header mappings, predefined format presets, and single-column
    balance parsing.
    """
    text = (csv_text or "").lstrip("﻿")
    if not text.strip():
        raise ValueError("The uploaded file is empty")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("Could not read a CSV header row")

    normalized_fields = {_norm_header(name): name for name in reader.fieldnames if name}
    
    resolved_mapping = {}
    if preset == "tally":
        resolved_mapping = TALLY_PRESET
    elif preset == "zoho":
        resolved_mapping = ZOHO_PRESET
    elif preset == "quickbooks":
        resolved_mapping = QUICKBOOKS_PRESET
    elif header_mapping:
        resolved_mapping = header_mapping

    headers: dict[str, str] = {}
    if resolved_mapping:
        for key, field_alias in resolved_mapping.items():
            norm_alias = _norm_header(field_alias)
            if norm_alias in normalized_fields:
                headers[key] = normalized_fields[norm_alias]

    # Fallback to defaults if key not found in resolved_mapping
    for key, aliases in _HEADER_ALIASES.items():
        if key not in headers:
            for alias in aliases:
                if alias in normalized_fields:
                    headers[key] = normalized_fields[alias]
                    break

    if "account_code" not in headers and "account_name" not in headers:
        raise ValueError("Could not find an account column (tried: account code / code / account name / ledger ...)")
    if "debit" not in headers and "credit" not in headers and "balance" not in headers:
        raise ValueError("Could not find debit/credit or balance columns")

    rows: list[dict] = []
    for line_no, row in enumerate(reader, start=2):  # header is line 1
        debit = Decimal("0.00")
        credit = Decimal("0.00")
        
        if "balance" in headers:
            val_str = row.get(headers["balance"], "")
            debit, credit = _parse_single_balance(val_str)
        else:
            if "debit" in headers:
                debit = _parse_amount(row.get(headers["debit"], ""))
            if "credit" in headers:
                credit = _parse_amount(row.get(headers["credit"], ""))

        account_code = str(row.get(headers.get("account_code", ""), "") or "").strip()
        account_name = str(row.get(headers.get("account_name", ""), "") or "").strip()
        if not account_code and not account_name:
            continue  # blank / spacer row
        if debit == 0 and credit == 0:
            continue
        rows.append({
            "row_number": line_no,
            "account_code": account_code,
            "account_name": account_name,
            "party": str(row.get(headers.get("party", ""), "") or "").strip(),
            "debit": str(abs(debit)),
            "credit": str(abs(credit)),
        })
    if not rows:
        raise ValueError("No opening-balance rows could be parsed from the file")
    return rows


def csv_template() -> str:
    """A ready-to-fill sample the frontend offers for download."""
    return (
        "account_code,account_name,party,debit,credit\n"
        "11001,Cash in Hand,,25000,\n"
        "11010,Bank Account,,150000,\n"
        "12001,Sundry Debtors,CUST-001,40000,\n"
        "12001,Sundry Debtors,Acme Traders,15000,\n"
        "21001,Sundry Creditors,VEND-007,,30000\n"
        "13001,Inventory / Stock in Hand,,60000,\n"
        "24002,Loans Payable,,,100000\n"
    )


# --------------------------------------------------------------------------- #
# Preview assembly (pure given resolved lookups).
# --------------------------------------------------------------------------- #

def assemble_opening_preview(
    *,
    rows: list[dict],
    accounts_by_code: dict[str, dict],
    accounts_by_name: dict[str, dict],
    parties_by_code: dict[str, dict],
    parties_by_name: dict[str, dict],
    as_of: date,
) -> dict:
    """Resolve every CSV row against the COA/parties and compute the balancing
    line. Returns resolved lines + row-level errors; posting requires zero
    errors. All matching is exact (code first, then case-insensitive name)."""
    lines: list[dict] = []
    errors: list[dict] = []
    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")

    for row in rows:
        problems: list[str] = []
        debit = _q2(row.get("debit") or 0)
        credit = _q2(row.get("credit") or 0)
        if debit > 0 and credit > 0:
            problems.append("Row has both a debit and a credit — split it into two rows")

        account = None
        code = str(row.get("account_code") or "").strip()
        name = str(row.get("account_name") or "").strip()
        if code:
            account = accounts_by_code.get(code)
            if account is None:
                problems.append(f"Unknown account code '{code}'")
        elif name:
            account = accounts_by_name.get(name.lower())
            if account is None:
                problems.append(f"Unknown account name '{name}'")

        party = None
        party_key = str(row.get("party") or "").strip()
        if party_key:
            party = (
                parties_by_code.get(party_key)
                or parties_by_code.get(party_key.upper())
                or parties_by_name.get(party_key.lower())
            )
            if party is None:
                problems.append(f"Unknown party '{party_key}' (match by party code or exact name)")

        if problems:
            errors.append({"row_number": row.get("row_number"), "problems": problems,
                           "account": code or name, "party": party_key or None})
            continue

        total_debit += debit
        total_credit += credit
        lines.append({
            "row_number": row.get("row_number"),
            "account_id": account["account_id"],
            "account_code": account["code"],
            "account_name": account["name"],
            "party_id": party["party_id"] if party else None,
            "party_name": party["party_name"] if party else None,
            "debit": str(debit),
            "credit": str(credit),
        })

    difference = _q2(total_debit - total_credit)
    balancing_line = None
    if difference != 0 and lines:
        balancing_line = {
            "account_code": OPENING_BALANCE_EQUITY_CODE,
            "account_name": "Opening Balance Equity",
            "debit": str(-difference) if difference < 0 else "0.00",
            "credit": str(difference) if difference > 0 else "0.00",
        }

    return {
        "as_of": as_of.isoformat(),
        "lines": lines,
        "errors": errors,
        "line_count": len(lines),
        "error_count": len(errors),
        "total_debit": str(_q2(total_debit)),
        "total_credit": str(_q2(total_credit)),
        "difference": str(difference),
        "balancing_line": balancing_line,
        "can_post": len(errors) == 0 and len(lines) > 0,
        "notes": [
            "Posting writes ONE opening journal entry dated as-of; any debit/credit difference goes to Opening Balance Equity.",
            "Rows on Sundry Debtors/Creditors with a party post party-wise — they appear in aging, statements and allocation.",
            "To redo an opening balance, reverse the previous opening journal first, then upload again.",
        ],
    }


# --------------------------------------------------------------------------- #
# Year-end close (pure assembly from P&L lines).
# --------------------------------------------------------------------------- #

def assemble_year_end_lines(pnl_lines: list[dict], net_profit) -> dict:
    """Closing entries: zero out each income/expense account's net balance,
    with the net result going to Retained Earnings. Returns line specs with
    account ids plus the retained-earnings movement (by code; the caller
    resolves the account id)."""
    closing_lines: list[dict] = []
    for line in pnl_lines:
        net = _q2(line.get("net_amount") or 0)
        if net == 0:
            continue
        is_income = str(line.get("account_type")) == "income"
        # Income holds a credit balance (positive net) -> debit it closed.
        # Expense holds a debit balance (positive net) -> credit it closed.
        if is_income:
            debit, credit = (net, Decimal("0.00")) if net > 0 else (Decimal("0.00"), -net)
        else:
            debit, credit = (Decimal("0.00"), net) if net > 0 else (-net, Decimal("0.00"))
        closing_lines.append({
            "account_id": line.get("account_id"),
            "account_code": line.get("account_code"),
            "account_name": line.get("account_name"),
            "account_type": line.get("account_type"),
            "debit": str(debit),
            "credit": str(credit),
        })

    net = _q2(net_profit or 0)
    retained = {
        "account_code": RETAINED_EARNINGS_CODE,
        "account_name": "Retained Earnings",
        "debit": str(-net) if net < 0 else "0.00",   # loss reduces retained earnings
        "credit": str(net) if net > 0 else "0.00",
    }
    return {"closing_lines": closing_lines, "retained_earnings": retained, "net_profit": str(net)}


def _fy_dates(financial_year: str) -> tuple[date, date]:
    """'YYYY-YY' -> (Apr 1, Mar 31)."""
    start_year = int(str(financial_year)[:4])
    return date(start_year, 4, 1), date(start_year + 1, 3, 31)


# --------------------------------------------------------------------------- #
# Async service layer.
# --------------------------------------------------------------------------- #

async def _account_lookups(session, *, tenant_id: str, app_key: str, accounting_entity_id: str):
    from sqlalchemy import select
    from app.accounting.models.entities import Account
    from app.accounting.service import _accounting_scope

    rows = (await session.execute(
        select(Account.id, Account.code, Account.name).where(
            *_accounting_scope(Account, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        )
    )).all()
    by_code: dict[str, dict] = {}
    by_name: dict[str, dict] = {}
    for row in rows:
        info = {"account_id": row.id, "code": row.code, "name": row.name}
        if row.code:
            by_code[str(row.code)] = info
        if row.name:
            by_name[str(row.name).strip().lower()] = info
    return by_code, by_name


async def _party_lookups(*, tenant_id: str, app_key: str, accounting_entity_id: str):
    from app.db.mongo import get_collection
    from app.modules.business.service import PARTIES_COLLECTION

    rows = await get_collection(PARTIES_COLLECTION).find({
        "tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id,
    }).to_list(length=5000)
    by_code: dict[str, dict] = {}
    by_name: dict[str, dict] = {}
    for row in rows:
        info = {"party_id": row.get("party_id"), "party_name": row.get("party_name")}
        if row.get("party_code"):
            by_code[str(row["party_code"])] = info
        if row.get("party_id"):
            by_code[str(row["party_id"])] = info
        if row.get("party_name"):
            by_name[str(row["party_name"]).strip().lower()] = info
    return by_code, by_name


def _default_opening_date() -> date:
    today = date.today()
    return date(today.year if today.month >= 4 else today.year - 1, 4, 1)


async def build_opening_preview(
    session,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    csv_text: str,
    as_of: date | None = None,
    header_mapping: dict[str, str] | None = None,
    preset: str | None = None,
) -> dict:
    from app.accounting.service import initialize_default_chart_of_accounts

    if app_key == "mitrabooks":
        await initialize_default_chart_of_accounts(
            session, tenant_id=tenant_id, app_key=app_key,
            accounting_entity_id=accounting_entity_id, organization_type="BUSINESS",
        )
    rows = parse_opening_balances_csv(csv_text, header_mapping=header_mapping, preset=preset)
    accounts_by_code, accounts_by_name = await _account_lookups(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    parties_by_code, parties_by_name = await _party_lookups(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    preview = assemble_opening_preview(
        rows=rows,
        accounts_by_code=accounts_by_code, accounts_by_name=accounts_by_name,
        parties_by_code=parties_by_code, parties_by_name=parties_by_name,
        as_of=as_of or _default_opening_date(),
    )
    existing = await _find_opening_entries(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    preview["existing_opening_entries"] = existing
    if existing:
        preview["notes"].insert(0, "An opening journal already exists — posting again needs allow_duplicate, or reverse the old entry first.")
    return preview


async def _find_opening_entries(session, *, tenant_id: str, app_key: str, accounting_entity_id: str) -> list[dict]:
    from sqlalchemy import select
    from app.accounting.models.entities import JournalEntry
    from app.accounting.service import _accounting_scope

    rows = (await session.execute(
        select(JournalEntry.id, JournalEntry.entry_date, JournalEntry.description).where(
            *_accounting_scope(JournalEntry, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
            JournalEntry.source_document_type == "opening_balance",
        ).order_by(JournalEntry.id.asc())
    )).all()
    return [{"journal_entry_id": r.id,
             "entry_date": r.entry_date.isoformat() if hasattr(r.entry_date, "isoformat") else str(r.entry_date),
             "description": r.description} for r in rows]


async def post_opening_balances(
    session,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    csv_text: str,
    as_of: date | None = None,
    allow_duplicate: bool = False,
    created_by: str,
    idempotency_key: str | None = None,
    header_mapping: dict[str, str] | None = None,
    preset: str | None = None,
) -> dict:
    from app.accounting.schemas import JournalLineIn, JournalPostRequest
    from app.accounting.service import AccountingValidationError, post_journal_entry

    as_of = as_of or _default_opening_date()
    preview = await build_opening_preview(
        session, tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, csv_text=csv_text, as_of=as_of,
        header_mapping=header_mapping, preset=preset,
    )
    if not preview["can_post"]:
        raise AccountingValidationError(
            f"The file has {preview['error_count']} unresolved row(s) — fix them and re-upload"
        )
    if preview["existing_opening_entries"] and not allow_duplicate:
        first = preview["existing_opening_entries"][0]
        raise AccountingValidationError(
            f"An opening journal already exists (entry #{first['journal_entry_id']} dated {first['entry_date']}). "
            "Reverse it first, or pass allow_duplicate to post another."
        )

    accounts_by_code, _ = await _account_lookups(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    journal_lines = [
        JournalLineIn(
            account_id=line["account_id"],
            debit=Decimal(line["debit"]),
            credit=Decimal(line["credit"]),
            party_id=line["party_id"],
        )
        for line in preview["lines"]
    ]
    balancing = preview["balancing_line"]
    if balancing:
        obe = accounts_by_code.get(OPENING_BALANCE_EQUITY_CODE)
        if obe is None:
            raise AccountingValidationError(
                f"Opening Balance Equity account ({OPENING_BALANCE_EQUITY_CODE}) not found in the chart of accounts"
            )
        journal_lines.append(JournalLineIn(
            account_id=obe["account_id"],
            debit=Decimal(balancing["debit"]),
            credit=Decimal(balancing["credit"]),
        ))

    journal_entry, created = await post_journal_entry(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        created_by=created_by,
        payload=JournalPostRequest(
            entry_date=as_of,
            description=f"Opening balances as of {as_of.isoformat()}",
            reference="OPENING",
            source_module="business",
            source_document_type="opening_balance",
            source_document_id=f"opening:{accounting_entity_id}:{as_of.isoformat()}",
            lines=journal_lines,
        ),
        idempotency_key=idempotency_key or f"opening-balance:{accounting_entity_id}:{as_of.isoformat()}",
    )
    return {
        "journal_entry_id": journal_entry.id,
        "created": created,
        "as_of": as_of.isoformat(),
        "line_count": len(journal_lines),
        "total_debit": preview["total_debit"],
        "total_credit": preview["total_credit"],
        "balancing_line": balancing,
    }


async def build_year_end_preview(
    session,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    financial_year: str,
) -> dict:
    from app.accounting.service import get_profit_loss

    fy_start, fy_end = _fy_dates(financial_year)
    pnl_lines, income_total, expense_total, net_profit = await get_profit_loss(
        session, tenant_id=tenant_id, from_date=fy_start, to_date=fy_end,
        app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    assembled = assemble_year_end_lines(pnl_lines, net_profit)
    existing = await _find_year_end_entries(
        session, tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, financial_year=financial_year,
    )
    return {
        "financial_year": financial_year,
        "from_date": fy_start.isoformat(),
        "to_date": fy_end.isoformat(),
        "income_total": str(_q2(income_total)),
        "expense_total": str(_q2(expense_total)),
        "net_profit": assembled["net_profit"],
        "closing_lines": assembled["closing_lines"],
        "retained_earnings": assembled["retained_earnings"],
        "already_closed": existing,
        "can_post": len(assembled["closing_lines"]) > 0 and not existing,
        "notes": [
            "Closing zeroes every income/expense account for the year and moves the net result to Retained Earnings on 31 March.",
            "Post all year-end adjustments (depreciation, provisions) BEFORE closing.",
            "The close is one reversible journal entry — reverse it to reopen the year.",
        ],
    }


async def _find_year_end_entries(
    session, *, tenant_id: str, app_key: str, accounting_entity_id: str, financial_year: str,
) -> list[dict]:
    from sqlalchemy import select
    from app.accounting.models.entities import JournalEntry
    from app.accounting.service import _accounting_scope

    rows = (await session.execute(
        select(JournalEntry.id, JournalEntry.entry_date).where(
            *_accounting_scope(JournalEntry, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
            JournalEntry.source_document_type == "year_end_close",
            JournalEntry.source_document_id == f"year-end:{financial_year}",
        ).order_by(JournalEntry.id.asc())
    )).all()
    return [{"journal_entry_id": r.id,
             "entry_date": r.entry_date.isoformat() if hasattr(r.entry_date, "isoformat") else str(r.entry_date)}
            for r in rows]


async def post_year_end_close(
    session,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    financial_year: str,
    created_by: str,
    idempotency_key: str | None = None,
) -> dict:
    from app.accounting.schemas import JournalLineIn, JournalPostRequest
    from app.accounting.service import AccountingValidationError, post_journal_entry

    preview = await build_year_end_preview(
        session, tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, financial_year=financial_year,
    )
    if preview["already_closed"]:
        first = preview["already_closed"][0]
        raise AccountingValidationError(
            f"FY {financial_year} is already closed (entry #{first['journal_entry_id']}). Reverse it to reopen."
        )
    if not preview["closing_lines"]:
        raise AccountingValidationError(f"No income or expense activity found in FY {financial_year}")

    accounts_by_code, _ = await _account_lookups(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    retained = accounts_by_code.get(RETAINED_EARNINGS_CODE)
    if retained is None:
        raise AccountingValidationError(
            f"Retained Earnings account ({RETAINED_EARNINGS_CODE}) not found in the chart of accounts"
        )

    journal_lines = [
        JournalLineIn(account_id=line["account_id"], debit=Decimal(line["debit"]), credit=Decimal(line["credit"]))
        for line in preview["closing_lines"]
    ]
    re_line = preview["retained_earnings"]
    if Decimal(re_line["debit"]) > 0 or Decimal(re_line["credit"]) > 0:
        journal_lines.append(JournalLineIn(
            account_id=retained["account_id"],
            debit=Decimal(re_line["debit"]),
            credit=Decimal(re_line["credit"]),
        ))

    fy_end = _fy_dates(financial_year)[1]
    journal_entry, created = await post_journal_entry(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        created_by=created_by,
        payload=JournalPostRequest(
            entry_date=fy_end,
            description=f"Year-end close FY {financial_year}",
            reference=f"YE-{financial_year}",
            source_module="business",
            source_document_type="year_end_close",
            source_document_id=f"year-end:{financial_year}",
            lines=journal_lines,
        ),
        idempotency_key=idempotency_key or f"year-end-close:{accounting_entity_id}:{financial_year}",
    )
    return {
        "journal_entry_id": journal_entry.id,
        "created": created,
        "financial_year": financial_year,
        "entry_date": fy_end.isoformat(),
        "net_profit": preview["net_profit"],
        "line_count": len(journal_lines),
    }


async def export_opening_balances_csv(
    session,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
) -> str:
    from sqlalchemy import select
    from app.accounting.models.entities import JournalEntry, JournalLine, Account
    from app.accounting.service import _accounting_scope
    from app.db.mongo import get_collection
    from app.modules.business.service import PARTIES_COLLECTION
    import io
    import csv

    # 1. Fetch opening journal entry
    stmt = select(JournalEntry).where(
        *_accounting_scope(JournalEntry, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        JournalEntry.source_document_type == "opening_balance"
    ).order_by(JournalEntry.id.desc())
    entry = (await session.execute(stmt)).scalars().first()
    
    if not entry:
        # Return empty template if no opening balances have been posted yet
        return csv_template()

    # 2. Fetch lines with account join
    lines_stmt = select(JournalLine, Account).join(Account).where(
        JournalLine.journal_id == entry.id
    ).order_by(JournalLine.id.asc())
    results = (await session.execute(lines_stmt)).all()

    # 3. Load parties for subledger mapping
    parties = await get_collection(PARTIES_COLLECTION).find({
        "tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id,
    }).to_list(length=5000)
    party_map = {p["party_id"]: p.get("party_code") or p.get("party_name") or "" for p in parties if p.get("party_id")}

    # 4. Generate CSV
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["account_code", "account_name", "party", "debit", "credit"])
    
    for line, account in results:
        # Skip the Opening Balance Equity line if it was automatically added for balancing
        if account.code == OPENING_BALANCE_EQUITY_CODE:
            continue
            
        party_val = party_map.get(line.party_id, "") if line.party_id else ""
        debit_val = str(line.debit) if line.debit > 0 else ""
        credit_val = str(line.credit) if line.credit > 0 else ""
        writer.writerow([account.code, account.name, party_val, debit_val, credit_val])
        
    return out.getvalue()

