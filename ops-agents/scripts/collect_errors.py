"""
Error collector (pluggable source).

The summarizer is only worth running if it has errors to summarize. This module
gathers recent error text from whatever source you have, and returns a list of
short strings. It returns [] cleanly when nothing is configured, so the rest of
the pipeline still runs (you just get a "no errors" report).

Sources, in priority order:
  1. Sentry  - if SENTRY_AUTH_TOKEN, SENTRY_ORG, SENTRY_PROJECT are set.
  2. Log file - if OPS_LOG_FILE points at a readable file (tails ERROR lines).
  3. Nothing - returns [].

Raw text is NOT redacted here; redaction happens in generate_report.py right
before the single LLM call, so there is exactly one place to audit.
"""

from __future__ import annotations

import os
from typing import Any

import requests

SENTRY_AUTH_TOKEN = os.getenv("SENTRY_AUTH_TOKEN")
SENTRY_ORG = os.getenv("SENTRY_ORG")
SENTRY_PROJECT = os.getenv("SENTRY_PROJECT")
OPS_LOG_FILE = os.getenv("OPS_LOG_FILE")

MAX_ITEMS = int(os.getenv("ERROR_MAX_ITEMS", "20"))


def _from_sentry() -> list[str]:
    url = f"https://sentry.io/api/0/projects/{SENTRY_ORG}/{SENTRY_PROJECT}/issues/"
    headers = {"Authorization": f"Bearer {SENTRY_AUTH_TOKEN}"}
    # Unresolved issues seen in the last 24h, most frequent first.
    params = {"statsPeriod": "24h", "query": "is:unresolved", "sort": "freq"}
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    issues: list[dict[str, Any]] = resp.json()[:MAX_ITEMS]
    return [
        f"[{i.get('count', '?')}x] {i.get('culprit') or i.get('title', 'error')}: "
        f"{i.get('metadata', {}).get('value', '')}".strip()
        for i in issues
    ]


def _from_logfile() -> list[str]:
    keep: list[str] = []
    with open(OPS_LOG_FILE, "r", errors="replace") as f:  # type: ignore[arg-type]
        for line in f:
            if any(k in line for k in ("ERROR", "CRITICAL", "Traceback", "Exception")):
                keep.append(line.rstrip())
    return keep[-MAX_ITEMS:]


def collect_errors() -> list[str]:
    """Return recent error strings from the first configured source, else []."""
    try:
        if SENTRY_AUTH_TOKEN and SENTRY_ORG and SENTRY_PROJECT:
            return _from_sentry()
        if OPS_LOG_FILE and os.path.isfile(OPS_LOG_FILE):
            return _from_logfile()
    except Exception as e:
        # A broken error source must never crash the report.
        return [f"(error collector failed: {type(e).__name__})"]
    return []
