"""Opening balances (CSV import) + year-end close — pure logic. The preview
assembler gets pre-resolved account/party lookups; the year-end assembler gets
P&L lines exactly as get_profit_loss shapes them."""
from datetime import date
from decimal import Decimal

import pytest

from app.modules.business.opening_close import (
    OPENING_BALANCE_EQUITY_CODE,
    RETAINED_EARNINGS_CODE,
    assemble_opening_preview,
    assemble_year_end_lines,
    csv_template,
    parse_opening_balances_csv,
)

AS_OF = date(2026, 4, 1)

ACCOUNTS_BY_CODE = {
    "11001": {"account_id": 1, "code": "11001", "name": "Cash in Hand"},
    "12001": {"account_id": 2, "code": "12001", "name": "Sundry Debtors"},
    "21001": {"account_id": 3, "code": "21001", "name": "Sundry Creditors"},
    "31004": {"account_id": 4, "code": "31004", "name": "Opening Balance Equity"},
}
ACCOUNTS_BY_NAME = {info["name"].lower(): info for info in ACCOUNTS_BY_CODE.values()}
PARTIES_BY_CODE = {"CUST-001": {"party_id": "p-1", "party_name": "Acme Traders"}}
PARTIES_BY_NAME = {"acme traders": {"party_id": "p-1", "party_name": "Acme Traders"}}


def _preview(rows):
    return assemble_opening_preview(
        rows=rows,
        accounts_by_code=ACCOUNTS_BY_CODE, accounts_by_name=ACCOUNTS_BY_NAME,
        parties_by_code=PARTIES_BY_CODE, parties_by_name=PARTIES_BY_NAME,
        as_of=AS_OF,
    )


# ---- CSV parsing ---------------------------------------------------------- #

def test_parse_template_roundtrip():
    rows = parse_opening_balances_csv(csv_template())
    assert len(rows) == 7
    assert rows[0]["account_code"] == "11001"
    assert rows[0]["debit"] == "25000.00"
    assert rows[2]["party"] == "CUST-001"
    assert rows[4]["credit"] == "30000.00"


def test_parse_header_aliases_and_formats():
    rows = parse_opening_balances_csv(
        "Ledger,Dr,Cr\n"
        "Cash in Hand,\"1,00,000.00\",\n"
        "Sundry Creditors,,50000\n"
        ",,\n"                       # blank row skipped
        "Sundry Debtors,0,0\n"       # zero row skipped
    )
    assert len(rows) == 2
    assert rows[0]["account_name"] == "Cash in Hand"
    assert rows[0]["debit"] == "100000.00"


def test_parse_rejects_unusable():
    with pytest.raises(ValueError):
        parse_opening_balances_csv("")
    with pytest.raises(ValueError):
        parse_opening_balances_csv("foo,debit,credit\n")          # no account column... header maps 'foo'? no
    with pytest.raises(ValueError):
        parse_opening_balances_csv("account_code,notes\n11001,x\n")  # no amounts


# ---- Preview assembly ----------------------------------------------------- #

def test_preview_resolves_and_balances():
    out = _preview([
        {"row_number": 2, "account_code": "11001", "account_name": "", "party": "", "debit": "25000", "credit": "0"},
        {"row_number": 3, "account_code": "12001", "account_name": "", "party": "CUST-001", "debit": "40000", "credit": "0"},
        {"row_number": 4, "account_code": "21001", "account_name": "", "party": "", "debit": "0", "credit": "30000"},
    ])
    assert out["can_post"] is True
    assert out["error_count"] == 0
    assert out["total_debit"] == "65000.00"
    assert out["total_credit"] == "30000.00"
    # Debits exceed credits by 35000 -> OBE is credited.
    assert out["balancing_line"]["account_code"] == OPENING_BALANCE_EQUITY_CODE
    assert out["balancing_line"]["credit"] == "35000.00"
    assert out["balancing_line"]["debit"] == "0.00"
    # Party row resolved to the party id.
    assert out["lines"][1]["party_id"] == "p-1"


def test_preview_matches_by_name_and_flags_errors():
    out = _preview([
        {"row_number": 2, "account_code": "", "account_name": "Cash in Hand", "party": "", "debit": "100", "credit": "0"},
        {"row_number": 3, "account_code": "99999", "account_name": "", "party": "", "debit": "1", "credit": "0"},
        {"row_number": 4, "account_code": "12001", "account_name": "", "party": "Nobody & Co", "debit": "5", "credit": "0"},
        {"row_number": 5, "account_code": "11001", "account_name": "", "party": "", "debit": "10", "credit": "10"},
    ])
    assert out["can_post"] is False
    assert out["error_count"] == 3
    problems = {e["row_number"]: " ".join(e["problems"]) for e in out["errors"]}
    assert "Unknown account code" in problems[3]
    assert "Unknown party" in problems[4]
    assert "both a debit and a credit" in problems[5]
    # The good row still resolves (by name).
    assert out["lines"][0]["account_id"] == 1


def test_preview_balanced_file_needs_no_balancing_line():
    out = _preview([
        {"row_number": 2, "account_code": "11001", "account_name": "", "party": "", "debit": "500", "credit": "0"},
        {"row_number": 3, "account_code": "21001", "account_name": "", "party": "", "debit": "0", "credit": "500"},
    ])
    assert out["difference"] == "0.00"
    assert out["balancing_line"] is None


# ---- Year-end close ------------------------------------------------------- #

def _pnl_line(account_id, code, name, kind, net):
    return {"account_id": account_id, "account_code": code, "account_name": name,
            "account_type": kind, "net_amount": Decimal(net)}


def test_year_end_lines_profit():
    out = assemble_year_end_lines([
        _pnl_line(10, "41001", "Sales", "income", "100000.00"),
        _pnl_line(11, "51001", "Purchases", "expense", "60000.00"),
        _pnl_line(12, "42002", "Discount Received", "income", "0.00"),   # zero -> skipped
    ], Decimal("40000.00"))
    lines = {l["account_code"]: l for l in out["closing_lines"]}
    assert set(lines) == {"41001", "51001"}
    assert lines["41001"]["debit"] == "100000.00"     # income closed with a debit
    assert lines["51001"]["credit"] == "60000.00"     # expense closed with a credit
    re_line = out["retained_earnings"]
    assert re_line["account_code"] == RETAINED_EARNINGS_CODE
    assert re_line["credit"] == "40000.00"            # profit credits retained earnings
    # The closing journal balances: debits == credits.
    total_dr = sum(Decimal(l["debit"]) for l in out["closing_lines"]) + Decimal(re_line["debit"])
    total_cr = sum(Decimal(l["credit"]) for l in out["closing_lines"]) + Decimal(re_line["credit"])
    assert total_dr == total_cr


def test_year_end_lines_loss_and_contra_balances():
    out = assemble_year_end_lines([
        _pnl_line(10, "41001", "Sales", "income", "20000.00"),
        _pnl_line(13, "54004", "Discount Allowed", "expense", "-500.00"),  # contra (credit) expense
        _pnl_line(11, "51001", "Purchases", "expense", "30000.00"),
    ], Decimal("-9500.00"))
    lines = {l["account_code"]: l for l in out["closing_lines"]}
    assert lines["54004"]["debit"] == "500.00"        # negative expense closes with a debit
    re_line = out["retained_earnings"]
    assert re_line["debit"] == "9500.00"              # loss debits retained earnings
    total_dr = sum(Decimal(l["debit"]) for l in out["closing_lines"]) + Decimal(re_line["debit"])
    total_cr = sum(Decimal(l["credit"]) for l in out["closing_lines"]) + Decimal(re_line["credit"])
    assert total_dr == total_cr
