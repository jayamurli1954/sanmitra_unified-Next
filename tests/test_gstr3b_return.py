"""GSTR-3B return assembly — the pure assembler (no DB) and the ledger
period-balance aggregation (DB-backed, no Mongo)."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models import Account
from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import post_journal_entry
from app.modules.business.gst_returns import (
    _gst_gross_by_head,
    _ret_period,
    assemble_gstr3b,
)

APP_KEY = "mitrabooks"
ENTITY_ID = "primary"


# --------------------------------------------------------------------------- #
# Pure assembler
# --------------------------------------------------------------------------- #
def test_assemble_gstr3b_tables_and_setoff():
    report = assemble_gstr3b(
        gstin="29ABCDE1234F1Z5",
        period="2026-05",
        output={"igst": Decimal("1000"), "cgst": Decimal("500"), "sgst": Decimal("500")},
        itc_available={"igst": Decimal("300"), "cgst": Decimal("200"), "sgst": Decimal("200")},
        itc_reversed={"igst": Decimal("0"), "cgst": Decimal("50"), "sgst": Decimal("50")},
        outward_taxable_value=Decimal("50000"),
    )

    # 3.1(a) outward taxable supplies.
    taxable = report["outward_supplies"]["taxable"]
    assert taxable["taxable_value"] == Decimal("50000.00")
    assert taxable["igst"] == Decimal("1000.00")

    # 4. ITC — net = available - reversed.
    assert report["itc"]["net_available"] == {
        "igst": Decimal("300.00"), "cgst": Decimal("150.00"), "sgst": Decimal("150.00")
    }

    # 6.1 payment of tax: IGST has no usable IGST credit beyond 300, rest cash.
    pay = report["tax_payment"]
    assert pay["igst"] == {
        "tax_payable": Decimal("1000.00"),
        "paid_through_itc": Decimal("300.00"),
        "paid_in_cash": Decimal("700.00"),
    }
    assert pay["cgst"]["paid_in_cash"] == Decimal("350.00")
    assert pay["sgst"]["paid_in_cash"] == Decimal("350.00")

    assert report["totals"] == {
        "total_output_tax": Decimal("2000.00"),
        "total_itc_net": Decimal("600.00"),
        "total_cash_payable": Decimal("1400.00"),
    }


def test_assemble_gstr3b_gstn_json_shape():
    report = assemble_gstr3b(
        gstin="29ABCDE1234F1Z5", period="2026-05",
        output={"igst": Decimal("1000"), "cgst": Decimal("500"), "sgst": Decimal("500")},
        itc_available={"igst": Decimal("300"), "cgst": Decimal("200"), "sgst": Decimal("200")},
        itc_reversed={"igst": Decimal("0"), "cgst": Decimal("50"), "sgst": Decimal("50")},
        outward_taxable_value=Decimal("50000"),
    )
    j = report["gstn_json"]
    assert j["gstin"] == "29ABCDE1234F1Z5"
    assert j["ret_period"] == "052026"
    assert j["sup_details"]["osup_det"] == {
        "txval": 50000.0, "iamt": 1000.0, "camt": 500.0, "samt": 500.0, "csamt": 0.0
    }
    # ITC available rows: 4(A)(3) RCM first (zero here), then 4(A)(5) all-other.
    assert j["itc_elg"]["itc_avl"][0] == {
        "ty": "ISRC", "iamt": 0.0, "camt": 0.0, "samt": 0.0, "csamt": 0.0
    }
    assert j["itc_elg"]["itc_avl"][1] == {
        "ty": "OTH", "iamt": 300.0, "camt": 200.0, "samt": 200.0, "csamt": 0.0
    }
    assert j["itc_elg"]["itc_rev"][0]["camt"] == 50.0
    igst_pmt = next(p for p in j["tx_pmt"]["tx_pd"] if p["ty"] == "IGST")
    assert igst_pmt == {"ty": "IGST", "tx_payable": 1000.0, "tx_paid_itc": 300.0, "tx_paid_cash": 700.0}


def test_assemble_gstr3b_rcm_inward_and_itc_split():
    report = assemble_gstr3b(
        gstin=None, period="2026-05",
        output={"igst": Decimal("0"), "cgst": Decimal("500"), "sgst": Decimal("500")},
        # Ledger ITC includes the RCM ITC (booked on Input GST at posting).
        itc_available={"igst": Decimal("0"), "cgst": Decimal("950"), "sgst": Decimal("950")},
        itc_reversed={}, outward_taxable_value=Decimal("20000"),
        rcm_inward={"taxable_value": Decimal("10000"), "igst": Decimal("0"),
                    "cgst": Decimal("900"), "sgst": Decimal("900")},
        itc_rcm={"igst": Decimal("0"), "cgst": Decimal("900"), "sgst": Decimal("900")},
    )
    # 3.1(d) shows the RCM inward supply with its self-assessed tax.
    rcm = report["outward_supplies"]["inward_reverse_charge"]
    assert rcm["taxable_value"] == Decimal("10000.00")
    assert rcm["cgst"] == Decimal("900.00")
    # 4(A)(3) vs 4(A)(5): the RCM portion is split out of the ledger total.
    assert report["itc"]["available_rcm"]["cgst"] == Decimal("900.00")
    assert report["itc"]["available_all_other"]["cgst"] == Decimal("50.00")
    # Net ITC for set-off still uses the full ledger figure.
    assert report["itc"]["net_available"]["cgst"] == Decimal("950.00")
    # The 3.1(d) liability is cash-only and reported separately.
    assert report["rcm_cash_payable"] == Decimal("1800.00")
    # GSTN JSON carries the RCM rows.
    j = report["gstn_json"]
    assert j["sup_details"]["isup_rev"] == {
        "txval": 10000.0, "iamt": 0.0, "camt": 900.0, "samt": 900.0, "csamt": 0.0
    }
    assert j["itc_elg"]["itc_avl"][0] == {
        "ty": "ISRC", "iamt": 0.0, "camt": 900.0, "samt": 900.0, "csamt": 0.0
    }


def test_ret_period_format():
    assert _ret_period("2026-05") == "052026"
    assert _ret_period("2026-12") == "122026"


def test_assemble_gstr3b_empty_period_is_all_zero():
    report = assemble_gstr3b(
        gstin=None, period="2026-04",
        output={}, itc_available={}, itc_reversed={}, outward_taxable_value=Decimal("0"),
    )
    assert report["totals"]["total_output_tax"] == Decimal("0.00")
    assert report["totals"]["total_cash_payable"] == Decimal("0.00")
    assert report["gstn_json"]["gstin"] is None


# --------------------------------------------------------------------------- #
# Ledger period-balance aggregation (DB-backed)
# --------------------------------------------------------------------------- #
async def _acct(session, *, tenant_id, code, name, account_type, classification="real"):
    acc = Account(app_key=APP_KEY, tenant_id=tenant_id, accounting_entity_id=ENTITY_ID,
                  code=code, name=name, type=account_type, classification=classification)
    session.add(acc)
    return acc


async def _post(session, tenant_id, *, lines, key, entry_date):
    await post_journal_entry(
        session, tenant_id=tenant_id, app_key=APP_KEY, accounting_entity_id=ENTITY_ID,
        created_by="tester",
        payload=JournalPostRequest(entry_date=entry_date, description="t", reference=key, lines=lines),
        idempotency_key=key,
    )


@pytest.mark.asyncio
async def test_gst_gross_by_head_splits_output_itc_and_reversal(async_session: AsyncSession):
    tenant = "tenant-3b-1"
    debtor = await _acct(async_session, tenant_id=tenant, code="12001", name="Debtors", account_type="asset")
    creditor = await _acct(async_session, tenant_id=tenant, code="21001", name="Creditors", account_type="liability", classification="personal")
    sales = await _acct(async_session, tenant_id=tenant, code="41001", name="Sales", account_type="income", classification="nominal")
    purchases = await _acct(async_session, tenant_id=tenant, code="51001", name="Purchases", account_type="expense", classification="nominal")
    out_cgst = await _acct(async_session, tenant_id=tenant, code="22001", name="Output CGST", account_type="liability", classification="personal")
    out_sgst = await _acct(async_session, tenant_id=tenant, code="22002", name="Output SGST", account_type="liability", classification="personal")
    in_cgst = await _acct(async_session, tenant_id=tenant, code="14001", name="Input CGST", account_type="asset", classification="personal")
    in_sgst = await _acct(async_session, tenant_id=tenant, code="14002", name="Input SGST", account_type="asset", classification="personal")
    itc_rev = await _acct(async_session, tenant_id=tenant, code="14004", name="ITC Reversed Recoverable", account_type="asset", classification="personal")
    await async_session.commit()

    # Intra-state sale: output CGST 90 + SGST 90.
    await _post(async_session, tenant, key="sale", entry_date=date(2026, 5, 4), lines=[
        JournalLineIn(account_id=debtor.id, debit=Decimal("1180"), credit=Decimal("0")),
        JournalLineIn(account_id=sales.id, debit=Decimal("0"), credit=Decimal("1000")),
        JournalLineIn(account_id=out_cgst.id, debit=Decimal("0"), credit=Decimal("90")),
        JournalLineIn(account_id=out_sgst.id, debit=Decimal("0"), credit=Decimal("90")),
    ])
    # Intra-state purchase: input CGST 45 + SGST 45 (gross ITC).
    await _post(async_session, tenant, key="buy", entry_date=date(2026, 5, 6), lines=[
        JournalLineIn(account_id=purchases.id, debit=Decimal("500"), credit=Decimal("0")),
        JournalLineIn(account_id=in_cgst.id, debit=Decimal("45"), credit=Decimal("0")),
        JournalLineIn(account_id=in_sgst.id, debit=Decimal("45"), credit=Decimal("0")),
        JournalLineIn(account_id=creditor.id, debit=Decimal("0"), credit=Decimal("590")),
    ])
    # Rule-37 reversal: credit Input CGST 10 (reduces ITC), park as recoverable.
    await _post(async_session, tenant, key="rev", entry_date=date(2026, 5, 20), lines=[
        JournalLineIn(account_id=itc_rev.id, debit=Decimal("10"), credit=Decimal("0")),
        JournalLineIn(account_id=in_cgst.id, debit=Decimal("0"), credit=Decimal("10")),
    ])
    # An entry outside the period must be excluded.
    await _post(async_session, tenant, key="next-month", entry_date=date(2026, 6, 2), lines=[
        JournalLineIn(account_id=debtor.id, debit=Decimal("118"), credit=Decimal("0")),
        JournalLineIn(account_id=sales.id, debit=Decimal("0"), credit=Decimal("100")),
        JournalLineIn(account_id=out_cgst.id, debit=Decimal("0"), credit=Decimal("9")),
        JournalLineIn(account_id=out_sgst.id, debit=Decimal("0"), credit=Decimal("9")),
    ])

    output, itc_available, itc_reversed = await _gst_gross_by_head(
        async_session, tenant_id=tenant, app_key=APP_KEY,
        accounting_entity_id=ENTITY_ID, first=date(2026, 5, 1), last=date(2026, 5, 31),
    )
    assert output == {"igst": Decimal("0"), "cgst": Decimal("90"), "sgst": Decimal("90")}
    assert itc_available == {"igst": Decimal("0"), "cgst": Decimal("45"), "sgst": Decimal("45")}
    assert itc_reversed == {"igst": Decimal("0"), "cgst": Decimal("10"), "sgst": Decimal("0")}
