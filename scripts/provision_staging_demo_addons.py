#!/usr/bin/env python3
"""Provision enterprise add-ons for the MitraBooks demo tenant on staging.

Platform-owner (super_admin) action via HTTP API — does not print tokens or passwords.

Usage (interactive prompts for secrets):
    python scripts/provision_staging_demo_addons.py

Or set env vars:
    STAGING_API_BASE_URL=https://sanmitra-unified-next-staging-sg.onrender.com
    SUPER_ADMIN_EMAIL=superadmin@sanmitra.local
    SUPER_ADMIN_PASSWORD=<staging secret>
    DEMO_MITRABOOKS_TENANT_ID=demo-mitrabooks-business
"""

from __future__ import annotations

import getpass
import json
import os
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

DEFAULT_API_BASE = "https://sanmitra-unified-next-staging-sg.onrender.com"
DEFAULT_APP_KEY = "mitrabooks"
DEFAULT_TENANT_ID = "demo-mitrabooks-business"
DEFAULT_SUPERADMIN_EMAIL = "superadmin@sanmitra.local"


def _request_json(request: Request, timeout: int = 30) -> tuple[int, dict]:
    try:
        with urlopen(request, timeout=timeout) as response:
            status = int(getattr(response, "status", 200))
            body = response.read().decode("utf-8")
            return status, json.loads(body or "{}")
    except HTTPError as exc:
        payload = {"detail": exc.reason}
        try:
            payload = json.loads(exc.read().decode("utf-8") or "{}")
        except Exception:
            pass
        return int(exc.code), payload


def _detail(payload: dict) -> str:
    detail = payload.get("detail")
    if isinstance(detail, str):
        return detail
    return str(payload or "unknown error")


def _login(api_base: str, email: str, password: str, app_key: str) -> str:
    login_body = json.dumps({"email": email, "password": password}).encode("utf-8")
    login_req = Request(
        f"{api_base}/api/v1/auth/login",
        data=login_body,
        headers={"Content-Type": "application/json", "X-App-Key": app_key},
        method="POST",
    )
    status, payload = _request_json(login_req)
    if status != 200:
        raise RuntimeError(f"Login failed ({status}): {_detail(payload)}")
    token = str(payload.get("access_token") or "").strip()
    if not token:
        raise RuntimeError("Login succeeded but no access_token was returned")
    return token


def _put_addon(api_base: str, token: str, app_key: str, tenant_id: str, addon: str, available: bool) -> None:
    body = json.dumps({"available": available}).encode("utf-8")
    req = Request(
        f"{api_base}/api/v1/platform-owner/tenants/{tenant_id}/addon/{addon}",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "X-App-Key": app_key,
        },
        method="PUT",
    )
    status, payload = _request_json(req)
    if status != 200:
        raise RuntimeError(f"Provision {addon} failed ({status}): {_detail(payload)}")
    print(f"OK: {addon} available={available} for tenant {tenant_id}")


def _put_hr_addon(api_base: str, token: str, app_key: str, tenant_id: str, available: bool) -> None:
    body = json.dumps({"available": available}).encode("utf-8")
    req = Request(
        f"{api_base}/api/v1/platform-owner/tenants/{tenant_id}/hr-addon",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "X-App-Key": app_key,
        },
        method="PUT",
    )
    status, payload = _request_json(req)
    if status != 200:
        raise RuntimeError(f"Provision HR failed ({status}): {_detail(payload)}")
    print(f"OK: hr-addon available={available} for tenant {tenant_id}")


def main() -> int:
    api_base = str(os.getenv("STAGING_API_BASE_URL", DEFAULT_API_BASE)).strip().rstrip("/")
    app_key = str(os.getenv("STAGING_APP_KEY", DEFAULT_APP_KEY)).strip() or DEFAULT_APP_KEY
    tenant_id = str(os.getenv("DEMO_MITRABOOKS_TENANT_ID", DEFAULT_TENANT_ID)).strip() or DEFAULT_TENANT_ID
    email = str(os.getenv("SUPER_ADMIN_EMAIL", "")).strip() or DEFAULT_SUPERADMIN_EMAIL
    password = str(os.getenv("SUPER_ADMIN_PASSWORD", "")).strip()

    if sys.stdin.isatty() and not password:
        password = getpass.getpass(f"Super-admin password for {email}: ").strip()

    if not password:
        print("FAIL: SUPER_ADMIN_PASSWORD is required (env var or interactive prompt).")
        return 2

    try:
        token = _login(api_base, email, password, app_key)
        _put_hr_addon(api_base, token, app_key, tenant_id, True)
        _put_addon(api_base, token, app_key, tenant_id, "cost-centre", True)
        _put_addon(api_base, token, app_key, tenant_id, "manufacturing", True)
    except RuntimeError as exc:
        print(f"FAIL: {exc}")
        return 1

    print()
    print("Provisioning complete. Next steps:")
    print("  1. Log in as business.admin@sanmitra.local")
    print("  2. Open Manufacturing → Manufacturing → Enable Cost Centres (if prompted)")
    print("  3. Hard refresh the browser (Ctrl+Shift+R)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
