"""Minimal MCP (Model Context Protocol) server over Streamable HTTP.

Stateless and JSON-only: every POST carries one JSON-RPC message (or a batch) and
gets a JSON reply; no sessions and no SSE stream. That is a valid subset of the
Streamable HTTP transport and is what remote MCP clients need for tool calling.
Hand-rolled instead of using the ``mcp`` SDK so it fits the pinned FastAPI /
Starlette versions without new dependencies.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.modules.mcp.tools import TOOLS, TOOLS_BY_NAME, ToolArgumentError, build_request

logger = logging.getLogger(__name__)

SUPPORTED_PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
LATEST_PROTOCOL_VERSION = SUPPORTED_PROTOCOL_VERSIONS[0]
SERVER_INFO = {"name": "mitrabooks", "title": "MitraBooks", "version": "1.0.0"}
MAX_RESULT_CHARS = 200_000

INSTRUCTIONS = (
    "MitraBooks is an Indian double-entry accounting and GST system. All tools are read-only "
    "and act on the books of the signed-in user's company. Amounts are in INR. Dates are "
    "YYYY-MM-DD. The Indian financial year runs April-March; quarters are written YYYY-Qn "
    "with YYYY the FY start year (Q1 = Apr-Jun). Use list_accounts to find account ids and "
    "list_parties to find party ids. For a month-end or book review, start with "
    "get_trial_balance and get_data_health."
)

# JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602


def _error(msg_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def _result(msg_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _tool_text(text: str, *, is_error: bool = False) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


class McpCaller:
    """Runs tool calls against this app in-process, as the token's user."""

    def __init__(self, asgi_app, access_token: str):
        self._app = asgi_app
        self._access_token = access_token

    async def get(self, path: str, query: dict[str, str], entity_id: str | None) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "X-App-Key": "mitrabooks",
            "Accept": "application/json",
        }
        if entity_id:
            headers["X-Accounting-Entity-ID"] = entity_id
        transport = httpx.ASGITransport(app=self._app)
        async with httpx.AsyncClient(transport=transport, base_url="http://mcp.internal") as client:
            return await client.get(path, params=query, headers=headers)


def _format_http_error(response: httpx.Response) -> str:
    try:
        detail = response.json().get("detail")
    except (ValueError, AttributeError):
        detail = None
    if isinstance(detail, list):
        # FastAPI validation errors: keep field + message only.
        detail = "; ".join(
            f"{'.'.join(str(p) for p in (item.get('loc') or [])[1:])}: {item.get('msg')}"
            for item in detail
            if isinstance(item, dict)
        )
    if response.status_code == 403:
        prefix = "Not permitted for this user"
    elif response.status_code == 404:
        prefix = "Not found"
    elif response.status_code == 422:
        prefix = "Invalid arguments"
    else:
        prefix = f"MitraBooks returned HTTP {response.status_code}"
    return f"{prefix}: {detail}" if detail else prefix


async def _call_tool(params: dict, caller: McpCaller) -> dict:
    name = params.get("name")
    tool = TOOLS_BY_NAME.get(name) if isinstance(name, str) else None
    if tool is None:
        raise LookupError(f"Unknown tool: {name}")
    arguments = params.get("arguments") or {}
    if not isinstance(arguments, dict):
        return _tool_text("arguments must be an object", is_error=True)

    entity_id = arguments.get("accounting_entity_id")
    try:
        path, query = build_request(tool, arguments)
    except ToolArgumentError as exc:
        return _tool_text(str(exc), is_error=True)

    try:
        response = await caller.get(path, query, str(entity_id) if entity_id else None)
    except Exception:  # pragma: no cover - defensive: never leak internals to the client
        logger.exception("MCP tool %s failed", tool.name)
        return _tool_text("MitraBooks could not complete this request. Please retry.", is_error=True)

    if response.status_code >= 400:
        return _tool_text(_format_http_error(response), is_error=True)

    try:
        text = json.dumps(response.json(), ensure_ascii=False, default=str)
    except ValueError:
        text = response.text
    if len(text) > MAX_RESULT_CHARS:
        text = (
            text[:MAX_RESULT_CHARS]
            + f"\n\n[Truncated: result was {len(text)} characters. Narrow the date range, filter by party, or paginate.]"
        )
    return _tool_text(text)


async def handle_message(message: Any, caller: McpCaller) -> dict | None:
    """Handle one JSON-RPC message. Returns None for notifications and responses."""
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return _error(None, INVALID_REQUEST, "Invalid JSON-RPC message")

    method = message.get("method")
    msg_id = message.get("id")
    if method is None:
        # A response to a server request; this server sends none.
        return None
    if "id" not in message:
        # Notification (e.g. notifications/initialized): nothing to send back.
        return None
    params = message.get("params") or {}
    if not isinstance(params, dict):
        return _error(msg_id, INVALID_PARAMS, "params must be an object")

    if method == "initialize":
        requested = params.get("protocolVersion")
        version = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else LATEST_PROTOCOL_VERSION
        return _result(
            msg_id,
            {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
                "instructions": INSTRUCTIONS,
            },
        )
    if method == "ping":
        return _result(msg_id, {})
    if method == "tools/list":
        return _result(msg_id, {"tools": [tool.descriptor() for tool in TOOLS]})
    if method == "tools/call":
        try:
            return _result(msg_id, await _call_tool(params, caller))
        except LookupError as exc:
            return _error(msg_id, INVALID_PARAMS, str(exc))
    if method in ("resources/list", "prompts/list"):
        key = "resources" if method == "resources/list" else "prompts"
        return _result(msg_id, {key: []})
    return _error(msg_id, METHOD_NOT_FOUND, f"Method not found: {method}")


async def handle_payload(payload: Any, caller: McpCaller) -> Any:
    """Handle a single message or a batch. Returns the reply body, or None (HTTP 202)."""
    if isinstance(payload, list):
        if not payload:
            return _error(None, INVALID_REQUEST, "Empty batch")
        replies = [reply for item in payload if (reply := await handle_message(item, caller)) is not None]
        return replies or None
    return await handle_message(payload, caller)
