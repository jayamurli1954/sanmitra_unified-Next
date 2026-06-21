import logging
import os
import re
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_config_logger = logging.getLogger(__name__)

# Read VERSION file if it exists, otherwise fall back to env var or default
def _get_app_version() -> str:
    version_file = Path(__file__).parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return os.getenv("APP_VERSION", "1.2.0")


class Settings:
    APP_NAME = os.getenv("APP_NAME", "SanMitra Unified Backend")
    APP_VERSION = _get_app_version()
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

    MONGODB_URI = os.getenv("MONGODB_URI", "")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sanmitra")
    MONGO_SERVER_SELECTION_TIMEOUT_MS = int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "2000"))
    MONGO_CONNECT_TIMEOUT_MS = int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "2000"))
    MONGO_SOCKET_TIMEOUT_MS = int(os.getenv("MONGO_SOCKET_TIMEOUT_MS", "5000"))

    POSTGRES_URI = os.getenv("POSTGRES_URI", "")
    PG_CONNECT_TIMEOUT_SECONDS = int(os.getenv("PG_CONNECT_TIMEOUT_SECONDS", "5"))
    PG_POOL_SIZE = int(os.getenv("PG_POOL_SIZE", "8"))
    PG_MAX_OVERFLOW = int(os.getenv("PG_MAX_OVERFLOW", "0"))
    PG_POOL_TIMEOUT_SECONDS = int(os.getenv("PG_POOL_TIMEOUT_SECONDS", "5"))
    PG_POOL_RECYCLE_SECONDS = int(os.getenv("PG_POOL_RECYCLE_SECONDS", "1800"))
    PG_AUTO_CREATE_TABLES = os.getenv("PG_AUTO_CREATE_TABLES", "true").lower() in {"1", "true", "yes", "on"}

    JWT_SECRET = os.getenv("JWT_SECRET", "")
    # Validated at startup — see validate() below.
    OTP_PEPPER = os.getenv("OTP_PEPPER", "")
    VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
    VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    _env_origins = [
        origin.strip()
        for origin in re.split(r"[,\r\n]+", os.getenv("ALLOWED_ORIGINS", ""))
        if origin.strip() and origin.strip() != "*"
    ]
    ALLOWED_ORIGINS = list(set(_env_origins + [
        "https://mitrabooks-erp.vercel.app",
        "https://mitrabooks-erp-staging.vercel.app",
        "https://mitrabooks.sanmitratech.in",
        "https://www.mitrabooks.sanmitratech.in",
        "https://staging.mitrabooks.sanmitratech.in",
        "https://mandirmitra.sanmitratech.in",
        "https://www.mandirmitra.sanmitratech.in",
        "https://gruhamitra.sanmitratech.in",
        "https://www.gruhamitra.sanmitratech.in",
        "https://mandirmitra.vercel.app",
        "https://mandir-mitra-alpha.vercel.app",
        "https://legalmitra.vercel.app",
        "https://gruhamitra.vercel.app",
        "https://invest-mitra.vercel.app",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3006",
        "http://127.0.0.1:3006",
        "http://localhost:3100",
        "http://127.0.0.1:3100",
        "http://localhost:3200",
        "http://127.0.0.1:3200",
        "http://localhost:3201",
        "http://127.0.0.1:3201",
        "http://localhost:3300",
        "http://127.0.0.1:3300",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "null",
    ]))
    GOOGLE_OAUTH_CLIENT_IDS = [
        client_id.strip()
        for client_id in os.getenv("GOOGLE_OAUTH_CLIENT_IDS", "").split(",")
        if client_id.strip()
    ]
    AUTH_PUBLIC_BASE_URL = os.getenv("AUTH_PUBLIC_BASE_URL", "").strip()
    MITRABOOKS_PUBLIC_URL = os.getenv("MITRABOOKS_PUBLIC_URL", "").strip()
    AUTH_ACTIVATION_TOKEN_TTL_MINUTES = int(os.getenv("AUTH_ACTIVATION_TOKEN_TTL_MINUTES", "60"))
    AUTH_RESET_TOKEN_TTL_MINUTES = int(os.getenv("AUTH_RESET_TOKEN_TTL_MINUTES", "30"))
    AUTH_EMAIL_DEBUG_RETURN_LINK = os.getenv(
        "AUTH_EMAIL_DEBUG_RETURN_LINK",
        "true" if ENVIRONMENT not in {"production", "prod"} else "false",
    ).lower() in {"1", "true", "yes", "on"}
    SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes", "on"}
    SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() in {"1", "true", "yes", "on"}
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "no-reply@sanmitra.local").strip()
    SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "SanMitra").strip()

    # Mobile OTP login settings
    MOBILE_OTP_ENABLED = os.getenv("MOBILE_OTP_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    MOBILE_OTP_LENGTH = int(os.getenv("MOBILE_OTP_LENGTH", "6"))
    MOBILE_OTP_TTL_SECONDS = int(os.getenv("MOBILE_OTP_TTL_SECONDS", "300"))
    MOBILE_OTP_MAX_ATTEMPTS = int(os.getenv("MOBILE_OTP_MAX_ATTEMPTS", "5"))
    MOBILE_OTP_RESEND_COOLDOWN_SECONDS = int(os.getenv("MOBILE_OTP_RESEND_COOLDOWN_SECONDS", "30"))
    MOBILE_OTP_DEBUG_RETURN_CODE = os.getenv("MOBILE_OTP_DEBUG_RETURN_CODE", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    MOBILE_OTP_PROVIDER = os.getenv("MOBILE_OTP_PROVIDER", "none").strip().lower()
    MOBILE_OTP_MESSAGE_TEMPLATE = os.getenv(
        "MOBILE_OTP_MESSAGE_TEMPLATE",
        "Your SanMitra OTP is {otp}. Valid for {ttl_minutes} minutes.",
    )
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "").strip()

    # Token required in X-Onboarding-Token header on the public first-login onboarding endpoint.
    # If left empty, the endpoint is open (dev/demo convenience); set in production.
    MANDIR_ONBOARDING_SECRET = os.getenv("MANDIR_ONBOARDING_SECRET", "").strip()

    DEFAULT_APP_KEY = os.getenv("DEFAULT_APP_KEY", "mandirmitra").strip().lower()
    ALLOWED_APP_KEYS = [
        key.strip().lower()
        # InvestMitra is intentionally excluded from the unified backend scope.
        # The investment module definitions remain in the registry as a dormant,
        # tested capability, but the app key is not accepted at runtime here.
        for key in os.getenv(
            "ALLOWED_APP_KEYS",
            "mandirmitra,gruhamitra,mitrabooks,legalmitra",
        ).split(",")
        if key.strip()
    ]

    # Phase-2 RAG embedding configuration
    RAG_EMBEDDING_PROVIDER = os.getenv("RAG_EMBEDDING_PROVIDER", "hash").strip().lower()
    RAG_EMBEDDING_HASH_DIM = int(os.getenv("RAG_EMBEDDING_HASH_DIM", "256"))
    RAG_EMBEDDING_ST_MODEL = os.getenv("RAG_EMBEDDING_ST_MODEL", "all-MiniLM-L6-v2").strip()

    # Gemini embeddings (same API key/project can be used as generation, if enabled)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    RAG_GEMINI_EMBED_MODEL = os.getenv("RAG_GEMINI_EMBED_MODEL", "gemini-embedding-001").strip()
    RAG_GEMINI_EMBED_DIM = int(os.getenv("RAG_GEMINI_EMBED_DIM", "768"))
    RAG_GEMINI_TASK_TYPE = os.getenv("RAG_GEMINI_TASK_TYPE", "RETRIEVAL_DOCUMENT").strip().upper()
    RAG_GEMINI_API_BASE = os.getenv("RAG_GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta").strip()

    # Hybrid legal response behavior
    LEGAL_HYBRID_AI_FALLBACK_ENABLED = os.getenv("LEGAL_HYBRID_AI_FALLBACK_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    # Set LEGAL_RAG_ENABLED=false to bypass the RAG knowledge-base lookup and send
    # queries directly to the Gemini Senior Counsel pipeline.  Use this in production
    # while the RAG corpus (semantic embeddings + authoritative legal documents) is
    # being rebuilt locally.  Re-enable once local RAG testing is satisfactory.
    LEGAL_RAG_ENABLED = os.getenv("LEGAL_RAG_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    CLAUDE_LEGAL_COUNSEL_ENABLED = os.getenv("CLAUDE_LEGAL_COUNSEL_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
    CLAUDE_LEGAL_COUNSEL_MODEL = os.getenv("CLAUDE_LEGAL_COUNSEL_MODEL", "claude-3-5-sonnet-latest").strip()
    ANTHROPIC_API_BASE = os.getenv("ANTHROPIC_API_BASE", "https://api.anthropic.com/v1").strip()
    LEGAL_FALLBACK_GEMINI_MODEL = os.getenv("LEGAL_FALLBACK_GEMINI_MODEL", "gemini-2.5-flash").strip()

    # MitraBooks Financial Health — AI narration of the CFO-Insight figures.
    # Reuses ANTHROPIC_API_KEY / ANTHROPIC_API_BASE. The model only rewrites the
    # already-computed figures as prose; it never invents numbers. Degrades to the
    # deterministic summary when disabled, unkeyed, or the call fails.
    FINANCIAL_HEALTH_AI_ENABLED = os.getenv("FINANCIAL_HEALTH_AI_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    FINANCIAL_HEALTH_AI_MODEL = os.getenv("FINANCIAL_HEALTH_AI_MODEL", "claude-haiku-4-5").strip()
    FINANCIAL_HEALTH_AI_MAX_TOKENS = int(os.getenv("FINANCIAL_HEALTH_AI_MAX_TOKENS", "400"))
    # Raised from 900 — Gemini fallback answers were truncating mid-sentence
    # because the prompt requests 5-6 structured sections (Quick Answer,
    # Business Impact, Key Rules, Action Plan, Risks, If You Want I Can).
    # 1800 gives enough headroom for all sections to complete.
    LEGAL_FALLBACK_MAX_TOKENS = int(os.getenv("LEGAL_FALLBACK_MAX_TOKENS", "1800"))

    # Auto-sync queue hooks for low-confidence legal queries
    RAG_AUTO_SYNC_ENABLED = os.getenv("RAG_AUTO_SYNC_ENABLED", "true").lower() in {"1", "true", "yes", "on"}

    # Legal RAG sync worker (continuous queue processor)
    LEGAL_SYNC_WORKER_ENABLED = os.getenv("LEGAL_SYNC_WORKER_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    LEGAL_SYNC_WORKER_POLL_SECONDS = int(os.getenv("LEGAL_SYNC_WORKER_POLL_SECONDS", "60"))
    LEGAL_SYNC_WORKER_BATCH_SIZE = int(os.getenv("LEGAL_SYNC_WORKER_BATCH_SIZE", "5"))
    LEGAL_SYNC_WORKER_MAX_ATTEMPTS = int(os.getenv("LEGAL_SYNC_WORKER_MAX_ATTEMPTS", "4"))
    LEGAL_SYNC_WORKER_LOCK_TIMEOUT_SECONDS = int(os.getenv("LEGAL_SYNC_WORKER_LOCK_TIMEOUT_SECONDS", "600"))
    LEGAL_SYNC_WORKER_MAX_SOURCES_PER_JOB = int(os.getenv("LEGAL_SYNC_WORKER_MAX_SOURCES_PER_JOB", "8"))
    LEGAL_SYNC_WORKER_HTTP_TIMEOUT_SECONDS = int(os.getenv("LEGAL_SYNC_WORKER_HTTP_TIMEOUT_SECONDS", "15"))
    # Official form bank (MVP upload constraints)
    LEGAL_OFFICIAL_FORM_MAX_UPLOAD_MB = int(os.getenv("LEGAL_OFFICIAL_FORM_MAX_UPLOAD_MB", "20"))
    LEGAL_OFFICIAL_FORM_MAX_PAGES = int(os.getenv("LEGAL_OFFICIAL_FORM_MAX_PAGES", "80"))
    LEGAL_OFFICIAL_FORM_MIN_SUGGESTED_LABELS = int(os.getenv("LEGAL_OFFICIAL_FORM_MIN_SUGGESTED_LABELS", "3"))

    # OpenAI-compatible embeddings gateway
    RAG_EMBEDDING_OPENAI_URL = os.getenv("RAG_EMBEDDING_OPENAI_URL", "").strip()
    RAG_EMBEDDING_OPENAI_MODEL = os.getenv("RAG_EMBEDDING_OPENAI_MODEL", "text-embedding-3-small").strip()
    RAG_EMBEDDING_OPENAI_API_KEY = os.getenv("RAG_EMBEDDING_OPENAI_API_KEY", "").strip()

    # Tavily Web Search (LegalMitra live judgement & news search)
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
    ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() in {"1", "true", "yes", "on"}
    WEB_SEARCH_TIMEOUT_SECONDS = int(os.getenv("WEB_SEARCH_TIMEOUT_SECONDS", "5"))

    # Razorpay Payments
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "").strip()
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
    RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "").strip()
    RAZORPAY_ACCOUNT_OWNER = os.getenv("RAZORPAY_ACCOUNT_OWNER", "Sanmita Tech Solutions").strip()
    RAZORPAY_MERCHANT_SCOPE = os.getenv("RAZORPAY_MERCHANT_SCOPE", "sanmitra_platform").strip()
    RAZORPAY_PAYMENT_PAGE_MAP_JSON = os.getenv("RAZORPAY_PAYMENT_PAGE_MAP_JSON", "").strip()

    _IS_PRODUCTION = ENVIRONMENT in {"production", "prod"}

    SUPER_ADMIN_BOOTSTRAP = os.getenv(
        "SUPER_ADMIN_BOOTSTRAP",
        "false" if _IS_PRODUCTION else "true",
    ).lower() in {"1", "true", "yes", "on"}
    SUPER_ADMIN_EMAIL = os.getenv("SUPER_ADMIN_EMAIL", "superadmin@sanmitra.local")
    # No default password — must be set explicitly when SUPER_ADMIN_BOOTSTRAP=true.
    SUPER_ADMIN_PASSWORD = os.getenv("SUPER_ADMIN_PASSWORD", "")
    SUPER_ADMIN_FULL_NAME = os.getenv("SUPER_ADMIN_FULL_NAME", "SanMitra Super Admin")
    SUPER_ADMIN_TENANT_ID = os.getenv("SUPER_ADMIN_TENANT_ID", "seed-tenant-1")

    # Demo Mandir bootstrap (non-production convenience seed)
    DEMO_MANDIR_BOOTSTRAP = os.getenv(
        "DEMO_MANDIR_BOOTSTRAP",
        "false" if _IS_PRODUCTION else "true",
    ).lower() in {"1", "true", "yes", "on"}
    DEMO_MANDIR_TENANT_ID = os.getenv("DEMO_MANDIR_TENANT_ID", "seed-tenant-1")
    DEMO_MANDIR_TEMPLE_NAME = os.getenv("DEMO_MANDIR_TEMPLE_NAME", "Local ERP Demo Temple")
    DEMO_MANDIR_TRUST_NAME = os.getenv("DEMO_MANDIR_TRUST_NAME", "Local ERP Demo Temple Trust")
    DEMO_MANDIR_TEMPLE_ADDRESS = os.getenv("DEMO_MANDIR_TEMPLE_ADDRESS", "Demo Temple Address")
    DEMO_MANDIR_TEMPLE_CONTACT = os.getenv("DEMO_MANDIR_TEMPLE_CONTACT", "+91-9000000000")
    DEMO_MANDIR_TEMPLE_EMAIL = os.getenv("DEMO_MANDIR_TEMPLE_EMAIL", "temple.demo@sanmitra.local")
    DEMO_MANDIR_CITY = os.getenv("DEMO_MANDIR_CITY", "Bengaluru")
    DEMO_MANDIR_STATE = os.getenv("DEMO_MANDIR_STATE", "Karnataka")
    DEMO_MANDIR_UPI_ID = os.getenv("DEMO_MANDIR_UPI_ID", "demo-temple@sanmitra")
    DEMO_MANDIR_UPI_PAYEE_NAME = os.getenv("DEMO_MANDIR_UPI_PAYEE_NAME", "Local ERP Demo Temple Trust")
    DEMO_MANDIR_ADMIN_FULL_NAME = os.getenv("DEMO_MANDIR_ADMIN_FULL_NAME", "Demo Temple Admin")
    DEMO_MANDIR_ADMIN_EMAIL = os.getenv("DEMO_MANDIR_ADMIN_EMAIL", "demo.admin@sanmitra.local")
    # No default password — must be set explicitly when DEMO_MANDIR_BOOTSTRAP=true.
    DEMO_MANDIR_ADMIN_PASSWORD = os.getenv("DEMO_MANDIR_ADMIN_PASSWORD", "")
    DEMO_MANDIR_ADMIN_PHONE = os.getenv("DEMO_MANDIR_ADMIN_PHONE", "+91-9000000001")

    DEMO_MITRABOOKS_BOOTSTRAP = os.getenv("DEMO_MITRABOOKS_BOOTSTRAP", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    DEMO_MITRABOOKS_TENANT_ID = os.getenv("DEMO_MITRABOOKS_TENANT_ID", "demo-mitrabooks-business")
    DEMO_MITRABOOKS_ADMIN_EMAIL = os.getenv("DEMO_MITRABOOKS_ADMIN_EMAIL", "admin@mitrabooks.local")
    DEMO_MITRABOOKS_ADMIN_PASSWORD = os.getenv("DEMO_MITRABOOKS_ADMIN_PASSWORD", "")
    DEMO_MITRABOOKS_ADMIN_FULL_NAME = os.getenv("DEMO_MITRABOOKS_ADMIN_FULL_NAME", "MitraBooks Admin")
    DEMO_MITRABOOKS_ADMIN_ALIAS_EMAILS = [
        email.strip().lower()
        for email in os.getenv(
            "DEMO_MITRABOOKS_ADMIN_ALIAS_EMAILS",
            "business.admin@sanmitra.local,businessadmin@sanmitra.local",
        ).split(",")
        if email.strip()
    ]
    DEMO_MITRABOOKS_E2E_SEED_ENABLED = os.getenv("DEMO_MITRABOOKS_E2E_SEED_ENABLED", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


    def validate(self) -> None:
        """Fail fast on dangerous mis-configuration before the app accepts traffic."""
        is_prod = self._IS_PRODUCTION

        if not self.JWT_SECRET:
            if is_prod:
                raise ValueError(
                    "JWT_SECRET must be set in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_hex(64))\""
                )
            _config_logger.warning(
                "JWT_SECRET is not set. Tokens are signed with an empty secret. "
                "Set JWT_SECRET before deploying to production."
            )

        if not self.VAPID_PUBLIC_KEY or not self.VAPID_PRIVATE_KEY:
            try:
                import base64
                from py_vapid import Vapid
                vapid = Vapid()
                vapid.generate_keys()
                public_key_bytes = vapid.public_key.to_string("uncompressed")
                self.VAPID_PUBLIC_KEY = base64.urlsafe_b64encode(public_key_bytes).decode('utf-8').rstrip('=')
                private_value = vapid.private_key.private_numbers().private_value
                private_key_bytes = private_value.to_bytes(32, byteorder="big")
                self.VAPID_PRIVATE_KEY = base64.urlsafe_b64encode(private_key_bytes).decode('utf-8').rstrip('=')
                _config_logger.warning(
                    "VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY are not configured. Generated a temporary keypair. "
                    "Push subscriptions will expire and fail on server restart."
                )
            except Exception as e:
                _config_logger.error("Failed to generate temporary VAPID keys: %s", e)

        if is_prod and self.AUTH_EMAIL_DEBUG_RETURN_LINK:
            raise ValueError(
                "AUTH_EMAIL_DEBUG_RETURN_LINK must be disabled in production "
                "(it returns one-time tokens in API responses)."
            )

        if is_prod and self.MOBILE_OTP_DEBUG_RETURN_CODE:
            raise ValueError(
                "MOBILE_OTP_DEBUG_RETURN_CODE must be disabled in production "
                "(it returns OTP codes in API responses)."
            )

        if self.SUPER_ADMIN_BOOTSTRAP and not self.SUPER_ADMIN_PASSWORD:
            if is_prod:
                raise ValueError(
                    "SUPER_ADMIN_PASSWORD must be set when SUPER_ADMIN_BOOTSTRAP=true."
                )
            _config_logger.warning(
                "SUPER_ADMIN_BOOTSTRAP=true but SUPER_ADMIN_PASSWORD is not set — "
                "bootstrap will be skipped at startup. Set SUPER_ADMIN_PASSWORD to enable it."
            )

        if self.DEMO_MANDIR_BOOTSTRAP and not self.DEMO_MANDIR_ADMIN_PASSWORD:
            if is_prod:
                raise ValueError(
                    "DEMO_MANDIR_ADMIN_PASSWORD must be set when DEMO_MANDIR_BOOTSTRAP=true."
                )
            _config_logger.warning(
                "DEMO_MANDIR_BOOTSTRAP=true but DEMO_MANDIR_ADMIN_PASSWORD is not set — "
                "demo bootstrap will be skipped at startup."
            )

        if self.DEMO_MITRABOOKS_BOOTSTRAP and not self.DEMO_MITRABOOKS_ADMIN_PASSWORD:
            if is_prod:
                raise ValueError(
                    "DEMO_MITRABOOKS_ADMIN_PASSWORD must be set when DEMO_MITRABOOKS_BOOTSTRAP=true."
                )
            _config_logger.warning(
                "DEMO_MITRABOOKS_BOOTSTRAP=true but DEMO_MITRABOOKS_ADMIN_PASSWORD is not set — "
                "demo bootstrap will be skipped at startup."
            )

        if is_prod and (
            self.SUPER_ADMIN_BOOTSTRAP
            or self.DEMO_MANDIR_BOOTSTRAP
            or self.DEMO_MITRABOOKS_BOOTSTRAP
            or self.DEMO_MITRABOOKS_E2E_SEED_ENABLED
        ):
            _config_logger.warning(
                "Bootstrap flags (SUPER_ADMIN_BOOTSTRAP / DEMO_MANDIR_BOOTSTRAP / "
                "DEMO_MITRABOOKS_BOOTSTRAP / DEMO_MITRABOOKS_E2E_SEED_ENABLED) are enabled "
                "in a production environment. Ensure this is intentional."
            )

        if not self.OTP_PEPPER:
            if is_prod:
                raise ValueError(
                    "OTP_PEPPER must be set in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
            _config_logger.warning(
                "OTP_PEPPER is not set. OTP hashes will use JWT_SECRET as fallback. "
                "Set OTP_PEPPER before deploying to production."
            )

        # DB pool recycle: warn if > 5 minutes (Render/RDS drop idle connections ~300s)
        if self.PG_POOL_RECYCLE_SECONDS > 300:
            _config_logger.warning(
                "PG_POOL_RECYCLE_SECONDS=%d is high. Consider setting it to <=300 to avoid "
                "stale connection errors on Render/RDS (which drops idle connections ~300s).",
                self.PG_POOL_RECYCLE_SECONDS,
            )


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.validate()
    return s
