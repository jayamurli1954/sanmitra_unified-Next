"""MandirMitra pincode lookup helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.modules.mandir_compat.helpers.coercions import _safe_optional_int

def _normalize_pincode(value: Any) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits[:6]


MANDIR_PINCODE_FALLBACKS: dict[str, tuple[str, str]] = {
    "560001": ("Bengaluru", "Karnataka"),
    "560002": ("Bengaluru", "Karnataka"),
    "560003": ("Bengaluru", "Karnataka"),
    "560004": ("Bengaluru", "Karnataka"),
    "560011": ("Bengaluru", "Karnataka"),
    "560019": ("Bengaluru", "Karnataka"),
    "560070": ("Bengaluru", "Karnataka"),
    "560078": ("Bengaluru", "Karnataka"),
    "575001": ("Mangaluru", "Karnataka"),
    "575002": ("Mangaluru", "Karnataka"),
    "575003": ("Mangaluru", "Karnataka"),
    "575004": ("Mangaluru", "Karnataka"),
    "575005": ("Mangaluru", "Karnataka"),
    "600004": ("Chennai", "Tamil Nadu"),
    "600017": ("Chennai", "Tamil Nadu"),
    "600020": ("Chennai", "Tamil Nadu"),
    "600028": ("Chennai", "Tamil Nadu"),
    "500034": ("Hyderabad", "Telangana"),
    "530017": ("Visakhapatnam", "Andhra Pradesh"),
    "641002": ("Coimbatore", "Tamil Nadu"),
}


async def _lookup_pincode_city_state(pincode: str) -> tuple[str | None, str | None]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"https://api.postalpincode.in/pincode/{pincode}")
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return MANDIR_PINCODE_FALLBACKS.get(pincode, (None, None))

    if not isinstance(payload, list) or not payload:
        return MANDIR_PINCODE_FALLBACKS.get(pincode, (None, None))

    first = payload[0] if isinstance(payload[0], dict) else {}
    if str(first.get("Status") or "").strip().lower() != "success":
        return MANDIR_PINCODE_FALLBACKS.get(pincode, (None, None))

    offices = first.get("PostOffice")
    if not isinstance(offices, list) or not offices:
        return MANDIR_PINCODE_FALLBACKS.get(pincode, (None, None))

    primary = offices[0] if isinstance(offices[0], dict) else {}
    city = str(primary.get("District") or primary.get("Taluk") or primary.get("Name") or "").strip() or None
    state = str(primary.get("State") or "").strip() or None
    return (city, state) if city and state else MANDIR_PINCODE_FALLBACKS.get(pincode, (city, state))


def _to_positive_int(value: Any) -> int | None:
    parsed = _safe_optional_int(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed

