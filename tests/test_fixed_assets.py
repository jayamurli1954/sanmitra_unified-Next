"""Fixed assets — SLM/WDV depreciation math and the FY preview assembler.
Pure functions: assets and accumulated figures are passed in directly."""
from datetime import date
from decimal import Decimal

from app.modules.business.fixed_assets import (
    ACCUMULATED_DEPRECIATION_CODE,
    DEFAULT_DISPOSAL_BANK_CODE,
    DISPOSAL_GAIN_CODE,
    DISPOSAL_LOSS_CODE,
    assemble_depreciation_preview,
    assemble_disposal_plan,
    compute_depreciation,
)

FY_START = date(2026, 4, 1)
FY_END = date(2027, 3, 31)


def _asset(**overrides):
    base = {
        "asset_id": "a1",
        "asset_name": "Machine",
        "asset_account_code": "16003",
        "purchase_date": "2026-04-01",
        "cost": "100000.00",
        "salvage_value": "10000.00",
        "method": "slm",
        "useful_life_years": "5",
        "depreciation_rate": None,
        "status": "active",
    }
    base.update(overrides)
    return base


def _charge(asset, accumulated="0.00"):
    return compute_depreciation(asset, fy_start=FY_START, fy_end=FY_END,
                                accumulated_before=Decimal(accumulated))


def test_slm_full_year():
    # (100000 - 10000) / 5 = 18000 for a full year in service.
    assert _charge(_asset()) == Decimal("18000.00")


def test_slm_prorated_first_year():
    # In service 1 Oct 2026 -> 182 of 365 days.
    charge = _charge(_asset(purchase_date="2026-10-01"))
    assert charge == Decimal("8975.34")  # 18000 * 182/365


def test_wdv_uses_opening_book_value():
    asset = _asset(method="wdv", depreciation_rate="40", useful_life_years=None)
    # Year 1: 40% of 100000 = 40000.
    assert _charge(asset) == Decimal("40000.00")
    # Year 2: 40% of (100000 - 40000) = 24000.
    assert _charge(asset, accumulated="40000.00") == Decimal("24000.00")


def test_salvage_clamp_and_fully_depreciated():
    # Only 2000 of depreciable value left -> charge clamps to it.
    assert _charge(_asset(), accumulated="88000.00") == Decimal("2000.00")
    # Fully depreciated -> nothing.
    assert _charge(_asset(), accumulated="90000.00") == Decimal("0.00")


def test_not_yet_purchased_and_zero_life():
    assert _charge(_asset(purchase_date="2027-06-01")) == Decimal("0.00")
    assert _charge(_asset(useful_life_years="0")) == Decimal("0.00")


def test_preview_totals_and_already_run_guard():
    assets = [
        _asset(),
        _asset(asset_id="a2", asset_name="Car", method="wdv",
               depreciation_rate="20", useful_life_years=None, cost="500000.00", salvage_value="0.00"),
        _asset(asset_id="a3", asset_name="Sold machine", status="disposed"),
    ]
    out = assemble_depreciation_preview(
        financial_year="2026-27",
        assets=assets,
        accumulated_by_asset={"a2": Decimal("100000.00")},
        existing_run=None,
    )
    rows = {r["asset_id"]: r for r in out["rows"]}
    assert set(rows) == {"a1", "a2"}                       # disposed asset skipped
    assert rows["a1"]["depreciation"] == "18000.00"
    assert rows["a2"]["opening_book_value"] == "400000.00"
    assert rows["a2"]["depreciation"] == "80000.00"        # 20% WDV on 400000
    assert rows["a2"]["closing_book_value"] == "320000.00"
    assert out["total_depreciation"] == "98000.00"
    assert out["can_post"] is True

    rerun = assemble_depreciation_preview(
        financial_year="2026-27", assets=assets,
        accumulated_by_asset={}, existing_run={"run_id": "r1", "journal_entry_id": 9},
    )
    assert rerun["already_run"] is True
    assert rerun["can_post"] is False


def _accounts():
    codes = ["16003", ACCUMULATED_DEPRECIATION_CODE, DEFAULT_DISPOSAL_BANK_CODE, DISPOSAL_GAIN_CODE, DISPOSAL_LOSS_CODE]
    return {code: {"account_id": index + 1, "account_code": code, "code": code} for index, code in enumerate(codes)}


def test_disposal_plan_posts_loss_on_asset_disposal():
    out = assemble_disposal_plan(
        asset=_asset(cost="100000.00", asset_account_code="16003"),
        accumulated_depreciation=Decimal("40000.00"),
        sale_value=Decimal("50000.00"),
        disposal_date=date(2027, 3, 31),
        accounts_by_code=_accounts(),
    )

    by_code = {line["account_code"]: line for line in out["lines"]}
    assert out["book_value"] == "60000.00"
    assert out["loss"] == "10000.00"
    assert out["gain"] == "0.00"
    assert by_code[ACCUMULATED_DEPRECIATION_CODE]["debit"] == Decimal("40000.00")
    assert by_code[DEFAULT_DISPOSAL_BANK_CODE]["debit"] == Decimal("50000.00")
    assert by_code[DISPOSAL_LOSS_CODE]["debit"] == Decimal("10000.00")
    assert by_code["16003"]["credit"] == Decimal("100000.00")
    assert out["total_debit"] == out["total_credit"] == "100000.00"


def test_disposal_plan_posts_gain_on_asset_disposal():
    out = assemble_disposal_plan(
        asset=_asset(cost="100000.00", asset_account_code="16003"),
        accumulated_depreciation=Decimal("70000.00"),
        sale_value=Decimal("35000.00"),
        disposal_date=date(2027, 3, 31),
        accounts_by_code=_accounts(),
    )

    by_code = {line["account_code"]: line for line in out["lines"]}
    assert out["book_value"] == "30000.00"
    assert out["gain"] == "5000.00"
    assert out["loss"] == "0.00"
    assert by_code[ACCUMULATED_DEPRECIATION_CODE]["debit"] == Decimal("70000.00")
    assert by_code[DEFAULT_DISPOSAL_BANK_CODE]["debit"] == Decimal("35000.00")
    assert by_code["16003"]["credit"] == Decimal("100000.00")
    assert by_code[DISPOSAL_GAIN_CODE]["credit"] == Decimal("5000.00")
    assert out["total_debit"] == out["total_credit"] == "105000.00"


def test_disposal_plan_rejects_invalid_disposal_date_and_missing_accounts():
    try:
        assemble_disposal_plan(
            asset=_asset(cost="100000.00", asset_account_code="16003"),
            accumulated_depreciation=Decimal("0.00"),
            sale_value=Decimal("0.00"),
            disposal_date=date(2025, 3, 31),
            accounts_by_code=_accounts(),
        )
    except Exception as exc:
        assert "before purchase_date" in str(exc)
    else:
        raise AssertionError("expected invalid disposal date to fail")

    try:
        assemble_disposal_plan(
            asset=_asset(cost="100000.00", asset_account_code="16003"),
            accumulated_depreciation=Decimal("0.00"),
            sale_value=Decimal("50000.00"),
            disposal_date=date(2027, 3, 31),
            accounts_by_code={"16003": {"account_id": 1}},
        )
    except Exception as exc:
        detail = str(exc)
        assert ACCUMULATED_DEPRECIATION_CODE in detail
        assert DEFAULT_DISPOSAL_BANK_CODE in detail
        assert DISPOSAL_LOSS_CODE in detail
    else:
        raise AssertionError("expected missing disposal accounts to fail")
