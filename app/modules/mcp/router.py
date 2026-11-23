"""HTTP routes for the MitraBooks MCP server and its access tokens.

* ``POST /api/v1/mcp``           MCP endpoint (Streamable HTTP, JSON replies)
* ``GET|DELETE /api/v1/mcp``     405: no SSE stream or sessions are offered
* ``/api/v1/mcp/tokens``         create / list / revoke personal access tokens
                                 (signed-in web session; not reachable via MCP)
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.audit.service import log_audit_event
from app.core.auth.dependencies import get_current_user
from app.core.rate_limiting import limiter
from app.modules.mcp import tokens as token_service
from app.modules.mcp.server import PARSE_ERROR, McpCaller, handle_payload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["mcp"])

MCP_RATE_LIMIT = "120/minute"


class TokenCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    expires_in_days: int = Field(default=token_service.DEFAULT_EXPIRY_DAYS)


def _bearer(request: Request) -> str:
    header = str(request.headers.get("authorization") or "")
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        raise HTTPException(
            status_code=401,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": 'Bearer realm="mitrabooks-mcp"'},
        )
    return value.strip()


def _reject_mcp_session(current_user: dict) -> None:
    # Token management needs a real web sign-in, never a token-derived session.
    if current_user.get("via") == "mcp":
        raise HTTPException(status_code=403, detail="Not available to AI clients")


async def _audit(current_user: dict, request: Request, action: str, token: dict) -> None:
    try:
        await log_audit_event(
            tenant_id=str(current_user.get("tenant_id") or "platform"),
            user_id=str(current_user.get("sub") or "unknown"),
            product="mitrabooks",
            action=action,
            entity_type="mcp_access_token",
            entity_id=str(token.get("token_id")),
            old_value=None,
            new_value={"name": token.get("name"), "prefix": token.get("prefix"), "expires_at": str(token.get("expires_at"))},
            ip_address=request.client.host if request.client else None,
        )
    except Exception:  # audit must not block token management
        logger.warning("Could not record audit event %s", action, exc_info=True)


@router.post("")
@limiter.limit(MCP_RATE_LIMIT)
async def mcp_endpoint(request: Request):
    access_token, _doc = await token_service.exchange_token(_bearer(request))

    try:
        payload = json.loads(await request.body())
    except (ValueError, UnicodeDecodeError):
        return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": PARSE_ERROR, "message": "Parse error"}})

    reply = await handle_payload(payload, McpCaller(request.app, access_token))
    if reply is None:
        return Response(status_code=202)
    return JSONResponse(reply)


@router.get("")
@router.delete("")
async def mcp_no_stream():
    return Response(status_code=405, headers={"Allow": "POST"})


@router.post("/tokens", status_code=201)
async def create_mcp_token(
    body: TokenCreateRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    _reject_mcp_session(current_user)
    plain, token = await token_service.create_token(
        current_user=current_user, name=body.name, expires_in_days=body.expires_in_days
    )
    await _audit(current_user, request, "mcp_token_created", token)
    return {**token, "token": plain}


@router.get("/tokens")
async def list_mcp_tokens(current_user: dict = Depends(get_current_user)):
    _reject_mcp_session(current_user)
    return {"tokens": await token_service.list_tokens(current_user=current_user)}


@router.delete("/tokens/{token_id}")
async def revoke_mcp_token(
    token_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    _reject_mcp_session(current_user)
    token = await token_service.revoke_token(current_user=current_user, token_id=token_id)
    await _audit(current_user, request, "mcp_token_revoked", token)
    return token
