"""Deterministic Review findings from MIS facts (ADR-015).

Does not post journals. Does not call SSDV CLI. Optional in-process SSDV import
is a no-op when the package is not installed.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from app.modules.office_ai.models import REVIEW_RULE_VERSION

SEVERITY_WEIGHTS = {"high": 25, "medium": 10, "low": 4}


def _amount(fact: dict[str, Any]) -> Decimal:
    raw = fact.get("amount_decimal")
    if raw is None:
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _dims(fact: dict[str, Any]) -> dict[str, Any]:
    return dict(fact.get("dimensions") or {})


def _label(fact: dict[str, Any]) -> str:
    dims = _dims(fact)
    parts = [
        str(dims.get("account") or ""),
        str(dims.get("group") or ""),
        str(dims.get("line") or ""),
        str(dims.get("label") or ""),
        str(fact.get("source_ref") or ""),
    ]
    return " ".join(parts).lower()


def _issue(
    *,
    code: str,
    severity: str,
    description: str,
    fact_ids: list[str],
) -> dict[str, Any]:
    return {
        "finding_code": code,
        "rule_version": REVIEW_RULE_VERSION,
        "severity": severity,
        "description": description,
        "fact_ids": [fid for fid in fact_ids if fid],
        "ai_generated": False,
    }


def scan_facts(facts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Return (issues, engagement_risk_score 0–100). Distinct from MIS data_quality_score."""
    issues: list[dict[str, Any]] = []
    rows = list(facts or [])

    cash_rows = [f for f in rows if f.get("entity_type") == "cash_summary"]
    bs_rows = [f for f in rows if f.get("entity_type") == "bs_line"]
    aging_rows = [f for f in rows if f.get("entity_type") == "aging_bucket"]
    party_rows = [f for f in rows if f.get("entity_type") == "party"]
    pnl_rows = [f for f in rows if f.get("entity_type") == "pnl_line"]

    if not cash_rows:
        issues.append(
            _issue(
                code="MISSING_CASH",
                severity="medium",
                description="No cash_summary facts on the linked pack.",
                fact_ids=[],
            )
        )
    for fact in cash_rows:
        line = str(_dims(fact).get("line") or "").strip().lower()
        if line in {"closing", "cash", "bank"} and _amount(fact) < 0:
            issues.append(
                _issue(
                    code="NEGATIVE_CASH",
                    severity="high",
                    description=f"Cash/bank line '{line}' is negative ({fact.get('amount_decimal')}).",
                    fact_ids=[str(fact.get("fact_id") or "")],
                )
            )

    for fact in bs_rows:
        if _amount(fact) < 0 and "liab" not in _label(fact) and "equity" not in _label(fact):
            issues.append(
                _issue(
                    code="NEGATIVE_BS_LINE",
                    severity="medium",
                    description=f"Balance-sheet line is negative: {_label(fact)[:120] or fact.get('source_ref')}.",
                    fact_ids=[str(fact.get("fact_id") or "")],
                )
            )
        if "suspense" in _label(fact) and _amount(fact) != 0:
            issues.append(
                _issue(
                    code="SUSPENSE_BALANCE",
                    severity="high",
                    description="Suspense balance is non-zero.",
                    fact_ids=[str(fact.get("fact_id") or "")],
                )
            )

    ar_aging = [f for f in aging_rows if str(_dims(f).get("side") or "").upper() == "AR"]
    ap_aging = [f for f in aging_rows if str(_dims(f).get("side") or "").upper() == "AP"]
    if not ar_aging:
        issues.append(
            _issue(
                code="MISSING_AR_AGING",
                severity="low",
                description="No AR aging_bucket facts on the linked pack.",
                fact_ids=[],
            )
        )
    if not ap_aging:
        issues.append(
            _issue(
                code="MISSING_AP_AGING",
                severity="low",
                description="No AP aging_bucket facts on the linked pack.",
                fact_ids=[],
            )
        )
    for fact in ar_aging:
        bucket = str(_dims(fact).get("bucket") or "")
        if _is_overdue_90_bucket(bucket) and _amount(fact) > 0:
            issues.append(
                _issue(
                    code="AR_AGING_90",
                    severity="high",
                    description=f"AR aging bucket {bucket} has a balance of {fact.get('amount_decimal')}.",
                    fact_ids=[str(fact.get("fact_id") or "")],
                )
            )
    for fact in ap_aging:
        bucket = str(_dims(fact).get("bucket") or "")
        if _is_overdue_90_bucket(bucket) and _amount(fact) > 0:
            issues.append(
                _issue(
                    code="AP_AGING_90",
                    severity="medium",
                    description=f"AP aging bucket {bucket} has a balance of {fact.get('amount_decimal')}.",
                    fact_ids=[str(fact.get("fact_id") or "")],
                )
            )

    ar_parties = [f for f in party_rows if str(_dims(f).get("type") or "").lower() in {"customer", "ar"}]
    ap_parties = [f for f in party_rows if str(_dims(f).get("type") or "").lower() in {"vendor", "supplier", "ap"}]
    _flag_concentration(issues, ar_parties, code="AR_CONCENTRATION", label="customer")
    _flag_concentration(issues, ap_parties, code="AP_CONCENTRATION", label="vendor")

    for fact in pnl_rows:
        dims = _dims(fact)
        if str(dims.get("line") or dims.get("group") or "").lower() not in {"gross margin", "margin", "gp"}:
            continue
        prior = dims.get("prior_period") or dims.get("prior")
        if prior is None:
            continue
        try:
            prior_amt = Decimal(str(prior))
        except (InvalidOperation, ValueError):
            continue
        current = _amount(fact)
        if prior_amt > 0 and current < prior_amt * Decimal("0.90"):
            issues.append(
                _issue(
                    code="MARGIN_DROP",
                    severity="medium",
                    description="Gross margin declined more than 10% versus prior period.",
                    fact_ids=[str(fact.get("fact_id") or "")],
                )
            )

    issues.extend(_optional_ssdv_signals(rows))
    score = engagement_risk_score(issues)
    return issues, score


def engagement_risk_score(issues: list[dict[str, Any]]) -> int:
    total = 0
    for issue in issues:
        total += SEVERITY_WEIGHTS.get(str(issue.get("severity") or "medium"), 10)
    return max(0, min(100, total))


def _is_overdue_90_bucket(bucket: str) -> bool:
    """True for 90+ overdue buckets only — not current / 61-90 ranges."""
    token = str(bucket or "").replace(" ", "").lower()
    if not token:
        return False
    if token in {">90", "90plus", "over90", "90d+", "120+", "180+", "365+"}:
        return True
    return token.endswith("90+") or token.endswith("+") and token.rstrip("+").isdigit() and int(token.rstrip("+")) >= 90


def _flag_concentration(
    issues: list[dict[str, Any]],
    parties: list[dict[str, Any]],
    *,
    code: str,
    label: str,
) -> None:
    if len(parties) < 2:
        return
    amounts = [(f, _amount(f)) for f in parties]
    total = sum(amt for _f, amt in amounts)
    if total <= 0:
        return
    top_fact, top_amt = max(amounts, key=lambda pair: pair[1])
    if top_amt / total >= Decimal("0.25"):
        pct = (top_amt / total * Decimal("100")).quantize(Decimal("0.1"))
        issues.append(
            _issue(
                code=code,
                severity="medium",
                description=f"Top {label} is {pct}% of the party total.",
                fact_ids=[str(top_fact.get("fact_id") or "")],
            )
        )


def _optional_ssdv_signals(_facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """In-process SSDV hook. Never invoke the SSDV CLI. Missing package is a no-op."""
    try:
        import ssdv  # noqa: F401
    except Exception:
        return []
    return []
