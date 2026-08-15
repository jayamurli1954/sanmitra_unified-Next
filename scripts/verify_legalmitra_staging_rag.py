#!/usr/bin/env python3
"""Verify LegalMitra Stage 2 staging RAG readiness (corpus + retrieval quality).

Rate-limit aware: sleeps between API calls. Does not flip LEGAL_RAG_ENABLED.

Examples:

  # Corpus counts only (point MONGODB_URI at staging Atlas temporarily)
  $env:MONGODB_URI="..."
  $env:MONGO_DB_NAME="..."
  python scripts/verify_legalmitra_staging_rag.py --mode corpus --tenant-id demo-legal-firm

  # API retrieval checks against staging (LEGAL_RAG may still be false; uses /rag/query)
  $env:STAGING_API_BASE_URL="https://sanmitra-unified-next-staging-sg.onrender.com"
  $env:E2E_USER_EMAIL="..."
  $env:E2E_USER_PASSWORD="..."
  python scripts/verify_legalmitra_staging_rag.py --mode api --sleep-ms 800
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_ACTS = ("cgst", "cgst_rules", "income_tax_1961")
DEFAULT_MIN_COUNTS = {
    "cgst": 150,
    "cgst_rules": 100,
    "income_tax_1961": 400,
}

PROBE_QUERIES = (
    {
        "id": "gst-54",
        "query": "CGST Act Section 54 refund of tax time limit two years",
        "must_terms": ("54", "refund"),
    },
    {
        "id": "it-139",
        "query": "Income-tax Act Section 139 return of income",
        "must_terms": ("139", "return"),
    },
    {
        "id": "refuse-noise",
        "query": "painting contractor liability owner supplied materials contract act",
        "must_not_dominate": ("gst", "cgst", "section 54"),
    },
)


def _sleep(ms: int) -> None:
    if ms > 0:
        time.sleep(ms / 1000.0)


def _login(base: str, email: str, password: str, app_key: str) -> str:
    with httpx.Client(timeout=45.0) as client:
        response = client.post(
            f"{base.rstrip('/')}/api/v1/auth/login",
            json={"email": email, "password": password},
            headers={"X-App-Key": app_key},
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token") or payload.get("token")
        if not token:
            raise RuntimeError(f"Login response missing token: {payload}")
        return str(token)


def verify_corpus(*, tenant_id: str, app_key: str, acts: list[str]) -> dict[str, Any]:
    import asyncio

    from app.db.mongo import close_mongo, get_collection, init_mongo

    async def _run() -> dict[str, Any]:
        await init_mongo()
        try:
            sections = get_collection("legal_statute_sections")
            chunks = get_collection("rag_chunks")
            counts: dict[str, Any] = {}
            failures: list[str] = []
            for act in acts:
                section_count = await sections.count_documents(
                    {"tenant_id": tenant_id, "app_key": app_key, "act_key": act}
                )
                chunk_count = await chunks.count_documents(
                    {
                        "tenant_id": tenant_id,
                        "app_key": app_key,
                        "metadata.ingest_manifest_key": act,
                    }
                )
                minimum = DEFAULT_MIN_COUNTS.get(act, 1)
                ok = section_count >= minimum
                counts[act] = {
                    "sections": section_count,
                    "chunks": chunk_count,
                    "min_sections": minimum,
                    "ok": ok,
                }
                if not ok:
                    failures.append(f"{act}: sections={section_count} < min={minimum}")
            return {
                "ok": not failures,
                "tenant_id": tenant_id,
                "app_key": app_key,
                "counts": counts,
                "failures": failures,
            }
        finally:
            await close_mongo()

    return asyncio.run(_run())


def _citation_blob(citations: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in citations:
        parts.append(str(item.get("title") or ""))
        parts.append(str(item.get("snippet") or ""))
        meta = item.get("legal_metadata") or {}
        if isinstance(meta, dict):
            parts.extend(str(v) for v in meta.values())
    return " ".join(parts).lower()


def verify_api(
    *,
    base: str,
    email: str,
    password: str,
    app_key: str,
    sleep_ms: int,
) -> dict[str, Any]:
    token = _login(base, email, password, app_key)
    _sleep(sleep_ms)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-App-Key": app_key,
        "Content-Type": "application/json",
    }
    results: list[dict[str, Any]] = []
    failures: list[str] = []

    with httpx.Client(timeout=60.0) as client:
        for probe in PROBE_QUERIES:
            _sleep(sleep_ms)
            response = client.post(
                f"{base.rstrip('/')}/api/v1/rag/query",
                headers=headers,
                json={"query": probe["query"], "top_k": 5, "max_candidates": 200},
            )
            if response.status_code == 429:
                failures.append(f"{probe['id']}: rate limited (429) — increase --sleep-ms and retry")
                results.append({"id": probe["id"], "ok": False, "status_code": 429})
                _sleep(max(sleep_ms, 2000))
                continue
            if response.status_code >= 400:
                failures.append(f"{probe['id']}: HTTP {response.status_code} {response.text[:200]}")
                results.append({"id": probe["id"], "ok": False, "status_code": response.status_code})
                continue

            payload = response.json()
            citations = list(payload.get("citations") or [])
            blob = _citation_blob(citations)
            ok = True
            notes: list[str] = []

            for term in probe.get("must_terms") or ():
                if term.lower() not in blob and citations:
                    # Soft fail if no citations at all — corpus may be empty for tenant
                    ok = False
                    notes.append(f"missing term '{term}' in top citations")
            if not citations:
                ok = False
                notes.append("no citations returned (corpus missing for this tenant, or RAG empty)")

            dominate = probe.get("must_not_dominate") or ()
            if dominate and citations:
                hits = sum(1 for term in dominate if term.lower() in blob)
                if hits >= max(2, len(dominate) - 1):
                    ok = False
                    notes.append("irrelevant GST/tax citations dominate unrelated query")

            if not ok:
                failures.append(f"{probe['id']}: " + "; ".join(notes))
            results.append(
                {
                    "id": probe["id"],
                    "ok": ok,
                    "citation_count": len(citations),
                    "strategy": payload.get("strategy"),
                    "notes": notes,
                    "titles": [c.get("title") for c in citations[:3]],
                }
            )

    return {"ok": not failures, "results": results, "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify LegalMitra staging RAG corpus/retrieval.")
    parser.add_argument("--mode", choices=("corpus", "api", "both"), default="both")
    parser.add_argument(
        "--tenant-id",
        default=os.getenv("LEGAL_INGEST_TENANT_ID") or os.getenv("DEMO_LEGAL_TENANT_ID") or "demo-legal-firm",
    )
    parser.add_argument("--app-key", default="legalmitra")
    parser.add_argument("--acts", nargs="+", default=list(DEFAULT_ACTS))
    parser.add_argument(
        "--api-base",
        default=os.getenv("STAGING_API_BASE_URL", "https://sanmitra-unified-next-staging-sg.onrender.com"),
    )
    parser.add_argument("--email", default=os.getenv("E2E_USER_EMAIL", ""))
    parser.add_argument("--password", default=os.getenv("E2E_USER_PASSWORD", ""))
    parser.add_argument(
        "--sleep-ms",
        type=int,
        default=int(os.getenv("LEGAL_STAGING_VERIFY_SLEEP_MS", "800")),
        help="Delay between API calls to avoid staging rate limits (default 800).",
    )
    parser.add_argument("--json-out", default="", help="Optional path to write full JSON report.")
    args = parser.parse_args()
    if str(args.tenant_id or "").strip() == "seed-tenant-1":
        raise SystemExit(
            "seed-tenant-1 is the MandirMitra temple seed. "
            "Pass DEMO_LEGAL_TENANT_ID (demo-legal-firm)."
        )

    report: dict[str, Any] = {"ok": True, "mode": args.mode}

    if args.mode in {"corpus", "both"}:
        if not os.getenv("MONGODB_URI"):
            report["corpus"] = {
                "ok": False,
                "failures": ["MONGODB_URI not set — required for --mode corpus/both"],
            }
            report["ok"] = False
        else:
            corpus = verify_corpus(
                tenant_id=args.tenant_id,
                app_key=args.app_key,
                acts=list(args.acts),
            )
            report["corpus"] = corpus
            report["ok"] = report["ok"] and bool(corpus.get("ok"))

    if args.mode in {"api", "both"}:
        if not args.email or not args.password:
            report["api"] = {
                "ok": False,
                "failures": ["E2E_USER_EMAIL / E2E_USER_PASSWORD (or --email/--password) required"],
            }
            report["ok"] = False
        else:
            api = verify_api(
                base=args.api_base,
                email=args.email,
                password=args.password,
                app_key=args.app_key,
                sleep_ms=args.sleep_ms,
            )
            report["api"] = api
            report["ok"] = report["ok"] and bool(api.get("ok"))

    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n", encoding="utf-8")

    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
