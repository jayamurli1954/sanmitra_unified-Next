"""Shared SlowAPI rate limiter instance for public endpoints.

Storage: in-memory by default (per process). Set ``RATE_LIMIT_STORAGE_URI`` (for
example ``redis://host:6379/0``) so every worker and instance shares one set of
counters; otherwise limits multiply with the number of processes.

Client key: behind Render's proxy every request arrives from the proxy, so the
socket address would put all users in one bucket. When ``X-Forwarded-For`` is
present the key is the entry appended by our own proxy chain
(``RATE_LIMIT_TRUSTED_PROXY_HOPS`` from the right), which a client cannot forge by
sending its own header.
"""
from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

_DEFAULT_STORAGE_URI = "memory://"


def _trusted_hops() -> int:
    try:
        return max(1, int(os.getenv("RATE_LIMIT_TRUSTED_PROXY_HOPS", "1")))
    except ValueError:
        return 1


def client_rate_limit_key(request: Request) -> str:
    forwarded = str(request.headers.get("x-forwarded-for") or "").strip()
    if forwarded:
        hops = [part.strip() for part in forwarded.split(",") if part.strip()]
        if hops:
            return hops[-min(_trusted_hops(), len(hops))]
    return get_remote_address(request)


def rate_limit_storage_uri() -> str:
    return str(os.getenv("RATE_LIMIT_STORAGE_URI", "") or "").strip() or _DEFAULT_STORAGE_URI


# If shared storage is unreachable (bad URL, Redis down), fall back to per-process
# memory instead of failing the request: a broken limiter must never block logins.
limiter = Limiter(
    key_func=client_rate_limit_key,
    storage_uri=rate_limit_storage_uri(),
    in_memory_fallback_enabled=True,
    swallow_errors=True,
)
