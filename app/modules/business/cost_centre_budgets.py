"""Cost-centre budgets (enterprise Cost-Centre Accounting add-on).

A budget allocates spend/income limits per account under one cost centre for a
fiscal period (a calendar year, or a single month within it). Budget-vs-actual
pairs these allocations against the POSTED ledger (via
``get_cost_centre_account_actuals``) so the burn rate always ties to the books.

Lifecycle: DRAFT -> APPROVED -> LOCKED. Only APPROVED/LOCKED budgets drive the
variance report. Everything is scoped by tenant + app + accounting entity, and the
cost centre referenced must be an active cost centre in that same scope — a budget
can never point at another tenant's cost centre.
"""
from calendar import monthrange
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

BUDGETS_COLLECTION = "business_cost_centre_budgets"

BUDGET_STATUSES = ("DRAFT", "APPROVED", "LOCKED")
# Forward-only lifecycle.
_ALLOWED_TRANSITIONS = {"DRAFT": {"APPROVED"}, "APPROVED": {"LOCKED"}, "LOCKED": set()}

_CENT = Decimal("0.01")


def _q2(value) -> Decimal:
    return Decimal(str(value)).quantize(_CENT, rounding=ROUND_HALF_UP)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _scope(tenant_id: str, app_key: str, accounting_entity_id: str) -> dict:
    return {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}


def _response(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    for key in ("created_at", "updated_at"):
        if isinstance(doc.get(key), datetime):
            doc[key] = doc[key].isoformat()
    return doc


def _period_bounds(fiscal_year: int, fiscal_month: int | None) -> tuple[date, date]:
    """Calendar bounds for a budget period. fiscal_month None -> the whole year."""
    if fiscal_month is None:
        return date(fiscal_year, 1, 1), date(fiscal_year, 12, 31)
    last = monthrange(fiscal_year, fiscal_month)[1]
    return date(fiscal_year, fiscal_month, 1), date(fiscal_year, fiscal_month, last)


# --------------------------------------------------------------------------- #
# Masters / lifecycle.
# --------------------------------------------------------------------------- #

async def create_budget(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, payload: dict, created_by: str,
) -> dict:
    from app.accounting.service import AccountingValidationError
    from app.db.mongo import get_collection
    from app.modules.business.dimensions import validate_ledger_cost_centre_ids

    cost_centre_id = str(payload.get("cost_centre_id") or "").strip()
    if not cost_centre_id:
        raise AccountingValidationError("cost_centre_id is required")
    # The cost centre must exist and be active in THIS scope (tenant-isolation guard).
    await validate_ledger_cost_centre_ids(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        cost_centre_ids={cost_centre_id},
    )

    try:
        fiscal_year = int(payload.get("fiscal_year"))
    except (TypeError, ValueError):
        raise AccountingValidationError("fiscal_year must be a 4-digit year")
    fiscal_month = payload.get("fiscal_month")
    if fiscal_month is not None:
        fiscal_month = int(fiscal_month)
        if not 1 <= fiscal_month <= 12:
            raise AccountingValidationError("fiscal_month must be between 1 and 12")

    raw_lines = payload.get("lines") or []
    if not raw_lines:
        raise AccountingValidationError("A budget needs at least one allocation line")
    lines = []
    for ln in raw_lines:
        try:
            account_id = int(ln.get("account_id"))
            amount = _q2(ln.get("allocated_amount") or 0)
        except (TypeError, ValueError):
            raise AccountingValidationError("Each line needs account_id and allocated_amount")
        if amount < 0:
            raise AccountingValidationError("allocated_amount cannot be negative")
        lines.append({"account_id": account_id, "allocated_amount": str(amount)})

    col = get_collection(BUDGETS_COLLECTION)
    scope = _scope(tenant_id, app_key, accounting_entity_id)
    if await col.find_one({**scope, "cost_centre_id": cost_centre_id,
                           "fiscal_year": fiscal_year, "fiscal_month": fiscal_month}):
        raise AccountingValidationError("A budget already exists for this cost centre and period")

    now = _now()
    doc = {
        **scope,
        "budget_id": str(uuid4()),
        "cost_centre_id": cost_centre_id,
        "fiscal_year": fiscal_year,
        "fiscal_month": fiscal_month,
        "status": "DRAFT",
        "lines": lines,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    await col.insert_one(doc)
    return _response(doc)


async def list_budgets(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, cost_centre_id: str | None = None,
) -> dict:
    from app.db.mongo import get_collection

    filters = _scope(tenant_id, app_key, accounting_entity_id)
    if cost_centre_id:
        filters["cost_centre_id"] = cost_centre_id
    rows = await get_collection(BUDGETS_COLLECTION).find(filters).sort(
        [("fiscal_year", -1), ("fiscal_month", 1)]
    ).to_list(length=1000)
    items = [_response(r) for r in rows]
    return {"items": items, "count": len(items)}


async def set_budget_status(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, budget_id: str, status: str, updated_by: str,
) -> dict:
    from app.accounting.service import AccountingNotFoundError, AccountingValidationError
    from app.db.mongo import get_collection

    status = str(status or "").strip().upper()
    if status not in BUDGET_STATUSES:
        raise AccountingValidationError(f"status must be one of {', '.join(BUDGET_STATUSES)}")

    col = get_collection(BUDGETS_COLLECTION)
    scope = _scope(tenant_id, app_key, accounting_entity_id)
    row = await col.find_one({**scope, "budget_id": budget_id})
    if row is None:
        raise AccountingNotFoundError("Budget not found")
    current = str(row.get("status") or "DRAFT")
    if status != current and status not in _ALLOWED_TRANSITIONS.get(current, set()):
        raise AccountingValidationError(f"Cannot move budget from {current} to {status}")

    await col.update_one(
        {**scope, "budget_id": budget_id},
        {"$set": {"status": status, "updated_by": updated_by, "updated_at": _now()}},
    )
    row["status"] = status
    return _response(row)


# --------------------------------------------------------------------------- #
# Budget-vs-actual — pure assembly.
# --------------------------------------------------------------------------- #

def assemble_budget_vs_actual(*, budget: dict, actuals_by_account: dict[int, dict]) -> dict:
    """Pair a budget's allocations against per-account actuals. Variance =
    allocated − actual (positive = under budget). Accounts with actual spend but
    no allocation surface as 'unbudgeted' rows so nothing hides."""
    rows: list[dict] = []
    seen: set[int] = set()
    total_alloc = Decimal("0.00")
    total_actual = Decimal("0.00")

    for ln in budget.get("lines") or []:
        account_id = int(ln["account_id"])
        seen.add(account_id)
        allocated = _q2(ln.get("allocated_amount") or 0)
        meta = actuals_by_account.get(account_id, {})
        actual = _q2(meta.get("actual") or 0)
        total_alloc += allocated
        total_actual += actual
        burn = (actual / allocated * 100) if allocated > 0 else Decimal("0")
        rows.append({
            "account_id": account_id,
            "code": meta.get("code"),
            "name": meta.get("name"),
            "allocated": str(allocated),
            "actual": str(actual),
            "variance": str(_q2(allocated - actual)),
            "burn_rate_pct": str(_q2(burn)),
            "unbudgeted": False,
        })

    for account_id, meta in actuals_by_account.items():
        if account_id in seen:
            continue
        actual = _q2(meta.get("actual") or 0)
        if actual == 0:
            continue
        total_actual += actual
        rows.append({
            "account_id": account_id,
            "code": meta.get("code"),
            "name": meta.get("name"),
            "allocated": "0.00",
            "actual": str(actual),
            "variance": str(_q2(-actual)),
            "burn_rate_pct": "0.00",
            "unbudgeted": True,
        })

    rows.sort(key=lambda r: (not r["unbudgeted"], r.get("code") or ""))
    return {
        "cost_centre_id": budget.get("cost_centre_id"),
        "fiscal_year": budget.get("fiscal_year"),
        "fiscal_month": budget.get("fiscal_month"),
        "status": budget.get("status"),
        "rows": rows,
        "totals": {
            "allocated": str(_q2(total_alloc)),
            "actual": str(_q2(total_actual)),
            "variance": str(_q2(total_alloc - total_actual)),
        },
    }


async def build_budget_vs_actual(
    *, session, tenant_id: str, app_key: str, accounting_entity_id: str, budget_id: str,
) -> dict:
    from app.accounting.service import AccountingNotFoundError, get_cost_centre_account_actuals
    from app.db.mongo import get_collection

    scope = _scope(tenant_id, app_key, accounting_entity_id)
    budget = await get_collection(BUDGETS_COLLECTION).find_one({**scope, "budget_id": budget_id})
    if budget is None:
        raise AccountingNotFoundError("Budget not found")

    from_date, to_date = _period_bounds(int(budget["fiscal_year"]), budget.get("fiscal_month"))
    actuals = await get_cost_centre_account_actuals(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        cost_centre_id=budget["cost_centre_id"], from_date=from_date, to_date=to_date,
    )
    return assemble_budget_vs_actual(budget=_response(budget), actuals_by_account=actuals)
