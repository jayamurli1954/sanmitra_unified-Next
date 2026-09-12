"""ADR-014 Path A: map MitraBooks report reads into MIS facts (Decimal only)."""
from __future__ import annotations

import calendar
import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.modules.office_ai.connectors import mitrabooks_connector
from app.modules.office_ai.services import mis_store

_CENT = Decimal("0.01")
_SOURCE = "mitrabooks"
_PERIOD_YM = re.compile(r"^(\d{4})-(\d{2})$")
_PERIOD_RANGE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})$")


class MISLiveIngestError(ValueError):
    pass


def parse_pack_period(period: str) -> tuple[date, date, date]:
    """Return (from_date, to_date, as_of) for a pack period string."""
    raw = str(period or "").strip()
    ym = _PERIOD_YM.match(raw)
    if ym:
        year, month = int(ym.group(1)), int(ym.group(2))
        if month < 1 or month > 12:
            raise MISLiveIngestError("unsupported_period")
        last = calendar.monthrange(year, month)[1]
        from_date = date(year, month, 1)
        to_date = date(year, month, last)
        return from_date, to_date, to_date
    rng = _PERIOD_RANGE.match(raw)
    if rng:
        from_date = date.fromisoformat(rng.group(1))
        to_date = date.fromisoformat(rng.group(2))
        if to_date < from_date:
            raise MISLiveIngestError("unsupported_period")
        return from_date, to_date, to_date
    raise MISLiveIngestError("unsupported_period")


def _money(value: Any) -> tuple[str, int]:
    amount = Decimal(str(value)).quantize(_CENT, rounding=ROUND_HALF_UP)
    minor = int((amount * 100).to_integral_value(rounding=ROUND_HALF_UP))
    return format(amount, "f"), minor


def _assert_decimal(value: Any) -> None:
    if isinstance(value, float):
        raise MISLiveIngestError("float amounts are not allowed in live MIS mapping")


def _fact(
    *,
    entity_type: str,
    period: str,
    as_of: str,
    source_id: str,
    source_ref: str,
    amount: Any,
    dimensions: dict[str, Any],
) -> dict[str, Any]:
    _assert_decimal(amount)
    amount_decimal, amount_minor = _money(amount)
    return {
        "entity_type": entity_type,
        "period": period,
        "as_of": as_of,
        "source_system": _SOURCE,
        "source_id": source_id,
        "source_ref": source_ref,
        "amount_decimal": amount_decimal,
        "amount_minor": amount_minor,
        "currency": "INR",
        "dimensions": dimensions,
    }


def _map_pnl(report: dict[str, Any], *, period: str, as_of: str) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for line in report.get("lines") or []:
        name = str(line.get("account_name") or line.get("account_code") or "Account").strip()
        code = str(line.get("account_code") or line.get("account_id") or name).strip()
        amount = line.get("net_amount")
        if amount is None:
            continue
        _assert_decimal(amount)
        facts.append(
            _fact(
                entity_type="pnl_line",
                period=period,
                as_of=as_of,
                source_id=f"pnl-{code}".lower(),
                source_ref=f"mitrabooks:pnl:{code}",
                amount=amount,
                dimensions={
                    "line": name,
                    "account_type": str(line.get("account_type") or ""),
                    "account_code": code,
                },
            )
        )
    for label, key, code in (
        ("Revenue", "income_total", "REV"),
        ("Operating Expenses", "expense_total", "OPEX"),
        ("PAT", "net_profit", "PAT"),
    ):
        total = report.get(key)
        if total is None:
            continue
        facts.append(
            _fact(
                entity_type="pnl_line",
                period=period,
                as_of=as_of,
                source_id=f"pnl-{code.lower()}",
                source_ref=f"mitrabooks:pnl:{code}",
                amount=total,
                dimensions={"line": label, "rollup": "true"},
            )
        )
    return facts


def _map_bs(report: dict[str, Any], *, period: str, as_of: str) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for section, key in (("asset", "assets"), ("liability", "liabilities"), ("equity", "equity")):
        for line in report.get(key) or []:
            name = str(line.get("account_name") or line.get("account_code") or "Account").strip()
            code = str(line.get("account_code") or line.get("account_id") or name).strip()
            amount = line.get("balance")
            if amount is None:
                continue
            facts.append(
                _fact(
                    entity_type="bs_line",
                    period=period,
                    as_of=as_of,
                    source_id=f"bs-{section}-{code}".lower(),
                    source_ref=f"mitrabooks:bs:{section}:{code}",
                    amount=amount,
                    dimensions={"line": name, "section": section, "account_code": code},
                )
            )
    for label, key, code in (
        ("Total Assets", "total_assets", "ASSETS"),
        ("Total Liabilities", "total_liabilities", "LIAB"),
        ("Total Equity", "total_equity", "EQ"),
    ):
        total = report.get(key)
        if total is None:
            continue
        facts.append(
            _fact(
                entity_type="bs_line",
                period=period,
                as_of=as_of,
                source_id=f"bs-{code.lower()}",
                source_ref=f"mitrabooks:bs:{code}",
                amount=total,
                dimensions={"line": label, "rollup": "true"},
            )
        )
    return facts


def _map_cash(report: dict[str, Any], *, period: str, as_of: str) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for label, key, code in (
        ("Receipts", "total_receipts", "CFI"),
        ("Payments", "total_payments", "CFO"),
        ("Net Change", "net", "NET"),
    ):
        total = report.get(key)
        if total is None:
            continue
        facts.append(
            _fact(
                entity_type="cash_summary",
                period=period,
                as_of=as_of,
                source_id=f"cf-{code.lower()}",
                source_ref=f"mitrabooks:cash:{code}",
                amount=total,
                dimensions={"line": label, "rollup": "true"},
            )
        )
    return facts


def _map_aging_side(side: str, aging: dict[str, Any] | None, *, period: str, as_of: str) -> list[dict[str, Any]]:
    if not aging:
        return []
    facts: list[dict[str, Any]] = []
    totals = aging.get("totals") or {}
    for bucket, raw in totals.items():
        facts.append(
            _fact(
                entity_type="aging_bucket",
                period=period,
                as_of=as_of,
                source_id=f"aging-{side.lower()}-{bucket}".lower(),
                source_ref=f"mitrabooks:aging:{side}:{bucket}",
                amount=raw,
                dimensions={"side": side, "bucket": str(bucket)},
            )
        )
    grand = aging.get("grand_total")
    if grand is not None:
        facts.append(
            _fact(
                entity_type="aging_bucket",
                period=period,
                as_of=as_of,
                source_id=f"aging-{side.lower()}-total",
                source_ref=f"mitrabooks:aging:{side}:total",
                amount=grand,
                dimensions={"side": side, "bucket": "Total", "rollup": "true"},
            )
        )
    return facts


def compute_live_data_quality(facts: list[dict[str, Any]], warnings: list[str]) -> tuple[int, dict[str, Any]]:
    types = {str(f.get("entity_type") or "") for f in facts}
    checks = {
        "has_pnl": "pnl_line" in types,
        "has_bs": "bs_line" in types,
        "has_cash": "cash_summary" in types,
        "has_aging": "aging_bucket" in types,
        "no_warnings": len(warnings) == 0,
    }
    score = int(round(100 * (sum(1 for ok in checks.values() if ok) / len(checks))))
    return score, {"checks": checks, "fact_count": len(facts), "warning_count": len(warnings)}


async def probe_live_status(
    *,
    tenant_id: str,
    tenant: dict[str, Any],
    session=None,
    accounting_entity_id: str = "primary",
) -> dict[str, Any]:
    from app.modules.office_ai.connectors.base import tenant_has_module

    books = tenant_has_module(tenant, "business") or tenant_has_module(tenant, "accounting")
    if not books:
        return {
            "enabled": False,
            "reason": "business_module_off",
            "session_available": session is not None,
            "adr_014_live_mitrabooks": True,
        }
    if session is None:
        return {
            "enabled": False,
            "reason": "session_required",
            "session_available": False,
            "adr_014_live_mitrabooks": True,
        }
    today = date.today()
    from_date = today.replace(day=1)
    pnl = await mitrabooks_connector.get_mis_profit_loss(
        tenant_id=tenant_id,
        tenant=tenant,
        session=session,
        from_date=from_date,
        to_date=today,
        accounting_entity_id=accounting_entity_id,
    )
    line_count = len(pnl.get("lines") or [])
    return {
        "enabled": bool(pnl.get("enabled")) and not pnl.get("error"),
        "reason": pnl.get("reason") or pnl.get("error") or ("empty_books" if line_count == 0 else None),
        "session_available": True,
        "has_pnl_rows": line_count > 0,
        "adr_014_live_mitrabooks": True,
    }


async def import_from_mitrabooks(
    *,
    tenant_id: str,
    tenant: dict[str, Any],
    user: dict[str, Any],
    pack_id: str,
    session=None,
    accounting_entity_id: str = "primary",
) -> dict[str, Any]:
    pack = await mis_store.get_pack(tenant_id=tenant_id, pack_id=pack_id)
    if pack is None:
        raise mis_store.MISPackNotFoundError(f"MIS pack not found: {pack_id}")
    if not mis_store.pack_is_editable(pack):
        raise mis_store.MISImmutableError(
            f"Pack {pack_id} is immutable (status={pack.get('status')}); create a new revision instead"
        )
    period = str(pack.get("period") or "").strip()
    try:
        from_date, to_date, as_of = parse_pack_period(period)
    except MISLiveIngestError as exc:
        raise MISLiveIngestError(str(exc)) from exc

    from app.modules.office_ai.connectors.base import tenant_has_module

    if not (tenant_has_module(tenant, "business") or tenant_has_module(tenant, "accounting")):
        raise MISLiveIngestError("business_module_off")
    if session is None:
        raise MISLiveIngestError("session_required")

    warnings: list[str] = []
    pnl = await mitrabooks_connector.get_mis_profit_loss(
        tenant_id=tenant_id,
        tenant=tenant,
        session=session,
        from_date=from_date,
        to_date=to_date,
        accounting_entity_id=accounting_entity_id,
    )
    bs = await mitrabooks_connector.get_mis_balance_sheet(
        tenant_id=tenant_id,
        tenant=tenant,
        session=session,
        as_of=as_of,
        accounting_entity_id=accounting_entity_id,
    )
    cash = await mitrabooks_connector.get_mis_cash_movement(
        tenant_id=tenant_id,
        tenant=tenant,
        session=session,
        from_date=from_date,
        to_date=to_date,
        accounting_entity_id=accounting_entity_id,
    )
    aging = await mitrabooks_connector.get_mis_ar_ap_aging(
        tenant_id=tenant_id,
        tenant=tenant,
        as_of=as_of,
        accounting_entity_id=accounting_entity_id,
    )

    for label, report in (("pnl", pnl), ("balance_sheet", bs), ("cash", cash), ("aging", aging)):
        if report.get("error"):
            warnings.append(f"{label}_connector_failed")
        if report.get("enabled") is False:
            warnings.append(report.get("reason") or f"{label}_disabled")

    as_of_s = as_of.isoformat()
    facts: list[dict[str, Any]] = []
    if pnl.get("enabled") and not pnl.get("error"):
        facts.extend(_map_pnl(pnl, period=period, as_of=as_of_s))
    if bs.get("enabled") and not bs.get("error"):
        facts.extend(_map_bs(bs, period=period, as_of=as_of_s))
    if cash.get("enabled") and not cash.get("error"):
        facts.extend(_map_cash(cash, period=period, as_of=as_of_s))
    if aging.get("enabled") and not aging.get("error"):
        facts.extend(_map_aging_side("AR", aging.get("receivable"), period=period, as_of=as_of_s))
        facts.extend(_map_aging_side("AP", aging.get("payable"), period=period, as_of=as_of_s))

    if not facts:
        warnings.append("empty_books_no_facts")

    score, breakdown = compute_live_data_quality(facts, warnings)
    result = await mis_store.replace_facts_by_source_system(
        tenant_id=tenant_id,
        pack_id=pack_id,
        user=user,
        source_system=_SOURCE,
        facts=facts,
        set_ingestion_path_if_blank_or_manual=True,
        data_quality_score=score,
        data_quality_breakdown=breakdown,
    )
    return {
        "pack": result["pack"],
        "facts_upserted": result["inserted"],
        "facts_replaced": result["deleted"],
        "warnings": warnings,
        "data_quality_score": score,
        "period": period,
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "as_of": as_of_s,
        "adr_014_live_mitrabooks": True,
    }
