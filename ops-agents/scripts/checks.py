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
from typing import Any
from urllib.parse import urlparse

import requests

TIMEOUT = float(os.getenv("CHECK_TIMEOUT_SECONDS", "20"))
HEALTH_TOKEN = os.getenv("HEALTH_TOKEN")  # forwarded if the backend requires it


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
    result: dict[str, Any] = {"url": health_url, "reachable": False,
                              "status_code": None, "latency_ms": None,
                              "app_status": None, "checks": None, "error": None}
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
            result["checks"] = body.get("checks")
        except ValueError:
            result["error"] = "health endpoint did not return JSON"
    except requests.exceptions.RequestException as e:
        result.update(error=f"{type(e).__name__}")
    return result


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

    if fe_ok and be_ok:
        return None
    if not fe_ok and be_ok:
        if ssl_error:
            return "Vercel/DNS/SSL — SSL handshake failed; check Vercel domain assignment and DNS CNAME/A records"
        if "Timeout" in fe_err or "timeout" in fe_err:
            return "Vercel/DNS — connection timeout; check DNS records and Vercel project domain"
        return "Vercel/DNS/frontend — backend healthy, frontend unreachable; check Vercel deployment"
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
