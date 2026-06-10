"""TDS/TCS (Income-tax) — section masters, deduction/collection math and the
quarterly register assembler. Pure functions, no DB: rates come from the
section masters (overridable per document), TDS bases exclude GST (Circular
23/2017), TCS bases include it (Circular 17/2020)."""
from datetime import date
from decimal import Decimal

import pytest

from app.modules.business.tds import (
    NO_PAN_TDS_RATE,
    TCS_SECTIONS,
    TDS_SECTIONS,
    assemble_tds_register,
    compute_tcs,
    compute_tds,
    list_sections,
)


def test_section_masters_and_listing():
    assert TDS_SECTIONS["194J"]["rate"] == Decimal("10")
    assert TDS_SECTIONS["194C"]["rate"] == Decimal("2")
    assert TDS_SECTIONS["194Q"]["rate"] == Decimal("0.1")
    assert TCS_SECTIONS["206C-1H"]["rate"] == Decimal("0.1")
    listing = list_sections()
    assert {row["section"] for row in listing["tds"]} == set(TDS_SECTIONS)
    assert {row["section"] for row in listing["tcs"]} == set(TCS_SECTIONS)
    assert listing["no_pan_rate"] == str(NO_PAN_TDS_RATE)
    # JSON-safe: every rate is a string
    assert all(isinstance(row["rate"], str) for row in listing["tds"] + listing["tcs"])


def test_compute_tds_default_and_override():
    rate, amount = compute_tds("194J", Decimal("50000"))
    assert (rate, amount) == (Decimal("10"), Decimal("5000.00"))
    # 206AA no-PAN override at 20%
    rate, amount = compute_tds("194J", Decimal("50000"), Decimal("20"))
    assert (rate, amount) == (Decimal("20"), Decimal("10000.00"))
    # fractional rate quantizes half-up to 2dp: 123456.78 * 0.1% = 123.45678 -> 123.46
    rate, amount = compute_tds("194Q", Decimal("123456.78"))
    assert (rate, amount) == (Decimal("0.1"), Decimal("123.46"))


def test_compute_tcs_default_and_override():
    rate, amount = compute_tcs("206C-1H", Decimal("118000"))  # GST-inclusive base
    assert (rate, amount) == (Decimal("0.1"), Decimal("118.00"))
    rate, amount = compute_tcs("206C-SCRAP", Decimal("10000"), Decimal("5"))
    assert (rate, amount) == (Decimal("5"), Decimal("500.00"))


def test_unknown_section_and_bad_rate_rejected():
    with pytest.raises(ValueError):
        compute_tds("194Z", Decimal("100"))
    with pytest.raises(ValueError):
        compute_tcs("206C-9X", Decimal("100"))
    with pytest.raises(ValueError):
        compute_tds("194J", Decimal("100"), Decimal("101"))
    with pytest.raises(ValueError):
        compute_tcs("206C-1H", Decimal("100"), Decimal("-1"))


def _tds_entry(**overrides) -> dict:
    base = {
        "section": "194J",
        "doc_date": "2026-05-10",
        "doc_number": "BILL-1",
        "doc_id": "b1",
        "party_name": "Acme Consultants",
        "pan": "ABCDE1234F",
        "pan_missing": False,
        "base_amount": "50000.00",
        "rate": "10",
        "tax_amount": "5000.00",
    }
    base.update(overrides)
    return base


def test_register_groups_sections_and_totals():
    out = assemble_tds_register(
        quarter="2026-Q1",
        period_start=date(2026, 4, 1),
        period_end=date(2026, 6, 30),
        tds_entries=[
            _tds_entry(),
            _tds_entry(doc_number="BILL-3", doc_date="2026-04-02", base_amount="10000.00", tax_amount="1000.00"),
            _tds_entry(section="194C", doc_number="BILL-2", rate="2", base_amount="30000.00", tax_amount="600.00",
                       pan=None, pan_missing=True),
        ],
        tcs_entries=[
            {"section": "206C-1H", "doc_date": "2026-06-01", "doc_number": "INV-9", "doc_id": "i9",
             "party_name": "Bulk Buyer", "pan": "AAACB1234C", "pan_missing": False,
             "base_amount": "118000.00", "rate": "0.1", "tax_amount": "118.00"},
        ],
    )
    assert out["quarter"] == "2026-Q1"
    tds = out["tds"]
    assert [s["section"] for s in tds["sections"]] == ["194C", "194J"]  # sorted
    s194j = tds["sections"][1]
    # entries sorted by (date, number) within the section
    assert [e["doc_number"] for e in s194j["entries"]] == ["BILL-3", "BILL-1"]
    assert s194j["total_base"] == "60000.00"
    assert s194j["total_tax"] == "6000.00"
    assert tds["total_tax"] == "6600.00"
    assert tds["entry_count"] == 3
    assert tds["pan_missing_count"] == 1
    tcs = out["tcs"]
    assert tcs["total_tax"] == "118.00"
    assert tcs["sections"][0]["label"] == TCS_SECTIONS["206C-1H"]["label"]


def test_register_empty_quarter():
    out = assemble_tds_register(
        quarter="2026-Q2",
        period_start=date(2026, 7, 1),
        period_end=date(2026, 9, 30),
        tds_entries=[],
        tcs_entries=[],
    )
    assert out["tds"]["sections"] == []
    assert out["tds"]["total_tax"] == "0.00"
    assert out["tcs"]["entry_count"] == 0


def test_register_keeps_unknown_section_with_fallback_label():
    # A document posted under a section later removed from the master must not
    # vanish from the statutory register.
    out = assemble_tds_register(
        quarter="2026-Q1",
        period_start=date(2026, 4, 1),
        period_end=date(2026, 6, 30),
        tds_entries=[_tds_entry(section="194X")],
        tcs_entries=[],
    )
    assert out["tds"]["sections"][0]["label"] == "194X"
    assert out["tds"]["total_tax"] == "5000.00"
