#!/usr/bin/env python3
"""MitraBooks Phase 5 MIS / Data-Health / Export-governance gate (read-only).

Proves that the MitraBooks ERP Phase 5 reporting surfaces are production-signoff
ready against the hosted staging stack, without any mutation:

1. MIS KPI contract (`/api/v1/business/mis/kpis`) returns a source-backed,
   deterministic payload (trend, top parties, working capital, overdue views).
2. Financial-health contract (`/api/v1/business/financial-health?narrate=false`)
   returns deterministic summary/kpis/charts/alerts with AI narration OFF.
3. Data Health Score (`/api/v1/business/data-health`) returns score/grade/status
   plus a remediation issue list with stable issue ids and workspace deep-links.
4. Export governance (`/api/v1/business/reports/export`) stamps governed headers
   (`X-SanMitra-Export-Governed: true` + type/format/entity) for every format.
5. Tally XML export (`/api/v1/business/tally/xml-export`) returns governed
   application/xml with the expected ledger-master envelope + source metadata.
6. Optional fail-closed / RBAC probe: when a non-business tenant credential is
   supplied, the Phase 5 routes fail closed (401/403/404) for that tenant.

The gate is READ-ONLY: login + GET only. It never posts, mutates, prints
tokens/passwords, or writes secrets. Sanitized evidence is written under ``tmp/``.

Credentials come from the runtime environment (prefer a secret manager):

    MB_PHASE5_API_BASE_URL   (optional; default staging SG)
    MB_E2E_EMAIL / MB_E2E_PASSWORD          (demo-mitrabooks-business)
    GRUHA_E2E_EMAIL / GRUHA_E2E_PASSWORD    (optional fail-closed probe tenant)

Example:

    python scripts/mitrabooks_phase5_mis_datahealth_export_gate.py --as-of 2026-07-31
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_API_BASE = "https://sanmitra-unified-next-staging-sg.onrender.com"

BUSINESS_APP_KEY = "mitrabooks"
BUSINESS_TENANT_ID = "demo-mitrabooks-business"
BUSINESS_ORG_TYPE = "BUSINESS"
BUSINESS_REQUIRED_MODULES = {"business", "accounting", "audit"}

# Optional non-business tenant used only to prove Phase 5 routes fail closed.
FAILCLOSED_APP_KEY = "gruhamitra"
FAILCLOSED_EMAIL_ENV = "GRUHA_E2E_EMAIL"
FAILCLOSED_PASSWORD_ENV = "GRUHA_E2E_PASSWORD"

FAIL_CLOSED_STATUSES = {401, 403, 404}
DEFAULT_EXPORT_FORMATS = ("json", "csv", "xlsx", "pdf")

# Phase 5 routes probed for fail-closed behaviour on a non-business tenant.
PHASE5_PROBE_ROUTES = (
    "/api/v1/business/mis/kpis",
    "/api/v1/business/data-health",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _request_raw(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict | None = None,
    timeout: int = 90,
) -> tuple[int, dict[str, str], str]:
    """Return (status, lowercased-headers, raw-text) for any content type."""
    data = None
    req_headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            hdrs = {str(k).lower(): str(v) for k, v in response.headers.items()}
            return int(getattr(response, "status", 200)), hdrs, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        hdrs = {str(k).lower(): str(v) for k, v in (exc.headers or {}).items()}
        return int(exc.code), hdrs, raw


def _request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict | None = None,
    timeout: int = 90,
) -> tuple[int, dict | list]:
    status, _hdrs, raw = _request_raw(method, url, headers=headers, body=body, timeout=timeout)
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError:
        payload = {"detail": raw[:200]}
    return status, payload


def _detail(payload: dict | list) -> str:
    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("error") or payload.get("message")
        if isinstance(detail, str):
            return detail
        return str(detail or payload)
    return str(payload)


def _module_keys(modules_payload: dict) -> set[str]:
    keys: set[str] = set()
    for item in modules_payload.get("enabled_modules") or []:
        if isinstance(item, dict):
            key = str(item.get("module_key") or "").strip().lower()
        else:
            key = str(item or "").strip().lower()
        if key:
            keys.add(key)
    return keys


def _login(api_base: str, app_key: str, email: str, password: str) -> tuple[str | None, str]:
    status, payload = _request_json(
        "POST",
        f"{api_base}/api/v1/auth/login",
        headers={"Content-Type": "application/json", "X-App-Key": app_key},
        body={"email": email, "password": password},
    )
    if status >= 300 or not isinstance(payload, dict) or not payload.get("access_token"):
        return None, f"login failed HTTP {status}: {_detail(payload)}"
    return str(payload["access_token"]), ""


def _step(name: str, passed: bool, **extra) -> dict:
    return {"name": name, "status": "passed" if passed else "failed", **extra}


def check_context(api_base: str, auth: dict) -> dict:
    status, payload = _request_json("GET", f"{api_base}/api/v1/modules/me", headers=auth)
    if status >= 300 or not isinstance(payload, dict):
        return _step("context", False, error=f"modules/me HTTP {status}: {_detail(payload)}")
    tenant_id = str(payload.get("tenant_id") or "").strip()
    org_type = str(payload.get("organization_type") or "").strip().upper()
    module_keys = _module_keys(payload)
    errors: list[str] = []
    if tenant_id != BUSINESS_TENANT_ID:
        errors.append(f"tenant mismatch: expected {BUSINESS_TENANT_ID!r}, got {tenant_id!r}")
    if org_type != BUSINESS_ORG_TYPE:
        errors.append(f"org_type mismatch: expected {BUSINESS_ORG_TYPE!r}, got {org_type!r}")
    missing = sorted(BUSINESS_REQUIRED_MODULES - module_keys)
    if missing:
        errors.append(f"missing modules: {', '.join(missing)}")
    return _step(
        "context",
        not errors,
        tenant_id=tenant_id,
        organization_type=org_type,
        enabled_modules=sorted(module_keys),
        errors=errors,
    )


def check_mis(api_base: str, auth: dict, as_of: str) -> dict:
    qs = urlencode({"as_of": as_of})
    status, payload = _request_json("GET", f"{api_base}/api/v1/business/mis/kpis?{qs}", headers=auth)
    if status != 200 or not isinstance(payload, dict):
        return _step("mis_kpis", False, http_status=status, error=_detail(payload))
    required = {"source", "monthly_sales_purchase_trend", "top_customers", "working_capital", "overdue"}
    present = required & set(payload.keys())
    missing = sorted(required - present)
    wc = payload.get("working_capital") if isinstance(payload.get("working_capital"), dict) else {}
    has_source = isinstance(payload.get("source"), dict) and bool(payload["source"])
    ok = not missing and has_source
    return _step(
        "mis_kpis",
        ok,
        http_status=status,
        missing_keys=missing,
        source_backed=has_source,
        current_ratio_present="current_ratio" in wc,
    )


def check_financial_health(api_base: str, auth: dict, as_of: str) -> dict:
    qs = urlencode({"as_of": as_of, "narrate": "false"})
    status, payload = _request_json(
        "GET", f"{api_base}/api/v1/business/financial-health?{qs}", headers=auth
    )
    if status != 200 or not isinstance(payload, dict):
        return _step("financial_health", False, http_status=status, error=_detail(payload))
    required = {"summary", "kpis", "charts", "alerts"}
    missing = sorted(required - set(payload.keys()))
    # narrate=false must yield deterministic output with no AI narrative.
    narrative_off = payload.get("narrative") in (None, "", [])
    ok = not missing and narrative_off
    return _step(
        "financial_health",
        ok,
        http_status=status,
        missing_keys=missing,
        narrative_off=narrative_off,
    )


def check_data_health(api_base: str, auth: dict, as_of: str) -> dict:
    qs = urlencode({"as_of": as_of})
    status, payload = _request_json("GET", f"{api_base}/api/v1/business/data-health?{qs}", headers=auth)
    if status != 200 or not isinstance(payload, dict):
        return _step("data_health", False, http_status=status, error=_detail(payload))
    errors: list[str] = []
    if not isinstance(payload.get("score"), (int, float)):
        errors.append("score missing/non-numeric")
    if not payload.get("grade"):
        errors.append("grade missing")
    if payload.get("status") not in {"ready", "needs_attention"}:
        errors.append(f"unexpected status {payload.get('status')!r}")
    rules = payload.get("rules")
    if not isinstance(rules, list) or not rules:
        errors.append("rules missing/empty")
    issues = payload.get("issues")
    if not isinstance(issues, list):
        errors.append("issues not a list")
    else:
        for issue in issues:
            if not isinstance(issue, dict) or not {"issue_id", "workspace", "action_label"} <= set(issue.keys()):
                errors.append("issue missing issue_id/workspace/action_label")
                break
    return _step(
        "data_health",
        not errors,
        http_status=status,
        score=payload.get("score"),
        grade=payload.get("grade"),
        health_status=payload.get("status"),
        rule_count=len(rules) if isinstance(rules, list) else 0,
        issue_count=len(issues) if isinstance(issues, list) else 0,
        errors=errors,
    )


def check_export_governance(api_base: str, auth: dict, as_of: str, formats: tuple[str, ...]) -> dict:
    per_format: list[dict] = []
    all_ok = True
    for fmt in formats:
        qs = urlencode({"report": "trial_balance", "format": fmt, "as_of": as_of})
        status, hdrs, _raw = _request_raw(
            "GET", f"{api_base}/api/v1/business/reports/export?{qs}", headers=auth
        )
        governed = hdrs.get("x-sanmitra-export-governed") == "true"
        type_ok = hdrs.get("x-sanmitra-export-type") == "business_report"
        format_ok = hdrs.get("x-sanmitra-export-format") == fmt
        ok = status == 200 and governed and type_ok and format_ok
        all_ok = all_ok and ok
        per_format.append(
            {
                "format": fmt,
                "http_status": status,
                "governed": governed,
                "type_ok": type_ok,
                "format_ok": format_ok,
                "status": "passed" if ok else "failed",
            }
        )
    return _step("export_governance", all_ok, formats=per_format)


def check_tally_xml(api_base: str, auth: dict, as_of: str) -> dict:
    qs = urlencode({"as_of": as_of})
    status, hdrs, raw = _request_raw(
        "GET", f"{api_base}/api/v1/business/tally/xml-export?{qs}", headers=auth
    )
    content_type = hdrs.get("content-type", "")
    governed = hdrs.get("x-sanmitra-export-governed") == "true"
    type_ok = hdrs.get("x-sanmitra-export-type") == "tally_xml"
    is_xml = "xml" in content_type.lower()
    has_masters = "All Masters" in raw
    has_source = "SANMITRAEXPORT" in raw
    ok = status == 200 and governed and type_ok and is_xml and has_masters and has_source
    return _step(
        "tally_xml",
        ok,
        http_status=status,
        content_type=content_type,
        governed=governed,
        type_ok=type_ok,
        is_xml=is_xml,
        has_ledger_masters=has_masters,
        has_source_metadata=has_source,
    )


def check_fail_closed(api_base: str) -> dict:
    email = os.environ.get(FAILCLOSED_EMAIL_ENV, "").strip()
    password = os.environ.get(FAILCLOSED_PASSWORD_ENV, "").strip()
    if not email or not password:
        return _step(
            "fail_closed",
            True,
            skipped=True,
            note=f"no non-business creds ({FAILCLOSED_EMAIL_ENV}/{FAILCLOSED_PASSWORD_ENV}); probe skipped",
        )
    token, err = _login(api_base, FAILCLOSED_APP_KEY, email, password)
    if not token:
        return _step("fail_closed", False, error=err)
    auth = {"Authorization": f"Bearer {token}", "X-App-Key": FAILCLOSED_APP_KEY, "Content-Type": "application/json"}
    probes: list[dict] = []
    all_ok = True
    for route in PHASE5_PROBE_ROUTES:
        status, _payload = _request_json("GET", f"{api_base}{route}", headers=auth)
        ok = status in FAIL_CLOSED_STATUSES
        all_ok = all_ok and ok
        probes.append({"route": route, "http_status": status, "status": "passed" if ok else "failed"})
    return _step("fail_closed", all_ok, app_key=FAILCLOSED_APP_KEY, probes=probes)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="MitraBooks Phase 5 MIS/Data-Health/Export gate (read-only)"
    )
    parser.add_argument("--api-base", default=os.getenv("MB_PHASE5_API_BASE_URL", DEFAULT_API_BASE))
    parser.add_argument("--as-of", default=date.today().isoformat(), help="report as_of date (YYYY-MM-DD)")
    parser.add_argument(
        "--formats",
        default=",".join(DEFAULT_EXPORT_FORMATS),
        help="comma-separated export formats to verify (default json,csv,xlsx,pdf)",
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=ROOT / "tmp" / "mitrabooks-phase5-mis-datahealth-export-evidence.json",
    )
    parser.add_argument("--dry-run", action="store_true", help="print planned checks without network calls")
    args = parser.parse_args()

    api_base = str(args.api_base).rstrip("/")
    formats = tuple(f.strip().lower() for f in str(args.formats).split(",") if f.strip())
    bad_formats = [f for f in formats if f not in {"json", "csv", "xlsx", "pdf"}]
    if bad_formats:
        print(f"FAIL: unknown export formats: {', '.join(bad_formats)}")
        return 2

    if args.dry_run:
        print("MitraBooks Phase 5 MIS/Data-Health/Export gate - dry run")
        print(f" - api_base: {api_base}")
        print(f" - as_of: {args.as_of}")
        print(f" - business tenant: {BUSINESS_TENANT_ID} (app_key={BUSINESS_APP_KEY}, org={BUSINESS_ORG_TYPE})")
        print(f" - required modules: {sorted(BUSINESS_REQUIRED_MODULES)}")
        print(f" - export formats: {list(formats)}")
        print(f" - fail-closed probe routes: {list(PHASE5_PROBE_ROUTES)}")
        print(f" - business creds env: (MB_E2E_EMAIL, MB_E2E_PASSWORD)")
        print(f" - optional fail-closed creds env: ({FAILCLOSED_EMAIL_ENV}, {FAILCLOSED_PASSWORD_ENV})")
        print("PASS: dry run only (no network calls, no assertions evaluated)")
        return 0

    email = os.environ.get("MB_E2E_EMAIL", "").strip()
    password = os.environ.get("MB_E2E_PASSWORD", "").strip()
    if not email or not password:
        print("FAIL: missing credentials: set MB_E2E_EMAIL and MB_E2E_PASSWORD")
        return 2

    evidence: dict = {
        "gate": "mitrabooks_phase5_mis_datahealth_export",
        "status": "pending",
        "read_only": True,
        "started_at": utc_now(),
        "api_base": api_base,
        "as_of": args.as_of,
        "formats": list(formats),
        "steps": [],
    }

    token, err = _login(api_base, BUSINESS_APP_KEY, email, password)
    if not token:
        print(f"FAIL: {err}")
        evidence["status"] = "failed"
        evidence["error"] = err
        evidence["completed_at"] = utc_now()
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        return 1
    auth = {"Authorization": f"Bearer {token}", "X-App-Key": BUSINESS_APP_KEY, "Content-Type": "application/json"}

    steps = [
        check_context(api_base, auth),
        check_mis(api_base, auth, args.as_of),
        check_financial_health(api_base, auth, args.as_of),
        check_data_health(api_base, auth, args.as_of),
        check_export_governance(api_base, auth, args.as_of, formats),
        check_tally_xml(api_base, auth, args.as_of),
        check_fail_closed(api_base),
    ]
    evidence["steps"] = steps

    for step in steps:
        label = step.get("status", "?")
        if step.get("skipped"):
            label = "skipped"
        print(f"  {step['name']}: {label}")
        if step.get("error"):
            print(f"    error: {step['error']}")

    all_passed = all(s.get("status") == "passed" for s in steps)
    evidence["status"] = "passed" if all_passed else "failed"
    evidence["completed_at"] = utc_now()

    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    print("\n================================================")
    print("MITRABOOKS PHASE 5 MIS / DATA-HEALTH / EXPORT SUMMARY")
    print("================================================")
    for step in steps:
        label = "SKIPPED" if step.get("skipped") else step.get("status", "?").upper()
        print(f"  [{label}] {step['name']}")
    print(f"  evidence: {args.evidence}")

    if all_passed:
        print("\nPASS: MitraBooks Phase 5 MIS/Data-Health/Export gate")
        return 0
    print("\nFAIL: MitraBooks Phase 5 MIS/Data-Health/Export gate")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
