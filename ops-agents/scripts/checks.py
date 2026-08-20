"""
Deterministic checks. No AI here, on purpose.

These answer the boring factual questions ("is the URL up", "does /health say
the DB is connected") with plain HTTP. They never touch a database directly and
never hold DB credentials. SSL validity is a side effect of letting requests
verify certs: an expired/invalid cert raises SSLError and is reported as such.
"""

from __future__ import annotations

import os
import ssl
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

TIMEOUT = float(os.getenv("CHECK_TIMEOUT_SECONDS", "20"))
HEALTH_TOKEN = os.getenv("HEALTH_TOKEN")  # forwarded if the backend requires it

DEFAULT_THRESHOLDS = {
    "fe_latency_ms_warn": 500,
    "be_latency_ms_warn": 2000,
    "ssl_warn_days": 21,
}


def check_frontend(url: str) -> dict[str, Any]:
    """Liveness of a frontend URL: reachable, HTTP status, latency."""
    result: dict[str, Any] = {"url": url, "reachable": False, "status_code": None,
                              "latency_ms": None, "ssl_ok": None, "error": None}
    try:
        resp = requests.get(url, timeout=TIMEOUT, allow_redirects=True)
        result.update(
            reachable=True,
            status_code=resp.status_code,
            latency_ms=int(resp.elapsed.total_seconds() * 1000),
            ssl_ok=url.startswith("https://"),  # no SSLError => cert verified
        )
    except requests.exceptions.SSLError as e:
        result.update(ssl_ok=False, error=f"ssl: {type(e).__name__}")
    except requests.exceptions.RequestException as e:
        result.update(error=f"{type(e).__name__}")
    return result


def check_backend_health(health_url: str) -> dict[str, Any]:
    """Call the backend /health endpoint and surface its self-report."""
    result: dict[str, Any] = {
        "url": health_url,
        "reachable": False,
        "status_code": None,
        "latency_ms": None,
        "app_status": None,
        "version": None,
        "checks": None,
        "error": None,
    }
    headers = {"X-Health-Token": HEALTH_TOKEN} if HEALTH_TOKEN else {}
    try:
        resp = requests.get(health_url, timeout=TIMEOUT, headers=headers)
        result.update(
            reachable=True,
            status_code=resp.status_code,
            latency_ms=int(resp.elapsed.total_seconds() * 1000),
        )
        try:
            body = resp.json()
            result["app_status"] = body.get("status")
            result["version"] = body.get("version")
            result["checks"] = body.get("checks")
        except ValueError:
            result["error"] = "health endpoint did not return JSON"
    except requests.exceptions.RequestException as e:
        result.update(error=f"{type(e).__name__}")
    return result


def summarize_deep_checks(checks: dict[str, Any] | None) -> str:
    """Compact postgres/mongo (etc.) line from /health.checks."""
    if not isinstance(checks, dict) or not checks:
        return "checks:n/a"
    parts: list[str] = []
    for name in ("postgres", "mongo", "redis"):
        item = checks.get(name)
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "?")
        parts.append(f"{name}:{status}")
    return " ".join(parts) if parts else "checks:n/a"


def deep_checks_attention(checks: dict[str, Any] | None) -> bool:
    """True when a dependency is not connected (mongo degraded, postgres error, …)."""
    if not isinstance(checks, dict):
        return False
    for item in checks.values():
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "").lower()
        if status and status not in {"connected", "ok", "up", "healthy"}:
            return True
    return False


def check_ssl_expiry(url: str, warn_days: int = 21) -> dict[str, Any]:
    """Days until the TLS cert expires. Cheap, no third-party service needed."""
    host = urlparse(url).hostname
    result: dict[str, Any] = {"host": host, "days_left": None,
                              "expiring_soon": None, "error": None}
    if not host:
        result["error"] = "no host in url"
        return result
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=host) as s:
            s.settimeout(TIMEOUT)
            s.connect((host, 443))
            not_after = s.getpeercert()["notAfter"]
        expires = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(
            tzinfo=timezone.utc)
        days = (expires - datetime.now(timezone.utc)).days
        result.update(days_left=days, expiring_soon=days <= warn_days)
    except Exception as e:
        result["error"] = f"{type(e).__name__}"
    return result


def classify_failure_layer(row: dict) -> str | None:
    """Return the most likely failure layer for a service row, or None if healthy."""
    fe_ok: bool = row["fe_ok"]
    be_ok: bool = row["be_ok"]
    ssl_error: bool = bool(row["ssl"].get("error"))
    fe_err: str = row["fe"].get("error") or ""
    host: str = urlparse(row["fe"].get("url") or "").hostname or "the frontend host"

    if fe_ok and be_ok:
        return None
    if not fe_ok and be_ok:
        if ssl_error:
            return (f"Frontend/DNS/SSL — TLS handshake to {host} failed; verify the "
                    "cert and DNS for whichever platform serves this host")
        if "Timeout" in fe_err or "timeout" in fe_err:
            return (f"Frontend/DNS — connection to {host} timed out; could be DNS, a "
                    "host firewall throttling the runner IP, or the platform being down")
        return (f"Frontend/DNS — backend healthy but {host} unreachable; check the "
                "frontend platform deployment and DNS")
    if not be_ok and fe_ok:
        return "Render/API/backend — frontend reachable but backend down; check Render service logs"
    return "DNS/global — both frontend and backend unreachable; check domain DNS and platform status pages"


def check_vercel_deployment(project_id: str, token: str) -> dict[str, Any]:
    """Query Vercel API for the latest production deployment state."""
    result: dict[str, Any] = {"status": None, "url": None, "age_hours": None, "error": None}
    if not project_id or not token:
        result["error"] = "not configured"
        return result
    try:
        resp = requests.get(
            "https://api.vercel.com/v6/deployments",
            params={"projectId": project_id, "limit": 1, "target": "production"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        resp.raise_for_status()
        deployments = resp.json().get("deployments", [])
        if not deployments:
            result["error"] = "no deployments found"
            return result
        d = deployments[0]
        created_ms = d.get("createdAt")
        age_hours = None
        if created_ms:
            created = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc)
            age_hours = round((datetime.now(timezone.utc) - created).total_seconds() / 3600, 1)
        result.update(
            status=d.get("state"),   # READY | ERROR | BUILDING | QUEUED | CANCELED
            url=d.get("url"),
            age_hours=age_hours,
        )
    except requests.exceptions.RequestException as e:
        result["error"] = f"{type(e).__name__}"
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
    return result


def check_consecutive_failures(gh_token: str, repo: str, workflow_filename: str, lookback: int = 5) -> int:
    """Return count of consecutive recent failures for a workflow via GitHub API.

    Returns 0 on any error or if the most recent run was successful.
    """
    if not gh_token or not repo:
        return 0
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_filename}/runs",
            params={"per_page": lookback, "status": "completed", "branch": "main"},
            headers={
                "Authorization": f"Bearer {gh_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=15,
        )
        resp.raise_for_status()
        runs = resp.json().get("workflow_runs", [])
        count = 0
        for run in runs:
            if run.get("conclusion") == "failure":
                count += 1
            else:
                break
        return count
    except Exception:
        return 0


def read_repo_version(repo_root: Path | None = None) -> str | None:
    """Read VERSION from repo root (ops drift check)."""
    root = repo_root or Path(__file__).resolve().parents[2]
    version_path = root / "VERSION"
    try:
        text = version_path.read_text(encoding="utf-8").strip()
        return text or None
    except OSError:
        return None


def check_version_drift(repo_version: str | None, live_version: str | None) -> dict[str, Any]:
    """Compare repo VERSION file to /health version field."""
    result: dict[str, Any] = {
        "repo_version": repo_version,
        "live_version": live_version,
        "drift": False,
        "note": None,
    }
    if not repo_version:
        result["note"] = "repo VERSION missing"
        return result
    if not live_version:
        result["note"] = "live version missing from /health"
        return result
    if str(repo_version).strip() != str(live_version).strip():
        result["drift"] = True
        result["note"] = f"repo={repo_version} live={live_version}"
    else:
        result["note"] = f"aligned at {repo_version}"
    return result


def resolve_backend_urls(backends: list[dict]) -> list[dict]:
    """Apply PRODUCTION_BACKEND_HEALTH_URL override; drop empty production URLs."""
    prod_override = (os.getenv("PRODUCTION_BACKEND_HEALTH_URL") or "").strip()
    resolved: list[dict] = []
    for b in backends or []:
        item = dict(b)
        env = str(item.get("env") or "").lower()
        url = str(item.get("health_url") or "").strip()
        if env == "production" and prod_override:
            url = prod_override
            item["health_url"] = url
        if not url:
            item["skipped"] = True
            item["skip_reason"] = (
                "PRODUCTION_BACKEND_HEALTH_URL not set"
                if env == "production"
                else "health_url empty"
            )
        else:
            item["skipped"] = False
        resolved.append(item)
    return resolved


def compute_verdict(
    *,
    product_rows: list[dict],
    backend_rows: list[dict],
    version_drift: dict[str, Any] | None,
    error_count: int,
) -> tuple[str, list[str]]:
    """Return (verdict, attention_reasons).

    Healthy | Attention | ACTION NEEDED
    """
    reasons: list[str] = []
    outage = False

    for r in product_rows:
        if not r.get("fe_ok") or not r.get("be_ok"):
            outage = True
            reasons.append(f"{r.get('name')}: frontend/backend down")
        if r.get("ssl", {}).get("expiring_soon"):
            reasons.append(
                f"{r.get('name')}: SSL expiring soon ({r['ssl'].get('days_left')}d)"
            )
        if r.get("fe_latency_warn"):
            reasons.append(
                f"{r.get('name')}: FE latency {r['fe'].get('latency_ms')}ms "
                f"(warn>{r.get('fe_latency_warn_ms')}ms)"
            )
        v = r.get("vercel") or {}
        if v.get("status") == "ERROR":
            reasons.append(f"{r.get('name')}: Vercel deploy ERROR")

    for b in backend_rows:
        if b.get("skipped"):
            continue
        be = b.get("be") or {}
        if not b.get("be_ok") or be.get("app_status") == "error":
            outage = True
            reasons.append(f"{b.get('name')}: backend {be.get('app_status') or 'DOWN'}")
        if be.get("app_status") == "degraded":
            reasons.append(f"{b.get('name')}: backend degraded")
        if b.get("deep_attention"):
            reasons.append(f"{b.get('name')}: dependency check not connected ({b.get('deep_line')})")
        if b.get("be_latency_warn"):
            reasons.append(
                f"{b.get('name')}: BE latency {be.get('latency_ms')}ms "
                f"(warn>{b.get('be_latency_warn_ms')}ms)"
            )

    if version_drift and version_drift.get("drift"):
        reasons.append(f"VERSION drift ({version_drift.get('note')})")
    if error_count > 0:
        reasons.append(f"{error_count} unresolved error(s) in collector (Sentry/log)")

    # Dedupe while preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for reason in reasons:
        if reason not in seen:
            seen.add(reason)
            uniq.append(reason)

    if outage:
        return "ACTION NEEDED", uniq
    if uniq:
        return "Attention", uniq
    return "Healthy", []
