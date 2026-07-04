"""Fixed-asset register + depreciation.

The register is metadata in Mongo: each asset records its cost, salvage value
and depreciation policy (SLM over a useful life, or WDV at a rate). The asset's
purchase itself is booked the normal way (purchase bill / voucher to a 16xxx
asset account) — registering an asset never posts.

Depreciation is the posting half, run per financial year with the usual
preview → confirm flow:

  * SLM: (cost − salvage) / useful life, day-prorated from the purchase date
    within the year.
  * WDV: rate% × opening written-down value, day-prorated in the first year.
  * Never depreciates below salvage value.
  * Posting writes ONE journal: Dr Depreciation Expense (54003) per asset's
    charge, Cr Accumulated Depreciation (16099, contra-asset). Idempotent per
    FY; the run history is stored so the next year's WDV opens correctly.
    Reverse the journal AND delete the run to redo a year (admin).
"""
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

FIXED_ASSETS_COLLECTION = "business_fixed_assets"
DEPRECIATION_RUNS_COLLECTION = "business_depreciation_runs"

DEPRECIATION_EXPENSE_CODE = "54003"
ACCUMULATED_DEPRECIATION_CODE = "16099"
DEFAULT_DISPOSAL_BANK_CODE = "11010"
DISPOSAL_GAIN_CODE = "42003"
DISPOSAL_LOSS_CODE = "54005"

_CENT = Decimal("0.01")


def _q2(value) -> Decimal:
    return Decimal(str(value)).quantize(_CENT, rounding=ROUND_HALF_UP)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _fy_dates(financial_year: str) -> tuple[date, date]:
    start_year = int(str(financial_year)[:4])
    return date(start_year, 4, 1), date(start_year + 1, 3, 31)


# --------------------------------------------------------------------------- #
# Pure depreciation math.
# --------------------------------------------------------------------------- #

def compute_depreciation(
    asset: dict,
    *,
    fy_start: date,
    fy_end: date,
    accumulated_before: Decimal,
) -> Decimal:
    """One asset's depreciation charge for the FY window.

    `accumulated_before` is everything depreciated in earlier years (opening
    accumulated + posted runs). Day-prorated when the asset enters service
    inside the window; clamped so book value never falls below salvage.
    """
    cost = _q2(asset.get("cost") or 0)
    salvage = _q2(asset.get("salvage_value") or 0)
    purchase = date.fromisoformat(str(asset.get("purchase_date"))[:10])
    if cost <= 0 or purchase > fy_end:
        return Decimal("0.00")

    depreciable_left = cost - salvage - _q2(accumulated_before)
    if depreciable_left <= 0:
        return Decimal("0.00")

    method = str(asset.get("method") or "slm").lower()
    if method == "wdv":
        rate = Decimal(str(asset.get("depreciation_rate") or 0)) / Decimal("100")
        opening_wdv = cost - _q2(accumulated_before)
        annual = opening_wdv * rate
    else:
        life_years = Decimal(str(asset.get("useful_life_years") or 0))
        if life_years <= 0:
            return Decimal("0.00")
        annual = (cost - salvage) / life_years

    # Pro-rate the first year by days in service within the window.
    window_days = (fy_end - fy_start).days + 1
    service_start = max(purchase, fy_start)
    service_days = (fy_end - service_start).days + 1
    charge = annual * Decimal(service_days) / Decimal(window_days)

    return _q2(min(charge, depreciable_left))


def assemble_depreciation_preview(
    *,
    financial_year: str,
    assets: list[dict],
    accumulated_by_asset: dict[str, Decimal],
    existing_run: dict | None,
) -> dict:
    """Per-asset depreciation schedule for the FY + totals. Pure: callers
    fetch the register and the prior accumulated figures."""
    fy_start, fy_end = _fy_dates(financial_year)
    rows: list[dict] = []
    total = Decimal("0.00")
    for asset in assets:
        if str(asset.get("status") or "active") != "active":
            continue
        accumulated = _q2(accumulated_by_asset.get(str(asset.get("asset_id")), Decimal("0.00")))
        charge = compute_depreciation(asset, fy_start=fy_start, fy_end=fy_end, accumulated_before=accumulated)
        cost = _q2(asset.get("cost") or 0)
        rows.append({
            "asset_id": asset.get("asset_id"),
            "asset_name": asset.get("asset_name"),
            "asset_account_code": asset.get("asset_account_code"),
            "method": asset.get("method"),
            "purchase_date": asset.get("purchase_date"),
            "cost": str(cost),
            "accumulated_before": str(accumulated),
            "opening_book_value": str(_q2(cost - accumulated)),
            "depreciation": str(charge),
            "closing_book_value": str(_q2(cost - accumulated - charge)),
        })
        total += charge
    return {
        "financial_year": financial_year,
        "from_date": fy_start.isoformat(),
        "to_date": fy_end.isoformat(),
        "rows": rows,
        "asset_count": len(rows),
        "total_depreciation": str(_q2(total)),
        "already_run": bool(existing_run),
        "existing_run": existing_run,
        "can_post": total > 0 and not existing_run,
        "notes": [
            "SLM: (cost − salvage) / useful life. WDV: rate% on the opening book value. First-year charges are day-prorated from the purchase date.",
            "Depreciation never takes an asset below its salvage value.",
            "Posting writes one journal: Dr Depreciation Expense (54003), Cr Accumulated Depreciation (16099). Run it before the year-end close.",
        ],
    }


def assemble_disposal_plan(
    *,
    asset: dict,
    accumulated_depreciation: Decimal,
    sale_value: Decimal,
    disposal_date: date,
    accounts_by_code: dict[str, dict],
    cash_bank_account_code: str = DEFAULT_DISPOSAL_BANK_CODE,
) -> dict:
    """Build the balanced journal plan for disposing one fixed asset."""
    from app.accounting.service import AccountingValidationError

    cost = _q2(asset.get("cost") or 0)
    accumulated = _q2(accumulated_depreciation)
    proceeds = _q2(sale_value)
    if cost <= 0:
        raise AccountingValidationError("asset cost must be greater than zero")
    if accumulated < 0 or accumulated > cost:
        raise AccountingValidationError("accumulated depreciation cannot be negative or exceed cost")
    if proceeds < 0:
        raise AccountingValidationError("sale_value cannot be negative")
    try:
        purchased_on = date.fromisoformat(str(asset.get("purchase_date") or "")[:10])
    except ValueError:
        raise AccountingValidationError("asset purchase_date is invalid")
    if disposal_date < purchased_on:
        raise AccountingValidationError("disposal_date cannot be before purchase_date")

    asset_code = str(asset.get("asset_account_code") or "").strip()
    bank_code = str(cash_bank_account_code or DEFAULT_DISPOSAL_BANK_CODE).strip()
    asset_account = accounts_by_code.get(asset_code)
    contra_account = accounts_by_code.get(ACCUMULATED_DEPRECIATION_CODE)
    bank_account = accounts_by_code.get(bank_code) if proceeds > 0 else None
    gain_account = accounts_by_code.get(DISPOSAL_GAIN_CODE)
    loss_account = accounts_by_code.get(DISPOSAL_LOSS_CODE)
    missing = []
    if asset_account is None:
        missing.append(asset_code or "<asset_account_code>")
    if contra_account is None:
        missing.append(ACCUMULATED_DEPRECIATION_CODE)
    if proceeds > 0 and bank_account is None:
        missing.append(bank_code)

    book_value = _q2(cost - accumulated)
    gain = _q2(proceeds - book_value) if proceeds > book_value else Decimal("0.00")
    loss = _q2(book_value - proceeds) if proceeds < book_value else Decimal("0.00")
    if gain > 0 and gain_account is None:
        missing.append(DISPOSAL_GAIN_CODE)
    if loss > 0 and loss_account is None:
        missing.append(DISPOSAL_LOSS_CODE)
    if missing:
        raise AccountingValidationError(f"Fixed-asset disposal accounts missing from the chart: {', '.join(missing)}")

    lines: list[dict] = []
    if accumulated > 0:
        lines.append({
            "account_id": contra_account["account_id"],
            "account_code": ACCUMULATED_DEPRECIATION_CODE,
            "debit": accumulated,
            "credit": Decimal("0.00"),
        })
    if proceeds > 0:
        lines.append({
            "account_id": bank_account["account_id"],
            "account_code": bank_code,
            "debit": proceeds,
            "credit": Decimal("0.00"),
        })
    if loss > 0:
        lines.append({
            "account_id": loss_account["account_id"],
            "account_code": DISPOSAL_LOSS_CODE,
            "debit": loss,
            "credit": Decimal("0.00"),
        })
    lines.append({
        "account_id": asset_account["account_id"],
        "account_code": asset_code,
        "debit": Decimal("0.00"),
        "credit": cost,
    })
    if gain > 0:
        lines.append({
            "account_id": gain_account["account_id"],
            "account_code": DISPOSAL_GAIN_CODE,
            "debit": Decimal("0.00"),
            "credit": gain,
        })

    total_debit = _q2(sum((line["debit"] for line in lines), Decimal("0.00")))
    total_credit = _q2(sum((line["credit"] for line in lines), Decimal("0.00")))
    if total_debit != total_credit:
        raise AccountingValidationError("Fixed-asset disposal journal is not balanced")
    return {
        "book_value": str(book_value),
        "sale_value": str(proceeds),
        "gain": str(gain),
        "loss": str(loss),
        "total_debit": str(total_debit),
        "total_credit": str(total_credit),
        "lines": lines,
    }


# --------------------------------------------------------------------------- #
# Async service layer.
# --------------------------------------------------------------------------- #

def _scope(tenant_id: str, app_key: str, accounting_entity_id: str) -> dict:
    return {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}


def _asset_response(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    for key in ("created_at", "updated_at"):
        if isinstance(doc.get(key), datetime):
            doc[key] = doc[key].isoformat()
    return doc


async def create_fixed_asset(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    payload: dict,
    created_by: str,
) -> dict:
    from app.accounting.service import AccountingValidationError
    from app.db.mongo import get_collection

    name = str(payload.get("asset_name") or "").strip()
    if not name:
        raise AccountingValidationError("asset_name is required")
    try:
        purchase_date = date.fromisoformat(str(payload.get("purchase_date") or "")[:10])
    except ValueError:
        raise AccountingValidationError("purchase_date must be YYYY-MM-DD")
    cost = _q2(payload.get("cost") or 0)
    if cost <= 0:
        raise AccountingValidationError("cost must be greater than zero")
    salvage = _q2(payload.get("salvage_value") or 0)
    if salvage < 0 or salvage >= cost:
        raise AccountingValidationError("salvage_value must be >= 0 and below cost")
    method = str(payload.get("method") or "slm").lower()
    if method not in ("slm", "wdv"):
        raise AccountingValidationError("method must be 'slm' or 'wdv'")
    useful_life = Decimal(str(payload.get("useful_life_years") or 0))
    rate = Decimal(str(payload.get("depreciation_rate") or 0))
    if method == "slm" and useful_life <= 0:
        raise AccountingValidationError("useful_life_years is required for SLM")
    if method == "wdv" and (rate <= 0 or rate > 100):
        raise AccountingValidationError("depreciation_rate (0-100) is required for WDV")
    opening_accumulated = _q2(payload.get("opening_accumulated_depreciation") or 0)
    if opening_accumulated < 0 or opening_accumulated > cost - salvage:
        raise AccountingValidationError("opening_accumulated_depreciation must be between 0 and (cost − salvage)")

    now = _now()
    doc = {
        **_scope(tenant_id, app_key, accounting_entity_id),
        "asset_id": str(uuid4()),
        "asset_name": name,
        "asset_account_code": str(payload.get("asset_account_code") or "16001").strip(),
        "purchase_date": purchase_date.isoformat(),
        "cost": str(cost),
        "salvage_value": str(salvage),
        "method": method,
        "useful_life_years": str(useful_life) if useful_life > 0 else None,
        "depreciation_rate": str(rate) if rate > 0 else None,
        # For assets migrated mid-life: depreciation already charged in the old books.
        "opening_accumulated_depreciation": str(opening_accumulated),
        "notes": str(payload.get("notes") or "").strip() or None,
        "status": "active",
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    await get_collection(FIXED_ASSETS_COLLECTION).insert_one(doc)
    return _asset_response(doc)


async def _accumulated_by_asset(scope: dict) -> dict[str, Decimal]:
    """Opening accumulated depreciation + all posted run rows, per asset."""
    from app.db.mongo import get_collection

    totals: dict[str, Decimal] = {}
    assets = await get_collection(FIXED_ASSETS_COLLECTION).find(scope).to_list(length=2000)
    for asset in assets:
        totals[str(asset["asset_id"])] = _q2(asset.get("opening_accumulated_depreciation") or 0)
    runs = await get_collection(DEPRECIATION_RUNS_COLLECTION).find({**scope, "status": "posted"}).to_list(length=200)
    for run in runs:
        for row in run.get("rows") or []:
            key = str(row.get("asset_id"))
            totals[key] = totals.get(key, Decimal("0.00")) + _q2(row.get("depreciation") or 0)
    return totals


async def list_fixed_assets(*, tenant_id: str, app_key: str, accounting_entity_id: str) -> dict:
    from app.db.mongo import get_collection

    scope = _scope(tenant_id, app_key, accounting_entity_id)
    rows = await get_collection(FIXED_ASSETS_COLLECTION).find(scope).sort("purchase_date", 1).to_list(length=2000)
    accumulated = await _accumulated_by_asset(scope)
    items = []
    total_cost = Decimal("0.00")
    total_book = Decimal("0.00")
    for row in rows:
        item = _asset_response(row)
        acc = accumulated.get(str(row["asset_id"]), Decimal("0.00"))
        cost = _q2(row.get("cost") or 0)
        item["accumulated_depreciation"] = str(_q2(acc))
        item["book_value"] = str(_q2(cost - acc))
        total_cost += cost
        total_book += cost - acc
        items.append(item)
    return {"items": items, "count": len(items),
            "total_cost": str(_q2(total_cost)), "total_book_value": str(_q2(total_book))}


async def _find_run(scope: dict, financial_year: str) -> dict | None:
    from app.db.mongo import get_collection

    run = await get_collection(DEPRECIATION_RUNS_COLLECTION).find_one(
        {**scope, "financial_year": financial_year, "status": "posted"}
    )
    if run is None:
        return None
    run.pop("_id", None)
    if isinstance(run.get("created_at"), datetime):
        run["created_at"] = run["created_at"].isoformat()
    return run


async def build_depreciation_preview(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, financial_year: str,
) -> dict:
    from app.db.mongo import get_collection

    scope = _scope(tenant_id, app_key, accounting_entity_id)
    assets = await get_collection(FIXED_ASSETS_COLLECTION).find(scope).sort("purchase_date", 1).to_list(length=2000)
    accumulated = await _accumulated_by_asset(scope)

    # Accumulated BEFORE this FY: subtract this FY's own posted run (if any),
    # so previewing an already-run year shows the original figures.
    existing_run = await _find_run(scope, financial_year)
    if existing_run:
        for row in existing_run.get("rows") or []:
            key = str(row.get("asset_id"))
            accumulated[key] = accumulated.get(key, Decimal("0.00")) - _q2(row.get("depreciation") or 0)

    return assemble_depreciation_preview(
        financial_year=financial_year,
        assets=[_asset_response(a) for a in assets],
        accumulated_by_asset=accumulated,
        existing_run=existing_run,
    )


async def post_depreciation_run(
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
    from app.accounting.service import (
        AccountingValidationError,
        initialize_default_chart_of_accounts,
        post_journal_entry,
    )
    from app.db.mongo import get_collection
    from app.modules.business.opening_close import _account_lookups

    preview = await build_depreciation_preview(
        tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, financial_year=financial_year,
    )
    if preview["already_run"]:
        run = preview["existing_run"]
        raise AccountingValidationError(
            f"Depreciation for FY {financial_year} is already posted (run {run['run_id']}, "
            f"journal entry #{run['journal_entry_id']}). Reverse that entry and delete the run to redo it."
        )
    total = Decimal(preview["total_depreciation"])
    if total <= 0:
        raise AccountingValidationError(f"No depreciation to post for FY {financial_year}")

    if app_key == "mitrabooks":
        await initialize_default_chart_of_accounts(
            session, tenant_id=tenant_id, app_key=app_key,
            accounting_entity_id=accounting_entity_id, organization_type="BUSINESS",
        )
    accounts_by_code, _ = await _account_lookups(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    expense = accounts_by_code.get(DEPRECIATION_EXPENSE_CODE)
    contra = accounts_by_code.get(ACCUMULATED_DEPRECIATION_CODE)
    if expense is None or contra is None:
        raise AccountingValidationError(
            f"Depreciation accounts missing from the chart "
            f"({DEPRECIATION_EXPENSE_CODE} / {ACCUMULATED_DEPRECIATION_CODE})"
        )

    fy_end = _fy_dates(financial_year)[1]
    journal_entry, created = await post_journal_entry(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        created_by=created_by,
        payload=JournalPostRequest(
            entry_date=fy_end,
            description=f"Depreciation FY {financial_year}",
            reference=f"DEP-{financial_year}",
            source_module="business",
            source_document_type="depreciation",
            source_document_id=f"depreciation:{financial_year}",
            lines=[
                JournalLineIn(account_id=expense["account_id"], debit=total, credit=Decimal("0")),
                JournalLineIn(account_id=contra["account_id"], debit=Decimal("0"), credit=total),
            ],
        ),
        idempotency_key=idempotency_key or f"depreciation:{accounting_entity_id}:{financial_year}",
    )

    run_doc = {
        **_scope(tenant_id, app_key, accounting_entity_id),
        "run_id": str(uuid4()),
        "financial_year": financial_year,
        "rows": [{"asset_id": r["asset_id"], "asset_name": r["asset_name"], "depreciation": r["depreciation"]}
                 for r in preview["rows"] if Decimal(r["depreciation"]) > 0],
        "total_depreciation": preview["total_depreciation"],
        "journal_entry_id": journal_entry.id,
        "status": "posted",
        "created_by": created_by,
        "created_at": _now(),
    }
    await get_collection(DEPRECIATION_RUNS_COLLECTION).insert_one(run_doc)
    return {
        "run_id": run_doc["run_id"],
        "journal_entry_id": journal_entry.id,
        "created": created,
        "financial_year": financial_year,
        "entry_date": fy_end.isoformat(),
        "total_depreciation": preview["total_depreciation"],
        "asset_count": len(run_doc["rows"]),
    }


async def dispose_fixed_asset(
    session,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    asset_id: str,
    payload: dict,
    created_by: str,
    idempotency_key: str | None = None,
) -> dict:
    from app.accounting.schemas import JournalLineIn, JournalPostRequest
    from app.accounting.service import (
        AccountingValidationError,
        initialize_default_chart_of_accounts,
        post_journal_entry,
        reverse_journal_entry,
    )
    from app.db.mongo import get_collection
    from app.modules.business.opening_close import _account_lookups

    scope = _scope(tenant_id, app_key, accounting_entity_id)
    assets_col = get_collection(FIXED_ASSETS_COLLECTION)
    asset = await assets_col.find_one({**scope, "asset_id": asset_id})
    if asset is None:
        raise AccountingValidationError("Fixed asset not found")
    if str(asset.get("status") or "active") == "disposed":
        return {
            "asset_id": asset_id,
            "status": "disposed",
            "created": False,
            "journal_entry_id": asset.get("disposal_journal_entry_id"),
            "disposal_date": asset.get("disposal_date"),
            "sale_value": asset.get("disposal_sale_value"),
            "book_value": asset.get("disposal_book_value"),
            "gain": asset.get("disposal_gain"),
            "loss": asset.get("disposal_loss"),
        }

    try:
        disposal_date = date.fromisoformat(str(payload.get("disposal_date") or "")[:10])
    except ValueError:
        raise AccountingValidationError("disposal_date must be YYYY-MM-DD")
    sale_value = _q2(payload.get("sale_value") or 0)
    if sale_value < 0:
        raise AccountingValidationError("sale_value cannot be negative")
    cash_bank_account_code = str(payload.get("cash_bank_account_code") or DEFAULT_DISPOSAL_BANK_CODE).strip()
    reason = str(payload.get("reason") or "Fixed asset disposal").strip() or "Fixed asset disposal"

    if app_key == "mitrabooks":
        await initialize_default_chart_of_accounts(
            session, tenant_id=tenant_id, app_key=app_key,
            accounting_entity_id=accounting_entity_id, organization_type="BUSINESS",
        )
    accounts_by_code, _ = await _account_lookups(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    accumulated = (await _accumulated_by_asset(scope)).get(asset_id, Decimal("0.00"))
    plan = assemble_disposal_plan(
        asset=_asset_response(asset),
        accumulated_depreciation=accumulated,
        sale_value=sale_value,
        disposal_date=disposal_date,
        accounts_by_code=accounts_by_code,
        cash_bank_account_code=cash_bank_account_code,
    )

    journal_entry, created = await post_journal_entry(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        created_by=created_by,
        payload=JournalPostRequest(
            entry_date=disposal_date,
            description=f"Dispose fixed asset: {asset.get('asset_name')}",
            reference=f"FAD-{asset_id[:8]}",
            source_module="business",
            source_document_type="fixed_asset_disposal",
            source_document_id=asset_id,
            lines=[
                JournalLineIn(
                    account_id=line["account_id"],
                    debit=line["debit"],
                    credit=line["credit"],
                )
                for line in plan["lines"]
            ],
        ),
        idempotency_key=idempotency_key or f"fixed-asset-disposal:{accounting_entity_id}:{asset_id}",
    )

    update_doc = {
        "status": "disposed",
        "disposal_date": disposal_date.isoformat(),
        "disposal_sale_value": plan["sale_value"],
        "disposal_book_value": plan["book_value"],
        "disposal_gain": plan["gain"],
        "disposal_loss": plan["loss"],
        "disposal_reason": reason,
        "disposal_cash_bank_account_code": cash_bank_account_code if sale_value > 0 else None,
        "disposal_journal_entry_id": journal_entry.id,
        "disposed_by": created_by,
        "disposed_at": _now(),
        "updated_at": _now(),
    }
    try:
        result = await assets_col.update_one(
            {**scope, "asset_id": asset_id, "status": "active"},
            {"$set": update_doc},
        )
    except Exception as exc:
        try:
            await reverse_journal_entry(
                session,
                tenant_id=tenant_id,
                app_key=app_key,
                accounting_entity_id=accounting_entity_id,
                journal_id=int(journal_entry.id),
                created_by=created_by,
                reversal_date=disposal_date,
                reason=f"Compensation after fixed asset disposal persistence failure for {asset_id}",
                idempotency_key=f"fixed-asset-disposal-compensate:{asset_id}:{journal_entry.id}",
            )
        except Exception as reversal_exc:
            raise AccountingValidationError(
                "Fixed asset disposal persistence failed after journal posting, and automatic reversal also failed"
            ) from reversal_exc
        raise AccountingValidationError("Fixed asset disposal persistence failed; posted journal was reversed") from exc
    if getattr(result, "modified_count", 0) != 1:
        existing = await assets_col.find_one({**scope, "asset_id": asset_id})
        if existing and str(existing.get("status")) == "disposed":
            return {
                "asset_id": asset_id,
                "status": "disposed",
                "created": False,
                "journal_entry_id": existing.get("disposal_journal_entry_id"),
                "disposal_date": existing.get("disposal_date"),
                "sale_value": existing.get("disposal_sale_value"),
                "book_value": existing.get("disposal_book_value"),
                "gain": existing.get("disposal_gain"),
                "loss": existing.get("disposal_loss"),
            }
        await reverse_journal_entry(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=accounting_entity_id,
            journal_id=int(journal_entry.id),
            created_by=created_by,
            reversal_date=disposal_date,
            reason=f"Compensation after fixed asset disposal status race for {asset_id}",
            idempotency_key=f"fixed-asset-disposal-race:{asset_id}:{journal_entry.id}",
        )
        raise AccountingValidationError("Fixed asset was not active when disposal was posted; journal was reversed")

    return {
        "asset_id": asset_id,
        "status": "disposed",
        "created": created,
        "journal_entry_id": journal_entry.id,
        "disposal_date": disposal_date.isoformat(),
        "sale_value": plan["sale_value"],
        "book_value": plan["book_value"],
        "gain": plan["gain"],
        "loss": plan["loss"],
        "total_debit": plan["total_debit"],
        "total_credit": plan["total_credit"],
    }
