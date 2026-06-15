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

TIMEOUT = float(os.getenv("CHECK_TIMEOUT_SECONDS", "10"))
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
