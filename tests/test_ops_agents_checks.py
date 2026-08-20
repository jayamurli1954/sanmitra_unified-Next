"""Unit tests for SanMitra ops-agent deterministic helpers (no network)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ops-agents" / "scripts"))

from checks import (  # noqa: E402
    check_version_drift,
    compute_verdict,
    deep_checks_attention,
    summarize_deep_checks,
)


def test_summarize_deep_checks_formats_postgres_mongo() -> None:
    line = summarize_deep_checks(
        {
            "postgres": {"status": "connected"},
            "mongo": {"status": "connected"},
        }
    )
    assert "postgres:connected" in line
    assert "mongo:connected" in line


def test_deep_checks_attention_on_mongo_error() -> None:
    assert deep_checks_attention({"mongo": {"status": "error"}}) is True
    assert deep_checks_attention({"postgres": {"status": "connected"}}) is False


def test_version_drift_detects_mismatch() -> None:
    drift = check_version_drift("1.3.1", "1.2.0")
    assert drift["drift"] is True
    aligned = check_version_drift("1.3.1", "1.3.1")
    assert aligned["drift"] is False


def test_compute_verdict_healthy() -> None:
    verdict, reasons = compute_verdict(
        product_rows=[
            {
                "name": "LegalMitra",
                "fe_ok": True,
                "be_ok": True,
                "ssl": {"expiring_soon": False},
                "fe": {"latency_ms": 20},
                "vercel": {"error": "not configured"},
            }
        ],
        backend_rows=[
            {
                "name": "Staging API",
                "skipped": False,
                "be_ok": True,
                "be": {"app_status": "ok", "latency_ms": 300},
                "deep_attention": False,
                "be_latency_warn": False,
            }
        ],
        version_drift={"drift": False},
        error_count=0,
    )
    assert verdict == "Healthy"
    assert reasons == []


def test_compute_verdict_attention_on_ssl_and_drift() -> None:
    verdict, reasons = compute_verdict(
        product_rows=[
            {
                "name": "LegalMitra",
                "fe_ok": True,
                "be_ok": True,
                "ssl": {"expiring_soon": True, "days_left": 10},
                "fe": {"latency_ms": 20},
                "vercel": {},
            }
        ],
        backend_rows=[
            {
                "name": "Staging API",
                "skipped": False,
                "be_ok": True,
                "be": {"app_status": "ok", "latency_ms": 300},
                "deep_attention": False,
                "be_latency_warn": False,
            }
        ],
        version_drift={"drift": True, "note": "repo=1.3.1 live=1.2.0"},
        error_count=0,
    )
    assert verdict == "Attention"
    assert any("SSL" in r for r in reasons)
    assert any("VERSION drift" in r for r in reasons)


def test_compute_verdict_action_needed_on_outage() -> None:
    verdict, reasons = compute_verdict(
        product_rows=[
            {
                "name": "MitraBooks",
                "fe_ok": False,
                "be_ok": True,
                "ssl": {"expiring_soon": False},
                "fe": {"latency_ms": None},
                "vercel": {},
            }
        ],
        backend_rows=[],
        version_drift={"drift": False},
        error_count=0,
    )
    assert verdict == "ACTION NEEDED"
    assert reasons
