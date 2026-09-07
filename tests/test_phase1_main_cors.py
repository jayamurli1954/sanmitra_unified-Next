"""phase1_main is a test/dev entrypoint and must not use wildcard CORS."""
from __future__ import annotations

from fastapi.middleware.cors import CORSMiddleware

from app.phase1_main import app


def test_phase1_main_cors_is_allowlisted_not_wildcard() -> None:
    middleware = next(item for item in app.user_middleware if item.cls is CORSMiddleware)
    origins = middleware.kwargs.get("allow_origins") or []
    assert origins, "phase1 CORS must keep an explicit origin allowlist"
    assert "*" not in origins
    assert middleware.kwargs.get("allow_credentials") is True
