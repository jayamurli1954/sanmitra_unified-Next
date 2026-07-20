"""MandirMitra panchang (today) route.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
Panchang location helpers remain on router.py for settings routes.
"""
from __future__ import annotations

import logging
from datetime import datetime

from fastapi import Depends, Header, HTTPException, Query

from app.core.auth.dependencies import get_current_user
from app.core.tenants.context import resolve_app_key, resolve_tenant_id
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import router
from app.services.panchang import PanchangService

_logger = logging.getLogger(__name__)


@router.get("/panchang/today")
async def panchang_today(
    city_name: str | None = Query(default=None),
    latitude: float | None = Query(default=None),
    longitude: float | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Calculate today's panchang using Swiss Ephemeris with temple location."""
    try:
        tenant_id = resolve_tenant_id(current_user, x_tenant_id)
        app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())

        # Get temple location from MongoDB
        temple_doc = await mandir_router.get_collection("mandir_temples").find_one(
            {"tenant_id": tenant_id, "app_key": app_key}
        )
        if not temple_doc:
            temple_doc = await mandir_router.get_collection("mandir_temples").find_one({"tenant_id": tenant_id})
        if not temple_doc:
            temple_doc = {}

        # Get panchang display settings for overrides
        settings_doc = await mandir_router.get_collection("mandir_panchang_settings").find_one(
            {"tenant_id": tenant_id, "app_key": app_key}
        ) or {}

        latitude, longitude, city = mandir_router._resolve_panchang_location(
            settings_doc,
            temple_doc,
            city_name=city_name,
            latitude=latitude,
            longitude=longitude,
        )

        # Calculate panchang using Swiss Ephemeris
        panchang_service = PanchangService()
        now = datetime.now()
        panchang_data = panchang_service.calculate_panchang(now, latitude, longitude, city)

        return panchang_data
    except Exception as e:
        _logger.error("Error calculating panchang: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate panchang: {str(e)}"
        ) from e
