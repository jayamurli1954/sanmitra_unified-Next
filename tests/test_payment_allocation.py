"""Payment allocation (open-item AR/AP) — pure-logic unit tests.

These cover the core matching math (outstanding, unallocated, validation, FIFO
suggestion, and the ledger reconciliation invariant) without any DB, so they run
fast and deterministically. The async I/O wrappers are thin and exercised by the
real-stack E2E driver separately."""
from datetime import date
from decimal import Decimal

import pytest

from app.accounting.service import AccountingValidationError
from app.modules.business.allocation_service import (
    _SIDE,
    aging_bucket,
    aging_summary,
    compute_open_items,
    compute_unallocated_payments,
    open_item_view,
    payment_view,
    reconcile,
    suggest_fifo,
    sum_allocated,
    validate_allocation,
)

RECV = _SIDE["receivable"]
AS_OF = date(2026, 6, 30)


def _invoice(invoice_id, number, total, dt="2026-06-01", due=None, party="cust-A"):
    return {
        "invoice_id": invoice_id, "invoice_number": number, "invoice_total": total,
        "invoice_date": dt, "due_date": due, "customer_party_id": party, "status": "posted",
    }


def _alloc(open_item_id, amount, payment_id="rv1", status="active"):
    return {"open_item_id": open_item_id, "payment_id": payment_id,
            "allocated_amount": amount, "status": status}


def _receipt(voucher_id, number, amount, dt="2026-06-10", party="cust-A"):
    return {"voucher_id": voucher_id, "voucher_number": number, "amount": amount,
            "entry_date": dt, "party_id": party, "voucher_type": "receipt", "status": "posted"}


# --------------------------- outstanding / sums --------------------------- #

def test_sum_allocated_ignores_reversed():
    allocs = [_alloc("i1", "100"), _alloc("i1", "50"), _alloc("i1", "30", status="reversed")]
    assert sum_allocated(allocs) == Decimal("150.00")


def test_open_item_outstanding_is_total_minus_active_allocations():
    view = open_item_view(_invoice("i1", "INV-1", "1000.00"),
                          [_alloc("i1", "400"), _alloc("i1", "100", status="reversed")],
                          spec=RECV, as_of=AS_OF)
    assert view["total"] == "1000.00"
    assert view["allocated"] == "400.00"      # reversed 100 excluded
    assert view["outstanding"] == "600.00"


def test_compute_open_items_hides_settled_and_sorts_oldest_first():
    items = [
        _invoice("i2", "INV-2", "500.00", dt="2026-06-05"),
        _invoice("i1", "INV-1", "300.00", dt="2026-06-01"),
        _invoice("i3", "INV-3", "200.00", dt="2026-06-09"),
    ]
    allocs = {"i3": [_alloc("i3", "200")]}  # i3 fully settled
    views = compute_open_items(items, allocs, spec=RECV, as_of=AS_OF)
    assert [v["open_item_id"] for v in views] == ["i1", "i2"]  # oldest first, i3 hidden

    with_settled = compute_open_items(items, allocs, spec=RECV, as_of=AS_OF, include_settled=True)
    assert [v["open_item_id"] for v in with_settled] == ["i1", "i2", "i3"]


def test_days_overdue_uses_due_date_then_clamps_to_zero():
    overdue = open_item_view(_invoice("i1", "INV-1", "100", due="2026-06-20"), [], spec=RECV, as_of=AS_OF)
    assert overdue["days_overdue"] == 10
    not_yet = open_item_view(_invoice("i2", "INV-2", "100", due="2026-07-15"), [], spec=RECV, as_of=AS_OF)
    assert not_yet["days_overdue"] == 0


# --------------------------- payments / unallocated --------------------------- #

def test_payment_unallocated_balance():
    view = payment_view(_receipt("rv1", "RV-1", "1000.00"), [_alloc("i1", "600", payment_id="rv1")])
    assert view["unallocated"] == "400.00"


def test_compute_unallocated_hides_fully_applied():
    payments = [_receipt("rv1", "RV-1", "1000.00"), _receipt("rv2", "RV-2", "500.00", dt="2026-06-12")]
    allocs = {"rv2": [_alloc("i9", "500", payment_id="rv2")]}  # rv2 fully applied
    views = compute_unallocated_payments(payments, allocs)
    assert [v["payment_id"] for v in views] == ["rv1"]


# --------------------------- validation --------------------------- #

def test_validate_allocation_accepts_valid():
    validate_allocation(
        payment_unallocated=Decimal("1000.00"),
        outstanding_by_item={"i1": Decimal("600.00"), "i2": Decimal("500.00")},
        requested=[("i1", Decimal("600.00")), ("i2", Decimal("400.00"))],
    )  # no raise


def test_validate_allocation_rejects_overpaying_an_item():
    with pytest.raises(AccountingValidationError, match="exceeds outstanding"):
        validate_allocation(
            payment_unallocated=Decimal("1000.00"),
            outstanding_by_item={"i1": Decimal("600.00")},
            requested=[("i1", Decimal("700.00"))],
        )


def test_validate_allocation_rejects_over_allocating_the_payment():
    with pytest.raises(AccountingValidationError, match="exceeds the payment"):
        validate_allocation(
            payment_unallocated=Decimal("500.00"),
            outstanding_by_item={"i1": Decimal("600.00"), "i2": Decimal("600.00")},
            requested=[("i1", Decimal("300.00")), ("i2", Decimal("300.00"))],
        )


def test_validate_allocation_rejects_unknown_item_and_nonpositive():
    with pytest.raises(AccountingValidationError, match="not found"):
        validate_allocation(payment_unallocated=Decimal("100"), outstanding_by_item={},
                            requested=[("missing", Decimal("10"))])
    with pytest.raises(AccountingValidationError, match="greater than zero"):
        validate_allocation(payment_unallocated=Decimal("100"),
                            outstanding_by_item={"i1": Decimal("100")},
                            requested=[("i1", Decimal("0"))])
    with pytest.raises(AccountingValidationError, match="At least one"):
        validate_allocation(payment_unallocated=Decimal("100"), outstanding_by_item={"i1": Decimal("100")},
                            requested=[])


# --------------------------- FIFO suggestion --------------------------- #

def test_suggest_fifo_fills_oldest_first_with_partial_last():
    open_items = [
        {"open_item_id": "i1", "open_item_number": "INV-1", "outstanding": "300.00"},
        {"open_item_id": "i2", "open_item_number": "INV-2", "outstanding": "500.00"},
        {"open_item_id": "i3", "open_item_number": "INV-3", "outstanding": "200.00"},
    ]
    suggestion = suggest_fifo(open_items, Decimal("650.00"))
    assert suggestion == [
        {"open_item_id": "i1", "open_item_number": "INV-1", "allocated_amount": "300.00"},
        {"open_item_id": "i2", "open_item_number": "INV-2", "allocated_amount": "350.00"},
    ]


def test_suggest_fifo_stops_when_nothing_available():
    assert suggest_fifo([{"open_item_id": "i1", "open_item_number": "INV-1", "outstanding": "300.00"}],
                        Decimal("0.00")) == []


# --------------------------- reconciliation invariant --------------------------- #

def test_reconcile_balanced_when_metadata_matches_ledger():
    # Invoice 1000, receipt 400 fully allocated -> open outstanding 600, unallocated 0.
    # Ledger receivable for the party = 1000 - 400 = 600. Must balance.
    result = reconcile(
        open_items_outstanding=Decimal("600.00"),
        unallocated_payments=Decimal("0.00"),
        ledger_balance=Decimal("600.00"),
    )
    assert result["balanced"] is True
    assert result["computed_net"] == "600.00"
    assert result["difference"] == "0.00"


def test_reconcile_balanced_with_unapplied_receipt_on_account():
    # Invoice 1000 (unpaid) + receipt 400 NOT yet allocated (on-account).
    # open outstanding 1000, unallocated 400 -> net 600 == ledger 600.
    result = reconcile(
        open_items_outstanding=Decimal("1000.00"),
        unallocated_payments=Decimal("400.00"),
        ledger_balance=Decimal("600.00"),
    )
    assert result["balanced"] is True


def test_reconcile_flags_drift():
    result = reconcile(
        open_items_outstanding=Decimal("600.00"),
        unallocated_payments=Decimal("0.00"),
        ledger_balance=Decimal("550.00"),
    )
    assert result["balanced"] is False
    assert result["difference"] == "50.00"


# --------------------------- aging buckets (Phase B) --------------------------- #

def test_aging_bucket_boundaries():
    assert aging_bucket(0) == "0-30"
    assert aging_bucket(30) == "0-30"
    assert aging_bucket(31) == "31-60"
    assert aging_bucket(60) == "31-60"
    assert aging_bucket(61) == "61-90"
    assert aging_bucket(90) == "61-90"
    assert aging_bucket(91) == "90+"
    assert aging_bucket(999) == "90+"


def test_aging_summary_groups_by_party_and_bucket():
    open_items = [
        {"open_item_id": "i1", "party_id": "cust-A", "outstanding": "600.00", "days_overdue": 10},
        {"open_item_id": "i2", "party_id": "cust-A", "outstanding": "400.00", "days_overdue": 45},
        {"open_item_id": "i3", "party_id": "cust-B", "outstanding": "1200.00", "days_overdue": 120},
    ]
    summary = aging_summary(open_items)
    assert summary["buckets_order"] == ["0-30", "31-60", "61-90", "90+"]
    assert summary["grand_total"] == "2200.00"
    assert summary["totals"] == {"0-30": "600.00", "31-60": "400.00", "61-90": "0.00", "90+": "1200.00"}
    # Sorted by total desc -> cust-B (1200) first.
    assert [r["party_id"] for r in summary["by_party"]] == ["cust-B", "cust-A"]
    cust_a = next(r for r in summary["by_party"] if r["party_id"] == "cust-A")
    assert cust_a["buckets"]["0-30"] == "600.00"
    assert cust_a["buckets"]["31-60"] == "400.00"
    assert cust_a["total"] == "1000.00"


def test_aging_summary_empty():
    summary = aging_summary([])
    assert summary["grand_total"] == "0.00"
    assert summary["by_party"] == []
