"""
Phase 1: Foundation - Main FastAPI Application.

Production-ready with logging, middleware, and lifecycle management.
"""

import asyncio
import logging
import os
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.phase1_config import get_settings
from app.db.mongo import close_mongo, init_mongo, ping_mongo
from app.db.postgres import close_postgres, init_postgres, ping_postgres
from app.utils.logging_config import configure_logging

settings = get_settings()

# Configure logging
log_level = "DEBUG" if settings.ENVIRONMENT == "development" else "INFO"
configure_logging(log_level)
logger = logging.getLogger(__name__)


def _is_local_mongo_uri(uri: str) -> bool:
    parsed = urlparse(uri)
    hosts: list[str] = []

    if parsed.hostname:
        hosts.append(parsed.hostname.lower())

    if parsed.netloc and "@" in parsed.netloc:
        # Handles mongodb://user:pass@host:port/db
        netloc = parsed.netloc.split("@", 1)[1]
        host_part = netloc.split(",", 1)[0].split(":", 1)[0].strip().lower()
        if host_part:
            hosts.append(host_part)

    if not hosts and uri.startswith("mongodb"):
        # Fallback parser for uncommon URI forms
        tail = uri.split("://", 1)[-1]
        host_part = tail.split("/", 1)[0].split("@")[-1].split(",", 1)[0].split(":", 1)[0].strip().lower()
        if host_part:
            hosts.append(host_part)

    return any(h in {"localhost", "127.0.0.1", "::1"} for h in hosts)


def _local_mongo_bootstrap_script() -> Path:
    return Path(__file__).resolve().parent.parent / "START_LOCAL_MONGODB.ps1"


def _can_attempt_local_mongo_recovery() -> bool:
    if os.name != "nt":
        return False
    if settings.ENVIRONMENT not in {"development", "dev", "local"}:
        return False
    if not settings.MONGODB_URL:
        return False
    if not _is_local_mongo_uri(settings.MONGODB_URL):
        return False
    return _local_mongo_bootstrap_script().exists()


def _run_local_mongo_recovery() -> tuple[bool, str]:
    script = _local_mongo_bootstrap_script()
    if not script.exists():
        return False, f"Mongo bootstrap script not found: {script}"

    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except Exception as exc:
        return False, f"Failed to execute Mongo bootstrap: {exc}"

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    if stdout:
        logger.info("Mongo bootstrap output:\n%s", stdout)
    if stderr:
        logger.warning("Mongo bootstrap error output:\n%s", stderr)

    if result.returncode == 0:
        return True, "ok"
    return False, f"bootstrap_exit_{result.returncode}"


async def _wait_for_mongo(max_attempts: int, delay_seconds: float) -> tuple[bool, str]:
    last_detail = "unknown"
    for attempt in range(1, max_attempts + 1):
        mongo_ok, mongo_detail = await ping_mongo()
        if mongo_ok:
            return True, "ok"
        last_detail = mongo_detail
        logger.warning("MongoDB ping attempt %s/%s failed: %s", attempt, max_attempts, mongo_detail)
        if attempt < max_attempts:
            await asyncio.sleep(delay_seconds)
    return False, last_detail


async def _ensure_mongo_ready() -> None:
    await init_mongo()

    # First pass: short retries for normal startup races.
    mongo_ok, mongo_detail = await _wait_for_mongo(max_attempts=3, delay_seconds=1.2)
    if mongo_ok:
        logger.info("MongoDB initialized")
        return

    # Optional local self-heal on Windows dev machines using localhost Mongo.
    if _can_attempt_local_mongo_recovery():
        logger.warning("MongoDB unavailable. Attempting local bootstrap recovery...")
        recovered, reason = _run_local_mongo_recovery()
        if recovered:
            await asyncio.sleep(1.0)
            mongo_ok, mongo_detail = await _wait_for_mongo(max_attempts=6, delay_seconds=1.0)
            if mongo_ok:
                logger.info("MongoDB recovered via local bootstrap")
                return
            logger.error("MongoDB bootstrap ran but ping still failed: %s", mongo_detail)
        else:
            logger.error("MongoDB bootstrap recovery failed: %s", reason)

    raise RuntimeError(f"MongoDB ping failed: {mongo_detail}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan management.
    Startup: Initialize databases.
    Shutdown: Close connections.
    """
    logger.info("SanMitra Backend starting...")

    try:
        logger.info("Initializing PostgreSQL...")
        await init_postgres()
        pg_ok, pg_detail = await ping_postgres()
        if not pg_ok:
            raise RuntimeError(f"PostgreSQL ping failed: {pg_detail}")
        logger.info("PostgreSQL initialized")

        logger.info("Initializing MongoDB...")
        await _ensure_mongo_ready()

        logger.info("Application ready")
    except Exception as exc:
        logger.error("Startup failed: %s", exc)
        raise

    yield

    logger.info("SanMitra Backend shutting down...")
    try:
        await close_postgres()
        await close_mongo()
        logger.info("All connections closed")
    except Exception as exc:
        logger.error("Shutdown error: %s", exc)


# Create FastAPI app with lifespan
app = FastAPI(
    title=settings.API_TITLE,
    description="SanMitra: Multi-tenant SaaS platform for temples, housing, legal, investment",
    version=settings.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add CORS middleware - MUST be added before other middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    max_age=600,
)


@app.middleware("http")
async def log_requests(request, call_next):
    """Log all HTTP requests and responses."""
    logger.debug("%s %s", request.method, request.url.path)
    response = await call_next(request)
    logger.debug("Response: %s", response.status_code)
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    mongo_ok, mongo_detail = await ping_mongo()
    postgres_ok, postgres_detail = await ping_postgres()
    overall_status = "ok" if (mongo_ok and postgres_ok) else "degraded"

    return {
        "status": overall_status,
        "version": settings.API_VERSION,
        "db": {
            "mongo": {"ok": mongo_ok, "detail": mongo_detail},
            "postgres": {"ok": postgres_ok, "detail": postgres_detail},
        },
        "environment": settings.ENVIRONMENT,
    }


@app.options("/health")
async def options_health():
    """CORS preflight for health endpoint."""
    return {}


@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle CORS preflight requests for all endpoints."""
    return {}


from app.api.legacy_alias_router import router as legacy_router
from app.api.v1.router import api_router

app.include_router(api_router)
app.include_router(legacy_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.phase1_main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level="debug" if settings.ENVIRONMENT == "development" else "info",
    )