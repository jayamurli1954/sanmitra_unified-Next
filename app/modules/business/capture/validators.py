"""Deterministic validation — the hard gate. These checks never depend on the
model; a failure forces human review regardless of extraction confidence."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

_GSTIN_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_ROUNDING_TOLERANCE = Decimal("1.00")  # rupee rounding slack on the arithmetic check


def _dec(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def gstin_check_digit_ok(gstin: str | None) -> bool:
    """Validate the GSTIN mod-36 check digit (and basic shape)."""
    if not gstin:
        return False
    g = str(gstin).strip().upper()
    if len(g) != 15 or any(ch not in _GSTIN_CHARS for ch in g):
        return False
    cp = len(_GSTIN_CHARS)
    factor = 1
    total = 0
    for ch in g[:14]:
        prod = _GSTIN_CHARS.index(ch) * factor
        total += prod // cp + prod % cp
        factor = 2 if factor == 1 else 1
    check = (cp - (total % cp)) % cp
    return _GSTIN_CHARS[check] == g[14]


def validate(fields: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a list of {check, passed, detail}. Order is stable for the UI."""
    checks: list[dict[str, Any]] = []

    # 1. Required fields present.
    missing = [k for k in ("vendor_name", "total_amount", "invoice_date") if not fields.get(k)]
    checks.append({
        "check": "required_fields",
        "passed": not missing,
        "detail": "all present" if not missing else f"missing: {', '.join(missing)}",
    })

    # 2. Arithmetic: taxable + tax ≈ total (within rupee rounding).
    taxable = _dec(fields.get("taxable_value"))
    total = _dec(fields.get("total_amount"))
    tax = _dec(fields.get("tax_amount"))
    if tax is None:
        tax = sum(
            (d for d in (_dec(fields.get("cgst_amount")), _dec(fields.get("sgst_amount")), _dec(fields.get("igst_amount"))) if d is not None),
            Decimal("0"),
        )
    if taxable is not None and total is not None:
        diff = abs((taxable + tax) - total)
        checks.append({
            "check": "arithmetic",
            "passed": diff <= _ROUNDING_TOLERANCE,
            "detail": f"taxable+tax vs total differ by {diff}",
        })
    else:
        checks.append({"check": "arithmetic", "passed": False, "detail": "taxable or total missing"})

    # 3. GSTIN checksum (only when a GSTIN was read — absence is not a failure here).
    gstin = fields.get("vendor_gstin")
    if gstin:
        checks.append({
            "check": "gstin_checksum",
            "passed": gstin_check_digit_ok(gstin),
            "detail": "valid" if gstin_check_digit_ok(gstin) else "invalid check digit",
        })

    return checks


def all_passed(checks: list[dict[str, Any]]) -> bool:
    return all(bool(c.get("passed")) for c in checks)
