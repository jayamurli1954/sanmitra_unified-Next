"""ADR-014 MIS narrative routes (kept separate to avoid growing office_ai/router.py)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.modules.dependencies import require_enabled_module_feature
from app.modules.office_ai.services import mis_service, mis_store

router = APIRouter(prefix="/officemitra", tags=["officemitra"])


def _tenant_id(ctx: dict) -> str:
    return str((ctx.get("tenant") or {}).get("tenant_id") or (ctx.get("user") or {}).get("tenant_id") or "").strip()


@router.post("/mis/packs/{pack_id}/narrative")
async def generate_mis_pack_narrative(
    pack_id: str,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "mis")),
) -> dict:
    """Generate attributed narrative with fact citations (ADR-014 step 5)."""
    try:
        return await mis_service.generate_pack_narrative(
            tenant_id=_tenant_id(ctx),
            pack_id=pack_id,
            user=ctx["user"],
        )
    except mis_store.MISPackNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except mis_store.MISImmutableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except mis_store.MISStoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
