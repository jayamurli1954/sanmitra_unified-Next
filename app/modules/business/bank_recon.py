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
import hashlib
import io
import logging
import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

logger = logging.getLogger(__name__)

BANK_STATEMENT_LINES_COLLECTION = "business_bank_statement_lines"
BANK_RECON_MATCHES_COLLECTION = "business_bank_recon_matches"
# One document per statement line / book line currently held by a match.
# The document `_id` encodes scope + line, so MongoDB's always-present unique
# `_id` index makes claiming a line atomic without any extra index setup.
# See docs/prd/MITRABOOKS_BANK_RECON_GAP_ANALYSIS.md (gap #14).
BANK_RECON_LINE_CLAIMS_COLLECTION = "business_bank_recon_line_claims"
# A claim whose owner never wrote any match rows (crash between claiming and
# saving) is treated as abandoned after this long and may be taken over.
CLAIM_STALE_AFTER_SECONDS = 300

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
    text = re.sub(r"[_\-]+", " ", str(name or "").strip().lower())
    return re.sub(r"\s+", " ", re.sub(r"[^a-z/. ]", "", text)).strip()


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
# Group matching — one statement line <-> several book lines (one_to_many), or
# several statement lines <-> one book line (many_to_one). Exact sums only.
# See docs/prd/MITRABOOKS_BANK_RECON_GAP_ANALYSIS.md (gap #1).
# --------------------------------------------------------------------------- #

# Hard limit on a confirmed group (server-side validation).
GROUP_MATCH_MAX_LINES = 10
# Suggestion search bounds — keep the subset-sum search cheap and predictable.
GROUP_SUGGEST_MAX_LINES = 4
GROUP_SUGGEST_MAX_CANDIDATES = 12
_GROUP_SUGGEST_MAX_STEPS = 20000
_GROUP_SUGGEST_MAX_SOLUTIONS = 25


def _find_exact_subsets(target: Decimal, amounts: list[Decimal], *, max_size: int) -> list[tuple[int, ...]]:
    """Index tuples (size >= 2, <= max_size) of `amounts` summing exactly to
    `target`. All amounts must be positive. Bounded by a step and solution cap
    so a pathological statement can never stall the reconciliation view."""
    order = sorted(range(len(amounts)), key=lambda i: amounts[i], reverse=True)
    values = [amounts[i] for i in order]
    solutions: list[tuple[int, ...]] = []
    steps = 0

    def dfs(start: int, remaining: Decimal, chosen: list[int]) -> bool:
        nonlocal steps
        if remaining == 0:
            if len(chosen) >= 2:
                solutions.append(tuple(sorted(order[i] for i in chosen)))
            return len(solutions) >= _GROUP_SUGGEST_MAX_SOLUTIONS
        slots = max_size - len(chosen)
        if slots <= 0:
            return False
        for i in range(start, len(values)):
            steps += 1
            if steps > _GROUP_SUGGEST_MAX_STEPS:
                return True
            # Values are sorted descending: if the largest `slots` values from
            # here cannot reach the target, nothing later can either.
            if sum(values[i:i + slots], Decimal("0")) < remaining:
                return False
            if values[i] > remaining:
                continue
            chosen.append(i)
            stop = dfs(i + 1, remaining - values[i], chosen)
            chosen.pop()
            if stop:
                return True
        return False

    dfs(0, target, [])
    return solutions


def _brief_statement(s: dict) -> dict:
    side, amount = _statement_side_amount(s)
    return {
        "statement_line_id": s.get("statement_line_id"),
        "txn_date": s.get("txn_date"),
        "description": s.get("description"),
        "ref": s.get("ref"),
        "amount": str(amount),
    }


def _brief_book(l: dict) -> dict:
    side, amount = _ledger_side_amount(l)
    return {
        "line_id": l.get("line_id"),
        "journal_id": l.get("journal_id"),
        "entry_date": l.get("entry_date"),
        "reference": l.get("reference"),
        "description": l.get("description"),
        "amount": str(amount),
    }


def _group_pass(
    singles: list[dict],
    pool: list[dict],
    *,
    single_side_amount,
    pool_side_amount,
    single_id,
    pool_id,
    single_date,
    pool_date,
    used_singles: set[str],
    used_pool: set[str],
    date_window_days: int,
) -> list[tuple[dict, list[dict], int, bool]]:
    """For each single line, find a subset of pool lines (same side, within the
    date window, each strictly smaller) summing exactly to it. Greedy: a line
    is used in at most one suggestion. Returns (single, members, max_diff, ambiguous)."""
    found = []
    for single in sorted(singles, key=lambda x: (str(single_date(x) or ""), str(single_id(x)))):
        sid = str(single_id(single))
        if sid in used_singles:
            continue
        side, target = single_side_amount(single)
        if target <= 0:
            continue
        candidates = []
        for p in pool:
            pid = str(pool_id(p))
            if pid in used_pool:
                continue
            p_side, p_amount = pool_side_amount(p)
            if p_side != side or p_amount <= 0 or p_amount >= target:
                continue
            diff = _date_diff_days(single_date(single), pool_date(p))
            if diff is None or diff > date_window_days:
                continue
            candidates.append((diff, pid, p, p_amount))
        if len(candidates) < 2:
            continue
        candidates.sort(key=lambda c: (c[0], c[1]))
        candidates = candidates[:GROUP_SUGGEST_MAX_CANDIDATES]
        subsets = _find_exact_subsets(target, [c[3] for c in candidates], max_size=GROUP_SUGGEST_MAX_LINES)
        if not subsets:
            continue
        # Fewest lines first, then tightest dates, then deterministic by ids.
        ranked = sorted(
            subsets,
            key=lambda idx: (len(idx), max(candidates[i][0] for i in idx), sum(candidates[i][0] for i in idx), [candidates[i][1] for i in idx]),
        )
        best = ranked[0]
        members = [candidates[i][2] for i in best]
        max_diff = max(candidates[i][0] for i in best)
        used_singles.add(sid)
        used_pool.update(str(pool_id(m)) for m in members)
        found.append((single, members, max_diff, len(subsets) > 1))
    return found


def suggest_group_matches(
    statement_lines: list[dict],
    ledger_lines: list[dict],
    *,
    date_window_days: int = SUGGEST_DATE_WINDOW_DAYS,
    exclude_statement_ids: set[str] | None = None,
    exclude_line_ids: set[str] | None = None,
) -> list[dict]:
    """Exact-sum group suggestions over unmatched lines. Run AFTER the 1:1
    pass and pass its picks in `exclude_*` so a line is never offered twice.

    Pass 1 (one_to_many): one statement line = sum of several book lines
            (deposit slip / UPI settlement / bulk NEFT payout).
    Pass 2 (many_to_one): one book line = sum of several statement lines
            (a payment the bank split into several debits).

    `confidence` is "ambiguous" when more than one distinct subset fits —
    the accountant should check which receipts the bank actually combined.
    Never auto-applies."""
    used_stmt = {str(x) for x in (exclude_statement_ids or set())}
    used_book = {str(x) for x in (exclude_line_ids or set())}
    suggestions: list[dict] = []

    one_to_many = _group_pass(
        statement_lines, ledger_lines,
        single_side_amount=_statement_side_amount, pool_side_amount=_ledger_side_amount,
        single_id=lambda s: s.get("statement_line_id"), pool_id=lambda l: l.get("line_id"),
        single_date=lambda s: s.get("txn_date"), pool_date=lambda l: l.get("entry_date"),
        used_singles=used_stmt, used_pool=used_book, date_window_days=date_window_days,
    )
    for s, members, max_diff, ambiguous in one_to_many:
        side, amount = _statement_side_amount(s)
        suggestions.append({
            "group_type": "one_to_many",
            "side": side,
            "amount": str(amount),
            "statement_line_ids": [s.get("statement_line_id")],
            "line_ids": [m.get("line_id") for m in members],
            "max_date_diff_days": max_diff,
            "confidence": "ambiguous" if ambiguous else "exact_sum",
            "statement": [_brief_statement(s)],
            "book": [_brief_book(m) for m in members],
        })

    many_to_one = _group_pass(
        ledger_lines, statement_lines,
        single_side_amount=_ledger_side_amount, pool_side_amount=_statement_side_amount,
        single_id=lambda l: l.get("line_id"), pool_id=lambda s: s.get("statement_line_id"),
        single_date=lambda l: l.get("entry_date"), pool_date=lambda s: s.get("txn_date"),
        used_singles=used_book, used_pool=used_stmt, date_window_days=date_window_days,
    )
    for l, members, max_diff, ambiguous in many_to_one:
        side, amount = _ledger_side_amount(l)
        suggestions.append({
            "group_type": "many_to_one",
            "side": side,
            "amount": str(amount),
            "statement_line_ids": [m.get("statement_line_id") for m in members],
            "line_ids": [l.get("line_id")],
            "max_date_diff_days": max_diff,
            "confidence": "ambiguous" if ambiguous else "exact_sum",
            "statement": [_brief_statement(m) for m in members],
            "book": [_brief_book(l)],
        })
    return suggestions


def validate_group_match(statement_lines: list[dict], book_lines: list[dict]) -> tuple[str, str, Decimal]:
    """Pure validation of a proposed group. Returns (group_type, side, amount)
    or raises ValueError. Exactly one side must hold a single line; the other
    2..GROUP_MATCH_MAX_LINES lines; same direction; exact totals."""
    n_s, n_b = len(statement_lines), len(book_lines)
    if n_s == 0 or n_b == 0:
        raise ValueError("Select at least one statement line and one book entry")
    if n_s == 1 and n_b == 1:
        raise ValueError("Use a single match for one statement line and one book entry")
    if n_s > 1 and n_b > 1:
        raise ValueError("Many-to-many is not supported — split it into groups with one line on one side")
    if max(n_s, n_b) > GROUP_MATCH_MAX_LINES:
        raise ValueError(f"A group can contain at most {GROUP_MATCH_MAX_LINES} lines on one side")

    sides = {_statement_side_amount(s)[0] for s in statement_lines} | {_ledger_side_amount(l)[0] for l in book_lines}
    if len(sides) != 1:
        raise ValueError("All lines must be in the same direction (deposits with book debits, withdrawals with book credits)")
    side = sides.pop()
    if any(_statement_side_amount(s)[1] <= 0 for s in statement_lines) or any(_ledger_side_amount(l)[1] <= 0 for l in book_lines):
        raise ValueError("Every line must carry a non-zero amount")

    stmt_total = sum((_statement_side_amount(s)[1] for s in statement_lines), Decimal("0.00"))
    book_total = sum((_ledger_side_amount(l)[1] for l in book_lines), Decimal("0.00"))
    if stmt_total != book_total:
        raise ValueError(
            f"Totals do not agree: statement {side} {_q2(stmt_total)} vs book {_q2(book_total)} "
            f"(difference {_q2(stmt_total - book_total)})"
        )
    group_type = "one_to_many" if n_s == 1 else "many_to_one"
    return group_type, side, _q2(stmt_total)


# --------------------------------------------------------------------------- #
# Match with a difference — the bank amount differs from the books by bank
# charges, MDR, TDS or rounding. The difference is posted as a typed voucher
# on the bank account (normal approval path); the match only becomes active
# once that voucher is posted, and then includes the voucher's bank line.
# See docs/prd/MITRABOOKS_BANK_RECON_GAP_ANALYSIS.md (gap #3).
# --------------------------------------------------------------------------- #

# Suggestion tolerance: the difference must be within BOTH limits. Manual
# matches may exceed them (TDS at 10% is legitimate) — the voucher approval
# is the control there.
DIFFERENCE_SUGGEST_MAX_ABS = Decimal("1000.00")
DIFFERENCE_SUGGEST_MAX_PCT = Decimal("2.5")  # percent of the book amount

MATCH_STATUS_ACTIVE = "active"
MATCH_STATUS_PENDING = "pending_adjustment"
# Statuses that hold a line: neither may be matched again while either applies.
LIVE_MATCH_STATUSES = [MATCH_STATUS_ACTIVE, MATCH_STATUS_PENDING]

_DIFFERENCE_HINTS = {
    "bank_deducted": "Bank credited less than booked: bank charges, card/UPI MDR or TDS deducted?",
    "bank_charged": "Bank debited more than booked: transfer charges and GST on them?",
    "bank_excess": "Bank shows more in your favour than booked: interest, cashback or rounding?",
}


def _difference_hint(side: str, bank_entry: str) -> str:
    if bank_entry == "debit":
        return "bank_excess"
    return "bank_deducted" if side == "deposit" else "bank_charged"


def plan_difference_adjustment(statement_lines: list[dict], book_lines: list[dict]) -> dict:
    """Pure: work out the adjustment that makes a near-match balance.

    Returns {group_type, side, statement_total, book_total, difference,
    bank_entry, hint, hint_text}. `bank_entry` is the side of the BANK account
    the adjustment voucher must hit: "credit" when the bank holds less money
    than the books say (charges deducted), "debit" when it holds more.
    Raises ValueError when the selection is not a valid near-match."""
    n_s, n_b = len(statement_lines), len(book_lines)
    if n_s == 0 or n_b == 0:
        raise ValueError("Select at least one statement line and one book entry")
    if n_s > 1 and n_b > 1:
        raise ValueError("Many-to-many is not supported — split it into groups with one line on one side")
    if max(n_s, n_b) > GROUP_MATCH_MAX_LINES:
        raise ValueError(f"A group can contain at most {GROUP_MATCH_MAX_LINES} lines on one side")

    sides = {_statement_side_amount(s)[0] for s in statement_lines} | {_ledger_side_amount(l)[0] for l in book_lines}
    if len(sides) != 1:
        raise ValueError("All lines must be in the same direction (deposits with book debits, withdrawals with book credits)")
    side = sides.pop()
    if any(_statement_side_amount(s)[1] <= 0 for s in statement_lines) or any(_ledger_side_amount(l)[1] <= 0 for l in book_lines):
        raise ValueError("Every line must carry a non-zero amount")

    stmt_total = sum((_statement_side_amount(s)[1] for s in statement_lines), Decimal("0.00"))
    book_total = sum((_ledger_side_amount(l)[1] for l in book_lines), Decimal("0.00"))
    sign = Decimal("1") if side == "deposit" else Decimal("-1")
    # Signed effect on the bank balance: statement view minus book view.
    net_difference = sign * stmt_total - sign * book_total
    if net_difference == 0:
        raise ValueError("Totals already agree — use a normal match instead")
    difference = abs(net_difference)
    if difference >= min(stmt_total, book_total):
        raise ValueError(
            f"The difference ({_q2(difference)}) is not smaller than the amounts being matched — "
            "these lines are probably not the same transaction"
        )
    bank_entry = "debit" if net_difference > 0 else "credit"
    hint = _difference_hint(side, bank_entry)
    if n_s == 1 and n_b == 1:
        group_type = "one_to_one"
    else:
        group_type = "one_to_many" if n_s == 1 else "many_to_one"
    return {
        "group_type": group_type,
        "side": side,
        "statement_total": _q2(stmt_total),
        "book_total": _q2(book_total),
        "difference": _q2(difference),
        "bank_entry": bank_entry,
        "hint": hint,
        "hint_text": _DIFFERENCE_HINTS[hint],
    }


def _within_difference_tolerance(difference: Decimal, book_amount: Decimal) -> bool:
    if difference <= 0 or book_amount <= 0:
        return False
    return difference <= DIFFERENCE_SUGGEST_MAX_ABS and difference * 100 <= book_amount * DIFFERENCE_SUGGEST_MAX_PCT


def suggest_difference_matches(
    statement_lines: list[dict],
    ledger_lines: list[dict],
    *,
    date_window_days: int = SUGGEST_DATE_WINDOW_DAYS,
    exclude_statement_ids: set[str] | None = None,
    exclude_line_ids: set[str] | None = None,
) -> list[dict]:
    """One-to-one near-matches: same direction, dates within the window, and
    an amount difference within DIFFERENCE_SUGGEST_MAX_ABS and
    DIFFERENCE_SUGGEST_MAX_PCT of the book amount. Run AFTER the exact 1:1
    and group passes (pass their picks in `exclude_*`). Smallest difference
    wins, then closest date; each line is suggested at most once. The
    accountant must still pick the offset account and confirm."""
    used_stmt = {str(x) for x in (exclude_statement_ids or set())}
    used_book = {str(x) for x in (exclude_line_ids or set())}
    candidates: list[tuple] = []
    for s in statement_lines:
        s_id = str(s.get("statement_line_id"))
        if s_id in used_stmt:
            continue
        s_side, s_amount = _statement_side_amount(s)
        if s_amount <= 0:
            continue
        for l in ledger_lines:
            l_id = str(l.get("line_id"))
            if l_id in used_book:
                continue
            l_side, l_amount = _ledger_side_amount(l)
            if l_side != s_side or l_amount == s_amount:
                continue
            difference = abs(s_amount - l_amount)
            if not _within_difference_tolerance(difference, l_amount):
                continue
            diff_days = _date_diff_days(s.get("txn_date"), l.get("entry_date"))
            if diff_days is None or diff_days > date_window_days:
                continue
            candidates.append((difference, diff_days, s_id, l_id, s, l))

    candidates.sort(key=lambda c: (c[0], c[1], c[2], c[3]))
    suggestions: list[dict] = []
    for difference, diff_days, s_id, l_id, s, l in candidates:
        if s_id in used_stmt or l_id in used_book:
            continue
        used_stmt.add(s_id)
        used_book.add(l_id)
        plan = plan_difference_adjustment([s], [l])
        suggestions.append({
            "statement_line_id": s.get("statement_line_id"),
            "line_id": l.get("line_id"),
            "side": plan["side"],
            "statement_amount": str(plan["statement_total"]),
            "book_amount": str(plan["book_total"]),
            "difference": str(plan["difference"]),
            "bank_entry": plan["bank_entry"],
            "hint": plan["hint"],
            "hint_text": plan["hint_text"],
            "date_diff_days": diff_days,
            "statement": _brief_statement(s),
            "book": _brief_book(l),
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
    group_suggestions: list[dict] | None = None,
    difference_suggestions: list[dict] | None = None,
    pending_differences: list[dict] | None = None,
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
            "matched_groups": len({str(m.get("match_group_id")) for m in matches if m.get("match_group_id")}),
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
        "group_suggestions": group_suggestions or [],
        "difference_suggestions": difference_suggestions or [],
        "pending_differences": pending_differences or [],
        "notes": [
            "Matching is metadata only — confirming a match never posts to the ledger.",
            "'In bank, not in books' lines usually need a voucher (bank charges, interest, direct credits).",
            "'In books, not in bank' lines are uncleared cheques or deposits in transit — they should clear on a later statement.",
            (
                "Suggestions require an exact amount match within a "
                f"{SUGGEST_DATE_WINDOW_DAYS}-day date window and are never applied automatically."
            ),
            (
                "Group suggestions pair one line with several on the other side whose amounts sum exactly; "
                "unmatching any line of a group unmatches the whole group."
            ),
            (
                "Near-matches (bank charges, MDR, TDS, rounding) post the difference as a voucher through "
                f"approval; they are suggested only within {DIFFERENCE_SUGGEST_MAX_PCT}% and "
                f"{DIFFERENCE_SUGGEST_MAX_ABS} of the book amount, and count as matched only once the voucher is posted."
            ),
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

    result = {"inserted": len(docs), "skipped_duplicates": skipped, "parsed": len(parsed), "batch_id": batch_id}

    # Bank-feed policy (MITRABOOKS_BANK_FEED_POLICY.md): every import must record an
    # audit event with actor, account, provider, and inserted/duplicate counts.
    # Best-effort so an audit-store hiccup never drops already-stored statement lines.
    try:
        from app.core.audit.service import log_audit_event

        await log_audit_event(
            tenant_id=tenant_id,
            user_id=created_by,
            product=app_key,
            action="business_bank_statement_imported",
            entity_type="business_bank_statement_import",
            entity_id=f"{accounting_entity_id}:{account_id}:{batch_id}",
            new_value={
                "account_id": account_id,
                "provider": "csv",
                "parsed": len(parsed),
                "inserted": len(docs),
                "skipped_duplicates": skipped,
                "batch_id": batch_id,
            },
        )
    except Exception:
        pass

    return result


async def _load_pending_difference_rows(scope: dict, account_id: int) -> list[dict]:
    from app.db.mongo import get_collection

    rows = await get_collection(BANK_RECON_MATCHES_COLLECTION).find(
        {**scope, "account_id": account_id, "status": MATCH_STATUS_PENDING}
    ).to_list(length=20000)
    for row in rows:
        row.pop("_id", None)
        if isinstance(row.get("created_at"), datetime):
            row["created_at"] = row["created_at"].isoformat()
    return rows


def summarize_pending_differences(rows: list[dict]) -> list[dict]:
    """Collapse pending difference rows into one entry per group for the UI."""
    groups: dict[str, dict] = {}
    for row in rows:
        gid = str(row.get("match_group_id"))
        g = groups.setdefault(gid, {
            "match_group_id": gid,
            "match_id": row.get("match_id"),
            "side": row.get("side"),
            "statement_total": row.get("group_amount"),
            "book_total": row.get("book_total"),
            "difference": row.get("difference_amount"),
            "bank_entry": row.get("difference_bank_entry"),
            "hint": row.get("difference_hint"),
            "adjustment_voucher_id": row.get("adjustment_voucher_id"),
            "statement_line_ids": [],
            "line_ids": [],
        })
        if row.get("statement_line_id") not in g["statement_line_ids"]:
            g["statement_line_ids"].append(row.get("statement_line_id"))
        if row.get("line_id") not in g["line_ids"]:
            g["line_ids"].append(row.get("line_id"))
    return list(groups.values())


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
    # Lines held by a pending difference match stay unmatched in the BRS
    # (their voucher is not posted yet) but are never suggested again.
    pending_rows = await _load_pending_difference_rows(scope, account_id)
    held_stmt_ids = matched_stmt_ids | {str(m.get("statement_line_id")) for m in pending_rows}
    held_line_ids = matched_line_ids | {str(m.get("line_id")) for m in pending_rows}
    open_stmt = [s for s in stmt_rows if str(s.get("statement_line_id")) not in held_stmt_ids]
    open_book = [l for l in ledger_view if str(l.get("line_id")) not in held_line_ids]
    suggestions = suggest_matches(open_stmt, open_book)
    taken_stmt = {str(g.get("statement_line_id")) for g in suggestions}
    taken_book = {str(g.get("line_id")) for g in suggestions}
    group_suggestions = suggest_group_matches(
        open_stmt,
        open_book,
        exclude_statement_ids=taken_stmt,
        exclude_line_ids=taken_book,
    )
    for g in group_suggestions:
        taken_stmt.update(str(x) for x in g["statement_line_ids"])
        taken_book.update(str(x) for x in g["line_ids"])
    difference_suggestions = suggest_difference_matches(
        open_stmt,
        open_book,
        exclude_statement_ids=taken_stmt,
        exclude_line_ids=taken_book,
    )

    return assemble_bank_reconciliation(
        account={"account_id": account.id, "code": account.code, "name": account.name},
        as_of=as_of,
        statement_lines=stmt_rows,
        ledger_lines=ledger_view,
        matches=match_rows,
        suggestions=suggestions,
        group_suggestions=group_suggestions,
        difference_suggestions=difference_suggestions,
        pending_differences=summarize_pending_differences(pending_rows),
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
    if await match_col.find_one({**scope, "statement_line_id": statement_line_id, "status": {"$in": LIVE_MATCH_STATUSES}}):
        raise AccountingValidationError("Statement line is already matched")
    if await match_col.find_one({**scope, "line_id": line_id, "status": {"$in": LIVE_MATCH_STATUSES}}):
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
    await claim_bank_recon_lines(
        scope, owner_id=doc["match_id"], account_id=account_id,
        statement_line_ids=[statement_line_id], line_ids=[line_id],
    )
    try:
        await match_col.insert_one(doc)
    except Exception:
        await release_bank_recon_claims(scope, doc["match_id"])
        raise
    doc.pop("_id", None)
    doc["created_at"] = doc["created_at"].isoformat()
    return doc


def _claim_id(scope: dict, kind: str, key) -> str:
    return "|".join([
        "bankrecon", str(scope["tenant_id"]), str(scope["app_key"]),
        str(scope["accounting_entity_id"]), kind, str(key),
    ])


async def _claim_is_abandoned(scope: dict, claim: dict) -> bool:
    from app.db.mongo import get_collection

    claimed_at = claim.get("claimed_at")
    if isinstance(claimed_at, str):
        try:
            claimed_at = datetime.fromisoformat(claimed_at)
        except ValueError:
            claimed_at = None
    if not isinstance(claimed_at, datetime):
        return False
    if claimed_at.tzinfo is None:
        claimed_at = claimed_at.replace(tzinfo=timezone.utc)
    if (_now() - claimed_at).total_seconds() < CLAIM_STALE_AFTER_SECONDS:
        return False
    owner = claim.get("owner_id")
    match_col = get_collection(BANK_RECON_MATCHES_COLLECTION)
    for field in ("match_group_id", "match_id"):
        if await match_col.find_one({**scope, field: owner, "status": {"$in": LIVE_MATCH_STATUSES}}):
            return False
    return True


async def claim_bank_recon_lines(
    scope: dict,
    *,
    owner_id: str,
    account_id: int,
    statement_line_ids: list[str] = (),
    line_ids: list[int] = (),
) -> None:
    """Atomically reserve lines for one match/group (`owner_id`).

    Each line gets a claim document whose `_id` is derived from scope + line,
    so two requests racing for the same line cannot both succeed: the second
    insert hits the `_id` unique index. On any conflict the claims this call
    already made are rolled back and AccountingValidationError is raised."""
    from pymongo.errors import DuplicateKeyError

    from app.accounting.service import AccountingValidationError
    from app.db.mongo import get_collection

    col = get_collection(BANK_RECON_LINE_CLAIMS_COLLECTION)
    wanted = [("stmt", str(x)) for x in statement_line_ids] + [("book", str(x)) for x in line_ids]
    taken: list[str] = []
    now = _now()
    try:
        for kind, key in wanted:
            doc = {
                "_id": _claim_id(scope, kind, key),
                **scope,
                "account_id": account_id,
                "kind": kind,
                "key": key,
                "owner_id": owner_id,
                "claimed_at": now,
            }
            try:
                await col.insert_one(dict(doc))
            except DuplicateKeyError:
                existing = await col.find_one({"_id": doc["_id"]})
                if existing is None or not await _claim_is_abandoned(scope, existing):
                    raise
                await col.delete_many({"_id": doc["_id"], "owner_id": existing.get("owner_id")})
                await col.insert_one(dict(doc))
            taken.append(doc["_id"])
    except DuplicateKeyError as exc:
        if taken:
            await col.delete_many({"_id": {"$in": taken}})
        raise AccountingValidationError(
            "A selected line was just matched by someone else — reload the reconciliation and try again"
        ) from exc


async def release_bank_recon_claims(scope: dict, owner_id: str) -> None:
    from app.db.mongo import get_collection

    await get_collection(BANK_RECON_LINE_CLAIMS_COLLECTION).delete_many({**scope, "owner_id": owner_id})


async def _load_match_selection(
    session,
    *,
    scope: dict,
    account_id: int,
    statement_line_ids: list[str],
    line_ids: list[int],
) -> tuple[list[dict], list[dict]]:
    """Load and check a user's selection for a group / difference match:
    no duplicates, every line in scope on this bank account, none already
    held by an active or pending match. Returns lines in selection order."""
    from app.accounting.service import AccountingValidationError, get_ledger_lines
    from app.db.mongo import get_collection

    stmt_ids = [str(x).strip() for x in (statement_line_ids or []) if str(x).strip()]
    book_ids = [int(x) for x in (line_ids or []) if int(x) > 0]
    if len(set(stmt_ids)) != len(stmt_ids) or len(set(book_ids)) != len(book_ids):
        raise AccountingValidationError("Duplicate line in the selection")
    if not stmt_ids or not book_ids:
        raise AccountingValidationError("Select at least one statement line and one book entry")

    stmt_col = get_collection(BANK_STATEMENT_LINES_COLLECTION)
    match_col = get_collection(BANK_RECON_MATCHES_COLLECTION)
    stmt_rows = await stmt_col.find(
        {**scope, "account_id": account_id, "statement_line_id": {"$in": stmt_ids}}
    ).to_list(length=len(stmt_ids) + 1)
    by_stmt_id = {str(r.get("statement_line_id")): r for r in stmt_rows}
    missing = [x for x in stmt_ids if x not in by_stmt_id]
    if missing:
        raise AccountingValidationError(f"Statement line not found: {', '.join(missing)}")

    if await match_col.find_one({**scope, "statement_line_id": {"$in": stmt_ids}, "status": {"$in": LIVE_MATCH_STATUSES}}):
        raise AccountingValidationError("A selected statement line is already matched")
    if await match_col.find_one({**scope, "line_id": {"$in": book_ids}, "status": {"$in": LIVE_MATCH_STATUSES}}):
        raise AccountingValidationError("A selected book entry is already matched")

    _, ledger_lines = await get_ledger_lines(
        session, tenant_id=scope["tenant_id"], account_id=account_id,
        app_key=scope["app_key"], accounting_entity_id=scope["accounting_entity_id"],
    )
    by_line_id = {l["line_id"]: l for l in ledger_lines}
    missing_book = [str(x) for x in book_ids if x not in by_line_id]
    if missing_book:
        raise AccountingValidationError(f"Book entry not found on this bank account: {', '.join(missing_book)}")
    return [by_stmt_id[x] for x in stmt_ids], [by_line_id[x] for x in book_ids]


async def create_bank_recon_group_match(
    session,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    account_id: int,
    statement_line_ids: list[str],
    line_ids: list[int],
    created_by: str,
) -> dict:
    """Confirm a one-to-many or many-to-one match. Metadata only — writes one
    match row per pair sharing a `match_group_id`, so every existing reader
    that keys on scalar statement_line_id / line_id keeps working."""
    from app.accounting.service import AccountingValidationError
    from app.db.mongo import get_collection

    scope = _scope(tenant_id, app_key, accounting_entity_id)
    match_col = get_collection(BANK_RECON_MATCHES_COLLECTION)
    ordered_stmt, ordered_book = await _load_match_selection(
        session, scope=scope, account_id=account_id,
        statement_line_ids=statement_line_ids, line_ids=line_ids,
    )
    try:
        group_type, side, group_amount = validate_group_match(
            ordered_stmt,
            [{"debit": l["debit"], "credit": l["credit"]} for l in ordered_book],
        )
    except ValueError as exc:
        raise AccountingValidationError(str(exc)) from exc

    group_id = str(uuid4())
    now = _now()
    group_size = len(ordered_stmt) + len(ordered_book)
    pairs = (
        [(ordered_stmt[0], b) for b in ordered_book]
        if group_type == "one_to_many"
        else [(s, ordered_book[0]) for s in ordered_stmt]
    )
    docs = []
    for s, b in pairs:
        # Each row carries its own share so summing active rows never double counts.
        share = (
            _ledger_side_amount({"debit": b["debit"], "credit": b["credit"]})[1]
            if group_type == "one_to_many"
            else _statement_side_amount(s)[1]
        )
        docs.append({
            **scope,
            "match_id": str(uuid4()),
            "match_group_id": group_id,
            "group_type": group_type,
            "group_size": group_size,
            "group_amount": str(group_amount),
            "account_id": account_id,
            "statement_line_id": s.get("statement_line_id"),
            "line_id": b["line_id"],
            "journal_id": b["journal_id"],
            "side": side,
            "amount": str(_q2(share)),
            "statement_txn_date": s.get("txn_date"),
            "book_entry_date": b.get("entry_date"),
            "status": "active",
            "created_by": created_by,
            "created_at": now,
        })
    await claim_bank_recon_lines(
        scope, owner_id=group_id, account_id=account_id,
        statement_line_ids=[s.get("statement_line_id") for s in ordered_stmt],
        line_ids=[b["line_id"] for b in ordered_book],
    )
    try:
        await match_col.insert_many(docs)
    except Exception:
        await release_bank_recon_claims(scope, group_id)
        raise
    for doc in docs:
        doc.pop("_id", None)
        doc["created_at"] = now.isoformat()
    return {
        "match_group_id": group_id,
        "group_type": group_type,
        "side": side,
        "amount": str(group_amount),
        "status": "active",
        "matches": docs,
    }


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
    if row.get("status") not in LIVE_MATCH_STATUSES:
        raise AccountingValidationError("Match is already reversed")
    reversal = {"status": "reversed", "reversed_by": reversed_by, "reversed_at": _now()}
    group_id = row.get("match_group_id")
    if group_id:
        # A group is all-or-nothing: unmatching one row unmatches every row,
        # so a statement line is never left partially matched.
        result = await match_col.update_many(
            {**scope, "match_group_id": group_id, "status": {"$in": LIVE_MATCH_STATUSES}},
            {"$set": reversal},
        )
        await release_bank_recon_claims(scope, group_id)
        out = {
            "match_id": match_id,
            "status": "reversed",
            "match_group_id": group_id,
            "reversed_rows": int(getattr(result, "modified_count", 0) or 0),
        }
        if row.get("adjustment_voucher_id"):
            # Unmatching is metadata only: the difference voucher is a real
            # accounting entry and stays as it is.
            out["adjustment_voucher_id"] = row.get("adjustment_voucher_id")
            out["note"] = (
                "The difference voucher was not reversed. Reject it (if still pending) or reverse it "
                "from Vouchers if it is no longer needed; otherwise its bank line can be matched again."
            )
        return out
    await match_col.update_one({**scope, "match_id": match_id}, {"$set": reversal})
    await release_bank_recon_claims(scope, match_id)
    return {"match_id": match_id, "status": "reversed"}


async def _post_bank_voucher(
    session,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    bank_account_id: int,
    bank_entry: str,
    amount: Decimal,
    offset_account_id: int | None,
    offset_account_code: str | None,
    entry_date: date,
    description: str,
    reference: str,
    approve: bool,
    approval_note: str,
    created_by: str,
    idempotency_key: str,
) -> dict:
    """Create a journal voucher between the bank account and an offset
    account, through the normal typed-voucher path. `bank_entry` is "debit"
    (money into the bank) or "credit" (money out). When `approve` is true the
    voucher is approved straight away; otherwise it waits in the approval
    queue. Never writes journal rows directly."""
    from app.modules.business.schemas import ApprovalReviewRequest, TypedVoucherCreateRequest
    from app.modules.business.service import post_typed_voucher, review_typed_voucher

    if bank_entry == "debit":
        debit_account_id, debit_account_code = bank_account_id, None
        credit_account_id, credit_account_code = offset_account_id, offset_account_code
    else:
        debit_account_id, debit_account_code = offset_account_id, offset_account_code
        credit_account_id, credit_account_code = bank_account_id, None

    voucher = await post_typed_voucher(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        created_by=created_by,
        payload=TypedVoucherCreateRequest(
            voucher_type="journal",
            entry_date=entry_date,
            amount=amount,
            debit_account_id=debit_account_id,
            credit_account_id=credit_account_id,
            debit_account_code=debit_account_code,
            credit_account_code=credit_account_code,
            description=description,
            reference=reference,
            accounting_entity_id=accounting_entity_id,
        ),
        idempotency_key=idempotency_key,
    )
    # Only a voucher still waiting for approval can be approved here; a
    # rejected one (returned again by its idempotency key) is handed back as is.
    if approve and str(voucher.get("status") or "").lower() == "pending_approval":
        voucher = await review_typed_voucher(
            session=session,
            tenant_id=tenant_id,
            app_key=app_key,
            voucher_id=voucher["voucher_id"],
            reviewed_by=created_by,
            payload=ApprovalReviewRequest(
                approve=True,
                notes=approval_note,
                accounting_entity_id=accounting_entity_id,
            ),
        )
    return voucher


async def post_bank_statement_line_voucher(
    session,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    account_id: int,
    statement_line_id: str,
    offset_account_id: int | None,
    offset_account_code: str | None,
    description: str | None,
    reference: str | None,
    approve: bool,
    created_by: str,
    idempotency_key: str | None,
) -> dict:
    """Create a typed voucher for a bank-only statement line.

    A statement withdrawal credits the bank account and debits the chosen
    offset account. A statement deposit debits the bank account and credits
    the chosen offset account. Posting is still routed through the normal
    voucher approval path; this function never writes journal rows directly.
    """
    from app.accounting.service import AccountingValidationError
    from app.db.mongo import get_collection

    if not offset_account_id and not offset_account_code:
        raise AccountingValidationError("Offset account is required")

    scope = _scope(tenant_id, app_key, accounting_entity_id)
    stmt_col = get_collection(BANK_STATEMENT_LINES_COLLECTION)
    match_col = get_collection(BANK_RECON_MATCHES_COLLECTION)
    stmt_line = await stmt_col.find_one({**scope, "account_id": account_id, "statement_line_id": statement_line_id})
    if stmt_line is None:
        raise AccountingValidationError("Statement line not found")
    if await match_col.find_one({**scope, "statement_line_id": statement_line_id, "status": {"$in": LIVE_MATCH_STATUSES}}):
        raise AccountingValidationError("Statement line is already matched")
    if stmt_line.get("posted_voucher_id"):
        raise AccountingValidationError("Statement line already has a voucher")

    side, amount = _statement_side_amount(stmt_line)
    if amount <= 0:
        raise AccountingValidationError("Statement line has no amount to post")

    txn_date = date.fromisoformat(str(stmt_line.get("txn_date") or "")[:10])
    line_ref = str(reference or stmt_line.get("ref") or f"BANK-{statement_line_id}").strip()
    narration = str(description or stmt_line.get("description") or "Bank statement line").strip()
    voucher = await _post_bank_voucher(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        bank_account_id=account_id,
        bank_entry="debit" if side == "deposit" else "credit",
        amount=amount,
        offset_account_id=offset_account_id,
        offset_account_code=offset_account_code,
        entry_date=txn_date,
        description=narration,
        reference=line_ref,
        approve=approve,
        approval_note=f"Posted from bank statement line {statement_line_id}",
        created_by=created_by,
        idempotency_key=idempotency_key or f"bank-statement-voucher:{statement_line_id}",
    )

    posting_status = "posted" if str(voucher.get("status") or "").lower() == "posted" else "pending_approval"
    await stmt_col.update_one(
        {**scope, "account_id": account_id, "statement_line_id": statement_line_id, "posted_voucher_id": {"$exists": False}},
        {
            "$set": {
                "posted_voucher_id": voucher.get("voucher_id"),
                "posted_journal_entry_id": voucher.get("journal_entry_id"),
                "posting_status": posting_status,
                "posted_by": created_by,
                "posted_at": _now(),
            }
        },
    )
    match = None
    if posting_status == "posted" and voucher.get("journal_entry_id"):
        match = await _auto_match_statement_voucher(
            session,
            scope=scope,
            account_id=account_id,
            stmt_line=stmt_line,
            journal_entry_id=voucher["journal_entry_id"],
            voucher_id=voucher.get("voucher_id"),
            created_by=created_by,
        )
    return {
        "statement_line_id": statement_line_id,
        "posting_status": posting_status,
        "voucher": voucher,
        "match": match,
    }


async def _auto_match_statement_voucher(
    session,
    *,
    scope: dict,
    account_id: int,
    stmt_line: dict,
    journal_entry_id,
    voucher_id: str | None,
    created_by: str,
) -> dict | None:
    """Gap #12: once a voucher posted from a bank-only statement line is on
    the ledger, match that line to the voucher's own bank line, so it does not
    come back as an open item. Best effort: the voucher is already posted, so
    any problem here leaves the line for the normal suggestions instead of
    failing the request."""
    from app.accounting.service import AccountingValidationError, get_ledger_lines
    from app.db.mongo import get_collection

    statement_line_id = stmt_line.get("statement_line_id")
    match_id = str(uuid4())
    try:
        _, ledger_lines = await get_ledger_lines(
            session, tenant_id=scope["tenant_id"], account_id=account_id,
            app_key=scope["app_key"], accounting_entity_id=scope["accounting_entity_id"],
        )
        side, amount = _statement_side_amount(stmt_line)
        book_line = next(
            (
                l for l in ledger_lines
                if str(l.get("journal_id")) == str(journal_entry_id)
                and _ledger_side_amount({"debit": l["debit"], "credit": l["credit"]}) == (side, amount)
            ),
            None,
        )
        if book_line is None:
            return None
        match_col = get_collection(BANK_RECON_MATCHES_COLLECTION)
        if await match_col.find_one({**scope, "statement_line_id": statement_line_id, "status": {"$in": LIVE_MATCH_STATUSES}}):
            return None
        if await match_col.find_one({**scope, "line_id": book_line["line_id"], "status": {"$in": LIVE_MATCH_STATUSES}}):
            return None
        try:
            await claim_bank_recon_lines(
                scope, owner_id=match_id, account_id=account_id,
                statement_line_ids=[statement_line_id], line_ids=[book_line["line_id"]],
            )
        except AccountingValidationError:
            return None
        now = _now()
        doc = {
            **scope,
            "match_id": match_id,
            "account_id": account_id,
            "statement_line_id": statement_line_id,
            "line_id": book_line["line_id"],
            "journal_id": book_line["journal_id"],
            "side": side,
            "amount": str(amount),
            "statement_txn_date": stmt_line.get("txn_date"),
            "book_entry_date": book_line.get("entry_date"),
            "source": "statement_voucher",
            "voucher_id": voucher_id,
            "status": MATCH_STATUS_ACTIVE,
            "created_by": created_by,
            "created_at": now,
        }
        try:
            await match_col.insert_one(doc)
        except Exception:
            await release_bank_recon_claims(scope, match_id)
            raise
        doc.pop("_id", None)
        doc["created_at"] = now.isoformat()
        return doc
    except Exception:  # pragma: no cover - defensive: never fail a posted voucher
        logger.exception("bank recon auto-match failed for statement line %s", statement_line_id)
        return None


def _difference_voucher_idempotency_key(account_id: int, stmt_ids: list[str], line_ids: list[int]) -> str:
    raw = f"{account_id}|{','.join(sorted(stmt_ids))}|{','.join(str(x) for x in sorted(line_ids))}"
    return "bank-recon-difference:" + hashlib.sha256(raw.encode()).hexdigest()[:32]


async def create_bank_recon_difference_match(
    session,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    account_id: int,
    statement_line_ids: list[str],
    line_ids: list[int],
    offset_account_id: int | None,
    offset_account_code: str | None,
    description: str | None,
    approve: bool,
    created_by: str,
    idempotency_key: str | None,
) -> dict:
    """Match lines whose totals differ (bank charges, MDR, TDS, rounding) and
    post the difference as a voucher on the bank account.

    The match rows are written as `pending_adjustment` first, which holds the
    lines. When the voucher is posted (immediately with `approve`, or later
    by an approver) `finalize_bank_recon_difference_match` adds the voucher's
    bank line to the group and makes it active. Until then the BRS treats
    the lines as unmatched, which is the truthful position."""
    from app.accounting.service import AccountingValidationError
    from app.db.mongo import get_collection

    if not offset_account_id and not offset_account_code:
        raise AccountingValidationError("Choose the account for the difference (for example Bank Charges or TDS Receivable)")

    scope = _scope(tenant_id, app_key, accounting_entity_id)
    match_col = get_collection(BANK_RECON_MATCHES_COLLECTION)
    ordered_stmt, ordered_book = await _load_match_selection(
        session, scope=scope, account_id=account_id,
        statement_line_ids=statement_line_ids, line_ids=line_ids,
    )
    try:
        plan = plan_difference_adjustment(
            ordered_stmt,
            [{"debit": l["debit"], "credit": l["credit"]} for l in ordered_book],
        )
    except ValueError as exc:
        raise AccountingValidationError(str(exc)) from exc

    stmt_ids = [str(x.get("statement_line_id")) for x in ordered_stmt]
    book_ids = [int(x["line_id"]) for x in ordered_book]
    group_id = str(uuid4())
    latest_stmt_date = max(str(x.get("txn_date") or "")[:10] for x in ordered_stmt)
    narration = str(description or "").strip() or (
        f"Bank reconciliation difference: {plan['hint_text']} "
        f"(bank {plan['statement_total']} vs books {plan['book_total']})"
    )[:300]
    voucher_kwargs = dict(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        bank_account_id=account_id,
        bank_entry=plan["bank_entry"],
        amount=plan["difference"],
        offset_account_id=offset_account_id,
        offset_account_code=offset_account_code,
        entry_date=date.fromisoformat(latest_stmt_date),
        description=narration,
        reference=f"BRDIFF-{group_id[:8].upper()}",
        approve=approve,
        approval_note="Bank reconciliation difference",
        created_by=created_by,
    )
    base_key = idempotency_key or _difference_voucher_idempotency_key(account_id, stmt_ids, book_ids)
    # Hold the lines before creating the voucher, so a concurrent match
    # cannot take them while the voucher is being created.
    await claim_bank_recon_lines(
        scope, owner_id=group_id, account_id=account_id,
        statement_line_ids=stmt_ids, line_ids=book_ids,
    )
    try:
        voucher = await _post_bank_voucher(session, **voucher_kwargs, idempotency_key=base_key)
        # The idempotency key returns an earlier voucher for the same selection
        # (safe retries). If that one was rejected, the accountant is retrying on
        # purpose — post a fresh voucher rather than reuse the rejected one.
        if str(voucher.get("status") or "").lower() == "rejected":
            voucher = await _post_bank_voucher(session, **voucher_kwargs, idempotency_key=f"{base_key}:{group_id}")
    except Exception:
        await release_bank_recon_claims(scope, group_id)
        raise

    now = _now()
    pairs = (
        [(ordered_stmt[0], b) for b in ordered_book]
        if len(ordered_stmt) == 1
        else [(s, ordered_book[0]) for s in ordered_stmt]
    )
    docs = []
    for s, b in pairs:
        share = (
            _ledger_side_amount({"debit": b["debit"], "credit": b["credit"]})[1]
            if len(ordered_stmt) == 1
            else _statement_side_amount(s)[1]
        )
        docs.append({
            **scope,
            "match_id": str(uuid4()),
            "match_group_id": group_id,
            "group_type": plan["group_type"],
            "group_size": len(ordered_stmt) + len(ordered_book) + 1,
            "group_amount": str(plan["statement_total"]),
            "account_id": account_id,
            "statement_line_id": s.get("statement_line_id"),
            "line_id": b["line_id"],
            "journal_id": b["journal_id"],
            "side": plan["side"],
            "amount": str(_q2(share)),
            "statement_txn_date": s.get("txn_date"),
            "book_entry_date": b.get("entry_date"),
            "book_total": str(plan["book_total"]),
            "difference_amount": str(plan["difference"]),
            "difference_bank_entry": plan["bank_entry"],
            "difference_hint": plan["hint"],
            "adjustment_voucher_id": voucher.get("voucher_id"),
            "status": MATCH_STATUS_PENDING,
            "created_by": created_by,
            "created_at": now,
        })
    try:
        await match_col.insert_many(docs)
    except Exception:
        await release_bank_recon_claims(scope, group_id)
        raise

    if str(voucher.get("status") or "").lower() == "posted":
        return await finalize_bank_recon_difference_match(
            session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
            match_group_id=group_id, finalized_by=created_by,
        )
    return {
        "match_group_id": group_id,
        "status": MATCH_STATUS_PENDING,
        "difference": str(plan["difference"]),
        "bank_entry": plan["bank_entry"],
        "voucher": voucher,
        "note": "The difference voucher is waiting for approval. Complete the match once it is posted.",
    }


async def finalize_bank_recon_difference_match(
    session,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    match_group_id: str,
    finalized_by: str,
) -> dict:
    """Activate a pending difference match once its voucher is posted: add
    the voucher's bank ledger line to the group and flip every row to active."""
    from app.accounting.service import AccountingNotFoundError, AccountingValidationError, get_ledger_lines
    from app.db.mongo import get_collection
    from app.modules.business.service import VOUCHERS_COLLECTION

    scope = _scope(tenant_id, app_key, accounting_entity_id)
    match_col = get_collection(BANK_RECON_MATCHES_COLLECTION)
    rows = await match_col.find(
        {**scope, "match_group_id": match_group_id, "status": MATCH_STATUS_PENDING}
    ).to_list(length=GROUP_MATCH_MAX_LINES * 2 + 2)
    if not rows:
        if await match_col.find_one({**scope, "match_group_id": match_group_id, "status": MATCH_STATUS_ACTIVE}):
            raise AccountingValidationError("This match is already complete")
        raise AccountingNotFoundError("Pending difference match not found")
    head = rows[0]
    account_id = int(head["account_id"])

    voucher = await get_collection(VOUCHERS_COLLECTION).find_one(
        {**scope, "voucher_id": head.get("adjustment_voucher_id")}
    )
    if voucher is None:
        raise AccountingNotFoundError("Difference voucher not found")
    status = str(voucher.get("status") or "").lower()
    if status != "posted" or not voucher.get("journal_entry_id"):
        if status == "rejected":
            raise AccountingValidationError("The difference voucher was rejected. Unmatch to release the lines.")
        raise AccountingValidationError("The difference voucher is still waiting for approval")

    _, ledger_lines = await get_ledger_lines(
        session, tenant_id=tenant_id, account_id=account_id,
        app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    difference = _q2(head["difference_amount"])
    expected_side = "deposit" if head.get("difference_bank_entry") == "debit" else "withdrawal"
    adjustment_line = next(
        (
            l for l in ledger_lines
            if int(l["journal_id"]) == int(voucher["journal_entry_id"])
            and _ledger_side_amount({"debit": l["debit"], "credit": l["credit"]}) == (expected_side, difference)
        ),
        None,
    )
    if adjustment_line is None:
        raise AccountingValidationError("The difference voucher did not post to this bank account for the expected amount")
    if await match_col.find_one({**scope, "line_id": adjustment_line["line_id"], "status": {"$in": LIVE_MATCH_STATUSES}}):
        raise AccountingValidationError("The difference voucher's bank line is already matched elsewhere")
    await claim_bank_recon_lines(
        scope, owner_id=match_group_id, account_id=account_id, line_ids=[adjustment_line["line_id"]],
    )

    now = _now()
    adjustment_row = {
        **{k: head[k] for k in (
            "tenant_id", "app_key", "accounting_entity_id", "match_group_id", "group_type", "group_size",
            "group_amount", "account_id", "book_total", "difference_amount", "difference_bank_entry",
            "difference_hint", "adjustment_voucher_id", "created_by", "created_at",
        )},
        "match_id": str(uuid4()),
        "is_adjustment": True,
        "statement_line_id": head.get("statement_line_id"),
        "line_id": adjustment_line["line_id"],
        "journal_id": adjustment_line["journal_id"],
        "side": expected_side,
        "amount": str(difference),
        "statement_txn_date": head.get("statement_txn_date"),
        "book_entry_date": adjustment_line.get("entry_date"),
        "status": MATCH_STATUS_PENDING,
    }
    await match_col.insert_one(adjustment_row)
    await match_col.update_many(
        {**scope, "match_group_id": match_group_id, "status": MATCH_STATUS_PENDING},
        {"$set": {"status": MATCH_STATUS_ACTIVE, "finalized_by": finalized_by, "finalized_at": now}},
    )
    final_rows = await match_col.find(
        {**scope, "match_group_id": match_group_id, "status": MATCH_STATUS_ACTIVE}
    ).to_list(length=GROUP_MATCH_MAX_LINES * 2 + 2)
    for row in final_rows:
        row.pop("_id", None)
        for key in ("created_at", "finalized_at"):
            if isinstance(row.get(key), datetime):
                row[key] = row[key].isoformat()
    return {
        "match_group_id": match_group_id,
        "status": MATCH_STATUS_ACTIVE,
        "difference": str(difference),
        "adjustment_voucher_id": head.get("adjustment_voucher_id"),
        "matches": final_rows,
    }
