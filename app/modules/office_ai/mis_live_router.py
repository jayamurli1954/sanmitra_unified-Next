"""ADR-014 Path A live MitraBooks MIS reads (kept separate to avoid growing office_ai/router.py)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.modules.dependencies import require_enabled_module_feature
from app.core.modules.registry import is_office_ai_mis_live_mitrabooks_enabled
from app.db.postgres import get_optional_async_session
from app.modules.office_ai.services import mis_live_ingest, mis_store

router = APIRouter(prefix="/officemitra", tags=["officemitra"])


class MISLiveImportRequest(BaseModel):
    accounting_entity_id: str = Field(default="primary", max_length=80)


def _tenant_id(ctx: dict) -> str:
    return str((ctx.get("tenant") or {}).get("tenant_id") or (ctx.get("user") or {}).get("tenant_id") or "").strip()


def _require_live_mitrabooks(tenant: dict) -> None:
    if not is_office_ai_mis_live_mitrabooks_enabled(
        enabled_modules=tenant.get("enabled_modules") or [],
        office_ai_features=tenant.get("office_ai_features"),
    ):
        raise HTTPException(status_code=403, detail="Enable office_ai.mis.live_mitrabooks")


@router.get("/mis/live-mitrabooks/status")
async def live_mitrabooks_status(
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "mis")),
    session: AsyncSession | None = Depends(get_optional_async_session),
) -> dict:
    tenant = ctx.get("tenant") or {}
    _require_live_mitrabooks(tenant)
    probe = await mis_live_ingest.probe_live_status(
        tenant_id=_tenant_id(ctx),
        tenant=tenant,
        session=session,
    )
    return {
        "live_mitrabooks": True,
        **probe,
    }


@router.post("/mis/packs/{pack_id}/import/mitrabooks")
async def import_mis_pack_from_mitrabooks(
    pack_id: str,
    payload: MISLiveImportRequest | None = None,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "mis")),
    session: AsyncSession | None = Depends(get_optional_async_session),
) -> dict:
    tenant = ctx.get("tenant") or {}
    _require_live_mitrabooks(tenant)
    body = payload or MISLiveImportRequest()
    try:
        return await mis_live_ingest.import_from_mitrabooks(
            tenant_id=_tenant_id(ctx),
            tenant=tenant,
            user=ctx["user"],
            pack_id=pack_id,
            session=session,
            accounting_entity_id=body.accounting_entity_id,
        )
    except mis_store.MISPackNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except mis_store.MISImmutableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except mis_live_ingest.MISLiveIngestError as exc:
        detail = str(exc)
        if detail in {"business_module_off", "session_required"}:
            raise HTTPException(status_code=400, detail=detail) from exc
        if detail == "unsupported_period":
            raise HTTPException(status_code=400, detail="unsupported_period") from exc
        raise HTTPException(status_code=400, detail=detail) from exc
    except mis_store.MISStoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
