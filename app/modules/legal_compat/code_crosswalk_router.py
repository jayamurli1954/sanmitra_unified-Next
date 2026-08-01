"""LegalMitra IPC/CrPC <-> BNS/BNSS curated crosswalk API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field

from app.core.permissions.rbac import Role, require_roles
from app.modules.legal_compat import code_crosswalk as cx

router = APIRouter(tags=["legal-compat"])

_DEFAULT_APP_KEY = "legalmitra"
_any_authenticated = require_roles(
    [Role.viewer, Role.operator, Role.accountant, Role.tenant_admin, Role.super_admin]
)


def _resolve_compat_app_key(x_app_key: str | None) -> str:
    value = (x_app_key or "").strip().lower()
    return value or _DEFAULT_APP_KEY


class CrosswalkValidateRequest(BaseModel):
    from_code: str = Field(min_length=2, max_length=40)
    from_section: str = Field(min_length=1, max_length=20)
    to_code: str = Field(min_length=2, max_length=40)
    to_section: str = Field(min_length=1, max_length=20)


@router.get("/legalmitra/code-crosswalk")
async def legalmitra_code_crosswalk_lookup(
    from_code: str = Query(..., min_length=2, max_length=40, description="e.g. IPC, CrPC, BNS, BNSS"),
    section: str = Query(..., min_length=1, max_length=20, description="e.g. 420, 482, 3(5)"),
    direction: str = Query(default="forward", pattern="^(forward|reverse)$"),
    current_user: dict = Depends(_any_authenticated),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Lookup curated successor / predecessor criminal-code section mappings.

    This is a deterministic registry lookup — not model generation.
    Missing mappings must not be invented by clients.
    """
    _ = current_user
    _ = _resolve_compat_app_key(x_app_key)
    result = cx.lookup(from_code=from_code, section=section, direction=direction)
    return {"ok": True, **result}


@router.get("/legalmitra/code-crosswalk/list")
async def legalmitra_code_crosswalk_list(
    from_code: str | None = Query(default=None, max_length=40),
    to_code: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: dict = Depends(_any_authenticated),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    _ = current_user
    _ = _resolve_compat_app_key(x_app_key)
    data = cx.load_crosswalk()
    mappings = cx.list_mappings(from_code=from_code, to_code=to_code, limit=limit)
    return {
        "ok": True,
        "registry_version": data.get("version"),
        "notes": data.get("notes") or [],
        "count": len(mappings),
        "mappings": mappings,
        "known_false_mappings": data.get("known_false_mappings") or [],
        "human_review_required": True,
        "advisory": "Curated seed only. Confirm against Bare Acts / India Code before filing.",
    }


@router.post("/legalmitra/code-crosswalk/validate")
async def legalmitra_code_crosswalk_validate(
    payload: CrosswalkValidateRequest,
    current_user: dict = Depends(_any_authenticated),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Check whether a claimed mapping is a documented false pair or a curated match."""
    _ = current_user
    _ = _resolve_compat_app_key(x_app_key)

    false = cx.detect_false_mapping(
        from_code=payload.from_code,
        from_section=payload.from_section,
        to_code=payload.to_code,
        to_section=payload.to_section,
    )
    if false:
        return {
            "ok": True,
            "status": "known_false",
            "claimed": payload.model_dump(),
            "false_mapping": false,
            "human_review_required": True,
        }

    forward = cx.lookup(
        from_code=payload.from_code, section=payload.from_section, direction="forward"
    )
    matched = None
    for row in forward.get("matches") or []:
        if cx.normalize_code(str(row.get("to_code"))) == cx.normalize_code(
            payload.to_code
        ) and cx.sections_compatible(str(row.get("to_section")), payload.to_section):
            matched = row
            break

    if matched:
        return {
            "ok": True,
            "status": "verified_in_registry",
            "mapping": matched,
            "human_review_required": True,
        }

    if not forward.get("found"):
        return {
            "ok": True,
            "status": "unverifiable",
            "note": "Pair not in curated seed and not a documented false mapping. Verify against Bare Acts.",
            "human_review_required": True,
        }

    return {
        "ok": True,
        "status": "mismatch",
        "note": "From-section exists in registry but claimed to-section does not match curated successor.",
        "registry_matches": forward.get("matches"),
        "human_review_required": True,
    }
