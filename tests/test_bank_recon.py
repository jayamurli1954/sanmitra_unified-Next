"""Bank reconciliation — CSV statement parsing, match suggestion and the BRS
assembler. Pure functions, no DB. Sign convention under test: a statement
DEPOSIT corresponds to a book DEBIT on the bank account (asset increases)."""
from datetime import date
from decimal import Decimal

import pytest

from app.modules.business.bank_recon import (
    assemble_bank_reconciliation,
    parse_bank_statement_csv,
    statement_line_dedupe_key,
    suggest_matches,
)


# ---- CSV parsing ---------------------------------------------------------- #

def test_parse_two_column_csv_with_common_headers():
    csv_text = (
        "Txn Date,Narration,Chq No,Withdrawal Amt,Deposit Amt,Balance\n"
        "01/04/2026,NEFT FROM ACME,UTR123,,\"50,000.00\",\"1,50,000.00\"\n"
        "03/04/2026,CHQ PAID RENT,000451,25000,,125000\n"
        "  ,Opening Balance,,,,100000\n"          # no date -> skipped
        "05/04/2026,ZERO ROW,,0,0,125000\n"       # zero movement -> skipped
    )
    lines = parse_bank_statement_csv(csv_text)
    assert len(lines) == 2
    assert lines[0] == {
        "txn_date": "2026-04-01", "description": "NEFT FROM ACME", "ref": "UTR123",
        "withdrawal": "0.00", "deposit": "50000.00", "balance": "150000.00",
    }
    assert lines[1]["withdrawal"] == "25000.00"
    assert lines[1]["deposit"] == "0.00"
    assert lines[1]["txn_date"] == "2026-04-03"


def test_parse_single_amount_with_drcr_column_and_date_variants():
    csv_text = (
        "Date,Particulars,Amount,Dr/Cr\n"
        "2026-04-01,UPI received,1500.50,CR\n"
        "02-Apr-2026,Bank charges,118.00,DR\n"
    )
    lines = parse_bank_statement_csv(csv_text)
    assert lines[0]["deposit"] == "1500.50"
    assert lines[1]["withdrawal"] == "118.00"
    assert lines[1]["txn_date"] == "2026-04-02"


def test_parse_signed_single_amount_column():
    csv_text = "date,description,amount\n01/04/2026,salary out,-30000\n01/04/2026,client in,45000\n"
    lines = parse_bank_statement_csv(csv_text)
    assert lines[0]["withdrawal"] == "30000.00"
    assert lines[1]["deposit"] == "45000.00"


def test_parse_rejects_unusable_files():
    with pytest.raises(ValueError):
        parse_bank_statement_csv("")
    with pytest.raises(ValueError):
        parse_bank_statement_csv("foo,bar\n1,2\n")  # no date column
    with pytest.raises(ValueError):
        parse_bank_statement_csv("date,notes\n01/04/2026,hello\n")  # no amounts


def test_dedupe_key_stable_and_distinguishing():
    a = {"txn_date": "2026-04-01", "withdrawal": "0.00", "deposit": "500.00", "ref": "U1", "description": "NEFT"}
    assert statement_line_dedupe_key(a) == statement_line_dedupe_key(dict(a))
    assert statement_line_dedupe_key(a) != statement_line_dedupe_key({**a, "deposit": "501.00"})


# ---- Matching ------------------------------------------------------------- #

def _stmt(id_, d, *, deposit="0.00", withdrawal="0.00", ref="", desc=""):
    return {"statement_line_id": id_, "txn_date": d, "deposit": deposit,
            "withdrawal": withdrawal, "ref": ref, "description": desc}


def _book(line_id, d, *, debit="0.00", credit="0.00", reference="", description=""):
    return {"line_id": line_id, "journal_id": 100 + line_id, "entry_date": d,
            "debit": debit, "credit": credit, "reference": reference, "description": description}


def test_suggest_matches_amount_side_and_window():
    suggestions = suggest_matches(
        [
            _stmt("s1", "2026-04-03", deposit="5000.00"),            # matches book debit 2 days earlier
            _stmt("s2", "2026-04-10", withdrawal="2000.00"),          # matches book credit same day
            _stmt("s3", "2026-04-20", deposit="999.00"),              # no book counterpart
            _stmt("s4", "2026-04-01", deposit="7000.00"),             # book line is 30 days away -> outside window
        ],
        [
            _book(1, "2026-04-01", debit="5000.00"),
            _book(2, "2026-04-10", credit="2000.00"),
            _book(3, "2026-05-01", debit="7000.00"),
            _book(4, "2026-04-03", credit="5000.00"),  # wrong side for s1 (deposit needs debit)
        ],
    )
    by_stmt = {s["statement_line_id"]: s for s in suggestions}
    assert set(by_stmt) == {"s1", "s2"}
    assert by_stmt["s1"]["line_id"] == 1 and by_stmt["s1"]["date_diff_days"] == 2
    assert by_stmt["s2"]["side"] == "withdrawal"


def test_suggest_matches_prefers_reference_hit_and_is_one_to_one():
    suggestions = suggest_matches(
        [_stmt("s1", "2026-04-05", deposit="1000.00", ref="INV-77")],
        [
            _book(1, "2026-04-05", debit="1000.00", reference="misc"),
            _book(2, "2026-04-07", debit="1000.00", reference="Receipt INV-77"),
        ],
    )
    # The ref match wins even though the other candidate's date is closer.
    assert len(suggestions) == 1
    assert suggestions[0]["line_id"] == 2
    assert suggestions[0]["confidence"] == "ref"


# ---- BRS assembly --------------------------------------------------------- #

def test_brs_identity_and_classification():
    account = {"account_id": 7, "code": "11010", "name": "Bank Account"}
    statement_lines = [
        _stmt("s1", "2026-04-01", deposit="50000.00") | {"balance": "50000.00"},
        _stmt("s2", "2026-04-05", withdrawal="118.00", desc="bank charges") | {"balance": "49882.00"},
    ]
    ledger_lines = [
        _book(1, "2026-04-01", debit="50000.00"),    # matched to s1
        _book(2, "2026-04-06", credit="25000.00"),   # cheque issued, not presented
    ]
    matches = [{"statement_line_id": "s1", "line_id": "1", "journal_id": 101, "amount": "50000.00"}]
    out = assemble_bank_reconciliation(
        account=account, as_of=date(2026, 4, 30),
        statement_lines=statement_lines, ledger_lines=ledger_lines,
        matches=matches, suggestions=[],
    )
    s = out["summary"]
    # Book balance = 50000 - 25000 = 25000.
    assert s["book_balance"] == "25000.00"
    # Expected statement = book 25000 + uncleared credit 25000 - 0 + 0 - bank-only 118 = 49882.
    assert s["expected_statement_balance"] == "49882.00"
    assert s["statement_balance"] == "49882.00"
    assert s["difference"] == "0.00"
    assert [l["statement_line_id"] for l in out["in_bank_not_in_books"]] == ["s2"]
    assert [l["line_id"] for l in out["in_books_not_in_bank"]] == [2]
    assert s["uncleared_withdrawals"] == "25000.00"
    assert s["bank_only_withdrawals"] == "118.00"


def test_brs_without_statement_balance_column():
    out = assemble_bank_reconciliation(
        account={"account_id": 7, "code": "11010", "name": "Bank"},
        as_of=date(2026, 4, 30),
        statement_lines=[_stmt("s1", "2026-04-01", deposit="100.00")],
        ledger_lines=[], matches=[], suggestions=[],
    )
    assert out["summary"]["statement_balance"] is None
    assert out["summary"]["difference"] is None
    assert out["summary"]["expected_statement_balance"] == "100.00"
