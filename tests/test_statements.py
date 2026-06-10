"""Customer statements + dunning — pure assembly logic. No DB: transactions
and open items are passed in as the allocation/ledger layers shape them."""
from datetime import date
from decimal import Decimal

from app.modules.business.statements import (
    DUNNING_LEVELS,
    assemble_party_statement,
    build_dunning_letter,
    suggest_dunning_level,
)

AS_OF = date(2026, 6, 30)


def _open_item(days, outstanding, number="INV-1", item_date="2026-05-01"):
    return {"open_item_id": number.lower(), "open_item_number": number, "item_date": item_date,
            "due_date": None, "outstanding": outstanding, "days_overdue": days}


def test_dunning_level_escalation():
    assert suggest_dunning_level([])["level"] == 0
    assert suggest_dunning_level([_open_item(0, "100.00")])["level"] == 0   # not overdue
    assert suggest_dunning_level([_open_item(5, "100.00")])["level"] == 1
    assert suggest_dunning_level([_open_item(45, "100.00")])["level"] == 2
    s = suggest_dunning_level([_open_item(5, "100.00"), _open_item(75, "250.00", "INV-2")])
    assert s["level"] == 3                      # oldest item drives the level
    assert s["max_days_overdue"] == 75
    assert s["overdue_count"] == 2
    assert s["overdue_total"] == "350.00"
    # Settled-but-old items don't trigger reminders.
    assert suggest_dunning_level([_open_item(90, "0.00")])["level"] == 0


def test_dunning_letter_contains_figures_and_tone():
    items = [_open_item(75, "250.00", "INV-2"), _open_item(5, "100.00")]
    suggestion = suggest_dunning_level(items)
    letter = build_dunning_letter(
        business_name="Sanmitra Traders", party_name="Acme Ltd",
        as_of=AS_OF, open_items=items, suggestion=suggestion,
    )
    assert "Sanmitra Traders" in letter and "Acme Ltd" in letter
    assert "INV-2" in letter and "250.00" in letter
    assert "Total overdue: Rs. 350.00" in letter
    assert "final" in letter.lower()            # level-3 tone
    # Level 0 produces no letter.
    assert build_dunning_letter(business_name="X", party_name="Y", as_of=AS_OF,
                                open_items=[], suggestion={"level": 0}) == ""


def _txn(d, debit="0", credit="0", doc="sales_invoice", ref="INV-1"):
    return {"entry_date": d, "debit": Decimal(debit), "credit": Decimal(credit),
            "document_type": doc, "reference": ref, "description": f"{doc} {ref}"}


def test_statement_running_balance_receivable():
    out = assemble_party_statement(
        party={"party_id": "p1", "party_name": "Acme Ltd"},
        kind="receivable", from_date=date(2026, 4, 1), to_date=AS_OF,
        opening_balance=Decimal("1000.00"),
        transactions=[
            _txn("2026-04-10", debit="5000.00"),                       # invoice
            _txn("2026-05-02", credit="3000.00", doc="receipt", ref="RCT-9"),
        ],
        open_items=[], dunning_suggestion={"level": 0}, dunning_letter="",
        dunning_log=[], business_name="Sanmitra Traders",
    )
    assert out["opening_balance"] == "1000.00"
    assert [r["balance"] for r in out["transactions"]] == ["6000.00", "3000.00"]
    assert out["closing_balance"] == "3000.00"
    assert out["total_debit"] == "5000.00"
    assert out["total_credit"] == "3000.00"
    assert out["transactions"][0]["document_type"] == "Invoice"
    assert out["transactions"][1]["document_type"] == "Receipt"


def test_statement_running_balance_payable_sign_flips():
    out = assemble_party_statement(
        party={"party_id": "v1", "party_name": "Vendor"},
        kind="payable", from_date=date(2026, 4, 1), to_date=AS_OF,
        opening_balance=Decimal("0.00"),
        transactions=[
            _txn("2026-04-10", credit="2000.00", doc="purchase_bill", ref="B-1"),  # we owe more
            _txn("2026-04-20", debit="500.00", doc="payment", ref="PMT-1"),        # we paid
        ],
        open_items=[], dunning_suggestion={"level": 0}, dunning_letter="",
        dunning_log=[], business_name="Sanmitra Traders",
    )
    assert [r["balance"] for r in out["transactions"]] == ["2000.00", "1500.00"]
    assert out["closing_balance"] == "1500.00"


def test_dunning_levels_policy_shape():
    assert [r["level"] for r in DUNNING_LEVELS] == [1, 2, 3]
    assert [r["min_days_overdue"] for r in DUNNING_LEVELS] == [1, 31, 61]
