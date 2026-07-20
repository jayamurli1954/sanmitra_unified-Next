"""MandirMitra pincode lookup route.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from fastapi import Depends, Query

from app.core.auth.dependencies import get_current_user
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import router

@router.get("/pincode/lookup")
async def mandir_pincode_lookup(pincode: str = Query(...), _current_user: dict = Depends(get_current_user)):
    normalized = mandir_router._normalize_pincode(pincode)
    if len(normalized) != 6:
        return {"pincode": normalized, "city": None, "state": None, "country": "India", "found": False}

    city, state = await mandir_router._lookup_pincode_city_state(normalized)
    found = bool(city and state)

    return {
        "pincode": normalized,
        "city": city if found else None,
        "state": state if found else None,
        "country": "India",
        "found": found,
    }

