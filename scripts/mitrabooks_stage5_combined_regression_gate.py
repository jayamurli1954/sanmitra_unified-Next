#!/usr/bin/env python3
"""Stage 5 combined MitraBooks ERP regression gate (read-only).

Proves that MitraBooks, MandirMitra, and GruhaMitra can coexist in the unified
ERP shell against the hosted staging stack:

1. Enabled modules and permissions drive access (compared by module key, not by
   hardcoded product name).
2. App context does not leak across tenants/workflows (each demo tenant resolves
   only its own tenant/organization context).
3. Accounting reports remain correct after mixed workflow postings (each tenant's
   trial balance returns HTTP 200 and is balanced: total_debit == total_credit).
4. Module-specific routes fail closed when module access is disabled: the
   ``require_enabled_module("business")`` guarded route ``/api/v1/business/parties``
   returns 2xx for the BUSINESS tenant and 403 for the HOUSING/TEMPLE tenants.

The gate is READ-ONLY: it only performs login + GET requests. It never posts,
mutates, prints tokens/passwords, or writes secrets. Sanitized evidence is
written under ``tmp/``.

Credentials are supplied through the runtime environment (prefer a secret
manager), one email/password pair per demo tenant:

    STAGE5_API_BASE_URL           (optional; default staging SG)
    MB_E2E_EMAIL / MB_E2E_PASSWORD          (demo-mitrabooks-business)
    MANDIR_E2E_EMAIL / MANDIR_E2E_PASSWORD  (demo-mandir-tenant)
    GRUHA_E2E_EMAIL / GRUHA_E2E_PASSWORD    (gruhamitra-demo-society)

Example:

    python scripts/mitrabooks_stage5_combined_regression_gate.py --as-of 2026-07-31
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_API_BASE = "https://sanmitra-unified-next-staging-sg.onrender.com"

# Module-gated route used as the authoritative fail-closed probe. It is guarded
# by require_enabled_module("business"), so it deterministically returns 403 for
# tenants without the business module enabled.
BUSINESS_MODULE_PROBE = "/api/v1/business/parties"

# Per-app expected context, aligned with app/core/modules/registry.py.
APP_CONFIG: dict[str, dict] = {
    "mitrabooks": {
        "app_key": "mitrabooks",
        "tenant_id": "demo-mitrabooks-business",
        "organization_type": "BUSINESS",
        "required_modules": {"business", "accounting", "audit"},
        "email_env": "MB_E2E_EMAIL",
        "password_env": "MB_E2E_PASSWORD",
        # BUSINESS tenant HAS the business module -> probe should succeed (2xx).
        "business_probe_should_pass": True,
    },
    "mandirmitra": {
        "app_key": "mandirmitra",
        "tenant_id": "demo-mandir-tenant",
        "organization_type": "TEMPLE",
        "required_modules": {"temple", "accounting", "audit"},
        "email_env": "MANDIR_E2E_EMAIL",
        "password_env": "MANDIR_E2E_PASSWORD",
        # TEMPLE tenant does NOT have the business module -> probe must fail closed (403).
        "business_probe_should_pass": False,
    },
    "gruhamitra": {
        "app_key": "gruhamitra",
        "tenant_id": "gruhamitra-demo-society",
        "organization_type": "HOUSING",
        "required_modules": {"housing", "accounting", "audit"},
        "email_env": "GRUHA_E2E_EMAIL",
        "password_env": "GRUHA_E2E_PASSWORD",
        # HOUSING tenant does NOT have the business module -> probe must fail closed (403).
        "business_probe_should_pass": False,
    },
}

FAIL_CLOSED_STATUSES = {401, 403, 404}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict | None = None,
    timeout: int = 60,
) -> tuple[int, dict | list]:
    data = None
    req_headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            payload = json.loads(raw or "{}")
            return int(getattr(response, "status", 200)), payload
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        try:
            payload = json.loads(raw or "{}")
        except json.JSONDecodeError:
            payload = {"detail": raw or exc.reason}
        return int(exc.code), payload


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


def check_app(app: str, api_base: str, as_of: str) -> dict:
    """Run the read-only combined-regression checks for one demo tenant."""
    cfg = APP_CONFIG[app]
    result: dict = {
        "app_key": cfg["app_key"],
        "tenant_id_expected": cfg["tenant_id"],
        "status": "pending",
        "steps": {},
    }
    email = os.environ.get(cfg["email_env"], "").strip()
    password = os.environ.get(cfg["password_env"], "").strip()
    if not email or not password:
        result["status"] = "failed"
        result["error"] = f"missing credentials: set {cfg['email_env']} and {cfg['password_env']}"
        return result

    app_key = cfg["app_key"]

    # 1. Login
    login_status, login_payload = _request_json(
        "POST",
        f"{api_base}/api/v1/auth/login",
        headers={"Content-Type": "application/json", "X-App-Key": app_key},
        body={"email": email, "password": password},
    )
    if login_status >= 300 or not isinstance(login_payload, dict) or not login_payload.get("access_token"):
        result["status"] = "failed"
        result["error"] = f"login failed HTTP {login_status}: {_detail(login_payload)}"
        return result
    token = str(login_payload["access_token"])
    auth = {"Authorization": f"Bearer {token}", "X-App-Key": app_key, "Content-Type": "application/json"}

    # 2. Modules/context: enabled modules + org type drive access
    mod_status, mod_payload = _request_json("GET", f"{api_base}/api/v1/modules/me", headers=auth)
    if mod_status >= 300 or not isinstance(mod_payload, dict):
        result["status"] = "failed"
        result["error"] = f"modules/me failed HTTP {mod_status}: {_detail(mod_payload)}"
        return result
    tenant_id = str(mod_payload.get("tenant_id") or "").strip()
    org_type = str(mod_payload.get("organization_type") or "").strip().upper()
    module_keys = _module_keys(mod_payload)
    missing = sorted(cfg["required_modules"] - module_keys)
    context_errors: list[str] = []
    if tenant_id != cfg["tenant_id"]:
        context_errors.append(f"tenant mismatch: expected {cfg['tenant_id']!r}, got {tenant_id!r}")
    if org_type != cfg["organization_type"]:
        context_errors.append(
            f"organization_type mismatch: expected {cfg['organization_type']!r}, got {org_type!r}"
        )
    if missing:
        context_errors.append(f"missing required modules: {', '.join(missing)}")
    result["tenant_id"] = tenant_id
    result["organization_type"] = org_type
    result["enabled_modules"] = sorted(module_keys)
    result["steps"]["context"] = {
        "status": "passed" if not context_errors else "failed",
        "errors": context_errors,
    }

    # 3. Accounting trial balance is tenant-scoped and balanced
    tb_qs = urlencode({"as_of": as_of})
    tb_status, tb_payload = _request_json(
        "GET", f"{api_base}/api/v1/accounting/reports/trial-balance?{tb_qs}", headers=auth
    )
    if tb_status >= 300 or not isinstance(tb_payload, dict):
        result["steps"]["accounting"] = {
            "status": "failed",
            "error": f"trial-balance failed HTTP {tb_status}: {_detail(tb_payload)}",
        }
    else:
        total_debit = float(tb_payload.get("total_debit") or 0)
        total_credit = float(tb_payload.get("total_credit") or 0)
        balanced = bool(tb_payload.get("balanced")) and abs(total_debit - total_credit) < 0.005
        result["steps"]["accounting"] = {
            "status": "passed" if balanced else "failed",
            "as_of": as_of,
            "total_debit": round(total_debit, 2),
            "total_credit": round(total_credit, 2),
            "balanced": balanced,
        }

    # 4. Module fail-closed probe on the business-guarded route
    probe_status, probe_payload = _request_json("GET", f"{api_base}{BUSINESS_MODULE_PROBE}", headers=auth)
    if cfg["business_probe_should_pass"]:
        ok = 200 <= probe_status < 300
        expectation = "2xx (business module enabled)"
    else:
        ok = probe_status in FAIL_CLOSED_STATUSES
        expectation = "fail-closed (401/403/404, business module disabled)"
    result["steps"]["module_access"] = {
        "status": "passed" if ok else "failed",
        "probe": BUSINESS_MODULE_PROBE,
        "http_status": probe_status,
        "expectation": expectation,
        "detail": _detail(probe_payload) if not ok else None,
    }

    step_statuses = [step.get("status") for step in result["steps"].values()]
    result["status"] = "passed" if all(s == "passed" for s in step_statuses) else "failed"
    return result


def cross_tenant_isolation(app_results: list[dict]) -> dict:
    """Confirm each demo tenant resolved a distinct tenant context (no leak)."""
    resolved = [r.get("tenant_id") for r in app_results if r.get("tenant_id")]
    unique = set(resolved)
    ok = len(resolved) == len(app_results) and len(unique) == len(app_results)
    return {
        "status": "passed" if ok else "failed",
        "resolved_tenants": resolved,
        "unique": sorted(unique),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 5 combined MitraBooks ERP regression gate (read-only)")
    parser.add_argument("--api-base", default=os.getenv("STAGE5_API_BASE_URL", DEFAULT_API_BASE))
    parser.add_argument(
        "--apps",
        default="mitrabooks,mandirmitra,gruhamitra",
        help="comma-separated subset of apps to check",
    )
    parser.add_argument(
        "--as-of",
        default=date.today().isoformat(),
        help="trial-balance as_of date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=ROOT / "tmp" / "mitrabooks-stage5-combined-regression-evidence.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the planned checks and config without making network calls",
    )
    args = parser.parse_args()

    api_base = str(args.api_base).rstrip("/")
    apps = [a.strip().lower() for a in str(args.apps).split(",") if a.strip()]
    unknown = [a for a in apps if a not in APP_CONFIG]
    if unknown:
        print(f"FAIL: unknown apps requested: {', '.join(unknown)}")
        print(f"       valid apps: {', '.join(APP_CONFIG)}")
        return 2

    if args.dry_run:
        print("Stage 5 combined regression gate - dry run")
        print(f" - api_base: {api_base}")
        print(f" - as_of: {args.as_of}")
        print(f" - fail-closed probe: {BUSINESS_MODULE_PROBE}")
        for app in apps:
            cfg = APP_CONFIG[app]
            print(
                f" - {app}: tenant={cfg['tenant_id']} org={cfg['organization_type']} "
                f"modules={sorted(cfg['required_modules'])} "
                f"business_probe_should_pass={cfg['business_probe_should_pass']} "
                f"creds_env=({cfg['email_env']},{cfg['password_env']})"
            )
        print("PASS: dry run only (no network calls, no assertions evaluated)")
        return 0

    evidence: dict = {
        "gate": "mitrabooks_stage5_combined_regression",
        "status": "pending",
        "read_only": True,
        "started_at": utc_now(),
        "api_base": api_base,
        "as_of": args.as_of,
        "apps": apps,
        "results": [],
    }

    app_results: list[dict] = []
    for app in apps:
        print(f"\n=== {app} ===", flush=True)
        res = check_app(app, api_base, args.as_of)
        app_results.append(res)
        evidence["results"].append(res)
        for name, step in res.get("steps", {}).items():
            print(f"  {name}: {step.get('status')}")
        if res.get("error"):
            print(f"  error: {res['error']}")

    isolation = cross_tenant_isolation(app_results)
    evidence["cross_tenant_isolation"] = isolation
    print(f"\n=== cross-tenant isolation ===\n  {isolation['status']} ({isolation['resolved_tenants']})")

    all_passed = all(r.get("status") == "passed" for r in app_results) and isolation["status"] == "passed"
    evidence["status"] = "passed" if all_passed else "failed"
    evidence["completed_at"] = utc_now()

    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    print("\n================================================")
    print("STAGE 5 COMBINED REGRESSION SUMMARY")
    print("================================================")
    for res in app_results:
        print(f"  [{res.get('status', '?').upper()}] {res.get('app_key')} ({res.get('tenant_id') or res.get('tenant_id_expected')})")
    print(f"  [{isolation['status'].upper()}] cross-tenant isolation")
    print(f"  evidence: {args.evidence}")

    if all_passed:
        print("\nPASS: Stage 5 combined MitraBooks ERP regression gate")
        return 0
    print("\nFAIL: Stage 5 combined MitraBooks ERP regression gate")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
