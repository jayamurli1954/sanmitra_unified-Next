"""Optional in-process SSDV board red-flag signals for OfficeMitra Review (ADR-015).

Never invokes the SSDV CLI or Streamlit. Never posts to MitraBooks ledgers.

When the ``ssdv`` package is importable, uses ``ssdv.officemitra.insights.build_red_flags``.
Otherwise applies the same board rules locally (DSO policy, negative cash/equity, falling
or negative last-month profit) so Review stays useful in CI without D:\\SSDV installed.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from app.modules.office_ai.models import REVIEW_RULE_VERSION

# Mirror ssdv.mis.policy.DSO_DAYS_MAX when the package is absent.
_LOCAL_DSO_DAYS_MAX = 120

_INSIGHT_TO_CODE = {
    "flag_dso": "SSDV_FLAG_DSO",
    "flag_cash": "SSDV_FLAG_CASH",
    "flag_equity": "SSDV_FLAG_EQUITY",
    "flag_profit": "SSDV_FLAG_PROFIT",
}

_TONE_TO_SEVERITY = {
    "danger": "high",
    "warning": "medium",
    "success": "low",
    "neutral": "low",
}


@dataclass(frozen=True)
class _BoardMetrics:
    cash: Decimal | None
    equity: Decimal | None
    dso: int | None
    monthly_profit: Decimal | None
    series_sales: tuple[Decimal, ...]
    series_cogs: tuple[Decimal, ...]
    series_opex: tuple[Decimal, ...]
    fact_ids: tuple[str, ...]


def _dec(raw: Any) -> Decimal | None:
    if raw is None or raw == "":
        return None
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return None


def _dims(fact: dict[str, Any]) -> dict[str, Any]:
    return dict(fact.get("dimensions") or {})


def _fact_id(fact: dict[str, Any]) -> str:
    return str(fact.get("fact_id") or "").strip()


def _line_name(fact: dict[str, Any]) -> str:
    dims = _dims(fact)
    return str(dims.get("line") or dims.get("kpi") or dims.get("label") or "").strip().lower()


def extract_board_metrics(facts: list[dict[str, Any]]) -> _BoardMetrics:
    """Pull cash / equity / DSO / profit series from MIS facts for board red flags."""
    rows = list(facts or [])
    ids: list[str] = []

    cash: Decimal | None = None
    equity: Decimal | None = None
    dso: int | None = None
    monthly_profit: Decimal | None = None

    cash_parts: list[Decimal] = []
    for fact in rows:
        et = str(fact.get("entity_type") or "").strip().lower()
        dims = _dims(fact)
        fid = _fact_id(fact)
        if et == "kpi" and str(dims.get("kpi") or "").strip().lower() in {"cashandbank", "cash_and_bank"}:
            val = _dec(fact.get("value") if fact.get("value") is not None else fact.get("amount_decimal"))
            if val is not None:
                cash = val
                if fid:
                    ids.append(fid)
        if et == "kpi" and str(dims.get("kpi") or "").strip().lower() == "dso":
            val = _dec(fact.get("value") if fact.get("value") is not None else fact.get("amount_decimal"))
            if val is not None:
                dso = int(val.to_integral_value())
                if fid:
                    ids.append(fid)
        if et == "bs_line":
            line = _line_name(fact)
            amt = _dec(fact.get("amount_decimal"))
            if amt is None:
                continue
            if line in {"cash", "bank"}:
                cash_parts.append(amt)
                if fid:
                    ids.append(fid)
            if line in {"equity", "total equity"} or str(dims.get("section") or "").lower() == "equity":
                if "total" in line or line == "equity":
                    equity = amt
                    if fid:
                        ids.append(fid)
        if et == "cash_summary":
            line = _line_name(fact)
            amt = _dec(fact.get("amount_decimal"))
            if amt is not None and line in {"closing", "cash", "bank"}:
                cash_parts.append(amt)
                if fid:
                    ids.append(fid)
        if et == "pnl_line" and _line_name(fact) in {"pat", "profit after tax", "net profit"}:
            amt = _dec(fact.get("amount_decimal"))
            if amt is not None and not dims.get("trend"):
                monthly_profit = amt
                if fid:
                    ids.append(fid)

    if cash is None and cash_parts:
        cash = sum(cash_parts, Decimal("0"))

    # Trend months: Revenue / COGS / OPEX with period or trend dimension.
    by_period: dict[str, dict[str, Decimal]] = {}
    for fact in rows:
        if str(fact.get("entity_type") or "").strip().lower() != "pnl_line":
            continue
        dims = _dims(fact)
        period = str(fact.get("period") or dims.get("period") or "").strip()
        if not period and not dims.get("trend"):
            continue
        if not period:
            # source_id pnl-trend-rev-2026-06
            sid = str(fact.get("source_id") or "")
            parts = sid.split("-")
            if len(parts) >= 5 and parts[0] == "pnl" and parts[1] == "trend":
                period = f"{parts[-2]}-{parts[-1]}" if len(parts[-1]) == 2 else "-".join(parts[-3:])
        if not period:
            continue
        line = _line_name(fact)
        amt = _dec(fact.get("amount_decimal"))
        if amt is None:
            continue
        bucket = by_period.setdefault(period, {})
        if line in {"revenue", "sales"}:
            bucket["sales"] = amt
        elif line == "cogs":
            bucket["cogs"] = amt
        elif line in {"operating expenses", "opex"}:
            bucket["opex"] = amt
        fid = _fact_id(fact)
        if fid:
            ids.append(fid)

    periods = sorted(by_period.keys())
    series_sales = tuple(by_period[p].get("sales", Decimal("0")) for p in periods)
    series_cogs = tuple(by_period[p].get("cogs", Decimal("0")) for p in periods)
    series_opex = tuple(by_period[p].get("opex", Decimal("0")) for p in periods)

    if monthly_profit is None and series_sales:
        monthly_profit = series_sales[-1] - series_cogs[-1] - series_opex[-1]

    return _BoardMetrics(
        cash=cash,
        equity=equity,
        dso=dso,
        monthly_profit=monthly_profit,
        series_sales=series_sales,
        series_cogs=series_cogs,
        series_opex=series_opex,
        fact_ids=tuple(dict.fromkeys(ids)),
    )


def _issue(code: str, severity: str, description: str, fact_ids: list[str]) -> dict[str, Any]:
    return {
        "finding_code": code,
        "rule_version": REVIEW_RULE_VERSION,
        "severity": severity,
        "description": description,
        "fact_ids": [fid for fid in fact_ids if fid],
        "ai_generated": False,
        "source_engine": "ssdv_board",
    }


def _local_board_issues(metrics: _BoardMetrics) -> list[dict[str, Any]]:
    """Same board exceptions as ssdv.officemitra.insights.build_red_flags."""
    flags: list[dict[str, Any]] = []
    fids = list(metrics.fact_ids)
    if metrics.dso is not None and metrics.dso > _LOCAL_DSO_DAYS_MAX:
        flags.append(
            _issue(
                "SSDV_FLAG_DSO",
                "high",
                f"DSO {metrics.dso} days exceeds {_LOCAL_DSO_DAYS_MAX}-day policy.",
                fids,
            )
        )
    if metrics.cash is not None and metrics.cash < 0:
        flags.append(
            _issue(
                "SSDV_FLAG_CASH",
                "high",
                f"Cash position is negative ({metrics.cash}).",
                fids,
            )
        )
    if metrics.equity is not None and metrics.equity < 0:
        flags.append(
            _issue(
                "SSDV_FLAG_EQUITY",
                "high",
                f"Equity after close is negative ({metrics.equity}).",
                fids,
            )
        )
    if len(metrics.series_sales) >= 2:
        prev = metrics.series_sales[-2] - metrics.series_cogs[-2] - metrics.series_opex[-2]
        last = metrics.monthly_profit if metrics.monthly_profit is not None else (
            metrics.series_sales[-1] - metrics.series_cogs[-1] - metrics.series_opex[-1]
        )
        if last < prev:
            flags.append(
                _issue(
                    "SSDV_FLAG_PROFIT",
                    "high" if last < 0 else "medium",
                    f"Last-month profit {last} is below prior month {prev}.",
                    fids,
                )
            )
    elif metrics.monthly_profit is not None and metrics.monthly_profit < 0:
        flags.append(
            _issue(
                "SSDV_FLAG_PROFIT",
                "high",
                f"Last-month profit is negative ({metrics.monthly_profit}).",
                fids,
            )
        )
    return flags


def _via_ssdv_package(metrics: _BoardMetrics) -> list[dict[str, Any]]:
    from ssdv.mis.policy import DSO_DAYS_MAX  # type: ignore
    from ssdv.money import ZERO, money  # type: ignore
    from ssdv.officemitra.insights import build_red_flags  # type: ignore

    class _Series:
        def __init__(self) -> None:
            self.sales = tuple(money(v) for v in metrics.series_sales)
            self.cogs = tuple(money(v) for v in metrics.series_cogs)
            self.opex = tuple(money(v) for v in metrics.series_opex)
            self.labels = tuple(f"M{i+1}" for i in range(len(self.sales)))

    class _Snap:
        def __init__(self) -> None:
            self.dso = metrics.dso
            self.cash = money(metrics.cash) if metrics.cash is not None else ZERO
            self.equity = money(metrics.equity) if metrics.equity is not None else ZERO
            self.series = _Series()
            self._monthly_override = (
                money(metrics.monthly_profit) if metrics.monthly_profit is not None else None
            )

        @property
        def monthly_profit(self):
            if self.series.sales:
                return money(self.series.sales[-1] - self.series.cogs[-1] - self.series.opex[-1])
            if self._monthly_override is not None:
                return self._monthly_override
            return ZERO

    _ = DSO_DAYS_MAX
    flags = build_red_flags(_Snap())
    out: list[dict[str, Any]] = []
    fids = list(metrics.fact_ids)
    for item in flags:
        code = _INSIGHT_TO_CODE.get(str(item.id), f"SSDV_{str(item.id).upper()}")
        severity = _TONE_TO_SEVERITY.get(str(item.tone), "medium")
        out.append(_issue(code, severity, str(item.text), fids))
    return out


def optional_ssdv_signals(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return Review issues from SSDV board red flags (in-process) or local mirror."""
    metrics = extract_board_metrics(facts)
    if (
        metrics.cash is None
        and metrics.equity is None
        and metrics.dso is None
        and metrics.monthly_profit is None
        and not metrics.series_sales
    ):
        return []
    try:
        return _via_ssdv_package(metrics)
    except Exception:
        return _local_board_issues(metrics)
