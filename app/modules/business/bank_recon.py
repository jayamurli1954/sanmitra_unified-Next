"""Bank reconciliation — import a bank-statement CSV, match its lines against
the bank account's posted ledger lines, and produce a Bank Reconciliation
Statement (BRS).

Design rules, mirroring payment allocation and the GSTR-2B reconciliation:

  * A match is PURE METADATA in Mongo — it never posts to the GL. The ledger
    legs already exist (the voucher posted Dr/Dr Bank); matching only records
    that a statement line corresponds to them.
  * Suggestions never auto-apply (maker-checker): amount must agree exactly,
    dates may differ within a window, the accountant confirms each match.
  * Sign convention: the books' bank account is an asset, so a statement
    DEPOSIT (bank credit) corresponds to a ledger DEBIT, and a statement
    WITHDRAWAL (bank debit) corresponds to a ledger CREDIT.
  * Pure functions parse/suggest/assemble; async wrappers do the I/O.
"""
import csv
import io
import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

BANK_STATEMENT_LINES_COLLECTION = "business_bank_statement_lines"
BANK_RECON_MATCHES_COLLECTION = "business_bank_recon_matches"

# How far apart the statement date and the book entry date may be for a
# suggestion (cheque clearing / processing lag).
SUGGEST_DATE_WINDOW_DAYS = 7

_CENT = Decimal("0.01")


def _q2(value) -> Decimal:
    return Decimal(str(value)).quantize(_CENT, rounding=ROUND_HALF_UP)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# CSV parsing — tolerant of the header/format variety Indian banks export.
# --------------------------------------------------------------------------- #

# Header aliases, lowercased and stripped of punctuation, checked in order.
_HEADER_ALIASES = {
    "txn_date": ["date", "txn date", "transaction date", "value date", "tran date", "post date", "value dt", "txn posted date"],
    "description": ["description", "narration", "particulars", "details", "transaction remarks", "remarks", "transaction details"],
    "ref": ["ref", "ref no", "reference", "reference no", "cheque no", "chq no", "cheque number", "chq./ref.no.", "utr", "utr no", "cheque/ref no"],
    "withdrawal": ["withdrawal", "withdrawal amt", "withdrawal amount", "debit", "debit amount", "dr", "dr amount", "paid out", "withdrawals"],
    "deposit": ["deposit", "deposit amt", "deposit amount", "credit", "credit amount", "cr", "cr amount", "paid in", "deposits"],
    "balance": ["balance", "closing balance", "running balance", "bal", "available balance"],
    # Single-amount layouts: one amount column plus a Dr/Cr indicator column.
    "amount": ["amount", "transaction amount", "amt"],
    "drcr": ["dr/cr", "cr/dr", "type", "dr cr", "transaction type"],
}

_DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%d-%b-%Y", "%d %b %Y", "%d-%b-%y"]


def _norm_header(name: str) -> str:
    return re.sub(r"[^a-z/. ]", "", str(name or "").strip().lower()).strip()


def _map_headers(fieldnames: list[str]) -> dict[str, str]:
    """Map our canonical keys to the CSV's actual column names."""
    normalized = {_norm_header(name): name for name in fieldnames if name}
    mapping: dict[str, str] = {}
    for key, aliases in _HEADER_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                mapping[key] = normalized[alias]
                break
    return mapping


def _parse_date(value: str) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    # ISO with time component
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError:
        return None


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


def parse_bank_statement_csv(csv_text: str) -> list[dict]:
    """Parse a bank-statement CSV into normalized line dicts:
    {txn_date, description, ref, withdrawal, deposit, balance} (amounts as str).

    Supports separate withdrawal/deposit columns, or a single amount column
    with a Dr/Cr indicator, or a single signed amount column (negative =
    withdrawal). Rows without a parseable date or with zero movement are
    skipped. Raises ValueError when no usable columns/rows are found.
    """
    text = (csv_text or "").lstrip("﻿")
    if not text.strip():
        raise ValueError("The uploaded file is empty")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("Could not read a CSV header row")
    headers = _map_headers(list(reader.fieldnames))
    if "txn_date" not in headers:
        raise ValueError("Could not find a date column (tried: date / txn date / value date ...)")
    has_two_cols = "withdrawal" in headers or "deposit" in headers
    if not has_two_cols and "amount" not in headers:
        raise ValueError("Could not find amount columns (withdrawal/deposit, debit/credit, or amount)")

    lines: list[dict] = []
    for row in reader:
        txn_date = _parse_date(row.get(headers["txn_date"]))
        if txn_date is None:
            continue  # blank/summary/header-repeat rows
        if has_two_cols:
            withdrawal = _parse_amount(row.get(headers.get("withdrawal", ""), ""))
            deposit = _parse_amount(row.get(headers.get("deposit", ""), ""))
        else:
            amount = _parse_amount(row.get(headers["amount"]))
            drcr = str(row.get(headers.get("drcr", ""), "") or "").strip().upper()
            if drcr.startswith("D"):
                withdrawal, deposit = abs(amount), Decimal("0.00")
            elif drcr.startswith("C"):
                withdrawal, deposit = Decimal("0.00"), abs(amount)
            else:
                # Signed single column: negative = money out.
                withdrawal = abs(amount) if amount < 0 else Decimal("0.00")
                deposit = amount if amount > 0 else Decimal("0.00")
        withdrawal = abs(withdrawal)
        deposit = abs(deposit)
        if withdrawal == 0 and deposit == 0:
            continue
        balance_raw = row.get(headers.get("balance", ""), "")
        balance = _parse_amount(balance_raw) if str(balance_raw or "").strip() else None
        lines.append({
            "txn_date": txn_date,
            "description": str(row.get(headers.get("description", ""), "") or "").strip(),
            "ref": str(row.get(headers.get("ref", ""), "") or "").strip(),
            "withdrawal": str(withdrawal),
            "deposit": str(deposit),
            "balance": str(balance) if balance is not None else None,
        })
    if not lines:
        raise ValueError("No transaction rows could be parsed from the file")
    return lines


def statement_line_dedupe_key(line: dict) -> str:
    """Stable fingerprint so re-uploading the same statement skips known rows."""
    return "|".join([
        str(line.get("txn_date") or ""),
        str(line.get("withdrawal") or "0"),
        str(line.get("deposit") or "0"),
        str(line.get("ref") or "").strip().lower(),
        str(line.get("description") or "").strip().lower()[:80],
    ])


# --------------------------------------------------------------------------- #
# Matching — pure suggestion logic (never auto-applies).
# --------------------------------------------------------------------------- #

def _ledger_side_amount(ledger_line: dict) -> tuple[str, Decimal]:
    """('deposit'|'withdrawal', amount): which statement side this book line
    should appear on. Book debit = money into bank = statement deposit."""
    debit = _q2(ledger_line.get("debit") or 0)
    credit = _q2(ledger_line.get("credit") or 0)
    if debit > 0:
        return "deposit", debit
    return "withdrawal", credit


def _statement_side_amount(stmt_line: dict) -> tuple[str, Decimal]:
    deposit = _q2(stmt_line.get("deposit") or 0)
    if deposit > 0:
        return "deposit", deposit
    return "withdrawal", _q2(stmt_line.get("withdrawal") or 0)


def _date_diff_days(a: str | None, b: str | None) -> int | None:
    try:
        return abs((date.fromisoformat(str(a)[:10]) - date.fromisoformat(str(b)[:10])).days)
    except (ValueError, TypeError):
        return None


def suggest_matches(
    statement_lines: list[dict],
    ledger_lines: list[dict],
    *,
    date_window_days: int = SUGGEST_DATE_WINDOW_DAYS,
) -> list[dict]:
    """One-to-one match suggestions between unmatched statement lines and
    unmatched book lines. Amount and side must agree exactly; dates may differ
    by up to `date_window_days`. A reference appearing in the book entry's
    reference/description upgrades confidence. Greedy assignment, closest
    date first — each line is suggested at most once."""
    candidates: list[tuple] = []
    for s in statement_lines:
        s_side, s_amount = _statement_side_amount(s)
        if s_amount <= 0:
            continue
        s_ref = str(s.get("ref") or "").strip().lower()
        for l in ledger_lines:
            l_side, l_amount = _ledger_side_amount(l)
            if l_side != s_side or l_amount != s_amount or l_amount <= 0:
                continue
            diff = _date_diff_days(s.get("txn_date"), l.get("entry_date"))
            if diff is None or diff > date_window_days:
                continue
            haystack = f"{l.get('reference') or ''} {l.get('description') or ''}".lower()
            ref_hit = bool(s_ref) and s_ref in haystack
            candidates.append((0 if ref_hit else 1, diff, str(s.get("txn_date")), s, l, ref_hit))

    candidates.sort(key=lambda c: (c[0], c[1], c[2]))
    used_statement: set[str] = set()
    used_ledger: set[str] = set()
    suggestions: list[dict] = []
    for _, diff, _, s, l, ref_hit in candidates:
        s_id = str(s.get("statement_line_id"))
        l_id = str(l.get("line_id"))
        if s_id in used_statement or l_id in used_ledger:
            continue
        used_statement.add(s_id)
        used_ledger.add(l_id)
        side, amount = _statement_side_amount(s)
        suggestions.append({
            "statement_line_id": s.get("statement_line_id"),
            "line_id": l.get("line_id"),
            "journal_id": l.get("journal_id"),
            "side": side,
            "amount": str(amount),
            "date_diff_days": diff,
            "confidence": "ref" if ref_hit else "amount_date",
            "statement": {"txn_date": s.get("txn_date"), "description": s.get("description"), "ref": s.get("ref")},
            "book": {"entry_date": l.get("entry_date"), "reference": l.get("reference"), "description": l.get("description")},
        })
    return suggestions


# --------------------------------------------------------------------------- #
# Reconciliation statement — pure assembly.
# --------------------------------------------------------------------------- #

def assemble_bank_reconciliation(
    *,
    account: dict,
    as_of: date,
    statement_lines: list[dict],
    ledger_lines: list[dict],
    matches: list[dict],
    suggestions: list[dict],
) -> dict:
    """Classify lines and compute the BRS identity:

        statement balance == book balance
                             + unmatched book credits   (issued, not presented)
                             - unmatched book debits    (deposits in transit)
                             + bank-only deposits       (not yet in books)
                             - bank-only withdrawals    (not yet in books)
    """
    matched_stmt_ids = {str(m.get("statement_line_id")) for m in matches}
    matched_line_ids = {str(m.get("line_id")) for m in matches}

    unmatched_stmt = [s for s in statement_lines if str(s.get("statement_line_id")) not in matched_stmt_ids]
    unmatched_book = [l for l in ledger_lines if str(l.get("line_id")) not in matched_line_ids]

    book_balance = Decimal("0.00")
    for l in ledger_lines:
        book_balance += _q2(l.get("debit") or 0) - _q2(l.get("credit") or 0)

    unmatched_book_debits = sum((_q2(l.get("debit") or 0) for l in unmatched_book), Decimal("0.00"))
    unmatched_book_credits = sum((_q2(l.get("credit") or 0) for l in unmatched_book), Decimal("0.00"))
    bank_only_deposits = sum((_q2(s.get("deposit") or 0) for s in unmatched_stmt), Decimal("0.00"))
    bank_only_withdrawals = sum((_q2(s.get("withdrawal") or 0) for s in unmatched_stmt), Decimal("0.00"))

    expected_statement_balance = (
        book_balance + unmatched_book_credits - unmatched_book_debits
        + bank_only_deposits - bank_only_withdrawals
    )

    # Last statement line (by date, then upload order) that carries a balance.
    statement_balance = None
    dated = [s for s in statement_lines if s.get("balance") not in (None, "")]
    if dated:
        dated.sort(key=lambda s: (str(s.get("txn_date") or ""), str(s.get("uploaded_at") or "")))
        statement_balance = _q2(dated[-1]["balance"])

    difference = (
        str(_q2(statement_balance - expected_statement_balance))
        if statement_balance is not None else None
    )

    return {
        "account": {
            "account_id": account.get("account_id"),
            "code": account.get("code"),
            "name": account.get("name"),
        },
        "as_of": as_of.isoformat(),
        "summary": {
            "book_balance": str(_q2(book_balance)),
            "statement_balance": str(statement_balance) if statement_balance is not None else None,
            "expected_statement_balance": str(_q2(expected_statement_balance)),
            "difference": difference,  # None when no statement balance column
            "matched_count": len(matches),
            "statement_lines_total": len(statement_lines),
            "book_lines_total": len(ledger_lines),
            "uncleared_withdrawals": str(_q2(unmatched_book_credits)),   # issued, not presented
            "deposits_in_transit": str(_q2(unmatched_book_debits)),
            "bank_only_deposits": str(_q2(bank_only_deposits)),
            "bank_only_withdrawals": str(_q2(bank_only_withdrawals)),
        },
        "matched": matches,
        "in_bank_not_in_books": unmatched_stmt,     # post these (charges/interest)
        "in_books_not_in_bank": unmatched_book,     # uncleared cheques / transit
        "suggestions": suggestions,
        "notes": [
            "Matching is metadata only — confirming a match never posts to the ledger.",
            "'In bank, not in books' lines usually need a voucher (bank charges, interest, direct credits).",
            "'In books, not in bank' lines are uncleared cheques or deposits in transit — they should clear on a later statement.",
            "Suggestions require an exact amount match within a "
            f"{SUGGEST_DATE_WINDOW_DAYS}-day date window and are never applied automatically.",
        ],
    }


# --------------------------------------------------------------------------- #
# Async service layer (Mongo + ledger I/O).
# --------------------------------------------------------------------------- #

def _scope(tenant_id: str, app_key: str, accounting_entity_id: str) -> dict:
    return {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}


async def upload_bank_statement(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    account_id: int,
    csv_text: str,
    created_by: str,
) -> dict:
    """Parse and store statement lines for a bank account. Re-uploading the
    same rows is a no-op (dedupe fingerprint), so monthly files can overlap."""
    from app.db.mongo import get_collection

    parsed = parse_bank_statement_csv(csv_text)
    col = get_collection(BANK_STATEMENT_LINES_COLLECTION)
    scope = _scope(tenant_id, app_key, accounting_entity_id)

    existing_keys = {
        row.get("dedupe_key")
        for row in await col.find({**scope, "account_id": account_id}, {"dedupe_key": 1}).to_list(length=20000)
    }
    batch_id = str(uuid4())
    now = _now()
    docs = []
    skipped = 0
    for line in parsed:
        key = statement_line_dedupe_key(line)
        if key in existing_keys:
            skipped += 1
            continue
        existing_keys.add(key)
        docs.append({
            **scope,
            "statement_line_id": str(uuid4()),
            "account_id": account_id,
            "batch_id": batch_id,
            "dedupe_key": key,
            **line,
            "uploaded_by": created_by,
            "uploaded_at": now,
        })
    if docs:
        await col.insert_many(docs)
    return {"inserted": len(docs), "skipped_duplicates": skipped, "parsed": len(parsed), "batch_id": batch_id}


async def _load_recon_state(scope: dict, account_id: int) -> tuple[list[dict], list[dict]]:
    from app.db.mongo import get_collection

    stmt_rows = await get_collection(BANK_STATEMENT_LINES_COLLECTION).find(
        {**scope, "account_id": account_id}
    ).sort("txn_date", 1).to_list(length=20000)
    match_rows = await get_collection(BANK_RECON_MATCHES_COLLECTION).find(
        {**scope, "account_id": account_id, "status": "active"}
    ).to_list(length=20000)
    for row in stmt_rows + match_rows:
        row.pop("_id", None)
        for key in ("uploaded_at", "created_at"):
            if isinstance(row.get(key), datetime):
                row[key] = row[key].isoformat()
    return stmt_rows, match_rows


async def build_bank_reconciliation(
    session,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    account_id: int,
    as_of: date | None = None,
) -> dict:
    from app.accounting.service import get_ledger_lines

    as_of = as_of or date.today()
    account, ledger_lines = await get_ledger_lines(
        session,
        tenant_id=tenant_id,
        account_id=account_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
    )
    ledger_view = [
        {
            "line_id": l["line_id"],
            "journal_id": l["journal_id"],
            "entry_date": l["entry_date"],
            "reference": l["reference"],
            "description": l["description"],
            "debit": str(_q2(l["debit"])),
            "credit": str(_q2(l["credit"])),
        }
        for l in ledger_lines
        if l.get("entry_date") and str(l["entry_date"])[:10] <= as_of.isoformat()
    ]

    scope = _scope(tenant_id, app_key, accounting_entity_id)
    stmt_rows, match_rows = await _load_recon_state(scope, account_id)
    stmt_rows = [s for s in stmt_rows if str(s.get("txn_date") or "")[:10] <= as_of.isoformat()]

    matched_stmt_ids = {str(m.get("statement_line_id")) for m in match_rows}
    matched_line_ids = {str(m.get("line_id")) for m in match_rows}
    suggestions = suggest_matches(
        [s for s in stmt_rows if str(s.get("statement_line_id")) not in matched_stmt_ids],
        [l for l in ledger_view if str(l.get("line_id")) not in matched_line_ids],
    )

    return assemble_bank_reconciliation(
        account={"account_id": account.id, "code": account.code, "name": account.name},
        as_of=as_of,
        statement_lines=stmt_rows,
        ledger_lines=ledger_view,
        matches=match_rows,
        suggestions=suggestions,
    )


async def create_bank_recon_match(
    session,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    account_id: int,
    statement_line_id: str,
    line_id: int,
    created_by: str,
) -> dict:
    """Confirm a statement-line <-> book-line match (amount/side must agree)."""
    from app.accounting.service import AccountingValidationError, get_ledger_lines
    from app.db.mongo import get_collection

    scope = _scope(tenant_id, app_key, accounting_entity_id)
    stmt_col = get_collection(BANK_STATEMENT_LINES_COLLECTION)
    match_col = get_collection(BANK_RECON_MATCHES_COLLECTION)

    stmt_line = await stmt_col.find_one({**scope, "account_id": account_id, "statement_line_id": statement_line_id})
    if stmt_line is None:
        raise AccountingValidationError("Statement line not found")
    if await match_col.find_one({**scope, "statement_line_id": statement_line_id, "status": "active"}):
        raise AccountingValidationError("Statement line is already matched")
    if await match_col.find_one({**scope, "line_id": line_id, "status": "active"}):
        raise AccountingValidationError("That book entry is already matched to another statement line")

    _, ledger_lines = await get_ledger_lines(
        session, tenant_id=tenant_id, account_id=account_id,
        app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    book_line = next((l for l in ledger_lines if l["line_id"] == line_id), None)
    if book_line is None:
        raise AccountingValidationError("Book entry not found on this bank account")

    s_side, s_amount = _statement_side_amount(stmt_line)
    l_side, l_amount = _ledger_side_amount({"debit": book_line["debit"], "credit": book_line["credit"]})
    if s_side != l_side or s_amount != l_amount:
        raise AccountingValidationError(
            f"Amounts do not agree: statement {s_side} {s_amount} vs book {l_side} {l_amount}"
        )

    doc = {
        **scope,
        "match_id": str(uuid4()),
        "account_id": account_id,
        "statement_line_id": statement_line_id,
        "line_id": line_id,
        "journal_id": book_line["journal_id"],
        "side": s_side,
        "amount": str(s_amount),
        "statement_txn_date": stmt_line.get("txn_date"),
        "book_entry_date": book_line.get("entry_date"),
        "status": "active",
        "created_by": created_by,
        "created_at": _now(),
    }
    await match_col.insert_one(doc)
    doc.pop("_id", None)
    doc["created_at"] = doc["created_at"].isoformat()
    return doc


async def reverse_bank_recon_match(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    match_id: str,
    reversed_by: str,
) -> dict:
    from app.accounting.service import AccountingNotFoundError, AccountingValidationError
    from app.db.mongo import get_collection

    scope = _scope(tenant_id, app_key, accounting_entity_id)
    match_col = get_collection(BANK_RECON_MATCHES_COLLECTION)
    row = await match_col.find_one({**scope, "match_id": match_id})
    if row is None:
        raise AccountingNotFoundError("Match not found")
    if row.get("status") != "active":
        raise AccountingValidationError("Match is already reversed")
    await match_col.update_one(
        {**scope, "match_id": match_id},
        {"$set": {"status": "reversed", "reversed_by": reversed_by, "reversed_at": _now()}},
    )
    return {"match_id": match_id, "status": "reversed"}
