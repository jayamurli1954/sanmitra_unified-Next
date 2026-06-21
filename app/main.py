import asyncio
import logging

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.rate_limiting import limiter

_startup_logger = logging.getLogger(__name__)

from app.accounting.models.base import Base
from app.api.legacy_alias_router import router as legacy_alias_router
from app.api.v1.router import api_router
from app.api.gruhamitra_compat_router import router as gruhamitra_compat_router
from app.accounting.report_alias_router import router as accounting_report_alias_router
from app.config import get_settings
from app.core.audit.service import ensure_audit_indexes
from app.core.onboarding.service import ensure_onboarding_indexes
from app.core.tenants.context import TenantContextMiddleware
from app.core.tenants.service import ensure_seed_tenant
from app.core.users.service import ensure_demo_mitrabooks_user, ensure_seed_user, ensure_super_admin_user
from app.db.mongo import close_mongo, init_mongo, ping_mongo
from app.db.postgres import close_postgres, create_postgres_tables, get_session_factory, init_postgres, ping_postgres
from app.modules.business.seed import ensure_mitrabooks_e2e_seed
from app.modules.housing.service import ensure_maintenance_indexes
from app.modules.housing_compat.service import ensure_housing_compat_indexes
from app.modules.legal.service import ensure_legal_indexes
from app.modules.legal_compat.service import ensure_legal_compat_indexes
from app.modules.legal_compat.retention import cleanup_expired_legal_retention_records, ensure_legal_retention_indexes
from app.modules.legal_compat.sync_worker import start_legal_sync_worker, stop_legal_sync_worker
from app.modules.mandir_compat.reminder_worker import start_seva_reminder_worker, stop_seva_reminder_worker
from app.modules.mandir_compat.service import ensure_demo_mandir_bootstrap
from app.modules.rag.service import ensure_rag_indexes
from app.modules.temple.service import ensure_donations_indexes

settings = get_settings()

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    # Restrict to known SanMitra Vercel apps only; the broad *.vercel.app wildcard
    # would allow any Vercel deployment to make credentialed cross-origin requests.
    allow_origin_regex=(
        r"https://(mitrabooks|mitrabooks-erp|mandirmitra|mandir-mitra-alpha|legalmitra|gruhamitra|invest-mitra)"
        r"(-[a-z0-9-]+)?\.vercel\.app"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TenantContextMiddleware)


_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
_API_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "frame-ancestors 'none'"
)
_CSP_EXEMPT_PATHS = {"/docs", "/redoc", "/openapi.json"}


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    for header, value in _SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)

    if request.url.path not in _CSP_EXEMPT_PATHS:
        response.headers.setdefault("Content-Security-Policy", _API_CONTENT_SECURITY_POLICY)

    forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
    if request.url.scheme == "https" or forwarded_proto == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

    return response


app.include_router(legacy_alias_router)
app.include_router(api_router)
app.include_router(gruhamitra_compat_router, prefix="/api", tags=["gruhamitra-frontend-compat"])
app.include_router(accounting_report_alias_router, prefix="/api", tags=["accounting-reports-compat"])


@app.on_event("startup")
async def on_startup() -> None:
    try:
        await init_mongo()
        await ensure_seed_tenant()
        await ensure_seed_user()
        await ensure_super_admin_user()
        if settings.DEMO_MITRABOOKS_BOOTSTRAP:
            if settings.DEMO_MITRABOOKS_ADMIN_PASSWORD:
                demo_mitrabooks_emails = []
                for email in [settings.DEMO_MITRABOOKS_ADMIN_EMAIL, *settings.DEMO_MITRABOOKS_ADMIN_ALIAS_EMAILS]:
                    normalized_email = str(email or "").strip().lower()
                    if normalized_email and normalized_email not in demo_mitrabooks_emails:
                        demo_mitrabooks_emails.append(normalized_email)
                seeded_count = 0
                for email in demo_mitrabooks_emails:
                    user = await ensure_demo_mitrabooks_user(
                        email=email,
                        password=settings.DEMO_MITRABOOKS_ADMIN_PASSWORD,
                        full_name=settings.DEMO_MITRABOOKS_ADMIN_FULL_NAME,
                        tenant_id=settings.DEMO_MITRABOOKS_TENANT_ID,
                    )
                    if user is not None:
                        seeded_count += 1
                _startup_logger.info(
                    "MitraBooks demo admin bootstrap completed for tenant=%s emails=%s",
                    settings.DEMO_MITRABOOKS_TENANT_ID,
                    seeded_count,
                )
            else:
                _startup_logger.warning(
                    "MitraBooks demo admin bootstrap skipped: DEMO_MITRABOOKS_ADMIN_PASSWORD is not set"
                )
        await ensure_demo_mandir_bootstrap()
        await ensure_audit_indexes()
        await ensure_donations_indexes()
        await ensure_maintenance_indexes()
        await ensure_housing_compat_indexes()
        await ensure_legal_indexes()
        await ensure_legal_compat_indexes()
        await ensure_legal_retention_indexes()
        await cleanup_expired_legal_retention_records()
        # InvestMitra excluded from unified scope — investment indexes not provisioned.
        await ensure_onboarding_indexes()
        await ensure_rag_indexes()
    except Exception as exc:
        # Keep app booting even if Mongo is unavailable; health endpoint will show degraded state.
        _startup_logger.error("MongoDB startup initialisation failed: %s", exc, exc_info=True)

    try:
        await start_legal_sync_worker()
    except Exception as exc:
        # Worker is best-effort; API should still boot even if background sync is unavailable.
        _startup_logger.warning("Legal sync worker failed to start: %s", exc, exc_info=True)

    try:
        await start_seva_reminder_worker()
    except Exception as exc:
        # Worker is best-effort; API should still boot even if reminder worker is unavailable.
        _startup_logger.warning("Seva reminder worker failed to start: %s", exc, exc_info=True)

    try:
        await init_postgres()
        # Ensure model metadata is loaded before create_all.
        import app.accounting.models.entities  # noqa: F401

        if settings.PG_AUTO_CREATE_TABLES:
            await create_postgres_tables(Base.metadata)

        # Warn loudly if DB migrations are behind. The party sub-ledger column is the
        # latest additive change; its absence means ledger postings 500 until migrated.
        try:
            from sqlalchemy import inspect as _sa_inspect

            async with get_session_factory()() as _mig_session:
                _conn = await _mig_session.connection()
                _jl_cols = await _conn.run_sync(
                    lambda c: [col["name"] for col in _sa_inspect(c).get_columns("journal_lines")]
                )
            if "party_id" not in _jl_cols:
                _startup_logger.warning(
                    "DB MIGRATIONS BEHIND: journal_lines.party_id is missing. "
                    "Run 'alembic upgrade head' on this database. Ledger postings "
                    "(invoices/bills/vouchers) will fail with HTTP 500 until applied."
                )
        except Exception as mig_exc:  # never block startup on the check itself
            _startup_logger.warning("Migration-state check skipped: %s", mig_exc)
        if settings.DEMO_MITRABOOKS_E2E_SEED_ENABLED:
            session_factory = get_session_factory()
            async with session_factory() as session:
                seed_result = await ensure_mitrabooks_e2e_seed(
                    session,
                    tenant_id=settings.DEMO_MITRABOOKS_TENANT_ID,
                    created_by=settings.DEMO_MITRABOOKS_ADMIN_EMAIL or "system",
                )
            _startup_logger.info("MitraBooks E2E seed completed: %s", seed_result)
    except Exception as exc:
        # Keep app booting even if PostgreSQL is unavailable; health endpoint will show degraded state.
        _startup_logger.error("PostgreSQL startup initialisation failed: %s", exc, exc_info=True)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await stop_seva_reminder_worker()
    await stop_legal_sync_worker()
    await close_mongo()
    await close_postgres()


async def _ping_with_timeout(coro, timeout_seconds: float) -> tuple[bool, str]:
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        return False, "timeout"
    except Exception as exc:
        return False, str(exc)


@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    """Root route — satisfies Render's HEAD / health check (returns 200 for both GET and HEAD)."""
    return {"status": "ok", "service": "sanmitra-unified-next"}


@app.get("/health")
async def health(response: Response):
    mongo_task = _ping_with_timeout(ping_mongo(), timeout_seconds=2.5)
    pg_task = _ping_with_timeout(ping_postgres(), timeout_seconds=2.5)
    mongo_result, pg_result = await asyncio.gather(mongo_task, pg_task)

    mongo_ok, mongo_detail = mongo_result
    pg_ok, pg_detail = pg_result

    # Postgres holds the ledger → down = hard error; Mongo down = degraded.
    if not pg_ok:
        overall = "error"
    elif not mongo_ok:
        overall = "degraded"
    else:
        overall = "ok"

    if overall == "error":
        response.status_code = 503

    payload: dict = {
        "status": overall,
        "version": settings.APP_VERSION,
        "checks": {
            "postgres": {"status": "connected" if pg_ok else "error", "detail": pg_detail},
            "mongo": {"status": "connected" if mongo_ok else "error", "detail": mongo_detail},
        },
    }
    # Expose environment only in non-production to avoid leaking deployment topology.
    if settings.ENVIRONMENT not in {"production", "prod"}:
        payload["environment"] = settings.ENVIRONMENT
    return payload



