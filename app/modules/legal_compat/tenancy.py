"""LegalMitra corpus tenant — never the MandirMitra temple seed.

Current: local history parked LegalMitra RAG rows on ``seed-tenant-1`` (TEMPLE).
Target: LegalMitra ingest, public act catalog, and open registration use
``DEMO_LEGAL_TENANT_ID`` (LEGAL org, app key ``legalmitra``).
"""
from __future__ import annotations

from app.config import Settings, get_settings

LEGALMITRA_APP_KEY = "legalmitra"
TEMPLE_SEED_TENANT_ID = "seed-tenant-1"
DEFAULT_LEGAL_DEMO_TENANT_ID = "demo-legal-firm"


def legalmitra_corpus_tenant_id(settings: Settings | None = None) -> str:
    """Tenant that owns LegalMitra RAG corpus and the public acts catalog."""
    settings = settings or get_settings()
    ingest = str(getattr(settings, "LEGAL_INGEST_TENANT_ID", "") or "").strip()
    demo = str(getattr(settings, "DEMO_LEGAL_TENANT_ID", "") or "").strip() or DEFAULT_LEGAL_DEMO_TENANT_ID
    blocked = forbidden_legal_ingest_tenants(settings)
    if ingest and ingest not in blocked:
        return ingest
    return require_legalmitra_ingest_tenant(demo, settings=settings)


def forbidden_legal_ingest_tenants(settings: Settings | None = None) -> set[str]:
    settings = settings or get_settings()
    blocked = {TEMPLE_SEED_TENANT_ID}
    mandir = str(getattr(settings, "DEMO_MANDIR_TENANT_ID", "") or "").strip()
    if mandir:
        blocked.add(mandir)
    return {item for item in blocked if item}


def require_legalmitra_ingest_tenant(tenant_id: str, settings: Settings | None = None) -> str:
    """Reject MandirMitra/temple seed tenants for LegalMitra corpus writes."""
    settings = settings or get_settings()
    normalized = str(tenant_id or "").strip()
    if not normalized:
        raise ValueError("LegalMitra ingest tenant_id is required")
    if normalized in forbidden_legal_ingest_tenants(settings):
        demo = str(getattr(settings, "DEMO_LEGAL_TENANT_ID", "") or "").strip() or DEFAULT_LEGAL_DEMO_TENANT_ID
        raise ValueError(
            f"LegalMitra ingest cannot use MandirMitra/temple tenant {normalized!r}. "
            f"Use DEMO_LEGAL_TENANT_ID ({demo})."
        )
    return normalized
